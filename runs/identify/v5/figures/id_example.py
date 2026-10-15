"""The thesis's example of identification's signal (Editor Main's figure request, Uzayr's go in Agent1's chat, 13 Oct):
one natural identification walk of B1 (a training session, not a test session) after the engine's own conditioning.
Read-only on code and data: nothing under pipeline/ changes, no model is loaded, and the walker is named only by PA code.

The walk: every natural walk of B1, its window at t0 (T = 4.0 s) extracted by the engine's own `Extractor` (frames pushed to
the walk's cap, as the replay does), and the clearest step rhythm chosen by the signal alone: among the walks whose RX2
step-band autocorrelation peaks at the step rate the resolver chose (`cadence_estimates`' acf_cycle within 0.1 Hz of
`cad|all|-|-|cadence_hz`; on many walks it peaks at the stride, two steps, instead), the largest share of cadence estimates
agreeing (`cad|all|-|-|agree_frac`), then the highest autocorrelation peak. No label, decision or accuracy is read.

(a) RX2's 4 to 70 Hz Doppler map exactly as the CNNs receive it: the extraction's `maps[1]`, checked bit for bit against
`idz_bank.conditioned_map_v2` on the window's interpolated RX2 amplitude; its 28 frequency bins are `idv2_core.F_BINS` and
its frame times are those of that call's own STFT. Over it, the torso's 50th-percentile energy contour from
`id29_dc2_score.torso_hz` on the same RX2 window: the contour and its times are the values that call's own
`conditioning.energy_percentile_contour` and STFT return (recorded, not recomputed).
(b) RX2's step-band (0.8 to 3.5 Hz) mean over the window (`idmax_features.reduce_link(.., "b08_35", "mean")`, the channel
the cadence resolver reads) and its autocorrelation (`idmax_features._acf`), with the step period the resolver chose for
the window (1 / `cad|all|-|-|cadence_hz`, engine v3's resolver, from the extraction's own features).

The bottom row (Uzayr's gait-expansion prompt, 14 Oct; the top row is kept as `id_example_toprow.pdf`) reads the engine's
own feature calls for this window: `engine.extract_window`'s `id19_featbank.pass_features` (the window path; the bank's
`idz_bank.pass_features_cf` is its long-stream twin), recorded with `Capture` while the extraction runs, inputs included:
(c) RX2's step-band mean's cycle template (`idmax_features.cycle_templates(x, c, method="acf")`, the call whose output is the
extraction's `tplacf|mean@b08_35|RX2|0|*`): its K strides of 2 f_s / c samples, each resampled to 32 phases, aligned with the
first, rotated by the template's own shift and z-normalised (grey), and the template (black), asserted equal to the
extraction's tpl_00 to tpl_31 to 1e-9.
(d) RX2's Doppler contours (`idmax_features.doppler_features(P[1:], win_s=0.2)`, components 2 to 6 of the 4 to 70 Hz band,
the call whose output is the extraction's `dop|pca-pc1@w0.2|RX2|-|*`): f25, f50, f75 and f95 over the window's median f50,
the ratios leg_torso, q25_torso and q75_torso from the plotted contours asserted equal to the extraction's.

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. nice -n 10 python3 runs/identify/v5/figures/id_example.py

Development evaluation, all data seen; a figure of training data, no figure of merit.
"""

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.join("runs", "identify", "v5", "figures")
PDF = os.path.join(HERE, "id_example.pdf")
TOPROW = os.path.join(HERE, "id_example_toprow.pdf")
PNG = os.path.join(HERE, "id_example_preview.png")
OUT = os.path.join(HERE, "id_example.json")
W_CM, TOP_CM, BOT_CM = 15.92, 4.8, 4.0
H_CM = TOP_CM + BOT_CM


def walks():
    """Every natural walk of B1: (PA code, its natural recording (1 or 2), walk number in that recording, extraction,
    interpolated window, t0, feature names)."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.identify.iv5_report import PA
    from pipeline.io.capture_logger import read_capture_file
    man = json.load(open(os.path.join(EN.ENG, "models", "deploy_all5_v5", "manifest.json")))     # its alpha only
    names = json.load(open(EN.DEV_NAMES))
    dmode = RP.direction_mode()
    nrec = {}
    for rec in RP.session_recordings("B1"):
        if rec["kind"] != "idcap" or rec["block"] != "natural":
            continue
        pa = PA[rec["name"]]
        nrec[pa] = nrec.get(pa, 0) + 1
        ex = EN.Extractor(EN.T_S, IT.gs_adopted(), "id_spot", names, man["alpha"])
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        pos = {L: 0 for L in EN.LINKS}
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        presses = sorted((float(q["t_start"]), q.get("path_name")) for q in gt["passes"])          # only these two fields
        del gt
        for k, (t0, path) in enumerate(presses):
            lim = t0 + EN.T_S + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            ex.press(t0, path=None if dmode == "detected" else path, layout="id_spot")
            got = ex.poll(lim)
            assert len(got) == 1
            w, td, x = got[0]
            A = ex._raw(t0, ex._end(w), td)
            yield pa, nrec[pa], k + 1, x, A, t0, names


class Capture:
    """Records what a module function returns (and, in `calls`, what it was given) while a call runs, without changing it."""

    def __init__(self, module, attr):
        self.m, self.a, self.out, self.calls = module, attr, [], []

    def __enter__(self):
        f = self.orig = getattr(self.m, self.a)

        def w(*a, **k):
            r = f(*a, **k)
            self.out.append(r)
            self.calls.append((a, k, r))
            return r
        setattr(self.m, self.a, w)
        return self

    def __exit__(self, *e):
        setattr(self.m, self.a, self.orig)
        return False


def _same(r: dict, want: dict) -> bool:
    """A call's output equals the extraction's entries exactly (NaN equal to NaN)."""
    if set(r) != set(want):
        return False
    return all((v == want[q]) or (np.isnan(v) and np.isnan(want[q])) for q, v in r.items())


def _strides(x, c, fs, phases):
    """`idmax_features.cycle_templates`' acf branch on its own input, keeping what it averages: the K strides (resampled,
    aligned with the first, rotated by the template's shift, z-normalised), the template and the stride length."""
    x = np.asarray(x, float)
    stride = int(round(2.0 * fs / c))
    segs = [x[s:s + stride] for s in range(0, len(x) - stride + 1, stride)]
    if len(segs) < 2:
        return stride, len(segs), None, None, None
    P = np.vstack([np.interp(np.linspace(0, 1, phases, endpoint=False), np.linspace(0, 1, len(s), endpoint=False), s)
                   for s in segs])
    ref = P[0] - P[0].mean()
    A = []
    for cyc in P:
        c0 = cyc - cyc.mean()
        xc = np.real(np.fft.ifft(np.fft.fft(c0) * np.conj(np.fft.fft(ref))))
        A.append(np.roll(cyc, -int(np.argmax(xc))))
    A = np.asarray(A)
    m = A.mean(axis=0)
    shift = int(np.argmax(m))
    m = np.roll(m, -shift)
    sd = np.std(m)
    tpl = (m - m.mean()) / sd if sd > 0 else m * 0
    Ar = np.roll(A, -shift, axis=1)
    Az = (Ar - Ar.mean(axis=1, keepdims=True)) / np.maximum(Ar.std(axis=1, keepdims=True), 1e-12)
    return stride, len(segs), Az, tpl, shift


def _contours(x, fs, win_s):
    """`idmax_features.doppler_features`' contours on its own input: frame times, f_q per kept frame, the median f50."""
    import scipy.signal as SS
    x = np.atleast_2d(np.asarray(x, float))
    n = int(round(win_s * fs))
    f, t, Z = SS.stft(x, fs=fs, nperseg=n, noverlap=int(0.75 * n), axis=-1, nfft=max(n, 64))
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 0.95 * fs / 2)
    f, mag = f[keep], mag[:, keep]
    P = mag ** 2
    cs = np.cumsum(P, axis=1)
    tot = cs[:, -1:]
    ok = tot[:, 0] > 0
    cn = cs[ok] / tot[ok]
    cont = {q: f[np.clip(np.argmax(cn >= q / 100.0, axis=1), 0, len(f) - 1)] for q in (25, 50, 75, 95)}
    return t[ok], cont, max(float(np.median(cont[50])), 1e-6)


def main():
    import scipy.signal as SS
    from pipeline.identify import conditioning as CO
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import idmax_features as F
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idz_bank as ZB
    t_all = time.time()
    best, n = None, 0
    n_at_step = 0
    # the engine's own feature calls, recorded per walk while its extraction runs (inputs and outputs; nothing changed)
    with Capture(FB, "pass_features") as cpf, Capture(F, "cycle_templates") as ctp, Capture(F, "doppler_features") as cdf:
        for pa, nr, k, x, A, t0, names in walks():
            rec = (list(cpf.out), list(ctp.calls), list(cdf.calls))
            for lst in (cpf.out, cpf.calls, ctp.out, ctp.calls, cdf.out, cdf.calls):
                del lst[:]
            n += 1
            fv = dict(zip(names, x["features"].astype(float)))
            agree, cad_w = fv.get("cad|all|-|-|agree_frac", np.nan), fv.get("cad|all|-|-|cadence_hz", np.nan)
            est = F.cadence_estimates(F.reduce_link(A[1], "b08_35", "mean")[0])
            peak, cyc = est.get("acf_peak") or np.nan, est.get("acf_cycle") or np.nan
            if not (np.isfinite(cad_w) and np.isfinite(cyc) and abs(cyc - cad_w) <= 0.1):
                continue
            n_at_step += 1
            key = (np.nan_to_num(agree, nan=-1.0), np.nan_to_num(peak, nan=-1.0))
            if best is None or key > best[0]:
                best = (key, pa, nr, k, x, A, t0, fv, rec)
    (agree, peak), pa, nr, k, x, A, t0, fv, rec = best
    assert len(rec[0]) == 1, f"{len(rec[0])} pass_features calls recorded for the chosen walk"
    feats = rec[0][0]                                       # the extraction's features before their float32 store
    cad = fv["cad|all|-|-|cadence_hz"]
    period = 1.0 / cad
    # (a) the map as the CNNs receive it, its frame times from its own STFT; the torso contour from torso_hz's own calls
    with Capture(SS, "stft") as st:
        m = ZB.conditioned_map_v2(A[1])
    assert np.array_equal(m, x["maps"][1]), "the map differs from the extraction's"
    t_map = st.out[-1][1]
    with Capture(SS, "stft") as st2, Capture(CO, "energy_percentile_contour") as ec:
        f_t = D.torso_hz(A[1])
    t_tor, contour = st2.out[-1][1], np.asarray(ec.out[-1], float)
    # (b) the step-band mean and its autocorrelation
    s = F.reduce_link(A[1], "b08_35", "mean")[0]
    r = F._acf(s)
    t_s = np.arange(len(s)) / F.FS
    lag = np.arange(len(r)) / F.FS
    j = int(round(period * F.FS))
    # (c) the cycle template: the recorded cycle_templates call whose output is the extraction's RX2 mean@b08_35 template
    pre_t = "tplacf|mean@b08_35|RX2|0|"
    want_t = {q[len(pre_t):]: v for q, v in feats.items() if q.startswith(pre_t)}
    hits_t = [a_ for a_, k_, r_ in rec[1] if k_.get("method", "acf") == "acf" and _same(r_, want_t)]
    assert hits_t, "no recorded cycle_templates call returns the extraction's template"
    assert all(np.array_equal(h[0], hits_t[0][0]) and h[1] == hits_t[0][1] for h in hits_t), "matching calls differ"
    x_t, c_t = np.asarray(hits_t[0][0], float), float(hits_t[0][1])
    assert c_t == feats["cad|all|-|-|cadence_hz"], (c_t, feats["cad|all|-|-|cadence_hz"])
    stride, K, Az, tpl, shift = _strides(x_t, c_t, F.FS, F.PHASE)
    if K < 2:
        raise SystemExit(f"STOP: K = {K} strides (< 2): no template to draw")
    tpl_ext = np.array([want_t[f"tpl_{i:02d}"] for i in range(F.PHASE)])
    d_t64 = float(np.max(np.abs(tpl - tpl_ext)))
    assert d_t64 <= 1e-9, f"the plotted template differs from the extraction's by {d_t64}"
    tpl_f32 = np.array([x["features"][names.index(pre_t + f"tpl_{i:02d}")] for i in range(F.PHASE)], float)
    d_t32 = float(np.max(np.abs(tpl - tpl_f32)))
    # (d) the contours: the recorded doppler_features call whose output is the extraction's RX2 pca-pc1@w0.2 features
    pre_d = "dop|pca-pc1@w0.2|RX2|-|"
    want_d = {q[len(pre_d):]: v for q, v in feats.items() if q.startswith(pre_d)}
    hits_d = [a_ for a_, k_, r_ in rec[2] if k_.get("win_s") == 0.2 and np.atleast_2d(a_[0]).shape[0] == 5
              and _same(r_, want_d)]
    assert hits_d, "no recorded doppler_features call returns the extraction's RX2 pca-pc1@w0.2 features"
    assert all(np.array_equal(h[0], hits_d[0][0]) for h in hits_d), "matching calls differ"
    t_c, cont, med50 = _contours(hits_d[0][0], F.FS, 0.2)
    ratios = {"leg_torso": float(np.median(cont[95]) / med50), "q25_torso": float(np.median(cont[25]) / med50),
              "q75_torso": float(np.median(cont[75]) / med50)}
    d_r = {q: abs(v - want_d[q]) for q, v in ratios.items()}
    assert all(v <= 1e-12 for v in d_r.values()), f"the plotted contours' ratios differ from the extraction's: {d_r}"

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8,
                         "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "pdf.fonttype": 42, "axes.linewidth": 0.6,
                         "xtick.major.width": 0.6, "ytick.major.width": 0.6})
    fig = plt.figure(figsize=(W_CM / 2.54, H_CM / 2.54))
    # the top row keeps its 4.8 cm layout (the same axes in cm); the bottom row is 4.0 cm below it
    y0, hh = (BOT_CM + 0.215 * TOP_CM) / H_CM, 0.69 * TOP_CM / H_CM
    ax = fig.add_axes([0.068, y0, 0.37, hh])
    bx = fig.add_axes([0.525, y0, 0.235, hh])
    cx = fig.add_axes([0.845, y0, 0.145, hh])
    yb, hb = 0.95 / H_CM, 2.6 / H_CM
    dx = fig.add_axes([0.068, yb, 0.37, hb])
    ex = fig.add_axes([0.525, yb, 0.42, hb])
    fb = C.F_BINS
    df = float(fb[1] - fb[0])
    dt = float(t_map[1] - t_map[0])
    ax.imshow(m, origin="lower", aspect="auto", cmap="gray_r", interpolation="nearest",
              extent=[t_map[0] - dt / 2, t_map[-1] + dt / 2, fb[0] - df / 2, fb[-1] + df / 2])
    ok = np.isfinite(contour)
    ax.plot(t_tor[ok], contour[ok], color="white", lw=1.1, path_effects=[pe.Stroke(linewidth=2.3, foreground="black"),
                                                                           pe.Normal()])
    ax.set_xlim(0, 4.0)
    ax.set_ylim(fb[0] - df / 2, fb[-1] + df / 2)
    ax.set_xlabel("time after the press (s)")
    ax.set_ylabel("Doppler frequency (Hz)")
    bx.plot(t_s, s, color="black", lw=0.7)
    bx.set_xlim(0, 4.0)
    bx.set_xlabel("time after the press (s)")
    bx.set_ylabel("step-band mean (a.u.)")
    bx.set_yticks([])
    kk = lag <= 2.2
    cx.plot(lag[kk], r[kk], color="black", lw=0.7)
    cx.axhline(0, color="0.6", lw=0.5)
    cx.axvline(period, color="black", lw=0.7, ls="--")
    cx.plot([period], [r[j]], "o", ms=3, mfc="white", mec="black", mew=0.7)
    cx.set_xlim(0, 2.2)
    cx.set_xlabel("lag (s)")
    cx.set_ylabel("autocorrelation")
    cx.text(period + 0.05, 0.93, f"{period:.2f} s", fontsize=7.5, va="top", transform=cx.get_xaxis_transform())
    # (c) the K aligned strides (grey) and the template (black), one stride from phase 0 to 1 (phase 1 is phase 0 again)
    ph = np.arange(F.PHASE + 1) / F.PHASE
    for row in Az:
        dx.plot(ph, np.append(row, row[0]), color="0.62", lw=0.5)
    dx.plot(ph, np.append(tpl, tpl[0]), color="black", lw=1.2)
    dx.axhline(0, color="0.8", lw=0.4, zorder=0)
    dx.set_xlim(0, 1)
    dx.set_xlabel("gait phase (strides)")
    dx.set_ylabel("z-score")
    # (d) the four contours over the window's median f50, against time after the press
    style = {25: dict(color="0.55", lw=0.7, ls="-"), 50: dict(color="black", lw=0.9, ls="-"),
             75: dict(color="0.35", lw=0.8, ls=(0, (3.5, 1.5))), 95: dict(color="black", lw=0.8, ls=(0, (5, 1.5, 1, 1.5)))}
    ex.axhline(1.0, color="0.45", lw=0.5, ls=":", zorder=0)
    ends = {}
    for q in (25, 50, 75, 95):
        ex.plot(t_c, cont[q] / med50, **style[q])
        ends[q] = float(cont[q][-1] / med50)
    ex.set_xlim(0, 4.0)
    ex.set_xticks([0, 1, 2, 3, 4])                          # whole seconds, as (a) and (b)
    ex.set_xlabel("time after the press (s)")
    ex.set_ylabel("contour / torso median")
    lo_, hi_ = ex.get_ylim()
    gap, placed = 0.075 * (hi_ - lo_), []                    # the end labels, nudged apart where two ends meet
    for q in sorted(ends, key=ends.get):
        y_ = ends[q] if not placed else max(ends[q], placed[-1] + gap)
        placed.append(y_)
        ex.text(4.0 + 0.05, y_, str(q), fontsize=7, va="center", ha="left", clip_on=False)
    for a_, lab in ((ax, "(a)"), (bx, "(b)"), (dx, "(c)"), (ex, "(d)")):
        a_.text(0.0, 1.03, lab, transform=a_.transAxes, ha="left", va="bottom", fontsize=8.5)
    if not os.path.exists(TOPROW):                          # the one-row figure kept for rollback, before any overwrite
        import shutil
        shutil.copy2(PDF, TOPROW)
    fig.savefig(PDF)
    fig.savefig(PNG, dpi=200)
    w_pt, h_pt = fig.get_size_inches() * 72
    res = {"label": "development evaluation, all data seen; a figure of training data (B1), no figure of merit",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "session": "B1", "block": "natural", "walks_considered": n,
           "walks_peaking_at_the_step": n_at_step,
           "chosen": {"pa_code": pa, "natural_recording": nr, "walk_in_recording": k,
                      "rule": "RX2 step-band acf_cycle within 0.1 Hz of the resolved cadence; then largest cad|all|-|-|agree_frac, "
                              "then RX2 step-band acf_peak",
                      "agree_frac": float(agree), "rx2_step_band_acf_peak": float(peak)},
           "map": {"shape": list(m.shape), "bins_hz": [float(fb[0]), float(fb[-1])], "bin_spacing_hz": df,
                   "frame_s": dt, "equals_extraction_maps_1": True},
           "torso": {"torso_hz_rx2_window": float(f_t), "contour_hz_median": float(np.nanmedian(contour)),
                     "contour_hz_min": float(np.nanmin(contour)), "contour_hz_max": float(np.nanmax(contour)),
                     "frames": int(ok.sum()), "engine_f_torso": float(x["f_torso"]), "engine_speed_link": x["speed_link"],
                     "note": "the panel's contour is torso_hz on RX2's whole window; the engine's own speed uses the speed "
                             "link's walking span"},
           "step": {"cadence_hz": float(cad), "period_s": float(period), "acf_at_period": float(r[j])},
           "template": {"feature": pre_t + "tpl_00..tpl_31", "call": "idmax_features.cycle_templates(x, c, method='acf'), "
                        "recorded during engine.extract_window's id19_featbank.pass_features",
                        "c_hz": c_t, "c_hz_float32_stored": float(cad), "stride_samples": stride, "K": K,
                        "template_shift_phases": shift, "matching_calls": len(hits_t),
                        "input_equals_panel_b_signal": bool(np.array_equal(x_t, s)),
                        "ASSERT_template_equals_extraction_1e-9": True, "max_abs_diff": d_t64,
                        "max_abs_diff_float32_stored": d_t32, "template": [float(v) for v in tpl]},
           "contours": {"feature": pre_d + "*", "call": "idmax_features.doppler_features(P[1:], win_s=0.2) on RX2's "
                        "components 2 to 6 of the 4 to 70 Hz band, recorded during the same extraction",
                        "median_f50_hz": med50, "frames": int(len(t_c)), "matching_calls": len(hits_d),
                        "ratios_from_plotted_contours": ratios,
                        "ratios_extraction": {q: float(want_d[q]) for q in ratios},
                        "ASSERT_ratios_equal": True, "max_abs_diff": max(d_r.values())},
           "pdf": {"path": PDF, "bytes": os.path.getsize(PDF), "cm": [W_CM, H_CM], "pt": [round(w_pt, 2), round(h_pt, 2)],
                   "rows_cm": [TOP_CM, BOT_CM], "top_row_kept_as": TOPROW},
           "preview_png": PNG,
           "seconds": round(time.time() - t_all, 1), "nice": os.nice(0)}
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
