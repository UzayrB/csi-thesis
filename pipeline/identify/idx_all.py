"""idx_all. Identification development (the operator's direction of 2026-09-28): every selector component's
log-probabilities for one held-out session, saved, so selection rules and fixed ensembles can be compared
afterwards without retraining (`idx_all_eval`).

For the held-out session S (training = the other four sessions):
- `oof__<component>`: the inner leave-one-session-out predictions on the four training sessions (each
  training session predicted by components fitted on the other three), `inner_steps`, seed 0;
- `test__<component>`: the components fitted on all four training sessions, predicting S, `steps`, `seeds`.

Components are those of `idx_sel --wide --perlink --no-cnnf`: the gait RF (per-path z, causal session
normalisation, and that with pace as one gait parameter), extra trees and shrinkage LDA on the gait-plus-pace
features, CNN-v2 plain and with AdaBN from the session's earlier recordings, and the per-link CNN with
AdaBN. Every component is causal; no test label is used by anything here.

    PYTHONPATH=. python3 -m pipeline.identify.idx_all --session B1 --device mps
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idx_loso as L
from pipeline.identify import idx_sel as S

OUT = os.path.join("runs", "identify", "dev", "all")


def run(session, inner_steps=1500, steps=6000, seeds=(0, 1, 2), device="cpu", tag="all") -> str:
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    S.PERLINK, S.NO_CNNF = True, True
    S.widen()
    bank = L.load()
    a = bank["a"]
    t0 = time.time()
    tr, te = np.flatnonzero(a["session"] != session), np.flatnonzero(a["session"] == session)
    oof = {}
    for s_in in np.unique(a["session"][tr]):
        m = a["session"][tr] == s_in
        comp = S.components(bank, tr[~m], tr[m], (0,), inner_steps, device=device)
        for k, v in comp.items():
            oof.setdefault(k, np.zeros((len(tr), 6)))[m] = v
        print(f"{time.strftime('%H:%M:%S')} {session}: inner {s_in} done", flush=True)
    test = S.components(bank, tr, te, tuple(seeds), steps, device=device)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{tag}_{session}.npz")
    np.savez(path, tr=tr, te=te, **{f"oof__{k}": v for k, v in oof.items()}, **{f"test__{k}": v for k, v in test.items()})
    meta = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "session": session, "inner_steps": inner_steps, "steps": steps,
            "seeds": list(seeds), "device": device, "components": sorted(test), "seconds": round(time.time() - t0, 1)}
    txt = json.dumps(meta, indent=1)
    assert IC.no_names(txt)
    open(path.replace(".npz", ".json"), "w").write(txt)
    print(f"{time.strftime('%H:%M:%S')} {session}: saved {path}, {meta['seconds']} s", flush=True)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", required=True, choices=L.SESSIONS)
    ap.add_argument("--inner-steps", type=int, default=1500)
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--tag", default="all")
    a = ap.parse_args(argv)
    run(a.session, a.inner_steps, a.steps, tuple(a.seeds), a.device, a.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
