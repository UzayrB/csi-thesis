#!/bin/zsh
# The reader-leak fix (DEVLOG_TRACKING VERIFY; QUEUE items F1 and F2). ONE CPU job at a time, no GPU.
# Written 2026-09-29 by the tracking session. Stops at the first failure.
#   0. the cross-fit builder against dc2_run.do_infer's own file (crossfit --plumb)
#   1. own-map reproductions with the audit trace: the final cells, and one cell of each other kind
#   2. cross-fit reader files for every cell of the two affected rotations, and fin_A3 / fin_B2
#   3. PHASE A: the ladder and every choice on the final configuration's path, clean readers
#   4. PHASE B: every other rule comparison's sources, clean readers
#   5. all 78 rule comparisons re-run on the clean sources (rule/CR_*)
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
run() {
  echo "[$(date '+%H:%M:%S')] START pd_clean $*"
  caffeinate -dimsu python3 -m pipeline.constrained.pd_clean "$@" || { echo "[$(date '+%H:%M:%S')] CHAIN FAILED at pd_clean $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE pd_clean $*"
}
ROTS=(01B1_to_02 02B1_to_01 0102_to_B1)
CHANGED=(01B1_to_02 02B1_to_01)
typeset -A A B
A[d1sp]="ref"
A[d1sr]="ref"
A[d2pc_ar]="ref relgateU relgateU+a2w0.25 relgateU+abstain relgateU+g100n relgateU+interp relgateU+lw0.25 relgateU+margin2.5 relgateU+off-6 relgateU+off-9 relgateU+onhead relgateU+pace relgateU+sd3.5 relgateU+w0.25 relgateU+w0.5"
A[d4c_fuse]="relgateU relgateU+g100n relgateU+interp"
B[d1sp]="abstain cnull lw0.25 lw0.5 onhead pace relgate relgate+abstain relgate+abstain+lw0.25 relgateA relgateA+a2w0.25 relgateA+a2w1.0 relgateA+abstain relgateA+abstain+lw0.25 relgateA+margin1.5 relgateA+margin2.5 relgateA+off-6 relgateA+off-9 relgateA+sd3.5 relgateA+sd5.5 relgateU relgateU+abstain w0.25 w0.5 w1.0"
B[d2p_base]="ref"
B[d2p_ar]="ref relgateU"
B[d2p_arE]="ref"
B[d2p_arEx]="ref"
B[d2p_aug]="ref"
B[d2p_early]="ref"
B[d2p_earlyx]="ref"
B[d2p_mix]="ref"
B[d2p_rrel]="ref"
B[d4_attn]="relgateU"
B[d4_fuse]="relgateU"

while pgrep -f "pd_clean decode --inner" >/dev/null; do sleep 10; done   # one CPU job at a time
grep "against the record" runs/dc2_results/logs/clean_own_d4c_01B1.log | grep -q "'EXACT': True" || { echo "CHAIN FAILED: the first CPU reproduction is not exact"; exit 1; }
echo "CLEAN CHAIN START $(date '+%F %T')"
# 0.
run crossfit --cell fin_A3 --plumb
# 1. the record reproduced on the CPU, with every file each decode opens
run decode --cell fin_A3 --variants relgateU --own
run decode --cell fin_B2 --variants relgateU --own
run decode --cell zsf_B2 --variants relgateU --own
run decode --cell d1sp_01B1_to_02 --variants ref --own
run decode --cell d2p_base_01B1_to_02 --variants ref --own
run decode --cell d1sr_01B1_to_02 --variants ref --own
echo "OWN-MAP REPRODUCTIONS DONE $(date '+%F %T')"
# 2.
for r in $CHANGED; do
  for p in ${(k)A} ${(k)B}; do run crossfit --cell ${p}_$r; done
done
run crossfit --cell fin_A3
run crossfit --cell fin_B2
echo "CROSSFIT DONE $(date '+%F %T')"
# 3. and 4.
phase() {
  local ph=$1 p r v
  for p in ${(kP)ph}; do
    eval "v=\"\${${ph}[$p]}\""
    for r in $ROTS; do run decode --cell ${p}_$r --variants ${=v}; done
  done
  echo "PHASE $ph DONE $(date '+%F %T')"
}
phase A
phase B
# 5.
python3 - <<'PY' || { echo "CHAIN FAILED at the rules"; exit 1; }
import glob, json, os, sys
sys.path.insert(0, ".")
from pipeline.constrained import pd_rule
def cr(src):
    pre, _at, var = src.partition("@")
    return f"{pre}@CR.{var or 'ref'}"
n = 0
for p in sorted(glob.glob("runs/dc2_results/rule/D*.json")):
    d = json.load(open(p))
    args = ["compare", "--name", f"CR_{d['name']}", "--base", cr(d["base"]), "--arm", cr(d["arm"]), "--lock", d["lock"]]
    if d.get("arm_lock") and d["arm_lock"] != d["lock"]:
        args += ["--arm-lock", d["arm_lock"]]
    pd_rule.main(args)
    n += 1
print(f"RULES RE-RUN: {n}")
PY
echo "CLEAN CHAIN DONE $(date '+%F %T')"
