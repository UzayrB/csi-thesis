"""Parallel-extraction feasibility test (Uzayr's go, 12 Oct; the Mastermind's spec). Scratch measurement only: nothing that
ships changes (engine.py and identify_engine.py are only imported). On recorded B2 identification walks, engine v5's three
window extractions (0, 0.15 and 0.30 s after the press) are timed three ways, each window extracted by the engine's own
`Extractor.extract_v4` from its OWN deep copy of the receivers frozen at the third window's decision (no shared mutable state):

  (a) series, as the engine does now: each window starts when it is due (its decision time, relative to the 0 s window's) or
      when the window before it has finished, whichever is later;
  (b) threads: each window in its own thread, started when it is due;
  (c) processes: three pre-started worker processes (OMP_NUM_THREADS 1 each), each window's frozen copy sent when it is due.

Per walk: each arm's wall time from the third window being due to all three extractions done, and whether every extraction
output (features, maps, path, speed and every other field but extract_s) is bit-identical to (a)'s. The implied decision
delay after t0 + 4.0 s is an ESTIMATE: the walk's own 0 s window decision time after t0 + 4.0 s, plus the arm's wall time
from then to the last extraction, plus the latency run's median classification (0.140 s), plus the latency run's median
remaining overhead on the same walk (its measured delay minus the series arm's implied delay).

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/identify/v5/latency/parallel_test/ptest.py 3

Development evaluation, all data seen.
"""

import copy
import glob
import json
import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

OUT = os.path.join("runs", "identify", "v5", "latency", "parallel_test")
OFFS = (0.0, 0.15, 0.30)
CLASSIFY_S = 0.140             # the latency run's median model time for the three windows (rig_timing_confirm_lat.json)


def params() -> dict:
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_train as IT
    man = json.load(open(os.path.join(EN.ENG, "models", "loso_B2_v5", "manifest.json")))
    return {"T": EN.T_S, "amp_norm": IT.gs_adopted(), "names": json.load(open(EN.DEV_NAMES)), "alpha": man["alpha"]}


def extract(job: dict) -> dict:
    """One window, from its own frozen receivers: the engine's extraction, unchanged."""
    from pipeline.identify import engine as EN
    p, rx, w, td, cut = job["p"], job["rx"], job["w"], job["td"], job["cut"]
    e = EN.Extractor(p["T"], p["amp_norm"], w["layout"], p["names"], p["alpha"], rx=rx, cut=cut)
    timed = [rx[L].timed(td) for L in EN.LINKS]
    return e.extract_v4(w, td, timed)


def _worker_init():
    """Every module the extraction imports lazily, imported before any timing."""
    from pipeline.identify import engine, id19_bank, id19_featbank, id29_dc2_score, idmax_features, idz_bank  # noqa: F401
    from pipeline.identify import rehearsal_doppler_check  # noqa: F401


def _worker(job: dict, at: float) -> tuple:
    """Process arm: wait for the window's due moment (wall clock), extract, return (result, start, end)."""
    d = at - time.time()
    if d > 0:
        time.sleep(d)
    s = time.time()
    r = extract(job)
    return r, s, time.time()


def walks(n_rec: int) -> list:
    """The first `n_rec` B2 identification recordings, walk by walk, as the engine meets them (frames pushed to the third
    window's cap, the presses at t0 and t0 + 0.15, 0.30): per walk the three windows and their decision times, the receivers
    frozen there."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.io.capture_logger import read_capture_file
    p = params()
    out = []
    recs = [r for r in RP.session_recordings("B2") if r["kind"] == "idcap"][:n_rec]
    for rec in recs:
        ex = EN.Extractor(p["T"], p["amp_norm"], "id_spot", p["names"], p["alpha"])
        offs = {o: EN.Extractor(p["T"], p["amp_norm"], "id_spot", p["names"], p["alpha"], rx=ex.rx, cut=False) for o in OFFS[1:]}
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0 = float(q["t_start"])
            lim = t0 + OFFS[-1] + EN.T_S + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            for e in offs.values():
                e.newest = ex.newest
            ex.press(t0, path=None, layout="id_spot")
            for o, e in offs.items():
                e.press(t0 + o, path=None, layout="id_spot")
            for r in ex.rx.values():
                r.consolidate(trim_before=ex.newest - EN.KEEP_S)
            win = []
            for o, e in [(0.0, ex)] + list(offs.items()):
                w = e.pending.pop(0)
                td = e._t_dec(w, lim)
                assert td is not None
                win.append({"o": o, "w": w, "td": float(td), "cut": e.cut})
            out.append({"recording": os.path.basename(rec["stem"]), "block": rec["block"], "t0": t0, "windows": win, "rx": copy.deepcopy(ex.rx)})
    return out


def same(a: dict, b: dict) -> bool:
    if set(a) != set(b):
        return False
    for k in a:
        if k == "extract_s":
            continue
        x, y = a[k], b[k]
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            x, y = np.asarray(x), np.asarray(y)
            if x.shape != y.shape or x.dtype != y.dtype:
                return False
            if not np.array_equal(x, y, equal_nan=bool(np.issubdtype(x.dtype, np.floating))):
                return False
        elif isinstance(x, float) and isinstance(y, float):
            if not (x == y or (np.isnan(x) and np.isnan(y))):
                return False
        elif x != y:
            return False
    return True


def run_arm(arm: str, walk: dict, p: dict, pool=None) -> dict:
    jobs = [{"p": p, "rx": copy.deepcopy(walk["rx"]), "w": W["w"], "td": W["td"], "cut": W["cut"]} for W in walk["windows"]]
    due = [W["td"] - walk["windows"][0]["td"] for W in walk["windows"]]
    res, st, en = [None] * 3, [0.0] * 3, [0.0] * 3
    t_start = time.time() + 0.05
    if arm == "series":
        while time.time() < t_start:
            time.sleep(0.001)
        prev = t_start
        for k in range(3):
            at = max(t_start + due[k], prev)
            while time.time() < at:
                time.sleep(0.001)
            st[k] = time.time()
            res[k] = extract(jobs[k])
            en[k] = prev = time.time()
    elif arm == "threads":
        def go(k):
            d = t_start + due[k] - time.time()
            if d > 0:
                time.sleep(d)
            st[k] = time.time()
            res[k] = extract(jobs[k])
            en[k] = time.time()
        th = [threading.Thread(target=go, args=(k,)) for k in range(3)]
        for t in th:
            t.start()
        for t in th:
            t.join()
    else:
        futs = []
        for k in range(3):                               # each window's copy sent when it is due (the transfer on the path)
            d = t_start + due[k] - time.time()
            if d > 0:
                time.sleep(d)
            futs.append(pool.submit(_worker, jobs[k], t_start + due[k]))
        for k, f in enumerate(futs):
            res[k], st[k], en[k] = f.result()
    done = max(en)
    return {"results": res, "start_rel": [s - t_start for s in st], "end_rel": [e - t_start for e in en],
            "from_first_due_s": done - t_start, "from_third_due_s": done - (t_start + due[2]), "due_rel": due}


if __name__ == "__main__":
    from pipeline.identify import idmax_features as IMF
    n_rec = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT, exist_ok=True)
    t_all = time.time()
    p = params()
    W = walks(n_rec)
    print(f"{time.strftime('%H:%M:%S')} {len(W)} walks frozen", flush=True)
    v1 = IMF.resolve_cadence
    pool = ProcessPoolExecutor(max_workers=3, initializer=_worker_init)
    warm = W[0]
    for f in [pool.submit(_worker, {"p": p, "rx": copy.deepcopy(warm["rx"]), "w": x["w"], "td": x["td"], "cut": x["cut"]}, 0.0)
              for x in warm["windows"] * 3]:                 # nine warm extractions, so every worker has run one
        f.result()
    for x in warm["windows"]:                            # the in-process arms' first-call cost, paid before timing
        extract({"p": p, "rx": copy.deepcopy(warm["rx"]), "w": x["w"], "td": x["td"], "cut": x["cut"]})
    rows = []
    for i, w in enumerate(W):
        r = {"recording": w["recording"], "block": w["block"], "t0": w["t0"],
             "due_after_t0_plus_4_s": [x["td"] - (w["t0"] + 4.0) for x in w["windows"]]}
        ref = None
        for arm in ("series", "threads", "processes"):
            a = run_arm(arm, w, p, pool)
            if arm == "threads":
                IMF.resolve_cadence = v1                 # the threads may leave engine.py's scoped swap in place: restored
            if ref is None:
                ref = a["results"]
            r[arm] = {"from_first_due_s": round(a["from_first_due_s"], 4), "from_third_due_s": round(a["from_third_due_s"], 4),
                      "start_rel": [round(x, 4) for x in a["start_rel"]], "end_rel": [round(x, 4) for x in a["end_rel"]],
                      "identical_to_series": [bool(same(ref[k], a["results"][k])) for k in range(3)]}
        rows.append(r)
        print(f"{time.strftime('%H:%M:%S')} walk {i + 1}/{len(W)}: series {r['series']['from_third_due_s']:.3f}, threads "
              f"{r['threads']['from_third_due_s']:.3f} {all(r['threads']['identical_to_series'])}, processes "
              f"{r['processes']['from_third_due_s']:.3f} {all(r['processes']['identical_to_series'])}", flush=True)
    pool.shutdown()
    # the implied decision delay (an estimate), calibrated walk by walk on the latency run's measured delays
    z = np.load(sorted(glob.glob(os.path.join("runs", "identify", "v5", "rig", "rig_timing_confirm_lat_2*.npz")))[-1])
    meas = {round(float(t), 6): float(d) for t, d in zip(z["t0"], z["delay_after_t0_plus_4_s"])}
    for r in rows:
        first = r["due_after_t0_plus_4_s"][0]
        imp = {arm: first + r[arm]["from_first_due_s"] + CLASSIFY_S for arm in ("series", "threads", "processes")}
        m = meas.get(round(r["t0"], 6))
        r["implied_delay_estimate_s"] = {k: round(v, 4) for k, v in imp.items()}
        r["measured_delay_latency_run_s"] = m
        r["overhead_s"] = None if m is None else round(m - imp["series"], 4)
    ov = float(np.median([r["overhead_s"] for r in rows if r["overhead_s"] is not None]))
    pooled = {}
    for arm in ("series", "threads", "processes"):
        x = np.array([r[arm]["from_third_due_s"] for r in rows])
        pooled[arm] = {"from_third_due_s": {"median": round(float(np.median(x)), 4), "p95": round(float(np.percentile(x, 95)), 4),
                                            "max": round(float(x.max()), 4)},
                       "walks_all_identical": int(sum(all(r[arm]["identical_to_series"]) for r in rows)),
                       "windows_identical": int(sum(sum(r[arm]["identical_to_series"]) for r in rows)),
                       "implied_delay_estimate_s": {
                           "median": round(float(np.median([r["implied_delay_estimate_s"][arm] for r in rows])) + ov, 4),
                           "max": round(float(np.max([r["implied_delay_estimate_s"][arm] + (r["overhead_s"] or ov) for r in rows])), 4)}}
        if arm != "series":
            sp = np.array([r["series"]["from_third_due_s"] / r[arm]["from_third_due_s"] for r in rows])
            pooled[arm]["speedup_over_series_from_third_due"] = {"median": round(float(np.median(sp)), 3), "min": round(float(sp.min()), 3)}
    res = {"label": "development evaluation, all data seen; a scratch timing measurement, nothing ships",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "walks": len(rows), "recordings": sorted({r["recording"] for r in rows}),
           "threads": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS")}, "nice": os.nice(0), "workers": 3,
           "classify_s_assumed": CLASSIFY_S, "overhead_s_median_from_latency_run": round(ov, 4),
           "measured_delay_latency_run_median_s": round(float(np.median([r["measured_delay_latency_run_s"] for r in rows])), 4),
           "pooled": pooled, "seconds": round(time.time() - t_all, 1), "per_walk": rows,
           "note": "implied_delay_estimate: the 0 s window's decision after t0 + 4.0 s + the arm's wall time to the last "
                   "extraction + 0.140 s classification + the walk's measured overhead in the latency run (median over walks "
                   "for the median); an ESTIMATE, not a measurement of a wired-in arm"}
    json.dump(res, open(os.path.join(OUT, "ptest.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("walks", "pooled", "overhead_s_median_from_latency_run", "measured_delay_latency_run_median_s",
                                          "seconds")}, indent=1), flush=True)
