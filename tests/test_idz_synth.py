"""Identification audit, stage 2: the synthetic walker through the real code path (runs/identify/audit/PLAN.md
section 2). Checks 1 to 4 must pass after the bug fixes B-1 (dwt_6 removed from the model's columns) and B-2
(conditioned_map_v2); the as-built failures of checks 3 and 4a are asserted too, so the record stays honest."""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(not os.path.isdir("data/room_B"), reason="needs the DC2 recordings (read only)")


@pytest.fixture(scope="module")
def res(tmp_path_factory):
    from pipeline.identify import idz_synth as S
    return S.run_checks(out_dir=str(tmp_path_factory.mktemp("synth")))


def test_torso_frequency_within_one_bin(res):
    assert res["check1_torso"]["PASS"], res["check1_torso"]


def test_cadence_within_5_percent(res):
    assert res["check2_cadence"]["PASS"], res["check2_cadence"]


def test_features_complete_after_fix(res):
    assert res["check3_complete_fixed"]["PASS"], res["check3_complete_fixed"]
    assert set(res["check3_complete"]["nan_names"]) == {f"wav|mean@full|RX{i}|0|dwt_6" for i in (1, 2, 3)}


def test_gain_invariance_after_fix(res):
    assert res["check4a_gain_float"]["n_features_changed"] == 0
    assert res["check4a_gain_float_fixed"]["PASS"], res["check4a_gain_float_fixed"]


def test_measurements_present(res):
    assert np.isfinite(res["check5_suspect"]["change_db"])
    assert set(res["check6_edges_rel_rms_error"]) == {"b08_35", "b03_2"}
