#!/bin/zsh
# D4 chain (tracking attack): starts when the midpoint model has freed the GPU. Screens the shared
# encoder (learned fusion; attention over links) with the single 0.5 s g25 head and D2's training
# options, decodes both and their base (d2p_ar, per-link networks) under D3's configuration, and applies
# the rule with the scorer lock. Written 2026-09-29 04:44.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
until grep -qE "MIDPOINT MODEL READY|MIDPOINT .* FAILED" runs/dc2_results/logs/midpoint.log; do sleep 30; done
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
C=()
for a in fuse attn; do for r in $RT; do C+=(d4_${a}_$r); done; done
echo "D4 START $(date '+%F %T'): $C"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells pqueue --cells $C
echo "D4 QUEUE EXIT $? at $(date '+%F %T')"
V=relgateU
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell d2p_ar_$r --variants $V &
  pids+=($!)
done
for p in $pids; do wait $p; done
pids=()
for a in fuse attn; do for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell d4_${a}_$r --variants $V &
  pids+=($!)
done; for p in $pids; do wait $p; done; pids=(); done
for a in fuse attn; do
  for lk in scorer display; do
    echo "== D4 $a ($lk)"
    python3 -m pipeline.constrained.pd_rule compare --name D4_${a} --base d2p_ar@$V --arm d4_${a}@$V --lock $lk | grep -E "^\| [BA]|Objective|Paired|Decision|guard"
  done
done
echo "D4 RULES DONE $(date '+%F %T')"
