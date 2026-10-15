"""ADDENDUM.md: build the rotation cells f05r_* beside d4c_fuse_*, check them, swap in the all-0.5 s heads, decode the
new reference. The ship's builder (runs/ship_0p5_2026-10-08/build_cells.py), pointed at the rotations.

    prep  ROT   view, models shared from d4c_fuse (byte-checked), the twin's readers, the Room A reader-row files copied
                from d4c_fuse, the clean reader rows (pd_clean crossfit)
    plumb ROT   d4c_fuse's heads' test posteriors copied in, then pd_clean decode under prefix PL with the DT0 settings
                (frozen A1+A2 pace, clean reader map, readers fitted fresh); its rows must equal
                d4c_fuse/d3/DT0.<variant> exactly (committed line, display lock, scorer lock), or this exits 1
    swap  ROT   the four ALL05 seed set 0 networks replace the old slots, renamed to the slot's file seed, byte-checked;
                the old heads' posteriors move to art_*/posteriors_plumb/ (nothing is deleted)
    infer ROT   the four swapped heads inferred on the GPU (pd_cells infer), one at a time, under a memory watchdog;
                half is unchanged, so its posteriors stay
    ref   ROT   pd_clean decode under prefix D05, the DT0 settings: the new reference of PREREG sections 2 and 7

ROT is B1, A2 or A1. Writes: runs/dc2_results/cells/f05r_*/ and this folder. d4c_fuse_* and the ablation are read only.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import reg  # noqa: E402

reg.register()
VARIANT = "relgateU+abstain+a2w0.25"
ABL = J(REPO, "runs", "ablations", "stride_mix_2026-10-08", "runs")
#: slot -> (ablation network folder, cells, training seed, slot file seed): ALL05 seed set 0
SLOTS = {"fh1s": ("p05_s3_k0", 25, 3, 0), "g1s1": ("p05_s1_k0", 25, 1, 1), "g1s2": ("p05_s2_k0", 25, 2, 2),
         "g100": ("g100_05_k0", 100, 0, 0)}
FILE_SEED = {"half": 0, "fh1s": 0, "g1s1": 1, "g1s2": 2, "g100": 0}
with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as _f:
    _P = json.load(_f)
ENV = {"PD_PACE_MEAN": repr(_P["v_mean"]), "PD_PACE_SD": repr(_P["v_sd"]), "PD_CLEAN_NOCACHE": "1",
       "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
       "PYTHONPATH": REPO}
INPROC = J(HERE, "inproc.py")
LOGS = J(HERE, "logs")


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(LOGS, "build.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def env_of(cell: str, head: str = "half", step: str = "decode", **extra) -> dict:
    from pipeline.constrained import pd_cells as P
    c = P.cfg(cell, "decode" if step == "decode" else None)
    return dict(P.env_for(c, head, step), **ENV, **extra)


def prep(rot: str) -> int:
    from pipeline.constrained import pd_cells as P
    cell, old_cell = reg.CELLS[rot], reg.OLD[rot]
    c, old = P.cfg(cell), P.cfg(old_cell)
    assert c["heads_tag"] == old["heads_tag"] and c["train"] == old["train"] and c["test"] == old["test"], cell
    os.makedirs(c["base"], exist_ok=True)
    # the 1 s feature caches were deleted (6 Oct cleanup) and these cells never train: do_view only links the 1 s
    # training folders to them, so they are made empty here and stay unused (as for the shipped f05 cells)
    for sub in ("features", "rssi_full"):
        os.makedirs(J(c["shared10"], sub), exist_ok=True)
    P.do_view(c)
    P.do_shared_models(c, P.SHARED_MODELS[cell])
    # the start-of-walk readers: pd_cells.do_readers copies them from the d1sp twin, whose tree was removed in the
    # 6 Oct cleanup, so they come from d4c_fuse, which holds that copy (alias <twin tag>V0) byte for byte
    alias = P.cfg(cell, "readers")["reader_tag"]
    assert alias == P.twin_tag(cell) + "V0", alias
    nr = 0
    for sub in ("models", "posteriors"):
        for f in sorted(glob.glob(J(old["tree"]("half"), sub, f"{alias}_*"))):
            dst = J(c["tree"]("half"), sub, os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
            assert sha(f) == sha(dst), dst
            nr += 1
    assert nr == 7, f"{cell}: {nr} reader files under {alias} in {old_cell}"
    say(f"{cell}: readers {alias} (6 networks, 1 posterior file) copied from {old_cell}")
    n = 0
    for sub in ("models", "posteriors"):
        for f in sorted(glob.glob(J(old["tree"]("half"), sub, "s0?_to_s0?_*"))):
            dst = J(c["tree"]("half"), sub, os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
                n += 1
            assert sha(f) == sha(dst), dst
    say(f"{cell}: {n} Room A reader-row files copied from {old_cell}")
    with open(J(LOGS, f"crossfit_{rot}.log"), "a", encoding="utf-8") as log:
        code = subprocess.call([sys.executable, INPROC, "pd_clean", "crossfit", "--cell", cell], cwd=REPO,
                               env=env_of(cell), stdout=log, stderr=subprocess.STDOUT)
    say(f"{cell}: crossfit exit {code}")
    return code


def rows(d3: str) -> dict:
    dec = json.load(open(J(d3, "decode.json")))
    (b,) = list(dec["sessions"])
    sl = {r["key"]: r for r in json.load(open(J(d3, "scorerlock.json")))["sessions"][b]["rows"]["A"]}
    return {r["key"]: (r["final_line"], sl[r["key"]]["display_lock"], sl[r["key"]].get("scorer_lock"))
            for r in dec["sessions"][b]["rows"]["A"]}


def _decode(rot: str, prefix: str) -> int:
    cell = reg.CELLS[rot]
    stage = J(HERE, "stage", prefix, cell)
    with open(J(LOGS, f"decode_{prefix}_{rot}.log"), "a", encoding="utf-8") as log:
        return subprocess.call(["nice", "-n", "10", sys.executable, INPROC, "pd_clean", "decode", "--cell", cell,
                                "--variants", VARIANT], cwd=REPO,
                               env=env_of(cell, PD_CLEAN_PREFIX=prefix, PD_CLEAN_STAGE=stage),
                               stdout=log, stderr=subprocess.STDOUT)


def plumb(rot: str) -> int:
    from pipeline.constrained import pd_cells as P
    cell, old_cell = reg.CELLS[rot], reg.OLD[rot]
    c, old = P.cfg(cell), P.cfg(old_cell)
    assert not os.path.exists(J(c["base"], "SWAPPED_0p5.json")), f"{cell}: swapped already; the plumbing is before"
    for h in c["heads"]:
        for f in glob.glob(J(old["tree"](h), "posteriors", f"{c['heads_tag']}_*_full.npz")):
            dst = J(c["tree"](h), "posteriors", os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
            assert sha(f) == sha(dst), dst
    t0 = time.time()
    code = _decode(rot, "PL")
    if code:
        say(f"{cell}: plumbing decode exit {code}")
        return 1
    a = rows(J(c["base"], "d3", f"PL.{VARIANT}"))
    b = rows(J(old["base"], "d3", f"DT0.{VARIANT}"))
    diff = [k for k in b if a.get(k) != b[k]]
    res = {"cell": cell, "against": f"{old_cell}/d3/DT0.{VARIANT}", "n": len(b), "n_new": len(a),
           "differ": diff[:20], "EXACT": not diff and len(a) == len(b) == 120,
           "minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(J(LOGS, f"plumb_{rot}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    say(f"{cell}: plumbing {'EXACT' if res['EXACT'] else 'FAILED'} ({len(diff)} of {len(b)} rows differ, "
        f"{res['minutes']} min)")
    return 0 if res["EXACT"] else 1


def swap(rot: str) -> int:
    from pipeline.constrained import pd_cells as P
    cell = reg.CELLS[rot]
    c = P.cfg(cell)
    out = J(c["base"], "SWAPPED_0p5.json")
    if os.path.exists(out):
        say(f"{cell}: swapped already")
        return 0
    done = {}
    for slot, (net, cells, seed, fs) in SLOTS.items():
        for li in range(3):
            src = J(ABL, rot, net, "art", "models", f"{c['heads_tag']}_g{cells}_e24_s{seed}_link{li}.pt")
            dst = J(c["tree"](slot), "models", f"{c['heads_tag']}_g{cells}_e24_s{fs}_link{li}.pt")
            assert os.path.exists(src) and os.path.exists(dst), (src, dst)
            assert sha(src) != sha(dst), f"{dst}: the new network equals the old one"
            shutil.copy2(src, dst)
            assert sha(src) == sha(dst), dst
            done[os.path.relpath(dst, REPO)] = {"from": os.path.relpath(src, REPO), "sha256": sha(dst)}
        post, keep = J(c["tree"](slot), "posteriors"), J(c["tree"](slot), "posteriors_plumb")
        os.makedirs(keep, exist_ok=True)
        for f in glob.glob(J(post, f"{c['heads_tag']}_*_full.npz")):
            shutil.move(f, J(keep, os.path.basename(f)))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"cell": cell, "slots": list(SLOTS), "files": done, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "note": "half is unchanged; the fh1s slot's file s0 holds the network trained with seed 3 "
                           "(ALL05 seed set 0 of the stride ablation)"}, f, indent=1)
    say(f"{cell}: {len(done)} slot files swapped")
    return 0


def infer(rot: str) -> int:
    sys.path.insert(0, J(REPO, "runs", "ship_0p5_2026-10-08"))
    from run_train import footprint_gb, free_pct
    from pipeline.constrained import pd_cells as P
    cell = reg.CELLS[rot]
    c = P.cfg(cell)
    assert os.path.exists(J(c["base"], "SWAPPED_0p5.json")), f"{cell}: not swapped"
    for h in c["heads"]:
        out = J(c["tree"](h), "posteriors", f"{c['heads_tag']}_g{100 if h == 'g100' else 25}_e24_s{FILE_SEED[h]}_full.npz")
        if os.path.exists(out):
            say(f"{cell} infer {h}: posteriors present ({'unchanged head' if h == 'half' else 'already inferred'})")
            continue
        env = dict(P.env_for(c, h, "infer"), PYTHONPATH=REPO, OMP_NUM_THREADS="1",
                   PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
        with open(J(LOGS, f"infer_{rot}.log"), "a", encoding="utf-8") as log:
            p = subprocess.Popen([sys.executable, INPROC, "pd_cells", "infer", "--cell", cell, "--head", h], cwd=REPO,
                                 env=env, stdout=log, stderr=subprocess.STDOUT)
            t0, peak = time.time(), 0.0
            while p.poll() is None:
                fr, gb = free_pct(), footprint_gb(p.pid)
                peak = max(peak, gb)
                if fr < 15 or gb > 14:
                    p.kill()
                    say(f"KILLED {cell} infer {h}: free {fr} %, footprint {gb:.1f} GB; stopping")
                    return 3
                time.sleep(5)
        if p.returncode or not os.path.exists(out):
            say(f"FAILED {cell} infer {h} (exit {p.returncode}); see logs/infer_{rot}.log")
            return p.returncode or 1
        say(f"{cell} infer {h}: done in {(time.time() - t0) / 60:.1f} min, peak {peak:.1f} GB")
    return 0


def ref(rot: str) -> int:
    from pipeline.constrained import pd_cells as P
    cell = reg.CELLS[rot]
    c = P.cfg(cell)
    for h in c["heads"]:
        assert os.path.exists(J(c["tree"](h), "posteriors", f"{c['heads_tag']}_g{100 if h == 'g100' else 25}_e24_s"
                                f"{FILE_SEED[h]}_full.npz")), (cell, h)
    t0 = time.time()
    code = _decode(rot, "D05")
    d = J(c["base"], "d3", f"D05.{VARIANT}")
    if code or not os.path.exists(J(d, "decode.json")):
        say(f"{cell}: D05 decode exit {code}")
        return code or 1
    a, b = rows(d), rows(J(P.cfg(reg.OLD[rot])["base"], "d3", f"DT0.{VARIANT}"))
    dj = json.load(open(J(d, "decode.json")))
    (b1,) = list(dj["sessions"])
    true = {r["key"]: r["true"] for r in dj["sessions"][b1]["rows"]["A"]}
    pct = lambda i, rr: round(100.0 * sum(rr[k][i] == true[k] for k in true) / len(true), 2)  # noqa: E731
    res = {"cell": cell, "n": len(a), "minutes": round((time.time() - t0) / 60.0, 2),
           "new_heads": {"committed": pct(0, a), "lock": pct(1, a)}, "old_heads_DT0": {"committed": pct(0, b),
                                                                                       "lock": pct(1, b)}}
    with open(J(LOGS, f"ref_{rot}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    say(f"{cell}: D05 reference decoded: {res}")
    return 0


if __name__ == "__main__":
    os.makedirs(LOGS, exist_ok=True)
    cmd, rot = sys.argv[1], sys.argv[2]
    assert rot in reg.CELLS, rot
    sys.exit({"prep": prep, "plumb": plumb, "swap": swap, "infer": infer, "ref": ref}[cmd](rot) or 0)
