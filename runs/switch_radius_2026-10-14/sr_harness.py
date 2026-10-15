"""The switch-radius test's replay harness (PREREG.md sections 1 to 3): one rotation recording, one arm, per process.

    python3 runs/switch_radius_2026-10-14/sr_harness.py replay --rot B1 --stem participant_PA3_walk --arm R0

The head-offset test's harness (`runs/head_offset_2026-10-14/ho_harness.py`: the live app's own tracking session, the
pooled display, the rotation's all-0.5 s cell, the 9 Oct dot side's event loop, the input guard), on the shipped
`clean_1s` profile. Arm R1.5 changes nothing; arm R0 sets the built display's switch `radius_m` to None in this process.
Every held setting is asserted on the built session; the device (`nets.device()` after `force_cpu()`) is recorded and must
be the CPU. Writes are refused outside this folder.

Development evaluation, all data seen.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HO = J(REPO, "runs", "head_offset_2026-10-14")
DOT = J(REPO, "runs", "a3_clean_2026-10-08")
sys.path.insert(0, HO)
import ho_harness as H  # noqa: E402

ARMS = {"R1.5": 1.5, "R0": None}
CELLS, SESSION, STEMS = H.CELLS, H.SESSION, H.STEMS
SWITCH_SHIPPED = {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}


def install_guard(opened: dict) -> None:
    """ho_harness.install_guard with THIS folder as the only writable place."""
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
                raise PermissionError(f"SR GUARD: write outside {HERE} refused: {p}")
        elif ev in ("os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.symlink", "os.link"):
            if args and isinstance(args[0], (str, bytes, os.PathLike)) and not allowed(os.fsdecode(args[0])):
                raise PermissionError(f"SR GUARD: {ev} outside {HERE} refused: {os.fsdecode(args[0])}")
        elif ev == "os.rename":
            for p in args[:2]:
                if isinstance(p, (str, bytes, os.PathLike)) and not allowed(os.fsdecode(p)):
                    raise PermissionError(f"SR GUARD: rename outside {HERE} refused: {os.fsdecode(p)}")
    sys.addaudithook(hook)


def build_session(rot: str, stem: str, arm: str, comps):
    """The app's session as shipped (clean_1s, pooled display), then the arm's switch radius on its display."""
    import pipeline.io.windows as W
    import pipeline.live.display as LD
    import pipeline.live.final_model as FM
    PC, c, pieces, pool, terms, G0 = comps
    session = SESSION[rot]
    assert c["test"] == session, (c["test"], session)
    assert FM.DISPLAY_PROFILE == "clean_1s", FM.DISPLAY_PROFILE
    sdir = PC.raw_dir(session)
    s = FM.FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"],
                                test=(session,), reader_tag=c["reader_tag"], pieces=pieces,
                                baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)), end_head=None,
                                display_candidate=None, mode="semi")
    d = s.display
    held = {"candidate": s.display_candidate, "anchor": d.sett.get("anchor"), "path_lag_extra": d.sett.get("path_lag_extra"),
            "prior_f": d.sett.get("prior_f"), "shift_w": d.sett.get("shift_w"), "head_offset_s": d.sett.get("head_offset_s"),
            "switch": {k: (d.sett.get("switch") or {}).get(k) for k in SWITCH_SHIPPED}, "sd": d.cfg_disp.sd_scale,
            "entry": d.opts.get("entry"), "entry_window_m": d.opts.get("entry_window_m"), "end_head": s._end,
            "cap_m": LD.DISPLAY_CAP_M_PER_WINDOW, "latency_s": LD.LATENCY_S, "fps": LD.FPS}
    want = {"candidate": "K1gf", "anchor": "glide_first", "path_lag_extra": 1, "prior_f": 0.5, "shift_w": 1.0,
            "head_offset_s": 1.0, "switch": SWITCH_SHIPPED, "sd": 3.0, "entry": "soft", "entry_window_m": 1.0,
            "end_head": None, "cap_m": 0.8, "latency_s": 2.0, "fps": 10}
    assert held == want, {k: (held[k], want[k]) for k in want if held[k] != want[k]}
    d.sett["switch"] = dict(d.sett["switch"], radius_m=ARMS[arm])        # a copy: the profile's dict is not touched
    assert d.sett["switch"]["radius_m"] == ARMS[arm]
    assert {k: v for k, v in d.sett["switch"].items() if k != "radius_m"} == \
           {k: v for k, v in SWITCH_SHIPPED.items() if k != "radius_m"}
    held = dict(held, switch=dict(d.sett["switch"]), end_head="pooled (no display head)")
    return s, sdir, held


def replay_inner(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, DOT)
    opened = {}
    install_guard(opened)
    H.register()
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.constrained.nets import device
    dev = str(device())
    if dev != "cpu":
        raise SystemExit(f"STOP: device {dev}, not cpu")
    from dot_harness import APP_VARIANT, feed
    from pipeline.live.final_model import _components
    t0 = time.time()
    comps = _components(CELLS[a.rot], APP_VARIANT)
    s, sdir, held = build_session(a.rot, a.stem, a.arm, comps)
    log = feed(s, sdir, a.stem)
    dev_end = str(device())
    if dev_end != "cpu":
        raise SystemExit(f"STOP: device {dev_end} at the end, not cpu")
    bad, side = H.forbidden_inputs(list(opened))
    if bad:
        raise SystemExit(f"STOP: inputs naming session 03 or B2 were opened: {bad[:5]}")
    from lock_side import geometry_from_session_01
    geo = bool(geometry_from_session_01()) if side else None
    if side and not geo:
        raise SystemExit("STOP: A3's sidecars were opened and the line geometry is not session 01's alone")
    path = H.write_log(log, s, J(HERE, "logs", a.arm), SESSION[a.rot], a.stem,
                       {"rotation": a.rot, "cell": CELLS[a.rot], "arm": a.arm, "switch_radius_m": ARMS[a.arm],
                        "device": dev, "device_at_end": dev_end, "held": held,
                        "minutes": round((time.time() - t0) / 60.0, 2), "forbidden_inputs": bad,
                        "a3_sidecars_opened_for_geometry": [os.path.relpath(p, REPO) for p in side],
                        "geometry_equals_session_01_alone": geo,
                        "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items()
                                         if "w" in m and p.startswith(REPO))})
    print(f"[{time.strftime('%H:%M:%S')}] {a.rot} {a.stem} {a.arm} ({dev}): {len(s.decisions)} committed, "
          f"{log.n_frames} frames -> {os.path.relpath(path, REPO)}", flush=True)
    return 0


def replay_outer(a) -> int:
    sys.path.insert(0, REPO)
    H.register()
    from pipeline.live.final_model import _env
    env = dict(_env(CELLS[a.rot]), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--rot", a.rot,
                            "--stem", a.stem, "--arm", a.arm], cwd=REPO, env=env)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay"])
    ap.add_argument("--rot", choices=sorted(CELLS), required=True)
    ap.add_argument("--stem", choices=STEMS, required=True)
    ap.add_argument("--arm", choices=sorted(ARMS), required=True)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    return replay_inner(a) if a.inner else replay_outer(a)


if __name__ == "__main__":
    sys.exit(main())
