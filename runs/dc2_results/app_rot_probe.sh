#!/bin/zsh
# Part B audit probe (30 Sep): does a START-PRESS-ONLY replay of the app reproduce the 15:39 decisions on a
# development rotation (A1+A2 -> B1)? Against the offline decode DT0 (the 15:39 configuration, frozen pace).
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
C=d4c_fuse_0102_to_B1; REF=DT0.relgateU+abstain+a2w0.25; V=relgateU+abstain+a2w0.25
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@"; echo "[$(date '+%H:%M:%S')] EXIT $? $*"; }
step python3 -m pipeline.live.final_model gate --cell $C --ref $REF --variant $V --mode semi
step python3 -m pipeline.live.final_model gate --cell $C --ref $REF --variant $V --mode legacy
step python3 -m pipeline.live.final_model gate --cell $C --ref $REF --variant $V --mode semi --causal
echo "PROBE DONE $(date '+%F %T')"
