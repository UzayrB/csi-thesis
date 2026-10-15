#!/bin/zsh
# APP_PREREG section 4, split over two cores (30 Sep, Identification's extra cores): G2rest.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
V=relgateU+abstain+a2w0.25; REF=FC.$V
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256 APP_PREREG.md.sha256 APP_PREREG_ADDENDUM_1.md.sha256) || { echo "GATES FAILED: a frozen file changed"; exit 1; }
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@"; rc=$?; echo "[$(date '+%H:%M:%S')] EXIT $rc $*"; [[ $rc == 0 ]] || { echo "GATE DIFFERS: STOP ($*)"; exit 2; }; }
while kill -0 $(pgrep -f "final_model gate --inner --cell fin_B2 .*--mode semi" | head -1) 2>/dev/null; do sleep 15; done
for cell in zsf_B2 fin_A3; do
  step python3 -m pipeline.live.final_model gate --cell $cell --ref $REF --variant $V --mode semi
done
echo "GATES G2rest DONE $(date '+%F %T')"
