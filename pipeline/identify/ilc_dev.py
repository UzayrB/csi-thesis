"""ilc_dev. The combine run's development stage (Uzayr's prompt of 10 Oct; `runs/identify/combine/`): the shortlist's
changes combined on last night's development folds (A1, A2, B1 only) with last night's scorer and DS (`ilp_cand`): all
10 pairs of F3, F7, NP, F4 and F5; the greedy path from the best single (add the change that raises DS most; stop when
none raises it); the full stack. The greedy result is the primary configuration. Writes runs/identify/combine/dev.json.

    PYTHONPATH=. python3 -m pipeline.identify.ilc_dev

Exploratory development, all data seen.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time

from pipeline.identify import ilp_cand as PC

CB = os.path.join("runs", "identify", "combine")
LABEL = "exploratory development, all data seen"
SHORT = {"F3": {"shrink_k": 160}, "F7": {"f7": True}, "NP": {"weights": {c: 0.0 for c in PC.PACE}},
         "F4": {"icc_k": 200}, "F5": {"drop_families": ["mod"]}}
SINGLE_NAMES = {"F3": "F3_shrink_k160", "F7": "F7_offset_augmentation", "NP": "H3_drop_pace", "F4": "F4_icc_top200",
                "F5": "F5a_drop_mod", "CNN": "H3_cnn_only"}
ORDER = ("F3", "F7", "NP", "F4", "F5")


def config(ids) -> dict:
    """The merged configuration of a set of shortlist changes (each changes a different thing; keys never collide)."""
    cfg = {}
    for i in ids:
        for k, v in SHORT[i].items():
            assert k not in cfg, (i, k)
            cfg[k] = v
    return cfg


def name(ids) -> str:
    return "+".join(i for i in ORDER if i in ids)


def score(ids, res: dict) -> dict:
    n = name(ids)
    if n in res["configs"]:
        return res["configs"][n]
    t0 = time.time()
    r = PC.ds_of(PC.run_config(config(ids)))
    v4 = res["configs"]["v4"]
    r["guard"] = bool(r["B1_slow"] >= v4["B1_slow"] - 5 and r["B1_fast"] >= v4["B1_fast"] - 5)
    r["minus_v4"] = round(r["DS"] - v4["DS"], 2)
    r["seconds"] = round(time.time() - t0, 1)
    res["configs"][n] = r
    print(f"{time.strftime('%H:%M:%S')} {n}: DS {r['DS']} ({r['minus_v4']:+.2f}), guard {r['guard']}", flush=True)
    json.dump(res, open(os.path.join(CB, "dev.json"), "w"), indent=1)
    return r


def run() -> dict:
    PC.load_folds()
    last = json.load(open(os.path.join(PC.OUT, "dev.json")))["configs"]
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rules": "DS and guard as last night (PREREG_LP sections 3 and 6); greedy from the best single, strictly higher DS",
           "configs": {"v4": PC.ds_of({f: fd["ensemble"] for f, fd in PC.FD.items()})}}
    assert res["configs"]["v4"]["DS"] == last["v4"]["DS"], "v4's DS differs from last night's"
    singles = {}
    for i in ORDER:                                              # the singles, recomputed: must equal last night's
        r = score([i], res)
        singles[i] = r["DS"]
        assert r["DS"] == last[SINGLE_NAMES[i]]["DS"], (i, r["DS"], last[SINGLE_NAMES[i]]["DS"])
    res["singles_equal_last_night"] = True
    for a, b in itertools.combinations(ORDER, 2):
        score([a, b], res)
    best = max(ORDER, key=lambda i: (singles[i], -ORDER.index(i)))
    path, cur = [best], singles[best]
    res["greedy"] = [{"step": 1, "added": best, "config": best, "DS": cur}]
    while True:
        rest = [i for i in ORDER if i not in path]
        if not rest:
            break
        trials = {i: score(path + [i], res)["DS"] for i in rest}
        top = max(rest, key=lambda i: (trials[i], -ORDER.index(i)))
        if trials[top] <= cur:
            res["greedy"].append({"step": len(path) + 1, "stopped": True, "best_addition": top, "DS": trials[top],
                                  "note": "no addition raises DS"})
            break
        path.append(top)
        cur = trials[top]
        res["greedy"].append({"step": len(path), "added": top, "config": name(path), "DS": cur})
    res["primary"] = name(path)
    res["stack"] = name(ORDER)
    score(list(ORDER), res)
    res["n_configurations_scored_today"] = len(res["configs"]) - 1
    json.dump(res, open(os.path.join(CB, "dev.json"), "w"), indent=1)
    print(f"primary (greedy): {res['primary']} DS {cur}; stack {res['stack']} DS {res['configs'][res['stack']]['DS']}", flush=True)
    return res


if __name__ == "__main__":
    run()
    sys.exit(0)
