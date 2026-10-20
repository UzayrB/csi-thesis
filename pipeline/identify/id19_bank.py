# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The IDMAX signal bank: every pass, three links, on ONE common 150 Hz grid.

from __future__ import annotations

import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC

STAGE = "id19_bank"
DROP = sorted({0, 1, 64} | set(range(27, 38)) | set(range(96, 104)))
KEEP = np.array([i for i in range(128) if i not in DROP])
assert len(KEEP) == 106


# Function bank path.
def bank_path(r: dict) -> str:
    return os.path.join(IC.BANK, f"{r['session']}_{r['anon']}_{format(r['pass_id'], '02d')}.npz")


# Function link stream.
def _link_stream(session: str, stem: str, link: str):
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.identify.raw_access import amplitude_from_frames
    p = os.path.join("data", "room_A", f"session_{session}", f"{stem}_{link}.bin")
    IC.assert_allowed(p)
    _h, fr = read_capture_file(p)
    tm = np.asarray(fr["t_mono"], np.float64)
    lt = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
    d = np.diff(lt)
    for i in np.flatnonzero(d < -1.0):
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
    t_hat = lt + np.interp(lt, cen, val) if len(cen) >= 2 else tm
    order = np.argsort(t_hat, kind="stable")
    amp = amplitude_from_frames(fr[order])[:, KEEP]
    return {"t": t_hat[order], "amp": amp.astype(np.float32),
            "rssi": np.asarray(fr["rssi"], np.float32)[order],
            "clock_fit_bins": len(cen),
            "median_lag_s": float(np.median(tm - t_hat)) if len(cen) >= 2 else None}


# Function interp cols.
def _interp_cols(tq: np.ndarray, t: np.ndarray, a: np.ndarray) -> np.ndarray:
    j = np.clip(np.searchsorted(t, tq) - 1, 0, len(t) - 2)
    t0, t1 = t[j], t[j + 1]
    w = np.clip((tq - t0) / np.maximum(t1 - t0, 1e-9), 0.0, 1.0)
    if a.ndim == 1:
        return a[j] * (1 - w) + a[j + 1] * w
    return a[j] * (1 - w)[:, None] + a[j + 1] * w[:, None]


# Function build recording.
def build_recording(session: str, stem: str, rows: list) -> dict:
    from pipeline.identify.conditioning import c2_hampel
    todo = [r for r in rows if not os.path.exists(bank_path(r))]
    if not todo:
        return {"skipped": len(rows)}
    links = {}
    for link in ("RX1", "RX2", "RX3"):
        links[link] = _link_stream(session, stem, link)
    info = {"clock": {k: {"bins": v["clock_fit_bins"], "median_lag_s": v["median_lag_s"]}
                      for k, v in links.items()},
            "median_amp_kept_min": {k: float(np.median(v["amp"], axis=0).min())
                                    for k, v in links.items()}}
    for r in todo:
        if IC.should_stop():
            break
        t0 = r["t_start_press"] - IC.PRE_S
        t1 = r["t_end_press"] + IC.POST_S
        grid = np.arange(t0, t1, 1.0 / IC.FS)
        A, H, R, G = [], [], [], []
        for link in ("RX1", "RX2", "RX3"):
            L = links[link]
            m = (L["t"] >= t0 - 1.0) & (L["t"] <= t1 + 1.0)
            t, a = L["t"][m], L["amp"][m]
            if len(t) < 50:
                raise RuntimeError(f"{session} {stem} pass {r['pass_id']} {link}: {len(t)} packets")
            a_g = _interp_cols(grid, t, a)
            A.append(a_g)
            H.append(c2_hampel(a_g))
            R.append(_interp_cols(grid, t, L["rssi"][m]))
            k = np.clip(np.searchsorted(t, grid), 1, len(t) - 1)
            G.append(np.minimum(np.abs(grid - t[k - 1]), np.abs(t[k] - grid)))
        ix = lambda tt: int(round((tt - t0) * IC.FS))
        np.savez(bank_path(r),
                 amp_raw=np.asarray(A, np.float16), amp_hampel=np.asarray(H, np.float16),
                 rssi=np.asarray(R, np.float16), gap=np.asarray(G, np.float16),
                 i_start=ix(r["t_start_press"]), i_end=ix(r["t_end_press"]),
                 i_we_lo=ix(r["walk_edge_lo"]) if r["walk_edge_lo"] is not None else -1,
                 i_we_hi=ix(r["walk_edge_hi"]) if r["walk_edge_hi"] is not None else -1,
                 t0=t0)
    return info


# Function main.
def main(argv) -> int:
    w = int(argv[1]) if len(argv) > 1 else 0
    n = int(argv[2]) if len(argv) > 2 else 1
    IC.job_start(f"{STAGE}_w{w}of{n}")
    os.makedirs(IC.BANK, exist_ok=True)
    inv = IC.pass_inventory()
    recs = IC.recordings()[w::n]
    t_all = time.time()
    for session, stem in recs:
        if IC.should_stop():
            IC.status(STAGE, "SIGTERM: stopping after the last written pass")
            break
        t = time.time()
        rows = [r for r in inv if r["session"] == session and r["stem"] == stem]
        info = build_recording(session, stem, rows)
        IC.status(STAGE, f"w{w} {session}/{IC.anon(IC.participant_of(stem))} {len(rows)} passes "
                         f"{time.time() - t:.0f}s {info}")
    IC.status(STAGE, f"w{w} finished {len(recs)} recordings in {time.time() - t_all:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
