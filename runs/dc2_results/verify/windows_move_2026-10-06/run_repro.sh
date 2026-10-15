#!/bin/zsh
# EXACT reproduction of the three tracking cells after the windows path change (plan: reports/project/repository/2026-10-06_windows-path-plan.md)
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
O=runs/dc2_results/verify/windows_move_2026-10-06
export OMP_NUM_THREADS=1 PYTHONPATH=. PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.2
for c in fin_A3 fin_B2 zsf_B2; do
  echo "[$(date '+%H:%M:%S')] start $c" >> $O/progress.log
  /opt/anaconda3/bin/python3 -m pipeline.constrained.pd_repro_trace run --cell $c --variant relgateU+abstain+a2w0.25 > $O/$c.log 2>&1 &
  P=$!
  while kill -0 $P 2>/dev/null; do
    fr=$(memory_pressure | awk -F: '/free percentage/{gsub(/[ %]/,"",$2); print $2}')
    if [ -n "$fr" ] && [ "$fr" -lt 15 ]; then kill $P; echo "[$(date '+%H:%M:%S')] KILLED $c: free memory $fr%" >> $O/progress.log; exit 3; fi
    sleep 30
  done
  wait $P; rc=$?
  echo "[$(date '+%H:%M:%S')] $c exit $rc: $(grep -E '^REPRODUCTION' $O/$c.log | tail -1)" >> $O/progress.log
  [ $rc -ne 0 ] && exit $rc
done
echo "[$(date '+%H:%M:%S')] DONE" >> $O/progress.log
