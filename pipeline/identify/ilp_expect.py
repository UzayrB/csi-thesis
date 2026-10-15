"""ilp_expect. The last push's output check (the Mastermind, 02:0x): a step counts as done only if its expected output
exists and is complete; run as its own driver step right after the producing step, it exits 1 ("FAILED (no output)")
otherwise, which blocks the rest of the block.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_expect model <model_dir>          # meta, manifest, 5 feature + 16 CNN files
    PYTHONPATH=. python3 -m pipeline.identify.ilp_expect npz <file> <session>       # a scoring of every walk of the session
    PYTHONPATH=. python3 -m pipeline.identify.ilp_expect config <part.json> <name>  # a configuration's DS recorded
    PYTHONPATH=. python3 -m pipeline.identify.ilp_expect merged <min_configs>       # dev.json holds at least this many
    PYTHONPATH=. python3 -m pipeline.identify.ilp_expect file <path>                # exists and non-empty

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np


def fail(msg: str):
    print(f"FAILED (no output): {msg}", flush=True)
    sys.exit(1)


def main(argv) -> None:
    what = argv[1]
    if what == "file":
        p = argv[2]
        if not (os.path.exists(p) and os.path.getsize(p) > 0):
            fail(p)
    elif what == "model":
        d = argv[2]
        files = os.listdir(d) if os.path.isdir(d) else []
        need = {"meta_feat_cnn.json", "manifest.json", "train_rows.npy"} | {f"feat_{c}.pkl" for c in
                ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior")}
        seeds = json.load(open(os.path.join(d, "meta_feat_cnn.json")))["seeds"] if "meta_feat_cnn.json" in files else []
        need |= {f"{t}_seed{s}.pt" for t in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2") for s in seeds}
        need |= {f"{t}_norm.pkl" for t in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")}
        missing = sorted(f for f in need if f not in files or os.path.getsize(os.path.join(d, f)) == 0)
        if missing or len(seeds) != 3:
            fail(f"{d}: missing {missing}, seeds {seeds}")
    elif what == "npz":
        p, s = argv[2], argv[3]
        if not os.path.exists(p):
            fail(p)
        from pipeline.identify import ilw_score as LS
        z = np.load(p)
        n = len(LS.order(s)["te"])
        if len(z["te"]) != n or len(z["ensemble"]) != n or not np.isfinite(z["ensemble"]).all():
            fail(f"{p}: {len(z['te'])} of {n} walks")
    elif what == "config":
        p, name = argv[2], argv[3]
        if not os.path.exists(p) or name not in json.load(open(p))["configs"]:
            fail(f"{p}: {name}")
    elif what == "merged":
        p = os.path.join("runs", "identify", "lastpush", "dev", "dev.json")
        n = json.load(open(p)).get("n_configurations_scored", 0) if os.path.exists(p) else 0
        if n < int(argv[2]):
            fail(f"{p}: {n} configurations, expected at least {argv[2]}")
    else:
        fail(f"unknown check {what}")
    print(f"OK: {' '.join(argv[1:])}", flush=True)


if __name__ == "__main__":
    main(sys.argv)
