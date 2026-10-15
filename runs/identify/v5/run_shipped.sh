#!/bin/zsh
# Step 7's fallback (agreed with the Mastermind, 10 Oct): the cpu rig run at the documented shipped launch setting,
# OMP_NUM_THREADS=1 at nice 0, outside the driver (which can only lower priority). Its own memory watch: the process is
# killed below 30 % free memory or above 6 GB, as the driver's guard would.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
L=runs/identify/v5/logs
echo "[$(date '+%H:%M:%S')] START rig_timing_cpu_shipped (OMP_NUM_THREADS=1, nice 0)" >> $L/run.log
OMP_NUM_THREADS=1 PYTHONPATH=. /opt/anaconda3/bin/python3 -m pipeline.identify.iv5_rig timing --device cpu --tag cpu_shipped \
  < /dev/null > $L/rig_timing_cpu_shipped.log 2>&1 &
pid=$!
while kill -0 $pid 2>/dev/null; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  mem=$(top -l 1 -pid $pid -stats mem | tail -1)
  gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
  echo "[$(date '+%H:%M:%S')] rig_timing_cpu_shipped pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
  if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 6" | bc -l) -eq 1 ]; then
    kill $pid; echo "[$(date '+%H:%M:%S')] KILLED rig_timing_cpu_shipped (pid $pid): footprint $mem, free ${free}%" >> $L/run.log; break
  fi
  sleep 10
done
wait $pid; rc=$?
echo "[$(date '+%H:%M:%S')] END rig_timing_cpu_shipped rc $rc" >> $L/run.log
