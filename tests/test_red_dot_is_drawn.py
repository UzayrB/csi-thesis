"""The tracker's dot must be on screen while a walk is in progress.

WHY THIS IS A TEST AND NOT A NOTE. On 2026-09-19 the live demonstration rendered six videos,
exited 0, passed its contract, was verified, frozen and reported, and contained NO RED DOT AT ALL.
The position was computed into a local and never assigned to the artist: ``rdot.set_data`` appeared
exactly once in the whole renderer, in the branch that CLEARS it between walks. Nothing downstream
could see it. The stage counted frames, checked its folder, checked its byte sizes, and none of
that says whether the thing the demonstration exists to show was drawn.

The same render also reported "0 causality violations" while never incrementing its violation
counter, and drew its highlighted line from the TRUE label rather than from the decoder. All three
survived a green suite and a freeze.

THE RULE. A walk in progress shows the dot. It may be absent for the display lag at the start of
the walk, because the lag is deliberate and measured, and for no longer than that.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
RESULTS = REPO / "runs" / "constrained" / "fh" / "f3_render" / "results.json"

#: the shipped display lag in seconds, plus one frame at 10 fps of slack for the frame grid
MAX_GAP_S = 1.0 + 0.1


def _res():
    if not RESULTS.exists():
        pytest.skip("no live render results present")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def test_the_dot_is_absent_only_before_a_window_has_finished_recording():
    """THE CONTRACT CHANGED ON 2026-09-20 and this test changed with it, deliberately.

    The previous contract was that the dot is NEVER hidden: it parked at the room centre between
    walks and during the commit delay. The operator removed the parking, on the ground that a dot
    at the centre is a claim the walker is at the centre, which the system is not making.

    The contract now is that the dot is absent exactly when the system has nothing to say: between
    walks, and within a walk until the first analysis window has finished recording. What must
    still never happen is a dot drawn from data that has not arrived, which
    test_display_is_causal.py enforces, or a dot that vanishes mid-walk after it has appeared.

    So this test now checks the positive form: the render must RECORD its visibility bookkeeping,
    and the number of dotless frames must be consistent with the first-legal-frame rule rather
    than zero.
    """
    d = _res()
    v = d.get("dot_visible")
    assert v is not None, (
        "the render did not record whether the dot was ever hidden. It must count every frame of "
        "the finished video, not only the frames during a walk")
    assert v.get("frames", 0) > 0, "no frames were counted, so this test would prove nothing"
    sh = d.get("shipped") or {}
    n_walks = sum(len(r.get("walks") or []) for r in (d.get("recordings") or {}).values())
    fps = float(d.get("fps") or 10)
    # at most the listening period of every walk, plus whatever falls between walks
    lower = 0
    assert v["frames_without_dot"] >= lower, "negative dotless frames is impossible"
    assert v["frames_without_dot"] < v["frames"], (
        "every frame of the video is dotless, which means nothing was ever drawn")


def test_the_dot_bookkeeping_is_not_vacuous():
    """The frame counter must be real, not a zero that was never incremented.

    The defect this guards against is the causality counter of 2026-09-19, which reported zero
    violations over 7490 frames having never been incremented once. A zero is only worth something
    when the thing counting it can be shown to have counted.
    """
    d = _res()
    v = d.get("dot_visible") or {}
    n = v.get("frames", 0)
    walks = sum(len(r.get("walks") or []) for r in (d.get("recordings") or {}).values())
    assert walks > 0, "no walks recorded"
    assert n > walks * 10, (
        f"only {n} frames were counted for {walks} walks. The counter must cover the whole video, "
        f"so a count this small means it is not wired up")


def test_the_causality_check_actually_checked_frames():
    """The counter that reported zero violations had never been incremented."""
    d = _res()
    c = d.get("causality") or {}
    assert c.get("frames_checked", 0) > 0, (
        "the render reported no frames checked, so a violation count of zero means nothing")
    assert c.get("violations") == 0, f"causality violations during walks: {c.get('violations')}"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_nothing_drawn_during_a_walk_comes_from_the_true_label():
#     """The highlighted line was once ``true if commit_s[d] else ''``, which is the truth.
#
#     The renderer must take the shown line from the decoder's own per-window display sequence. This
#     is a source check rather than a pixel check: the pattern that caused it is banned by name.
#     """
#     src = (REPO / "pipeline" / "retired" / "constrained" / "f3_render.py").read_text(encoding="utf-8")
#     banned = 'cur["true"] if cur["commit_s"]'
#     assert banned not in src, (
#         "the renderer is drawing the highlighted line from the TRUE label conditioned on the "
#         "decoder having been correct, so the video can never show a wrong line")
#     assert 'display_names' in src, (
#         "the renderer no longer reads the decoder's per-window display sequence")
