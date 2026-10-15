"""THE FIFTH RECEIVER (a fourth RX, identification only). Batch 2026-09-23e, item 6.

Tracking reads ONLY RX1, RX2 and RX3, BY NODE NAME, never by file order, and a fourth receiver's
capture is accepted without error. The decoys used below are copies of OTHER tracking nodes' radio
under the names RX0 (sorts before RX1) and RX4 (sorts after RX3), so a loader that took the first or
the last three files would read the wrong radio and change its answer; identical decisions are only
possible if the loader goes by name.

The end-to-end check is the DC2 stand-in re-run WITH the decoys present
(`dc2_pipeline --stand-in --decoy-receivers`): its decisions must equal the shipped system's.
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

from pipeline.constrained import nodes

REPO = pathlib.Path(__file__).resolve().parents[1]
S01 = REPO / "data" / "room_A" / "session_01"
STEM = "participant_PA5_walk"


@pytest.fixture(autouse=True)
def _no_env_leak():
    before = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(before)


def test_every_tracking_loader_names_the_same_three_nodes():
    from pipeline.constrained import recordings
    from pipeline.live import realtime_engine as engine
    from pipeline.io import windows
    assert nodes.TRACKING_NODES == ("RX1", "RX2", "RX3")
    assert tuple(recordings.NODES) == tuple(windows.NODES) == tuple(engine.NODES) == nodes.TRACKING_NODES


def test_no_tracking_loader_globs_capture_files():
    """File order can only enter through a glob over *.bin; no tracking loader may have one."""
    for rel in ("pipeline/constrained/recordings.py", "pipeline/io/windows.py",
                "pipeline/live/realtime_engine.py", "pipeline/live/realtime_replay.py",
                "pipeline/live/tracker_live.py", "pipeline/constrained/dc2_run.py",
                "pipeline/constrained/y4_pressalign.py", "pipeline/constrained/features.py"):
        src = (REPO / rel).read_text(encoding="utf-8")
        assert "*.bin" not in src and "_*.bin" not in src, f"{rel} globs capture files"


def _decoy_session(tmp_path):
    d = tmp_path / "session_01"
    d.mkdir()
    for f in S01.glob(f"{STEM}*"):
        os.symlink(f, d / f.name)
    os.symlink(S01 / f"{STEM}_RX3.bin", d / f"{STEM}_RX0.bin")
    os.symlink(S01 / f"{STEM}_RX2.bin", d / f"{STEM}_RX4.bin")
    return d


def test_the_cutter_reads_rx1_to_rx3_by_name_with_decoys_present(tmp_path, monkeypatch):
    if not (S01 / f"{STEM}_RX1.bin").exists():
        pytest.skip("Room A raw data absent")
    from pipeline.io import windows
    d = _decoy_session(tmp_path)
    assert windows.recordings_in(str(d)) == [STEM], "decoy files must not add or drop a recording"
    opened = []
    real = windows.load_node

    def spy(path):
        opened.append(os.path.basename(path))
        return real(path)

    class _Stop(Exception):
        pass

    def stop(*_a, **_k):
        raise _Stop                                   # every node loaded; nothing else is needed
    monkeypatch.setattr(windows, "load_node", spy)
    monkeypatch.setattr(windows, "clean_arrays", lambda *a, **k: None)
    monkeypatch.setattr(windows, "window_starts", stop)
    with pytest.raises(_Stop):
        windows.cut_recording(str(d), STEM, {n: None for n in windows.NODES})
    assert opened == [f"{STEM}_RX1.bin", f"{STEM}_RX2.bin", f"{STEM}_RX3.bin"], opened


def test_the_live_engine_decisions_are_identical_with_a_fourth_receiver_streaming():
    if not (S01 / f"{STEM}_RX1.bin").exists():
        pytest.skip("Room A raw data absent")
    from pipeline.live.realtime_engine import NODES, RealTimeEngine
    from pipeline.constrained.gate import presence_threshold
    from pipeline.io.windows import load_node, session_baseline
    from tools.calibrate_gate import band_energy, cut_baseline
    sc = json.loads((S01 / f"{STEM}.gt.json").read_text(encoding="utf-8"))
    bdir = sc["baseline_capture"].rstrip("/")
    streams = {}
    for n in NODES:
        amp, ts, _s, _e = load_node(str(S01 / f"{STEM}_{n}.bin"))
        streams[n] = (ts, amp)
    t0 = min(float(ts[0]) for ts, _a in streams.values())
    extra = {"RX4": streams["RX2"], "RX0": streams["RX3"]}      # decoys: other nodes' real radio

    def run(with_extra):
        eng = RealTimeEngine(baseline=session_baseline(bdir),
                             presence_theta=presence_threshold(band_energy(cut_baseline(bdir))))
        src = dict(streams, **(extra if with_extra else {}))
        merged = sorted((float(t), n, i) for n, (ts, _a) in src.items() for i, t in enumerate(ts)
                        if float(t) <= t0 + 25.0)
        for t, n, i in merged:
            eng.push(n, t + (1e-4 if n in extra else 0.0), src[n][1][i])
        return [(r.t_start, r.t_end, r.gate, round(r.band_energy, 9), r.cell, r.n_links)
                for r in eng.results]

    a, b = run(False), run(True)
    assert a and a == b, "a fourth receiver's packets changed the engine's windows or decisions"
    assert all(x[-1] == 3 for x in b), "the engine must report three tracking links"


def _raw_room(tmp_path, macs, files=("RX1", "RX2", "RX3", "RX4")):
    d = tmp_path / "room_B" / "session_B1"
    d.mkdir(parents=True)
    (d / "participant_X_walk.gt.json").write_text(json.dumps({"node_macs": macs}), encoding="utf-8")
    for n in files:
        (d / f"participant_X_walk_{n}.bin").write_bytes(b"")
    return str(tmp_path / "room_B")


def test_identity_check_accepts_an_extra_receiver_and_reports_it(tmp_path):
    A = nodes.room_a_macs(str(REPO / "data"))
    raw = _raw_room(tmp_path, dict(A, RX4="aa:bb:cc:dd:ee:ff"))
    out = nodes.identity_check(raw, A)
    assert not out["REFUSE"] and out["extra_receivers"] == ["RX4"]


def test_identity_check_refuses_a_tracking_board_under_another_name(tmp_path):
    """The autodiscovery mislabel: the ID board recorded as RX1, RX1's board recorded as RX4."""
    A = nodes.room_a_macs(str(REPO / "data"))
    raw = _raw_room(tmp_path, dict(A, RX1="aa:bb:cc:dd:ee:ff", RX4=A["RX1"]))
    out = nodes.identity_check(raw, A)
    assert out["REFUSE"] and out["swapped"] and out["mismatches"]


def test_identity_check_refuses_a_changed_board_unless_overridden(tmp_path):
    A = nodes.room_a_macs(str(REPO / "data"))
    raw = _raw_room(tmp_path, dict(A, RX2="11:22:33:44:55:66"), files=("RX1", "RX2", "RX3"))
    out = nodes.identity_check(raw, A)
    assert out["REFUSE"] and not out["swapped"] and "--node-macs-changed-ok" in out["reason"]


def test_decoys_are_a_stand_in_option_only(tmp_path):
    from pipeline.constrained.dc2_pipeline import main
    with pytest.raises(SystemExit) as e:
        main(["--room", "room_B", "--decoy-receivers", "--data", str(tmp_path)])
    assert "stand-in" in str(e.value)


def test_the_stand_in_with_decoy_receivers_equals_the_shipped_decisions():
    """THE END-TO-END FIFTH-RECEIVER TEST: the whole DC2 path, from raw files with RX0 and RX4 decoys
    beside every recording, reproduces the shipped system's decisions exactly."""
    p = REPO / "runs" / "constrained" / "fh" / "dc2_pipeline_standin_decoys" / "results.json"
    assert p.exists(), "run: python3 -m pipeline.constrained.dc2_pipeline --stand-in --decoy-receivers"
    R = json.loads(p.read_text(encoding="utf-8"))
    assert R["decoy_receivers"] is True
    assert R["steps"]["0_nodes"]["extra_receivers"] == ["RX0", "RX4"]
    eq = R["stand_in_equals_shipped"]
    assert eq and eq["EXACT"] and eq["n"] > 0, eq
