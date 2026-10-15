"""Motion gate from the six participants without dwells: the run (PREREG.md, committed in 6ee73695).

    python gate_six.py checks     # PREREG section 6: inputs verified, no result computed
    python gate_six.py run        # steps 3 and 4, after the checks pass

Read only. One process; the launcher sets nice 10 and every thread cap at 1. No torch, no GPU.
It writes only into this folder.

Two small definitions are re-implemented verbatim rather than imported, because importing their
modules loads torch and resets the window roots (`night_common.set_half_roots`):
  - `u1_adapt.calibration_indices`: windows that END at or before the first press with mode `idle`;
  - `p1_runup.first_presses`: {pass_id: anchor_times[0]}, after asserting the reaction-time bias is
    recorded as applied.
The rule itself, `tools/calibrate_gate.best_split`, IS imported.

A3 and B2: from the window metadata only `t_start_abs` is used, and from the ground-truth file only
each pass's first anchor press. No mode, position, line or end press is read for them.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
os.environ["TDR_ART_DIR"] = os.path.join(HERE, "art")    # nothing here writes a cache; belt and braces

from calibrate_gate import best_split                       # noqa: E402  the original rule
from pipeline.constrained.common import SIX                 # noqa: E402
from pipeline.constrained.gate import band_energy           # noqa: E402

J = os.path.join
THETA_OLD = 0.431
G0 = 0.7541556642487132
WINDOW_S, WALK_EDGE_S, STRIDE_S, FS = 2.0, 3.0, 0.5, 150.0
MAX_WALK_S = 20.0
HORIZON_W = int(round(MAX_WALK_S / STRIDE_S))
CELLS = J(REPO, "runs", "dc2_results", "cells")
BROOT = J(REPO, "runs", "constrained", "dc2_room_B_s0.5_pressalign", "by_session")
AROOT = J(REPO, "runs", "constrained", "windows_s0.5_pressalign", "room_A")
DEC = "d3/FC.relgateU+abstain+a2w0.25/decode.json"

SESS = {
    "01": {"meta": J(AROOT, "session_01"), "gt": J(REPO, "data", "room_A", "session_01"),
           "cache": J(CELLS, "fin_B2", "art_half", "gate_energy"), "labels": True},
    "02": {"meta": J(AROOT, "session_02"), "gt": J(REPO, "data", "room_A", "session_02"),
           "cache": J(CELLS, "fin_B2", "art_half", "gate_energy"), "labels": True},
    "B1": {"meta": J(BROOT, "B1", "windows", "room_B", "session_B1"), "gt": J(REPO, "data", "room_B", "session_B1"),
           "cache": J(BROOT, "B1", "art_half", "gate_energy"), "labels": True},
    "03": {"meta": J(AROOT, "session_03"), "gt": J(REPO, "data", "room_A", "session_03"),
           "cache": J(CELLS, "fin_A3", "art_half", "gate_energy"), "labels": False},
    "B2": {"meta": J(BROOT, "B2", "windows", "room_B", "session_B2"), "gt": J(REPO, "data", "room_B", "session_B2"),
           "cache": J(CELLS, "fin_B2", "art_half", "gate_energy"), "labels": False},
}
NAME = {"01": "A1", "02": "A2", "03": "A3", "B1": "B1", "B2": "B2"}
CACHE_GLOBS = [J(CELLS, "*", "art_half", "gate_energy"), J(BROOT, "*", "art_half", "gate_energy"),
               J(REPO, "runs", "artefacts_s0.5_pressalign_half", "gate_energy")]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def recordings(sid: str) -> list:
    out = []
    for mp in sorted(glob.glob(J(SESS[sid]["meta"], "*.meta.json"))):
        stem = os.path.basename(mp)[:-len(".meta.json")]
        if "_DEMO_" in stem:
            continue
        if stem.replace("participant_", "").split("_")[0] not in SIX:
            continue
        out.append(stem)
    return out


def is_cal(stem: str) -> bool:
    return "_C_" in stem


def load(sid: str, stem: str) -> dict:
    """t0 always; mode and pass id only where labels may be read (A1, A2, B1)."""
    with open(J(SESS[sid]["meta"], f"{stem}.meta.json"), encoding="utf-8") as f:
        wins = json.load(f)["windows"]
    r = {"t0": np.array([w["t_start_abs"] for w in wins], float)}
    if SESS[sid]["labels"]:
        r["mode"] = np.array([w["mode"] for w in wins]).astype(str)
        r["pass_id"] = np.array([-1 if w["pass_id"] is None else int(w["pass_id"]) for w in wins])
    del wins
    return r


def first_presses(sid: str, stem: str) -> dict:
    """p1_runup.first_presses, verbatim in effect: {pass_id: first anchor press}."""
    p = J(SESS[sid]["gt"], f"{stem}.gt.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    assert (d.get("reaction_time") or {}).get("applied"), f"{p}: reaction-time bias not recorded as applied"
    out = {int(ps["pass_id"]): float(ps["anchor_times"][0]) for ps in d.get("passes", []) if ps.get("anchor_times")}
    del d
    return out


def cal_idx_labels(r: dict, fp: dict) -> np.ndarray:
    """u1_adapt.calibration_indices."""
    if not fp:
        return np.zeros(0, int)
    first = float(min(fp.values()))
    return np.flatnonzero((r["t0"] + WINDOW_S <= first + 1e-9) & (r["mode"] == "idle"))


def cal_idx_time(r: dict, fp: dict) -> np.ndarray:
    """final_model._final_stats' label-free rule."""
    first = float(min(fp.values()))
    t0 = r["t0"]
    return np.flatnonzero((t0 + WINDOW_S <= first + 1e-9) & (np.abs(t0 + 1.0 - first) > WALK_EDGE_S))


def cache(sid: str, stem: str) -> np.ndarray:
    return np.load(J(SESS[sid]["cache"], f"session_{sid}_{stem}.npy"))


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def free_pct() -> int:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    m = re.search(r"free percentage:\s*(\d+)%", out)
    return int(m.group(1)) if m else -1


def wait_memory(min_pct: int = 30, max_wait_s: int = 1800) -> int:
    t = time.time()
    while True:
        p = free_pct()
        if p >= min_pct:
            return p
        if time.time() - t > max_wait_s:
            raise SystemExit(f"HALT: system free memory {p} % stayed below {min_pct} % for {max_wait_s} s")
        log(f"waiting: system free memory {p} % < {min_pct} %")
        time.sleep(60)


def lo_from_press(t0: np.ndarray, press: float) -> int:
    i = int(np.argmin(np.abs(t0 - (press - 1.0))))
    assert abs(t0[i] - (press - 1.0)) < 1e-3, f"no window centred on the press at {press}"
    return i


def decoder_record_scales() -> dict:
    out = {}
    for cell in ("fin_A3", "fin_B2", "zsf_B2"):
        with open(J(CELLS, cell, DEC), encoding="utf-8") as f:
            info = json.load(f)["info"]                     # the info block only; no row is read
        out[cell] = {"G0": info["gate_reference_G0"], "gate_scale": info["gate_scale"], "train": info["train"]}
    return out


# ------------------------------------------------------------------------------------------ checks
def checks() -> dict:
    res = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "free_memory_pct_at_start": free_pct()}
    src = open(J(REPO, "pipeline", "constrained", "night_arms.py"), encoding="utf-8").read()
    assert re.search(r"^MAX_WALK_S = 20\.0$", src, re.M), "night_arms.MAX_WALK_S is no longer 20.0"
    n2 = json.load(open(J(REPO, "runs", "constrained", "night", "n2_arms", "results.json"), encoding="utf-8"))
    arms = next(iter((n2.get("per_pairing") or {}).values()))["arms"]
    shipped = {n_: (arms.get(n_) or {}).get("opts") for n_ in ("C_family", "G_maxlik", "I_chainprior")}
    assert not any("runup_states" in (o or {}) or "dir_prior_w" in (o or {}) for o in shipped.values()), shipped
    res["shipped_opts_arms"] = shipped
    # 1. caches identical across cells, and lengths equal to the meta
    c1, bad = {}, []
    for sid in SESS:
        for stem in recordings(sid):
            fn = f"session_{sid}_{stem}.npy"
            canon = J(SESS[sid]["cache"], fn)
            if not os.path.exists(canon):
                bad.append(f"{sid}/{stem}: no canonical cache")
                continue
            h0 = sha(canon)
            others = sorted({p for g in CACHE_GLOBS for p in glob.glob(J(g, fn))} - {canon})
            diff = [p for p in others if sha(p) != h0]
            n_meta = len(load(sid, stem)["t0"])
            n_cache = int(np.load(canon).shape[0])
            c1[f"{sid}/{stem}"] = {"canonical": os.path.relpath(canon, REPO), "sha256": h0,
                                   "copies_identical": len(others) - len(diff), "copies_different":
                                   [os.path.relpath(p, REPO) for p in diff], "n_meta": n_meta, "n_cache": n_cache}
            if diff:
                bad.append(f"{sid}/{stem}: {len(diff)} cached copies differ")
            if n_meta != n_cache:
                bad.append(f"{sid}/{stem}: cache {n_cache} windows against meta {n_meta}")
    res["1_caches"] = c1
    # 2. recompute one A1 and one B1 recording from their window files
    c2 = {}
    for sid in ("01", "B1"):
        stems = sorted(recordings(sid), key=lambda s: os.path.getsize(J(SESS[sid]["meta"], f"{s}.npz")))
        stem = stems[0]
        p = wait_memory()
        log(f"recompute {sid}/{stem} from its window file (free memory {p} %)")
        X = np.load(J(SESS[sid]["meta"], f"{stem}.npz"))["X"]
        e = np.array([band_energy(X[i].astype(np.float32), FS) for i in range(len(X))], dtype=float)
        del X
        ce = cache(sid, stem)
        c2[f"{sid}/{stem}"] = {"n": int(len(e)), "max_abs_diff": float(np.max(np.abs(e - ce))),
                               "exact": bool(np.array_equal(e, ce)), "free_memory_pct_before": p,
                               "free_memory_pct_after": free_pct()}
        if not np.array_equal(e, ce):
            bad.append(f"{sid}/{stem}: recomputed energies differ from the cache by up to {c2[f'{sid}/{stem}']['max_abs_diff']}")
    res["2_recompute"] = c2
    # 3. G0 from the caches; time rule equals calibration_indices on A1, A2, B1; lo rule on the same
    meds, rule_eq, lo_eq = [], {}, {"passes": 0, "agree": 0}
    for sid in ("01", "02", "B1"):
        for stem in recordings(sid):
            r, fp = load(sid, stem), first_presses(sid, stem)
            ia, ib = cal_idx_labels(r, fp), cal_idx_time(r, fp)
            rule_eq[f"{sid}/{stem}"] = {"labels": int(len(ia)), "time": int(len(ib)),
                                        "identical": bool(np.array_equal(ia, ib))}
            if not np.array_equal(ia, ib):
                bad.append(f"{sid}/{stem}: the time rule selects other windows than calibration_indices")
            if sid in ("01", "02") and not is_cal(stem):
                meds.append(float(np.median(cache(sid, stem)[ia])))
            for k, pr in fp.items():
                w = np.flatnonzero((r["pass_id"] == k) & (r["mode"] == "walk"))
                if len(w) < 2:
                    continue
                lo_eq["passes"] += 1
                lo_eq["agree"] += int(lo_from_press(r["t0"], pr) == int(w[0]))
    g0 = float(np.median(meds))
    res["3_G0"] = {"recomputed": g0, "deployed": G0, "abs_diff": abs(g0 - G0), "n_recordings": len(meds)}
    if abs(g0 - G0) >= 1e-12:
        bad.append(f"G0 recomputed {g0} against {G0}")
    res["3_time_rule_equals_calibration_indices"] = rule_eq
    res["3_lo_rule"] = lo_eq
    if lo_eq["agree"] != lo_eq["passes"]:
        bad.append(f"lo rule agrees on {lo_eq['agree']} of {lo_eq['passes']} passes")
    # 4. scales on A3 and B2 (label-free) against the decode records
    rec = decoder_record_scales()
    c4 = {"records_G0": {k: v["G0"] for k, v in rec.items()}}
    for sid, cells in (("03", ("fin_A3",)), ("B2", ("fin_B2", "zsf_B2"))):
        for stem in recordings(sid):
            r, fp = load(sid, stem), first_presses(sid, stem)
            ib = cal_idx_time(r, fp)
            g = float(np.median(cache(sid, stem)[ib]))
            sc = max(1.0, G0 / g)
            row = {"n_idle": int(len(ib)), "g_rec": g, "scale": sc}
            for cell in cells:
                ref = rec[cell]["gate_scale"][stem]
                row[f"{cell}_scale"] = ref
                if abs(sc - ref) >= 1e-9:
                    bad.append(f"{sid}/{stem}: scale {sc} against {cell}'s {ref}")
            c4[f"{sid}/{stem}"] = row
    for cell, v in rec.items():
        if abs(v["G0"] - G0) >= 1e-15:
            bad.append(f"{cell}: decode record G0 {v['G0']}")
    res["4_scales"] = c4
    res["problems"] = bad
    res["passed"] = not bad
    res["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(J(HERE, "checks.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    log(f"checks {'PASSED' if not bad else 'FAILED'}: {len(bad)} problem(s)")
    for b in bad:
        log(f"  {b}")
    return res


# ------------------------------------------------------------------------------------- the results
def scaled_and_classes(sid: str) -> dict:
    """Per recording of a labelled Room A session: raw, scale, still idx, walking idx."""
    out = {}
    for stem in recordings(sid):
        r, fp = load(sid, stem), first_presses(sid, stem)
        raw = cache(sid, stem)
        ci = cal_idx_labels(r, fp)
        g = float(np.median(raw[ci]))
        out[stem] = {"raw": raw, "scale": max(1.0, G0 / g), "still": ci,
                     "walk": np.flatnonzero((r["mode"] == "walk") & (r["pass_id"] >= 0))}
    return out


def balanced(still: np.ndarray, walk: np.ndarray, th: float) -> float:
    return float(0.5 * ((still < th).mean() + (walk >= th).mean()))


def derive(cls_a1: dict, cls_a2: dict, scaled: bool) -> dict:
    def pools(cls):
        s = np.concatenate([v["raw"][v["still"]] * (v["scale"] if scaled else 1.0) for v in cls.values()])
        w = np.concatenate([v["raw"][v["walk"]] * (v["scale"] if scaled else 1.0) for v in cls.values()])
        return s, w
    s1, w1 = pools(cls_a1)
    s2, w2 = pools(cls_a2)
    th, s_over, w_under = best_split(s1, w1)
    # the same candidate grid, to find the flat range of maximal balanced accuracy
    a, b = np.log10(s1), np.log10(w1)
    cands = np.linspace(min(a.min(), b.min()), max(a.max(), b.max()), 2000)
    bal = np.array([0.5 * ((a < c).mean() + (b >= c).mean()) for c in cands])
    top = np.flatnonzero(bal == bal.max())
    assert abs(10 ** cands[top[-1]] - th) < 1e-12 * max(1.0, th), "flat-range search disagrees with best_split"
    curve_a2 = np.array([balanced(s2, w2, 10 ** c) for c in cands])
    return {"statistic": "scaled" if scaled else "raw", "theta_new": th,
            "A1": {"n_still": int(len(s1)), "n_walk": int(len(w1)), "balanced_at_new": balanced(s1, w1, th),
                   "balanced_at_0.431": balanced(s1, w1, THETA_OLD), "still_read_walking_pct_at_new": s_over,
                   "walking_read_still_pct_at_new": w_under,
                   "still_read_walking_pct_at_0.431": float(100 * (s1 >= THETA_OLD).mean()),
                   "walking_read_still_pct_at_0.431": float(100 * (w1 < THETA_OLD).mean()),
                   "still_median": float(np.median(s1)), "walk_median": float(np.median(w1))},
            "A2": {"n_still": int(len(s2)), "n_walk": int(len(w2)), "balanced_at_new": balanced(s2, w2, th),
                   "balanced_at_0.431": balanced(s2, w2, THETA_OLD),
                   "still_read_walking_pct_at_new": float(100 * (s2 >= th).mean()),
                   "walking_read_still_pct_at_new": float(100 * (w2 < th).mean()),
                   "still_read_walking_pct_at_0.431": float(100 * (s2 >= THETA_OLD).mean()),
                   "walking_read_still_pct_at_0.431": float(100 * (w2 < THETA_OLD).mean()),
                   "still_median": float(np.median(s2)), "walk_median": float(np.median(w2))},
            "flat_range": {"n_candidates": int(len(top)), "lo": float(10 ** cands[top[0]]),
                           "hi": float(10 ** cands[top[-1]]), "contiguous": bool(np.all(np.diff(top) == 1)),
                           "log_midpoint": float(10 ** ((cands[top[0]] + cands[top[-1]]) / 2)),
                           "max_balanced": float(bal.max())},
            "curve": {"theta": [float(10 ** c) for c in cands], "balanced_A1": bal.tolist(),
                      "balanced_A2": curve_a2.tolist()}}


def spans(sid: str, stem: str, n: int) -> np.ndarray:
    r, fp = load(sid, stem), first_presses(sid, stem)
    t0 = r["t0"]
    lab = np.full(n, "elsewhere", dtype=object)
    first = float(min(fp.values()))
    lab[t0 + WINDOW_S <= first + 1e-9] = "before_first_press"
    if SESS[sid]["labels"]:
        for k, pr in fp.items():
            w = np.flatnonzero((r["pass_id"] == k) & (r["mode"] == "walk"))
            if len(w) < 2:
                continue
            lo, hi_true = int(w[0]), int(w[-1])
            hi = min(n - 1, lo + HORIZON_W)
            seg = np.arange(hi_true + 1, hi + 1)
            lab[seg[lab[seg] != "press_to_walk_end"]] = "walk_end_to_horizon"
        for k, pr in fp.items():
            w = np.flatnonzero((r["pass_id"] == k) & (r["mode"] == "walk"))
            if len(w) >= 2:
                lab[int(w[0]):int(w[-1]) + 1] = "press_to_walk_end"
    else:
        for k, pr in fp.items():
            lo = lo_from_press(t0, pr)
            lab[lo:min(n - 1, lo + HORIZON_W) + 1] = "decode_range"
    return lab


def run() -> dict:
    with open(J(HERE, "checks.json"), encoding="utf-8") as f:
        ck = json.load(f)
    assert ck.get("passed"), "the pre-registered checks have not passed"
    res = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "prereg_sha256": open(J(HERE, "PREREG.md.sha256")).read().split()[0]}
    a1, a2 = scaled_and_classes("01"), scaled_and_classes("02")
    res["still_counts"] = {NAME[s]: {k: int(len(v["still"])) for k, v in c.items()} for s, c in (("01", a1), ("02", a2))}
    res["walk_counts"] = {NAME[s]: {k: int(len(v["walk"])) for k, v in c.items()} for s, c in (("01", a1), ("02", a2))}
    prim, sec = derive(a1, a2, True), derive(a1, a2, False)
    res["primary_scaled"] = {k: v for k, v in prim.items() if k != "curve"}
    res["secondary_raw"] = {k: v for k, v in sec.items() if k != "curve"}
    with open(J(HERE, "curve.json"), "w", encoding="utf-8") as f:
        json.dump({"scaled": prim["curve"], "raw": sec["curve"]}, f)
    th = prim["theta_new"]
    log(f"theta_new (scaled, primary) = {th:.6g}; raw secondary {sec['theta_new']:.6g}")
    # equivalence
    rec = decoder_record_scales()
    models = {"fin": ("01", "02", "B1", "03", "B2"), "zsf": ("B2",)}
    rows, table = [], {}
    for model, sids in models.items():
        for sid in sids:
            for stem in recordings(sid):
                raw = cache(sid, stem)
                if sid in ("03", "B2"):
                    r, fp = load(sid, stem), first_presses(sid, stem)
                    g = float(np.median(raw[cal_idx_time(r, fp)]))
                    cellname = {"03": "fin_A3", "B2": "fin_B2" if model == "fin" else "zsf_B2"}[sid]
                    sc = rec[cellname]["gate_scale"][stem]
                    assert abs(sc - max(1.0, G0 / g)) < 1e-9
                else:
                    r, fp = load(sid, stem), first_presses(sid, stem)
                    sc = max(1.0, G0 / float(np.median(raw[cal_idx_labels(r, fp)])))
                s = raw * sc
                old_still, new_still = s < THETA_OLD, s < th
                flip = old_still != new_still
                lab = spans(sid, stem, len(s))
                for sp in sorted(set(lab.tolist())):
                    m = lab == sp
                    row = {"model": model, "session": NAME[sid], "stem": stem, "calibration": is_cal(stem),
                           "span": sp, "windows": int(m.sum()), "flips": int((flip & m).sum()),
                           "walking_to_still": int((flip & m & new_still).sum()),
                           "still_to_walking": int((flip & m & old_still).sum()), "scale": sc}
                    rows.append(row)
                    key = f"{model}|{NAME[sid]}|{sp}"
                    t = table.setdefault(key, {"windows": 0, "flips": 0, "walking_to_still": 0, "still_to_walking": 0})
                    for kk in t:
                        t[kk] += row[kk]
    res["flips_by_model_session_span"] = table
    reach = {k: v["flips"] for k, v in table.items()
             if k.split("|")[2] in ("press_to_walk_end", "walk_end_to_horizon", "decode_range")}
    res["flips_inside_decode_ranges"] = reach
    res["stop_case"] = bool(sum(reach.values()) > 0)
    res["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(J(HERE, "flips_per_recording.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    with open(J(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    plot(prim, sec)
    log(f"STOP case: {res['stop_case']}; flips inside decode ranges {sum(reach.values())}")
    return res


def plot(prim: dict, sec: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, d in zip(axs, (prim, sec)):
        c = d["curve"]
        ax.plot(c["theta"], np.array(c["balanced_A1"]) * 100, label="A1 (placed here)", color="#1f5fa8")
        ax.plot(c["theta"], np.array(c["balanced_A2"]) * 100, label="A2 (check)", color="#d9822b")
        ax.axvline(THETA_OLD, color="k", lw=1.5, ls="--", label="0.431 (deployed)")
        ax.axvline(d["theta_new"], color="#2a9d5c", lw=1.5, label=f"new {d['theta_new']:.3g}")
        ax.set_xscale("log")
        ax.set_xlabel(f"threshold on the {d['statistic']} band energy")
        ax.set_title(f"{d['statistic']}: still = idle before the first press, six participants")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axs[0].set_ylabel("balanced accuracy, %")
    fig.tight_layout()
    fig.savefig(J(HERE, "curve.png"), dpi=130)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "checks":
        sys.exit(0 if checks()["passed"] else 2)
    if cmd == "run":
        run()
        sys.exit(0)
    raise SystemExit(__doc__)
