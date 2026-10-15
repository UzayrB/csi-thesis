"""dc2_verify_run. Run after `dc2b_pipeline`, BEFORE any DC2 figure is read or quoted. READ ONLY.

    python3 -m tools.dc2_verify_run --room room_B

The DC2 decode can finish with exit 0 and still be wrong in ways its report only shows as a blank:
found on 2026-09-24 by the hardware check, a calibration recording the pipeline's recording list does
not keep (any name outside the six) leaves `s_B` empty, and configuration B silently equals A. This
refuses, loudly, unless for every Room B session:

  - calibration constants exist and `s_B` is a number (B was re-anchored on the calibration walks);
  - the scored passes are exactly the manifest's: every pass of every non-calibration recording, less
    the passes aborted at capture time, and no calibration pass among them;
  - configurations A and B scored the same passes;
and, for room_B, the run went through `dc2b_pipeline` (never the frozen `dc2_pipeline`).

Exit 0: the run is what the pre-registration describes. Exit 1: do not read the figures.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verify(room: str, room_dir: str, base: str, results: str, want_wrapper: bool) -> list:
    bad = []
    dp = os.path.join(base, "decode.json")
    if not os.path.exists(dp):
        return [f"no {dp}: run the DC2 pipeline first"]
    dec = json.load(open(dp, encoding="utf-8"))
    man = json.load(open(os.path.join(room_dir, "calibration.json"), encoding="utf-8"))
    sessions = sorted(os.path.basename(d).split("session_", 1)[1] for d in glob.glob(os.path.join(room_dir, "session_*")))
    if not sessions:
        return [f"no Room B session folders in {room_dir}"]
    per = (dec.get("calibration") or {}).get("per_session") or {}
    for b in sessions:
        node = (dec.get("sessions") or {}).get(b)
        if node is None:
            bad.append(f"session {b}: not decoded at all")
            continue
        if b not in per or b not in (dec.get("constants") or {}):
            bad.append(f"session {b}: NO CALIBRATION CONSTANTS. No calibration walk reached the pipeline, "
                       f"so configuration B is configuration A. Is the calibration recording named for one "
                       f"of the six (participant_<name>_C_walk) and listed in the manifest?")
        if not isinstance(node.get("s_B"), (int, float)):
            bad.append(f"session {b}: s_B is {node.get('s_B')!r}; the null was NOT re-anchored")
        m = (man.get("sessions") or {}).get(b) or {}
        cal = set(m.get("calibration_recordings") or [])
        aborted = m.get("aborted") or {}
        want = set()
        for gp in glob.glob(os.path.join(room_dir, f"session_{b}", "participant_*.gt.json")):
            stem = os.path.basename(gp)[: -len(".gt.json")]
            if stem in cal:
                continue
            ids = {int(p["pass_id"]) for p in (json.load(open(gp, encoding="utf-8")).get("passes") or [])}
            want |= {(stem, i) for i in ids - set(aborted.get(stem, []))}
        rows = node.get("rows") or {}
        for cfg in ("A", "B"):
            got = {(r["stem"], int(r["pass_id"])) for r in rows.get(cfg, [])}
            if got != want:
                bad.append(f"session {b}, configuration {cfg}: scored {len(got)} passes, the manifest says "
                           f"{len(want)}; missing {sorted(want - got)[:4]}, extra {sorted(got - want)[:4]}")
            if any(s in cal for s, _ in got):
                bad.append(f"session {b}, configuration {cfg}: a calibration pass was scored")
    if want_wrapper:
        R = json.load(open(results, encoding="utf-8")) if os.path.exists(results) else {}
        if (R.get("run_through") or {}).get("wrapper") != "pipeline.constrained.dc2b_pipeline":
            bad.append(f"{results} did not come through dc2b_pipeline; the frozen dc2_pipeline mis-splits passes")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="verify a DC2 run before any figure is read")
    ap.add_argument("--room", default="room_B")
    ap.add_argument("--room-dir", default=None, help="default: data/<room>")
    ap.add_argument("--base", default=None, help="default: runs/constrained/dc2_<room>_s0.5_pressalign")
    a = ap.parse_args(argv)
    room_dir = a.room_dir or os.path.join(REPO, "data", a.room)
    base = a.base or os.path.join(REPO, "runs", "constrained", f"dc2_{a.room}_s0.5_pressalign")
    results = os.path.join(REPO, "runs", "constrained", "fh", f"dc2_pipeline_{a.room}", "results.json")
    bad = verify(a.room, room_dir, base, results, want_wrapper=(a.room == "room_B"))
    print("DC2 RUN: " + ("VERIFIED" if not bad else f"NOT VALID, {len(bad)} PROBLEM(S). Do not read the figures."))
    for b in bad:
        print("  - " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
