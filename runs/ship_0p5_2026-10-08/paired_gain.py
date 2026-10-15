"""The value of one day of Room B data: main model minus zero-shot model on B2, paired by walk, from the FC decode rows
(which the live-app gates reproduce exactly). Bootstrap over walks, 1,000 draws, seed 0, as the 29 Sep figure.
Checked first on the old cells (fin_B2, zsf_B2) against the recorded +13.33 [7.48, 20.00] / +23.33 [15.83, 31.67]."""
import json, os, sys
import numpy as np
J = os.path.join
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = "FC.relgateU+abstain+a2w0.25"

def rows(cell):
    d3 = J(REPO, "runs", "dc2_results", "cells", cell, "d3", V)
    dec = json.load(open(J(d3, "decode.json")))["sessions"]["B2"]["rows"]["A"]
    sl = {r["key"]: r for r in json.load(open(J(d3, "scorerlock.json")))["sessions"]["B2"]["rows"]["A"]}
    return {r["key"]: (float(r["correct"]), float(sl[r["key"]]["display_lock"] == r["true"])) for r in dec}

def gain(main, zs, draws=1000, seed=0):
    a, b = rows(main), rows(zs)
    keys = sorted(a)
    assert keys == sorted(b)
    out = {}
    for i, name in enumerate(("committed", "lock")):
        d = np.array([a[k][i] - b[k][i] for k in keys]) * 100
        rng = np.random.default_rng(seed)
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]
        out[name] = [round(float(d.mean()), 2), round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]
    return out

if __name__ == "__main__":
    print("old (fin_B2 - zsf_B2):", gain("fin_B2", "zsf_B2"))
    print("new (f05_B2 - z05_B2):", gain("f05_B2", "z05_B2"))
