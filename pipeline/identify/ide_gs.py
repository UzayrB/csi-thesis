"""ide_gs. The engine brief's stage 1 (`runs/identify/engine/PLAN.md`, section 1): the GS confirmation on the
600 tracking passes, leave one session out, CAL-causal, run once.

B1+GS is the audit's item 17 configuration (bank `runs/identify/audit/bank_gs`, columns v2, fusion F0),
trained and applied by the audit's own code (`idz_core.train`, `idz_core.apply`), exactly as the audit's
`idz_run.stage_final` loop runs B1. The baseline is B1's saved `final_loso_*_causal.npz`, never retrained.
The B1 and B2 folds reuse the audit's `GS_toB1` and `GS_toB2` models, whose training rows equal the
leave-one-session-out rows (asserted here).

    PYTHONPATH=. python3 -m pipeline.identify.ide_gs run
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L
from pipeline.identify import idz_core as Z
from pipeline.identify import idz_run as ZR

AUD = os.path.join("runs", "identify", "audit")
ENG = os.path.join("runs", "identify", "engine")
OUT = os.path.join(ENG, "stage1")
CFG = {"bank": os.path.join(AUD, "bank_gs"), "cols": "v2", "layout": False, "fn": False, "amp_norm": True}
CL = np.array(L.CLASSES)
LABEL = "development evaluation, all data seen"
log = lambda s: print(s, flush=True)  # noqa: E731


def model_dir(sname: str) -> str:
    if sname in ("B1", "B2"):
        return os.path.join(AUD, "models", f"GS_to{sname}")
    return os.path.join(ENG, "models", f"gs_loso_{sname}")


def outputs(sname: str) -> str:
    return os.path.join(OUT, f"gs_loso_{sname}_causal.npz")


def run_folds() -> None:
    bank = ZR.bank_of(CFG["bank"])
    a = bank["a"]
    os.makedirs(OUT, exist_ok=True)
    for sname in L.SESSIONS:
        tr = np.flatnonzero(a["session"] != sname)
        md = model_dir(sname)
        if sname in ("B1", "B2"):
            assert np.array_equal(np.load(os.path.join(md, "train_rows.npy")), tr), sname
            assert json.load(open(os.path.join(md, "meta_feat_cnn.json")))["cfg"] == CFG, sname
        elif not os.path.exists(os.path.join(md, "meta_feat_cnn.json")):
            dev = ZR.device()
            log(f"{time.strftime('%H:%M:%S')} GS LOSO training {sname} on {dev}")
            Z.train(bank, tr, md, CFG, device=dev, log=log)
        if os.path.exists(outputs(sname)):
            continue
        te_all = np.flatnonzero(a["session"] == sname)
        comp = Z.apply(bank, md, md, te_all, Z.calibration_groups(a, te_all, "causal"), CFG, device=ZR.device())
        k = a["kind"][te_all] == "track"
        comp = {c: v[k] for c, v in comp.items()}
        np.savez(outputs(sname), te=te_all[k], **comp)
        acc = np.mean(CL[Z.fuse(comp, "F0").argmax(1)] == a["anon"][te_all[k]])
        log(f"{time.strftime('%H:%M:%S')} GS LOSO {sname}: {100 * acc:.2f}")


def evaluate() -> dict:
    a = ZR.bank_of(CFG["bank"])["a"]
    te, cb, cg = [], [], []
    for sname in L.SESSIONS:
        zb = np.load(os.path.join(AUD, "outputs", f"final_loso_{sname}_causal.npz"))
        zg = np.load(outputs(sname))
        assert np.array_equal(zb["te"], zg["te"]), sname
        who = a["anon"][zb["te"]]
        cb.append((CL[Z.fuse({c: zb[c] for c in Z.COMPONENTS}, "F0").argmax(1)] == who).astype(float))
        cg.append((CL[Z.fuse({c: zg[c] for c in Z.COMPONENTS}, "F0").argmax(1)] == who).astype(float))
        te.append(zb["te"])
    te, cb, cg = np.concatenate(te), np.concatenate(cb), np.concatenate(cg)
    assert len(te) == 600 and np.all(a["kind"][te] == "track")
    who, ses, room = a["anon"][te], a["session"][te], a["room"][te]
    pooled = EV.paired(cg, cb, who)
    rooms = {r: {"B1": round(100 * float(cb[room == r].mean()), 2), "B1_GS": round(100 * float(cg[room == r].mean()), 2),
                 "change": round(100 * float(cg[room == r].mean() - cb[room == r].mean()), 2),
                 "paired": EV.paired(cg[room == r], cb[room == r], who[room == r])} for r in ("A", "B")}
    cond1 = bool(pooled["ci95"][0] > 0)
    cond2 = bool(all(rooms[r]["change"] >= -3.0 for r in rooms))
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rule": "adopt only if (1) the pooled paired gain's 95 % interval over participants is entirely above 0 "
                   "and (2) neither room loses more than 3 points (point estimate)",
           "n": int(len(te)), "B1": EV._boot(cb, who), "B1_GS": EV._boot(cg, who), "paired_pooled": pooled,
           "rooms": rooms, "condition_1": cond1, "condition_2": cond2, "ADOPT": cond1 and cond2,
           "information": {
               "paired_by_participant_session_cluster": EV.paired(cg, cb, np.array([f"{w}|{s}" for w, s in zip(who, ses)])),
               "per_session": {s: {"B1": round(100 * float(cb[ses == s].mean()), 2), "B1_GS": round(100 * float(cg[ses == s].mean()), 2),
                                   "change": round(100 * float(cg[ses == s].mean() - cb[ses == s].mean()), 2)} for s in L.SESSIONS},
               "per_participant": {p: {"B1": round(100 * float(cb[who == p].mean()), 2), "B1_GS": round(100 * float(cg[who == p].mean()), 2),
                                       "change": round(100 * float(cg[who == p].mean() - cb[who == p].mean()), 2)} for p in L.CLASSES}},
           "models": {s: model_dir(s) for s in L.SESSIONS}}
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(OUT, "result.json"), "w").write(txt)
    log(json.dumps({k: res[k] for k in ("B1", "B1_GS", "paired_pooled", "condition_1", "condition_2", "ADOPT")}, default=str))
    log(json.dumps({r: {k: v for k, v in res["rooms"][r].items() if k != "paired"} for r in res["rooms"]}))
    return res


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run_folds()
        evaluate()
    elif sys.argv[1] == "evaluate":
        evaluate()
    sys.exit(0)
