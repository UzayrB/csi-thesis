#!/bin/zsh
# wait_log.sh STEP -- CMD...: wait until the driver's log says STEP ended rc 0, then exec CMD (same PID); exit 1 if STEP
# was BLOCKED, KILLED or SKIPPED.
L=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/best/logs/run.log
s=$1
shift 2
while ! grep -q "END $s rc 0" $L; do
  if grep -qE "(BLOCKED|KILLED|SKIPPED) $s" $L; then echo "[$(date '+%H:%M:%S')] $s failed: not run: $*"; exit 1; fi
  sleep 30
done
exec "$@"
