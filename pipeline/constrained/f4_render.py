"""F4: the demonstration re-rendered for the operator, 2026-09-24. A COPY of `f3_render.py`.

`f3_render.py` is pinned and hashed by freeze 23h, and so are its six videos in
`runs/constrained/demo/`. Neither is touched: this file writes to `runs/constrained/demo_v2/` and
`runs/constrained/fh/f4_render/`. The decode, the lock, the committed decision, switching and V1 to V4
are f3's, line for line. What differs, and nothing else:

  1. THE DISPLAY PHASE. `HEAD_OFFSET_S` (when the display head is taken to name, behind the end of its
     window) is chosen by `reports/tracking/history/2026-09-24_prereg-display-phase.md` on `s0103_to_s02`, not assumed at
     R1's 0.75 s of 2026-09-21. Run with F4_SWEEP=1 (and F4_TAG) to measure the grid; F4_HEAD_OFFSET_S
     sets the value drawn.
  2. THE LAYOUT. A larger room, the legend and the clock in a band above it, clear of RX1.
  3. THE RESULT. At each walk's end the bottom says CORRECT in green or WRONG in red, with the running
     accuracy for this participant and the total over all six, held until the next walk starts. The
     old "lag 1s" label is gone: the display runs 2.0 s behind real time, and that is the only delay
     shown.
  4. THE CAUSAL BOUNDS are computed on the step the dot actually glides towards (SHIFT_W included).
  5. No retired-folder move, no reports/FINDINGS or HEADLINES write.

F3's docstring follows.

PHASE 3: the operator-assisted live demonstration. A RENDER JOB. No decoder change, no training.

WHAT THE MODE IS. The system is told when each walk STARTS. During the walk it shows the
semi-bounded running estimate exactly as the decoder produces it causally, all twelve lines alive.
When the operator presses end it rescores the whole walk and commits the final answer.

THE CAUSALITY ASSERTION IS THE POINT OF THIS STAGE. Every frame drawn during a walk must be
computable from windows up to that frame's time plus the display lag. The provisional sequence is
produced by a forward pass, which is causal by construction, and this stage checks the index
arithmetic that turns it into frames: a frame at time tq may read display index at most
floor((tq - t_start)/stride) - lag_windows. Any frame that reads further ahead fails the render.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated  # noqa: E402
assert_isolated("f4_render", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import REPO, RUN_DIR, status                      # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, load, release, save  # noqa
from pipeline.constrained.night_arms import default_opts, night_track              # noqa: E402
from pipeline.constrained import switching as SW                                  # noqa: E402
from pipeline.constrained.g3_final import shipped_pool_emissions                   # noqa: E402
from pipeline.constrained.render_display import (CENTRE, monotonicity_violations,  # noqa: E402
                                                 on_screen_tracking, simulate_walk, xy_of)
from pipeline.constrained.night_common import (STRIDE, assert_motion_model,        # noqa: E402
                                               pairing_emissions, shipped_pieces)
from pipeline.constrained.n2_arms import fit_chain_prior                           # noqa: E402
from pipeline.constrained.render_display import backward_steps as _back            # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S                            # noqa: E402

#: F4_OUT and F4_ONLY exist for a one-participant preview written somewhere else
DEMO = os.environ.get("F4_OUT") or os.path.join(REPO, "runs", "constrained", "demo_v2")
ONLY = os.environ.get("F4_ONLY")
TAG = os.environ.get("F4_TAG", "s0102_to_s03")
_tr, _te = TAG[1:].split("_to_s")
TRAIN, TEST = tuple(_tr[i:i + 2] for i in range(0, len(_tr), 2)), (_te,)
assert len(_te) == 2, f"{TAG}: one test session only"
SWEEP = os.environ.get("F4_SWEEP") == "1"
STAGE = f"f4_phase_{TAG}" if SWEEP else ("f4_preview" if os.environ.get("F4_ONLY") else "f4_render")
#: reports/tracking/history/2026-09-24_prereg-display-phase.md, fixed before any value was measured
HEAD_OFFSET_GRID = (0.75, 0.625, 0.50, 0.375, 0.25, 0.125, 0.00)
PHASE_TARGET_AHEAD_PCT = 33.5
#: how long the walk's result stays on screen at the least, if the next walk starts sooner
RESULT_HOLD_S = 3.0
FPS = 10
LAG_S = 1.0
SLIDE_S = 0.3
DT_AXIS = ("0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0")
DISPLAY_HYSTERESIS = 1      #: windows a new leader must hold before the dot and highlight move


def _sidecar(stem: str) -> dict:
    """The ground-truth sidecar for THIS run's test session. rb7_demo.sidecar_for is fixed to session
    03, which is right for the demo pairing and wrong for every sweep pairing that tests 01 or 02."""
    import glob
    hits = glob.glob(os.path.join(REPO, "data", "room_*", f"session_{TEST[0]}", f"{stem}.gt.json"))
    assert len(hits) == 1, f"{stem}: {len(hits)} sidecars for session {TEST[0]}"
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def along(room_paths, line, p):
    """Arc position of p along `line`'s straight tape, from its entry, in metres."""
    a = np.asarray(room_paths[line], float)
    u = a[-1] - a[0]
    u = u / float(np.hypot(u[0], u[1]))
    return float((np.asarray(p, float) - a[0]) @ u)


def lead_stats(pairs):
    """(signed along-line lead of red over green, red-green distance) per frame, metres.

    Positive lead is red AHEAD of the walker along the true line. within_0_5m_pct uses the plain
    distance, as every on-screen tracking figure in this project does."""
    v = np.asarray([a for a, _d in pairs], float)
    d = np.asarray([_d for _a, _d in pairs], float)
    if not len(v):
        return {"n_frames": 0}
    return {"n_frames": int(len(v)), "ahead_pct": 100.0 * float(np.mean(v > 0)),
            "signed_mean_m": float(np.mean(v)), "signed_median_m": float(np.median(v)),
            "within_0_5m_pct": 100.0 * float(np.mean(d <= 0.5)), "mean_distance_m": float(np.mean(d))}


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.animation as anim
    import matplotlib.pyplot as plt
    from pipeline.constrained.decoder import decoded_xy
    # truth_at, sidecar_for and room all live in rb7_demo; rc8_demo imports them from there too
    from pipeline.constrained.rb7_demo import room, sidecar_for, truth_at
    from pipeline.constrained.rb10_bounded_demo import bounded_track
    from pipeline.constrained.sb2_structural import press_ends

    lock = claim_fh(STAGE)
    t0 = time.time()
    f2 = load("f2_verdict")
    g3 = load("g3_final")
    r3 = load("r3_lagsweep") or {}
    r1 = load("r1_oldcensus") or {}
    a3 = load("a3_lock") or {}
    b1 = load("b1_motion") or {}
    SH = a3.get("shipped") or {}
    ENTRY = "soft"
    # THE STRICT CAUSAL LAG. A window spans [t0, t0 + WINDOW_S] and may only be drawn once it has
    # ENDED. The render calls the walk's start the window CENTRE, so the first window has ended
    # half a window length after that. Anything shorter draws frames from samples not yet
    # recorded, which is what the 0 s lag was doing.
    LAG = WINDOW_S / 2.0
    # OPERATOR OVERRIDE of the pre-registered delay rule, 2026-09-20, recorded in those words.
    # The rule chose 1.5 s. The operator asked for a shorter wait AND for 0.25 m accuracy to be
    # kept. At the 0.5 s decision rate a 1.25 s wait locks on the SAME step-2 estimate as 0.75 s,
    # so it costs half a second of extra waiting for identical evidence and drags 0.25 m accuracy
    # from 20.2 to 6.2 percent. 0.75 s honours both instructions better than the 1.25 s asked for,
    # and is shipped in its place with the substitution stated. The cost is line accuracy:
    # 49.2 percent against 63.3 at 1.5 s.
    # PART 3: 1.0 s TOTAL LATENCY. There is no visible wait and no parking at the room centre.
    # The dot appears at the FIRST LEGAL FRAME, press + 1.0 s, which is the earliest moment a
    # window has ended, and tracks from then under the strict causal lag. The line lock is still
    # decided internally at the shipped wait, but the display does not wait for it: before the
    # lock it follows the leading candidate, after it the locked chain.
    # THE DELAYED-PLAYBACK TIMELINE, 2026-09-21.
    #
    # The video runs LATENCY seconds behind the wall clock. At video time x the scene shows the
    # moment x - LATENCY, and the decoder is allowed every window that had finished recording by
    # x. Nothing is projected: the future is simply not shown yet. In a live deployment this is
    # what a viewer would see LATENCY seconds after the fact, and the caption says so.
    #
    # It buys the one thing the operator asked for. The line is committed on EVIDENCE seconds of
    # radio, and under a latency of the same size that commitment is already made by the time the
    # walk is shown to begin. So the dot parks at the room centre for exactly LATENCY seconds
    # while it listens, the green marker then appears at the walk's start, and the dot commits and
    # follows it from that instant. No provisional wandering before the commit, and no waiting
    # after it.
    #
    # EVIDENCE is 2.0 s on R6's curve: 55.00 percent line accuracy against 50.00 at 1.5 s, paired
    # +2.87 points with an interval of [0.65, 5.46] that excludes zero. Longer settings measured
    # higher but are not a live claim, because past about the walk duration the lock lands after
    # the walk has ended and reads a retrospective answer.
    DELAY = float(os.environ.get("RENDER_DELAY_S", "2.0"))     # EVIDENCE before the line commits
    LATENCY = float(os.environ.get("RENDER_LATENCY_S", "2.0"))  # how far behind the video runs
    #: when the drawn head is taken to name, behind the end of the window it is read from. f3 used
    #: R1's 0.75 s of 2026-09-21; f4 draws the value reports/tracking/history/2026-09-24_prereg-display-phase.md chose
    HEAD_OFFSET_S = float(os.environ.get("F4_HEAD_OFFSET_S", "0.375"))  # chosen 2026-09-24 17:42
    #: retired 2026-09-21. Under the delayed timeline the dot parks for the whole LATENCY and
    #: there is no separate "first legal frame": by the time the scene starts, three windows have
    #: finished recording. Kept as a named quantity because the causality argument still rests on
    #: it: a window may only be drawn once it has ended, and LATENCY is comfortably larger.
    FIRST_LEGAL_S = WINDOW_S / 2.0
    assert LATENCY >= FIRST_LEGAL_S, (
        f"a {LATENCY:g} s latency is shorter than the {FIRST_LEGAL_S:g} s a {WINDOW_S:g} s window "
        f"needs to finish recording, so the scene would be shown before any window could be read")
    assert LATENCY >= HEAD_OFFSET_S + STRIDE, (
        f"a {LATENCY:g} s latency is shorter than the head's {HEAD_OFFSET_S:g} s offset plus the "
        f"{STRIDE:g} s stride the dot needs to glide towards the NEXT decoded point. Without that "
        f"margin the dot would have to lead into a window that has not finished recording")
    #: the dot waits at the room centre until it has something to say, at the operator's request
    PARK_WHILE_LISTENING = True
    DELAY_OVERRIDE = {
        "pre_registered_rule_chose_s": SH.get("commit_delay_s"),
        "operator_asked_for_s": 1.5, "shipped_s": DELAY,
        "why": ("the operator chose 1.5 s from the causal wait curve. Under the strict rule the "
                "earliest legal lock is 1.0 s, because window lo has not ended before then."),
        "cost": None}
    CAP = None                     # nothing slides: the dot never crosses lines at all
    # R3: the display's own transition prior, chosen over nine pairings under a gate that was
    # loosened POST HOC and is disclosed as such in ACCEPTANCE.md and in the freeze.
    # NOT `r3`: that name is already the lag sweep, twenty lines above, and is read again when
    # ACCEPTANCE.md is built. Shadowing it rendered six videos and then crashed on the markdown.
    r3p = load("r3_prior") or {}
    PRIOR_ARM = r3p.get("SHIPPED_DISPLAY_PRIOR") or "flatten_0.00"
    PRIOR_F = 0.0 if PRIOR_ARM == "DISP_RAW" else float(PRIOR_ARM.split("_")[-1])
    PRIOR_SUBS = (((r3p.get("per_arm") or {}).get(PRIOR_ARM) or {})
                  .get("substitution", {}).get("ratio"))
    # R1: the delay is MEASURED on the display this render actually draws, prior included, and is
    # NOT taken from the training label. DISP-END's label says it names the present; it does not.
    r1ref = load("r1_reference") or {}
    HEAD_MEASURED_S = float(r1ref.get("R2_DELAY_S") or LAG)
    LABEL_DELAY = float((r1ref.get("label_offset_s") or {}).get("DISP_END", 0.0))

    CAPTION = (
        f"THE WHOLE DISPLAY RUNS {LATENCY:g} s BEHIND REAL TIME, which is the live mode's "
        f"latency and its limitation. The dot waits at the room centre for those {LATENCY:g} s "
        f"while it listens, then the green marker appears at the walk's start and the dot has "
        f"already committed to a line. It stays on that line for the whole walk, right or wrong, "
        f"and never switches. Nothing is projected: every position drawn is one the decoder "
        f"produced from radio already recorded.")
    # the CURRENT verdict is g3's, taken on the shipped pool against bounded under the
    # SAME heads; f2 was taken on the single-head arm and is kept only as the earlier record
    verdict_src = "g3_final" if g3 else "f2_verdict"
    verdict_passed = bool((((g3 or f2) or {}).get("verdict") or {}).get("BECOMES_THE_CORE"))
    from pipeline.constrained import paths as P
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    # THE 3 m/s CEILING, asked for by the operator and now measured to help under the locked
    # display: at 1.5 s it takes 0.5 m accuracy from 37.0 to 40.5 percent and the median distance
    # from 0.77 to 0.68 m, and at shorter waits it adds 6.7 points of LINE accuracy. B1 measured it
    # as costing 7.5 points, but B1 measured the PRE-LOCK display where wrong-line errors of about
    # three metres masked a sub-metre along-line lag. That null was an artefact.
    import dataclasses as _dc
    import pipeline.constrained.decoder as _D
    import pipeline.constrained.decoder2 as _D2
    # THE DISPLAY SPEED CAP, 0.80 m per window = 1.6 m/s, swept on 2026-09-21 against the walker's
    # own pace. At the old 1.5 the dot ran ahead of the walker on 72 percent of frames, by more
    # than half a metre on 46. At 0.80 that falls to 61 and 34 percent and every error measure
    # improves: mean 1.164 to 1.094 m, median 0.783 to 0.667, within 0.5 m 33.0 to 38.6 percent.
    # Below 0.65 the cap stops binding, because the chain's own step model is 0.649 m per window,
    # and the dot swings from racing to lagging with error worse than either.
    # IT REMAINS SIGNAL-BASED. A cap constrains the transition model: it forbids motion the radio
    # cannot justify. It does not invent a position, and the emissions are untouched.
    DISPLAY_CAP_M_PER_WINDOW = 0.80
    #: ZERO, and measured rather than assumed. Reaching back one window to start the scene at the
    #: walker's own first press was tried on 2026-09-21 and made everything worse: mean error
    #: 1.094 to 1.339 m, within 0.5 m 38.6 to 20.2 percent, the start gap 1.11 to 1.23 m, and 88
    #: frames where the scene ran ahead of the first press so there was no marker to show at all.
    #: The window before the walk is real radio, but the position decoded from it is poor, and a
    #: bad position at the start is worse than starting a fraction of a second late.
    DISPLAY_LEAD_IN_W = 0
    #: OPERATOR DECISION, 2026-09-23. The drawn dot's phase, in strides, measured over nine
    #: pairings in w1_dotphase. It is a DISPLAY PHASE and not a fitted bias: it changes no
    #: decision and no accuracy figure, and 1.00 (the old lead=True) was measured as
    #: +0.046 m ahead on 52.8 percent of frames. 0.50 keeps the dot slightly BEHIND at
    #: -0.281 m, leading on 33.5 percent. See reports/tracking/history/2026-09-22_prereg-dotphase.md.
    SHIFT_W = 0.50
    _D.MAX_ADVANCE_M = DISPLAY_CAP_M_PER_WINDOW
    _D2._LT_CACHE.clear()
    cfg_dec = _dc.replace(cfg, sd_scale=1.0)      # the DECISION: no ceiling
    cfg = _dc.replace(cfg, sd_scale=4.5)          # the DISPLAY: the speed cap lives here
    MOTION = {
        "display_max_advance_m_per_window": DISPLAY_CAP_M_PER_WINDOW,
        "display_ceiling_m_per_s": DISPLAY_CAP_M_PER_WINDOW / STRIDE,
        "display_sd_scale": 4.5,
        "decision_ceiling": None,
        "cap_chosen_by": ("a sweep on 2026-09-21 against the walker's own pace. 0.80 m per "
                          "window is best on every error measure; below 0.65 the cap stops "
                          "binding because the chain's step model is 0.649 m per window"),
        "why_split": ("the ceiling costs 7.50 points of line accuracy paired [-11.48, -3.15] "
                      "and loses the verdict, but improves along-line progress; the decision "
                      "is taken without it and the display drawn with it")}
    room_paths = P.load_paths()      # the polylines room() draws; NOT the PathStates object
    mm = assert_motion_model()
    status(f"{STAGE} START: the operator-assisted live demonstration. verdict passed="
           f"{verdict_passed}; motion model {mm['step_m_per_window']:.3f} m per window")

    RES = {"stage": STAGE, "verdict_passed": verdict_passed, "verdict_source": verdict_src,
           "tag": TAG, "fps": FPS,
           "lag_s": LAG, "display_latency_s": LATENCY, "display_delay_s": LATENCY,
           "head_measured_offset_s": HEAD_MEASURED_S, "caption": CAPTION,
           "recordings": {}, "failures": [],
           "causality": {"violations": 0, "frames_checked": 0},
           "shipped": {"entry": ENTRY, "display_lag_s": LAG, "commit_delay_s": DELAY,
                       "causal": True, "direction_prior": None,
                       "why_no_direction_prior": ("p3 measured both run-up arms and neither met "
                                                  "the ship rule; nothing from that batch ships"),
                       "end_slide_cap_m_s": CAP, "cross_line_cap_m_s": None,
                       "motion_model": MOTION, "delay_override": DELAY_OVERRIDE,
                       "hysteresis_windows": DISPLAY_HYSTERESIS,
                       "basis": ("entry from r2_softentry, lag and cap from r3_lagsweep, both by "
                                 "the rules pre-registered before any number existed")},
           "rule": {"violations": 0, "frames_checked": 0, "examples": [],
                    "statement": ("every drawn red position is a decoded position or a point on "
                                  "the straight segment between two decoded positions, and "
                                  "nothing is drawn ahead of the latest decode")},
           "dot_visible": {"frames": 0, "frames_without_dot": 0, "expected": 0,
                           "missing_after_first_legal": 0,
                           "contract": ("the dot is absent between walks and until the first "
                                        "analysis window has finished recording, and present on "
                                        "every frame after that until the end press")},
           "causal_bound_s": -9.0,
           # THE SECOND BOUND, added 2026-09-20. causal_bound_s asks whether the window being
           # NAMED had ended by the frame. causal_evidence_bound_s asks whether the radio that
           # decoded it had. The first read a clean -0.000 s through a leak of a full second that
           # only the second one shows, so both are reported and neither stands alone.
           "causal_evidence_bound_s": -9.0,
           "two_bounds": {"causal_bound_s": "t0[window drawn] + WINDOW_S minus the frame time",
                          "causal_evidence_bound_s": ("t0[latest window that entered that step's "
                                                      "Viterbi] + WINDOW_S minus the frame time"),
                          "both_must_be_at_or_below": 0.0},
           "dwell_cut": {"recordings": 0, "frames_removed": 0, "grid_windows_seen": 0,
                         "frames_remaining_inside_a_grid_block": 0,
                         "rule": ("V4: no static dwell footage in a demonstration video. The whole "
                                  "grid block is cut, not excerpted, so frames_remaining_inside_a_"
                                  "grid_block must be 0")},
           "vision_rules": {
               "V1_latency_s": None, "V1_every_walk_same": None,
               "V2_commit_frame_equals_marker_frame": {"walks": 0, "violations": 0,
                                                       "max_gap_s": 0.0},
               "V3_lock_offset_s_distinct_values": None, "V3_lock_offset_s": None,
               "statement": ("V1 the display runs exactly 2.0 s behind real time; V2 the commit "
                             "and the marker are one event; V3 the lock time is structural and "
                             "identical on every walk, so confidence-gated or variable latency is "
                             "forbidden; V4 no dwell footage. See reports/tracking/render-rules.md")},
           "leave_together": {"walks": 0, "max_gap_s": 0.0, "violations": 0,
                              "max_stall_s": 0.0, "stall_violations": 0,
                              "stall_explained_by_the_decoder": 0,
                    "rule": ("rule 6: the first frame on which the marker is shown is "
                                       "the first frame on which the dot is drawn, AND the dot "
                                       "starts moving on its first frame rather than holding "
                                       "still while the marker walks away. Neither leads the "
                                       "other, on any walk, by more than one frame.")},
           "jumps": {"total": 0, "caused_by_the_lock": 0, "caused_by_a_switch": 0,
                     "definition": "a frame-to-frame move of the drawn dot over 0.5 m"}}

    # the shipped configuration from phase 2, rebuilt here
    names = []
    cfg_name = ((g3 or {}).get("shipped_pool") or {}).get("arm") \
        or ((f2 or {}).get("shipped_configuration") or "")
    if "nightcombo" in cfg_name or "pool" in cfg_name:
        names = ["C_family", "G_maxlik", "I_chainprior"]
    uses_pool = "pool" in cfg_name
    uses_F = cfg_name.endswith("_F")
    n2 = json.load(open(os.path.join(RUN_DIR, "night", "n2_arms", "results.json"),
                        encoding="utf-8"))
    arm_opts = {}
    for _t, v in (n2.get("per_pairing") or {}).items():
        for n_, row in (v.get("arms") or {}).items():
            if row and row.get("opts") is not None:
                arm_opts[n_] = {k: ("FIT" if val == "fitted" else val)
                                for k, val in row["opts"].items()}
        break
    prior = fit_chain_prior(st, TRAIN)
    opts = default_opts()
    for n_ in names:
        for k, val in (arm_opts.get(n_) or {}).items():
            opts[k] = prior if val == "FIT" else val
    RES["configuration"] = {"name": cfg_name, "arms": names,
                            "uses_ensemble": bool(uses_F or uses_pool),
                            "uses_pool": uses_pool}

    if uses_pool:
        src, pool_info = shipped_pool_emissions(TAG, TRAIN, TEST, False, st, kind, alpha)
        RES["configuration"]["pool"] = pool_info
        status(f"  rendering from the SHIPPED POOL: {pool_info}")
    else:
        src = pairing_emissions(TAG, TRAIN, TEST, False, st, kind, alpha)
    if src is None:
        status(f"{STAGE}: no posteriors for {TAG}")
        return 1
    if uses_F and not uses_pool:
        from pipeline.constrained.f1_arms import ensemble_emission, one_second_emissions
        one = one_second_emissions(TAG, TRAIN, TEST, False, st, kind, alpha)
        if one:
            src = [(s_, r, g, ensemble_emission(e, one[s_])) for s_, r, g, e in src if s_ in one]
            status("  using the two-head ensemble for the committed answer, as phase 2 shipped")

    # THE SHIPPED PART 2 ARM: A1_A2_0.5, chosen on the held-out selection folds. A1 restricts
    # entry to the first 1.0 m of each chain without pinning it; A2 adds a start-consistency term
    # to the chain totals, fed by the A3 classifier, at weight 0.5.
    from pipeline.constrained.q4_arms import start_terms as _st_terms
    ARM = {"entry_window_m": 1.0, "start_weight": 0.5}
    # APPLY THE ENTRY THIS STAGE REPORTS. Until 2026-09-20 ENTRY was recorded in the results as
    # "soft" and never reached opts, so the render ran the FREE entry prior while claiming the
    # soft one. That matters: A1 restricts the entry to the first 1.0 m of each chain, and under
    # "free" what survives inside that window is flat, while under "soft" it is the first window's
    # own posterior. The shipped arm was selected in q4_arms and confirmed in step 1 under "soft",
    # so the render was drawing a decoder neither of those stages measured.
    opts["entry"] = ENTRY
    opts["entry_window_m"] = ARM["entry_window_m"]
    opts["start_term"] = _st_terms(TRAIN, TEST, st, ARM["start_weight"])
    # THE DISPLAY decode (lock, drawn path) keeps the A2 term alone, exactly as before 2026-09-23d.
    opts_disp = dict(opts)
    # THE COMMITTED decision gains the shipped a_veto_1.0 (pipeline/constrained/veto.py, batch 23d
    # item 3; it passes the ship rule with (f) as AMENDED, POST HOC). It reaches the decision decode
    # only: the lock and the drawn path never read it.
    from pipeline.constrained.veto import A2_WEIGHT, committed_start_terms
    assert float(ARM["start_weight"]) == A2_WEIGHT, "the veto's A2 weight must be the shipped one"
    opts = dict(opts)
    opts["start_term"] = committed_start_terms(TRAIN, TEST, st)
    status(f"  shipped Part 2 arm: {ARM}, start terms for {len(opts['start_term'])} passes")
    # MID-WALK SWITCHING, RENDER_RULES rule 1a, OPERATOR DECISION, display only. Batch 23f: the arm
    # (at most K switches, the final-zone cutoff, the 1.5 m proximity) and theta are the ones
    # `e2_switch` chose by the operator's rule fixed before any number
    # (reports/tracking/history/2026-09-23f_prereg-switching-arms.md). No VALID e2 run, or no arm qualifying, means
    # NO switching (lock-final). The running score adds the SHIPPED committed start term, the same
    # dict the committed decision reads, keyed session|stem|pass_id.
    e2 = load("e2_switch") or {}
    SWITCH = ((e2.get("evaluation") or {}).get("RENDER") if e2.get("VALID") else None)
    SCORER = SW.Scorer(st, cfg_dec, transit) if SWITCH else None
    SW_ADJ = opts["start_term"]
    RES["switching"] = {
        "rule": "RENDER_RULES rule 1a as amended 2026-09-23f", "source": "e2_switch",
        "arm": (SWITCH or {}).get("arm"), "theta": (SWITCH or {}).get("theta"),
        "max_switches": (SWITCH or {}).get("max_switches"), "final_m": (SWITCH or {}).get("final_m"),
        "radius_m": (SWITCH or {}).get("radius_m"),
        "walks": 0, "switches": 0, "w2r": 0, "r2w": 0, "w2w": 0, "jump_m": [],
        "slide_off_segment_frames": 0, "slide_frame_jumps_over_0_5m": 0,
        "decision_evidence_worst_s": -9.0, "target_drawn_worst_s": -9.0,
        "target_evidence_worst_s": -9.0, "switch_in_final_zone": 0, "persistence_violations": 0,
        "returns_to_a_drawn_line": 0, "more_than_max_switches": 0, "earliest_after_lock_s": None,
        "end_on_committed": 0}
    status(f"  mid-walk switching: {SWITCH or 'NONE (no valid e2_switch choice: lock-final)'}")

    # THE SHIPPED DISPLAY, chosen in step 2 over nine pairings and 1080 passes: DISP-END, a
    # display-only head labelled at the window END rather than its centre. It changes ONE thing,
    # which emissions the restricted along-line Viterbi reads after the lock. The committed line,
    # the lock step and the locked line are the shipped pool's and are untouched by it; it never
    # enters the line decision pool. Its dwell drift, its causality at +0.000 s on both bounds and
    # its substitution were all measured before it was allowed near this renderer.
    from pipeline.constrained.s2_display import end_emissions
    s2 = load("s2_display") or {}
    SHIPPED_DISPLAY = (s2.get("SHIPPED_DISPLAY") or "centre_labelled")
    e_end, end_cov = (None, None)
    if SHIPPED_DISPLAY == "DISP_END":
        e_end, end_cov = end_emissions(TAG, TRAIN, TEST, st, alpha)
        if e_end is None:
            SHIPPED_DISPLAY = "centre_labelled"
            status("  DISP-END posteriors are absent; the centre-labelled display is drawn")
    RES["anchor_segment"] = {
        "frames": 0, "off_segment_frames": 0, "shift_w": SHIFT_W,
        "rule": ("RULE 2 EXCEPTION, operator decision 2026-09-23: at the press the dot is\n"
                 "placed at the ENTRY POINT of the committed line, which is not a decoded\n"
                 "position. Every frame between that anchor and the first decoded position\n"
                 "must lie ON the straight segment joining them, so off_segment_frames must\n"
                 "be 0. No pace and no projection: the parameter is elapsed fraction of a\n"
                 "fixed interval, and it cannot run past the first decoded position")}
    RES["shipped"]["display_arm"] = SHIPPED_DISPLAY
    RES["shipped"]["display_arm_source"] = "s2_display, nine pairings, 1080 passes"
    RES["shipped"]["end_label_coverage"] = end_cov
    status(f"  shipped display arm: {SHIPPED_DISPLAY}")

    before = sorted(os.listdir(DEMO)) if os.path.isdir(DEMO) else []
    os.makedirs(DEMO, exist_ok=True)
    lag_w = int(round(LAG / STRIDE))
    acceptance = []
    SWEEP_ACC = {}
    # THE TOTAL the result panel shows: the shipped committed decision over all six participants on
    # this pairing, from d4_headline's per-walk rows (the headline's own answer, which the end text
    # equals walk for walk: end_text_check), and the nine-pairing median beside it.
    TOTAL = {}
    _rv = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "d4_headline", "rows_veto.json")
    if os.path.exists(_rv):
        with open(_rv, encoding="utf-8") as _f:
            _mine = [r for r in json.load(_f) if r["tag"] == TAG]
        TOTAL = {"n": len(_mine), "right": sum(1 for r in _mine if r["final_correct"])}
    _d4 = load("d4_headline") or {}
    if _d4.get("VALID"):
        TOTAL["nine_pairing_median"] = float(_d4["COMMITTED"]["POST_AMENDMENT_SHIPPED"]["all9_median"])
    RES["result_panel_total"] = TOTAL
    for stem, rec, ge, e in src:
        who = stem.replace("participant_", "").split("_")[0]
        if ONLY and who != ONLY:
            continue
        try:
            # TWO DECODES, deliberately. The 3 m/s ceiling costs 7.50 points of line accuracy
            # with a paired interval of [-11.48, -3.15] that excludes zero, and takes the
            # semi-bounded against bounded gap from 7.5 to 15.8 points, which loses the verdict.
            # It also improves along-line progress, 40.7 percent within 0.25 m against 36.6. So
            # the DECISION is taken without it and the DISPLAY is drawn with it, which is what the
            # operator's instruction to keep the ceiling on the display either way asks for.
            import pipeline.constrained.decoder as _Dm
            import pipeline.constrained.decoder2 as _D2m
            _Dm.MAX_ADVANCE_M = None
            _D2m._LT_CACHE.clear()
            rows = night_track(e, rec, st, cfg_dec, transit, ne, ge, STRIDE, opts, None)
            _Dm.MAX_ADVANCE_M = DISPLAY_CAP_M_PER_WINDOW
            _D2m._LT_CACHE.clear()
            alt_disp = ({"end": e_end[stem]} if (e_end and stem in e_end) else None)
            rows_disp = night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, opts_disp, None,
                                    want_display=True, display_lags_w=(lag_w,),
                                    display_to_horizon=True, display_alt_e=alt_disp,
                                    display_alt_flatten=({"end": PRIOR_F} if PRIOR_F else None),
                                    display_lead_in_w=DISPLAY_LEAD_IN_W,
                                    display_switch_paths=bool(SWITCH))
            disp_by_pid = {int(r["pass_id"]): r for r in rows_disp}
            # MID-WALK SWITCHING (batch 23e item 1, operator decision, display only): the running
            # score of every line on the DECISION emissions, wall-clock causal, by the same
            # functions e2_switch measured with. Computed after both decodes, which calibrate the
            # null on this same recording, so the state it reads is the one they left.
            if SWITCH:
                ne.calibrate(e)
                E_sw = SCORER.stack(e, ge, ne)
            # THE COMMIT AT THE OPERATOR'S END PRESS is the bounded rescore over the SAME pooled
            # emissions. That is the whole point of the operator-assisted mode: the person supplies
            # the end, so the committed answer is entitled to use it.
            bt = bounded_track(e, rec, st, None)
            b_line = {int(q["pass_id"]): q["chosen_line"] for q in bt["passes"]}
            b_seq = np.asarray(bt["seq"])
            presses = press_ends(rec.session, rec.stem)
            sc = _sidecar(stem)
            # THE START PRESS. Rule 6 as amended on 2026-09-23 starts the scene at the
            # DELAYED PRESS MOMENT, so the render needs the press itself and not the first
            # window centre. The sidecar's own t_start is that press: it equals
            # anchor_times[0] exactly on every pass, and anchor_coords[0] is the tape entry.
            pstart = {int(q["pass_id"]): float(q["t_start"]) for q in sc.get("passes", [])}
            t = np.asarray(rec.t0, float)
            mode = np.asarray(rec.mode).astype(str)

            # per-walk display sequences, causal by construction
            walks = []
            for r in rows:
                lo = r["lo"]
                pid = int(r["pass_id"])
                # RULE 6: THE DOT AND THE MARKER LEAVE TOGETHER.
                # The first position the dot HAS is the label time of its first drawable window,
                # which is WINDOW_S - HEAD_OFFSET_S after that window starts. Until 2026-09-21 the
                # marker appeared at the walker's true first press instead, which is on average
                # 0.475 s earlier and up to 0.743 s earlier, so the marker left and the dot sat
                # still. That is the lag the operator saw, and it lived entirely in the first
                # second of each walk, which is why an aggregate check could not find it.
                # The scene now starts when the dot has something to say, and the marker is not
                # shown before then. Nothing is projected backwards to fill the gap.
                walks.append({"pass_id": pid, "true": r["true_line"],
                              "key": f"{TAG}|{rec.session}|{stem}|{pid}",
                              "scene_start": (float(t[max(0, lo - DISPLAY_LEAD_IN_W)])
                                              + WINDOW_S - HEAD_OFFSET_S),
                              "lo": lo, "end_i": r["own_end_i"],
                              "t_start": float(t[lo]) + WINDOW_S / 2.0,
                              "t_press_start": pstart.get(pid),
                              "t_own_end": float(t[r["own_end_i"]]) + WINDOW_S / 2.0,
                              "t_press": float(presses[pid]),
                              # THE END TEXT, batch 23e item 2: the SHIPPED semi-bounded
                              # committed decision (A2 + a_veto_1.0), the headline's own answer.
                              # Until 23e it named the bounded rescore at the end press, which
                              # uses the end press the semi-bounded mode is not told; that line
                              # is kept beside it, as the disclosed price of the ONE lattice.
                              "committed": r["final_line"],
                              "committed_source": ("the shipped semi-bounded committed decision "
                                                   "(A2 + a_veto_1.0), the headline's answer"),
                              "semibounded_own_end_line": r["final_line"],
                              "bounded_end_press_line": b_line.get(pid, ""),
                              "bounded_found": b_line.get(pid, "") == r["true_line"],
                              "shown_last": r["provisional_line_h1"],
                              "found": r["final_line"] == r["true_line"],
                              "err": r["err_m"],
                              "switches": r["revisions_h1"],
                              "switches_hysteresis_2": r["revisions"],
                              "commit_s": r["commit_s_h1"],
                              "commit_s_hysteresis_2": r["commit_s"],
                              "locked": disp_by_pid[pid]["display_locked"][f"{lag_w}|{DELAY}"],
                              "path": disp_by_pid[pid]["display_paths"][str(lag_w)],
                              "entry_state": disp_by_pid[pid]["entry_state"],
                              "entry_line": disp_by_pid[pid]["entry_line"],
                              "old_display_names": disp_by_pid[pid]["display_names"],
                              "old_display_state": disp_by_pid[pid]["display_state"]})

            frames = [float(x) for x in np.arange(t[0], t[-1] + WINDOW_S, 1.0 / FPS)]
            # RULE V4: NO STATIC DWELL FOOTAGE IN A DEMONSTRATION VIDEO. The whole grid block is
            # cut, not excerpted. The recordings run walk_half, grid, walk_half, so the 25-cell
            # standing block sits in the middle of every recording by protocol.
            #
            # THE BUG THIS REPLACES, kept in words because the shape recurs: the old cut kept an
            # excerpt whose length came from DWELL_EXCERPT_S, and that constant was added to a
            # window INDEX rather than to a time. At a 0.5 s stride 30 "seconds" was 30 windows,
            # so the excerpt was 15 s and the name said 30. A constant whose name ends in _S is a
            # duration and may never be used as a window count;
            # tests/test_render_rules.py::test_no_seconds_constant_used_as_a_window_count now
            # refuses it for the whole render.
            grid = np.flatnonzero(mode == "grid")
            n_before = len(frames)
            if len(grid):
                lo_c = float(t[int(grid[0])])
                hi_c = float(t[int(grid[-1])]) + WINDOW_S
                frames = [x for x in frames if not (lo_c <= x <= hi_c)]
            RES["dwell_cut"]["recordings"] += 1
            RES["dwell_cut"]["frames_removed"] += n_before - len(frames)
            RES["dwell_cut"]["grid_windows_seen"] += int(len(grid))
            RES["dwell_cut"]["frames_remaining_inside_a_grid_block"] += int(sum(
                1 for x in frames
                if len(grid) and float(t[int(grid[0])]) <= x <= float(t[int(grid[-1])]) + WINDOW_S))

            # THE DRAWN DOT, precomputed on the renderer's OWN frame times by the same function
            # the sweep measured with. The frame callback looks the answer up rather than
            # recomputing it, so what is measured and what is drawn cannot drift apart.
            def green_at(tq, park_until=None):
                """The scene's truth, and NOT SHOWN before the dot has an answer.

                Rule 6. Showing the marker earlier than the dot can draw makes the display look
                like it is lagging when it is in fact waiting, and the two are different faults
                with different fixes.
                """
                if park_until is not None and float(tq) < park_until:
                    return None
                g_, _gl, _p = truth_at(sc, float(tq) - LATENCY)
                return (float(g_[0]), float(g_[1])) if g_ else None

            def green_live(tq):
                """The truth at the video's own time, for the offset figure ONLY. Never drawn."""
                g_, _gl, _p = truth_at(sc, float(tq))
                return (float(g_[0]), float(g_[1])) if g_ else None

            def green_at_decoded(tq):
                """Where the person was at the moment the DECODER is naming, not at the frame.

                A window spans [t0, t0 + 2.0] and its label sits at the centre, so a dot drawn at
                frame time tq from a window that has just ended is naming tq - 1.0 s. Comparing the
                dot against the truth AT THAT MOMENT measures the decoder; comparing it against the
                truth at tq measures the decoder plus the lag. ACCEPTANCE.md reports both, and
                their difference is the display offset. Nothing is projected to close it.
                """
                g_, _gl, _p = truth_at(sc, float(tq) - LAG)
                return (float(g_[0]), float(g_[1])) if g_ else None

            if SWEEP:
                # THE PHASE SWEEP, reports/tracking/history/2026-09-24_prereg-display-phase.md. The dot drawn here is
                # the dot the loop below draws, with only HEAD_OFFSET_S varied: t_dec0 moves, the
                # anchor segment runs from the commit to it, and simulate_walk draws the rest.
                for wk in walks:
                    L = wk["locked"]
                    if not L["lock_correct"]:
                        continue
                    _alt = (L.get("paths_alt") or {}).get("end")
                    lpath = (_alt if (SHIPPED_DISPLAY == "DISP_END" and _alt) else L["path"])
                    if not lpath:
                        continue
                    park = float(wk["t_press_start"]) + LATENCY
                    t_end = wk["t_press"] + LATENCY
                    fr = [x for x in frames if float(wk["t_press_start"]) <= x < t_end]
                    _a, _b = st.slice_of[L["lock_line"]]
                    entry = xy_of(st, _a)
                    true_ = wk["true"]
                    L_m = along(room_paths, true_, room_paths[true_][-1])
                    for ho in HEAD_OFFSET_GRID:
                        t_d0 = float(t[max(0, wk["lo"] - DISPLAY_LEAD_IN_W)]) + WINDOW_S - ho + LATENCY
                        post = [x for x in fr if x >= t_d0]
                        anch = [x for x in fr if park <= x < t_d0]
                        if not post:
                            continue
                        sim = simulate_walk(lpath, st, t_d0, t_end, entry, L["lock_line"], STRIDE, 0,
                                            FPS, None, lambda q, _p=park: green_at(q, _p),
                                            frames=post, lead=False, shift_w=SHIFT_W)
                        acc = SWEEP_ACC.setdefault(ho, {"post": [], "all": [], "quarters": {},
                                                        "drawn_bound_s": -9.0, "evidence_bound_s": -9.0,
                                                        "walks": 0})
                        acc["walks"] += 1
                        seam = sim["red"][0] if sim["red"] else entry
                        span = t_d0 - park
                        for x in anch:
                            f_ = 0.0 if span <= 0 else float(np.clip((x - park) / span, 0.0, 1.0))
                            pq = (entry[0] + (seam[0] - entry[0]) * f_, entry[1] + (seam[1] - entry[1]) * f_)
                            g_ = green_at(x, park)
                            if g_ is not None:
                                acc["all"].append((along(room_paths, true_, pq) - along(room_paths, true_, g_),
                                                   float(np.hypot(pq[0] - g_[0], pq[1] - g_[1]))))
                        for x, r_, g_ in zip(post, sim["red"], sim["green"]):
                            if r_ is None or g_ is None:
                                continue
                            ag = along(room_paths, true_, g_)
                            pr = (along(room_paths, true_, r_) - ag,
                                  float(np.hypot(r_[0] - g_[0], r_[1] - g_[1])))
                            acc["post"].append(pr)
                            acc["all"].append(pr)
                            q_ = int(np.clip(np.floor(4.0 * ag / L_m), 0, 3))
                            acc["quarters"].setdefault(q_, []).append(pr)
                            # both causal bounds, on the step the dot actually glides towards
                            raw = (x - t_d0) / STRIDE + SHIFT_W
                            if raw >= 0:
                                i_ = int(min(np.floor(raw), len(lpath) - 1))
                                w_ = lpath[i_]["window"]
                                ew_ = lpath[i_].get("evidence_window", w_)
                                if w_ < len(t):
                                    acc["drawn_bound_s"] = max(acc["drawn_bound_s"], float(t[w_] + WINDOW_S - x))
                                if ew_ < len(t):
                                    acc["evidence_bound_s"] = max(acc["evidence_bound_s"],
                                                                  float(t[ew_] + WINDOW_S - x))
                status(f"  {who}: phase sweep over {sum(1 for w in walks if w['locked']['lock_correct'])} "
                       f"lock-correct walks")
                continue

            for wk in walks:
                L = wk["locked"]
                # RULE 6 AS AMENDED, 2026-09-23, OPERATOR DECISION. The scene starts at the
                # DELAYED PRESS MOMENT, not at the first window's label time. park_until is now
                # press + LATENCY, so red and green appear on the SAME frame at the press itself
                # and the 0.45 s gap is gone. t_dec0 is where the first DECODED position is
                # drawn; between the two the dot runs the anchor segment of rule 2's exception.
                wk["t_dec0"] = wk["scene_start"] + LATENCY
                wk["park_until"] = float(wk["t_press_start"]) + LATENCY
                # THE WALK OCCUPIES [t_start, t_press] IN SCENE TIME, so on the video it runs
                # from t_start to t_press + LATENCY. The first LATENCY seconds show the dot
                # parked at the room centre with no green marker yet: the walk has begun in the
                # world but the display has not caught up to it.
                fr = [x for x in frames
                      if float(wk["t_press_start"]) <= x < wk["t_press"] + LATENCY]
                pre = [x for x in fr if x < wk["park_until"]]
                anch = [x for x in fr if wk["park_until"] <= x < wk["t_dec0"]]
                post = [x for x in fr if x >= wk["t_dec0"]]
                # THE DRAWN PATH IS THE SHIPPED DISPLAY ARM'S, from its FIRST step: the lock has
                # already happened by the time the scene starts, so there is no step to skip.
                _alt = (L.get("paths_alt") or {}).get("end")
                lpath = (_alt if (SHIPPED_DISPLAY == "DISP_END" and _alt) else L["path"])
                drawn, rseq, gseq = {}, [], []
                wk["rule_violations"] = []
                # THE PARK. No provisional line, no leading candidate, no wandering. The dot sits
                # at the room centre, which is the null state's own decoded position, and says
                # nothing until it has an answer. Rule 1 of reports/tracking/render-rules.md.
                for x in pre:
                    drawn[round(float(x), 4)] = CENTRE
                    rseq.append(CENTRE)
                    gseq.append(green_at(x, wk["park_until"]))
                # ---- RULE 2's ONE NARROW EXCEPTION, operator decision 2026-09-23.
                # At the press the dot is placed at the ENTRY POINT OF THE COMMITTED LINE, which
                # is not a decoded position. It is permitted because the press is DEFINED as the
                # walker crossing that line's start tape, and the line is already committed on
                # the 2 s of post-press radio. From that anchor the dot moves along the straight
                # segment to the first decoded position, and rule 2 applies unchanged from there.
                # NO PACE AND NO PROJECTION: the interpolation parameter is the fraction of the
                # anchor interval elapsed, between two fixed endpoints. It is not a speed, and it
                # cannot run past the first decoded position.
                # A WRONG COMMITTED LINE STARTS AT THE WRONG LINE'S ENTRY. That is shown.
                _a, _b = st.slice_of[L["lock_line"]]
                line_entry = xy_of(st, _a)
                wk["line_entry_xy"] = (float(line_entry[0]), float(line_entry[1]))
                if post and lpath:
                    # THE DRAWN INDEX MATCHES THE SCENE. Step i is read from the window whose own
                    # label time is the moment being shown, so the dot answers for the same
                    # instant the green marker shows and the two are directly comparable. R1
                    # measured the head naming HEAD_OFFSET_S behind the window it is read from.
                    # index 0 is drawn at exactly park_until, which is the same instant the
                    # marker appears, so the two leave together by construction rather than by
                    # arithmetic that happens to agree.
                    t_eff = wk["t_dec0"]
                    # THE DECODED SEGMENT. entry_xy is the LINE'S ENTRY rather than the first
                    # decoded state, so the anchor segment and this segment are two parts of one
                    # straight line and the seam between them cannot jump.
                    sim = simulate_walk(lpath, st, t_eff, wk["t_press"] + LATENCY,
                                        line_entry, L["lock_line"], STRIDE, 0,
                                        FPS, None, lambda q: green_at(q, wk["park_until"]),
                                        frames=post, lead=False, shift_w=SHIFT_W)
                    # THE SEAM, read from the decoded loop rather than recomputed, so the anchor
                    # cannot drift from what the decoded segment actually draws.
                    seam = sim["red"][0] if sim["red"] else line_entry
                    span = float(wk["t_dec0"]) - float(wk["park_until"])
                    for x in anch:
                        f_ = 0.0 if span <= 0 else float(np.clip((x - wk["park_until"]) / span,
                                                                 0.0, 1.0))
                        pq = (line_entry[0] + (seam[0] - line_entry[0]) * f_,
                              line_entry[1] + (seam[1] - line_entry[1]) * f_)
                        drawn[round(float(x), 4)] = pq
                        rseq.append(pq)
                        gseq.append(green_at(x, wk["park_until"]))
                        RES["anchor_segment"]["frames"] += 1
                        # the anchor frame must lie ON the segment [line entry, seam]; that is
                        # the exception's own contract and it is checked, not asserted
                        _d1 = float(np.hypot(pq[0] - line_entry[0], pq[1] - line_entry[1]))
                        _d2 = float(np.hypot(seam[0] - pq[0], seam[1] - pq[1]))
                        _dt = float(np.hypot(seam[0] - line_entry[0], seam[1] - line_entry[1]))
                        RES["anchor_segment"]["off_segment_frames"] += int(
                            abs(_d1 + _d2 - _dt) > 1e-6)
                    drawn.update({round(f, 4): p for f, p in zip(sim["frames"], sim["red"])})
                    rseq += sim["red"]
                    gseq += sim["green"]
                    wk["rule_violations"] += sim["violations"]
                    RES["rule"]["frames_checked"] += sim["n_frames"]
                    RES["rule"]["violations"] += len(sim["violations"])
                    # THE START GAP IS ZERO BY CONSTRUCTION on a correct committed line, because
                    # the press is the walker AT the tape entry and the dot is placed there. It
                    # is a DISPLAY RULE and is reported as one, never as a tracking result:
                    # rule 4. Tracking is measured from the first decoded position onward.
                    _g0 = green_at(wk["park_until"], wk["park_until"])
                    wk["start_gap_m"] = (None if _g0 is None else
                                         float(np.hypot(line_entry[0] - _g0[0],
                                                        line_entry[1] - _g0[1])))
                    # and what a VIEWER sees on the first drawn frame, which carries up to one
                    # frame of grid quantisation on top of the by-construction zero. Both are
                    # reported: the first is the rule, the second is the picture.
                    _f0 = anch[0] if anch else (post[0] if post else None)
                    _gf = None if _f0 is None else green_at(_f0, wk["park_until"])
                    _rf = None if _f0 is None else drawn.get(round(float(_f0), 4))
                    wk["start_gap_first_frame_m"] = (
                        None if (_gf is None or _rf is None) else
                        float(np.hypot(_rf[0] - _gf[0], _rf[1] - _gf[1])))
                    wk["rpost"], wk["gpost"] = list(sim["red"]), list(sim["green"])
                    # ---- MID-WALK SWITCHING, RENDER_RULES rule 1a (batch 23f: up to K switches).
                    # The decision (`switching.decide_walk`), the slide and the new lines' paths are
                    # the functions e2_switch measured with, on the dot drawn above.
                    wk["mid_switches"], wk["mid_switch_paths"] = [], []
                    if SWITCH:
                        assert SHIPPED_DISPLAY == "DISP_END", "switch paths exist for DISP_END only"
                        _lo = int(wk["lo"])
                        _decs = SCORER.decisions(E_sw, t, _lo, SCORER.start(E_sw, _lo),
                                                 SW.decision_frames(wk["t_press_start"],
                                                                    wk["t_press"]))
                        _dots = [(float(x), drawn[round(float(x), 4)]) for x in anch + post]

                        def _newsim(line, frames_, green=False, _wk=wk, _L=L):
                            _na, _nb = st.slice_of[line]
                            return simulate_walk(
                                _L["switch_paths"]["end"][line], st, t_eff, _wk["t_press"] + LATENCY,
                                xy_of(st, _na), line, STRIDE, 0, FPS, None,
                                (lambda q: green_at(q, _wk["park_until"])) if green else (lambda q: None),
                                frames=frames_, lead=False, shift_w=SHIFT_W)

                        def _dots_for(line, x_from, _post=post):
                            s_ = _newsim(line, [x for x in _post if x >= x_from - 1e-9])
                            return list(zip(s_["frames"], s_["red"]))

                        _res = SW.decide_walk(L["lock_line"], _decs,
                                              SW_ADJ.get(f"{rec.session}|{stem}|{wk['pass_id']}"),
                                              float(SWITCH["theta"]), st, _dots, _dots_for,
                                              radius=SWITCH["radius_m"],
                                              max_switches=int(SWITCH["max_switches"]),
                                              final_m=float(SWITCH["final_m"]))
                        RES["switching"]["walks"] += 1
                        _cur_sim, _seen_lines = sim, {L["lock_line"]}
                        _order = sorted(float(x) for x in anch + post)
                        for _sw in _res["switches"]:
                            xs, new, old = float(_sw["x"]), _sw["new"], _sw["old"]
                            _bef = [x_ for x_ in _order if x_ < xs - 1e-9]
                            p_old = drawn[round(_bef[-1], 4)] if _bef else line_entry
                            npath = L["switch_paths"]["end"][new]
                            q_new = _newsim(new, [xs + SW.SLIDE_S])["red"][0]
                            _slide = SW.slide(p_old, q_new, xs, post)
                            _after = [x for x in post if x >= xs + SW.SLIDE_S - 1e-9]
                            _nsim = _newsim(new, _after, green=True)
                            for x_, p_, _off in _slide:
                                drawn[round(float(x_), 4)] = p_
                            drawn.update({round(f, 4): p_ for f, p_ in
                                          zip(_nsim["frames"], _nsim["red"])})
                            # the previous line's frames from the switch on are no longer drawn, so
                            # their rule checks are replaced by the new line's and the slide's
                            _gone = [v for v in _cur_sim["violations"] if v["t"] >= xs - 1e-9]
                            wk["rule_violations"] = [v for v in wk["rule_violations"]
                                                     if v not in _gone] + _nsim["violations"]
                            RES["rule"]["violations"] += len(_nsim["violations"]) - len(_gone)
                            RES["rule"]["frames_checked"] += _nsim["n_frames"] - sum(
                                1 for x_ in _cur_sim["frames"] if x_ >= xs - 1e-9)
                            _cur_sim = _nsim
                            # the drawn target's two causal bounds, from the frame the slide starts,
                            # with the step simulate_walk actually reads (shift_w)
                            _it = int(np.clip(int(np.floor((xs + SW.SLIDE_S - t_eff) / STRIDE
                                                           + SHIFT_W)), 0, len(npath) - 1))
                            _w, _ew = npath[_it]["window"], npath[_it].get("evidence_window",
                                                                         npath[_it]["window"])
                            _seq = [p_old] + [p_ for _x, p_, _o in _slide] + (
                                [_nsim["red"][0]] if _nsim["red"] else [])
                            rec_sw = {
                                "k": _sw["k"], "x": xs, "after_lock_s": round(xs - wk["park_until"], 6),
                                "old": old, "new": new, "lead": _sw["lead"],
                                "persist": _sw["persist"], "theta": float(SWITCH["theta"]),
                                "dot_max_arc_m": _sw["dot_max_arc_m"],
                                "line_length_m": _sw["line_length_m"], "final_m": _sw["final_m"],
                                "decision_evidence_bound_s": _sw["evidence_bound_s"],
                                "target_drawn_bound_s": float(t[_w] + WINDOW_S - xs),
                                "target_evidence_bound_s": float(t[_ew] + WINDOW_S - xs),
                                "p_old": list(p_old), "q_new": list(q_new),
                                "jump_m": float(np.hypot(q_new[0] - p_old[0], q_new[1] - p_old[1])),
                                "slide_frames": len(_slide),
                                "slide_off_segment": int(sum(o_ for _x, _p, o_ in _slide)),
                                "slide_frame_jumps_over_0_5m": int(sum(
                                    1 for a_, b_ in zip(_seq, _seq[1:])
                                    if float(np.hypot(b_[0] - a_[0], b_[1] - a_[1])) > 0.5)),
                                "returns_to_a_drawn_line": bool(new in _seen_lines),
                                "w2r": bool(old != wk["true"] and new == wk["true"]),
                                "r2w": bool(old == wk["true"] and new != wk["true"]),
                                "w2w": bool(old != wk["true"] and new != wk["true"])}
                            _seen_lines.add(new)
                            wk["mid_switches"].append(rec_sw)
                            wk["mid_switch_paths"].append((xs, npath))
                            S_ = RES["switching"]
                            S_["switches"] += 1
                            for k_ in ("w2r", "r2w", "w2w"):
                                S_[k_] += int(rec_sw[k_])
                            S_["jump_m"].append(rec_sw["jump_m"])
                            S_["slide_off_segment_frames"] += rec_sw["slide_off_segment"]
                            S_["slide_frame_jumps_over_0_5m"] += rec_sw["slide_frame_jumps_over_0_5m"]
                            for k_, v_ in (("decision_evidence_worst_s", "decision_evidence_bound_s"),
                                           ("target_drawn_worst_s", "target_drawn_bound_s"),
                                           ("target_evidence_worst_s", "target_evidence_bound_s")):
                                S_[k_] = max(S_[k_], rec_sw[v_])
                            S_["switch_in_final_zone"] += int(
                                rec_sw["dot_max_arc_m"] >= rec_sw["line_length_m"] - rec_sw["final_m"])
                            S_["persistence_violations"] += int(not (
                                len(rec_sw["persist"]) == SW.PERSIST_STEPS
                                and all(q_["qualifies"] and q_["best"] == new
                                        and q_["lead"] > rec_sw["theta"] for q_ in rec_sw["persist"])))
                            S_["returns_to_a_drawn_line"] += int(rec_sw["returns_to_a_drawn_line"])
                            S_["earliest_after_lock_s"] = (
                                rec_sw["after_lock_s"] if S_["earliest_after_lock_s"] is None
                                else min(S_["earliest_after_lock_s"], rec_sw["after_lock_s"]))
                        RES["switching"]["more_than_max_switches"] += int(
                            len(wk["mid_switches"]) > int(SWITCH["max_switches"]))
                        wk["rpost"] = [drawn[round(float(x_), 4)] for x_ in post]
                if wk["rule_violations"]:
                    RES["rule"]["examples"] += wk["rule_violations"][:3]
                # JUMPS: every frame-to-frame move over 0.5 m, and whether the lock caused it
                # every frame of the walk has a dot: parked at the centre during the latency,
                # tracking after it. There is no frame on which the dot is absent.
                expect = list(fr)
                wk["frames_expected"] = len(expect)
                wk["frames_missing_after_first_legal"] = int(sum(
                    1 for x in expect if drawn.get(round(float(x), 4)) is None))
                RES["dot_visible"]["expected"] += wk["frames_expected"]
                RES["dot_visible"]["missing_after_first_legal"] += \
                    wk["frames_missing_after_first_legal"]
                # THE CAUSAL BOUND, confirmed on every drawn frame against real timestamps: the
                # window being read must have ENDED by the frame time.
                # THE CAUSAL BOUNDS under the delayed timeline: at video time x the decoder
                # may read any window that had finished recording by x, and the scene it is
                # drawing is x - LATENCY, so it has LATENCY seconds of margin it does not spend.
                _swl = wk.get("mid_switches") or []
                for x in post:
                    # after a switch the frames are drawn from the NEW line's path, and checked on it
                    _pth = lpath
                    for _xs, _np in (wk.get("mid_switch_paths") or []):
                        if x >= _xs - 1e-9:
                            _pth = _np
                    # f4: the step the dot actually glides towards, SHIFT_W included. f3 took the
                    # floor without it, which checks a step up to one stride EARLIER than the one read.
                    _raw = (x - t_eff) / STRIDE + SHIFT_W
                    i_ = int(min(np.floor(_raw), len(_pth) - 1)) if _raw >= 0 else -1
                    if 0 <= i_ < len(_pth):
                        w_ = _pth[i_]["window"]
                        if w_ < len(t):
                            RES["causal_bound_s"] = max(
                                RES["causal_bound_s"], float(t[w_] + WINDOW_S - x))
                        ew_ = _pth[i_].get("evidence_window", w_)
                        if ew_ < len(t):
                            RES["causal_evidence_bound_s"] = max(
                                RES["causal_evidence_bound_s"], float(t[ew_] + WINDOW_S - x))
                jumps, lock_jumps, switch_jumps = 0, 0, 0
                order = sorted(drawn)
                for a_, b_ in zip(order, order[1:]):
                    pa, pb = drawn[a_], drawn[b_]
                    if pa is None or pb is None:
                        continue
                    if float(np.hypot(pb[0] - pa[0], pb[1] - pa[1])) > 0.5:
                        jumps += 1
                        if (a_ - wk["t_press_start"]) < DELAY <= (b_ - wk["t_press_start"]):
                            lock_jumps += 1
                        elif any(_s["x"] - 1e-9 <= b_ <= _s["x"] + SW.SLIDE_S + 1.0 / FPS + 1e-9
                                 for _s in _swl):
                            switch_jumps += 1             # a slide, counted apart from the lock
                wk["jumps_over_0.5m"] = int(jumps)
                wk["jumps_caused_by_the_lock"] = int(lock_jumps)
                wk["jumps_caused_by_a_switch"] = int(switch_jumps)
                RES["jumps"]["total"] += jumps
                RES["jumps"]["caused_by_the_lock"] += lock_jumps
                RES["jumps"]["caused_by_a_switch"] += switch_jumps
                # RULE 6, measured rather than asserted: the marker's first frame and the dot's
                # first drawn frame must be the same frame.
                _first_g = next((x for x in sorted(drawn)
                                 if green_at(x, wk["park_until"]) is not None), None)
                _first_r = next((x for x in sorted(drawn) if x >= wk["park_until"]), None)
                # V2 and V3, MEASURED PER WALK. _first_r is the first frame at or after the
                # commit, so it IS the commit frame; _first_g is the marker's first frame. V2 says
                # those are one event. V3 says the offset from the walk start is the same number
                # on every walk, which is what makes an adaptive lock detectable.
                wk["first_marker_frame"] = None if _first_g is None else float(_first_g)
                wk["first_committed_frame"] = None if _first_r is None else float(_first_r)
                # V3 AS AMENDED, 2026-09-23. The origin is now the START PRESS rather than
                # the first window centre, so the offset is exactly LATENCY on every walk
                # by construction. The 0.202 s of window-lattice scatter that used to sit
                # in the origin is gone with it: the press is a physical event, not a
                # lattice position.
                wk["lock_offset_s"] = round(float(wk["park_until"])
                                            - float(wk["t_press_start"]), 6)
                if _first_g is not None and _first_r is not None:
                    _v2 = abs(float(_first_g) - float(_first_r))
                    _V2 = RES["vision_rules"]["V2_commit_frame_equals_marker_frame"]
                    _V2["walks"] += 1
                    _V2["max_gap_s"] = max(_V2["max_gap_s"], _v2)
                    _V2["violations"] += int(_v2 > 1.0 / FPS + 1e-6)
                    _gap = abs(float(_first_g) - float(_first_r))
                    RES["leave_together"]["walks"] += 1
                    RES["leave_together"]["max_gap_s"] = max(
                        RES["leave_together"]["max_gap_s"], _gap)
                    RES["leave_together"]["violations"] += int(_gap > 1.0 / FPS + 1e-6)
                    # THE STALL. Appearing together is not enough: the dot must also START
                    # MOVING, or it stands at the line entry while the marker walks off and the
                    # display reads as lagging for the second time in the same second.
                    _ord = [q for q in sorted(drawn) if q >= wk["park_until"]]
                    _stall, _p0 = None, drawn.get(_ord[0]) if _ord else None
                    for q in _ord[1:]:
                        _pq = drawn.get(q)
                        if _p0 is None or _pq is None:
                            continue
                        if float(np.hypot(_pq[0] - _p0[0], _pq[1] - _p0[1])) > 1e-9:
                            _stall = float(q) - float(_ord[0])
                            break
                    # WHEN THE DECODER ITSELF SAYS THE WALKER HAS NOT MOVED, a held dot is the
                    # honest picture and not the display fault rule 6 was written against. That
                    # fault was BACKWARD INTERPOLATION: the dot held while the decodes differed.
                    # So the violation is a hold the decoder does NOT account for, measured here
                    # as the time until the decoded target first leaves the line entry.
                    _dm = None
                    _le = wk.get("line_entry_xy")
                    for q in _ord:
                        if q < wk["t_dec0"]:
                            _tg = seam if post else _le
                        else:
                            _i = int(np.clip(int(np.floor((q - wk["t_dec0"]) / STRIDE + SHIFT_W)),
                                             0, len(lpath) - 1))
                            _st_i = lpath[_i]["state"]
                            _tg = xy_of(st, _st_i) if _st_i is not None and _st_i >= 0 else None
                        if _tg is not None and _le is not None and float(
                                np.hypot(_tg[0] - _le[0], _tg[1] - _le[1])) > 1e-9:
                            _dm = float(q) - float(_ord[0])
                            break
                    wk["decoder_first_moves_s"] = _dm
                    wk["stall_s"] = _stall
                    if _stall is not None:
                        RES["leave_together"]["max_stall_s"] = max(
                            RES["leave_together"]["max_stall_s"], _stall)
                        _explained = (_dm is not None and _stall <= _dm + 1.0 / FPS + 1e-6)
                        RES["leave_together"]["stall_explained_by_the_decoder"] += int(_explained)
                        RES["leave_together"]["stall_violations"] += int(
                            _stall > 1.0 / FPS + 1e-6 and not _explained)
                wk["entry_xy"] = (xy_of(st, lpath[0]["state"]) if lpath
                                  and lpath[0]["state"] >= 0 else None)
                wk["locked_line"] = L["lock_line"]
                wk["lock_correct"] = bool(L["lock_correct"])
                wk["drawn"] = drawn
                # TWO SEPARATE NUMBERS, never added together and never traded off.
                #   tracking          the dot against where the person IS at that frame. The
                #                     display lag counts against it, in full.
                #   decoded_accuracy  the dot against where the person WAS at the moment the
                #                     window it came from is naming. This is the decoder's own
                #                     accuracy with the lag taken out, and it is not what a viewer
                #                     sees.
                #   display_offset    how far the person travels during the lag. It is the whole
                #                     of the difference between the two, and it is a property of
                #                     walking pace and the window length, not of the model.
                # RULE 4 AND THE 2026-09-23 AMENDMENT: the anchor segment is a DISPLAY RULE
                # whose start gap is zero by construction on a correct line, so including
                # it here would report a rule as though it were a measurement. Tracking is
                # measured from the first DECODED position onward.
                wk["tracking"] = on_screen_tracking(wk.get("rpost") or [],
                                                    wk.get("gpost") or [])
                wk["tracking_includes_the_anchor_segment"] = False
                gseq_dec = [green_at_decoded(f) for f in sorted(drawn)]
                rseq_dec = [drawn[f] for f in sorted(drawn)]
                wk["decoded_accuracy"] = on_screen_tracking(rseq_dec, gseq_dec)
                _off = [float(np.hypot(a[0] - b[0], a[1] - b[1]))
                        for a, b in zip(gseq_dec, [green_at(f) for f in sorted(drawn)])
                        if a is not None and b is not None]
                _live = [float(np.hypot(a[0] - b[0], a[1] - b[1]))
                         for a, b in zip([green_at(f) for f in sorted(drawn)],
                                         [green_live(f) for f in sorted(drawn)])
                         if a is not None and b is not None]
                wk["offset_from_live_truth"] = {
                    "n_frames": len(_live),
                    "mean_m": float(np.mean(_live)) if _live else None,
                    "median_m": float(np.median(_live)) if _live else None,
                    "definition": (f"how far the walker travels during the {LATENCY:g} s "
                                   f"the whole display runs behind. It is the price of the "
                                   f"delay, not an error in the tracker, and it is reported "
                                   f"apart from the accuracy figure rather than folded into it")}
                wk["display_offset"] = {
                    "n_frames": len(_off),
                    "mean_m": float(np.mean(_off)) if _off else None,
                    "median_m": float(np.median(_off)) if _off else None,
                    "definition": ("the distance the person travels during the display lag of "
                                   f"{LAG:g} s, which is the gap between what the decoder names "
                                   "and where the person is when it is drawn")}
                wk["monotonicity_violations"] = int(monotonicity_violations(lpath, st))
                wk["distinct_lines_after_lock"] = len({q["line"] for q in lpath}) + len(_swl)
                wk["switches"] = 1 if lpath else 0          # the lock itself
                wk["mid_walk_switches"] = len(_swl)
                wk["drawn_end_line"] = _swl[-1]["new"] if _swl else wk["locked_line"]
                RES["switching"]["end_on_committed"] += int(wk["drawn_end_line"] == wk["committed"])

            # ---- THE LAYOUT, f4 (operator, 2026-09-24): the room as large as the frame allows, the
            # legend and the clock in a band ABOVE it so neither covers RX1 or the tape, and the
            # walk's result in a band below. RX1 is drawn at its measured position: the frame is
            # tightened around it, the node is never moved.
            fig = plt.figure(figsize=(9.0, 11.0))
            ax = fig.add_axes([0.09, 0.19, 0.88, 0.70])
            room(ax, room_paths)
            ax.set_xlim(-0.8, 5.8)
            ax.set_ylim(-0.8, 5.9)
            ax.tick_params(labelsize=10)
            ax.xaxis.label.set_fontsize(11)
            ax.yaxis.label.set_fontsize(11)
            for _tx in ax.texts:                      # the RX and TX names
                _tx.set_fontsize(10)
            hl, = ax.plot([], [], "-", color="tab:orange", lw=5, alpha=0.30, zorder=2)
            lock_hl, = ax.plot([], [], "-", color="tab:red", lw=5, alpha=0.45, zorder=3)
            trail, = ax.plot([], [], "-", color="tab:red", lw=1.8, alpha=0.5, zorder=4)
            gdot, = ax.plot([], [], "o", color="tab:green", ms=15, zorder=5,
                            label=f"where the person was {LATENCY:g} s ago")
            rdot, = ax.plot([], [], "o", color="tab:red", ms=12, zorder=6,
                            label="the tracker's answer for that same moment")
            # THE SWITCH MARK (rule 1 as amended, batch 23e): where the dot left the locked line,
            # shown from the switch to the end of the walk, with the switch named in the text line.
            swmark, = ax.plot([], [], "X", color="tab:purple", ms=14, zorder=7,
                              label="where the display switched line")
            fig.legend(handles=[gdot, rdot, swmark], loc="upper left", bbox_to_anchor=(0.075, 0.958),
                       fontsize=10, framealpha=0.9)
            # THE CLOCK, rule 3: the delay is stated on screen on every frame. In the header band,
            # beside the legend, where it covers nothing.
            clock = fig.text(0.60, 0.952, "", fontsize=15, ha="left", va="top", color="0.15",
                             weight="bold", family="monospace")
            ttl = fig.text(0.5, 0.982, "", fontsize=13, ha="center", va="top", color="0.1")
            info = fig.text(0.5, 0.128, "", fontsize=12, ha="center", family="monospace",
                            color="0.25")
            # THE RESULT, f4: CORRECT in green or WRONG in red, the running accuracy for this
            # participant and the total over all six. Shown from the walk's end until the next
            # walk commits, so it stays up through the gap and the next listening period.
            res1 = fig.text(0.5, 0.086, "", fontsize=18, ha="center", weight="bold")
            res2 = fig.text(0.5, 0.051, "", fontsize=12, ha="center", color="0.15")
            res3 = fig.text(0.5, 0.029, "", fontsize=9.5, ha="center", color="0.45")
            res4 = fig.text(0.5, 0.009, "", fontsize=9.5, ha="center", color="0.45")
            GREEN_TXT, RED_TXT = "#1a7f37", "#c62828"
            walks_by_t = sorted(walks, key=lambda w_: float(w_["t_press_start"]))
            tx, ty = [], []
            state = {"walk": None, "shown": "", "cue_until": -9.0, "cue_txt": "",
                     "switches": 0, "last": CENTRE, "frames": 0, "nodot": 0}

            def chain_xy(nm):
                a, b = st.slice_of[nm]
                p = np.asarray(st.xy)[a:b]
                return p[:, 0], p[:, 1]

            def result_panel(tq):
                """The latest finished walk's result, until the walk after it commits."""
                done = [w_ for w_ in walks_by_t if w_["t_press"] + LATENCY <= tq]
                if not done:
                    res1.set_text(""); res2.set_text(""); res3.set_text(""); res4.set_text("")
                    return
                last = done[-1]
                nxt = next((w_ for w_ in walks_by_t
                            if float(w_["t_press_start"]) > float(last["t_press_start"])), None)
                right = sum(1 for w_ in done if w_["found"])
                if nxt is not None and tq >= nxt["park_until"]:
                    res1.set_text("")
                    res3.set_text("")
                    res4.set_text("")
                else:
                    ok_ = bool(last["found"])
                    res1.set_text((f"walk {last['pass_id']}: CORRECT   walked {last['true']}, "
                                   f"answered {last['committed']}"
                                   if ok_ else
                                   f"walk {last['pass_id']}: WRONG   walked {last['true']}, "
                                   f"answered {last['committed'] or 'none'}"))
                    res1.set_color(GREEN_TXT if ok_ else RED_TXT)
                    _dr = last.get("drawn_end_line")
                    res3.set_text(f"the dot was drawn on {_dr}; the answer is decided on the whole walk"
                                  if _dr and _dr != last["committed"] else "")
                    res4.set_text(f"{TAG} is the easiest of nine cross-day pairings; their median is "
                                  + (f"{TOTAL['nine_pairing_median']:.1f} %"
                                     if TOTAL.get("nine_pairing_median") else "not available"))
                res2.set_text(f"{who} so far: {right} of {len(done)} walks right "
                              f"({100.0 * right / len(done):.1f} %)      "
                              + (f"all six participants: {TOTAL['right']} of {TOTAL['n']} "
                                 f"({100.0 * TOTAL['right'] / TOTAL['n']:.1f} %)" if TOTAL.get("n")
                                 else ""))

            def frame(k):
                tq = frames[k]
                state["frames"] += 1
                result_panel(tq)
                # R2: the marker shows the DELAYED moment, which is the moment the dot is
                # answering for. A live marker beside a delayed dot reads as error when it is
                # latency, which is what the two-marker display was trying and failing to say.
                cur = None
                for wk in walks:
                    if float(wk["t_press_start"]) - 0.05 <= tq <= wk["t_press"] + LATENCY + 0.5:
                        cur = wk
                        break

                # THE MARKER, gated on the same instant the dot starts. Rule 6.
                g = green_at(tq, cur["park_until"]) if cur is not None else None
                w = int(np.clip(np.searchsorted(t, tq) - 1, 0, len(rec) - 1))
                if cur is None and mode[w] == "grid" and np.isfinite(rec.xy[w]).all():
                    g = (float(rec.xy[w][0]), float(rec.xy[w][1]))
                gdot.set_data([g[0]] if g else [], [g[1]] if g else [])

                if cur is None:
                    # BETWEEN WALKS the dot waits at the room centre, the null state's own
                    # decoded position.
                    state["last"] = CENTRE
                    rdot.set_data([CENTRE[0]], [CENTRE[1]])
                    hl.set_data([], []); lock_hl.set_data([], []); trail.set_data([], [])
                    swmark.set_data([], [])
                    tx.clear(); ty.clear(); state["walk"] = None
                    info.set_text("waiting for the next walk")
                    clock.set_text(f"\n{LATENCY:g} s behind real time")
                    ttl.set_text(f"{who}   |   {TAG}, cross-day, trained on sessions "
                                 f"{' and '.join(TRAIN)}")
                    if len(np.atleast_1d(rdot.get_xdata())) == 0:
                        state["nodot"] += 1
                    return

                if state["walk"] != cur["pass_id"]:
                    state.update({"walk": cur["pass_id"], "shown": "", "switches": 0,
                                  "cue_until": tq + 2.0, "cue_txt": "WALK DECLARED"})
                    tx.clear(); ty.clear()
                clock.set_text(f"t = {max(0.0, tq - cur['park_until']):4.1f} s\n"
                               f"{LATENCY:g} s behind real time")

                if tq < cur["t_press"] + LATENCY:
                    p = cur["drawn"].get(round(float(tq), 4))
                    if p is None:
                        p = state["last"]
                    state["last"] = p
                    if p is None:
                        # BEFORE THE FIRST LEGAL FRAME the dot WAITS AT THE ROOM CENTRE, which is
                        # the null state's own decoded position: the system is saying it does not
                        # yet know, in the one place that means exactly that.
                        if PARK_WHILE_LISTENING:
                            rdot.set_data([CENTRE[0]], [CENTRE[1]])
                            state["last"] = CENTRE
                        else:
                            rdot.set_data([], [])
                            state["nodot"] += 1
                        hl.set_data([], []); trail.set_data([], []); tx.clear(); ty.clear()
                        info.set_text(f"listening: {cur['park_until'] - tq:.1f} s until the "
                                      f"display reaches this walk's start")
                    elif tq < cur["park_until"]:
                        # THE PARK, gated on the COMMIT itself (V2 and rule 1).
                        rdot.set_data([CENTRE[0]], [CENTRE[1]])
                        tx.clear(); ty.clear(); trail.set_data([], [])
                        hl.set_data([], [])
                        lock_hl.set_data([], [])
                        info.set_text(f"listening: this walk commits in {cur['park_until'] - tq:.1f} s")
                    else:
                        rdot.set_data([p[0]], [p[1]])
                        _done = [q_ for q_ in (cur.get("mid_switches") or []) if tq >= q_["x"] - 1e-9]
                        _named = SW.named_line_at_multi(cur["locked_line"], _done, tq)
                        if state["shown"] != _named:
                            state["shown"] = _named
                            state["switches"] += 1         # the lock, then each switch
                        hl.set_data(*chain_xy(state["shown"]))
                        tx.append(p[0]); ty.append(p[1]); trail.set_data(tx, ty)
                        d = (float(np.hypot(p[0] - g[0], p[1] - g[1])) if g else None)
                        if _done:
                            _s = _done[-1]
                            swmark.set_data([q_["p_old"][0] for q_ in _done],
                                            [q_["p_old"][1] for q_ in _done])
                            info.set_text(f"switched {_s['old']} -> {_s['new']}"
                                          + (f"      off by {d:.2f} m" if d is not None else ""))
                        else:
                            swmark.set_data([], [])
                            info.set_text(f"tracking on {state['shown']}"
                                          + (f"      off by {d:.2f} m" if d is not None else ""))
                    lock_hl.set_data([], [])
                else:
                    # A5, THE END PRESS. THE DOT DOES NOT MOVE: it holds its final position on the
                    # line it was drawn on. The committed answer is the result panel's.
                    lock_hl.set_data(*(chain_xy(cur["drawn_end_line"]) if cur.get("drawn_end_line")
                                       else ([], [])))
                    hl.set_data([], [])
                    if state["last"] is not None:
                        rdot.set_data([state["last"][0]], [state["last"][1]])
                    info.set_text("walk finished")
                # THE DOT IS NEVER HIDDEN. Every branch above sets it, so this must stay zero.
                if len(np.atleast_1d(rdot.get_xdata())) == 0:
                    state["nodot"] += 1
                ttl.set_text(f"{who}   |   {TAG}   |   walk {cur['pass_id']}   |   "
                             f"true line {cur['true']}")

            ani = anim.FuncAnimation(fig, frame, frames=len(frames), interval=1000 // FPS)
            out = os.path.join(DEMO, f"{stem}_live.mp4")
            ani.save(out, writer=anim.FFMpegWriter(fps=FPS, bitrate=3000))
            plt.close(fig)
            # causality is now subsumed by THE ONE RULE, which is stricter: nothing may be drawn
            # ahead of the latest decode, checked per frame in simulate_walk against real
            # timestamps. The old counter is kept at zero so downstream readers do not break.
            RES["causality"]["frames_checked"] = RES["rule"]["frames_checked"]
            RES["causality"]["violations"] = RES["rule"]["violations"]
            RES["causality"]["superseded_by"] = "the one rule, see RES['rule']"
            RES["dot_visible"]["frames"] += state["frames"]
            RES["dot_visible"]["frames_without_dot"] += state["nodot"]
            for wk in walks:
                wk["flagged_many_switches"] = bool(wk["switches"] > 4)
                wk["old_backward_steps"] = int(_back(wk["old_display_names"],
                                                     wk["old_display_state"]))
                wk["n_rule_violations"] = len(wk["rule_violations"])
                for k_ in ("path", "drawn", "locked", "old_display_names",
                           "old_display_state", "rule_violations", "mid_switch_paths"):
                    wk.pop(k_, None)
            RES["recordings"][who] = {
                "video": os.path.basename(out), "bytes": os.path.getsize(out),
                "n_frames": len(frames), "walks": walks,
                "tracking": on_screen_tracking(
                    [p for w in walks for p in [None]] or [], []) if False else None,
                "bytes_per_frame": round(os.path.getsize(out) / max(1, len(frames)), 1)}
            acceptance.append((who, walks))
            tws = [w["tracking"]["within_pct"] for w in walks
                   if w["tracking"]["within_pct"] is not None]
            status(f"  {who:8s} {len(walks)} walks, {sum(w['found'] for w in walks)} committed "
                   f"correctly, tracking {np.mean(tws):5.1f}%, "
                   f"{sum(w['switches'] for w in walks)} switches, "
                   f"{sum(w['n_rule_violations'] for w in walks)} rule violations, "
                   f"{state['nodot']} frames without a dot, {os.path.getsize(out)/1e6:.2f} MB")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"who": who, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1500:]})
            status(f"  {who}: FAILED {exc!r}")

    if SWEEP:
        out = {"stage": STAGE, "tag": TAG, "prereg": "reports/tracking/history/2026-09-24_prereg-display-phase.md",
               "grid": list(HEAD_OFFSET_GRID), "target_ahead_pct": PHASE_TARGET_AHEAD_PCT,
               "shift_w": SHIFT_W, "latency_s": LATENCY, "display": SHIPPED_DISPLAY,
               "definition": ("lock-correct walks; lead = red minus green along the TRUE line, "
                              "positive is red ahead; 'post' is the frames from the first decoded "
                              "frame to the end press (w1's definition), 'all' adds the anchor "
                              "segment from the commit"),
               "per_head_offset": {}, "failures": RES["failures"]}
        for ho, acc in SWEEP_ACC.items():
            out["per_head_offset"][f"{ho:.3f}"] = {
                "walks": acc["walks"], "post": lead_stats(acc["post"]), "all": lead_stats(acc["all"]),
                "post_by_line_quarter": {str(q): lead_stats(v) for q, v in sorted(acc["quarters"].items())},
                "drawn_bound_s": acc["drawn_bound_s"], "evidence_bound_s": acc["evidence_bound_s"]}
        out["minutes"] = round((time.time() - t0) / 60.0, 2)
        save(STAGE, out)
        release(lock)
        for k, v in out["per_head_offset"].items():
            p = v["post"]
            status(f"  {TAG} head offset {k}: ahead {p.get('ahead_pct', float('nan')):5.1f}%  "
                   f"mean {p.get('signed_mean_m', float('nan')):+.3f} m  bounds "
                   f"{v['drawn_bound_s']:+.3f}/{v['evidence_bound_s']:+.3f} s")
        return 0 if not RES["failures"] else 1

    # f4 NEVER moves files: the frozen demo folder is not its folder, and demo_v2 starts empty
    RES["folder"] = {"before": before, "moved": [], "n_moved": 0, "moved_to": None,
                     "why_not": "f4 writes a new folder and moves nothing"}

    # ---- 3.3 ACCEPTANCE.md
    # THE LOCK AGAINST THE COMMITMENT, over nine pairings, from `d6_lock_commit` (2026-09-23d). It
    # measures the lock THIS RENDER DRAWS (the display decode, sd_scale 4.5) and the text commitment
    # on the ONE lattice. Until 2026-09-23d this table read `r5_lock`, the lock at 1.5 s on the grid
    # lattice printed as the 2 s lock. d6 is quoted only if its rows equal THIS render's walks, walk
    # for walk on this pairing; otherwise the table says STALE, and d6 must be re-run after the render.
    d6 = load("d6_lock_commit") or {}
    _d6_rows_p = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "d6_lock_commit", "rows.json")
    _d6_fresh = False
    if d6.get("VALID") and os.path.exists(_d6_rows_p):
        with open(_d6_rows_p, encoding="utf-8") as _f:
            _d6_mine = {(r["stem"].replace("participant_", "").split("_")[0], r["pass_id"]):
                        (r["lock_drawn"], r["headline_line"], r["text_line"])
                        for r in json.load(_f) if r["tag"] == TAG}
        # since 23e the text is the shipped semi-bounded decision, d6's HEADLINE line; the bounded
        # line is still checked, because it is still quoted as the disclosed price
        _here = {(who, int(w["pass_id"])): (w["locked_line"], w["committed"],
                                            w.get("bounded_end_press_line"))
                 for who, ws in acceptance for w in ws}
        _d6_fresh = bool(_here) and all(_d6_mine.get(k) == v for k, v in _here.items())
    _L6 = (d6.get("LOCK_DRAWN") or {}) if _d6_fresh else {}
    _C6 = (d6.get("COMMITTED_HEADLINE_semibounded_A2_veto") or {}) if _d6_fresh else {}
    _B6 = (d6.get("COMMITTED_TEXT_bounded_at_end_press") or {}) if _d6_fresh else {}
    _W6 = (d6.get("headline_minus_drawn_lock") or {}) if _d6_fresh else {}

    def _pct(s, key="all9_median"):
        if not s:
            return "STALE: re-run d6_lock_commit against this render"
        ci = s.get(f"{key}_ci95") or [float("nan")] * 2
        return f"{s[key]:.1f} percent [{ci[0]:.1f}, {ci[1]:.1f}]"
    n_walks = sum(len(w) for _who, w in acceptance)
    n_switch = sum(1 for _who, ws in acceptance for w in ws if w["switches"] > 0)
    # sort on an explicit KEY: the tuples end in a dict, and on a tie Python would try to compare
    # dicts, which raises rather than ordering
    best = sorted(((w["switches"], who, w) for who, ws in acceptance for w in ws),
                  key=lambda x: (-x[0], x[1]))[:3]
    r5 = load("r5_timeline") or load("g6_timeline") or {}
    agg_tl = (r5.get("aggregate") or {}).get("commit_pct_h1") or {}
    all_w = [w for _who, ws in acceptance for w in ws]
    here_tl = {d: 100.0 * sum(bool(w["commit_s"].get(d)) for w in all_w) / max(1, len(all_w))
               for d in DT_AXIS}
    flagged = [(who, w) for who, ws in acceptance for w in ws if w["flagged_many_switches"]]

    def pool(ws, field="within_pct"):
        v = [w["tracking"][field] for w in ws if w["tracking"].get(field) is not None]
        return float(np.mean(v)) if v else None

    ok_w = [w for w in all_w if w["found"]]
    bad_w = [w for w in all_w if not w["found"]]
    # THE SPLIT THAT MATTERS FOR TRACKING: whether the DRAWN line was right. On a wrong line the
    # distance between the dot and the walker is a line separation, not a tracking error, and
    # pooling the two makes the tracking figure a function of line accuracy instead of tracking.
    on_line = [w for w in all_w if w.get("lock_correct")]
    off_line = [w for w in all_w if not w.get("lock_correct")]
    before = (r1.get("pooled_tracking") or {})
    before_split = (r1.get("split") or {})
    committed = 100.0 * sum(w["found"] for w in all_w) / max(1, len(all_w))
    old_back = (r1.get("backward_steps") or {})
    now_back = sum(w["monotonicity_violations"] for w in all_w)

    L = ["# Acceptance: the measured results of the live demonstration", "",
         "**RULES LIVE IN `reports/tracking/render-rules.md`, NOT HERE.** This document holds MEASURED "
         "RESULTS ONLY. If you want to know what the demonstration is required to do, read the "
         "contract: rules 1 to 6 and the operator's rules V1 to V4. Two copies of a rule is how a "
         "rule gets re-litigated, so there is exactly one copy and it is not this file.", ""]
    # ---- f4's own section: what changed from the frozen f3 videos, measured on both
    def _phase(recs):
        pr = []
        for _who, _ws in recs:
            for _w in _ws:
                if _w["locked_line"] != _w["true"] or _w.get("mid_walk_switches"):
                    continue
                for _r, _g in zip(_w.get("rpost") or [], _w.get("gpost") or []):
                    if _r is None or _g is None:
                        continue
                    pr.append((along(room_paths, _w["true"], _r) - along(room_paths, _w["true"], _g),
                               float(np.hypot(_r[0] - _g[0], _r[1] - _g[1]))))
        return lead_stats(pr)
    _f3 = load("f3_render") or {}
    ph_old = _phase([(k, v["walks"]) for k, v in (_f3.get("recordings") or {}).items()])
    ph_new = _phase(acceptance)
    _sel = (load("f4_phase_s0103_to_s02") or {}).get("per_head_offset", {}).get(f"{HEAD_OFFSET_S:.3f}", {})
    _sp = _sel.get("post") or {}
    RES["phase"] = {"head_offset_s": HEAD_OFFSET_S, "f3_frozen_videos": ph_old, "f4_this_render": ph_new,
                    "selection_pairing_s0103_to_s02": _sp,
                    "prereg": "reports/tracking/history/2026-09-24_prereg-display-phase.md"}

    def _f(d, k, fmt):
        return format(d[k], fmt) if d.get(k) is not None else "n/a"
    L += ["## What f4 changes, 2026-09-24, measured against the frozen f3 videos", "",
          "`runs/constrained/demo/` (f3, frozen and hashed in freeze 23h) is untouched. These videos come "
          "from `pipeline/constrained/f4_render.py`, a copy of f3 with the changes below and nothing else: "
          "the decode, the lock, the committed decision, switching and V1 to V4 are f3's.", "",
          "**The display phase.** The dot's timing rests on `HEAD_OFFSET_S`, when the display head is taken "
          "to name behind the end of its window. f3 used R1's 0.75 s of 2026-09-21, measured before the ONE "
          f"lattice. f4 draws **{HEAD_OFFSET_S:g} s**, chosen by `reports/tracking/history/2026-09-24_prereg-display-phase.md` "
          "on `s0103_to_s02`, the other pairing trained on two sessions, against the operator's accepted phase "
          "of 2026-09-23 (ahead on 33.5 percent of frames, mean -0.281 m). **The demo pairing was not used to "
          "choose.** A smaller value draws every decoded position later, never earlier.", "",
          "| lock-correct walks without a switch | f3, frozen videos | f4, these videos | f4 on the selection pairing |",
          "|---|---|---|---|",
          f"| frames | {ph_old.get('n_frames', 0)} | {ph_new.get('n_frames', 0)} | {_sp.get('n_frames', 0)} |",
          f"| red AHEAD of green along the line | {_f(ph_old, 'ahead_pct', '.1f')} percent | "
          f"{_f(ph_new, 'ahead_pct', '.1f')} percent | {_f(_sp, 'ahead_pct', '.1f')} percent |",
          f"| signed mean, median | {_f(ph_old, 'signed_mean_m', '+.3f')}, {_f(ph_old, 'signed_median_m', '+.3f')} m | "
          f"{_f(ph_new, 'signed_mean_m', '+.3f')}, {_f(ph_new, 'signed_median_m', '+.3f')} m | "
          f"{_f(_sp, 'signed_mean_m', '+.3f')}, {_f(_sp, 'signed_median_m', '+.3f')} m |",
          f"| within 0.5 m | {_f(ph_old, 'within_0_5m_pct', '.1f')} percent | {_f(ph_new, 'within_0_5m_pct', '.1f')} "
          f"percent | {_f(_sp, 'within_0_5m_pct', '.1f')} percent |", "",
          "**The picture.** The room fills the frame; the legend and the clock sit in a band above it, clear of "
          "RX1, which is drawn at its measured position. At each walk's end the bottom says CORRECT in green or "
          "WRONG in red for the shipped committed decision, with this participant's running accuracy and the "
          "total over all six, held until the next walk commits. The old \"lag 1s\" label is gone: it was the "
          "window-centre offset, not a delay the viewer sees, and the display's only delay is the 2.0 s stated "
          "in the clock.", "",
          "**The causal bounds** are computed on the step the dot actually glides towards. f3's check left "
          "SHIFT_W out and so checked a step up to one stride earlier than the one read.", "",
          f"Rendered on `{TAG}`, cross-day, trained on sessions 01 and 02. Five-head pool, "
         f"0.5 s stride, nothing retrained. **This is the strongest of the nine cross-day "
         f"pairings and is not the system**; the figure to quote is the nine-pairing aggregate.",
         "",
         "## Configuration as applied", "",
         "| setting | value |",
         "|---|---|",
         f"| display arm | {SHIPPED_DISPLAY} |",
         f"| decoder entry | {ENTRY} |",
         f"| display lag | {LAG:g} s |",
         f"| cross-line slide cap | {CAP if CAP else 'none'} |",
         f"| display hysteresis | {DISPLAY_HYSTERESIS} window |",
         "| semi-bounded exit rule | causal |",
         f"| display latency, rule V1 | {LATENCY:g} s |",
         f"| evidence before the commit | {DELAY:g} s |",
         f"| lock offset from the walk start, rule V3 | {WINDOW_S - HEAD_OFFSET_S - WINDOW_S / 2.0 + LATENCY:g} s, "
         f"identical on every walk |",
         "",
         "### Why V3's lock offset is 2.25 s while V1's latency is 2.0 s", "",
         f"**They are measured from different origins, and both numbers are measured rather than "
         f"assumed.** V1's {LATENCY:g} s is how far the SCENE runs behind real time. V3's offset is "
         f"measured from `t_start`, which the render defines as the CENTRE of the walk's first "
         f"window, at `t[lo] + {WINDOW_S / 2.0:g}`. The scene itself begins "
         f"{WINDOW_S - HEAD_OFFSET_S - WINDOW_S / 2.0:g} s after that centre, at "
         f"`t[lo] + {WINDOW_S:g} - {HEAD_OFFSET_S:g}`: the first window finishes recording "
         f"{WINDOW_S:g} s after it began, and the display head names a moment {HEAD_OFFSET_S:g} s "
         f"behind the window it is read from. The commit is then exactly {LATENCY:g} s after the "
         f"scene begins, so "
         f"{WINDOW_S - HEAD_OFFSET_S - WINDOW_S / 2.0:g} + {LATENCY:g} = "
         f"{WINDOW_S - HEAD_OFFSET_S - WINDOW_S / 2.0 + LATENCY:g} s.", "",
         "Measured over the 120 walks of this pairing: the offset is identical on every one of "
         "them, which is what rule V3 requires, and the window centre it is measured from sits a "
         "median 0.202 s after the press (p10 0.031, p90 0.418) because the 0.5 s window lattice "
         "does not align with the press. That spread is in WHERE THE ORIGIN FALLS, never in the "
         "offset itself.", "", "## The lock against the commitment", "",
         "| | over nine pairings |", "|---|---|",
         f"| line locked at {DELAY:g} s, which is what the viewer watches | {_pct(_L6)} |",
         f"| line committed, shown as text: the SHIPPED semi-bounded decision | {_pct(_C6)} |",
         "| they agree, pooled over passes | "
         + (f"{d6['agree_pooled_pct']['lock_drawn_vs_headline']:.1f} percent |"
            if _d6_fresh else "STALE |"),
         "| waiting buys, paired per pairing | "
         + (f"{_W6['all9_mean_paired']:+.1f} points, interval [{_W6['all9_ci95'][0]:.1f}, "
            f"{_W6['all9_ci95'][1]:.1f}] |" if _d6_fresh else "STALE |"),
         "",
         "Medians over the nine cross-day pairings with 95 percent intervals, ONE lattice, from "
         "`d6_lock_commit`, which decodes the lock exactly as this render draws it and matches this "
         "render walk for walk. **Since 2026-09-23e the text names the SHIPPED semi-bounded committed "
         "decision (A2 + a_veto_1.0), the headline's own answer**, checked against `d4_headline` walk "
         "for walk below. Until then it named the bounded rescore at the end press, which uses the "
         "end press the semi-bounded mode is not told.", "",
         "**THE DISCLOSED PRICE OF THE CORRECTNESS FIX.** The ONE lattice costs the bounded rescore at "
         "the end press, which is no longer shown: "
         + (f"{_pct(_B6)}, from 65.83 on the grid lattice, " if _d6_fresh else "")
         + "paired **-2.59 [-4.63, -0.46]**, every edge line losing walks (E_col1 -6, E_col5 -3, "
         "E_row1 -3, E_row5 -6). `reports/tracking/history/2026-09-23_correction-drawn-lock.md`.",
         "", "## The lock, on this pairing", "",
         "| | |", "|---|---|",
         f"| commit delay | {DELAY:g} s |",
         f"| display lag after the lock | {LAG:g} s |",
         f"| locked line correct | {100.0 * sum(w['lock_correct'] for w in all_w) / max(1, len(all_w)):.1f} percent of walks |",
         f"| distinct lines after the lock | {max(w['distinct_lines_after_lock'] for w in all_w)} on every walk |",
         f"| frozen tails, display running out before the press | "
         f"{(a3.get('horizon') or {}).get('frozen_gt_1s_pct_own_end', 0):.1f} percent to "
         f"{(a3.get('horizon') or {}).get('frozen_gt_1s_pct_horizon', 0):.1f} percent |", "",
         "| participant | locked line correct | committed correct | tracking |",
         "|---|---|---|---|"]
    for who, ws in acceptance:
        L.append(f"| {who} | {100.0 * sum(w['lock_correct'] for w in ws) / max(1, len(ws)):.0f} "
                 f"percent | {100.0 * sum(w['found'] for w in ws) / max(1, len(ws)):.0f} percent | "
                 f"{(pool(ws) or 0):.1f} percent |")

    def pool_dec(ws, field="within_pct"):
        v = [w["decoded_accuracy"][field] for w in ws
             if (w.get("decoded_accuracy") or {}).get(field) is not None]
        return float(np.mean(v)) if v else None

    def pool_off(ws, field="mean_m"):
        v = [w["display_offset"][field] for w in ws
             if (w.get("display_offset") or {}).get(field) is not None]
        return float(np.mean(v)) if v else None

    _near = "t minus %.1f s" % LAG if (pool_dec(all_w) or 0) > (pool(all_w) or 0) else "t"

    def pool_live(ws, field="mean_m"):
        v = [w["offset_from_live_truth"][field] for w in ws
             if (w.get("offset_from_live_truth") or {}).get(field) is not None]
        return float(np.mean(v)) if v else None

    L += ["", "## The whole display runs behind real time, and the delay was measured", "",
          f"**{LATENCY:g} seconds**, rule V1. The green marker shows where the walker was "
          f"{LATENCY:g} s ago and the red dot shows the tracker's answer for that same moment, so "
          f"the two are directly comparable.", "",
          "**The delay is MEASURED, not taken from the training label**, and the two disagree:",
          "", "| | |", "|---|---|",
          f"| what the head's training label says it names | **{LABEL_DELAY:g} s**, the window END |",
          f"| what the head actually names, measured over nine pairings | "
          f"**{HEAD_MEASURED_S:g} s** behind the window it is read from |",
          f"| what the DISPLAY runs behind, which is the live mode's latency | **{LATENCY:g} s** |",
          "", "The shipped display head is trained on the position at the window end, so by its "
          "label it names the present. Measured, it does not: R1 swept the offset and found the "
          f"drawn dot closest to the truth {HEAD_MEASURED_S:g} s earlier, and the drawn index is "
          "set from the measurement rather than from the label.", "",
          "### The delay was chosen on the same data it is reported on", "",
          "**Disclosed, because it flatters the figure below.** R1 swept the offset and picked the "
          "one with the lowest mean error. The display is then scored at that same offset, over "
          "the same nine pairings. That is selection and reporting on one dataset, and the "
          "within-0.5 m figure it yields is optimistically biased.", "",
          "Two things follow, and they point opposite ways:", "",
          "| | |", "|---|---|"]
    _cur = ((r1ref.get("per_arm") or {}).get("DISP_END") or {}).get("by_offset") or {}
    _best = _cur.get(f"{HEAD_MEASURED_S:.2f}") or {}
    _alt = _cur.get("1.00") or {}
    L += [f"| the DELAY is robust | the curve is smooth and single-peaked: "
          f"{HEAD_MEASURED_S:g} s gives {(_best.get('abs_mean_m') or 0):.3f} m and 1.0 s gives "
          f"{(_alt.get('abs_mean_m') or 0):.3f} m, a tie. 'About three quarters of a second "
          f"behind' holds whichever side of the peak you take |",
          f"| the SCORE at the peak is not | within 0.5 m reads "
          f"{(_best.get('within_0_5_pct') or 0):.1f} percent at the selected "
          f"{HEAD_MEASURED_S:g} s against {(_alt.get('within_0_5_pct') or 0):.1f} percent at a "
          f"pre-specified 1.0 s, so picking the peak buys about "
          f"{abs((_best.get('within_0_5_pct') or 0) - (_alt.get('within_0_5_pct') or 0)):.1f} "
          f"points |",
          "", "The honest reading is the second column of that table: quote the delay with "
          "confidence and treat the accuracy at it as a slight upper bound. A clean version would "
          "pick the offset on some folds and report it on the others; that was not done and this "
          "note stands in its place.", "",
          "| | |", "|---|---|",
          f"| display transition prior | **{PRIOR_ARM}** |",
          f"| its substitution ratio on post-lock along-line progress | **{(PRIOR_SUBS or 0):.2f}** "
          f"against **0.29** for the previous setting |",
          "", "The prior was chosen in R3 by sweeping the display's own motion model from the "
          "shipped step model down to none. A weaker prior means more of the drawn along-line "
          "progress comes from the radio and less from the model: the substitution ratio roughly "
          "doubles. **The gate that selected it was loosened AFTER the sweep was seen**, from "
          "'no worse than the shipped display' to 'excess motion under 0.5 percent of frames', "
          "because the first form meant exactly zero and only the shipped setting could meet it. "
          "That is a post-hoc rule change and it is disclosed here rather than folded in. It is "
          "acceptable only because the display is a presentation choice: no accuracy figure "
          "quoted anywhere in this project depends on it.", "",
          "| | |", "|---|---|",
          f"| frames within 0.5 m of the marker, the single reference | "
          f"**{(pool(all_w) or 0):.1f} percent** |",
          f"| mean distance to it | {(pool(all_w, 'mean_m') or 0):.2f} m |",
          f"| offset from LIVE truth, reported separately | {(pool_live(all_w) or 0):.2f} m mean |",
          "", "The last row is the price of the delay, not an error in the tracker. It is kept "
          "apart from the row above it rather than folded in.", "",
          "### Tracking, split by whether the dot is on the right line", "",
          "**This is the split to read.** When the dot has committed to the wrong line, the "
          "distance between it and the walker is the distance between two taped lines. That is a "
          "LINE error being reported as a TRACKING error, and pooling the two makes the tracking "
          "figure a function of line accuracy rather than of tracking.", "",
          "| | walks | within 0.5 m | mean distance |", "|---|---|---|---|",
          f"| **dot on the RIGHT line** | **{len(on_line)} of {len(all_w)}** | "
          f"**{(pool(on_line) or 0):.1f} percent** | **{(pool(on_line, 'mean_m') or 0):.2f} m** |",
          f"| dot on the wrong line | {len(off_line)} of {len(all_w)} | "
          + (f"{(pool(off_line) or 0):.1f} percent | {(pool(off_line, 'mean_m') or 0):.2f} m |"
             if off_line else "no wrong-line walks | no wrong-line walks |"),
          f"| pooled, as quoted above | {len(all_w)} | {(pool(all_w) or 0):.1f} percent | "
          f"{(pool(all_w, 'mean_m') or 0):.2f} m |",
          "", "The first row is what the tracker does when it knows where you are. The third is "
          "the first dragged down by the second, and it is the weaker question: it asks how often "
          "the system is both on the right line AND close, which is two things at once.", "",
          "**The dot and the marker leave together.** The scene begins at the first moment the "
          "decoder has a position to draw, and the marker is not shown before then. Until "
          "2026-09-21 the marker appeared at the walker's true first press while the dot could "
          "not draw until its first window's label time, on average 0.475 s later. Rules 6 and V2 "
          "in `reports/tracking/render-rules.md` are what stop it recurring.", "",
          "## Decoded accuracy and display offset, reported separately", "",
          f"Reported apart and never added, per rule 4. A window spans {WINDOW_S:g} s and may only "
          f"be drawn once it has ENDED, so a dot drawn at time t comes from a window covering "
          f"t minus {WINDOW_S:g} s to t.", "",
          f"The shipped display arm is **{SHIPPED_DISPLAY}**. The pool heads that decide the LINE "
          f"are labelled at the window CENTRE, so they name t minus {LAG:g} s. DISP-END is a "
          f"display-only head trained on the position at the window END, which would name t. "
          f"**It does not get there.** Measured below, the drawn dot is nearer the truth at "
          f"{_near} than at the other moment, so the end label moved the dot forward without "
          f"closing the lag: step 2 measured it closing about a quarter of the gap over nine "
          f"pairings, 2.087 m to 1.867 m. The two rows below are the same dot against two "
          "different moments, and they are never added together or traded off.", "",
          "| | measured against | value |", "|---|---|---|",
          f"| **decoded accuracy** | the truth at the moment the CENTRE-labelled pool is naming, "
          f"t minus {LAG:g} s | **{(pool_dec(all_w) or 0):.1f} percent** within 0.5 m, "
          f"{(pool_dec(all_w, 'mean_m') or 0):.2f} m mean |",
          f"| **on-screen tracking** | the truth at the frame the viewer sees, t | "
          f"**{(pool(all_w) or 0):.1f} percent** within 0.5 m, "
          f"{(pool(all_w, 'mean_m') or 0):.2f} m mean |",
          f"| **display offset** | how far the walker travels during the {LAG:g} s lag | "
          f"**{(pool_off(all_w) or 0):.2f} m** mean, "
          f"{(pool_off(all_w, 'median_m') or 0):.2f} m median |", "",
          "The display offset is how far the walker travels during the lag. It is a property of "
          f"walking pace and the {WINDOW_S:g} s window, not of the model. The only thing that "
          "closes it completely is assuming the walker kept going at the pace just measured, and "
          "that assumption is dead reckoning: it was deleted from the display path on 2026-09-20 "
          "and it is not coming back through a caption. Training a head on the end label was the "
          "honest attempt at closing it from the signal, it is what ships, and it recovers only "
          "part of it.", "",
          "**Both causality bounds are reported, because one of them is not enough.** The "
          f"drawn-window bound asks whether the window being NAMED had finished recording by the "
          f"frame: {RES['causal_bound_s']:+.3f} s. The evidence bound asks whether the radio that "
          f"DECODED it had: {RES['causal_evidence_bound_s']:+.3f} s. Until 2026-09-20 only the "
          "first was checked, and it read a clean zero through a leak of a full second that only "
          "the second one shows.", "",
          "| split | decoded accuracy, within 0.5 m | on-screen tracking, within 0.5 m |",
          "|---|---|---|",
          f"| correct-line passes | {(pool_dec(ok_w) or 0):.1f} percent | {(pool(ok_w) or 0):.1f} "
          f"percent |",
          "| wrong-line passes | "
          + (f"{(pool_dec(bad_w) or 0):.1f} percent | {(pool(bad_w) or 0):.1f} percent |"
             if bad_w else "no wrong-line passes | no wrong-line passes |"),
          "", "## On-screen tracking, which is the acceptance number", "",
         "Measured **at the displayed time, so the display lag counts against it**: the fraction "
         "of frames in which the drawn red dot is within 0.5 m of the drawn green dot.", "",
         "| | before, the render frozen at 18m | after |", "|---|---|---|",
         f"| frames within 0.5 m | **{(before.get('within_pct') or 0):.1f} percent** | "
         f"**{pool(all_w):.1f} percent** |",
         f"| mean on-screen distance | {(before.get('mean_m') or 0):.2f} m | "
         f"{pool(all_w, 'mean_m'):.2f} m |",
         f"| frames with NO red dot | {before.get('n_no_red_dot')} | "
         f"**{RES['dot_visible']['frames_without_dot']}** |",
         f"| backward steps along a line | {old_back.get('total')} | **{now_back}** |",
         f"| changes of the shown line per walk | up to 4 | **the lock, plus at most ONE mid-walk "
         f"switch (rule 1 as amended, 23e)** |", "",
         "| split | before, within 0.5 m | after, within 0.5 m |", "|---|---|---|",
         f"| correct-line passes | "
         f"{(((before_split.get('correct_line') or {}).get('within_pct_mean_over_passes')) or 0):.1f} "
         f"percent | {pool(ok_w):.1f} percent |",
         f"| wrong-line passes | "
         f"{(((before_split.get('wrong_line') or {}).get('within_pct_mean_over_passes')) or 0):.1f} "
         f"percent | " + (f"{pool(bad_w):.1f} percent |" if bad_w else "no wrong-line passes |"),
         "", "### Every display lag that was swept", "",
         "| lag | cap | within 0.5 m | interval | mean distance | rule violations |",
         "|---|---|---|---|---|---|"]
    for k in sorted((r3.get("arms") or {})):
        a = r3["arms"][k]
        L.append(f"| {a['lag_s']:g} s | {a['cap']} | {a['pooled']['within_pct']:.2f} percent | "
                 f"{[round(x, 2) for x in a['ci95'][-2:]]} | {a['pooled']['mean_m']:.2f} m | "
                 f"{a['rule_violations']} |")
    L += ["", "**The 2.0 m/s cross-line cap was dropped.** It cost on-screen tracking and, under "
          "continuous retargeting, it could not satisfy the one rule either: the destination moves "
          "out from under the dot mid-crossing. Both are visible in the table above.", "",
          "## Walks flagged for many switches", ""]
    if flagged:
        L += [f"**{len(flagged)} walks change the shown line more than four times.** Flagged, not "
              "smoothed.", "", "| participant | walk | switches | true | committed |",
              "|---|---|---|---|---|"]
        for who, w in flagged:
            L.append(f"| {who} | {w['pass_id']} | {w['switches']} | {w['true']} | "
                     f"{w['committed'] or 'none'} |")
    else:
        L.append("No walk changes the shown line more than four times.")
    L += ["", "## The commitment timeline, on the pool at the shipped lag", "",
          "| seconds after the press | this pairing | nine-pairing aggregate |", "|---|---|---|"]
    for d in DT_AXIS:
        a = agg_tl.get(d)
        L.append(f"| {d} s | {here_tl[d]:.1f} percent | "
                 + (f"{a:.1f} percent |" if a is not None else "not measured |"))
    L += ["", "## Per participant, at the shipped lag", ""]
    for who, ws in acceptance:
        L += [f"### {who}", "",
              "| walk | true | locked | lock correct | switched to | drawn at end | committed | "
              "committed correct | within 0.5 m | mean distance |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for w in ws:
            tw = w["tracking"]
            _s = w.get("mid_switches") or []
            L.append(f"| {w['pass_id']} | {w['true']} | {w['locked_line']} | "
                     f"{'yes' if w['lock_correct'] else 'no'} | "
                     + ("; ".join(f"{q_['new']} at +{q_['after_lock_s']:.1f} s" for q_ in _s) or "none")
                     + f" | {w.get('drawn_end_line') or 'none'} | {w['committed'] or 'none'} | "
                     f"{'yes' if w['found'] else 'no'} | {(tw['within_pct'] or 0):.0f} percent | "
                     f"{(tw['mean_m'] or 0):.2f} m |")
        L.append("")
    L += ["## This pairing against the aggregate", "",
          "| | this pairing | nine-pairing aggregate |", "|---|---|---|",
          f"| committed line, the SHIPPED semi-bounded decision (shown as text) | {committed:.1f} "
          f"percent | {_pct(_C6)} |",
          f"| the bounded rescore at the end press (NOT shown since 23e; the disclosed price) | "
          f"{100.0 * np.mean([bool(w.get('bounded_found')) for w in all_w]):.1f} percent | "
          f"{_pct(_B6)} |",
          f"| line locked at {DELAY:g} s (drawn) | "
          + (f"{_L6['per_pairing'].get(TAG, float('nan')):.1f} percent" if _L6 else "STALE")
          + f" | {_pct(_L6)} |", ""]
    # BOTH HEADLINES, operator instruction 4 item 4: the pre-registered 62.50 and the
    # post-amendment figure, with the amendment disclosed beside it. From d4_headline, which
    # re-measures both over nine pairings with intervals and reproduces the measured arms exactly.
    d4 = load("d4_headline") or {}
    if d4.get("VALID"):
        C4 = d4["COMMITTED"]
        # THE LOCK COLUMN is the DRAWN lock (d6_lock_commit, sd_scale 4.5, both lattices). d4's LOCK
        # decoded at sd_scale 1.0, which is not the lock this render draws (13 of 120 walks differ
        # on this pairing); it is no longer quoted here.
        _Lg = (d6.get("PRE_REGISTERED_grid_LOCK_DRAWN") or {}) if _d6_fresh else {}
        _Ld = (d6.get("drawn_lock_one_minus_grid") or {}) if _d6_fresh else {}

        def _h7(x):
            return f"{x['heldout7_median']:.2f}" if x else "STALE"
        pr, sh = C4["PRE_REGISTERED_62_50"], C4["POST_AMENDMENT_SHIPPED"]
        pv = C4["shipped_vs_prereg_paired"]
        L += ["## The headline, both figures (nine pairings, median, 95 percent intervals)", "",
              "| | committed, semi-bounded, all nine | held-out seven | lock, held-out seven |",
              "|---|---|---|---|",
              f"| **PRE-REGISTERED** (freeze 23b, grid lattice) | **{pr['all9_median']:.2f}** "
              f"[{pr['all9_median_ci95'][0]:.2f}, {pr['all9_median_ci95'][1]:.2f}] | "
              f"{pr['heldout7_median']:.2f} | {_h7(_Lg)} |",
              f"| **POST-AMENDMENT, SHIPPED** (the ONE lattice + a_veto_1.0) | "
              f"**{sh['all9_median']:.2f}** [{sh['all9_median_ci95'][0]:.2f}, "
              f"{sh['all9_median_ci95'][1]:.2f}] | {sh['heldout7_median']:.2f} | "
              f"{_h7(_L6)} |", "",
              f"Paired, shipped against pre-registered, all nine: "
              f"{pv['all9_mean_paired']:+.2f} [{pv['all9_ci95'][0]:.2f}, {pv['all9_ci95'][1]:.2f}]. "
              f"**The amendment, disclosed:** a_veto_1.0 ships only because condition (f) was AMENDED "
              f"by the operator on 2026-09-23, POST HOC; the figure also moves because the lattice "
              f"was fixed (a correctness change, not an arm). The lock column is the lock this "
              f"render DRAWS (display decode); paired, one lattice minus grid, all nine: "
              + (f"{_Ld['all9_mean_paired']:+.2f} [{_Ld['all9_ci95'][0]:.2f}, "
                 f"{_Ld['all9_ci95'][1]:.2f}]." if _Ld else "STALE."), ""]
    # ---- batch 23e: THE TWO WALK-FOR-WALK CHECKS, computed here and asserted by the suite
    _fh = os.path.join(REPO_ROOT, "runs", "constrained", "fh")
    _vp = os.path.join(_fh, "d4_headline", "rows_veto.json")
    _veto = {}
    if os.path.exists(_vp):
        with open(_vp, encoding="utf-8") as _f:
            _veto = {r["key"]: r["final_line"] for r in json.load(_f)}
    _chk = [(w["key"], w["committed"], _veto.get(w["key"])) for w in all_w]
    RES["end_text_check"] = {
        "what": "the end-of-walk text equals the shipped headline decision (d4_headline rows_veto)",
        "n": len(_chk), "equal": int(sum(a == b for _k, a, b in _chk)),
        "mismatches": [k for k, a, b in _chk if a != b][:10]}
    RES["end_text_check"]["PASSED"] = bool(_chk and RES["end_text_check"]["equal"] == len(_chk))
    _e2p = os.path.join(_fh, "e2_switch", "rows.json")
    if SWITCH and os.path.exists(_e2p):
        _arm = f"{SWITCH['arm']}_t{float(SWITCH['theta']):g}"
        with open(_e2p, encoding="utf-8") as _f:
            _e2r = {r["key"]: r["arms"][_arm] for r in json.load(_f) if r["tag"] == TAG}
        # the switch SEQUENCE: each switch's new line and decision frame, as both records carry them
        _pairs = [(w["key"], [(q_["new"], round(float(q_["x"]), 3)) for q_ in (w.get("mid_switches") or [])],
                   [(q_["new"], round(float(q_["x"]), 3)) for q_ in ((_e2r.get(w["key"]) or {}).get("switches") or [])])
                  for w in all_w]
        RES["switch_check_vs_e2"] = {
            "what": "the render's switch sequences equal e2_switch's at the rendered arm, walk for walk",
            "arm": _arm, "n": len(_pairs), "equal": int(sum(a == b for _k, a, b in _pairs)),
            "mismatches": [k for k, a, b in _pairs if a != b][:10]}
        RES["switch_check_vs_e2"]["PASSED"] = bool(
            _pairs and RES["switch_check_vs_e2"]["equal"] == len(_pairs))
    else:
        RES["switch_check_vs_e2"] = {"what": "no switching rendered", "PASSED": SWITCH is None}
    _S = RES["switching"]
    _J = _S["jump_m"]
    _ev = (e2.get("evaluation") or {})
    _inv = _ev.get("estimators_at_the_lock") or {}
    L += ["", "## Mid-walk switching, rule 1a (display only, operator decision, batch 23f)", "",
          "**It changes no committed answer and no quoted accuracy figure.** Disclosed beside it: "
          "as a DECISION arm, switching failed (f) in `y3_switch` (E_col5 -3 walks).", ""]
    if _inv:
        L += ["**How switching works, as measured.** The LOCK is drawn from the edge-safe DISPLAY "
              "decoder (the speed cap and the end-of-walk display head). A switch hands the dot over "
              "to the FINAL-ANSWER scorer, each line's evidence total with the shipped start term (the "
              "committed decision's own estimator), once that scorer is confidently different: ahead "
              "by more than theta nats at two consecutive checks. **The two estimators disagree at the "
              f"lock on {_inv['disagree_walks']} of 1080 walks ({_inv['disagree_pct']:.1f} percent) "
              "over nine pairings.** On the lock's own radio the display lock is right on "
              f"{_inv['display_lock_correct_pct']:.1f} percent of walks and the scorer on "
              f"{_inv['scorer_best_correct_pct']:.1f} percent; edge recall, display lock against "
              "scorer: " + ", ".join(f"{ln} {v['display_lock']:.1f} / {v['scorer_at_lock']:.1f}"
                                     for ln, v in (_inv.get("edge_recall") or {}).items()) + ".", ""]
    if SWITCH:
        _arm = f"{SWITCH['arm']}_t{float(SWITCH['theta']):g}"
        _A = (_ev.get("per_arm") or {}).get(_arm) or {}
        _rs = _A.get("reconciling_share")
        if _rs is not None:
            L += [("**Most switches reconcile the two estimators rather than react to new mid-walk "
                   f"evidence: {100.0 * _rs:.1f} percent of the rendered rule's switches go to the line "
                   "the scorer already preferred on the lock's own radio.**") if _rs > 0.5 else
                  ("**Measured, most switches do NOT merely reconcile the two estimators: only "
                   f"{100.0 * _rs:.1f} percent of the rendered rule's switches go to the line the "
                   "scorer already preferred on the lock's own radio; the rest follow evidence that "
                   "arrived after the lock.**"), ""]
        L += [f"Rendered: **arm {SWITCH['arm']}**, at most {SWITCH['max_switches']} switch(es), none "
              f"in the final {float(SWITCH['final_m']):g} m, within {float(SWITCH['radius_m']):g} m, "
              f"theta **{float(SWITCH['theta']):g}** nats on the selection folds, chosen by the "
              "operator's rule fixed before any number (`reports/tracking/history/2026-09-23f_prereg-switching-arms.md`, "
              "`e2_switch`).", "",
              "| arm, nine pairings | theta | time on correct [95%] | held-out [95%] | W2R / R2W / W2W | "
              "dot ends on committed | text contradicts dot | switches | over 1.5 m | qualifies |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for _a, _c in sorted((_ev.get("chosen") or {}).items()):
            L.append(f"| {_a} | {_c['theta']:g} | {_c['toc_all9']:+.2f} "
                     f"[{_c['ci95'][0]:.2f}, {_c['ci95'][1]:.2f}] | {_c['toc_heldout7']:+.2f} "
                     f"[{_c['heldout7_ci95'][0]:.2f}, {_c['heldout7_ci95'][1]:.2f}] | "
                     f"{_c['w2r']} / {_c['r2w']} / {_c['w2w']} | {_c['end_on_committed']} | "
                     f"{_c['text_contradicts_dot']} | {_c['switch_events']} | {_c['jumps_over_1_5m']} | "
                     f"{_c['QUALIFIES']} |")
        L += ["", "| this render's own switches | |", "|---|---|",
              f"| walks / switches | {_S['walks']} / {_S['switches']} |",
              f"| wrong-to-right, right-to-wrong, wrong-to-wrong | {_S['w2r']}, {_S['r2w']}, {_S['w2w']} |",
              f"| dot ends on the committed line | {_S['end_on_committed']} of {_S['walks']} |",
              f"| jump distance, median / over 1.5 m | "
              + (f"{np.median(_J):.2f} m / {sum(j > 1.5 for j in _J)}" if _J else "none") + " |",
              f"| earliest switch after the lock | {_S['earliest_after_lock_s']} s |",
              f"| switches in the final zone / persistence violations / back to a drawn line | "
              f"{_S['switch_in_final_zone']} / {_S['persistence_violations']} / "
              f"{_S['returns_to_a_drawn_line']} |",
              f"| decision evidence bound / target drawn bound / target evidence bound | "
              f"{_S['decision_evidence_worst_s']:.3f} / {_S['target_drawn_worst_s']:.3f} / "
              f"{_S['target_evidence_worst_s']:.3f} s |",
              f"| slide frames off their segment | {_S['slide_off_segment_frames']} |",
              f"| frame jumps over 0.5 m caused by a switch (apart from the lock's) | "
              f"{RES['jumps']['caused_by_a_switch']} |",
              f"| render equals `e2_switch`, walk for walk | "
              f"{RES['switch_check_vs_e2'].get('equal')} of {RES['switch_check_vs_e2'].get('n')} |", ""]
    else:
        L += ["**No switching rendered**: " + (_ev.get("why_none") or "no valid `e2_switch` choice")
              + "; the dot stays on the locked line (lock-final).", ""]
    L += [f"**The end text equals the shipped headline decision on "
          f"{RES['end_text_check']['equal']} of {RES['end_text_check']['n']} walks** "
          "(`d4_headline` rows_veto).", ""]
    L += [
          "**This is the strongest cross-day pairing and it is not typical.** The aggregate is "
          "the figure to quote. The committed answer here is the shipped SEMI-BOUNDED decision, "
          "which is not told the end press."]
    with open(os.path.join(DEMO, "ACCEPTANCE.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    after = sorted(os.listdir(DEMO))
    vids = [f for f in after if f.endswith(".mp4")]
    RES["folder"]["after"] = after
    RES["folder"]["is_six_videos_and_acceptance"] = bool(
        len(vids) == 6 and set(after) == set(vids) | {"ACCEPTANCE.md"})
    mt = [os.path.getmtime(os.path.join(DEMO, v)) for v in vids]
    RES["folder"]["one_render_run"] = bool(mt and (max(mt) - min(mt)) < 3600)
    RES["folder"]["all_plausible_by_bytes"] = bool(
        all(RES["recordings"][w]["bytes_per_frame"] > 100 for w in RES["recordings"]))
    RES["acceptance"] = {"n_walks": n_walks, "n_walks_with_a_switch": n_switch,
                         "committed_line_pct_this_pairing": committed,
                         "commit_timeline_h1_this_pairing": here_tl,
                         "commit_timeline_h1_aggregate": agg_tl,
                         "display_hysteresis": DISPLAY_HYSTERESIS,
                         "on_screen_within_pct": pool(all_w),
                         "on_screen_mean_m": pool(all_w, "mean_m"),
                         # THE TWO SEPARATE NUMBERS the brief of 2026-09-20 asks for, kept apart
                         # here as well as in the markdown so no later stage can pool them.
                         "decoded_within_pct": pool_dec(all_w),
                         "decoded_mean_m": pool_dec(all_w, "mean_m"),
                         "decoded_within_pct_correct_line": pool_dec(ok_w),
                         "display_offset_mean_m": pool_off(all_w),
                         "display_offset_median_m": pool_off(all_w, "median_m"),
                         "nothing_is_projected": True,
                         "display_arm": SHIPPED_DISPLAY,
                         "display_latency_s": LATENCY,
                         "evidence_before_commit_s": DELAY,
                         "head_measured_offset_s": HEAD_MEASURED_S,
                         "display_delay_is_measured_not_the_label": True,
                         "label_delay_s": LABEL_DELAY,
                         "display_prior_arm": PRIOR_ARM,
                         "display_prior_substitution_ratio": PRIOR_SUBS,
                         "display_prior_gate_was_loosened_post_hoc": True,
                         "offset_from_live_truth_mean_m": pool_live(all_w),
                         "within_0_5m_of_the_single_delayed_marker_pct": pool(all_w),
                         "tracking_on_the_right_line_within_0_5m_pct": pool(on_line),
                         "tracking_on_the_right_line_mean_m": pool(on_line, "mean_m"),
                         "tracking_on_the_right_line_n_walks": len(on_line),
                         "tracking_on_the_wrong_line_within_0_5m_pct": pool(off_line),
                         "tracking_on_the_wrong_line_mean_m": pool(off_line, "mean_m"),
                         "tracking_on_the_wrong_line_n_walks": len(off_line),
                         "why_split": ("on a wrong line the dot-to-walker distance is a line "
                                       "separation, not a tracking error; pooling them makes the "
                                       "tracking figure a function of line accuracy"),
                         "locked_line_pct_nine_pairings": _L6.get("all9_median"),
                         "committed_line_pct_nine_pairings": _C6.get("all9_median"),
                         "nine_pairing_figures_from": ("d6_lock_commit, matched to this render walk "
                                                       "for walk" if _d6_fresh else "STALE"),
                         "the_dot_is_never_moved_onto_the_committed_line": True,
                         "what_the_offset_is": (
                             f"the distance the walker travels during the {LAG:g} s display lag. "
                             f"A window spans {WINDOW_S:g} s, its label sits at the centre, and it "
                             f"may only be drawn once it has ended, so the dot names t minus "
                             f"{LAG:g} s. Closing it would mean assuming the walker kept going, "
                             f"which is dead reckoning and was deleted from the display path."),
                         "on_screen_within_pct_correct_line": pool(ok_w),
                         "on_screen_within_pct_wrong_line": pool(bad_w),
                         "before_within_pct": before.get("within_pct"),
                         "before_mean_m": before.get("mean_m"),
                         "backward_steps_before": old_back.get("total"),
                         "backward_steps_now": now_back,
                         "n_walks_flagged_many_switches": len(flagged),
                         "commit_delay_s": DELAY,
                         "locked_line_correct_pct":
                             100.0 * sum(w["lock_correct"] for w in all_w) / max(1, len(all_w)),
                         "max_distinct_lines_after_lock":
                             max(w["distinct_lines_after_lock"] for w in all_w),
                         "decoded_error_m": float(np.median(
                             [w["err"] for w in all_w if w.get("err") is not None]))
                             if any(w.get("err") is not None for w in all_w) else None,
                         # NOT a second display_offset. The on-screen mean is the decoder's own
                         # error PLUS the offset; calling it the offset, as this line did until
                         # 2026-09-20, understates the decoder and overstates the lag at once.
                         "on_screen_mean_m_again": pool(all_w, "mean_m"),
                         "two_accuracies_note": (
                             "decoded error compares the decoded position with the truth at the "
                             "same window centre; on-screen tracking compares the drawn dot with "
                             "the truth at the frame time and carries the whole 1.0 s causal lag; "
                             "display offset is the distance walked during that lag, which is the "
                             "difference between them. They are never added"),
                         "jumps_over_0.5m": RES["jumps"]["total"],
                         "jumps_at_the_lock": RES["jumps"]["caused_by_the_lock"],
                         "causal_bound_s": RES["causal_bound_s"],
                         "frozen_before_pct": (a3.get("horizon") or {}).get("frozen_gt_1s_pct_own_end"),
                         "frozen_after_pct": (a3.get("horizon") or {}).get("frozen_gt_1s_pct_horizon")}
    # V1 and V3, COMPUTED from the walks rather than restated from the constants. A constant
    # says what was intended; these say what every walk actually got.
    _allw = [w for _who, ws in acceptance for w in ws]
    _offs = sorted({w["lock_offset_s"] for w in _allw if w.get("lock_offset_s") is not None})
    RES["vision_rules"]["V1_latency_s"] = float(LATENCY)
    RES["vision_rules"]["V1_every_walk_same"] = bool(len(_offs) <= 1)
    RES["vision_rules"]["V3_lock_offset_s_distinct_values"] = len(_offs)
    RES["vision_rules"]["V3_lock_offset_s"] = _offs[0] if len(_offs) == 1 else _offs
    RES["vision_rules"]["n_walks"] = len(_allw)

    _ok = [w for w in _allw if w.get("lock_correct")]
    _bad = [w for w in _allw if not w.get("lock_correct")]

    def _gap(rows, key):
        v = [w[key] for w in rows if w.get(key) is not None]
        return {"n": len(v), "mean_m": (float(np.mean(v)) if v else None),
                "max_m": (float(np.max(v)) if v else None)}

    RES["start_gap"] = {
        "correct_line_by_construction": _gap(_ok, "start_gap_m"),
        "wrong_line_by_construction": _gap(_bad, "start_gap_m"),
        "correct_line_first_drawn_frame": _gap(_ok, "start_gap_first_frame_m"),
        "wrong_line_first_drawn_frame": _gap(_bad, "start_gap_first_frame_m"),
        "rule": ("THIS IS A DISPLAY RULE AND NEVER A TRACKING RESULT, per rule 4 and the "
                 "operator's decision of 2026-09-23. On a correct committed line the gap is ZERO "
                 "BY CONSTRUCTION: the press is defined as the walker at the tape entry and the "
                 "dot is placed at that entry. Quoting it as tracking accuracy would be quoting "
                 "an identity. Tracking is measured from the first decoded position onward"),
        "first_frame_note": ("the first DRAWN frame carries up to one frame of grid quantisation, "
                             "1/FPS of walking, on top of the by-construction zero"),
        "wrong_line_note": ("a wrong committed line starts at the WRONG line's entry and the gap "
                            "is the distance between two tape entries. That is shown, not hidden")}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["recordings", "folder", "acceptance",
                                           "anchor_segment", "start_gap"],
                                     {"recordings": 6})
    save(STAGE, RES)
    release(lock)

    ok = bool(RES["contract"]["SATISFIED"] and RES["folder"]["is_six_videos_and_acceptance"]
              and RES["rule"]["violations"] == 0
              and RES["rule"]["frames_checked"] > 0
              and RES["dot_visible"]["missing_after_first_legal"] == 0
              and RES["dot_visible"]["expected"] > 0
              and RES["causal_bound_s"] <= 1e-9)
    status(f"  folder now {len(after)} files, six videos and ACCEPTANCE.md = "
           f"{RES['folder']['is_six_videos_and_acceptance']}")
    status(f"  the one rule: {RES['rule']['violations']} violations over "
           f"{RES['rule']['frames_checked']} frames")
    status(f"  dot present on every frame after the first legal one: "
           f"{RES['dot_visible']['missing_after_first_legal']} missing of "
           f"{RES['dot_visible']['expected']} expected; "
           f"{RES['dot_visible']['frames_without_dot']} of {RES['dot_visible']['frames']} total "
           f"frames have no dot, which is the listening periods and the gaps between walks")
    status(f"  causal bound over every drawn frame: {RES['causal_bound_s']:+.3f} s "
           f"(must be <= 0)")
    status(f"  jumps over 0.5 m: {RES['jumps']['total']}, of which "
           f"{RES['jumps']['caused_by_the_lock']} at the lock")
    status(f"  on-screen tracking {pool(all_w):.2f}% within 0.5 m (before "
           f"{(before.get('within_pct') or 0):.2f}%), mean {pool(all_w, 'mean_m'):.2f} m "
           f"(before {(before.get('mean_m') or 0):.2f} m)")
    # f4 writes nothing to reports/: no FINDINGS_stagef3.txt overwrite, no HEADLINES.txt append.
    # Its record is runs/constrained/fh/f4_render/results.json and demo_v2/ACCEPTANCE.md.
    status(f"  contract checks all pass: {ok}")
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
