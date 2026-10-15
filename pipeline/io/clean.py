"""Cleaning steps shared by every branch: amplitude, resampling, baseline.

This module is deliberately minimal. It produces one clean amplitude
representation that all three branches consume unchanged, so that any
difference between branch results is attributable to the branch itself.

PROJECT RULES ENCODED HERE
--------------------------
* NO bandpass filtering at this stage.
* NO PCA at this stage.
  Both belong inside the branches (see ``pipeline/branches/``), because the
  tracking branch must retain near-DC content that a shared bandpass would
  destroy, and PCA must be fit per-recording or on training data only.
* Phase is discarded: this project is amplitude only.
* PER-PACKET SHAPE NORMALISATION IS MANDATORY, and it runs immediately after
  dead-bin masking, before anything else. Each packet is divided by its own
  mean across the live subcarriers. See :func:`normalise_shape` for why.

THE PIPELINE IS SHAPE-BASED BY MEASUREMENT, NOT BY PREFERENCE
-------------------------------------------------------------
Measured 8 September 2026 on RX2 (ESP32-D0WD-V3): moving the transmitter to
change the received power by -11.8 dB changed the recorded CSI amplitude by
-0.5 dB. The receiver's automatic gain control normalises level away before
anything reaches storage, it cannot be locked or read on the plain ESP32
(esp_csi_gain_ctrl is an empty stub for this target, agc_gain is absent from
wifi_pkt_rx_ctrl_t, the digital manu_scale stage sits downstream of it, and
the PHY's own disable_wifi_agc forces a gain that stops packets decoding).

So absolute amplitude and cross-link level ratios carry no information here.
What the AGC cannot touch is the SHAPE across subcarriers, because it applies
one scalar per packet: relative structure across the live bins survives, and
that structure is frequency-selective fading, which is where position
information lives. Normalising each packet by its own mean therefore costs
nothing, and it removes the gain-switching steps that would otherwise appear
as amplitude discontinuities the motion gate could read as movement.

Absolute-amplitude features must not be added anywhere. If raw amplitude ever
became available on other hardware it would be an extra channel and an
ablation, never a dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.io.parse import CSI_LEN, N_SUBCARRIERS, CsiRecord, extract_amplitude

#: Index at which the HT-LTF half of the payload begins. The 128 complex
#: values are two 64-point estimates of the same channel: the legacy LTF in
#: 0-63 and the HT-LTF in 64-127, each in FFT order (subcarrier 0, +1..+31,
#: then -32..-1).
HALF: int = N_SUBCARRIERS // 2

#: Subcarriers that are structurally empty, from the 802.11 HT20 layout
#: rather than from measurement. In FFT order the nulls are DC (k = 0), the
#: upper guard (+27..+31 for the 52-subcarrier legacy LTF, +29..+31 for the
#: 56-subcarrier HT-LTF) and the lower guard (-32..-27, i.e. k = 32..37,
#: legacy; -32..-29, k = 32..35, HT). Bins 0 and 1 are additionally the
#: hardware-invalid first word IDF documents (``first_word``), which the
#: radio fills with constants.
#:
#: Measured 8 September 2026 on a 15,002-packet walk: 28-36 read exactly 0;
#: 27 and 37 read 4-6 against live neighbours at 17-25, and the HT nulls
#: 93-99 read 1-8 against live neighbours at 29-47, because
#: ``channel_filter_en`` smooths adjacent bins and leaks 10-16 dB of
#: neighbour energy into an empty one. That leakage is why an amplitude
#: threshold in raw units under-reports the HT half, and why 94, 95 and 97
#: were once read as "marginal": they are the interior HT nulls, not
#: sometimes-useful channels. Bin 0 was the worst of all: a raw constant,
#: which after division by the packet mean became a pure inverse-level
#: feature with the largest variance in the vector, smuggling the AGC level
#: this module exists to remove back in through the front door.
#:
#: The mask must stay FIXED across the whole dataset, since the per-link CNN
#: shares weights and every link must present the same input layout.
LLTF_NULLS: tuple[int, ...] = (0, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37)
HT_NULLS: tuple[int, ...] = tuple(HALF + k for k in (0, 29, 30, 31, 32, 33, 34, 35))
INVALID_FIRST_WORD: tuple[int, ...] = (0, 1)

DEAD_SUBCARRIERS: tuple[int, ...] = tuple(sorted(set(LLTF_NULLS) | set(HT_NULLS) | set(INVALID_FIRST_WORD)))

#: Subcarriers retained by default: everything not in :data:`DEAD_SUBCARRIERS`.
#: 107 of 128: 51 from the legacy half, 56 from the HT half.
DEFAULT_KEEP: tuple[int, ...] = tuple(i for i in range(N_SUBCARRIERS) if i not in DEAD_SUBCARRIERS)

#: A packet whose mean amplitude over the live bins is below this carries no
#: signal, and dividing by it would only amplify noise. Such packets are set
#: to zero shape rather than divided.
MIN_PACKET_MEAN: float = 1e-3

#: A subcarrier whose mean amplitude and temporal spread are both below these
#: is carrying nothing. Used by :func:`measure_dead_subcarriers`.
DEAD_MEAN_THRESHOLD: float = 1.0
DEAD_STD_THRESHOLD: float = 0.5

#: Window either side of a sample used by the Hampel outlier filter, so the
#: comparison window is ``2 * OUTLIER_WINDOW + 1`` samples: 21 at this
#: setting, which is 140 ms at 150 Hz and far shorter than any motion the
#: branches care about.
#:
#: Chosen by measurement. A MAD estimated from too few samples is itself
#: noisy, which flags clean data as outliers. On Gaussian noise the measured
#: false-positive rate was 1.23 % at a window of 5 and 0.38 % at 10, both
#: still catching an injected impulse; 15 bought almost nothing further.
OUTLIER_WINDOW: int = 10

#: Deviations from the local median, in robust sigmas, beyond which a sample
#: is treated as an impulse rather than signal. At 3.0 the false-positive
#: rate rose to 1.65 %, which starts to smooth rather than despike.
OUTLIER_SIGMAS: float = 4.0

#: Scale factor converting a median absolute deviation to a standard
#: deviation for normally distributed data.
_MAD_TO_SIGMA: float = 1.4826

#: The device's ``local_timestamp`` is a 32-bit microsecond counter, so it
#: wraps every 4294.967 s, about 71.6 minutes. A session can straddle a wrap.
DEVICE_CLOCK_MODULUS_US: int = 1 << 32

#: Nominal host seconds per device microsecond.
NOMINAL_SLOPE: float = 1e-6

#: How far the fitted clock rate may stray from nominal before the fit is
#: rejected. Crystal tolerance on these boards is tens of ppm; 500 ppm is far
#: outside that and means the fit found something other than a clock.
MAX_CLOCK_PPM: float = 500.0

#: A backwards step in the device counter is a 32-bit wrap only if the
#: counter was within this many microseconds of the modulus when it stepped.
#: Any other backwards step is a restart: the board rebooted and its counter
#: began again from zero. Measured 10 September 2026 on four ``--reset``
#: baselines: the reset pulse rebooted the board after one to four packets
#: from the previous boot had already been read, so the counter fell by 91
#: to 1930 s at packet 0 to 3. A single line fitted across that restart
#: reported a clock rate of up to -758,000 ppm and was refused, and the
#: fallback was the quantised host clock, silently, on baselines that feed
#: :func:`subtract_baseline` and the per-session presence threshold.
WRAP_MARGIN_US: int = 2_000_000

#: The longest inter-packet gap verified to interpolate cleanly, in seconds.
#: Zaid's RX3 captures carry single gaps of 527 ms (day 1) and 254 ms (day
#: 2) that exceed it. They are not chased in hardware. Instead the gap
#: between the source packets bracketing every uniform sample is carried
#: through cleaning (see :func:`packet_gap_on_grid`), so a window's maximum
#: packet gap sits in its metadata and windows over this ceiling can be
#: flagged at evaluation. Losses are non-random in time and must be carried,
#: not hidden: the 10 September audit found every failing capture's losses
#: spread evenly through the file and unchanged by whether a body was in
#: the link (3.8 percent walking, 4.2 standing, 4.1 otherwise), which rules
#: out line-of-sight blockage as their cause but not their relevance.
MAX_VERIFIED_GAP_S: float = 0.25

#: Quantile of the fit residuals taken as the true arrival line. Host stamps
#: are taken after a read returns, so every one is LATE by an unknown amount
#: and none is ever early: the latency is one-sided. A least-squares line
#: therefore sits in the middle of the latency spread rather than on the
#: arrivals. Shifting it down to a low quantile removes that bias while
#: staying robust to the occasional outlier that a strict minimum would chase.
ARRIVAL_QUANTILE: float = 0.02

#: Above this share of duplicated timestamps, the host clock is quantised by
#: the serial read boundary rather than resolving individual packets, and
#: resampling from it would discard most of the capture.
MAX_DUPLICATE_TIMESTAMP_FRACTION: float = 0.05


def to_amplitude(raw_csi: np.ndarray) -> np.ndarray:
    """Convert one interleaved int8 CSI packet to subcarrier amplitudes.

    Args:
        raw_csi: Interleaved int8 array of length exactly 256, ordered
            (imag, real) per subcarrier, 128 complex pairs.

    Returns:
        Float array of shape ``(128,)`` giving per-subcarrier magnitude.

    Constraints:
        Amplitude only; phase is computed nowhere and stored nowhere.
        Input length other than 256 is a programming error upstream and is
        rejected here rather than silently reshaped.
    """
    arr = np.asarray(raw_csi)
    if arr.shape != (CSI_LEN,):
        raise ValueError(f"expected a ({CSI_LEN},) CSI payload, got {arr.shape}")
    pairs = arr.astype(np.float32).reshape(N_SUBCARRIERS, 2)
    return np.sqrt(pairs[:, 0] ** 2 + pairs[:, 1] ** 2, dtype=np.float32)


def measure_dead_subcarriers(
    amplitude: np.ndarray,
    mean_threshold: float = DEAD_MEAN_THRESHOLD,
    std_threshold: float = DEAD_STD_THRESHOLD,
) -> tuple[int, ...]:
    """Find which subcarriers carry no signal in a given capture.

    Args:
        amplitude: Amplitude array of shape ``(n_samples, n_sub)``.
        mean_threshold: Mean amplitude below which a bin is considered empty.
        std_threshold: Temporal spread below which a bin is considered
            constant.

    Returns:
        The indices that are both near-zero and unvarying.

    Constraints:
        Both conditions must hold. A bin can be small but informative, and a
        bin can be large but stuck; only one that is both is truly dead.

        This is a diagnostic, not the source of :data:`DEAD_SUBCARRIERS`,
        which is fixed by the 802.11 layout. Its thresholds are in raw int8
        units, and the HT half of the payload is scaled about 1.7x larger
        than the legacy half while ``channel_filter_en`` leaks neighbour
        energy into empty bins, so it UNDER-REPORTS the HT nulls (93-99
        read 1-8 raw against a threshold of 1). Read its output as "is
        anything OUTSIDE the structural mask dead on this board", never as
        "is the mask right".
    """
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    mean = a.mean(axis=0)
    std = a.std(axis=0)
    return tuple(int(i) for i in np.where((mean < mean_threshold) & (std < std_threshold))[0])


def select_subcarriers(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    """Drop guard/null subcarriers and keep a usable subcarrier set.

    Args:
        amplitude: Amplitude array of shape ``(n_packets, 128)``.
        keep: Explicit subcarrier indices to retain. If ``None``, the
            project default set (pilots and null subcarriers removed) is used.

    Returns:
        Amplitude array of shape ``(n_packets, n_keep)``.

    Constraints:
        The same subcarrier set must be used for every node and every
        session in a given experiment. Passing ``keep`` explicitly is for
        ablations; production paths take the default so the input layout
        cannot drift between links or sessions.
    """
    a = np.asarray(amplitude)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    idx = np.asarray(DEFAULT_KEEP if keep is None else list(keep), dtype=int)
    if idx.size == 0:
        raise ValueError("keep must retain at least one subcarrier")
    if idx.min() < 0 or idx.max() >= a.shape[1]:
        raise ValueError(f"keep indices out of range for {a.shape[1]} subcarriers")
    return a[:, idx]


@dataclass(frozen=True)
class Timebase:
    """A fit relating one receiver's device clock to host time.

    Attributes:
        slope: Host seconds per device microsecond, nominally 1e-6.
        offset: Host seconds corresponding to device time zero.
        residual_std: Spread of the host stamps about the fitted line, in
            seconds. Expect roughly the serial read period: it measures the
            host's timing jitter, not the device's.
        n: Packets the fit used.
        n_wraps: Times the device counter wrapped during the session.
        ppm_error: Fitted clock rate error against nominal, in parts per
            million.
        ok: Whether the fit is usable. False means the caller must fall back
            to raw host stamps.
        reason: Why the fit was rejected, empty when ``ok``.
    """

    slope: float
    offset: float
    residual_std: float
    n: int
    n_wraps: int
    ppm_error: float
    ok: bool
    reason: str = ""


def unwrap_device_time(local_us: np.ndarray) -> tuple[np.ndarray, int]:
    """Undo the wrapping of the device's 32-bit microsecond counter.

    Args:
        local_us: Raw ``local_timestamp`` values in capture order.

    Returns:
        A tuple of (monotonically increasing microseconds as int64, number
        of wraps detected).

    Constraints:
        A wrap is a backwards step taken while the counter sat within
        :data:`WRAP_MARGIN_US` of the modulus, which at 150 Hz cannot be
        confused with an out-of-order packet. A backwards step from anywhere
        else is not a wrap but a restart, the board having rebooted, and it
        is left in place for :func:`device_epoch_start` to find: adding a
        modulus to it would manufacture a gap of up to 71 minutes.
    """
    t = np.asarray(local_us, dtype=np.int64)
    if t.size < 2:
        return t, 0
    d = np.diff(t)
    wraps = (d < 0) & (t[:-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US)
    n_wraps = int(wraps.sum())
    if n_wraps:
        t = t + np.concatenate(([0], np.cumsum(wraps))) * DEVICE_CLOCK_MODULUS_US
    return t, n_wraps


def device_epoch_start(local_us: np.ndarray) -> int:
    """Index of the first packet of the device's current boot.

    Args:
        local_us: Raw ``local_timestamp`` values in capture order.

    Returns:
        0 when the counter never restarted; otherwise the index just after
        the last backwards step that is not a 32-bit wrap. Packets before
        it belong to a previous boot of the board.

    Constraints:
        A ``--reset`` capture opens the port and then pulses RTS, so the
        first packets read can predate the reboot. Their counter values are
        on a different epoch and cannot be anchored with the rest; a fit
        across the restart is meaningless and is refused by
        :func:`fit_timebase`. :func:`records_to_matrix` drops them.
    """
    t = np.asarray(local_us, dtype=np.int64)
    if t.size < 2:
        return 0
    d = np.diff(t)
    restarts = np.flatnonzero((d < 0) & ~(t[:-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US))
    return int(restarts[-1] + 1) if restarts.size else 0


def anchor_times(local_us: np.ndarray, t_mono: np.ndarray) -> tuple[np.ndarray, int]:
    """Device-anchored host times for a capture, dropping any stale epoch.

    Args:
        local_us: Raw ``local_timestamp`` values in capture order.
        t_mono: Host stamps for the same packets.

    Returns:
        A tuple of (host-referenced times for the packets from the device's
        current boot onward, index of the first such packet). The caller
        slices its own arrays from that index. Falls back to the raw host
        stamps, from the same index, if the fit is refused.
    """
    local = np.asarray(local_us, dtype=np.int64)
    ts = np.asarray(t_mono, dtype=np.float64)
    start = device_epoch_start(local)
    local, ts = local[start:], ts[start:]
    tb = fit_timebase(local, ts)
    return (apply_timebase(local, tb) if tb.ok else ts), start


def fit_timebase(local_us: np.ndarray, t_host: np.ndarray) -> Timebase:
    """Anchor a receiver's device clock to host time.

    Args:
        local_us: Raw device ``local_timestamp`` values, in capture order.
        t_host: Host stamps for the same packets, from ``t_mono``.

    Returns:
        The fitted :class:`Timebase`.

    Constraints:
        This exists because the host stamps are quantised by the serial read
        boundary: the reader takes one clock reading per read and applies it
        to every line in that chunk, so at 150 Hz roughly seven packets
        share a stamp and only about 13 % of a capture has a distinct host
        time. The device counter, by contrast, is unique for every packet.

        The fit gives per-packet microsecond resolution while keeping the
        result on the host clock, which is what makes it comparable across
        nodes and against the ground-truth anchors.

        The line is shifted to the :data:`ARRIVAL_QUANTILE` of the residuals
        rather than left at the least-squares centre. Host latency is
        one-sided, never negative, so the centre of the spread sits about
        half a read period late; the low quantile sits on the arrivals.

        A fit whose rate is implausible is rejected rather than used, since
        a wrong slope would stretch or compress the whole session's timing.

        ``ppm_error`` is diagnostic, not a correction that anything depends
        on. The chunked host stamps give it a small edge bias that shrinks
        with the square of the span: measured against synthetic data with an
        exactly known rate, -7 ppm over 20 s and -0.07 ppm over 200 s. Even
        the 20 s figure is 140 us of drift across the whole record, which is
        nothing beside the 50 ms of quantisation this function exists to
        remove. Real sessions run for minutes.
    """
    x_us, n_wraps = unwrap_device_time(local_us)
    y = np.asarray(t_host, dtype=np.float64)
    n = int(x_us.size)

    start = device_epoch_start(local_us)
    if start:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False,
                        f"device counter restarted at packet {start}: {start} stale packet(s) from a "
                        f"previous boot precede it; drop them before fitting")
    if n < 100:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False, f"only {n} packets")
    if np.unique(x_us).size < n // 2:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False, "device clock is not unique per packet")

    # Fit in approximate seconds rather than raw microseconds. Over a long
    # session the raw values span tens of millions, and the normal equations
    # then lose enough precision to shift the fitted rate by several ppm:
    # measured at -7 ppm on synthetic data with an exactly known answer.
    x = x_us.astype(np.float64)
    x0 = x[0]
    xs = (x - x0) * NOMINAL_SLOPE
    m, intercept = np.polyfit(xs, y, 1)
    slope = m * NOMINAL_SLOPE

    ppm = (slope / NOMINAL_SLOPE - 1.0) * 1e6
    if abs(ppm) > MAX_CLOCK_PPM:
        return Timebase(slope, intercept, float("nan"), n, n_wraps, float(ppm), False, f"clock rate {ppm:+.0f} ppm from nominal")

    resid = y - (m * xs + intercept)
    intercept += float(np.quantile(resid, ARRIVAL_QUANTILE))

    return Timebase(
        slope=float(slope),
        offset=float(intercept - slope * x0),
        residual_std=float(resid.std()),
        n=n,
        n_wraps=n_wraps,
        ppm_error=float(ppm),
        ok=True,
    )


def apply_timebase(local_us: np.ndarray, tb: Timebase) -> np.ndarray:
    """Convert device timestamps to host-referenced seconds.

    Args:
        local_us: Raw device ``local_timestamp`` values, in capture order.
        tb: A fitted :class:`Timebase` for the same node and session.

    Returns:
        Host-referenced times in seconds, one per packet.
    """
    x, _ = unwrap_device_time(local_us)
    return tb.slope * x.astype(np.float64) + tb.offset


def normalise_shape(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    """Divide each LTF half of each packet by that half's own mean.

    Args:
        amplitude: Amplitude array of shape ``(n_packets, n_live)``, AFTER
            dead-bin masking with the same ``keep``.
        keep: The subcarrier indices the columns came from, in column
            order. Project default if ``None``. Needed to know which columns
            are legacy-LTF and which are HT-LTF.

    Returns:
        Array of the same shape in which every packet's legacy half has mean
        1.0 across its bins and its HT half has mean 1.0 across its bins, so
        the packet as a whole has mean 1.0 too. Only the relative structure
        across bins remains.

    Constraints:
        * TWO scalars per packet, not one. The 802.11n mixed preamble trains
          the AGC on L-STF before the legacy LTF and then re-trains it on
          HT-STF before the HT-LTF, so the two halves arrive with
          independent gains. Measured 8 September 2026 on a walk: legacy
          per-packet level CV 0.076, HT half CV 0.244, correlation between
          them 0.53, ratio ranging 0.6 to 3.8. Dividing the whole vector by
          one mean therefore left a random +/-20 % step at the half boundary
          and injected the HT scalar into the clean legacy bins: a fake
          feature that would have been the ID branch's first principal
          component. Each half is scaled by its own mean.
        * Runs immediately after :func:`select_subcarriers` and before any
          resampling, despiking or baseline work. It refuses input that is
          still 128 wide, since the dead bins would drag every packet's mean
          and the result would not be a shape; and it refuses a column count
          that does not match ``keep``, since it then cannot tell the halves
          apart.
        * Invariant to any scalar applied to either half of a packet: a
          packet and the same packet with one half scaled by an arbitrary
          constant produce identical output. That is exactly what the
          receiver's AGC does, so a gain step between two packets, in either
          half, vanishes here.
        * A half with no signal at all is returned as zeros, not divided by
          something near zero.
        * This is normalisation ACROSS SUBCARRIERS within one packet. It is
          not temporal mean removal, which remains forbidden: a subcarrier's
          normalised value drifting slowly over time is the tracking signal.
    """
    a = np.asarray(amplitude, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError(f"expected (n_packets, n_live), got {a.shape}")
    if a.shape[1] == N_SUBCARRIERS:
        raise ValueError(
            f"normalise_shape received {N_SUBCARRIERS} subcarriers: dead bins are still "
            f"present. Call select_subcarriers first; the empty bins would drag every "
            f"packet's mean and the result would not be a shape."
        )
    idx = tuple(DEFAULT_KEEP if keep is None else keep)
    if a.shape[1] != len(idx):
        raise ValueError(
            f"normalise_shape got {a.shape[1]} columns but keep names {len(idx)} subcarriers: "
            f"pass the same keep that select_subcarriers used, or it cannot tell the legacy "
            f"half from the HT half."
        )
    is_lltf = np.fromiter((i < HALF for i in idx), dtype=bool, count=len(idx))

    out = np.empty_like(a)
    for cols in (is_lltf, ~is_lltf):
        if not cols.any():
            continue
        part = a[:, cols]
        m = part.mean(axis=1, keepdims=True)
        live = m > MIN_PACKET_MEAN
        safe = np.where(live, m, 1.0)
        scaled = part / safe
        scaled[~live.ravel()] = 0.0
        out[:, cols] = scaled
    return out


def records_to_matrix(
    records: Sequence[CsiRecord],
    use_device_clock: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Stack per-node records into an amplitude matrix and a time vector.

    Args:
        records: Validated records from a single node, in capture order.
        use_device_clock: Anchor the device's per-packet microsecond counter
            to host time instead of using the raw host stamps. On by
            default, and only turned off to reproduce the old behaviour.

    Returns:
        A tuple of (amplitude array of shape ``(n_packets, 128)``,
        timestamp array of shape ``(n_packets,)`` in host-referenced
        seconds).

    Constraints:
        All records must share one ``node_id``; mixing nodes is rejected,
        because the resulting matrix would interleave two different channels
        and nothing downstream could detect it.

        Times are host-referenced but derived from the device counter. The
        raw ``t_mono`` stamps are quantised by the serial read boundary,
        with roughly seven packets sharing a value at 150 Hz, so using them
        directly costs about 50 ms of timing resolution: 7 cm of position
        error at walking pace, and larger than the whole reaction-time
        budget. The device counter is unique per packet, and anchoring it to
        the host clock keeps the result comparable across nodes and against
        the ground-truth anchors.

        If the anchoring fails, the raw host stamps are used instead, which
        is worse but never wrong in kind.

        Packets that predate a restart of the device counter (see
        :func:`device_epoch_start`) are dropped before the fit. They are
        one to four stale packets from the board's previous boot, and
        keeping them would either refuse the fit or, worse, time them
        hundreds of seconds away from their neighbours.
    """
    if not records:
        return np.zeros((0, N_SUBCARRIERS), dtype=np.float32), np.zeros(0, dtype=np.float64)

    node_ids = {r.node_id for r in records}
    if len(node_ids) != 1:
        raise ValueError(f"records span multiple nodes: {sorted(node_ids)}")

    amp = np.empty((len(records), N_SUBCARRIERS), dtype=np.float32)
    ts = np.empty(len(records), dtype=np.float64)
    local = np.empty(len(records), dtype=np.int64)
    for i, rec in enumerate(records):
        amp[i] = extract_amplitude(rec)
        ts[i] = rec.t_mono
        local[i] = rec.local_timestamp

    if use_device_clock:
        ts, start = anchor_times(local, ts)
        return amp[start:], ts
    start = device_epoch_start(local)
    return amp[start:], ts[start:]


def resample_uniform(
    amplitude: np.ndarray,
    timestamps: np.ndarray,
    fs: float,
    grid_origin: Optional[float] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Resample irregular packet arrivals onto a uniform time grid.

    Args:
        amplitude: Amplitude array of shape ``(n_packets, n_sub)``.
        timestamps: Capture times of shape ``(n_packets,)``, non-decreasing.
        fs: Target sampling rate in Hz for the uniform grid.
        grid_origin: Absolute time the grid is a multiple of ``1/fs`` from.
            ``None`` anchors the grid at this capture's own first sample,
            which is fine for one node alone and wrong for three: each
            receiver's first packet lands at a different instant, so their
            grids differ by a fraction of a sample and a window cut by
            index on each is not the same window. Pass the same origin
            for every node of a session (``clean_session`` uses 0.0, so
            the lattice is the absolute host-time multiples of ``1/fs``)
            and every node's grid lies on one lattice; a window at
            absolute time ``k / fs`` is then the same window on all three.

    Returns:
        A tuple of (resampled amplitude of shape ``(n_samples, n_sub)``,
        uniform timestamp grid of shape ``(n_samples,)``).

    Constraints:
        Linear interpolation only; no frequency-selective filtering is
        applied here, so the near-DC content the tracking branch depends on
        survives untouched.

        A few duplicate timestamps are collapsed, since two samples at one
        instant would make the interpolation arbitrary. But a capture where
        MOST stamps are duplicated is not a few coincidences: it is a clock
        that cannot resolve individual packets, and collapsing would discard
        the bulk of the data. That raises rather than silently proceeding,
        because a guard that quietly throws away most of a capture is worse
        than no guard at all.
    """
    a = np.asarray(amplitude, dtype=np.float64)
    t = np.asarray(timestamps, dtype=np.float64)
    if a.ndim != 2 or t.ndim != 1 or a.shape[0] != t.shape[0]:
        raise ValueError(f"shape mismatch: amplitude {a.shape}, timestamps {t.shape}")
    if fs <= 0:
        raise ValueError("fs must be positive")
    if a.shape[0] < 2:
        return a.astype(np.float32), t

    if np.any(np.diff(t) < 0):
        raise ValueError("timestamps must be non-decreasing")

    uniq, first = np.unique(t, return_index=True)
    dup_fraction = 1.0 - uniq.size / t.size
    if dup_fraction > MAX_DUPLICATE_TIMESTAMP_FRACTION:
        raise ValueError(
            f"{dup_fraction:.1%} of timestamps are duplicated ({uniq.size} distinct of "
            f"{t.size}). Resampling would discard most of this capture. The host clock "
            f"is quantised by the serial read boundary; use the device-anchored times "
            f"from records_to_matrix instead of raw t_mono."
        )
    a = a[first]
    t = uniq

    if grid_origin is None:
        start = t[0]
    else:
        start = grid_origin + np.ceil((t[0] - grid_origin) * fs - 1e-9) / fs
    n = int(np.floor((t[-1] - start) * fs + 1e-9)) + 1
    grid = start + np.arange(n, dtype=np.float64) / fs
    out = np.empty((n, a.shape[1]), dtype=np.float32)
    for j in range(a.shape[1]):
        out[:, j] = np.interp(grid, t, a[:, j])
    return out, grid


def packet_gap_on_grid(timestamps: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """The interval between the source packets that bracket each grid sample.

    Args:
        timestamps: Capture times of the source packets, non-decreasing.
        grid: The uniform grid returned by :func:`resample_uniform`.

    Returns:
        Seconds, shape ``(n_samples,)``. A sample interpolated inside a
        long gap reports that gap; a sample in dense data reports the
        packet period, about 1/150 s.

    Constraints:
        Resampling hides packet loss: an interpolated sample looks like any
        other. This is the record that survives it. A window's maximum over
        this array is the ``max_packet_gap`` its metadata carries, and a
        window whose maximum exceeds :data:`MAX_VERIFIED_GAP_S` is one the
        evaluation can flag or exclude. Losses are non-random in time and
        are carried for later analysis, never hidden.
    """
    t = np.asarray(timestamps, dtype=np.float64)
    g = np.asarray(grid, dtype=np.float64)
    if t.size < 2:
        return np.zeros(g.shape, dtype=np.float32)
    t = np.unique(t)
    hi = np.clip(np.searchsorted(t, g, side="right"), 1, t.size - 1)
    return (t[hi] - t[hi - 1]).astype(np.float32)


def remove_outliers(amplitude: np.ndarray) -> np.ndarray:
    """Suppress impulsive amplitude spikes from packet-level glitches.

    Args:
        amplitude: Amplitude array of shape ``(n_samples, n_sub)``.

    Returns:
        Array of the same shape with impulsive outliers replaced.

    Constraints:
        A Hampel filter: each sample is compared with the median of its
        local window, and only samples further than
        :data:`OUTLIER_SIGMAS` robust sigmas away are replaced by that
        median. Everything else is returned bit-for-bit unchanged.

        That property is the point. A plain median or moving average would
        act as a lowpass on the motion band, and a subtract-the-average
        variant would act as a highpass and destroy the near-DC trend the
        tracking branch regresses position from. This touches only the
        spikes.
    """
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    n = a.shape[0]
    w = OUTLIER_WINDOW
    if n < 2 * w + 1:
        return a.astype(np.float32)

    # Sliding windows of length 2w+1, edges handled by edge replication so
    # the first and last samples are still examined.
    padded = np.pad(a, ((w, w), (0, 0)), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * w + 1, axis=0)
    med = np.median(windows, axis=-1)
    mad = np.median(np.abs(windows - med[..., None]), axis=-1)
    sigma = _MAD_TO_SIGMA * mad

    # Where the window is perfectly flat the MAD is zero; treat those as
    # having no spread rather than flagging every tiny deviation.
    with np.errstate(invalid="ignore", divide="ignore"):
        is_outlier = np.abs(a - med) > OUTLIER_SIGMAS * sigma
    is_outlier &= sigma > 0

    out = np.where(is_outlier, med, a)
    return out.astype(np.float32)


def estimate_baseline(amplitude: np.ndarray) -> np.ndarray:
    """Estimate the per-session static baseline for each subcarrier.

    Args:
        amplitude: Amplitude array of shape ``(n_samples, n_sub)`` for one
            node in one session, ideally covering an empty-room interval.

    Returns:
        Baseline vector of shape ``(n_sub,)``.

    Constraints:
        Operates in SHAPE space: the input must already be per-packet
        normalised, and the result is the empty room's mean shape across
        subcarriers, not a mean level. A level baseline is meaningless on
        this hardware because the AGC has removed level before storage.
        Input whose overall mean is not close to 1.0 is rejected as not
        normalised.

        Estimated per session and per node. A baseline is never carried
        across sessions or rooms, since the static multipath differs: the
        furniture, the cabling and the seated operator are all part of it.

        The median is used rather than the mean so that a person moving
        through part of the interval does not drag the estimate.
    """
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    if a.shape[0] == 0:
        raise ValueError("cannot estimate a baseline from zero samples")
    overall = float(a[a.sum(axis=1) > 0].mean()) if np.any(a.sum(axis=1) > 0) else 1.0
    if abs(overall - 1.0) > 0.5:
        raise ValueError(
            f"estimate_baseline expects per-packet normalised input (mean ~1.0), got mean "
            f"{overall:.3g}. Call normalise_shape first; baselines live in shape space."
        )
    return np.median(a, axis=0).astype(np.float32)


def subtract_baseline(amplitude: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    """Subtract the per-session static baseline from an amplitude matrix.

    Args:
        amplitude: Amplitude array of shape ``(n_samples, n_sub)``.
        baseline: Baseline vector of shape ``(n_sub,)`` from the same node
            and the same session.

    Returns:
        Baseline-subtracted amplitude of shape ``(n_samples, n_sub)``.

    Constraints:
        Subtraction in SHAPE space: both operands are per-packet normalised,
        and what is removed is the empty room's mean shape across
        subcarriers. What remains is the deviation of each packet's shape
        from the empty room, which is where a person's position shows up as
        frequency-selective fading. An empty-room capture comes out near
        zero.

        No bandpass and no dimensionality reduction, so the slowly varying
        part of that shape deviation, the tracking branch's signal, survives.

        A baseline whose mean is far from 1.0 is a level baseline from before
        this pipeline went shape-based, and is rejected rather than silently
        subtracted.
    """
    a = np.asarray(amplitude, dtype=np.float32)
    b = np.asarray(baseline, dtype=np.float32)
    if a.ndim != 2 or b.ndim != 1 or a.shape[1] != b.shape[0]:
        raise ValueError(f"shape mismatch: amplitude {a.shape}, baseline {b.shape}")
    if abs(float(b.mean()) - 1.0) > 0.5:
        raise ValueError(
            f"baseline mean is {float(b.mean()):.3g}, not ~1.0: this is a level baseline, "
            f"not a shape. Baselines must come from estimate_baseline on normalised data."
        )
    return a - b[None, :]


@dataclass(frozen=True)
class CleanedNode:
    """One receiver's cleaned session, with the record cleaning would otherwise hide.

    Attributes:
        amplitude: Clean shape deviations, shape ``(n_samples, n_sub)``.
        grid: Uniform host-referenced times, shape ``(n_samples,)``, on the
            shared lattice so every node of the session aligns by time.
        packet_gap_s: Interval between the source packets bracketing each
            grid sample; see :func:`packet_gap_on_grid`. A window's maximum
            over its span is its ``max_packet_gap`` metadata.
        n_dropped_restart: Stale packets from a previous boot discarded
            ahead of a device-counter restart; see :func:`device_epoch_start`.
    """

    amplitude: np.ndarray
    grid: np.ndarray
    packet_gap_s: np.ndarray
    n_dropped_restart: int


def clean_arrays(
    amplitude: np.ndarray,
    timestamps: np.ndarray,
    fs: float,
    keep: Optional[Sequence[int]] = None,
    baseline: Optional[np.ndarray] = None,
    grid_origin: Optional[float] = 0.0,
    n_dropped_restart: int = 0,
) -> CleanedNode:
    """The shared cleaning chain on an amplitude matrix with anchored times.

    Args:
        amplitude: Raw 128-subcarrier amplitude, shape ``(n_packets, 128)``.
        timestamps: Device-anchored host times, one per packet, from
            :func:`anchor_times`.
        fs: Target uniform sampling rate in Hz.
        keep: Subcarrier indices to retain; project default if ``None``.
        baseline: Per-session baseline SHAPE in the retained subcarrier
            space, or ``None`` to estimate it from this recording.
        grid_origin: See :func:`resample_uniform`; 0.0 is the shared lattice.
        n_dropped_restart: Recorded on the result; see :func:`anchor_times`.

    Returns:
        A :class:`CleanedNode`.

    Constraints:
        The chain, in order: subcarrier selection -> PER-PACKET SHAPE
        NORMALISATION -> outlier removal on the packets -> uniform resample
        -> baseline subtraction in shape space. See :func:`clean_session`
        for why the order is what it is. Whole-file only in the sense that
        the resampler needs the packet times; every step is per packet or
        per sample and nothing here fits a statistic across the file.
    """
    n_sub = len(DEFAULT_KEEP) if keep is None else len(list(keep))
    amp = np.asarray(amplitude, dtype=np.float32)
    ts = np.asarray(timestamps, dtype=np.float64)
    if amp.shape[0] == 0:
        empty = np.zeros(0, dtype=np.float32)
        return CleanedNode(np.zeros((0, n_sub), dtype=np.float32), ts, empty, n_dropped_restart)
    amp = select_subcarriers(amp, keep)
    amp = normalise_shape(amp, keep)
    amp = remove_outliers(amp)
    amp, grid = resample_uniform(amp, ts, fs, grid_origin=grid_origin)
    gaps = packet_gap_on_grid(ts, grid)
    base = estimate_baseline(amp) if baseline is None else np.asarray(baseline, dtype=np.float32)
    amp = subtract_baseline(amp, base)
    return CleanedNode(amp, grid, gaps, n_dropped_restart)


def baseline_shape(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    """The per-session baseline SHAPE from an empty-room capture.

    Args:
        amplitude: Raw 128-subcarrier amplitude of the baseline capture.
        keep: Subcarrier indices to retain; project default if ``None``.

    Returns:
        The median normalised shape, ``(n_sub,)``, ready for
        :func:`clean_arrays`'s ``baseline`` argument.

    Constraints:
        Mask, per-half normalisation, Hampel, median: the same first three
        steps as the chain, so the baseline lives in the space it is
        subtracted from. No resampling, since a median does not care about
        packet timing.
    """
    a = remove_outliers(normalise_shape(select_subcarriers(np.asarray(amplitude, dtype=np.float32), keep), keep))
    return estimate_baseline(a)


def clean_session(
    records: Sequence[CsiRecord],
    fs: float,
    keep: Optional[Sequence[int]] = None,
    baseline: Optional[np.ndarray] = None,
    grid_origin: Optional[float] = 0.0,
) -> CleanedNode:
    """Run the full shared cleaning chain for one node in one session.

    Args:
        records: Validated records for one node in one session.
        fs: Target uniform sampling rate in Hz.
        keep: Subcarrier indices to retain; project default if ``None``.
        baseline: Precomputed per-session baseline SHAPE (per-packet
            normalised, mean ~1.0), already in the retained subcarrier
            space. If ``None``, it is estimated from these records.
        grid_origin: Origin of the uniform grid's lattice. The default 0.0
            puts every node of every session on the absolute host-time
            multiples of ``1/fs``, so fusion windows are cut at the same
            instant on all three receivers. ``None`` reverts to a grid
            anchored at this node's own first packet, for one-node use.

    Returns:
        A :class:`CleanedNode`.

    Constraints:
        The chain is: amplitude -> subcarrier selection -> PER-PACKET SHAPE
        NORMALISATION -> outlier removal -> uniform resample -> baseline
        subtraction in shape space. Normalisation comes straight after
        masking and before everything else, so that AGC gain steps are gone
        before any time-domain step could turn them into edges. Outlier
        removal runs on the packets, BEFORE resampling: a one-packet spike
        that reaches the interpolator survives it as two half-height
        samples the Hampel window then reads as plausible. It contains NO
        bandpass and NO PCA; both belong inside the branches.

        Pass ``baseline`` from the session's empty-room capture wherever one
        exists. Estimating it from the recording itself works, but a session
        in which the participant is present throughout will fold some of
        their presence into the static estimate.
    """
    local = np.array([r.local_timestamp for r in records], dtype=np.int64)
    n_dropped = device_epoch_start(local) if local.size else 0
    amp, ts = records_to_matrix(records)
    return clean_arrays(amp, ts, fs, keep=keep, baseline=baseline, grid_origin=grid_origin, n_dropped_restart=n_dropped)
