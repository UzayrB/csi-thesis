"""The streamed rig run (Uzayr, 30 September 2026, item 5): a recorded session fed to the live app, in wall-clock
time, through the SAME ingestion path the boards use.

    python3 -m pipeline.live rig --stream B2/participant_PA5_walk [--screen runs/live/stream] [--speed 1.0]

WHAT IS REPLACED: ONLY THE PACKET SOURCE. A stand-in `serial` module is registered before `run_capture` opens its
ports. Its `Serial(port)` replays one receiver of the recording: each recorded frame is written back as the
project firmware's base64 `CSI_DATA` row (`frame_to_line`, the exact inverse of `pipeline.io.parse.parse_line`)
and released at its recorded pace in wall-clock time, in chunks as a serial read returns them.

EVERYTHING DOWNSTREAM IS A PLUGGED-IN RUN'S:
- `pipeline.io.capture_logger.run_capture`, unchanged: one `SerialReader` thread per receiver, each chunk stamped
  on `time.monotonic()` / `time.time()` as it is read, split into lines, parsed by `parse_line`, queued;
- the rate monitor, the config watch and the dispatch loop;
- the rig's `TrackingConsumer`: the causal clock anchor per receiver, the final model in its semi-constrained
  mode (every SPACE a start press), the display and the screen.
Nothing under `pipeline/io/` is edited.

THE KEYS: each walk's FIRST press is put in the consumer's key queue as a SPACE `KeyEvent` at its recorded time,
stamped on `time.monotonic()` when it is injected, as the terminal key reader stamps a real key.

DIFFERENCES FROM A PLUGGED-IN RUN, other than the packet source:
1. the key source: an injector thread in place of the terminal `KeyReader`;
2. no board reset or boot banner (the rig runs with reset off as well);
3. the replay port emulates the serial read timeout: it waits up to the timeout when no line is due;
4. the screen's green marker and verdict: the recording's own truth, shifted onto the stream's clock (a
   replay-only overlay, read only by the screen; a live run has none);
5. the pre-flight's baseline-age check is made against the recording's start, not against today.

It writes runs/live/stream/<session>__<stem>/: the app's log (every output with its wall-clock time, as the
replay harness logs it), a summary with the wall-clock measurements, and with --screen the recorded screen.
"""

from __future__ import annotations

import argparse
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
TX_MAC = "1a:00:00:00:00:00"          # the transmitter's ESP-NOW address; parse keeps it, nothing reads it
_INT = ("pkt_id", None, "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
        "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
        "ant", "sig_len", "rx_format", None, "first_word")


def out_root() -> str:
    """Where a streamed run writes. runs/live/stream holds the K0 run of 30 Sep; a run drawn with any other display
    (the app's DISPLAY_CANDIDATE) goes to runs/live/stream_disp-<K>, so it never overwrites that record."""
    from pipeline.live.final_model import DISPLAY_CANDIDATE
    return OUT if DISPLAY_CANDIDATE == "K0" else f"{OUT}_disp-{DISPLAY_CANDIDATE}"


def frame_to_line(fr, mac: str = TX_MAC) -> str:
    """One recorded frame as the project firmware's base64 CSI_DATA row: fields 1 to 23 as `parse._INT_FIELDS`
    reads them (2 is the MAC, 22 the declared length 256), then gain x 10000 and the raw payload in base64."""
    parts = ["CSI_DATA"]
    for name in _INT:
        if name is None:
            parts.append(mac if len(parts) == 2 else "256")
        else:
            parts.append(str(int(fr[name])))
    parts.append(str(int(round(float(fr["gain"]) * 10000.0))))
    parts.append(base64.b64encode(np.asarray(fr["data"], np.int8).tobytes()).decode("ascii"))
    return ",".join(parts)


class ReplayPort:
    """A serial port that replays one receiver: a line is readable once the wall clock has passed its recorded
    time (relative to the recording's start, over `speed`). `read(n)` returns every due line up to n bytes, as a
    serial read returns what the UART buffered; with nothing due it waits up to `timeout`, then returns b""."""

    def __init__(self, frames, t_rec0: float, t_wall0: float, speed: float = 1.0, timeout: float = 0.05):
        self.lines = [(float(f["t_mono"]) - t_rec0, (frame_to_line(f) + "\n").encode("ascii")) for f in frames]
        self.i, self.t_wall0, self.speed, self.timeout = 0, float(t_wall0), float(speed), float(timeout)
        self.closed = False

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

    def close(self) -> None:
        self.closed = True


def serial_module(ports: dict):
    """A stand-in `serial` module: `Serial(port, baud, timeout=...)` returns the ReplayPort registered for that
    port name. Registered in sys.modules so that `SerialReader.open`'s own `import serial` finds it."""
    mod = types.ModuleType("serial")

    class SerialException(Exception):
        pass

    def Serial(port, baud=None, timeout=None, **_k):          # noqa: N802 (pyserial's name)
        if port not in ports:
            raise SerialException(f"no replay registered for {port}")
        p = ports[port]
        if timeout is not None:
            p.timeout = float(timeout)
        return p
    mod.Serial, mod.SerialException = Serial, SerialException
    return mod


def load_recording(session: str, stem: str):
    from pipeline.constrained import pd_cells as PC
    from pipeline.io.capture_logger import read_capture_file
    sdir = PC.raw_dir(session)
    frames = {n: read_capture_file(J(sdir, f"{stem}_{n}.bin"))[1] for n in NODES}
    with open(J(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    return sdir, frames, sidecar


def shifted_truth(sidecar: dict, delta: float) -> dict:
    """The sidecar with every time moved onto the stream's clock (for the screen's replay-only overlay)."""
    out = json.loads(json.dumps(sidecar))
    for p in out.get("passes", []):
        for k in ("t_start", "t_end"):
            if p.get(k) is not None:
                p[k] = float(p[k]) + delta
        p["anchor_times"] = [float(t) + delta for t in p.get("anchor_times", [])]
    return out


def stream_inner(session: str, stem: str, screen_dir: str = None, speed: float = 1.0) -> dict:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.io.windows as W
    from pipeline.io.capture_logger import run_capture
    from pipeline.io.ground_truth import KeyEvent
    from pipeline.live.app_replay import VARIANT, Logger, cell_for
    from pipeline.live.final_model import end_head_for, FinalTrackingSession, _components, preflight
    from pipeline.live.model_sets import check
    from pipeline.live.rig import TrackingConsumer
    sdir, frames, sidecar = load_recording(session, stem)
    base_dir = W.baseline_dir_for(sdir, stem)
    # 5c: the pre-flight, in stream mode, before anything. Its one difference from the boards: the baseline must be
    # recent against the RECORDING's start (its first packet's host time), not against today
    t_rec_host = min(float(frames[n]["t_host"][0]) for n in NODES)
    chk = preflight(base_dir, at=t_rec_host)
    for k, v in chk.items():
        print(f"  {'ok  ' if v else 'FAIL'} {k}", flush=True)
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was streamed")
    ms = check("final")
    if not ms["ok"]:
        raise SystemExit(f"REFUSED: the final model set differs from its manifest: {ms['mismatched'][:5]}")
    cell = cell_for("final", session)
    PC_, c, pieces, pool, terms, G0 = _components(cell, VARIANT)
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"],
                             test=(session,), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=W.session_baseline(base_dir), end_head=end_head_for(st, alpha, "final"),
                             mode="semi")
    log = Logger(s)
    t_rec0 = min(float(frames[n]["t_mono"][0]) for n in NODES)
    t_rec1 = max(float(frames[n]["t_mono"][-1]) for n in NODES)
    presses = sorted(float(p["t_start"]) for p in sidecar["passes"])
    rec = None
    # the replay ports are built FIRST (writing every frame back as a CSI_DATA row takes a while); the stream's
    # clock starts only once everything is ready, just before the readers open
    ports = {n: ReplayPort(frames[n], t_rec0, 0.0, speed) for n in NODES}

    class Consumer(TrackingConsumer):
        def handle(self, r):
            log.event(time.monotonic())
            super().handle(r)

        def tick(self, now):
            log.event(time.monotonic())
            super().tick(now)
            if rec is not None and self.last_draw == now:
                rec.grab()

    scr = None
    if screen_dir:
        from pipeline.live.screen import Screen
        scr = Screen(st, headless=True)
        rec = _Grabber(scr, J(screen_dir, f"stream_{session}_{stem}.mp4"))
    con = Consumer(s, scr)
    sys.modules["serial"] = serial_module({f"replay://{n}": ports[n] for n in NODES})
    t_wall0 = time.monotonic() + 2.0                          # the stream starts two seconds from now
    for p_ in ports.values():
        p_.t_wall0 = t_wall0
    delta = t_wall0 - t_rec0                                  # recorded clock -> the stream's clock
    s.set_truth(shifted_truth(sidecar, delta))                # the screen's replay-only overlay

    def inject():
        for i, P in enumerate(presses):
            due = t_wall0 + (P - t_rec0) / speed
            while time.monotonic() < due:
                time.sleep(min(0.002, max(0.0, due - time.monotonic())))
            con.keys.put(KeyEvent(key=" ", t_mono=time.monotonic(), t_host=time.time()))
    threading.Thread(target=inject, daemon=True).start()
    states = {}
    t_start = time.time()
    cap_dir = J(out_root(), f"{session}__{stem}", "capture")       # what the app received, written as a plugged-in run writes it
    os.makedirs(cap_dir, exist_ok=True)
    rc = run_capture({n: f"replay://{n}" for n in NODES}, duration=1.0 + (t_rec1 - t_rec0) / speed + 3.0,
                     extra_consumers=[con], stop_when=con.stop.is_set, quiet_monitor=True, states_out=states,
                     out_dir=cap_dir, timestamped_subdir=False, writer_prefix=f"{stem}_",
                     run_config={"stream": f"{session}/{stem}", "speed": speed})
    log.event(time.monotonic())
    s.close()
    log.finish()
    video = rec.close() if rec is not None else None
    # --- the wall-clock measurements
    lock_late = [float(r["at"]) - (float(s.passes[r["pid"]]["press"]) + 2.0) for r in log.rows if r["kind"] == "lock"]
    ends = {i + 1: float(p["t_end"]) + delta for i, p in enumerate(sorted(sidecar["passes"], key=lambda q: q["t_start"]))}
    ann_late = [float(r["at"]) - ends[r["pid"]] for r in log.rows if r["kind"] == "committed" and r["pid"] in ends]
    dots = [r for r in log.rows if r["kind"] == "dot"]
    lag = [max(0.0, float(r["computed_at"]) - float(r["x"])) for r in dots if r["computed_at"] is not None]
    ws = [x for x, prov in s.timing["window_s"] if not prov]
    q = lambda v, p: float(np.percentile(v, p)) if v else None                     # noqa: E731
    summ = {"session": session, "stem": stem, "speed": speed, "exit": rc, "delta_s": delta,
            "wall_minutes": round((time.time() - t_start) / 60.0, 2),
            "n_presses_injected": len(presses), "n_committed": len(s.decisions), "n_locks": len(log.locks),
            "n_frames": len(dots),
            "window_service_s": {"median": q(ws, 50), "p95": q(ws, 95), "p99": q(ws, 99), "max": max(ws) if ws else None,
                                 "n": len(ws)},
            "press_service_s": {"median": q(s.timing["press_s"], 50), "max": max(s.timing["press_s"]) if s.timing["press_s"] else None},
            "lock_late_s": {"median": q(lock_late, 50), "p90": q(lock_late, 90), "max": max(lock_late) if lock_late else None},
            "announce_after_walk_end_s": {"median": q(ann_late, 50), "p90": q(ann_late, 90), "max": max(ann_late) if ann_late else None},
            "frames_late": {"over_0.1s": int(sum(1 for x in lag if x > 0.1)), "over_0.5s": int(sum(1 for x in lag if x > 0.5)),
                            "max_s": max(lag) if lag else None},
            "receivers": {n: {"queue_dropped": int(getattr(st_, "queue_dropped", 0)),
                              "parsed_ok": int(getattr(getattr(st_, "counters", None), "ok", 0)),
                              "read_errors": int(getattr(st_, "read_errors", 0))} for n, st_ in states.items()},
            "video": video, "presses": {int(pid): float(p["press"]) for pid, p in s.passes.items()}}
    d = J(out_root(), f"{session}__{stem}")
    os.makedirs(d, exist_ok=True)
    # the capture's sidecar: the presses AS THE APP GOT THEM (the injected keys' own times), the truth on the
    # stream's clock, the recording's own baseline; so the capture replays through the harness exactly as streamed
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
    print(json.dumps({k: summ[k] for k in ("n_committed", "n_locks", "window_service_s", "lock_late_s",
                                           "announce_after_walk_end_s", "frames_late")}, default=str), flush=True)
    return summ


def rereplay_inner(session: str, stem: str) -> dict:
    """The streamed run's own capture (the packets and presses exactly as the app received them) replayed through
    the harness: if the app is the same on both paths, every output equals the stream's (only the moments things
    were computed differ, wall clock against stream time)."""
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.live.app_replay as AR
    cap = J(out_root(), f"{session}__{stem}", "capture")
    AR.OUT = J(out_root(), f"{session}__{stem}", "rereplay")
    rr = AR.replay_inner("final", session, stem, "start", "causal", False, sdir=cap)
    strip = lambda r: {k: v for k, v in r.items() if k not in ("computed_at", "at")}             # noqa: E731
    a = [strip(json.loads(ln)) for ln in open(J(out_root(), f"{session}__{stem}", "log.jsonl"), encoding="utf-8")
         if '"kind": "press"' not in ln]
    b = [strip(json.loads(ln)) for ln in open(rr["log"], encoding="utf-8")
         if '"kind": "press"' not in ln]
    key = lambda r: json.dumps(r, sort_keys=True)                                                 # noqa: E731
    out = {"rows_stream": len(a), "rows_rereplay": len(b), "IDENTICAL": sorted(map(key, a)) == sorted(map(key, b))}
    with open(J(out_root(), f"{session}__{stem}", "rereplay.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out), flush=True)
    return out


def compare(session: str, stem: str, replay_dir: str) -> dict:
    """The streamed run against the replay of the same recording (item 5d): every walk's committed line and lock,
    and every dot at the same time from its walk's press (the stream re-stamps the packets on the wall clock, so
    its times differ by a constant plus the reader's jitter)."""
    import numpy as np
    a = [json.loads(ln) for ln in open(J(out_root(), f"{session}__{stem}", "log.jsonl"), encoding="utf-8")]
    b = [json.loads(ln) for ln in open(J(replay_dir, f"{session}__{stem}.jsonl"), encoding="utf-8")]
    sa = json.load(open(J(out_root(), f"{session}__{stem}", "summary.json"), encoding="utf-8"))
    pa = {int(k): float(v) for k, v in sa["presses"].items()}
    pb = {r["pid"]: float(r["t"]) for r in b if r["kind"] == "press"}
    lines = lambda rows, k: {r["pid"]: r["line"] for r in rows if r["kind"] == k}      # noqa: E731
    out = {"walks": len(pb), "committed_equal": sum(lines(a, "committed").get(p) == v for p, v in lines(b, "committed").items()),
           "lock_equal": sum(lines(a, "lock").get(p) == v for p, v in lines(b, "lock").items())}
    dev = []
    for pid in pb:
        if pid not in pa:
            continue
        da = sorted((r["x"] - pa[pid], r["xy"]) for r in a if r["kind"] == "dot" and r["pid"] == pid)
        db = sorted((r["x"] - pb[pid], r["xy"]) for r in b if r["kind"] == "dot" and r["pid"] == pid)
        if not da or not db:
            continue
        ta = np.array([t for t, _ in da])
        for t, xy in db:
            j = int(np.argmin(np.abs(ta - t)))
            if abs(ta[j] - t) <= 0.05:
                dev.append(float(np.hypot(*(np.asarray(da[j][1]) - np.asarray(xy)))))
    out["dots_compared"] = len(dev)
    out["dot_deviation_m"] = {"median": float(np.median(dev)) if dev else None, "p99": float(np.percentile(dev, 99)) if dev else None,
                              "max": max(dev) if dev else None}
    return out


class _Grabber:
    """The screen, recorded as it is drawn (each tick of the rig's screen), to H.264."""

    def __init__(self, scr, path: str):
        import subprocess
        self.scr, self.path, self.n = scr, path, 0
        scr.fig.canvas.draw()
        self.w, self.h = scr.fig.canvas.get_width_height()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                                    "-s", f"{self.w}x{self.h}", "-r", "10", "-i", "-", "-threads", "1", "-c:v", "libx264",
                                    "-pix_fmt", "yuv420p", "-crf", "20", path], stdin=subprocess.PIPE)

    def grab(self):
        self.scr.fig.canvas.draw()
        self.ff.stdin.write(bytes(self.scr.fig.canvas.buffer_rgba()))
        self.n += 1

    def close(self):
        self.ff.stdin.close()
        return {"video": os.path.relpath(self.path, REPO_ROOT), "frames": self.n, "exit": self.ff.wait()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live rig --stream")
    ap.add_argument("--stream", required=True, help="<session>/<stem>, e.g. B2/participant_PA5_walk")
    ap.add_argument("--screen", default=None, help="a folder: the screen is recorded there")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--rereplay", action="store_true")
    a, _rest = ap.parse_known_args(argv)
    session, stem = a.stream.split("/", 1)
    if a.inner and a.rereplay:
        rereplay_inner(session, stem)
        return 0
    if a.inner:
        stream_inner(session, stem, os.path.abspath(a.screen) if a.screen else None, a.speed)
        return 0
    import subprocess
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    args = [sys.executable, "-m", "pipeline.live.stream_source", "--inner", "--stream", a.stream, "--speed", str(a.speed)] \
        + (["--screen", os.path.abspath(a.screen)] if a.screen else []) + (["--rereplay"] if a.rereplay else [])
    return subprocess.call(args, cwd=REPO_ROOT, env=dict(_env(cell_for("final", session)), OMP_NUM_THREADS="1"))


if __name__ == "__main__":
    sys.exit(main())
