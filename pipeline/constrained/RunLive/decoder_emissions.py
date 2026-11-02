# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Turns the networks' outputs into what the decoder needs: how likely the person is at each point on each line.

from __future__ import annotations


import numpy as np

from pipeline.constrained.RunLive.cell_grid import cell_index

LOG_FLOOR = -30.0


# Function log.
def _log(p: np.ndarray) -> np.ndarray:
    return np.log(np.clip(p, np.exp(LOG_FLOOR), None))


# (T, n_cells) posterior to (T, n_states) log emission, by the cell each state sits in.
def cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    return _log(np.asarray(prob, dtype=float))[:, idx]


# Brief stage 1.5: decode on p(cell | x) / p(cell) rather than the posterior itself.
def scaled_cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int,
                         marginal: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    e = _log(np.asarray(prob, dtype=float))[:, idx]
    if alpha == 0.0:
        return e
    return e - float(alpha) * np.log(np.asarray(marginal, float))[idx][None, :]




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
        from pipeline.constrained.RunLive.decoder_lines import decoded_paths, viterbi
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


# Equal-weight log-opinion pool of N emissions, renormalised per window.
def pool(emissions):
    n = min(len(e) for e in emissions)
    m = np.mean([np.asarray(e[:n], float) for e in emissions], axis=0)
    return m - m.max(axis=1, keepdims=True)


# A 10 by 10 grid summed into 5 by 5: each 25-cell is exactly four g100 cells.
def g100_to_25(prob100):
    p = np.asarray(prob100, float)
    n = p.shape[0]
    g = p.reshape(n, 10, 10)
    return g.reshape(n, 5, 2, 5, 2).sum(axis=(2, 4)).reshape(n, 25)
