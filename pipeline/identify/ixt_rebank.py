"""ixt_rebank. Engine v2 (the cadence bug fix, `runs/identify/engine/PLAN.md` note of 2026-10-01): the v2 banks and models.

banks: one pass over every recording through the engine's own Extractor (now v2), T = 2.5, 3.0 and 3.5, B1's signal
path (no GS); the Doppler maps and decision times are asserted equal to the v1 banks' (the fix touches only the gait
features); the meta is the v1 bank's (labels, speed and direction do not depend on the cadence).
models: for every v1 engine model, the five feature components retrained on the v2 bank (`idz_core.train`, parts
"feat"; the same rows, heads and seeds), the CNN files copied unchanged, a meta and a manifest written. Nothing old is
overwritten.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_rebank banks|models
"""

from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

TS = (2.5, 3.0, 3.5)
MODELS = {"loso_A1": 3.0, "loso_A2": 3.0, "loso_A3": 3.0, "loso_B1": 3.0, "loso_B2": 3.0, "deploy_all5": 3.0,
          "T2.5_toB2": 2.5, "T2.5_toB1": 2.5, "T3.5_toB2": 3.5, "T3.5_toB1": 3.5}


def v1_bank(T):
    return os.path.join(EN.ENG, f"bank_T{T:.1f}")


def banks() -> dict:
    from pipeline.identify import idx_bank as B
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    names = json.load(open(EN.DEV_NAMES))
    meta = {T: json.load(open(os.path.join(v1_bank(T), "meta.json")))["passes"] for T in TS}
    old_maps = {T: pickle.load(open(os.path.join(v1_bank(T), "maps.pkl"), "rb")) for T in TS}
    feats = {T: [] for T in TS}
    k = 0
    for rec in B.recordings():
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = {T: EN.Extractor(T=T, layout=layout, names=names) for T in TS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + max(TS) + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if rec["kind"] == "idcap" else q["path_name"]
            for T, e in ex.items():
                e.press(t0, path=known)
                (_w, td, x), = e.poll(t0 + T + EN.CAP_S)
                m = meta[T][k]
                assert abs(m["t_start"] - t0) < 1e-6 and abs(td - m["t_dec"]) < 1e-9, (k, T)
                assert np.array_equal(x["maps"], old_maps[T][k]), (k, T)          # the maps are untouched by the fix
                assert x["wifi_speed"] == m["wifi_speed"] or (np.isnan(x["wifi_speed"]) and np.isnan(m["wifi_speed"]))
                feats[T].append(x["features"])
            k += 1
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k}, {time.time() - t_all:.0f} s", flush=True)
    out = {}
    for T in TS:
        d = EN.bank_dir(T)
        assert not os.path.exists(os.path.join(d, "features.npy")), f"{d} exists: never overwritten"
        os.makedirs(d, exist_ok=True)
        X = np.asarray(feats[T], np.float32)
        np.save(os.path.join(d, "features.npy"), X)
        for f in ("meta.json", "feature_names.json", "maps.pkl"):
            shutil.copy(os.path.join(v1_bank(T), f), os.path.join(d, f))
        old = np.load(os.path.join(v1_bank(T), "features.npy"))
        changed = int(np.sum(np.any(~np.isclose(X, old, rtol=1e-6, atol=1e-9, equal_nan=True), axis=1)))
        json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "T": T, "engine_version": EN.ENGINE_VERSION, "n_passes": k,
                   "maps_equal_v1": True, "t_dec_equal_v1": True, "windows_with_changed_features": changed,
                   "extractor": "engine.Extractor v2 (cadence fix)", "label": EN.LABEL, "seconds": round(time.time() - t_all, 1)},
                  open(os.path.join(d, "build.json"), "w"), indent=1)
        out[T] = changed
    print(json.dumps({"windows_with_changed_features": out}), flush=True)
    return out


def models() -> dict:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {}
    for base, T in MODELS.items():
        old = os.path.join(EN.ENG, "models", base)
        new = os.path.join(EN.ENG, "models", EN.model_name(base))
        if os.path.exists(os.path.join(new, "meta_feat_cnn.json")):
            out[base] = "exists"
            continue
        bank = L.load(EN.bank_dir(T))
        tr = np.load(os.path.join(old, "train_rows.npy"))
        meta_old = json.load(open(os.path.join(old, "meta_feat_cnn.json")))
        cfg = {**meta_old["cfg"], "bank": EN.bank_dir(T), "engine_version": EN.ENGINE_VERSION}
        t0 = time.time()
        Z.train(bank, tr, new, cfg, parts=("feat",), log=print)
        for f in os.listdir(old):
            if f.startswith("cnn") and (f.endswith(".pt") or f.endswith("_norm.pkl")):
                shutil.copy(os.path.join(old, f), os.path.join(new, f))
        meta = {**meta_old, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "cfg": cfg, "parts": ["feat", "cnn"],
                "feature_components": "retrained on the v2 bank", "cnn_components": f"copied unchanged from {base} (maps unchanged by the fix)",
                "seconds_feature_retraining": round(time.time() - t0, 1)}
        json.dump(meta, open(os.path.join(new, "meta_feat_cnn.json"), "w"), indent=1)
        sess = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
        man = {"model": EN.model_name(base), "engine_version": EN.ENGINE_VERSION,
               "training_sessions": sorted({sess[int(i)]["session"] for i in tr}), "n_train": int(len(tr)), "T_s": T,
               "gs_adopted": False, "config": cfg, "bank": EN.bank_dir(T), "derived_from": base,
               "code_commit_at_training": head, "plan": "runs/identify/engine/PLAN.md (note 2026-10-01: the cadence bug fix)",
               "use": "the rig's deployment model; never scores anything" if base == "deploy_all5" else "thesis figures and replays",
               "label": EN.LABEL}
        json.dump(man, open(os.path.join(new, "manifest.json"), "w"), indent=1)
        out[base] = round(time.time() - t0, 1)
        print(f"{time.strftime('%H:%M:%S')} {EN.model_name(base)}: feature components {out[base]} s", flush=True)
    return out


if __name__ == "__main__":
    {"banks": banks, "models": models}[sys.argv[1]]()
    sys.exit(0)
