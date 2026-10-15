"""The re-selection's rule steps on relgateU+abstain (DEVLOG VERIFY, F2 DONE entry), after reselect_abstain.sh.

The original D3R, D4 and D5 steps, judged the same way (pd_rule, display lock as the original D3R and D5; D4 under
both locks as the original), with every source on the CLEAN readers and the base moved from relgateU to
relgateU+abstain. Writes runs/dc2_results/rule/RS_*.json and .md (pd_rule's own writer) and RS_SUMMARY.md.

    python3 runs/dc2_results/reselect_rules.py [<base variant> <name prefix>]      # default relgateU+abstain RS
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from pipeline.constrained import pd_rule as R   # noqa: E402

B = sys.argv[1] if len(sys.argv) > 1 else "relgateU+abstain"
PX = sys.argv[2] if len(sys.argv) > 2 else "RS"
OPTS = [x for x in ("w0.25", "w0.5", "lw0.25", "onhead", "pace", "off-9", "off-6", "a2w0.25", "sd3.5", "margin2.5")
        if x not in B.split("+")]
STEPS = []
for x in OPTS:
    STEPS.append((f"{PX}_D3R_{x}_over_base", f"d2pc_ar@CR.{B}", f"d2pc_ar@CR.{B}+{x}", "display", None))
STEPS.append((f"{PX}_D3R_scorer_over_display", f"d2pc_ar@CR.{B}", f"d2pc_ar@CR.{B}", "display", "scorer"))
for lk in ("display", "scorer"):
    STEPS.append((f"{PX}_D4_fuse", f"d2p_ar@CR.{B}", f"d4_fuse@CR.{B}", lk, None))
    STEPS.append((f"{PX}_D4_attn", f"d2p_ar@CR.{B}", f"d4_attn@CR.{B}", lk, None))
    STEPS.append((f"{PX}_D4_confirm_fuse", f"d2pc_ar@CR.{B}", f"d4c_fuse@CR.{B}", lk, None))
for x in ("g100n", "interp"):
    STEPS.append((f"{PX}_D5_{x}_on_d4c", f"d4c_fuse@CR.{B}", f"d4c_fuse@CR.{B}+{x}", "display", None))

rows = []
for name, base, arm, lock, al in STEPS:
    args = ["compare", "--name", name, "--base", base, "--arm", arm, "--lock", lock] + (["--arm-lock", al] if al else [])
    R.main(args)
    with open(os.path.join(R.RULE_DIR, f"{name}_{lock}.json".replace("@", "-")), encoding="utf-8") as f:
        o = json.load(f)
    rows.append(o)
L = [f"# Re-selection on {B}, clean readers (rotations only)", "",
     "| step | lock | base objective | arm objective | paired gain [95%] | guard | decision |", "|---|---|---|---|---|---|---|"]
for o in rows:
    p = o.get("paired") or {}
    ci = p.get("ci95") or [float("nan")] * 2
    L.append(f"| {o['name']} | {o['lock']} | {o['base_summary']['objective']:.2f} | {o['arm_summary']['objective']:.2f} | "
             f"{p.get('gain', float('nan')):+.2f} [{ci[0]:.2f}, {ci[1]:.2f}] | {(o.get('guard') or {}).get('holds')} | "
             f"{o.get('decision')} |")
with open(os.path.join(R.RULE_DIR, f"{PX}_SUMMARY.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("\n".join(L))
