# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: PHASE 2: the four structural changes to the semi-bounded decoder, each behind its own flag.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STRIDE = float(os.environ.get("SB_STRIDE", "1.0"))
if abs(STRIDE - 0.5) < 1e-9:
    from pipeline.constrained import lattice as _lattice
    _WANT = _lattice.half_art_dir()
    _already = os.environ.get("TDR_ART_DIR") == _WANT
    os.environ["TDR_WINDOWS_ROOT"] = _lattice.windows_root()
    os.environ["TDR_ART_DIR"] = _WANT
    assert _already or "pipeline.constrained.common" not in sys.modules, \
        "sb2_structural must be the entry point at 0.5 s, or its importer must set the roots first"

import itertools
import json
import time

import numpy as np

NEG_BIG = -1e30

from pipeline.constrained.common import (E_POST, RUN_DIR, is_cross,
                                         pairings, read_json, status, tag_of)
from pipeline.constrained.rebuild_common import (WINDOW_S, findings, headline,
                                                 save_results, stage_dir)

STAGE = f"sb2_structural_{'half' if abs(STRIDE - 0.5) < 1e-9 else 'one'}"
MAX_WALK_S = 20.0
NEVER_EXIT_S = 5.0
SAFETY_SPEED = 0.5
V_GRID = (1.6, 2.0, 2.4)
UPPER_SPEED_GRID = (1.8, 2.2, 2.6)
HYSTERESIS = 2
SEED = 0
FLAGS = ("pinned_entry", "max_speed", "time_lockout", "all_alive", "rescore_end")


_PRESS_CACHE: dict = {}


# {pass_id: last anchor press time}, from the read-only ground truth.
def press_ends(session: str, stem: str) -> dict:
    key = (session, stem)
    if key not in _PRESS_CACHE:
        from pipeline.constrained.lattice import gt_path
        path = gt_path(session, stem)
        with open(path, encoding="utf-8") as f:
            gt = json.load(f)
        got = {int(q["pass_id"]): float(q["t_end"]) for q in gt.get("passes", [])}
        if not got:
            raise RuntimeError(f"no passes with anchor presses in {path}")
        rt = gt.get("reaction_time") or {}
        if not rt.get("applied"):
            raise RuntimeError(f"{path} does not record the reaction-time bias as applied; "
                               f"the end would be biased by the operator's keypress latency")
        _PRESS_CACHE[key] = got
    return _PRESS_CACHE[key]


# Refuse to start if another live process already holds this stage.
def claim_stage(stage: str):
    d = stage_dir(stage)
    lock = os.path.join(d, ".running")
    if os.path.exists(lock):
        try:
            with open(lock, encoding="utf-8") as f:
                old = int((f.read().split() or ["0"])[0])
        except (ValueError, OSError):
            old = 0
        if old and old != os.getpid():
            try:
                os.kill(old, 0)
            except (ProcessLookupError, PermissionError):
                pass
            else:
                raise RuntimeError(
                    f"{stage} is already running as pid {old}. Two instances would write the same "
                    f"results.json. Stop that one first, or remove {lock} if it is stale.")
    with open(lock, "w", encoding="utf-8") as f:
        f.write(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    return lock


# Function release stage.
def release_stage(lock: str) -> None:
    try:
        os.remove(lock)
    except OSError:
        pass


GUARD_MIN_PCT = 50.0


# Select among arms that PASS the end-time substitution guard, never across it.
def apply_gate(by_arm: dict, guard_min: float = GUARD_MIN_PCT) -> dict:
    # Function line.
    def line(k):
        return (by_arm.get(k) or {}).get("final_line_pct")

    # Function subs.
    def subs(k):
        return (by_arm.get(k) or {}).get("substitution_end_pct")

    scored = [k for k in by_arm if line(k) is not None]
    passing = [k for k in scored if subs(k) is not None and subs(k) > guard_min]
    unmeasured = [k for k in scored if subs(k) is None]
    best_overall = max(scored, key=line) if scored else None
    best_passing = max(passing, key=line) if passing else None
    return {
        "guard_min_pct": guard_min,
        "rule": ("among the arms whose end-time substitution EXCEEDS the bar, take the best line "
                 "identification. The guard is a gate applied first, not an axis traded against "
                 "the line."),
        "n_arms_scored": len(scored),
        "n_arms_passing_guard": len(passing),
        "n_arms_guard_unmeasured": len(unmeasured),
        "best_overall_arm": best_overall,
        "best_overall_line_pct": line(best_overall) if best_overall else None,
        "best_overall_substitution_end_pct": subs(best_overall) if best_overall else None,
        "best_overall_passes_guard": (None if best_overall is None or subs(best_overall) is None
                                      else bool(subs(best_overall) > guard_min)),
        "best_guard_passing_arm": best_passing,
        "best_guard_passing_line_pct": line(best_passing) if best_passing else None,
        "best_guard_passing_substitution_end_pct": subs(best_passing) if best_passing else None,
        "line_cost_of_the_gate_points": (
            None if (best_passing is None or best_overall is None)
            else line(best_overall) - line(best_passing)),
        "arms_passing_guard": sorted(passing, key=line, reverse=True)}


# Function chain lengths.
def chain_lengths(st):
    s_of = np.asarray(st.s_of, float)
    return {nm: float(s_of[st.slice_of[nm][1] - 1]) for nm in st.names}


# 2.2a: forbid any within-chain advance faster than V m/s.
def speed_capped_transition(lT, st, V, stride_s):
    lT2 = lT.copy()
    s_of = np.asarray(st.s_of, float)
    max_step = V * stride_s
    for nm in st.names:
        lo, hi = st.slice_of[nm]
        blk = s_of[lo:hi]
        adv = blk[None, :] - blk[:, None]
        lT2[lo:hi, lo:hi] = np.where(adv > max_step + 1e-9, -1e30, lT2[lo:hi, lo:hi])
    return lT2


# 2.2b: the null is unavailable until T seconds have elapsed since the start press.
def time_lockout_mask(e_stacked, st, sp, lo, hi_lim, nm, upper_speed, stride_s):
    L = chain_lengths(st)
    T = (L.get(nm, 0.0) / float(upper_speed)) if upper_speed else 0.0
    n_lock = int(np.floor(T / stride_s))
    if n_lock <= 0:
        return e_stacked, 0.0, 0
    e2 = e_stacked.copy()
    end = min(lo + n_lock, hi_lim + 1)
    e2[lo:end, st.n_states:] = NEG_BIG
    return e2, T, n_lock


# 2.3: the forward pass with every chain alive, and the line a viewer would have seen.
def running_argmax_display(e_stacked, lT, log_start, st, sl, hysteresis=None):
    h = int(HYSTERESIS if hysteresis is None else hysteresis)
    T = np.exp(lT)
    a = e_stacked[sl][0] + log_start
    lead, held, shown, revisions, seq_shown, seq_state = None, 0, [], 0, [], []
    for t in range(len(e_stacked[sl])):
        if t:
            m = float(a.max())
            if not np.isfinite(m):
                break
            a = np.log(np.maximum(np.exp(a - m) @ T, 1e-300)) + m + e_stacked[sl][t]
        best, best_v = "", -np.inf
        for nm in st.names:
            lo, hi = st.slice_of[nm]
            v = a[lo:hi]
            v = v[np.isfinite(v)]
            if not len(v):
                continue
            mm = float(v.max())
            tot = mm + np.log(np.exp(v - mm).sum())
            if tot > best_v:
                best_v, best = tot, nm
        if best == lead:
            held += 1
        else:
            lead, held = best, 1
        if held >= h and (not shown or shown[-1] != lead):
            if shown:
                revisions += 1
            shown.append(lead)
        now = shown[-1] if shown else ""
        seq_shown.append(now)
        if now:
            lo, hi = st.slice_of[now]
            v = a[lo:hi]
            seq_state.append(int(lo + int(np.nanargmax(np.where(np.isfinite(v), v, -np.inf))))
                             if np.isfinite(v).any() else -1)
        else:
            seq_state.append(-1)
    return {"displayed": seq_shown, "final_displayed": (shown[-1] if shown else ""),
            "revisions": revisions, "state_idx": seq_state, "hysteresis": h}


# The semi-bounded decoder with the five flags.
def track2(e_path, rec, st, cfg, transit, ne, ge, stride_s, flags, V=2.0, upper_speed=2.2,
           alt_e=None):
    from pipeline.constrained.decoder import NEG, decoded_paths, transition_matrix, viterbi
    from pipeline.constrained.decoder2 import Space, stack2, transition_matrix2

    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit)
    lT_chains = transition_matrix(st, "tight", with_null=False)

    # Function stacked.
    def stacked(src):
        if ne is not None and ge is not None:
            ne.calibrate(src)
            return stack2(src, ge, ne, sp)
        return src

    e_stacked = stacked(e_path)
    alt_stacked = (stacked(np.resize(alt_e, (len(e_path), alt_e.shape[1])))
                   if alt_e is not None else None)

    lT_use = speed_capped_transition(lT, st, V, stride_s) if flags["max_speed"] else lT

    all_names = np.asarray(decoded_paths(np.arange(e_stacked.shape[1]), st)).astype(str)
    on_chain = all_names != ""
    first_state = np.zeros(e_stacked.shape[1], bool)
    for nm in st.names:
        first_state[st.slice_of[nm][0]] = True

    start = np.full(e_stacked.shape[1], NEG)
    start[first_state if flags["pinned_entry"] else on_chain] = 0.0

    L = chain_lengths(st)
    longest = max(L.values())
    horizon_w = int(round(MAX_WALK_S / stride_s))
    timeout_w = int(np.ceil(longest / SAFETY_SPEED / stride_s))
    n = len(rec)
    t0 = np.asarray(rec.t0, float)
    centres = t0 + WINDOW_S / 2.0
    xy_true = np.asarray(rec.xy, float)
    s_of = np.asarray(st.s_of, float)
    presses = press_ends(rec.session, rec.stem)
    out = []

    # The decoder's own end on one emission, with the time lockout applied if set.
    def decode_end(src_stacked, lo, hi_lim, nm):
        e_use, T_lock, n_lock = (
            time_lockout_mask(src_stacked, st, sp, lo, hi_lim, nm, upper_speed, stride_s)
            if flags["time_lockout"] else (src_stacked, 0.0, 0))
        s = viterbi(e_use[lo:hi_lim + 1], lT_use, log_start=start)
        names = np.asarray(decoded_paths(s, st)).astype(str)
        ek = None
        for k in range(1, len(s)):
            if names[k] == "":
                ek = k
                break
        fired = False
        if ek is None and timeout_w < len(s):
            ek, fired = timeout_w, True
        return s, names, ek, fired, T_lock, n_lock

    for pid, nm, p_lo, p_hi in rec.pass_spans():
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if len(w) < 2:
            continue
        lo, hi_true = int(w[0]), int(w[-1])
        hi_lim = int(min(n - 1, len(e_stacked) - 1, lo + horizon_w))
        if hi_lim <= lo:
            continue

        s, names, exit_k, timeout_fired, T_lock, n_lock = decode_end(e_stacked, lo, hi_lim, nm)
        own_end_i = lo + (exit_k if exit_k is not None else len(s) - 1)

        subs_end_changed = None
        if alt_stacked is not None:
            s2, _n2, ek2, _f2, _t2, _l2 = decode_end(alt_stacked, lo, hi_lim, nm)
            own_end_i2 = lo + (ek2 if ek2 is not None else len(s2) - 1)
            subs_end_changed = bool(own_end_i2 != own_end_i)

        on_h = names[names != ""]
        if len(on_h):
            v, c = np.unique(on_h, return_counts=True)
            shipped_line = str(v[c.argmax()])
        else:
            shipped_line = ""

        sl = slice(lo, own_end_i + 1)
        commit_s, displayed_seq = {}, None
        if flags["all_alive"]:
            disp = running_argmax_display(e_stacked, lT_use, start, st, sl)
            provisional, revisions = disp["final_displayed"], disp["revisions"]
            displayed_seq = disp["displayed"]
        else:
            on = names[:max(1, (exit_k if exit_k is not None else len(names)))]
            on = on[on != ""]
            if len(on):
                v, c = np.unique(on, return_counts=True)
                provisional = str(v[c.argmax()])
            else:
                provisional = ""
            revisions = 0

        for dt in (1.0, 2.0, 3.0, 4.0):
            k = int(round(dt / stride_s))
            if displayed_seq is not None:
                commit_s[str(dt)] = bool(k < len(displayed_seq) and displayed_seq[k] == nm)
            else:
                commit_s[str(dt)] = bool(k < len(names) and names[k] == nm)

        if flags["rescore_end"] and own_end_i > lo:
            s_fin = viterbi(e_path[sl], lT_chains)
            n_fin = np.asarray(decoded_paths(s_fin, st)).astype(str)
            on_f = n_fin[n_fin != ""]
            if len(on_f):
                v, c = np.unique(on_f, return_counts=True)
                final = str(v[c.argmax()])
            else:
                final = ""
            seq_fin = s_fin
        else:
            final = provisional
            seq_fin = s[:max(1, (exit_k if exit_k is not None else len(s)))]

        err = None
        if final == nm and len(seq_fin):
            idx = np.arange(lo, lo + len(seq_fin))
            keep = (idx <= hi_true) & (np.asarray(seq_fin) < st.n_states)
            if keep.any():
                xy_hat = np.asarray(st.xy)[np.asarray(seq_fin)[keep]]
                err = float(np.median(np.linalg.norm(xy_hat - xy_true[idx[keep]], axis=1)))

        arc_frac = None
        s_arr = np.asarray(s)
        on_idx = np.flatnonzero(s_arr < st.n_states)
        if len(on_idx):
            last_on = int(s_arr[on_idx[-1]])
            own_chain = str(np.asarray(st.path_of)[last_on])
            if L.get(own_chain):
                arc_frac = float(s_of[last_on]) / L[own_chain]

        end_passend = float(t0[p_hi]) + WINDOW_S
        end_walkend = float(centres[hi_true])
        end_press = presses.get(int(pid))
        if end_press is None:
            raise RuntimeError(f"pass {pid} of {rec.stem} has no anchor press in the ground truth")
        own_end_t = float(centres[own_end_i])
        out.append({"pass_id": int(pid),
                    "key": f"{rec.session}|{rec.stem}|{int(pid)}",
                    "true_line": nm,
                    "shipped_rule_line": shipped_line, "found_shipped_rule": shipped_line == nm,
                    "arc_frac_at_exit": arc_frac,
                    "provisional_line": provisional, "final_line": final,
                    "found_provisional": provisional == nm, "found_final": final == nm,
                    "err_m": err,
                    "exit_dt_press_s": own_end_t - end_press,
                    "exit_dt_s": own_end_t - end_passend,
                    "exit_dt_walkend_s": own_end_t - end_walkend,
                    "never_ended": bool(abs(own_end_t - end_press) > NEVER_EXIT_S),
                    "revisions": int(revisions), "timeout_fired": bool(timeout_fired),
                    "time_lockout_s": float(T_lock), "time_lockout_windows": int(n_lock),
                    "subs_end_changed": subs_end_changed,
                    "commit_s": commit_s,
                    "impossible": int(sum(
                        1 for i in range(1, len(seq_fin))
                        if seq_fin[i] < st.n_states and seq_fin[i - 1] < st.n_states
                        and lT_chains[int(seq_fin[i - 1]), int(seq_fin[i])] <= -1e29)),
                    "own_end_i": int(own_end_i), "lo": int(lo)})
    return out


# Function summarise.
def summarise(rows):
    if not rows:
        return None
    err = [r["err_m"] for r in rows if r["found_final"] and r["err_m"] is not None]
    dtp = [r["exit_dt_press_s"] for r in rows]
    dts = [r["exit_dt_s"] for r in rows]
    dtw = [r["exit_dt_walkend_s"] for r in rows]
    arcs = [r["arc_frac_at_exit"] for r in rows if r["arc_frac_at_exit"] is not None]
    subs = [r["subs_end_changed"] for r in rows if r["subs_end_changed"] is not None]
    per_line = {}
    for r in rows:
        d = per_line.setdefault(r["true_line"], {"n": 0, "hit": 0})
        d["n"] += 1
        d["hit"] += int(r["found_final"])
    return {"n_passes": len(rows),
            "final_line_pct": 100.0 * float(np.mean([r["found_final"] for r in rows])),
            "provisional_line_pct": 100.0 * float(np.mean([r["found_provisional"] for r in rows])),
            "shipped_rule_line_pct": 100.0 * float(np.mean([r["found_shipped_rule"] for r in rows])),
            "arc_frac_at_exit_median": float(np.median(arcs)) if arcs else None,
            "err_m": float(np.median(err)) if err else None,
            "exit_dt_press_median_s": float(np.median(dtp)) if dtp else None,
            "exit_dt_press_mean_s": float(np.mean(dtp)) if dtp else None,
            "exit_dt_press_p90_s": float(np.percentile(dtp, 90)) if dtp else None,
            "exit_dt_press_within_1s_pct": (100.0 * float(np.mean([abs(x) <= 1.0 for x in dtp]))
                                            if dtp else None),
            "exit_dt_median_s": float(np.median(dts)) if dts else None,
            "exit_dt_mean_s": float(np.mean(dts)) if dts else None,
            "exit_dt_p90_s": float(np.percentile(dts, 90)) if dts else None,
            "exit_dt_walkend_median_s": float(np.median(dtw)) if dtw else None,
            "exit_dt_walkend_mean_s": float(np.mean(dtw)) if dtw else None,
            "exit_dt_walkend_p90_s": float(np.percentile(dtw, 90)) if dtw else None,
            "never_ended_pct": 100.0 * float(np.mean([r["never_ended"] for r in rows])),
            "revisions_mean": float(np.mean([r["revisions"] for r in rows])),
            "timeout_fired_pct": 100.0 * float(np.mean([r["timeout_fired"] for r in rows])),
            "time_lockout_s_median": float(np.median([r["time_lockout_s"] for r in rows])),
            "substitution_end_pct": (100.0 * float(np.mean(subs)) if subs else None),
            "n_substitution": len(subs),
            "impossible_transitions": int(sum(r.get("impossible", 0) for r in rows)),
            "commit_timeline_pct": {d: 100.0 * float(np.mean([r["commit_s"].get(d, False)
                                                              for r in rows]))
                                    for d in ("1.0", "2.0", "3.0", "4.0")},
            "per_line_recall_pct": {k: 100.0 * v["hit"] / v["n"] for k, v in sorted(per_line.items())}}


# A pairing whose TEST session is one of this one's TRAINING sessions and whose training never touches this...
def selection_pairing_for(tr_s, te_s):
    for a, b in pairings():
        if a == b:
            continue
        if b[0] in tr_s and te_s[0] not in a:
            return tag_of(a, b, False), (a, b)
    return None, None


# The per-recording emission for a pairing, at whichever stride this process is isolated on.
def emissions_for(tag, tr_s, te_s, within, st, kind, alpha_e):
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    from pipeline.constrained.recordings import gate_energy, load_meta
    pp = posterior_path(tag, 25, E_POST, SEED)
    if not os.path.exists(pp):
        return None
    marg = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
            if kind == "scaled" else None)
    out = []
    for stem, b in sorted(read_full_posteriors(pp).items()):
        prob = b["prob"].astype(float)
        e = (cell_emission(prob, st.xy, 25) if marg is None
             else scaled_cell_emission(prob, st.xy, 25, marg, alpha=alpha_e))
        out.append((stem, load_meta(te_s[0], stem), gate_energy(te_s[0], stem), e))
    return out


# One arm over every recording of a pairing.
def run_arm(rows_src, st, cfg, transit, ne, flags, V=2.0, upper_speed=2.2, subs=False):
    rows = []
    n = len(rows_src)
    for k, (_stem, rec, ge, e) in enumerate(rows_src):
        alt = rows_src[(k + 1) % n][3] if (subs and n > 1) else None
        rows += track2(e, rec, st, cfg, transit, ne, ge, STRIDE, flags, V, upper_speed, alt)
    return rows


# Function main.
def main() -> int:
    from pipeline.constrained import paths as P
    import pipeline.constrained.decoder as D
    from pipeline.constrained.common import ART_DIR
    from pipeline.constrained.rb3_display import shipped_config
    from pipeline.constrained.rebuild_common import emission_choice, load_results

    lock = claim_stage(STAGE)
    t_start = time.time()
    st = P.states()
    kind, alpha_e, _s = emission_choice()
    s2 = load_results("rb2_decoder")
    cfg, ne, _sel = shipped_config(s2, "s0102_to_s03")
    transit = read_json(os.path.join(RUN_DIR, "rb0_preflight", "transit_geometry.json"), {}) or {}

    was = D.DT
    D.DT = STRIDE
    status(f"{STAGE} START: the four structural changes at {STRIDE} s. art={ART_DIR}")
    status(f"  motion model: step {D.V_MEAN * D.DT:.3f} m per window, sd {D.V_SD * D.DT:.4f}")

    full = os.environ.get("SB2_ARMS", "16") == "16"
    if full:
        arms = [dict(zip(FLAGS, c)) for c in itertools.product([False, True], repeat=len(FLAGS))]
    else:
        arms = ([dict.fromkeys(FLAGS, False)]
                + [{f: (f == g) for f in FLAGS} for g in FLAGS]
                + [dict.fromkeys(FLAGS, True)])
    status(f"  {len(arms)} arms ({'full factorial' if full else 'six-arm fallback'})")

    RES = {"stage": STAGE, "stride_s": STRIDE, "n_arms": len(arms),
           "arms_mode": "full" if full else "reduced", "v_grid": list(V_GRID),
           "upper_speed_grid": list(UPPER_SPEED_GRID),
           "hysteresis_windows": HYSTERESIS, "safety_speed_m_s": SAFETY_SPEED,
           "flags": list(FLAGS), "per_pairing": {}, "sweeps": {}, "failures": []}

    emis_cache = {}

    # Function emis.
    def emis(tag, tr_s, te_s, within):
        if tag not in emis_cache:
            emis_cache[tag] = emissions_for(tag, tr_s, te_s, within, st, kind, alpha_e)
        return emis_cache[tag]

    only = [x.strip() for x in os.environ.get("SB2_ONLY", "").split(",") if x.strip()]
    RES["only"] = only or None

    ALL_ON = dict.fromkeys(FLAGS, True)

    for tr_s, te_s in pairings():
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        if only and tag not in only:
            continue
        src = emis(tag, tr_s, te_s, within)
        if src is None:
            RES["failures"].append({"tag": tag, "error": "no posteriors at this stride"})
            continue
        try:
            sel_tag, sel_pair = selection_pairing_for(tr_s, te_s)
            V, UP = V_GRID[1], UPPER_SPEED_GRID[1]
            basis = "defaults kept: no selection pairing avoids this pairing's test session"
            if sel_tag is not None:
                s_tr, s_te = sel_pair
                sel_src = emis(sel_tag, s_tr, s_te, False)
                if sel_src is not None:
                    vs = {}
                    for v in V_GRID:
                        sm = summarise(run_arm(sel_src, st, cfg, transit, ne, ALL_ON, v, UP))
                        vs[v] = (sm or {}).get("final_line_pct", -1)
                    us = {}
                    for u in UPPER_SPEED_GRID:
                        sm = summarise(run_arm(sel_src, st, cfg, transit, ne, ALL_ON, V_GRID[1], u))
                        us[u] = (sm or {}).get("final_line_pct", -1)
                    v_tied = (max(vs.values()) - min(vs.values())) < 1e-9
                    u_tied = (max(us.values()) - min(us.values())) < 1e-9
                    V = V_GRID[1] if v_tied else max(V_GRID, key=lambda x: vs[x])
                    UP = UPPER_SPEED_GRID[1] if u_tied else max(UPPER_SPEED_GRID, key=lambda x: us[x])
                    basis = (f"V {'NOT SELECTED (tied, the cap never binds)' if v_tied else 'selected'}"
                             f", upper speed "
                             f"{'NOT SELECTED (tied, the lockout never binds)' if u_tied else 'selected'}"
                             f" on {sel_tag}, which never trains or tests on session {te_s[0]}")
                    RES["sweeps"][tag] = {"V": V, "upper_speed": UP, "basis": basis,
                                          "selection_pairing": sel_tag,
                                          "V_tied": bool(v_tied), "upper_tied": bool(u_tied),
                                          "V_scores": {str(k): v for k, v in vs.items()},
                                          "upper_scores": {str(k): v for k, v in us.items()}}
            RES["sweeps"].setdefault(tag, {"V": V, "upper_speed": UP, "basis": basis,
                                           "selection_pairing": sel_tag})

            per_arm = {}
            for a_ in arms:
                key = "+".join([f for f in FLAGS if a_[f]]) or "none"
                want_subs = True
                sm = summarise(run_arm(src, st, cfg, transit, ne, a_, V, UP, subs=want_subs))
                if sm is not None:
                    sm["flags"] = dict(a_)
                    sm["V"] = V
                    sm["upper_speed"] = UP
                    sm["selection_basis"] = basis
                per_arm[key] = sm
            RES["per_pairing"][tag] = {"regime": "cross" if is_cross(tag) else "within",
                                       "V": V, "upper_speed": UP, "selection_basis": basis,
                                       "arms": per_arm}
            none_a, all_a = per_arm.get("none"), per_arm.get("+".join(FLAGS))
            status(f"  {tag:16s} [{'cross' if is_cross(tag) else 'within':6s}] V={V} T@{UP} "
                   f"none {none_a['final_line_pct']:5.1f}% -> all "
                   f"{all_a['final_line_pct']:5.1f}% | exit(pass) "
                   f"{none_a['exit_dt_median_s']:+.1f} -> {all_a['exit_dt_median_s']:+.1f} "
                   f"| exit(walk) {none_a['exit_dt_walkend_median_s']:+.1f} -> "
                   f"{all_a['exit_dt_walkend_median_s']:+.1f} | subs end "
                   f"{none_a['substitution_end_pct']} -> {all_a['substitution_end_pct']}")
        except Exception as exc:
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-2000:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    cross = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "cross"}

    # Function arm med.
    def arm_med(key, field):
        v = [p["arms"][key][field] for p in cross.values()
             if p["arms"].get(key) and p["arms"][key].get(field) is not None]
        return float(np.median(v)) if v else None

    arm_keys = sorted({k for p in cross.values() for k in p["arms"]})
    RES["cross_day"] = {"n_pairings": len(cross), "by_arm": {
        k: {f: arm_med(k, f) for f in ("final_line_pct", "provisional_line_pct",
                                       "shipped_rule_line_pct", "err_m",
                                       "exit_dt_press_median_s", "exit_dt_press_mean_s",
                                       "exit_dt_press_p90_s", "exit_dt_press_within_1s_pct",
                                       "exit_dt_median_s",
                                       "exit_dt_mean_s", "exit_dt_p90_s",
                                       "exit_dt_walkend_median_s", "exit_dt_walkend_mean_s",
                                       "exit_dt_walkend_p90_s", "never_ended_pct",
                                       "revisions_mean", "timeout_fired_pct",
                                       "arc_frac_at_exit_median", "substitution_end_pct",
                                       "time_lockout_s_median")}
        for k in arm_keys}}
    all_key = "+".join(FLAGS)
    c = RES["cross_day"]["by_arm"]
    base, best_all = c.get("none", {}), c.get(all_key, {})
    singles = {f: c.get(f, {}).get("final_line_pct") for f in FLAGS}
    singles = {k: v for k, v in singles.items() if v is not None}
    strongest = max(singles, key=singles.get) if singles else None
    RES["cross_day"]["strongest_single_flag"] = strongest
    RES["cross_day"]["single_flag_line_pct"] = singles
    RES["cross_day"]["timeout_too_strong"] = bool(
        (best_all.get("timeout_fired_pct") or 0.0) > 5.0)
    # Function d.
    def d(with_key, without_key):
        a_, b_ = c.get(with_key, {}), c.get(without_key, {})
        if a_.get("final_line_pct") is None or b_.get("final_line_pct") is None:
            return None
        return a_["final_line_pct"] - b_["final_line_pct"]
    RES["cross_day"]["rescore_delta"] = {
        "alone": d("rescore_end", "none"),
        "with_2_2a": d("max_speed+rescore_end", "max_speed"),
        "with_2_2b": d("time_lockout+rescore_end", "time_lockout"),
        "with_both": d("max_speed+time_lockout+rescore_end", "max_speed+time_lockout"),
        "note": ("positive means rescoring at the decoder's own end HELPS. If it is negative alone "
                 "and positive once the constraints are on, the constraints fixed the end.")}
    guard = {}
    for k in ("none", "max_speed", "time_lockout", "max_speed+time_lockout",
              "pinned_entry", "all_alive", "rescore_end", "pinned_entry+all_alive", all_key):
        guard[k] = c.get(k, {}).get("substitution_end_pct")
    RES["cross_day"]["substitution_end_pct_by_arm"] = guard
    RES["cross_day"]["gate"] = apply_gate(c)
    base_subs = c.get("none", {}).get("substitution_end_pct")
    marg = {}
    for f_ in FLAGS:
        v = c.get(f_, {}).get("substitution_end_pct")
        marg[f_] = (None if (v is None or base_subs is None) else v - base_subs)
    RES["cross_day"]["substitution_end_marginal_points"] = marg
    RES["cross_day"]["substitution_end_baseline_pct"] = base_subs
    worst = [k for k, v in marg.items() if v is not None and v < 0]
    RES["cross_day"]["flags_that_lower_end_substitution"] = sorted(
        worst, key=lambda k: marg[k])
    RES["cross_day"]["all_alive_interaction"] = {
        "over_true_walk_window_points": None,
        "over_decoder_own_end_points": (
            None if (c.get("all_alive", {}).get("final_line_pct") is None or base is None
                     or base.get("final_line_pct") is None)
            else c["all_alive"]["final_line_pct"] - base["final_line_pct"]),
        "prediction": ("keeping every chain alive helps only because the decoder's own end is "
                       "wrong; if the end is fixed its value should shrink towards the phase 1 "
                       "figure, which was negative")}
    base_subs = guard.get("none")
    con_subs = guard.get("max_speed+time_lockout")
    RES["cross_day"]["end_still_signal_driven"] = (
        None if con_subs is None else bool(con_subs > 50.0))
    RES["cross_day"]["end_became_a_clock"] = (
        None if (con_subs is None or base_subs is None) else bool(con_subs <= 50.0 < base_subs))
    RES["minutes"] = round((time.time() - t_start) / 60.0, 1)
    D.DT = was
    save_results(STAGE, RES)
    release_stage(lock)

    cd = RES["cross_day"]
    rd, guard = cd["rescore_delta"], cd["substitution_end_pct_by_arm"]
    status(f"  CROSS-DAY at {STRIDE} s, {len(cross)} pairings:")
    status(f"    none     final {base.get('final_line_pct')} | exit vs PRESS "
           f"{base.get('exit_dt_press_median_s')} s (within 1 s on "
           f"{base.get('exit_dt_press_within_1s_pct')}%) | vs pass end "
           f"{base.get('exit_dt_median_s')} | vs last label {base.get('exit_dt_walkend_median_s')}")
    status(f"    all on   final {best_all.get('final_line_pct')} | exit vs PRESS "
           f"{best_all.get('exit_dt_press_median_s')} s (within 1 s on "
           f"{best_all.get('exit_dt_press_within_1s_pct')}%) | timeout "
           f"{best_all.get('timeout_fired_pct')}%")
    status(f"    strongest single flag: {strongest} at {singles.get(strongest)}")
    status(f"    2.4 rescore delta: alone {rd['alone']}, with 2.2a {rd['with_2_2a']}, "
           f"with 2.2b {rd['with_2_2b']}, with both {rd['with_both']}")
    status(f"    GUARD, substitution on the END TIME by arm: {guard}")
    status(f"    GUARD PER FLAG, points against the {cd['substitution_end_baseline_pct']} baseline: "
           f"{cd['substitution_end_marginal_points']}")
    status(f"    flags that LOWER the end substitution: {cd['flags_that_lower_end_substitution']}")
    status(f"    end still signal-driven: {cd['end_still_signal_driven']}; "
           f"end became a clock: {cd['end_became_a_clock']}")

    ok = bool(cross) and base.get("final_line_pct") is not None
    headline(f"PHASE 2 ABLATION at {STRIDE} s: none {base.get('final_line_pct')} -> all "
             f"{best_all.get('final_line_pct')} percent cross-day; strongest single flag "
             f"{strongest}; end-time error against the pass end "
             f"{base.get('exit_dt_median_s')} -> {best_all.get('exit_dt_median_s')} s and against "
             f"the last labelled walk window {base.get('exit_dt_walkend_median_s')} -> "
             f"{best_all.get('exit_dt_walkend_median_s')} s; substitution on the end time "
             f"{guard.get('none')} -> {guard.get('max_speed+time_lockout')} percent.")
    findings(f"sb2_{'half' if STRIDE < 0.9 else 'one'}", ok, (
        f"Phase 2, the structural changes at a {STRIDE} s stride, {len(arms)} arms over "
        f"{len(cross)} cross-day pairings.\n\n"
        f"THE LINE. With no flag set the final line is right on {base.get('final_line_pct')} "
        f"percent, which is the shipped decoder with the line read at its own end rather than over "
        f"the horizon; the shipped rule itself scores "
        f"{base.get('shipped_rule_line_pct')} percent. With every flag on it is "
        f"{best_all.get('final_line_pct')} percent. The strongest single flag is {strongest} at "
        f"{singles.get(strongest)} percent.\n\n"
        f"2.2a AND 2.2b, DID THEY BIND. The maximum-speed cap sat at V={cd.get('V_note', 'per row')} "
        f"and the time lockout at a median {best_all.get('time_lockout_s_median')} s. The safety "
        f"timeout fired on {best_all.get('timeout_fired_pct')} percent of passes, so the lockout "
        f"being too strong is {cd['timeout_too_strong']}. D1 established that the decoder's "
        f"implied traversal speed is 1.26 m/s with a p90 of 1.27 and NO pass above 2.0 m/s, so a "
        f"cap at {list(V_GRID)} m/s is expected to be inert, and whether it is shows in the arms "
        f"above rather than in this sentence.\n\n"
        f"2.4, BEFORE AND AFTER, WHICH IS THE FINDING. Rescoring at the decoder's own end changes "
        f"the line by {rd['alone']} points on its own, {rd['with_2_2a']} with the speed cap, "
        f"{rd['with_2_2b']} with the time lockout and {rd['with_both']} with both. Rescoring over "
        f"a window that ends short must hurt, so a negative alone that turns positive with the "
        f"constraints on is the evidence that the constraints fixed the end. \n\n"
        f"THE GUARD, WHICH DECIDES WHETHER ANY OF THIS SHIPS. The end counts as signal-driven only "
        f"if another participant's CSI changes it. Substitution on the END TIME by arm: {guard}. "
        f"With the two constraints on it is {guard.get('max_speed+time_lockout')} percent against "
        f"{guard.get('none')} percent with neither. The bar is more than half of passes: "
        f"end_still_signal_driven={cd['end_still_signal_driven']}. "
        + ("THE END HAS BECOME A CLOCK RATHER THAN A MEASUREMENT: the constraints moved the end "
           "while the substitution rate fell to or below half, so this does NOT ship whatever it "
           "does to the line figure."
           if cd["end_became_a_clock"] else
           "The end did not become a clock: the substitution rate on the end time did not collapse "
           "below the bar when the constraints were applied.") + "\n\n"
        f"THE END IS REPORTED AGAINST TWO DEFINITIONS and they disagree by more than the bar. "
        f"Against the pass end, the far edge of a 3 s run-out grace zone that recordings.py "
        f"documents as windows in which the person IS still walking, the error is "
        f"{base.get('exit_dt_median_s')} s with no flags and {best_all.get('exit_dt_median_s')} s "
        f"with all. Against the centre of the last window carrying a position label it is "
        f"{base.get('exit_dt_walkend_median_s')} s and {best_all.get('exit_dt_walkend_median_s')} "
        f"s. The two sit a median 4.0 s apart, so which one the one-second bar refers to decides "
        f"the verdict and has not been fixed by this project. It is flagged, not chosen here."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
