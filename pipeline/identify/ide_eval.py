"""ide_eval. The engine's figures (`runs/identify/engine/PLAN.md`, section 4), from the harness's replays only
(`ide_replay`). No training. Development evaluation, all data seen.

1. identification walks: `loso_B2` replaying B2 and `loso_B1` replaying B1, pooled; blocks, S0 and the paired
   difference, the engine without its pace components, per participant, confusion, deployment measures;
   CAL-others as information;
2. leave one session out on the tracking passes (known route);
3. the one-press cost against the two-press configuration (CAL-causal), paired;
4. T sensitivity (information);
5. latency.

    PYTHONPATH=. python3 -m pipeline.identify.ide_eval [--device mps] [--version 5]

`--version 5` (engine v5, 10 Oct): the same figures from the `*_v5` replays, written to eval_v5.json (CAL-others through v5's
three windows and room weight; a section that cannot be computed for v5 is labelled); without it everything is v4's.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ide_replay as RP
from pipeline.identify import ide_train as IT
from pipeline.identify import idmax_common as IC
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L

CL = np.array(L.CLASSES)
FOLDS = {"toB2": "B2", "toB1": "B1"}
SUF = EN.SUFFIX          # engine v2 (the cadence bug fix); `--v1` sets "" to reproduce the v1 evaluation
TW = EN.T_S              # the engine's window (engine v4: 4.0 s; `--v1`: 3.0 s)


def wkey(model: str) -> str:
    """The Wi-Fi speed column a model was trained with (engine v4: its end detector's alpha, in its manifest)."""
    p = os.path.join(EN.ENG, "models", model, "manifest.json")
    a = json.load(open(p)).get("alpha") if os.path.exists(p) else None
    return "wifi_speed" if a in (None, 0.5) else f"wifi_speed_a{a}"
OUT = os.path.join(EN.ENG, "eval")


def labels(T: float, gs: bool) -> dict:
    meta = json.load(open(os.path.join(EN.bank_dir(T) if SUF else os.path.join(EN.ENG, f"bank_T{T:.1f}{'_gs' if gs else ''}"), "meta.json")))["passes"]
    a = {k: np.array([m[k] for m in meta]) for k in ("session", "room", "kind", "block", "anon", "path", "t_start", "t_end",
                                                      "press_speed_m_s", "wifi_speed")}
    if "wifi_speed_a0.2" in meta[0]:
        a["wifi_speed_a0.2"] = np.array([m["wifi_speed_a0.2"] for m in meta], float)
    return a


def replay_arrays(name: str) -> dict:
    z = np.load(os.path.join(RP.OUT, f"{name}.npz"))
    return {k: z[k] for k in z.files}


def walks_set(T: float, gs: bool, model_of=lambda f: f"loso_{FOLDS[f]}{SUF}") -> dict:
    """Both folds' identification-walk windows, pooled, with labels (`idw_eval.masks` / `deployment` keys)."""
    a = labels(T, gs)
    parts = []
    for f, s in FOLDS.items():
        r = replay_arrays(f"{model_of(f)}_{s}_T{T:.1f}")
        k = a["kind"][r["te"]] == "idcap"
        parts.append({kk: v[k] for kk, v in r.items() if len(v) == len(k)} | {"fold": np.full(int(k.sum()), f)})
    d = {kk: np.concatenate([p[kk] for p in parts]) for kk in parts[0]}
    te = d["te"]
    d.update({"who": a["anon"][te], "block": a["block"][te], "path": a["path"][te], "session": a["session"][te],
              "t_start": a["t_start"][te], "t_end": a["t_end"][te]})
    return d


def correct(lp, who) -> np.ndarray:
    return (CL[lp.argmax(1)] == who).astype(float)


def blocks(d, lp) -> dict:
    c = correct(lp, d["who"])
    out = {}
    for b, m in EV.masks(d).items():
        out[b] = EV._boot(c[m], d["who"][m]) | {f: EV._boot(c[m & (d["fold"] == f)], d["who"][m & (d["fold"] == f)])["pct"] for f in FOLDS}
    return out


def s0(d, gs: bool) -> np.ndarray:
    """S0: press speed alone (an LDA on it), trained on the other day's identification walks, as `idw_core.s0`."""
    from pipeline.identify import idv2_core as C
    a = labels(TW, gs)
    out = np.zeros((len(d["te"]), 6))
    for f, s in FOLDS.items():
        k = d["fold"] == f
        other = "B1" if s == "B2" else "B2"
        tr = np.flatnonzero((a["session"] == other) & (a["kind"] == "idcap"))
        P, cl = C.lda_proba(a["press_speed_m_s"][tr][:, None], a["press_speed_m_s"][d["te"][k]][:, None], a["anon"][tr])
        out[k] = L._order(C.logp_from_proba(P), cl)
    return out


def cal_others(d, gs: bool, device: str) -> np.ndarray:
    """Information only: each window calibrated on every window of its session by the other five people."""
    import pickle
    bdir = EN.bank_dir(TW) if SUF else os.path.join(EN.ENG, f"bank_T3.0{'_gs' if gs else ''}")
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    X = np.load(os.path.join(bdir, "features.npy"))
    maps = pickle.load(open(os.path.join(bdir, "maps.pkl"), "rb"))
    a = labels(TW, gs)
    mode = RP.direction_mode()

    def ex_of(i, key="wifi_speed"):
        m = meta[i]
        path = m["engine_path"] if (m["kind"] == "idcap" and mode == "detected") else m["path"]
        return {"features": X[i], "maps": maps[i], "wifi_speed": m[key], "path": path}
    out = np.zeros((len(d["te"]), 6))
    for f, s in FOLDS.items():
        model = EN.Model(os.path.join(EN.ENG, "models", f"loso_{s}{SUF}"), device)
        key = wkey(f"loso_{s}{SUF}")
        if model.version >= 5:                      # engine v5: the walk's offset windows (`ilb_extract tta`, as replayed)
            tt = pickle.load(open(os.path.join("runs", "identify", "best", "extract", "tta", f"{s}.pkl"), "rb"))
            tix = {(int(r), f"{o:.2f}"): j for j, (r, o) in enumerate(zip(tt["rows"], tt["offset"]))}
            cols = EN.v2_columns(json.load(open(EN.DEV_NAMES)))
            alpha = json.load(open(os.path.join(EN.ENG, "models", f"loso_{s}{SUF}", "manifest.json")))["alpha"]

            def offs(i):
                exs = []
                for o in model.offsets:
                    k_ = tix[(int(i), f"{o:.2f}")]
                    fv = np.zeros(X.shape[1], np.float64)
                    fv[cols] = tt["F"][k_]
                    exs.append({"features": fv, "maps": tt["maps"][k_], "wifi_speed": float(tt[f"speed_{alpha}"][k_]),
                                "path": str(tt["path_used"][k_])})
                return exs
        for p in L.CLASSES:
            k = np.flatnonzero((d["fold"] == f) & (d["who"] == p))
            pool = np.flatnonzero((a["session"] == s) & (a["anon"] != p))
            sess = EN.Session(model)
            sess.set_pool([ex_of(i, key) for i in pool])
            for j in k:
                if model.version >= 5:
                    i = int(d["te"][j])
                    exs = [ex_of(i, key)] + offs(i)
                    out[j] = sess.combine([sess.classify(e) for e in exs], model.weight(s[0], "id_spot"))["ensemble"]
                else:
                    out[j] = sess.classify(ex_of(int(d["te"][j]), key))["ensemble"]
    return out


def two_press(d, gs: bool, device: str) -> np.ndarray:
    """The two-press configuration's ensemble on the same windows' passes, CAL-causal (`idz_core.apply`)."""
    from pipeline.identify import idz_core as Z
    from pipeline.identify import idz_run as ZR
    out = np.zeros((len(d["te"]), 6))
    for f, s in FOLDS.items():
        k = d["fold"] == f
        if not gs:
            zp = os.path.join("runs", "identify", "audit", "outputs", f"B1_to{s}_causal.npz")
            if not os.path.exists(zp) and SUF not in ("", EN.SUFFIX):    # engine v5: removed 6 Oct (3f3612b4), recovered byte for byte
                zp = os.path.join("runs", "identify", "v5", "recovered", "two_press", f"B1_to{s}_causal.npz")
            z = np.load(zp)
            comp = {c: z[c] for c in Z.COMPONENTS}
            te = z["te"]
        else:
            p = os.path.join(EN.ENG, "twopress", f"GS_to{s}_causal.npz")
            if not os.path.exists(p):
                cfg = {"bank": os.path.join("runs", "identify", "audit", "bank_gs"), "cols": "v2", "layout": False, "fn": False, "amp_norm": True}
                bank = ZR.bank_of(cfg["bank"])
                a = bank["a"]
                te = np.flatnonzero((a["session"] == s) & (a["kind"] == "idcap"))
                md = os.path.join("runs", "identify", "audit", "models", f"GS_to{s}")
                comp = Z.apply(bank, md, md, te, Z.calibration_groups(a, te, "causal"), cfg, device=device)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                np.savez(p, te=te, **comp)
            z = np.load(p)
            comp = {c: z[c] for c in Z.COMPONENTS}
            te = z["te"]
        ens = Z.fuse(comp, "F0")
        pos = {int(r): j for j, r in enumerate(te)}
        out[k] = ens[[pos[int(r)] for r in d["te"][k]]]
    return out


def latency(d) -> dict:
    lat = d["latency_s"]
    after_end = d["t0"] + d["wait_s"] + (d["latency_s"] - d["wait_s"]) + (d["t_dec"] - d["t0"] - d["wait_s"]) - d["t_end"]
    q = lambda v: {"median": round(float(np.median(v)), 3), "p90": round(float(np.percentile(v, 90)), 3),  # noqa: E731
                   "max": round(float(np.max(v)), 3)}
    return {"after_window_end_s": q(lat), "after_recorded_end_press_s": q(after_end),
            "wait_for_packets_s": q(d["wait_s"]), "extract_s": q(d["extract_s"]), "model_s": q(d["model_s"]),
            "calibration_update_s": q(d["update_s"][np.isfinite(d["update_s"])])}


def run(device: str = "cpu") -> dict:
    gs = IT.gs_adopted()
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "gs_adopted": gs,
           "direction_mode": RP.direction_mode(), "T": TW, "calibration": "causal: every earlier window of the session"}
    d = walks_set(TW, gs)
    nat = EV.masks(d)["natural_both"]
    c = correct(d["ensemble"], d["who"])
    res["walks"] = {"engine": blocks(d, d["ensemble"]), "engine_without_pace": blocks(d, d["ensemble_nopace"])}
    s0lp = s0(d, gs)
    res["walks"]["S0"] = blocks(d, s0lp)
    cs0 = correct(s0lp, d["who"])
    res["walks"]["engine_minus_S0"] = {b: EV.paired(c[m], cs0[m], d["who"][m]) for b, m in EV.masks(d).items()}
    res["walks"]["per_participant_natural"] = {p: round(100 * float(c[nat & (d["who"] == p)].mean()), 2) for p in L.CLASSES}
    pred = CL[d["ensemble"].argmax(1)]
    res["walks"]["confusion_natural_rows_true_P1_to_P6"] = [[int(np.sum(nat & (d["who"] == t) & (pred == q))) for q in L.CLASSES] for t in L.CLASSES]
    res["walks"]["deployment"] = EV.deployment(d, None)
    conf = d["confidence"].max(1)
    res["walks"]["displayed_confidence_median"] = {"right": round(float(np.median(conf[nat & (c == 1)])), 3),
                                                   "wrong": round(float(np.median(conf[nat & (c == 0)])), 3)}
    # the one-press cost (information)
    tp = two_press(d, gs, device)
    ctp = correct(tp, d["who"])
    res["one_press_cost"] = {"two_press_config": "B1+GS" if gs else "B1", "two_press_calibration": "CAL-causal (earlier recordings)",
                             "two_press": blocks(d, tp),
                             "engine_minus_two_press": {b: EV.paired(c[m], ctp[m], d["who"][m]) for b, m in EV.masks(d).items()}}
    res["one_press_cost"]["LOSES_MORE_THAN_5_NATURAL"] = bool(res["one_press_cost"]["engine_minus_two_press"]["natural_both"]["pct"] < -5.0)
    # CAL-others (information)
    co = cal_others(d, gs, device)
    res["walks"]["cal_others_information"] = blocks(d, co)
    # leave one session out, tracking passes (known route)
    a = labels(TW, gs)
    loso, preds = {}, {}
    for s in L.SESSIONS:
        r = replay_arrays(f"loso_{s}{SUF}_{s}_T{TW:.1f}")
        k = a["kind"][r["te"]] == "track"
        te = r["te"][k]
        preds[s] = (te, correct(r["ensemble"][k], a["anon"][te]))
        loso[s] = EV._boot(preds[s][1], a["anon"][te])
    for room in ("A", "B"):
        te = np.concatenate([preds[s][0] for s in L.SESSIONS if s[0] == room])
        cc = np.concatenate([preds[s][1] for s in L.SESSIONS if s[0] == room])
        loso[f"room_{room}"] = EV._boot(cc, a["anon"][te])
    res["loso_tracking_known_route"] = loso
    # T sensitivity (information)
    tsens = {}
    for T in (2.5, 3.5):
        try:
            dt = walks_set(T, gs, model_of=lambda f, T=T: f"T{T}_{f}{SUF}")
        except FileNotFoundError:
            continue
        tsens[f"T{T}"] = blocks(dt, dt["ensemble"])
    if not tsens and SUF not in ("", EN.SUFFIX):
        tsens["not_computed"] = f"no T-variant models exist for engine {SUF[1:]} (the T sensitivity is v4's, information only)"
    res["T_sensitivity_information"] = tsens
    # latency: every replayed decision at the engine's window, and the identification walks alone
    alld = {}
    for s in L.SESSIONS:
        r = replay_arrays(f"loso_{s}{SUF}_{s}_T{TW:.1f}")
        te = r["te"]
        for kk in ("latency_s", "wait_s", "extract_s", "model_s", "update_s", "t0", "t_dec"):
            alld.setdefault(kk, []).append(r[kk])
        alld.setdefault("t_end", []).append(a["t_end"][te])
    alld = {k: np.concatenate(v) for k, v in alld.items()}
    res["latency"] = {"all_decisions": latency(alld), "identification_walks": latency(d)}
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, f"eval{SUF}.json"), "w").write(txt)
    head = {"natural": res["walks"]["engine"]["natural_both"], "S0": res["walks"]["S0"]["natural_both"],
            "engine_minus_S0": res["walks"]["engine_minus_S0"]["natural_both"],
            "one_press_cost": res["one_press_cost"]["engine_minus_two_press"]["natural_both"],
            "room_A": loso["room_A"], "room_B": loso["room_B"], "latency": res["latency"]["identification_walks"]["after_window_end_s"]}
    print(json.dumps(head, indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--v1", action="store_true", help="the engine v1 models and banks (the cadence bug unfixed)")
    ap.add_argument("--version", type=int, default=4, help="the engine version (default 4: everything as before)")
    a = ap.parse_args(argv)
    global SUF, TW
    SUF = "" if a.v1 else (EN.SUFFIX if a.version == 4 else f"_v{a.version}")
    TW = 3.0 if a.v1 else EN.T_S
    run(a.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
