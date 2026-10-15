"""The identification heads are FIXED, and the interval clusters on recordings.

THE FAILURE THIS EXISTS FOR. `id3_embeddings.score` fits two heads and returns whichever scores
higher ON THE TEST SESSION. That is selection on the test side. It inflated every figure it touched
and the 19b voting batch had to pin LDA by hand to stop it bending a curve that was being read for
where it flattened. `id_heads.fit_score` fixes the primary head before any data is seen. If this
test fails, a head is being chosen by test accuracy again.

THE SECOND FAILURE. A pass-level interval treats one recording's twenty passes as twenty
independent observations. All 18 participant-session cells hold exactly ONE recording, so that
interval is far too narrow and a claim built on it is not supported. The cluster interval over
recordings must be the wider of the two.

Synthetic data only. This test never reads CSI.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.identify import id_heads as H


def _synth(n=240, d=8, sep=1.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.array([f"P{i % 6 + 1}" for i in range(n)])
    X = np.vstack([rng.normal(int(p[1:]) * sep, 1.0, d) for p in y])
    rows = [{"anon": y[i], "session": ["01", "02", "03"][i % 3],
             "line": ["A_fwd", "E_col1", "E_row5", "C_rev"][i % 4]} for i in range(n)]
    return X, y, rows


def test_primary_head_is_fixed_not_chosen_by_test_accuracy():
    """The returned head is always the pre-registered primary, even when a secondary wins."""
    X, y, rows = _synth()
    r = H.fit_score(X[:160], y[:160], X[160:], y[160:], rows[160:])
    assert r["head"] == H.PRIMARY == "lda_shrinkage"
    best_secondary = max((v.get("accuracy_pct") or -1) for v in r["secondary"].values())
    # the primary is reported whether or not a secondary beat it: that is the whole point
    assert r["accuracy_pct"] is not None
    assert "FIXED BEFORE THE RUN" in r["head_choice"]
    if best_secondary > r["accuracy_pct"]:
        assert r["head"] == H.PRIMARY, "a secondary beat the primary and was returned anyway"


def test_secondaries_are_reported_but_never_selected():
    X, y, rows = _synth()
    r = H.fit_score(X[:160], y[:160], X[160:], y[160:], rows[160:])
    assert set(r["secondary"]) == {"logreg_c1", "linsvm_c1"}
    assert all("accuracy_pct" in v for v in r["secondary"].values())


def test_cluster_interval_is_wider_than_the_pass_interval():
    """The recording-level interval must not be narrower than the pass-level one."""
    X, y, rows = _synth()
    r = H.fit_score(X[:160], y[:160], X[160:], y[160:], rows[160:])
    correct = (r["pred"] == y[160:]).astype(float)
    cl = H.cluster_bootstrap(correct, r["recording_ids"])
    ps = H.pass_bootstrap(correct)
    assert cl["n_clusters"] < len(correct), "clusters must be recordings, not passes"
    assert (cl["hi"] - cl["lo"]) >= (ps["hi"] - ps["lo"]), (
        "the cluster interval came out narrower than the pass interval, so it is not clustering")


def test_edge_lines_are_reported_beside_the_pooled_figure():
    """A pooled number hides the edge lines. They are reported separately, always."""
    X, y, rows = _synth()
    r = H.fit_score(X[:160], y[:160], X[160:], y[160:], rows[160:])
    per_line = r["per_line_recall_pct"]
    assert per_line["_EDGE_MEAN"] is not None
    assert per_line["_NON_EDGE_MEAN"] is not None
    for ln in ("E_col1", "E_row5"):
        assert ln in per_line


def test_r3_needs_both_the_count_and_the_interval():
    """R3 is a conjunction. Either half alone must not ship an arm."""
    a = {f"p{i}": 20.0 for i in range(9)}
    # improves on 9 of 9 and the interval excludes zero: ships
    assert H.ships_r3(a, {f"p{i}": 23.0 for i in range(9)})["R3_SHIPS"] is True
    # improves on only 3 of 9: must not ship however large those three gains are
    mixed = {f"p{i}": (40.0 if i < 3 else 19.0) for i in range(9)}
    assert H.ships_r3(a, mixed)["R3_SHIPS"] is False
    # no change at all: must not ship
    assert H.ships_r3(a, dict(a))["R3_SHIPS"] is False


def test_paired_delta_reports_both_readings():
    """Difference of medians AND median of paired deltas, never only one."""
    a = {f"p{i}": 20.0 + i for i in range(9)}
    b = {f"p{i}": 22.0 + i for i in range(9)}
    d = H.paired_delta(a, b)
    assert "median_paired_delta" in d and "difference_of_medians" in d
    assert d["median_paired_delta"] == pytest.approx(2.0, abs=0.01)


def test_permutation_null_sits_near_chance():
    """Shuffled train labels must not classify. If they do, something leaks."""
    X, y, _ = _synth()

    def fit(yshuf):
        r = H.fit_score(X[:160], yshuf, X[160:], y[160:])
        return r["accuracy_pct"]

    null = H.permutation_null(fit, y[:160], n=20, seed=0)
    assert null["n"] == 20
    assert null["mean"] < 35.0, f"permutation null at {null['mean']} is far above 16.7 chance"
