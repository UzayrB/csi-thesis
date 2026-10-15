"""STAGE 10 of the decoder rebuild: the BOUNDARIES-GIVEN tracking demonstration.

Requested by the operator on 2026-09-17: "with the boundaries, like when it starts, given can it not
follow and track the user along the paths accurately. Do not really want it to just say which path
was walked. Low-key useless as a live demo."

WHAT THIS GRANTS THE SYSTEM, and it is exactly one thing: WHEN each walk starts and ends. It does
NOT grant which line. The decoder still chooses among the twelve and still has to hold position
along its choice, window by window, and the render shows it doing so at the participant's real pace.

WHY THIS IS THE RIGHT DEMONSTRATION. Detection is what the tracker is bad at and position is what it
is good at, and the unbounded demo conflates them. Measured offline: on the windows where it claims
a line it holds position to 0.363 m within-day and 0.695 m cross-day, sub-cell on a 1 m grid, while
the unbounded live decoder finds only 4 of 120 passes across a day boundary. Granting the boundaries
separates the two, so the viewer sees the part that works and the report still carries the part that
does not.

WHAT IT MUST NOT DO. It must not look better than it is. Every pass is marked correct or wrong on
screen, the wrong-line passes are rendered rather than dropped, and the notes carry the full twelve
line table so that naming the strong routes is not cherry-picking.

The decode is identify_with_boundaries' own: a Viterbi over the twelve chains alone, with no null
state, inside each pass span. That function already computes this track and then keeps only the
modal line name; here the track itself is what is drawn.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.constrained.common import (E_POST, REPORT_DIR, RUN_DIR, fmt, status, tag_of)
from pipeline.constrained.rebuild_common import (emission_choice, findings, headline,
                                                 load_results, save_results, stage_dir)

STAGE = "rb10_bounded_demo"
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "runs", "constrained", "demo_bounded")
#: cross-day is the honest headline pairing; the within-day one is rendered too and LABELLED, because
#: within-day the model has seen 96 of that session's 120 passes and a viewer must be told so
PAIRINGS = (("s0102_to_s03", ("01", "02"), ("03",), False),
            ("within_s03", ("03",), ("03",), True))

EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
CENTRAL = ("A_fwd", "A_rev", "B_fwd", "B_rev")
DIAGONAL = ("C_fwd", "C_rev", "D_fwd", "D_rev")


def forced_align(e_path: np.ndarray, st, line: str, lo: int, hi: int):
    """Viterbi along ONE chain with both ends pinned: first cell at lo, last cell at hi.

    PHASE 4 of the 2026-09-18 brief. Standard forced alignment, no new parameters. The emissions
    still decide which chain wins and where the pace speeds up or slows down in between; what is
    imposed is only that a walk which was declared to start and end does in fact run the length of
    the line, which is a fact the bounded mode is already granted and was simply not using.

    Returns (states, score) in GLOBAL state indices, or (None, -inf) if the span is too short.
    """
    from pipeline.constrained.decoder import NEG, along_log_score
    a, b = st.slice_of[line]
    n, S = hi - lo + 1, b - a
    if n < 1 or S < 1:
        return None, float("-inf")
    if n == 1:
        return (np.array([a], dtype=int), float(e_path[lo, a])) if S == 1 else (None, float("-inf"))
    T = along_log_score(np.asarray(st.s_of)[a:b], "tight")
    em = e_path[lo:hi + 1, a:b]
    dp = np.full((n, S), NEG)
    back = np.zeros((n, S), dtype=np.int32)
    dp[0, 0] = em[0, 0]                       # pinned: the chain's first cell at the start time
    for k in range(1, n):
        m = dp[k - 1][:, None] + T
        back[k] = m.argmax(0)
        dp[k] = m.max(0) + em[k]
    end = S - 1                               # pinned: the chain's last cell at the end time
    if not np.isfinite(dp[-1, end]):
        return None, float("-inf")
    out = np.zeros(n, dtype=np.int32)
    out[-1] = end
    for k in range(n - 1, 0, -1):
        out[k - 1] = back[k, out[k]]
    return out + a, float(dp[-1, end])


def _end_windows(rec, pid, line):
    """The window indices the protocol rule labels for this pass: one at each end, or fewer."""
    from pipeline.constrained.dataset import _end_label_mask
    try:
        idx, _lab = _end_label_mask(rec, str(rec.session), str(rec.stem))
    except Exception:                                                  # noqa: BLE001
        return []
    if not len(idx):
        return []
    w = set(np.flatnonzero(rec.pass_id == int(pid)).tolist())
    return [int(i) for i in idx if int(i) in w]


def bounded_track(e_path: np.ndarray, rec, st, held_out=None, pin_end: bool = False,
                  full_span: bool = False, with_ends: bool = False) -> dict:
    """The track the decoder produces when it is told WHEN each walk happens, but not which line.

    Returns a full-length state sequence (null outside the passes) plus a per-pass verdict. The
    Viterbi is over the twelve chains ALONE, with_null=False, exactly as identify_with_boundaries
    does it, so the demonstration and the 63.2 / 86.1 percent identification figures are the same
    computation and cannot drift apart.
    """
    from pipeline.constrained.decoder import (NEG, along_log_score, decoded_paths,
                                              decoded_xy, transition_matrix, viterbi)
    lT = transition_matrix(st, "tight", with_null=False)
    n = len(rec)
    seq = np.full(n, st.n_states, dtype=int)          # null everywhere to begin with
    passes = []
    # THE RAMP EXTENSION IS DELETED, 2026-09-18, not disabled. It advanced the dot
    # through the walk_edge windows and the substitution test showed it was dead
    # reckoning: removing the CSI changed 0.0 percent of its answers and swapping in
    # another participant's changed 0.6 percent. Nothing in this decoder now places a
    # position that the radio did not decide.
    for pid, nm, _a, _b in rec.pass_spans():
        key = f"{rec.participant}|{rec.session}|{pid}"
        if held_out is not None and key not in held_out:
            continue
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if not len(w):
            continue
        lo, hi = int(w[0]), int(w[-1])
        if with_ends and not pin_end and not full_span:
            # THE LINE COMES FROM THE CORE. Measured on s01_to_s02: choosing it over the whole
            # interval instead costs 28 points, 75.0 down to 46.7, because the end windows are
            # decoded from the radio but decoded BADLY, at about 2.2 m. The brief's rule 3.1 is
            # exactly this case: if the whole-interval choice changes decisions, use the core.
            s_core = viterbi(e_path[lo:hi + 1], lT)
            names = decoded_paths(s_core, st)
            vals, counts = np.unique(names[names != ""], return_counts=True)
            chosen = str(vals[counts.argmax()]) if len(vals) else ""
            ok = chosen == nm
            seq[lo:hi + 1] = s_core
            # THE POSITION on the end windows is then decoded along that already-chosen chain,
            # from the emissions the retrained heads now provide there. This is NOT the deleted
            # pacer: that one ignored the radio entirely, 0.0 percent of its answers changing when
            # the CSI was removed. This one is checked by the same substitution test in re3_bounded
            # and must move with another participant's CSI or it does not ship.
            ends = _end_windows(rec, pid, nm)
            if chosen and ends:
                a0, b0 = st.slice_of[chosen]
                T = along_log_score(np.asarray(st.s_of)[a0:b0], "tight")
                for i in sorted([x for x in ends if x > hi]):
                    cur = int(seq[min(i - 1, hi)]) - a0 if seq[min(i - 1, hi)] < st.n_states else 0
                    cur = int(np.clip(cur, 0, b0 - a0 - 1))
                    sc = T[cur] + e_path[i, a0:b0]
                    sc[:cur] = NEG
                    if np.isfinite(sc).any():
                        seq[i] = int(np.argmax(sc)) + a0
                for i in sorted([x for x in ends if x < lo], reverse=True):
                    nxt = int(seq[max(i + 1, lo)]) - a0 if seq[max(i + 1, lo)] < st.n_states else 0
                    nxt = int(np.clip(nxt, 0, b0 - a0 - 1))
                    sc = T[:, nxt] + e_path[i, a0:b0]
                    sc[nxt + 1:] = NEG
                    if np.isfinite(sc).any():
                        seq[i] = int(np.argmax(sc)) + a0
            s = seq[lo:hi + 1]
        elif full_span and not pin_end:
            d_lo, d_hi = int(_a), int(_b)
            sv = viterbi(e_path[d_lo:d_hi + 1], lT)
            seq[d_lo:d_hi + 1] = sv
            names = decoded_paths(sv, st)
            vals, counts = np.unique(names[names != ""], return_counts=True)
            chosen = str(vals[counts.argmax()]) if len(vals) else ""
            ok = chosen == nm
            s = seq[lo:hi + 1]
        elif pin_end:
            # the declared walk, whole: _a and _b are the pass boundaries this mode is given
            d_lo, d_hi = int(_a), int(_b)
            best, best_s, best_nm = None, float("-inf"), ""
            for cand in st.names:
                sts, sc = forced_align(e_path, st, cand, d_lo, d_hi)
                if sts is not None and sc > best_s:
                    best, best_s, best_nm = sts, sc, cand
            if best is None:
                continue
            seq[d_lo:d_hi + 1] = best
            chosen = best_nm
            ok = chosen == nm
            # scored on the SAME windows as the unpinned mode, so the two are comparable
            s = seq[lo:hi + 1]
        else:
            s = viterbi(e_path[lo:hi + 1], lT)
            seq[lo:hi + 1] = s
            names = decoded_paths(s, st)
            vals, counts = np.unique(names[names != ""], return_counts=True)
            chosen = str(vals[counts.argmax()]) if len(vals) else ""
            ok = chosen == nm
        xy_hat = decoded_xy(s, st)
        truth = rec.xy[lo:hi + 1]
        good = np.isfinite(truth).all(1) & np.isfinite(xy_hat).all(1)
        err = (float(np.median(np.linalg.norm(xy_hat[good] - truth[good], axis=1)))
               if good.any() else None)
        passes.append({"pass_id": int(pid), "true_line": nm, "chosen_line": chosen,
                       "found": bool(ok), "median_error_m": err,
                       "n_windows": hi - lo + 1, "start_window": lo})
    return {"seq": seq, "passes": passes}


def family_of(line: str) -> str:
    return "edge" if line in EDGE else ("central" if line in CENTRAL else "diagonal")


def per_line_table(all_passes: list) -> dict:
    out = {}
    for p in all_passes:
        o = out.setdefault(p["true_line"], {"n": 0, "correct": 0, "errs": []})
        o["n"] += 1
        o["correct"] += int(p["found"])
        if p["found"] and p["median_error_m"] is not None:
            o["errs"].append(p["median_error_m"])
    for ln, o in out.items():
        o["accuracy_pct"] = 100.0 * o["correct"] / o["n"] if o["n"] else None
        o["median_error_m_when_correct"] = (float(np.median(o["errs"])) if o["errs"] else None)
        o.pop("errs")
        o["family"] = family_of(ln)
    return out


def write_notes(RES: dict) -> str:
    """The notes, as a function of the saved results only, so they regenerate without re-rendering."""
    L = ["# Demonstration notes: the boundaries-given tracker", "",
         "The system is told ONE thing it is not told in the live demonstration: **when each walk "
         "starts and ends**. It is NOT told which line. It still chooses among the twelve and still "
         "has to hold position along its choice, window by window, at the participant's real pace.", "",
         "## Why this demonstration exists", "",
         "Detection and position are different problems and the unbounded demonstration conflates "
         "them. The tracker is poor at detecting that a walk began and good at following a line once "
         "it is on one. Granting the boundaries separates the two. The unbounded live figures stay in "
         "the report; nothing here replaces them.", ""]
    for tag, v in (RES.get("pairings") or {}).items():
        lab = "WITHIN-DAY" if v.get("within") else "CROSS-DAY"
        L += [f"## {tag} ({lab})", ""]
        if v.get("within"):
            L += ["> **Read this one with care.** Within a day the model was fitted on 96 of that "
                  "session's 120 passes. Only the held-out passes are scored and rendered here, but "
                  "the session is not new to the model. The cross-day pairing is the honest headline.",
                  ""]
        L += [f"- **{v['n_correct']} of {v['n_passes']} passes identified correctly "
              f"({fmt(v['accuracy_pct'], 1)} percent).**",
              f"- Median position error when it chose the right line: "
              f"**{fmt(v.get('median_error_m_when_correct'), 3)} m**, on a 1 m grid.",
              f"- Renders: `{os.path.relpath(DEMO_DIR, os.path.dirname(REPORT_DIR))}`", "",
              "| line | family | identified | median error when right |", "|---|---|---|---|"]
        for ln in EDGE + CENTRAL + DIAGONAL:
            o = (v.get("per_line") or {}).get(ln)
            if not o:
                continue
            L.append(f"| {ln} | {o['family']} | {o['correct']}/{o['n']} "
                     f"({fmt(o['accuracy_pct'], 1)} %) | "
                     f"{fmt(o.get('median_error_m_when_correct'), 3)} m |")
        L += [""]
    L += ["## What to say", "",
          "- \"It is told when a walk happens. It is not told which of the twelve lines it is.\"",
          "- \"When it picks the right line it follows the person to about a third of a metre "
          "within a day, and about seven tenths across days. The grid cells are a metre.\"",
          "- \"The passes it gets wrong are in the video too, marked wrong. It commits to the wrong "
          "line and follows that one confidently.\"", "",
          "## What NOT to say", "",
          "- ~~\"This is the live system.\"~~ It is not. The live system must also detect that a walk "
          "began, and at that it finds 4 of 120 passes across days. That figure stands.",
          "- ~~Quoting only the strong routes.~~ The full twelve line table is above and goes with "
          "any claim about the diagonals.", ""]
    out = os.path.join(REPORT_DIR, "DEMO_NOTES_BOUNDED.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return out


def main() -> int:
    from pipeline.constrained import paths as P
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.dataset import held_out_passes, sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    from pipeline.constrained.rb7_demo import render, sidecar_for
    from pipeline.constrained.recordings import load_meta
    os.makedirs(DEMO_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    stage_dir(STAGE)
    t_start = time.time()
    st, paths = P.states(), P.load_paths()
    kind, alpha, _src = emission_choice()
    status(f"{STAGE} START: boundaries-given tracking, emission {kind} alpha {alpha}")
    RES = {"stage": STAGE, "emission": {"kind": kind, "alpha": alpha},
           "grants": "the pass spans only, never the line", "pairings": {}, "failures": []}

    for tag, tr_s, te_s, within in PAIRINGS:
        pp = posterior_path(tag, 25, E_POST, 0)
        if not os.path.exists(pp):
            RES["failures"].append(f"{tag}: no posteriors at {os.path.relpath(pp)}")
            status(f"  {tag}: SKIPPED, no posteriors")
            continue
        try:
            held = held_out_passes(tr_s, te_s, within)
            marginal = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
                        if kind == "scaled" else None)
            all_passes, rendered = [], {}
            for stem, b in read_full_posteriors(pp).items():
                rec = load_meta(te_s[0], stem)
                prob = b["prob"].astype(float)
                e = (cell_emission(prob, st.xy, 25) if marginal is None
                     else scaled_cell_emission(prob, st.xy, 25, marginal, alpha=alpha))
                bt = bounded_track(e, rec, st, held)
                if not bt["passes"]:
                    continue
                all_passes += bt["passes"]
                metrics = {"passes": [{"pass_id": p["pass_id"], "found": p["found"]}
                                      for p in bt["passes"]]}
                base = os.path.join(DEMO_DIR, f"{stem}_{tag}_bounded")
                nok = sum(p["found"] for p in bt["passes"])
                rendered[stem] = render(stem, rec, sidecar_for(stem), bt["seq"], bt["seq"], st,
                                        paths, metrics, base,
                                        f"boundaries given, {nok}/{len(bt['passes'])} lines correct")
                status(f"    {stem[:30]:30s} {nok}/{len(bt['passes'])} correct")
            n_ok = sum(p["found"] for p in all_passes)
            errs = [p["median_error_m"] for p in all_passes
                    if p["found"] and p["median_error_m"] is not None]
            RES["pairings"][tag] = {
                "within": within, "n_passes": len(all_passes), "n_correct": n_ok,
                "accuracy_pct": 100.0 * n_ok / len(all_passes) if all_passes else None,
                "median_error_m_when_correct": float(np.median(errs)) if errs else None,
                "per_line": per_line_table(all_passes), "renders": rendered,
                "passes": all_passes}
            status(f"  {tag:14s} {n_ok}/{len(all_passes)} correct "
                   f"({100.0 * n_ok / max(len(all_passes), 1):.1f}%), median error when right "
                   f"{fmt(RES['pairings'][tag]['median_error_m_when_correct'], 3)} m")
        except Exception as exc:                          # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": f"{type(exc).__name__}: {exc}",
                                    "trace": traceback.format_exc()[-1200:]})
            status(f"  {tag}: FAILED {type(exc).__name__}: {exc}")
        save_results(STAGE, RES)

    RES["notes"] = os.path.relpath(write_notes(RES), os.path.dirname(REPORT_DIR))
    RES["minutes"] = round((time.time() - t_start) / 60.0, 1)
    save_results(STAGE, RES)
    cross = (RES["pairings"].get("s0102_to_s03") or {})
    headline(f"STAGE 10: boundaries-given tracking. Cross-day {cross.get('n_correct')} of "
             f"{cross.get('n_passes')} lines identified ({fmt(cross.get('accuracy_pct'), 1)} percent), "
             f"median position error when right {fmt(cross.get('median_error_m_when_correct'), 3)} m.")
    findings(10, not RES["failures"], (
        f"The boundaries-given demonstration. The system is granted the pass spans and NOTHING else: "
        f"it still chooses among the twelve lines and still holds position along its choice. This "
        f"separates detection, which the tracker is bad at, from position, which it is good at, and "
        f"the unbounded live figures are unaffected and stay in the report. Cross-day "
        f"{cross.get('n_correct')} of {cross.get('n_passes')} lines correct at "
        f"{fmt(cross.get('median_error_m_when_correct'), 3)} m median error when right. Wrong-line "
        f"passes are rendered and marked, not dropped, and the notes carry the full twelve line table "
        f"so that naming the strong routes is not cherry-picking."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0 if not RES["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
