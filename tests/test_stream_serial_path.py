"""The boards' ingestion path, exercised with recorded packets (Uzayr, 30 September 2026, item 5b).

The streamed rig run (`pipeline/live/stream_source.py`) replaces ONLY the packet source. These tests push a B2
recording's own frames through the REAL serial path, with nothing under `pipeline/io/` edited:
1. every frame, written back as the project firmware's base64 CSI_DATA row, parses (`parse_line`) to the same
   metadata, the same 256 int8 values and the same gain;
2. a real `SerialReader` thread, given a port object that returns those rows in serial-read chunks, stamps,
   splits, parses and queues them: every record arrives, in order, identical to its frame, with host timestamps
   taken by the reader.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import time

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
BIN = os.path.join(REPO_ROOT, "data", "room_B", "session_B2", "participant_PA5_walk_RX1.bin")
INT_FIELDS = ("pkt_id", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
              "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
              "ant", "sig_len", "rx_format", "first_word")

pytestmark = pytest.mark.skipif(not os.path.exists(BIN), reason="the B2 recording is not on this machine")


def _frames():
    from pipeline.io.capture_logger import read_capture_file
    return read_capture_file(BIN)[1]


def _same(rec, fr) -> bool:
    return (all(int(getattr(rec, k)) == int(fr[k]) for k in INT_FIELDS)
            and np.array_equal(np.asarray(rec.data, np.int8), np.asarray(fr["data"], np.int8))
            and np.float32(rec.compensate_gain) == np.float32(fr["gain"]))


def test_every_frame_round_trips_through_the_parser():
    from pipeline.io.parse import ParseCounters, parse_line
    from pipeline.live.stream_source import frame_to_line
    frames = _frames()
    c = ParseCounters()
    bad = 0
    for fr in frames:
        rec = parse_line(frame_to_line(fr), "RX1", c, 0.0, 0.0)
        bad += int(rec is None or not _same(rec, fr))
    assert bad == 0 and c.ok == len(frames), (bad, c)


def test_the_serial_reader_thread_carries_them():
    from pipeline.io.capture_logger import NodeState, SerialReader
    from pipeline.live.stream_source import frame_to_line
    frames = _frames()[:600]
    blob = b"".join((frame_to_line(fr) + "\n").encode("ascii") for fr in frames)

    class Port:                                          # a serial port: reads return what is buffered, in chunks
        def __init__(self):
            self.pos = 0

        def read(self, n):
            if self.pos >= len(blob):
                time.sleep(0.01)
                return b""
            out = blob[self.pos:self.pos + 1500]          # a boundary mid-line, as a real read can fall
            self.pos += len(out)
            return out

        def close(self):
            pass
    q, stop = queue.Queue(), threading.Event()
    r = SerialReader(NodeState(node_id="RX1", port="replay://RX1"), q, stop)
    r._ser = Port()                                      # the port the boards would give; open() is not needed
    r.start()
    got, t_end = [], time.time() + 20.0
    while len(got) < len(frames) and time.time() < t_end:
        try:
            got.append(q.get(timeout=0.2))
        except queue.Empty:
            pass
    stop.set()
    r.join(timeout=2.0)
    assert len(got) == len(frames), len(got)
    assert all(_same(g, fr) for g, fr in zip(got, frames))
    t = [g.t_mono for g in got]
    assert all(b >= a for a, b in zip(t, t[1:])), "the reader's own timestamps must not go backwards"
    assert all(g.node_id == "RX1" for g in got)
