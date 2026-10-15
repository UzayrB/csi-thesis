"""ixt_cadimpact. Information for Uzayr's decision on the cadence bug (`ixt_cadfix`): what the candidate fix would do to the
engine's figures, measured WITHOUT changing the engine. The fix changes only the gait features (the maps and the CNN
outputs are unchanged), so the figures follow exactly from the A-stage feature re-scoring (`ixa_score`, anchored to the
replays at 5e-14): every window's features recomputed by the engine's own extraction with the patched resolver
(installed only in this process), the five feature components retrained per fold, re-scored in replay order, and the
replays' CNN outputs added. Nothing is adopted. Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_cadimpact
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idmax_features as F
from pipeline.identify import ixt_cadfix as CF

OUT = os.path.join("runs", "identify", "teaching", "cadence_fix")


def fixed_features() -> np.ndarray:
    from pipeline.identify import idx_bank as B
    from pipeline.identify import ixa_data as XD
    from pipeline.io.capture_logger import read_capture_file
    p = os.path.join(OUT, "features_fixed.npy")
    if os.path.exists(p):
        return np.load(p)
    meta = json.load(open(os.path.join(EN.ENG, "bank_T3.0", "meta.json")))["passes"]
    names = json.load(open(EN.DEV_NAMES))
    F.resolve_cadence = CF.resolve_fixed
    feats, k = [], 0
    t = time.time()
    for rec in B.recordings():
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        ex = XD.Tap(T=3.0, layout="id_spot" if rec["kind"] == "idcap" else "home", names=names)
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + 3.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            ex.press(t0, path=meta[k]["engine_path"], info={"features": True})
            (_w, td, _A, x), = ex.poll(lim)
            assert abs(td - meta[k]["t_dec"]) < 1e-9
            feats.append(x["features"])
            k += 1
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k}, {time.time() - t:.0f} s", flush=True)
    F.resolve_cadence = CF.ORIGINAL
    X = np.asarray(feats, np.float32)
    os.makedirs(OUT, exist_ok=True)
    np.save(p, X)
    return X


def main() -> int:
    from pipeline.identify import ixa_score as S
    from pipeline.identify import ixa_run as R
    t = time.time()
    Xf = fixed_features().astype(np.float64)
    B = S.base()
    a = B["a"]
    Gf = Xf[:, EN.v2_columns(B["names"])]
    pace = a["wifi_speed"].astype(float)
    ens = {}
    for s in S.SESS:
        tr = np.flatnonzero(a["session"] != s)
        feat = S.rescore(S.train_feat(Gf, None, pace, a, tr), Gf, None, pace, B["rep"][s])
        ens[s] = {"te": B["rep"][s]["te"], "ensemble": S.ensemble(feat, B["rep"][s])}
    D = R.Data()
    base = S.collect(R.c0_outputs(D), a)
    cand = S.collect(ens, a)
    rule = S.rule(cand, base)
    loso = {}
    for room in ("A", "B"):
        m = np.array([a["room"][i] == room for i in cand["track"]["te"]])
        from pipeline.identify import idw_eval as EV
        loso[f"room_{room}_engine"] = EV._boot(base["track"]["ok"][m], base["track"]["who"][m])
        loso[f"room_{room}_with_fix"] = EV._boot(cand["track"]["ok"][m], cand["track"]["who"][m])
        loso[f"room_{room}_paired"] = EV.paired(cand["track"]["ok"][m], base["track"]["ok"][m], base["track"]["who"][m])
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "information_only": True, "engine_unchanged": True,
           "what": "the engine with the candidate cadence fix (gait features recomputed; CNN outputs unchanged), by feature re-scoring",
           "engine_table": S.table(base), "with_fix_table": S.table(cand),
           "paired_natural": rule["paired_natural"], "paired_by_block": rule["paired_by_block"],
           "tracking_pooled_change": rule["tracking_pooled_change"], "loso_by_room": loso,
           "features_changed_windows": int(np.sum(np.any(~np.isclose(Gf, B["G"], rtol=1e-9, atol=1e-12, equal_nan=True), axis=1))),
           "seconds": round(time.time() - t, 1)}
    json.dump(res, open(os.path.join(OUT, "impact.json"), "w"), indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("paired_natural", "tracking_pooled_change", "features_changed_windows")}, indent=1, default=str))
    print(json.dumps({b: (res["engine_table"][b]["pct"], res["with_fix_table"][b]["pct"]) for b in ("natural_both", "slow", "fast", "loso_tracking_pooled")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
