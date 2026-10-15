"""pd_repro_trace: rebuild a test decode from hashed files, with the hash list taken from FILE TRACES
(29 to 30 September 2026; Uzayr's items A2 and A3).

    python3 -m pipeline.constrained.pd_repro_trace hashes --cell zsf_B2 --variant relgateU+abstain+a2w0.25
    python3 -m pipeline.constrained.pd_repro_trace run    --cell zsf_B2 --variant relgateU+abstain+a2w0.25

WHY. `pd_repro.write_hashes` chose its files by name pattern, and missed the B1 reader's three position
networks (`reports/MODEL_FINAL_TRACKING_CORRECTED.md` section 10). Here the list is what was actually read:
  1. the test decode's own trace: every file `pd_clean.decode_inner` opened for reading
     (`cells/<cell>/d3/<PREFIX>.<variant>/clean.json`, `files_opened`);
  2. the trace of a full rebuild of that decode's derived inputs (reader rows, the five heads' posteriors,
     the decode itself), run in a scratch tree with an audit hook in every step, recording every file
     opened and every pipeline module imported.
Every input read outside the scratch tree is hashed: data, caches, networks, results files and code.

`run` refuses unless every listed file still has its hash, rebuilds again in a FRESH scratch tree with the
same hooks, and FAILS if any step reads an input outside the scratch tree that the list does not hold. The
rows must equal the test decode's, committed, display lock and scorer lock (`pd_clean.compare`).

The step functions are `pd_repro`'s own (`infer_inner`, `decode_inner`), unchanged; `pd_repro.py` is in the
frozen hash list and is not edited. Only the scratch location, the head files copied in (each cell's OWN
heads, not fin_A3's) and the reader plan (from the decode's own record when no crossfit.json exists) differ.
Runs on the CPU. Writes under runs/dc2_results/verify/repro_trace/ and runs/dc2_results/final/TRACE_HASHES_<cell>.txt.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
TRACE_ROOT = J(RES, "verify", "repro_trace")
HEAD_TREES = ("half", "fh1s", "g1s1", "g1s2", "g100")
#: paths that are the system, not the model's inputs
SYSTEM = ("/System/", "/dev/", "/proc/", "/usr/", "/var/folders/", "/private/var/", "/opt/", "/Library/",
          "/etc/", "/private/etc/")
OLD_LISTS = [J(RES, "final", n) for n in ("FINAL_HASHES.txt", "FINAL_CORRECTED_HASHES.txt",
                                           "FINAL_CORRECTED_HASHES_SUPPLEMENT.txt")]


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def list_path(cell: str) -> str:
    return J(RES, "final", f"TRACE_HASHES_{cell}.txt")


def rel(p: str) -> str:
    a = os.path.abspath(p)
    return os.path.relpath(a, REPO_ROOT) if a.startswith(REPO_ROOT + os.sep) else a


def is_input(p: str, scratch: str) -> bool:
    a = os.path.abspath(J(REPO_ROOT, p)) if not os.path.isabs(p) else p
    if a.startswith(SYSTEM) or "/site-packages/" in a or a.endswith((".pyc",)) or "__pycache__" in a:
        return False
    if not a.startswith(REPO_ROOT + os.sep):
        return False
    if a.startswith(os.path.abspath(scratch) + os.sep) or a.startswith(TRACE_ROOT + os.sep):
        return False
    return True


# ------------------------------------------------------------------------------------------ the steps

def _plan(cell: str, variant: str) -> dict:
    from pipeline.constrained.pd_clean import PREFIX
    cf = J(RES, "cells", cell, "crossfit.json")
    if os.path.exists(cf):
        with open(cf, encoding="utf-8") as f:
            return json.load(f)["plan"]
    with open(J(RES, "cells", cell, "d3", f"{PREFIX}.{variant}", "clean.json"), encoding="utf-8") as f:
        plan = json.load(f)["plan"]
    assert not any(p["changed"] for p in plan.values()), f"{cell}: a changed reader map needs crossfit.json"
    return plan


def build_inputs(cell: str, variant: str) -> list:
    """Every source file `build` copies into the scratch tree, by build's own rules, copying nothing.
    The copy runs in the driver process, which has no audit hook, so these are listed here (fixed 30 Sep 01:21:
    the first lists missed them)."""
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    out = []
    for h in HEAD_TREES:
        out += [rel(p) for p in sorted(glob.glob(J(c["tree"](h), "models", f"{c['heads_tag']}_*.pt")))]
    plan = _plan(cell, variant)
    for t in [c["reader_tag"]] + [p["clean"] for p in plan.values()]:
        out += [rel(p) for p in sorted(glob.glob(J(c["tree"]("half"), "models", f"{t}_*.pt")))]
    for s_, p in plan.items():
        if not p["changed"]:
            out.append(rel(J(c["tree"]("half"), "posteriors", f"{p['clean']}_g25_e24_s0_full.npz")))
    return sorted(set(out))


def build(cell: str, variant: str, scratch: str) -> dict:
    """The scratch trees: the cell's OWN head files, the reader networks and the unchanged sessions' reader
    rows copied in (all hashed inputs); the posteriors, the corrected rows and the gate energies left to
    re-derive."""
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    base = J(scratch, cell)
    if os.path.exists(base):
        shutil.rmtree(base)
    copied = []
    for h in HEAD_TREES:
        dst = J(base, f"art_{h}")
        os.makedirs(J(dst, "models"))
        os.makedirs(J(dst, "posteriors"))
        for sub in ("features", "rssi_full"):
            os.symlink(J(c["shared"], sub), J(dst, sub))
        for p in sorted(glob.glob(J(c["tree"](h), "models", f"{c['heads_tag']}_*.pt"))):
            shutil.copy2(p, J(dst, "models", os.path.basename(p)))
            copied.append(rel(p))
    plan = _plan(cell, variant)
    half = J(base, "art_half")
    for t in [c["reader_tag"]] + [p["clean"] for p in plan.values()]:
        for p in sorted(glob.glob(J(c["tree"]("half"), "models", f"{t}_*.pt"))):
            if not os.path.exists(J(half, "models", os.path.basename(p))):
                shutil.copy2(p, J(half, "models", os.path.basename(p)))
                copied.append(rel(p))
    for s, p in plan.items():
        if not p["changed"]:
            src = J(c["tree"]("half"), "posteriors", f"{p['clean']}_g25_e24_s0_full.npz")
            shutil.copy2(src, J(half, "posteriors", os.path.basename(src)))
            copied.append(rel(src))
    return {"copied": copied, "plan": plan, "reader_tag": c["reader_tag"]}


def readers_inner(cell: str, variant: str) -> int:
    """pd_repro.readers_inner, with the plan from _plan: the test-side reader posteriors re-inferred
    (absolute RSSI, as the twin made them) and any corrected rows rebuilt from their source heads."""
    from pipeline.constrained.pd_clean import SOURCES, build_block_file, force_cpu
    import pipeline.constrained.pd_repro as PR
    force_cpu()
    from pipeline.constrained import pd_cells as PC
    c = PR.scratch_cfg(PC, cell, "decode")
    from pipeline.constrained import dc2_run as R
    R._bind(c)
    half = c["tree"]("half")
    plan = _plan(cell, variant)
    out = {}
    v0 = c["reader_tag"]
    build_block_file(c, c["test"], half, v0, J(half, "posteriors", f"{v0}_g25_e24_s0_full.npz"))
    out["V0"] = v0
    for sess, p in plan.items():
        if p["changed"]:
            src_tree, src_tag = SOURCES[tuple(p["clean_train"])]
            build_block_file(c, sess, src_tree, src_tag, J(half, "posteriors", f"{p['clean']}_g25_e24_s0_full.npz"))
            out[sess] = p["clean"]
    print("readers re-derived:", json.dumps(out), flush=True)
    return 0


def step_inner(a) -> int:
    """One step in its own process, with an audit hook recording every file it opens."""
    seen = {}
    wmask = os.O_WRONLY | os.O_RDWR | os.O_CREAT

    def hook(ev, args):
        if ev != "open" or not args:
            return
        p = args[0]
        if not isinstance(p, (str, bytes, os.PathLike)):
            return
        p = os.fsdecode(p)
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        w = (isinstance(mode, str) and any(ch in mode for ch in "wax+")) or \
            (mode is None and isinstance(flags, int) and bool(flags & wmask))
        seen.setdefault(os.path.abspath(p), set()).add("w" if w else "r")
    sys.addaudithook(hook)
    import pipeline.constrained.pd_repro as PR
    PR.SCRATCH = a.scratch
    code = 1
    try:
        if a.step == "readers":
            code = readers_inner(a.cell, a.variant)
        elif a.step == "infer":
            code = PR.infer_inner(a.cell, a.head)
        elif a.step == "decode":
            code = PR.decode_inner(a.cell, a.variant)
        else:
            raise SystemExit(f"unknown step {a.step}")
    finally:
        mods = sorted({rel(m.__file__) for m in list(sys.modules.values())
                       if getattr(m, "__file__", None) and os.path.isabs(m.__file__)
                       and os.path.abspath(m.__file__).startswith(REPO_ROOT + os.sep) and os.path.isfile(m.__file__)})
        with open(a.trace_out, "w", encoding="utf-8") as f:
            json.dump({"step": a.step, "head": a.head, "exit": code,
                       "files": {rel(p): sorted(m) for p, m in sorted(seen.items())}, "modules": mods}, f, indent=1)
    return code


# ------------------------------------------------------------------------------------------ the driver

def _env(cell: str, head: str, step: str, scratch: str) -> dict:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    e = dict(PC.env_for(c, head, step), PYTHONPATH=REPO_ROOT, TDR_ART_DIR=J(scratch, cell, f"art_{head}"))
    tmap = json.loads(e.get("TDR_TEST_TAG_MAP") or "{}")
    for s, p in _plan(cell, os.environ["PD_REPRO_VARIANT"]).items():
        if p["changed"]:
            tmap[s] = p["clean"]
    e["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    e.update(PD_CLEAN_NOCACHE="1", PD_CLEAN_STAGE=J(scratch, cell, "stage"), OMP_NUM_THREADS="1")
    for k in ("PD_CLEAN_PREFIX", "PD_PACE_MEAN", "PD_PACE_SD"):
        assert os.environ.get(k), f"{k} must be set, as the test chain set it"
        e[k] = os.environ[k]
    return e


def rebuild(cell: str, variant: str, scratch: str) -> dict:
    """Build the scratch trees, run every step with its trace, and compare the decode with the record."""
    t0 = time.time()
    os.environ["PD_REPRO_VARIANT"] = variant
    info = build(cell, variant, scratch)
    tdir = J(scratch, cell, "trace")
    os.makedirs(tdir, exist_ok=True)
    steps = [("readers", "half", "decode", [])] + \
            [("infer", h, "infer", ["--head", h]) for h in HEAD_TREES] + \
            [("decode", "half", "decode", [])]
    traces = []
    for st, h, envstep, extra in steps:
        out = J(tdir, f"{st}_{h}.json")
        cmd = [sys.executable, "-m", "pipeline.constrained.pd_repro_trace", "step", "--cell", cell,
               "--variant", variant, "--step", st, "--scratch", scratch, "--trace-out", out] + extra
        print(f"[{time.strftime('%H:%M:%S')}] {cell}: {st} {h if st == 'infer' else ''}", flush=True)
        code = subprocess.call(cmd, cwd=REPO_ROOT, env=_env(cell, h, envstep, scratch))
        if code:
            raise SystemExit(f"{cell}: the {st} step ({h}) failed (exit {code})")
        traces.append(out)
    rp = J(scratch, cell, "reproduction.json")
    with open(rp, encoding="utf-8") as f:
        res = json.load(f)
    return {"build": info, "traces": traces, "reproduction": res, "minutes": round((time.time() - t0) / 60.0, 1)}


def trace_inputs(traces: list, scratch: str) -> tuple:
    files, mods, writes_outside = set(), set(), set()
    for t in traces:
        with open(t, encoding="utf-8") as f:
            d = json.load(f)
        for p, m in d["files"].items():
            if "w" in m and not ("r" in m) and is_input(p, scratch):
                writes_outside.add(p)
            if "r" in m and is_input(p, scratch) and os.path.isfile(J(REPO_ROOT, p)):
                files.add(p)
        # a module whose __file__ is relative (torch._classes gives "_classes.py") is not a repository file
        mods |= {m for m in d["modules"] if is_input(m, scratch) and os.path.isfile(J(REPO_ROOT, m))}
    return files, mods, writes_outside


def decode_trace(cell: str, variant: str) -> set:
    from pipeline.constrained.pd_clean import PREFIX
    with open(J(RES, "cells", cell, "d3", f"{PREFIX}.{variant}", "clean.json"), encoding="utf-8") as f:
        fo = json.load(f)["files_opened"]
    return {p for p, m in fo.items() if "r" in m and "w" not in m and is_input(p, J(RES, "verify", "clean"))
            and os.path.isfile(J(REPO_ROOT, p))}


def old_hashes() -> dict:
    out = {}
    for lp in OLD_LISTS:
        if os.path.exists(lp):
            with open(lp, encoding="utf-8") as f:
                for ln in f:
                    if ln.strip():
                        h, p = ln.split(None, 1)
                        out[p.strip()] = h
    return out


def do_hashes(cell: str, variant: str, reuse: bool = False, amend: bool = False) -> int:
    """The list from the decode's own trace and a traced rebuild; cross-checked against the earlier lists.
    reuse: take the traces of a completed traced rebuild in the same scratch tree rather than rebuilding."""
    scratch = J(TRACE_ROOT, "list", cell)
    tdir = J(scratch, cell, "trace")
    if reuse:
        with open(J(scratch, cell, "reproduction.json"), encoding="utf-8") as f:
            rep = json.load(f)
        traces = sorted(J(tdir, x) for x in os.listdir(tdir) if x.endswith(".json"))
        assert len(traces) == 7, traces
        r = {"traces": traces, "reproduction": rep, "minutes": None, "reused": True}
    else:
        r = rebuild(cell, variant, scratch)
    files, mods, wout = trace_inputs(r["traces"], scratch)
    dec = decode_trace(cell, variant)
    bins = set(build_inputs(cell, variant))
    allf = sorted(files | mods | dec | bins)
    lp = list_path(cell)
    if os.path.exists(lp):
        if not amend:
            raise SystemExit(f"REFUSING to overwrite {lp}")
        v1 = lp.replace(".txt", ".v1.txt")
        assert not os.path.exists(v1), f"{v1} exists"
        os.replace(lp, v1)                      # the first version, kept
    old = old_hashes()
    rows, agree, differ = [], 0, []
    for p in allf:
        h = sha(J(REPO_ROOT, p))
        rows.append(f"{h}  {p}")
        if p in old:
            if old[p] == h:
                agree += 1
            else:
                differ.append(p)
    with open(lp, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    summ = {"cell": cell, "variant": variant, "list": rel(lp), "n_files": len(allf),
            "from_decode_trace": len(dec), "from_rebuild_trace": len(files), "code_modules": len(mods),
            "from_the_copy_step": len(bins), "copy_step_only": len(bins - files - mods - dec),
            "decode_trace_only": sorted(dec - files - mods), "in_earlier_lists": agree + len(differ),
            "agree_with_earlier_lists": agree, "DIFFER_from_earlier_lists": differ,
            "writes_outside_scratch": sorted(wout), "trace_rebuild": r["reproduction"], "minutes": r["minutes"]}
    with open(J(scratch, cell, "hashes_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k != "decode_trace_only"}, indent=1), flush=True)
    return 0 if not differ else 1


def do_run(cell: str, variant: str) -> int:
    lp = list_path(cell)
    listed, bad = {}, []
    with open(lp, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                h, p = ln.split(None, 1)
                listed[p.strip()] = h
    for p, h in listed.items():
        if not os.path.exists(J(REPO_ROOT, p)) or sha(J(REPO_ROOT, p)) != h:
            bad.append(p)
    print(f"hashes: {len(listed)} files, mismatched {bad}", flush=True)
    if bad:
        raise SystemExit(f"REFUSED: files differ from their hashes: {bad}")
    scratch = J(TRACE_ROOT, "run", cell)
    r = rebuild(cell, variant, scratch)
    files, mods, wout = trace_inputs(r["traces"], scratch)
    unlisted = sorted((files | mods | set(build_inputs(cell, variant))) - set(listed))
    out = {"cell": cell, "variant": variant, "hashes_checked": len(listed), "mismatched": bad,
           "inputs_read": len(files | mods), "copy_step_inputs": len(build_inputs(cell, variant)), "UNLISTED_INPUTS": unlisted, "writes_outside_scratch": sorted(wout),
           "reproduction": r["reproduction"], "minutes": r["minutes"],
           "PASS": bool(not unlisted and r["reproduction"].get("EXACT"))}
    with open(J(scratch, cell, "run.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"REPRODUCTION {cell}: {json.dumps(r['reproduction'])}", flush=True)
    print(f"unlisted inputs: {unlisted}", flush=True)
    return 0 if out["PASS"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hashes", "run", "step"])
    ap.add_argument("--cell", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--step")
    ap.add_argument("--head", default="half")
    ap.add_argument("--scratch")
    ap.add_argument("--trace-out")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--amend", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "step":
        return step_inner(a)
    sys.path.insert(0, REPO_ROOT)
    return do_hashes(a.cell, a.variant, a.reuse, a.amend) if a.cmd == "hashes" else do_run(a.cell, a.variant)


if __name__ == "__main__":
    sys.exit(main())
