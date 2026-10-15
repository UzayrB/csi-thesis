"""pd_subst: the substitution test and the shuffled-radio control on the final model (VERIFY 1c).

For every evaluated pass X of a test session, the committed decision and the display lock are taken on
X's own radio, which must reproduce the cell's decode rows pass for pass or the run is VOID, and on a
DONOR's radio. Every radio-derived input X's decisions read becomes the donor's:
  - the pooled emissions and the relative gate energy, from 4 s before X's first walk window to the
    donor walk's last labelled window plus 4 s (capped at X's next pass and the recordings' ends);
  - both start terms, A2 and the veto, which read the windows around the press.
X keeps only its press times. The donor's radio carries its own recording's relative RSSI and gate
scale, as it was computed for the donor.

  substitution  the donor is the NEXT participant's recording (by name, cyclic), the SAME pass number:
                another person at the same point of the protocol, on whatever line they walked (the
                order is randomised per participant). The changed share is the decisions that differ
                from X's own; its CEILING is the share whose donor walked a different line, since a
                decision that follows the radio changes exactly then.
  shuffle       the donor is the next participant's walk on a DIFFERENT line, closest in duration
                (f5_donor's rule). Accuracy against X's own line should fall to chance (8.33 percent)
                or below; the share that follows the donor's line is reported beside it.

Each recording is decoded twice per scheme, its passes at even and at odd positions spliced
separately, and a spliced region never reaches back into the previous spliced one. The decoder reads at
most 6 windows before a walk's first (LIVE_SYSTEM_2026-09-25, gate 3), inside the 8 swapped.
DIAGNOSTIC: it chooses nothing and changes nothing.

    python3 -m pipeline.constrained.pd_subst --cell fin_A3 --variant V --ref CR.V --clean
    python3 -m pipeline.constrained.pd_subst --cell zsf_B2 --variant V --ref CR.V --clean
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "dc2_results", "verify", "subst")
PRE_W, MARGIN_W = 8, 8
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")


def _who(stem: str) -> str:
    return stem.replace("participant_", "").split("_")[0]


def _pct(v):
    return None if not len(v) else round(100.0 * float(np.mean(v)), 2)


def _ci(v, n_boot=1000, seed=0):
    v = np.asarray(v, float)
    if not len(v):
        return None
    rng = np.random.default_rng(seed)
    bs = [float(np.mean(v[rng.integers(0, len(v), len(v))])) for _ in range(n_boot)]
    return [round(100.0 * float(np.percentile(bs, 2.5)), 2), round(100.0 * float(np.percentile(bs, 97.5)), 2)]


def inner(cell: str, ref_variant: str, clean: bool, variant: str = "relgateU") -> int:
    t_start = time.time()
    from pipeline.constrained.pd_clean import _bound, apply_pace, force_cpu, plan_for, start_terms_for
    force_cpu()
    PC, c, tfs = _bound(cell)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    if clean:
        plan = plan_for(c, tfs)
        for s, p in plan.items():
            if p["changed"]:
                tmap[s] = p["clean"]
        os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
        assert all(tfs(s) == plan[s]["clean"] for s in plan), "the clean map did not take"
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained.dc2_pipeline import read_manifest, split_passes
    from pipeline.constrained.dc2_scorerlock import CAP, DELAY_S, DISPLAY_SD_SCALE, LAG_W
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE, shipped_pieces
    from pipeline.constrained.pd_decode import gate_reference, idle_idx
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.recordings import load_meta, recordings
    from pipeline.constrained.u1_adapt import session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader
    st, cfg0, ne0, transit, kind, alpha = shipped_pieces()
    pace = apply_pace()
    cfg_disp = dataclasses.replace(cfg0, sd_scale=DISPLAY_SD_SCALE)
    b = c["test"]
    te = (b,)
    man = read_manifest(J(c["data_view"], c["room"]))
    recs = [(s, stem) for s, stem in recordings() if s == b]
    splits = {f"{s}|{stem}": split_passes(load_meta(s, stem), (man.get("sessions") or {}).get(s) or {})
              for s, stem in recs}
    evald = {stem: set(splits[f"{s}|{stem}"]["evaluated"]) for s, stem in recs}
    # the start terms, exactly as pd_decode.inner builds them for the variant (configuration A)
    cache = {}
    Xtr, ytr, _k, _w, _u, _a = session_rows(c["train"], st, ADAPT_MODE, cache)
    Xte, _y, kte, _w2, _u2, _a2 = session_rows(te, st, ADAPT_MODE, cache)
    _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)
    a2, start = start_terms_for(variant, c, te, st, kte, proba, classes)
    # the emissions and the relative gate (relgateU)
    src = list(shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind, alpha, fusion_w=0.0)[0])
    G0 = gate_reference(c["train"], PC.cal_stems, room_a_only=True)
    S = {}
    for stem, rec, ge, e in src:
        ix = idle_idx(rec)
        g = float(np.median(np.asarray(ge)[ix])) if len(ix) else G0
        S[stem] = (rec, np.asarray(ge, float) * max(1.0, G0 / g), np.asarray(e, float))
    opts = shipped_opts(st, c["train"])
    opts["entry"], opts["entry_window_m"] = "soft", 1.0
    lopts = shipped_opts(st, c["train"])
    lopts["entry"], lopts["entry_window_m"] = "soft", 1.0

    def decode(stem, e, ge, st_c, st_l):
        rec = S[stem][0]
        D.MAX_ADVANCE_M = None
        D2._LT_CACHE.clear()
        com = {int(r["pass_id"]): r for r in night_track(e, rec, st, cfg0, transit, copy.deepcopy(ne0), ge, STRIDE,
                                                          dict(opts, start_term=st_c), None)}
        D.MAX_ADVANCE_M = CAP
        D2._LT_CACHE.clear()
        rr = night_track(e, rec, st, cfg_disp, transit, copy.deepcopy(ne0), ge, STRIDE, dict(lopts, start_term=st_l),
                         None, want_display=True, display_lags_w=(LAG_W,), display_to_horizon=True,
                         display_lead_in_w=0, display_lock_scores=True)
        D.MAX_ADVANCE_M = None
        D2._LT_CACHE.clear()
        lock = {}
        for r in rr:
            Lk = (r["display_locked"] or {}).get(f"{LAG_W}|{DELAY_S}")
            lock[int(r["pass_id"])] = Lk["lock_line"] if Lk else None
        return com, lock

    # 1. OWN radio: must equal the cell's record pass for pass
    own, W = {}, {}
    cal = PC.cal_stems(b)
    stems = sorted((s_ for s_ in S if s_ not in cal), key=_who)
    for stem in stems:
        rec, ge, e = S[stem]
        com, lock = decode(stem, e, ge, start, a2)
        own[stem] = (com, lock)
        order = sorted(com, key=lambda p: int(com[p]["lo"]))
        W[stem] = {}
        for k, pid in enumerate(order):
            lo = int(com[pid]["lo"])
            walk = np.flatnonzero((np.asarray(rec.pass_id) == pid) & (np.asarray(rec.mode).astype(str) == "walk"))
            W[stem][pid] = {"pid": pid, "pos": k, "lo": lo, "end_w": int(walk[-1]) if len(walk) else lo,
                            "next_lo": int(com[order[k + 1]]["lo"]) if k + 1 < len(order) else len(rec),
                            "true": com[pid]["true_line"]}
    ref_dir = J(c["base"], "d3", ref_variant)
    with open(J(ref_dir, "decode.json"), encoding="utf-8") as f:
        rc = {(r["stem"], int(r["pass_id"])): r["final_line"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    with open(J(ref_dir, "scorerlock.json"), encoding="utf-8") as f:
        rl = {(r["stem"], int(r["pass_id"])): r["display_lock"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    mc = {(s_, p): own[s_][0][p]["final_line"] for s_ in stems for p in own[s_][0] if p in evald.get(s_, set())}
    ml = {(s_, p): own[s_][1].get(p) for s_ in stems for p in own[s_][0] if p in evald.get(s_, set())}
    ml = {k: v for k, v in ml.items() if k in rl}
    repro = {"committed_equal": sum(mc.get(k) == v for k, v in rc.items()), "n_committed": len(rc),
             "lock_equal": sum(ml.get(k) == v for k, v in rl.items()), "n_lock": len(rl),
             "ref": os.path.relpath(ref_dir, REPO_ROOT)}
    repro["EXACT"] = repro["committed_equal"] == repro["n_committed"] and repro["lock_equal"] == repro["n_lock"]
    print(f"[{time.strftime('%H:%M:%S')}] {cell} own radio against {repro['ref']}: {repro}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    if not repro["EXACT"]:
        with open(J(OUT, f"{cell}.json"), "w", encoding="utf-8") as f:
            json.dump({"cell": cell, "VOID": True, "reproduction": repro}, f, indent=1)
        raise SystemExit(f"{cell}: VOID, the own-radio decode does not reproduce {repro['ref']}")

    # 2. donors
    def donor_plan(scheme: str) -> dict:
        plan = {}
        for i, sx in enumerate(stems):
            sy = stems[(i + 1) % len(stems)]
            for pid in sorted(evald.get(sx, set()) & set(W[sx])):
                X = W[sx][pid]
                if scheme == "substitution":
                    Y = W[sy].get(pid) or min(W[sy].values(), key=lambda y: (abs(y["pid"] - pid), y["pid"]))
                else:
                    cand = [y for y in W[sy].values() if y["true"] != X["true"]]
                    dur = X["end_w"] - X["lo"]
                    Y = min(cand, key=lambda y: (abs((y["end_w"] - y["lo"]) - dur), y["pid"]))
                plan.setdefault(sx, {})[pid] = (sy, Y["pid"])
        return plan

    def run(scheme: str) -> list:
        plan, rows = donor_plan(scheme), []
        for sx in stems:
            rec, ge, e = S[sx]
            items = sorted(plan.get(sx, {}).items(), key=lambda kv: W[sx][kv[0]]["pos"])
            for parity in (0, 1):
                part = [(p, v) for p, v in items if W[sx][p]["pos"] % 2 == parity]
                if not part:
                    continue
                e2, ge2, sc, sl, info, last_end = e.copy(), ge.copy(), dict(start), dict(a2), {}, 0
                for pX, (sy, pY) in part:
                    X, Y = W[sx][pX], W[sy][pY]
                    _ry, geY, eY = S[sy]
                    pre = int(max(0, min(PRE_W, X["lo"] - last_end, Y["lo"])))
                    want = (Y["end_w"] - Y["lo"] + 1) + MARGIN_W
                    m = int(min(want, X["next_lo"] - X["lo"], len(eY) - Y["lo"], len(e) - X["lo"]))
                    e2[X["lo"] - pre:X["lo"] + m] = eY[Y["lo"] - pre:Y["lo"] + m]
                    ge2[X["lo"] - pre:X["lo"] + m] = geY[Y["lo"] - pre:Y["lo"] + m]
                    last_end = X["lo"] + m
                    kx, ky = f"{b}|{sx}|{pX}", f"{b}|{sy}|{pY}"
                    for dst, srcd in ((sc, start), (sl, a2)):
                        if ky in srcd:
                            dst[kx] = srcd[ky]
                        else:
                            dst.pop(kx, None)
                    info[pX] = {"pre": pre, "m": m, "truncated": bool(m < Y["end_w"] - Y["lo"] + 1)}
                com, lock = decode(sx, e2, ge2, sc, sl)
                for pX, (sy, pY) in part:
                    X, Y = W[sx][pX], W[sy][pY]
                    oc, ol = own[sx][0][pX]["final_line"], own[sx][1].get(pX)
                    yc = own[sy][0][pY]["final_line"] if pY in own[sy][0] else None
                    yl = own[sy][1].get(pY)
                    rows.append({"key": f"{b}|{sx}|{pX}", "who": _who(sx), "donor": f"{b}|{sy}|{pY}",
                                 "true": X["true"], "donor_line": Y["true"],
                                 "own_committed": oc, "own_lock": ol, "donor_own_committed": yc, "donor_own_lock": yl,
                                 "committed": com[pX]["final_line"], "lock": lock.get(pX),
                                 "exit_past_donor": bool(int(com[pX].get("own_end_i", -1)) >= X["lo"] + info[pX]["m"]),
                                 **info[pX]})
        return rows

    def summ(rows, scheme):
        out = {"n": len(rows)}
        for what, o, dn in (("committed", "own_committed", "donor_own_committed"), ("lock", "own_lock", "donor_own_lock")):
            rs = [r for r in rows if r[what] is not None and r[o] is not None]
            chg = [r[what] != r[o] for r in rs]
            ceil = [r["donor_line"] != r["true"] for r in rs]
            out[what] = {
                "n": len(rs),
                "own_accuracy_pct": _pct([r[o] == r["true"] for r in rs]),
                "accuracy_on_donor_radio_pct": _pct([r[what] == r["true"] for r in rs]),
                "accuracy_on_donor_radio_ci95": _ci([r[what] == r["true"] for r in rs]),
                "changed_pct": _pct(chg), "ceiling_pct": _pct(ceil),
                "changed_over_ceiling": (round(float(np.mean(chg)) / float(np.mean(ceil)), 3) if rs and np.mean(ceil) else None),
                "changed_where_donor_line_differs_pct": _pct([r[what] != r[o] for r in rs if r["donor_line"] != r["true"]]),
                "changed_where_donor_line_same_pct": _pct([r[what] != r[o] for r in rs if r["donor_line"] == r["true"]]),
                "follows_donor_line_pct": _pct([r[what] == r["donor_line"] for r in rs]),
                "equals_donor_own_decision_pct": _pct([r[what] == r[dn] for r in rs if r[dn] is not None]),
                "edges_on_donor_radio": {ln: _pct([r[what] == r["true"] for r in rs if r["true"] == ln]) for ln in EDGE}}
        out["truncated_donor_walks"] = int(sum(r["truncated"] for r in rows))
        out["exit_past_donor_segment"] = int(sum(r["exit_past_donor"] for r in rows))
        out["short_pre_press_swaps"] = int(sum(r["pre"] < PRE_W for r in rows))
        out["chance_pct"] = round(100.0 / 12.0, 2)
        return out

    res = {"cell": cell, "test": b, "train": list(c["train"]), "variant": variant, "pace": pace, "clean_readers": clean, "tag_map": tmap,
           "reproduction": repro, "stems": stems, "pre_w": PRE_W, "margin_w": MARGIN_W,
           "at": time.strftime("%Y-%m-%d %H:%M:%S"), "device": "cpu (forced)"}
    for scheme in ("substitution", "shuffle"):
        rows = run(scheme)
        res[scheme] = summ(rows, scheme)
        with open(J(OUT, f"{cell}_{scheme}_rows.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
        s_ = res[scheme]
        print(f"[{time.strftime('%H:%M:%S')}] {cell} {scheme}: committed {s_['committed']}, lock {s_['lock']}", flush=True)
    res["minutes"] = round((time.time() - t_start) / 60.0, 1)
    with open(J(OUT, f"{cell}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--ref", default="relgateU", help="the d3 folder the own-radio rows must reproduce")
    ap.add_argument("--clean", action="store_true", help="the corrected readers (pd_clean's map)")
    ap.add_argument("--variant", default="relgateU", help="the decode variant (pd_clean.variant_spec)")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return inner(a.cell, a.ref, a.clean, a.variant)
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(a.cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_subst", "--inner", "--cell", a.cell,
                            "--ref", a.ref, "--variant", a.variant] + (["--clean"] if a.clean else []), cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
