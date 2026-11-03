# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: I3 and I8, the extraction workers: a pool of helper processes, started and warmed when the app starts...

from __future__ import annotations

import os
import time

import numpy as np

EXTRACT_WORKERS = 4
EXTRACT_HELP = (f"worker processes for the windows' extraction (default {EXTRACT_WORKERS}: early jobs while each window is "
                "open, a late job at its decision time); 0 = serial extraction, the safe fallback (identical decisions, slower)")



# The window extraction in parallel: a pool of n worker processes, made once and warmed at app start...
class ExtractPool:

    THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")

    # Sets up the object.
    def __init__(self, engine, n: int = EXTRACT_WORKERS):
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        for k in self.THREAD_VARS:
            os.environ[k] = "1"
        self.e, self.n = engine, int(n)
        x = engine.ex
        self.pool = ProcessPoolExecutor(max_workers=self.n, mp_context=mp.get_context("spawn"),
                                        initializer=_extract_worker_init, initargs=(x.amp_norm, x.names, x.alpha))
        list(self.pool.map(time.sleep, [0.5] * self.n))
        self.windows = {}
        self.polled = -np.inf
        self.late_frames = 0

    # Frames the engine is about to take: a frame older than the last poll makes the open windows' early results...
    def arrived(self, frames) -> None:
        if len(frames) and float(np.min(frames["t_mono"])) <= self.polled:
            self.late_frames += 1

    # A new recording: no window is open.
    def reset(self) -> None:
        self.windows, self.polled = {}, -np.inf

    # Each receiver's frames that had arrived by upto, copied (what a job is sent).
    @staticmethod
    def _freeze(x, upto: float) -> dict:
        rx = {}
        for L, r in x.rx.items():
            k = int(np.searchsorted(r.tm, upto, side="right"))
            rx[L] = tuple(a[:k].copy() for a in (r.tm, r.lt, r.ep, r.amp, r.rssi))
        return rx

    # Function job.
    def _job(self, x, w: dict, rx: dict) -> dict:
        return {"T": x.T, "amp_norm": x.amp_norm, "layout": x.layout, "names": x.names, "alpha": x.alpha, "cut": x.cut,
                "w": dict(w), "rx": rx}

    # A window at its decision time: its late job sent to a worker, with the early results that are done and...
    def late(self, x, w: dict, td: float) -> "PendingExtraction":
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

    # Staged, after each finite poll: every open window's early stages whose data has ended by now and that have...
    def early(self, now: float, send: bool = True, probe: bool = True) -> int:
        import pipeline.identification.engine as EN
        if not np.isfinite(now):
            return 0
        self.polled = max(self.polled, float(now))
        sent = 0
        frozen = {}
        for x in [self.e.ex] + list(self.e.ex_off.values()):
            if not x.pending:
                continue
            cs = x.checkpoints()
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


# A window's extraction while its worker runs; the engine waits for it (resolve) when it classifies the walk.
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


# One window extracted from made-up frames, exactly as a worker's late job extracts a real one.
def warm_window(amp_norm: bool, names: list, alpha: float) -> dict:
    import pipeline.identification.engine as EN
    from pipeline.io.serial_capture import FRAME_DTYPE
    e = EN.Extractor(EN.T_S, amp_norm, "home", names, alpha)
    rng = np.random.default_rng(0)
    n = int(6.0 * EN.FS)
    for j, L in enumerate(EN.LINKS):
        fr = np.zeros(n, FRAME_DTYPE)
        fr["t_mono"] = 100.0 + np.arange(n) / EN.FS + 0.001 * j
        fr["t_host"] = fr["t_mono"]
        fr["local_timestamp"] = (1_000_000 + np.arange(n) * (1e6 / EN.FS)).astype(np.uint64)
        fr["rssi"], fr["channel"], fr["gain"] = -50, 11, 1.0
        fr["data"] = rng.integers(-40, 40, (n, fr["data"].shape[1])).astype(np.int8)
        e.push(L, fr)
    for r in e.rx.values():
        r.consolidate()
    e.press(100.5, "A_fwd", "home")
    w = e.pending[-1]
    td = e.t_dec_end(w["t0"], e._end(w))
    return e.extract(w, td, [e.rx[L].timed(td) for L in EN.LINKS], {}, True)[0]


# A worker of the parallel extraction: one made-up window extracted at start, so the first walk pays no...
def _extract_worker_init(amp_norm: bool, names: list, alpha: float = None) -> None:
    try:
        warm_window(amp_norm, names, alpha)
    except Exception:
        pass



# An early job: one stage of a window (its direction, or one end-detector checkpoint) whose data ends before...
def _early_job(job: dict) -> tuple:
    import pipeline.identification.engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    w, frz, stage = job["w"], job["frozen_at"], job["stage"]
    t0, end = w["t0"], e._end(w)
    cs = e.checkpoints()
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


# The late job: the window at its decision time on a frozen copy of the frames that had arrived by then...
def _late_job(job: dict) -> tuple:
    import pipeline.identification.engine as EN
    s = time.time()
    e = _frozen_extractor(job)
    td = job["td"]
    _check_receivers(e.rx, float(job["w"]["t0"]), min(float(td), float(job["w"]["t0"]) + float(job["T"])))
    ex, how = e.extract(job["w"], td, [e.rx[L].timed(td) for L in EN.LINKS], job["early"], job["td_is_search"])
    return ex, s, time.time(), os.getpid(), how


# An extractor on a job's frozen copy of the receivers.
def _frozen_extractor(job: dict):
    import pipeline.identification.engine as EN
    rx = {}
    for L, (tm, lt, ep, amp, rssi) in job["rx"].items():
        r = EN.Receiver()
        r.tm, r.lt, r.ep, r.amp, r.rssi = tm, lt, ep, amp, rssi
        rx[L] = r
    return EN.Extractor(job["T"], job["amp_norm"], job["layout"], job["names"], job["alpha"], rx=rx, cut=job["cut"])



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
