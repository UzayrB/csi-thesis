#!/bin/zsh
# Identification development queue runner. Runs the jobs in jobs.txt in order, one at a time, and picks
# up jobs appended while it runs. jobs.txt lines: <name>|<command>. State per job in state/<name>:
# RUNNING, DONE <time> or FAILED <exit> <time>. Logs in logs/<name>.log. Stops when STOP exists.
Q=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/dev/queue
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
mkdir -p $Q/state $Q/logs
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
  ( export OMP_NUM_THREADS=4 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=.; eval "$cmd" ) > $Q/logs/$name.log 2>&1
  rc=$?
  if [[ $rc -eq 0 ]]; then echo "DONE $(date '+%Y-%m-%d %H:%M:%S')" > $Q/state/$name
  else echo "FAILED $rc $(date '+%Y-%m-%d %H:%M:%S')" > $Q/state/$name; fi
  echo "$(date '+%H:%M:%S') END $name rc=$rc" >> $Q/runner.log
done
echo "$(date '+%H:%M:%S') runner stopped (STOP file)" >> $Q/runner.log
