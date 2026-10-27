# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Identification audit: bank builds for the bug fixes and the candidates.

from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_features as F
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_bank as B
from pipeline.identify.id19_bank import _interp_cols
from pipeline.identify.id19_featbank import CADENCE_CH, LINKS, RHYTHM_CH, SC

AUDIT = os.path.join("runs", "identify", "audit")



# Function columns v2.
def columns_v2(bank) -> np.ndarray:
    from pipeline.identify import idx_loso as L
    cols = L.columns("U_all_gait")
    names = np.array(bank["names"])
    return np.array([j for j in cols if not names[j].endswith("|dwt_6")])


# The conditioned map from an already band-limited (4 to 70 Hz) pass: per-pass PCA (PCs 2 to 4, skew sign)...
def _map_from_bmat(bm_dop: np.ndarray) -> np.ndarray:
    from scipy import signal
    P = F.reduce_link(bm_dop, "dop", "pca", n_pc=4, bmat=bm_dop)[1:]
    s = C.HP["stft"]
    _f, _t, Z = signal.stft(P, fs=C.HP["fs"], nperseg=s["nperseg"], noverlap=s["noverlap"], nfft=s["nfft"],
                            axis=-1, boundary=None, padded=False)
    mag = np.abs(Z).sum(axis=0)[C.KEEP_F]
    eps = 1e-6 * (float(np.median(mag)) if mag.size and np.median(mag) > 0 else 1.0)
    m = np.log(mag + eps)
    return (m - m.mean()).astype(np.float32)


# Function conditioned map v2.
def conditioned_map_v2(a_link: np.ndarray) -> np.ndarray:
    return _map_from_bmat(F.bandpass(np.asarray(a_link, float), "dop", axis=0))



# Id19_featbank.pass_features with every band-pass on the long stream al (3, N, 103) / rl (3, N), cut to...
def pass_features_cf(al: np.ndarray, rl: np.ndarray, i0: int, i1: int, cadence_env: bool = False) -> dict:
    from pipeline.identify.id19_featbank import pass_features
    cut = slice(i0, i1)
    a = al[:, cut]
    rssi = rl[:, cut]
    out, chans, bm, env = {}, {}, {}, {}
    for li, link in enumerate(LINKS):
        long_b = {band: F.bandpass(al[li], band, axis=0) for band in ("b03_2", "b08_35", "full", "dop")}
        for band in long_b:
            bm[(li, band)] = long_b[band][cut]
        for red, band in RHYTHM_CH + [("mean", "dop"), ("pca", "dop"), ("mean", "full")]:
            key = (link, red, band)
            if key in chans:
                continue
            if red == "mean":
                chans[key] = F.bandpass(al[li].mean(axis=1), band)[cut][None, :]
            elif red == "rms":
                e = np.sqrt(np.mean(long_b[band] ** 2, axis=1))
                chans[key] = F.bandpass(e, "b03_2" if band == "b03_2" else "b08_35")[cut][None, :]
            else:
                chans[key] = F.reduce_link(a[li], band, "pca", n_pc=6, bmat=bm[(li, band)])
        chans[(link, "rssi", "b03_2")] = F.bandpass(rl[li], "b03_2")[cut][None, :]
        chans[(link, "rssi", "b08_35")] = F.bandpass(rl[li], "b08_35")[cut][None, :]
        if cadence_env:
            env[link] = doppler_envelope(bm[(li, "dop")])
    est = []
    for link in LINKS:
        for red, band in CADENCE_CH:
            est.append(F.cadence_estimates(chans[(link, red, band)][0]))
        if cadence_env and env[link] is not None:
            est.append(F.cadence_estimates(env[link], fs=C.HP["fs"] / 8.0))
    cad = F.resolve_cadence(est)
    c = cad["cadence_hz"]
    out["cad|all|-|-|cadence_hz"] = c
    out["cad|all|-|-|agree_frac"] = cad["agree_frac"]
    per_link = []
    for link in LINKS:
        e = [F.cadence_estimates(chans[(link, red, band)][0]) for red, band in CADENCE_CH]
        if cadence_env and env[link] is not None:
            e.append(F.cadence_estimates(env[link], fs=C.HP["fs"] / 8.0))
        rl_ = F.resolve_cadence(e)
        per_link.append(rl_["cadence_hz"])
        out[f"cad|link|{link}|-|cadence_hz"] = rl_["cadence_hz"]
    pl = [x for x in per_link if x]
    out["cad|all|-|-|link_spread"] = float(np.ptp(pl)) if len(pl) > 1 else np.nan
    for (link, red, band), X in chans.items():
        rh = (red, band) in RHYTHM_CH or red == "rssi"
        for ci in range(X.shape[0]):
            x = X[ci]
            tag = f"{red}@{band}|{link}|{ci}"
            if rh:
                for k, v in F.rhythm_features(x, c).items():
                    out[f"rhy|{tag}|{k}"] = v
                for m in ("acf", "peaks"):
                    for k, v in F.cycle_templates(x, c, method=m).items():
                        out[f"tpl{m}|{tag}|{k}"] = v
            sb = band if band in ("b08_35", "dop", "full", "b03_2") else "b08_35"
            if red in ("mean", "rssi") or (red == "pca" and ci < 3) or red == "rms":
                for k, v in F.spectral_shape(x, sb).items():
                    out[f"spec|{tag}|{k}"] = v
    for li, link in enumerate(LINKS):
        P = chans[(link, "pca", "dop")]
        for w in F.STFT_WINDOWS_S:
            for drop in (0, 1):
                for k, v in F.doppler_features(P[drop:], win_s=w, cadence_hz=c).items():
                    out[f"dop|pca{'-' if drop else '+'}pc1@w{w}|{link}|-|{k}"] = v
        for k, v in F.wavelet_features(chans[(link, "mean", "full")][0]).items():
            out[f"wav|mean@full|{link}|0|{k}"] = v
        for k, v in modulation_cf(al[li], a[li], rssi[li], cut).items():
            out[f"mod|-|{link}|-|{k}"] = v
        for k, v in F.profile_features(a[li], b_full=bm[(li, "full")]).items():
            out[f"prof|-|{link}|-|{k}"] = v
        for k, v in F.recsig_features(a[li], rssi[li]).items():
            out[f"RECSIG|-|{link}|-|{k}"] = v
    return out


# Idmax_features.modulation_features with its band-passes on the long stream.
def modulation_cf(a_long, a_cut, rssi_cut, cut) -> dict:
    lvl = max(float(np.asarray(a_cut, float).mean()), 1e-6)
    g = F.bandpass(a_long.mean(axis=1), "b08_35")[cut]
    bd = F.bandpass(a_long, "dop", axis=0)
    bg = F.bandpass(a_long, "b08_35", axis=0)[cut]
    d = F.bandpass(np.sqrt(np.mean(bd ** 2, axis=1)), "b08_35")[cut]
    r = np.asarray(rssi_cut, float)
    return {"moddepth_gait": float(np.std(g) / lvl), "moddepth_dop": float(np.std(d) / lvl),
            "sub_dispersion": float(np.median(np.std(bg, axis=0)) / max(np.std(g), 1e-9)),
            "rssi_std": float(np.std(r - np.median(r)))}


# C1's envelope: the power of PCs 2 to 4 of the pass's 4-70 Hz band, STFT (32, 24, 64), summed over 10 to 70...
def doppler_envelope(bm_dop: np.ndarray):
    from scipy import signal
    P = F.reduce_link(bm_dop, "dop", "pca", n_pc=4, bmat=bm_dop)[1:]
    f, _t, Z = signal.stft(P, fs=C.HP["fs"], nperseg=32, noverlap=24, nfft=64, axis=-1, boundary=None, padded=False)
    pw = (np.abs(Z) ** 2).sum(axis=0)
    m = (f >= 10.0) & (f <= 70.0)
    e = pw[m].sum(axis=0)
    return e - e.mean() if e.size >= 8 else None



# Function links.
def _links(rec, amp_norm: bool):
    out = []
    for L in LINKS:
        t, a, r, ch = D._link(f"{rec['stem']}_{L}.bin")
        a = np.asarray(a, float)[:, SC]
        if amp_norm:
            a = a / np.maximum(a.mean(axis=1, keepdims=True), 1e-9)
        out.append((t, a, np.asarray(r, float)))
    return out


# A bank in the dev bank's format and row order.
def build(out: str, context_s: float = 0.0, amp_norm: bool = False, cadence_env: bool = False,
          maps_only: bool = False) -> dict:
    os.makedirs(out, exist_ok=True)
    meta = json.load(open(os.path.join(B.OUT, "meta.json")))
    names = json.load(open(os.path.join(B.OUT, "feature_names.json")))
    col = {n: j for j, n in enumerate(names)}
    X = np.load(os.path.join(B.OUT, "features.npy")) if maps_only else np.full((len(meta["passes"]), len(names)), np.nan, np.float32)
    maps = []
    k = 0
    t0_all = time.time()
    fs = C.HP["fs"]
    for rec in B.recordings():
        links = _links(rec, amp_norm)
        lo = max(l[0].min() for l in links)
        hi = min(l[0].max() for l in links)
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0, t1 = float(q["t_start"]), float(q["t_end"])
            assert abs(meta["passes"][k]["t_start"] - t0) < 1e-6, (k, rec["session"])
            g_pass = np.arange(t0, t1, 1.0 / fs)
            n = len(g_pass)
            pre = int(np.floor(min(context_s, max(t0 - lo, 0.0)) * fs))
            post = int(np.floor(min(context_s, max(hi - t1, 0.0)) * fs))
            grid = np.concatenate([t0 - np.arange(pre, 0, -1) / fs, g_pass, g_pass[-1] + np.arange(1, post + 1) / fs])
            al = np.asarray([_interp_cols(grid, t, a) for t, a, _r in links], np.float64)
            rl = np.asarray([_interp_cols(grid, t, r) for t, _a, r in links], np.float64)
            i0, i1 = pre, pre + n
            maps.append(np.stack([_map_from_bmat(F.bandpass(al[li], "dop", axis=0)[i0:i1]) for li in range(3)]))
            if not maps_only:
                feats = pass_features_cf(al, rl, i0, i1, cadence_env=cadence_env)
                for nm, v in feats.items():
                    if nm in col and v is not None and np.isfinite(v):
                        X[k, col[nm]] = v
            k += 1
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k} passes, "
              f"{time.time() - t0_all:.0f} s", flush=True)
    assert k == len(meta["passes"])
    shutil.copy(os.path.join(B.OUT, "meta.json"), os.path.join(out, "meta.json"))
    json.dump(names, open(os.path.join(out, "feature_names.json"), "w"))
    np.save(os.path.join(out, "features.npy"), X.astype(np.float32))
    pickle.dump(maps, open(os.path.join(out, "maps.pkl"), "wb"))
    info = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "context_s": context_s, "amp_norm": amp_norm,
            "cadence_env": cadence_env, "maps_only": maps_only, "map": "conditioned_map_v2 (relative constant)",
            "n_passes": k, "seconds": round(time.time() - t0_all, 1)}
    json.dump(info, open(os.path.join(out, "build.json"), "w"), indent=1)
    print(json.dumps(info))
    return info


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--context", type=float, default=0.0)
    ap.add_argument("--amp-norm", action="store_true")
    ap.add_argument("--cadence-env", action="store_true")
    ap.add_argument("--maps-only", action="store_true")
    a = ap.parse_args(argv)
    assert os.path.abspath(a.out).startswith(os.path.abspath(AUDIT)), "banks go under runs/identify/audit/"
    build(a.out, a.context, a.amp_norm, a.cadence_env, a.maps_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
