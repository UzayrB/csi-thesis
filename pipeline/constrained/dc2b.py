"""dc2b. The DC2 pipeline's pass bookkeeping, corrected, around the FROZEN code (2026-09-24).

WHY THIS EXISTS. Three faults were found in `dc2_pipeline.py` and `dc2_run.py` on 2026-09-24, before
any Room B data existed, by reading the code against the real DC2 layout. Both files are pinned and
hashed by freeze 23h, so they are NOT edited: this module replaces the two functions at fault, at
call time, and adds the refusals. Nothing in the model changes: the heads, the decoder, the
constants and every arm are the frozen ones, byte for byte.

  1. A ROOM B SESSION NAMED LIKE A ROOM A ONE WAS SILENTLY REPLACED BY ROOM A. `dc2_run.do_view`
     links Room A's training sessions (01, 02, 03) into the view first, then skips any Room B
     session whose link already exists. Room B folders named session_01 and session_02 (as the
     identification sheet had them) made DC2 score Room A's own training data as Room B, with no
     error. Reproduced 2026-09-24. Now REFUSED.
  2. CALIBRATION AND ABORTED PASS IDS WERE PER SESSION. `split_passes` applied one session's id
     lists to every recording in it, and pass ids restart at 1 in every recording, so a dedicated
     calibration recording with passes 1 to 8 also took passes 1 to 8 from every participant, as
     calibration. The manifest now names calibration RECORDINGS, and aborted passes per recording.
     The old per-session form is refused on real data and kept only for the stand-in, whose
     manifest was written in it.
  3. IDENTIFICATION RECORDINGS INSIDE A TRACKING SESSION WERE SCORED AS TRACKING. Discovery takes
     every `participant_*.gt.json` except `_DEMO_`. An `_idpath_` recording (RX2 moved, line A only)
     in a Room B session is now REFUSED. Identification lives in data/room_B/identification/.

The manifest, per Room B session key (the folder session_B1 is key "B1"):

    {"room": "room_B",
     "sessions": {"B1": {"calibration_recordings": ["participant_CAL_walk"],
                         "aborted": {"participant_PA5_walk": [7]},
                         "calibration_pass_ids": "NOT USED: per recording, see dc2b"}}}

The string in `calibration_pass_ids` is a tripwire: the frozen command, run by mistake on this
manifest, fails loudly on it instead of treating every pass as evaluated.
"""

from __future__ import annotations

import glob
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRIPWIRE = "NOT USED: per recording, see pipeline/constrained/dc2b.py"
#: env vars the step processes need beside the frozen allowlist. TDR_DC2B_MANIFEST points the
#: STAND-IN at another manifest (a test of the per-recording form on real CSI); a real run refuses it.
PASS_ENV = ("TDR_LATTICE", "TDR_STANDIN_B1", "TDR_STANDIN_SUFFIX", "TDR_DC2_FUSION", "TDR_DC2B_MANIFEST")


class Refused(SystemExit):
    pass


# ------------------------------------------------------------------ the refusals (faults 1 and 3)

def layout_problems(c: dict, room_a_dir: str) -> list:
    """Every reason the Room B layout cannot be scored. Empty means it can."""
    bad = []
    if c["room"] == "room_A":
        bad.append("DC2 runs on Room B; --room room_A would score the training room")
    taken = set(c["train"]) | {os.path.basename(d).split("session_", 1)[1]
                               for d in glob.glob(os.path.join(room_a_dir, "session_*"))}
    for b, d in sorted(c["b_sessions"].items()):
        if b in taken:
            bad.append(f"Room B folder {d} is named session_{b}, the name of a Room A session. The "
                       f"view would link Room A's session_{b} in its place and score it as Room B. "
                       f"Name Room B sessions B1 and B2 (ground_truth --session B1)")
        for p in sorted(glob.glob(os.path.join(d, "*"))):
            n = os.path.basename(p)
            if "_idpath_" in n or "REHEARSAL" in n:
                bad.append(f"{p}: an identification or rehearsal recording inside a tracking session "
                           f"would be scored as tracking. Identification belongs in "
                           f"data/room_B/identification/")
    return bad


def guard_cfg(orig_cfg_for):
    def cfg_for(room: str, stand_in: bool) -> dict:
        c = orig_cfg_for(room, stand_in)
        if stand_in:
            alt = os.environ.get("TDR_DC2B_MANIFEST")
            if alt:
                c["manifest"] = alt
            return c
        if os.environ.get("TDR_DC2B_MANIFEST"):
            raise Refused("REFUSED: TDR_DC2B_MANIFEST is for the stand-in only; a real run reads "
                          "data/room_B/calibration.json")
        bad = layout_problems(c, os.path.join(REPO_ROOT, "data", "room_A"))
        if bad:
            raise Refused("REFUSED, nothing run:\n  " + "\n  ".join(bad))
        return c
    return cfg_for


# ------------------------------------------------------------------ the manifest (fault 2)

def _stems(d: str) -> set:
    return {os.path.basename(p)[:-len(".gt.json")] for p in glob.glob(os.path.join(d, "participant_*.gt.json"))}


def manifest_problems(man: dict, b_sessions: dict) -> list:
    """Every reason a REAL run's manifest cannot be trusted. Empty means it can."""
    bad = []
    sess = man.get("sessions")
    if not isinstance(sess, dict):
        return ["the manifest has no \"sessions\" object"]
    for k in sorted(set(sess) - set(b_sessions)):
        bad.append(f"manifest session {k!r} has no folder data/room_B/session_{k}")
    for b, d in sorted(b_sessions.items()):
        m = sess.get(b)
        if not isinstance(m, dict):
            bad.append(f"session {b}: no manifest entry; its calibration recording must be named")
            continue
        if isinstance(m.get("calibration_pass_ids"), list):
            bad.append(f"session {b}: calibration_pass_ids is a per-SESSION list, applied to every "
                       f"recording; name the calibration recording in calibration_recordings")
        if isinstance(m.get("aborted_pass_ids"), list) and m["aborted_pass_ids"]:
            bad.append(f"session {b}: aborted_pass_ids is a per-SESSION list; use aborted "
                       f"{{stem: [pass ids]}}")
        have = _stems(d)
        cal = m.get("calibration_recordings")
        if not isinstance(cal, list) or not cal:
            bad.append(f"session {b}: calibration_recordings is missing or empty; configuration B "
                       f"would fall back to the absolute constants without saying why")
        else:
            if len(set(cal)) != len(cal):
                bad.append(f"session {b}: a calibration recording is listed twice")
            for s in cal:
                if s not in have:
                    bad.append(f"session {b}: calibration recording {s} is not in {d}")
            if have and set(cal) >= have:
                bad.append(f"session {b}: every recording is a calibration recording; nothing is evaluated")
        ab = m.get("aborted", {})
        if not isinstance(ab, dict):
            bad.append(f"session {b}: aborted must be {{stem: [pass ids]}}")
        else:
            for s, ids in ab.items():
                if s not in have:
                    bad.append(f"session {b}: aborted names {s}, which is not in {d}")
                if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                    bad.append(f"session {b}: aborted[{s}] must be a list of pass ids")
    return bad


def by_recording(orig_split):
    def split_passes(rec, sess_manifest) -> dict:
        """Calibration, aborted and evaluated pass ids for ONE recording, keyed by its stem."""
        if "calibration_recordings" not in (sess_manifest or {}):
            return orig_split(rec, sess_manifest)      # the stand-in's per-session form, unchanged
        allp = set(int(p) for p, _nm, _a, _b in rec.pass_spans())
        abort = set(int(x) for x in (sess_manifest.get("aborted") or {}).get(rec.stem, []))
        stray = sorted(abort - allp)
        if stray:
            raise Refused(f"REFUSED: {rec.stem} has no passes {stray}, which the manifest calls aborted")
        if rec.stem in sess_manifest["calibration_recordings"]:
            cal, evaluated = sorted(allp - abort), []
        else:
            cal, evaluated = [], sorted(allp - abort)
        return {"calibration": cal, "aborted": sorted(abort), "evaluated": evaluated, "n_all": len(allp)}
    return split_passes


# ------------------------------------------------------------------ installing it

def _run_step(cmd_args, env_extra, log):
    """The frozen `_run_step`, launching dc2b_run so every step process carries these corrections."""
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith("TDR_") or k in PASS_ENV}
    env.update(env_extra)
    env["OMP_NUM_THREADS"] = "1"
    with open(log, "a", encoding="utf-8") as f:
        return subprocess.Popen([sys.executable, "-m", "pipeline.constrained.dc2b_run"] + cmd_args,
                                cwd=REPO_ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)


def install() -> None:
    """Replace, in this process, the frozen functions at fault. Idempotent."""
    import pipeline.constrained.dc2_pipeline as P
    import pipeline.constrained.dc2_run as R
    if getattr(R, "_dc2b_installed", False):
        return
    R.cfg_for = guard_cfg(R.cfg_for)
    P.split_passes = by_recording(P.split_passes)
    P._run_step = _run_step
    R._dc2b_installed = True


def check_real_manifest(room: str) -> dict:
    """The parent's check before any step runs: the layout, then the manifest."""
    import pipeline.constrained.dc2_run as R
    c = R.cfg_for(room, False)                     # the guarded one: raises on a bad layout
    p = c["manifest"]
    if not os.path.exists(p):
        raise Refused(f"REFUSED: no calibration manifest at {p}. Write it with "
                      f"python3 -m pipeline.constrained.dc2b_manifest")
    with open(p, encoding="utf-8") as f:
        man = json.load(f)
    bad = manifest_problems(man, c["b_sessions"])
    if bad:
        raise Refused("REFUSED, nothing run: the calibration manifest\n  " + "\n  ".join(bad))
    return man
