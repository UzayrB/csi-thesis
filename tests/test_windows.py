"""Windows are cut on one lattice, per recording, and carry the metadata a result needs.

Synthetic captures in the on-disk format stand in for the data. No hardware.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from pipeline.io.windows import (
    FS,
    STRIDE_S,
    WINDOW_S,
    WindowMeta,
    cut_recording,
    label_window,
    pass_speed,
    recordings_in,
    session_baseline,
    window_starts,
    write_recording,
)
from tests.test_inspect_capture import write_capture

T0 = 1000.0


def _sidecar(cells=(), passes=(), participant="Zaid", session="01", mode=None):
    doc = {"participant_code": participant, "session_id": session, "room": "A",
           "participant": {"clothing": "black", "footwear": "boots", "height_cm": 176.0, "weight_kg": 74.0},
           "cells": list(cells), "passes": list(passes), "baseline_capture": ""}
    if mode:
        doc["mode"] = mode
    return doc


def _cell(index, t_start, cell="(3,3)", xy=(2.5, 2.5), cup="RED"):
    return {"cell_index": index, "cell_id": cell, "cell_centre_xy": list(xy), "facing_cup": cup, "facing": "N",
            "t_start": t_start, "t_end": t_start + 7.0, "flagged": False}


def _pass(pid, t0, speed=1.0):
    times = [t0 + i / speed for i in range(6)]
    coords = [[2.5, float(i)] for i in range(6)]
    return {"pass_id": pid, "path_name": "A_fwd", "anchor_times": times, "anchor_coords": coords,
            "t_start": times[0], "t_end": times[-1], "flagged": False}


def make_recording(tmp_path, n=3000, offsets=(0.0, 0.0031, 0.0062), sidecar=None, hole_at=None):
    """Three receiver files at 150 Hz plus a baseline directory and a sidecar."""
    d = tmp_path / "room_A" / "session_01"
    b = d / "20260911-090000"
    b.mkdir(parents=True)
    for i, node in enumerate(("RX1", "RX2", "RX3")):
        write_capture(str(b / f"{node}.bin"), node, T0 - 100.0, 1, n=1500, seed=10 + i)
        p = str(d / f"participant_Zaid_walk_{node}.bin")
        write_capture(p, node, T0 + offsets[i], 100_000, n=n, seed=i)
        if hole_at is not None:
            from pipeline.io.capture_logger import FILE_MAGIC, FRAME_DTYPE
            from pipeline.io.capture_logger import read_capture_file
            _, fr = read_capture_file(p)
            keep = ~((fr["t_mono"] > T0 + hole_at) & (fr["t_mono"] < T0 + hole_at + 0.6))
            fr = fr[keep]
            header = json.dumps({"node_id": node}).encode()
            with open(p, "wb") as f:
                f.write(FILE_MAGIC); f.write(np.uint32(len(header)).tobytes()); f.write(header); f.write(fr.tobytes())
    doc = sidecar or _sidecar()
    doc["baseline_capture"] = str(b)
    (d / "participant_Zaid_walk.gt.json").write_text(json.dumps(doc))
    return str(d), "participant_Zaid_walk", str(b)


# --------------------------------------------------------------------------
# Lattice and shape
# --------------------------------------------------------------------------


def test_windows_are_cut_on_the_shared_lattice_across_links(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path)
    X, metas, summary = cut_recording(d, stem, session_baseline(b))
    assert X.shape[1:] == (3, 300, 107) and X.shape[0] == len(metas) == summary["n_windows"]
    starts = np.array([m.t_start_abs for m in metas])
    assert np.allclose(starts / STRIDE_S, np.round(starts / STRIDE_S)), "starts are multiples of the stride, in absolute time"
    assert np.allclose(np.diff(starts), STRIDE_S)
    # about 20 s of data: 19 windows of 2 s at a 1 s stride, less lattice trimming
    assert 16 <= len(metas) <= 19


def test_a_window_is_the_same_instant_on_every_link(tmp_path) -> None:
    """Receivers start 3 ms apart; the window still begins on the lattice on all three."""
    d, stem, b = make_recording(tmp_path, offsets=(0.0, 0.0031, 0.0062))
    _, metas, summary = cut_recording(d, stem, session_baseline(b))
    for span in summary["grid_span_s"].values():
        assert abs(span[0] * FS - round(span[0] * FS)) < 1e-6, "every link's grid lies on the absolute lattice"


def test_overlap_never_crosses_the_recording(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path)
    _, metas, summary = cut_recording(d, stem, session_baseline(b))
    lo = max(s[0] for s in summary["grid_span_s"].values()); hi = min(s[1] for s in summary["grid_span_s"].values())
    assert metas[0].t_start_abs >= lo and metas[-1].t_start_abs + WINDOW_S <= hi + 1e-6


def test_window_starts_handles_no_overlap() -> None:
    from pipeline.io.clean import CleanedNode
    a = CleanedNode(np.zeros((10, 1)), np.arange(10) / FS, np.zeros(10), 0)
    b = CleanedNode(np.zeros((10, 1)), 100 + np.arange(10) / FS, np.zeros(10), 0)
    assert window_starts({"RX1": a, "RX2": b}, WINDOW_S, STRIDE_S, FS).size == 0


# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------


def _meta(t):
    return WindowMeta(participant="P", session_id="01", room="A", file_id="f", rx_files={}, index=0,
                      t_start_abs=t, t_start_epoch=t, mode="idle")


def test_a_window_inside_a_dwell_is_labelled_by_dwell_not_cell() -> None:
    sc = _sidecar(cells=[_cell(7, 100.0, cell="(2,4)", xy=(1.5, 3.5), cup="BLUE")])
    m = _meta(102.0); label_window(m, 102.0, 104.0, sc)
    assert m.mode == "grid" and m.dwell_id == 7 and m.cell_id == "(2,4)" and m.xy == [1.5, 3.5] and m.facing == "BLUE"
    edge = _meta(106.0); label_window(edge, 106.0, 108.0, sc)          # straddles the dwell's end
    assert edge.mode != "grid" and edge.dwell_id is None


def test_a_window_in_a_pass_gets_interpolated_position_and_speed() -> None:
    sc = _sidecar(passes=[_pass(3, 200.0, speed=1.25)])
    m = _meta(200.4); label_window(m, 200.4, 202.4, sc)                 # midpoint 201.4 s = 1.75 m along
    assert m.mode == "walk" and m.pass_id == 3 and m.path_name == "A_fwd"
    assert m.xy == [2.5, 1.75] and m.walk_speed == pytest.approx(1.25)


def test_no_extrapolation_before_the_first_or_after_the_last_anchor() -> None:
    sc = _sidecar(passes=[_pass(1, 200.0, speed=1.0)])                  # anchors 200 .. 205
    before = _meta(198.0); label_window(before, 198.0, 200.0, sc)       # midpoint 199: run-in
    assert before.mode == "walk_edge" and before.pass_id == 1 and before.xy is None and before.walk_speed == pytest.approx(1.0)
    after = _meta(205.5); label_window(after, 205.5, 207.5, sc)         # midpoint 206.5: run-out
    assert after.mode == "walk_edge" and after.xy is None
    far = _meta(240.0); label_window(far, 240.0, 242.0, sc)
    assert far.mode == "idle" and far.pass_id is None


def test_pass_speed_is_path_length_over_anchor_time() -> None:
    p = _pass(1, 0.0, speed=1.0); assert pass_speed(p) == pytest.approx(1.0)
    p["anchor_times"] = [0, 1, 2, 3, 4, 10]; assert pass_speed(p) == pytest.approx(0.5)


def test_sidecar_covariates_and_provenance_are_carried(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path, sidecar=_sidecar(cells=[_cell(0, T0 + 2.0)]))
    _, metas, _ = cut_recording(d, stem, session_baseline(b))
    m = metas[0]
    assert m.clothing == "black" and m.footwear == "boots" and m.height_cm == 176.0 and m.weight_kg == 74.0
    assert m.file_id == stem and set(m.rx_files) == {"RX1", "RX2", "RX3"} and m.rx_files["RX2"].endswith("_RX2.bin")
    assert m.t_start_epoch == pytest.approx(m.t_start_abs, abs=1e-3), "synthetic host clock equals monotonic"
    grid = [m for m in metas if m.mode == "grid"]
    assert grid and all(m.dwell_id == 0 and m.cell_id == "(3,3)" for m in grid) and len(grid) == 6


# --------------------------------------------------------------------------
# Packet gaps and the demo
# --------------------------------------------------------------------------


def test_a_long_gap_flags_exactly_the_windows_that_cover_it(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path, hole_at=8.0)                  # 0.6 s hole at T0 + 8.0 on every link
    _, metas, summary = cut_recording(d, stem, session_baseline(b))
    flagged = [m for m in metas if m.gap_flag]
    assert flagged and summary["gap_flagged"] == len(flagged)
    for m in flagged:
        assert m.t_start_abs <= T0 + 8.6 + 1e-6 and m.t_start_abs + WINDOW_S >= T0 + 8.0 - 1e-6
        assert m.max_packet_gap > 0.25 and set(m.max_packet_gap_per_rx) == {"RX1", "RX2", "RX3"}
    assert all(m.max_packet_gap < 0.05 for m in metas if not m.gap_flag)


def test_the_demo_is_never_windowed(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path, sidecar=_sidecar(mode="demo"))
    with pytest.raises(ValueError):
        cut_recording(d, stem, session_baseline(b))
    os.rename(os.path.join(d, f"{stem}.gt.json"), os.path.join(d, "participant_Zaid_DEMO_free.gt.json"))
    assert recordings_in(d) == []


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------


def test_written_windows_round_trip(tmp_path) -> None:
    d, stem, b = make_recording(tmp_path, sidecar=_sidecar(cells=[_cell(2, T0 + 2.0)], passes=[_pass(1, T0 + 12.0)]))
    X, metas, summary = cut_recording(d, stem, session_baseline(b))
    npz, meta_path = write_recording(X, metas, summary, str(tmp_path / "w"), stem)
    z = np.load(npz)
    doc = json.loads(open(meta_path).read())
    assert z["X"].shape == X.shape and z["X"].dtype == X.dtype
    assert len(doc["windows"]) == len(metas) and doc["summary"]["n_windows"] == len(metas)
    assert list(z["dwell_id"]) == [-1 if m.dwell_id is None else m.dwell_id for m in metas]
    assert all(w["gate"] is None for w in doc["windows"]), "gate labels are Stage 3"
