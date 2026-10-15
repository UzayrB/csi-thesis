"""The lock must have finished recording by the frame it is drawn on. ON THE ONE LATTICE.

HISTORY. Until 2026-09-23d this was a STRICT expected failure on the grid lattice, where it failed
on 360 of 360 passes. Operator instruction 4, item 2, adopted the press-aligned lattice as the ONE
lattice; the property now holds on every pass and the marker was REMOVED DELIBERATELY, as its own
docstring said it must be. The grid lattice's failure is kept as a second test, so the fault the
fix removed stays documented by a measurement rather than by prose.

Original statement follows.

`reports/tracking/history/2026-09-23_finding-lock-phase.md`. V3 as amended on 2026-09-23 draws the lock at exactly
press + 2.0 s (`f3_render`: `park_until = t_press_start + LATENCY`), but the lock reads window
`lo + 2`, and on the shipped lattice that window ends after the lock frame on 360 of 360 passes.

This test asserts the property the render SHOULD have: on every pass, window `lo + 2` has finished
recording by press + 2.0 s. It is marked xfail(strict=True) because the shipped tree does not have
it. **When the fault is fixed the test passes, strict turns that into a failure, and the marker
must be removed deliberately**, so a fix cannot land silently and the guard then stays.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO))
from pipeline.constrained import lattice as _lattice                                # noqa: E402

TREE = REPO / _lattice.windows_root() / "room_A"
GRID_TREE = REPO / "runs" / "constrained" / "windows_half" / "room_A"
LOCK_FRAME_S = 2.0      # LATENCY in f3_render, V1/V3
WINDOW_S = 2.0
LOCK_STEP_W = 2         # round(2.0 / 0.5) - lag_w 2, at display lead-in 0


def _late_passes(tree=None):
    tree = TREE if tree is None else tree
    late, n = [], 0
    for mp in sorted(glob.glob(str(tree / "session_*" / "*.meta.json"))):
        stem = os.path.basename(mp)[:-len(".meta.json")]
        if "_DEMO_" in stem:
            continue
        session = mp.split("session_")[1][:2]
        sc = REPO / "data" / "room_A" / f"session_{session}" / f"{stem}.gt.json"
        if not sc.exists():
            continue
        press = {int(p["pass_id"]): float(p["t_start"])
                 for p in json.loads(sc.read_text())["passes"]}
        wins = json.loads(Path(mp).read_text())["windows"]
        first = {}
        for i, w in enumerate(wins):
            if w.get("mode") == "walk" and w.get("pass_id") is not None:
                first.setdefault(int(w["pass_id"]), i)
        for pid, lo in first.items():
            if pid not in press or lo + LOCK_STEP_W >= len(wins):
                continue
            n += 1
            end = float(wins[lo + LOCK_STEP_W]["t_start_abs"]) + WINDOW_S
            if end > press[pid] + LOCK_FRAME_S + 1e-5:
                late.append((stem, pid, round(end - press[pid] - LOCK_FRAME_S, 3)))
    return late, n


@pytest.mark.skipif(not TREE.exists(), reason="shipped window tree absent")
def test_the_lock_has_finished_recording_by_its_frame():
    """ON THE ONE LATTICE: every pass's lock window has ended by press + 2.0 s."""
    assert _lattice.LATTICE == _lattice.SHIPPED == "pressalign", \
        "the lock-phase property is asserted on the SHIPPED lattice"
    late, n = _late_passes()
    assert n >= 300, f"only {n} passes found; the census itself is broken"
    assert not late, f"{len(late)} of {n} locks drawn before their last window ended: {late[:3]}"


@pytest.mark.skipif(not GRID_TREE.exists(), reason="grid tree absent")
def test_the_retired_grid_lattice_still_shows_the_fault_it_had():
    """The fault the fix removed, measured and kept: the grid lattice is late on every pass."""
    late, n = _late_passes(GRID_TREE)
    assert n >= 300 and len(late) == n, (len(late), n)
