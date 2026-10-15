"""The gate labels windows from one global motion constant and a per-session presence rule."""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.constrained.gate import (
    MAX_BASELINE_AGE_S,
    MOTION_THETA,
    PRESENCE_K,
    PRESENCE_QUANTILE,
    band_energy,
    baseline_is_fresh,
    label_window,
    presence_threshold,
)

FS = 150.0


def _window(freq: float, amp: float, seed: int = 0, noise: float = 0.001) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(300) / FS
    return (amp * np.sin(2 * np.pi * freq * t)[None, :, None] + rng.normal(0, noise, (3, 300, 107))).astype(np.float32)


def test_the_accepted_constants_are_the_checkpoint_4_values() -> None:
    assert MOTION_THETA == 0.431 and PRESENCE_K == 1.04 and PRESENCE_QUANTILE == 0.75 and MAX_BASELINE_AGE_S == 3600.0


def test_band_energy_matches_the_calibration_tool_on_a_batch() -> None:
    from tools.calibrate_gate import band_energy as batch
    X = np.stack([_window(1.0, 0.1, s) for s in range(4)])
    assert np.allclose([band_energy(x, FS) for x in X], batch(X), rtol=1e-6)


def test_presence_threshold_requires_a_baseline_and_has_no_default() -> None:
    import inspect
    assert inspect.signature(label_window).parameters["presence_theta"].default is inspect.Parameter.empty
    assert inspect.signature(presence_threshold).parameters["baseline_band_energies"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        label_window(_window(1.0, 0.1), FS)      # type: ignore[call-arg]
    with pytest.raises(ValueError):
        presence_threshold(np.array([0.01, 0.02]))
    e = np.array([0.01, 0.012, 0.011, 0.02, 0.015, 0.013])
    assert presence_threshold(e) == pytest.approx(PRESENCE_K * np.quantile(e, PRESENCE_QUANTILE))


def test_labels_fall_out_of_the_two_thresholds() -> None:
    theta_p = presence_threshold(np.full(20, 0.01))
    quiet = label_window(_window(1.0, 0.0), FS, presence_theta=theta_p)
    still = label_window(_window(1.0, 0.03), FS, presence_theta=theta_p)
    walk = label_window(_window(1.0, 0.3), FS, presence_theta=theta_p)
    assert quiet.label == "empty" and still.label == "standing" and walk.label == "walking"
    assert quiet.band_energy < theta_p <= still.band_energy < MOTION_THETA <= walk.band_energy
    assert walk.presence_theta == theta_p and walk.motion_theta == MOTION_THETA


def test_a_bad_presence_threshold_is_refused_not_defaulted() -> None:
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            label_window(_window(1.0, 0.1), FS, presence_theta=bad)


def test_baseline_freshness_is_an_hour_and_the_order_matters() -> None:
    assert baseline_is_fresh(1000.0 + 3599.0, 1000.0) and not baseline_is_fresh(1000.0 + 3601.0, 1000.0)
    with pytest.raises(ValueError):
        baseline_is_fresh(1000.0, 1000.0 + 10.0)
