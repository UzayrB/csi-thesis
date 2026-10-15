#!/bin/zsh
# Part E and the headline replays (APP_PREREG section 4: only after G1 and G2 pass), then the fully constrained
# mode (the user's order: E, then the fully constrained part of C). Three lanes while tracking has 4 cores.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1
L=runs/dc2_results/logs
until grep -q "GATES G1 DONE" $L/app_gates_G1.log && grep -q "GATES G2rest DONE" $L/app_gates.log; do
  if grep -q "GATE DIFFERS\|GATES FAILED" $L/app_gates_G1.log $L/app_gates.log; then echo "[$(date '+%H:%M:%S')] A GATE DIFFERS: E NOT RUN"; exit 2; fi
  sleep 30
done
python3 - <<'PY' || { echo "[$(date '+%H:%M:%S')] GATE FILES NOT ALL EXACT: E NOT RUN"; exit 2; }
import json, os, sys, datetime
ok = True
for cell in ("fin_B2", "zsf_B2", "fin_A3"):
    for tag, mode in (("", "legacy"), ("_semi", "semi")):
        p = f"runs/live/final/gate_{cell}{tag}.json"
        g = json.load(open(p))
        t = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        good = g.get("EXACT") and g.get("mode") == mode and g.get("n") == 120 and t.strftime("%H:%M") >= "09:56"
        print(p, g.get("mode"), g.get("committed_equal"), g.get("lock_equal"), g.get("EXACT"), t.strftime("%H:%M:%S"), "OK" if good else "BAD")
        ok = ok and bool(good)
sys.exit(0 if ok else 1)
PY
echo "[$(date '+%H:%M:%S')] gates EXACT: E starts"
lane() { for a in "$@"; do eval "echo \"[\$(date '+%H:%M:%S')] START $a\"; caffeinate -dimsu $a; echo \"[\$(date '+%H:%M:%S')] EXIT \$? $a\""; done; }
R="python3 -m pipeline.live replay"
lane "$R --session 03 --presses start --model final --clock causal --realtime --screen runs/live/renders" > $L/app_E_lane1.log 2>&1 &
lane "$R --session B2 --presses start --model final --clock causal --realtime --screen runs/live/renders" > $L/app_E_lane2.log 2>&1 &
lane "$R --session B2 --presses start --model zeroshot --clock causal" \
     "$R --session 03 --presses start_end --model final --clock causal" \
     "$R --session B2 --presses start_end --model final --clock causal" \
     "$R --session B2 --presses start_end --model zeroshot --clock causal" > $L/app_E_lane3.log 2>&1 &
wait
echo "E DONE $(date '+%F %T')"
