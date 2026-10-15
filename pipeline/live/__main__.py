"""The live system's one entry command.

    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live gates --gate e2e      # the proofs, on replay
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay --recording B2/participant_X_walk --presses start   # the app
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay-standin --stem participant_X_TEST_walk --screen   # the old stand-in
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay-identify --snapshots runs/live/screen
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live preflight --baseline <dir>        # the final model's checks
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --mode tracking --baseline <dir> --minutes 10

`replay` feeds a recorded Room A session 03 walk recording through the whole tracking session (packets
and presses as they arrived) with the Room A stand-in's heads, and shows or saves the screen.
`replay-identify` does the same for identification on id29's synthetic DC2 recordings (the only DC2-
layout identification data before 26 September). `rig` runs on the boards: it OPENS SERIAL PORTS, so
it is never started by a gate or a test, only by the operator.

Nothing here writes under data/. Replay outputs go to runs/live/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _standin_session(stem: str, pieces=None, components=None):
    import pipeline.io.windows as W
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.live.gates import TAG, TEST, TRAIN
    from pipeline.live.tracking import TrackingSession
    sdir = os.path.join(REPO_ROOT, "data", "room_A", f"session_{TEST[0]}")
    return TrackingSession(tag=TAG, train=TRAIN, test=TEST, reader_tag=tag_for_session(TEST[0]),
                           baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)), session=TEST[0],
                           stem=stem, pieces=pieces, components=components), sdir


def cmd_replay(a) -> int:
    import numpy as np

    from pipeline.live.replay import recording_events
    from pipeline.live.screen import Screen
    s, sdir = _standin_session(a.stem)
    with open(os.path.join(sdir, f"{a.stem}.gt.json"), encoding="utf-8") as f:
        s.set_truth(json.load(f))                 # the screen's green marker and verdict colour only
    ev, _info = recording_events(sdir, a.stem, end_presses=True, causal_anchor=a.causal)
    screen = Screen(s.st, headless=not a.screen) if (a.screen or a.snapshots) else None
    if a.snapshots:
        os.makedirs(a.snapshots, exist_ok=True)
    if a.passes:
        ends = sorted(e_[3] for e_ in ev if e_[2] == "end")
        stop = ends[min(a.passes, len(ends)) - 1] + 3.0
        ev = [e_ for e_ in ev if e_[0] <= stop]
    wall0, t_first = time.time(), ev[0][0]
    next_draw, shots = None, 0
    # snapshots at the moments the rules are about: mid-walk after the lock, and after the end text
    moments = sorted([e_[3] + 3.5 for e_ in ev if e_[2] == "press"][: a.max_snapshots // 2]
                     + [e_[3] + 2.5 for e_ in ev if e_[2] == "end"][: a.max_snapshots // 2])
    for e_ in ev:
        now = e_[0]
        if a.screen and a.speed > 0:                     # play at real speed (or a multiple)
            lag = (now - t_first) / a.speed - (time.time() - wall0)
            if lag > 0:
                time.sleep(lag)
        if e_[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
            if ts is None:
                s.rssi(n, t_host, rssi)
            else:
                s.packet(n, ts, amp, t_host, t_mono, rssi)
        elif e_[2] == "press":
            s.press(e_[4], e_[3])
        else:
            s.end_press(e_[4], e_[3])
        if screen is not None and a.snapshots:
            while moments and now >= moments[0]:
                moments.pop(0)
                screen.tracking(**s.screen_state(now))
                screen.save(os.path.join(a.snapshots, f"tracking_{a.stem}_{now:.1f}.png"))
                shots += 1
        elif screen is not None and s.passes:
            next_draw = now if next_draw is None else next_draw
            if now >= next_draw:
                screen.tracking(**s.screen_state(now))
                next_draw = now + 0.1
    s.close()
    out = {"stem": a.stem, "decisions": s.decisions, "snapshots": shots,
           "per_window_s_median": float(np.median([x for x, p in s.timing["window_s"] if not p]))}
    print(json.dumps(out, indent=1))
    return 0


def cmd_replay_identify(a) -> int:
    from pipeline.live.gates import gate5
    from pipeline.live.screen import Screen
    res = gate5()
    print(json.dumps({k: v for k, v in res.items() if k != "example"}, indent=1))
    if a.snapshots:
        import numpy as np  # noqa: F401
        from pipeline.constrained.night_common import shipped_pieces
        st = shipped_pieces()[0]
        sc = Screen(st, headless=True)
        os.makedirs(a.snapshots, exist_ok=True)
        ex = res.get("example")
        sc.identification(result=ex, combined=None, n_passes=1)
        sc.save(os.path.join(a.snapshots, "identification_synthetic.png"))
    return 0 if res["PASSED"] else 1


def cmd_rig(a) -> int:
    """On the boards. Since 2026-09-29 the FINAL model by default (pipeline/live/final_model.py: its pre-flight
    runs first and refuses on any failure; either room). --model frozen keeps the frozen Room A stand-in."""
    if a.model == "final":
        from pipeline.live.final_model import main as fmain
        return fmain(["rig", "--baseline", a.baseline or ""] + (["--minutes", str(a.minutes)] if a.minutes else []))
    if a.room != "A":
        raise SystemExit("REFUSED: the Room B live mode is not built. It needs the DISP_END display head for "
                         "s010203_to_sB (not trained), dc2_run's tree binding, and configuration B's constants "
                         "re-anchored on the day's calibration walk. See reports/LIVE_SYSTEM_2026-09-25.md.")
    if not a.baseline or not os.path.isdir(a.baseline):
        raise SystemExit("REFUSED: --baseline <dir> is required: this session's own 60 s empty-room capture, "
                         "taken with RX2 where this mode needs it")
    from pipeline.constrained.nodes import room_a_macs
    from pipeline.live.rig import TrackingConsumer, run
    from pipeline.live.screen import Screen
    from pipeline.live.rig_run import identify, mapping_by_mac
    from pipeline.io.windows import session_baseline
    nodes = mapping_by_mac(identify(), room_a_macs(os.path.join(REPO_ROOT, "data")))
    nodes = {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}
    if a.mode != "tracking":
        raise SystemExit("REFUSED: the identification rig mode needs an enrolment set (DC2 day 1 natural "
                         "passes); run `replay-identify` until DC2 day 1 exists")
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.live.gates import TAG, TEST, TRAIN
    from pipeline.live.tracking import TrackingSession
    s = TrackingSession(tag=TAG, train=TRAIN, test=TEST, reader_tag=tag_for_session(TEST[0]),
                        baseline=session_baseline(a.baseline), session="live", stem=time.strftime("rig_%Y%m%d_%H%M%S"))
    c = TrackingConsumer(s, Screen(s.st, headless=False))
    rc = run(c, nodes, duration=a.minutes * 60.0 if a.minutes else None)
    s.close()
    os.makedirs(os.path.join(REPO_ROOT, "runs", "live", "rig"), exist_ok=True)
    with open(os.path.join(REPO_ROOT, "runs", "live", "rig", f"{s.stem}.json"), "w", encoding="utf-8") as f:
        json.dump(c.summary(), f, indent=1, default=str)
    return rc


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["replay"]:
        # THE APP'S REPLAY HARNESS: everything after `replay` is its own arguments
        from pipeline.live.app_replay import main as rmain
        return rmain(argv[1:])
    if (argv[:1] == ["replay-identify"] and "--session" in argv) or (argv[:1] == ["rig"] and "identify" in argv and "--legacy" not in argv):
        from pipeline.live.identify_engine import main as imain   # identification: the one-press engine
        return imain(argv)
    if argv[:1] == ["rig"] and "--stream" in argv:
        # THE STREAMED RIG RUN: a recorded session through the boards' own ingestion path (stream_source.py)
        from pipeline.live.stream_source import main as smain
        return smain(argv[1:])
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gates", help="run an equality gate on replay")
    g.add_argument("--gate", required=True)
    g.add_argument("--every", type=int, default=1)
    sub.add_parser("replay", help="THE APP'S REPLAY HARNESS (app_replay): --recording/--session, --presses start|start_end|none",
                   add_help=False)
    r = sub.add_parser("replay-standin", help="the old Room A stand-in recording through the tracking session")
    r.add_argument("--stem", default="participant_PA5_TEST_walk")
    r.add_argument("--screen", action="store_true", help="open the window and play at --speed")
    r.add_argument("--speed", type=float, default=1.0)
    r.add_argument("--passes", type=int, default=None, help="stop after this many walks")
    r.add_argument("--snapshots", default=None, help="save the screen here after the lock and after the end text")
    r.add_argument("--max-snapshots", type=int, default=6)
    r.add_argument("--causal", action="store_true", help="anchor device clocks causally, as the rig must")
    i = sub.add_parser("replay-identify", help="identification on id29's synthetic DC2 recordings")
    i.add_argument("--snapshots", default=None)
    k = sub.add_parser("rig", help="ON THE BOARDS: opens serial ports")
    k.add_argument("--mode", choices=("tracking", "identify"), default="tracking")
    k.add_argument("--room", choices=("A", "B"), default="A")
    k.add_argument("--baseline", default=None)
    k.add_argument("--minutes", type=float, default=None)
    k.add_argument("--model", choices=("final", "frozen"), default="final",
                   help="final (default since 2026-09-29): the final tracker, either room; frozen: the Room A stand-in")
    f = sub.add_parser("preflight", help="what must hold before the rig runs the final model (opens no port)")
    f.add_argument("--baseline", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "gates":
        from pipeline.live.gates import main as gmain
        return gmain(["--gate", a.gate, "--every", str(a.every)])
    if a.cmd == "preflight":
        from pipeline.live.final_model import main as fmain
        return fmain(["preflight"] + (["--baseline", a.baseline] if a.baseline else []))
    return {"replay-standin": cmd_replay, "replay-identify": cmd_replay_identify, "rig": cmd_rig}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
