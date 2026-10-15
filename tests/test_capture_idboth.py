"""capture_idboth, the DC2 identification capture in both directions (2026-09-24). No hardware is touched."""

from __future__ import annotations

import json
import os

import pytest

from pipeline.identify import capture_idboth as C
from pipeline.identify import capture_idpath as F


def test_plan_in_cycles_keeps_the_preregistered_a_fwd_counts():
    """Addendum B trains on 10 day 1 natural A_fwd passes and tests on 5 per day 2 block: unchanged."""
    assert C.PLAN[(1, "natural")] == F.PLAN[(1, "natural")] == 10
    for b in ("natural", "slow", "fast"):
        assert C.PLAN[(2, b)] == F.PLAN[(2, b)] == 5
    assert C.PLAN[(1, "slow")] == C.PLAN[(1, "fast")] == 5          # added on day 1, 2026-09-24


def test_passes_alternate_away_then_back():
    plan = C.pass_plan(10)
    assert len(plan) == 20 and [p for p, _ in plan] == list(range(1, 21))
    assert all(d == ("A_fwd" if p % 2 else "A_rev") for p, d in plan)
    assert sum(d == "A_fwd" for _, d in plan) == 10


def test_both_paths_exist_and_run_opposite_ways():
    from pipeline.io.anchors import PATHS
    f, r = PATHS["A_fwd"], PATHS["A_rev"]
    assert f.anchors[0] == (2.5, 0.0) and f.anchors[-1] == (2.5, 5.0) and f.direction == "N"
    assert tuple(reversed(f.anchors)) == r.anchors


def test_block_order_both_days():
    for day in (1, 2):
        with pytest.raises(C.Refused):
            C.check_block_order("PA5", day, "slow", set())          # natural first
        C.check_block_order("PA5", day, "natural", set())
        C.check_block_order("PA5", day, "slow", {"natural"})       # P1, odd: slow first
        with pytest.raises(C.Refused):
            C.check_block_order("PA5", day, "fast", {"natural"})
        C.check_block_order("PA1", day, "fast", {"natural"})       # P2, even: fast first
        with pytest.raises(C.Refused):
            C.check_block_order("PA5", day, "natural", {"natural"})  # never overwritten


def test_folder_is_room_b_identification_never_a_tracking_session(tmp_path):
    d = C.out_dir(1, root=str(tmp_path))
    assert d == os.path.join(str(tmp_path), "room_B", "identification", "session_01")
    import glob
    os.makedirs(d)
    tracking = glob.glob(os.path.join(str(tmp_path), "room_B", "session_*"))
    assert tracking == []                    # the tracking pipeline's own pattern never sees it
    assert "room_A" not in d


def test_count_by_direction_and_status(tmp_path):
    gt = tmp_path / "x.gt.json"
    gt.write_text(json.dumps({"passes": [{"pass_id": i, "path_name": d} for i, d in C.pass_plan(5)]}))
    got = C.count_by_direction(str(gt))
    assert got == {"A_fwd": 5, "A_rev": 5}
    assert C.count_status(5, got, None)["status"] == "COMPLETE"
    short = {"A_fwd": 5, "A_rev": 4}
    assert C.count_status(5, short, None)["status"].startswith("REFUSED")
    assert C.count_status(5, short, "stumbled")["status"] == "COUNT_DIFFERS_REASON_LOGGED"


def test_spot_cannot_change_once_dc2_identification_files_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "SPOT_FILE", str(tmp_path / "rx2_spot.json"))
    C.set_spot("primary", root=str(tmp_path))
    d = C.out_dir(1, root=str(tmp_path))
    os.makedirs(d)
    open(os.path.join(d, "participant_PA5_idpath_d1_natural.gt.json"), "w").write("{}")
    with pytest.raises(C.Refused):
        C.set_spot("fallback", root=str(tmp_path))
    assert json.load(open(F.SPOT_FILE))["label"] == "primary"


def test_dry_run_prints_both_directions(capsys):
    assert C.main(["--participant", "PA5", "--day", "1", "--block", "natural", "--dry-run",
                   "--rehearsal"]) == 0
    out = capsys.readouterr().out
    assert "10 cycles = 20 passes" in out and "A_rev" in out


def test_unknown_participant_refused():
    assert C.main(["--participant", "Nobody", "--day", "1", "--block", "natural", "--dry-run",
                   "--rehearsal"]) == 2


def test_one_block_in_the_day_plan_order_through_the_cli(tmp_path, monkeypatch):
    """The day plan's order for P1 (PA5, odd: slow first): empty home, empty idspot, natural, slow,
    fast, on both days, through the real CLI; only the two hardware calls are replaced."""
    monkeypatch.setattr(F, "SPOT_FILE", str(tmp_path / "rx2_spot.json"))
    C.set_spot("primary", root=str(tmp_path))

    def fake_empty(a, st, d):
        os.makedirs(d, exist_ok=True)
        for L in ("RX1", "RX2", "RX3"):
            open(os.path.join(d, f"{st}_{L}.bin"), "wb").close()
        return 0.0, 30.0

    def fake_walk(a, code, st, d, cycles, rx):
        os.makedirs(d, exist_ok=True)
        gt = os.path.join(d, f"{st}.gt.json")
        json.dump({"passes": [{"pass_id": p, "path_name": n} for p, n in C.pass_plan(cycles)]}, open(gt, "w"))
        return gt, 0.0, 60.0

    monkeypatch.setattr(F, "_capture_empty", fake_empty)
    monkeypatch.setattr(C, "_capture_walk", fake_walk)
    base = ["--participant", "PA5", "--nodes", "RX1=a,RX2=b,RX3=c", "--data-root", str(tmp_path)]
    body = ["--height-cm", "170", "--weight-kg", "65", "--shoes", "s", "--clothing", "c", "--nothing-carried"]
    for day in (1, 2):
        d = ["--day", str(day)]
        assert C.main(base + d + ["--empty", "--position", "home", "--move-time", "09:00"]) == 0
        assert C.main(base + d + ["--block", "fast"] + body) == 2                  # pace before natural
        assert C.main(base + d + ["--empty", "--position", "idspot", "--move-time", "09:10"]) == 0
        assert C.main(base + d + ["--block", "natural"] + body) == 0
        assert C.main(base + d + ["--block", "fast"] + body) == 2                  # PA5: slow first
        assert C.main(base + d + ["--block", "slow"] + body) == 0
        assert C.main(base + d + ["--block", "fast"] + body) == 0
        assert C.main(base + d + ["--empty", "--position", "home", "--move-time", "09:30"]) == 2  # no overwrite
        out = C.out_dir(day, root=str(tmp_path))
        side = json.load(open(os.path.join(out, f"participant_PA5_idpath_d{day}_natural.idmax.json")))
        assert side["count"]["status"] == "COMPLETE"
        assert side["count"]["recorded"] == {"A_fwd": C.PLAN[(day, "natural")], "A_rev": C.PLAN[(day, "natural")]}
    assert not (tmp_path / "room_B" / "session_01").exists()                       # never a tracking folder
