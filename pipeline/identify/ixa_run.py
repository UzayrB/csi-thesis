"""ixa_run. The extras brief's section 2, stages E0 (anchor) and A1 to A3, in the PLAN's order, each against the current
best configuration (`runs/identify/final_extras/state.json`). A4 is `ixa_a4`. Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ixa_run anchor|A1|A2|A3
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import ixa_score as S
from pipeline.identify import ixa_speed as V

OUT = os.path.join("runs", "identify", "final_extras")
STATE = os.path.join(OUT, "state.json")
SESS = S.SESS


def state() -> dict:
    return json.load(open(STATE)) if os.path.exists(STATE) else {"best": {"A1": False, "A2": False, "A3": False}, "history": []}


def save(st: dict) -> None:
    json.dump(st, open(STATE, "w"), indent=1, default=str)


class Data:
    def __init__(self):
        self.B = S.base()
        self._w = None
        self.Goff = {}

    @property
    def W(self):
        if self._w is None:
            self._w = V.load()
        return self._w[0]

    @property
    def emp(self):
        if self._w is None:
            self._w = V.load()
        return self._w[1]

    def E(self, held):
        return V.empty_spectrum(self.emp, V.room_b_training_days(held))

    def current_speed(self, row) -> float:
        if row["contour"] is None or row["F"] < 0.3 or not np.isfinite(row["contour"]).any():
            return float("nan")
        return float(np.nanmedian(row["contour"]) * V.LAMBDA / (2.0 * row["F"]))

    def emp_days(self, days) -> np.ndarray:
        """E(f) from the given Room B days' empty idspot recordings; with no Room B day in a training set, E = 0
        (the estimator without subtraction; this arises only in A4's inner loop, for the A1A2A3 set)."""
        return V.empty_spectrum(self.emp, days) if days else np.zeros(10)

    def inputs(self, cfg: dict, held: str, offset: float = 0.0):
        """(pace, extra) for every bank row at one window offset, under configuration cfg, for the fold `held`."""
        return self.inputs_E(cfg, self.E(held), offset)

    def inputs_E(self, cfg: dict, E: np.ndarray, offset: float = 0.0):
        rows = self.W[offset]
        if offset == 0.0:
            base = self.B["a"]["wifi_speed"].astype(float)
        else:
            base = np.array([self.current_speed(r) for r in rows])
        pace = np.array([V.speed(r, E, base[i]) for i, r in enumerate(rows)]) if cfg["A1"] else base
        extra = np.array([V.profile(r, E) for r in rows]) if cfg["A2"] else None
        return pace, extra

    def offsets(self, cfg: dict, E: np.ndarray, tr: np.ndarray) -> list:
        """A3's extra training rows (t0 + 0.15 s and + 0.30 s) for the training rows tr."""
        out = []
        for o in (0.15, 0.30):
            po, eo = self.inputs_E(cfg, E, o)
            out.append({"G": self.G_off(o)[tr], "extra": None if eo is None else eo[tr], "pace": po[tr], "rows": tr})
        return out

    def G_off(self, offset: float):
        if offset not in self.Goff:
            from pipeline.identify import engine as EN
            X = np.load(os.path.join(V.A_DATA, f"features_off{offset:.2f}.npy")).astype(np.float64)
            self.Goff[offset] = X[:, EN.v2_columns(self.B["names"])]
        return self.Goff[offset]

    def score(self, cfg: dict) -> dict:
        """Every fold: the feature components retrained under cfg, the session re-scored, the ensembles."""
        a, G = self.B["a"], self.B["G"]
        ens = {}
        for s in SESS:
            tr = np.flatnonzero(a["session"] != s)
            pace, extra = self.inputs(cfg, s)
            off = self.offsets(cfg, self.E(s), tr) if cfg["A3"] else None
            models = S.train_feat(G, extra, pace, a, tr, off)
            feat = S.rescore(models, G, extra, pace, self.B["rep"][s])
            ens[s] = {"te": self.B["rep"][s]["te"], "ensemble": S.ensemble(feat, self.B["rep"][s]), "feat": feat}
        return ens


def c0_outputs(D: Data) -> dict:
    return {s: {"te": D.B["rep"][s]["te"], "ensemble": D.B["rep"][s]["ensemble"]} for s in SESS}


def anchor() -> dict:
    """E0: re-scoring with the saved C0 feature models, and with C0 retrained here, reproduces the replays."""
    import pickle
    D = Data()
    a, G = D.B["a"], D.B["G"]
    res = {}
    for s in SESS:
        rep = D.B["rep"][s]
        md = os.path.join("runs", "identify", "engine", "models", f"loso_{s}")
        saved = {c: pickle.load(open(os.path.join(md, f"feat_{c}.pkl"), "rb")) for c in S.W.FEAT}
        f1 = S.rescore(saved, G, None, a["wifi_speed"].astype(float), rep)
        tr = np.flatnonzero(a["session"] != s)
        f2 = S.rescore(S.train_feat(G, None, a["wifi_speed"].astype(float), a, tr), G, None, a["wifi_speed"].astype(float), rep)
        e1 = S.ensemble(f1, rep)
        res[s] = {"saved_models_max_abs_diff": float(max(np.abs(f1[c] - rep[f"c_{c}"]).max() for c in S.W.FEAT)),
                  "retrained_max_abs_diff": float(max(np.abs(f2[c] - rep[f"c_{c}"]).max() for c in S.W.FEAT)),
                  "ensemble_max_abs_diff": float(np.abs(e1 - rep["ensemble"]).max()),
                  "decisions_equal": int(np.sum(e1.argmax(1) == rep["ensemble"].argmax(1))), "n": int(len(e1))}
    res["PASSED"] = all(v["ensemble_max_abs_diff"] < 1e-9 and v["retrained_max_abs_diff"] < 1e-9 for k, v in res.items() if k in SESS)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "anchor.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


def physics_gate(D: Data) -> dict:
    """A1's identity-blind gate: Pearson(new speed, press speed) on the 180 natural walks, each with its fold's E."""
    from scipy.stats import pearsonr, spearmanr
    a = D.B["a"]
    rows = D.W[0.0]
    nat = np.flatnonzero((a["kind"] == "idcap") & (a["block"] == "natural"))
    v_new = np.array([V.speed(rows[i], D.E(a["session"][i]), np.nan) for i in nat])
    v_old = a["wifi_speed"][nat].astype(float)
    p = a["press_speed_m_s"][nat].astype(float)
    ok = np.isfinite(v_new)
    out = {"n": int(len(nat)), "nan_new": int((~ok).sum()), "pearson_new": round(float(pearsonr(v_new[ok], p[ok])[0]), 3),
           "spearman_new": round(float(spearmanr(v_new[ok], p[ok])[0]), 3), "pearson_current": round(float(pearsonr(v_old, p)[0]), 3),
           "median_abs_error_new": round(float(np.median(np.abs(v_new[ok] - p[ok]))), 3),
           "distinct_values_new": int(len(np.unique(np.round(v_new[ok], 6))))}
    allid = np.flatnonzero(a["kind"] == "idcap")
    va = np.array([V.speed(rows[i], D.E(a["session"][i]), np.nan) for i in allid])
    oka = np.isfinite(va)
    out["all_identification_walks_pearson_new"] = round(float(pearsonr(va[oka], a["press_speed_m_s"][allid][oka].astype(float))[0]), 3)
    out["GATE_PASSED"] = bool(out["pearson_new"] >= 0.70)
    return out


def stage(name: str) -> dict:
    st = state()
    D = Data()
    best_cfg = dict(st["best"])
    cand_cfg = {**best_cfg, name: True}
    res = {"item": name, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "best_before": best_cfg, "candidate": cand_cfg}
    if name == "A1":
        g = physics_gate(D)
        res["physics_gate"] = g
        if not g["GATE_PASSED"]:
            res.update({"ADOPT": False, "note": "physics gate not passed; A1 not tested for identity"})
            st["history"].append(res)
            save(st)
            print(json.dumps(res, indent=1, default=str), flush=True)
            return res
    a = D.B["a"]
    best = S.collect(c0_outputs(D) if not any(best_cfg.values()) else D.score(best_cfg), a)
    cand = S.collect(D.score(cand_cfg), a)
    res["best_table"], res["candidate_table"] = S.table(best), S.table(cand)
    res.update(S.rule(cand, best))
    if res["ADOPT"]:
        st["best"] = cand_cfg
    st["history"].append(res)
    save(st)
    print(json.dumps({k: res[k] for k in ("item", "paired_natural", "slow_change", "fast_change", "tracking_pooled_change",
                                          "condition_1", "condition_2", "condition_3", "ADOPT")}, indent=1, default=str), flush=True)
    return res


if __name__ == "__main__":
    {"anchor": anchor, "A1": lambda: stage("A1"), "A2": lambda: stage("A2"), "A3": lambda: stage("A3")}[sys.argv[1]]()
    sys.exit(0)
