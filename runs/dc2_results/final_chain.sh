#!/bin/zsh
# FINAL chain (tracking attack). Waits for D4's confirmation; the final model is the shared encoder with
# learned fusion if D4 is confirmed (cells fin_*), else the midpoint model (mid_*, already trained and
# tested with this configuration). Trains the ZERO-SHOT model (A1+A2 only, readers from A1+A2 only),
# runs the one sanctioned FINAL decode per test cell, times the heads with the GPU idle, and builds the
# tables. Written 2026-09-29 07:52.
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
until grep -q "D4 CONFIRM RULES DONE" runs/dc2_results/logs/d4c.log; do sleep 30; done
D4=$(python3 -c "import json;print(int(bool(json.load(open('runs/dc2_results/rule/D4_confirm_fuse_display.json')).get('ADOPT'))))")
V=relgateU
for v in g100n interp; do
  a=$(python3 -c "import json;print(int(bool(json.load(open('runs/dc2_results/rule/D5_${v}_on_d4c_display.json')).get('ADOPT'))))")
  [[ $D4 == 1 && $a == 1 ]] && V=$V+$v
done
echo "FINAL: D4 confirmed=$D4, decode variant $V at $(date '+%F %T')"
if [[ $D4 == 1 ]]; then F=fin; Z=zsf; else F=mid; Z=zs; fi
echo "FINAL MODEL CELLS ${F}_A3 ${F}_B2; ZERO-SHOT ${Z}_B2"
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell zsp_B2 --phase prep || { echo "FINAL zsp prep FAILED"; exit 1; }
if [[ $F == fin ]]; then
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell fin_A3 --phase prep || { echo "FINAL fin_A3 prep FAILED"; exit 1; }
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell fin_B2 --phase prep || { echo "FINAL fin_B2 prep FAILED"; exit 1; }
fi
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_cells run --cell ${Z}_B2 --phase prep || { echo "FINAL zero-shot prep FAILED"; exit 1; }
echo "FINAL MODELS READY $(date '+%F %T')"
# latency with the GPU idle: the per-link and the final heads on the same development windows
LC=(d2pc_ar_0102_to_B1); [[ $D4 == 1 ]] && LC+=(d4c_fuse_0102_to_B1)
OMP_NUM_THREADS=1 python3 -m pipeline.constrained.pd_latency --cells $LC --n 200
echo "FINAL DECODE START $(date '+%F %T')"
pids=()
if [[ $F == fin || $V != relgateU ]]; then
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${F}_A3 --variants $V & pids+=($!)
  OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${F}_B2 --variants $V $V+cfgBn & pids+=($!)
fi
OMP_NUM_THREADS=1 caffeinate -dimsu python3 -m pipeline.constrained.pd_decode --cell ${Z}_B2 --variants $V $V+cfgBn & pids+=($!)
for p in $pids; do wait $p; done
python3 -m pipeline.constrained.pd_final --name FINAL --a3 ${F}_A3@$V --b2 ${F}_B2@$V --b2-config-b ${F}_B2@$V+cfgBn
python3 - $Z $V <<'PY'
import json, sys
from pipeline.constrained.pd_final import load, fmt, edges
from pipeline.constrained.pd_report import acc
Z, V = sys.argv[1], sys.argv[2]
L = ["## ZERO-SHOT (trained on A1+A2 only; readers from A1+A2 only; tested once on B2)", "",
     "| test | committed | display lock | scorer lock | edges committed | edges display lock | resolution: correct-lock walks, along the line (median / p90, m) |",
     "|---|---|---|---|---|---|---|"]
out = {}
for label, src in (("B2 (A)", f"{Z}_B2@{V}"), ("B2 (B)", f"{Z}_B2@{V}+cfgBn")):
    m = load(src)
    a = {k: acc(m[k]) for k in ("committed", "lock_display", "lock_scorer")}
    r = m.get("resolution") or {}
    f = lambda q: "-" if not q else f"{q['median']:.2f} / {q['p90']:.2f}"
    L.append(f"| {label} | {fmt(a['committed'])} | {fmt(a['lock_display'])} | {fmt(a['lock_scorer'])} | {edges(a['committed'])} | "
             f"{edges(a['lock_display'])} | {f(r.get('correct_lock_walks'))}; {f(r.get('along_line_on_true_line'))} |")
    out[label] = {"src": src, "acc": a, "resolution": r}
L += ["", "Beside it: the frozen DC2 reference on B2 (trained on A1+A2+A3) 50.00 / 12.50.", ""]
md = "\n".join(L)
open("runs/dc2_results/final/ZERO_SHOT.md", "w").write(md)
json.dump(out, open("runs/dc2_results/final/ZERO_SHOT.json", "w"), indent=1, default=str)
print(md)
PY
echo "FINAL DONE $(date '+%F %T')"
