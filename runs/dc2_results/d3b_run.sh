#!/bin/zsh
# D3 layer 2 (tracking attack): the Room-A-referenced relative gate, lock-only fusion and the
# combinations of the singly adopted options. usage: d3b_run.sh <prefix>. Written 2026-09-29 03:46.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
P=$1
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
V=(ref relgateA lw0.25 lw0.5 relgate+abstain relgateA+abstain relgateA+abstain+lw0.25 relgate+abstain+lw0.25)
echo "D3B START $(date '+%F %T') on $P: $V"
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${P}_$r --variants $V &
  pids+=($!)
done
fail=0
for p in $pids; do wait $p || fail=1; done
echo "D3B decodes done $(date '+%F %T') fail=$fail"
for v in ${V[2,-1]}; do
  for lk in display scorer; do
    echo "== $v ($lk)"
    python3 -m pipeline.constrained.pd_rule compare --name D3b_${v}_vs_ref --base ${P}@ref --arm ${P}@$v --lock $lk | grep -E "Objective|Paired|Decision|guard"
  done
done
echo "D3B RULES DONE $(date '+%F %T')"
