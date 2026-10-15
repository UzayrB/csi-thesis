#!/bin/zsh
# Backup heartbeat: every 15 minutes write the running PIDs and the tail of the newest stage log.
REPO="/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code"
HB="$REPO/runs/constrained/logs/heartbeat.txt"
while true; do
  {
    echo "===== $(date '+%Y-%m-%dT%H:%M:%S') ====="
    echo "-- python pipeline PIDs --"
    pgrep -fl "pipeline.constrained|pipeline.realtime" 2>/dev/null || echo "  none running"
    NEW=$(ls -t "$REPO"/runs/constrained/logs/*.log 2>/dev/null | head -1)
    echo "-- newest log: ${NEW:t} --"
    [ -n "$NEW" ] && tail -3 "$NEW"
  } >> "$HB"
  sleep 900
done
