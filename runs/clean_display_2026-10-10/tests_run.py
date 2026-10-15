"""Dry tests of run.py's gate 6 check (PLAN_NOTE_2), on synthetic logs with known exact frames. No decode.

    python3 -m pytest -q runs/clean_display_2026-10-10/tests_run.py

A synthetic seventh look (K1g anchor dots) and a synthetic new log (K1gf anchor dots) are built from one frame grid, one
entry and a seam per frame; every other row is shared. The check must pass them, and must fail: a moved row outside the
anchor span (condition 1, with condition 2 then not evaluated), an anchor dot off the formula, a first anchor frame off
the entry, a changed computed_at, and a later anchor frame with f_K1g = 0 (guard 2).
"""

from __future__ import annotations

import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run as R  # noqa: E402

STEM = "participant_X_TEST_walk"
SETT = {"anchor": "glide_first", "path_lag_extra": 1, "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 0.75,
        "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5},
        "shipped_display": "DISP_END"}


def build(origin=1000.0123456789, press_i=30, seams=((1.0, 0.2), (1.1, 0.25), (1.2, 0.3)), park_on_grid=False):
    from pipeline.live import display as LD
    grid = LD.frame_times(origin, 400)
    press = float(grid[press_i]) - 0.0371
    park_until = press + 2.0
    if park_on_grid:
        park_until = float(grid[press_i + 21])                 # a later anchor frame lands exactly on park_until
        press = park_until - 2.0
    t_dec0 = park_until + 0.25
    entry = [0.0, 0.0]
    anch = [float(x) for x in grid if park_until <= x < t_dec0]
    assert len(anch) >= 2
    base = [{"kind": "press", "pid": 1, "t": press}]
    base += [{"kind": "dot", "pid": 1, "x": round(float(x), 4), "xy": [2.5, 2.5], "computed_at": float(x) + 0.1}
             for x in grid if press <= x < park_until]
    old, new = list(base), list(base)
    for k, x in enumerate(anch):
        S = seams[min(k, len(seams) - 1)]
        f_old = (x - park_until) / (t_dec0 - park_until)
        f_new = (x - anch[0]) / (t_dec0 - anch[0])
        row = {"kind": "dot", "pid": 1, "x": round(x, 4), "computed_at": x + 0.12}
        old.append(dict(row, xy=[entry[0] + (S[0] - entry[0]) * f_old, entry[1] + (S[1] - entry[1]) * f_old]))
        new.append(dict(row, xy=[entry[0] + (S[0] - entry[0]) * f_new, entry[1] + (S[1] - entry[1]) * f_new]))
    lock = {"kind": "lock", "pid": 1, "line": "A_fwd", "at": park_until - 0.1, "line_entry": entry, "t_dec0": t_dec0,
            "park_until": park_until}
    tail = [{"kind": "dot", "pid": 1, "x": round(float(x), 4), "xy": [1.5, 0.3], "computed_at": float(x) + 0.1}
            for x in grid if t_dec0 <= x < t_dec0 + 1.0]
    tail += [{"kind": "committed", "pid": 1, "line": "A_fwd", "at": t_dec0 + 3.0}, {"kind": "margin", "pid": 1,
                                                                                 "min_margin_s": 0.3}]
    old, new = [old[0], lock] + old[1:] + tail, [new[0], lock] + new[1:] + tail
    facts = {"origin": origin, "n_frames_grid": 400, "display_profile": "clean", "display_candidate": "K1gf",
             "cfg_disp_sd_scale": 3.0, "end_head": "pooled (no display head)", "sett": SETT}
    return old, new, facts


def check(tmp_path, old, new, facts):
    R.HERE, R.REPLAY, R.SEVENTH = str(tmp_path / "here"), str(tmp_path / "replay"), str(tmp_path / "seventh")
    for d, rows in ((os.path.join(R.REPLAY, "final", R.NEW_MODE), new), (R.SEVENTH, old)):
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"03__{STEM}.jsonl"), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    os.makedirs(os.path.join(R.HERE, "facts", "final"), exist_ok=True)
    with open(os.path.join(R.HERE, "facts", "final", f"03__{STEM}.json"), "w", encoding="utf-8") as f:
        json.dump(facts, f)
    return R.anchor_check(STEM)


def anchor_rows(rows, lock):
    return [i for i, r in enumerate(rows) if r["kind"] == "dot" and lock["park_until"] - 1e-3 <= r["x"] < lock["t_dec0"]]


def test_a_true_k1gf_log_passes(tmp_path):
    old, new, facts = build()
    r = check(tmp_path, old, new, facts)
    assert r["condition1"]["PASS"] and r["condition2"]["PASS"], r
    assert r["condition2"]["max_deviation_m"] <= 1e-12
    w = r["condition2"]["anchor_frames_per_walk"]["1"]
    assert w["checked"] == w["anchor_frames"] >= 2


def test_condition1_failure_stops_before_condition2(tmp_path):
    old, new, facts = build()
    new = copy.deepcopy(new)
    new[-3]["xy"] = [1.5, 0.30000001]                     # a decoded dot after t_dec0
    r = check(tmp_path, old, new, facts)
    assert not r["condition1"]["PASS"] and r["condition2"]["PASS"] is None


@pytest.mark.parametrize("fault", ["off_formula", "first_off_entry", "computed_at", "profile"])
def test_condition2_failures(tmp_path, fault):
    old, new, facts = build()
    new, facts = copy.deepcopy(new), copy.deepcopy(facts)
    idx = anchor_rows(new, new[1])
    if fault == "off_formula":
        new[idx[-1]]["xy"][0] += 1e-6
    elif fault == "first_off_entry":
        new[idx[0]]["xy"] = [1e-12, 0.0]
    elif fault == "computed_at":
        new[idx[1]]["computed_at"] += 1e-9
    else:
        facts["sett"] = dict(SETT, shift_w=0.5)
    r = check(tmp_path, old, new, facts)
    assert r["condition1"]["PASS"] and not r["condition2"]["PASS"], (fault, r)


def test_guard2(tmp_path):
    # f_K1g = 0 can only happen on the FIRST anchor frame (anchor frames are at or after park_until, in order); there the
    # check needs no seam (bit-exact at the entry), so a first anchor frame exactly on park_until passes
    old, new, facts = build(park_on_grid=True)
    r = check(tmp_path, old, new, facts)
    assert r["condition1"]["PASS"] and r["condition2"]["PASS"], r
    # a seam that cannot be recovered on a later anchor frame is a FAIL, not a skip
    old2 = copy.deepcopy(old)
    old2[anchor_rows(old2, old2[1])[-1]]["xy"] = [float("nan"), 0.0]
    r2 = check(tmp_path, old2, new, facts)
    assert r2["condition1"]["PASS"] and not r2["condition2"]["PASS"]
    assert any("guard 2" in f_["why"] for f_ in r2["condition2"]["first"])
