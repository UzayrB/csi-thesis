"""PLAN.md steps 2 and 3: build the new cells f05_A3, f05_B2 (deployed) and z05_B2 (zero-shot) beside the old ones.

    prep  CELL   view, models shared from the old cell (byte-checked), the start readers from the twin, the Room A
                 reader-row files copied from the old cell, the cross-fitted B1 rows (pd_clean crossfit)
    plumb CELL   the OLD heads' test posteriors copied in, then pd_clean decode under prefix PL; its rows must equal
                 the old cell's FC record exactly (committed line, display lock, scorer lock), or this exits 1
    swap  CELL   the four new slot networks (train/) replace the old ones in the new cell, byte-checked; the old
                 heads' posteriors move to art_*/posteriors_plumb/ (nothing is deleted)
    decode CELL  pd_clean decode under prefix FC: the new model's record

Every write is inside runs/dc2_results/cells/<new cell>/ or this folder. The old cells are read only.
"""

from __future__ import annotations

import filecmp
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
OLD = {"f05_A3": "fin_A3", "f05_B2": "fin_B2", "z05_B2": "zsf_B2"}
TRAIN = {"f05_A3": "fin_A3", "f05_B2": "fin_A3", "z05_B2": "zsf_B2"}   # which train/ folder holds the new nets
VARIANT = "relgateU+abstain+a2w0.25"
SLOTS = {"fh1s": (25, 0), "g1s1": (25, 1), "g1s2": (25, 2), "g100": (100, 0)}   # slot: (cells, file seed)
with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as _f:
    _P = json.load(_f)
ENV = {"PD_PACE_MEAN": repr(_P["v_mean"]), "PD_PACE_SD": repr(_P["v_sd"]), "PD_CLEAN_NOCACHE": "1",
       "OMP_NUM_THREADS": "1", "PYTHONPATH": REPO}


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def prep(cell: str) -> None:
    from pipeline.constrained import pd_cells as P
    c = P.cfg(cell)
    old = P.cfg(OLD[cell])
    os.makedirs(c["base"], exist_ok=True)
    # the 1 s feature caches were deleted (6 Oct cleanup) and these cells never train: do_view only links the 1 s
    # training folders to them, so they are made empty here and stay unused
    for sub in ("features", "rssi_full"):
        os.makedirs(J(c["shared10"], sub), exist_ok=True)
    P.do_view(c)
    P.do_shared_models(c, P.SHARED_MODELS[cell])
    P.do_readers(P.cfg(cell, "readers"))
    # the Room A reader-row networks and their posteriors (tags trained on one Room A session), byte for byte
    n = 0
    for sub in ("models", "posteriors"):
        for f in sorted(glob.glob(J(old["tree"]("half"), sub, "s0?_to_s0?_*"))):
            dst = J(c["tree"]("half"), sub, os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
                n += 1
            assert sha(f) == sha(dst), dst
    print(f"{cell}: {n} Room A reader-row files copied", flush=True)
    code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_clean", "crossfit", "--cell", cell],
                           cwd=REPO, env=dict(os.environ, **ENV))
    assert code == 0, f"{cell}: crossfit exit {code}"


def rows(d3: str, session: str) -> dict:
    dec = json.load(open(J(d3, "decode.json")))["sessions"][session]["rows"]["A"]
    sl = {r["key"]: r for r in json.load(open(J(d3, "scorerlock.json")))["sessions"][session]["rows"]["A"]}
    return {r["key"]: (r["final_line"], sl[r["key"]]["display_lock"], sl[r["key"]].get("scorer_lock"))
            for r in dec}


def plumb(cell: str) -> int:
    from pipeline.constrained import pd_cells as P
    c, old = P.cfg(cell), P.cfg(OLD[cell])
    for h in c["heads"]:
        for f in glob.glob(J(old["tree"](h), "posteriors", f"{c['heads_tag']}_*_full.npz")):
            dst = J(c["tree"](h), "posteriors", os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
    stage = J(HERE, "stage", "PL", cell)
    code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_clean", "decode", "--cell", cell,
                            "--variants", VARIANT], cwd=REPO,
                           env=dict(os.environ, **ENV, PD_CLEAN_PREFIX="PL", PD_CLEAN_STAGE=stage))
    if code:
        print(f"{cell}: plumbing decode exit {code}", flush=True)
        return 1
    a = rows(J(c["base"], "d3", f"PL.{VARIANT}"), c["test"])
    b = rows(J(old["base"], "d3", f"FC.{VARIANT}"), c["test"])
    diff = [k for k in b if a.get(k) != b[k]]
    res = {"cell": cell, "against": f"{OLD[cell]}/d3/FC.{VARIANT}", "n": len(b), "n_new": len(a),
           "differ": diff[:20], "EXACT": not diff and len(a) == len(b)}
    with open(J(HERE, "logs", f"plumb_{cell}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res), flush=True)
    return 0 if res["EXACT"] else 1


def swap(cell: str) -> None:
    from pipeline.constrained import pd_cells as P
    c = P.cfg(cell)
    src_tag = P.cfg(TRAIN[cell])["heads_tag"]
    done = {}
    for slot, (cells, fs) in SLOTS.items():
        for li in range(3):
            src = J(HERE, "train", TRAIN[cell], slot, "art", "models", f"{src_tag}_g{cells}_e24_s{fs}_link{li}.pt")
            dst = J(c["tree"](slot), "models", f"{c['heads_tag']}_g{cells}_e24_s{fs}_link{li}.pt")
            assert os.path.exists(src) and os.path.exists(dst), (src, dst)
            shutil.copy2(src, dst)
            assert sha(src) == sha(dst), dst
            done[os.path.relpath(dst, REPO)] = {"from": os.path.relpath(src, REPO), "sha256": sha(dst)}
        post = J(c["tree"](slot), "posteriors")
        keep = J(c["tree"](slot), "posteriors_plumb")
        os.makedirs(keep, exist_ok=True)
        for f in glob.glob(J(post, f"{c['heads_tag']}_*_full.npz")):
            shutil.move(f, J(keep, os.path.basename(f)))
    with open(J(c["base"], "SWAPPED_0p5.json"), "w", encoding="utf-8") as f:
        json.dump({"cell": cell, "slots": list(SLOTS), "files": done,
                   "note": "half is unchanged; the fh1s slot's file s0 holds the network trained with seed 3"}, f, indent=1)
    print(f"{cell}: {len(done)} slot files swapped", flush=True)


def decode(cell: str) -> int:
    stage = J(HERE, "stage", "FC", cell)
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_clean", "decode", "--cell", cell,
                            "--variants", VARIANT], cwd=REPO,
                           env=dict(os.environ, **ENV, PD_CLEAN_PREFIX="FC", PD_CLEAN_STAGE=stage))


if __name__ == "__main__":
    cmd, cell = sys.argv[1], sys.argv[2]
    assert cell in OLD, cell
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    r = {"prep": prep, "plumb": plumb, "swap": swap, "decode": decode}[cmd](cell)
    sys.exit(r or 0)
