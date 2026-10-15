"""Queue 15 (a): the two Results figures redrawn for the shipped display, `clean_1s_r0` (Editor list E10 and E11; Uzayr's go in
the Code agent's chat). No script for either figure exists in the Code or the report repository, so each matches the current
PDF's style as read from its own drawing stream (sizes, Times New Roman at 8 and 9 pt, colours, line widths, dash patterns).
The previous PDFs are kept here as `*_previous.pdf` for rollback.

E10, fig:error-cdf (`results_dot_cdf.pdf`): the cumulative dot error, from the first decoded frame against the truth 2.0 s
earlier (app_score.score_recording), (a) all walks and (b) correct-lock walks, for B2 and A3 (deployed) and B2 (zero-shot),
from the shipped profile's replays (`runs/switch_radius_a3b2_2026-10-14/R0/`). Asserted: panel (b)'s frames equal
`clean_1s`'s (`runs/head_offset_2026-10-14/step4_cpu/`, the display the current PDF drew).
E11, fig:decode-example (`results_decode_example.pdf`): two B2 C_fwd walks of the deployed model chosen by the figure's own
rule (the first in sorted log order of each kind: (a) lock and committed right, (b) locked E_col1, committed C_fwd), drawn
from the shipped profile's replay. Asserted: both walks are the ones the current figure shows (the 11 Oct comment's recording
and pass), the old caption's numbers reproduce from the 0.75 s replay the current PDF drew (0.18 and 2.35 m, 1.15 and 1.03 s),
and panel (a)'s rows equal `clean_1s`'s (the radius changes only panel (b)).

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. nice -n 10 python3 runs/switch_radius_ship_2026-10-14/figures/results_figures.py

Development evaluation, all data seen; inside A3's tenth and B2's eighth looks (no decode).
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
REPORT_FIGS = os.path.join(os.path.dirname(REPO), "BLLUZA001_Final_Year_Report", "Figures")
R0 = lambda m: J(REPO, "runs", "switch_radius_a3b2_2026-10-14", "R0", m, "semi_disp-K1gf_prof-clean_1s_r0_causal")   # noqa: E731
R15 = lambda m: J(REPO, "runs", "head_offset_2026-10-14", "step4_cpu", m, "semi_disp-K1gf_causal")                     # noqa: E731
OLD075 = J(REPO, "runs", "live", "replay", "final", "semi_disp-K1gf_causal")
BLUE, ORANGE, GREEN = (0.1647058824, 0.4705882353, 0.8392156863), (0.9215686275, 0.4078431373, 0.2039215686), \
    (0.1058823529, 0.6862745098, 0.4784313725)
GRID_CDF, MARK05 = (0.8941176471, 0.8901960784, 0.8745098039), (0.5411764706, 0.537254902, 0.5176470588)
PA = {"PA1": "PA1", "PA2": "PA2", "PA3": "PA3", "PA4": "PA4", "PA5": "PA5", "PA6": "PA6"}
OTHER, GRID_MAP = (0.7254901961, 0.7215686275, 0.6980392157), (0.9254901961, 0.9215686275, 0.9058823529)


def rc():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"], "mathtext.fontset": "stix",
                         "font.size": 9, "pdf.fonttype": 42, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
                         "ytick.major.width": 0.6, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def walks(d: str, session: str) -> list:
    """app_score.score_recording's rows for every recording of the session in the folder, in sorted log order."""
    import pipeline.live.app_score as S
    out = []
    for lp in sorted(glob.glob(J(d, f"{session}__*.jsonl"))):
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        for r in S.score_recording(lp, J(S.DATA[session], f"{stem}.gt.json"), "committed"):
            out.append(dict(r, stem=stem, log=lp))
    return out


def ecdf(e: list, xs: np.ndarray) -> np.ndarray:
    v = np.sort(np.asarray(e, float))
    return 100.0 * np.searchsorted(v, xs, side="right") / len(v)


def cdf_figure(res: dict) -> None:
    cells = [("B2, deployed", "final", "B2", BLUE, "-"), ("A3, deployed", "final", "03", ORANGE, (0, (3.7, 1.6))),
             ("B2, zero-shot", "zeroshot", "B2", GREEN, (0, (1.2, 1.2)))]
    data, chk = {}, {}
    for lab, m, s, _c, _ls in cells:
        new, old = walks(R0(m), s), walks(R15(m), s)
        assert [(w["stem"], w["pid"], w["lock_correct"]) for w in new] == [(w["stem"], w["pid"], w["lock_correct"]) for w in old]
        e_all = [e for w in new for e in w["err"]]
        e_ok = [e for w in new if w["lock_correct"] for e in w["err"]]
        o_ok = [e for w in old if w["lock_correct"] for e in w["err"]]
        o_all = [e for w in old for e in w["err"]]
        assert e_ok == o_ok, f"{lab}: panel (b)'s frames differ from clean_1s's"
        data[lab] = (e_all, e_ok)
        chk[lab] = {"walks": len(new), "frames_all": len(e_all), "frames_correct_lock": len(e_ok),
                    "ASSERT_panel_b_equal_to_clean_1s": True, "panel_a_equal_to_clean_1s": e_all == o_all,
                    "all_walks_within_0_5m_pct": {"new": float(np.mean(np.asarray(e_all) <= 0.5) * 100),
                                                  "clean_1s": float(np.mean(np.asarray(o_all) <= 0.5) * 100)},
                    "all_walks_median_m": {"new": float(np.median(e_all)), "clean_1s": float(np.median(o_all))},
                    "correct_lock_median_m": float(np.median(e_ok))}
    plt = rc()
    fig = plt.figure(figsize=(446.4 / 72, 176.4 / 72))
    axa = fig.add_axes([0.078, 0.2, 0.43, 0.7])
    axb = fig.add_axes([0.555, 0.2, 0.43, 0.7], sharey=axa)
    xs = np.linspace(0.0, 3.0, 1201)
    for ax, which, title in ((axa, 0, "(a) All walks"), (axb, 1, "(b) Correct-lock walks")):
        ax.grid(True, color=GRID_CDF, lw=0.5)
        ax.set_axisbelow(True)
        ax.axvline(0.5, color=MARK05, lw=0.6, ls=":")
        for lab, _m, _s, col, ls in cells:
            ax.plot(xs, ecdf(data[lab][which], xs), color=col, lw=1.4, ls=ls, label=lab)
        ax.set_xlim(0, 3.0)
        ax.set_ylim(0, 100)
        ax.set_xticks(np.arange(0, 3.01, 0.5))
        ax.set_xticklabels([f"{v:.1f}" for v in np.arange(0, 3.01, 0.5)])
        ax.set_yticks(range(0, 101, 20))
        ax.set_xlabel("Dot error (m)")
        ax.set_title(title, loc="left", fontsize=9, pad=4)
    axa.set_ylabel("Frames within error (%)")
    plt.setp(axb.get_yticklabels(), visible=False)
    axb.legend(loc="lower right", frameon=False, fontsize=9, handlelength=2.6)
    fig.savefig(J(HERE, "results_dot_cdf.pdf"))
    fig.savefig(J(HERE, "results_dot_cdf_preview.png"), dpi=250)
    plt.close(fig)
    res["E10_results_dot_cdf"] = chk


def pick(ws: list, kind: str) -> dict:
    """The figure's rule: the first B2 C_fwd walk in sorted log order of each kind."""
    if kind == "a":
        sel = [w for w in ws if w["true"] == "C_fwd" and w["lock_correct"] and w["committed_correct"]]
    else:
        sel = [w for w in ws if w["true"] == "C_fwd" and w["lock"] == "E_col1" and w["committed"] == "C_fwd"]
    return sel[0]


def walk_rows(w: dict) -> dict:
    rows = [json.loads(x) for x in open(w["log"], encoding="utf-8")]
    pid = w["pid"]
    P = [r for r in rows if r.get("pid") == pid]
    press = next(float(r["t"]) for r in P if r["kind"] == "press")
    lock = next(r for r in P if r["kind"] == "lock")
    dots = sorted((r for r in P if r["kind"] == "dot" and float(r["x"]) >= press + 2.0 - 1e-4), key=lambda r: float(r["x"]))
    sw = [r for r in P if r["kind"] == "switch"]
    return {"press": press, "lock": lock, "dots": dots, "switches": sw, "rows": P}


def decode_figure(res: dict) -> None:
    import pipeline.live.app_score as S
    new, old75, r15 = walks(R0("final"), "B2"), walks(OLD075, "B2"), walks(R15("final"), "B2")
    stems = sorted({w["stem"] for w in new})
    out = {}
    for kind in ("a", "b"):
        w, w75, w15 = pick(new, kind), pick(old75, kind), pick(r15, kind)
        assert (w["stem"], w["pid"]) == (w75["stem"], w75["pid"]) == (w15["stem"], w15["pid"])
        rn, r75, rr15 = walk_rows(w), walk_rows(w75), walk_rows(w15)
        rec = stems.index(w["stem"]) + 1
        first_xy = np.asarray(rn["dots"][0]["xy"], float)
        entry = np.asarray(S._line_ends(w["lock"])[0], float)
        out[kind] = {"recording": f"{rec} of {len(stems)}", "pass": w["pid"], "pa": None,
                     "true": w["true"], "lock": w["lock"], "committed": w["committed"],
                     "dot_median_m": float(np.median(w["err"])), "announce_latency_s": float(w["announce_latency_s"]),
                     "first_frame_from_lock_entry_m": float(np.hypot(*(first_xy - entry))),
                     "switches": [{"after_press_s": round(float(s["x"]) - rn["press"], 2), "old": s["old"], "new": s["new"]}
                                  for s in rn["switches"]],
                     "old_figure_0p75s": {"dot_median_m": float(np.median(w75["err"])),
                                          "announce_latency_s": float(w75["announce_latency_s"])},
                     "equal_to_clean_1s_rows": rn["rows"] == rr15["rows"]}
        out[kind]["_rows"] = rn
    # the current figure's walks (its 11 Oct comment): (a) recording 3 of 6, pass 2; (b) recording 1 of 6, pass 3
    assert (out["a"]["recording"], out["a"]["pass"]) == ("3 of 6", 2), out["a"]
    assert (out["b"]["recording"], out["b"]["pass"]) == ("1 of 6", 3), out["b"]
    # the current caption's numbers reproduce from the 0.75 s replay it drew
    assert round(out["a"]["old_figure_0p75s"]["dot_median_m"], 2) == 0.18, out["a"]["old_figure_0p75s"]
    assert round(out["b"]["old_figure_0p75s"]["dot_median_m"], 2) == 2.35, out["b"]["old_figure_0p75s"]
    assert round(out["a"]["old_figure_0p75s"]["announce_latency_s"], 2) == 1.15
    assert round(out["b"]["old_figure_0p75s"]["announce_latency_s"], 2) == 1.03
    assert out["a"]["equal_to_clean_1s_rows"], "panel (a)'s walk differs from clean_1s's"
    out["a"]["pa"] = PA[next(w["stem"] for w in new if stems.index(w["stem"]) + 1 == 3).split("_")[1]]
    out["b"]["pa"] = PA[next(w["stem"] for w in new if stems.index(w["stem"]) + 1 == 1).split("_")[1]]

    plt = rc()
    from matplotlib.lines import Line2D
    fig = plt.figure(figsize=(424.8 / 72, 259.2 / 72))
    axs = [fig.add_axes([0.075, 0.25, 0.425, 0.67]), fig.add_axes([0.555, 0.25, 0.425, 0.67])]
    S._line_ends("C_fwd")                                   # fills app_score's line table (the room's geometry)
    names = sorted(S._LINES)
    titles = {"a": f"(a) Lock {out['a']['lock']}, committed {out['a']['committed']}",
              "b": f"(b) Lock {out['b']['lock']}, switch to {out['b']['switches'][0]['new']}" if out["b"]["switches"]
              else f"(b) Lock {out['b']['lock']}, committed {out['b']['committed']}"}
    for ax, kind in zip(axs, ("a", "b")):
        o, rn = out[kind], out[kind]["_rows"]
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.grid(True, color=GRID_MAP, lw=0.5)
        ax.set_axisbelow(True)
        for nm in names:
            a, b = S._line_ends(nm)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=OTHER, lw=0.8, zorder=1)
        la, lb = S._line_ends(o["lock"])
        ax.plot([la[0], lb[0]], [la[1], lb[1]], color=ORANGE, alpha=0.35, lw=4, solid_capstyle="round", zorder=2)
        ta, tb = S._line_ends(o["true"])
        ax.annotate("", xy=tb, xytext=ta, arrowprops=dict(arrowstyle="-|>", color="black", lw=1.3, mutation_scale=9,
                                                          shrinkA=0, shrinkB=0), zorder=3)
        xy = np.asarray([d["xy"] for d in rn["dots"]], float)
        ax.plot(xy[:, 0], xy[:, 1], color=BLUE, lw=1.0, marker="o", ms=3.2, mfc=BLUE, mec="white", mew=0.3, zorder=4)
        ax.plot([xy[0, 0]], [xy[0, 1]], marker="s", ms=5.5, color=BLUE, ls="none", zorder=5)
        for s in rn["switches"]:
            xs_ = float(s["x"])
            k = int(np.searchsorted([float(d["x"]) for d in rn["dots"]], xs_ - 1e-6)) - 1    # the last frame on the old line
            ax.plot([xy[k, 0]], [xy[k, 1]], marker="D", ms=5, mfc="white", mec=BLUE, mew=1.0, ls="none", zorder=6)
        ax.set_xlim(-0.25, 5.25)
        ax.set_ylim(-0.25, 5.25)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("x (m)")
        ax.set_title(titles[kind], loc="left", fontsize=9, pad=4)
    axs[0].set_ylabel("y (m)")
    h = [Line2D([], [], color="black", lw=1.3), Line2D([], [], color=ORANGE, alpha=0.35, lw=4),
         Line2D([], [], color=BLUE, lw=1.0, marker="o", ms=3.2, mfc=BLUE, mec="white", mew=0.3),
         Line2D([], [], color=BLUE, marker="s", ms=5.5, ls="none"),
         Line2D([], [], color=OTHER, lw=0.8),
         Line2D([], [], marker="D", ms=5, mfc="white", mec=BLUE, mew=1.0, ls="none")]
    sw = out["b"]["switches"][0]["after_press_s"] if out["b"]["switches"] else None
    labs = ["True line", "Locked line", "Drawn dot, 0.1 s apart", "First frame, press + 2.0 s", "The other lines",
            f"Switch, press + {sw:.1f} s" if sw is not None else "Switch"]
    fig.legend(h, labs, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.53, 0.0),
               columnspacing=2.2, handlelength=2.6)
    fig.savefig(J(HERE, "results_decode_example.pdf"))
    fig.savefig(J(HERE, "results_decode_example_preview.png"), dpi=250)
    plt.close(fig)
    for kind in out:
        out[kind].pop("_rows")
    res["E11_results_decode_example"] = out


def main() -> int:
    t0 = time.time()
    for n in ("results_dot_cdf.pdf", "results_decode_example.pdf"):
        dst = J(HERE, n.replace(".pdf", "_previous.pdf"))
        if not os.path.exists(dst):
            shutil.copy2(J(REPORT_FIGS, n), dst)                     # the current PDFs, read-only copies for rollback
    res = {"label": "development evaluation, all data seen; inside A3's tenth and B2's eighth looks (no decode)",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "the shipped profile's replays, R0/ (clean_1s_r0)"}
    cdf_figure(res)
    decode_figure(res)
    res["seconds"] = round(time.time() - t0, 1)
    res["nice"] = os.nice(0)
    json.dump(res, open(J(HERE, "FIGURES.json"), "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
