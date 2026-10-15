#!/bin/zsh
# Part 2 of the components-and-features TEST (PLAN.md, Part 2 note, 72af18c1): the permutations, then the analysis and
# the figure. CPU only, nice 19, OMP_NUM_THREADS=1. Usage: run_part2.sh 1   (one process)
#                                                        run_part2.sh 4   (one permutation process per model)
# Launched detached from the Code root; every step's exit code is captured before anything else is logged.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
export OMP_NUM_THREADS=1 PYTHONPATH=.
PY=/opt/anaconda3/bin/python3
LOG=runs/identify/v6_test/logs/part2_driver.log
mkdir -p runs/identify/v6_test/logs
say() { print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> $LOG }
say "START mode $1 (pid $$)"
if [[ "$1" == "4" ]]; then
  pids=()
  for m in xr_ABtrk xr_A loso_B1 loso_B2; do
    nice -n 19 $PY -m pipeline.identify.iv6_features permute $m > runs/identify/v6_test/logs/permute_$m.log 2>&1 &
    pids+=($!)
    say "permute $m pid $!"
  done
  fail=0
  for p in $pids; do
    wait $p; rc=$?
    say "permute pid $p rc $rc"
    (( rc != 0 )) && fail=1
  done
else
  nice -n 19 $PY -m pipeline.identify.iv6_features permute > runs/identify/v6_test/logs/permute_all.log 2>&1
  rc=$?
  say "permute (all) rc $rc"
  fail=$(( rc != 0 ))
fi
if (( fail )); then
  say "STOP: a permutation process failed; no analysis"
  exit 2
fi
nice -n 19 $PY -m pipeline.identify.iv6_features analyse > runs/identify/v6_test/logs/analyse.log 2>&1
rc=$?
say "analyse rc $rc"
(( rc != 0 )) && exit 3
nice -n 19 $PY -m pipeline.identify.iv6_features figure > runs/identify/v6_test/logs/figure.log 2>&1
rc=$?
say "figure rc $rc"
say "END"
