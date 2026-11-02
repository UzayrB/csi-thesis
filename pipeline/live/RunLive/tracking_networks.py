# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Two small helpers for the tracking networks: a window as the networks expect it, and its features.

from __future__ import annotations

import numpy as np

# A window as the networks expect it, and its features.
class LivePool:

    # The window as the offline tree stores it: float16, then float32.
    @staticmethod
    def as_stored(window: np.ndarray) -> np.ndarray:
        return np.asarray(window).astype(np.float16).astype(np.float32)

    # Features.tracking_features_links on each window as stored, exactly as the feature cache.
    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        from pipeline.constrained.RunLive.network_inputs import tracking_features_links
        from pipeline.constrained.RunLive.shared_settings import FS
        return np.stack([tracking_features_links(LivePool.as_stored(w), FS) for w in windows]).astype(np.float32)
