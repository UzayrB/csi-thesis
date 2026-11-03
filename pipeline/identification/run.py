# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Identification, run: on the boards (on_the_boards: the model, the extraction workers, the boards by MAC...

from __future__ import annotations

import json
import os
import time

import numpy as np

from pipeline.identification.extraction import EXTRACT_HELP, EXTRACT_WORKERS, DataEnded, ExtractPool, SilentReceiver
from pipeline.identification.window import DIR_WORD, EngineScreen, IdentifyWindow, _norm

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO_ROOT, "runs", "live", "identify")
ROUND_TRIP_S = 15.0
CHUNK_S = 0.25



# ON THE BOARDS: the deployment model, from its manifest; each walk's path is picked on the window's map...
def on_the_boards(minutes: float = None, device: str = None, focus_back: bool = True,
                  extract_workers: int = None) -> int:
    from pipeline.identification import engine as EN
    from pipeline.io.boards import RigSteps, receiver_ports, rig_banner, run
    md, man = load_deployment()
    layout = "home"
    os.chdir(REPO_ROOT)
    steps = RigSteps(4)
    print("IDENTIFICATION, the live app on the boards: starting", flush=True)
    dev = rig_device(md, device)
    dmode = direction_mode_for(layout)
    rx2 = tuple(EN._rigs()[layout]["RX2"])
    steps.step(f"Loading the identification model {man['model']} on the {'GPU' if dev == 'mps' else 'CPU'}; RX2 at {rx2} "
               "(the tracking rig); direction: each walk's path picked on the map, then SPACE")
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"], layout=layout, device=dev)
    stem = time.strftime("rig_%Y%m%d_%H%M%S")
    steps.step("Starting and warming the extraction workers")
    app = EngineApp(eng, f"{man['model']} (all five sessions)", replay=False, jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"),
                    dmode=dmode, extract_workers=extract_workers)
    app.layout = layout
    steps.step("Naming the boards by their MAC addresses")
    nodes = receiver_ports()
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    steps.step("Opening the identification window")
    win = IdentifyWindow(headless=False, layout=layout, focus_back=focus_back)
    c = EngineConsumer(app, win)
    win.key_sink = c.window_key
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                "In the identification window: click the walk's path on the map, then Done. Then press SPACE here as the "
                "walker starts. After the result, Next identification walk goes back to the map (the last path stays "
                "picked). The window comes back in front after SPACE, so Next takes one click. a / t = line A (away from / "
                "towards the TX); n = a new walker; q quits (n and q work in the window too).",
                "Keep the plot window visible during a walk (a hidden window can be slowed by macOS)."])
    rc = run(c, nodes, duration=minutes * 60.0 if minutes else None, mode="identify", stem=stem,
             run_config={"model": man["model"], "layout": layout, "direction_mode": dmode, "path_popup": True,
                         "device": str(getattr(eng.model, "device", None)),
                         "extract_mode": "staged", "extract_workers": extract_workers, "jsonl": app.jsonl})
    c.finish()
    rec = getattr(c, "record_dir", None)
    if rec:
        with open(os.path.join(rec, f"{stem}.summary.json"), "w", encoding="utf-8") as f:
            json.dump({"model": man["model"], "layout": layout, "rx2": list(rx2), "direction_mode": dmode,
                       "path_popup": True, "popup_picks": win.history, "popup_clicks_ignored_during_a_walk": win.ignored,
                       "space_refused": int(getattr(c, "refused", 0)), "device": str(getattr(eng.model, "device", None)),
                       "decisions": len(app.decisions), "jsonl": app.jsonl, "exit": rc,
                       "settles": list(getattr(eng.session, "settles", []) or []),
                       "skipped_walks_silent_receiver": app.skipped}, f, indent=1, default=str)
    print(json.dumps({"decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return rc



# P1 to P6 (the model's classes) -> the report's participant codes, PA1 to PA6: what the app shows and...
def code_names() -> dict:
    from pipeline.tracking.settings import PA_OF_CLASS
    return dict(PA_OF_CLASS)


# Function model dir.
def model_dir(name: str) -> str:
    return os.path.join(REPO_ROOT, "runs", "identify", "engine", "models", name)


# Whether a model's features take the per-packet gain step: its manifest's gs_adopted (false for every...
def gs_of(md: str) -> bool:
    with open(os.path.join(md, "manifest.json"), encoding="utf-8") as f:
        return bool(json.load(f)["gs_adopted"])


# The deployment model: engine v5n trained on all five sessions.
def deployment_model() -> str:
    return "deploy_all5_v5n"


# (model directory, manifest) of the deployment model; refuses unless the manifest is complete.
def load_deployment() -> tuple:
    d = model_dir(deployment_model())
    p = os.path.join(d, "manifest.json")
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: no deployment manifest at {p} (train it: python -m development.identify.RunLive.support.ide_train deploy_all5)")
    man = json.load(open(p))
    for k in ("model", "gs_adopted", "T_s", "config", "code_commit_at_training"):
        if k not in man:
            raise SystemExit(f"REFUSED: the manifest lacks {k}")
    return d, man


# The rig's device: --device if given, else mps (the engine is real time on the GPU only).
def rig_device(md: str, device: str = None) -> str:
    device = device or "mps"
    if device == "mps":
        import torch
        if not torch.backends.mps.is_available():
            raise SystemExit("REFUSED: --device mps (the default) but this machine has no MPS; pass --device cpu "
                             "(not real time: the adaptation reaches about 6 s a walk)")
    return device


# Function direction mode.
def direction_mode() -> str:
    import pipeline.identification.recordings as RP
    old = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        return RP.direction_mode()
    finally:
        os.chdir(old)


# The direction for a layout: at the identification spot from checks.json (direction_mode); at home from...
def direction_mode_for(layout: str) -> str:
    if layout == "id_spot":
        return direction_mode()
    p = os.path.join(REPO_ROOT, "runs", "identify", "engine", "checks", "direction_home.json")
    if not os.path.exists(p):
        return "recorded"
    return "detected" if json.load(open(p))["RULE_detected_used"] else "recorded"



SPACE_REFUSED = ("SPACE refused: this walk has no known path and the direction detector is not validated here; press a "
                 "(away from the TX) or t (towards it) as the walker starts on line A")


POPUP_SOURCE = "popup"


# Run_capture's extra consumer, and the recorded source's: frames in, keys on the same clock, the engine...
class EngineConsumer:
    owns_terminal = True
    SILENT_S = 1.0
    KEY_SLACK_S = 0.05

    # Screen: the live IdentifyWindow (its map gives each SPACE its path), a plain EngineScreen (the recorded...
    def __init__(self, app: EngineApp, screen=None, nodes=("RX1", "RX2", "RX3"), snapshots: str = None):
        import queue
        import threading
        self.app, self.screen, self.nodes = app, screen, tuple(nodes)
        self.window = screen if isinstance(screen, IdentifyWindow) else None
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
        self.refused = 0

    # Q or n pressed in the identification window: into the same key queue (and key record) as the Terminal's.
    def window_key(self, key: str) -> None:
        from pipeline.io.boards import KeyEvent
        (getattr(self, "key_input", None) or self.keys).put(KeyEvent(key, time.monotonic(), time.time()))

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
        from pipeline.io.boards import frame_of
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
        self._window_tick()

    # The held keys up to upto, in time order (data-time order: see the class docstring).
    def _keys(self, upto: float = np.inf) -> None:
        self._take_keys()
        self.keys_held.sort(key=lambda e: float(e.t_mono))
        while self.keys_held and float(self.keys_held[0].t_mono) <= upto:
            ev = self.keys_held.pop(0)
            w = self.window
            if ev.key == " ":
                route = self.routes.get(float(ev.t_mono))
                if route is not None:
                    self.app.press(ev.t_mono, path=route, source="known route")
                elif w is not None:
                    path = w.take(float(ev.t_mono))
                    if path is None:
                        self.refused += 1
                        print(w.refusal(), flush=True)
                    else:
                        self.app.press(ev.t_mono, path=path, source=POPUP_SOURCE)
                        w.walk_started(path, float(ev.t_mono), len(self.app.decisions))
                elif self.app.dmode == "detected":
                    self.app.press(ev.t_mono)
                else:
                    self.refused += 1
                    print(SPACE_REFUSED, flush=True)
            elif ev.key in ("a", "t"):
                path = "A_fwd" if ev.key == "a" else "A_rev"
                if w is None:
                    self.app.press(ev.t_mono, path=path, source="key")
                elif w.phase in ("choose", "ready"):
                    self.app.press(ev.t_mono, path=path, source="key")
                    w.walk_started(path, float(ev.t_mono), len(self.app.decisions))
                else:
                    self.refused += 1
                    print(w.refusal().replace("SPACE", ev.key), flush=True)
            elif ev.key == "n":
                self.app.new_walker()

    # The walk's result page once no walk is open (the last decision is out).
    def _window_tick(self) -> None:
        w = self.window
        if w is not None and w.phase == "walk" and not getattr(getattr(self.app, "e", None), "open_windows", 0):
            w.walk_ended(len(self.app.decisions))

    # What the screen shows, beyond the clock: the last decision, the walks seen, whether a walk is in progress...
    def _seen(self, st: dict) -> tuple:
        return (None if st["last"] is None else st["last"]["t0"], st["walks_seen"], bool(st["open"]), tuple(st["score"]),
                st["stream"], st.get("phase"), st.get("picked"))

    # The app's state for the screen, with the window's stage and the path picked on its map.
    def _state(self) -> dict:
        st = self.app.state()
        if self.window is not None:
            st.update(phase=self.window.phase, picked=self.window.picked)
        return st

    # Function after.
    def _after(self, got: list, now: float) -> None:
        if self.screen is None or not self.display:
            return
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

    # Now is the stream's time: run_capture passes the host's time.monotonic() (the clock of t_mono and of the...
    def tick(self, now: float) -> None:
        self._after(self._release(self._horizon(now), now), now)
        self._window_tick()
        self._announce(now)

    # The silent-receiver guard's messages: a receiver with no frame for over SILENT_S (rig.silent_receivers: in...
    def _announce(self, now: float) -> None:
        from pipeline.io.boards import silent_receivers
        silent = silent_receivers(self.last_t, now)
        for n in sorted(silent - self.silent):
            print(f"IDENTIFICATION: {n} is silent (no frames for over {self.SILENT_S:g} s); a walk while it is silent "
                  f"cannot be identified. Check its power and cable.", flush=True)
        for n in sorted(self.silent - silent):
            print(f"IDENTIFICATION: {n} is sending again.", flush=True)
        self.silent = silent



# The app's logic around one engine: presses, decisions, round trip, walker tally, JSON lines.
class EngineApp:

    # Sets up the object.
    def __init__(self, engine, model_name: str, replay: bool, jsonl: str = None, dmode: str = "detected",
                 extract_workers: int = None):
        self.e, self.model_name, self.replay, self.dmode = engine, model_name, replay, dmode
        self.written = 0
        self.extract_pool = None
        engine.session.hold = self._write_pending
        n = EXTRACT_WORKERS if extract_workers is None else int(extract_workers)
        if n > 0:
            engine.pool = self.extract_pool = ExtractPool(engine, n)
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

    # Each CNN run once on zero windows of the usual shapes (10 to 12 windows of 28 x 34; three channels for...
    def _warm(self) -> None:
        import pipeline.identification.classifiers as C
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

    # The last decision is out (written, and shown after the last poll), so its walk joins the pool first; then...
    def poll(self, now: float, closing: bool = False) -> list:
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
        if self.extract_pool is not None:
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
        import pipeline.identification.engine as EN
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
                "score": tuple(self.score), "stream": self.stream_label}


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
    out["schema"] = "id_engine_decision_v4"
    out.update({"engine_version": int(d["engine_version"]), "weight_a": round(float(d["weight_a"]), 4),
                "windows_s": [round(float(k), 2) for k in d["windows"]],
                "window_decisions_mono": [float(w["t_dec"]) for w in d["windows"].values()],
                "components": {f"{k:.2f}": {c: [round(float(x), 4) for x in v] for c, v in w["components"].items()}
                               for k, w in d["windows"].items()},
                "ensemble_without_pace_top": classes[int(np.argmax(d["ensemble_nopace"]))]})
    return out



# A model's training sessions, from its manifest.
def training_sessions(md: str) -> list:
    return list(json.load(open(os.path.join(md, "manifest.json")))["training_sessions"])


# Refuses any model trained on the streamed session.
def guard(md: str, session: str) -> list:
    ts = training_sessions(md)
    if session in ts:
        raise SystemExit(f"REFUSED: {os.path.basename(md)} was trained on {ts}, which includes the streamed session {session}; "
                         f"a recorded stream needs a model that never saw it (for {session}: loso_{session})")
    return ts


# The fold model that never saw session (engine v5n).
def final_model(session: str) -> str:
    return f"loso_{session}_v5n"


# The rig run: a recorded session through the rig's interface, the fold model that never saw it.
def recorded(a) -> int:
    import pipeline.identification.engine as EN
    from pipeline.identification.recordings import RecordedSource, stream
    os.chdir(REPO_ROOT)
    model = a.model or final_model(a.session)
    md = model_dir(model) if not os.path.isabs(model) else model
    ts = guard(md, a.session)
    eng = EN.Engine(md, T=EN.T_S, amp_norm=gs_of(md), layout="id_spot", device=rig_device(md, a.device))
    stem = time.strftime(f"rig_recorded_{a.session}_%Y%m%d_%H%M%S")
    app = EngineApp(eng, f"{os.path.basename(md)} (trained on {', '.join(ts)})", replay=True,
                    jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"), dmode=direction_mode(), extract_workers=a.extract_workers)
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


# A recorded session through the app: frames pushed as they arrived (in chunk_s arrival blocks, or paced in...
def replay_session(session: str, model: str = None, realtime: bool = False, speed: float = 1.0, screen: bool = False,
                   snapshots: str = None, device: str = "cpu", chunk_s: float = CHUNK_S, tally: bool = False,
                   jsonl: str = None, recordings: int = None, extract_workers: int = None) -> EngineApp:
    import pipeline.identification.engine as EN
    import pipeline.identification.recordings as RP
    from pipeline.io.serial_capture import read_capture_file
    os.chdir(REPO_ROOT)
    model = model or final_model(session)
    gs = gs_of(model_dir(model))
    dmode = RP.direction_mode()
    eng = EN.Engine(model_dir(model), T=EN.T_S, amp_norm=gs, device=device)
    app = EngineApp(eng, f"{model} (never saw {session})", replay=True, jsonl=jsonl, dmode=dmode, extract_workers=extract_workers)
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
                         jsonl=os.path.join(OUT_DIR, f"{stem}.jsonl"), recordings=a.recordings, extract_workers=a.extract_workers)
    print(json.dumps({"session": a.session, "decisions": len(app.decisions), "jsonl": app.jsonl}, indent=1))
    return 0



# Identify... (on the boards), identify-recorded... (IR) or replay-identify..., from main.py.
def main(argv=None) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m pipeline.main", description="identification: the one-press engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("identify", help="ON THE BOARDS: opens the serial ports; the deployment model")
    k.add_argument("--minutes", type=float, default=None)
    k.add_argument("--device", default=None, choices=("cpu", "mps"), help="default: mps (real time on the GPU only)")
    k.add_argument("--popup", action="store_true", help=argparse.SUPPRESS)
    k.add_argument("--no-focus-return", action="store_true",
                   help="do not give the keyboard to the Terminal at Done, nor the window back after SPACE")
    k.add_argument("--extract-workers", type=int, default=None, help=EXTRACT_HELP)
    g = sub.add_parser("identify-recorded", help="NO BOARDS: a recorded session streamed as if live (IR)")
    g.add_argument("--session", required=True, choices=("A1", "A2", "A3", "B1", "B2"), help="the recorded session")
    g.add_argument("--speed", default="1", help="1 = real time (or any factor), max = as fast as possible")
    g.add_argument("--from", dest="start", default=None, help="play from this recording (index, label or stem part); "
                   "earlier recordings are fed at maximum speed without display, so adaptation is the whole day's")
    g.add_argument("--render", choices=("natural",), default=None,
                   help="play only the session's natural identification blocks at --speed; the rest fed fast, hidden")
    g.add_argument("--screen", action="store_true", help="show the window for every played recording")
    g.add_argument("--snapshots", default=None, help="save the screen after each shown decision here")
    g.add_argument("--headless", action="store_true", help="draw off screen (with --snapshots: stills only, no window)")
    g.add_argument("--device", default=None, choices=("cpu", "mps"), help="default: mps (real time on the GPU only)")
    g.add_argument("--extract-workers", type=int, default=None, help=EXTRACT_HELP)
    g.add_argument("--model", default=None, help="a model that never saw the session (default: the final loso_<session>)")
    r = sub.add_parser("replay-identify", help="NO BOARDS: a recorded session through the app, as fast as possible "
                       "(the fold model that never saw it)")
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
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.cmd == "replay-identify":
        return cmd_replay(a)
    if a.cmd == "identify-recorded":
        return recorded(a)
    return on_the_boards(minutes=a.minutes, device=a.device, focus_back=not a.no_focus_return,
                         extract_workers=a.extract_workers)
