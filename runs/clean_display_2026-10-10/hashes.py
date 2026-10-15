"""Gate 1 of PLAN.md (5f13034c): every shipped file outside section 2's list, hashed before the work and checked after.

    python3 runs/clean_display_2026-10-10/hashes.py before     # writes HASHES_BEFORE.json (refuses to overwrite)
    python3 runs/clean_display_2026-10-10/hashes.py after      # writes HASHES_AFTER.json: every file identical, or not

The files: data/, the two model sets' files (runs/live/models/{final,zeroshot}.json: the networks, the offline records
and the code they load), the three cells and the rotation cells of the 0.5 s tree (the FC records among them), the
display heads, the trace hash lists, the rule folder, the live app's replays, renders, gate records, unconstrained
records and model folder, and the seventh look's folder (gate 6's reference).

Expected to change (PLAN.md section 2), so left out: FINAL_CONFIG.md and its .sha256, the two model-set manifests, and
the two gate records gate 5 rewrites (gate_f05_A3.json, gate_f05_B2.json; z05_B2 has none yet). New files (the FCC
records, the new replay folders, the archives, renders_K1gf) are listed by "after" separately; they never count as a
change.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ROOTS = ["data", "runs/live/replay", "runs/live/renders", "runs/live/renders_K1g_0p5", "runs/live/final",
         "runs/live/unconstrained", "runs/live/models", "runs/dc2_results/rule", "runs/dc2_results/final",
         "runs/dc2_results/dispend_final", "runs/dc2_results/dispend_zeroshot", "runs/dc2_results/display",
         "runs/dc2_results/clean_readers", "runs/a3_clean_2026-10-08"] + \
    sorted(os.path.relpath(p, REPO) for p in glob.glob(J(REPO, "runs", "dc2_results", "cells", "*05*")))
EXPECTED = {"runs/dc2_results/rule/FINAL_CONFIG.md", "runs/dc2_results/rule/FINAL_CONFIG.md.sha256",
            "runs/live/models/final.json", "runs/live/models/zeroshot.json",
            "runs/live/final/gate_f05_A3.json", "runs/live/final/gate_f05_B2.json"}


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def listing() -> list:
    out = set()
    for r in ROOTS:
        for dp, _dn, fn in os.walk(J(REPO, r)):
            out |= {os.path.relpath(J(dp, f), REPO) for f in fn if f != ".DS_Store"}
    for m in ("final", "zeroshot"):
        with open(J(REPO, "runs", "live", "models", f"{m}.json"), encoding="utf-8") as f:
            out |= set(json.load(f)["files"])
    return sorted(out - EXPECTED)


def main(which: str) -> int:
    out = J(HERE, f"HASHES_{which.upper()}.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    t0 = time.time()
    if which == "before":
        files = listing()
        res = {"what": "gate 1, hashes before (PLAN.md 5f13034c)", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "roots": ROOTS, "expected_to_change": sorted(EXPECTED), "n": len(files),
               "sha256": {p: sha(J(REPO, p)) for p in files}}
    else:
        with open(J(HERE, "HASHES_BEFORE.json"), encoding="utf-8") as f:
            bef = json.load(f)["sha256"]
        now = {p: (sha(J(REPO, p)) if os.path.exists(J(REPO, p)) else None) for p in bef}
        changed = sorted(p for p in bef if now[p] != bef[p])
        new = sorted(set(listing()) - set(bef))
        res = {"what": "gate 1, hashes after (PLAN.md 5f13034c)", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "n_checked": len(bef), "changed_or_missing": changed, "IDENTICAL": not changed, "new_files": new}
    res["seconds"] = round(time.time() - t0, 1)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print({k: v for k, v in res.items() if k not in ("sha256", "new_files", "roots", "expected_to_change")},
          f"new files: {len(res.get('new_files', []))}" if which == "after" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
