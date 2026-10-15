"""Step 2a of the parallel-extraction go (Uzayr, 12 Oct): every window of every B2 walk (all 299, three windows each) extracted
twice from the same frames, as the engine meets them (frames pushed to each walk's last cap, the presses at t0 and t0 + 0.15,
0.30, the known route for a tracking walk and the detected direction for an identification walk, as iv5_replay): (i) serially,
by the engine's own Extractor.poll and extract_v4; (ii) through the live app's ExtractPool (identify_engine.py), its worker
processes running the same extract_v4 on frozen copies. Every extraction must be bitwise identical (every field but the
timing field extract_s; arrays with NaN in the same places), and every decision time equal.

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/identify/v5/parallel/extract_exact.py

Development evaluation, all data seen.
"""

import json
import os
import time
import types

import numpy as np

OUT = os.path.join("runs", "identify", "v5", "parallel", "extract_exact.json")
OFFS = (0.15, 0.30)


def same(a: dict, b: dict) -> list:
    """The fields that differ (empty: identical)."""
    bad = sorted(set(a) ^ set(b))
    for k in set(a) & set(b):
        if k == "extract_s":
            continue
        x, y = a[k], b[k]
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            x, y = np.asarray(x), np.asarray(y)
            ok = (x.shape == y.shape and x.dtype == y.dtype
                  and np.array_equal(x, y, equal_nan=bool(np.issubdtype(x.dtype, np.floating))))
        elif isinstance(x, float) and isinstance(y, float):
            ok = x == y or (np.isnan(x) and np.isnan(y))
        else:
            ok = x == y
        if not ok:
            bad.append(k)
    return bad


if __name__ == "__main__":
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live import identify_engine as IE
    t_all = time.time()
    man = json.load(open(os.path.join(EN.ENG, "models", "loso_B2_v5", "manifest.json")))
    T, amp_norm, alpha = EN.T_S, IT.gs_adopted(), man["alpha"]
    names = json.load(open(EN.DEV_NAMES))
    dmode = RP.direction_mode()

    def fresh(layout):
        ex = EN.Extractor(T, amp_norm, layout, names, alpha)
        return ex, {o: EN.Extractor(T, amp_norm, layout, names, alpha, rx=ex.rx, cut=False) for o in OFFS}

    stand_in = types.SimpleNamespace()                 # the pool's view of an engine: its extractors and new_recording

    def new_recording(layout=None):
        stand_in.ex, stand_in.ex_off = fresh(layout or "id_spot")
    stand_in.new_recording = new_recording
    new_recording("id_spot")
    pool = IE.ExtractPool(stand_in, IE.EXTRACT_WORKERS_V5)
    n_w = n_win = n_same = 0
    diffs, t_ser, t_par = [], 0.0, 0.0
    for rec in RP.session_recordings("B2"):
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        exS, offS = fresh(layout)
        stand_in.new_recording(layout)                 # the pool's wrapper: fresh extractors, hooked
        exP, offP = stand_in.ex, stand_in.ex_off
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + OFFS[-1] + T + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                exS.push(L, fr[L][pos[L]:n])
                exP.push(L, fr[L][pos[L]:n])
                pos[L] = n
            for e in offS.values():
                e.newest = exS.newest
            for e in offP.values():
                e.newest = exP.newest
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else q["path_name"]
            for ex, offs in ((exS, offS), (exP, offP)):
                ex.press(t0, path=known, layout=layout)
                for o, e in offs.items():
                    e.press(t0 + o, path=known, layout=layout)
            c0 = time.time()
            gotS = [e.poll(lim) for e in [exS] + list(offS.values())]
            c1 = time.time()
            gotP = [e.poll(lim) for e in [exP] + list(offP.values())]
            for g in gotP:
                for _w, _td, x in g:
                    x.resolve()
            c2 = time.time()
            t_ser, t_par = t_ser + (c1 - c0), t_par + (c2 - c1)
            n_w += 1
            for k, (gs, gp) in enumerate(zip(gotS, gotP)):
                assert len(gs) == len(gp) == 1, (rec["stem"], t0, len(gs), len(gp))
                (ws, tds, xs), (wp, tdp, xp) = gs[0], gp[0]
                n_win += 1
                bad = same(xs, dict(xp)) + ([] if tds == tdp else ["t_dec"]) + ([] if ws["t0"] == wp["t0"] else ["t0"])
                if bad:
                    diffs.append({"recording": os.path.basename(rec["stem"]), "t0": t0, "window": k, "fields": bad})
                else:
                    n_same += 1
        print(f"{time.strftime('%H:%M:%S')} {os.path.basename(rec['stem'])}: {n_w} walks, {n_same} of {n_win} windows identical",
              flush=True)
    pool.close()
    res = {"label": "development evaluation, all data seen; an identity check of the extraction, no figure",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "session": "B2", "walks": n_w, "windows": n_win,
           "identical_windows": n_same, "differences": diffs[:50], "n_differences": len(diffs),
           "workers": IE.EXTRACT_WORKERS_V5, "serial_extraction_s": round(t_ser, 1), "pool_extraction_s": round(t_par, 1),
           "PASSED": bool(n_w == 299 and n_win == 897 and n_same == n_win), "seconds": round(time.time() - t_all, 1)}
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("walks", "windows", "identical_windows", "n_differences", "serial_extraction_s",
                                          "pool_extraction_s", "PASSED", "seconds")}), flush=True)
