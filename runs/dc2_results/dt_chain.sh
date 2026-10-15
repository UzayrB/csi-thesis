#!/bin/zsh
# Item 2 (Uzayr, 29 Sep): the time-step disclosure on the rotations. Waits for the zero-shot chain (one CPU job at a time).
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
while pgrep -f "zsf_trace_chain.sh" > /dev/null; do sleep 30; done
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256 && shasum -a 256 -c V2_PREREG.md.sha256) || { echo "DT CHAIN FAILED: a frozen file changed"; exit 1; }
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] DT CHAIN FAILED at $*"; exit 1; }; echo "[$(date '+%H:%M:%S')] DONE $*"; }
for arm in 0 1 1K; do
  for cell in d4c_fuse_0102_to_B1 d4c_fuse_01B1_to_02 d4c_fuse_02B1_to_01; do
    step python3 -m pipeline.constrained.pd_dt decode --cell $cell --arm $arm
  done
done
step python3 -m pipeline.constrained.pd_dt report
echo "DT CHAIN DONE $(date '+%F %T')"
