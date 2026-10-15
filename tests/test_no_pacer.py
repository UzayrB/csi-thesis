"""The pacer must stay deleted. Added 2026-09-18 after it was measured as dead reckoning.

WHY THIS IS A TEST AND NOT A NOTE. The ramp extension read the CSI in its code and ignored it in
practice: removing the emissions changed 0.0 percent of its answers. It looked like a decoder and
behaved like a constant-speed guess, and it survived a code review because the emission term was
right there in the expression. Only the substitution test caught it. So the ban is enforced here,
where it runs on every future freeze, rather than remembered.
"""

from __future__ import annotations

import os
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
BANNED = ("extend_along", "decode_along", "split_decode", "inferred_windows", "extrapolate_to")

#: Files whose JOB is to enumerate the banned names, so they mention them inside string literals
#: and would otherwise trip their own check. Kept as an explicit short list rather than a clever
#: exemption rule, because a clever rule is how a real reappearance would get waved through.
#: The two checkers (re5_ship, re7_finalise) were removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
CHECKERS: set = set()


def _py_files():
    for p in (REPO / "pipeline").rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        if str(p.relative_to(REPO)) in CHECKERS:
            continue
        yield p


@pytest.mark.parametrize("name", BANNED)
def test_the_ramp_extension_code_path_is_absent(name):
    """Deleted, not disabled: the identifier must not exist anywhere under pipeline/."""
    hits = [str(p.relative_to(REPO)) for p in _py_files() if name in p.read_text(encoding="utf-8")]
    assert not hits, f"the pacer identifier {name!r} is back in {hits}"


def test_the_checker_list_is_honest():
    """Every exempted file must actually be a checker, not a hiding place."""
    for rel in CHECKERS:
        src = (REPO / rel).read_text(encoding="utf-8")
        assert "BANNED" in src, f"{rel} is exempted but does not enumerate the ban"
        for name in BANNED:
            assert f"def {name}" not in src, f"{rel} DEFINES {name}, which the ban forbids"
            assert f"{name}=" not in src.replace(" ", ""), f"{rel} CALLS {name} as a keyword"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_renderer_draws_no_inferred_segment():
#     """No dashed tail, no hollow dot: every drawn position came from the decoder."""
#     src = (REPO / "pipeline" / "retired" / "constrained" / "rc8_demo.py").read_text(encoding="utf-8")
#     assert "set_markerfacecolor" not in src, "the hollow inferred dot is back"
#     assert '"--"' not in src, "a dashed artist is back in the demonstration renderer"


def test_bounded_track_has_no_pacer_flag():
    import inspect
    from pipeline.constrained.rb10_bounded_demo import bounded_track
    sig = set(inspect.signature(bounded_track).parameters)
    assert "split_decode" not in sig, "the split_decode flag is back"
