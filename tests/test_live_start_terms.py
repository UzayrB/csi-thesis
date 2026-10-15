"""The live start terms (A2 + the veto) equal the offline ones, pass by pass, on one replayed recording.

The offline reference is built exactly as `dc2_run.do_decode` builds the committed decision's terms.
AdaBN runs on this recording's own idle windows before its first press, as `u1_adapt` does. In a child
process (`tests/_live_checks.py` says why). The full run is `python3 -m pipeline.live gates --gate 2`.
"""

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_live_checks", os.path.join(REPO, "tests", "_live_checks.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope="module")
def terms():
    if not C.present():
        pytest.skip("Room A session 03 or the frozen render results are not present")
    return C.child("start_terms_one")


def test_adabn_ran_on_this_recordings_own_idle_windows(terms):
    assert terms["adapted"]["adapted"] and terms["adapted"]["n_calibration_windows"] >= 20


def test_every_pass_term_equals_the_offline_term(terms):
    assert len(terms["rows"]) == 20
    for r in terms["rows"]:
        assert r["max_diff"] <= terms["tol"], r
        # the veto (-3 nats) is a discrete choice: the same lines must be vetoed
        assert r["veto_live"] == r["veto_off"], r


def test_some_pass_is_vetoed(terms):
    """The veto must actually fire somewhere, or the equality above says nothing about it."""
    assert any(r["veto_live"] for r in terms["rows"])
