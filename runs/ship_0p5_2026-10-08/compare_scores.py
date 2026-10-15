"""Old (MIX, archived under runs/live/replay/*.pre_0p5) against new (all-0.5 s) app_score results, side by side.
Writes logs/compare_scores.json and prints a table. Reads only."""

from __future__ import annotations

import json
import os
import sys

J = os.path.join
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = J(REPO, "runs", "live", "replay")
CASES = [("final", "semi_disp-K1g_causal_realtime_screen", "B2"), ("final", "semi_disp-K1g_causal_realtime_screen", "03"),
         ("final", "full_disp-K1g_causal", "B2"), ("final", "full_disp-K1g_causal", "03"),
         ("zeroshot", "semi_disp-K1g_causal", "B2"), ("zeroshot", "full_disp-K1g_causal", "B2")]
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")


def load(model, mode, session, old):
    p = J(R, f"{model}.pre_0p5" if old else model, mode, f"SCORE_{session}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def row(d):
    if not d:
        return None
    dot = d.get("dot_error_m", {})
    return {"committed": d["committed_pct"], "committed_ci": d["committed_ci95"], "lock": d["lock_pct"],
            "lock_ci": d["lock_ci95"], "edges_committed": d["edges"]["committed"], "edges_lock": d["edges"]["lock"],
            "dot_all": dot.get("all_walks"), "dot_correct": dot.get("correct_lock_walks"),
            "announce_latency_s": d.get("announce_latency_s"), "draw_lag_s_max": d.get("render_rules", {}).get("draw_lag_s_max"),
            "window_service_s_median_by_recording": d.get("window_service_s_median_by_recording"),
            "n_switches": d.get("render_rules", {}).get("n_switches"), "vs_gate": d.get("vs_gate")}


def main() -> int:
    out = {}
    for model, mode, s in CASES:
        o, n = row(load(model, mode, s, True)), row(load(model, mode, s, False))
        out[f"{model}|{mode}|{s}"] = {"old": o, "new": n}
        f = lambda r: ("--" if not r else f"{r['committed']:.2f} [{r['committed_ci'][0]:.2f}, {r['committed_ci'][1]:.2f}] / "
                       f"{r['lock']:.2f} [{r['lock_ci'][0]:.2f}, {r['lock_ci'][1]:.2f}]")
        e = lambda r: ("--" if not r else " ".join(f"{k} {r['edges_committed'][k]:.0f}/{r['edges_lock'][k]:.0f}" for k in EDGES))
        print(f"{model:8s} {mode:38s} {s}: OLD {f(o)}  NEW {f(n)}")
        print(f"{'':58s} edges OLD {e(o)} | NEW {e(n)}")
        for k in ("dot_all", "dot_correct"):
            if o and n and o[k] and n[k]:
                print(f"{'':58s} {k}: OLD median {o[k]['median']:.3f} p90 {o[k]['p90']:.3f} within {o[k]['within_0_5m_pct']:.1f} | "
                      f"NEW median {n[k]['median']:.3f} p90 {n[k]['p90']:.3f} within {n[k]['within_0_5m_pct']:.1f}")
    with open(J(os.path.dirname(os.path.abspath(__file__)), "logs", "compare_scores.json"), "w", encoding="utf-8") as f_:
        json.dump(out, f_, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
