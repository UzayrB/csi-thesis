"""ixr_eval. Identification across days and rooms on tracking's split (`runs/identify/engine/PREREG_XROOM_V4.md`): the
scoring, from the harness's replays only (`ide_replay`, the leave-one-session-out replay path; B2's identification walks
with the direction detected as shipped). No training but the speed controls' one-number LDAs.

- Table 1: every model on A3 tracking, B2 tracking, B2 natural, slow and fast; the engine (CAL-causal), CAL-none, S0 and
  S_wifi, each with its interval and cluster count;
- Table 2: the comparisons fixed in the addendum, paired on the same walks;
- the speed controls on the existing leave-one-session-out tracking figures (loso_*_v4 replays; the two-press reference
  `final_loso_<s>_causal.npz`, recovered from git), anchored to `one_press_cost_tracking_information_v4.json`.

Intervals: `idw_eval._boot` / `paired` as `eval_v4.json` (10,000 resamples, seed 0, clusters = participants; in every
test cell each participant has exactly one recording, asserted, so this equals resampling recordings).

    PYTHONPATH=. python3 -m pipeline.identify.ixr_eval calnone --model xr_AB_v4 --session A3 [--device mps]
    PYTHONPATH=. python3 -m pipeline.identify.ixr_eval score
    PYTHONPATH=. python3 -m pipeline.identify.ixr_eval tables       # the report's tables, from the json

`--version 5` (engine v5, 10 Oct): the same tables for the `*_v5` models and replays (CAL-none through v5's three windows
and room weight; the loso engine anchored to eval_v5.json); without it everything is v4's, unchanged.

Development evaluation, all data seen.
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

T = 4.0
CL = np.array(L.CLASSES)
CHANCE = 100.0 / 6
SESSIONS = ("A1", "A2", "A3", "B1", "B2")
VER = 4                     # the engine version evaluated (`--version`; v4 by default)
MODELS = ("xr_AB_v4", "xr_ABtrk_v4", "xr_A_v4", "xr_B1_v4")
CELLS = {"A3_tracking": ("A3", "track", None), "B2_tracking": ("B2", "track", None), "B2_natural": ("B2", "idcap", "natural"),
         "B2_slow": ("B2", "idcap", "slow"), "B2_fast": ("B2", "idcap", "fast")}
XR = os.path.join(EN.ENG, "xroom")
REP = os.path.join(EN.ENG, "replays")
OUT = os.path.join(EN.ENG, "eval", "eval_xroom_v4.json")
NOTE = {("xr_A_v4", "B2_natural"): "double jump: cross-room and cross-layout (Room A never had RX2 beside the transmitter)",
        ("xr_A_v4", "B2_slow"): "double jump: cross-room and cross-layout",
        ("xr_A_v4", "B2_fast"): "double jump: cross-room and cross-layout"}


def M(base: str) -> str:
    """A model's name at the evaluated engine version."""
    return f"{base}_v{VER}"


def set_version(v: int) -> None:
    global VER, MODELS, OUT, NOTE
    VER = int(v)
    MODELS = tuple(M(b) for b in ("xr_AB", "xr_ABtrk", "xr_A", "xr_B1"))
    OUT = os.path.join(EN.ENG, "eval", f"eval_xroom_v{VER}.json")
    NOTE = {(M("xr_A"), k): v_ for (_m, k), v_ in NOTE.items() if _m.startswith("xr_A_")}


def labels() -> dict:
    meta = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
    a = {k: np.array([m[k] for m in meta]) for k in ("session", "room", "kind", "block", "anon", "path", "t_start")}
    for k in ("press_speed_m_s", "wifi_speed", "wifi_speed_a0.2"):
        a[k] = np.array([m[k] for m in meta], float)
    return a


def recording_of_rows(a: dict) -> np.ndarray:
    """Each bank row's recording (its ground-truth file), from the recordings' start presses."""
    from pipeline.identify import idx_bank as B
    idx = {(s, round(float(t), 6)): i for i, (s, t) in enumerate(zip(a["session"], a["t_start"]))}
    out = np.full(len(a["session"]), "", dtype=object)
    for r in B.recordings():
        gt = json.load(open(r["stem"] + ".gt.json", encoding="utf-8"))
        for q in gt["passes"]:
            out[idx[(r["session"], round(float(q["t_start"]), 6))]] = os.path.basename(r["stem"])
    assert all(out)
    return out


def wkey(model: str) -> str:
    a = json.load(open(os.path.join(EN.ENG, "models", model, "manifest.json"))).get("alpha")
    return "wifi_speed" if a in (None, 0.5) else f"wifi_speed_a{a}"


def lda_one(a: dict, col: str, tr: np.ndarray, te: np.ndarray) -> np.ndarray:
    """S0's arithmetic (`ixa_measures.lda_one`): an LDA on one number, trained on the rows `tr` with a finite value; a
    test row without one gets the training median."""
    x = a[col].astype(float)
    trf = tr[np.isfinite(x[tr])]
    x_te = np.where(np.isfinite(x[te]), x[te], np.nanmedian(x[trf]))
    P, cl = C.lda_proba(x[trf][:, None], x_te[:, None], a["anon"][trf])
    return L._order(C.logp_from_proba(P), cl)


def correct(lp: np.ndarray, who: np.ndarray) -> np.ndarray:
    return (CL[lp.argmax(1)] == who).astype(float)


def boot(c, who, rec=None) -> dict:
    out = EV._boot(c, who) | {"clusters": int(len(np.unique(who)))}
    if rec is not None:
        out["recordings"] = int(len(np.unique(rec)))
    return out


def paired(c1, c2, who) -> dict:
    d = EV.paired(c1, c2, who) | {"clusters": int(len(np.unique(who)))}
    d["label"] = ("separable gain" if d["ci95"][0] > 0 else "separable cost" if d["ci95"][1] < 0 else "not separable")
    return d


def replay(model: str, session: str) -> dict:
    z = np.load(os.path.join(REP, f"{model}_{session}_T{T:.1f}.npz"))
    return {k: z[k] for k in z.files}


# ------------------------------------------------------------------ CAL-none (information)

def calnone(model: str, session: str, device: str = "cpu") -> str:
    """Every replayed window through the engine's own `Session.classify` with an empty pool (training statistics, no
    AdaBN), the features and maps from the bank (equal to the replay's, asserted there), the replay's path."""
    bank = EN.bank_dir(T)
    X = np.load(os.path.join(bank, "features.npy"))
    maps = pickle.load(open(os.path.join(bank, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(bank, "meta.json")))["passes"]
    r = replay(model, session)
    assert r["features_equal_bank"].all() and r["maps_equal_bank"].all()
    m = EN.Model(os.path.join(EN.ENG, "models", model), device)
    key = wkey(model)
    sess = EN.Session(m)
    lp = []
    if m.version >= 5:                              # engine v5: the 0 s window and the offset windows (the replay's own), combined
        cols = EN.v2_columns(json.load(open(EN.DEV_NAMES)))
        tt = pickle.load(open(os.path.join("runs", "identify", "best", "extract", "tta", f"{session}.pkl"), "rb"))
        tix = {(int(rr), f"{o:.2f}"): j for j, (rr, o) in enumerate(zip(tt["rows"], tt["offset"]))}
        alpha = json.load(open(os.path.join(EN.ENG, "models", model, "manifest.json")))["alpha"]
        for j_, (i, path) in enumerate(zip(r["te"], r["path_used"])):
            layout = "id_spot" if meta[i]["kind"] == "idcap" else "home"
            exs = [{"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path), "layout": layout}]
            for o in m.offsets:
                k = tix[(int(i), f"{o:.2f}")]
                f = np.zeros(len(X[i]), np.float64)
                f[cols] = tt["F"][k]
                exs.append({"features": f, "maps": tt["maps"][k], "wifi_speed": float(tt[f"speed_{alpha}"][k]),
                            "path": str(tt["path_used"][k]), "layout": layout})
            a_ = m.weight(session[0], layout)
            assert a_ == float(r["weight_a"][j_])
            lp.append(sess.combine([sess.classify(e) for e in exs], a_)["ensemble"])
            assert len(sess) == 0
    for i, path in zip(r["te"], r["path_used"]) if m.version < 5 else ():
        lp.append(sess.classify({"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path)})["ensemble"])
        assert len(sess) == 0
    p = os.path.join(REP, f"{model}_{session}_T{T:.1f}_calnone.npz")
    np.savez(p, te=r["te"], ensemble=np.array(lp))
    print(f"{time.strftime('%H:%M:%S')} {model} {session}: CAL-none on {len(lp)} windows -> {p}", flush=True)
    return p


# ------------------------------------------------------------------ Table 1 and Table 2

def table1(a: dict, rec: np.ndarray, models=MODELS) -> tuple:
    res, keep = {}, {}
    for model in models:
        man = json.load(open(os.path.join(EN.ENG, "models", model, "manifest.json")))
        tr = np.load(os.path.join(EN.ENG, "models", model, "train_rows.npy"))
        assert not set(a["session"][tr]) & {"A3", "B2"}, model
        res[model] = {"training_sessions": man["training_sessions"], "training_kinds": man.get("training_kinds"),
                      "n_train": man["n_train"], "alpha": man["alpha"], "cells": {}}
        for s in ("A3", "B2"):
            r = replay(model, s)
            te = r["te"]
            assert sorted(te.tolist()) == np.flatnonzero(a["session"] == s).tolist(), (model, s)
            assert r["features_equal_bank"].all() and r["maps_equal_bank"].all(), (model, s)
            key = wkey(model)
            assert np.array_equal(r["wifi_speed"], a[key][te], equal_nan=True), (model, s, "wifi speed")
            cn = np.load(os.path.join(REP, f"{model}_{s}_T{T:.1f}_calnone.npz"))
            assert np.array_equal(cn["te"], te)
            s0 = lda_one(a, "press_speed_m_s", tr, te)
            sw = lda_one(a, key, tr, te)
            who = a["anon"][te]
            for cell, (cs, kind, block) in CELLS.items():
                if cs != s:
                    continue
                m = (a["kind"][te] == kind) & ((a["block"][te] == block) if block else True)
                w, rr = who[m], rec[te[m]]
                assert len(np.unique(rr)) == len(np.unique(w)) == 6, (model, cell)      # one recording per participant
                ce, cc, c0, cw = (correct(lp[m], w) for lp in (r["ensemble"], cn["ensemble"], s0, sw))
                d = {"engine": boot(ce, w, rr), "cal_none": boot(cc, w, rr), "S0": boot(c0, w, rr), "S_wifi": boot(cw, w, rr),
                     "engine_minus_S0": paired(ce, c0, w), "engine_minus_S_wifi": paired(ce, cw, w)}
                d["ABOVE_CHANCE"] = d["engine"]["ci95"][0] > 16.67          # the addendum's rule: above 16.67, as printed
                d["BEYOND_SPEED"] = d["engine_minus_S0"]["ci95"][0] > 0
                d["BELOW_SPEED"] = d["engine_minus_S0"]["ci95"][1] < 0
                if (model, cell) in NOTE:
                    d["note"] = NOTE[(model, cell)]
                res[model]["cells"][cell] = d
                keep[(model, cell)] = (te[m], ce, w)
    return res, keep


def compare(keep: dict, m1: str, m2: str, cell: str) -> dict:
    te1, c1, w = keep[(m1, cell)]
    te2, c2, _w = keep[(m2, cell)]
    assert np.array_equal(te1, te2)
    return paired(c1, c2, w) | {"a": m1, "b": m2, "cell": cell, "a_pct": round(100 * float(c1.mean()), 2),
                                "b_pct": round(100 * float(c2.mean()), 2)}


def table2(t1: dict, keep: dict) -> dict:
    def acc(model, cell):
        c = t1[model]["cells"][cell]
        return {"model": model, "cell": cell, **c["engine"], "ABOVE_CHANCE": c["ABOVE_CHANCE"], "BEYOND_SPEED": c["BEYOND_SPEED"],
                "BELOW_SPEED": c["BELOW_SPEED"], "n_train": t1[model]["n_train"], **({"note": c["note"]} if "note" in c else {})}
    sizes = f"training walks: {M('xr_A')} 240 (A1+A2, tracking only), {M('xr_B1')} 360 (B1, 120 tracking + 240 identification)"
    return {
        "Q1_across_days_same_room_only": [acc(M("xr_A"), "A3_tracking"), acc(M("xr_B1"), "B2_tracking"), acc(M("xr_B1"), "B2_natural")],
        "Q2_across_rooms_zero_shot": {
            "accuracy": [acc(M("xr_A"), "B2_tracking"), acc(M("xr_A"), "B2_natural"), acc(M("xr_B1"), "A3_tracking")],
            "against_same_room_only": [compare(keep, M("xr_A"), M("xr_B1"), "B2_tracking"),
                                       compare(keep, M("xr_A"), M("xr_B1"), "B2_natural"),
                                       compare(keep, M("xr_B1"), M("xr_A"), "A3_tracking")],
            "training_sizes": sizes},
        "Q3_one_day_of_new_room_data": [compare(keep, M("xr_AB"), M("xr_A"), "B2_tracking"),
                                        compare(keep, M("xr_AB"), M("xr_A"), "B2_natural")],
        "Q3_information_A3": [compare(keep, M("xr_AB"), M("xr_A"), "A3_tracking")],
        "tracking_deployed_split": [acc(M("xr_AB"), "A3_tracking"), acc(M("xr_AB"), "B2_tracking")],
        "never_sees_an_identification_walk": {
            "across_days": [acc(M("xr_ABtrk"), "A3_tracking"), acc(M("xr_A"), "A3_tracking")],
            "across_rooms": [acc(M("xr_A"), "B2_tracking"), acc(M("xr_A"), "B2_natural")],
            "one_day_of_new_room_data": [compare(keep, M("xr_ABtrk"), M("xr_A"), "B2_tracking"),
                                         compare(keep, M("xr_ABtrk"), M("xr_A"), "B2_natural")],
            "one_day_information_A3": [compare(keep, M("xr_ABtrk"), M("xr_A"), "A3_tracking")]},
        "what_B1_identification_walks_add": [compare(keep, M("xr_AB"), M("xr_ABtrk"), "A3_tracking"),
                                             compare(keep, M("xr_AB"), M("xr_ABtrk"), "B2_tracking")],
    }


# ------------------------------------------------------------------ the speed controls on the leave-one-session-out figures

def loso_speed(a: dict, rec: np.ndarray) -> dict:
    from pipeline.identify import idz_core as Z
    eng, two, s0, sw, who, ses, room, recs = [], [], [], [], [], [], [], []
    for s in SESSIONS:
        model = f"loso_{s}_v{VER}"
        r = replay(model, s)
        k = a["kind"][r["te"]] == "track"
        te = r["te"][k]
        tr = np.load(os.path.join(EN.ENG, "models", model, "train_rows.npy"))
        assert s not in set(a["session"][tr])
        b = np.load(os.path.join(XR, "recovered", "two_press", f"final_loso_{s}_causal.npz"))
        pos = {int(x): j for j, x in enumerate(b["te"])}
        j = [pos[int(x)] for x in te]
        w = a["anon"][te]
        eng.append(correct(r["ensemble"][k], w))
        two.append(correct(Z.fuse({c: b[c][j] for c in Z.COMPONENTS}, "F0"), w))
        s0.append(correct(lda_one(a, "press_speed_m_s", tr, te), w))
        sw.append(correct(lda_one(a, wkey(model), tr, te), w))
        who.append(w)
        ses.append(a["session"][te])
        room.append(a["room"][te])
        recs.append(rec[te])
    eng, two, s0, sw = (np.concatenate(v) for v in (eng, two, s0, sw))
    who, ses, room, recs = (np.concatenate(v) for v in (who, ses, room, recs))

    def block(m):
        return {"engine": boot(eng[m], who[m], recs[m]), "two_press": boot(two[m], who[m], recs[m]),
                "S0": boot(s0[m], who[m], recs[m]), "S_wifi": boot(sw[m], who[m], recs[m]),
                "engine_minus_S0": paired(eng[m], s0[m], who[m]), "two_press_minus_S0": paired(two[m], s0[m], who[m]),
                "engine_minus_S_wifi": paired(eng[m], sw[m], who[m]), "two_press_minus_S_wifi": paired(two[m], sw[m], who[m])}
    out = {s: block(ses == s) for s in SESSIONS}
    out["room_A"] = block(room == "A")
    out["room_B"] = block(room == "B")
    out["pooled"] = block(np.ones(len(who), bool))
    anchor = json.load(open(os.path.join(EN.ENG, "eval", "one_press_cost_tracking_information_v4.json")))
    ev4 = json.load(open(os.path.join(EN.ENG, "eval", f"eval_v{VER}.json")))["loso_tracking_known_route"]
    for kk in ("pooled", "room_A", "room_B"):
        if VER == 4:                                # the v4 engine's own anchor; the two-press reference anchors every version
            assert out[kk]["engine"]["pct"] == anchor[kk]["engine"], (kk, out[kk]["engine"]["pct"], anchor[kk]["engine"])
        assert out[kk]["two_press"]["pct"] == anchor[kk]["two_press"], (kk, out[kk]["two_press"]["pct"], anchor[kk]["two_press"])
    for kk in SESSIONS + ("room_A", "room_B"):
        assert out[kk]["engine"]["pct"] == ev4[kk]["pct"] and out[kk]["engine"]["ci95"] == ev4[kk]["ci95"], kk
    out["anchor"] = ("engine and two-press equal one_press_cost_tracking_information_v4.json (pooled, room A, room B) and the "
                     "engine equals eval_v4.json's loso_tracking_known_route per session and room, intervals included") if VER == 4 else (
        f"two-press equals one_press_cost_tracking_information_v4.json (pooled, room A, room B) and the engine equals "
        f"eval_v{VER}.json's loso_tracking_known_route per session and room, intervals included")
    out["S0_training"] = f"each fold's own training walks (loso_<s>_v{VER}/train_rows.npy: every walk of the other four sessions)"
    out["S_wifi_column"] = f"each fold model's own Wi-Fi speed column (alpha in its manifest: loso_B1_v{VER} 0.2, the rest 0.5)"
    return out


def score() -> dict:
    from pipeline.identify import idmax_common as IC
    a = labels()
    rec = recording_of_rows(a)
    t1, keep = table1(a, rec, MODELS)            # the evaluated version's models (the default argument is bound to v4's)
    res = {"label": (EN.LABEL + "; the four models' first looks at A3 and B2; the identification design (the 4.0 s window "
                                "included) was chosen with all data seen, B2 included") if VER == 4 else (
                   EN.LABEL + f"; engine v{VER}'s configuration was chosen with A3 and B2 in view"),
           "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "prereg": "runs/identify/engine/PREREG_XROOM_V4.md",
           "engine_version": EN.ENGINE_VERSION if VER == 4 else VER, "T": T, "chance": round(CHANCE, 2),
           "calibration": "CAL-causal as shipped (each walk on its own session's earlier walks in its own layout, "
                          "unlabelled); CAL-none as information",
           "intervals": "idw_eval._boot/paired: 10,000 resamples, seed 0, clusters = participants (one recording each per cell)",
           "rules": {"above_chance": "interval lower bound above 16.67", "beyond_speed": "engine minus S0 interval above zero",
                     "separable": "a paired interval excluding zero"},
           "table1": t1, "table2": table2(t1, keep), "loso_speed_controls": loso_speed(a, rec)}
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt)
    open(OUT, "w").write(txt)
    print(f"{time.strftime('%H:%M:%S')} wrote {OUT}", flush=True)
    return res


# ------------------------------------------------------------------ the report's tables

def _ci(d) -> str:
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def _dci(d) -> str:
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]"


def tables(res: dict = None) -> str:
    res = res or json.load(open(OUT))
    t1 = res["table1"]
    lines = ["| model | trains on | walks | A3 tracking | B2 tracking | B2 natural | B2 slow | B2 fast |", "|---|---|---|---|---|---|---|---|"]
    for model, v in t1.items():
        kinds = "tracking only" if v["training_kinds"] == ["track"] else "all walks"
        row = [f"`{model}`", f"{'+'.join(v['training_sessions'])} ({kinds})", str(v["n_train"])]
        for cell in CELLS:
            c = v["cells"][cell]
            row.append(f"{_ci(c['engine'])} ({c['engine']['clusters']}); none {c['cal_none']['pct']:.2f}; "
                       f"S0 {c['S0']['pct']:.2f}; S_wifi {c['S_wifi']['pct']:.2f}")
        lines.append("| " + " | ".join(row) + " |")
    t2 = res["table2"]

    def arow(q, d):
        lab = ["above chance" if d["ABOVE_CHANCE"] else "not above chance",
               "beyond speed" if d["BEYOND_SPEED"] else ("below speed" if d["BELOW_SPEED"] else "not beyond speed")]
        return f"| {q} | `{d['model']}` on {d['cell'].replace('_', ' ')} | {_ci(d)} ({d['clusters']}) | {', '.join(lab)} |"

    def crow(q, d):
        return (f"| {q} | `{d['a']}` minus `{d['b']}` on {d['cell'].replace('_', ' ')} ({d['a_pct']:.2f} against "
                f"{d['b_pct']:.2f}) | {_dci(d)} ({d['clusters']}) | {d['label']} |")
    lines += ["", "| question | comparison | figure [95 % interval] (clusters) | label |", "|---|---|---|---|"]
    for d in t2["Q1_across_days_same_room_only"]:
        lines.append(arow("1. across days, same room only", d))
    for d in t2["Q2_across_rooms_zero_shot"]["accuracy"]:
        lines.append(arow("2. across rooms, zero-shot", d))
    for d in t2["Q2_across_rooms_zero_shot"]["against_same_room_only"]:
        lines.append(crow("2. zero-shot against same room only", d))
    for d in t2["Q3_one_day_of_new_room_data"]:
        lines.append(crow("3. one day of new-room data", d))
    for d in t2["Q3_information_A3"]:
        lines.append(crow("3. (information) on A3", d))
    for d in t2["tracking_deployed_split"]:
        lines.append(arow("tracking's deployed split", d))
    ns = t2["never_sees_an_identification_walk"]
    for d in ns["across_days"]:
        lines.append(arow("no identification walk: across days", d))
    for d in ns["across_rooms"]:
        lines.append(arow("no identification walk: across rooms", d))
    for d in ns["one_day_of_new_room_data"]:
        lines.append(crow("no identification walk: one day of new-room data", d))
    for d in ns["one_day_information_A3"]:
        lines.append(crow("no identification walk: (information) on A3", d))
    for d in t2["what_B1_identification_walks_add"]:
        lines.append(crow("what B1's identification walks add", d))
    ls = res["loso_speed_controls"]
    lines += ["", f"| tracking walks (loso_*_v{VER}) | walks | engine | two-press | S0 | S_wifi | engine minus S0 | two-press minus S0 |",
              "|---|---|---|---|---|---|---|---|"]
    for kk in SESSIONS + ("room_A", "room_B", "pooled"):
        v = ls[kk]
        lines.append(f"| {kk.replace('_', ' ')} | {v['engine']['n']} | {_ci(v['engine'])} | {_ci(v['two_press'])} | {_ci(v['S0'])} | "
                     f"{_ci(v['S_wifi'])} | {_dci(v['engine_minus_S0'])} {v['engine_minus_S0']['label']} | "
                     f"{_dci(v['two_press_minus_S0'])} {v['two_press_minus_S0']['label']} |")
    txt = "\n".join(lines)
    print(txt)
    return txt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("calnone", "score", "tables"))
    ap.add_argument("--model")
    ap.add_argument("--session")
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--version", type=int, default=4, help="the engine version (default 4: everything as before)")
    a = ap.parse_args(argv)
    if a.version != 4:
        set_version(a.version)
    if a.what == "calnone":
        calnone(a.model, a.session, a.device)
    elif a.what == "score":
        score()
    else:
        tables()
    return 0


if __name__ == "__main__":
    sys.exit(main())
