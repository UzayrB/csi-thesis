"""ixt_v2. Engine v2 (the cadence bug fix, `runs/identify/engine/PLAN.md` note of 2026-10-01): the one figure of the
engine's final report that had no saved script, the one-press cost on the 600 tracking passes (information only),
recomputed from the replays: the engine (`loso_<s>[_x]` replays) minus the two-press B1 configuration (CAL-causal,
`final_loso_<s>_causal.npz`, never retrained), paired, pooled and by room, with and without the pace components.
The engine bank and the audit bank share row order, so rows are matched by index (as `ide_eval.two_press`).
`--v1` reproduces `one_press_cost_tracking_information.json` (the anchor). Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_v2 [--v1]
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
from pipeline.identify import idx_loso as L

CL = np.array(L.CLASSES)
SESS = ("A1", "A2", "A3", "B1", "B2")
AUD = os.path.join("runs", "identify", "audit", "outputs")
PACE = ("rf_pace_prior", "et_pace_prior", "lda_pace_prior")


def tracking_cost(suffix: str) -> dict:
    from pipeline.identify import idz_core as Z
    TW = EN.T_S if suffix == EN.SUFFIX else 3.0
    bank = EN.bank_dir(TW) if suffix else os.path.join(EN.ENG, "bank_T3.0")
    meta = json.load(open(os.path.join(bank, "meta.json")))["passes"]
    e_ok, e_np_ok, t_ok, t_np_ok, who, room = [], [], [], [], [], []
    for s in SESS:
        z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}{suffix}_{s}_T{TW:.1f}.npz"))
        b = np.load(os.path.join(AUD, f"final_loso_{s}_causal.npz"))
        pos = {int(r): j for j, r in enumerate(b["te"])}
        k = np.array([meta[int(i)]["kind"] == "track" for i in z["te"]])
        te = z["te"][k]
        j = [pos[int(r)] for r in te]
        comp = {c: b[c][j] for c in Z.COMPONENTS}
        y = np.array([meta[int(i)]["anon"] for i in te])
        e_ok.append(CL[z["ensemble"][k].argmax(1)] == y)
        e_np_ok.append(CL[z["ensemble_nopace"][k].argmax(1)] == y)
        t_ok.append(CL[Z.fuse(comp, "F0").argmax(1)] == y)
        t_np_ok.append(CL[Z.fuse(comp, "F0", keep=[c for c in Z.COMPONENTS if c not in PACE]).argmax(1)] == y)
        who.append(y)
        room.append(np.array([meta[int(i)]["room"] for i in te]))
    e_ok, e_np_ok, t_ok, t_np_ok = (np.concatenate(v).astype(float) for v in (e_ok, e_np_ok, t_ok, t_np_ok))
    who, room = np.concatenate(who), np.concatenate(room)

    def cost(a, b, m):
        return EV.paired(a[m], b[m], who[m]) | {"engine": round(100 * float(a[m].mean()), 2), "two_press": round(100 * float(b[m].mean()), 2)}
    allm = np.ones(len(who), bool)
    return {"label": "development evaluation, all data seen; information only (not in the PLAN's decisions)",
            "what": "one-press engine minus the two-press B1 (CAL-causal, final_loso) on the 600 tracking passes, paired",
            "engine_version": EN.ENGINE_VERSION if suffix else 1, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "engine_replays": [f"loso_{s}{suffix}_{s}_T{TW:.1f}.npz" for s in SESS],
            "two_press_outputs": [os.path.join(AUD, f"final_loso_{s}_causal.npz") for s in SESS],
            "train_sessions": "the other four sessions per fold", "test_session": "all five", "calibration": "causal",
            "pooled": cost(e_ok, t_ok, allm), "room_A": cost(e_ok, t_ok, room == "A"), "room_B": cost(e_ok, t_ok, room == "B"),
            "room_A_without_pace": cost(e_np_ok, t_np_ok, room == "A"), "room_B_without_pace": cost(e_np_ok, t_np_ok, room == "B"),
            "n": int(len(who))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--v1", action="store_true")
    a = ap.parse_args(argv)
    suffix = "" if a.v1 else EN.SUFFIX
    res = tracking_cost(suffix)
    p = os.path.join(EN.ENG, "eval", "one_press_cost_tracking_information.json")
    if a.v1:                                                        # the anchor: the saved v1 figures, reproduced
        old = json.load(open(p))
        for k in ("pooled", "room_A", "room_B", "room_A_without_pace", "room_B_without_pace"):
            assert old[k]["pct"] == res[k]["pct"] and old[k]["ci95"] == res[k]["ci95"], (k, old[k], res[k])
        print("anchor: v1 reproduced exactly", flush=True)
    else:
        json.dump(res, open(p.replace(".json", f"{suffix}.json"), "w"), indent=1)
    print(json.dumps({k: (res[k]["pct"], res[k]["ci95"], res[k]["engine"], res[k]["two_press"]) for k in
                      ("pooled", "room_A", "room_B", "room_A_without_pace", "room_B_without_pace")}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
