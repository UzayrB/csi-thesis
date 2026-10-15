"""ixt_shuffle. The teaching-pack brief's shuffled-label control (`runs/identify/engine/PLAN.md`, the teaching note, C2).

- full: the whole engine trained for "to B2" with participant labels permuted at row level within each training
  session (class counts kept; numpy seed 0), then B2 replayed through the engine;
- null: seeds 1 to 20, the five feature components only on permuted labels, B2 re-scored causally; the statistic is
  the feature-only ensemble (the sum of the five feature components) on B2's natural walks, against the real one.

From 1 Oct, engine v2 (the cadence bug fix): `full` retrains the five feature components of `shuffled_loso_B2_x` on the v2
bank with the same permutation (seed 0) and copies the shuffled CNNs from `shuffled_loso_B2` (the maps are unchanged by
the fix), then replays B2; `null` re-scores on the v2 bank and replay. Outputs `shuffled_full_x.json`, `shuffled_null_x.json`;
the v1 files are kept as superseded.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_shuffle full|null [--device mps]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L

OUT = os.path.join("runs", "identify", "teaching")
BANK = EN.bank_dir(EN.T_S)
SUF = EN.SUFFIX
M = f"shuffled_loso_B2{SUF}"
CL = np.array(L.CLASSES)


def permuted(a_anon, a_session, train_sessions, seed) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = np.array(a_anon, copy=True)
    for s in train_sessions:
        idx = np.flatnonzero(a_session == s)
        y[idx] = y[idx][rng.permutation(len(idx))]
    return y


def natural_mask(meta, te):
    return np.array([meta[int(i)]["kind"] == "idcap" and meta[int(i)]["block"] == "natural" for i in te])


def full(device: str = "mps") -> dict:
    from pipeline.identify import idz_core as Z
    from pipeline.identify import ide_replay as RP
    t_all = time.time()
    bank = L.load(BANK)
    a = bank["a"]
    tr = np.flatnonzero(a["session"] != "B2")
    real = np.array(a["anon"], copy=True)
    a["anon"] = permuted(a["anon"], a["session"], ("A1", "A2", "A3", "B1"), 0)
    for s in ("A1", "A2", "A3", "B1"):                       # class counts kept within every training session
        m = a["session"] == s
        assert sorted(a["anon"][m]) == sorted(real[m]) and np.mean(a["anon"][m] == real[m]) < 0.5
    out = os.path.join(OUT, "models", M)
    v1 = os.path.join(OUT, "models", "shuffled_loso_B2")
    cfg = {"bank": BANK, "cols": "v2", "layout": False, "fn": False, "amp_norm": False, "engine_T": EN.T_S,
           "labels": "permuted within each training session, numpy seed 0", "engine_version": EN.ENGINE_VERSION}
    if not os.path.exists(os.path.join(out, "meta_feat_cnn.json")):
        assert np.array_equal(np.load(os.path.join(v1, "train_rows.npy")), tr)
        Z.train(bank, tr, out, cfg, parts=("feat",), log=print)
        for f in os.listdir(v1):
            if f.startswith("cnn") and (f.endswith(".pt") or f.endswith("_norm.pkl")):
                shutil.copy(os.path.join(v1, f), os.path.join(out, f))
        m1 = json.load(open(os.path.join(v1, "meta_feat_cnn.json")))
        json.dump({**m1, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "cfg": cfg, "parts": ["feat", "cnn"],
                   "feature_components": f"retrained on the {EN.SUFFIX} bank (T {EN.T_S} s), permuted labels (seed 0)",
                   "cnn_components": "copied unchanged from shuffled_loso_B2 (trained on the same permuted labels; maps unchanged by the fix)"},
                  open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    json.dump({"model": M, "engine_version": EN.ENGINE_VERSION, "training_sessions": ["A1", "A2", "A3", "B1"], "labels": cfg["labels"],
               "purpose": "the shuffled-label control; never used by the app", "T_s": EN.T_S,
               "alpha": 0.5 if EN.ENGINE_VERSION >= 4 else None}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    dec = RP.replay("B2", out, EN.T_S, False, device, RP.direction_mode())
    meta = json.load(open(os.path.join(BANK, "meta.json")))["passes"]
    bank_rows = RP.load_bank(EN.T_S, False, v2=True)["index"]
    te = np.array([bank_rows[("B2", round(d["t0"], 6))] for d in dec])
    who = np.array([meta[int(i)]["anon"] for i in te])
    ens = np.array([d["ensemble"] for d in dec])
    nat = natural_mask(meta, te)
    ok = (CL[ens.argmax(1)] == who).astype(float)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": M, "engine_version": EN.ENGINE_VERSION, "train_sessions": ["A1", "A2", "A3", "B1"],
           "test_session": "B2", "calibration": "causal", "scored_set": "B2 natural identification walks",
           "natural_accuracy": EV._boot(ok[nat], who[nat]), "all_b2_windows_accuracy": EV._boot(ok, who), "chance_pct": 16.67,
           "predicted_share_natural_pct": {c: round(100 * float(np.mean(CL[ens[nat].argmax(1)] == c)), 1) for c in CL},
           "seconds": round(time.time() - t_all, 1)}
    np.savez(os.path.join(OUT, f"shuffled_full_B2{SUF}.npz"), te=te, ensemble=ens)
    json.dump(res, open(os.path.join(OUT, f"shuffled_full{SUF}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


def null_layout(n: int = 20) -> dict:
    """Engine v3 onwards (fix L: calibration pools per layout): the null re-scored with the screen's per-layout feature
    path (`ils_feat`, whose components equal the engine's replay, checked here), permuted labels as `null`."""
    from pipeline.identify import ili_stack as LS
    from pipeline.identify import ils_feat as FT
    t_all = time.time()
    d = LS.data()
    g = LS.arm(f"T{EN.T_S:.1f}", "B2")
    cfg = {"G": g["features"].astype(np.float64)[:, EN.v2_columns(d["names"])], "pace": g["wifi_speed"], "pool": "layout"}
    rep = np.load(os.path.join(EN.ENG, "replays", f"{EN.model_name('loso_B2')}_B2_T{EN.T_S:.1f}.npz"))
    te = rep["te"]
    assert np.array_equal(te, d["rep"]["B2"]["te"])
    meta = json.load(open(os.path.join(BANK, "meta.json")))["passes"]
    nat = natural_mask(meta, te)
    who = d["a"]["anon"][te]
    FEATS = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior")

    def feat_only_acc(feat):
        f = C.normalise_logp(sum(feat[c] for c in FEATS))
        return float(np.mean(CL[f[nat].argmax(1)] == who[nat]))
    real = feat_only_acc({c: rep[f"c_{c}"] for c in FEATS})
    anchor = FT.rescore(FT.train(d, "B2", cfg), d, "B2", cfg)
    anchor_diff = max(float(np.abs(anchor[c] - rep[f"c_{c}"]).max()) for c in FEATS)
    assert anchor_diff < 1e-6, anchor_diff
    nulls = []
    for seed in range(1, n + 1):
        dd = dict(d)
        dd["a"] = dict(d["a"])
        dd["a"]["anon"] = permuted(d["a"]["anon"], d["a"]["session"], ("A1", "A2", "A3", "B1"), seed)
        nulls.append(feat_only_acc(FT.rescore(FT.train(dd, "B2", cfg), dd, "B2", cfg)))
        print(f"{time.strftime('%H:%M:%S')} null seed {seed}: {100 * nulls[-1]:.2f}", flush=True)
    p = (1 + sum(x >= real for x in nulls)) / (n + 1)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "statistic": "feature-only ensemble (sum of the five feature components), "
           "B2 natural identification walks, causal per-layout pools", "train_sessions": ["A1", "A2", "A3", "B1"], "test_session": "B2",
           "real_pct": round(100 * real, 2), "null_pct": [round(100 * x, 2) for x in nulls],
           "null_mean_pct": round(100 * float(np.mean(nulls)), 2), "null_max_pct": round(100 * float(np.max(nulls)), 2),
           "p_value": round(p, 4), "n_permutations": n, "chance_pct": 16.67, "engine_version": EN.ENGINE_VERSION,
           "anchor_max_abs_diff_vs_replay": anchor_diff, "seconds": round(time.time() - t_all, 1)}
    json.dump(res, open(os.path.join(OUT, f"shuffled_null{SUF}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


def null(n: int = 20) -> dict:
    if EN.ENGINE_VERSION >= 3:
        return null_layout(n)
    from pipeline.identify import ixa_score as S
    t_all = time.time()
    B = S.base(SUF)
    a, G = B["a"], B["G"]
    rep = B["rep"]["B2"]
    te = rep["te"]
    nat = natural_mask(B["meta"], te)
    who = a["anon"][te]
    tr = np.flatnonzero(a["session"] != "B2")
    pace = a["wifi_speed"].astype(float)

    def feat_only_acc(feat):
        f = C.normalise_logp(sum(feat[c] for c in S.W.FEAT))
        return float(np.mean(CL[f[nat].argmax(1)] == who[nat])), f
    real, _ = feat_only_acc({c: rep[f"c_{c}"] for c in S.W.FEAT})
    nulls = []
    for seed in range(1, n + 1):
        aa = dict(a)
        aa["anon"] = permuted(a["anon"], a["session"], ("A1", "A2", "A3", "B1"), seed)
        feat = S.rescore(S.train_feat(G, None, pace, aa, tr), G, None, pace, rep)
        nulls.append(feat_only_acc(feat)[0])
        print(f"{time.strftime('%H:%M:%S')} null seed {seed}: {100 * nulls[-1]:.2f}", flush=True)
    p = (1 + sum(x >= real for x in nulls)) / (n + 1)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "statistic": "feature-only ensemble (sum of the five feature components), "
           "B2 natural identification walks, causal", "train_sessions": ["A1", "A2", "A3", "B1"], "test_session": "B2",
           "real_pct": round(100 * real, 2), "null_pct": [round(100 * x, 2) for x in nulls],
           "null_mean_pct": round(100 * float(np.mean(nulls)), 2), "null_max_pct": round(100 * float(np.max(nulls)), 2),
           "p_value": round(p, 4), "n_permutations": n, "chance_pct": 16.67, "engine_version": EN.ENGINE_VERSION,
           "seconds": round(time.time() - t_all, 1)}
    json.dump(res, open(os.path.join(OUT, f"shuffled_null{SUF}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("full", "null"))
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    x = ap.parse_args()
    full(x.device) if x.what == "full" else null()
    sys.exit(0)
