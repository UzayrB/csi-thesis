# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Pd_decode: D3 of the tracking attack: decoder and decision variants on a finished cell's networks, with no...

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


# Function parse.
def parse(name: str) -> dict:
    v = {"w": 0.0, "cnull": False, "relgate": False, "abstain": False, "pace": False,
         "offset": None, "margin": None, "a2w": None, "sd": None, "onhead": None, "g100n": False,
         "interp": False, "cfgB": None, "lw": None, "relgate_a": False, "relgate_up": False}
    if name == "ref":
        return v
    for part in name.split("+"):
        if part in ("cnull", "relgate", "abstain", "pace", "g100n", "interp"):
            v[part] = True
        elif part == "relgateA":
            v["relgate"], v["relgate_a"] = True, True
        elif part == "relgateU":
            v["relgate"], v["relgate_a"], v["relgate_up"] = True, True, True
        elif part in ("cfgB", "cfgBc", "cfgBn"):
            v["cfgB"] = part
        elif part.startswith("onhead"):
            v["onhead"], v["cnull"] = float(part[6:] or 1.0), True
        elif part.startswith("margin"):
            v["margin"] = float(part[6:])
        elif part.startswith("off"):
            v["offset"] = float(part[3:])
        elif part.startswith("a2w"):
            v["a2w"] = float(part[3:])
        elif part.startswith("sd"):
            v["sd"] = float(part[2:])
        elif part.startswith("lw"):
            v["lw"] = float(part[2:])
        elif part.startswith("w"):
            v["w"] = float(part[1:])
        else:
            raise SystemExit(f"unknown variant part {part!r}")
    return v


# Np.quantile (linear) of x[:t+1] for every t: the reference a live system has at window t.
def running_quantile(x: np.ndarray, q: float) -> np.ndarray:
    import bisect
    out, srt = np.empty(len(x)), []
    for t, v in enumerate(np.asarray(x, float)):
        bisect.insort(srt, float(v))
        pos = q * (len(srt) - 1)
        lo = int(np.floor(pos))
        hi = min(lo + 1, len(srt) - 1)
        out[t] = srt[lo] + (pos - lo) * (srt[hi] - srt[lo])
    return out


# The shipped AdaptiveNullEmission with its reference made causal (a per-window array).
def make_causal(ne):
    from pipeline.constrained.emissions import AdaptiveNullEmission

    # Class Causal Null Emission.
    class CausalNullEmission(AdaptiveNullEmission):
        # Function calibrate.
        def calibrate(self, path_emission):
            self._ref = running_quantile(np.asarray(path_emission).max(1), self.quantile)
            return self

        # Function to dict.
        def to_dict(self):
            d = super().to_dict()
            d["kind"], d["reference_of_last_recording"] = "causal", None
            return d
    out = CausalNullEmission(ne.quantile, ne.offset, ne.gate_weight, ne.motion_theta)
    return out


# The causal null with the on-a-line head's log-odds against 'on a line' added per window.
def make_onhead(ne, beta: float, p_on: np.ndarray):
    base = make_causal(ne)
    lo = -float(beta) * np.log(np.clip(p_on, 1e-4, 1 - 1e-4) / np.clip(1 - p_on, 1e-4, 1.0))
    cls = type(base)

    # Class On Head Null.
    class OnHeadNull(cls):
        # Calls the object.
        def __call__(self, gate_energy):
            out = super().__call__(gate_energy)
            n = min(len(out), len(lo))
            out = np.array(out, float)
            out[:n] = out[:n] + lo[:n]
            return out
    o = OnHeadNull(ne.quantile, ne.offset, ne.gate_weight, ne.motion_theta)
    return o


# (n, 3 x 64): each link's pooled embedding of every window of one recording, chunked.
def embeddings(c, session, stem, models, stats) -> np.ndarray:
    import torch
    from pipeline.constrained.nets import device, stack_link
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi
    rec = load_meta(session, stem)
    R = np.asarray(load_rssi(session, stem, rec.t0_epoch), np.float32)
    dev = device()
    out = []
    for i0 in range(0, len(rec), 256):
        idx = np.arange(i0, min(len(rec), i0 + 256))
        X = np.array(load_features(session, stem, idx), dtype=np.float32)
        Rb = R[idx].copy()
        if stats is not None:
            st = stats[f"{session}|{stem}"]
            for li in range(3):
                if "x" in st:
                    X[:, li] = (X[:, li] - st["x"][li][0]) / st["x"][li][1]
                Rb[:, li] = (Rb[:, li] - st["r"][li][0]) / (st["r"][li][1] if "x" in st else 1.0)
        Z = []
        for li, (m, mu, sd) in enumerate(models):
            xl = (stack_link(X[:, [li]], Rb[:, [li]]) - mu) / sd
            m = m.to(dev).eval()
            with torch.no_grad():
                Z.append(m.embed(torch.from_numpy(xl.astype(np.float32)).to(dev)).cpu().numpy())
        out.append(np.concatenate(Z, axis=1))
    return np.concatenate(out)


# Fit on the training sessions; return ({test stem: p_on per window}, info).
def on_line_head(c, cal_stems, test_stems) -> tuple:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from pipeline.constrained.artefacts import _load
    from pipeline.constrained.recordings import load_meta, session_recordings
    from pipeline.constrained import pd_cells as PC
    tag, tree = c["heads_tag"], c["tree"]("half")
    models = [_load(J(tree, "models", f"{tag}_g25_e24_s0_link{li}.pt")) for li in range(3)]
    stats = None
    if c["norm"] == "per_recording" or c["opts"].get("rrel"):
        with open(PC.PRN_STATS, encoding="utf-8") as f:
            raw = json.load(f)["recordings"]
        stats = raw if c["norm"] == "per_recording" else {k: {"r": v["r"]} for k, v in raw.items()}
    Xs, ys = [], []
    for s in c["train"]:
        for _s, stem in session_recordings(s):
            if stem in cal_stems(s):
                continue
            mode = np.asarray(load_meta(s, stem).mode).astype(str)
            keep = np.flatnonzero(np.isin(mode, ["walk", "idle", "walk_edge"]))
            Z = embeddings(c, s, stem, models, stats)[keep]
            Xs.append(Z)
            ys.append((mode[keep] == "walk").astype(int))
    X, y = np.concatenate(Xs), np.concatenate(ys)
    sc = StandardScaler().fit(X)
    clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced").fit(sc.transform(X), y)
    acc_tr = float((clf.predict(sc.transform(X)) == y).mean())
    out = {}
    for stem in test_stems:
        Z = embeddings(c, c["test"], stem, models, stats)
        out[stem] = clf.predict_proba(sc.transform(Z))[:, 1]
    return out, {"n_train": int(len(y)), "walk_share": float(y.mean()), "train_accuracy": acc_tr}


# D5: log of the scaled posterior interpolated bilinearly (in probability) at each state's xy.
def interp_scaled_emission(prob, state_xy, n_cells, marginal, alpha=1.0):
    from pipeline.constrained.grid import ROOM_M, grid_n
    n = grid_n(n_cells)
    step = ROOM_M / n
    q = np.asarray(prob, float) / (np.asarray(marginal, float)[None, :] ** float(alpha))
    q = q.reshape(len(q), n, n)
    xy = np.asarray(state_xy, float)
    gx, gy = xy[:, 0] / step - 0.5, xy[:, 1] / step - 0.5
    i0 = np.clip(np.floor(gx).astype(int), 0, n - 2)
    j0 = np.clip(np.floor(gy).astype(int), 0, n - 2)
    fx, fy = np.clip(gx - i0, 0.0, 1.0), np.clip(gy - j0, 0.0, 1.0)
    v = ((1 - fx) * (1 - fy))[None] * q[:, j0, i0] + (fx * (1 - fy))[None] * q[:, j0, i0 + 1] + \
        ((1 - fx) * fy)[None] * q[:, j0 + 1, i0] + (fx * fy)[None] * q[:, j0 + 1, i0 + 1]
    return np.log(np.maximum(v, 1e-300))


# Context: swap the emission builders the shipped pool calls at call time; restored on exit.
def patched_emissions(g100n: bool, interp: bool):
    import contextlib
    import pipeline.constrained.emissions as EM
    import pipeline.constrained.g3_final as G3

    # Function ctx.
    @contextlib.contextmanager
    def ctx():
        o_sc, o_g100 = EM.scaled_cell_emission, G3.g100_emissions
        try:
            if interp:
                EM.scaled_cell_emission = interp_scaled_emission
            if g100n:
                # Function g100 native.
                def g100_native(tag, tr_s, te_s, within, st, kind, alpha, fusion_w=0.0):
                    from pipeline.constrained.artefacts import read_full_posteriors
                    from pipeline.constrained.dataset import sides
                    from pipeline.constrained.fusion import fused_prob
                    p = os.path.join(REPO_ROOT, G3.G100_TREE, "posteriors", f"{tag}_g100_e{G3.E_POST}_s0_full.npz")
                    if not os.path.exists(p):
                        return None
                    marg = EM.cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 100)
                    return {stem: EM.scaled_cell_emission(fused_prob(b, fusion_w).astype(float), st.xy, 100,
                                                          marg, alpha=alpha)
                            for stem, b in read_full_posteriors(p).items()}
                G3.g100_emissions = g100_native
            yield
        finally:
            EM.scaled_cell_emission, G3.g100_emissions = o_sc, o_g100
    return ctx()


# The DRAWN dot's error on every labelled walk window of one pass: the free fixed-lag path before the lock...
def drawn_errors(r, Lk, rec, st) -> dict:
    free = (r.get("display_paths") or {}).get(str(Lk.get("_lag", 2))) or []
    path, ls, lo_d = Lk["path"], int(Lk["lock_step"]), int(Lk["lo_disp"])
    sxy = np.asarray(st.xy, float)
    a, b = st.slice_of[r["true_line"]]
    u = sxy[b - 1] - sxy[a]
    u = u / max(np.linalg.norm(u), 1e-9)
    xy_true = np.asarray(rec.xy, float)
    err, along, across, same = [], [], [], []
    for w in range(int(r["lo"]), int(r["hi_true"]) + 1):
        i = w - lo_d
        src = free if i < ls else path
        if not (0 <= i < len(src)) or not np.isfinite(xy_true[w]).all():
            continue
        k = int(src[i]["state"])
        if k < 0 or k >= len(sxy):
            continue
        d = sxy[k] - xy_true[w]
        err.append(round(float(np.linalg.norm(d)), 4))
        along.append(round(float(abs(d @ u)), 4))
        across.append(round(float(abs(d[0] * u[1] - d[1] * u[0])), 4))
        same.append(bool(src[i]["line"] == r["true_line"]))
    return {"err": err, "along": along, "across": across, "on_true_line": same}


# Configuration B's constants for the test session from its calibration walks (see cfgB*).
def config_b(c, kind_b, src, splits, w, room) -> dict:
    from pipeline.constrained import dc2_run as R
    from pipeline.constrained.dc2_pipeline import calibration_numbers, re_anchored_constants
    from pipeline.constrained.recordings import gate_energy
    b = c["test"]
    if not any(v["calibration"] for k, v in splits.items() if k.startswith(f"{b}|")):
        return {"available": False}
    assert float(w) in R.S_A_BY_W, f"no S_A frozen at fusion w {w}"
    calw = []
    for stem, rec, ge, e in src:
        sp = splits.get(f"{b}|{stem}") or {}
        m = np.isin(np.asarray(rec.pass_id), list(sp.get("calibration", []))) & (np.asarray(rec.mode) == "walk")
        if m.any():
            calw.append(R.emission_spread(e, m))
    s_b = float(np.median([x for x in calw if x is not None]))
    null_rel = R.NULL_ABS * s_b / R.S_A_BY_W[float(w)]
    null_b = null_rel if abs(null_rel - R.NULL_ABS) <= R.NULL_GUARD_NATS else R.NULL_ABS
    out = {"available": True, "s_B": s_b, "s_A": R.S_A_BY_W[float(w)], "null_relative": null_rel,
           "null_used": null_b, "null_scale": null_b / R.NULL_ABS}
    if kind_b == "cfgBn":
        return out
    cal = calibration_numbers(room, [b], splits)
    if kind_b == "cfgBc":
        still = []
        for stem, rec, ge, e in src:
            sp = splits.get(f"{b}|{stem}") or {}
            if sp.get("calibration"):
                ix = idle_idx(rec)
                still += list(np.asarray(gate_energy(b, stem), float)[ix])
        node = cal["per_session"][b]["band_energy_idle_or_standing"]
        node.update({"p50": float(np.median(still)), "n": len(still), "causal": True})
    consts = re_anchored_constants(cal)
    out["theta_used"] = float(consts[b]["theta"])
    out["gate_constants"] = consts[b]
    return out


# Function spread.
def spread(e, idx) -> float:
    e = np.asarray(e, float)[idx]
    return float(np.median(e.max(axis=1) - np.median(e, axis=1)))


# Function idle idx.
def idle_idx(rec) -> np.ndarray:
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.u1_adapt import calibration_indices
    return np.asarray(calibration_indices(rec, first_presses(rec.session, rec.stem)), int)


# Mean and between-pass spread of walking speed (m/s) over the training sessions' passes.
def fit_pace(train, cal_stems) -> dict:
    from pipeline.constrained.recordings import load_meta, session_recordings
    from pipeline.constrained.rebuild_common import WINDOW_S
    v = []
    for s in train:
        for _s, stem in session_recordings(s):
            if stem in cal_stems(s):
                continue
            rec = load_meta(s, stem)
            t = np.asarray(rec.t0, float) + WINDOW_S / 2.0
            xy = np.asarray(rec.xy, float)
            for pid, _nm, _a, _b in rec.pass_spans():
                w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk") & np.isfinite(xy).all(1))
                if len(w) < 3 or t[w[-1]] <= t[w[0]]:
                    continue
                arc = float(np.sum(np.linalg.norm(np.diff(xy[w], axis=0), axis=1)))
                v.append(arc / float(t[w[-1]] - t[w[0]]))
    v = np.asarray(v)
    return {"v_mean": float(v.mean()), "v_sd": float(v.std(ddof=1)), "n_passes": int(len(v))}


# G0: the median over the training recordings of each recording's median idle gate energy.
def gate_reference(train, cal_stems, room_a_only: bool = False) -> float:
    from pipeline.constrained.recordings import gate_energy, load_meta, session_recordings
    meds = []
    for s in train:
        if room_a_only and s.startswith("B"):
            continue
        for _s, stem in session_recordings(s):
            if stem in cal_stems(s):
                continue
            rec = load_meta(s, stem)
            ix = idle_idx(rec)
            if len(ix):
                meds.append(float(np.median(gate_energy(s, stem)[ix])))
    return float(np.median(meds))


# Function inner.
def inner(cell: str, names: list) -> int:
    from pipeline.constrained import dc2b
    dc2b.install()
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    from pipeline.constrained import dc2_run as R
    R._bind(c)
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
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_abstain, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
    from pipeline.constrained.dc2_scorerlock import CAP, DELAY_S, DISPLAY_SD_SCALE, LAG_W, W
    st, cfg0, ne0, transit, kind, alpha = shipped_pieces()
    V0 = (D.V_MEAN, D.V_SD, D2.V_MEAN)
    b = c["test"]
    te = (b,)
    man = read_manifest(J(c["data_view"], c["room"]))
    recs = [(s, stem) for s, stem in recordings() if s == b]
    splits = {f"{s}|{stem}": split_passes(load_meta(s, stem), (man.get("sessions") or {}).get(s) or {})
              for s, stem in recs}
    evald = {stem: set(splits[f"{s}|{stem}"]["evaluated"]) for s, stem in recs}
    cache, a2c, src_c = {}, {}, {}
    Xtr, ytr, _k, _w, _u, _a = session_rows(c["train"], st, ADAPT_MODE, cache)
    Xte, _y, kte, _w2, _u2, _a2 = session_rows(te, st, ADAPT_MODE, cache)
    _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)

    # Function a2 of.
    def a2_of(wt):
        if wt not in a2c:
            a2c[wt] = start_terms(c["train"], te, st, wt)
        return a2c[wt]

    # Function src of.
    def src_of(w, g100n=False, interp=False):
        key = (w, g100n, interp)
        if key not in src_c:
            with patched_emissions(g100n, interp):
                src_c[key] = list(shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind, alpha,
                                                         fusion_w=w)[0])
        return src_c[key]

    G0, pace, onp, G0c = None, None, None, {}
    for name in names:
        t0 = time.time()
        v = parse(name)
        out_dir = J(c["base"], "d3", name)
        os.makedirs(out_dir, exist_ok=True)
        info = {"variant": name, "parsed": v, "cell": cell, "heads_tag": c["heads_tag"], "train": list(c["train"])}
        cfg = cfg0 if v["margin"] is None else dataclasses.replace(cfg0, margin=v["margin"])
        cfg_disp = dataclasses.replace(cfg, sd_scale=v["sd"] if v["sd"] is not None else DISPLAY_SD_SCALE)
        if v["pace"]:
            if pace is None:
                pace = fit_pace(c["train"], PC.cal_stems)
            D.V_MEAN, D.V_SD = pace["v_mean"], pace["v_sd"]
            D2.V_MEAN = pace["v_mean"]
            info["pace"] = pace
        else:
            D.V_MEAN, D.V_SD, D2.V_MEAN = V0
        D2._LT_CACHE.clear()
        a2 = a2_of(v["a2w"] if v["a2w"] is not None else A2_WEIGHT)
        if v["abstain"]:
            term, _cov = term_abstain(kte, proba, classes, st, R.ABSTAIN_THR, R.ABSTAIN_W)
        else:
            term = term_veto(kte, proba, classes, st, VETO_THR, VETO_W)
        start = merged(dict(a2), term)
        base_off = float(v["offset"]) if v["offset"] is not None else float(ne0.offset)
        if v["onhead"] is not None and onp is None:
            onp, oninfo = on_line_head(c, PC.cal_stems, [s_ for s_, *_r in src_of(0.0)])
            info["on_head"] = oninfo
        if v["relgate"] and v["cfgB"] not in ("cfgB", "cfgBc"):
            key = "A" if v["relgate_a"] else "all"
            if key not in G0c:
                G0c[key] = gate_reference(c["train"], PC.cal_stems, room_a_only=v["relgate_a"])
            G0 = G0c[key]

        # Function prep.
        def prep(w_x, tag):
            src_x = src_of(w_x, v["g100n"], v["interp"])
            if v["relgate"] and v["cfgB"] in ("cfgB", "cfgBc"):
                info["relgate_replaced_by"] = v["cfgB"]
            elif v["relgate"]:
                info["gate_reference_G0"] = G0
                scaled = []
                for stem, rec, ge, e in src_x:
                    ix = idle_idx(rec)
                    g = float(np.median(np.asarray(ge)[ix])) if len(ix) else G0
                    sc = max(1.0, G0 / g) if v["relgate_up"] else G0 / g
                    scaled.append((stem, rec, np.asarray(ge, float) * sc, e))
                    info.setdefault("gate_scale", {})[stem] = sc
                src_x = scaled
            cb = None
            if v["cfgB"]:
                cb = config_b(c, v["cfgB"], src_x, splits, w_x, c["room"])
                info[f"config_b{tag}"] = cb
                if not cb["available"]:
                    cb = None
            ne_x = {}
            for stem, rec, ge, e in src_x:
                if v["onhead"] is not None:
                    ne = make_onhead(ne0, v["onhead"], onp[stem])
                elif v["cnull"]:
                    ne = make_causal(ne0)
                else:
                    ne = copy.deepcopy(ne0)
                if cb is not None:
                    ne.offset = base_off * cb["null_scale"]
                    if "theta_used" in cb:
                        ne.motion_theta = cb["theta_used"]
                    ne_x[stem] = ne
                    continue
                k = 1.0
                if w_x:
                    ix = idle_idx(rec)
                    e0 = dict((s_, e_) for s_, _r, _g, e_ in src_of(0.0, v["g100n"], v["interp"]))[stem]
                    k = spread(e, ix) / spread(e0, ix) if len(ix) else 1.0
                    info.setdefault(f"offset_scale{tag}", {})[stem] = k
                ne.offset = base_off * k
                ne_x[stem] = ne
            return src_x, ne_x
        src, ne_of = prep(v["w"], "")
        src_l, ne_l = (src, ne_of) if v["lw"] is None else prep(v["lw"], "_lock")
        opts = shipped_opts(st, c["train"])
        opts["entry"], opts["entry_window_m"], opts["start_term"] = "soft", 1.0, start
        D.MAX_ADVANCE_M = None
        D2._LT_CACHE.clear()
        crow = []
        for stem, rec, ge, e in src:
            for r in night_track(e, rec, st, cfg, transit, ne_of[stem], ge, STRIDE, opts, None):
                sess, stm, pid = r["key"].split("|")
                if int(pid) not in evald.get(stm, set()):
                    continue
                crow.append({"key": f"{c['room']}|{r['key']}", "stem": stm, "pass_id": int(pid),
                             "true": r["true_line"], "final_line": r["final_line"],
                             "correct": bool(r["final_line"] == r["true_line"]), "err_m": r.get("err_m")})
        scorer = SW.Scorer(st, cfg, transit)
        lopts = shipped_opts(st, c["train"])
        lopts["entry"], lopts["entry_window_m"], lopts["start_term"] = "soft", 1.0, a2
        lrow = []
        for stem, rec, ge, e in src_l:
            ne = ne_l[stem]
            D.MAX_ADVANCE_M = CAP
            D2._LT_CACHE.clear()
            rr = night_track(e, rec, st, cfg_disp, transit, ne, ge, STRIDE, lopts, None,
                             want_display=True, display_lags_w=(LAG_W,), display_to_horizon=True,
                             display_lead_in_w=0, display_lock_scores=True)
            D.MAX_ADVANCE_M = None
            D2._LT_CACHE.clear()
            E = scorer.stack(e, ge, ne)
            for r in rr:
                pid = int(r["pass_id"])
                Lk = (r["display_locked"] or {}).get(f"{LAG_W}|{DELAY_S}")
                if not Lk or pid not in evald.get(stem, set()):
                    continue
                lo, hi = int(r["lo"]), int(Lk["lock_scores_last_window"])
                Dsc = Lk["lock_scores"]
                adj = start.get(f"{b}|{stem}|{pid}") or {}
                S, _e0 = scorer.totals_and_ends(E, lo, hi, scorer.start(E, lo))
                S = {nm: val + float(adj.get(nm, 0.0)) for nm, val in S.items()}
                arm = max(Dsc, key=lambda nm: (1 - W) * Dsc[nm] + W * S[nm])
                Lk["_lag"] = LAG_W
                lrow.append({"key": f"{c['room']}|{b}|{stem}|{pid}", "stem": stem, "pass_id": pid,
                             "true": r["true_line"], "display_lock": Lk["lock_line"], "scorer_lock": arm,
                             "res": drawn_errors(r, Lk, rec, st)})
        D.V_MEAN, D.V_SD, D2.V_MEAN = V0
        info["resolution"] = resolution(lrow)
        info["minutes"] = round((time.time() - t0) / 60.0, 2)
        with open(J(out_dir, "decode.json"), "w", encoding="utf-8") as f:
            json.dump({"info": info, "sessions": {b: {"rows": {"A": crow}}}}, f, indent=1, default=str)
        with open(J(out_dir, "scorerlock.json"), "w", encoding="utf-8") as f:
            json.dump({"info": info, "sessions": {b: {"rows": {"A": lrow}}}}, f, indent=1, default=str)
        pc = 100.0 * np.mean([r["correct"] for r in crow])
        pl = 100.0 * np.mean([r["display_lock"] == r["true"] for r in lrow])
        ps = 100.0 * np.mean([r["scorer_lock"] == r["true"] for r in lrow])
        print(f"[{time.strftime('%H:%M:%S')}] {cell} {name}: committed {pc:.2f}, display lock {pl:.2f}, "
              f"scorer lock {ps:.2f} ({len(crow)} passes, {info['minutes']} min)", flush=True)
        if name in ("ref", "cfgB"):
            plumb(c, crow, lrow, name, "A" if name == "ref" else "B")
    return 0


# Median and 90th-percentile drawn-dot error (m), over every labelled walk window, over the walks whose...
def resolution(lrow) -> dict:
    # Function q.
    def q(v):
        v = np.asarray(v, float)
        return None if not len(v) else {"median": round(float(np.median(v)), 3),
                                        "p90": round(float(np.percentile(v, 90)), 3), "n_windows": int(len(v))}
    allv = [e for r in lrow for e in r["res"]["err"]]
    ok = [e for r in lrow if r["display_lock"] == r["true"] for e in r["res"]["err"]]
    al = [a for r in lrow for a, s_ in zip(r["res"]["along"], r["res"]["on_true_line"]) if s_]
    ac = [a for r in lrow for a, s_ in zip(r["res"]["across"], r["res"]["on_true_line"]) if s_]
    return {"overall": q(allv), "correct_lock_walks": q(ok), "along_line_on_true_line": q(al),
            "across_line_on_true_line": q(ac)}


# Ref must equal the cell's own configuration A rows, and cfgB its configuration B rows, pass for pass.
def plumb(c, crow, lrow, name="ref", config="A") -> None:
    with open(J(c["base"], "decode.json"), encoding="utf-8") as f:
        d = json.load(f)["sessions"][c["test"]]["rows"][config]
    with open(J(c["base"], "scorerlock.json"), encoding="utf-8") as f:
        s = json.load(f)["sessions"][c["test"]]["rows"][config]
    a = {(r["stem"], r["pass_id"]): r["final_line"] for r in d}
    b = {(r["stem"], r["pass_id"]): r["final_line"] for r in crow}
    la = {(r["stem"], r["pass_id"]): (r["display_lock"], r["scorer_lock"]) for r in s}
    lb = {(r["stem"], r["pass_id"]): (r["display_lock"], r["scorer_lock"]) for r in lrow}
    ok = a == b and la == lb
    res = {"committed_equal": sum(a.get(k) == b.get(k) for k in set(a) | set(b)), "n": len(a),
           "locks_equal": sum(la.get(k) == lb.get(k) for k in set(la) | set(lb)), "n_locks": len(la), "EXACT": ok}
    with open(J(c["base"], "d3", name, "plumb.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"PLUMB {c['cell']}: {res}", flush=True)
    if not ok:
        raise SystemExit(f"{c['cell']}: ref does not reproduce the cell's own rows: {res}")


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    for n in a.variants:
        parse(n)
    if a.inner:
        return inner(a.cell, a.variants)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(a.cell, "decode")
    env = PC.env_for(c, "half", "decode")
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_decode", "--inner", "--cell", a.cell,
                            "--variants", *a.variants], cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
