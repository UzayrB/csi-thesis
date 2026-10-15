#!/bin/zsh
# The SECOND parallel-extraction confirmation run's launcher (run_confirm_par.sh, with every running process logged at the start
# and the end, and decide2.py on rules2.json, the memory rule Uzayr redefined after the first run; 12 Oct): NAME NICE MINUTES CMD...
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
SC=$L/${NAME}_system.csv
gb_of() { echo $1 | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} /K/ {sub("K[+-]?","",$1); print $1/1048576; next} {print 0}' }
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
ms busy "parallel extraction, $NAME (main and 3 worker processes, nice $NICE)" $MINS
ms log "parallel extraction: $NAME starts (main and 3 workers, nice $NICE, about $MINS min)"
echo "[$(date '+%H:%M:%S')] START $NAME (nice $NICE, OMP_NUM_THREADS=1)" >> $L/run.log
echo "clock,epoch,footprint_gb,free_pct" > $MC
echo "clock,epoch,pid,footprint_gb,command" > $WC
echo "clock,epoch,swap_used_mb,swapouts,pressure_level,free_pct" > $SC
{ echo "# $(date '+%Y-%m-%d %H:%M:%S %Z'): every running process at the start, by resident memory (ps -axo pid,rss,%cpu,command)"; ps -axo pid,rss,%cpu,command | sort -k2 -n -r | head -60; echo; memory_pressure | tail -1; sysctl vm.swapusage; } > $L/${NAME}_processes_start.txt
env OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5 \
  nice -n $NICE "$@" < /dev/null > $L/$NAME.log 2>&1 &
pid=$!
echo $pid > $L/$NAME.pid
n=0 killed=0
while kill -0 $pid 2>/dev/null; do
  CL=$(date '+%H:%M:%S'); EP=$(date +%s)
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
      echo "$CL,$EP,$k,$kg,$(ps -o command= -p $k | cut -c1-80 | tr ',' ' ')" >> $WC
    fi
  done
  if [ $(( n % 3 )) -eq 0 ]; then
    echo "$CL,$EP,$gb,$free" >> $MC
    su=$(sysctl -n vm.swapusage | awk '{for (i=1;i<=NF;i++) if ($i=="used") {v=$(i+2); sub("M","",v); print v}}')
    so=$(vm_stat | awk -F: '/Swapouts/ {gsub("[ .]","",$2); print $2}')
    pl=$(sysctl -n kern.memorystatus_vm_pressure_level)
    echo "$CL,$EP,$su,$so,$pl,$free" >> $SC
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
# one last system sample at the end, then the memory summary and the ship rule's decision (decide.py, the rules fixed before)
echo "$(date '+%H:%M:%S'),$(date +%s),$(sysctl -n vm.swapusage | awk '{for (i=1;i<=NF;i++) if ($i=="used") {v=$(i+2); sub("M","",v); print v}}'),$(vm_stat | awk -F: '/Swapouts/ {gsub("[ .]","",$2); print $2}'),$(sysctl -n kern.memorystatus_vm_pressure_level),$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')" >> $SC
if [ -f $D/rig_timing_${NAME}.json ] && [ $killed -eq 0 ]; then
  $PY -c "import sys; sys.path.insert(0, '.'); from pipeline.identify import iv5_rig as R; R.memory('$MC', '$NAME', workers_csv='$WC')" >> $L/$NAME.log 2>&1
  $PY $D/parallel/decide2.py >> $L/$NAME.log 2>&1
  echo "[$(date '+%H:%M:%S')] memory summarised and the ship rule decided (rc $?)" >> $L/run.log
fi
{ echo "# $(date '+%Y-%m-%d %H:%M:%S %Z'): every running process at the end"; ps -axo pid,rss,%cpu,command | sort -k2 -n -r | head -60; } > $L/${NAME}_processes_end.txt
ms log "parallel extraction: $NAME ends (rc $rc, killed $killed)"
ms quiet "Third overall's parallel extraction $NAME ended (rc $rc, killed $killed)"
