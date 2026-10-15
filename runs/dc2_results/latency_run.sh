#!/bin/zsh
# APP_PREREG section 5: the latency figures from a replay on a quiet machine (Identification paused, tracking's
# other processes stopped by PID). B2, final model, semi mode, the as-it-arrives clock, full speed.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
P=($(pgrep -f "unconstrained choose_m --inner"))
echo "[$(date '+%H:%M:%S')] pausing ${P[*]}"; kill -STOP ${P[@]}
uptime
caffeinate -dimsu python3 -m pipeline.live replay --session B2 --presses start --model final --clock causal
rc=$?
kill -CONT ${P[@]}; echo "[$(date '+%H:%M:%S')] EXIT $rc latency; resumed ${P[*]}"
uptime
