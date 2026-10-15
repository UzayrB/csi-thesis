"""ilc_outer. The combine run's outer test (Uzayr's prompt of 10 Oct; `runs/identify/combine/PREREG_C.md`): for each
configuration, the five feature components of nine models retrained with its change (loso_A1 to loso_B2, xr_AB,
xr_ABtrk, xr_A, xr_B1: each model's own rows, cfg, seeds and speed column), scored by the feature-side scorer in the replay's
order; the CNN components are the shipped replays' own (the CNNs are reused). The scorecard, Z (the three zero-shot
cells), D (the ten cross-day cells), the paired participant bootstrap and the verdicts.

    PYTHONPATH=. python3 -m pipeline.identify.ilc_outer reproduce          # C4: v4 through this path = every v4 figure
    PYTHONPATH=. python3 -m pipeline.identify.ilc_outer score --config F3  # C5 (needs runs/identify/combine/C5_GO)
    PYTHONPATH=. python3 -m pipeline.identify.ilc_outer summarise          # the scorecard, Z, D, verdicts, tables

Exploratory development, all data seen.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilc_dev as CD
from pipeline.identify import ilp_cand as PC
from pipeline.identify import idw_eval as EV
from pipeline.identify import ixr_eval as XE

CB = CD.CB
OUTD = os.path.join(CB, "outer")
REP = os.path.join(EN.ENG, "replays")
GO = os.path.join(CB, "C5_GO")
MODELS = {f"loso_{s}": (f"loso_{s}_v4", [s]) for s in ("A1", "A2", "A3", "B1", "B2")} | {
    "xr_AB": ("xr_AB_v4", ["A3", "B2"]), "xr_ABtrk": ("xr_ABtrk_v4", ["A3", "B2"]), "xr_A": ("xr_A_v4", ["A3", "B2"]),
    "xr_B1": ("xr_B1_v4", ["A3", "B2"])}
ZERO = [("xr_A", "B2", "path"), ("xr_A", "B2", "natural"), ("xr_B1", "A3", "path")]
CROSS = [("loso", "*", "natural"), ("loso", "*", "path"), ("xr_AB", "A3", "path"), ("xr_AB", "B2", "path"),
         ("xr_AB", "B2", "natural"), ("xr_A", "A3", "path"), ("xr_B1", "B2", "path"), ("xr_B1", "B2", "natural"),
         ("xr_ABtrk", "A3", "path"), ("xr_ABtrk", "B2", "path")]
GUARD = [("loso", "*", "natural"), ("loso", "*", "slow"), ("loso", "*", "fast")]
EXTRA = [("xr_A", "B2", "slow"), ("xr_A", "B2", "fast")]
V4_FIGURES = {"xr_A|B2|path": 23.33, "xr_A|B2|natural": 23.33, "xr_B1|A3|path": 30.0, "loso|*|natural": 37.78,
              "loso|*|path": 30.67, "xr_AB|A3|path": 30.0, "xr_AB|B2|path": 22.5, "xr_AB|B2|natural": 25.0,
              "xr_A|A3|path": 23.33, "xr_B1|B2|path": 22.5, "xr_B1|B2|natural": 28.33, "xr_ABtrk|A3|path": 25.0,
              "xr_ABtrk|B2|path": 30.83, "loso|*|slow": 29.17, "loso|*|fast": 30.25,
              "S0|loso|*|natural": 38.33, "S0|loso|*|path": 30.17, "S0|loso|*|slow": 17.5, "S0|loso|*|fast": 16.81,
              "top2": 62.78, "group2": 72.33, "loso|B1|natural": 41.67, "loso|B2|natural": 30.0, "loso|A2|path": 35.83}


def key(c) -> str:
    return "|".join(c)


def mdir(model: str) -> str:
    return os.path.join(EN.ENG, "models", model)


def speed_col(model: str) -> np.ndarray:
    a = json.load(open(os.path.join(mdir(model), "manifest.json")))["alpha"]
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    return np.array([m["wifi_speed" if a == 0.5 else f"wifi_speed_a{a}"] for m in meta], float), a


def f7_extra(tr: np.ndarray, alpha: float) -> dict:
    parts = [np.load(os.path.join(CB, "extract", "f7", f"{s}.npz")) for s in ("A1", "A2", "A3", "B1", "B2")]
    rows = np.concatenate([p["rows"] for p in parts])
    keep = np.isin(rows, tr)
    return {"rows": rows[keep], "F": np.concatenate([p["F"] for p in parts])[keep],
            "speed": np.concatenate([p[f"speed_{alpha}"] for p in parts])[keep]}


def configs_of(dev: dict) -> dict:
    """v4, the six singles, the primary (greedy) and the stack if it differs; duplicates kept once."""
    out = {"v4": [], "F3": ["F3"], "F7": ["F7"], "CNN": "CNN", "NP": ["NP"], "F4": ["F4"], "F5": ["F5"]}
    prim = dev["primary"].split("+")
    if dev["primary"] not in out:
        out[dev["primary"]] = prim
    if dev["stack"] not in out:
        out[dev["stack"]] = dev["stack"].split("+")
    return out


def ens_multi(ids, model: str, sessions: list, flags: list) -> dict:
    """{session: ensemble log-probabilities} of configuration `ids` for one shipped model (trained once)."""
    b = PC.bank()
    zs = {s: np.load(os.path.join(REP, f"{model}_{s}_T4.0.npz")) for s in sessions}
    cnn = {s: {c: z[f"c_{c}"] for c in PC.CNNC} for s, z in zs.items()}
    fds = {s: {"te": z["te"], "path_used": z["path_used"],
               "layout": np.where(b["kind"][z["te"]] == "idcap", "id_spot", "home")} for s, z in zs.items()}
    if ids == "CNN":
        return {s: PC.ensemble(cnn[s]) for s in sessions}
    tr = np.load(os.path.join(mdir(model), "train_rows.npy"))
    v, alpha = speed_col(model)
    if not ids:
        feats = PC.load_feat(mdir(model))
        return {s: PC.ensemble(PC.score_feat(feats, b["F"], v, fds[s], {}) | cnn[s]) for s in sessions}
    cfg = CD.config(ids)
    if cfg.get("icc_k") and len(np.unique(b["a"]["session"][tr])) < 2:
        cfg.pop("icc_k")
        flags.append(f"{model}: F4 needs two training days; dropped (v4's columns) on this one-day model")
    F, _ = PC.transform(cfg, tr)
    opt = {k: cfg[k] for k in ("by_layout", "shrink_k", "head_params") if k in cfg}
    models = PC.train_feat(F, v, tr, opt, extra=f7_extra(tr, alpha) if cfg.get("f7") else None)
    return {s: PC.ensemble(PC.score_feat(models, F, v, fds[s], opt) | cnn[s], cfg.get("weights")) for s in sessions}


def correct_all(ids, flags: list) -> dict:
    """{model|session: (te, correct, log-probabilities)} for every model and test session."""
    out = {}
    for m, (model, sessions) in MODELS.items():
        lps = ens_multi(ids, model, sessions, flags)
        for s in sessions:
            z = np.load(os.path.join(REP, f"{model}_{s}_T4.0.npz"))
            out[f"{m}|{s}"] = (z["te"], PC.accuracy(lps[s], z["te"]), lps[s])
        print(f"{time.strftime('%H:%M:%S')} {model}: {sessions}", flush=True)
    return out


def cell_rows(c, store: dict) -> tuple:
    """(rows, correct, log-probabilities) of a scorecard cell: (model, session or "*", kind)."""
    b = PC.bank()
    m, s, kind = c
    parts = []
    keys = [f"loso_{x}|{x}" for x in ("A1", "A2", "A3", "B1", "B2")] if m == "loso" else [f"{m}|{s}"]
    for k in keys:
        te, ok, lp = store[k]
        msk = (b["kind"][te] == "track") if kind == "path" else ((b["kind"][te] == "idcap") & (b["block"][te] == kind))
        parts.append((te[msk], ok[msk], lp[msk]))
    return tuple(np.concatenate([p[i] for p in parts]) for i in range(3))


def s0_cell(c) -> np.ndarray:
    """S0's correctness on a cell: xr cells and loso path walks as ixr_eval (an LDA on press speed trained on the model's
    own rows); loso identification walks as eval_v4 (trained on the other Room B day's identification walks)."""
    a = XE.labels()
    b = PC.bank()
    m, s, kind = c
    out = []
    keys = [x for x in ("A1", "A2", "A3", "B1", "B2")] if m == "loso" else [s]
    for x in keys:
        model = f"loso_{x}_v4" if m == "loso" else MODELS[m][0]
        z = np.load(os.path.join(REP, f"{model}_{x}_T4.0.npz"))
        te = z["te"]
        msk = (b["kind"][te] == "track") if kind == "path" else ((b["kind"][te] == "idcap") & (b["block"][te] == kind))
        if not msk.any():
            continue
        if m == "loso" and kind != "path":
            other = "B1" if x == "B2" else "B2"
            tr = np.flatnonzero((a["session"] == other) & (a["kind"] == "idcap"))
        else:
            tr = np.load(os.path.join(mdir(model), "train_rows.npy"))
        lp = XE.lda_one(a, "press_speed_m_s", tr, te[msk])
        out.append(XE.correct(lp, a["anon"][te[msk]]))
    return np.concatenate(out)


def ranking(lp: np.ndarray, who: np.ndarray) -> dict:
    """eval_v4's single_top2 and group_size_2 (idw_eval.deployment) on the given walks."""
    CLs = np.array(PC.CLASSES)
    order = np.argsort(-lp, axis=1)
    top2 = np.array([who[i] in CLs[order[i, :2]] for i in range(len(who))], float)
    subsets = list(itertools.combinations(range(6), 2))
    g2 = np.array([np.mean([S[int(np.argmax(lp[i, list(S)]))] == PC.CLASSES.index(who[i])
                            for S in subsets if PC.CLASSES.index(who[i]) in S]) for i in range(len(who))])
    return {"top2": top2, "group2": g2}


def figures(store: dict) -> dict:
    """The scorecard's point figures for one configuration (for the reproduction check)."""
    b = PC.bank()
    out = {}
    for c in ZERO + CROSS + GUARD + EXTRA:
        rows, ok, _lp = cell_rows(c, store)
        out[key(c)] = round(100 * float(ok.mean()), 2)
    for c in [("loso", "*", "natural"), ("loso", "*", "path"), ("loso", "*", "slow"), ("loso", "*", "fast")]:
        out["S0|" + key(c)] = round(100 * float(s0_cell(c).mean()), 2)
    rows, ok, lp = cell_rows(("loso", "*", "natural"), store)
    rk = ranking(lp, b["a"]["anon"][rows])
    out["top2"] = EV._boot(rk["top2"], b["a"]["anon"][rows])["pct"]
    out["group2"] = EV._boot(rk["group2"], b["a"]["anon"][rows])["pct"]
    for x, kind in (("B1", "natural"), ("B2", "natural"), ("A2", "path")):
        te, okk, _ = store[f"loso_{x}|{x}"]
        msk = (b["kind"][te] == "track") if kind == "path" else ((b["kind"][te] == "idcap") & (b["block"][te] == kind))
        out[f"loso|{x}|{kind}"] = round(100 * float(okk[msk].mean()), 2)
    return out


def save(name: str, store: dict, flags: list) -> str:
    os.makedirs(OUTD, exist_ok=True)
    p = os.path.join(OUTD, f"{name}.npz")
    flat = {}
    for k, (te, ok, lp) in store.items():
        flat[f"{k}|te"], flat[f"{k}|ok"], flat[f"{k}|lp"] = te, ok, lp
    np.savez(p, **flat)
    json.dump({"config": name, "flags": flags, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": CD.LABEL},
              open(os.path.join(OUTD, f"{name}.json"), "w"), indent=1)
    return p


def load(name: str) -> dict:
    z = np.load(os.path.join(OUTD, f"{name}.npz"))
    keys = sorted({k.rsplit("|", 1)[0] for k in z.files})
    return {k: (z[f"{k}|te"], z[f"{k}|ok"], z[f"{k}|lp"]) for k in keys}


def reproduce() -> bool:
    """C4: v4 through this path: ensembles equal the replays (1e-9) and every scorecard figure equals the v4 figure."""
    flags = []
    store = correct_all([], flags)
    diffs = {}
    for k, (te, ok, lp) in store.items():
        m, s = k.split("|")
        z = np.load(os.path.join(REP, f"{MODELS[m][0]}_{s}_T4.0.npz"))
        diffs[k] = float(np.abs(lp - z["ensemble"]).max())
    fig = figures(store)
    mism = {k: (fig.get(k), v) for k, v in V4_FIGURES.items() if fig.get(k) != v}
    res = {"ensemble_max_abs_diff": diffs, "figures": fig, "expected": V4_FIGURES, "mismatches": mism}
    res["PASSED"] = max(diffs.values()) <= 1e-9 and not mism
    os.makedirs(os.path.join(CB, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(CB, "checks", "v4_reproduction.json"), "w"), indent=1)
    save("v4", store, flags)
    print(json.dumps({"max_diff": max(diffs.values()), "mismatches": mism, "PASSED": res["PASSED"]}, indent=1), flush=True)
    return res["PASSED"]


def score(name: str) -> str:
    if not os.path.exists(GO):
        raise SystemExit("C5 is held: no runs/identify/combine/C5_GO (the Mastermind relays Uzayr's answer first)")
    dev = json.load(open(os.path.join(CB, "dev.json")))
    ids = configs_of(dev)[name]
    flags = []
    p = save(name, correct_all(ids, flags), flags)
    print(f"{time.strftime('%H:%M:%S')} {name}: scored ({p}); flags {flags}", flush=True)
    return p


# ------------------------------------------------------------------ the scorecard, Z, D and the verdicts

def boot_counts(n_boot=10000, seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    counts = np.zeros((n_boot, 6))
    np.add.at(counts, (np.repeat(np.arange(n_boot), 6), rng.integers(0, 6, (n_boot, 6)).ravel()), 1)
    return counts


def per_part(ok: np.ndarray, who: np.ndarray) -> tuple:
    return (np.array([ok[who == p].sum() for p in PC.CLASSES]), np.array([(who == p).sum() for p in PC.CLASSES]))


def summarise() -> dict:
    dev = json.load(open(os.path.join(CB, "dev.json")))
    cfgs = configs_of(dev)
    b = PC.bank()
    who_all = b["a"]["anon"]
    counts = boot_counts()
    v4 = load("v4")
    res = {"label": CD.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "primary": dev["primary"], "configs": {},
           "n_configurations": len(cfgs) - 1}
    s0 = {key(c): s0_cell(c) for c in ZERO + CROSS + GUARD + EXTRA}
    for name in cfgs:
        if not os.path.exists(os.path.join(OUTD, f"{name}.npz")):
            continue
        st = load(name)
        rec = {"cells": {}, "flags": json.load(open(os.path.join(OUTD, f"{name}.json")))["flags"]}
        boots = {"Z": [], "D": []}
        for group, cells in (("zero-shot", ZERO), ("cross-day", CROSS), ("guard", GUARD[1:]), ("extra", EXTRA)):
            for c in cells:
                rows, ok, _ = cell_rows(c, st)
                rows0, ok0, _ = cell_rows(c, v4)
                assert np.array_equal(rows, rows0)
                w = who_all[rows]
                d = {"group": group, "n": int(len(rows)), "new": EV._boot(ok, w), "v4": EV._boot(ok0, w),
                     "S0": EV._boot(s0[key(c)], w), "new_minus_v4": XE.paired(ok, ok0, w)}
                rec["cells"][key(c)] = d
                if group in ("zero-shot", "cross-day"):
                    boots["Z" if group == "zero-shot" else "D"].append((per_part(ok, w), per_part(ok0, w)))
        rows, _ok, lp = cell_rows(("loso", "*", "natural"), st)
        _r0, _o0, lp0 = cell_rows(("loso", "*", "natural"), v4)
        w = who_all[rows]
        rk, rk0 = ranking(lp, w), ranking(lp0, w)
        rec["ranking"] = {m: {"new": EV._boot(rk[m], w), "v4": EV._boot(rk0[m], w), "new_minus_v4": XE.paired(rk[m], rk0[m], w)}
                          for m in ("top2", "group2")}
        for g in ("Z", "D"):
            new = np.mean([(counts @ a_[0]) / (counts @ a_[1]) for a_, _b in boots[g]], axis=0)
            old = np.mean([(counts @ b_[0]) / (counts @ b_[1]) for _a, b_ in boots[g]], axis=0)
            pt_new = np.mean([a_[0].sum() / a_[1].sum() for a_, _b in boots[g]])
            pt_old = np.mean([b_[0].sum() / b_[1].sum() for _a, b_ in boots[g]])
            lo, hi = np.percentile(new - old, [2.5, 97.5])
            rec[g] = {"new": round(100 * float(pt_new), 2), "v4": round(100 * float(pt_old), 2),
                      "minus_v4": round(100 * float(pt_new - pt_old), 2), "ci95": [round(100 * float(lo), 2), round(100 * float(hi), 2)]}
        guard_ok = all(rec["cells"][key(c)]["new"]["pct"] >= rec["cells"][key(c)]["v4"]["pct"] - 5
                       for c in [("loso", "*", "natural")] + GUARD[1:]) if ("loso|*|natural" in rec["cells"]) else False
        rec["guard"] = bool(guard_ok)
        z, dd = rec["Z"], rec["D"]
        if name == "v4":
            rec["verdict"] = "reference"
        elif z["ci95"][0] > 0 and dd["ci95"][0] > 0 and guard_ok:
            rec["verdict"] = "BETTER"
        elif z["minus_v4"] > 0 and dd["minus_v4"] > 0 and guard_ok:
            rec["verdict"] = "HIGHER, NOT SEPARABLE"
        else:
            rec["verdict"] = "NOT BETTER"
        if name not in ("v4", dev["primary"]):
            rec["verdict_note"] = f"chosen on A3 and B2, {len(cfgs) - 1} configurations tried"
        elif name == dev["primary"]:
            rec["verdict_note"] = "confirmatory (the primary, fixed on A1, A2 and B1 before any look)"
        res["configs"][name] = rec
    json.dump(res, open(os.path.join(CB, "outer.json"), "w"), indent=1, default=str)
    open(os.path.join(CB, "outer_tables.md"), "w").write(tables(res))
    print(tables(res)[:3000], flush=True)
    return res


def _ci(d) -> str:
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def tables(res: dict) -> str:
    out = ["| configuration | Z (minus v4 [95 %]) | D (minus v4 [95 %]) | guard | verdict |", "|---|---|---|---|---|"]
    for n, r in res["configs"].items():
        out.append(f"| {n}{' (primary)' if n == res['primary'] else ''} | {r['Z']['new']:.2f} ({r['Z']['minus_v4']:+.2f} "
                   f"[{r['Z']['ci95'][0]:+.2f}, {r['Z']['ci95'][1]:+.2f}]) | {r['D']['new']:.2f} ({r['D']['minus_v4']:+.2f} "
                   f"[{r['D']['ci95'][0]:+.2f}, {r['D']['ci95'][1]:+.2f}]) | {'holds' if r['guard'] else 'FAILS'} | {r['verdict']}"
                   f"{' (' + r['verdict_note'] + ')' if r.get('verdict_note') else ''} |")
    for n, r in res["configs"].items():
        out += ["", f"**{n}**{' (primary)' if n == res['primary'] else ''}" + (f"; flags: {'; '.join(r['flags'])}" if r["flags"] else ""), "",
                "| group | cell | walks | new | v4 | S0 | new minus v4 |", "|---|---|---|---|---|---|---|"]
        for k, d in r["cells"].items():
            pm = d["new_minus_v4"]
            out.append(f"| {d['group']} | {k.replace('|', ' ')} | {d['n']} | {_ci(d['new'])} | {d['v4']['pct']:.2f} | {d['S0']['pct']:.2f} | "
                       f"{pm['pct']:+.2f} [{pm['ci95'][0]:+.2f}, {pm['ci95'][1]:+.2f}] {pm['label']} |")
        for m, d in r["ranking"].items():
            pm = d["new_minus_v4"]
            out.append(f"| ranking | {m} (loso natural) | {d['new']['n']} | {_ci(d['new'])} | {d['v4']['pct']:.2f} |  | "
                       f"{pm['pct']:+.2f} [{pm['ci95'][0]:+.2f}, {pm['ci95'][1]:+.2f}] {pm['label']} |")
    return "\n".join(out)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "reproduce":
        sys.exit(0 if reproduce() else 1)
    elif what == "score":
        score(sys.argv[sys.argv.index("--config") + 1])
    elif what == "summarise":
        summarise()
    sys.exit(0)
