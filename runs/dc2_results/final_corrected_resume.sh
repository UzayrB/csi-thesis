#!/bin/zsh
# RESUME of final_corrected_chain.sh from the teaching export (the one test, the tables and the verification are DONE) (Uzayr's instructions of 29 Sep, points 3 to 7).
#   0. the frozen configuration's hash (rule/FINAL_CONFIG.md); refuse on a mismatch
#   1. provenance PRE-checks: zero-shot (fails on any component touching B1 or B2), main (fails on A3 or B2)
#   2. THE ONE TEST: fin_A3, fin_B2, zsf_B2 decoded with the frozen variant, clean readers, the A1+A2 pace (prefix FC)
#   3. provenance POST-checks on each decode's own file trace; STOP on a failure
#   4. the tables: main (pd_final), zero-shot old and new, the B1 gain paired on B2
#   5. verification (substitution, shuffled radio), then the teaching export, the renders, the live gates, the reproduction
# ONE CPU job at a time. Stops at the first failure. Usage: final_corrected_chain.sh relgateU+abstain+a2w0.25
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=$1
[[ $V == relgateU+abstain+a2w0.25 ]] || { echo "FINAL CHAIN REFUSED: the frozen variant is relgateU+abstain+a2w0.25, got '$V'"; exit 2; }
step() {
  echo "[$(date '+%H:%M:%S')] START $*"
  caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] FINAL CHAIN FAILED at $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE $*"
}
hashcheck() { (cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "FINAL CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }; }
hashcheck
step python3 tools/teaching_pack_corrected.py --variant $V
echo "TEACHING DONE $(date '+%F %T')"
# the renders (the display head trained on the GPU at 13:00 on A1+A2+B1)
step python3 -m pipeline.constrained.pd_render --cell fin_B2 --variant $V --ref FC.$V --stems participant_PA5_walk --no-video
step python3 -m pipeline.constrained.pd_render --cell fin_B2 --variant $V --ref FC.$V
step python3 -m pipeline.constrained.pd_render --cell fin_A3 --variant $V --ref FC.$V
echo "RENDERS DONE $(date '+%F %T')"
# the live port: replay gates
step python3 -m pipeline.live.final_model gate --cell fin_B2 --variant $V --ref FC.$V --stems participant_PA5_walk
step python3 -m pipeline.live.final_model gate --cell fin_B2 --variant $V --ref FC.$V
step python3 -m pipeline.live.final_model gate --cell fin_A3 --variant $V --ref FC.$V
echo "LIVE GATES DONE $(date '+%F %T')"
# the reproduction from the hashes, last (the slowest step)
step python3 -m pipeline.constrained.pd_repro hashes --variant $V
step python3 -m pipeline.constrained.pd_repro run --cell fin_B2 --variant $V
step python3 -m pipeline.constrained.pd_repro run --cell fin_A3 --variant $V
hashcheck
echo "FINAL CHAIN DONE $(date '+%F %T')"
