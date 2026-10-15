#!/bin/zsh
# THE ONE TEST of the corrected final tracker, then everything that follows it (Uzayr's instructions of 29 Sep, points 3 to 7).
#   0. the frozen configuration's hash (rule/FINAL_CONFIG.md); refuse on a mismatch
#   1. provenance PRE-checks: zero-shot (fails on any component touching B1 or B2), main (fails on A3 or B2)
#   2. THE ONE TEST: fin_A3, fin_B2, zsf_B2 decoded with the frozen variant, clean readers, the A1+A2 pace (prefix FC)
#   3. provenance POST-checks on each decode's own file trace; STOP on a failure
#   4. the tables: main (pd_final), zero-shot old and new, the B1 gain paired on B2
#   5. verification (substitution, shuffled radio), then the teaching export, the renders, the live gates, the reproduction
# ONE CPU job at a time. Stops at the first failure. Usage: final_corrected_chain.sh relgateU+abstain+a2w0.25
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
export OMP_NUM_THREADS=1 PD_CLEAN_PREFIX=FC PD_PACE_MEAN=1.3034113357347858 PD_PACE_SD=0.11254567809955889
V=$1
[[ $V == relgateU+abstain+a2w0.25 ]] || { echo "FINAL CHAIN REFUSED: the frozen variant is relgateU+abstain+a2w0.25, got '$V'"; exit 2; }
step() {
  echo "[$(date '+%H:%M:%S')] START $*"
  caffeinate -dimsu "$@" || { echo "[$(date '+%H:%M:%S')] FINAL CHAIN FAILED at $*"; exit 1; }
  echo "[$(date '+%H:%M:%S')] DONE $*"
}
hashcheck() { (cd runs/dc2_results/rule && shasum -a 256 -c FINAL_CONFIG.md.sha256) || { echo "FINAL CHAIN FAILED: FINAL_CONFIG.md changed"; exit 1; }; }
hashcheck
grep -q "variant \`relgateU+abstain+a2w0.25\`" runs/dc2_results/rule/FINAL_CONFIG.md || { echo "FINAL CHAIN FAILED: the variant is not the frozen one"; exit 1; }
echo "FINAL TEST START $(date '+%F %T') variant $V pace $PD_PACE_MEAN / $PD_PACE_SD prefix $PD_CLEAN_PREFIX"
# 1. pre-checks (records, the reader map, the zero-shot's own-map trace of this morning: the same network files)
step python3 -m pipeline.constrained.pd_provenance --cell zsf_B2 --variant $V --allowed 01 02 03 --trace runs/dc2_results/verify/own/zsf_B2/clean.json
cp runs/dc2_results/verify/provenance_zsf_B2.md runs/dc2_results/verify/provenance_zsf_B2_pre.md
step python3 -m pipeline.constrained.pd_provenance --cell fin_A3 --variant $V --allowed 01 02 B1
cp runs/dc2_results/verify/provenance_fin_A3.md runs/dc2_results/verify/provenance_fin_A3_pre.md
step python3 -m pipeline.constrained.pd_provenance --cell fin_B2 --variant $V --allowed 01 02 B1
cp runs/dc2_results/verify/provenance_fin_B2.md runs/dc2_results/verify/provenance_fin_B2_pre.md
echo "PROVENANCE PRE-CHECKS PASS $(date '+%F %T')"
# 2. THE ONE TEST
step python3 -m pipeline.constrained.pd_clean decode --cell zsf_B2 --variants $V
step python3 -m pipeline.constrained.pd_clean decode --cell fin_A3 --variants $V
step python3 -m pipeline.constrained.pd_clean decode --cell fin_B2 --variants $V
# 3. post-checks on each decode's own file trace
step python3 -m pipeline.constrained.pd_provenance --cell zsf_B2 --variant $V --allowed 01 02 03 --trace runs/dc2_results/cells/zsf_B2/d3/FC.$V/clean.json
step python3 -m pipeline.constrained.pd_provenance --cell fin_A3 --variant $V --allowed 01 02 B1 --trace runs/dc2_results/cells/fin_A3/d3/FC.$V/clean.json
step python3 -m pipeline.constrained.pd_provenance --cell fin_B2 --variant $V --allowed 01 02 B1 --trace runs/dc2_results/cells/fin_B2/d3/FC.$V/clean.json
echo "PROVENANCE POST-CHECKS PASS $(date '+%F %T')"
# 4. the tables
step python3 -m pipeline.constrained.pd_final --name FINAL_CORRECTED --a3 fin_A3@FC.$V --b2 fin_B2@FC.$V
python3 - "$V" <<'PY' || { echo "FINAL CHAIN FAILED at the zero-shot and B1-gain tables"; exit 1; }
import json, sys
sys.path.insert(0, ".")
from pipeline.constrained.pd_final import load, fmt, edges
from pipeline.constrained.pd_report import acc, paired
v = sys.argv[1]
f = lambda q: "-" if not q else f"{q['median']:.2f} / {q['p90']:.2f}"
L = ["## ZERO-SHOT B2 (trained and fitted on A1+A2 only; tested once on B2)", "",
     "| decode | committed | display lock | scorer lock | edges committed | edges display lock | dot error, correct-lock walks (median / p90, m) |",
     "|---|---|---|---|---|---|---|"]
out = {}
for label, src in ((f"CORRECTED: {v}, A1+A2 pace", f"zsf_B2@FC.{v}"), ("as first reported, 29 Sep 09:55: relgateU, shipped pace", "zsf_B2@relgateU")):
    m = load(src)
    a = {k: acc(m[k]) for k in ("committed", "lock_display", "lock_scorer")}
    r = m.get("resolution") or {}
    L.append(f"| {label} | {fmt(a['committed'])} | {fmt(a['lock_display'])} | {fmt(a['lock_scorer'])} | {edges(a['committed'])} | "
             f"{edges(a['lock_display'])} | {f(r.get('correct_lock_walks'))} |")
    out[label] = {"src": src, "acc": a, "resolution": r}
full, zs = load(f"fin_B2@FC.{v}"), load(f"zsf_B2@FC.{v}")
gain = {k: paired(zs[k], full[k]) for k in ("committed", "lock_display")}
L += ["", "## THE B1 GAIN on B2 under the same decoder (full A1+A2+B1 minus zero-shot A1+A2; paired on the same 120 passes)", "",
      "| | committed | display lock |", "|---|---|---|",
      f"| full (A1+A2+B1) | {fmt(acc(full['committed']))} | {fmt(acc(full['lock_display']))} |",
      f"| zero-shot (A1+A2) | {fmt(acc(zs['committed']))} | {fmt(acc(zs['lock_display']))} |",
      f"| gain (points) | {gain['committed']['points']:+.2f} [{gain['committed']['ci95'][0]:.2f}, {gain['committed']['ci95'][1]:.2f}] | "
      f"{gain['lock_display']['points']:+.2f} [{gain['lock_display']['ci95'][0]:.2f}, {gain['lock_display']['ci95'][1]:.2f}] |", ""]
out["b1_gain"] = gain
open("runs/dc2_results/final/ZERO_SHOT_CORRECTED.md", "w").write("\n".join(L))
json.dump(out, open("runs/dc2_results/final/ZERO_SHOT_CORRECTED.json", "w"), indent=1, default=str)
print("\n".join(L))
PY
hashcheck
echo "CORRECTED FINAL DONE $(date '+%F %T')"
# 5. verification (diagnostics only; nothing feeds back into the configuration)
step python3 -m pipeline.constrained.pd_subst --cell fin_B2 --variant $V --ref FC.$V --clean
step python3 -m pipeline.constrained.pd_subst --cell fin_A3 --variant $V --ref FC.$V --clean
step python3 -m pipeline.constrained.pd_subst --cell zsf_B2 --variant $V --ref FC.$V --clean
echo "SUBSTITUTION DONE $(date '+%F %T')"
# the teaching export on the corrected run
step python3 -m pipeline.constrained.pd_clean ladder
step python3 tools/teaching_pack_corrected.py --variant $V
echo "TEACHING DONE $(date '+%F %T')"
# the renders (the display head trained on the GPU at 13:00 on A1+A2+B1)
step python3 -m pipeline.constrained.pd_render --cell fin_B2 --variant $V --ref FC.$V --stems participant_PA5_walk --no-video
step python3 -m pipeline.constrained.pd_render --cell fin_B2 --variant $V --ref FC.$V
step python3 -m pipeline.constrained.pd_render --cell fin_A3 --variant $V --ref FC.$V
echo "RENDERS DONE $(date '+%F %T')"
# the live port: replay gates
step python3 -m pipeline.live.final_model gate --cell fin_B2 --variant $V --ref FC.$V --stems participant_PA5_walk
step python3 -m pipeline.live.final_model gate --cell fin_B2 --variant $V --ref FC.$V
step python3 -m pipeline.live.final_model gate --cell fin_A3 --variant $V --ref FC.$V
echo "LIVE GATES DONE $(date '+%F %T')"
# the reproduction from the hashes, last (the slowest step)
step python3 -m pipeline.constrained.pd_repro hashes --variant $V
step python3 -m pipeline.constrained.pd_repro run --cell fin_B2 --variant $V
step python3 -m pipeline.constrained.pd_repro run --cell fin_A3 --variant $V
hashcheck
echo "FINAL CHAIN DONE $(date '+%F %T')"
