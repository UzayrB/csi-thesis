"""The live screen: one window, two modes.

TRACKING draws the room, the twelve lines, the receivers where tracking needs them (RX2 at home), the
red dot, the drawn line (the lock, or the one switch), the green marker where the walker was 2.0 s ago
when a ground truth exists (a replayed recording's sidecar), and on the right the end-of-walk banner
naming the SHIPPED committed decision, green when it is the true line and red when it is not. The caption states the delay, because the whole display runs 2.0 s behind real
time (RENDER_RULES V1, rule 3).

IDENTIFICATION draws the enrolled people's probabilities for the last pass, chance marked (1 in the
number enrolled), and S0, the speed-only control, beside them, with the pass's speed. A viewer can see
whether a confident answer is only reading pace. Optionally the product over the passes so far
(addendum C's MULTI-PASS row). The receivers are drawn where identification needs them (RX2 at the
spot).

It draws what it is given and decides nothing. `Screen(headless=True)` renders to files (the replay
evidence); otherwise it opens an interactive window.
"""

from __future__ import annotations

import numpy as np

TX, RX1, RX3 = (2.5, -0.5), (2.5, 5.5), (5.5, 2.5)
RX2_HOME, RX2_SPOT = (-0.5, 2.5), (2.0, -0.5)


class Screen:
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

    # -- tracking ------------------------------------------------------------------------------
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

    def tracking(self, *, dot=None, line=None, switched=False, green=None, verdict=None, status="",
                 t_scene=None, identity=None):
        """verdict: {"committed", "drawn", "true"}; "true" is None when there is no ground truth (the rig)."""
        from pipeline.live.display import LATENCY_S
        self._room(RX2_HOME)
        self.header.set_text("TRACKING")
        if line:
            a, b = self.st.slice_of[line]
            p = np.asarray(self.st.xy[a:b], float)
            self.ax.plot(p[:, 0], p[:, 1], color="tab:orange" if switched else "tab:blue", lw=4, zorder=2,
                         label=("switched to " if switched else "locked: ") + line)
        if green is not None:                                     # f3_render's marker
            self.ax.plot([green[0]], [green[1]], "o", color="tab:green", ms=11, zorder=5,
                         label=f"where the person was {LATENCY_S:g} s ago")
        if dot is not None:
            self.ax.plot([dot[0]], [dot[1]], "o", color="red", ms=9, zorder=6,
                         label="the tracker's answer for that same moment")
        for x in (self.bx, self.cx):
            x.clear()
            x.axis("off")
        if line or green is not None or dot is not None:            # the key sits in the right panel
            h, lab = self.ax.get_legend_handles_labels()
            self.cx.legend(h, lab, loc="upper left", fontsize=9, frameon=False)
        if identity:                           # identification's decision for this walk (the screen only)
            status = status + f"\nwho: {identity.get('top')}  p {identity.get('probability')}"
        self.bx.text(0.0, 1.0, status, fontsize=9, va="top", family="monospace", transform=self.bx.transAxes)
        if verdict:
            self._verdict(verdict)
        self.caption.set_text(f"THE WHOLE DISPLAY RUNS {LATENCY_S:g} s BEHIND REAL TIME. Nothing is projected: every\n"
                              "position drawn is one the decoder produced from radio already recorded."
                              + (f"   scene time {t_scene:.1f}" if t_scene is not None else ""))
        self._draw()

    def _verdict(self, v):
        """The end-of-walk banner, on the right: the SHIPPED committed decision, the drawn line, and, with a
        ground truth, the true line. Green when the committed line is the true one, red when it is not,
        grey when there is no truth to judge it by."""
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

    # -- identification ------------------------------------------------------------------------
    def identification(self, *, result=None, combined=None, n_passes=0, names=None, status=""):
        """result: `LiveIdentifier.predict` output for the last pass; names: {anon code: shown name}."""
        self._room(RX2_SPOT)
        self.header.set_text("IDENTIFICATION")
        a, b = self.st.slice_of["A_fwd"]
        p = np.asarray(self.st.xy[a:b], float)
        self.ax.plot(p[:, 0], p[:, 1], color="tab:green", lw=4, zorder=2, label="walk: line A, away from the TX")
        self.ax.legend(loc="upper right", fontsize=8)
        for x in (self.bx, self.cx):
            x.clear()
        if result is None:
            self.bx.axis("off")
            self.cx.axis("off")
            self.bx.text(0.0, 0.9, status or "waiting for a pass", fontsize=10, va="top")
            self._draw()
            return
        cls = sorted(result["proba"])
        lab = [(names or {}).get(c, c) for c in cls]
        x = np.arange(len(cls))
        self.bx.bar(x - 0.2, [result["proba"][c] for c in cls], 0.4, color="tab:blue", label="gait (PRIMARY)")
        self.bx.bar(x + 0.2, [result["s0_proba"].get(c, 0.0) for c in cls], 0.4, color="0.7",
                    label="speed only (S0)")
        self.bx.axhline(result["chance"], color="red", ls="--", lw=1, label=f"chance {100 * result['chance']:.1f} %")
        self.bx.set_xticks(x, lab, fontsize=8)
        self.bx.set_ylim(0, 1)
        self.bx.set_title(f"last pass: {result['speed_m_s']:.2f} m/s, gait says "
                          f"{(names or {}).get(result['pred'], result['pred'])}, speed says "
                          f"{(names or {}).get(result['s0_pred'], result['s0_pred'])}", fontsize=9)
        self.bx.legend(fontsize=7, loc="upper right")
        if combined:
            self.cx.bar(x, [combined.get(c, 0.0) for c in cls], 0.5, color="tab:purple")
            self.cx.axhline(result["chance"], color="red", ls="--", lw=1)
            self.cx.set_xticks(x, lab, fontsize=8)
            self.cx.set_ylim(0, 1)
            self.cx.set_title(f"gait, combined over {n_passes} passes", fontsize=9)
        else:
            self.cx.axis("off")
        self.caption.set_text("A CLOSED SET: only enrolled people can be named. The pre-registered expectation is that\n"
                              "one pass will not separate from chance; compare the gait bars with the speed-only bars."
                              + (f"   {status}" if status else ""))
        self._draw()

    # -- output --------------------------------------------------------------------------------
    def _draw(self):
        if self.headless:
            return
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def save(self, path: str) -> None:
        self.fig.savefig(path, dpi=90)
