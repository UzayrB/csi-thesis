"""ixt_verify. The teaching-pack brief's verification (`runs/identify/engine/PLAN.md`, the teaching note, section V): B2
streamed through the live app's rig path (`pipeline/live/identify_recorded.py` and `EngineConsumer`, `loso_B2`), every
decision logged, then compared with the saved harness replay pass for pass. The app-level numbers the pack quotes for
the two worked walks are this run's own logged values. From 1 Oct: engine v2 (`loso_B2_x`, the cadence bug fix), outputs
`verify_B2_x*`; the v1 run's files are kept as superseded.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_verify [--device mps]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

OUT = os.path.join("runs", "identify", "teaching")
M = EN.model_name("loso_B2")
SUF = EN.SUFFIX


def run(device: str = "mps") -> dict:
    from pipeline.identify import ide_train as IT
    from pipeline.live import identify_engine as IE
    from pipeline.live.identify_recorded import RecordedSource, stream
    t_all = time.time()
    md = IE.model_dir(M)
    ts = IE.guard(md, "B2")
    eng = EN.Engine(md, amp_norm=IT.gs_adopted(), device=device)
    jl = os.path.join(OUT, f"verify_B2{SUF}_rig_path.jsonl")
    if os.path.exists(jl):
        os.remove(jl)                                   # this run's own log (never an earlier output of another kind)
    app = IE.EngineApp(eng, M, replay=True, jsonl=jl, dmode=IE.direction_mode())
    app.stream_label = "B2"
    c = IE.EngineConsumer(app, None)
    stream(c, RecordedSource("B2"), speed="max")
    dec = app.decisions
    h = np.load(os.path.join(EN.ENG, "replays", f"{M}_B2_T{EN.T_S:.1f}.npz"))
    e = np.array([d["ensemble"] for d in dec])
    t0 = np.array([d["t0"] for d in dec])
    same_t0 = bool(len(dec) == len(h["t0"]) and np.array_equal(t0, h["t0"]))
    same_arg = int(np.sum(e.argmax(1) == h["ensemble"].argmax(1))) if same_t0 else 0
    max_diff = float(np.max(np.abs(e - h["ensemble"]))) if same_t0 else float("nan")
    arr = {"t0": t0, "t_dec": np.array([d["t_dec"] for d in dec]), "wait_s": np.array([d["wait_s"] for d in dec]),
           "latency_s": np.array([d["latency_s"] for d in dec]), "extract_s": np.array([d["extraction"]["extract_s"] for d in dec]),
           "model_s": np.array([d["model_s"] for d in dec]), "ensemble": e, "confidence": np.array([d["confidence"] for d in dec]),
           "calib_n": np.array([d["calib_n"] for d in dec]), "wifi_speed": np.array([d["extraction"]["wifi_speed"] for d in dec]),
           "path": np.array([d["extraction"]["path"] for d in dec]), "dir_detected": np.array([str(d["extraction"]["dir_detected"]) for d in dec]),
           "dir_slope": np.array([d["extraction"]["dir_slope"] for d in dec]),
           **{f"c_{k}": np.array([d["components"][k] for d in dec]) for k in dec[0]["components"]}}
    np.savez(os.path.join(OUT, f"verify_B2{SUF}_rig_path.npz"), **arr)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "path": "the rig path: RecordedSource -> EngineConsumer -> EngineApp -> engine",
           "model": M, "engine_version": EN.ENGINE_VERSION, "training_sessions": ts, "device": device, "n_app": len(dec), "n_harness": int(len(h["t0"])),
           "press_times_equal": same_t0, "decisions_equal": same_arg, "ensemble_max_abs_diff": max_diff,
           "PASSED": bool(same_t0 and same_arg == len(dec) == 299 and max_diff < 1e-6), "jsonl": jl,
           "seconds": round(time.time() - t_all, 1)}
    json.dump(res, open(os.path.join(OUT, f"verify_B2{SUF}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    run(ap.parse_args().device)
    sys.exit(0)
