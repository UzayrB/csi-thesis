"""Two colour figures for Methodology 3.4.2 (queue 13, Uzayr's prompt via Editor Main; his go in the Code agent's chat, 14 Oct),
replacing the two-row `id_example.pdf` (kept, with its JSON, for rollback). The same walk and data path as `id_example.py`
(PA4, B1 natural, the signal-only rhythm rule; the engine's own extraction recorded with `Capture`, nothing recomputed along
another filtering path). Read-only on code and data; no model is loaded; the walker is named only by PA code.

`id_speed.pdf`:
(a) RX2's Doppler map as the CNNs receive it (viridis) with the torso contour of `id29_dc2_score.torso_hz` on RX2's window
    (id_example's (a), recoloured).
(b) The torso contour f_torso(t) of the engine's OWN speed: `engine.Extractor.extract_v4`'s `D.torso_hz(A[li][:nw])` on the
    speed link over the detected walking span (engine.py:430), whose median is the reported `f_torso` and gives
    `wifi_speed` = f_torso lambda / (2F) (engine.py:431); the plotted median and v asserted equal to the extraction's.
`id_gait.pdf`:
(a) RX2's step-band mean and its autocorrelation, the step lag tau_s = 1/c and the stride lag 2 tau_s marked.
(b) The K strides (grey) and the cycle template (colour): `cycle_templates`' acf call, asserted equal to the extraction's
    tplacf|mean@b08_35|RX2|0|tpl_00..31 to 1e-9.
(c) f25, f50, f75 and f95 over the window's median f50 (`doppler_features`' RX2 pca-pc1@w0.2 call), a dotted line at 1, a
    legend; leg_torso, q25_torso and q75_torso from the plotted contours asserted equal to the extraction's.

Colour: Okabe-Ito for lines (every line also has its own line style, so it reads in greyscale); viridis for the map, the
colour map of the report's only other colour figure (`chain_example.pdf`, `tools/make_chain_example.py`).

    cd <Code> && OMP_NUM_THREADS=1 PYTHONPATH=. nice -n 10 python3 runs/identify/v5/figures/id_speed_gait.py

Development evaluation, all data seen; a figure of training data (B1), no figure of merit.
"""

import os
import sys

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.join("runs", "identify", "v5", "figures")
sys.path.insert(0, HERE)
import id_example as IX  # noqa: E402  (walks, Capture, _same, _strides, _contours: the same data path)

PDF_SPEED, PDF_GAIT = os.path.join(HERE, "id_speed.pdf"), os.path.join(HERE, "id_gait.pdf")
PNG_SPEED, PNG_GAIT = os.path.join(HERE, "id_speed_preview.png"), os.path.join(HERE, "id_gait_preview.png")
OUT = os.path.join(HERE, "id_speed_gait.json")
W_CM, H_CM = 15.92, 4.0                    #: 4.0 cm each (Uzayr via Editor Main, 19:53: 4.4 cm spills Chapter 3 to 19 pages)
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7"}          #: Okabe and Ito's colour-blind-safe set


def main():
    import scipy.signal as SS
    from pipeline.identify import conditioning as CO
    from pipeline.identify import engine as EN
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import idmax_features as F
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idz_bank as ZB
    t_all = time.time()
    best, n, n_at_step = None, 0, 0
    # the engine's own calls, recorded per walk while its extraction runs (inputs and outputs; nothing changed)
    with IX.Capture(FB, "pass_features") as cpf, IX.Capture(F, "cycle_templates") as ctp, \
            IX.Capture(F, "doppler_features") as cdf, IX.Capture(D, "torso_hz") as cth:
        for pa, nr, k, x, A, t0, names in IX.walks():
            rec = (list(cpf.out), list(ctp.calls), list(cdf.calls), list(cth.calls))
            for lst in (cpf.out, cpf.calls, ctp.out, ctp.calls, cdf.out, cdf.calls, cth.out, cth.calls):
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
    feats = rec[0][0]
    c = float(feats["cad|all|-|-|cadence_hz"])
    tau_s = 1.0 / c

    # ---- id_speed (a): the map as the CNNs receive it, and torso_hz's contour on RX2's window (id_example's (a))
    with IX.Capture(SS, "stft") as st:
        m = ZB.conditioned_map_v2(A[1])
    assert np.array_equal(m, x["maps"][1]), "the map differs from the extraction's"
    t_map = st.out[-1][1]
    with IX.Capture(SS, "stft") as st2, IX.Capture(CO, "energy_percentile_contour") as ec:
        f_rx2 = D.torso_hz(A[1])
    t_tor_a, cont_a = st2.out[-1][1], np.asarray(ec.out[-1], float)
    # ---- id_speed (b): the engine's own speed call, extract_v4's torso_hz on the speed link's walking span (its last
    # torso_hz call for the window), replayed on its own recorded input to read its contour
    assert rec[3], "no torso_hz call recorded for the chosen walk"
    (span,), _kw, ft_engine = rec[3][-1]
    li = EN.LINKS.index(x["speed_link"])
    nw = int(np.asarray(span).shape[0])                    # the span's samples, as engine.py:429 cut them
    assert abs(nw - x["walk_end_s"] * EN.FS) <= 1.0, (nw, x["walk_end_s"])
    assert ft_engine == x["f_torso"], (ft_engine, x["f_torso"])
    with IX.Capture(SS, "stft") as st3, IX.Capture(CO, "energy_percentile_contour") as ec3:
        ft_replay = D.torso_hz(span)
    assert ft_replay == ft_engine, (ft_replay, ft_engine)
    t_tor, cont = st3.out[-1][1], np.asarray(ec3.out[-1], float)
    okc = np.isfinite(cont)
    med_plot = float(np.median(cont[okc]))
    Fgeo = float(x["speed_F"])
    v_plot = float(med_plot * EN.LAMBDA / (2.0 * Fgeo)) if Fgeo >= EN.F_MIN else float("nan")
    assert med_plot == x["f_torso"], (med_plot, x["f_torso"])
    assert v_plot == x["wifi_speed"], (v_plot, x["wifi_speed"])
    # the training row of this walk in the deployed model's bank (bank_T4.0_v4, alpha 0.5): its speed is the same path's
    man = json.load(open(os.path.join(EN.ENG, "models", "deploy_all5_v5", "manifest.json")))
    meta = json.load(open(os.path.join(man["bank"], "meta.json")))["passes"]
    rows = [r for r in meta if r["session"] == "B1" and abs(float(r["t_start"]) - t0) < 1e-6]
    assert len(rows) == 1, f"{len(rows)} bank rows at this walk's press"
    bank_v = float(rows[0]["wifi_speed"])
    bank_equal = bool(bank_v == x["wifi_speed"])
    assert bank_equal, (bank_v, x["wifi_speed"])

    # ---- id_gait (a): the step band and its autocorrelation
    s = F.reduce_link(A[1], "b08_35", "mean")[0]
    r = F._acf(s)
    t_s = np.arange(len(s)) / F.FS
    lag = np.arange(len(r)) / F.FS
    j1, j2 = int(round(tau_s * F.FS)), int(round(2 * tau_s * F.FS))
    # ---- id_gait (b): the template (the recorded cycle_templates call whose output is the extraction's)
    pre_t = "tplacf|mean@b08_35|RX2|0|"
    want_t = {q[len(pre_t):]: v for q, v in feats.items() if q.startswith(pre_t)}
    hits_t = [a_ for a_, k_, r_ in rec[1] if k_.get("method", "acf") == "acf" and IX._same(r_, want_t)]
    assert hits_t and all(np.array_equal(h[0], hits_t[0][0]) and h[1] == hits_t[0][1] for h in hits_t)
    x_t, c_t = np.asarray(hits_t[0][0], float), float(hits_t[0][1])
    assert c_t == c, (c_t, c)
    stride, K, Az, tpl, shift = IX._strides(x_t, c_t, F.FS, F.PHASE)
    if K < 2:
        raise SystemExit(f"STOP: K = {K} strides (< 2)")
    tpl_ext = np.array([want_t[f"tpl_{i:02d}"] for i in range(F.PHASE)])
    d_t = float(np.max(np.abs(tpl - tpl_ext)))
    assert d_t <= 1e-9, d_t
    # ---- id_gait (c): the contours (the recorded doppler_features call whose output is the extraction's)
    pre_d = "dop|pca-pc1@w0.2|RX2|-|"
    want_d = {q[len(pre_d):]: v for q, v in feats.items() if q.startswith(pre_d)}
    hits_d = [a_ for a_, k_, r_ in rec[2] if k_.get("win_s") == 0.2 and np.atleast_2d(a_[0]).shape[0] == 5
              and IX._same(r_, want_d)]
    assert hits_d and all(np.array_equal(h[0], hits_d[0][0]) for h in hits_d)
    t_c, cq, med50 = IX._contours(hits_d[0][0], F.FS, 0.2)
    ratios = {"leg_torso": float(np.median(cq[95]) / med50), "q25_torso": float(np.median(cq[25]) / med50),
              "q75_torso": float(np.median(cq[75]) / med50)}
    d_r = {q: abs(v - want_d[q]) for q, v in ratios.items()}
    assert all(v <= 1e-12 for v in d_r.values()), d_r

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8,
                         "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "pdf.fonttype": 42, "axes.linewidth": 0.6,
                         "xtick.major.width": 0.6, "ytick.major.width": 0.6})
    yb, hb = 0.95 / H_CM, 2.62 / H_CM                     # 0.95 cm below the axes, 0.43 cm above for the panel letters

    # ================================================================ id_speed.pdf
    fig = plt.figure(figsize=(W_CM / 2.54, H_CM / 2.54))
    ax = fig.add_axes([0.068, yb, 0.40, hb])
    bx = fig.add_axes([0.575, yb, 0.415, hb])
    fb = C.F_BINS
    df = float(fb[1] - fb[0])
    dt = float(t_map[1] - t_map[0])
    ax.imshow(m, origin="lower", aspect="auto", cmap="viridis", interpolation="nearest",
              extent=[t_map[0] - dt / 2, t_map[-1] + dt / 2, fb[0] - df / 2, fb[-1] + df / 2])
    oka = np.isfinite(cont_a)
    ax.plot(t_tor_a[oka], cont_a[oka], color=OI["orange"], lw=1.1,
            path_effects=[pe.Stroke(linewidth=2.3, foreground="black"), pe.Normal()])
    ax.set_xlim(0, 4.0)
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_ylim(fb[0] - df / 2, fb[-1] + df / 2)
    ax.set_xlabel("time after the press (s)")
    ax.set_ylabel("Doppler frequency (Hz)")
    bx.plot(t_tor[okc], cont[okc], color=OI["blue"], lw=0.9, ls="-", label=r"$f_{\mathrm{torso}}(t)$")
    bx.axhline(med_plot, color=OI["vermillion"], lw=0.9, ls=(0, (4, 2)), label="median")
    bx.set_xlim(0, 4.0)
    bx.set_xticks([0, 1, 2, 3, 4])
    lo_, hi_ = float(np.nanmin(cont[okc])), float(np.nanmax(cont[okc]))
    bx.set_ylim(max(0.0, lo_ - 3.0), hi_ + 0.45 * (hi_ - lo_ + 6.0))
    bx.set_xlabel("time after the press (s)")
    bx.set_ylabel("torso contour (Hz)")
    bx.text(0.98, 0.95, f"median {med_plot:.1f} Hz\n" + rf"$v = f\lambda/(2F)$ = {v_plot:.2f} m/s ($F$ = {Fgeo:.2f})",
            transform=bx.transAxes, ha="right", va="top", fontsize=7.5, linespacing=1.3)
    bx.legend(loc="upper left", fontsize=7, frameon=False, handlelength=2.2, borderaxespad=0.3)
    for a_, lab in ((ax, "(a)"), (bx, "(b)")):
        a_.text(0.0, 1.03, lab, transform=a_.transAxes, ha="left", va="bottom", fontsize=8.5)
    fig.savefig(PDF_SPEED)
    fig.savefig(PNG_SPEED, dpi=200)
    plt.close(fig)

    # ================================================================ id_gait.pdf
    fig = plt.figure(figsize=(W_CM / 2.54, H_CM / 2.54))
    gx = fig.add_axes([0.055, yb, 0.165, hb])             # (a) the step-band mean
    hx = fig.add_axes([0.30, yb, 0.145, hb])              # (a) its autocorrelation (room for its tick labels and label)
    ix = fig.add_axes([0.51, yb, 0.17, hb])               # (b) the strides and template
    jx = fig.add_axes([0.755, yb, 0.235, hb])             # (c) the contours
    gx.plot(t_s, s, color=OI["black"], lw=0.7)
    gx.set_xlim(0, 4.0)
    gx.set_xticks([0, 1, 2, 3, 4])
    gx.set_yticks([])
    gx.set_xlabel("time after the press (s)")
    gx.set_ylabel("step-band mean (a.u.)")
    kk = lag <= 2.2
    hx.plot(lag[kk], r[kk], color=OI["black"], lw=0.7)
    hx.axhline(0, color="0.6", lw=0.5)
    for jj, lab, col, ls in ((j1, r"$\tau_s$", OI["vermillion"], (0, (4, 2))), (j2, r"$2\tau_s$", OI["blue"], (0, (6, 1.5, 1.5, 1.5)))):
        hx.axvline(lag[jj], color=col, lw=0.8, ls=ls)
        hx.plot([lag[jj]], [r[jj]], "o", ms=3, mfc="white", mec=col, mew=0.8)
        hx.text(lag[jj] + 0.04, 0.96, lab, fontsize=7.5, va="top", ha="left", transform=hx.get_xaxis_transform())
    hx.set_xlim(0, 2.2)
    hx.set_xlabel("lag (s)")
    hx.set_ylabel("autocorrelation")
    ph = np.arange(F.PHASE + 1) / F.PHASE
    for row in Az:
        ix.plot(ph, np.append(row, row[0]), color="0.62", lw=0.5, ls="-")
    ix.plot(ph, np.append(tpl, tpl[0]), color=OI["blue"], lw=1.3, ls="-")
    ix.axhline(0, color="0.82", lw=0.4, zorder=0)
    ix.set_xlim(0, 1)
    ix.set_xticks([0, 0.5, 1])
    ix.set_xlabel("gait phase (strides)")
    ix.set_ylabel("z-score")
    style = {25: dict(color=OI["orange"], lw=0.8, ls=(0, (4, 1.2, 1, 1.2, 1, 1.2))),
             50: dict(color=OI["blue"], lw=1.0, ls="-"),
             75: dict(color=OI["green"], lw=0.8, ls=(0, (4, 1.5))),
             95: dict(color=OI["vermillion"], lw=0.8, ls=(0, (6, 1.5, 1.5, 1.5)))}
    jx.axhline(1.0, color="0.45", lw=0.5, ls=":", zorder=0)
    for q in (25, 50, 75, 95):
        jx.plot(t_c, cq[q] / med50, label=str(q), **style[q])
    jx.set_xlim(0, 4.0)
    jx.set_xticks([0, 1, 2, 3, 4])
    top = float(max(np.max(cq[q] / med50) for q in cq))
    jx.set_ylim(0, top * 1.5)
    jx.set_xlabel("time after the press (s)")
    jx.set_ylabel("contour / torso median")
    jx.legend(loc="upper center", ncol=2, fontsize=6.5, frameon=False, handlelength=2.2, columnspacing=1.0,
              handletextpad=0.4, borderaxespad=0.2, labelspacing=0.25)
    for a_, lab in ((gx, "(a)"), (ix, "(b)"), (jx, "(c)")):
        a_.text(0.0, 1.03, lab, transform=a_.transAxes, ha="left", va="bottom", fontsize=8.5)
    fig.savefig(PDF_GAIT)
    fig.savefig(PNG_GAIT, dpi=200)
    plt.close(fig)

    res = {"label": "development evaluation, all data seen; figures of training data (B1), no figure of merit",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "session": "B1", "block": "natural", "walks_considered": n,
           "walks_peaking_at_the_step": n_at_step,
           "chosen": {"pa_code": pa, "natural_recording": nr, "walk_in_recording": k, "rule": "as id_example.py",
                      "agree_frac": float(agree), "rx2_step_band_acf_peak": float(peak)},
           "palette": {"lines": "Okabe-Ito (#E69F00, #56B4E9, #009E73, #0072B2, #D55E00) with a distinct line style each",
                       "map": "viridis, as the report's chain_example.pdf (tools/make_chain_example.py), the only colour "
                              "palette among the report's figures found in the Code"},
           "speed": {"plotted_path": "engine.Extractor.extract_v4 (engine.py:427-433): D.torso_hz(A[li][:nw]) (:430) on the "
                                     "speed link over the detected walking span, then v = f_torso * LAMBDA / (2F) when "
                                     "F >= F_MIN; recorded during the extraction and replayed on its own input",
                     "speed_link": x["speed_link"], "path": x["path"], "F": Fgeo, "lambda_m": EN.LAMBDA, "F_MIN": EN.F_MIN,
                     "walk_end_s": float(x["walk_end_s"]), "span_samples": nw, "window_s": float(x["window_s"]),
                     "median_f_torso_hz": med_plot, "v_m_s": v_plot,
                     "ASSERT_median_equals_extraction_f_torso": True, "ASSERT_v_equals_extraction_wifi_speed": True,
                     "contour_frames": int(okc.sum()),
                     "panel_a_contour": {"what": "torso_hz on RX2's whole window (id_example's (a))", "median_hz": f_rx2,
                                         "equals_panel_b": bool(np.array_equal(cont_a, cont) and x["speed_link"] == "RX2")},
                     "training_row": {"bank": man["bank"], "alpha": man["alpha"], "wifi_speed": bank_v,
                                      "ASSERT_equals_live_extraction": bank_equal},
                     "reference_speed_json_only": {"press_speed_m_s": rows[0].get("press_speed_m_s"),
                                                   "note": "the bank meta's press-derived speed (labels), not on the figure"},
                     "which_path_feeds_what": {
                         "plotted": "the live walking-span path (extract_v4), the value identification reports",
                         "classifiers": "Model.classify reads ex['wifi_speed'] as the pace column (engine.py:591, :608) "
                                        "and the calibration pool appends it (engine.py:694); for T = 4.0 s, Extractor.poll "
                                        "calls extract_v4 (engine.py:395-396), whose speed (engine.py:430-431) and x.update (:432-433) overwrite "
                                        "extract_window's whole-window wifi_speed (signal_measures, engine.py:293-294). "
                                        "Editor Main's reading is right: the live walking span feeds the classifiers.",
                         "training": "deploy_all5_v5's bank is bank_T4.0_v4 at alpha 0.5 (its manifest), built by "
                                     "pipeline/identify/iv4_build.py through the engine's own Extractor, so through "
                                     "extract_v4's walking span, each speed asserted at build time equal to the lean-in "
                                     "screen's 4.0 s arm (iwg_bank.window, the same formula); this walk's row asserted "
                                     "equal to the live extraction here. idx_bank.pass_items computes no speed.",
                         "same_path_in_training_and_live": True}},
           "step": {"c_hz": c, "c_hz_float32_stored": float(fv["cad|all|-|-|cadence_hz"]), "tau_s": tau_s,
                    "two_tau_s": 2 * tau_s, "acf_at_tau_s": float(r[j1]), "acf_at_2tau_s": float(r[j2])},
           "template": {"feature": pre_t + "tpl_00..tpl_31", "K": K, "stride_samples": stride, "template_shift_phases": shift,
                        "ASSERT_template_equals_extraction_1e-9": True, "max_abs_diff": d_t,
                        "input_equals_panel_a_signal": bool(np.array_equal(x_t, s))},
           "contours": {"feature": pre_d + "*", "median_f50_hz": med50, "frames": int(len(t_c)),
                        "ratios_from_plotted_contours": ratios, "ratios_extraction": {q: float(want_d[q]) for q in ratios},
                        "ASSERT_ratios_equal": True, "max_abs_diff": max(d_r.values())},
           "pdfs": {"id_speed": PDF_SPEED, "id_gait": PDF_GAIT, "cm": [W_CM, H_CM],
                    "bytes": [os.path.getsize(PDF_SPEED), os.path.getsize(PDF_GAIT)]},
           "previews": [PNG_SPEED, PNG_GAIT], "replaces": "id_example.pdf (kept with id_example.json for rollback)",
           "seconds": round(time.time() - t_all, 1), "nice": os.nice(0)}
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
