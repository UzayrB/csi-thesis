"""pd_cells: items 3 and 4 of the DC2 results batch. EXPLORATORY, POST HOC to the Room B data.

Pre-registration: `reports/PREREG_postDC2_training_2026-09-28.md` (written before item 2 ran).

    python3 -m pipeline.constrained.pd_cells run --cell 3a        # view, stats, train, infer, decode, lock
    python3 -m pipeline.constrained.pd_cells queue --cells 3a 3b ...
    python3 -m pipeline.constrained.pd_cells b10                  # Room B's 1 s features, once

WHAT A CELL IS. Heads trained on a set of sessions from either room, then the frozen DC2 machinery on
one test session: `dc2_run.do_infer`, `dc2_run.do_decode` and `dc2_scorerlock._inner`, called with this
cell's settings. Each step is its own process, because the pipeline binds its roots at import.

THE VIEW, per cell under runs/dc2_results/cells/<cell>/, so every loader works unchanged and data/ is
never written. All sessions sit in one view room, as DC2's own view does:
  data/room_B/session_<s>     the raw capture and ground truth
  win05/room_B/session_<s>    0.5 s press-aligned windows (Room A: the ONE lattice; Room B: item 2's cut)
  win10/room_B/session_<s>    1.0 s windows, training sessions only (Room A: runs/constrained/windows_s1.0_roomA; Room B:
                              runs/constrained/windows_s1.0_dc2)
  shared05/, shared10/        features and RSSI caches, linked file by file
  train_<h>/                  where head h trains (its features link to its own stride)
  art_<h>/                    what inference and decoding read
A ROOM B TRAINING SESSION IS LINKED FILE BY FILE WITHOUT ITS CALIBRATION RECORDING, so no training step,
reader or chain prior can see a calibration walk. The TEST session is linked whole: configuration B
needs its calibration walk.

THE READERS' TRAINING FEATURES for a Room B day come from the frozen Room A heads as item 2 inferred them
on that day, under a per-day tag (`s010203_to_sB1`, `s010203_to_sB2`), because one shared tag would make
the two days' recordings, which have the same names, collide (the fault `dc2c.py` records).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(REPO_ROOT, "runs", "dc2_results")
J = os.path.join
DATA_A, DATA_B = J(REPO_ROOT, "data", "room_A"), J(REPO_ROOT, "data", "room_B")
A_WIN05 = J(REPO_ROOT, "runs", "constrained", "windows_s0.5_pressalign", "room_A")
A_WIN10 = J(REPO_ROOT, "runs", "constrained", "windows_s1.0_roomA", "room_A")
B_WIN10 = J(REPO_ROOT, "runs", "constrained", "windows_s1.0_dc2", "room_B")
DC2_BY = J(REPO_ROOT, "runs", "constrained", "dc2_room_B_s0.5_pressalign", "by_session")
A_SH05 = J(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_shared")
A_SH10 = J(REPO_ROOT, "runs", "artefacts_s1.0_retrain_shared")
B_SH10 = J(RES, "shared10_roomB")
FROZEN_HALF = J(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_roomA3")
FROZEN_TAG = "s010203_to_sB"
VIEW_ROOM = "room_B"

#: head -> (training stride, [(kind, out cells, seed)]); the frozen DC2 heads' recipe (d5_train_room_a)
HEADS = {"half": ("05", [("g", 25, 0), ("pos", 2, 0)]), "fh1s": ("10", [("g", 25, 0)]),
         "g1s1": ("10", [("g", 25, 1)]), "g1s2": ("10", [("g", 25, 2)]), "g100": ("10", [("g", 100, 0)])}

#: cell -> (training sessions, test session, normalisation). The pre-registration's sections 4 and 5.
CELLS = {"3a": (("B1",), "B2", "pooled"), "3b": (("B2",), "B1", "pooled")}
for _nm, (_tr, _te) in {"B2": (("01", "02", "03", "B1"), "B2"), "B1": (("01", "02", "03", "B2"), "B1"),
                        "A1": (("02", "03", "B1", "B2"), "01"), "A2": (("01", "03", "B1", "B2"), "02"),
                        "A3": (("01", "02", "B1", "B2"), "03")}.items():
    CELLS[f"4ii_{_nm}"] = (_tr, _te, "pooled")
    CELLS[f"4iii_{_nm}"] = (_tr, _te, "per_room")
#: THE PLUMBING CHECK: shipped Room A heads s0102_to_s03 through this harness must give d4_headline's
#: committed decisions on every one of session 03's 120 passes. Nothing is trained.
CELLS["plumb_A3"] = (("01", "02"), "03", "pooled")
#: THE TRAINING-PATH PLUMBING CHECK: session 01 trained FRESH through this harness must reproduce the
#: shipped s01_to_s02 heads bit for bit (batch 23c item 5: the code is deterministic) and its decisions.
CELLS["plumbT_A2"] = (("01",), "02", "pooled")
#: ADDENDUM 2026-09-28 (recipe): Room A comparators through this harness and recipe, reported BESIDE the
#: pre-registered ones. The shipped Room A folds' 0.5 s heads trained on the grid lattice.
for _nm, (_tr, _te) in {"A1": (("02", "03"), "01"), "A2": (("01", "03"), "02"),
                        "A3": (("01", "02"), "03")}.items():
    CELLS[f"4i_{_nm}"] = (_tr, _te, "pooled")
for _tr, _te in (("01", "03"), ("02", "01"), ("02", "03"), ("03", "01"), ("03", "02")):
    CELLS[f"3ref_s{_tr}_to_s{_te}"] = ((_tr,), _te, "pooled")
#: ADDENDUM 2026-09-28 20:13 (posthoc_cell), POST HOC: ONE model on A1+A2+B1, tested on A3 and on B2.
#: It trains once in ph_A3; ph_B2 takes the same weight files, byte for byte, under its own tag.
CELLS["ph_A3"] = (("01", "02", "B1"), "03", "pooled")
CELLS["ph_B2"] = (("01", "02", "B1"), "B2", "pooled")
SHARED_MODELS = {"ph_B2": "ph_A3"}
#: DEVELOPMENT D1 (DEVLOG_TRACKING_2026-09-28): per-recording normalisation, choices on inner validation.
#: Each of the ten three-session training sets is trained once per normalisation and tested on both
#: sessions it leaves out (the second cell shares the first cell's weights). Finals train on four.
SESS5 = ("01", "02", "03", "B1", "B2")
LOSO_NAME = {"01": "A1", "02": "A2", "03": "A3", "B1": "B1", "B2": "B2"}
PRN_STATS = J(RES, "prn_stats.json")
FROZEN_DC2 = {"half": J(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_roomA3"),
              "fh1s": J(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s0"),
              "g1s1": J(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s1"),
              "g1s2": J(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s2"),
              "g100": J(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_g100")}
D1_ORDER, TWIN = [], {}
for _S in __import__("itertools").combinations(SESS5, 3):
    _rest = [x for x in SESS5 if x not in _S]
    for _nk, _norm in (("p", "pooled"), ("r", "per_recording")):
        _a, _b = (f"d1{_nk}_{''.join(_S)}_to_{_rest[0]}", f"d1{_nk}_{''.join(_S)}_to_{_rest[1]}")
        CELLS[_a], CELLS[_b] = (_S, _rest[0], _norm), (_S, _rest[1], _norm)
        SHARED_MODELS[_b] = _a
        D1_ORDER += [_a, _b]
        if _nk == "r":
            TWIN[_a], TWIN[_b] = _a.replace("d1r_", "d1p_"), _b.replace("d1r_", "d1p_")
#: the pooled three-session models that already exist, reused rather than retrained
SHARED_MODELS["d1p_0102B1_to_03"] = "ph_A3"
SHARED_MODELS["d1p_010203_to_B1"] = "FROZEN_DC2"
for _held in SESS5:
    _tr = tuple(x for x in SESS5 if x != _held)
    CELLS[f"d1r_final_{LOSO_NAME[_held]}"] = (_tr, _held, "per_recording")
    TWIN[f"d1r_final_{LOSO_NAME[_held]}"] = f"4ii_{LOSO_NAME[_held]}"
#: THE SPLIT, the operator's decision of 2026-09-28 22:2x: train and choose on A1, A2, B1 ONLY; A3 and B2 are
#: the tests and the renders and never enter training. D1 redone on it: inner validation rotates over
#: the three development sessions (train two, validate the third), then one final on all three.
DEV3, TEST2 = ("01", "02", "B1"), ("03", "B2")
D1S_ORDER = []
for _v in DEV3:
    _tr = tuple(x for x in DEV3 if x != _v)
    for _nk, _norm in (("p", "pooled"), ("r", "per_recording")):
        _c = f"d1s{_nk}_{''.join(_tr)}_to_{_v}"
        CELLS[_c] = (_tr, _v, _norm)
        D1S_ORDER.append(_c)
        if _nk == "r":
            TWIN[_c] = _c.replace("d1sr_", "d1sp_")
SHARED_MODELS["d1sp_0102_to_B1"] = "4i_A3"          # A1+A2 pooled already trained (cell 4i_A3)
CELLS["d1sr_final_A3"] = (DEV3, "03", "per_recording")
CELLS["d1sr_final_B2"] = (DEV3, "B2", "per_recording")
SHARED_MODELS["d1sr_final_B2"] = "d1sr_final_A3"
TWIN["d1sr_final_A3"], TWIN["d1sr_final_B2"] = "ph_A3", "ph_B2"
D1S_ORDER += ["d1sr_final_A3", "d1sr_final_B2"]
#: DEVELOPMENT D2 (BRIEF_tracking_attack_2026-09-28): training variants SCREENED with the single 0.5 s g25
#: head on the three rotations, on either D1 normalisation's base (d2p_ pooled, d2r_ per-recording; the
#: queue runs D1's winner). A screen cell trains only the g25 half head, through pd_train; the half
#: position head is copied from the base cell byte for byte, because the decode reads positions only
#: through the readers, which stay the pooled D1 rotation cell's. It decodes with a one-head pool.
D2_VARIANTS = {"base": None, "aug": {"aug": True}, "rrel": {"rrel": True},
               "early": {"early": True, "max_epochs": 40, "snapshots": True}, "mix": {"mixup": True}}
D2, EARLYX = {}, {}
for _v in DEV3:
    _tr = tuple(x for x in DEV3 if x != _v)
    _rt = f"{''.join(_tr)}_to_{_v}"
    for _nk, _norm in (("p", "pooled"), ("r", "per_recording")):
        for _var, _o in D2_VARIANTS.items():
            if _nk == "r" and _var == "rrel":
                continue                   # subsumed: per-recording already centres RSSI on its idle
            _c = f"d2{_nk}_{_var}_{_rt}"
            CELLS[_c], TWIN[_c] = (_tr, _v, _norm), f"d1sp_{_rt}"
            D2[_c] = {"heads": ["half"], "opts": dict(_o or {}), "pos_from": f"d1s{_nk}_{_rt}"}
            if _o is None:
                SHARED_MODELS[_c] = f"d1s{_nk}_{_rt}"
        # the HONEST early-stopping screen: this rotation's early-stopped run read at the epoch the OTHER
        # two rotations chose (per link, their mean), so no epoch is chosen on the session it is scored on
        _c = f"d2{_nk}_earlyx_{_rt}"
        CELLS[_c], TWIN[_c] = (_tr, _v, _norm), f"d1sp_{_rt}"
        D2[_c] = {"heads": ["half"], "opts": {}, "pos_from": f"d1s{_nk}_{_rt}"}
        EARLYX[_c] = (f"d2{_nk}_early_{_rt}",
                      [f"d2{_nk}_early_{''.join(x for x in DEV3 if x != o)}_to_{o}" for o in DEV3 if o != _v])
#: LATER STAGES, registered from runs/dc2_results/stage_cells.json so a decision needs no code edit under
#: a running queue. {prefix: {"opts": {...}, "heads": [...] | "all", "base": "d1sp", "arch": null,
#: "rotations": true}} registers <prefix>_<rotation> on the three rotations; with "rotations": false and
#: "tests": {"A3": "03", "B2": "B2"} it registers <prefix>_A3 (trained on A1+A2+B1) and <prefix>_B2 sharing
#: its weights, with the pooled readers of ph_A3 / ph_B2 (TEST cells: the midpoint and FINAL only).
STAGE_CELLS = J(RES, "stage_cells.json")
if os.path.exists(STAGE_CELLS):
    with open(STAGE_CELLS, encoding="utf-8") as _f:
        _reg = json.load(_f)
    for _pre, _d in _reg.items():
        _heads = list(HEADS) if _d.get("heads", "all") == "all" else list(_d["heads"])
        if _d.get("rotations", True):
            for _v in DEV3:
                _tr = tuple(x for x in DEV3 if x != _v)
                _rt = f"{''.join(_tr)}_to_{_v}"
                _c = f"{_pre}_{_rt}"
                CELLS[_c], TWIN[_c] = (_tr, _v, "pooled"), f"d1sp_{_rt}"
                D2[_c] = {"heads": _heads, "opts": dict(_d.get("opts", {})), "arch": _d.get("arch"),
                          "pos_from": f"{_d.get('base', 'd1sp')}_{_rt}"}
                if _d.get("shared_from"):
                    SHARED_MODELS[_c] = f"{_d['shared_from']}_{_rt}"
                if _d.get("earlyx_of"):
                    # the honest version of an early-stopped registry prefix: its own run at the other
                    # rotations' mean best epoch (per head, kind and link)
                    _e = _d["earlyx_of"]
                    EARLYX[_c] = (f"{_e}_{_rt}", [f"{_e}_{''.join(x for x in DEV3 if x != o)}_to_{o}"
                                                  for o in DEV3 if o != _v])
        else:
            # TEST cells: trained on "train" (default A1+A2+B1), one cell per test session in "tests";
            # the first trains, the others share its weights byte for byte
            _trn = tuple(_d.get("train", DEV3))
            _tests = _d.get("tests", {"A3": "03", "B2": "B2"})
            _first = None
            for _nm, _te in _tests.items():
                _c = f"{_pre}_{_nm}"
                CELLS[_c] = (_trn, _te, "pooled")
                _tw = _d.get("readers", {}).get(_nm, {"03": "ph_A3", "B2": "ph_B2"}[_te])
                if _tw:                                    # null: the cell's own heads are its readers
                    TWIN[_c] = _tw
                D2[_c] = {"heads": _heads, "opts": dict(_d.get("opts", {})), "arch": _d.get("arch"),
                          "pos_from": _d.get("pos_from", "ph_A3")}
                if _first is None:
                    _first = _c
                    if _d.get("shared_from"):
                        SHARED_MODELS[_c] = _d["shared_from"]
                else:
                    SHARED_MODELS[_c] = _first
for _c in D1S_ORDER + ["ph_A3", "ph_B2", "4i_A3"] + list(D2):
    _tr, _te, _n = CELLS[_c]
    assert not (set(_tr) & set(TEST2)), f"{_c}: a test session in training"
    assert _c not in D2 or _te not in TEST2 or _c.endswith(("_A3", "_B2")), \
        f"{_c}: a test session in a development choice"
ORDER = ["3a", "3b"] + [f"4ii_{r}" for r in ("B2", "B1", "A1", "A2", "A3")] + \
        [f"4iii_{r}" for r in ("B2", "B1", "A1", "A2", "A3")] + \
        ["4i_A1", "4i_A2", "4i_A3"] + [f"3ref_s{a}_to_s{b}" for a, b in
                                       (("01", "03"), ("02", "01"), ("02", "03"), ("03", "01"), ("03", "02"))]
#: the pre-registration's section 7: the first item 4 cell's six networks, against 90 minutes
SPEED_RULE_CELL, SPEED_LIMIT_MIN = "4ii_B2", 90.0


def room_of(s: str) -> str:
    return "B" if s.startswith("B") else "A"


def raw_dir(s: str) -> str:
    return J(DATA_B if room_of(s) == "B" else DATA_A, f"session_{s}")


def cal_stems(s: str) -> set:
    if room_of(s) != "B":
        return set()
    with open(J(DATA_B, "calibration.json"), encoding="utf-8") as f:
        man = json.load(f)
    cal = set((man["sessions"].get(s) or {}).get("calibration_recordings") or [])
    assert cal, f"session {s}: the manifest names no calibration recording"
    return cal


def tag_of(tr, te) -> str:
    return f"s{''.join(tr)}_to_s{''.join(te)}"


def twin_tag(cell: str) -> str:
    return cfg(TWIN[cell])["heads_tag"]


def cfg(cell: str, cmd: str = None) -> dict:
    tr, te, norm = CELLS[cell]
    assert te not in tr, f"{cell}: the test session is in its own training set"
    base = J(RES, "cells", cell)
    tag = tag_of(tr, (te,))
    reader = "s01_to_s03" if cell == "plumb_A3" else tag     # plumbing: the shipped rule for session 03
    if cell in TWIN and cmd in ("decode", "lock", "readers"):
        # D1, D2: the start-of-walk readers stay the pooled twin's, so only the tracking heads change
        reader = twin_tag(cell) + "V0"
    d2 = D2.get(cell, {})
    return {"cell": cell, "base": base, "room": VIEW_ROOM, "stand_in": False, "train": tuple(tr),
            "heads": list(d2.get("heads", HEADS)), "opts": dict(d2.get("opts", {})),
            "test": te, "norm": norm, "b_sessions": {te: raw_dir(te)}, "heads_tag": tag,
            "reader_tag": reader, "model_src": {h: J(base, f"art_{h}") for h in HEADS},
            "manifest": J(DATA_B, "calibration.json"), "data_view": J(base, "data"),
            "win_view": J(base, "win05"), "win10": J(base, "win10"),
            "tree": (lambda h, _b=base: J(_b, f"art_{h}")), "shared": J(base, "shared05"),
            "shared10": J(base, "shared10")}


def _ln(src, dst):
    assert os.path.exists(src), f"missing source {src}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.lexists(dst):
        os.symlink(src, dst)


def _link_session(src_dir, dst_dir, drop: set):
    """Link a session folder whole, or file by file without the recordings named in drop."""
    if not drop:
        _ln(src_dir, dst_dir)
        return
    os.makedirs(dst_dir, exist_ok=True)
    for p in sorted(glob.glob(J(src_dir, "*"))):
        n = os.path.basename(p)
        if any(n == d or n.startswith(d + ".") or n.startswith(d + "_") for d in drop):
            continue
        _ln(p, J(dst_dir, n))


def _link_cache(src_root, dst_root, s, drop: set):
    for sub in ("features", "rssi_full"):
        for p in sorted(glob.glob(J(src_root, sub, f"session_{s}_*"))):
            n = os.path.basename(p)
            if any(f"session_{s}_{d}." in n for d in drop):
                continue
            _ln(os.path.realpath(p), J(dst_root, sub, n))


# ------------------------------------------------------------------------------------------ view

def do_view(c) -> int:
    te = c["test"]
    for s in c["train"] + (te,):
        is_test = s == te
        drop = set() if is_test else cal_stems(s)
        _link_session(raw_dir(s), J(c["data_view"], VIEW_ROOM, f"session_{s}"), drop)
        w05 = (J(A_WIN05, f"session_{s}") if room_of(s) == "A"
               else J(DC2_BY, s, "windows", "room_B", f"session_{s}"))
        _link_session(w05, J(c["win_view"], VIEW_ROOM, f"session_{s}"), drop)
        sh05 = A_SH05 if room_of(s) == "A" else J(DC2_BY, s, "art_shared")
        _link_cache(sh05, c["shared"], s, drop)
        if not is_test:
            w10 = J(A_WIN10, f"session_{s}") if room_of(s) == "A" else J(B_WIN10, f"session_{s}")
            _link_session(w10, J(c["win10"], VIEW_ROOM, f"session_{s}"), drop)
            _link_cache(A_SH10 if room_of(s) == "A" else B_SH10, c["shared10"], s, drop)
        elif c["opts"].get("early") and any(HEADS[h][0] == "10" for h in c["heads"]):
            # D2 early stopping: a 1 s head validates on the rotation's validation session at 1 s
            w10 = J(A_WIN10, f"session_{s}") if room_of(s) == "A" else J(B_WIN10, f"session_{s}")
            _link_session(w10, J(c["win10"], VIEW_ROOM, f"session_{s}"), cal_stems(s))
            _link_cache(A_SH10 if room_of(s) == "A" else B_SH10, c["shared10"], s, cal_stems(s))
    shutil.copy2(c["manifest"], J(c["data_view"], VIEW_ROOM, "calibration.json"))
    for h, (stride, _jobs) in HEADS.items():
        for d in (J(c["base"], f"train_{h}"), c["tree"](h)):
            os.makedirs(J(d, "models"), exist_ok=True)
            os.makedirs(J(d, "posteriors"), exist_ok=True)
        for sub in ("features", "rssi_full"):
            _ln(J(c["shared10"] if stride == "10" else c["shared"], sub), J(c["base"], f"train_{h}", sub))
            # every head is INFERRED over the 0.5 s windows, and the statistics step reads them too
            _ln(J(c["shared"], sub), J(c["tree"](h), sub))
    # the readers' per-day Room B tags, from item 2's frozen-head inference on that day
    half = c["tree"]("half")
    for s in c["train"]:
        if room_of(s) != "B":
            continue
        alias = tag_of(("01", "02", "03"), (s,))
        src = J(DC2_BY, s, "art_half")
        for f in glob.glob(J(src, "models", f"{FROZEN_TAG}_*")):
            dst = J(half, "models", os.path.basename(f).replace(FROZEN_TAG, alias, 1))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
        pf = J(src, "posteriors", f"{FROZEN_TAG}_g25_e24_s0_full.npz")
        dst = J(half, "posteriors", f"{alias}_g25_e24_s0_full.npz")
        if not os.path.exists(dst):
            shutil.copy2(pf, dst)
    _say(f"{c['cell']}: view built; train {c['train']}, test {te}, {c['norm']}")
    return 0


# ----------------------------------------------------------------------------- environment, steps

def env_for(c, head: str, step: str) -> dict:
    stride = HEADS[head][0]
    if step == "train":
        art, win = J(c["base"], f"train_{head}"), (c["win10"] if stride == "10" else c["win_view"])
    else:
        art, win = c["tree"](head), c["win_view"]
    tmap = {c["test"]: c["reader_tag"]}
    for s in c["train"]:
        if room_of(s) == "B":
            tmap[s] = tag_of(("01", "02", "03"), (s,))
    e = {k: v for k, v in os.environ.items() if not k.startswith("TDR_") or k == "TDR_LATTICE"}
    e.update({"TDR_ROOM": VIEW_ROOM, "TDR_DATA_ROOT": c["data_view"], "TDR_WINDOWS_ROOT": win,
              "TDR_ART_DIR": art, "TDR_TEST_TAG_MAP": json.dumps(tmap), "OMP_NUM_THREADS": "1"})
    return e


def _say(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def _sub(cell, cmd, head, step, log):
    c = cfg(cell, cmd)
    args = [sys.executable, "-m", "pipeline.constrained.pd_cells", cmd, "--cell", cell] + \
           (["--head", head] if head and cmd in ("train", "infer") else [])
    with open(log, "a", encoding="utf-8") as f:
        return subprocess.call(args, cwd=REPO_ROOT, env=env_for(c, head or "half", step), stdout=f,
                               stderr=subprocess.STDOUT)


# ------------------------------------------------------------------------- per-room normalisation

def _stats(X, rssi):
    """per_channel_stats' statistic for one link: (mean, sd) of the features and of the RSSI."""
    import numpy as np
    return ([float(np.mean(X, dtype=np.float64)), float(np.std(X, dtype=np.float64)) + 1e-8],
            [float(np.mean(rssi, dtype=np.float64)), float(np.std(rssi, dtype=np.float64)) + 1e-8])


def do_teststats(c) -> int:
    """(iii) only: the test session's normalisation, per link and channel, on its 0.5 s windows. Room B:
    every window of the day's calibration recording plus the idle windows before each evaluated
    recording's first press. Room A: those idle windows only (u1_adapt's anchor)."""
    import numpy as np
    from pipeline.constrained import dc2_run as R
    R._bind(c)                       # the roots asserted, then the import-time guards satisfied
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi, session_recordings
    from pipeline.constrained.u1_adapt import calibration_indices
    te, cal = c["test"], cal_stems(c["test"])
    Xs, Rs, used = [], [], {}
    for _s, stem in session_recordings(te):
        rec = load_meta(te, stem)
        idx = (np.arange(len(rec)) if stem in cal
               else np.asarray(calibration_indices(rec, first_presses(te, stem)), int))
        if not len(idx):
            continue
        Xs.append(load_features(te, stem, idx))
        Rs.append(load_rssi(te, stem, rec.t0_epoch)[idx])
        used[stem] = int(len(idx))
    X, R = np.concatenate(Xs), np.concatenate(Rs)
    out = {"test": te, "windows": used, "n": int(len(X)),
           "links": [dict(zip(("x", "r"), _stats(X[:, li], R[:, li]))) for li in range(3)]}
    with open(J(c["base"], "teststats.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    _say(f"{c['cell']}: test normalisation from {out['n']} windows of {te}")
    return 0


# ----------------------------------------------------------------------------------------- train

def do_train(c, head: str) -> int:
    import numpy as np
    import torch
    from pipeline.constrained.artefacts import model_path, train_pairing
    from pipeline.constrained.common import E_POST, E_REG
    from pipeline.constrained.dataset import walking_windows
    t0 = time.time()
    tr = walking_windows(list(c["train"]))
    stems = set(tr.stem.tolist())
    for s in c["train"]:
        leak = stems & cal_stems(s)
        assert not leak, f"calibration recordings among the training windows: {leak}"
    assert c["test"] not in set(tr.session.tolist())
    rec = {"cell": c["cell"], "head": head, "windows": int(len(tr)),
           "by_session": {s: int(np.sum(tr.session == s)) for s in c["train"]}}
    if c["norm"] == "per_room":
        rooms = np.array([room_of(str(s)) for s in tr.session])
        rec["room_stats"] = {}
        for r in sorted(set(rooms.tolist())):
            m = np.flatnonzero(rooms == r)
            rec["room_stats"][r] = []
            for li in range(3):
                (xm, xs), (rm, rs) = _stats(tr.X[m, li], tr.rssi[m, li])
                tr.X[m, li] = ((tr.X[m, li] - xm) / xs).astype(tr.X.dtype)
                tr.rssi[m, li] = ((tr.rssi[m, li] - rm) / rs).astype(tr.rssi.dtype)
                rec["room_stats"][r].append({"x": [xm, xs], "r": [rm, rs]})
    tag = c["heads_tag"]
    for kind, n, seed in HEADS[head][1]:
        ep = E_REG if kind == "pos" else E_POST
        train_pairing(c["train"], (c["test"],), False, kind, n, ep, seed, tr_windows=tr)
        for li in range(3):
            p = model_path(tag, kind, 2 if kind == "pos" else n, ep, seed, li)
            if c["norm"] == "per_room":
                # fold the TEST session's own normalisation into the saved standardisation, so the
                # unchanged inference computes ((X - m_t) / s_t - mu) / sd
                with open(J(c["base"], "teststats.json"), encoding="utf-8") as f:
                    ts = json.load(f)["links"][li]
                d = torch.load(p, map_location="cpu", weights_only=False)
                if not d.get("folded_test_stats"):
                    mu, sd = np.array(d["mu"], dtype=np.float64), np.array(d["sd"], dtype=np.float64)
                    for ch, key in ((0, "x"), (1, "r")):
                        if mu.shape[2] > ch:
                            m_t, s_t = ts[key]
                            mu[:, :, ch] = m_t + mu[:, :, ch] * s_t
                            sd[:, :, ch] = sd[:, :, ch] * s_t
                    d["mu"], d["sd"] = mu.astype(np.float32), sd.astype(np.float32)
                    d["folded_test_stats"] = ts
                    torch.save(d, p)
            dst = J(c["tree"](head), "models", os.path.basename(p))
            shutil.copy2(p, dst)
    rec["minutes"] = round((time.time() - t0) / 60.0, 2)
    with open(J(c["base"], f"train_{head}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    _say(f"{c['cell']} {head}: trained on {rec['windows']} windows in {rec['minutes']} min")
    return 0


def _rssi_unit(c) -> float:
    """dB to model units: 1 when pooled, else 1 / the median idle RSSI spread of the training recordings."""
    import numpy as np
    if c["norm"] != "per_recording":
        return 1.0
    with open(PRN_STATS, encoding="utf-8") as f:
        st = json.load(f)["recordings"]
    sds = [v["r"][li][1] for k, v in st.items() if k.split("|")[0] in c["train"] for li in range(3)]
    return float(1.0 / np.median(sds))


def do_train_d2(c, head: str) -> int:
    """D2: one head's networks through pd_train under the cell's options. The position head of the
    0.5 s head is copied from the base cell when the cell names one (the screens)."""
    import numpy as np
    from pipeline.constrained.artefacts import _save, model_path
    from pipeline.constrained.common import E_POST, E_REG
    from pipeline.constrained.dataset import walking_windows
    from pipeline.constrained.grid import cell_index
    from pipeline.constrained.nets import stack_link
    from pipeline.constrained.pd_train import fit_link
    t0 = time.time()
    d2, tag = D2[c["cell"]], c["heads_tag"]
    opts = {k: v for k, v in c["opts"].items() if k != "rrel"}
    opts["rssi_unit"] = _rssi_unit(c)
    tr = walking_windows(list(c["train"]))
    stems = set(tr.stem.tolist())
    for s in c["train"]:
        leak = stems & cal_stems(s)
        assert not leak, f"calibration recordings among the training windows: {leak}"
    assert c["test"] not in set(tr.session.tolist()) and not (set(c["train"]) & set(TEST2))
    # early stopping validates on the cell's test session, which must never be A3 or B2
    assert not (opts.get("early") and c["test"] in TEST2), f"{c['cell']}: early stopping on a test session"
    rec = {"cell": c["cell"], "head": head, "opts": c["opts"], "rssi_unit": opts["rssi_unit"],
           "windows": int(len(tr)), "by_session": {s: int(np.sum(tr.session == s)) for s in c["train"]},
           "links": {}}
    v, keep = None, None
    if opts.get("early"):
        v = walking_windows([c["test"]])
        keep = np.flatnonzero(~np.isin(np.asarray(v.stem), sorted(cal_stems(c["test"]))))
        rec["validation"] = {"session": c["test"], "windows": int(len(keep))}
    base_opts = opts
    for kind, n, seed in HEADS[head][1]:
        ep = E_REG if kind == "pos" else E_POST
        out_dim = 2 if kind == "pos" else n
        paths = [model_path(tag, kind, out_dim, ep, seed, li) for li in range(3)]
        # a final model without a validation session: each head and kind at its own fixed epoch count
        opts = dict(base_opts)
        if opts.get("epochs_by_head"):
            opts["epochs"] = int(opts["epochs_by_head"][f"{head}:{kind}"])
            opts.pop("early", None)
        opts.pop("epochs_by_head", None)
        if kind == "pos" and d2.get("pos_from"):
            src = cfg(d2["pos_from"])
            assert src["train"] == c["train"], (src["train"], c["train"])
            for p in paths:
                # the same training sessions; the file tag names the test session, so it is renamed
                shutil.copy2(J(src["tree"](head), "models", os.path.basename(p).replace(tag, src["heads_tag"], 1)),
                             J(c["tree"](head), "models", os.path.basename(p)))
            rec["pos_copied_from"] = d2["pos_from"]
            continue
        if d2.get("arch") and kind == "g" and not all(os.path.exists(p) for p in paths):
            # D4: ONE shared network over the three links, saved under each link's file name
            from pipeline.constrained.pd_arch import stack_all
            y = cell_index(tr.xy, n)
            X = stack_all(tr.X, tr.rssi)
            Xv = None if v is None else stack_all(v.X[keep], v.rssi[keep])
            yv = None if v is None else cell_index(v.xy[keep], n)
            model, mu, sd, r = fit_link(X, y, kind, out_dim, seed, opts, sessions=tr.session, Xv=Xv, yv=yv,
                                        arch=d2["arch"])
            snaps = r.pop("_snapshots", None)
            for li, p in enumerate(paths):
                if snaps and li == 0:
                    import torch
                    torch.save({"snapshots": snaps, "mu": mu, "sd": sd}, p + ".epochs.pt")
                _save(model, mu, sd, p, {"kind": kind, "out_dim": out_dim, "n_links": X.shape[1],
                                         "in_channels": X.shape[2], "epochs": ep, "seed": seed, "tag": tag,
                                         "link": li, "arch": d2["arch"], "pd_train": r})
            rec["links"][f"{kind}{out_dim}_s{seed}_shared"] = {k: r[k] for k in ("epochs_run", "best_epoch", "val_history")}
            _say(f"{c['cell']} {head} {d2['arch']}: {r['epochs_run']} epochs, best {r['best_epoch']}")
            del X, Xv
        elif not all(os.path.exists(p) for p in paths):
            y = tr.xy if kind == "pos" else cell_index(tr.xy, n)
            yv = None if v is None else (v.xy[keep] if kind == "pos" else cell_index(v.xy[keep], n))
            for li in range(3):
                X = stack_link(tr.X[:, [li]], tr.rssi[:, [li]])
                Xv = None if v is None else stack_link(v.X[keep][:, [li]], v.rssi[keep][:, [li]])
                model, mu, sd, r = fit_link(X, y, kind, out_dim, seed, opts, sessions=tr.session, Xv=Xv, yv=yv)
                snaps = r.pop("_snapshots", None)
                if snaps:
                    import torch
                    torch.save({"snapshots": snaps, "mu": mu, "sd": sd}, paths[li] + ".epochs.pt")
                _save(model, mu, sd, paths[li],
                      {"kind": kind, "out_dim": out_dim, "n_links": X.shape[1], "in_channels": X.shape[2],
                       "epochs": ep, "seed": seed, "tag": tag, "link": li, "pd_train": r})
                rec["links"][f"{kind}{out_dim}_s{seed}_link{li}"] = {k: r[k] for k in ("epochs_run", "best_epoch", "val_history")}
                _say(f"{c['cell']} {head} {kind}{out_dim} link {li}: {r['epochs_run']} epochs, best {r['best_epoch']}")
                del X, Xv
        for p in paths:
            shutil.copy2(p, J(c["tree"](head), "models", os.path.basename(p)))
    rec["minutes"] = round((time.time() - t0) / 60.0, 2)
    with open(J(c["base"], f"train_{head}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    _say(f"{c['cell']} {head}: trained on {rec['windows']} windows in {rec['minutes']} min")
    return 0


def do_earlyx_models(c) -> int:
    """EARLYX: the early cell's snapshot at the other rotations' mean best epoch, per link and kind."""
    import numpy as np
    import torch
    from pipeline.constrained.artefacts import _save, model_path
    from pipeline.constrained.common import E_POST, E_REG
    from pipeline.constrained.nets import LinkNet
    own, others = EARLYX[c["cell"]]
    oc = cfg(own)
    rec = {"from": own, "epochs_from": others, "links": {}}
    for h in c["heads"]:
        best = {}
        for o in others:
            with open(J(cfg(o)["base"], f"train_{h}.json"), encoding="utf-8") as f:
                for k, v in json.load(f)["links"].items():
                    best.setdefault(k, []).append(int(v["best_epoch"]))
        for kind, n, seed in HEADS[h][1]:
            ep = E_REG if kind == "pos" else E_POST
            out_dim = 2 if kind == "pos" else n
            for li in range(3):
                key = f"{kind}{out_dim}_s{seed}_link{li}"
                if key not in best:
                    continue                                    # a head copied, not trained (pos)
                k = int(round(float(np.mean(best[key]))))
                p_own = J(oc["tree"](h), "models", os.path.basename(model_path(c["heads_tag"], kind, out_dim, ep, seed, li)))
                # the snapshots sit beside the TRAINING copy of the weights (train_<h>/models)
                snap = torch.load(J(oc["base"], f"train_{h}", "models", os.path.basename(p_own) + ".epochs.pt"),
                                  map_location="cpu", weights_only=False)
                d = torch.load(p_own, map_location="cpu", weights_only=False)
                m = LinkNet(d["n_links"], out_dim, "position" if kind == "pos" else "posterior", d["in_channels"])
                m.load_state_dict(snap["snapshots"][k - 1])
                dst = J(c["tree"](h), "models", os.path.basename(p_own))
                _save(m, snap["mu"], snap["sd"], dst,
                      {"kind": kind, "out_dim": out_dim, "n_links": d["n_links"], "in_channels": d["in_channels"],
                       "epochs": ep, "seed": seed, "tag": c["heads_tag"], "link": li,
                       "pd_train": {"earlyx_epoch": k, "from": own, "other_best": best[key]}})
                rec["links"][f"{h}:{key}"] = {"epoch": k, "other_best": best[key]}
            if kind == "pos":
                src = cfg(D2[c["cell"]]["pos_from"])
                for li in range(3):
                    nm = os.path.basename(model_path(c["heads_tag"], kind, out_dim, ep, seed, li))
                    shutil.copy2(J(src["tree"](h), "models", nm), J(c["tree"](h), "models", nm))
    with open(J(c["base"], "earlyx.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    _say(f"{c['cell']}: models from {own} at the other rotations' epochs {rec['links']}")
    return 0


def do_plumb_models(c) -> int:
    """plumb_A3: the SHIPPED s0102_to_s03 weights (and s01_to_s03's, the shipped reader rule) copied in."""
    pa = lambda h: J(REPO_ROOT, "runs", f"artefacts_s0.5_pressalign_{h}")   # noqa: E731
    for h in HEADS:
        for tag in ([c["heads_tag"], c["reader_tag"]] if h == "half" else [c["heads_tag"]]):
            for f in glob.glob(J(pa(h), "models", f"{tag}_*")):
                dst = J(c["tree"](h), "models", os.path.basename(f))
                if not os.path.exists(dst):
                    shutil.copy2(f, dst)
    return 0


def do_shared_models(c, src_cell: str) -> int:
    """The source's trained weights, copied unchanged under this cell's tag; one training job serves
    both. Refuses unless the training sessions and normalisation match, and checks every copy. The
    source is another cell, or FROZEN_DC2 (the frozen A1+A2+A3 heads, pooled)."""
    import hashlib
    if src_cell == "FROZEN_DC2":
        assert c["train"] == ("01", "02", "03") and c["norm"] == "pooled", c["cell"]
        src_dir, src_tag = (lambda h: FROZEN_DC2[h]), FROZEN_TAG
    else:
        s = cfg(src_cell)
        assert s["train"] == c["train"] and s["norm"] == c["norm"], (s["train"], c["train"], s["norm"], c["norm"])
        src_dir, src_tag = s["tree"], s["heads_tag"]
    n = 0
    for h in c["heads"]:
        files = sorted(glob.glob(J(src_dir(h), "models", f"{src_tag}_*.pt")))
        assert files, f"{src_cell}/{h}: no trained weights to share"
        for f in files:
            dst = J(c["tree"](h), "models", os.path.basename(f).replace(src_tag, c["heads_tag"], 1))
            shutil.copy2(f, dst)
            same = hashlib.sha256(open(f, "rb").read()).hexdigest() == hashlib.sha256(open(dst, "rb").read()).hexdigest()
            assert same, f"copy differs: {dst}"
            n += 1
    with open(J(c["base"], "shared_models.json"), "w", encoding="utf-8") as fh:
        json.dump({"from": src_cell, "from_tag": src_tag, "to_tag": c["heads_tag"],
                   "files": n, "byte_identical": True}, fh, indent=1)
    _say(f"{c['cell']}: {n} weight files shared from {src_cell}, byte for byte")
    return 0


def do_readers(c) -> int:
    """D1: the pooled twin's start-of-walk reader files (its 0.5 s g25 and position heads, and its
    posteriors on the test session), copied in under the alias tag <twin tag>V0."""
    t = cfg(TWIN[c["cell"]])
    twin, alias = t["heads_tag"], c["reader_tag"]
    assert alias == twin + "V0", (alias, twin)
    half = c["tree"]("half")
    n = 0
    for f in glob.glob(J(t["tree"]("half"), "models", f"{twin}_g25_*.pt")) + \
            glob.glob(J(t["tree"]("half"), "models", f"{twin}_pos2_*.pt")):
        shutil.copy2(f, J(half, "models", os.path.basename(f).replace(twin, alias, 1)))
        n += 1
    pf = J(t["tree"]("half"), "posteriors", f"{twin}_g25_e24_s0_full.npz")
    shutil.copy2(pf, J(half, "posteriors", f"{alias}_g25_e24_s0_full.npz"))
    assert n == 6, f"{c['cell']}: {n} reader model files from {TWIN[c['cell']]}"
    _say(f"{c['cell']}: readers from its pooled twin {TWIN[c['cell']]} as {alias}")
    return 0


def install_prn() -> None:
    """D1, per-recording normalisation: wrap the feature and RSSI loaders so every recording is
    standardised per link and channel by its own idle radio before its first press. Installed at the
    start of a train or infer process, BEFORE dataset and artefacts import the loaders by name."""
    import numpy as np
    for m in ("pipeline.constrained.dataset", "pipeline.constrained.artefacts"):
        assert m not in sys.modules, f"{m} imported before the normalisation was installed"
    import pipeline.constrained.recordings as RC
    with open(PRN_STATS, encoding="utf-8") as f:
        stats = json.load(f)["recordings"]
    of, orr = RC.load_features, RC.load_rssi

    def load_features(session, stem, indices=None):
        X = np.array(of(session, stem, indices), dtype=np.float32)
        st = stats[f"{session}|{stem}"]
        for li in range(X.shape[1]):
            m, s = st["x"][li]
            X[:, li] = (X[:, li] - m) / s
        return X

    def load_rssi(session, stem, t0_epoch):
        R = np.array(orr(session, stem, t0_epoch), dtype=np.float32)
        st = stats[f"{session}|{stem}"]
        for li in range(R.shape[1]):
            m, s = st["r"][li]
            R[:, li] = (R[:, li] - m) / s
        return R
    RC.load_features, RC.load_rssi = load_features, load_rssi


def install_arch_infer() -> None:
    """D4: the unchanged inference (dc2_run.do_infer) reads a shared network's files. `_load` builds a
    SharedNet when the file says so; `posterior_of` routes it to pd_arch.infer_shared."""
    import pipeline.constrained.artefacts as A
    import pipeline.constrained.nets as N
    from pipeline.constrained.pd_arch import SharedNet, infer_shared
    ol, op = A._load, N.posterior_of

    def _load(path):
        import torch
        d = torch.load(path, map_location="cpu", weights_only=False)
        if not d.get("arch"):
            return ol(path)
        m = SharedNet(d["n_links"], d["out_dim"], d["arch"], d["in_channels"])
        m.load_state_dict(d["state_dict"])
        m.eval()
        return m, d["mu"], d["sd"]

    def posterior_of(models, X, rssi, batch=128):
        if isinstance(models[0][0], SharedNet):
            return infer_shared(models[0][0], models[0][1], models[0][2], X, rssi, batch)
        return op(models, X, rssi, batch)
    A._load, N.posterior_of = _load, posterior_of


def install_rrel() -> None:
    """D2, RSSI made relative: each recording's RSSI minus its own idle-before-first-press mean, per
    link (prn_stats); the CSI features are untouched. Installed as install_prn is."""
    import numpy as np
    for m in ("pipeline.constrained.dataset", "pipeline.constrained.artefacts"):
        assert m not in sys.modules, f"{m} imported before the relative RSSI was installed"
    import pipeline.constrained.recordings as RC
    with open(PRN_STATS, encoding="utf-8") as f:
        stats = json.load(f)["recordings"]
    orr = RC.load_rssi

    def load_rssi(session, stem, t0_epoch):
        R = np.array(orr(session, stem, t0_epoch), dtype=np.float32)
        st = stats[f"{session}|{stem}"]
        for li in range(R.shape[1]):
            R[:, li] = R[:, li] - st["r"][li][0]
        return R
    RC.load_rssi = load_rssi


def do_prn_stats() -> int:
    """Every recording's idle-before-first-press statistics, per link and channel, from UNNORMALISED
    features: u1_adapt's calibration_indices on the 0.5 s windows. All five sessions, calibration
    recordings included (a Room B test session decodes them for configuration B)."""
    view = J(RES, "prn_view")
    if os.environ.get("TDR_ART_DIR") != J(view, "shared05"):
        for s in SESS5:
            _link_session(raw_dir(s), J(view, "data", VIEW_ROOM, f"session_{s}"), set())
            w05 = (J(A_WIN05, f"session_{s}") if room_of(s) == "A"
                   else J(DC2_BY, s, "windows", "room_B", f"session_{s}"))
            _link_session(w05, J(view, "win05", VIEW_ROOM, f"session_{s}"), set())
            _link_cache(A_SH05 if room_of(s) == "A" else J(DC2_BY, s, "art_shared"), J(view, "shared05"), s, set())
        e = {k: v for k, v in os.environ.items() if not k.startswith("TDR_")}
        e.update({"TDR_ROOM": VIEW_ROOM, "TDR_DATA_ROOT": J(view, "data"), "TDR_WINDOWS_ROOT": J(view, "win05"),
                  "TDR_ART_DIR": J(view, "shared05"), "OMP_NUM_THREADS": "1"})
        return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_cells", "prn_stats"],
                               cwd=REPO_ROOT, env=e)
    import numpy as np
    import pipeline.constrained.common as C                                 # binds the view's roots
    import pipeline.constrained.recordings as RC
    from pipeline.constrained import lattice
    assert os.path.abspath(C.ART_DIR) == os.path.abspath(J(view, "shared05")), C.ART_DIR
    os.environ["TDR_ART_DIR"] = lattice.half_art_dir()      # the guards only, as dc2_run._bind does
    from pipeline.constrained.u1_adapt import calibration_indices
    from pipeline.constrained.p1_runup import first_presses
    load_features, load_meta, load_rssi, recordings = RC.load_features, RC.load_meta, RC.load_rssi, RC.recordings
    out, low = {}, []
    for s, stem in recordings():
        rec = load_meta(s, stem)
        idx = np.asarray(calibration_indices(rec, first_presses(s, stem)), int)
        if len(idx) < 10:
            low.append((s, stem, int(len(idx))))
        X, R = load_features(s, stem, idx), load_rssi(s, stem, rec.t0_epoch)[idx]
        out[f"{s}|{stem}"] = {"n": int(len(idx)),
                              "x": [[float(X[:, li].mean(dtype=np.float64)), float(X[:, li].std(dtype=np.float64)) + 1e-8] for li in range(3)],
                              "r": [[float(R[:, li].mean(dtype=np.float64)), float(R[:, li].std(dtype=np.float64)) + 1e-8] for li in range(3)]}
        _say(f"prn stats {s}/{stem}: {len(idx)} idle windows")
    assert not low, f"recordings with fewer than 10 idle windows before the first press: {low}"
    with open(PRN_STATS, "w", encoding="utf-8") as f:
        json.dump({"what": "per-recording idle-before-first-press statistics, D1", "recordings": out}, f, indent=1)
    return 0


# ------------------------------------------------------------------------------ infer, decode, lock

def do_infer(c, head: str) -> int:
    from pipeline.constrained import dc2_run as R
    return R.do_infer(c, head)


def do_decode(c) -> int:
    from pipeline.constrained import dc2b
    dc2b.install()                                   # split_passes per recording
    import pipeline.constrained.dc2_pipeline as P
    from pipeline.constrained import dc2_run as R
    orig = P.calibration_numbers

    def calibration_numbers(room, sessions, splits):
        # a Room A test session has no calibration walk: no constants, so configuration B = A
        have = [s for s in sessions if any(v["calibration"] for k, v in splits.items() if k.startswith(f"{s}|"))]
        return orig(room, have, splits)
    P.calibration_numbers = calibration_numbers
    return R.do_decode(c)


def do_lock(c) -> int:
    from pipeline.constrained import dc2b
    dc2b.install()                                   # split_passes per recording, as in the decode
    from pipeline.constrained import dc2_run as R
    import pipeline.constrained.dc2_scorerlock as S
    R.cfg_for = lambda room, stand_in: c
    return S._inner(VIEW_ROOM, False)


# ----------------------------------------------------------------------------------------- driver

def run_cell(cell: str, phase: str = "all") -> int:
    """phase 'gpu': view, models or training, inference; 'cpu': readers, decode, lock; 'all': both.
    The cpu phase keeps its own status file so it can run beside the next cell's gpu phase."""
    c = cfg(cell)
    os.makedirs(c["base"], exist_ok=True)
    log = J(RES, "logs", f"cell_{cell}.log")
    t0 = time.time()
    status = J(c["base"], "status.json" if phase != "cpu" else "status_cpu.json")
    done = json.load(open(status)) if os.path.exists(status) else {}
    if phase == "cpu" and os.path.exists(J(c["base"], "status.json")):
        prior = json.load(open(J(c["base"], "status.json")))
        done.update({k: v for k, v in prior.items() if k in ("readers", "decode", "lock")})
        missing = [f"infer_{h}" for h in c["heads"] if not prior.get(f"infer_{h}")]
        assert not missing, f"{cell}: the cpu phase needs {missing} first"

    def step(name, fn):
        if done.get(name):
            return 0
        t = time.time()
        code = fn()
        if code:
            raise SystemExit(f"{cell}: step {name} failed with exit {code}; see {log}")
        done[name] = {"minutes": round((time.time() - t) / 60.0, 2), "at": time.strftime("%H:%M:%S")}
        with open(status, "w", encoding="utf-8") as f:
            json.dump(done, f, indent=1)
        _say(f"{cell}: {name} done in {done[name]['minutes']} min")
        return 0

    if phase == "cpu":
        return _cpu_phase(cell, c, step, log, t0)
    step("view", lambda: do_view(c))
    if cell == "plumb_A3":
        step("models", lambda: do_plumb_models(c))
    elif cell in SHARED_MODELS:
        step("models", lambda: do_shared_models(c, SHARED_MODELS[cell]))
    elif cell in EARLYX:
        step("models", lambda: do_earlyx_models(c))
    else:
        if c["norm"] == "per_room":
            step("teststats", lambda: _sub(cell, "teststats", "half", "infer", log))
        for h in c["heads"]:                              # ONE training job at a time
            step(f"train_{h}", lambda h=h: _sub(cell, "train", h, "train", log))
    for h in c["heads"]:
        step(f"infer_{h}", lambda h=h: _sub(cell, "infer", h, "infer", log))
    if phase == "gpu":
        _say(f"{cell}: gpu phase complete in {(time.time() - t0) / 60.0:.1f} min")
        return 0
    if phase == "prep":
        # TEST cells (midpoint, final): networks, inference and readers only. The shipped default
        # decode is never run on A3 or B2; the one sanctioned decode is pd_decode's chosen variant.
        if cell in TWIN:
            step("readers", lambda: do_readers(cfg(cell, "readers")))
        _say(f"{cell}: prep complete in {(time.time() - t0) / 60.0:.1f} min")
        return 0
    return _cpu_phase(cell, c, step, log, t0)


def _cpu_phase(cell, c, step, log, t0) -> int:
    if cell in TWIN:
        step("readers", lambda: do_readers(cfg(cell, "readers")))
    step("decode", lambda: _sub(cell, "decode", None, "decode", log))
    step("lock", lambda: _sub(cell, "lock", None, "decode", log))
    _say(f"{cell}: complete in {(time.time() - t0) / 60.0:.1f} min")
    return 0


def pipelined(cells, max_cpu: int = 2) -> int:
    """ONE training job at a time, as before; each cell's decode and lock run in their own process
    beside the next cell's training (at most max_cpu at once). Any failure stops the queue."""
    procs, failed = [], []

    def reap(block_until: int):
        while True:
            for cell, p in list(procs):
                code = p.poll()
                if code is not None:
                    procs.remove((cell, p))
                    if code:
                        failed.append(cell)
                        _say(f"FAILED {cell}: cpu phase exit {code}; the queue continues")
            if len(procs) <= block_until:
                return
            time.sleep(5)
    for cell in cells:
        # a cell whose inputs failed (an earlyx cell without its early cells) fails in turn, logged
        try:
            run_cell(cell, "gpu")
        except (SystemExit, Exception) as e:          # one bad cell must not stop the night
            failed.append(cell)
            _say(f"FAILED {cell}: gpu phase: {e}; the queue continues")
            continue
        reap(max_cpu - 1)
        procs.append((cell, subprocess.Popen([sys.executable, "-m", "pipeline.constrained.pd_cells", "run",
                                              "--cell", cell, "--phase", "cpu"], cwd=REPO_ROOT)))
    reap(0)
    _say(f"pipelined queue done: {len(cells)} cells, {len(failed)} failed {failed}")
    return 1 if failed else 0


def do_b10() -> int:
    """Room B's 1 s features and RSSI, once, for every non-calibration recording."""
    if os.environ.get("TDR_ART_DIR") != B_SH10:
        view = J(RES, "b10_view")
        for s in ("B1", "B2"):
            _link_session(J(B_WIN10, f"session_{s}"), J(view, VIEW_ROOM, f"session_{s}"), cal_stems(s))
        e = {k: v for k, v in os.environ.items() if not k.startswith("TDR_")}
        e.update({"TDR_ROOM": VIEW_ROOM, "TDR_DATA_ROOT": J(REPO_ROOT, "data"), "TDR_WINDOWS_ROOT": view,
                  "TDR_ART_DIR": B_SH10, "OMP_NUM_THREADS": "1"})
        return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_cells", "b10"],
                               cwd=REPO_ROOT, env=e)
    from pipeline.constrained.recordings import build_feature_cache, load_meta, load_rssi, recordings
    for s, stem in recordings():
        build_feature_cache(s, stem)
        load_rssi(s, stem, load_meta(s, stem).t0_epoch)
        _say(f"b10 features {s}/{stem}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "queue", "pqueue", "b10", "prn_stats", "teststats", "train", "infer",
                                    "decode", "lock"])
    ap.add_argument("--phase", default="all", choices=["all", "gpu", "cpu", "prep"])
    ap.add_argument("--cell")
    ap.add_argument("--cells", nargs="*")
    ap.add_argument("--head", choices=sorted(HEADS))
    a = ap.parse_args(argv)
    if a.cmd == "b10":
        return do_b10()
    if a.cmd == "prn_stats":
        return do_prn_stats()
    if a.cmd == "queue":
        for cell in (a.cells or ORDER):
            run_cell(cell)
            if cell == SPEED_RULE_CELL:
                with open(J(RES, "cells", cell, "status.json"), encoding="utf-8") as f:
                    st = json.load(f)
                mins = sum(v["minutes"] for k, v in st.items() if k.startswith("train_"))
                rule = {"cell": cell, "training_minutes": round(mins, 2), "limit": SPEED_LIMIT_MIN,
                        "SWITCH_TO_SINGLE_HEAD": bool(mins > SPEED_LIMIT_MIN)}
                with open(J(RES, "speed_rule.json"), "w", encoding="utf-8") as f:
                    json.dump(rule, f, indent=1)
                _say(f"speed rule: {cell} trained its six networks in {mins:.1f} min "
                     f"(limit {SPEED_LIMIT_MIN}): {'SWITCH' if rule['SWITCH_TO_SINGLE_HEAD'] else 'five-head pool stays'}")
                if rule["SWITCH_TO_SINGLE_HEAD"]:
                    raise SystemExit("SPEED RULE fired: stop, and re-plan every cell as single-head")
        return 0
    if a.cmd == "pqueue":
        return pipelined(a.cells)
    if a.cmd == "run":
        return run_cell(a.cell, a.phase)
    c = cfg(a.cell, a.cmd)
    if c["norm"] == "per_recording" and a.cmd in ("train", "infer"):
        install_prn()
    if c["opts"].get("rrel") and a.cmd in ("train", "infer"):
        install_rrel()
    if a.cell in D2 and D2[a.cell].get("arch") and a.cmd == "infer":
        install_arch_infer()
    train = do_train_d2 if a.cell in D2 else do_train
    return {"teststats": lambda: do_teststats(c), "train": lambda: train(c, a.head),
            "infer": lambda: do_infer(c, a.head), "decode": lambda: do_decode(c),
            "lock": lambda: do_lock(c)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
