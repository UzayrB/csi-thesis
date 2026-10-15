"""ixt_plots. Sanity plots made FROM the teaching pack itself (`reports/identification/teaching/check_png/`), so the page writer can check
its own figures against them. Nothing here reads anything but the pack.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_plots
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

OUT = os.path.join("reports", "identification", "teaching", "check_png")
# engine v4 (2 Oct): the newest dated pack; its plots get the pack's date as a prefix, beside the 1 Oct plots (never overwritten)
PACK = "2026-10-02_teaching-pack.json" if os.path.exists(os.path.join("reports", "identification", "teaching", "2026-10-02_teaching-pack.json")) \
    else "2026-10-01_teaching-pack.json"
PREFIX = "" if PACK.startswith("2026-10-01") else PACK[:11]


def load_pack() -> dict:
    d = os.path.join("reports", "identification", "teaching")
    one = os.path.join(d, PACK)
    if os.path.exists(one):
        return json.load(open(one))
    core = json.load(open(os.path.join(d, "id_teaching_pack_core.json")))
    sg = json.load(open(os.path.join(d, "id_teaching_pack_signals.json")))
    for r, w in sg["walks"].items():
        core["walks"][r].update({k: v for k, v in w.items() if k != "cnn_evolution"})
        core["walks"][r]["evidence"]["cnn_evolution"] = w["cnn_evolution"]
    return core


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = load_pack()
    os.makedirs(OUT, exist_ok=True)
    W = p["walks"]
    names = W["wrong"]["evidence"]["classes_order"]
    tag = {r: f"{W[r]['name']} pass {W[r]['pass_index_in_recording']} ({r}: app said {W[r]['app']['top']})" for r in W}
    # 1-2. RX2 raw amplitude and conditioned map, both walks
    for r in ("wrong", "right"):
        L = W[r]["links"]["RX2"]
        fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
        H = np.array(L["raw_amplitude_heatmap_25hz"])
        ax[0].imshow(H, aspect="auto", origin="lower", extent=[0, H.shape[1] / 25.0, 0, 103])      # the window's own length
        ax[0].set(title="RX2 raw amplitude (103 entries, 25 Hz)", xlabel="s after press", ylabel="CSI entry")
        m = np.array(L["conditioning"]["step5_log_map_minus_mean_cnn_input"])
        f = W[r]["map_frequency_axis_hz"]
        t = W[r]["map_frame_times_s"]
        ax[1].imshow(m, aspect="auto", origin="lower", extent=[t[0], t[-1], f[0], f[-1]])
        ax[1].axhline(L["predicted_torso_hz_press_speed"], color="w", ls="--", lw=1)
        ax[1].set(title="RX2 conditioned map (the CNN input)", xlabel="s after press", ylabel="Hz")
        fig.suptitle(tag[r])
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, PREFIX + f"01_rx2_raw_and_map_{r}.png"), dpi=90)
        plt.close(fig)
    # 3. CNN score evolution (true person and the decided person)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for a, r in zip(ax, ("wrong", "right")):
        ev = W[r]["evidence"]["cnn_evolution"]
        tc = ev["window_centre_s"]
        for c, ls in (("cnn_prior", "-"), ("cnn_perlink_prior", "--")):
            run = np.exp(np.array(ev[c]["running_logp"]))
            for j, n in enumerate(names):
                if n in (W[r]["app"]["truth"], W[r]["app"]["top"]):
                    a.plot(tc, run[:, j], ls, label=f"{c}: {n}")
        a.axhline(1 / 6, color="grey", lw=0.8)
        a.set(title=tag[r], xlabel="window centre, s after press", ylabel="running probability")
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "02_cnn_score_evolution.png"), dpi=90)
    plt.close(fig)
    # 4. the eight components' log-probabilities
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for a, r in zip(ax, ("wrong", "right")):
        comps = W[r]["evidence"]["components"]
        M = np.array([comps[c]["logp"] for c in comps])
        im = a.imshow(M, aspect="auto", cmap="viridis")
        a.set_xticks(range(6), names, rotation=45, fontsize=8)
        a.set_yticks(range(len(comps)), list(comps), fontsize=8)
        a.set_title(tag[r], fontsize=9)
        fig.colorbar(im, ax=a)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "03_component_logprobs.png"), dpi=90)
    plt.close(fig)
    # 5. the B2 confusion matrix
    cm = p["results"]["confusion_B2"]
    M = np.array(cm["matrix"])
    fig, a = plt.subplots(figsize=(5.5, 4.6))
    a.imshow(M, cmap="Blues")
    for i in range(6):
        for j in range(6):
            a.text(j, i, M[i, j], ha="center", va="center", fontsize=9)
    a.set_xticks(range(6), cm["rows_true_cols_predicted"], rotation=45)
    a.set_yticks(range(6), cm["rows_true_cols_predicted"])
    a.set(xlabel="predicted", ylabel="true", title="B2 natural walks (loso_B2_x, engine v2, causal)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "04_confusion_B2.png"), dpi=90)
    plt.close(fig)
    # 6. substitution
    s = p["checks"]["substitution"]
    fig, a = plt.subplots(figsize=(7, 3.6))
    labels, vals, lo, hi = [], [], [], []
    for v in ("A", "B"):
        for k, nm in (("equals_donor_own_decision", "= donor's own decision"), ("accuracy_vs_donor_identity", "names the donor"),
                      ("accuracy_vs_host_identity", "names the host")):
            d = s[f"variant_{v}"][k]
            labels.append(f"{v}: {nm}")
            vals.append(d["pct"])
            lo.append(d["pct"] - d["ci95"][0])
            hi.append(d["ci95"][1] - d["pct"])
    a.barh(labels, vals, xerr=[lo, hi], color="tab:blue")
    a.axvline(16.67, color="red", ls="--", lw=1)
    a.set(xlabel="%", title="substitution: another person's radio in the host's slot")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "05_substitution.png"), dpi=90)
    plt.close(fig)
    # 7. shuffled-label null
    sn, sf = p["checks"]["shuffled_null"], p["checks"]["shuffled_full"]
    fig, a = plt.subplots(figsize=(7, 3.6))
    a.hist(sn["null_pct"], bins=10, color="0.6", label="20 feature-only permutations")
    a.axvline(sn["real_pct"], color="tab:blue", lw=2, label=f"real feature components {sn['real_pct']}")
    a.axvline(sf["natural_accuracy"]["pct"], color="tab:orange", lw=2, ls="--", label=f"full engine, shuffled labels {sf['natural_accuracy']['pct']}")
    a.axvline(16.67, color="red", ls=":", lw=1, label="chance 16.67")
    a.set(xlabel="% correct, B2 natural walks", title=f"shuffled-label control (p = {sn['p_value']})")
    a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "06_shuffled_label.png"), dpi=90)
    plt.close(fig)
    # 8. conditioning ablation
    ab = p["checks"]["conditioning_ablation"]
    keys = ["engine", "V1", "V2", "V3", "V4"]
    fig, a = plt.subplots(figsize=(7, 3.6))
    vals = [ab[k]["natural"]["pct"] for k in keys]
    err = [[ab[k]["natural"]["pct"] - ab[k]["natural"]["ci95"][0] for k in keys], [ab[k]["natural"]["ci95"][1] - ab[k]["natural"]["pct"] for k in keys]]
    a.bar(keys, vals, yerr=err, color=["tab:blue"] + ["0.6"] * 4)
    a.axhline(16.67, color="red", ls="--", lw=1)
    a.set(ylabel="% correct, natural walks (both folds)", title="conditioning ablation: one step removed at a time")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, PREFIX + "07_conditioning_ablation.png"), dpi=90)
    plt.close(fig)
    # 9. AC1: resolved step rate over the true one on the simulated walks, before and after the cadence bug fix
    ac1 = p["addendum"].get("AC1_step_rate_simulated")
    if ac1:
        fig, a = plt.subplots(figsize=(7, 3.6))
        for walks, lab, col, mk in ((ac1["before_the_fix"]["walks"], "engine v1 (the bug)", "tab:red", "x"),
                                    (ac1["walks"], "engine v2 (fixed)", "tab:blue", "o")):
            a.scatter([w["step_hz"] for w in walks], [w["engine_3s_window"]["resolver_over_true"] for w in walks],
                      marker=mk, color=col, s=18, label=lab)
        a.axhspan(0.95, 1.05, color="0.9", zorder=0)
        a.axhline(1.0, color="0.4", lw=0.8)
        a.set(xlabel="true step rate (Hz)", ylabel="resolved / true", title="AC1: step rate on 48 simulated walks (3 s window)")
        a.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, PREFIX + "08_ac1_step_rate.png"), dpi=90)
        plt.close(fig)
    print(sorted(glob.glob(os.path.join(OUT, PREFIX + "*.png"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
