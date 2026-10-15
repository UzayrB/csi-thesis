# The identification teaching pack: README (2026-10-01)

**For:** the claude.ai chat building the identification teaching page. It cannot see the repository.

**What it is:**
- **Where the numbers come from:** every number the page shows comes from the pack below.
  - The pack was produced by the identification engine, `pipeline/identify/engine.py`, which is the live
    app's model.
  - It was checked against the live app's own replay.
- **Engine v2:** the one-press engine with the cadence bug fixed on 1 Oct 2026. Older figures appear only
  in `timeline`.
- **Development evaluation, all data seen.**

**Files to upload** (all of them, together):

| file | bytes | what it is |
|---|---|---|
| `id_teaching_pack_2026-10-01.json` | 1,099,561 | the pack: every number the page shows (one file; under 3 MB, so not split) |
| `ID_TEACHING_NOTES_2026-10-01.md` | 33,346 | the notes: the prose facts chapter by chapter, with sources |
| `README_ID_TEACHING_PACK.md` | 190,139 | this README: conventions, the selection, the checks, the field guide |
| `check_png/01_rx2_raw_and_map_right.png` | 129,556 | a check plot made from the pack itself |
| `check_png/01_rx2_raw_and_map_wrong.png` | 130,019 | a check plot made from the pack itself |
| `check_png/02_cnn_score_evolution.png` | 42,632 | a check plot made from the pack itself |
| `check_png/03_component_logprobs.png` | 25,835 | a check plot made from the pack itself |
| `check_png/04_confusion_B2.png` | 26,328 | a check plot made from the pack itself |
| `check_png/05_substitution.png` | 22,177 | a check plot made from the pack itself |
| `check_png/06_shuffled_label.png` | 24,490 | a check plot made from the pack itself |
| `check_png/07_conditioning_ablation.png` | 17,447 | a check plot made from the pack itself |
| `check_png/08_ac1_step_rate.png` | 21,702 | a check plot made from the pack itself |

## Names, and a warning about codes

The pack uses names only: PA5, PA1, PA2, PA3, PA4, PA6. **Never use codes.**
- **Identification's old reports** call them P1 to P6 in that order: P1 PA5, P2 PA1, P3 PA2,
  P4 PA3, P5 PA4, P6 PA6.
- **Tracking numbers people differently:** its "P5" is PA2. A code read across the two branches names
  the wrong person.
- **The pack builder refuses** to write a pack that contains a code.

## Conventions

- **Rounding:** numbers are rounded to 4 significant figures, with two exceptions:
  - `walks.<role>.app` holds the live app's own logged values, unrounded, because they were checked;
  - absolute clock times (`press_time_mono_s`, `t_start`, `t_end`) are kept to 1e-6 s.
- **Units** are in the field names (`_s`, `_hz`, `_m_s`, `_pct`, `_ms`, `_dbm`). Times are seconds after
  the walk's press, unless the name says `_mono` (the host's monotonic clock).
- **Arrays** are plain lists, row-major. A heatmap is listed as [rows][columns]: frequency or CSI entry is
  the row and time the column, unless stated otherwise.
- **A result entry** has the fields `value`, `ci_low`, `ci_high`, `n`, `train_sessions`, `test_session`,
  `calibration` (causal, others or none), `scored_set`, `source_file` and `source_commit`.
  - Intervals are 95 %, by bootstrap over participants (10,000 resamples).
  - `value` is a percentage unless the name says otherwise.
- **Partitions:**
  - "to B2" trains on A1, A2, A3 and B1 and tests B2;
  - "to B1" trains on A1, A2, A3 and B2 and tests B1;
  - the walks figures pool both, with each walk scored by the model that never saw its day;
  - leave one session out trains on four sessions and tests the fifth.
- **`provisional`** is false in the final pack.

## The selection rule and how it was applied (`selection`)

**The rule** was committed before any walk-level output was read (PLAN note of 1 Oct 09:54, aa500c3):
1. the commonest confusion on B2's natural walks (`loso_B2_x`, causal), ties to the larger row, then to
   the first recording;
2. the first recording with a right and a wrong walk of that person, in the same direction if possible;
3. the first wrong walk;
4. the right walk whose displayed confidence is closest to the median of all correct B2 natural walks;
5. if no recording qualifies, the next confusion cell.

**How it was applied on engine v2** (re-applied unchanged after the bug fix; PLAN note of 1 Oct 13:37,
db0898b):
- **The tie:** three cells tie at 4 walks: PA2, PA4 and PA5 named as PA1. Their rows are equal
  (10 walks each), and the first recording ranks PA2 first.
- **PA2's cell fails:** none of his 10 B2 natural walks is right on engine v2, so the rule falls back to
  the next cell, **PA4 named as PA1** (`selection.fallbacks`).
- **The recording:** PA4's natural recording, both walks towards the TX (`A_rev`).
- **The wrong walk** is his pass 1 (replay position 151), named PA1 at 0.4405.
- **The right walk** is his pass 7 (position 157), PA4 at 0.4446, which equals the median to 4 figures.

The ranked cells, the median and the branch that decided each choice are in
`selection.confusion_cells_ranked`, `selection.median_conf_correct_b2_natural` and `selection.branches`.
The v1 selection (PA2, before the fix) is kept in the repository as superseded and is not in the pack.

## The two checks (`checks.verification`)

1. **Replay equals live:** B2 streamed through the live app's rig path equals the saved harness decisions
   on **299 of 299** (`n_app`, `decisions_equal`, `ensemble_max_abs_diff` = 0.0).
2. **The worked walks' numbers equal the app's:** see `worked_walk_values`, per walk.
   - **The comparison:** the pack's app-level numbers are the run's own decision records (the npz written
     from the app's decisions), so they are equal exactly.
   - **Against the run's JSON lines log:** the decision, runner-up, direction and calibration count are
     equal. The probabilities, confidence, speed and latency agree to the log's rounding (largest
     difference 4.7e-4, from latency logged to 3 decimals).

## Field guide

Every key path of the pack, with its type or shape and its meaning. Paths under per-person, per-block or
per-link dictionaries are listed once, with a placeholder.

| field | type or shape | meaning |
|---|---|---|
| `schema_version` | str | the pack's format version |
| `generated_at` | str | when the pack was built (SAST) |
| `git_commit` | str | the repository commit the pack was built at |
| `engine_version` | int | 2: engine v1 plus the cadence bug fix (1 Oct 2026); every engine figure in the pack is v2's |
| `engine_version_note` | str | what engine v2 is and where v1's figures went (the timeline, as superseded) |
| `engine_plan_sha256` | str | SHA-256 of runs/identify/engine/PLAN.md at build time |
| `label` | str | the evaluation label (development evaluation, all data seen) |
| `names_note` | str | why names, not codes |
| `models` | object | model name -> the sessions it was trained on |
| `models.loso_B2_x` | object | (part of `models`) |
| `models.loso_B2_x.training_sessions` | array 4 | (part of `models`) |
| `models.loso_B1_x` | object | (part of `models`) |
| `models.loso_B1_x.training_sessions` | array 4 | (part of `models`) |
| `models.loso_A1_x` | object | (part of `models`) |
| `models.loso_A1_x.training_sessions` | array 4 | (part of `models`) |
| `models.loso_A2_x` | object | (part of `models`) |
| `models.loso_A2_x.training_sessions` | array 4 | (part of `models`) |
| `models.loso_A3_x` | object | (part of `models`) |
| `models.loso_A3_x.training_sessions` | array 4 | (part of `models`) |
| `models.deploy_all5_x` | object | (part of `models`) |
| `models.deploy_all5_x.training_sessions` | array 5 | (part of `models`) |
| `selection` | object | the worked-walk selection rule's inputs, ranking, decisions and branches |
| `selection.confusion_cells_ranked` | list of 18 objects | (part of `selection`) |
| `selection.confusion_cells_ranked[]` | object | (part of `selection`) |
| `selection.confusion_cells_ranked[].true` | str | (part of `selection`) |
| `selection.confusion_cells_ranked[].pred` | str | (part of `selection`) |
| `selection.confusion_cells_ranked[].walks` | int | (part of `selection`) |
| `selection.median_conf_correct_b2_natural` | float | (part of `selection`) |
| `selection.fallbacks` | list of 1 objects | (part of `selection`) |
| `selection.fallbacks[]` | object | (part of `selection`) |
| `selection.fallbacks[].cell` | array 2 | (part of `selection`) |
| `selection.fallbacks[].reason` | str | (part of `selection`) |
| `selection.cell_used` | object | (part of `selection`) |
| `selection.cell_used.true` | str | (part of `selection`) |
| `selection.cell_used.pred` | str | (part of `selection`) |
| `selection.cell_used.walks` | int | (part of `selection`) |
| `selection.cell_used.rank` | int | (part of `selection`) |
| `selection.branches` | object | (part of `selection`) |
| `selection.branches.confusion` | str | (part of `selection`) |
| `selection.branches.recording` | str | (part of `selection`) |
| `selection.branches.wrong_walk` | str | (part of `selection`) |
| `selection.branches.right_walk` | str | (part of `selection`) |
| `selection.ties_at_top` | list of 3 objects | (part of `selection`) |
| `selection.ties_at_top[]` | object | (part of `selection`) |
| `selection.ties_at_top[].true` | str | (part of `selection`) |
| `selection.ties_at_top[].pred` | str | (part of `selection`) |
| `selection.recording` | str | (part of `selection`) |
| `selection.recording_index` | int | (part of `selection`) |
| `selection.wrong` | object | (part of `selection`) |
| `selection.wrong.k` | int | (part of `selection`) |
| `selection.wrong.row` | int | (part of `selection`) |
| `selection.wrong.true` | str | (part of `selection`) |
| `selection.wrong.pred` | str | (part of `selection`) |
| `selection.wrong.conf` | float | (part of `selection`) |
| `selection.wrong.path` | str | (part of `selection`) |
| `selection.wrong.t_start` | float | (part of `selection`) |
| `selection.wrong.recording` | str | (part of `selection`) |
| `selection.wrong.rec_index` | int | (part of `selection`) |
| `selection.right` | object | (part of `selection`) |
| `selection.right.k` | int | (part of `selection`) |
| `selection.right.row` | int | (part of `selection`) |
| `selection.right.true` | str | (part of `selection`) |
| `selection.right.pred` | str | (part of `selection`) |
| `selection.right.conf` | float | (part of `selection`) |
| `selection.right.path` | str | (part of `selection`) |
| `selection.right.t_start` | float | (part of `selection`) |
| `selection.right.recording` | str | (part of `selection`) |
| `selection.right.rec_index` | int | (part of `selection`) |
| `selection.built` | str | (part of `selection`) |
| `selection.engine_version` | int | (part of `selection`) |
| `selection.model` | str | (part of `selection`) |
| `selection.replay` | str | (part of `selection`) |
| `selection.note` | str | (part of `selection`) |
| `walks` | object | the two worked walks, keyed 'wrong' and 'right' |
| `walks.<role>` | object | (part of `walks`) |
| `walks.<role>.role` | str | (part of `walks`) |
| `walks.<role>.name` | str | (part of `walks`) |
| `walks.<role>.session` | str | (part of `walks`) |
| `walks.<role>.recording` | str | (part of `walks`) |
| `walks.<role>.pass_index_in_recording` | int | (part of `walks`) |
| `walks.<role>.pace_block` | str | (part of `walks`) |
| `walks.<role>.direction_true` | str | (part of `walks`) |
| `walks.<role>.direction_detected` | str | (part of `walks`) |
| `walks.<role>.press_time_mono_s` | float | (part of `walks`) |
| `walks.<role>.truth_for_teaching_only_never_seen_by_the_model` | object | metre-anchor presses and the end press: animation only; the model never sees them |
| `walks.<role>.truth_for_teaching_only_never_seen_by_the_model.metre_anchor_press_times_s_after_press` | array 6 | (part of `walks.<role>.truth_for_teaching_only_never_seen_by_the_model`) |
| `walks.<role>.truth_for_teaching_only_never_seen_by_the_model.anchor_coords_m` | array 6 x 2 | (part of `walks.<role>.truth_for_teaching_only_never_seen_by_the_model`) |
| `walks.<role>.truth_for_teaching_only_never_seen_by_the_model.end_press_s_after_press` | float | (part of `walks.<role>.truth_for_teaching_only_never_seen_by_the_model`) |
| `walks.<role>.event_timeline` | object | packet arrivals per receiver in 50 ms bins from press - 1 s to the decision + 0.5 s, and the key moments |
| `walks.<role>.event_timeline.bin_start_s_after_press` | array 96 | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.bin_s` | float | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.arrivals_per_bin` | object | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.arrivals_per_bin.RX1` | array 96 | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.arrivals_per_bin.RX2` | array 96 | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.arrivals_per_bin.RX3` | array 96 | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.press_s` | float | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.window_end_s` | float | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.decision_data_complete_s` | float | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.event_timeline.decision_s` | float | (part of `walks.<role>.event_timeline`) |
| `walks.<role>.links` | object | (part of `walks`) |
| `walks.<role>.links.<link>` | object | (part of `walks`) |
| `walks.<role>.links.<link>.raw_amplitude_heatmap_25hz` | array 103 x 75 | [103 CSI entries][75 time bins]: amplitude on the 150 Hz grid averaged to 25 Hz |
| `walks.<role>.links.<link>.subcarrier_mean_50hz` | array 150 | the mean over the 103 entries, at 50 Hz (150 samples) |
| `walks.<role>.links.<link>.rssi_50hz_dbm` | array 150 | RSSI on the grid at 50 Hz |
| `walks.<role>.links.<link>.packets_in_window` | int | (part of `walks`) |
| `walks.<role>.links.<link>.inter_packet_gap_median_ms` | float | median gap between this receiver's packets inside the window (causal clock) |
| `walks.<role>.links.<link>.inter_packet_gap_max_ms` | float | (part of `walks`) |
| `walks.<role>.links.<link>.conditioning` | object | (part of `walks`) |
| `walks.<role>.links.<link>.conditioning.step1_resampled_amplitude` | str | (part of `walks`) |
| `walks.<role>.links.<link>.conditioning.step2_bandpass_4_70hz_rms_heatmap_25hz` | array 103 x 75 | [103][75]: RMS of the 4 to 70 Hz band-passed amplitude per 40 ms bin |
| `walks.<role>.links.<link>.conditioning.step3_pca_explained_variance_pc1_to_pc4` | array 4 | fraction of the band-passed variance in PCs 1 to 4 |
| `walks.<role>.links.<link>.conditioning.step3_pc1_trace_50hz_discarded` | array 150 | PC1 (common-mode power; discarded), every third sample |
| `walks.<role>.links.<link>.conditioning.step3_pc2_to_pc4_traces_50hz` | array 3 x 150 | [3][150]: PCs 2 to 4 (kept), every third sample (display only) |
| `walks.<role>.links.<link>.conditioning.step3_note` | str | (part of `walks`) |
| `walks.<role>.links.<link>.conditioning.step4_stft_magnitude_per_pc` | array 3 x 28 x 53 | [3 PCs][28 freqs][53 frames]: STFT magnitude per kept PC |
| `walks.<role>.links.<link>.conditioning.step5_log_map_minus_mean_cnn_input` | array 28 x 53 | [28 freqs][53 frames]: the CNN's input map |
| `walks.<role>.links.<link>.gait_channel_mean_b08_35_50hz` | array 150 | the 0.8 to 3.5 Hz subcarrier-mean channel at 50 Hz |
| `walks.<role>.links.<link>.gait_channel_autocorrelation_50hz_lags_0_to_2s` | array 101 | its autocorrelation, lags 0 to 2 s at 50 Hz |
| `walks.<role>.links.<link>.bistatic_factor_F` | float | the link's mean projected bistatic factor along line A in this direction |
| `walks.<role>.links.<link>.predicted_torso_hz_press_speed` | float | 2 F v / lambda with v the press speed (a physics reference; press speed is not a model input) |
| `walks.<role>.links.<link>.predicted_torso_hz_wifi_speed` | float | (part of `walks`) |
| `walks.<role>.map_frequency_axis_hz` | array 28 | the 28 map frequencies (Hz) |
| `walks.<role>.map_frame_times_s` | array 53 | the 53 STFT frame centres (s after the press) |
| `walks.<role>.direction` | object | RX2's 10 to 35 Hz log energy per frame, its least-squares slope, and the detected direction |
| `walks.<role>.direction.rx2_log10_energy_10_35hz_per_frame` | array 53 | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.fit_slope_per_frame` | float | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.fit_intercept` | float | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.sign` | str | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.detected` | str | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.true` | str | (part of `walks.<role>.direction`) |
| `walks.<role>.direction.frame_times_s` | array 53 | (part of `walks.<role>.direction`) |
| `walks.<role>.speed` | object | the per-frame torso contour, f_torso, F, lambda and the Wi-Fi speed v = f lambda / (2 F) |
| `walks.<role>.speed.torso_contour_hz_per_frame_rx2` | array 58 | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.f_torso_hz_median` | float | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.F_rx2` | float | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.lambda_m` | float | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.v_wifi_m_s` | float | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.speed_trace_m_s` | array 58 | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.formula` | str | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.press_speed_m_s_not_used` | float | (part of `walks.<role>.speed`) |
| `walks.<role>.speed.contour_frame_times_s` | array 58 | (part of `walks.<role>.speed`) |
| `walks.<role>.gait_features` | object | the 630 gait features: names, families, raw values, and as standardised by the calibration in force |
| `walks.<role>.gait_features.names` | array 630 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.family` | array 630 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.raw` | array 630 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.standardised_by_session_calibration` | array 630 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.standardised_per_path_training` | array 630 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.calibration_in_force` | str | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.resolved_cadence_hz` | float | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.cycle_template_rx2` | array 32 | (part of `walks.<role>.gait_features`) |
| `walks.<role>.gait_features.envelope_cadence_hz` | NoneType | (part of `walks.<role>.gait_features`) |
| `walks.<role>.evidence` | object | (part of `walks`) |
| `walks.<role>.evidence.components` | dict over rf, rf_prior, rf_pace_prior, et_pace_prior, lda_pace_prior, cnn, cnn_prior, cnn_perlink_prior | each of the 8 components' six log-probabilities and probabilities |
| `walks.<role>.evidence.components.<key>` | object | (part of `walks.<role>.evidence.components`) |
| `walks.<role>.evidence.components.<key>.logp` | array 6 | (part of `walks.<role>.evidence.components`) |
| `walks.<role>.evidence.components.<key>.p` | array 6 | (part of `walks.<role>.evidence.components`) |
| `walks.<role>.evidence.sum_logp` | array 6 | (part of `walks`) |
| `walks.<role>.evidence.ensemble_logp` | array 6 | (part of `walks`) |
| `walks.<role>.evidence.ensemble_probability` | array 6 | (part of `walks`) |
| `walks.<role>.evidence.displayed_confidence` | array 6 | (part of `walks`) |
| `walks.<role>.evidence.argmax` | str | (part of `walks`) |
| `walks.<role>.evidence.runner_up` | str | (part of `walks`) |
| `walks.<role>.evidence.margin_log_units` | float | ensemble log-probability of the top minus the runner-up |
| `walks.<role>.evidence.cnn_evolution` | object | each CNN component's per-window log-probabilities and running mean, by window centre time |
| `walks.<role>.evidence.cnn_evolution.window_centre_s` | array 5 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn` | object | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn.per_window_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn.running_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_prior` | object | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_prior.per_window_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_prior.running_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_perlink_prior` | object | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_perlink_prior.per_window_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.cnn_evolution.cnn_perlink_prior.running_logp` | array 5 x 6 | (part of `walks.<role>.evidence.cnn_evolution`) |
| `walks.<role>.evidence.classes_order` | array 6 | (part of `walks`) |
| `walks.<role>.evidence.note` | str | (part of `walks`) |
| `walks.<role>.drivers` | object | diagnostics, not causes: forest importances (global) with this walk's values; LDA coef x z contributions |
| `walks.<role>.drivers.rf` | list of 20 objects | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf[]` | object | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf[].feature` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf[].importance` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf[].this_walk_raw` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_prior` | list of 20 objects | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_prior[]` | object | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_prior[].feature` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_prior[].importance` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_prior[].this_walk_raw` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_pace_prior` | list of 20 objects | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_pace_prior[]` | object | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_pace_prior[].feature` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_pace_prior[].importance` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.rf_pace_prior[].this_walk_raw` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.et_pace_prior` | list of 20 objects | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.et_pace_prior[]` | object | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.et_pace_prior[].feature` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.et_pace_prior[].importance` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.et_pace_prior[].this_walk_raw` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions` | dict over PA1, PA4 | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>` | list of 15 objects | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>[]` | object | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>[].feature` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>[].contribution` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>[].z` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.lda_pace_prior_contributions.<key>[].coef` | float | (part of `walks.<role>.drivers`) |
| `walks.<role>.drivers.note` | str | (part of `walks.<role>.drivers`) |
| `walks.<role>.substitution` | object | this walk's slot given its donor's radio: the donor, the swapped decision, and the decision with the rebuilt pool |
| `walks.<role>.substitution.donor` | str | (part of `walks.<role>.substitution`) |
| `walks.<role>.substitution.donor_own_decision` | str | (part of `walks.<role>.substitution`) |
| `walks.<role>.substitution.swapped_decision` | str | (part of `walks.<role>.substitution`) |
| `walks.<role>.substitution.swapped_confidence` | float | (part of `walks.<role>.substitution`) |
| `walks.<role>.substitution.rebuilt_pool_decision` | str | (part of `walks.<role>.substitution`) |
| `walks.<role>.app` | object | the live app's own logged values for this walk (rig-path verification run), unrounded |
| `walks.<role>.app.top` | str | (part of `walks.<role>.app`) |
| `walks.<role>.app.runner_up` | str | (part of `walks.<role>.app`) |
| `walks.<role>.app.truth` | str | (part of `walks.<role>.app`) |
| `walks.<role>.app.correct` | bool | (part of `walks.<role>.app`) |
| `walks.<role>.app.ensemble_probability` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | the ensemble's normalised probability per person (what decides) |
| `walks.<role>.app.ensemble_probability.<key>` | float | (part of `walks.<role>.app.ensemble_probability`) |
| `walks.<role>.app.displayed_confidence` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | softmax(sum / 8) per person: the number on screen |
| `walks.<role>.app.displayed_confidence.<key>` | float | (part of `walks.<role>.app.displayed_confidence`) |
| `walks.<role>.app.wifi_speed_m_s` | float | (part of `walks.<role>.app`) |
| `walks.<role>.app.direction_detected` | str | (part of `walks.<role>.app`) |
| `walks.<role>.app.calibration_walks_seen` | int | earlier walks of the day the engine had adapted to (unlabelled) |
| `walks.<role>.app.t_decision_data_s` | float | when the last packet the decision needed arrived (s after the press) |
| `walks.<role>.app.t_decision_s_after_press` | float | when the decision was made: data complete plus measured compute |
| `walks.<role>.app.latency_after_window_s` | float | decision time minus the window's end (press + 3 s) |
| `walks.<role>.app.packet_wait_after_window_s` | float | the deterministic part of the latency: waiting for every receiver's packets |
| `walks.<role>.app.note` | str | (part of `walks.<role>.app`) |
| `model` | object | the model: settings, network tables, components, features, training statistics and chance |
| `model.settings` | object | every fixed parameter of the engine |
| `model.settings.window_T_s` | float | (part of `model.settings`) |
| `model.settings.decision_cap_s` | float | (part of `model.settings`) |
| `model.settings.causal_clock` | object | (part of `model.settings`) |
| `model.settings.causal_clock.trailing_s` | float | (part of `model.settings`) |
| `model.settings.causal_clock.min_frames` | int | (part of `model.settings`) |
| `model.settings.causal_clock.percentile` | float | (part of `model.settings`) |
| `model.settings.causal_clock.wrap` | str | (part of `model.settings`) |
| `model.settings.causal_clock.reboot` | str | (part of `model.settings`) |
| `model.settings.grid_hz` | float | (part of `model.settings`) |
| `model.settings.csi_entries` | int | (part of `model.settings`) |
| `model.settings.unique_subcarriers` | int | (part of `model.settings`) |
| `model.settings.bands_hz` | object | (part of `model.settings`) |
| `model.settings.bands_hz.map_bandpass` | array 2 | (part of `model.settings`) |
| `model.settings.bands_hz.gait_b08_35` | array 2 | (part of `model.settings`) |
| `model.settings.bands_hz.b03_2` | array 2 | (part of `model.settings`) |
| `model.settings.bands_hz.full` | array 2 | (part of `model.settings`) |
| `model.settings.bands_hz.direction_energy` | array 2 | (part of `model.settings`) |
| `model.settings.pca_rule` | str | (part of `model.settings`) |
| `model.settings.stft` | object | (part of `model.settings`) |
| `model.settings.stft.window_samples` | int | (part of `model.settings`) |
| `model.settings.stft.overlap` | int | (part of `model.settings`) |
| `model.settings.stft.hop_samples` | int | (part of `model.settings`) |
| `model.settings.stft.nfft` | int | (part of `model.settings`) |
| `model.settings.stft.bin_hz` | float | (part of `model.settings`) |
| `model.settings.stft.frames_per_s` | float | (part of `model.settings`) |
| `model.settings.map_bins` | object | (part of `model.settings`) |
| `model.settings.map_bins.count` | int | (part of `model.settings`) |
| `model.settings.map_bins.from_hz` | float | (part of `model.settings`) |
| `model.settings.map_bins.to_hz` | float | (part of `model.settings`) |
| `model.settings.log_rule` | str | (part of `model.settings`) |
| `model.settings.cnn_window` | object | (part of `model.settings`) |
| `model.settings.cnn_window.frames` | int | (part of `model.settings`) |
| `model.settings.cnn_window.hop_frames` | int | (part of `model.settings`) |
| `model.settings.cnn_window.seconds` | float | (part of `model.settings`) |
| `model.settings.calibration_thresholds` | object | (part of `model.settings`) |
| `model.settings.calibration_thresholds.feature_standardisation_min_windows` | int | (part of `model.settings`) |
| `model.settings.calibration_thresholds.adabn_min_windows` | int | (part of `model.settings`) |
| `model.settings.fusion` | str | (part of `model.settings`) |
| `model.settings.displayed_confidence` | str | (part of `model.settings`) |
| `model.settings.lambda_m` | float | (part of `model.settings`) |
| `model.settings.F_min_for_speed` | float | (part of `model.settings`) |
| `model.settings.node_positions_m` | object | (part of `model.settings`) |
| `model.settings.node_positions_m.identification_layout` | object | (part of `model.settings`) |
| `model.settings.node_positions_m.identification_layout.TX` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.identification_layout.RX1` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.identification_layout.RX2` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.identification_layout.RX3` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.tracking_layout_rx2_home` | object | (part of `model.settings`) |
| `model.settings.node_positions_m.tracking_layout_rx2_home.TX` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.tracking_layout_rx2_home.RX1` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.tracking_layout_rx2_home.RX2` | array 2 | (part of `model.settings`) |
| `model.settings.node_positions_m.tracking_layout_rx2_home.RX3` | array 2 | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout` | object | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX1` | object | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX1.away` | float | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX1.towards` | float | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX2` | object | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX2.away` | float | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX2.towards` | float | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX3` | object | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX3.away` | float | (part of `model.settings`) |
| `model.settings.F_along_line_a_identification_layout.RX3.towards` | float | (part of `model.settings`) |
| `model.cnn_3link` | object | the 3-link CNN layer by layer with parameter counts |
| `model.cnn_3link.input` | str | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers` | list of 12 objects | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers[]` | object | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers[].layer` | str | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers[].output_shape` | str | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers[].parameters` | int | (part of `model.cnn_3link`) |
| `model.cnn_3link.layers[].how_the_count_arises` | str | (part of `model.cnn_3link`) |
| `model.cnn_3link.total_from_table` | int | (part of `model.cnn_3link`) |
| `model.cnn_3link.total_from_the_network` | int | (part of `model.cnn_3link`) |
| `model.cnn_1link` | object | the 1-link CNN |
| `model.cnn_1link.input` | str | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers` | list of 12 objects | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers[]` | object | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers[].layer` | str | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers[].output_shape` | str | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers[].parameters` | int | (part of `model.cnn_1link`) |
| `model.cnn_1link.layers[].how_the_count_arises` | str | (part of `model.cnn_1link`) |
| `model.cnn_1link.total_from_table` | int | (part of `model.cnn_1link`) |
| `model.cnn_1link.total_from_the_network` | int | (part of `model.cnn_1link`) |
| `model.saved_state_dict_totals` | object | parameter totals read from the saved weights |
| `model.saved_state_dict_totals.cnn3` | int | (part of `model.saved_state_dict_totals`) |
| `model.saved_state_dict_totals.cnn_link0` | int | (part of `model.saved_state_dict_totals`) |
| `model.cnn_training` | object | the CNNs' training recipe: optimiser, steps, batch, sampling, augmentation and seeds |
| `model.cnn_training.optimiser` | str | (part of `model.cnn_training`) |
| `model.cnn_training.steps` | int | (part of `model.cnn_training`) |
| `model.cnn_training.batch` | int | (part of `model.cnn_training`) |
| `model.cnn_training.sampling` | str | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation` | object | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation.time_mask_max` | int | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation.freq_mask_max` | int | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation.log_gain_sd` | float | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation.link_drop_p` | float | (part of `model.cnn_training`) |
| `model.cnn_training.augmentation.noise_sd` | float | (part of `model.cnn_training`) |
| `model.cnn_training.seeds` | array 3 | (part of `model.cnn_training`) |
| `model.components` | dict over rf, rf_prior, rf_pace_prior, et_pace_prior, lda_pace_prior, cnn, cnn_prior, cnn_perlink_prior | the eight components, each in one line |
| `model.components.<key>` | str | (part of `model.components`) |
| `model.lda_fitted_shrinkage_per_class_loso_B2` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | Ledoit-Wolf shrinkage per class |
| `model.lda_fitted_shrinkage_per_class_loso_B2.<key>` | float | (part of `model.lda_fitted_shrinkage_per_class_loso_B2`) |
| `model.features_630_by_family` | object | how many of the 630 gait features are in each family (rhythm, Doppler contours, cycle templates, spectral shape, wavelets, modulation, cadence) |
| `model.features_630_by_family.cad` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.dop` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.mod` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.rhy` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.spec` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.tplacf` | int | (part of `model.features_630_by_family`) |
| `model.features_630_by_family.wav` | int | (part of `model.features_630_by_family`) |
| `model.training` | object | per-session, per-person passes and CNN windows, class balance, training time and seeds |
| `model.training.loso_B2` | object | (part of `model.training`) |
| `model.training.loso_B2.model` | str | (part of `model.training`) |
| `model.training.loso_B2.passes_total` | int | (part of `model.training`) |
| `model.training.loso_B2.passes_per_session_per_person` | dict over A1, A2, A3, B1 | (part of `model.training`) |
| `model.training.loso_B2.passes_per_session_per_person.<key>` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.loso_B2.passes_per_session_per_person.<key>.<key>` | int | (part of `model.training`) |
| `model.training.loso_B2.cnn_windows_per_session_per_person` | dict over A1, A2, A3, B1 | (part of `model.training`) |
| `model.training.loso_B2.cnn_windows_per_session_per_person.<key>` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.loso_B2.cnn_windows_per_session_per_person.<key>.<key>` | int | (part of `model.training`) |
| `model.training.loso_B2.class_balance_passes` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.loso_B2.class_balance_passes.<key>` | int | (part of `model.training`) |
| `model.training.loso_B2.training_seconds` | float | (part of `model.training`) |
| `model.training.loso_B2.seeds` | array 3 | (part of `model.training`) |
| `model.training.loso_B2.cnn_steps` | int | (part of `model.training`) |
| `model.training.loso_B2.device` | str | (part of `model.training`) |
| `model.training.loso_B2.built` | str | (part of `model.training`) |
| `model.training.loso_B2.feature_retraining_seconds_v2` | float | (part of `model.training`) |
| `model.training.loso_B2.feature_components` | str | (part of `model.training`) |
| `model.training.loso_B2.cnn_components` | str | (part of `model.training`) |
| `model.training.deploy_all5` | object | (part of `model.training`) |
| `model.training.deploy_all5.model` | str | (part of `model.training`) |
| `model.training.deploy_all5.passes_total` | int | (part of `model.training`) |
| `model.training.deploy_all5.passes_per_session_per_person` | dict over A1, A2, A3, B1, B2 | (part of `model.training`) |
| `model.training.deploy_all5.passes_per_session_per_person.<key>` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.deploy_all5.passes_per_session_per_person.<key>.<key>` | int | (part of `model.training`) |
| `model.training.deploy_all5.cnn_windows_per_session_per_person` | dict over A1, A2, A3, B1, B2 | (part of `model.training`) |
| `model.training.deploy_all5.cnn_windows_per_session_per_person.<key>` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.deploy_all5.cnn_windows_per_session_per_person.<key>.<key>` | int | (part of `model.training`) |
| `model.training.deploy_all5.class_balance_passes` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `model.training`) |
| `model.training.deploy_all5.class_balance_passes.<key>` | int | (part of `model.training`) |
| `model.training.deploy_all5.training_seconds` | float | (part of `model.training`) |
| `model.training.deploy_all5.seeds` | array 3 | (part of `model.training`) |
| `model.training.deploy_all5.cnn_steps` | int | (part of `model.training`) |
| `model.training.deploy_all5.device` | str | (part of `model.training`) |
| `model.training.deploy_all5.built` | str | (part of `model.training`) |
| `model.training.deploy_all5.feature_retraining_seconds_v2` | float | (part of `model.training`) |
| `model.training.deploy_all5.feature_components` | str | (part of `model.training`) |
| `model.training.deploy_all5.cnn_components` | str | (part of `model.training`) |
| `model.chance_pct` | object | chance for every measure |
| `model.chance_pct.single_walk` | float | (part of `model.chance_pct`) |
| `model.chance_pct.top_2` | float | (part of `model.chance_pct`) |
| `model.chance_pct.household_2` | float | (part of `model.chance_pct`) |
| `model.chance_pct.household_3` | float | (part of `model.chance_pct`) |
| `model.chance_pct.household_4` | float | (part of `model.chance_pct`) |
| `model.chance_pct.household_5` | float | (part of `model.chance_pct`) |
| `model.chance_pct.household_6` | float | (part of `model.chance_pct`) |
| `results` | object | every results table; each entry is a result entry (see Conventions) |
| `results.headline` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results`) |
| `results.headline.<key>` | object | (part of `results`) |
| `results.headline.<key>.value` | float | (part of `results`) |
| `results.headline.<key>.ci_low` | float | (part of `results`) |
| `results.headline.<key>.ci_high` | float | (part of `results`) |
| `results.headline.<key>.n` | int | (part of `results`) |
| `results.headline.<key>.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.headline.<key>.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.headline.<key>.test_session` | str | (part of `results`) |
| `results.headline.<key>.calibration` | str | (part of `results`) |
| `results.headline.<key>.scored_set` | str | (part of `results`) |
| `results.headline.<key>.source_file` | str | (part of `results`) |
| `results.headline.<key>.source_commit` | str | (part of `results`) |
| `results.headline.<key>.to_B2_pct` | float | (part of `results`) |
| `results.headline.<key>.to_B1_pct` | float | (part of `results`) |
| `results.component_families` | object | the CNN components alone, the feature components alone and all eight, natural walks (information) |
| `results.component_families.cnn_only` | object | (part of `results.component_families`) |
| `results.component_families.cnn_only.value` | float | (part of `results.component_families`) |
| `results.component_families.cnn_only.ci_low` | float | (part of `results.component_families`) |
| `results.component_families.cnn_only.ci_high` | float | (part of `results.component_families`) |
| `results.component_families.cnn_only.n` | int | (part of `results.component_families`) |
| `results.component_families.cnn_only.train_sessions` | dict over to B2, to B1 | (part of `results.component_families`) |
| `results.component_families.cnn_only.train_sessions.<key>` | array 4 | (part of `results.component_families`) |
| `results.component_families.cnn_only.test_session` | str | (part of `results.component_families`) |
| `results.component_families.cnn_only.calibration` | str | (part of `results.component_families`) |
| `results.component_families.cnn_only.scored_set` | str | (part of `results.component_families`) |
| `results.component_families.cnn_only.source_file` | str | (part of `results.component_families`) |
| `results.component_families.cnn_only.source_commit` | str | (part of `results.component_families`) |
| `results.component_families.cnn_only.to_B2_pct` | float | (part of `results.component_families`) |
| `results.component_families.cnn_only.to_B1_pct` | float | (part of `results.component_families`) |
| `results.component_families.cnn_only.components` | array 3 | (part of `results.component_families`) |
| `results.component_families.features_only` | object | (part of `results.component_families`) |
| `results.component_families.features_only.value` | float | (part of `results.component_families`) |
| `results.component_families.features_only.ci_low` | float | (part of `results.component_families`) |
| `results.component_families.features_only.ci_high` | float | (part of `results.component_families`) |
| `results.component_families.features_only.n` | int | (part of `results.component_families`) |
| `results.component_families.features_only.train_sessions` | dict over to B2, to B1 | (part of `results.component_families`) |
| `results.component_families.features_only.train_sessions.<key>` | array 4 | (part of `results.component_families`) |
| `results.component_families.features_only.test_session` | str | (part of `results.component_families`) |
| `results.component_families.features_only.calibration` | str | (part of `results.component_families`) |
| `results.component_families.features_only.scored_set` | str | (part of `results.component_families`) |
| `results.component_families.features_only.source_file` | str | (part of `results.component_families`) |
| `results.component_families.features_only.source_commit` | str | (part of `results.component_families`) |
| `results.component_families.features_only.to_B2_pct` | float | (part of `results.component_families`) |
| `results.component_families.features_only.to_B1_pct` | float | (part of `results.component_families`) |
| `results.component_families.features_only.components` | array 5 | (part of `results.component_families`) |
| `results.component_families.all_eight` | object | (part of `results.component_families`) |
| `results.component_families.all_eight.value` | float | (part of `results.component_families`) |
| `results.component_families.all_eight.ci_low` | float | (part of `results.component_families`) |
| `results.component_families.all_eight.ci_high` | float | (part of `results.component_families`) |
| `results.component_families.all_eight.n` | int | (part of `results.component_families`) |
| `results.component_families.all_eight.train_sessions` | dict over to B2, to B1 | (part of `results.component_families`) |
| `results.component_families.all_eight.train_sessions.<key>` | array 4 | (part of `results.component_families`) |
| `results.component_families.all_eight.test_session` | str | (part of `results.component_families`) |
| `results.component_families.all_eight.calibration` | str | (part of `results.component_families`) |
| `results.component_families.all_eight.scored_set` | str | (part of `results.component_families`) |
| `results.component_families.all_eight.source_file` | str | (part of `results.component_families`) |
| `results.component_families.all_eight.source_commit` | str | (part of `results.component_families`) |
| `results.component_families.all_eight.to_B2_pct` | float | (part of `results.component_families`) |
| `results.component_families.all_eight.to_B1_pct` | float | (part of `results.component_families`) |
| `results.component_families.all_eight.components` | str | (part of `results.component_families`) |
| `results.component_families.note` | str | (part of `results.component_families`) |
| `results.confusion_B2` | object | [true][predicted] counts on B2's natural walks (names in rows_true_cols_predicted) |
| `results.confusion_B2.rows_true_cols_predicted` | array 6 | (part of `results.confusion_B2`) |
| `results.confusion_B2.matrix` | array 6 x 6 | (part of `results.confusion_B2`) |
| `results.confusion_B1` | object | (part of `results`) |
| `results.confusion_B1.rows_true_cols_predicted` | array 6 | (part of `results`) |
| `results.confusion_B1.matrix` | array 6 x 6 | (part of `results`) |
| `results.confusion_pooled` | object | (part of `results`) |
| `results.confusion_pooled.rows_true_cols_predicted` | array 6 | (part of `results`) |
| `results.confusion_pooled.matrix` | array 6 x 6 | (part of `results`) |
| `results.per_person_natural_pct` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `results`) |
| `results.per_person_natural_pct.<key>` | float | (part of `results`) |
| `results.loso_tracking` | dict over A1, A2, A3, B1, B2, room_A, room_B | (part of `results`) |
| `results.loso_tracking.<key>` | object | (part of `results`) |
| `results.loso_tracking.<key>.value` | float | (part of `results`) |
| `results.loso_tracking.<key>.ci_low` | float | (part of `results`) |
| `results.loso_tracking.<key>.ci_high` | float | (part of `results`) |
| `results.loso_tracking.<key>.n` | int | (part of `results`) |
| `results.loso_tracking.<key>.train_sessions` | array 4 | (part of `results`) |
| `results.loso_tracking.<key>.test_session` | str | (part of `results`) |
| `results.loso_tracking.<key>.calibration` | str | (part of `results`) |
| `results.loso_tracking.<key>.scored_set` | str | (part of `results`) |
| `results.loso_tracking.<key>.source_file` | str | (part of `results`) |
| `results.loso_tracking.<key>.source_commit` | str | (part of `results`) |
| `results.pace_confound` | object | S0 (press speed), S_wifi (Wi-Fi speed), the engine without pace, and paired differences by block |
| `results.pace_confound.S0_press_speed` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S0_press_speed.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.S_wifi.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S0.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_minus_S_wifi.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>` | object | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.value` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.ci_low` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.ci_high` | float | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.n` | int | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.train_sessions.<key>` | array 4 | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.test_session` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.calibration` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.scored_set` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.source_file` | str | (part of `results.pace_confound`) |
| `results.pace_confound.engine_without_pace_minus_S_wifi.<key>.source_commit` | str | (part of `results.pace_confound`) |
| `results.pace_confound.note` | str | (part of `results.pace_confound`) |
| `results.no_same_day_adaptation` | object | (part of `results`) |
| `results.no_same_day_adaptation.walks` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>` | object | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.walks.<key>.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>` | object | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.engine_minus_cal_none.<key>.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_A.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_room_B.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_A.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.cal_none_room_B.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_A.source_commit` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B` | object | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.value` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.ci_low` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.ci_high` | float | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.n` | int | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.train_sessions` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.test_session` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.calibration` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.scored_set` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.source_file` | str | (part of `results`) |
| `results.no_same_day_adaptation.loso.adapted_minus_cal_none_room_B.source_commit` | str | (part of `results`) |
| `results.deployment` | object | (part of `results`) |
| `results.deployment.single_top1` | object | (part of `results`) |
| `results.deployment.single_top1.value` | float | (part of `results`) |
| `results.deployment.single_top1.ci_low` | float | (part of `results`) |
| `results.deployment.single_top1.ci_high` | float | (part of `results`) |
| `results.deployment.single_top1.n` | int | (part of `results`) |
| `results.deployment.single_top1.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.single_top1.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.single_top1.test_session` | str | (part of `results`) |
| `results.deployment.single_top1.calibration` | str | (part of `results`) |
| `results.deployment.single_top1.scored_set` | str | (part of `results`) |
| `results.deployment.single_top1.source_file` | str | (part of `results`) |
| `results.deployment.single_top1.source_commit` | str | (part of `results`) |
| `results.deployment.single_top1.chance_pct` | float | (part of `results`) |
| `results.deployment.single_top2` | object | (part of `results`) |
| `results.deployment.single_top2.value` | float | (part of `results`) |
| `results.deployment.single_top2.ci_low` | float | (part of `results`) |
| `results.deployment.single_top2.ci_high` | float | (part of `results`) |
| `results.deployment.single_top2.n` | int | (part of `results`) |
| `results.deployment.single_top2.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.single_top2.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.single_top2.test_session` | str | (part of `results`) |
| `results.deployment.single_top2.calibration` | str | (part of `results`) |
| `results.deployment.single_top2.scored_set` | str | (part of `results`) |
| `results.deployment.single_top2.source_file` | str | (part of `results`) |
| `results.deployment.single_top2.source_commit` | str | (part of `results`) |
| `results.deployment.single_top2.chance_pct` | float | (part of `results`) |
| `results.deployment.round_trip_natural` | object | (part of `results`) |
| `results.deployment.round_trip_natural.value` | float | (part of `results`) |
| `results.deployment.round_trip_natural.ci_low` | float | (part of `results`) |
| `results.deployment.round_trip_natural.ci_high` | float | (part of `results`) |
| `results.deployment.round_trip_natural.n` | int | (part of `results`) |
| `results.deployment.round_trip_natural.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.round_trip_natural.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.round_trip_natural.test_session` | str | (part of `results`) |
| `results.deployment.round_trip_natural.calibration` | str | (part of `results`) |
| `results.deployment.round_trip_natural.scored_set` | str | (part of `results`) |
| `results.deployment.round_trip_natural.source_file` | str | (part of `results`) |
| `results.deployment.round_trip_natural.source_commit` | str | (part of `results`) |
| `results.deployment.round_trip_natural.chance_pct` | float | (part of `results`) |
| `results.deployment.round_trip_all_paces` | object | (part of `results`) |
| `results.deployment.round_trip_all_paces.value` | float | (part of `results`) |
| `results.deployment.round_trip_all_paces.ci_low` | float | (part of `results`) |
| `results.deployment.round_trip_all_paces.ci_high` | float | (part of `results`) |
| `results.deployment.round_trip_all_paces.n` | int | (part of `results`) |
| `results.deployment.round_trip_all_paces.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.round_trip_all_paces.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.round_trip_all_paces.test_session` | str | (part of `results`) |
| `results.deployment.round_trip_all_paces.calibration` | str | (part of `results`) |
| `results.deployment.round_trip_all_paces.scored_set` | str | (part of `results`) |
| `results.deployment.round_trip_all_paces.source_file` | str | (part of `results`) |
| `results.deployment.round_trip_all_paces.source_commit` | str | (part of `results`) |
| `results.deployment.round_trip_all_paces.chance_pct` | float | (part of `results`) |
| `results.deployment.walks_k3` | object | (part of `results`) |
| `results.deployment.walks_k3.value` | float | (part of `results`) |
| `results.deployment.walks_k3.ci_low` | float | (part of `results`) |
| `results.deployment.walks_k3.ci_high` | float | (part of `results`) |
| `results.deployment.walks_k3.n` | int | (part of `results`) |
| `results.deployment.walks_k3.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.walks_k3.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.walks_k3.test_session` | str | (part of `results`) |
| `results.deployment.walks_k3.calibration` | str | (part of `results`) |
| `results.deployment.walks_k3.scored_set` | str | (part of `results`) |
| `results.deployment.walks_k3.source_file` | str | (part of `results`) |
| `results.deployment.walks_k3.source_commit` | str | (part of `results`) |
| `results.deployment.walks_k3.chance_pct` | float | (part of `results`) |
| `results.deployment.walks_k5` | object | (part of `results`) |
| `results.deployment.walks_k5.value` | float | (part of `results`) |
| `results.deployment.walks_k5.ci_low` | float | (part of `results`) |
| `results.deployment.walks_k5.ci_high` | float | (part of `results`) |
| `results.deployment.walks_k5.n` | int | (part of `results`) |
| `results.deployment.walks_k5.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.walks_k5.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.walks_k5.test_session` | str | (part of `results`) |
| `results.deployment.walks_k5.calibration` | str | (part of `results`) |
| `results.deployment.walks_k5.scored_set` | str | (part of `results`) |
| `results.deployment.walks_k5.source_file` | str | (part of `results`) |
| `results.deployment.walks_k5.source_commit` | str | (part of `results`) |
| `results.deployment.walks_k5.chance_pct` | float | (part of `results`) |
| `results.deployment.group_size_2` | object | (part of `results`) |
| `results.deployment.group_size_2.value` | float | (part of `results`) |
| `results.deployment.group_size_2.ci_low` | float | (part of `results`) |
| `results.deployment.group_size_2.ci_high` | float | (part of `results`) |
| `results.deployment.group_size_2.n` | int | (part of `results`) |
| `results.deployment.group_size_2.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.group_size_2.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.group_size_2.test_session` | str | (part of `results`) |
| `results.deployment.group_size_2.calibration` | str | (part of `results`) |
| `results.deployment.group_size_2.scored_set` | str | (part of `results`) |
| `results.deployment.group_size_2.source_file` | str | (part of `results`) |
| `results.deployment.group_size_2.source_commit` | str | (part of `results`) |
| `results.deployment.group_size_2.chance_pct` | float | (part of `results`) |
| `results.deployment.group_size_3` | object | (part of `results`) |
| `results.deployment.group_size_3.value` | float | (part of `results`) |
| `results.deployment.group_size_3.ci_low` | float | (part of `results`) |
| `results.deployment.group_size_3.ci_high` | float | (part of `results`) |
| `results.deployment.group_size_3.n` | int | (part of `results`) |
| `results.deployment.group_size_3.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.group_size_3.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.group_size_3.test_session` | str | (part of `results`) |
| `results.deployment.group_size_3.calibration` | str | (part of `results`) |
| `results.deployment.group_size_3.scored_set` | str | (part of `results`) |
| `results.deployment.group_size_3.source_file` | str | (part of `results`) |
| `results.deployment.group_size_3.source_commit` | str | (part of `results`) |
| `results.deployment.group_size_3.chance_pct` | float | (part of `results`) |
| `results.deployment.group_size_4` | object | (part of `results`) |
| `results.deployment.group_size_4.value` | float | (part of `results`) |
| `results.deployment.group_size_4.ci_low` | float | (part of `results`) |
| `results.deployment.group_size_4.ci_high` | float | (part of `results`) |
| `results.deployment.group_size_4.n` | int | (part of `results`) |
| `results.deployment.group_size_4.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.group_size_4.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.group_size_4.test_session` | str | (part of `results`) |
| `results.deployment.group_size_4.calibration` | str | (part of `results`) |
| `results.deployment.group_size_4.scored_set` | str | (part of `results`) |
| `results.deployment.group_size_4.source_file` | str | (part of `results`) |
| `results.deployment.group_size_4.source_commit` | str | (part of `results`) |
| `results.deployment.group_size_4.chance_pct` | float | (part of `results`) |
| `results.deployment.group_size_5` | object | (part of `results`) |
| `results.deployment.group_size_5.value` | float | (part of `results`) |
| `results.deployment.group_size_5.ci_low` | float | (part of `results`) |
| `results.deployment.group_size_5.ci_high` | float | (part of `results`) |
| `results.deployment.group_size_5.n` | int | (part of `results`) |
| `results.deployment.group_size_5.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.group_size_5.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.group_size_5.test_session` | str | (part of `results`) |
| `results.deployment.group_size_5.calibration` | str | (part of `results`) |
| `results.deployment.group_size_5.scored_set` | str | (part of `results`) |
| `results.deployment.group_size_5.source_file` | str | (part of `results`) |
| `results.deployment.group_size_5.source_commit` | str | (part of `results`) |
| `results.deployment.group_size_5.chance_pct` | float | (part of `results`) |
| `results.deployment.group_size_6` | object | (part of `results`) |
| `results.deployment.group_size_6.value` | float | (part of `results`) |
| `results.deployment.group_size_6.ci_low` | float | (part of `results`) |
| `results.deployment.group_size_6.ci_high` | float | (part of `results`) |
| `results.deployment.group_size_6.n` | int | (part of `results`) |
| `results.deployment.group_size_6.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.deployment.group_size_6.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.deployment.group_size_6.test_session` | str | (part of `results`) |
| `results.deployment.group_size_6.calibration` | str | (part of `results`) |
| `results.deployment.group_size_6.scored_set` | str | (part of `results`) |
| `results.deployment.group_size_6.source_file` | str | (part of `results`) |
| `results.deployment.group_size_6.source_commit` | str | (part of `results`) |
| `results.deployment.group_size_6.chance_pct` | float | (part of `results`) |
| `results.confidence_coverage` | object | accuracy on the most confident walks, who is in each level, and the AUROC |
| `results.confidence_coverage.levels` | dict over 100%, 75%, 50%, 30%, 20% | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>` | object | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.value` | float | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.ci_low` | float | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.ci_high` | float | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.n` | int | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.train_sessions.<key>` | array 4 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.test_session` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.calibration` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.scored_set` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.source_file` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.source_commit` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.walks_per_person` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.walks_per_person.<key>` | int | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.correct_per_person` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.correct_per_person.<key>` | int | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.levels.<key>.lowest_confidence` | float | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc` | object | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.value` | float | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.ci_low` | NoneType | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.ci_high` | NoneType | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.n` | int | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.train_sessions` | dict over to B2, to B1 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.train_sessions.<key>` | array 4 | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.test_session` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.calibration` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.scored_set` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.source_file` | str | (part of `results.confidence_coverage`) |
| `results.confidence_coverage.auroc.source_commit` | str | (part of `results.confidence_coverage`) |
| `results.one_press_cost` | object | the engine against the two-press configuration, paired |
| `results.one_press_cost.natural_walks` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.train_sessions` | dict over to B2, to B1 | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.train_sessions.<key>` | array 4 | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.natural_walks.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.train_sessions` | dict over to B2, to B1 | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.train_sessions.<key>` | array 4 | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.by_block.<key>.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.train_sessions` | dict over to B2, to B1 | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.train_sessions.<key>` | array 4 | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.two_press_natural.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.train_sessions` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_pooled.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.train_sessions` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_A.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.train_sessions` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.tracking_room_B.source_commit` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace` | object | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.value` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.ci_low` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.ci_high` | float | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.n` | int | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.train_sessions` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.test_session` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.calibration` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.scored_set` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.source_file` | str | (part of `results.one_press_cost`) |
| `results.one_press_cost.room_A_without_pace.source_commit` | str | (part of `results.one_press_cost`) |
| `results.T_sensitivity_information` | dict over T2.5, T3.5 | (part of `results`) |
| `results.T_sensitivity_information.<key>` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>` | object | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.value` | float | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.ci_low` | float | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.ci_high` | float | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.n` | int | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.test_session` | str | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.calibration` | str | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.scored_set` | str | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.source_file` | str | (part of `results`) |
| `results.T_sensitivity_information.<key>.<key>.source_commit` | str | (part of `results`) |
| `results.latency_s` | object | (part of `results`) |
| `results.latency_s.all_decisions` | object | (part of `results`) |
| `results.latency_s.all_decisions.after_window_end_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.after_window_end_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.after_window_end_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.after_window_end_s.max` | float | (part of `results`) |
| `results.latency_s.all_decisions.after_recorded_end_press_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.after_recorded_end_press_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.after_recorded_end_press_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.after_recorded_end_press_s.max` | float | (part of `results`) |
| `results.latency_s.all_decisions.wait_for_packets_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.wait_for_packets_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.wait_for_packets_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.wait_for_packets_s.max` | float | (part of `results`) |
| `results.latency_s.all_decisions.extract_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.extract_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.extract_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.extract_s.max` | float | (part of `results`) |
| `results.latency_s.all_decisions.model_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.model_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.model_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.model_s.max` | float | (part of `results`) |
| `results.latency_s.all_decisions.calibration_update_s` | object | (part of `results`) |
| `results.latency_s.all_decisions.calibration_update_s.median` | float | (part of `results`) |
| `results.latency_s.all_decisions.calibration_update_s.p90` | float | (part of `results`) |
| `results.latency_s.all_decisions.calibration_update_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks` | object | (part of `results`) |
| `results.latency_s.identification_walks.after_window_end_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.after_window_end_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.after_window_end_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.after_window_end_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks.after_recorded_end_press_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.after_recorded_end_press_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.after_recorded_end_press_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.after_recorded_end_press_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks.wait_for_packets_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.wait_for_packets_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.wait_for_packets_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.wait_for_packets_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks.extract_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.extract_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.extract_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.extract_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks.model_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.model_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.model_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.model_s.max` | float | (part of `results`) |
| `results.latency_s.identification_walks.calibration_update_s` | object | (part of `results`) |
| `results.latency_s.identification_walks.calibration_update_s.median` | float | (part of `results`) |
| `results.latency_s.identification_walks.calibration_update_s.p90` | float | (part of `results`) |
| `results.latency_s.identification_walks.calibration_update_s.max` | float | (part of `results`) |
| `results.two_press_reference` | object | (part of `results`) |
| `results.two_press_reference.identification_walks_natural` | object | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.value` | float | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.ci_low` | float | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.ci_high` | float | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.n` | int | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.test_session` | str | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.calibration` | str | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.scored_set` | str | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.source_file` | str | (part of `results`) |
| `results.two_press_reference.identification_walks_natural.source_commit` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0` | object | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.value` | float | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.ci_low` | float | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.ci_high` | float | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.n` | int | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.train_sessions` | dict over to B2, to B1 | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.train_sessions.<key>` | array 4 | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.test_session` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.calibration` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.scored_set` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.source_file` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.source_commit` | str | (part of `results`) |
| `results.two_press_reference.fast_lead_over_S0.section` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A` | object | (part of `results`) |
| `results.two_press_reference.loso_room_A.value` | float | (part of `results`) |
| `results.two_press_reference.loso_room_A.ci_low` | float | (part of `results`) |
| `results.two_press_reference.loso_room_A.ci_high` | float | (part of `results`) |
| `results.two_press_reference.loso_room_A.n` | int | (part of `results`) |
| `results.two_press_reference.loso_room_A.train_sessions` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A.test_session` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A.calibration` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A.scored_set` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A.source_file` | str | (part of `results`) |
| `results.two_press_reference.loso_room_A.source_commit` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B` | object | (part of `results`) |
| `results.two_press_reference.loso_room_B.value` | float | (part of `results`) |
| `results.two_press_reference.loso_room_B.ci_low` | float | (part of `results`) |
| `results.two_press_reference.loso_room_B.ci_high` | float | (part of `results`) |
| `results.two_press_reference.loso_room_B.n` | int | (part of `results`) |
| `results.two_press_reference.loso_room_B.train_sessions` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B.test_session` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B.calibration` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B.scored_set` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B.source_file` | str | (part of `results`) |
| `results.two_press_reference.loso_room_B.source_commit` | str | (part of `results`) |
| `results.two_press_reference.note` | str | (part of `results`) |
| `results.physics` | object | identity-blind physics checks |
| `results.physics.torso_hz_rx2` | object | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd` | object | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.value` | float | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.ci_low` | NoneType | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.ci_high` | NoneType | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.n` | int | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.train_sessions` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.test_session` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.calibration` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.scored_set` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.source_file` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.source_commit` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.predicted_hz` | float | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_fwd.spearman` | float | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev` | object | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.value` | float | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.ci_low` | NoneType | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.ci_high` | NoneType | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.n` | int | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.train_sessions` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.test_session` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.calibration` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.scored_set` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.source_file` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.source_commit` | str | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.predicted_hz` | float | (part of `results.physics`) |
| `results.physics.torso_hz_rx2.A_rev.spearman` | float | (part of `results.physics`) |
| `results.physics.direction_detector` | object | (part of `results.physics`) |
| `results.physics.direction_detector.value` | float | (part of `results.physics`) |
| `results.physics.direction_detector.ci_low` | NoneType | (part of `results.physics`) |
| `results.physics.direction_detector.ci_high` | NoneType | (part of `results.physics`) |
| `results.physics.direction_detector.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.train_sessions` | str | (part of `results.physics`) |
| `results.physics.direction_detector.test_session` | str | (part of `results.physics`) |
| `results.physics.direction_detector.calibration` | str | (part of `results.physics`) |
| `results.physics.direction_detector.scored_set` | str | (part of `results.physics`) |
| `results.physics.direction_detector.source_file` | str | (part of `results.physics`) |
| `results.physics.direction_detector.source_commit` | str | (part of `results.physics`) |
| `results.physics.direction_detector.by_group` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.all` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.all.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.all.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.all.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B1` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B1.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B1.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B1.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B2` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B2.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B2.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.B2.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.natural` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.natural.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.natural.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.natural.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.slow` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.slow.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.slow.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.slow.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.fast` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.fast.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.fast.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.fast.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_fwd` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_fwd.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_fwd.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_fwd.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_rev` | object | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_rev.accuracy_pct` | float | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_rev.n` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.A_rev.wrong` | int | (part of `results.physics`) |
| `results.physics.direction_detector.by_group.RULE_detected_used` | bool | (part of `results.physics`) |
| `results.physics.wifi_speed_current` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.nan` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.pearson` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.spearman` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.median_abs_error_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.median_ratio_wifi_over_press` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.wifi_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.press_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_all.distinct_wifi_values` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.nan` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.pearson` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.spearman` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.median_abs_error_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.median_ratio_wifi_over_press` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.wifi_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.press_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_natural.distinct_wifi_values` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.nan` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.pearson` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.spearman` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.median_abs_error_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.median_ratio_wifi_over_press` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.wifi_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.press_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_slow.distinct_wifi_values` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.nan` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.pearson` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.spearman` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.median_abs_error_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.median_ratio_wifi_over_press` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.wifi_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.press_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.identification_fast.distinct_wifi_values` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.nan` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.pearson` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.spearman` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.median_abs_error_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.median_ratio_wifi_over_press` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.wifi_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.press_median_m_s` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_current.tracking_all_information.distinct_wifi_values` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_current.source_file` | str | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator` | object | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.n` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.nan_new` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.pearson_new` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.spearman_new` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.pearson_current` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.median_abs_error_new` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.distinct_values_new` | int | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.all_identification_walks_pearson_new` | float | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.GATE_PASSED` | bool | (part of `results.physics`) |
| `results.physics.wifi_speed_a1_estimator.source_file` | str | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room` | object | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.n` | int | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.torso_10_35` | object | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.torso_10_35.median_ratio` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.torso_10_35.frac_above_2` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.arms_35_55` | object | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.arms_35_55.median_ratio` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.arms_35_55.frac_above_2` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.feet_55_75` | object | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.feet_55_75.median_ratio` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.feet_55_75.frac_above_2` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.limbs_35_75` | object | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.limbs_35_75.median_ratio` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.limbs_35_75.frac_above_2` | float | (part of `results.physics`) |
| `results.physics.limb_bands_rx2_over_empty_room.source_file` | str | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2` | object | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.energy_envelope` | object | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.energy_envelope.step_peak` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.energy_envelope.stride_peak` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.energy_envelope.either` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.gait_band_channel` | object | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.gait_band_channel.step_peak` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.gait_band_channel.stride_peak` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.gait_band_channel.either` | float | (part of `results.physics`) |
| `results.physics.rhythm_visibility_natural_rx2.source_file` | str | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias` | object | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.n_clear` | int | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.fractions_within_10pct` | object | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.fractions_within_10pct.near_0.5` | float | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.fractions_within_10pct.near_1` | float | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.fractions_within_10pct.near_2` | float | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.fractions_within_10pct.elsewhere` | float | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.ratio_percentiles_10_25_50_75_90` | array 5 | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.sentence` | str | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.source_file` | str | (part of `results.physics`) |
| `results.physics.cadence_resolver_bias.note` | str | (part of `results.physics`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2` | object | the resolved step rate on the 180 natural walks' engine windows, before and after the fix, against the energy envelope |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.n` | int | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.cadence_changes_over_5pct` | int | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.frac_changed` | float | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.median_fixed_over_now` | float | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.envelope_clear_walks` | int | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.agree_with_envelope_within_10pct_now` | int | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.agree_with_envelope_within_10pct_fixed` | int | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.ratio_to_envelope_median_now` | float | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.ratio_to_envelope_median_fixed` | float | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.source_file` | str | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.cadence_resolver_engine_windows_v1_and_v2.what` | str | (part of `results.physics.cadence_resolver_engine_windows_v1_and_v2`) |
| `results.physics.clock_causal_vs_whole_file` | object | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.engine_windows_T3.0_at_decision` | object | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.engine_windows_T3.0_at_decision.n_frames` | int | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.engine_windows_T3.0_at_decision.median_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.engine_windows_T3.0_at_decision.p99_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.engine_windows_T3.0_at_decision.max_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.every_frame_at_arrival_0.5s` | object | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.every_frame_at_arrival_0.5s.n_frames` | int | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.every_frame_at_arrival_0.5s.median_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.every_frame_at_arrival_0.5s.p99_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.every_frame_at_arrival_0.5s.max_ms` | float | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.wraps_total` | int | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.reboots_total` | int | (part of `results.physics`) |
| `results.physics.clock_causal_vs_whole_file.source_file` | str | (part of `results.physics`) |
| `results.rejected_candidates` | object | every candidate tried and not adopted |
| `results.rejected_candidates.GS` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.value` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.ci_low` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.ci_high` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.n` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.train_sessions` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.test_session` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.calibration` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.scored_set` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.source_file` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.source_commit` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.GS.decision` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.n` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.nan_new` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.pearson_new` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.spearman_new` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.pearson_current` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.median_abs_error_new` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.distinct_values_new` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.all_identification_walks_pearson_new` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.physics_gate.GATE_PASSED` | bool | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A1.decision` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.value` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.ci_low` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.ci_high` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.n` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.train_sessions` | dict over to B2, to B1 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.train_sessions.<key>` | array 4 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.test_session` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.calibration` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.scored_set` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.source_file` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.source_commit` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A2.decision` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.value` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.ci_low` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.ci_high` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.n` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.train_sessions` | dict over to B2, to B1 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.train_sessions.<key>` | array 4 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.test_session` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.calibration` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.scored_set` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.source_file` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.source_commit` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A3.decision` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4` | object | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.value` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.ci_low` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.ci_high` | float | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.n` | int | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.train_sessions` | dict over to B2, to B1 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.train_sessions.<key>` | array 4 | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.test_session` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.calibration` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.scored_set` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.source_file` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.source_commit` | str | (part of `results.rejected_candidates`) |
| `results.rejected_candidates.A4.decision` | str | (part of `results.rejected_candidates`) |
| `results.label` | str | (part of `results`) |
| `provenance` | list of 17 objects | one row per fitted part or design choice: what it was fitted or chosen on, when, by what rule, file and commit; the flag marks choices made with test results in view |
| `provenance[]` | object | (part of `provenance`) |
| `provenance[].element` | str | (part of `provenance`) |
| `provenance[].fitted_or_chosen_on` | str | (part of `provenance`) |
| `provenance[].date` | str | (part of `provenance`) |
| `provenance[].rule` | str | (part of `provenance`) |
| `provenance[].file` | str | (part of `provenance`) |
| `provenance[].commit` | str | (part of `provenance`) |
| `provenance[].chosen_with_test_results_in_view` | bool | (part of `provenance`) |
| `timeline` | list of 21 objects | every headline figure since 12 September with its status and why it was superseded |
| `timeline[]` | object | (part of `timeline`) |
| `timeline[].date` | str | (part of `timeline`) |
| `timeline[].value_pct` | float | (part of `timeline`) |
| `timeline[].ci` | NoneType | (part of `timeline`) |
| `timeline[].measured` | str | (part of `timeline`) |
| `timeline[].train_test` | str | (part of `timeline`) |
| `timeline[].calibration` | str | (part of `timeline`) |
| `timeline[].status` | str | (part of `timeline`) |
| `timeline[].superseded_why` | str | (part of `timeline`) |
| `timeline[].superseded_by` | NoneType | (part of `timeline`) |
| `timeline[].source` | str | (part of `timeline`) |
| `checks` | object | replay equals live, the substitution test, the shuffled-label control and the conditioning ablation |
| `checks.verification` | object | replay equals live, and the worked walks' numbers equal the app's log |
| `checks.verification.built` | str | (part of `checks.verification`) |
| `checks.verification.path` | str | (part of `checks.verification`) |
| `checks.verification.model` | str | (part of `checks.verification`) |
| `checks.verification.engine_version` | int | (part of `checks.verification`) |
| `checks.verification.training_sessions` | array 4 | (part of `checks.verification`) |
| `checks.verification.device` | str | (part of `checks.verification`) |
| `checks.verification.n_app` | int | (part of `checks.verification`) |
| `checks.verification.n_harness` | int | (part of `checks.verification`) |
| `checks.verification.press_times_equal` | bool | (part of `checks.verification`) |
| `checks.verification.decisions_equal` | int | (part of `checks.verification`) |
| `checks.verification.ensemble_max_abs_diff` | float | (part of `checks.verification`) |
| `checks.verification.PASSED` | bool | (part of `checks.verification`) |
| `checks.verification.jsonl` | str | (part of `checks.verification`) |
| `checks.verification.seconds` | float | (part of `checks.verification`) |
| `checks.verification.worked_walk_values` | object | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong` | object | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.decision_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.runner_up_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.direction_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.calibration_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.max_abs_diff_against_log` | float | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.note` | str | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.wrong.PASSED` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right` | object | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.decision_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.runner_up_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.direction_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.calibration_equal` | bool | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.max_abs_diff_against_log` | float | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.note` | str | (part of `checks.verification`) |
| `checks.verification.worked_walk_values.right.PASSED` | bool | (part of `checks.verification`) |
| `checks.substitution` | object | the substitution test, both calibration variants, per pair |
| `checks.substitution.built` | str | (part of `checks.substitution`) |
| `checks.substitution.model` | str | (part of `checks.substitution`) |
| `checks.substitution.engine_version` | int | (part of `checks.substitution`) |
| `checks.substitution.train_sessions` | array 4 | (part of `checks.substitution`) |
| `checks.substitution.test_session` | str | (part of `checks.substitution`) |
| `checks.substitution.scored_set` | str | (part of `checks.substitution`) |
| `checks.substitution.variant_A` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_A.equals_donor_own_decision` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_A.equals_donor_own_decision.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_A.equals_donor_own_decision.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_A.equals_donor_own_decision.n` | int | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_donor_identity` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_donor_identity.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_donor_identity.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_donor_identity.n` | int | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_host_identity` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_host_identity.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_host_identity.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_A.accuracy_vs_host_identity.n` | int | (part of `checks.substitution`) |
| `checks.substitution.variant_B` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_B.equals_donor_own_decision` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_B.equals_donor_own_decision.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_B.equals_donor_own_decision.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_B.equals_donor_own_decision.n` | int | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_donor_identity` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_donor_identity.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_donor_identity.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_donor_identity.n` | int | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_host_identity` | object | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_host_identity.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_host_identity.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.variant_B.accuracy_vs_host_identity.n` | int | (part of `checks.substitution`) |
| `checks.substitution.reference` | object | (part of `checks.substitution`) |
| `checks.substitution.reference.donor_own_accuracy` | object | (part of `checks.substitution`) |
| `checks.substitution.reference.donor_own_accuracy.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.reference.donor_own_accuracy.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.reference.donor_own_accuracy.n` | int | (part of `checks.substitution`) |
| `checks.substitution.reference.host_own_accuracy` | object | (part of `checks.substitution`) |
| `checks.substitution.reference.host_own_accuracy.pct` | float | (part of `checks.substitution`) |
| `checks.substitution.reference.host_own_accuracy.ci95` | array 2 | (part of `checks.substitution`) |
| `checks.substitution.reference.host_own_accuracy.n` | int | (part of `checks.substitution`) |
| `checks.substitution.seconds` | float | (part of `checks.substitution`) |
| `checks.substitution.pairs` | list of 60 objects | (part of `checks.substitution`) |
| `checks.substitution.pairs[]` | object | (part of `checks.substitution`) |
| `checks.substitution.pairs[].host_k` | int | (part of `checks.substitution`) |
| `checks.substitution.pairs[].donor_k` | int | (part of `checks.substitution`) |
| `checks.substitution.pairs[].host` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].donor` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].direction` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].donor_own_decision` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].host_own_decision` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].j_replaced` | int | (part of `checks.substitution`) |
| `checks.substitution.pairs[].A_decision` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].A_confidence` | float | (part of `checks.substitution`) |
| `checks.substitution.pairs[].B_decision` | str | (part of `checks.substitution`) |
| `checks.substitution.pairs[].B_confidence` | float | (part of `checks.substitution`) |
| `checks.shuffled_full` | object | the full engine retrained on permuted labels (to B2) |
| `checks.shuffled_full.built` | str | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.model` | str | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.engine_version` | int | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.train_sessions` | array 4 | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.test_session` | str | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.calibration` | str | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.scored_set` | str | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.natural_accuracy` | object | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.natural_accuracy.pct` | float | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.natural_accuracy.ci95` | array 2 | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.natural_accuracy.n` | int | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.all_b2_windows_accuracy` | object | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.all_b2_windows_accuracy.pct` | float | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.all_b2_windows_accuracy.ci95` | array 2 | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.all_b2_windows_accuracy.n` | int | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.chance_pct` | float | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.predicted_share_natural_pct` | dict over PA5, PA1, PA2, PA3, PA4, PA6 | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.predicted_share_natural_pct.<key>` | float | (part of `checks.shuffled_full`) |
| `checks.shuffled_full.seconds` | float | (part of `checks.shuffled_full`) |
| `checks.shuffled_null` | object | 20 feature-only permutations and the empirical p-value |
| `checks.shuffled_null.built` | str | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.statistic` | str | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.train_sessions` | array 4 | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.test_session` | str | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.real_pct` | float | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.null_pct` | array 20 | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.null_mean_pct` | float | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.null_max_pct` | float | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.p_value` | float | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.n_permutations` | int | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.chance_pct` | float | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.engine_version` | int | (part of `checks.shuffled_null`) |
| `checks.shuffled_null.seconds` | float | (part of `checks.shuffled_null`) |
| `checks.conditioning_ablation` | object | the CNNs retrained without one conditioning step at a time (information only) |
| `checks.conditioning_ablation.built` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.variants` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.variants.V1` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.variants.V2` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.variants.V3` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.variants.V4` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.information_only` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine_version` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.feature_components` | str | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.slow` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.slow.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.slow.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.slow.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.fast` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.fast.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.fast.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.engine.fast.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.slow` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.slow.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.slow.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.slow.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.fast` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.fast.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.fast.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.fast.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural.ABOVE_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V1.variant_minus_engine_natural.EXCLUDES_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.slow` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.slow.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.slow.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.slow.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.fast` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.fast.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.fast.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.fast.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural.ABOVE_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V2.variant_minus_engine_natural.EXCLUDES_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.slow` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.slow.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.slow.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.slow.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.fast` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.fast.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.fast.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.fast.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural.ABOVE_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V3.variant_minus_engine_natural.EXCLUDES_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.slow` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.slow.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.slow.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.slow.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.fast` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.fast.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.fast.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.fast.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural` | object | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural.pct` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural.ci95` | array 2 | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural.n` | int | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural.ABOVE_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.V4.variant_minus_engine_natural.EXCLUDES_ZERO` | bool | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_ablation.seconds` | float | (part of `checks.conditioning_ablation`) |
| `checks.conditioning_energy_identity_blind` | object | RX2's 10 to 35 Hz energy over the empty room, raw and conditioned |
| `checks.conditioning_energy_identity_blind.raw` | object | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.raw.median_ratio` | float | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.raw.frac_above_2` | float | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.raw.n` | int | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.conditioned` | object | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.conditioned.median_ratio` | float | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.conditioned.frac_above_2` | float | (part of `checks.conditioning_energy_identity_blind`) |
| `checks.conditioning_energy_identity_blind.conditioned.n` | int | (part of `checks.conditioning_energy_identity_blind`) |
| `addendum` | object | the addendum's three measurements: AC1 step-rate grid, AC2 same day, AC3 training without paced walks |
| `addendum.status` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.resolver_within_5pct` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.resolver_nan` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.resolver_ratio_median` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.resolver_ratio_min` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.resolver_ratio_max` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.envelope_within_5pct` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.envelope_nan` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.envelope_ratio_median` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.engine_3s_window.n` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.resolver_within_5pct` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.resolver_nan` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.resolver_ratio_median` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.resolver_ratio_min` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.resolver_ratio_max` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.envelope_within_5pct` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.envelope_nan` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.envelope_ratio_median` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.summary.whole_walk.n` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks` | list of 48 objects | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[]` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].step_hz` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].v0_m_s` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].direction` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].walk_s` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window.resolver_hz` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window.resolver_over_true` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window.envelope_hz` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window.envelope_over_true` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].engine_3s_window.envelope_lag_range` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk.resolver_hz` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk.resolver_over_true` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk.envelope_hz` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk.envelope_over_true` | float | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.walks[].whole_walk.envelope_lag_range` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.grid` | object | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.grid.steps_hz` | array 8 | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.grid.speeds_m_s` | array 3 | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.grid.directions` | array 2 | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.source_file` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.engine_version` | int | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.train_test` | str | (part of `addendum`) |
| `addendum.AC1_step_rate_simulated.before_the_fix` | object | the same simulated-walk grid through engine v1: the run that found the cadence bug |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.resolver_within_5pct` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.resolver_nan` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.resolver_ratio_median` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.resolver_ratio_min` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.resolver_ratio_max` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.envelope_within_5pct` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.envelope_nan` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.envelope_ratio_median` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.engine_3s_window.n` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.resolver_within_5pct` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.resolver_nan` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.resolver_ratio_median` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.resolver_ratio_min` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.resolver_ratio_max` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.envelope_within_5pct` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.envelope_nan` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.envelope_ratio_median` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.summary.whole_walk.n` | int | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks` | list of 48 objects | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[]` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].step_hz` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].v0_m_s` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].direction` | str | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].walk_s` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window.resolver_hz` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window.resolver_over_true` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window.envelope_hz` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window.envelope_over_true` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].engine_3s_window.envelope_lag_range` | str | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk` | object | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk.resolver_hz` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk.resolver_over_true` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk.envelope_hz` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk.envelope_over_true` | float | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.walks[].whole_walk.envelope_lag_range` | str | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.source_file` | str | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.before_the_fix.note` | str | (part of `addendum.AC1_step_rate_simulated.before_the_fix`) |
| `addendum.AC1_step_rate_simulated.the_bug` | object | the fault, the fix, worked simulated walks, and the fix's effect on the real walks' resolved step rate |
| `addendum.AC1_step_rate_simulated.the_bug.fault` | str | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.fix` | str | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks` | object | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>` | object | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.name` | str | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.cadence_now_hz` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.cadence_with_fix_hz` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.features_changed_of_630` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.changed_by_family` | object | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.changed_by_family.cad` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.changed_by_family.dop` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.changed_by_family.rhy` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.worked_walks.<role>.changed_by_family.tplacf` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks` | object | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.n` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.cadence_changes_over_5pct` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.frac_changed` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.median_fixed_over_now` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.envelope_clear_walks` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.agree_with_envelope_within_10pct_now` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.agree_with_envelope_within_10pct_fixed` | int | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.ratio_to_envelope_median_now` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.real_natural_walks.ratio_to_envelope_median_fixed` | float | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.the_bug.source_file` | str | (part of `addendum.AC1_step_rate_simulated.the_bug`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption` | object | the fix's effect on the figures, measured by feature re-scoring before Uzayr adopted it |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural.ABOVE_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_natural.EXCLUDES_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>.ABOVE_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.paired_by_block.<key>.EXCLUDES_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.tracking_pooled_change` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_engine` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_engine.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_engine.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_engine.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_with_fix` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_with_fix.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_with_fix.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_with_fix.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired.ABOVE_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_A_paired.EXCLUDES_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_engine` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_engine.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_engine.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_engine.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_with_fix` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_with_fix.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_with_fix.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_with_fix.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired` | object | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired.pct` | float | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired.ci95` | array 2 | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired.n` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired.ABOVE_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.loso_by_room.room_B_paired.EXCLUDES_ZERO` | bool | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.features_changed_windows` | int | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.source_file` | str | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.effect_measured_before_adoption.how` | str | (part of `addendum.AC1_step_rate_simulated.effect_measured_before_adoption`) |
| `addendum.AC1_step_rate_simulated.decision` | str | Uzayr's decision on the bug (1 Oct 2026) |
| `addendum.AC2_same_day_confounded_by_recording` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.label` | str | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days` | dict over B1, B2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.train_sessions` | array 1 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.test_session` | str | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.calibration` | str | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_both` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_both.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_both.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_both.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_away` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_away.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_away.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_away.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_towards` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_towards.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_towards.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.natural_towards.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.slow` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.slow.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.slow.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.slow.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.fast` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.fast.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.fast.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.fast.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.all_paces` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.all_paces.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.all_paces.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_day.all_paces.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_both` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_both.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_both.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_both.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_away` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_away.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_away.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_away.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_towards` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_towards.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_towards.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.natural_towards.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.slow` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.slow.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.slow.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.slow.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.fast` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.fast.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.fast.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.fast.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.all_paces` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.all_paces.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.all_paces.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.cross_day_engine_same_walks.all_paces.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural` | object | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural.pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural.n` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.same_minus_cross_natural.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.n_test_walks` | int | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.days.<key>.chance_pct` | float | (part of `addendum`) |
| `addendum.AC2_same_day_confounded_by_recording.source_file` | str | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.train_sessions` | dict over to B2, to B1 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.train_sessions.<key>` | str | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.test_session` | str | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.calibration` | str | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_paced` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_paced.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_paced.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_paced.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_paced.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_engine.<key>.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S0.<key>.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S0.<key>.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.engine_minus_S_wifi.<key>.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi` | dict over natural_both, natural_away, natural_towards, slow, fast | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>` | object | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>.pct` | float | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>.ci95` | array 2 | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>.n` | int | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>.ABOVE_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.without_minus_S_wifi.<key>.EXCLUDES_ZERO` | bool | (part of `addendum`) |
| `addendum.AC3_training_without_slow_and_fast_walks.source_file` | str | (part of `addendum`) |
| `provisional` | bool | false in the final pack (true only in a drafting build without every result) |
