"""ilb_extract. The best-model run's extractions through the engine's own Extractor (Uzayr's prompt of 10 Oct;
`runs/identify/best/`), every session, features only (no decision, no score):

- `dense`: A1's training windows started 0.05, 0.10, 0.20, 0.25, 0.35, 0.40, 0.45, 0.50 s after the press (0.15 and 0.30
  are this morning's `ilc_extract` files), T 4.0, the Wi-Fi speed at alpha 0.5 and 0.2; anchor: offset 0 on each session's
  first recording reproduces the bank's features and both speeds exactly.
- `stretch`: A3's time-stretched windows: each walk's frames (taken at the decision time of a 4.5 s window, so the
  stretched window has its data) with their times rescaled about the press, t' = t0 + s (t - t0), s in {0.9, 1.1}, and the
  features recomputed by the engine's `extract_window` on [t0, t0 + 4.0]; the pace column scaled to v / s. Anchor: s = 1.0
  (and 1.1) on the standard 4.0 s window's frames reproduce the bank exactly on every walk; 0.9 uses a 4.5 s window.
- `tta`: A4's test windows at 0.15 and 0.30 s with their maps (the CNNs need them), both speeds.

    PYTHONPATH=. python3 -m pipeline.identify.ilb_extract dense --session A1 --part 0|1
    PYTHONPATH=. python3 -m pipeline.identify.ilb_extract stretch --session A1
    PYTHONPATH=. python3 -m pipeline.identify.ilb_extract tta --session A1

Exploratory development, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilp_extract as X

BD = os.path.join("runs", "identify", "best")
OUT = os.path.join(BD, "extract")
DENSE = ((0.05, 0.10, 0.20, 0.25), (0.35, 0.40, 0.45, 0.50))
STRETCH = (0.9, 1.1)
TTA = (0.15, 0.30)
LABEL = "exploratory development, all data seen"


def _same(u, v) -> bool:
    return (u == v) or (np.isnan(u) and np.isnan(v))


def offsets(session: str, offs: tuple, with_maps: bool, tag: str, anchor: bool) -> str:
    from pipeline.io.capture_logger import read_capture_file
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    X4 = np.load(os.path.join(EN.bank_dir(4.0), "features.npy"))
    out = {"rows": [], "offset": [], "F": [], "speed_0.5": [], "speed_0.2": [], "maps": [], "anchor": []}
    t_all = time.time()
    first = anchor
    for rec, qs, rows, meta in X._recordings(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        oo = ((0.0,) if first else ()) + tuple(offs)
        ex = {(o, a): EN.Extractor(T=4.0, layout=layout, names=names, alpha=a) for o in oo for a in (0.5, 0.2)}
        pos = {L: 0 for L in EN.LINKS}
        for q, k in zip(qs, rows):
            t0 = float(q["t_start"])
            lim = t0 + max(oo) + 4.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if rec["kind"] == "idcap" else q["path_name"]
            for o in oo:
                got = {}
                for a in (0.5, 0.2):
                    e = ex[(o, a)]
                    e.press(t0 + o, path=known)
                    (_w, _td, x), = e.poll(t0 + o + 4.0 + EN.CAP_S)
                    got[a] = x
                if o == 0.0:
                    out["anchor"].append(bool(np.array_equal(got[0.5]["features"], X4[k], equal_nan=True)
                                              and _same(got[0.5]["wifi_speed"], meta[k]["wifi_speed"])
                                              and _same(got[0.2]["wifi_speed"], meta[k]["wifi_speed_a0.2"])))
                    continue
                out["rows"].append(k)
                out["offset"].append(o)
                out["F"].append(np.asarray(got[0.5]["features"], np.float64)[cols])
                out["speed_0.5"].append(float(got[0.5]["wifi_speed"]))
                out["speed_0.2"].append(float(got[0.2]["wifi_speed"]))
                if with_maps:
                    out["maps"].append(got[0.5]["maps"])
                    out.setdefault("path_used", []).append(str(got[0.5]["path"]))
        first = False
        print(f"{time.strftime('%H:%M:%S')} {tag} {session} {rec['kind']} {rec['block']}: {len(out['rows'])} windows, "
              f"{time.time() - t_all:.0f} s, anchor {sum(out['anchor'])} of {len(out['anchor'])}", flush=True)
    p = os.path.join(OUT, tag, f"{session}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump({k: (v if k == "maps" else np.asarray(v)) for k, v in out.items()} | {"label": LABEL}, open(p, "wb"))
    if anchor and not (out["anchor"] and all(out["anchor"])):
        raise SystemExit(f"offset 0 does not reproduce the bank: {tag} {session} BLOCKED")
    print(f"{time.strftime('%H:%M:%S')} wrote {p}", flush=True)
    return p


class StretchTap(EN.Extractor):
    """The engine's Extractor; `extract_v4` replaced by stretched windows' features (the engine's `extract_window` on
    [t0, t0 + 4.0], the window's own path and layout) for the factors given. At T 4.0 (factors 1.0 and 1.1, which need no
    frame past 4.0 s) the frames and clock are exactly the bank's; the 0.9 stretch needs frames to 4.44 s, so it runs on a
    4.5 s window, whose later decision time can shift the causal clock slightly (disclosed)."""

    def __init__(self, *a, factors=(1.0,), **k):
        super().__init__(*a, **k)
        self.factors = factors

    def extract_v4(self, w: dict, td: float, timed: list) -> dict:
        t0 = w["t0"]
        out = {}
        for s in self.factors:
            ts = [(t0 + (t - t0) * s, a, r) for t, a, r in timed]
            out[s] = EN.extract_window(ts, t0, 4.0, self.amp_norm, w["path"], w["layout"], self.names)["features"]
        return out


def stretch(session: str) -> str:
    from pipeline.io.capture_logger import read_capture_file
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    X4 = np.load(os.path.join(EN.bank_dir(4.0), "features.npy"))
    out = {"rows": [], "factor": [], "F": [], "speed_0.5": [], "speed_0.2": [], "anchor_exact": []}
    t_all = time.time()
    for rec, qs, rows, meta in X._recordings(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        taps = {4.0: StretchTap(T=4.0, layout=layout, names=names, alpha=0.5, factors=(1.0, 1.1)),
                4.5: StretchTap(T=4.5, layout=layout, names=names, alpha=0.5, factors=(0.9,))}
        pos = {L: 0 for L in EN.LINKS}
        for q, k in zip(qs, rows):
            t0 = float(q["t_start"])
            lim = t0 + 4.5 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in taps.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            x = {}
            for T, e in taps.items():
                e.press(t0, path=meta[k]["engine_path"])
                (_w, _td, xx), = e.poll(t0 + T + EN.CAP_S)
                x.update(xx)
            out["anchor_exact"].append(bool(np.array_equal(x[1.0], X4[k], equal_nan=True)))
            for s in STRETCH:
                out["rows"].append(k)
                out["factor"].append(s)
                out["F"].append(np.asarray(x[s], np.float64)[cols])
                out["speed_0.5"].append(meta[k]["wifi_speed"] / s)
                out["speed_0.2"].append(meta[k]["wifi_speed_a0.2"] / s)
        print(f"{time.strftime('%H:%M:%S')} stretch {session} {rec['kind']} {rec['block']}: {len(out['rows'])} windows, "
              f"{time.time() - t_all:.0f} s, anchor {sum(out['anchor_exact'])} of {len(out['anchor_exact'])}", flush=True)
    p = os.path.join(OUT, "stretch", f"{session}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump({k: np.asarray(v) for k, v in out.items()} | {"label": LABEL}, open(p, "wb"))
    if not all(out["anchor_exact"]):
        raise SystemExit(f"s = 1.0 does not reproduce the bank: stretch {session} BLOCKED")
    print(f"{time.strftime('%H:%M:%S')} wrote {p}; s = 1.0 reproduces the bank on every walk", flush=True)
    return p


if __name__ == "__main__":
    what = sys.argv[1]
    s = sys.argv[sys.argv.index("--session") + 1]
    if what == "dense":
        part = int(sys.argv[sys.argv.index("--part") + 1])
        offsets(s, DENSE[part], False, f"dense{part}", anchor=(part == 0))
    elif what == "stretch":
        stretch(s)
    elif what == "tta":
        offsets(s, TTA, True, "tta", anchor=False)
    sys.exit(0)
