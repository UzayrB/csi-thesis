"""ixt_walk. One worked walk, opened up for the teaching pack (`reports/identification/briefs/2026-10-01_teaching.md` section 2.3 A):
the engine's own extraction of the walk re-run step by step (the same frames, the same causal clock, the same
functions), every intermediate kept, and asserted equal to the engine bank's features and maps. The app-level
numbers (decision, probabilities, confidence, latency, calibration count) come from the verification run of the live
app's rig path (`ixt_verify`). Names, not codes. Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify.common import SIX, anon

CODES = ("P1", "P2", "P3", "P4", "P5", "P6")
NAME = {anon(n): n for n in SIX}
FS = 150.0


def ds_mean(x, k, axis=0):
    """Average consecutive groups of k samples along axis (drops a ragged end)."""
    x = np.asarray(x, float)
    n = (x.shape[axis] // k) * k
    x = np.take(x, np.arange(n), axis=axis)
    shp = list(x.shape)
    shp[axis:axis + 1] = [n // k, k]
    return x.reshape(shp).mean(axis=axis + 1)


def ds_rms(x, k, axis=0):
    return np.sqrt(ds_mean(np.asarray(x, float) ** 2, k, axis))


def acf(x, max_lag):
    x = np.asarray(x, float) - np.mean(x)
    den = float(np.dot(x, x)) or 1.0
    return np.array([np.dot(x[:len(x) - k], x[k:]) / den for k in range(max_lag + 1)])


def extract(stem: str, t0: float, row: int, meta_row: dict, bank_X, bank_maps, alpha: float = None) -> dict:
    """Re-run the engine's extraction of one walk (its own recording, frames pushed to the window's cap as the bank
    builder does) and keep every intermediate."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import ixa_data as XD
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.io.capture_logger import read_capture_file
    fr = {L: read_capture_file(f"{stem}_{L}.bin")[1] for L in EN.LINKS}
    names = json.load(open(EN.DEV_NAMES))
    ex = XD.Tap(T=EN.T_S, layout="id_spot", names=names, alpha=alpha)
    gt = json.load(open(stem + ".gt.json", encoding="utf-8"))
    pos = {L: 0 for L in EN.LINKS}
    out = None
    for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
        tq = float(q["t_start"])
        lim = tq + EN.T_S + EN.CAP_S
        for L in EN.LINKS:
            n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
            ex.push(L, fr[L][pos[L]:n])
            pos[L] = n
        ex.press(tq, path=None, info={"features": True})
        (_w, td, A, x), = ex.poll(lim)
        if abs(tq - t0) < 1e-9:
            timed = [ex.rx[L].timed(td) for L in EN.LINKS]
            arrivals = {L: np.asarray(fr[L]["t_mono"][:pos[L]], float) for L in EN.LINKS}
            grid = np.arange(t0, t0 + EN.T_S, 1.0 / FS)
            R = np.asarray([_interp_cols(grid, t, r.astype(np.float64)) for t, _a, r in timed], np.float64)
            with (EN._cadence_v3() if EN.ENGINE_VERSION >= 3 else EN._cadence_v2()):   # the engine's own resolver
                feats = FB.pass_features(A, R)
            out = {"t_dec": td, "A": A, "R": R, "timed": timed, "arrivals": arrivals, "x": x, "q": q, "feats": feats}
            if EN.T_S > EN.DIR_T_S:                    # engine v4: the direction's 3 s window and the end detector's series
                e3 = t0 + EN.DIR_T_S
                out["A3"] = ex._raw(t0, e3, ex.t_dec_end(t0, e3))
                out["t_dec3"] = ex.t_dec_end(t0, e3)
                out["series"] = [(float(c), EN.band_energy_rx2(ex._raw(t0, t0 + c, ex.t_dec_end(t0, t0 + c))[1]))
                                 for c in np.round(np.arange(EN.DIR_T_S, EN.T_S + 1e-9, EN.DET_STEP_S), 2)]
            break
    assert out is not None
    assert abs(out["t_dec"] - meta_row["t_dec"]) < 1e-9
    assert np.array_equal(out["x"]["features"], bank_X[row], equal_nan=True)          # the bank's own features
    assert np.array_equal(out["x"]["maps"], bank_maps[row])                           # and maps
    return out


def conditioning(a_link: np.ndarray) -> dict:
    """The map's chain, step by step, for one link (the statements of `idz_bank.conditioned_map_v2`)."""
    from scipy import signal
    from pipeline.identify import idmax_features as F
    from pipeline.identify import idz_bank as ZB
    a = np.asarray(a_link, float)
    b = F.bandpass(a, "dop", axis=0)
    P = F.reduce_link(b, "dop", "pca", n_pc=4, bmat=b)                                # PCs 1 to 4, skew-signed
    c = b - b.mean(axis=0, keepdims=True)
    ev = np.linalg.eigvalsh(np.cov(c, rowvar=False))[::-1]
    s = C.HP["stft"]
    _f, _t, Z = signal.stft(P[1:], fs=FS, nperseg=s["nperseg"], noverlap=s["noverlap"], nfft=s["nfft"], axis=-1,
                            boundary=None, padded=False)
    mag = np.abs(Z)                                                                     # (3 PCs, 33 freqs, frames)
    final = ZB.conditioned_map_v2(a)
    summed = mag.sum(axis=0)[C.KEEP_F]
    eps = 1e-6 * float(np.median(summed))
    lg = np.log(summed + eps)
    assert np.allclose(lg - lg.mean(), final, atol=1e-5)
    return {"raw": a, "band": b, "pcs": P, "explained": ev[:4] / ev.sum(), "stft_per_pc": mag[:, C.KEEP_F, :],
            "log_map": final}


def cnn_evolution(model, session, ex: dict) -> dict:
    """Each CNN component's per-window log-probabilities in time order, and their running mean; the last running
    value equals the component's output (the feature components decide once, on the whole window)."""
    Wn = C.windows(ex["maps"])
    nwin = len(Wn)
    out = {}
    for comp, tags, adapted in (("cnn", ("cnn3",), False), ("cnn_prior", ("cnn3",), True),
                                ("cnn_perlink_prior", ("cnn_link0", "cnn_link1", "cnn_link2"), True)):
        per_tag = []
        for tag in tags:
            Xw, dw, _pw = session._cnn_input(tag, [Wn], [ex["path"]])
            seeds = []
            for s in model.meta["seeds"]:
                net = session.adapted.get((tag, s), model.nets[(tag, s)]) if adapted else model.nets[(tag, s)]
                seeds.append(C.pass_logp(net, Xw, dw, np.arange(nwin), nwin, 6, model.device))   # per window
            per_tag.append(np.array(seeds))                                                  # (seeds, windows, 6)
        win = []
        run = []
        for w in range(nwin):
            pw_ = C.normalise_logp(sum(np.mean(t[:, w, :], axis=0) for t in per_tag)[None, :])[0]
            win.append(pw_)
            rr = []
            for t in per_tag:
                seed_run = [C.normalise_logp(t[si, :w + 1, :].mean(axis=0)[None, :])[0] for si in range(t.shape[0])]
                rr.append(C.normalise_logp(np.mean(seed_run, axis=0)[None, :])[0])
            run.append(C.normalise_logp(sum(rr)[None, :])[0])
        out[comp] = {"per_window_logp": np.array(win), "running_logp": np.array(run)}
    centre = (16.0 + 8.0 * (4 * np.arange(nwin) + 16.5)) / FS
    return {"window_centre_s": centre, **out}
