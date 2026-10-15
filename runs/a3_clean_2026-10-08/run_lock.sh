#!/bin/zsh
# The lock-side run (PREREG.md section 8): two lanes, at most two CPU processes. Lane 1: B1 then A1. Lane 2: A2.
# A lane starts its next rotation only while system free memory is at least 25 %; otherwise it stops and logs why.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/a3_clean_2026-10-08
L=$D/lock/logs
mkdir -p $L

free_pct() { memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}'; }

one() {
  local rot=$1
  local f=$(free_pct)
  if [ "$f" -lt 25 ]; then
    echo "[$(date '+%H:%M:%S')] $rot NOT STARTED: system free memory $f % < 25 %" >> $L/driver.log
    return 1
  fi
  echo "[$(date '+%H:%M:%S')] $rot START (free $f %)" >> $L/driver.log
  $PY $D/lock_side.py decode --rot $rot >> $L/$rot.log 2>&1
  local rc=$?
  echo "[$(date '+%H:%M:%S')] $rot EXIT $rc" >> $L/driver.log
  return $rc
}

( one B1 && one A1 ) &
( one A2 ) &
wait
echo "[$(date '+%H:%M:%S')] ALL LANES DONE" >> $L/driver.log
