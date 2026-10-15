"""Where the live app's memory goes as a day's walks accumulate (the confirmation run's footprint grows; nothing is
changed, this only measures): B2's first recordings through the live app (`replay_session`, cpu), then the bytes of numpy
arrays held by (a) the decision log (`EngineApp.decisions`, the same dicts as `Engine.decisions`: each decision keeps its
three windows' extractions) and (b) the calibration pool (`Session.pools`: each earlier walk's features and CNN windows,
which the AdaBN adaptation needs by design), per walk.

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. nice -n 10 python3 runs/identify/v5/memory_account.py 8

Development evaluation, all data seen.
"""

import json
import os
import sys
import time

import numpy as np


def nbytes(obj, seen: set) -> int:
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    if isinstance(obj, np.ndarray):
        return int(obj.nbytes)
    if isinstance(obj, dict):
        return sum(nbytes(v, seen) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(nbytes(v, seen) for v in obj)
    return 0


if __name__ == "__main__":
    from pipeline.live import identify_engine as IE
    n_rec = int(sys.argv[1])
    t = time.time()
    app = IE.replay_session("B2", model="loso_B2_v5", device="cpu", recordings=n_rec)
    walks = len(app.decisions)
    seen = set()
    dec = nbytes(app.decisions, seen)
    pool = nbytes(app.e.session._s.pools, seen)
    one = app.decisions[-1]
    parts = {k: nbytes(v, set()) for k, v in one.items() if nbytes(v, set())}
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "recordings": n_rec, "walks": walks,
           "decision_log_bytes": dec, "pool_bytes": pool, "per_walk_decision_log_mb": round(dec / walks / 2 ** 20, 3),
           "per_walk_pool_mb": round(pool / walks / 2 ** 20, 3),
           "at_299_walks_gb": {"decision_log": round(dec / walks * 299 / 2 ** 30, 2), "pool": round(pool / walks * 299 / 2 ** 30, 2)},
           "one_decision_bytes_by_field": parts, "seconds": round(time.time() - t, 1)}
    json.dump(res, open(os.path.join("runs", "identify", "v5", "checks", "memory_account.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
