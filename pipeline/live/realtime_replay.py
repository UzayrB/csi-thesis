"""Feed a capture file through the engine, for testing without hardware.

Replays the packets of one recording in time order, optionally at
wall-clock speed, so the streaming path can be exercised and its timing
contract measured on real CSI with no receiver attached and no serial port
opened. The baseline comes from the recording's own sidecar, as it must.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.gate import presence_threshold
from pipeline.live.realtime_engine import NODES, RealTimeEngine, Result
from pipeline.io.windows import FS, load_node, session_baseline


def replay(session_dir: str, stem: str, realtime: bool = False, limit_s: Optional[float] = None,
           engine: Optional[RealTimeEngine] = None) -> RealTimeEngine:
    """Push one recording's packets through an engine in time order."""
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    bdir = sidecar["baseline_capture"].rstrip("/")
    if engine is None:
        from tools.calibrate_gate import band_energy, cut_baseline
        engine = RealTimeEngine(baseline=session_baseline(bdir), presence_theta=presence_threshold(band_energy(cut_baseline(bdir))))
    streams = {}
    for n in NODES:
        amp, ts, _start, _eo = load_node(os.path.join(session_dir, f"{stem}_{n}.bin"))
        streams[n] = (ts, amp)
    merged = sorted(((float(t), n, i) for n, (ts, _a) in streams.items() for i, t in enumerate(ts)))
    if limit_s is not None and merged:
        cutoff = merged[0][0] + limit_s
        merged = [m for m in merged if m[0] <= cutoff]
    t_zero = merged[0][0] if merged else 0.0
    wall0 = time.monotonic()
    for t, n, i in merged:
        if realtime:
            due = (t - t_zero) - (time.monotonic() - wall0)
            if due > 0:
                time.sleep(due)
        engine.push(n, t, streams[n][1][i])
    return engine


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--session", default="data/room_A/session_01")
    ap.add_argument("--stem", default="participant_Zaid_walk")
    ap.add_argument("--limit-s", type=float, default=60.0)
    ap.add_argument("--realtime", action="store_true", help="pace the replay at wall-clock speed")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if "_TEST_" in args.stem:
        print("refusing: the held-out test session is opened once, by the operator, from pipeline.eval")
        return 2
    eng = replay(args.session, args.stem, realtime=args.realtime, limit_s=args.limit_s)
    rep = eng.timing_report()
    print(json.dumps(rep, indent=1))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"session": args.session, "stem": args.stem, "timing": rep,
                       "results": [r.__dict__ for r in eng.results[:50]]}, f, indent=1)
    return 0 if rep.get("meets_contract") else 1


if __name__ == "__main__":
    sys.exit(main())
