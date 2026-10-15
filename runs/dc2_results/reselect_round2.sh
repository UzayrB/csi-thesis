#!/bin/zsh
# RE-SELECTION round 2 (DEVLOG VERIFY): round 1 on relgateU+abstain adopted a2w0.25 (+1.88 [0.42, 3.55]), so the base
# is relgateU+abstain+a2w0.25 and the remaining D3R options, the lock re-check, D4 and D5 are judged on it, as the attack
# layered after each adoption. Decode only; clean readers; ONE CPU job at a time.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
run() {
  echo "[$(date '+%H:%M:%S')] START pd_clean $*"
  caffeinate -dimsu python3 -m pipeline.constrained.pd_clean "$@" || { echo "[$(date '+%H:%M:%S')] RESELECT2 FAILED at $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE pd_clean $*"
}
B=relgateU+abstain+a2w0.25
for r in 01B1_to_02 02B1_to_01 0102_to_B1; do
  [[ $r == 01B1_to_02 ]] || run decode --cell d2pc_ar_$r --variants $B+w0.25 $B+w0.5 $B+lw0.25 $B+onhead $B+pace $B+off-9 $B+off-6 $B+sd3.5 $B+margin2.5
  run decode --cell d4c_fuse_$r --variants $B $B+g100n $B+interp
  for p in d2p_ar d4_fuse d4_attn; do run decode --cell ${p}_$r --variants $B; done
done
echo "RESELECT2 DECODES DONE $(date '+%F %T')"
