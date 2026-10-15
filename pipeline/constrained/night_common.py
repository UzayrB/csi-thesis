"""Shared machinery for the overnight semi-bounded batch, 2026-09-19.

THE OUTPUT CONTRACT is the reason this module exists. A stage is complete when its results satisfy
the keys and row counts it declares, not when its process exits zero. Exit codes have hidden two
crashes in this project already, once because a $(date) inside an echo reset $? before it was read.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np

NIGHT = os.path.join("runs", "constrained", "night")
STRIDE = 0.5
SEED = 0
N_BOOT = 1000
NOISE_M = 0.11
GUARD_END_MIN = 50.0        #: end-time substitution bar
BOUNDED_LINE_SUBS = 87.5    #: bounded's line substitution, the "same order" reference
CHANCE_PCT = 100.0 / 12.0
#: the shipped reference figures at 0.5 s, from TRACKING_FROZEN_2026-09-18f.json
SHIPPED = {"semibounded_line_pct": 46.666666666666664, "bounded_line_pct": 58.333333333333336,
           "bar_points": 10.0, "stretch_points": 5.0}


def stage_dir(name: str) -> str:
    p = os.path.join(NIGHT, name)
    os.makedirs(p, exist_ok=True)
    return p


def save(name: str, res: dict) -> str:
    p = os.path.join(stage_dir(name), "results.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    os.replace(tmp, p)          # atomic: a reader never sees half a results file
    return p


def load(name: str):
    p = os.path.join(NIGHT, name, "results.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_contract(res: dict, keys, rows: dict = None) -> dict:
    """The contract: required keys present and non-empty, and named collections at least n long."""
    missing = [k for k in keys if res.get(k) in (None, {}, [])]
    short = {}
    for k, n in (rows or {}).items():
        got = res.get(k)
        got_n = len(got) if hasattr(got, "__len__") else 0
        if got_n < n:
            short[k] = {"expected_at_least": n, "got": got_n}
    ok = not missing and not short
    return {"SATISFIED": bool(ok), "missing_keys": missing, "short_collections": short,
            "note": "a stage is complete when this is satisfied, never when its process exits zero"}


def claim(name: str):
    """One instance per stage. Refuses a second launch; reclaims a lock whose process is gone."""
    d = stage_dir(name)
    lock = os.path.join(d, ".running")
    if os.path.exists(lock):
        try:
            old = int(open(lock, encoding="utf-8").read().split()[0])
        except (ValueError, OSError, IndexError):
            old = 0
        if old and old != os.getpid():
            try:
                os.kill(old, 0)
            except (ProcessLookupError, PermissionError):
                pass
            else:
                raise RuntimeError(f"{name} already running as pid {old}")
    with open(lock, "w", encoding="utf-8") as f:
        f.write(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    return lock


def release(lock: str) -> None:
    try:
        os.remove(lock)
    except OSError:
        pass


def boot_ci(v, n_boot=N_BOOT, seed=SEED):
    """Cluster bootstrap over passes. Keyed by the caller on stem|pass_id."""
    v = np.asarray([x for x in v if x is not None], float)
    if not len(v):
        return None, None, None
    rng = np.random.default_rng(seed)
    bs = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def boot_paired(a_rows, b_rows, field="found_final"):
    """Paired difference on SESSION|STEM|PASS_ID, the standing pairing key since 2026-09-20.

    pass_id restarts at 1 in every recording, so a dict keyed on it alone silently compares
    different recordings; and recording STEMS repeat across sessions, so stem|pass_id is unique
    inside one session and not across three. Both forms have cost this project a wrong interval.
    A dict spanning several PAIRINGS needs the pairing tag on top of this key, because three
    pairings can test the same session.
    """
    a = {r["key"]: r for r in a_rows}
    b = {r["key"]: r for r in b_rows}
    assert len(a) == len(a_rows) and len(b) == len(b_rows), (
        "pass keys are not unique; the standing key is session|stem|pass_id and a dict spanning "
        "pairings needs the tag as well")
    keys = sorted(set(a) & set(b))
    d = [100.0 * (float(b[k][field]) - float(a[k][field])) for k in keys]
    return boot_ci(d) + (len(keys),)


def tree_manifest(root: str):
    """Files and bytes under a tree, for the untouched-shipped-trees assertion."""
    if not os.path.isdir(root):
        return None
    n = size = 0
    for r, _d, files in os.walk(root):
        for f in files:
            n += 1
            size += os.path.getsize(os.path.join(r, f))
    return {"n_files": n, "bytes": size}


def guard_verdict(end_subs, line_subs) -> dict:
    """THE GUARD IS A GATE, applied before any line figure is allowed to count."""
    end_ok = end_subs is not None and end_subs > GUARD_END_MIN
    line_ok = line_subs is not None and line_subs >= 0.5 * BOUNDED_LINE_SUBS
    return {"PASSES": bool(end_ok and line_ok), "end_substitution_pct": end_subs,
            "line_substitution_pct": line_subs, "end_bar_pct": GUARD_END_MIN,
            "line_reference_pct": BOUNDED_LINE_SUBS,
            "why": ("an arm whose end-time substitution is at or below the bar, or whose line "
                    "substitution is not of the same order as bounded's, is OUT whatever its "
                    "line figure")}


# ---------------------------------------------------------------- the shared decode layer
# Loading posteriors and building emissions is the expensive part, so it is done once per pairing
# and reused across every arm. The 0.5 s roots must be set BEFORE any pipeline import; each stage
# does that at its own module top, exactly as the stride arms did.

def set_half_roots(repo_root: str) -> None:
    """Point the roots at the shipped 0.5 s tree. Call BEFORE importing pipeline modules.

    The shipped tree is the ONE LATTICE of `pipeline/constrained/lattice.py`, press-aligned since
    2026-09-23d. `repo_root` is kept for the callers' signature; the lattice knows its own root.
    """
    from pipeline.constrained import lattice
    os.environ.setdefault("TDR_WINDOWS_ROOT", lattice.windows_root())
    os.environ.setdefault("TDR_ART_DIR", lattice.half_art_dir())


def shipped_pieces():
    """The frozen decoder configuration every arm starts from.

    IT ALSO RE-DERIVES THE MOTION MODEL IN SECONDS, which is not optional and is easy to forget.
    decoder.DT defaults to 1.0; at a 0.5 s stride the chain must advance 0.649 m per window rather
    than 1.298. Without this line the decoder believes the walker moves at twice their pace and the
    demonstration pairing scores 30.8 percent instead of 71.7, which is how this was caught.
    """
    import pipeline.constrained.decoder as D
    from pipeline.constrained import paths as P
    from pipeline.constrained.common import RUN_DIR, read_json
    from pipeline.constrained.rb3_display import shipped_config
    from pipeline.constrained.rebuild_common import emission_choice, load_results
    st = P.states()
    kind, alpha, _s = emission_choice()
    cfg, ne, _sel = shipped_config(load_results("rb2_decoder"), "s0102_to_s03")
    transit = read_json(os.path.join(RUN_DIR, "rb0_preflight", "transit_geometry.json"), {}) or {}
    D.DT = STRIDE
    return st, cfg, ne, transit, kind, alpha


def assert_motion_model():
    """Fail loudly if the motion model is not at this batch's stride."""
    import pipeline.constrained.decoder as D
    assert abs(D.DT - STRIDE) < 1e-9, (
        f"the motion model is at DT={D.DT}, not the batch's {STRIDE} s stride; the decoder would "
        f"advance {D.V_MEAN * D.DT:.3f} m per window instead of {D.V_MEAN * STRIDE:.3f}")
    return {"DT": D.DT, "step_m_per_window": float(D.V_MEAN * D.DT),
            "sd_m_per_window": float(D.V_SD * D.DT)}


def pairing_emissions(tag, tr_s, te_s, within, st, kind, alpha, art_dir=None, fusion_w=0.0):
    """[(stem, rec, gate_energy, emission)] for one pairing, or None if its posteriors are absent."""
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.common import E_POST
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    from pipeline.constrained.recordings import gate_energy, load_meta
    pp = posterior_path(tag, 25, E_POST, SEED)
    if art_dir is not None:
        pp = os.path.join(art_dir, "posteriors", os.path.basename(pp))
    if not os.path.exists(pp):
        return None
    marg = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
            if kind == "scaled" else None)
    out = []
    for stem, b in sorted(read_full_posteriors(pp).items()):
        from pipeline.constrained.fusion import fused_prob
        prob = fused_prob(b, fusion_w).astype(float)
        e = (cell_emission(prob, st.xy, 25) if marg is None
             else scaled_cell_emission(prob, st.xy, 25, marg, alpha=alpha))
        out.append((stem, load_meta(te_s[0], stem), gate_energy(te_s[0], stem), e))
    return out


#: the shipped guard-passing arm: all_alive plus rescore_end. max_speed and time_lockout measured
#: INERT in the stride batch and are carried at their defaults, doing nothing.
SHIPPED_FLAGS = {"pinned_entry": False, "max_speed": False, "time_lockout": False,
                 "all_alive": True, "rescore_end": True}


def semibounded_rows(src, st, cfg, ne, transit, flags=None, subs=True):
    """Per-pass rows for one pairing under the shipped decoder. subs runs the substitution test."""
    from pipeline.constrained.sb2_structural import track2
    flags = dict(SHIPPED_FLAGS if flags is None else flags)
    rows, n = [], len(src)
    for k, (_stem, rec, ge, e) in enumerate(src):
        alt = src[(k + 1) % n][3] if (subs and n > 1) else None
        rows += track2(e, rec, st, cfg, transit, ne, ge, STRIDE, flags, 2.0, 2.2, alt)
    return rows
