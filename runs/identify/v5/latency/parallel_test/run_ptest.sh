#!/bin/zsh
# The parallel-extraction feasibility test (Uzayr's go, 12 Oct; the Mastermind's slot 08:31): ptest.py on B2's first three
# identification recordings, alone, nice 0, OMP_NUM_THREADS=1 (inherited by the 3 workers); killed below 30 % free or above
# 6 GB (the parent's footprint). MACHINE_STATE written before and after. Nothing that ships changes.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
P=$D/latency/parallel_test
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
ms busy "parallel-extraction feasibility test (scratch timing; B2 walks; series, threads, 3 processes; nice 0, alone)" 20
ms log "parallel-extraction test starts (CPU up to 4, about 15 min; nice 0)"
echo "[$(date '+%H:%M:%S')] START ptest (cpu, OMP_NUM_THREADS=1, nice 0)" >> $L/run.log
env OMP_NUM_THREADS=1 PYTHONPATH=. $PY $P/ptest.py 3 < /dev/null > $P/ptest.log 2>&1 &
pid=$! killed=0
while kill -0 $pid 2>/dev/null; do
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  mem=$(top -l 1 -pid $pid -stats mem | tail -1)
  gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
  echo "[$(date '+%H:%M:%S')] ptest pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
  if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 6" | bc -l) -eq 1 ]; then
    pkill -P $pid; kill $pid; killed=1; echo "[$(date '+%H:%M:%S')] KILLED ptest (pid $pid): footprint $mem, free ${free}%" >> $L/run.log; break
  fi
  sleep 10
done
wait $pid; rc=$?
echo "[$(date '+%H:%M:%S')] END ptest rc $rc killed $killed" >> $L/run.log
ms log "parallel-extraction test ends (rc $rc, killed $killed)"
ms quiet "Third overall's parallel-extraction test ended (rc $rc)"
