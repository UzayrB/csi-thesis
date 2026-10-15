"""The five-head pool and the display head, one window at a time, against their offline emissions.

Sampled (every 40th window of one recording), in a child process (`tests/_live_checks.py` says why).
The full run is `python3 -m pipeline.live gates --gate 1`.
"""

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_live_checks", os.path.join(REPO, "tests", "_live_checks.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope="module")
def src():
    if not C.present():
        pytest.skip("Room A session 03 or the frozen render results are not present")
    return C.child("pool_sample")


def test_the_pool_has_the_five_shipped_heads(src):
    assert src["heads"] == ["g25_half", "g25_1s_seed0", "g25_1s_seed1", "g25_1s_seed2", "g100"]


def test_each_window_pools_to_the_offline_emission(src):
    assert len(src["rows"]) > 30
    for r in src["rows"]:
        assert r["max_diff"] <= src["tol"], r
        assert r["argmax_equal"] and r["gate_equal"], r
        assert r["row_max"] == 0.0, r            # renormalised: the decoder's null reference is 0


def test_the_display_head_equals_its_offline_emission(src):
    assert src["end_max_diff"] <= src["tol"]
