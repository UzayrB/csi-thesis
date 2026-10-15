#!/bin/bash
# H3 on/off proof chain (15 Oct 2026): each step's exit code captured before anything else runs
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; L=$H/H3_onoff.log; PY=/opt/anaconda3/bin/python3
export OMP_NUM_THREADS=1 PYTHONPATH=.
echo "[$(date '+%H:%M:%S')] start; load $(sysctl -n vm.loadavg)" > $L
$PY $H/h3_onoff.py run --tag on2 --record 1 >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] on rc=$rc" >> $L
$PY $H/h3_onoff.py run --tag off2 --record 0 >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] off rc=$rc" >> $L
$PY $H/h3_onoff.py compare_rel on2 off2 >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] compare rc=$rc" >> $L
$PY $H/h3_onoff.py replay --tag on2 >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] replay rc=$rc" >> $L
echo "[$(date '+%H:%M:%S')] CHAIN DONE" >> $L
