"""The live system's equality gates, run on replayed Room A recordings. Evidence, not assertion.

    OMP_NUM_THREADS=1 python3 -m pipeline.live.gates --gate 1          # every window, all six recordings
    OMP_NUM_THREADS=1 python3 -m pipeline.live.gates --gate 1 --every 25

THE REPLAY. The Room A stand-in: session 03's six walk recordings, the heads `s0102_to_s03` trained on
sessions 01 and 02, and the offline objects built from them (`shipped_pool_emissions`, the
d4_headline decisions). Each gate feeds the live code the SAME windows the offline tree holds, so a
difference is the live code's own and nothing else's. Whether the live engine cuts those same
windows from raw packets is a different question, answered separately (`--gate stream`), exactly as
`pipeline/live/tracker_live.py` keeps its two measurements apart.

Results go to runs/live/gate<N>.json. Nothing is written under data/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)

import numpy as np                                                                # noqa: E402

TAG, TRAIN, TEST = "s0102_to_s03", ("01", "02"), ("03",)
OUT = os.path.join(REPO_ROOT, "runs", "live")
#: gate 1's tolerance on a log emission: the live head runs one window where the offline one ran
#: 256, so float32 summation order differs; anything above this is a real difference
EMISSION_TOL = 1e-4


def replay_source():
    """The offline objects of the stand-in: pieces, pooled emissions, and the walk recordings."""
    from pipeline.constrained.g3_final import shipped_pool_emissions
    from pipeline.constrained.night_common import shipped_pieces
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    src, info = shipped_pool_emissions(TAG, TRAIN, TEST, False, st, kind, alpha)
    walks = [s for s in src if "_walk" in s[0] and "_DEMO_" not in s[0]]
    return (st, cfg, ne, transit, kind, alpha), walks, info


def offline_windows(stem: str, rec):
    """The stored window array and its RSSI, exactly as the offline heads read them."""
    from pipeline.constrained.recordings import ROOM, WINDOWS_ROOT, load_rssi
    X = np.load(os.path.join(REPO_ROOT, WINDOWS_ROOT, ROOM, f"session_{TEST[0]}", f"{stem}.npz"))["X"]
    return X, load_rssi(TEST[0], stem, rec.t0_epoch)


def gate1(every: int = 1) -> dict:
    """The five-head pool: each live window's pooled emission against `shipped_pool_emissions`."""
    from pipeline.live.pool import LivePool
    (st, _cfg, _ne, _tr, kind, alpha), walks, info = replay_source()
    lp = LivePool(TAG, TRAIN, TEST, st, kind, alpha)
    rows, times = [], []
    for stem, rec, ge, e in walks:
        X, rssi = offline_windows(stem, rec)
        n = min(len(e), len(X))
        idx = list(range(0, n, every))
        de, dg, am = [], [], 0
        for i in idx:
            t = time.monotonic()
            ei, gi = lp.window(X[i], rssi[i])
            times.append(time.monotonic() - t)
            de.append(float(np.max(np.abs(ei - e[i]))))
            dg.append(abs(gi - float(ge[i])))
            am += int(np.argmax(ei) == np.argmax(e[i]))
        rows.append({"stem": stem, "windows": len(idx), "max_abs_emission_diff": max(de),
                     "max_abs_gate_diff": max(dg), "argmax_equal": am,
                     "EQUAL": bool(max(de) <= EMISSION_TOL and max(dg) == 0.0 and am == len(idx))})
    t = np.asarray(times[1:] or times)
    return {"gate": 1, "what": "live five-head pool against g3_final.shipped_pool_emissions, window by window",
            "tag": TAG, "heads": lp.head_names, "offline_pool": info, "every": every,
            "emission_tolerance": EMISSION_TOL, "rows": rows,
            "windows": sum(r["windows"] for r in rows),
            "windows_equal": sum(r["windows"] for r in rows if r["EQUAL"]),
            "per_window_s": {"median": float(np.median(t)), "p95": float(np.percentile(t, 95)),
                             "max": float(t.max())},
            "PASSED": all(r["EQUAL"] for r in rows)}


def gate2(every: int = 1) -> dict:
    """The start terms, A2 plus a_veto_1.0: each pass's live terms against the offline ones."""
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.recordings import load_meta
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.constrained.u1_adapt import calibration_indices, session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
    from pipeline.live.pool import LivePool
    from pipeline.live.start_terms import LiveStartTerms
    (st, *_rest), walks, _info = replay_source()
    # OFFLINE, exactly as dc2_run.do_decode builds the committed decision's terms
    a2 = start_terms(TRAIN, TEST, st, A2_WEIGHT)
    cache = {}
    Xtr, ytr, _k, _w, _u, _a = session_rows(TRAIN, st, ADAPT_MODE, cache)
    Xte, _y, kte, _w2, _u2, _a2 = session_rows(TEST, st, ADAPT_MODE, cache)
    _p, proba, classes = fit_reader(Xtr, ytr, Xte, False)
    ref = merged(dict(a2), term_veto(kte, proba, classes, st, VETO_THR, VETO_W))
    # LIVE
    reader = tag_for_session(TEST[0])
    lst = LiveStartTerms(TRAIN, reader, st)
    rows = []
    for stem, rec, _ge, _e in walks:
        X, rssi = offline_windows(stem, rec)
        t0 = np.asarray(rec.t0, float)
        fp = first_presses(TEST[0], stem)
        cal = calibration_indices(rec, fp)
        ad = lst.adapt(LivePool.features(X[cal]), rssi[cal]) if len(cal) else lst.adapt(np.zeros((0,)), np.zeros((0,)))
        for pid, nm, _a, _b in rec.pass_spans()[::every]:
            press = fp.get(int(pid))
            key = f"{TEST[0]}|{stem}|{int(pid)}"
            if press is None or key not in ref:
                continue
            idx = np.flatnonzero((t0 + 2.0 >= press - 2.0 - 1e-6) & (t0 + 2.0 <= press + 1.0 + 1e-6))
            F, R = LivePool.features(X[idx]), rssi[idx].astype(np.float32)
            live = lst.terms(lst.a2_row(t0[idx], F, R, press), lst.veto_row(t0[idx], F, R, press))
            off = ref[key]
            lines = sorted(set(off) | set(live))
            d = max(abs(live.get(l, 0.0) - off.get(l, 0.0)) for l in lines)
            vl = sorted(l for l in lines if live.get(l, 0.0) <= -2.0)
            vo = sorted(l for l in lines if off.get(l, 0.0) <= -2.0)
            rows.append({"key": key, "line": nm, "adapted": ad["adapted"], "max_abs_term_diff": d,
                         "vetoed_live": vl, "vetoed_offline": vo,
                         "EQUAL": bool(d <= TERM_TOL and vl == vo)})
    return {"gate": 2, "what": "live start terms (A2 + a_veto_1.0) against the offline ones, pass by pass",
            "reader_tag": reader, "term_tolerance": TERM_TOL, "passes": len(rows),
            "passes_equal": sum(r["EQUAL"] for r in rows),
            "max_abs_term_diff": max((r["max_abs_term_diff"] for r in rows), default=None),
            "rows": rows, "PASSED": bool(rows) and all(r["EQUAL"] for r in rows)}


#: gate 2's tolerance on a start term, in nats: the position and embedding heads run on this pass's
#: windows where the offline ones ran on the whole recording, so float32 summation order differs
TERM_TOL = 1e-4

def shipped_decode_opts(st, term):
    """The committed decision's options, exactly as d4_headline and dc2_run.do_decode set them."""
    from pipeline.constrained.r1_oldcensus import shipped_opts
    o = shipped_opts(st, TRAIN)
    o["entry"] = "soft"
    o["entry_window_m"] = 1.0
    o["start_term"] = term
    return o


def replay_decoder(stem, rec, e, ge, terms, pieces, opts_base):
    """Push one recording through LiveDecoder window by window, pressing at each pass's first press."""
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.live.decoder import LiveDecoder
    st, cfg, ne, transit, _k, _a = pieces
    dec = LiveDecoder(st, cfg, ne, transit, opts_base, TEST[0], stem)
    fp = first_presses(TEST[0], stem)
    order = sorted((press, int(pid)) for pid, press in fp.items()
                   if int(pid) in {int(q[0]) for q in rec.pass_spans()})
    t0 = np.asarray(rec.t0, float)
    rows, pi = [], 0
    for k in range(min(len(e), len(t0))):
        while pi < len(order) and t0[k] + 2.0 > order[pi][0]:
            press, pid = order[pi]
            dec.press(press, pid)
            dec.set_term(pid, terms.get(f"{TEST[0]}|{stem}|{pid}"))
            pi += 1
        rows += dec.push(t0[k], float(rec.t0_epoch[k]), e[k], float(ge[k]))
    for r in dec.close():
        r["live_decided_at_close"] = True
        rows.append(r)
    return rows


def gate3(every: int = 1, inputs: str = "offline") -> dict:
    """The committed decision: the live decoder's final line against the SHIPPED decision, every pass.

    inputs="offline": the offline pooled emissions and committed start terms, so only the decoder is on
    trial. inputs="live": the live pool (gate 1) and the live start terms (gate 2), so the whole live
    compute path is.
    """
    from pipeline.constrained.n2_arms import run
    from pipeline.constrained.veto import committed_start_terms
    pieces, walks, _info = replay_source()
    st = pieces[0]
    terms = committed_start_terms(TRAIN, TEST, st, {})
    if inputs == "live":
        walks, terms = live_inputs(pieces, walks)
    ship = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "fh", "d4_headline", "rows_veto.json"),
                          encoding="utf-8"))
    ship = {"|".join(r["key"].split("|")[1:]): r["final_line"] for r in ship if r["key"].startswith(TAG + "|")}
    offline = {r["key"]: r for r in run(walks, st, pieces[1], pieces[2], pieces[3],
                                        shipped_decode_opts(st, terms), subs=False)}
    rows = []
    for stem, rec, ge, e in walks:
        for r in replay_decoder(stem, rec, e, ge, terms, pieces, shipped_decode_opts(st, None)):
            key = r["key"]
            off = offline.get(key) or {}
            rows.append({"key": key, "live_final": r["final_line"], "shipped_final": ship.get(key),
                         "offline_exit_window": off.get("own_end_i"), "live_exit_window": r["live_exit_window"],
                         "decided_at_window": r["live_decided_at_window"],
                         "decided_at_close": bool(r.get("live_decided_at_close", False)),
                         "decided_after_press_s": round(float(rec.t0[r["live_decided_at_window"]]) + 2.0
                                                        - r["live_press"], 2),
                         "EQUAL": bool(r["final_line"] == ship.get(key)
                                       and r["live_exit_window"] == off.get("own_end_i"))})
    n_ship = sum(1 for k in ship if k.split("|")[1] in {w[0] for w in walks})
    return {"gate": 3, "inputs": inputs,
            "what": "live committed decision against d4_headline's shipped decision and the offline exit",
            "passes_shipped": n_ship, "passes_decided_live": len(rows),
            "passes_equal": sum(r["EQUAL"] for r in rows),
            "passes_decided_at_close": sum(r["decided_at_close"] for r in rows),
            "decided_after_press_s": {"median": float(np.median([r["decided_after_press_s"] for r in rows])),
                                      "max": float(max(r["decided_after_press_s"] for r in rows))} if rows else None,
            "rows": rows, "PASSED": bool(rows) and len(rows) == n_ship and all(r["EQUAL"] for r in rows)}


def live_inputs(pieces, walks):
    """The whole live compute path: pooled emissions from LivePool and terms from LiveStartTerms."""
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.constrained.u1_adapt import calibration_indices
    from pipeline.live.pool import LivePool
    from pipeline.live.start_terms import LiveStartTerms
    st, _c, _n, _t, kind, alpha = pieces
    lp = LivePool(TAG, TRAIN, TEST, st, kind, alpha)
    lst = LiveStartTerms(TRAIN, tag_for_session(TEST[0]), st)
    out, terms = [], {}
    for stem, rec, _ge, e_off in walks:
        X, rssi = offline_windows(stem, rec)
        n = min(len(e_off), len(X))
        cache = os.path.join(OUT, "cache", f"live_pool_{stem}.npz")
        if os.path.exists(cache):
            d = np.load(cache)
            e, ge = d["e"], d["ge"]
        else:
            e = np.zeros((n, e_off.shape[1]))
            ge = np.zeros(n)
            for i in range(n):
                e[i], ge[i] = lp.window(X[i], rssi[i])
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            np.savez_compressed(cache, e=e, ge=ge)
        t0 = np.asarray(rec.t0, float)
        fp = first_presses(TEST[0], stem)
        cal = calibration_indices(rec, fp)
        lst.adapt(LivePool.features(X[cal]) if len(cal) else np.zeros((0,)), rssi[cal])
        for pid, press in fp.items():
            idx = np.flatnonzero((t0 + 2.0 >= press - 2.0 - 1e-6) & (t0 + 2.0 <= press + 1.0 + 1e-6))
            if len(idx) < 2:
                continue
            F, R = LivePool.features(X[idx]), rssi[idx].astype(np.float32)
            terms[f"{TEST[0]}|{stem}|{int(pid)}"] = lst.terms(lst.a2_row(t0[idx], F, R, press),
                                                              lst.veto_row(t0[idx], F, R, press))
        out.append((stem, rec, ge, e))
    return out, terms


def stream_windows(stem: str, end_presses: bool = True, causal_anchor: bool = False) -> tuple:
    """Replay one recording's packets and presses through LiveStream: ({round(t0, 6): record}, stream).

    A record is kept as last written: emitted, then replaced if a press re-cut it."""
    import pipeline.io.windows as W
    from pipeline.live.replay import feed, recording_events
    from pipeline.live.stream import LiveStream
    sdir = os.path.join(REPO_ROOT, "data", "room_A", f"session_{TEST[0]}")
    ls = LiveStream(W.session_baseline(W.baseline_dir_for(sdir, stem)))
    final = {}

    def on_windows(recs):
        for r in recs:
            final[r["k"]] = r

    def on_press(_pid, res):
        for r in res["windows"]:
            final[r["k"]] = r
        for k in res["dropped"] + res["withdrawn"]:
            final.pop(k, None)

    def on_close(withdrawn):
        for k in withdrawn:
            final.pop(k, None)

    ev, _info = recording_events(sdir, stem, end_presses=end_presses, causal_anchor=causal_anchor)
    t = time.time()
    feed(ls, ev, on_windows, on_press, on_close)
    ls.seconds = time.time() - t
    return {r["t0"]: r for r in final.values()}, ls


def gate_stream(every: int = 1, end_presses: bool = True) -> dict:
    """The live stream's windows against the tree's, window by window: t0, the stored float16 array,
    and the RSSI series. Windows a press does not re-cut (older than RECUT_BACK_S before a later press,
    in a long gap) are counted apart: nothing reads them, and they stay on the previous phase."""
    from pipeline.live.stream import RECUT_BACK_S
    _pieces, walks, _info = replay_source()
    rows = []
    for stem, rec, _ge, _e in walks:
        X, rssi = offline_windows(stem, rec)
        live, ls = stream_windows(stem, end_presses=end_presses)
        sc = json.load(open(os.path.join(REPO_ROOT, "data", "room_A", f"session_{TEST[0]}", f"{stem}.gt.json"),
                            encoding="utf-8"))
        ps = sorted(sc["passes"], key=lambda p: float(p["t_start"]))
        bounds = np.asarray([0.5 * (float(ps[i]["t_end"]) + float(ps[i + 1]["t_start"])) for i in range(len(ps) - 1)])
        t0 = np.asarray(rec.t0, float)
        n_read = n_t0 = n_x = n_r = n_ep = 0
        n_unread, worst = 0, 0.0
        for i in range(0, len(t0), every):
            base = np.round(t0[i] / 0.5) * 0.5
            j = int(np.searchsorted(bounds, base, side="right"))
            read = j == 0 or t0[i] >= float(ps[j]["t_start"]) - RECUT_BACK_S
            if not read:
                n_unread += 1
                continue
            n_read += 1
            r = live.get(round(float(t0[i]), 6))
            if r is None:
                continue
            n_t0 += 1
            a = r["X"].astype(np.float16)
            eq = bool(np.array_equal(a, X[i]))
            n_x += int(eq)
            if not eq:
                worst = max(worst, float(np.max(np.abs(a.astype(np.float32) - X[i].astype(np.float32)))))
            n_r += int(np.array_equal(r["rssi"], rssi[i]))
            n_ep += int(r["t0_epoch"] == round(float(rec.t0_epoch[i]), 6))
        # a live window in the read range that the tree does not hold is a failure. The range is
        # decided by the TREE's segment for the window's base start, never by the segment the live
        # window happened to be cut in (a window a press never re-cut keeps the older one)
        tree_t0 = {round(float(x), 6) for x in t0}
        extra = []
        for tt, r in live.items():
            if tt in tree_t0:
                continue
            base = ls.first_base + r["k"] * ls.stride_s
            j = int(np.searchsorted(bounds, base, side="right"))
            if j == 0 or base + ls.passes[j]["shift"] >= float(ps[j]["t_start"]) - RECUT_BACK_S:
                extra.append(tt)
        extra.sort()
        row = {"stem": stem, "windows_offline": int(len(t0)), "windows_read": n_read, "t0_found": n_t0,
               "live_windows_in_read_range_not_in_tree": len(extra), "extra_t0": extra[:5],
               "X_equal": n_x, "rssi_equal": n_r, "t0_epoch_equal": n_ep, "max_abs_diff_unequal": worst,
               "windows_not_recut_unread": n_unread, "live_windows": len(live),
               "recuts": [{k: v for k, v in c.items()} for c in ls.recuts],
               "replay_seconds": round(ls.seconds, 1)}
        row["EQUAL"] = bool(n_read and n_t0 == n_read and n_x == n_read and n_r == n_read and n_ep == n_read
                            and not extra)
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "recuts"}), flush=True)
    return {"gate": "stream", "end_presses": end_presses,
            "what": "LiveStream's windows, from replayed packets and presses, against the tree's windows",
            "anchoring": "offline (whole-file fit), as the tree; the causal fit is measured separately",
            "every": every, "rows": rows, "PASSED": bool(rows) and all(r["EQUAL"] for r in rows)}


def gate4(every: int = 1) -> dict:
    """The display, frame by frame: every frame computed from the windows that had ended by its time,
    against the frame `f3_render` drew (its saved `rpost`), and the lock, the switch and the anchor.

    Inputs are the offline ones (the pooled and DISP_END emissions, the start terms), so only the
    display is on trial; gates 1 to 3 cover the rest."""
    import pipeline.live.display as D
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.s2_display import end_emissions
    from pipeline.constrained.veto import A2_WEIGHT, committed_start_terms
    (st, cfg, ne, transit, kind, alpha), walks, _info = replay_source()
    f3 = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "fh", "f3_render", "results.json"),
                        encoding="utf-8"))
    sett = D.settings()
    # f3_render's locals, as it recorded them, against this module's constants
    sw = f3.get("switching") or {}
    const = {"latency_s": (D.LATENCY_S, f3.get("display_latency_s")), "lag_s": (D.LAG_S, f3.get("lag_s")),
             "commit_delay_s": (D.DELAY_S, (f3.get("shipped") or {}).get("commit_delay_s")),
             "shift_w": (D.SHIFT_W, (f3.get("anchor_segment") or {}).get("shift_w")),
             "fps": (D.FPS, f3.get("fps")),
             "display_cap": (D.DISPLAY_CAP_M_PER_WINDOW, ((f3.get("shipped") or {}).get("motion_model") or {})
                             .get("display_max_advance_m_per_window")),
             "display_sd_scale": (D.DISPLAY_SD_SCALE, ((f3.get("shipped") or {}).get("motion_model") or {})
                                  .get("display_sd_scale")),
             "display_arm": (sett["shipped_display"], (f3.get("shipped") or {}).get("display_arm")),
             "switch_arm": ((sett["switch"] or {}).get("arm"), sw.get("arm")),
             "switch_theta": ((sett["switch"] or {}).get("theta"), sw.get("theta")),
             "switch_max": ((sett["switch"] or {}).get("max_switches"), sw.get("max_switches")),
             "switch_final_m": ((sett["switch"] or {}).get("final_m"), sw.get("final_m")),
             "switch_radius_m": ((sett["switch"] or {}).get("radius_m"), sw.get("radius_m"))}
    const_ok = all(a == b for a, b in const.values())
    a2 = start_terms(TRAIN, TEST, st, A2_WEIGHT)
    committed = committed_start_terms(TRAIN, TEST, st)
    e_end, _cov = end_emissions(TAG, TRAIN, TEST, st, alpha)
    opts_disp = shipped_decode_opts(st, None)
    caps = D.CapSwitch()
    rows, t_all = [], time.time()
    for stem, rec, ge, e in walks:
        who = stem.replace("participant_", "").split("_")[0]
        # keyed session|stem|pass_id, the standing pairing key (tests/test_pass_pairing_key.py)
        ref = {f"{TEST[0]}|{stem}|{int(w['pass_id'])}": w for w in f3["recordings"][who]["walks"]}
        sc = json.load(open(os.path.join(REPO_ROOT, "data", "room_A", f"session_{TEST[0]}", f"{stem}.gt.json"),
                            encoding="utf-8"))
        ps = sorted(sc["passes"], key=lambda p: float(p["t_start"]))
        want = {int(p["pass_id"]) for p in ps[::every]}
        disp = D.LiveDisplay(st, cfg, ne, transit, opts_disp, TEST[0], stem, sett, caps)
        t0 = np.asarray(rec.t0, float)
        disp.set_origin(float(t0[0]))
        ee = e_end[stem]
        events = sorted([(float(p["t_start"]), "press", p) for p in ps if int(p["pass_id"]) in want]
                        + [(float(p["t_end"]), "end", p) for p in ps if int(p["pass_id"]) in want])
        ei = 0
        t_rec = time.time()
        for k in range(len(t0)):
            # a press is known once it has happened; the window that ends first after it is the
            # earliest moment the live system can act on it
            while ei < len(events) and events[ei][0] < t0[k] + 2.0:
                tt, kind_, p = events[ei]
                key = f"{TEST[0]}|{stem}|{int(p['pass_id'])}"
                if kind_ == "press":
                    disp.press(int(p["pass_id"]), tt, a2.get(key), committed.get(key))
                else:
                    disp.end_press(int(p["pass_id"]), tt)
                ei += 1
            disp.push(t0[k], float(rec.t0_epoch[k]), e[k], float(ge[k]), ee[k])
        disp.close()
        for pid in sorted(want):
            w = ref.get(f"{TEST[0]}|{stem}|{pid}")
            if w is None:
                continue
            got = disp.out.get(pid, {})
            meta = disp.meta.get(pid, {})
            # f3_render's own frame grid: np.arange(t[0], t[-1] + WINDOW_S, 1 / FPS)
            grid = np.arange(float(t0[0]), float(t0[-1]) + 2.0, 1.0 / D.FPS)
            post = [x for x in (float(v) for v in grid)
                    if float(w["t_press_start"]) <= x < float(w["t_press"]) + D.LATENCY_S
                    and x >= float(w["t_dec0"])]
            live_post = [got.get(round(x, 4)) for x in post]
            ref_post = [tuple(v) for v in (w.get("rpost") or [])]
            n_eq = sum(1 for a, b in zip(live_post, ref_post) if a is not None and tuple(a) == b)
            first_bad = next((i for i, (a, b) in enumerate(zip(live_post, ref_post))
                              if a is None or tuple(a) != b), None)
            ref_sw = [(round(float(s["x"]), 6), s["old"], s["new"]) for s in (w.get("mid_switches") or [])]
            live_sw = [(round(float(s["x"]), 6), s["old"], s["new"]) for s in meta.get("switches", [])]
            row = {"key": f"{TEST[0]}|{stem}|{pid}", "frames_post": len(ref_post), "frames_live": len(live_post),
                   "frames_equal": n_eq, "first_unequal_frame": first_bad,
                   "lock_live": meta.get("lock_line"), "lock_f3": w.get("locked_line"),
                   "switches_live": live_sw, "switches_f3": ref_sw,
                   "line_entry_equal": bool(meta.get("line_entry") is not None
                                            and tuple(meta["line_entry"]) == tuple(w["line_entry_xy"])),
                   "t_dec0_equal": bool(meta.get("t_dec0") == w.get("t_dec0")),
                   "park_until_equal": bool(meta.get("park_until") == w.get("park_until"))}
            if first_bad is not None and first_bad < len(ref_post) and live_post[first_bad] is not None:
                a, b = live_post[first_bad], ref_post[first_bad]
                row["first_diff_m"] = float(np.hypot(a[0] - b[0], a[1] - b[1]))
            row["EQUAL"] = bool(len(live_post) == len(ref_post) and n_eq == len(ref_post)
                                and row["lock_live"] == row["lock_f3"] and live_sw == ref_sw
                                and row["line_entry_equal"] and row["t_dec0_equal"] and row["park_until_equal"])
            rows.append(row)
        print(json.dumps({"stem": stem, "walks": sum(1 for r in rows if stem in r["key"]),
                          "equal": sum(1 for r in rows if stem in r["key"] and r["EQUAL"]),
                          "decodes": disp.n_decodes, "seconds": round(time.time() - t_rec, 1)}), flush=True)
    return {"gate": 4, "what": ("the live display, each frame from the windows ended by its time, against "
                                "f3_render's drawn frames (rpost), lock, switch and anchor"),
            "constants": {k: {"live": a, "f3_render": b, "equal": a == b} for k, (a, b) in const.items()},
            "constants_equal": const_ok, "walks": len(rows), "walks_equal": sum(r["EQUAL"] for r in rows),
            "frames": sum(r["frames_post"] for r in rows), "frames_equal": sum(r["frames_equal"] for r in rows),
            "minutes_compute": round((time.time() - t_all) / 60.0, 2),
            "rows": rows, "PASSED": bool(rows) and const_ok and all(r["EQUAL"] for r in rows)}


from pipeline.live.identify import nan_equal as _nan_equal                          # noqa: E402


def gate5(every: int = 1) -> dict:
    """Identification: live extraction and prediction against `id29_dc2_score`, on id29's own SYNTHETIC
    DC2 recordings (no DC2 identification recording exists before 26 September; Room A has none in
    the DC2 layout). The recordings are written under runs/live/, never under data/.

    (a) each pass's features, single-link rows, spectrogram and row, from packets and presses pushed
        as they would arrive, against `extract` on the finished files;
    (b) each day-2 natural pass predicted ON ITS OWN from the day-1 natural passes (PRIMARY with its
        probabilities, and S0), against the offline P1 fold predicted as one batch."""
    import importlib.util
    import shutil

    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import idmax_eval as E
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live.identify import LINKS, LiveIdentifier, LiveIdRecording
    root = os.path.join(OUT, "id_synthetic")
    if os.path.isdir(root):
        shutil.rmtree(root)                     # this gate's own synthetic output, nothing else
    os.makedirs(root)
    spec = importlib.util.spec_from_file_location("t_id29", os.path.join(REPO_ROOT, "tests", "test_id29_dc2_score.py"))
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    cfg = T.make_cfg(root)
    assert "data" + os.sep + "room_" not in os.path.abspath(cfg.data_root), "synthetic data must not land in data/"
    T.make_dc2(cfg.data_root)
    found, bad = D._scan(cfg.data_root)
    t_off = time.time()
    dc2 = D.extract(cfg, found)
    ra = T.synthetic_room_a()
    M = D.build(dc2, ra)
    dc = M["room"] == "DC2"
    d1n = np.flatnonzero(dc & (M["day"] == 1) & (M["block"] == "natural"))
    d2n = np.flatnonzero(dc & (M["day"] == 2) & (M["block"] == "natural"))
    fc = E.FConf("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")
    off_pred, off_P, off_cl = E.fit_predict(fc, "rf", d1n, d2n, M["y"][d1n], M, proba=True)
    s0_pred, s0_P, s0_cl = E.fit_predict(E.FConf("dc2e_S0", "S0", "-"), "lda", d1n, d2n, M["y"][d1n], M,
                                         proba=True)
    # the id29 closure itself, so the batch above is id29's PRIMARY and not a look-alike
    closure = np.asarray(D.predictors(cfg, M)["PRIMARY"](d1n, d2n, M["y"][d1n]))
    off_seconds = time.time() - t_off
    # LIVE: every walk recording's packets in arrival order, the presses at their times
    live, t_ext = [], []
    for (name, day, what), rec in sorted(found.items()):
        if what.startswith("empty"):
            continue
        lr = LiveIdRecording(name, day, what)
        frs = {L: read_capture_file(os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin"))[1] for L in LINKS}
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        ev = []
        for L in LINKS:
            tm = np.asarray(frs[L]["t_mono"], float)
            for a in range(0, len(tm), 15):             # ~0.1 s chunks, as a reader would hand them over
                ev.append((float(tm[min(a + 14, len(tm) - 1)]), 1, L, a))
        for q in gt["passes"]:
            ev.append((float(q["t_start"]), 0, "press", float(q["t_start"])))
            ev.append((float(q["t_end"]), 0, "end", float(q["t_end"])))
        ev.sort(key=lambda e: (e[0], e[1]))
        for e_ in ev:
            t_ = time.time()
            if e_[2] == "press":
                lr.press(e_[3])
            elif e_[2] == "end":
                n_before = len(lr.done)
                lr.end_press(e_[3])
            else:
                n_before = len(lr.done)
                lr.push(e_[2], frs[e_[2]][e_[3]:e_[3] + 15])
            if e_[2] != "press" and len(lr.done) > n_before:
                t_ext.append(time.time() - t_)
        lr.close()
        live += lr.done
    # (a) features, in extract's order
    n = min(len(live), len(dc2["rows"]))
    feat_eq = sum(_nan_equal(live[i]["feats"], dc2["feats"][i]) for i in range(n))
    single_eq = sum(all(_nan_equal(live[i]["single"][k], dc2["single"][k][i]) for k in dc2["single"]) for i in range(n))
    spec_eq = sum(bool(np.array_equal(live[i]["spec"], dc2["specs"][i], equal_nan=True)) for i in range(n))
    row_eq = sum(_nan_equal({k: v for k, v in live[i]["row"].items()},
                            {k: v for k, v in dc2["rows"][i].items()}) for i in range(n))
    # (b) each day-2 natural pass on its own
    is_ = lambda r, d, b: r["row"]["day"] == d and r["row"]["block"] == b          # noqa: E731
    enrolled = [r for r in live if is_(r, 1, "natural")]
    tests = [r for r in live if is_(r, 2, "natural")]
    ident = LiveIdentifier(enrolled, ra)
    t_p = time.time()
    got = ident.predict(tests[::every])
    pred_seconds = (time.time() - t_p) / max(1, len(got))
    idx = list(range(0, len(tests), every))
    pred_eq = sum(got[j]["pred"] == str(off_pred[i]) for j, i in enumerate(idx))
    proba_eq = sum(all(got[j]["proba"][str(c)] == float(off_P[i][ci]) for ci, c in enumerate(off_cl))
                   for j, i in enumerate(idx))
    s0_eq = sum(got[j]["s0_pred"] == str(s0_pred[i])
                and all(got[j]["s0_proba"][str(c)] == float(s0_P[i][ci]) for ci, c in enumerate(s0_cl))
                for j, i in enumerate(idx))
    res = {"gate": 5, "what": ("identification: live features and single-pass predictions against "
                               "id29_dc2_score on its own synthetic DC2 recordings"),
           "data": os.path.relpath(cfg.data_root, REPO_ROOT), "layout_problems": bad,
           "passes_offline": len(dc2["rows"]), "passes_live": len(live),
           "features_equal": feat_eq, "single_link_equal": single_eq, "spectrogram_equal": spec_eq,
           "rows_equal": row_eq,
           "offline_batch_equals_id29_closure": bool(np.array_equal(closure, off_pred)),
           "day2_natural_passes": len(idx), "primary_pred_equal": pred_eq, "primary_proba_equal": proba_eq,
           "s0_equal": s0_eq, "classes": [str(c) for c in off_cl], "chance": 1.0 / len(off_cl),
           "accuracy_primary_pct": round(100.0 * float(np.mean([g["pred"] == str(M["y"][d2n][i])
                                                                for g, i in zip(got, idx)])), 2),
           "accuracy_s0_pct": round(100.0 * float(np.mean([g["s0_pred"] == str(M["y"][d2n][i])
                                                           for g, i in zip(got, idx)])), 2),
           "extract_seconds_per_pass": {"median": float(np.median(t_ext)) if t_ext else None,
                                        "max": float(np.max(t_ext)) if t_ext else None},
           "predict_seconds_per_pass": round(pred_seconds, 3), "offline_seconds": round(off_seconds, 1),
           "wait_after_end_press_s": __import__("pipeline.live.identify", fromlist=["WAIT_S"]).WAIT_S,
           "example": got[0] if got else None}
    res["PASSED"] = bool(n and len(live) == len(dc2["rows"]) and feat_eq == n and single_eq == n
                         and spec_eq == n and row_eq == n and res["offline_batch_equals_id29_closure"]
                         and pred_eq == len(idx) and proba_eq == len(idx) and s0_eq == len(idx))
    return res


from pipeline.live.timing import live_queue                                        # noqa: E402


def gate_e2e(every: int = 1, causal: bool = False) -> dict:
    """END TO END, and gate 6's timing: raw packets and the operator's presses through the whole
    tracking session, against the shipped decision (d4_headline) and f3_render's drawn frames.

    causal=False anchors the device clocks with the offline whole-file fit, so equality is the claim.
    causal=True anchors them as a live system must (`anchor.CausalAnchor`): that is a MEASUREMENT of
    what live data changes, reported with its numbers and never tuned. `every` > 1 runs every Nth
    recording only."""
    import pipeline.io.windows as W
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.live.display import LATENCY_S
    from pipeline.live.pool import LiveEndHead, LivePool
    from pipeline.live.replay import recording_events
    from pipeline.live.start_terms import LiveStartTerms
    from pipeline.live.tracking import TrackingSession
    pieces, walks, _info = replay_source()
    st, cfg, ne, transit, kind, alpha = pieces
    comp = {"pool": LivePool(TAG, TRAIN, TEST, st, kind, alpha), "end_head": LiveEndHead(TAG, TRAIN, st, alpha),
            "terms": LiveStartTerms(TRAIN, tag_for_session(TEST[0]), st)}
    ship = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "fh", "d4_headline", "rows_veto.json"),
                          encoding="utf-8"))
    ship = {"|".join(r["key"].split("|")[1:]): r["final_line"] for r in ship if r["key"].startswith(TAG + "|")}
    f3 = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "fh", "f3_render", "results.json"),
                        encoding="utf-8"))
    rows, per_rec, t_win, t_press, t_cut, queue_all = [], [], [], [], [], []
    for stem, rec, _ge, _e in walks[::every]:
        who = stem.replace("participant_", "").split("_")[0]
        ref = {f"{TEST[0]}|{stem}|{int(w['pass_id'])}": w for w in f3["recordings"][who]["walks"]}
        sdir = os.path.join(REPO_ROOT, "data", "room_A", f"session_{TEST[0]}")
        s = TrackingSession(tag=TAG, train=TRAIN, test=TEST, reader_tag=tag_for_session(TEST[0]),
                            baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)), session=TEST[0],
                            stem=stem, pieces=pieces, components=comp)
        ev, _inf = recording_events(sdir, stem, end_presses=True, causal_anchor=causal)
        t_rec = time.time()
        for e_ in ev:
            if e_[2] == "frame":
                _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
                if ts is None:
                    s.rssi(n, t_host, rssi)
                else:
                    s.packet(n, ts, amp, t_host, t_mono, rssi)
            elif e_[2] == "press":
                s.press(e_[4], e_[3])
            else:
                s.end_press(e_[4], e_[3])
        s.close()
        dec = {f"{TEST[0]}|{stem}|{d['pass_id']}": d for d in s.decisions}
        t0_all = np.asarray(s.decoder.t0, float)
        grid = np.arange(float(t0_all[0]), float(t0_all[-1]) + 2.0, 0.1)
        n_eq_rec = 0
        for key, w in sorted(ref.items(), key=lambda kv: int(kv[1]["pass_id"])):
            pid = int(w["pass_id"])
            d = dec.get(key)
            got = s.display.out.get(pid, {})
            meta = s.display.meta.get(pid, {})
            post = [float(x) for x in grid if float(w["t_press_start"]) <= x < float(w["t_press"]) + LATENCY_S
                    and x >= float(w["t_dec0"])]
            live_post = [got.get(round(x, 4)) for x in post]
            ref_post = [tuple(v) for v in (w.get("rpost") or [])]
            n_fr = sum(1 for a, b in zip(live_post, ref_post) if a is not None and tuple(a) == b)
            ref_sw = [(round(float(q["x"]), 6), q["old"], q["new"]) for q in (w.get("mid_switches") or [])]
            live_sw = [(round(float(q["x"]), 6), q["old"], q["new"]) for q in meta.get("switches", [])]
            row = {"key": key, "final_live": d and d["final_line"], "final_shipped": ship.get(key),
                   "decided_after_press_s": d and round(d["t0_decided"] + 2.0 - d["press"], 3),
                   "decided_at_close": d and d["at_close"],
                   "end_text_frame_s": round(float(w["t_press"]) + LATENCY_S - float(w["t_press_start"]), 3),
                   "frames_f3": len(ref_post), "frames_live": len(live_post), "frames_equal": n_fr,
                   "lock_live": meta.get("lock_line"), "lock_f3": w.get("locked_line"),
                   "switches_live": live_sw, "switches_f3": ref_sw}
            row["DECISION_EQUAL"] = bool(d is not None and d["final_line"] == ship.get(key))
            row["DISPLAY_EQUAL"] = bool(len(live_post) == len(ref_post) and n_fr == len(ref_post)
                                        and row["lock_live"] == row["lock_f3"] and live_sw == ref_sw)
            n_eq_rec += int(row["DECISION_EQUAL"] and row["DISPLAY_EQUAL"])
            rows.append(row)
        tw = [x for x, prov in s.timing["window_s"] if not prov]
        t_win += tw
        t_press += s.timing["press_s"]
        t_cut += s.timing["cut_s"]
        gaps = np.diff(t0_all)
        q_live = live_queue(s.events)
        queue_all.append(q_live)
        per_rec.append({"stem": stem, "passes": len(ref), "equal": n_eq_rec, "windows": len(t0_all),
                        "max_gap_between_windows_s": float(gaps.max()) if len(gaps) else None,
                        "live_queue": q_live,
                        "dropped_backwards_packets": s.stream.n_dropped_backwards,
                        "adaptation": s.adaptation, "replay_seconds": round(time.time() - t_rec, 1)})
        print(json.dumps(per_rec[-1]), flush=True)
    q = lambda v: ({"n": len(v), "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),  # noqa: E731
                    "p99": float(np.percentile(v, 99)), "max": float(np.max(v))} if v else None)
    late = [r for r in rows if r["decided_after_press_s"] is not None
            and r["decided_after_press_s"] > r["end_text_frame_s"] + 1e-9]
    res = {"gate": "e2e-causal" if causal else "e2e",
           "anchoring": "causal (CausalAnchor, refit every 10 s)" if causal else "offline whole-file fit",
           "what": "raw packets and presses through the whole tracking session",
           "passes": len(rows), "decisions_equal": sum(r["DECISION_EQUAL"] for r in rows),
           "displays_equal": sum(r["DISPLAY_EQUAL"] for r in rows),
           "frames_f3": sum(r["frames_f3"] for r in rows), "frames_equal": sum(r["frames_equal"] for r in rows),
           "recordings": per_rec,
           "timing_s": {"per_window_compute_after_first_press": q(t_win), "per_window_cut": q(t_cut),
                        "per_press": q(t_press),
                        "per_window_total_p99": (float(np.percentile(t_win, 99)) + float(np.percentile(t_cut, 99)))
                        if t_win and t_cut else None},
           "live_queue_worst": {"max_latency_after_window_end_s": max(q["max_latency_s"] for q in queue_all),
                                "max_gap_between_outputs_s": max(q["max_gap_s"] for q in queue_all),
                                "contract": "latency at most 0.5 s per window, at most 4 s between outputs"},
           "end_text_later_than_f3": {"passes": len(late),
                                      "max_extra_s": max((r["decided_after_press_s"] - r["end_text_frame_s"]
                                                          for r in late), default=0.0)},
           "rows": rows}
    res["PASSED"] = (bool(rows) and res["decisions_equal"] == len(rows) and res["displays_equal"] == len(rows)
                     if not causal else None)
    return res


GATES = {"1": gate1, "2": gate2, "3": gate3, "3live": lambda every=1: gate3(every, "live"),
         "stream": gate_stream, "4": gate4, "5": gate5, "e2e": gate_e2e,
         "e2e-causal": lambda every=1: gate_e2e(every, causal=True)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate", required=True, choices=sorted(GATES))
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args(argv)
    t0 = time.time()
    res = GATES[a.gate](every=a.every)
    res["minutes"] = round((time.time() - t0) / 60.0, 2)
    res["run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"gate{a.gate}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
    return 0 if res["PASSED"] else 1


if __name__ == "__main__":
    sys.exit(main())
