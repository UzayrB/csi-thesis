"""ITEM B: REAL-TIME OPERATION. The frozen tracker, live, under RENDER_RULES V1 to V4.

    python3 -m pipeline.live.tracker_live --session 03 --stem participant_PA5_TEST_walk

Brief: `reports/BRIEF_render_and_prepress_2026-09-22.md`, open item B.

WHAT THIS IS. A live runner that streams CSI, windows it CAUSALLY, runs the frozen semi-bounded
tracker from an operator start press, and reports what a live display would draw. It reuses
`pipeline/live/realtime_engine.py` for the streaming contract and `pipeline/io/` READ-ONLY. Neither is
edited.

THE TWO THINGS IT MEASURES, and they are different questions kept apart on purpose.

  1  DECISION EQUALITY   given the SAME windows, does the live path produce the SAME decisions as
                         the offline path, exactly? This isolates the tracker and its causal
                         decode from the windowing.
  2  LATTICE ALIGNMENT   do the engine's own windows land where the offline tree's windows land?
                         The engine cuts on the absolute lattice from the packet stream; the
                         offline tree was cut once and stored. If these differ the decisions
                         diverge for a reason that has NOTHING to do with the tracker.

  Reporting one number for both would hide which of the two failed, and the second is the one that
  is likely to be imperfect. A runner that "nearly" matches is worse than none, because it puts a
  figure on screen in Room B that no offline figure can reproduce.

THE CHANNEL GAP, found while building this and stated rather than worked around. The shipped heads
take TWO channels, CSI amplitude and RSSI resampled onto the window's own lattice. The engine's
buffers carry amplitude only, because the branches it was built for do not use RSSI. So this
module keeps its OWN RSSI ring buffer alongside and samples it on the same window span. That is
why it is a runner around the engine rather than a `Predictor` handed to it.

CAUSALITY. A window may be read only once it has ENDED. The decode at display step i uses windows
up to i plus the fixed evidence lag and never beyond, which is the same rule
`tests/test_display_is_causal.py` enforces offline.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)

import argparse                                                                   # noqa: E402
import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

WINDOW_S = 2.0
STRIDE = 0.5
#: rule V1: the display runs exactly this far behind real time
LATENCY_S = 2.0
#: evidence before the line commits. Same 2 s, not additive; see RENDER_RULES V1
DELAY_S = 2.0
LAG_W = int(round((WINDOW_S / 2.0) / STRIDE))
ENTRY_WINDOW_M = 1.0
#: THE LOCK, as the render takes it (V3, and the ONE lattice of 2026-09-23d): the line is read at
#: the window that ENDS at press + 2.0 s, from windows lo .. lo + LOCK_W and nothing later. On the
#: press-aligned lattice lo starts at press - 1.0 s, so lo + 2 ends at exactly press + 2.0 s.
#: Until 2026-09-23d this runner locked at lo + 4 reading two windows past the lock, a different
#: convention from the render's; `reports/FINDING_lock_phase_2026-09-23.md`.
LOCK_W = int(round(DELAY_S / STRIDE)) - LAG_W


class LiveTracker:
    """The frozen tracker, fed one window at a time, deciding only from what has arrived.

    STATEFUL BY NATURE, which is why it is not the engine's per-window `Predictor`: a semi-bounded
    decode runs forward from a start press and its answer at window k depends on windows 0..k.
    """

    def __init__(self, tag: str, st, cfg, ne, transit, kind, alpha, chain_prior=None):
        from pipeline.constrained.decoder import transition_matrix
        from pipeline.constrained.decoder2 import Space, transition_matrix2
        from pipeline.constrained.t2_embed import load_heads
        self.st, self.cfg, self.ne, self.transit = st, cfg, ne, transit
        self.kind, self.alpha = kind, alpha
        self.heads = load_heads(tag)
        if self.heads is None:
            raise SystemExit(f"no trained heads for tag {tag}")
        self.sp = Space(st, cfg)
        self.lT = transition_matrix2(st, cfg, transit)
        self.lT_chains = transition_matrix(st, "tight", with_null=False)
        self.marg = None
        self.reset()

    def set_marginal(self, marg):
        self.marg = marg

    def reset(self):
        self.emissions = []          # the 25-cell posteriors, in arrival order
        self.gate = []               # band energy per window
        self.t0s = []                # window starts
        self.press_index = None      # the window index the operator pressed at
        self.press_time = None       # the press, on the windows' own clock, when it is known
        self.lock_evidence_end_minus_frame_s = None
        self.locked_line = None
        self.lock_step = None
        self._timings = []

    # -- one window in ------------------------------------------------
    def push_window(self, t0: float, window: np.ndarray, rssi: np.ndarray, band_energy: float):
        """One completed window. Returns (line, xy) as a live display would draw them, or None.

        `window` is (n_links, n_samples, n_sub) CSI amplitude, `rssi` is (n_links, n_samples).
        """
        import torch
        from pipeline.constrained.features import tracking_features_links
        from pipeline.constrained.nets import stack_link
        t_start = time.monotonic()
        feat = tracking_features_links(window)[None]                 # (1, links, samp, sub)
        rs = np.asarray(rssi, float)[None]
        per_link = []
        with torch.no_grad():
            for li, (m, mu, sd) in enumerate(self.heads):
                Xb = stack_link(feat[:, [li]], rs[:, [li]])
                Xb = ((Xb - mu) / sd).astype(np.float32)
                lg = m(torch.from_numpy(Xb))
                per_link.append(torch.softmax(lg, dim=1).numpy().astype(np.float64)[0])
        p = np.mean(np.stack(per_link), axis=0)
        p = p / max(p.sum(), 1e-12)
        self.emissions.append(p)
        self.gate.append(float(band_energy))
        self.t0s.append(float(t0))
        out = self._decide()
        self._timings.append(time.monotonic() - t_start)
        return out

    def press(self, t_press: float = None):
        """The operator start press. Semi-bounded: the walk's start is GIVEN, the end is not.

        The windows pushed from here on must be the PRESS-ALIGNED ones (`RealTimeEngine.
        rephase_to_press`), so the window at `press_index` starts half a window before the press.
        """
        self.press_index = len(self.emissions) - 1
        self.press_time = None if t_press is None else float(t_press)
        self.locked_line, self.lock_step = None, None
        self.lock_evidence_end_minus_frame_s = None

    # -- the decode ---------------------------------------------------
    def _emission_stack(self):
        from pipeline.constrained.decoder2 import stack2
        from pipeline.constrained.emissions import cell_emission, scaled_cell_emission
        P = np.stack(self.emissions)
        e = (cell_emission(P, self.st.xy, 25) if self.marg is None
             else scaled_cell_emission(P, self.st.xy, 25, self.marg, alpha=self.alpha))
        self.ne.calibrate(e)
        return stack2(e, np.asarray(self.gate, float), self.ne, self.sp)

    def _decide(self):
        """The line the display would draw NOW, from windows that have already ended."""
        if self.press_index is None:
            return None
        n_since = len(self.emissions) - 1 - self.press_index
        if n_since < LAG_W:
            return None
        from pipeline.constrained.decoder import decoded_paths, viterbi
        from pipeline.constrained.night_arms import entry_start
        from pipeline.constrained.render_display import chain_of, xy_of
        E = self._emission_stack()
        lo = self.press_index
        names = np.asarray(decoded_paths(np.arange(self.sp.N), self.st)).astype(str)
        on_chain = names != ""
        first_state = np.zeros(self.sp.N, bool)
        for nm in self.st.names:
            first_state[self.st.slice_of[nm][0]] = True
        sl = np.asarray(entry_start("soft", E, self.st, self.sp, lo, on_chain, first_state),
                        float).copy()
        s_arr = np.asarray(self.st.s_of, float)
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            far = a + np.flatnonzero((s_arr[a:b] - s_arr[a]) > ENTRY_WINDOW_M + 1e-9)
            if len(far):
                sl[far] = -1.0e9
        end = len(E) - 1
        s = viterbi(E[lo:end + 1], self.lT, log_start=sl)
        step = max(0, end - lo - LAG_W)
        k = int(s[step]) if step < len(s) else int(s[-1])
        line = chain_of(self.st, k) if k < self.st.n_states else ""
        # RULE 1: once locked, the drawn line NEVER changes for the rest of the walk. THE LOCK is
        # taken the render's way: from windows lo .. lo + LOCK_W only, at the window that ends at
        # press + 2.0 s, never from a later decode that happens to have more windows in it.
        if self.locked_line is None and n_since >= LOCK_W:
            s_lock = viterbi(E[lo:lo + LOCK_W + 1], self.lT, log_start=sl)
            k_lock = int(s_lock[LOCK_W])
            self.locked_line = (chain_of(self.st, k_lock) if k_lock < self.st.n_states else "") or None
            self.lock_step = LOCK_W
            if self.press_time is not None:
                self.lock_evidence_end_minus_frame_s = (
                    self.t0s[lo + LOCK_W] + WINDOW_S - (self.press_time + LATENCY_S))
        drawn = self.locked_line or line
        xy = xy_of(self.st, k) if k < self.st.n_states else None
        return {"line": drawn, "free_line": line, "xy": None if xy is None else tuple(xy),
                "locked": self.locked_line is not None, "step": step,
                "n_windows_since_press": n_since}

    def timing(self) -> dict:
        """Per-window compute time, and the headroom against one stride."""
        if not self._timings:
            return {"n": 0}
        t = np.asarray(self._timings, float)
        return {"n": int(len(t)),
                "per_window_s": {"median": float(np.median(t)), "p90": float(np.percentile(t, 90)),
                                 "max": float(t.max())},
                "stride_s": STRIDE,
                "headroom_per_stride": {
                    "median": float(STRIDE / max(np.median(t), 1e-9)),
                    "p90": float(STRIDE / max(np.percentile(t, 90), 1e-9)),
                    "worst": float(STRIDE / max(t.max(), 1e-9))},
                "meets_stride_budget": bool(t.max() <= STRIDE),
                "note": ("headroom is stride divided by compute time. Below 1.0 the tracker cannot "
                         "keep up with the stream and the display would fall behind without bound")}


# ---------------------------------------------------------------- the acceptance harness

def replay_offline_windows(sess: str, stem: str, tag: str, limit_passes: int = 6) -> dict:
    """ACCEPTANCE TEST 1: same windows in, are the live decisions the offline ones EXACTLY?

    The windows come from the stored tree, so the windowing is held identical and what is compared
    is the TRACKER: its emission, its causal decode, its lock. Test 2 asks the separate question of
    whether the engine's own lattice lands on these same windows.
    """
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_marginal
    from pipeline.constrained.night_common import shipped_pieces
    from pipeline.constrained.recordings import gate_energy, load_features, load_meta, load_rssi
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    import pipeline.constrained.decoder as D
    D.MAX_ADVANCE_M = None
    tr_s = ("01", "02") if sess == "03" else (("01",) if sess != "01" else ("02",))
    lt = LiveTracker(tag, st, cfg, ne, transit, kind, alpha)
    if kind == "scaled":
        lt.set_marginal(cell_marginal(sides(tr_s, (sess,), False, with_features=False)[0].xy, 25))

    rec = load_meta(sess, stem)
    ge = np.asarray(gate_energy(sess, stem), float)
    spans = rec.pass_spans()[:limit_passes]
    rows = []
    for pid, true_line, a, b in spans:
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if len(w) < 2:
            continue
        lo = int(w[0])
        hi = min(lo + int(round(8.0 / STRIDE)), len(rec) - 1)
        idx = list(range(lo, hi + 1))
        F = load_features(sess, stem, idx).astype(np.float32)
        R = load_rssi(sess, stem, rec.t0_epoch)[np.asarray(idx, int)].astype(np.float32)
        lt.reset()
        lt.set_marginal(lt.marg)
        live = None
        t_press = _press_times(sess, stem).get(int(pid))
        for j, wi in enumerate(idx):
            out = lt.push_window(float(rec.t0[wi]), F[j], R[j], ge[wi])
            if j == 0:
                lt.press(t_press)
            if out is not None:
                live = out
        # THE ACCEPTANCE COMPARISON: the OFFLINE decode of the same windows, same single head,
        # same emission, run through the offline code path. Comparing live against TRUTH would
        # measure the tracker's accuracy; comparing it against OFFLINE measures what this test is
        # for, which is whether the live path reproduces the offline one.
        # the LOCAL index into the accumulated emissions, not the absolute recording index:
        # the tracker was reset for this pass, so its stack starts at 0 and press_index is 0.
        off = _offline_same_head(lt, int(lt.press_index or 0), len(idx))
        rows.append({"pass_id": int(pid), "true": true_line,
                     "lock_evidence_end_minus_frame_s": lt.lock_evidence_end_minus_frame_s,
                     "live_line": None if live is None else live["line"],
                     "offline_line": off,
                     "MATCHES_OFFLINE": bool(live is not None and live["line"] == off),
                     "live_locked": bool(live and live["locked"]),
                     "n_windows": len(idx)})
        del F, R
    return {"rows": rows, "timing": lt.timing()}



def _offline_same_head(lt, lo: int, n: int):
    """The offline decode of the emissions the live tracker accumulated, same head, same rule.

    Run from the SAME emission stack, so any difference is the live path's sequencing and not the
    model. If this disagrees with the live answer, the live decode is reading evidence the offline
    one does not, or the other way round, and that is a defect rather than a tolerance.
    """
    from pipeline.constrained.decoder import decoded_paths, viterbi
    from pipeline.constrained.night_arms import entry_start
    from pipeline.constrained.render_display import chain_of
    E = lt._emission_stack()
    names = np.asarray(decoded_paths(np.arange(lt.sp.N), lt.st)).astype(str)
    on_chain = names != ""
    first_state = np.zeros(lt.sp.N, bool)
    for nm in lt.st.names:
        first_state[lt.st.slice_of[nm][0]] = True
    sl = np.asarray(entry_start("soft", E, lt.st, lt.sp, lo, on_chain, first_state), float).copy()
    s_arr = np.asarray(lt.st.s_of, float)
    for nm in lt.st.names:
        a_, b_ = lt.st.slice_of[nm]
        far = a_ + np.flatnonzero((s_arr[a_:b_] - s_arr[a_]) > ENTRY_WINDOW_M + 1e-9)
        if len(far):
            sl[far] = -1.0e9
    # THE EVIDENCE HORIZON MUST BE THE LIVE ONE, exactly. The live tracker locks when
    # n_since == commit_w, at which point it has seen windows lo .. lo+commit_w, and it reads
    # display step n_since - LAG_W. An offline helper that reads lo .. lo+commit_w+LAG_W sees TWO
    # WINDOWS MORE and is not the same decision: it was the first version of this helper, and the
    # single pass that "differed" differed because of it, not because the live path disagreed.
    # the lock the render takes, 2026-09-23d: windows lo .. lo + LOCK_W, the state at LOCK_W
    end = min(lo + LOCK_W, len(E) - 1)
    seq = viterbi(E[lo:end + 1], lt.lT, log_start=sl)
    k = int(seq[end - lo])
    return chain_of(lt.st, k) if k < lt.st.n_states else None


def _press_times(sess: str, stem: str) -> dict:
    """{pass_id: start press}, from the read-only sidecar, on the windows' own clock."""
    with open(os.path.join(REPO_ROOT, "data", "room_A", f"session_{sess}", f"{stem}.gt.json"),
              encoding="utf-8") as f:
        return {int(p["pass_id"]): float(p["t_start"]) for p in json.load(f)["passes"]}


def lattice_alignment(sess: str, stem: str, n_passes: int = 6, fs: float = 150.0) -> dict:
    """ACCEPTANCE TEST 2: does the LIVE ENGINE cut the windows the stored ONE lattice holds?

    The recording's raw packets are pushed through `RealTimeEngine` in time order, and at each
    pass's start press the engine is re-phased onto the press (`rephase_to_press`), exactly as a
    live operator press would. Its emitted window starts are then compared, pass by pass, with the
    stored press-aligned tree's starts over the same span: the first walk window and the next
    sixteen. THIS IS REPORTED, NEVER RELAXED: half a sample is the tolerance.
    """
    from pipeline.constrained.lattice import PRESS_EPS_S
    from pipeline.constrained.recordings import load_meta
    from pipeline.live.realtime_engine import NODES, RealTimeEngine
    from pipeline.io.windows import load_node, session_baseline
    sdir = os.path.join(REPO_ROOT, "data", "room_A", f"session_{sess}")
    with open(os.path.join(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sc = json.load(f)
    ps = sorted(sc["passes"], key=lambda p: float(p["t_start"]))
    presses = [float(p["t_start"]) for p in ps][:n_passes]
    # the offline cutter's segment boundary: midway between one pass's end and the next's start.
    # The comparison stops there, because past it the stored tree is on the NEXT pass's phase and
    # the live engine cannot re-phase until that pass's press arrives.
    bound = {float(ps[i]["t_start"]): (0.5 * (float(ps[i]["t_end"]) + float(ps[i + 1]["t_start"]))
                                       if i + 1 < len(ps) else float("inf"))
             for i in range(len(ps))}
    base = session_baseline(sc["baseline_capture"].rstrip("/"))
    eng = RealTimeEngine(baseline=base, presence_theta=1.0, fs=fs)
    streams = {}
    for n in NODES:
        amp, ts, _s, _e = load_node(os.path.join(sdir, f"{stem}_{n}.bin"))
        streams[n] = (ts, amp)
    merged = sorted((float(t), n, i) for n, (ts, _a) in streams.items() for i, t in enumerate(ts))
    horizon = presses[-1] + 10.0
    todo = list(presses)
    for t, n, i in merged:
        if t > horizon:
            break
        while todo and t >= todo[0]:
            eng.rephase_to_press(todo.pop(0), PRESS_EPS_S)
        eng.push(n, t, streams[n][1][i])
    live = np.asarray([r.t_start for r in eng.results], float)
    rec = load_meta(sess, stem)
    t0 = np.asarray(rec.t0, float)
    rows = []
    for P in presses:
        top = min(P + 7.0, bound[P])
        stored = t0[(t0 >= P - 1.0 - 1e-3) & (t0 < top)]
        got = live[(live >= P - 1.0 - 1e-3) & (live < top)]
        n = min(len(stored), len(got))
        d = np.abs(stored[:n] - got[:n]) if n else np.asarray([np.inf])
        rows.append({"press": P, "n_stored": int(len(stored)), "n_live": int(len(got)),
                     "max_abs_start_diff_s": float(d.max()),
                     "first_live_start_minus_press_s": float(got[0] - P) if len(got) else None,
                     "ALIGNED": bool(n == len(stored) and n > 0 and d.max() <= 0.5 / fs)})
    return {"n_passes": len(rows), "rows": rows, "rephases": eng.rephases,
            "ALL_ALIGNED": all(r["ALIGNED"] for r in rows),
            "tolerance_s": 0.5 / fs,
            "reading": ("the live engine re-phased at each press must emit the SAME window starts as "
                        "the stored press-aligned tree from the first walk window to the end of the "
                        "pass's segment (at most eight seconds)"),
            "KNOWN_GAP": ("PRE-PRESS windows differ in phase by construction: the live engine can "
                          "re-phase only AT the press, so windows it emitted before press - 2 s are "
                          "on the previous pass's phase, while the offline cutter switches phase at "
                          "the midpoint between passes. The shipped A2 start term reads windows "
                          "ending in [press - 2, press + 1]; this runner does not implement A2, so "
                          "its decisions are unaffected, but a live POOLED runner with A2 must cut "
                          "those windows the live way before its decisions can equal the render's")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The live tracker, and its acceptance tests.")
    ap.add_argument("--session", default="03")
    ap.add_argument("--stem", default="participant_PA5_TEST_walk")
    ap.add_argument("--tag", default="s0102_to_s03")
    ap.add_argument("--passes", type=int, default=6)
    args = ap.parse_args(argv)

    print(f"LIVE TRACKER acceptance, {args.session}|{args.stem}, tag {args.tag}")
    lat = lattice_alignment(args.session, args.stem, args.passes)
    print(f"\n[2] LATTICE, live engine re-phased at each press against the stored ONE lattice:")
    for x in lat["rows"]:
        print(f"    press {x['press']:.3f}: {x['n_live']} live / {x['n_stored']} stored starts, "
              f"max diff {x['max_abs_start_diff_s']:.2e} s, first live start "
              f"{x['first_live_start_minus_press_s']}, aligned {x['ALIGNED']}")
    print(f"    ALL ALIGNED: {lat['ALL_ALIGNED']}")

    t = time.time()
    r = replay_offline_windows(args.session, args.stem, args.tag, args.passes)
    print(f"\n[1] DECISIONS, {len(r['rows'])} passes, same windows in:")
    n_match = sum(1 for x in r["rows"] if x["MATCHES_OFFLINE"])
    for row in r["rows"]:
        eq = "MATCH" if row["MATCHES_OFFLINE"] else "DIFFER"
        print(f"    pass {row['pass_id']:2d}  true {row['true']:8s}  live {str(row['live_line']):8s}"
              f"  offline {str(row['offline_line']):8s}  {eq}")
    print(f"\n    ACCEPTANCE: live == offline on {n_match} of {len(r['rows'])} passes"
          f"  -> {'PASS' if n_match == len(r['rows']) else 'FAIL'}")
    tm = r["timing"]
    print(f"\n[3] TIMING over {tm['n']} windows: median {tm['per_window_s']['median'] * 1000:.1f} ms, "
          f"p90 {tm['per_window_s']['p90'] * 1000:.1f} ms, max {tm['per_window_s']['max'] * 1000:.1f} ms")
    print(f"    headroom per {STRIDE} s stride: median {tm['headroom_per_stride']['median']:.1f}x, "
          f"worst {tm['headroom_per_stride']['worst']:.1f}x, "
          f"meets budget: {tm['meets_stride_budget']}")

    out = {"session": args.session, "stem": args.stem, "tag": args.tag,
           "lattice": lat, "decisions": r["rows"], "timing": tm,
           "acceptance": {
               "n_passes": len(r["rows"]),
               "n_live_equals_offline": sum(1 for x in r["rows"] if x["MATCHES_OFFLINE"]),
               "EXACT_EQUALITY": all(x["MATCHES_OFFLINE"] for x in r["rows"]),
               "what_is_compared": ("live against OFFLINE on the same windows and the same single "
                                    "head, never live against truth"),
               "LATTICE_ALIGNED": lat["ALL_ALIGNED"],
               "lock_evidence_end_minus_frame_s_max": max(
                   (x["lock_evidence_end_minus_frame_s"] for x in r["rows"]
                    if x["lock_evidence_end_minus_frame_s"] is not None), default=None),
               "POOL_CAVEAT": ("the SHIPPED tracker reads a FIVE-HEAD pool and the A2 start term; "
                               "this runner uses the 0.5 s head alone and no start term. CORRECTED "
                               "2026-09-23d: the three 1 s heads are inferred over the 0.5 s "
                               "windows (g2_multihead.ONE_S_TREES), so a live stream CAN feed them; "
                               "the earlier caveat said it could not. The pool is not yet wired "
                               "into this runner, so equality here is single-head against "
                               "single-head")},
           "minutes": round((time.time() - t) / 60.0, 2)}
    od = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "live_tracker")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nwrote {os.path.join(od, 'results.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
