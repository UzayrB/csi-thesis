# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The tracking window itself: the room, the twelve lines, the receivers, the dot and the decision.

from __future__ import annotations

import numpy as np

TX, RX1, RX3 = (2.5, -0.5), (2.5, 5.5), (5.5, 2.5)
RX2_HOME = (-0.5, 2.5)


# Class Screen.
class Screen:
    # Sets up the object.
    def __init__(self, st, headless: bool = False, title: str = "TDR-03 live"):
        import matplotlib
        if headless:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        self.plt, self.st, self.headless = plt, st, headless
        self.fig = plt.figure(figsize=(11.0, 6.4))
        self.fig.canvas.manager.set_window_title(title) if not headless and self.fig.canvas.manager else None
        self.ax = self.fig.add_axes([0.04, 0.10, 0.50, 0.82])
        self.bx = self.fig.add_axes([0.62, 0.52, 0.35, 0.36])
        self.cx = self.fig.add_axes([0.62, 0.10, 0.35, 0.30])
        self.caption = self.fig.text(0.04, 0.02, "", fontsize=9, color="0.25")
        self.header = self.fig.text(0.04, 0.955, "", fontsize=13, weight="bold")
        if not headless:
            plt.ion()
            plt.show(block=False)

    # Function room.
    def _room(self, rx2):
        ax = self.ax
        ax.clear()
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            p = np.asarray(self.st.xy[a:b], float)
            ax.plot(p[:, 0], p[:, 1], color="0.86", lw=3, zorder=1)
        for g in np.arange(0, 5.001, 1.0):
            ax.axhline(g, color="0.94", lw=0.6, zorder=0)
            ax.axvline(g, color="0.94", lw=0.6, zorder=0)
        for nm, (x, y) in {"TX": TX, "RX1": RX1, "RX2": rx2, "RX3": RX3}.items():
            ax.plot(x, y, "^", color="tab:purple", ms=8, zorder=3)
            ax.annotate(nm, (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8,
                        color="tab:purple")
        ax.set_xlim(-1.0, 6.0)
        ax.set_ylim(-1.0, 6.0)
        ax.set_aspect("equal")

    # Verdict: {"committed", "drawn", "true"}; "true" is None when there is no ground truth (the rig).
    def tracking(self, *, dot=None, line=None, switched=False, green=None, verdict=None, status="",
                 t_scene=None):
        from pipeline.live.RunLive.tracking_display import LATENCY_S
        self._room(RX2_HOME)
        self.header.set_text("TRACKING")
        if line:
            a, b = self.st.slice_of[line]
            p = np.asarray(self.st.xy[a:b], float)
            self.ax.plot(p[:, 0], p[:, 1], color="tab:orange" if switched else "tab:blue", lw=4, zorder=2,
                         label=("switched to " if switched else "locked: ") + line)
        if green is not None:
            self.ax.plot([green[0]], [green[1]], "o", color="tab:green", ms=11, zorder=5,
                         label=f"where the person was {LATENCY_S:g} s ago")
        if dot is not None:
            self.ax.plot([dot[0]], [dot[1]], "o", color="red", ms=9, zorder=6,
                         label="the tracker's answer for that same moment")
        for x in (self.bx, self.cx):
            x.clear()
            x.axis("off")
        if line or green is not None or dot is not None:
            h, lab = self.ax.get_legend_handles_labels()
            self.cx.legend(h, lab, loc="upper left", fontsize=9, frameon=False)
        self.bx.text(0.0, 1.0, status, fontsize=9, va="top", family="monospace", transform=self.bx.transAxes)
        if verdict:
            self._verdict(verdict)
        self.caption.set_text(f"THE WHOLE DISPLAY RUNS {LATENCY_S:g} s BEHIND REAL TIME. Nothing is projected: every\n"
                              "position drawn is one the decoder produced from radio already recorded."
                              + (f"   scene time {t_scene:.1f}" if t_scene is not None else ""))
        self._draw()

    # The end-of-walk banner, on the right: the SHIPPED committed decision, the drawn line, and, with a ground...
    def _verdict(self, v):
        if v.get("pending"):
            self.bx.text(0.0, 0.62, f"WALK OVER\n\ncommitted decision: still deciding\ndrawn: {v.get('drawn') or 'none'}",
                         fontsize=11, va="top", family="monospace", transform=self.bx.transAxes,
                         bbox={"facecolor": "#eeeeee", "edgecolor": "0.5", "linewidth": 2,
                               "boxstyle": "round,pad=0.6"})
            return
        right = None if v.get("true") is None else v["committed"] == v["true"]
        face = {True: "#c8e6c9", False: "#ffcdd2", None: "#eeeeee"}[right]
        edge = {True: "tab:green", False: "tab:red", None: "0.5"}[right]
        head = {True: "RIGHT", False: "WRONG", None: "NO GROUND TRUTH"}[right]
        agree = "agrees" if v["committed"] == v.get("drawn") else "differs"
        lines = [head, "", f"{v.get('label') or 'committed (shipped, semi-bounded)'}: {v['committed'] or 'none'}",
                 f"drawn: {v.get('drawn') or 'none'} ({agree})"]
        if v.get("true") is not None:
            lines.append(f"true: {v['true']}")
        self.bx.text(0.0, 0.62, "\n".join(lines), fontsize=11, va="top", family="monospace",
                     transform=self.bx.transAxes,
                     bbox={"facecolor": face, "edgecolor": edge, "linewidth": 2, "boxstyle": "round,pad=0.6"})

    # Function draw.
    def _draw(self):
        if self.headless:
            return
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
