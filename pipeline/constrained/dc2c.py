"""dc2c. The DC2 run, one Room B session at a time. POST HOC TOOLING NOTE, 2026-09-28.

WHY THIS EXISTS. Found on 2026-09-28, after both days of Room B data existed and before any model had
run on them: `dc2_run.do_infer` writes each head's posteriors to ONE file named by the head tag alone
(`{tag}_g{cells}_e{E}_s{seed}_full.npz`), rewriting it once per Room B session. With two sessions the
second overwrites the first. `pairing_emissions` then reads that one file for every session, taking
its recordings' stems and loading each stem's labels from the session being decoded. B1 and B2 hold
recordings with the same names, so day 1 would have been decoded on day 2's radio against day 1's
labels. `dc2_verify_run` compares pass lists only, which are identical across the two days, so it
could not have seen this. Every earlier run (the stand-ins, the hardware check) had ONE Room B
session, which is why it never showed.

THE CORRECTION changes no model, decision, threshold or arm. The frozen steps (view, cut, features,
infer, decode) run once per Room B session, exactly as the validated one-session stand-in ran them,
each in its own folder `<base>/by_session/<session>/`. The two decodes are merged into `<base>/
decode.json`, and the report, the verifier and the scorer lock read that as before. `dc2b`'s three
corrections stay installed underneath. A guard checks that every posterior file holds only its own
session's recordings, recorded on that session's own date.

All DC2 files, `dc2b` included, are pinned, so none is edited: this module wraps them at call time.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import sys

from pipeline.constrained import dc2b

REPO_ROOT = dc2b.REPO_ROOT
SESSION_ENV = "TDR_DC2C_SESSION"


def per_session_cfg(c: dict, b: str) -> dict:
    """The frozen cfg with ONE Room B session and every tree under <base>/by_session/<b>."""
    if b not in c["b_sessions"]:
        raise dc2b.Refused(f"REFUSED: {SESSION_ENV}={b!r} is not one of {sorted(c['b_sessions'])}")
    base = os.path.join(c["base"], "by_session", b)
    return dict(c, base=base, b_sessions={b: c["b_sessions"][b]},
                data_view=os.path.join(base, "data"), win_view=os.path.join(base, "windows"),
                tree=lambda h: os.path.join(base, f"art_{h}"),
                shared=os.path.join(base, "art_shared"), dc2c_session=b)


def session_cfg(orig_cfg_for):
    def cfg_for(room: str, stand_in: bool) -> dict:
        c = orig_cfg_for(room, stand_in)
        b = os.environ.get(SESSION_ENV)
        return per_session_cfg(c, b) if b else c
    return cfg_for


def _run_step(cmd_args, env_extra, log):
    """dc2b's `_run_step`, launching dc2c_run so every step process carries both corrections."""
    import subprocess
    keep = tuple(dc2b.PASS_ENV) + (SESSION_ENV,)
    env = {k: v for k, v in os.environ.items() if not k.startswith("TDR_") or k in keep}
    env.update(env_extra)
    env["OMP_NUM_THREADS"] = "1"
    with open(log, "a", encoding="utf-8") as f:
        return subprocess.Popen([sys.executable, "-m", "pipeline.constrained.dc2c_run"] + cmd_args,
                                cwd=REPO_ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)


def install() -> None:
    """dc2b's corrections, then this one. Idempotent."""
    dc2b.install()
    import pipeline.constrained.dc2_pipeline as P
    import pipeline.constrained.dc2_run as R
    if getattr(R, "_dc2c_installed", False):
        return
    R.cfg_for = session_cfg(R.cfg_for)
    P._run_step = _run_step
    R._dc2c_installed = True


# ------------------------------------------------------------------ merging and the guard

def merge_decodes(base: str, sessions) -> dict:
    """<base>/by_session/<b>/decode.json for every b, merged into one decode.json at <base>."""
    out = None
    for b in sessions:
        p = os.path.join(base, "by_session", b, "decode.json")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if set(d.get("sessions") or {}) != {b}:
            raise dc2b.Refused(f"REFUSED: {p} decodes {sorted(d.get('sessions') or {})}, not exactly {b}")
        if out is None:
            out = {k: v for k, v in d.items()
                   if k not in ("sessions", "calibration", "constants", "bound_roots")}
            out.update(sessions={}, constants={}, bound_roots={},
                       calibration={k: v for k, v in (d.get("calibration") or {}).items()
                                    if k != "per_session"})
            out["calibration"]["per_session"] = {}
        for k in ("heads_tag", "train", "fusion_per_arm"):
            if d.get(k) != out.get(k):
                raise dc2b.Refused(f"REFUSED: session {b} ran with {k}={d.get(k)!r}, not {out.get(k)!r}")
        out["sessions"][b] = d["sessions"][b]
        out["calibration"]["per_session"].update((d.get("calibration") or {}).get("per_session") or {})
        out["constants"].update(d.get("constants") or {})
        out["bound_roots"][b] = d.get("bound_roots")
    out["dc2c"] = {"merged_from": {b: os.path.join("by_session", b, "decode.json") for b in sessions},
                   "why": "one Room B session per run; see pipeline/constrained/dc2c.py"}
    with open(os.path.join(base, "decode.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    return out


def capture_date(session_dir: str) -> str:
    """The session's capture date, from its baseline folders (YYYYMMDD-HHMMSS)."""
    days = {os.path.basename(d.rstrip("/"))[:8] for d in glob.glob(os.path.join(session_dir, "2026*/"))}
    if len(days) != 1:
        raise dc2b.Refused(f"REFUSED: {session_dir} has baselines from {sorted(days)}, not one day")
    return days.pop()


def posterior_guard(base: str, b_sessions: dict, heads) -> list:
    """Every head's posterior file for session b holds exactly b's recordings, every window of which
    was recorded on b's own capture date. Returns the problems; empty means sound."""
    import numpy as np
    bad = []
    for b, sdir in sorted(b_sessions.items()):
        day = capture_date(sdir)
        want = {os.path.basename(p)[:-len(".gt.json")]
                for p in glob.glob(os.path.join(sdir, "participant_*.gt.json"))}
        for h in heads:
            files = sorted(glob.glob(os.path.join(base, "by_session", b, f"art_{h}", "posteriors", "*_full.npz")))
            files = [f for f in files if os.path.basename(f).startswith("s010203_to_sB_")]
            if len(files) != 1:
                bad.append(f"{b}/{h}: {len(files)} heads-tag posterior files, want 1")
                continue
            z = np.load(files[0], allow_pickle=False)
            stems = set(str(s) for s in z["__stems__"])
            if stems != want:
                bad.append(f"{b}/{h}: recordings {sorted(stems ^ want)} differ from {sdir}")
            for s in stems:
                ep = np.asarray(z[f"{s}::t0_epoch"], float)
                got = {datetime.datetime.fromtimestamp(float(t)).strftime("%Y%m%d") for t in (ep.min(), ep.max())}
                if got != {day}:
                    bad.append(f"{b}/{h}/{s}: windows dated {sorted(got)}, the session is {day}")
    return bad
