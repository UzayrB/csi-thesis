"""DC2, EXPLORATORY DISPLAY COMPARISON: the scorer lock at w = 0.25 against the display lock.

PREREG_DC2_crossroom section 13 (operator instruction 8), written before this file and before any Room B
data. **It affects no DC2 outcome and changes no model**: it is a separate command run AFTER the DC2
pipeline, reading that pipeline's own trees, calibration constants and reader, and writing its own report.
None of the files hashed in the DC2 model freeze (23h) is edited by it or for it.

    python3 -m pipeline.constrained.dc2_pipeline --room room_B      # first: the DC2 outcomes
    python3 -m pipeline.constrained.dc2_scorerlock --room room_B    # then this, exploratory

THE TWO LOCKS, per evaluated walk: the DISPLAY lock (DC2's frozen display component) and the SCORER LOCK
argmax of 0.75 x D + 0.25 x S (D: the display decode's per-line score at the lock's last window; S: the
final-answer scorer's line total with A2 + `a_veto_1.0` on the lock's own windows). Under configuration B
(primary) and A (beside it).

SUBSTITUTION, as defined in section 13 BEFORE any data: the scorer part recomputed with BOTH the partner's
walk emissions (the next recording in the session) AND the partner pass's start term (the reader's A2 +
veto from the partner pass's own pre-press radio, same pass id); D held.

PLUMBING CHECK (the stand-in, configuration A): both locks must equal Room A's `g2_scorerlock` rows on
every evaluated walk.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = 0.25
LAG_W, DELAY_S, DISPLAY_SD_SCALE, CAP = 2, 2.0, 4.5, 0.80
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")


def _inner(room: str, stand_in: bool) -> int:
    import dataclasses
    import numpy as np
    from pipeline.constrained.dc2_run import _bind, cfg_for
    c = cfg_for(room, stand_in)
    _bind(c)
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained import switching as SW
    from pipeline.constrained.dc2_pipeline import read_manifest, split_passes
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE, shipped_pieces
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.recordings import load_meta, recordings
    from pipeline.constrained.u1_adapt import session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W

    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    cfg_disp = dataclasses.replace(cfg, sd_scale=DISPLAY_SD_SCALE)
    scorer = SW.Scorer(st, cfg, transit)
    with open(os.path.join(c["base"], "decode.json"), encoding="utf-8") as f:
        dec = json.load(f)                                      # the DC2 pipeline's own constants
    man = read_manifest(os.path.join(c["data_view"], c["room"]))
    out = {"sessions": {}, "w": W}
    cache = {}
    for b in sorted(c["b_sessions"]):
        te = (b,)
        node = dec["sessions"][b]
        recs = [(s, stem) for s, stem in recordings() if s == b]
        evald = {stem: set(split_passes(load_meta(s, stem), (man.get("sessions") or {}).get(s) or {})
                           ["evaluated"]) for s, stem in recs}
        src = list(shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind, alpha)[0])
        a2 = start_terms(c["train"], te, st, A2_WEIGHT)
        Xtr, ytr, _k, _w, utr, _a = session_rows(c["train"], st, ADAPT_MODE, cache)
        Xte, _y, kte, _w2, ute, _a2 = session_rows(te, st, ADAPT_MODE, cache)
        _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)
        veto = merged(dict(a2), term_veto(kte, proba, classes, st, VETO_THR, VETO_W))
        ne_b = copy.deepcopy(ne)
        ne_b.motion_theta = float(node["theta_used"])
        ne_b.offset = float(node["null_used"])
        rows = {"A": [], "B": []}
        for cname, ne_x in (("A", ne), ("B", ne_b)):
            opts = shipped_opts(st, c["train"])
            opts["entry"] = "soft"
            opts["entry_window_m"] = 1.0
            opts["start_term"] = a2                              # the DISPLAY decode's start term
            for idx, (stem, rec, ge, e) in enumerate(src):
                D.MAX_ADVANCE_M = CAP
                D2._LT_CACHE.clear()
                rr = night_track(e, rec, st, cfg_disp, transit, ne_x, ge, STRIDE, opts, None,
                                 want_display=True, display_lags_w=(LAG_W,), display_to_horizon=True,
                                 display_lead_in_w=0, display_lock_scores=True)
                D.MAX_ADVANCE_M = None
                D2._LT_CACHE.clear()
                E = scorer.stack(e, ge, ne_x)                    # ne_x was calibrated on e by night_track
                p_stem, p_rec, _pg, p_e = src[(idx + 1) % len(src)]
                EA = scorer.stack(np.resize(p_e, e.shape), ge, ne_x)
                p_true = {int(q): n for q, n, _x, _y in p_rec.pass_spans()}
                for r in rr:
                    pid = int(r["pass_id"])
                    Lk = (r["display_locked"] or {}).get(f"{LAG_W}|{DELAY_S}")
                    if not Lk or pid not in evald.get(stem, set()):
                        continue
                    lo, hi = int(r["lo"]), int(Lk["lock_scores_last_window"])
                    Dsc = Lk["lock_scores"]
                    adj = veto.get(f"{b}|{stem}|{pid}") or {}
                    S, _e0 = scorer.totals_and_ends(E, lo, hi, scorer.start(E, lo))
                    S = {nm: v + float(adj.get(nm, 0.0)) for nm, v in S.items()}
                    adjP = veto.get(f"{b}|{p_stem}|{pid}") or {}   # the PARTNER pass's start term
                    SP, _eP = scorer.totals_and_ends(EA, lo, hi, scorer.start(EA, lo))
                    SP = {nm: v + float(adjP.get(nm, 0.0)) for nm, v in SP.items()}
                    arm = max(Dsc, key=lambda nm: (1 - W) * Dsc[nm] + W * S[nm])
                    sub = max(Dsc, key=lambda nm: (1 - W) * Dsc[nm] + W * SP[nm])
                    rows[cname].append({"key": f"{c['room']}|{b}|{stem}|{pid}", "stem": stem, "pass_id": pid,
                                        "true": r["true_line"], "display_lock": Lk["lock_line"],
                                        "scorer_lock": arm, "scorer_lock_substituted": sub,
                                        "partner_true": p_true.get(pid)})
        out["sessions"][b] = {"rows": rows, "null_used": node["null_used"], "theta_used": node["theta_used"]}
    with open(os.path.join(c["base"], "scorerlock.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    return 0


def summarise(rows):
    import numpy as np
    if not rows:
        return None
    d = np.array([float(r["scorer_lock"] == r["true"]) - float(r["display_lock"] == r["true"]) for r in rows])
    rng = np.random.default_rng(0)
    bs = [float(np.mean(d[rng.integers(0, len(d), len(d))])) for _ in range(1000)]
    diff = [r for r in rows if r["scorer_lock"] != r["display_lock"]]
    ch = float(np.mean([r["scorer_lock_substituted"] != r["scorer_lock"] for r in diff])) if diff else None
    ceil = float(np.mean([r["partner_true"] is not None and r["partner_true"] != r["true"] for r in rows]))
    edge = {ln: {"walks": sum(r["true"] == ln for r in rows),
                 "display_right": int(sum(r["display_lock"] == ln for r in rows if r["true"] == ln)),
                 "scorer_right": int(sum(r["scorer_lock"] == ln for r in rows if r["true"] == ln))}
            for ln in EDGE}
    ch_e = {ln: v["scorer_right"] - v["display_right"] for ln, v in edge.items()}
    return {"n": len(rows),
            "display_lock_pct": 100.0 * float(np.mean([r["display_lock"] == r["true"] for r in rows])),
            "scorer_lock_pct": 100.0 * float(np.mean([r["scorer_lock"] == r["true"] for r in rows])),
            "paired_points": 100.0 * float(np.mean(d)),
            "paired_ci95": [100.0 * float(np.percentile(bs, 2.5)), 100.0 * float(np.percentile(bs, 97.5))],
            "locks_changed": len(diff), "edge": edge, "edge_change": ch_e,
            "f_amended_reading": bool(sum(ch_e.values()) >= 0 and min(ch_e.values()) >= -2),
            "substitution": {"changed_share": ch, "ceiling_share": ceil,
                             "ratio": (ch / ceil if (ch is not None and ceil) else None),
                             "swaps": "walk emissions AND the partner pass's start term (section 13)"}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DC2 exploratory display comparison (PREREG_DC2 section 13)")
    ap.add_argument("--room", default="room_B")
    ap.add_argument("--stand-in", action="store_true")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.inner:
        return _inner(a.room, a.stand_in)
    from pipeline.constrained.dc2_run import _env, cfg_for
    c = cfg_for(a.room, a.stand_in)
    if not os.path.exists(os.path.join(c["base"], "decode.json")):
        raise SystemExit(f"REFUSING: run the DC2 pipeline first; no decode.json in {c['base']}")
    t0 = time.time()
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("TDR_") or k in ("TDR_LATTICE", "TDR_STANDIN_B1", "TDR_STANDIN_SUFFIX")}
    env.update(_env(c, c["tree"]("half")))
    env["OMP_NUM_THREADS"] = "1"
    cmd = [sys.executable, "-m", "pipeline.constrained.dc2_scorerlock", "--inner", "--room", a.room]
    code = subprocess.call(cmd + (["--stand-in"] if a.stand_in else []), cwd=REPO_ROOT, env=env)
    if code:
        raise SystemExit(f"the inner run failed with exit {code}")
    with open(os.path.join(c["base"], "scorerlock.json"), encoding="utf-8") as f:
        sl = json.load(f)
    R = {"room": a.room, "stand_in": a.stand_in, "EXPLORATORY": True, "affects_no_DC2_outcome": True,
         "prereg": "reports/PREREG_DC2_crossroom_2026-09-22.md, section 13", "w": W,
         "STAND_IN_WARNING": ("THESE NUMBERS ARE A PLUMBING CHECK AND ARE NOT RESULTS" if a.stand_in else None),
         "per_session": {b: {cn: summarise(v["rows"][cn]) for cn in ("A", "B")} for b, v in sl["sessions"].items()},
         "pooled": {cn: summarise(sum((v["rows"][cn] for v in sl["sessions"].values()), [])) for cn in ("A", "B")}}
    if a.stand_in:
        # PLUMBING: under configuration A, both locks equal Room A's g2_scorerlock rows, walk for walk
        g2p = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "g2_scorerlock", "rows.json")
        with open(g2p, encoding="utf-8") as f:
            g2 = {"|".join(r["key"].split("|")[2:]): r for r in json.load(f) if r["tag"] == "s0102_to_s03"}
        rowsA = sl["sessions"]["B1"]["rows"]["A"]
        pairs = [((r["display_lock"], r["scorer_lock"]),
                  (g2[f"{r['stem']}|{r['pass_id']}"]["w"]["0"]["lock"],
                   g2[f"{r['stem']}|{r['pass_id']}"]["w"]["0.25"]["lock"])) for r in rowsA]
        R["plumbing_vs_room_A_g2"] = {"n": len(pairs), "equal": int(sum(x == y for x, y in pairs)),
                                      "EXACT": bool(pairs and all(x == y for x, y in pairs))}
    R["minutes"] = round((time.time() - t0) / 60.0, 2)
    od = os.path.join(REPO_ROOT, "runs", "constrained", "fh",
                      "dc2_scorerlock_standin" if a.stand_in else f"dc2_scorerlock_{a.room}")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "results.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    P = R["pooled"]
    L = [f"# DC2 exploratory display comparison: the scorer lock against the display lock"
         f"{' (STAND-IN)' if a.stand_in else ''}", "",
         "**EXPLORATORY. It affects no DC2 outcome and changes no model** (PREREG_DC2 section 13).", ""]
    if a.stand_in:
        pl = R["plumbing_vs_room_A_g2"]
        L += ["> **EVERY NUMBER BELOW IS A PLUMBING CHECK, NOT A RESULT.**", "",
              f"**Plumbing, configuration A, both locks against Room A's `g2_scorerlock`:** "
              f"{'EXACT' if pl['EXACT'] else 'NOT EXACT'} ({pl['equal']} of {pl['n']}).", ""]
    L += ["| configuration | walks | display lock | scorer lock (w 0.25) | paired [95%] | locks changed | "
          "edge change E_col1 / E_col5 / E_row1 / E_row5 | substitution ratio (both swapped) |",
          "|---|---|---|---|---|---|---|---|"]
    for cn in ("B", "A"):
        s = P[cn]
        if s:
            L.append(f"| {cn}{' (primary)' if cn == 'B' else ''} | {s['n']} | {s['display_lock_pct']:.2f} | "
                     f"{s['scorer_lock_pct']:.2f} | {s['paired_points']:+.2f} [{s['paired_ci95'][0]:.2f}, "
                     f"{s['paired_ci95'][1]:.2f}] | {s['locks_changed']} | "
                     + " / ".join(f"{s['edge_change'][ln]:+d}" for ln in EDGE)
                     + f" | {s['substitution']['ratio']} |")
    rp = os.path.join(REPO_ROOT, "reports",
                      f"DC2_SCORERLOCK_{a.room}{'_STANDIN' if a.stand_in else ''}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {rp}\nwrote {os.path.join(od, 'results.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
