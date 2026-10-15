"""ils_common. The identification lever screen (`reports/BRIEF_ID_LEVER_SCREEN_2026-10-01.md`; every rule fixed in
`runs/identify/engine/PLAN.md`, the note of 2026-10-01 17:18): the shared data, the scoring against engine v2, the
promise rule and the lever records.

Development evaluation, all data seen. A screen: nothing here changes the engine.
"""

from __future__ import annotations

import json
import os
import re
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L

OUT = os.path.join("runs", "identify", "lever_screen")
LEVERS = os.path.join(OUT, "levers")
SESS = ("B2", "B1")                      # loso_B2_x replays B2 ("to B2"); loso_B1_x replays B1 ("to B1")
NAME = {"P1": "PA5", "P2": "PA1", "P3": "PA2", "P4": "PA3", "P5": "PA4", "P6": "PA6"}
CL = np.array(L.CLASSES)
COMPS = tuple(W.COMPONENTS)
FEATC = tuple(W.FEAT)
CNNC = ("cnn", "cnn_prior", "cnn_perlink_prior")
V2 = "_x"                                # engine v2's banks, models and replays, pinned (engine v3 moved EN.SUFFIX on)
V2_PA1 = 63                           # engine v2: natural walks named PA1, of 180 (the promise rule's ceiling)
LABEL = "development evaluation, all data seen (a screen: exploratory)"

_D = {}


def data() -> dict:
    """Engine v2's bank (labels, the 630 gait columns), its two walks-fold replays and their training rows."""
    if _D:
        return _D
    bdir = os.path.join(EN.ENG, f"bank_T3.0{V2}")
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    names = json.load(open(os.path.join(bdir, "feature_names.json")))
    X = np.load(os.path.join(bdir, "features.npy")).astype(np.float64)
    cols = EN.v2_columns(names)
    a = {k: np.array([m[k] for m in meta]) for k in ("session", "room", "kind", "block", "anon", "path", "wifi_speed",
                                                      "t_start")}
    a["layout"] = np.where(a["kind"] == "idcap", "id_spot", "home")      # as `ide_replay.replay` sets it
    rep = {}
    for s in SESS:
        z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}{V2}_{s}_T3.0.npz"))
        rep[s] = {k: z[k] for k in z.files}
    tr = {s: np.load(os.path.join(EN.ENG, "models", f"loso_{s}{V2}", "train_rows.npy")) for s in SESS}
    _D.update({"a": a, "X": X, "G": X[:, cols], "gnames": [names[j] for j in cols], "names": names, "rep": rep,
               "tr": tr, "meta": meta, "bank": bdir})
    return _D


def walks(d: dict) -> dict:
    """Per session, the replay positions of its natural identification walks (60 on B2, 120 on B1)."""
    out = {}
    for s in SESS:
        te = d["rep"][s]["te"]
        out[s] = np.flatnonzero((d["a"]["kind"][te] == "idcap") & (d["a"]["block"][te] == "natural"))
    return out


def ensemble(comps: dict, use=COMPS) -> np.ndarray:
    """The engine's fusion: the equal-weight sum of the components' normalised log-probabilities, normalised."""
    return C.normalise_logp(sum(np.asarray(comps[c]) for c in use))


def replay_comps(d: dict, s: str) -> dict:
    return {c: d["rep"][s][f"c_{c}"] for c in COMPS}


def _flat(ens: dict, d: dict) -> dict:
    wk = walks(d)
    ok, who, fold, pred = [], [], [], []
    for s in SESS:
        k = wk[s]
        te = d["rep"][s]["te"][k]
        p = CL[np.asarray(ens[s])[k].argmax(1)]
        ok.append((p == d["a"]["anon"][te]).astype(float))
        who.append(d["a"]["anon"][te])
        fold.append(np.full(len(k), s))
        pred.append(p)
    return {"ok": np.concatenate(ok), "who": np.concatenate(who), "fold": np.concatenate(fold),
            "pred": np.concatenate(pred)}


def baseline(d: dict) -> dict:
    """Engine v2 as replayed: the reference every lever is paired against."""
    return _flat({s: d["rep"][s]["ensemble"] for s in SESS}, d)


def score(ens: dict, d: dict) -> dict:
    """A lever's natural walks against engine v2: accuracy, the paired change (bootstrap over participants, 10,000
    resamples, seed 0), per fold, walks named PA1, PA2, per person."""
    f, b = _flat(ens, d), baseline(d)
    assert np.array_equal(f["who"], b["who"]) and np.array_equal(f["fold"], b["fold"])
    r = {"natural": EV._boot(f["ok"], f["who"]), "paired": EV.paired(f["ok"], b["ok"], f["who"])}
    for s in SESS:
        m = f["fold"] == s
        r[f"to{s}"] = round(100 * float(f["ok"][m].mean()), 2)
        r[f"paired_to{s}"] = round(100 * float(f["ok"][m].mean() - b["ok"][m].mean()), 2)
    r["pa1"] = int((f["pred"] == "P2").sum())
    j = f["who"] == "P3"
    r["pa2"] = f"{int(f['ok'][j].sum())} of {int(j.sum())}"
    r["per_person"] = {NAME[p]: round(100 * float(f["ok"][f["who"] == p].mean()), 2) for p in L.CLASSES}
    r["_ok"], r["_pred"] = f["ok"], f["pred"]
    return r


def verdict(r: dict, S: float) -> str:
    """The PLAN note's promise rule (17:18)."""
    g = r["paired"]["pct"]
    if g >= 3.0 and r["paired_toB1"] > 0 and r["paired_toB2"] > 0 and g > S and r["pa1"] <= V2_PA1:
        return "PROMISING"
    if g <= -3.0 and -g > S:
        return "WORSE"
    return "FLAT"


_CODE = re.compile(r"\bP[1-6]\b")


def save(lid: str, tier: str, what: str, r: dict, seconds: float, extra: dict = None, mark: bool = True) -> dict:
    """One lever's record under `runs/identify/lever_screen/levers/<lid>.json` (names only; codes refused)."""
    rec = {"id": lid, "tier": tier, "lever": what, "label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "scored": "180 natural identification walks (loso_B2_x replaying B2, loso_B1_x replaying B1), causal",
           "train_sessions": {"toB2": ["A1", "A2", "A3", "B1"], "toB1": ["A1", "A2", "A3", "B2"]},
           "marked": mark, "seconds": round(float(seconds), 1),
           **{k: v for k, v in r.items() if not k.startswith("_")},
           "correct": [int(x) for x in r["_ok"]], "named": [NAME[p] for p in r["_pred"]]}
    if extra:
        rec["extra"] = extra
    txt = json.dumps(rec, indent=1, default=float)
    assert not _CODE.search(txt), f"{lid}: a participant code reached the record"
    os.makedirs(LEVERS, exist_ok=True)
    open(os.path.join(LEVERS, f"{lid}.json"), "w").write(txt)
    g = r["paired"]
    print(f"{time.strftime('%H:%M:%S')} {lid:<28} natural {r['natural']['pct']:6.2f}  paired {g['pct']:+6.2f} "
          f"[{g['ci95'][0]:+.2f}, {g['ci95'][1]:+.2f}]  B1 {r['toB1']:6.2f} B2 {r['toB2']:6.2f}  PA1 {r['pa1']:3d}  "
          f"PA2 {r['pa2']}  ({seconds:.0f} s)", flush=True)
    return rec


def dump(path: str, obj) -> None:
    txt = json.dumps(obj, indent=1, default=float)
    assert not _CODE.search(txt), f"{path}: a participant code reached the output"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(txt)
