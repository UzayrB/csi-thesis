# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The streamed tracking run: one recorded walk recording fed to the frozen tracker in wall-clock time through the boards' own ingestion path (run_capture, the serial readers, parse_line, the rig's TrackingConsumer), with a stand-in serial module in place of the three receivers.

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import types

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
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


# One recorded frame as the firmware's base64 CSI_DATA row (the inverse of pipeline.io.parse.parse_line).
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


# A serial port that replays one receiver: each line is readable once the wall clock passes its recorded time.
class ReplayPort:

    # Sets up the object.
    def __init__(self, frames, t_rec0: float, t_wall0: float, speed: float = 1.0, timeout: float = 0.05):
        self.lines = [(float(f["t_mono"]) - t_rec0, (frame_to_line(f) + "\n").encode("ascii")) for f in frames]
        self.i, self.t_wall0, self.speed, self.timeout = 0, float(t_wall0), float(speed), float(timeout)
        self.closed = False

    # Every due line up to n bytes; with nothing due it waits up to the timeout, then returns b"".
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


# A stand-in serial module whose Serial(port) returns the ReplayPort registered for that port name.
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


# A recording's folder, its three receivers' frames and its sidecar.
def load_recording(session: str, stem: str):
    from pipeline.io.capture_logger import read_capture_file
    if session not in SESSIONS:
        raise SystemExit(f"REFUSED: session {session!r}: one of {', '.join(SESSIONS)}")
    sdir = J(REPO_ROOT, "data", SESSIONS[session])
    if not os.path.isdir(sdir):
        raise SystemExit(NO_DATA)
    if not os.path.exists(J(sdir, f"{stem}.gt.json")):
        stems = sorted(f[:-8] for f in os.listdir(sdir) if f.endswith(".gt.json"))
        raise SystemExit(f"REFUSED: {session} has no recording {stem!r}; its recordings: {', '.join(stems)}")
    frames = {n: read_capture_file(J(sdir, f"{stem}_{n}.bin"))[1] for n in NODES}
    with open(J(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    return sdir, frames, sidecar


# The sidecar with every time moved onto the stream's clock (the screen's replay-only overlay).
def shifted_truth(sidecar: dict, delta: float) -> dict:
    out = json.loads(json.dumps(sidecar))
    for p in out.get("passes", []):
        for k in ("t_start", "t_end"):
            if p.get(k) is not None:
                p[k] = float(p[k]) + delta
        p["anchor_times"] = [float(t) + delta for t in p.get("anchor_times", [])]
    return out


# The pre-flight of a streamed run: the frozen tracker's checks, the baseline recent against the recording's start, no boards.
def stream_preflight(base_dir: str, at: float, folder: str) -> dict:
    from pipeline.live import frozen_model as FZ
    chk = FZ.preflight(base_dir, at=at, folder=folder)
    chk.pop("boards.json names RX1, RX2 and RX3", None)
    chk.pop("ALL", None)
    chk["ALL"] = all(chk.values())
    return chk


# Only q reaches the app from the terminal (a SPACE would add a walk the recording does not have).
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


# One recording streamed through the frozen tracker; writes runs/live/stream/<session>__<stem>/.
def stream(session: str, stem: str, speed: float = 1.0, window: bool = True, screen_dir: str = None, folder: str = None) -> dict:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    os.chdir(REPO_ROOT)
    import pipeline.io.windows as W
    from pipeline.io.capture_logger import run_capture
    from pipeline.io.ground_truth import KeyEvent, KeyReader
    from pipeline.live import frozen_model as FZ
    from pipeline.live.app_replay import Logger
    from pipeline.live.rig import TrackingConsumer
    folder = folder or FZ.TRACKER
    sdir, frames, sidecar = load_recording(session, stem)
    base_dir = W.baseline_dir_for(sdir, stem)
    t_rec_host = min(float(frames[n]["t_host"][0]) for n in NODES)
    print(f"STREAMED TRACKING: {session}/{stem}, {len(sidecar['passes'])} walks, speed {speed:g}, on the CPU", flush=True)
    chk = stream_preflight(base_dir, t_rec_host, folder)
    for k, v in chk.items():
        print(f"  {'ok  ' if v else 'FAIL'} {k}", flush=True)
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was streamed")
    built = FZ.load(folder)
    if CODES[session] in built["meta"]["train"]:
        print(f"NOTE: the frozen tracker was trained on {session}; A3 and B2 are the sessions it never saw", flush=True)
    print("Loading the tracking model and building the replay ports (about a minute)", flush=True)
    s = FZ.session(built, session="live", stem=stem, baseline=W.session_baseline(base_dir))
    log = Logger(s)
    t_rec0 = min(float(frames[n]["t_mono"][0]) for n in NODES)
    t_rec1 = max(float(frames[n]["t_mono"][-1]) for n in NODES)
    presses = sorted(float(p["t_start"]) for p in sidecar["passes"])
    ports = {n: ReplayPort(frames[n], t_rec0, 0.0, speed) for n in NODES}
    grab = [None]

    # The rig's consumer, every output logged as it exists.
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
        from pipeline.live.screen import Screen
        scr = Screen(s.st, headless=bool(screen_dir), title=f"streamed run: {session}/{stem} (q in the Terminal stops)")
        if screen_dir:
            grab[0] = Grabber(scr, J(screen_dir, f"stream_{session}_{stem}.mp4"))
    con = Consumer(s, scr)
    sys.modules["serial"] = serial_module({f"replay://{n}": ports[n] for n in NODES})
    t_wall0 = time.monotonic() + 2.0
    for p_ in ports.values():
        p_.t_wall0 = t_wall0
    delta = t_wall0 - t_rec0
    s.set_truth(shifted_truth(sidecar, delta))

    # Each walk's recorded start press as a SPACE, stamped when it is injected.
    def inject():
        for P in presses:
            due = t_wall0 + (P - t_rec0) / speed
            while time.monotonic() < due:
                time.sleep(min(0.002, max(0.0, due - time.monotonic())))
            con.keys.put(KeyEvent(key=" ", t_mono=time.monotonic(), t_host=time.time()))
    threading.Thread(target=inject, daemon=True).start()
    print("STREAMING: the walks start as recorded; q in this Terminal stops", flush=True)
    d = J(OUT, f"{session}__{stem}")
    cap_dir = J(d, "capture")
    os.makedirs(cap_dir, exist_ok=True)
    states, stop_keys = {}, threading.Event()
    t_start = time.time()
    with KeyReader(QuitOnly(con.keys), stop_keys):
        rc = run_capture({n: f"replay://{n}" for n in NODES}, duration=1.0 + (t_rec1 - t_rec0) / speed + 3.0,
                         extra_consumers=[con], stop_when=con.stop.is_set, quiet_monitor=True, states_out=states,
                         out_dir=cap_dir, timestamped_subdir=False, writer_prefix=f"{stem}_",
                         run_config={"stream": f"{session}/{stem}", "speed": speed, "tracker": os.path.relpath(folder, REPO_ROOT)})
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
    summ = {"session": session, "stem": stem, "speed": speed, "exit": rc, "delta_s": delta,
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
    with open(J(cap_dir, f"{stem}.gt.json"), "w", encoding="utf-8") as f:
        json.dump(sc, f)
    with open(J(d, "log.jsonl"), "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    with open(J(d, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=str)
    walks = [r for r in log.rows if r["kind"] == "committed"]
    print(f"DONE: {len(walks)} walks committed, {len(log.locks)} locks; {os.path.relpath(d, REPO_ROOT)}/", flush=True)
    for r in walks:
        t = (s.truth or {}).get(f"live|{stem}|{int(r['pid'])}") if hasattr(s, "truth") else None
        print(f"  walk {int(r['pid']):2d}: {r['line']}" + (f" (walked {t['path_name']})" if t and t.get("path_name") else ""),
              flush=True)
    return summ


# The screen, recorded as it is drawn, to H.264 with ffmpeg.
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


# Command line: python3 -m pipeline.live.stream_frozen --stream <session>/<stem> [--speed S] [--screen DIR] [--no-window].
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live.frozen_model stream")
    ap.add_argument("--stream", required=True, help="<session>/<stem>, e.g. B2/participant_PA5_walk")
    ap.add_argument("--speed", type=float, default=1.0, help="must be 1 (real time); kept for the app's --speed")
    ap.add_argument("--screen", default=None, help="record the screen to an .mp4 in this folder (no window; needs ffmpeg)")
    ap.add_argument("--no-window", action="store_true", help="no tracking window (the log and summary only)")
    a = ap.parse_args(argv)
    if "/" not in a.stream:
        raise SystemExit("REFUSED: --stream <session>/<stem>, e.g. B2/participant_PA5_walk")
    if a.speed != 1.0:
        raise SystemExit("REFUSED: --speed must be 1: the app fits each receiver's clock to the packets' arrival times and "
                         "refuses a clock rate far from real time, so a faster stream never starts")
    session, stem = a.stream.split("/", 1)
    stream(session, stem, a.speed, window=not a.no_window, screen_dir=os.path.abspath(a.screen) if a.screen else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
