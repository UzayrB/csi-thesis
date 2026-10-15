#!/bin/zsh
# D3 layer 3 (tracking attack): the scale-up-only gate and the re-tuned constants on the adopted
# relgateA base, judged with the adopted scorer lock. usage: d3c_run.sh <prefix>. Written 2026-09-29 04:16.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
P=$1
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
V=(relgateU relgateU+abstain relgateA+off-6 relgateA+off-9 relgateA+margin1.5 relgateA+margin2.5 relgateA+a2w0.25 relgateA+a2w1.0 relgateA+sd3.5 relgateA+sd5.5)
echo "D3C START $(date '+%F %T') on $P: $V"
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${P}_$r --variants $V &
  pids+=($!)
done
fail=0
for p in $pids; do wait $p || fail=1; done
echo "D3C decodes done $(date '+%F %T') fail=$fail"
for v in $V; do
  echo "== $v over relgateA (scorer)"
  python3 -m pipeline.constrained.pd_rule compare --name D3c_${v}_over_relgateA --base ${P}@relgateA --arm ${P}@$v --lock scorer | grep -E "Objective|Paired|Decision|guard"
done
echo "D3C RULES DONE $(date '+%F %T')"
