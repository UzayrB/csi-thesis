"""ilc_extract. The combine run's F7 offset windows for the outer test's training side (Uzayr's prompt of 10 Oct; the
Mastermind's grant C3): every session's windows started 0.15 s and 0.30 s after each press, through the engine's own
Extractor at T 4.0, with the Wi-Fi speed at both end-detector alphas (0.5, and 0.2 for loso_B1_v4's column). No decision,
no score: feature extraction only. Anchors: offset 0 on each session's first recording reproduces the bank's features
and both speeds exactly; for A1, A2 and B1 the windows equal last night's `ilp_extract` files exactly (features, 0.5).

    PYTHONPATH=. python3 -m pipeline.identify.ilc_extract offsets --session A3
    PYTHONPATH=. python3 -m pipeline.identify.ilc_extract check-last-night

Exploratory development, all data seen.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilp_extract as X

CB = os.path.join("runs", "identify", "combine")
OUT = os.path.join(CB, "extract", "f7")
OFFSETS = (0.15, 0.30)


def offsets(session: str) -> str:
    from pipeline.io.capture_logger import read_capture_file
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    X4 = np.load(os.path.join(EN.bank_dir(4.0), "features.npy"))
    out = {"rows": [], "offset": [], "F": [], "speed_0.5": [], "speed_0.2": [], "anchor": []}
    t_all = time.time()
    first = True
    for rec, qs, rows, meta in X._recordings(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        offs = ((0.0,) if first else ()) + OFFSETS
        ex = {(o, a): EN.Extractor(T=4.0, layout=layout, names=names, alpha=a) for o in offs for a in (0.5, 0.2)}
        pos = {L: 0 for L in EN.LINKS}
        for q, k in zip(qs, rows):
            t0 = float(q["t_start"])
            assert abs(meta[k]["t_start"] - t0) < 1e-6
            lim = t0 + max(offs) + 4.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if rec["kind"] == "idcap" else q["path_name"]
            for o in offs:
                got = {}
                for a in (0.5, 0.2):
                    e = ex[(o, a)]
                    e.press(t0 + o, path=known)
                    (_w, _td, x), = e.poll(t0 + o + 4.0 + EN.CAP_S)
                    got[a] = x
                assert np.array_equal(got[0.5]["features"], got[0.2]["features"], equal_nan=True), (k, o, "alpha changed features")
                if o == 0.0:
                    same = lambda u, v: (u == v) or (np.isnan(u) and np.isnan(v))  # noqa: E731
                    out["anchor"].append(bool(np.array_equal(got[0.5]["features"], X4[k], equal_nan=True)
                                              and same(got[0.5]["wifi_speed"], meta[k]["wifi_speed"])
                                              and same(got[0.2]["wifi_speed"], meta[k]["wifi_speed_a0.2"])))
                    continue
                out["rows"].append(k)
                out["offset"].append(o)
                out["F"].append(np.asarray(got[0.5]["features"], np.float64)[cols])
                out["speed_0.5"].append(float(got[0.5]["wifi_speed"]))
                out["speed_0.2"].append(float(got[0.2]["wifi_speed"]))
        first = False
        print(f"{time.strftime('%H:%M:%S')} {session} {rec['kind']} {rec['block']}: {len(out['rows'])} windows, "
              f"{time.time() - t_all:.0f} s, anchor {sum(out['anchor'])} of {len(out['anchor'])}", flush=True)
    p = os.path.join(OUT, f"{session}.npz")
    os.makedirs(OUT, exist_ok=True)
    np.savez(p, **{k: np.asarray(v) for k, v in out.items()})
    ok = bool(out["anchor"]) and all(out["anchor"])
    print(f"{time.strftime('%H:%M:%S')} wrote {p}: {len(out['rows'])} windows; anchor {'PASSED' if ok else 'FAILED'}", flush=True)
    if not ok:
        raise SystemExit("offset 0 does not reproduce the bank: C3 BLOCKED")
    return p


def check_last_night() -> bool:
    res = {}
    for s in X.DEV_SESSIONS:
        a = np.load(os.path.join(X.X_DIR, "f7", f"{s}.npz"))
        b = np.load(os.path.join(OUT, f"{s}.npz"))
        res[s] = bool(np.array_equal(a["rows"], b["rows"]) and np.array_equal(a["offset"], b["offset"])
                      and np.array_equal(a["F"], b["F"], equal_nan=True) and np.array_equal(a["speed"], b["speed_0.5"], equal_nan=True))
    res["PASSED"] = all(res.values())
    os.makedirs(os.path.join(CB, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(CB, "checks", "f7_equal_last_night.json"), "w"), indent=1)
    print(json.dumps(res), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    if sys.argv[1] == "offsets":
        offsets(sys.argv[sys.argv.index("--session") + 1])
    elif sys.argv[1] == "check-last-night":
        sys.exit(0 if check_last_night() else 1)
    sys.exit(0)
