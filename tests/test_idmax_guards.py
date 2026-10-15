"""Guards for the 2026-09-23b IDMAX run. Every test checks BEHAVIOUR, not a message.

1. retired participants and free-mode recordings are never read
2. no test label is read before final scoring
3. no speed input enters a gait arm
4. no pass is split across train and test, in any scope
5. participant names never leave runs/
"""

import glob
import os
import re

import numpy as np
import pytest

from pipeline.identify import idmax_common as IC
from pipeline.identify.common import RETIRED, SIX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ 1

@pytest.fixture(autouse=True)
def _private_reads_log(monkeypatch, tmp_path):
    """Tests never write the run's real READS.log: a test call is not a read (fault 4, 13:57)."""
    monkeypatch.setattr(IC, "READS_LOG", str(tmp_path / "READS.log"))


@pytest.mark.parametrize("path", [
    "data/room_A/session_03/participant_PA5_DEMO_free_RX1.bin",
    "data/room_A/session_03/participant_PA6_DEMO_free.gt.json",
    "data/room_A/session_01/participant_Azrah_walk_RX1.bin",
    "data/room_A/session_02/participant_Zaid_walk.gt.json",
    "data/room_A/session_01/20260909-104952/whatever_RX1.bin",
])
def test_forbidden_paths_are_refused(path):
    with pytest.raises(PermissionError):
        IC.assert_allowed(path)


@pytest.mark.parametrize("path", [
    "data/room_A/session_01/participant_PA5_walk_RX1.bin",
    "data/room_A/session_03/participant_PA4_TEST_walk.gt.json",
])
def test_the_six_walk_recordings_are_allowed(path):
    IC.assert_allowed(path)


def test_reads_log_holds_only_allowed_stems():
    p = os.path.join(ROOT, "runs", "identify", "idmax", "READS.log")
    if not os.path.exists(p):
        pytest.skip("no IDMAX read yet")
    # documented non-reads, honoured ONLY for a PID that was never a registered IDMAX job
    reg = {l.split("\t")[0] for l in open(os.path.join(ROOT, "runs", "identify", "logs", "idmax_pids.tsv"))}
    excl = set()
    xp = os.path.join(ROOT, "runs", "identify", "idmax", "READS.not_reads.tsv")
    if os.path.exists(xp):
        for l in open(xp, encoding="utf-8"):
            if l.startswith("#") or not l.strip():
                continue
            pid, path, _why = l.rstrip("\n").split("\t", 2)
            assert pid not in reg, f"a registered job's read cannot be excluded: {pid}"
            excl.add((pid, path))
    bad = []
    for line in open(p, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        path = parts[-1]
        if (parts[1], path) in excl:
            continue
        base = os.path.basename(path)
        stem = re.sub(r"(_RX\d)?\.(bin|gt\.json|meta\.json|npz)$", "", base)
        if not IC.stem_allowed(stem) or any(r in path for r in RETIRED) or "DEMO" in path:
            bad.append(path)
    assert not bad, bad[:5]


def test_inventory_is_six_people_three_sessions_360_passes():
    inv = IC.pass_inventory()
    assert len(inv) == 360
    assert {r["participant"] for r in inv} == set(SIX)
    assert not any("DEMO" in r["stem"] for r in inv)


# ------------------------------------------------------------------ 2

def test_sealed_labels_cannot_be_read_as_an_array():
    s = IC.SealedLabels(np.array(["P1", "P2"]), "t")
    with pytest.raises(PermissionError):
        np.asarray(s)
    assert list(s.reveal(np.array(["P1", "P1"]))) == ["P1", "P2"]


def test_selection_never_reveals_test_labels(monkeypatch):
    from pipeline.identify import idmax_eval as E
    if not os.path.exists(os.path.join(ROOT, IC.FEAT, "steady_raw.npz")):
        pytest.skip("feature bank not built")
    M = E.meta()
    fold = [f for f in E.crossday_folds(M) if f.scope == "LOSO"][0]

    def boom(self, pred):
        raise AssertionError("reveal called during selection")
    monkeypatch.setattr(IC.SealedLabels, "reveal", boom)
    sel = E.select(fold, M["y"], M, [E.FConf("steady_raw", "B1_rhythm")], ["lda"], top_k=1)
    assert sel["model"] == "lda"


def test_selection_blanks_the_test_side_labels(monkeypatch):
    """Behavioural: corrupting the test-side labels must not change the selection."""
    from pipeline.identify import idmax_eval as E
    if not os.path.exists(os.path.join(ROOT, IC.FEAT, "steady_raw.npz")):
        pytest.skip("feature bank not built")
    M = E.meta()
    fold = [f for f in E.crossday_folds(M) if f.scope == "LOSO"][0]
    cands = [E.FConf("steady_raw", "B1_rhythm"), E.FConf("steady_raw", "B4_spectral")]
    a = E.select(fold, M["y"], M, cands, ["lda"], top_k=2)
    y2 = M["y"].copy()
    y2[fold.te] = "P1"
    b = E.select(fold, y2, M, cands, ["lda"], top_k=2)
    assert a["fconf"] == b["fconf"] and a["inner_acc"] == b["inner_acc"]


# ------------------------------------------------------------------ 3

def test_no_gait_set_can_select_speed_or_static_levels():
    from pipeline.identify import idmax_eval as E
    if not os.path.exists(os.path.join(ROOT, IC.FEAT, "steady_raw.npz")):
        pytest.skip("feature bank not built")
    V = E.load_variant("steady_raw")
    for fs in E.GAIT_SETS:
        for ch in E.CH:
            cols = E.columns(E.FConf("steady_raw", fs, ch))
            fams = set(V["fam"][cols])
            assert "S0" not in fams and "RECSIG" not in fams, (fs, ch, fams)


def test_feature_names_hold_no_speed_duration_or_anchor():
    from pipeline.identify import idmax_eval as E
    if not os.path.exists(os.path.join(ROOT, IC.FEAT, "steady_raw.npz")):
        pytest.skip("feature bank not built")
    for n in E.load_variant("steady_raw")["names"]:
        low = n.lower()
        assert not any(w in low for w in ("speed", "duration", "anchor", "dwell", "n_cycles",
                                          "n_steps")), n


def test_feature_code_never_touches_speed_or_anchors():
    for mod in ("pipeline/identify/idmax_features.py", "pipeline/identify/id19_featbank.py"):
        src = open(os.path.join(ROOT, mod), encoding="utf-8").read()
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
        body = re.sub(r'"""[\s\S]*?"""', "", code)
        for w in ("speed_m_s", "anchor_times", "duration_s", "walk_speed"):
            assert w not in body, (mod, w)


def test_features_do_not_depend_on_pass_length_by_count():
    """Behavioural: the same stationary signal cut at two lengths gives the same shape features."""
    from pipeline.identify import idmax_features as F
    t = np.arange(0, 8, 1 / F.FS)
    x = np.sin(2 * np.pi * 1.8 * t) + 0.3 * np.sin(2 * np.pi * 0.9 * t)
    a = F.cycle_templates(x[: int(4 * F.FS)], 1.8)
    b = F.cycle_templates(x, 1.8)
    ka = np.array([a[f"tpl_{i:02d}"] for i in range(F.PHASE)])
    kb = np.array([b[f"tpl_{i:02d}"] for i in range(F.PHASE)])
    assert np.corrcoef(ka, kb)[0, 1] > 0.99
    assert not any("n_" in k for k in list(a) + list(b))


# ------------------------------------------------------------------ 4

def test_no_pass_is_split_across_train_and_test_in_any_scope():
    from pipeline.identify import idmax_eval as E
    M = E.meta()
    keys = M["key"]
    assert len(set(keys)) == len(keys)
    for scope in ("pairings9", "WD_temporal", "WD_LOLO"):
        for f in E.scope_folds(M, M["y"], scope):
            assert not set(f.tr) & set(f.te), (scope, f.tag)
            for a, b in f.inner:
                assert set(a) <= set(f.tr) and set(b) <= set(f.tr) and not set(a) & set(b)
            if scope == "pairings9":
                assert not set(M["session"][f.tr]) & set(M["session"][f.te]), f.tag


# ------------------------------------------------------------------ 5

def _written_outside_runs() -> list:
    # 2026-09-24: the IDMAX queue, check-in log and closing report were combined verbatim into
    # reports/identification/history/record-identification-history.md, and figures_idmax moved to figures/identify/idmax.
    pats = ["reports/identification/history/record-identification-history.md", "reports/identification/dc2/2026-09-23b_identification-sheet.md",
            "reports/identification/history/findings-id19.txt", "reports/identification/history/findings-id2*.txt",
            "reports/identification/dc2/2026-09-28_findings-id29.txt", "reports/identification/figures/idmax/*"]
    out = []
    for p in pats:
        out += glob.glob(os.path.join(ROOT, p))
    return [p for p in out if os.path.isfile(p)]


def test_participant_names_never_leave_runs():
    bad = []
    for p in _written_outside_runs():
        if p.endswith((".png", ".pdf")):
            txt = open(p, "rb").read().decode("latin-1")
        else:
            txt = open(p, encoding="utf-8").read()
        for n in tuple(SIX) + tuple(RETIRED):
            if n in txt:
                bad.append((os.path.basename(p), n))
    assert not bad, bad


def test_the_idmax_report_section_holds_no_names():
    p = os.path.join(ROOT, "reports", "identification", "history", "2026-09-18_identification.md")
    txt = open(p, encoding="utf-8").read()
    i = txt.find("2026-09-23b, gait identification maximisation")
    if i < 0:
        pytest.skip("section not written yet")
    sec = txt[i:]
    assert not any(n in sec for n in tuple(SIX) + tuple(RETIRED))
