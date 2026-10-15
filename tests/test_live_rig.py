"""The rig's plumbing, without a serial port: records in, causally anchored packets out, keys to presses.

A stub session stands in for the tracking session, so this checks only what the consumer itself does:
the device clock is anchored causally (`anchor.CausalAnchor`, the same fit the replay's causal gate
uses), nothing is pushed before its clock fit exists, RSSI is pushed at arrival, and SPACE alternates
start and end presses at the RAW key time. Also the gate-6 queue model and the display constants.
"""

import json
import os
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StubSession:
    def __init__(self):
        self.csi_calls, self.rssi_calls, self.presses, self.ends = [], [], [], []

    def rssi(self, n, t_host, r):
        self.rssi_calls.append((n, t_host, r))

    def csi(self, n, t, amp, t_host, t_mono):
        self.csi_calls.append((n, t, t_mono))

    def press(self, pid, t):
        self.presses.append((pid, t))

    def end_press(self, pid, t):
        self.ends.append((pid, t))


def _records(n=400, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        for node in ("RX1", "RX2", "RX3"):
            tm = 50.0 + i / 150.0 + rng.uniform(0, 0.03)
            out.append(SimpleNamespace(node_id=node, t_mono=tm, t_host=tm + 1.79e9, rssi=-55,
                                       local_timestamp=int(3_000_000 + i * 1e6 / 150.0),
                                       data=rng.integers(-40, 40, 256).astype(np.int8), channel=6))
    return out


def test_packets_are_timed_by_the_causal_fit_and_never_before_it():
    from pipeline.live.anchor import MIN_PACKETS, causal_anchor_times
    from pipeline.live.rig import TrackingConsumer
    s = StubSession()
    c = TrackingConsumer(s)
    recs = _records()
    for r in recs[: 3 * (MIN_PACKETS - 1)]:
        c.handle(r)
    assert not s.csi_calls and len(s.rssi_calls) == 3 * (MIN_PACKETS - 1)
    for r in recs[3 * (MIN_PACKETS - 1):]:
        c.handle(r)
    rx1 = [r for r in recs if r.node_id == "RX1"]
    want, _start = causal_anchor_times([r.local_timestamp for r in rx1], [r.t_mono for r in rx1])
    got = [t for n, t, _m in s.csi_calls if n == "RX1"]
    assert np.array_equal(np.asarray(got), want)


def test_space_alternates_start_and_end_presses_at_the_raw_key_time():
    from pipeline.live.rig import TrackingConsumer
    s = StubSession()
    c = TrackingConsumer(s)
    for t in (10.0, 15.0, 30.0, 34.5):
        c.keys.put(SimpleNamespace(key=" ", t_mono=t))
    c.tick(40.0)
    assert s.presses == [(1, 10.0), (2, 30.0)] and s.ends == [(1, 15.0), (2, 34.5)]
    c.keys.put(SimpleNamespace(key="q", t_mono=41.0))
    c.tick(41.0)
    assert c.stop.is_set()


def test_record_amplitude_is_the_loaders_amplitude():
    from pipeline.live.rig import amplitude
    d = np.random.default_rng(2).integers(-100, 100, 256).astype(np.int8)
    want = np.sqrt((d.astype(np.float32).reshape(1, 128, 2) ** 2).sum(-1))[0]
    assert np.array_equal(amplitude(d), want)


def test_the_queue_model_charges_a_slow_press_to_the_windows_behind_it():
    from pipeline.live.timing import live_queue
    ev = [(10.0 + 0.5 * k + 2.0, 0.05, "window", 10.0 + 0.5 * k) for k in range(20)]
    fast = live_queue(ev)
    assert fast["max_latency_s"] < 0.06 and fast["max_gap_s"] < 0.51
    slow = live_queue(ev + [(15.0, 3.0, "press", None)])
    assert slow["max_latency_s"] > 2.5 and slow["max_gap_s"] > 3.0 and slow["windows_over_0_5_s"] > 0


def test_the_display_constants_are_the_ones_f3_render_recorded():
    import pipeline.live.display as D
    p = os.path.join(REPO, "runs", "constrained", "fh", "f3_render", "results.json")
    if not os.path.exists(p):
        return
    f3 = json.load(open(p, encoding="utf-8"))
    assert D.LATENCY_S == f3["display_latency_s"] and D.LAG_S == f3["lag_s"] and D.FPS == f3["fps"]
    assert D.SHIFT_W == f3["anchor_segment"]["shift_w"]
    assert D.DELAY_S == f3["shipped"]["commit_delay_s"]
    mm = f3["shipped"]["motion_model"]
    assert D.DISPLAY_CAP_M_PER_WINDOW == mm["display_max_advance_m_per_window"]
    assert D.DISPLAY_SD_SCALE == mm["display_sd_scale"]


def _fake_session(truth=True):
    """A TrackingSession holding one walk's drawn frames and decision, without building its heads."""
    from pipeline.live.tracking import TrackingSession
    s = TrackingSession.__new__(TrackingSession)
    s.order = list(range(40))
    s.passes = {1: {"press": 100.0, "end": 105.0, "terms": None}}
    s.display = SimpleNamespace(out={1: {round(100.0 + 0.1 * i, 4): (1.0, 0.1 * i) for i in range(80)}},
                                meta={1: {"lock_line": "A_fwd", "switches": []}})
    s.decisions = [{"pass_id": 1, "final_line": "A_fwd"}]
    s.session, s.stem = "03", "stem"
    s.truth = None
    if truth:
        s.set_truth({"passes": [{"pass_id": 1, "path_name": "A_rev", "anchor_times": [100.0, 105.0],
                                 "anchor_coords": [[2.5, 5.0], [2.5, 0.0]]}]})
    return s


def test_the_green_marker_appears_with_the_dot_and_shows_where_the_walker_was():
    s = _fake_session()
    assert s.screen_state(101.9)["green"] is None               # the park: nothing shown before press + 2 s
    st = s.screen_state(103.0)                                   # shows the moment 101.0: 1 s into a 5 s walk
    assert st["green"] == (2.5, 4.0) and st["dot"] is not None
    assert s.screen_state(107.5)["green"] is None               # the walk's frames are over


def test_the_verdict_is_judged_against_the_truth_and_only_after_the_walk():
    s = _fake_session()
    assert s.screen_state(106.9)["verdict"] is None              # end press + 2 s not reached
    v = s.screen_state(107.1)["verdict"]
    assert v == {"committed": "A_fwd", "drawn": "A_fwd", "true": "A_rev"}
    assert _fake_session(truth=False).screen_state(107.1)["verdict"]["true"] is None


def test_the_banner_is_green_when_right_red_when_wrong_grey_without_truth():
    from pipeline.constrained.paths import states
    from pipeline.live.screen import Screen
    sc = Screen(states(), headless=True)
    edges = {}
    for true in ("A_fwd", "A_rev", None):
        sc.tracking(verdict={"committed": "A_fwd", "drawn": "A_fwd", "true": true})
        box = [t for t in sc.bx.texts if t.get_bbox_patch() is not None][0].get_bbox_patch()
        edges[true] = box.get_edgecolor()[:3]
    import matplotlib.colors as mc
    assert edges["A_fwd"] == mc.to_rgb("tab:green") and edges["A_rev"] == mc.to_rgb("tab:red")
    assert edges[None] == mc.to_rgb("0.5")


def test_a_walk_over_but_undecided_says_so():
    s = _fake_session()
    s.decisions = []
    v = s.screen_state(107.1)["verdict"]
    assert v["pending"] and "committed" not in v
