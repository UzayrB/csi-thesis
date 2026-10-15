"""STEP 2: DISPLAY POSITION, TWO ARMS, HEAD TO HEAD.

THE QUESTION. The dot shows where the walker was at the window's CENTRE, about a second before the
frame it is drawn on. Step 0 removed the forward projection that used to hide that, so the lag is
now visible and honest. This stage asks whether the lag can be closed FROM THE SIGNAL.

DISP-SHORT is VOID and was marked so in the pre-registration before this stage was written: every
one of the five shipped pool heads reads a (n, 3, 300, 107) tensor, and 300 samples at 150 Hz is a
2.0 s window. The three heads named for one second are one second of STRIDE. There is no shorter
window to take a position from, so the arm has nothing to run on.

DISP-END is the surviving arm: a head of the same architecture trained on the position at the
window END. It supplies emissions to ONE thing, the restricted along-line Viterbi that runs after
the lock. The committed line, the lock step and the locked line are the shipped pool's on both
arms and are identical between them, which is checked rather than asserted.

THE FOUR TESTS were fixed in the pre-registration before any DISP-END weight existed: dwell drift,
the pace shortcut, substitution under the generalised rule, and causality at +0.000 s. An arm that
fails any one of them does not ship however good its error is.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("s2_display", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import glob                                                                       # noqa: E402
import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import REPO, status, tag_of                      # noqa: E402
from pipeline.constrained.fh_common import boot_ci, check_contract, claim_fh, release, save  # noqa
from pipeline.constrained.g3_final import shipped_pool_emissions                  # noqa: E402
from pipeline.constrained.night_arms import night_track                           # noqa: E402
from pipeline.constrained.night_common import STRIDE, assert_motion_model, shipped_pieces  # noqa
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline      # noqa: E402
from pipeline.constrained.render_display import simulate_walk, xy_of              # noqa: E402
from pipeline.constrained.s2a_dispend import (PAIRINGS, end_labelled_windows,     # noqa: E402
                                              posterior_path)

STAGE = "s2_display"
FPS = 10
LAG = WINDOW_S / 2.0          #: the strict causal lag, 1.0 s
DELAY = 1.5                   #: the internal lock, as step 3 will render it
FIRST_FRAME_S = WINDOW_S / 2.0
#: one state spacing. The finest along-line change the chain can represent, and therefore the
#: tolerance the substitution test counts a change at. Fixed in the pre-registration.
SUB_TOL_M = 0.25
PREREG = os.path.join(REPO, "runs", "PREREGISTRATION_display_position_2026-09-20.json")


# --------------------------------------------------------------------------- geometry helpers

def arc_of_xy(st, line: str, xy) -> float:
    """Where a point falls ALONG one chain, in metres of arc. Nearest state, spacing 0.25 m."""
    a, b = st.slice_of[line]
    p = np.asarray(st.xy)[a:b]
    d = np.linalg.norm(p - np.asarray(xy, float)[None, :], axis=1)
    return float(np.asarray(st.s_of)[a + int(np.argmin(d))])


def xy_at_arc(st, line: str, s_m: float):
    """The point on a chain at a given arc, clamped to the chain. Always a decoded state's own xy."""
    a, b = st.slice_of[line]
    s = np.asarray(st.s_of)[a:b]
    k = int(np.argmin(np.abs(s - float(s_m))))
    q = np.asarray(st.xy)[a + k]
    return (float(q[0]), float(q[1]))


def sidecar(session: str, stem: str) -> dict:
    hits = glob.glob(os.path.join(REPO, "data", "room_*", f"session_{session}", f"{stem}.gt.json"))
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def truth_at(sc: dict, t: float):
    for p in sc.get("passes", []):
        at, ac = p["anchor_times"], p["anchor_coords"]
        if at[0] <= t <= at[-1]:
            return (float(np.interp(t, at, [c[0] for c in ac])),
                    float(np.interp(t, at, [c[1] for c in ac])))
    return None


def training_mean_pace(tr_s) -> dict:
    """The TRAINING-SET mean walking pace, metres per second, for the pace-shortcut baseline.

    Measured from the anchors of the training sessions alone: line length over the time between
    the first and last press. It never sees the test side.
    """
    from pipeline.constrained import paths as P
    lines = P.load_paths()
    v = []
    for sid in tr_s:
        for p in glob.glob(os.path.join(REPO, "data", "room_*", f"session_{sid}", "*.gt.json")):
            with open(p, encoding="utf-8") as f:
                sc = json.load(f)
            for ps in sc.get("passes", []):
                at, nm = ps.get("anchor_times") or [], str(ps.get("path_name", ""))
                if len(at) < 2 or nm not in lines:
                    continue
                pts = np.asarray(lines[nm], float)
                ln = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
                dt = float(at[-1]) - float(at[0])
                if dt > 0.5:
                    v.append(ln / dt)
    return {"mean_m_per_s": float(np.mean(v)) if v else None, "n_passes": len(v),
            "median_m_per_s": float(np.median(v)) if v else None,
            "from": "the TRAINING sessions' anchor presses only"}


# --------------------------------------------------------------------------- the end emissions

def end_emissions(tag, tr_s, te_s, st, alpha, variant: str = "",
                  include_edge: bool = False):
    """{stem: emission} from the DISP-END head, scaled by ITS OWN training marginal.

    The shipped emission divides the posterior by the cell marginal of the head's training labels.
    DISP-END's labels are different labels, so it gets its own marginal: using the centre-labelled
    one would mix two arms inside a single quantity.
    """
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.emissions import cell_marginal, scaled_cell_emission
    p = posterior_path(tag, variant)
    if not os.path.exists(p):
        return None, None
    # THE MARGINAL MUST MATCH THE HEAD. An edge-trained head has a different label
    # distribution, heavier near the tape entry, so dividing by the base head's
    # marginal would mix two arms inside one quantity.
    tr, cov = end_labelled_windows(tr_s, with_features=False, include_edge=include_edge)
    marg = cell_marginal(tr.xy, 25)
    out = {stem: scaled_cell_emission(b["prob"].astype(float), st.xy, 25, marg, alpha=alpha)
           for stem, b in sorted(read_full_posteriors(p).items())}
    return out, cov


# --------------------------------------------------------------------------- test (i) dwell drift

def dwell_drift(session: str, post_path: str) -> dict:
    """How far one head's estimate TRAVELS while the participant stands still.

    Measured on the grid dwells, where the truth does not move at all. The estimate is the
    posterior mean over the 25 cell centres, which is the head's own output and not a decoded
    state, so the decoder's motion model cannot flatter or spoil it.

    Two numbers. The mean speed of the estimate in metres per second, and the direction
    consistency: the resultant length of the unit step directions, 1.0 for a straight march and
    near 0 for jitter about a point. A head that has learned to MOVE rather than to locate shows
    both a high speed and a high consistency.
    """
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.grid import centres
    cc = centres(25)
    spd, res, n_runs, n_win = [], [], 0, 0
    for stem, b in sorted(read_full_posteriors(post_path).items()):
        mode = np.asarray(b["mode"]).astype(str)
        t = np.asarray(b["t0"], float)
        xy = np.asarray(b["xy"], float)
        prob = np.asarray(b["prob"], float)
        est = prob @ cc
        g = np.flatnonzero(mode == "grid")
        if not len(g):
            continue
        # one run per contiguous dwell at ONE labelled cell: the participant is standing still
        runs, i = [], 0
        while i < len(g):
            j = i
            while (j + 1 < len(g) and g[j + 1] == g[j] + 1
                   and np.allclose(xy[g[j + 1]], xy[g[i]], equal_nan=True)):
                j += 1
            if j - i >= 3:
                runs.append(g[i:j + 1])
            i = j + 1
        for r in runs:
            d = np.diff(est[r], axis=0)
            dt = np.diff(t[r])
            ok = dt > 1e-6
            if ok.sum() < 3:
                continue
            step = np.linalg.norm(d[ok], axis=1)
            spd += list(step / dt[ok])
            u = d[ok][step > 1e-9] / step[step > 1e-9][:, None]
            if len(u) >= 3:
                res.append(float(np.linalg.norm(u.mean(axis=0))))
            n_runs += 1
            n_win += len(r)
    return {"session": session, "n_dwell_runs": n_runs, "n_windows": n_win,
            "mean_drift_m_per_s": float(np.mean(spd)) if spd else None,
            "median_drift_m_per_s": float(np.median(spd)) if spd else None,
            "direction_consistency": float(np.mean(res)) if res else None,
            "definition": ("mean speed of the posterior-mean estimate across consecutive windows "
                           "of a static dwell, and the resultant length of its unit step "
                           "directions")}


# --------------------------------------------------------------------------- the per-pass display

def walk_frames(t, lo, t_press):
    """The renderer's own frame grid, filtered to this walk. Identical for every arm."""
    fr = np.arange(float(t[0]), float(t[-1]) + WINDOW_S, 1.0 / FPS)
    t_start = float(t[lo]) + WINDOW_S / 2.0
    return [float(x) for x in fr if t_start <= x < t_press], t_start


def draw(path, st, t_start, t_press, line, frames):
    """The drawn red positions on these frames, by the same loop the renderer uses."""
    if not path or not frames:
        return {}, []
    sim = simulate_walk(path, st, t_start, t_press, xy_of(st, path[0]["state"]), line,
                        STRIDE, 0, FPS, None, lambda _t: None, frames=frames)
    return {round(f, 4): p for f, p in zip(sim["frames"], sim["red"])}, sim["violations"]


def score_frames(drawn, sc, st, line, pace_advance_m=None):
    """Position-NOW error: the distance from the drawn dot to the truth AT THAT FRAME'S TIME."""
    err, within, jumps = [], 0, 0
    order = sorted(drawn)
    prev = None
    for f in order:
        p = drawn[f]
        if p is None:
            continue
        if pace_advance_m is not None:
            p = xy_at_arc(st, line, arc_of_xy(st, line, p) + pace_advance_m)
        g = truth_at(sc, f)
        if g is not None:
            d = float(np.hypot(p[0] - g[0], p[1] - g[1]))
            err.append(d)
            within += int(d <= 0.5)
        if prev is not None and float(np.hypot(p[0] - prev[0], p[1] - prev[1])) > 0.5:
            jumps += 1
        prev = p
    return {"n": len(err), "within_n": int(within),
            "mean_error_m": float(np.mean(err)) if err else None,
            "median_error_m": float(np.median(err)) if err else None,
            "within_0_5_pct": (100.0 * within / len(err)) if err else None,
            "jumps_over_0_5m": int(jumps), "errors": err}


def raw_path(e_disp, st, line, lo, hi, lag_w):
    """DISP-RAW: each window's own head output, projected onto the committed line. No training,
    no transition prior, no Viterbi.

    The other display arms read a Viterbi restricted to the committed chain, so the position they
    draw is part radio and part motion model, and the substitution test says how much of each:
    about a third of what the substitution offers, on every one of them. This arm removes the
    model entirely. At window w the drawn state is simply the argmax of that window's own emission
    over the committed line's states, which is the head's answer projected onto the line and
    nothing else. It will be jumpier, and every metre of its progress will have come from the
    radio.

    The evidence horizon is zero by construction: a window's own emission is all it reads, so the
    step drawn at a frame reads exactly the window that has just ended and not one sample more.
    """
    e = np.asarray(e_disp, float)
    a, b = st.slice_of[line]
    out = []
    for i in range(hi - lo + 1):
        w = lo + i
        if w >= len(e):
            w = len(e) - 1
        seg = e[w, a:b]
        k = int(np.nanargmax(np.where(np.isfinite(seg), seg, -np.inf)))
        out.append({"step": i, "window": lo + i, "evidence_window": lo + i, "state": int(a + k),
                    "line": line, "on_chain": True})
    return out


def substitution_on_arc(path_own, path_sub, st, line, rec, sub_rec):
    """The generalised substitution test on a CONTINUOUS quantity, along-line position.

    A step counts as CHANGED when the substituted decode's arc differs from the original's by more
    than one state spacing. The CEILING is the share of the SAME steps whose two TRUTHS differ by
    more than that, which is how much the substitution could have moved the answer at all. Both
    rates are taken over identical steps, so the ratio is a fraction of what was on offer.
    """
    s_of = np.asarray(st.s_of, float)
    xy_o, xy_s = np.asarray(rec.xy, float), np.asarray(sub_rec.xy, float)
    n_sub = len(sub_rec)
    obs, ceil = [], []
    for a, b in zip(path_own, path_sub):
        w = int(a["window"])
        to_, ts_ = xy_o[w] if w < len(xy_o) else None, xy_s[w % n_sub]
        if to_ is None or not np.isfinite(to_).all() or not np.isfinite(ts_).all():
            continue
        obs.append(bool(abs(s_of[int(a["state"])] - s_of[int(b["state"])]) > SUB_TOL_M))
        ceil.append(bool(abs(arc_of_xy(st, line, to_) - arc_of_xy(st, line, ts_)) > SUB_TOL_M))
    return obs, ceil


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    import dataclasses as _dc

    import pipeline.constrained.decoder as _D
    import pipeline.constrained.decoder2 as _D2
    from pipeline.constrained.q4_arms import start_terms as _st_terms
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.sb2_structural import press_ends

    st, cfg0, ne, transit, kind, alpha = shipped_pieces()
    assert_motion_model()
    prereg = json.load(open(PREREG, encoding="utf-8"))["step_2_display_position"]
    lag_w = int(round(LAG / STRIDE))
    # DISP_END_shifted_entry is a DIAGNOSTIC and is outside the ship rule. A1 restricts the
    # decoder's entry to the first 1.0 m of the chain, measured in CENTRE-label coordinates. An
    # end-labelled head names a position about one pace further on, so that window excludes its own
    # answer before a single frame is drawn. This arm widens the window by exactly the pace-times-
    # lag offset so the reader can tell whether a rejection is about the head or about the prior.
    ARMS = ("centre_labelled", "DISP_END", "DISP_RAW", "DISP_END_shifted_entry", "pace_shortcut")
    #: under the revised rule of 2026-09-20 the pace shortcut is a REFERENCE ROW, not a gate: its
    #: labels are interpolated at constant velocity between anchors, which structurally favours a
    #: constant-velocity baseline, so it cannot be used to reject an arm. DISP_END_shifted_entry
    #: stays a diagnostic because it was not one of the briefed arms; what the rule would do with
    #: it is recorded beside the verdict so the choice to promote it is not made here.
    SHIP_ARMS = ("centre_labelled", "DISP_END", "DISP_RAW")

    RES = {"stage": STAGE, "lag_s": LAG, "lock_delay_s": DELAY, "fps": FPS,
           "state_spacing_m": SUB_TOL_M, "preregistration": prereg,
           "arms": list(ARMS), "arms_under_the_ship_rule": list(SHIP_ARMS),
           "DISP_SHORT": prereg["DISP_SHORT"],
           "DISP_END_shifted_entry_is_a_diagnostic": (
               "it is NOT under the ship rule and cannot ship. A1's entry window is expressed in "
               "centre-label coordinates and excludes an end-labelled head's own answer, so this "
               "arm widens it by the pace-times-lag offset to show whether the rejection is about "
               "the head or about the prior."),
           "what_each_arm_changes": ("ONLY the emissions the restricted along-line Viterbi reads "
                                     "after the lock. The committed line, the lock step and the "
                                     "locked line are the shipped pool's and are the SAME object "
                                     "on every arm, not two decodes that happen to agree."),
           "per_pairing": {}, "failures": [], "n_passes": 0,
           "causality": {"per_arm": {},
                         "what_each_bound_asks": {
                             "drawn_window_bound_s": ("had the window being NAMED finished "
                                                      "recording by the frame time"),
                             "evidence_bound_s": ("had the radio that DECODED it finished "
                                                  "recording by the frame time. This is the one "
                                                  "that showed the 2026-09-20 leak; the first "
                                                  "read -0.000 s throughout it")}},
           "tests": {}, "outcomes": {}}

    # the DISPLAY decode, exactly as the render draws it: the 3 m/s ceiling is ON for the display
    # and OFF for the decision, which is what part 3 shipped and is unchanged here.
    _D.MAX_ADVANCE_M = 1.5
    _D2._LT_CACHE.clear()
    cfg = _dc.replace(cfg0, sd_scale=4.5)

    per_pass = {}                                     # stem|pass_id -> {arm: mean error}
    per_pass_within = {}                              # stem|pass_id -> {arm: within 0.5 m}
    frames_tot = {a: 0 for a in ARMS}
    within_tot = {a: 0 for a in ARMS}
    jumps_tot = {a: 0 for a in ARMS}
    err_all = {a: [] for a in ARMS}
    SUB_ARMS = ("DISP_END", "centre_labelled", "DISP_RAW", "DISP_END_shifted_entry")
    sub_obs = {a: [] for a in SUB_ARMS}
    sub_ceil = {a: [] for a in SUB_ARMS}
    paces = {}

    for tr_s, te_s in PAIRINGS:
        tag = tag_of(tr_s, te_s, False)
        try:
            src, pool_info = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
            if src is None:
                RES["failures"].append({"tag": tag, "error": "no shipped pool emissions"})
                continue
            e_end, cov = end_emissions(tag, tr_s, te_s, st, alpha)
            if e_end is None:
                RES["failures"].append({"tag": tag, "error": "no DISP-END posteriors"})
                continue
            pace = training_mean_pace(tr_s)
            paces[tag] = pace
            advance_m = float(pace["mean_m_per_s"]) * LAG       # pace times the centre-to-end lag
            # THE SHIPPED CONFIGURATION, not a bare default. shipped_opts applies the three
            # night-combo arms the decoder actually ships with (family_first, the maxlik final
            # rule and the fitted chain prior) and the soft entry, which is what q4_arms selected
            # A1_A2_0.5 under and what step 1 confirmed it under. default_opts() alone is a
            # different decoder and its figures are not comparable to either.
            opts = shipped_opts(st, tr_s)
            opts["entry"] = "soft"
            opts["entry_window_m"] = 1.0
            opts["start_term"] = _st_terms(tr_s, te_s, st, 0.5)
            node = {"pool": pool_info, "end_label_coverage": cov, "pace": pace,
                    "pace_advance_m": advance_m, "passes": {}}
            n_rec = len(src)
            for k, (stem, rec, ge, e) in enumerate(src):
                sub_stem, sub_rec, _sge, sub_e = src[(k + 1) % n_rec]
                if stem not in e_end or sub_stem not in e_end:
                    continue
                alt = {"end": e_end[stem], "end_shift": e_end[stem],
                       "end_sub": e_end[sub_stem], "end_shift_sub": e_end[sub_stem],
                       "centre_sub": sub_e}
                shift = {"end_shift": advance_m, "end_shift_sub": advance_m}
                rows = night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, opts, None,
                                   want_display=True, display_lags_w=(lag_w,),
                                   display_to_horizon=True, display_alt_e=alt,
                                   display_alt_entry_m=shift)
                presses = press_ends(rec.session, rec.stem)
                sc = sidecar(rec.session, rec.stem)
                t = np.asarray(rec.t0, float)
                for r in rows:
                    pid = int(r["pass_id"])
                    L = r["display_locked"][f"{lag_w}|{DELAY}"]
                    line, li = L["lock_line"], L["lock_step"]
                    frames, t_start = walk_frames(t, r["lo"], float(presses[pid]))
                    post = [x for x in frames if (x - t_start) >= DELAY]
                    if not post:
                        continue
                    hi_disp = L["path"][-1]["window"] if L["path"] else r["lo"]
                    paths = {"centre_labelled": L["path"][li:],
                             "DISP_END": L["paths_alt"]["end"][li:],
                             "DISP_END_shifted_entry": L["paths_alt"]["end_shift"][li:],
                             "DISP_RAW": raw_path(e_end[stem], st, line, r["lo"], hi_disp,
                                                  lag_w)[li:]}
                    raw_sub = raw_path(e_end[sub_stem], st, line, r["lo"], hi_disp, lag_w)[li:]
                    # THE PAIRING KEY CARRIES THE TAG AS WELL AS THE STEM. stem|pass_id is
                    # unique inside ONE pairing and is not unique across nine: sessions 01 and 02
                    # hold recordings with the SAME stem names, so a stem|pass_id dict spanning
                    # pairings silently keeps only the last writer. Measured here on 2026-09-20:
                    # 240 keys survived of 1080 passes, and every paired interval was taken over
                    # that quarter. It is the 2026-09-18 sb3_exitsweep failure wearing a different
                    # collision, and the frame-level totals never showed it because they are
                    # accumulators and were right all along.
                    key = f"{tag}|{rec.stem}|{pid}"
                    row = {"true_line": r["true_line"], "locked_line": line,
                           "lock_correct": bool(L["lock_correct"]), "n_frames": len(post),
                           "substituted_by": sub_stem}
                    drawn_c = None
                    for arm in ("centre_labelled", "DISP_END", "DISP_RAW",
                                "DISP_END_shifted_entry"):
                        drawn, viol = draw(paths[arm], st, t_start + DELAY, float(presses[pid]),
                                           line, post)
                        if arm == "centre_labelled":
                            drawn_c = drawn
                        sco = score_frames(drawn, sc, st, line)
                        row[arm] = {q: v for q, v in sco.items() if q != "errors"}
                        row[arm]["rule_violations"] = len(viol)
                        per_pass.setdefault(key, {})[arm] = sco["mean_error_m"]
                        per_pass_within.setdefault(key, {})[arm] = sco["within_0_5_pct"]
                        frames_tot[arm] += sco["n"]
                        within_tot[arm] += sco["within_n"]
                        jumps_tot[arm] += sco["jumps_over_0_5m"]
                        err_all[arm] += sco["errors"]
                        # THE TWO CAUSAL BOUNDS, per arm, on every drawn frame.
                        # The index is the one simulate_walk actually draws: the path is ALREADY
                        # sliced at the lock step, so subtracting the lag again reads two windows
                        # too early and reports a spurious -1.000 s. That double subtraction is
                        # the same mistake c1_causal made in June and it is not repeated here.
                        cz = RES["causality"]["per_arm"].setdefault(
                            arm, {"drawn_window_bound_s": -9.0, "evidence_bound_s": -9.0,
                                  "frames_checked": 0, "violations": 0})
                        for x in post:
                            i_ = int(np.floor((x - (t_start + DELAY)) / STRIDE))
                            if not (0 <= i_ < len(paths[arm])):
                                continue
                            step = paths[arm][i_]
                            w_ = int(step["window"])
                            ew_ = int(step.get("evidence_window", w_))
                            if w_ >= len(t):
                                continue
                            gap = float(t[w_] + WINDOW_S - x)
                            egap = float(t[min(ew_, len(t) - 1)] + WINDOW_S - x)
                            cz["drawn_window_bound_s"] = max(cz["drawn_window_bound_s"], gap)
                            cz["evidence_bound_s"] = max(cz["evidence_bound_s"], egap)
                            cz["frames_checked"] += 1
                            cz["violations"] += int(max(gap, egap) > 1e-9)
                    # TEST (ii) THE PACE SHORTCUT: the centre arm's own dot, advanced along the
                    # committed line by the TRAINING-set mean pace times the centre-to-end lag.
                    # If DISP-END cannot beat this it has learned the pace, not the position.
                    sco_p = score_frames(drawn_c, sc, st, line, pace_advance_m=advance_m)
                    row["pace_shortcut"] = {q: v for q, v in sco_p.items() if q != "errors"}
                    per_pass.setdefault(key, {})["pace_shortcut"] = sco_p["mean_error_m"]
                    per_pass_within.setdefault(key, {})["pace_shortcut"] = sco_p["within_0_5_pct"]
                    frames_tot["pace_shortcut"] += sco_p["n"]
                    within_tot["pace_shortcut"] += sco_p["within_n"]
                    jumps_tot["pace_shortcut"] += sco_p["jumps_over_0_5m"]
                    err_all["pace_shortcut"] += sco_p["errors"]
                    # TEST (iii) SUBSTITUTION on along-line position, on both real arms
                    for arm, sub_p in (("DISP_END", L["paths_alt"]["end_sub"][li:]),
                                       ("centre_labelled", L["paths_alt"]["centre_sub"][li:]),
                                       ("DISP_END_shifted_entry",
                                        L["paths_alt"]["end_shift_sub"][li:]),
                                       ("DISP_RAW", raw_sub)):
                        o_, c_ = substitution_on_arc(paths[arm], sub_p, st, line, rec, sub_rec)
                        sub_obs[arm] += o_
                        sub_ceil[arm] += c_
                    node["passes"][key] = row
                    RES["n_passes"] += 1
            RES["per_pairing"][tag] = node
            status(f"  {tag}: {len(node['passes'])} passes drawn on every arm, pace "
                   f"{pace['mean_m_per_s']:.3f} m/s, advance {advance_m:.3f} m")
        except Exception as exc:                                             # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-900:]})
            status(f"  {tag} FAILED {exc!r}")

    # ----------------------------------------------------------------- the outcomes, per arm
    for arm in ARMS:
        e_ = err_all[arm]
        RES["outcomes"][arm] = {
            "frames": frames_tot[arm],
            "within_0_5m_pct": (100.0 * within_tot[arm] / frames_tot[arm]) if frames_tot[arm] else None,
            "mean_position_now_error_m": float(np.mean(e_)) if e_ else None,
            "median_position_now_error_m": float(np.median(e_)) if e_ else None,
            "jumps_over_0_5m": jumps_tot[arm]}

    def paired_within(a, b):
        """The same pairing, on the share of frames within 0.5 m of where the person is now."""
        ks = sorted(k for k, v in per_pass_within.items()
                    if v.get(a) is not None and v.get(b) is not None)
        d = [per_pass_within[k][b] - per_pass_within[k][a] for k in ks]
        m, lo, hi = boot_ci(d)
        return {"n_pairs": len(ks), "mean_improvement_points": m, "ci95": [lo, hi],
                "median_of_paired_deltas_points": float(np.median(d)) if d else None,
                "interval_above_zero": bool(lo is not None and lo > 0),
                "definition": f"positive means {b} spends more frames within 0.5 m than {a}"}

    def paired(a, b):
        """b minus a over the passes both have, as the improvement of b on a."""
        ks = sorted(k for k, v in per_pass.items()
                    if v.get(a) is not None and v.get(b) is not None)
        d = [per_pass[k][a] - per_pass[k][b] for k in ks]
        m, lo, hi = boot_ci(d)
        return {"n_pairs": len(ks), "mean_improvement_m": m, "ci95": [lo, hi],
                "median_of_paired_deltas_m": float(np.median(d)) if d else None,
                "difference_of_medians_m": (float(np.median([per_pass[k][a] for k in ks]))
                                            - float(np.median([per_pass[k][b] for k in ks])))
                if ks else None,
                "interval_above_zero": bool(lo is not None and lo > 0),
                "definition": f"positive means {b} is closer to where the person is than {a}"}

    # ----------------------------------------------------------------- the four tests
    T = RES["tests"]
    T["ii_pace_shortcut"] = paired("pace_shortcut", "DISP_END")
    # NOT A GATE since the operator's revision of 2026-09-20. Kept as a reference row because it
    # bounds what the lag is worth, but the position labels are interpolated at CONSTANT VELOCITY
    # between anchor presses, so a constant-velocity baseline is favoured by the very quantity it
    # is scored on. Rejecting an arm on it would be rejecting it for not beating the label model.
    T["ii_pace_shortcut"]["IS_A_GATE"] = False
    T["ii_pace_shortcut"]["beats_the_baseline"] = bool(
        T["ii_pace_shortcut"]["interval_above_zero"])
    T["ii_pace_shortcut"]["diagnostic_shifted_entry"] = paired("pace_shortcut",
                                                               "DISP_END_shifted_entry")
    T["ii_pace_shortcut"]["rule"] = ("DISP-END must beat the centre-labelled estimate advanced by "
                                     "the training-set mean pace, with a paired interval above "
                                     "zero, or it has learned the pace rather than the position")

    T["iii_substitution"] = {}
    for arm in SUB_ARMS:
        o_, c_ = sub_obs[arm], sub_ceil[arm]
        obs = 100.0 * float(np.mean(o_)) if o_ else None
        ceil = 100.0 * float(np.mean(c_)) if c_ else None
        ratio = (obs / ceil) if (obs is not None and ceil) else None
        T["iii_substitution"][arm] = {
            "n_steps": len(o_), "observed_change_pct": obs, "ceiling_pct": ceil, "ratio": ratio,
            "tolerance_m": SUB_TOL_M,
            "PASSES": bool(ratio is not None and ratio >= 0.5),
            "rule": ("a step counts as changed when the substituted arc moves by more than one "
                     "state spacing; the ceiling is the share of the same steps whose two truths "
                     "differ by more than that; pass at half the ceiling")}

    PA = RES["causality"]["per_arm"]
    T["iv_causality"] = {
        "per_arm": PA,
        "worst_drawn_window_bound_s": max((v["drawn_window_bound_s"] for v in PA.values()),
                                          default=None),
        "worst_evidence_bound_s": max((v["evidence_bound_s"] for v in PA.values()), default=None),
        "frames_checked": sum(v["frames_checked"] for v in PA.values()),
        "violations": sum(v["violations"] for v in PA.values()),
        "PASSES_per_arm": {a: bool(v["violations"] == 0 and v["drawn_window_bound_s"] <= 1e-9
                                   and v["evidence_bound_s"] <= 1e-9) for a, v in PA.items()},
        "rule": ("over every drawn frame BOTH the window being named and the latest window that "
                 "decoded it must have ENDED by the frame time, so neither bound may exceed "
                 "+0.000 s")}
    T["iv_causality"]["PASSES"] = bool(T["iv_causality"]["PASSES_per_arm"]
                                       and all(T["iv_causality"]["PASSES_per_arm"].values()))

    dwell = {}
    for _tr, te_s in [(("01", "02"), ("03",)), (("01", "03"), ("02",)), (("02", "03"), ("01",))]:
        tag = tag_of(_tr, te_s, False)
        from pipeline.constrained.artefacts import posterior_path as _shipped_pp
        centre_p = _shipped_pp(tag, 25, 24, 0)
        end_p = posterior_path(tag)
        if os.path.exists(centre_p) and os.path.exists(end_p):
            dwell[tag] = {"centre_labelled": dwell_drift(te_s[0], centre_p),
                          "DISP_END": dwell_drift(te_s[0], end_p)}

    def _avg(which, field):
        v = [d[which][field] for d in dwell.values() if d[which][field] is not None]
        return float(np.mean(v)) if v else None
    T["i_dwell_drift"] = {
        "per_pairing": dwell,
        "centre_labelled": {"mean_drift_m_per_s": _avg("centre_labelled", "mean_drift_m_per_s"),
                            "direction_consistency": _avg("centre_labelled",
                                                          "direction_consistency")},
        "DISP_END": {"mean_drift_m_per_s": _avg("DISP_END", "mean_drift_m_per_s"),
                     "direction_consistency": _avg("DISP_END", "direction_consistency")},
        "note": ("the drift is a property of the HEAD, not of what is done with its output "
                 "afterwards, so the shifted-entry diagnostic and DISP-RAW both share DISP-END's "
                 "figure exactly: all three read the same head"),
        "rule": ("the output must not travel on a static dwell; DISP-END fails if its drift is "
                 "materially larger than the centre-labelled head's, which would mean it has "
                 "learned to move rather than to locate")}
    dc, dd = T["i_dwell_drift"]["centre_labelled"], T["i_dwell_drift"]["DISP_END"]
    T["i_dwell_drift"]["ratio_to_centre"] = (
        (dd["mean_drift_m_per_s"] / dc["mean_drift_m_per_s"])
        if (dc["mean_drift_m_per_s"] and dd["mean_drift_m_per_s"]) else None)
    #: MATERIALLY LARGER is fixed here as more than a quarter again, and it is fixed before the
    #: number is read because "materially" with the answer in view is not a rule at all.
    T["i_dwell_drift"]["materially_larger_means"] = "drift more than 1.25 times the centre head's"
    T["i_dwell_drift"]["PASSES"] = bool(T["i_dwell_drift"]["ratio_to_centre"] is not None
                                        and T["i_dwell_drift"]["ratio_to_centre"] <= 1.25)

    # ----------------------------------------------------------------- the ship rule
    # REVISED 2026-09-20, by the operator, before this run. The pace shortcut is a REFERENCE ROW
    # and not a gate: the position labels are interpolated at CONSTANT VELOCITY between anchor
    # presses, so a constant-velocity baseline is structurally favoured by the very quantity it is
    # scored on, and it cannot be used to reject an arm. It is still reported, because it bounds
    # what the lag is worth.
    #
    #   an arm must pass (i) dwell drift and (iv) causality
    #   and on (iii) substitution be NO WORSE than the incumbent centre-labelled display
    #   among the arms that pass, prefer zero jumps over 0.5 m
    #   among those, ship the best mean position-now error over the nine pairings
    inc_ratio = T["iii_substitution"]["centre_labelled"]["ratio"]
    T["iii_substitution"]["incumbent_ratio"] = inc_ratio
    T["iii_substitution"]["rule_is_now"] = ("no worse than the incumbent, not half the ceiling. "
                                            "Half the ceiling is a bar the incumbent itself does "
                                            "not clear, so it cannot separate a challenger from "
                                            "the thing it would replace")
    for a_, v_ in T["iii_substitution"].items():
        if isinstance(v_, dict) and "ratio" in v_:
            v_["NO_WORSE_THAN_INCUMBENT"] = bool(
                v_["ratio"] is not None and inc_ratio is not None
                and v_["ratio"] >= inc_ratio - 1e-9)

    eligible = {}
    for a_ in SHIP_ARMS:
        o_ = RES["outcomes"][a_]
        sub_ = T["iii_substitution"].get(a_) or {}
        gates = {
            # DISP-RAW reads DISP-END's head, so it inherits that head's drift exactly: drift is
            # a property of the head, not of what is done with its output afterwards.
            "i_dwell_drift": (True if a_ == "centre_labelled"
                              else bool(T["i_dwell_drift"]["PASSES"])),
            "iv_causality": bool(T["iv_causality"]["PASSES_per_arm"].get(a_)),
            "iii_no_worse_than_incumbent": bool(sub_.get("NO_WORSE_THAN_INCUMBENT")),
        }
        eligible[a_] = {"gates": gates, "PASSES": all(gates.values()),
                        "jumps_over_0_5m": o_["jumps_over_0_5m"],
                        "mean_position_now_error_m": o_["mean_position_now_error_m"]}
    RES["eligibility"] = eligible
    passing = [a_ for a_, v_ in eligible.items() if v_["PASSES"]]
    # prefer zero jumps, then the best mean position-now error. Lexicographic, in that order.
    ranked = sorted(passing, key=lambda a_: (1 if eligible[a_]["jumps_over_0_5m"] else 0,
                                             eligible[a_]["mean_position_now_error_m"]))
    RES["arms_that_pass"] = passing
    RES["ranking"] = ranked
    RES["SHIPPED_DISPLAY"] = ranked[0] if ranked else "centre_labelled"
    RES["ship_rule"] = ("pass (i) dwell drift and (iv) causality, and on (iii) substitution be no "
                        "worse than the incumbent; among those prefer zero jumps over 0.5 m, then "
                        "the best mean position-now error over nine pairings. The pace shortcut "
                        "is a reference row and not a gate")
    head = paired("centre_labelled", "DISP_END")
    RES["DISP_END_against_the_centre_labelled_display"] = head
    RES["DISP_RAW_against_the_centre_labelled_display"] = paired("centre_labelled", "DISP_RAW")
    RES["diagnostic_shifted_entry_against_the_centre_labelled_display"] = paired(
        "centre_labelled", "DISP_END_shifted_entry")
    RES["within_0_5m_head_to_head"] = {
        b: paired_within("centre_labelled", b)
        for b in ("DISP_END", "DISP_RAW", "DISP_END_shifted_entry", "pace_shortcut")}
    # what the same rule would do with the diagnostic, stated rather than acted on
    d_ = RES["outcomes"]["DISP_END_shifted_entry"]
    d_sub = T["iii_substitution"]["DISP_END_shifted_entry"]
    RES["if_the_diagnostic_were_promoted"] = {
        "arm": "DISP_END_shifted_entry",
        "why_it_is_a_diagnostic": ("it widens A1's entry window, which is stated in centre-label "
                                   "coordinates and excludes an end-labelled head's own answer. "
                                   "It was built to tell whether a rejection was about the head "
                                   "or about the prior, and it was not one of the briefed arms"),
        "would_pass_the_gates": bool(T["i_dwell_drift"]["PASSES"]
                                     and T["iv_causality"]["PASSES_per_arm"].get(
                                         "DISP_END_shifted_entry")
                                     and d_sub.get("NO_WORSE_THAN_INCUMBENT")),
        "jumps_over_0_5m": d_["jumps_over_0_5m"],
        "mean_position_now_error_m": d_["mean_position_now_error_m"],
        "the_decision_to_promote_it_is_not_taken_here": True}
    RES["POST_LOCK_PROGRESS_IS_SUBSTANTIALLY_PRIOR_DRIVEN"] = {
        "finding": ("on the centre-labelled display, on DISP-END and on the widened-entry "
                    "diagnostic, substituting another participant's radio moves the along-line "
                    "position on only about three tenths of the steps where the two truths "
                    "differ. Most of the drawn progress along the committed line is the chain's "
                    "motion model, not the radio."),
        "ratios": {a_: (T["iii_substitution"][a_] or {}).get("ratio")
                   for a_ in SUB_ARMS if a_ in T["iii_substitution"]},
        "this_is_why_DISP_RAW_exists": ("it removes the transition prior entirely, so its ratio "
                                        "says what the radio alone can carry")}
    RES["why"] = (f"{RES['SHIPPED_DISPLAY']} ships"
                  if ranked else
                  "no arm passed every gate, so the centre-labelled display stays")

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "tests", "outcomes"])
    save(STAGE, RES)
    release(lock)

    for a in ARMS:
        o = RES["outcomes"][a]
        note = "" if a in SHIP_ARMS else ("  REFERENCE ROW" if a == "pace_shortcut"
                                          else "  DIAGNOSTIC")
        status(f"  {a:24s} within 0.5 m {o['within_0_5m_pct']:5.2f}%  mean "
               f"{o['mean_position_now_error_m']:.3f} m  jumps {o['jumps_over_0_5m']:3d} over "
               f"{o['frames']} frames{note}")
    for a_, v_ in PA.items():
        status(f"  causality {a_:24s} drawn {v_['drawn_window_bound_s']:+.4f} s  evidence "
               f"{v_['evidence_bound_s']:+.4f} s  violations {v_['violations']} over "
               f"{v_['frames_checked']} frames")
    status(f"  (i) dwell drift ratio {T['i_dwell_drift']['ratio_to_centre']:.3f} PASSES "
           f"{T['i_dwell_drift']['PASSES']}; (ii) pace shortcut is a REFERENCE ROW "
           f"({T['ii_pace_shortcut']['mean_improvement_m']:+.3f} m), not a gate")
    for a_ in SUB_ARMS:
        v_ = T["iii_substitution"][a_]
        status(f"  (iii) substitution {a_:24s} observed {v_['observed_change_pct']:5.1f} over "
               f"ceiling {v_['ceiling_pct']:5.1f}, ratio {v_['ratio']:.2f}, no worse than the "
               f"incumbent {v_['NO_WORSE_THAN_INCUMBENT']}")
    for a_, v_ in RES["eligibility"].items():
        status(f"  eligible {a_:24s} {v_['PASSES']}  gates {v_['gates']}")
    status(f"  RANKING {RES['ranking']}")
    status(f"  SHIPPED DISPLAY = {RES['SHIPPED_DISPLAY']}; {RES['why']}")
    headline(f"STEP 2 DISPLAY: DISP-SHORT void; arms that pass "
             f"{RES['arms_that_pass']}; shipped display = {RES['SHIPPED_DISPLAY']} at "
             f"{RES['outcomes'][RES['SHIPPED_DISPLAY']]['mean_position_now_error_m']:.3f} m mean "
             f"position-now error against the incumbent's "
             f"{RES['outcomes']['centre_labelled']['mean_position_now_error_m']:.3f} m.")
    findings("s2", bool(RES["contract"]["SATISFIED"]), (
        "STEP 2, DISPLAY POSITION. DISP-SHORT is void: every shipped pool head reads a 2.0 s "
        "window, so there is no shorter one to take a position from.\n\n"
        + "\n".join(
            f"  {a}: within 0.5 m of where the person is now "
            f"{RES['outcomes'][a]['within_0_5m_pct']:.2f} percent, mean position-now error "
            f"{RES['outcomes'][a]['mean_position_now_error_m']:.3f} m, "
            f"{RES['outcomes'][a]['jumps_over_0_5m']} jumps over 0.5 m, "
            f"{RES['outcomes'][a]['frames']} frames"
            + ("" if a in SHIP_ARMS else
               (" [REFERENCE ROW, not a gate]" if a == "pace_shortcut" else " [DIAGNOSTIC]"))
            for a in ARMS)
        + f"\n\nHead to head over {head['n_pairs']} passes, DISP-END on the centre-labelled "
          f"display: {head['mean_improvement_m']:+.3f} m, interval "
          f"{[round(x, 3) for x in head['ci95']]}, above zero = {head['interval_above_zero']}.\n\n"
          f"TESTS. (i) dwell drift {T['i_dwell_drift']['DISP_END']['mean_drift_m_per_s']} m/s "
          f"against the centre head's "
          f"{T['i_dwell_drift']['centre_labelled']['mean_drift_m_per_s']}, ratio "
          f"{T['i_dwell_drift']['ratio_to_centre']}, passes {T['i_dwell_drift']['PASSES']}. "
          f"(ii) the pace shortcut is a REFERENCE ROW and not a gate: its labels are interpolated "
          f"at constant velocity, which structurally favours a constant-velocity baseline. "
          f"(iii) substitution, ratio of observed change to ceiling: "
        + ", ".join(f"{a_} {T['iii_substitution'][a_]['ratio']:.2f}" for a_ in SUB_ARMS)
        + f", incumbent {T['iii_substitution']['incumbent_ratio']:.2f}. "
          f"(iv) causality, worst drawn-window bound "
          f"{T['iv_causality']['worst_drawn_window_bound_s']:+.3f} s and worst EVIDENCE bound "
          f"{T['iv_causality']['worst_evidence_bound_s']:+.3f} s over "
          f"{T['iv_causality']['frames_checked']} frames, "
          f"{T['iv_causality']['violations']} violations.\n\n"
          f"POST-LOCK PROGRESS IS SUBSTANTIALLY PRIOR-DRIVEN. "
        + RES["POST_LOCK_PROGRESS_IS_SUBSTANTIALLY_PRIOR_DRIVEN"]["finding"]
        + f"\n\nARMS THAT PASS {RES['arms_that_pass']}, ranked {RES['ranking']}. "
          f"SHIPPED DISPLAY = {RES['SHIPPED_DISPLAY']}. {RES['why']}."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min over {RES['n_passes']} passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
