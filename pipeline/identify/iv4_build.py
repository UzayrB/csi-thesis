"""iv4_build. Engine v4 (`runs/identify/engine/PLAN.md`, the note of 2026-10-02 00:23): its bank and models, beside v3's
(never overwritten).

bank: one pass over every recording through the engine's own Extractor (now v4, T = 4.0 s), once per end-detector alpha
(0.5 and 0.2); every window's features, maps, decision time and Wi-Fi speed are asserted equal to the lean-in screen's
4.0 s arm (`runs/identify/window_gait/bank/a<alpha>/`); the meta is v3's, with v4's decision time, the speed at alpha 0.5
(`wifi_speed`, `speed_m_s`) and at 0.2 (`wifi_speed_a0.2`).
models: for every v3 model but the T-sensitivity ones, the five feature components retrained on the v4 bank (the same
rows, heads and seeds) with its alpha's speed as the pace column; the CNN files copied from the `_v3` model; alpha in the
manifest.

    PYTHONPATH=. python3 -m pipeline.identify.iv4_build bank --session B2      # per session (parallel, at most five)
    PYTHONPATH=. python3 -m pipeline.identify.iv4_build merge
    PYTHONPATH=. python3 -m pipeline.identify.iv4_build models
    PYTHONPATH=. python3 -m pipeline.identify.iv4_build check     # the replays against the lean-in screen's prediction

Development evaluation, all data seen.
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

V3 = "_v3"
T = 4.0
ALPHAS = (0.5, 0.2)
SCREEN = os.path.join("runs", "identify", "window_gait", "bank")
MODELS = {"loso_A1": 0.5, "loso_A2": 0.5, "loso_A3": 0.5, "loso_B1": 0.2, "loso_B2": 0.5, "deploy_all5": 0.5}


def v3_bank():
    return os.path.join(EN.ENG, f"bank_T3.0{V3}")


def bank(session: str, limit: int = None) -> str:
    from pipeline.identify import idx_bank as B
    from pipeline.io.capture_logger import read_capture_file
    assert EN.ENGINE_VERSION == 4 and EN.SUFFIX == "_v4" and EN.T_S == T
    names = json.load(open(EN.DEV_NAMES))
    meta = json.load(open(os.path.join(v3_bank(), "meta.json")))["passes"]
    screen = {a: pickle.load(open(os.path.join(SCREEN, f"a{a}", f"{session}.pkl"), "rb"))["T4.0"] for a in ALPHAS}
    pos_of = {a: {r: j for j, r in enumerate(screen[a]["rows"])} for a in ALPHAS}
    out = {"rows": [], "features": [], "maps": [], "t_dec": [], "wifi": {a: [] for a in ALPHAS}, "walk_end_s": {a: [] for a in ALPHAS}}
    t_all, k, n = time.time(), 0, 0
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda z: z["t_start"])
        if rec["session"] != session:
            k += len(qs)
            continue
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = {a: EN.Extractor(T=T, layout=layout, names=names, alpha=a) for a in ALPHAS}
        pos = {L: 0 for L in EN.LINKS}
        for q in qs:
            t0 = float(q["t_start"])
            assert abs(meta[k]["t_start"] - t0) < 1e-6
            lim = t0 + T + EN.CAP_S
            for L in EN.LINKS:
                m_ = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:m_])
                pos[L] = m_
            known = None if rec["kind"] == "idcap" else q["path_name"]
            res = {}
            for a, e in ex.items():
                e.press(t0, path=known)
                (_w, td, x), = e.poll(lim)
                res[a] = (td, x)
            x5 = res[0.5][1]
            for a in ALPHAS:
                td, x = res[a]
                j = pos_of[a][k]
                s = screen[a]
                assert np.array_equal(x["features"], s["features"][j], equal_nan=True), (k, a, "features")
                assert np.array_equal(x["maps"], s["maps"][j]), (k, a, "maps")
                assert abs((td - t0) - s["dec_s"][j]) < 1e-9, (k, a, "t_dec")
                assert (x["wifi_speed"] == s["wifi_speed"][j]) or (np.isnan(x["wifi_speed"]) and np.isnan(s["wifi_speed"][j])), (k, a, "wifi")
                out["wifi"][a].append(x["wifi_speed"])
                out["walk_end_s"][a].append(x["walk_end_s"])
            assert x5["path"] == meta[k]["engine_path"], (k, "direction")
            out["rows"].append(k)
            out["features"].append(x5["features"])
            out["maps"].append(x5["maps"])
            out["t_dec"].append(res[0.5][0])
            k += 1
            n += 1
            if limit and n >= limit:
                break
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {n}, {time.time() - t_all:.0f} s", flush=True)
        if limit and n >= limit:
            break
    p = os.path.join(EN.ENG, "v4_parts", f"{session}{'_test' if limit else ''}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump(out, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} {session}: {n} windows equal to the screen's 4.0 s arm at both alphas", flush=True)
    return p


def merge() -> dict:
    """The five sessions' parts into bank_T4.0_v4 (never overwriting)."""
    d = EN.bank_dir(T)
    assert not os.path.exists(os.path.join(d, "features.npy")), f"{d} exists: never overwritten"
    parts = [pickle.load(open(os.path.join(EN.ENG, "v4_parts", f"{s}.pkl"), "rb")) for s in ("A1", "A2", "A3", "B1", "B2")]
    rows = np.concatenate([p["rows"] for p in parts])
    o = np.argsort(rows)
    assert np.array_equal(rows[o], np.arange(len(rows)))
    X = np.asarray([x for p in parts for x in p["features"]], np.float32)[o]
    maps = [m for p in parts for m in p["maps"]]
    maps = [maps[i] for i in o]
    meta = json.load(open(os.path.join(v3_bank(), "meta.json")))
    tdec = np.concatenate([p["t_dec"] for p in parts])[o]
    w = {a: np.concatenate([p["wifi"][a] for p in parts])[o] for a in ALPHAS}
    we = {a: np.concatenate([p["walk_end_s"][a] for p in parts])[o] for a in ALPHAS}
    for i, m in enumerate(meta["passes"]):
        m.update({"T": T, "t_dec": float(tdec[i]), "wifi_speed": float(w[0.5][i]), "speed_m_s": float(w[0.5][i]),
                  "wifi_speed_a0.2": float(w[0.2][i]), "walk_end_s": float(we[0.5][i]), "walk_end_s_a0.2": float(we[0.2][i]),
                  "speed_note": "engine v4: Wi-Fi speed on the walking span (end detector, alpha 0.5; _a0.2 for alpha 0.2)"})
    os.makedirs(d, exist_ok=True)
    np.save(os.path.join(d, "features.npy"), X)
    pickle.dump(maps, open(os.path.join(d, "maps.pkl"), "wb"))
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
    shutil.copy(os.path.join(v3_bank(), "feature_names.json"), os.path.join(d, "feature_names.json"))
    rec = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "T": T, "engine_version": EN.ENGINE_VERSION, "n_passes": int(len(X)),
           "equal_to_lean_in_screen": "features, maps, decision times and both speeds asserted equal on every window",
           "alphas": list(ALPHAS), "label": EN.LABEL}
    json.dump(rec, open(os.path.join(d, "build.json"), "w"), indent=1)
    print(rec, flush=True)
    return rec


def models() -> dict:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    assert EN.ENGINE_VERSION == 4 and EN.SUFFIX == "_v4"
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {}
    meta_all = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
    for base, a in MODELS.items():
        old = os.path.join(EN.ENG, "models", base + V3)
        new = os.path.join(EN.ENG, "models", EN.model_name(base))
        if os.path.exists(os.path.join(new, "meta_feat_cnn.json")):
            out[base] = "exists"
            continue
        bank = L.load(EN.bank_dir(T))
        if a != 0.5:
            bank["a"]["speed_m_s"] = np.array([m[f"wifi_speed_a{a}"] for m in meta_all], float)
        tr = np.load(os.path.join(old, "train_rows.npy"))
        meta_old = json.load(open(os.path.join(old, "meta_feat_cnn.json")))
        cfg = {**meta_old["cfg"], "bank": EN.bank_dir(T), "engine_version": EN.ENGINE_VERSION, "engine_T": T, "alpha": a}
        t0 = time.time()
        Z.train(bank, tr, new, cfg, parts=("feat",), log=print)
        for f in os.listdir(old):
            if f.startswith("cnn") and (f.endswith(".pt") or f.endswith("_norm.pkl")):
                shutil.copy(os.path.join(old, f), os.path.join(new, f))
        meta = {**meta_old, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "cfg": cfg, "parts": ["feat", "cnn"],
                "feature_components": f"retrained on the v4 bank (4.0 s windows; speed at alpha {a})",
                "cnn_components": f"copied unchanged from {base + V3} (the lean-in stack kept v3's CNN weights)",
                "seconds_feature_retraining": round(time.time() - t0, 1)}
        json.dump(meta, open(os.path.join(new, "meta_feat_cnn.json"), "w"), indent=1)
        man = {"model": EN.model_name(base), "engine_version": EN.ENGINE_VERSION, "T_s": T, "alpha": a,
               "training_sessions": sorted({meta_all[int(i)]["session"] for i in tr}), "n_train": int(len(tr)),
               "gs_adopted": False, "config": cfg, "bank": EN.bank_dir(T), "derived_from": base + V3,
               "code_commit_at_training": head,
               "plan": "runs/identify/engine/PLAN.md (note 2026-10-02 00:23: engine v4, the 4.0 s window)",
               "use": "the rig's deployment model; never scores anything" if base == "deploy_all5" else "thesis figures and replays",
               "label": EN.LABEL}
        json.dump(man, open(os.path.join(new, "manifest.json"), "w"), indent=1)
        out[base] = round(time.time() - t0, 1)
        print(f"{time.strftime('%H:%M:%S')} {EN.model_name(base)} (alpha {a}): feature components {out[base]} s", flush=True)
    return out


def check() -> dict:
    """Every v4 fold replay against the lean-in screen's prediction of the same ensemble: B2 and B1 against the cached
    T4.0 ensembles (`runs/identify/lean_in/ens/`), the Room A folds against `ili_stack.stack_ensemble("T4.0", {})`.
    Decisions must agree walk for walk and the ensembles to 1e-6."""
    from pipeline.identify import ili_stack as LS
    out = {}
    pred = {s: dict(np.load(os.path.join(LS.ENS, f"T4.0_{s}.npz"))) for s in ("B2", "B1")}
    ensA, _w = LS.stack_ensemble("T4.0", {}, folds=("A1", "A2", "A3"))
    pred.update({s: {"ensemble": ensA[s]} for s in ensA})
    for s in ("B2", "B1", "A1", "A2", "A3"):
        r = np.load(os.path.join(EN.ENG, "replays", f"{EN.model_name('loso_' + s)}_{s}_T{T:.1f}.npz"))
        e, p = r["ensemble"], pred[s]["ensemble"]
        same = int((e.argmax(1) == p.argmax(1)).sum())
        out[s] = {"n": int(len(e)), "same_decision": same, "max_abs_diff": float(np.abs(e - p).max()),
                  "features_equal_bank": int(r["features_equal_bank"].sum()), "maps_equal_bank": int(r["maps_equal_bank"].sum())}
        print(f"{s}: {same} of {len(e)} decisions as predicted; max |diff| {out[s]['max_abs_diff']:.2e}; "
              f"features equal {out[s]['features_equal_bank']}, maps equal {out[s]['maps_equal_bank']}", flush=True)
    out["PASSED"] = all(v["same_decision"] == v["n"] and v["max_abs_diff"] < 1e-6 for v in out.values())
    out["label"] = EN.LABEL
    json.dump(out, open(os.path.join(EN.ENG, "v4_prediction_check.json"), "w"), indent=1)
    print("PASSED" if out["PASSED"] else "FAILED", flush=True)
    return out


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "bank":
        bank(sys.argv[sys.argv.index("--session") + 1], int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None)
    elif what == "merge":
        merge()
    elif what == "check":
        check()
    else:
        models()
    sys.exit(0)
