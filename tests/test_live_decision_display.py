"""The live committed decision and the live display, on one replayed Room A recording.

Inputs are the offline ones (the shipped pool's emissions, the DISP_END emissions, the committed and
display start terms), so the decoder and the display alone are on trial. The full runs are gates 3 and
4 (`python3 -m pipeline.live gates --gate 3`, `--gate 4`); the end-to-end run from raw packets is
`--gate e2e`. In a child process (`tests/_live_checks.py` says why).

CAUSALITY is tested by SUBSTITUTION, not by reading index arithmetic: every window that ends after a
cut time is replaced by ANOTHER participant's windows. A decision made before the cut and every frame
drawn before it must not change, and something after the cut must (or the substitution proved nothing).
"""

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_live_checks", os.path.join(REPO, "tests", "_live_checks.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope="module")
def res():
    if not C.present():
        pytest.skip("Room A session 03 or the frozen render results are not present")
    return C.child("decision_display_all")


def test_every_decision_equals_the_shipped_one(res):
    assert len(res["decisions"]) == 20
    for key, (live, shipped) in res["decisions"].items():
        assert live == shipped, key


def test_every_frame_equals_f3_render(res):
    total = 0
    for pid, f in res["frames"].items():
        assert f["n"] == f["n_f3"] and f["equal"] == f["n"], (pid, f)
        assert f["lock"][0] == f["lock"][1], (pid, f)
        total += f["n"]
    assert total > 500


def test_a_decision_never_reads_a_window_after_the_one_it_was_made_at(res):
    sub = res["decision_sub"]
    early = [k for k, v in sub.items() if v["early"]]
    assert len(early) >= 5
    assert all(sub[k]["same"] for k in early), [k for k in early if not sub[k]["same"]]
    assert any(not v["same"] for v in sub.values() if not v["early"]), \
        "substituting another participant changed nothing after the cut: the test proves nothing"


def test_a_frame_never_reads_a_window_that_ended_after_it(res):
    f = res["frame_sub"]
    assert f["before"] > 10
    assert not f["before_changed"], "frames changed when only later radio changed"
    assert f["after_changed"] > 0, "substituting another participant changed no later frame: the test proves nothing"
