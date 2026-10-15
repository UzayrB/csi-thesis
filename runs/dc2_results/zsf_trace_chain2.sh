#!/bin/zsh
# Items A2 and A3, resumed: the list from the completed traced rebuild (22:46 to 22:58, EXACT), then the rebuild from it.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
while pgrep -f "dt_chain.sh" > /dev/null; do sleep 30; done
export OMP_NUM_THREADS=1 PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=relgateU+abstain+a2w0.25
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "ZSF CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] ZSF CHAIN FAILED at $*"; exit 1; }; echo "[$(date '+%H:%M:%S')] DONE $*"; }
step python3 -m pipeline.constrained.pd_repro_trace hashes --cell zsf_B2 --variant $V --reuse
step python3 -m pipeline.constrained.pd_repro_trace run --cell zsf_B2 --variant $V
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "ZSF CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }
echo "ZSF CHAIN DONE $(date '+%F %T')"
