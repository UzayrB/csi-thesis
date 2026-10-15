"""ilb_gpu. The best-model run's GPU work (`runs/identify/best/POA_B.md`):

- `a4cache --model M --session S`: A4's CNN components of the offset test windows (0.15 and 0.30 s, `ilb_extract tta`)
  through the shipped model: `engine.Session` in the replay's order, each walk's offset-0 window classified (it must
  equal the replay's components exactly, else BLOCKED), then its offset windows classified against the same pool, then
  the offset-0 window added (only offset 0 enters the pool). `torch.mps.empty_cache()` after each walk.
- `a4done`: every model-session's cache present and checked: writes `a4cache/DONE` (else `a4cache/FAILED`).
- `train CAND FOLD` / `score CAND FOLD` / `dev`: the GPU candidates on last night's development folds (D1 A1, D2 A2, D3
  B1; selection there only, no A3 or B2): the fold model's CNN components retrained by v4's recipe (`idz_core.train`,
  parts "cnn", 6,000 steps, seeds 0 to 2) with A2 (each training window time-stretched by a factor s ~ U(0.85, 1.15)
  about its centre with its frequency axis scaled by s, new(f, t) = old(f / s, c + (t - c) s), zeros outside, then
  augment as before), M1 (on bank_T4.0_v4's 4.0 s maps instead of bank_T3.0's) or A2M1 (both); the fold model's feature
  components copied. `dev` scores each with F7's feature components against v4+F7's development score (29.59).

    PYTHONPATH=. python3 -m pipeline.identify.ilb_gpu a4cache --model xr_AB_v4 --session A3 --device mps

Exploratory development, all data seen; selection on A3 and B2.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

BD = os.path.join("runs", "identify", "best")
A4 = os.path.join(BD, "a4cache")
REP = os.path.join(EN.ENG, "replays")
PAIRS = [(f"loso_{s}_v4", s) for s in ("A1", "A2", "A3", "B1", "B2")] + [
    (f"{m}_v4", s) for m in ("xr_AB", "xr_ABtrk", "xr_A", "xr_B1") for s in ("A3", "B2")]


def a4cache(model: str, session: str, device: str = "mps") -> str:
    bank_dir = EN.bank_dir(4.0)
    X = np.load(os.path.join(bank_dir, "features.npy"))
    maps = pickle.load(open(os.path.join(bank_dir, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(bank_dir, "meta.json")))["passes"]
    md = os.path.join(EN.ENG, "models", model)
    alpha = json.load(open(os.path.join(md, "manifest.json")))["alpha"]
    key = "wifi_speed" if alpha == 0.5 else f"wifi_speed_a{alpha}"
    z = np.load(os.path.join(REP, f"{model}_{session}_T4.0.npz"))
    tt = pickle.load(open(os.path.join(BD, "extract", "tta", f"{session}.pkl"), "rb"))
    offs = {}
    for j, (r, o) in enumerate(zip(tt["rows"], tt["offset"])):
        offs.setdefault(int(r), {})[f"{o:.2f}"] = j
    sess = EN.Session(EN.Model(md, device))
    cols = sess.m.cols
    n_all = X.shape[1]
    comps = {"0": {}, "0.15": {}, "0.30": {}}
    t0 = time.time()
    worst = 0.0
    for i, path in zip(z["te"], z["path_used"]):
        layout = "id_spot" if meta[i]["kind"] == "idcap" else "home"
        ex = {"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path), "layout": layout}
        d = sess.classify(ex)
        for c, v in d["components"].items():
            comps["0"].setdefault(c, []).append(v)
        for w in ("0.15", "0.30"):
            j = offs[int(i)][w]
            f = np.zeros(n_all, np.float64)
            f[cols] = tt["F"][j]
            exo = {"features": f, "maps": tt["maps"][j], "wifi_speed": float(tt[f"speed_{alpha}"][j]),
                   "path": str(tt["path_used"][j]), "layout": layout}
            do = sess.classify(exo)
            for c, v in do["components"].items():
                comps[w].setdefault(c, []).append(v)
        sess.add(ex)
        if device == "mps":
            import torch
            torch.mps.empty_cache()
    out = {"te": z["te"]}
    for w, cm in comps.items():
        for c, v in cm.items():
            out[f"c_{c}" if w == "0" else f"c_{c}_{w}"] = np.array(v)
    for c in ("cnn", "cnn_prior", "cnn_perlink_prior", "rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior"):
        worst = max(worst, float(np.abs(out[f"c_{c}"] - z[f"c_{c}"]).max()))
    os.makedirs(A4, exist_ok=True)
    p = os.path.join(A4, f"{model}_{session}.npz")
    np.savez(p, **out, offset0_max_abs_diff=worst)
    print(f"{time.strftime('%H:%M:%S')} {model} on {session} ({device}): {len(z['te'])} walks x 3 windows in "
          f"{time.time() - t0:.0f} s; offset 0 against the replay: max abs diff {worst:.3g}", flush=True)
    if worst > 1e-6:
        raise SystemExit(f"offset 0 does not reproduce the replay ({worst}): {model} {session} BLOCKED")
    return p


def a4done() -> bool:
    bad = []
    for model, s in PAIRS:
        p = os.path.join(A4, f"{model}_{s}.npz")
        if not os.path.exists(p):
            bad.append(f"{p} missing")
            continue
        z = np.load(p)
        if float(z["offset0_max_abs_diff"]) > 1e-6:
            bad.append(f"{p} offset 0 diff {float(z['offset0_max_abs_diff'])}")
    f = os.path.join(A4, "FAILED" if bad else "DONE")
    open(f, "w").write(json.dumps({"built": time.strftime("%Y-%m-%d %H:%M:%S"), "bad": bad}) + "\n")
    print(f, bad, flush=True)
    return not bad


# ------------------------------------------------------------------ the GPU candidates on the development folds

CANDS = ("A2", "M1", "A2M1")
MD = os.path.join(BD, "models")
DEV = os.path.join(BD, "dev")
LO, HI = 0.85, 1.15


def stretch_batch(x, s):
    """(B, C, F, T) windows, factors s (B,): new(f, t) = old(f / s, c + (t - c) s), bilinear, zeros outside (CPU)."""
    import torch
    from pipeline.identify import idv2_core as C
    B, _C, Fq, T = x.shape
    fb = torch.tensor(C.F_BINS, dtype=torch.float32)
    df = float(fb[1] - fb[0])
    fi = (fb[None, :] / s[:, None] - fb[0]) / df                       # (B, F) source frequency index
    c = (T - 1) / 2.0
    ti = c + (torch.arange(T, dtype=torch.float32)[None, :] - c) * s[:, None]   # (B, T) source time index
    gx = (2 * ti / (T - 1) - 1)[:, None, :].expand(B, Fq, T)
    gy = (2 * fi / (Fq - 1) - 1)[:, :, None].expand(B, Fq, T)
    grid = torch.stack([gx, gy], dim=-1)
    return torch.nn.functional.grid_sample(x, grid, mode="bilinear", padding_mode="zeros", align_corners=True)


def a2_augment(orig):
    def aug(x, g):
        import torch
        s = LO + (HI - LO) * torch.rand(x.shape[0], generator=g)
        y = stretch_batch(x.detach().to("cpu"), s).to(x.device)
        return orig(y, g)
    return aug


def train_cand(cand: str, f: str, device: str = "mps") -> str:
    import shutil
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    from pipeline.identify import ilp_score as PS
    from pipeline.identify import ixr_train as XT
    s, src = PS.FOLDS[f]
    out = os.path.join(MD, f"{cand}_{f}")
    assert not os.path.exists(os.path.join(out, "meta_feat_cnn.json")), f"{out} exists"
    tr = np.load(os.path.join(src, "train_rows.npy"))
    m1 = cand in ("M1", "A2M1")
    bank = L.load(EN.bank_dir(4.0) if m1 else XT.BANK3)
    cfg = XT.cfg_cnn()
    if m1:
        cfg.update({"bank": EN.bank_dir(4.0), "engine_T": 4.0})
    orig = C.augment
    if cand in ("A2", "A2M1"):
        C.augment = a2_augment(orig)
    t0 = time.time()
    try:
        Z.train(bank, tr, out, cfg, parts=("cnn",), device=device, log=print)
    finally:
        C.augment = orig
    for fn in os.listdir(src):
        if fn.startswith("feat_"):
            shutil.copy(os.path.join(src, fn), os.path.join(out, fn))
    meta = json.load(open(os.path.join(src, "meta_feat_cnn.json")))
    cm = json.load(open(os.path.join(out, "meta_cnn.json")))
    meta.update({"seeds": cm["seeds"], "steps": cm["steps"], "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "device": device,
                 "cnn_components": f"retrained ({cand}; exploratory development, all data seen)",
                 "feature_components": f"copied unchanged from {src}", "seconds_cnn_training": round(time.time() - t0, 1)})
    json.dump(meta, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    man = json.load(open(os.path.join(src, "manifest.json")))
    man.update({"model": os.path.basename(out), "derived_from": src, "candidate": cand, "plan": "runs/identify/best/POA_B.md",
                "use": "development fold only"})
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{time.strftime('%H:%M:%S')} {out} trained in {time.time() - t0:.0f} s", flush=True)
    return out


def score_cand(cand: str, f: str, device: str = "mps") -> str:
    from pipeline.identify import ilp_score as PS
    s, _src = PS.FOLDS[f]
    os.makedirs(DEV, exist_ok=True)
    p = os.path.join(DEV, f"{cand}_{f}_{s}.npz")
    np.savez(p, **PS.score(os.path.join(MD, f"{cand}_{f}"), s, device=device))
    return p


def ds_paired(lps: dict, ref: dict) -> dict:
    """DS(candidate) - DS(v4+F7) with a paired participant bootstrap (10,000 draws, seed 0, participants resampled
    jointly across the four DS cells), as last night's DS intervals (the Mastermind: point values screen, intervals
    reported)."""
    from pipeline.identify import ilc_outer as CO
    from pipeline.identify import ilp_cand as PC
    counts = CO.boot_counts()
    who = PC.bank()["a"]["anon"]
    new, old, pn, po = [], [], [], []
    for f, cells in (("D1", ["path"]), ("D2", ["path"]), ("D3", ["path", "natural"])):
        te = PC.FD[f]["te"]
        a, b_ = PC.accuracy(lps[f], te), PC.accuracy(ref[f], te)
        for c in cells:
            m = PC.cells(f, te)[c]
            for ok, B, P in ((a, new, pn), (b_, old, po)):
                k, n = CO.per_part(ok[m], who[te][m])
                B.append((counts @ k) / (counts @ n))
                P.append(k.sum() / n.sum())
    d = np.mean(new, axis=0) - np.mean(old, axis=0)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"pct": round(100 * float(np.mean(pn) - np.mean(po)), 2), "ci95": [round(100 * float(lo), 2), round(100 * float(hi), 2)]}


def dev() -> dict:
    """Each GPU candidate's CNN components with F7's feature components on the three folds: the development score
    against v4+F7's (the CNN components of v4); passes only above 29.59 (POA_B)."""
    from pipeline.identify import ilc_dev as CD
    from pipeline.identify import ilp_cand as PC
    from pipeline.identify import ilp_score as PS
    PC.load_folds()
    base = {f: {c: PC.FD[f][f"c_{c}"].copy() for c in PC.CNNC} for f in PC.FD}
    res = {"label": "exploratory development, all data seen; selection on A1, A2 and B1 (development folds)",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "threshold": 29.59, "configs": {}}
    v4 = PC.ds_of({f: PC.ensemble({c: PC.FD[f][f"c_{c}"] for c in PC.FEATC + PC.CNNC}) for f in PC.FD})
    res["configs"]["v4"] = v4
    ref_lps = PC.run_config(CD.config(["F7"]))
    res["configs"]["v4+F7"] = PC.ds_of(ref_lps)
    for cand in CANDS:
        ok = True
        for f in PC.FD:
            p = os.path.join(DEV, f"{cand}_{f}_{PS.FOLDS[f][0]}.npz")
            if not os.path.exists(p):
                ok = False
                break
            z = np.load(p)
            assert np.array_equal(z["te"], PC.FD[f]["te"])
            for c in PC.CNNC:
                PC.FD[f][f"c_{c}"] = z[f"c_{c}"]
        if ok:
            lps = PC.run_config(CD.config(["F7"]))
            r = PC.ds_of(lps)
            r["guard"] = bool(all(r[f"B1_{b}"] >= v4[f"B1_{b}"] - 5 for b in ("natural", "slow", "fast")))
            r["passes"] = bool(r["DS"] > res["threshold"] and r["guard"])
            r["DS_minus_v4F7"] = ds_paired(lps, ref_lps)
            res["configs"][f"{cand}+F7"] = r
        for f in PC.FD:
            for c in PC.CNNC:
                PC.FD[f][f"c_{c}"] = base[f][c]
    json.dump(res, open(os.path.join(DEV, "gpu_dev.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


def gate() -> None:
    """The Mastermind's rule (POA_B, 11:00): A2M1 runs only if A2 or M1 alone passes the development screen (DS above
    29.59, the development guard holding). Appends A2M1's steps, or the skip, to the GPU queue; writes dev/gate.json."""
    res = dev()
    c = res["configs"]
    passed = [k for k in ("A2+F7", "M1+F7") if c.get(k, {}).get("passes")]
    missing = [k for k in ("A2+F7", "M1+F7") if k not in c]
    run = bool(passed) and not missing
    g = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "passed": passed, "missing": missing, "run_A2M1": run,
         "A2+F7": c.get("A2+F7"), "M1+F7": c.get("M1+F7"), "v4+F7": c["v4+F7"], "v4": c["v4"],
         "rule": "A2M1 only if A2 or M1 alone has DS above 29.59 with the development guard (POA_B, 11:00)"}
    json.dump(g, open(os.path.join(DEV, "gate.json"), "w"), indent=1)
    PY = "/opt/anaconda3/bin/python3"
    L = [f"# A2M1 gate ({time.strftime('%H:%M:%S')}): {'RUN, passed: ' + ', '.join(passed) if run else 'SKIPPED (neither A2 nor M1 passed' + (', missing ' + ', '.join(missing) if missing else '') + ')'}"]
    if run:
        for f in ("D1", "D2", "D3"):
            L += [f"STEP tr_A2M1_{f} 12 0.7 0.5 {PY} -m pipeline.identify.ilb_gpu train A2M1 {f} --device mps",
                  f"STEP expect_tr_A2M1_{f} 6 0.7 0.5 {PY} -m pipeline.identify.ilp_expect model {MD}/A2M1_{f}",
                  f"STEP sc_A2M1_{f} 12 0.7 0.5 {PY} -m pipeline.identify.ilb_gpu score A2M1 {f} --device mps"]
        L += [f"STEP gpu_dev 6 0.7 0.5 {PY} -m pipeline.identify.ilb_gpu dev",
              f"STEP expect_gpu_dev 6 0.7 0.5 {PY} -m pipeline.identify.ilp_expect file {DEV}/gpu_dev.json"]
    L.append("ENDBLOCK GPU block B (GPU candidates, development screen)")
    with open(os.path.join(BD, "STEPS_GPU"), "a") as f:
        f.write("\n".join(L) + "\n")
    print(json.dumps(g, indent=1), "\n".join(L), sep="\n", flush=True)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "a4cache":
        a4cache(sys.argv[sys.argv.index("--model") + 1], sys.argv[sys.argv.index("--session") + 1],
                sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps")
    elif what == "a4done":
        sys.exit(0 if a4done() else 1)
    elif what in ("train", "score"):
        dev_ = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
        (train_cand if what == "train" else score_cand)(sys.argv[2], sys.argv[3], dev_)
    elif what == "dev":
        dev()
    elif what == "gate":
        gate()
    sys.exit(0)
