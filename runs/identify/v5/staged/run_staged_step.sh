#!/bin/zsh
# One heavy step of the staged-extraction job (Uzayr's go, 12 Oct; QUEUE_STAGED.md): NAME NICE MINUTES CMD...
# The main process and its worker processes are one job: their TOTAL footprint is guarded (killed above 12 GB, or below
# 30 % free memory, the whole process group); every 30 s the main process's footprint goes to logs/<NAME>_memory.csv
# (clock,epoch,footprint_gb,free_pct, as iv5_rig.memory reads) and each child's to logs/<NAME>_workers.csv
# (clock,epoch,pid,footprint_gb,command). OMP_NUM_THREADS=1 (and BLAS at one in the workers, set by the app); MPS 0.7/0.5.
# MACHINE_STATE written before and after. No caffeinate: the Mastermind holds the one for the whole job.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
NAME=$1 NICE=$2 MINS=$3
shift 3
MC=$L/${NAME}_memory.csv
WC=$L/${NAME}_workers.csv
gb_of() { echo $1 | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} /K/ {sub("K[+-]?","",$1); print $1/1048576; next} {print 0}' }
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
ms busy "Agent1 staged extraction, $NAME (main and 4 worker processes, cpu, nice $NICE; untimed, LaTeX allowed)" $MINS
ms log "staged extraction: $NAME starts (main and 4 workers, cpu, nice $NICE, about $MINS min)"
echo "[$(date '+%H:%M:%S')] START $NAME (nice $NICE, OMP_NUM_THREADS=1)" >> $L/run.log
echo "clock,epoch,footprint_gb,free_pct" > $MC
echo "clock,epoch,pid,footprint_gb,command" > $WC
env OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 \
  nice -n $NICE "$@" < /dev/null > $L/$NAME.log 2>&1 &
pid=$!
echo $pid > $L/$NAME.pid
n=0 killed=0
while kill -0 $pid 2>/dev/null; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  mem=$(top -l 1 -pid $pid -stats mem | tail -1)
  gb=$(gb_of $mem)
  tot=$gb
  kids=$(pgrep -P $pid)
  for k in ${=kids}; do
    km=$(top -l 1 -pid $k -stats mem | tail -1)
    kg=$(gb_of $km)
    tot=$(echo "$tot + $kg" | bc -l)
    if [ $(( n % 3 )) -eq 0 ]; then
      echo "$(date '+%H:%M:%S'),$(date +%s),$k,$kg,$(ps -o command= -p $k | cut -c1-80 | tr ',' ' ')" >> $WC
    fi
  done
  if [ $(( n % 3 )) -eq 0 ]; then
    echo "$(date '+%H:%M:%S'),$(date +%s),$gb,$free" >> $MC
  fi
  echo "[$(date '+%H:%M:%S')] $NAME pid $pid footprint $mem total ${tot}G free ${free}% nice $(ps -o nice= -p $pid) children $(echo $kids | wc -w | tr -d ' ')" >> $L/guard.log
  if [ ${free:-100} -lt 30 ] || [ $(echo "$tot > 12" | bc -l) -eq 1 ]; then
    for k in ${=kids}; do kill $k 2>/dev/null; done
    kill $pid; killed=1
    echo "[$(date '+%H:%M:%S')] KILLED $NAME and its workers (pid $pid): total ${tot}G, free ${free}%" >> $L/run.log
    break
  fi
  n=$(( n + 1 ))
  sleep 10
done
wait $pid
rc=$?
echo "[$(date '+%H:%M:%S')] END $NAME rc $rc killed $killed" >> $L/run.log
ms log "staged extraction: $NAME ends (rc $rc, killed $killed)"
ms quiet "Agent1's staged extraction $NAME ended (rc $rc, killed $killed)"
