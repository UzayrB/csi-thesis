"""Step A of the staged extraction (Uzayr's go, 12 Oct; QUEUE_STAGED.md beside this file): every window of every B2 walk (the
window at t0 and the offset windows at t0 + 0.15 and 0.30 s) extracted twice from the same frames, the frames pushed in
0.05 s ticks of arrival time and every extractor polled after each tick, as the app polls: (i) serially, by the engine's own
`Extractor.poll` and `extract_v4`; (ii) through the live app's staged `ExtractPool` (identify_engine.py): early jobs sent
after each tick's poll, the late job at the decision time. Every extraction must be bitwise identical in every field but the
timing field `extract_s` (`n_frames` included; arrays with NaN in the same places), and every decision time equal. Each
recording's closing poll is included, and every window decided at its cap.

So that every branch of the staged assembly runs, walk i follows policy i mod 4 (the policy changes only when early jobs are
sent and how long the harness waits for them, never what a worker computes): "wait" (the harness waits for each tick's early
jobs, so every final early result is used), "nowait" (no waiting: results not back by the decision time are computed late),
"eager" (no readiness probe, and waiting: stages are sent before their search can settle, so results that are not final are
discarded and sent again), "late frame" (one late frame simulated by the pool's own counter after the walk's windows open, so
the window uses no early result and no shortcut: the whole extraction is computed late).

Part A2 (synthetic cuts; B2 has no press within 6 s of the last): B2's first two identification recordings again, with an
extra press for every walk: at t0 + 3.4 s handed to the engine at t0 + 3.9 s (even walks), or at t0 + 2.5 s handed over at
t0 + 3.6 s (odd walks), as a key press reaching the app late would be. The press cuts the open window after some of its early
jobs were sent, so their results are no longer for the window's data end and are recomputed late.

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/identify/v5/staged/staged_exact.py [--recordings N] [--out PATH]

Development evaluation, all data seen; an identity check of the extraction, no figure.
"""

import json
import os
import sys
import time
import types
from concurrent.futures import wait as wait_all

import numpy as np

OUT = os.path.join("runs", "identify", "v5", "staged", "staged_exact.json")
OFFS = (0.15, 0.30)
STEP = 0.05
POLICIES = ("wait", "nowait", "eager", "late frame")


def run(recs, synthetic: bool, policy_of, log) -> dict:
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live import identify_engine as IE
    from runs.identify.v5.parallel.extract_exact import same
    man = json.load(open(os.path.join(EN.ENG, "models", "loso_B2_v5", "manifest.json")))
    T, amp_norm, alpha = EN.T_S, IT.gs_adopted(), man["alpha"]
    names = json.load(open(EN.DEV_NAMES))
    dmode = RP.direction_mode()

    def fresh(layout):
        ex = EN.Extractor(T, amp_norm, layout, names, alpha)
        return ex, {o: EN.Extractor(T, amp_norm, layout, names, alpha, rx=ex.rx, cut=False) for o in OFFS}

    stand = types.SimpleNamespace()                    # the pool's view of an engine: extractors, new_recording, push

    def new_recording(layout=None):
        stand.ex, stand.ex_off = fresh(layout or "id_spot")

    def push(L, frames):
        stand.ex.push(L, frames)
        for e in stand.ex_off.values():
            e.newest = stand.ex.newest
    stand.new_recording, stand.push = new_recording, push
    new_recording("id_spot")
    pool = IE.ExtractPool(stand, IE.EXTRACT_WORKERS_STAGED, staged=True)
    res = {"windows": 0, "identical": 0, "t_dec_equal": 0, "walks": 0, "closing_windows": 0, "cap_windows": 0,
           "cut_windows": 0, "early_jobs": 0, "late_frames_simulated": 0, "differences": [], "by_policy": {},
           "sources": {}, "early_used": {}, "early_tries_over_1": 0, "clean_windows": 0}
    for rec in recs:
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        exS, offS = fresh(layout)
        stand.new_recording(layout)
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        walks = sorted((float(q["t_start"]), q.get("path_name")) for q in gt["passes"])      # only these two fields
        del gt
        presses = []                                   # (handed over at, t0, path, walk number, policy)
        for j, (t0, path) in enumerate(walks):
            wid = res["walks"] + j
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else path
            pol = policy_of(wid)
            presses.append((t0, t0, known, wid, pol))
            if synthetic:
                cut, at = ((t0 + 3.4, t0 + 3.9) if j % 2 == 0 else (t0 + 2.5, t0 + 3.6))
                presses.append((at, cut, known, wid, pol))
        presses.sort(key=lambda p: p[0])
        res["walks"] += len(walks)
        pos = {L: 0 for L in EN.LINKS}
        t_first = min(float(fr[L]["t_mono"][0]) for L in EN.LINKS)
        t_last = max(float(fr[L]["t_mono"][-1]) for L in EN.LINKS)
        pi = 0
        pol_now, opened = "wait", None
        wins_of = {}                                   # id(window) -> (walk, policy)

        def compare(gs, gp, closing):
            for (ws, tds, xs), (wp, tdp, xp) in zip(gs, gp):
                xp.resolve()
                res["windows"] += 1
                bad = same(xs, dict(xp))
                res["identical"] += int(not bad)
                res["t_dec_equal"] += int(tds == tdp and ws["t0"] == wp["t0"])
                end = ws.get("end", ws["t0"] + T)
                res["closing_windows"] += int(closing)
                res["cap_windows"] += int(tds == end + EN.CAP_S)
                res["cut_windows"] += int("end" in ws)
                wid, pol = wins_of.get(id(wp), (None, "?"))
                b = res["by_policy"].setdefault(pol, {"windows": 0, "identical": 0})
                b["windows"] += 1
                b["identical"] += int(not bad)
                st = xp.staged
                res["clean_windows"] += int(st["clean"])
                how = st.get("how") or {}
                for k, v in [("dir", how.get("dir"))] + [(f"cp{k}", v) for k, v in (how.get("cp") or {}).items()]:
                    if v is not None:
                        res["sources"].setdefault(k, {}).setdefault(v, 0)
                        res["sources"][k][v] += 1
                for s_ in st["early_used"]:
                    res["early_used"][s_] = res["early_used"].get(s_, 0) + 1
                tries = st.get("early_tries") or {}
                res["early_tries_over_1"] += sum(1 for n in tries.values() if n > 1)
                if bad or tds != tdp:
                    res["differences"].append({"recording": os.path.basename(rec["stem"]), "t0": ws["t0"], "fields": bad,
                                               "t_dec": [tds, tdp], "policy": pol})

        for now in np.arange(t_first + STEP, t_last + STEP + 1e-9, STEP):
            while pi < len(presses) and presses[pi][0] <= now:
                _at, t0, known, wid, pol = presses[pi]
                for ex, offs in ((exS, offS), (stand.ex, stand.ex_off)):
                    ex.press(t0, path=known, layout=layout)
                    for o, e in offs.items():
                        e.press(t0 + o, path=known, layout=layout)
                for e in [stand.ex] + list(stand.ex_off.values()):
                    wins_of[id(e.pending[-1])] = (wid, pol)
                pol_now = pol
                if pol == "late frame" and _at == t0:   # the walk's own press (A2's extra presses never use this policy)
                    opened = wid
                pi += 1
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], now, side="right"))
                if n > pos[L]:
                    exS.push(L, fr[L][pos[L]:n])
                    stand.push(L, fr[L][pos[L]:n])
                    pos[L] = n
            for e in offS.values():
                e.newest = exS.newest
            gs = [g for e in [exS] + list(offS.values()) for g in e.poll(now)]
            gp = [g for e in [stand.ex] + list(stand.ex_off.values()) for g in e.poll(now)]
            assert len(gs) == len(gp), (os.path.basename(rec["stem"]), now, len(gs), len(gp))
            compare(gs, gp, False)
            res["early_jobs"] += pool.early(now, send=not gp, probe=(pol_now != "eager"))
            if opened is not None and any(id(w) in pool.windows for e in [stand.ex] + list(stand.ex_off.values())
                                          for w in e.pending):
                pool.late_frames += 1                  # the simulated late frame, after the walk's windows registered
                res["late_frames_simulated"] += 1
                opened = None
            if pol_now in ("wait", "eager"):
                wait_all([f for ent in pool.windows.values() for f in ent["jobs"].values()])
        gs = [g for e in [exS] + list(offS.values()) for g in e.poll(np.inf, closing=True)]
        gp = [g for e in [stand.ex] + list(stand.ex_off.values()) for g in e.poll(np.inf, closing=True)]
        assert len(gs) == len(gp)
        compare(gs, gp, True)
        log(f"{time.strftime('%H:%M:%S')} {os.path.basename(rec['stem'])}: {res['walks']} walks, {res['identical']} of "
            f"{res['windows']} windows identical, {res['early_jobs']} early jobs")
    pool.close()
    return res


def main(argv):
    from pipeline.identify import ide_replay as RP
    from pipeline.live import identify_engine as IE
    n_rec = int(argv[argv.index("--recordings") + 1]) if "--recordings" in argv else None
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT
    t_all = time.time()
    recs = RP.session_recordings("B2")
    A = run(recs[:n_rec], False, lambda wid: POLICIES[wid % len(POLICIES)], print)
    idcap = [r for r in recs if r["kind"] == "idcap"][:2]
    A2 = run(idcap, True, lambda wid: ("wait", "nowait")[wid % 2], print)
    full = n_rec is None
    need = {("dir", "early"), ("dir", "late"), ("cp0", "early"), ("cp0", "direction"), ("cp1", "early"), ("cp1", "late"),
            ("cp4", "decision time"), ("cp4", "late")}
    seen = {(k, v) for part in (A, A2) for k, d in part["sources"].items() for v in d}
    checks = {
        "A_all_windows": A["windows"] == 897 if full else None,
        "A_identical": A["identical"] == A["windows"],
        "A_t_dec_equal": A["t_dec_equal"] == A["windows"],
        "A2_identical": A2["identical"] == A2["windows"] and A2["t_dec_equal"] == A2["windows"],
        "A2_cut_windows": A2["cut_windows"] > 0,
        "branches_exercised": sorted(f"{k}:{v}" for k, v in need - seen) == [],
        "retries_after_not_final": (A["early_tries_over_1"] + A2["early_tries_over_1"]) > 0,
        "late_frame_fallback": A["late_frames_simulated"] > 0 and A["clean_windows"] < A["windows"],
    }
    res = {"label": "development evaluation, all data seen; an identity check of the extraction, no figure",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "code": os.path.abspath(IE.__file__),
           "workers": IE.EXTRACT_WORKERS_STAGED, "tick_s": STEP, "A": A, "A2": A2, "branches_needed": sorted(f"{k}:{v}" for k, v in need),
           "branches_missing": sorted(f"{k}:{v}" for k, v in need - seen), "checks": checks,
           "PASSED": bool(all(v for v in checks.values() if v is not None)), "seconds": round(time.time() - t_all, 1),
           "nice": os.nice(0), "threads": os.environ.get("OMP_NUM_THREADS")}
    for part in (A, A2):
        part["differences"] = part["differences"][:50]
    json.dump(res, open(out, "w"), indent=1, default=float)
    print(json.dumps({k: res[k] for k in ("checks", "branches_missing", "PASSED", "seconds")}
                     | {"A": {k: A[k] for k in ("walks", "windows", "identical", "closing_windows", "cap_windows", "cut_windows",
                                                "early_jobs", "sources")},
                        "A2": {k: A2[k] for k in ("windows", "identical", "cut_windows", "sources")}}, default=float), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
