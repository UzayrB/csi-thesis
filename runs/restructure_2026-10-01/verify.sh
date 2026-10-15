#!/bin/zsh
# Verification of the 1 October 2026 pipeline restructure (reports/PIPELINE_RESTRUCTURE_2026-10-01.md).
# Tracking: the traced reproduction from the translated hash lists (must be EXACT, no unlisted input) and the
# app's G2 gate in semi mode with display K1g (must be 120/120 committed and locks, EXACT), on the three test cells.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PYTHONPATH=.
V=relgateU+abstain+a2w0.25; L=runs/restructure_2026-10-01/logs
for c in fin_A3 fin_B2 zsf_B2; do
  (echo "[$(date +%H:%M:%S)] START repro $c"; python3 -m pipeline.constrained.pd_repro_trace run --cell $c --variant $V; echo "[$(date +%H:%M:%S)] EXIT $? repro $c") > $L/repro_$c.log 2>&1 &
  (echo "[$(date +%H:%M:%S)] START G2 $c"; python3 -m pipeline.live.final_model gate --cell $c --ref FC.$V --variant $V --mode semi; echo "[$(date +%H:%M:%S)] EXIT $? G2 $c") > $L/g2_$c.log 2>&1 &
done
wait
echo "VERIFY DONE $(date '+%F %T')"
