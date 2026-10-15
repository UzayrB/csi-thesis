"""pd_repro: the corrected FINAL reproduced from its hashes (29 September 2026; QUEUE item 1b).

    python3 -m pipeline.constrained.pd_repro hashes                 # FINAL_CORRECTED_HASHES.txt, after F3
    python3 -m pipeline.constrained.pd_repro run --cell fin_A3      # then fin_B2

`hashes` writes `runs/dc2_results/final/FINAL_CORRECTED_HASHES.txt`. It holds every file in
FINAL_HASHES.txt, plus every network file the corrected decodes opened (from their audit traces), plus
the code that fixes the readers.

`run` refuses unless every file of that list still has its hash. It then re-derives the corrected FINAL
decode in a SCRATCH tree, on the CPU, from nothing but hashed files and the window caches:
  1. the five heads' posteriors on the test session, inferred afresh from the hashed weights (relative
     RSSI and the shared-encoder inference installed, as the prep phase ran them; `dc2_run.do_infer`);
  2. the test-side reader's posteriors, re-inferred from the hashed V0 heads with absolute RSSI, as
     the twin cell made them;
  3. the corrected B1 reader rows, re-inferred from the hashed A1+A2 heads;
  4. the decode of the re-selected variant with the corrected map (`pd_clean.decode_inner`), the readers refitted rather
     than read from the cache.
The rows must equal `cells/<cell>/d3/CR.<variant>`, committed answer and both locks, or it fails. The A1
and A2 reader rows (`s02_to_s01`, `s01_to_s02` posteriors) are hashed inputs copied from the shipped
tree; with PD_REPRO_REBUILD_AB=1 they are also rebuilt and compared (about 24 CPU minutes per session).
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
HASHES = J(RES, "final", "FINAL_CORRECTED_HASHES.txt")
SCRATCH = J(RES, "verify", "repro")
HEAD_TREES = ("half", "fh1s", "g1s1", "g1s2", "g100")


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def write_hashes(variant: str) -> int:
    files = []
    with open(J(RES, "final", "FINAL_HASHES.txt"), encoding="utf-8") as f:
        files += [ln.split()[1] for ln in f if ln.strip()]
    for cell in ("fin_A3", "fin_B2"):
        from pipeline.constrained.pd_clean import PREFIX
        with open(J(RES, "cells", cell, "d3", f"{PREFIX}.{variant}", "clean.json"), encoding="utf-8") as f:
            opened = json.load(f)["files_opened"]
        files += [p for p in opened if p.startswith("runs/dc2_results/cells/") and p.endswith((".pt", ".npz"))
                  and "/d3/" not in p]
    files += ["pipeline/constrained/pd_clean.py", "pipeline/constrained/pd_repro.py"]
    files += sorted(os.path.relpath(p, REPO_ROOT) for p in glob.glob(J(RES, "clean_readers", "*")))
    files = sorted(set(files))
    with open(HASHES, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"{sha(J(REPO_ROOT, p))}  {p}\n")
    print(f"{len(files)} files hashed -> {os.path.relpath(HASHES, REPO_ROOT)}")
    return 0


def check_hashes() -> dict:
    bad, n = [], 0
    with open(HASHES, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            h, p = ln.split(None, 1)
            p = p.strip()
            n += 1
            if not os.path.exists(J(REPO_ROOT, p)) or sha(J(REPO_ROOT, p)) != h:
                bad.append(p)
    return {"n": n, "mismatched": bad}


def hashed(p: str) -> bool:
    with open(HASHES, encoding="utf-8") as f:
        return any(ln.split(None, 1)[1].strip() == p for ln in f if ln.strip())


def scratch_cfg(PC, cell: str, cmd: str = None) -> dict:
    """The cell's configuration with its trees moved to the scratch folder; its views are the cell's own."""
    c = PC.cfg(cell, cmd)
    base = J(SCRATCH, cell)
    return dict(c, base=base, tree=(lambda h, _b=base: J(_b, f"art_{h}")),
                model_src={h: J(base, f"art_{h}") for h in HEAD_TREES})


def build(cell: str) -> dict:
    """The scratch trees: the hashed weights and reader inputs copied in, posteriors left to re-derive."""
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c, s = PC.cfg(cell, "decode"), scratch_cfg(PC, cell, "decode")
    if os.path.exists(s["base"]):
        shutil.rmtree(s["base"])
    copied = []
    for h in HEAD_TREES:
        dst = s["tree"](h)
        os.makedirs(J(dst, "models"))
        os.makedirs(J(dst, "posteriors"))
        for sub in ("features", "rssi_full"):
            os.symlink(J(c["shared"], sub), J(dst, sub))
        # the five heads' weights: fin_A3's hashed files (fin_B2 holds byte-identical copies under its own tag)
        a3 = PC.cfg("fin_A3", "decode")
        for p in glob.glob(J(a3["tree"](h), "models", f"{a3['heads_tag']}_*.pt")):
            rel = os.path.relpath(p, REPO_ROOT)
            assert hashed(rel), f"not in the hashed set: {rel}"
            name = os.path.basename(p).replace(a3["heads_tag"], c["heads_tag"], 1)
            own = J(c["tree"](h), "models", name)
            assert os.path.exists(own) and sha(own) == sha(p), f"{own} differs from the hashed {rel}"
            shutil.copy2(p, J(dst, "models", name))
            copied.append(rel)
    # the readers' model files (V0, the A1 and A2 cross-fit tags, the corrected B1 tag): hashed inputs
    half = s["tree"]("half")
    with open(J(c["base"], "crossfit.json"), encoding="utf-8") as f:
        plan = json.load(f)["plan"]
    tags = [c["reader_tag"]] + [p["clean"] for p in plan.values()]
    for t in tags:
        for p in glob.glob(J(c["tree"]("half"), "models", f"{t}_*.pt")):
            shutil.copy2(p, J(half, "models", os.path.basename(p)))
            copied.append(os.path.relpath(p, REPO_ROOT))
    # the A1 and A2 reader rows' posteriors: hashed inputs (rebuilt and compared in the decode step)
    for sess, p in plan.items():
        if not p["changed"]:
            src = J(c["tree"]("half"), "posteriors", f"{p['clean']}_g25_e24_s0_full.npz")
            shutil.copy2(src, J(half, "posteriors", os.path.basename(src)))
            copied.append(os.path.relpath(src, REPO_ROOT))
    return {"copied": copied, "plan": plan, "reader_tag": c["reader_tag"]}


def infer_inner(cell: str, head: str) -> int:
    """One head's posteriors on the test session, as the prep phase inferred them."""
    from pipeline.constrained import pd_cells as PC
    PC.install_rrel()
    PC.install_arch_infer()
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.constrained import dc2_run as R
    c = scratch_cfg(PC, cell, "infer")
    return R.do_infer(c, head)


def readers_inner(cell: str) -> int:
    """The test-side V0 posteriors and the corrected B1 rows, re-inferred WITHOUT relative RSSI (the
    per-link reader heads were trained on absolute RSSI), plus the A1 and A2 rows rebuilt for comparison."""
    from pipeline.constrained.pd_clean import SOURCES, build_block_file, force_cpu
    force_cpu()
    from pipeline.constrained import pd_cells as PC
    c = scratch_cfg(PC, cell, "decode")
    orig = PC.cfg(cell, "decode")
    from pipeline.constrained import dc2_run as R
    R._bind(c)
    half = c["tree"]("half")
    with open(J(orig["base"], "crossfit.json"), encoding="utf-8") as f:
        plan = json.load(f)["plan"]
    out = {}
    v0 = c["reader_tag"]
    build_block_file(c, c["test"], half, v0, J(half, "posteriors", f"{v0}_g25_e24_s0_full.npz"))
    out["V0"] = v0
    for sess, p in plan.items():
        if p["changed"]:
            src_tree, src_tag = SOURCES[tuple(p["clean_train"])]
            build_block_file(c, sess, src_tree, src_tag, J(half, "posteriors", f"{p['clean']}_g25_e24_s0_full.npz"))
            out[sess] = p["clean"]
        elif os.environ.get("PD_REPRO_REBUILD_AB") == "1":
            # rebuilt beside the hashed copy, compared, never used (opt-in: about 24 CPU minutes per Room A session)
            from pipeline.constrained.artefacts import read_full_posteriors
            import numpy as np
            tmp = J(c["base"], f"rebuilt_{p['clean']}.npz")
            build_block_file(c, sess, J(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_half"), p["clean"], tmp)
            a, b = read_full_posteriors(J(half, "posteriors", f"{p['clean']}_g25_e24_s0_full.npz")), read_full_posteriors(tmp)
            out[f"{sess}_rebuilt_against_hashed"] = {
                "stems_equal": sorted(a) == sorted(b),
                "max_abs_diff_xy_hat": max(float(np.max(np.abs(a[k]["xy_hat"].astype(float) - b[k]["xy_hat"].astype(float))))
                                           for k in set(a) & set(b)) if set(a) & set(b) else None}
    with open(J(c["base"], "readers.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("readers re-derived:", json.dumps(out), flush=True)
    return 0


def decode_inner(cell: str, variant: str) -> int:
    """pd_clean.decode_inner on the scratch trees, readers refitted (no cache), then the comparison."""
    from pipeline.constrained import pd_cells as PC
    o = PC.cfg
    PC.cfg = lambda cell_, cmd=None: (dict(o(cell_, cmd), base=J(SCRATCH, cell),
                                           tree=(lambda h, _b=J(SCRATCH, cell): J(_b, f"art_{h}")))
                                      if cell_ == cell else o(cell_, cmd))
    from pipeline.constrained import pd_clean
    code = pd_clean.decode_inner(cell, [variant], False)
    if code:
        return code
    from pipeline.constrained.pd_clean import compare
    res = compare(J(SCRATCH, cell, "d3", f"{pd_clean.PREFIX}.{variant}"), J(RES, "cells", cell, "d3", f"{pd_clean.PREFIX}.{variant}"))
    with open(J(SCRATCH, cell, "reproduction.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"REPRODUCTION {cell}: {res}", flush=True)
    return 0 if res["EXACT"] else 1


def run(cell: str, variant: str) -> int:
    t0 = time.time()
    sys.path.insert(0, REPO_ROOT)
    chk = check_hashes()
    print(f"hashes: {chk['n']} files, mismatched {chk['mismatched']}", flush=True)
    if chk["mismatched"]:
        raise SystemExit(f"REFUSED: files differ from their hashes: {chk['mismatched']}")
    info = build(cell)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    base_env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT, TDR_ART_DIR=J(SCRATCH, cell, "art_half"))
    base_env["TDR_TEST_TAG_MAP"] = _clean_map(c, base_env)
    base_env.update(PD_CLEAN_NOCACHE="1", PD_CLEAN_STAGE=J(SCRATCH, cell, "stage"))

    def sub(cmd, env, *extra):
        code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_repro", cmd, "--inner", "--cell", cell,
                                *extra], cwd=REPO_ROOT, env=env)
        if code:
            raise SystemExit(f"{cell}: the {cmd} step {extra} failed (exit {code})")
    sub("readers", base_env)
    for h in HEAD_TREES:
        env = dict(PC.env_for(c, h, "infer"), PYTHONPATH=REPO_ROOT, TDR_ART_DIR=J(SCRATCH, cell, f"art_{h}"))
        env["TDR_TEST_TAG_MAP"] = _clean_map(c, env)
        sub("infer", env, "--head", h)
    sub("decode", base_env, "--variant", variant)
    with open(J(SCRATCH, cell, "run.json"), "w", encoding="utf-8") as f:
        json.dump({"hashes": chk, "build": info, "minutes": round((time.time() - t0) / 60.0, 1)}, f, indent=1)
    return 0


def _clean_map(c, env) -> str:
    tmap = json.loads(env.get("TDR_TEST_TAG_MAP") or "{}")
    with open(J(c["base"], "crossfit.json"), encoding="utf-8") as f:
        for s, p in json.load(f)["plan"].items():
            if p["changed"]:
                tmap[s] = p["clean"]
    return json.dumps(tmap)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hashes", "run", "infer", "readers", "decode"])
    ap.add_argument("--cell")
    ap.add_argument("--head")
    ap.add_argument("--variant", default=None, help="default: the recorded final variant")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.variant is None:
        from pipeline.live.final_model import final_variant
        a.variant = final_variant()
    if a.cmd == "hashes":
        return write_hashes(a.variant)
    if a.cmd == "run":
        return run(a.cell, a.variant)
    return {"infer": lambda: infer_inner(a.cell, a.head), "readers": lambda: readers_inner(a.cell),
            "decode": lambda: decode_inner(a.cell, a.variant)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
