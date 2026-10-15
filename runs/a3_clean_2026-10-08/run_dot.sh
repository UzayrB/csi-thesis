#!/bin/zsh
# The dot side's compute (POA_DOT.md section 5). Start it ONLY when runs/MACHINE_STATE.md says QUIET AND Uzayr has said go:
#   nohup runs/a3_clean_2026-10-08/run_dot.sh 6 > runs/a3_clean_2026-10-08/dot/logs/run_dot.out 2>&1 &!
# One caffeinate for the whole run (started beforehand, see below); the memory guard (pause below 25 % free, resume at
# 40 %); every job niced.
# Order: the two held-out heads train on the GPU (one at a time) while P1 runs on the CPU; P1 must pass; then the
# offline gates (C3) and the five stages. It stops at the first failure and resumes where it stopped.
# The full configuration's commit and the A3 decode (a3_full.py) are done by hand after stage 5.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PROCS=${1:-5}
PY=/opt/anaconda3/bin/python3
D=runs/a3_clean_2026-10-08
L=$D/dot/logs
mkdir -p $L
log() { echo "[$(date '+%H:%M:%S')] $*" >> $L/run_dot.log; }

MS() { $PY $D/machine_state.py "$@"; }
MS is-quiet || MS is-mine || { echo "REFUSED: runs/MACHINE_STATE.md says neither QUIET nor this chat's BUSY"; exit 1; }
# ONE caffeinate for the whole run, started before this script and released after the A3 decode (dot/logs/caffeinate.pid)
CAF=$(cat $L/caffeinate.pid 2>/dev/null)
{ [ -n "$CAF" ] && ps -p $CAF -o command= | grep -q caffeinate; } || { echo "REFUSED: no caffeinate held (dot/logs/caffeinate.pid)"; exit 1; }
eta() { date -v+$1M '+%H:%M'; }
MS busy "A3-clean dot side (Uzayr's go). Now: training the two held-out display heads (GPU, one at a time, about 15 min). Then P1, the offline gates, five stages, the config commit and one A3 decode; CPU at most $PROCS niced processes, memory guard. ETA for QUIET about $(eta 540). One caffeinate held for the whole run."
$PY $D/mem_guard.py $$ dot &!
log "start, $PROCS processes"

# Uzayr's order: the two display heads, then the reproduction check
hrc=0
for r in A2 A1; do
  t=$([ $r = A2 ] && echo s01B1_dispend_rot || echo s02B1_dispend_rot)
  if [ ! -f $D/heads/$t/train.json ]; then
    $PY $D/heads.py train --rot $r --device gpu >> $L/heads_train.log 2>&1 || { hrc=$?; break; }
  fi
done
log "heads exit $hrc"
rc=1
if [ $hrc -eq 0 ]; then
  MS update "A3-clean dot side (Uzayr's go). Now: P1, the reproduction check (18 replays, $PROCS niced CPU processes, about 50 min). Then the offline gates, five stages, the config commit and one A3 decode. ETA for QUIET about $(eta 500). One caffeinate held."
  if grep -q '"PASSES": true' $D/dot/p1/P1.json 2>/dev/null; then rc=0; log "P1 passed already (dot/p1/P1.json), kept"; else
    $PY $D/run_dot.py p1 --procs $PROCS; rc=$?
  fi
fi
log "P1 exit $rc"
if [ $rc -ne 0 ] || [ $hrc -ne 0 ]; then
  log "STOP (P1 $rc, heads $hrc)"
  kill $CAF; MS quiet "the dot side STOPPED (P1 $rc, heads $hrc); caffeinate released"
  exit 1
fi

MS update "A3-clean dot side (Uzayr's go). Now: stage 1's offline gates (inference and three substitution decodes, about 25 min). Then five stages, the config commit and one A3 decode. ETA for QUIET about $(eta 450). One caffeinate held."
$PY $D/run_dot.py gates --procs $PROCS; rc=$?
log "gates exit $rc"
[ $rc -ne 0 ] && { kill $CAF; MS quiet "the dot side STOPPED (gates); caffeinate released"; exit 1; }

for n in 1 2 3 4 5; do
  if [ -f $D/dot/stage$n/SELECTION.json ]; then continue; fi
  MS update "A3-clean dot side (Uzayr's go). Now: stage $n of 5 (about 75 min each, $PROCS niced CPU processes). Then the config commit and one A3 decode. ETA for QUIET about $(eta $(( (6 - n) * 75 + 45 )))). One caffeinate held."
  $PY $D/run_dot.py stage $n --procs $PROCS; rc=$?
  log "stage $n exit $rc"
  if [ $rc -ne 0 ]; then
    kill $CAF; MS quiet "the dot side STOPPED at stage $n; caffeinate released"
    exit 1
  fi
done
log "all five stages selected"
MS update "A3-clean dot side (Uzayr's go). Now: the five stages are done; writing and committing the full configuration, then one A3 decode (6 niced CPU processes at most $PROCS, about 40 min). ETA for QUIET about $(eta 60). The same caffeinate is held through it."
