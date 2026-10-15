"""MID-WALK SWITCHING, RENDER_RULES rule 1 as amended 2026-09-23e (operator decision, display only).

Two layers. UNIT tests drive `switching.decide` on a synthetic two-line space, so each constraint is
shown to BITE, not merely to hold on the data. CONTRACT tests read the render's own results and
re-check every switch it drew:

  at most one switch per walk, none back to the locked line, none in the final 1.0 m, the
  persistence rule holds, every switch decision causal on both bounds, and switch jumps counted
  separately from lock jumps.
"""

from __future__ import annotations

import json
import pathlib
import types

import numpy as np
import pytest

from pipeline.constrained import switching as SW

REPO = pathlib.Path(__file__).resolve().parents[1]
RESULTS = REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json"


# --------------------------------------------------------------------------- a synthetic space

def _space():
    """Two straight 5 m lines, states every 0.25 m: A along x at y = 0, B along x at y = 3."""
    xs = np.arange(0.0, 5.0 + 1e-9, 0.25)
    xy = np.concatenate([np.c_[xs, np.zeros_like(xs)], np.c_[xs, np.full_like(xs, 3.0)]])
    s_of = np.concatenate([xs, xs])
    n = len(xs)
    return types.SimpleNamespace(names=["A", "B"], slice_of={"A": (0, n), "B": (n, 2 * n)},
                                 xy=xy, s_of=s_of)


def _decs(leads, x0=10.0):
    """Decision records where B leads A by the given amounts at successive steps."""
    return [{"x": x0 + 0.5 * (k + 1), "w": 5 + k, "evidence_bound_s": -0.5,
             "raw": {"A": 0.0, "B": float(lead)}, "end": {"A": 4, "B": 25}}
            for k, lead in enumerate(leads)]


def _dots(x0=10.0, arc=0.5, n=40):
    return [(x0 + 0.1 * i, (arc, 0.0)) for i in range(n)]


def test_one_qualifying_step_is_not_enough():
    st = _space()
    out = SW.decide("A", _decs([5.0, 0.0, 5.0, 0.0]), None, 1.0, st, _dots())
    assert not out["switched"], "a lead at single, non-consecutive steps must not switch"


def test_two_consecutive_steps_switch_at_the_second():
    st = _space()
    d = _decs([0.0, 5.0, 5.0, 5.0])
    out = SW.decide("A", d, None, 1.0, st, _dots())
    assert out["switched"] and out["new"] == "B" and out["x"] == d[2]["x"]
    assert len(out["persist"]) == SW.PERSIST_STEPS and all(q["qualifies"] for q in out["persist"])


def test_a_lead_at_or_below_theta_does_not_count():
    st = _space()
    assert not SW.decide("A", _decs([1.0, 1.0, 1.0]), None, 1.0, st, _dots())["switched"]


def test_the_earliest_switch_is_one_second_after_the_lock():
    xf = SW.decision_frames(100.0, 110.0)
    lock = 100.0 + SW.LATENCY_S
    assert abs(xf[0] - (lock + 0.5)) < 1e-9, "decisions start one step after the lock"
    # persistence of two steps: the earliest possible switch is the SECOND decision frame
    assert abs(xf[SW.PERSIST_STEPS - 1] - (lock + 1.0)) < 1e-9


def test_never_in_the_final_metre_and_never_after_it():
    st = _space()
    L = SW.line_length(st, "A")
    # the dot reaches the final 1.0 m before the lead appears: switching is disabled for good
    dots = [(10.0 + 0.1 * i, (min(L, 3.0 + 0.2 * i), 0.0)) for i in range(40)]
    out = SW.decide("A", _decs([5.0] * 6), None, 1.0, st, dots)
    assert not out["switched"] and out.get("disabled_final_m_at") is not None


def test_at_most_one_switch_and_never_back():
    st = _space()
    out = SW.decide("A", _decs([5.0, 5.0, -5.0, -5.0, 5.0, 5.0]), None, 1.0, st, _dots())
    assert out["switched"] and out["new"] != "A", "the one switch is final and never to the lock"
    assert "switches" not in out, "decide returns at the FIRST switch; there is no second"


def test_the_slide_is_on_its_segment_by_elapsed_fraction():
    frames = [20.0 + 0.1 * i for i in range(10)]
    sl = SW.slide((0.0, 0.0), (3.0, 4.0), 20.05, frames)
    assert sl and all(not off for _x, _p, off in sl)
    assert all(20.05 - 1e-9 <= x < 20.05 + SW.SLIDE_S for x, _p, _o in sl)
    f = [(x - 20.05) / SW.SLIDE_S for x, _p, _o in sl]
    for (x, p, _o), fi in zip(sl, f):
        assert np.allclose(p, (3.0 * fi, 4.0 * fi)), "no pace: the parameter is elapsed fraction"


def test_decisions_read_only_finished_windows(monkeypatch):
    """The causal bound, on the decision itself: at frame x only windows with t + 2.0 <= x."""
    seen = []
    sc = SW.Scorer.__new__(SW.Scorer)
    monkeypatch.setattr(sc, "totals_and_ends", lambda E, lo, hi, sl: (seen.append(hi) or ({}, {})),
                        raising=False)
    t = np.arange(0.0, 20.0, 0.5) + 2e-6                  # the ONE lattice's 2 us offset
    frames = [10.0, 10.5, 11.0]
    out = SW.Scorer.decisions(sc, None, t, 0, None, frames)
    for d, x in zip(out, frames):
        assert t[d["w"]] + SW.WINDOW_S <= x + 1e-9 and d["evidence_bound_s"] <= 0
        assert not (t[d["w"] + 1] + SW.WINDOW_S <= x + 1e-9), "the latest finished window is used"


def test_decide_walk_at_one_switch_is_decide_exactly():
    st = _space()
    for leads in ([0.0, 5.0, 5.0, 5.0], [5.0, 0.0, 5.0, 0.0], [5.0] * 6):
        a = SW.decide("A", _decs(leads), None, 1.0, st, _dots())
        b = SW.decide_walk("A", _decs(leads), None, 1.0, st, _dots(), lambda l, x: _dots(),
                           max_switches=1, final_m=SW.FINAL_M)
        assert bool(a["switched"]) == bool(b["switches"])
        if b["switches"]:
            assert (a["new"], a["x"]) == (b["switches"][0]["new"], b["switches"][0]["x"])


def _space3():
    xs = np.arange(0.0, 5.0 + 1e-9, 0.25)
    n = len(xs)
    xy = np.concatenate([np.c_[xs, np.full_like(xs, y)] for y in (0.0, 1.0, 2.0)])
    return types.SimpleNamespace(names=["A", "B", "C"], xy=xy, s_of=np.concatenate([xs] * 3),
                                 slice_of={"A": (0, n), "B": (n, 2 * n), "C": (2 * n, 3 * n)})


def _decs3(best_seq, x0=10.0):
    out = []
    for k, b in enumerate(best_seq):
        raw = {"A": 0.0, "B": 0.0, "C": 0.0}
        raw[b] = 5.0
        out.append({"x": x0 + 0.5 * (k + 1), "w": 5 + k, "evidence_bound_s": -0.5, "raw": raw,
                    "end": {"A": 4, "B": 25, "C": 46}})
    return out


def test_a_second_switch_waits_for_the_slide_and_a_fresh_streak():
    st = _space3()
    d = _decs3(["B", "B", "C", "C", "C"])
    out = SW.decide_walk("A", d, None, 1.0, st, _dots(), lambda l, x: _dots(x0=x),
                         max_switches=2, final_m=1.5)
    S = out["switches"]
    assert [q["new"] for q in S] == ["B", "C"]
    assert S[1]["x"] - S[0]["x"] >= SW.SLIDE_S + SW.STRIDE_S - 1e-9, "fresh two-check streak"


def test_a_second_switch_never_returns_to_a_drawn_line():
    st = _space3()
    d = _decs3(["B", "B", "A", "A", "A", "A"])
    out = SW.decide_walk("A", d, None, 1.0, st, _dots(), lambda l, x: _dots(x0=x),
                         max_switches=2, final_m=1.5)
    assert [q["new"] for q in out["switches"]] == ["B"], "the lock line may not be drawn again"


def test_the_final_zone_is_read_on_the_current_line():
    st = _space3()
    d = _decs3(["B", "B", "C", "C", "C"])
    late = lambda l, x: [(x + 0.1 * i, (4.0, 1.0)) for i in range(20)]      # 1.0 m from B's end
    out = SW.decide_walk("A", d, None, 1.0, st, _dots(), late, max_switches=2, final_m=1.5)
    assert [q["new"] for q in out["switches"]] == ["B"] and out["disabled_final_m_at"] is not None


# --------------------------------------------------------------------------- the render's contract

def _walks():
    if not RESULTS.exists():
        pytest.skip("no render results present")
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert "switching" in d, "a render from before 23e: re-render under rule 1 as amended"
    ws = [w for rec in (d.get("recordings") or {}).values() for w in (rec.get("walks") or [])]
    assert ws, "no walks: every contract test below would pass vacuously"
    return d, ws


def test_render_at_most_k_switches_and_never_back_to_a_drawn_line():
    d, ws = _walks()
    K = d["switching"]["max_switches"] or 0
    for w in ws:
        S = w.get("mid_switches") or []
        assert int(w["mid_walk_switches"]) == len(S) <= K
        seen = {w["locked_line"]}
        for q in S:
            assert q["new"] not in seen, (w["key"], q["new"])
            seen.add(q["new"])
        assert w["drawn_end_line"] == (S[-1]["new"] if S else w["locked_line"])
    S_ = d["switching"]
    assert S_["returns_to_a_drawn_line"] == 0 and S_["more_than_max_switches"] == 0


def test_render_no_switch_in_the_final_zone():
    _d, ws = _walks()
    for w in ws:
        for q in (w.get("mid_switches") or []):
            assert q["dot_max_arc_m"] < q["line_length_m"] - q["final_m"], (w["key"], q)


def test_render_persistence_rule_holds():
    _d, ws = _walks()
    for w in ws:
        prev = None
        for q in (w.get("mid_switches") or []):
            p = q["persist"]
            assert len(p) == SW.PERSIST_STEPS
            assert all(c["qualifies"] and c["best"] == q["new"] and c["lead"] > q["theta"] for c in p)
            assert abs(p[1]["x"] - p[0]["x"] - SW.STRIDE_S) < 1e-6, "consecutive decode steps"
            assert q["after_lock_s"] >= 1.0 - 1e-6, "the earliest switch is 1.0 s after the lock"
            if prev is not None:
                assert p[0]["x"] >= prev["x"] + SW.SLIDE_S - 1e-9, "a fresh streak after the slide"
            prev = q


def test_render_every_switch_is_causal_on_both_bounds():
    d, ws = _walks()
    for w in ws:
        for s in (w.get("mid_switches") or []):
            assert s["decision_evidence_bound_s"] <= 1e-9, (w["key"], s["decision_evidence_bound_s"])
            assert s["target_drawn_bound_s"] <= 1e-9 and s["target_evidence_bound_s"] <= 1e-9, w["key"]
            assert all(q["evidence_bound_s"] <= 1e-9 for q in s["persist"])


def test_render_switch_jumps_are_counted_apart_from_lock_jumps():
    d, ws = _walks()
    J = d["jumps"]
    assert "caused_by_a_switch" in J and "caused_by_the_lock" in J
    assert J["caused_by_a_switch"] + J["caused_by_the_lock"] <= J["total"]
    assert sum(w["jumps_caused_by_a_switch"] for w in ws) == J["caused_by_a_switch"]
    for w in ws:
        if not w.get("mid_switches"):
            assert w["jumps_caused_by_a_switch"] == 0


def test_render_slides_stay_on_their_segments():
    d, _ws = _walks()
    assert d["switching"]["slide_off_segment_frames"] == 0


def test_render_equals_the_measurement_walk_for_walk():
    """Recomputed HERE from the render's own walk records and e2_switch's rows, not read from the
    render's flag (the first 23e render's own check mis-compared a key)."""
    d, ws = _walks()
    S_ = d["switching"]
    if not S_.get("arm"):
        assert all(not w.get("mid_switches") for w in ws), "lock-final: no switch may be drawn"
        return
    arm = f"{S_['arm']}_t{float(S_['theta']):g}"
    e2 = {r["key"]: r["arms"][arm] for r in json.loads(
        (REPO / "runs" / "constrained" / "fh" / "e2_switch" / "rows.json").read_text(encoding="utf-8"))}
    bad = []
    for w in ws:
        a = [(q["new"], round(q["x"], 3)) for q in (w.get("mid_switches") or [])]
        b = [(q["new"], round(q["x"], 3)) for q in e2[w["key"]]["switches"]]
        if a != b:
            bad.append((w["key"], a, b))
    assert not bad, f"the render's switches differ from e2_switch's on {len(bad)} walks: {bad[:3]}"
    assert d["switch_check_vs_e2"]["PASSED"], d["switch_check_vs_e2"]


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_end_text_is_the_shipped_headline_decision():
#     """Batch 23e item 2: the text names the shipped semi-bounded decision, walk for walk."""
#     d, ws = _walks()
#     c = d["end_text_check"]
#     assert c["PASSED"] and c["n"] == len(ws), c
#     src = (REPO / "pipeline" / "retired" / "constrained" / "f3_render.py").read_text(encoding="utf-8")
#     assert '"committed": r["final_line"],' in src, "the text source must be the decision decode"
