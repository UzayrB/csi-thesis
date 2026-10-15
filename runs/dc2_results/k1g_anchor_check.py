"""Rule 2a's K1g form on the existing logs (Uzayr, 1 Oct 09:19, item 1; reports/RENDER_RULES.md 2a, the K1g form,
committed 431b180 before this ran).

    python3 runs/dc2_results/k1g_anchor_check.py

The 360 semi-constrained test walks drawn with K1g (A3 and B2 final, zero-shot B2), each checked by the form of
its display (the glide), with the held form beside them for reference; the same 360 walks drawn with K0, checked by
the held form, unchanged; and the 360 fully constrained K1g walks as an aside. Reads the replay logs only (no
label). Writes runs/dc2_results/display/K1G_ANCHOR_CHECK.json.
"""

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from pipeline.live.app_score import anchor_form, rule_checks   # noqa: E402

J = os.path.join
REPLAY = J(ROOT, "runs", "live", "replay")
CELLS = {"K1g semi": [("final", "B2", "semi_disp-K1g_causal_realtime_screen"), ("final", "03", "semi_disp-K1g_causal_realtime_screen"),
                      ("zeroshot", "B2", "semi_disp-K1g_causal")],
         "K0 semi": [("final", "B2", "semi_disp-K0_causal"), ("final", "03", "semi_disp-K0_causal"),
                     ("zeroshot", "B2", "semi_disp-K0_causal")],
         "K1g full": [("final", "B2", "full_disp-K1g_causal"), ("final", "03", "full_disp-K1g_causal"),
                      ("zeroshot", "B2", "full_disp-K1g_causal")]}


def cell(model, session, mode):
    out = {"walks": 0, "forms": set(), "fail_own_form": 0, "fail_held_form": 0, "from_entry_m": [], "off_line_max_m": 0.0,
           "failed": []}
    for lp in sorted(glob.glob(J(REPLAY, model, mode, f"{session}__*.jsonl"))):
        rows = [json.loads(ln) for ln in open(lp, encoding="utf-8")]
        form = anchor_form(lp[:-len(".jsonl")] + ".summary.json")
        own, held = rule_checks(rows, anchor=form), rule_checks(rows, anchor="hold")
        out["walks"] += len({r["pid"] for r in rows if r["kind"] == "press"})
        out["forms"].add(form)
        out["fail_own_form"] += len(own["anchor_violations"])
        out["fail_held_form"] += len(held["anchor_violations"])
        out["failed"] += [f"{os.path.basename(lp)[:-len('.jsonl')]}#{p}" for p in own["anchor_violations"]]
        if form == "glide":
            # the per-walk distances, recomputed as rule_checks measures them, for the report
            from pipeline.live.app_score import _glide_measure
            press = {r["pid"]: float(r["t"]) for r in rows if r["kind"] == "press"}
            lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
            for pid, P in press.items():
                off = sorted((r for r in rows if r["kind"] == "dot" and r["pid"] == pid and r["x"] >= P + 2.0 - 1e-4),
                             key=lambda r: r["x"])
                if off and pid in lock:
                    de, do = _glide_measure(off[0]["xy"], lock[pid])
                    out["from_entry_m"].append(de)
                    out["off_line_max_m"] = max(out["off_line_max_m"], do)
    fe = sorted(out.pop("from_entry_m"))
    out["forms"] = sorted(out["forms"])
    out["from_entry_m"] = ({"median": fe[len(fe) // 2], "max": fe[-1], "n": len(fe)} if fe else None)
    return out


def main():
    res = {}
    for group, cells in CELLS.items():
        res[group] = {f"{m} {s} {mode}": cell(m, s, mode) for m, s, mode in cells}
        tot = res[group]
        print(group, "walks", sum(v["walks"] for v in tot.values()), "fail (own form)", sum(v["fail_own_form"] for v in tot.values()),
              "fail (held form)", sum(v["fail_held_form"] for v in tot.values()))
        for k, v in tot.items():
            print("  ", k, {kk: vv for kk, vv in v.items() if kk != "failed"}, v["failed"][:5])
    res["rule"] = {"source": "reports/RENDER_RULES.md, 2a, the K1g form (commit 431b180, 09:22)", "glide_entry_m": 0.15,
                   "on_line_m": 1e-6}
    with open(J(ROOT, "runs", "dc2_results", "display", "K1G_ANCHOR_CHECK.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=float)


if __name__ == "__main__":
    main()
