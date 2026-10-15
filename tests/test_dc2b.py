"""The dc2b corrections to the frozen DC2 pipeline (2026-09-24), tested on their behaviour.

Each fault is first REPRODUCED on the frozen code, so the test that the correction holds is not a
test of a fault that never existed; then the corrected path is shown to stop, or to split correctly.
`install()` changes modules process-wide, so it is exercised in a subprocess only.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import types

import pytest

import pipeline.constrained.dc2_pipeline as P
import pipeline.constrained.dc2_run as R
from pipeline.constrained import dc2b, dc2b_manifest

REPO = pathlib.Path(__file__).resolve().parents[1]


def _rec(stem, ids):
    return types.SimpleNamespace(stem=stem, session="B1",
                                 pass_spans=lambda: [(i, "A_fwd", 0, 1) for i in ids])


def _layout(tmp_path, room_b_sessions, room_a_sessions=("01", "02", "03")):
    for s in room_a_sessions:
        (tmp_path / "data" / "room_A" / f"session_{s}").mkdir(parents=True)
    for s in room_b_sessions:
        (tmp_path / "data" / "room_B" / f"session_{s}").mkdir(parents=True)
    return tmp_path


# ------------------------------------------------------------------ fault 1: Room A in Room B's place

def test_fault_1_reproduced_on_the_frozen_view(tmp_path, monkeypatch):
    """The frozen view links Room A's session_01 where Room B's session_01 should be, silently."""
    root = _layout(tmp_path, ["01"])
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    c = R.cfg_for("room_B", False)
    assert R.do_view(c) == 0
    link = os.readlink(os.path.join(c["data_view"], "room_B", "session_01"))
    assert link.endswith(os.path.join("room_A", "session_01"))


def test_fault_1_refused(tmp_path, monkeypatch):
    root = _layout(tmp_path, ["01"])
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    monkeypatch.setattr(dc2b, "REPO_ROOT", str(root))
    with pytest.raises(dc2b.Refused):
        dc2b.guard_cfg(R.cfg_for)("room_B", False)


def test_b1_b2_pass_and_view_points_at_room_b(tmp_path, monkeypatch):
    root = _layout(tmp_path, ["B1", "B2"])
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    monkeypatch.setattr(dc2b, "REPO_ROOT", str(root))
    c = dc2b.guard_cfg(R.cfg_for)("room_B", False)
    R.do_view(c)
    for b in ("B1", "B2"):
        assert os.readlink(os.path.join(c["data_view"], "room_B", f"session_{b}")).endswith(
            os.path.join("room_B", f"session_{b}"))


def test_room_a_is_refused_as_the_dc2_room(tmp_path):
    c = {"room": "room_A", "train": ("01", "02", "03"), "b_sessions": {}}
    assert dc2b.layout_problems(c, str(tmp_path))


# ------------------------------------------------------------------ fault 3: identification as tracking

def test_fault_3_idpath_in_a_tracking_session_refused(tmp_path):
    root = _layout(tmp_path, ["B1"])
    d = root / "data" / "room_B" / "session_B1"
    (d / "participant_PA5_idpath_d1_natural.gt.json").write_text("{}")
    c = {"room": "room_B", "train": ("01", "02", "03"), "b_sessions": {"B1": str(d)}}
    assert any("identification" in p for p in dc2b.layout_problems(c, str(root / "data" / "room_A")))


def test_identification_folder_is_not_a_tracking_session(tmp_path, monkeypatch):
    """data/room_B/identification/ holds _idpath_ files and is never taken as a Room B session."""
    root = _layout(tmp_path, ["B1"])
    idd = root / "data" / "room_B" / "identification" / "session_01"
    idd.mkdir(parents=True)
    (idd / "participant_PA5_idpath_d1_natural.gt.json").write_text("{}")
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    monkeypatch.setattr(dc2b, "REPO_ROOT", str(root))
    c = dc2b.guard_cfg(R.cfg_for)("room_B", False)
    assert sorted(c["b_sessions"]) == ["B1"]


# ------------------------------------------------------------------ fault 2: per-session pass ids

def test_fault_2_reproduced_on_the_frozen_split():
    """One session's ids reach every recording: passes 1 to 8 of a PARTICIPANT become calibration."""
    man = {"calibration_pass_ids": list(range(1, 9)), "aborted_pass_ids": []}
    sp = P.split_passes(_rec("participant_PA5_walk", range(1, 21)), man)
    assert sp["calibration"] == list(range(1, 9))


def test_split_by_recording():
    split = dc2b.by_recording(P.split_passes)
    man = {"calibration_recordings": ["participant_CAL_walk"],
           "aborted": {"participant_PA5_walk": [7]}}
    cal = split(_rec("participant_CAL_walk", range(1, 9)), man)
    assert cal["calibration"] == list(range(1, 9)) and cal["evaluated"] == []
    h = split(_rec("participant_PA5_walk", range(1, 21)), man)
    assert h["calibration"] == [] and h["aborted"] == [7]
    assert h["evaluated"] == [i for i in range(1, 21) if i != 7]
    z = split(_rec("participant_PA6_walk", range(1, 21)), man)
    assert z["evaluated"] == list(range(1, 21)) and z["aborted"] == []


def test_aborted_id_that_does_not_exist_is_refused():
    split = dc2b.by_recording(P.split_passes)
    with pytest.raises(dc2b.Refused):
        split(_rec("participant_PA5_walk", range(1, 21)),
              {"calibration_recordings": ["x"], "aborted": {"participant_PA5_walk": [27]}})


def test_the_stand_in_form_is_unchanged():
    split = dc2b.by_recording(P.split_passes)
    man = {"calibration_pass_ids": list(range(1, 9)), "aborted_pass_ids": []}
    r = _rec("participant_PA5_TEST_walk", range(1, 21))
    assert split(r, man) == P.split_passes(r, man)


def test_the_tripwire_stops_the_frozen_command():
    """The frozen split, handed the new manifest by mistake, fails loudly rather than scoring all passes."""
    with pytest.raises(ValueError):
        P.split_passes(_rec("participant_PA5_walk", range(1, 21)),
                       {"calibration_pass_ids": dc2b.TRIPWIRE, "calibration_recordings": ["x"]})


def _gt(d, stem, n):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.gt.json").write_text(json.dumps(
        {"passes": [{"pass_id": i, "path_name": "B_fwd"} for i in range(1, n + 1)]}))


def test_manifest_problems(tmp_path):
    d = tmp_path / "session_B1"
    _gt(d, "participant_CAL_walk", 8)
    _gt(d, "participant_PA5_walk", 20)
    ok = {"sessions": {"B1": {"calibration_recordings": ["participant_CAL_walk"], "aborted": {},
                              "calibration_pass_ids": dc2b.TRIPWIRE}}}
    assert dc2b.manifest_problems(ok, {"B1": str(d)}) == []
    per_session = {"sessions": {"B1": {"calibration_pass_ids": [1, 2, 3], "aborted_pass_ids": []}}}
    assert dc2b.manifest_problems(per_session, {"B1": str(d)})
    # a per-session list is refused EVEN beside a valid calibration recording: it is still ambiguous
    both = {"sessions": {"B1": {**ok["sessions"]["B1"], "calibration_pass_ids": [1, 2, 3]}}}
    assert any("per-SESSION" in p for p in dc2b.manifest_problems(both, {"B1": str(d)}))
    both_ab = {"sessions": {"B1": {**ok["sessions"]["B1"], "aborted_pass_ids": [4]}}}
    assert any("per-SESSION" in p for p in dc2b.manifest_problems(both_ab, {"B1": str(d)}))
    none = {"sessions": {"B1": {"calibration_recordings": [], "aborted": {}}}}
    assert dc2b.manifest_problems(none, {"B1": str(d)})
    typo = {"sessions": {"B1": {"calibration_recordings": ["participant_CAL_wlak"], "aborted": {}}}}
    assert dc2b.manifest_problems(typo, {"B1": str(d)})
    missing = {"sessions": {}}
    assert dc2b.manifest_problems(missing, {"B1": str(d)})
    stray_key = {"sessions": {**ok["sessions"], "b1": ok["sessions"]["B1"]}}
    assert dc2b.manifest_problems(stray_key, {"B1": str(d)})
    all_cal = {"sessions": {"B1": {"calibration_recordings": ["participant_CAL_walk",
                                                               "participant_PA5_walk"], "aborted": {}}}}
    assert dc2b.manifest_problems(all_cal, {"B1": str(d)})


def test_the_parent_stops_before_any_step_on_a_bad_manifest(tmp_path, monkeypatch):
    """check_real_manifest runs before dc2_pipeline.main: a missing or per-session manifest stops the run."""
    root = _layout(tmp_path, ["B1"])
    d = root / "data" / "room_B" / "session_B1"
    _gt(d, "participant_CAL_walk", 8)
    _gt(d, "participant_PA5_walk", 20)
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    monkeypatch.setattr(dc2b, "REPO_ROOT", str(root))
    monkeypatch.setattr(R, "cfg_for", dc2b.guard_cfg(R.cfg_for))
    with pytest.raises(dc2b.Refused):
        dc2b.check_real_manifest("room_B")                          # no manifest at all
    man = root / "data" / "room_B" / "calibration.json"
    man.write_text(json.dumps({"sessions": {"B1": {"calibration_pass_ids": list(range(1, 9)),
                                                    "aborted_pass_ids": []}}}))
    with pytest.raises(dc2b.Refused):
        dc2b.check_real_manifest("room_B")                          # the per-session form
    man.write_text(json.dumps({"sessions": {"B1": {"calibration_recordings": ["participant_CAL_walk"],
                                                    "aborted": {}, "calibration_pass_ids": dc2b.TRIPWIRE}}}))
    assert dc2b.check_real_manifest("room_B")["sessions"]["B1"]["calibration_recordings"]


def test_stand_in_override_refused_on_a_real_run(tmp_path, monkeypatch):
    root = _layout(tmp_path, ["B1"])
    monkeypatch.setattr(R, "REPO_ROOT", str(root))
    monkeypatch.setattr(dc2b, "REPO_ROOT", str(root))
    monkeypatch.setenv("TDR_DC2B_MANIFEST", "/elsewhere.json")
    with pytest.raises(dc2b.Refused):
        dc2b.guard_cfg(R.cfg_for)("room_B", False)


# ------------------------------------------------------------------ the manifest writer

def test_manifest_writer(tmp_path):
    d = tmp_path / "room_B" / "session_B1"
    _gt(d, "participant_CAL_walk", 8)
    _gt(d, "participant_PA5_walk", 20)
    root = str(tmp_path)
    assert dc2b_manifest.main(["--session", "B1", "--calibration", "participant_CAL_walk", "--data-root", root]) == 0
    assert dc2b_manifest.main(["--session", "B1", "--aborted", "participant_PA5_walk:7", "--data-root", root]) == 0
    man = json.loads((tmp_path / "room_B" / "calibration.json").read_text())
    s = man["sessions"]["B1"]
    assert s["calibration_recordings"] == ["participant_CAL_walk"]
    assert s["aborted"] == {"participant_PA5_walk": [7]}
    assert s["calibration_pass_ids"] == dc2b.TRIPWIRE and len(man["log"]) == 2
    assert dc2b.manifest_problems(man, {"B1": str(d)}) == []
    for bad in (["--session", "B1", "--calibration", "participant_CAL_wlak"],
                ["--session", "B1", "--aborted", "participant_PA5_walk:27"],
                ["--session", "B1", "--aborted", "participant_PA5_walk:seven"],
                ["--session", "01", "--calibration", "participant_CAL_walk"]):
        assert dc2b_manifest.main(bad + ["--data-root", root]) == 2


# ------------------------------------------------------------------ install, in its own process

def test_install_reaches_every_entry_point():
    code = (
        "import pipeline.constrained.dc2b_pipeline, pipeline.constrained.dc2b_scorerlock as SL\n"
        "import pipeline.constrained.dc2_run as R, pipeline.constrained.dc2_pipeline as P\n"
        "from pipeline.constrained import dc2b\n"
        "assert R._dc2b_installed and P._run_step is dc2b._run_step\n"
        "assert P.split_passes.__qualname__.startswith('by_recording')\n"
        "assert R.cfg_for.__qualname__.startswith('guard_cfg')\n"
        "import pipeline.constrained.dc2_scorerlock as S\n"
        "assert S.subprocess.call is SL._call\n"
        "print('ok')\n")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True,
                         env={**os.environ, "OMP_NUM_THREADS": "1"})
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr
