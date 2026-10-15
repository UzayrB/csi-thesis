"""ACCEPTANCE for the app's renders (Uzayr, 30 September 2026, part E): MEASURED RESULTS ONLY.

    python3 -m pipeline.live.app_acceptance --model final --mode semi_causal_realtime_screen \
        --out runs/live/renders/ACCEPTANCE.md --a3-label "<the label from DISPLAY_PROVENANCE>"

The rules are in reports/tracking/render-rules.md, never here. Each video is one recording replayed through the app at
real-time pace with its screen recorded (`app_replay --screen`); its row is that replay's own log, scored by
`app_score` (the dot error, the lock and the committed line) and checked by `app_score.rule_checks` (the
render rules, from the log alone). Participants are P1 to P6 (runs/dc2_results/teaching/anon_map.json).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join


def _anchor_line(res: dict) -> str:
    """Which form of rule 2a the anchor column counts (RENDER_RULES 2a: held for K0, the glide for K1g)."""
    forms = res["render_rules"]["anchor_form"]
    if forms not in (["glide"], ["glide_first"]):
        return ("**The anchor column** is rule 2a's held form: the green marker's first frame is the locked line's "
                "entry.")
    g = [v["anchor_glide_m"] for v in res["render_rules"]["per_recording"].values() if v.get("anchor_glide_m")]
    med = sorted(x["from_entry_median"] for x in g)[len(g) // 2] if g else None
    form = ("K1g form (the glide)" if forms == ["glide"] else
            "glide form, drawn by K1gf (the glide starts at the first anchor frame, so that frame is the entry)")
    return (f"**The anchor column** is rule 2a's {form}: on the green marker's first frame the dot is on "
            "the locked line within 0.15 m of its entry. That frame's distance from the entry: median of the "
            f"recordings' medians {med:.3f} m, at most {max(x['from_entry_max'] for x in g):.3f} m; off the line at most "
            f"{max(x['off_line_max'] for x in g):.1e} m.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="final")
    ap.add_argument("--mode", default="semi_causal_realtime_screen")
    ap.add_argument("--sessions", nargs="+", default=["03", "B2"])
    ap.add_argument("--out", default=J(REPO_ROOT, "runs", "live", "renders", "ACCEPTANCE.md"))
    ap.add_argument("--a3-label", default=None)
    a = ap.parse_args(argv)
    from pipeline.live.app_replay import SESSION_LABEL, code_of
    from pipeline.live.app_score import REPLAY, score
    L = ["# ACCEPTANCE: the app's renders. MEASURED RESULTS ONLY",
         "",
         "**The rules are in `reports/tracking/render-rules.md`,** never here.",
         "",
         "**Each video** is one recording replayed through the live app (`python3 -m pipeline.live replay "
         "--presses start --clock causal --realtime --screen`). It is the semi-constrained mode: one start press "
         "per walk, the as-it-arrives clock fit, at real-time pace, with the app's own screen recorded frame by "
         "frame.",
         "",
         "**Each row** is that replay's own log, scored by `pipeline/live/app_score.py`. The render-rule counts "
         "come from the log alone (`rule_checks`).",
         "",
         f"Model set `{a.model}` (`runs/live/models/{a.model}.json`). Written {time.strftime('%Y-%m-%d %H:%M')} SAST.",
         ""]
    if a.a3_label:
        L += [f"**The A3 display figures (the lock and the dot error) are labelled:** {a.a3_label}", ""]
    for session in a.sessions:
        res = score(a.model, a.mode, session)
        lab = SESSION_LABEL.get(session, session)
        L += [f"## {lab}", "",
              f"**Session:** lock {res['lock_pct']:.2f} [{res['lock_ci95'][0]:.2f}, {res['lock_ci95'][1]:.2f}], "
              f"committed {res['committed_pct']:.2f} [{res['committed_ci95'][0]:.2f}, {res['committed_ci95'][1]:.2f}], "
              f"{res['n_passes']} walks, {res['never_announced']} never announced.",
              "",
              "**The edge lines:** " + "; ".join(f"{ln} lock {res['edges']['lock'][ln]:.1f}, committed "
                                                  f"{res['edges']['committed'][ln]:.1f}" for ln in res["edges"]["lock"]
                                                  if res["edges"]["lock"][ln] is not None) + ".",
              "",
              f"**The dot error** (all walks): median {res['dot_error_m']['all_walks']['median']:.3f} m, p90 "
              f"{res['dot_error_m']['all_walks']['p90']:.3f} m, {res['dot_error_m']['all_walks']['within_0_5m_pct']:.1f} "
              f"percent within 0.5 m.",
              "",
              f"**On the walks whose lock is correct:** median "
              f"{res['dot_error_m']['correct_lock_walks']['median']:.3f} m.",
              "",
              f"**The display offset,** reported apart and never added: median {res['display_offset_m']['median']:.3f} m.",
              "",
              _anchor_line(res),
              "",
              "| video | participant | frames | lock % | committed % | dot err median (all / correct lock) m | within 0.5 m % "
              "| park / together / anchor / lock changes / >1 switch | switches | draw lag p99 / max s |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        d = J(REPLAY, a.model, a.mode)
        for stem, sm in sorted(res["per_recording_summary"].items(), key=lambda kv: code_of(kv[0])):
            summ = json.load(open(J(d, f"{session}__{stem}.summary.json"), encoding="utf-8"))
            v = summ.get("video") or {}
            rr = res["render_rules"]["per_recording"][stem]
            L.append(f"| `{os.path.basename(v.get('video', '-'))}` | {code_of(stem)} | {v.get('frames', '-')} | "
                     f"{sm['lock_pct']:.1f} | {sm['committed_pct']:.1f} | {sm['dot_error_median_m_all']} / "
                     f"{sm['dot_error_median_m_correct_lock']} | {sm['within_0_5m_pct_all']} | "
                     f"{len(rr['park_violations'])} / {len(rr['together_violations'])} / {len(rr['anchor_violations'])} / "
                     f"{rr['lock_changes_after_first']} / {len(rr['walks_over_one_switch'])} | {rr['n_switches']} | "
                     f"{rr['draw_lag_s']['p99']:.3f} / {rr['draw_lag_s']['max']:.3f} |")
        L.append("")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {os.path.relpath(a.out, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
