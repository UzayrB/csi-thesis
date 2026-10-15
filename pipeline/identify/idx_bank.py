"""idx_bank. Identification development (the operator's direction of 2026-09-28): one pass bank over
the five sessions A1, A2, A3 (Room A sessions 01 to 03) and B1, B2 (DC2's two days).

Per pass: the conditioned maps (the frozen chain to the STFT, `idv2_core.conditioned_map`), the frozen
PRIMARY feature bank (`id19_featbank.pass_features`), each link's torso frequency and channel, press
pace, and the pass's session, room, kind (tracking walk or identification capture), block, path and
participant code. Reads `data/` (and the addendum E relabelled source for B's identification captures)
and writes only `runs/identify/dev/bank/`. Free-movement recordings (`DEMO_free`) and calibration walks
(`_C_walk`) are never read into the bank.

    PYTHONPATH=. python3 -m pipeline.identify.idx_bank
"""

from __future__ import annotations

import glob
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idrelabel as R
from pipeline.identify import idv2_core as C
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "dev", "bank")
LINKS = ("RX1", "RX2", "RX3")
TRACK = {"A1": ("data/room_A/session_01", "_walk"), "A2": ("data/room_A/session_02", "_walk"),
         "A3": ("data/room_A/session_03", "_TEST_walk"), "B1": ("data/room_B/session_B1", "_walk"),
         "B2": ("data/room_B/session_B2", "_walk")}
IDCAP = {"B1": os.path.join(R.DST, "session_01"), "B2": os.path.join(R.DST, "session_02")}


def recordings() -> list:
    out = []
    for ses, (d, suf) in TRACK.items():
        for name in SIX:
            stem = os.path.join(d, f"participant_{name}{suf}")
            assert os.path.exists(stem + ".gt.json"), stem
            out.append({"session": ses, "room": ses[0], "kind": "track", "block": "track", "name": name, "stem": stem})
    for ses, d in IDCAP.items():
        day = ses[1]
        for name in SIX:
            for blk in ("natural", "slow", "fast"):
                stem = os.path.join(d, f"participant_{name}_idpath_d{day}_{blk}")
                assert os.path.exists(stem + ".gt.json"), stem
                out.append({"session": ses, "room": "B", "kind": "idcap", "block": blk, "name": name, "stem": stem})
    for r in out:
        assert "DEMO_free" not in r["stem"] and "_C_walk" not in r["stem"]
    return out


def pass_items(rec: dict) -> list:
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    links = [D._link(f"{rec['stem']}_{L}.bin") for L in LINKS]
    gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
    items = []
    for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
        t0, t1 = float(q["t_start"]), float(q["t_end"])
        grid = np.arange(t0, t1, 1.0 / C.HP["fs"])
        A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, SC]
        Rr = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links], np.float64)
        items.append({
            "session": rec["session"], "room": rec["room"], "kind": rec["kind"], "block": rec["block"],
            "anon": anon(rec["name"]), "path": q["path_name"], "t_start": t0, "t_end": t1,
            "speed_m_s": (5.0 if rec["kind"] == "idcap" else float(np.hypot(*np.subtract(q["anchor_coords"][-1], q["anchor_coords"][0]))))
                         / max(t1 - t0, 1e-6),
            "flagged": bool(q.get("flagged", False)),
            "torso_hz": {L: D.torso_hz(A[i]) for i, L in enumerate(LINKS)},
            "channel": {L: links[i][3] for i, L in enumerate(LINKS)},
            "feats": FB.pass_features(A, Rr),
            "maps": np.stack([C.conditioned_map(A[li]) for li in range(3)]).astype(np.float32)})
    return items


def build(out: str = OUT) -> dict:
    os.makedirs(out, exist_ok=True)
    recs = recordings()
    items = []
    t0 = time.time()
    for k, rec in enumerate(recs):
        items += pass_items(rec)
        print(f"{k + 1}/{len(recs)} {rec['session']} {rec['kind']} {rec['block']} {anon(rec['name'])}: "
              f"{len(items)} passes, {time.time() - t0:.0f} s", flush=True)
    names = sorted(set().union(*[set(it["feats"]) for it in items]))
    col = {n: j for j, n in enumerate(names)}
    X = np.full((len(items), len(names)), np.nan, np.float32)
    for i, it in enumerate(items):
        for n, v in it.pop("feats").items():
            if v is not None and np.isfinite(v):
                X[i, col[n]] = v
    maps = [it.pop("maps") for it in items]
    np.save(os.path.join(out, "features.npy"), X)
    json.dump(names, open(os.path.join(out, "feature_names.json"), "w"))
    pickle.dump(maps, open(os.path.join(out, "maps.pkl"), "wb"))
    txt = json.dumps({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": len(items), "passes": items}, default=float)
    from pipeline.identify import idmax_common as IC
    assert IC.no_names(txt)
    open(os.path.join(out, "meta.json"), "w").write(txt)
    return {"n": len(items)}


if __name__ == "__main__":
    print(build())
    sys.exit(0)
