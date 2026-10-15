"""Identification, the rig run: a recorded session streamed into the live app through the rig's own interface.

The source stands in for the three serial ports (`reports/identification/briefs/2026-09-30_extras.md`, section 5). It reads a
session's `.bin` files per receiver (identification recordings through the relabelled source, as
`pipeline/identify/ide_replay.py` does), and releases each receiver's frames as `pipeline.io.parse.CsiRecord`
objects, the objects the serial reader gives the app, in one global order by their recorded `t_mono` (the
recorded `t_mono` already carries the serial batching). Only each walk's recorded START press is injected, as a
space-bar `KeyEvent` at its recorded time; end presses and metre anchors never are. The consumer is ticked after
each arrival batch with the stream time, so every time the app uses comes from the stream's own time base.

Recordings, order and presses are exactly the harness's. A tracking recording's walks carry their recorded route
with the stream (the known-route rule of the thesis figures); identification recordings use the detector. The
truth (who walked) is given to the display only, after each decision is logged; it never reaches the engine.

Nothing here writes under data/.
"""

from __future__ import annotations

import json
import time

import numpy as np

MAC = "1a:00:00:00:00:00"   # the transmitter's ESP-NOW address: identical on every receiver, not stored per frame
LINKS = ("RX1", "RX2", "RX3")
INT_FIELDS = ("pkt_id", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
              "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
              "ant", "sig_len", "rx_format", "first_word")


def record_of(node: str, f) -> object:
    """One capture frame as the `CsiRecord` the serial reader would have produced for it."""
    from pipeline.io.parse import CSI_LEN, CsiRecord
    kw = {k: int(f[k]) for k in INT_FIELDS}
    return CsiRecord(node_id=node, t_mono=float(f["t_mono"]), t_host=float(f["t_host"]), mac=MAC, csi_len=CSI_LEN,
                     data=np.asarray(f["data"], np.int8).copy(), compensate_gain=float(f["gain"]), **kw)


class RecordedSource:
    """A recorded session: its recordings in the harness's order, each with its frames, presses, routes and truth."""

    def __init__(self, session: str):
        from pipeline.identify import ide_replay as RP
        from pipeline.identify.common import anon
        self.session = session
        self.recs = []
        for r in RP.session_recordings(session):
            gt = json.load(open(r["stem"] + ".gt.json", encoding="utf-8"))
            passes = sorted(gt["passes"], key=lambda q: q["t_start"])
            self.recs.append({"stem": r["stem"], "kind": r["kind"], "block": r["block"], "name": r["name"],
                              "code": anon(r["name"]), "label": f"{r['kind']}_{r['block']}_{r['name']}",
                              "presses": [float(q["t_start"]) for q in passes],
                              "routes": [q["path_name"] for q in passes],
                              "layout": "id_spot" if r["kind"] == "idcap" else "home"})

    def index_of(self, which: str) -> int:
        """A recording by its index, its label (kind_block_name) or a substring of its stem."""
        if which.isdigit():
            return int(which)
        hits = [i for i, r in enumerate(self.recs) if which == r["label"] or which in r["stem"]]
        if len(hits) != 1:
            raise SystemExit(f"--from {which!r} matches {len(hits)} recordings; labels: {[r['label'] for r in self.recs]}")
        return hits[0]

    def batches(self, rec: dict):
        """(stream time, [records]) in one global order by recorded t_mono (ties: RX1, RX2, RX3, then file order)."""
        from pipeline.io.capture_logger import read_capture_file
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in LINKS}
        tm = np.concatenate([np.asarray(fr[L]["t_mono"], np.float64) for L in LINKS])
        li = np.concatenate([np.full(len(fr[L]), k) for k, L in enumerate(LINKS)])
        ix = np.concatenate([np.arange(len(fr[L])) for L in LINKS])
        order = np.lexsort((ix, li, tm))
        tm, li, ix = tm[order], li[order], ix[order]
        cut = np.flatnonzero(np.diff(tm) > 0) + 1
        for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)]):
            yield float(tm[a]), [record_of(LINKS[li[j]], fr[LINKS[li[j]]][ix[j]]) for j in range(a, b)]


def stream(consumer, source: RecordedSource, speed="max", start: int = 0, play=None, log=None, until: int = None) -> dict:
    """Feed the session through the consumer, the rig's way: `handle` each record, space-bar `KeyEvent`s at the
    recorded start presses, `tick(stream time)` after each batch. Recordings before `start` are fed at maximum
    speed without display (calibration only); from `start`, recordings for which play(rec) holds are played at
    `speed` (1.0 = real time) with the display, the others fed fast without it. `until`: stop after this recording
    (a render ends with its last shown recording)."""
    from pipeline.io.ground_truth import KeyEvent
    info = {"recordings": [], "presses": 0}
    for k, rec in enumerate(source.recs):
        if until is not None and k > until:
            break
        shown = k >= start and (play is None or play(rec))
        consumer.new_stream(rec["layout"], display=shown,
                            routes=None if rec["kind"] == "idcap" else dict(zip(rec["presses"], rec["routes"])))
        for t in rec["presses"]:
            consumer.set_truth(t, rec["name"])                     # the display's truth: never enters the engine
        presses = list(rec["presses"])
        wall0, first = None, None
        for tau, recs in source.batches(rec):
            while presses and presses[0] <= tau:
                t = presses.pop(0)
                consumer.keys.put(KeyEvent(" ", t, t))
                info["presses"] += 1
            for r in recs:
                consumer.handle(r)
            if shown and speed != "max":
                if wall0 is None:
                    wall0, first = time.time(), tau
                lag = (tau - first) / float(speed) - (time.time() - wall0)
                if lag > 0:
                    time.sleep(lag)
            consumer.tick(tau)
        for t in presses:                                          # a press after the last frame (never in this data)
            consumer.keys.put(KeyEvent(" ", t, t))
            info["presses"] += 1
        consumer.end_stream()
        info["recordings"].append({"label": rec["label"], "shown": shown, "walks": len(rec["presses"])})
        if log:
            log(f"{time.strftime('%H:%M:%S')} {rec['label']}: {len(rec['presses'])} walks{' (shown)' if shown else ''}")
    return info
