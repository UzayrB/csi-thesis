#!/bin/zsh
# Run identification GPU jobs ONE AT A TIME under a memory watchdog (lean-in brief, 1 Oct; after the out-of-memory
# crash of 1 Oct ~22:10). Each argument is one job: a python module and its arguments in one quoted string, e.g.
#   guard.sh "pipeline.identify.iwg_screen cnn --arm T3.75 --device mps" "pipeline.identify.iwg_screen cnn --arm T4.25 --device mps"
# Every 10 s: if the system's free memory falls below 30 % or the job's footprint passes 6 GB, that job's PID alone is
# killed and the queue stops (GUARD_MAX_GB overrides the 6 GB; 9 for the 4 s replays); a failing job also stops it. The log is runs/identify/lean_in/logs/guard.log.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
L=runs/identify/lean_in/logs
for job in "$@"; do
  name=$(echo $job | awk '{print $1}' | sed 's/.*\.//')_$(echo $job | md5 | cut -c1-6)
  log=$L/job_$name.log
  echo "[$(date '+%H:%M:%S')] start $job (log $log)" >> $L/guard.log
  PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.2 OMP_NUM_THREADS=1 PYTHONPATH=. $PY -m ${=job} > $log 2>&1 &
  pid=$!
  killed=0
  while kill -0 $pid 2>/dev/null; do
    free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
    mem=$(top -l 1 -pid $pid -stats mem | tail -1)
    echo "[$(date '+%H:%M:%S')] pid $pid footprint $mem free ${free}%" >> $L/guard.log
    gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
    if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > ${GUARD_MAX_GB:-6}" | bc -l) -eq 1 ]; then
      kill $pid; killed=1
      echo "[$(date '+%H:%M:%S')] KILLED pid $pid: footprint $mem, free ${free}%" >> $L/guard.log
      break
    fi
    sleep 10
  done
  wait $pid; rc=$?
  echo "[$(date '+%H:%M:%S')] end rc $rc: $job" >> $L/guard.log
  if [ $killed -eq 1 ] || [ $rc -ne 0 ]; then
    echo "[$(date '+%H:%M:%S')] QUEUE STOPPED" >> $L/guard.log
    exit 1
  fi
done
echo "[$(date '+%H:%M:%S')] QUEUE DONE" >> $L/guard.log
