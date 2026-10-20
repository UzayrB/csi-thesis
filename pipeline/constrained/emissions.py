# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: What the radio says about each state: log P(the person is at this point on this path).

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.grid import cell_index

LOG_FLOOR = -30.0


# Function log.
def _log(p: np.ndarray) -> np.ndarray:
    return np.log(np.clip(p, np.exp(LOG_FLOOR), None))


# (T, n_cells) posterior to (T, n_states) log emission, by the cell each state sits in.
def cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    return _log(np.asarray(prob, dtype=float))[:, idx]


# P(cell) over the TRAINING windows, add-one smoothed so no cell is impossible.
def cell_marginal(xy_train: np.ndarray, n_cells: int, alpha: float = 1.0) -> np.ndarray:
    idx = cell_index(np.asarray(xy_train, float), n_cells)
    counts = np.bincount(idx, minlength=n_cells).astype(float) + alpha
    return counts / counts.sum()


# Decode on p(cell | x) / p(cell) rather than the posterior itself.
def scaled_cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int,
                         marginal: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    e = _log(np.asarray(prob, dtype=float))[:, idx]
    if alpha == 0.0:
        return e
    return e - float(alpha) * np.log(np.asarray(marginal, float))[idx][None, :]


# The position head's 2 x 2 residual covariance, fitted on the TRAINING side.
def fit_residual_covariance(xy_hat: np.ndarray, xy_true: np.ndarray,
                            min_sd: float = 0.15) -> np.ndarray:
    r = np.asarray(xy_hat, float) - np.asarray(xy_true, float)
    C = np.cov(r.T)
    C = np.atleast_2d(C)
    ev, V = np.linalg.eigh(C)
    ev = np.maximum(ev, min_sd ** 2)
    return (V * ev) @ V.T


# (T, 2) position estimates to (T, n_states) log emission, continuous and gridless.
def gaussian_emission(xy_hat: np.ndarray, state_xy: np.ndarray, cov: np.ndarray) -> np.ndarray:
    xy_hat = np.asarray(xy_hat, float)
    P = np.linalg.inv(np.asarray(cov, float))
    d = state_xy[None, :, :] - xy_hat[:, None, :]
    q = np.einsum("tsi,ij,tsj->ts", d, P, d)
    return -0.5 * q - 0.5 * float(np.log(np.linalg.det(2 * np.pi * cov)))


# One of the four emissions, as (T, n_states) in log space.
def build_emission(kind: str, state_xy: np.ndarray, *, prob25: Optional[np.ndarray] = None,
                   prob100: Optional[np.ndarray] = None, xy_hat: Optional[np.ndarray] = None,
                   cov: Optional[np.ndarray] = None) -> np.ndarray:
    if kind == "cell25":
        return cell_emission(prob25, state_xy, 25)
    if kind == "cell100":
        return cell_emission(prob100, state_xy, 100)
    if kind == "gauss":
        return gaussian_emission(xy_hat, state_xy, cov)
    if kind == "product":
        return cell_emission(prob100, state_xy, 100) + gaussian_emission(xy_hat, state_xy, cov)
    raise ValueError(f"unknown emission {kind!r}")




# The background level the twelve chains must beat.
class NullEmission:

    # Sets up the object.
    def __init__(self, base: float = 0.0, gate_weight: float = 0.0, motion_theta: float = 0.431):
        self.base = float(base)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)

    # Calls the object.
    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self.base + self.gate_weight * still

    # Function to dict.
    def to_dict(self) -> dict:
        return {"base": self.base, "gate_weight": self.gate_weight,
                "motion_theta": self.motion_theta}

    # Choose base and gate weight on the training side by balanced accuracy.
    @classmethod
    def fit(cls, path_emissions, gate_energies, on_path_masks, motion_theta: float = 0.431,
            gate_weights=(0.0, 1.0, 2.0, 4.0), n_base: int = 81) -> "NullEmission":
        best = (None, -1.0)
        peaks = np.concatenate([e.max(1) for e in path_emissions])
        still = np.concatenate([(np.asarray(g, float) < motion_theta).astype(float)
                                for g in gate_energies])
        on = np.concatenate([np.asarray(m, bool) for m in on_path_masks])
        if on.sum() == 0 or (~on).sum() == 0:
            return cls(base=float(np.median(peaks)), gate_weight=0.0, motion_theta=motion_theta)
        lo, hi = float(np.percentile(peaks, 1)), float(np.percentile(peaks, 99))
        for gw in gate_weights:
            for base in np.linspace(lo, hi, n_base):
                null = base + gw * still
                pred_on = peaks > null
                tpr = float(pred_on[on].mean())
                tnr = float((~pred_on[~on]).mean())
                bal = 0.5 * (tpr + tnr)
                if bal > best[1]:
                    best = (cls(base=float(base), gate_weight=float(gw),
                                motion_theta=motion_theta), bal)
        return best[0]


# A null level anchored to the CURRENT recording's own emission scale, not to the training days.
class AdaptiveNullEmission:

    # Sets up the object.
    def __init__(self, quantile: float = 0.5, offset: float = 0.0, gate_weight: float = 0.0,
                 motion_theta: float = 0.431):
        self.quantile = float(np.clip(quantile, 0.01, 0.999))
        self.offset = float(offset)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)
        self._ref = None

    # Set the reference from this recording's own peaks.
    def calibrate(self, path_emission: np.ndarray) -> "AdaptiveNullEmission":
        self._ref = float(np.quantile(np.asarray(path_emission).max(1), self.quantile))
        return self

    # Calls the object.
    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        if self._ref is None:
            raise RuntimeError("calibrate() must be called on the recording before decoding it")
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self._ref + self.offset + self.gate_weight * still

    # Function to dict.
    def to_dict(self) -> dict:
        return {"kind": "adaptive", "quantile": self.quantile, "offset": self.offset,
                "gate_weight": self.gate_weight, "motion_theta": self.motion_theta,
                "reference_of_last_recording": self._ref}

    # Choose the quantile, offset and gate weight on the TRAINING recordings, by F1.
    @classmethod
    def fit(cls, path_emissions, gate_energies, on_path_masks, grace_masks, states, log_T,
            quantiles=(0.25, 0.5, 0.75), offsets=None, gate_weights=(0.0, 2.0, 4.0)) -> tuple:
        from pipeline.constrained.decoder import decoded_paths, viterbi
        if offsets is None:
            offsets = np.linspace(-8.0, 2.0, 21)
        best = (None, -1.0, None)
        for q in quantiles:
            refs = [float(np.quantile(np.asarray(e).max(1), q)) for e in path_emissions]
            for off in offsets:
                for gw in gate_weights:
                    tp = fp = fn = 0
                    for e, g, on, grace, ref in zip(path_emissions, gate_energies, on_path_masks,
                                                    grace_masks, refs):
                        ne = cls(quantile=q, offset=float(off), gate_weight=gw)
                        ne._ref = ref
                        pred = decoded_paths(viterbi(stack_with_null(e, ne(g)), log_T), states) != ""
                        sc = ~np.asarray(grace, bool)
                        on_ = np.asarray(on, bool)
                        tp += int((pred & on_ & sc).sum())
                        fp += int((pred & ~on_ & sc).sum())
                        fn += int((~pred & on_ & sc).sum())
                    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
                    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
                    if f1 > best[1]:
                        best = (cls(quantile=q, offset=float(off), gate_weight=gw), f1,
                                {"precision_pct": round(100 * prec, 1),
                                 "recall_pct": round(100 * rec, 1)})
        if best[0] is None:
            return cls(), {"fitted": False, "reason": "no candidate scored"}
        return best[0], {"fitted": True, "f1": round(best[1], 4), "counts": best[2],
                         "selected_on": "F1 over the on-path class on the training recordings, each "
                                        "calibrated per recording as it would be at test time",
                         **best[0].to_dict()}


# (T, n_states) plus (T,) to (T, n_states + 1), the null state last.
def stack_with_null(path_emis: np.ndarray, null_emis: np.ndarray) -> np.ndarray:
    return np.concatenate([path_emis, np.asarray(null_emis, float)[:, None]], axis=1)
