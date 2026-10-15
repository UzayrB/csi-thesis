"""ixa_data. The extras brief's candidates A1 to A3 (`runs/identify/engine/PLAN.md`, the extras note): the
identity-blind ingredients, from one pass over every recording through the engine's own Extractor.

For each pass and each window start (t0, t0 + 0.15 s, t0 + 0.30 s; 3 s windows):
- identification-spot windows: RX2's conditioned spectrogram (raw amplitude) on the 10 bins 10 <= f < 35 Hz;
- other windows: the best link's per-frame torso contour (the current estimator's frames) and F;
- the offset windows' gait features (the t0 features are the engine bank's).
And the empty-room spectra: every `*_empty_idspot` RX2 recording of each Room B day, in 3 s windows.

    PYTHONPATH=. python3 -m pipeline.identify.ixa_data
"""

from __future__ import annotations

import glob
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idx_bank as B

OUT = os.path.join("runs", "identify", "final_extras", "a_data")
OFFSETS = (0.0, 0.15, 0.30)
BAND = (10.0, 35.0)


def rx2_band_spectrum(a_rx2: np.ndarray):
    """(f (10,), P (10, frames)): `conditioned_spectrogram` of the raw RX2 window, bins 10 <= f < 35 Hz."""
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(a_rx2)
    m = (f >= BAND[0]) & (f < BAND[1])
    return f[m], P[m].astype(np.float64)


def torso_contour(a_link: np.ndarray) -> np.ndarray:
    """`id29_dc2_score.torso_hz`'s per-frame contour (its median is the current estimator's f_torso)."""
    from scipy import signal
    from pipeline.identify import idmax_common as IC
    from pipeline.identify import idmax_features as F
    from pipeline.identify.conditioning import energy_percentile_contour
    P = F.reduce_link(a_link, "dop", "pca", n_pc=4)[1:]
    f, _t, Z = signal.stft(P, fs=IC.FS, nperseg=32, noverlap=24, nfft=64, axis=-1)
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 70.0)
    return np.asarray(energy_percentile_contour(f[keep], mag[:, keep], 50.0), float)


def window_raw(ex: EN.Extractor, w: dict, td: float) -> np.ndarray:
    """The window's raw amplitude (3, n, 103) on the engine's grid, from the frames the engine used."""
    from pipeline.identify.id19_bank import _interp_cols
    grid = np.arange(w["t0"], w["t0"] + ex.T, 1.0 / EN.FS)
    timed = [ex.rx[L].timed(td) for L in EN.LINKS]
    return np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in timed], np.float64)


class Tap(EN.Extractor):
    """The engine's Extractor, keeping each decided window's raw amplitude (for the ingredients above)."""

    def poll(self, now, closing=False):
        for r in self.rx.values():
            r.consolidate(trim_before=self.newest - EN.KEEP_S)
        out = []
        while self.pending:
            w = self.pending[0]
            td = self._t_dec(w, np.inf if closing else now)
            if td is None:
                break
            A = window_raw(self, w, td)
            timed = [self.rx[L].timed(td) for L in EN.LINKS]
            if not w["info"].get("features"):
                x = None
            elif self.T > EN.DIR_T_S:                    # engine v4 (2 Oct): the engine's own 4 s path
                x = self.extract_v4(w, td, timed)
            else:
                x = EN.extract_window(timed, w["t0"], self.T, self.amp_norm, w["path"], w["layout"], self.names)
            self.pending.pop(0)
            out.append((w, td, A, x))
        return out


def build(limit: int = None, out: str = OUT) -> dict:
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    meta = json.load(open(os.path.join(EN.ENG, "bank_T3.0", "meta.json")))["passes"]
    names = json.load(open(EN.DEV_NAMES))
    rows = {o: [] for o in OFFSETS}
    feats = {o: [] for o in OFFSETS if o > 0}
    k = 0
    for rec in B.recordings()[:limit]:
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = {o: Tap(T=3.0, layout=layout, names=names) for o in OFFSETS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            m = meta[k]
            t0 = float(q["t_start"])
            assert abs(m["t_start"] - t0) < 1e-6
            lim = t0 + max(OFFSETS) + 3.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                for e in ex.values():
                    e.push(L, fr[L][pos[L]:n])
                pos[L] = n
            path = m["engine_path"]                      # detected (identification walks) or recorded (tracking)
            for o, e in ex.items():
                e.press(t0 + o, path=path, info={"features": o > 0})
                (w, td, A, x), = e.poll(t0 + o + 3.0 + EN.CAP_S)
                if o == 0:
                    assert abs(td - m["t_dec"]) < 1e-9, (k, td, m["t_dec"])   # the engine bank's own window
                row = {"row": k, "offset": o, "kind": rec["kind"], "t_dec": td}
                li, F = EN.best_link(path, layout)
                row.update({"idspot": rec["kind"] == "idcap", "F": F, "link": EN.LINKS[li],
                            "contour": torso_contour(A[li]) if F >= EN.F_MIN else None})
                if rec["kind"] == "idcap":
                    f, P = rx2_band_spectrum(A[1])
                    row.update({"f": f.tolist(), "P": P})
                rows[o].append(row)
                if o > 0:
                    feats[o].append(x["features"])
            k += 1
        print(f"{time.strftime('%H:%M:%S')} {rec['session']} {rec['kind']} {rec['block']}: {k} passes, {time.time() - t_all:.0f} s", flush=True)
    assert limit is not None or k == len(meta)
    OUT_ = out
    os.makedirs(OUT_, exist_ok=True)
    pickle.dump(rows, open(os.path.join(OUT_, "windows.pkl"), "wb"))
    for o, v in feats.items():
        np.save(os.path.join(OUT_, f"features_off{o:.2f}.npy"), np.asarray(v, np.float32))
    # empty-room spectra at the identification spot, per Room B day
    emp = {}
    for day, d in (("B1", "session_01"), ("B2", "session_02")):
        spec = []
        for p in sorted(glob.glob(os.path.join("runs", "identify", "dc2_src_relabelled", "identification", d, "*_empty_idspot_RX2.bin"))):
            t, a, _r, _c = EN_link(p)
            for s in np.arange(t.min() + 1.0, t.max() - 3.0 - 1.0, 3.0):
                from pipeline.identify.id19_bank import _interp_cols
                seg = _interp_cols(np.arange(s, s + 3.0, 1.0 / EN.FS), t, a)
                f, P = rx2_band_spectrum(seg)
                spec.append(P)
        emp[day] = {"n_windows": len(spec), "frames": np.concatenate(spec, axis=1)}
        print(f"empty idspot {day}: {len(spec)} windows", flush=True)
    pickle.dump(emp, open(os.path.join(OUT_, "empty_idspot.pkl"), "wb"))
    json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "offsets": OFFSETS, "n_passes": k, "seconds": round(time.time() - t_all, 1),
               "extractor": "engine.Extractor (Tap keeps the raw window)", "label": EN.LABEL},
              open(os.path.join(OUT_, "build.json"), "w"), indent=1)
    return {"n": k}


def EN_link(path: str):
    """A whole empty-room recording on the frozen clock (`id29_dc2_score._link`), amplitude on the 103 entries."""
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify.id19_featbank import SC
    t, a, r, c = D._link(path)
    return t, np.asarray(a, np.float64)[:, SC], r, c


if __name__ == "__main__":
    build()
    sys.exit(0)
