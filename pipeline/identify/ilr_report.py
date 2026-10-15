"""ilr_report. The Room A run's report (`reports/identification/2026-10-10_room-a.md`) from its result files: `mixes.json`,
`exact.json`, `summary.json`, `looks.json`, the stores of v4 (this morning), the build's winner and the pick. Every
figure is read from those files.

    PYTHONPATH=. python3 -m pipeline.identify.ilr_report

Exploratory development, all data seen; selection uses the combine scorecard (A3 and B2).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import ilb_core as B
from pipeline.identify import ilb_report as BR
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC
from pipeline.identify import ilr_core as R

OUT = os.path.join("reports", "identification", "2026-10-10_room-a.md")
NAME = {"xr_A": "A1+A2 [xr_A]", "xr_ABtrk": "A1+A2+B1 path walks [xr_ABtrk]",
        "xr_AB": "A1+A2+B1 path walks + B1's identification walks [xr_AB]", "xr_B1": "B1, path and identification walks [xr_B1]",
        "loso": "the other four sessions [loso]"}
KIND = {"path": "path walks", "natural": "natural walks", "slow": "slow walks", "fast": "fast walks"}


def j(p):
    p = os.path.join(R.RD, p)
    return json.load(open(p)) if os.path.exists(p) else None


def label(c) -> str:
    m, s, k = c
    if s == "*":
        return f"{NAME[m]} to each held-out session's {KIND[k]}" + (" (B1's and B2's)" if k != "path" else "")
    return f"{NAME[m]} to {s} {KIND[k]}"


def rows(c, st):
    return B.cell_rows_b(c, st)


def s0(c) -> np.ndarray:
    m, s, k = c
    return B.s0_session(c) if (m == "loso" and s != "*") else CO.s0_cell(c)


def ci(d) -> str:
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]"


def pct(ok, who) -> str:
    from pipeline.identify import idw_eval as EV
    d = EV._boot(ok, who)
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def cell_table(cells: list, S: dict) -> list:
    from pipeline.identify import ixr_eval as XE
    who_all = PC.bank()["a"]["anon"]
    has_pick = "pick" in S
    hdr = ["cell", "walks", "v4", "the winner"] + (["the pick [95 %]", "S0", "pick minus v4 [95 %]", "pick minus S0 [95 %]"]
                                                    if has_pick else ["S0", "winner minus v4 [95 %]", "winner minus S0 [95 %]"])
    L = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for c in cells:
        r4, ok4, _ = rows(c, S["v4"])
        rw, okw, _ = rows(c, S["winner"])
        assert np.array_equal(r4, rw)
        z0 = s0(c)
        w = who_all[r4]
        if has_pick:
            rp, okp, _ = rows(c, S["pick"])
            assert np.array_equal(r4, rp)
            L.append(f"| {label(c)} | {len(r4)} | {100 * ok4.mean():.2f} | {100 * okw.mean():.2f} | {pct(okp, w)} | "
                     f"{100 * z0.mean():.2f} | {ci(XE.paired(okp, ok4, w))} | {ci(XE.paired(okp, z0, w))} |")
        else:
            L.append(f"| {label(c)} | {len(r4)} | {100 * ok4.mean():.2f} | {pct(okw, w)} | {100 * z0.mean():.2f} | "
                     f"{ci(XE.paired(okw, ok4, w))} | {ci(XE.paired(okw, z0, w))} |")
    return L


def zd(st: dict, ref: dict) -> dict:
    """Z, D, (Z + D) / 2 of `st` against `ref` with the paired participant bootstrap (10,000 draws, seed 0, jointly)."""
    who_all = PC.bank()["a"]["anon"]
    counts = CO.boot_counts()
    out = {}
    bs = {}
    for g, cells in (("Z", CO.ZERO), ("D", CO.CROSS)):
        new, old, pn, po = [], [], [], []
        for c in cells:
            r_, ok, _ = CO.cell_rows(c, st)
            _r, ok0, _ = CO.cell_rows(c, ref)
            w = who_all[r_]
            for o, Bv, P in ((ok, new, pn), (ok0, old, po)):
                k, n = CO.per_part(o, w)
                Bv.append((counts @ k) / (counts @ n))
                P.append(k.sum() / n.sum())
        bs[g] = (np.mean(new, axis=0) - np.mean(old, axis=0), float(np.mean(pn) - np.mean(po)))
        lo, hi = np.percentile(bs[g][0], [2.5, 97.5])
        out[g] = {"pct": round(100 * bs[g][1], 2), "ci95": [round(100 * lo, 2), round(100 * hi, 2)]}
    sc = (bs["Z"][0] + bs["D"][0]) / 2
    lo, hi = np.percentile(sc, [2.5, 97.5])
    out["score"] = {"pct": round(50 * (bs["Z"][1] + bs["D"][1]), 2), "ci95": [round(100 * lo, 2), round(100 * hi, 2)]}
    return out


def zd_half(st: dict, ref: dict, h: str) -> dict:
    """One half's Z, D and (Z + D) / 2 of `st` minus `ref` (paired participant bootstrap, 10,000 draws, seed 0, jointly)."""
    who_all = PC.bank()["a"]["anon"]
    counts = CO.boot_counts()
    bs, out = {}, {}
    for g in ("Z", "D"):
        new, old, pn, po = [], [], [], []
        for c in R.HALF[h][g]:
            r_, ok, _ = B.cell_rows_b(c, st)
            _r, ok0, _ = B.cell_rows_b(c, ref)
            w = who_all[r_]
            for o, Bv, P in ((ok, new, pn), (ok0, old, po)):
                k, n = CO.per_part(o, w)
                Bv.append((counts @ k) / (counts @ n))
                P.append(k.sum() / n.sum())
        bs[g] = (np.mean(new, axis=0) - np.mean(old, axis=0), float(np.mean(pn) - np.mean(po)), float(np.mean(pn)))
        out[g] = round(100 * bs[g][2], 2)
    sc = (bs["Z"][0] + bs["D"][0]) / 2
    lo, hi = np.percentile(sc, [2.5, 97.5])
    out["score"] = round(50 * (bs["Z"][2] + bs["D"][2]), 2)
    out["minus"] = {"pct": round(50 * (bs["Z"][1] + bs["D"][1]), 2), "ci95": [round(100 * lo, 2), round(100 * hi, 2)]}
    return out


def split_table(S: dict, sm: dict, n: int) -> list:
    rows_ = [("v4", "v4 (reference)"), ("winner", "this morning's winner (chosen among 35 configurations this morning)")]
    if "pick" in S:
        rows_.append(("pick", f"PLAN_RA's pick (chosen on both halves, among {n:,} configurations)"))
    rows_ += [("split_A3", f"chosen on the A3 half only, among {n:,}: {mixname(sm['split']['A3']['pick'])}"
               + ("" if sm["split"]["A3"]["how"] == "qualifier" else f" ({sm['split']['A3']['how']})")),
              ("split_B2", f"chosen on the B2 half only, among {n:,}: {mixname(sm['split']['B2']['pick'])}"
               + ("" if sm["split"]["B2"]["how"] == "qualifier" else f" ({sm['split']['B2']['how']})"))]
    L = ["| configuration | A3 half: (Z + D) / 2 (Z, D) | minus v4 [95 %] | minus the winner [95 %] | B2 half: (Z + D) / 2 (Z, D) | minus v4 [95 %] | minus the winner [95 %] |",
         "|---|---|---|---|---|---|---|"]
    for key, nm in rows_:
        cells = []
        for h in ("A3", "B2"):
            a, b_ = zd_half(S[key], S["v4"], h), zd_half(S[key], S["winner"], h)
            mark = "**" if (key == "split_A3" and h == "B2") or (key == "split_B2" and h == "A3") else ""
            cells += [f"{mark}{a['score']:.2f}{mark} ({a['Z']:.2f}, {a['D']:.2f})", ci(a["minus"]), ci(b_["minus"])]
        L.append(f"| {nm} | " + " | ".join(cells) + " |")
    return L


def mixname(r: dict) -> str:
    w = (f"w_path {r['w_A']}" if r["C1"] else f"w_A {r['w_A']}, w_B {r['w_B']}, w_unseen {r['w_unseen']}")
    return f"{r['base']}, {'C1' if r['C1'] else 'C2'} ({w}; w_id {r['w_id']})"


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-10 15:20", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "runs/identify/roomA", "pipeline/identify/ilr_core.py", "pipeline/identify/ilr_report.py", OUT],
                       capture_output=True, text=True)
    return [l[:160] for l in r.stdout.strip().split("\n") if l][::-1]


def write() -> str:
    mx, ex, sm, lk = j("mixes.json"), j("exact.json"), j("summary.json"), j("looks.json")
    CO.OUTD = B.CB_OUT
    S = {"v4": CO.load("v4")}
    CO.OUTD = os.path.join(R.RD, "stores")
    S["winner"] = CO.load("winner")
    pick = sm.get("pick")
    if pick:
        S["pick"] = CO.load("pick")
    for h in ("A3", "B2"):
        S[f"split_{h}"] = CO.load(f"split_{h}")
    win = sm["winner"]
    P = pick or win
    who = "the pick" if pick else "the winner"
    now = time.strftime("%d %b %Y %H:%M:%S %Z")
    L = ["# Identification: lift Room A, keep the gains, pick the model to ship (2026-10-10)", "",
         f"**For Mastermind's review.** Selection used this morning's combine scorecard (A3 and B2): the {lk['n_configurations']:,} "
         f"configurations here ({lk['model_session_looks_A3']:,} model-session looks at A3 and as many at B2) were chosen and "
         "scored on the same data, so nothing is confirmatory, no figure is a held-out or generalisation result, and the "
         "pick's figures are optimistic by an amount this run cannot estimate. Confirming the pick needs data it was never "
         "chosen on.", "",
         f"Brief: Uzayr's prompt (received at or before 10 Oct 2026 15:25:40 SAST). Plan: `runs/identify/roomA/PLAN_RA.md` "
         f"(a83bc578, fd3e2ed9, committed before any score). Generated {now} by `ilr_report`. Models are named by what they "
         f"trained on, with the `xr_` name in brackets; S0 is the stopwatch (an LDA on the press speed, a speed the engine "
         f"does not have).", ""]
    # 1. the pick
    L += ["## 1. The pick", ""]
    ref = zd(S["pick"] if pick else S["winner"], S["v4"])
    refw = zd(S["pick"], S["winner"]) if pick else None
    if pick:
        L += [f"**{mixname(pick)}.** {mx['n_qualifiers']} of {mx['n_mixes']:,} configurations qualified (the guard, both core "
              f"Room A cells at least 25.00, Z at least 32.00, D at least 31.00); {mx['n_tied_within_0.25']} were within 0.25 of "
              f"the best qualifying score ({mx['top_score']:.2f}), and the pick is the one of those with the highest core "
              "Room A mean" + (" (all of them share the same core Room A mean, so the next tie-break, the higher (Z + D) / 2, "
              "decided)." if len({r['core_mean'] for r in mx['mixes'] if r['guard'] and r['xr_A_A3'] >= 25 and r['xr_ABtrk_A3'] >= 25
                                  and r['Z'] >= 32 and r['D'] >= 31 and r['score'] >= mx['top_score'] - 0.25 - 1e-9}) == 1 else "."), ""]
        if pick["base"] == win["base"]:
            diff = [k for k in ("w_A", "w_B", "w_unseen", "w_id") if pick[k] != 1.0]
            L += [f"**What the pick changes.** It is the build's winner with one change: {', '.join(f'{k} = {pick[k]}' for k in diff)}. "
                  + ("On the path walks of Room A, for a model that trained in Room A, the feature components are switched off and "
                     "the CNN components alone decide; every other walk is scored exactly as the winner scores it. " if diff == ["w_A"] and pick["w_A"] == 0.0 else "")
                  + f"Its core Room A cells ({pick['xr_A_A3']:.2f} and {pick['xr_ABtrk_A3']:.2f}) clear the 25.00 bar but stay below "
                  "the stopwatch's (S0, section 2).", ""]
    else:
        L += [f"**Nothing qualified** ({mx['n_mixes']:,} configurations; the rule needs the guard, both core Room A cells at "
              "least 25.00, Z at least 32.00 and D at least 31.00). The trade-off set is in section 5; **the run stops here "
              "for Uzayr's choice**, and the figures below are the build's winner's.", ""]
    L += ["| | v4 | the build's winner (chosen among 35 this morning) | " + (f"the pick (chosen among {lk['n_configurations']:,}) |" if pick else ""),
          "|---|---|---|" + ("---|" if pick else "")]
    v4f = R.figures(S["v4"], S["v4"])
    for k, nm in (("Z", "Z (zero-shot)"), ("D", "D (cross-day)"), ("score", "(Z + D) / 2"), ("xr_A_A3", "A1+A2 [xr_A] to A3 path"),
                  ("xr_ABtrk_A3", "A1+A2+B1 path walks [xr_ABtrk] to A3 path"), ("xr_ABtrk_B2", "A1+A2+B1 path walks [xr_ABtrk] to B2 path")):
        L.append(f"| {nm} | {v4f[k]:.2f} | {win[k]:.2f} | " + (f"{pick[k]:.2f} |" if pick else ""))
    L.append(f"| guard | holds | {'holds' if win['guard'] else 'FAILS'} | " + (("holds" if pick["guard"] else "FAILS") + " |" if pick else ""))
    L += ["", f"{who.capitalize()} minus v4: Z {ci(ref['Z'])}, D {ci(ref['D'])}, (Z + D) / 2 {ci(ref['score'])}."]
    if refw:
        L.append(f"The pick minus the build's winner: Z {ci(refw['Z'])}, D {ci(refw['D'])}, (Z + D) / 2 {ci(refw['score'])}.")
    L += ["", f"**The split check (report-only, the Mastermind's addition; how much of this is selection).** The same rule "
          f"run on one half of the scorecard's cells (A3's walks or B2's), its choice scored on the other half; bold marks "
          f"the half a choice was NOT made on, the honest estimate of what transfers. Every chosen row was chosen among "
          f"{lk['n_configurations']:,} configurations.", ""]
    L += split_table(S, sm, lk["n_configurations"])
    L += ["", "**What the split check cannot test.** w_A acts only on Room A's walks and w_B only on Room B's, so a choice made "
          "on the B2 half leaves w_A at its default (1.0, the tie order's weight closest to 1) and says nothing about it, and a "
          "choice made on the A3 half is in-sample for w_A. The B2 half's guard (loso_B2's own natural, slow and fast walks "
          "within 5 points of v4) fails for every one of the 1,500 mixes (loso_B2's fast walks), so its choice is the best "
          "score, labelled so. The one out-of-sample read on w_A is the Room A cells that belong to neither half: the A1 and "
          "A2 path walks of the other-four-sessions models [loso_A1, loso_A2] (part of D's pooled path cell, so in-sample for "
          "PLAN_RA's pick, but out-of-sample for the A3-half choice). Added after the mix step (report-only, not in PLAN_RA; no "
          "selection uses it):", ""]
    from pipeline.identify import ixr_eval as XE
    who_all = PC.bank()["a"]["anon"]
    keys = [("v4", "v4"), ("winner", "the winner")] + ([("pick", "PLAN_RA's pick")] if pick else []) + [
        ("split_A3", "chosen on the A3 half"), ("split_B2", "chosen on the B2 half")]
    L += ["| cell | walks | " + " | ".join(n for _k, n in keys) + " | A3-half choice minus the winner [95 %] |",
          "|---|---|" + "---|" * len(keys) + "---|"]
    for c in [("loso", "A1", "path"), ("loso", "A2", "path"), ("loso", "B1", "path")]:
        vals = [rows(c, S[k]) for k, _n in keys]
        w_ = who_all[vals[0][0]]
        L.append(f"| {label(c)} | {len(vals[0][0])} | " + " | ".join(f"{100 * v[1].mean():.2f}" for v in vals) + " | "
                 + ci(XE.paired(rows(c, S["split_A3"])[1], rows(c, S["winner"])[1], w_)) + " |")
    if pick:
        a1 = [100 * rows(("loso", "A1", "path"), S[k])[1].mean() for k in ("winner", "pick")]
        a2 = [100 * rows(("loso", "A2", "path"), S[k])[1].mean() for k in ("winner", "pick")]
        L += ["", "**On the Room A days outside A3, the pick's switch does not help:** against the winner it "
              + (f"leaves A1's held-out path walks at {a1[0]:.2f}" if a1[0] == a1[1] else f"moves A1's held-out path walks from {a1[0]:.2f} to {a1[1]:.2f}")
              + f" and moves A2's from {a2[0]:.2f} to {a2[1]:.2f}. Its Room A lift is seen on A3, the day it was chosen on."]
    L += [""]
    L.append(f"Exactness (before any mix was scored): every base at weight 1 reproduces this morning's ensembles; W and B "
             f"max abs diff {ex['bases'][R.BASES[0]]['max_abs_diff']} and {ex['bases'][R.BASES[1]]['max_abs_diff']}, same "
             f"decisions ({'PASSED' if ex['PASSED'] else 'FAILED'}).")
    L.append("")
    # 2. core model
    L += ["## 2. The core model (path walks only)", "", "Cross-day:", ""]
    L += cell_table([("xr_A", "A3", "path"), ("xr_ABtrk", "A3", "path"), ("xr_ABtrk", "B2", "path")], S)
    L += ["", "Zero-shot (A1+A2 never saw Room B):", ""]
    L += cell_table([("xr_A", "B2", k) for k in ("path", "natural", "slow", "fast")], S)
    # 3. B1's identification walks
    L += ["", "## 3. What B1's identification walks add", "",
          "A1+A2+B1 path walks + B1's identification walks [xr_AB] minus A1+A2+B1 path walks [xr_ABtrk], the same walks "
          "(paired participant bootstrap):", ""]
    from pipeline.identify import ixr_eval as XE
    who_all = PC.bank()["a"]["anon"]
    names = ["v4", "winner"] + (["pick"] if pick else [])
    L += ["| cell | walks | " + " | ".join(f"{n}: path only, plus id walks, difference [95 %]" for n in names) + " |",
          "|---|---|" + "---|" * len(names)]
    for s_, k in (("A3", "path"), ("B2", "path"), ("B2", "natural"), ("B2", "slow"), ("B2", "fast")):
        parts = []
        for n in names:
            ra, oka, _ = rows(("xr_AB", s_, k), S[n])
            rt, okt, _ = rows(("xr_ABtrk", s_, k), S[n])
            assert np.array_equal(ra, rt)
            parts.append(f"{100 * okt.mean():.2f}, {100 * oka.mean():.2f}, {ci(XE.paired(oka, okt, who_all[ra]))}")
        L.append(f"| {s_} {KIND[k]} | {len(ra)} | " + " | ".join(parts) + " |")
    # 4. identification walks
    L += ["", "## 4. Identification walks", "", "B1 (path and identification walks) [xr_B1]:", ""]
    L += cell_table([("xr_B1", "B2", k) for k in ("natural", "slow", "fast")] + [("xr_B1", "A3", "path")], S)
    L += ["", "The best case, the other four sessions [loso] (every session held out in turn):", ""]
    L += cell_table([("loso", "*", k) for k in ("natural", "slow", "fast")], S)
    L += ["", "Ranking on the 180 natural walks (the other four sessions [loso]); S0's ranking from the same LDA:", "",
          "| measure | v4 | the winner | " + ("the pick [95 %] | pick minus v4 [95 %] | " if pick else "") + "S0 |",
          "|---|---|---|" + ("---|---|" if pick else "") + "---|"]
    rp_, _o, lp_p = CO.cell_rows(("loso", "*", "natural"), S["pick"] if pick else S["winner"])
    w = who_all[rp_]
    rk = {n: CO.ranking(CO.cell_rows(("loso", "*", "natural"), S[n])[2], w) for n in names}
    rks = CO.ranking(B.s0_natural_lp(), w)
    for m_, nm in (("top2", "top-2"), ("group2", "household of two")):
        row = f"| {nm} | {100 * rk['v4'][m_].mean():.2f} | {100 * rk['winner'][m_].mean():.2f} | "
        if pick:
            row += f"{pct(rk['pick'][m_], w)} | {ci(XE.paired(rk['pick'][m_], rk['v4'][m_], w))} | "
        L.append(row + f"{100 * rks[m_].mean():.2f} |")
    # 5. trade-off set
    L += ["", "## 5. The trade-off set", ""]
    if pick:
        L.append(f"Not needed: {mx['n_qualifiers']} configurations qualified. For reference, the best qualifiers:")
        top = sorted([r for r in mx["mixes"] if r["guard"] and r["xr_A_A3"] >= 25 and r["xr_ABtrk_A3"] >= 25 and r["Z"] >= 32
                      and r["D"] >= 31], key=lambda r: -r["score"])[:10]
    else:
        L.append(f"Every configuration holding the guard that no other beats on all three of the core Room A mean, Z and D "
                 f"({len(mx['tradeoff'])} configurations):")
        top = mx["tradeoff"]
    L += ["", "| configuration | core Room A mean | A1+A2 to A3 | A1+A2+B1 path to A3 | Z | D | (Z + D) / 2 |",
          "|---|---|---|---|---|---|---|"]
    for r in top[:40]:
        L.append(f"| {mixname(r)} | {r['core_mean']:.2f} | {r['xr_A_A3']:.2f} | {r['xr_ABtrk_A3']:.2f} | {r['Z']:.2f} | "
                 f"{r['D']:.2f} | {r['score']:.2f} |")
    if len(top) > 40:
        L.append(f"| ({len(top) - 40} more in `runs/identify/roomA/mixes.json`) | | | | | | |")
    # 6. ship plan
    L += ["", "## 6. The engine v5 ship plan, updated for " + who + " (written, not built)", ""]
    toks = P["base"].split("+")
    L.append(f"**Engine v5 = v4 + {', '.join(toks)}** with the feature components weighted as below (the CNN weight 1); "
             "same CAL-causal pools and contract.")
    L.append("")
    for i, t in enumerate(toks, 1):
        L.append(f"{i}. **{BR.NAMES.get(t, t)}**: {BR.SHIP.get(t, '')}")
    if P["C1"]:
        L.append(f"{len(toks) + 1}. **Weights (C1, by walk type):** feature components {P['w_A']} on path walks, {P['w_id']} "
                 "on identification walks; no room setting.")
    else:
        if P["w_B"] == P["w_unseen"] and P["w_id"] == 1.0:
            L.append(f"{len(toks) + 1}. **Weights (C2, room-aware), in practice one switch:** in Room A, with a model that "
                     f"trained in Room A, the feature components weigh {P['w_A']} on path walks (the CNN components alone decide "
                     f"them); everywhere else (Room B, any new room, every identification walk) the weights are "
                     f"{P['w_B']}, as in the winner. **The room setting the app needs:** the installed room and whether the "
                     "shipped model's training sessions include it, set once per installation before any press (no label from "
                     "the test day). A new home always gets the unseen weight. The Room A weight was chosen on Room A's own "
                     "test day (A3); confirming it needs a new Room A day.")
        else:
            L.append(f"{len(toks) + 1}. **Weights (C2, room-aware):** feature components on path walks {P['w_A']} when the "
                     f"model has trained in the installed room and the room is Room A, {P['w_B']} likewise for Room B, "
                     f"{P['w_unseen']} when the model has never trained in the installed room; {P['w_id']} on identification "
                     "walks. **The room setting the app needs:** the installed room's identity and whether the shipped model's "
                     "training sessions include it (one setting per installation, fixed before any press; no label from the "
                     "test day). For a new home it is always the unseen weight.")
    L += ["", "**A4's timing:** three windows per press (0, 0.15 and 0.30 s after it), so the decision comes 0.30 s later "
          "and the CNN work per press triples; it is measured on the rig before adoption. Build order as the best-model "
          "report's section 7 (extractions, retraining, a version switch with v4 reproduced exactly when every change is "
          "off, every identification figure regenerated). Not built in this run.", ""]
    # 7. files, commits, timings
    L += ["## 7. Files, commits and timings", "",
          "- Code: `pipeline/identify/ilr_core.py`, `ilr_report.py` (importing `ilb_core`, `ilc_outer`, `ilp_cand`).",
          "- Plan and queue: `runs/identify/roomA/PLAN_RA.md`, `QUEUE_RA.md`, `STEPS_CPU1`, the driver `run_ra.sh`, `ms_ra.py`.",
          "- Results: `exact.json`, `mixes.json` (every configuration's Z, D, guard and core cells), `looks.json`, "
          "`summary.json`, `stores/` (the winner's, the pick's and the split choices' log-probabilities); `comps/<base>/` "
          "(every component, 21 MB, regenerable by `ilr_core components`) is not committed.", "",
          "Commits:", ""] + [f"- {c}" for c in git_log()]
    L += ["", "Timings (the driver's log):", ""]
    for l in open(os.path.join(R.RD, "logs", "run.log")):
        if re.search(r"BLOCK START|BLOCK END|START |END ", l) and "waits: free" not in l and "expect_" not in l:
            L.append("- " + l.strip()[:150])
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    t = write()
    open(OUT, "w").write(t)
    print(f"wrote {OUT} ({len(t)} characters)")
    sys.exit(0)
