#!/bin/zsh
# D4 confirmation (tracking attack): the shared encoder with the learned fusion head, all five heads,
# D2's training options, on the three rotations; decoded under D3 (relgateU) and judged against the
# per-link confirmed networks d2pc_ar@relgateU. Written 2026-09-29 07:41.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
C=(); for r in $RT; do C+=(d4c_fuse_$r); done
echo "D4 CONFIRM START $(date '+%F %T'): $C"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells pqueue --cells $C
echo "D4 CONFIRM QUEUE EXIT $? at $(date '+%F %T')"
pids=()
for r in $RT; do
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell d4c_fuse_$r --variants relgateU relgateU+g100n relgateU+interp &
  pids+=($!)
done
for p in $pids; do wait $p; done
for lk in display scorer; do
  echo "== D4 confirm fuse ($lk)"
  python3 -m pipeline.constrained.pd_rule compare --name D4_confirm_fuse --base d2pc_ar@relgateU --arm d4c_fuse@relgateU --lock $lk | grep -E "^\| [BA]|Objective|Paired|Decision|guard|committed:|lock:"
done
for v in g100n interp; do
  echo "== D5 $v on d4c_fuse (display)"
  python3 -m pipeline.constrained.pd_rule compare --name D5_${v}_on_d4c --base d4c_fuse@relgateU --arm d4c_fuse@relgateU+$v | grep -E "^\| [BA]|Objective|Paired|Decision|guard"
done
echo "D4 CONFIRM RULES DONE $(date '+%F %T')"
