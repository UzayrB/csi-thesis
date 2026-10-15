"""pd_render: the demonstration videos of the FINAL tracker on A3 and B2 (29 September 2026, QUEUE item 3).

Rendered under `reports/tracking/render-rules.md` in full:
  - V1: the display runs exactly 2.0 s behind real time;
  - rule 6 and V2: red and green appear on the same frame, at the delayed press;
  - V3: the lock is read at press + 2.0 s on every walk;
  - rule 1a arm C: the lock is final apart from at most one display-only switch;
  - rule 1b: the end text names the committed decision;
  - rule 2 and 2a: nothing is projected; the one exception is the press anchor;
  - rule 3: the delay is stated on screen;
  - rule 4: decoded accuracy and display offset are kept apart;
  - V4: no dwell footage;
  - rule 5: every check is computed.

THE COMPOSITION IS f3_render'S, WITH f4_render'S THREE CHANGES. The frozen renderer is pinned, and its
main is not run: it renders the frozen model, and it moves the frozen demonstration videos. Each walk
here is composed by f3_render's own steps, with the same functions (`render_display.simulate_walk`,
`switching.decide_walk`, `.slide`, the anchor segment). Its checks are computed the same way, both
causal bounds included, from each drawn step's `window` and `evidence_window`.

f4_render (2026-09-24, the current demonstration in runs/constrained/demo_v2/) changed three things, and
they are taken here:
  - the display phase HEAD_OFFSET_S = 0.375 s, pre-registered in
    `reports/tracking/history/2026-09-24_prereg-display-phase.md` and chosen on s0103_to_s02;
  - both causal bounds computed on the step the dot actually GLIDES TOWARDS, SHIFT_W included, which is
    stricter than f3's;
  - the result at each walk's end: CORRECT or WRONG, with the running accuracy.

What differs from f3_render, and only this:
  - the emissions are the final model's pool (fin_<test>) decoded with the re-selected variant, with the corrected start-of-walk
    readers (`pd_clean`'s map; `reports/tracking/2026-09-29_audit-leakage.md`);
  - the gate energy is relative: x max(1, G0 / g_rec);
  - the display head is the final DISP_END (`pd_dispend`), trained on A1+A2+B1 only;
  - the end text names the final committed decision, which must equal `cells/<cell>/d3/CR.relgateU`
    walk for walk, as must the lock, or the render refuses;
  - there is no bounded rescore (the final model has none).

    python3 -m pipeline.constrained.pd_render --cell fin_A3 [--stems participant_X ...] [--no-video]

Output: runs/dc2_results/render_final/<test>/: one video per recording, RESULTS.json and ACCEPTANCE.md.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT_ROOT = J(REPO_ROOT, "runs", "dc2_results", "render_final")
FPS = 10
LATENCY = 2.0                #: V1
DELAY = 2.0                  #: V3: the lock reads the window ending at press + 2.0 s
HEAD_OFFSET_S = 0.375        #: f4_render's display phase, chosen 2026-09-24 by PREREG_display_phase on s0103_to_s02
SHIFT_W = 0.50               #: V5
DISPLAY_CAP_M_PER_WINDOW = 0.80
DISPLAY_SD_SCALE = 4.5
LAG_S = 1.0                  #: WINDOW_S / 2


def inner(cell: str, stems: list, video: bool, end_kind: str, variant: str = "relgateU", ref_name: str = None) -> int:
    t_all = time.time()
    from pipeline.constrained.pd_clean import _bound, apply_pace, force_cpu, plan_for, start_terms_for
    force_cpu()
    PC, c, tfs = _bound(cell)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    plan = plan_for(c, tfs)
    for s, p in plan.items():
        if p["changed"]:
            tmap[s] = p["clean"]
    os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    assert all(tfs(s) == plan[s]["clean"] for s in plan), "the corrected reader map did not take"
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained import switching as SW
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE, shipped_pieces
    from pipeline.constrained.pd_decode import gate_reference, idle_idx
    from pipeline.constrained.r1_oldcensus import shipped_opts
    from pipeline.constrained.rb7_demo import room, truth_at
    from pipeline.constrained.rebuild_common import WINDOW_S
    from pipeline.constrained.render_display import (CENTRE, monotonicity_violations, on_screen_tracking,
                                                     simulate_walk, xy_of)
    from pipeline.constrained.sb2_structural import press_ends
    from pipeline.constrained.u1_adapt import session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader
    from pipeline.constrained import paths as P
    from pipeline.live.display import settings
    b = c["test"]
    te = (b,)
    st, cfg0, ne, transit, kind, alpha = shipped_pieces()
    pace = apply_pace()
    cfg_dec = dataclasses.replace(cfg0, sd_scale=1.0)
    cfg_disp = dataclasses.replace(cfg0, sd_scale=DISPLAY_SD_SCALE)
    sett = settings()
    SWITCH, PRIOR_F = sett["switch"], sett["prior_f"]
    assert SWITCH and SWITCH.get("max_switches") == 1, f"arm C (one switch) expected, got {SWITCH}"
    # the start terms, as pd_decode.inner builds them: A2 for the display, A2 + the veto committed
    cache = {}
    Xtr, ytr, _k, _w, _u, _a = session_rows(c["train"], st, ADAPT_MODE, cache)
    Xte, _y, kte, _w2, _u2, _a2 = session_rows(te, st, ADAPT_MODE, cache)
    _pred, proba, classes = fit_reader(Xtr, ytr, Xte, False)
    a2, start = start_terms_for(variant, c, te, st, kte, proba, classes)
    opts = shipped_opts(st, c["train"])
    opts.update(entry="soft", entry_window_m=1.0, start_term=start)
    opts_disp = shipped_opts(st, c["train"])
    opts_disp.update(entry="soft", entry_window_m=1.0, start_term=a2)
    src = list(shipped_pool_emissions(c["heads_tag"], c["train"], te, False, st, kind, alpha, fusion_w=0.0)[0])
    G0 = gate_reference(c["train"], PC.cal_stems, room_a_only=True)
    if end_kind == "final":
        from pipeline.constrained.pd_dispend import end_emissions
        e_end = end_emissions(b, st, alpha)
        end_note = "the final DISP_END (pd_dispend), trained on A1+A2+B1"
    else:
        e_end = None
        end_note = "SMOKE TEST ONLY: the pooled emission stands in for the display head"
    ref = J(c["base"], "d3", ref_name or f"CR.{variant}")
    with open(J(ref, "decode.json"), encoding="utf-8") as f:
        ref_c = {(r["stem"], int(r["pass_id"])): r["final_line"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    with open(J(ref, "scorerlock.json"), encoding="utf-8") as f:
        ref_l = {(r["stem"], int(r["pass_id"])): r["display_lock"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    room_paths = P.load_paths()
    lag_w = int(round(LAG_S / STRIDE))
    SCORER = None
    out_dir = J(OUT_ROOT, f"{b}" if end_kind == "final" else f"{b}_smoke")
    os.makedirs(out_dir, exist_ok=True)
    CAPTION = (f"The whole display runs {LATENCY:g} s behind real time. The dot waits at the room centre for "
               f"those {LATENCY:g} s while it listens; the green marker then appears at the walk's start on the "
               f"same frame as the dot commits to its line. The line is final apart from at most one marked "
               f"switch. Nothing is projected: every position drawn is one the decoder produced from radio "
               f"already recorded, or a point between two of them.")
    RES = {"cell": cell, "test": b, "train": list(c["train"]), "variant": variant, "pace": pace, "ref": os.path.relpath(ref, REPO_ROOT),
           "model": f"FINAL, corrected readers, re-selected decode ({variant})",
           "display_head": end_note, "tag_map": tmap, "G0": G0, "fps": FPS, "latency_s": LATENCY, "delay_s": DELAY,
           "head_offset_s": HEAD_OFFSET_S, "shift_w": SHIFT_W, "prior_flatten": PRIOR_F, "switch_arm": SWITCH,
           "caption": CAPTION, "recordings": {}, "failures": [],
           "equality_with_the_decode": {"committed_equal": 0, "lock_equal": 0, "n": 0},
           "rule": {"violations": 0, "frames_checked": 0, "examples": []},
           "dot_visible": {"frames": 0, "frames_without_dot": 0, "expected": 0, "missing_after_first_legal": 0},
           "causal_bound_s": -9.0, "causal_evidence_bound_s": -9.0,
           "dwell_cut": {"recordings": 0, "frames_removed": 0, "grid_windows_seen": 0,
                         "frames_remaining_inside_a_grid_block": 0},
           "anchor_segment": {"frames": 0, "off_segment_frames": 0},
           "vision_rules": {"V1_latency_s": LATENCY,
                            "V2_commit_frame_equals_marker_frame": {"walks": 0, "violations": 0, "max_gap_s": 0.0},
                            "V3_lock_offset_s_distinct_values": []},
           "leave_together": {"walks": 0, "max_gap_s": 0.0, "violations": 0, "max_stall_s": 0.0,
                              "stall_violations": 0, "stall_explained_by_the_decoder": 0},
           "jumps": {"total": 0, "caused_by_the_lock": 0, "caused_by_a_switch": 0},
           "switching": {"walks": 0, "switches": 0, "w2r": 0, "r2w": 0, "w2w": 0, "jump_m": [],
                         "slide_off_segment_frames": 0, "slide_frame_jumps_over_0_5m": 0,
                         "decision_evidence_worst_s": -9.0, "target_drawn_worst_s": -9.0,
                         "target_evidence_worst_s": -9.0, "switch_in_final_zone": 0, "persistence_violations": 0,
                         "returns_to_a_drawn_line": 0, "more_than_max_switches": 0, "earliest_after_lock_s": None,
                         "end_on_committed": 0},
           "rule1_lines_named_after_lock": {"walks_over_two": 0, "max": 0},
           "end_text_equals_committed": {"walks": 0, "equal": 0}}
    cal = PC.cal_stems(b)
    todo = [x for x in src if x[0] not in cal and (not stems or x[0] in stems)]
    for stem, rec, ge_raw, e in todo:
        who = stem.replace("participant_", "").split("_")[0]
        try:
            ix = idle_idx(rec)
            g = float(np.median(np.asarray(ge_raw)[ix])) if len(ix) else G0
            gscale = max(1.0, G0 / g)
            ge = np.asarray(ge_raw, float) * gscale
            e = np.asarray(e, float)
            # THE DECISION: no display cap (the committed answer, pd_decode's)
            D.MAX_ADVANCE_M = None
            D2._LT_CACHE.clear()
            rows = night_track(e, rec, st, cfg_dec, transit, ne, ge, STRIDE, opts, None)
            # THE DISPLAY: the cap, the display spread, A2 alone, the display head's paths after the lock
            D.MAX_ADVANCE_M = DISPLAY_CAP_M_PER_WINDOW
            D2._LT_CACHE.clear()
            alt = {"end": e_end[stem]} if e_end is not None else {"end": e}
            rows_disp = night_track(e, rec, st, cfg_disp, transit, ne, ge, STRIDE, opts_disp, None,
                                    want_display=True, display_lags_w=(lag_w,), display_to_horizon=True,
                                    display_alt_e=alt, display_alt_flatten=({"end": PRIOR_F} if PRIOR_F else None),
                                    display_lead_in_w=0, display_switch_paths=True)
            disp = {int(r["pass_id"]): r for r in rows_disp}
            if SCORER is None:
                SCORER = SW.Scorer(st, cfg_dec, transit)
            ne.calibrate(e)
            E_sw = SCORER.stack(e, ge, ne)
            presses = press_ends(rec.session, rec.stem)
            with open(J(PC.raw_dir(b), f"{stem}.gt.json"), encoding="utf-8") as f:
                sc = json.load(f)
            pstart = {int(q["pass_id"]): float(q["t_start"]) for q in sc.get("passes", [])}
            t = np.asarray(rec.t0, float)
            mode = np.asarray(rec.mode).astype(str)
            walks = []
            for r in rows:
                pid = int(r["pass_id"])
                if (stem, pid) not in ref_c:
                    continue                                   # not an evaluated pass
                L = disp[pid]["display_locked"][f"{lag_w}|{DELAY}"]
                RES["equality_with_the_decode"]["n"] += 1
                RES["equality_with_the_decode"]["committed_equal"] += int(r["final_line"] == ref_c[(stem, pid)])
                RES["equality_with_the_decode"]["lock_equal"] += int(L["lock_line"] == ref_l.get((stem, pid)))
                walks.append({"pass_id": pid, "true": r["true_line"], "lo": int(r["lo"]),
                              "scene_start": float(t[int(r["lo"])]) + WINDOW_S - HEAD_OFFSET_S,
                              "t_press_start": pstart[pid], "t_press": float(presses[pid]),
                              "committed": r["final_line"], "found": r["final_line"] == r["true_line"],
                              "locked": L})
            frames = [float(x) for x in np.arange(t[0], t[-1] + WINDOW_S, 1.0 / FPS)]
            grid = np.flatnonzero(mode == "grid")
            n_before = len(frames)
            if len(grid):
                lo_c, hi_c = float(t[int(grid[0])]), float(t[int(grid[-1])]) + WINDOW_S
                frames = [x for x in frames if not (lo_c <= x <= hi_c)]
            RES["dwell_cut"]["recordings"] += 1
            RES["dwell_cut"]["frames_removed"] += n_before - len(frames)
            RES["dwell_cut"]["grid_windows_seen"] += int(len(grid))
            RES["dwell_cut"]["frames_remaining_inside_a_grid_block"] += int(sum(
                1 for x in frames if len(grid) and float(t[int(grid[0])]) <= x <= float(t[int(grid[-1])]) + WINDOW_S))

            def green_at(tq, park_until=None):
                if park_until is not None and float(tq) < park_until:
                    return None
                g_, _gl, _p = truth_at(sc, float(tq) - LATENCY)
                return (float(g_[0]), float(g_[1])) if g_ else None

            def green_live(tq):
                g_, _gl, _p = truth_at(sc, float(tq))
                return (float(g_[0]), float(g_[1])) if g_ else None

            def green_at_decoded(tq):
                g_, _gl, _p = truth_at(sc, float(tq) - LAG_S)
                return (float(g_[0]), float(g_[1])) if g_ else None

            for wk in walks:
                L = wk["locked"]
                wk["t_dec0"] = wk["scene_start"] + LATENCY
                wk["park_until"] = float(wk["t_press_start"]) + LATENCY
                fr = [x for x in frames if float(wk["t_press_start"]) <= x < wk["t_press"] + LATENCY]
                pre = [x for x in fr if x < wk["park_until"]]
                anch = [x for x in fr if wk["park_until"] <= x < wk["t_dec0"]]
                post = [x for x in fr if x >= wk["t_dec0"]]
                _alt = (L.get("paths_alt") or {}).get("end")
                lpath = _alt if _alt else L["path"]
                drawn, wk["rule_violations"] = {}, []
                for x in pre:
                    drawn[round(float(x), 4)] = CENTRE
                _a, _b = st.slice_of[L["lock_line"]]
                line_entry = xy_of(st, _a)
                wk["line_entry_xy"] = (float(line_entry[0]), float(line_entry[1]))
                t_eff = wk["t_dec0"]
                sim, seam = None, line_entry
                wk["mid_switches"], wk["mid_switch_paths"] = [], []
                if post and lpath:
                    sim = simulate_walk(lpath, st, t_eff, wk["t_press"] + LATENCY, line_entry, L["lock_line"], STRIDE,
                                        0, FPS, None, lambda q: green_at(q, wk["park_until"]), frames=post, lead=False,
                                        shift_w=SHIFT_W)
                    seam = sim["red"][0] if sim["red"] else line_entry
                    span = float(wk["t_dec0"]) - float(wk["park_until"])
                    for x in anch:
                        f_ = 0.0 if span <= 0 else float(np.clip((x - wk["park_until"]) / span, 0.0, 1.0))
                        pq = (line_entry[0] + (seam[0] - line_entry[0]) * f_, line_entry[1] + (seam[1] - line_entry[1]) * f_)
                        drawn[round(float(x), 4)] = pq
                        RES["anchor_segment"]["frames"] += 1
                        _d1 = float(np.hypot(pq[0] - line_entry[0], pq[1] - line_entry[1]))
                        _d2 = float(np.hypot(seam[0] - pq[0], seam[1] - pq[1]))
                        _dt = float(np.hypot(seam[0] - line_entry[0], seam[1] - line_entry[1]))
                        RES["anchor_segment"]["off_segment_frames"] += int(abs(_d1 + _d2 - _dt) > 1e-6)
                    drawn.update({round(f, 4): p for f, p in zip(sim["frames"], sim["red"])})
                    wk["rule_violations"] += sim["violations"]
                    RES["rule"]["frames_checked"] += sim["n_frames"]
                    RES["rule"]["violations"] += len(sim["violations"])
                    _g0 = green_at(wk["park_until"], wk["park_until"])
                    wk["start_gap_m"] = None if _g0 is None else float(np.hypot(line_entry[0] - _g0[0], line_entry[1] - _g0[1]))
                    wk["rpost"], wk["gpost"] = list(sim["red"]), list(sim["green"])
                    # RULE 1a, ARM C: the one display-only switch, by f3_render's own steps
                    _lo = int(wk["lo"])
                    _decs = SCORER.decisions(E_sw, t, _lo, SCORER.start(E_sw, _lo),
                                             SW.decision_frames(wk["t_press_start"], wk["t_press"]))
                    _dots = [(float(x), drawn[round(float(x), 4)]) for x in anch + post]

                    def _newsim(line, frames_, green=False, _wk=wk, _L=L):
                        _na, _nb = st.slice_of[line]
                        return simulate_walk(_L["switch_paths"]["end"][line], st, t_eff, _wk["t_press"] + LATENCY,
                                             xy_of(st, _na), line, STRIDE, 0, FPS, None,
                                             (lambda q: green_at(q, _wk["park_until"])) if green else (lambda q: None),
                                             frames=frames_, lead=False, shift_w=SHIFT_W)

                    def _dots_for(line, x_from, _post=post):
                        s_ = _newsim(line, [x for x in _post if x >= x_from - 1e-9])
                        return list(zip(s_["frames"], s_["red"]))

                    _res = SW.decide_walk(L["lock_line"], _decs, start.get(f"{rec.session}|{stem}|{wk['pass_id']}"),
                                          float(SWITCH["theta"]), st, _dots, _dots_for, radius=SWITCH["radius_m"],
                                          max_switches=int(SWITCH["max_switches"]), final_m=float(SWITCH["final_m"]))
                    RES["switching"]["walks"] += 1
                    _cur_sim, _seen = sim, {L["lock_line"]}
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
                        drawn.update({round(f, 4): p_ for f, p_ in zip(_nsim["frames"], _nsim["red"])})
                        _gone = [v for v in _cur_sim["violations"] if v["t"] >= xs - 1e-9]
                        wk["rule_violations"] = [v for v in wk["rule_violations"] if v not in _gone] + _nsim["violations"]
                        RES["rule"]["violations"] += len(_nsim["violations"]) - len(_gone)
                        RES["rule"]["frames_checked"] += _nsim["n_frames"] - sum(1 for x_ in _cur_sim["frames"] if x_ >= xs - 1e-9)
                        _cur_sim = _nsim
                        _it = int(np.clip(int(np.floor((xs + SW.SLIDE_S - t_eff) / STRIDE + SHIFT_W)), 0, len(npath) - 1))
                        _w, _ew = npath[_it]["window"], npath[_it].get("evidence_window", npath[_it]["window"])
                        _seq = [p_old] + [p_ for _x, p_, _o in _slide] + ([_nsim["red"][0]] if _nsim["red"] else [])
                        rec_sw = {"x": xs, "after_lock_s": round(xs - wk["park_until"], 6), "old": old, "new": new,
                                  "lead": _sw["lead"], "persist": _sw["persist"], "theta": float(SWITCH["theta"]),
                                  "dot_max_arc_m": _sw["dot_max_arc_m"], "line_length_m": _sw["line_length_m"],
                                  "final_m": _sw["final_m"], "decision_evidence_bound_s": _sw["evidence_bound_s"],
                                  "target_drawn_bound_s": float(t[_w] + WINDOW_S - xs),
                                  "target_evidence_bound_s": float(t[_ew] + WINDOW_S - xs),
                                  "p_old": list(p_old), "q_new": list(q_new),
                                  "jump_m": float(np.hypot(q_new[0] - p_old[0], q_new[1] - p_old[1])),
                                  "slide_frames": len(_slide), "slide_off_segment": int(sum(o_ for _x, _p, o_ in _slide)),
                                  "slide_frame_jumps_over_0_5m": int(sum(1 for a_, b_ in zip(_seq, _seq[1:])
                                                                        if float(np.hypot(b_[0] - a_[0], b_[1] - a_[1])) > 0.5)),
                                  "returns_to_a_drawn_line": bool(new in _seen),
                                  "w2r": bool(old != wk["true"] and new == wk["true"]),
                                  "r2w": bool(old == wk["true"] and new != wk["true"]),
                                  "w2w": bool(old != wk["true"] and new != wk["true"])}
                        _seen.add(new)
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
                        S_["switch_in_final_zone"] += int(rec_sw["dot_max_arc_m"] >= rec_sw["line_length_m"] - rec_sw["final_m"])
                        S_["persistence_violations"] += int(not (
                            len(rec_sw["persist"]) == SW.PERSIST_STEPS
                            and all(q_["qualifies"] and q_["best"] == new and q_["lead"] > rec_sw["theta"]
                                    for q_ in rec_sw["persist"])))
                        S_["returns_to_a_drawn_line"] += int(rec_sw["returns_to_a_drawn_line"])
                        S_["earliest_after_lock_s"] = (rec_sw["after_lock_s"] if S_["earliest_after_lock_s"] is None
                                                       else min(S_["earliest_after_lock_s"], rec_sw["after_lock_s"]))
                    RES["switching"]["more_than_max_switches"] += int(len(wk["mid_switches"]) > int(SWITCH["max_switches"]))
                    wk["rpost"] = [drawn[round(float(x_), 4)] for x_ in post]
                if wk["rule_violations"]:
                    RES["rule"]["examples"] += wk["rule_violations"][:3]
                expect = list(fr)
                wk["frames_expected"] = len(expect)
                wk["frames_missing"] = int(sum(1 for x in expect if drawn.get(round(float(x), 4)) is None))
                RES["dot_visible"]["expected"] += wk["frames_expected"]
                RES["dot_visible"]["missing_after_first_legal"] += wk["frames_missing"]
                # THE TWO CAUSAL BOUNDS, as f4_render computes them: on the step the dot actually glides
                # towards, SHIFT_W included (f3 took the floor without it, a step up to one stride early)
                for x in post:
                    _pth = lpath
                    for _xs, _np in wk["mid_switch_paths"]:
                        if x >= _xs - 1e-9:
                            _pth = _np
                    _raw = (x - t_eff) / STRIDE + SHIFT_W
                    i_ = int(min(np.floor(_raw), len(_pth) - 1)) if _raw >= 0 else -1
                    if 0 <= i_ < len(_pth):
                        w_ = _pth[i_]["window"]
                        if w_ < len(t):
                            RES["causal_bound_s"] = max(RES["causal_bound_s"], float(t[w_] + WINDOW_S - x))
                        ew_ = _pth[i_].get("evidence_window", w_)
                        if ew_ < len(t):
                            RES["causal_evidence_bound_s"] = max(RES["causal_evidence_bound_s"], float(t[ew_] + WINDOW_S - x))
                # JUMPS over 0.5 m, and whether the lock or a switch caused them
                jumps = lock_jumps = switch_jumps = 0
                order = sorted(drawn)
                for a_, b_ in zip(order, order[1:]):
                    pa, pb = drawn[a_], drawn[b_]
                    if pa is None or pb is None:
                        continue
                    if float(np.hypot(pb[0] - pa[0], pb[1] - pa[1])) > 0.5:
                        jumps += 1
                        if (a_ - wk["t_press_start"]) < DELAY <= (b_ - wk["t_press_start"]):
                            lock_jumps += 1
                        elif any(_s["x"] - 1e-9 <= b_ <= _s["x"] + SW.SLIDE_S + 1.0 / FPS + 1e-9 for _s in wk["mid_switches"]):
                            switch_jumps += 1
                wk["jumps_over_0.5m"], wk["jumps_at_the_lock"], wk["jumps_at_a_switch"] = jumps, lock_jumps, switch_jumps
                RES["jumps"]["total"] += jumps
                RES["jumps"]["caused_by_the_lock"] += lock_jumps
                RES["jumps"]["caused_by_a_switch"] += switch_jumps
                # RULE 6, V2, V3, measured per walk
                _first_g = next((x for x in sorted(drawn) if green_at(x, wk["park_until"]) is not None), None)
                _first_r = next((x for x in sorted(drawn) if x >= wk["park_until"]), None)
                wk["first_marker_frame"], wk["first_committed_frame"] = _first_g, _first_r
                wk["lock_offset_s"] = round(float(wk["park_until"]) - float(wk["t_press_start"]), 6)
                if wk["lock_offset_s"] not in RES["vision_rules"]["V3_lock_offset_s_distinct_values"]:
                    RES["vision_rules"]["V3_lock_offset_s_distinct_values"].append(wk["lock_offset_s"])
                if _first_g is not None and _first_r is not None:
                    _gap = abs(float(_first_g) - float(_first_r))
                    V2 = RES["vision_rules"]["V2_commit_frame_equals_marker_frame"]
                    V2["walks"] += 1
                    V2["max_gap_s"] = max(V2["max_gap_s"], _gap)
                    V2["violations"] += int(_gap > 1.0 / FPS + 1e-6)
                    LT = RES["leave_together"]
                    LT["walks"] += 1
                    LT["max_gap_s"] = max(LT["max_gap_s"], _gap)
                    LT["violations"] += int(_gap > 1.0 / FPS + 1e-6)
                    _ord = [q for q in sorted(drawn) if q >= wk["park_until"]]
                    _stall, _p0 = None, drawn.get(_ord[0]) if _ord else None
                    for q in _ord[1:]:
                        _pq = drawn.get(q)
                        if _p0 is not None and _pq is not None and float(np.hypot(_pq[0] - _p0[0], _pq[1] - _p0[1])) > 1e-9:
                            _stall = float(q) - float(_ord[0])
                            break
                    _dm, _le = None, wk["line_entry_xy"]
                    for q in _ord:
                        if q < wk["t_dec0"]:
                            _tg = seam if post else _le
                        else:
                            _i = int(np.clip(int(np.floor((q - wk["t_dec0"]) / STRIDE + SHIFT_W)), 0, len(lpath) - 1))
                            _st_i = lpath[_i]["state"]
                            _tg = xy_of(st, _st_i) if _st_i is not None and _st_i >= 0 else None
                        if _tg is not None and float(np.hypot(_tg[0] - _le[0], _tg[1] - _le[1])) > 1e-9:
                            _dm = float(q) - float(_ord[0])
                            break
                    wk["stall_s"], wk["decoder_first_moves_s"] = _stall, _dm
                    if _stall is not None:
                        LT["max_stall_s"] = max(LT["max_stall_s"], _stall)
                        _expl = _dm is not None and _stall <= _dm + 1.0 / FPS + 1e-6
                        LT["stall_explained_by_the_decoder"] += int(_expl)
                        LT["stall_violations"] += int(_stall > 1.0 / FPS + 1e-6 and not _expl)
                wk["locked_line"] = L["lock_line"]
                wk["lock_correct"] = bool(L["lock_line"] == wk["true"])
                wk["drawn_end_line"] = wk["mid_switches"][-1]["new"] if wk["mid_switches"] else L["lock_line"]
                RES["switching"]["end_on_committed"] += int(wk["drawn_end_line"] == wk["committed"])
                named = {L["lock_line"]} | {s_["new"] for s_ in wk["mid_switches"]}
                RES["rule1_lines_named_after_lock"]["max"] = max(RES["rule1_lines_named_after_lock"]["max"], len(named))
                RES["rule1_lines_named_after_lock"]["walks_over_two"] += int(len(named) > 2)
                RES["end_text_equals_committed"]["walks"] += 1
                RES["end_text_equals_committed"]["equal"] += int(wk["committed"] == ref_c[(stem, wk["pass_id"])])
                # RULE 4: the two numbers, never added
                wk["tracking"] = on_screen_tracking(wk.get("rpost") or [], wk.get("gpost") or [])
                wk["tracking_includes_the_anchor_segment"] = False
                gseq_dec = [green_at_decoded(f) for f in sorted(drawn)]
                wk["decoded_accuracy"] = on_screen_tracking([drawn[f] for f in sorted(drawn)], gseq_dec)
                _off = [float(np.hypot(a[0] - b_[0], a[1] - b_[1]))
                        for a, b_ in zip(gseq_dec, [green_at(f) for f in sorted(drawn)]) if a is not None and b_ is not None]
                wk["display_offset"] = {"n_frames": len(_off), "mean_m": float(np.mean(_off)) if _off else None,
                                        "median_m": float(np.median(_off)) if _off else None}
                wk["monotonicity_violations"] = int(monotonicity_violations(lpath, st)) if lpath else 0
                wk["drawn"] = drawn
            n_nodot = 0
            vid = None
            if video:
                n_nodot, vid = draw(out_dir, stem, who, b, walks, frames, t, rec, mode, st, room, room_paths, SW, CENTRE,
                                    green_at, CAPTION)
            RES["dot_visible"]["frames"] += len(frames)
            RES["dot_visible"]["frames_without_dot"] += n_nodot
            for wk in walks:
                wk["n_rule_violations"] = len(wk["rule_violations"])
                for k_ in ("drawn", "locked", "rule_violations", "mid_switch_paths", "rpost", "gpost"):
                    wk.pop(k_, None)
            RES["recordings"][who] = {"stem": stem, "video": vid, "n_frames": len(frames), "gate_scale": gscale,
                                      "walks": walks}
            print(f"[{time.strftime('%H:%M:%S')}] {b} {who}: {len(walks)} walks, committed "
                  f"{sum(w['found'] for w in walks)}, lock {sum(w['lock_correct'] for w in walks)}, "
                  f"switches {sum(len(w['mid_switches']) for w in walks)}, frames {len(frames)}, no-dot {n_nodot}", flush=True)
        except Exception as exc:                                            # noqa: BLE001
            import traceback
            RES["failures"].append({"who": who, "error": repr(exc), "traceback": traceback.format_exc()[-2000:]})
            print(f"  {who}: FAILED {exc!r}", flush=True)
    D.MAX_ADVANCE_M = None
    D2._LT_CACHE.clear()
    E = RES["equality_with_the_decode"]
    RES["STATUS"] = status(RES)
    RES["minutes"] = round((time.time() - t_all) / 60.0, 1)
    with open(J(out_dir, "RESULTS.json"), "w", encoding="utf-8") as f:
        json.dump(RES, f, indent=1, default=str)
    with open(J(out_dir, "ACCEPTANCE.md"), "w", encoding="utf-8") as f:
        f.write(acceptance(RES))
    print(f"{cell}: equality {E}; status {RES['STATUS']}", flush=True)
    return 0 if (RES["STATUS"]["ALL_PASS"] and not RES["failures"]) else 1


def status(R: dict) -> dict:
    """Every rule's check, computed: True where it holds."""
    E, S = R["equality_with_the_decode"], R["switching"]
    V2 = R["vision_rules"]["V2_commit_frame_equals_marker_frame"]
    out = {
        "decode_equality (committed and lock equal the corrected decode)": E["n"] > 0 and E["committed_equal"] == E["n"] and E["lock_equal"] == E["n"],
        "rule 1 / 1a (the lock is final; at most one switch; never back)": S["more_than_max_switches"] == 0 and S["returns_to_a_drawn_line"] == 0 and R["rule1_lines_named_after_lock"]["walks_over_two"] == 0,
        "rule 1a (no switch in the final 1.5 m; persistence)": S["switch_in_final_zone"] == 0 and S["persistence_violations"] == 0,
        "rule 1a (switch decisions and targets causal)": S["decision_evidence_worst_s"] <= 1e-9 and S["target_drawn_worst_s"] <= 1e-9 and S["target_evidence_worst_s"] <= 1e-9,
        "rule 1a (slides on their segments)": S["slide_off_segment_frames"] == 0,
        "rule 1b (end text is the committed decision)": R["end_text_equals_committed"]["walks"] == R["end_text_equals_committed"]["equal"],
        "rule 2 (nothing projected: every frame decoded or between two decodes)": R["rule"]["violations"] == 0,
        "rule 2a (anchor frames on the anchor segment)": R["anchor_segment"]["off_segment_frames"] == 0,
        "rule 5 (drawn-window causal bound <= 0)": R["causal_bound_s"] <= 1e-9,
        "rule 5 (evidence causal bound <= 0)": R["causal_evidence_bound_s"] <= 1e-9,
        "rule 5 (no frame without a dot inside a walk)": R["dot_visible"]["missing_after_first_legal"] == 0,
        "rule 5 (frames without a dot, whole video)": R["dot_visible"]["frames_without_dot"] == 0,
        "rule 6 / V2 (dot and marker leave together)": V2["violations"] == 0 and R["leave_together"]["violations"] == 0,
        "rule 6 (no stall the decoder does not account for)": R["leave_together"]["stall_violations"] == 0,
        "V1 (2.0 s latency)": R["latency_s"] == 2.0,
        "V3 (lock offset one constant, 2.0 s)": R["vision_rules"]["V3_lock_offset_s_distinct_values"] in ([2.0], []),
        "V4 (no dwell footage)": R["dwell_cut"]["frames_remaining_inside_a_grid_block"] == 0,
        "V5 (dot phase 0.50)": R["shift_w"] == 0.50}
    out["ALL_PASS"] = all(out.values())
    return out


def draw(out_dir, stem, who, b, walks, frames, t, rec, mode, st, room, room_paths, SW, CENTRE, green_at, caption):
    """The video, drawn as f3_render draws it: the room, the parked or tracking red dot, the delayed green
    marker, the named line, the switch mark, the clock stating the delay, and the end text naming the
    committed decision. Returns (frames without a dot, file name)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.animation as anim
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.0, 8.2))
    fig.subplots_adjust(bottom=0.22, top=0.93)
    room(ax, room_paths)
    hl, = ax.plot([], [], "-", color="tab:orange", lw=3.5, alpha=0.30, zorder=2)
    lock_hl, = ax.plot([], [], "-", color="tab:red", lw=3.5, alpha=0.45, zorder=3)
    trail, = ax.plot([], [], "-", color="tab:red", lw=1.4, alpha=0.5, zorder=4)
    gdot, = ax.plot([], [], "o", color="tab:green", ms=11, zorder=5, label=f"where the person was {LATENCY:g} s ago")
    rdot, = ax.plot([], [], "o", color="tab:red", ms=9, zorder=6, label="the tracker's answer for that same moment")
    swmark, = ax.plot([], [], "X", color="tab:purple", ms=11, zorder=7, label="where the display switched line")
    clock = ax.text(2.5, 5.32, "", fontsize=12, ha="center", color="0.15", weight="bold", family="monospace", zorder=8)
    ttl = ax.set_title("", fontsize=8.5)
    info = fig.text(0.5, 0.045, "", fontsize=8, ha="center", family="monospace", color="0.25")
    fig.text(0.5, 0.125, caption, fontsize=6.3, ha="center", va="center", wrap=True, color="0.35")
    ax.legend(loc="upper left", fontsize=6.2, framealpha=0.85)
    tx, ty = [], []
    state = {"walk": None, "shown": "", "last": CENTRE, "nodot": 0, "scored": set(), "right": 0}
    session_name = {"03": "A3 (Room A, third day)", "B2": "B2 (Room B, second day)"}.get(b, b)

    def chain_xy(nm):
        a, b_ = st.slice_of[nm]
        p = np.asarray(st.xy)[a:b_]
        return p[:, 0], p[:, 1]

    def frame(k):
        tq = frames[k]
        cur = next((wk for wk in walks if float(wk["t_press_start"]) - 0.05 <= tq <= wk["t_press"] + LATENCY + 0.5), None)
        g = green_at(tq, cur["park_until"]) if cur is not None else None
        gdot.set_data([g[0]] if g else [], [g[1]] if g else [])
        if cur is None:
            state["last"] = CENTRE
            rdot.set_data([CENTRE[0]], [CENTRE[1]])
            hl.set_data([], []); lock_hl.set_data([], []); trail.set_data([], []); swmark.set_data([], [])
            tx.clear(); ty.clear(); state["walk"] = None
            clock.set_text(f"{LATENCY:g} s behind real time")
            info.set_color("0.25")
            info.set_text("waiting for the next walk")
            ttl.set_text(f"{who}  |  FINAL tracker  |  test session {session_name}, never trained on")
        else:
            if state["walk"] != cur["pass_id"]:
                state.update({"walk": cur["pass_id"], "shown": ""})
                tx.clear(); ty.clear()
            clock.set_text(f"t = {max(0.0, tq - cur['park_until']):5.1f} s      {LATENCY:g} s behind real time")
            if tq < cur["t_press"] + LATENCY:
                info.set_color("0.25")
                p = cur["drawn"].get(round(float(tq), 4)) or state["last"]
                state["last"] = p
                if tq < cur["park_until"]:
                    rdot.set_data([CENTRE[0]], [CENTRE[1]])
                    tx.clear(); ty.clear(); trail.set_data([], []); hl.set_data([], []); lock_hl.set_data([], [])
                    swmark.set_data([], [])
                    info.set_text(f"listening   {cur['park_until'] - tq:.1f}s until this walk commits")
                else:
                    rdot.set_data([p[0]], [p[1]])
                    done = [q_ for q_ in cur["mid_switches"] if tq >= q_["x"] - 1e-9]
                    named = SW.named_line_at_multi(cur["locked_line"], done, tq)
                    state["shown"] = named
                    hl.set_data(*chain_xy(named))
                    tx.append(p[0]); ty.append(p[1]); trail.set_data(tx, ty)
                    d = float(np.hypot(p[0] - g[0], p[1] - g[1])) if g else None
                    if done:
                        s_ = done[-1]
                        swmark.set_data([q_["p_old"][0] for q_ in done], [q_["p_old"][1] for q_ in done])
                        info.set_text(f"SWITCHED: {s_['old']} -> {s_['new']}" + (f"   off by {d:.2f} m" if d is not None else ""))
                    else:
                        swmark.set_data([], [])
                        info.set_text(f"LOCKED: {named}" + (f"   off by {d:.2f} m" if d is not None else ""))
                lock_hl.set_data([], [])
            else:
                lock_hl.set_data(*(chain_xy(cur["drawn_end_line"]) if cur.get("drawn_end_line") else ([], [])))
                hl.set_data([], [])
                if state["last"] is not None:
                    rdot.set_data([state["last"][0]], [state["last"][1]])
                agree = cur["committed"] == cur.get("drawn_end_line")
                if cur["pass_id"] not in state["scored"]:
                    state["scored"].add(cur["pass_id"])
                    state["right"] += int(cur["found"])
                verdict = "CORRECT" if cur["found"] else "WRONG"
                info.set_color("tab:green" if cur["found"] else "tab:red")
                info.set_text(f"{verdict}: COMMITTED (final model) {cur['committed'] or 'none'}   true {cur['true']}\n"
                              f"drawn {cur.get('drawn_end_line') or 'none'}" + (" (agrees)" if agree else " (differs)")
                              + f"   {who} so far: {state['right']} of {len(state['scored'])} committed correctly")
            ttl.set_text(f"{who}  |  FINAL tracker  |  {session_name}  |  walk {cur['pass_id']}  |  true {cur['true']}")
        if len(np.atleast_1d(rdot.get_xdata())) == 0:
            state["nodot"] += 1

    ani = anim.FuncAnimation(fig, frame, frames=len(frames), interval=1000 // FPS)
    name = f"{b}_{who}_final.mp4"
    ani.save(J(out_dir, name), writer=anim.FFMpegWriter(fps=FPS, bitrate=1800))
    plt.close(fig)
    return state["nodot"], name


def acceptance(R: dict) -> str:
    """ACCEPTANCE.md for one test session: the checks, then the walks. MEASURED RESULTS ONLY; the rules are
    reports/RENDER_RULES.md."""
    S, E = R["status"] if "status" in R else R["STATUS"], R["equality_with_the_decode"]
    walks = [w for r in R["recordings"].values() for w in r["walks"]]

    def pct(v):
        v = [x for x in v if x is not None]
        return f"{100.0 * float(np.mean(v)):.2f}" if v else "-"
    trk = [w["tracking"].get("within_pct") for w in walks if w.get("tracking")]
    dec = [w["decoded_accuracy"].get("within_pct") for w in walks if w.get("decoded_accuracy")]
    off = [w["display_offset"]["median_m"] for w in walks if w.get("display_offset") and w["display_offset"]["median_m"] is not None]
    L = [f"# Render of the FINAL tracker on {R['test']}: acceptance (measured results only)", "",
         f"Rules: `reports/tracking/render-rules.md`. Model: {R['model']}. Display head: {R['display_head']}.",
         f"Every walk's committed line and lock equal the corrected decode (`CR.relgateU`): "
         f"committed {E['committed_equal']}/{E['n']}, lock {E['lock_equal']}/{E['n']}.", "",
         "| check | holds |", "|---|---|"]
    L += [f"| {k} | {'yes' if v else '**NO**'} |" for k, v in S.items() if k != "ALL_PASS"]
    L += ["", f"**All checks: {'PASS' if S['ALL_PASS'] else 'FAIL'}.**", "", "## Rule 5, the computed quantities", "",
          f"- jumps over 0.5 m: {R['jumps']['total']}, of which at the lock {R['jumps']['caused_by_the_lock']} and at a switch "
          f"{R['jumps']['caused_by_a_switch']};",
          f"- frames without a dot: {R['dot_visible']['frames_without_dot']} of {R['dot_visible']['frames']} (the contract: 0); "
          f"inside walks {R['dot_visible']['missing_after_first_legal']} of {R['dot_visible']['expected']};",
          f"- the drawn-window causal bound: {R['causal_bound_s']:+.3f} s (must be at or below 0);",
          f"- the evidence causal bound: {R['causal_evidence_bound_s']:+.3f} s (must be at or below 0).", "",
          "## Rule 4: two numbers, never added", "",
          f"- decoded accuracy (the dot against where the walker was at the moment the decoder names), within 0.5 m: "
          f"mean over walks {np.mean([x for x in dec if x is not None]):.1f} percent" if dec else "- decoded accuracy: -",
          f"- on-screen tracking (against the delayed marker, the anchor segment excluded), within 0.5 m: "
          f"mean over walks {np.mean([x for x in trk if x is not None]):.1f} percent" if trk else "- on-screen tracking: -",
          f"- display offset (how far the walker moves during the lag): median over walks {np.median(off):.2f} m" if off else "- display offset: -",
          "", f"Switches (arm C): {R['switching']['switches']} (wrong to right {R['switching']['w2r']}, right to wrong "
          f"{R['switching']['r2w']}, wrong to wrong {R['switching']['w2w']}); the drawn line ends on the committed line on "
          f"{R['switching']['end_on_committed']} of {len(walks)} walks.", "",
          f"Committed correct: {pct([w['found'] for w in walks])} percent; lock correct: {pct([w['lock_correct'] for w in walks])} "
          f"percent ({len(walks)} walks; these equal the corrected decode, they are not a new measurement).", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--stems", nargs="*", default=None)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--end", choices=["final", "pooled_smoke"], default="final")
    ap.add_argument("--variant", default="relgateU")
    ap.add_argument("--ref", default=None, help="the decode folder the render must equal (default CR.<variant>)")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return inner(a.cell, a.stems, not a.no_video, a.end, a.variant, a.ref)
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(a.cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT)
    extra = (["--stems", *a.stems] if a.stems else []) + (["--no-video"] if a.no_video else [])
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_render", "--inner", "--cell", a.cell,
                            "--end", a.end, "--variant", a.variant] + (["--ref", a.ref] if a.ref else []) + extra, cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
