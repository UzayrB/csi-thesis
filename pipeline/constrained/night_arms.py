# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The parameterised semi-bounded decoder every arm of the overnight batch runs through.

from __future__ import annotations

import numpy as np

NEG_BIG = -1e30
MAX_WALK_S = 20.0
SAFETY_SPEED = 0.5
HYSTERESIS = 2
LOCK_DELAYS_S = (0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0)
RUNUP_LOOKBACK_S = 2.0
REVERSE_PAIRS = (("A_fwd", "A_rev"), ("B_fwd", "B_rev"),
                 ("C_fwd", "C_rev"), ("D_fwd", "D_rev"))
FAMILY_OF = {"A": "vert", "B": "horz", "C": "diagC", "D": "diagD", "E": "edge"}


# Function default opts.
def default_opts() -> dict:
    return {"entry": "free", "prior_flatten": 0.0, "cand_thresh": None,
            "chain_logprior": None, "family_first": False, "e_rescore": None,
            "final_rule": "majority"}


# Arm A: mix each chain's within-chain step model towards uniform by a fraction f.
def flatten_chain_prior(lT, st, f: float):
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


# A ZERO-SUM log adjustment between each fwd/rev pair, read from the run-up windows.
def direction_prior(e_stacked, st, t0, first_press, weight):
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


# The initial distribution over states at the start press.
def entry_start(kind, e_stacked, st, sp, lo, on_chain, first_state):
    start = np.full(sp.N, NEG_BIG)
    if kind == "hard":
        start[first_state] = 0.0
    elif kind == "soft":
        v = np.full(sp.N, NEG_BIG)
        v[:st.n_states] = e_stacked[lo, :st.n_states]
        m = float(np.max(v[:st.n_states]))
        if np.isfinite(m):
            v[:st.n_states] -= m
        start = v
    else:
        start[on_chain] = 0.0
    return start


# Total log-likelihood of every chain over one window range, by Viterbi within the chain.
def chain_totals(e_chain, st, seq_range, lT_chains, chain_logprior=None):
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


# The final line from per-chain totals, flat or family-first (arm C).
def pick_line(totals, st, family_first=False):
    if not totals:
        return ""
    if not family_first:
        return max(totals, key=totals.get)
    fam = {}
    for nm, v in totals.items():
        f = FAMILY_OF.get(nm.split("_")[0], "other")
        fam.setdefault(f, []).append(v)
    # Function lse.
    def lse(xs):
        m = max(xs)
        return m + float(np.log(sum(np.exp(x - m) for x in xs)))
    best_fam = max(fam, key=lambda f: lse(fam[f]))
    members = {nm: v for nm, v in totals.items()
               if FAMILY_OF.get(nm.split("_")[0], "other") == best_fam}
    return max(members, key=members.get)


# {line: the best Viterbi score over that line's states at the LAST window}.
def viterbi_last_scores(log_emis, log_T, log_start, st):
    dp = np.asarray(log_emis[0], float) + np.asarray(log_start, float)
    for t in range(1, len(log_emis)):
        dp = (dp[:, None] + log_T).max(0) + np.asarray(log_emis[t], float)
    return {nm: float(dp[st.slice_of[nm][0]:st.slice_of[nm][1]].max()) for nm in st.names}


# The shipped semi-bounded decoder with every arm's option available.
def night_track(e_path, rec, st, cfg, transit, ne, ge, stride_s, opts=None, alt_e=None, want_display=False, display_lags_w=(0, 1, 2), display_to_horizon=False,
                display_alt_e=None, display_alt_entry_m=None, display_alt_flatten=None,
                display_lead_in_w=0, display_switch_paths=False, display_lock_scores=False):
    from pipeline.constrained.decoder import decoded_paths, transition_matrix, viterbi
    from pipeline.constrained.decoder2 import Space, stack2, transition_matrix2
    from pipeline.constrained.rebuild_common import WINDOW_S
    from pipeline.constrained.sb2_structural import press_ends, running_argmax_display

    o = dict(default_opts())
    o.setdefault("causal_exit", True)
    o.setdefault("want_batch_end", False)
    o.update(opts or {})
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit)
    lT = flatten_chain_prior(lT, st, float(o["prior_flatten"]))
    lT_chains = transition_matrix(st, "tight", with_null=False)

    # Function stacked.
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

        lo_dec = lo
        if o.get("runup_states") and first_press is not None:
            end_w = t0 + WINDOW_S
            pre = np.flatnonzero((end_w <= first_press + 1e-9)
                                 & (end_w >= first_press - RUNUP_LOOKBACK_S - 1e-9))
            if len(pre):
                lo_dec = int(max(0, min(lo, int(pre[0]))))
        st_lo = entry_start(o["entry"], e_stacked, st, sp, lo_dec, on_chain, first_state)

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

        start_adj = None
        if o.get("start_term") is not None:
            start_adj = (o["start_term"] or {}).get(f"{rec.session}|{rec.stem}|{int(pid)}")

        dir_adj = None
        if o.get("dir_prior_w") and first_press is not None:
            dir_adj = direction_prior(e_stacked, st, t0, first_press, float(o["dir_prior_w"]))
            st_lo = np.asarray(st_lo, float).copy()
            for nm_x, adj in dir_adj.items():
                aa, bb = st.slice_of[nm_x]
                st_lo[aa:bb] += adj

        # Function own end.
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

        # THE LIVE EXIT.
        def causal_end(src_stacked):
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

        alt_end_i = None
        if o.get("want_batch_end"):
            s_b, _nb, ek_b, _fb = own_end(e_stacked)
            alt_end_i = lo_dec + (ek_b if ek_b is not None else len(s_b) - 1)

        subs_end_changed = None
        if alt_stacked is not None:
            if o.get("causal_exit", True):
                e2_ = causal_end(alt_stacked)[0]
            else:
                s2, _n2, ek2, _f2 = own_end(alt_stacked)
                e2_ = lo_dec + (ek2 if ek2 is not None else len(s2) - 1)
            subs_end_changed = bool(e2_ != end_i)

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
                nm_c = pick_line(tot, st, o["family_first"])
                v = tot[nm_c]
                if c < hi_lim:
                    v += float(e_stacked[c + 1:hi_lim + 1, st.n_states:].max(axis=1).sum())
                if v > best_v:
                    best_v, best = v, (c, nm_c)
            if best is not None:
                end_i, cand = best[0], {"n_candidates": len(ends), "chosen_end": best[0]}

        sl = slice(lo_dec, end_i + 1)
        disp = running_argmax_display(e_stacked, lT, st_lo, st, sl)
        provisional, revisions = disp["final_displayed"], disp["revisions"]

        disp1 = running_argmax_display(e_stacked, lT, st_lo, st, sl, hysteresis=1)

        disp_paths, disp_held, entry_k, entry_nm = None, None, None, ""
        if want_display:
            from pipeline.constrained.render_display import (entry_position, fixed_lag_path,
                                                             locked_chain_path)
            disp_paths, disp_held = {}, {}
            disp_hi = hi_lim if display_to_horizon else end_i
            lo_disp = max(0, lo - int(display_lead_in_w))
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
            disp_locked = {}
            for lw in display_lags_w:
                free = disp_paths[str(int(lw))]
                for delay in LOCK_DELAYS_S:
                    li = int(round(delay / stride_s)) - int(lw)
                    li = max(0, min(li, len(free) - 1))
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

        # Function commit.
        def _commit(d):
            out_ = {}
            for dt in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
                k = int(round(dt / stride_s))
                out_[str(dt)] = bool(k < len(d["displayed"]) and d["displayed"][k] == nm)
            return out_

        commit_s = _commit(disp)
        commit_s_h1 = _commit(disp1)

        if end_i > lo:
            s_fin = viterbi(e_res[sl], lT_chains)
            if o["final_rule"] == "maxlik" or o["family_first"] or o["chain_logprior"]:
                tot = chain_totals(e_res, st, sl, lT_chains, o["chain_logprior"])
                if dir_adj:
                    tot = {k: v + dir_adj.get(k, 0.0) for k, v in tot.items()}
                if start_adj:
                    tot = {k: v + start_adj.get(k, 0.0) for k, v in tot.items()}
                final = pick_line(tot, st, o["family_first"])
            else:
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
                    "display_names": (list(disp1["displayed"]) if want_display else None),
                    "display_state": (list(disp1["state_idx"]) if want_display else None),
                    "display_paths": disp_paths, "display_offchain_held": disp_held,
                    "display_locked": (disp_locked if want_display else None),
                    "entry_state": (int(entry_k) if entry_k is not None else None),
                    "entry_line": entry_nm,
                    "subs_end_changed": subs_end_changed,
                    "subs_line_changed": subs_line_changed,
                    "candidates": cand,
                    "lo": int(lo), "own_end_i": int(end_i), "hi_true": int(hi_true),
                    "lo_dec": int(lo_dec), "exit_search_hi": int(hi_lim),
                    "exit_rule": ("causal" if o.get("causal_exit", True) else "batch"),
                    "batch_own_end_i": (int(alt_end_i) if alt_end_i is not None else None),
                    "batch_final_line": causal_final,
                    "batch_found_final": (None if causal_final is None
                                          else bool(causal_final == nm))})
    return out
