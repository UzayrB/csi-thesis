"""Train one cell-classifier network of the stride ablation (PLAN.md). Run by run.py, which sets the environment.

The shipped training function (`pd_cells.do_train_d2`) is called unchanged on a rotation cell of the final recipe
(`d4c_fuse_<rotation>`: shared `fuse` encoder, augmentation, relative RSSI, 24 epochs). Only these differ, in this
process only: the head's training stride, cell count and seed (one `g` job, no position job, since the decode never
reads the position head), and the output folders, which point into this ablation's run folder.
"""

from __future__ import annotations

import argparse
import os
import sys

J = os.path.join


def _nocopy_class():
    import numpy as np

    class NoCopy(np.ndarray):
        """Same-type astype returns a view, not a copy (memory only; values unchanged)."""

        def astype(self, dtype, *args, **kw):
            base = np.asarray(self).view(np.ndarray)
            return base if np.dtype(dtype) == base.dtype else base.astype(dtype, *args, **kw)

    return NoCopy


NoCopy = _nocopy_class()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, help="the rotation cell, d4c_fuse_<rotation>")
    ap.add_argument("--stride", choices=("05", "10"), required=True)
    ap.add_argument("--cells", type=int, choices=(25, 100), required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True, help="this network's own folder")
    a = ap.parse_args()

    from pipeline.constrained import pd_cells as P
    c = dict(P.cfg(a.cell))
    assert c["opts"].get("aug") and c["opts"].get("rrel") and P.D2[a.cell].get("arch") == "fuse", c
    assert c["test"] not in ("03", "B2") and not (set(c["train"]) & {"03", "B2"}), c
    if c["opts"].get("rrel"):
        P.install_rrel()  # before the data modules are imported, as the shipped train command does

    head = "net"
    P.HEADS[head] = (a.stride, [("g", a.cells, a.seed)])

    # Memory only, as in the dwell ablation: avoid fit_link's duplicate float32 copy. Values unchanged.
    import numpy as np
    import pipeline.constrained.pd_train as PT

    fit = PT.fit_link

    def fit_link(X, *args, **kw):
        X = np.asarray(X)
        print(f"fit_link input {X.shape} {X.dtype} {X.nbytes / 2**30:.2f} GiB", flush=True)
        model, mu, sd, r = fit(X.view(NoCopy) if X.dtype == np.float32 else X, *args, **kw)
        return model, np.asarray(mu).view(np.ndarray), np.asarray(sd).view(np.ndarray), r

    PT.fit_link = fit_link

    c["base"] = a.out
    c["tree"] = lambda h: J(a.out, "art")
    os.makedirs(J(a.out, "art", "models"), exist_ok=True)
    return P.do_train_d2(c, head)


if __name__ == "__main__":
    sys.exit(main())
