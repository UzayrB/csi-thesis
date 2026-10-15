"""The head-offset test's replay harness (PREREG.md sections 1 to 3): one rotation recording, one arm, per process.

    python3 runs/head_offset_2026-10-14/ho_harness.py replay --rot B1 --stem participant_PA5_walk --arm 0.875 --out logs

The live app's own tracking session (`final_model.FinalTrackingSession`) under the shipped clean display profile, the pooled
display (no display head), on the rotation's all-0.5 s cell (`f05r_*`, registered by runs/a3_clean_0p5_2026-10-09/reg.py), fed
by the 9 Oct dot side's event loop (`runs/a3_clean_2026-10-08/dot_harness.feed`: semi mode, the causal clock). The ONLY change
is the display head offset, set on the built display's `sett["head_offset_s"]` in this process; every held setting is
asserted on the built session. Logs are written by `app_replay.Logger` in its own format, under this folder only (the write
guard refuses anything else), with every opened file recorded.

Development evaluation, all data seen.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DOT = J(REPO, "runs", "a3_clean_2026-10-08")
REGISTER = J(REPO, "runs", "a3_clean_0p5_2026-10-09", "reg.py")
ARMS = (0.75, 0.875, 1.0)
CELLS = {"B1": "f05r_0102_to_B1", "A2": "f05r_01B1_to_02", "A1": "f05r_02B1_to_01"}
SESSION = {"B1": "B1", "A2": "02", "A1": "01"}
STEMS = ["participant_PA5_walk", "participant_PA1_walk", "participant_PA2_walk", "participant_PA3_walk",
         "participant_PA4_walk", "participant_PA6_walk"]
SWITCH_A = {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}


def arm_name(arm: float) -> str:
    return f"o{arm:g}"


def install_guard(opened: dict) -> None:
    """lock_side.install_guard's hook with this folder as the only writable place: refuse any write elsewhere (bytecode
    caches, /dev/null and the temp dirs excepted) and record every opened path."""
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
                raise PermissionError(f"HO GUARD: write outside {HERE} refused: {p}")
        elif ev in ("os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.symlink", "os.link"):
            if args and isinstance(args[0], (str, bytes, os.PathLike)) and not allowed(os.fsdecode(args[0])):
                raise PermissionError(f"HO GUARD: {ev} outside {HERE} refused: {os.fsdecode(args[0])}")
        elif ev == "os.rename":
            for p in args[:2]:
                if isinstance(p, (str, bytes, os.PathLike)) and not allowed(os.fsdecode(p)):
                    raise PermissionError(f"HO GUARD: rename outside {HERE} refused: {os.fsdecode(p)}")
    sys.addaudithook(hook)


GEOMETRY_SIDECAR = r".*/data/room_A/session_03/participant_[^/]+_walk\.gt\.json"


def forbidden_inputs(paths) -> tuple:
    """(forbidden, geometry sidecars): opened paths that name session 03 (A3) or B2 (the 9 Oct test, `lock_side.a3_inputs`,
    plus B2's data folder), less A3's walk sidecars read for the line geometry, the 9 Oct documented exception
    (PREREG_ADDENDUM_2), which holds only while `lock_side.geometry_from_session_01()` is true."""
    import re
    sys.path.insert(0, DOT)
    from lock_side import a3_inputs
    from pipeline.live.app_score import DATA
    b2 = os.path.realpath(DATA["B2"]) + os.sep
    flagged = sorted(set(a3_inputs(paths)) | {p for p in paths if os.path.realpath(p).startswith(b2)})
    side = [p for p in flagged if re.fullmatch(GEOMETRY_SIDECAR, p)]
    return [p for p in flagged if p not in side], side


def register() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ho_register", REGISTER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.register()


def build_session(rot: str, stem: str, arm: float, comps):
    """The app's session as shipped (clean profile, pooled display), then the arm's head offset on its display."""
    import pipeline.io.windows as W
    import pipeline.live.display as LD
    import pipeline.live.final_model as FM
    PC, c, pieces, pool, terms, G0 = comps
    session = SESSION[rot]
    assert c["test"] == session, (c["test"], session)
    assert FM.DISPLAY_PROFILE == "clean", FM.DISPLAY_PROFILE
    sdir = PC.raw_dir(session)
    s = FM.FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"],
                                test=(session,), reader_tag=c["reader_tag"], pieces=pieces,
                                baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)), end_head=None,
                                display_candidate=None, mode="semi")
    d = s.display
    # every held setting, as shipped (PREREG section 1), BEFORE the arm is set
    held = {"candidate": s.display_candidate, "anchor": d.sett.get("anchor"), "path_lag_extra": d.sett.get("path_lag_extra"),
            "prior_f": d.sett.get("prior_f"), "shift_w": d.sett.get("shift_w"), "head_offset_s": d.sett.get("head_offset_s"),
            "switch": {k: (d.sett.get("switch") or {}).get(k) for k in SWITCH_A}, "sd": d.cfg_disp.sd_scale,
            "entry": d.opts.get("entry"), "entry_window_m": d.opts.get("entry_window_m"), "end_head": s._end,
            "cap_m": LD.DISPLAY_CAP_M_PER_WINDOW, "latency_s": LD.LATENCY_S, "fps": LD.FPS}
    want = {"candidate": "K1gf", "anchor": "glide_first", "path_lag_extra": 1, "prior_f": 0.5, "shift_w": 1.0,
            "head_offset_s": 0.75, "switch": SWITCH_A, "sd": 3.0, "entry": "soft", "entry_window_m": 1.0, "end_head": None,
            "cap_m": 0.8, "latency_s": 2.0, "fps": 10}
    assert held == want, {k: (held[k], want[k]) for k in want if held[k] != want[k]}
    d.sett["head_offset_s"] = float(arm)
    assert d.sett["head_offset_s"] == float(arm)
    return s, sdir, dict(held, head_offset_s=float(arm), end_head="pooled (no display head)")


def write_log(log, s, out_dir: str, session: str, stem: str, extra: dict) -> str:
    os.makedirs(out_dir, exist_ok=True)
    base = J(out_dir, f"{session}__{stem}")
    if os.path.exists(base + ".jsonl"):
        raise SystemExit(f"REFUSED: {base}.jsonl exists")
    with open(base + ".jsonl", "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    summ = {"session": session, "stem": stem, "mode": "semi", "clock": "causal", "display_candidate": s.display_candidate,
            "n_committed": len(s.decisions), "n_locks": len(log.locks), "n_frames": log.n_frames,
            "n_lock_changes_after_first": len(s.lock_changes), "stats": s.stats, **extra,
            "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(base + ".summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=str)
    return base + ".jsonl"


def replay_inner(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, DOT)
    opened = {}
    install_guard(opened)
    register()
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from dot_harness import APP_VARIANT, feed
    from pipeline.live.final_model import _components
    t0 = time.time()
    comps = _components(CELLS[a.rot], APP_VARIANT)
    s, sdir, held = build_session(a.rot, a.stem, a.arm, comps)
    log = feed(s, sdir, a.stem)
    bad, side = forbidden_inputs(list(opened))
    if bad:
        raise SystemExit(f"STOP: inputs naming session 03 or B2 were opened: {bad[:5]}")
    from lock_side import geometry_from_session_01
    geo = bool(geometry_from_session_01()) if side else None
    if side and not geo:
        raise SystemExit("STOP: A3's sidecars were opened and the line geometry is not session 01's alone")
    path = write_log(log, s, J(HERE, a.out, arm_name(a.arm)), SESSION[a.rot], a.stem,
                     {"rotation": a.rot, "cell": CELLS[a.rot], "arm_head_offset_s": a.arm, "held": held,
                      "minutes": round((time.time() - t0) / 60.0, 2), "forbidden_inputs": bad,
                      "a3_sidecars_opened_for_geometry": [os.path.relpath(p, REPO) for p in side],
                      "geometry_equals_session_01_alone": geo,
                      "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))})
    print(f"[{time.strftime('%H:%M:%S')}] {a.rot} {a.stem} {arm_name(a.arm)}: {len(s.decisions)} committed, "
          f"{log.n_frames} frames -> {os.path.relpath(path, REPO)}", flush=True)
    return 0


def replay_outer(a) -> int:
    sys.path.insert(0, REPO)
    register()
    from pipeline.live.final_model import _env
    env = dict(_env(CELLS[a.rot]), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--rot", a.rot,
                            "--stem", a.stem, "--arm", repr(a.arm), "--out", a.out], cwd=REPO, env=env)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay"])
    ap.add_argument("--rot", choices=sorted(CELLS), required=True)
    ap.add_argument("--stem", choices=STEMS, required=True)
    ap.add_argument("--arm", type=float, required=True)
    ap.add_argument("--out", default="logs")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    assert a.arm in ARMS, a.arm
    return replay_inner(a) if a.inner else replay_outer(a)


if __name__ == "__main__":
    sys.exit(main())
