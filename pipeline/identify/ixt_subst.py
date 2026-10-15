"""ixt_subst. The teaching-pack brief's substitution test (`runs/identify/engine/PLAN.md`, the teaching note, C1): each B2
natural walk (host) is given another person's radio (donor) in its own slot; the engine's answer should follow the
radio. Uses the engine's own `Session` (`loso_B2`). Names, not codes. Development evaluation, all data seen.
From 1 Oct: engine v2 (`loso_B2_x`, the v2 bank and replay; the cadence bug fix), output `substitution_x.json`.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_subst [--device mps]
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idw_eval as EV
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "teaching")
CODES = ("P1", "P2", "P3", "P4", "P5", "P6")
NAME = {anon(n): n for n in SIX}
M = EN.model_name("loso_B2")
SUF = EN.SUFFIX


def load():
    b = EN.bank_dir(EN.T_S)
    meta = json.load(open(os.path.join(b, "meta.json")))["passes"]
    z = np.load(os.path.join(EN.ENG, "replays", f"{M}_B2_T{EN.T_S:.1f}.npz"))
    return meta, np.load(os.path.join(b, "features.npy")), pickle.load(open(os.path.join(b, "maps.pkl"), "rb")), z


def plan(meta, z) -> list:
    """(host k, donor k) by the PLAN's rule: the next natural walk in session order by a different person, same
    recorded direction; wrap to the session start if none follows."""
    te = z["te"]
    nat = [k for k, i in enumerate(te) if meta[int(i)]["kind"] == "idcap" and meta[int(i)]["block"] == "natural"]
    out = []
    for h in nat:
        mh = meta[int(te[h])]
        cand = [k for k in nat if meta[int(te[k])]["anon"] != mh["anon"] and meta[int(te[k])]["path"] == mh["path"]]
        after = [k for k in cand if k > h]
        out.append((h, (after or cand)[0]))
    return out


def rec_rows(meta, z, k) -> list:
    """Replay positions of the recording holding position k (same person, kind and block), in replay order."""
    te = z["te"]
    m = meta[int(te[k])]
    return [j for j, i in enumerate(te) if meta[int(i)]["anon"] == m["anon"] and meta[int(i)]["kind"] == m["kind"]
            and meta[int(i)]["block"] == m["block"]]


def run(device: str = "mps") -> dict:
    t_all = time.time()
    meta, X, maps, z = load()
    te, paths = z["te"], z["path_used"]

    def ex(k):
        i = int(te[k])
        return {"features": X[i], "maps": maps[i], "wifi_speed": meta[i]["wifi_speed"], "path": str(paths[k]),
                "layout": "id_spot" if meta[i]["kind"] == "idcap" else "home"}      # engine v3's fix L: pools per layout

    model = EN.Model(os.path.join(EN.ENG, "models", M), device)
    pairs = plan(meta, z)
    rows = []
    for h, d in pairs:
        own = CODES[int(z["ensemble"][d].argmax())]
        hrec = rec_rows(meta, z, h)
        drec = rec_rows(meta, z, d)
        before = [j for j in hrec if j < h]
        pool_a = list(range(h))
        pool_b = [j for j in pool_a if j not in set(before)] + drec[:len(before)]
        out = {"host_k": h, "donor_k": d, "host": NAME[meta[int(te[h])]["anon"]], "donor": NAME[meta[int(te[d])]["anon"]],
               "direction": meta[int(te[h])]["path"], "donor_own_decision": NAME[own],
               "host_own_decision": NAME[CODES[int(z["ensemble"][h].argmax())]], "j_replaced": len(before)}
        for tag, pool in (("A", pool_a), ("B", pool_b)):
            s = EN.Session(model)
            s.set_pool([ex(j) for j in pool])
            r = s.classify(ex(d))
            out[f"{tag}_decision"] = NAME[CODES[int(np.argmax(r["ensemble"]))]]
            out[f"{tag}_confidence"] = float(np.max(r["confidence"]))
        rows.append(out)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": M, "engine_version": EN.ENGINE_VERSION, "train_sessions": ["A1", "A2", "A3", "B1"],
           "test_session": "B2", "scored_set": "B2 natural identification walks (hosts), 60", "pairs": rows}
    host = np.array([r["host"] for r in rows])
    donor = np.array([r["donor"] for r in rows])
    for tag in ("A", "B"):
        dec = np.array([r[f"{tag}_decision"] for r in rows])
        own = np.array([r["donor_own_decision"] for r in rows])
        res[f"variant_{tag}"] = {
            "equals_donor_own_decision": EV._boot((dec == own).astype(float), donor),
            "accuracy_vs_donor_identity": EV._boot((dec == donor).astype(float), donor),
            "accuracy_vs_host_identity": EV._boot((dec == host).astype(float), host)}
    res["reference"] = {"donor_own_accuracy": EV._boot((np.array([r["donor_own_decision"] for r in rows]) == donor).astype(float), donor),
                        "host_own_accuracy": EV._boot((np.array([r["host_own_decision"] for r in rows]) == host).astype(float), host)}
    res["seconds"] = round(time.time() - t_all, 1)
    json.dump(res, open(os.path.join(OUT, f"substitution{SUF}.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "pairs"}, indent=1, default=str), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    run(ap.parse_args().device)
    sys.exit(0)
