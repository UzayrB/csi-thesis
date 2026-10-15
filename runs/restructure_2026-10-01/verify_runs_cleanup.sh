#!/bin/zsh
# After the runs/ cleanup of 1 Oct 2026 (files moved to the Bin, list in runs_cleanup_2026-10-01.tsv.gz): the exact
# reproduction and the app's G2 gate (semi, K1g) on the three test cells. Exit codes are captured before the log line.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PYTHONPATH=. PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=relgateU+abstain+a2w0.25; L=runs/restructure_2026-10-01/logs
for c in fin_A3 fin_B2 zsf_B2; do
  (echo "[$(date +%H:%M:%S)] START repro $c"; caffeinate -dimsu python3 -m pipeline.constrained.pd_repro_trace run --cell $c --variant $V; rc=$?; echo "[$(date +%H:%M:%S)] EXIT $rc repro $c") > $L/cleanup_repro_$c.log 2>&1 &
  (echo "[$(date +%H:%M:%S)] START G2 $c"; env -u PD_CLEAN_PREFIX -u PD_PACE_MEAN -u PD_PACE_SD caffeinate -dimsu python3 -m pipeline.live.final_model gate --cell $c --ref FC.$V --variant $V --mode semi; rc=$?; echo "[$(date +%H:%M:%S)] EXIT $rc G2 $c") > $L/cleanup_g2_$c.log 2>&1 &
done
wait
echo "CLEANUP VERIFY DONE $(date '+%F %T')"
