"""What the radio says about each state: log P(the person is at this point on this path).

THE RESOLUTION PROBLEM THIS EXISTS TO ATTACK. The frozen emission is
``log P(cell containing position(p, s))`` over 25 cells of one metre. Along a 5 m path that is a
five-step staircase: the CSI cannot express anything finer than a metre along the line however good
the sensing is, because every state inside a cell gets an identical emission. The quantisation floor
is 0.383 m at 25 cells and 0.190 m at 100. If the along-path error is near the floor then the number
being quoted is the grid's resolution, not the radio's.

So three emissions are offered and stage 2 chooses between them on evidence:

    cell25    the frozen one, kept as the control
    cell100   a 0.5 m grid, read at 0.25 m arc-length steps
    gauss     the position head's (x, y) as a Gaussian with a residual covariance fitted on the
              training side, which has no grid and therefore no floor
    product   cell100 and gauss treated as independent evidence and added in log space

THE NULL EMISSION is not a detector. It is a background level the twelve chains have to beat, with
two parameters fitted on the training sessions' own off-path windows. The alternative, a rule on the
motion gate, was measured in stage 0 and cannot work: the gate calls 53.2 percent of transit windows
walking, because during transit the person genuinely is walking. A chain wins a window only when the
radio evidence fits that line's geometry and forward progress better than the background does.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.grid import cell_index

LOG_FLOOR = -30.0


def _log(p: np.ndarray) -> np.ndarray:
    return np.log(np.clip(p, np.exp(LOG_FLOOR), None))


def cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int) -> np.ndarray:
    """``(T, n_cells)`` posterior to ``(T, n_states)`` log emission, by the cell each state sits in.

    Every state inside one cell receives the same value. That is the staircase, and it is the whole
    reason the finer grid and the continuous emission are on trial.
    """
    idx = cell_index(state_xy, n_cells)
    return _log(np.asarray(prob, dtype=float))[:, idx]


def cell_marginal(xy_train: np.ndarray, n_cells: int, alpha: float = 1.0) -> np.ndarray:
    """p(cell) over the TRAINING windows, add-one smoothed so no cell is impossible."""
    idx = cell_index(np.asarray(xy_train, float), n_cells)
    counts = np.bincount(idx, minlength=n_cells).astype(float) + alpha
    return counts / counts.sum()


def scaled_cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int,
                         marginal: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Brief stage 1.5: decode on p(cell | x) / p(cell) rather than the posterior itself.

    The posterior head was trained on windows in which the centre cells are over-represented, since
    eight of the twelve lines cross the centre, so it carries a prior toward the centre that the HMM
    then multiplies into its own. Dividing by the training marginal removes it. In log space that is
    a per-cell constant subtracted from every window, so it changes which STATES compete, which is
    the point, and nothing else.

    ALPHA, amendment D2. The correction was validated BOUNDARIES-GIVEN, where scaling only reorders
    twelve candidates with the span fixed. In the unified decoder the same term also drives entry
    and exit, so it bites far harder, and at alpha 1 it over-corrects: the baseline arm went from
    89 percent of occupancies on diagonals to 33.8 percent edge recall against 1.2 percent diagonal,
    which is the mirror image of the problem rather than a fix. Alpha 0 reproduces the unscaled
    emission exactly and alpha 1 the fully scaled one, so both endpoints are recoverable.
    """
    idx = cell_index(state_xy, n_cells)
    e = _log(np.asarray(prob, dtype=float))[:, idx]
    if alpha == 0.0:
        return e
    return e - float(alpha) * np.log(np.asarray(marginal, float))[idx][None, :]


def fit_residual_covariance(xy_hat: np.ndarray, xy_true: np.ndarray,
                            min_sd: float = 0.15) -> np.ndarray:
    """The position head's 2 x 2 residual covariance, fitted on the TRAINING side.

    In-sample by construction, which understates the spread a little; the brief asks for the
    training side and the consequence is stated rather than silently corrected. The floor on the
    standard deviation stops a pathologically confident covariance from turning the emission into a
    delta function that the decoder can never move away from.
    """
    r = np.asarray(xy_hat, float) - np.asarray(xy_true, float)
    C = np.cov(r.T)
    C = np.atleast_2d(C)
    ev, V = np.linalg.eigh(C)
    ev = np.maximum(ev, min_sd ** 2)
    return (V * ev) @ V.T


def gaussian_emission(xy_hat: np.ndarray, state_xy: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """``(T, 2)`` position estimates to ``(T, n_states)`` log emission, continuous and gridless.

    Computed as a quadratic form rather than by calling a density routine per state, because the
    full matrix is T by n_states by 2 and there are a thousand windows in a recording.
    """
    xy_hat = np.asarray(xy_hat, float)
    P = np.linalg.inv(np.asarray(cov, float))
    d = state_xy[None, :, :] - xy_hat[:, None, :]            # (T, S, 2)
    q = np.einsum("tsi,ij,tsj->ts", d, P, d)
    return -0.5 * q - 0.5 * float(np.log(np.linalg.det(2 * np.pi * cov)))


def build_emission(kind: str, state_xy: np.ndarray, *, prob25: Optional[np.ndarray] = None,
                   prob100: Optional[np.ndarray] = None, xy_hat: Optional[np.ndarray] = None,
                   cov: Optional[np.ndarray] = None) -> np.ndarray:
    """One of the four emissions, as ``(T, n_states)`` in log space."""
    if kind == "cell25":
        return cell_emission(prob25, state_xy, 25)
    if kind == "cell100":
        return cell_emission(prob100, state_xy, 100)
    if kind == "gauss":
        return gaussian_emission(xy_hat, state_xy, cov)
    if kind == "product":
        return cell_emission(prob100, state_xy, 100) + gaussian_emission(xy_hat, state_xy, cov)
    raise ValueError(f"unknown emission {kind!r}")


# --------------------------------------------------------------------------- the null state


class NullEmission:
    """The background level the twelve chains must beat.

    ``log b(t) = base + gate_weight * [the gate reads this window as not walking]``

    Two parameters, fitted on the training sessions' own off-path windows against their known pass
    boundaries, which is the only labelled information about "not on a path" that exists without
    reading a free-movement recording. The gate term is worth having because the gate is decisive
    for the stationary case (8 percent of dwell windows read as walking against 97 percent of
    on-path windows) even though it is useless for transit.

    The fit is one-dimensional in ``base`` for each candidate ``gate_weight``: raising the base makes
    the null state win more windows. It is chosen to maximise the balanced accuracy of the
    resulting on-path against off-path decision on the TRAINING side, so nothing about the test
    session touches it.
    """

    def __init__(self, base: float = 0.0, gate_weight: float = 0.0, motion_theta: float = 0.431):
        self.base = float(base)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)

    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self.base + self.gate_weight * still

    def to_dict(self) -> dict:
        return {"base": self.base, "gate_weight": self.gate_weight,
                "motion_theta": self.motion_theta}

    @classmethod
    def fit(cls, path_emissions, gate_energies, on_path_masks, motion_theta: float = 0.431,
            gate_weights=(0.0, 1.0, 2.0, 4.0), n_base: int = 81) -> "NullEmission":
        """Choose base and gate weight on the training side by balanced accuracy.

        ``path_emissions`` is a list of ``(T, n_states)`` log-emission blocks, one per training
        recording; ``on_path_masks`` says which windows were really on a taped line. The decision
        modelled here is the per-window one, ``max_state emission > null``, which is the comparison
        the decoder actually makes before any transition structure is applied. Fitting it without
        the transitions keeps the parameter honest: it is a level, not a segmentation.
        """
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


class AdaptiveNullEmission:
    """A null level anchored to the CURRENT recording's own emission scale, not to the training days.

    WHY THIS EXISTS. The fixed level does not transfer across days. Measured: 83 percent precision
    and 63 recall on the training recordings against 71 and 26 on a session the model has not seen,
    and only half the passes found. The level is a threshold on how strong the best chain's evidence
    is, and that strength shifts between days for the same reason path identification does.

    THE PARAMETRISATION MATTERS and the first attempt got it wrong. Setting the level AT a quantile
    of the recording's peaks never enters a chain at all: entering costs log((1 - null_self) / 12),
    about 4.8 nats, so a level sitting inside the peak distribution is never beaten. What is learned
    is therefore an OFFSET below a reference quantile of that distribution, which is the quantity
    that has to transfer, while the reference itself is recomputed per recording.

        level = quantile(this recording's emission peaks, q) + offset + gate_weight * [still]

    Only q, the offset and the gate weight are learned, all on the training side. The reference is
    calibrated per recording from emissions the decoder has already computed, reading no labels and
    no truth, which is something a live system can do to its own incoming stream. It is calibration,
    not fitting, and it is reported as its own arm rather than folded into the headline.
    """

    def __init__(self, quantile: float = 0.5, offset: float = 0.0, gate_weight: float = 0.0,
                 motion_theta: float = 0.431):
        self.quantile = float(np.clip(quantile, 0.01, 0.999))
        self.offset = float(offset)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)
        self._ref = None

    def calibrate(self, path_emission: np.ndarray) -> "AdaptiveNullEmission":
        """Set the reference from this recording's own peaks. Reads no labels and no truth."""
        self._ref = float(np.quantile(np.asarray(path_emission).max(1), self.quantile))
        return self

    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        if self._ref is None:
            raise RuntimeError("calibrate() must be called on the recording before decoding it")
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self._ref + self.offset + self.gate_weight * still

    def to_dict(self) -> dict:
        return {"kind": "adaptive", "quantile": self.quantile, "offset": self.offset,
                "gate_weight": self.gate_weight, "motion_theta": self.motion_theta,
                "reference_of_last_recording": self._ref}

    @classmethod
    def fit(cls, path_emissions, gate_energies, on_path_masks, grace_masks, states, log_T,
            quantiles=(0.25, 0.5, 0.75), offsets=None, gate_weights=(0.0, 2.0, 4.0)) -> tuple:
        """Choose the quantile, offset and gate weight on the TRAINING recordings, by F1.

        Each candidate is calibrated per recording exactly as it would be at test time, so what is
        selected is the RULE and never a level.
        """
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


def stack_with_null(path_emis: np.ndarray, null_emis: np.ndarray) -> np.ndarray:
    """``(T, n_states)`` plus ``(T,)`` to ``(T, n_states + 1)``, the null state last."""
    return np.concatenate([path_emis, np.asarray(null_emis, float)[:, None]], axis=1)
