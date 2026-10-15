#!/bin/zsh
# Heartbeat watchdog for the 15 Oct hardware job: one line a minute (time, 1-min load, free memory, python count).
H=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/live/hw_2026-10-15
while true; do
  l=$(sysctl -n vm.loadavg | awk '{print $2}')
  f=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/ {print $2}')
  n=$(pgrep -f "anaconda3/bin/python3" | wc -l | tr -d ' ')
  echo "$(date '+%Y-%m-%d %H:%M:%S') load1 $l free $f python $n" >> $H/heartbeat.log
  sleep 60
done
