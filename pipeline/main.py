# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: START HERE: the live app's front door.

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINES = os.path.join("runs", "live", "baselines")
NO_FOCUS_HELP = "identification: do not give the keyboard to the Terminal at Done, nor the window back after SPACE"



# Python -m pipeline.main app: the start window, then the chosen task's steps, one after another.
def app(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline.main app", description="The live app: one task per run.")
    ap.add_argument("--task", choices=("tracking", "identification"), default=None, help="skip the start window")
    ap.add_argument("--minutes", type=float, default=None, help="stop after this many minutes (default: until q)")
    ap.add_argument("--baseline", default=None, help="tracking: an earlier 60 s empty-room capture, instead of a new one")
    ap.add_argument("--stream", default=None, help="tracking: a recorded <session>/<stem> through the boards' ingestion path")
    ap.add_argument("--speed", type=float, default=None, help="tracking --stream: the playback speed (default 1)")
    ap.add_argument("--screen", default=None, help="tracking --stream: record the screen in this folder")
    ap.add_argument("--no-focus-return", action="store_true", help=NO_FOCUS_HELP)
    a = ap.parse_args(argv)
    if a.stream and not os.path.isdir(os.path.join(REPO_ROOT, "data")):
        raise SystemExit("REFUSED: --stream needs the recordings in data/")
    if a.task is None:
        picked = start_window()
        if picked is None:
            print("Cancelled: no task was started.", flush=True)
            return 1
        a.task = picked
    if a.task == "identification" and (a.stream or a.baseline):
        raise SystemExit("REFUSED: --stream and --baseline are tracking options")
    print(f"THE LIVE APP: {a.task}", flush=True)
    if a.task == "tracking":
        if a.stream:
            return stream(a.stream, a.speed, a.screen)
        return tracking_steps(a.baseline, a.minutes)
    return identification_steps(a.minutes, focus_back=not a.no_focus_return)



# The start window, shown until Start or Cancel: "tracking" or "identification", or None when cancelled.
def start_window():
    r = subprocess.run([sys.executable, "-c", "from pipeline.main import show_start_window; show_start_window()"],
                       cwd=REPO_ROOT, env=dict(os.environ, PYTHONPATH=REPO_ROOT), stdout=subprocess.PIPE, text=True)
    picked = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
    return ((json.loads(picked[-1]) if picked else {}) or {}).get("task")


# The start window's own process: the window until Start or Cancel, then the choice as one JSON line.
def show_start_window() -> None:
    import matplotlib.pyplot as plt
    fig, choice, _w = build_start_window()
    plt.show(block=True)
    print(json.dumps(dict(choice)), flush=True)


# The start window: the task, Start and Cancel.
def build_start_window(headless: bool = False):
    import matplotlib
    if headless:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, RadioButtons
    fig = plt.figure(figsize=(5.6, 3.6))
    if not headless and fig.canvas.manager:
        fig.canvas.manager.set_window_title("TDR-03 live app: choose the task")
    fig.text(0.05, 0.9, "The live app: one task per run", fontsize=13, weight="bold")
    fig.text(0.05, 0.82, "Nothing on the rig moves for either task.", fontsize=9, color="0.3")
    fig.text(0.05, 0.72, "Task", fontsize=10, weight="bold")
    task = RadioButtons(fig.add_axes([0.05, 0.3, 0.42, 0.4], frameon=False), ("Tracking", "Identification"))
    start = Button(fig.add_axes([0.53, 0.07, 0.2, 0.14]), "Start")
    cancel = Button(fig.add_axes([0.76, 0.07, 0.2, 0.14]), "Cancel")
    choice = {}

    # Function go.
    def go(_ev):
        choice.update(task=task.value_selected.lower())
        plt.close(fig)

    start.on_clicked(go)
    cancel.on_clicked(lambda _ev: plt.close(fig))
    return fig, choice, {"task": task, "start": start, "cancel": cancel}



# Tracking's steps in order: find the receivers (T1), record the 60 s baseline (T2, skipped with...
def tracking_steps(baseline: str = None, minutes: float = None) -> int:
    from pipeline.tracking.run import on_the_boards
    from pipeline.tracking.tracker import preflight, print_checks
    if baseline is None:
        ports = ports_text()
        print(f"Receivers: {ports}", flush=True)
        baseline = record_baseline(ports)
    chk = preflight(baseline)
    print_checks(chk)
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed (every line must read ok); tracking did not start")
    return on_the_boards(baseline, minutes)


# The three receivers' ports by MAC address, as RX1=<port>,RX2=<port>,RX3=<port>.
def ports_text() -> str:
    from pipeline.io.boards import receiver_ports
    nodes = receiver_ports()
    return ",".join(f"{k}={v}" for k, v in sorted(nodes.items()))


# The 60 s empty-room capture, recorded now; returns its folder (the one the capture added).
def record_baseline(ports: str) -> str:
    input("BASELINE: nobody walks and the operator sits still for 60 s. Press Enter to start the capture. ")
    root = os.path.join(REPO_ROOT, BASELINES)
    before = set(os.listdir(root)) if os.path.isdir(root) else set()
    cmd = [sys.executable, "-m", "pipeline.io.serial_capture", "--duration", "60", "--out", BASELINES, "--nodes", ports,
           "--reset", "--interval", "10"]
    print("  $ " + " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    if rc != 0:
        raise SystemExit(f"REFUSED: the baseline capture failed (exit {rc}); tracking did not start")
    new = sorted(d for d in set(os.listdir(root)) - before if os.path.isdir(os.path.join(root, d)))
    if len(new) != 1:
        raise SystemExit(f"REFUSED: expected one new capture folder under {BASELINES}, found {new}")
    return os.path.join(BASELINES, new[0])



# Identification on the boards, each walk's path picked on the map (I1 to I9).
def identification_steps(minutes: float = None, focus_back: bool = True) -> int:
    from pipeline.identification.run import on_the_boards
    return on_the_boards(minutes=minutes, focus_back=focus_back)



# NO BOARDS: a recorded walk, <session>/<stem>, tracked in real time.
def stream(spec: str, speed: float = None, screen: str = None, window: bool = True) -> int:
    from pipeline.tracking.run import stream as run_stream
    if "/" not in spec:
        raise SystemExit("REFUSED: --stream <session>/<stem>, e.g. B2/participant_PA5_walk")
    if speed not in (None, 1.0):
        raise SystemExit("REFUSED: --speed must be 1: the app fits each receiver's clock to the packets' arrival times and "
                         "refuses a clock rate far from real time, so a faster stream never starts")
    session, stem = spec.split("/", 1)
    run_stream(session, stem, 1.0, window=window, screen_dir=os.path.abspath(screen) if screen else None)
    return 0



# Function main.
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd, rest = (argv[0], argv[1:]) if argv else (None, [])
    if cmd == "app":
        return app(rest)
    if cmd in ("identify", "identify-recorded", "replay-identify"):
        from pipeline.identification.run import main as identification_main
        return identification_main([cmd] + rest)
    ap = argparse.ArgumentParser(prog="python -m pipeline.main", description="The live app and its steps (see the top "
                                 "of pipeline/main.py).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("app", help="THE LIVE APP: the start window, then tracking's or identification's steps", add_help=False)
    sub.add_parser("ports", help="T1: the receivers' ports by MAC, as RX1=<port>,RX2=<port>,RX3=<port> (for the baseline)")
    p = sub.add_parser("preflight", help="T3: the checks before a board run (opens no port)")
    p.add_argument("--baseline", default=None)
    t = sub.add_parser("track", help="T4 to T11, ON THE BOARDS: tracking (opens the serial ports)")
    t.add_argument("--baseline", required=True, help="this session's 60 s empty-room capture (a folder with RX1-3.bin)")
    t.add_argument("--minutes", type=float, default=None)
    sub.add_parser("identify", help="I1 to I9, ON THE BOARDS: identification (opens the serial ports; --help for its "
                   "options)", add_help=False)
    s = sub.add_parser("stream", help="TR, NO BOARDS: tracking on a recorded walk from data/, streamed in real time")
    s.add_argument("--stream", required=True, help="<session>/<stem>, e.g. B2/participant_PA5_walk")
    s.add_argument("--speed", type=float, default=1.0, help="must be 1 (real time); kept for the app's --speed")
    s.add_argument("--screen", default=None, help="record the screen to an .mp4 in this folder (no window; needs ffmpeg)")
    s.add_argument("--no-window", action="store_true", help="no tracking window (the log and summary only)")
    sub.add_parser("identify-recorded", help="IR, NO BOARDS: a recorded session identified as if live (--help for its "
                   "options)", add_help=False)
    sub.add_parser("replay-identify", help="NO BOARDS: a recorded session through the identification app, as fast as "
                   "possible (--help for its options)", add_help=False)
    a = ap.parse_args(argv)
    if a.cmd == "ports":
        print(ports_text())
        return 0
    if a.cmd == "preflight":
        from pipeline.tracking.tracker import preflight, print_checks
        chk = preflight(a.baseline)
        print_checks(chk)
        return 0 if chk["ALL"] else 1
    if a.cmd == "track":
        from pipeline.tracking.run import on_the_boards
        if not os.path.isdir(a.baseline):
            raise SystemExit("REFUSED: --baseline <dir> is required: this session's own 60 s empty-room capture")
        return on_the_boards(a.baseline, a.minutes)
    return stream(a.stream, a.speed, a.screen, window=not a.no_window)


if __name__ == "__main__":
    sys.exit(main())
