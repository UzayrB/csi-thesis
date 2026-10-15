"""The identification conditioning chain does what each stage claims, on synthetic signals.

PORTED INTENT. `testing/tests/test_id_branch.py` (removed on 2026-09-24 with the rest of `testing/`,
restorable from the git tag `pre-cleanup`) had a test that the notch "takes out the line and little
else". Its intent is re-implemented here against the port in `pipeline/identify/conditioning.py`.

THE FAILURES THESE EXIST FOR.
  - A notch that removes the 50.5 Hz line AND the gait content either side of it. The line sits
    inside the path-rate band, so a wide notch would take the leg content with it.
  - C1 interpolating across a dropout, which invents motion that was never observed and lands in
    the spectrogram as broadband energy at the moment the person was least observable.
  - C3 "normalise" being applied when the gain never moved, which removes body shadowing for
    nothing. Shadow depth is already a measured feature in this project.
  - An energy contour returning 0 Hz for a silent frame, which reads as a stationary torso rather
    than as no measurement.

Synthetic data only. These tests never read CSI.
"""

from __future__ import annotations

import numpy as np

from pipeline.identify import conditioning as C

FS = 150.0


def _signal(n=1500, n_sub=8, line_hz=50.5, gait_hz=(2.0, 12.0, 30.0), seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FS
    x = np.zeros((n, n_sub))
    for j in range(n_sub):
        for g in gait_hz:
            x[:, j] += np.sin(2 * np.pi * g * t + j)
        x[:, j] += 2.0 * np.sin(2 * np.pi * line_hz * t)      # the room's line, on every subcarrier
        x[:, j] += 0.05 * rng.standard_normal(n)
    return x + 10.0


def _power_at(x, hz, fs=FS, halfwidth=1.0):
    f = np.fft.rfftfreq(x.shape[0], 1 / fs)
    P = (np.abs(np.fft.rfft(x, axis=0)) ** 2).mean(axis=1)
    m = (f >= hz - halfwidth) & (f <= hz + halfwidth)
    return float(P[m].sum())


def test_notch_removes_the_line_and_little_else():
    x = _signal()
    y = C.c4_notch(x, FS)
    before, after = _power_at(x, 50.5), _power_at(y, 50.5)
    assert after < 0.02 * before, f"line only fell from {before:.3g} to {after:.3g}"
    # the gait content either side of the line must survive
    for g in (12.0, 30.0):
        keep = _power_at(y, g) / max(_power_at(x, g), 1e-12)
        assert keep > 0.5, f"the notch took {1 - keep:.0%} of the {g} Hz content with it"


def test_c1_marks_gaps_instead_of_interpolating_through_them():
    n = 600
    t = np.arange(n) / FS
    t[300:] += 0.5                                   # a half-second dropout
    x = np.sin(2 * np.pi * 2.0 * t)[:, None] * np.ones((1, 4))
    out, grid, bad = C.c1_resample(x, t, FS, gap_rule_s=0.05)
    assert bad.any(), "a 0.5 s dropout was not marked"
    assert bad.sum() >= 0.4 * FS, "the marked region is shorter than the gap itself"
    assert np.isfinite(out).all(), "marking must not introduce NaNs into the stream"


def test_c3_auto_does_nothing_when_the_gain_never_moved():
    x = _signal(n=300)
    gain = np.ones(300)
    y, mode = C.c3_gain(x, gain, mode="auto")
    assert mode == "null"
    assert np.allclose(x, y), "a constant gain was 'corrected', which can only remove signal"


def test_c3_auto_divides_out_a_gain_that_did_move():
    x = _signal(n=300)
    gain = np.ones(300)
    gain[150:] = 2.0
    y, mode = C.c3_gain(x * gain[:, None], gain, mode="auto")
    assert mode == "exact"
    assert np.allclose(y, x, atol=1e-6), "the logged gain was not divided out exactly"


def test_c3_normalise_destroys_broadband_shadowing_and_exact_does_not():
    """The reason Addendum B prefers exact: this is what the lossy branch costs."""
    x = _signal(n=600)
    shadow = np.ones(600)
    shadow[250:350] = 0.5                            # a body shadowing every subcarrier at once
    obs = x * shadow[:, None]
    norm, _ = C.c3_gain(obs, None, mode="normalise")
    exact, _ = C.c3_gain(obs, np.ones(600), mode="null")
    depth_norm = 1 - norm[250:350].mean() / norm[:250].mean()
    depth_exact = 1 - exact[250:350].mean() / exact[:250].mean()
    assert abs(depth_norm) < 0.05, "normalise was expected to remove the shadow"
    assert depth_exact > 0.3, "the uncorrected stream should still carry the shadow"


def test_c7_band_b_excludes_the_envelope_band():
    x = _signal(n=1500)
    out = C.c7_bands(x, FS)
    lo, hi = out["band_b_hz"]
    assert lo >= 4.0 and hi < FS / 2
    assert _power_at(out["band_b"], 2.0) < 0.05 * _power_at(x, 2.0)
    assert _power_at(out["band_a"], 30.0) < 0.05 * _power_at(x, 30.0)


def test_c7_notches_band_b():
    x = _signal(n=1500)
    out = C.c7_bands(x, FS)
    assert _power_at(out["band_b"], 50.5) < 0.05 * _power_at(x, 50.5)


def test_contour_returns_nan_for_a_silent_frame_not_zero():
    f = np.linspace(0, 75, 64)
    mag = np.zeros((3, 64))
    mag[0, 20] = 1.0
    c = C.energy_percentile_contour(f, mag, 50.0)
    assert np.isfinite(c[0])
    assert np.isnan(c[1]) and np.isnan(c[2]), "a silent frame returned a frequency"


def test_path_rate_to_speed_matches_the_archived_constant():
    """8.13 Hz per m/s per unit geometric factor, from the archived branch, independently."""
    hz = C.path_rate_to_speed(np.array([16.26]), F=1.0)
    assert abs(float(hz[0]) - 1.0) < 0.02, "2 F v / lambda did not invert to 1.0 m/s"
    assert abs(2 * C.DOPPLER_HZ_PER_MPS_PER_UNIT_FACTOR - 16.26) < 0.1


def test_leave_one_stage_out_actually_drops_the_stage():
    full = C.Chain.full()
    assert full.has("C4")
    assert not full.without("C4").has("C4")
    assert full.without("C4").has("C5"), "dropping one stage dropped another"
    assert C.Chain.full().upto("C2").on == ("C1", "C2")
