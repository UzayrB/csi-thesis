# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The start window (pick Tracking or Identification), then that task's steps in order: find the boards...

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TASKS = ("tracking", "identification")
BASELINES = os.path.join("runs", "live", "baselines")
MAIN = ["-m", "pipeline.live.RunLive.main"]



# The start dialog's window: the task, Start and Cancel.
def build_dialog(headless: bool = False):
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


# The start dialog, shown until Start or Cancel: {"task"}, or None when cancelled or closed.
def dialog():
    import json
    r = subprocess.run([sys.executable, "-c", "from pipeline.live.RunLive.start_dialog import show_dialog; show_dialog()"],
                       cwd=REPO_ROOT, env=dict(os.environ, PYTHONPATH=REPO_ROOT), stdout=subprocess.PIPE, text=True)
    picked = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
    return (json.loads(picked[-1]) if picked else {}) or None


# The start dialog's own process: the window until Start or Cancel, then the choice as one JSON line.
def show_dialog() -> None:
    import json
    import matplotlib.pyplot as plt
    fig, choice, _w = build_dialog()
    plt.show(block=True)
    print(json.dumps(dict(choice)), flush=True)



# One step, as its own process in the repository root, with this environment.
def call(cmd: list) -> int:
    print("  $ " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=REPO_ROOT)


# The three receivers' ports by MAC address (main.py ports, the MACs from boards.json), as...
def receiver_ports() -> str:
    return subprocess.run([sys.executable, *MAIN, "ports"], cwd=REPO_ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()


# The 60 s empty-room capture; returns its folder (the one the capture added).
def capture_baseline() -> str:
    ports = receiver_ports()
    print(f"Receivers: {ports}", flush=True)
    input("BASELINE: nobody walks and the operator sits still for 60 s. Press Enter to start the capture. ")
    root = os.path.join(REPO_ROOT, BASELINES)
    before = set(os.listdir(root)) if os.path.isdir(root) else set()
    rc = call([sys.executable, "-m", "pipeline.io.RunLive.serial_capture", "--duration", "60", "--out", BASELINES, "--nodes", ports,
               "--reset", "--interval", "10"])
    if rc != 0:
        raise SystemExit(f"REFUSED: the baseline capture failed (exit {rc}); tracking did not start")
    new = sorted(d for d in set(os.listdir(root)) - before if os.path.isdir(os.path.join(root, d)))
    if len(new) != 1:
        raise SystemExit(f"REFUSED: expected one new capture folder under {BASELINES}, found {new}")
    return os.path.join(BASELINES, new[0])


# Tracking: the baseline (recorded now unless --baseline), the pre-flight, then tracking on the boards; or...
def tracking(a) -> int:
    py = sys.executable
    if a.stream:
        return call([py, *MAIN, "stream", "--stream", a.stream]
                    + (["--speed", str(a.speed)] if a.speed is not None else []) + (["--screen", a.screen] if a.screen else []))
    base = a.baseline or capture_baseline()
    rc = call([py, *MAIN, "preflight", "--baseline", base])
    if rc != 0:
        raise SystemExit("REFUSED: the pre-flight failed (every line must read ok); tracking did not start")
    return call([py, *MAIN, "track", "--baseline", base] + (["--minutes", str(a.minutes)] if a.minutes else []))


# Identification on the boards, with the path pop-up.
def identification(a) -> int:
    return call([sys.executable, *MAIN, "identify", "--popup"]
                + (["--minutes", str(a.minutes)] if a.minutes else []) + (["--no-focus-return"] if a.no_focus_return else []))


FLOWS = {"tracking": tracking, "identification": identification}


# Python -m pipeline.live.RunLive.main app: the start window, then the chosen task's steps.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline.live.RunLive.main app", description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--task", choices=TASKS, default=None, help="skip the dialog: the task to run")
    ap.add_argument("--minutes", type=float, default=None, help="stop after this many minutes (default: until q)")
    ap.add_argument("--baseline", default=None, help="tracking: an earlier 60 s empty-room capture, instead of a new one")
    ap.add_argument("--stream", default=None, help="tracking: a recorded <session>/<stem> through the boards' ingestion path")
    ap.add_argument("--speed", type=float, default=None, help="tracking --stream: the playback speed (default 1)")
    ap.add_argument("--screen", default=None, help="tracking --stream: record the screen in this folder")
    ap.add_argument("--no-focus-return", action="store_true",
                    help="identification: do not give the keyboard to the Terminal at Done, nor the window back after SPACE")
    a = ap.parse_args(argv)
    if a.stream and not os.path.isdir(os.path.join(REPO_ROOT, "data")):
        raise SystemExit("REFUSED: --stream needs the recordings in data/")
    if a.task is None:
        ch = dialog()
        if ch is None:
            print("Cancelled: no task was started.", flush=True)
            return 1
        a.task = ch["task"]
    if a.task == "identification" and (a.stream or a.baseline):
        raise SystemExit("REFUSED: --stream and --baseline are tracking options")
    print(f"THE LIVE APP: {a.task}", flush=True)
    return FLOWS[a.task](a)
