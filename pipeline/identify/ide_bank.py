"""ide_bank. The engine's training banks, built by the engine's own extraction (`runs/identify/engine/PLAN.md`,
sections 2.2 and 3), and the identity-blind clock check.

Every recording of `idx_bank.recordings()` is replayed in arrival order through `engine.Extractor`s. Each
recorded pass's start press opens a window; no other press is used. One pass over the recordings feeds six
extractors: T = 2.5, 3.0 and 3.5 s, each with B1's signal path and with GS. Frames are pushed in blocks up
to the latest window's cap, which is harmless: the engine reads only frames arrived by the decision time.

Rows follow the dev bank's order (asserted by start press) and carry its labels. The meta's `speed_m_s` is
the Wi-Fi speed (the engine's pace input); press speed is kept as `press_speed_m_s`, for the S0 control
only.

The clock check (PLAN 2.2) compares, for the T = 3.0 windows, each frame's causal time at the decision with
the frozen centred map (`id29_dc2_score._link`'s statements), and, for every frame of every recording, the
causal time at the frame's own arrival (offset refreshed every 0.5 s).

    PYTHONPATH=. python3 -m pipeline.identify.ide_bank
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idmax_common as IC
from pipeline.identify import idx_bank as B

TS = (2.5, 3.0, 3.5)
VARIANTS = [(T, gs) for T in TS for gs in (False, True)]


def bank_dir(T: float, gs: bool) -> str:
    return os.path.join(EN.ENG, f"bank_T{T:.1f}{'_gs' if gs else ''}")


def frozen_t_hat(fr) -> np.ndarray:
    """`id29_dc2_score._link`'s corrected times, in ARRIVAL order (the same statements, not sorted)."""
    tm = np.asarray(fr["t_mono"], np.float64)
    lt = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
    for i in np.flatnonzero(np.diff(lt) < -1.0):
        lt[i + 1:] += 2.0 ** 32 * 1e-6
    off = tm - lt
    edges = np.arange(lt.min(), lt.max() + 10.0, 10.0)
    idx = np.clip(np.searchsorted(edges, lt) - 1, 0, len(edges) - 2)
    cen, val = [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() >= 20:
            cen.append(float(np.median(lt[m])))
            val.append(float(np.percentile(off[m], 5)))
    return lt + np.interp(lt, cen, val) if len(cen) >= 2 else tm


def every_frame_diff(fr, frozen: np.ndarray) -> np.ndarray:
    """|causal - frozen| for every frame, the causal offset taken at the latest 0.5 s point at or before the
    frame's arrival (engine.Receiver's statements, one receiver fed the whole file)."""
    r = EN.Receiver()
    r.push(fr)
    r.consolidate()
    grid = np.arange(r.tm[0], r.tm[-1] + 0.5, 0.5)
    off = np.full(len(grid), np.nan)
    ep = np.full(len(grid), -1)
    for g, tau in enumerate(grid):
        idx = r.arrived(tau)
        o = r.offset(tau, idx)
        if o is not None:
            off[g], ep[g] = o, r.ep[idx[-1]]
    j = np.clip(np.searchsorted(grid, r.tm, side="right") - 1, 0, len(grid) - 1)
    ok = np.isfinite(off[j]) & (ep[j] == r.ep)
    t = np.where(ok, r.lt + np.nan_to_num(off[j]), r.tm)
    return np.abs(t - frozen)


def build(limit: int = None) -> dict:
    """limit: only the first `limit` recordings (a smoke test; writes nothing complete)."""
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    dev_meta = json.load(open(os.path.join(B.OUT, "meta.json")))["passes"]
    names = json.load(open(os.path.join(B.OUT, "feature_names.json")))
    rows = {v: [] for v in VARIANTS}
    feats = {v: [] for v in VARIANTS}
    maps = {v: [] for v in VARIANTS}
    clock_win, clock_all, clock_rec = [], [], []
    k = 0
    for rec in B.recordings()[:limit]:
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        frozen = {L: frozen_t_hat(fr[L]) for L in EN.LINKS}
        for L in EN.LINKS:
            d = every_frame_diff(fr[L], frozen[L])
            clock_all.append(d)
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = {v: EN.Extractor(T=v[0], amp_norm=v[1], layout=layout, names=names) for v in VARIANTS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            dm = dev_meta[k]
            t0 = float(q["t_start"])
            assert abs(dm["t_start"] - t0) < 1e-6 and dm["session"] == rec["session"], (k, rec["session"])
            lim = t0 + max(TS) + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            known = None if rec["kind"] == "idcap" else q["path_name"]
            for v, e in ex.items():
                e.press(t0, path=known)
                got = e.poll(t0 + v[0] + EN.CAP_S)
                assert len(got) == 1, (k, v, len(got))
                _w, td, x = got[0]
                if v == (3.0, False):
                    for L in EN.LINKS:
                        r = e.rx[L]
                        idx = r.arrived(td)
                        off = r.offset(td, idx)
                        causal = r.lt[idx] + off if off is not None else r.tm[idx]
                        first = pos[L] - len(r.tm)                         # frames trimmed off the front
                        fz = frozen[L][first + idx]
                        inw = (fz >= t0) & (fz <= t0 + v[0])
                        clock_win.append(np.abs(causal - fz)[inw])
                row = {kk: dm[kk] for kk in ("session", "room", "kind", "block", "anon", "path", "t_start", "t_end", "flagged", "channel")}
                row.update({"speed_m_s": x["wifi_speed"], "press_speed_m_s": dm["speed_m_s"],
                            "torso_hz": {L: (x["f_torso"] if x["speed_link"] == L else float("nan")) for L in EN.LINKS},
                            "engine_path": x["path"], "dir_detected": x["dir_detected"], "dir_slope": x["dir_slope"],
                            "wifi_speed": x["wifi_speed"], "speed_link": x["speed_link"], "speed_F": x["speed_F"],
                            "f_torso": x["f_torso"], "t_dec": td, "wait_s": td - (t0 + v[0]), "extract_s": x["extract_s"],
                            "n_frames": x["n_frames"], "T": v[0], "gs": v[1]})
                rows[v].append(row)
                feats[v].append(x["features"])
                maps[v].append(x["maps"])
            k += 1
        clock_rec.append({"session": rec["session"], "kind": rec["kind"], "block": rec["block"],
                          "wraps": {L: ex[(3.0, False)].rx[L].n_wraps for L in EN.LINKS},
                          "reboots": {L: ex[(3.0, False)].rx[L].n_reboots for L in EN.LINKS}})
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k} passes, "
              f"{time.time() - t_all:.0f} s", flush=True)
    assert limit is not None or k == len(dev_meta)
    for v in VARIANTS:
        out = bank_dir(*v)
        os.makedirs(out, exist_ok=True)
        txt = json.dumps({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": k, "passes": rows[v]}, default=float)
        assert IC.no_names(txt)
        open(os.path.join(out, "meta.json"), "w").write(txt)
        json.dump(names, open(os.path.join(out, "feature_names.json"), "w"))
        np.save(os.path.join(out, "features.npy"), np.asarray(feats[v], np.float32))
        pickle.dump(maps[v], open(os.path.join(out, "maps.pkl"), "wb"))
        json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "T": v[0], "gs": v[1], "n_passes": k,
                   "extractor": "pipeline.identify.engine.Extractor", "label": EN.LABEL,
                   "seconds": round(time.time() - t_all, 1)}, open(os.path.join(out, "build.json"), "w"), indent=1)
    cw, ca = np.concatenate(clock_win), np.concatenate(clock_all)
    stat = lambda d: {"n_frames": int(len(d)), "median_ms": round(1e3 * float(np.median(d)), 4),  # noqa: E731
                      "p99_ms": round(1e3 * float(np.percentile(d, 99)), 4), "max_ms": round(1e3 * float(np.max(d)), 4)}
    clock = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "what": "|causal clock (PLAN 2.2) - frozen centred map (id29 _link)|",
             "engine_windows_T3.0_at_decision": stat(cw), "every_frame_at_arrival_0.5s": stat(ca),
             "recordings": clock_rec,
             "wraps_total": int(sum(sum(r["wraps"].values()) for r in clock_rec)),
             "reboots_total": int(sum(sum(r["reboots"].values()) for r in clock_rec))}
    os.makedirs(os.path.join(EN.ENG, "checks"), exist_ok=True)
    txt = json.dumps(clock, indent=1)
    assert IC.no_names(txt)
    open(os.path.join(EN.ENG, "checks", "clock.json"), "w").write(txt)
    print(json.dumps({k_: clock[k_] for k_ in ("engine_windows_T3.0_at_decision", "every_frame_at_arrival_0.5s",
                                               "wraps_total", "reboots_total")}))
    return clock


if __name__ == "__main__":
    build()
    sys.exit(0)
