#!/bin/zsh
# Identification-walks queue runner (brief reports/BRIEF_ID_WALKS_2026-09-29.md, section 1): one job at a time,
# every job under taskpolicy -c utility and nice 19 with OMP_NUM_THREADS=1. No caffeinate, governor or watchdog.
# jobs.txt lines: <name>|<command>. State per job in state/<name>: RUNNING, DONE <time> or FAILED <exit> <time>.
# Stops when STOP exists. Each training job itself waits while a tracking training process runs.
Q=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/idwalks/queue
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
echo $$ > $Q/runner.pid
while [[ ! -e $Q/STOP ]]; do
  next=""
  while IFS='|' read -r name cmd; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    [[ -e $Q/state/$name ]] && continue
    next="$name|$cmd"; break
  done < $Q/jobs.txt
  if [[ -z "$next" ]]; then sleep 30; continue; fi
  name=${next%%|*}; cmd=${next#*|}
  echo "RUNNING $(date '+%Y-%m-%d %H:%M:%S')" > $Q/state/$name
  echo "$(date '+%H:%M:%S') START $name" >> $Q/runner.log
  ( export OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=.; eval "taskpolicy -c utility nice -n 19 $cmd" ) > $Q/logs/$name.log 2>&1
  rc=$?
  if [[ $rc -eq 0 ]]; then echo "DONE $(date '+%Y-%m-%d %H:%M:%S')" > $Q/state/$name
  else echo "FAILED $rc $(date '+%Y-%m-%d %H:%M:%S')" > $Q/state/$name; fi
  echo "$(date '+%H:%M:%S') END $name rc=$rc" >> $Q/runner.log
done
echo "$(date '+%H:%M:%S') runner stopped (STOP file)" >> $Q/runner.log
