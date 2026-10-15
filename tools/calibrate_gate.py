"""Calibrate the walking gate from this data: empty, standing and walking on one axis.

Offline, whole-file, clearly named. The gate statistic is the 0.3 to 2 Hz
band power of the cleaned window: FFT along time per subcarrier, band
energy summed, averaged over subcarriers and over the three links. Two
thresholds come out, and they are different kinds of thing:

* ``motion``: standing versus walking. One global number. Measured before
  this tool existed to transfer across participants and sessions.
* ``presence``: empty versus standing. NOT a global number. The empty room's
  resting level moves within a morning, so the threshold is a RULE applied
  to each session's own fresh baseline: a quantile of the baseline's window
  energies times a calibrated factor. The factor is what is calibrated here.

Calibrated on session 01. Session 02 is reported alongside as the transfer
check and is not used to place anything. Nothing is copied from WiWho.

Usage::

    python tools/calibrate_gate.py --windows runs/constrained/windows_s1.0_roomA --data data --out reports/audit

Writes ``gate_distributions.png`` and ``gate_calibration.json`` to ``--out``
and a PROPOSED ``configs/gate.yaml``. The values are a proposal for
Checkpoint 4; the operator places the final thresholds.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.io.clean import baseline_shape, clean_arrays  # noqa: E402
from pipeline.io.windows import FS, NODES, STRIDE_S, WINDOW_S, load_node, window_starts  # noqa: E402

BAND = (0.3, 2.0)


def band_energy(X: np.ndarray) -> np.ndarray:
    """0.3 to 2 Hz band power per window: (n, links, samples, sub) -> (n,)."""
    x = X.astype(np.float64)
    x = x - x.mean(axis=2, keepdims=True)
    f = np.fft.rfftfreq(X.shape[2], 1 / FS)
    P = (np.abs(np.fft.rfft(x, axis=2)) ** 2) / X.shape[2]
    band = (f >= BAND[0]) & (f <= BAND[1])
    return P[:, :, band, :].sum(axis=2).mean(axis=(1, 2))


def cut_baseline(bdir: str) -> np.ndarray:
    """Window an empty-room capture exactly as a recording is windowed, against its own shape."""
    nodes = {}
    for n in NODES:
        amp, ts, start, _ = load_node(os.path.join(bdir, f"{n}.bin"))
        nodes[n] = clean_arrays(amp, ts, FS, baseline=baseline_shape(amp), grid_origin=0.0, n_dropped_restart=start)
    starts = window_starts(nodes, WINDOW_S, STRIDE_S, FS)
    n_samp = int(round(WINDOW_S * FS))
    X = np.zeros((len(starts), len(NODES), n_samp, nodes[NODES[0]].amplitude.shape[1]), dtype=np.float32)
    for k, T in enumerate(starts):
        for j, n in enumerate(NODES):
            i0 = int(round((T - nodes[n].grid[0]) * FS))
            X[k, j] = nodes[n].amplitude[i0:i0 + n_samp]
    return X


def session_energies(windows_root: str, data_root: str, sid: str) -> dict:
    """Empty, standing and walking energies for one session, plus per-baseline empty energies."""
    standing, walking, per_file = [], [], {}
    for meta_path in sorted(glob.glob(os.path.join(windows_root, "room_A", f"session_{sid}", "*.meta.json"))):
        doc = json.load(open(meta_path))
        z = np.load(meta_path.replace(".meta.json", ".npz"))
        e = band_energy(z["X"])
        modes = np.array([w["mode"] for w in doc["windows"]])
        standing.append(e[modes == "grid"]); walking.append(e[modes == "walk"])
        per_file[doc["summary"]["stem"]] = {"standing": e[modes == "grid"].tolist(), "walking": e[modes == "walk"].tolist()}
    empty, per_baseline = [], {}
    for bdir in sorted(glob.glob(os.path.join(data_root, "room_A", f"session_{sid}", "2026*"))):
        if not all(os.path.exists(os.path.join(bdir, f"{n}.bin")) for n in NODES):
            continue
        e = band_energy(cut_baseline(bdir))
        empty.append(e); per_baseline[os.path.basename(bdir)] = e.tolist()
    return {"empty": np.concatenate(empty), "standing": np.concatenate(standing), "walking": np.concatenate(walking),
            "per_baseline": per_baseline, "per_file": per_file}


def best_split(lo: np.ndarray, hi: np.ndarray) -> tuple[float, float, float]:
    """Log-domain threshold maximising balanced accuracy; returns (theta, lo_above_pct, hi_below_pct)."""
    a, b = np.log10(lo), np.log10(hi)
    cands = np.linspace(min(a.min(), b.min()), max(a.max(), b.max()), 2000)
    bal = [(0.5 * ((a < c).mean() + (b >= c).mean()), c) for c in cands]
    _, c = max(bal)
    return float(10 ** c), float(100 * (a >= c).mean()), float(100 * (b < c).mean())


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--windows", default="runs/constrained/windows_s1.0_roomA")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="reports/audit")
    ap.add_argument("--config", default="configs/gate.yaml")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    S = {sid: session_energies(args.windows, args.data, sid) for sid in ("01", "02")}
    cal = S["01"]

    # Motion: one global threshold, placed on session 01, checked on 02.
    theta_m, stand_over, walk_under = best_split(cal["standing"], cal["walking"])
    m02_stand_over = 100 * (S["02"]["standing"] >= theta_m).mean()
    m02_walk_under = 100 * (S["02"]["walking"] < theta_m).mean()

    # Presence: a rule on each session's own baseline: theta = k * Q(empty windows of that session's baselines),
    # with BOTH the reference quantile Q and the factor k searched on session 01 by balanced accuracy, then
    # applied unchanged on session 02. Also the ceiling: the best any per-session threshold could do if it
    # were placed with that session's standing data in hand (an oracle, never deployable), so the reader can
    # tell a weak rule from a weak statistic.
    def balanced(sid, th):
        return 0.5 * ((S[sid]["empty"] < th).mean() + (S[sid]["standing"] >= th).mean())
    best = None
    for q in (0.5, 0.75, 0.9, 0.95, 0.99):
        ref01 = float(np.quantile(cal["empty"], q))
        for k in np.logspace(np.log10(0.3), np.log10(100), 600):
            b = balanced("01", k * ref01)
            if best is None or b > best[0]:
                best = (b, q, float(k))
    _, BASELINE_Q, k = best
    pres = {}
    for sid in ("01", "02"):
        th = k * float(np.quantile(S[sid]["empty"], BASELINE_Q))
        pres[sid] = {"theta": th, "empty_over_pct": 100 * (S[sid]["empty"] >= th).mean(), "standing_under_pct": 100 * (S[sid]["standing"] < th).mean(),
                     "balanced_acc_pct": 100 * balanced(sid, th)}
    fixed_on_02 = {"empty_over_pct": 100 * (S["02"]["empty"] >= pres["01"]["theta"]).mean(), "standing_under_pct": 100 * (S["02"]["standing"] < pres["01"]["theta"]).mean()}
    ceiling = {}
    for sid in ("01", "02"):
        th, e_over, s_under = best_split(S[sid]["empty"], S[sid]["standing"])
        ceiling[sid] = {"oracle_theta": th, "empty_over_pct": e_over, "standing_under_pct": s_under, "balanced_acc_pct": 100 * balanced(sid, th)}
    per_b = {sid: {b: float(np.median(v)) for b, v in S[sid]["per_baseline"].items()} for sid in S}
    np.savez(os.path.join(args.out, "gate_energies.npz"), **{f"{sid}_{c}": S[sid][c] for sid in S for c in ("empty", "standing", "walking")})

    # Figure: both sessions, three distributions each, on one log axis.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    allv = np.concatenate([S[s][c] for s in S for c in ("empty", "standing", "walking")])
    bins = np.logspace(np.log10(allv.min()), np.log10(allv.max()), 80)
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, sid in zip(axes, ("01", "02")):
        for cls, col in (("empty", "tab:grey"), ("standing", "tab:blue"), ("walking", "tab:orange")):
            v = S[sid][cls]
            ax.hist(v, bins=bins, alpha=0.55, color=col, label=f"{cls} (n={len(v)})", weights=np.full(len(v), 100.0 / len(v)))
        ax.axvline(theta_m, color="k", lw=2, label=f"motion theta {theta_m:.3g} (global)")
        ax.axvline(pres[sid]["theta"], color="tab:red", lw=2, ls="--", label=f"presence theta {pres[sid]['theta']:.3g} (= {k:.2f} x Q{int(BASELINE_Q*100)} of this session's baselines)")
        ax.set_xscale("log"); ax.set_ylabel("percent of that class's windows"); ax.grid(alpha=0.3)
        ax.set_title(f"session {sid}" + ("  (calibration)" if sid == "01" else "  (transfer check, nothing placed here)"))
        ax.legend(fontsize=9)
    axes[1].set_xlabel("0.3 to 2 Hz band power of the cleaned 2 s window, mean over subcarriers and links")
    fig.tight_layout()
    png = os.path.join(args.out, "gate_distributions.png")
    fig.savefig(png, dpi=130); plt.close(fig)

    result = {
        "statistic": "0.3-2 Hz band power, FFT along time per subcarrier, mean over subcarriers and links, 2 s window",
        "calibrated_on": "session 01 (dev train side)", "transfer_check": "session 02, not used to place anything",
        "motion": {"theta": theta_m, "session_01": {"standing_over_pct": stand_over, "walking_under_pct": walk_under},
                   "session_02": {"standing_over_pct": m02_stand_over, "walking_under_pct": m02_walk_under}},
        "presence": {"rule": f"theta = k * Q{int(BASELINE_Q*100)}(empty-window energies of the session's own baselines)", "k": k,
                     "baseline_quantile": BASELINE_Q, "sessions": pres, "session_01_absolute_applied_to_02": fixed_on_02,
                     "oracle_ceiling_per_session": ceiling, "per_baseline_median_empty": per_b},
        "counts": {sid: {c: int(len(S[sid][c])) for c in ("empty", "standing", "walking")} for sid in S},
        "medians": {sid: {c: float(np.median(S[sid][c])) for c in ("empty", "standing", "walking")} for sid in S},
        "figure": png, "status": "PROPOSED, awaiting Checkpoint 4",
    }
    with open(os.path.join(args.out, "gate_calibration.json"), "w") as f:
        json.dump(result, f, indent=1)
    if os.path.exists(args.config) and "status: accepted" in open(args.config, encoding="utf-8").read():
        args.config = args.config.replace(".yaml", ".proposed.yaml")
        print(f"  the accepted gate config is left alone; this proposal goes to {args.config}")
    with open(args.config, "w") as f:
        f.write("# Walking gate thresholds. PROPOSED by tools/calibrate_gate.py; the operator places the\n"
                "# final values at Checkpoint 4. Calibrated on session 01 only, from this data, never copied.\n"
                f"status: proposed\nstatistic: 0.3-2 Hz band power of the cleaned 2 s window, mean over subcarriers and links\n"
                f"band_hz: [0.3, 2.0]\nwindow_s: 2.0\n"
                f"motion:\n  theta: {theta_m:.6g}   # global: standing below, walking above\n"
                f"presence:\n  rule: k times the {int(BASELINE_Q*100)}th percentile of the session's own baseline window energies\n"
                f"  k: {k:.4f}\n  baseline_quantile: {BASELINE_Q}\n  never_a_global_constant: true\n"
                f"figure: {png}\ncalibration_file_lists: [splits/dev.txt]\n")

    print("=" * 96); print("CHECKPOINT 4: threshold placement (PROPOSED, nothing committed)"); print("=" * 96)
    for sid in S:
        m = result["medians"][sid]; c = result["counts"][sid]
        print(f"  session {sid}: empty n={c['empty']:4d} median {m['empty']:.3g}   standing n={c['standing']:4d} median {m['standing']:.3g}   walking n={c['walking']:4d} median {m['walking']:.3g}"
              f"   ratios walking/standing {m['walking']/m['standing']:.1f}x  standing/empty {m['standing']/m['empty']:.1f}x")
    print(f"\n  MOTION (global)  theta = {theta_m:.4g}")
    print(f"    session 01 (placed here): standing read as walking {stand_over:.1f} %   walking read as standing {walk_under:.1f} %")
    print(f"    session 02 (transfer):    standing read as walking {m02_stand_over:.1f} %   walking read as standing {m02_walk_under:.1f} %")
    print(f"\n  PRESENCE (rule)  theta = {k:.2f} x Q{int(BASELINE_Q*100)}(own baselines)   [quantile and factor both searched on session 01]")
    for sid in ("01", "02"):
        p = pres[sid]; c = ceiling[sid]
        print(f"    session {sid}: theta {p['theta']:.4g}   empty read as occupied {p['empty_over_pct']:.1f} %   standing read as empty {p['standing_under_pct']:.1f} %   balanced {p['balanced_acc_pct']:.1f} %")
        print(f"               oracle ceiling (threshold placed with this session's standing data, not deployable): empty {c['empty_over_pct']:.1f} %  standing {c['standing_under_pct']:.1f} %  balanced {c['balanced_acc_pct']:.1f} %")
    print(f"    session 01's absolute theta applied to 02 instead: empty read as occupied {fixed_on_02['empty_over_pct']:.1f} %   standing read as empty {fixed_on_02['standing_under_pct']:.1f} %")
    print("\n  per-baseline median empty energy (what moves within a morning):")
    for sid in ("01", "02"):
        print(f"    session {sid}: " + "  ".join(f"{b[9:11]}:{b[11:13]} {v:.2g}" for b, v in per_b[sid].items()))
    print(f"\n  figure {png}   json {os.path.join(args.out, 'gate_calibration.json')}   config {args.config} (status: proposed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
