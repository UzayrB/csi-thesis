"""Tests for the channel-filter shape-separability check.

``compare_shapes`` is the number the channel_filter_en decision hinges on, so
its direction is pinned down here: identical near/far shapes must report
zero separability, a real shape difference against low noise must report a
high ratio and a low correlation, and pure noise between conditions must
report neither.

No hardware required.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.io.check_channel_filter import compare_shapes, run


def summary(node: str, mean_shape, var_shape, n: int = 5000) -> dict:
    """Build a capture summary directly, bypassing any capture file."""
    return {"node": node, "n": n, "mean_shape": np.asarray(mean_shape, dtype=np.float32), "var_shape": np.asarray(var_shape, dtype=np.float32)}


def test_identical_shapes_are_perfectly_correlated_and_zero_ratio() -> None:
    """No real change in geometry: nothing to separate."""
    shape = [1.0, 1.1, 0.9, 1.0, 1.2]
    var = [0.01] * 5
    r = compare_shapes(summary("RX1", shape, var), summary("RX1", shape, var))
    assert r["correlation"] == pytest.approx(1.0)
    assert r["between"] == pytest.approx(0.0)
    assert r["ratio"] == pytest.approx(0.0)


def test_a_real_shape_difference_against_low_noise_gives_a_high_ratio() -> None:
    """A large, structured difference between conditions with a quiet noise floor."""
    near = [1.0, 1.2, 0.8, 1.0, 1.0]
    far = [0.6, 1.6, 0.5, 1.3, 1.0]
    tiny_var = [1e-4] * 5
    r = compare_shapes(summary("RX1", near, tiny_var), summary("RX1", far, tiny_var))
    assert r["ratio"] > 5.0
    assert r["correlation"] < 0.9


def test_the_same_shape_difference_with_more_noise_gives_a_lower_ratio() -> None:
    """Separability is relative to the noise floor, not the raw difference alone."""
    near = [1.0, 1.2, 0.8, 1.0, 1.0]
    far = [0.6, 1.6, 0.5, 1.3, 1.0]
    quiet = compare_shapes(summary("RX1", near, [1e-4] * 5), summary("RX1", far, [1e-4] * 5))
    noisy = compare_shapes(summary("RX1", near, [0.5] * 5), summary("RX1", far, [0.5] * 5))
    assert noisy["ratio"] < quiet["ratio"]
    # correlation depends only on the mean shapes, not the noise, so it is unchanged
    assert noisy["correlation"] == pytest.approx(quiet["correlation"])


def test_an_inverted_shape_is_reported_as_strongly_anti_correlated() -> None:
    """corrcoef is signed: a flipped shape gives r near -1, not just 'low'."""
    near = [1.0, 1.5, 0.5, 1.2, 0.8]
    far = [1.0, 0.5, 1.5, 0.8, 1.2]
    r = compare_shapes(summary("RX1", near, [1e-4] * 5), summary("RX1", far, [1e-4] * 5))
    assert r["correlation"] < -0.5


def test_mismatched_bin_counts_are_rejected() -> None:
    """Two summaries from different dead-bin sets are not comparable bin for bin."""
    with pytest.raises(ValueError):
        compare_shapes(summary("RX1", [1.0, 1.0, 1.0], [0.01] * 3), summary("RX1", [1.0, 1.0], [0.01] * 2))


def test_run_reports_no_shared_files_cleanly(tmp_path) -> None:
    """An empty or mismatched pair of directories is reported, not a traceback."""
    (tmp_path / "near").mkdir()
    (tmp_path / "far").mkdir()
    assert run(str(tmp_path / "near"), str(tmp_path / "far")) == 2
