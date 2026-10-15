"""ide_replay. The evaluation harness (`runs/identify/engine/PLAN.md`, section 4): a recorded session replayed through
`engine.Engine`, in session order, one start press per walk, every other press ignored, decisions causal.

Each recording's frames are pushed in arrival order up to each window's cap and the engine polled there (the
engine reads only frames arrived by its decision time, so the block size cannot change a decision). The
session's calibration pool runs across its recordings. Every window's features and maps are checked against
the engine bank's row for that pass (the same code on the same frames).

    PYTHONPATH=. python3 -m pipeline.identify.ide_replay --session B2 --model loso_B2 [--T 3.0] [--device mps]
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
from pipeline.identify import idmax_common as IC
from pipeline.identify import idx_bank as B

OUT = os.path.join(EN.ENG, "replays")


def session_recordings(session: str) -> list:
    recs = [r for r in B.recordings() if r["session"] == session]
    first = {}
    for r in recs:
        gt = json.load(open(r["stem"] + ".gt.json", encoding="utf-8"))
        first[r["stem"]] = min(float(q["t_start"]) for q in gt["passes"])
    return sorted(recs, key=lambda r: first[r["stem"]])


def load_bank(T: float, gs: bool, v2: bool = False) -> dict:
    """The engine bank a replay is checked against: v2 (`EN.bank_dir`) for engine v2 models (names ending in
    `EN.SUFFIX`), else the v1 bank."""
    d = EN.bank_dir(T) if v2 else os.path.join(EN.ENG, f"bank_T{T:.1f}{'_gs' if gs else ''}")
    meta = json.load(open(os.path.join(d, "meta.json")))["passes"]
    return {"meta": meta, "X": np.load(os.path.join(d, "features.npy")), "maps": pickle.load(open(os.path.join(d, "maps.pkl"), "rb")),
            "index": {(m["session"], round(m["t_start"], 6)): i for i, m in enumerate(meta)}}


def direction_mode() -> str:
    """PLAN 2.4: the detected direction if its accuracy on the identification walks is at least 95 %."""
    c = json.load(open(os.path.join(EN.ENG, "checks", "checks.json")))
    return "detected" if c["direction"]["RULE_detected_used"] else "recorded"


def replay(session: str, model_dir: str, T: float, gs: bool, device: str, dmode: str, on_decision=None, realtime=None) -> list:
    """The session through one engine; returns the decisions (dicts), in press order."""
    from pipeline.io.capture_logger import read_capture_file
    eng = EN.Engine(model_dir, T=T, amp_norm=gs, device=device)
    out = []
    for rec in session_recordings(session):
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        eng.new_recording(layout)
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + T + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                eng.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else q["path_name"]
            eng.press(t0, path=known, info={"session": session, "t_start": t0, "kind": rec["kind"], "block": rec["block"],
                                            "path": q["path_name"], "t_end": float(q["t_end"])})
            for d in eng.poll(lim):
                out.append(d)
                if on_decision:
                    on_decision(d)
    out_upd = list(eng.session.update_s) if eng.session is not None else []
    for d, u in zip(out, out_upd):
        d["update_s"] = u
    return out


def run(session: str, model: str, T: float = 3.0, device: str = "cpu", tag: str = None) -> dict:
    from pipeline.identify import ide_train as IT
    gs = IT.gs_adopted()
    dmode = direction_mode()
    model_dir = os.path.join(EN.ENG, "models", model)
    bank = load_bank(T, gs, v2=model.endswith(EN.SUFFIX))
    t_all = time.time()
    dec = replay(session, model_dir, T, gs, device, dmode)
    rows, feq, meq = [], [], []
    for d in dec:
        i = bank["index"][(session, round(d["t0"], 6))]
        rows.append(i)
        x = d["extraction"]
        feq.append(bool(np.array_equal(x["features"], bank["X"][i], equal_nan=True)))
        meq.append(bool(x["maps"].shape == bank["maps"][i].shape and np.array_equal(x["maps"], bank["maps"][i])))
    comps = {c: np.array([d["components"][c] for d in dec]) for c in dec[0]["components"]}
    arr = {"te": np.array(rows), "ensemble": np.array([d["ensemble"] for d in dec]),
           "ensemble_nopace": np.array([d["ensemble_nopace"] for d in dec]),
           "confidence": np.array([d["confidence"] for d in dec]),
           **{f"c_{c}": v for c, v in comps.items()},
           "t0": np.array([d["t0"] for d in dec]), "t_dec": np.array([d["t_dec"] for d in dec]),
           "wait_s": np.array([d["wait_s"] for d in dec]), "extract_s": np.array([d["extraction"]["extract_s"] for d in dec]),
           "model_s": np.array([d["model_s"] for d in dec]), "latency_s": np.array([d["latency_s"] for d in dec]),
           "update_s": np.array([d.get("update_s", np.nan) for d in dec]), "calib_n": np.array([d["calib_n"] for d in dec]),
           "path_used": np.array([d["extraction"]["path"] for d in dec]), "dir_detected": np.array([str(d["extraction"]["dir_detected"]) for d in dec]),
           "wifi_speed": np.array([d["extraction"]["wifi_speed"] for d in dec]),
           "features_equal_bank": np.array(feq), "maps_equal_bank": np.array(meq)}
    name = tag or f"{model}_{session}_T{T:.1f}"
    os.makedirs(OUT, exist_ok=True)
    np.savez(os.path.join(OUT, f"{name}.npz"), **arr)
    summ = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "session": session, "model": model, "T": T,
            "gs": gs, "direction_mode": dmode, "device": device, "n": len(dec),
            "features_equal_bank": int(np.sum(feq)), "maps_equal_bank": int(np.sum(meq)),
            "latency_s_median": round(float(np.median(arr["latency_s"])), 3), "update_s_median": round(float(np.nanmedian(arr["update_s"])), 3),
            "update_s_max": round(float(np.nanmax(arr["update_s"])), 3), "seconds": round(time.time() - t_all, 1)}
    txt = json.dumps(summ, indent=1)
    assert IC.no_names(txt)
    open(os.path.join(OUT, f"{name}.json"), "w").write(txt)
    print(txt, flush=True)
    return summ


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", required=True, nargs="+")
    ap.add_argument("--model", required=True, nargs="+", help="one model per session, in the same order")
    ap.add_argument("--T", type=float, default=3.0)
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    a = ap.parse_args(argv)
    assert len(a.session) == len(a.model)
    for s, m in zip(a.session, a.model):
        run(s, m, a.T, a.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
