"""THE CORRECTED MEASUREMENT. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, the block headed
"THE CORRECTED MEASUREMENT", and stage 1.2. Every number quoted from stage 1 onward is computed here
and nowhere else.

WHY THE OLD METRIC HAD TO GO. ``segmentation_metrics`` counted a pass as found if the decoder was on
ANY path ANYWHERE within eight windows of it. Eight of the twelve lines pass through the room
centre, and the decoder was on a path about thirty percent of the time, so a dot hovering near the
centre was credited with every pass in the recording. The operator saw it in the animation before
any number showed it. That function is deleted, not kept.

WHAT A FOUND PASS IS NOW. The decoder occupied the CORRECT chain during the pass, that occupancy
reached the chain's exit zone no later than two seconds after the true pass end, and the decoder was
on the correct chain for at least half of the pass's labelled windows. Partial traversals and
occupancies of the wrong line are not finds; they are reported as what they are.

Everything here takes the decoder's committed output (state sequence, line name per window, xy per
window), the recording's truth, the motion gate's reading and the transition matrix that was used,
and returns one dict per recording. :func:`aggregate_pairing` combines recordings within ONE
pairing; cross-day and within-day are combined only by ``regime_split`` in the stage modules.
"""

from __future__ import annotations

import glob
import json
import math
import os
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.common import REPO, group_bootstrap, position_report
from pipeline.constrained.decoder import NEG

WINDOW_S = 2.0
EXIT_GRACE_S = 2.0          #: the exit zone must be reached within this of the true pass end
COVERAGE_MIN = 0.5          #: on the correct chain for at least this fraction of labelled windows
DIAGONALS = ("C_fwd", "C_rev", "D_fwd", "D_rev")
DIAGONAL_SHARE = 4.0 / 12.0
MOTION_THETA = 0.431
#: Where the decoder is drawn when it declines to answer, and therefore the comparator every
#: all-windows positional row is measured against. Amendment C2: the stage 1.3 re-baseline showed
#: cross-day all-windows error of 1.602 to 1.801 m against a centre guess of about 1.80 m, so the
#: decoder does not beat guessing the middle of the room cross-day, and no table said so.
CENTRE = (2.5, 2.5)


# --------------------------------------------------------------------------- truth helpers


def pass_anchor_times(rec) -> dict:
    """``pass_id -> (t_first_anchor, t_last_anchor)`` on the window time base, from the sidecar.

    Stage 0 established that ``t_start == anchor_times[0]`` and ``t_end == anchor_times[-1]`` on
    every pass, and that the window labels compare against the same base, so these are the true
    pass boundaries at full time resolution rather than at the one second lattice.
    """
    hits = glob.glob(os.path.join(REPO, "data", "room_*", f"session_{rec.session}",
                                  f"{rec.stem}.gt.json"))
    out = {}
    if hits:
        with open(hits[0], encoding="utf-8") as f:
            for p in json.load(f).get("passes", []):
                at = p.get("anchor_times") or []
                if len(at) >= 2:
                    out[int(p["pass_id"])] = (float(at[0]), float(at[-1]))
    # fall back to the window lattice for any pass the sidecar did not cover
    for pid, _nm, i0, i1 in rec.pass_spans():
        if pid not in out:
            w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
            if len(w):
                out[pid] = (float(rec.t0[w[0]]), float(rec.t0[w[-1]] + WINDOW_S))
    return out


def centre_times(rec) -> np.ndarray:
    return np.asarray(rec.t0, float) + WINDOW_S / 2.0


def occupancy_runs(names: np.ndarray) -> list:
    """Contiguous runs of the decoder on one line: ``(line, first, last)`` inclusive."""
    names = np.asarray(names).astype(str)
    runs, i, n = [], 0, len(names)
    while i < n:
        if not names[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and names[j + 1] == names[i]:
            j += 1
        runs.append((str(names[i]), int(i), int(j)))
        i = j + 1
    return runs


def audit_transitions(seq: np.ndarray, log_T: np.ndarray) -> int:
    """How many consecutive emissions the model itself scores as impossible. Zero on a committed
    track, by construction, or the decoder is emitting something it does not believe."""
    seq = np.asarray(seq, int)
    if len(seq) < 2:
        return 0
    return int(np.sum(log_T[seq[:-1], seq[1:]] <= NEG / 2))


def binomial_two_sided(k: int, n: int, p: float) -> float:
    """Exact two-sided binomial p-value (sum of outcomes at most as likely as the observed one).

    In log space: math.comb overflows a float once n passes about a thousand, and the regime-pooled
    occupancy count does, which killed stage 1 the first time it ran on all twelve pairings."""
    if n <= 0:
        return 1.0
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    lp = np.array([math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                   + i * math.log(p) + (n - i) * math.log1p(-p) for i in range(n + 1)])
    obs = lp[int(k)]
    return float(min(1.0, np.exp(lp[lp <= obs + 1e-12]).sum()))


# --------------------------------------------------------------------------- one recording


def recording_metrics(rec, dec: dict, st, log_T: np.ndarray, gate_e: np.ndarray,
                      exit_k: int = 1, held_out: Optional[set] = None,
                      revisions: Optional[Sequence[dict]] = None,
                      provisional_seq: Optional[np.ndarray] = None) -> dict:
    """The full corrected measurement for one decoded recording.

    ``dec`` is the decoder's committed output: ``seq`` (state per window, null states are any index
    at or beyond ``st.n_states``), ``names`` (line per window, '' off a line) and ``xy``.
    ``revisions`` is the display layer's list of ``{"window", "distance_m", "kind"}``; None means
    the arm has no display layer and the revision fields are reported as None rather than zero.
    """
    seq = np.asarray(dec["seq"], int)
    names = np.asarray(dec["names"]).astype(str)
    xy_hat = np.asarray(dec["xy"], float)
    n = len(seq)
    walking = np.asarray(gate_e, float) >= MOTION_THETA
    truth_line = np.where(rec.mode == "walk", rec.path_name.astype(str), "")
    labelled = (rec.mode == "walk") & np.isfinite(rec.xy).all(1)
    keys = rec.pass_keys()
    ct = centre_times(rec)
    anchors = pass_anchor_times(rec)
    runs = occupancy_runs(names)

    # which passes are scored (within-day: only the held-out ones)
    spans = rec.pass_spans()
    scored_pids = {pid for pid, _nm, _a, _b in spans
                   if held_out is None or f"{rec.participant}|{rec.session}|{pid}" in held_out}
    unscored_windows = np.zeros(n, bool)
    for pid, _nm, a, b in spans:
        if pid not in scored_pids:
            unscored_windows[a:b + 1] = True

    # ---- passes: strict found, coverage, exit, entry latency
    passes = []
    correct_run_ids = set()
    for pid, nm, a_full, b_full in spans:
        if pid not in scored_pids:
            continue
        walk_idx = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if not len(walk_idx):
            continue
        i0, i1 = int(walk_idx[0]), int(walk_idx[-1])
        t_s, t_e = anchors.get(pid, (float(rec.t0[i0]), float(rec.t0[i1] + WINDOW_S)))
        lab = np.flatnonzero(labelled & (rec.pass_id == pid))
        n_lab = int(len(lab))
        coverage = float(np.mean(names[lab] == nm)) if n_lab else 0.0
        c_runs = [(ri, r) for ri, r in enumerate(runs) if r[0] == nm and r[1] <= i1 and r[2] >= i0]
        found = exit_reached = exit_in_time = False
        entry_latency = None
        first_correct = None
        clean_entry = None
        if c_runs:
            for ri, _r in c_runs:
                correct_run_ids.add(ri)
            # D4(b): was the chain ENTERED during the pass, or already occupied when it began?
            # A negative entry latency means the latter, and with tens of transit false fires per
            # recording that is a false-fire artefact rather than fast detection.
            earliest = min(r[1] for _ri, r in c_runs)
            clean_entry = bool(earliest >= i0)
            # the occupancy that overlaps the pass most is the one judged for exit
            ri, (_ln, ra, rb) = max(c_runs, key=lambda x: min(x[1][2], i1) - max(x[1][1], i0))
            c0, c1 = st.slice_of[nm]
            exit_reached = bool(seq[rb] >= c1 - max(1, int(exit_k)))
            exit_in_time = bool(ct[rb] <= t_e + EXIT_GRACE_S)
            first_correct = int(min(r[1] for _ri, r in c_runs))
            entry_latency = float(ct[first_correct] - t_s)
            found = bool(coverage >= COVERAGE_MIN and exit_reached and exit_in_time)
        passes.append({
            "pass_id": int(pid), "line": nm, "first_walk_window": i0, "last_walk_window": i1,
            "t_start": t_s, "t_end": t_e, "n_labelled": n_lab, "coverage": round(coverage, 4),
            "correct_occupancy": bool(c_runs), "exit_reached": exit_reached,
            "exit_in_time": exit_in_time, "found": found, "entry_latency_s": entry_latency,
            "clean_entry": clean_entry,
            "first_correct_window": first_correct, "key": f"{rec.participant}|{rec.session}|{pid}",
        })

    # ---- every occupancy that is not a correct one, classified by what the person was doing
    false_occ = {"stationary": 0, "transit": 0, "wrong_line": 0}
    false_occ_windows = {"stationary": 0, "transit": 0, "wrong_line": 0}
    unscored_runs = 0
    per_line_occ = {nm: {"occupancies": 0, "correct_occupancies": 0} for nm in st.names}
    for ri, (ln, a, b) in enumerate(runs):
        per_line_occ.setdefault(ln, {"occupancies": 0, "correct_occupancies": 0})
        per_line_occ[ln]["occupancies"] += 1
        if ri in correct_run_ids:
            per_line_occ[ln]["correct_occupancies"] += 1
            continue
        if unscored_windows[a:b + 1].any():
            unscored_runs += 1
            continue
        w = slice(a, b + 1)
        tl = truth_line[w]
        if np.any((tl != "") & (tl != ln)):
            kind = "wrong_line"
        elif np.mean(walking[w]) >= 0.5:
            kind = "transit"
        else:
            kind = "stationary"
        false_occ[kind] += 1
        false_occ_windows[kind] += int(b - a + 1)

    # ---- null holding where nobody is walking a line
    dwell = rec.mode == "grid"
    on_chain = names != ""
    stationary = ~walking
    held = {
        "dwell_held_in_null_pct": float(100 * (~on_chain[dwell]).mean()) if dwell.any() else None,
        "stationary_held_in_null_pct": (float(100 * (~on_chain[stationary]).mean())
                                        if stationary.any() else None),
        "transit_held_in_null_pct": (float(100 * (~on_chain[walking & (truth_line == "")]).mean())
                                     if (walking & (truth_line == "")).any() else None),
    }

    # ---- per line, predicted against true
    per_line = {}
    for nm in st.names:
        tp_ = [p for p in passes if p["line"] == nm]
        per_line[nm] = {
            "true_passes": len(tp_), "found": int(sum(p["found"] for p in tp_)),
            "recall_pct": (100.0 * sum(p["found"] for p in tp_) / len(tp_)) if tp_ else None,
            "occupancies": per_line_occ[nm]["occupancies"],
            "correct_occupancies": per_line_occ[nm]["correct_occupancies"],
            "precision_pct": (100.0 * per_line_occ[nm]["correct_occupancies"]
                              / per_line_occ[nm]["occupancies"]) if per_line_occ[nm]["occupancies"] else None,
        }
    n_occ = sum(v["occupancies"] for v in per_line.values())
    n_diag = sum(per_line[d]["occupancies"] for d in DIAGONALS if d in per_line)
    diag = {"predicted_occupancies": n_occ, "on_diagonals": n_diag,
            "diagonal_share_pct": (100.0 * n_diag / n_occ) if n_occ else None,
            "protocol_share_pct": 100.0 * DIAGONAL_SHARE,
            "true_diagonal_share_pct": (100.0 * sum(1 for p in passes if p["line"] in DIAGONALS)
                                        / len(passes)) if passes else None,
            "binomial_p": binomial_two_sided(n_diag, n_occ, DIAGONAL_SHARE) if n_occ else None}

    # ---- positional, two ways, as raw arrays so a pairing can pool and bootstrap once
    scored_lab = labelled & ~unscored_windows
    dirs = np.zeros((n, 2))
    for i in np.flatnonzero(scored_lab):
        dirs[i] = st.direction_of(str(rec.path_name[i]))
    on_path_sel = scored_lab & on_chain
    centre_pred = np.tile(np.asarray(CENTRE, float), (int(scored_lab.sum()), 1))
    positional = {
        "all_windows": {"pred": xy_hat[scored_lab], "true": rec.xy[scored_lab],
                        "dirs": dirs[scored_lab], "keys": keys[scored_lab]},
        "on_path_only": {"pred": xy_hat[on_path_sel], "true": rec.xy[on_path_sel],
                         "dirs": dirs[on_path_sel], "keys": keys[on_path_sel]},
        # C2: the same evaluation windows, answered by always saying "the middle of the room"
        "centre_guess": {"pred": centre_pred, "true": rec.xy[scored_lab],
                         "dirs": dirs[scored_lab], "keys": keys[scored_lab]},
        "n_all": int(scored_lab.sum()), "n_on_path": int(on_path_sel.sum()),
    }

    # ---- window-level precision and recall, LINE-AWARE
    tp = int(np.sum(on_chain & (truth_line != "") & (names == truth_line) & ~unscored_windows))
    fp = int(np.sum(on_chain & (names != truth_line) & ~unscored_windows))
    fn = int(np.sum(~on_chain & (truth_line != "") & ~unscored_windows))

    # ---- revisions, from the display layer when there is one
    rev = None
    if revisions is not None:
        per_pass, dists, span = [], [], 0
        for p in passes:
            lo, hi = p["first_walk_window"] - 8, p["last_walk_window"] + 8
            span = max(span, hi - lo + 1)
            mine = [r for r in revisions if lo <= int(r.get("window", -1)) <= hi]
            per_pass.append(len(mine))
            dists += [float(r.get("distance_m", 0.0)) for r in mine]
        rev = {"revisions_per_pass_mean": float(np.mean(per_pass)) if per_pass else None,
               "catchup_distance_mean_m": float(np.mean(dists)) if dists else None,
               "catchup_distance_median_m": float(np.median(dists)) if dists else None,
               "catchup_distance_p90_m": float(np.percentile(dists, 90)) if dists else None,
               "n_revisions": int(len(revisions)),
               # D4(a): the denominator, stated, because "per pass" was read as "per four windows"
               "counted_over_windows": int(span),
               "revisions_per_window": (float(np.mean(per_pass)) / span) if (per_pass and span) else None,
               "definition": ("a window where the committed LINE differs from the displayed line, or "
                              "where both are on the same line more than one state (0.25 m) apart; "
                              "summed over the pass span plus 8 windows either side, not over the "
                              "pass's own walk windows")}

    lat = [p["entry_latency_s"] for p in passes if p["found"]]
    lat_any = [p["entry_latency_s"] for p in passes if p["entry_latency_s"] is not None]
    lat_clean = [p["entry_latency_s"] for p in passes if p["found"] and p.get("clean_entry")]
    lat_occ = [p["entry_latency_s"] for p in passes if p["found"] and p.get("clean_entry") is False]
    out = {
        "recording": f"{rec.session}/{rec.stem}", "n_windows": n,
        "passes": passes,
        "strict": {
            "n_passes": len(passes), "n_found": int(sum(p["found"] for p in passes)),
            "found_pct": (100.0 * sum(p["found"] for p in passes) / len(passes)) if passes else None,
            "coverage_mean": float(np.mean([p["coverage"] for p in passes])) if passes else None,
            "exit_reached_pct": (100.0 * sum(p["exit_reached"] for p in passes) / len(passes)) if passes else None,
            "correct_occupancy_pct": (100.0 * sum(p["correct_occupancy"] for p in passes) / len(passes)) if passes else None,
            "partial_pct": (100.0 * sum(p["correct_occupancy"] and not p["found"] for p in passes) / len(passes)) if passes else None,
        },
        "entry_latency": {
            "median_s": float(np.median(lat)) if lat else None,
            "p90_s": float(np.percentile(lat, 90)) if lat else None,
            "n_found": len(lat),
            "median_s_any_correct": float(np.median(lat_any)) if lat_any else None,
            "n_any_correct": len(lat_any),
            "values": [round(v, 3) for v in lat],
            # D4(b): NEVER quote the pooled figure as responsiveness
            "clean_entry_median_s": float(np.median(lat_clean)) if lat_clean else None,
            "n_clean_entry": len(lat_clean),
            "already_occupying_median_s": float(np.median(lat_occ)) if lat_occ else None,
            "n_already_occupying": len(lat_occ),
            "clean_entry_pct": (100.0 * len(lat_clean) / max(len(lat_clean) + len(lat_occ), 1)),
        },
        "revisions": rev,
        "false_occupancies": false_occ,
        "false_occupancy_windows": false_occ_windows,
        "unscored_occupancies": unscored_runs,
        "held": held,
        "per_line": per_line,
        "diagonal": diag,
        "positional": positional,
        "window": {"tp": tp, "fp": fp, "fn": fn,
                   "precision_pct": 100.0 * tp / max(tp + fp, 1),
                   "recall_pct": 100.0 * tp / max(tp + fn, 1)},
        "audit": {"committed_impossible": audit_transitions(seq, log_T),
                  "provisional_impossible": (audit_transitions(provisional_seq, log_T)
                                             if provisional_seq is not None else None)},
    }
    return out


def compat_segmentation(rec, dec: dict, st, gate_e: np.ndarray, exit_k: int = 1,
                        log_T: Optional[np.ndarray] = None, held_out: Optional[set] = None) -> dict:
    """The few flat keys the finished batch's stage modules print, computed under the CORRECTED
    definitions. Exists so those modules still import and run; nothing new should call it."""
    from pipeline.constrained.decoder import transition_matrix
    if log_T is None:
        log_T = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=exit_k)
    m = recording_metrics(rec, dec, st, log_T, gate_e, exit_k, held_out)
    fo = m["false_occupancies"]
    return {
        "n_passes": m["strict"]["n_passes"], "passes_found": m["strict"]["n_found"],
        "passes_missed": m["strict"]["n_passes"] - m["strict"]["n_found"],
        "false_passes": fo["stationary"] + fo["transit"] + fo["wrong_line"],
        "false_stationary": fo["stationary"], "false_transit": fo["transit"],
        "false_wrong_line": fo["wrong_line"],
        "window_precision_pct": m["window"]["precision_pct"],
        "window_recall_pct": m["window"]["recall_pct"],
        "dwell_held_in_null_pct": m["held"]["dwell_held_in_null_pct"],
        "transit_held_in_null_pct": m["held"]["transit_held_in_null_pct"],
        "stationary_held_in_null_pct": m["held"]["stationary_held_in_null_pct"],
        "impossible_transitions": m["audit"]["committed_impossible"],
        "definition": "STRICT: correct chain, exit zone reached within 2 s of the true end, "
                      "on the correct chain for at least half the labelled windows",
    }


# --------------------------------------------------------------------------- one pairing


def aggregate_pairing(per_recording: Sequence[dict], tag: str = "") -> dict:
    """Combine the recordings of ONE pairing. Never call this across pairings."""
    recs = [r for r in per_recording if r]
    passes = [p for r in recs for p in r["passes"]]
    n_pass = len(passes)
    found = np.array([p["found"] for p in passes], float)
    pkeys = np.array([p["key"] for p in passes])
    lo, hi = group_bootstrap(found, pkeys, stat=np.mean) if n_pass >= 2 else (np.nan, np.nan)
    lat = [p["entry_latency_s"] for p in passes if p["found"]]
    lat_any = [p["entry_latency_s"] for p in passes if p["entry_latency_s"] is not None]
    n_rec = max(len(recs), 1)
    fo = {k: sum(r["false_occupancies"][k] for r in recs) for k in ("stationary", "transit", "wrong_line")}
    per_line = {}
    lines = sorted({ln for r in recs for ln in r["per_line"]})
    for ln in lines:
        tp_ = sum(r["per_line"][ln]["true_passes"] for r in recs)
        fd = sum(r["per_line"][ln]["found"] for r in recs)
        oc = sum(r["per_line"][ln]["occupancies"] for r in recs)
        co = sum(r["per_line"][ln]["correct_occupancies"] for r in recs)
        per_line[ln] = {"true_passes": tp_, "found": fd, "recall_pct": (100.0 * fd / tp_) if tp_ else None,
                        "occupancies": oc, "correct_occupancies": co,
                        "precision_pct": (100.0 * co / oc) if oc else None}
    n_occ = sum(v["occupancies"] for v in per_line.values())
    n_diag = sum(per_line[d]["occupancies"] for d in DIAGONALS if d in per_line)
    true_diag = sum(1 for p in passes if p["line"] in DIAGONALS)
    pos = {}
    for key in ("all_windows", "on_path_only", "centre_guess"):
        parts = [r["positional"][key] for r in recs if r["positional"][key]["pred"].shape[0]]
        if parts:
            pred = np.concatenate([q["pred"] for q in parts]); true = np.concatenate([q["true"] for q in parts])
            dirs = np.concatenate([q["dirs"] for q in parts]); keys = np.concatenate([q["keys"] for q in parts])
            pos[key] = position_report(pred, true, dirs, keys, f"{tag}:{key}")
        else:
            pos[key] = None
    tp = sum(r["window"]["tp"] for r in recs); fp = sum(r["window"]["fp"] for r in recs)
    fn = sum(r["window"]["fn"] for r in recs)
    rev_rows = [r["revisions"] for r in recs if r.get("revisions")]
    held = {}
    for k in ("dwell_held_in_null_pct", "stationary_held_in_null_pct", "transit_held_in_null_pct"):
        vals = [r["held"][k] for r in recs if r["held"].get(k) is not None]
        held[k] = float(np.mean(vals)) if vals else None
    return {
        "tag": tag, "n_recordings": len(recs), "n_passes": n_pass,
        "strict": {
            "found_pct": (100.0 * found.mean()) if n_pass else None,
            "found_ci_pct": [100.0 * lo, 100.0 * hi] if n_pass >= 2 else [None, None],
            "n_found": int(found.sum()),
            "coverage_mean": float(np.mean([p["coverage"] for p in passes])) if passes else None,
            "exit_reached_pct": (100.0 * np.mean([p["exit_reached"] for p in passes])) if passes else None,
            "correct_occupancy_pct": (100.0 * np.mean([p["correct_occupancy"] for p in passes])) if passes else None,
            "partial_pct": (100.0 * np.mean([p["correct_occupancy"] and not p["found"] for p in passes])) if passes else None,
        },
        "entry_latency": {"median_s": float(np.median(lat)) if lat else None,
                          "p90_s": float(np.percentile(lat, 90)) if lat else None, "n_found": len(lat),
                          "median_s_any_correct": float(np.median(lat_any)) if lat_any else None},
        "revisions": ({"revisions_per_pass_mean": float(np.mean([r["revisions_per_pass_mean"] for r in rev_rows
                                                                 if r["revisions_per_pass_mean"] is not None] or [np.nan])),
                       "catchup_distance_mean_m": float(np.mean([r["catchup_distance_mean_m"] for r in rev_rows
                                                                 if r["catchup_distance_mean_m"] is not None] or [np.nan]))}
                      if rev_rows else None),
        "false_occupancies_per_recording": {k: v / n_rec for k, v in fo.items()},
        "false_occupancies_total": fo,
        "held": held,
        "per_line": per_line,
        "diagonal": {"predicted_occupancies": n_occ, "on_diagonals": n_diag,
                     "diagonal_share_pct": (100.0 * n_diag / n_occ) if n_occ else None,
                     "true_diagonal_share_pct": (100.0 * true_diag / n_pass) if n_pass else None,
                     "protocol_share_pct": 100.0 * DIAGONAL_SHARE,
                     "binomial_p": binomial_two_sided(n_diag, n_occ, DIAGONAL_SHARE) if n_occ else None,
                     "over_predicted": bool(n_occ and n_diag / n_occ > DIAGONAL_SHARE
                                            and binomial_two_sided(n_diag, n_occ, DIAGONAL_SHARE) < 0.05)},
        "positional": pos,
        "window": {"tp": tp, "fp": fp, "fn": fn, "precision_pct": 100.0 * tp / max(tp + fp, 1),
                   "recall_pct": 100.0 * tp / max(tp + fn, 1)},
        "audit": {"committed_impossible": int(sum(r["audit"]["committed_impossible"] for r in recs)),
                  "provisional_impossible": (int(sum(r["audit"]["provisional_impossible"] or 0 for r in recs))
                                             if any(r["audit"].get("provisional_impossible") is not None for r in recs) else None)},
    }


def flat(agg: dict) -> dict:
    """The headline scalars of one pairing, for regime_split and for tables."""
    pos_all = (agg.get("positional") or {}).get("all_windows") or {}
    pos_on = (agg.get("positional") or {}).get("on_path_only") or {}
    pos_c = (agg.get("positional") or {}).get("centre_guess") or {}
    a_m = (pos_all.get("total") or {}).get("median_m")
    c_m = (pos_c.get("total") or {}).get("median_m")
    return {
        # C2: every all-windows row carries its centre-guess comparator and an explicit verdict
        "all_windows_centre_m": c_m,
        "beats_centre": (None if (a_m is None or c_m is None) else bool(a_m < c_m)),
        "centre_margin_m": (None if (a_m is None or c_m is None) else float(c_m - a_m)),
        "found_pct": agg["strict"]["found_pct"],
        "found_ci_hi": (agg["strict"]["found_ci_pct"] or [None, None])[1],
        "coverage_mean": agg["strict"]["coverage_mean"],
        "exit_reached_pct": agg["strict"]["exit_reached_pct"],
        "partial_pct": agg["strict"]["partial_pct"],
        "entry_latency_median_s": agg["entry_latency"]["median_s"],
        "entry_latency_p90_s": agg["entry_latency"]["p90_s"],
        "false_stationary": agg["false_occupancies_per_recording"]["stationary"],
        "false_transit": agg["false_occupancies_per_recording"]["transit"],
        "false_wrong_line": agg["false_occupancies_per_recording"]["wrong_line"],
        "dwell_held_pct": agg["held"]["dwell_held_in_null_pct"],
        "stationary_held_pct": agg["held"]["stationary_held_in_null_pct"],
        "all_windows_total_m": (pos_all.get("total") or {}).get("median_m"),
        "all_windows_total_ci_hi": ((pos_all.get("total") or {}).get("median_ci") or [None, None])[1],
        "on_path_total_m": (pos_on.get("total") or {}).get("median_m"),
        "on_path_along_m": (pos_on.get("along") or {}).get("median_m"),
        "on_path_cross_m": (pos_on.get("cross") or {}).get("median_m"),
        "window_precision_pct": agg["window"]["precision_pct"],
        "window_recall_pct": agg["window"]["recall_pct"],
        "diagonal_share_pct": agg["diagonal"]["diagonal_share_pct"],
        "diagonal_p": agg["diagonal"]["binomial_p"],
        "committed_impossible": agg["audit"]["committed_impossible"],
        "revisions_per_pass": (agg.get("revisions") or {}).get("revisions_per_pass_mean"),
        "catchup_m": (agg.get("revisions") or {}).get("catchup_distance_mean_m"),
    }


def compat_gate_only(rec, on_path_pred: np.ndarray) -> dict:
    """For the finished batch's gate comparator, which has no decoder: null-holding fields only."""
    on = np.asarray(on_path_pred, bool)
    dwell = rec.mode == "grid"
    return {"n_passes": len(rec.pass_spans()), "passes_found": None, "false_passes": None,
            "dwell_held_in_null_pct": float(100 * (~on[dwell]).mean()) if dwell.any() else None,
            "transit_held_in_null_pct": float(100 * (~on[rec.mode == "idle"]).mean())
            if (rec.mode == "idle").any() else None,
            "window_precision_pct": None, "window_recall_pct": None,
            "definition": "gate only; no line, so no pass can be found under the strict definition"}
