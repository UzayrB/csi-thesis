"""Read-only profile of one window's extraction (Uzayr's go, 12 Oct; prompt_agent1_extraction_profile.md; rules in
QUEUE_STAGES.md beside this file). B2's first 4 recordings, fed as parallel/extract_exact.py feeds them; at each window's
decision time the frames are frozen as `ExtractPool._dispatch` freezes them, and the worker's path (`_extract_window_job`:
receivers rebuilt, an `Extractor`, three `Receiver.timed`, the engine's serial `Extractor.extract_v4`) is run here, in one
process, with self-time timers around the listed stages (installed on the modules in this process only; nothing under
pipeline/ changes). No Model or Session is loaded; nothing but frames, `t_start` and `path_name` is read from a recording.

    cd <Code> && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
        PYTHONPATH=. python3 runs/identify/v5/latency/stages/stage_profile.py run
    PYTHONPATH=. python3 runs/identify/v5/latency/stages/stage_profile.py report      # the report, from the JSON

Development evaluation, all data seen; timing only, no figure.
"""

import os

THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
for _k in THREAD_VARS:                       # before numpy, as in the workers
    os.environ[_k] = "1"

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.join("runs", "identify", "v5", "latency", "stages")
OUT = os.path.join(HERE, "stage_profile.json")
REPORT = os.path.join("reports", "identification", "2026-10-12_extraction-stages.md")
N_REC = 4
OFFS = (0.15, 0.30)
N_CHECK = 5
N_PAYLOAD = 20
PAYLOAD_EVERY = 7
TRIM_S = 21.0
REPEATS = 5

# the stages the prompt lists, then the extras this harness adds (each timed as self-time)
LISTED = ["Extractor.t_dec_end", "Extractor._raw", "engine.signal_measures", "engine.band_energy_rx2", "engine.detect_end",
          "engine.extract_window", "id19_bank._interp_cols", "conditioning.c2_hampel", "scipy.signal.stft",
          "id29_dc2_score.torso_hz", "idz_bank.conditioned_map_v2", "id19_featbank.pass_features",
          "pf.bandpass", "pf.reduce_link", "pf.cadence_estimates", "pf.resolve_cadence", "pf.rhythm_features",
          "pf.cycle_templates", "pf.spectral_shape", "pf.doppler_features", "pf.wavelet_features",
          "pf.modulation_features", "pf.profile_features", "pf.recsig_features"]
EXTRA = ["Receiver.timed", "rehearsal_doppler_check.conditioned_spectrogram"]
PF_FUNCS = ["bandpass", "reduce_link", "cadence_estimates", "resolve_cadence", "rhythm_features", "cycle_templates",
            "spectral_shape", "doppler_features", "wavelet_features", "modulation_features", "profile_features",
            "recsig_features"]


# ------------------------------------------------------------------ the timers

class Prof:
    def __init__(self):
        self.rec = None          # the current window's record; None: every wrapper passes straight through
        self.stack = []          # [name, child seconds]
        self.phase = "-"
        self.capture = None      # check mode: outputs of _raw and t_dec_end, in call order

    def add(self, name, phase, self_s, incl):
        for d in (self.rec["stages"], self.rec["by_phase"].setdefault(phase, {})):
            s = d.setdefault(name, [0.0, 0, 0.0])
            s[0] += self_s
            s[1] += 1
            s[2] += incl


P = Prof()


def wrap(name, fn, pre=None, post=None, phase=None, parents=None, on_out=None):
    def w(*a, **k):
        if P.rec is None or (parents is not None and (not P.stack or P.stack[-1][0] not in parents)):
            return fn(*a, **k)
        if pre is not None:
            pre(a)
        fr = [name, 0.0]
        P.stack.append(fr)
        ph = phase or P.phase                    # the phase at entry (after this stage's own pre)
        c0 = time.perf_counter()
        try:
            out = fn(*a, **k)
        finally:
            el = time.perf_counter() - c0
            P.stack.pop()
            if P.stack:
                P.stack[-1][1] += el
            P.add(name, ph, el - fr[1], el)
            if post is not None:
                post()
        if on_out is not None:
            on_out(a, out)
        return out
    w._orig = fn
    return w


def _W():
    return P.rec["_w"]


def pre_tdec(a):
    _self, t0, end = a[0], a[1], a[2]
    W = _W()
    i = W["n_tdec"]
    W["n_tdec"] += 1
    lab = "dir" if i == 0 else f"cp{end - t0:.2f}"
    P.phase = ("a:" if end < W["end"] - 1e-9 else "b:") + lab


def out_tdec(a, out):
    _W()["tdecs"].append([round(a[2] - a[1], 6), out])
    if P.capture is not None:
        P.capture.append(("t_dec_end", a[2] - a[1], out))


def pre_raw(a):
    if _W()["after_xw"]:
        P.phase = "b:speed"


def out_raw(a, out):
    if P.capture is not None:
        P.capture.append(("_raw", a[2] - a[1], a[3], out))


def pre_detect(a):
    P.phase = "b:detect"


def out_detect(a, out):
    _W()["detect"] = None if out is None else [float(out[0]), float(out[1])]


def pre_xw(a):
    P.phase = "b:extract_window"
    _W()["after_xw"] = True


_PF_SAVED = {}


def pf_on(a):
    from pipeline.identify import idmax_features as F
    for nm in PF_FUNCS:
        f = getattr(F, nm)
        _PF_SAVED[nm] = f
        setattr(F, nm, wrap("pf." + nm, f))


def pf_off():
    from pipeline.identify import idmax_features as F
    for nm, f in _PF_SAVED.items():
        setattr(F, nm, f)
    _PF_SAVED.clear()


_INSTALLED = []


def install():
    import scipy.signal as SS
    from pipeline.identify import engine as EN
    from pipeline.identify import conditioning as CO
    from pipeline.identify import id19_bank as B19
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import idz_bank as ZB
    from pipeline.identify import rehearsal_doppler_check as RD
    spec = [(EN.Extractor, "extract_v4", "Extractor.extract_v4", dict(phase="glue")),
            (EN.Extractor, "t_dec_end", "Extractor.t_dec_end", dict(pre=pre_tdec, on_out=out_tdec)),
            (EN.Extractor, "_raw", "Extractor._raw", dict(pre=pre_raw, on_out=out_raw)),
            (EN.Receiver, "timed", "Receiver.timed", {}),
            (EN, "signal_measures", "engine.signal_measures", {}),
            (EN, "band_energy_rx2", "engine.band_energy_rx2", {}),
            (EN, "detect_end", "engine.detect_end", dict(pre=pre_detect, on_out=out_detect)),
            (EN, "extract_window", "engine.extract_window", dict(pre=pre_xw)),
            (B19, "_interp_cols", "id19_bank._interp_cols", {}),
            (CO, "c2_hampel", "conditioning.c2_hampel", {}),
            (SS, "stft", "scipy.signal.stft",
             dict(parents={"rehearsal_doppler_check.conditioned_spectrogram", "id29_dc2_score.torso_hz"})),
            (RD, "conditioned_spectrogram", "rehearsal_doppler_check.conditioned_spectrogram", {}),
            (D, "torso_hz", "id29_dc2_score.torso_hz", {}),
            (ZB, "conditioned_map_v2", "idz_bank.conditioned_map_v2", {}),
            (FB, "pass_features", "id19_featbank.pass_features", dict(pre=pf_on, post=pf_off))]
    for obj, attr, name, kw in spec:
        orig = obj.__dict__[attr] if isinstance(obj, type) else getattr(obj, attr)
        setattr(obj, attr, wrap(name, orig, **kw))
        _INSTALLED.append((obj, attr, orig))


def uninstall():
    while _INSTALLED:
        obj, attr, orig = _INSTALLED.pop()
        setattr(obj, attr, orig)


# ------------------------------------------------------------------ the worker's path, here

def freeze(x, td):
    """Exactly `ExtractPool._dispatch`'s copy of the receivers at the decision time."""
    rx = {}
    for L, r in x.rx.items():
        k = int(np.searchsorted(r.tm, td, side="right"))
        rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
    return rx


def make_job(x, w, td):
    return {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
            "w": dict(w), "td": float(td), "rx": freeze(x, td)}


def worker_path(job):
    """`_extract_window_job`'s statements, timed in parts: (extraction, setup s, timed args s, extract_v4 s, total s)."""
    from pipeline.identify import engine as EN
    P.phase = "setup"
    c0 = time.perf_counter()
    rx = {}
    for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
        r = EN.Receiver()
        r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
        rx[L] = r
    e = EN.Extractor(job["T"], job["amp_norm"], job["layout"], job["names"], job["alpha"], rx=rx, cut=job["cut"])
    td = job["td"]
    c1 = time.perf_counter()
    P.phase = "b:timed_args"
    timed = [rx[L].timed(td) for L in EN.LINKS]
    c2 = time.perf_counter()
    ex = e.extract_v4(job["w"], td, timed)
    c3 = time.perf_counter()
    return ex, c1 - c0, c2 - c1, c3 - c2, c3 - c0


def new_rec(job):
    w = job["w"]
    return {"stages": {}, "by_phase": {},
            "_w": {"end": w.get("end", w["t0"] + job["T"]), "n_tdec": 0, "after_xw": False, "tdecs": [], "detect": None}}


def checks(job, ex):
    """Rule 2 and the duplicate-work facts, on one window: unwrapped against wrapped, and the repeated inputs compared."""
    from pipeline.identify import engine as EN
    from pipeline.identify.id19_bank import _interp_cols
    from runs.identify.v5.parallel.extract_exact import same
    uninstall()
    ex_u = worker_path(job)[0]               # unwrapped: every original function back in place
    install()
    bad = same(ex, dict(ex_u))
    P.rec, P.capture = new_rec(job), []
    worker_path(job)
    cap, P.rec, P.capture = P.capture, None, None
    raws = [c for c in cap if c[0] == "_raw"]
    tdecs = [c for c in cap if c[0] == "t_dec_end"]
    w, td = job["w"], job["td"]
    t0, end = w["t0"], w.get("end", w["t0"] + job["T"])
    full = end == t0 + job["T"]
    out = {"identical_wrapped_unwrapped": not bad, "fields_differing": bad, "window_full_length": bool(full)}
    if len(raws) >= 2 and abs(raws[0][1] - raws[1][1]) < 1e-9:
        out["dir_and_cp3.00_raw_equal"] = bool(raws[0][2] == raws[1][2] and np.array_equal(raws[0][3], raws[1][3]))
        out["dir_and_cp3.00_t_dec_equal"] = bool(tdecs[0][2] == tdecs[1][2])
    out["last_checkpoint_t_dec_equals_td"] = bool(tdecs[-1][2] == td) if abs(tdecs[-1][1] - (end - t0)) < 1e-9 else None
    if abs(raws[-2][1] - (end - t0)) < 1e-9:
        out["last_checkpoint_raw_equals_speed_raw"] = bool(np.array_equal(raws[-2][3], raws[-1][3]))
    if full and not job["amp_norm"]:
        rx = {}
        for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
            r = EN.Receiver()
            r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
            rx[L] = r
        grid = np.arange(t0, t0 + job["T"], 1.0 / EN.FS)
        A_xw = np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in [rx[L].timed(td) for L in EN.LINKS]],
                          np.float64)
        out["speed_raw_equals_extract_window_A_raw"] = bool(np.array_equal(raws[-1][3], A_xw))
    return out


def payload(job, ex):
    """Rule 4: bytes and pickle + unpickle seconds of the dispatch job, as sent and with frames trimmed to tm > t0 - 21 s."""
    import pickle
    from multiprocessing.reduction import ForkingPickler
    from runs.identify.v5.parallel.extract_exact import same
    t0 = job["w"]["t0"]
    trim = dict(job)
    trim["rx"] = {}
    for L, arrs in job["rx"].items():
        k = int(np.searchsorted(arrs[0], t0 - TRIM_S, side="right"))
        trim["rx"][L] = tuple(a[k:].copy() for a in arrs)
    res = {}
    for tag, j in (("full", job), ("trimmed", trim)):
        dt, lt = [], []
        for _ in range(REPEATS):
            c0 = time.perf_counter()
            b = bytes(ForkingPickler.dumps(j))
            c1 = time.perf_counter()
            pickle.loads(b)
            c2 = time.perf_counter()
            dt.append(c1 - c0)
            lt.append(c2 - c1)
        res[tag] = {"bytes": len(b), "frames": {L: int(len(a[0])) for L, a in j["rx"].items()},
                    "pickle_s": float(np.median(dt)), "unpickle_s": float(np.median(lt))}
    ex_t = worker_path(trim)[0]
    res["trimmed_extraction_identical"] = not same(ex, dict(ex_t))
    return res


# ------------------------------------------------------------------ the run

def run():
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    built = time.strftime("%Y-%m-%d %H:%M:%S")
    man = json.load(open(os.path.join(EN.ENG, "models", "loso_B2_v5", "manifest.json")))
    T, amp_norm, alpha = EN.T_S, IT.gs_adopted(), man["alpha"]       # the manifest's alpha only; no model is loaded
    names = json.load(open(EN.DEV_NAMES))
    dmode = RP.direction_mode()
    install()
    windows, n_walks, warmed = [], 0, [False]
    ctx = {}

    def hook(x, k):
        def extract_v4(w, td, _timed):
            job = make_job(x, w, td)
            if not warmed[0]:                # one untimed extraction first, as the workers warm at start
                worker_path(job)
                warmed[0] = True
            P.rec = new_rec(job)
            ex, setup_s, targs_s, v4_s, tot_s = worker_path(job)
            rec, P.rec = P.rec, None
            W = rec.pop("_w")
            i = len(windows)
            row = {"i": i, "recording": ctx["rec"], "walk": ctx["walk"], "window": k, "t0": w["t0"],
                   "window_s": W["end"] - w["t0"], "cut": "end" in w, "td_minus_t0": td - w["t0"],
                   "frames": {L: int(len(a[0])) for L, a in job["rx"].items()},
                   "setup_s": setup_s, "timed_args_s": targs_s, "extract_v4_s": v4_s, "worker_total_s": tot_s,
                   "extract_s": float(ex["extract_s"]), "tdecs": W["tdecs"], "detect": W["detect"],
                   "walk_end_s": float(ex["walk_end_s"]), "stages": rec["stages"], "by_phase": rec["by_phase"]}
            if i < N_CHECK:
                row["check"] = checks(job, ex)
            if i % PAYLOAD_EVERY == 0 and i // PAYLOAD_EVERY < N_PAYLOAD:
                row["payload"] = payload(job, ex)
            windows.append(row)
            return ex
        return extract_v4

    def fresh(layout):
        ex = EN.Extractor(T, amp_norm, layout, names, alpha)
        offs = {o: EN.Extractor(T, amp_norm, layout, names, alpha, rx=ex.rx, cut=False) for o in OFFS}
        ex.extract_v4 = hook(ex, 0)
        for j, (o, e) in enumerate(offs.items()):
            e.extract_v4 = hook(e, j + 1)
        return ex, offs

    recs = RP.session_recordings("B2")[:N_REC]
    for rec in recs:
        ctx["rec"] = os.path.basename(rec["stem"])
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        exS, offS = fresh(layout)
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        walks = [(float(q["t_start"]), q.get("path_name")) for q in gt["passes"]]     # only these two fields
        del gt
        for t0, path_name in sorted(walks, key=lambda z: z[0]):
            ctx["walk"] = n_walks
            lim = t0 + OFFS[-1] + T + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                exS.push(L, fr[L][pos[L]:n])
                pos[L] = n
            for e in offS.values():
                e.newest = exS.newest
            known = None if (rec["kind"] == "idcap" and dmode == "detected") else path_name
            exS.press(t0, path=known, layout=layout)
            for o, e in offS.items():
                e.press(t0 + o, path=known, layout=layout)
            got = [e.poll(lim) for e in [exS] + list(offS.values())]
            assert all(len(g) == 1 for g in got), (ctx["rec"], t0, [len(g) for g in got])
            n_walks += 1
        print(f"{time.strftime('%H:%M:%S')} {ctx['rec']} ({rec['kind']}): {n_walks} walks, {len(windows)} windows",
              flush=True)
    uninstall()
    res = {"label": "development evaluation, all data seen; timing only, no figure",
           "built": built, "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t_all, 1),
           "session": "B2", "recordings": [os.path.basename(r["stem"]) for r in recs],
           "kinds": [r["kind"] for r in recs], "direction_mode": dmode, "alpha": alpha, "amp_norm": bool(amp_norm),
           "T": T, "offsets": list(OFFS), "walks": n_walks, "n_windows": len(windows),
           "env": {k: os.environ.get(k) for k in THREAD_VARS}, "nice": os.nice(0), "pid": os.getpid(),
           "python": sys.version.split()[0], "numpy": np.__version__,
           "windows": windows}
    json.dump(res, open(OUT, "w"), indent=1)
    ok = n_walks == 47 and len(windows) == 141
    ident = all(w["check"]["identical_wrapped_unwrapped"] for w in windows if "check" in w)
    print(json.dumps({"walks": n_walks, "windows": len(windows), "RULE1": ok, "RULE2": ident, "seconds": res["seconds"]}),
          flush=True)


# ------------------------------------------------------------------ the report, from the JSON alone

OUTSIDE = ("setup", "b:timed_args")          # the worker's path outside extract_v4
PHASE_ORDER = ["a:dir", "a:cp3.00", "a:cp3.25", "a:cp3.50", "a:cp3.75", "b:dir", "b:cp3.00", "b:cp3.25", "b:cp3.50",
               "b:cp3.75", "b:cp4.00", "b:detect", "b:extract_window", "b:speed", "glue", "b:timed_args", "setup"]


def _ph(w, phase, name=None, k=0):
    d = w["by_phase"].get(phase, {})
    if name is None:
        return sum(v[k] for v in d.values()) if k != 2 else sum(v[0] for v in d.values())
    return d.get(name, [0.0, 0, 0.0])[k]


def _in_v4(w, name, k=0):
    return sum(d.get(name, [0.0, 0, 0.0])[k] for ph, d in w["by_phase"].items() if ph not in OUTSIDE)


def _md(x):
    return float(np.median(x))


def _p95(x):
    return float(np.percentile(x, 95))


def report():
    js = json.load(open(OUT))
    W = js["windows"]
    v4 = np.array([w["extract_v4_s"] for w in W])
    tot = np.array([w["worker_total_s"] for w in W])
    xs = np.array([w["extract_s"] for w in W])
    glue = np.array([_ph(w, "glue", "Extractor.extract_v4") for w in W])
    cover = 1.0 - glue / v4
    checks = [w["check"] for w in W if "check" in w]
    ident = sum(c["identical_wrapped_unwrapped"] for c in checks)
    L = []
    a = L.append
    a("# Extraction stages: a read-only profile of one window's extraction (12 Oct 2026)")
    a("")
    a(f"Development evaluation, all data seen; timing only, no figure. Generated by "
      f"`runs/identify/v5/latency/stages/stage_profile.py report` from `stage_profile.json` (run {js['built']} to "
      f"{js['finished']}, {js['seconds']} s). Uzayr's go in Agent1's chat (prompt_agent1_extraction_profile.md); the "
      f"Mastermind's slot 12 Oct 12:19:15; the rules are in `stages/QUEUE_STAGES.md`, written before the run. Nothing "
      f"under `pipeline/` changed, no Model or Session was loaded, and nothing but frames, `t_start` and `path_name` was "
      f"read from a recording.")
    a("")
    a("## 1. The run")
    a("")
    a(f"- B2's first {len(js['recordings'])} recordings ({', '.join(js['recordings'])}; kinds "
      f"{', '.join(sorted(set(js['kinds'])))}), fed as `parallel/extract_exact.py` feeds them: **{js['walks']} walks, "
      f"{js['n_windows']} windows** (the window at t0 and the offset windows at t0 + 0.15 and 0.30 s). Direction mode "
      f"{js['direction_mode']}, alpha {js['alpha']}, amp_norm {js['amp_norm']}, T {js['T']} s.")
    a(f"- One process, CPU only, nice {js['nice']}, {', '.join(f'{k}={v}' for k, v in js['env'].items())}; Python "
      f"{js['python']}, numpy {js['numpy']}. Each window's frames are frozen at its decision time exactly as "
      f"`ExtractPool._dispatch` freezes them, and the worker's path (`_extract_window_job`: receivers rebuilt, an "
      f"`Extractor`, three `Receiver.timed`, then the engine's serial `Extractor.extract_v4`) runs in this process with "
      f"self-time timers around the stages. One untimed extraction ran first, as the workers warm at start.")
    r1 = js["walks"] == 47 and js["n_windows"] == 141
    a(f"- **Rule 1 (count):** {js['walks']} walks and {js['n_windows']} windows against the prompt's 47 and 141: "
      f"{'PASSED' if r1 else 'FAILED'}." + ("" if r1 else
      " B2's first 4 recordings have 10 + 10 + 10 + 20 walks, and no 4 whole B2 recordings sum to 47. The job stopped "
      "before the report; Uzayr, in Agent1's chat on 12 Oct (noted at 12:29:45), accepted 50 walks and 150 windows (QUEUE_STAGES.md, "
      "\"After the run\"), and this report is generated from the saved JSON with no new compute."))
    a(f"- **Rule 2 (identity):** the wrapped extraction equals an unwrapped one (every original function back in place), "
      f"bitwise on every field but `extract_s`, on {ident} of {len(checks)} windows: "
      f"{'PASSED' if ident == len(checks) == 5 else 'FAILED'}.")
    a(f"- **Rule 3 (coverage):** the timed stages' self-times cover a median {100 * _md(cover):.1f} % of `extract_v4`'s "
      f"total (minimum {100 * cover.min():.1f} %); the rest is `extract_v4`'s own statements (the loop, `np.round`, "
      f"`np.searchsorted`, `best_link`, the dict update) and the timers' own cost: "
      f"{'PASSED' if _md(cover) >= 0.90 else 'NOT MET'}.")
    a("")
    a("The whole worker path, per window (median / p95, seconds):")
    a("")
    a("| | median | p95 |")
    a("|---|---|---|")
    for lab, x in (("worker path total (setup + timed arguments + extract_v4)", tot), ("extract_v4", v4),
                   ("extract_s (the engine's own timer, inside extract_window)", xs),
                   ("extract_v4 minus extract_s", v4 - xs),
                   ("setup (receivers rebuilt, Extractor made)", np.array([w["setup_s"] for w in W])),
                   ("timed arguments (three Receiver.timed at td)", np.array([w["timed_args_s"] for w in W]))):
        a(f"| {lab} | {_md(x):.4f} | {_p95(x):.4f} |")
    a("")
    a("For comparison, the 12 Oct confirmation run (`rig_timing_confirm_par2`) gives a last window's extraction in its "
      "worker of 0.307 s and `extract_s` of 0.104 s (medians, from the prompt). That run had three workers and the main "
      f"process (mps) running at once; this profile is one process alone. The totals are close ({_md(tot):.3f} s here "
      f"against 0.307 s there, {_md(xs):.3f} against 0.104 for `extract_s`), so the gap the prompt asks about, about 0.20 s "
      f"there, is {_md(v4 - xs):.3f} s here: the work in extract_v4 outside extract_window (sections 3 and 4).")
    a("")
    a("## 2. Each stage (self-time per window)")
    a("")
    a("Self-time: a stage's time minus the time of the timed stages it calls. `pf.*` are the functions called inside "
      "`id19_featbank.pass_features` (only there; `bandpass` and `reduce_link` outside it fall in their caller's "
      "self-time). `scipy.signal.stft` is timed only when called by `rehearsal_doppler_check.conditioned_spectrogram` "
      "(the direction and the end detector) or `id29_dc2_score.torso_hz` (the speed); the STFTs inside "
      "`pf.doppler_features` are in that stage. Share: the stage's self-time summed over all windows, over "
      "`extract_v4`'s total summed over all windows. Calls: median per window. Two stages are extras, not in the prompt's "
      "list: `Receiver.timed` and `conditioned_spectrogram`.")
    a("")
    a("| stage | median s | p95 s | share of extract_v4 | calls |")
    a("|---|---|---|---|---|")
    rows = []
    for nm in LISTED + EXTRA:
        x = np.array([_in_v4(w, nm) for w in W])
        c = np.array([_in_v4(w, nm, 1) for w in W])
        rows.append((nm, x, c))
    rows.append(("extract_v4's own statements (not timed)", glue, np.ones(len(W))))
    for nm, x, c in sorted(rows, key=lambda r: -r[1].sum()):
        extra = " (extra)" if nm in EXTRA else ""
        a(f"| `{nm}`{extra} | {_md(x):.4f} | {_p95(x):.4f} | {100 * x.sum() / v4.sum():.1f} % | {int(_md(c))} |")
    a("")
    # the dominant stage, by share
    top = sorted(rows, key=lambda r: -r[1].sum())[0]
    a(f"**Dominant stage:** `{top[0]}`, {100 * top[1].sum() / v4.sum():.1f} % of `extract_v4` "
      f"(median {_md(top[1]):.4f} s per window).")
    a("")
    a("Inclusive time of the larger callers (median s per window, inside extract_v4):")
    a("")
    a("| caller | inclusive median s | share |")
    a("|---|---|---|")
    for nm in ("engine.extract_window", "id19_featbank.pass_features", "Extractor.t_dec_end", "Extractor._raw",
               "engine.signal_measures", "engine.band_energy_rx2", "rehearsal_doppler_check.conditioned_spectrogram",
               "id29_dc2_score.torso_hz", "idz_bank.conditioned_map_v2"):
        x = np.array([_in_v4(w, nm, 2) for w in W])
        a(f"| `{nm}` | {_md(x):.4f} | {100 * x.sum() / v4.sum():.1f} % |")
    a("")
    a("## 3. Where the time goes, by phase of extract_v4")
    a("")
    a("Phases follow `extract_v4`'s order (engine.py lines 404 to 436): the direction on [t0, t0 + 3] (`dir`); the end "
      "detector's checkpoints at 3.0, 3.25, 3.5, 3.75 and 4.0 s (`cpX`, each a decision-time search `t_dec_end`, a "
      "re-interpolation `_raw` from t0, and RX2's band energy); the detector itself (`detect`); `extract_window` on the "
      "whole window; the speed on the walking span (`speed`: a fourth `_raw` and `torso_hz`). `a:` marks work whose "
      "inputs end before the window's end, `b:` work that needs data to the window's end. `glue` is extract_v4's own "
      "statements; `b:timed_args` and `setup` are the worker's path outside extract_v4.")
    a("")
    a("| phase | windows | median s | p95 s | share of worker total |")
    a("|---|---|---|---|---|")
    for ph in PHASE_ORDER:
        has = [w for w in W if ph in w["by_phase"]]
        if not has:
            continue
        x = np.array([_ph(w, ph) for w in W])
        a(f"| `{ph}` | {len(has)} | {_md(x):.4f} | {_p95(x):.4f} | {100 * x.sum() / tot.sum():.1f} % |")
    a("")
    A = np.array([sum(_ph(w, ph) for ph in w["by_phase"] if ph.startswith("a:")) for w in W])
    B = np.array([sum(_ph(w, ph) for ph in w["by_phase"] if ph.startswith("b:")) for w in W])
    G = glue
    S = np.array([_ph(w, "setup") for w in W])
    a("## 4. The (a)/(b) split")
    a("")
    a("(a) work whose inputs end before the window's end: the direction on its first 3 s and the checkpoints at 3.0, "
      "3.25, 3.5 and 3.75 s, with their decision-time searches and re-interpolations. (b) work that needs data to the "
      "window's end: the 4.0 s checkpoint, the detector, extract_window, the speed, and the worker's three "
      "`Receiver.timed` at td. A window cut short by the next press has its last checkpoint (and, if cut before 3 s, its "
      "direction) in (b).")
    a("")
    a("| part | median s | p95 s | median % of worker total | median % of extract_v4 |")
    a("|---|---|---|---|---|")
    for lab, x in (("(a) inputs end before the window's end", A), ("(b) needs data to the window's end", B),
                   ("extract_v4's own statements", G), ("setup", S)):
        inv4 = x if lab != "setup" else None
        a(f"| {lab} | {_md(x):.4f} | {_p95(x):.4f} | {100 * _md(x / tot):.1f} % | "
          f"{'' if inv4 is None else f'{100 * _md(x / v4):.1f} %'} |")
    a("")
    a(f"**(a) share:** median {100 * _md(A / tot):.1f} % of the worker path ({_md(A):.4f} s per window); "
      f"{100 * A.sum() / tot.sum():.1f} % of all windows' time summed.")
    a("")
    det = [w["detect"] for w in W]
    a("End detector (alpha 0.5): the checkpoint at which it fired, per window:")
    a("")
    a("| checkpoint s | windows | median walk end s |")
    a("|---|---|---|")
    for c in sorted({d[1] for d in det if d is not None}):
        sel = [d[0] for d in det if d is not None and d[1] == c]
        a(f"| {c:.2f} | {len(sel)} | {_md(sel):.3f} |")
    a(f"| none (walking span = whole window) | {sum(d is None for d in det)} | |")
    a("")
    a("## 5. Work done twice")
    a("")
    D1 = np.array([_ph(w, "a:cp3.00") for w in W])
    D3 = np.array([_ph(w, "b:cp4.00", "Extractor.t_dec_end", 2) for w in W])
    D4a = np.array([_ph(w, "b:cp4.00", "Extractor._raw", 2) for w in W])
    D4b = np.array([_ph(w, "b:speed", "Extractor._raw", 2) for w in W])
    D5 = np.array([_ph(w, "b:extract_window", "engine.signal_measures", 2) for w in W])
    full = [c for c in checks if c.get("window_full_length")]
    a("Each item is checked on the identity windows (rule 2's five) where stated; the times are medians per window "
      "over all windows.")
    a("")
    a("| repeated work | repeats | median s | check on the 5 identity windows |")
    a("|---|---|---|---|")
    a(f"| the 3.0 s checkpoint: `t_dec_end(t0, t0 + 3)`, `_raw(t0, t0 + 3)` and RX2's conditioned spectrogram, all "
      f"already computed for the direction (lines 412 and 419) | the whole `a:cp3.00` phase | {_md(D1):.4f} | "
      f"raw equal {sum(bool(c.get('dir_and_cp3.00_raw_equal')) for c in checks)} of {len(checks)}, decision time "
      f"equal {sum(bool(c.get('dir_and_cp3.00_t_dec_equal')) for c in checks)} of {len(checks)} |")
    a(f"| the 4.0 s checkpoint's `t_dec_end(t0, end)`: the engine's own decision search, already done to schedule "
      f"the window (its result is td) | inclusive | {_md(D3):.4f} | equals td "
      f"{sum(bool(c.get('last_checkpoint_t_dec_equals_td')) for c in checks)} of {len(checks)} |")
    a(f"| the whole window re-interpolated three times: the 4.0 s checkpoint's `_raw`, extract_window's `A_raw` and the "
      f"speed's `_raw` (line 427), each with three `Receiver.timed` at td that the worker already made | two of the "
      f"three (`b:cp4.00` and `b:speed` `_raw`, inclusive) | {_md(D4a + D4b):.4f} | 4.0 s raw equals speed raw "
      f"{sum(bool(c.get('last_checkpoint_raw_equals_speed_raw')) for c in checks)} of {len(checks)}; speed raw "
      f"equals extract_window's A_raw {sum(bool(c.get('speed_raw_equals_extract_window_A_raw')) for c in full)} of "
      f"{len(full)} full-length |")
    a(f"| extract_window's own `signal_measures` on the whole window (line 318: a direction spectrogram and "
      f"`torso_hz`): every key it returns is overwritten by extract_v4's update (line 432) | inclusive, discarded | "
      f"{_md(D5):.4f} | by the code |")
    a("")
    dup = D1 + D3 + D4a + D4b + D5
    a(f"Together: median {_md(dup):.4f} s per window ({100 * _md(dup / v4):.1f} % of extract_v4). Not counted above: "
      f"the checkpoints at 3.25, 3.5, 3.75 and 4.0 s each restart from t0, so each repeats the previous checkpoint's "
      f"search and interpolation over [t0, t0 + c - 0.25] and recomputes RX2's spectrogram over the whole prefix "
      f"(checkpoints 3.25 to 4.0 together: median "
      f"{_md(np.array([sum(_ph(w, p) for p in ('a:cp3.25', 'a:cp3.50', 'a:cp3.75', 'b:cp3.25', 'b:cp3.50', 'b:cp3.75', 'b:cp4.00')) for w in W])):.4f} s).")
    a("")
    a("## 6. The dispatch payload")
    a("")
    pw = [w for w in W if "payload" in w]
    a(f"{len(pw)} windows (every {PAYLOAD_EVERY}th). Bytes: `multiprocessing.reduction.ForkingPickler.dumps` of the job "
      f"`ExtractPool._dispatch` submits; pickle and unpickle: median of {REPEATS} repeats per window, then median and "
      f"maximum over windows. Trimmed: each link's frames cut to tm > t0 - {TRIM_S:.0f} s (measured only; nothing in the "
      f"app changed).")
    a("")
    a("| payload | frames per link (median) | MB (median) | MB (max) | pickle s | unpickle s | pickle + unpickle s (max) |")
    a("|---|---|---|---|---|---|---|")
    for tag in ("full", "trimmed"):
        fpl = [_md(list(w["payload"][tag]["frames"].values())) for w in pw]
        mb = np.array([w["payload"][tag]["bytes"] / 1e6 for w in pw])
        pk = np.array([w["payload"][tag]["pickle_s"] for w in pw])
        up = np.array([w["payload"][tag]["unpickle_s"] for w in pw])
        a(f"| {tag} | {_md(fpl):.0f} | {_md(mb):.2f} | {mb.max():.2f} | {_md(pk):.4f} | {_md(up):.4f} | "
          f"{(pk + up).max():.4f} |")
    a("")
    nt = sum(bool(w["payload"]["trimmed_extraction_identical"]) for w in pw)
    a(f"The extraction from the trimmed frames equalled the untrimmed one, bitwise on every field but `extract_s`, on "
      f"{nt} of {len(pw)} windows; the JSON records only equal or not. By the code, the field `n_frames` (engine.py line "
      f"321) counts every frame in the buffer, so it differs whenever trimming removes frames. A spot check after the run "
      f"(a one-off script, not kept, 12 Oct about 12:30, on windows 0 and 7 of the first recording, the first two payload "
      f"windows) found window 0 equal (its buffer was under 21 s old) and window 7 different in `n_frames` only. The "
      f"other {len(pw) - nt - 1} differing windows were not checked field by field.")
    a("")
    a("## 7. Notes")
    a("")
    a("- Every second here is one process alone on an otherwise quiet machine; in the app three workers and the main "
      "process share the CPU, so absolute times there can differ (section 1 compares the totals). Shares and the (a)/(b) "
      "split are the transferable facts.")
    a("- The timers add a small cost per call (a few microseconds); it falls in the caller's self-time, and in "
      "`extract_v4`'s own statements.")
    a("- This report proposes nothing and the app is unchanged.")
    a("")
    open(REPORT, "w", encoding="utf-8").write("\n".join(L))
    print(REPORT)
    print(json.dumps({"dominant": top[0], "dominant_share": round(100 * top[1].sum() / v4.sum(), 1),
                      "a_median_pct_worker": round(100 * _md(A / tot), 1), "a_median_s": round(_md(A), 4),
                      "coverage_median": round(100 * _md(cover), 1), "identity": f"{ident}/{len(checks)}"}))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "report":
        report()
    else:
        raise SystemExit(sys.argv[1])
