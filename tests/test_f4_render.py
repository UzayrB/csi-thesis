"""The demo re-render of 2026-09-24 (f4) and the donor swap (f5), held to what they claim.

f4 is a copy of the frozen f3_render. Its claims: it never writes the frozen demo folder; its display
phase is the one reports/tracking/history/2026-09-24_prereg-display-phase.md's rule picks, not a value typed in; and its
sweep draws the same dot the frozen videos draw. f5's claim is that its own-radio decisions are the
shipped ones, walk for walk, which is what makes its donor numbers about the shipped system.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
F4 = REPO / "pipeline" / "constrained" / "f4_render.py"
FH = REPO / "runs" / "constrained" / "fh"


def _json(p):
    if not p.exists():
        pytest.skip(f"{p.relative_to(REPO)} has not been produced")
    return json.loads(p.read_text(encoding="utf-8"))


def test_f4_writes_its_own_folder_and_moves_nothing():
    src = F4.read_text(encoding="utf-8")
    assert '"demo_v2"' in src
    assert 'os.path.join(REPO, "runs", "constrained", "demo")' not in src
    assert "shutil.move" not in src and "RETIRED" not in src
    assert "findings(" not in src and "headline(" not in src


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_f3_render_is_untouched():
#     """Unchanged since its pin. The 2026-10-01 restructure moved it to pipeline/retired/constrained/: the pin is
#     checked at the restructure's base commit, and the move may have changed only path lines (tests/_restructure.py)."""
#     from tests import _restructure as RS
#     pinned = {ln.split()[1]: ln.split()[0] for ln in (REPO / "reports" / "PINNED_FILES.txt")
#               .read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")}
#     p = "pipeline/constrained/f3_render.py"
#     assert RS.sha(RS.at_base(p)) == pinned[p]
#     assert not RS.non_mechanical_changes(p), RS.non_mechanical_changes(p)


def test_the_drawn_phase_is_the_preregistered_choice():
    sweep = _json(FH / "f4_phase_s0103_to_s02" / "results.json")
    target = float(sweep["target_ahead_pct"])
    rows = [(float(k), v["post"]["ahead_pct"]) for k, v in sweep["per_head_offset"].items()]
    best = min(abs(a - target) for _k, a in rows)
    # ties within 1.0 point go to the larger value, the smaller change
    chosen = max(k for k, a in rows if abs(a - target) <= best + 1.0)
    default = float(re.search(r'F4_HEAD_OFFSET_S", "([0-9.]+)"', F4.read_text(encoding="utf-8")).group(1))
    assert default == chosen, f"f4 draws {default}, the pre-registered rule picks {chosen}"


def _along(room, line, p):
    a = np.asarray(room[line], float)
    u = (a[-1] - a[0]) / np.hypot(*(a[-1] - a[0]))
    return float((np.asarray(p, float) - a[0]) @ u)


def test_the_sweep_draws_the_frozen_videos_dot_at_0_75():
    import os
    import sys
    sys.path.insert(0, str(REPO))
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        from pipeline.constrained import paths as P
        room = P.load_paths()
    finally:
        os.chdir(cwd)
    f3 = _json(FH / "f3_render" / "results.json")
    sweep = _json(FH / "f4_phase_s0102_to_s03" / "results.json")
    lead = []
    for R in f3["recordings"].values():
        for w in R["walks"]:
            if w["locked_line"] != w["true"] or w.get("mid_walk_switches"):
                continue
            lead += [_along(room, w["true"], r) - _along(room, w["true"], g)
                     for r, g in zip(w["rpost"], w["gpost"]) if r is not None and g is not None]
    s = sweep["per_head_offset"]["0.750"]["post"]
    assert s["n_frames"] == len(lead)
    assert abs(s["ahead_pct"] - 100.0 * float(np.mean(np.asarray(lead) > 0))) < 1e-6
    assert abs(s["signed_mean_m"] - float(np.mean(lead))) < 1e-6


def test_the_donor_swap_is_about_the_shipped_decisions():
    d = _json(FH / "f5_donor" / "results.json")
    rep = d["reproduction_own_vs_d4_rows_veto"]
    assert rep["n"] == 1080 and rep["equal"] == 1080 and d["VALID"]
