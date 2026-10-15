#!/bin/zsh
# D1 -> D2 chain (tracking attack). Waits for the D1 rotation queue, decides D1 by pd_rule, then
# launches the D2 single-head screen on D1's winner. Written 2026-09-28 23:41.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
while kill -0 76031 2>/dev/null; do sleep 20; done
echo "D1 queue gone at $(date '+%F %T')"
tail -1 runs/dc2_results/logs/queue_d1s.log | grep -q "QUEUE EXIT 0" || { echo "D1 queue did not exit 0; D2 NOT launched"; exit 1; }
python3 -m pipeline.constrained.pd_rule compare --name D1 --base d1sp --arm d1sr || exit 1
python3 -m pipeline.constrained.pd_rule compare --name D1 --base d1sp --arm d1sr --lock scorer || exit 1
N=$(python3 -c "import json;print('r' if json.load(open('runs/dc2_results/rule/D1_display.json'))['ADOPT'] else 'p')")
echo "D1 decision: base prefix d1s$N"
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
C=()
for r in $RT; do C+=(d2${N}_base_$r); done
for v in aug mix early; do for r in $RT; do C+=(d2${N}_${v}_$r); done; done
if [[ $N == p ]]; then for r in $RT; do C+=(d2p_rrel_$r); done; fi
for r in $RT; do C+=(d2${N}_earlyx_$r); done
echo "D2 START $(date '+%F %T'): $C"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells pqueue --cells $C
echo "D2 QUEUE EXIT $? at $(date '+%F %T')"
