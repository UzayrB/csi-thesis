"""The rig run (`reports/identification/briefs/2026-09-30_extras.md`, sections 5.5 and 6.1): recorded B2 streamed through the live
app's rig interface (`pipeline/live/identify_recorded.py`, `pipeline/live/identify_engine.py`).

Fast (always):
- the guard refuses the deployment model for a B2 stream;
- the engine decides from the very first walk of a session (no warm-up);
- the display's truth overlay never changes a decision.
Slow (IDE_SLOW=1):
- the rig run equals the harness's B2 decisions, pass for pass (the whole session);
- --speed 1 equals --speed max on a full B2 recording;
- --from equals the whole-day stream for the same passes;
- a fake serial port, through the real SerialReader and parse_line, equals the recorded source.

    OMP_NUM_THREADS=1 PYTHONPATH=. IDE_SLOW=1 python3 -m pytest -q tests/test_ide_rigrun.py
"""

from __future__ import annotations

import base64
import json
import os
import queue
import sys
import threading
import types

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOW = pytest.mark.skipif(os.environ.get("IDE_SLOW") != "1", reason="slow: set IDE_SLOW=1")


@pytest.fixture(autouse=True)
def _at_repo(monkeypatch):
    monkeypatch.chdir(REPO)


def _harness():
    from pipeline.identify import engine as EN
    from pipeline.live import identify_engine as IE
    m = IE.final_model("B2")
    p = os.path.join(REPO, "runs", "identify", "engine", "replays", f"{m}_B2_T{EN.T_S:.1f}")
    if not os.path.exists(p + ".npz"):
        pytest.skip(f"no harness replay {p}")
    return m, np.load(p + ".npz"), json.load(open(p + ".json"))["device"]


def _run(model, device, n_recs=None, speed="max", start=0, truth=True, source=None):
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_train as IT
    from pipeline.live import identify_engine as IE
    from pipeline.live.identify_recorded import RecordedSource, stream
    src = source or RecordedSource("B2")
    if n_recs:
        src.recs = src.recs[:n_recs]
    app = IE.EngineApp(EN.Engine(IE.model_dir(model), amp_norm=IT.gs_adopted(), device=device), model, replay=True,
                       dmode=IE.direction_mode())
    c = IE.EngineConsumer(app, None)
    if not truth:
        c.set_truth = lambda *a_, **k_: None
    stream(c, src, speed=speed, start=start)
    return app.decisions


def _same(d1, d2, atol=1e-9):
    assert len(d1) == len(d2) and len(d1) > 0
    assert [d["t0"] for d in d1] == [d["t0"] for d in d2]
    e1, e2 = np.array([d["ensemble"] for d in d1]), np.array([d["ensemble"] for d in d2])
    assert np.array_equal(e1.argmax(1), e2.argmax(1))
    assert np.allclose(e1, e2, atol=atol, rtol=0)


# ------------------------------------------------------------------ fast

def test_guard_refuses_deployment_model_for_b2():
    from pipeline.live import identify_engine as IE
    with pytest.raises(SystemExit):
        IE.guard(IE.model_dir(IE.deployment_model()), "B2")
    assert IE.guard(IE.model_dir(IE.final_model("B2")), "B2") == ["A1", "A2", "A3", "B1"]


def test_first_walk_decides_without_warmup():
    """A fresh session decides its very first walk (training statistics; no calibration walk asked for)."""
    m, _h, dev = _harness()
    d = _run(m, dev, n_recs=1)
    assert d[0]["calib_n"] == 0 and d[0]["top"] in ("P1", "P2", "P3", "P4", "P5", "P6")
    assert len(d) == 10


def test_overlay_never_changes_a_decision():
    m, _h, dev = _harness()
    _same(_run(m, dev, n_recs=1, truth=True), _run(m, dev, n_recs=1, truth=False), atol=0.0)


# ------------------------------------------------------------------ slow

@SLOW
def test_rig_run_equals_harness_whole_b2():
    m, h, dev = _harness()
    d = _run(m, dev)
    n = len(d)
    assert n == len(h["t0"]) == 299
    assert np.array_equal(np.array([x["t0"] for x in d]), h["t0"])
    e = np.array([x["ensemble"] for x in d])
    assert np.array_equal(e.argmax(1), h["ensemble"].argmax(1))
    assert np.allclose(e, h["ensemble"], atol=1e-6, rtol=0)


@SLOW
def test_speed_1_equals_speed_max():
    m, _h, dev = _harness()
    _same(_run(m, dev, n_recs=1, speed=1.0), _run(m, dev, n_recs=1, speed="max"), atol=0.0)


@SLOW
def test_from_equals_whole_day():
    m, _h, dev = _harness()
    whole = _run(m, dev, n_recs=2)
    late = _run(m, dev, n_recs=2, start=1, speed=1.0)
    k = [i for i, d in enumerate(whole) if i >= 10]            # the second recording's walks
    _same([whole[i] for i in k], [late[i] for i in k], atol=0.0)


class FakeSerialSource:
    """The recorded source's recordings, delivered through the SERIAL code path: each recorded frame re-encoded as
    the firmware's base64 CSI_DATA row, read by the real `SerialReader` from a fake port and parsed by the real
    `parse_line`; the reader stamps t_mono and t_host from a per-reader clock set to the frame's recorded times."""

    FIELDS = ("pkt_id", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
              "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
              "ant", "sig_len", "rx_format")

    def __init__(self, inner):
        self.inner = inner
        self.recs = inner.recs

    def index_of(self, which):
        return self.inner.index_of(which)

    @staticmethod
    def line(f) -> bytes:
        from pipeline.live.identify_recorded import MAC
        vals = [MAC if k == "mac" else str(int(f[k])) for k in FakeSerialSource.FIELDS]
        b64 = base64.b64encode(np.asarray(f["data"], np.int8).tobytes()).decode()
        return ("CSI_DATA," + ",".join(vals) + f",256,{int(f['first_word'])},{int(round(float(f['gain']) * 10000))},{b64}\n").encode()

    def batches(self, rec):
        from pipeline.io import capture_logger as CLG
        from pipeline.io.capture_logger import NodeState, SerialReader, read_capture_file
        links = ("RX1", "RX2", "RX3")
        clock = threading.local()
        chunks = {}
        for L in links:
            fr = read_capture_file(f"{rec['stem']}_{L}.bin")[1]
            tm = np.asarray(fr["t_mono"], np.float64)
            cut = np.flatnonzero(np.diff(tm) > 0) + 1
            chunks[L] = [(float(tm[a]), float(fr["t_host"][a]), b"".join(self.line(fr[j]) for j in range(a, b)))
                         for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)])]
        left = {L: len(chunks[L]) for L in links}

        class Port:
            def __init__(self, L):
                self.L = L

            def read(self, n):
                if not chunks[self.L]:
                    __import__("time").sleep(0.02)            # a real port blocks for its read timeout
                    return b""
                tm, th, data = chunks[self.L].pop(0)
                clock.t_mono, clock.t_host = tm, th
                left[self.L] -= 1
                return data

            def close(self):
                pass

        fake_serial = types.ModuleType("serial")
        fake_serial.Serial = lambda port, baud, timeout=None: Port(port)
        fake_time = types.SimpleNamespace(monotonic=lambda: clock.t_mono, time=lambda: clock.t_host,
                                          sleep=__import__("time").sleep)
        saved_serial, saved_time = sys.modules.get("serial"), CLG.time
        sys.modules["serial"], CLG.time = fake_serial, fake_time
        q, stop = queue.Queue(), threading.Event()
        try:
            readers = [SerialReader(NodeState(node_id=L, port=L), q, stop) for L in links]
            for r in readers:
                assert r.open()
                r.start()
            while any(left.values()):
                __import__("time").sleep(0.05)
            __import__("time").sleep(0.3)
            stop.set()
            for r in readers:
                r.join(timeout=5)
        finally:
            CLG.time = saved_time
            if saved_serial is None:
                sys.modules.pop("serial", None)
            else:
                sys.modules["serial"] = saved_serial
        recs = []
        while not q.empty():
            recs.append(q.get_nowait())
        order = {L: k for k, L in enumerate(links)}
        seq = {L: 0 for L in links}
        keyed = []
        for r in recs:
            keyed.append(((r.t_mono, order[r.node_id], seq[r.node_id]), r))
            seq[r.node_id] += 1
        keyed.sort(key=lambda x: x[0])
        i = 0
        while i < len(keyed):
            j = i
            while j < len(keyed) and keyed[j][0][0] == keyed[i][0][0]:
                j += 1
            yield keyed[i][0][0], [x[1] for x in keyed[i:j]]
            i = j


@SLOW
def test_fake_serial_port_equals_recorded_source():
    from pipeline.live.identify_recorded import RecordedSource
    m, _h, dev = _harness()
    inner = RecordedSource("B2")
    inner.recs = inner.recs[:1]
    serial = _run(m, dev, source=FakeSerialSource(inner))
    rec = _run(m, dev, n_recs=1)
    _same(serial, rec, atol=0.0)
