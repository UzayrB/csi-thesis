#!/bin/zsh
# The traced reproduction after the restructure, with the environment of tracking's own trace chains
# (runs/dc2_results/trace_amend_chain.sh): PD_CLEAN_PREFIX=FC and the frozen A1+A2 pace prior.
# verify.sh's first repro launch omitted that environment and failed in _plan (the CR prefix); its log line
# read "EXIT 0" because $(date) reset $? before it was printed. Here the code is captured first.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PYTHONPATH=. PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=relgateU+abstain+a2w0.25; L=runs/restructure_2026-10-01/logs
(cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "REPRO FAILED: FINAL_CONFIG.md changed"; exit 1; }
for c in fin_A3 fin_B2 zsf_B2; do
  (echo "[$(date +%H:%M:%S)] START repro $c"; python3 -m pipeline.constrained.pd_repro_trace run --cell $c --variant $V; rc=$?; echo "[$(date +%H:%M:%S)] EXIT $rc repro $c") > $L/repro2_$c.log 2>&1 &
done
wait
echo "REPRO DONE $(date '+%F %T')"
