"""F5: THE DONOR SWAP. Is the committed line read from the radio, or from the walk's timing?

Pre-registration: reports/tracking/history/2026-09-24_prereg-donor-swap.md, written before this file ran.

For every walk X on the nine cross-day pairings the shipped committed decision (A2 at 0.5 plus
a_veto_1.0, exactly as d4_headline takes it) is taken twice: on X's own radio, which must reproduce
d4_headline's rows_veto.json walk for walk or the run is VOID, and on a DONOR's. The donor Y is the
next participant's walk in the same test session, on a DIFFERENT line, closest in duration. Every
CSI-derived input X's decision reads becomes Y's: the pool emissions and the gate energy from X's first
window for Y's walk plus 4 s, and the pre-press start term. X keeps only its press time.

DIAGNOSTIC. Ships nothing, changes nothing.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("f5_donor", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

from pipeline.constrained.common import pairings, status, tag_of                  # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402

STAGE = "f5_donor"
FH = os.path.join(REPO_ROOT, "runs", "constrained", "fh")
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
MARGIN_W = 8          #: 4 s of the donor's own radio after its end press, so the exit sees its stop


def _who(stem: str) -> str:
    return stem.replace("participant_", "").split("_")[0]


def _pct(v):
    return 100.0 * float(np.mean(v)) if len(v) else None


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE, shipped_pieces
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.sb2_structural import press_ends
    from pipeline.constrained.veto import committed_start_terms
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    D.MAX_ADVANCE_M = None                 # the DECISION: no display ceiling, as d4_headline
    D2._LT_CACHE.clear()
    with open(os.path.join(FH, "d4_headline", "rows_veto.json"), encoding="utf-8") as f:
        ref = {r["key"]: r for r in json.load(f)}
    status(f"{STAGE} START: the donor swap over nine pairings, pre-registered")
    rows, fails, cache = [], [], {}
    for tr_s, te_s in pairings():
        if tr_s == te_s or len(te_s) != 1:
            continue
        tag = tag_of(tr_s, te_s, False)
        try:
            src, _i = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
            src = sorted(src, key=lambda s_: _who(s_[0]))
            o = shipped_opts(st, tr_s)
            o["entry"] = "soft"
            o["entry_window_m"] = 1.0
            terms = committed_start_terms(tr_s, te_s, st, cache)
            o["start_term"] = terms
            # 1. OWN: X's own radio, which must equal d4_headline walk for walk
            own = {}
            for stem, rec, ge, e in src:
                for r in night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, o, None):
                    own[(stem, int(r["pass_id"]))] = r
            # the walks of every recording, with their first window and their end-press window
            walks = {}
            for stem, rec, ge, e in src:
                t = np.asarray(rec.t0, float)
                ends = press_ends(rec.session, rec.stem)
                ws = sorted(((pid, r) for (s_, pid), r in own.items() if s_ == stem), key=lambda x: x[1]["lo"])
                walks[stem] = []
                for k, (pid, r) in enumerate(ws):
                    lo = int(r["lo"])
                    end_w = int(np.clip(np.searchsorted(t, float(ends[pid])), lo + 1, len(t) - 1))
                    nxt = int(ws[k + 1][1]["lo"]) if k + 1 < len(ws) else len(t)
                    walks[stem].append({"pid": pid, "lo": lo, "end_w": end_w, "next_lo": nxt,
                                        "true": r["true_line"], "dur": float(ends[pid]) - float(t[lo])})
            # 2. DONOR: the next participant's walk on a different line, closest in duration
            n = len(src)
            for i, (stem, rec, ge, e) in enumerate(src):
                d_stem, d_rec, d_ge, d_e = src[(i + 1) % n]
                e2, ge2 = np.array(e, copy=True), np.array(ge, copy=True)
                assert e2.shape[0] == len(rec) and ge2.shape[0] == len(rec), (e2.shape, ge2.shape, len(rec))
                o2 = dict(o)
                o2["start_term"] = dict(terms)
                plan = {}
                for X in walks[stem]:
                    cand = [Y for Y in walks[d_stem] if Y["true"] != X["true"]]
                    Y = min(cand, key=lambda Y_: (abs(Y_["dur"] - X["dur"]), Y_["pid"]))
                    want = (Y["end_w"] - Y["lo"] + 1) + min(MARGIN_W, Y["next_lo"] - Y["end_w"] - 1)
                    m = int(min(want, X["next_lo"] - X["lo"], len(d_rec) - Y["lo"]))
                    e2[X["lo"]:X["lo"] + m] = d_e[Y["lo"]:Y["lo"] + m]
                    ge2[X["lo"]:X["lo"] + m] = d_ge[Y["lo"]:Y["lo"] + m]
                    kx = f"{rec.session}|{rec.stem}|{X['pid']}"
                    ky = f"{d_rec.session}|{d_rec.stem}|{Y['pid']}"
                    if ky in terms:
                        o2["start_term"][kx] = terms[ky]
                    else:
                        o2["start_term"].pop(kx, None)
                    plan[X["pid"]] = {"Y": Y, "m": m,
                                      "truncated": bool(m < (Y["end_w"] - Y["lo"] + 1)),
                                      "donor_key": ky}
                for r in night_track(e2, rec, st, cfg, transit, ne, ge2, STRIDE, o2, None):
                    pid = int(r["pass_id"])
                    P = plan[pid]
                    ro = own[(stem, pid)]
                    key = f"{tag}|{rec.session}|{stem}|{pid}"
                    rows.append({
                        "key": key, "tag": tag, "who": _who(stem), "donor_who": _who(d_stem),
                        "donor_key": P["donor_key"], "true": ro["true_line"],
                        "donor_line": P["Y"]["true"],
                        "own_final": ro["final_line"], "donor_final": r["final_line"],
                        "own_correct": bool(ro["final_line"] == ro["true_line"]),
                        "follows_donor": bool(r["final_line"] == P["Y"]["true"]),
                        "stays_own": bool(r["final_line"] == ro["true_line"]),
                        "truncated": P["truncated"],
                        "exit_past_donor": bool(int(r["own_end_i"]) >= int(ro["lo"]) + P["m"]),
                        "reproduces_d4": bool(key in ref and ref[key]["final_line"] == ro["final_line"])})
            status(f"  {tag}: {sum(1 for r in rows if r['tag'] == tag)} walks")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            fails.append({"tag": tag, "error": repr(exc), "tb": traceback.format_exc()[-1500:]})
            status(f"  {tag}: FAILED {exc!r}")

    def summ(rs):
        return {"n": len(rs), "own_accuracy_pct": _pct([r["own_correct"] for r in rs]),
                "follows_donor_pct": _pct([r["follows_donor"] for r in rs]),
                "stays_own_pct": _pct([r["stays_own"] for r in rs]),
                "neither_pct": _pct([not (r["follows_donor"] or r["stays_own"]) for r in rs])}

    tags = sorted({r["tag"] for r in rows})
    whos = sorted({r["who"] for r in rows})
    rep = {"n": len(rows), "n_ref": len(ref), "equal": sum(r["reproduces_d4"] for r in rows)}
    rep["PASSED"] = bool(rep["n"] == 1080 and rep["equal"] == 1080)
    RES = {"stage": STAGE, "prereg": "reports/tracking/history/2026-09-24_prereg-donor-swap.md",
           "reproduction_own_vs_d4_rows_veto": rep,
           "POOLED": summ(rows),
           "per_pairing": {t: summ([r for r in rows if r["tag"] == t]) for t in tags},
           "session01_folds": {t: summ([r for r in rows if r["tag"] == t]) for t in tags if t.endswith("_to_s01")},
           "per_participant": {w: summ([r for r in rows if r["who"] == w]) for w in whos},
           "edge_as_donor_line": {ln: summ([r for r in rows if r["donor_line"] == ln]) for ln in EDGE},
           "edge_as_own_line": {ln: summ([r for r in rows if r["true"] == ln]) for ln in EDGE},
           "truncated_walks": sum(r["truncated"] for r in rows),
           "exit_past_donor_segment": sum(r["exit_past_donor"] for r in rows),
           "chance_pct": 100.0 / 12.0, "failures": fails,
           "minutes": round((time.time() - t0) / 60.0, 1)}
    RES["contract"] = check_contract(RES, ["POOLED", "per_pairing"])
    RES["VALID"] = bool(rep["PASSED"] and not fails)
    save(STAGE, RES)
    with open(os.path.join(FH, STAGE, "rows.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f)
    release(lock)
    P = RES["POOLED"]
    status(f"{STAGE} DONE: reproduction {rep['equal']}/{rep['n']}; own radio {P['own_accuracy_pct']:.1f}%, "
           f"donor's radio: follows donor {P['follows_donor_pct']:.1f}%, stays on own "
           f"{P['stays_own_pct']:.1f}% (chance 8.3%); VALID {RES['VALID']}")
    return 0 if RES["VALID"] else 1


if __name__ == "__main__":
    sys.exit(main())
