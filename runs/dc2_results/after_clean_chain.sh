#!/bin/zsh
# After the clean-reader chain (QUEUE items F2 to 3). ONE CPU job at a time; stops at the first failure.
# Written 2026-09-29 by the tracking session.
#   a. the choice table: every rule decision on the clean readers against the original. ANY flip STOPS the
#      chain here (Uzayr's instruction: re-select, retrain, test once; that is decided, not automated)
#   b. F3: the corrected FINAL, fin_A3 and fin_B2 re-decoded with clean readers (CR.relgateU); zsf copied
#   a2. the ablation ladder with the clean readers (rule/CR_LADDER.md)
#   b2. 1b: the corrected FINAL reproduced from its hashes (pd_repro)
#   b3. 5: the teaching pack re-exported on the corrected model
#   c. 1c: the substitution test and the shuffled-radio control, fin_A3, fin_B2 (clean) and zsf_B2
#   d. 2: the live replay gate, one recording first, then A3 and B2 whole
#   e. 3: the final display head (DISP_END) on A1+A2+B1, its A3 and B2 posteriors
#   f. 3: the renders, one recording first without video, then A3 and B2 whole
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
step() {
  echo "[$(date '+%H:%M:%S')] START $*"
  caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] AFTER CHAIN FAILED at $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE $*"
}
until grep -q "CLEAN CHAIN DONE\|CHAIN FAILED" runs/dc2_results/logs/clean_chain.log; do sleep 30; done
grep -q "CLEAN CHAIN DONE" runs/dc2_results/logs/clean_chain.log || { echo "AFTER CHAIN: the clean chain failed; nothing run"; exit 1; }
while pgrep -f "pd_clean (decode|crossfit) --inner" >/dev/null; do sleep 10; done
echo "AFTER CHAIN START $(date '+%F %T')"
# a.
python3 - <<'PY' || { echo "AFTER CHAIN STOPPED: a D-stage choice moved (rule/CR_CHOICES.md)"; exit 3; }
import glob, json, os, sys
rows, flips = [], []
for p in sorted(glob.glob("runs/dc2_results/rule/D*.json")):
    o = json.load(open(p))
    q = "runs/dc2_results/rule/CR_" + os.path.basename(p)
    if not os.path.exists(q):
        print(f"missing clean comparison {q}"); sys.exit(2)
    n = json.load(open(q))
    ob, nb = o["base_summary"]["objective"], n["base_summary"]["objective"]
    oa, na = o["arm_summary"]["objective"], n["arm_summary"]["objective"]
    row = {"name": o["name"], "lock": o["lock"], "arm_lock": o.get("arm_lock"), "base": o["base"], "arm": o["arm"],
           "ADOPT_before": bool(o["ADOPT"]), "ADOPT_clean": bool(n["ADOPT"]),
           "paired_before": o.get("paired"), "paired_clean": n.get("paired"),
           "missing_rotations_clean": n.get("missing_rotations"),
           "objective_base_before": ob, "objective_base_clean": nb, "objective_arm_before": oa, "objective_arm_clean": na}
    if n.get("missing_rotations"):
        print(f"clean comparison {q} is missing rotations {n['missing_rotations']}"); sys.exit(2)
    rows.append(row)
    if row["ADOPT_before"] != row["ADOPT_clean"]:
        flips.append(row)
out = {"n": len(rows), "flips": flips, "rows": rows}
json.dump(out, open("runs/dc2_results/rule/CR_CHOICES.json", "w"), indent=1, default=str)
L = ["# Every rule decision on the clean readers against the original", "",
     f"{len(rows)} comparisons; {len(flips)} decisions moved.", "",
     "| comparison | lock | ADOPT before | ADOPT clean | objective arm before -> clean |", "|---|---|---|---|---|"]
L += [f"| {r['name']} | {r['lock']}{'/' + r['arm_lock'] if r['arm_lock'] and r['arm_lock'] != r['lock'] else ''} | "
      f"{r['ADOPT_before']} | {r['ADOPT_clean']} | {r['objective_arm_before']:.2f} -> {r['objective_arm_clean']:.2f} |" for r in rows]
open("runs/dc2_results/rule/CR_CHOICES.md", "w").write("\n".join(L) + "\n")
print(f"CHOICE TABLE: {len(rows)} comparisons, {len(flips)} flips: {[f['name'] + '_' + f['lock'] for f in flips]}")
sys.exit(3 if flips else 0)
PY
echo "NO CHOICE MOVED $(date '+%F %T')"
step python3 -m pipeline.constrained.pd_clean ladder
# b.
step python3 -m pipeline.constrained.pd_clean decode --cell fin_A3 --variants relgateU
step python3 -m pipeline.constrained.pd_clean decode --cell fin_B2 --variants relgateU
step python3 -m pipeline.constrained.pd_clean decode --cell zsf_B2 --variants relgateU
echo "CORRECTED FINAL DONE $(date '+%F %T')"
# b2. 1b: the corrected FINAL reproduced from its hashes
step python3 -m pipeline.constrained.pd_repro hashes
step python3 -m pipeline.constrained.pd_repro run --cell fin_A3
step python3 -m pipeline.constrained.pd_repro run --cell fin_B2
echo "REPRODUCTION FROM HASHES DONE $(date '+%F %T')"
# b3. 5: the teaching pack on the corrected model (a new dated file)
step python3 tools/teaching_pack_corrected.py
# c.
step python3 -m pipeline.constrained.pd_subst --cell fin_A3 --ref CR.relgateU --clean
step python3 -m pipeline.constrained.pd_subst --cell fin_B2 --ref CR.relgateU --clean
step python3 -m pipeline.constrained.pd_subst --cell zsf_B2 --ref relgateU
echo "SUBSTITUTION DONE $(date '+%F %T')"
# d.
step python3 -m pipeline.live.final_model gate --cell fin_A3 --stems participant_PA5_TEST_walk
step python3 -m pipeline.live.final_model gate --cell fin_A3
step python3 -m pipeline.live.final_model gate --cell fin_B2
echo "LIVE GATES DONE $(date '+%F %T')"
# e.
# the display head may already have been trained and inferred on the GPU, beside this chain (Uzayr, 12:4x)
while pgrep -f "pd_dispend (train|infer) --inner" >/dev/null; do sleep 30; done
D=runs/dc2_results/dispend_final
[[ -f $D/models/s0102B1_dispend_final_g25_s0_fuse.pt ]] || step python3 -m pipeline.constrained.pd_dispend train --cell fin_A3 --device cpu
[[ -f $D/posteriors/s0102B1_dispend_final_on_03_full.npz ]] || step python3 -m pipeline.constrained.pd_dispend infer --cell fin_A3
[[ -f $D/posteriors/s0102B1_dispend_final_on_B2_full.npz ]] || step python3 -m pipeline.constrained.pd_dispend infer --cell fin_B2
echo "DISPLAY HEAD DONE $(date '+%F %T')"
# f.
step python3 -m pipeline.constrained.pd_render --cell fin_A3 --stems participant_PA5_TEST_walk --no-video
step python3 -m pipeline.constrained.pd_render --cell fin_A3
step python3 -m pipeline.constrained.pd_render --cell fin_B2
echo "AFTER CHAIN DONE $(date '+%F %T')"
