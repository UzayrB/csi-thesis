"""Decode one arm and seed set on one rotation cell and score it (PLAN.md, Evaluation).

The dwell ablation's evaluator, pointed at the rotation cells. The decode is `pd_repro_trace`'s own (`build`, then
its `readers`, `infer` and `decode` steps), with the rotation records' settings: prefix CR and the modules' default
pace (1.298, 0.123), which is what `pace: None` meant when the records were made. The five pool slots of the scratch
tree are filled with the arm's networks (ARMS); every other network there (the start-of-walk readers and the reader
rows' networks) stays as recorded. With --arm MIX --k 0 nothing is replaced, which must reproduce the cell's
recorded decode exactly (the plumbing check). Writes <rot folder>/eval_<arm>_k<k>.json and deletes the scratch tree.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # runs/ablations/<this folder>
VARIANT = "relgateU+abstain+a2w0.25"
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")
ENV = {"PD_CLEAN_PREFIX": "CR", "PD_PACE_MEAN": "1.298", "PD_PACE_SD": "0.123", "PD_REPRO_VARIANT": VARIANT}
ROTATIONS = {"B1": "d4c_fuse_0102_to_B1", "A2": "d4c_fuse_01B1_to_02", "A1": "d4c_fuse_02B1_to_01"}
#: network name -> (training stride, cells, base seed); seed set k adds 100 x k
NETS = {"p05_s0": ("05", 25, 0), "p05_s1": ("05", 25, 1), "p05_s2": ("05", 25, 2), "p05_s3": ("05", 25, 3),
        "p10_s0": ("10", 25, 0), "p10_s1": ("10", 25, 1), "p10_s2": ("10", 25, 2), "p10_s3": ("10", 25, 3),
        "g100_05": ("05", 100, 0), "g100_10": ("10", 100, 0)}
#: the shipped pool's slot (its tree name and file seed) -> the network each arm puts there
SLOTS = {"half": ("g25", 0), "fh1s": ("g25", 0), "g1s1": ("g25", 1), "g1s2": ("g25", 2), "g100": ("g100", 0)}
ARMS = {"MIX": {"half": "p05_s0", "fh1s": "p10_s0", "g1s1": "p10_s1", "g1s2": "p10_s2", "g100": "g100_10"},
        "ALL05": {"half": "p05_s0", "fh1s": "p05_s3", "g1s1": "p05_s1", "g1s2": "p05_s2", "g100": "g100_05"},
        "ALL1": {"half": "p10_s3", "fh1s": "p10_s0", "g1s1": "p10_s1", "g1s2": "p10_s2", "g100": "g100_10"}}
#: seed set 0 of these networks IS the rotation cell's own trained head (same recipe, same seed; training is
#: deterministic on this machine, as the dwell ablation's W0 showed byte for byte)
RECORDED = {"p05_s0": "half", "p10_s0": "fh1s", "p10_s1": "g1s1", "p10_s2": "g1s2", "g100_10": "g100"}


def net_dir(rot: str, net: str, k: int) -> str:
    return J(HERE, "runs", rot, f"{net}_k{k}")


def net_files(rot: str, net: str, k: int) -> list:
    """The network's three link files, in link order."""
    sys.path.insert(0, REPO)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(ROTATIONS[rot], "decode")
    _stride, n, seed = NETS[net]
    if k == 0 and net in RECORDED:
        d = J(c["tree"](RECORDED[net]), "models")
    else:
        d = J(net_dir(rot, net, k), "art", "models")
    out = [J(d, f"{c['heads_tag']}_g{n}_e24_s{seed + 100 * k}_link{li}.pt") for li in range(3)]
    assert all(os.path.exists(p) for p in out), out
    return out


def fill_slots(scratch_cell: str, rot: str, arm: str, k: int, heads_tag: str) -> dict:
    done = {}
    for slot, (g, s) in SLOTS.items():
        net = ARMS[arm][slot]
        for li, src in enumerate(net_files(rot, net, k)):
            dst = J(scratch_cell, f"art_{slot}", "models", f"{heads_tag}_{g}_e24_s{s}_link{li}.pt")
            assert os.path.exists(dst), dst
            shutil.copy2(src, dst)
        done[slot] = net
    return done


def reader_files(cell: str) -> list:
    """The posterior files the readers step re-derives: the test-side V0 reader and every changed (cross-fitted) row."""
    import pipeline.constrained.pd_repro_trace as T
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    tags = [c["reader_tag"]] + [p["clean"] for p in T._plan(cell, VARIANT).values() if p["changed"]]
    return [f"{t}_g25_e24_s0_full.npz" for t in tags]


def readers_cache(rot: str) -> str:
    """Addendum 8 Oct 17:2x: the readers step's outputs depend only on the rotation (byte-identical across arms,
    checked on A1 and A2), so the first decode of a rotation stores them here and later decodes copy them in."""
    return J(HERE, "runs", rot, "readers_cache")


def score(scratch_cell: str, session: str) -> dict:
    d3 = J(scratch_cell, "d3", f"CR.{VARIANT}")
    dec = json.load(open(J(d3, "decode.json")))["sessions"][session]["rows"]["A"]
    sl = {r["key"]: r for r in json.load(open(J(d3, "scorerlock.json")))["sessions"][session]["rows"]["A"]}
    n = len(dec)
    com = [r["correct"] for r in dec]
    lock = [sl[r["key"]]["display_lock"] == r["true"] for r in dec]
    edges = {}
    for e in EDGES:
        idx = [i for i, r in enumerate(dec) if r["true"] == e]
        edges[e] = {"n": len(idx), "committed": 100.0 * sum(com[i] for i in idx) / max(len(idx), 1),
                    "lock": 100.0 * sum(lock[i] for i in idx) / max(len(idx), 1)}
    return {"walks": n, "committed_pct": 100.0 * sum(com) / n, "committed_err_pct": 100.0 - 100.0 * sum(com) / n,
            "lock_pct": 100.0 * sum(lock) / n, "edges": edges,
            "rows": [{"key": r["key"], "true": r["true"], "committed": r["final_line"],
                      "lock": sl[r["key"]]["display_lock"]} for r in dec]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rot", choices=tuple(ROTATIONS), required=True)
    ap.add_argument("--arm", choices=tuple(ARMS), required=True)
    ap.add_argument("--k", type=int, required=True)
    a = ap.parse_args()
    os.environ.update(ENV)
    sys.path.insert(0, REPO)
    import pipeline.constrained.pd_repro_trace as T
    from pipeline.constrained import pd_cells as PC

    cell = ROTATIONS[a.rot]
    c = PC.cfg(cell, "decode")
    out_dir = J(HERE, "runs", a.rot)
    os.makedirs(out_dir, exist_ok=True)
    out = J(out_dir, f"eval_{a.arm}_k{a.k}.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    scratch = J(out_dir, f"scratch_{a.arm}_k{a.k}")
    cell_dir = J(scratch, cell)
    tdir = J(cell_dir, "trace")
    marker = J(cell_dir, "FILLED.json")
    if os.path.exists(marker):  # resume after an interruption
        filled = json.load(open(marker))
    else:
        T.build(cell, VARIANT, scratch)
        check = a.arm == "MIX" and a.k == 0
        filled = {} if check else fill_slots(cell_dir, a.rot, a.arm, a.k, c["heads_tag"])
        os.makedirs(tdir, exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            json.dump(filled, f)
    steps = [("readers", "half", "decode", [])] + [("infer", h, "infer", ["--head", h]) for h in T.HEAD_TREES] + \
            [("decode", "half", "decode", [])]
    post = J(cell_dir, "art_half", "posteriors")
    rfiles, rcache = reader_files(cell), readers_cache(a.rot)
    rtr = J(tdir, "readers_half.json")
    if not os.path.exists(rtr) and all(os.path.exists(J(rcache, f)) for f in rfiles):
        for f in rfiles:
            shutil.copy2(J(rcache, f), J(post, f))
        with open(rtr, "w", encoding="utf-8") as f:
            json.dump({"step": "readers", "head": "half", "exit": 0, "from_cache": rcache, "files": rfiles}, f)
    for st, h, envstep, extra in steps:
        tr = J(tdir, f"{st}_{h}.json")
        if os.path.exists(tr) and json.load(open(tr)).get("exit") == 0:
            if st == "readers" and not all(os.path.exists(J(rcache, f)) for f in rfiles):
                os.makedirs(rcache, exist_ok=True)
                for f in rfiles:
                    if not os.path.exists(J(rcache, f)):
                        shutil.copy2(J(post, f), J(rcache, f))
            continue
        cmd = [sys.executable, "-m", "pipeline.constrained.pd_repro_trace", "step", "--cell", cell, "--variant",
               VARIANT, "--step", st, "--scratch", scratch, "--trace-out", tr] + extra
        if st == "decode":
            shutil.rmtree(J(cell_dir, "d3", f"CR.{VARIANT}"), ignore_errors=True)
            if os.path.exists(J(cell_dir, "reproduction.json")):
                os.remove(J(cell_dir, "reproduction.json"))
        t_step = time.time()
        code = subprocess.call(cmd, cwd=REPO, env=T._env(cell, h, envstep, scratch))
        if code and st == "decode" and filled:
            # the decode step exits 1 when its answers differ from the recorded ones, the expected outcome for
            # any arm whose networks differ: accept it when this attempt wrote the decode's own outputs
            d3 = J(cell_dir, "d3", f"CR.{VARIANT}")
            outs = [J(d3, "decode.json"), J(d3, "scorerlock.json"), J(cell_dir, "reproduction.json")]
            if all(os.path.exists(p) and os.path.getmtime(p) >= t_step for p in outs):
                print(f"{cell}: decode differs from the record, as expected for this arm", flush=True)
                continue
        if code:
            raise SystemExit(f"{cell}: step {st} {h} failed ({code})")
        if st == "readers":
            os.makedirs(rcache, exist_ok=True)
            for f in rfiles:
                if not os.path.exists(J(rcache, f)):
                    shutil.copy2(J(post, f), J(rcache, f))
    res = score(cell_dir, c["test"])
    res.update({"rotation": a.rot, "cell": cell, "arm": a.arm, "k": a.k, "slots": filled or "recorded heads",
                "against_record": json.load(open(J(cell_dir, "reproduction.json")))})
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    shutil.rmtree(scratch)
    print(f"{a.rot} {a.arm} k{a.k}: committed {res['committed_pct']:.2f} lock {res['lock_pct']:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
