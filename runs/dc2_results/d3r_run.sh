#!/bin/zsh
# D3 on D2's CONFIRMED networks (d2pc_ar): every option that was rejected on d1sp, layered on relgateU,
# judged against relgateU with the display lock (the lock kept on these networks). Written 2026-09-29 06:14.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
P=d2pc_ar
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
V=(relgateU+w0.25 relgateU+w0.5 relgateU+lw0.25 relgateU+onhead relgateU+pace relgateU+off-9 relgateU+off-6 relgateU+a2w0.25 relgateU+sd3.5 relgateU+margin2.5)
echo "D3R START $(date '+%F %T'): $V"
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${P}_$r --variants $V &
  pids+=($!)
done
for p in $pids; do wait $p; done
echo "D3R decodes done $(date '+%F %T')"
for v in $V; do
  echo "== $v over relgateU (display)"
  python3 -m pipeline.constrained.pd_rule compare --name D3R_${v}_over_relgateU --base ${P}@relgateU --arm ${P}@$v | grep -E "Objective|Paired|Decision|guard"
done
echo "D3R RULES DONE $(date '+%F %T')"
