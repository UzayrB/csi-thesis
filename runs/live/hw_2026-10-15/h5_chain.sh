#!/bin/bash
# H5 chain (15 Oct 2026): the H3 second identity check, then the fast replays, the six 1x streams alone, then
# each stream's re-replay and comparison. Each step's exit code is captured before anything else runs.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; L=$H/H5.log; PY=/opt/anaconda3/bin/python3
export OMP_NUM_THREADS=1 PYTHONPATH=.
STEMS="participant_PA5_walk participant_PA1_walk participant_PA2_walk participant_PA3_walk participant_PA4_walk participant_PA6_walk"
echo "[$(date '+%H:%M:%S')] start; load $(sysctl -n vm.loadavg)" > $L
$PY $H/h3_onoff.py replay --tag on >> $H/H3_onoff.log 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] H3 replay of attempt 1 rc=$rc" >> $L
for s in $STEMS; do
  $PY $H/h5_stream.py fast $s >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] fast $s rc=$rc" >> $L
done
for s in $STEMS; do
  echo "[$(date '+%H:%M:%S')] stream $s starts; load $(sysctl -n vm.loadavg)" >> $L
  $PY $H/h5_stream.py stream $s >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] stream $s rc=$rc; load $(sysctl -n vm.loadavg)" >> $L
done
for s in $STEMS; do
  $PY $H/h5_stream.py rereplay $s >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] rereplay $s rc=$rc" >> $L
  $PY $H/h5_stream.py compare $s >> $L 2>&1; rc=$?; echo "[$(date '+%H:%M:%S')] compare $s rc=$rc" >> $L
done
echo "[$(date '+%H:%M:%S')] H5 CHAIN DONE" >> $L
