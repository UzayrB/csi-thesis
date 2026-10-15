"""ixa_measures. The extras brief's measures on the FINAL engine (`runs/identify/engine/PLAN.md`, the extras note):
2.4 CAL-none (adaptation off), 3 S_wifi (the Wi-Fi-speed-alone control) and 4 accuracy against coverage.
Names are used in the outputs (allowed from 30 September). Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ixa_measures [--device mps]
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "final_extras", "measures")
CL = np.array(L.CLASSES)
NAME = {anon(n): n for n in SIX}
FOLDS = {"toB2": "B2", "toB1": "B1"}


def final() -> dict:
    """The final engine: its model names, bank, and replays. Section 2 adopted nothing; engine v2 (the cadence bug fix,
    1 Oct) is the final engine once its models exist (`EN.SUFFIX`, `EN.bank_dir`)."""
    st = json.load(open(os.path.join("runs", "identify", "final_extras", "state.json")))
    assert not any(st["best"].values())
    x = os.path.exists(os.path.join(EN.ENG, "models", EN.model_name("loso_B2"), "manifest.json"))
    return {"suffix": EN.SUFFIX if x else "", "bank": EN.bank_dir(EN.T_S) if x else os.path.join(EN.ENG, "bank_T3.0"),
            "engine_version": EN.ENGINE_VERSION if x else 1, "config": st["best"], "T": EN.T_S if x else 3.0}


def wkey(model: str) -> str:
    """The Wi-Fi speed column a model was trained with (engine v4: its end detector's alpha, in its manifest)."""
    p = os.path.join(EN.ENG, "models", model, "manifest.json")
    a = json.load(open(p)).get("alpha") if os.path.exists(p) else None
    return "wifi_speed" if a in (None, 0.5) else f"wifi_speed_a{a}"


def replays(fin: dict) -> dict:
    out = {}
    for s in ("A1", "A2", "A3", "B1", "B2"):
        z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}{fin['suffix']}_{s}_T{fin.get('T', 3.0):.1f}.npz"))
        out[s] = {k: z[k] for k in z.files}
    return out


def labels(bank: str) -> dict:
    meta = json.load(open(os.path.join(bank, "meta.json")))["passes"]
    out = {k: np.array([m[k] for m in meta]) for k in ("session", "kind", "block", "anon", "path", "press_speed_m_s", "wifi_speed")}
    if "wifi_speed_a0.2" in meta[0]:
        out["wifi_speed_a0.2"] = np.array([m["wifi_speed_a0.2"] for m in meta], float)
    return out


def walks(rep: dict, a: dict, key: str = "ensemble") -> dict:
    parts = []
    for f, s in FOLDS.items():
        r = rep[s]
        k = a["kind"][r["te"]] == "idcap"
        parts.append({"te": r["te"][k], "lp": r[key][k], "conf": r["confidence"][k] if "confidence" in r else None, "fold": np.full(int(k.sum()), f)})
    d = {"te": np.concatenate([p["te"] for p in parts]), "lp": np.concatenate([p["lp"] for p in parts]),
         "fold": np.concatenate([p["fold"] for p in parts])}
    if parts[0]["conf"] is not None:
        d["conf"] = np.concatenate([p["conf"] for p in parts])
    d.update({"who": a["anon"][d["te"]], "block": a["block"][d["te"]], "path": a["path"][d["te"]]})
    return d


def blocks(d: dict, lp: np.ndarray) -> dict:
    ok = (CL[lp.argmax(1)] == d["who"]).astype(float)
    return {b: EV._boot(ok[m], d["who"][m]) | {f: round(100 * float(ok[m & (d["fold"] == f)].mean()), 2) for f in FOLDS}
            for b, m in EV.masks(d).items()}


def paired(d: dict, lp1, lp2) -> dict:
    o1 = (CL[lp1.argmax(1)] == d["who"]).astype(float)
    o2 = (CL[lp2.argmax(1)] == d["who"]).astype(float)
    return {b: EV.paired(o1[m], o2[m], d["who"][m]) for b, m in EV.masks(d).items()}


def lda_one(a: dict, col: str, d: dict, fin: dict = None) -> np.ndarray:
    """An LDA on one number (S0's arithmetic, `idx_loso.arm_s0`), trained on the other Room B day's identification walks.
    With `fin`, the Wi-Fi speed is each fold model's own column (engine v4's alpha)."""
    out = np.zeros((len(d["te"]), 6))
    base_col = col
    for f, s in FOLDS.items():
        col = wkey(f"loso_{s}{fin['suffix']}") if (fin and base_col == "wifi_speed") else base_col
        k = d["fold"] == f
        other = "B1" if s == "B2" else "B2"
        tr = np.flatnonzero((a["session"] == other) & (a["kind"] == "idcap") & np.isfinite(a[col].astype(float)))
        x_te = a[col][d["te"][k]].astype(float)
        x_te = np.where(np.isfinite(x_te), x_te, np.nanmedian(a[col][tr].astype(float)))
        P, cl = C.lda_proba(a[col][tr].astype(float)[:, None], x_te[:, None], a["anon"][tr])
        out[k] = L._order(C.logp_from_proba(P), cl)
    return out


def cal_none(fin: dict, a: dict, rep: dict, device: str) -> dict:
    """Every window through the engine's own `Session.classify` with an empty pool: training statistics, no AdaBN."""
    bank = fin["bank"]
    X = np.load(os.path.join(bank, "features.npy"))
    maps = pickle.load(open(os.path.join(bank, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(bank, "meta.json")))["passes"]
    out = {}
    for s in ("A1", "A2", "A3", "B1", "B2"):
        model = EN.Model(os.path.join(EN.ENG, "models", f"loso_{s}{fin['suffix']}"), device)
        key = wkey(f"loso_{s}{fin['suffix']}")
        sess = EN.Session(model)
        r = rep[s]
        lp = []
        for i, path in zip(r["te"], r["path_used"]):
            ex = {"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path)}
            lp.append(sess.classify(ex)["ensemble"])
            assert len(sess) == 0
        out[s] = {"te": r["te"], "ensemble": np.array(lp)}
    return out


def coverage(d: dict) -> dict:
    nat = np.flatnonzero(d["block"] == "natural")
    conf = d["conf"][nat].max(1)
    top = np.exp(d["lp"][nat]).max(1)
    order = np.lexsort((np.arange(len(nat)), -top, -conf))
    ok = (CL[d["lp"][nat].argmax(1)] == d["who"][nat]).astype(float)
    who = d["who"][nat]
    res = {"n": int(len(nat)), "levels": {}}
    for c in (100, 75, 50, 30, 20):
        k = int(np.ceil(c / 100 * len(nat)))
        sel = order[:k]
        res["levels"][f"{c}%"] = {"walks": k, **EV._boot(ok[sel], who[sel]),
                                  "walks_per_person": {NAME[p]: int(np.sum(who[sel] == p)) for p in L.CLASSES},
                                  "correct_per_person": {NAME[p]: int(np.sum(ok[sel][who[sel] == p])) for p in L.CLASSES},
                                  "min_confidence": round(float(conf[sel].min()), 4)}
    from scipy.stats import mannwhitneyu
    r, w = conf[ok == 1], conf[ok == 0]
    res["auroc"] = round(float(mannwhitneyu(r, w).statistic / (len(r) * len(w))), 3)
    return res


def run(device: str = "cpu") -> dict:
    fin = final()
    a = labels(fin["bank"])
    rep = replays(fin)
    d = walks(rep, a)
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "final": fin, "names": NAME}
    res["engine"] = blocks(d, d["lp"])
    # 2.4 CAL-none
    cn = cal_none(fin, a, rep, device)
    dn = walks(cn, a)
    assert np.array_equal(dn["te"], d["te"])
    res["cal_none"] = {"walks": blocks(dn, dn["lp"]), "engine_minus_cal_none": paired(d, d["lp"], dn["lp"])}
    loso = {}
    for tag, key in (("adapted", rep), ("cal_none", cn)):
        for room in ("A", "B"):
            te, ok = [], []
            for s in ("A1", "A2", "A3", "B1", "B2"):
                if s[0] != room:
                    continue
                k = a["kind"][key[s]["te"]] == "track"
                t = key[s]["te"][k]
                te.append(t)
                ok.append(CL[key[s]["ensemble"][k].argmax(1)] == a["anon"][t])
            te, ok = np.concatenate(te), np.concatenate(ok).astype(float)
            loso[f"{tag}_room_{room}"] = EV._boot(ok, a["anon"][te])
            loso[f"{tag}_room_{room}_ok"] = ok
    res["cal_none"]["loso"] = {k: v for k, v in loso.items() if not k.endswith("_ok")}
    for room in ("A", "B"):
        te = np.concatenate([rep[s]["te"][a["kind"][rep[s]["te"]] == "track"] for s in ("A1", "A2", "A3", "B1", "B2") if s[0] == room])
        res["cal_none"]["loso"][f"adapted_minus_cal_none_room_{room}"] = EV.paired(loso[f"adapted_room_{room}_ok"], loso[f"cal_none_room_{room}_ok"], a["anon"][te])
    # 3 S_wifi (and S0 beside it)
    sw, s0 = lda_one(a, "wifi_speed", d, fin), lda_one(a, "press_speed_m_s", d)
    res["S_wifi"] = blocks(d, sw)
    res["S0"] = blocks(d, s0)
    res["engine_minus_S_wifi"] = paired(d, d["lp"], sw)
    nopace = np.concatenate([rep[s]["ensemble_nopace"][a["kind"][rep[s]["te"]] == "idcap"] for s in FOLDS.values()])
    res["engine_without_pace_minus_S_wifi"] = paired(d, nopace, sw)
    res["engine_without_pace"] = blocks(d, nopace)
    # 4 coverage
    res["coverage"] = coverage(d)
    # per participant (natural), with names
    nat = d["block"] == "natural"
    ok = CL[d["lp"].argmax(1)] == d["who"]
    res["per_participant_natural"] = {NAME[p]: round(100 * float(ok[nat & (d["who"] == p)].mean()), 2) for p in L.CLASSES}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, f"measures{fin['suffix']}.json"), "w"), indent=1, default=str)
    print(json.dumps({"engine_natural": res["engine"]["natural_both"], "cal_none_natural": res["cal_none"]["walks"]["natural_both"],
                      "S_wifi_natural": res["S_wifi"]["natural_both"], "engine_minus_S_wifi": res["engine_minus_S_wifi"]["natural_both"],
                      "coverage": {k: (v["pct"], v["ci95"]) for k, v in res["coverage"]["levels"].items()}, "auroc": res["coverage"]["auroc"]},
                     indent=1, default=str), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    run(ap.parse_args().device)
    sys.exit(0)
