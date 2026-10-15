#!/bin/zsh
# Item A2 (Uzayr, 29 Sep): the trace-derived hash lists for fin_B2 and fin_A3 (each a full traced rebuild, compared
# with the test decode). Waits for the V2 development chain: one CPU job at a time.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
while pgrep -f "v2_chain.py|pd_v2 " > /dev/null; do sleep 60; done
export OMP_NUM_THREADS=1 PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=relgateU+abstain+a2w0.25
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "FIN TRACE CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }
step() { echo "[$(date '+%H:%M:%S')] START $*"; caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] FIN TRACE CHAIN FAILED at $*"; exit 1; }; echo "[$(date '+%H:%M:%S')] DONE $*"; }
step python3 -m pipeline.constrained.pd_repro_trace hashes --cell fin_B2 --variant $V
step python3 -m pipeline.constrained.pd_repro_trace hashes --cell fin_A3 --variant $V
echo "FIN TRACE CHAIN DONE $(date '+%F %T')"
