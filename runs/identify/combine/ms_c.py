"""runs/MACHINE_STATE.md for the Third overall chat's combine run (Uzayr's prompt, received at or before 10 Oct 00:59:54; the file's own format; every write read back):
only the "## Now" paragraph and the top of "## Log" are touched; nobody else's lines are edited; every time is the clock's.

    python3 runs/identify/combine/ms_c.py now                          # print the Now paragraph
    python3 runs/identify/combine/ms_c.py busy "<text>" <minutes left>  # Now = BUSY (Third overall), from the clock
    python3 runs/identify/combine/ms_c.py update "<step>" <minutes left>
    python3 runs/identify/combine/ms_c.py log "<event>"
    python3 runs/identify/combine/ms_c.py quiet "<what ended>"
    python3 runs/identify/combine/ms_c.py queue "<entry>"               # one line under "## Queue" (Uzayr's prompt)
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PATH = os.path.join(REPO, "runs", "MACHINE_STATE.md")
TAG = "**BUSY (Third overall), from "
HEAD = "Identification combine run, exploratory development, all data seen (Uzayr's prompt of 10 Oct, about 07:45)."


def _split(text: str):
    a = text.index("## Now")
    b = text.index("## Log")
    return text[:a], text[a:b], text[b:]


def _write(head: str, now: str, log: str) -> None:
    tmp = PATH + ".c.tmp"
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


def queue(entry: str) -> None:
    """Uzayr's prompt asks for the queue entry: one line right under the Queue heading (replacing this run's earlier
    line), nothing else touched."""
    text = open(PATH, encoding="utf-8").read()
    i = text.index("## Queue")
    j = text.index("\n", i) + 1
    tag = "- Third overall (combine):"
    body = "\n".join(line for line in text[j:].split("\n") if not line.startswith(tag)).lstrip("\n")
    tmp = PATH + ".c.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text[:j] + "\n" + f"{tag} {time.strftime('%d %b %H:%M')}: {entry}\n\n" + body)
    os.replace(tmp, PATH)

def landed(text: str) -> None:
    """Read the file back and stop with an error if `text` is not in it (every write is confirmed)."""
    if text not in open(PATH, encoding="utf-8").read():
        raise SystemExit(f"MACHINE_STATE write NOT confirmed: {text[:80]}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "now":
        print(_split(open(PATH, encoding="utf-8").read())[1])
    elif cmd == "busy":
        busy(sys.argv[2], float(sys.argv[3]))
        landed(f"{TAG}")
    elif cmd == "update":
        update(sys.argv[2], float(sys.argv[3]))
        landed(sys.argv[2])
    elif cmd == "log":
        log_line(sys.argv[2])
        landed(sys.argv[2])
    elif cmd == "quiet":
        quiet(sys.argv[2])
        landed(f"**QUIET.** Nothing heavy is running ({time.strftime('%d %b')}")
    elif cmd == "queue":
        queue(sys.argv[2])
        landed(sys.argv[2])
    else:
        raise SystemExit(cmd)
