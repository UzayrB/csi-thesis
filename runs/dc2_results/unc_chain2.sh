#!/bin/zsh
# The unconstrained mode, continued (14:08; Identification finished, the machine is free; at most 6 heavy processes
# for memory, 2.8 GB each): B1's m grid runs on (PID 83121, display on); A2 and A1 run one process per m with the
# display's frames off (UNC_NO_DISPLAY: no input of the detector or the decoder, and the objective reads neither a
# dot nor a lock; checked on B1: identical detections and committed lines). Then the choice of m, then the test
# replays WITH the display, one process per recording.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
heavy() { pgrep -f "app_replay --inner|unconstrained choose_m --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 6 ]; do sleep 15; done; }
(cd runs/dc2_results/rule && shasum -a 256 -c APP_PREREG.md.sha256 APP_PREREG_ADDENDUM_2.md.sha256) || { echo "UNC FAILED: a rule file changed"; exit 1; }
for rot in A2 A1; do for m in 1 2 3 4; do
  slot
  echo "[$(date '+%H:%M:%S')] START m grid $rot m$m"
  (UNC_NO_DISPLAY=1 caffeinate -dimsu python3 -m pipeline.live.unconstrained choose_m --rot $rot --m $m; echo "[$(date '+%H:%M:%S')] EXIT $? m grid $rot m$m") &
  sleep 20
done; done
wait
while kill -0 83121 2>/dev/null; do sleep 15; done
echo "[$(date '+%H:%M:%S')] the m grid is complete"
python3 -m pipeline.live.unconstrained decide_m || { echo "UNC FAILED: decide_m"; exit 1; }
for sess in B2 03; do
  for stem in $(ls data/room_$([ $sess = B2 ] && echo B/session_B2 || echo A/session_03)/participant_*walk.gt.json | xargs -n1 basename | sed 's/.gt.json//' | grep -v "_C_walk"); do
    for model in final zeroshot; do
      [ $model = zeroshot ] && [ $sess = 03 ] && continue
      slot
      echo "[$(date '+%H:%M:%S')] START test $model $sess/$stem"
      (caffeinate -dimsu python3 -m pipeline.live replay --recording $sess/$stem --presses none --model $model --clock causal; echo "[$(date '+%H:%M:%S')] EXIT $? test $model $sess/$stem") &
      sleep 20
    done
  done
done
wait
echo "UNC DONE $(date '+%F %T')"
