#!/bin/zsh
# The Third overall chat's Room A run (runs/identify/roomA/PLAN_RA.md; copied from the best-model run's tested run_b.sh). Exploratory development,
# all data seen; adopt nothing. One driver with two queues that may overlap (the
# Mastermind's rule: at most one GPU block and one CPU-heavy block at a time): STEPS_GPU and STEPS_CPU, each executed line
# by line as lines are appended (only after the Mastermind grants each block's slot):
#   BLOCK GPU|CPU <minutes> <text>   start a block: battery check (GPU blocks never start on battery), BUSY or Now updated
#   STEP NAME LIMIT_GB HW LW CMD...  one step under run_lw.sh's memory guard (own process killed below 30 % free or above
#                                    the limit; top reads whole GB above 10 GB, so "13G" against a 12 GB limit kills)
#   WAITFREE <pct>                   wait until the other queue has no active block, or free memory >= pct
#   PSTEP NAME LIMIT_GB HW LW CMD... a step run in parallel inside the block (CPU only; at most eight at once)
#   PWAIT                            wait for the block's parallel steps; a failed one skips the rest of the block
#   WAITPID <pid>                    wait until a process (the block-1 driver) has exited
#   CLEAR <name> <text>              end an external block registered in active/ (block 1): log; QUIET only if none left
# Every step waits for at least 45 % free memory before it starts (50 % for a 12 GB scoring step; the Mastermind, 01:3x and 01:5x).
# Queues are named on the command line: run_lp.sh GPU CPU1 CPU2 ... (STEPS_<queue> each; at most eight CPU queues).
#   ENDBLOCK <text>                  end a block: log; QUIET only when no other block is active
#   FINISH                           end that queue (the driver ends when both have)
# No caffeinate: the Mastermind holds the single one for the whole job (Uzayr's instruction). A failed or killed step is
# BLOCKED and the rest of its block skipped. Every MACHINE_STATE write is read back (ms_ra.py), under a lock.
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
export OMP_NUM_THREADS=1 PYTHONPATH=.
PY=/opt/anaconda3/bin/python3
D=runs/identify/roomA
LG=$D/logs
AC=$D/active
mkdir -p $LG $AC
note() { echo "[$(date '+%H:%M:%S')] $*" >> $LG/run.log }
ms() {
  while ! mkdir $D/ms.lock 2>/dev/null; do sleep 0.3; done
  $PY $D/ms_ra.py "$@" || note "MS WRITE NOT CONFIRMED: $1 $2"
  rmdir $D/ms.lock
}
active() { ls $AC 2>/dev/null | tr '\n' ' ' }

queue_loop() {
  local Q=$1 S=$D/STEPS_$1 n=0 skipping=0 inblock=0 LIMIT=6 line kind where mins total
  touch $S
  guarded() {
    local name=$1 lim=$2 hw=$3 lw=$4
    shift 4
    LIMIT=$lim
    local need=$([ $lim -ge 12 ] && echo 50 || echo 45) fr0
    while true; do
      fr0=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
      [ ${fr0:-0} -ge $need ] && break
      note "[$Q] $name waits: free ${fr0} % below ${need} %"
      sleep 30
    done
    note "[$Q] START $name"
    env PYTORCH_MPS_HIGH_WATERMARK_RATIO=$hw PYTORCH_MPS_LOW_WATERMARK_RATIO=$lw nice -n 10 "$@" < /dev/null > $LG/$name.log 2>&1 &
    local pid=$! killed=0 free mem gb rc
    while kill -0 $pid 2>/dev/null; do
      free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
      mem=$(top -l 1 -pid $pid -stats mem | tail -1)
      gb=$(echo $mem | awk '/G/ {sub("G[+-]?","",$1); print $1+0; next} /M/ {sub("M[+-]?","",$1); print $1/1024; next} {print 0}')
      echo "[$(date '+%H:%M:%S')] $name pid $pid footprint $mem free ${free}%" >> $LG/guard.log
      if [ ${free:-100} -lt 30 ] || [ $(echo "$gb > $LIMIT" | bc -l) -eq 1 ]; then
        kill $pid
        killed=1
        note "[$Q] KILLED $name (pid $pid): footprint $mem, free ${free}%"
        break
      fi
      sleep 10
    done
    wait $pid
    rc=$?
    note "[$Q] END $name rc $rc"
    if grep -qiE "MTLCompilerService|metal|mps.*(error|out of memory)" $LG/$name.log; then
      note "[$Q] METAL/MPS message in $name.log: STOP (no restart)"
      killed=2
    fi
    if [ $killed -ne 0 ] || [ $rc -ne 0 ]; then
      note "[$Q] BLOCKED $name (rc $rc, killed $killed); the rest of this block is skipped"
      ms log "room A: step $name BLOCKED (exit $rc, killed $killed); the rest of its block skipped"
      skipping=1
    fi
  }
  while true; do
    total=$(wc -l < $S | tr -d ' ')
    if [ $n -ge $total ]; then
      sleep 20
      continue
    fi
    n=$(( n + 1 ))
    line=$(sed -n "${n}p" $S)
    set -- ${=line}
    kind=$1
    shift
    case $kind in
      BLOCK)
        where=$1 mins=$2
        shift 2
        skipping=0
        if [ $where = GPU ] && pmset -g batt | head -1 | grep -q "Battery Power"; then
          note "[$Q] HOLD: GPU block not started on battery ($*); its steps are skipped"
          skipping=1
          continue
        fi
        inblock=1
        note "[$Q] BLOCK START ($where, about $mins min): $*"
        if [ -z "$(active)" ]; then
          echo "$*" > $AC/$Q
          ms busy "$*" $mins
        else
          echo "$*" > $AC/$Q
          ms update "blocks running: $(cat $AC/* | tr '\n' ' ')" $mins
        fi
        ms log "room A: block starts ($where, about $mins min): $*"
        ;;
      STEP)
        if [ $skipping -eq 1 ]; then
          note "[$Q] SKIPPED $1 (block stopped or held)"
          continue
        fi
        guarded "$@"
        ;;
      ENDBLOCK)
        note "[$Q] BLOCK END: $*"
        if [ $inblock -eq 1 ]; then
          rm -f $AC/$Q
          ms log "room A: block ends: $*"
          if [ -z "$(active)" ]; then
            ms quiet "Third overall's Room A block ended: $*"
          else
            ms update "blocks running: $(cat $AC/* | tr '\n' ' ')" 30
          fi
        fi
        inblock=0
        skipping=0
        ;;
      WAITFREE)
        local other=$([ $Q = GPU ] && echo CPU1 || echo GPU) fr
        note "[$Q] WAITFREE: the $other queue idle, or free memory >= $1 %"
        while true; do
          fr=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
          { [ ! -f $AC/$other ] || [ ${fr:-0} -ge $1 ]; } && break
          sleep 30
        done
        note "[$Q] WAITFREE met (free ${fr} %, $other active: $([ -f $AC/$other ] && echo yes || echo no))"
        ;;
      PSTEP)
        if [ $skipping -eq 1 ]; then
          note "[$Q] SKIPPED $1 (block stopped or held)"
          continue
        fi
        ( guarded "$@"; [ $skipping -eq 1 ] && touch $LG/failed_${Q}_$1 ) &
        sleep 2
        ;;
      PWAIT)
        wait
        local fl=$(find $LG -maxdepth 1 -name "failed_${Q}_*" 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ')
        if [ -n "$fl" ]; then
          note "[$Q] a parallel step failed ($fl): the rest of the block is skipped"
          find $LG -maxdepth 1 -name "failed_${Q}_*" -delete
          skipping=1
        fi
        ;;
      WAITPID)
        note "[$Q] WAITPID $1"
        while kill -0 $1 2>/dev/null; do sleep 15; done
        note "[$Q] WAITPID $1: gone"
        ;;
      CLEAR)
        local nm=$1
        shift
        rm -f $AC/$nm
        note "[$Q] CLEAR $nm: $*"
        ms log "room A: block ends: $*"
        if [ -z "$(active)" ]; then
          ms quiet "Third overall's Room A block ended: $*"
        else
          ms update "blocks running: $(cat $AC/* | tr '\n' ' ')" 30
        fi
        ;;
      FINISH)
        note "[$Q] FINISH: queue ends"
        return 0
        ;;
      \#*|"")
        ;;
      *)
        note "[$Q] UNKNOWN line $n: $line"
        ;;
    esac
  done
}

note "driver (two queues) starts (pid $$); no caffeinate of its own: the Mastermind holds the single one (Uzayr's instruction)"
for q in "$@"; do
  queue_loop $q &
done
wait
note "FINISH: driver ends"
