#!/bin/zsh
# After step 7's shipped-setting cpu fallback (the Mastermind, 10 Oct): (1) the mps timing run at nice 0 (like 30 Sep), with the
# app's per-decision cache release, 12 GB limit; (2) the AdaBN timing sample on cpu (v4 against v5, first 30 B2 presses; timing
# only, decisions discarded), OMP_NUM_THREADS=1 at nice 0. Each with its own memory watch, one at a time.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
L=runs/identify/v5/logs
while pgrep -f "iv5_rig timing --device cpu --tag cpu_shipped" > /dev/null; do sleep 15; done
watch_run() {   # name limit_gb cmd...
  local name=$1 lim=$2; shift 2
  echo "[$(date '+%H:%M:%S')] START $name" >> $L/run.log
  "$@" < /dev/null > $L/$name.log 2>&1 &
  local pid=$! free mem gb
  while kill -0 $pid 2>/dev/null; do
    free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
    mem=$(top -l 1 -pid $pid -stats mem | tail -1)
    gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
    echo "[$(date '+%H:%M:%S')] $name pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
    if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > $lim" | bc -l) -eq 1 ]; then
      kill $pid; echo "[$(date '+%H:%M:%S')] KILLED $name (pid $pid): footprint $mem, free ${free}%" >> $L/run.log; break
    fi
    sleep 10
  done
  wait $pid; echo "[$(date '+%H:%M:%S')] END $name rc $?" >> $L/run.log
}
export OMP_NUM_THREADS=1 PYTHONPATH=.
watch_run rig_timing_mps 12 env PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 /opt/anaconda3/bin/python3 -m pipeline.identify.iv5_rig timing --device mps --tag mps
watch_run adapt_sample_cpu 6 /opt/anaconda3/bin/python3 -m pipeline.identify.iv5_rig adapt --device cpu
echo "[$(date '+%H:%M:%S')] after-fallback measurements done" >> $L/run.log
