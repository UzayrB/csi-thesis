"""idx_all_eval. Identification development (the operator's direction of 2026-09-28): selection rules and
ensembles compared on the saved component log-probabilities of `idx_all`, without retraining.

Every rule chooses from the INNER leave-one-session-out predictions of the four training sessions only
(their tracking passes); the held-out session is scored once per rule. Rules:
- `pooled`: the candidate (component or pairwise fusion, as `idx_sel`) with the best pooled inner accuracy.
  This is `idx_sel`'s rule.
- `balanced`: the same candidates, ranked by the mean of the two rooms' inner accuracies. A Room B fold's
  training has three Room A sessions and one Room B session, so the pooled rule mostly measures Room A.
- `greedy_pooled`, `greedy_balanced`: greedy forward ensemble selection (equal-weight product of the chosen
  components; add the component that most improves the inner criterion; stop when none improves).
- `all`: the equal-weight product of every component. No choice at all.
Per-component test figures are reported beside them as references, never used to choose.

    PYTHONPATH=. python3 -m pipeline.identify.idx_all_eval [--tag all]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_all as A
from pipeline.identify import idx_loso as L

CLASSES = L.CLASSES


def _acc(lp, y, m) -> float:
    return float(np.mean(lp[m].argmax(1) == y[m])) if m.any() else float("nan")


def criterion(lp, y, trk, rooms, how) -> float:
    if how == "pooled":
        return _acc(lp, y, trk)
    return float(np.mean([_acc(lp, y, trk & (rooms == r)) for r in np.unique(rooms)]))


def candidates(parts: dict) -> dict:
    """Every component and every pairwise equal-weight fusion of a feature head with a CNN."""
    out = dict(parts)
    feats = [k for k in parts if not k.startswith("cnn")]
    cnns = [k for k in parts if k.startswith("cnn")]
    for f, c in itertools.product(feats, cnns):
        out[f"{f}+{c}"] = C.normalise_logp(parts[f] + parts[c])
    return out


def greedy(oof: dict, y, trk, rooms, how) -> list:
    chosen, best = [], -1.0
    while True:
        trial = {k: criterion(C.normalise_logp(sum(oof[c] for c in chosen + [k])), y, trk, rooms, how)
                 for k in oof if k not in chosen}
        if not trial:
            return chosen
        k = max(trial, key=trial.get)
        if trial[k] <= best:
            return chosen
        chosen.append(k)
        best = trial[k]


def run(tag="all") -> dict:
    bank = L.load()
    a = bank["a"]
    y_all = np.array([CLASSES.index(v) for v in a["anon"]])
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "tag": tag, "folds": {}}
    preds = {}
    for s in L.SESSIONS:
        path = os.path.join(A.OUT, f"{tag}_{s}.npz")
        if not os.path.exists(path):
            continue
        z = np.load(path)
        tr, te = z["tr"], z["te"]
        oof = {k[5:]: z[k] for k in z.files if k.startswith("oof__")}
        test = {k[6:]: z[k] for k in z.files if k.startswith("test__")}
        ytr, trk, rooms = y_all[tr], a["kind"][tr] == "track", np.array([v[0] for v in a["session"][tr]])
        m = a["kind"][te] == "track"
        oof_c, test_c = candidates(oof), candidates(test)
        fold = {"rules": {}, "components_test": {}}
        rule_lp = {}
        for how in ("pooled", "balanced"):
            inner = {k: criterion(v, ytr, trk, rooms, how) for k, v in oof_c.items()}
            k = max(inner, key=inner.get)
            rule_lp[how] = (k, test_c[k])
            g = greedy(oof, ytr, trk, rooms, how)
            rule_lp[f"greedy_{how}"] = ("*".join(g), C.normalise_logp(sum(test[c] for c in g)))
        rule_lp["all"] = ("*".join(sorted(test)), C.normalise_logp(sum(test.values())))
        for r, (choice, lp) in rule_lp.items():
            st = L.score(bank, te[m], lp[m], f"allx|{s}|{r}")
            fold["rules"][r] = {"choice": choice, "acc_pct": st["acc_pct"], "ci95_pct": st["ci95_pct"]}
            preds.setdefault(r, {})[s] = (te[m], np.array(CLASSES)[lp[m].argmax(1)])
        for k, v in test.items():
            fold["components_test"][k] = round(100 * _acc(v, y_all[te], m), 2)
        doc["folds"][s] = fold
        print(s, {r: (v["choice"], v["acc_pct"]) for r, v in fold["rules"].items()}, flush=True)
    from pipeline.identify import id29_dc2_score as D
    doc["rooms"] = {}
    for r, per in preds.items():
        for room in ("A", "B"):
            ss = [s for s in per if s[0] == room]
            if not ss:
                continue
            te = np.concatenate([per[s][0] for s in ss])
            pr = np.concatenate([per[s][1] for s in ss])
            st = D.id_stats([{"tag": f"allx|{room}|{r}", "te": list(map(int, te)), "pred": pr.tolist(),
                              "truth": a["anon"][te].tolist()}], {"anon": a["anon"]}, D.Config())
            doc["rooms"].setdefault(r, {})[room] = {"acc_pct": st["acc_pct"], "ci95_pct": st["ci95_pct"], "sessions": ss}
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(A.OUT, f"eval_{tag}.json"), "w").write(txt)
    for r, v in doc["rooms"].items():
        print(r, {room: (x["acc_pct"], x["ci95_pct"]) for room, x in v.items()})
    return doc


def export_ensemble(tag="all") -> str:
    """The `all` ensemble's decisions on every pass of each held-out session, in `idx_sel`'s format, so
    `idx_live --selection sel_all_ens` can replay it and compare its live decisions with these."""
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": f"idx_all {tag}, rule all", "folds": {}, "preds": {}}
    for s in L.SESSIONS:
        z = np.load(os.path.join(A.OUT, f"{tag}_{s}.npz"))
        lp = C.normalise_logp(sum(z[k] for k in z.files if k.startswith("test__")))
        doc["folds"][s] = {"choice": "all"}
        doc["preds"][s] = {"te": z["te"].tolist(), "pred": np.array(CLASSES)[lp.argmax(1)].tolist()}
    txt = json.dumps(doc, indent=1)
    assert IC.no_names(txt)
    path = os.path.join(L.OUT, "sel_all_ens.json")
    open(path, "w").write(txt)
    return path


def paired_rules(tag="all", base="pooled") -> dict:
    """Each rule minus `base` on the same tracking passes, per room, bootstrap over participants."""
    from pipeline.identify.idgp_dc2_score import paired
    bank = L.load()
    a = bank["a"]
    rows = {}
    for s in L.SESSIONS:
        z = np.load(os.path.join(A.OUT, f"{tag}_{s}.npz"))
        te = z["te"]
        m = a["kind"][te] == "track"
        tr = z["tr"]
        oof = {k[5:]: z[k] for k in z.files if k.startswith("oof__")}
        test = {k[6:]: z[k] for k in z.files if k.startswith("test__")}
        y_all = np.array([CLASSES.index(v) for v in a["anon"]])
        ytr, trk = y_all[tr], a["kind"][tr] == "track"
        rooms = np.array([v[0] for v in a["session"][tr]])
        oof_c, test_c = candidates(oof), candidates(test)
        lps = {"all": C.normalise_logp(sum(test.values()))}
        for how in ("pooled", "balanced"):
            inner = {k: criterion(v, ytr, trk, rooms, how) for k, v in oof_c.items()}
            lps[how] = test_c[max(inner, key=inner.get)]
        for r, lp in lps.items():
            rows.setdefault(r, {})[s] = (te[m], np.array(CLASSES)[lp[m].argmax(1)])
    out = {}
    for r in rows:
        if r == base:
            continue
        for room in ("A", "B"):
            ss = [s for s in L.SESSIONS if s[0] == room]
            te = np.concatenate([rows[r][s][0] for s in ss]).tolist()
            ra = {"te": te, "pred": np.concatenate([rows[r][s][1] for s in ss]).tolist(), "truth": a["anon"][te].tolist()}
            rb = {"te": te, "pred": np.concatenate([rows[base][s][1] for s in ss]).tolist(), "truth": a["anon"][te].tolist()}
            out[f"{r}-{base}|{room}"] = paired(ra, rb, {"anon": a["anon"]}, 2000)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tag", default="all")
    ap.add_argument("--export", action="store_true", help="write sel_all_ens.json and the paired comparisons")
    a = ap.parse_args(argv)
    if a.export:
        print(export_ensemble(a.tag))
        print(json.dumps(paired_rules(a.tag), indent=1))
        return 0
    run(a.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
