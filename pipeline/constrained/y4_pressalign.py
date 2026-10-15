"""ITEM 2 of batch 2026-09-23c: THE PRESS-ALIGNED WINDOW LATTICE. Pre-registration
`reports/PREREG_pressalign_2026-09-23.md`.

WHAT IT CHANGES. The shipped 0.5 s lattice is one grid per recording, `ceil(lo / 0.5) * 0.5`, so
its phase against each press is whatever the recording's start happened to give: the first walk
window starts between 0.501 and 0.999 s before the press, median 0.782 (measured, 360 passes).
Here each pass gets its own lattice PHASE: the recording's grid is shifted by the smallest amount,
never more than a quarter stride, that puts a window START exactly on that pass's press. The
window length (2 s), the stride (0.5 s) and the labelling rule (`windows.label_window`) are the
shipped ones, untouched. The shift is constant within a pass's segment; segments meet at the
midpoint between one pass's end and the next pass's start, which on Room A is 5 to 300 s from any
walk, so the only irregular spacings sit in standing or dwell time.

WHY THAT IS THE ALIGNMENT. With a window starting at the press, window `lo + 2` (the last one the
index-based lock reads) ends at exactly press + 2.0 s, the frame V3 draws the lock on. On the
shipped lattice it ends 0.001 to 0.499 s AFTER that frame on 360 of 360 passes.

ISOLATION. Nothing shipped is written. The windows go to `runs/constrained/windows_s0.5_pressalign`,
and each head's artefacts to `runs/artefacts_s0.5_pressalign_<head>`: every name carries the stride,
so the stride-blind feature cache can never be served to, or written into, another lattice. The
shipped weights are COPIED in, never moved or linked, and the shipped trees are read only.

Subcommands, run in order and each logged to runs/constrained/logs/y4_pressalign.log:
  cut      the new lattice over the eighteen recordings (`--one` times a single recording)
  prep     features once, then the five frozen heads' posteriors, inference only
  measure  the lock, the entry hold and whole-walk tracking, against the shipped lattice
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STRIDE_S = 0.5
PA_WINDOWS = os.path.join("runs", "constrained", "windows_s0.5_pressalign")
#: each window starts this long AFTER the press, not on it. On the press itself the first window's
#: midpoint is the press to the last bit, and `label_window`'s `t_start <= t_mid` then labels it
#: walk or walk_edge by float rounding: measured, 9 of 20 passes of the first recording came out
#: the wrong way and put `lo` half a stride late. 2 microseconds is 1/3300 of a sample period.
from pipeline.constrained.lattice import PRESS_EPS_S as EPS_S                   # noqa: E402
PA_ART_PREFIX = os.path.join(REPO_ROOT, "runs", "artefacts_s0.5_pressalign")
OUT_DIR = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "y4_pressalign")
SHIPPED_TREES_NEVER_WRITTEN = (
    os.path.join(REPO_ROOT, "runs", "constrained", "windows_half"),
    os.path.join(REPO_ROOT, "runs", "constrained", "windows_w1"),
    os.path.join(REPO_ROOT, "runs", "artefacts"),
    os.path.join(REPO_ROOT, "runs", "artefacts_half"),
    os.path.join(REPO_ROOT, "runs", "artefacts_fh1s"),
    os.path.join(REPO_ROOT, "runs", "artefacts_g1s1"),
    os.path.join(REPO_ROOT, "runs", "artefacts_g1s2"),
    os.path.join(REPO_ROOT, "runs", "artefacts_g1g100s0"),
)


def _say(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line, flush=True)


def assert_not_shipped(path: str) -> None:
    """Refuse any write location inside a shipped tree, or one whose name lacks the stride."""
    ap = os.path.abspath(path)
    for t in SHIPPED_TREES_NEVER_WRITTEN:
        if ap == t or ap.startswith(t + os.sep):
            raise AssertionError(f"y4_pressalign refuses to write inside shipped tree {t}")
    if "s0.5_pressalign" not in ap:
        raise AssertionError(f"y4_pressalign write location {ap} does not carry the stride")


# ------------------------------------------------------------------------------------------ cut

def pa_starts(base_starts, passes, stride_s: float = STRIDE_S, lo: float = -math.inf,
              hi: float = math.inf):
    """The shipped lattice, re-phased per pass so a window STARTS exactly on each press.

    `passes` is the sidecar's pass list. Each window belongs to the pass whose segment holds its
    start; segments meet midway between one pass's `t_end` and the next pass's `t_start`. Within a
    segment the whole lattice moves by one constant shift in [-stride/2, +stride/2). Windows whose
    shifted span leaves the recorded data, or that would duplicate or precede their predecessor,
    are dropped, so the output is strictly increasing.
    """
    import numpy as np
    base = np.asarray(base_starts, float)
    if len(base) == 0 or not passes:
        return base, []
    ps = sorted(passes, key=lambda p: float(p["t_start"]))
    bounds = [0.5 * (float(ps[i]["t_end"]) + float(ps[i + 1]["t_start"])) for i in range(len(ps) - 1)]
    t0 = float(base[0])
    shifts = []
    for p in ps:
        d = (float(p["t_start"]) + EPS_S - t0) / stride_s
        shifts.append((d - math.floor(d + 0.5)) * stride_s)        # in [-stride/2, +stride/2)
    seg = np.searchsorted(np.asarray(bounds), base, side="right")
    out, last = [], -math.inf
    for T, k in zip(base, seg):
        T2 = float(T) + shifts[int(k)]
        if T2 < lo - 1e-9 or T2 > hi + 1e-9 or T2 <= last + 1e-6:
            continue
        out.append(T2)
        last = T2
    return np.asarray(out), [round(s, 6) for s in shifts]


def cut_one(session_dir: str, stem: str, baselines, out_dir: str) -> dict:
    """Cut one recording on the press-aligned lattice with the SHIPPED cutter, re-phased."""
    import numpy as np
    import pipeline.io.windows as W
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    orig = W.window_starts
    record = {}

    def _phased(nodes, window_s, stride_s, fs):
        base = orig(nodes, window_s, stride_s, fs)
        lo_ = max(c.grid[0] for c in nodes.values())
        hi_ = min(c.grid[-1] for c in nodes.values()) - window_s
        new, shifts = pa_starts(base, sidecar.get("passes", []), stride_s, lo_, hi_)
        record["shifts"] = shifts
        record["n_base"] = int(len(base))
        return new

    W.window_starts = _phased
    try:
        X, metas, summary = W.cut_recording(session_dir, stem, baselines, stride_s=STRIDE_S)
    finally:
        W.window_starts = orig
    summary["lattice"] = "press_aligned_per_pass"
    summary["pass_phase_shifts_s"] = record.get("shifts")
    summary["n_windows_shipped_lattice"] = record.get("n_base")
    assert_not_shipped(out_dir)
    W.write_recording(X, metas, summary, out_dir, stem)
    # THE ALIGNMENT, verified on what was written rather than on what was intended
    t = np.array([m.t_start_abs for m in metas])
    offs, lo_ok = [], 0
    mode = np.array([m.mode for m in metas])
    pid = np.array([-1 if m.pass_id is None else m.pass_id for m in metas])
    for p in sidecar.get("passes", []):
        P = float(p["t_start"])
        offs.append(float(np.min(np.abs(t - (P + EPS_S)))))
        w = np.flatnonzero((pid == int(p["pass_id"])) & (mode == "walk"))
        # lo must start exactly one second before the press, so lo + 2 ends on press + 2.0 s
        lo_ok += int(len(w) > 0 and abs(float(t[w[0]]) - (P + EPS_S - 1.0)) < 1e-5)
    return {"stem": stem, "n": len(metas), "n_shipped": record.get("n_base"),
            "max_press_to_nearest_start_s": round(max(offs) if offs else -1.0, 6),
            "passes_with_lo_at_press_minus_1s": lo_ok, "n_passes_sidecar": len(offs),
            "modes": summary["modes"], "passes": summary["passes"]}


def do_cut(one: bool) -> int:
    import pipeline.io.windows as W
    t_all = time.time()
    rows = []
    for session_dir in sorted(glob.glob(os.path.join(REPO_ROOT, "data", "room_A", "session_*"))):
        out_dir = os.path.join(REPO_ROOT, PA_WINDOWS, "room_A", os.path.basename(session_dir))
        assert_not_shipped(out_dir)
        cache = {}
        for stem in W.recordings_in(session_dir):
            bdir = W.baseline_dir_for(session_dir, stem)
            if bdir not in cache:
                cache[bdir] = W.session_baseline(bdir)
            t0 = time.time()
            r = cut_one(session_dir, stem, cache[bdir], out_dir)
            r["seconds"] = round(time.time() - t0, 1)
            rows.append(r)
            _say(f"cut {os.path.basename(session_dir)}/{stem}: {r['n']} windows (shipped lattice "
                 f"{r['n_shipped']}), press-to-start max {r['max_press_to_nearest_start_s']:.6f} s, "
                 f"lo at press - 1 s on {r['passes_with_lo_at_press_minus_1s']} of "
                 f"{r['n_passes_sidecar']}, {r['seconds']} s")
            if one:
                _say(f"ONE-RECORDING TIMING: {r['seconds']} s")
                return 0
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "cut.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "minutes": round((time.time() - t_all) / 60.0, 1)}, f, indent=1)
    bad = [r for r in rows if r["max_press_to_nearest_start_s"] > 1e-5
           or r["passes_with_lo_at_press_minus_1s"] != r["n_passes_sidecar"]]
    _say(f"cut DONE: {len(rows)} recordings, {sum(r['n'] for r in rows)} windows, "
         f"{len(bad)} with a press not on a window start")
    return 0 if not bad and len(rows) == 18 else 1


# ----------------------------------------------------------------------------------------- prep

#: the six frozen heads the shipped render reads, and where their weights live. Five are the
#: decision pool (`g3_final.shipped_pool_emissions`); `dispend` is the DISPLAY head (DISP_END),
#: read only by the drawn path. g100 is a 100-cell REGION head (the "g" in g100 is the grid).
HEADS = {
    "half":    {"src": "runs/artefacts_half/models",     "cells": 25,  "seed": 0},
    "fh1s":    {"src": "runs/artefacts/models",          "cells": 25,  "seed": 0},
    "g1s1":    {"src": "runs/artefacts/models",          "cells": 25,  "seed": 1},
    "g1s2":    {"src": "runs/artefacts/models",          "cells": 25,  "seed": 2},
    "g100":    {"src": "runs/artefacts/models",          "cells": 100, "seed": 0},
    "dispend": {"src": "runs/artefacts_dispend/models",  "cells": 25,  "seed": 0},
}
SHARED = PA_ART_PREFIX + "_shared"


def head_tree(h: str) -> str:
    return f"{PA_ART_PREFIX}_{h}"


def _cross_tags():
    """The nine cross-day pairings, built here: `s2a_dispend` guards its import on artefacts_half."""
    from pipeline.constrained.common import pairings, tag_of
    return [(tag_of(tr, te, False), tr, te) for tr, te in pairings() if tr != te]


def prep_shared() -> int:
    """Features and RSSI for the eighteen recordings, ONCE, in a stride-named shared tree.

    Both are fixed transforms of the windows (a 2 Hz lowpass; RSSI on each window's own lattice),
    identical for every head, so six copies would be 90 GB of the same numbers.
    """
    assert os.environ.get("TDR_ART_DIR") == SHARED, "prep-shared must run with the shared root"
    assert os.environ.get("TDR_WINDOWS_ROOT") == PA_WINDOWS
    assert_not_shipped(SHARED)
    from pipeline.constrained.recordings import build_feature_cache, load_meta, load_rssi, recordings
    t0 = time.time()
    for s_, stem in recordings():
        build_feature_cache(s_, stem)
        load_rssi(s_, stem, load_meta(s_, stem).t0_epoch)
        _say(f"prep-shared {s_}/{stem} features and rssi ready")
    _say(f"prep-shared DONE in {(time.time() - t0) / 60.0:.1f} min")
    return 0


def prep_head(h: str) -> int:
    """One frozen head over the press-aligned windows. INFERENCE ONLY: refuses to train."""
    import numpy as np
    tree = head_tree(h)
    assert os.environ.get("TDR_ART_DIR") == tree, f"prep-head {h} must run with its own root"
    assert os.environ.get("TDR_WINDOWS_ROOT") == PA_WINDOWS
    assert_not_shipped(tree)
    spec = HEADS[h]
    os.makedirs(os.path.join(tree, "models"), exist_ok=True)
    for sub in ("features", "rssi_full"):
        link = os.path.join(tree, sub)
        if not os.path.lexists(link):
            os.symlink(os.path.join(SHARED, sub), link)
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.common import E_POST
    from pipeline.constrained.recordings import session_recordings
    t0 = time.time()
    for tag, tr_s, te_s in _cross_tags():
        names = [f"{tag}_g{spec['cells']}_e{E_POST}_s{spec['seed']}_link{li}.pt" for li in range(3)]
        srcs = [os.path.join(REPO_ROOT, spec["src"], n) for n in names]
        missing = [p for p in srcs if not os.path.exists(p)]
        if missing:
            raise AssertionError(f"{h} {tag}: frozen weights missing, and this stage never "
                                 f"trains: {missing}")
        dsts = [os.path.join(tree, "models", n) for n in names]
        for a, b in zip(srcs, dsts):
            if not os.path.exists(b):
                shutil.copy2(a, b)                  # a COPY; the shipped weights stay put
        out = os.path.join(tree, "posteriors",
                           f"{tag}_g{spec['cells']}_e{E_POST}_s{spec['seed']}_full.npz")
        if os.path.exists(out):
            continue
        models = [_load(p) for p in dsts]
        flat, stems = {}, []
        for _s, stem in session_recordings(te_s[0]):
            prob, per_link, rec = infer_recording(models, te_s[0], stem, "g")
            block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                     "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                     "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10"),
                     "xy": rec.xy,
                     "participant": np.array([rec.participant] * len(rec), dtype="U16")}
            for k_, v in block.items():
                flat[f"{stem}::{k_}"] = v
            stems.append(stem)
        flat["__stems__"] = np.array(sorted(stems), dtype="U64")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        np.savez_compressed(out + ".tmp.npz", **flat)
        os.replace(out + ".tmp.npz", out)
        _say(f"prep-head {h} {tag}: {len(stems)} recordings inferred")
    _say(f"prep-head {h} DONE in {(time.time() - t0) / 60.0:.1f} min")
    return 0


def prep_pos() -> int:
    """The POSITION head over the press-aligned windows, into the 0.5 s head's posterior files.

    The A2 start term (`q3_startclf.features`) reads `xy_hat` and `xy_hat_link` from those files
    over the windows straddling the press, exactly as `build_full_posteriors` writes them. The first
    press-aligned measurement failed on all nine pairings because this head had not been inferred.
    """
    import numpy as np
    tree = head_tree("half")
    assert os.environ.get("TDR_ART_DIR") == tree and os.environ.get("TDR_WINDOWS_ROOT") == PA_WINDOWS
    assert_not_shipped(tree)
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.common import E_POST, E_REG
    for tag, tr_s, te_s in _cross_tags():
        names = [f"{tag}_pos2_e{E_REG}_s0_link{li}.pt" for li in range(3)]
        dsts = []
        for n in names:
            a = os.path.join(REPO_ROOT, "runs", "artefacts_half", "models", n)
            if not os.path.exists(a):
                raise AssertionError(f"position weights missing, never trained here: {a}")
            b = os.path.join(tree, "models", n)
            if not os.path.exists(b):
                shutil.copy2(a, b)
            dsts.append(b)
        models = [_load(q) for q in dsts]
        path = os.path.join(tree, "posteriors", f"{tag}_g25_e{E_POST}_s0_full.npz")
        d = dict(np.load(path, allow_pickle=False))
        stems = [str(x) for x in d["__stems__"]]
        if all(f"{st_}::xy_hat" in d for st_ in stems):
            continue
        for st_ in stems:
            xy_hat, xy_link = infer_recording(models, te_s[0], st_, "pos")[:2]
            d[f"{st_}::xy_hat"] = xy_hat.astype(np.float32)
            d[f"{st_}::xy_hat_link"] = xy_link.astype(np.float32)
        np.savez_compressed(path + ".tmp.npz", **d)
        os.replace(path + ".tmp.npz", path)
        _say(f"prep-pos {tag}: position head added for {len(stems)} recordings")
    return 0


def do_prep() -> int:
    """Shared features first, then the six heads as six parallel single-thread processes."""
    import subprocess
    env0 = dict(os.environ, OMP_NUM_THREADS="1", TDR_WINDOWS_ROOT=PA_WINDOWS)
    r = subprocess.run([sys.executable, "-m", "pipeline.constrained.y4_pressalign", "prep-shared"],
                       env=dict(env0, TDR_ART_DIR=SHARED), cwd=REPO_ROOT)
    if r.returncode != 0:
        return r.returncode
    procs = {h: subprocess.Popen([sys.executable, "-m", "pipeline.constrained.y4_pressalign",
                                  "prep-head", "--head", h],
                                 env=dict(env0, TDR_ART_DIR=head_tree(h)), cwd=REPO_ROOT)
             for h in HEADS}
    codes = {h: p.wait() for h, p in procs.items()}
    _say(f"prep DONE: exit codes {codes}")
    return 0 if all(c == 0 for c in codes.values()) else 1


# -------------------------------------------------------------------------------------- measure

#: the render's own constants, as x1_edgedisp carries them, so the measured dot is the drawn dot
FPS, LAG, LATENCY, DELAY, HEAD_OFFSET_S, SHIFT_W = 10, 1.0, 2.0, 2.0, 0.75, 0.50
DISPLAY_CAP_M_PER_WINDOW = 0.80
PRIOR_F = 0.50
SELECTION_FOLDS = ("s01_to_s02", "s02_to_s01")
EDGE_LINES = ("E_col1", "E_col5", "E_row1", "E_row5")
EARLY_S = 1.0          #: the "opening" of a walk, for the early-versus-late split
AT_ENTRY_M = 0.05      #: a first decoded position this close to the line's entry IS the entry


def _repoint_heads():
    """Every head the shipped pool and display read, pointed at its press-aligned tree."""
    import pipeline.constrained.g2_multihead as G2
    import pipeline.constrained.g3_final as G3
    import pipeline.constrained.s2a_dispend as SA
    rel = {h: os.path.relpath(head_tree(h), REPO_ROOT) for h in HEADS}
    trees = {0: rel["fh1s"], 1: rel["g1s1"], 2: rel["g1s2"]}
    G2.ONE_S_TREES = dict(trees)
    G3.ONE_S_TREES = dict(trees)
    G3.G100_TREE = rel["g100"]
    SA.END_ART = head_tree("dispend")
    return {"one_s": trees, "g100": rel["g100"], "dispend": rel["dispend"],
            "half": os.path.relpath(os.environ["TDR_ART_DIR"], REPO_ROOT)}


def _sidecar(session, stem):
    hits = glob.glob(os.path.join(REPO_ROOT, "data", "room_*", f"session_{session}",
                                  f"{stem}.gt.json"))
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def _truth_at(sc, t):
    import numpy as np
    for p in sc.get("passes", []):
        at, ac = p["anchor_times"], p["anchor_coords"]
        if at[0] <= t <= at[-1]:
            return (float(np.interp(t, at, [c[0] for c in ac])),
                    float(np.interp(t, at, [c[1] for c in ac])))
    return None


def _snapshot():
    """(path, size, mtime) of every file in the shipped half-stride trees."""
    out = {}
    for root in (os.path.join(REPO_ROOT, "runs", "artefacts_half"),
                 os.path.join(REPO_ROOT, "runs", "constrained", "windows_half")):
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                p = os.path.join(dp, f)
                st_ = os.stat(p)
                out[p] = (st_.st_size, st_.st_mtime_ns)
    return out


def _pa_bound(A, C, RC):
    want = os.path.abspath(head_tree("half"))
    got = {"common.ART_DIR": os.path.abspath(C.ART_DIR),
           "artefacts.POST_DIR": os.path.abspath(A.POST_DIR),
           "recordings.ART_DIR": os.path.abspath(RC.ART_DIR),
           "recordings.WINDOWS_ROOT": RC.WINDOWS_ROOT}
    assert got["common.ART_DIR"] == want and got["recordings.ART_DIR"] == want, got
    assert got["artefacts.POST_DIR"] == os.path.join(want, "posteriors"), got
    assert got["recordings.WINDOWS_ROOT"] == PA_WINDOWS, got
    return got


def do_measure(lattice: str) -> int:
    shipped_snapshot = _snapshot()
    if lattice == "one":
        # THE ONE LATTICE (2026-09-23d): NO root is set by hand. The stage modules' own defaults,
        # read from pipeline/constrained/lattice.py, must land on the press-aligned trees, and the
        # rows must equal the hand-rooted `pa` rows pass for pass. That is the whole check.
        assert "TDR_ART_DIR" not in os.environ and "TDR_WINDOWS_ROOT" not in os.environ, \
            "the one-lattice check must run with NO roots set by hand"
    if lattice == "pa":
        assert os.environ.get("TDR_WINDOWS_ROOT") == PA_WINDOWS
        assert os.path.abspath(os.environ.get("TDR_ART_DIR", "")) == os.path.abspath(head_tree("half"))
        # BIND THE PRESS-ALIGNED ROOTS FIRST. Only `artefacts` (MODEL_DIR, POST_DIR) and
        # `recordings` (features, rssi, gate energy) build paths from the artefact root, and both
        # bind it at import. They are imported now, under the press-aligned root, and asserted.
        import pipeline.constrained.artefacts as _A
        import pipeline.constrained.common as _C
        import pipeline.constrained.recordings as _RC
        _bound = _pa_bound(_A, _C, _RC)
        # THEN, AND ONLY FOR THE IMPORT-TIME GUARDS: n2_arms asserts the environment variable is
        # literally artefacts_half, and `_guard.assert_isolated` checks the same. Every path is
        # already bound above; the shipped trees are snapshotted and must be byte-for-byte
        # untouched at the end, which is what makes this safe rather than merely convenient.
        os.environ["TDR_ART_DIR"] = os.path.join(REPO_ROOT, "runs", "artefacts_half")
    elif lattice == "shipped":
        # "shipped" here means the GRID lattice, the one shipped until 2026-09-23d
        assert os.environ.get("TDR_WINDOWS_ROOT") == os.path.join("runs", "constrained", "windows_half")
        assert os.path.abspath(os.environ.get("TDR_ART_DIR", "")) == os.path.join(REPO_ROOT, "runs", "artefacts_half")
    import numpy as np
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE, assert_motion_model, shipped_pieces
    from pipeline.constrained.render_display import simulate_walk, xy_of
    from pipeline.constrained.s2_display import arc_of_xy, end_emissions
    from pipeline.constrained.s2a_dispend import PAIRINGS
    from pipeline.constrained.common import tag_of
    from pipeline.constrained.q4_arms import start_terms as _st_terms
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.sb2_structural import press_ends
    import pipeline.constrained.decoder as _Dm
    import pipeline.constrained.decoder2 as _D2m
    roots = _repoint_heads() if lattice == "pa" else {"shipped": True}
    if lattice == "one":
        import pipeline.constrained.artefacts as _A1
        import pipeline.constrained.common as _C1
        import pipeline.constrained.g2_multihead as _G2
        import pipeline.constrained.g3_final as _G3
        import pipeline.constrained.recordings as _RC1
        import pipeline.constrained.s2a_dispend as _SA
        roots = {"bound": _pa_bound(_A1, _C1, _RC1),
                 "one_s": _G2.ONE_S_TREES, "g100": _G3.G100_TREE, "dispend": _SA.END_ART}
        assert roots["one_s"] == {0: os.path.relpath(head_tree("fh1s"), REPO_ROOT),
                                  1: os.path.relpath(head_tree("g1s1"), REPO_ROOT),
                                  2: os.path.relpath(head_tree("g1s2"), REPO_ROOT)}, roots
        assert roots["g100"] == os.path.relpath(head_tree("g100"), REPO_ROOT), roots
        assert os.path.abspath(roots["dispend"]) == os.path.abspath(head_tree("dispend")), roots
    if lattice == "pa":
        _pa_bound(_A, _C, _RC)                     # still bound after every stage module imported
        roots["bound"] = _bound
    t_all = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    assert_motion_model()
    lag_w = int(round(LAG / STRIDE))
    rows, fails, pool_info = [], [], {}
    for tr_s, te_s in PAIRINGS:
        tag = tag_of(tr_s, te_s, False)
        try:
            src, info = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
            pool_info[tag] = info
            if src is None:
                fails.append({"tag": tag, "error": "no pool emissions"})
                continue
            e_end, _cov = end_emissions(tag, tr_s, te_s, st, alpha)
            if e_end is None:
                fails.append({"tag": tag, "error": "no display head posteriors"})
                continue
            opts = shipped_opts(st, tr_s)
            opts["entry"] = "soft"
            opts["entry_window_m"] = 1.0
            opts["start_term"] = _st_terms(tr_s, te_s, st, 0.5)
            for stem, rec, ge, e in src:
                presses = press_ends(rec.session, rec.stem)
                sc = _sidecar(rec.session, rec.stem)
                pstart = {int(q["pass_id"]): float(q["t_start"]) for q in sc.get("passes", [])}
                t = np.asarray(rec.t0, float)
                _Dm.MAX_ADVANCE_M = DISPLAY_CAP_M_PER_WINDOW
                _D2m._LT_CACHE.clear()
                rr = night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, opts, None,
                                 want_display=True, display_lags_w=(lag_w,),
                                 display_to_horizon=True, display_alt_e={"end": e_end[stem]},
                                 display_alt_flatten={"end": PRIOR_F}, display_lead_in_w=0)
                _Dm.MAX_ADVANCE_M = None
                _D2m._LT_CACHE.clear()
                for r in rr:
                    pid = int(r["pass_id"])
                    L = (r["display_locked"] or {}).get(f"{lag_w}|{DELAY}")
                    if not L or pid not in pstart:
                        continue
                    lo = int(r["lo"])
                    P = pstart[pid]
                    # THE LOCK'S LAST WINDOW, and when it finished recording, against the frame
                    # the lock is drawn on (press + LATENCY). Positive = drawn before its evidence.
                    ew = int(L["lo_disp"]) + int(L["lock_step"]) + int(L["evidence_horizon_w"])
                    lock_bound = (float(t[ew]) + 2.0 - (P + LATENCY)) if ew < len(t) else None
                    row = {"key": f"{tag}|{rec.session}|{rec.stem}|{pid}", "tag": tag,
                           "true": r["true_line"], "lock_line": L["lock_line"],
                           "lock_correct": bool(L["lock_correct"]),
                           "lock_source": L.get("lock_line_source"),
                           "final_line": r["final_line"],
                           "final_correct": bool(r["final_line"] == r["true_line"]),
                           "lo_start_rel_press_s": float(t[lo]) - P,
                           "lock_evidence_end_minus_frame_s": lock_bound}
                    lpath = (L.get("paths_alt") or {}).get("end") or L["path"]
                    a_, _b = st.slice_of[L["lock_line"]]
                    ent = xy_of(st, a_)
                    if lpath:
                        s0 = int(lpath[0]["state"])
                        p0 = xy_of(st, s0)
                        row["first_decoded_to_entry_m"] = float(np.hypot(p0[0] - ent[0],
                                                                         p0[1] - ent[1]))
                        hold = 0
                        for q in lpath[1:]:
                            if int(q["state"]) != s0:
                                break
                            hold += 1
                        row["decoder_hold_s"] = hold * STRIDE
                    t_dec0 = (float(t[lo]) + 2.0 - HEAD_OFFSET_S) + LATENCY
                    tp_video = float(presses[pid]) + LATENCY
                    allf = np.arange(float(t[0]), float(t[-1]) + 2.0, 1.0 / FPS)
                    post = [float(x) for x in allf if t_dec0 <= x < tp_video]
                    row["first_decoded_frame_after_lock_s"] = t_dec0 - (P + LATENCY)
                    if lpath and len(post) >= 3:
                        sim = simulate_walk(lpath, st, t_dec0, tp_video, ent, L["lock_line"],
                                            STRIDE, 0, FPS, None,
                                            lambda q: _truth_at(sc, float(q) - LATENCY),
                                            frames=post, lead=False, shift_w=SHIFT_W)
                        d, sgn, early = [], [], []
                        for x_, p_, g_ in zip(post, sim["red"], sim["green"]):
                            if p_ is None or g_ is None:
                                continue
                            dd = float(np.hypot(p_[0] - g_[0], p_[1] - g_[1]))
                            d.append(dd)
                            if x_ < t_dec0 + EARLY_S:
                                early.append(dd)
                            try:
                                sgn.append(float(arc_of_xy(st, L["lock_line"], p_)
                                                 - arc_of_xy(st, L["lock_line"], g_)))
                            except Exception:                            # noqa: BLE001
                                pass
                        if d:
                            row["within_pct"] = 100.0 * float(np.mean(np.asarray(d) <= 0.5))
                            row["mean_m"] = float(np.mean(d))
                            row["signed_mean_m"] = float(np.mean(sgn)) if sgn else None
                            row["early_within_pct"] = (100.0 * float(np.mean(np.asarray(early) <= 0.5))
                                                       if early else None)
                            row["late_within_pct"] = (100.0 * float(np.mean(np.asarray(d[len(early):]) <= 0.5))
                                                      if len(d) > len(early) else None)
                    rows.append(row)
            _say(f"measure {lattice} {tag}: {sum(1 for x in rows if x['tag'] == tag)} passes")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            fails.append({"tag": tag, "error": repr(exc), "tb": traceback.format_exc()[-1500:]})
            _say(f"measure {lattice} {tag}: FAILED {exc!r}")
    after = _snapshot()
    if after != shipped_snapshot:
        changed = sorted(set(after.items()) ^ set(shipped_snapshot.items()))[:10]
        raise AssertionError(f"a SHIPPED tree changed during the {lattice} measurement: {changed}")
    roots["shipped_trees_untouched"] = len(after)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"rows_{lattice}.json"), "w", encoding="utf-8") as f:
        json.dump({"lattice": lattice, "roots": roots, "pool_info": pool_info, "rows": rows,
                   "failures": fails, "minutes": round((time.time() - t_all) / 60.0, 1)}, f,
                  indent=1, default=str)
    _say(f"measure {lattice} DONE: {len(rows)} passes, {len(fails)} failures, "
         f"{(time.time() - t_all) / 60.0:.1f} min")
    return 0 if not fails else 1


# -------------------------------------------------------------------------------------- compare

def _boot(d, n=10000, seed=0):
    import numpy as np
    d = np.asarray(d, float)
    if len(d) == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, size=(n, len(d)), replace=True).mean(axis=1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def _per_pairing(rows, field):
    import numpy as np
    out = {}
    for tag in sorted({r["tag"] for r in rows}):
        v = [bool(r[field]) for r in rows if r["tag"] == tag]
        out[tag] = 100.0 * float(np.mean(v))
    return out


def _decision_block(A, B, field):
    """Shipped (A) against press-aligned (B) for one line decision, every reading beside it."""
    import numpy as np
    pa, pb = _per_pairing(A, field), _per_pairing(B, field)
    held = [t for t in pa if t not in SELECTION_FOLDS]
    edge = {}
    for rows, nm in ((A, "shipped"), (B, "press_aligned")):
        edge[nm] = {ln: round(100.0 * float(np.mean([r[field] for r in rows if r["true"] == ln])), 3)
                    for ln in EDGE_LINES}
    d_held = [pb[t] - pa[t] for t in held]
    m, lo, hi = _boot(d_held)
    n_per = {t: sum(1 for r in A if r["tag"] == t) for t in pa}
    passes = {t: int(round((pb[t] - pa[t]) * n_per[t] / 100.0)) for t in held}
    edge_delta_passes = {ln: int(round((edge["press_aligned"][ln] - edge["shipped"][ln]) * 54 / 100.0))
                         for ln in EDGE_LINES}
    return {
        "per_pairing": {t: {"shipped": round(pa[t], 3), "press_aligned": round(pb[t], 3)} for t in pa},
        "session01_folds": {t: {"shipped": round(pa[t], 3), "press_aligned": round(pb[t], 3)}
                            for t in pa if t.endswith("_to_s01")},
        "heldout7_median": {"shipped": round(float(np.median([pa[t] for t in held])), 3),
                            "press_aligned": round(float(np.median([pb[t] for t in held])), 3)},
        "all9_median": {"shipped": round(float(np.median(list(pa.values()))), 3),
                        "press_aligned": round(float(np.median(list(pb.values()))), 3)},
        "edge_recall": edge, "edge_delta_passes": edge_delta_passes,
        "paired_heldout": {"mean_points": m, "ci95": [lo, hi],
                           "a_interval_above_zero": bool(lo is not None and lo > 0)},
        "paired_passes_per_pairing": passes,
        "b_median_passes": float(np.median(list(passes.values()))) if passes else None,
        "b_at_least_two": bool(passes and np.median(list(passes.values())) >= 2),
        "f_no_edge_line_degraded": bool(all(v >= 0 for v in edge_delta_passes.values())),
        "c_monotone": "NOT EVALUABLE: a lattice phase is binary and has no dial (pre-registered)"}


def do_compare() -> int:
    import numpy as np
    with open(os.path.join(OUT_DIR, "rows_shipped.json"), encoding="utf-8") as f:
        RA = json.load(f)
    with open(os.path.join(OUT_DIR, "rows_pa.json"), encoding="utf-8") as f:
        RB = json.load(f)
    A = {r["key"]: r for r in RA["rows"]}
    B = {r["key"]: r for r in RB["rows"]}
    keys = sorted(set(A) & set(B))
    a = [A[k] for k in keys]
    b = [B[k] for k in keys]
    R = {"stage": "y4_pressalign", "prereg": "reports/PREREG_pressalign_2026-09-23.md",
         "n_passes_shipped": len(A), "n_passes_pa": len(B), "n_paired": len(keys),
         "unpaired": {"shipped_only": sorted(set(A) - set(B))[:10],
                      "pa_only": sorted(set(B) - set(A))[:10]},
         "failures": {"shipped": RA["failures"], "pa": RB["failures"]},
         "roots_pa": RB.get("roots")}

    # ---- the reproduction check, which voids the run if it fails
    lock_a = _decision_block(a, b, "lock_correct")
    wa = [r for r in RA["rows"] if r.get("within_pct") is not None]
    wa_ok = [r for r in wa if r["lock_correct"]]
    rep = {"lock_heldout7": lock_a["heldout7_median"]["shipped"],
           "lock_edge": lock_a["edge_recall"]["shipped"],
           "within_whole_walk": float(np.mean([r["within_pct"] for r in wa])),
           "n_within": len(wa),
           "within_correct_line": float(np.mean([r["within_pct"] for r in wa_ok])),
           "n_correct_line": len(wa_ok)}
    want = {"lock_heldout7": 57.5, "lock_edge": {"E_col1": 42.593, "E_col5": 77.778,
                                                  "E_row1": 35.185, "E_row5": 57.407},
            "within_whole_walk": 28.245559635288853, "n_within": 1077,
            "within_correct_line": 53.10452134628239, "n_correct_line": 517}
    ok = (abs(rep["lock_heldout7"] - want["lock_heldout7"]) < 1e-6
          and all(abs(rep["lock_edge"][k] - v) < 0.01 for k, v in want["lock_edge"].items())
          and abs(rep["within_whole_walk"] - want["within_whole_walk"]) < 1e-6
          and rep["n_within"] == want["n_within"]
          and abs(rep["within_correct_line"] - want["within_correct_line"]) < 1e-6
          and rep["n_correct_line"] == want["n_correct_line"])
    R["reproduction_check"] = {"measured": rep, "expected": want, "PASSED": bool(ok)}

    # ---- the lock and the committed answer
    R["lock"] = lock_a
    R["committed_semibounded"] = _decision_block(a, b, "final_correct")

    # ---- the causal bound on the lock, per pass, both lattices
    def cb(rows):
        v = np.array([r["lock_evidence_end_minus_frame_s"] for r in rows
                      if r.get("lock_evidence_end_minus_frame_s") is not None], float)
        lo_ = np.array([r["lo_start_rel_press_s"] for r in rows], float)
        return {"n": int(len(v)), "median_s": float(np.median(v)), "max_s": float(v.max()),
                "min_s": float(v.min()), "late_passes": int((v > 1e-5).sum()),
                "lo_start_rel_press_median_s": float(np.median(lo_)),
                "lo_start_rel_press_range_s": [float(lo_.min()), float(lo_.max())]}
    R["lock_causal_bound"] = {"shipped": cb(a), "press_aligned": cb(b),
                              "ARM_IS_CAUSAL": cb(b)["late_passes"] == 0}

    # ---- the entry hold, correct-lock walks on each side
    def hold(rows):
        ok_ = [r for r in rows if r["lock_correct"] and r.get("first_decoded_to_entry_m") is not None]
        d0 = np.array([r["first_decoded_to_entry_m"] for r in ok_], float)
        h = np.array([r.get("decoder_hold_s") or 0.0 for r in ok_], float)
        fd = np.array([r["first_decoded_frame_after_lock_s"] for r in ok_], float)
        return {"n": len(ok_), "first_decoded_at_entry_pct": 100.0 * float(np.mean(d0 <= AT_ENTRY_M)),
                "first_decoded_to_entry_mean_m": float(d0.mean()),
                "first_decoded_to_entry_median_m": float(np.median(d0)),
                "decoder_hold_mean_s": float(h.mean()), "decoder_hold_median_s": float(np.median(h)),
                "decoder_hold_over_0.5s_pct": 100.0 * float(np.mean(h > 0.5 + 1e-9)),
                "first_decoded_frame_after_lock_median_s": float(np.median(fd))}
    both_ok = [k for k in keys if A[k]["lock_correct"] and B[k]["lock_correct"]
               and A[k].get("decoder_hold_s") is not None and B[k].get("decoder_hold_s") is not None]
    dh = [B[k]["decoder_hold_s"] - A[k]["decoder_hold_s"] for k in both_ok]
    m, lo, hi = _boot(dh)
    R["entry_hold"] = {"shipped": hold(a), "press_aligned": hold(b),
                       "paired_on_walks_correct_under_both": {
                           "n": len(both_ok), "hold_delta_mean_s": m, "ci95": [lo, hi]}}

    # ---- whole-walk tracking, with the early-versus-late split
    def trk(rows, field):
        v = [r[field] for r in rows if r.get(field) is not None]
        return float(np.mean(v)) if v else None
    tr = {}
    for field in ("within_pct", "early_within_pct", "late_within_pct"):
        pk = [k for k in keys if A[k].get(field) is not None and B[k].get(field) is not None]
        m, lo, hi = _boot([B[k][field] - A[k][field] for k in pk])
        pk_ok = [k for k in pk if A[k]["lock_correct"] and B[k]["lock_correct"]]
        m2, lo2, hi2 = _boot([B[k][field] - A[k][field] for k in pk_ok])
        tr[field] = {"shipped_all": trk(a, field), "pa_all": trk(b, field),
                     "shipped_correct_line": trk([r for r in a if r["lock_correct"]], field),
                     "pa_correct_line": trk([r for r in b if r["lock_correct"]], field),
                     "paired_all": {"n": len(pk), "points": m, "ci95": [lo, hi],
                                    "NO_WORSE": bool(hi is not None and hi >= 0)},
                     "paired_correct_under_both": {"n": len(pk_ok), "points": m2,
                                                   "ci95": [lo2, hi2]}}
    R["tracking"] = tr

    L = R["lock"]
    R["verdict"] = {
        "reproduction_check_passed": R["reproduction_check"]["PASSED"],
        "lock_arm_causal": R["lock_causal_bound"]["ARM_IS_CAUSAL"],
        "lock": {"a": L["paired_heldout"]["a_interval_above_zero"], "b": L["b_at_least_two"],
                 "c": L["c_monotone"], "f": L["f_no_edge_line_degraded"]},
        "SHIPS_A_DECISION_CHANGE": False,
        "why": ("(c) cannot be evaluated for a binary lattice change, so by the rule as written "
                "no decision change ships from this arm; if (a), (b), (f) and the causal bound "
                "pass it goes to the operator as a decision"),
        "display_tracking_no_worse": tr["within_pct"]["paired_all"]["NO_WORSE"]}
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    _say(f"compare DONE: reproduction {'PASSED' if ok else 'FAILED'}; lock held-out "
         f"{L['heldout7_median']['shipped']} -> {L['heldout7_median']['press_aligned']}; "
         f"late locks {R['lock_causal_bound']['shipped']['late_passes']} -> "
         f"{R['lock_causal_bound']['press_aligned']['late_passes']}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cut", "prep", "prep-shared", "prep-head", "prep-pos",
                                    "measure", "compare"])
    ap.add_argument("--one", action="store_true")
    ap.add_argument("--head", choices=sorted(HEADS))
    ap.add_argument("--lattice", choices=["shipped", "pa", "one"])
    a = ap.parse_args(argv)
    if a.cmd == "cut":
        return do_cut(a.one)
    if a.cmd == "prep":
        return do_prep()
    if a.cmd == "prep-shared":
        return prep_shared()
    if a.cmd == "prep-head":
        return prep_head(a.head)
    if a.cmd == "prep-pos":
        return prep_pos()
    if a.cmd == "measure":
        return do_measure(a.lattice)
    if a.cmd == "compare":
        return do_compare()
    raise SystemExit(f"{a.cmd}: not yet written")


if __name__ == "__main__":
    sys.exit(main())
