#!/bin/zsh
# Runs a python command with HEADLINE replaced by the headline training set that PLAN.md's rule chose
# (read from runs/identify/idwalks/eval_A.json, written by idw_eval --stage A). Refuses if there is none.
H=$(/opt/anaconda3/bin/python3 -c "import json;print(json.load(open('runs/identify/idwalks/eval_A.json'))['A']['rule']['headline_set'])" 2>/dev/null)
[[ -z "$H" ]] && { echo "no headline set in eval_A.json"; exit 3; }
echo "headline set (PLAN rule): $H"
exec /opt/anaconda3/bin/python3 ${@//HEADLINE/$H}
