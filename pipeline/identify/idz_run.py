"""idz_run. Identification audit: the stage controller (`runs/identify/audit/PLAN.md`). Each stage reads the
current best configuration from `runs/identify/audit/state.json`, runs, applies the PLAN rule, and writes
the decision back, so the queue can run the stages in PLAN order unattended.

    PYTHONPATH=. python3 -m pipeline.identify.idz_run <stage>
stages: B1 fusion L1 L2 cadence CF FN GS final
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idw_core as W
from pipeline.identify import idw_eval as EV
from pipeline.identify import idw_run as R
from pipeline.identify import idx_loso as L
from pipeline.identify import idz_bank as ZB
from pipeline.identify import idz_core as Z

AUD = os.path.join("runs", "identify", "audit")
STATE = os.path.join(AUD, "state.json")
OUTS = os.path.join(AUD, "outputs")
MODELS = os.path.join(AUD, "models")
FOLDS = ("toB2", "toB1")
CL = np.array(L.CLASSES)
log = lambda s: print(s, flush=True)  # noqa: E731


def state() -> dict:
    return json.load(open(STATE)) if os.path.exists(STATE) else {"history": []}


def save_state(s):
    txt = json.dumps(s, indent=1, default=str)
    assert IC.no_names(txt)
    open(STATE, "w").write(txt)


_BANKS = {}


def bank_of(path):
    if path not in _BANKS:
        _BANKS[path] = L.load(path)
    L.register_variant("dev", _BANKS[path]["X"], _BANKS[path]["names"])
    return _BANKS[path]


HOLD = os.path.join(AUD, "queue", "HOLD_GPU")


def device():
    """Before every training or scoring step: wait while HOLD_GPU exists (tracking's agreed GPU slot), then
    while any tracking training process runs; then MPS if available."""
    if os.path.exists(HOLD):
        log(f"{time.strftime('%H:%M:%S')} PAUSED for tracking (HOLD_GPU); nothing of identification's is on the GPU")
        while os.path.exists(HOLD):
            time.sleep(30)
        log(f"{time.strftime('%H:%M:%S')} resumed")
    return W.wait_for_tracking(log)


# ------------------------------------------------------------------ train, score, evaluate

def train_cfg(name, cfg, parts=("feat", "cnn")) -> dict:
    bank = bank_of(cfg["bank"])
    dirs = {}
    for f in FOLDS:
        tr = R.train_rows(bank["a"], "TR-AB", f)
        d = os.path.join(MODELS, f"{name}_{f}")
        if not os.path.exists(os.path.join(d, f"meta_{'_'.join(parts)}.json")):
            dev = device()
            log(f"{time.strftime('%H:%M:%S')} training {name} {f} ({'+'.join(parts)}) on {dev}")
            Z.train(bank, tr, d, cfg, parts=parts, device=dev, log=log)
        dirs[f] = d
    return dirs


def score_cfg(name, cfg, feat_dirs, cnn_dirs, calib) -> str:
    bank = bank_of(cfg["bank"])
    a = bank["a"]
    os.makedirs(OUTS, exist_ok=True)
    for f in FOLDS:
        p = os.path.join(OUTS, f"{name}_{f}_{calib}.npz")
        if os.path.exists(p):
            continue
        te = R.test_rows(a, f)
        comp = Z.apply(bank, feat_dirs[f], cnn_dirs[f], te, Z.calibration_groups(a, te, calib), cfg, device=device())
        other = "B1" if R.TEST[f] == "B2" else "B2"
        s0 = W.s0(bank, np.flatnonzero((a["session"] == other) & (a["kind"] == "idcap")), te)
        np.savez(p, te=te, s0=s0, **comp)
        log(f"{time.strftime('%H:%M:%S')} scored {name} {f} {calib}")
    return name


def loaded(name, calib, a) -> dict:
    parts = []
    for f in FOLDS:
        z = np.load(os.path.join(OUTS if not name.startswith("idwalks:") else R.OUTPUTS,
                                 f"{name.split(':')[-1]}_{f}_{calib}.npz"))
        parts.append({k: z[k] for k in z.files} | {"fold": np.full(len(z["te"]), f)})
    d = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    te = d["te"]
    d.update({"who": a["anon"][te], "block": a["block"][te], "path": a["path"][te], "session": a["session"][te],
              "t_start": a["t_start"][te]})
    return d


def correct(d, fusion, keep=Z.COMPONENTS) -> np.ndarray:
    return (CL[Z.fuse(d, fusion, keep).argmax(1)] == d["who"]).astype(float)


def table(d, fusion) -> dict:
    c = correct(d, fusion)
    out = {}
    for b, m in EV.masks(d).items():
        out[b] = EV._boot(c[m], d["who"][m]) | {f: EV._boot(c[m & (d["fold"] == f)], d["who"][m & (d["fold"] == f)])["pct"] for f in FOLDS}
    return out


def evaluate(best: dict, cand_name: str, cand_fusion: str, cand_calib: str, a) -> dict:
    db = loaded(best["outputs"], best["calib"], a)
    dc = loaded(cand_name, cand_calib, a)
    assert np.array_equal(db["te"], dc["te"])
    cb, cc = correct(db, best["fusion"]), correct(dc, cand_fusion)
    mk = EV.masks(db)
    nat = mk["natural_both"]
    diff = EV.paired(cc[nat], cb[nat], db["who"][nat])
    slow_d = 100 * (cc[mk["slow"]].mean() - cb[mk["slow"]].mean())
    fast_d = 100 * (cc[mk["fast"]].mean() - cb[mk["fast"]].mean())
    adopt = bool(diff["ci95"][0] > 0 and slow_d >= -3.0 and fast_d >= -3.0)
    return {"candidate": table(dc, cand_fusion), "current_best": table(db, best["fusion"]),
            "paired_natural": diff, "slow_change": round(slow_d, 2), "fast_change": round(fast_d, 2),
            "paired_by_block": {b: EV.paired(cc[m], cb[m], db["who"][m]) for b, m in mk.items() if b != "natural_both"},
            "ADOPT": adopt}


def record(s, item, result, adopted_cfg=None):
    s["history"].append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "item": item, **result})
    if adopted_cfg is not None:
        s["best"] = adopted_cfg
    save_state(s)
    log(json.dumps({"item": item, "ADOPT": result.get("ADOPT"), "paired_natural": result.get("paired_natural"),
                    "slow_change": result.get("slow_change"), "fast_change": result.get("fast_change")}, default=str))


# ------------------------------------------------------------------ stages

def stage_B1():
    """The bug fixes B-1 (columns v2) and B-2 (maps v2): retrain TR-AB on bank_v2; the new baseline."""
    s = state()
    cfg = {"bank": os.path.join(AUD, "bank_v2"), "cols": "v2", "layout": False, "fn": False}
    dirs = train_cfg("B1", cfg)
    for calib in ("others", "causal", "none"):
        score_cfg("B1", cfg, dirs, dirs, calib)
    best0 = {"outputs": "idwalks:TR-AB", "calib": "others", "fusion": "F0"}
    a = bank_of(cfg["bank"])["a"]
    res = evaluate(best0, "B1", "F0", "others", a)
    res["ADOPT"] = True
    res["note"] = "bug fixes B-1 and B-2, adopted without the rule; compared with the frozen B0 for the record"
    best = {**cfg, "name": "B1", "feat_dirs": dirs, "cnn_dirs": dirs, "outputs": "B1", "calib": "others", "fusion": "F0",
            "adopted": ["B-1", "B-2"]}
    record(s, "B1 (bug fixes)", res, best)


def stage_fusion():
    s = state()
    best = s["best"]
    a = bank_of(best["bank"])["a"]
    d = loaded(best["outputs"], best["calib"], a)
    floor = np.log(1.0001e-9)
    diag = {"floor_frac": {c: round(float(np.mean(d[c] <= floor)), 4) for c in Z.COMPONENTS}}
    ens = Z.fuse(d, "F0").argmax(1)
    diag["agree_with_ensemble"] = {c: round(float(np.mean(d[c].argmax(1) == ens)), 3) for c in Z.COMPONENTS}
    truth = np.array([L.CLASSES.index(w) for w in d["who"]])
    veto = {}
    for c in Z.COMPONENTS:
        without = Z.fuse(d, "F0", [k for k in Z.COMPONENTS if k != c]).argmax(1)
        at_floor = d[c][np.arange(len(truth)), truth] <= floor
        veto[c] = int(np.sum(at_floor & (without == truth) & (ens != truth)))
    diag["vetoes"] = veto
    dev = {}
    for sname in L.SESSIONS:
        z = np.load(os.path.join("runs", "identify", "dev", "all", f"all_{sname}.npz"))
        dev[sname] = {c: round(float(np.mean(z["test__" + c] <= floor)), 4) for c in Z.COMPONENTS}
    diag["dev_all_floor_frac"] = dev
    res1 = evaluate(best, best["outputs"], "F1", best["calib"], a)
    out = {"diagnostics": diag, "F1": res1}
    chosen = "F1" if res1["ADOPT"] else None
    if not chosen:
        r2 = evaluate(best, best["outputs"], "F2", best["calib"], a)
        r3 = evaluate(best, best["outputs"], "F3", best["calib"], a)
        out["F2"], out["F3"] = r2, r3
        ok = [(v["paired_natural"]["pct"], k) for k, v in (("F2", r2), ("F3", r3)) if v["ADOPT"]]
        chosen = max(ok)[1] if ok else None
    conf = Z.fuse(d, "F0")
    g = np.exp(conf / 8.0)
    g = g / g.sum(1, keepdims=True)
    ok_ = CL[conf.argmax(1)] == d["who"]
    out["displayed_confidence_geomean"] = {"median_when_right": round(float(np.median(g.max(1)[ok_])), 3),
                                           "median_when_wrong": round(float(np.median(g.max(1)[~ok_])), 3)}
    out["ADOPT"] = chosen is not None
    out["chosen"] = chosen
    out["paired_natural"] = out[chosen]["paired_natural"] if chosen else res1["paired_natural"]
    new = {**best, "fusion": chosen, "adopted": best["adopted"] + [chosen]} if chosen else None
    record(s, "fusion", out, new)


def stage_L1():
    s = state()
    best = s["best"]
    cfg = {k: best[k] for k in ("bank", "cols", "layout", "fn")}
    name = f"{best['name']}_L1"
    score_cfg(name, cfg, best["feat_dirs"], best["cnn_dirs"], "others_idcap")
    a = bank_of(best["bank"])["a"]
    res = evaluate(best, name, best["fusion"], "others_idcap", a)
    record(s, "L1", res, {**best, "outputs": name, "calib": "others_idcap", "adopted": best["adopted"] + ["L1"]} if res["ADOPT"] else None)


def stage_retrain(item, cfg_change, parts):
    s = state()
    best = s["best"]
    cfg = {**{k: best[k] for k in ("bank", "cols", "layout", "fn")}, **cfg_change}
    dirs = train_cfg(item, cfg, parts)
    feat_dirs = dirs if "feat" in parts else best["feat_dirs"]
    cnn_dirs = dirs if "cnn" in parts else best["cnn_dirs"]
    score_cfg(item, cfg, feat_dirs, cnn_dirs, best["calib"])
    a = bank_of(cfg["bank"])["a"]
    res = evaluate(best, item, best["fusion"], best["calib"], a)
    record(s, item, res, {**best, **cfg, "name": item, "feat_dirs": feat_dirs, "cnn_dirs": cnn_dirs, "outputs": item,
                          "adopted": best["adopted"] + [item]} if res["ADOPT"] else None)


def stage_cadence():
    from pipeline.identify import idz_cadence as ZC
    s = state()
    best = s["best"]
    summ = ZC.run(best["bank"])
    if not summ["C1_GATE"]:
        record(s, "C1", {"diagnostic": summ, "GATE": False, "ADOPT": False, "note": "gate not met; C1 not run"})
        return
    out = os.path.join(AUD, "bank_c1")
    if not os.path.exists(os.path.join(out, "build.json")):
        device()
        ZB.build(out, context_s=best.get("context_s", 0.0), amp_norm=False, cadence_env=True)
    s["history"].append({"item": "C1 diagnostic", "diagnostic": summ, "GATE": True})
    save_state(s)
    stage_retrain("C1", {"bank": out, "cadence_env": True}, ("feat",))


def stage_bank_candidate(item, out, **kw):
    s = state()
    best = s["best"]
    if not os.path.exists(os.path.join(out, "build.json")):
        device()
        ZB.build(out, context_s=kw.get("context_s", best.get("context_s", 0.0)), amp_norm=kw.get("amp_norm", False),
                 cadence_env=best.get("cadence_env", False))
    stage_retrain(item, {"bank": out, **{k: v for k, v in kw.items() if k in ("context_s", "amp_norm")}}, ("feat", "cnn"))


def stage_final():
    """The final configuration in full: the identification-walks tables and leave-one-session-out."""
    s = state()
    best = s["best"]
    bank = bank_of(best["bank"])
    a = bank["a"]
    d = loaded(best["outputs"], best["calib"], a)
    out = {"config": {k: best[k] for k in ("bank", "cols", "layout", "fn", "calib", "fusion", "adopted")}}
    out["walks"] = table(d, best["fusion"])
    c = correct(d, best["fusion"])
    nat = EV.masks(d)["natural_both"]
    s0_ok = (CL[d["s0"].argmax(1)] == d["who"]).astype(float)
    out["controls"] = {"S0": {b: EV._boot(s0_ok[m], d["who"][m]) for b, m in EV.masks(d).items()},
                       "no_pace": {b: EV._boot(correct(d, best["fusion"], [k for k in Z.COMPONENTS if k not in Z.PACE_COMPONENTS])[m], d["who"][m])
                                   for b, m in EV.masks(d).items()}}
    out["per_participant"] = {p: round(100 * float(c[nat & (d["who"] == p)].mean()), 2) for p in L.CLASSES}
    pred = CL[Z.fuse(d, best["fusion"]).argmax(1)]
    out["confusion_natural"] = [[int(np.sum(nat & (d["who"] == t) & (pred == q))) for q in L.CLASSES] for t in L.CLASSES]
    dd = dict(d)
    dd["ensemble"] = Z.fuse(d, best["fusion"])
    out["deployment"] = EV.deployment(dd, a)
    # leave one session out on the tracking passes, CAL-causal, the final configuration retrained per fold
    cfg = {k: best[k] for k in ("bank", "cols", "layout", "fn")}
    preds = {}
    for sname in L.SESSIONS:
        tr = np.flatnonzero(a["session"] != sname)
        te = np.flatnonzero((a["session"] == sname) & (a["kind"] == "track"))
        md = os.path.join(MODELS, f"final_loso_{sname}")
        if not os.path.exists(os.path.join(md, "meta_feat_cnn.json")):
            dev = device()
            log(f"{time.strftime('%H:%M:%S')} LOSO training {sname} on {dev}")
            Z.train(bank, tr, md, cfg, device=dev, log=log)
        te_all = np.flatnonzero(a["session"] == sname)
        comp = Z.apply(bank, md, md, te_all, Z.calibration_groups(a, te_all, "causal"), cfg, device=device())
        k = a["kind"][te_all] == "track"
        comp = {c_: v[k] for c_, v in comp.items()}
        preds[sname] = (te, CL[Z.fuse(comp, best["fusion"]).argmax(1)])
        np.savez(os.path.join(OUTS, f"final_loso_{sname}_causal.npz"), te=te, **comp)
        log(f"{time.strftime('%H:%M:%S')} LOSO {sname}: {100 * float(np.mean(preds[sname][1] == a['anon'][te])):.2f}")
    loso = {}
    for sname in L.SESSIONS:
        te, pr = preds[sname]
        loso[sname] = EV._boot((pr == a["anon"][te]).astype(float), a["anon"][te])
    for room in ("A", "B"):
        te = np.concatenate([preds[x][0] for x in L.SESSIONS if x[0] == room])
        pr = np.concatenate([preds[x][1] for x in L.SESSIONS if x[0] == room])
        loso[f"room_{room}"] = EV._boot((pr == a["anon"][te]).astype(float), a["anon"][te])
    out["loso_tracking_causal"] = loso
    txt = json.dumps(out, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(AUD, "final.json"), "w").write(txt)
    s["final"] = {"walks_natural": out["walks"]["natural_both"], "loso": {k: v for k, v in loso.items() if k.startswith("room")}}
    save_state(s)
    log(json.dumps(s["final"], default=str))


STAGES = {"B1": stage_B1, "fusion": stage_fusion, "L1": stage_L1,
          "L2": lambda: stage_retrain("L2", {"layout": True}, ("feat", "cnn")),
          "cadence": stage_cadence,
          "CF": lambda: stage_bank_candidate("CF", os.path.join(AUD, "bank_cf"), context_s=3.0),
          "FN": lambda: stage_retrain("FN", {"fn": True}, ("cnn",)),
          "GS": lambda: stage_bank_candidate("GS", os.path.join(AUD, "bank_gs"), amp_norm=True),
          "final": stage_final}


if __name__ == "__main__":
    STAGES[sys.argv[1]]()
    sys.exit(0)
