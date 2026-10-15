"""ixa_a4. The extras brief's candidate A4 (`runs/identify/engine/PLAN.md`, the extras note): the lean correction learned
from the training days only. For each outer fold, m_c = the mean ensemble probability of person c over every inner
held-out window (identification and tracking walks) of that fold's inner loop (`ixa_inner`), divided by 1/6. The
vector is written before the test day's outputs are corrected: log p' = log p - log m, renormalised.

    PYTHONPATH=. python3 -m pipeline.identify.ixa_a4 walks      # conditions 1 and 2 on the two walks folds
    PYTHONPATH=. python3 -m pipeline.identify.ixa_a4 tracking   # condition 3, all five folds (only if 1 and 2 held)

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import ixa_inner as I
from pipeline.identify import ixa_run as R
from pipeline.identify import ixa_score as S

OUT = os.path.join("runs", "identify", "final_extras", "a4")
CL = S.CL


def inner_ensembles(outer: str, D: "R.Data", cfg: dict) -> list:
    """Every inner held-out session's ensembles for an outer fold, under the current best configuration cfg.
    With C0 (nothing adopted) these are the inner replays themselves; otherwise the inner feature components are
    retrained and re-scored under cfg (the CNN outputs are the inner replays')."""
    out = []
    a, G = D.B["a"], D.B["G"]
    for name, held in I.inner_plan(outer):
        z = np.load(os.path.join(I.OUT, "replays", f"inner_{name}_{held}.npz"))
        rep = {k: z[k] for k in z.files}
        assert rep["features_equal_bank"].all()
        if any(cfg.values()):
            tr = np.flatnonzero(np.isin(a["session"], I.sessions_of(name)))
            days = tuple(d for d in ("B1", "B2") if d in I.sessions_of(name))
            E = D.emp_days(days)
            pace, extra = D.inputs_E(cfg, E)
            off = D.offsets(cfg, E, tr) if cfg["A3"] else None
            feat = S.rescore(S.train_feat(G, extra, pace, a, tr, off), G, extra, pace, rep)
            rep["ensemble"] = S.ensemble(feat, rep)
        out.append(rep)
    return out


def bias_vector(inner: list) -> np.ndarray:
    P = np.concatenate([np.exp(r["ensemble"]) for r in inner])
    return P.mean(axis=0) / (1.0 / 6.0)


def correct(ens: np.ndarray, m: np.ndarray) -> np.ndarray:
    return C.normalise_logp(ens - np.log(m)[None, :])


def run(scope: str) -> dict:
    st = R.state()
    cfg = st["best"]
    D = R.Data()
    a = D.B["a"]
    outers = ("B2", "B1") if scope == "walks" else R.SESS
    best_ens = R.c0_outputs(D) if not any(cfg.values()) else D.score(cfg)
    res = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "scope": scope, "config_before": cfg, "folds": {}}
    cand = {s: dict(v) for s, v in best_ens.items()}
    os.makedirs(OUT, exist_ok=True)
    for s in outers:
        m = bias_vector(inner_ensembles(s, D, cfg))
        p = os.path.join(OUT, f"bias_{s}.json")
        if not os.path.exists(p):                      # written before the test day's outputs are corrected
            json.dump({"outer_fold": s, "m": m.tolist(), "classes": list(CL), "config": cfg,
                       "made_from": [f"inner_{n} -> {h}" for n, h in I.inner_plan(s)], "time": time.strftime("%Y-%m-%dT%H:%M:%S")},
                      open(p, "w"), indent=1)
        m = np.array(json.load(open(p))["m"])
        before = best_ens[s]["ensemble"]
        after = correct(before, m)
        cand[s]["ensemble"] = after
        te = best_ens[s]["te"]
        who = a["anon"][te]
        pb, pa = before.argmax(1), after.argmax(1)
        changed = pb != pa
        runner = np.argsort(-before, axis=1)[:, 1]
        test_share = np.array([np.mean(pb == k) for k in range(6)])
        from scipy.stats import spearmanr
        res["folds"][s] = {"m": dict(zip(CL, np.round(m, 4))), "most_over_named_training": CL[int(np.argmax(m))],
                           "most_named_test_uncorrected": CL[int(np.argmax(test_share))],
                           "lean_matches": bool(np.argmax(m) == np.argmax(test_share)),
                           "spearman_m_vs_test_share": round(float(spearmanr(m, test_share)[0]), 3),
                           "share_before": dict(zip(CL, np.round(100 * test_share, 1))),
                           "share_after": dict(zip(CL, np.round(100 * np.array([np.mean(pa == k) for k in range(6)]), 1))),
                           "truth_share": dict(zip(CL, np.round(100 * np.array([np.mean(who == c) for c in CL]), 1))),
                           "decisions_changed": int(changed.sum()), "n": int(len(te)),
                           "changed_to_runner_up_frac": round(float(np.mean(pa[changed] == runner[changed])), 3) if changed.any() else None}
    if scope == "walks":
        # conditions 1 and 2 on the walks folds; the tracking passes keep the current best's outputs here
        bc, cc = S.collect(best_ens, a), S.collect(cand, a)
        rl = S.rule(cc, bc)
        res.update({"best_table": S.table(bc), "candidate_table": S.table(cc), **{k: rl[k] for k in (
            "paired_natural", "paired_by_block", "slow_change", "fast_change", "condition_1", "condition_2")}})
        res["PROCEED_TO_TRACKING"] = bool(rl["condition_1"] and rl["condition_2"])
    else:
        bc, cc = S.collect(best_ens, a), S.collect(cand, a)
        rl = S.rule(cc, bc)
        res.update({"best_table": S.table(bc), "candidate_table": S.table(cc), **rl})
        if rl["ADOPT"]:
            st["best"] = {**cfg, "A4": True}
    st["history"].append({"item": f"A4 ({scope})", **{k: v for k, v in res.items() if k != "folds"}})
    R.save(st)
    json.dump(res, open(os.path.join(OUT, f"a4_{scope}.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("best_table", "candidate_table", "paired_by_block")}, indent=1, default=str), flush=True)
    return res


if __name__ == "__main__":
    run(sys.argv[1])
    sys.exit(0)
