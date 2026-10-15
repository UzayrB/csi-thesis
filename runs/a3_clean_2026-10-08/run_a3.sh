#!/bin/zsh
# The ONE lock-side A3 decode (A3's fourth look): six recordings, one niced CPU process each, under mem_guard.py.
# A recording starts only while system free memory is at least 25 %.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/a3_clean_2026-10-08
L=$D/a3_lock/logs

free_pct() { memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}'; }

one() {
  local stem=$1
  local f=$(free_pct)
  if [ "$f" -lt 25 ]; then
    echo "[$(date '+%H:%M:%S')] $stem NOT STARTED: system free memory $f % < 25 %" >> $L/driver.log
    return 1
  fi
  echo "[$(date '+%H:%M:%S')] $stem START (free $f %)" >> $L/driver.log
  $PY $D/a3_replay.py replay --stem $stem >> $L/$stem.log 2>&1
  local rc=$?
  echo "[$(date '+%H:%M:%S')] $stem EXIT $rc" >> $L/driver.log
  return $rc
}

for s in $(cat $L/stems.txt); do
  one $s &
done
wait
echo "[$(date '+%H:%M:%S')] A3 ALL RECORDINGS DONE" >> $L/driver.log
