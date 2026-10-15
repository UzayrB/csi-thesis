"""Tests for the post-hoc capture inspector.

The inspector judges what landed on disk. Its cross-node checks assume the
files it compares heard the same transmission, so it must first group a
directory's files into runs. A session directory holds several
participants side by side, and comparing one participant's RX1 against
another's RX3 produced "started very late" and "packet ids do not overlap"
on every end-of-day check of 9 Sept 2026. It must also notice a participant
run whose ground truth was never written: two such runs were captured that
morning before anyone did.

No hardware required: capture files are synthesised in the on-disk format.
"""

from __future__ import annotations

import json
import os

import numpy as np

from pipeline.io.capture_logger import FILE_MAGIC, FRAME_DTYPE
from pipeline.io.inspect_capture import ground_truth_status, group_runs, inspect_run


def write_capture(path: str, node: str, t0: float, pkt0: int, n: int = 600, seed: int = 0) -> None:
    """Write a synthetic but valid capture file: real CSI-looking payloads."""
    rng = np.random.default_rng(seed)
    fr = np.zeros(n, dtype=FRAME_DTYPE)
    fr["t_mono"] = t0 + np.arange(n) / 150.0
    fr["t_host"] = fr["t_mono"]
    fr["pkt_id"] = pkt0 + np.arange(n)
    fr["local_timestamp"] = (np.arange(n) * 6667).astype(np.uint64)
    fr["rssi"] = -75
    fr["noise_floor"] = -96
    fr["gain"] = 1.0
    fr["data"] = rng.integers(-40, 40, size=(n, 256)).astype(np.int8)
    header = json.dumps({"node_id": node}).encode()
    with open(path, "wb") as f:
        f.write(FILE_MAGIC)
        f.write(np.uint32(len(header)).tobytes())
        f.write(header)
        f.write(fr.tobytes())


def write_gt(path: str, passes: int = 20, cells: int = 25, aborted: bool = False, mode_order: str = "walk_half, grid, walk_half") -> None:
    doc = {
        "mode_order": mode_order,
        "n_passes": passes,
        "n_cells": cells,
        "passes": [{"flagged": False} for _ in range(passes)],
        "cells": [{} for _ in range(cells)],
        "aborted": aborted,
    }
    with open(path, "w") as f:
        json.dump(doc, f)


def participant(d, code, t0, pkt0, gt=True, **gt_kw):
    for i, node in enumerate(("RX1", "RX2", "RX3")):
        write_capture(str(d / f"participant_{code}_walk_{node}.bin"), node, t0 + 0.1 * i, pkt0 + 5 * i, seed=i)
    if gt:
        write_gt(str(d / f"participant_{code}_walk.gt.json"), **gt_kw)


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------


def test_plain_capture_is_one_run_with_an_empty_stem() -> None:
    g = group_runs(["x/RX1.bin", "x/RX2.bin", "x/RX3.bin"])
    assert list(g) == [""] and len(g[""]) == 3


def test_session_files_group_by_participant() -> None:
    g = group_runs([
        "s/participant_Zaid_walk_RX1.bin", "s/participant_Zaid_walk_RX2.bin",
        "s/participant_Azrah_walk_RX1.bin", "s/participant_Azrah_walk_RX3.bin",
    ])
    assert set(g) == {"participant_Zaid_walk", "participant_Azrah_walk"}
    assert len(g["participant_Zaid_walk"]) == 2


def test_a_file_that_is_not_a_node_capture_is_its_own_run() -> None:
    g = group_runs(["x/RX1.bin", "x/oddball.bin"])
    assert set(g) == {"", "oddball"}


# --------------------------------------------------------------------------
# A session directory with several participants
# --------------------------------------------------------------------------


def test_two_participants_half_an_hour_apart_is_not_a_failure(tmp_path, capsys) -> None:
    """The false alarm of 9 Sept: the two runs are judged separately."""
    participant(tmp_path, "Zaid", t0=1000.0, pkt0=100_000)
    participant(tmp_path, "Azrah", t0=1000.0 + 1844.0, pkt0=400_000)   # no id overlap, 30 min later
    rc = inspect_run(str(tmp_path))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "started very late" not in out
    assert "do not overlap" not in out
    assert "2 runs" in out
    assert "CAPTURE LOOKS OK" in out


def test_nodes_within_one_run_are_still_cross_checked(tmp_path, capsys) -> None:
    """Scoping to a run must not switch the cross-node checks off."""
    write_capture(str(tmp_path / "participant_P01_walk_RX1.bin"), "RX1", 1000.0, 100_000)
    write_capture(str(tmp_path / "participant_P01_walk_RX2.bin"), "RX2", 1000.0 + 60.0, 900_000)  # late, different counter
    write_gt(str(tmp_path / "participant_P01_walk.gt.json"))
    rc = inspect_run(str(tmp_path))
    out = capsys.readouterr().out
    assert rc == 1
    assert "started very late" in out or "do not overlap" in out


def test_plain_run_directory_still_works(tmp_path, capsys) -> None:
    """A timestamped RX1/RX2/RX3 directory is one run with an empty stem."""
    for i, node in enumerate(("RX1", "RX2", "RX3")):
        write_capture(str(tmp_path / f"{node}.bin"), node, 500.0 + 0.1 * i, 7_000 + i, seed=i)
    rc = inspect_run(str(tmp_path))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "1 run" in out
    assert "ground truth" not in out, "a plain capture carries no ground truth and must not be asked for one"


# --------------------------------------------------------------------------
# The ground-truth sidecar
# --------------------------------------------------------------------------


def test_participant_run_without_ground_truth_fails(tmp_path, capsys) -> None:
    """CSI with no labels is unusable; this is the failure that must be loud."""
    participant(tmp_path, "Zaid", t0=1000.0, pkt0=100_000, gt=False)
    rc = inspect_run(str(tmp_path))
    out = capsys.readouterr().out
    assert rc == 1
    assert "NO .gt.json" in out
    assert "CAPTURE LOOKS WRONG" in out


def test_complete_ground_truth_is_reported(tmp_path, capsys) -> None:
    participant(tmp_path, "Zaid", t0=1000.0, pkt0=100_000)
    assert inspect_run(str(tmp_path)) == 0
    assert "20/20 passes, 25/25 cells, 0 flagged" in capsys.readouterr().out


def test_aborted_session_fails(tmp_path, capsys) -> None:
    participant(tmp_path, "Zaid", t0=1000.0, pkt0=100_000, passes=3, cells=0, aborted=True)
    assert inspect_run(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "ABORTED" in out and "aborted before it finished" in out


def test_incomplete_session_fails(tmp_path, capsys) -> None:
    participant(tmp_path, "Zaid", t0=1000.0, pkt0=100_000, passes=20, cells=17)
    assert inspect_run(str(tmp_path)) == 1
    assert "incomplete" in capsys.readouterr().out


def test_expected_counts_follow_the_mode(tmp_path) -> None:
    write_gt(str(tmp_path / "participant_P01_grid.gt.json"), passes=0, cells=25, mode_order="grid_only")
    line, problem = ground_truth_status(str(tmp_path), "participant_P01_grid")
    assert problem is None and "0/0 passes, 25/25 cells" in line


def test_demo_recording_needs_no_labels(tmp_path) -> None:
    with open(tmp_path / "participant_P01_DEMO_free.gt.json", "w") as f:
        json.dump({"mode": "demo", "position_labels": None}, f)
    line, problem = ground_truth_status(str(tmp_path), "participant_P01_DEMO_free")
    assert problem is None and "demonstration" in line


def test_non_participant_run_is_not_asked_for_ground_truth(tmp_path) -> None:
    assert ground_truth_status(str(tmp_path), "") == (None, None)
