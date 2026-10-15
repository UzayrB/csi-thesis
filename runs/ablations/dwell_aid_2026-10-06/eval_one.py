"""Decode one arm and seed set on one test cell and score it (PLAN.md, Evaluation).

The decode is `pd_repro_trace`'s own, which equals the live app on 360 of 360 walks: its `build` makes a scratch tree
with the cell's head files, readers and reader rows, and its `step` runs readers, the five heads' inference and the
decode. The only change is that the five cell heads' files in the scratch tree are replaced by this arm's, under the
names the steps load. With --run shipped nothing is replaced, which reproduces the shipped decode (a check).
Writes <run>/eval_<cell>.json and deletes the scratch tree's bulky files afterwards.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
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
ENV = {"PD_CLEAN_PREFIX": "FC", "PD_PACE_MEAN": "1.3034113357347858", "PD_PACE_SD": "0.11254567809955889",
       "PD_REPRO_VARIANT": VARIANT}


def swap_heads(scratch_cell: str, run: str, k: int, heads_tag: str) -> list:
    """Replace the cell's OWN head files (tag = the cell's heads_tag; g25/g100) in the scratch tree with this
    arm's, seed offset 100 x k. Every other network there (the V0 readers and the reader rows' networks, such as
    s0102_to_sB1, s01_to_s02 and s02_to_s01) stays as shipped."""
    done = []
    for f in sorted(glob.glob(J(scratch_cell, "art_*", "models", f"{heads_tag}_g*_e24_s*_link*.pt"))):
        head = os.path.basename(os.path.dirname(os.path.dirname(f)))[4:]
        m = re.match(r"(?P<tag>.+)_g(?P<n>\d+)_e24_s(?P<s>\d+)_link(?P<l>\d)\.pt$", os.path.basename(f))
        if not m or m["tag"] != heads_tag:
            continue
        src = glob.glob(J(run, f"art_{head}", "models", f"*_g{m['n']}_e24_s{int(m['s']) + 100 * k}_link{m['l']}.pt"))
        assert len(src) == 1, (f, src)
        shutil.copy2(src[0], f)
        done.append(os.path.basename(f))
    return done


def score(scratch_cell: str, session: str) -> dict:
    d3 = J(scratch_cell, "d3", f"FC.{VARIANT}")
    dec = json.load(open(J(d3, "decode.json")))["sessions"][session]["rows"]["A"]
    sl = {r["key"]: r for r in json.load(open(J(d3, "scorerlock.json")))["sessions"][session]["rows"]["A"]}
    n = len(dec)
    com = [r["correct"] for r in dec]
    lock = [sl[r["key"]]["display_lock"] == r["true"] for r in dec]
    frames = [e for r in dec for e in sl[r["key"]]["res"]["err"]]
    edges = {}
    for e in EDGES:
        idx = [i for i, r in enumerate(dec) if r["true"] == e]
        edges[e] = {"n": len(idx), "committed": 100.0 * sum(com[i] for i in idx) / max(len(idx), 1),
                    "lock": 100.0 * sum(lock[i] for i in idx) / max(len(idx), 1)}
    return {"walks": n, "committed_pct": 100.0 * sum(com) / n, "committed_err_pct": 100.0 - 100.0 * sum(com) / n,
            "lock_pct": 100.0 * sum(lock) / n, "frame_err_median_m": statistics.median(frames),
            "frame_err_mean_m": statistics.fmean(frames), "frames": len(frames), "edges": edges,
            "rows": [{"key": r["key"], "true": r["true"], "committed": r["final_line"],
                      "lock": sl[r["key"]]["display_lock"]} for r in dec]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", choices=("fin_A3", "fin_B2"), required=True)
    ap.add_argument("--run", required=True, help="the arm and seed set's folder, or 'shipped'")
    ap.add_argument("--k", type=int, default=0)
    a = ap.parse_args()
    os.environ.update(ENV)
    sys.path.insert(0, REPO)
    import pipeline.constrained.pd_repro_trace as T

    out_dir = J(HERE, "shipped_check") if a.run == "shipped" else a.run
    scratch = J(out_dir, f"scratch_{a.cell}")
    cell_dir = J(scratch, a.cell)
    tdir = J(cell_dir, "trace")
    marker = J(cell_dir, "SWAPPED.json")
    if os.path.exists(marker):  # resume: the scratch tree was built and swapped by an earlier, interrupted run
        swapped = json.load(open(marker))
    else:
        T.build(a.cell, VARIANT, scratch)
        from pipeline.constrained import pd_cells as PC
        heads_tag = PC.cfg(a.cell, "decode")["heads_tag"]
        swapped = [] if a.run == "shipped" else swap_heads(cell_dir, a.run, a.k, heads_tag)
        assert a.run == "shipped" or len(swapped) == 15, f"expected 15 head files (5 heads x 3 links), got {len(swapped)}"
        os.makedirs(tdir, exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            json.dump(swapped, f)
    steps = [("readers", "half", "decode", [])] + [("infer", h, "infer", ["--head", h]) for h in T.HEAD_TREES] + \
            [("decode", "half", "decode", [])]
    for st, h, envstep, extra in steps:
        tr = J(tdir, f"{st}_{h}.json")
        if os.path.exists(tr) and json.load(open(tr)).get("exit") == 0:
            continue  # finished before an interruption; its outputs are in the scratch tree
        cmd = [sys.executable, "-m", "pipeline.constrained.pd_repro_trace", "step", "--cell", a.cell, "--variant",
               VARIANT, "--step", st, "--scratch", scratch, "--trace-out", J(tdir, f"{st}_{h}.json")] + extra
        if st == "decode":  # an earlier, unaccepted attempt's outputs would make the step refuse; clear them
            shutil.rmtree(J(cell_dir, "d3", f"FC.{VARIANT}"), ignore_errors=True)
            if os.path.exists(J(cell_dir, "reproduction.json")):
                os.remove(J(cell_dir, "reproduction.json"))
        t_step = time.time()
        code = subprocess.call(cmd, cwd=REPO, env=T._env(a.cell, h, envstep, scratch))
        if code and st == "decode" and a.run != "shipped":
            # The decode step exits 1 when its answers differ from the shipped record, which is the expected outcome
            # for any arm whose heads differ. Accept it when the decode's own outputs were written.
            d3 = J(cell_dir, "d3", f"FC.{VARIANT}")
            outs = [J(d3, "decode.json"), J(d3, "scorerlock.json"), J(cell_dir, "reproduction.json")]
            if all(os.path.exists(p) and os.path.getmtime(p) >= t_step for p in outs):  # written by THIS attempt
                print(f"{a.cell}: decode differs from the shipped record, as expected for this arm", flush=True)
                continue
        if code:
            raise SystemExit(f"{a.cell}: step {st} {h} failed ({code})")
    res = score(cell_dir, "03" if a.cell == "fin_A3" else "B2")
    res.update({"cell": a.cell, "run": a.run, "k": a.k, "swapped": swapped,
                "against_shipped": json.load(open(J(cell_dir, "reproduction.json")))})
    with open(J(out_dir, f"eval_{a.cell}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    shutil.rmtree(scratch)  # bulky posteriors and copies; the rows are kept in eval_<cell>.json
    print(f"{a.cell} {a.run}: committed {res['committed_pct']:.2f} lock {res['lock_pct']:.2f} "
          f"frame median {res['frame_err_median_m']:.3f} m", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
