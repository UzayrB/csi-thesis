"""iv6_report. The tables of `reports/identification/2026-10-15_components-and-features.md`, generated from
`runs/identify/v6_test/part1.json` and `part2.json` (no number typed by hand), and `results.json` (both parts with the
checks and commits).

    PYTHONPATH=. python3 -m pipeline.identify.iv6_report tables      # prints the tables (markdown) to tables.md
    PYTHONPATH=. python3 -m pipeline.identify.iv6_report results     # results.json

Development evaluation, all data seen; exploratory.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import iv6_common as K

FAMS = ["rhythm", "cycle templates", "Doppler contours", "spectral shape", "wavelets", "modulation", "cadence"]
SHORT = {"rf": "rf", "rf_prior": "rf_prior", "rf_pace_prior": "rf_pace_prior", "et_pace_prior": "et_pace_prior",
         "lda_pace_prior": "lda_pace_prior (LDA)", "hgb_pace_prior": "hgb_pace_prior", "cnn": "cnn",
         "cnn_prior": "cnn_prior", "cnn_perlink_prior": "cnn_perlink_prior (per-link CNN)"}


def ci(d, k="pct", sign=True) -> str:
    f = "{:+.2f}" if sign else "{:.2f}"
    return f"{f.format(d[k])} [{f.format(d['ci95'][0])}, {f.format(d['ci95'][1])}]"


def p1_tables(r: dict) -> list:
    L = []
    c = r["candidates"]
    L += ["### Table 1. The five candidates against v5 (cross-fitted; the installation rule on top, as judged)", "",
          "| candidate | Z | D | (Z + D) / 2 | minus v5 [95 %] | guards (natural, slow, fast, Room A, Room B tracking) | core (A3+B2 path, all B2) | passes |",
          "|---|---|---|---|---|---|---|---|"]
    v5c = c["INVLL"]["with_rule"]["cells"]
    gk = ["guard loso natural", "guard loso slow", "guard loso fast", "guard Room A tracking", "guard Room B tracking"]
    ck = ["core xr_ABtrk A3+B2 path", "core xr_A all B2"]
    L.append(f"| v5 (equal weights) | 33.61 | 33.35 | 33.48 | 0 | {', '.join(f'{v5c[k]['v5']:.2f}' for k in gk)} | "
             f"{', '.join(f'{v5c[k]['v5']:.2f}' for k in ck)} | reference |")
    for nm in ("INVLL", "TEMP", "STACK", "TOP3", "BEST1"):
        x = c[nm]["with_rule"]
        g = ", ".join(f"{x['cells'][k]['acc']['pct']:.2f}{'' if x['guards_hold'][k[6:]] else ' (fails)'}" for k in gk)
        co = ", ".join(f"{x['cells'][k]['acc']['pct']:.2f}{'' if x['core_holds'][k[5:]] else ' (falls)'}" for k in ck)
        L.append(f"| {nm} | {x['Z']:.2f} | {x['D']:.2f} | {x['score']:.2f} | {ci(x['score_minus_v5'])} | {g} | {co} | "
                 f"{'**yes**' if x['PASSES'] else 'no'} |")
    L += ["", "Without the installation rule (information only; cannot pass):", "",
          "| candidate | Z | D | (Z + D) / 2 | minus v5 [95 %] |", "|---|---|---|---|---|"]
    w = r["v5_without_rule"]
    L.append(f"| v5 without the rule (every a = 1) | {w['Z']:.2f} | {w['D']:.2f} | {w['score']:.2f} | {ci(w['score_minus_v5'])} |")
    for nm in ("INVLL", "TEMP", "STACK", "TOP3", "BEST1"):
        x = c[nm]["without_rule"]
        L.append(f"| {nm} | {x['Z']:.2f} | {x['D']:.2f} | {x['score']:.2f} | {ci(x['score_minus_v5'])} |")
    L += ["", "### Table 2. The weights each candidate fitted, per scored session (fitted on the other four sessions' held-out walks)", "",
          "| candidate | scored session | " + " | ".join(K.COMPS) + " |", "|---|---|" + "---|" * len(K.COMPS)]
    for nm in ("INVLL", "TEMP", "STACK", "TOP3", "BEST1"):
        for S, wv in c[nm]["with_rule"]["weights"].items():
            L.append(f"| {nm} | {S} | " + " | ".join(f"{wv[k]:.2f}" for k in K.COMPS) + " |")
    d = r["diagnostics"]["all_held_out"]
    L += ["", f"### Table 3. Each component alone and in the sum, on all 1,019 held-out walks (each session by the model "
          f"that never trained on it); v5 {r['v5_all_held_out_acc']['pct']:.2f} [{r['v5_all_held_out_acc']['ci95'][0]:.2f}, "
          f"{r['v5_all_held_out_acc']['ci95'][1]:.2f}]", "",
          "| component | accuracy alone [95 %] | log-loss | Brier | calibration error | sharpness (walk / 0 s window) | share of v5's margin (pooled / median) | leaving it out flips (right to wrong / wrong to right) | v5 without it, minus v5 [95 %] |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k in K.COMPS:
        x = d[k]
        L.append(f"| {SHORT[k]} | {ci(x['acc'], sign=False)} | {x['logloss']:.3f} | {x['brier']:.3f} | {x['ece']:.3f} | "
                 f"{x['sharpness']:.2f} / {x['sharpness_w0']:.2f} | {x['margin_share_pooled']:.3f} / {x['margin_share_median']:.3f} | "
                 f"{x['loco_flips']} ({x['loco_right_to_wrong']} / {x['loco_wrong_to_right']}) | {ci(x['loco_minus_v5'])} |")
    b = r["diagnostics"]["best_by_session"]
    L += ["", "### Table 4. The best single component, session by session (held-out walks), and what BEST1 chose", "",
          "| held-out session | best by accuracy | its accuracy | best by log-loss | BEST1's choice (cross-fitted on the other four) |",
          "|---|---|---|---|---|"]
    for S in K.SESSIONS:
        ba = b["per_session"][S]["by_acc"]
        L.append(f"| {S} | {ba} | {r['diagnostics']['sessions'][S][ba]['acc']['pct']:.2f} | {b['per_session'][S]['by_logloss']} | "
                 f"{', '.join(c['BEST1']['with_rule']['fit_info'][S]['chosen'])} |")
    L += ["", f"By accuracy: {b['distinct_by_acc']} different winners and {b['changes_by_acc']} changes over the five sessions; "
          f"by log-loss: {b['distinct_by_logloss']} and {b['changes_by_logloss']}.", ""]
    L += ["### Table 5. Oracles (UNATTAINABLE: chosen or fitted on the scored walks themselves)", "",
          "| cell | v5 | best single component on the cell | STACK fitted on the cell itself |", "|---|---|---|---|"]
    for nm, o in r["oracles"].items():
        L.append(f"| {nm} | {v5c[nm]['v5']:.2f} | {o['best_single_acc']:.2f} ({o['best_single']}) | {o['stack_in_cell_acc']['pct']:.2f} |")
    return L


def p1_errcorr(r: dict) -> list:
    p = r["diagnostics"]["pairs"]["all_held_out"]
    F, Cn = set(K.FEATC), set(K.CNNC)

    def sel(f):
        return [v for k, v in p.items() if f(*k.split("|"))]
    rows = [("feature with feature", sel(lambda a, b: a in F and b in F)), ("CNN with CNN", sel(lambda a, b: a in Cn and b in Cn)),
            ("feature with CNN", sel(lambda a, b: (a in F) != (b in F)))]
    L = ["### Table 6. Pairwise errors on the held-out walks (median [range] over the pairs)", "",
         "| pairs | error correlation | disagreement (argmax differs) |", "|---|---|---|"]
    for nm, v in rows:
        e = [x["error_corr"] for x in v]
        dg = [x["disagreement"] for x in v]
        L.append(f"| {nm} ({len(v)}) | {np.median(e):.3f} [{min(e):.3f}, {max(e):.3f}] | {np.median(dg):.3f} [{min(dg):.3f}, {max(dg):.3f}] |")
    return L


def p2_tables(q: dict) -> list:
    L = []
    a = q["2a"]["cells"]
    cells = ["core pooled", "xr_ABtrk A3+B2 path", "xr_A all B2", "loso natural", "loso slow", "loso fast"]
    L += ["### Table 7. Grouped permutation importance: the ensemble's accuracy drop (points) when a group is permuted (20 repeats; 95 % participant intervals)", "",
          "| group (columns) | " + " | ".join(f"{c} ({a[c]['n']}; v5 {a[c]['base_ens_acc']:.2f})" for c in cells) + " |",
          "|---|" + "---|" * len(cells)]
    G = q["groups"]
    for g in FAMS + ["Wi-Fi speed"]:
        L.append(f"| {g} ({G[g]}) | " + " | ".join(ci(a[c]["groups"][g]["ens_acc_drop"]) for c in cells) + " |")
    L += ["", "### Table 8. The same, family by link", "", "| group (columns) | " + " | ".join(cells) + " |", "|---|" + "---|" * len(cells)]
    for f in FAMS:
        for lk in ("RX1", "RX2", "RX3", "across links"):
            g = f"{f} {lk}"
            if g in a["core pooled"]["groups"]:
                L.append(f"| {g} ({G[g]}) | " + " | ".join(ci(a[c]["groups"][g]["ens_acc_drop"]) for c in cells) + " |")
    for lk in ("RX1", "RX2", "RX3"):
        g = f"all families {lk}"
        L.append(f"| {g} ({G[g]}) | " + " | ".join(ci(a[c]["groups"][g]["ens_acc_drop"]) for c in cells) + " |")
    L += ["", "### Table 9. Each feature component's own drop on core pooled: accuracy (points) and log-loss rise (nats)", "",
          "| group | " + " | ".join(K.FEATC) + " |", "|---|" + "---|" * len(K.FEATC)]
    cp = a["core pooled"]
    L.append("| (unpermuted accuracy) | " + " | ".join(f"{cp['base_comp_acc'][c]:.2f}" for c in K.FEATC) + " |")
    for g in FAMS + ["Wi-Fi speed"]:
        L.append(f"| {g} | " + " | ".join(f"{cp['groups'][g]['comp'][c]['acc_drop']['pct']:+.2f} / "
                                         f"{cp['groups'][g]['comp'][c]['nll_rise']['mean']:+.3f}" for c in K.FEATC) + " |")
    L += ["", "### Table 10. Speed hidden in the families (2c): the drop with the Wi-Fi speed permuted together, core pooled and loso natural", "",
          "| family | core pooled: family / speed alone / both | loso natural: family / speed alone / both |", "|---|---|---|"]
    for f in FAMS:
        cells_ = []
        for c in ("core pooled", "loso natural"):
            gg = a[c]["groups"]
            cells_.append(f"{gg[f]['ens_acc_drop']['pct']:+.2f} / {gg['Wi-Fi speed']['ens_acc_drop']['pct']:+.2f} / "
                          f"{gg[f + ' + Wi-Fi speed']['ens_acc_drop']['pct']:+.2f}")
        L.append(f"| {f} | {cells_[0]} | {cells_[1]} |")
    s = q["2c_correlations"]
    L += ["", f"### Table 11. Correlation with speed per family (2c; all {s['rows']} walks of A1 to B2; Wi-Fi against press speed r = {s['wifi_vs_press_r']})", "",
          "| family | Wi-Fi speed: median / largest abs r, columns above 0.3, ridge R^2 | press speed: the same |", "|---|---|---|"]
    for f in FAMS + ["all 630"]:
        x, y = s["Wi-Fi speed"][f], s["press speed"][f]
        L.append(f"| {f} ({x['columns']}) | {x['median |r|']:.3f} / {x['largest |r|']:.3f}, {x['columns |r| > 0.3']}, {x['ridge R2 (leave one session out)']:.3f} | "
                 f"{y['median |r|']:.3f} / {y['largest |r|']:.3f}, {y['columns |r| > 0.3']}, {y['ridge R2 (leave one session out)']:.3f} |")
    b = q["2b"]
    L += ["", f"### Table 12. Person or day (2b; balanced accuracy, %; chance: person {b['chance']['person']}, session {b['chance']['session']}, "
          f"day in Room A {b['chance']['day in Room A']}, day in Room B {b['chance']['day in Room B']})", "",
          "| family | input | person across days | session | day in Room A | day in Room B |", "|---|---|---|---|---|---|"]
    for f in FAMS + ["all 630"]:
        for kind in ("raw", "session-standardised"):
            x = b[kind][f]
            L.append(f"| {f} | {kind} | {x['person across days (leave one session out)']:.2f} | {x['session (leave one participant out)']:.2f} | "
                     f"{x['day in Room A (leave one participant out)']:.2f} | {x['day in Room B (leave one participant out)']:.2f} |")
    v = b["variance_shares_raw"]
    L += ["", "### Table 13. Variance shares per column (raw; medians over the family's columns). \"Day within person\" is the spread of "
          "each participant's day means around that participant's mean, so it includes each day's shift common to everyone", "",
          "| family | between participants | day within person | between participants over day within person | columns where between participants is larger |",
          "|---|---|---|---|---|"]
    for f in FAMS + ["all 630"]:
        x = v[f]
        L.append(f"| {f} | {x['person share median']:.3f} | {x['person x day share median']:.3f} | {x['person over person x day, median']:.2f} | "
                 f"{x['columns where person > person x day']} of {x['columns']} |")
    d = q["2d_secondary"]
    L += ["", "### Table 14. Secondary only (biased): impurity importances and LDA |coefficients|, share by family, mean over the four models", "",
          "| component | " + " | ".join(FAMS) + " | Wi-Fi speed |", "|---|" + "---|" * (len(FAMS) + 1)]
    key = {"rhythm": "rhy", "cycle templates": "tplacf", "Doppler contours": "dop", "spectral shape": "spec", "wavelets": "wav",
           "modulation": "mod", "cadence": "cad", "Wi-Fi speed": "speed"}
    for c in ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior"):
        vals = []
        for f in FAMS + ["Wi-Fi speed"]:
            xs = [d[m][c].get(key[f], np.nan) for m in d]
            vals.append("-" if all(np.isnan(xs)) else f"{np.nanmean(xs):.3f}")
        L.append(f"| {c} | " + " | ".join(vals) + " |")
    return L


def tables() -> str:
    r = json.load(open(os.path.join(K.OUT, "part1.json")))
    L = p1_tables(r) + [""] + p1_errcorr(r)
    p2 = os.path.join(K.OUT, "part2.json")
    if os.path.exists(p2):
        q = json.load(open(p2))
        from pipeline.identify import iv6_features as F
        q["groups"] = {nm: len(v[0]) + (1 if v[1] else 0) for nm, v in F.groups().items()}
        L += [""] + p2_tables(q)
    txt = "\n".join(L) + "\n"
    open(os.path.join(K.OUT, "tables.md"), "w").write(txt)
    return txt


def results() -> None:
    out = {"label": K.LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"),
           "plan": {"part1": "runs/identify/engine/PLAN.md note 2026-10-15 14:53, commit 0243a768",
                    "part2": "note headed 15:05 (written 15:03:44; corrections cc8d3770, 1d21ccfc), commit 72af18c1"},
           "checks": {"ensemble_equal": json.load(open(os.path.join(K.OUT, "checks", "ensemble_equal.json")))}}
    oe = os.path.join(K.OUT, "checks", "offline_equal.json")
    if os.path.exists(oe):
        out["checks"]["offline_equal"] = json.load(open(oe))
    out["part1"] = json.load(open(os.path.join(K.OUT, "part1.json")))
    p2 = os.path.join(K.OUT, "part2.json")
    if os.path.exists(p2):
        out["part2"] = json.load(open(p2))
    json.dump(out, open(os.path.join(K.OUT, "results.json"), "w"), indent=1, default=str)


def prose_numbers() -> dict:
    """The numbers the record's prose quotes, each computed from the JSON; `report` asserts each appears in the text."""
    r = json.load(open(os.path.join(K.OUT, "part1.json")))
    q = json.load(open(os.path.join(K.OUT, "part2.json")))
    c, d = r["candidates"], r["diagnostics"]["all_held_out"]
    a, b, s = q["2a"]["cells"], q["2b"], q["2c_correlations"]
    cp, nat = a["core pooled"]["groups"], a["loso natural"]["groups"]
    out = {
        "per-link CNN alone": f"{d['cnn_perlink_prior']['acc']['pct']:.2f} %",
        "v5 held-out": f"{r['v5_all_held_out_acc']['pct']:.2f} %",
        "TEMP": ci(c["TEMP"]["with_rule"]["score_minus_v5"]),
        "BEST1": ci(c["BEST1"]["with_rule"]["score_minus_v5"]),
        "no rule": f"{-r['v5_without_rule']['score_minus_v5']['pct']:.2f} points [{r['v5_without_rule']['score_minus_v5']['ci95'][0]:+.2f}, "
                   f"{r['v5_without_rule']['score_minus_v5']['ci95'][1]:+.2f}]",
        "Doppler core": ci(cp["Doppler contours"]["ens_acc_drop"]),
        "modulation core": ci(cp["modulation"]["ens_acc_drop"]),
        "wavelets core": ci(cp["wavelets"]["ens_acc_drop"]),
        "Doppler natural": ci(nat["Doppler contours"]["ens_acc_drop"]),
        "cycle core": ci(cp["cycle templates"]["ens_acc_drop"]),
        "cadence core": ci(cp["cadence"]["ens_acc_drop"]),
        "cadence natural": ci(nat["cadence"]["ens_acc_drop"]),
        "rhythm core": ci(cp["rhythm"]["ens_acc_drop"]),
        "speed core": ci(cp["Wi-Fi speed"]["ens_acc_drop"]),
        "mod xr_A": ci(a["xr_A all B2"]["groups"]["modulation"]["ens_acc_drop"]),
        "raw session": f"{b['raw']['all 630']['session (leave one participant out)']:.2f} %",
        "raw person": f"{b['raw']['all 630']['person across days (leave one session out)']:.2f} %",
        "std session": f"{b['session-standardised']['all 630']['session (leave one participant out)']:.2f} %",
        "std person": f"{b['session-standardised']['all 630']['person across days (leave one session out)']:.2f} %",
        "Doppler raw session": f"{b['raw']['Doppler contours']['session (leave one participant out)']:.2f} %",
        "Doppler raw person": f"{b['raw']['Doppler contours']['person across days (leave one session out)']:.2f} %",
        "Doppler press R2": f"R^2 {s['press speed']['Doppler contours']['ridge R2 (leave one session out)']:.3f}",
        "Doppler wifi R2": f"R^2 {s['Wi-Fi speed']['Doppler contours']['ridge R2 (leave one session out)']:.3f}",
        "columns between > day": f"{q['2b']['variance_shares_raw']['all 630']['columns where person > person x day']} of 630",
        "feat-cnn corr": f"{np.median([v['error_corr'] for k, v in r['diagnostics']['pairs']['all_held_out'].items() if (k.split('|')[0] in K.FEATC) != (k.split('|')[1] in K.FEATC)]):.3f}",
    }
    return out


def report() -> str:
    import subprocess
    tables()
    T = open(os.path.join(K.OUT, "tables.md")).read()
    i = T.index("### Table 7.")
    tpl = open(os.path.join(K.OUT, "REPORT_TEMPLATE.md")).read()
    missing = {k: v for k, v in prose_numbers().items() if v not in tpl}
    assert not missing, f"prose numbers not found in the template: {missing}"
    log = subprocess.run(["git", "log", "--format=%h %s", "--", "pipeline/identify/iv6_common.py", "pipeline/identify/iv6_components.py",
                          "pipeline/identify/iv6_features.py", "pipeline/identify/iv6_report.py", "runs/identify/v6_test",
                          "runs/identify/engine/PLAN.md"], capture_output=True, text=True).stdout.splitlines()
    log = [l for l in log if "Components-and-features" in l or "PLAN.md: the" in l]
    commits = "\n" + "\n".join(f"  - {l[:150]}" for l in reversed(log))
    txt = (tpl.replace("{{BUILT}}", time.strftime("%Y-%m-%d %H:%M:%S SAST") + " by `iv6_report report`")
           .replace("{{TABLES_PART1}}", T[:i].strip()).replace("{{TABLES_PART2}}", T[i:].strip()).replace("{{COMMITS}}", commits))
    assert "{{" not in txt
    out = os.path.join("reports", "identification", "2026-10-15_components-and-features.md")
    open(out, "w").write(txt)
    return out


if __name__ == "__main__":
    {"tables": lambda: print(tables()), "results": results, "report": lambda: print(report())}[sys.argv[1]]()
