"""runs/MACHINE_STATE.md, the way Overall keeps it (its message of 9 Oct, about 07:35):
  - a log line goes at the TOP of "## Log", as "- 09 Oct HH:MM: Second Overall ...", the time from the clock;
  - at the start of a run the "## Now" paragraph is set to BUSY (Second Overall) with the plan and ETA; at the end, QUIET;
  - nobody else's lines are ever edited or removed.

    python3 runs/a3_clean_2026-10-08/machine_state.py is-quiet          # exit 0 only if the Now paragraph says QUIET
    python3 runs/a3_clean_2026-10-08/machine_state.py busy "<plan and ETA>"
    python3 runs/a3_clean_2026-10-08/machine_state.py log "<what happened>"
    python3 runs/a3_clean_2026-10-08/machine_state.py update "<current step and ETA>"   # the Now paragraph only
    python3 runs/a3_clean_2026-10-08/machine_state.py quiet "<what ended>"
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(REPO, "runs", "MACHINE_STATE.md")


def _split(text: str):
    a = text.index("## Now")
    b = text.index("## Log")
    return text[:a], text[a:b], text[b:]


def now_paragraph() -> str:
    _h, now, _l = _split(open(PATH, encoding="utf-8").read())
    return now


def is_quiet() -> bool:
    return "**QUIET" in now_paragraph()


def _write(head: str, now: str, log: str) -> None:
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(head + now + log)
    os.replace(tmp, PATH)


def log_line(msg: str) -> None:
    head, now, log = _split(open(PATH, encoding="utf-8").read())
    first, rest = log.split("\n", 1)                    # "## Log" and what follows
    rest = rest.lstrip("\n")
    line = f"- {time.strftime('%d %b %H:%M')}: Second Overall {msg}\n"
    _write(head, now, first + "\n\n" + line + rest)


def current_busy_since() -> str:
    now = now_paragraph()
    i = now.find("**BUSY (Second Overall), from ")
    return now[i + 2:now.index("**", i + 2)] if i >= 0 else None


#: measured minutes per step at 6 to 7 processes (Mastermind, 9 Oct 09:30: the file must use the measured times):
#: a Room A two-variant replay takes about 20 to 25 min on these cores, so a stage is about 80 min (stage 3, seven
#: variants, about 90); the config commit plus the A3 decode and its score about 45 min
STAGE_MIN = {1: 56, 2: 69, 3: 85, 4: 70, 5: 65}             #: measured for 1 to 3 (Mastermind, 12:40), estimated for 4 and 5
TAIL_MIN = 50


def _stage_start(n: int):
    """The time the stage's first job started (dot/logs/driver.log), today; None before it starts."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dot", "logs", "driver.log")
    try:
        for ln in open(p, encoding="utf-8"):
            if f"] start s{n}_" in ln:
                hh, mm, ss = (int(x) for x in ln[1:9].split(":"))
                t = time.localtime()
                return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, hh, mm, ss, 0, 0, -1))
    except OSError:
        return None
    return None


def eta_minutes_from(msg: str):
    """(base time, minutes) for the step the message names."""
    import re
    m = re.search(r"stage (\d) of 5", msg)
    if m:
        n = int(m.group(1))
        return (_stage_start(n) or time.time()), sum(STAGE_MIN[k] for k in range(n, 6)) + TAIL_MIN
    if "five stages are done" in msg:
        return time.time(), TAIL_MIN + 15
    if "offline gates" in msg:
        return time.time(), 10 + sum(STAGE_MIN.values()) + TAIL_MIN
    if "P1" in msg:
        return time.time(), 20 + 10 + sum(STAGE_MIN.values()) + TAIL_MIN
    return None, None


def live_figures(msg: str) -> str:
    """The process count from dot/PROCS (the run's current value) and the ETA recomputed from the step named."""
    import re
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dot", "PROCS")
    try:
        procs = int(open(p, encoding="utf-8").read().split()[0])
    except (OSError, ValueError, IndexError):
        procs = None
    if procs:
        msg = re.sub(r"(at most |, )(\d) niced", lambda m: f"{m.group(1)}{procs} niced", msg)
        msg = re.sub(r"\((\d+) niced", f"({procs} niced", msg)
        msg = re.sub(r"(\d) niced CPU processes", f"{procs} niced CPU processes", msg)
    msg = msg.replace("about 75 min each", "about 80 min each").replace("about 65 min each", "about 80 min each")
    base, mins = eta_minutes_from(msg)
    try:                                   # pauses since the run's stages began (dot/ETA_EXTRA_MIN): Mastermind's 36.5 min
        extra = float(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dot", "ETA_EXTRA_MIN"),
                           encoding="utf-8").read().split()[0])
    except (OSError, ValueError, IndexError):
        extra = 0.0
    if base is not None:
        mins = mins + extra
        eta = time.strftime("%H:%M", time.localtime(base + 60 * mins))
        msg = re.sub(r"ETA for QUIET about \d\d:\d\d\)?", f"ETA for QUIET about {eta}", msg)
    return msg


def set_now(state: str, msg: str) -> None:
    msg = live_figures(msg)
    head, _now, log = _split(open(PATH, encoding="utf-8").read())
    _write(head, f"## Now\n\n**{state}** {msg}\n\n", log)


def main(argv=None) -> int:
    a = (argv or sys.argv)[1:]
    if a[0] == "is-quiet":
        return 0 if is_quiet() else 1
    if a[0] == "is-mine":
        return 0 if current_busy_since() else 1
    if a[0] == "busy":
        set_now(f"BUSY (Second Overall), from {time.strftime('%H:%M')} SAST, {time.strftime('%d %b')}.", a[1])
        log_line(f"starts: {a[1]}")
    elif a[0] == "log":
        log_line(a[1])
    elif a[0] == "update":
        since = current_busy_since()
        assert since, "the Now paragraph is not this chat's BUSY line"
        set_now(since, a[1])
    elif a[0] == "quiet":
        set_now("QUIET.", f"Nothing heavy is running ({time.strftime('%d %b %H:%M')}: {a[1]}).")
        log_line(f"ends, QUIET: {a[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
