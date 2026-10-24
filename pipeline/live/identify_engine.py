# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Identification mode, live: the one-press engine (pipeline/identify/engine.py) and nothing else.

from __future__ import annotations

import json
import os
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACT_WORKERS_V5 = 3
EXTRACT_WORKERS_STAGED = 4
EXTRACT_MODE_V5 = "staged"
EXTRACT_HELP = (f"engine v5: worker processes for the windows' extraction (default {EXTRACT_WORKERS_STAGED} staged, "
                f"{EXTRACT_WORKERS_V5} pool); 0 = serial extraction, the safe fallback (identical decisions, slower); a v4 model "
                "always extracts serially")
EXTRACT_MODE_HELP = ("engine v5: staged (the default: early jobs while each window is open, a late job at its decision time) or "
                     "pool (one job per window, as shipped on 12 Oct); identical decisions either way")
OUT_DIR = os.path.join(REPO_ROOT, "runs", "live", "identify")
ROUND_TRIP_S = 15.0
CHUNK_S = 0.25
DIR_WORD = {"A_fwd": "away", "A_rev": "towards"}


# P1 to P6 -> the participants' names.
def code_names() -> dict:
    from pipeline.identify.common import SIX, anon
    return {anon(n): n for n in SIX}


# Function model dir.
def model_dir(name: str) -> str:
    return os.path.join(REPO_ROOT, "runs", "identify", "engine", "models", name)


NUMBER_WORDS = {5: "five", 8: "eight", 9: "nine"}


# The deployment model's name: the newest engine's that is built (v5s deploy_all5_v5s, then v5...
def deployment_model() -> str:
    from pipeline.identify import engine as EN
    for name in ("deploy_all5_v5n", "deploy_all5_v5s", "deploy_all5_v5", EN.model_name("deploy_all5"), "deploy_all5_x"):
        if os.path.exists(os.path.join(model_dir(name), "manifest.json")):
            return name
    return "deploy_all5"


# (model directory, manifest) of the deployment model; refuses unless the manifest is complete.
def load_deployment() -> tuple:
    d = model_dir(deployment_model())
    p = os.path.join(d, "manifest.json")
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: no deployment manifest at {p} (train it: python3 -m pipeline.identify.ide_train deploy_all5)")
    man = json.load(open(p))
    for k in ("model", "gs_adopted", "T_s", "config", "code_commit_at_training"):
        if k not in man:
            raise SystemExit(f"REFUSED: the manifest lacks {k}")
    return d, man


# Function direction mode.
def direction_mode() -> str:
    from pipeline.identify import ide_replay as RP
    old = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        return RP.direction_mode()
    finally:
        os.chdir(old)


RIG_LAYOUTS = ("home", "id_spot")
SPACE_REFUSED = ("SPACE refused: with RX2 at home the direction detector is not validated (runs/identify/engine/checks/"
                 "direction_home.json); press a (away from the TX) or t (towards it) as the walker starts on line A")
POPUP_SOURCE = "popup"
POPUP_REFUSED = ("SPACE refused: no path picked. Click the walk's path on the map window (one click gives its line and "
                 "direction), then press SPACE here; a / t start a line-A walk (away from / towards the TX)")
POPUP_PICK_M = 0.4
POPUP_LANE_M = 0.18


PATHS_FILE = os.path.join(REPO_ROOT, "runs", "public_model", "tracking_paths.json")


# {path name: (start, end)} in name order, from the tracking sidecars (every *_walk.gt.json of the recorded...
def tracking_paths(root: str = None) -> dict:
    import glob
    root = root or os.path.join(REPO_ROOT, "data")
    files = sorted(glob.glob(os.path.join(root, "room_*", "session_*", "*_walk.gt.json")))
    if not files and os.path.exists(PATHS_FILE):
        with open(PATHS_FILE, encoding="utf-8") as fh:
            return {k: (tuple(v[0]), tuple(v[1])) for k, v in sorted(json.load(fh)["paths"].items())}
    geo = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            passes = json.load(fh).get("passes", [])
        for p in passes:
            ac = json.loads(p["anchor_coords"]) if isinstance(p["anchor_coords"], str) else p["anchor_coords"]
            se = (tuple(float(v) for v in ac[0]), tuple(float(v) for v in ac[-1]))
            if geo.setdefault(p["path_name"], se) != se:
                raise SystemExit(f"REFUSED: the tracking sidecars disagree on {p['path_name']}: {geo[p['path_name']]} and "
                                 f"{se} ({f})")
    if len(geo) != 12:
        raise SystemExit(f"REFUSED: {len(geo)} paths in the {len(files)} tracking sidecars under {root}, not twelve")
    return {k: geo[k] for k in sorted(geo)}


_SCREEN_PATHS = {}


# Tracking_paths(), read once per process (the screen and the pop-up draw from it).
def screen_paths() -> dict:
    if not _SCREEN_PATHS:
        _SCREEN_PATHS.update(tracking_paths())
    return _SCREEN_PATHS


# The path as the map draws it: moved POPUP_LANE_M to its own left when its reverse is also offered (so a...
def lane_of(path: str, paths: dict) -> tuple:
    s, e = (np.asarray(x, float) for x in paths[path])
    u = (e - s) / max(float(np.hypot(*(e - s))), 1e-9)
    both = any(tuple(paths[path][1]) == tuple(s2) and tuple(paths[path][0]) == tuple(e2) for s2, e2 in paths.values())
    off = POPUP_LANE_M * np.array([-u[1], u[0]]) if both else np.zeros(2)
    return s + off, e + off


# A path drawn as an arrow from its start to its end, inset metres in from both ends (line A's arrow as before).
def path_arrow(start, end, inset: float = 0.3) -> tuple:
    a, b = np.asarray(start, float), np.asarray(end, float)
    u = (b - a) / max(float(np.hypot(*(b - a))), 1e-9)
    return tuple(a + inset * u), tuple(b - inset * u)


# The direction on the boards for a layout: at the identification spot as before (direction_mode...
def direction_mode_for(layout: str) -> str:
    if layout == "id_spot":
        return direction_mode()
    p = os.path.join(REPO_ROOT, "runs", "identify", "engine", "checks", "direction_home.json")
    if not os.path.exists(p):
        return "recorded"
    return "detected" if json.load(open(p))["RULE_detected_used"] else "recorded"


# The rig's device: --device if given, else mps for an engine v5 model and cpu for any other model (v4...
def rig_device(md: str, device: str = None) -> str:
    if device is None:
        p = os.path.join(md, "manifest.json")
        version = json.load(open(p)).get("engine_version", 4) if os.path.exists(p) else 4
        device = "mps" if int(version) >= 5 else "cpu"
    if device == "mps":
        import torch
        if not torch.backends.mps.is_available():
            raise SystemExit("REFUSED: --device mps (engine v5's default) but this machine has no MPS; pass --device cpu "
                             "(not real time: the adaptation reaches about 6 s a walk)")
    return device


# A worker of engine v5's parallel extraction.
def _extract_worker_init(amp_norm: bool, names: list) -> None:
    from pipeline.identify import engine as EN
    from pipeline.identify import id19_bank, id19_featbank, id29_dc2_score, idmax_features, idz_bank
    from pipeline.identify import rehearsal_doppler_check
    t = np.arange(0.0, 4.6, 1.0 / EN.FS)
    rng = np.random.default_rng(0)
    timed = [(t, (rng.random((len(t), 103)) + 1.0).astype(np.float32), np.zeros(len(t), np.float32)) for _ in EN.LINKS]
    try:
        EN.extract_window(timed, 0.0, 4.0, amp_norm, "A_fwd", "id_spot", names)
    except Exception:
        pass


# One window, in a worker: the engine's own Extractor.extract_v4 on a frozen copy of the receivers (each...
def _extract_window_job(job: dict) -> tuple:
    from pipeline.identify import engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    rx = e.rx
    td = job["td"]
    _check_receivers(rx, float(job["w"]["t0"]), min(float(td), float(job["w"]["t0"]) + float(job["T"])))
    ex = e.extract_v4(job["w"], td, [rx[L].timed(td) for L in EN.LINKS])
    return ex, s, time.time(), os.getpid()


# A window without usable frames from a receiver (it stopped sending): the walk cannot be identified.
class SilentReceiver(RuntimeError):
    pass


# A walk pressed as the run stopped: the data of every receiver ends before its window has a second of it...
class DataEnded(SilentReceiver):
    pass


SILENT_GAP_S = 1.0


# Raise SilentReceiver when a receiver's frames do not cover [t0, end]: fewer than two frames in it, or a...
def _check_receivers(rx: dict, t0: float, end: float) -> None:
    newest = max((float(np.asarray(rx[L].tm, float)[-1]) for L in rx if len(rx[L].tm)), default=-np.inf)
    if newest < end and newest - t0 < SILENT_GAP_S:
        raise DataEnded(f"the data ended {max(newest - t0, 0.0):.1f} s into its window (the run stopped, or every "
                        f"receiver went silent)")
    end = min(end, newest)
    for L in sorted(rx):
        r = rx[L]
        tm = np.asarray(r.tm, float)
        tm = tm[(tm >= t0) & (tm <= end)]
        if len(tm) < 2:
            raise SilentReceiver(f"{L} sent {len(tm)} frames in the window ({t0:.2f} to {end:.2f} s)")
        gap = max(float(tm[0] - t0), float(end - tm[-1]), float(np.max(np.diff(tm))))
        if gap > SILENT_GAP_S:
            raise SilentReceiver(f"{L} was silent for {gap:.1f} s inside the window ({t0:.2f} to {end:.2f} s)")


# An Extractor on a job's frozen copy of the receivers, as _extract_window_job builds it.
def _frozen_extractor(job: dict):
    from pipeline.identify import engine as EN
    v5n = bool(job.get("v5n"))
    rx = {}
    for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
        r = EN.V5NReceiver() if v5n else EN.Receiver()
        r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
        rx[L] = r
    X = EN.V5NExtractor if v5n else EN.Extractor
    return X(job["T"], job["amp_norm"], job["layout"], job["names"], job["alpha"], rx=rx, cut=job["cut"])


# The end detector's checkpoints, exactly as Extractor.extract_v4 makes them.
def _checkpoints(e) -> np.ndarray:
    from pipeline.identify import engine as EN
    return np.round(np.arange(EN.DIR_T_S, e.T + 1e-9, EN.DET_STEP_S), 2)


# Engine v5's staged extraction, an early job: one stage of a window whose data ends before the window's...
def _early_job(job: dict) -> tuple:
    from pipeline.identify import engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    w, frz, stage = job["w"], job["frozen_at"], job["stage"]
    t0, end = w["t0"], e._end(w)
    cs = _checkpoints(e)
    if stage == "dir":
        e3 = min(t0 + EN.DIR_T_S, end)
        td3 = e.t_dec_end(t0, e3)
        if not td3 <= frz:
            return None, s, time.time(), os.getpid()
        raw3 = e._raw(t0, e3, td3)
        out = {"e3": e3, "td3": td3, "sm3": EN.signal_measures(raw3, w["path"], w["layout"]), "cp": {}}
        if e.alpha is not None and len(cs):
            ec = min(t0 + cs[0], end)
            if ec == e3:
                out["cp"][0] = (ec, (float(ec - t0), EN.band_energy_rx2(raw3[1])))
        return out, s, time.time(), os.getpid()
    c = cs[stage]
    ec = min(t0 + c, end)
    tdc = e.t_dec_end(t0, ec)
    if not tdc <= frz:
        return None, s, time.time(), os.getpid()
    return {"cp": {stage: (ec, (float(ec - t0), EN.band_energy_rx2(e._raw(t0, ec, tdc)[1])))}}, s, time.time(), os.getpid()


# Extractor.extract_v4's statements in its order, each stage taken from early when that result is for the...
def _staged_extract_v4(e, w: dict, td: float, timed: list, early: dict, td_is_search: bool) -> tuple:
    from pipeline.identify import engine as EN
    from pipeline.identify import id29_dc2_score as D
    how = {"dir": "late", "cp": {}}
    t0, end = w["t0"], e._end(w)
    layout = w["layout"]
    e3 = min(t0 + EN.DIR_T_S, end)
    d3 = early.get("dir")
    raw3 = None
    if d3 is not None and d3["e3"] == e3:
        sm3 = d3["sm3"]
        how["dir"] = "early"
    else:
        raw3 = e._raw(t0, e3, e.t_dec_end(t0, e3))
        sm3 = EN.signal_measures(raw3, w["path"], layout)
    path = sm3["path"]
    walk_end = end
    A = None
    if e.alpha is not None:
        series = []
        cp = early.get("cp", {})
        for k, c in enumerate(_checkpoints(e)):
            ec = min(t0 + c, end)
            hit = cp.get(k)
            if hit is not None and hit[0] == ec:
                series.append(hit[1])
                how["cp"][k] = "early"
            elif raw3 is not None and ec == e3:
                series.append((float(ec - t0), EN.band_energy_rx2(raw3[1])))
                how["cp"][k] = "direction"
            elif td_is_search and ec == end:
                A = e._raw(t0, end, td)
                series.append((float(ec - t0), EN.band_energy_rx2(A[1])))
                how["cp"][k] = "decision time"
            else:
                series.append((float(ec - t0), EN.band_energy_rx2(e._raw(t0, ec, e.t_dec_end(t0, ec))[1])))
                how["cp"][k] = "late"
            if ec < t0 + c:
                break
        d = EN.detect_end(series, e.alpha, upto=e.T)
        if d is not None:
            walk_end = min(t0 + d[0], end)
    if isinstance(e, EN.V5NExtractor):
        return e.window(w, timed, path, sm3, walk_end), how
    T_win = e.T if end == t0 + e.T else end - t0
    x = EN.extract_window(timed, t0, T_win, e.amp_norm, path, layout, e.names)
    if A is None:
        A = e._raw(t0, end, td)
    li, F = EN.best_link(path, layout)
    nw = int(np.searchsorted(np.arange(t0, end, 1.0 / EN.FS), walk_end, side="left"))
    ft = D.torso_hz(A[li][:nw]) if nw >= 64 else float("nan")
    v = float(ft * EN.LAMBDA / (2.0 * F)) if (F >= EN.F_MIN and np.isfinite(ft)) else float("nan")
    x.update({"path": path, "dir_detected": sm3["dir_detected"], "dir_slope": sm3["dir_slope"], "speed_link": EN.LINKS[li],
              "speed_F": F, "f_torso": ft, "wifi_speed": v, "walk_end_s": walk_end - t0, "alpha": e.alpha,
              "window_s": end - t0})
    return x, how


# Engine v5's staged extraction, the late job: the window at its decision time on a frozen copy of the...
def _late_job(job: dict) -> tuple:
    from pipeline.identify import engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    td = job["td"]
    _check_receivers(e.rx, float(job["w"]["t0"]), min(float(td), float(job["w"]["t0"]) + float(job["T"])))
    ex, how = _staged_extract_v4(e, job["w"], td, [e.rx[L].timed(td) for L in EN.LINKS], job["early"], job["td_is_search"])
    return ex, s, time.time(), os.getpid(), how


# Engine v5's parallel extraction: a window's extraction while its worker runs.
class PendingExtraction(dict):

    # Sets up the object.
    def __init__(self, fut, sent: float, staged: dict = None):
        super().__init__()
        self.fut, self.sent, self.worker, self.waited_s = fut, sent, None, None
        self.staged = staged

    # Function resolve.
    def resolve(self) -> "PendingExtraction":
        if self.fut is not None:
            c0 = time.time()
            got = self.fut.result()
            self.waited_s = time.time() - c0
            ex, s, e, pid = got[:4]
            self.update(ex)
            self.worker = {"start": s, "end": e, "pid": pid}
            if self.staged is not None:
                self.staged["how"] = got[4]
            self.fut = None
        return self


# Engine v5's parallel window extraction: a pool of n worker processes, made once and warmed at app start...
class ExtractPool:

    THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")

    # Sets up the object.
    def __init__(self, engine, n: int = EXTRACT_WORKERS_V5, staged: bool = False):
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        for k in self.THREAD_VARS:
            os.environ[k] = "1"
        self.e, self.n, self.staged = engine, int(n), bool(staged)
        x = engine.ex
        self.pool = ProcessPoolExecutor(max_workers=self.n, mp_context=mp.get_context("spawn"),
                                        initializer=_extract_worker_init, initargs=(x.amp_norm, x.names))
        list(self.pool.map(time.sleep, [0.5] * self.n))
        self.windows = {}
        self.polled = -np.inf
        self.late_frames = 0
        self.hook()
        new_recording = engine.new_recording

        # Function renewed.
        def renewed(layout=None):
            new_recording(layout)
            self.windows, self.polled = {}, -np.inf
            self.hook()
        engine.new_recording = renewed
        if self.staged:
            push = engine.push

            # Function pushed.
            def pushed(link, frames):
                if len(frames) and float(np.min(frames["t_mono"])) <= self.polled:
                    self.late_frames += 1
                push(link, frames)
            engine.push = pushed

    # Function hook.
    def hook(self) -> None:
        for x in [self.e.ex] + list(self.e.ex_off.values()):
            if not getattr(x, "_pooled", False):
                x.extract_v4 = self._late(x) if self.staged else self._dispatch(x)
                x._pooled = True

    # Each receiver's frames that had arrived by upto, copied (_dispatch's copy).
    @staticmethod
    def _freeze(x, upto: float) -> dict:
        rx = {}
        for L, r in x.rx.items():
            k = int(np.searchsorted(r.tm, upto, side="right"))
            rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
        return rx

    # Function dispatch.
    def _dispatch(self, x):
        # Function extract v4.
        def extract_v4(w, td, _timed):
            from pipeline.identify import engine as EN
            rx = {}
            for L, r in x.rx.items():
                k = int(np.searchsorted(r.tm, td, side="right"))
                rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
            job = {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
                   "w": dict(w), "td": float(td), "rx": rx, "v5n": isinstance(x, EN.V5NExtractor)}
            return PendingExtraction(self.pool.submit(_extract_window_job, job), time.time())
        return extract_v4

    # Function job.
    def _job(self, x, w: dict, rx: dict) -> dict:
        from pipeline.identify import engine as EN
        return {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
                "w": dict(w), "rx": rx, "v5n": isinstance(x, EN.V5NExtractor)}

    # Staged: the window's late job at its decision time, with the early results that are done and final.
    def _late(self, x):
        # Function extract v4.
        def extract_v4(w, td, _timed):
            c0 = time.time()
            ent = self.windows.pop(id(w), None)
            clean = ent is None or ent["late_frames"] == self.late_frames
            early, used, tries = {}, [], {}
            if ent is not None:
                tries = {str(k): n for k, n in ent["tries"].items()}
                for stage, fut in ent["jobs"].items():
                    if clean and fut.done() and not fut.cancelled() and fut.exception() is None:
                        res = fut.result()[0]
                        if res is not None:
                            used.append(str(stage))
                            if stage == "dir":
                                early["dir"] = {k: res[k] for k in ("e3", "td3", "sm3")}
                            early.setdefault("cp", {}).update(res["cp"])
            job = self._job(x, w, self._freeze(x, td))
            job.update({"td": float(td), "early": early, "td_is_search": bool(clean)})
            info = {"clean": bool(clean), "early_used": used, "early_tries": tries,
                    "early_sent": None if ent is None else {str(k): v for k, v in ent["sent"].items()}}
            fut = self.pool.submit(_late_job, job)
            sent = time.time()
            info["dispatch_s"] = sent - c0
            return PendingExtraction(fut, sent, staged=info)
        return extract_v4

    # Staged, after each finite poll: every open window's early stages whose data has ended by now and that have...
    def early(self, now: float, send: bool = True, probe: bool = True) -> int:
        from pipeline.identify import engine as EN
        if not np.isfinite(now):
            return 0
        self.polled = max(self.polled, float(now))
        sent = 0
        frozen = {}
        for x in [self.e.ex] + list(self.e.ex_off.values()):
            if not x.pending:
                continue
            cs = _checkpoints(x)
            stages = [("dir", EN.DIR_T_S)] + ([(k, cs[k]) for k in range(1, len(cs))] if x.alpha is not None else [])
            for w in x.pending:
                ent = self.windows.get(id(w))
                if ent is None:
                    ent = self.windows[id(w)] = {"w": w, "late_frames": self.late_frames, "jobs": {}, "final": set(),
                                                 "tries": {}, "sent": {}}
                if not send or ent["late_frames"] != self.late_frames:
                    continue
                t0, end = w["t0"], x._end(w)
                for stage, c in stages:
                    edge = min(t0 + c, end)
                    if edge >= end or now < edge or stage in ent["final"]:
                        continue
                    fut = ent["jobs"].get(stage)
                    if fut is not None:
                        if not fut.done():
                            continue
                        if not fut.cancelled() and fut.exception() is None and fut.result()[0] is not None:
                            ent["final"].add(stage)
                            continue
                    if probe and not all(r.last_time(now) > edge for r in x.rx.values()):
                        continue
                    if id(x.rx) not in frozen:
                        frozen[id(x.rx)] = self._freeze(x, now)
                    job = self._job(x, w, frozen[id(x.rx)])
                    job.update({"frozen_at": float(now), "stage": stage})
                    ent["jobs"][stage] = self.pool.submit(_early_job, job)
                    ent["tries"][stage] = ent["tries"].get(stage, 0) + 1
                    ent["sent"].setdefault(stage, []).append(float(now))
                    sent += 1
        return sent

    # Function close.
    def close(self) -> None:
        self.pool.shutdown(wait=True)


# Engine v5 in the app: the engine's Session, with each walk's add (the walk joins the pool and the AdaBN...
class AfterDecision:

    # Sets up the object.
    def __init__(self, session, write_pending):
        self._s, self._write_pending = session, write_pending
        self._pending = None
        self.settles = []

    # Function getattr.
    def __getattr__(self, k):
        return getattr(self._s, k)

    # The number of items.
    def __len__(self):
        return len(self._s) + (self._pending is not None)

    # Function add.
    def add(self, ex: dict) -> None:
        assert self._pending is None
        self._pending = ex

    # The held walk joins the pool.
    def settle(self, trigger: str = "poll") -> bool:
        if self._pending is None:
            return False
        if trigger == "classify":
            self._write_pending()
        ex, self._pending = self._pending, None
        w0 = time.time()
        self._s.add(ex)
        self.settles.append({"trigger": trigger, "wall_start": w0, "wall_end": time.time(), "update_s": self._s.update_s[-1]})
        return True

    # Function classify.
    def classify(self, ex: dict) -> dict:
        self.settle("classify")
        if isinstance(ex, PendingExtraction):
            ex.resolve()
        return self._s.classify(ex)


# The app's logic around one engine: presses, decisions, round trip, walker tally, JSON lines.
class EngineApp:

    # Sets up the object.
    def __init__(self, engine, model_name: str, replay: bool, jsonl: str = None, dmode: str = "detected",
                 extract_workers: int = None, extract_mode: str = None):
        self.e, self.model_name, self.replay, self.dmode = engine, model_name, replay, dmode
        self.v5 = bool(getattr(engine, "v5", False))
        self.written = 0
        self.extract_pool = None
        if self.v5:
            engine.session = AfterDecision(engine.session, self._write_pending)
            mode = extract_mode or EXTRACT_MODE_V5
            if mode not in ("staged", "pool"):
                raise ValueError(f"extract_mode {mode!r}: staged or pool")
            default = EXTRACT_WORKERS_STAGED if mode == "staged" else EXTRACT_WORKERS_V5
            n = default if extract_workers is None else int(extract_workers)
            if n > 0:
                self.extract_pool = ExtractPool(engine, n, staged=(mode == "staged"))
            self._warm()
        self.decisions = []
        self.skipped = []
        self.last = None
        self.round_trip = None
        self.tally = None
        self.truth = {}
        self.counting = True
        self.score = [0, 0]
        self.names = code_names()
        self.stream_label = None
        self.jsonl = jsonl
        if jsonl:
            os.makedirs(os.path.dirname(jsonl), exist_ok=True)

    # Engine v5: each CNN run once on zero windows of the usual shapes (10 to 12 windows of 28 x 34; three...
    def _warm(self) -> None:
        from pipeline.identify import idv2_core as C
        m = self.e.model
        for (tag, _s), net in sorted(m.nets.items()):
            ch = 3 if tag == "cnn3" else 1
            for k in (10, 11, 12):
                C.pass_logp(net, np.zeros((k, ch, 28, C.HP["win_frames"]), np.float32), np.zeros(k, int), np.zeros(k, int), 1, 6,
                            m.device)

    # One press.
    def press(self, t: float, path=None, source: str = None) -> None:
        src = source or ("detected" if path is None else "key")
        self.e.press(t, path=path, info={"direction_source": src})

    # Function new walker.
    def new_walker(self) -> None:
        self.tally = {"k": 0, "logp": np.zeros(6)}

    # Function poll.
    def poll(self, now: float, closing: bool = False) -> list:
        if self.v5:
            return self._poll_v5(now, closing)
        out = []
        for d in self.e.poll(now, closing):
            self._write(d)
            out.append(d)
        return out

    # Engine v5: the last decision is out (written, and shown after the last poll), so its walk joins the pool...
    def _poll_v5(self, now: float, closing: bool) -> list:
        settled = self.e.session.settle("poll")
        try:
            got = self.e.poll(now, closing)
        except SilentReceiver as err:
            got = []
            self.skipped.append({"t_poll": float(now), "why": str(err)})
            print(f"IDENTIFICATION: a walk could not be identified: {err}" + (
                "." if isinstance(err, DataEnded) else
                ". Check that receiver's power and cable; the next walks are identified once it sends again."), flush=True)
        self._write_pending()
        if self.extract_pool is not None and self.extract_pool.staged:
            self.extract_pool.early(now, send=not got)
        if (got or settled) and self.e.model.device == "mps":
            import torch
            torch.mps.empty_cache()
        return got

    # Function write pending.
    def _write_pending(self) -> None:
        while self.written < len(self.e.decisions):
            self._write(self.e.decisions[self.written])
            self.written += 1

    # Function write.
    def _write(self, d: dict) -> None:
        from pipeline.identify import engine as EN
        ens = d["ensemble"]
        rt = None
        prev = self.last
        if (prev is not None and d["extraction"]["path"] == "A_rev" and prev["extraction"]["path"] == "A_fwd"
                and d["t0"] - (prev["t_dec"] + prev["latency_s"] - prev["wait_s"]) <= ROUND_TRIP_S):
            rt = _norm(prev["ensemble"] + ens)
        self.round_trip = rt
        if self.tally is not None:
            self.tally["k"] += 1
            self.tally["logp"] = self.tally["logp"] + ens
        d["round_trip"] = rt
        d["tally"] = {"k": self.tally["k"], "logp": _norm(self.tally["logp"])} if self.tally else None
        d["truth_name"] = self.truth.get(d["t0"])
        if d["truth_name"] is not None and self.counting:
            self.score[1] += 1
            self.score[0] += int(self.names[d["top"]] == d["truth_name"])
        d["counted"] = bool(d["truth_name"] is not None and self.counting)
        self.last = d
        self.decisions.append(d)
        if self.jsonl:
            line = line_of(d, self.model_name, self.replay, EN.CLASSES, self.names)
            if getattr(self, "layout", None):
                line["layout"] = self.layout
            with open(self.jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")

    # Function state.
    def state(self) -> dict:
        return {"last": self.last, "model": self.model_name, "replay": self.replay, "walks_seen": len(self.e.session),
                "open": self.e.open_windows, "round_trip": self.round_trip, "dmode": self.dmode, "names": self.names,
                "score": tuple(self.score), "stream": self.stream_label, "v5": bool(getattr(self.e, "v5", False)),
                "room": getattr(self.e, "room", None)}


# Function norm.
def _norm(lp):
    lp = np.asarray(lp, float)
    m = lp.max()
    return lp - (m + np.log(np.exp(lp - m).sum()))


# The JSON line of one decision.
def line_of(d: dict, model: str, replay: bool, classes, names: dict = None) -> dict:
    ens, conf = np.exp(d["ensemble"]), d["confidence"]
    k = int(np.argmax(d["ensemble"]))
    r = int(np.argsort(-d["ensemble"])[1])
    x = d["extraction"]
    names = names or code_names()
    out = {"schema": "id_engine_decision_v2", "t_press_mono": d["t0"], "t_decision_mono": d["t_dec"] + d["latency_s"] - d["wait_s"],
           "t_written_host": time.time(), "window_s": d["T"], "direction": DIR_WORD.get(x["path"], x["path"]), "path": x["path"],
           "direction_source": d["info"].get("direction_source", "detected"), "top": classes[k],
           "probability": round(float(conf[k]), 4), "runner_up": classes[r], "runner_up_probability": round(float(conf[r]), 4),
           "displayed_confidence": {c: round(float(v), 4) for c, v in zip(classes, conf)},
           "ensemble_probability": {c: round(float(v), 6) for c, v in zip(classes, ens)},
           "wifi_speed_m_s": None if not np.isfinite(x["wifi_speed"]) else round(float(x["wifi_speed"]), 3),
           "latency_after_window_s": round(float(d["latency_s"]), 3), "calibration_windows": int(d["calib_n"]),
           "closed_set": list(classes), "model": model, "replay": bool(replay), "round_trip": None, "tally": None,
           "top_name": names[classes[k]], "runner_up_name": names[classes[r]]}
    if d.get("truth_name") is not None:
        out["truth_name"] = d["truth_name"]
    if d.get("round_trip") is not None:
        rt = d["round_trip"]
        out["round_trip"] = {"top": classes[int(np.argmax(rt))], "probability": round(float(np.exp(rt).max()), 4)}
    if d.get("tally") is not None:
        t = d["tally"]["logp"]
        out["tally"] = {"k": int(d["tally"]["k"]), "top": classes[int(np.argmax(t))], "probability": round(float(np.exp(t).max()), 4)}
    if d.get("engine_version", 4) >= 5:
        out["schema"] = "id_engine_decision_v3"
        out.update({"engine_version": int(d["engine_version"]), "room": d["room"], "weight_a": round(float(d["weight_a"]), 4),
                    "windows_s": [round(float(k), 2) for k in d["windows"]],
                    "window_decisions_mono": [float(w["t_dec"]) for w in d["windows"].values()],
                    "components": {f"{k:.2f}": {c: [round(float(x), 4) for x in v] for c, v in w["components"].items()}
                                   for k, w in d["windows"].items()},
                    "ensemble_without_pace_top": classes[int(np.argmax(d["ensemble_nopace"]))]})
    return out



# Draws what the app gives it and decides nothing.
class EngineScreen:

    # Layout: where RX2 is drawn, engine._rigs()'s position for it (home on the tracking rig, id_spot beside the...
    def __init__(self, headless: bool = False, layout: str = "id_spot"):
        import matplotlib
        if headless:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        self.plt, self.headless, self.layout = plt, headless, layout
        self.fig = plt.figure(figsize=(12.0, 6.6))
        if not headless and self.fig.canvas.manager:
            self.fig.canvas.manager.set_window_title("identification: press SPACE in the Terminal window, not here"
                                                     if layout == "id_spot" else
                                                     "identification: press the keys in the Terminal window, not here")
        self.ax = self.fig.add_axes([0.03, 0.12, 0.36, 0.76])
        self.bx = self.fig.add_axes([0.47, 0.50, 0.50, 0.36])
        self.cx = self.fig.add_axes([0.47, 0.12, 0.23, 0.26])
        self.tx = self.fig.add_axes([0.74, 0.08, 0.24, 0.32])
        self.header = self.fig.text(0.03, 0.94, "", fontsize=14, weight="bold")
        self.caption = self.fig.text(0.03, 0.02, "", fontsize=9, color="0.25")
        if not headless:
            plt.ion()
            plt.show(block=False)

    # Function draw.
    def draw(self, st: dict, now: float = None) -> None:
        from pipeline.identify import engine as EN
        ax, bx, cx, tx = self.ax, self.bx, self.cx, self.tx
        names = st.get("names") or {c: c for c in EN.CLASSES}
        label = [names[c] for c in EN.CLASSES]
        for x in (ax, bx, cx, tx):
            x.clear()
        head = f"RECORDED STREAM: {st['stream']}   " if st.get("stream") else ("REPLAY   " if st["replay"] else "")
        self.header.set_text(head + "IDENTIFICATION, one press")
        for g in np.arange(0, 5.001, 1.0):
            ax.axhline(g, color="0.93", lw=0.6)
            ax.axvline(g, color="0.93", lw=0.6)
        if st.get("popup"):
            for a_, b_ in {tuple(sorted(se)) for se in screen_paths().values()}:
                ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="0.88", lw=2.5)
        else:
            ax.plot([2.5, 2.5], [0, 5], color="0.8", lw=4)
        rx2 = tuple(EN._rigs()[getattr(self, "layout", "id_spot")]["RX2"])
        for nm, (x, y) in {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": rx2, "RX3": (5.5, 2.5)}.items():
            ax.plot(x, y, "^", color="tab:purple", ms=8)
            ax.annotate(nm, (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color="tab:purple")
        ax.set_xlim(-1, 6)
        ax.set_ylim(-1, 6)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        d = st["last"]
        tx.axis("off")
        k_, n_ = st.get("score") or (0, 0)
        lines = [f"model: {st['model']}", "closed set: six enrolled people", "chance: 1 in 6",
                 f"adapting to this room: {st['walks_seen']} walks seen"]
        if st.get("v5"):
            lines.insert(1, f"room: {st['room']} (engine v5)")
        if n_:
            lines.append(f"correct {k_} of {n_} ({100 * k_ / n_:.1f} %), chance 16.7 %")
        if st["open"]:
            lines.append("listening: walk in progress")
        nxt = st.get("next_path") if st.get("popup") else None
        if nxt:
            s_, e_ = path_arrow(*lane_of(nxt, screen_paths()))
            ax.annotate("", xy=e_, xytext=s_, arrowprops={"arrowstyle": "-|>", "color": "tab:blue", "lw": 2, "ls": "--"})
            ax.set_xlabel(f"next walk: {nxt}" if st.get("map_open", True) else f"this walk: {nxt} (picked on the map)",
                          fontsize=10, color="tab:blue", weight="bold")
        if d is None:
            bx.axis("off")
            cx.axis("off")
            if st.get("popup"):
                msg = ("pick the walk's path on the map window (one click),\nthen press SPACE in the Terminal as the walker "
                       "starts\n(a / t: line A, away from / towards the TX)")
            elif st.get("dmode", "detected") == "detected":
                msg = "press SPACE when the walker starts on line A"
            else:
                msg = "press a (away from the TX) or t (towards it)\nwhen the walker starts on line A"
            bx.text(0, 0.8, msg, fontsize=12)
            tx.text(0, 1, "\n".join(lines), va="top", fontsize=9)
            self._show()
            return
        x = d["extraction"]
        way = DIR_WORD.get(x["path"], x["path"])
        if x["path"] in ("A_fwd", "A_rev"):
            y0, y1 = (0.3, 4.7) if x["path"] == "A_fwd" else (4.7, 0.3)
            ax.annotate("", xy=(2.5, y1), xytext=(2.5, y0), arrowprops={"arrowstyle": "-|>", "color": "tab:green", "lw": 3})
        elif x["path"] in screen_paths():
            s_, e_ = path_arrow(*screen_paths()[x["path"]])
            ax.annotate("", xy=e_, xytext=s_, arrowprops={"arrowstyle": "-|>", "color": "tab:green", "lw": 3})
        ax.set_title(f"direction: {way} ({d['info'].get('direction_source', 'detected')})", fontsize=10)
        conf = d["confidence"]
        k = int(np.argmax(d["ensemble"]))
        r = int(np.argsort(-d["ensemble"])[1])
        cols = ["tab:blue" if i == k else "0.7" for i in range(6)]
        bx.bar(np.arange(6), conf, color=cols)
        bx.axhline(1 / 6, color="red", ls="--", lw=1, label="chance 1 in 6")
        bx.set_xticks(np.arange(6), label)
        bx.set_ylim(0, 1)
        bx.legend(fontsize=8, loc="upper right")
        bx.set_title(f"this walk: {label[k]} ({conf[k]:.2f}), runner-up {label[r]} ({conf[r]:.2f})", fontsize=11)
        if d.get("truth_name") is not None:
            right = label[k] == d["truth_name"]
            bx.text(0.5, -0.16, f"truth: {d['truth_name']}", transform=bx.transAxes, ha="center", fontsize=12,
                    weight="bold", color="tab:green" if right else "tab:red")
        extra = st["round_trip"] if st["round_trip"] is not None else (d["tally"]["logp"] if d.get("tally") else None)
        if extra is not None:
            p = np.exp(extra)
            cx.bar(np.arange(6), p, color="tab:purple")
            cx.axhline(1 / 6, color="red", ls="--", lw=1)
            cx.set_xticks(np.arange(6), label, fontsize=8)
            cx.set_ylim(0, 1)
            cx.set_title("round trip (away + towards)" if st["round_trip"] is not None else f"{d['tally']['k']} walks (this walker)", fontsize=9)
        else:
            cx.axis("off")
        v = x["wifi_speed"]
        lines = [f"Wi-Fi speed: {v:.2f} m/s" if np.isfinite(v) else "Wi-Fi speed: undefined",
                 f"latency: {d['latency_s']:.2f} s after the {d['T']:.0f} s window"] + lines
        tx.text(0, 1, "\n".join(lines), va="top", fontsize=9)
        if d.get("engine_version", 4) >= 5:
            n = len(d.get("components") or {})
            self.caption.set_text("One press when the walker starts. The answer comes from three 4 s windows of Wi-Fi signal (0, "
                                  f"0.15 and 0.30 s after the press): gait features and Doppler maps, {NUMBER_WORDS.get(n, n)} models "
                                  "summed and the windows averaged. Displayed confidence is their geometric mean.")
        else:
            self.caption.set_text("One press when the walker starts. The answer comes from 3 s of Wi-Fi signal: gait features and "
                                  "Doppler maps, eight models summed. Displayed confidence is their geometric mean.")
        self._show()

    # Function show.
    def _show(self):
        if self.headless:
            return
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    # The window's events only (engine v5: between redraws); nothing is rebuilt.
    def pump(self) -> None:
        if not self.headless:
            self.fig.canvas.flush_events()

    # Function save.
    def save(self, path: str) -> None:
        self.fig.savefig(path, dpi=110)


# The path pop-up: a map of the taped grid with the twelve tracking paths as arrows, start to end, read from...
class PathPopup:

    # Sets up the object.
    def __init__(self, headless: bool = False, paths: dict = None, focus_back: bool = None, clock=None):
        import matplotlib
        if headless:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        self.plt, self.headless = plt, headless
        self.paths = dict(paths or screen_paths())
        self.clock = clock or time.monotonic
        self.focus_back = (not headless) if focus_back is None else bool(focus_back)
        self.history = []
        self.locked = False
        self.ignored = 0
        self.lanes = self._lanes()
        self.fig = plt.figure(figsize=(5.6, 6.4))
        if not headless and self.fig.canvas.manager:
            self.fig.canvas.manager.set_window_title("identification: click the next walk's path, then SPACE in the Terminal")
        self.ax = self.fig.add_axes([0.03, 0.03, 0.94, 0.82])
        self.title = self.fig.text(0.04, 0.95, "", fontsize=12, weight="bold")
        self.sub = self.fig.text(0.04, 0.905, "seen from above, the TX at the bottom; one click picks line and direction",
                                 fontsize=9, color="0.3")
        self.art = {}
        self._build()
        self._restyle()
        self.fig.canvas.mpl_connect("button_press_event", self._click)
        if not headless:
            plt.show(block=False)
            self._draw()

    # {path: (start, end)} as drawn (lane_of): a line's two directions side by side.
    def _lanes(self) -> dict:
        return {nm: lane_of(nm, self.paths) for nm in self.paths}

    # Function build.
    def _build(self) -> None:
        from matplotlib.patches import FancyArrowPatch
        ax = self.ax
        for g in np.arange(0, 5.001, 1.0):
            ax.axhline(g, color="0.93", lw=0.6, zorder=0)
            ax.axvline(g, color="0.93", lw=0.6, zorder=0)
        for nm, (a, b) in self.lanes.items():
            s, e = path_arrow(a, b, inset=0.15)
            arr = FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=16, lw=1.6, color="0.6", zorder=2)
            ax.add_patch(arr)
            u = (np.asarray(e) - np.asarray(s)) / max(float(np.hypot(*(np.asarray(e) - np.asarray(s)))), 1e-9)
            lab = ax.text(*(np.asarray(a) - 0.34 * u), nm, ha="center", va="center", fontsize=8, color="0.35", zorder=3)
            self.art[nm] = (arr, lab)
        ax.set_xlim(-1.0, 6.0)
        ax.set_ylim(-1.0, 6.0)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])

    # Function chosen.
    @property
    def chosen(self):
        return self.history[-1][1] if self.history else None

    # The path picked last at or before t (a key's time), or None.
    def path_at(self, t: float):
        for tp, nm in reversed(self.history):
            if tp <= float(t):
                return nm
        return None

    # The path drawn nearest to the point (x, y) on the grid, within POPUP_PICK_M, or None.
    def pick(self, x: float, y: float):
        p = np.array([x, y], float)
        best, dist = None, POPUP_PICK_M
        for nm, (a, b) in self.lanes.items():
            ab = b - a
            q = a + np.clip(float(np.dot(p - a, ab) / max(float(np.dot(ab, ab)), 1e-12)), 0.0, 1.0) * ab
            d_ = float(np.hypot(*(p - q)))
            if d_ <= dist:
                best, dist = nm, d_
        return best

    # A point on the path's own arrow, a quarter of the way along (where a click picks it and no other).
    def pick_point(self, path: str) -> tuple:
        a, b = self.lanes[path]
        return tuple(a + 0.25 * (b - a))

    # Function click.
    def _click(self, ev) -> None:
        if ev.inaxes is not self.ax or ev.xdata is None:
            return
        nm = self.pick(ev.xdata, ev.ydata)
        if nm is not None:
            self.choose(nm)

    # A pick (the click's callback): refused while a walk is open; else recorded on the keys' clock and shown.
    def choose(self, path: str, t: float = None) -> bool:
        if path not in self.paths:
            raise ValueError(f"{path!r} is not one of the tracking paths {sorted(self.paths)}")
        if self.locked:
            self.ignored += 1
            print("IDENTIFICATION: a walk is in progress; the map opens again after its decision", flush=True)
            return False
        self.history.append((float(self.clock() if t is None else t), path))
        self._restyle()
        self._draw()
        print(f"IDENTIFICATION: next walk {path}. Press SPACE in the Terminal as the walker starts.", flush=True)
        if self.focus_back:
            self._focus_terminal()
        return True

    # An a / t press: its line-A path becomes the one picked (the next SPACE repeats it).
    def preselect(self, path: str, t: float) -> None:
        self.history.append((float(t), path))

    # A press: the map takes no pick until no walk is open.
    def lock(self) -> None:
        self.locked = True

    # No walk open any more: the map opens again, the last path still picked.
    def reopen(self) -> None:
        self.locked = False
        self._restyle()
        self._draw()

    # Function restyle.
    def _restyle(self) -> None:
        for nm, (arr, lab) in self.art.items():
            on = nm == self.chosen
            arr.set_color("tab:green" if on else "0.6")
            arr.set_linewidth(3.4 if on else 1.6)
            arr.set_zorder(4 if on else 2)
            lab.set_color("tab:green" if on else "0.35")
            lab.set_fontweight("bold" if on else "normal")
        self.title.set_text("walk in progress: the map opens again after its decision" if self.locked else
                            (f"next walk: {self.chosen}   (SPACE in the Terminal starts it)" if self.chosen else
                             "click the next walk's path"))

    # Function draw.
    def _draw(self) -> None:
        if not self.headless:
            self.fig.canvas.draw_idle()

    # Function pump.
    def pump(self) -> None:
        if not self.headless:
            self.fig.canvas.flush_events()

    # Function save.
    def save(self, path: str) -> None:
        self.fig.savefig(path, dpi=110)

    # Give the keyboard back to the Terminal the app runs in, so SPACE reaches the key reader (macOS; not waited...
    @staticmethod
    def _focus_terminal() -> None:
        import subprocess
        import sys
        app = {"Apple_Terminal": "Terminal", "iTerm.app": "iTerm", "vscode": "Visual Studio Code"}.get(
            os.environ.get("TERM_PROGRAM", ""))
        if sys.platform == "darwin" and app:
            subprocess.Popen(["open", "-a", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



# Run_capture's extra consumer, and the recorded source's: frames in, keys on the same clock, the engine...
class EngineConsumer:
    owns_terminal = True
    SILENT_S = 1.0
    KEY_SLACK_S = 0.05

    # Sets up the object.
    def __init__(self, app: EngineApp, screen=None, nodes=("RX1", "RX2", "RX3"), snapshots: str = None):
        import queue
        import threading
        self.app, self.screen, self.nodes = app, screen, tuple(nodes)
        self.buf = {n: [] for n in self.nodes}
        self.keys = queue.Queue()
        self.stop = threading.Event()
        self.last_draw = -np.inf
        self.display = True
        self.routes = {}
        self.snapshots, self.shots = snapshots, 0
        self.shown = None
        self.held = []
        self.arrived = 0
        self.last_t = {}
        self.keys_held = []
        self.silent = set()
        self.popup = None
        self.refused = 0

    # Function handle.
    def handle(self, rec) -> None:
        if rec.node_id in self.buf:
            t = float(rec.t_mono)
            self.held.append((t, self.nodes.index(rec.node_id), self.arrived, rec))
            self.arrived += 1
            self.last_t[rec.node_id] = max(self.last_t.get(rec.node_id, -np.inf), t)

    # Frames below this time are complete: every receiver still sending has delivered past it.
    def _horizon(self, now: float) -> float:
        if not self.last_t:
            return -np.inf
        newest = max(self.last_t.values())
        return min(min(t for t in self.last_t.values() if t >= newest - self.SILENT_S), now - self.KEY_SLACK_S)

    # Keys from the reader's queue: q acts at once, every other key waits for the data to pass its time.
    def _take_keys(self) -> None:
        while not self.keys.empty():
            ev = self.keys.get_nowait()
            if ev.key == "q":
                self.stop.set()
            else:
                self.keys_held.append(ev)

    # Every held frame below upto, in timestamp order (ties: receiver, then arrival), one group of equal t_mono...
    def _release(self, upto: float, now: float) -> list:
        from pipeline.live.rig import frame_of
        self._take_keys()
        if not self.held:
            return []
        self.held.sort(key=lambda h: (h[0], h[1], h[2]))
        k = int(np.searchsorted([h[0] for h in self.held], upto, side="left"))
        ready, self.held = self.held[:k], self.held[k:]
        got_all, i = [], 0
        while i < len(ready):
            tau, j = ready[i][0], i
            while j < len(ready) and ready[j][0] == tau:
                rec = ready[j][3]
                self.buf[rec.node_id].append(frame_of(rec))
                j += 1
            self._flush()
            self._keys(upto=tau)
            got_all += self.app.poll(tau)
            i = j
        return got_all

    # The stream's end: every held frame and key given, then the closing poll (the rig's end, and end_stream's).
    def finish(self) -> list:
        got = self._release(np.inf, np.inf)
        self._keys(upto=np.inf)
        got += self.app.poll(np.inf, closing=True)
        return got

    # Function flush.
    def _flush(self) -> None:
        for n in self.nodes:
            if self.buf[n]:
                self.app.e.push(n, np.concatenate(self.buf[n]))
                self.buf[n] = []

    # A new capture stream: the receivers restart; the session's adaptation carries on.
    def new_stream(self, layout: str, display: bool = True, routes: dict = None) -> None:
        if self.held:
            self._release(np.inf, np.inf)
        self.last_t = {}
        self.app.e.new_recording(layout)
        self.display, self.routes = display, dict(routes or {})
        self.app.counting = display

    # Function set truth.
    def set_truth(self, t_press: float, name: str) -> None:
        self.app.truth[float(t_press)] = name

    # Function end stream.
    def end_stream(self) -> None:
        self._after(self.finish(), np.inf)
        self._popup_tick()

    # The held keys up to upto, in time order (data-time order: see the class docstring).
    def _keys(self, upto: float = np.inf) -> None:
        self._take_keys()
        self.keys_held.sort(key=lambda e: float(e.t_mono))
        while self.keys_held and float(self.keys_held[0].t_mono) <= upto:
            ev = self.keys_held.pop(0)
            if ev.key == " ":
                route = self.routes.get(float(ev.t_mono))
                if route is not None:
                    self.app.press(ev.t_mono, path=route, source="known route")
                elif self.popup is not None:
                    path = self.popup.path_at(float(ev.t_mono))
                    if path is None:
                        self.refused += 1
                        print(POPUP_REFUSED, flush=True)
                    else:
                        self.app.press(ev.t_mono, path=path, source=POPUP_SOURCE)
                        self.popup.lock()
                elif self.app.dmode == "detected":
                    self.app.press(ev.t_mono)
                else:
                    self.refused += 1
                    print(SPACE_REFUSED, flush=True)
            elif ev.key in ("a", "t"):
                path = "A_fwd" if ev.key == "a" else "A_rev"
                self.app.press(ev.t_mono, path=path, source="key")
                if self.popup is not None:
                    self.popup.preselect(path, float(ev.t_mono))
                    self.popup.lock()
            elif ev.key == "n":
                self.app.new_walker()

    # The path pop-up opens again once no walk is open (the last decision is out), the last path still picked.
    def _popup_tick(self) -> None:
        p = self.popup
        if p is not None and p.locked and not getattr(getattr(self.app, "e", None), "open_windows", 0):
            p.reopen()

    # Engine v5: what the screen shows, beyond the clock: the last decision, the walks seen, whether a walk is...
    def _seen(self, st: dict) -> tuple:
        return (None if st["last"] is None else st["last"]["t0"], st["walks_seen"], bool(st["open"]), tuple(st["score"]),
                st["stream"], st.get("next_path"), st.get("map_open"))

    # The app's state for the screen, with the path pop-up's pick and whether its map is open.
    def _state(self) -> dict:
        st = self.app.state()
        if self.popup is not None:
            st.update(popup=True, next_path=self.popup.chosen, map_open=not self.popup.locked)
        return st

    # Function after.
    def _after(self, got: list, now: float) -> None:
        if self.screen is None or not self.display:
            return
        if getattr(self.app, "v5", False):
            st = self._state()
            seen = self._seen(st)
            if got or seen != self.shown:
                self.shown, self.last_draw = seen, now
                self.screen.draw(st, now)
                if got and self.snapshots:
                    os.makedirs(self.snapshots, exist_ok=True)
                    self.screen.save(os.path.join(self.snapshots, f"identify_{self.shots:04d}.png"))
                    self.shots += 1
            elif now - self.last_draw >= 0.1:
                self.last_draw = now
                self.screen.pump()
                if self.popup is not None:
                    self.popup.pump()
            return
        if got or now - self.last_draw >= 0.1:
            self.last_draw = now
            self.screen.draw(self._state(), now)
            if self.popup is not None:
                self.popup.pump()
            if got and self.snapshots:
                os.makedirs(self.snapshots, exist_ok=True)
                self.screen.save(os.path.join(self.snapshots, f"identify_{self.shots:04d}.png"))
                self.shots += 1

    # Now is the stream's time: run_capture passes the host's time.monotonic() (the clock of t_mono and of the...
    def tick(self, now: float) -> None:
        self._after(self._release(self._horizon(now), now), now)
        self._popup_tick()
        self._announce(now)

    # The silent-receiver guard's messages: a receiver with no frame for over SILENT_S (rig.silent_receivers: in...
    def _announce(self, now: float) -> None:
        from pipeline.live.rig import silent_receivers
        silent = silent_receivers(self.last_t, now)
        for n in sorted(silent - self.silent):
            print(f"IDENTIFICATION: {n} is silent (no frames for over {self.SILENT_S:g} s); a walk while it is silent "
                  f"cannot be identified. Check its power and cable.", flush=True)
        for n in sorted(self.silent - silent):
            print(f"IDENTIFICATION: {n} is sending again.", flush=True)
        self.silent = silent


# A model's training sessions: its manifest's training_sessions, else from its train_rows and bank.
def training_sessions(md: str) -> list:
    p = os.path.join(md, "manifest.json")
    man = json.load(open(p)) if os.path.exists(p) else {}
    if "training_sessions" in man:
        return list(man["training_sessions"])
    meta = json.load(open(os.path.join(md, "meta_feat_cnn.json")))
    bank = os.path.join(REPO_ROOT, meta["cfg"]["bank"])
    sess = [q["session"] for q in json.load(open(os.path.join(bank, "meta.json")))["passes"]]
    return sorted({sess[int(i)] for i in np.load(os.path.join(md, "train_rows.npy"))})


# Refuses any model trained on the streamed session.
def guard(md: str, session: str) -> list:
    ts = training_sessions(md)
    if session in ts:
        raise SystemExit(f"REFUSED: {os.path.basename(md)} was trained on {ts}, which includes the streamed session {session}; "
                         f"a recorded stream needs a model that never saw it (for {session}: loso_{session})")
    return ts


# The final engine's fold model that never saw session: the newest engine's that is built (v5, then v4, then...
def final_model(session: str) -> str:
    from pipeline.identify import engine as EN
    for name in (f"loso_{session}_v5n", f"loso_{session}_v5", EN.model_name(f"loso_{session}"), f"loso_{session}_x"):
        if os.path.exists(os.path.join(model_dir(name), "meta_feat_cnn.json")):
            return name
    return f"loso_{session}"


# The rig run: a recorded session through the rig's interface, the fold model that never saw it.
def cmd_rig_recorded(a) -> int:
    from pipeline.identify import engine as EN
    from pipeline.live.identify_recorded import RecordedSource, stream
    os.chdir(REPO_ROOT)
    model = a.model or final_model(a.session)
    md = model_dir(model) if not os.path.isabs(model) else model
    ts = guard(md, a.session)
    room = a.session[0]
    if a.room is not None and a.room != room:
        raise SystemExit(f"REFUSED: --room {a.room}, but the recorded session {a.session} is in Room {room}")
    from pipeline.identify import ide_train as IT
    eng = EN.Engine(md, T=EN.T_S, amp_norm=IT.gs_adopted(), layout="id_spot", device=rig_device(md, a.device), room=room)
    stem = time.strftime(f"rig_recorded_{a.session}_%Y%m%d_%H%M%S")
    app = EngineApp(eng, f"{os.path.basename(md)} (trained on {', '.join(ts)})", replay=True,
                    jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"), dmode=direction_mode(), extract_workers=a.extract_workers,
                    extract_mode=a.extract_mode)
    app.stream_label = a.session
    src = RecordedSource(a.session)
    start = src.index_of(a.start) if a.start else 0
    play = (lambda r: r["kind"] == "idcap" and r["block"] == "natural") if a.render == "natural" else None
    shown = a.screen or a.render or a.snapshots
    scr = EngineScreen(headless=a.headless or not (a.screen or a.render)) if shown else None
    c = EngineConsumer(app, scr, snapshots=a.snapshots)
    speed = "max" if a.speed == "max" else float(a.speed)
    until = max(k for k, r in enumerate(src.recs) if k >= start and play(r)) if play else None
    info = stream(c, src, speed=speed, start=start, play=play, log=print, until=until)
    out = {"session": a.session, "model": os.path.basename(md), "training_sessions": ts, "decisions": len(app.decisions),
           "presses": info["presses"], "score_shown": app.score, "jsonl": app.jsonl}
    print(json.dumps(out, indent=1))
    return 0


# On the boards: the deployment model, from its manifest.
def cmd_rig(a) -> int:
    if getattr(a, "source", "serial") == "recorded":
        return cmd_rig_recorded(a)
    from pipeline.constrained.nodes import room_a_macs
    from pipeline.identify import engine as EN
    from pipeline.live.rig import run
    from pipeline.live.rig_run import identify, mapping_by_mac
    md, man = load_deployment()
    if getattr(a, "room", None) not in ("A", "B", "new"):
        raise SystemExit("REFUSED: the rig needs the installation's room before any press: --room A, --room B or --room new "
                         "(a room the deployment model never trained in)")
    layout = getattr(a, "layout", None) or "home"
    if layout not in RIG_LAYOUTS:
        raise SystemExit(f"REFUSED: --layout {layout!r}: home (RX2 where tracking has it) or id_spot (the geometry test)")
    popup = bool(getattr(a, "popup", False))
    if popup and layout != "home":
        raise SystemExit("REFUSED: --popup is for the home layout; at the identification spot SPACE uses the direction detector")
    os.chdir(REPO_ROOT)
    from pipeline.live.final_model import RigSteps, rig_banner
    steps = RigSteps(4)
    print("IDENTIFICATION, the live app on the boards: starting (about half a minute)", flush=True)
    dev = rig_device(md, getattr(a, "device", None))
    dmode = direction_mode_for(layout)
    rx2 = tuple(EN._rigs()[layout]["RX2"])
    steps.step(f"Loading the identification model {man['model']} on the {'GPU' if dev == 'mps' else 'CPU'}; layout {layout}: "
               f"RX2 at {rx2}{' (the tracking rig)' if layout == 'home' else ' (the geometry test)'}; direction: "
               + ("each walk's path picked on the map (the path pop-up), then SPACE" if popup else
                  'SPACE (the detector)' if dmode == 'detected' else 'the a / t keys (SPACE is refused here)'))
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"], layout=layout, device=dev, room=a.room)
    stem = time.strftime("rig_%Y%m%d_%H%M%S")
    steps.step("Starting and warming the extraction workers")
    app = EngineApp(eng, f"{man['model']} (all five sessions; room {a.room})", replay=False, jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"),
                    dmode=dmode, extract_workers=getattr(a, "extract_workers", None),
                    extract_mode=getattr(a, "extract_mode", None))
    app.layout = layout
    steps.step("Naming the boards by their MAC addresses")
    nodes = mapping_by_mac(identify(), room_a_macs(os.path.join(REPO_ROOT, "data")))
    nodes = {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    steps.step("Opening the identification window" + (" and the path map" if popup else ""))
    c = EngineConsumer(app, EngineScreen(headless=False, layout=layout))
    if popup:
        c.popup = PathPopup(headless=False, focus_back=not getattr(a, "no_focus_return", False))
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                ("Before each walk, click its path on the map window (one click: line and direction); then SPACE here as "
                 "the walker starts. The map opens again after each decision with the last path picked, so a repeat is one "
                 "SPACE. a / t = line A (away from / towards the TX); n = a new walker; q quits." if popup else
                 "SPACE once as each walker starts; n = a new walker; a / t = the route (away / towards); q quits."
                 if dmode == "detected" else
                 "a (away from the TX) or t (towards it) once as each walker starts on line A; n = a new walker; q quits."),
                "Keep the plot window visible during a walk (a hidden window can be slowed by macOS)."])
    rc = run(c, nodes, duration=a.minutes * 60.0 if a.minutes else None, mode="identify", stem=stem,
             run_config={"model": man["model"], "room": a.room, "layout": layout, "direction_mode": dmode, "path_popup": popup,
                         "device": str(getattr(eng.model, "device", None)),
                         "extract_mode": getattr(a, "extract_mode", None) or EXTRACT_MODE_V5,
                         "extract_workers": getattr(a, "extract_workers", None), "jsonl": app.jsonl})
    c.finish()
    rec = getattr(c, "record_dir", None)
    if rec:
        with open(os.path.join(rec, f"{stem}.summary.json"), "w", encoding="utf-8") as f:
            json.dump({"model": man["model"], "room": a.room, "layout": layout, "rx2": list(rx2), "direction_mode": dmode,
                       "path_popup": popup, "popup_picks": (c.popup.history if popup else None),
                       "popup_clicks_ignored_during_a_walk": (c.popup.ignored if popup else None),
                       "space_refused": int(getattr(c, "refused", 0)), "device": str(getattr(eng.model, "device", None)),
                       "decisions": len(app.decisions), "jsonl": app.jsonl, "exit": rc,
                       "settles": list(getattr(eng.session, "settles", []) or []),
                       "skipped_walks_silent_receiver": app.skipped}, f, indent=1, default=str)
    print(json.dumps({"decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return rc



# A recorded session through the app: frames pushed as they arrived (in chunk_s arrival blocks, or paced in...
def replay_session(session: str, model: str = None, realtime: bool = False, speed: float = 1.0, screen: bool = False,
                   snapshots: str = None, device: str = "cpu", chunk_s: float = CHUNK_S, tally: bool = False,
                   jsonl: str = None, recordings: int = None, extract_workers: int = None,
                   extract_mode: str = None) -> EngineApp:
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    os.chdir(REPO_ROOT)
    model = model or final_model(session)
    gs = IT.gs_adopted()
    dmode = RP.direction_mode()
    eng = EN.Engine(model_dir(model), T=EN.T_S, amp_norm=gs, device=device, room=session[0])
    app = EngineApp(eng, f"{model} (never saw {session})", replay=True, jsonl=jsonl, dmode=dmode, extract_workers=extract_workers,
                    extract_mode=extract_mode)
    scr = EngineScreen(headless=not screen) if (screen or snapshots) else None
    if snapshots:
        os.makedirs(snapshots, exist_ok=True)
    wall0, v0 = None, None
    shots = 0
    for rec in RP.session_recordings(session)[:recordings]:
        eng.new_recording("id_spot" if rec["kind"] == "idcap" else "home")
        if tally:
            app.new_walker()
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        presses = sorted((float(q["t_start"]), q["path_name"]) for q in gt["passes"])
        t_first = min(float(fr[L]["t_mono"][0]) for L in EN.LINKS)
        t_last = max(float(fr[L]["t_mono"][-1]) for L in EN.LINKS)
        pos = {L: 0 for L in EN.LINKS}
        pi = 0
        step = 0.05 if realtime else chunk_s
        for now in np.arange(t_first + step, t_last + step + 1e-9, step):
            while pi < len(presses) and presses[pi][0] <= now:
                t0, path = presses[pi]
                if rec["kind"] == "idcap":
                    if dmode == "detected":
                        app.press(t0)
                    else:
                        app.press(t0, path=path, source="key")
                else:
                    app.press(t0, path=path, source="known route")
                pi += 1
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], now, side="right"))
                if n > pos[L]:
                    eng.push(L, fr[L][pos[L]:n])
                    pos[L] = n
            got = app.poll(now)
            if realtime:
                if wall0 is None:
                    wall0, v0 = time.time(), now
                lag = (now - v0) / speed - (time.time() - wall0)
                if lag > 0:
                    time.sleep(lag)
            if scr is not None and (screen or got):
                scr.draw(app.state(), now)
                if snapshots and got:
                    scr.save(os.path.join(snapshots, f"identify_{session}_{shots:04d}.png"))
                    shots += 1
        app.poll(np.inf, closing=True)
    return app


# Function cmd replay.
def cmd_replay(a) -> int:
    stem = f"replay_{a.session}_{time.strftime('%Y%m%d_%H%M%S')}"
    app = replay_session(a.session, model=a.model, realtime=a.realtime, speed=a.speed, screen=a.realtime or a.screen,
                         snapshots=a.snapshots, device=a.device, tally=a.tally,
                         jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"), recordings=a.recordings, extract_workers=a.extract_workers,
                         extract_mode=a.extract_mode)
    print(json.dumps({"session": a.session, "decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return 0



# Replay-identify --session <S>... or rig --mode identify... (the same words python3 -m pipeline.live uses...
def main(argv=None) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live", description="identification: the one-press engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay-identify", help="replay a recorded session through the app (the fold model that never saw it)")
    r.add_argument("--session", required=True, choices=("A1", "A2", "A3", "B1", "B2"))
    r.add_argument("--model", default=None, help="default loso_<session>: never trained on the replayed session")
    r.add_argument("--realtime", action="store_true", help="play at real speed in a window (for screen recording)")
    r.add_argument("--speed", type=float, default=1.0)
    r.add_argument("--screen", action="store_true")
    r.add_argument("--snapshots", default=None, help="save the screen after each decision here")
    r.add_argument("--tally", action="store_true", help="mark a new walker at each recording's start (the `n` key)")
    r.add_argument("--recordings", type=int, default=None, help="only the first N recordings of the session")
    r.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    r.add_argument("--extract-workers", type=int, default=None, help=EXTRACT_HELP)
    r.add_argument("--extract-mode", choices=("staged", "pool"), default=None, help=EXTRACT_MODE_HELP)
    k = sub.add_parser("rig", help="ON THE BOARDS: opens serial ports; the deployment model")
    k.add_argument("--mode", choices=("identify",), default="identify")
    k.add_argument("--source", choices=("serial", "recorded"), default="serial",
                   help="serial: the boards (default); recorded: a recorded session streamed as if live")
    k.add_argument("--session", default=None, choices=("A1", "A2", "A3", "B1", "B2"), help="the recorded session (--source recorded)")
    k.add_argument("--speed", default="1", help="1 = real time (or any factor), max = as fast as possible")
    k.add_argument("--from", dest="start", default=None, help="play from this recording (index, label or stem part); "
                   "earlier recordings are fed at maximum speed without display, so adaptation is the whole day's")
    k.add_argument("--render", choices=("natural",), default=None,
                   help="play only the session's natural identification blocks at --speed; the rest fed fast, hidden")
    k.add_argument("--screen", action="store_true", help="show the window for every played recording")
    k.add_argument("--snapshots", default=None, help="save the screen after each shown decision here")
    k.add_argument("--headless", action="store_true", help="draw off screen (with --snapshots: stills only, no window)")
    k.add_argument("--minutes", type=float, default=None)
    k.add_argument("--device", default=None, choices=("cpu", "mps"),
                   help="default: mps for an engine v5 model (real time on the GPU only), cpu for any other")
    k.add_argument("--layout", default="home", choices=RIG_LAYOUTS,
                   help="home (default): RX2 where tracking has it, (-0.5, 2.5); id_spot: RX2 beside the TX at (2.0, -0.5), "
                        "the geometry test only (--source serial; a recorded stream takes each recording's own layout)")
    k.add_argument("--popup", action="store_true",
                   help="home layout: pick each walk's path on a pop-up map of the twelve paths, then SPACE starts it "
                        "(`python3 -m pipeline.live app` turns this on); without it the keys are as before")
    k.add_argument("--no-focus-return", action="store_true",
                   help="with --popup: do not give the keyboard back to the Terminal after a click on the map")
    k.add_argument("--room", default=None, choices=("A", "B", "new"),
                   help="REQUIRED on the boards (engine v5): the installation's room, A, B, or new (a room the deployment "
                        "model never trained in); a recorded stream takes it from its session")
    k.add_argument("--extract-workers", type=int, default=None, help=EXTRACT_HELP)
    k.add_argument("--extract-mode", choices=("staged", "pool"), default=None, help=EXTRACT_MODE_HELP)
    k.add_argument("--baseline", default=None, help="(ignored: the engine needs no empty-room baseline)")
    k.add_argument("--model", default=None, help="recorded source only: a model that never saw the session "
                   "(default: the final loso_<session>); the boards always load the deployment model's manifest")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    return cmd_replay(a) if a.cmd == "replay-identify" else cmd_rig(a)


if __name__ == "__main__":
    import sys
    sys.exit(main())
