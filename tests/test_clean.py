"""Tests for the shared cleaning stage.

The rules this stage exists to enforce are negative ones: no bandpass, no
PCA, nothing that removes the near-DC level. Those are easy to break by
accident and impossible to notice later, so most of what follows checks that
signal content SURVIVES rather than that it is transformed.

No hardware required.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.io.clean import (
    DEAD_SUBCARRIERS,
    DEFAULT_KEEP,
    HALF,
    OUTLIER_SIGMAS,
    clean_session,
    estimate_baseline,
    measure_dead_subcarriers,
    normalise_shape,
    records_to_matrix,
    remove_outliers,
    resample_uniform,
    select_subcarriers,
    subtract_baseline,
    to_amplitude,
)
from pipeline.io.parse import CSI_LEN, N_SUBCARRIERS, CsiRecord

FS = 150.0


def make_record(node_id: str = "RX1", t: float = 0.0, value: int = 40, gain: float = 1.0) -> CsiRecord:
    """Build a record whose every subcarrier has the same known amplitude."""
    data = np.full(CSI_LEN, value, dtype=np.int8)
    return CsiRecord(
        node_id=node_id, t_mono=t, t_host=t + 1e9, pkt_id=int(t * 150), mac="1a:00:00:00:00:00",
        rssi=-70, rate=11, sig_mode=1, mcs=0, bandwidth=0, smoothing=1, not_sounding=1,
        aggregation=0, stbc=0, fec_coding=0, sgi=0, noise_floor=-96, ampdu_cnt=0, channel=11,
        secondary_channel=0, local_timestamp=0, ant=0, sig_len=47, rx_format=1,
        csi_len=CSI_LEN, first_word=1, data=data, compensate_gain=gain,
    )


# --------------------------------------------------------------------------
# Amplitude
# --------------------------------------------------------------------------


def test_to_amplitude_shape_and_value() -> None:
    """Interleaved (imag, real) pairs become 128 magnitudes."""
    raw = np.zeros(CSI_LEN, dtype=np.int8)
    raw[0], raw[1] = 3, 4          # first subcarrier: 3-4-5 triangle
    amp = to_amplitude(raw)
    assert amp.shape == (N_SUBCARRIERS,)
    assert amp[0] == pytest.approx(5.0)
    assert amp[1] == pytest.approx(0.0)


def test_to_amplitude_rejects_wrong_length() -> None:
    """A wrong-length payload is a bug upstream, not something to reshape."""
    with pytest.raises(ValueError):
        to_amplitude(np.zeros(128, dtype=np.int8))


def test_amplitude_is_never_negative() -> None:
    """It is a magnitude; phase is discarded entirely."""
    rng = np.random.default_rng(0)
    raw = rng.integers(-128, 128, CSI_LEN).astype(np.int8)
    assert np.all(to_amplitude(raw) >= 0)


# --------------------------------------------------------------------------
# Subcarrier selection
# --------------------------------------------------------------------------


def test_default_keep_drops_exactly_the_dead_bins() -> None:
    """107 live of 128: 51 from the legacy half, 56 from the HT half."""
    assert len(DEAD_SUBCARRIERS) == 21
    assert len(DEFAULT_KEEP) == 107
    assert sum(1 for i in DEFAULT_KEEP if i < HALF) == 51
    assert sum(1 for i in DEFAULT_KEEP if i >= HALF) == 56
    assert set(DEFAULT_KEEP).isdisjoint(DEAD_SUBCARRIERS)
    assert set(DEFAULT_KEEP) | set(DEAD_SUBCARRIERS) == set(range(N_SUBCARRIERS))


def test_dead_bins_are_the_802_11_nulls_and_the_invalid_first_word() -> None:
    """Structural, from the HT20 layout, not a threshold on one capture.

    Legacy LTF in FFT order: DC and the guards, 0 and 27-37. HT-LTF: DC and
    the guards, 64 and 93-99. Plus bins 0 and 1, the hardware-invalid first
    word. Nothing else.
    """
    assert set(DEAD_SUBCARRIERS) == {0, 1} | set(range(27, 38)) | {64} | set(range(93, 100))


def test_the_interior_ht_nulls_are_masked() -> None:
    """94, 95 and 97 were once read as 'marginal'. They are HT nulls +30, +31, -31.

    channel_filter_en leaks neighbour energy into them, which is why a raw
    threshold saw them flicker between deployments. They carry no channel.
    """
    for i in (93, 94, 95, 96, 97, 98, 99):
        assert i in DEAD_SUBCARRIERS
        assert i not in DEFAULT_KEEP


def test_the_invalid_first_word_is_masked() -> None:
    """Bins 0 and 1 are raw constants.

    Divided by the packet mean, bin 0 became a pure inverse-level feature
    with the largest variance in the vector: the AGC level this module
    exists to remove, back in through the front door.
    """
    assert 0 in DEAD_SUBCARRIERS and 1 in DEAD_SUBCARRIERS


def test_select_subcarriers_shape() -> None:
    """Selection reduces the feature axis and leaves time untouched."""
    a = np.ones((50, N_SUBCARRIERS), dtype=np.float32)
    assert select_subcarriers(a).shape == (50, 107)
    assert select_subcarriers(a, keep=[0, 1, 2]).shape == (50, 3)


def test_select_subcarriers_rejects_bad_indices() -> None:
    """An out-of-range or empty selection is caught, not silently clipped."""
    a = np.ones((5, N_SUBCARRIERS), dtype=np.float32)
    with pytest.raises(ValueError):
        select_subcarriers(a, keep=[200])
    with pytest.raises(ValueError):
        select_subcarriers(a, keep=[])


def test_measure_dead_subcarriers_finds_injected_dead_bins() -> None:
    """The measurement tool recovers bins that are both empty and constant."""
    rng = np.random.default_rng(1)
    a = 30.0 + rng.normal(0, 2.0, size=(500, N_SUBCARRIERS))
    a[:, [5, 40, 100]] = 0.0
    assert measure_dead_subcarriers(a) == (5, 40, 100)


def test_measure_ignores_small_but_varying_bins() -> None:
    """A weak bin that still varies is informative and must be kept."""
    rng = np.random.default_rng(2)
    a = 30.0 + rng.normal(0, 2.0, size=(500, N_SUBCARRIERS))
    a[:, 7] = 0.5 + rng.normal(0, 2.0, size=500)   # small mean, real variance
    assert 7 not in measure_dead_subcarriers(a)


# --------------------------------------------------------------------------
# Records to matrix
# --------------------------------------------------------------------------


def test_records_to_matrix_shapes_and_order() -> None:
    """Records become a matrix in capture order with their monotonic times."""
    recs = [make_record(t=i / FS, value=10 + i) for i in range(20)]
    amp, ts = records_to_matrix(recs)
    assert amp.shape == (20, N_SUBCARRIERS)
    assert ts.shape == (20,)
    assert np.all(np.diff(ts) > 0)
    assert amp[0, 0] < amp[-1, 0]


def test_records_to_matrix_rejects_mixed_nodes() -> None:
    """Interleaving two channels would be undetectable downstream."""
    with pytest.raises(ValueError):
        records_to_matrix([make_record(node_id="RX1"), make_record(node_id="RX2")])


def test_records_to_matrix_applies_gain() -> None:
    """The AGC factor stored per packet is applied to the amplitude."""
    unity, _ = records_to_matrix([make_record(gain=1.0)])
    doubled, _ = records_to_matrix([make_record(gain=2.0)])
    assert doubled[0, 0] == pytest.approx(2.0 * unity[0, 0], rel=1e-5)


def test_records_to_matrix_handles_empty() -> None:
    """An empty session is not an error."""
    amp, ts = records_to_matrix([])
    assert amp.shape == (0, N_SUBCARRIERS) and ts.shape == (0,)


# --------------------------------------------------------------------------
# Resampling
# --------------------------------------------------------------------------


def test_resample_produces_a_uniform_grid() -> None:
    """The output grid is exactly 1/fs apart."""
    t = np.array([0.0, 0.007, 0.013, 0.021, 0.028])
    a = np.ones((5, 3))
    out, grid = resample_uniform(a, t, fs=FS)
    assert np.allclose(np.diff(grid), 1.0 / FS)
    assert out.shape[1] == 3


def test_resample_preserves_a_constant_level() -> None:
    """Interpolation is not a filter: a constant stays exactly constant.

    This is the near-DC guarantee the tracking branch depends on.
    """
    t = np.linspace(0, 1, 137)
    a = np.full((137, 4), 12.5)
    out, _ = resample_uniform(a, t, fs=FS)
    assert np.allclose(out, 12.5, atol=1e-5)


def test_resample_preserves_a_slow_trend() -> None:
    """A slow ramp, which is what a person changing position looks like."""
    t = np.linspace(0, 4.0, 600)
    ramp = np.linspace(0.0, 10.0, 600)[:, None]
    out, grid = resample_uniform(ramp, t, fs=FS)
    expected = np.interp(grid, t, ramp[:, 0])
    assert np.allclose(out[:, 0], expected, atol=1e-4)
    assert out[-1, 0] - out[0, 0] == pytest.approx(10.0, abs=0.1)


def test_resample_collapses_a_few_duplicate_timestamps() -> None:
    """Two samples at one instant would make the interpolation arbitrary."""
    t = np.arange(200) / FS
    t[50] = t[49]                       # one coincidence in 200
    a = np.arange(200, dtype=float)[:, None]
    out, grid = resample_uniform(a, t, fs=FS)
    assert np.all(np.isfinite(out))
    assert grid[0] == pytest.approx(0.0)


def test_resample_refuses_a_mass_duplicated_clock() -> None:
    """A clock that cannot resolve packets must raise, not discard the data.

    This is the real failure it guards: host stamps taken once per serial
    read give roughly seven packets per distinct value, so collapsing would
    silently throw away about 87 % of a capture.
    """
    t = np.repeat(np.arange(100) * 0.05, 7)        # 7 packets per stamp
    a = np.arange(t.size, dtype=float)[:, None]
    with pytest.raises(ValueError) as exc:
        resample_uniform(a, t, fs=FS)
    msg = str(exc.value)
    assert "duplicated" in msg and "device-anchored" in msg


def test_resample_rejects_backwards_time() -> None:
    """Monotonic time cannot go backwards; if it did, something is wrong."""
    with pytest.raises(ValueError):
        resample_uniform(np.ones((3, 1)), np.array([0.0, 0.02, 0.01]), fs=FS)


# --------------------------------------------------------------------------
# Outlier removal: must not become a filter
# --------------------------------------------------------------------------


def test_outlier_removal_replaces_an_impulse() -> None:
    """A single wild sample is pulled back to the local median."""
    rng = np.random.default_rng(3)
    a = 30.0 + rng.normal(0, 0.5, size=(400, 2))
    a[200, 0] = 500.0
    out = remove_outliers(a)
    assert out[200, 0] < 40.0


def test_outlier_removal_leaves_clean_data_untouched() -> None:
    """Nothing within the threshold is altered at all.

    This is what makes it safe: it is not a smoother, so it cannot quietly
    attenuate the motion band.
    """
    rng = np.random.default_rng(4)
    a = 30.0 + rng.normal(0, 0.5, size=(400, 3))
    out = remove_outliers(a)
    changed = np.abs(out - a.astype(np.float32)) > 1e-6
    assert changed.mean() < 0.01, "a clean signal should be essentially unchanged"


def test_outlier_removal_is_not_a_lowpass() -> None:
    """A 1 Hz component, squarely in the motion band, survives intact."""
    t = np.arange(0, 4.0, 1 / FS)
    sig = 30.0 + 5.0 * np.sin(2 * np.pi * 1.0 * t)
    out = remove_outliers(sig[:, None])[:, 0]
    assert out.std() == pytest.approx(sig.std(), rel=0.02)
    assert np.corrcoef(out, sig)[0, 1] > 0.999


def test_outlier_removal_preserves_the_dc_level() -> None:
    """It must not be a subtract-the-average operation, which is a highpass."""
    t = np.arange(0, 4.0, 1 / FS)
    sig = 42.0 + 0.5 * np.sin(2 * np.pi * 0.5 * t)
    out = remove_outliers(sig[:, None])[:, 0]
    assert out.mean() == pytest.approx(42.0, abs=0.05)


def test_outlier_removal_handles_short_input() -> None:
    """Too few samples to form a window is not an error."""
    a = np.ones((3, 2))
    assert remove_outliers(a).shape == (3, 2)


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------








def test_subtract_baseline_rejects_shape_mismatch() -> None:
    """A baseline from a different subcarrier set must not broadcast silently."""
    with pytest.raises(ValueError):
        subtract_baseline(np.ones((10, 107)), np.ones(128, dtype=np.float32))


# --------------------------------------------------------------------------
# The full chain
# --------------------------------------------------------------------------


def test_clean_session_shapes() -> None:
    """The chain yields aligned amplitude and a uniform grid."""
    recs = [make_record(t=i / FS) for i in range(600)]
    _c = clean_session(recs, fs=FS)
    amp, grid = _c.amplitude, _c.grid
    assert amp.shape[1] == 107
    assert amp.shape[0] == grid.shape[0]
    assert np.allclose(np.diff(grid), 1 / FS)








def test_clean_session_handles_empty_input() -> None:
    """No records is an empty result, not a crash."""
    _c = clean_session([], fs=FS)
    amp, grid = _c.amplitude, _c.grid
    assert amp.shape[0] == 0 and grid.shape[0] == 0


# --------------------------------------------------------------------------
# Device-clock anchoring
#
# The host stamps a whole serial read at once, so about seven packets share
# a value at 150 Hz. The device's own microsecond counter is unique per
# packet; anchoring it to host time recovers the resolution without losing
# cross-node comparability.
# --------------------------------------------------------------------------


def synth_clock(n: int = 3000, fs: float = FS, chunk: int = 8, t0_us: int = 1_000_000,
                host0: float = 5000.0, ppm: float = 0.0, seed: int = 0):
    """Build device timestamps and the chunk-quantised host stamps they cause."""
    rng = np.random.default_rng(seed)
    step_us = 1e6 / fs
    local = (t0_us + np.arange(n) * step_us).astype(np.int64)
    true_host = host0 + (local - t0_us) * 1e-6 * (1.0 + ppm / 1e6)
    # The host stamps every packet in a chunk with the time the read returned,
    # which is at or after the last packet in that chunk arrived.
    host = np.empty(n)
    for i in range(0, n, chunk):
        j = min(i + chunk, n)
        host[i:j] = true_host[j - 1] + rng.uniform(0.0, 0.002)
    return local, host, true_host


def test_device_clock_is_unique_where_the_host_clock_is_not() -> None:
    """The premise: the host stamp cannot resolve individual packets."""
    local, host, _ = synth_clock()
    assert len(np.unique(local)) == len(local)
    assert len(np.unique(host)) < len(host) / 5


def test_timebase_recovers_the_true_arrival_times() -> None:
    """Anchoring restores per-packet timing to well under a millisecond."""
    from pipeline.io.clean import apply_timebase, fit_timebase

    local, host, true_host = synth_clock()
    tb = fit_timebase(local, host)
    assert tb.ok
    err = apply_timebase(local, tb) - true_host
    assert np.abs(err - err.mean()).max() < 1e-3
    assert abs(err.mean()) < 5e-3, "a one-sided host latency should not leave a large bias"


def test_timebase_beats_raw_host_stamps() -> None:
    """The whole point: it is materially better than what it replaces."""
    from pipeline.io.clean import apply_timebase, fit_timebase

    local, host, true_host = synth_clock()
    tb = fit_timebase(local, host)
    raw_err = np.abs(host - true_host - (host - true_host).mean()).max()
    new_err = np.abs(apply_timebase(local, tb) - true_host - (apply_timebase(local, tb) - true_host).mean()).max()
    assert new_err < raw_err / 10


def test_timebase_tracks_a_clock_rate_error() -> None:
    """A crystal a few ppm off nominal is measured, not rejected.

    Measured over a long span, because the chunked host stamps leave a small
    edge bias in the rate estimate that falls off with the square of the
    span: about -7 ppm over 20 s and -0.07 ppm over 200 s. Real sessions run
    for minutes, and the rate estimate is diagnostic rather than something
    the timing depends on.
    """
    from pipeline.io.clean import fit_timebase

    local, host, _ = synth_clock(n=30000, ppm=25.0)
    tb = fit_timebase(local, host)
    assert tb.ok
    assert tb.ppm_error == pytest.approx(25.0, abs=1.0)


def test_rate_estimate_bias_is_negligible_at_short_spans() -> None:
    """Even the worst case is far below what the anchoring is fixing."""
    from pipeline.io.clean import fit_timebase

    local, host, _ = synth_clock(n=3000)          # 20 s
    tb = fit_timebase(local, host)
    span_s = (local[-1] - local[0]) * 1e-6
    drift_s = abs(tb.ppm_error) * 1e-6 * span_s
    assert drift_s < 1e-3, "rate bias must stay far below the 50 ms it replaces"


def test_timebase_rejects_an_implausible_rate() -> None:
    """A wrong slope would stretch the whole session, so it is refused."""
    from pipeline.io.clean import fit_timebase

    local, host, _ = synth_clock()
    tb = fit_timebase(local, host * 2.0)          # nothing like a clock
    assert not tb.ok and "ppm" in tb.reason


def test_timebase_rejects_too_few_packets() -> None:
    """A short burst cannot support a rate fit."""
    from pipeline.io.clean import fit_timebase

    local, host, _ = synth_clock(n=50)
    assert not fit_timebase(local, host).ok


def test_device_clock_wrap_is_unwrapped() -> None:
    """The 32-bit microsecond counter wraps every 71.6 minutes."""
    from pipeline.io.clean import DEVICE_CLOCK_MODULUS_US, unwrap_device_time

    raw = np.array([DEVICE_CLOCK_MODULUS_US - 2000, DEVICE_CLOCK_MODULUS_US - 1000, 0, 1000], dtype=np.int64)
    out, n_wraps = unwrap_device_time(raw)
    assert n_wraps == 1
    assert np.all(np.diff(out) > 0)
    assert out[2] - out[1] == 1000


def test_records_to_matrix_uses_the_device_clock() -> None:
    """Chunked host stamps in, distinct per-packet times out."""
    n = 800
    chunk = 8
    recs = []
    for i in range(n):
        # The host stamps a whole chunk at the time its last packet arrived,
        # so the host and device clocks agree on rate and differ only in
        # resolution. Anything else would be a rate mismatch, not chunking.
        r = make_record(t=((i // chunk) * chunk + chunk - 1) / FS, value=40)
        object.__setattr__(r, "local_timestamp", 1_000_000 + int(i * 1e6 / FS))
        recs.append(r)
    _, ts = records_to_matrix(recs)
    assert len(np.unique(ts)) == n, "every packet should get its own time"
    assert np.all(np.diff(ts) > 0)
    assert np.median(np.diff(ts)) == pytest.approx(1 / FS, rel=0.01)


def test_records_to_matrix_can_fall_back_to_host_stamps() -> None:
    """The old behaviour remains reachable for comparison."""
    recs = [make_record(t=(i // 8) * 0.05) for i in range(80)]
    for i, r in enumerate(recs):
        object.__setattr__(r, "local_timestamp", 1_000_000 + int(i * 1e6 / FS))
    _, ts = records_to_matrix(recs, use_device_clock=False)
    assert len(np.unique(ts)) == 10


# --------------------------------------------------------------------------
# Per-packet shape normalisation
#
# Measured 8 Sep 2026: -11.8 dB of real received power produced -0.5 dB of
# recorded amplitude. The AGC removes level before storage and cannot be
# locked or read on the ESP32. So level carries nothing, shape carries
# everything, and normalising each packet by its own mean is mandatory.
# --------------------------------------------------------------------------


def make_shaped_record(t: float, amps: np.ndarray, node_id: str = "RX1") -> CsiRecord:
    """A record whose per-subcarrier amplitude is the given 128-vector."""
    data = np.zeros(CSI_LEN, dtype=np.int8)
    data[1::2] = np.clip(np.round(amps), 0, 127).astype(np.int8)      # real part = amplitude, imag = 0
    r = make_record(node_id=node_id, t=t)
    object.__setattr__(r, "data", data)
    object.__setattr__(r, "local_timestamp", int(t * 1e6) + 1_000_000)
    return r


def _shape(seed: int = 0, n_live: int = 107) -> np.ndarray:
    """A fixed, non-trivial subcarrier profile with mean 1.0."""
    rng = np.random.default_rng(seed)
    v = 1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, n_live)) + 0.05 * rng.normal(size=n_live)
    return v / v.mean()


def test_normalise_is_scale_invariant() -> None:
    """A packet and the same packet scaled by any constant are identical after."""
    rng = np.random.default_rng(1)
    a = 20.0 + 10.0 * rng.random((50, 107))
    for k in (0.1, 2.0, 7.3, 100.0):
        assert np.allclose(normalise_shape(a), normalise_shape(k * a), atol=1e-6)


def test_normalised_packets_have_unit_mean() -> None:
    """Every packet's mean across live bins is exactly one afterwards."""
    rng = np.random.default_rng(2)
    out = normalise_shape(5.0 + rng.random((40, 107)))
    assert np.allclose(out.mean(axis=1), 1.0, atol=1e-6)


def test_normalise_refuses_unmasked_input() -> None:
    """Normalisation runs after dead-bin masking, never before.

    128 columns means the dead bins are still present; they would drag every
    packet's mean and the result would not be a shape.
    """
    with pytest.raises(ValueError) as exc:
        normalise_shape(np.ones((10, N_SUBCARRIERS)))
    assert "select_subcarriers" in str(exc.value)


def test_normalise_removes_a_gain_step() -> None:
    """An AGC gain switch in the middle of a capture vanishes.

    Without this, the step would be an amplitude discontinuity the motion
    gate could read as movement.
    """
    shape = _shape(3)
    a = np.tile(30.0 * shape, (400, 1))
    a[200:] *= 2.0                                  # the AGC halves its gain
    raw_jump = np.abs(a[200] - a[199]).max()
    out = normalise_shape(a)
    assert raw_jump > 10.0
    assert np.abs(out[200] - out[199]).max() < 1e-5
    assert np.allclose(out[:200], out[200:], atol=1e-5)


def test_normalise_handles_a_silent_packet() -> None:
    """A packet with no signal is zeros, not a divide by nearly nothing."""
    a = np.ones((3, 107)); a[1] = 0.0
    out = normalise_shape(a)
    assert np.all(np.isfinite(out))
    assert np.all(out[1] == 0.0)
    assert np.allclose(out[0], 1.0)


def test_normalise_is_not_temporal_mean_removal() -> None:
    """A subcarrier drifting slowly relative to the rest survives.

    Normalisation is across subcarriers within a packet. It must not touch
    a per-subcarrier offset along time, because that drift is the tracking
    branch's signal.
    """
    n = 300
    a = np.tile(30.0 * _shape(4), (n, 1))
    a[:, 5] *= np.linspace(1.0, 1.5, n)             # bin 5 slowly rises relative to the rest
    out = normalise_shape(a)
    assert out[-1, 5] - out[0, 5] > 0.3


def test_each_half_has_unit_mean_after_normalisation() -> None:
    """Two AGC scalars per packet, so two means: one per LTF half."""
    rng = np.random.default_rng(11)
    out = normalise_shape(5.0 + rng.random((40, 107)))
    is_lltf = np.array([i < HALF for i in DEFAULT_KEEP])
    assert np.allclose(out[:, is_lltf].mean(axis=1), 1.0, atol=1e-6)
    assert np.allclose(out[:, ~is_lltf].mean(axis=1), 1.0, atol=1e-6)


def test_a_gain_step_in_the_ht_half_alone_vanishes() -> None:
    """The bug this exists to fix.

    HT-STF re-trains the AGC after the legacy LTF, so the HT half can change
    gain on its own. A single whole-vector mean left that as a random step
    across the half boundary and a fake feature in the legacy bins.
    """
    shape = _shape(12)
    a = np.tile(30.0 * shape, (400, 1))
    is_lltf = np.array([i < HALF for i in DEFAULT_KEEP])
    a[200:, ~is_lltf] *= 2.0                        # the HT half re-trains to a different gain
    out = normalise_shape(a)
    assert np.abs(out[200] - out[199]).max() < 1e-5
    assert np.allclose(out[:200], out[200:], atol=1e-5)


def test_a_whole_vector_mean_would_not_have_removed_it() -> None:
    """Pins down that the old operation was wrong, not just different."""
    shape = _shape(13)
    a = np.tile(30.0 * shape, (2, 1))
    is_lltf = np.array([i < HALF for i in DEFAULT_KEEP])
    a[1, ~is_lltf] *= 2.0
    old = a / a.mean(axis=1, keepdims=True)
    assert np.abs(old[1] - old[0]).max() > 0.2, "a single mean leaves the step in"


def test_normalise_refuses_a_column_count_that_does_not_match_keep() -> None:
    """Without the matching keep it cannot tell which columns are which half."""
    with pytest.raises(ValueError) as exc:
        normalise_shape(np.ones((5, 100)))
    assert "keep" in str(exc.value)


def test_normalise_accepts_a_custom_keep_in_any_order() -> None:
    """An ablation may pass an unsorted or one-sided keep; halves follow the indices."""
    keep = [100, 5, 70, 10]                         # HT, legacy, HT, legacy
    a = np.array([[1.0, 3.0, 5.0, 7.0]], dtype=np.float32)
    out = normalise_shape(a, keep=keep)
    # legacy columns hold 3 and 7 (mean 5); HT columns hold 1 and 5 (mean 3)
    assert np.allclose(out[0], [1 / 3, 3 / 5, 5 / 3, 7 / 5])


def test_normalise_lltf_only_keep_is_one_half() -> None:
    """A legacy-only ablation normalises as a single group."""
    keep = [i for i in DEFAULT_KEEP if i < HALF]
    rng = np.random.default_rng(14)
    a = 5.0 + rng.random((10, len(keep)))
    out = normalise_shape(a, keep=keep)
    assert np.allclose(out.mean(axis=1), 1.0, atol=1e-6)


# --------------------------------------------------------------------------
# Baseline, in shape space
# --------------------------------------------------------------------------


def test_baseline_in_shape_space_leaves_empty_room_near_zero() -> None:
    """Subtracting the empty room's mean shape from itself leaves ~nothing."""
    rng = np.random.default_rng(5)
    shape = _shape(6)
    empty = np.tile(shape, (600, 1)) * (25.0 + 5.0 * rng.random((600, 1)))  # AGC-like level wander
    empty += rng.normal(0, 0.01, empty.shape)
    norm = normalise_shape(empty)
    base = estimate_baseline(norm)
    resid = subtract_baseline(norm, base)
    assert np.abs(resid).mean() < 0.01
    assert np.abs(resid.mean()) < 1e-3


def test_baseline_is_robust_to_a_person_passing_through() -> None:
    """The median shape ignores a minority of disturbed packets."""
    s0, s1 = _shape(7), _shape(8)
    a = np.tile(s0, (300, 1)); a[:80] = s1           # someone present for the first 80
    base = estimate_baseline(a)
    assert np.allclose(base, s0, atol=1e-6)


def test_subtract_baseline_keeps_a_shape_change() -> None:
    """A person at a new position changes the shape, and that change survives.

    This is the tracking signal: a deviation of the subcarrier profile from
    the empty room, not a change in level (which the AGC has removed).
    """
    s0, s1 = _shape(9), _shape(10)
    base = estimate_baseline(np.tile(s0, (100, 1)))
    out = subtract_baseline(np.tile(s1, (100, 1)), base)
    assert np.allclose(out[0], s1 - s0, atol=1e-6)
    assert np.abs(out).max() > 0.05


def test_estimate_baseline_rejects_unnormalised_input() -> None:
    """A level capture is not a shape and must not become a baseline."""
    with pytest.raises(ValueError) as exc:
        estimate_baseline(np.full((50, 107), 30.0))
    assert "normalise_shape" in str(exc.value)


def test_subtract_baseline_rejects_a_level_baseline() -> None:
    """A baseline from before the pipeline went shape-based is refused."""
    with pytest.raises(ValueError) as exc:
        subtract_baseline(np.ones((10, 107)), np.full(107, 20.0, dtype=np.float32))
    assert "level baseline" in str(exc.value)


# --------------------------------------------------------------------------
# The full chain, in shape space
# --------------------------------------------------------------------------


def _shaped_session(n: int, per_packet) -> list:
    """Records whose 128-bin amplitude comes from per_packet(i, t)."""
    t = np.arange(n) / FS
    return [make_shaped_record(t[i], per_packet(i, t[i])) for i in range(n)]


def test_clean_session_removes_a_mid_capture_gain_step() -> None:
    """A gain switch at the receiver leaves no edge in the cleaned output."""
    n = 900
    base = 30.0 * (1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, N_SUBCARRIERS)))
    recs = _shaped_session(n, lambda i, t: base * (2.0 if i >= n // 2 else 1.0))
    amp = clean_session(recs, fs=FS).amplitude
    mid = amp.shape[0] // 2
    assert np.abs(amp[mid + 5] - amp[mid - 5]).max() < 0.02


def test_clean_session_preserves_near_dc_in_shape() -> None:
    """No bandpass anywhere: a slow drift in one subcarrier's share survives.

    This is the rule the tracking branch depends on, restated in shape
    space. If a bandpass or a temporal mean removal ever creeps in, this
    catches it.
    """
    n = 900
    base = 30.0 * (1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, N_SUBCARRIERS)))
    def per(i, t):
        v = base.copy(); v[5] *= 1.0 + 0.8 * (i / n); return v
    amp = clean_session(_shaped_session(n, per), fs=FS).amplitude
    col = amp[:, DEFAULT_KEEP.index(5)]        # raw subcarrier 5, wherever the mask put it
    assert col[-50:].mean() - col[:50].mean() > 0.2, "the slow shape trend was removed; something is filtering"


def test_clean_session_preserves_the_motion_band_in_shape() -> None:
    """A 1 Hz modulation of one subcarrier's share survives the chain."""
    n = 900
    base = 30.0 * (1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, N_SUBCARRIERS)))
    def per(i, t):
        v = base.copy(); v[5] *= 1.0 + 0.4 * np.sin(2 * np.pi * 1.0 * t); return v
    amp = clean_session(_shaped_session(n, per), fs=FS).amplitude
    col = amp[:, DEFAULT_KEEP.index(5)]        # raw subcarrier 5, wherever the mask put it
    spec = np.abs(np.fft.rfft(col - col.mean()))
    freqs = np.fft.rfftfreq(len(col), 1 / FS)
    assert freqs[np.argmax(spec)] == pytest.approx(1.0, abs=0.2)


def test_clean_session_accepts_an_external_shape_baseline() -> None:
    """A supplied empty-room shape baseline is subtracted, not re-estimated."""
    base = 30.0 * (1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, N_SUBCARRIERS)))
    recs = _shaped_session(400, lambda i, t: base)
    live = list(DEFAULT_KEEP)
    shape_base = normalise_shape(base[live][None, :].astype(np.float32))[0]
    amp = clean_session(recs, fs=FS, baseline=shape_base).amplitude
    assert np.abs(amp).mean() < 0.02


def test_clean_session_output_packets_are_shape_deviations() -> None:
    """Each cleaned packet is a deviation from the baseline shape: mean ~0."""
    base = 30.0 * (1.0 + 0.3 * np.sin(np.linspace(0, 4 * np.pi, N_SUBCARRIERS)))
    amp = clean_session(_shaped_session(300, lambda i, t: base), fs=FS).amplitude
    assert np.abs(amp.mean(axis=1)).max() < 0.02


# --------------------------------------------------------------------------
# Device-counter restarts (10 September 2026)
#
# Four --reset baselines carried one to four packets from the board's
# previous boot ahead of the counter restart. A line fitted across the
# restart was refused and the pipeline fell back to the quantised host clock
# without saying so.
# --------------------------------------------------------------------------


def _restart_records(n: int = 800, stale: int = 3) -> list:
    """`stale` packets from a previous boot (counter high), then a fresh boot from ~0."""
    recs = []
    for i in range(n):
        r = make_record(t=((i // 8) * 8 + 7) / FS)
        local = 600_000_000 + int(i * 1e6 / FS) if i < stale else 14_000 + int((i - stale) * 1e6 / FS)
        object.__setattr__(r, "local_timestamp", local)
        recs.append(r)
    return recs


def test_a_counter_restart_is_not_a_wrap() -> None:
    """A fall from 600 s to 0 is a reboot, not a 71-minute wrap, and is left in place."""
    from pipeline.io.clean import device_epoch_start, unwrap_device_time
    raw = np.array([600_000_000, 600_006_667, 14_000, 20_667], dtype=np.int64)
    out, n_wraps = unwrap_device_time(raw)
    assert n_wraps == 0 and out[2] < out[1]
    assert device_epoch_start(raw) == 2
    assert device_epoch_start(np.array([1, 2, 3])) == 0


def test_fit_refuses_to_span_a_restart_and_says_so() -> None:
    from pipeline.io.clean import fit_timebase
    recs = _restart_records()
    tb = fit_timebase(np.array([r.local_timestamp for r in recs]), np.array([r.t_mono for r in recs]))
    assert not tb.ok and "restarted at packet 3" in tb.reason


def test_records_to_matrix_drops_the_stale_packets_and_anchors_the_rest() -> None:
    """The live bug: without this, those baselines silently used host stamps."""
    recs = _restart_records(n=800, stale=3)
    amp, ts = records_to_matrix(recs)
    assert amp.shape[0] == 797, "the three stale packets are gone"
    assert len(np.unique(ts)) == 797, "and the remainder is device-anchored, one time per packet"
    assert np.median(np.diff(ts)) == pytest.approx(1 / FS, rel=0.01)


def test_clean_session_reports_dropped_stale_packets() -> None:
    c = clean_session(_restart_records(n=800, stale=4), fs=FS)
    assert c.n_dropped_restart == 4
    assert c.amplitude.shape[0] == c.grid.shape[0] == c.packet_gap_s.shape[0]


# --------------------------------------------------------------------------
# Notion open items 3, 4, 5: Hampel before resample, one lattice, gaps carried
# --------------------------------------------------------------------------


def test_a_one_packet_spike_does_not_survive_as_two_half_height_samples() -> None:
    """Hampel runs on the packets, so the interpolator never sees the spike.

    The mechanism: a spike on a packet midway between two grid samples is
    split into two half-height samples by the interpolator. Measured on
    this synthetic data, spikes of 6 to 10 robust sigmas clear the 4-sigma
    Hampel threshold whole but not once halved, so the old order (resample,
    then Hampel) keeps 2.4 to 3.9 sigma of residue where the new order
    leaves noise. Very large spikes are caught either way; this is about
    the moderate ones a real capture actually contains.
    """
    from pipeline.io.clean import remove_outliers
    rng = np.random.default_rng(3)
    n, sigma = 900, 0.01
    t = (np.arange(n) + 0.5) / FS                          # every packet midway between grid samples
    base = np.ones((n, 4)) + rng.normal(0, sigma, (n, 4))
    for k in (6, 8, 10):
        a = base.copy()
        a[450] += k * sigma
        old = remove_outliers(resample_uniform(a, t, fs=FS, grid_origin=0.0)[0])
        new = resample_uniform(remove_outliers(a), t, fs=FS, grid_origin=0.0)[0]
        assert np.abs(old[445:455] - 1).max() > 2.2 * sigma, f"{k} sigma: the old order leaves the halves"
        assert np.abs(new[445:455] - 1).max() < 2.2 * sigma, f"{k} sigma: the new order removes the packet"


def test_clean_session_runs_hampel_before_the_resampler() -> None:
    rng = np.random.default_rng(4)
    recs = []
    for i in range(900):
        recs.append(make_record(t=i / FS + rng.uniform(-0.002, 0.002), value=40))
    spike = recs[450]
    object.__setattr__(spike, "data", np.full(CSI_LEN, 120, dtype=np.int8))
    amp = clean_session(recs, fs=FS).amplitude
    assert np.abs(amp[440:460]).max() < 0.1


def test_all_nodes_share_one_grid_lattice() -> None:
    """Three receivers with different first packets land on the same absolute lattice."""
    a = np.ones((300, 2))
    grids = [resample_uniform(a, 1000.0123 + k * 0.0031 + np.arange(300) / FS, fs=FS, grid_origin=0.0)[1] for k in range(3)]
    for g in grids:
        assert np.allclose((g * FS) - np.round(g * FS), 0.0, atol=1e-6)
    assert np.allclose(grids[0][1:], grids[1][:-1]) or np.allclose(grids[0], grids[1]) or abs(grids[0][0] - grids[1][0]) * FS % 1 < 1e-6


def test_own_origin_remains_available_for_one_node() -> None:
    a = np.ones((100, 1)); t = 7.123 + np.arange(100) / FS
    _, g = resample_uniform(a, t, fs=FS, grid_origin=None)
    assert g[0] == pytest.approx(7.123)


def test_packet_gap_survives_resampling() -> None:
    """A 500 ms hole is invisible in the interpolated amplitude and visible in the gap record."""
    from pipeline.io.clean import MAX_VERIFIED_GAP_S, packet_gap_on_grid
    t = np.concatenate([np.arange(300) / FS, 2.0 + 0.5 + np.arange(300) / FS])   # hole from ~2.0 s to 2.5 s
    a = np.ones((600, 1))
    out, grid = resample_uniform(a, t, fs=FS)
    gaps = packet_gap_on_grid(t, grid)
    inside = (grid > 2.0) & (grid < 2.5)
    assert np.all(np.abs(out - 1) < 1e-6), "the amplitude shows nothing"
    assert np.all(gaps[inside] > MAX_VERIFIED_GAP_S), "the gap record shows the hole"
    assert np.median(gaps[~inside]) == pytest.approx(1 / FS, rel=0.05)


def test_clean_session_carries_the_gap_record() -> None:
    recs = [make_record(t=i / FS) for i in range(300)] + [make_record(t=2.6 + i / FS) for i in range(300)]
    c = clean_session(recs, fs=FS)
    assert c.packet_gap_s.shape == c.grid.shape
    assert c.packet_gap_s.max() == pytest.approx(0.6 + 1 / FS, abs=0.02)
