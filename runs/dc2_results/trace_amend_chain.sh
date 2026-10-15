#!/bin/zsh
# Item A2/A3 amended (30 Sep): the trace lists with the copy step's sources, then zsf_B2 rebuilt against the amended list.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=relgateU+abstain+a2w0.25
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "AMEND CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] AMEND CHAIN FAILED at $*"; exit 1; }; echo "[$(date '+%H:%M:%S')] DONE $*"; }
for c in zsf_B2 fin_B2 fin_A3; do step python3 -m pipeline.constrained.pd_repro_trace hashes --cell $c --variant $V --reuse --amend; done
step python3 -m pipeline.constrained.pd_repro_trace run --cell zsf_B2 --variant $V
echo "AMEND CHAIN DONE $(date '+%F %T')"
