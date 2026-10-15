"""The live stream cuts the tree's windows from packets and presses, and its guards hold.

The equality test replays the start of one Room A session 03 recording (read only) through
`LiveStream` and compares every window the decision could read, bit for bit, with the press-aligned
tree the shipped heads were run on: the stored float16 array, the RSSI series and the epoch start. It
runs in a child process (`tests/_live_checks.py` says why). The full run over all six recordings is
`python3 -m pipeline.live gates --gate stream`. The guard tests use synthetic packets, in process.
"""

import importlib.util
import math
import os

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_live_checks", os.path.join(REPO, "tests", "_live_checks.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope="module")
def replayed():
    if not C.present():
        pytest.skip("Room A session 03 or the frozen render results are not present")
    return C.child("stream_prefix")


def test_every_window_the_decision_reads_equals_the_tree(replayed):
    assert replayed["n"] > 60
    assert not replayed["missing"], "tree windows not cut live"
    assert not replayed["x_unequal"], "windows whose float16 array differs"
    assert not replayed["rssi_unequal"] and not replayed["epoch_unequal"]


def test_no_live_window_in_that_range_is_missing_from_the_tree(replayed):
    assert not replayed["extra"]


def test_the_first_walk_window_starts_one_second_before_each_raw_press(replayed):
    """On the SIDECAR's raw press time (the key's own time.monotonic()), which is what the tree's lattice
    is phased on. A live press with the reaction-time bias subtracted lands 51 ms off it."""
    assert len(replayed["first_walk_offset_s"]) == 3
    assert all(d < 1e-6 for d in replayed["first_walk_offset_s"])


# ------------------------------------------------------------------ guards, on synthetic packets

def _synthetic(seconds=40.0, seed=0, start=1000.0):
    from pipeline.io.clean import DEFAULT_KEEP
    rng = np.random.default_rng(seed)
    base = {n: np.ones(len(DEFAULT_KEEP), np.float32) for n in ("RX1", "RX2", "RX3")}
    pk = []
    for j, n in enumerate(("RX1", "RX2", "RX3")):
        t = start + 0.0013 * j + np.arange(0, seconds, 1 / 150.0)
        for tt in t:
            pk.append((float(tt), n, (20 + rng.normal(0, 1, 128)).astype(np.float32)))
    pk.sort(key=lambda x: x[0])
    return base, pk


def _stream(base):
    from pipeline.live.stream import LiveStream
    return LiveStream(base)


def test_a_packet_behind_its_predecessor_is_dropped_and_counted():
    base, pk = _synthetic(5.0)
    ls = _stream(base)
    for t, n, a in pk[:300]:
        ls.push_packet(n, t, a, t_host=t + 1e9, t_mono=t)
    last = ls.radio["RX1"].t[-1]
    ls.push_packet("RX1", last - 0.001, pk[0][2], t_host=1e9, t_mono=last)
    assert ls.n_dropped_backwards == 1
    assert all(b > a for a, b in zip(ls.radio["RX1"].t, ls.radio["RX1"].t[1:]))


def test_a_press_re_cuts_the_windows_it_re_assigns_onto_its_phase():
    from pipeline.constrained.lattice import PRESS_EPS_S
    base, pk = _synthetic(30.0)
    ls = _stream(base)
    press = 1000.0 + 20.137
    res = None
    for t, n, a in pk:
        if res is None and t >= press:
            res = ls.press(press)
        ls.push_packet(n, t, a, t_host=t + 1e9, t_mono=t)
    assert res["first"] and res["n_recut"] > 0
    for r in ls.ordered():
        ph = ((r["t0_exact"] - (press + PRESS_EPS_S)) / 0.5)
        assert abs(ph - round(ph)) < 1e-9, "a window is off the press's phase"


def test_close_withdraws_windows_past_the_trees_end_limit():
    base, pk = _synthetic(20.0)
    ls = _stream(base)
    press = 1000.0 + 10.0 - 0.2 - 2e-6          # a shift of about -0.2 s
    seen, pressed = {}, False
    for t, n, a in pk:
        if not pressed and t >= press:
            ls.press(press)
            pressed = True
        for r in ls.push_packet(n, t, a, t_host=t + 1e9, t_mono=t):
            seen[r["k"]] = r
    hi = min(ls._grid_last(n) for n in ls.nodes) - ls.window_s
    k_max = int(math.floor((hi - ls.first_base) / ls.stride_s + 1e-9))
    assert any(k > k_max for k in seen), "the synthetic end did not produce a window past the limit"
    res = ls.close()
    assert res["withdrawn"] and all(k > k_max for k in res["withdrawn"])
    assert all(k <= k_max and r["t0_exact"] <= hi + 1e-9 for k, r in ls.windows.items())


def test_rssi_is_the_whole_series_interpolation_even_with_tied_host_times():
    rng = np.random.default_rng(3)
    base, _pk = _synthetic(1.0)
    ls = _stream(base)
    ls.epoch_offset = 0.0
    th = np.repeat(np.arange(0.0, 30.0, 0.05), 7)           # seven packets per host stamp, as a serial read
    rv = rng.integers(-80, -40, len(th)).astype(np.float32)
    for n in ls.nodes:
        for a, b in zip(th, rv):
            ls.push_rssi(n, float(a), float(b))
    t0e = 12.3456
    got = ls.rssi_window(t0e)
    lat = t0e + np.arange(ls.n_samp) / ls.fs
    o = np.argsort(th, kind="stable")
    want = np.interp(lat, th[o], rv[o]).astype(np.float32)
    assert np.array_equal(got[0], want)
