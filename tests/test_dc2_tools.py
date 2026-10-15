"""The day checker and the post-run gate (2026-09-24), on synthetic files. Each fault the hardware check
found, or that the day could produce, must be caught; the clean case must pass."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from pipeline.constrained import dc2b, dc2b_manifest
from tests.test_id29_dc2_score import write_bin
# RETIRED 2026-10-01: tools/dc2_day_check.py was deleted with the DC2 tools (Uzayr; in git at 5c49f09). The
# verify-run tests below still need its board MACs and the geometry, copied here unchanged; its own tests are
# commented out where they stood.
# from tools import dc2_day_check as DC
import types as _types
DC = _types.SimpleNamespace(
    MACS={"RX1": "68:09:47:4c:ef:b4", "RX2": "20:50:0d:1a:28:74", "RX3": "20:50:0d:30:5f:80"},
    GEOMETRY={"RX1": [2.5, 5.5], "RX2": [-0.5, 2.5], "RX3": [5.5, 2.5]},
    TX=[2.5, -0.5])
from tools import dc2_verify_run as VR


def _bins(prefix, seconds, rng):
    t = np.arange(0, seconds, 1 / 150.0) + 1000.0
    for n in ("RX1", "RX2", "RX3"):
        write_bin(f"{prefix}{n}.bin", t, np.full((len(t), 128), 20.0), rng)


PASS = {n: {"pass": True, "drop_pct": 0.2, "sent_hz": 150.0} for n in ("RX1", "RX2", "RX3")}


def _tracking_day(root, cal_code="PA5_C", macs=None, baseline=True, people=("PA5",)):
    rng = np.random.default_rng(0)
    sess = root / "room_B" / "session_B1"
    sess.mkdir(parents=True)
    for code, n in [(cal_code, 8)] + [(p, 20) for p in people]:
        stem = f"participant_{code}_walk"
        bdir = sess / f"base_{code}"
        bdir.mkdir()
        _bins(str(bdir) + os.sep, 61.0, rng)
        _bins(str(sess / f"{stem}_"), 5.0, rng)
        (bdir / "run.json").write_text(json.dumps({"summary": PASS}))
        (sess / f"{stem}_run.json").write_text(json.dumps({"summary": PASS}))
        gt = {"passes": [{"pass_id": i, "path_name": "A_fwd", "t_start": 0.0, "t_end": 4.0} for i in range(1, n + 1)],
              "node_macs": macs or DC.MACS, "aborted": code == cal_code,
              "geometry": {"rx_positions_m": DC.GEOMETRY, "tx_position_m": DC.TX},
              "reaction_time": {"applied": "subtracted"}, "baseline_capture": (str(bdir) + "/") if baseline else None}
        (sess / f"{stem}.gt.json").write_text(json.dumps(gt))
    dc2b_manifest.main(["--session", "B1", "--calibration", f"participant_{cal_code}_walk", "--data-root", str(root)])
    return sess


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_clean(tmp_path):
#     _tracking_day(tmp_path)
#     bad, rows = DC.tracking(str(tmp_path), 1, False, ["PA5"])
#     assert bad == [] and {r["recording"] for r in rows} == {"participant_PA5_C_walk", "participant_PA5_walk"}


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_catches_a_calibration_recording_named_cal(tmp_path):
#     """The hardware check's finding: the pipeline never sees participant_CAL_walk."""
#     _tracking_day(tmp_path, cal_code="CAL")
#     bad, _ = DC.tracking(str(tmp_path), 1, False, ["PA5"])
#     assert any("not one of the six" in b for b in bad)


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_catches_a_missing_baseline(tmp_path):
#     _tracking_day(tmp_path, baseline=False)
#     bad, _ = DC.tracking(str(tmp_path), 1, False, ["PA5"])
#     assert any("names no baseline" in b for b in bad)


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_catches_the_wrong_board(tmp_path):
#     _tracking_day(tmp_path, macs={**DC.MACS, "RX2": "aa:bb:cc:dd:ee:ff"})
#     bad, _ = DC.tracking(str(tmp_path), 1, False, ["PA5"])
#     assert any("not the tracking boards" in b for b in bad)


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_final_wants_everyone(tmp_path):
#     _tracking_day(tmp_path)
#     bad, _ = DC.tracking(str(tmp_path), 1, True, ["PA5", "PA1"])
#     assert any("no tracking recording for PA1" in b for b in bad)


def _decode(base, rows, s_b=1.9, constants=True):
    base.mkdir(parents=True, exist_ok=True)
    d = {"calibration": {"per_session": {"B1": {"x": 1}} if constants else {}},
         "constants": {"B1": {"theta": 0.43}} if constants else {},
         "sessions": {"B1": {"s_B": s_b, "rows": {"A": rows, "B": rows}}}}
    (base / "decode.json").write_text(json.dumps(d))


def _rows(pairs):
    return [{"stem": s, "pass_id": i} for s, i in pairs]


def test_verify_run(tmp_path):
    root = tmp_path / "data"
    _tracking_day(root)
    dc2b_manifest.main(["--session", "B1", "--aborted", "participant_PA5_walk:2", "--data-root", str(root)])
    room_dir, base = str(root / "room_B"), tmp_path / "base"
    good = _rows([("participant_PA5_walk", i) for i in range(1, 21) if i != 2])
    _decode(base, good)
    assert VR.verify("room_B", room_dir, str(base), "", want_wrapper=False) == []
    _decode(base, good, s_b=None, constants=False)                            # the silent B == A
    assert any("NO CALIBRATION CONSTANTS" in b for b in VR.verify("room_B", room_dir, str(base), "", False))
    _decode(base, good + _rows([("participant_PA5_C_walk", 1)]))         # a calibration pass scored
    assert VR.verify("room_B", room_dir, str(base), "", False)
    _decode(base, good[:-1])                                                  # a pass lost
    assert VR.verify("room_B", room_dir, str(base), "", False)
    _decode(base, good + _rows([("participant_PA5_walk", 2)]))             # an aborted pass scored
    assert VR.verify("room_B", room_dir, str(base), "", False)


def test_verify_run_wants_the_dc2b_wrapper_on_room_b(tmp_path):
    root = tmp_path / "data"
    _tracking_day(root)
    base = tmp_path / "base"
    _decode(base, _rows([("participant_PA5_walk", i) for i in range(1, 21)]))
    res = tmp_path / "results.json"
    res.write_text(json.dumps({"run_through": None}))
    assert any("dc2b_pipeline" in b for b in VR.verify("room_B", str(root / "room_B"), str(base), str(res), True))
    res.write_text(json.dumps({"run_through": {"wrapper": "pipeline.constrained.dc2b_pipeline"}}))
    assert VR.verify("room_B", str(root / "room_B"), str(base), str(res), True) == []


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_day_check_reports_a_failed_gate(tmp_path):
#     sess = _tracking_day(tmp_path)
#     assert DC.tracking(str(tmp_path), 1, False, ["PA5"])[0] == []
#     failed = {**PASS, "RX2": {"pass": False, "drop_pct": 5.8, "sent_hz": 158.0}}
#     (sess / "participant_PA5_walk_run.json").write_text(json.dumps({"summary": failed}))
#     assert any("RX2 FAILED its gates" in b for b in DC.tracking(str(tmp_path), 1, False, ["PA5"])[0])
#     (sess / "participant_PA5_walk_run.json").write_text(json.dumps({"summary": PASS}))
#     (sess / "base_PA5" / "run.json").write_text(json.dumps({"summary": failed}))
#     assert any("names a failed baseline" in b for b in DC.tracking(str(tmp_path), 1, False, ["PA5"])[0])
