#!/bin/zsh
# A CPU slot for one step, then exec the command (same PID, so run_b.sh's memory guard still watches it). The Mastermind's
# share (10 Oct): from about 09:00 (Second Overall started early) at most 3 CPU processes; earlier 6. A slot is a directory
# holding its PID; a slot whose PID has gone is free. Counting and taking a slot happen under one lock.
D=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/best
S=$D/slots
mkdir -p $S
while true; do
  hm=$(date '+%H%M')
  cap=$([ $hm -ge 0858 ] && echo 3 || echo 6)
  if mkdir $D/slot.lock 2>/dev/null; then
    live=0
    for d in $S/*(N/); do
      p=$(cat $d/pid 2>/dev/null)
      if [ -n "$p" ] && kill -0 $p 2>/dev/null; then live=$(( live + 1 )); else rm -rf $d; fi
    done
    if [ $live -lt $cap ]; then
      i=0
      while [ -d $S/$i ]; do i=$(( i + 1 )); done
      mkdir $S/$i && echo $$ > $S/$i/pid
      rmdir $D/slot.lock
      echo "[$(date '+%H:%M:%S')] slot $i taken (cap $cap, $live others live)"
      exec "$@"
    fi
    rmdir $D/slot.lock
  fi
  sleep 15
done
