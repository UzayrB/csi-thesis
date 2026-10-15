#!/bin/zsh
# Storage (Uzayr, 11 Oct: Drive by his own copy; the Mastermind: one model rebuilt in scratch and compared): (1) iv5_train
# storage: STORAGE.json, STORAGE.md, STORAGE.sha256 (every v5 RF/ET pickle's size and sha256); (2) iv5_train rebuild
# loso_B2 into a scratch folder, its four pickles' sha256 against STORAGE.json. One process at a time, nice 10,
# OMP_NUM_THREADS=1, MPS 0.3/0.2, killed below 30 % free or above 6 GB. MACHINE_STATE written before and after.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
SCRATCH=$1
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
watch_run() {   # name cmd...
  local name=$1; shift
  echo "[$(date '+%H:%M:%S')] START $name (nice 10, OMP_NUM_THREADS=1)" >> $L/run.log
  env OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.2 nice -n 10 "$@" \
    < /dev/null > $L/$name.log 2>&1 &
  local pid=$! free mem gb killed=0 rc
  while kill -0 $pid 2>/dev/null; do
    free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
    mem=$(top -l 1 -pid $pid -stats mem | tail -1)
    gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
    echo "[$(date '+%H:%M:%S')] $name pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
    if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 6" | bc -l) -eq 1 ]; then
      kill $pid; killed=1
      echo "[$(date '+%H:%M:%S')] KILLED $name (pid $pid): footprint $mem, free ${free}%" >> $L/run.log
      break
    fi
    sleep 10
  done
  wait $pid
  rc=$?
  echo "[$(date '+%H:%M:%S')] END $name rc $rc killed $killed" >> $L/run.log
}
ms busy "engine v5 storage: sha256 of the v5 RF/ET pickles, then loso_B2_v5 rebuilt in scratch and compared (CPU 1, nice 10)" 10
ms log "engine v5: storage block starts (CPU 1, about 10 min)"
watch_run storage $PY -m pipeline.identify.iv5_train storage
watch_run rebuild_loso_B2 $PY -m pipeline.identify.iv5_train rebuild loso_B2 $SCRATCH
ms log "engine v5: storage block ends"
ms quiet "Third overall's engine v5 storage block ended"
