"""iv5_figures. Engine v5's figures in the brief's section 4 structure (`prompt_identification_v5_ship.md`), from a store
of `ilc_outer` format ({model|session: (te, correct, log-probabilities)}) beside v4's (this morning's combine files):

- `expected`: from the Room A run's `split_A3` store (the configuration v5 ships), every number checked against the
  brief's section 4 (STOP if any differs); writes `runs/identify/v5/expected.json`;
- `scorecard`: the same from the v5 replays (step 5); writes `runs/identify/v5/scorecard_v5.json` and checks it equals
  `expected.json`.

Pooled cells concatenate the walks and resample participants jointly; intervals are paired participant bootstraps
(10,000 draws, seed 0, six clusters); S0 as `ilr_report.s0`.

    PYTHONPATH=. python3 -m pipeline.identify.iv5_figures expected
    PYTHONPATH=. python3 -m pipeline.identify.iv5_figures scorecard

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import ilb_core as B
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC
from pipeline.identify import ilr_core as R
from pipeline.identify import ilr_report as RR

V5D = os.path.join("runs", "identify", "v5")
LABEL = "development evaluation, all data seen"
CORE = [("xr_ABtrk B2 path", [("xr_ABtrk", "B2", "path")]), ("xr_ABtrk A3 path", [("xr_ABtrk", "A3", "path")]),
        ("xr_ABtrk A3+B2 path", [("xr_ABtrk", "A3", "path"), ("xr_ABtrk", "B2", "path")]),
        ("xr_A A3 path", [("xr_A", "A3", "path")]), ("xr_A B2 path", [("xr_A", "B2", "path")]),
        ("xr_A all B2", [("xr_A", "B2", k) for k in ("path", "natural", "slow", "fast")]),
        ("xr_B1 A3 path", [("xr_B1", "A3", "path")])]
IDW = [("loso natural", [("loso", "*", "natural")]), ("loso slow", [("loso", "*", "slow")]), ("loso fast", [("loso", "*", "fast")]),
       ("loso slow and fast", [("loso", "*", "slow"), ("loso", "*", "fast")])] + [
       (f"{m} B2 {k}", [(m, "B2", k)]) for m in ("xr_B1", "xr_A") for k in ("natural", "slow", "fast")]
ADD = [("A3 path", [("A3", "path")]), ("B2 path", [("B2", "path")]), ("B2 natural", [("B2", "natural")]),
       ("B2 slow", [("B2", "slow")]), ("B2 fast", [("B2", "fast")]),
       ("all 419", [("A3", "path"), ("B2", "path"), ("B2", "natural"), ("B2", "slow"), ("B2", "fast")])]

# the brief's section 4 (the numbers v5 must reproduce), as printed there
BRIEF = {
    "scorecard": {"Z": ("25.56", "33.61", "+8.06 [-1.11, +16.67]"), "D": ("27.59", "33.35", "+5.76 [+1.94, +9.31]"),
                  "score": ("26.57", "33.48", "+6.91 [+0.63, +12.75]")},
    "guard": {"loso|*|natural": ("37.78", "36.67"), "loso|*|slow": ("29.17", "33.33"), "loso|*|fast": ("30.25", "30.25")},
    "core": {"xr_ABtrk B2 path": ("30.83", "40.00 [27.50, 57.50]", "20.83", "+9.17 [+1.67, +16.67]", "+19.17 [+3.33, +35.83]"),
             "xr_ABtrk A3 path": ("25.00", "24.17 [15.83, 32.50]", "39.17", "-0.83 [-8.33, +6.67]", "-15.00 [-38.33, +0.00]"),
             "xr_ABtrk A3+B2 path": ("27.92", "32.08 [25.83, 43.33]", "30.00", "+4.17 [-1.67, +9.58]", "+2.08 [-13.33, +15.43]"),
             "xr_A A3 path": ("23.33", "26.67 [15.83, 39.17]", "38.33", "+3.33 [-9.17, +15.83]", "-11.67 [-39.17, +14.17]"),
             "xr_A B2 path": ("23.33", "29.17 [10.00, 50.00]", "20.83", "+5.83 [-5.83, +20.83]", "+8.33 [-15.00, +33.33]"),
             "xr_A all B2": ("24.41", "32.11 [15.38, 48.33]", "20.40", "+7.69 [-0.67, +15.67]", "+11.71 [-15.54, +36.00]"),
             "xr_B1 A3 path": ("30.00", "33.33 [22.50, 45.00]", "44.17", "+3.33 [-3.33, +9.17]", "-10.83 [-31.67, +11.67]")},
    "one_day_of_room_B": "+10.83 [-5.00, +24.17]",
    "per_participant": {"xr_A B2 path": [25, 60, 65, 0, 20, 5], "xr_ABtrk B2 path": [30, 80, 40, 35, 35, 20],
                        "xr_ABtrk A3 path": [25, 40, 10, 15, 20, 35]},
    "identification": {"loso natural": ("37.78", "36.67 [23.33, 50.00]", "38.33", "-1.67 [-22.78, +13.89]"),
                       "loso slow": ("29.17", "33.33 [9.17, 60.00]", "17.50", "+15.83 [-2.50, +39.17]"),
                       "loso fast": ("30.25", "30.25 [20.34, 41.18]", "16.81", "+13.45 [-1.68, +26.89]"),
                       "loso slow and fast": ("29.71", "31.80 [21.67, 43.04]", "17.15", "+14.64 [+0.00, +30.83]"),
                       "xr_B1 B2 natural": ("28.33", "35.00 [15.00, 55.00]", "30.00", "+5.00 [-16.67, +25.00]"),
                       "xr_B1 B2 slow": ("31.67", "35.00 [6.67, 68.33]", "16.67", "+18.33 [+3.33, +41.67]"),
                       "xr_B1 B2 fast": ("42.37", "33.90 [13.56, 53.33]", "16.95", "+16.95 [-11.86, +43.33]"),
                       "xr_A B2 natural": ("23.33", "38.33 [11.67, 66.67]", "23.33", "+15.00 [-28.33, +56.67]"),
                       "xr_A B2 slow": ("18.33", "33.33 [10.00, 63.33]", "16.67", "+16.67 [-26.67, +56.75]"),
                       "xr_A B2 fast": ("33.90", "30.51 [5.08, 57.63]", "20.34", "+10.17 [-13.56, +40.00]"),
                       "top-2": ("62.78", "61.11 [38.89, 81.11]", "67.78", "-6.67 [-16.67, +3.33]"),
                       "household of two": ("72.33", "75.56 [66.33, 84.22]", "76.78", "-1.22 [-7.89, +4.22]")},
    "b1_identification_walks_add": {"A3 path": ("24.17", "37.50", "+13.33 [+6.67, +21.67]"),
                                    "B2 path": ("40.00", "33.33", "-6.67 [-13.33, +2.50]"),
                                    "B2 natural": ("31.67", "33.33", "+1.67 [-5.00, +8.33]"),
                                    "B2 slow": ("43.33", "36.67", "-6.67 [-18.33, +6.67]"),
                                    "B2 fast": ("22.03", "27.12", "+5.08 [-6.90, +18.64]"),
                                    "all 419": ("32.22", "34.13", "+1.91 [-3.58, +6.92]")},
    "equal_training_size": ("33.33", "24.17", "+9.17 [+0.00, +18.33]"),
    "by_held_out_session": {"v5": ["30.00", "40.00", "37.50", "24.17", "35.83"], "S0": ["13.33", "24.17", "48.33", "41.67", "23.33"]},
    "room_a_weight": {"A1": ("26.67", "30.00"), "A2": ("34.17", "40.00"), "A1 and A2": ("30.42", "35.00", "+4.58 [+2.08, +7.08]")},
}


def f2(x) -> str:
    return f"{x:.2f}"


def ci(d) -> str:
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]"


def acc(d) -> str:
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def pooled(cells: list, st: dict) -> tuple:
    rr = [B.cell_rows_b(c, st) for c in cells]
    return np.concatenate([r[0] for r in rr]), np.concatenate([r[1] for r in rr])


def s0_pooled(cells: list) -> np.ndarray:
    return np.concatenate([RR.s0(c) for c in cells])


def compute(st: dict, v4: dict, w1: dict) -> dict:
    """Every section 4 figure of store `st` (v5) beside v4; `w1` = base A1+A3+A4+M3 at weight 1."""
    from pipeline.identify import idw_eval as EV
    from pipeline.identify import ixr_eval as XE
    who_all = PC.bank()["a"]["anon"]
    out = {"label": LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    zd = RR.zd(st, v4)
    f5, f4 = R.figures(st, v4), R.figures(v4, v4)
    out["scorecard"] = {k: (f2(f4[k]), f2(f5[k]), ci(zd[k])) for k in ("Z", "D", "score")}
    out["guard"] = {CO.key(c): (f2(100 * CO.cell_rows(c, v4)[1].mean()), f2(100 * CO.cell_rows(c, st)[1].mean())) for c in CO.GUARD}
    out["guard_holds"] = bool(f5["guard"])

    def row(cells):
        r5, ok5 = pooled(cells, st)
        r4, ok4 = pooled(cells, v4)
        assert np.array_equal(r5, r4)
        z0 = s0_pooled(cells)
        w = who_all[r5]
        return {"n": int(len(r5)), "v4": f2(100 * ok4.mean()), "v5": acc(EV._boot(ok5, w)), "S0": f2(100 * z0.mean()),
                "v5_minus_v4": ci(XE.paired(ok5, ok4, w)), "v5_minus_S0": ci(XE.paired(ok5, z0, w)),
                "label_v5_minus_v4": XE.paired(ok5, ok4, w)["label"], "label_v5_minus_S0": XE.paired(ok5, z0, w)["label"]}
    out["core"] = {nm: row(cells) for nm, cells in CORE}
    r_t, ok_t = pooled([("xr_ABtrk", "B2", "path")], st)
    r_a, ok_a = pooled([("xr_A", "B2", "path")], st)
    assert np.array_equal(r_t, r_a)
    out["one_day_of_room_B"] = ci(XE.paired(ok_t, ok_a, who_all[r_t]))
    out["per_participant"] = {}
    for nm, _c in CORE:
        r_, ok_ = pooled(dict(CORE)[nm], st)
        w = who_all[r_]
        vals = [100 * ok_[w == p].mean() for p in PC.CLASSES]
        out["per_participant"][nm] = [int(round(v)) if abs(v - round(v)) < 1e-9 else round(float(v), 2) for v in vals]
    out["identification"] = {nm: row(cells) for nm, cells in IDW}
    rows_, _o, lp = CO.cell_rows(("loso", "*", "natural"), st)
    w = who_all[rows_]
    rk5 = CO.ranking(lp, w)
    rk4 = CO.ranking(CO.cell_rows(("loso", "*", "natural"), v4)[2], w)
    rks = CO.ranking(B.s0_natural_lp(), w)
    for m_, nm in (("top2", "top-2"), ("group2", "household of two")):
        out["identification"][nm] = {"n": int(len(w)), "v4": f2(100 * rk4[m_].mean()), "v5": acc(EV._boot(rk5[m_], w)),
                                     "S0": f2(100 * rks[m_].mean()), "v5_minus_S0": ci(XE.paired(rk5[m_], rks[m_], w)),
                                     "v5_minus_v4": ci(XE.paired(rk5[m_], rk4[m_], w))}
    out["b1_identification_walks_add"] = {}
    for nm, parts in ADD:
        r1, ok1 = pooled([("xr_ABtrk", s, k) for s, k in parts], st)
        r2, ok2 = pooled([("xr_AB", s, k) for s, k in parts], st)
        assert np.array_equal(r1, r2)
        out["b1_identification_walks_add"][nm] = (f2(100 * ok1.mean()), f2(100 * ok2.mean()), ci(XE.paired(ok2, ok1, who_all[r1])))
    r1, ok1 = pooled([("xr_B1", "A3", "path")], st)
    r2, ok2 = pooled([("xr_ABtrk", "A3", "path")], st)
    out["equal_training_size"] = (f2(100 * ok1.mean()), f2(100 * ok2.mean()), ci(XE.paired(ok1, ok2, who_all[r1])))
    out["by_held_out_session"] = {"v5": [f2(100 * B.cell_rows_b(("loso", s, "path"), st)[1].mean()) for s in ("A1", "A2", "A3", "B1", "B2")],
                                  "S0": [f2(100 * RR.s0(("loso", s, "path")).mean()) for s in ("A1", "A2", "A3", "B1", "B2")]}
    rw = {}
    for s in ("A1", "A2"):
        rw[s] = (f2(100 * B.cell_rows_b(("loso", s, "path"), w1)[1].mean()), f2(100 * B.cell_rows_b(("loso", s, "path"), st)[1].mean()))
    ra, oka = pooled([("loso", "A1", "path"), ("loso", "A2", "path")], w1)
    rb, okb = pooled([("loso", "A1", "path"), ("loso", "A2", "path")], st)
    assert np.array_equal(ra, rb)
    rw["A1 and A2"] = (f2(100 * oka.mean()), f2(100 * okb.mean()), ci(XE.paired(okb, oka, who_all[ra])))
    out["room_a_weight"] = rw
    return out


def check(got: dict) -> list:
    """Every number of the brief's section 4 against `got`: the differing ones (empty: all reproduce)."""
    bad = []

    def eq(path, want, have):
        if str(want) != str(have):
            bad.append({"where": path, "brief": want, "computed": have})
    for k, v in BRIEF["scorecard"].items():
        eq(f"scorecard {k}", v, tuple(got["scorecard"][k]))
    for k, v in BRIEF["guard"].items():
        eq(f"guard {k}", v, tuple(got["guard"][k]))
    for k, v in BRIEF["core"].items():
        g = got["core"][k]
        eq(f"core {k}", v, (g["v4"], g["v5"], g["S0"], g["v5_minus_v4"], g["v5_minus_S0"]))
    eq("one day of Room B data", BRIEF["one_day_of_room_B"], got["one_day_of_room_B"])
    for k, v in BRIEF["per_participant"].items():
        eq(f"per participant {k}", v, got["per_participant"][k])
    for k, v in BRIEF["identification"].items():
        g = got["identification"][k]
        eq(f"identification {k}", v, (g["v4"], g["v5"], g["S0"], g["v5_minus_S0"]))
    for k, v in BRIEF["b1_identification_walks_add"].items():
        eq(f"B1 identification walks add {k}", v, tuple(got["b1_identification_walks_add"][k]))
    eq("equal training size", BRIEF["equal_training_size"], tuple(got["equal_training_size"]))
    for k, v in BRIEF["by_held_out_session"].items():
        eq(f"by held-out session {k}", v, got["by_held_out_session"][k])
    for k, v in BRIEF["room_a_weight"].items():
        eq(f"Room A weight {k}", v, tuple(got["room_a_weight"][k]))
    return bad


def stores() -> tuple:
    CO.OUTD = B.CB_OUT
    v4 = CO.load("v4")
    CO.OUTD = B.OUTD
    w1 = CO.load("A1+A3+A4+M3")
    CO.OUTD = os.path.join(R.RD, "stores")
    s5 = CO.load("split_A3")
    return s5, v4, w1


def expected() -> bool:
    s5, v4, w1 = stores()
    got = compute(s5, v4, w1)
    bad = check(got)
    got["source"] = "runs/identify/roomA/stores/split_A3.npz (A1+A3+A4+M3, C2: w_A 0.25, w_B 1, w_unseen 1, w_id 1)"
    got["brief_numbers_reproduced"] = not bad
    got["differences"] = bad
    os.makedirs(V5D, exist_ok=True)
    json.dump(got, open(os.path.join(V5D, "expected.json"), "w"), indent=1)
    print(json.dumps({"brief_numbers_reproduced": not bad, "differences": bad}, indent=1), flush=True)
    return not bad


def store_from_replays() -> dict:
    """{model|session: (te, correct, ensemble)} from the v5 replays (`iv5_replay replay`)."""
    from pipeline.identify import ide_replay as RP
    st = {}
    for m, (model, sessions) in CO.MODELS.items():
        for s in sessions:
            z = np.load(os.path.join(RP.OUT, f"{model[:-3]}_v5_{s}_T4.0.npz"))
            st[f"{m}|{s}"] = (z["te"], PC.accuracy(z["ensemble"], z["te"]), z["ensemble"])
    return st


def _norm(x):
    return json.loads(json.dumps(x))


def scorecard() -> bool:
    """Step 5: the figures from the v5 replays; must equal expected.json (step 1) in every figure."""
    st = store_from_replays()
    _s5, v4, w1 = stores()
    got = compute(st, v4, w1)
    exp = json.load(open(os.path.join(V5D, "expected.json")))
    skip = {"built", "label", "source", "brief_numbers_reproduced", "differences"}
    diffs = {k: {"replays": _norm(got[k]), "expected": exp.get(k)} for k in got if k not in skip and _norm(got[k]) != exp.get(k)}
    got.update({"source": "the engine v5 replays, runs/identify/engine/replays/*_v5_*_T4.0.npz", "equals_expected": not diffs,
                "brief_numbers_reproduced": not check(got)})
    json.dump(got, open(os.path.join(V5D, "scorecard_v5.json"), "w"), indent=1)
    os.makedirs(os.path.join(V5D, "checks"), exist_ok=True)
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "PASSED": not diffs, "differences": diffs}
    json.dump(res, open(os.path.join(V5D, "checks", "scorecard_equal.json"), "w"), indent=1)
    print(json.dumps({"PASSED": not diffs, "n_differences": len(diffs)}), flush=True)
    return not diffs


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "expected":
        sys.exit(0 if expected() else 1)
    if what == "scorecard":
        sys.exit(0 if scorecard() else 1)
    sys.exit(0)
