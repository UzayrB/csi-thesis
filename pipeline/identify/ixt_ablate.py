"""ixt_ablate. The teaching-pack brief's conditioning ablation (`runs/identify/engine/PLAN.md`, the teaching note, C3).
Information only; never adopted; the engine does not change.

Maps from the engine's own windows (one pass through `engine.Extractor`), each variant changing one conditioning step:
V1 no band-pass (PCA on the mean-centred raw window); V2 PCs 1 to 3 kept; V3 the band-passed subcarrier mean (one
channel) instead of PCA; V4 no log and no mean subtraction. The three CNN components are retrained per variant for
"to B2" and "to B1" (`idz_core.train`, parts "cnn") and scored in replay order with causal AdaBN, beside the frozen
feature components of the engine's replays. Also the identity-blind RX2 10 to 35 Hz energy over the empty room, raw
and conditioned.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_ablate maps | train V1 B2 ... | score [--device mps]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C

OUT = os.path.join("runs", "identify", "teaching", "ablation")
VARIANTS = ("V1", "V2", "V3", "V4")
TW = EN.T_S                                        # engine v4 (2 Oct): the engine's window; 3 s files keep their old names
MAPS = (lambda v: f"maps_{v}.pkl") if TW == 3.0 else (lambda v: f"maps_T{TW:.1f}_{v}.pkl")       # noqa: E731
DESC = {"V1": "no band-pass (PCA on the mean-centred raw window)", "V2": "PC1 kept (PCs 1 to 3)",
        "V3": "the band-passed subcarrier mean instead of PCA", "V4": "no log and no mean subtraction"}


def _stft(P):
    from scipy import signal
    s = C.HP["stft"]
    _f, _t, Z = signal.stft(P, fs=C.HP["fs"], nperseg=s["nperseg"], noverlap=s["noverlap"], nfft=s["nfft"], axis=-1,
                            boundary=None, padded=False)
    return np.abs(Z)


def _finish(mag, log_mean=True):
    mag = mag[C.KEEP_F]
    if not log_mean:
        return mag.astype(np.float32)
    eps = 1e-6 * (float(np.median(mag)) if mag.size and np.median(mag) > 0 else 1.0)
    m = np.log(mag + eps)
    return (m - m.mean()).astype(np.float32)


def variant_map(a_link: np.ndarray, v: str) -> np.ndarray:
    """One link's (28, frames) map under variant v; the engine's map is `idz_bank.conditioned_map_v2`."""
    from pipeline.identify import idmax_features as F
    a = np.asarray(a_link, float)
    if v == "V1":
        b = a - a.mean(axis=0, keepdims=True)
        return _finish(_stft(F.reduce_link(b, "dop", "pca", n_pc=4, bmat=b)[1:]).sum(axis=0))
    b = F.bandpass(a, "dop", axis=0)
    if v == "V2":
        return _finish(_stft(F.reduce_link(b, "dop", "pca", n_pc=4, bmat=b)[0:3]).sum(axis=0))
    if v == "V3":
        return _finish(_stft(b.mean(axis=1)[None, :]).sum(axis=0))
    if v == "V4":
        return _finish(_stft(F.reduce_link(b, "dop", "pca", n_pc=4, bmat=b)[1:]).sum(axis=0), log_mean=False)
    raise ValueError(v)


def band_power(seg: np.ndarray, conditioned: bool) -> np.ndarray:
    """RX2's 10 to 35 Hz power per frame: raw (the STFT of the raw subcarrier mean) or conditioned (the engine's PCs 2
    to 4 of the band-passed window)."""
    from scipy import signal
    from pipeline.identify import idmax_features as F
    a = np.asarray(seg, float)
    X = F.reduce_link(F.bandpass(a, "dop", axis=0), "dop", "pca", n_pc=4, bmat=F.bandpass(a, "dop", axis=0))[1:] if conditioned \
        else (a.mean(axis=1) - a.mean())[None, :]
    f, _t, Z = signal.stft(X, fs=150.0, nperseg=32, noverlap=24, nfft=64, axis=-1, boundary=None, padded=False)
    P = (np.abs(Z) ** 2).sum(axis=0)
    return P[(f >= 10.0) & (f < 35.0)].sum(axis=0)


def maps() -> dict:
    """One pass over every recording through the engine's Extractor: the four variant maps of every window, and the
    identity-blind energy ratios of the natural identification walks."""
    from pipeline.identify import idx_bank as B
    from pipeline.identify import ixa_data as XD
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    meta = json.load(open(os.path.join(EN.ENG, "bank_T3.0", "meta.json") if TW == 3.0 else
                          os.path.join(EN.bank_dir(TW), "meta.json")))["passes"]
    names = json.load(open(EN.DEV_NAMES))
    vm = {v: [] for v in VARIANTS}
    walk_power = []
    k = 0
    for rec in B.recordings():
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        ex = XD.Tap(T=TW, layout="id_spot" if rec["kind"] == "idcap" else "home", names=names)
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            m = meta[k]
            t0 = float(q["t_start"])
            lim = t0 + TW + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            ex.press(t0, path=m["engine_path"], info={"features": False})
            (_w, td, A, _x), = ex.poll(lim)
            assert abs(td - m["t_dec"]) < 1e-9
            for v in VARIANTS:
                vm[v].append(np.stack([variant_map(A[li], v) for li in range(3)]))
            if rec["kind"] == "idcap" and rec["block"] == "natural":
                walk_power.append({"row": k, "session": rec["session"], "raw": float(np.median(band_power(A[1], False))),
                                   "conditioned": float(np.median(band_power(A[1], True)))})
            k += 1
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k}", flush=True)
    assert k == len(meta)
    os.makedirs(OUT, exist_ok=True)
    for v in VARIANTS:
        assert not os.path.exists(os.path.join(OUT, MAPS(v))), "never overwritten"
        pickle.dump(vm[v], open(os.path.join(OUT, MAPS(v)), "wb"))
    # the empty idspot recordings, per Room B day (3 s windows), raw and conditioned
    emp = {}
    for day, d in (("B1", "session_01"), ("B2", "session_02")):
        raw, con = [], []
        for p in sorted(glob.glob(os.path.join("runs", "identify", "dc2_src_relabelled", "identification", d, "*_empty_idspot_RX2.bin"))):
            t, a, _r, _c = XD.EN_link(p)
            from pipeline.identify.id19_bank import _interp_cols
            for s in np.arange(t.min() + 1.0, t.max() - 4.0, 3.0):
                seg = _interp_cols(np.arange(s, s + 3.0, 1.0 / 150.0), t, a)
                raw.append(float(np.median(band_power(seg, False))))
                con.append(float(np.median(band_power(seg, True))))
        emp[day] = {"raw": float(np.median(raw)), "conditioned": float(np.median(con)), "n_windows": len(raw)}
    rat = {"raw": [], "conditioned": []}
    for w in walk_power:
        other = "B1" if w["session"] == "B2" else "B2"           # the training day's empty room
        for kind in rat:
            rat[kind].append(w[kind] / emp[other][kind])
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "variants": DESC, "n_windows": k,
           "energy_over_empty_rx2_10_35hz": {kind: {"median_ratio": round(float(np.median(v)), 3),
                                                    "frac_above_2": round(float(np.mean(np.array(v) > 2)), 3), "n": len(v)}
                                             for kind, v in rat.items()},
           "empty_room": emp, "seconds": round(time.time() - t_all, 1)}
    json.dump(res, open(os.path.join(OUT, "maps.json" if TW == 3.0 else f"maps_T{TW:.1f}.json"), "w"), indent=1)
    print(json.dumps(res["energy_over_empty_rx2_10_35hz"], indent=1), flush=True)
    return res


def train(v: str, held: str, device=None) -> str:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    from pipeline.identify import idz_run as ZR
    out = os.path.join(OUT, "models", f"{v}_loso_{held}")
    if os.path.exists(os.path.join(out, "meta_cnn.json")):
        return out
    bank = L.load(os.path.join(EN.ENG, "bank_T3.0"))
    vm = pickle.load(open(os.path.join(OUT, f"maps_{v}.pkl"), "rb"))
    bank["maps"], bank["W"] = vm, [C.windows(m) for m in vm]
    tr = np.flatnonzero(bank["a"]["session"] != held)
    cfg = {"bank": os.path.join(EN.ENG, "bank_T3.0"), "cols": "v2", "layout": False, "fn": False, "ablation": v, "maps": DESC[v]}
    Z.train(bank, tr, out, cfg, parts=("cnn",), device=device or ZR.device(), log=print)
    return out


class CnnOnly:
    """The engine's three CNN components (`engine.Session`'s arithmetic) for a CNN-only model directory."""

    def __init__(self, md: str, device: str):
        from pipeline.identify import idw_core as W
        self.meta = json.load(open(os.path.join(md, "meta_cnn.json")))
        self.device = device
        self.norm, self.nets = {}, {}
        for chan in (None, 0, 1, 2):
            tag = "cnn3" if chan is None else f"cnn_link{chan}"
            self.norm[tag] = pickle.load(open(os.path.join(md, f"{tag}_norm.pkl"), "rb"))
            for s in self.meta["seeds"]:
                self.nets[(tag, s)] = W._load_net(os.path.join(md, f"{tag}_seed{s}.pt"), 3 if chan is None else 1).to(device)

    def _input(self, tag, Wl, paths):
        from pipeline.identify import idz_core as Z
        chan = None if tag == "cnn3" else int(tag[-1])
        nd = self.norm[tag]
        Xs, ds, ps = [], [], []
        for k, (w, p) in enumerate(zip(Wl, paths)):
            Xs.append(w if chan is None else w[:, chan:chan + 1])
            ds.append(np.full(len(w), nd["dir_map"][1 if p.endswith("_rev") else 0]))
            ps.append(np.full(len(w), k))
        Xw, dw, pw = np.concatenate(Xs), np.concatenate(ds).astype(int), np.concatenate(ps).astype(int)
        return Z.apply_norm_keyed(Xw, dw, None, nd["st"]), dw, pw

    def score(self, Wl: list, paths: list, which: list, layouts: list = None) -> dict:
        """The three components for windows `which` (replay positions), each with AdaBN on every earlier window of its
        own layout (engine v3's fix L; `layouts` None: every earlier window, as engine v2)."""
        out = {"cnn": {}, "cnn_prior": {}, "cnn_perlink_prior": {}}
        for k in which:
            res = {}
            for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
                Xw, dw, pw = self._input(tag, [Wl[k]], [paths[k]])
                same = [j for j in range(k) if layouts is None or layouts[j] == layouts[k]]
                Xo = self._input(tag, [Wl[j] for j in same], [paths[j] for j in same]) if same else None
                plain, adapted = [], []
                for s in self.meta["seeds"]:
                    net = self.nets[(tag, s)]
                    if tag == "cnn3":
                        plain.append(C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, self.device)))
                    netr = C.adabn(net, Xo[0], Xo[1], self.device) if Xo is not None else net
                    adapted.append(C.normalise_logp(C.pass_logp(netr, Xw, dw, pw, 1, 6, self.device)))
                if tag == "cnn3":
                    res["cnn"] = C.normalise_logp(np.mean(plain, axis=0))[0]
                    res["cnn_prior"] = C.normalise_logp(np.mean(adapted, axis=0))[0]
                else:
                    res[tag] = C.normalise_logp(np.mean(adapted, axis=0))[0]
            res["cnn_perlink_prior"] = C.normalise_logp(sum(res.pop(f"cnn_link{c}") for c in range(3))[None, :])[0]
            for c in out:
                out[c][k] = res[c]
        return out


def score(device: str = "mps") -> dict:
    from pipeline.identify import idw_eval as EV
    from pipeline.identify import idx_loso as L
    t_all = time.time()
    meta = json.load(open(os.path.join(EN.bank_dir(TW), "meta.json")))["passes"]
    CL = np.array(L.CLASSES)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "variants": DESC, "information_only": True, "engine_version": EN.ENGINE_VERSION,
           "feature_components": f"engine v{EN.ENGINE_VERSION}'s, from its replays (window {TW} s); the variant CNNs were trained on 3 s "
                                 "variant maps (as the engine's own CNNs were) and are scored on the engine's window"}
    base_ok, var_ok, who_all, blk_all = [], {v: [] for v in VARIANTS}, [], []
    for held in ("B2", "B1"):
        z = np.load(os.path.join(EN.ENG, "replays", f"{EN.model_name(f'loso_{held}')}_{held}_T{TW:.1f}.npz"))
        te, paths = z["te"], [str(p) for p in z["path_used"]]
        which = [k for k, i in enumerate(te) if meta[int(i)]["kind"] == "idcap"]
        who = np.array([meta[int(te[k])]["anon"] for k in which])
        blk = np.array([meta[int(te[k])]["block"] for k in which])
        feat = sum(z[f"c_{c}"][which] for c in ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior"))
        base_ok.append(CL[z["ensemble"][which].argmax(1)] == who)
        who_all.append(who)
        blk_all.append(blk)
        for v in VARIANTS:
            vm = pickle.load(open(os.path.join(OUT, MAPS(v)), "rb"))
            Wl = [C.windows(vm[int(i)]) for i in te]
            lays = ["id_spot" if meta[int(i)]["kind"] == "idcap" else "home" for i in te] if EN.ENGINE_VERSION >= 3 else None
            sc = CnnOnly(os.path.join(OUT, "models", f"{v}_loso_{held}"), device).score(Wl, paths, which, lays)
            cnn = sum(np.array([sc[c][k] for k in which]) for c in sc)
            ens = C.normalise_logp(feat + cnn)
            var_ok[v].append(CL[ens.argmax(1)] == who)
            print(f"{time.strftime('%H:%M:%S')} {v} to{held} scored", flush=True)
    who, blk = np.concatenate(who_all), np.concatenate(blk_all)
    b = np.concatenate(base_ok).astype(float)
    res["engine"] = {k: EV._boot(b[blk == k], who[blk == k]) for k in ("natural", "slow", "fast")}
    for v in VARIANTS:
        o = np.concatenate(var_ok[v]).astype(float)
        res[v] = {k: EV._boot(o[blk == k], who[blk == k]) for k in ("natural", "slow", "fast")}
        res[v]["variant_minus_engine_natural"] = EV.paired(o[blk == "natural"], b[blk == "natural"], who[blk == "natural"])
    res["seconds"] = round(time.time() - t_all, 1)
    json.dump(res, open(os.path.join(OUT, f"ablation{EN.SUFFIX}.json"), "w"), indent=1)
    print(json.dumps({v: (res[v]["natural"]["pct"], res[v]["variant_minus_engine_natural"]["pct"], res[v]["variant_minus_engine_natural"]["ci95"])
                      for v in VARIANTS}, indent=1), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("maps", "train", "score"))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    x = ap.parse_args()
    if x.what == "maps":
        maps()
    elif x.what == "train":
        for v in VARIANTS:
            for held in ("B2", "B1"):
                if not x.args or f"{v}_{held}" in x.args:
                    train(v, held)
    else:
        score(x.device)
    sys.exit(0)
