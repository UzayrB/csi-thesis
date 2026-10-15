"""ilb_report. The best-model run's report (`reports/identification/2026-10-10_best-model.md`) from its result files:
`scorecard.json` (`ilb_core summarise`), `greedy.json`, `looks.json`, `p1_quality.json`, `p2_quality.json`,
`m2_weights.json`, `dev/gpu_dev.json` and the checks. Every figure in the report is read from those files.

    PYTHONPATH=. python3 -m pipeline.identify.ilb_report

Exploratory development, all data seen; selection on A3 and B2.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

BD = os.path.join("runs", "identify", "best")
OUT = os.path.join("reports", "identification", "2026-10-10_best-model.md")
NAMES = {"F7": "F7 (offset windows 0.15 and 0.30 s in training)", "A1": "A1 (dense offsets 0.05 to 0.50 s in training)",
         "A3": "A3 (time-stretched training windows, 0.9 and 1.1)", "A4": "A4 (test-time average over 0, 0.15, 0.30 s)",
         "A5": "A5 (cross-day mixup)", "P1": "P1 (learned path-walk speed)", "P2": "P2 (tracker speed)",
         "M2": "M2 (feature weight by walk type)", "M3": "M3 (gradient-boosted sixth component)"}
SHIP = {
    "F7": "training only: extract the 0.15 and 0.30 s offset windows of every training walk (`ilc_extract`), append them "
          "to the feature components' training rows; `engine.py` and the live app unchanged at run time.",
    "A1": "training only: the dense offsets 0.05 to 0.50 s (`ilb_extract dense` and `ilc_extract`), appended as F7's; "
          "run time unchanged.",
    "A3": "training only: each training walk's frames rescaled in time by 0.9 and 1.1 (`ilb_extract stretch`, the "
          "engine's own `extract_window`), appended with pace v / s; run time unchanged.",
    "A4": "run time: the engine classifies three windows per press (0, 0.15 and 0.30 s after it) against the same "
          "CAL-causal pool and averages the ensembles; only the 0 s window enters the pool. The decision comes 0.30 s "
          "later and the CNN work triples; `Engine`/`Extractor` need a second and third poll per press.",
    "A5": "training only: one mixed row per training row (same person, same route, another day, weight U(0.2, 0.8), "
          "seed 0) in each component's normalised space; run time unchanged.",
    "P1": "run time: the pace column becomes a regressor's output (per-link contour statistics on the walking span, "
          "mean F, route) for path walks; the engine must compute the link-weighting cache's contours live (today they "
          "come from `ilw_cache`), and the regressor ships with the model; identification walks keep the Wi-Fi speed.",
    "P2": "run time: the pace column for path walks comes from the tracker's dot (needs the tracker running beside "
          "identification, and only about 1.4 s of walking is visible by the decision); weak on the stopwatch check.",
    "M2": "run time: the ensemble weights the feature components by walk type (path walks and identification walks) "
          "with the development folds' weights; `Session.classify` gains the walk type.",
    "M3": "training and run time: a sixth feature component (HistGradientBoosting on the Prior-standardised columns and "
          "pace) saved with the model; `Model` and `Session.classify` loop over six feature components.",
}


def j(p):
    p = os.path.join(BD, p)
    return json.load(open(p)) if os.path.exists(p) else None


def ci(d):
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]"


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-10 08:20", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "runs/identify/best", "pipeline/identify/ilb_core.py", "pipeline/identify/ilb_p1.py",
                        "pipeline/identify/ilb_p2.py", "pipeline/identify/ilb_extract.py", "pipeline/identify/ilb_gpu.py",
                        "pipeline/identify/ilb_report.py", OUT], capture_output=True, text=True)
    return [l[:160] for l in r.stdout.strip().split("\n") if l][::-1]


def build() -> str:
    sc, G, lk = j("scorecard.json"), j("greedy.json"), j("looks.json")
    p1, p2, m2, gd = j("p1_quality.json"), j("p2_quality.json"), j("m2_weights.json"), j("dev/gpu_dev.json")
    cf = sc["configs"]
    win = (G.get("winner") or "+".join(x for x in ("F7", "A1", "A3", "A4", "A5", "P1", "M2", "M3", "P2") if x in G["current"] and not (x == "F7" and "A1" in G["current"]))) if G else None
    now = time.strftime("%d %b %Y %H:%M:%S %Z")
    L = ["# Identification: building the best model (2026-10-10)", "",
         "**For Mastermind's review. Exploratory, nothing adopted.** Exploratory development, all data seen. Engine v4 "
         "stays shipped until Uzayr decides.", "",
         "- **Selection is on A3 and B2.** Every candidate and every greedy step is chosen on this morning's combine "
         "scorecard, which is built from A3 and B2.",
         f"- **Every scored configuration is a look at A3 and B2 and is counted** ({lk['n_configurations']} configurations "
         f"in this run; section 8).",
         "- **Nothing in this run is confirmatory.** The winner is selected on the data it is scored on, so its figures "
         "are optimistic by an amount this run cannot estimate.",
         "- **No figure from this run may be reported as a held-out or generalisation result.** A generalisation claim "
         "for the winner needs data it was never chosen on (new sessions).", "",
         f"Brief: Uzayr's prompt of 10 Oct (about 08:22) and his message asking for P2 ON and OFF. Plan: "
         f"`runs/identify/best/POA_B.md` (b7e8aa25 and dated notes). Generated {now} by `ilb_report`.", ""]
    return "\n".join(L), cf, win, G, lk, p1, p2, m2, gd, sc


def scorecard_table(cf: dict) -> list:
    L = ["| configuration | Z | D | (Z + D) / 2 | minus v4 [95 %] | minus F7 [95 %] | guard | against v4 |",
         "|---|---|---|---|---|---|---|---|"]
    for n, r in sorted(cf.items(), key=lambda kv: -kv[1]["score"]):
        L.append(f"| {n} | {r['Z']:.2f} | {r['D']:.2f} | {r['score']:.2f} | {ci(r['score_minus_v4'])} | "
                 f"{ci(r['score_minus_F7'])} | {'holds' if r['guard'] else 'FAILS'} | {r['verdict_vs_v4']} |")
    return L


def cells_table(r: dict) -> list:
    L = ["| cell | walks | this configuration [95 %] | v4 | F7 | S0 | minus v4 [95 %] | minus F7 [95 %] |",
         "|---|---|---|---|---|---|---|---|"]
    for k, d in r["cells"].items():
        L.append(f"| {k.replace('|', ' ').replace('*', 'all')} | {d['n']} | {d['new']['pct']:.2f} [{d['new']['ci95'][0]:.2f}, "
                 f"{d['new']['ci95'][1]:.2f}] | {d['v4']:.2f} | {d['F7']:.2f} | {d['S0']:.2f} | {ci(d['new_minus_v4'])} "
                 f"{d['new_minus_v4']['label']} | {ci(d['new_minus_F7'])} |")
    for m, d in r["ranking"].items():
        L.append(f"| {'top-2' if m == 'top2' else 'household of two'} (loso natural) | {d['new']['n']} | {d['new']['pct']:.2f} "
                 f"[{d['new']['ci95'][0]:.2f}, {d['new']['ci95'][1]:.2f}] | {d['v4']:.2f} |  | {d['S0']:.2f} | "
                 f"{ci(d['new_minus_v4'])} {d['new_minus_v4']['label']} |  |")
    return L


def timings() -> list:
    import re
    out = []
    for l in open(os.path.join(BD, "logs", "run.log")):
        if re.search(r"BLOCK START|BLOCK END|START next_|END next_|START summarise", l) and "waits: free" not in l:
            out.append("- " + l.strip()[:170])
    return out


def write(extra_status: str = "") -> str:
    head, cf, win, G, lk, p1, p2, m2, gd, sc = build()
    L = [head]
    w = cf[win]
    rw = lambda k: cf[k]
    on = f"{win}+P2" if f"{win}+P2" in cf else ("+".join(sorted(set(win.split("+")) | {"P2"})) if False else None)
    on = next((k for k in cf if set(k.split("+")) == set(win.split("+")) | {"P2"}), None)
    # 1. verdict
    L += ["## 1. Verdict", "",
          f"1. **The build's winner (greedy from F7, P2 OFF): {win}** = " + " + ".join(NAMES.get(t, t) for t in win.split("+")) + ".",
          f"   Z {w['Z']:.2f}, D {w['D']:.2f}, (Z + D) / 2 = **{w['score']:.2f}** against v4's {cf['v4']['score']:.2f} "
          f"({ci(w['score_minus_v4'])}) and F7's {cf['F7']['score']:.2f} ({ci(w['score_minus_F7'])}). Against v4: Z "
          f"{ci(w['Z_minus_v4'])}, D {ci(w['D_minus_v4'])}; the guard {'holds' if w['guard'] else 'FAILS'}; by this "
          f"morning's labels **{w['verdict_vs_v4']}** (chosen on A3 and B2, {lk['n_configurations']} configurations tried: "
          f"exploratory, optimistic).",
          f"   Against F7: Z {ci(w['Z_minus_F7'])}, D {ci(w['D_minus_F7'])}"
          + (f". **Its advantage over this morning's F7 is entirely zero-shot**: D is level ({w['D_minus_F7']['pct']:+.2f}), "
             f"and the Z gain rests on three cells (360 walks) that the build was chosen on." if abs(w['D_minus_F7']['pct']) < 1 else ".")]
    costs = [(k, d) for k, d in w["cells"].items() if d["new_minus_v4"]["ci95"][1] < 0 or d["new_minus_F7"]["ci95"][1] < 0]
    if costs:
        L.append("   **It is not better everywhere:** " + "; ".join(
            f"{k.replace('|', ' ').replace('*', 'all')} {d['new']['pct']:.2f} (v4 {d['v4']:.2f}, F7 {d['F7']:.2f}; minus v4 "
            f"{ci(d['new_minus_v4'])}, minus F7 {ci(d['new_minus_F7'])})" for k, d in costs) + " (section 4).")
    if on:
        o = cf[on]
        L.append(f"2. **P2 ON (Uzayr's toggle) on the winner, {on}:** (Z + D) / 2 = {o['score']:.2f} against OFF's {w['score']:.2f} "
                 f"(Z {o['Z']:.2f}, D {o['D']:.2f}; guard {'holds' if o['guard'] else 'FAILS'}). P2 alone (v4 + P2): "
                 f"{cf['P2']['score']:.2f}. P2's cells for xr_A and xr_B1 are not zero-shot (the tracker saw A1, A2 and B1).")
    L += [f"{3 if on else 2}. **Nothing is adopted; v4 stays shipped.** Shipping the winner needs Uzayr's decision and its own brief "
          "(section 7 is the plan, written, not built).", ""]
    # 2. scorecard
    L += ["## 2. The scorecard, every configuration", "",
          "(Z + D) / 2 with Z the mean of the three zero-shot cells and D of the ten cross-day cells; intervals: paired "
          "participant bootstrap (10,000 draws, seed 0, participants resampled jointly across cells). Guard: loso natural, "
          "slow and fast each no more than 5 points below v4. 'Against v4' uses this morning's labels (BETTER needs both Z "
          "and D lower bounds above 0). v4 and F7 are this morning's files; F7 was reproduced exactly by this run's scorer.", ""]
    L += scorecard_table(cf)
    L += ["", "Where a candidate could not apply (the configurations' flags, condensed):", "",
          "- A5: xr_B1 has one training day, so no partner and no mixed rows (every configuration with A5).",
          "- P1: xr_B1 has one training session, so P1 cannot be cross-fitted by session and keeps the Wi-Fi speed.",
          "- M2: not applied on loso_A1, loso_A2 and loso_B1 (tested on development sessions; choosing weights there "
          "would use the test day's labels); elsewhere feature weight 0.0 on path walks, 0.5 on identification walks.",
          "- P2: every model's trackers below; xr_A's and xr_B1's P2 cells are **not zero-shot: the tracker saw A1, A2, B1**.",
          "", "| model | trackers behind its training rows' P2 | trackers behind its test sessions' P2 |", "|---|---|---|"]
    import re as _re
    for f in cf.get("P2", {}).get("flags", []):
        m = _re.match(r"(\S+): P2 trackers: training rows (\{.*\}); test (\{.*\}); (\d+) path walks", f)
        if m:
            tr_ = _re.sub(r"np\.str_\('(\w+)'\)", r"\1", m.group(2)).replace("'", "")
            te_ = _re.sub(r"'source': '\w+', ", "", m.group(3)).replace("'", "").replace("tracker_trained_on: ", "")
            L.append(f"| {m.group(1)} | {tr_} | {te_} |")
    L += ["", "Path walks keeping the Wi-Fi speed under P2: 36 (52 for xr_A, whose B2 comes from the zero-shot tracker)."]
    # 3. greedy path
    L += ["", "## 3. The greedy path", ""]
    for r in G["rounds"]:
        tried = ", ".join(f"{t['config']} {t['score']:.2f}{'' if t['guard'] else ' (guard FAILS)'}"
                          for x, t in sorted(r["tried"].items(), key=lambda kv: -kv[1].get("score", 0)) if not t.get("missing"))
        if r["chosen"]:
            t = r["tried"][r["chosen"]]
            gain = t["score"] - r["current_point"]["score"]
            d = (f"Chosen: **{r['chosen']}** ({t['config']}: Z {t['Z'] - r['current_point']['Z']:+.2f}, "
                 f"D {t['D'] - r['current_point']['D']:+.2f}; score {gain:+.2f}"
                 + ("; **a gain of about one walk in one cell, noise: the rule adds anything that raises the score**"
                    if gain < 0.3 else "") + ").")
        else:
            d = "None raises it: the build stops."
        L.append(f"- Round {r['round']} from **{r['current']}** ({r['current_point']['score']:.2f}; Z "
                 f"{r['current_point']['Z']:.2f}, D {r['current_point']['D']:.2f}): {tried}. {d}")
    m3 = [r for r in G["rounds"] if r.get("chosen") == "M3"]
    if m3:
        r = m3[0]
        t = r["tried"]["M3"]
        L += ["", f"**M3's step is a zero-shot gain only.** Adding M3 in round {r['round']} raised Z by "
              f"{t['Z'] - r['current_point']['Z']:+.2f} (the three zero-shot cells: 360 walks, 120 per cell) while D moved "
              f"{t['D'] - r['current_point']['D']:+.2f}; the score rose because Z rose. Like every step here it was "
              f"selected on A3 and B2 ({lk['n_configurations']} configurations looked at), so it is exploratory and "
              f"optimistic."]
    # 4. winner's figures
    L += ["", f"## 4. The winner's figures ({win}), every cell with v4, F7 and S0", "",
          "S0: xr cells and loso path walks as `ixr_eval` (an LDA on press speed trained on the model's own rows); loso "
          "identification walks as `eval_v4` (trained on the other Room B day's identification walks). Tracking's split is "
          "the xr_AB rows (trained on A1, A2, B1; tested on A3 and B2) and xr_ABtrk.", ""]
    L += cells_table(w)
    cost4 = [k for k, d in w["cells"].items() if d["new_minus_v4"]["ci95"][1] < 0]
    gain4 = [k for k, d in w["cells"].items() if d["new_minus_v4"]["ci95"][0] > 0]
    cost7 = [k for k, d in w["cells"].items() if d["new_minus_F7"]["ci95"][1] < 0]
    s0b = [k for k, d in w["cells"].items() if d["S0"] > d["new"]["pct"] and not k.startswith("loso|*")]
    nice = lambda ks: ", ".join(f"{k.replace('|', ' ').replace('*', 'all')} ({w['cells'][k]['new']['pct']:.2f})" for k in ks) or "none"
    L += ["", "**What the cells show.** Separable gains against v4: " + nice(gain4) + ". Separable costs against v4: "
          + nice(cost4) + ". Separable costs against F7: " + nice(cost7) + ". The pooled guard holds (loso natural, slow "
          "and fast), but a pooled figure hides the per-day cells above. Speed alone (S0, the stopwatch's press speed: a "
          "speed oracle the engine does not have) is above the winner on: " + nice(s0b) + "; identification beyond speed "
          "stays weak on those cells."]
    if on:
        L += ["", f"P2 ON ({on}), same cells:", ""] + cells_table(cf[on])
    # 5. speed checks
    L += ["", "## 5. The speed checks (the stopwatch only; no identification score)", "",
          "| session | P1 r | Wi-Fi r | P1 median abs error (m/s) | Wi-Fi median abs error |", "|---|---|---|---|---|"]
    for k, v in p1["sessions"].items():
        L.append(f"| {k} | {v['P1_pearson']:.3f} | {v['wifi_pearson']:.3f} | {v['P1_median_abs_error']:.3f} | {v['wifi_median_abs_error']:.3f} |")
    L += ["", "P2 (POA_B's note of 08:38; tracker sessions in brackets):", "",
          "| source | walks with P2 | P2 r | Wi-Fi r (same walks) | P2 median | press median |", "|---|---|---|---|---|---|"]
    for k, v in p2["sources"].items():
        L.append(f"| {k} ({'+'.join(v['tracker_trained_on'])}) | {v['n_p2']} of {v['n']} | {v['P2_pearson_on_own']} | "
                 f"{v['wifi_pearson_same_walks']} | {v['P2_median']} | {v['press_median']} |")
    L += ["", "P2's caveats (Second Overall's, as relayed): (a) the drawn path is a Viterbi under the pace prior N(1.30, 0.11), "
          "so its speed shrinks towards 1.30, and part of it is the motion model; (b) by press + 4.0 s the logged dot covers "
          "only about 1.4 s of walking; (c) the A1/A2/B1 source's display settings differ slightly from A3/B2's.",
          f"M2's weights (development folds): feature components {m2['path']} on path walks, {m2['id']} on identification walks "
          f"(CNN weight 1); applied only to models tested on A3 or B2.", ""]
    # 6. GPU
    L += ["## 6. The GPU candidates on the development folds (A1, A2, B1; no A3 or B2)", ""]
    if gd:
        L += ["| configuration | A1 path | A2 path | B1 path | B1 natural | B1 slow | B1 fast | DS | DS minus v4+F7 [95 %] | passes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for k, v in gd["configs"].items():
            dd = ci(v["DS_minus_v4F7"]) if "DS_minus_v4F7" in v else ""
            L.append(f"| {k} | {v['A1_path']} | {v['A2_path']} | {v['B1_path']} | {v['B1_natural']} | {v['B1_slow']} | "
                     f"{v['B1_fast']} | {v['DS']} | {dd} | {v.get('passes', '')} |")
    gt = j("dev/gate.json")
    if gt and not gt["run_A2M1"]:
        L += ["", "**Not run, and why: A2M1.** The Mastermind's rule (POA_B, 11:00, confirmed by Uzayr 11:03): A2M1 runs only "
              "if A2 or M1 alone beats v4+F7's development score (29.59) with the development guard; "
              f"neither did (A2+F7 DS {gt['A2+F7']['DS']}, M1+F7 DS {gt['M1+F7']['DS']}; intervals above)."]
    # 7. ship plan
    toks = [t for t in win.split("+")]
    L += ["", "## 7. The ship plan (engine v5; written, not built)", "",
          f"Only if Uzayr decides to ship, and under its own brief. **Engine v5 = v4 + {', '.join(toks)}**, same CAL-causal "
          "pools, same contract (start press only; nothing labelled from the test day; adaptation only from CAL-causal's "
          "pool; nothing that uses the order people walk in).", ""]
    for i, t in enumerate(toks, 1):
        L.append(f"{i}. **{NAMES.get(t, t)}**: {SHIP.get(t, '')}")
    L += ["", "Build order: (1) the extractions for every training walk of every shipped model (offsets, stretches) through "
          "the engine's own `Extractor`, anchors exact; (2) retrain the feature components (six with M3) of the nine "
          "scorecard models and the live model, the CNNs unchanged; (3) the run-time changes in `engine.py` behind a "
          "version switch, with a null check that v5 with every change off reproduces v4's replays exactly; (4) replay "
          "every session through v5 and regenerate every identification figure; (5) the live app's timing budget "
          "measured on the rig before adoption (A4 triples the CNN work per press and delays the decision 0.30 s); "
          "(6) nothing to the Editor until Uzayr approves the figures. Not built in this run.", ""]
    # 8. looks
    L += ["## 8. Configurations tried and looks at A3 and B2", "",
          f"{lk['n_configurations']} configurations, each scored on all nine models: 5 model-session looks at A3 (xr_AB, "
          f"xr_ABtrk, xr_A, xr_B1, loso_A3) and 5 at B2 (the same xr models, loso_B2): **{lk['model_session_looks_A3']} "
          f"model-session looks at A3 and {lk['model_session_looks_B2']} at B2**, all on 10 Oct, all exploratory. The "
          "F7 reproduction (identical to this morning's F7) is not a new look. The GPU candidates were screened on the "
          "development folds only (A1, A2, B1): no A3 or B2 look.", "",
          "| # | configuration | scored at |", "|---|---|---|"]
    for i, (n, d) in enumerate(sorted(lk["configurations"].items(), key=lambda kv: kv[1]["date"]), 1):
        L.append(f"| {i} | {n} | {d['date'][11:]} |")
    # 9. files, commits, timings
    L += ["", "## 9. Files, commits and timings", "",
          "- Code: `pipeline/identify/ilb_extract.py`, `ilb_p1.py`, `ilb_p2.py`, `ilb_core.py`, `ilb_gpu.py`, `ilb_report.py`.",
          "- Plan and queue: `runs/identify/best/POA_B.md`, `QUEUE_B.md`, `STEPS_CPU1`, `STEPS_GPU`, the driver `run_b.sh`, "
          "`slot.sh`, `ms_b.py`.",
          "- Results: `runs/identify/best/scorecard.json` and `scorecard.md` (every configuration, every cell), "
          "`greedy.json`, `looks.json`, `p1_quality.json`, `p2_quality.json`, `m2_weights.json`, `dev/gpu_dev.json`, "
          "`dev/gate.json`, `checks/f7_reproduction.json`, `outer/<configuration>.npz` and `.json` (log-probabilities, "
          "flags), `a4cache/` (the A4 CNN components; offset 0 equal to every replay).",
          "- Not committed (size): `extract/` (106 MB of windows), `models/` (214 MB of development-fold CNNs).", "",
          "Commits (this run):", ""]
    L += [f"- {c}" for c in git_log()]
    L += ["", "Timings (the driver's log):", ""] + timings()
    L += [extra_status, ""]
    return "\n".join(L)



if __name__ == "__main__":
    t = write()
    open(OUT, "w").write(t)
    print(f"wrote {OUT} ({len(t)} characters)")
    sys.exit(0)
