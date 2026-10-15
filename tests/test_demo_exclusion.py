"""Tests that the demonstration recording can never be trained or tested on.

The demo is CSI with no ground truth, recorded to show the live system
running. It is excluded by filename at three points: enumeration, split
construction, and dataset assembly. These tests hold all three in place, and
check the capture side names and describes the file correctly at the moment
it is created.

No hardware required.
"""

from __future__ import annotations

import json

import pytest

from pipeline.io.ground_truth import (
    DEMO_REASON,
    DEMO_SCRIPT,
    DemoClock,
    KeyEvent,
    SessionConfig,
    main,
    session_paths,
    write_demo_sidecar,
)
# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# from pipeline.retired.splits.assemble import assemble_dataset, assert_usable
# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# from pipeline.retired.splits.split_by_file import (
#     DEMO_INFIX,
#     FileMeta,
#     Split,
#     index_files,
#     is_demo_path,
#     reject_demo,
#     split_by_unit,
# )


def _session_dir(tmp_path, room="A", session="03"):
    d = tmp_path / f"room_{room}" / f"session_{session}"
    d.mkdir(parents=True)
    return d


def _write_participant(d, code, mode="walk", nodes=(1, 2, 3), infix=""):
    (d / f"participant_{code}_{infix}{mode}.gt.json").write_text(
        json.dumps({"room": "A", "session_id": d.name.split("_")[1], "participant_code": code})
    )
    for n in nodes:
        (d / f"participant_{code}_{infix}{mode}_RX{n}.bin").write_bytes(b"x")


# --------------------------------------------------------------------------
# Naming at capture time
# --------------------------------------------------------------------------


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_demo_produces_the_demo_infix() -> None:
#     """--demo names the file with _DEMO_ at capture time."""
#     _, stem = session_paths("data", "A", "03", "P01", "free", demo=True)
#     assert stem == "participant_P01_DEMO_free"
#     assert is_demo_path(stem + "_RX1.bin")
#     assert DEMO_INFIX in stem + "_RX1.bin"


def test_demo_and_test_infixes_are_mutually_exclusive() -> None:
    """A recording cannot be both excluded from every split and in the test split."""
    with pytest.raises(ValueError):
        session_paths("data", "A", "03", "P01", "free", test=True, demo=True)


def test_demo_is_free_walk_only() -> None:
    """The demo carries no labels, so it cannot be a grid or walk capture."""
    for mode in ("grid", "walk"):
        with pytest.raises(ValueError):
            session_paths("data", "A", "03", "P01", mode, demo=True)


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_ordinary_captures_never_carry_the_demo_infix() -> None:
#     """Only --demo can produce it."""
#     for mode in ("grid", "walk"):
#         for test in (False, True):
#             _, stem = session_paths("data", "A", "03", "P01", mode, test=test)
#             assert not is_demo_path(stem + "_RX1.bin")


# --------------------------------------------------------------------------
# The sidecar
# --------------------------------------------------------------------------


def _demo_config(filmed: bool = False) -> SessionConfig:
    return SessionConfig(participant_code="P01", room="A", session_id="03", demo=True, filmed=filmed)


def test_demo_sidecar_has_no_position_records_and_reads_demo(tmp_path) -> None:
    """mode is 'demo', position_labels is null, passes and cells are empty."""
    path = write_demo_sidecar(_demo_config(), {"RX1": "aa:bb"}, str(tmp_path), "participant_P01_DEMO_free", 0.0, 150.0)
    doc = json.loads(open(path).read())
    assert doc["mode"] == "demo"
    assert doc["position_labels"] is None
    assert doc["passes"] == [] and doc["cells"] == []
    assert doc["n_passes"] == 0 and doc["n_cells"] == 0
    assert doc["reason"] == DEMO_REASON
    assert "excluded from all training and evaluation" in doc["reason"]
    assert doc["test_session"] is False
    assert "anchor_times" not in json.dumps(doc)


def test_filmed_flag_is_recorded_and_defaults_to_false(tmp_path) -> None:
    """--filmed sets the boolean; omitting it records false, never null."""
    p_off = write_demo_sidecar(_demo_config(False), {}, str(tmp_path / "a"), "s", 0.0, 1.0)
    p_on = write_demo_sidecar(_demo_config(True), {}, str(tmp_path / "b"), "s", 0.0, 1.0)
    assert json.loads(open(p_off).read())["filmed"] is False
    assert json.loads(open(p_on).read())["filmed"] is True


def test_demo_sidecar_refuses_a_non_demo_config(tmp_path) -> None:
    """The demo writer cannot be used to produce an unlabelled ordinary capture."""
    with pytest.raises(ValueError):
        write_demo_sidecar(SessionConfig(participant_code="P01", room="A", session_id="03"), {}, str(tmp_path), "s", 0.0, 1.0)


# --------------------------------------------------------------------------
# Exclusion at enumeration
# --------------------------------------------------------------------------


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_demo_file_is_absent_from_every_split(tmp_path) -> None:
#     """A _DEMO_ file in a session directory reaches no side, including test."""
#     for sid, code in (("01", "P01"), ("02", "P02"), ("03", "P03"), ("04", "P04")):
#         d = _session_dir(tmp_path, session=sid)
#         _write_participant(d, code)
#     demo_dir = tmp_path / "room_A" / "session_03"
#     _write_participant(demo_dir, "P03", mode="free", infix="DEMO_")
#
#     files = index_files(str(tmp_path))
#     assert files, "ordinary files must still be indexed"
#     assert not any(is_demo_path(f.path) for f in files)
#
#     split = split_by_unit(files, "session", (0.75, 0.25, 0.0), seed=1)
#     for side in (split.train, split.val, split.test):
#         assert not any(is_demo_path(f.path) for f in side)
#     assert sum(len(x) for x in (split.train, split.val, split.test)) == 12


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_demo_rejected_even_when_only_file_present(tmp_path) -> None:
#     """A directory holding only a demo yields an empty index, not a demo."""
#     d = _session_dir(tmp_path)
#     _write_participant(d, "P03", mode="free", infix="DEMO_")
#     assert index_files(str(tmp_path)) == []


# --------------------------------------------------------------------------
# Exclusion at split construction and assembly
# --------------------------------------------------------------------------


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def _meta(path: str) -> FileMeta:
#     return FileMeta(path=path, session_id="03", room="A", subject_id="P03", node_id="RX1")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_split_by_unit_refuses_a_hand_built_list_with_a_demo() -> None:
#     """Rejected at construction, not filtered afterwards."""
#     files = [_meta("data/room_A/session_03/participant_P03_walk_RX1.bin"),
#              _meta("data/room_A/session_03/participant_P03_DEMO_free_RX1.bin")]
#     with pytest.raises(ValueError) as exc:
#         split_by_unit(files, "session", (1.0, 0.0, 0.0), seed=1)
#     assert DEMO_INFIX in str(exc.value)


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_assembly_raises_if_a_demo_file_is_passed_explicitly() -> None:
#     """The exclusion holds even for a split written by hand."""
#     demo = _meta("data/room_A/session_03/participant_P03_DEMO_free_RX1.bin")
#     ok = _meta("data/room_A/session_01/participant_P01_walk_RX1.bin")
#     for side in ("train", "val", "test"):
#         kwargs = {"train": [ok], "val": [], "test": [], "unit": "session"}
#         kwargs[side] = [demo] if side != "train" else [ok, demo]
#         with pytest.raises(ValueError) as exc:
#             assemble_dataset(Split(**kwargs))
#         assert "demonstration" in str(exc.value)


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_assert_usable_accepts_paths_and_metas() -> None:
#     """The guard works on raw strings too, for callers that skip FileMeta."""
#     assert_usable(["data/room_A/session_01/participant_P01_walk_RX1.bin"])
#     with pytest.raises(ValueError):
#         assert_usable(["data/room_A/session_03/participant_P03_DEMO_free_RX1.bin"])
#     with pytest.raises(ValueError):
#         reject_demo([_meta("x/participant_P03_DEMO_free_RX2.bin")])


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_assembly_passes_a_clean_split_through() -> None:
#     """A split with no demo file assembles unchanged."""
#     ok = _meta("data/room_A/session_01/participant_P01_walk_RX1.bin")
#     m = assemble_dataset(Split(train=[ok], val=[], test=[], unit="session"))
#     assert len(m) == 1 and m.unit == "session"


# --------------------------------------------------------------------------
# The CLI gates
# --------------------------------------------------------------------------


def test_cli_refuses_demo_with_test() -> None:
    """--demo and --test on one command is refused before anything runs."""
    rc = main(["--participant", "P01", "--room", "A", "--session", "03", "--demo", "--test", "--dry-run"])
    assert rc == 2


def test_cli_refuses_demo_outside_session_03_without_force() -> None:
    """The demo belongs to the held-out session."""
    assert main(["--participant", "P01", "--room", "A", "--session", "01", "--demo", "--dry-run"]) == 2
    assert main(["--participant", "P01", "--room", "A", "--session", "01", "--demo", "--force", "--dry-run"]) == 0
    assert main(["--participant", "P01", "--room", "A", "--session", "03", "--demo", "--dry-run"]) == 0


def test_cli_demo_dry_run_needs_no_calibration_or_geometry() -> None:
    """The demo starts no anchor logger, so the reaction-time file is not required."""
    assert main(["--participant", "P01", "--room", "A", "--session", "03", "--demo", "--dry-run"]) == 0


# --------------------------------------------------------------------------
# Spacebar in / out markers (added 10 September 2026)
# --------------------------------------------------------------------------


def _clock(enabled: bool = True):
    import queue
    q: "queue.Queue[KeyEvent]" = queue.Queue()
    return DemoClock(q, enabled=enabled, ceiling_s=600.0), q


def test_two_spaces_mark_in_and_out_and_finish(capsys) -> None:
    clock, q = _clock()
    clock.tick(0.0)
    assert not clock.finished and clock.markers() is None
    q.put(KeyEvent(" ", 10.0, 1_000_010.0))
    clock.tick(10.0)
    assert clock.start is not None and not clock.finished
    q.put(KeyEvent("x", 11.0, 1_000_011.0))        # any other key is ignored
    q.put(KeyEvent(" ", 72.5, 1_000_072.5))
    clock.tick(72.5)
    assert clock.finished
    m = clock.markers()
    assert m["in_mono"] == 10.0 and m["out_mono"] == 72.5 and m["in_grid_s"] == 62.5
    assert m["in_epoch"] == 1_000_010.0 and m["out_epoch"] == 1_000_072.5
    out = capsys.readouterr().out
    assert "IN " in out and "OUT " in out


def test_a_third_space_changes_nothing() -> None:
    clock, q = _clock()
    for t in (1.0, 2.0, 3.0):
        q.put(KeyEvent(" ", t, t))
    clock.tick(3.0)
    assert clock.markers()["out_mono"] == 2.0 and clock.finished


def test_without_a_terminal_the_ceiling_ends_it(capsys) -> None:
    clock, _ = _clock(enabled=False)
    clock.tick(0.0)
    assert "ceiling" in capsys.readouterr().out and not clock.finished


def test_demo_sidecar_carries_markers_and_script_but_no_positions(tmp_path) -> None:
    clock, q = _clock()
    q.put(KeyEvent(" ", 5.0, 5.0))
    q.put(KeyEvent(" ", 65.0, 65.0))
    clock.tick(65.0)
    path = write_demo_sidecar(_demo_config(True), {"RX1": "aa"}, str(tmp_path), "participant_P01_DEMO_free",
                              0.0, 70.0, markers=clock.markers(), script=DEMO_SCRIPT, ended_by="spacebar")
    doc = json.loads(open(path).read())
    assert doc["markers"]["in_grid_s"] == 60.0 and doc["ended_by"] == "spacebar"
    assert doc["script"] == list(DEMO_SCRIPT) and len(doc["script"]) == 8
    assert doc["position_labels"] is None and doc["passes"] == [] and doc["cells"] == []
    assert "anchor_times" not in json.dumps(doc)


def test_demo_script_is_the_same_for_everyone() -> None:
    """One script, so two demos differ only in who is walking."""
    assert isinstance(DEMO_SCRIPT, tuple) and all(isinstance(s, str) for s in DEMO_SCRIPT)
    assert "(1,1)" in " ".join(DEMO_SCRIPT) and "(5,5)" in " ".join(DEMO_SCRIPT)


# --------------------------------------------------------------------------
# The overwrite guard (added 11 September 2026, after a session was lost)
# --------------------------------------------------------------------------


def test_an_existing_recording_is_refused_without_redo(tmp_path, capsys) -> None:
    from pipeline.io.ground_truth import existing_recording, refuse_overwrite
    d = tmp_path / "room_A" / "session_03"
    d.mkdir(parents=True)
    assert existing_recording(str(d), "participant_P01_TEST_walk") == [] and not refuse_overwrite(str(d), "participant_P01_TEST_walk", False)
    for n in (1, 2, 3):
        (d / f"participant_P01_TEST_walk_RX{n}.bin").write_bytes(b"x")
    (d / "participant_P01_TEST_walk.gt.json").write_text("{}")
    assert len(existing_recording(str(d), "participant_P01_TEST_walk")) == 4
    assert refuse_overwrite(str(d), "participant_P01_TEST_walk", False)
    assert "REFUSING TO START" in capsys.readouterr().out
    assert not refuse_overwrite(str(d), "participant_P01_TEST_walk", True), "--redo is the deliberate path"
    assert existing_recording(str(d), "participant_P02_TEST_walk") == [], "another participant is untouched"
    assert existing_recording(str(d), "participant_P01_DEMO_free") == [], "the demo has its own name"


def test_the_cli_refuses_a_second_run_under_the_same_name(tmp_path, capsys) -> None:
    from pipeline.io.ground_truth import main
    d = tmp_path / "room_A" / "session_03"
    d.mkdir(parents=True)
    (d / "participant_P01_TEST_walk_RX1.bin").write_bytes(b"x")
    rc = main(["--participant", "P01", "--room", "A", "--session", "03", "--test", "--mode", "walk",
               "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5", "--height-cm", "178", "--weight-kg", "72",
               "--nodes", "RX1=/dev/fake0", "--no-images", "--data-root", str(tmp_path)])
    assert rc == 2 and "REFUSING TO START" in capsys.readouterr().out
    (d / "participant_P01_DEMO_free_RX1.bin").write_bytes(b"x")
    rc = main(["--participant", "P01", "--room", "A", "--session", "03", "--demo", "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5",
               "--nodes", "RX1=/dev/fake0", "--data-root", str(tmp_path)])
    assert rc == 2 and "REFUSING TO START" in capsys.readouterr().out
