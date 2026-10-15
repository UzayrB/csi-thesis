#!/bin/bash
# H4 (Uzayr's hardware test, 15 Oct 2026): the smoke runs on the boards, no walker. Timed work: run alone.
# Each step's exit code is captured before anything else runs. The test-only key injector (TDR_RIG_TEST_INJECT) is set
# only on the rig commands, never exported.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; L=$H/H4.log; PY=/opt/anaconda3/bin/python3
export OMP_NUM_THREADS=1 PYTHONPATH=.
NODES="RX1=/dev/cu.usbserial-3,RX2=/dev/cu.usbserial-4,RX3=/dev/cu.usbserial-0001"
say() { echo "[$(date '+%H:%M:%S')] $*; load $(sysctl -n vm.loadavg)" >> $L; }
echo "[$(date '+%H:%M:%S')] H4 start" > $L
ps -axo pid,%cpu,command | grep -E "anaconda3/bin/python|latexmk|lualatex|pdflatex|ffmpeg" | grep -v grep >> $L
say "quiet check above (python, LaTeX, ffmpeg processes)"

# --- tracking: a fresh 60 s baseline (Uzayr seated at the desk: not a true empty room, acceptable for a smoke run)
mkdir -p $H/H4_baseline
$PY -m pipeline.io.capture_logger --duration 60 --out $H/H4_baseline --nodes "$NODES" --reset --interval 10 >> $L 2>&1; rc=$?
B=$(ls -d $H/H4_baseline/*/ | tail -1); B=${B%/}
say "baseline rc=$rc dir=$B"
$PY -m pipeline.live preflight --baseline $B >> $L 2>&1; rc=$?; say "preflight with the baseline rc=$rc"

# --- the refusal: an early press (3 s in) with fewer than 10 idle windows
TDR_RIG_TEST_INJECT="3,15" $PY -m pipeline.live rig --baseline $B --minutes 1 >> $L 2>&1; rc=$?; say "refusal run rc=$rc"
R0=$(ls -d $H/rig_tracking_*/ | tail -1); say "refusal run recording ${R0%/}"

# --- the tracking smoke run: SPACE every 15 s after a 15 s idle start, 6 minutes
TDR_RIG_TEST_INJECT="15,15" $PY -m pipeline.live rig --baseline $B --minutes 6 >> $L 2>&1; rc=$?; say "tracking run rc=$rc"
RT=$(ls -d $H/rig_tracking_*/ | tail -1); RT=${RT%/}; say "tracking run recording $RT"
$PY $H/live_replay.py tracking $RT >> $L 2>&1; rc=$?; say "tracking replay rc=$rc"

# --- identification: room new, mps, staged, SPACE every 20 s, 6 minutes; memory sampled every 5 s
( while true; do
    t=$(date '+%s'); m=0
    for p in $(pgrep -f "pipeline.live.identify_engine rig"; pgrep -f "multiprocessing.spawn"); do
      r=$(ps -o rss= -p $p 2>/dev/null | tr -d ' '); [ -n "$r" ] && m=$((m + r))
    done
    echo "$t $m" >> $H/H4_identify_rss.txt; sleep 5
  done ) &
SAMP=$!
TDR_RIG_TEST_INJECT="20,20" $PY -m pipeline.live.identify_engine rig --mode identify --room new --minutes 6 >> $L 2>&1; rc=$?
kill $SAMP 2>/dev/null; say "identification run rc=$rc"
RI=$(ls -d $H/rig_identify_*/ | tail -1); RI=${RI%/}; say "identification run recording $RI"
$PY $H/live_replay.py identify $RI >> $L 2>&1; rc=$?; say "identification replay rc=$rc"
say "H4 DONE"
