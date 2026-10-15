"""The app's replay harness (Uzayr, 30 September 2026: one model, and it is the live app).

    python3 -m pipeline.live replay --recording B2/participant_X_walk --presses start [--model final] [--realtime]
    python3 -m pipeline.live replay --recording 03/participant_X_TEST_walk --presses start_end
    python3 -m pipeline.live replay --session B2 --presses start           # every evaluated recording
    python3 -m pipeline.live replay --session B2 --presses start --realtime --screen runs/live/renders
                                                                           # a render: the app's screen, recorded

A recorded session is fed to the app EXACTLY as the rig would feed it:
  - every packet, CSI and RSSI, in arrival order;
  - only the chosen presses:
      start      ONE press per walk, at its start: the semi-constrained mode, the headline
      start_end  the start and the end press: the fully constrained mode, an upper bound
      none       no press: the unconstrained mode (not built yet; refused)
  - never presses 2 to 6, the walk's duration, labels, pace or elapsed time.

Every app output is logged with the stream time at which it existed:
  - the lock (its line, the moment it was first set);
  - the committed line (its line, the window that decided it, when it was announced);
  - in full mode, the rescored committed line;
  - every drawn dot (its frame time, the xy, the walk, and the stream time it was computed);
  - the switches;
  - the per-window service times.

The ground truth is NOT given to the app. The scorer (`pipeline.live.app_score`) reads it beside the log.
The green overlay exists only in `--screen` replays, through `TrackingSession.set_truth`, which only the
screen reads. `tests/test_live_truth_isolation.py` proves that the app's outputs do not depend on it.

The clock: `--clock causal` (the default, as the rig must: each receiver's clock fitted on the packets
seen so far) or `--clock file` (the whole-file fit, the offline tree's; for the equality gates only).
With `--realtime` the events are paced by their stream times. The outputs are identical either way,
because nothing in the app reads a wall clock.

Writes runs/live/replay/<model>/<mode>_<clock>/<session>__<stem>.jsonl and .summary.json; <mode> carries
_disp-<K> for any display but K0 (the untagged folders are K0's, commit 63987d1). It never writes under data/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "replay")
MODE_OF = {"start": "semi", "start_end": "full", "none": "unconstrained"}
#: the model sets: the cell whose frozen files the app loads for each test session, and its display head
from pipeline.live.final_model import MODEL_CELLS  # noqa: E402  (since 8 Oct: the all-0.5 s cells)
MODEL_SETS = {"final": {**MODEL_CELLS["final"], "end_head": "final"},
              "zeroshot": {**MODEL_CELLS["zeroshot"], "end_head": "zeroshot"}}
#: development sets: a rotation cell through the app, for behaviour checks only (no manifest; never a figure).
#: rotB1's display head is the final one, trained on B1, so its dots are not a held-out measurement
DEV_SETS = {"rotB1": {"B1": "d4c_fuse_0102_to_B1", "end_head": "final"},
            "rotA2": {"02": "d4c_fuse_01B1_to_02", "end_head": "final"},
            "rotA1": {"01": "d4c_fuse_02B1_to_01", "end_head": "final"}}
MODEL_SETS.update(DEV_SETS)
VARIANT = "relgateU+abstain+a2w0.25"


SESSION_LABEL = {"01": "A1", "02": "A2", "03": "A3"}
ANON = J(REPO_ROOT, "runs", "dc2_results", "teaching", "anon_map.json")


def code_of(stem: str) -> str:
    """The participant's code (P1 to P6, the reports' map), so a video's name carries no name."""
    with open(ANON, encoding="utf-8") as f:
        m = json.load(f)["map"]
    who = stem.replace("participant_", "").split("_")[0]
    return m[who]


def cell_for(model: str, session: str) -> str:
    ms = MODEL_SETS[model]
    if session not in ms:
        raise SystemExit(f"REFUSED: model {model!r} has no test cell for session {session}")
    return ms[session]


class Logger:
    """Wraps the session so that every output is logged the moment it exists (stream time)."""

    def __init__(self, s):
        self.s, self.rows, self.now = s, [], None
        self.locks = {}
        self.n_frames = 0
        disp = s.display
        orig_draw = disp._draw_until

        def draw_until(x_stop):
            before = {pid: set(v) for pid, v in disp.out.items()}
            orig_draw(x_stop)
            for pid, v in disp.out.items():
                for x in sorted(set(v) - before.get(pid, set())):
                    xy = v[x]
                    self.rows.append({"kind": "dot", "pid": int(pid), "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                                      "computed_at": self.now})
                    self.n_frames += 1
            for pid, ln in s.first_lock.items():                  # rule 1: the line first drawn is THE lock
                m = disp.meta[pid]
                if pid not in self.locks:
                    self.locks[pid] = ln
                    self.rows.append({"kind": "lock", "pid": int(pid), "line": ln, "at": self.now,
                                      "line_entry": [float(v) for v in m["line_entry"]] if m.get("line_entry") else None,
                                      "t_dec0": m.get("t_dec0"), "park_until": m.get("park_until")})
        disp._draw_until = draw_until
        if hasattr(s, "_park_drawn_ahead"):
            # a start press inside frames already drawn ahead: the app writes the new walk's park frames directly
            # (FinalTrackingSession._park_drawn_ahead), outside _draw_until. They are logged here too (found 30 Sep
            # 23:30: without this, whether a walk's first park frames were logged depended on when its press was
            # handled, the only difference between the streamed run and the re-replay of its own capture)
            orig_park = s._park_drawn_ahead

            def park(pid, t_press):
                before = set(disp.out.get(int(pid), {}))
                orig_park(pid, t_press)
                for x in sorted(set(disp.out.get(int(pid), {})) - before):
                    xy = disp.out[int(pid)][x]
                    self.rows.append({"kind": "dot", "pid": int(pid), "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                                      "computed_at": self.now})
                    self.n_frames += 1
            s._park_drawn_ahead = park
        orig_dec = s._decided

        def decided(row, at_close=False):
            orig_dec(row, at_close)
            d = s.decisions[-1]
            self.rows.append({"kind": "committed", "pid": d["pass_id"], "line": d["final_line"], "at": self.now,
                              "exit_window_centre": float(s.decoder.t0[d["exit_window"]]) + 1.0,
                              "decided_window_end": float(s.decoder.t0[d["decided_at_window"]]) + 2.0,
                              "at_close": bool(at_close)})
        s._decided = decided

    def event(self, t):
        self.now = float(t)

    def finish(self):
        s = self.s
        for d in getattr(s, "decisions_full", []):
            self.rows.append({"kind": "committed_full", "pid": d["pass_id"], "line": d["final_line"], "t_end": d["t_end"],
                              "hi_end": d["hi_end"]})
        for ch in s.lock_changes:
            self.rows.append({"kind": "lock_change", **ch})
        for dd in getattr(s, "detections", []):
            self.rows.append({"kind": "detected_start", "pid": int(dd["pid"]), "t": float(dd["t_start"]),
                              "at": dd.get("at"), "m": dd["m"]})
        for pid, m in s.display.meta.items():
            if m.get("min_margin_s") is not None:
                self.rows.append({"kind": "margin", "pid": int(pid), "min_margin_s": float(m["min_margin_s"])})
            for sw in m.get("switches", []):
                self.rows.append({"kind": "switch", "pid": int(pid), "x": float(sw["x"]), "old": sw["old"], "new": sw["new"]})


class ScreenRecorder:
    """The app's own screen (`pipeline.live.screen.Screen`, the window the rig opens), drawn from
    `screen_state` every 1 / FPS of stream time and written frame by frame to an H.264 video. Headless (Agg)
    renders the same figure the window shows, so the video is the window's content, frame for frame. The
    ground truth reaches only the screen (`set_truth`): the green marker and the RIGHT/WRONG banner."""

    #: V4, no dwell footage: a gap between one walk's end and the next walk's start longer than this is cut
    #: (Room A's recordings hold the 25-cell standing block, 450 to 530 s, between their two walk halves; B2's
    #: longest gap between walks is 22 s). The harness knows the walks' times from the sidecar; the app does not
    CUT_GAP_S, MARGIN_S = 60.0, 3.0

    def __init__(self, s, st, path: str, t_start: float, passes: list = None):
        from pipeline.live.display import FPS
        from pipeline.live.screen import Screen
        self.s, self.path, self.dt = s, path, 1.0 / FPS
        self.scr = Screen(st, headless=True)
        self.scr.fig.canvas.draw()
        self.w, self.h = self.scr.fig.canvas.get_width_height()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                                    "-s", f"{self.w}x{self.h}", "-r", str(FPS), "-i", "-", "-threads", "1", "-c:v", "libx264",
                                    "-pix_fmt", "yuv420p", "-crf", "20", path], stdin=subprocess.PIPE)
        self.tick, self.n = float(t_start), 0
        from pipeline.live.display import LATENCY_S
        ps = sorted(passes or [], key=lambda p: float(p["t_start"]))
        self.cuts = [(float(a["t_end"]) + LATENCY_S + self.MARGIN_S, float(b["t_start"]) - self.MARGIN_S)
                     for a, b in zip(ps, ps[1:]) if float(b["t_start"]) - float(a["t_end"]) > self.CUT_GAP_S]
        self.cut_s = 0.0

    def in_cut(self, t: float) -> bool:
        return any(a <= t < b for a, b in self.cuts)

    def until(self, now: float) -> None:
        """Every video frame strictly before `now`: all events up to it have been given to the app. A frame inside
        a cut (V4) is not recorded."""
        while self.tick < now:
            if self.in_cut(self.tick):
                self.tick += self.dt
                self.cut_s += self.dt
                continue
            self.scr.tracking(**self.s.screen_state(self.tick))
            self.scr.fig.canvas.draw()
            self.ff.stdin.write(bytes(self.scr.fig.canvas.buffer_rgba()))
            self.tick += self.dt
            self.n += 1

    def close(self) -> dict:
        self.ff.stdin.close()
        rc = self.ff.wait()
        return {"video": os.path.relpath(self.path, REPO_ROOT), "frames": self.n, "fps": round(1.0 / self.dt, 3),
                "size": [self.w, self.h], "ffmpeg_exit": rc, "cuts_v4": [[round(a, 3), round(b, 3)] for a, b in self.cuts],
                "cut_s": round(self.cut_s, 1)}


def mode_dir_for(presses: str, m: int, disp: str, profile: str, profile_given: bool) -> str:
    """The replay folder's mode part. Every folder before 10 Oct holds the pre_clean display; the K1gf folders hold
    the clean one. A replay drawn with another profile than its folder's, or with a profile given explicitly (gate 3's
    pre_clean reproduction), is tagged _prof-<profile>, so no shipped replay is ever overwritten."""
    from pipeline.live.final_model import DISPLAY_PROFILES
    d = MODE_OF[presses] + (f"_m{m}" if presses == "none" else "") + (f"_disp-{disp}" if disp else "")
    canon = "clean" if disp == DISPLAY_PROFILES["clean"]["candidate"] else "pre_clean"
    return d + (f"_prof-{profile}" if (profile_given or profile != canon) else "")


def replay_inner(model: str, session: str, stem: str, presses: str, clock: str, realtime: bool,
                 components=None, screen: str = None, hold: list = None, m: int = None,
                 identity: list = None, display: str = None, sdir: str = None, profile: str = None) -> dict:
    """One recording through the app. Returns the summary; writes the log (and with `screen`, the video).
    `profile`: a display profile (final_model.DISPLAY_PROFILES); default the app's."""
    from pipeline.live.final_model import FinalTrackingSession, _components, end_head_for
    from pipeline.live.replay import recording_events
    import pipeline.io.windows as W
    cell = cell_for(model, session)
    PC, c, pieces, pool, terms, G0 = components or _components(cell, VARIANT)
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    assert c["test"] == session, (c["test"], session)
    sdir = sdir or PC.raw_dir(session)                  # sdir: another folder of the same layout (a streamed run's capture)
    end_head = end_head_for(st, alpha, MODEL_SETS[model]["end_head"], profile)      # none under the clean profile
    kw = dict(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"], test=(session,),
              reader_tag=c["reader_tag"], pieces=pieces, baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)),
              end_head=end_head, display_candidate=display, display_profile=profile)
    if presses == "none":
        # UNCONSTRAINED: no press is given; the statistics are fixed at S and the starts detected (APP_PREREG 6)
        from pipeline.live.unconstrained import load_m, make_session
        m = int(m or load_m())
        s = make_session(m, **kw)
    else:
        s = FinalTrackingSession(mode=MODE_OF[presses], **kw)
    log = Logger(s)
    ev, _info = recording_events(sdir, stem, end_presses=(presses == "start_end"), causal_anchor=(clock == "causal"))
    rec = None
    if screen:
        with open(J(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
            sidecar = json.load(f)
        s.set_truth(sidecar)                          # the replay-only overlay: the green marker and the verdict
        t_press1 = min(e_[0] for e_ in ev if e_[2] == "press")
        rec = ScreenRecorder(s, st, screen, t_press1 - 3.0, sidecar.get("passes"))
    t_first, wall0 = ev[0][0], time.time()
    t1 = time.time()
    skipped, prev = 0.0, ev[0][0]
    # identification's decision lines (schema id_engine_decision_v1), handed to the app when each was made, as the
    # live app follows identification's file; only the screen reads them (tests/test_live_truth_isolation.py)
    id_q = sorted(identity or [], key=lambda ln: float(ln["t_decision_mono"]))
    for e_ in ev:
        now = e_[0]
        while id_q and float(id_q[0]["t_decision_mono"]) <= now:
            s.identity(id_q.pop(0))
        if realtime:
            if rec is not None and rec.in_cut(prev):
                skipped += now - prev                 # nothing is filmed inside a V4 cut: not paced
            lag = (now - t_first - skipped) - (time.time() - wall0)
            if lag > 0:
                time.sleep(lag)
        prev = now
        if rec is not None:
            rec.until(now)
        log.event(now)
        if e_[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
            if ts is None:
                s.rssi(n, t_host, rssi)
            else:
                s.packet(n, ts, amp, t_host, t_mono, rssi)
        elif e_[2] == "press":
            if presses == "none":
                continue                              # never given: the app finds its own starts
            s.press(e_[4], e_[3])
            log.rows.append({"kind": "press", "pid": int(e_[4]), "t": float(e_[3])})
        else:
            s.end_press(e_[4], e_[3])
            log.rows.append({"kind": "end_press", "pid": int(e_[4]), "t": float(e_[3])})
    log.event(ev[-1][0])
    s.close()
    log.finish()
    video = None
    if rec is not None:
        from pipeline.live.display import LATENCY_S
        rec.until(ev[-1][0] + LATENCY_S + 1.0)       # the last walk's frames and its banner, shown 2.0 s behind
        video = rec.close()
    ws = [x for x, prov in s.timing["window_s"] if not prov]
    q = lambda v, p: float(np.percentile(v, p)) if v else None                     # noqa: E731
    summ = {"model": model, "cell": cell, "session": session, "stem": stem, "presses": presses, "mode": MODE_OF[presses],
            "clock": clock, "realtime": realtime, "variant": VARIANT,
            "end_head": end_head.file if end_head is not None else "pooled (no display head)",
            "display_profile": s.display_profile,
            "stats": s.stats, "n_passes_pressed": len(s.passes), "n_committed": len(s.decisions),
            "n_committed_full": len(getattr(s, "decisions_full", [])), "n_locks": len(log.locks), "n_frames": log.n_frames,
            "n_lock_changes_after_first": len(s.lock_changes),
            "timing": {"window_s": {"median": q(ws, 50), "p95": q(ws, 95), "p99": q(ws, 99), "max": max(ws) if ws else None,
                                    "n": len(ws)},
                       "press_s": {"median": q(s.timing["press_s"], 50), "max": max(s.timing["press_s"]) if s.timing["press_s"] else None}},
            "minutes": round((time.time() - t1) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"), "video": video,
            "duration_s": float(ev[-1][0] - ev[0][0]), "m": (m if presses == "none" else None),
            "display_candidate": s.display_candidate,
            "n_detected_starts": len(getattr(s, "detections", []))}
    # the folders without a _disp tag hold K0 (commit 63987d1); a replay drawn with any other display is tagged
    # with it even when it is the app's default, so it never overwrites them
    disp = display or (s.display_candidate if s.display_candidate != "K0" else None)
    mode_dir = mode_dir_for(presses, m, disp, s.display_profile, profile is not None)
    d = J(OUT, model, f"{mode_dir}_{clock}" + ("_realtime" if realtime else "") + ("_screen" if screen else ""))
    os.makedirs(d, exist_ok=True)
    base = J(d, f"{session}__{stem}")
    with open(base + ".jsonl", "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    with open(base + ".summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=str)
    summ["log"] = base + ".jsonl"                    # the returned summary only (not the file): where the log went
    if hold is not None:
        hold.append(s)                                # the session itself, for a caller that reads its internals
    print(f"[{time.strftime('%H:%M:%S')}] replay {model} {session}/{stem} {presses} {clock}: {len(s.decisions)} committed, "
          f"{len(log.locks)} locks, {log.n_frames} frames, window median {summ['timing']['window_s']['median']}", flush=True)
    return summ


def session_inner(model: str, session: str, presses: str, clock: str, realtime: bool, stems=None,
                  screen_dir: str = None, m: int = None, display: str = None, profile: str = None) -> int:
    if model in DEV_SETS:
        assert session not in ("03", "B2"), "a development set never replays a test session"
        print(f"development set {model}: behaviour checks only, no figure", flush=True)
    else:
        from pipeline.live.model_sets import check
        chk = check(model)
        if not chk["ok"]:
            raise SystemExit(f"REFUSED: the {model} model set differs from its manifest: {chk['mismatched'][:5]}")
        print(f"model set {model}: {chk['n']} files match runs/live/models/{model}.json", flush=True)
    from pipeline.live.final_model import _components
    cell = cell_for(model, session)
    comp = _components(cell, VARIANT)
    PC, c = comp[0], comp[1]
    cal = PC.cal_stems(session)
    from pipeline.constrained.recordings import session_recordings
    todo = [st_ for _s, st_ in session_recordings(session) if st_ not in cal and (not stems or st_ in stems)]
    for stem in todo:
        vid = J(screen_dir, f"{model}_{MODE_OF[presses]}_{SESSION_LABEL.get(session, session)}_{code_of(stem)}.mp4") \
            if screen_dir else None
        replay_inner(model, session, stem, presses, clock, realtime, components=comp, screen=vid, m=m, display=display,
                     profile=profile)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live replay")
    ap.add_argument("--recording", help="<session>/<stem>, e.g. B2/participant_X_walk")
    ap.add_argument("--session", help="every evaluated recording of a test session (03 or B2)")
    ap.add_argument("--presses", required=True, choices=["start", "start_end", "none"])
    ap.add_argument("--model", default="final", choices=sorted(MODEL_SETS))
    ap.add_argument("--clock", default="causal", choices=["causal", "file"])
    ap.add_argument("--realtime", action="store_true")
    ap.add_argument("--screen", default=None, help="a folder: the app's screen is recorded to <folder>/<...>.mp4")
    ap.add_argument("--m", type=int, default=None, help="unconstrained only: the detector's m (default: M.json's choice)")
    ap.add_argument("--display", default=None, help="a display candidate (display.DISPLAY_CANDIDATES); default: the app's")
    ap.add_argument("--profile", default=None, help="a display profile (final_model.DISPLAY_PROFILES); default: the app's")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    session = a.session or (a.recording.split("/")[0] if a.recording else None)
    if not session:
        raise SystemExit("give --recording or --session")
    if a.inner:
        from pipeline.constrained.pd_clean import force_cpu
        force_cpu()
        stems = [a.recording.split("/", 1)[1]] if a.recording else None
        return session_inner(a.model, session, a.presses, a.clock, a.realtime, stems,
                             os.path.abspath(a.screen) if a.screen else None, a.m, a.display, a.profile)
    from pipeline.live.final_model import _env
    args = [sys.executable, "-m", "pipeline.live.app_replay", "--inner", "--presses", a.presses, "--model", a.model,
            "--clock", a.clock] + (["--recording", a.recording] if a.recording else ["--session", session]) \
        + (["--realtime"] if a.realtime else []) + (["--screen", os.path.abspath(a.screen)] if a.screen else []) \
        + (["--m", str(a.m)] if a.m else []) + (["--display", a.display] if a.display else []) \
        + (["--profile", a.profile] if a.profile else [])
    return subprocess.call(args, cwd=REPO_ROOT, env=_env(cell_for(a.model, session)))


if __name__ == "__main__":
    sys.exit(main())
