"""iv5_check. Engine v5's gates (`prompt_identification_v5_ship.md`, stop rules): `gate N` exits 1 unless every check of
the steps before N passed, so a block that starts with it never runs after a failed check.

    PYTHONPATH=. python3 -m pipeline.identify.iv5_check gate 3

Development evaluation, all data seen.
"""

from __future__ import annotations

import glob
import json
import os
import sys

V5D = os.path.join("runs", "identify", "v5")
PAIRS = [(f"loso_{s}", s) for s in ("A1", "A2", "A3", "B1", "B2")] + [
    (f"{m}", s) for m in ("xr_AB", "xr_ABtrk", "xr_A", "xr_B1") for s in ("A3", "B2")]


def step_ok(n: int) -> tuple:
    if n == 1:
        p = os.path.join(V5D, "expected.json")
        return (os.path.exists(p) and json.load(open(p)).get("brief_numbers_reproduced") is True), "expected.json"
    if n == 2:
        bad = [f"{m}_v4 {s}" for m, s in PAIRS
               if not (os.path.exists(p := os.path.join(V5D, "null", f"{m}_v4_{s}_T4.0.json")) and json.load(open(p))["PASSED"])]
        return (not bad), f"null replays not passed: {bad}"
    if n == 3:
        p = os.path.join(V5D, "checks", "train.json")
        return (os.path.exists(p) and json.load(open(p)).get("PASSED") is True), "checks/train.json"
    if n == 4:
        bad = [f"{m}_v5 {s}" for m, s in PAIRS
               if not (os.path.exists(p := os.path.join(V5D, "checks", f"replay_{m}_v5_{s}_T4.0.json")) and json.load(open(p))["PASSED"])]
        return (not bad), f"v5 replays not passed: {bad}"
    if n == 5:
        p = os.path.join(V5D, "checks", "scorecard_equal.json")
        return (os.path.exists(p) and json.load(open(p)).get("PASSED") is True), "checks/scorecard_equal.json"
    if n == 6:
        p = os.path.join(V5D, "checks", "smoke.json")
        return (os.path.exists(p) and json.load(open(p)).get("PASSED") is True), "checks/smoke.json"
    if n == 7:                                  # the cpu run (one thread, nice 10); if it failed, the shipped setting's rerun
        p = os.path.join(V5D, "rig_timing.json")    # (one thread, nice 0) decides (the Mastermind, 10 Oct)
        q = os.path.join(V5D, "rig_timing_cpu_shipped.json")
        ok = os.path.exists(p) and json.load(open(p)).get("PASSED") is True
        if not ok and os.path.exists(q):
            return json.load(open(q)).get("PASSED") is True, "rig_timing_cpu_shipped.json (the shipped setting decides)"
        return ok, "rig_timing.json"
    return True, ""


def gate(n: int) -> bool:
    for k in range(1, n):
        ok, why = step_ok(k)
        print(f"step {k}: {'PASSED' if ok else 'NOT PASSED'} ({why})", flush=True)
        if not ok:
            return False
    return True


if __name__ == "__main__":
    if sys.argv[1] == "gate":
        sys.exit(0 if gate(int(sys.argv[2])) else 1)
    sys.exit(2)
