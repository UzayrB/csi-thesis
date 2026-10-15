"""ixt_readme. The teaching pack's field guide: every key path of the built pack with its type or shape, and its meaning
and units from the descriptions below (the README's last section). Paths under per-person, per-block or per-link
dictionaries are listed once with a placeholder (<name>, <block>, <link>, ...).

    PYTHONPATH=. python3 -m pipeline.identify.ixt_readme
"""

from __future__ import annotations

import json
import os
import re
import sys

from pipeline.identify import ixt_plots as XP

DESC = {
    "schema_version": "the pack's format version", "generated_at": "when the pack was built (SAST)",
    "git_commit": "the repository commit the pack was built at", "engine_plan_sha256": "SHA-256 of runs/identify/engine/PLAN.md at build time",
    "label": "the evaluation label (development evaluation, all data seen)", "names_note": "why names, not codes",
    "models": "model name -> the sessions it was trained on",
    "selection": "the worked-walk selection rule's inputs, ranking, decisions and branches",
    "walks": "the two worked walks, keyed 'wrong' and 'right'",
    "walks.<role>.app": "the live app's own logged values for this walk (rig-path verification run), unrounded",
    "walks.<role>.app.ensemble_probability": "the ensemble's normalised probability per person (what decides)",
    "walks.<role>.app.displayed_confidence": "softmax(sum / 8) per person: the number on screen",
    "walks.<role>.app.t_decision_data_s": "when the last packet the decision needed arrived (s after the press)",
    "walks.<role>.app.t_decision_s_after_press": "when the decision was made: data complete plus measured compute",
    "walks.<role>.app.latency_after_window_s": "decision time minus the window's end (press + 3 s)",
    "walks.<role>.app.packet_wait_after_window_s": "the deterministic part of the latency: waiting for every receiver's packets",
    "walks.<role>.app.calibration_walks_seen": "earlier walks of the day the engine had adapted to (unlabelled)",
    "walks.<role>.truth_for_teaching_only_never_seen_by_the_model": "metre-anchor presses and the end press: animation only; the model never sees them",
    "walks.<role>.event_timeline": "packet arrivals per receiver in 50 ms bins from press - 1 s to the decision + 0.5 s, and the key moments",
    "walks.<role>.links.<link>.raw_amplitude_heatmap_25hz": "[103 CSI entries][75 time bins]: amplitude on the 150 Hz grid averaged to 25 Hz",
    "walks.<role>.links.<link>.subcarrier_mean_50hz": "the mean over the 103 entries, at 50 Hz (150 samples)",
    "walks.<role>.links.<link>.rssi_50hz_dbm": "RSSI on the grid at 50 Hz",
    "walks.<role>.links.<link>.inter_packet_gap_median_ms": "median gap between this receiver's packets inside the window (causal clock)",
    "walks.<role>.links.<link>.conditioning.step2_bandpass_4_70hz_rms_heatmap_25hz": "[103][75]: RMS of the 4 to 70 Hz band-passed amplitude per 40 ms bin",
    "walks.<role>.links.<link>.conditioning.step3_pca_explained_variance_pc1_to_pc4": "fraction of the band-passed variance in PCs 1 to 4",
    "walks.<role>.links.<link>.conditioning.step3_pc1_trace_50hz_discarded": "PC1 (common-mode power; discarded), every third sample",
    "walks.<role>.links.<link>.conditioning.step3_pc2_to_pc4_traces_50hz": "[3][150]: PCs 2 to 4 (kept), every third sample (display only)",
    "walks.<role>.links.<link>.conditioning.step4_stft_magnitude_per_pc": "[3 PCs][28 freqs][53 frames]: STFT magnitude per kept PC",
    "walks.<role>.links.<link>.conditioning.step5_log_map_minus_mean_cnn_input": "[28 freqs][53 frames]: the CNN's input map",
    "walks.<role>.links.<link>.gait_channel_mean_b08_35_50hz": "the 0.8 to 3.5 Hz subcarrier-mean channel at 50 Hz",
    "walks.<role>.links.<link>.gait_channel_autocorrelation_50hz_lags_0_to_2s": "its autocorrelation, lags 0 to 2 s at 50 Hz",
    "walks.<role>.links.<link>.bistatic_factor_F": "the link's mean projected bistatic factor along line A in this direction",
    "walks.<role>.links.<link>.predicted_torso_hz_press_speed": "2 F v / lambda with v the press speed (a physics reference; press speed is not a model input)",
    "walks.<role>.map_frequency_axis_hz": "the 28 map frequencies (Hz)", "walks.<role>.map_frame_times_s": "the 53 STFT frame centres (s after the press)",
    "walks.<role>.direction": "RX2's 10 to 35 Hz log energy per frame, its least-squares slope, and the detected direction",
    "walks.<role>.speed": "the per-frame torso contour, f_torso, F, lambda and the Wi-Fi speed v = f lambda / (2 F)",
    "walks.<role>.gait_features": "the 630 gait features: names, families, raw values, and as standardised by the calibration in force",
    "walks.<role>.evidence.components": "each of the 8 components' six log-probabilities and probabilities",
    "walks.<role>.evidence.cnn_evolution": "each CNN component's per-window log-probabilities and running mean, by window centre time",
    "walks.<role>.evidence.margin_log_units": "ensemble log-probability of the top minus the runner-up",
    "walks.<role>.drivers": "diagnostics, not causes: forest importances (global) with this walk's values; LDA coef x z contributions",
    "walks.<role>.substitution": "this walk's slot given its donor's radio: the donor, the swapped decision, and the decision with the rebuilt pool",
    "model.settings": "every fixed parameter of the engine", "model.cnn_3link": "the 3-link CNN layer by layer with parameter counts",
    "model.cnn_1link": "the 1-link CNN", "model.saved_state_dict_totals": "parameter totals read from the saved weights",
    "model.training": "per-session, per-person passes and CNN windows, class balance, training time and seeds",
    "model.chance_pct": "chance for every measure", "model.lda_fitted_shrinkage_per_class_loso_B2": "Ledoit-Wolf shrinkage per class",
    "results": "every results table; each entry is a result entry (see Conventions)",
    "results.confusion_B2": "[true][predicted] counts on B2's natural walks (names in rows_true_cols_predicted)",
    "results.pace_confound": "S0 (press speed), S_wifi (Wi-Fi speed), the engine without pace, and paired differences by block",
    "results.confidence_coverage": "accuracy on the most confident walks, who is in each level, and the AUROC",
    "results.one_press_cost": "the engine against the two-press configuration, paired",
    "results.physics": "identity-blind physics checks", "results.rejected_candidates": "every candidate tried and not adopted",
    "provenance": "one row per fitted part or design choice: what it was fitted or chosen on, when, by what rule, file and commit; the flag marks choices made with test results in view",
    "timeline": "every headline figure since 12 September with its status and why it was superseded",
    "checks.verification": "replay equals live, and the worked walks' numbers equal the app's log",
    "checks.substitution": "the substitution test, both calibration variants, per pair",
    "checks.shuffled_full": "the full engine retrained on permuted labels (to B2)",
    "checks.shuffled_null": "20 feature-only permutations and the empirical p-value",
    "checks.conditioning_ablation": "the CNNs retrained without one conditioning step at a time (information only)",
    "checks.conditioning_energy_identity_blind": "RX2's 10 to 35 Hz energy over the empty room, raw and conditioned",
    "addendum": "the addendum's three measurements: AC1 step-rate grid, AC2 same day, AC3 training without paced walks",
    "engine_version": "2: engine v1 plus the cadence bug fix (1 Oct 2026); every engine figure in the pack is v2's",
    "engine_version_note": "what engine v2 is and where v1's figures went (the timeline, as superseded)",
    "results.physics.cadence_resolver_engine_windows_v1_and_v2": "the resolved step rate on the 180 natural walks' engine windows, before and after the fix, against the energy envelope",
    "addendum.AC1_step_rate_simulated.before_the_fix": "the same simulated-walk grid through engine v1: the run that found the cadence bug",
    "addendum.AC1_step_rate_simulated.the_bug": "the fault, the fix, worked simulated walks, and the fix's effect on the real walks' resolved step rate",
    "addendum.AC1_step_rate_simulated.effect_measured_before_adoption": "the fix's effect on the figures, measured by feature re-scoring before Uzayr adopted it",
    "addendum.AC1_step_rate_simulated.decision": "Uzayr's decision on the bug (1 Oct 2026)",
    "model": "the model: settings, network tables, components, features, training statistics and chance",
    "model.cnn_training": "the CNNs' training recipe: optimiser, steps, batch, sampling, augmentation and seeds",
    "model.components": "the eight components, each in one line",
    "model.features_630_by_family": "how many of the 630 gait features are in each family (rhythm, Doppler contours, cycle templates, spectral shape, wavelets, modulation, cadence)",
    "checks": "replay equals live, the substitution test, the shuffled-label control and the conditioning ablation",
    "provisional": "false in the final pack (true only in a drafting build without every result)",
    "results.component_families": "the CNN components alone, the feature components alone and all eight, natural walks (information)"}

PLACE = [(r"walks\.(wrong|right)", "walks.<role>"), (r"\.links\.RX[123]", ".links.<link>")]
BUCKET = {"PA5", "PA1", "PA2", "PA3", "PA4", "PA6", "natural_both", "natural_away", "natural_towards", "slow", "fast",
          "A1", "A2", "A3", "B1", "B2", "room_A", "room_B", "to B2", "to B1", "rf", "rf_prior", "rf_pace_prior", "et_pace_prior",
          "lda_pace_prior", "cnn", "cnn_prior", "cnn_perlink_prior"}


def walk(x, path, rows):
    p = path
    for a, b in PLACE:
        p = re.sub(a, b, p)
    if isinstance(x, dict):
        keys = list(x)
        if keys and all(k in BUCKET or k.endswith("%") or k.startswith("T") and k[1:2].isdigit() for k in keys):
            rows.setdefault(p, ("dict over " + ", ".join(keys[:8]) + (" ..." if len(keys) > 8 else ""), None))
            walk(x[keys[0]], p + ".<key>", rows)
            return
        rows.setdefault(p, ("object", None))
        for k, v in x.items():
            walk(v, f"{p}.{k}" if p else k, rows)
    elif isinstance(x, list):
        shape, y = [], x
        while isinstance(y, list):
            shape.append(len(y))
            y = y[0] if y else None
        if isinstance(y, dict):
            rows.setdefault(p, (f"list of {len(x)} objects", None))
            walk(y, p + "[]", rows)
        else:
            rows.setdefault(p, ("array " + " x ".join(map(str, shape)), None))
    else:
        rows.setdefault(p, (type(x).__name__, None))


def guide() -> str:
    p = XP.load_pack()
    rows = {}
    walk(p, "", rows)
    out = ["| field | type or shape | meaning |", "|---|---|---|"]
    for k, (t, _) in rows.items():
        if not k:
            continue
        d = DESC.get(k, "")
        if not d:
            for pre in sorted(DESC, key=len, reverse=True):
                if k.startswith(pre + ".") or k.startswith(pre + "["):
                    d = f"(part of `{pre}`)"
                    break
        out.append(f"| `{k}` | {t} | {d} |")
    return "\n".join(out)


if __name__ == "__main__":
    print(guide())
    sys.exit(0)
