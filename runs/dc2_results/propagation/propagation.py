"""A propagation investigation on the labelled walks (reports/BRIEF_PRESENCE_PROPAGATION_2026-10-01.md, item 2). A
measurement on existing recordings: nothing is adopted and no model, setting or figure changes.

    python3 runs/dc2_results/propagation/propagation.py collect   # per-block responses, every evaluated recording
    python3 runs/dc2_results/propagation/propagation.py analyse   # half-widths, Fresnel comparison, the RX1 check, figures

THE METHOD, fixed before any response was looked at:
- Recordings: the 30 evaluated walk recordings (A1, A2, A3, B1, B2; six each; calibration recordings left out), read
  only from data/. Geometry (every sidecar, both rooms): TX (2.5, -0.5), RX1 (2.5, 5.5), RX2 (-0.5, 2.5),
  RX3 (5.5, 2.5). Link k is TX to RXk; link 1 is 6.00 m long, links 2 and 3 are 4.24 m.
- Blocks: 0.1 s of packets (about 15; the walker moves about 0.13 m), inside each unflagged labelled pass, between its
  first and last anchor press. The walker's position is the pass's anchors interpolated linearly at the block's centre
  (the windows' own labelling, without the press-reaction offset).
- Two responses per block and link:
  - RSSI DIP: the recording's idle RSSI mean for that link minus the block's mean RSSI, in dB (positive = weaker).
    The idle mean is the app's own (`stats.rssi_idle_mean` of the recording's committed causal replay).
  - CSI-SHAPE CHANGE: the RMS difference between the block's shape and the empty-room baseline's shape, over the live
    subcarriers. A shape is `baseline_shape`'s: dead bins masked, each LTF half of each packet divided by its own mean,
    Hampel, then the median over packets; the baseline's is the shape the recording itself is cleaned against.
- Geometry per block and link: u, the position along the link (0 at TX, 1 at RX), and d, the perpendicular distance
  to the link's line. Only blocks with 0.05 <= u <= 0.95 (beside the link's span) are used.
- THE HALF-WIDTH of a response: the median response in 0.05 m bins of d; the peak is the median over d < 0.10 m, the
  floor the median over 1.5 <= d <= 2.5 m; the half-width is the first d (linear between bin centres, after a 3-bin
  running median) at which the binned median falls to floor + (peak - floor) / 2. Per link and room, over the
  mid-link blocks (0.3 <= u <= 0.7), and separately for u < 0.3 and u > 0.7. 95 % intervals: a bootstrap over passes,
  1000 draws, seed 0.
- THE FRESNEL COMPARISON: the first Fresnel zone's radius r1(u) = sqrt(lambda L u (1 - u)), lambda = c / 2.462 GHz =
  0.1218 m (channel 11): 0.427 m at mid-link on link 1, 0.359 m on links 2 and 3.
- THE RX1 BISTATIC CHECK (the identification work's finding: on line A, TX-RX1's projected bistatic factor F is 0 for
  the whole line, so a walker there changes that path's length not at all): per pass and link, the Doppler-band power
  of the cleaned amplitude (Welch PSD, 5 to 40 Hz, mean over subcarriers) relative to the same in the empty-room
  baseline, against the geometry's mean F over the line, F = |d(|p - TX| + |p - RX|)/ds| / 2.
"""

import csv
import glob
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
J = os.path.join
OUT = J(ROOT, "runs", "dc2_results", "propagation")
TX = np.array([2.5, -0.5])
RX = {"RX1": np.array([2.5, 5.5]), "RX2": np.array([-0.5, 2.5]), "RX3": np.array([5.5, 2.5])}
LAMBDA = 299792458.0 / 2.462e9
BLOCK_S = 0.1
SESSIONS = {"01": ("A", "room_A/session_01", "rotA1/semi_disp-K1g_causal"), "02": ("A", "room_A/session_02", "rotA2/semi_disp-K1g_causal"),
            "03": ("A", "room_A/session_03", "final/semi_disp-K1g_causal_realtime_screen"),
            "B1": ("B", "room_B/session_B1", "rotB1/semi_disp-K1g_causal"), "B2": ("B", "room_B/session_B2", "final/semi_disp-K1g_causal_realtime_screen")}
LABEL = {"01": "A1", "02": "A2", "03": "A3", "B1": "B1", "B2": "B2"}
DOPPLER = (5.0, 40.0)


def geometry(p, rx):
    v = rx - TX
    L = float(np.linalg.norm(v))
    u = float(np.dot(p - TX, v) / (L * L))
    d = float(abs(v[0] * (p - TX)[1] - v[1] * (p - TX)[0]) / L)
    return u, d, L


def fresnel(u, L):
    return float(np.sqrt(LAMBDA * L * u * (1 - u)))


def shapes(amp):
    """Per-packet shapes in baseline_shape's space (mask, per-half normalisation, Hampel), (n, n_live)."""
    from pipeline.io.clean import normalise_shape, remove_outliers, select_subcarriers
    return remove_outliers(normalise_shape(select_subcarriers(np.asarray(amp, np.float32), None), None))


def load(path):
    """Raw amplitude, anchored times, RSSI: load_node's own steps, with the RSSI kept."""
    from pipeline.io.windows import anchor_times, read_capture_file
    _h, fr = read_capture_file(path)
    ts, start = anchor_times(fr["local_timestamp"], fr["t_mono"])
    fr = fr[start:]
    amp = np.sqrt((fr["data"].astype(np.float32).reshape(len(fr), 128, 2) ** 2).sum(-1))
    return amp, np.asarray(ts, float), fr["rssi"].astype(float)


def mean_F(anchors, rx, step=0.05):
    """The line's mean projected bistatic factor, |d(path length)/ds| / 2, sampled every 5 cm along its anchors."""
    pts = np.asarray(anchors, float)
    F = []
    for a, b in zip(pts[:-1], pts[1:]):
        seg = b - a
        n = max(1, int(np.ceil(np.linalg.norm(seg) / step)))
        t_hat = seg / np.linalg.norm(seg)
        for k in range(n):
            p = a + seg * (k + 0.5) / n
            g = (p - TX) / np.linalg.norm(p - TX) + (p - rx) / np.linalg.norm(p - rx)
            F.append(abs(float(np.dot(g, t_hat))) / 2)
    return float(np.mean(F))


def doppler_power(x, fs=150.0):
    """Mean Welch PSD over the Doppler band, mean over subcarriers, of an (n, sub) cleaned amplitude segment."""
    from scipy.signal import welch
    x = np.asarray(x, float) - np.mean(x, axis=0, keepdims=True)
    f, P = welch(x, fs=fs, nperseg=min(256, len(x)), axis=0)
    sel = (f >= DOPPLER[0]) & (f <= DOPPLER[1])
    return float(P[sel].mean())


def collect():
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.io.clean import baseline_shape, clean_arrays
    from pipeline.io.windows import FS
    rows, dop = [], []
    for session, (room, rel, appdir) in SESSIONS.items():
        sd = J(ROOT, "data", rel)
        cal = set(json.load(open(J(ROOT, "data", "room_B", "calibration.json")))["sessions"].get(session, {}).get("calibration_recordings", []))
        for gt in sorted(glob.glob(J(sd, "participant_*_walk.gt.json"))):
            stem = os.path.basename(gt)[:-len(".gt.json")]
            if stem in cal or "_C_walk" in stem or "DEMO" in stem:
                continue
            sc = json.load(open(gt))
            stats = json.load(open(J(ROOT, "runs", "live", "replay", appdir, f"{session}__{stem}.summary.json")))["stats"]
            idle = dict(zip(["RX1", "RX2", "RX3"], stats["rssi_idle_mean"]))
            bdir = J(ROOT, sc["baseline_capture"].rstrip("/"))
            for n, rx in RX.items():
                amp, ts, rssi = load(J(sd, f"{stem}_{n}.bin"))
                bamp, bts, _br = load(J(bdir, f"{n}.bin"))
                bshape = baseline_shape(bamp)
                S = shapes(amp)
                # the cleaned series (for the Doppler band): the chain, against the baseline's shape, as the tree cuts it
                cn = clean_arrays(amp, ts, FS, baseline=bshape, grid_origin=0.0)
                cb = clean_arrays(bamp, bts, FS, baseline=bshape, grid_origin=0.0)
                nb = int(4 * FS)
                bp = float(np.median([doppler_power(cb.amplitude[i:i + nb]) for i in range(0, len(cb.amplitude) - nb, nb)]))
                for p in sc["passes"]:
                    if p.get("flagged"):
                        continue
                    at, ac = np.asarray(p["anchor_times"], float), np.asarray(p["anchor_coords"], float)
                    t = at[0]
                    while t + BLOCK_S <= at[-1] + 1e-9:
                        sel = (ts >= t) & (ts < t + BLOCK_S)
                        if sel.sum() >= 5:
                            tc = t + BLOCK_S / 2
                            pos = np.array([np.interp(tc, at, ac[:, 0]), np.interp(tc, at, ac[:, 1])])
                            u, d, L = geometry(pos, rx)
                            rows.append([session, room, stem, int(p["pass_id"]), p["path_name"], n, round(tc, 4), round(pos[0], 4), round(pos[1], 4),
                                         round(u, 5), round(d, 5), round(idle[n] - float(rssi[sel].mean()), 4),
                                         round(float(np.sqrt(np.mean((np.median(S[sel], axis=0) - bshape) ** 2))), 6)])
                        t += BLOCK_S
                    g = (cn.grid >= at[0]) & (cn.grid <= at[-1])
                    if g.sum() >= 64:
                        dop.append([session, room, stem, int(p["pass_id"]), p["path_name"], n, mean_F(ac, rx),
                                    doppler_power(cn.amplitude[g]) / bp])
            print(session, stem, len(rows), flush=True)
    with open(J(OUT, "blocks.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["session", "room", "stem", "pass_id", "line", "link", "t", "x", "y", "u", "d", "rssi_dip_db", "shape_change"])
        w.writerows(rows)
    with open(J(OUT, "doppler_passes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["session", "room", "stem", "pass_id", "line", "link", "mean_F", "doppler_power_vs_empty"])
        w.writerows(dop)


BINS = np.arange(0.0, 3.0001, 0.05)


def binned(d, r):
    idx = np.digitize(d, BINS) - 1
    med = np.full(len(BINS) - 1, np.nan)
    for i in range(len(BINS) - 1):
        m = idx == i
        if m.sum() >= 5:
            med[i] = np.median(r[m])
    return med


def half_width(d, r):
    """The half-width as the method fixes it; None when the curve never falls to half way."""
    if (d < 0.10).sum() < 5 or ((d >= 1.5) & (d <= 2.5)).sum() < 5:
        return None, None, None
    peak = float(np.median(r[d < 0.10]))
    floor = float(np.median(r[(d >= 1.5) & (d <= 2.5)]))
    med = binned(d, r)
    sm = med.copy()
    for i in range(1, len(med) - 1):                     # a 3-bin running median
        w = med[i - 1:i + 2]
        sm[i] = np.nanmedian(w) if np.isfinite(w).any() else np.nan
    centres = 0.5 * (BINS[1:] + BINS[:-1])
    half = floor + 0.5 * (peak - floor)
    if peak <= floor:
        return None, peak, floor
    for i in range(1, len(sm)):
        if np.isfinite(sm[i]) and np.isfinite(sm[i - 1]) and sm[i - 1] > half >= sm[i]:
            x0, x1, y0, y1 = centres[i - 1], centres[i], sm[i - 1], sm[i]
            return float(x0 + (half - y0) * (x1 - x0) / (y1 - y0)), peak, floor
    return None, peak, floor


def analyse():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader(open(J(OUT, "blocks.csv"))))
    A = {k: np.array([r[k] for r in rows]) for k in ("session", "room", "stem", "pass_id", "line", "link")}
    N = {k: np.array([float(r[k]) for r in rows]) for k in ("u", "d", "rssi_dip_db", "shape_change")}
    passkey = np.char.add(np.char.add(A["session"], "|"), np.char.add(np.char.add(A["stem"], "|"), A["pass_id"]))
    res = {"lambda_m": LAMBDA, "n_blocks": len(rows), "half_widths": {}, "fresnel_m": {}, "rx1_bistatic": {}}
    segs = {"mid (0.3 to 0.7)": (0.3, 0.7), "TX end (0.05 to 0.3)": (0.05, 0.3), "RX end (0.7 to 0.95)": (0.7, 0.95)}
    rng = np.random.default_rng(0)
    for room in ("A", "B"):
        for link in ("RX1", "RX2", "RX3"):
            L = float(np.linalg.norm(RX[link] - TX))
            for sname, (lo, hi) in segs.items():
                base = (A["room"] == room) & (A["link"] == link) & (N["u"] >= lo) & (N["u"] <= hi)
                fr = fresnel(0.5 * (lo + hi), L)
                for meas in ("rssi_dip_db", "shape_change"):
                    hw, pk, fl = half_width(N["d"][base], N[meas][base])
                    keys = np.unique(passkey[base])
                    idx = {k: np.flatnonzero(base & (passkey == k)) for k in keys}
                    boots = []
                    for _ in range(1000):
                        pick = rng.choice(keys, size=len(keys), replace=True)
                        ii = np.concatenate([idx[k] for k in pick])
                        b, _p, _f = half_width(N["d"][ii], N[meas][ii])
                        if b is not None:
                            boots.append(b)
                    res["half_widths"][f"{room}|{link}|{sname}|{meas}"] = {
                        "half_width_m": hw, "ci95": ([float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if len(boots) >= 100 else None),
                        "boot_defined": len(boots), "peak": pk, "floor": fl, "fresnel_r1_m_at_segment_centre": fr,
                        "n_blocks": int(base.sum()), "n_passes": int(len(keys))}
            res["fresnel_m"][link] = {"mid": fresnel(0.5, L), "u0.175": fresnel(0.175, L), "u0.825": fresnel(0.825, L), "length_m": L}
    # the RX1 bistatic check
    D = list(csv.DictReader(open(J(OUT, "doppler_passes.csv"))))
    for room in ("A", "B"):
        cells = {}
        for r in D:
            if r["room"] != room:
                continue
            fam = r["line"].split("_")[0]
            cells.setdefault((r["link"], fam), []).append((float(r["mean_F"]), float(r["doppler_power_vs_empty"])))
        tab = {f"{k[0]}|{k[1]}": {"mean_F": float(np.mean([a for a, _ in v])), "doppler_ratio_median": float(np.median([b for _, b in v])),
                                  "n_passes": len(v)} for k, v in sorted(cells.items())}
        from scipy.stats import spearmanr
        xs = [v["mean_F"] for v in tab.values()]
        ys = [np.log10(v["doppler_ratio_median"]) for v in tab.values()]
        rho = spearmanr(xs, ys)
        res["rx1_bistatic"][room] = {"by_link_and_line_family": tab, "spearman_F_vs_log_doppler": float(rho.correlation), "p": float(rho.pvalue)}
    # RSSI dip on line A per link, for the shadowing side of the same check
    for room in ("A", "B"):
        out = {}
        for link in ("RX1", "RX2", "RX3"):
            m = (A["room"] == room) & (A["link"] == link) & np.isin(A["line"], ["A_fwd", "A_rev"]) & (N["u"] >= 0.05) & (N["u"] <= 0.95)
            out[link] = {"rssi_dip_db_median": float(np.median(N["rssi_dip_db"][m])), "shape_change_median": float(np.median(N["shape_change"][m])),
                         "d_median_m": float(np.median(N["d"][m])), "n_blocks": int(m.sum())}
        res["rx1_bistatic"][room]["line_A_blocks"] = out
    json.dump(res, open(J(OUT, "PROPAGATION.json"), "w"), indent=1)
    # figures: response against perpendicular distance, mid-link, per link and room, with the Fresnel radius
    centres = 0.5 * (BINS[1:] + BINS[:-1])
    for meas, ylab in (("rssi_dip_db", "RSSI dip below the idle mean (dB)"), ("shape_change", "CSI-shape change from the empty room (RMS)")):
        fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
        for ax, link in zip(axs, ("RX1", "RX2", "RX3")):
            L = float(np.linalg.norm(RX[link] - TX))
            for room, col in (("A", "#4c72b0"), ("B", "#dd8452")):
                m = (A["room"] == room) & (A["link"] == link) & (N["u"] >= 0.3) & (N["u"] <= 0.7)
                med = binned(N["d"][m], N[meas][m])
                ax.plot(centres, med, color=col, label=f"Room {room}")
                hw = res["half_widths"][f"{room}|{link}|mid (0.3 to 0.7)|{meas}"]["half_width_m"]
                if hw:
                    ax.axvline(hw, color=col, ls=":", lw=1)
            ax.axvline(fresnel(0.5, L), color="k", ls="--", lw=1, label=f"first Fresnel radius, mid-link {fresnel(0.5, L):.2f} m")
            ax.set_title(f"TX-{link}, mid-link blocks (u 0.3 to 0.7)")
            ax.set_xlabel("perpendicular distance from the link's line (m)")
            ax.set_xlim(0, 3)
            ax.legend(fontsize=7)
        axs[0].set_ylabel(ylab)
        fig.tight_layout()
        fig.savefig(J(OUT, f"falloff_{meas}.png"), dpi=130)
        plt.close(fig)
    # figure: response along the link, on the link (d < 0.15 m)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    ub = np.arange(0.05, 0.9501, 0.05)
    for ax, (meas, ylab) in zip(axs, (("rssi_dip_db", "RSSI dip (dB)"), ("shape_change", "CSI-shape change (RMS)"))):
        for link, ls in (("RX1", "-"), ("RX2", "--"), ("RX3", ":")):
            for room, col in (("A", "#4c72b0"), ("B", "#dd8452")):
                m = (A["room"] == room) & (A["link"] == link) & (N["d"] < 0.15)
                ix = np.digitize(N["u"][m], ub) - 1
                y = [np.median(N[meas][m][ix == i]) if (ix == i).sum() >= 5 else np.nan for i in range(len(ub) - 1)]
                ax.plot(0.5 * (ub[1:] + ub[:-1]), y, ls=ls, color=col, label=f"TX-{link}, Room {room}")
        ax.set_xlabel("position along the link, u (0 at TX, 1 at RX)")
        ax.set_ylabel(ylab + ", walker within 0.15 m of the line")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(J(OUT, "along_link.png"), dpi=130)
    plt.close(fig)
    # figure: the Doppler band against F
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for room, mk in (("A", "o"), ("B", "s")):
        for k, v in res["rx1_bistatic"][room]["by_link_and_line_family"].items():
            link, fam = k.split("|")
            c = {"RX1": "#c44e52", "RX2": "#4c72b0", "RX3": "#55a868"}[link]
            ax.scatter(v["mean_F"], v["doppler_ratio_median"], marker=mk, color=c)
            if fam == "A":
                ax.annotate(f"{link} line A ({room})", (v["mean_F"], v["doppler_ratio_median"]), fontsize=7)
    ax.set_yscale("log")
    ax.set_xlabel("mean projected bistatic factor F over the line")
    ax.set_ylabel("Doppler-band (5 to 40 Hz) power / empty room")
    ax.set_title("Doppler band against geometry (red RX1, blue RX2, green RX3; o Room A, s Room B)", fontsize=8)
    fig.tight_layout()
    fig.savefig(J(OUT, "doppler_vs_F.png"), dpi=130)
    plt.close(fig)
    for k, v in res["half_widths"].items():
        if "mid" in k:
            print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "ci95"}, v["ci95"])
    for room in ("A", "B"):
        print(room, "spearman", round(res["rx1_bistatic"][room]["spearman_F_vs_log_doppler"], 3), res["rx1_bistatic"][room]["line_A_blocks"])
        for k, v in res["rx1_bistatic"][room]["by_link_and_line_family"].items():
            print("  ", k, round(v["mean_F"], 3), round(v["doppler_ratio_median"], 2), v["n_passes"])


def crossing_of(line_name, link):
    """Where a taped line crosses a link's segment (u in (0, 1)), from the line's own anchors; None if it does not."""
    from pipeline.constrained.paths import load_paths
    cwd = os.getcwd()
    try:
        os.chdir(ROOT)
        pts = np.asarray(load_paths()[line_name], float)
    finally:
        os.chdir(cwd)
    a, b = pts[0], pts[-1]
    r = RX[link] - TX
    s_ = b - a
    den = r[0] * s_[1] - r[1] * s_[0]
    if abs(den) < 1e-12:
        return None                                       # parallel
    w = a - TX
    u = (w[0] * s_[1] - w[1] * s_[0]) / den
    v = (w[0] * r[1] - w[1] * r[0]) / den
    return float(u) if (0.0 < u < 1.0 and -1e-9 <= v <= 1 + 1e-9) else None


def crossings():
    """POST HOC (chosen after the pre-fixed analysis, labelled as such in the report). Only passes that CROSS a link,
    each block's response taken relative to its own pass's far level (the median over 1.0 <= d <= 2.5 m in that pass),
    so a recording's idle reference and pass-to-pass offsets drop out; per (room, link, crossing line): the half-width
    as fixed before (peak d < 0.10 m, floor 0 by construction, half way), against r1 at that crossing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader(open(J(OUT, "blocks.csv"))))
    res = {}
    rng = np.random.default_rng(0)
    lines = sorted({r["line"] for r in rows})
    cross = {(ln, k): crossing_of(ln, k) for ln in lines for k in RX}
    data = {}
    for r in rows:
        uc = cross[(r["line"], r["link"])]
        if uc is None:
            continue
        key = (r["room"], r["link"], r["line"].split("_")[0], round(uc, 3))
        pk = (r["session"], r["stem"], r["pass_id"])
        data.setdefault(key, {}).setdefault(pk, []).append((float(r["d"]), float(r["rssi_dip_db"]), float(r["shape_change"])))
    def hw_from(passes, j):
        d_all, y_all = [], []
        for blocks in passes:
            b = np.asarray(blocks)
            far = b[(b[:, 0] >= 1.0) & (b[:, 0] <= 2.5), j]
            if len(far) < 5 or (b[:, 0] < 0.10).sum() < 1:
                continue
            d_all.append(b[:, 0]); y_all.append(b[:, j] - np.median(far))
        if not d_all:
            return None, None, None, 0
        d, y = np.concatenate(d_all), np.concatenate(y_all)
        if (d < 0.10).sum() < 5:
            return None, None, None, len(d_all)
        peak = float(np.median(y[d < 0.10]))
        med = binned(d, y)
        sm = med.copy()
        for i in range(1, len(med) - 1):
            w = med[i - 1:i + 2]
            sm[i] = np.nanmedian(w) if np.isfinite(w).any() else np.nan
        c = 0.5 * (BINS[1:] + BINS[:-1])
        if peak <= 0:
            return None, peak, (c, med), len(d_all)
        half = 0.5 * peak
        for i in range(1, len(sm)):
            if np.isfinite(sm[i]) and np.isfinite(sm[i - 1]) and sm[i - 1] > half >= sm[i]:
                return float(c[i - 1] + (half - sm[i - 1]) * (c[i] - c[i - 1]) / (sm[i] - sm[i - 1])), peak, (c, med), len(d_all)
        return None, peak, (c, med), len(d_all)
    curves = {}
    for key, by_pass in sorted(data.items()):
        room, link, fam, uc = key
        L = float(np.linalg.norm(RX[link] - TX))
        passes = list(by_pass.values())
        for j, meas in ((1, "rssi_dip_db"), (2, "shape_change")):
            hw, pk, curve, n = hw_from(passes, j)
            boots = []
            for _ in range(1000):
                pick = [passes[i] for i in rng.integers(0, len(passes), len(passes))]
                b, _p, _c, _n = hw_from(pick, j)
                if b is not None:
                    boots.append(b)
            res[f"{room}|{link}|{fam}|u={uc}|{meas}"] = {
                "half_width_m": hw, "ci95": ([float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if len(boots) >= 100 else None),
                "boot_defined": len(boots), "peak_above_far": pk, "fresnel_r1_m": fresnel(uc, L), "crossing_u": uc, "n_passes": n}
            if curve is not None:
                curves[(room, link, fam, uc, meas)] = curve
    out = json.load(open(J(OUT, "PROPAGATION.json")))
    out["post_hoc_crossings"] = res
    json.dump(out, open(J(OUT, "PROPAGATION.json"), "w"), indent=1)
    for meas, ylab in (("rssi_dip_db", "RSSI dip relative to the pass's far level (dB)"), ("shape_change", "CSI-shape change relative to the pass's far level")):
        fig, axs = plt.subplots(2, 3, figsize=(14, 7), sharex=True)
        for col, link in enumerate(("RX1", "RX2", "RX3")):
            for row, room in enumerate(("A", "B")):
                ax = axs[row, col]
                for (rm, lk, fam, uc, ms), (c, med) in curves.items():
                    if rm == room and lk == link and ms == meas:
                        L = float(np.linalg.norm(RX[link] - TX))
                        h, = ax.plot(c, med, label=f"line {fam}, crossing u {uc:.2f} (r1 {fresnel(uc, L):.2f} m)")
                        ax.axvline(fresnel(uc, L), color=h.get_color(), ls="--", lw=0.8)
                ax.axhline(0, color="k", lw=0.5)
                ax.set_xlim(0, 2.5)
                ax.set_title(f"TX-{link}, Room {room}: crossing passes", fontsize=9)
                ax.legend(fontsize=6)
                if col == 0:
                    ax.set_ylabel(ylab, fontsize=8)
                if row == 1:
                    ax.set_xlabel("perpendicular distance from the link's line (m)")
        fig.suptitle("Crossing passes only, each pass relative to its own far level (POST HOC); dashed: first Fresnel radius at the crossing", fontsize=10)
        fig.tight_layout()
        fig.savefig(J(OUT, f"crossings_{meas}.png"), dpi=120)
        plt.close(fig)
    for k, v in res.items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "ci95"}, None if v["ci95"] is None else [round(x, 3) for x in v["ci95"]])


if __name__ == "__main__":
    {"collect": collect, "analyse": analyse, "crossings": crossings}[sys.argv[1]]()
