"""ilw_gate. The link-weighting run's gate (`runs/identify/linkweight/PREREG_LW.md`, sections 4 and 5), from the cache
only (`ilw_cache`), with no identity labels: the estimators V0 to V3 under P_or, P_nom and P_it; Pearson r against the
press speed with Delta r against V0 (paired cluster bootstrap over recordings); the secondary measures; the decision.
Writes `runs/identify/linkweight/gate.json` and `gate_table.md`.

    PYTHONPATH=. python3 -m pipeline.identify.ilw_gate

Exploratory development, all data seen.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilw_cache as LC

LAM, FMIN, VNOM = 0.123, 0.3, 1.2
NB, SEED = 10000, 0
ESTS = ("V1", "V2", "V3")
POS = ("P_nom", "P_it", "P_or")
ORDER = {("V1", "P_nom"): 0, ("V1", "P_it"): 1, ("V2", "P_nom"): 2, ("V2", "P_it"): 3, ("V3", "P_nom"): 4, ("V3", "P_it"): 5}


def family(path: str) -> str:
    return {"A": "A", "B": "B", "C": "C/D", "D": "C/D"}.get(path[0]) or ("E_col" if path.startswith("E_col") else "E_row")


def F_along(path: str, layout: str, s: np.ndarray) -> np.ndarray:
    """(3, frames): the bistatic factor of each link at the fractions s of the path (`mean_F`'s formula per point)."""
    from pipeline.identify.id15_factor_map import bistatic_factor
    from pipeline.identify.idgp_contract import PATHS
    rig = EN._rigs()[layout]
    a, b = (np.asarray(x, float) for x in PATHS[path])
    pts = a[None, :] + np.clip(s, 0, 1)[:, None] * (b - a)[None, :]
    return np.array([bistatic_factor(pts, b - a, rig["TX"], rig[L]) for L in EN.LINKS])


def wmedian(v: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(v, kind="stable")
    v, w = v[o], w[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, 0.5 * c[-1])])


def estimate(est: str, span: dict, link: str, path: str, layout: str, s: np.ndarray) -> float:
    """One estimator on one walk, positions s (fractions of `path`) at the contour's frames."""
    Fk = F_along(path, layout, s)
    C = np.array([span["links"][L]["c"] for L in EN.LINKS])
    if est == "V1":
        j = EN.LINKS.index(link)
        ok = np.isfinite(C[j]) & (Fk[j] >= FMIN)
        return float(np.median(C[j][ok] * LAM / (2 * Fk[j][ok]))) if ok.any() else float("nan")
    if est == "V2":
        j = np.argmax(Fk, axis=0)
        k = np.arange(Fk.shape[1])
        f, c = Fk[j, k], C[j, k]
        ok = np.isfinite(c) & (f >= FMIN)
        return float(np.median(c[ok] * LAM / (2 * f[ok]))) if ok.any() else float("nan")
    ok = np.isfinite(C) & (Fk >= FMIN)
    return wmedian((C[ok] * LAM / (2 * Fk[ok])), Fk[ok] ** 2) if ok.any() else float("nan")


def speeds(r: dict, meta_row: dict, alpha: float = 0.5) -> dict:
    """Every estimator for one walk: V0 and V1 to V3 under P_or, P_nom and P_it."""
    from pipeline.identify.idgp_contract import path_length
    span = r["spans"][alpha]
    out = {"V0": span["v0"]}
    if any(span["links"][L] is None for L in EN.LINKS):
        return out | {f"{e}|{p}": float("nan") for e in ESTS for p in POS}
    t = span["links"][EN.LINKS[0]]["t"]
    ep, tp, layout, link = meta_row["engine_path"], meta_row["path"], r["layout"], r["link"]
    dur = meta_row["t_end"] - meta_row["t_start"]
    for e in ESTS:
        out[f"{e}|P_or"] = estimate(e, span, link, tp, layout, t / dur)
        out[f"{e}|P_nom"] = estimate(e, span, link, ep, layout, VNOM * t / path_length(ep))
        v1 = estimate(e, span, link, ep, layout, VNOM * t / path_length(ep))
        v_pos = v1 if np.isfinite(v1) else VNOM
        out[f"{e}|P_it"] = estimate(e, span, link, ep, layout, v_pos * t / path_length(ep))
    return out


# ------------------------------------------------------------------ statistics

def impute(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, float)
    return np.where(np.isfinite(v), v, np.nanmedian(v)) if np.isfinite(v).any() else v


def pearson_w(x, y, w):
    """Weighted Pearson r for every row of the weight matrix w (resamples x walks)."""
    sw = w.sum(1)
    mx, my = (w @ x) / sw, (w @ y) / sw
    dx, dy = x[None, :] - mx[:, None], y[None, :] - my[:, None]
    return (w * dx * dy).sum(1) / np.sqrt((w * dx * dx).sum(1) * (w * dy * dy).sum(1))


def boot_weights(cluster: np.ndarray, n=NB, seed=SEED) -> np.ndarray:
    u, inv = np.unique(cluster, return_inverse=True)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(u), (n, len(u)))
    counts = np.zeros((n, len(u)))
    np.add.at(counts, (np.repeat(np.arange(n), len(u)), draws.ravel()), 1)
    return counts[:, inv]


def summary(v, ref, mask=None) -> dict:
    from scipy import stats
    m = np.ones(len(v), bool) if mask is None else mask
    cov = float(np.isfinite(v[m]).mean())
    vi = impute(v[m])
    return {"n": int(m.sum()), "coverage": round(cov, 4), "pearson": round(float(stats.pearsonr(vi, ref[m])[0]), 4),
            "spearman": round(float(stats.spearmanr(vi, ref[m])[0]), 4),
            "median_abs_error": round(float(np.median(np.abs(vi - ref[m]))), 4)}


def run() -> dict:
    from scipy import stats
    meta = json.load(open(os.path.join(EN.bank_dir(LC.T), "meta.json")))["passes"]
    rows = LC.load_all()
    assert [r["row"] for r in rows] == list(range(len(meta)))
    V = [speeds(r, meta[r["row"]]) for r in rows]
    names = list(V[0])
    S = {k: np.array([v[k] for v in V], float) for k in names}
    press = np.array([m["press_speed_m_s"] for m in meta], float)
    kind = np.array([m["kind"] for m in meta])
    sess = np.array([m["session"] for m in meta])
    room = np.array([m["room"] for m in meta])
    anon = np.array([m["anon"] for m in meta])
    block = np.array([m["block"] for m in meta])
    fam = np.array([family(m["path"]) for m in meta])
    trk, idc = kind == "track", kind == "idcap"
    assert trk.sum() == 600 and idc.sum() == 419
    assert np.allclose(S["V0"], [m["wifi_speed"] for m in meta], equal_nan=True, rtol=0, atol=1e-9)
    # primary: tracking walks, paired cluster bootstrap over recordings (session x participant)
    W = boot_weights(np.char.add(sess[trk], anon[trk]))
    y = press[trk]
    base = impute(S["V0"][trk])
    r0 = float(stats.pearsonr(base, y)[0])
    rb0 = pearson_w(base, y, W)
    res = {"label": LC.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "prereg": "runs/identify/linkweight/PREREG_LW.md",
           "clusters_tracking": int(len(np.unique(np.char.add(sess[trk], anon[trk])))), "resamples": NB, "seed": SEED,
           "rows": {}}
    yi = press[idc]
    r0_id = float(stats.pearsonr(impute(S["V0"][idc]), yi)[0])
    for k in names:
        v = impute(S[k][trk])
        r = float(stats.pearsonr(v, y)[0])
        d = pearson_w(v, y, W) - rb0
        lo, hi = np.percentile(d, [2.5, 97.5])
        ri = float(stats.pearsonr(impute(S[k][idc]), yi)[0])
        row = {"tracking": summary(S[k], press, trk), "identification": summary(S[k], press, idc),
               "delta_r": round(r - r0, 4), "delta_r_ci95": [round(float(lo), 4), round(float(hi), 4)],
               "delta_r_identification": round(ri - r0_id, 4),
               "by_session": {s: summary(S[k], press, trk & (sess == s)) for s in LC.SESSIONS},
               "by_room": {rm: summary(S[k], press, trk & (room == rm)) for rm in ("A", "B")},
               "by_family": {f: summary(S[k], press, trk & (fam == f)) for f in ("A", "B", "C/D", "E_col", "E_row")},
               "identification_by_block": {b: summary(S[k], press, idc & (block == b)) for b in ("natural", "slow", "fast")}}
        if k != "V0":
            mae0 = res["rows"]["V0"]["tracking"]["median_abs_error"] if "V0" in res["rows"] else None
            c1 = row["delta_r"] >= 0.05 and row["delta_r_ci95"][0] > 0
            c2 = row["tracking"]["median_abs_error"] <= mae0 + 0.02
            c3 = row["delta_r_identification"] >= -0.02
            row["conditions"] = {"delta_r_ge_0.05_and_lower_bound_above_0": bool(c1), "mae_within_0.02_of_V0": bool(c2),
                                 "identification_delta_r_ge_-0.02": bool(c3)}
            row["PASSES"] = bool(c1 and c2 and c3)
        res["rows"][k] = row
    # the decision (deployable candidates only; P_or beside as the upper bound)
    passing = [(k, res["rows"][k]["delta_r"]) for k in names if k != "V0" and not k.endswith("P_or") and res["rows"][k]["PASSES"]]
    fwd = None
    if passing:
        best = max(d for _k, d in passing)
        near = [k for k, d in passing if d >= best - 0.01]
        fwd = min(near, key=lambda k: ORDER[tuple(k.split("|"))])
    res["passing_deployable"] = [k for k, _d in passing]
    res["passing_oracle"] = [k for k in names if k.endswith("P_or") and res["rows"][k]["PASSES"]]
    res["forwarded"] = fwd
    res["oracle_note"] = ("no P_or candidate passes: perfect position does not help, so no deployable version can"
                          if not res["passing_oracle"] else "at least one P_or candidate passes")
    res["snr_db"] = snr(rows, meta)
    res["doppler_follows_geometry"] = follows(rows, meta)
    json.dump(res, open(os.path.join(LC.LW, "gate.json"), "w"), indent=1)
    open(os.path.join(LC.LW, "gate_table.md"), "w").write(table(res))
    print(table(res))
    print(f"forwarded: {fwd}; passing deployable: {res['passing_deployable']}; passing oracle: {res['passing_oracle']}")
    return res


# ------------------------------------------------------------------ secondary: SNR and the geometry diagnostic

def snr(rows: list, meta: list) -> dict:
    """10 log10(median torso-band power / median 60 to 70 Hz power) over the walking span's frames, per walk and link;
    the median over walks by room x link (every walk) and by family for the shipped link (tracking walks)."""
    by, shipped = {}, {}
    for r in rows:
        m = meta[r["row"]]
        sp = r["spans"][0.5]
        for L in EN.LINKS:
            d = sp["links"][L]
            if d is None or not len(d["e_ref"]) or np.median(d["e_ref"]) <= 0:
                continue
            val = 10 * np.log10(np.median(d["e_torso"]) / np.median(d["e_ref"]))
            by.setdefault(f"{m['room']} {m['kind']} {L}", []).append(val)
            if L == r["link"] and m["kind"] == "track":
                shipped.setdefault(f"{m['room']} {family(m['path'])} {L}", []).append(val)
    q = lambda v: {"median_db": round(float(np.median(v)), 2), "n": len(v)}  # noqa: E731
    return {"room_kind_link": {k: q(v) for k, v in sorted(by.items())},
            "tracking_shipped_link_by_room_family": {k: q(v) for k, v in sorted(shipped.items())}}


def follows(rows: list, meta: list) -> dict:
    """Within-walk Spearman of c_k against F_L(p_k) under P_or (at least 5 frames with finite c and F > 0, F not
    constant); the median over walks per room, kind and link."""
    from scipy import stats
    out = {}
    for r in rows:
        m = meta[r["row"]]
        sp = r["spans"][0.5]
        if any(sp["links"][L] is None for L in EN.LINKS):
            continue
        t = sp["links"]["RX1"]["t"]
        Fk = F_along(m["path"], r["layout"], t / (m["t_end"] - m["t_start"]))
        for j, L in enumerate(EN.LINKS):
            c = sp["links"][L]["c"]
            ok = np.isfinite(c) & (Fk[j] > 0)
            if ok.sum() < 5 or np.ptp(Fk[j][ok]) < 1e-9 or np.ptp(c[ok]) == 0:
                continue
            out.setdefault(f"{m['room']} {m['kind']} {L}", []).append(float(stats.spearmanr(c[ok], Fk[j][ok])[0]))
    return {k: {"median_rho": round(float(np.median(v)), 3), "walks": len(v)} for k, v in sorted(out.items())}


def table(res: dict) -> str:
    lines = ["| estimator | position | tracking r | Delta r [95 %] | median abs error (m/s) | coverage | identification r | "
             "Delta r (identification) | passes |", "|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["rows"].items():
        e, p = (k.split("|") + ["shipped"])[:2]
        if k == "V0":
            dr = dri = ok = ""
        else:
            ci = v["delta_r_ci95"]
            dr = f"{v['delta_r']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]"
            dri = f"{v['delta_r_identification']:+.3f}"
            ok = "yes" if v["PASSES"] else "no"
        tr = v["tracking"]
        lines.append(f"| {e} | {p} | {tr['pearson']:.3f} | {dr} | {tr['median_abs_error']:.3f} | {tr['coverage']:.3f} | "
                     f"{v['identification']['pearson']:.3f} | {dri} | {ok} |")
    return "\n".join(lines)

if __name__ == "__main__":
    run()
    sys.exit(0)
