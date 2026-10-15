#!/bin/zsh
# The ship rule, chained behind item 3's arms. Separate script from chain_item3.sh on purpose:
# editing a script zsh is currently reading is its own class of fault.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export PYTHONPATH=.
L=runs/constrained/logs
while pgrep -f "chain_item3.sh" > /dev/null; do sleep 20; done
echo "[eval] $(date '+%H:%M:%S') arms finished; applying the ship rule" >> $L/chain_eval.log
python3 -m pipeline.constrained.x3_edgeeval > $L/x3_edgeeval.log 2>&1
echo "[eval] $(date '+%H:%M:%S') x3_edgeeval exited $?" >> $L/chain_eval.log
