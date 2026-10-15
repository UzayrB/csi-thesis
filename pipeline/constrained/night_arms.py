"""The parameterised semi-bounded decoder every arm of the overnight batch runs through.

Written once so the arms cannot drift apart. With every option at its default this is the shipped
decoder, all_alive plus rescore_end, and that is asserted in n2 by reproducing the shipped figure
before any arm is measured.

THE OPTIONS, one per arm:
  entry          "free" shipped, "hard" arm A, "soft" arm A
  prior_flatten  0.0 shipped; arm A mixes the within-chain step model towards uniform
  cand_thresh    None shipped; arm B proposes candidate ends where null mass exceeds it
  chain_logprior None shipped; arm I adds a per-chain prior fitted on the training sessions
  family_first   False shipped; arm C decides the family before the member
  e_rescore      None shipped; arm H rescores with a differently scaled emission
  final_rule     "majority" SHIPPED; "maxlik" is arm G

ARM G EXISTS BECAUSE OF A MISTAKE, and it is a better arm for it. The first version of this module
picked the final line as the highest-total-likelihood chain, which scored 80.0 on the demonstration
pairing against the shipped 71.7. That is not a default, it is a CHANGE: the shipped rescore runs a
free Viterbi over all twelve chains at once and takes the MAJORITY of the decoded window names,
which is a different rule and can be dragged by a few windows spent on a neighbouring chain. The
default here is the shipped majority rule, verified to reproduce it, and the likelihood rule is
measured as an arm like everything else.
"""

from __future__ import annotations

import numpy as np

NEG_BIG = -1e30
MAX_WALK_S = 20.0
SAFETY_SPEED = 0.5
HYSTERESIS = 2
#: commit delays swept by A1 to A3, seconds after the start press
#: Evidence-before-commit settings the display block reports a lock for. Extended on
#: 2026-09-20 past 3 s: under a playback latency the wait is hidden from the viewer, so
#: the only cost of waiting longer is latency, and the question becomes how much accuracy
#: a longer wait buys rather than how long a viewer will tolerate staring at a centre dot.
LOCK_DELAYS_S = (0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0)
#: how far back before the first press the run-up arms may look. Every such window has ENDED by the
#: press, so this uses no sample recorded after it.
RUNUP_LOOKBACK_S = 2.0
#: the fwd/rev pairs the direction prior may reweight. The E lines have no reverse.
REVERSE_PAIRS = (("A_fwd", "A_rev"), ("B_fwd", "B_rev"),
                 ("C_fwd", "C_rev"), ("D_fwd", "D_rev"))
FAMILY_OF = {"A": "vert", "B": "horz", "C": "diagC", "D": "diagD", "E": "edge"}


def default_opts() -> dict:
    return {"entry": "free", "prior_flatten": 0.0, "cand_thresh": None,
            "chain_logprior": None, "family_first": False, "e_rescore": None,
            "final_rule": "majority"}


def flatten_chain_prior(lT, st, f: float):
    """Arm A: mix each chain's within-chain step model towards uniform by a fraction f.

    Done in PROBABILITY space and renormalised per row, so f=0 is the shipped matrix exactly and
    f=1 is a uniform choice among that chain's reachable cells. The point is to keep the geometry,
    which is the chain structure, while removing the sharpness that makes arrival time-determined.
    """
    if f <= 0:
        return lT
    lT2 = lT.copy()
    for nm in st.names:
        lo, hi = st.slice_of[nm]
        blk = np.exp(lT2[lo:hi, lo:hi])
        reach = blk > 0
        n_reach = reach.sum(axis=1, keepdims=True)
        uni = np.where(reach, 1.0 / np.maximum(n_reach, 1), 0.0)
        mix = (1.0 - f) * blk + f * uni
        s = mix.sum(axis=1, keepdims=True)
        mix = np.where(s > 0, mix / np.maximum(s, 1e-300), 0.0)
        with np.errstate(divide="ignore"):
            lT2[lo:hi, lo:hi] = np.where(mix > 0, np.log(np.maximum(mix, 1e-300)), NEG_BIG)
    return lT2


def direction_prior(e_stacked, st, t0, first_press, weight):
    """A ZERO-SUM log adjustment between each fwd/rev pair, read from the run-up windows.

    The run-up carries DIRECTION and not LINE, measured on nine cross-day pairings: 55.2 percent
    against a 50 percent chance with an interval of [52.4, 57.6] for direction, and 9.2 against 8.3
    for the line. So this is allowed to move the split between the two directions of one tape and
    nothing else. Centring the pair's log posterior makes that exact: the pair's total is unchanged
    and no line becomes more or less likely relative to any other line.

    Only windows whose END is at or before the first press are used, so every sample was recorded
    before the press and nothing here looks into the future.
    """
    from pipeline.constrained.rebuild_common import WINDOW_S
    out = {}
    end_w = np.asarray(t0, float) + WINDOW_S
    pre = np.flatnonzero((end_w <= first_press + 1e-9)
                         & (end_w >= first_press - RUNUP_LOOKBACK_S - 1e-9))
    pre = pre[pre < len(e_stacked)]
    if not len(pre):
        return out
    E = np.asarray(e_stacked)
    for nm_a, nm_b in REVERSE_PAIRS:
        if nm_a not in st.slice_of or nm_b not in st.slice_of:
            continue
        sc = []
        for nm_x in (nm_a, nm_b):
            aa, bb = st.slice_of[nm_x]
            v = E[np.ix_(pre, np.arange(aa, bb))]
            m_ = np.max(v, axis=1)
            m_ = np.where(np.isfinite(m_), m_, 0.0)
            sc.append(float(np.sum(m_ + np.log(np.sum(np.exp(v - m_[:, None]), axis=1) + 1e-300))))
        mx = max(sc)
        lp = [x - mx - float(np.log(np.exp(sc[0] - mx) + np.exp(sc[1] - mx))) for x in sc]
        mid = 0.5 * (lp[0] + lp[1])
        out[nm_a] = weight * (lp[0] - mid)
        out[nm_b] = weight * (lp[1] - mid)
    return out


def entry_start(kind, e_stacked, st, sp, lo, on_chain, first_state):
    """The initial distribution over states at the start press."""
    start = np.full(sp.N, NEG_BIG)
    if kind == "hard":
        start[first_state] = 0.0
    elif kind == "soft":
        # the first window's own position posterior, projected onto the chains. Where the walker
        # starts is READ from the emissions at the press rather than assumed, which is the whole
        # difference from hard pinning and the reason it need not behave like a clock.
        v = np.full(sp.N, NEG_BIG)
        v[:st.n_states] = e_stacked[lo, :st.n_states]
        m = float(np.max(v[:st.n_states]))
        if np.isfinite(m):
            v[:st.n_states] -= m
        start = v
    else:
        start[on_chain] = 0.0
    return start


def chain_totals(e_chain, st, seq_range, lT_chains, chain_logprior=None):
    """Total log-likelihood of every chain over one window range, by Viterbi within the chain."""
    from pipeline.constrained.decoder import viterbi
    out = {}
    for nm in st.names:
        a, b = st.slice_of[nm]
        sub_e = e_chain[seq_range, a:b]
        sub_T = lT_chains[a:b, a:b]
        s = viterbi(sub_e, sub_T)
        tot = float(sub_e[np.arange(len(s)), s].sum())
        if chain_logprior:
            tot += float(chain_logprior.get(nm, 0.0))
        out[nm] = tot
    return out


def pick_line(totals, st, family_first=False):
    """The final line from per-chain totals, flat or family-first (arm C)."""
    if not totals:
        return ""
    if not family_first:
        return max(totals, key=totals.get)
    fam = {}
    for nm, v in totals.items():
        f = FAMILY_OF.get(nm.split("_")[0], "other")
        fam.setdefault(f, []).append(v)
    # sum likelihood over each family's members, in log space
    def lse(xs):
        m = max(xs)
        return m + float(np.log(sum(np.exp(x - m) for x in xs)))
    best_fam = max(fam, key=lambda f: lse(fam[f]))
    members = {nm: v for nm, v in totals.items()
               if FAMILY_OF.get(nm.split("_")[0], "other") == best_fam}
    return max(members, key=members.get)


def viterbi_last_scores(log_emis, log_T, log_start, st):
    """{line: the best Viterbi score over that line's states at the LAST window}. The same recursion
    as `decoder.viterbi`, which reads its path from the argmax of this last row."""
    dp = np.asarray(log_emis[0], float) + np.asarray(log_start, float)
    for t in range(1, len(log_emis)):
        dp = (dp[:, None] + log_T).max(0) + np.asarray(log_emis[t], float)
    return {nm: float(dp[st.slice_of[nm][0]:st.slice_of[nm][1]].max()) for nm in st.names}


def night_track(e_path, rec, st, cfg, transit, ne, ge, stride_s, opts=None, alt_e=None, want_display=False, display_lags_w=(0, 1, 2), display_to_horizon=False,
                display_alt_e=None, display_alt_entry_m=None, display_alt_flatten=None,
                display_lead_in_w=0, display_switch_paths=False, display_lock_scores=False):
    """The shipped semi-bounded decoder with every arm's option available. Defaults are shipped.

    ``display_switch_paths`` (batch 23e, mid-walk switching as a display decision): for each display
    ARM, the same restricted along-line Viterbi on EVERY line, not only the locked one, so a switch
    can hand the dot to the new line's decoded path. Same emissions, prior, entry, window range and
    evidence horizon as the locked line's; nothing else is touched, and False is bit-identical.

    ``display_lock_scores`` (batch 23g, the scorer-lock arm): the per-line DISPLAY-LOCK SCORE at the
    lock step, the best Viterbi score over each line's on-chain states at the lock's last window, from
    the SAME decode the lock line is read from. Its argmax is the lock line whenever the lock state is
    on a chain. False is bit-identical.

    ``display_alt_e`` is a DISPLAY-ONLY hook: ``{name: emission}``, each run through the same
    restricted along-line Viterbi, on the same lock step and the same locked line, with the same
    entry prior. Nothing in it can reach the committed answer, the lock or the line, because it is
    read at one call site and that call site is after all three are fixed. It exists so two display
    arms can be compared on identical decisions rather than on two separate decodes that might
    differ for some other reason.

    ``display_alt_entry_m`` widens A1's entry window for a named display arm alone,
    ``{name: metres}``. A1's 1.0 m window is expressed in CENTRE-label coordinates; a head labelled
    at the window end names a position about 1.3 m further on, so the unwidened window excludes its
    own answer by construction. This exists so that confound can be measured rather than left to
    decide an arm. It touches nothing but that arm's drawn path.
    """
    from pipeline.constrained.decoder import decoded_paths, transition_matrix, viterbi
    from pipeline.constrained.decoder2 import Space, stack2, transition_matrix2
    from pipeline.constrained.rebuild_common import WINDOW_S
    from pipeline.constrained.sb2_structural import press_ends, running_argmax_display

    o = dict(default_opts())
    o.setdefault("causal_exit", True)      # the SHIPPED exit rule since 2026-09-20
    o.setdefault("want_batch_end", False)  # the retired one, for audits only
    o.update(opts or {})
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit)
    lT = flatten_chain_prior(lT, st, float(o["prior_flatten"]))
    lT_chains = transition_matrix(st, "tight", with_null=False)

    def stacked(src):
        ne.calibrate(src)
        return stack2(src, ge, ne, sp)

    e_stacked = stacked(e_path)
    alt_stacked = (stacked(np.resize(alt_e, (len(e_path), alt_e.shape[1])))
                   if alt_e is not None else None)
    e_res = o["e_rescore"] if o["e_rescore"] is not None else e_path

    all_names = np.asarray(decoded_paths(np.arange(sp.N), st)).astype(str)
    on_chain = all_names != ""
    first_state = np.zeros(sp.N, bool)
    for nm in st.names:
        first_state[st.slice_of[nm][0]] = True
    start = entry_start(o["entry"], e_stacked, st, sp, 0, on_chain, first_state)

    s_of = np.asarray(st.s_of, float)
    L = {nm: float(s_of[st.slice_of[nm][1] - 1]) for nm in st.names}
    horizon_w = int(round(MAX_WALK_S / stride_s))
    timeout_w = int(np.ceil(max(L.values()) / SAFETY_SPEED / stride_s))
    n = len(rec)
    t0 = np.asarray(rec.t0, float)
    centres = t0 + WINDOW_S / 2.0
    xy_true = np.asarray(rec.xy, float)
    presses = press_ends(rec.session, rec.stem)
    # THE FIRST anchor press, for the run-up arms. press_ends gives the LAST one, which is what the
    # end is scored against; these are different quantities and must not be confused.
    first_presses_map = {}
    if o.get("dir_prior_w") or o.get("runup_states"):
        from pipeline.constrained.p1_runup import first_presses as _fp
        first_presses_map = _fp(rec.session, rec.stem)
    out = []

    for pid, nm, p_lo, p_hi in rec.pass_spans():
        first_press = first_presses_map.get(int(pid))
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if len(w) < 2:
            continue
        lo, hi_true = int(w[0]), int(w[-1])
        hi_lim = int(min(n - 1, len(e_stacked) - 1, lo + horizon_w))
        if hi_lim <= lo:
            continue

        # ARM B: START THE DECODE AT THE EARLIEST PRE-PRESS WINDOW, so the run-up is integrated as
        # part of the walk rather than discarded. lo_dec is used ONLY for the entry, the own-end
        # search and the rescore interval; lo itself still marks the labelled walk and is what the
        # display, the error and the exit timing are measured against, because the run-up windows
        # have no labelled position and would otherwise poison them.
        #
        # The decoder is NOT forced to reach the chain's start at the press. It enters the extended
        # chain wherever the emissions put it and the transition model carries it forward; pinning
        # it to the run-up's first state at a fixed time would be the clock that was refused.
        lo_dec = lo
        if o.get("runup_states") and first_press is not None:
            end_w = t0 + WINDOW_S
            pre = np.flatnonzero((end_w <= first_press + 1e-9)
                                 & (end_w >= first_press - RUNUP_LOOKBACK_S - 1e-9))
            if len(pre):
                lo_dec = int(max(0, min(lo, int(pre[0]))))
        st_lo = entry_start(o["entry"], e_stacked, st, sp, lo_dec, on_chain, first_state)

        # ARM A: A SOFT DIRECTION PRIOR FROM THE RUN-UP, and ONLY a direction prior.
        # The run-up carries direction (55.2 percent against 50, interval [52.4, 57.6]) and NOT
        # line (9.2 against 8.3 chance), so this may reweight the two directions of the SAME tape
        # and nothing else. The adjustment is ZERO-SUM within each fwd/rev pair: the pair's total
        # entry score is unchanged and only its split moves, so no line is made more or less
        # likely than any other. The four E lines have no reverse and are never touched.
        # A1: ENTRY RESTRICTED TO THE FIRST entry_window_m OF EACH CHAIN, not pinned to a cell.
        # Within that window the soft entry's own emission-derived posterior decides and progress
        # afterwards is driven by emissions alone. Pinned entry fixed position at a known state at
        # a known time and was refused as a clock; a 1.0 m window of five states that the
        # emissions choose within is a different object, and the end-time substitution reported
        # beside it is the check on that claim.
        st_lo_raw = np.asarray(st_lo, float).copy()
        if o.get("entry_window_m"):
            lim = float(o["entry_window_m"])
            st_lo = np.asarray(st_lo, float).copy()
            s_arr = np.asarray(st.s_of, float)
            for nm_x in st.names:
                aa, bb = st.slice_of[nm_x]
                far = aa + np.flatnonzero((s_arr[aa:bb] - s_arr[aa]) > lim + 1e-9)
                if len(far):
                    st_lo[far] = NEG_BIG

        # A2: A START-CONSISTENCY TERM ON THE CHAIN TOTALS, fed by the A3 classifier. It scores how
        # well each line's START REGION agrees with where the classifier says the walker started.
        # It is NOT a direction term: D4 measured direction from the start at or below chance.
        start_adj = None
        if o.get("start_term") is not None:
            start_adj = (o["start_term"] or {}).get(f"{rec.session}|{rec.stem}|{int(pid)}")

        dir_adj = None
        if o.get("dir_prior_w") and first_press is not None:
            dir_adj = direction_prior(e_stacked, st, t0, first_press, float(o["dir_prior_w"]))
            # it also biases the OWN-END decision and the display, which read st_lo
            st_lo = np.asarray(st_lo, float).copy()
            for nm_x, adj in dir_adj.items():
                aa, bb = st.slice_of[nm_x]
                st_lo[aa:bb] += adj

        def own_end(src_stacked):
            s = viterbi(src_stacked[lo_dec:hi_lim + 1], lT, log_start=st_lo)
            names = np.asarray(decoded_paths(s, st)).astype(str)
            ek = None
            for k in range(1, len(s)):
                if names[k] == "":
                    ek = k
                    break
            fired = False
            if ek is None and timeout_w < len(s):
                ek, fired = timeout_w, True
            return s, names, ek, fired

        def causal_end(src_stacked):
            """THE LIVE EXIT. Declare the walk over at the first step whose decode, OVER THE
            WINDOWS AVAILABLE THEN, ends in the null state.

            One forward pass, not one Viterbi per step. A Viterbi backtrace's LAST state is the
            argmax of the max-product forward score at that step, so running the recursion once
            and watching its argmax gives exactly the answer that re-decoding at every step would,
            at a fortieth of the cost.

            This replaces a search that ran one Viterbi over lo_dec to lo_dec + MAX_WALK_S and
            took the first null in it, whose evidence bound was +20.5 s: the exit index could
            depend on radio recorded long after the walk. It was measured inert on 2026-09-20,
            paired delta -0.09 points with interval [-1.57, 1.30], and it is gone rather than
            kept on the strength of being harmless.
            """
            d = np.asarray(src_stacked[lo_dec], float) + np.asarray(st_lo, float)
            for k in range(1, hi_lim - lo_dec + 1):
                d = np.asarray(src_stacked[lo_dec + k], float) + (d[:, None] + lT).max(axis=0)
                if int(np.nanargmax(np.where(np.isfinite(d), d, -np.inf))) >= st.n_states:
                    return lo_dec + k, False
            return hi_lim, True

        if o.get("causal_exit", True):
            end_i, timeout_fired = causal_end(e_stacked)
            s = viterbi(e_stacked[lo_dec:end_i + 1], lT, log_start=st_lo)
            names = np.asarray(decoded_paths(s, st)).astype(str)
            exit_k = end_i - lo_dec
        else:
            s, names, exit_k, timeout_fired = own_end(e_stacked)
            end_i = lo_dec + (exit_k if exit_k is not None else len(s) - 1)

        # THE CAUSAL OWN END, for the causality audit of 2026-09-20. own_end() runs ONE Viterbi
        # over lo_dec to hi_lim and takes the first null in it, so the exit index depends on
        # windows recorded long after the walk ended. A live semi-bounded system cannot do that:
        # it must declare the end at the first step whose backtrace, over the windows it HAS,
        # ends in the null state. Computed here beside the batch answer so the two can be
        # compared rather than assumed equal. It does not feed the committed line.
        # THE RETIRED BATCH EXIT, computed only when an audit asks for it, so the two rules can
        # still be compared after the causal one became the shipped default.
        alt_end_i = None
        if o.get("want_batch_end"):
            s_b, _nb, ek_b, _fb = own_end(e_stacked)
            alt_end_i = lo_dec + (ek_b if ek_b is not None else len(s_b) - 1)

        subs_end_changed = None
        if alt_stacked is not None:
            # the SAME exit rule the decoder ships, or the substitution tests a thing that is no
            # longer in the live path
            if o.get("causal_exit", True):
                e2_ = causal_end(alt_stacked)[0]
            else:
                s2, _n2, ek2, _f2 = own_end(alt_stacked)
                e2_ = lo_dec + (ek2 if ek2 is not None else len(s2) - 1)
            subs_end_changed = bool(e2_ != end_i)

        # ---- ARM B: candidate ends where the null carries real mass, scored jointly with the chain
        cand = None
        if o["cand_thresh"] is not None:
            T = np.exp(lT)
            a = e_stacked[lo] + st_lo
            mass = []
            for t in range(lo, hi_lim + 1):
                if t > lo:
                    m = float(a.max())
                    if not np.isfinite(m):
                        break
                    a = np.log(np.maximum(np.exp(a - m) @ T, 1e-300)) + m + e_stacked[t]
                mx = float(a.max())
                p = np.exp(a - mx)
                p = p / max(p.sum(), 1e-300)
                mass.append(float(p[st.n_states:].sum()))
            ends = [lo + i for i, mv in enumerate(mass)
                    if mv >= float(o["cand_thresh"]) and lo + i > lo]
            ends = ends[:8] or [end_i]
            best, best_v = None, -np.inf
            for c in ends:
                tot = chain_totals(e_res, st, slice(lo, c + 1), lT_chains, o["chain_logprior"])
                if not tot:
                    continue
                nm_c = pick_line(tot, st, o["family_first"])   # candidates always score by likelihood
                v = tot[nm_c]
                # null accounts for every window after the exit, so candidates of different
                # lengths are compared over the SAME windows and no normalisation is needed
                if c < hi_lim:
                    v += float(e_stacked[c + 1:hi_lim + 1, st.n_states:].max(axis=1).sum())
                if v > best_v:
                    best_v, best = v, (c, nm_c)
            if best is not None:
                end_i, cand = best[0], {"n_candidates": len(ends), "chosen_end": best[0]}

        # ---- the provisional display a viewer sees
        sl = slice(lo_dec, end_i + 1)
        disp = running_argmax_display(e_stacked, lT, st_lo, st, sl)
        provisional, revisions = disp["final_displayed"], disp["revisions"]

        # THE DISPLAY THE RENDERER DRAWS, at hysteresis one, which is the earliest the decoder
        # allows a line to be shown. It is computed SEPARATELY and never feeds the committed
        # answer: for the shipped arm `final` comes from the chain totals at the end, so the two
        # cannot interact and no committed figure moves when the display is made quicker.
        disp1 = running_argmax_display(e_stacked, lT, st_lo, st, sl, hysteresis=1)

        # THE DRAWN PATH. A fixed-lag Viterbi backtrace read at each display step, one path per
        # display lag, built from THIS decode's own emissions and transition matrix so the render
        # cannot drift from the decoder. The per-window argmax above is kept only as the record of
        # what the old display did.
        disp_paths, disp_held, entry_k, entry_nm = None, None, None, ""
        if want_display:
            from pipeline.constrained.render_display import (entry_position, fixed_lag_path,
                                                             locked_chain_path)
            disp_paths, disp_held = {}, {}
            # A4: THE DISPLAY KEEPS DECODING PAST THE DECODER'S OWN END, to the horizon. It uses
            # only windows up to the current frame plus the lag, so it is told nothing about when
            # the walk ends; it simply keeps estimating as evidence arrives. The COMMITTED answer
            # still comes from the own-end decision at end_i and is untouched. Without this the dot
            # freezes at own-end and sits still while the walker carries on, which was 9 of 20
            # walks for one participant, the worst frozen for 4.2 s of a 5.7 s walk.
            disp_hi = hi_lim if display_to_horizon else end_i
            # THE DISPLAY MAY START BEFORE THE FIRST LABELLED WALK WINDOW. Those windows are real
            # radio recorded during the run-up, and the scene needs one of them so that it can
            # begin at the walker's own first press rather than half a second later, by which
            # time they are already 0.6 m along the line while the dot is still entering at 0.26.
            # It is DISPLAY ONLY: the committed line, the lock and every decision are unchanged,
            # and the extra window is causally legal because the display runs behind by more than
            # the half second it reaches back.
            lo_disp = max(0, lo - int(display_lead_in_w))
            # THE EVIDENCE HORIZON IS NOT THE DRAW OFFSET, and conflating them leaked a second of
            # the future into every drawn dot until 2026-09-20.
            #
            # `lw` is the DRAW OFFSET: at frame x the display shows the window lw steps behind
            # floor((x - t_start)/stride). A window spans WINDOW_S and may only be drawn once it
            # has ENDED, so the latest legal window at frame x is lw0 = (WINDOW_S/2)/stride steps
            # behind that same quantity. The evidence legally available when step i is drawn
            # therefore reaches lw - lw0 windows PAST step i, and no further.
            #
            # fixed_lag_path and locked_chain_path were being handed `lw` itself as that horizon,
            # so each step was decoded with lw windows of future radio instead of lw - lw0. At the
            # shipped lw = 2 that is exactly +1.000 s, measured: the drawn-window bound read
            # -0.000 s while the radio that produced the dot ended a second after the frame. A
            # negative horizon means the configuration cannot be drawn causally at all, which is
            # what the old 0 s lag was doing and why LAG is pinned at WINDOW_S/2.
            lw0 = int(round((WINDOW_S / 2.0) / stride_s))
            for lw in display_lags_w:
                ev_w = int(lw) - lw0
                if ev_w < 0:
                    raise AssertionError(
                        f"display lag {lw} windows is shorter than the {lw0} windows a "
                        f"{WINDOW_S:g} s window needs to finish recording; it cannot be drawn "
                        f"causally")
                pth, held_ = fixed_lag_path(e_stacked, lT, st_lo, st, lo_disp, disp_hi, ev_w)
                disp_paths[str(int(lw))] = pth
                disp_held[str(int(lw))] = int(held_)
            entry_k, entry_nm = entry_position(e_stacked, st_lo, st, lo)
            # A1 to A3: everything the renderer needs to PARK, WATCH and LOCK. The free path says
            # which line leads at the lock step; the locked path is a Viterbi restricted to that
            # chain, so after the lock the drawn position is still decoded and still on that line.
            disp_locked = {}
            for lw in display_lags_w:
                free = disp_paths[str(int(lw))]
                for delay in LOCK_DELAYS_S:
                    li = int(round(delay / stride_s)) - int(lw)
                    li = max(0, min(li, len(free) - 1))
                    # WHY this line was locked, recorded so the fallback cannot hide inside the
                    # answer. `st.names[0]` is A_fwd, so a free path that is OFF-CHAIN at the lock
                    # step and has no entry line is drawn as A_fwd BY NAME ORDER, not by evidence.
                    # Purely additive: nm_lock is the same expression it always was.
                    nm_free = free[li]["line"]
                    nm_lock = nm_free or entry_nm or st.names[0]
                    lock_scores = None
                    if display_lock_scores:
                        _end = min(disp_hi, lo_disp + li + (int(lw) - lw0))
                        lock_scores = viterbi_last_scores(e_stacked[lo_disp:_end + 1], lT, st_lo, st)
                    node = {
                        "lock_step": li, "lock_line": nm_lock,
                        "lock_line_source": ("path" if nm_free else
                                             ("entry" if entry_nm else "FIRST_NAME_FALLBACK")),
                        "lock_correct": bool(nm_lock == nm),
                        "path": locked_chain_path(e_res, lT_chains, st, lo_disp, disp_hi,
                                                  int(lw) - lw0, nm_lock, log_start=st_lo),
                        "lo_disp": int(lo_disp),
                        "evidence_horizon_w": int(lw) - lw0}
                    if lock_scores is not None:
                        node["lock_scores"] = lock_scores
                        node["lock_scores_last_window"] = int(_end)
                    if display_alt_e:
                        # the DISPLAY ARMS. Same lock step, same locked line, same entry prior,
                        # same window range: only the emissions the along-line Viterbi reads
                        # differ, which is the one thing an arm is allowed to change.
                        node["paths_alt"] = {}
                        for k, v in display_alt_e.items():
                            ls_k = st_lo
                            extra = (display_alt_entry_m or {}).get(k)
                            if extra is not None and o.get("entry_window_m"):
                                ls_k = st_lo_raw.copy()
                                lim_k = float(o["entry_window_m"]) + float(extra)
                                s_arr_k = np.asarray(st.s_of, float)
                                for nm_y in st.names:
                                    aa_, bb_ = st.slice_of[nm_y]
                                    far_ = aa_ + np.flatnonzero(
                                        (s_arr_k[aa_:bb_] - s_arr_k[aa_]) > lim_k + 1e-9)
                                    if len(far_):
                                        ls_k[far_] = NEG_BIG
                            # R3: the DISPLAY's own motion model may be weakened per arm,
                            # without touching the line decision. f = 0 is the shipped step
                            # model, f = 1 is uniform over the cells the chain can still reach.
                            lTk = lT_chains
                            fk = (display_alt_flatten or {}).get(k)
                            if fk:
                                lTk = flatten_chain_prior(lT_chains, st, float(fk))
                            node["paths_alt"][k] = locked_chain_path(
                                np.resize(v, (len(e_path), np.shape(v)[1])), lTk, st, lo_disp,
                                disp_hi, int(lw) - lw0, nm_lock, log_start=ls_k)
                            if display_switch_paths:
                                node.setdefault("switch_paths", {})[k] = {
                                    nm_z: (node["paths_alt"][k] if nm_z == nm_lock else
                                           locked_chain_path(
                                               np.resize(v, (len(e_path), np.shape(v)[1])), lTk,
                                               st, lo_disp, disp_hi, int(lw) - lw0, nm_z,
                                               log_start=ls_k))
                                    for nm_z in st.names}
                    disp_locked[f"{int(lw)}|{delay}"] = node

        def _commit(d):
            out_ = {}
            for dt in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
                k = int(round(dt / stride_s))
                out_[str(dt)] = bool(k < len(d["displayed"]) and d["displayed"][k] == nm)
            return out_

        commit_s = _commit(disp)
        commit_s_h1 = _commit(disp1)

        # ---- the final rescore over the committed interval
        if end_i > lo:
            s_fin = viterbi(e_res[sl], lT_chains)
            if o["final_rule"] == "maxlik" or o["family_first"] or o["chain_logprior"]:
                tot = chain_totals(e_res, st, sl, lT_chains, o["chain_logprior"])
                # THE LINE IS DECIDED HERE, not at entry. An entry prior alone is inert on the
                # committed answer for this arm, which is why the direction prior is applied to the
                # chain totals as well. It is still zero-sum within each fwd/rev pair, so it can
                # only move the split between two directions of one tape.
                if dir_adj:
                    tot = {k: v + dir_adj.get(k, 0.0) for k, v in tot.items()}
                if start_adj:
                    tot = {k: v + start_adj.get(k, 0.0) for k, v in tot.items()}
                final = pick_line(tot, st, o["family_first"])
            else:
                # THE SHIPPED RULE: majority of the decoded window names on a free Viterbi over
                # all twelve chains at once.
                n_fin = np.asarray(decoded_paths(s_fin, st)).astype(str)
                on_f = n_fin[n_fin != ""]
                if len(on_f):
                    v, c = np.unique(on_f, return_counts=True)
                    final = str(v[c.argmax()])
                else:
                    final = ""
        else:
            final, s_fin = provisional, s[:1]

        err = None
        if final == nm and len(s_fin):
            idx = np.arange(lo_dec, lo_dec + len(s_fin))
            keep = (idx <= hi_true) & (np.asarray(s_fin) < st.n_states)
            if keep.any():
                xy_hat = np.asarray(st.xy)[np.asarray(s_fin)[keep]]
                err = float(np.median(np.linalg.norm(xy_hat - xy_true[idx[keep]], axis=1)))

        subs_line_changed = None
        if alt_stacked is not None and end_i > lo:
            alt_res = np.resize(alt_e, (len(e_path), alt_e.shape[1]))
            if o["final_rule"] == "maxlik" or o["family_first"] or o["chain_logprior"]:
                alt_tot = chain_totals(alt_res, st, sl, lT_chains, o["chain_logprior"])
                if start_adj:
                    alt_tot = {k: v + start_adj.get(k, 0.0) for k, v in alt_tot.items()}
                if o.get("dir_prior_w") and first_press is not None:
                    # the substituted decode gets the SUBSTITUTED participant's run-up prior, so
                    # the test asks what the other person's radio says and not what this one's did
                    a_adj = direction_prior(alt_stacked, st, t0, first_press,
                                            float(o["dir_prior_w"]))
                    alt_tot = {k: v + a_adj.get(k, 0.0) for k, v in alt_tot.items()}
                alt_final = pick_line(alt_tot, st, o["family_first"])
            else:
                s_a = viterbi(alt_res[sl], lT_chains)
                n_a = np.asarray(decoded_paths(s_a, st)).astype(str)
                on_a = n_a[n_a != ""]
                if len(on_a):
                    v, c = np.unique(on_a, return_counts=True)
                    alt_final = str(v[c.argmax()])
                else:
                    alt_final = ""
            subs_line_changed = bool(alt_final != final)

        causal_final = None
        if alt_end_i is not None and alt_end_i > lo:
            # THE SAME RULE, over the causal interval. If this disagrees with `final`, the
            # semi-bounded figure depends on the look-ahead and the honest number is this one.
            c_tot = chain_totals(e_res, st, slice(lo_dec, alt_end_i + 1), lT_chains,
                                 o["chain_logprior"])
            if c_tot:
                if dir_adj:
                    c_tot = {k: v + dir_adj.get(k, 0.0) for k, v in c_tot.items()}
                if start_adj:
                    c_tot = {k: v + start_adj.get(k, 0.0) for k, v in c_tot.items()}
                causal_final = pick_line(c_tot, st, o["family_first"])

        end_press = presses.get(int(pid))
        if end_press is None:
            raise RuntimeError(f"pass {pid} of {rec.stem} has no anchor press")
        own_t = float(centres[end_i])
        imposs = int(sum(1 for i in range(1, len(s_fin))
                         if s_fin[i] < st.n_states and s_fin[i - 1] < st.n_states
                         and lT_chains[int(s_fin[i - 1]), int(s_fin[i])] <= -1e29))
        out.append({"key": f"{rec.session}|{rec.stem}|{int(pid)}",
                    "pass_id": int(pid), "true_line": nm,
                    "final_line": final, "provisional_line": provisional,
                    "found_final": final == nm, "found_provisional": provisional == nm,
                    "err_m": err,
                    "exit_dt_press_s": own_t - end_press,
                    "exit_dt_passend_s": own_t - (float(t0[p_hi]) + WINDOW_S),
                    "exit_dt_walkend_s": own_t - float(centres[hi_true]),
                    "never_ended": bool(abs(own_t - end_press) > 5.0),
                    "revisions": int(revisions), "timeout_fired": bool(timeout_fired),
                    "revisions_h1": int(disp1["revisions"]),
                    "provisional_line_h1": disp1["final_displayed"],
                    "found_provisional_h1": disp1["final_displayed"] == nm,
                    "commit_s": commit_s, "commit_s_h1": commit_s_h1, "impossible": imposs,
                    # the per-window display, attached only when a caller asks, because it is the
                    # only field in this row that grows with the length of the walk
                    "display_names": (list(disp1["displayed"]) if want_display else None),
                    "display_state": (list(disp1["state_idx"]) if want_display else None),
                    "display_paths": disp_paths, "display_offchain_held": disp_held,
                    "display_locked": (disp_locked if want_display else None),
                    "entry_state": (int(entry_k) if entry_k is not None else None),
                    "entry_line": entry_nm,
                    "subs_end_changed": subs_end_changed,
                    "subs_line_changed": subs_line_changed,
                    "candidates": cand,
                    # the window indices a renderer needs to turn rows into frames. track2 carried
                    # these and night_track did not, which failed f3_render on every recording.
                    "lo": int(lo), "own_end_i": int(end_i), "hi_true": int(hi_true),
                    # the causality audit needs to know how far the EXIT SEARCH read, which is
                    # not the same as how far the scoring interval reached
                    "lo_dec": int(lo_dec), "exit_search_hi": int(hi_lim),
                    "exit_rule": ("causal" if o.get("causal_exit", True) else "batch"),
                    "batch_own_end_i": (int(alt_end_i) if alt_end_i is not None else None),
                    "batch_final_line": causal_final,
                    "batch_found_final": (None if causal_final is None
                                          else bool(causal_final == nm))})
    return out
