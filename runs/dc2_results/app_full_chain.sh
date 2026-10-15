#!/bin/zsh
# The fully constrained mode (the user's order: after E), relaunched after the rescore slice fix (12:19). Each
# replay starts when tracking runs fewer than 4 heavy processes; once all three have started, the paused
# unconstrained chain (PID 80355) is resumed.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
heavy() { pgrep -f "app_replay --inner|final_model gate --inner|pd_clean decode --inner|pd_disp_prov (cap_inner|app_cap_inner)|unconstrained choose_m --inner|pipeline.live.app_teaching --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 4 ]; do sleep 15; done; }
for job in "--session B2 --presses start_end --model final" "--session 03 --presses start_end --model final" "--session B2 --presses start_end --model zeroshot"; do
  slot
  echo "[$(date '+%H:%M:%S')] START full $job"
  (caffeinate -dimsu python3 -m pipeline.live replay ${=job} --clock causal; echo "[$(date '+%H:%M:%S')] EXIT $? full $job") &
  sleep 60
done
kill -CONT 80355 && echo "[$(date '+%H:%M:%S')] unconstrained chain resumed"
wait
echo "FULL DONE $(date '+%F %T')"
