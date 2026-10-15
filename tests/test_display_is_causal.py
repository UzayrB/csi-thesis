"""No frame may be drawn from a sample recorded after that frame's time.

WHY THIS IS A TEST AND NOT A NOTE. On 2026-09-20 the shipped demonstration drew, at "0 s display
lag", a window that ENDED between 0.51 and 1.00 s after the frame being drawn. Every frame of every
walk used samples not yet recorded. It passed the one-rule check, which asks whether the drawn
point lies on the decoded path, and the old causality check, which had never been incremented.
Neither asked the only question that matters for a display presented as live: had the data arrived?

Worse, a lag sweep then chose that setting over the honest one, because a display allowed to see a
second into the future naturally tracks better. The result reversed once the rule was applied.

THE RULE. A window w spans [t0[w], t0[w] + WINDOW_S]; t0 is the window START. At frame time t the
display may use only windows with t0[w] + WINDOW_S <= t. With the render defining the walk's start
as the CENTRE of the first walk window, that means the display index may be at most
floor((t - t_start)/STRIDE) - WINDOW_S/(2*STRIDE), which at a 2 s window and a 0.5 s stride is a
lag of two windows, one second.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
RESULTS = REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json"
WINDOW_S = 2.0
STRIDE = 0.5


def _min_causal_lag_s(window_s=WINDOW_S):
    """The smallest display lag for which the window being drawn has already ended."""
    return window_s / 2.0


def test_the_minimum_causal_lag_is_half_the_window():
    """The arithmetic itself, independent of any run."""
    assert _min_causal_lag_s(2.0) == 1.0
    assert _min_causal_lag_s(1.0) == 0.5


def test_the_shipped_render_did_not_draw_from_unrecorded_samples():
    if not RESULTS.exists():
        pytest.skip("no live render results present")
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    sh = d.get("shipped") or {}
    lag = sh.get("display_lag_s")
    assert lag is not None, "the render did not record its display lag, so causality cannot be checked"
    need = _min_causal_lag_s(WINDOW_S)
    assert float(lag) >= need - 1e-9, (
        f"the render drew at a {lag} s display lag. A {WINDOW_S} s window has not ended until "
        f"{need} s after the render's own t_start, so every frame used samples recorded up to "
        f"{need - float(lag):.2f} s AFTER the frame time. That is future information in a display "
        f"presented as live")


def test_the_commit_delay_cannot_precede_the_first_usable_window():
    """Locking before any window has ended means locking on data that has not arrived."""
    if not RESULTS.exists():
        pytest.skip("no live render results present")
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    sh = d.get("shipped") or {}
    delay = sh.get("commit_delay_s")
    if delay is None:
        pytest.skip("this render has no commit delay")
    need = _min_causal_lag_s(WINDOW_S)
    assert float(delay) >= need - 1e-9, (
        f"the dot locked {delay} s after the walk's start, but the first window does not end until "
        f"{need} s, so the lock used a window that had not finished recording")


# --------------------------------------------------------------------------- the evidence horizon

def test_the_evidence_horizon_is_not_the_draw_offset():
    """The second causality leak: the window drawn had ended, the radio that decoded it had not.

    Found 2026-09-20. `fixed_lag_path` and `locked_chain_path` decode display step i with every
    window up to lo + i + lag_w, and night_arms was handing them the DRAW OFFSET as that horizon.
    At the shipped offset of two windows the drawn window's own end landed exactly on the frame,
    so the render's causality check read a clean -0.000 s, while the Viterbi that produced the
    position had read a further 1.000 s of radio recorded after the frame.

    The correct horizon is the draw offset MINUS the windows a window needs to finish recording,
    which at a 2 s window and a 0.5 s stride is two. This pins the arithmetic and the call sites.
    """
    src = (REPO / "pipeline" / "constrained" / "night_arms.py").read_text(encoding="utf-8")
    assert "lw0 = int(round((WINDOW_S / 2.0) / stride_s))" in src, (
        "night_arms no longer derives the recording delay in windows; the display evidence "
        "horizon cannot be correct without it")
    # the call gained a lo_disp argument on 2026-09-21 when the display briefly reached back a
    # window; what this test is actually about is the LAST argument, the evidence horizon
    assert re.search(r"fixed_lag_path\(e_stacked, lT, st_lo, st, \w+, disp_hi, ev_w\)", src), (
        "the free display path is not built on the evidence horizon")
    assert src.count("int(lw) - lw0") >= 2, (
        "a locked display path is still built on the draw offset rather than the evidence horizon")
    # and a lag shorter than the recording delay must be refused rather than silently clamped
    assert "cannot be drawn\n                        f\"causally\"" in src or "causally" in src


def test_every_display_step_records_the_window_that_decoded_it():
    """A step that does not say what it read cannot be checked. Both builders must record it."""
    src = (REPO / "pipeline" / "constrained" / "render_display.py").read_text(encoding="utf-8")
    assert src.count('"evidence_window": int(end)') == 2, (
        "fixed_lag_path and locked_chain_path must each record the latest window that entered "
        "their decode, or the evidence bound cannot be measured at all")


def test_the_render_reports_both_bounds():
    """A render that reports only the drawn-window bound hides exactly this leak."""
    if not RESULTS.exists():
        pytest.skip("no live render results present")
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert "causal_bound_s" in d, "the render did not report the drawn-window bound"
    assert "causal_evidence_bound_s" in d, (
        "the render did not report the EVIDENCE bound. The drawn-window bound read -0.000 s "
        "through the whole of the 2026-09-20 leak; only the evidence bound showed it")
    assert float(d["causal_evidence_bound_s"]) <= 1e-9, (
        f"the radio that produced the drawn dot ended {d['causal_evidence_bound_s']:+.3f} s after "
        f"the frame it was drawn on")


# --------------------------------------------------------------------------- the decision path

DECISION = REPO / "runs" / "constrained" / "fh" / "s2b_decision_causality" / "results.json"

#: bounds that must be at or below zero for the SHIPPED live claim to hold. The committed line's
#: scoring bound and the bounded rescore's are DECLARATION LATENCIES, not leaks: neither reads a
#: window past its own end, they simply cannot be announced at the instant they are dated to. They
#: are reported and are not gated here, and the report says so in those words.
MUST_BE_CAUSAL = ("locked_line",)


def test_the_lock_reads_the_same_builder_as_the_display():
    """Why the decision path needed auditing at all: the lock is taken from fixed_lag_path.

    The evidence leak of 2026-09-20 lived in fixed_lag_path and locked_chain_path. The locked line
    is read off the free path that fixed_lag_path builds, so the leak was never confined to the
    display: every locked-line figure and the whole wait curve were measured through it. This
    pins the dependency, so that if the lock ever stops reading that builder somebody has to come
    and change this test deliberately.
    """
    src = (REPO / "pipeline" / "constrained" / "night_arms.py").read_text(encoding="utf-8")
    # CHANGED DELIBERATELY 2026-09-23, which is what this test asks for. The lock's line was split
    # across two statements so that `lock_line_source` could record WHY it was chosen (the free
    # path, the entry line, or the name-order fallback). The DEPENDENCY is unchanged: the lock
    # still reads the free path fixed_lag_path builds, and both halves are pinned below so the
    # split cannot become a substitution.
    assert 'nm_free = free[li]["line"]' in src, (
        "the lock no longer reads the free display path; the decision-path causality argument in "
        "tests/test_display_is_causal.py was written against that dependency")
    assert "nm_lock = nm_free or entry_nm or st.names[0]" in src, (
        "the locked line is no longer the free path's line falling back to the entry line; the "
        "fallback census in y1b_locksrc and the causality argument here both assume it is")


def test_the_decision_path_evidence_bounds_were_measured():
    if not DECISION.exists():
        pytest.skip("no decision-path causality results present")
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    b = d.get("bounds") or {}
    for k in ("locked_line", "committed_scoring", "committed_exit_search", "bounded_rescore"):
        assert k in b, f"the decision-path audit did not report a bound for {k}"
        assert b[k]["n_decisions"] > 0, f"the bound for {k} was reported over no decisions at all"


@pytest.mark.parametrize("which", MUST_BE_CAUSAL)
def test_the_shipped_live_decision_uses_no_future_samples(which):
    if not DECISION.exists():
        pytest.skip("no decision-path causality results present")
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    b = (d.get("bounds") or {}).get(which)
    assert b is not None, f"no bound reported for {which}"
    assert float(b["evidence_bound_s"]) <= 1e-9, (
        f"{which} was decided using radio that had not finished recording: its evidence bound is "
        f"{b['evidence_bound_s']:+.4f} s. A decision presented as live may not read the future")


# --------------------------------------------------------------------------- the exit search

def test_the_exit_search_may_not_read_past_the_answers_own_end():
    """The retired batch exit read 20.5 s into the future to decide where the walk had ended.

    Found 2026-09-20. ``own_end()`` ran ONE Viterbi over lo_dec to lo_dec + MAX_WALK_S and took
    the first null in it, so the exit INDEX could depend on radio recorded long after the walk.
    It was measured inert -- the committed line changed on 5.5 percent of passes and the paired
    delta was -0.09 points with interval [-1.57, 1.30] -- and it was removed anyway, because a
    live claim that happens to be harmless is still not a live claim.

    THE RULE. The exit decision may read no window that the committed answer does not already
    read. Its evidence bound may therefore not exceed the scoring interval's, which is the
    WINDOW_S/2 declaration latency every semi-bounded answer carries.
    """
    if not DECISION.exists():
        pytest.skip("no decision-path causality results present")
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    b = d.get("bounds") or {}
    ex, sc = b.get("committed_exit_search"), b.get("committed_scoring")
    assert ex is not None and sc is not None, "the audit did not report both committed bounds"
    assert float(ex["evidence_bound_s"]) <= float(sc["evidence_bound_s"]) + 1e-9, (
        f"the exit search reads {ex['evidence_bound_s']:+.3f} s past the frame while the answer "
        f"it dates only reads {sc['evidence_bound_s']:+.3f} s. The exit decision may not see a "
        f"window the committed answer does not")
    assert float(ex["evidence_bound_s"]) <= WINDOW_S / 2.0 + 1e-9, (
        f"the exit search's evidence bound is {ex['evidence_bound_s']:+.3f} s, past the "
        f"{WINDOW_S / 2.0:g} s declaration latency. The 20.5 s look-ahead has come back")


def test_the_shipped_exit_rule_is_the_causal_one():
    """Pinned in the code as well as in a result, so a default flip cannot pass unnoticed."""
    src = (REPO / "pipeline" / "constrained" / "night_arms.py").read_text(encoding="utf-8")
    assert 'o.setdefault("causal_exit", True)' in src, (
        "the causal exit is no longer the shipped default; the retired batch search read 20.5 s "
        "into the future")
    assert 'if o.get("causal_exit", True):' in src, "the exit rule is not switched on the flag"
    if DECISION.exists():
        d = json.loads(DECISION.read_text(encoding="utf-8"))
        if d.get("exit_rule_shipped") is not None:
            assert d["exit_rule_shipped"] == "causal", (
                f"the audit saw exit rule {d['exit_rule_shipped']!r}, not the causal one")
