#!/bin/zsh
# RE-SELECTION, case (a) (DEVLOG VERIFY, F2 interim): if the d1sp lock layers still adopt the scorer lock on the
# clean readers, the re-check on D2's networks adopts abstain over relgateU, and every later D-stage step is judged
# on relgateU+abstain (display lock, as the original D3R, D4 and D5 were on relgateU). This decodes those steps'
# sources on the three rotations with the clean readers. Decode only: no network changes. ONE CPU job at a time.
# Launched by hand only once the choice table shows case (a).
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
run() {
  echo "[$(date '+%H:%M:%S')] START pd_clean $*"
  caffeinate -dimsu python3 -m pipeline.constrained.pd_clean "$@" || { echo "[$(date '+%H:%M:%S')] RESELECT FAILED at $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE pd_clean $*"
}
B=relgateU+abstain
for r in 01B1_to_02 02B1_to_01 0102_to_B1; do
  run decode --cell d2pc_ar_$r --variants $B+w0.25 $B+w0.5 $B+lw0.25 $B+onhead $B+pace $B+off-9 $B+off-6 $B+a2w0.25 $B+sd3.5 $B+margin2.5
  run decode --cell d4c_fuse_$r --variants $B $B+g100n $B+interp
  for p in d2p_ar d4_fuse d4_attn; do run decode --cell ${p}_$r --variants $B; done
done
echo "RESELECT DECODES DONE $(date '+%F %T')"
