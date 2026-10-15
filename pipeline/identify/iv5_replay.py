"""iv5_replay. Engine v5's replays (`prompt_identification_v5_ship.md`, steps 2 and 4), through `engine.Engine` on the
recorded sessions, in session order, one start press per walk:

- `null --model loso_A1_v4 --session A1`: step 2's null check. A v4 model through the unchanged harness
  (`ide_replay.replay`) and the new engine code must reproduce the shipped v4 replay exactly (every array but the
  timings; written to `runs/identify/v5/null/`, never over a v4 file).
- `replay --model loso_A1_v5 --session A1`: step 4. A v5 model, the room from the session; each walk's frames pushed up to
  its last window's cap (t0 + 0.30 + T + 1 s) and the engine polled there, so all three windows are decided. Checks: the
  0 s window equals the bank, each offset window equals `runs/identify/best/extract/tta/<session>.pkl` (features, maps,
  path, speed at the model's alpha), and the decisions reproduce `runs/identify/roomA/stores/split_A3.npz` (max abs
  difference 1e-6, every decision equal). Written as `runs/identify/engine/replays/<model>_<session>_T4.0.npz`.

    PYTHONPATH=. python3 -m pipeline.identify.iv5_replay null --model loso_A1_v4 --session A1 --device mps
    PYTHONPATH=. python3 -m pipeline.identify.iv5_replay replay --model loso_A1_v5 --session A1 --device mps

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ide_replay as RP

V5D = os.path.join("runs", "identify", "v5")
NULL = os.path.join(V5D, "null")
CHK = os.path.join(V5D, "checks")
T = 4.0
TIMING = ("extract_s", "model_s", "latency_s", "update_s")


def gs() -> bool:
    from pipeline.identify import ide_train as IT
    return IT.gs_adopted()


def release(device: str) -> None:
    """The allocator's cached MPS memory released after each walk (no number changes: last push's `check-d1`), so a long
    session stays inside the 12 GB limit; the harness's own per-decision callback calls it."""
    if device == "mps":
        import torch
        torch.mps.empty_cache()


def arrays_v4(dec: list, bank: dict, session: str) -> dict:
    """`ide_replay.run`'s arrays, the same statements."""
    rows, feq, meq = [], [], []
    for d in dec:
        i = bank["index"][(session, round(d["t0"], 6))]
        rows.append(i)
        x = d["extraction"]
        feq.append(bool(np.array_equal(x["features"], bank["X"][i], equal_nan=True)))
        meq.append(bool(x["maps"].shape == bank["maps"][i].shape and np.array_equal(x["maps"], bank["maps"][i])))
    comps = {c: np.array([d["components"][c] for d in dec]) for c in dec[0]["components"]}
    return {"te": np.array(rows), "ensemble": np.array([d["ensemble"] for d in dec]),
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


def diff(a, b) -> float:
    """Max abs difference (0.0 when equal; NaN-equal counts as equal); inf on a shape or kind mismatch."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return float("inf")
    if a.dtype.kind in "fc" or b.dtype.kind in "fc":
        a, b = a.astype(float), b.astype(float)
        both = np.isnan(a) & np.isnan(b)
        if (np.isnan(a) ^ np.isnan(b)).any():
            return float("inf")
        return float(np.abs(np.where(both, 0.0, a - b)).max()) if a.size else 0.0
    return 0.0 if np.array_equal(a, b) else float("inf")


def null(model: str, session: str, device: str) -> bool:
    bank = RP.load_bank(T, gs(), v2=True)
    t_all = time.time()
    dec = RP.replay(session, os.path.join(EN.ENG, "models", model), T, gs(), device, RP.direction_mode(),
                    on_decision=lambda d: release(device))
    arr = arrays_v4(dec, bank, session)
    name = f"{model}_{session}_T{T:.1f}"
    z = np.load(os.path.join(RP.OUT, f"{name}.npz"))
    res = {"model": model, "session": session, "device": device, "n": len(dec), "built": time.strftime("%Y-%m-%d %H:%M:%S"),
           "seconds": round(time.time() - t_all, 1), "compared": {}, "timings_not_compared": list(TIMING)}
    for k in z.files:
        if k in TIMING:
            continue
        res["compared"][k] = diff(arr[k], z[k])
    res["max_abs_diff"] = max(res["compared"].values())
    res["PASSED"] = bool(res["max_abs_diff"] == 0.0 and set(z.files) == set(arr))
    os.makedirs(NULL, exist_ok=True)
    np.savez(os.path.join(NULL, f"{name}.npz"), **arr)
    json.dump(res, open(os.path.join(NULL, f"{name}.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("model", "session", "n", "max_abs_diff", "PASSED", "seconds")}), flush=True)
    return res["PASSED"]


# ------------------------------------------------------------------ step 4: the v5 replays

def replay_v5(session: str, model_dir: str, device: str, dmode: str) -> list:
    """`ide_replay.replay` for an engine v5 model: the room from the session; each walk polled at its last window's cap."""
    from pipeline.io.capture_logger import read_capture_file
    eng = EN.Engine(model_dir, T=T, amp_norm=gs(), device=device, room=session[0])
    assert eng.v5
    extra = max(eng.model.offsets)
    out = []
    for rec in RP.session_recordings(session):
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        eng.new_recording(layout)
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + extra + T + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                eng.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else q["path_name"]
            eng.press(t0, path=known, info={"session": session, "t_start": t0, "kind": rec["kind"], "block": rec["block"],
                                            "path": q["path_name"], "t_end": float(q["t_end"])})
            got = eng.poll(lim)
            assert len(got) == 1, f"walk at {t0}: {len(got)} decisions at its last cap"
            out += got
            release(device)
        assert eng.open_windows == 0
    for d, u in zip(out, eng.session.update_s):
        d["update_s"] = u
    return out


def tta(session: str) -> dict:
    d = pickle.load(open(os.path.join("runs", "identify", "best", "extract", "tta", f"{session}.pkl"), "rb"))
    return {(int(r), f"{o:.2f}"): j for j, (r, o) in enumerate(zip(d["rows"], d["offset"]))}, d


def run_v5(model: str, session: str, device: str) -> bool:
    from pipeline.identify import ilc_outer as CO
    from pipeline.identify import ilr_core as R
    bank = RP.load_bank(T, gs(), v2=True)
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    md = os.path.join(EN.ENG, "models", model)
    man = json.load(open(os.path.join(md, "manifest.json")))
    alpha = man["alpha"]
    t_all = time.time()
    dec = replay_v5(session, md, device, RP.direction_mode())
    arr = arrays_v4(dec, bank, session)
    idx, tt = tta(session)
    keys = sorted({k for d in dec for k in d["windows"]})
    chk = {"tta_features": [], "tta_maps": [], "tta_path": [], "tta_speed": []}
    for k in keys:
        if k == 0.0:
            continue
        o = f"{k:.2f}"
        for c in dec[0]["windows"][k]["components"]:
            arr[f"c_{c}_{o}"] = np.array([d["windows"][k]["components"][c] for d in dec])
        arr[f"path_used_{o}"] = np.array([d["windows"][k]["extraction"]["path"] for d in dec])
        arr[f"wifi_speed_{o}"] = np.array([d["windows"][k]["extraction"]["wifi_speed"] for d in dec])
        arr[f"t_dec_{o}"] = np.array([d["windows"][k]["t_dec"] for d in dec])
        arr[f"extract_s_{o}"] = np.array([d["windows"][k]["extraction"]["extract_s"] for d in dec])
        fe, me, pe, se = [], [], [], []
        for i, d in zip(arr["te"], dec):
            j = idx[(int(i), o)]
            x = d["windows"][k]["extraction"]
            fe.append(bool(np.array_equal(np.asarray(x["features"], np.float64)[cols], tt["F"][j], equal_nan=True)))
            me.append(bool(np.array_equal(x["maps"], tt["maps"][j])))
            pe.append(str(x["path"]) == str(tt["path_used"][j]))
            sp = float(tt[f"speed_{alpha}"][j])
            se.append(bool(x["wifi_speed"] == sp or (np.isnan(x["wifi_speed"]) and np.isnan(sp))))
        arr[f"features_equal_tta_{o}"], arr[f"maps_equal_tta_{o}"] = np.array(fe), np.array(me)
        arr[f"path_equal_tta_{o}"], arr[f"speed_equal_tta_{o}"] = np.array(pe), np.array(se)
        for nm, v in (("tta_features", fe), ("tta_maps", me), ("tta_path", pe), ("tta_speed", se)):
            chk[nm].append(int(np.sum(v)))
    arr["t_dec_0.00"] = np.array([d["windows"][0.0]["t_dec"] for d in dec])
    arr["weight_a"] = np.array([d["weight_a"] for d in dec])
    arr["room"] = np.array([d["room"] for d in dec])
    name = f"{model}_{session}_T{T:.1f}"
    os.makedirs(RP.OUT, exist_ok=True)
    np.savez(os.path.join(RP.OUT, f"{name}.npz"), **arr)
    # the decisions against split_A3 (the configuration v5 ships)
    short = model[:-3]
    CO.OUTD = os.path.join(R.RD, "stores")
    ref = CO.load("split_A3")[f"{short}|{session}"]
    n = len(dec)
    same_rows = bool(np.array_equal(arr["te"], ref[0]))
    lpd = float(np.abs(arr["ensemble"] - ref[2]).max()) if same_rows else float("inf")
    same_dec = bool(same_rows and np.array_equal(arr["ensemble"].argmax(1), ref[2].argmax(1)))
    res = {"model": model, "session": session, "device": device, "n": n, "built": time.strftime("%Y-%m-%d %H:%M:%S"),
           "seconds": round(time.time() - t_all, 1), "room": session[0], "weights_a": sorted(set(arr["weight_a"].tolist())),
           "features_equal_bank": int(arr["features_equal_bank"].sum()), "maps_equal_bank": int(arr["maps_equal_bank"].sum()),
           **{f"{k}_per_offset": v for k, v in chk.items()}, "split_A3_same_rows": same_rows,
           "split_A3_max_abs_diff": lpd, "split_A3_decisions_equal": int(np.sum(arr["ensemble"].argmax(1) == ref[2].argmax(1))) if same_rows else 0,
           "latency_s_median": round(float(np.median(arr["latency_s"])), 3), "wait_s_median": round(float(np.median(arr["wait_s"])), 3),
           "model_s_median": round(float(np.median(arr["model_s"])), 3)}
    res["PASSED"] = bool(same_rows and lpd <= 1e-6 and same_dec and res["features_equal_bank"] == n and res["maps_equal_bank"] == n
                         and all(v == n for vv in chk.values() for v in vv))
    os.makedirs(CHK, exist_ok=True)
    json.dump(res, open(os.path.join(CHK, f"replay_{name}.json"), "w"), indent=1)
    json.dump(res | {"label": EN.LABEL}, open(os.path.join(RP.OUT, f"{name}.json"), "w"), indent=1)
    print(json.dumps(res), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    what = sys.argv[1]
    m = sys.argv[sys.argv.index("--model") + 1]
    s = sys.argv[sys.argv.index("--session") + 1]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
    if what == "null":
        sys.exit(0 if null(m, s, dev) else 1)
    if what == "replay":
        sys.exit(0 if run_v5(m, s, dev) else 1)
    raise SystemExit(what)
