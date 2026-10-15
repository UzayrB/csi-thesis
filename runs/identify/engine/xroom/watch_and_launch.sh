#!/bin/zsh
# Waits for the machine, then starts run_xroom.sh (PREREG_XROOM_V4.md section 7; the Mastermind's conditions, 9 Oct).
# Launch only when all hold on two checks 60 s apart:
#   (a) runs/a3_clean_2026-10-08/machine_state.py is-quiet exits 0;
#   (b) the Now paragraph does not contain STOPPED (run_dot.sh also writes QUIET when a stage fails, and may resume);
#   (c) no process with runs/a3_clean_2026-10-08/ in its command line is alive.
# QUIET with STOPPED is a HOLD: no launch; the Mastermind decides. Run detached: nohup zsh <this> &!
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code || exit 1
PY=/opt/anaconda3/bin/python3
D=runs/identify/engine/xroom
LG=$D/logs
mkdir -p $LG
W=$LG/watcher.log
say() { echo "[$(date '+%H:%M:%S')] $*" >> $W }

state() {
  $PY runs/a3_clean_2026-10-08/machine_state.py is-quiet || return 1
  $PY $D/ms_xr.py now | grep -q STOPPED && return 2
  [ $(ps -A -o command= | grep -c '[r]uns/a3_clean_2026-10-08/') -eq 0 ] || return 3
  return 0
}

say "watcher starts (pid $$)"
last=x
while true; do
  state
  r=$?
  if [ $r -eq 0 ]; then
    sleep 60
    state
    r=$?
    if [ $r -eq 0 ]; then
      say "LAUNCH: QUIET, no STOPPED, no dot-side process, on two checks 60 s apart"
      break
    fi
  fi
  if [ "$r" != "$last" ]; then
    case $r in
      1) say "waiting: the Now paragraph is not QUIET" ;;
      2) say "HOLD: QUIET with STOPPED; not launching (message the Mastermind)" ;;
      3) say "waiting: QUIET but a dot-side process is alive" ;;
    esac
  fi
  last=$r
  sleep 60
done
nohup zsh $D/run_xroom.sh >> $LG/driver.out 2>&1 &!
say "driver launched"
exit 0
