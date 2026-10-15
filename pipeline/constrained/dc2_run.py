"""DC2: THE ROOM B RUN, END TO END. Called by `dc2_pipeline`, one subcommand per step.

Pre-registration `reports/PREREG_DC2_crossroom_2026-09-22.md`, section 10 (written 2026-09-23 before
any Room B data existed). The steps, each a separate process because each needs its own roots:

  view    a per-room VIEW directory of symlinks: Room A's training sessions beside the Room B
          sessions, for the raw data and for the windows, so every loader in the pipeline works
          unchanged and `data/` is never written. Room A sessions point at the ONE lattice.
  cut     the Room B sessions on the ONE lattice (press-aligned, `y4_pressalign.cut_one`)
  infer   one frozen head over the Room B windows, inference only (`--head`)
  decode  configurations A and B, and the two confirmatory arms, on the evaluated passes

EVERY TREE IS UNDER runs/constrained/dc2_<room>[_standin]_s0.5_pressalign/, named with the stride.

The stand-in (`--stand-in`) is Room A session 03 dressed as Room B session "B1", with heads trained on
sessions 01 and 02 and its first eight passes standing in for the calibration block. It is a
PLUMBING CHECK: its numbers are never results, and its decode is required to reproduce the SHIPPED
system's decisions on those passes exactly.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PA_WINDOWS = os.path.join(REPO_ROOT, "runs", "constrained", "windows_s0.5_pressalign", "room_A")
PA = lambda h: os.path.join(REPO_ROOT, "runs", f"artefacts_s0.5_pressalign_{h}")     # noqa: E731
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
#: Room A's pooled emission spread, the reference for the relative null. Computed 2026-09-23 BEFORE
#: any Room B data existed, on the shipped pool (mean fusion, ONE lattice) over the walking windows
#: of the three two-session pairings' test sessions, 3394 windows (per session 2.662, 1.795, 2.001).
S_A = 2.1108124982838437
#: THE EXPLORATORY PRODUCT-FUSION ARM (batch 23e item 4, frozen as TRACKING_FROZEN_2026-09-23e
#: before any Room B data): the per-link posteriors fused by log-linear blend w = 0.25 towards the
#: renormalised product (`fusion.py`), in EVERY head of the pool. S_A at the PRODUCT's scale, computed
#: exactly as S_A on the same 3394 Room A windows (the same code reproduces S_A to the last digit at
#: w = 0): per session 4.721, 3.093, 3.890.
EXPLORATORY_FUSION = {"B_prod0.25": 0.25}
S_A_BY_W = {0.0: S_A, 0.25: 3.7428177798574556}
#: arms whose fusion is fixed by the pre-registration and may NOT be changed by a flag
FIXED_MEAN_ARMS = ("A", "B", "B0", "B0_abstain")
NULL_ABS, THETA_ABS, NULL_GUARD_NATS = -7.50, 0.431, 3.0
ABSTAIN_THR, ABSTAIN_W = 0.90, 0.25        #: b_abstain_0.25, frozen 22c


def cfg_for(room: str, stand_in: bool) -> dict:
    # TDR_STANDIN_B1 / TDR_STANDIN_SUFFIX (batch 23e item 6): the stand-in's session may be a VIEW of
    # session 03 with extra receivers' files beside it, in its own base so no cache is reused
    sfx = os.environ.get("TDR_STANDIN_SUFFIX", "") if stand_in else ""
    base = os.path.join(REPO_ROOT, "runs", "constrained",
                        f"dc2_{room}{'_standin' if stand_in else ''}{sfx}_s0.5_pressalign")
    if stand_in:
        tr = ("01", "02")
        b = {"B1": os.environ.get("TDR_STANDIN_B1") or
             os.path.join(REPO_ROOT, "data", "room_A", "session_03")}
        heads_tag = "s0102_to_s03"
        # THE SHIPPED READERS' TAG for session 03. t2_embed.tag_for_session returns the FIRST
        # pairing that tests a session, so the shipped A2 term and veto reader read s01_to_s03's heads
        # for session 03 even inside s0102_to_s03. The stand-in reproduces that exactly.
        reader_tag = "s01_to_s03"
        src = {"half": PA("half"), "fh1s": PA("fh1s"), "g1s1": PA("g1s1"), "g1s2": PA("g1s2"),
               "g100": PA("g100")}
        manifest = os.path.join(REPO_ROOT, "runs", "constrained", "dc2_standin", "data", "room_B",
                                "calibration.json")
    else:
        tr = ("01", "02", "03")
        rdir = os.path.join(REPO_ROOT, "data", room)
        b = {os.path.basename(d).split("session_", 1)[1]: d
             for d in sorted(glob.glob(os.path.join(rdir, "session_*")))}
        heads_tag = "s010203_to_sB"
        reader_tag = heads_tag               # DC2: readers and pool on the same all-sessions heads
        src = {"half": os.path.join(REPO_ROOT, "runs", "artefacts_s0.5_pressalign_roomA3"),
               "fh1s": os.path.join(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s0"),
               "g1s1": os.path.join(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s1"),
               "g1s2": os.path.join(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_s2"),
               "g100": os.path.join(REPO_ROOT, "runs", "artefacts_s1.0_roomA3_g100")}
        manifest = os.path.join(rdir, "calibration.json")
    return {"base": base, "room": room, "stand_in": stand_in, "train": tr, "b_sessions": b,
            "heads_tag": heads_tag, "reader_tag": reader_tag, "model_src": src, "manifest": manifest,
            "data_view": os.path.join(base, "data"), "win_view": os.path.join(base, "windows"),
            "tree": lambda h: os.path.join(base, f"art_{h}"),
            "shared": os.path.join(base, "art_shared")}


HEADS = {"half": (25, 0), "fh1s": (25, 0), "g1s1": (25, 1), "g1s2": (25, 2), "g100": (100, 0)}


def _env(c, art):
    """The roots a DC2 subprocess runs under. Written out so no default can leak in."""
    return {"TDR_ROOM": c["room"], "TDR_DATA_ROOT": c["data_view"],
            "TDR_WINDOWS_ROOT": c["win_view"], "TDR_ART_DIR": art,
            "TDR_TEST_TAG_MAP": json.dumps({s: c["reader_tag"] for s in c["b_sessions"]})}


def _say(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ------------------------------------------------------------------------------------------ view

def do_view(c) -> int:
    room = c["room"]
    for root in (c["data_view"], c["win_view"]):
        os.makedirs(os.path.join(root, room), exist_ok=True)
    for s in c["train"]:
        for root, target in ((c["data_view"], os.path.join(REPO_ROOT, "data", "room_A", f"session_{s}")),
                             (c["win_view"], os.path.join(PA_WINDOWS, f"session_{s}"))):
            link = os.path.join(root, room, f"session_{s}")
            if not os.path.lexists(link):
                os.symlink(target, link)
    for b, raw in c["b_sessions"].items():
        link = os.path.join(c["data_view"], room, f"session_{b}")
        if not os.path.lexists(link):
            os.symlink(raw, link)
    if os.path.exists(c["manifest"]):
        shutil.copy2(c["manifest"], os.path.join(c["data_view"], room, "calibration.json"))
    # the shared features and rssi: Room A sessions linked file by file, Room B computed later
    for sub in ("features", "rssi_full"):
        d = os.path.join(c["shared"], sub)
        os.makedirs(d, exist_ok=True)
        for f in glob.glob(os.path.join(PA("shared"), sub, "session_0*")):
            if any(f"session_{s}_" in os.path.basename(f) for s in c["train"]):
                link = os.path.join(d, os.path.basename(f))
                if not os.path.lexists(link):
                    os.symlink(f, link)
    _say(f"view built at {c['base']}: train {c['train']}, Room B {sorted(c['b_sessions'])}")
    return 0


# ------------------------------------------------------------------------------------------- cut

def do_cut(c) -> int:
    import pipeline.io.windows as W
    from pipeline.constrained.y4_pressalign import cut_one
    rows = []
    for b, raw in c["b_sessions"].items():
        sdir = os.path.join(c["data_view"], c["room"], f"session_{b}")
        out = os.path.join(c["win_view"], c["room"], f"session_{b}")
        os.makedirs(out, exist_ok=True)
        cache = {}
        for stem in W.recordings_in(sdir):
            bdir = W.baseline_dir_for(sdir, stem)
            if bdir not in cache:
                cache[bdir] = W.session_baseline(bdir)
            r = cut_one(sdir, stem, cache[bdir], out)
            rows.append({"session": b, **r})
            _say(f"cut {b}/{stem}: {r['n']} windows, lo at press - 1 s on "
                 f"{r['passes_with_lo_at_press_minus_1s']} of {r['n_passes_sidecar']}")
    ok = all(r["passes_with_lo_at_press_minus_1s"] == r["n_passes_sidecar"]
             and r["max_press_to_nearest_start_s"] <= 1e-5 for r in rows)
    with open(os.path.join(c["base"], "cut.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "ALIGNED": ok}, f, indent=1)
    return 0 if ok and rows else 1


def do_features(c) -> int:
    """Room B features and RSSI, ONCE, before the heads run in parallel: five processes building the
    same cache file at once would race."""
    assert os.path.abspath(os.environ["TDR_ART_DIR"]) == os.path.abspath(c["shared"])
    from pipeline.constrained.recordings import build_feature_cache, load_meta, load_rssi, session_recordings
    for b in c["b_sessions"]:
        for _s, stem in session_recordings(b):
            build_feature_cache(b, stem)
            load_rssi(b, stem, load_meta(b, stem).t0_epoch)
            _say(f"features {b}/{stem}")
    return 0


# ----------------------------------------------------------------------------------------- infer

def do_infer(c, head: str) -> int:
    import numpy as np
    tree = c["tree"](head)
    assert os.path.abspath(os.environ["TDR_ART_DIR"]) == os.path.abspath(tree)
    os.makedirs(os.path.join(tree, "models"), exist_ok=True)
    os.makedirs(os.path.join(tree, "posteriors"), exist_ok=True)
    for sub in ("features", "rssi_full"):
        link = os.path.join(tree, sub)
        if not os.path.lexists(link):
            os.symlink(os.path.join(c["shared"], sub), link)
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.common import E_POST, E_REG
    from pipeline.constrained.recordings import session_recordings
    cells, seed = HEADS[head]
    tag = c["heads_tag"]
    jobs = [("g", cells, seed, E_POST)] + ([("pos", 2, 0, E_REG)] if head == "half" else [])
    for kind, n, sd, ep in jobs:
        for li in range(3):
            nm = f"{tag}_{kind}{n}_e{ep}_s{sd}_link{li}.pt"
            a = os.path.join(c["model_src"][head], "models", nm)
            if not os.path.exists(a):
                raise AssertionError(f"{head}: frozen weights missing, never trained here: {a}")
            dst = os.path.join(tree, "models", nm)
            if not os.path.exists(dst):
                shutil.copy2(a, dst)
    if head == "half":
        # the TRAINING side's A2 classifier and veto reader read Room A's cross-day tags: their
        # models and their posteriors (with the position head) on the ONE lattice, copied in
        # t2_embed.tag_for_session's rule, without importing t2_embed: its import-time guard
        # refuses this tree. Room A's pairings, then the DC2 override; the same answer by design.
        from pipeline.constrained.common import pairings, tag_of
        from pipeline.constrained.lattice import test_tag_override

        def tag_for_session(sess):
            over = test_tag_override(sess)
            if over:
                return over
            for tr_s, te_s in pairings():
                if te_s == (sess,) and tr_s != te_s:
                    return tag_of(tr_s, te_s, False)
            return None
        for s in c["train"]:
            t = tag_for_session(s)
            for f in glob.glob(os.path.join(PA("half"), "models", f"{t}_g25_e{E_POST}_s0_link*.pt")):
                if not os.path.exists(os.path.join(tree, "models", os.path.basename(f))):
                    shutil.copy2(f, os.path.join(tree, "models", os.path.basename(f)))
            pf = os.path.join(PA("half"), "posteriors", f"{t}_g25_e{E_POST}_s0_full.npz")
            if not os.path.exists(os.path.join(tree, "posteriors", os.path.basename(pf))):
                shutil.copy2(pf, os.path.join(tree, "posteriors", os.path.basename(pf)))
    tags = [tag] + ([c["reader_tag"]] if head == "half" and c["reader_tag"] != tag else [])
    for rt in tags[1:]:
        for kind, n, sd, ep in [("g", 25, 0, E_POST), ("pos", 2, 0, E_REG)]:
            for li in range(3):
                nm = f"{rt}_{kind}{n}_e{ep}_s{sd}_link{li}.pt"
                if not os.path.exists(os.path.join(tree, "models", nm)):
                    shutil.copy2(os.path.join(c["model_src"]["half"], "models", nm),
                                 os.path.join(tree, "models", nm))
    for tag, b in [(t_, b_) for t_ in tags for b_ in c["b_sessions"]]:
        out = os.path.join(tree, "posteriors", f"{tag}_g{cells}_e{E_POST}_s{seed}_full.npz")
        flat, stems = {}, []
        models = [_load(os.path.join(tree, "models", f"{tag}_g{cells}_e{E_POST}_s{seed}_link{li}.pt"))
                  for li in range(3)]
        pos = ([_load(os.path.join(tree, "models", f"{tag}_pos2_e{E_REG}_s0_link{li}.pt"))
                for li in range(3)] if head == "half" else None)
        for _s, stem in session_recordings(b):
            fp = os.path.join(c["shared"], "features", f"session_{b}_{stem}.npy")
            assert os.path.exists(fp), f"features not built for {b}/{stem}: run the features step"
            prob, per_link, rec = infer_recording(models, b, stem, "g")
            block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                     "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                     "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10"),
                     "xy": rec.xy,
                     "participant": np.array([rec.participant] * len(rec), dtype="U16")}
            if pos is not None:
                xh, xl = infer_recording(pos, b, stem, "pos")[:2]
                block["xy_hat"] = xh.astype(np.float32)
                block["xy_hat_link"] = xl.astype(np.float32)
            for k, v in block.items():
                flat[f"{stem}::{k}"] = v
            stems.append(stem)
        flat["__stems__"] = np.array(sorted(stems), dtype="U64")
        np.savez_compressed(out + ".tmp.npz", **flat)
        os.replace(out + ".tmp.npz", out)
        _say(f"infer {head} {b}: {len(stems)} recordings")
    return 0


# ---------------------------------------------------------------------------------------- decode

def _bind(c):
    """Bind the DC2 roots, then satisfy the import-time guards (the y4_pressalign pattern)."""
    import pipeline.constrained.artefacts as A
    import pipeline.constrained.common as C
    import pipeline.constrained.recordings as RC
    half = os.path.abspath(c["tree"]("half"))
    assert os.path.abspath(C.ART_DIR) == half and RC.WINDOWS_ROOT == c["win_view"], \
        (C.ART_DIR, RC.WINDOWS_ROOT)
    assert RC.ROOM == c["room"]
    from pipeline.constrained import lattice
    os.environ["TDR_ART_DIR"] = lattice.half_art_dir()   # guards only; every path is bound above
    import pipeline.constrained.g2_multihead as G2
    import pipeline.constrained.g3_final as G3
    rel = lambda h: os.path.relpath(c["tree"](h), REPO_ROOT)                       # noqa: E731
    G2.ONE_S_TREES = {0: rel("fh1s"), 1: rel("g1s1"), 2: rel("g1s2")}
    G3.ONE_S_TREES = dict(G2.ONE_S_TREES)
    G3.G100_TREE = rel("g100")
    return {"art": C.ART_DIR, "windows": RC.WINDOWS_ROOT, "room": RC.ROOM,
            "one_s": G2.ONE_S_TREES, "g100": G3.G100_TREE, "posterior_dir": A.POST_DIR}


def emission_spread(e, mask):
    import numpy as np
    e = np.asarray(e, float)[mask]
    if not len(e):
        return None
    return float(np.median(e.max(axis=1) - np.median(e, axis=1)))


def do_decode(c) -> int:
    import copy
    import numpy as np
    bound = _bind(c)
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained.dc2_pipeline import (read_manifest, split_passes, calibration_numbers,
                                                   re_anchored_constants)
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.n2_arms import run
    from pipeline.constrained.night_common import shipped_pieces
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.recordings import load_meta, recordings
    from pipeline.constrained.t1_region import assert_grouped_by_pass
    from pipeline.constrained.u1_adapt import session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_abstain, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    D.MAX_ADVANCE_M = None
    D2._LT_CACHE.clear()
    room_dir = os.path.join(c["data_view"], c["room"])
    man = read_manifest(room_dir)
    recs = [(s, st_) for s, st_ in recordings() if s in c["b_sessions"]]
    splits = {f"{s}|{stem}": split_passes(load_meta(s, stem), (man.get("sessions") or {}).get(s) or {})
              for s, stem in recs}
    bad = [k for k, v in splits.items() if set(v["calibration"]) & set(v["evaluated"])]
    assert not bad, f"calibration passes leaked into the evaluated set: {bad}"
    cal = calibration_numbers(c["room"], sorted(c["b_sessions"]), splits)
    consts = re_anchored_constants(cal)
    out = {"bound_roots": bound, "heads_tag": c["heads_tag"], "train": list(c["train"]),
           "calibration": cal, "constants": consts, "sessions": {}}
    cache = {}
    # the fusion flag, PER ARM (dc2_pipeline --fusion ARM=W). Only exploratory arms may carry one.
    fusion = json.loads(os.environ.get("TDR_DC2_FUSION") or json.dumps(EXPLORATORY_FUSION))
    bad = [k for k in fusion if k in FIXED_MEAN_ARMS]
    assert not bad, f"the pre-registered arms {bad} are fixed at mean fusion; no flag may change them"
    for k, w in fusion.items():
        assert float(w) in S_A_BY_W, f"{k}: no S_A frozen at the scale of fusion w {w}"
    out["fusion_per_arm"] = {**{k: 0.0 for k in FIXED_MEAN_ARMS}, **{k: float(w) for k, w in fusion.items()}}
    for b in sorted(c["b_sessions"]):
        te = (b,)
        src, info = shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind, alpha)
        src = list(src)
        # the pooled emission spread on the calibration walks, and the relative null
        calw = []
        for stem, rec, ge, e in src:
            sp = splits.get(f"{b}|{stem}") or {}
            m = np.isin(np.asarray(rec.pass_id), list(sp.get("calibration", []))) & \
                (np.asarray(rec.mode) == "walk")
            if m.any():
                calw.append(emission_spread(e, m))
        s_b = float(np.median([x for x in calw if x is not None])) if calw else None
        null_rel = None if s_b is None else NULL_ABS * s_b / S_A
        null_b = null_rel if (null_rel is not None and abs(null_rel - NULL_ABS) <= NULL_GUARD_NATS) else NULL_ABS
        theta_b = float((consts.get(b) or {}).get("theta", THETA_ABS))
        # the terms
        a2 = start_terms(c["train"], te, st, A2_WEIGHT)
        Xtr, ytr, ktr, _w, utr, _a = session_rows(c["train"], st, ADAPT_MODE, cache)
        Xte, _y, kte, _w2, ute, _a2 = session_rows(te, st, ADAPT_MODE, cache)
        assert_grouped_by_pass(ktr, utr)
        assert_grouped_by_pass(kte, ute)
        _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)
        veto = merged(dict(a2), term_veto(kte, proba, classes, st, VETO_THR, VETO_W))
        abst, cov = term_abstain(kte, proba, classes, st, ABSTAIN_THR, ABSTAIN_W)
        abstain = merged(dict(a2), abst)
        ne_b = copy.deepcopy(ne)
        ne_b.motion_theta = theta_b
        ne_b.offset = float(null_b)
        CONF = {"A": (ne, veto, src), "B": (ne_b, veto, src), "B0": (ne_b, a2, src),
                "B0_abstain": (ne_b, abstain, src)}
        # EXPLORATORY fusion arms: B with the pool re-fused at w, and the null re-anchored at the
        # PRODUCT's scale (s_B and S_A both at w) for this arm only. The gate threshold is B's: it is
        # read from gate energy, which no emission fusion touches.
        expl = {}
        for arm, w in fusion.items():
            src_w, _iw = shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind,
                                                alpha, fusion_w=float(w))
            src_w = list(src_w)
            cw = []
            for stem, rec, ge, e in src_w:
                sp_ = splits.get(f"{b}|{stem}") or {}
                m_ = np.isin(np.asarray(rec.pass_id), list(sp_.get("calibration", []))) & \
                    (np.asarray(rec.mode) == "walk")
                if m_.any():
                    cw.append(emission_spread(e, m_))
            s_bw = float(np.median([x for x in cw if x is not None])) if cw else None
            nr = None if s_bw is None else NULL_ABS * s_bw / S_A_BY_W[float(w)]
            nu = nr if (nr is not None and abs(nr - NULL_ABS) <= NULL_GUARD_NATS) else NULL_ABS
            ne_w = copy.deepcopy(ne)
            ne_w.motion_theta = theta_b
            ne_w.offset = float(nu)
            CONF[arm] = (ne_w, veto, src_w)
            expl[arm] = {"fusion_w": float(w), "EXPLORATORY": True, "s_B": s_bw,
                         "s_A": S_A_BY_W[float(w)], "null_relative": nr, "null_used": nu,
                         "null_fell_back": bool(nu == NULL_ABS and nr is not None and nr != NULL_ABS),
                         "theta_used": theta_b}
            if c["stand_in"]:
                # PLUMBING ONLY: the fused pool unanchored with A2 alone, which must equal the Room A
                # measurement z3a_linkprod_pa_w025 pass for pass
                CONF[f"{arm}_plumbing_a2_unanchored"] = (ne, a2, src_w)
        node = {"pool_info": info, "exploratory": expl, "s_B": s_b, "s_A": S_A, "null_relative": null_rel,
                "null_used": null_b, "null_fell_back": bool(null_b == NULL_ABS and null_rel is not None
                                                            and null_rel != NULL_ABS),
                "theta_used": theta_b, "abstain_coverage_passes": int(cov),
                "n_reader_passes": int(len(kte)), "rows": {}}
        for name, (ne_x, term, src_x) in CONF.items():
            o = shipped_opts(st, c["train"])
            o["entry"] = "soft"
            o["entry_window_m"] = 1.0
            o["start_term"] = term
            rows = []
            for r in run(src_x, st, cfg, ne_x, transit, o, subs=True):
                sess, stem, pid = r["key"].split("|")
                if int(pid) not in set((splits.get(f"{sess}|{stem}") or {}).get("evaluated", [])):
                    continue
                rows.append({"key": f"{c['room']}|{r['key']}", "stem": stem, "pass_id": int(pid),
                             "true": r["true_line"], "final_line": r["final_line"],
                             "correct": bool(r["final_line"] == r["true_line"]),
                             "subs_line_changed": r.get("subs_line_changed")})
            node["rows"][name] = rows
        out["sessions"][b] = node
        _say(f"decode {b}: " + ", ".join(
            f"{k} {100.0 * np.mean([r['correct'] for r in v]):.1f}%" for k, v in node["rows"].items()))
    with open(os.path.join(c["base"], "decode.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["view", "cut", "features", "infer", "decode"])
    ap.add_argument("--room", required=True)
    ap.add_argument("--stand-in", action="store_true")
    ap.add_argument("--head", choices=sorted(HEADS))
    a = ap.parse_args(argv)
    c = cfg_for(a.room, a.stand_in)
    return {"view": lambda: do_view(c), "cut": lambda: do_cut(c), "features": lambda: do_features(c),
            "infer": lambda: do_infer(c, a.head), "decode": lambda: do_decode(c)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
