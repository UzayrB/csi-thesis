# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: PART 1, D1 to D4: diagnostics only.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated
assert_isolated("q1_diag", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import dataclasses
import time

import numpy as np

from pipeline.constrained.common import E_POST, pairings, status, tag_of
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save
from pipeline.constrained.g3_final import shipped_pool_emissions
from pipeline.constrained.night_arms import night_track
from pipeline.constrained.night_common import STRIDE, boot_ci, shipped_pieces
from pipeline.constrained.p1_runup import first_presses
from pipeline.constrained.paths import REVERSE_OF
from pipeline.constrained.r1_oldcensus import shipped_opts
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline

STAGE = "q1_diag"
DEMO_TAG, DEMO_TRAIN, DEMO_TEST = "s0102_to_s03", ("01", "02"), ("03",)
LAG_W = int(round(WINDOW_S / 2.0 / STRIDE))
REGIONS = {"S_mid": (2.5, 0.0), "N_mid": (2.5, 5.0), "W_mid": (0.0, 2.5), "E_mid": (5.0, 2.5),
           "SW": (0.0, 0.0), "NE": (5.0, 5.0), "NW": (0.0, 5.0), "SE": (5.0, 0.0)}
MID_CHAIN_M = 0.75


# Function region of.
def region_of(xy):
    xy = np.asarray(xy, float)
    return min(REGIONS, key=lambda k: float(np.linalg.norm(xy - np.asarray(REGIONS[k], float))))


# Function chain score.
def chain_score(e, st, rows, nm):
    a, b = st.slice_of[nm]
    v = np.asarray(e)[np.ix_(rows, np.arange(a, b))]
    m = np.max(v, axis=1)
    m = np.where(np.isfinite(m), m, 0.0)
    return float(np.sum(m + np.log(np.sum(np.exp(v - m[:, None]), axis=1) + 1e-300)))


# Function main.
def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    D.MAX_ADVANCE_M = 1.5
    D2._LT_CACHE.clear()
    cfg = dataclasses.replace(cfg, sd_scale=4.5)
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    status(f"{STAGE} START: D1 to D4, diagnostics only, strict lag_w {LAG_W}")

    xy_states = np.asarray(st.xy)
    starts = {nm: xy_states[st.slice_of[nm][0]] for nm in st.names}
    RES = {"stage": STAGE, "read_only": True, "strict_lag_w": LAG_W,
           "regions": {k: list(v) for k, v in REGIONS.items()},
           "line_start_region": {nm: region_of(starts[nm]) for nm in st.names},
           "per_pairing": {}, "failures": []}

    d2_counts = {"start_right_line_wrong": 0, "reversed": 0, "not_starting_there": 0,
                 "mid_chain_entry": 0, "start_right": 0, "n": 0}
    d2_examples = []
    d4 = {k: [] for k in ("k1", "k2", "k3", "k4", "middle", "full")}
    d3_pair = {p: [] for p in ("A", "B", "C", "D")}
    d3_link = {li: {"A": [], "B": []} for li in range(3)}

    for tr_s, te_s in pairings():
        if tr_s == te_s:
            continue
        tag = tag_of(tr_s, te_s, False)
        try:
            src, _i = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
            if src is None:
                continue
            o = shipped_opts(st, tr_s)
            o["entry"] = "soft"
            blocks = read_full_posteriors(posterior_path(tag, 25, E_POST, 0))
            dec_err, disp_err, line_ok, locked_ok = [], [], [], []
            for stem, rec, ge, e in src:
                blk = blocks.get(stem) or {}
                xh = np.asarray(blk.get("xy_hat")) if "xy_hat" in blk else None
                xhl = np.asarray(blk.get("xy_hat_link")) if "xy_hat_link" in blk else None
                t = np.asarray(rec.t0, float)
                txy = np.asarray(rec.xy, float)
                fp = first_presses(rec.session, rec.stem)
                rows = night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, o, None,
                                   want_display=True, display_lags_w=(LAG_W,),
                                   display_to_horizon=True)
                for r in rows:
                    nm, fin, lo = r["true_line"], r["final_line"], r["lo"]
                    line_ok.append(bool(r["found_final"]))
                    if r["err_m"] is not None:
                        dec_err.append(float(r["err_m"]))
                    press = fp.get(int(r["pass_id"]))
                    if press is None:
                        continue
                    end_w = t + WINDOW_S
                    legal = np.flatnonzero(end_w <= press + 1e-9)
                    legal = legal[legal < len(t)]
                    if not len(legal) or xh is None:
                        continue
                    w0 = int(legal[-1])
                    pred_reg = region_of(xh[w0])
                    true_reg = RES["line_start_region"][nm]
                    fin_reg = RES["line_start_region"].get(fin, "")
                    d2_counts["n"] += 1
                    right = bool(pred_reg == true_reg)
                    d2_counts["start_right"] += int(right)
                    if right and fin != nm:
                        d2_counts["start_right_line_wrong"] += 1
                        if fin == REVERSE_OF.get(nm):
                            d2_counts["reversed"] += 1
                            kindq = "reversed"
                        elif fin in st.slice_of:
                            a2, b2 = st.slice_of[fin]
                            dmin = float(np.min(np.linalg.norm(
                                xy_states[a2:b2] - starts[nm], axis=1)))
                            at_start = float(np.linalg.norm(starts[fin] - starts[nm]))
                            if dmin < MID_CHAIN_M < at_start:
                                d2_counts["mid_chain_entry"] += 1
                                kindq = "mid_chain_entry"
                            else:
                                d2_counts["not_starting_there"] += 1
                                kindq = "not_starting_there"
                        else:
                            kindq = "not_starting_there"
                        if len(d2_examples) < 40:
                            d2_examples.append({"tag": tag, "key": r["key"], "true": nm,
                                                "committed": fin, "kind": kindq,
                                                "start_region": true_reg})
                    rev = REVERSE_OF.get(nm)
                    if rev is not None:
                        hi = r["own_end_i"]
                        span = np.arange(lo, min(hi + 1, len(e)))
                        if len(span) >= 4:
                            for kk, lab in ((1, "k1"), (2, "k2"), (3, "k3"), (4, "k4")):
                                rr = span[:kk]
                                d4[lab].append(bool(chain_score(e, st, rr, nm)
                                                    >= chain_score(e, st, rr, rev)))
                            m0 = len(span) // 3
                            m1 = max(m0 + 1, 2 * len(span) // 3)
                            rr = span[m0:m1]
                            if len(rr):
                                d4["middle"].append(bool(chain_score(e, st, rr, nm)
                                                         >= chain_score(e, st, rr, rev)))
                            d4["full"].append(bool(chain_score(e, st, span, nm)
                                                   >= chain_score(e, st, span, rev)))
                        fam = nm.split("_")[0]
                        if fam in d3_pair:
                            d3_pair[fam].append(bool(fin == rev))
                        if xhl is not None and fam in ("A", "B") and len(legal):
                            k4 = np.arange(lo, min(lo + 4, len(t)))
                            for li in range(xhl.shape[0]):
                                p_ = np.nanmean(xhl[li][k4], axis=0)
                                if fam == "A":
                                    guess = "S_mid" if p_[1] < 2.5 else "N_mid"
                                else:
                                    guess = "W_mid" if p_[0] < 2.5 else "E_mid"
                                d3_link[li][fam].append(bool(guess == true_reg))
                    L = r["display_locked"].get(f"{LAG_W}|1.5")
                    if L is not None:
                        locked_ok.append(bool(L["lock_correct"]))
            RES["per_pairing"][tag] = {
                "line_pct": 100.0 * float(np.mean(line_ok)) if line_ok else None,
                "locked_line_pct_1.5s": 100.0 * float(np.mean(locked_ok)) if locked_ok else None,
                "decoded_error_m_median": float(np.median(dec_err)) if dec_err else None}
            status(f"  {tag:16s} line {RES['per_pairing'][tag]['line_pct']:5.1f}  locked "
                   f"{RES['per_pairing'][tag]['locked_line_pct_1.5s']:5.1f}  decoded err "
                   f"{RES['per_pairing'][tag]['decoded_error_m_median']:.3f} m")
        except Exception as exc:
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1000:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    P = RES["per_pairing"]
    RES["D1"] = {
        "semibounded_line_nine_pairings_pct": float(np.median(
            [v["line_pct"] for v in P.values() if v["line_pct"] is not None])),
        "semibounded_line_demo_pct": (P.get(DEMO_TAG) or {}).get("line_pct"),
        "locked_line_nine_pairings_pct": float(np.median(
            [v["locked_line_pct_1.5s"] for v in P.values()
             if v["locked_line_pct_1.5s"] is not None])),
        "locked_line_demo_pct": (P.get(DEMO_TAG) or {}).get("locked_line_pct_1.5s"),
        "decoded_error_m_nine": float(np.median(
            [v["decoded_error_m_median"] for v in P.values()
             if v["decoded_error_m_median"] is not None])),
        "decoded_error_m_demo": (P.get(DEMO_TAG) or {}).get("decoded_error_m_median"),
        "note": ("decoded accuracy compares the dot with where the person was at the window's own "
                 "centre; display offset compares it with where the person is at the frame time "
                 "and therefore carries the whole causal lag. They are different quantities and "
                 "are never added together.")}
    RES["D2"] = {**d2_counts, "examples_runs_only": d2_examples,
                 "start_right_pct": 100.0 * d2_counts["start_right"] / max(1, d2_counts["n"])}
    RES["D3"] = {
        "geometry": {"TX_to_RX1_path_from_both_ends_of_A_m": [6.0, 6.0],
                     "TX_to_RX2_path_m": [4.41, 9.41], "TX_to_RX3_path_m": [4.41, 9.41],
                     "hypothesis": ("the TX to RX1 link is symmetric about the midpoint of line A, "
                                    "so only RX2 and RX3 can separate its two ends")},
        "reversed_by_pair": {k: {"pct": 100.0 * float(np.mean(v)) if v else None,
                                 "ci95": boot_ci([100.0 * x for x in v])[-2:] if v else None,
                                 "n": len(v)} for k, v in d3_pair.items()},
        "per_link_start_end_accuracy": {
            f"link{li}": {fam: (100.0 * float(np.mean(v)) if v else None)
                          for fam, v in d.items()} for li, d in d3_link.items()}}
    RES["D4"] = {k: {"pct": 100.0 * float(np.mean(v)) if v else None, "n": len(v)}
                 for k, v in d4.items()}
    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["D1", "D2", "D3", "D4", "per_pairing"],
                                     {"per_pairing": 9})
    save(STAGE, RES)
    release(lock)

    d1, d2, d3, d4r = RES["D1"], RES["D2"], RES["D3"], RES["D4"]
    status(f"  D1 semi-bounded line: demo {d1['semibounded_line_demo_pct']:.1f}, nine "
           f"{d1['semibounded_line_nine_pairings_pct']:.1f}; locked at 1.5 s: demo "
           f"{d1['locked_line_demo_pct']:.1f}, nine {d1['locked_line_nine_pairings_pct']:.1f}")
    status(f"  D1 decoded error: demo {d1['decoded_error_m_demo']:.3f} m, nine "
           f"{d1['decoded_error_m_nine']:.3f} m")
    status(f"  D2 start region right on {d2['start_right_pct']:.1f}% of {d2['n']} passes; of "
           f"those, line wrong on {d2['start_right_line_wrong']}: reversed {d2['reversed']}, "
           f"not starting there {d2['not_starting_there']}, mid-chain {d2['mid_chain_entry']}")
    status(f"  D3 reversed by pair: " + ", ".join(
        f"{k} {v['pct']:.1f}%" for k, v in d3["reversed_by_pair"].items() if v["pct"] is not None))
    status(f"  D3 per-link start-end accuracy: {d3['per_link_start_end_accuracy']}")
    status(f"  D4 direction: " + ", ".join(f"{k} {v['pct']:.1f}%" for k, v in d4r.items()
                                           if v["pct"] is not None))
    headline(f"Q1 DIAGNOSTICS: start region right on {d2['start_right_pct']:.1f} percent of "
             f"passes; direction from the first window {d4r['k1']['pct']:.1f} percent against "
             f"{d4r['middle']['pct']:.1f} from the middle and {d4r['full']['pct']:.1f} from the "
             f"whole interval.")
    findings("q1", bool(RES["contract"]["SATISFIED"]), (
        f"D1, TWO ACCURACIES KEPT APART. {d1['note']}\n"
        f"  semi-bounded committed line: demo {d1['semibounded_line_demo_pct']:.1f} percent, nine "
        f"pairings {d1['semibounded_line_nine_pairings_pct']:.1f}\n"
        f"  locked display line at the 1.5 s wait: demo {d1['locked_line_demo_pct']:.1f}, nine "
        f"{d1['locked_line_nine_pairings_pct']:.1f}\n"
        f"  decoded error when right: demo {d1['decoded_error_m_demo']:.3f} m, nine "
        f"{d1['decoded_error_m_nine']:.3f} m\n\n"
        f"D2, START AGAINST COMMITMENT. The start region is right on {d2['start_right_pct']:.1f} "
        f"percent of {d2['n']} passes. On {d2['start_right_line_wrong']} of those the committed "
        f"line is still wrong: {d2['reversed']} same-line reversed, {d2['not_starting_there']} a "
        f"line that does not start there, {d2['mid_chain_entry']} entering another line "
        f"mid-chain.\n\n"
        f"D3, TX AGAINST RX1. Geometry: {d3['geometry']['hypothesis']}. Measured per-link "
        f"start-end accuracy: {d3['per_link_start_end_accuracy']}. Reversed error by pair: "
        f"{ {k: v['pct'] for k, v in d3['reversed_by_pair'].items()} }\n\n"
        f"D4, WHERE DIRECTION LIVES: " + ", ".join(
            f"{k} {v['pct']:.1f} percent" for k, v in d4r.items() if v["pct"] is not None)))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
