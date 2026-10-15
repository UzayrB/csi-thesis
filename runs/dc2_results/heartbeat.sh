#!/bin/zsh
# Heartbeat watchdog for the DC2 results batch. Every 60 s it rewrites HEARTBEAT.txt with the clock,
# the queue's NOW line, and the age of the newest log under runs/dc2_results/logs. A running job whose
# log has not moved for STALL_MIN minutes is reported as STALLED. It reads only; it never kills.
cd "$(dirname "$0")/../.." || exit 1
STALL_MIN=${STALL_MIN:-20}
while true; do
  now=$(date '+%Y-%m-%d %H:%M:%S %Z')
  item=$(grep -m1 '^NOW:' QUEUE.md 2>/dev/null)
  newest=$(ls -t runs/dc2_results/logs/*.log 2>/dev/null | head -1)
  if [[ -n "$newest" ]]; then
    age=$(( ($(date +%s) - $(stat -f %m "$newest")) / 60 ))
    jobs=$(pgrep -f "OMP_NUM_THREADS=1|pipeline.constrained|tools.dc2" | wc -l | tr -d ' ')
    state="ok"
    if (( age >= STALL_MIN )) && (( jobs > 0 )); then state="STALLED (log idle ${age} min)"; fi
    printf '%s\n%s\nnewest log: %s, %d min old\npython jobs: %s\nstate: %s\n' \
      "$now" "$item" "$newest" "$age" "$jobs" "$state" > runs/dc2_results/HEARTBEAT.txt
  else
    printf '%s\n%s\nno log yet\n' "$now" "$item" > runs/dc2_results/HEARTBEAT.txt
  fi
  sleep 60
done
