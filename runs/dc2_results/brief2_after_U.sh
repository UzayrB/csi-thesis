#!/bin/zsh
# The second brief's queue after the unconstrained runs (Uzayr: no competing compute while they go): item 4's
# profile, then item 3c's candidate chain (runs/dc2_results/dot_chain.sh).
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
until grep -q "UNC DONE\|UNC FAILED" runs/dc2_results/logs/unc_chain2.log; do sleep 30; done
echo "[$(date '+%H:%M:%S')] the unconstrained runs are done"
(caffeinate -dimsu python3 -m pipeline.live.press_profile --recording B2/participant_PA5_walk --presses 3 > runs/dc2_results/logs/press_profile.log 2>&1; echo "[$(date '+%H:%M:%S')] EXIT $? press_profile") &
runs/dc2_results/dot_chain.sh > runs/dc2_results/logs/dot_chain.log 2>&1
echo "[$(date '+%H:%M:%S')] EXIT $? dot_chain"
wait
echo "AFTER_U DONE $(date '+%F %T')"
