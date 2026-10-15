"""runs/MACHINE_STATE.md for the Third overall chat's best-model run (Uzayr's prompt, received at or before 10 Oct 00:59:54; the file's own format; every write read back):
only the "## Now" paragraph and the top of "## Log" are touched; nobody else's lines are edited; every time is the clock's.

    python3 runs/identify/best/ms_b.py now                          # print the Now paragraph
    python3 runs/identify/best/ms_b.py busy "<text>" <minutes left>  # Now = BUSY (Third overall), from the clock
    python3 runs/identify/best/ms_b.py update "<step>" <minutes left>
    python3 runs/identify/best/ms_b.py log "<event>"
    python3 runs/identify/best/ms_b.py quiet "<what ended>"
    python3 runs/identify/best/ms_b.py queue "<entry>"               # one line under "## Queue" (Uzayr's prompt)
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PATH = os.path.join(REPO, "runs", "MACHINE_STATE.md")
TAG = "**BUSY (Third overall), from "
HEAD = "Identification best-model run, exploratory development, all data seen; selection on A3 and B2 (Uzayr's prompt of 10 Oct, about 08:22)."


def _split(text: str):
    a = text.index("## Now")
    b = text.index("## Log")
    return text[:a], text[a:b], text[b:]


def _write(head: str, now: str, log: str) -> None:
    tmp = PATH + ".b.tmp"
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


def _second_overall_alive() -> bool:
    """The Mastermind (10 Oct, about 08:4x and 09:1x): never QUIET while Second Overall's display adoption runs: any process
    whose command line contains runs/clean_display_2026-10-10, pipeline.live or pipeline/live. When in doubt (pgrep fails),
    treat it as alive."""
    import subprocess
    for pat in ("runs/clean_display_2026-10-10", "pipeline\\.live", "pipeline/live"):
        r = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
        if r.returncode not in (0, 1) or r.stdout.strip():
            return True
    return False


def quiet(what: str) -> str:
    head, now, log = _split(open(PATH, encoding="utf-8").read())
    if TAG not in now:
        print("Now paragraph is not Third overall's; QUIET not written", file=sys.stderr)
        return ""
    if _second_overall_alive():
        step = (f"no Third overall block running ({what}); Second Overall's display adoption is running "
                f"(runs/clean_display_2026-10-10), so not QUIET.")
        update(step, max(1.0, (time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 12:15", "%Y-%m-%d %H:%M"))
                               - time.time()) / 60))
        return step
    _write(head, _now_block(f"**QUIET.** Nothing heavy is running ({time.strftime('%d %b %H:%M')}: {what})."), log)
    return f"**QUIET.** Nothing heavy is running ({time.strftime('%d %b')}"


def queue(entry: str) -> None:
    """Uzayr's prompt asks for the queue entry: one line right under the Queue heading (replacing this run's earlier
    line), nothing else touched."""
    text = open(PATH, encoding="utf-8").read()
    i = text.index("## Queue")
    j = text.index("\n", i) + 1
    tag = "- Third overall (best model):"
    body = "\n".join(line for line in text[j:].split("\n") if not line.startswith(tag)).lstrip("\n")
    tmp = PATH + ".b.tmp"
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
        t = quiet(sys.argv[2])
        if t:
            landed(t)
    elif cmd == "queue":
        queue(sys.argv[2])
        landed(sys.argv[2])
    else:
        raise SystemExit(cmd)
