"""THE LIVE RIG RUN (batch 23e item 7), tested without hardware.

A capture is SIMULATED by writing a real Room A recording's files the way the logger does: the
header first, then frames in chunks, including a HALF-WRITTEN frame. The follower must read every
whole frame exactly once, never a partial one, push RX1 to RX3 by name, and never push RX4.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from pipeline.live import rig_run as R

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = REPO / "data" / "room_A" / "session_01"
STEM = "participant_PA5_walk"


class _Eng:
    def __init__(self):
        self.pushed, self.results = {}, []

    def push(self, n, t, a):
        self.pushed[n] = self.pushed.get(n, 0) + 1


def _split(path):
    blob = path.read_bytes()
    n = int(np.frombuffer(blob[len(R.MAGIC):len(R.MAGIC) + 4], dtype="<u4")[0])
    head_end = len(R.MAGIC) + 4 + n
    dt = np.dtype([tuple(d) for d in json.loads(blob[len(R.MAGIC) + 4:head_end])["dtype"]])
    return blob[:head_end], blob[head_end:], dt.itemsize


def test_the_follower_reads_whole_frames_once_and_never_pushes_rx4(tmp_path):
    if not (SRC / f"{STEM}_RX1.bin").exists():
        pytest.skip("Room A raw data absent")
    parts = {n: _split(SRC / f"{STEM}_{n}.bin") for n in ("RX1", "RX2", "RX3")}
    parts["RX4"] = parts["RX2"]                               # the ID link: another node's real radio
    lim = {n: min(len(b), 2000 * isz) for n, (_h, b, isz) in parts.items()}
    files = {n: tmp_path / f"{STEM}_{n}.bin" for n in parts}
    for n, (h, _b, _i) in parts.items():
        files[n].write_bytes(h)
    eng = _Eng()
    fs = R.FollowSession(str(tmp_path), STEM, eng)
    written = {n: 0 for n in parts}
    for k in range(1, 9):
        for n, (h, b, isz) in parts.items():
            upto = min(lim[n], (lim[n] // 8) * k + isz // 2)        # ends mid-frame on purpose
            with open(files[n], "ab") as f:
                f.write(b[written[n]:upto])
            written[n] = upto
        fs.step()
        for n in parts:
            assert sum(len(x) for x in fs.seen[n]) == written[n] // parts[n][2], "a partial frame was read"
    for n, (h, b, isz) in parts.items():
        with open(files[n], "ab") as f:
            f.write(b[written[n]:lim[n]])
    fs.step()
    assert "RX4" not in eng.pushed, "the identification link must never reach tracking"
    for n in ("RX1", "RX2", "RX3"):
        assert sum(len(x) for x in fs.seen[n]) == lim[n] // parts[n][2]
        assert eng.pushed[n] == len(fs.pushed_ts[n]) > 0, "each anchored frame pushed exactly once"
    s = fs.summary()
    assert s["never_pushed"] == ["RX4"] and s["per_link"]["RX4"]["packets"] > 0
    assert set(s["anchor_drift_s"]) == {"RX1", "RX2", "RX3"}, "the prefix-fit drift must be measured"


def test_nodes_are_named_by_mac_not_by_port_order():
    A = {"RX1": "aa:00:00:00:00:01", "RX2": "aa:00:00:00:00:02", "RX3": "aa:00:00:00:00:03"}
    found = {"/dev/cu.usbserial-0001": ("aa:00:00:00:00:03", "receiver"),   # sorts first, is RX3
             "/dev/cu.usbserial-0002": ("bb:00:00:00:00:09", "receiver"),   # the ID board
             "/dev/cu.usbserial-0003": ("aa:00:00:00:00:01", "receiver"),
             "/dev/cu.usbserial-0004": ("aa:00:00:00:00:02", "receiver"),
             "/dev/cu.usbserial-0005": (None, "transmitter")}
    m = R.mapping_by_mac(found, A)
    assert m == {"RX1": "/dev/cu.usbserial-0003", "RX2": "/dev/cu.usbserial-0004",
                 "RX3": "/dev/cu.usbserial-0001", "RX4": "/dev/cu.usbserial-0002"}


def test_a_missing_tracking_board_refuses():
    A = {"RX1": "aa:00:00:00:00:01", "RX2": "aa:00:00:00:00:02", "RX3": "aa:00:00:00:00:03"}
    found = {"/dev/cu.usbserial-0001": ("aa:00:00:00:00:01", "receiver"),
             "/dev/cu.usbserial-0002": ("bb:00:00:00:00:09", "receiver"),
             "/dev/cu.usbserial-0003": ("aa:00:00:00:00:02", "receiver")}
    with pytest.raises(SystemExit) as e:
        R.mapping_by_mac(found, A)
    assert "RX3" in str(e.value)


def test_no_receivers_is_blocked_on_operator(monkeypatch, capsys):
    monkeypatch.setattr(R, "ports", lambda: [])
    assert R.main([]) == 2
    assert "BLOCKED ON OPERATOR" in capsys.readouterr().out
