#!/bin/zsh
# MIDPOINT chain (tracking attack). Waits for D2's full-pool confirmation; registers the midpoint model
# (A1+A2+B1, the D2 winner's training options, full pool); re-checks D3's decode choice on the confirmed
# networks while the midpoint model trains; then runs the ONE sanctioned midpoint decode on A3 and B2.
# Written 2026-09-29 04:43.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
until grep -q "D2 CONFIRM RULES DONE" runs/dc2_results/logs/queue_d2confirm.log; do sleep 30; done
A=$(python3 -c "import json;print(int(bool(json.load(open('runs/dc2_results/rule/D2_confirm_ar_display.json')).get('ADOPT'))))")
echo "D2 confirmation ADOPT=$A at $(date '+%F %T')"
python3 - $A <<'PY'
import json, sys
p = "runs/dc2_results/stage_cells.json"
d = json.load(open(p))
if sys.argv[1] == "1":
    d["mid"] = {"rotations": False, "opts": {"aug": True, "rrel": True}, "heads": "all", "pos_from": "ph_A3"}
else:
    d["mid"] = {"rotations": False, "opts": {}, "heads": "all", "shared_from": "ph_A3"}
json.dump(d, open(p, "w"), indent=1)
print("registered mid:", d["mid"])
PY
P2=d1sp; [[ $A == 1 ]] && P2=d2pc_ar
RT=(0102_to_B1 01B1_to_02 02B1_to_01)
pids=()
if [[ $P2 == d2pc_ar ]]; then
  for r in $RT; do
    OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${P2}_$r --variants ref relgateU relgateU+abstain &
    pids+=($!)
  done
fi
echo "MIDPOINT MODEL START $(date '+%F %T')"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell mid_A3 --phase prep || { echo "MIDPOINT mid_A3 prep FAILED"; exit 1; }
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell mid_B2 --phase prep || { echo "MIDPOINT mid_B2 prep FAILED"; exit 1; }
echo "MIDPOINT MODEL READY $(date '+%F %T')"
for p in $pids; do wait $p; done
V=relgateU
if [[ $P2 == d2pc_ar ]]; then
  python3 -m pipeline.constrained.pd_rule compare --name D3R_relgateU_over_ref_on_d2pc --base ${P2}@ref --arm ${P2}@relgateU --lock scorer | grep -E "Objective|Paired|Decision|guard"
  python3 -m pipeline.constrained.pd_rule compare --name D3R_abstain_over_relgateU_on_d2pc --base ${P2}@relgateU --arm ${P2}@relgateU+abstain --lock scorer | grep -E "Objective|Paired|Decision|guard"
  R1=$(python3 -c "import json;print(int(bool(json.load(open('runs/dc2_results/rule/D3R_relgateU_over_ref_on_d2pc_scorer.json')).get('ADOPT'))))")
  R2=$(python3 -c "import json;print(int(bool(json.load(open('runs/dc2_results/rule/D3R_abstain_over_relgateU_on_d2pc_scorer.json')).get('ADOPT'))))")
  [[ $R1 == 0 ]] && echo "WARNING: relgateU does not pass on the confirmed networks; the midpoint uses it as D3 decided on d1sp"
  [[ $R2 == 1 ]] && V=relgateU+abstain
fi
echo "MIDPOINT DECODE START $(date '+%F %T'): variant $V (scorer lock read beside the display lock)"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell mid_A3 --variants $V &
a3=$!
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell mid_B2 --variants $V $V+cfgBn
wait $a3
python3 -m pipeline.constrained.pd_final --name MIDPOINT --a3 mid_A3@$V --b2 mid_B2@$V --b2-config-b mid_B2@$V+cfgBn
echo "MIDPOINT DONE $(date '+%F %T')"
