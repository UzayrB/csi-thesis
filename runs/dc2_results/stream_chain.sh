#!/bin/zsh
# Item 5d: the streamed B2 run (the "rig run"), on a quiet machine: the six B2 recordings streamed one after
# another at their recorded pace, the screen recorded, then each compared with the replay of the same recording
# made with the same app (the chosen display): $1 = that replay's folder.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
REPLAY=$1
[ -d "$REPLAY" ] || { echo "STREAM FAILED: no replay folder $REPLAY"; exit 1; }
# where the run writes: runs/live/stream for K0 (the 30 Sep record), runs/live/stream_disp-<K> for any other display
OUTD=$(python3 -c "from pipeline.live.stream_source import out_root; print(out_root())")
echo "display folder $OUTD, compared with $REPLAY"
for stem in $(ls data/room_B/session_B2/participant_*walk.gt.json | xargs -n1 basename | sed 's/.gt.json//' | grep -v "_C_walk"); do
  echo "[$(date '+%H:%M:%S')] START stream B2/$stem"
  caffeinate -dimsu python3 -m pipeline.live rig --stream B2/$stem --screen $OUTD
  echo "[$(date '+%H:%M:%S')] EXIT $? stream B2/$stem"
  python3 -c "
import json
from pipeline.live.stream_source import compare
r = compare('B2', '$stem', '$REPLAY')
json.dump(dict(r, replay='$REPLAY'), open('$OUTD/B2__$stem/compare.json', 'w'), indent=1)
print(json.dumps(r))"
  # the stream's own capture (the packets and presses exactly as the app got them) through the harness
  python3 -m pipeline.live rig --stream B2/$stem --rereplay
done
echo "STREAM DONE $(date '+%F %T')"
