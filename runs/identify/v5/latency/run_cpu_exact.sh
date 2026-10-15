#!/bin/zsh
# The latency go's step 2 (Uzayr, 11 Oct; the Mastermind's slot 18:09): B2 through the live app on cpu at full speed, untimed,
# twice SIDE BY SIDE: (i) the code before the latency change (445d42c1's pipeline/ in a scratch tree, the repository's other folders
# linked) and (ii) the code after it (this tree, 7de0b32b). Each nice 10, OMP_NUM_THREADS=1, its own memory watch (killed below 30 %
# free or above 12 GB). Then `cpu_exact.py compare`: (i) and (ii) bit-identical on every decision; (ii) against the replay.
# MACHINE_STATE written before and after. No caffeinate: the Mastermind holds the one.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/v5
L=$D/logs
LA=$PWD/$L
OUT=$D/latency/cpu_exact
BEFORE=$1                                  # the scratch tree holding 445d42c1's pipeline/
mkdir -p $OUT
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_v5.py "$@" || echo "[$(date '+%H:%M:%S')] MS WRITE NOT CONFIRMED: $1 $2" >> $L/run.log
  rmdir $D/ms.lock
}
watch_run() {   # name dir cmd...
  local name=$1 dir=$2; shift 2
  echo "[$(date '+%H:%M:%S')] START $name (cpu, OMP_NUM_THREADS=1, nice 10, in $dir)" >> $L/run.log
  ( cd $dir && env OMP_NUM_THREADS=1 PYTHONPATH=. nice -n 10 "$@" < /dev/null > $LA/lat_cpu_exact_$name.log 2>&1 ) &
  local sub=$! pid="" free mem gb killed=0
  sleep 3
  pid=$(pgrep -f "cpu_exact.py run $name " | head -1)
  while kill -0 $sub 2>/dev/null; do
    free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
    if [ -n "$pid" ]; then
      mem=$(top -l 1 -pid $pid -stats mem | tail -1)
      gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
      echo "[$(date '+%H:%M:%S')] $name pid $pid footprint $mem free ${free}% nice $(ps -o nice= -p $pid)" >> $L/guard.log
      if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > 12" | bc -l) -eq 1 ]; then
        kill $pid; killed=1
        echo "[$(date '+%H:%M:%S')] KILLED $name (pid $pid): footprint $mem, free ${free}%" >> $L/run.log
        break
      fi
    fi
    sleep 10
  done
  wait $sub
  echo "[$(date '+%H:%M:%S')] END $name rc $? killed $killed" >> $L/run.log
}
ms busy "engine v5 latency, step 2: cpu exactness: B2 through the live app on cpu at full speed, before and after the change, side by side, nice 10" 30
ms log "engine v5 latency: cpu exactness check starts (CPU 2, about 30 min; two processes, nice 10, OMP 1)"
watch_run before $BEFORE $PY $PWD/$D/cpu_exact.py run before $PWD/$OUT &
sleep 5
watch_run after $PWD $PY $PWD/$D/cpu_exact.py run after $PWD/$OUT &
wait
$PY $D/cpu_exact.py compare $OUT $D/latency/cpu_exact.json >> $L/lat_cpu_exact_compare.log 2>&1
rc=$?
echo "[$(date '+%H:%M:%S')] cpu exactness compare rc $rc" >> $L/run.log
ms log "engine v5 latency: cpu exactness check ends (compare rc $rc)"
ms quiet "Third overall's engine v5 latency cpu exactness check ended (compare rc $rc)"
