#!/bin/zsh
# Uzayr's decisions of 1 Oct (reports/BRIEF_LIVE_APP_3_2026-10-01.md): K1g as the app's display. G2; the 12 renders
# (the final model's semi replays, at real-time pace, the screen recorded); the zero-shot semi replays; the fully
# constrained replays; the unconstrained view of PA2 for the teaching pack; the teaching pack v3. New folders
# (_disp-K1g), K0's stay beside them. 6 processes at most.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
APP=$(python3 -c "from pipeline.live.final_model import DISPLAY_CANDIDATE as K; print(K)")
[ "$APP" = "K1g" ] || { echo "K1G FAILED: the app's display is $APP"; exit 1; }
heavy() { pgrep -f "app_replay --inner|final_model gate --inner|pipeline.live.app_teaching --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 6 ]; do sleep 15; done; }
V=relgateU+abstain+a2w0.25
for cell in fin_B2 zsf_B2 fin_A3; do
  slot; echo "[$(date '+%H:%M:%S')] START G2 $cell"
  (caffeinate -dimsu python3 -m pipeline.live.final_model gate --cell $cell --ref FC.$V --variant $V --mode semi; echo "[$(date '+%H:%M:%S')] EXIT $? G2 $cell") &
  sleep 15
done
stems() { ls data/$1/participant_*walk.gt.json | xargs -n1 basename | sed 's/.gt.json//' | grep -v "_C_walk"; }
jobs_for() {
  for stem in $(stems room_B/session_B2); do
    echo "B2/$stem|--model final --presses start --realtime --screen runs/live/renders_K1g"
    echo "B2/$stem|--model zeroshot --presses start"
    echo "B2/$stem|--model final --presses start_end"
    echo "B2/$stem|--model zeroshot --presses start_end"
  done
  for stem in $(stems room_A/session_03); do
    echo "03/$stem|--model final --presses start --realtime --screen runs/live/renders_K1g"
    echo "03/$stem|--model final --presses start_end"
  done
  echo "B2/participant_PA2_walk|--model final --presses none --m 4"
}
jobs_for | while IFS='|' read rec args; do
  slot; echo "[$(date '+%H:%M:%S')] START $rec $args"
  (caffeinate -dimsu python3 -m pipeline.live replay --recording $rec ${=args} --clock causal --display K1g; echo "[$(date '+%H:%M:%S')] EXIT $? $rec $args") &
  sleep 15
done
wait
echo "[$(date '+%H:%M:%S')] START teaching pack v3"
TEACHING_OUT=teaching_pack_app_v3_2026-10-01.json TEACHING_UNC_LOG=runs/live/replay/final/unconstrained_m4_disp-K1g_causal/B2__participant_PA2_walk.jsonl \
  caffeinate -dimsu python3 -m pipeline.live.app_teaching
echo "[$(date '+%H:%M:%S')] EXIT $? teaching pack v3"
echo "K1G DONE $(date '+%F %T')"
