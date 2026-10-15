#!/bin/zsh
setopt NO_BG_NICE
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
S=runs/ship_0p5_2026-10-08
while kill -0 69799 2>/dev/null; do sleep 30; done
if grep -q "all heads trained" $S/logs/train.log; then
  echo "[$(date '+%H:%M:%S')] training complete; starting post_train" >> $S/logs/post.log
  OMP_NUM_THREADS=1 PYTHONPATH=. /opt/anaconda3/bin/python3 $S/post_train.py >> $S/logs/post.stdout 2>&1
  echo "[$(date '+%H:%M:%S')] post_train exit $?" >> $S/logs/post.log
else
  echo "[$(date '+%H:%M:%S')] training did not complete; post_train NOT started" >> $S/logs/post.log
fi
