"""ixr_train. Identification across days and rooms on tracking's split (`runs/identify/engine/PREREG_XROOM_V4.md`):
engine v4's recipe on an explicit list of training sessions and walk kinds, saved to
`runs/identify/engine/models/xr_*_v4` with a manifest. No v4 model, bank or replay is changed.

The recipe is the loso_*_v4 models' own:
- the five feature components on `bank_T4.0_v4` (columns v2; the pace column is the Wi-Fi speed at the model's alpha),
  as `iv4_build.models`;
- the three CNN components (cnn3 and cnn_link0 to 2; seeds 0 to 2; 6,000 steps; mps) on the 3.0 s maps of `bank_T3.0`,
  as the loso_* CNN weights that v2, v3 and v4 copied unchanged. That bank was removed in the 6 Oct cleanup; it is
  recovered byte for byte from git (3f3612b4^) into `runs/identify/engine/xroom/recovered/bank_T3.0`.

    PYTHONPATH=. python3 -m pipeline.identify.ixr_train recover          # the removed inputs, from git, hash-checked
    PYTHONPATH=. python3 -m pipeline.identify.ixr_train check-config     # A1, A2, B1, B2 must give loso_A3_v4's config and rows
    PYTHONPATH=. python3 -m pipeline.identify.ixr_train substitution     # every non-training row replaced: identical training
    PYTHONPATH=. python3 -m pipeline.identify.ixr_train train xr_AB [--device mps]
    PYTHONPATH=. python3 -m pipeline.identify.ixr_train audit xr_AB      # every file the training opened, mapped to sessions

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
import time

import numpy as np

from pipeline.identify import engine as EN

T = 4.0
SESSIONS = ("A1", "A2", "A3", "B1", "B2")
TEST = ("A3", "B2")
XR = os.path.join(EN.ENG, "xroom")
REC = os.path.join(XR, "recovered")
BANK3 = os.path.join(REC, "bank_T3.0")
MODELS = os.path.join(EN.ENG, "models")
SRC = "3f3612b4^"
RECOVER = {**{f"bank_T3.0/{f}": f"runs/identify/engine/bank_T3.0/{f}"
              for f in ("meta.json", "features.npy", "feature_names.json", "maps.pkl", "build.json")},
           **{f"two_press/final_loso_{s}_causal.npz": f"runs/identify/audit/outputs/final_loso_{s}_causal.npz" for s in SESSIONS},
           "window_gait_alpha.json": "runs/identify/window_gait/alpha.json"}
SPECS = {
    "xr_AB": {"sessions": ("A1", "A2", "B1"), "kinds": ("track", "idcap"), "n": 600,
              "role": "tracking's deployed split"},
    "xr_ABtrk": {"sessions": ("A1", "A2", "B1"), "kinds": ("track",), "n": 360,
                 "role": "tracking's deployed split, tracking walks only"},
    "xr_A": {"sessions": ("A1", "A2"), "kinds": ("track", "idcap"), "n": 240,
             "role": "Room A only: tracking's zero-shot split"},
    "xr_B1": {"sessions": ("B1",), "kinds": ("track", "idcap"), "n": 360,
              "role": "Room B only: same room for B2, zero-shot for A3"},
}
ORDER = ("xr_AB", "xr_A", "xr_ABtrk", "xr_B1")
PROVENANCE = ("derived_from", "code_commit_at_training", "plan", "use")
log = lambda s: print(s, flush=True)  # noqa: E731


def name_of(base: str) -> str:
    return EN.model_name(base)


def meta4() -> list:
    return json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]


def rows(sessions, kinds) -> np.ndarray:
    m = meta4()
    return np.array([i for i, p in enumerate(m) if p["session"] in sessions and p["kind"] in kinds], int)


def fitted_alpha(sessions, kinds) -> tuple:
    """The PLAN rule (window and gait): the alpha with the smallest median |detected end - end press| on the training
    sessions' identification walks. B1's walks alone: the recorded fold toB2 (trained on B1); both Room B days: the
    lean-in record the Room A folds use; no identification walks: 0.5 (the addendum's rule)."""
    idc = sorted(s for s in sessions if s.startswith("B")) if "idcap" in kinds else []
    if not idc:
        return 0.5, "no identification walks in training: 0.5, the value every Room A fold uses (the addendum's rule)"
    if idc == ["B1"]:
        f = json.load(open(os.path.join(REC, "window_gait_alpha.json")))["folds"]["toB2"]
        assert f["trained_on"] == "B1"
        return f["alpha"], ("the PLAN rule on B1's 240 identification walks: median |end error| "
                            f"{f['median_and_p75_abs_error_s']} by alpha (window_gait/alpha.json, fold toB2, recovered)")
    if idc == ["B1", "B2"]:
        f = json.load(open(os.path.join("runs", "identify", "lean_in", "alpha_A.json")))
        return f["alpha"], "the PLAN rule on both Room B days' identification walks (lean_in/alpha_A.json)"
    raise ValueError(idc)


def cfg(alpha: float) -> dict:
    from pipeline.identify import ide_train as IT
    assert not IT.gs_adopted()
    return {"bank": EN.bank_dir(T), "cols": "v2", "layout": False, "fn": False, "amp_norm": False, "engine_T": T,
            "engine_version": EN.ENGINE_VERSION, "alpha": alpha}


def cfg_cnn() -> dict:
    return {"bank": BANK3, "cols": "v2", "layout": False, "fn": False, "amp_norm": False, "engine_T": 3.0}


def manifest(model: str, sessions, kinds, tr: np.ndarray, alpha: float, alpha_rule: str, role: str) -> dict:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    m = meta4()
    by = {}
    for i in tr:
        k = f"{m[int(i)]['session']} {m[int(i)]['kind']}"
        by[k] = by.get(k, 0) + 1
    return {"model": model, "engine_version": EN.ENGINE_VERSION, "T_s": T, "alpha": alpha,
            "training_sessions": sorted({m[int(i)]["session"] for i in tr}), "n_train": int(len(tr)), "gs_adopted": False,
            "config": cfg(alpha), "bank": EN.bank_dir(T),
            "derived_from": "engine v4's recipe (the loso_*_v4 models): feature components as iv4_build.models, CNN "
                            "components on bank_T3.0's 3.0 s maps as loso_*'s (the weights every v4 model carries)",
            "code_commit_at_training": head, "plan": "runs/identify/engine/PREREG_XROOM_V4.md",
            "use": "the cross-room evaluation (replays of A3 and B2 only)", "label": EN.LABEL,
            "training_kinds": sorted(kinds), "training_walks": by, "role": role, "alpha_rule": alpha_rule,
            "cnn_bank": BANK3, "cnn_bank_source": f"git {SRC}:runs/identify/engine/bank_T3.0 (recovered byte for byte)"}


# ------------------------------------------------------------------ recovery of the removed inputs

def _blob(rev_path: str) -> str:
    return subprocess.run(["git", "rev-parse", f"{SRC}:{rev_path}"], capture_output=True, text=True, check=True).stdout.strip()


def recover() -> dict:
    out = {"source": SRC, "files": {}}
    for dst, src in RECOVER.items():
        p = os.path.join(REC, dst)
        blob = _blob(src)
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            data = subprocess.run(["git", "cat-file", "blob", blob], capture_output=True, check=True).stdout
            open(p, "wb").write(data)
        got = subprocess.run(["git", "hash-object", p], capture_output=True, text=True, check=True).stdout.strip()
        assert got == blob, (p, got, blob)
        out["files"][dst] = {"from": src, "blob": blob, "bytes": os.path.getsize(p)}
    for s in ("bank_T3.0_x", "bank_T3.0_v3"):     # the maps and meta the v2 and v3 CNN lineage carried are the same blobs
        for f in ("maps.pkl", "meta.json"):
            assert _blob(f"runs/identify/engine/{s}/{f}") == out["files"][f"bank_T3.0/{f}"]["blob"], (s, f)
    out["same_maps_and_meta_as"] = ["bank_T3.0_x", "bank_T3.0_v3"]
    m3 = json.load(open(os.path.join(BANK3, "meta.json")))["passes"]
    m4 = meta4()
    assert len(m3) == len(m4) == 1019
    for p, q in zip(m3, m4):
        assert (p["session"], p["kind"], p["block"], p["anon"], p["path"]) == (q["session"], q["kind"], q["block"], q["anon"], q["path"])
        assert abs(p["t_start"] - q["t_start"]) < 1e-6
    out["row_order_equal_to_bank_T4.0_v4"] = True
    json.dump(out, open(os.path.join(REC, "RECOVERED.json"), "w"), indent=1)
    log(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------ the config check (no training)

def check_config() -> dict:
    ref_dir = os.path.join(MODELS, "loso_A3_v4")
    ref = json.load(open(os.path.join(ref_dir, "manifest.json")))
    ref_meta = json.load(open(os.path.join(ref_dir, "meta_feat_cnn.json")))
    sessions, kinds = ("A1", "A2", "B1", "B2"), ("track", "idcap")
    tr = rows(sessions, kinds)
    a, rule = fitted_alpha(sessions, kinds)
    man = manifest("loso_A3_v4", sessions, kinds, tr, a, rule, "check")
    res = {"rows_equal_loso_A3_v4_train_rows": bool(np.array_equal(tr, np.load(os.path.join(ref_dir, "train_rows.npy")))),
           "config_fields": {k: {"wrapper": man["config"].get(k), "loso_A3_v4": v, "equal": man["config"].get(k) == v}
                             for k, v in ref["config"].items()},
           "config_same_keys": sorted(man["config"]) == sorted(ref["config"]),
           "manifest_fields": {}, "provenance_fields_differ_by_construction": {}}
    for k, v in ref.items():
        if k in PROVENANCE:
            res["provenance_fields_differ_by_construction"][k] = {"wrapper": man[k], "loso_A3_v4": v}
        else:
            res["manifest_fields"][k] = {"equal": man[k] == v, "wrapper": man[k], "loso_A3_v4": v}
    res["training_meta"] = {k: {"wrapper": w, "loso_A3_v4": ref_meta[k], "equal": w == ref_meta[k]}
                            for k, w in (("seeds", [0, 1, 2]), ("steps", 6000), ("device", "mps"), ("cfg", cfg(a)),
                                         ("parts", ["feat", "cnn"]))}
    res["PASSED"] = (res["rows_equal_loso_A3_v4_train_rows"] and res["config_same_keys"]
                     and all(v["equal"] for v in res["config_fields"].values())
                     and all(v["equal"] for v in res["manifest_fields"].values())
                     and all(v["equal"] for v in res["training_meta"].values()))
    res["models"] = {}
    for base in ORDER:
        sp = SPECS[base]
        trb = rows(sp["sessions"], sp["kinds"])
        ab, rb = fitted_alpha(sp["sessions"], sp["kinds"])
        ses = sorted({meta4()[int(i)]["session"] for i in trb})
        res["models"][name_of(base)] = {"n_train": int(len(trb)), "expected": sp["n"], "sessions": ses, "alpha": ab,
                                        "alpha_rule": rb, "no_test_session": not set(ses) & set(TEST)}
        res["PASSED"] = res["PASSED"] and len(trb) == sp["n"] and not set(ses) & set(TEST)
    res["built"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(res, open(os.path.join(XR, "check_config.json"), "w"), indent=1)
    log(json.dumps(res, indent=1))
    log("PASSED" if res["PASSED"] else "FAILED")
    return res


# ------------------------------------------------------------------ the open trace

_TRACE = {"f": None}


def start_trace(path: str) -> None:
    """Every file opened from here on, by a Python audit hook (it cannot be removed; the process ends after training)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _TRACE["f"] = open(path, "w")

    def hook(event, args):
        f = _TRACE["f"]
        if event == "open" and f is not None and args and isinstance(args[0], (str, bytes, os.PathLike)):
            f.write(f"{os.path.abspath(os.fsdecode(args[0]))}\t{args[1]}\n")
    sys.addaudithook(hook)


def stop_trace() -> None:
    f, _TRACE["f"] = _TRACE["f"], None
    if f is not None:
        f.close()


def trace_path(base: str) -> str:
    return os.path.join(XR, "audit", f"{name_of(base)}_open_trace.tsv")


# ------------------------------------------------------------------ training

def train(base: str, device: str = "mps", out: str = None, steps: int = 6000, seeds=(0, 1, 2), trace: str = None) -> str:
    """One model, the recipe above. `out`, `steps`, `seeds` and `trace` differ from the defaults only in the smoke test."""
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    sp = SPECS[base]
    out = out or os.path.join(MODELS, name_of(base))
    if os.path.exists(os.path.join(out, "meta_feat_cnn.json")):
        raise SystemExit(f"{out} is complete: never overwritten")
    assert json.load(open(os.path.join(REC, "RECOVERED.json")))["row_order_equal_to_bank_T4.0_v4"]
    tr = rows(sp["sessions"], sp["kinds"])
    assert len(tr) == sp["n"], (len(tr), sp["n"])
    assert not {meta4()[int(i)]["session"] for i in tr} & set(TEST)
    a, rule = fitted_alpha(sp["sessions"], sp["kinds"])
    assert a == 0.5          # the bank's `speed_m_s` is the Wi-Fi speed at alpha 0.5 (iv4_build.merge)
    start_trace(trace or trace_path(base))
    t_all = time.time()
    log(f"{time.strftime('%H:%M:%S')} {name_of(base)}: {len(tr)} rows of {sp['sessions']} ({sp['kinds']}), alpha {a}, on {device}")
    bank3 = L.load(BANK3)
    Z.train(bank3, tr, out, cfg_cnn(), parts=("cnn",), seeds=tuple(seeds), steps=steps, device=device, log=log)
    t_cnn = time.time() - t_all
    del bank3
    bank4 = L.load(EN.bank_dir(T))
    t1 = time.time()
    Z.train(bank4, tr, out, cfg(a), parts=("feat",), log=log)
    t_feat = time.time() - t1
    meta = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_train": int(len(tr)), "seeds": list(seeds), "steps": steps,
            "device": device, "cfg": cfg(a), "parts": ["feat", "cnn"], "seconds": round(time.time() - t_all, 1),
            "feature_components": f"trained on the v4 bank (4.0 s windows; speed at alpha {a})",
            "cnn_components": "trained on bank_T3.0's 3.0 s maps (recovered from git), as the loso_* CNN weights every "
                              "v4 model carries",
            "seconds_cnn_training": round(t_cnn, 1), "seconds_feature_training": round(t_feat, 1)}
    json.dump(meta, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    json.dump(manifest(name_of(base), sp["sessions"], sp["kinds"], tr, a, rule, sp["role"]),
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    stop_trace()
    log(f"{time.strftime('%H:%M:%S')} {name_of(base)} saved ({time.time() - t_all:.0f} s)")
    return out


# ------------------------------------------------------------------ the leak audit

def audit(base: str, out_dir: str = None, trace: str = None, save: bool = True) -> dict:
    """Every file the training opened, mapped to sessions; the training rows' sessions and kinds."""
    sp = SPECS[base]
    repo = os.path.abspath(".")
    out_dir = os.path.abspath(out_dir or os.path.join(MODELS, name_of(base)))
    trace = trace or trace_path(base)
    banks = {os.path.abspath(BANK3): "bank_T3.0 (recovered)", os.path.abspath(EN.bank_dir(T)): "bank_T4.0_v4"}
    tr = np.load(os.path.join(out_dir, "train_rows.npy"))
    m = meta4()
    used = sorted({m[int(i)]["session"] for i in tr})
    kinds = sorted({m[int(i)]["kind"] for i in tr})
    files, bad = {}, []
    seen = set()
    for line in open(trace):
        p, mode = line.rstrip("\n").split("\t")
        if p in seen:
            continue
        seen.add(p)
        rel = os.path.relpath(p, repo)
        if p.startswith(out_dir + os.sep):
            files[os.path.relpath(p, repo) if p.startswith(repo) else p] = f"this model's own output ({mode})"
            continue
        if not p.startswith(repo + os.sep):
            continue                                            # the interpreter and its libraries
        if rel.endswith((".py", ".pyc")) and (rel.startswith("pipeline") or "__pycache__" in rel):
            files[rel] = "code"
        elif os.path.dirname(p) in banks:
            files[rel] = f"{banks[os.path.dirname(p)]}: all five sessions' rows on disk; training indexed rows of {used} only"
        elif p.startswith(out_dir + os.sep):
            files[rel] = f"this model's own output ({mode})"
        elif rel == os.path.join("runs", "identify", "engine", "stage1", "result.json"):
            files[rel] = "configuration (the GS decision: not adopted)"
        elif rel in (os.path.join(REC, "RECOVERED.json"), os.path.join(REC, "window_gait_alpha.json"),
                     os.path.join("runs", "identify", "lean_in", "alpha_A.json")):
            files[rel] = "configuration (alpha record or recovery manifest)"
        elif p == os.path.abspath(trace):
            files[rel] = "the trace itself"
        else:
            sess = [s for s in SESSIONS if f"/{s}/" in f"/{rel}/" or f"session_{s[1:]}" in rel]
            files[rel] = f"UNEXPECTED ({mode}); sessions in its path: {sess or 'none'}"
            bad.append(rel)
    res = {"model": name_of(base), "training_rows": int(len(tr)), "training_sessions": used, "training_kinds": kinds,
           "rows_from_test_sessions": int(sum(m[int(i)]["session"] in TEST for i in tr)),
           "rows_as_specified": bool(np.array_equal(np.sort(tr), rows(sp["sessions"], sp["kinds"]))),
           "files_opened_in_repo": files, "unexpected": bad}
    res["PASSED"] = res["rows_from_test_sessions"] == 0 and res["rows_as_specified"] and not bad
    if save:
        json.dump(res, open(os.path.join(XR, "audit", f"{name_of(base)}_audit.json"), "w"), indent=1)
    log(json.dumps({k: v for k, v in res.items() if k != "files_opened_in_repo"}, indent=1))
    log("PASSED" if res["PASSED"] else "FAILED")
    return res


# ------------------------------------------------------------------ the substitution check

def _noised(bank: dict, keep: np.ndarray, seed: int) -> dict:
    """The bank with every row outside `keep` replaced: features and maps by noise, labels, paths and sessions
    shuffled among those rows, speeds drawn at random."""
    from pipeline.identify import idv2_core as C
    rng = np.random.default_rng(seed)
    other = np.setdiff1d(np.arange(bank["a"]["n"]), keep)
    b = dict(bank)
    b["a"] = dict(bank["a"])
    X = bank["X"].copy()
    X[other] = rng.normal(size=(len(other), X.shape[1]))
    b["X"] = X
    maps = list(bank["maps"])
    for i in other:
        maps[i] = rng.normal(size=maps[i].shape).astype(maps[i].dtype)
    b["maps"] = maps
    b["W"] = [C.windows(mp) for mp in maps]
    for k in ("anon", "path", "session"):
        v = bank["a"][k].copy()
        v[other] = rng.permutation(v[other])
        b["a"][k] = v
    sp = bank["a"]["speed_m_s"].astype(float).copy()
    sp[other] = rng.uniform(0.3, 2.0, len(other))
    b["a"]["speed_m_s"] = sp
    b["a"]["path_idx"] = bank["a"]["path_idx"].copy()
    return b


def substitution(bases=ORDER) -> dict:
    """For each model: the feature components (in full) and the CNN components (seed 0, 30 steps, CPU) trained twice,
    on the real banks and on banks whose non-training rows are replaced; every output must be identical."""
    import torch
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    bank3, bank4 = L.load(BANK3), L.load(EN.bank_dir(T))
    probe = np.arange(bank4["a"]["n"])
    res = {"what": "non-training rows replaced (features and maps by noise; labels, paths, sessions shuffled; speeds "
                   "random): feature components trained in full, CNN components seed 0 for 30 steps on CPU; outputs "
                   "compared exactly", "models": {}}
    for base in bases:
        sp = SPECS[base]
        tr = rows(sp["sessions"], sp["kinds"])
        a, _r = fitted_alpha(sp["sessions"], sp["kinds"])
        out = {}
        with tempfile.TemporaryDirectory() as d:
            for tag, b3, b4 in (("real", bank3, bank4), ("noised", _noised(bank3, tr, 1), _noised(bank4, tr, 2))):
                L.register_variant("dev", b4["X"], b4["names"])
                Z.train(b4, tr, os.path.join(d, tag), cfg(a), parts=("feat",), log=lambda s: None)
                Z.train(b3, tr, os.path.join(d, tag), cfg_cnn(), parts=("cnn",), seeds=(0,), steps=30, device="cpu",
                        log=lambda s: None)
            L.register_variant("dev", bank4["X"], bank4["names"])
            pk = Z.path_key(bank4["a"], False)
            for comp, (_h, norm, pace) in W.FEAT.items():
                Xf = Z.feature_matrix(bank4, pace, "v2")
                outs = []
                for tag in ("real", "noised"):
                    dd = pickle.load(open(os.path.join(d, tag, f"feat_{comp}.pkl"), "rb"))
                    Bm = dd["state"].transform(Xf[probe], pk[probe]) if norm == "perpath" else dd["state"].apply(Xf, pk, probe, None)
                    outs.append(dd["clf"].predict_proba(Bm))
                out[comp] = bool(np.array_equal(outs[0], outs[1]))
            for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
                s0 = torch.load(os.path.join(d, "real", f"{tag}_seed0.pt"))
                s1 = torch.load(os.path.join(d, "noised", f"{tag}_seed0.pt"))
                n0 = pickle.load(open(os.path.join(d, "real", f"{tag}_norm.pkl"), "rb"))
                n1 = pickle.load(open(os.path.join(d, "noised", f"{tag}_norm.pkl"), "rb"))
                same_norm = all(np.array_equal(n0["st"][k][j], n1["st"][k][j]) for k in n0["st"] for j in (0, 1))
                out[tag] = bool(all(torch.equal(s0[k], s1[k]) for k in s0) and same_norm and n0["dir_map"] == n1["dir_map"])
        res["models"][name_of(base)] = {"identical": out, "PASSED": all(out.values())}
        log(f"{time.strftime('%H:%M:%S')} {name_of(base)}: {out}")
    res["PASSED"] = all(v["PASSED"] for v in res["models"].values())
    res["built"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    os.makedirs(os.path.join(XR, "audit"), exist_ok=True)
    json.dump(res, open(os.path.join(XR, "audit", "substitution.json"), "w"), indent=1)
    log("PASSED" if res["PASSED"] else "FAILED")
    return res


def smoke(scratch: str) -> bool:
    """Before launch (seconds): xr_A_v4's recipe with 2 CNN steps and one seed on CPU into `scratch`, its open trace
    audited, and the saved model loaded by the engine and applied to one A3 window. Nothing under runs/ is written."""
    out, tr_p = os.path.join(scratch, "xr_A_smoke"), os.path.join(scratch, "xr_A_smoke_trace.tsv")
    train("xr_A", "cpu", out=out, steps=2, seeds=(0,), trace=tr_p)
    res = audit("xr_A", out_dir=out, trace=tr_p, save=False)
    m = meta4()
    i = next(j for j, p in enumerate(m) if p["session"] == "A3")
    X = np.load(os.path.join(EN.bank_dir(T), "features.npy"), mmap_mode="r")
    maps = pickle.load(open(os.path.join(EN.bank_dir(T), "maps.pkl"), "rb"))
    sess = EN.Session(EN.Model(out, "cpu"))
    lp = sess.classify({"features": np.asarray(X[i]), "maps": maps[i], "wifi_speed": m[i]["wifi_speed"], "path": m[i]["path"]})["ensemble"]
    log(f"engine loads the smoke model; one A3 window: {np.round(lp, 3).tolist()}")
    return bool(res["PASSED"]) and np.all(np.isfinite(lp))


if __name__ == "__main__":
    what = sys.argv[1]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
    if what == "recover":
        recover()
    elif what == "check-config":
        sys.exit(0 if check_config()["PASSED"] else 1)
    elif what == "substitution":
        sys.exit(0 if substitution(tuple(a for a in sys.argv[2:] if a in SPECS) or ORDER)["PASSED"] else 1)
    elif what == "train":
        train(sys.argv[2], dev)
    elif what == "audit":
        sys.exit(0 if audit(sys.argv[2])["PASSED"] else 1)
    elif what == "smoke":
        sys.exit(0 if smoke(sys.argv[2]) else 1)
    else:
        raise SystemExit(what)
    sys.exit(0)
