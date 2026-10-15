"""The streaming engine: same cleaning, one window at a time, and the filed timing contract."""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.live.realtime_engine import (
    MAX_LATENCY_S,
    MAX_OUTPUT_GAP_S,
    NODES,
    STRIDE_S,
    WINDOW_S,
    NullPredictor,
    RealTimeEngine,
)

FS = 150.0
N_SUB = 128


def _baseline() -> dict:
    return {n: np.ones(107, dtype=np.float32) for n in NODES}


def _engine(**kw) -> RealTimeEngine:
    return RealTimeEngine(baseline=_baseline(), presence_theta=0.02, fs=FS, **kw)


def _packet(rng, amp: float = 40.0) -> np.ndarray:
    return np.full(N_SUB, amp, dtype=np.float32) + rng.normal(0, 0.5, N_SUB).astype(np.float32)


#: A SHAPE tilt across subcarriers, not a level change: per-packet normalisation
#: divides each LTF half by its own mean, so a modulation applied equally to every
#: subcarrier is removed by design and would simulate nothing.
_TILT = np.linspace(-1.0, 1.0, N_SUB, dtype=np.float32)


def _feed(engine: RealTimeEngine, seconds: float, t0: float = 1000.0, seed: int = 0, motion_hz: float = 0.0, motion_amp: float = 0.0):
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    out = []
    for i in range(n):
        t = t0 + i / FS
        for node in NODES:
            a = _packet(rng)
            if motion_amp:
                a = a * (1.0 + motion_amp * _TILT * np.sin(2 * np.pi * motion_hz * (t - t0)))
            out += engine.push(node, t, a)
    return out


# --------------------------------------------------------------------------
# Construction: the baseline is required, with no default
# --------------------------------------------------------------------------


def test_the_engine_cannot_be_built_without_this_sessions_baseline() -> None:
    with pytest.raises(ValueError):
        RealTimeEngine(baseline={}, presence_theta=0.02)
    with pytest.raises(ValueError):
        RealTimeEngine(baseline={"RX1": np.ones(107)}, presence_theta=0.02)      # only one node
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            RealTimeEngine(baseline=_baseline(), presence_theta=bad)
    import inspect
    sig = inspect.signature(RealTimeEngine.__init__)
    assert sig.parameters["baseline"].default is inspect.Parameter.empty
    assert sig.parameters["presence_theta"].default is inspect.Parameter.empty


# --------------------------------------------------------------------------
# Windows: the lattice, the stride, and waiting for every link
# --------------------------------------------------------------------------


def test_windows_land_on_the_absolute_lattice_at_one_stride_apart() -> None:
    eng = _engine()
    out = _feed(eng, 5.0)
    assert len(out) >= 5
    starts = np.array([r.t_start for r in out])
    assert np.allclose(starts / STRIDE_S, np.round(starts / STRIDE_S)), "starts are multiples of the stride in absolute time"
    assert np.allclose(np.diff(starts), STRIDE_S)
    assert all(abs((r.t_end - r.t_start) - WINDOW_S) < 1e-9 for r in out)


def test_nothing_is_emitted_until_every_link_covers_the_window() -> None:
    eng = _engine()
    rng = np.random.default_rng(1)
    for i in range(int(3.0 * FS)):                      # two links only
        t = 1000.0 + i / FS
        for node in ("RX1", "RX2"):
            eng.push(node, t, _packet(rng))
    assert eng.results == [], "a window needs all three receivers"
    for i in range(int(3.0 * FS)):
        t = 1000.0 + i / FS
        eng.push("RX3", t, _packet(rng))
    assert eng.results, "once the third link arrives the windows complete"
    assert all(r.n_links == 3 for r in eng.results)


def test_an_unknown_node_is_ignored_rather_than_crashing() -> None:
    eng = _engine()
    assert eng.push("RX9", 1000.0, np.zeros(N_SUB, np.float32)) == []


# --------------------------------------------------------------------------
# The gate labels and never routes
# --------------------------------------------------------------------------


def test_every_branch_runs_whatever_the_gate_says() -> None:
    seen = []

    class Counting(NullPredictor):
        def identify(self, w):
            seen.append(("id", w.shape)); return "X", 0.5

        def locate(self, w):
            seen.append(("pos", w.shape)); return "(1,1)", (0.5, 0.5)

    eng = _engine(predictor=Counting())
    out = _feed(eng, 4.0)
    assert out and {r.gate for r in out} <= {"empty", "standing", "walking"}
    assert len(seen) == 2 * len(out), "identity and position run on every window, gate label notwithstanding"
    assert all(s[1] == (3, int(WINDOW_S * FS), 107) for s in seen)
    assert all(r.identity == "X" and r.cell == "(1,1)" for r in out)


def test_a_level_only_modulation_is_invisible_by_design() -> None:
    """Per-packet normalisation removes a change applied equally to every subcarrier.

    This is the AGC-removal property the whole pipeline rests on, asserted
    here so the streaming path cannot quietly reintroduce absolute level.
    """
    rng = np.random.default_rng(5)
    eng_flat, eng_scaled = _engine(), _engine()
    for i in range(int(4.0 * FS)):
        t = 1000.0 + i / FS
        a = _packet(rng)
        for node in NODES:
            eng_flat.push(node, t, a)
            eng_scaled.push(node, t, a * (1.0 + 0.5 * np.sin(2 * np.pi * 1.0 * (t - 1000.0))))
    assert eng_flat.results and len(eng_flat.results) == len(eng_scaled.results)
    for a, b in zip(eng_flat.results, eng_scaled.results):
        # A 50 percent level modulation must leave the gate statistic unchanged to
        # float32 rounding: measured relative difference about 5e-7.
        assert abs(a.band_energy - b.band_energy) / max(a.band_energy, 1e-12) < 1e-5


def test_a_still_room_reads_empty_and_a_shape_change_lifts_the_label() -> None:
    quiet = _feed(_engine(), 4.0, seed=2)
    moving = _feed(_engine(), 4.0, seed=2, motion_hz=1.0, motion_amp=0.30)
    assert quiet and moving
    assert all(r.gate == "empty" for r in quiet), "flat synthetic room sits under the presence threshold"
    assert np.mean([r.band_energy for r in moving]) > 10 * np.mean([r.band_energy for r in quiet])
    assert any(r.gate != "empty" for r in moving)


# --------------------------------------------------------------------------
# The timing contract, measured from the output
# --------------------------------------------------------------------------


def test_the_timing_contract_is_measured_and_met() -> None:
    eng = _engine()
    _feed(eng, 6.0)
    rep = eng.timing_report()
    assert rep["windows"] >= 6
    assert rep["latency_s"]["max"] <= MAX_LATENCY_S, f"per-window latency {rep['latency_s']['max']:.3f} s over the {MAX_LATENCY_S} s limit"
    assert rep["output_gap_s"]["max"] <= MAX_OUTPUT_GAP_S
    assert rep["update_interval_s"] == {"nominal": STRIDE_S, "window_s": WINDOW_S}
    assert rep["meets_contract"] is True
    assert sum(rep["gate_counts"].values()) == rep["windows"]
    assert all(r.within_contract() for r in eng.results)


def test_an_empty_report_says_so_rather_than_dividing_by_zero() -> None:
    assert _engine().timing_report() == {"windows": 0, "meets_contract": None}


# --------------------------------------------------------------------------
# Packet loss survives into the result
# --------------------------------------------------------------------------


def test_a_long_hole_flags_the_windows_that_cover_it() -> None:
    eng = _engine()
    rng = np.random.default_rng(3)
    t0 = 1000.0
    for i in range(int(6.0 * FS)):
        t = t0 + i / FS
        if 2.0 < (t - t0) < 2.6:            # a 600 ms hole on every link
            continue
        for node in NODES:
            eng.push(node, t, _packet(rng))
    flagged = [r for r in eng.results if r.gap_flag]
    assert flagged, "the hole must reach the output"
    for r in flagged:
        assert r.max_packet_gap > 0.25 and r.t_start <= t0 + 2.6 and r.t_end >= t0 + 2.0
    assert eng.timing_report()["gap_flagged_windows"] == len(flagged)


def test_the_replay_driver_refuses_the_held_out_session() -> None:
    from pipeline.live.realtime_replay import main
    assert main(["--stem", "participant_Zaid_TEST_walk"]) == 2
