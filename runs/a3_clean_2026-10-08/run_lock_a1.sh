#!/bin/zsh
# PREREG_ADDENDUM_1.md: A1's remaining 31 arms on four niced CPU processes, disjoint subsets (lock/logs/A1_split.txt).
# Each process starts only while system free memory is at least 25 %.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/a3_clean_2026-10-08
L=$D/lock/logs

free_pct() { memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}'; }

part() {
  local i=$1; shift
  local f=$(free_pct)
  if [ "$f" -lt 25 ]; then
    echo "[$(date '+%H:%M:%S')] A1 part $i NOT STARTED: system free memory $f % < 25 %" >> $L/driver.log
    return 1
  fi
  echo "[$(date '+%H:%M:%S')] A1 part $i START (free $f %): $*" >> $L/driver.log
  $PY $D/lock_side.py decode --rot A1 --arms "$@" >> $L/A1_p$i.log 2>&1
  local rc=$?
  echo "[$(date '+%H:%M:%S')] A1 part $i EXIT $rc" >> $L/driver.log
  return $rc
}

part 0 sd2.5_soft_w1.0 sd3.0_soft_w1.0 sd3.5_soft_w1.0 sd4.0_soft_w1.0 sd4.5_soft_w0 sd5.0_soft_w0 sd5.5_soft_w0 sd6.0_soft_w0 &
part 1 sd2.5_soft_w0 sd3.0_soft_w0 sd3.5_soft_w0 sd4.0_soft_w0 sd4.5_free_w1.0 sd5.0_free_w1.0 sd5.5_free_w1.0 sd6.0_free_w1.0 &
part 2 sd2.5_free_w1.0 sd3.0_free_w1.0 sd3.5_free_w1.0 sd4.0_free_w1.0 sd4.5_free_w0 sd5.0_free_w0 sd5.5_free_w0 sd6.0_free_w0 &
part 3 sd2.5_free_w0 sd3.0_free_w0 sd3.5_free_w0 sd4.0_free_w0 sd5.0_soft_w1.0 sd5.5_soft_w1.0 sd6.0_soft_w1.0 &
wait
echo "[$(date '+%H:%M:%S')] A1 ALL PARTS DONE" >> $L/driver.log
