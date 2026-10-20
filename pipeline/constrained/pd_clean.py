# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Pd_clean: the start-of-walk reader leak and its fix.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
VERIFY = J(RES, "verify")
SHIPPED_HALF = J(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_half")
SOURCES = {("01",): (SHIPPED_HALF, "s01_to_s02"), ("02",): (SHIPPED_HALF, "s02_to_s01"),
           ("01", "02"): (SHIPPED_HALF, "s0102_to_s03"),
           ("B1",): (J(RES, "cells", "3a", "art_half"), "sB1_to_sB2")}
PREFIX = os.environ.get("PD_CLEAN_PREFIX", "CR")
E_REG, E_POST = 20, 24


# The training sessions a tag names: s<training>_to_s<test>[V0], two characters per session.
def tag_train(tag: str) -> tuple:
    tr = tag[1:].split("_to_")[0]
    return tuple(tr[i:i + 2] for i in range(0, len(tr), 2))


# Function sha.
def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# Nets.device() takes the Apple GPU when it exists; the GPU belongs to Identification.
def force_cpu() -> None:
    import torch
    torch.backends.mps.is_available = lambda: False


# {training session: the reader tag it had, its training sessions, and the clean tag}.
def plan_for(c: dict, tag_for_session) -> dict:
    out = {}
    for s in c["train"]:
        t = tag_for_session(s)
        trn = tag_train(t)
        others = tuple(x for x in c["train"] if x != s)
        row = {"orig": t, "orig_train": list(trn), "others": list(others)}
        if set(trn) <= set(others):
            row.update({"clean": t, "clean_train": list(trn), "changed": False})
        else:
            src = SOURCES.get(others)
            if src is None:
                raise SystemExit(f"{c['cell']}: no clean source trained on exactly {others} for {s}")
            row.update({"clean": f"s{''.join(others)}_to_s{s}", "clean_train": list(others), "changed": True,
                        "src_tree": os.path.relpath(src[0], REPO_ROOT), "src_tag": src[1]})
        out[s] = row
    return out


# Function test side.
def test_side(c: dict) -> dict:
    t = c["reader_tag"]
    return {"session": c["test"], "tag": t, "train": list(tag_train(t.replace("V0", ""))),
            "clean": set(tag_train(t.replace("V0", ""))) <= set(c["train"])}



# The pace prior from PD_PACE_MEAN and PD_PACE_SD, set in every module that holds a copy (common, decoder...
def apply_pace() -> dict:
    mu, sd = os.environ.get("PD_PACE_MEAN"), os.environ.get("PD_PACE_SD")
    if not mu or not sd:
        return None
    import pipeline.constrained.bout as BO
    import pipeline.constrained.common as C
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    mu, sd = float(mu), float(sd)
    C.V_MEAN, C.V_SD = mu, sd
    D.V_MEAN, D.V_SD = mu, sd
    D2.V_MEAN = mu
    BO.V_MEAN = mu
    D2._LT_CACHE.clear()
    return {"v_mean": mu, "v_sd": sd, "set_in": ["common", "decoder", "decoder2", "bout"],
            "source": "A1+A2 tape anchors (stage1_pace's method), Uzayr 29 Sep"}



SUPPORTED_PARTS = {"relgate", "relgate_a", "relgate_up", "abstain", "a2w"}


# Pd_decode.parse, refusing anything the downstream tools do not reproduce.
def variant_spec(variant: str) -> dict:
    from pipeline.constrained.pd_decode import parse
    v = parse(variant)
    default = parse("ref")
    extra = [k for k in v if v[k] != default[k] and k not in SUPPORTED_PARTS]
    if extra:
        raise SystemExit(f"variant {variant!r}: {extra} are not reproduced by the downstream tools")
    assert v["relgate"] and v["relgate_a"] and v["relgate_up"], f"variant {variant!r} is not relgateU-based"
    return v


# (a2, committed start term), exactly as pd_decode.inner builds them for this variant: the A2 term at the...
def start_terms_for(variant: str, c: dict, te: tuple, st, kte, proba, classes):
    from pipeline.constrained import dc2_run as R
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.u2_useit import merged, term_abstain, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
    v = variant_spec(variant)
    a2 = start_terms(c["train"], te, st, v["a2w"] if v["a2w"] is not None else A2_WEIGHT)
    if v["abstain"]:
        term, _cov = term_abstain(kte, proba, classes, st, R.ABSTAIN_THR, R.ABSTAIN_W)
    else:
        term = term_veto(kte, proba, classes, st, VETO_THR, VETO_W)
    return a2, merged(dict(a2), term)



# Function bound.
def _bound(cell: str):
    from pipeline.constrained import dc2b
    dc2b.install()
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    from pipeline.constrained import dc2_run as R
    R._bind(c)
    from pipeline.constrained.t2_embed import tag_for_session
    return PC, c, tag_for_session


# Dc2_run.do_infer's posterior file, for heads src_tag applied to one session's recordings.
def build_block_file(c: dict, session: str, src_tree: str, src_tag: str, out: str) -> dict:
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.recordings import session_recordings
    models = [_load(J(src_tree, "models", f"{src_tag}_g25_e{E_POST}_s0_link{li}.pt")) for li in range(3)]
    pos = [_load(J(src_tree, "models", f"{src_tag}_pos2_e{E_REG}_s0_link{li}.pt")) for li in range(3)]
    flat, stems = {}, []
    for _s, stem in session_recordings(session):
        fp = J(c["shared"], "features", f"session_{session}_{stem}.npy")
        assert os.path.exists(fp), f"features not built for {session}/{stem}"
        prob, per_link, rec = infer_recording(models, session, stem, "g")
        block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                 "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                 "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10"), "xy": rec.xy,
                 "participant": np.array([rec.participant] * len(rec), dtype="U16")}
        xh, xl = infer_recording(pos, session, stem, "pos")[:2]
        block["xy_hat"] = xh.astype(np.float32)
        block["xy_hat_link"] = xl.astype(np.float32)
        for k, v in block.items():
            flat[f"{stem}::{k}"] = v
        stems.append(stem)
    flat["__stems__"] = np.array(sorted(stems), dtype="U64")
    np.savez_compressed(out + ".tmp.npz", **flat)
    os.replace(out + ".tmp.npz", out)
    return {"session": session, "recordings": sorted(stems), "file": os.path.relpath(out, REPO_ROOT)}


# Function crossfit inner.
def crossfit_inner(cell: str, plumb: bool) -> int:
    force_cpu()
    PC, c, tfs = _bound(cell)
    plan = plan_for(c, tfs)
    tree = c["tree"]("half")
    done = {"cell": cell, "plan": plan, "built": {}, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if plumb:
        ref = J(tree, "posteriors", f"s010203_to_sB1_g25_e{E_POST}_s0_full.npz")
        out = J(VERIFY, "crossfit_plumb_s010203_to_sB1.npz")
        os.makedirs(VERIFY, exist_ok=True)
        if not os.path.exists(out):
            build_block_file(c, "B1", tree, "s010203_to_sB1", out)
        from pipeline.constrained.artefacts import read_full_posteriors
        a, b = read_full_posteriors(ref), read_full_posteriors(out)
        res = {"stems_reference": sorted(a), "stems_rebuilt": sorted(b), "only_in_reference": sorted(set(a) - set(b)),
               "only_rebuilt": sorted(set(b) - set(a)), "max_abs_diff": {}, "argmax_equal": {}}
        for stem in sorted(set(a) & set(b)):
            for k in ("prob", "xy_hat", "xy_hat_link", "per_link"):
                d = float(np.max(np.abs(a[stem][k].astype(float) - b[stem][k].astype(float))))
                res["max_abs_diff"][k] = max(res["max_abs_diff"].get(k, 0.0), d)
            res["argmax_equal"][stem] = float(np.mean(a[stem]["prob"].argmax(1) == b[stem]["prob"].argmax(1)))
        with open(J(VERIFY, "crossfit_plumb.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
        print("CROSSFIT PLUMB", json.dumps(res), flush=True)
        return 0
    from pipeline.constrained.recordings import session_recordings
    for s, p in plan.items():
        if not p["changed"]:
            continue
        new, src_tree, src_tag = p["clean"], J(REPO_ROOT, p["src_tree"]), p["src_tag"]
        files = {}
        for kind, n, ep in (("g", 25, E_POST), ("pos", 2, E_REG)):
            for li in range(3):
                a = J(src_tree, "models", f"{src_tag}_{kind}{n}_e{ep}_s0_link{li}.pt")
                d = J(tree, "models", f"{new}_{kind}{n}_e{ep}_s0_link{li}.pt")
                if os.path.exists(d):
                    assert sha(a) == sha(d), f"{d} exists and differs from its source {a}"
                else:
                    shutil.copy2(a, d)
                files[os.path.basename(d)] = sha(d)[:16]
        caches = sorted(os.path.realpath(J(c["shared"], "features", f"session_{s}_{stem}.npy"))
                        for _s, stem in session_recordings(s))
        store = J(RES, "clean_readers")
        os.makedirs(store, exist_ok=True)
        sp, sj = J(store, f"{new}_g25_e{E_POST}_s0_full.npz"), J(store, f"{new}.json")
        if not os.path.exists(sp):
            info = build_block_file(c, s, src_tree, src_tag, sp)
            info.update({"src_tree": p["src_tree"], "src_tag": src_tag, "feature_caches": caches,
                         "built_in_cell": cell, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "sha256": sha(sp)})
            with open(sj, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=1)
        with open(sj, encoding="utf-8") as f:
            info = json.load(f)
        assert info["feature_caches"] == caches, f"{cell}: {s}'s window caches differ from the store's"
        assert (info["src_tree"], info["src_tag"]) == (p["src_tree"], src_tag), (info["src_tag"], src_tag)
        out = J(tree, "posteriors", f"{new}_g25_e{E_POST}_s0_full.npz")
        if os.path.exists(out):
            assert sha(out) == info["sha256"], f"{out} exists and differs from the store"
        else:
            shutil.copy2(sp, out)
        info = {"file": os.path.relpath(out, REPO_ROOT), "from_store": os.path.relpath(sp, REPO_ROOT),
                "models": files, "posterior_sha256_16": sha(out)[:16]}
        done["built"][s] = info
        print(f"[{time.strftime('%H:%M:%S')}] {cell}: {s} rows from {src_tag} as {new}", flush=True)
    with open(J(c["base"], "crossfit.json"), "w", encoding="utf-8") as f:
        json.dump(done, f, indent=1)
    return 0


# {(stem, pass): (committed, display lock, scorer lock)} from a decode folder (or a cell base).
def _rows(d: str) -> dict:
    with open(J(d, "decode.json"), encoding="utf-8") as f:
        dj = json.load(f)
    with open(J(d, "scorerlock.json"), encoding="utf-8") as f:
        sj = json.load(f)
    (b,) = list(dj["sessions"])
    com = {(r["stem"], int(r["pass_id"])): r["final_line"] for r in dj["sessions"][b]["rows"]["A"]}
    lk = {(r["stem"], int(r["pass_id"])): (r["display_lock"], r["scorer_lock"])
          for r in sj["sessions"][b]["rows"]["A"]}
    return {k: (com.get(k), *(lk.get(k) or (None, None))) for k in set(com) | set(lk)}


# Function compare.
def compare(new_dir: str, ref_dir: str) -> dict:
    a, b = _rows(new_dir), _rows(ref_dir)
    keys = sorted(set(a) | set(b))
    diff = [k for k in keys if a.get(k) != b.get(k)]
    return {"n": len(keys), "ref": os.path.relpath(ref_dir, REPO_ROOT),
            "committed_changed": sum(1 for k in keys if (a.get(k) or (None,))[0] != (b.get(k) or (None,))[0]),
            "display_lock_changed": sum(1 for k in keys if (a.get(k) or (0, None))[1] != (b.get(k) or (0, None))[1]),
            "scorer_lock_changed": sum(1 for k in keys if (a.get(k) or (0, 0, None))[2] != (b.get(k) or (0, 0, None))[2]),
            "EXACT": not diff, "first_differences": [list(map(str, k)) for k in diff[:10]]}


# Function ref dir of.
def ref_dir_of(base: str, variant: str):
    d = J(base, "d3", variant)
    if os.path.exists(J(d, "decode.json")):
        return d
    if variant == "ref" and os.path.exists(J(base, "decode.json")):
        return base
    return None


# The start-of-walk readers depend only on the training and test sessions, the reader map and the reader...
def install_reader_cache(c: dict, tmap: dict, tag_for_session) -> str:
    import pickle
    import pipeline.constrained.q4_arms as Q4
    import pipeline.constrained.u1_adapt as U1
    tree = c["tree"]("half")
    files = []
    for s in list(c["train"]) + [c["test"]]:
        t = tag_for_session(s)
        files += [J(tree, "models", f"{t}_g25_e{E_POST}_s0_link{li}.pt") for li in range(3)]
        files.append(J(tree, "posteriors", f"{t}_g25_e{E_POST}_s0_full.npz"))
    h = hashlib.sha256(json.dumps([list(c["train"]), c["test"], {k: tmap[k] for k in sorted(tmap)}]).encode())
    for f in files:
        h.update(sha(f).encode())
    path = J(VERIFY, "reader_cache", f"{c['test']}_{''.join(c['train'])}_{h.hexdigest()[:16]}.pkl")
    store = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            store = pickle.load(f)
    o_rows, o_a2 = U1.session_rows, Q4.start_terms

    # Function save.
    def save():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "wb") as f:
            pickle.dump(store, f)
        os.replace(path + ".tmp", path)

    # Function session rows.
    def session_rows(sessions, st, mode, cache):
        k = ("rows", tuple(sessions), mode)
        if k not in store:
            store[k] = o_rows(sessions, st, mode, cache)
            save()
        return store[k]

    # Function start terms.
    def start_terms(tr_s, te_s, st, weight):
        k = ("a2", tuple(tr_s), tuple(te_s), float(weight))
        if k not in store:
            store[k] = o_a2(tr_s, te_s, st, weight)
            save()
        return store[k]
    U1.session_rows, Q4.start_terms = session_rows, start_terms
    return os.path.relpath(path, REPO_ROOT) + (" (read)" if store else " (fitted)")


# Function decode inner.
def decode_inner(cell: str, variants: list, own: bool) -> int:
    opened = {}

    # Function hook.
    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes)):
            p = os.fsdecode(args[0])
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"
            if p.endswith((".py", ".pyc")) or "/site-packages/" in p or p.startswith("/opt/"):
                return
            opened.setdefault(p, set()).add(mode)
    sys.addaudithook(hook)
    force_cpu()
    PC, c0, tfs = _bound(cell)
    plan = plan_for(c0, tfs)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    changed = {s: p for s, p in plan.items() if p["changed"]}
    stage = J(os.environ.get("PD_CLEAN_STAGE") or VERIFY, "own" if own else "clean", cell)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    meta = {"cell": cell, "variants": variants, "own": own, "plan": plan, "test_side_reader": test_side(c0),
            "tag_map_before": tmap, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "device": "cpu (forced)"}
    if not own and not changed:
        meta["map_unchanged"] = True
        fresh = [v for v in variants if not ref_dir_of(c0["base"], v)]
        variants = [v for v in variants if v not in fresh]
        for v in variants:
            src = ref_dir_of(c0["base"], v)
            dst = J(c0["base"], "d3", f"{PREFIX}.{v}")
            if os.path.exists(dst):
                raise SystemExit(f"REFUSING to overwrite {dst}")
            os.makedirs(dst)
            for n in ("decode.json", "scorerlock.json"):
                shutil.copy2(J(src, n), J(dst, n))
            with open(J(dst, "clean.json"), "w", encoding="utf-8") as f:
                json.dump({**meta, "copied_from": os.path.relpath(src, REPO_ROOT)}, f, indent=1)
            print(f"{cell} {PREFIX}.{v}: map already clean, copied from {os.path.relpath(src, REPO_ROOT)}", flush=True)
        if not fresh:
            return 0
        variants = fresh
        meta["variants"] = variants
    if not own:
        tree = c0["tree"]("half")
        for s, p in changed.items():
            need = [J(tree, "posteriors", f"{p['clean']}_g25_e{E_POST}_s0_full.npz")] + \
                   [J(tree, "models", f"{p['clean']}_g25_e{E_POST}_s0_link{li}.pt") for li in range(3)]
            miss = [x for x in need if not os.path.exists(x)]
            if miss:
                raise SystemExit(f"{cell}: run crossfit first; missing {miss}")
            tmap[s] = p["clean"]
        os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
        assert all(tfs(s) == plan[s]["clean"] for s in plan), "the clean map did not take"
    meta["tag_map_used"] = tmap
    meta["pace"] = apply_pace()
    if os.environ.get("PD_CLEAN_NOCACHE") != "1":
        meta["reader_cache"] = install_reader_cache(c0, tmap, tfs)
    orig_cfg = PC.cfg

    # Function cfg.
    def cfg(cell_, cmd=None):
        c_ = orig_cfg(cell_, cmd)
        return dict(c_, base=stage) if cell_ == cell else c_
    PC.cfg = cfg
    import pipeline.constrained.pd_decode as PD
    PD.plumb = lambda *a, **k: None
    code = PD.inner(cell, variants)
    PC.cfg = orig_cfg
    if code:
        raise SystemExit(f"{cell}: pd_decode.inner returned {code}")
    res = {}
    for v in variants:
        ref = ref_dir_of(c0["base"], v)
        res[v] = compare(J(stage, "d3", v), ref) if ref else {"ref": None}
        print(f"{cell} {v}: against the record {res[v]}", flush=True)
    meta["against_record"] = res
    meta["files_opened"] = {os.path.relpath(p, REPO_ROOT) if p.startswith(REPO_ROOT) else p: sorted(m)
                            for p, m in sorted(opened.items())}
    with open(J(stage, "clean.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    if own:
        bad = {v: r for v, r in res.items() if r.get("ref") and not r["EXACT"]}
        if bad:
            raise SystemExit(f"{cell}: the reproduction FAILED: {bad}")
        return 0
    for v in variants:
        dst = J(c0["base"], "d3", f"{PREFIX}.{v}")
        if os.path.exists(dst):
            raise SystemExit(f"REFUSING to overwrite {dst}")
        shutil.copytree(J(stage, "d3", v), dst)
        shutil.copy2(J(stage, "clean.json"), J(dst, "clean.json"))
    return 0



# What a file opened by a decode is, what it was trained or fitted on, and whether that is only the cell's...
def classify(path: str, cell_train: tuple) -> dict:
    real = os.path.realpath(path if os.path.isabs(path) else J(REPO_ROOT, path))
    rel = os.path.relpath(real, REPO_ROOT)
    base = os.path.basename(rel)
    row = {"file": path, "real": rel}
    if base.endswith(".pt") and "_to_s" in base:
        t = base.split("_g")[0].split("_pos")[0]
        row.update({"kind": "network weights", "tag": t, "trained_on": list(tag_train(t.replace("V0", "")))})
    elif base.endswith("_full.npz") and "_to_s" in base:
        t = base.split("_g")[0]
        row.update({"kind": "network outputs (posteriors)", "tag": t, "trained_on": list(tag_train(t.replace("V0", "")))})
    elif ".gt.json" in base or "/data/" in f"/{rel}":
        row.update({"kind": "ground truth / raw data"})
    elif "/features/" in rel or "/rssi_full/" in rel or "/windows/" in rel or "/win05/" in rel:
        row.update({"kind": "window cache"})
    elif base.endswith(".json"):
        row.update({"kind": "stored result or statistics"})
    else:
        row.update({"kind": "other"})
    if "trained_on" in row:
        row["outside_training"] = sorted(set(row["trained_on"]) - set(cell_train))
    return row


# Function audit.
def audit(dirs: list) -> dict:
    out = {}
    for d in dirs:
        with open(J(d, "clean.json"), encoding="utf-8") as f:
            m = json.load(f)
        from pipeline.constrained import pd_cells as PC
        tr = PC.cfg(m["cell"])["train"]
        rows = [classify(p, tr) for p in m["files_opened"]]
        nets = {}
        for r in rows:
            if "tag" in r:
                k = (r["tag"], r["kind"])
                nets.setdefault(k, {"tag": r["tag"], "kind": r["kind"], "trained_on": r["trained_on"],
                                    "outside_training": r["outside_training"], "files": 0})
                nets[k]["files"] += 1
        kinds = {}
        for r in rows:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        out[m["cell"]] = {"train": list(tr), "own_map": m["own"], "files_opened": len(rows), "by_kind": kinds,
                          "networks": sorted(nets.values(), key=lambda x: (x["kind"], x["tag"])),
                          "stored_results": sorted({r["real"] for r in rows if r["kind"] == "stored result or statistics"}),
                          "LEAK": sorted({x["tag"] for x in nets.values() if x["outside_training"]})}
    return out



LADDER = (("D0 baseline: the pooled per-link recipe, shipped decode", "d1sp", "d1sp@CR.ref"),
          ("+ D2 augmentation + relative RSSI", "d2pc_ar", "d2pc_ar@CR.ref"),
          ("+ D3 relative motion gate", "d2pc_ar@relgateU", "d2pc_ar@CR.relgateU"),
          ("+ D4 shared encoder, learned fusion", "d4c_fuse@relgateU", "d4c_fuse@CR.relgateU"))


# The ablation ladder on the rotations (display lock, configuration A), before and with the clean readers...
def ladder() -> dict:
    from pipeline.constrained import pd_rule as R
    out = {}
    for which, k in (("before", 1), ("clean", 2)):
        rows, prev = [], None
        for step in LADDER:
            src = step[k]
            S = R.summarise(R.rot_rows(src, "display"))
            row = {"step": step[0], "source": src, "objective": S["objective"],
                   "rotations": {nm: [v["committed"], v["lock"]] for nm, v in S["rotations"].items()},
                   "pooled_edges": S.get("pooled_edges")}
            if prev is not None:
                o = R.compare(f"LADDER_{which}", prev, src, "display")
                row["paired_gain"] = [o["paired"]["gain"]] + list(o["paired"]["ci95"])
                row["guard_holds"], row["ADOPT"] = o["guard"]["holds"], o["ADOPT"]
            rows.append(row)
            prev = src
        o = R.compare(f"LADDER_{which}_total", LADDER[0][k], LADDER[-1][k], "display")
        out[which] = {"rows": rows, "total_gain": [o["paired"]["gain"]] + list(o["paired"]["ci95"])}
    with open(J(RES, "rule", "CR_LADDER.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    L = ["# The ablation ladder on the rotations, before and with the clean start-of-walk readers", "",
         "Display lock, configuration A; objective = weighted mean of committed + lock (B1 x2); each gain against the "
         "step before, paired, 95 percent interval.", "",
         "| step | objective before | objective clean | gain before | gain clean | clean B1 c/l | clean A2 c/l | clean A1 c/l |",
         "|---|---|---|---|---|---|---|---|"]
    for rb, rc in zip(out["before"]["rows"], out["clean"]["rows"]):
        g = lambda r: "" if "paired_gain" not in r else f"{r['paired_gain'][0]:+.2f} [{r['paired_gain'][1]:.2f}, {r['paired_gain'][2]:.2f}]"
        rot = lambda r, nm: "/".join(f"{x:.2f}" for x in r["rotations"].get(nm, []))
        L.append(f"| {rc['step']} | {rb['objective']:.2f} | {rc['objective']:.2f} | {g(rb)} | {g(rc)} | "
                 f"{rot(rc, 'B1')} | {rot(rc, 'A2')} | {rot(rc, 'A1')} |")
    tb, tc = out["before"]["total_gain"], out["clean"]["total_gain"]
    L += ["", f"D0 to final: before {tb[0]:+.2f} [{tb[1]:.2f}, {tb[2]:.2f}]; clean {tc[0]:+.2f} [{tc[1]:.2f}, {tc[2]:.2f}].", ""]
    with open(J(RES, "rule", "CR_LADDER.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("\n".join(L))
    return out



# Function outer.
def _outer(cmd: str, cell: str, extra: list) -> int:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_clean", cmd, "--inner", "--cell", cell,
                            *extra], cwd=REPO_ROOT, env=env)


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "crossfit", "decode", "audit", "ladder"])
    ap.add_argument("--cell")
    ap.add_argument("--variants", nargs="+", default=["ref"])
    ap.add_argument("--own", action="store_true")
    ap.add_argument("--plumb", action="store_true")
    ap.add_argument("--dirs", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "ladder":
        sys.path.insert(0, REPO_ROOT)
        ladder()
        return 0
    if a.cmd == "audit":
        res = audit(a.dirs)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=1)
        print(json.dumps({k: {"LEAK": v["LEAK"], "networks": [(n["tag"], n["trained_on"]) for n in v["networks"]]}
                          for k, v in res.items()}, indent=1))
        return 0
    if not a.inner:
        extra = []
        if a.cmd == "decode":
            extra = ["--variants", *a.variants] + (["--own"] if a.own else [])
        if a.cmd == "crossfit" and a.plumb:
            extra = ["--plumb"]
        return _outer(a.cmd, a.cell, extra)
    if a.cmd == "plan":
        force_cpu()
        _PC, c, tfs = _bound(a.cell)
        print(json.dumps({"cell": a.cell, "train": c["train"], "plan": plan_for(c, tfs), "test_side": test_side(c)},
                         indent=1))
        return 0
    if a.cmd == "crossfit":
        return crossfit_inner(a.cell, a.plumb)
    return decode_inner(a.cell, a.variants, a.own)


if __name__ == "__main__":
    sys.exit(main())
