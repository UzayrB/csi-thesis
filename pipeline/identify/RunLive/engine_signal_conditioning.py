# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Signal clean-up for identification: a Hampel outlier filter and the energy-percentile contour.

from __future__ import annotations


import numpy as np


# Hampel outlier removal per subcarrier, median window k, replace beyond n_sigma MAD.
def c2_hampel(amp: np.ndarray, k: int = 7, n_sigma: float = 3.0) -> np.ndarray:
    a = np.asarray(amp, float).copy()
    if a.shape[0] < 2 * k + 1:
        return a
    from scipy.ndimage import median_filter
    med = median_filter(a, size=(2 * k + 1, 1), mode="nearest")
    mad = median_filter(np.abs(a - med), size=(2 * k + 1, 1), mode="nearest")
    thr = n_sigma * 1.4826 * mad
    bad = np.abs(a - med) > np.maximum(thr, 1e-12)
    a[bad] = med[bad]
    return a
