"""ils_cnn. The lever screen's CNN harness (PLAN note 2026-10-01 17:18, anchor A-C): the three CNN components
recomputed from the saved `_x` models in replay order, with causal AdaBN exactly as `engine.Session` adapts, keeping
every (network, seed) output so seeds and links can be scored apart without inference again.

    pool "engine": every earlier window of the session (the engine's pool; must reproduce the replays, A-C)
    pool "layout": every earlier window of the same layout (Tier 0.1's fix L)

    PYTHONPATH=. python3 -m pipeline.identify.ils_cnn --pool engine --device mps

Development evaluation, all data seen. Inference only; no network is trained.
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import ils_common as IL

TAGS = ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")


def path_of(pool: str, s: str) -> str:
    return os.path.join(IL.OUT, "cnn", f"{pool}_{s}.npz")


def run(s: str, pool: str, device: str) -> dict:
    d = IL.data()
    maps = pickle.load(open(os.path.join(d["bank"], "maps.pkl"), "rb"))
    model = EN.Model(os.path.join(EN.ENG, "models", f"loso_{s}{IL.V2}"), device)
    seeds = list(model.meta["seeds"])
    r = d["rep"][s]
    te, paths = r["te"], r["path_used"]
    n = len(te)
    plain = np.zeros((n, len(seeds), 6))
    adapt = np.zeros((n, len(TAGS), len(seeds), 6))
    pools, t = {}, time.time()
    for k, (i, path) in enumerate(zip(te, paths)):
        key = "all" if pool == "engine" else d["a"]["layout"][i]
        sess = pools.setdefault(key, EN.Session(model))
        Wn = C.windows(maps[i])
        for ti, tag in enumerate(TAGS):
            Xw, dw, pw = sess._cnn_input(tag, [Wn], [str(path)])
            for si, sd in enumerate(seeds):
                if tag == "cnn3":
                    plain[k, si] = C.normalise_logp(C.pass_logp(model.nets[(tag, sd)], Xw, dw, pw, 1, 6, device))[0]
                net = sess.adapted.get((tag, sd), model.nets[(tag, sd)])
                adapt[k, ti, si] = C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, device))[0]
        sess.add({"features": d["X"][i], "wifi_speed": float(r["wifi_speed"][k]), "path": str(path), "maps": maps[i]})
        if k % 50 == 0:
            print(f"{time.strftime('%H:%M:%S')} {pool} {s}: {k}/{n} ({time.time() - t:.0f} s)", flush=True)
    os.makedirs(os.path.dirname(path_of(pool, s)), exist_ok=True)
    np.savez(path_of(pool, s), te=te, plain=plain, adapt=adapt, seeds=np.array(seeds), seconds=time.time() - t)
    return {"n": n, "seconds": round(time.time() - t, 1)}


def load(pool: str, s: str) -> dict:
    z = np.load(path_of(pool, s))
    return {k: z[k] for k in z.files}


def components(z: dict, seeds=None, links=(0, 1, 2)) -> dict:
    """The three CNN components as `engine.Session.classify` forms them, from the chosen seeds and links."""
    si = slice(None) if seeds is None else list(seeds)
    out = {"cnn": C.normalise_logp(z["plain"][:, si].mean(1)),
           "cnn_prior": C.normalise_logp(z["adapt"][:, 0, si].mean(1))}
    per = [C.normalise_logp(z["adapt"][:, 1 + l, si].mean(1)) for l in links]
    out["cnn_perlink_prior"] = C.normalise_logp(sum(per))
    return out


def link_alone(z: dict, l: int) -> np.ndarray:
    return C.normalise_logp(z["adapt"][:, 1 + l].mean(1))


def anchor() -> dict:
    """A-C: the engine pool's components against the replays (to 1e-5), and the decisions with the saved features."""
    d = IL.data()
    out = {}
    for s in IL.SESS:
        z = load("engine", s)
        r = d["rep"][s]
        assert np.array_equal(z["te"], r["te"])
        cc = components(z)
        diff = {c: float(np.abs(cc[c] - r[f"c_{c}"]).max()) for c in IL.CNNC}
        comps = {c: (cc[c] if c in IL.CNNC else r[f"c_{c}"]) for c in IL.COMPS}
        same = int((IL.ensemble(comps).argmax(1) == r["ensemble"].argmax(1)).sum())
        out[s] = {"max_abs_diff": diff, "decisions_equal": f"{same} of {len(r['te'])}",
                  "PASS": bool(max(diff.values()) <= 1e-5 and same == len(r["te"]))}
    out["PASS"] = all(out[s]["PASS"] for s in IL.SESS)
    IL.dump(os.path.join(IL.OUT, "anchor_cnn.json"), out)
    print(out, flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", choices=("engine", "layout"), required=True)
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    a = ap.parse_args(argv)
    for s in IL.SESS:
        print(run(s, a.pool, a.device), flush=True)
    if a.pool == "engine":
        return 0 if anchor()["PASS"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
