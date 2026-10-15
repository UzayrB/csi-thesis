#!/bin/bash
# H4 rerun after the fix (15 Oct 2026; 90d878c8 identification data-time order, 86b122ac tracking refusals).
# Timed work: run alone. Each step's exit code is captured before anything else runs.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
H=runs/live/hw_2026-10-15; L=$H/H4_run3.log; PY=/opt/anaconda3/bin/python3
export OMP_NUM_THREADS=1 PYTHONPATH=.
say() { echo "[$(date '+%H:%M:%S')] $*; load $(sysctl -n vm.loadavg)" >> $L; }
echo "[$(date '+%H:%M:%S')] H4 rerun 3 start (HEAD $(git rev-parse --short HEAD))" > $L
ps -axo pid,%cpu,command | grep -E "anaconda3/bin/python|latexmk|lualatex|pdflatex|ffmpeg" | grep -v grep >> $L
say "quiet check above"
$PY -m pipeline.io.identify_board >> $L 2>&1; rc=$?; say "identify_board rc=$rc"
P1=$(grep "68:09:47:4c:ef:b4" $L | tail -1 | awk '{print $1}'); P2=$(grep "20:50:0d:1a:28:74" $L | tail -1 | awk '{print $1}'); P3=$(grep "20:50:0d:30:5f:80" $L | tail -1 | awk '{print $1}')
NODES="RX1=$P1,RX2=$P2,RX3=$P3"; say "nodes by MAC: $NODES"
mkdir -p $H/H4r3_baseline
$PY -m pipeline.io.capture_logger --duration 60 --out $H/H4r3_baseline --nodes "$NODES" --reset --interval 10 >> $L 2>&1; rc=$?
B=$(ls -d $H/H4r3_baseline/*/ | tail -1); B=${B%/}; say "baseline rc=$rc dir=$B"
$PY -m pipeline.live preflight --baseline $B >> $L 2>&1; rc=$?; say "preflight with the baseline rc=$rc"
RIG_TEST_INJECT="3,15" $PY -m pipeline.live rig --baseline $B --minutes 1 >> $L 2>&1; rc=$?; say "refusal (press at 3 s) rc=$rc"
R=$(ls -d $H/rig_tracking_*/ | tail -1); say "refusal (3 s) recording ${R%/}"
RIG_TEST_INJECT="6,15" $PY -m pipeline.live rig --baseline $B --minutes 1 >> $L 2>&1; rc=$?; say "refusal (press at 6 s) rc=$rc"
R=$(ls -d $H/rig_tracking_*/ | tail -1); say "refusal (6 s) recording ${R%/}"
RIG_TEST_INJECT="15,15" $PY -m pipeline.live rig --baseline $B --minutes 6 >> $L 2>&1; rc=$?; say "tracking run rc=$rc"
RT=$(ls -d $H/rig_tracking_*/ | tail -1); RT=${RT%/}; say "tracking run recording $RT"
$PY $H/live_replay.py tracking $RT >> $L 2>&1; rc=$?; say "tracking replay rc=$rc"
( while true; do
    t=$(date '+%s'); m=0
    for p in $(pgrep -f "pipeline.live.identify_engine rig"; pgrep -f "multiprocessing.spawn"); do
      r=$(ps -o rss= -p $p 2>/dev/null | tr -d ' '); [ -n "$r" ] && m=$((m + r))
    done
    echo "$t $m" >> $H/H4r3_identify_rss.txt; sleep 5
  done ) &
SAMP=$!
RIG_TEST_INJECT="20,20" $PY -m pipeline.live.identify_engine rig --mode identify --room new --minutes 6 >> $L 2>&1; rc=$?
kill $SAMP 2>/dev/null; say "identification run rc=$rc"
RI=$(ls -d $H/rig_identify_*/ | tail -1); RI=${RI%/}; say "identification run recording $RI"
$PY $H/live_replay.py identify $RI >> $L 2>&1; rc=$?; say "identification replay rc=$rc"
say "H4 RERUN 3 DONE"
