#!/bin/zsh
# D3 (tracking attack): every decode option on D2's winner full-pool rotation cells, then the rule.
# usage: d3_run.sh <rotation prefix of D2's winner, e.g. d1sp>. Written 2026-09-29 00:05.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
P=$1
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
V=(ref cnull relgate w0.25 w0.5 w1.0 onhead abstain pace)
echo "D3 START $(date '+%F %T') on $P: $V"
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${P}_$r --variants $V &
  pids+=($!)
done
fail=0
for p in $pids; do wait $p || fail=1; done
echo "D3 decodes done $(date '+%F %T') fail=$fail"
for v in ${V[3,-1]}; do
  python3 -m pipeline.constrained.pd_rule compare --name D3_$v --base ${P}@ref --arm ${P}@$v | grep -E "Objective|Paired|Decision|guard"
done
python3 -m pipeline.constrained.pd_rule compare --name D3_cnull --base ${P}@ref --arm ${P}@cnull | grep -E "Objective|Decision"
python3 -m pipeline.constrained.pd_rule compare --name D3_scorerlock --base ${P}@ref --arm ${P}@ref --arm-lock scorer | grep -E "Objective|Paired|Decision|guard"
echo "D3 RULES DONE $(date '+%F %T')"
