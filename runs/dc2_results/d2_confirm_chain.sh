#!/bin/zsh
# D2 confirmation chain (tracking attack): waits for the combination queue, decides whether honest early
# stopping adds to aug+rrel by the rule, then confirms the winner with the full five-head pool on the
# three rotations. Written 2026-09-29 03:56.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
until grep -q "D2 COMBINATION QUEUE EXIT" runs/dc2_results/logs/queue_d2c.log; do sleep 20; done
echo "combination queue done $(date '+%F %T')"
python3 -m pipeline.constrained.pd_rule compare --name D2_arE --base d2p_base --arm d2p_arE | grep -E "Objective|Paired|Decision|guard"
python3 -m pipeline.constrained.pd_rule compare --name D2_arEx --base d2p_base --arm d2p_arEx | grep -E "Objective|Paired|Decision|guard"
python3 -m pipeline.constrained.pd_rule compare --name D2_arEx_over_ar --base d2p_ar --arm d2p_arEx | grep -E "Objective|Paired|Decision|guard"
W=$(python3 -c "import json;print('arE' if json.load(open('runs/dc2_results/rule/D2_arEx_over_ar_display.json')).get('ADOPT') else 'ar')")
echo "D2 winner for the confirmation: $W"
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
C=()
if [[ $W == arE ]]; then
  for r in $RT; do C+=(d2pc_arE_$r); done
  for r in $RT; do C+=(d2pc_arEx_$r); done
else
  for r in $RT; do C+=(d2pc_ar_$r); done
fi
echo "D2 CONFIRM START $(date '+%F %T'): $C"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells pqueue --cells $C
echo "D2 CONFIRM QUEUE EXIT $? at $(date '+%F %T')"
P=d2pc_ar; [[ $W == arE ]] && P=d2pc_arEx
python3 -m pipeline.constrained.pd_rule compare --name D2_confirm_${W} --base d1sp --arm $P
python3 -m pipeline.constrained.pd_rule compare --name D2_confirm_${W} --base d1sp --arm $P --lock scorer
echo "D2 CONFIRM RULES DONE $(date '+%F %T')"
