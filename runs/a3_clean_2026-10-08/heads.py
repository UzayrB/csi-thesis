"""The held-out display heads for the dot side (PREREG_DOT.md section 2; POA_DOT.md E1).

    python3 runs/a3_clean_2026-10-08/heads.py dry   --rot A2        # build the training windows, count them, no training
    python3 runs/a3_clean_2026-10-08/heads.py train --rot A2 --device gpu    # train (ONLY after QUIET and Uzayr's go)
    python3 runs/a3_clean_2026-10-08/heads.py check-zs                       # the B1 rotation's reuse of pd_dispend_zs

One head per rotation, trained only on that rotation's training sessions, with the shipped DISP_END recipe: the calls of
`pd_dispend.train_inner` (end_labelled_windows with include_edge False, stack_all, cell_index at 25 cells,
fit_link("g", 25, seed 0, {"aug": True, "rssi_unit": 1.0}, arch="fuse"), relative RSSI installed first). The rotation
A1+A2 -> B1 reuses `pd_dispend_zs` (A1+A2), which makes the same calls. Writes only under heads/ in this folder.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ROOT = J(HERE, "heads")
N_CELLS, SEED = 25, 0
OPTS = {"aug": True, "rssi_unit": 1.0}
#: rotation -> (cell whose environment the head trains in, its training sessions, tag)
ROTS = {"A2": ("d4c_fuse_01B1_to_02", ("01", "B1"), "s01B1_dispend_rot"),
        "A1": ("d4c_fuse_02B1_to_01", ("02", "B1"), "s02B1_dispend_rot")}
#: the B1 rotation's head: the zero-shot model's, trained on A1+A2 with the same recipe
ZS = {"tag": "s0102_dispend_zeroshot", "train": ["01", "02"]}


def model_file(rot: str) -> str:
    tag = ROTS[rot][2]
    return J(ROOT, tag, "models", f"{tag}_g{N_CELLS}_s{SEED}_fuse.pt")


def train_json(rot: str) -> str:
    return J(ROOT, ROTS[rot][2], "train.json")


def training_windows(rot: str, device: str = "cpu"):
    """(PC, c, windows, coverage) for the rotation's head, with every assertion pd_dispend makes."""
    cell, train, _tag = ROTS[rot]
    sys.path.insert(0, REPO)
    from pipeline.constrained.pd_dispend import _setup
    PC, c = _setup(cell, device)
    assert tuple(c["train"]) == train, f"{cell}: training sessions {c['train']} are not {train}"
    import numpy as np
    from pipeline.constrained.s2a_dispend import end_labelled_windows
    tr, cov = end_labelled_windows(tuple(c["train"]), with_features=True, include_edge=False)
    sess = set(np.asarray(tr.session).astype(str).tolist())
    assert sess <= set(train), f"sessions outside {train} in the display head's windows: {sess}"
    assert not sess & {"03", "B2"}, "A3 or B2 in a display head's windows"
    for s in train:
        leak = set(np.asarray(tr.stem).astype(str).tolist()) & PC.cal_stems(s)
        assert not leak, f"calibration recordings among the display head's windows: {leak}"
    return PC, c, tr, cov


def dry_inner(rot: str) -> int:
    import numpy as np
    _PC, c, tr, _cov = training_windows(rot, "cpu")
    by = {s: int(np.sum(np.asarray(tr.session).astype(str) == s)) for s in c["train"]}
    print(json.dumps({"rot": rot, "cell": ROTS[rot][0], "train": list(c["train"]), "windows": int(len(tr)),
                      "by_session": by, "X_shape": list(np.shape(tr.X)), "model_file": os.path.relpath(model_file(rot), REPO),
                      "exists": os.path.exists(model_file(rot))}))
    return 0


def train_inner(rot: str, device: str) -> int:
    t0 = time.time()
    out = model_file(rot)
    if os.path.exists(out):
        raise SystemExit(f"REFUSING to overwrite {out}")
    _PC, c, tr, cov = training_windows(rot, device)
    import numpy as np
    import torch
    from pipeline.constrained.artefacts import _save
    from pipeline.constrained.grid import cell_index
    from pipeline.constrained.pd_arch import stack_all
    from pipeline.constrained.pd_train import fit_link
    X = stack_all(tr.X, tr.rssi)
    y = cell_index(tr.xy, N_CELLS)
    model, mu, sd, r = fit_link(X, y, "g", N_CELLS, SEED, dict(OPTS), sessions=tr.session, arch="fuse")
    r.pop("_snapshots", None)
    tag = ROTS[rot][2]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _save(model, mu, sd, out, {"kind": "g", "out_dim": N_CELLS, "n_links": X.shape[1], "in_channels": X.shape[2],
                               "epochs": r.get("epochs_run"), "seed": SEED, "tag": tag, "link": 0, "arch": "fuse",
                               "pd_train": r, "labels": f"END of the window, not its centre. DISPLAY ONLY. "
                                                        f"Held out for rotation {rot}: {'+'.join(c['train'])} only."})
    rec = {"tag": tag, "rotation": rot, "cell_env": ROTS[rot][0], "train": list(c["train"]), "windows": int(len(tr)),
           "by_session": {s: int(np.sum(np.asarray(tr.session).astype(str) == s)) for s in c["train"]},
           "coverage": cov, "opts": OPTS, "arch": "fuse", "epochs_run": r.get("epochs_run"),
           "device": str(torch.device("mps") if (device != "cpu" and torch.backends.mps.is_available()) else "cpu"),
           "minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "marginal_xy": [list(map(float, q)) for q in np.asarray(tr.xy)]}
    with open(train_json(rot), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    print(f"[{time.strftime('%H:%M:%S')}] held-out DISP_END {rot}: {len(tr)} windows {rec['by_session']}, "
          f"{rec['epochs_run']} epochs, {rec['minutes']} min on {rec['device']}", flush=True)
    return 0


def posterior_file(rot: str) -> str:
    """The rotation's held-out head on its own TEST session (every window), for the offline gates (gates.py)."""
    if rot == "B1":
        return J(ROOT, ZS["tag"], "posteriors", f"{ZS['tag']}_on_B1_full.npz")
    tag = ROTS[rot][2]
    return J(ROOT, tag, "posteriors", f"{tag}_on_{ROT_TEST[rot]}_full.npz")


ROT_TEST = {"B1": "B1", "A2": "02", "A1": "01"}
ROT_CELL = {"B1": "d4c_fuse_0102_to_B1", "A2": ROTS["A2"][0], "A1": ROTS["A1"][0]}


def head_file(rot: str) -> str:
    if rot == "B1":
        sys.path.insert(0, REPO)
        from pipeline.constrained.pd_dispend_zs import model_file as zs_model_file
        return zs_model_file()
    return model_file(rot)


def infer_inner(rot: str, device: str) -> int:
    """pd_dispend.infer_inner with the rotation's held-out head, on the rotation's test session."""
    out = posterior_file(rot)
    if os.path.exists(out):
        raise SystemExit(f"REFUSING to overwrite {out}")
    sys.path.insert(0, REPO)
    from pipeline.constrained.pd_dispend import _setup
    PC, c = _setup(ROT_CELL[rot], device)
    assert c["test"] == ROT_TEST[rot], (c["test"], rot)
    PC.install_arch_infer()
    import numpy as np
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.recordings import session_recordings
    m = _load(head_file(rot))
    models = [m, m, m]                  # posterior_of reads the shared network from link 0
    flat, stems = {}, []
    for _s, stem in session_recordings(c["test"]):
        prob, per_link, rec = infer_recording(models, c["test"], stem, "g")
        block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32), "t0": rec.t0,
                 "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"), "pass_id": rec.pass_id,
                 "path_name": rec.path_name.astype("U10"), "xy": np.asarray(rec.xy, float)}
        for k, v in block.items():
            flat[f"{stem}::{k}"] = v
        stems.append(stem)
    flat["__stems__"] = np.array(sorted(stems), dtype="U64")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out + ".tmp.npz", **flat)
    os.replace(out + ".tmp.npz", out)
    print(f"[{time.strftime('%H:%M:%S')}] held-out display head {rot} on {c['test']}: {len(stems)} recordings -> "
          f"{os.path.relpath(out, REPO)}", flush=True)
    return 0


def _training_calls(path: str, func: str) -> list:
    """The source of every call in `func` that shapes the head: the data, the labels, the fit and its options."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func)
    keep = ("end_labelled_windows", "stack_all", "cell_index", "fit_link", "install_rrel")
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in keep:
                out.append(ast.unparse(node))
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "opts" for t in node.targets):
            out.append("opts = " + ast.unparse(node.value))
    return sorted(out)


def check_zs() -> dict:
    """The B1 rotation's head: pd_dispend_zs makes pd_dispend's training calls, with the same options, and its record
    says A1+A2, 24 epochs, the fuse architecture."""
    pc = J(REPO, "pipeline", "constrained")
    # relative RSSI is installed before the data modules in both: pd_dispend in _setup, pd_dispend_zs in train_inner
    a = _training_calls(J(pc, "pd_dispend.py"), "train_inner")
    a_rrel = any("install_rrel" in x for x in _training_calls(J(pc, "pd_dispend.py"), "_setup"))
    b_all = _training_calls(J(pc, "pd_dispend_zs.py"), "train_inner")
    b = [x for x in b_all if "install_rrel" not in x]
    b_rrel = len(b) < len(b_all)
    rec = json.load(open(J(REPO, "runs", "dc2_results", "dispend_zeroshot", "train.json"), encoding="utf-8"))
    mine = sorted(_training_calls(os.path.abspath(__file__), "train_inner")
                  + _training_calls(os.path.abspath(__file__), "training_windows"))
    res = {"pd_dispend_calls": a, "pd_dispend_zs_calls": b, "identical": a == b and a_rrel and b_rrel,
           "relative_rssi_installed_first": {"pd_dispend": a_rrel, "pd_dispend_zs": b_rrel},
           "this_wrapper_calls": mine,
           "record": {k: rec[k] for k in ("tag", "train", "opts", "arch", "epochs_run", "windows", "by_session")},
           "record_ok": (rec["train"] == ZS["train"] and rec["opts"] == OPTS and rec["arch"] == "fuse"
                         and rec["epochs_run"] == 24 and rec["tag"] == ZS["tag"])}
    res["OK"] = bool(res["identical"] and res["record_ok"])
    return res


def outer(cmd: str, rot: str, device: str) -> int:
    sys.path.insert(0, REPO)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(ROT_CELL[rot] if cmd == "infer" else ROTS[rot][0], "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO, OMP_NUM_THREADS="1")
    if device == "gpu":
        env.update(PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), cmd, "--inner", "--rot", rot,
                            "--device", device], cwd=REPO, env=env)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry", "train", "infer", "check-zs"])
    ap.add_argument("--rot", choices=sorted(set(ROTS) | {"B1"}))
    ap.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check-zs":
        r = check_zs()
        print(json.dumps(r, indent=1))
        return 0 if r["OK"] else 1
    if a.inner:
        if a.cmd == "infer":
            return infer_inner(a.rot, a.device)
        return dry_inner(a.rot) if a.cmd == "dry" else train_inner(a.rot, a.device)
    return outer(a.cmd, a.rot, a.device)


if __name__ == "__main__":
    sys.exit(main())
