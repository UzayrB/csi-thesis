#!/bin/zsh
# Watchdog for the IDENTIFICATION run only. Writes a heartbeat every 15 minutes.
# It never reads, writes, signals or repairs anything belonging to the tracking run.
set -o pipefail
setopt NULL_GLOB 2>/dev/null
ROOT=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
HB=$ROOT/runs/identify/logs/heartbeat_id.txt
while true; do
  {
    echo "===== $(date -u +%Y-%m-%dT%H:%M:%S) (UTC) / $(date +%H:%M:%S) SAST ====="
    echo "-- this run's PIDs --"
    echo "   caffeinate_id: $(cat $ROOT/runs/identify/logs/caffeinate_id.pid 2>/dev/null)"
    echo "   watchdog_id:   $(cat $ROOT/runs/identify/logs/watchdog_id.pid 2>/dev/null)"
    PIDS=$(pgrep -f "pipeline.identify.id1[1-8]" | tr '\n' ' ')
    echo "   id jobs:       ${PIDS:-none running}"
    echo "-- tracking run, READ ONLY --"
    echo "   their heartbeat mtime: $(stat -f '%Sm' $ROOT/runs/constrained/logs/heartbeat.txt 2>/dev/null || echo absent)"
    NEW=$(find $ROOT/runs/identify/logs -maxdepth 1 -name "*.log" -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1)
    if [ -n "$NEW" ]; then
      echo "-- newest id log: $(basename $NEW) --"
      tail -3 "$NEW"
    else
      echo "-- no id job logs yet (gate open, light work only) --"
    fi
  } > $HB 2>&1
  sleep 900
done
