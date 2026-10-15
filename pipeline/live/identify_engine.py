"""Identification mode, live: the one-press engine (`pipeline/identify/engine.py`) and nothing else.

One space-bar press when the walker starts on line A. The engine answers on its own about a second after
its 3 s window, from the signal alone: direction, Wi-Fi speed and identity. The same engine object is fed
by the rig (three receivers over serial) and by a replay of recorded `.bin` files, where each recorded
walk's start press is replayed as the one press and every other press is ignored. The thesis figures come
from the same engine (`pipeline/identify/ide_replay.py`), so the app and the figures cannot disagree.

    python3 -m pipeline.live.identify_engine rig --mode identify --room B         # on the boards: the deployment model
                                  # (engine v5: on the GPU, --device mps, unless --device cpu)
    python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1
                                  # the render: B2's natural blocks streamed as if live, through the "to B2" model
    python3 -m pipeline.live.identify_engine replay-identify --session B2 --realtime   # the older replay path
    python3 -m pipeline.live.identify_engine rig --mode identify --room B --extract-workers 0
                                  # engine v5 with serial window extraction: the fallback if the worker pool misbehaves
    python3 -m pipeline.live.identify_engine rig --mode identify --room B --extract-mode pool
                                  # engine v5 with the one-job-per-window pool exactly as shipped on 12 Oct (three workers)

Keys (rig): SPACE starts a walk; `n` marks a new walker (the "k walks" tally); `a` / `t` start an away /
towards walk when the direction detector is not used (PLAN 2.4); `q` stops. No warm-up: the engine decides from
the first walk, and adapts to the room, without labels, from the walks that happen anyway.

Engine v5 (10 Oct 2026): the deployment model is `deploy_all5_v5` and a recorded stream's fold model `loso_<session>_v5`.
A v5 model needs the installation's room, set once before any press and never from the walks: on the boards
`rig --room A|B|new` (the rig refuses to start without it); a recorded stream or replay takes it from the session. The
model's manifest gives the rooms it trained in; three windows per press, the answer after the 0.30 s window.

Engine v5 in the app (Uzayr, 11 Oct 2026, option (c)): a walk joins the calibration pool (its AdaBN copies recomputed)
only after its decision is written and shown (`AfterDecision`), and the rig runs a v5 model on the GPU (`--device mps`)
unless told `--device cpu`: on the cpu the adaptation grows with the day's pool to about 6 s a walk, so identification
runs in real time on the GPU only. Every walk is still classified against exactly the pool it saw before, so no decision
changes. A v4 model runs exactly as before (its adaptation inside the poll, cpu by default).

Engine v5's latency (Uzayr, 11 Oct, timing only): the screen is redrawn when what it shows changes (a press, a decision, the
score), not every 0.1 s, so the redraws no longer queue in front of the windows' extraction (the window's events are still
pumped every 0.1 s); and the CNNs are run once on zero windows before the first press, so the first walk does not pay the
device's first-call cost. Neither touches a decision.

Engine v5's parallel extraction (Uzayr, 12 Oct, timing only): the three windows of a walk are extracted in a warm pool of
worker processes (`ExtractPool`, created once at app start; three workers by default), each window sent to a worker the
moment it is due, so the 0.15 s and 0.30 s windows no longer queue behind the 0 s window's extraction. A worker runs the
engine's own `Extractor.extract_v4` on a frozen copy of the frames that had arrived by the window's decision time, with
numpy's and BLAS's threads at one; workers never use torch or the GPU; engine.py is unchanged. Every extraction equals the
serial one bit for bit. `--extract-workers 0` keeps the serial extraction (the safe fallback for a demo); a v4 model always
extracts serially.

Engine v5's staged extraction (Uzayr, 12 Oct, timing only; the default since then): half of a window's extraction needs only
data from before the window's end, so it runs while the window is still open. Early jobs (`_early_job`) go to the pool as soon
as their data is in: the direction on the first 3 s (with the 3.0 s checkpoint, the same search and interpolation) and the end
detector's checkpoints at 3.25, 3.5 and 3.75 s, each with its decision-time search and RX2's band energy. Each runs on a frozen
copy of the frames that had arrived by the poll that sent it (copied as `ExtractPool._dispatch` copies them), and its result
counts only if its search settled within that copy. At the window's decision time the late job (`_late_job`) assembles the
window in `Extractor.extract_v4`'s exact order (`_staged_extract_v4`), from the engine's own functions, using every early
result that is final, done and still valid for the window's end, and computing the rest itself. Two repeats are dropped where
the value is provably the same: the 3.0 s checkpoint's search and interpolation are the direction's, and the last checkpoint's
search is the window's own decision time, so its interpolation is the speed's (only while every frame reached the engine
before the poll that passed its arrival time, which the pool checks; otherwise every search is run). `--extract-mode pool`
restores the one-job-per-window pool exactly as shipped on 12 Oct (three workers); `--extract-workers 0` is the serial path.

Every decision is one JSON line under `runs/live/identify/` (format: `reports/identification/live-interface.md`; schema v2,
v3 for an engine v5 model).
The screen names the six enrolled people (names are allowed from 30 September); in recorded streams and replays
it also shows who really walked and a running score, which never reach the engine. The old frozen random forest
stays available as `python3 -m pipeline.live replay-identify` without a session (gate 5). Development
evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACT_WORKERS_V5 = 3            # engine v5: worker processes of the one-job-per-window pool (shipped 12 Oct); 0 = serial
EXTRACT_WORKERS_STAGED = 4        # engine v5: worker processes of the staged extraction (fixed 12 Oct before its cpu check)
EXTRACT_MODE_V5 = "staged"        # engine v5's default extraction: "staged" (early and late jobs) or "pool" (one job per window)
EXTRACT_HELP = (f"engine v5: worker processes for the windows' extraction (default {EXTRACT_WORKERS_STAGED} staged, "
                f"{EXTRACT_WORKERS_V5} pool); 0 = serial extraction, the safe fallback (identical decisions, slower); a v4 model "
                "always extracts serially")
EXTRACT_MODE_HELP = ("engine v5: staged (the default: early jobs while each window is open, a late job at its decision time) or "
                     "pool (one job per window, as shipped on 12 Oct); identical decisions either way")
OUT_DIR = os.path.join(REPO_ROOT, "runs", "live", "identify")
ROUND_TRIP_S = 15.0
CHUNK_S = 0.25
DIR_WORD = {"A_fwd": "away", "A_rev": "towards"}


def code_names() -> dict:
    """P1 to P6 -> the participants' names (allowed in every output since 30 September; earlier reports keep codes)."""
    from pipeline.identify.common import SIX, anon
    return {anon(n): n for n in SIX}


def model_dir(name: str) -> str:
    return os.path.join(REPO_ROOT, "runs", "identify", "engine", "models", name)


def deployment_model() -> str:
    """The deployment model's name: the newest engine's that is built (v5 `deploy_all5_v5`, then v4 `deploy_all5_v4`, then
    v2 `deploy_all5_x`), else v1's."""
    from pipeline.identify import engine as EN
    for name in ("deploy_all5_v5", EN.model_name("deploy_all5"), "deploy_all5_x"):
        if os.path.exists(os.path.join(model_dir(name), "manifest.json")):
            return name
    return "deploy_all5"


def load_deployment() -> tuple:
    """(model directory, manifest) of the deployment model; refuses unless the manifest is complete."""
    d = model_dir(deployment_model())
    p = os.path.join(d, "manifest.json")
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: no deployment manifest at {p} (train it: python3 -m pipeline.identify.ide_train deploy_all5)")
    man = json.load(open(p))
    for k in ("model", "gs_adopted", "T_s", "config", "code_commit_at_training"):
        if k not in man:
            raise SystemExit(f"REFUSED: the manifest lacks {k}")
    return d, man


def direction_mode() -> str:
    from pipeline.identify import ide_replay as RP
    old = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        return RP.direction_mode()
    finally:
        os.chdir(old)


def rig_device(md: str, device: str = None) -> str:
    """The rig's device: `--device` if given, else mps for an engine v5 model (Uzayr, 11 Oct: real time on the GPU only)
    and cpu for any other model (v4 unchanged)."""
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


def _extract_worker_init(amp_norm: bool, names: list) -> None:
    """A worker of engine v5's parallel extraction. Its numpy and BLAS pools are at one thread (set in the environment
    before the pool is made, so before this process imported numpy); it imports the engine's extraction modules and runs
    one extraction of a synthetic window, output discarded, so the first walk pays no first-call cost. No torch."""
    from pipeline.identify import engine as EN
    from pipeline.identify import id19_bank, id19_featbank, id29_dc2_score, idmax_features, idz_bank  # noqa: F401
    from pipeline.identify import rehearsal_doppler_check  # noqa: F401
    t = np.arange(0.0, 4.6, 1.0 / EN.FS)
    rng = np.random.default_rng(0)
    timed = [(t, (rng.random((len(t), 103)) + 1.0).astype(np.float32), np.zeros(len(t), np.float32)) for _ in EN.LINKS]
    try:
        EN.extract_window(timed, 0.0, 4.0, amp_norm, "A_fwd", "id_spot", names)
    except Exception:
        pass


def _extract_window_job(job: dict) -> tuple:
    """One window, in a worker: the engine's own `Extractor.extract_v4` on a frozen copy of the receivers (each link's
    frames that had arrived by the window's decision time, which is all the extraction reads). Returns (extraction, wall
    clock start, wall clock end, the worker's pid)."""
    from pipeline.identify import engine as EN
    s = time.time()
    rx = {}
    for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
        r = EN.Receiver()
        r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
        rx[L] = r
    e = EN.Extractor(job["T"], job["amp_norm"], job["layout"], job["names"], job["alpha"], rx=rx, cut=job["cut"])
    td = job["td"]
    _check_receivers(rx, float(job["w"]["t0"]), min(float(td), float(job["w"]["t0"]) + float(job["T"])))
    ex = e.extract_v4(job["w"], td, [rx[L].timed(td) for L in EN.LINKS])
    return ex, s, time.time(), os.getpid()


class SilentReceiver(RuntimeError):
    """A window without usable frames from a receiver (it stopped sending): the walk cannot be identified. Raised in the
    extraction worker before the extraction (which otherwise crashed on the empty receiver, IndexError, 15 Oct 2026, RX3)
    and caught by the app, which reports the walk as not identified and carries on (Uzayr, 15 Oct: the silent-receiver
    guard)."""


class DataEnded(SilentReceiver):
    """A walk pressed as the run stopped: the data of every receiver ends before its window has a second of it, so
    there is nothing to identify (the board runs' last press at 12:32 and 13:35 on 15 Oct came after the last frame;
    the app had decided it on no window data at all)."""


#: the guard: a receiver must cover the window with no gap longer than this (healthy data: at most about 0.1 s)
SILENT_GAP_S = 1.0


def _check_receivers(rx: dict, t0: float, end: float) -> None:
    """Raise SilentReceiver when a receiver's frames do not cover [t0, end]: fewer than two frames in it, or a gap over
    SILENT_GAP_S inside it or at either end. A healthy window never trips this, so no decision on good data changes.

    The window is checked only up to the newest frame of any receiver: a walk pressed in the run's last seconds is cut
    by the run's end for every receiver alike, and is decided on the data there is, as before the guard. With under
    SILENT_GAP_S of data in it, the walk raises DataEnded instead of blaming a receiver (15 Oct board test: the last
    press, as the run stopped, was reported as "RX1 silent")."""
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


def _frozen_extractor(job: dict):
    """An `Extractor` on a job's frozen copy of the receivers, as `_extract_window_job` builds it."""
    from pipeline.identify import engine as EN
    rx = {}
    for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
        r = EN.Receiver()
        r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
        rx[L] = r
    return EN.Extractor(job["T"], job["amp_norm"], job["layout"], job["names"], job["alpha"], rx=rx, cut=job["cut"])


def _checkpoints(e) -> np.ndarray:
    """The end detector's checkpoints, exactly as `Extractor.extract_v4` makes them."""
    from pipeline.identify import engine as EN
    return np.round(np.arange(EN.DIR_T_S, e.T + 1e-9, EN.DET_STEP_S), 2)


def _early_job(job: dict) -> tuple:
    """Engine v5's staged extraction, an early job: one stage of a window whose data ends before the window's end, on a frozen
    copy of the frames that had arrived by `frozen_at`. Stage "dir": the direction on [t0, e3] (its decision-time search,
    interpolation and `signal_measures`) and, when the 3.0 s checkpoint ends at e3, that checkpoint's RX2 band energy from the
    same interpolation (`extract_v4` makes the same search and interpolation twice). Stage k >= 1: checkpoint k's search,
    interpolation and band energy. The result is None when the stage's search did not settle within the copy (it could
    still change with frames that had not yet arrived); the late job then computes the stage itself. Returns (result,
    wall clock start, wall clock end, the worker's pid)."""
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


def _staged_extract_v4(e, w: dict, td: float, timed: list, early: dict, td_is_search: bool) -> tuple:
    """`Extractor.extract_v4`'s statements in its order, each stage taken from `early` when that result is for the same data
    end, else computed here by the same call. Two repeats are dropped where the value is provably the same: a checkpoint ending
    where the direction ends reuses the direction's interpolation (the same `t_dec_end` and `_raw` call on the same frames),
    and, when `td_is_search`, the checkpoint ending at the window's end uses the window's decision time `td` as its search
    (the engine's own scan of the same frames) and shares that interpolation with the speed (the same `_raw(t0, end, td)`).
    Returns (the extraction, how each stage was obtained)."""
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


def _late_job(job: dict) -> tuple:
    """Engine v5's staged extraction, the late job: the window at its decision time on a frozen copy of the frames that had
    arrived by then (as `_extract_window_job`), assembled by `_staged_extract_v4` from the early results sent with it.
    Returns (extraction, wall clock start, wall clock end, the worker's pid, how each stage was obtained)."""
    from pipeline.identify import engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    td = job["td"]
    _check_receivers(e.rx, float(job["w"]["t0"]), min(float(td), float(job["w"]["t0"]) + float(job["T"])))
    ex, how = _staged_extract_v4(e, job["w"], td, [e.rx[L].timed(td) for L in EN.LINKS], job["early"], job["td_is_search"])
    return ex, s, time.time(), os.getpid(), how


class PendingExtraction(dict):
    """Engine v5's parallel extraction: a window's extraction while its worker runs. The engine stores it where it stores
    any extraction and never reads it before classifying the window; the app fills it from the worker (`resolve`) just
    before that, so the engine only ever reads the worker's result. `sent`, `worker` and `waited_s` are timing only."""

    def __init__(self, fut, sent: float, staged: dict = None):
        super().__init__()
        self.fut, self.sent, self.worker, self.waited_s = fut, sent, None, None
        self.staged = staged       # staged extraction only: the dispatch's timing and each stage's source (timing only)

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


class ExtractPool:
    """Engine v5's parallel window extraction (Uzayr, 12 Oct): a pool of `n` worker processes, made once and warmed at app
    start (spawned, numpy and BLAS at one thread). Each of the engine's window extractors has its `extract_v4` replaced, on
    the instance, by a dispatch: the frames each receiver had by the window's decision time are copied and sent to a worker,
    which runs the engine's own extraction on them (`_extract_window_job`); the engine gets a `PendingExtraction`. Hooked
    again whenever the engine starts a new recording. engine.py is unchanged."""

    THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")

    def __init__(self, engine, n: int = EXTRACT_WORKERS_V5, staged: bool = False):
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        for k in self.THREAD_VARS:
            os.environ[k] = "1"
        self.e, self.n, self.staged = engine, int(n), bool(staged)
        x = engine.ex
        self.pool = ProcessPoolExecutor(max_workers=self.n, mp_context=mp.get_context("spawn"),
                                        initializer=_extract_worker_init, initargs=(x.amp_norm, x.names))
        list(self.pool.map(time.sleep, [0.5] * self.n))       # every worker started and warmed now, not at the first walk
        self.windows = {}         # staged: id(window) -> its early jobs, while the window is open
        self.polled = -np.inf     # staged: the last finite poll time; every frame up to it had reached the engine by then
        self.late_frames = 0      # staged: pushes holding a frame that arrived at or before the last poll (a late frame)
        self.hook()
        new_recording = engine.new_recording

        def renewed(layout=None):
            new_recording(layout)
            self.windows, self.polled = {}, -np.inf
            self.hook()
        engine.new_recording = renewed
        if self.staged:
            push = engine.push

            def pushed(link, frames):
                if len(frames) and float(np.min(frames["t_mono"])) <= self.polled:
                    self.late_frames += 1
                push(link, frames)
            engine.push = pushed

    def hook(self) -> None:
        for x in [self.e.ex] + list(self.e.ex_off.values()):
            if not getattr(x, "_pooled", False):
                x.extract_v4 = self._late(x) if self.staged else self._dispatch(x)
                x._pooled = True

    @staticmethod
    def _freeze(x, upto: float) -> dict:
        """Each receiver's frames that had arrived by `upto`, copied (`_dispatch`'s copy)."""
        rx = {}
        for L, r in x.rx.items():
            k = int(np.searchsorted(r.tm, upto, side="right"))
            rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
        return rx

    def _dispatch(self, x):
        def extract_v4(w, td, _timed):
            rx = {}
            for L, r in x.rx.items():
                k = int(np.searchsorted(r.tm, td, side="right"))
                rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
            job = {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
                   "w": dict(w), "td": float(td), "rx": rx}
            return PendingExtraction(self.pool.submit(_extract_window_job, job), time.time())
        return extract_v4

    def _job(self, x, w: dict, rx: dict) -> dict:
        return {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
                "w": dict(w), "rx": rx}

    def _late(self, x):
        """Staged: the window's late job at its decision time, with the early results that are done and final. A window
        that saw a late frame while it was open gets no early result and no shortcut (every stage is computed late)."""
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

    def early(self, now: float, send: bool = True, probe: bool = True) -> int:
        """Staged, after each finite poll: every open window's early stages whose data has ended by `now` and that have no
        final result or job in flight are sent, on a copy of the frames that had arrived by `now` (one copy per poll, the
        three windows' extractors sharing their receivers). `send` False (a poll that made a decision, so the decision is
        not held up): windows are registered and the poll time kept, nothing is sent. `probe`: send a stage only once every
        receiver's latest frame, on the causal clock at `now` (`Receiver.last_time`), is past the stage's data end, so the
        search is likely to settle within the copy. Returns the number of jobs sent."""
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
                    continue                                   # a late frame: this window's early results would be unused
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

    def close(self) -> None:
        self.pool.shutdown(wait=True)


class AfterDecision:
    """Engine v5 in the app (Uzayr, 11 Oct, option (c)): the engine's `Session`, with each walk's `add` (the walk joins the
    pool and the AdaBN copies are recomputed) held until its decision is written and shown. It runs at the start of the
    app's next poll; if a later walk is classified first (two walks decided in one poll, as at a recording's close), it runs
    just before that classification, once the earlier decision is written. Every walk is classified against exactly the
    pool it saw before, so no decision changes; only the moment of the adaptation moves. Everything else passes through."""

    def __init__(self, session, write_pending):
        self._s, self._write_pending = session, write_pending
        self._pending = None
        self.settles = []          # one per adaptation, in walk order: trigger, wall clock start and end, seconds

    def __getattr__(self, k):
        return getattr(self._s, k)

    def __len__(self):
        return len(self._s) + (self._pending is not None)

    def add(self, ex: dict) -> None:
        assert self._pending is None
        self._pending = ex

    def settle(self, trigger: str = "poll") -> bool:
        """The held walk joins the pool. trigger "poll": the app's next poll; "classify": a later walk waited for it."""
        if self._pending is None:
            return False
        if trigger == "classify":
            self._write_pending()
        ex, self._pending = self._pending, None
        w0 = time.time()
        self._s.add(ex)
        self.settles.append({"trigger": trigger, "wall_start": w0, "wall_end": time.time(), "update_s": self._s.update_s[-1]})
        return True

    def classify(self, ex: dict) -> dict:
        self.settle("classify")
        if isinstance(ex, PendingExtraction):
            ex.resolve()
        return self._s.classify(ex)


class EngineApp:
    """The app's logic around one engine: presses, decisions, round trip, walker tally, JSON lines."""

    def __init__(self, engine, model_name: str, replay: bool, jsonl: str = None, dmode: str = "detected",
                 extract_workers: int = None, extract_mode: str = None):
        self.e, self.model_name, self.replay, self.dmode = engine, model_name, replay, dmode
        self.v5 = bool(getattr(engine, "v5", False))
        self.written = 0              # engine v5: the engine's decisions written so far
        self.extract_pool = None      # engine v5: the warm extraction pool (None: serial extraction)
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
        self.skipped = []             # walks the silent-receiver guard could not identify (15 Oct 2026)
        self.last = None
        self.round_trip = None
        self.tally = None             # {"k", "logp"} after an `n`
        self.truth = {}               # press time -> who walked: recorded streams only, for the display and the log
        self.counting = True          # whether decisions count towards the running score (displayed walks)
        self.score = [0, 0]           # correct, scored
        self.names = code_names()
        self.stream_label = None
        self.jsonl = jsonl
        if jsonl:
            os.makedirs(os.path.dirname(jsonl), exist_ok=True)

    def _warm(self) -> None:
        """Engine v5: each CNN run once on zero windows of the usual shapes (10 to 12 windows of 28 x 34; three channels for
        cnn3, one for each link) before any press, in eval mode without gradients (`idv2_core.pass_logp`), its output
        discarded: no weight, statistic or pool changes, only the device's first-call cost paid before the first walk."""
        from pipeline.identify import idv2_core as C
        m = self.e.model
        for (tag, _s), net in sorted(m.nets.items()):
            ch = 3 if tag == "cnn3" else 1
            for k in (10, 11, 12):
                C.pass_logp(net, np.zeros((k, ch, 28, C.HP["win_frames"]), np.float32), np.zeros(k, int), np.zeros(k, int), 1, 6,
                            m.device)

    def press(self, t: float, path=None, source: str = None) -> None:
        """One press. path: None (detected), or a key's direction, or a known route (tracking replay)."""
        src = source or ("detected" if path is None else "key")
        self.e.press(t, path=path, info={"direction_source": src})

    def new_walker(self) -> None:
        self.tally = {"k": 0, "logp": np.zeros(6)}

    def poll(self, now: float, closing: bool = False) -> list:
        if self.v5:
            return self._poll_v5(now, closing)
        out = []
        for d in self.e.poll(now, closing):
            self._write(d)
            out.append(d)
        return out

    def _poll_v5(self, now: float, closing: bool) -> list:
        """Engine v5: the last decision is out (written, and shown after the last poll), so its walk joins the pool first;
        then the engine's poll, each new decision written. The MPS allocator's cache is released after a decision or an
        adaptation."""
        settled = self.e.session.settle("poll")
        try:
            got = self.e.poll(now, closing)
        except SilentReceiver as err:
            # the silent-receiver guard (15 Oct 2026): the engine had already taken this walk off its queue (it fails
            # only when its windows are resolved, after that) and never added it to the pool; the walks before it in
            # this poll are already in its decisions (written below); the walks after it are decided at the next poll
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

    def _write_pending(self) -> None:
        while self.written < len(self.e.decisions):
            self._write(self.e.decisions[self.written])
            self.written += 1

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
        d["truth_name"] = self.truth.get(d["t0"])              # read only after the decision exists
        if d["truth_name"] is not None and self.counting:
            self.score[1] += 1
            self.score[0] += int(self.names[d["top"]] == d["truth_name"])
        d["counted"] = bool(d["truth_name"] is not None and self.counting)
        self.last = d
        self.decisions.append(d)
        if self.jsonl:
            with open(self.jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(line_of(d, self.model_name, self.replay, EN.CLASSES, self.names)) + "\n")

    def state(self) -> dict:
        return {"last": self.last, "model": self.model_name, "replay": self.replay, "walks_seen": len(self.e.session),
                "open": self.e.open_windows, "round_trip": self.round_trip, "dmode": self.dmode, "names": self.names,
                "score": tuple(self.score), "stream": self.stream_label, "v5": bool(getattr(self.e, "v5", False)),
                "room": getattr(self.e, "room", None)}


def _norm(lp):
    lp = np.asarray(lp, float)
    m = lp.max()
    return lp - (m + np.log(np.exp(lp - m).sum()))


def line_of(d: dict, model: str, replay: bool, classes, names: dict = None) -> dict:
    """The JSON line of one decision (`reports/identification/live-interface.md`, schema v2: every v1 field, plus names)."""
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
    if d.get("engine_version", 4) >= 5:              # schema v3: every v2 field, plus engine v5's windows, components and room
        out["schema"] = "id_engine_decision_v3"
        out.update({"engine_version": int(d["engine_version"]), "room": d["room"], "weight_a": round(float(d["weight_a"]), 4),
                    "windows_s": [round(float(k), 2) for k in d["windows"]],
                    "window_decisions_mono": [float(w["t_dec"]) for w in d["windows"].values()],
                    "components": {f"{k:.2f}": {c: [round(float(x), 4) for x in v] for c, v in w["components"].items()}
                                   for k, w in d["windows"].items()},
                    "ensemble_without_pace_top": classes[int(np.argmax(d["ensemble_nopace"]))]})
    return out


# ------------------------------------------------------------------ the screen

class EngineScreen:
    """Draws what the app gives it and decides nothing. headless: renders to files."""

    def __init__(self, headless: bool = False):
        import matplotlib
        if headless:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        self.plt, self.headless = plt, headless
        self.fig = plt.figure(figsize=(12.0, 6.6))
        if not headless and self.fig.canvas.manager:
            self.fig.canvas.manager.set_window_title("identification: press SPACE in the Terminal window, not here")
        self.ax = self.fig.add_axes([0.03, 0.12, 0.36, 0.76])
        self.bx = self.fig.add_axes([0.47, 0.50, 0.50, 0.36])
        self.cx = self.fig.add_axes([0.47, 0.12, 0.23, 0.26])
        self.tx = self.fig.add_axes([0.74, 0.08, 0.24, 0.32])
        self.header = self.fig.text(0.03, 0.94, "", fontsize=14, weight="bold")
        self.caption = self.fig.text(0.03, 0.02, "", fontsize=9, color="0.25")
        if not headless:
            plt.ion()
            plt.show(block=False)

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
        ax.plot([2.5, 2.5], [0, 5], color="0.8", lw=4)
        for nm, (x, y) in {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": (2.0, -0.5), "RX3": (5.5, 2.5)}.items():
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
        if d is None:
            bx.axis("off")
            cx.axis("off")
            bx.text(0, 0.8, "press SPACE when the walker starts on line A", fontsize=12)
            tx.text(0, 1, "\n".join(lines), va="top", fontsize=9)
            self._show()
            return
        x = d["extraction"]
        way = DIR_WORD.get(x["path"], x["path"])
        if x["path"] in ("A_fwd", "A_rev"):
            y0, y1 = (0.3, 4.7) if x["path"] == "A_fwd" else (4.7, 0.3)
            ax.annotate("", xy=(2.5, y1), xytext=(2.5, y0), arrowprops={"arrowstyle": "-|>", "color": "tab:green", "lw": 3})
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
            self.caption.set_text("One press when the walker starts. The answer comes from three 4 s windows of Wi-Fi signal (0, "
                                  "0.15 and 0.30 s after the press): gait features and Doppler maps, nine models summed and the "
                                  "windows averaged. Displayed confidence is their geometric mean.")
        else:
            self.caption.set_text("One press when the walker starts. The answer comes from 3 s of Wi-Fi signal: gait features and "
                                  "Doppler maps, eight models summed. Displayed confidence is their geometric mean.")
        self._show()

    def _show(self):
        if self.headless:
            return
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def pump(self) -> None:
        """The window's events only (engine v5: between redraws); nothing is rebuilt."""
        if not self.headless:
            self.fig.canvas.flush_events()

    def save(self, path: str) -> None:
        self.fig.savefig(path, dpi=110)


# ------------------------------------------------------------------ the rig

class EngineConsumer:
    """`run_capture`'s extra consumer, and the recorded source's: frames in, keys on the same clock, the engine polled
    every tick.

    DATA-TIME ORDER (Uzayr's hardware test, 15 Oct 2026, "Fix H4 needs to be perfect"): frames are held as they arrive
    and handed to the engine in timestamp order, one group of equal `t_mono` at a time, and after each group the keys
    up to its time are applied and the engine is polled AT THAT TIME, never at a wall clock running ahead of frames
    still queued. A group is released only below the horizon (the oldest latest frame of the receivers still sending,
    and 0.05 s behind `now`), so every frame up to a poll's time has reached the engine at that poll. The engine then
    sees the same sequence live, streamed or replayed, whatever the serial reads' batching or the loop's stalls: a
    board run replays identically. Before this the rig polled at the wall clock while frames were still in the
    capture queue, so a window could be cut before its last frames arrived (its decisions then differed from the replay
    of its own recording, up to 0.577 in one ensemble probability) and the staged extraction's early results were
    discarded as late. The engine, the app and every decision rule are unchanged; only the order and the moment of
    what the engine is given."""
    owns_terminal = True
    #: a receiver whose latest frame is this far (data time) behind the newest no longer holds the others back
    SILENT_S = 1.0
    #: the release stays this far behind `now`, so a key stamped just before reaches the queue first
    KEY_SLACK_S = 0.05

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
        self.shown = None             # engine v5: what the screen last drew (`_seen`)
        self.held = []                # frames not yet given to the engine: (t_mono, receiver index, arrival, record)
        self.arrived = 0
        self.last_t = {}              # receiver -> its latest frame's t_mono
        self.keys_held = []           # keys not yet applied (applied once the data has passed their time)
        self.silent = set()           # receivers announced silent (the silent-receiver guard, 15 Oct 2026)

    def handle(self, rec) -> None:
        if rec.node_id in self.buf:
            t = float(rec.t_mono)
            self.held.append((t, self.nodes.index(rec.node_id), self.arrived, rec))
            self.arrived += 1
            self.last_t[rec.node_id] = max(self.last_t.get(rec.node_id, -np.inf), t)

    def _horizon(self, now: float) -> float:
        """Frames below this time are complete: every receiver still sending has delivered past it."""
        if not self.last_t:
            return -np.inf
        newest = max(self.last_t.values())
        return min(min(t for t in self.last_t.values() if t >= newest - self.SILENT_S), now - self.KEY_SLACK_S)

    def _take_keys(self) -> None:
        """Keys from the reader's queue: `q` acts at once, every other key waits for the data to pass its time."""
        while not self.keys.empty():
            ev = self.keys.get_nowait()
            if ev.key == "q":
                self.stop.set()
            else:
                self.keys_held.append(ev)

    def _release(self, upto: float, now: float) -> list:
        """Every held frame below `upto`, in timestamp order (ties: receiver, then arrival), one group of equal t_mono at a
        time: the group to the engine, then the keys up to its time, then the engine's poll at its time."""
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

    def finish(self) -> list:
        """The stream's end: every held frame and key given, then the closing poll (the rig's end, and end_stream's)."""
        got = self._release(np.inf, np.inf)
        self._keys(upto=np.inf)
        got += self.app.poll(np.inf, closing=True)
        return got

    def _flush(self) -> None:
        for n in self.nodes:
            if self.buf[n]:
                self.app.e.push(n, np.concatenate(self.buf[n]))
                self.buf[n] = []

    # -- a recorded stream: one per recording file (the rig itself is one stream) --------------------
    def new_stream(self, layout: str, display: bool = True, routes: dict = None) -> None:
        """A new capture stream: the receivers restart; the session's adaptation carries on. routes: the known
        route of each walk by press time (tracking recordings), else the detector decides."""
        if self.held:                                  # the previous stream's frames first (end_stream normally gave them)
            self._release(np.inf, np.inf)
        self.last_t = {}
        self.app.e.new_recording(layout)
        self.display, self.routes = display, dict(routes or {})
        self.app.counting = display

    def set_truth(self, t_press: float, name: str) -> None:
        self.app.truth[float(t_press)] = name

    def end_stream(self) -> None:
        self._after(self.finish(), np.inf)

    def _keys(self, upto: float = np.inf) -> None:
        """The held keys up to `upto`, in time order (data-time order: see the class docstring)."""
        self._take_keys()
        self.keys_held.sort(key=lambda e: float(e.t_mono))
        while self.keys_held and float(self.keys_held[0].t_mono) <= upto:
            ev = self.keys_held.pop(0)
            if ev.key == " ":
                route = self.routes.get(float(ev.t_mono))
                if route is not None:
                    self.app.press(ev.t_mono, path=route, source="known route")
                elif self.app.dmode == "detected":
                    self.app.press(ev.t_mono)
            elif ev.key in ("a", "t"):
                self.app.press(ev.t_mono, path="A_fwd" if ev.key == "a" else "A_rev", source="key")
            elif ev.key == "n":
                self.app.new_walker()

    def _seen(self, st: dict) -> tuple:
        """Engine v5: what the screen shows, beyond the clock: the last decision, the walks seen, whether a walk is in progress,
        the score and the stream."""
        return (None if st["last"] is None else st["last"]["t0"], st["walks_seen"], bool(st["open"]), tuple(st["score"]),
                st["stream"])

    def _after(self, got: list, now: float) -> None:
        if self.screen is None or not self.display:
            return
        if getattr(self.app, "v5", False):
            st = self.app.state()
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
            return
        if got or now - self.last_draw >= 0.1:
            self.last_draw = now
            self.screen.draw(self.app.state(), now)
            if got and self.snapshots:
                os.makedirs(self.snapshots, exist_ok=True)
                self.screen.save(os.path.join(self.snapshots, f"identify_{self.shots:04d}.png"))
                self.shots += 1

    def tick(self, now: float) -> None:
        """`now` is the stream's time: `run_capture` passes the host's `time.monotonic()` (the clock of `t_mono`
        and of the keys), the recorded source passes the recorded stream time. Nothing here reads a wall clock
        (brief 5.3; before 30 September 16:05 this polled `time.monotonic()` itself, wrong for recorded streams).
        Since 15 Oct 2026 the engine is polled in data-time order (the class docstring): the frames below the horizon are
        given group by group, each followed by its keys and a poll at its own time; `now` only bounds the horizon and
        paces the screen."""
        self._after(self._release(self._horizon(now), now), now)
        self._announce(now)

    def _announce(self, now: float) -> None:
        """The silent-receiver guard's messages: a receiver with no frame for over SILENT_S (rig.silent_receivers: in
        data time, so a stalled loop is no false alarm), and its return. Printed only; the decision path never reads
        them."""
        from pipeline.live.rig import silent_receivers
        silent = silent_receivers(self.last_t, now)
        for n in sorted(silent - self.silent):
            print(f"IDENTIFICATION: {n} is silent (no frames for over {self.SILENT_S:g} s); a walk while it is silent "
                  f"cannot be identified. Check its power and cable.", flush=True)
        for n in sorted(self.silent - silent):
            print(f"IDENTIFICATION: {n} is sending again.", flush=True)
        self.silent = silent


def training_sessions(md: str) -> list:
    """A model's training sessions: its manifest's `training_sessions`, else from its train_rows and bank."""
    p = os.path.join(md, "manifest.json")
    man = json.load(open(p)) if os.path.exists(p) else {}
    if "training_sessions" in man:
        return list(man["training_sessions"])
    meta = json.load(open(os.path.join(md, "meta_feat_cnn.json")))
    bank = os.path.join(REPO_ROOT, meta["cfg"]["bank"])
    sess = [q["session"] for q in json.load(open(os.path.join(bank, "meta.json")))["passes"]]
    return sorted({sess[int(i)] for i in np.load(os.path.join(md, "train_rows.npy"))})


def guard(md: str, session: str) -> list:
    """Refuses any model trained on the streamed session (brief 5.2)."""
    ts = training_sessions(md)
    if session in ts:
        raise SystemExit(f"REFUSED: {os.path.basename(md)} was trained on {ts}, which includes the streamed session {session}; "
                         f"a recorded stream needs a model that never saw it (for {session}: loso_{session})")
    return ts


def final_model(session: str) -> str:
    """The final engine's fold model that never saw `session`: the newest engine's that is built (v5, then v4, then v2
    `_x`), else v1's."""
    from pipeline.identify import engine as EN
    for name in (f"loso_{session}_v5", EN.model_name(f"loso_{session}"), f"loso_{session}_x"):
        if os.path.exists(os.path.join(model_dir(name), "meta_feat_cnn.json")):
            return name
    return f"loso_{session}"


def cmd_rig_recorded(a) -> int:
    """The rig run: a recorded session through the rig's interface (brief 5), the fold model that never saw it."""
    from pipeline.identify import engine as EN
    from pipeline.live.identify_recorded import RecordedSource, stream
    os.chdir(REPO_ROOT)
    model = a.model or final_model(a.session)
    md = model_dir(model) if not os.path.isabs(model) else model
    ts = guard(md, a.session)
    room = a.session[0]                             # a recorded stream's room comes from its session, never from its walks
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


def cmd_rig(a) -> int:
    """On the boards: the deployment model, from its manifest. Opens serial ports. `--source recorded` streams a
    recorded session instead (`cmd_rig_recorded`)."""
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
    os.chdir(REPO_ROOT)
    from pipeline.live.final_model import RigSteps, rig_banner      # the start-up status and READY banner (15 Oct)
    steps = RigSteps(4)
    print("IDENTIFICATION, the live app on the boards: starting (about half a minute)", flush=True)
    dev = rig_device(md, getattr(a, "device", None))
    steps.step(f"Loading the identification model {man['model']} on the {'GPU' if dev == 'mps' else 'CPU'}")
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"], layout="id_spot", device=dev, room=a.room)
    stem = time.strftime("rig_%Y%m%d_%H%M%S")
    steps.step("Starting and warming the extraction workers")
    app = EngineApp(eng, f"{man['model']} (all five sessions; room {a.room})", replay=False, jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"),
                    dmode=direction_mode(), extract_workers=getattr(a, "extract_workers", None),
                    extract_mode=getattr(a, "extract_mode", None))
    steps.step("Naming the boards by their MAC addresses")
    nodes = mapping_by_mac(identify(), room_a_macs(os.path.join(REPO_ROOT, "data")))
    nodes = {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    steps.step("Opening the identification window")
    c = EngineConsumer(app, EngineScreen(headless=False))
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                "SPACE once as each walker starts; n = a new walker; a / t = the route (away / towards); q quits.",
                "Keep the plot window visible during a walk (a hidden window can be slowed by macOS)."])
    # H3 (15 Oct 2026): rig.run keeps the run (packets through the capture writer, keys as received) so it replays
    rc = run(c, nodes, duration=a.minutes * 60.0 if a.minutes else None, mode="identify", stem=stem,
             run_config={"model": man["model"], "room": a.room, "device": str(getattr(eng.model, "device", None)),
                         "extract_mode": getattr(a, "extract_mode", None) or EXTRACT_MODE_V5,
                         "extract_workers": getattr(a, "extract_workers", None), "jsonl": app.jsonl})
    c.finish()                    # every held frame and key given, then the closing poll (data-time order, 15 Oct)
    rec = getattr(c, "record_dir", None)
    if rec:                       # the run's own measurements (H3, 15 Oct 2026): its adaptations as AfterDecision kept them
        with open(os.path.join(rec, f"{stem}.summary.json"), "w", encoding="utf-8") as f:
            json.dump({"model": man["model"], "room": a.room, "device": str(getattr(eng.model, "device", None)),
                       "decisions": len(app.decisions), "jsonl": app.jsonl, "exit": rc,
                       "settles": list(getattr(eng.session, "settles", []) or []),
                       "skipped_walks_silent_receiver": app.skipped}, f, indent=1, default=str)
    print(json.dumps({"decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return rc


# ------------------------------------------------------------------ replay

def replay_session(session: str, model: str = None, realtime: bool = False, speed: float = 1.0, screen: bool = False,
                   snapshots: str = None, device: str = "cpu", chunk_s: float = CHUNK_S, tally: bool = False,
                   jsonl: str = None, recordings: int = None, extract_workers: int = None,
                   extract_mode: str = None) -> EngineApp:
    """A recorded session through the app: frames pushed as they arrived (in `chunk_s` arrival blocks, or paced
    in real time), each recorded walk's start press replayed as the one press, the engine polled on the
    replay clock. model: the fold model that never saw the session (default `final_model(session)`)."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    os.chdir(REPO_ROOT)
    model = model or final_model(session)
    gs = IT.gs_adopted()
    dmode = RP.direction_mode()
    eng = EN.Engine(model_dir(model), T=EN.T_S, amp_norm=gs, device=device, room=session[0])   # the room: the session's
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


def cmd_replay(a) -> int:
    stem = f"replay_{a.session}_{time.strftime('%Y%m%d_%H%M%S')}"
    app = replay_session(a.session, model=a.model, realtime=a.realtime, speed=a.speed, screen=a.realtime or a.screen,
                         snapshots=a.snapshots, device=a.device, tally=a.tally,
                         jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"), recordings=a.recordings, extract_workers=a.extract_workers,
                         extract_mode=a.extract_mode)
    print(json.dumps({"session": a.session, "decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return 0


# ------------------------------------------------------------------ the command line

def main(argv=None) -> int:
    """`replay-identify --session <S> ...` or `rig --mode identify ...` (the same words `python3 -m pipeline.live`
    uses, so its dispatcher can hand these over unchanged)."""
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
