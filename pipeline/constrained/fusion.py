"""HOW THE THREE LINK POSTERIORS OF EACH HEAD ARE FUSED. One definition, used by every reader.

Shipped until 2026-09-23d: the arithmetic mean, renormalised (`nets.posterior_of`), which is the
fused `prob` every posterior file stores. The alternative measured in batch 23c (`z3a_linkprod`,
`reports/FINDING_linkfusion_2026-09-23.md`) is the renormalised PRODUCT, blended in log space:

    log p_w = (1 - w) log p_mean + w log p_product,  renormalised.

`w = 0` returns the STORED fused posterior untouched, so a reader passed `fusion_w = 0` is
bit-identical to what it was before this module existed. Numpy only.
"""

from __future__ import annotations

import numpy as np

TINY = 1e-300


def fuse_links(per_link, stored, w: float):
    """The blend. `per_link` is (3, n, cells); `stored` is the file's fused mean, (n, cells)."""
    if w == 0.0:
        return stored
    P = np.maximum(np.asarray(per_link, float), TINY)
    lp = np.log(P).sum(axis=0)
    lp = lp - lp.max(axis=1, keepdims=True)
    prod = np.exp(lp)
    prod /= prod.sum(axis=1, keepdims=True)
    lm = np.log(np.maximum(np.asarray(stored, float), TINY))
    lw = (1.0 - w) * lm + w * np.log(np.maximum(prod, TINY))
    lw = lw - lw.max(axis=1, keepdims=True)
    q = np.exp(lw)
    return q / q.sum(axis=1, keepdims=True)


def fused_prob(block: dict, w: float = 0.0):
    """A posterior-file block's `prob`, fused at weight w. w = 0 is the stored array, unchanged."""
    if not w:
        return block["prob"]
    if "per_link" not in block:
        raise AssertionError("product fusion needs the per-link posteriors, which this file lacks")
    return fuse_links(block["per_link"], block["prob"], float(w)).astype(np.float64)
