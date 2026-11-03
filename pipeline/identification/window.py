# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: I5, the identification window: the map of the twelve paths (click the walk's path, then Done), then the...

from __future__ import annotations

import json
import os
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_WORD = {"A_fwd": "away", "A_rev": "towards"}
NUMBER_WORDS = {5: "five"}
PICK_M = 0.4
LANE_M = 0.18
PATHS_FILE = os.path.join(REPO_ROOT, "runs", "public_model", "tracking_paths.json")



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
        import pipeline.identification.engine as EN
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
        if st.get("on_map"):
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
        if n_:
            lines.append(f"correct {k_} of {n_} ({100 * k_ / n_:.1f} %), chance 16.7 %")
        if st["open"]:
            lines.append("listening: walk in progress")
        nxt = st.get("walk_path")
        if nxt:
            s_, e_ = path_arrow(*lane_of(nxt, screen_paths()))
            ax.annotate("", xy=e_, xytext=s_, arrowprops={"arrowstyle": "-|>", "color": "tab:blue", "lw": 2, "ls": "--"})
            ax.set_xlabel(f"this walk: {nxt} (picked on the map)", fontsize=10, color="tab:blue", weight="bold")
        if d is None:
            bx.axis("off")
            cx.axis("off")
            if st.get("message"):
                msg = st["message"]
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
        order = pa_order(label)
        cols = ["tab:blue" if i == k else "0.7" for i in order]
        bx.bar(np.arange(6), np.asarray(conf)[order], color=cols)
        bx.axhline(1 / 6, color="red", ls="--", lw=1, label="chance 1 in 6")
        bx.set_xticks(np.arange(6), [label[i] for i in order])
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
            cx.bar(np.arange(6), np.asarray(p)[order], color="tab:purple")
            cx.axhline(1 / 6, color="red", ls="--", lw=1)
            cx.set_xticks(np.arange(6), [label[i] for i in order], fontsize=8)
            cx.set_ylim(0, 1)
            cx.set_title("round trip (away + towards)" if st["round_trip"] is not None else f"{d['tally']['k']} walks (this walker)", fontsize=9)
        else:
            cx.axis("off")
        v = x["wifi_speed"]
        lines = [f"Wi-Fi speed: {v:.2f} m/s" if np.isfinite(v) else "Wi-Fi speed: undefined",
                 f"latency: {d['latency_s']:.2f} s after the {d['T']:.0f} s window"] + lines
        tx.text(0, 1, "\n".join(lines), va="top", fontsize=9)
        n = len(d.get("components") or {})
        self.caption.set_text("One press when the walker starts. The answer comes from three 4 s windows of Wi-Fi signal (0, "
                              f"0.15 and 0.30 s after the press): gait features and Doppler maps, {NUMBER_WORDS.get(n, n)} models "
                              "summed and the windows averaged. Displayed confidence is their geometric mean.")
        self._show()

    # Function show.
    def _show(self):
        if self.headless:
            return
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    # The window's events only (between redraws); nothing is rebuilt.
    def pump(self) -> None:
        if not self.headless:
            self.fig.canvas.flush_events()

    # Function save.
    def save(self, path: str) -> None:
        self.fig.savefig(path, dpi=110)



# The live identification window: one window for every walk, in three stages.
class IdentifyWindow(EngineScreen):

    # Sets up the object.
    def __init__(self, headless: bool = False, layout: str = "home", paths: dict = None, focus_back: bool = None,
                 clock=None):
        super().__init__(headless=headless, layout=layout)
        from matplotlib.widgets import Button
        self.paths = dict(paths or screen_paths())
        self.lanes = {nm: lane_of(nm, self.paths) for nm in self.paths}
        self.clock = clock or time.monotonic
        self.focus_back = (not headless) if focus_back is None else bool(focus_back)
        self.phase = "choose"
        self.picked = None
        self.ready = None
        self.history = []
        self.ignored = 0
        self.decided = None
        self._n0 = 0
        if not headless and self.fig.canvas.manager:
            self.fig.canvas.manager.set_window_title("identification")
        self.mx = self.fig.add_axes([0.03, 0.06, 0.50, 0.80])
        self.mtext = self.fig.add_axes([0.58, 0.30, 0.40, 0.56])
        self.mtext.axis("off")
        self.done_ax = self.fig.add_axes([0.62, 0.10, 0.26, 0.11])
        self.next_ax = self.fig.add_axes([0.72, 0.90, 0.26, 0.07])
        self.done_btn = Button(self.done_ax, "Done")
        self.next_btn = Button(self.next_ax, "Next identification walk", color="#cfe8cf", hovercolor="#a8d8a8")
        self.done_btn.on_clicked(lambda _ev: self.done())
        self.next_btn.on_clicked(lambda _ev: self.next_walk())
        self.art = {}
        self._build_map()
        self.fig.canvas.mpl_connect("button_press_event", self._click)
        self.key_sink = None
        mgr = self.fig.canvas.manager
        if mgr is not None and getattr(mgr, "key_press_handler_id", None) is not None:
            self.fig.canvas.mpl_disconnect(mgr.key_press_handler_id)
        self.fig.canvas.mpl_connect("key_press_event", self._key)
        self._page()
        self._restyle()

    # A key pressed in this window: q and n act as in the Terminal; SPACE, a and t stay the Terminal's (their...
    def _key(self, ev) -> None:
        if ev.key in ("q", "n") and self.key_sink is not None:
            self.key_sink(ev.key)
        elif ev.key in (" ", "a", "t"):
            print(f"IDENTIFICATION: {'SPACE' if ev.key == ' ' else ev.key} is read in the Terminal: press Done, then "
                  "the key there.", flush=True)

    # Function build map.
    def _build_map(self) -> None:
        from matplotlib.patches import FancyArrowPatch
        ax = self.mx
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
        import pipeline.identification.engine as EN
        rx2 = tuple(EN._rigs()[self.layout]["RX2"])
        where = {"TX": ((2.5, -0.5), (14, -3), "left"), "RX1": ((2.5, 5.5), (14, -3), "left"),
                 "RX2": (rx2, (0, -14), "center"), "RX3": ((5.5, 2.5), (0, 8), "center")}
        for nm, ((x, y), off, ha) in where.items():
            ax.plot(x, y, "^", color="tab:purple", ms=7)
            ax.annotate(nm, (x, y), textcoords="offset points", xytext=off, ha=ha, fontsize=8, color="tab:purple")
        ax.set_xlim(-1.0, 6.0)
        ax.set_ylim(-1.0, 6.0)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])

    # The path drawn nearest to (x, y) on the grid, within PICK_M, or None.
    def pick(self, x: float, y: float):
        p = np.array([x, y], float)
        best, dist = None, PICK_M
        for nm, (a, b) in self.lanes.items():
            ab = b - a
            q = a + np.clip(float(np.dot(p - a, ab) / max(float(np.dot(ab, ab)), 1e-12)), 0.0, 1.0) * ab
            d_ = float(np.hypot(*(p - q)))
            if d_ <= dist:
                best, dist = nm, d_
        return best

    # Function click.
    def _click(self, ev) -> None:
        if ev.inaxes is not self.mx or ev.xdata is None:
            return
        nm = self.pick(ev.xdata, ev.ydata)
        if nm is not None:
            self.choose(nm)

    # A click on the map: the path it picks is highlighted (the map only takes clicks while it is shown).
    def choose(self, path: str) -> bool:
        if path not in self.paths:
            raise ValueError(f"{path!r} is not one of the tracking paths {sorted(self.paths)}")
        if self.phase != "choose":
            self.ignored += 1
            return False
        self.picked = path
        self._restyle()
        self._show()
        return True

    # Done: the picked path is the walk's path; the result page waits for SPACE in the Terminal.
    def done(self) -> bool:
        if self.phase != "choose" or self.picked is None:
            print("IDENTIFICATION: click the walk's path on the map first, then Done.", flush=True)
            return False
        self.ready = (float(self.clock()), self.picked)
        self.history.append(self.ready)
        self.phase = "ready"
        print(f"IDENTIFICATION: walk {self.picked}. Press SPACE in the Terminal as the walker starts.", flush=True)
        if self.focus_back:
            focus_terminal()
        return True

    # A SPACE at time t: the walk's path when the window is waiting and Done came before the key, else None.
    def take(self, t: float):
        if self.phase == "ready" and self.ready is not None and self.ready[0] <= float(t):
            return self.ready[1]
        return None

    # Function refusal.
    def refusal(self) -> str:
        return {"choose": "SPACE refused: click the walk's path on the map and press Done first.",
                "walk": "SPACE refused: a walk is in progress; wait for its result.",
                "result": "SPACE refused: press Next identification walk on the screen first."}.get(
                    self.phase, "SPACE refused: it came before Done; press it again as the walker starts.")

    # A press was given (SPACE after Done, or a / t): the walk is in progress.
    def walk_started(self, path: str, t: float, n_decisions: int) -> None:
        self.ready = (float(t), path)
        self.phase = "walk"
        self._n0 = int(n_decisions)
        if self.focus_back:
            bring_to_front()

    # The walk's windows are all closed: its result (or that it gave none) and the Next button.
    def walk_ended(self, n_decisions: int) -> None:
        self.decided = int(n_decisions) > self._n0
        self.phase = "result"

    # Next identification walk: back to the map, the last path still highlighted.
    def next_walk(self) -> bool:
        if self.phase != "result":
            return False
        self.phase, self.ready = "choose", None
        self._restyle()
        return True

    # Function page.
    def _page(self) -> None:
        on_map = self.phase == "choose"
        for x in (self.mx, self.mtext, self.done_ax):
            x.set_visible(on_map)
        for x in (self.ax, self.bx, self.cx, self.tx):
            x.set_visible(not on_map)
        self.next_ax.set_visible(self.phase == "result")
        if on_map:
            self.caption.set_text("")

    # Function restyle.
    def _restyle(self) -> None:
        for nm, (arr, lab) in self.art.items():
            on = nm == self.picked
            arr.set_color("tab:green" if on else "0.6")
            arr.set_linewidth(3.4 if on else 1.6)
            arr.set_zorder(4 if on else 2)
            lab.set_color("tab:green" if on else "0.35")
            lab.set_fontweight("bold" if on else "normal")
        ok = self.picked is not None
        self.done_btn.label.set_text(f"Done: walk {self.picked}" if ok else "Done (pick a path first)")
        self.done_btn.color = "#cfe8cf" if ok else "0.9"
        self.done_btn.hovercolor = "#a8d8a8" if ok else "0.9"
        self.done_ax.set_facecolor(self.done_btn.color)

    # Function draw.
    def draw(self, st: dict, now: float = None) -> None:
        self._page()
        if self.phase == "choose":
            self.header.set_text("IDENTIFICATION: pick the next walk's path")
            self.mtext.clear()
            self.mtext.axis("off")
            k_, n_ = st.get("score") or (0, 0)
            lines = ["1.  Click the walk's path on the map",
                     "     (one click gives the line and the direction).",
                     "2.  Press Done.",
                     "3.  Press SPACE in the Terminal as the walker starts.", "",
                     f"picked: {self.picked}" if self.picked else "picked: nothing yet", "",
                     f"model: {st['model']}", f"adapting to this room: {st['walks_seen']} walks seen"]
            if n_:
                lines.append(f"correct {k_} of {n_} ({100 * k_ / n_:.1f} %), chance 16.7 %")
            self.mtext.text(0, 1, "\n".join(lines), va="top", fontsize=11)
            self._show()
            return
        st = dict(st, on_map=True, walk_path=self.ready[1] if self.ready else None)
        if self.phase == "ready":
            st.update(last=None, message=f"walk: {self.ready[1]}\n\npress SPACE in the Terminal as the walker starts")
        elif self.phase == "walk":
            st.update(last=None, message=f"walk: {self.ready[1]}\n\nlistening: walk in progress ...")
        elif self.phase == "result" and not self.decided:
            st.update(last=None, message="no decision for this walk (a receiver was silent)\n\n"
                                         "press Next identification walk")
        super().draw(st, now)
        self._page()
        self._show()


# Make this process the active app (macOS), so its window comes in front of the Terminal and takes a click...
def bring_to_front() -> None:
    import sys
    if sys.platform != "darwin":
        return
    try:
        import ctypes
        import ctypes.util
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_getClass.restype = objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = objc.objc_msgSend
        send.restype, send.argtypes = ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]
        app = send(objc.objc_getClass(b"NSApplication"), objc.sel_registerName(b"sharedApplication"))
        send.restype, send.argtypes = ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
        send(app, objc.sel_registerName(b"activateIgnoringOtherApps:"), True)
    except Exception:
        pass


# Give the keyboard back to the Terminal the app runs in, so SPACE reaches the key reader (macOS; not waited...
def focus_terminal() -> None:
    import subprocess
    import sys
    app = {"Apple_Terminal": "Terminal", "iTerm.app": "iTerm", "vscode": "Visual Studio Code"}.get(
        os.environ.get("TERM_PROGRAM", ""))
    if sys.platform == "darwin" and app:
        subprocess.Popen(["open", "-a", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



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


# Tracking_paths(), read once per process (the screen and the map draw from it).
def screen_paths() -> dict:
    if not _SCREEN_PATHS:
        _SCREEN_PATHS.update(tracking_paths())
    return _SCREEN_PATHS


# The path as the map draws it: moved LANE_M to its own left when its reverse is also offered (so a line's...
def lane_of(path: str, paths: dict) -> tuple:
    s, e = (np.asarray(x, float) for x in paths[path])
    u = (e - s) / max(float(np.hypot(*(e - s))), 1e-9)
    both = any(tuple(paths[path][1]) == tuple(s2) and tuple(paths[path][0]) == tuple(e2) for s2, e2 in paths.values())
    off = LANE_M * np.array([-u[1], u[0]]) if both else np.zeros(2)
    return s + off, e + off


# A path drawn as an arrow from its start to its end, inset metres in from both ends (line A's arrow as before).
def path_arrow(start, end, inset: float = 0.3) -> tuple:
    a, b = np.asarray(start, float), np.asarray(end, float)
    u = (b - a) / max(float(np.hypot(*(b - a))), 1e-9)
    return tuple(a + inset * u), tuple(b - inset * u)


# The positions of labels sorted PA1 to PA6, so every chart reads in the report's order.
def pa_order(labels: list) -> np.ndarray:
    return np.array(sorted(range(len(labels)), key=lambda i: (int(labels[i][2:]) if str(labels[i])[2:].isdigit() else 99, i)))


# Function norm.
def _norm(lp):
    lp = np.asarray(lp, float)
    m = lp.max()
    return lp - (m + np.log(np.exp(lp - m).sum()))
