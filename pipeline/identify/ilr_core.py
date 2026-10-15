"""ilr_core. The Room A run (`runs/identify/roomA/PLAN_RA.md`): the six bases rescored by `ilb_core`'s code with every
component's log-probabilities saved, the exactness check, the C1 and C2 weight mixes, Uzayr's selection rule, and the
pick's figures.

    PYTHONPATH=. python3 -m pipeline.identify.ilr_core components --base A1+A3+A4+A5+M3
    PYTHONPATH=. python3 -m pipeline.identify.ilr_core exact
    PYTHONPATH=. python3 -m pipeline.identify.ilr_core mix
    PYTHONPATH=. python3 -m pipeline.identify.ilr_core summary

Exploratory development, all data seen; selection uses the combine scorecard (A3 and B2).
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import ilb_core as B
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC

RD = os.path.join("runs", "identify", "roomA")
CMP = os.path.join(RD, "comps")
LABEL = "exploratory development, all data seen; selection uses the combine scorecard (A3 and B2)"
BASES = [B.canon(t) for t in (["A1", "A3", "A4", "A5", "M3"], ["A1", "A3", "A4", "M3"], ["F7", "A3", "A4", "A5", "M3"],
                              ["A1", "A3", "A4", "A5", "M3", "P1"], ["A1", "A3", "A4", "M3", "P1"],
                              ["F7", "A3", "A4", "A5", "M3", "P1"])]
WINNER = BASES[0]
GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
GRID_ID = (0.5, 1.0)
CORE = [("xr_A", "A3", "path"), ("xr_ABtrk", "A3", "path")]
# the split check (PLAN_RA's note, report-only): every scorecard cell restricted to one test session's walks
HALF = {"A3": {"Z": [("xr_B1", "A3", "path")],
               "D": [("loso", "A3", "path"), ("xr_AB", "A3", "path"), ("xr_A", "A3", "path"), ("xr_ABtrk", "A3", "path")],
               "G": []},
        "B2": {"Z": [("xr_A", "B2", "path"), ("xr_A", "B2", "natural")],
               "D": [("loso", "B2", "natural"), ("loso", "B2", "path"), ("xr_AB", "B2", "path"), ("xr_AB", "B2", "natural"),
                     ("xr_B1", "B2", "path"), ("xr_B1", "B2", "natural"), ("xr_ABtrk", "B2", "path")],
               "G": [("loso", "B2", "natural"), ("loso", "B2", "slow"), ("loso", "B2", "fast")]}}


# ------------------------------------------------------------------ R1: every component saved

def comps_multi(fl: dict, model: str, sessions: list, flags: list) -> dict:
    """`ilb_core.ens_multi_b` up to the ensemble (no M2, the shipped CNNs): {session: {key: array}} with keys
    "<window>|feat|<component>" and "<window>|cnn|<component>" in the order the ensemble sums them."""
    from pipeline.identify import ilb_p1 as P1
    b = PC.bank()
    zs = {s: np.load(os.path.join(CO.REP, f"{model}_{s}_T4.0.npz")) for s in sessions}
    cnn = {s: {c: z[f"c_{c}"] for c in PC.CNNC} for s, z in zs.items()}
    fds = {s: {"te": z["te"], "path_used": z["path_used"],
               "layout": np.where(b["kind"][z["te"]] == "idcap", "id_spot", "home")} for s, z in zs.items()}
    tr = np.load(os.path.join(CO.mdir(model), "train_rows.npy"))
    v, alpha = CO.speed_col(model)
    if fl.get("p1"):
        pv, why = P1.pace_column(sorted(set(b["a"]["session"][tr])), alpha)
        if pv is None:
            flags.append(f"{model}: P1 {why}")
        else:
            v = pv
    if fl.get("a5") and len(set(b["a"]["session"][tr])) < 2:
        flags.append(f"{model}: A5 has no partner on one training day; no mixed rows")
    extra = B.extra_rows(fl, tr, alpha)
    if extra is not None and fl.get("p1"):
        pth = b["kind"][extra["rows"]] == "track"
        extra["speed"] = np.where(pth, v[extra["rows"]] / extra["factor"], extra["speed"])
    models = B.train_feat_b(b["F"], v, tr, extra, mixup=bool(fl.get("a5")), m3=bool(fl.get("m3")))
    out = {}
    for s in sessions:
        tta, cache = None, None
        if fl.get("a4"):
            tta = B.tta_windows(s, alpha)
            cache = np.load(os.path.join(B.BD, "a4cache", f"{model}_{s}.npz"))
            assert np.array_equal(cache["te"], zs[s]["te"])
        comps = B.score_feat_b(models, b["F"], v, fds[s], tta, own_speed=not fl.get("p1"))
        rec = {"te": zs[s]["te"]}
        for wn, cm in comps.items():
            cn = cnn[s] if wn == "0" else {c: cache[f"c_{c}_{wn}"] for c in PC.CNNC}
            for c, a in cm.items():
                rec[f"{wn}|feat|{c}"] = a
            for c, a in cn.items():
                rec[f"{wn}|cnn|{c}"] = a
        out[s] = rec
    return out


def components(base: str) -> str:
    fl = B.flags_of(base)
    flags = []
    d = os.path.join(CMP, base)
    os.makedirs(d, exist_ok=True)
    for m, (model, sessions) in CO.MODELS.items():
        for s, rec in comps_multi(fl, model, sessions, flags).items():
            np.savez(os.path.join(d, f"{m}_{s}.npz"), **rec)
        print(f"{time.strftime('%H:%M:%S')} {base}: {model} {sessions}", flush=True)
    json.dump({"base": base, "flags": flags, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": LABEL},
              open(os.path.join(d, "DONE.json"), "w"), indent=1)
    return d


def load_comps(base: str) -> dict:
    out = {}
    for m, (_model, sessions) in CO.MODELS.items():
        for s in sessions:
            z = np.load(os.path.join(CMP, base, f"{m}_{s}.npz"))
            out[f"{m}|{s}"] = {k: z[k] for k in z.files}
    return out


def ensemble(rec: dict, w_row: np.ndarray) -> np.ndarray:
    """`ilb_core.ens_multi_b`'s arithmetic: per window, the components summed in order (feature components times w),
    normalised; the windows averaged and normalised when more than one."""
    from pipeline.identify import idv2_core as C
    wins = sorted({k.split("|")[0] for k in rec if "|" in k}, key=float)
    w = w_row[:, None]
    ens = []
    for wn in wins:
        s_ = 0
        for k in rec:
            if k.startswith(f"{wn}|feat|"):
                s_ = s_ + w * rec[k]
        for k in rec:
            if k.startswith(f"{wn}|cnn|"):
                s_ = s_ + 1.0 * rec[k]
        ens.append(C.normalise_logp(s_))
    return C.normalise_logp(np.mean(ens, axis=0)) if len(ens) > 1 else ens[0]


def store_of(cm: dict, wfun) -> dict:
    """{model|session: (te, correct, log-probabilities)} with the path weight wfun(model, session) and the
    identification walks' weight."""
    b = PC.bank()
    out = {}
    for key, rec in cm.items():
        m, s = key.split("|")
        te = rec["te"]
        wp, wi = wfun(m, s)
        w_row = np.where(b["kind"][te] == "track", wp, wi).astype(float)
        lp = ensemble(rec, w_row)
        out[key] = (te, PC.accuracy(lp, te), lp)
    return out


def exact() -> bool:
    """With every weight 1, W and B (without P1) reproduce this morning's ensembles (`runs/identify/best/outer/`)."""
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "bases": {}}
    ok = True
    for base in BASES[:2]:
        st = store_of(load_comps(base), lambda m, s: (1.0, 1.0))
        CO.OUTD = B.OUTD
        ref = CO.load(base)
        d = {k: float(np.abs(st[k][2] - ref[k][2]).max()) for k in ref}
        same = all(np.array_equal(st[k][0], ref[k][0]) and np.array_equal(st[k][1], ref[k][1]) for k in ref)
        res["bases"][base] = {"max_abs_diff": max(d.values()), "per_model_session": d, "same_rows_and_decisions": same}
        ok = ok and max(d.values()) == 0.0 and same
    res["PASSED"] = bool(ok)
    json.dump(res, open(os.path.join(RD, "exact.json"), "w"), indent=1)
    print(json.dumps({k: (v["max_abs_diff"], v["same_rows_and_decisions"]) for k, v in res["bases"].items()} |
                     {"PASSED": res["PASSED"]}), flush=True)
    return res["PASSED"]


# ------------------------------------------------------------------ R2: the mixes and the pick

def rooms_of(model: str) -> set:
    b = PC.bank()
    tr = np.load(os.path.join(CO.mdir(model), "train_rows.npy"))
    return {str(x)[0] for x in set(b["a"]["session"][tr])}


def figures(st: dict, v4: dict) -> dict:
    z = np.mean([CO.cell_rows(c, st)[1].mean() for c in CO.ZERO])
    d = np.mean([CO.cell_rows(c, st)[1].mean() for c in CO.CROSS])
    g = all(CO.cell_rows(c, st)[1].mean() >= CO.cell_rows(c, v4)[1].mean() - 0.05 for c in CO.GUARD)
    core = [CO.cell_rows(c, st)[1].mean() for c in CORE]
    out = {"Z": round(100 * z, 2), "D": round(100 * d, 2), "score": round(50 * (z + d), 4), "guard": bool(g),
           "xr_A_A3": round(100 * core[0], 2), "xr_ABtrk_A3": round(100 * core[1], 2),
           "core_mean": round(50 * (core[0] + core[1]), 4), "xr_ABtrk_B2": round(100 * CO.cell_rows(("xr_ABtrk", "B2", "path"), st)[1].mean(), 2)}
    for h, cc in HALF.items():
        zh = np.mean([B.cell_rows_b(c, st)[1].mean() for c in cc["Z"]])
        dh = np.mean([B.cell_rows_b(c, st)[1].mean() for c in cc["D"]])
        out.update({f"Z_{h}": round(100 * zh, 2), f"D_{h}": round(100 * dh, 2), f"score_{h}": round(50 * (zh + dh), 4),
                    f"guard_{h}": bool(all(B.cell_rows_b(c, st)[1].mean() >= B.cell_rows_b(c, v4)[1].mean() - 0.05 for c in cc["G"]))})
    return out


def mix() -> dict:
    CO.OUTD = B.CB_OUT
    v4 = CO.load("v4")
    seen = {m: rooms_of(model) for m, (model, _s) in CO.MODELS.items()}
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "mixes": []}
    for bi, base in enumerate(BASES):
        cm = load_comps(base)
        cache = {}
        for wa, wb, wu, wi in itertools.product(GRID, GRID, GRID, GRID_ID):
            def wfun(m, s, wa=wa, wb=wb, wu=wu, wi=wi):
                room = s[0]
                return (wu if room not in seen[m] else (wa if room == "A" else wb)), wi
            st = {}
            for key in cm:
                m, s = key.split("|")
                wp = wfun(m, s)
                if (key, wp) not in cache:
                    cache[(key, wp)] = store_of({key: cm[key]}, lambda *_: wp)[key]
                st[key] = cache[(key, wp)]
            f = figures(st, v4)
            f.update({"base": base, "base_order": bi, "w_A": wa, "w_B": wb, "w_unseen": wu, "w_id": wi,
                      "C1": bool(wa == wb == wu)})
            res["mixes"].append(f)
        print(f"{time.strftime('%H:%M:%S')} {base}: {len(GRID) ** 3 * len(GRID_ID)} mixes", flush=True)
    res["n_mixes"] = len(res["mixes"])
    sel = select(res["mixes"])
    res.update(sel)
    res["split"] = {h: select_half(res["mixes"], h) for h in ("A3", "B2")}
    json.dump(res, open(os.path.join(RD, "mixes.json"), "w"), indent=1)
    looks = {"label": LABEL, "built": res["built"], "n_configurations": res["n_mixes"],
             "model_session_looks_A3": 5 * res["n_mixes"], "model_session_looks_B2": 5 * res["n_mixes"],
             "note": "every mix of every base (the six bases at weight 1 included) is a configuration scored on A3 and B2"}
    json.dump(looks, open(os.path.join(RD, "looks.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in sel.items() if k != "tradeoff"}, indent=1), flush=True)
    print(f"trade-off set: {len(sel.get('tradeoff', []))}", flush=True)
    return res


def wdist(r: dict) -> float:
    return abs(r["w_A"] - 1) + abs(r["w_B"] - 1) + abs(r["w_unseen"] - 1) + abs(r["w_id"] - 1)


def select(mixes: list) -> dict:
    """PLAN_RA section 4."""
    q = [r for r in mixes if r["guard"] and r["xr_A_A3"] >= 25.0 and r["xr_ABtrk_A3"] >= 25.0 and r["Z"] >= 32.0 and r["D"] >= 31.0]
    out = {"n_qualifiers": len(q)}
    if q:
        top = max(r["score"] for r in q)
        tied = [r for r in q if r["score"] >= top - 0.25 - 1e-9]
        pick = sorted(tied, key=lambda r: (-r["core_mean"], -r["score"], r["base_order"], wdist(r)))[0]
        out.update({"pick": pick, "n_tied_within_0.25": len(tied), "top_score": top})
    g = [r for r in mixes if r["guard"]]
    keyf = lambda r: (r["core_mean"], r["Z"], r["D"])
    front = [r for r in g if not any(all(x > y for x, y in zip(keyf(o), keyf(r))) for o in g)]
    out["tradeoff"] = sorted(front, key=lambda r: -r["score"])
    return out


def select_half(mixes: list, h: str) -> dict:
    """The split check (PLAN_RA's note, report-only): PLAN_RA's rule with one half's cells only."""
    if h == "A3":
        q = [r for r in mixes if r["xr_A_A3"] >= 25.0 and r["xr_ABtrk_A3"] >= 25.0 and r["Z_A3"] >= 32.0 and r["D_A3"] >= 31.0]
        tie = lambda r: (-r["core_mean"], -r["score_A3"], r["base_order"], wdist(r))
        pool = mixes
    else:
        q = [r for r in mixes if r["guard_B2"] and r["Z_B2"] >= 32.0 and r["D_B2"] >= 31.0]
        tie = lambda r: (-r["score_B2"], r["base_order"], wdist(r))
        pool = [r for r in mixes if r["guard_B2"]]
    if q:
        top = max(r[f"score_{h}"] for r in q)
        tied = [r for r in q if r[f"score_{h}"] >= top - 0.25 - 1e-9]
        return {"pick": sorted(tied, key=tie)[0], "n_qualifiers": len(q), "how": "qualifier"}
    how = f"no qualifier on the {h} half: its highest (Z + D) / 2"
    if not pool:
        pool, how = mixes, how + " (no mix holds the B2 guard: among all mixes)"
    top = max(r[f"score_{h}"] for r in pool)
    best = sorted([r for r in pool if r[f"score_{h}"] == top], key=tie)[0]
    return {"pick": best, "n_qualifiers": 0, "how": how}


def name_of(r: dict) -> str:
    return (f"{r['base']} | w_A {r['w_A']}, w_B {r['w_B']}, w_unseen {r['w_unseen']}, w_id {r['w_id']}")


# ------------------------------------------------------------------ R3: the pick's figures and the extra cells

def store_for(r: dict) -> dict:
    seen = {m: rooms_of(model) for m, (model, _s) in CO.MODELS.items()}
    wfun = lambda m, s: ((r["w_unseen"] if s[0] not in seen[m] else (r["w_A"] if s[0] == "A" else r["w_B"])), r["w_id"])
    return store_of(load_comps(r["base"]), wfun)


def summary() -> dict:
    """The pick's (or, without one, the winner's) store saved in `ilc_outer`'s format beside v4 and the winner, for the
    report."""
    res = json.load(open(os.path.join(RD, "mixes.json")))
    win = next(r for r in res["mixes"] if r["base"] == WINNER and r["w_A"] == r["w_B"] == r["w_unseen"] == r["w_id"] == 1.0)
    os.makedirs(os.path.join(RD, "stores"), exist_ok=True)
    CO.OUTD = os.path.join(RD, "stores")
    CO.save("winner", store_for(win), [])
    if res.get("pick"):
        CO.save("pick", store_for(res["pick"]), [])
    for h, sp in res["split"].items():
        CO.save(f"split_{h}", store_for(sp["pick"]), [])
    out = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "winner": win, "pick": res.get("pick"),
           "n_qualifiers": res["n_qualifiers"], "split": res["split"]}
    json.dump(out, open(os.path.join(RD, "summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1), flush=True)
    return out


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "components":
        components(sys.argv[sys.argv.index("--base") + 1])
    elif what == "exact":
        sys.exit(0 if exact() else 1)
    elif what == "mix":
        mix()
    elif what == "summary":
        summary()
    sys.exit(0)
