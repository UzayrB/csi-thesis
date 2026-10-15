#!/bin/zsh
# usage: wait_for.sh job1 job2 ... -- command args. Waits until every named job is DONE (fails if one FAILED),
# then runs the command. Used for jobs that depend on jobs in the other lane.
Q=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/idwalks/queue
names=()
while [[ "$1" != "--" ]]; do names+=("$1"); shift; done
shift
for n in $names; do
  until grep -q DONE $Q/state/$n 2>/dev/null; do
    grep -q FAILED $Q/state/$n 2>/dev/null && { echo "dependency $n FAILED"; exit 4; }
    sleep 30
  done
done
exec "$@"
