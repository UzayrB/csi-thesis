"""runs/MACHINE_STATE.md for the Third overall chat's cross-room identification run (the Mastermind's rules, 9 Oct):
only the "## Now" paragraph and the top of "## Log" are touched; nobody else's lines are edited; every time is the clock's.

    python3 runs/identify/engine/xroom/ms_xr.py now                          # print the Now paragraph
    python3 runs/identify/engine/xroom/ms_xr.py busy "<text>" <minutes left>  # Now = BUSY (Third overall), from the clock
    python3 runs/identify/engine/xroom/ms_xr.py update "<step>" <minutes left>
    python3 runs/identify/engine/xroom/ms_xr.py log "<event>"
    python3 runs/identify/engine/xroom/ms_xr.py quiet "<what ended>"
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
PATH = os.path.join(REPO, "runs", "MACHINE_STATE.md")
TAG = "**BUSY (Third overall), from "
HEAD = "Identification cross-room evaluation on engine v4 (Uzayr's go, prompt of 9 Oct)."


def _split(text: str):
    a = text.index("## Now")
    b = text.index("## Log")
    return text[:a], text[a:b], text[b:]


def _write(head: str, now: str, log: str) -> None:
    tmp = PATH + ".xr.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(head + now + log)
    os.replace(tmp, PATH)


def _now_block(par: str) -> str:
    return f"## Now\n\n{par}\n\n"


def _eta(minutes: float) -> str:
    return time.strftime("%H:%M", time.localtime(time.time() + 60 * float(minutes)))


def busy(step: str, minutes: float) -> None:
    head, _now, log = _split(open(PATH, encoding="utf-8").read())
    par = (f"{TAG}{time.strftime('%H:%M')} SAST, {time.strftime('%d %b')}.** {HEAD} Now: {step} "
           f"ETA for QUIET about {_eta(minutes)}. One caffeinate held.")
    _write(head, _now_block(par), log)


def update(step: str, minutes: float) -> None:
    head, now, log = _split(open(PATH, encoding="utf-8").read())
    i = now.find(TAG)
    if i < 0:                                   # not ours: never overwrite someone else's Now
        print("Now paragraph is not Third overall's; not updated", file=sys.stderr)
        return
    since = now[i:now.index(".**", i) + 3]
    _write(head, _now_block(f"{since} {HEAD} Now: {step} ETA for QUIET about {_eta(minutes)}. One caffeinate held."), log)


def log_line(msg: str) -> None:
    head, now, log = _split(open(PATH, encoding="utf-8").read())
    first, rest = log.split("\n", 1)
    rest = rest.lstrip("\n")
    _write(head, now, first + "\n\n" + f"- {time.strftime('%d %b %H:%M')}: Third overall {msg}\n" + rest)


def quiet(what: str) -> None:
    head, now, log = _split(open(PATH, encoding="utf-8").read())
    if TAG not in now:
        print("Now paragraph is not Third overall's; QUIET not written", file=sys.stderr)
        return
    _write(head, _now_block(f"**QUIET.** Nothing heavy is running ({time.strftime('%d %b %H:%M')}: {what})."), log)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "now":
        print(_split(open(PATH, encoding="utf-8").read())[1])
    elif cmd == "busy":
        busy(sys.argv[2], float(sys.argv[3]))
    elif cmd == "update":
        update(sys.argv[2], float(sys.argv[3]))
    elif cmd == "log":
        log_line(sys.argv[2])
    elif cmd == "quiet":
        quiet(sys.argv[2])
    else:
        raise SystemExit(cmd)
