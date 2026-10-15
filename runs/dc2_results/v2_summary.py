"""The V2 development round's record (rotations only), written after runs/dc2_results/v2_chain.py.

    python3 runs/dc2_results/v2_summary.py      # -> runs/dc2_results/v2/V2_DEVELOPMENT.md and .json

Reads rule/V2_option3.json and V2_option4.json (pd_v2 select), the decodes they name, and the base (V2-B, the
DT1K decodes). Adds, per arm, the pooled rotation figures, the edge lines, and the corner-pair lock confusions
(the pairs option 4 targets). Chooses nothing: the choices are in the two rule files.
"""
import collections
import json
import os
import sys

REPO = os.getcwd()
sys.path.insert(0, REPO)
J = os.path.join
RULE = J(REPO, "runs", "dc2_results", "rule")
OUT = J(REPO, "runs", "dc2_results", "v2")
CORNER = {"SW": ("C_fwd", "E_col1", "E_row1"), "SE": ("D_rev", "E_col5"), "NW": ("D_fwd", "E_row5")}
GROUP = {l: g for g, ls in CORNER.items() for l in ls}


def corner_confusions(R) -> dict:
    """Lock errors between two lines of one start corner, pooled over the rotations, by pair."""
    c = collections.Counter()
    for nm, rr in R.items():
        for r in rr["lock"]:
            if r["line"] != r["true"] and GROUP.get(r["true"]) and GROUP.get(r["true"]) == GROUP.get(r["line"]):
                c[f"{r['true']}->{r['line']}"] += 1
    return {"total": sum(c.values()), "by_pair": dict(sorted(c.items()))}


def main():
    from pipeline.constrained import pd_rule as PR
    from pipeline.constrained.pd_v2 import BASE_ARM
    o3 = json.load(open(J(RULE, "V2_option3.json"), encoding="utf-8"))
    o4 = json.load(open(J(RULE, "V2_option4.json"), encoding="utf-8"))
    arms = {"V2-B (base)": BASE_ARM, "option 3 candidate": o3["candidate_arm"],
            "option 4 base": o4["base"], "option 4 candidate": o4["candidate_arm"]}
    rows, out = [], {"option3": o3, "option4": o4, "arms": {}}
    for label, arm in arms.items():
        R = PR.rot_rows(arm, "display")
        S = PR.summarise(R)
        cc = corner_confusions(R)
        out["arms"][label] = {"arm": arm, "summary": S, "corner_lock_confusions": cc}
        per = S["rotations"]
        rows.append(f"| {label} | `{arm.split('@')[1]}` | {S['objective']:.2f} | "
                    + " | ".join(f"{per[nm]['committed']:.2f} / {per[nm]['lock']:.2f}" for nm in ("B1", "A2", "A1"))
                    + f" | {S['pooled_pct']['committed']:.2f} / {S['pooled_pct']['lock']:.2f} | "
                    + "/".join("-" if v is None else f"{v:.0f}" for v in S["pooled_edges"]["lock"].values())
                    + f" | {cc['total']} |")
    L = ["# V2 development round: rotations only (rule/V2_PREREG.md, 9bb52b68...)", "",
         "Committed / display lock, percent. The objective is the weighted mean of committed + lock (B1 x2).", "",
         "| arm | decode | objective | B1 | A2 | A1 | pooled | edge lines, lock (col1/col5/row1/row5) | corner-pair lock errors |",
         "|---|---|---|---|---|---|---|---|---|"] + rows + ["",
         "## Option 3: the grid (12 variants; the candidate is the highest objective)", "",
         "| w_A2, theta, w_ab | objective |", "|---|---|"]
    L += [f"| {g['setting']} | {g['objective']:.2f} |" for g in o3["grid"]]
    p3 = o3.get("paired") or {}
    L += ["", f"Candidate {o3['candidate']}; paired gain over V2-B {p3.get('gain', float('nan')):+.2f} "
          f"[{(p3.get('ci95') or [float('nan')] * 2)[0]:.2f}, {(p3.get('ci95') or [float('nan')] * 2)[1]:.2f}]; "
          f"edge guard holds: {(o3.get('guard') or {}).get('holds')}; **{o3['decision']}**", "",
          "## Option 4: the grid (3 variants, on whatever option 3 left)", "", "| w4 | objective |", "|---|---|"]
    L += [f"| {g['setting']} | {g['objective']:.2f} |" for g in o4["grid"]]
    p4 = o4.get("paired") or {}
    L += ["", f"Candidate w4 = {o4['candidate']}; paired gain over its base {p4.get('gain', float('nan')):+.2f} "
          f"[{(p4.get('ci95') or [float('nan')] * 2)[0]:.2f}, {(p4.get('ci95') or [float('nan')] * 2)[1]:.2f}]; "
          f"edge guard holds: {(o4.get('guard') or {}).get('holds')}; **{o4['decision']}**", ""]
    for label in ("option 4 base", "option 4 candidate"):
        L.append(f"- corner-pair lock errors, {label}: {out['arms'][label]['corner_lock_confusions']}")
    os.makedirs(OUT, exist_ok=True)
    with open(J(OUT, "V2_DEVELOPMENT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(J(OUT, "V2_DEVELOPMENT.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("\n".join(L))


if __name__ == "__main__":
    main()
