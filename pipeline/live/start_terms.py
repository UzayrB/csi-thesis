# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shipped committed decision's start terms, A2 plus a_veto_1.0, computed for one pass at its press.

from __future__ import annotations

import os

import numpy as np


# Class Live Start Terms.
class LiveStartTerms:
    # Sets up the object.
    def __init__(self, train_sessions, reader_tag: str, st):
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.preprocessing import StandardScaler

        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.common import ART_DIR, E_REG
        from pipeline.constrained.q3_startclf import collect
        from pipeline.constrained.t2_embed import load_heads
        from pipeline.constrained.u1_adapt import session_rows
        from pipeline.constrained.u2_useit import ADAPT_MODE
        self.st, self.reader_tag = st, reader_tag
        Xa, ya, _k, _w = collect(tuple(train_sessions), st)
        self.a2_sc = StandardScaler().fit(Xa)
        self.a2 = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(self.a2_sc.transform(Xa), ya)
        Xv, yv, *_rest = session_rows(tuple(train_sessions), st, ADAPT_MODE, {})
        self.v_sc = StandardScaler().fit(Xv)
        self.reader = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=None).fit(
            self.v_sc.transform(Xv), yv)
        paths = [os.path.join(ART_DIR, "models", f"{reader_tag}_pos2_e{E_REG}_s0_link{li}.pt") for li in range(3)]
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: the reader tag {reader_tag}'s position heads are missing: {missing}")
        self.pos = [_load(p) for p in paths]
        self.g25 = load_heads(reader_tag)
        if self.g25 is None:
            raise SystemExit(f"REFUSED: the reader tag {reader_tag}'s g25 heads are missing")
        self.heads = self.g25
        self.adaptation = {"adapted": False, "n_calibration_windows": 0}

    # AdaBN on the recording's idle windows before its first press; unadapted below 20.
    def adapt(self, cal_feats: np.ndarray, cal_rssi: np.ndarray) -> dict:
        from pipeline.constrained.u1_adapt import adapt_batchnorm
        n = int(len(cal_feats))
        self.heads = adapt_batchnorm(self.g25, cal_feats.astype(np.float32), cal_rssi.astype(np.float32)) \
            if n >= 20 else self.g25
        self.adaptation = {"adapted": bool(n >= 20), "n_calibration_windows": n}
        return self.adaptation

    # The A2 feature row from the windows given (starts t0), selected exactly as offline.
    def a2_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        from pipeline.constrained.nets import position_of
        from pipeline.constrained.q3_startclf import features
        xh, xl = position_of(self.pos, feats, rssi)
        blk = {"xy_hat": xh.astype(np.float32), "xy_hat_link": xl.astype(np.float32)}
        return features(blk, np.asarray(t0, float), press)

    # Function veto row.
    def veto_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        from pipeline.constrained.t1_region import prepress_indices
        from pipeline.constrained.u1_adapt import embed_rows
        sel = prepress_indices(np.asarray(t0, float), press)
        if len(sel) < 2:
            return None
        e = embed_rows(self.heads, feats[sel], rssi[sel])
        f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
        return np.where(np.isfinite(f), f, 0.0)

    # {line: log term} for one pass: A2 (weight 0.5) plus the veto (-3 nats below 0.01).
    def terms(self, a2_row, veto_row) -> dict:
        from pipeline.constrained.t0_oracle import line_regions
        from pipeline.constrained.u2_useit import VETO_NATS
        from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
        lr = line_regions(self.st)
        out = {}
        if a2_row is not None:
            P = self.a2.predict_proba(self.a2_sc.transform(a2_row[None]))[0]
            classes = list(self.a2.classes_)
            lp = np.log(np.clip(P, 1e-9, 1.0))
            base = float(np.mean(lp))
            out = {nm: A2_WEIGHT * float(lp[classes.index(r)] - base) for nm, r in lr.items() if r in classes}
        if veto_row is not None:
            p = self.reader.predict_proba(self.v_sc.transform(veto_row[None]))[0]
            ci = {c: i for i, c in enumerate(self.reader.classes_)}
            for nm, r in lr.items():
                v = -VETO_W * VETO_NATS if (r in ci and p[ci[r]] < VETO_THR) else 0.0
                out[nm] = out.get(nm, 0.0) + v
        return out
