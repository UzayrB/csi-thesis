#!/bin/zsh
# The latency go's new confirmation run (Uzayr, 11 Oct; the Mastermind's slot 18:09), the same setup as option (c)'s (run_confirm.sh): B2 through the live app and the real
# serial parser, every recording at 1x, loso_B2_v5, room B, mps, OMP_NUM_THREADS=1, nice 0, the app's MPS cache release on,
# alone on the machine. Its own memory watch, as the driver's: killed below 30 % free memory or above 12 GB (checked every
# 10 s); the footprint and free memory logged every 30 s to logs/confirm_memory.csv, judged flat by `iv5_rig memory`.
# MACHINE_STATE written before and after (ms_v5.py reads every write back). No caffeinate: the Mastermind holds the one.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
CSV=$L/confirm_lat_memory.csv
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
if pmset -g batt | head -1 | grep -q "Battery Power"; then
  echo "[$(date '+%H:%M:%S')] HOLD: confirmation run not started on battery" >> $L/run.log
  exit 3
fi
ms busy "engine v5 latency, step 4: the new confirmation run: B2 through the live app at 1x, loso_B2_v5, mps, one thread, nice 0, alone" 70
ms log "engine v5 latency: the new confirmation run starts (GPU, about 70 min; mps, nice 0, 12 GB limit, MPS 0.7/0.5)"
echo "[$(date '+%H:%M:%S')] START confirm_lat (mps, OMP_NUM_THREADS=1, nice 0)" >> $L/run.log
echo "clock,epoch,footprint_gb,free_pct" > $CSV
env OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 \
  $PY -m pipeline.identify.iv5_rig confirm --device mps --tag confirm_lat < /dev/null > $L/confirm_lat.log 2>&1 &
pid=$!
echo $pid > $L/confirm_lat.pid
n=0 killed=0
while kill -0 $pid 2>/dev/null; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  mem=$(top -l 1 -pid $pid -stats mem | tail -1)
  gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} /K/ {sub("K[+-]?","",$1); print $1/1048576; next} {print 0}')
  if [ $(( n % 3 )) -eq 0 ]; then
    echo "$(date '+%H:%M:%S'),$(date +%s),$gb,$free" >> $CSV
  fi
  echo "[$(date '+%H:%M:%S')] confirm_lat pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
  if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 12" | bc -l) -eq 1 ]; then
    kill $pid; killed=1
    echo "[$(date '+%H:%M:%S')] KILLED confirm_lat (pid $pid): footprint $mem, free ${free}%" >> $L/run.log
    break
  fi
  n=$(( n + 1 ))
  sleep 10
done
wait $pid
rc=$?
echo "[$(date '+%H:%M:%S')] END confirm_lat rc $rc killed $killed" >> $L/run.log
if grep -qiE "MTLCompilerService|metal.*error|mps.*(error|out of memory)" $L/confirm_lat.log; then
  echo "[$(date '+%H:%M:%S')] METAL/MPS message in confirm.log" >> $L/run.log
fi
if [ -f $D/rig_timing_confirm_lat.json ] && [ $killed -eq 0 ]; then
  $PY -c "import sys; sys.path.insert(0, '.'); from pipeline.identify import iv5_rig as R; R.memory('$CSV', 'confirm_lat')" >> $L/confirm_lat.log 2>&1
  echo "[$(date '+%H:%M:%S')] memory judged (rc $?)" >> $L/run.log
fi
ms log "engine v5 latency: the new confirmation run ends (rc $rc, killed $killed)"
ms quiet "Third overall's engine v5 latency confirmation run ended (rc $rc, killed $killed)"
echo "[$(date '+%H:%M:%S')] confirmation run done" >> $L/run.log
