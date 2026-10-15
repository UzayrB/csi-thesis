"""Walking gate: 0.3 to 2 Hz band energy used to LABEL windows.

The gate answers two questions per window, and they are different kinds of
question. Was there walking? One global threshold, :data:`MOTION_THETA`,
placed on session 01 and transferred to session 02 untouched (Checkpoint 4,
11 September 2026). Was there anyone at all? A per-session rule applied to
the session's own fresh baseline, never a constant.

PROJECT RULES ENCODED HERE
--------------------------
* The gate LABELS windows. It does NOT route data. All three branches run
  on every window; gate labels are metadata for evaluation and analysis,
  never a switch in the data path. A weak presence decision therefore
  costs nothing offline.
* The presence threshold is computed from THAT session's own baseline. It
  is a required argument with no default, so a missing baseline fails
  loudly instead of falling back to a constant. The empty room's resting
  level moved by a factor of four within one morning (the aircon coming on
  at 11:44 on 10 September) and a day-1 constant applied to day 2 read half
  of day 2's empty windows as occupied.
* A baseline older than :data:`MAX_BASELINE_AGE_S` when the recording
  started is flagged, never silently used.
* Every function here takes one window. Whole-file passes live in
  ``tools/calibrate_gate.py`` and ``tools/apply_gate.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

MOTION_BAND_HZ: tuple[float, float] = (0.3, 2.0)

#: Standing below, walking above. Placed on session 01 by balanced accuracy
#: (9.8 percent of standing read as walking, 2.0 percent of walking read as
#: standing) and transferred to session 02 untouched: 15.3 and 0.1 percent.
#: Accepted at Checkpoint 4 without nudging: a walking window read as
#: standing is a lost identification sample, a standing window read as
#: walking is a mislabelled one the branch can still recover from, so the
#: asymmetry stays where it is. The transfer figures are a result for the
#: write-up, not a diagnostic.
MOTION_THETA: float = 0.431

#: Presence rule: theta_presence = PRESENCE_K times the PRESENCE_QUANTILE of
#: the band energies of the session's own baseline windows. Both searched on
#: session 01; balanced accuracy 77 percent on day 1 and 69 percent on day 2,
#: within a point of the oracle ceiling on both, so the rule is at the limit
#: of what this statistic can do. Accepted as weak and not tuned further.
PRESENCE_K: float = 1.04
PRESENCE_QUANTILE: float = 0.75

#: A baseline older than this at the start of the recording is flagged.
MAX_BASELINE_AGE_S: float = 3600.0


@dataclass(frozen=True)
class GateLabel:
    """The gate's verdict on one window.

    Attributes:
        label: ``"empty"``, ``"standing"`` or ``"walking"``.
        band_energy: 0.3 to 2 Hz band power, mean over subcarriers and links.
        presence_theta: The per-session presence threshold that was applied.
        motion_theta: The global motion threshold that was applied.
    """

    label: str
    band_energy: float
    presence_theta: float
    motion_theta: float


def band_energy(window: np.ndarray, fs: float, band: tuple[float, float] = MOTION_BAND_HZ) -> float:
    """0.3 to 2 Hz band power of one window, mean over subcarriers and links.

    Args:
        window: Clean amplitude, ``(n_links, n_samples, n_sub)`` or a single
            link ``(n_samples, n_sub)``.
        fs: Sampling rate of the uniform grid in Hz.
        band: Band to integrate, in Hz.

    Returns:
        The band power, a scalar. FFT along time per subcarrier after
        removing the window's own mean, so a residual offset never enters.
    """
    x = np.asarray(window, dtype=np.float64)
    if x.ndim == 2:
        x = x[None]
    if x.ndim != 3:
        raise ValueError(f"expected (links, samples, sub) or (samples, sub), got {x.shape}")
    x = x - x.mean(axis=1, keepdims=True)
    f = np.fft.rfftfreq(x.shape[1], 1 / fs)
    P = (np.abs(np.fft.rfft(x, axis=1)) ** 2) / x.shape[1]
    sel = (f >= band[0]) & (f <= band[1])
    return float(P[:, sel, :].sum(axis=1).mean())


def presence_threshold(baseline_band_energies: np.ndarray) -> float:
    """The per-session presence threshold from that session's own baseline.

    Args:
        baseline_band_energies: :func:`band_energy` of every window of the
            session's empty-room baseline, cut and cleaned against its own
            shape. Required. There is no default and no fallback.

    Returns:
        ``PRESENCE_K * quantile(energies, PRESENCE_QUANTILE)``.
    """
    e = np.asarray(baseline_band_energies, dtype=np.float64)
    if e.ndim != 1 or e.size < 5:
        raise ValueError("the presence threshold needs the band energies of at least five baseline windows")
    return float(PRESENCE_K * np.quantile(e, PRESENCE_QUANTILE))


def baseline_is_fresh(recording_start: float, baseline_start: float, max_age_s: float = MAX_BASELINE_AGE_S) -> bool:
    """Whether a baseline was recorded recently enough to threshold this recording."""
    age = recording_start - baseline_start
    if age < 0:
        raise ValueError(f"baseline starts {-age:.0f} s AFTER the recording it is meant to precede")
    return age <= max_age_s


def label_window(window: np.ndarray, fs: float, presence_theta: float, motion_theta: float = MOTION_THETA) -> GateLabel:
    """Label one window empty, standing or walking.

    Args:
        window: Clean amplitude, ``(n_links, n_samples, n_sub)``.
        fs: Sampling rate in Hz.
        presence_theta: From :func:`presence_threshold` on THIS session's
            baseline. No default: a caller without a fresh baseline cannot
            call this.
        motion_theta: The global motion threshold.

    Returns:
        The :class:`GateLabel`. Labels only; nothing is routed.
    """
    if not np.isfinite(presence_theta) or presence_theta <= 0:
        raise ValueError(f"presence_theta must be a positive number from this session's baseline, got {presence_theta!r}")
    e = band_energy(window, fs)
    if e >= motion_theta:
        label = "walking"
    elif e >= presence_theta:
        label = "standing"
    else:
        label = "empty"
    return GateLabel(label=label, band_energy=e, presence_theta=float(presence_theta), motion_theta=float(motion_theta))
