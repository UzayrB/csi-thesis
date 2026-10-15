#!/bin/zsh
# Finish the last decodes at normal priority (8 Oct addendum, 22:3x): resume each from its scratch tree.
setopt NO_BG_NICE   # zsh runs background jobs at nice +5 by default (BG_NICE); the decodes must not be niced
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
A=runs/ablations/stride_mix_2026-10-08
caffeinate -dimsu -w $$ &
/opt/anaconda3/bin/python3 $A/mem_guard.py $$ >> $A/logs/mem_guard.stdout 2>&1 &
pids=()
for item in "A2 ALL05 2" "A1 MIX 2" "A1 ALL1 2" "A1 ALL05 2"; do
  set -- ${=item}
  ( t0=$(date +%s); OMP_NUM_THREADS=1 PYTHONPATH=. /opt/anaconda3/bin/python3 $A/eval_one.py --rot $1 --arm $2 --k $3 >> $A/runs/$1/eval_$2_k$3.log 2>&1; rc=$?
    echo "[$(date '+%H:%M:%S')] finish: $1 $2 k$3 exit $rc in $(( ($(date +%s) - t0) / 60 )) min" >> $A/logs/run.log ) &
  pids+=($!)
done
wait $pids
echo "[$(date '+%H:%M:%S')] finish: all four decodes ended" >> $A/logs/run.log
