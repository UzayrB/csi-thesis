"""END TO END on the first passes of one recording: raw packets and presses through the whole tracking
session (stream, pool, display head, start terms with AdaBN, decoder, display), against the shipped
decision and f3_render's frames. In a child process (`tests/_live_checks.py` says why). The full run
over the six recordings is `--gate e2e`.
"""

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_live_checks", os.path.join(REPO, "tests", "_live_checks.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope="module")
def session():
    if not C.present():
        pytest.skip("Room A session 03 or the frozen render results are not present")
    return C.child("tracking_prefix")


def test_adabn_ran_at_the_first_press(session):
    assert session["adapted"]["adapted"]


def test_each_pass_is_decided_as_shipped(session):
    assert len(session["decisions"]) == 3
    for pid, (live, shipped) in session["decisions"].items():
        assert live == shipped, pid


def test_each_pass_is_drawn_as_f3_render_drew_it(session):
    for pid, f in session["frames"].items():
        assert f["n"] == f["n_f3"] > 10 and f["equal"] == f["n"], (pid, f)
        assert f["lock"][0] == f["lock"][1], (pid, f)


def test_the_session_holds_the_trees_windows(session):
    """Every window the session holds after the first press, and that anything reads, is on the tree's
    lattice. The one exception is the stream's own rule: in a gap longer than twice RECUT_BACK_S, the
    windows a later press re-assigns but that lie more than RECUT_BACK_S before it keep the older phase
    (nothing reads them), and the check skips exactly those."""
    assert session["checked"] > 80
    assert not session["off_lattice"]
