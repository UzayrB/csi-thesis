#!/bin/zsh
# ITEM 3's arms, chained behind item 2 so the machine is never idle and nothing overlaps.
# Order is pre-registered: base (the control) then edge100. edge50 only if edge100 survives (a)
# and (b), which is decided by x3_edgeeval, not here.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export PYTHONPATH=.
L=runs/constrained/logs
# wait for item 2 to finish before touching the CPU
while pgrep -f "pipeline.constrained.x1_edgedisp" > /dev/null; do sleep 20; done
echo "[chain] item 2 finished at $(date '+%H:%M:%S'); starting item 3 arms" >> $L/chain_item3.log
for ARM in shipped base edge100; do
  echo "[chain] $(date '+%H:%M:%S') starting arm $ARM" >> $L/chain_item3.log
  TDR_EDGE_ARM=$ARM python3 -m pipeline.constrained.x2_edgepool > $L/x2_$ARM.log 2>&1
  echo "[chain] $(date '+%H:%M:%S') arm $ARM exited $?" >> $L/chain_item3.log
done
echo "[chain] $(date '+%H:%M:%S') all three arms done" >> $L/chain_item3.log
