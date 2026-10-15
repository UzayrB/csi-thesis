#!/bin/zsh
# Item 3d: the chosen display (runs/dc2_results/display/DOT_CHOICE.json, applied as final_model.DISPLAY_CANDIDATE)
# on the test sessions, once: G2 (semi, whole-file clock; must stay 120/120), the semi and fully constrained
# replays (causal clock) of A3, B2 and zero-shot B2. New folders (`_disp-<K>`), so the old logs stay beside them.
# The rule chose K0 (20:53), the display of the committed renders, so the 12 renders are not remade unless a log
# differs from its committed counterpart. One process per recording, 6 at most.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
K=$(python3 -c "import json;print(json.load(open('runs/dc2_results/display/DOT_CHOICE.json'))['chosen'])")
APP=$(python3 -c "from pipeline.live.final_model import DISPLAY_CANDIDATE as K; print(K)")
[ "$K" = "$APP" ] || { echo "3D FAILED: the app's DISPLAY_CANDIDATE ($APP) is not the choice ($K)"; exit 1; }
echo "[$(date '+%H:%M:%S')] the chosen display: $K"
heavy() { pgrep -f "app_replay --inner|unconstrained choose_m --inner|final_model gate --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 6 ]; do sleep 15; done; }
V=relgateU+abstain+a2w0.25
for cell in fin_B2 zsf_B2 fin_A3; do
  slot; echo "[$(date '+%H:%M:%S')] START G2 $cell"
  (caffeinate -dimsu python3 -m pipeline.live.final_model gate --cell $cell --ref FC.$V --variant $V --mode semi; echo "[$(date '+%H:%M:%S')] EXIT $? G2 $cell") &
  sleep 15
done
stems() { ls data/$1/participant_*walk.gt.json | xargs -n1 basename | sed 's/.gt.json//' | grep -v "_C_walk"; }
for stem in $(stems room_B/session_B2); do
  for job in "--model final --presses start" "--model zeroshot --presses start" \
             "--model final --presses start_end" "--model zeroshot --presses start_end"; do
    slot; echo "[$(date '+%H:%M:%S')] START B2/$stem $job"
    (caffeinate -dimsu python3 -m pipeline.live replay --recording B2/$stem ${=job} --clock causal --display $K; echo "[$(date '+%H:%M:%S')] EXIT $? B2/$stem $job") &
    sleep 15
  done
done
for stem in $(stems room_A/session_03); do
  for job in "--model final --presses start" "--model final --presses start_end"; do
    slot; echo "[$(date '+%H:%M:%S')] START 03/$stem $job"
    (caffeinate -dimsu python3 -m pipeline.live replay --recording 03/$stem ${=job} --clock causal --display $K; echo "[$(date '+%H:%M:%S')] EXIT $? 03/$stem $job") &
    sleep 15
  done
done
wait
echo "3D DONE $(date '+%F %T')"
