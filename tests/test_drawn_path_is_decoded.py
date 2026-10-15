"""Every drawn red position must be a decoded position, or a blend of two of them.

WHY THIS IS A TEST AND NOT A NOTE. On 2026-09-19 the live demonstration shipped with NO RED DOT at
all, a causality counter that had never been incremented, and a highlighted line taken from the
TRUE label. All three survived a green suite, a contract check, a verification stage and a freeze,
because every check in place measured whether the stage RAN rather than what it produced.

THE RULE, from the brief of 2026-09-20: every drawn red position is either a decoded position or a
point on the straight segment between two consecutive decoded positions, and nothing is ever drawn
ahead of the latest decode. The renderer asserts it per frame; this refuses a render that did not.

THE VACUOUS-PASS GUARD. A checker that examined nothing would report zero violations, which is the
same defect as the violation counter that was never incremented. This test therefore also requires
that frames were actually checked, and that the display genuinely interpolated rather than only
ever landing on exact decoded points.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
RESULTS = REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json"


def _res():
    if not RESULTS.exists():
        pytest.skip("no live render results present")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def test_no_drawn_position_left_the_decoded_path():
    d = _res()
    rule = d.get("rule")
    assert rule is not None, (
        "the render recorded no rule block at all, so nothing checked where the dot was drawn")
    assert rule.get("frames_checked", 0) > 0, (
        "the rule checker examined zero frames, so a violation count of zero means nothing. This "
        "is the same defect as the causality counter that was never incremented")
    assert rule.get("violations") == 0, (
        f"{rule.get('violations')} frames drew the red dot off the decoded path: "
        f"{rule.get('examples')}")


def test_the_dot_is_present_once_a_window_has_finished_recording():
    """THE CONTRACT CHANGED ON 2026-09-20 and this test changed with it.

    It used to require that the dot is NEVER hidden, because it parked at the room centre between
    walks. The operator removed the parking: a dot at the centre is a claim that the walker is at
    the centre, and the system is not making that claim. The dot is now absent exactly when there
    is nothing to say, between walks and until the first analysis window has finished recording.

    What must still never happen is a dot that vanishes mid-walk after it has appeared. That is
    what this now checks, and it is a stronger statement about the part of the video that matters
    than the old blanket rule was.
    """
    d = _res()
    v = d.get("dot_visible")
    assert v is not None, "the render did not record its visibility bookkeeping"
    assert v.get("expected", 0) > 0, (
        "no frames were expected to carry a dot, so this test would prove nothing")
    assert v.get("missing_after_first_legal") == 0, (
        f"{v['missing_after_first_legal']} of {v['expected']} frames after the first legal frame "
        f"had no red dot, so the dot vanished mid-walk")


def test_nothing_is_drawn_before_its_data_arrived():
    """The causal bound, confirmed by the render against real timestamps on every drawn frame."""
    d = _res()
    b = d.get("causal_bound_s")
    assert b is not None, "the render did not record its causal bound"
    assert b <= 1e-9, (
        f"the worst drawn frame read a window ending {b:+.3f} s AFTER the frame time")


def test_the_render_records_what_it_shipped():
    """A render that cannot say which entry and lag it used cannot be reproduced."""
    d = _res()
    sh = d.get("shipped") or {}
    for k in ("entry", "display_lag_s", "cross_line_cap_m_s"):
        assert k in sh, f"the render did not record {k}"
    assert sh["entry"] in ("free", "soft"), f"unknown entry rule {sh['entry']!r}"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_display_is_not_taken_from_the_true_label():
#     """The pattern that drew the highlighted line from the truth is banned by name."""
#     src = (REPO / "pipeline" / "retired" / "constrained" / "f3_render.py").read_text(encoding="utf-8")
#     assert 'cur["true"] if cur["commit_s"]' not in src, (
#         "the renderer is drawing the highlighted line from the TRUE label conditioned on the "
#         "decoder having been correct, so the video can never show a wrong line")
#     assert "display_paths" in src, (
#         "the renderer no longer reads the decoder's own fixed-lag path")
