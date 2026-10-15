"""Queue item 12's processes (PREREG.md): one A3 or B2 decode per process (step 1), one real-time video per process (step 2).

    python3 runs/switch_radius_a3b2_2026-10-14/harness.py decode --arm R0 --model final --session B2 --stem participant_PA6_walk
    python3 runs/switch_radius_a3b2_2026-10-14/harness.py render --session B2 --stem participant_PA6_walk

The live app's own replay (`app_replay.replay_inner`, or `session_inner` for a video) after `force_cpu()`, the device asserted
cpu at the start and the end. Arm R0 is the profile `clean_1s_r0`, registered in memory in this process: `clean_1s` with the
switch radius None. Decodes write only into this folder (write guard); videos go to runs/live/renders_K1gf_1s_r0/.

Development evaluation, all data seen. A3's tenth look and B2's eighth (the thesis table's count).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
VIDEOS = J(REPO, "runs", "live", "renders_K1gf_1s_r0")
R0_PROFILE = "clean_1s_r0"
ARMS = {"R1.5": None, "R0": R0_PROFILE}          # the profile given to the app (None: its default, clean_1s)
RADIUS = {"R1.5": 1.5, "R0": None}
LOOK = {"03": "A3's tenth look (the thesis table's count)", "B2": "B2's eighth look (the thesis table's count)"}


def install_guard(opened: dict) -> None:
    """Refuse any write outside this folder (bytecode caches, /dev/null and the temp dirs excepted); record opened paths."""
    tmp = os.path.realpath(tempfile.gettempdir())
    here = os.path.realpath(HERE) + os.sep

    def allowed(p: str) -> bool:
        rp = os.path.realpath(p)
        return (rp.startswith(here) or rp == "/dev/null" or "__pycache__" in rp or rp.startswith(tmp)
                or rp.startswith("/private/var/folders/"))

    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.path.abspath(os.fsdecode(args[0]))
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else None
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            write = (any(ch in mode for ch in "wax+") if mode is not None
                     else bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC)))
            if not (p.endswith((".py", ".pyc")) or "/site-packages/" in p or p.startswith("/opt/")):
                opened.setdefault(p, set()).add("w" if write else "r")
            if write and not allowed(p):
                raise PermissionError(f"Q12 GUARD: write outside {HERE} refused: {p}")
        elif ev in ("os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.symlink", "os.link"):
            if args and isinstance(args[0], (str, bytes, os.PathLike)) and not allowed(os.fsdecode(args[0])):
                raise PermissionError(f"Q12 GUARD: {ev} outside {HERE} refused: {os.fsdecode(args[0])}")
        elif ev == "os.rename":
            for p in args[:2]:
                if isinstance(p, (str, bytes, os.PathLike)) and not allowed(os.fsdecode(p)):
                    raise PermissionError(f"Q12 GUARD: rename outside {HERE} refused: {os.fsdecode(p)}")
    sys.addaudithook(hook)


def cpu_only() -> str:
    from pipeline.constrained import nets
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    dev = str(nets.device())
    if dev != "cpu":
        raise SystemExit(f"STOP: device {dev}, not cpu")
    return dev


def device_now() -> str:
    from pipeline.constrained import nets
    return str(nets.device())


def register_r0():
    """clean_1s_r0: a deep copy of clean_1s with only the switch radius None, in this process's memory."""
    import pipeline.live.final_model as FM
    assert FM.DISPLAY_PROFILE == "clean_1s", FM.DISPLAY_PROFILE
    base = FM.DISPLAY_PROFILES["clean_1s"]
    assert base["sett"]["switch"] == {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}
    prof = copy.deepcopy(base)
    prof["sett"]["switch"]["radius_m"] = None
    prof["source"] = "runs/switch_radius_a3b2_2026-10-14/PREREG.md: clean_1s with the switch radius None (in memory only)"
    FM.DISPLAY_PROFILES[R0_PROFILE] = prof
    return FM


def check_session(s, arm: str) -> dict:
    """Every setting of the built session equals clean_1s's, the switch radius the arm's."""
    import pipeline.live.final_model as FM
    want = copy.deepcopy(FM.DISPLAY_PROFILES["clean_1s"]["sett"])
    want["switch"]["radius_m"] = RADIUS[arm]
    got = {k: s.display.sett.get(k) for k in want}
    assert got == want, {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    assert s.display_candidate == "K1gf", s.display_candidate
    assert s.display_profile == ("clean_1s" if arm == "R1.5" else R0_PROFILE), s.display_profile
    assert s.display.cfg_disp.sd_scale == 3.0, s.display.cfg_disp.sd_scale
    return got


def decode_inner(a) -> int:
    opened = {}
    install_guard(opened)
    dev = cpu_only()
    register_r0()
    import pipeline.live.app_replay as AR
    AR.OUT = J(HERE, a.arm)
    hold = []
    summ = AR.replay_inner(a.model, a.session, a.stem, "start", "causal", False, hold=hold, profile=ARMS[a.arm])
    sett = check_session(hold[0], a.arm)
    dev_end = device_now()
    if dev_end != "cpu":
        raise SystemExit(f"STOP: device {dev_end} at the end, not cpu")
    with open(summ["log"][:-len(".jsonl")] + ".arm.json", "w", encoding="utf-8") as f:
        json.dump({"arm": a.arm, "profile": hold[0].display_profile, "switch": sett["switch"], "device": dev,
                   "device_at_end": dev_end, "model": a.model, "cell": summ["cell"], "look": LOOK[a.session],
                   "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))},
                  f, indent=1)
    return 0


def render_inner(a) -> int:
    dev = cpu_only()
    register_r0()
    import pipeline.live.app_replay as AR
    AR.OUT = J(HERE, "render_logs")
    held, orig = [], AR.replay_inner

    def replay_inner(*args, **kw):                   # session_inner's call, with the session held for the checks
        kw["hold"] = held
        return orig(*args, **kw)
    AR.replay_inner = replay_inner
    rc = AR.session_inner("final", a.session, "start", "causal", True, [a.stem], VIDEOS, None, None, R0_PROFILE)
    assert len(held) == 1, len(held)
    sett = check_session(held[0], "R0")
    dev_end = device_now()
    if dev_end != "cpu":
        raise SystemExit(f"STOP: device {dev_end} at the end, not cpu")
    os.makedirs(J(HERE, "render_logs"), exist_ok=True)
    with open(J(HERE, "render_logs", f"{a.session}__{a.stem}.render.json"), "w", encoding="utf-8") as f:
        json.dump({"profile": held[0].display_profile, "switch": sett["switch"], "device": dev, "device_at_end": dev_end,
                   "rc": rc, "at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=1)
    return rc


def outer(a) -> int:
    sys.path.insert(0, REPO)
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    model = a.model if a.cmd == "decode" else "final"
    env = dict(_env(cell_for(model, a.session)), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1", PYTHONPATH=REPO)
    nice = "10" if a.cmd == "decode" else "19"
    args = ["nice", "-n", nice, sys.executable, os.path.abspath(__file__), a.cmd, "--inner", "--session", a.session,
            "--stem", a.stem] + (["--arm", a.arm, "--model", a.model] if a.cmd == "decode" else [])
    return subprocess.call(args, cwd=REPO, env=env)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decode", "render"])
    ap.add_argument("--arm", choices=sorted(ARMS))
    ap.add_argument("--model", choices=["final", "zeroshot"])
    ap.add_argument("--session", choices=["03", "B2"], required=True)
    ap.add_argument("--stem", required=True)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "decode":
        assert a.arm and a.model, "decode needs --arm and --model"
    if not a.inner:
        return outer(a)
    sys.path.insert(0, REPO)
    return decode_inner(a) if a.cmd == "decode" else render_inner(a)


if __name__ == "__main__":
    sys.exit(main())
