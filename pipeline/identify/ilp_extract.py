"""ilp_extract. The last push's extractions through the engine's own Extractor (`runs/identify/lastpush/PREREG_LP.md`,
F7 and W1), development sessions only (A1, A2, B1; A3 and B2 need their own slot):

- `offsets`: each walk's windows started 0.15 s and 0.30 s after its press (T 4.0, alpha 0.5), features and Wi-Fi speed;
  anchor: offset 0 on each session's first recording reproduces the bank's features and speed exactly.
- `window --T 5.0`: the engine's v4 window at T 5.0 or 6.0 (alpha 0.5 end detector, direction from the first 3 s, start
  press only), features, maps, speed, t_dec; a window that would reach the next start press stops there (the engine's own
  rule, by registering that press before the window is decided); written as a bank whose other sessions' rows are marked
  not extracted.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_extract offsets --session A1
    PYTHONPATH=. python3 -m pipeline.identify.ilp_extract window --T 5.0 --session A1
    PYTHONPATH=. python3 -m pipeline.identify.ilp_extract merge-window --T 5.0

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import pickle
import shutil
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilp_train as LT

DEV_SESSIONS = ("A1", "A2", "B1")
OFFSETS = (0.15, 0.30)
X_DIR = os.path.join(LT.LP, "extract")


def _recordings(session: str):
    from pipeline.identify import idx_bank as B
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    k = 0
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda z: z["t_start"])
        if rec["session"] == session:
            yield rec, qs, list(range(k, k + len(qs))), meta
        k += len(qs)


def offsets(session: str, limit: int = None, out_file: str = None) -> str:
    """F7's windows: offsets 0.15 and 0.30 s (and 0 on the session's first recording, the anchor)."""
    from pipeline.io.capture_logger import read_capture_file
    assert session in DEV_SESSIONS
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    X4 = np.load(os.path.join(EN.bank_dir(4.0), "features.npy"))
    out = {"rows": [], "offset": [], "F": [], "speed": [], "anchor": []}
    t_all = time.time()
    first = True
    for rec, qs, rows, meta in _recordings(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        offs = ((0.0,) if first else ()) + OFFSETS
        ex = {o: EN.Extractor(T=4.0, layout=layout, names=names, alpha=0.5) for o in offs}
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
            for o, e in ex.items():
                e.press(t0 + o, path=known)
                (_w, _td, x), = e.poll(t0 + o + 4.0 + EN.CAP_S)
                f630 = np.asarray(x["features"], np.float64)[cols]
                if o == 0.0:
                    out["anchor"].append(bool(np.array_equal(x["features"], X4[k], equal_nan=True)
                                              and ((x["wifi_speed"] == meta[k]["wifi_speed"]) or
                                                   (np.isnan(x["wifi_speed"]) and np.isnan(meta[k]["wifi_speed"])))))
                    continue
                out["rows"].append(k)
                out["offset"].append(o)
                out["F"].append(f630)
                out["speed"].append(float(x["wifi_speed"]))
            if limit and len(out["anchor"]) >= limit:
                break
        first = False
        if limit:
            break
        print(f"{time.strftime('%H:%M:%S')} {session} {rec['kind']} {rec['block']}: {len(out['rows'])} windows, "
              f"{time.time() - t_all:.0f} s, anchor {sum(out['anchor'])} of {len(out['anchor'])}", flush=True)
    res = {k: np.asarray(v) for k, v in out.items()}
    p = out_file or os.path.join(X_DIR, "f7", f"{session}.npz")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez(p, **res)
    ok = bool(len(out["anchor"]) and all(out["anchor"]))
    print(f"{time.strftime('%H:%M:%S')} wrote {p}: {len(out['rows'])} windows; anchor {'PASSED' if ok else 'FAILED'}", flush=True)
    if not ok:
        raise SystemExit("offset 0 does not reproduce the bank: F7 BLOCKED")
    return p


def window(T: float, session: str, limit: int = None, out_file: str = None) -> str:
    """W1's windows at T, every pass of one development session."""
    from pipeline.io.capture_logger import read_capture_file
    assert session in DEV_SESSIONS and T > EN.DIR_T_S
    names = json.load(open(EN.DEV_NAMES))
    out = {"rows": [], "features": [], "maps": [], "t_dec": [], "wifi_speed": [], "walk_end_s": [], "path": [],
           "stopped_at_next_press": []}
    t_all = time.time()
    for rec, qs, rows, meta in _recordings(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = EN.Extractor(T=T, layout=layout, names=names, alpha=0.5)
        pos = {L: 0 for L in EN.LINKS}

        def push(upto):
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], upto, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
        pressed = set()
        for j, (q, k) in enumerate(zip(qs, rows)):
            t0 = float(q["t_start"])
            lim = t0 + T + EN.CAP_S
            if j not in pressed:
                push(t0)
                ex.press(t0, path=None if rec["kind"] == "idcap" else q["path_name"])
                pressed.add(j)
            stopped = False
            if j + 1 < len(qs) and float(qs[j + 1]["t_start"]) < t0 + T:
                t1 = float(qs[j + 1]["t_start"])
                push(t1)
                ex.press(t1, path=None if rec["kind"] == "idcap" else qs[j + 1]["path_name"])
                pressed.add(j + 1)
                stopped = True
            push(lim)
            got = ex.poll(lim)
            assert len(got) == 1, (k, len(got), "one window per poll")
            w, td, x = got[0]
            assert abs(w["t0"] - t0) < 1e-9, (k, "order")
            out["rows"].append(k)
            out["features"].append(np.asarray(x["features"], np.float32))
            out["maps"].append(x["maps"])
            out["t_dec"].append(td)
            out["wifi_speed"].append(float(x["wifi_speed"]))
            out["walk_end_s"].append(float(x["walk_end_s"]))
            out["path"].append(str(x["path"]))
            out["stopped_at_next_press"].append(stopped)
            if limit and len(out["rows"]) >= limit:
                break
        if limit:
            break
        print(f"{time.strftime('%H:%M:%S')} T {T} {session} {rec['kind']} {rec['block']}: {len(out['rows'])} windows, "
              f"{time.time() - t_all:.0f} s, stopped at a next press {sum(out['stopped_at_next_press'])}", flush=True)
    p = out_file or os.path.join(X_DIR, f"T{T:.1f}", f"{session}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump(out, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} wrote {p}", flush=True)
    return p


def merge_window(T: float) -> str:
    """A bank at T: the development sessions' rows extracted; the other rows' features NaN, maps empty, marked."""
    src = EN.bank_dir(4.0)
    meta = json.load(open(os.path.join(src, "meta.json")))
    X4 = np.load(os.path.join(src, "features.npy"))
    X = np.full_like(X4, np.nan)
    maps = [np.zeros((3, 28, 1), np.float32) for _ in range(len(X4))]
    for m in meta["passes"]:
        m["extracted"] = False
    for s in DEV_SESSIONS:
        d = pickle.load(open(os.path.join(X_DIR, f"T{T:.1f}", f"{s}.pkl"), "rb"))
        for i, k in enumerate(d["rows"]):
            X[k] = d["features"][i]
            maps[k] = d["maps"][i]
            m = meta["passes"][k]
            m.update({"T": T, "t_dec": float(d["t_dec"][i]), "wifi_speed": d["wifi_speed"][i], "speed_m_s": d["wifi_speed"][i],
                      "walk_end_s": d["walk_end_s"][i], "engine_path": d["path"][i], "extracted": True,
                      "stopped_at_next_press": bool(d["stopped_at_next_press"][i]),
                      "speed_note": f"last push W1 ({LT.LABEL}): engine v4's window at T {T}, alpha 0.5"})
    out = os.path.join(LT.LP, f"bank_T{T:.1f}_lp")
    assert not os.path.exists(os.path.join(out, "meta.json")), f"{out} exists: never overwritten"
    os.makedirs(out, exist_ok=True)
    np.save(os.path.join(out, "features.npy"), X)
    pickle.dump(maps, open(os.path.join(out, "maps.pkl"), "wb"))
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    shutil.copy(os.path.join(src, "feature_names.json"), os.path.join(out, "feature_names.json"))
    json.dump({"label": LT.LABEL, "T": T, "extracted_sessions": list(DEV_SESSIONS), "built": time.strftime("%Y-%m-%dT%H:%M:%S")},
              open(os.path.join(out, "build.json"), "w"), indent=1)
    print(f"{time.strftime('%H:%M:%S')} bank {out}", flush=True)
    return out


if __name__ == "__main__":
    what = sys.argv[1]
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None  # noqa: E731
    if what == "offsets":
        offsets(arg("--session"), int(arg("--limit")) if arg("--limit") else None, arg("--out"))
    elif what == "window":
        window(float(arg("--T")), arg("--session"), int(arg("--limit")) if arg("--limit") else None, arg("--out"))
    elif what == "merge-window":
        merge_window(float(arg("--T")))
    else:
        raise SystemExit(what)
    sys.exit(0)
