#!/bin/zsh
# Heartbeat watchdog for run_b.sh (Uzayr's prompt of 10 Oct, section 0): every 60 s one line in heartbeat.log with the
# driver's state, the last run.log line and free memory; when the driver is gone, one closing line (ended cleanly, or
# DIED without a QUIET line) and exit. Usage: zsh heartbeat.sh <driver pid>
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
D=runs/identify/best
H=$D/heartbeat.log
pid=$1
while true; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {print $2}')
  last=$(tail -1 $D/logs/run.log 2>/dev/null)
  if kill -0 $pid 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] driver $pid alive; free $free; last: $last" >> $H
  else
    if grep -q "FINISH: driver ends" $D/logs/run.log 2>/dev/null; then
      echo "[$(date '+%H:%M:%S')] driver $pid ended cleanly; last: $last" >> $H
    else
      echo "[$(date '+%H:%M:%S')] DRIVER $pid DIED without writing QUIET; last: $last" >> $H
    fi
    exit 0
  fi
  sleep 60
done
