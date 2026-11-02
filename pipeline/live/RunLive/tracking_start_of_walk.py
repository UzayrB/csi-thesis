# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: When you press SPACE: works out which start the walker is standing at, from the windows around the press.

from __future__ import annotations


import numpy as np


# Class Live Start Terms.
class LiveStartTerms:
    # Main.py replaces this while it builds the start terms from the frozen readers (readers.pkl).
    def __init__(self, train_sessions, reader_tag, st):
        raise SystemExit("REFUSED: start tracking through main.py, which builds the frozen start-of-walk readers")

    # AdaBN on the recording's idle windows before its first press; unadapted below 20.
    def adapt(self, cal_feats: np.ndarray, cal_rssi: np.ndarray) -> dict:
        from pipeline.constrained.RunLive.start_veto import adapt_batchnorm
        n = int(len(cal_feats))
        self.heads = adapt_batchnorm(self.g25, cal_feats.astype(np.float32), cal_rssi.astype(np.float32)) \
            if n >= 20 else self.g25
        self.adaptation = {"adapted": bool(n >= 20), "n_calibration_windows": n}
        return self.adaptation

    # The A2 feature row from the windows given (starts t0), selected exactly as offline.
    def a2_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        from pipeline.constrained.RunLive.network_build import position_of
        from pipeline.constrained.RunLive.start_veto import features
        xh, xl = position_of(self.pos, feats, rssi)
        blk = {"xy_hat": xh.astype(np.float32), "xy_hat_link": xl.astype(np.float32)}
        return features(blk, np.asarray(t0, float), press)

    # Function veto row.
    def veto_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        from pipeline.constrained.RunLive.start_veto import prepress_indices
        from pipeline.constrained.RunLive.start_veto import embed_rows
        sel = prepress_indices(np.asarray(t0, float), press)
        if len(sel) < 2:
            return None
        e = embed_rows(self.heads, feats[sel], rssi[sel])
        f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
        return np.where(np.isfinite(f), f, 0.0)
