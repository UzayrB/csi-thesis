#!/bin/zsh
# The Third overall chat's cross-room identification run (runs/identify/engine/PREREG_XROOM_V4.md, section 7). Started by
# watch_and_launch.sh once the machine is QUIET. One step at a time, nice 10, one caffeinate for the whole run, MPS
# watermarks 0.3 / 0.2. Every step runs under the memory guard of runs/identify/window_gait/queue/run_guarded.sh (1 Oct):
# checked every 10 s, this run's own process alone is killed if free memory falls below 30 % or its footprint passes
# 6 GB. Any kill or non-zero exit (a Metal or MPS crash included) is a STOP, never a restart: QUIET with STOPPED.
# Resume (after a stop and a dated note in the addendum): a step whose output exists is skipped; the replay and CAL-none
# steps take their footprint limit and MPS watermarks from REPLAY_GB, REPLAY_HW, REPLAY_LW (default 6, 0.3, 0.2);
# RESUME_NOTE replaces the first log line; START_LEFT the first ETA (minutes).
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
export OMP_NUM_THREADS=1 PYTHONPATH=. PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.2
PY=/opt/anaconda3/bin/python3
D=runs/identify/engine/xroom
LG=$D/logs
mkdir -p $LG $D/audit
ms() { $PY $D/ms_xr.py "$@" }
LIMIT=6
RGB=${REPLAY_GB:-6}
RHW=${REPLAY_HW:-0.3}
RLW=${REPLAY_LW:-0.2}
R=runs/identify/engine/replays
skip() { [ -f "$2" ] && { note "SKIP $1 (output exists: $2)"; return 0 }; return 1 }
note() { echo "[$(date '+%H:%M:%S')] $*" >> $LG/run.log }

# guarded NAME MINUTES_LEFT "STEP TEXT" command...
guarded() {
  local name=$1 left=$2 text=$3
  shift 3
  ms update "$text" $left
  note "START $name"
  nice -n 10 "$@" > $LG/$name.log 2>&1 &
  local pid=$! killed=0 free mem gb rc
  while kill -0 $pid 2>/dev/null; do
    free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
    mem=$(top -l 1 -pid $pid -stats mem | tail -1)
    gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
    echo "[$(date '+%H:%M:%S')] $name pid $pid footprint $mem free ${free}%" >> $LG/guard.log
    if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > $LIMIT" | bc -l) -eq 1 ]; then
      kill $pid
      killed=1
      note "KILLED $name (pid $pid): footprint $mem, free ${free}%"
      break
    fi
    sleep 10
  done
  wait $pid
  rc=$?
  note "END $name rc $rc"
  if [ $killed -eq 1 ] || [ $rc -ne 0 ]; then
    note "STOPPED at $name (rc $rc, killed $killed)"
    ms log "xroom run STOPPED at $name (exit $rc$([ $killed -eq 1 ] && echo ', killed by the memory guard')); caffeinate released, nothing heavy running"
    ms quiet "Third overall's xroom run STOPPED at $name"
    exit 1
  fi
}

note "driver starts (pid $$)"
caffeinate -dimsu -w $$ &!
note "caffeinate held for the driver (pid $$); $(pmset -g batt | head -1); $(pmset -g assertions | grep -c caffeinate) caffeinate assertion lines"
ms busy "the substitution check (CPU, 1 process, about 5 min). Then four trainings (GPU, one at a time, about 20.5 min each), each followed by its open-file audit, A3 and B2 replays and CAL-none (GPU, about 5.5 min); then scoring." ${START_LEFT:-113}
if [ -n "$RESUME_NOTE" ]; then ms log "$RESUME_NOTE"; else ms log "starts the identification cross-room run (runs/identify/engine/PREREG_XROOM_V4.md, 0c3f7ec2; Uzayr's go). Cost estimate: substitution check about 5 min (CPU, 1 process); four trainings about 20.5 min each (GPU, one at a time; CNNs 6,000 steps on mps, measured 18.6 to 20.8 min); per model the audit, A3 and B2 replays and CAL-none about 5.5 min (GPU); scoring about 2 min (CPU); about 1 h 55 min in all. nice 10, one caffeinate, MPS watermarks 0.3/0.2, memory guard (own PID only)."; fi
note "limits: training ${LIMIT} GB, MPS 0.3/0.2; replays and CAL-none ${RGB} GB, MPS ${RHW}/${RLW}; free-memory floor 30 %"

skip substitution $D/audit/substitution.json || guarded substitution 111 "the substitution check, four models (CPU, 1 process, about 5 min)." \
  $PY -m pipeline.identify.ixr_train substitution

left=106
for m in xr_AB xr_A xr_ABtrk xr_B1; do
  skip train_$m runs/identify/engine/models/${m}_v4/meta_feat_cnn.json || guarded train_$m $left "training ${m}_v4 (GPU, 1 process, about 20.5 min)." \
    $PY -m pipeline.identify.ixr_train train $m --device mps
  guarded audit_$m $(( left - 20 )) "the open-file audit of ${m}_v4 (CPU, seconds)." \
    $PY -m pipeline.identify.ixr_train audit $m
  LIMIT=$RGB
  skip replay_${m}_A3 $R/${m}_v4_A3_T4.0.npz || guarded replay_${m}_A3 $(( left - 21 )) "replaying A3 through ${m}_v4 (GPU, 1 process, about 1.2 min)." \
    env PYTORCH_MPS_HIGH_WATERMARK_RATIO=$RHW PYTORCH_MPS_LOW_WATERMARK_RATIO=$RLW $PY -m pipeline.identify.ide_replay --session A3 --model ${m}_v4 --T 4.0 --device mps
  skip replay_${m}_B2 $R/${m}_v4_B2_T4.0.npz || guarded replay_${m}_B2 $(( left - 22 )) "replaying B2 through ${m}_v4 (GPU, 1 process, about 2.8 min)." \
    env PYTORCH_MPS_HIGH_WATERMARK_RATIO=$RHW PYTORCH_MPS_LOW_WATERMARK_RATIO=$RLW $PY -m pipeline.identify.ide_replay --session B2 --model ${m}_v4 --T 4.0 --device mps
  skip calnone_${m}_A3 $R/${m}_v4_A3_T4.0_calnone.npz || guarded calnone_${m}_A3 $(( left - 25 )) "CAL-none on A3 for ${m}_v4 (GPU, 1 process)." \
    env PYTORCH_MPS_HIGH_WATERMARK_RATIO=$RHW PYTORCH_MPS_LOW_WATERMARK_RATIO=$RLW $PY -m pipeline.identify.ixr_eval calnone --model ${m}_v4 --session A3 --device mps
  skip calnone_${m}_B2 $R/${m}_v4_B2_T4.0_calnone.npz || guarded calnone_${m}_B2 $(( left - 25 )) "CAL-none on B2 for ${m}_v4 (GPU, 1 process)." \
    env PYTORCH_MPS_HIGH_WATERMARK_RATIO=$RHW PYTORCH_MPS_LOW_WATERMARK_RATIO=$RLW $PY -m pipeline.identify.ixr_eval calnone --model ${m}_v4 --session B2 --device mps
  LIMIT=6
  ms log "${m}_v4 trained, audited (open trace PASSED), replayed on A3 and B2, CAL-none done"
  left=$(( left - 26 ))
done

guarded score 2 "scoring (CPU, 1 process, about 2 min)." \
  $PY -m pipeline.identify.ixr_eval score
note "DONE: eval_xroom_v4.json written"
ms log "xroom run compute done (eval_xroom_v4.json written); caffeinate released; commit, push and report follow (light)"
ms quiet "Third overall's xroom run ended"
note "QUIET written"
exit 0
