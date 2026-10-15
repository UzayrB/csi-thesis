"""ilw_eval. The link-weighting run's identification tables (`runs/identify/linkweight/PREREG_LW.md`, section 6, LW7):
the `_lw` models (the forwarded speed) beside the shipped `_v4` models on the same walks, with `ixr_eval`'s intervals
(10,000 resamples, seed 0, clusters = participants) and labels; S0 beside every cell; S_wifi on the shipped and on the
new speed. The shipped figures are recomputed first and must equal `eval_xroom_v4.json` (the anchor).
Writes `runs/identify/linkweight/eval_lw.json` and `eval_lw_tables.md`.

    PYTHONPATH=. python3 -m pipeline.identify.ilw_eval

Exploratory development, all data seen. Nothing here is adopted.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilw_bank as LB
from pipeline.identify import ilw_cache as LC
from pipeline.identify import ilw_score as LS
from pipeline.identify import ixr_eval as XE

T = 4.0
XR = ("xr_AB", "xr_ABtrk", "xr_A")
SESSIONS = ("A1", "A2", "A3", "B1", "B2")


def col(model: str) -> str:
    a = json.load(open(os.path.join(EN.ENG, "models", f"{model}_v4", "manifest.json")))["alpha"]
    return "wifi_speed" if a == 0.5 else f"wifi_speed_a{a}"


def cell(c_new, c_ship, c0, csw0, csw1, who, rec) -> dict:
    d = {"new": XE.boot(c_new, who, rec), "shipped": XE.boot(c_ship, who, rec), "S0": XE.boot(c0, who, rec),
         "S_wifi_shipped": XE.boot(csw0, who, rec), "S_wifi_new": XE.boot(csw1, who, rec),
         "new_minus_shipped": XE.paired(c_new, c_ship, who), "new_minus_S0": XE.paired(c_new, c0, who),
         "shipped_minus_S0": XE.paired(c_ship, c0, who)}
    d["new_ABOVE_CHANCE"] = d["new"]["ci95"][0] > 16.67
    d["new_BEYOND_SPEED"] = d["new_minus_S0"]["ci95"][0] > 0
    d["new_BELOW_SPEED"] = d["new_minus_S0"]["ci95"][1] < 0
    return d


def run() -> dict:
    from pipeline.identify import idmax_common as IC
    a = XE.labels()
    rec = XE.recording_of_rows(a)
    meta_lw = json.load(open(os.path.join(LB.BANK_LW, "meta.json")))["passes"]
    new_col = {"wifi_speed": np.array([m["wifi_speed"] for m in meta_lw], float),
               "wifi_speed_a0.2": np.array([m["wifi_speed_a0.2"] for m in meta_lw], float)}
    est = json.load(open(os.path.join(LB.BANK_LW, "build.json")))["estimator"]
    ev = json.load(open(XE.OUT))
    res = {"label": LC.LABEL + "; nothing adopted", "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "estimator": est,
           "prereg": "runs/identify/linkweight/PREREG_LW.md", "anchor": {}, "xroom": {}, "loso": {}, "looks": []}
    # the anchor: the shipped figures recomputed from the existing replays
    for m in XR:
        tr = np.load(os.path.join(EN.ENG, "models", f"{m}_v4", "train_rows.npy"))
        for name, (s, kind, block) in XE.CELLS.items():
            z = XE.replay(f"{m}_v4", s)
            k = (a["kind"][z["te"]] == kind) & ((a["block"][z["te"]] == block) if block else True)
            te, w = z["te"][k], a["anon"][z["te"][k]]
            e = XE.boot(XE.correct(z["ensemble"][k], w), w, rec[te])
            s0 = XE.boot(XE.correct(XE.lda_one(a, "press_speed_m_s", tr, te), w), w, rec[te])
            ref = ev["table1"][f"{m}_v4"]["cells"][name]
            res["anchor"][f"{m}_v4 {name}"] = (e["pct"] == ref["engine"]["pct"] and e["ci95"] == ref["engine"]["ci95"]
                                               and s0["pct"] == ref["S0"]["pct"] and s0["ci95"] == ref["S0"]["ci95"])
    ls = XE.loso_speed(a, rec)                     # asserts its own anchors (one_press_cost and eval_v4)
    for kk in SESSIONS + ("room_A", "room_B", "pooled"):
        ref = ev["loso_speed_controls"][kk]
        res["anchor"][f"loso {kk}"] = all(ls[kk][x]["pct"] == ref[x]["pct"] and ls[kk][x]["ci95"] == ref[x]["ci95"]
                                          for x in ("engine", "S0"))
    res["ANCHOR_PASSED"] = all(res["anchor"].values())
    if not res["ANCHOR_PASSED"]:
        json.dump(res, open(os.path.join(LC.LW, "eval_lw.json"), "w"), indent=1, default=str)
        raise SystemExit("the anchor failed: LW7 BLOCKED")
    # tracking's split
    for m in XR:
        tr = np.load(os.path.join(EN.ENG, "models", f"{m}_v4", "train_rows.npy"))
        c = col(m)
        res["xroom"][m] = {}
        for s in ("A3", "B2"):
            z = XE.replay(f"{m}_v4", s)
            n = np.load(os.path.join(LS.SC, f"{m}_lw_{s}.npz"))
            assert np.array_equal(z["te"], n["te"])
            te = z["te"]
            s0 = XE.lda_one(a, "press_speed_m_s", tr, te)
            sw0 = XE.lda_one(a, c, tr, te)
            sw1 = XE.lda_one({**a, c: new_col[c]}, c, tr, te)
            for name, (cs, kind, block) in XE.CELLS.items():
                if cs != s:
                    continue
                k = (a["kind"][te] == kind) & ((a["block"][te] == block) if block else True)
                w = a["anon"][te[k]]
                res["xroom"][m][name] = cell(*(XE.correct(lp[k], w) for lp in (n["ensemble"], z["ensemble"], s0, sw0, sw1)),
                                             w, rec[te[k]])
                res["looks"].append({"date": "2026-10-10", "model": f"{m}_lw", "cell": name, "session": s})
    # the leave-one-session-out tracking walks
    parts = {x: [] for x in ("new", "ship", "s0", "sw0", "sw1", "who", "rec", "room", "ses")}
    for s in SESSIONS:
        m = f"loso_{s}"
        tr = np.load(os.path.join(EN.ENG, "models", f"{m}_v4", "train_rows.npy"))
        z = XE.replay(f"{m}_v4", s)
        n = np.load(os.path.join(LS.SC, f"{m}_lw_{s}.npz"))
        assert np.array_equal(z["te"], n["te"])
        k = a["kind"][z["te"]] == "track"
        te = z["te"][k]
        w = a["anon"][te]
        c = col(m)
        parts["new"].append(XE.correct(n["ensemble"][k], w))
        parts["ship"].append(XE.correct(z["ensemble"][k], w))
        parts["s0"].append(XE.correct(XE.lda_one(a, "press_speed_m_s", tr, te), w))
        parts["sw0"].append(XE.correct(XE.lda_one(a, c, tr, te), w))
        parts["sw1"].append(XE.correct(XE.lda_one({**a, c: new_col[c]}, c, tr, te), w))
        parts["who"].append(w)
        parts["rec"].append(rec[te])
        parts["room"].append(a["room"][te])
        parts["ses"].append(a["session"][te])
        res["looks"].append({"date": "2026-10-10", "model": f"{m}_lw", "cell": f"{s} tracking walks", "session": s})
    P = {x: np.concatenate(v) for x, v in parts.items()}
    for kk, mask in [(s, P["ses"] == s) for s in SESSIONS] + [("room_A", P["room"] == "A"), ("room_B", P["room"] == "B"),
                                                              ("pooled", np.ones(len(P["who"]), bool))]:
        res["loso"][kk] = cell(P["new"][mask], P["ship"][mask], P["s0"][mask], P["sw0"][mask], P["sw1"][mask],
                               P["who"][mask], P["rec"][mask])
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(LC.LW, "eval_lw.json"), "w").write(txt)
    open(os.path.join(LC.LW, "eval_lw_tables.md"), "w").write(tables(res))
    print(tables(res))
    return res


def _ci(d) -> str:
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def _dci(d) -> str:
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}] {d['label']}"


def tables(res: dict) -> str:
    head = ("| model, cell | walks | new | shipped | new minus shipped | S0 | new minus S0 | S_wifi shipped / new | label |\n"
            "|---|---|---|---|---|---|---|---|---|")
    lines = [head]
    for m, cells in res["xroom"].items():
        for name, d in cells.items():
            lines.append(row(f"`{m}_lw` {name.replace('_', ' ')}", d))
    lines += ["", head]
    for kk, d in res["loso"].items():
        lines.append(row(f"`loso_*_lw` {kk.replace('_', ' ')} (tracking walks)", d))
    return "\n".join(lines)


def row(name: str, d: dict) -> str:
    lab = ["above chance" if d["new_ABOVE_CHANCE"] else "not above chance",
           "beyond speed" if d["new_BEYOND_SPEED"] else ("below speed" if d["new_BELOW_SPEED"] else "not beyond speed")]
    return (f"| {name} | {d['new']['n']} | {_ci(d['new'])} | {_ci(d['shipped'])} | {_dci(d['new_minus_shipped'])} | "
            f"{_ci(d['S0'])} | {_dci(d['new_minus_S0'])} | {d['S_wifi_shipped']['pct']:.2f} / {d['S_wifi_new']['pct']:.2f} | "
            f"{', '.join(lab)} |")


if __name__ == "__main__":
    run()
    sys.exit(0)
