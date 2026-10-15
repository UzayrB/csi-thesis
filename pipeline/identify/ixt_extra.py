"""ixt_extra. The teaching-pack addendum's AC2 (same day, confounded by recording) and AC3 (training without the slow and
fast identification walks), as `runs/identify/engine/PLAN.md`'s addendum note defines them. The full engine recipe
(`idz_core.train`, engine v2's bank `bank_T3.0_x`: the cadence bug fix), replayed through the engine (`ide_replay.replay`,
causal) and compared with engine v2's replays (`loso_<day>_x`). Information only; the engine does not change. Names, not
codes. Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_extra train sameday_B1|sameday_B2|nopaced_loso_B2|nopaced_loso_B1
    PYTHONPATH=. python3 -m pipeline.identify.ixt_extra replay <model> [--device mps]
    PYTHONPATH=. python3 -m pipeline.identify.ixt_extra report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idw_eval as EV
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "teaching", "extra")
BANK = EN.bank_dir(3.0)
ENGINE = lambda s: f"{EN.model_name(f'loso_{s}')}_{s}_T3.0"      # noqa: E731  engine v2's replay of session s
CODES = ("P1", "P2", "P3", "P4", "P5", "P6")
NAME = {anon(n): n for n in SIX}
CL = np.array(CODES)


def meta() -> list:
    return json.load(open(os.path.join(BANK, "meta.json")))["passes"]


def cycle_train_mask(m: list) -> np.ndarray:
    """AC2's split: within each recording (session, person, kind, block), passes by press time paired into cycles of
    two; cycles 1, 3, 5 (1-based) train, cycles 2, 4, 6 test."""
    rec = {}
    for i, p in enumerate(m):
        rec.setdefault((p["session"], p["anon"], p["kind"], p["block"]), []).append(i)
    train = np.zeros(len(m), bool)
    for rows in rec.values():
        rows = sorted(rows, key=lambda i: m[i]["t_start"])
        for j, i in enumerate(rows):
            train[i] = (j // 2) % 2 == 0
    return train


def rows_for(name: str, m: list) -> tuple:
    """(training rows, the held-out or replayed session) for a model name."""
    ses = np.array([p["session"] for p in m])
    kind = np.array([p["kind"] for p in m])
    blk = np.array([p["block"] for p in m])
    if name.startswith("sameday_"):
        day = name.split("_")[1]
        return np.flatnonzero((ses == day) & cycle_train_mask(m)), day
    held = name.split("_")[-1]
    other = "B1" if held == "B2" else "B2"
    keep = (ses != held) & ~((ses == other) & (kind == "idcap") & np.isin(blk, ("slow", "fast")))
    return np.flatnonzero(keep), held


def train(name: str) -> str:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    from pipeline.identify import idz_run as ZR
    out = os.path.join(OUT, "models", name)
    if os.path.exists(os.path.join(out, "meta_feat_cnn.json")):
        return out
    bank = L.load(BANK)
    tr, s = rows_for(name, meta())
    cfg = {"bank": BANK, "cols": "v2", "layout": False, "fn": False, "amp_norm": False, "engine_T": 3.0, "addendum": name,
           "engine_version": EN.ENGINE_VERSION}
    Z.train(bank, tr, out, cfg, device=ZR.device(), log=print)
    json.dump({"model": name, "engine_version": EN.ENGINE_VERSION, "training_sessions": sorted({meta()[int(i)]["session"] for i in tr}), "n_train": int(len(tr)),
               "rows": "same-day training cycles" if name.startswith("sameday") else "the fold's rows minus the other Room B day's slow and fast walks",
               "purpose": "teaching-pack addendum, information only; never used by the app"},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


def replay(name: str, device: str = "mps") -> str:
    from pipeline.identify import ide_replay as RP
    p = os.path.join(OUT, f"replay_{name}.npz")
    if os.path.exists(p):
        return p
    _tr, s = rows_for(name, meta())
    dec = RP.replay(s, os.path.join(OUT, "models", name), 3.0, False, device, RP.direction_mode())
    idx = RP.load_bank(3.0, False, v2=True)["index"]
    te = np.array([idx[(s, round(d["t0"], 6))] for d in dec])
    np.savez(p, te=te, ensemble=np.array([d["ensemble"] for d in dec]), ensemble_nopace=np.array([d["ensemble_nopace"] for d in dec]))
    return p


def blocks(ok, who, blk, path, nat_only=False) -> dict:
    nat = blk == "natural"
    masks = {"natural_both": nat, "natural_away": nat & (path == "A_fwd"), "natural_towards": nat & (path == "A_rev"),
             "slow": blk == "slow", "fast": blk == "fast", "all_paces": np.ones(len(ok), bool)}
    return {b: EV._boot(ok[mk], who[mk]) for b, mk in masks.items() if mk.any()}


def report() -> dict:
    from pipeline.identify import ixa_measures as M
    m = meta()
    a = {k: np.array([p[k] for p in m]) for k in ("session", "kind", "block", "anon", "path", "press_speed_m_s", "wifi_speed")}
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": "development evaluation, all data seen; information only",
           "engine_version": EN.ENGINE_VERSION, "bank": BANK}
    # AC2: same day
    trm = cycle_train_mask(m)
    res["AC2_same_day"] = {"label": "same day, confounded by recording", "days": {}}
    for day in ("B1", "B2"):
        z = np.load(os.path.join(OUT, f"replay_sameday_{day}.npz"))
        zc = np.load(os.path.join(EN.ENG, "replays", f"{ENGINE(day)}.npz"))
        assert np.array_equal(z["te"], zc["te"])
        k = (a["kind"][z["te"]] == "idcap") & ~trm[z["te"]]
        te = z["te"][k]
        who, blk, path = a["anon"][te], a["block"][te], a["path"][te]
        ok_s = (CL[z["ensemble"][k].argmax(1)] == who).astype(float)
        ok_c = (CL[zc["ensemble"][k].argmax(1)] == who).astype(float)
        res["AC2_same_day"]["days"][day] = {
            "train_sessions": [day + " (training cycles only)"], "test_session": day + " (test cycles)", "calibration": "causal",
            "same_day": blocks(ok_s, who, blk, path), "cross_day_engine_same_walks": blocks(ok_c, who, blk, path),
            "same_minus_cross_natural": EV.paired(ok_s[blk == "natural"], ok_c[blk == "natural"], who[blk == "natural"]),
            "n_test_walks": int(k.sum()), "chance_pct": 16.67}
    # AC3: without the slow and fast walks
    res["AC3_without_paced_training"] = {}
    walks_eng, walks_np = [], []
    for held in ("B2", "B1"):
        z = np.load(os.path.join(OUT, f"replay_nopaced_loso_{held}.npz"))
        zc = np.load(os.path.join(EN.ENG, "replays", f"{ENGINE(held)}.npz"))
        assert np.array_equal(z["te"], zc["te"])
        k = a["kind"][z["te"]] == "idcap"
        walks_np.append((z["te"][k], z["ensemble"][k], np.full(int(k.sum()), f"to{held}")))
        walks_eng.append((zc["te"][k], zc["ensemble"][k]))
    te = np.concatenate([w[0] for w in walks_np])
    d = {"te": te, "fold": np.concatenate([w[2] for w in walks_np]), "who": a["anon"][te], "block": a["block"][te], "path": a["path"][te]}
    e_np = np.concatenate([w[1] for w in walks_np])
    e_en = np.concatenate([w[1] for w in walks_eng])
    ok_np = (CL[e_np.argmax(1)] == d["who"]).astype(float)
    ok_en = (CL[e_en.argmax(1)] == d["who"]).astype(float)
    s0 = M.lda_one(a, "press_speed_m_s", d)
    sw = M.lda_one(a, "wifi_speed", d)
    ok0 = (CL[s0.argmax(1)] == d["who"]).astype(float)
    okw = (CL[sw.argmax(1)] == d["who"]).astype(float)
    mk = EV.masks(d)
    res["AC3_without_paced_training"] = {
        "train_sessions": {"to B2": "A1, A2, A3, B1 minus B1's slow and fast walks", "to B1": "A1, A2, A3, B2 minus B2's slow and fast walks"},
        "test_session": "B2 and B1 pooled", "calibration": "causal",
        "without_paced": {b: EV._boot(ok_np[x], d["who"][x]) for b, x in mk.items()},
        "engine": {b: EV._boot(ok_en[x], d["who"][x]) for b, x in mk.items()},
        "without_minus_engine": {b: EV.paired(ok_np[x], ok_en[x], d["who"][x]) for b, x in mk.items()},
        "engine_minus_S0": {b: EV.paired(ok_en[x], ok0[x], d["who"][x]) for b, x in mk.items()},
        "without_minus_S0": {b: EV.paired(ok_np[x], ok0[x], d["who"][x]) for b, x in mk.items()},
        "engine_minus_S_wifi": {b: EV.paired(ok_en[x], okw[x], d["who"][x]) for b, x in mk.items()},
        "without_minus_S_wifi": {b: EV.paired(ok_np[x], okw[x], d["who"][x]) for b, x in mk.items()}}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "extra.json"), "w"), indent=1, default=str)
    print(json.dumps({"AC2": {d_: (v["same_day"]["natural_both"], v["cross_day_engine_same_walks"]["natural_both"]) for d_, v in res["AC2_same_day"]["days"].items()},
                      "AC3_natural": res["AC3_without_paced_training"]["without_minus_engine"]["natural_both"]}, indent=1, default=str))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("train", "replay", "report"))
    ap.add_argument("name", nargs="?")
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    x = ap.parse_args()
    if x.what == "train":
        train(x.name)
    elif x.what == "replay":
        replay(x.name, x.device)
    else:
        report()
    sys.exit(0)
