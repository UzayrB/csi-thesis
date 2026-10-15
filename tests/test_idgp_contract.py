"""The identification contract of brief 2026-09-23f, enforced as behaviour.

A pass handed to IDGP identification features carries only the CSI segment, the start and end
times, the path ID (with its protocol length and the rig), and no module the IDGP arms use imports
tracking code. Intermediate anchors and the old walk_edge span are unreachable.
"""

import ast
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline.identify import idgp_contract as K  # noqa: E402

IDGP_MODULES = sorted(glob.glob(os.path.join(ROOT, "pipeline", "identify", "idgp_*.py")))
FORBIDDEN_PKGS = ("pipeline.constrained", "pipeline.realtime", "pipeline.models", "pipeline.branches")
FORBIDDEN_NAMES = ("anchor_times", "anchor_coords", "i_we_lo", "i_we_hi", "walk_edge_lo",
                   "walk_edge_hi", "speed_m_s")
INV = os.path.join(ROOT, "runs", "identify", "idmax", "inventory.json")
HAVE_BANK = os.path.exists(INV) and os.path.isdir(os.path.join(ROOT, "runs", "identify", "idmax", "bank"))


def _rows(n=4):
    inv = json.load(open(INV))
    return [r for r in inv if r["line"] == "A_fwd"][:n] + [r for r in inv if r["line"] == "D_rev"][:1]


def _synthetic(margin=0.0, path="A_fwd", seed=0, dur=4.0):
    rng = np.random.default_rng(seed)
    m = int(round(margin * K.FS))
    n = int(round(dur * K.FS)) + 2 * m
    t = np.arange(n) / K.FS
    amp = 20 + rng.normal(0, 1, (3, n, 103)) + 3 * np.sin(2 * np.pi * 1.8 * t)[None, :, None]
    return K.ContractPass(amp=amp.astype(np.float32), fs=K.FS, t_start=100.0, t_end=100.0 + dur,
                          t_amp0=100.0 - margin, path_id=path, path_length_m=K.path_length(path),
                          rig=tuple(sorted(K.RIG_ROOM_A.items())), margin_s=margin)


def test_contract_pass_has_exactly_the_allowed_fields():
    assert K.contract_fields() == K.ALLOWED_FIELDS
    for f in K.contract_fields():
        assert not any(b in f for b in ("anchor", "label", "participant", "session", "speed", "who"))


def test_s_se_is_protocol_length_over_press_interval():
    p = _synthetic(dur=4.0)
    assert K.s_se(p) == pytest.approx(5.0 / 4.0)
    assert K.path_length("C_fwd") == pytest.approx(np.sqrt(50.0))


def test_pass_features_takes_only_the_contract_pass():
    import inspect
    from pipeline.identify.idgp_signal import pass_features
    assert list(inspect.signature(pass_features).parameters) == ["cp"]
    f = pass_features(_synthetic())
    assert f["P|pace|-|-|S_se"] == pytest.approx(1.25)
    # a synthetic 1.8 Hz step modulation must be recovered as the fused cadence
    assert f["P|rhy|-|fu|cadence_hz"] == pytest.approx(1.8, abs=0.1)


def test_features_do_not_move_when_the_margin_samples_change():
    """With margin 0.5 s, only cadence-derived quantities may depend on samples outside the presses."""
    from pipeline.identify.idgp_signal import pass_features
    p = _synthetic(margin=0.5)
    a2 = p.amp.copy()
    m = int(0.5 * K.FS)
    a2[:, :m, :] = 0.0
    a2[:, -m:, :] = 0.0
    q = K.ContractPass(**{**{f: getattr(p, f) for f in K.contract_fields()}, "amp": a2})
    fp, fq = pass_features(p), pass_features(q)
    for k in ("P|pace|-|-|S_se",) + tuple(k for k in fp if "|env|" in k or "|ctl|" in k):
        assert fp[k] == pytest.approx(fq[k], nan_ok=True), k


@pytest.mark.skipif(not HAVE_BANK, reason="the id19 bank is not on this machine")
def test_segment_is_start_to_end_only():
    for r in _rows():
        p = K.from_bank(r, margin_s=0.0)
        n = p.amp.shape[1]
        assert abs(n - (r["t_end_press"] - r["t_start_press"]) * K.FS) <= 1.5
        assert p.index_of(p.t_start) == 0 and abs(p.index_of(p.t_end) - n) <= 1
        q = K.from_bank(r, margin_s=0.5)
        assert q.amp.shape[1] == n + 150
        np.testing.assert_array_equal(q.walk(), p.amp)


@pytest.mark.skipif(not HAVE_BANK, reason="the id19 bank is not on this machine")
def test_row_stripped_or_poisoned_builds_the_identical_pass():
    for r in _rows():
        base = K.from_bank(r)
        stripped = K.from_bank({k: r[k] for k in K.ROW_KEYS})
        poisoned = dict(r, anchor_times=[-1e9] * 6, walk_edge_lo=-1e9, walk_edge_hi=1e9,
                        speed_m_s=99.0, participant="X", stem="X")
        for other in (stripped, K.from_bank(poisoned)):
            np.testing.assert_array_equal(base.amp, other.amp)
            assert (base.t_start, base.t_end, base.path_id) == (other.t_start, other.t_end, other.path_id)


def _code_strings_and_names(path):
    tree = ast.parse(open(path).read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                    getattr(node.body[0], "value", None), ast.Constant):
                docs.add(id(node.body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append(node.value)
        elif isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
    return tree, out


def test_no_idgp_module_names_an_intermediate_anchor_or_oracle_speed():
    assert IDGP_MODULES
    for p in IDGP_MODULES:
        _t, toks = _code_strings_and_names(p)
        bad = [t for t in toks if any(f in t for f in FORBIDDEN_NAMES)]
        assert not bad, (os.path.basename(p), bad)


def test_no_idgp_module_imports_tracking_code_statically():
    for p in IDGP_MODULES:
        tree, _ = _code_strings_and_names(p)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                assert not m.startswith(FORBIDDEN_PKGS), (os.path.basename(p), m)


def test_no_tracking_module_is_loaded_while_the_arms_run():
    code = (
        "import sys, importlib, glob, os\n"
        "sys.path.insert(0, %r)\n"
        "for p in sorted(glob.glob(os.path.join(%r, 'pipeline', 'identify', 'idgp_*.py'))):\n"
        "    importlib.import_module('pipeline.identify.' + os.path.basename(p)[:-3])\n"
        "import tests.test_idgp_contract as T\n"
        "from pipeline.identify.idgp_signal import pass_features\n"
        "pass_features(T._synthetic())\n"
        "bad = sorted(m for m in sys.modules if m.startswith(%r))\n"
        "print('BAD', bad)\n"
        "sys.exit(1 if bad else 0)\n" % (ROOT, ROOT, FORBIDDEN_PKGS))
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": ROOT, "KMP_DUPLICATE_LIB_OK": "TRUE"})
    assert r.returncode == 0, r.stdout + r.stderr


def test_protocol_paths_match_the_tape():
    try:
        from pipeline.constrained import paths as P
        tape = P.load_paths()
    except Exception:                                                      # noqa: BLE001
        pytest.skip("the ground-truth sidecars are not on this machine")
    if not tape:
        pytest.skip("no taped lines found")
    for k, (a, b) in K.PATHS.items():
        np.testing.assert_allclose(tape[k][0], a)
        np.testing.assert_allclose(tape[k][-1], b)
    # A_fwd runs north, away from the TX
    assert K.PATHS["A_fwd"][1][1] > K.PATHS["A_fwd"][0][1] > K.RIG_ROOM_A["TX"][1]
