# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Tracking, run: on the boards (on_the_boards, T4 to T11: the pre-flight again, the tracker, the boards by...

from __future__ import annotations

import base64
import json
import os
import queue
import sys
import threading
import time
import types

import numpy as np

from pipeline.io.boards import REPO_ROOT, KeyEvent, KeyReader, RigSteps, receiver_ports, rig_banner, run, silent_receivers, SILENT_S
from pipeline.io.serial_capture import read_capture_file, run_capture
from pipeline.io.signals import DEVICE_CLOCK_MODULUS_US, WRAP_MARGIN_US, baseline_dir_for, fit_timebase, session_baseline
from pipeline.tracking import networks
from pipeline.tracking.screen import Screen
from pipeline.tracking.session import Logger, Session
from pipeline.tracking.settings import name_text, pa_text
from pipeline.tracking.tracker import DISPLAY_PROFILE, TRACKER, load, preflight, print_checks

J = os.path.join
REFRESH_S = 0.1
KEYS_TITLE_TRACKING = "tracking: press SPACE in the Terminal window, not here"



# ON THE BOARDS: opens the serial ports.
def on_the_boards(baseline: str, minutes: float = None, folder: str = TRACKER) -> int:
    networks.use_cpu()
    steps = RigSteps(4)
    print("TRACKING, the live app on the boards: starting", flush=True)
    steps.step("Pre-flight: checking the shipped model's files and the baseline")
    chk = preflight(baseline, folder=folder)
    print_checks(chk)
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was opened")
    steps.step("Loading the tracking model: five networks, the readers and the start terms")
    tracker = load(folder)
    steps.step("Naming the boards by their MAC addresses")
    nodes = receiver_ports()
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    s = Session(tracker, session="live", stem=time.strftime("rig_final_%Y%m%d_%H%M%S"),
                baseline=session_baseline(baseline))
    log = Logger(s)
    steps.step("Opening the tracking window")
    con = LoggedConsumer(s, Screen(s.st, headless=False, title=KEYS_TITLE_TRACKING), log)
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                "Stand still for 10 s, then press SPACE once as each walk starts (at the start tape).",
                "q quits."])
    rc = None
    try:
        rc = run(con, nodes, duration=minutes * 60.0 if minutes else None, mode="tracking", stem=s.stem,
                 run_config={"model": "final", "mode": "semi", "cell": tracker.meta["cell"],
                             "display_profile": DISPLAY_PROFILE, "baseline": os.path.abspath(baseline)})
    finally:
        write_record(con, s, log, chk, baseline, tracker.meta["cell"], rc)
    os.makedirs(J(REPO_ROOT, "runs", "live", "rig"), exist_ok=True)
    with open(J(REPO_ROOT, "runs", "live", "rig", f"{s.stem}.json"), "w", encoding="utf-8") as f:
        json.dump({**con.summary(), "model": "final", "mode": "semi", "stats": s.stats,
                   "first_lock": s.first_lock, "lock_changes": s.lock_changes},
                  f, indent=1, default=str)
    return rc



# Class Tracking Consumer.
class TrackingConsumer:
    owns_terminal = True

    # Sets up the object.
    def __init__(self, session, screen=None, nodes=("RX1", "RX2", "RX3")):
        self.s, self.screen, self.nodes = session, screen, tuple(nodes)
        self.anchor = {n: CausalAnchor() for n in self.nodes}
        self.held = {n: {} for n in self.nodes}
        self.keys = queue.Queue()
        self.stop = threading.Event()
        self.pid = 0
        self.last_draw = 0.0
        self.refused = None
        self.last_pkt = {}
        self.silent, self.outages = set(), []

    # A start press, refused cleanly.
    def _press(self, pid: int, t: float) -> None:
        if getattr(getattr(self.s, "stream", None), "first_base", 0) is None:
            self.refused = ("REFUSED: no packets had reached the app before the first press; stand still for at least "
                            "10 s before the first walk")
            self.stop.set()
            raise SystemExit(self.refused)
        try:
            self.s.press(pid, t)
        except SystemExit as e:
            self.refused = str(e)
            self.stop.set()
            raise

    # The silent-receiver guard for tracking: tracking cuts a window only when every receiver has data, so a...
    def _announce(self, now: float) -> None:
        silent = silent_receivers(self.last_pkt, now)
        for n in sorted(silent - self.silent):
            print(f"TRACKING: {n} is silent (no frames for over {SILENT_S:g} s); a walk while it is silent cannot be "
                  f"tracked reliably. Check its power and cable.", flush=True)
            self.outages.append({"node": n, "from": float(self.last_pkt[n]), "to": None})
        for n in sorted(self.silent - silent):
            print(f"TRACKING: {n} is sending again.", flush=True)
            for o in reversed(self.outages):
                if o["node"] == n and o["to"] is None:
                    o["to"] = float(self.last_pkt[n])
                    break
        self.silent = silent

    # Function handle.
    def handle(self, rec) -> None:
        n = rec.node_id
        if n not in self.anchor or self.refused is not None:
            return
        self.last_pkt[n] = float(rec.t_mono)
        self.s.rssi(n, rec.t_host, rec.rssi)
        a = self.anchor[n]
        self.held[n][len(a.local)] = (amplitude(rec.data), rec.t_host, rec.t_mono)
        for i, t in a.push(rec.local_timestamp, rec.t_mono):
            amp, t_host, t_mono = self.held[n].pop(i)
            self.s.csi(n, t, amp, t_host, t_mono)

    # Function tick.
    def tick(self, now: float) -> None:
        self._announce(now)
        while not self.keys.empty():
            ev = self.keys.get_nowait()
            if ev.key == "q":
                self.stop.set()
            elif ev.key == " ":
                self.pid += 1
                self._press(self.pid, ev.t_mono)
        if self.screen is not None and now - self.last_draw >= REFRESH_S:
            self.last_draw = now
            self.screen.tracking(**self.s.screen_state(now))

    # Function summary.
    def summary(self) -> dict:
        return {"passes": self.pid, "decisions": self.s.decisions, "timing": {k: len(v) for k, v in self.s.timing.items()}}


# The board run's consumer: every packet and tick also stamped in the log (T11), and the screen's redraws...
class LoggedConsumer(TrackingConsumer):
    ticks, redraws = 0, 0

    # Sets up the object.
    def __init__(self, session, screen, log):
        super().__init__(session, screen)
        self.log = log

    # Function handle.
    def handle(self, r):
        self.log.event(time.monotonic())
        super().handle(r)

    # Function tick.
    def tick(self, now):
        self.log.event(time.monotonic())
        super().tick(now)
        self.ticks += 1
        self.redraws += int(self.last_draw == now)


# One record's amplitude, as signals.load_node makes it from a file: sqrt(I^2 + Q^2) over 128 subcarriers.
def amplitude(data) -> np.ndarray:
    d = np.asarray(data, np.int8).astype(np.float32).reshape(128, 2)
    return np.sqrt((d ** 2).sum(-1))



REFIT_S = 10.0


MIN_PACKETS = 100


# One receiver.
class CausalAnchor:

    # Sets up the object.
    def __init__(self, refit_s: float = REFIT_S):
        self.refit_s = float(refit_s)
        self.local, self.mono, self.x = [], [], []
        self.wraps, self.tb, self.fit_at, self.timed = 0, None, None, 0

    # Function push.
    def push(self, local_us: int, t_mono: float) -> list:
        local_us = int(local_us)
        if self.local and local_us < self.local[-1] and self.local[-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US:
            self.wraps += 1
        self.local.append(local_us)
        self.mono.append(float(t_mono))
        self.x.append(float(local_us + self.wraps * DEVICE_CLOCK_MODULUS_US))
        n = len(self.local)
        due = self.tb is None or (self.mono[-1] - self.fit_at >= self.refit_s)
        if due and n >= MIN_PACKETS:
            tb = fit_timebase(np.asarray(self.local, np.int64), np.asarray(self.mono, np.float64))
            if tb.ok:
                self.tb, self.fit_at = tb, self.mono[-1]
        if self.tb is None:
            return []
        out = [(i, float(self.tb.slope * self.x[i] + self.tb.offset)) for i in range(self.timed, n)]
        self.timed = n
        return out



# The session closed and the log finished, then (when the run was recorded) the log, the sidecar of presses...
def write_record(con, s, log, chk: dict, baseline: str, cell, rc) -> None:
    log.event(time.monotonic())
    close_error = None
    try:
        s.close()
    except Exception as e:
        close_error = f"{type(e).__name__}: {e}"
    log.finish()
    rec = getattr(con, "record_dir", None)
    if rec:
        with open(J(rec, f"{s.stem}.log.jsonl"), "w", encoding="utf-8") as f:
            for r_ in log.rows:
                f.write(json.dumps(r_, default=float) + "\n")
        with open(J(rec, f"{s.stem}.gt.json"), "w", encoding="utf-8") as f:
            json.dump({"rig": True, "mode": "semi", "baseline": os.path.abspath(baseline),
                       "baseline_capture": os.path.abspath(baseline), "session": "live",
                       "cell": cell, "display_profile": DISPLAY_PROFILE,
                       "passes": [{"pass_id": int(pid), "t_start": float(p["press"]),
                                   "t_end": None}
                                  for pid, p in sorted(s.passes.items())]}, f, indent=1)
        ws = [float(x) for x, prov in s.timing["window_s"] if not prov]
        dots = [r_ for r_ in log.rows if r_["kind"] == "dot" and r_.get("computed_at") is not None]
        lag = [max(0.0, float(r_["computed_at"]) - float(r_["x"])) for r_ in dots]
        lock_late = [float(r_["at"]) - (float(s.passes[r_["pid"]]["press"]) + 2.0)
                     for r_ in log.rows if r_["kind"] == "lock" and r_["pid"] in s.passes]
        q_ = lambda v, p_: float(np.percentile(v, p_)) if v else None
        with open(J(rec, f"{s.stem}.summary.json"), "w", encoding="utf-8") as f:
            json.dump({"device": str(networks.device()), "display_profile": DISPLAY_PROFILE, "mode": "semi",
                       "preflight": chk, "passes": len(s.passes), "committed": len(s.decisions),
                       "locks": len(log.locks), "frames": log.n_frames, "ticks": con.ticks, "redraws": con.redraws,
                       "window_service_s": {"median": q_(ws, 50), "p95": q_(ws, 95), "max": max(ws) if ws else None,
                                            "n": len(ws), "values": ws},
                       "press_service_s": {"median": q_(s.timing["press_s"], 50),
                                           "max": max(s.timing["press_s"]) if s.timing["press_s"] else None,
                                           "values": [float(x) for x in s.timing["press_s"]]},
                       "draw_lag_s": {"median": q_(lag, 50), "max": max(lag) if lag else None,
                                      "frames_late_over_0.1s": int(sum(x > 0.1 for x in lag)),
                                      "frames_late_over_0.5s": int(sum(x > 0.5 for x in lag)), "n": len(lag)},
                       "lock_late_s": {"median": q_(lock_late, 50), "max": max(lock_late) if lock_late else None},
                       "exit": rc, "close_error": close_error,
                       "receiver_outages": con.outages,
                       "walks_overlapping_an_outage": sorted(int(pid) for pid, p in s.passes.items()
                                                             for o in con.outages if p["press"] - 1.0 <= (o["to"] or np.inf)
                                                             and p["press"] + 10.0 >= o["from"])}, f, indent=1, default=str)



OUT = J(REPO_ROOT, "runs", "live", "stream")


NODES = ("RX1", "RX2", "RX3")
TX_MAC = "1a:00:00:00:00:00"
SESSIONS = {"A1": J("room_A", "session_01"), "A2": J("room_A", "session_02"), "A3": J("room_A", "session_03"),
            "B1": J("room_B", "session_B1"), "B2": J("room_B", "session_B2")}
CODES = {"A1": "01", "A2": "02", "A3": "03", "B1": "B1", "B2": "B2"}
_INT = ("pkt_id", None, "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
        "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
        "ant", "sig_len", "rx_format", None, "first_word")
NO_DATA = ("REFUSED: --stream needs the recordings in data/: download room_A_anon.zip and room_B_anon.zip and unzip them in "
           "the repository root (README, \"Run the thesis code on the recorded data\")")


# NO BOARDS: a recorded walk from data/, streamed in real time through the boards' path (run_capture with...
def stream(session: str, stem: str, speed: float = 1.0, window: bool = True, screen_dir: str = None,
           folder: str = TRACKER) -> dict:
    networks.use_cpu()
    os.chdir(REPO_ROOT)
    shown, stem = pa_text(stem), name_text(stem)
    sdir, frames, sidecar = load_recording(session, stem)
    base_dir = baseline_dir_for(sdir, stem)
    t_rec_host = min(float(frames[n]["t_host"][0]) for n in NODES)
    print(f"STREAMED TRACKING: {session}/{shown}, {len(sidecar['passes'])} walks, speed {speed:g}, on the CPU", flush=True)
    chk = preflight(base_dir, at=t_rec_host, folder=folder, boards=False)
    print_checks(chk)
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was streamed")
    tracker = load(folder)
    if CODES[session] in tracker.meta["train"]:
        print(f"NOTE: the frozen tracker was trained on {session}; A3 and B2 are the sessions it never saw", flush=True)
    print("Loading the tracking model and building the replay ports", flush=True)
    s = Session(tracker, session="live", stem=shown, baseline=session_baseline(base_dir))
    log = Logger(s)
    t_rec0 = min(float(frames[n]["t_mono"][0]) for n in NODES)
    t_rec1 = max(float(frames[n]["t_mono"][-1]) for n in NODES)
    presses = sorted(float(p["t_start"]) for p in sidecar["passes"])
    ports = {n: ReplayPort(frames[n], t_rec0, 0.0, speed) for n in NODES}
    grab = [None]

    # Class Consumer.
    class Consumer(TrackingConsumer):
        # Function handle.
        def handle(self, r):
            log.event(time.monotonic())
            super().handle(r)

        # Function tick.
        def tick(self, now):
            log.event(time.monotonic())
            super().tick(now)
            if grab[0] is not None and self.last_draw == now:
                grab[0].grab()

    scr = None
    if screen_dir or window:
        scr = Screen(s.st, headless=bool(screen_dir), title=f"streamed run: {session}/{shown} (q in the Terminal stops)")
        if screen_dir:
            grab[0] = Grabber(scr, J(screen_dir, f"stream_{session}_{shown}.mp4"))
    con = Consumer(s, scr)
    sys.modules["serial"] = serial_module({f"replay://{n}": ports[n] for n in NODES})
    t_wall0 = time.monotonic() + 2.0
    for p_ in ports.values():
        p_.t_wall0 = t_wall0
    delta = t_wall0 - t_rec0
    s.set_truth(shifted_truth(sidecar, delta))

    # Function inject.
    def inject():
        for P in presses:
            due = t_wall0 + (P - t_rec0) / speed
            while time.monotonic() < due:
                time.sleep(min(0.002, max(0.0, due - time.monotonic())))
            con.keys.put(KeyEvent(key=" ", t_mono=time.monotonic(), t_host=time.time()))
    threading.Thread(target=inject, daemon=True).start()
    print("STREAMING: the walks start as recorded; q in this Terminal stops", flush=True)
    d = J(OUT, f"{session}__{shown}")
    cap_dir = J(d, "capture")
    os.makedirs(cap_dir, exist_ok=True)
    states, stop_keys = {}, threading.Event()
    t_start = time.time()
    with KeyReader(QuitOnly(con.keys), stop_keys):
        rc = run_capture({n: f"replay://{n}" for n in NODES}, duration=1.0 + (t_rec1 - t_rec0) / speed + 3.0,
                         extra_consumers=[con], stop_when=con.stop.is_set, quiet_monitor=True, states_out=states,
                         out_dir=cap_dir, timestamped_subdir=False, writer_prefix=f"{shown}_",
                         run_config={"stream": f"{session}/{shown}", "speed": speed, "tracker": os.path.relpath(folder, REPO_ROOT)})
    log.event(time.monotonic())
    s.close()
    log.finish()
    video = grab[0].close() if grab[0] is not None else None
    lock_late = [float(r["at"]) - (float(s.passes[r["pid"]]["press"]) + 2.0) for r in log.rows if r["kind"] == "lock"]
    ends = {i + 1: float(p["t_end"]) + delta for i, p in enumerate(sorted(sidecar["passes"], key=lambda q: q["t_start"]))}
    ann_late = [float(r["at"]) - ends[r["pid"]] for r in log.rows if r["kind"] == "committed" and r["pid"] in ends]
    dots = [r for r in log.rows if r["kind"] == "dot"]
    lag = [max(0.0, float(r["computed_at"]) - float(r["x"])) for r in dots if r["computed_at"] is not None]
    ws = [x for x, prov in s.timing["window_s"] if not prov]
    q = lambda v, p: float(np.percentile(v, p)) if v else None
    summ = {"session": session, "stem": shown, "speed": speed, "exit": rc, "delta_s": delta,
            "tracker": os.path.relpath(folder, REPO_ROOT), "wall_minutes": round((time.time() - t_start) / 60.0, 2),
            "n_presses_injected": len(presses), "n_committed": len(s.decisions), "n_locks": len(log.locks),
            "n_frames": len(dots),
            "window_service_s": {"median": q(ws, 50), "p95": q(ws, 95), "max": max(ws) if ws else None, "n": len(ws)},
            "lock_late_s": {"median": q(lock_late, 50), "p90": q(lock_late, 90), "max": max(lock_late) if lock_late else None},
            "announce_after_walk_end_s": {"median": q(ann_late, 50), "p90": q(ann_late, 90),
                                          "max": max(ann_late) if ann_late else None},
            "frames_late": {"over_0.1s": int(sum(1 for x in lag if x > 0.1)), "over_0.5s": int(sum(1 for x in lag if x > 0.5)),
                            "max_s": max(lag) if lag else None},
            "receivers": {n: {"queue_dropped": int(getattr(st_, "queue_dropped", 0)),
                              "parsed_ok": int(getattr(getattr(st_, "counters", None), "ok", 0)),
                              "read_errors": int(getattr(st_, "read_errors", 0))} for n, st_ in states.items()},
            "video": video, "presses": {int(pid): float(p["press"]) for pid, p in s.passes.items()}}
    sc = shifted_truth(sidecar, delta)
    got = [float(p_["press"]) for _pid, p_ in sorted(s.passes.items())]
    for p_, t in zip(sorted(sc["passes"], key=lambda q: q["t_start"]), got):
        p_["t_start"] = t
    with open(J(cap_dir, f"{shown}.gt.json"), "w", encoding="utf-8") as f:
        f.write(pa_text(json.dumps(sc)))
    with open(J(d, "log.jsonl"), "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    with open(J(d, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=str)
    walks = [r for r in log.rows if r["kind"] == "committed"]
    print(f"DONE: {len(walks)} walks committed, {len(log.locks)} locks; {os.path.relpath(d, REPO_ROOT)}/", flush=True)
    for r in walks:
        t = (s.truth or {}).get(f"live|{shown}|{int(r['pid'])}") if hasattr(s, "truth") else None
        print(f"  walk {int(r['pid']):2d}: {r['line']}" + (f" (walked {t['path_name']})" if t and t.get("path_name") else ""),
              flush=True)
    return summ


# Function load recording.
def load_recording(session: str, stem: str):
    if session not in SESSIONS:
        raise SystemExit(f"REFUSED: session {session!r}: one of {', '.join(SESSIONS)}")
    sdir = J(REPO_ROOT, "data", SESSIONS[session])
    if not os.path.isdir(sdir):
        raise SystemExit(NO_DATA)
    if not os.path.exists(J(sdir, f"{stem}.gt.json")):
        stems = sorted(pa_text(f[:-8]) for f in os.listdir(sdir) if f.endswith(".gt.json"))
        raise SystemExit(f"REFUSED: {session} has no recording {pa_text(stem)!r}; its recordings: {', '.join(stems)}")
    frames = {n: read_capture_file(J(sdir, f"{stem}_{n}.bin"))[1] for n in NODES}
    with open(J(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    return sdir, frames, sidecar


# Function shifted truth.
def shifted_truth(sidecar: dict, delta: float) -> dict:
    out = json.loads(json.dumps(sidecar))
    for p in out.get("passes", []):
        for k in ("t_start", "t_end"):
            if p.get(k) is not None:
                p[k] = float(p[k]) + delta
        p["anchor_times"] = [float(t) + delta for t in p.get("anchor_times", [])]
    return out


# Function frame to line.
def frame_to_line(fr, mac: str = TX_MAC) -> str:
    parts = ["CSI_DATA"]
    for name in _INT:
        if name is None:
            parts.append(mac if len(parts) == 2 else "256")
        else:
            parts.append(str(int(fr[name])))
    parts.append(str(int(round(float(fr["gain"]) * 10000.0))))
    parts.append(base64.b64encode(np.asarray(fr["data"], np.int8).tobytes()).decode("ascii"))
    return ",".join(parts)


# Class Replay Port.
class ReplayPort:

    # Sets up the object.
    def __init__(self, frames, t_rec0: float, t_wall0: float, speed: float = 1.0, timeout: float = 0.05):
        self.lines = [(float(f["t_mono"]) - t_rec0, (frame_to_line(f) + "\n").encode("ascii")) for f in frames]
        self.i, self.t_wall0, self.speed, self.timeout = 0, float(t_wall0), float(speed), float(timeout)
        self.closed = False

    # Function read.
    def read(self, n: int = 4096) -> bytes:
        if self.i >= len(self.lines):
            time.sleep(self.timeout)
            return b""
        el = (time.monotonic() - self.t_wall0) * self.speed
        if self.lines[self.i][0] > el:
            time.sleep(min(self.timeout, (self.lines[self.i][0] - el) / self.speed))
            el = (time.monotonic() - self.t_wall0) * self.speed
        out = bytearray()
        while self.i < len(self.lines) and self.lines[self.i][0] <= el and len(out) + len(self.lines[self.i][1]) <= n:
            out += self.lines[self.i][1]
            self.i += 1
        return bytes(out)

    # Function close.
    def close(self) -> None:
        self.closed = True


# Function serial module.
def serial_module(ports: dict):
    mod = types.ModuleType("serial")

    # Class Serial Exception.
    class SerialException(Exception):
        pass

    # Function Serial.
    def Serial(port, baud=None, timeout=None, **_k):
        if port not in ports:
            raise SerialException(f"no replay registered for {port}")
        p = ports[port]
        if timeout is not None:
            p.timeout = float(timeout)
        return p
    mod.Serial, mod.SerialException = Serial, SerialException
    return mod


# Class Quit Only.
class QuitOnly:

    # Sets up the object.
    def __init__(self, q):
        self.q = q

    # Function put nowait.
    def put_nowait(self, ev) -> None:
        if ev.key == "q":
            self.q.put_nowait(ev)

    # Function put.
    def put(self, ev, block: bool = True, timeout=None) -> None:
        self.put_nowait(ev)


# Class Grabber.
class Grabber:

    # Sets up the object.
    def __init__(self, scr, path: str):
        import shutil
        import subprocess
        if shutil.which("ffmpeg") is None:
            raise SystemExit("REFUSED: --screen records with ffmpeg, which is not on the PATH (brew install ffmpeg)")
        self.scr, self.path, self.n = scr, path, 0
        scr.fig.canvas.draw()
        self.w, self.h = scr.fig.canvas.get_width_height()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                                    "-s", f"{self.w}x{self.h}", "-r", "10", "-i", "-", "-threads", "1", "-c:v", "libx264",
                                    "-pix_fmt", "yuv420p", "-crf", "20", path], stdin=subprocess.PIPE)

    # Function grab.
    def grab(self):
        self.scr.fig.canvas.draw()
        self.ff.stdin.write(bytes(self.scr.fig.canvas.buffer_rgba()))
        self.n += 1

    # Function close.
    def close(self):
        self.ff.stdin.close()
        return {"video": os.path.relpath(self.path, REPO_ROOT), "frames": self.n, "exit": self.ff.wait()}
