"""ilw_cache. The link-weighting run's cache (`runs/identify/linkweight/PREREG_LW.md`, section 3): one pass over every
recording through the engine's own Extractor at T 4.0, decisions at the engine's own t_dec (its `poll` unchanged; only
`extract_v4` is replaced, by the speed's own steps). For each pass, both walking spans (alpha 0.5 and 0.2, the engine's
`detect_end` on its own checkpoint series) and each link: the per-frame torso contour on A[L][:nw] exactly as
`id29_dc2_score.torso_hz` computes it, its frame times from `scipy.signal.stft`, and the band powers the SNR needs.

Checks on every pass: t_dec, both walking ends, the shipped link, f_torso and V0 (both alphas, to 1e-9) against
`bank_T4.0_v4/meta.json`.

    PYTHONPATH=. python3 -m pipeline.identify.ilw_cache build [--session A1] [--limit 5 --out <file>]
    PYTHONPATH=. python3 -m pipeline.identify.ilw_cache verify

Exploratory development, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

T = 4.0
ALPHAS = (0.5, 0.2)
WKEY = {0.5: "walk_end_s", 0.2: "walk_end_s_a0.2"}
VKEY = {0.5: "wifi_speed", 0.2: "wifi_speed_a0.2"}
SESSIONS = ("A1", "A2", "A3", "B1", "B2")
LW = os.path.join("runs", "identify", "linkweight")
OUT = os.path.join(LW, "cache")
LABEL = "exploratory development, all data seen"
TORSO_BAND, REF_BAND = (10.0, 35.0), (60.0, 70.0)


def contour(a_link: np.ndarray) -> dict:
    """`torso_hz`'s per-frame contour, with scipy's frame times and the SNR's band powers (same STFT)."""
    from scipy import signal
    from pipeline.identify import idmax_common as IC
    from pipeline.identify import idmax_features as F
    from pipeline.identify.conditioning import energy_percentile_contour
    P = F.reduce_link(a_link, "dop", "pca", n_pc=4)[1:]
    f, t, Z = signal.stft(P, fs=IC.FS, nperseg=32, noverlap=24, nfft=64, axis=-1)
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 70.0)
    c = np.asarray(energy_percentile_contour(f[keep], mag[:, keep], 50.0), float)
    pw = (np.abs(Z) ** 2).sum(axis=0).T
    e_t = pw[:, (f >= TORSO_BAND[0]) & (f < TORSO_BAND[1])].sum(axis=1)
    e_r = pw[:, (f >= REF_BAND[0]) & (f <= REF_BAND[1])].sum(axis=1)
    return {"t": np.asarray(t, float), "c": c, "e_torso": e_t, "e_ref": e_r}


class LWTap(EN.Extractor):
    """The engine's Extractor; `extract_v4` keeps only the speed's steps (no features), for both alphas."""

    def extract_v4(self, w: dict, td: float, timed: list) -> dict:
        from pipeline.identify import id29_dc2_score as D
        t0, end = w["t0"], self._end(w)
        series = []
        for c in np.round(np.arange(EN.DIR_T_S, self.T + 1e-9, EN.DET_STEP_S), 2):
            ec = min(t0 + c, end)
            series.append((float(ec - t0), EN.band_energy_rx2(self._raw(t0, ec, self.t_dec_end(t0, ec))[1])))
            if ec < t0 + c:
                break
        A = self._raw(t0, end, td)
        grid = np.arange(t0, end, 1.0 / EN.FS)
        path, layout = w["path"], w["layout"]
        li, Fm = EN.best_link(path, layout)
        out = {"path": path, "layout": layout, "link": EN.LINKS[li], "F_mean": Fm, "spans": {}}
        for a in ALPHAS:
            d = EN.detect_end(series, a, upto=self.T)
            walk_end = min(t0 + d[0], end) if d is not None else end
            nw = int(np.searchsorted(grid, walk_end, side="left"))
            ft = D.torso_hz(A[li][:nw]) if nw >= 64 else float("nan")
            v0 = float(ft * EN.LAMBDA / (2.0 * Fm)) if (Fm >= EN.F_MIN and np.isfinite(ft)) else float("nan")
            links = {L: (contour(A[j][:nw]) if nw >= 64 else None) for j, L in enumerate(EN.LINKS)}
            cl = links[EN.LINKS[li]]
            med = float(np.median(cl["c"][np.isfinite(cl["c"])])) if (cl is not None and np.isfinite(cl["c"]).any()) else float("nan")
            out["spans"][a] = {"walk_end_s": walk_end - t0, "nw": nw, "f_torso": ft, "v0": v0, "contour_median": med,
                               "links": links}
        return out


def build(session: str = None, limit: int = None, out_file: str = None) -> str:
    from pipeline.identify import idx_bank as B
    from pipeline.io.capture_logger import read_capture_file
    meta = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
    names = json.load(open(EN.DEV_NAMES))
    rows, k, n, t_all = [], 0, 0, time.time()
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda z: z["t_start"])
        if session and rec["session"] != session:
            k += len(qs)
            continue
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = LWTap(T=T, layout=layout, names=names, alpha=0.5)
        pos = {L: 0 for L in EN.LINKS}
        for q in qs:
            m = meta[k]
            t0 = float(q["t_start"])
            assert abs(m["t_start"] - t0) < 1e-6 and m["session"] == rec["session"], (k, "row order")
            lim = t0 + T + EN.CAP_S
            for L in EN.LINKS:
                j = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:j])
                pos[L] = j
            ex.press(t0, path=m["engine_path"])
            (w, td, x), = ex.poll(lim)
            chk = {"t_dec": abs(td - m["t_dec"]) < 1e-9, "link": x["link"] == m["speed_link"]}
            for a in ALPHAS:
                s = x["spans"][a]
                chk[f"walk_end_{a}"] = abs(s["walk_end_s"] - m[WKEY[a]]) < 1e-9
                b = m[VKEY[a]]
                chk[f"v0_{a}"] = bool((np.isnan(s["v0"]) and np.isnan(b)) or abs(s["v0"] - b) <= 1e-9)
                chk[f"contour_median_{a}"] = bool((np.isnan(s["f_torso"]) and np.isnan(s["contour_median"]))
                                                  or s["f_torso"] == s["contour_median"])
            # information only: the bank's `f_torso` is engine v3's (3.0 s; iv4_build.merge never updated it), so
            # f_torso is checked through V0 against `wifi_speed` (PREREG_LW note of 23:55)
            info = {"bank_f_torso_is_v3_and_equal": bool(x["spans"][0.5]["f_torso"] == m["f_torso"])}
            rows.append({"row": k, "session": m["session"], "kind": m["kind"], "t0": t0, "t_dec": td, **x, "checks": chk,
                         "info": info})
            k += 1
            n += 1
            if limit and n >= limit:
                break
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {n} passes, "
              f"{time.time() - t_all:.0f} s, checks failed so far {sum(not all(r['checks'].values()) for r in rows)}", flush=True)
        if limit and n >= limit:
            break
    p = out_file or os.path.join(OUT, f"{session or 'all'}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump({"label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "T": T, "rows": rows,
                 "seconds": round(time.time() - t_all, 1)}, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} wrote {p}: {n} passes in {time.time() - t_all:.0f} s", flush=True)
    return p


def load_all() -> list:
    rows = []
    for s in SESSIONS:
        rows += pickle.load(open(os.path.join(OUT, f"{s}.pkl"), "rb"))["rows"]
    return sorted(rows, key=lambda r: r["row"])


def verify() -> dict:
    meta = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
    rows = load_all()
    res = {"label": LABEL, "passes": len(rows), "expected": len(meta),
           "rows_complete": [r["row"] for r in rows] == list(range(len(meta))), "failed": {}}
    for r in rows:
        for c, ok in r["checks"].items():
            if not ok:
                res["failed"].setdefault(c, []).append(r["row"])
    res["checks"] = sorted(rows[0]["checks"]) if rows else []
    res["PASSED"] = res["rows_complete"] and not res["failed"]
    res["built"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(res, open(os.path.join(LW, "cache_verify.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    what = sys.argv[1]
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None  # noqa: E731
    if what == "build":
        build(arg("--session"), int(arg("--limit")) if arg("--limit") else None, arg("--out"))
    elif what == "verify":
        sys.exit(0 if verify()["PASSED"] else 1)
    else:
        raise SystemExit(what)
    sys.exit(0)
