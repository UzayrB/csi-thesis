#!/bin/zsh
# Part D chain (30 Sep), tracking's second core. Replaces the probe's last two steps (legacy, semi causal),
# which it runs itself: first the app's legacy agreement gates on the three rotations (DISPLAY_PREREG section 3's
# precondition), then the cap equivalence (offline, three rotations; the app on B1), the spread sweep, and last
# the B1 semi-causal probe step.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
REF=DT0.relgateU+abstain+a2w0.25; V=relgateU+abstain+a2w0.25
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@"; echo "[$(date '+%H:%M:%S')] EXIT $? $*"; }
while kill -0 70318 2>/dev/null; do sleep 15; done       # the real-time test replay (its own PID)
echo "[$(date "+%H:%M:%S")] real-time test finished"
for C in d4c_fuse_0102_to_B1 d4c_fuse_01B1_to_02 d4c_fuse_02B1_to_01; do
  step python3 -m pipeline.live.final_model gate --cell $C --ref $REF --variant $V --mode legacy
done
step python3 -m pipeline.constrained.pd_disp_prov cap
step python3 -m pipeline.constrained.pd_disp_prov sweep
step python3 -m pipeline.constrained.pd_disp_prov report
step python3 -m pipeline.constrained.pd_disp_prov app_cap
step python3 -m pipeline.live.final_model gate --cell d4c_fuse_0102_to_B1 --ref $REF --variant $V --mode semi --causal
echo "PARTD DONE $(date '+%F %T')"
