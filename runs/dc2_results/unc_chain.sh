#!/bin/zsh
# The unconstrained mode (APP_PREREG section 6 + addendum 2, hashed ebb9feed...): the m grid on the three
# rotations, then the choice of m, then the test replays. Each step starts only while tracking runs fewer than
# 4 heavy processes (Identification's allowance until 15:00).
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
heavy() { pgrep -f "app_replay --inner|final_model gate --inner|pd_clean decode --inner|pd_disp_prov (cap_inner|app_cap_inner)|unconstrained choose_m --inner|pipeline.live.app_teaching --inner" | wc -l | tr -d ' '; }
slot() { while [ "$(heavy)" -ge 4 ]; do sleep 20; done; }
(cd runs/dc2_results/rule && shasum -a 256 -c APP_PREREG.md.sha256 APP_PREREG_ADDENDUM_2.md.sha256) || { echo "UNC FAILED: a rule file changed"; exit 1; }
pids=()
for rot in B1 A2 A1; do
  slot
  echo "[$(date '+%H:%M:%S')] START m grid $rot"
  (caffeinate -dimsu python3 -m pipeline.live.unconstrained choose_m --rot $rot; echo "[$(date '+%H:%M:%S')] EXIT $? m grid $rot") &
  pids+=($!)
  sleep 60
done
wait $pids
echo "[$(date '+%H:%M:%S')] START decide_m"
python3 -m pipeline.live.unconstrained decide_m || { echo "UNC FAILED: decide_m"; exit 1; }
for job in "--session B2 --presses none --model final" "--session 03 --presses none --model final" "--session B2 --presses none --model zeroshot"; do
  slot
  echo "[$(date '+%H:%M:%S')] START test $job"
  (caffeinate -dimsu python3 -m pipeline.live replay ${=job} --clock causal; echo "[$(date '+%H:%M:%S')] EXIT $? test $job") &
  sleep 60
done
wait
echo "UNC DONE $(date '+%F %T')"
