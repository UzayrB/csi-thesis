# PLAN: identification on the identification walks (written 2026-09-29 15:46 SAST, before any training)

The brief is `reports/BRIEF_ID_WALKS_2026-09-29.md` (verbatim). This plan fixes its definitions, decision
rules and the end-detector grid before any model is trained. It is never edited after its commit; any
change is a dated note at the end. Development evaluation under the direction change of 2026-09-28,
all data seen; not a pre-registered test.

## 1. Scoring set, directions, round trips (checked before this plan: `counts.json`, `counts.md`)

- **Scoring set:** the 419 Room B identification captures in the dev batch's bank
  (`runs/identify/dev/bank`, `kind == "idcap"`), built from the relabelled source:
  - participant P5's day 2 fast `A_fwd` pass 9 closes on the real 5 m press (1.351 m/s);
  - pass 10 (`A_rev`) is excluded.
  Day 1 is B1 and day 2 is B2. No tracking pass is ever scored.
- **Count check:** all 48 cells (day x participant x direction x pace) match the capture plan (day 1:
  natural 10, slow 5, fast 5 per direction; day 2: 5, 5, 5; P5 day 2 fast towards 4). No cell is empty.
- **Directions:** from each pass's tape anchors against the TX at (2.5, -0.5):
  - all 210 `A_fwd` passes run (2.5, 0) to (2.5, 5): **away**;
  - all 209 `A_rev` passes run (2.5, 5) to (2.5, 0): **towards**.
  - RX2 is at (2.0, -0.5), beside the TX.
- **Round trips:** an `A_fwd` pass and the `A_rev` pass immediately after it in the same recording, by
  recording order. There are 209 pairs, 90 of them natural. The one unpaired pass is P5's day 2 fast
  `A_fwd` pass 9, left out of round-trip measures only.

## 2. Folds and training sets

- **Folds:** "to B2" (test B2, reported first) and "to B1" (test B1). The main figure pools both.
- **Training sets** (bank rows; the test day never enters):

  | set | to B2 | to B1 |
  |---|---|---|
  | TR-B | B1 idcap (240) | B2 idcap (179) |
  | TR-B+ | B1 idcap + B1 tracking (360) | B2 idcap + B2 tracking (299) |
  | TR-AB | A1, A2, A3 + all of B1 (720) | A1, A2, A3 + all of B2 (659) |

- **Direction-specific sets (stage B):** TR-B-away, TR-B-towards, TR-AB-away, TR-AB-towards restrict
  only the identification captures to one direction (`A_fwd` or `A_rev`). TR-AB's tracking passes stay
  unchanged.

## 3. The model (frozen: `reports/ID_DEV_FINAL_2026-09-29.md`)

- **Eight components:**
  - `rf`: per-path z;
  - `rf_prior`;
  - `rf_pace_prior`;
  - `et_pace_prior`;
  - `lda_pace_prior`;
  - `cnn` (plain);
  - `cnn_prior` (AdaBN);
  - `cnn_perlink_prior` (one CNN per link, AdaBN, product).
- **Ensemble:** the equal-weight sum of the components' normalised log-probabilities, normalised.
- **Fixed settings:**
  - CNN-v2 at 6,000 steps, seeds 0, 1 and 2;
  - the random forest and extra trees at 300 trees, `random_state` 0;
  - shrinkage LDA;
  - features `U_all_gait`, with press pace as one column in the `_pace_` components.
- **Implementation** (`pipeline/identify/idw_core.py`):
  - the dev code split into train-and-save and apply-with-calibration;
  - the arithmetic is the same as `idx_dev.features`, `idx_dev.prior_standardise`, `idx_dev.cnn` and
    `idx_sel.cnn_both`.
- **Anchor check** (before any result is read):
  - TR-AB to B2 under CAL-causal must reproduce the dev batch's saved `idx_all` B2 log-probabilities
    on the identification passes;
  - exactly for the five feature components;
  - for the CNNs, within GPU (MPS) retraining noise, with decision agreement reported.
- **A direction absent from a training set** (TR-B-away, TR-B-towards):
  - the CNN's normalisation already falls back to the other direction's statistics
    (`idv2_core.norm_stats`);
  - the pass is presented with the direction flag the model was trained with;
  - the per-path feature normalisation falls back to the global training statistics
    (`idmax_eval.prep`).
- **Saving:** every trained component (classifier objects, CNN weights and normalisation statistics,
  training rows) is saved under `runs/identify/idwalks/models/<set>_<fold>/`. Later stages load these
  and never retrain.

## 4. Calibration (test-time, unlabelled)

For each test pass, the calibration rows are:
- **CAL-causal:** the test day's recordings (identification blocks and tracking walks) that started
  before the pass's recording, as the dev batch.
- **CAL-others:** every pass of the test day (identification blocks and tracking walks) whose
  participant differs from the test pass's participant. The label is used only for this exclusion.
- **CAL-none:** no calibration rows.

The dev batch's rules apply to every setting:
- **Feature standardisation:** per path, with the calibration rows when there are at least 10;
  otherwise the global training statistics.
- **AdaBN:** BatchNorm statistics recomputed on the calibration rows' windows when there is at least
  one; otherwise the trained statistics.
- **Unchanged by calibration:** `rf` (per-path z on training statistics) and `cnn` (plain).

## 5. Measures and statistics

- **Headline:** six-way top-1 on the natural passes, both directions pooled, under CAL-others, pooled
  over both folds (n = 180: 120 on B1, 60 on B2).
- **Reported beside it:**
  - CAL-causal and CAL-none;
  - slow and fast;
  - away and towards;
  - per participant;
  - a confusion matrix (the headline configuration).
- **Intervals:** 95 % percentile intervals by bootstrap over participants.
  - 10,000 resamples of the six participants, with replacement, each carrying all its passes in the
    scored set (both folds when pooled).
  - Paired differences resample the per-pass differences the same way. Seed 0.
- **Chance:** 16.67 % unless a measure states its own.
- **Controls beside every headline row:**
  - **S0:** press pace, an LDA on that one number, trained on the training set's identification
    captures only (the other Room B day's, for every set);
  - **no-pace:** the ensemble without `rf_pace_prior`, `et_pace_prior` and `lda_pace_prior`, under
    the same training set and calibration.

## 6. Decision rules

- **Headline training set (stage A).**
  - Order the sets TR-B, TR-B+, TR-AB. Take the first set S such that no larger set S' clearly beats
    it.
  - "Clearly" means that the paired difference S' minus S has a 95 % interval entirely above zero.
    The difference is on the natural passes, both directions, pooled over both folds, under
    CAL-others.
  - TR-AB is taken if reached. All three sets are reported whatever the rule picks.
- **Calibration check (question 4).**
  - The paired difference is CAL-causal minus CAL-others, on the headline measure, for the headline
    training set; it is reported for all three sets.
  - If the headline set's point estimate differs from zero by more than 5 points in either
    direction, the report says plainly that the dev batch's figure depended on the slot structure.
    It then says that the live demo's warm-up walks must come from several people.
- **Direction (stage B, step 3).**
  - The comparison is away minus towards, paired by round trip, on the natural pairs (90), for the
    headline set under CAL-others, pooled over folds.
  - A direction is "better" only if this interval excludes zero. Otherwise the report says "no
    detectable difference at this sample size", with the point estimates, the per-participant
    breakdown and the number of pairs.
- **Start press only (stage E).** Recommend start-only for the demo if the pooled paired change
  (start-only minus two presses, natural passes, headline configuration) has a point estimate of
  -3 points or better and a 95 % interval that includes zero. Otherwise keep both presses.

## 7. Stage D: limb Doppler (identity-blind)

- **Spectra:** the project's established conditioned spectrogram
  (`rehearsal_doppler_check.conditioned_spectrogram`):
  - Hampel;
  - PCs 2 to 4 of the 4 to 70 Hz band;
  - STFT 32 / 24 / 64, power summed over the PCs.
  - The conditioning's 70 Hz edge means the 55 to 75 Hz band measures 55 to 70 Hz; the rest is
    attenuated. This is stated as a limit, not changed.
- **Band energy of a pass:** the median over frames of the power summed over the band's bins. The
  bands are 10 to 35, 35 to 55, 55 to 75 and 35 to 75 Hz.
- **Empty room:** each participant-day's `idpath_d<day>_empty_idspot` recording (RX2 beside the TX; it
  exists for all 12 participant-days), cut into windows of that day's median pass length. The band
  energy is the median over windows, as in `id_dc2_physics.energy`.
- **Ratio:** pass band energy over the same participant-day's empty-room band energy, same link.
  Reported per link, direction and band: the median ratio and the fraction of passes above 2.
  Natural walks only.
- **Predicted positions:** f = 2 F v / lambda, with lambda = 0.123 m, v each pass's press pace, and F
  the link's bistatic factor along line A, averaged over the path
  (`idgp_signal.frame_F`, the RX2 idspot rig).
  - Assumptions: the torso moves at v, the arms at 1.5 to 2 v, and the feet at 2.5 to 3.5 v.
  - Anything above 75 Hz folds back to 150 minus f.
- **Cadence:** RX2's torso contour is the per-frame 50th-percentile energy frequency (4 to 70 Hz), as
  `id29_dc2_score.torso_hz`, per frame.
  - A natural pass shows clear stride periodicity when the mean-removed contour's autocorrelation
    (normalised, lag 0 = 1) has a local maximum of at least 0.30 at a lag between 0.8 and 1.3 s.
  - Passes shorter than 2.6 s are not assessed and are counted separately.
- **Figure:** the mean conditioned spectrogram per direction on RX2.
  - Each natural pass is resampled to 64 time frames, in log power, averaged over passes.
  - The predicted torso, arm and foot bands (median pace) are overlaid and the 75 Hz ceiling marked.
  - Labelled "development evaluation, all data seen".
- **Gate:** the 35 to 75 Hz ratio exceeds 2 in at least half of RX2's natural passes (both days, both
  directions).
  - **If it passes:** the EXPLORATORY arm adds one feature group to `rf`, `rf_prior` and
    `rf_pace_prior` only, and retrains the headline configuration (2 trainings).
    - The group: per link, the log band energies 35 to 55 and 55 to 75 Hz, each relative to the
      pass's 10 to 35 Hz energy.
    - It also takes the mean and SD of the per-frame power-weighted mean frequency within 35 to
      75 Hz.
  - **If it fails:** the report says plainly that the ESP32 data contain no usable limb Doppler at
    this packet rate.
- **Direction physics (stage B, step 4):**
  - RX2's torso frequency (`torso_hz`) against 2 F v / lambda per direction (median ratio and
    Spearman);
  - the band energies per direction;
  - RX2's 10 to 35 Hz energy profile over the walk (thirds of the pass) per direction.

## 8. Stage E: start press only

- **The end detector** (causal, RX2 only, identification's own signal):
  - RX2's amplitude on the 150 Hz grid from the start press.
  - A causal 4th-order 4 to 70 Hz Butterworth (`sosfilt`), run from 2 s before the start press to
    settle.
  - PCA fitted on the first 1.5 s after the start press, keeping PCs 2 to 4 (skew sign rule).
  - Causal STFT frames: 32 samples ending at the frame time, a hop of 8.
  - Energy per frame is the power summed over the 10 to 35 Hz bins and the three PCs.
- **The end:** the first frame time t, from start + 1.5 s, at which the energy stays below f times the
  median energy from the start to t, for every frame in [t, t + h].
  - The search is capped at start + 8 s; if nothing is found, the end is start + 8 s.
  - The decision can be made at t + h.
- **Grid:**
  - f in {0.2, 0.3, 0.4, 0.5};
  - h in {0.25, 0.5, 0.75, 1.0} s (16 combinations).
- **Tuning:** on the training day only, meaning the other Room B day's natural identification walks,
  both directions. The criterion is the smallest mean absolute end-time error; ties go to the smaller
  h, then the smaller f. Never tuned on the test day.
- **Scoring:**
  - the features and maps are computed from [start, detected end] on the full-file clock map, as the
    bank;
  - pace is 5 m over the detected duration;
  - the saved headline models score the passes under CAL-others, with the calibration passes as in
    the bank (two presses);
  - a detected window too short for a CNN window leaves the CNNs uniform for that pass.
- **Reported:**
  - the end-time error (detected minus true end press), median and 90th percentile of the absolute
    error;
  - the paired accuracy change against two presses, per fold and pooled;
  - the decision latency: detected end + h + 5 s clock-map wait + compute, relative to the true end
    press and to the start press.

## 9. Compute, coordination and time

- **Priority settings:** every job runs under `taskpolicy -c utility nice -n 19` with
  `OMP_NUM_THREADS=1`, one at a time, from `runs/identify/idwalks/queue/`. There is no `caffeinate`,
  governor or watchdog.
- **Before each training**, the job checks tracking's root `QUEUE.md` (the brief says
  `reports/QUEUE.md`, but tracking's queue is the root `QUEUE.md`) and the process list. It waits
  while any tracking training process runs (`pipeline.constrained ... train`).
- **The GPU (MPS)** is used when no tracking job is on it; otherwise the CPU is used.
- **Measured under these settings** (15:44):
  - 300 steps take 5.2 s (3-link) and 3.7 s (1-link) on MPS, and 11.3 s on one CPU thread.
  - One training (3 three-link and 9 one-link nets, 6,000 steps each) is about 18 minutes on MPS,
    or about 47 minutes on the CPU.

| stage | work | estimate (MPS) |
|---|---|---|
| D | band energies, cadence, figure (CPU) | 30 min |
| code | `idw_core` and smoke tests | 60 min |
| A | 6 trainings + 3 calibrations each | 2 h 15 min |
| B | 8 trainings + scoring | 2 h 45 min |
| C | from saved log-probabilities | 15 min |
| E | detector tuning, re-extraction, scoring | 45 min |
| gated arm | 2 trainings, if the gate passes | 45 min |
| report | | 45 min |
| **total** | | **about 9 h: done about 01:00 on 30 Sept (MPS); later if the GPU is busy** |

## Dated notes

- **2026-09-29 17:58.** The operator: tracking is done and the machine is identification's. A second lane
  (`runner2.sh`, `jobs2.txt`) now runs beside the first, two jobs at a time. Lane 2 runs without the
  utility clamp, at nice 10 with 4 threads; lane 1 is unchanged. Jobs that depend on the other lane
  wait for it (`wait_for.sh`). No definition, rule or grid changes. Stage A's evaluation (`eval_A`)
  ran straight after stage A, at 17:52, before stage B.
