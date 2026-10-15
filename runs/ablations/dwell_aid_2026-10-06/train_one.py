"""Train one head of one arm of the dwell ablation (PLAN.md). Run by run.py, which sets the training environment.

The shipped training function (`pd_cells.do_train_d2`, cell `fin_A3`) is called unchanged. Three things differ, all
in this process only: the cell's output folders point into this ablation's run folder; the cell heads' seeds are
offset by 100 x the seed set; and, for arm WD, A1's and A2's dwell windows (mode `grid`) are relabelled `walk` so
that `dataset.walking_windows` admits them with their cell-centre labels.
"""

from __future__ import annotations

import argparse
import dataclasses
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
    ap.add_argument("--arm", choices=("W", "WD"), required=True)
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--run", required=True, help="this arm and seed set's folder")
    a = ap.parse_args()

    from pipeline.constrained import pd_cells as P
    c = dict(P.cfg("fin_A3"))
    if c["opts"].get("rrel"):
        P.install_rrel()  # before the data modules are imported, as the shipped train command does
    import pipeline.constrained.dataset as D
    import pipeline.constrained.recordings as R

    if a.arm == "WD":
        orig = R.load_meta

        def load_meta(session, stem):
            rec = orig(session, stem)
            if session in ("01", "02"):
                mode = rec.mode.copy()
                mode[mode == "grid"] = "walk"
                rec = dataclasses.replace(rec, mode=mode)
            return rec

        R.load_meta = load_meta
        D.load_meta = load_meta

    stride, jobs = P.HEADS[a.head]
    P.HEADS[a.head] = (stride, [(kind, n, seed + 100 * a.k if kind == "g" else seed) for kind, n, seed in jobs])

    # Memory only: fit_link copies its input with X.astype(np.float32) even when X is already float32. Handing it
    # an array whose same-type astype returns a view keeps the values identical and avoids the duplicate (several
    # GB for the 0.5 s head), so the W+D arm fits in this laptop's memory. Nothing else in training changes.
    import numpy as np
    import pipeline.constrained.pd_train as PT

    fit = PT.fit_link

    def fit_link(X, *args, **kw):
        X = np.asarray(X)
        print(f"fit_link input {X.shape} {X.dtype} {X.nbytes / 2**30:.2f} GiB", flush=True)
        model, mu, sd, r = fit(X.view(NoCopy) if X.dtype == np.float32 else X, *args, **kw)
        return model, np.asarray(mu).view(np.ndarray), np.asarray(sd).view(np.ndarray), r

    PT.fit_link = fit_link

    c["base"] = a.run
    c["tree"] = lambda h: J(a.run, f"art_{h}")
    os.makedirs(J(c["tree"](a.head), "models"), exist_ok=True)
    return P.do_train_d2(c, a.head)


if __name__ == "__main__":
    sys.exit(main())
