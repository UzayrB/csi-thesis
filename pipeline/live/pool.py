# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The SHIPPED five-head pool, computed one window at a time.

from __future__ import annotations

import os

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Function abs.
def _abs(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(REPO_ROOT, p)


# The five heads for one tag, applied to single windows.
class LivePool:

    # Sets up the object.
    def __init__(self, tag: str, tr_s, te_s, st, kind: str, alpha: float, within: bool = False):
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.common import E_POST
        from pipeline.constrained.emissions import cell_marginal
        from pipeline.constrained.lattice import g100_tree, half_art_dir, one_s_trees
        self.tag, self.st, self.kind, self.alpha = tag, st, kind, alpha
        heads = [("g25_half", 25, [os.path.join(half_art_dir(), "models", f"{tag}_g25_e{E_POST}_s0_link{li}.pt")
                                   for li in range(3)])]
        for seed, tree in sorted(one_s_trees().items()):
            if os.path.isdir(os.path.join(_abs(tree), "posteriors")):
                heads.append((f"g25_1s_seed{seed}", 25,
                              [os.path.join(_abs(tree), "models", f"{tag}_g25_e{E_POST}_s{seed}_link{li}.pt")
                               for li in range(3)]))
        heads.append(("g100", 100, [os.path.join(_abs(g100_tree()), "models", f"{tag}_g100_e{E_POST}_s0_link{li}.pt")
                                    for li in range(3)]))
        missing = [p for _n, _c, ps in heads for p in ps if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: head weights missing for tag {tag}: {missing[:3]}")
        self.heads = [(name, cells, [_load(p) for p in paths]) for name, cells, paths in heads]
        self.marg = None
        if kind == "scaled":
            from pipeline.constrained.dataset import sides
            self.marg = cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)

    # Function head names.
    @property
    def head_names(self) -> list:
        return [n for n, _c, _m in self.heads]

    # The window as the offline tree stores it: float16, then float32.
    @staticmethod
    def as_stored(window: np.ndarray) -> np.ndarray:
        return np.asarray(window).astype(np.float16).astype(np.float32)

    # {head: (n, cells) float32 fused posterior} for a block of windows' features.
    def head_probs(self, feats: np.ndarray, rssi: np.ndarray) -> dict:
        import torch
        from pipeline.constrained.nets import infer_logits, stack_link
        out = {}
        for name, _cells, models in self.heads:
            per_link = []
            for li, (m, mu, sd) in enumerate(models):
                Xb = stack_link(feats[:, [li]], None if rssi is None else rssi[:, [li]])
                Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
                lg = infer_logits(m, Xb, 128)
                per_link.append(torch.softmax(torch.from_numpy(lg), dim=1).numpy().astype(np.float64))
            p = np.mean(np.stack(per_link), axis=0)
            out[name] = (p / np.maximum(p.sum(1, keepdims=True), 1e-12)).astype(np.float32)
        return out

    # The pooled log emission from each head's stored-precision posterior.
    def emissions_from_probs(self, probs: dict) -> np.ndarray:
        from pipeline.constrained.emissions import cell_emission, scaled_cell_emission
        from pipeline.constrained.g2_multihead import pool
        from pipeline.constrained.g3_final import g100_to_25
        parts = []
        for name, cells, _m in self.heads:
            prob = probs[name].astype(float)
            if cells == 100:
                prob = g100_to_25(prob)
                prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
            parts.append(cell_emission(prob, self.st.xy, 25) if self.marg is None
                         else scaled_cell_emission(prob, self.st.xy, 25, self.marg, alpha=self.alpha))
        return pool(parts)

    # Features.tracking_features_links on each window as stored, exactly as the feature cache.
    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        from pipeline.constrained.features import tracking_features_links
        from pipeline.constrained.recordings import FS
        return np.stack([tracking_features_links(LivePool.as_stored(w), FS) for w in windows]).astype(np.float32)

    # Function gate energy.
    def gate_energy(self, window: np.ndarray) -> float:
        from pipeline.constrained.gate import band_energy
        from pipeline.constrained.recordings import FS
        return float(band_energy(self.as_stored(window), FS))

    # ONE completed window -> (pooled log emission row, gate energy).
    def window(self, window: np.ndarray, rssi: np.ndarray) -> tuple:
        feats = self.features(np.asarray(window)[None])
        e = self.emissions_from_probs(self.head_probs(feats, np.asarray(rssi, np.float32)[None]))
        return e[0], self.gate_energy(window)


# The DISPLAY head (DISP_END), one window at a time: its posterior as s2a_dispend stores it, and its...
class LiveEndHead:

    # Sets up the object.
    def __init__(self, tag: str, tr_s, st, alpha: float):
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.emissions import cell_marginal
        from pipeline.constrained.s2a_dispend import end_labelled_windows, model_path
        paths = [model_path(tag, li) for li in range(3)]
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: the display head's weights are missing for tag {tag}: {missing}")
        self.models = [_load(p) for p in paths]
        self.st, self.alpha = st, alpha
        tr, _cov = end_labelled_windows(tr_s, with_features=False, include_edge=False)
        self.marg = cell_marginal(tr.xy, 25)

    # (n, 25) emission rows for a block of windows' features.
    def emission(self, feats: np.ndarray, rssi: np.ndarray) -> np.ndarray:
        import torch
        from pipeline.constrained.emissions import scaled_cell_emission
        from pipeline.constrained.nets import infer_logits, stack_link
        per_link = []
        for li, (m, mu, sd) in enumerate(self.models):
            Xb = stack_link(feats[:, [li]], None if rssi is None else rssi[:, [li]])
            Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
            lg = infer_logits(m, Xb, 128)
            per_link.append(torch.softmax(torch.from_numpy(lg), dim=1).numpy().astype(np.float64))
        p = np.mean(np.stack(per_link), axis=0)
        prob = (p / np.maximum(p.sum(1, keepdims=True), 1e-12)).astype(np.float32)
        return scaled_cell_emission(prob.astype(float), self.st.xy, 25, self.marg, alpha=self.alpha)
