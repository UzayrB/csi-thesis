#!/bin/zsh
# Rewrites HEARTBEAT.txt every 60 s: the runner, the job running, every job's state, the v2 run, and
# ALERT lines for a failed job, a dead runner or a job silent for over 45 minutes.
Q=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/dev/queue
H=/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code/runs/identify/dev/HEARTBEAT.txt
while [[ ! -e $Q/STOP_HEARTBEAT ]]; do
  {
    echo "heartbeat $(date '+%Y-%m-%d %H:%M:%S')"
    for lane in $(cd $Q && ls runner*.pid 2>/dev/null | sed 's/.pid$//'); do
      rp=$(cat $Q/$lane.pid 2>/dev/null)
      if [[ -n "$rp" ]] && kill -0 $rp 2>/dev/null; then echo "$lane: alive (pid $rp)"; else echo "ALERT $lane not running"; fi
    done
    v2=$(pgrep -f '^/opt/anaconda3/bin/python3 -m pipeline.identify.idv2_run' | head -1)
    [[ -n "$v2" ]] && echo "v2 run: alive (pid $v2, cpu $(ps -o time= -p $v2 | tr -d ' '))" || echo "v2 run: not running"
    for f in $Q/state/*(N); do
      s=$(cat $f); echo "job $(basename $f): $s"
      [[ "$s" == FAILED* ]] && echo "ALERT job $(basename $f) $s"
      if [[ "$s" == RUNNING* ]]; then
        lg=$Q/logs/$(basename $f).log
        age=$(( $(date +%s) - $(stat -f %m $lg 2>/dev/null || date +%s) ))
        echo "  last log line: $(tail -1 $lg 2>/dev/null | cut -c1-150)"
        (( age > 9000 )) && echo "ALERT job $(basename $f) log silent for $((age/60)) min"
      fi
    done
    pending=$(cat $Q/jobs*.txt 2>/dev/null | grep -v '^#' | cut -d'|' -f1 | while read n; do [[ -n "$n" && ! -e $Q/state/$n ]] && echo $n; done | tr '\n' ' ')
    echo "queued: ${pending:-none}"
  } > $H.tmp && mv $H.tmp $H
  sleep 60
done
