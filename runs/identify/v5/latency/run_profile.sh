#!/bin/zsh
# The latency go's step 1 (Uzayr, 11 Oct; the Mastermind's slot 18:09): iv5_rig profile, B2's first 4 recordings at 1x on mps,
# OMP_NUM_THREADS=1, nice 0, MPS 0.7/0.5, alone on the machine; killed below 30 % free or above 12 GB. The timers live in the
# harness process only (iv5_rig.profile); the app is unchanged. MACHINE_STATE written before and after.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
ms busy "engine v5 latency, step 1: the live app's decision path profiled (B2's first 4 recordings at 1x, mps, nice 0, alone)" 15
ms log "engine v5 latency: profile starts (GPU, about 13 min; mps, nice 0)"
echo "[$(date '+%H:%M:%S')] START profile (mps, OMP_NUM_THREADS=1, nice 0)" >> $L/run.log
env OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 \
  $PY -m pipeline.identify.iv5_rig profile --device mps --recordings 4 < /dev/null > $L/profile.log 2>&1 &
pid=$! killed=0
while kill -0 $pid 2>/dev/null; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  mem=$(top -l 1 -pid $pid -stats mem | tail -1)
  gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
  echo "[$(date '+%H:%M:%S')] profile pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
  if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 12" | bc -l) -eq 1 ]; then
    kill $pid; killed=1; echo "[$(date '+%H:%M:%S')] KILLED profile (pid $pid): footprint $mem, free ${free}%" >> $L/run.log; break
  fi
  sleep 10
done
wait $pid; rc=$?
echo "[$(date '+%H:%M:%S')] END profile rc $rc killed $killed" >> $L/run.log
ms log "engine v5 latency: profile ends (rc $rc, killed $killed)"
ms quiet "Third overall's engine v5 latency profile ended (rc $rc)"
