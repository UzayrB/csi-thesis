"""Train one 0.5 s pool head for the shipped all-0.5 s model (PLAN.md step 1).

The shipped training function `pd_cells.do_train_d2` is called unchanged on the cell `fin_A3` (deployed, A1+A2+B1) or
`zsf_B2` (zero-shot, A1+A2). In this process only: the head is one `g` job at the 0.5 s stride with the given cell count
and training seed; the files are named by the pool slot's seed (`--file-seed`), and the saved model's own metadata keeps
the training seed; the outputs go to `--out`, never into a cell.
"""

from __future__ import annotations

import argparse
import os
import sys

J = os.path.join


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", choices=("fin_A3", "zsf_B2"), required=True)
    ap.add_argument("--cells", type=int, choices=(25, 100), required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--file-seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from pipeline.constrained import pd_cells as P
    c = dict(P.cfg(a.cell))
    assert c["opts"].get("aug") and c["opts"].get("rrel") and P.D2[a.cell].get("arch") == "fuse", c
    P.install_rrel()

    head = "net"
    P.HEADS[head] = ("05", [("g", a.cells, a.seed)])

    import pipeline.constrained.artefacts as A
    mp = A.model_path

    def model_path(tag, kind, out_dim, ep, seed, li):
        assert seed == a.seed, (seed, a.seed)
        return mp(tag, kind, out_dim, ep, a.file_seed, li)

    A.model_path = model_path

    c["base"] = a.out
    c["tree"] = lambda h: J(a.out, "art")
    os.makedirs(J(a.out, "art", "models"), exist_ok=True)
    return P.do_train_d2(c, head)


if __name__ == "__main__":
    sys.exit(main())
