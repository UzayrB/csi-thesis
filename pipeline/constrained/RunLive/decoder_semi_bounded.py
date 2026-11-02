# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The decoder the live app actually calls (night_track): it decodes a walk from its SPACE press until the...

from __future__ import annotations

import numpy as np

NEG_BIG = -1e30
MAX_WALK_S = 20.0
LOCK_DELAYS_S = (0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0)
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
    from pipeline.constrained.RunLive.decoder_lines import viterbi
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


# The semi-bounded decoder: for each walk, where it ends (the causal exit), the committed line, and with...
def night_track(e_path, rec, st, cfg, transit, ne, ge, stride_s, opts=None, want_display=False, display_lags_w=(0, 1, 2),
                display_delays_s=LOCK_DELAYS_S, display_to_horizon=False, display_alt_e=None, display_alt_flatten=None,
                display_lead_in_w=0, display_switch_paths=False):
    from pipeline.constrained.RunLive.decoder_lines import decoded_paths, transition_matrix
    from pipeline.constrained.RunLive.decoder_v2 import Space, stack2, transition_matrix2
    from pipeline.constrained.RunLive.shared_settings import WINDOW_S

    o = dict(default_opts())
    o.update(opts or {})
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit)
    lT = flatten_chain_prior(lT, st, float(o["prior_flatten"]))
    lT_chains = transition_matrix(st, "tight", with_null=False)
    ne.calibrate(e_path)
    e_stacked = stack2(e_path, ge, ne, sp)

    all_names = np.asarray(decoded_paths(np.arange(sp.N), st)).astype(str)
    on_chain = all_names != ""
    first_state = np.zeros(sp.N, bool)
    for nm in st.names:
        first_state[st.slice_of[nm][0]] = True
    horizon_w = int(round(MAX_WALK_S / stride_s))
    n = len(rec)
    out = []

    for pid, nm, _p_lo, _p_hi in rec.pass_spans():
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if len(w) < 2:
            continue
        lo = int(w[0])
        hi_lim = int(min(n - 1, len(e_stacked) - 1, lo + horizon_w))
        if hi_lim <= lo:
            continue
        st_lo = entry_start(o["entry"], e_stacked, st, sp, lo, on_chain, first_state)
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

        d = np.asarray(e_stacked[lo], float) + np.asarray(st_lo, float)
        end_i, timeout_fired = hi_lim, True
        for k in range(1, hi_lim - lo + 1):
            d = np.asarray(e_stacked[lo + k], float) + (d[:, None] + lT).max(axis=0)
            if int(np.nanargmax(np.where(np.isfinite(d), d, -np.inf))) >= st.n_states:
                end_i, timeout_fired = lo + k, False
                break
        sl = slice(lo, end_i + 1)

        disp_paths, entry_k, entry_nm, disp_locked = None, None, "", None
        if want_display:
            from pipeline.constrained.RunLive.display_rule import entry_position, fixed_lag_path, locked_chain_path
            disp_paths = {}
            disp_hi = hi_lim if display_to_horizon else end_i
            lo_disp = max(0, lo - int(display_lead_in_w))
            lw0 = int(round((WINDOW_S / 2.0) / stride_s))
            for lw in display_lags_w:
                if int(lw) - lw0 < 0:
                    raise AssertionError(f"display lag {lw} windows is shorter than the {lw0} windows a {WINDOW_S:g} s window "
                                         "needs to finish recording; it cannot be drawn causally")
                disp_paths[str(int(lw))], _held = fixed_lag_path(e_stacked, lT, st_lo, st, lo_disp, disp_hi, int(lw) - lw0)
            entry_k, entry_nm = entry_position(e_stacked, st_lo, st, lo)
            disp_locked = {}
            for lw in display_lags_w:
                free = disp_paths[str(int(lw))]
                for delay in display_delays_s:
                    li = max(0, min(int(round(delay / stride_s)) - int(lw), len(free) - 1))
                    nm_lock = free[li]["line"] or entry_nm or st.names[0]
                    node = {"lock_step": li, "lock_line": nm_lock, "lo_disp": int(lo_disp),
                            "evidence_horizon_w": int(lw) - lw0,
                            "path": locked_chain_path(e_path, lT_chains, st, lo_disp, disp_hi, int(lw) - lw0, nm_lock,
                                                      log_start=st_lo)}
                    if display_alt_e:
                        node["paths_alt"] = {}
                        for key_, v in display_alt_e.items():
                            lTk = lT_chains
                            fk = (display_alt_flatten or {}).get(key_)
                            if fk:
                                lTk = flatten_chain_prior(lT_chains, st, float(fk))
                            alt = np.resize(v, (len(e_path), np.shape(v)[1]))
                            node["paths_alt"][key_] = locked_chain_path(alt, lTk, st, lo_disp, disp_hi, int(lw) - lw0,
                                                                        nm_lock, log_start=st_lo)
                            if display_switch_paths:
                                node.setdefault("switch_paths", {})[key_] = {
                                    nm_z: (node["paths_alt"][key_] if nm_z == nm_lock else
                                           locked_chain_path(alt, lTk, st, lo_disp, disp_hi, int(lw) - lw0, nm_z,
                                                             log_start=st_lo))
                                    for nm_z in st.names}
                    disp_locked[f"{int(lw)}|{delay}"] = node

        tot = chain_totals(e_path, st, sl, lT_chains, o["chain_logprior"])
        if start_adj:
            tot = {k: v + start_adj.get(k, 0.0) for k, v in tot.items()}
        final = pick_line(tot, st, o["family_first"])
        out.append({"key": f"{rec.session}|{rec.stem}|{int(pid)}", "pass_id": int(pid), "true_line": nm,
                    "final_line": final, "timeout_fired": bool(timeout_fired), "lo": int(lo), "own_end_i": int(end_i),
                    "exit_search_hi": int(hi_lim), "display_paths": disp_paths, "display_locked": disp_locked,
                    "entry_state": (int(entry_k) if entry_k is not None else None), "entry_line": entry_nm})
    return out
