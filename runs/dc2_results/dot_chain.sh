#!/bin/zsh
# Item 3c (rule/DOT_PREREG.md, hashed 26b41a5b): the five display candidates on the three rotations through the app
# (semi mode, causal clock), one process per recording, at most 6 at once; then the rule.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
(cd runs/dc2_results/rule && shasum -a 256 -c DOT_PREREG.md.sha256) || { echo "DOT FAILED: the rule changed"; exit 1; }
heavy() { pgrep -f "app_replay --inner|unconstrained choose_m --inner|final_model gate --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 6 ]; do sleep 15; done; }
for K in K0 K1 K2 K1g K2g; do
  for pair in "rotB1 B1 room_B/session_B2" "rotA2 02 room_A/session_02" "rotA1 01 room_A/session_01"; do
    set -- ${=pair}
    model=$1; sess=$2
    dir=data/$([ $sess = B1 ] && echo room_B/session_B1 || echo room_A/session_$sess)
    for stem in $(ls $dir/participant_*walk.gt.json | xargs -n1 basename | sed 's/.gt.json//' | grep -v "_C_walk"); do
      slot
      echo "[$(date '+%H:%M:%S')] START $K $model $sess/$stem"
      (caffeinate -dimsu python3 -m pipeline.live replay --recording $sess/$stem --presses start --model $model --clock causal --display $K; echo "[$(date '+%H:%M:%S')] EXIT $? $K $model $sess/$stem") &
      sleep 15
    done
  done
done
wait
python3 -c "from pipeline.live.app_score import choose_dot; choose_dot()"
echo "DOT DONE $(date '+%F %T')"
