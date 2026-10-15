#!/bin/bash
# H4, tracking rerun (15 Oct 2026): the first run's test injector variable (TDR_RIG_TEST_INJECT) never reached the
# rig, because pd_cells.env_for drops TDR_* variables from the rig's subprocess environment; renamed RIG_TEST_INJECT.
# Same baseline as the first run (H4_baseline, 12:27:33; the rig's pre-flight requires it under 120 min old).
# Timed work: run alone. Each step's exit code is captured before anything else runs.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; L=$H/H4.log; PY=/opt/anaconda3/bin/python3
export OMP_NUM_THREADS=1 PYTHONPATH=.
say() { echo "[$(date '+%H:%M:%S')] $*; load $(sysctl -n vm.loadavg)" >> $L; }
B=$(ls -d $H/H4_baseline/*/ | tail -1); B=${B%/}
say "H4 tracking rerun start (baseline $B)"
ps -axo pid,%cpu,command | grep -E "anaconda3/bin/python|latexmk|lualatex|pdflatex|ffmpeg" | grep -v grep >> $L
say "quiet check above"
RIG_TEST_INJECT="3,15" $PY -m pipeline.live rig --baseline $B --minutes 1 >> $L 2>&1; rc=$?; say "refusal run 2 rc=$rc"
R0=$(ls -d $H/rig_tracking_*/ | tail -1); say "refusal run 2 recording ${R0%/}"
RIG_TEST_INJECT="15,15" $PY -m pipeline.live rig --baseline $B --minutes 6 >> $L 2>&1; rc=$?; say "tracking run 2 rc=$rc"
RT=$(ls -d $H/rig_tracking_*/ | tail -1); RT=${RT%/}; say "tracking run 2 recording $RT"
$PY $H/live_replay.py tracking $RT >> $L 2>&1; rc=$?; say "tracking replay 2 rc=$rc"
say "H4 TRACKING RERUN DONE"
