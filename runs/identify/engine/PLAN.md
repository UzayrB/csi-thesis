# PLAN: the GS confirmation and the one-press identification engine (written 2026-09-30 09:13 SAST, before any training or comparison)

- **The brief** is `reports/BRIEF_ID_ENGINE_2026-09-30.md` (verbatim, committed in ca0408f).
- **What this plan fixes:** the GS rule, every engine parameter, the direction-detector rule, the Wi-Fi
  speed rule, the calibration, the scoring and the reporting rules, before any training, bank build or
  comparison.
- **Never edited after its commit;** changes are dated notes at the end.
- **Status:** development evaluation, all data seen. Every figure is labelled so.
- **Decisions Uzayr confirmed on 2026-09-30 (09:05 to 09:12):**
  - tracking passes are replayed with their route known (line and direction from the recording's
    records), labelled "known route";
  - `pipeline/live/__main__.py` (shared with tracking, not pinned) gets additive lines only.

## 0. Coordination with tracking (brief section 1)

- **Before every training, bank build or replay:** read the root `QUEUE.md` and the process list, and
  never start while a tracking training job runs.
- **The protocol agreed with tracking's session on 2026-09-30:**
  1. identification sends "request: <job>, about N min" (one request may cover a back-to-back block);
  2. tracking replies "paused" at its next job boundary;
  3. identification starts;
  4. identification sends "done" when the job or block ends.

  When tracking announces a latency-measuring replay, identification starts nothing until tracking's
  "done" for it.
- **Every job** runs under `taskpolicy -c utility nice -n 19` with `OMP_NUM_THREADS=1`, one at a time.
  The GPU (MPS) is used only while tracking is not using it (today tracking runs CPU replays only).
- **While waiting:** a check every 30 minutes with the session's scheduler, one line per check in
  `reports/CHECKIN_LOG_ID_ENGINE.md`. No `caffeinate`, governor or watchdog.
- **Only identification's own processes are ever stopped,** by PID.

## 1. Stage 1: the GS confirmation (brief section 3; run once)

**Configurations.**
- **B1:** the audit's bug-fixed final configuration: bank `runs/identify/audit/bank_v2`, columns v2
  (630), maps v2, fusion F0.
- **B1+GS:** B1 with GS exactly as audit item 17 ran it: bank `runs/identify/audit/bank_gs` (each
  packet's amplitudes divided by their mean across the 103 kept subcarriers before resampling), the
  same columns, components, CNN settings and seeds. `bank_gs` already holds all 1,019 passes, so no
  pass is missing and no bank is built.

**Protocol** (the audit's `idz_run.stage_final` loop, unchanged):
- leave one session out over A1, A2, A3, B1, B2; train on the other four sessions (every pass);
- CAL-causal calibration (`calibration_groups(a, te_all, "causal")`: each test recording is
  calibrated on its session's recordings that started before it);
- CNNs at 6,000 steps, seeds 0, 1 and 2;
- scored on each held-out session's 120 tracking passes (600 in all);
- **the baseline** is B1's saved `runs/identify/audit/outputs/final_loso_{A1,A2,A3,B1,B2}_causal.npz`,
  never retrained;
- paired on the same 600 passes.

**Models.**
- **A1, A2, A3:** three new trainings, saved to `runs/identify/engine/models/gs_loso_{A1,A2,A3}`.
- **B1, B2:** the audit's GS models `runs/identify/audit/models/GS_toB1` and `GS_toB2` are reused, not
  retrained. Their training rows equal the leave-one-session-out rows exactly (checked 09:10: 659 and
  720 rows, arrays identical to `final_loso_B1` and `final_loso_B2`), and their configuration is B1+GS.
  This is the same training the loop would run, so it saves two trainings.

**The rule. GS is adopted only if both hold:**
1. the pooled paired gain (B1+GS minus B1, correct = 1, over the 600 tracking passes) has a 95 %
   bootstrap interval over participants (`idw_eval.paired`: 10,000 resamples, seed 0) entirely above
   zero;
2. neither room's accuracy (Room A: 360 passes; Room B: 240) falls by more than 3 points, as a point
   estimate.

**For information only:**
- a bootstrap over the 30 participant-session clusters (10,000 resamples, seed 0);
- the change per session and per participant.

**Procedure.** Run once. The decision is committed as a dated note below before stage 2's bank is
built. If adopted, the engine's signal path includes GS; otherwise it is B1's.

## 2. The engine's fixed parameters (brief section 4)

The engine is `pipeline/identify/engine.py` (with helpers in new `ide_*` files). The evaluation
harness, the bank builder and the live app all call it. Nothing is chosen on a test session.

### 2.1 Window and decision

- **The press** sets t0 (host monotonic clock, the clock of `t_mono`).
- **The window** is [t0, t0 + T] with **T = 3.0 s**.
- **The grid** is `np.arange(t0, t0 + T, 1/150)` (as the bank builds grids).
- **The decision time t_dec** is the earliest frame arrival time tau in (t0, t0 + T + 1.0] at which
  every receiver is complete; if there is none, t_dec = t0 + T + 1.0. A receiver is complete at tau
  when its latest arrived frame (arrival time t_mono <= tau), timed by the causal clock at tau
  (section 2.2), is later than t0 + T.
- **The window's frames** are, per receiver, those arrived by t_dec, timed by the causal clock at
  t_dec. t_dec depends only on the frames' arrival times, so the decision does not depend on how
  frames are batched when pushed (harness or live).

### 2.2 The causal clock map (per receiver)

- **Local time** lt = `local_timestamp` x 1e-6 s.
- **Wraps and reboots.** A backwards jump of more than 1 s is:
  - a **wrap** if the previous raw lt is within 5 s of 2^32 x 1e-6 s and the new raw lt is under 5 s;
    it is unwrapped by adding 2^32 x 1e-6 s, as today;
  - otherwise a **reboot:** the estimate restarts, and frames before the reboot are dropped from that
    receiver's buffer.
- **The offset at time tau** is the 5th percentile of (t_mono minus lt) over the receiver's frames of
  the current epoch that arrived in (tau minus 20 s, tau], when there are at least 20 of them.
- **Corrected time:** t_hat = lt + offset. With fewer than 20 frames, t_hat = t_mono.
- **Frames** are sorted by t_hat.

### 2.3 Signal path (fixed by stage 1)

Per receiver, the amplitude is `raw_access.amplitude_from_frames`, then `id19_bank.KEEP`, then
`id19_featbank.SC` (103 entries). If GS is adopted, each packet is divided by its mean across the 103
(minimum 1e-9) before resampling. Each subcarrier and the RSSI are resampled onto the grid with
`id19_bank._interp_cols`. Then, as the bank:
- **features:** `id19_featbank.pass_features(A, R)`, the model using the 630 v2 columns by name;
- **maps:** `idz_bank.conditioned_map_v2` per link, stacked (3, 28, frames), windows of 34 frames,
  hop 4.

### 2.4 Direction (identity-blind)

- **Input:** the RX2 window amplitude **without GS** (the raw 103 on the grid).
- **Rule:**
  1. `rehearsal_doppler_check.conditioned_spectrogram` (Hampel, PCs 2 to 4 of 4 to 70 Hz, STFT 32/24/64,
     power summed);
  2. per frame, e_k = the power summed over 10 <= f < 35 Hz;
  3. the least-squares slope of log10(e_k + 1e-12) against the frame index;
  4. **slope < 0 is away (`A_fwd`); otherwise towards (`A_rev`).**
- **Check (before any engine training):** its accuracy on all 419 identification walks against the
  recorded path, also by day and block.
- **The rule for the engine:** if the accuracy is at least 95 %, the engine uses the detected
  direction for identification walks. Otherwise the live app uses two trigger keys (one per
  direction), and the evaluation replays the recorded direction as that key. The report states which
  one was used.
- **Tracking passes:** known route (the recorded path).

### 2.5 Wi-Fi speed (identity-blind)

- **Input:** the window amplitude without GS.
- **Layout:** `id_spot` for Room B identification walks (`idgp_contract.RIG_DC2_IDSPOT["primary"]`),
  `home` otherwise (`RIG_ROOM_A`).
- **F per link:** the mean of `id15_factor_map.bistatic_factor` over 101 points along the path's
  segment (`idgp_contract.PATHS`), as `idw_physics.mean_F`.
- **The best link** is the one with the largest F.
- **The formula:** v = f_torso x 0.123 / (2 F), where f_torso = `id29_dc2_score.torso_hz` of the best
  link's window.
- **NaN** if the best F is below 0.3 or f_torso is undefined. NaN is imputed from the training median,
  as any feature.
- **The path** is the detected direction for identification walks (line A's F is the same both ways)
  and the recorded path for tracking passes.
- **Use:** Wi-Fi speed is the single pace column of the three pace components, in training and at test.
  Press speed is kept only for the S0 control.
- **Check:** on the identification walks, Pearson and Spearman correlation with press speed
  (5 m / (end press minus start press)), the median absolute error and the median ratio, by block. This
  is a physics result.

### 2.6 The model

- **The eight components** are unchanged: `rf` (per-path z), `rf_prior`, `rf_pace_prior`,
  `et_pace_prior`, `lda_pace_prior`, `cnn`, `cnn_prior`, `cnn_perlink_prior`.
- **Training** uses `idz_core.train` with columns v2, no layout keying and no frame normalisation;
  CNNs at 6,000 steps, seeds 0, 1 and 2.
- **Training labels:** the true participant, the true path and the true direction.
- **Fusion:** F0, the equal-weight sum of the eight log-probabilities, normalised. The answer is the
  argmax.
- **Displayed confidence:** softmax(sum / 8). It never changes the decision.

### 2.7 Calibration (headline: causal)

- **The calibration set** of a window is **every earlier window of its session**, unlabelled, with the
  engine's own path for each.
- **Session order.** A session's recordings are replayed in the order of their first start press.
- **Thresholds** as now:
  - feature standardisation (`idw_core.Prior.apply`) uses the calibration set when it has at least 10
    windows, otherwise the training statistics;
  - AdaBN (`idv2_core.adabn`) uses it when it has at least 1.
- **Order of work.** The engine computes the calibration state for the next walk after each decision,
  so a decision never waits for it. The calibration set is the same either way.
- **CAL-others** (every window of that session by the other five people) is reported for the
  identification walks as information only; it is not causal.

## 3. The engine bank and the engine models

**The bank.** Each recording in `idx_bank.recordings()` order is replayed through the engine's
extraction:
- frames in arrival order through the causal clock;
- t0 = every recorded pass's start press;
- the window [t0, t0 + T].

Rows are in the dev bank's order (asserted by start press). Each row stores:
- the features and maps;
- the Wi-Fi speed and the detected direction;
- t_dec and the extraction time;
- the labels from the dev bank's metadata: participant, true path, session, kind, block, start and end
  presses, press speed.

**Banks built:** T = 3.0 (`runs/identify/engine/bank_T3.0`), and T = 2.5 and 3.5 for the sensitivity
check only. Tracking passes are included; their window is the first T seconds of the walk.

**Models (under `runs/identify/engine/models/`):**
- **Leave one session out:** `loso_{A1,A2,A3,B1,B2}` on `bank_T3.0`, trained on every pass of the
  other four sessions.
  - The identification-walks folds reuse `loso_B2` ("to B2") and `loso_B1` ("to B1"). TR-AB (Room A
    plus the other Room B day, every pass) is exactly those rows.
- **T sensitivity:** `T2.5_toB2`, `T2.5_toB1`, `T3.5_toB2`, `T3.5_toB1`.
- **Deployment:** `deploy_all5`, on every pass of all five sessions, saved with `manifest.json`. It is
  never used to score anything.

That makes **10 trainings** (the brief's 12, less the two walks folds that equal leave-one-session-out
folds), plus stage 1's 3.

## 4. Scoring (brief section 4.5)

**Every figure comes from a replay of recordings through the engine,** in session order. Only the
start presses are inputs, every other press is ignored, and decisions are causal.
- A test checks that each replay's features and maps equal the engine bank's row for that pass.
- A test checks that the live app's replay decisions equal the harness's.

1. **Identification walks.**
   - **Setup:** `loso_B2` replaying B2 and `loso_B1` replaying B1; the identification-walk windows
     scored, pooled over both folds.
   - **Blocks:** natural (both directions, n 180, the headline), away and towards (by the recorded
     path), slow and fast.
   - **Controls:**
     - S0 (press speed, an LDA trained on the other day's identification walks, `idw_core.s0`), and
       the engine minus S0, paired;
     - the engine without its three pace components.
   - **Per participant,** with the natural confusion matrix.
   - **Deployment measures** (`idw_eval.deployment` on the engine's ensemble): top-2, round trip, 3
     and 5 walks, groups of 2 to 6.
   - **CAL-others,** information only.
2. **Leave one session out:** each `loso_*` model replaying its session, the 120 tracking windows
   scored (known route); per session, Room A (360) and Room B (240).
3. **The one-press cost** (information; never used to decide):
   - the engine minus the two-press configuration (B1, or B1+GS if adopted), CAL-causal, paired on
     the same 180 natural identification walks;
   - if the engine loses more than 5 points, the report says so prominently.
4. **T sensitivity** (information): the T = 2.5 and 3.5 models replaying B2 and B1; natural,
   slow and fast. The engine keeps T = 3.0.
5. **Latency:**
   - **definition:** (t_dec minus (t0 + T)) plus the decision's measured compute (extraction and
     inference, this machine, in replay);
   - **reported:** after the window's end, and after the recorded end press (reporting only), as the
     median, 90th percentile and maximum;
   - **the calibration update's time** is reported separately.

**Statistics.**
- 95 % percentile intervals by bootstrap over participants (10,000 resamples, seed 0).
- Differences are paired on the same passes.
- Chance is 16.67 %.
- Participants are "participant P1" to "P6"; `IC.no_names` is asserted on every written output.

## 5. Stage 3: the live app (brief section 5)

**The mode.**
- **New files:** `pipeline/live/identify_engine.py` (rig consumer, replay, screen text, JSON lines).
- **Wiring:** additive lines in `pipeline/live/__main__.py`:
  - `rig --mode identify` runs the engine;
  - `replay-identify --session <S> [--realtime]` replays a session;
  - `replay-identify` with no session keeps the legacy gate-5 behaviour;
  - `--legacy` keeps the old random forest.
- **Models:** the rig loads `deploy_all5` from its manifest. A replay loads the fold model that never
  saw the replayed day (`loso_B2` for B2, `loso_B1` for B1, `loso_<S>` otherwise). The screen names
  the model.
- **Screen, per walk:**
  - the detected direction;
  - the top identity with its displayed confidence, and the runner-up;
  - chance 1 in 6;
  - Wi-Fi speed;
  - latency;
  - "calibrating: n walks so far" under 10;
  - "closed set: six enrolled people";
  - "REPLAY" in replay.
- **Round trip:** a towards walk whose press is within 15 s of the previous away walk's decision also
  shows the summed round-trip decision.
- **Tally:** the `n` key marks a new walker; until the next `n`, the summed decision over that walker's
  walks is shown as "k walks".
- **Output:** each decision is one JSON line under `runs/live/identify/`; the format is documented in
  `reports/ID_LIVE_INTERFACE.md`.
- **Tests:**
  - an app replay equals the harness's decisions pass for pass;
  - the deployment model loads from its manifest;
  - one press gives exactly one decision;
  - the legacy random-forest mode still gives its old decisions (gate 5).

## 6. Stage 4: cadence (no model change)

- **Walks:** the 55 natural identification walks with a clear envelope rhythm (audit stage 5,
  `runs/identify/audit/stage5/cadence.json`).
- **The ratio:** the bank's resolved cadence divided by the envelope's cadence.
- **Reported:** its distribution, and the fractions within 10 % of 0.5, of 1 and of 2, and elsewhere.
- **Reading:** clustering at 0.5 or 2 means step-against-stride confusion; scatter means the resolver
  is unreliable.
- **One sentence** for the thesis.

## 7. Compute and time estimate (the audit measured about 20 minutes per full training on MPS: 1,183 s)

| step | work | estimate |
|---|---|---|
| stage 1 | 3 trainings + 5 applications + the rule | 75 min |
| checks | the clock check, the direction and Wi-Fi speed checks (CPU) | 20 min |
| engine banks | T = 3.0, 2.5, 3.5 (CPU) | 40 min |
| engine models | 5 leave-one-session-out + 4 T + 1 deployment | 200 min |
| replays | identification walks, leave one session out, T sensitivity, app equality | 90 min |
| code | engine, harness, app, tests | about 5 h, mostly while jobs run |
| stage 4, report, records | | 2 h |

- **Target:** the report on 2026-09-30 at about 22:00 SAST, if the GPU stays free.
- **Timebox:** the brief's day and a half, to about 21:00 on 1 October. If a stage balloons, record
  where it stopped and tell Uzayr.

## 8. Report and freeze (brief section 8)

- **The report:** `reports/ID_FINAL_<finish date>.md`, in the brief's order, ending with
  "Identification is frozen".
- **Dated sections appended to** `reports/ID_ARCHITECTURE_2026-09-29.md` and
  `reports/ID_THESIS_SUMMARY.md`.
- **Commits and pushes** by name only.

## Dated notes

- **2026-09-30 09:25. The banks are built before the GS decision, for both signal paths.**
  - **What:** one pass over the recordings builds six banks: T = 2.5, 3.0 and 3.5 s, each with B1's
    signal path and with GS (`pipeline/identify/ide_bank.py`). The clock check runs in the same pass.
  - **Why:** it saves a second pass over the recordings, and tracking needs the CPU today.
  - **What does not change:**
    - no bank is used, trained on or compared before stage 1's decision is committed here;
    - the unadopted path's banks are never used.
  - **Smoke test** (the first recording only, written to a scratch directory, not under `runs/`):
    - causal minus frozen clock in the windows: median 0.14 ms, maximum 0.63 ms;
    - decisions 30 to 48 ms after the window's end.

- **2026-09-30 09:52. The identity-blind checks (PLAN 2.2, 2.4, 2.5), before any engine training.**
  Source: `runs/identify/engine/checks/checks.json` and `clock.json`.
  - **The banks:** all six banks were built (1,019 passes each, 1,450 s).
  - **The clock**, causal against the frozen centred map:
    - in the T = 3.0 windows at the decision (1,353,844 frames): median 0.12 ms, 99th percentile
      0.51 ms, maximum 1.49 ms;
    - every frame at its own arrival (11.4 million frames): median 0.15 ms, 99th percentile 0.65 ms.
  - **Wraps and reboots:** 0 wraps and 1 reboot (RX2 of one B1 natural recording).
    - The maximum is 4,113 s from that recording's single pre-reboot frame, which the frozen map
      treats as a wrap.
    - Excluding it, the largest difference is about 48 ms, at recording starts (before 20 frames
      exist).
  - **Direction detector: 96.9 % (13 wrong of 419)**, at least 95 %, so **the engine uses the detected
    direction**.
    - By group:

      | B1 | B2 | natural | slow | fast | away | towards |
      |---|---|---|---|---|---|---|
      | 97.1 | 96.7 | 97.8 | 95.0 | 97.5 | 97.6 | 96.2 |

    - Information only: 90.5 % at T = 2.5 and 97.9 % at T = 3.5.
  - **Wi-Fi speed** on the identification walks (no NaN):
    - all walks: Pearson 0.82, Spearman 0.84, median absolute error 0.10 m/s, median ratio 0.97;
    - natural walks: Pearson 0.60, error 0.08 m/s;
    - 14 distinct values: the torso contour moves in 2.34 Hz bins, about 0.15 m/s at F = 0.98.
    - Information: on the tracking passes (home layout, F 0.46 to 0.62) the correlation is 0.10, so
      their Wi-Fi speed carries almost no pace.
  - **Decision wait after the window:** median 31 ms, 90th percentile 48 ms, 3 of 1,019 at the 1 s cap.
    Extraction takes a median 0.17 s.

- **2026-09-30 09:49. Correction:** the note above headed 09:52 was written at 09:49 (clock read after writing).

- **2026-09-30 10:01. Two lanes for the engine's jobs, agreed with tracking.**
  - **The change:** section 0 says one job at a time. From stage 1's decision to about 15:00, two lanes
    run instead:
    - `runs/identify/engine/queue/lane_train.sh`: the 10 trainings in order;
    - `lane_replay.sh`: each session's replay on MPS as soon as its model exists, then `ide_eval` and
      the tests.
  - **Resources:** each lane is one niced single-thread core plus MPS.
  - **Tracking's agreement:** "paused (GPU)" for 10:30 to 15:00, and 4 cores of its own until 12:30.
  - **The hold flag:** both lanes wait on `runs/identify/audit/queue/HOLD_GPU` between jobs, and it is
    set on tracking's request for its quiet-machine replays.
  - **What does not change:** nothing about what is trained, replayed or scored.

- **2026-09-30 10:19. Stage 1's decision: GS is NOT adopted.** Source:
  `runs/identify/engine/stage1/result.json`; run once, 09:19 to 10:19.
  - **Result:**

    | measure | value |
    |---|---|
    | B1 (baseline) | 35.67 [25.00, 44.17] |
    | B1+GS | 33.67 [23.00, 42.50] |
    | pooled paired | **-2.00 [-4.00, +0.50]** |
    | Room A | 39.44 to 36.67 (-2.78) |
    | Room B | 30.00 to 29.17 (-0.83) |

  - **The rule:**
    - condition 1 (interval entirely above zero) **fails**;
    - condition 2 (neither room loses more than 3) holds.
  - **For information:**
    - the participant-session cluster bootstrap gives -2.00 [-9.83, +6.00];
    - per session: A1 -0.83, A2 -7.50, A3 0.00, B1 +0.83, B2 -2.50;
    - per participant, from P1 to P6: -4, -4, 0, -2, +3, -5.
  - **Consequence:**
    - the engine uses B1's signal path: banks `bank_T{2.5,3.0,3.5}`;
    - the `_gs` banks are never used;
    - the two-press reference for the one-press cost is B1 (CAL-causal).
  - **For the thesis:** GS's +10.00 on the identification walks (audit item 17) does not carry to the
    tracking passes.

- **2026-09-30 15:50. The extras brief: every rule fixed before any computation.**
  - **Sources:** `reports/BRIEF_ID_EXTRAS_2026-09-30.md` (verbatim, ab26d24); outputs under
    `runs/identify/final_extras/` and `runs/live/identify/`.
  - **The engine is unfrozen for section 2 only**, then frozen again. From this brief, names may appear in
    new outputs (key: P1 PA5, P2 PA1, P3 PA2, P4 PA3, P5 PA4, P6 PA6).

  **E0. Baseline, scoring and the rule.**
  - **Current best C0:** the engine as frozen (`loso_*`, bank `bank_T3.0`). Its replays
    `runs/identify/engine/replays/loso_{S}_{S}_T3.0` are the baseline.
  - **Scored sets:**
    - natural identification walks pooled over "to B2" (`loso_B2` replaying B2) and "to B1" (n 180);
      also away, towards, slow and fast;
    - the 600 tracking passes (5 folds).
  - **Rule** (brief 2.1; each candidate against the current best, in the order A1, A2, A3, A4). Adopt only
    if all hold:
    1. the paired natural gain has a 95 % interval over participants (10,000 resamples, seed 0) entirely
       above zero;
    2. slow and fast each lose at most 3 points (point estimate);
    3. the 600 tracking passes lose at most 3 points pooled (point estimate).
  - **Feature re-scoring** (A1 to A3; the CNNs are untouched):
    - the five feature components are retrained for all five folds with `idz_core.train`'s feature part
      (same heads, statistics and random states) on the candidate's inputs;
    - each replayed session's windows are then re-scored **in replay order**, with every earlier window
      of the session as calibration, exactly as `engine.Session.classify` does;
    - the replay's saved CNN outputs (`c_cnn`, `c_cnn_prior`, `c_cnn_perlink_prior`) are added,
      then the ensemble is normalised.
    - **Anchor, before any candidate:** with C0's own inputs, re-scoring must reproduce the replays'
      feature components and ensembles.
    - An adopted configuration is verified by full engine replays (brief 2.3).

  **A1. Precise Wi-Fi speed.**
  - **Where:** identification-spot windows only (Room B identification walks: RX2 beside the TX, line A,
    F = 0.98). Every other window keeps the current estimator: `torso_hz` on the best link with its
    F, NaN if F < 0.3.
  - **The empty-room spectrum E(f), from training days only** (brief 2 principle):
    - the `*_empty_idspot` RX2 recordings of the Room B days in the model's training set: "to B2" uses
      B1's six, "to B1" uses B2's six, and Room A folds and `deploy_all5` use all twelve;
    - each recording is cut into consecutive 3 s windows (from 1 s after its start to 1 s before its
      end), each given `rehearsal_doppler_check.conditioned_spectrogram` on raw amplitude;
    - E(f) is the median over all frames of all windows.
  - **Per window:**
    1. P from the same spectrogram of the raw RX2 window;
    2. P_sub = max(P - E, 0) on the ten bins 10 <= f < 35 Hz (11.72 to 32.81 Hz);
    3. per frame, energy e_k = sum of P_sub and centroid c_k = sum(f P_sub) / e_k;
    4. keep frames with e_k above the window's 25th percentile of e (and e_k > 0);
    5. v = median(c_k) x 0.123 / (2 x 0.98); NaN if no frame is kept.
  - **The physics gate:** Pearson(v, press speed) on the 180 natural walks, each walk's v with its fold's
    E. Proceed to the identity test only if it is at least 0.70 (now 0.60).
  - **The candidate:** v replaces the pace column of the three pace components (every fold's rows use
    that fold's E).

  **A2. Speed profile, 9 columns.**
  - **The trace:**
    - identification-spot windows: v_k = c_k x 0.123 / (2 x 0.98) per frame (frames not kept by A1's
      rule are NaN);
    - other windows: the current estimator's per-frame torso contour on the best link x 0.123 / (2 F),
      all NaN if F < 0.3.
    - Frame times are STFT frame centres, (16 + 8k) / 150 s.
  - **The columns:**
    - v at 0.5, 1.0, 1.5, 2.0, 2.5 and 3.0 s, each the median of finite v_k within +-0.25 s;
    - the time of the first finite frame reaching 90 % of the window's maximum;
    - the maximum;
    - the distance: the trapezoid integral of the trace, NaN frames linearly interpolated.
  - **NaN** when fewer than 3 finite frames.
  - **Use:** appended to all five feature components' inputs (after the 630 gait columns, before pace).
    Always computed with A1's estimator, adopted or not.

  **A3. Offset training windows.**
  - **Extra rows:** each pass is also extracted at t0 + 0.15 s and t0 + 0.30 s (3 s windows) by the
    engine's own Extractor, with the current best's features, speed and profile. These are training rows
    only, labelled as the t0 row.
  - **Statistics:** imputation medians, the dead-column test, the per-path z statistics and the
    per-session standardisation are fitted on the t0 rows only, then applied to all rows. The classifiers
    fit on all rows.
  - **Test rows and calibration** are unchanged (t0 only).

  **A4. The lean correction, learned from the training days.**
  - **Inner loop:** for each outer fold, four inner trainings of the full current-best engine, each
    leaving out one of that fold's training sessions. Each held-out inner session is replayed through
    the engine (causal).
    - "to B2": trained on A1, A2, A3, B1 in turn, so the inner held-out sessions are A1, A2, A3, B1.
    - "to B1": the same with B2 in place of B1.
  - **The vector:** m_c = mean over every inner held-out window (identification and tracking) of the
    ensemble probability of c, divided by 1/6. It is written to
    `runs/identify/final_extras/a4/bias_<fold>.json` before the test day's outputs are corrected.
  - **The correction:** log p' = log p - log m, renormalised, on the outer model's replay of the test
    day.
  - **Order of work:**
    - the inner CNN trainings start at once: their CNNs do not depend on A1 to A3, which change only
      feature components;
    - if A1 to A3 adopt anything, the inner feature components are retrained and re-scored as in E0
      before the vectors are computed.
  - **Adoption:**
    - conditions 1 and 2 on the walks folds first;
    - only if both hold, the 12 inner trainings for the Room A folds follow, then condition 3 on the
      600 tracking passes, with every fold corrected by its own vector;
    - adopt only if all three hold.
  - **The deployment vector** comes from the five `loso_*` replays on their own sessions.
  - **Also reported:**
    - the vectors;
    - whether the training-day lean matches the test-day lean (the most over-named person the same or
      not; Spearman between m and the test day's prediction shares);
    - each person's share of predictions before and after;
    - the fraction of changed decisions that went to the uncorrected runner-up.

  **2.3.** Anything adopted enters `engine.py` and the bank extraction. The models are retrained under new
  names (`*_x`), verified by full replays pass for pass, then a re-freeze note follows.

  **2.4. CAL-none (information).**
  - **Setup:** the final engine replayed with adaptation off: feature standardisation on training
    statistics, AdaBN off, so the adapted CNN components use the plain nets.
  - **Implementation:** a harness session that never pools (new file); the engine's decision code is
    unchanged.
  - **Reported:** the blocks and leave-one-session-out, paired against the adapted engine.

  **Section 3. S_wifi.**
  - **The control:** an LDA on one number, the final engine's Wi-Fi speed of the same window, trained on
    the other Room B day's identification walks (all blocks), as S0, and scored on the same test walks.
  - **Reported:** per block, with S0 and chance beside it; the engine minus S_wifi; the engine without
    pace minus S_wifi (paired, bootstrap over participants).

  **Section 4. Coverage.**
  - **The ranking:** the final engine's 180 natural walks (pooled), ranked by the displayed confidence of
    the top identity, descending. Ties are broken by the ensemble's top probability, then by row order.
  - **Levels:** coverage 100, 75, 50, 30 and 20 % = the top ceil(c x 180) walks: 180, 135, 90, 54 and
    36.
  - **Reported:** accuracy with a bootstrap over participants; walks per participant per level; the AUROC
    of the confidence for right against wrong (Mann-Whitney).

  **Section 5. The rig run.**
  - **The source:**
    - records are released in one global order by recorded `t_mono` (ties: RX1, RX2, RX3, then file
      order);
    - each recorded start press is injected as a space-bar key event, processed once stream time reaches
      it;
    - the consumer's `tick` runs after each arrival batch, with the stream time.
  - **The guard:** the training sessions come from a manifest (`training_sessions`, written as a new
    file where missing, from the model's `train_rows.npy` and its bank). It refuses any model trained on
    the streamed session.
  - **Tests:** as brief 5.5, on B2 with the final `loso_B2`. The fake serial port re-encodes each recorded
    frame as a base64 `CSI_DATA` row through the real `SerialReader` and `parse_line`, which stamp
    `t_mono` from a patched per-reader clock set to the recorded time.

  **Section 6.2. The render stretch** (declared before any viewing):
  - B2's six natural identification blocks, in recording order, played at `--speed 1`;
  - every other B2 recording, before and between them, fed at maximum speed without display;
  - the running score counts the displayed walks only. Its final value must equal the final engine's "to
    B2" natural figure: **41.67 % (25 of 60) if section 2 adopts nothing**.

  **Estimate:**
  - A1 to A3: about 3 h, CPU;
  - A4: 8 inner trainings (about 2.7 h, GPU) plus 8 inner replays; 12 plus 12 more only if conditions 1
    and 2 hold;
  - sections 3 to 6: about 4 h;
  - the report: about 1.5 h.
  - Target: about midday on 1 October. Timebox: the brief's one and a half days.

- **2026-09-30 15:58. A clarification before any A-stage result.**
  - **A4's inner loop, if A1 or A2 has been adopted:** an inner training set with no Room B day (the
    A1A2A3 set) has no training-day empty-room spectrum. It uses E = 0 (the estimator without
    subtraction), so nothing is ever taken from a held-out day.
  - **The E0 anchor passed** (`runs/identify/final_extras/anchor.json`). Re-scoring reproduces every
    replay's feature components and ensembles to 5e-14, with 1,019 of 1,019 decisions equal, both with the
    saved models and with the feature components retrained by `ixa_score.train_feat`.

- **2026-09-30 16:03. Brief 5.3: the time base failed, and only the time base was fixed.**
  - **The fault:** the live app's consumer (`pipeline/live/identify_engine.EngineConsumer.tick`) polled
    the engine with the host's `time.monotonic()` instead of the time its caller passes.
    - On the boards the two are the same clock, since `run_capture` ticks with `time.monotonic()`, the
      clock of `t_mono` and of the keys.
    - On a recorded stream they are not: the host clock (1,095,943 s) was far past the stream's
      (830,307 s).
  - **The effect:** every window was decided at the first tick after its press, from the frames present
    then. On B2's first recording, **0 of 10** decisions (and 0 of 10 feature vectors) equalled the
    harness.
  - **Why the speed test alone could not see it:** the error is identical at every replay speed.
  - **The fix:** `tick` polls with its own `now`. The boards' path is unchanged in effect, and the engine
    (`engine.py`) is untouched. Every brief 5.5 test is run after the fix.

- **2026-09-30 16:15. A1 to A3, in order, against C0.** Source: `runs/identify/final_extras/state.json`.
  - **A1: not tested for identity.** Its physics gate gave Pearson **0.697** against the 0.70 bar (the
    current estimator gives 0.604).
    - The estimator is now continuous (179 distinct values on 180 walks) with a median error of
      0.067 m/s.
    - On all 419 identification walks, r = 0.81.
  - **A2 (speed profile): not adopted.**
    - Natural 0.00 [-3.33, +3.33]; slow -0.83, fast 0.00; tracking pooled -0.50.
    - Condition 1 fails.
  - **A3 (offset training rows): not adopted.**
    - Natural -3.33 [-5.56, -1.11]; slow -0.83, fast -3.36; tracking -0.50.
    - Conditions 1 and 2 fail.
  - **The current best stays C0.** A4 is judged against C0, from the inner replays as they are.

- **2026-09-30 18:18. A4, and the engine re-frozen: nothing adopted.** Source: `runs/identify/final_extras/a4/`.
  - **The inner loop:**
    - 7 inner trainings (the A1A2A3 set shared between the two walks folds);
    - 8 inner replays, every window's features equal to the bank (1,379 of 1,379).
  - **The bias vectors** (m, P1 to P6), written before the test days were corrected:

    | fold | P1 | P2 | P3 | P4 | P5 | P6 |
    |---|---|---|---|---|---|---|
    | "to B2" | 0.79 | 1.07 | 0.89 | 0.72 | 1.12 | 1.41 |
    | "to B1" | 1.00 | 1.28 | 0.93 | 0.68 | 1.10 | 1.01 |

  - **The result:** natural -0.56 [-1.67, 0.00]; slow -0.83, fast 0.00. Condition 1 fails, so **not
    adopted**. The Room A inner trainings (condition 3) are not run.
  - **Why it barely acts:** only 5 of 299 (B2) and 4 of 360 (B1) decisions change, all to the uncorrected
    runner-up. The ensemble's product of eight components is too peaked for a factor of 0.7 to 1.4 to
    move it.
  - **Lean match:** "to B2": no (training over-names P6, the test day most names P5; Spearman 0.66).
    "To B1": yes (P2; Spearman 0.37).
  - **Section 2 adopts nothing.**
    - **The engine is frozen again as it stood (C0)**, with the models `loso_*` and `deploy_all5`.
    - Every later figure uses it: the measures, the rig run and the render.

- **2026-10-01 09:54. The teaching-pack brief: the selection rule and the three checks, fixed before any walk-level output
  is read.**
  - **Sources:** `reports/BRIEF_ID_TEACHING_2026-10-01.md` (verbatim, 69fc041); outputs under
    `reports/teaching/` and `runs/identify/teaching/`. **The engine does not change.**

  **S. The two worked walks (brief 2.1).**
  - **Inputs:** B2 replayed by `loso_B2` with causal calibration; its natural identification walks
    (60), from the saved harness replay `runs/identify/engine/replays/loso_B2_B2_T3.0.npz`, whose 299
    decisions the rig run reproduced pass for pass.
  - **Recording order:** `ide_replay.session_recordings("B2")`, the session order by first press.
  - **The rule:**
    1. **The confusion:** the off-diagonal cell (true person, predicted person) with the most walks.
       - Ties go to the larger true-person row total, then to the true person whose natural recording
         comes first.
       - That cell's true person is the worked person; the predicted person is the confused person.
    2. **The recording:** the first recording in order holding at least one walk by that person
       predicted as the confused person and at least one predicted correctly. A recording with both in
       the same direction is preferred, else the first satisfying the rest.
    3. **The wrong walk:** the first walk of that confusion in that recording (by press time).
    4. **The right walk:**
       - the person's correct walk in that recording whose displayed confidence (top identity) is closest
         to the median displayed confidence of all correct B2 natural walks;
       - in the wrong walk's direction if one exists, else any direction;
       - ties go to the earlier walk.
    5. **The branch** that decided each choice is recorded.
    6. **Fallback:** if no recording qualifies, the next confusion cell in the same order, recorded.

  **V. Verification (brief 2.2).**
  - **The run:** B2 is streamed through the rig path (`identify_recorded` with `EngineConsumer`,
    `loso_B2`, speed max, on the harness's device), and every decision is logged.
  - **Check 1:** n of n decisions equal to the saved harness decisions (the same press time, argmax, and
    ensemble to 1e-6).
  - **Check 2:** for the two walks, every exported app-level number equals that run's logged value to
    1e-6: decision, ensemble probabilities, displayed confidence, Wi-Fi speed, direction, calibration
    count and latency.
  - **Latency** is quoted from that run: the packet wait (deterministic) plus the measured compute, which
    varies from run to run.

  **C1. The substitution test (brief 2.4.1).**
  - **Hosts:** the 60 B2 natural walks.
  - **The donor of a host:** the first walk after the host in session order (by press time) that is by
    a different person, in the same recorded direction and in a natural block. If none follows, wrap to
    the start of the session.
  - **The swapped window** is the donor's own engine window placed in the host's slot.
    - Its frames are timed by the donor's own causal clock, so its features, maps, Wi-Fi speed and
      detected direction are those of the donor's bank row.
    - The donor's frames from its press - 1 s to + 4 s contain every frame of that window, and a time
      shift onto the host's press changes no feature.
    - The donor's own clock offset is kept: mixing its frames into the host's clock estimate would
      combine two estimates.
  - **Variant A** (the host's calibration unchanged): the pool is every session window before the host,
    in replay order.
  - **Variant B** (the pool rebuilt as if the donor had walked that slot): the same pool, but the host
    recording's walks before the host (j of them) are replaced by the donor recording's first j walks.
  - **Classification:** `engine.Session.classify` with `set_pool`, `loso_B2`.
  - **Reported, for A and B:**
    - the fraction of swapped decisions equal to the donor's own decision in its own slot;
    - accuracy against the donor's identity and against the host's;
    - intervals by bootstrap over participants (donor's person for donor measures, host's for host
      measures).
  - **The worked walks:** their variant A swapped decisions, with the donor named.

  **C2. The shuffled-label control (brief 2.4.2).**
  - **The full control:**
    - "to B2" (train A1, A2, A3, B1, every pass);
    - labels permuted at row level within each training session (class counts kept), numpy seed 0;
    - the full engine trained by `idz_core.train` (`runs/identify/teaching/models/shuffled_loso_B2`);
    - B2 replayed through the engine; natural accuracy against chance, with its interval.
  - **The null:** seeds 1 to 20 retrain only the five feature components on permuted labels and re-score
    B2 (`ixa_score`, causal). The statistic is the feature-only ensemble (the sum of the five feature
    components) on natural walks.
  - **The p-value:** p = (1 + #null >= real) / 21, against the real feature-only ensemble of `loso_B2`.

  **C3. The conditioning ablation (brief 2.4.3; information only, never adopted).**
  - **The variants:** maps from the same windows (the engine's Extractor), each changing one step:
    1. V1, no band-pass: PCA on the mean-centred raw window;
    2. V2, PCs 1 to 3 kept;
    3. V3, the subcarrier mean of the band-passed window, one channel, instead of PCA;
    4. V4, no log and no mean subtraction (the summed raw STFT magnitude of PCs 2 to 4).
  - **Training:** the three CNN components retrained (`idz_core.train`, parts "cnn", same seeds and
    steps) for "to B2" and "to B1".
  - **Scoring:** in replay order with causal AdaBN, plus the replay's frozen feature components.
    Reported: natural, slow, fast, and paired against the engine.
  - **Identity-blind:** RX2's 10 to 35 Hz energy over the empty room (the training-day empty idspot
    recordings), median ratio and the fraction above 2, on the natural walks, both:
    - raw: the STFT power of the raw subcarrier mean;
    - conditioned: the engine's PCs 2 to 4 of the band-passed window.
  - **No result here changes the engine.**

  **Estimate:**
  - 9 GPU trainings (1 full, 8 CNN-only), about 2.5 h;
  - CPU: the selection, the verification run (about 12 min), C1, the C2 null, the ablation maps and the
    pack;
  - target: this afternoon.

- **2026-10-01 10:32. The teaching-pack addendum: three more measurements, defined before any is run.**
  - **Source:** `reports/BRIEF_ID_TEACHING_ADDENDUM_2026-10-01.md` (verbatim).
  - **Purpose:** information for the write-up; **the engine does not change.** Here "AC1" to "AC3" are the
    addendum's C1 to C3, to keep them apart from the pack's checks C1 to C3.

  **AC1. The step-rate estimator on simulated walks** (CPU; `pipeline/identify/ixt_synth.py`, new).
  - **The walker:** `idz_synth`'s, with its step rate f_s and its speed v0 made parameters:
    - v(t) = v0 (1 - exp(-t / 0.3)) (1 + 0.15 sin(2 pi f_s t)) from standing at the press, stopping at
      5 m;
    - the torso bobs at f_s;
    - the limbs move at f_s / 2 in antiphase.
  - **Away and towards:**
    - away: the torso path length is 1 + 2 F x and the attenuation 1 / (1 + x);
    - towards: 1 + 2 F (5 - x) and 1 / (1 + 5 - x).
  - **Timing:** every frame time and non-CSI field comes from the same real recording `idz_synth` uses.
  - **The path:** the frames enter the engine's own `Extractor` exactly as recorded frames do (amplitude,
    causal clock, the 3 s window from the press, the 150 Hz grid, `pass_features`). No capture files are
    written: the payload is built in memory.
  - **The grid:** f_s in {1.5, 1.6, ..., 2.2} x {away, towards} x v0 in {1.0, 1.2, 1.4}, which is 48 walks.
  - **Per walk:**
    - the resolver: `cad|all|-|-|cadence_hz` / f_s;
    - the envelope cadence / f_s, by the cadence diagnostic's method (`idz_cadence`): RX2's
      `conditioned_spectrogram` power over 10 to 70 Hz per frame, an autocorrelation peak of at least 0.30,
      1 / (step lag) in 0.4 to 0.7 s, else 2 / (stride lag) in 0.8 to 1.4 s.
  - **Also, for information:** the same on the whole walk (the window from the press to 5 m), the span the
    real-walk 0.88 was measured on.
  - **The reading** (the brief's):
    - the resolver within 5 % on the grid while the envelope is not means no bug;
    - otherwise a bug: the line found and the fix's effect on the two worked walks' features reported, the
      engine unchanged, and Uzayr told.

  **AC2. Same day, confounded by recording** (2 trainings).
  - **The split:** within each recording of a Room B day (identification and tracking recordings alike),
    passes are sorted by press time and paired into cycles of two (one away and one towards walk on the
    identification recordings). Cycles 1, 3, 5 and so on (1-based) train; cycles 2, 4, 6 and so on test.
  - **Training:** the full engine recipe (`idz_core.train`, `bank_T3.0`) on that day's training cycles
    only (`runs/identify/teaching/models/sameday_{B1,B2}`).
  - **Scoring:** the whole day replayed through the engine (causal); only the test cycles' identification
    walks scored, natural and all paces.
  - **Beside it:** the engine's cross-day replay (`loso_<day>`) scored on the same test-cycle walks, and
    chance.
  - **The label:** "same day, confounded by recording".

  **AC3. Training without the slow and fast walks** (2 trainings).
  - **Training:** for "to B2" and "to B1", the engine recipe on the same rows minus the other Room B day's
    slow and fast identification walks (`runs/identify/teaching/models/nopaced_loso_{B2,B1}`).
  - **Scoring:** the test day replayed (causal); natural, away, towards, slow and fast.
  - **Reported:**
    - paired against the engine;
    - the engine minus S0 and the engine minus S_wifi for both versions, by pace (S0 and S_wifi unchanged:
      LDAs on the other day's identification walks).
  - **Information only.**

  **Scheduling:** after the pack's lanes, or in a spare GPU slot, never delaying the pack.

- **2026-10-01 13:09. Uzayr's decision: the cadence bug is fixed and adopted** (option 1, given in the session at 2026-10-01 13:09, after
  the evidence in 9657f91 and the measured effect in 839e6d1).
  - **The rule:** as the audit's rule for bugs, the fix is adopted whatever it does to the figures. Its
    measured effect (natural -0.56 [-3.89, +2.78]; Room B tracking -5.42 [-8.75, -1.67]) is information,
    not the reason.
  - **The bug:** `idmax_features.resolve_cadence` lets every channel's estimates vote equally.
    - Channels with no rhythm give estimates at the 0.8 Hz band-pass edge, which `_candidates` doubles
      into the step band.
    - On simulated truth, fast away walks read 0.73 to 0.91 of the step rate, and 33 of 48 grid walks are
      within 5 %.
  - **The fix (engine v2):**
    - only channels whose autocorrelation peak (`acf_peak`) is at least 0.30 vote, the threshold the
      cadence diagnostic uses for clear rhythm;
    - if none qualifies, every channel votes as before;
    - on the grid, 48 of 48 walks are within 5 %.
  - **Where it lives:**
    - `engine.extract_window` computes the gait features with the fixed resolver (a scoped swap of
      `idmax_features.resolve_cadence`; the frozen module's text is not edited, and its other callers keep
      the old rule);
    - the bank builder and the live app both use `extract_window`, so the engine stays one code path.
  - **What changes:** only the gait features (cadence-scaled families: cad, rhy, tplacf, dop). The Doppler
    maps and the three CNN components are unchanged.
  - **New names** (nothing old is overwritten or deleted):
    - banks `runs/identify/engine/bank_T{2.5,3.0,3.5}_x`, with features by the engine v2 and maps asserted
      equal to the old banks;
    - models `loso_{A1,A2,A3,B1,B2}_x`, `deploy_all5_x` and `T{2.5,3.5}_to{B2,B1}_x`: the five feature
      components retrained (`idz_core.train` with parts "feat", the same rows, heads and seeds), and the CNN
      files copied unchanged from the old model of the same name;
    - replays `runs/identify/engine/replays/<model>_x_<session>_T<T>`.
  - **Then on the fixed engine:**
    - the evaluation, the measures and the rig-run checks;
    - the teaching pack's selection (the same rule, re-applied and recorded), its verification and its three
      checks;
    - the addendum's AC2 and AC3 (on `bank_T3.0_x`);
    - the pack and every report, each as a new dated version, with the old figures kept as superseded.
  - **The engine is frozen again** after the rebuild is verified.

- **2026-10-01 13:37. Engine v2 rebuilt and checked; the selection re-applied.**
  - **The banks** (`ixt_rebank banks`, 80cbf0c):
    - one pass of the engine's own Extractor;
    - every decision time and Doppler map is asserted equal to the v1 banks;
    - gait features changed in 944 of 1,019 windows at T 3.0 (952 at T 2.5 and at T 3.5).
  - **The models:** ten `_x` models built, with the five feature components retrained on the same rows,
    heads and seeds, and the CNN files copied.
  - **The replays:** B2 (299 of 299) and B1 (360 of 360) have features and maps equal to the v2 bank, and
    so far every T model's replay does too.
  - **AC1 re-run on engine v2** (`synth_grid_x.json`): 48 of 48 simulated walks are within 5 % (33 of 48
    on v1). The median ratio is 0.993, the same as the checked candidate.
  - **The selection rule, re-applied unchanged** to `loso_B2_x` (`runs/identify/teaching/selection_x.json`):
    - **The tie:** three cells tie at 4 walks (PA2, PA4 and PA5 named as PA1), with equal row
      totals (10).
    - **Ranked by first recording:** PA2, then PA4, then PA5.
    - **Cell 1 (PA2 as PA1) has no qualifying recording:** none of PA2's 10 B2 natural walks is
      right on v2.
    - **The fallback** goes to cell 2: PA4 named as PA1.
    - **The recording:** PA4's natural recording holds a right and a wrong walk in the same direction
      (towards, `A_rev`).
    - **The wrong walk** is replay position 151 (named PA1, displayed confidence 0.4405).
    - **The right walk** is position 157 (0.4446), the closest to the median of correct walks (0.4446).
    - **The v1 selection** (PA2, positions 50 and 56) is kept in `selection.json` as superseded.
  - **The verification on v2** (`verify_B2_x.json`) passes: rig path against harness, 299 of 299 decisions
    equal, with ensemble maximum difference 0.0.

- **2026-10-01 17:18. The lever screen: every lever, the order, the scoring and the promise rule, fixed before anything is
  run.**
  - **Sources:** `reports/BRIEF_ID_LEVER_SCREEN_2026-10-01.md` (verbatim, committed with this note). Code in new
    `pipeline/identify/ils_*.py` files; outputs under `runs/identify/lever_screen/`; the report
    `reports/ID_LEVER_SCREEN_2026-10-01.md`.
  - **What it is:** a screen, exploratory, development evaluation, all data seen. **Engine v2 does not change.** No
    screening number counts for the thesis until a chosen lever is built into `engine.py`, replayed and verified
    against the app n of n.
  - **Compute:** the machine is identification's once Monitor is done (Uzayr, 1 Oct, about 17:10). Tracking is told
    before and after. CPU and MPS; no CNN is trained.

  **Baseline and scoring (every lever the same).**
  - **The baseline:** engine v2's saved causal replays `loso_B2_x_B2_T3.0` (299 windows) and `loso_B1_x_B1_T3.0` (360).
  - **The scored set:** the 180 natural identification walks (60 on B2, 120 on B1).
  - **Primary:** natural accuracy, and the change paired against engine v2 on the same walks with the 95 % bootstrap
    interval over participants (`idw_eval.paired`: 10,000 resamples, seed 0).
  - **Beside it:** to B1 and to B2 (accuracy and paired change); natural walks named PA1 (v2: 63 of 180); PA2
    (v2: 3 of 30); accuracy per person; the runtime (wall clock of the lever's own training and scoring).
  - **Every lever re-scores each session's whole replay in replay order** (all windows, so calibration pools are as
    in the engine); only the natural walks are scored.

  **Anchors, before any lever (a failure stops the screen and is reported).**
  - **A-F:** the five feature components retrained with `idz_core.train`'s feature arithmetic (`ixa_score.train_feat`)
    on each fold's `train_rows.npy` and `bank_T3.0_x`, then re-scored in replay order, must reproduce the replays' five
    feature components to 1e-9 and all 659 decisions.
  - **A-C:** a CNN harness recomputes the three CNN components from the saved `_x` models in replay order, with causal
    AdaBN on every earlier window (the arithmetic of `engine.Session`), keeping every (network, seed) output. It must
    reproduce the replays' three CNN components to 1e-5 and all 659 decisions.

  **The noise floor (before any lever).**
  - **CNN seeds:** the ensemble with all three CNN components built from one seed only (0, 1 or 2), the five feature
    components as saved (inference only, from A-C's outputs).
  - **Feature random states:** the five feature components retrained with `random_state` 1 and with 2 (RF and ET; the
    LDA has none), the CNNs as saved; with the saved state 0, three values.
  - **The seed spread S** is the larger of the two ranges (maximum minus minimum natural accuracy). Each variant's
    paired change against engine v2 is also reported.

  **The promise rule.**
  - **PROMISING** if all four hold:
    1. the paired natural gain is at least +3.00 points;
    2. the paired change is above zero on to B1 and on to B2 separately;
    3. the gain is larger than S;
    4. the natural walks named PA1 do not rise above 63.
  - **WORSE** if the paired natural change is -3.00 points or lower and its size is larger than S.
  - **FLAT** otherwise. Diagnostic rows that are not an ensemble (single components, single links) are not marked.

  **Bugs.** As the brief says, a bug is fixed and adopted whatever its effect. In the screen, a fix is scored against
  engine v2 and enters the best combination; every other lever is still scored against engine v2. It is built into
  `engine.py` (engine v3) after the report, together with the levers Uzayr chooses, so the engine is rebuilt once.

  **Tier 0 (no training).**
  1. **The calibration pool.** For each natural walk, the windows in (a) the feature standardisation pool (earlier
     windows of the session with the same engine path, used once there are at least 10 earlier windows; all earlier
     windows if fewer than 3 share the path) and (b) the AdaBN pool (every earlier window), counted by kind, path and
     layout (Room B identification walks: `id_spot`, RX2 beside the TX; tracking passes: `home`). Line-A tracking
     passes carry the same path labels (`A_fwd`, `A_rev`) as the identification walks.
     - **If the pools mix layouts, that is the bug,** and **fix L** applies: each window calibrates only on earlier
       windows of its own layout, for both standardisation and AdaBN, with the same thresholds. It is test side only
       (no retraining), scored by both harnesses. Its training-side companion is lever 2.5a.
  2. **The cadence fallback.** The 180 natural windows are re-extracted with the engine's own Extractor (as
     `ixt_cadfix.real_walks`). Anchor: the resolved rate equals the bank's `cad|all|-|-|cadence_hz`.
     - **Per walk:** how many of the 9 voting channels (3 links x `CADENCE_CH`) have an autocorrelation peak of at least
       0.30; whether the fallback fires; the resolved rate; the same for the three per-link resolvers.
     - **On the walks where it fires:** whether the resolved rate lies within 0.1 Hz of a doubled band-edge estimate
       (an estimate of 0.80 to 0.88 Hz doubled, 1.60 to 1.76 Hz), and the envelope rate where the envelope is clear.
     - **The bug is confirmed** if the fallback fires on any natural walk and, on most of those walks, the rate sits at
       the doubled edge.
     - **Fix F, then:** no qualifying channel means no rhythm. The cadence is None, and the cadence-scaled features
       take what the feature code gives for None; where a function cannot take None, its columns are NaN and imputed
       from the training medians.
     - **Scoring fix F:** all 1,019 windows' features are re-extracted into a bank beside the old one
       (`runs/identify/lever_screen/bank_T3.0_cadF`), the feature components are retrained, and both sessions are
       re-scored.
  3. **Per component** (from the saved replays): each of the eight alone, with its accuracy, walks named PA1, the
     confusion matrix, the mean log-probability spread (maximum minus minimum per walk), and the mean negative
     log-likelihood of the true class.
  4. **Per link:** the per-link CNN component one receiver at a time (each link's AdaBN output averaged over seeds,
     from A-C), RX1, RX2 and RX3 alone, with accuracy and walks named PA1.
  5. **Packet gaps** (report only): in the same re-extraction as item 2, per window, how many of the sixty 50 ms bins
     over [t0, t0 + 3 s) hold no frame on all three receivers, and on each receiver. Reported over the 180 natural walks
     (and all identification walks for information), with how `id19_bank._interp_cols` fills a gap: linear
     interpolation between the neighbouring frames, clamped at the ends.

  **Tier 1 (re-fusion of saved outputs; no training).**
  1. **Leave one component out:** eight rows.
  2. **Temperature per component:**
     - T_c minimises the true-class negative log-likelihood of `normalise(logp_c / T_c)`;
     - cross-fitted: fitted on every identification walk of B1 (240) to score B2, and on B2's 179 to score B1;
     - the ensemble is the sum of the calibrated components.
     - Beyond the brief, labelled so: one weight per component fitted jointly by the ensemble's negative
       log-likelihood, with the same cross-fit.
  3. **Fusion rules:**
     - the mean of probabilities;
     - the two families: `normalise(sum of the 5 feature components) + normalise(sum of the 3 CNN components)`;
     - the sum of ranks (0 to 5 per component; ties broken by the engine's ensemble);
     - the sum of per-walk z-scores (each component's six log-probabilities minus their mean, over their standard
       deviation).
  4. **Link subsets** for the per-link component: RX2 alone, RX2 + RX3, and all three (this one equals the engine),
     each the normalised sum of the subset's per-link outputs.
  5. **Session bias correction:**
     - each class's summed log-probability minus its mean over the session's earlier windows, once there are at least
       10 of them;
     - pools: the engine's pool (every earlier window), and the earlier identification-layout windows only;
     - flagged beside the number: it assumes everyone walks equally often.

  **Tier 2 (the five feature components retrained, seconds each; the CNNs as saved; both folds).**
  1. **Columns:** RX2 only (its 209 columns and the 3 cross-link step-rate columns, 212); RX2 + RX3 (421); all three
     (630, which equals the engine).
  2. **The LDA:**
     - fixed shrinkage 0.7, and 0.9;
     - logistic regression, L2 with C = 0.01 (`lbfgs`, 5,000 iterations), in the LDA's place, with the same pace
       column and standardisation;
     - the LDA removed, leaving seven components.
  3. **Matched data.** The matched rows are the other Room B day's identification walks: 240 from B1 for to B2, 179
     from B2 for to B1.
     - Weighted x2 and x4: one or three extra copies of those rows for the classifiers; the statistics are fitted on
       the original rows.
     - Features trained on those rows only.
  4. **Families** (630 = rhy 219, dop 141, tplacf 129, spec 69, wav 54, mod 12, cad 6):
     - without `rhy` and `tplacf`;
     - only `dop`, `spec`, `wav` and `mod`.
  5. **Standardisation:**
     - (a) identification-layout session statistics: training groups by (session, layout), and the test pool is earlier
       windows of the same layout;
     - (b) per path from the training statistics only (`PerPath`), for the four session-standardised components;
     - (c) none: the global training statistics;
     - (d) session statistics without the path split.

  **The combination.**
  - **What goes in:** the compatible PROMISING levers, plus any adopted bug fix, scored once together.
  - **Compatible** means one choice per slot (fusion rule, LDA, columns, training weights, standardisation); within a
    slot, the larger gain.
  - **Reported:** its gain against engine v2, how far it gets towards 50 %, and whether the separate gains add up or
    overlap.

  **Stop after Tier 2.** No CNN is trained. If nothing is PROMISING, the report says so plainly.

  **Estimate:**
  - the anchors and the CNN harness's passes (the engine's pool, and fix L's): about 30 minutes, MPS;
  - Tier 0: about 1 hour, mostly the CPU re-extraction;
  - Tier 1: minutes;
  - Tier 2: about 30 feature retrains per fold, about 45 minutes;
  - the report: about 1.5 hours.
  - **Target:** about 22:30.

- **2026-10-01 17:38. The lever screen: three additions after the tiers ran, defined before any is run.**
  - **Where the screen stands:** the anchors passed (A-F 5e-14, A-C 0.0, 659 of 659 decisions each); the seed spread
    S is 4.45; Tiers 0 to 2 are done; **no lever is PROMISING**. Fix L (the layout-mixing bug, by the brief's
    definition) is scored: natural -3.33 [-7.22, +0.56].
  - **Addition 1, the two families at equal weight.** The brief's "each family's sum normalised, then added" is
    identical to the engine by construction: normalising subtracts one constant per window, which never changes the
    argmax (T1.3.two_families, paired 0.00 [0.00, 0.00]). The equal weight the brief means is the families' means:
    `sum of the 5 feature components / 5 + sum of the 3 CNN components / 3`, normalised (T1.3.two_families_mean).
  - **Addition 2, the combination the PLAN asks for.** No lever is PROMISING, so it is fix L alone (T0.1.fixL, already
    scored). Nothing more is run for it.
  - **Addition 3, information only, chosen with the test days' results in view:**
    - **what:** the compatible levers with a positive point gain on natural walks: the per-component temperature
      (T1.2), the LDA's fixed shrinkage 0.7 (T2.2) and the session bias correction on same-layout pools (T1.5),
      combined;
    - **how:** the LDA retrained with shrinkage 0.7, the temperatures refitted on the combination's own components (the
      same cross-fit), then the bias correction on the calibrated sum; scored twice, with the engine's pools and with
      fix L;
    - **what it is for:** it answers whether the small gains add up. It is not a candidate under the promise rule.

- **2026-10-01 17:34. Correction:** the note above headed 17:38 was written and committed at 17:33 (the time was
  typed before the clock was read). Nothing of the additions had run at either time.

- **2026-10-01 18:12. Engine v3 and one test of DANN: the reference, the arms, the scoring and the promise rule, fixed
  before anything runs.**
  - **Sources:** `reports/BRIEF_ID_V3_DANN_2026-10-01.md` (verbatim, committed with this note). New code in
    `pipeline/identify/iv3_*.py`; outputs under `runs/identify/v3/`; the report `reports/ID_V3_DANN_2026-10-01.md`.
  - **Development evaluation, all data seen.** Parts 1 and 2 are screens; only Part 3's replays through the engine,
    verified against the app n of n, give thesis figures.
  - **Compute:** Tracking is told before and after.

  **Part 1. The bug fixes, both adopted (the brief).**
  - **Fix L** is the lever screen's: each window calibrates (feature standardisation and AdaBN) only on earlier windows
    of its own layout, with the same thresholds.
  - **Fix F:** when no voting channel's autocorrelation peak reaches 0.30, the resolver returns no rhythm (cadence
    None) instead of letting every channel vote.
    - The same rule applies to the per-link resolvers, which call the same function.
    - **What the bank does with a missing step rate** (read in the code before this note): `rhythm_features` and
      `cycle_templates` return nothing, and `doppler_features` skips its stride part. Those columns are NaN and imputed
      from the training medians. There is no unscaled fallback.
  - **The screen:**
    - `ils_extract fixF` re-extracts all 1,019 windows' features into `runs/identify/lever_screen/bank_T3.0_cadF`;
    - **F alone:** the feature components retrained on that bank and re-scored with the engine's pools, plus the
      replays' CNN components;
    - **F + L, the v3 reference:** the same features re-scored on same-layout pools, plus the CNN components with
      AdaBN on same-layout pools (`ils_cnn` layout pass).
    - Both are paired against engine v2 on the 180 natural walks, both folds, causal, with the participant bootstrap
      (10,000 resamples, seed 0).

  **Part 2. DANN at seed 0, both walks folds (the training rows of `loso_B2_x` and `loso_B1_x`).**
  - **Networks:** the four CNNs of the engine: `cnn3`, and `cnn_link0` to `cnn_link2`.
    - Their inputs are the engine bank's maps (equal in v1, v2 and v3), windowed and normalised as `idz_core.train`
      does.
    - Training as `idv2_core.train_cnn`: Adam (lr 1e-3, weight decay 1e-4) with cosine decay, batch 64, 6,000 steps,
      class-balanced sampling, per-sample augmentation.
  - **The same-seed baseline** is `idv2_core.train_cnn` itself at seed 0. Information: its outputs are compared with the
    saved seed-0 networks (MPS training may not be bit-identical).
  - **DANN** (new, `iv3_dann.py`):
    - **The identity path is exactly the baseline's:** the same seed, the same generator order for sampling and
      augmentation, and the same network initialisation. The domain head is initialised inside a forked RNG, so it
      moves no random stream.
    - **The domain head:** a gradient-reversal layer on the pooled 896 features (32 x 28, after the mean over time,
      before dropout and the direction flag), then Linear 896 to 64, ReLU, Linear 64 to the number of domains.
    - **The loss:** identity cross-entropy plus domain cross-entropy. The reversal multiplies the gradient into the
      features by -lambda(p), with lambda(p) = lambda_max (2 / (1 + exp(-10 p)) - 1) and p = step / 6,000. The head
      shares the optimiser and its schedule.
    - **lambda_max:** 0.1 and 1.0.
  - **Arm A (deployable):**
    - **The domains are the training sessions, Room B split by layout.** To B2: A1, A2, A3, B1 `id_spot` and B1
      `home` (5 domains). To B1: the same with B2.
    - The domain loss is computed on the identity batch's own windows.
  - **Arm B (information only):**
    - Arm A's domains plus one more: the test session's windows (all of them, unlabelled).
    - Each step adds a batch of 64 test-session windows, drawn and augmented with a separate generator (seed 1000) and
      passed forward separately.
    - The domain loss is over both batches (128 windows).
  - **At the end of training:** the domain head's accuracy on every domain-labelled window (eval mode, no
    augmentation), beside the majority-domain share and 1 / the number of domains.
  - **Scoring** (the 180 natural walks, causal):
    - the CNN components from the seed-0 networks only (`cnn` plain; `cnn_prior` and the per-link component with AdaBN
      on same-layout pools), plus the v3 reference's feature components;
    - **primary:** each arm paired against the same-seed baseline built the same way;
    - **also:** the v3 reference's three-seed CNN components with seed 0's networks replaced by the arm's, against the v3
      reference;
    - **per row:** natural accuracy [95 %], the paired change [95 %], to B1 and to B2, walks named PA1, PA2 (of
      30), each CNN component alone (accuracy, walks named PA1), and the domain accuracy.
  - **The promise rule (Arm A only), at a lambda_max**, PROMISING if all hold:
    1. the paired natural gain over the same-seed baseline is at least +4.45 points;
    2. the paired change is above zero on to B1 and on to B2 separately;
    3. the walks named PA1 do not rise above the same-seed baseline's.
  - **If PROMISING:** seeds 1 and 2 at that lambda_max (if both qualify, the larger gain), and the three-seed ensemble
    against the v3 reference. **Otherwise Part 2 stops.**
  - **Compute:** 40 network trainings (baseline, A x 2, B x 2; two folds; four networks), in two MPS lanes.

  **Part 3. Engine v3, built once.**
  - **What it is:** fix L and fix F in `engine.py` (`ENGINE_VERSION = 3`), plus Arm A's DANN networks only if
    PROMISING across three seeds.
  - **Never overwrite:** banks, models and replays go beside the old ones under new names, and the live app prefers the
    v3 models when they exist.
  - **The end-to-end steps:**
    - the banks;
    - the models: feature components retrained; the CNN files copied from the `_x` models unless DANN is adopted;
    - the replays of all five sessions;
    - the rig path against the harness, n of n;
    - the headline, the controls (S0, S_wifi, no pace), leave one session out, slow and fast, and the deployment
      measures;
    - the tests.
  - **No teaching pack.**

- **2026-10-01 20:15. Windows and gait: the arms, the reference, the rule and the order, fixed before Parts A to D
  run.**
  - **Sources:** `reports/BRIEF_ID_WINDOW_GAIT_2026-10-01.md` (verbatim, committed with this note). Code in new
    `pipeline/identify/iwg_*.py`; outputs under `runs/identify/window_gait/`; the report
    `reports/ID_WINDOW_GAIT_2026-10-02.md`.
  - **What it is:** development evaluation, all data seen. Parts A to D are screens; engine v3 does not change until
    Uzayr chooses (Part E). **The hard stop is the end of 2 October.**
  - **Compute:** identification has priority (Uzayr via Tracking, 20:13). Jobs may run un-niced and in parallel.

  **The reference and the scoring (every row).**
  - **The reference is engine v3:** its replays `loso_B2_v3_B2_T3.0` and `loso_B1_v3_B1_T3.0`; natural 32.22, slow
    25.83, fast 23.53.
  - **Scored sets:** natural (n 180), slow (n 120) and fast (n 119) identification walks, both folds, causal, with fix L
    pools.
  - **Each row reports:**
    - natural, slow and fast accuracy, each paired against v3 on the same walks (participant bootstrap, 10,000
      resamples, seed 0);
    - to B1 and to B2;
    - walks named PA1, and PA2 (of 30);
    - the median decision time after the press, and the share of walks per block whose window ran past the true end
      press;
    - S_wifi on the row's own windows and the engine minus S_wifi, on natural, slow and fast. S_wifi is an LDA on the
      row's Wi-Fi speed, trained on the other Room B day's identification walks (`ixa_measures.lda_one`'s arithmetic).
  - **Part C rows** are paired against the same-seed baseline instead of v3.

  **The rule (quoted from the brief).** PROMISING means all of:
  1. the natural gain over v3 (or over the same-seed baseline in Part C) is at least +4.45 points;
  2. it is positive on to B1 and on to B2;
  3. neither the slow nor the fast paired change is below -4.45;
  4. the engine minus S_wifi on natural walks does not shrink: at least v3's +8.33, or in Part C at least the
     same-seed baseline's.

  Otherwise a row is FLAT, or WORSE if its natural change is -4.45 or lower.

  **Part 0 (housekeeping) runs first:** the engine v3 section in `reports/ID_THESIS_SUMMARY.md`, and one dated line at
  the top of each 1 October identification handoff. No render, no teaching pack.

  **Part A: how much of the walk to see.**
  - **What follows each walk** (descriptive), from every recording's ground truth and RX2:
    - the time from each end press to the next start press, by block;
    - RX2's 10 to 35 Hz energy in the second after the end press, against the walk's own first 2.5 s and against the
      training days' empty room.
  - **Every window stops at the next start press of the same recording** if that comes first. A window's frames are
    those arrived by its own decision time, timed by the causal clock at that time; the decision time is the engine's
    rule applied to the window's end.
  - **The end detector (W-radio, and the walking span of every window longer than 3 s):**
    - **Energy:** RX2's `conditioned_spectrogram` (as the direction rule) summed over 10 <= f < 35 Hz per frame (frame
      centres (16 + 8k) / 150 s).
    - **The reference level** is the median over frames centred in [0, 2.5 s].
    - **A low frame** is one below alpha x the reference. **The end** is the centre of the first frame of the first
      run of low frames lasting at least 0.5 s (10 frames) that starts at or after 2.5 s.
    - **Causal:** at checkpoints t0 + 3.0, 3.25, ..., 6.5 s, the spectrogram is recomputed on [t0, checkpoint], and
      the first checkpoint holding a complete run decides. With no run starting by 6.0 s the window ends at 6.0 s,
      decided at the 6.5 s checkpoint.
    - **alpha, from the training sessions only:** the value in {0.05, 0.1, 0.2, 0.3, 0.5} with the smallest median
      |detected end - end press| over the training sessions' identification walks (to B2: B1's; to B1: B2's). Ties go
      to the smaller 75th percentile, then the smaller alpha. If the two folds choose different values, each fold's
      windows (training and test rows) are built with its own.
  - **Two fixes for windows longer than 3 s:**
    - the direction stays the v3 bank's ([t0, t0 + 3 s]);
    - the Wi-Fi speed is the engine's estimator (torso contour median on the best link, x 0.123 / (2F)) on [t0, walking
      end], where the walking end is the detector's end inside the window, or the window's end.
  - **The arms:**
    - fixed T = 3.0 (this pipeline's anchor: it must reproduce the v3 bank's features and v3's decisions exactly),
      3.5, 4.0, 4.5, 5.0 and 6.0 s;
    - **W-radio** (deployable);
    - **W-oracle** (information only): from the press to the true end press, decided there, with the walking span
      equal to the window.
  - **Features:** the five feature components are retrained on each arm's windows (`idz_core.train`'s arithmetic, the
    same rows, heads and seeds), with the arm's Wi-Fi speed as the pace column.
  - **CNNs:** v3's weights (three seeds) score the arm's maps (more 34-frame windows on longer maps), with AdaBN on
    same-layout pools.
  - **W-radio's detected end against the true end press** is reported by block (median signed and absolute error),
    as information.
  - **Carried forward:** Parts B and C use the deployable arm (a fixed T or W-radio) with the best natural score whose
    slow and fast paired changes are both above -4.45; with none, T = 3.0. **That choice is made with results in view,
    and is recorded so.**

  **Part B: gait parameters on the carried window** (feature components only, retrained; CNNs as in that arm).
  - **B1.** From the window's Wi-Fi speed v and resolved step rate f (v3 resolver; no rhythm gives NaN):
    - the walk ratio v / f^2;
    - the brief's "stride length" v / f (strictly the step length);
    - speed-normalised cadence, the residual of f from a line f = a + b v fitted by least squares on each fold's
      training rows with both finite.
    - Reported beside them: the share of natural walks with a usable step rate at this window and at 3 s.
  - **B2. The contour:** a per-frame speed on the map's frame grid, on the walking span.
    - **On identification-spot windows:** A1's estimator per frame. RX2's spectrogram on 10 <= f < 35 Hz minus E(f),
      the median empty-room spectrum of the fold's training Room B day(s), clipped at 0; the power-weighted centroid;
      frames above the span's 25th energy percentile; v_k = centroid x 0.123 / (2 x 0.98).
    - **Elsewhere:** the same on the best link, with the band scaled by F / 0.98 and no empty-room subtraction; NaN if
      F < 0.3.
    - **Columns:**
      - the mean of the finite v_k;
      - the velocity fluctuation at the step rate, divided by that mean: the amplitude of the least-squares sinusoid at
        f fitted to the finite v_k, NaN without a step rate or with fewer than 8 finite frames;
      - the steady speed, the median v_k over the span's second half;
      - t90, the first frame time with v_k at least 0.9 x steady;
      - the start ratio, the median v_k over the first 0.5 s divided by steady.
    - **Information:** A1's speed (the median v_k on identification-spot windows) on this window, Pearson against press
      speed on the 180 natural walks.
  - **The rows:** B1, B2 and B1 + B2, the new columns added to all five feature components. Each is scored **with**
    the raw Wi-Fi speed column in the three pace components and **without** it (no speed column anywhere), beside the
    carried window without speed.
  - **B4 (body shape, optional, last, and only if time allows):**
    - RX1's attenuation (the subcarrier-mean amplitude over its first 0.5 s median, as dB) resampled from time to
      distance along the path, using the Wi-Fi speed;
    - its depth (the minimum) and width (the distance below half the depth) as two columns.

  **Part C: the networks.** One seed (0), both folds, on the carried window's maps.
  - **The same-seed baseline:** `idv2_core.train_cnn` at seed 0 on those maps. At T = 3.0 these are v3's own seed-0
    networks, reproduced bit for bit.
  - **Scoring:** the seed-0 CNN components with the carried arm's feature components, AdaBN on same-layout pools,
    paired against the baseline. Each CNN component alone is reported too.
  - **The velocity contour v_j for C1** is B2's, with NaN frames filled by the walk's median, then the Wi-Fi speed,
    then 1.2 m/s.
  - **C2, velocity maps (geometry only):**
    - each link's frequency axis becomes body velocity u = f x 0.123 / (2F), with F = `engine.mean_F` for the window's
      path and layout, resampled linearly onto 28 points from 0.3 to 4.3 m/s (zero outside the source band);
    - a link with F < 0.3 is all zeros;
    - the networks: `cnn3` on RX2 and RX3 (2 channels), and per-link networks on RX2 and RX3. RX1's per-link network
      stays the baseline's, on its original map.
  - **C1, pace-normalised maps:**
    - as C2, but the axis is the ratio r = u / v_j per frame, on 28 points from 0.2 to 3.0, so the torso sits at r = 1
      in every frame;
    - the Wi-Fi speed (standardised on the training rows) enters each C1 network's head as one scalar beside the
      direction flag (head input 896 + 2 + 1).
  - **C3, cross-session contrastive:**
    - all four networks on the original maps, with a supervised contrastive loss beside the identity loss;
    - the loss acts on a projection (896 to 128, L2-normalised) of the pooled features, temperature 0.1;
    - positives are the same person from a different session within the batch, and anchors without one are skipped;
    - the projection head is initialised inside a forked RNG, and no extra sampling is done, so the identity path's
      random streams match the baseline's;
    - weights 0.1 and 0.5.

  **Part D: combine and confirm.**
  - **Combine:** the compatible PROMISING rows from A to C, scored once together.
  - **Confirm the best deployable combination** with three seeds (each seed's networks trained or, for v3 weights,
    taken as they are; the three-seed ensemble), plus:
    - leave one session out on the tracking walks (Room A and Room B);
    - S0 and S_wifi on natural, slow and fast;
    - per person.
  - **Adopted only if it passes the rule on three seeds.** Nothing is built into the engine until Uzayr says.

  **Order:** Part 0; Part A (the follow-up check, alpha, the banks, scoring); Part B; Part C; Part D; the report. If
  nothing is PROMISING, the report says so plainly and stops, and identification closes at v3.

- **2026-10-01 22:48. Lean into the 4 s window and stack what works: the rules, the arms and the stacking order, fixed
  before anything runs.**
  - **Sources:** `reports/identification/briefs/2026-10-01_lean-in.md` (verbatim, committed with this note). Code in a
    new `pipeline/identify/ili_stack.py` plus additive options in `iwg_*`; outputs under `runs/identify/lean_in/`; the
    report `reports/identification/2026-10-02_lean-in.md`.
  - **What it is:** development evaluation, all data seen. **The hard stop is the end of 2 October,** including any
    engine build and the teaching pack.
  - **Compute:** **one GPU job at a time, under the memory watchdog** (it kills only its own job if free memory falls
    below 30 % or the job passes 6 GB), with the MPS cap (high 0.3, low 0.2). CPU extraction runs at most five
    processes at once, checked against free memory.
  - **Closed, not retried:** the radio end detector, C1, C2, C3, DANN, and Part B's walk ratio, step length,
    normalised cadence and contour columns.

  **Scoring (every row):**
  - natural (n 180), slow (120) and fast (119) identification walks, both walks folds, causal, fix L pools;
  - each block paired against the base (or the stack so far) and against engine v3, with the participant bootstrap;
  - to B1 and to B2, walks named PA1, PA2 (of 30), the median decision time, and the engine minus S_wifi on the
    row's own windows (reported, not required).

  **The step rule** (quoted from the brief; a lever stays only if all hold against the stack so far):
  1. the natural paired gain is at least +2.22 (4 walks);
  2. neither fold falls by more than 3.4 points;
  3. neither slow nor fast falls by more than 2.5 points;
  4. the walks named PA1 rise by no more than 5.

  **The final rule** (for adopting the stack as engine v4):
  1. the natural paired change against engine v3 has an interval that excludes zero;
  2. slow and fast are each at least engine v3's (25.83 and 23.53);
  3. the leave-one-session-out tracking walks (Room A and Room B) are not below v3's (31.67 and 27.50) by more than
     4.45;
  4. all of this holds with all three seeds.

  **Part 0: the base window.**
  - **The plateau check:** fixed T = 3.5, 3.75, 4.0, 4.25 and 4.5 s, built as the window and gait brief built its
    arms (the engine's own extraction at each window's decision time; the Wi-Fi speed on the walking span; v3's CNN
    weights, three seeds). 4.0 s is trusted only if 3.75 and 4.25 s are each within 2.5 points of it on natural walks.
  - **Direction:**
    - each window's natural accuracy is reported for towards (`A_rev`) and away (`A_fwd`), by the engine's detected
      direction;
    - **the direction rule:** each fold uses, per direction, the window (of 3.0, 3.5, 3.75, 4.0, 4.25, 4.5, 5.0 and 6.0
      s) with the best accuracy on the OTHER fold's identification walks of that direction (all paces), so the choice
      is cross-fitted;
    - the choice made on the scored walks themselves is reported as information only.
  - **The multi-window ensemble:** the sum of the normalised ensemble log-probabilities of 3.0, 3.5, 4.0 and 4.5 s,
    each with its own feature components and CNN components, decided at 4.5 s.
  - **The base:** the best of 4.0 s, the direction rule and the multi-window ensemble that passes the step rule
    against v3 and the plateau check. If none passes, the base is 4.0 s.
  - **The base on the leave-one-session-out tracking walks** (all five folds), scored at once:
    - Room A folds use the end-detector alpha fitted on both Room B days' identification walks (their training
      sessions), by the window and gait rule;
    - paired against v3's tracking replays.

  **Part 1: cheap levers on the base** (feature components retrained, seconds each; each scored against the base).
  - **1.1 Temperature:** one per component, fitted by the true-class negative log-likelihood on the other fold's
    identification walks (all paces); the ensemble is the sum of the calibrated components.
  - **1.2 Stable features:**
    - for each of the 630 columns, on the fold's training rows only, the ICC = the variance over people of their
      session means divided by the mean over people of the variance of that person's session means (each column
      standardised over the training rows first; NaN rows dropped);
    - keep the top k = 150, 300 or 450, and retrain the five feature components on them.
  - **1.3 Placement-robust RX2:** drop RX2's four amplitude-level columns, all in family `mod`:
    `mod|-|RX2|-|moddepth_gait`, `moddepth_dop`, `sub_dispersion` and `rssi_std`.
    - Read in the code before this note: RX2's other 205 columns are frequency measures or normalised shapes (Doppler
      contours, relative spectral and wavelet energies, z-normalised templates, autocorrelation shapes).
    - Information: the forest's feature importances, to test the brief's statement about which RX2 columns lead.
  - **1.4 RX1 shadowing and sway** (4 columns added to all five feature components). From RX1's subcarrier-mean
    amplitude a(t) on the base window:
    - the attenuation in dB against the window's 95th percentile of a(t), resampled from time to distance d = v t (v =
      the window's Wi-Fi speed) onto 0 to 5 m in 0.1 m steps, up to the distance covered;
    - **depth:** the minimum attenuation;
    - **width:** the length of the span below half the depth;
    - **asymmetry:** (the position of the minimum minus the centre of that span) / width;
    - **sway:** RX1's power within 0.1 Hz of the resolved step rate, divided by its power in 0.8 to 3.5 Hz (NaN without
      a step rate).
  - **1.5 Session bias correction:** the lever screen's, over earlier windows of the same layout, once there are at
    least 10. Flagged: it assumes everyone walks equally often.

  **Part 2: the networks on the base maps** (GPU, one job at a time).
  - **2.1 Retrained CNNs:** `idv2_core.train_cnn` on the base maps, seeds 0, 1 and 2, all four networks, both walks
    folds. Scored with AdaBN on same-layout pools.
  - **2.2 Whole-window CNN:** the same four networks, each input the whole base map (every frame) instead of 34-frame
    windows (the network already pools over time). Seed 0, against the same-seed baseline (2.1's seed 0).
  - **2.3 Pace augmentation:**
    - in training only, each sample's map is resampled so that new(f, t) = old(f / s, t x s), with s ~ U(0.92, 1.08)
      per sample, drawn from its own generator, and zero outside the source;
    - seed 0, against the same-seed baseline.

  **Part 3: the stack, in this fixed order** (the step rule against the stack so far at each step):
  1. the base;
  2. 2.1;
  3. 1.1;
  4. the better of 1.2 (its best k) and 1.3 (better = the larger natural gain over the stack), then the other;
  5. 1.4;
  6. the better of 2.2 and 2.3, then the other (with all three seeds once kept);
  7. 1.5, flagged.
  - **The final stack is scored on:** all three seeds; leave one session out (all five folds, every component the stack
    uses retrained per fold); slow and fast; S0 and S_wifi on natural, slow and fast; per person, PA1 and PA2;
    and the decision time. Then the final rule.

  **Part 4: diagnostics** (information only).
  - **4.1 Systematic errors:** for each person and test day, the share of their wrong natural walks that receive their
    most frequent wrong name, for engine v3 and for the final stack.
  - **4.2 Same day against across days, link by link:**
    - AC2's recipe (alternate walk cycles within each recording of a Room B day; odd cycles train, even cycles test),
      feature components only, on RX1's, RX2's and RX3's columns separately (each with the 3 cross-link step-rate
      columns);
    - against the cross-day feature components restricted to the same columns, on the same test walks.

  **Part 5: build.**
  - **If the final rule holds:** engine v4 into `engine.py`, replays, rig-path verification n of n, the full re-score,
    the render's count and command, and the teaching pack to the 1 October spec (the selection rule re-applied).
  - **Otherwise:** engine v3 stands, with v3's render command and v3's teaching pack.

- **2026-10-02 00:23. Engine v4: the lean-in brief's Part 5 build, fixed before the build runs.**
  - **The decision:** the final stack is the 4.0 s base with v3's CNN weights; no lever passed the step rule. It meets
    the final rule (`runs/identify/lean_in/final_final.json`, 71f823d), so it is built as engine v4.
  - **The screened arm, built exactly** (`iwg_bank.window`, the lean-in base):
    - **the window** is [t0, t0 + 4.0 s], decided by the engine's rule at its end. A window stops at the next start
      press if that press is already pending (in the data no 4 s window meets one);
    - **the direction** is detected on [t0, t0 + 3 s] at that 3 s window's own decision time, as v3 does;
    - **the end detector:**
      - at checkpoints t0 + 3.0, 3.25, 3.5, 3.75 and 4.0 s, each on [t0, checkpoint] at that checkpoint's decision time,
        RX2's 10 to 35 Hz energy per frame;
      - the reference is the median over frames centred in [0, 2.5 s];
      - the end is the first run of 10 frames below alpha x the reference that starts at or after 2.5 s;
    - **the Wi-Fi speed** is the engine's estimator (torso contour median on the best link for the direction's path,
      x 0.123 / (2F)) on [t0, the detected end], or the whole window without one;
    - **features and maps** are on the whole window.
  - **alpha is a model parameter, in each manifest:** `loso_B1_v4` uses 0.2 (fitted on B2); `loso_B2_v4` (fitted on B1),
    the Room A folds and `deploy_all5_v4` (both Room B days) use 0.5.
  - **Names:** `ENGINE_VERSION = 4`, `SUFFIX = "_v4"`, `T_S = 4.0`. Banks, models and replays get `_v4` names beside v3's,
    and nothing is overwritten. The CNN files are copied from the `_v3` models.
  - **Checks:**
    - the v4 bank's features, maps, decision times and both speeds equal the lean-in screen's 4.0 s bank on every window;
    - the v4 replays' decisions equal the screen's final stack on every window of B1 and B2, and its tracking walks;
    - the rig path against the harness n of n, and the identification tests.
  - **Re-scored on v4:** natural, slow, fast, leave one session out, the controls (S0, S_wifi, no pace), the deployment
    measures and confidence; the render's expected count and command.
  - **Not re-scored on v4:** the T-sensitivity models (information only; the lean-in screen's plateau check stands
    in their place).
  - **The screen's modules** are pinned to v3's 3 s bank before the engine changes.
  - **The teaching pack** follows to the 1 October spec on v4, the selection rule re-applied.

- **2026-10-02 00:51. The overnight brief (Uzayr, 2 Oct 00:40, unattended), fixed before anything is measured.**
  - **The brief:** `reports/identification/briefs/2026-10-02_overnight.md` (verbatim). Log: `runs/identify/overnight/log.md`.
    Code: `pipeline/identify/ion_night.py` (one module, subcommands). Outputs: `runs/identify/overnight/`. Report:
    `reports/identification/2026-10-02_overnight.md`. Development evaluation, all data seen.
  - **The reference is engine v4** (its replays equal the lean-in screen's 4.0 s ensembles on all 1,019 windows,
    `runs/identify/engine/v4_prediction_check.json`). Every row is paired against v4; the step rule is against the stack
    so far. Folds: the two walks folds (to B2: `loso_B2`, trained on A1, A2, A3, B1; to B1: `loso_B1`) score natural,
    slow and fast; the five leave-one-session-out folds score the tracking walks (Room A, Room B). Every fitted part
    below is fitted per fold on that fold's training sessions only.
  - **Part 1, the learned speed (target: press speed; inputs: radio only).**
    - **Inputs per walk**, from the v4 bank at the fold's alpha, all inside the 4 s window:
      - RX2's and RX3's torso contours, read from the walk's own conditioned maps: exp(map) is the STFT magnitude up to
        a per-map constant (the engine's STFT, 28 bins, 4.7 to 68 Hz, hop 8/150 s), so per frame the 25th, 50th,
        75th and 90th energy-percentile frequencies and the power-weighted centroid; over the walking span's frames
        (to the end detector's `walk_end_s`) their median, mean, 10th and 90th percentiles, the 50th contour's IQR
        and slope; each link's speed reading = 50th-contour median x 0.123 / (2F);
      - the energy envelope: each of RX2 and RX3's 10 to 35 Hz band power per frame; rise time (first frame at half
        its maximum, smoothed over 5 frames), the time of its maximum, `walk_end_s`, and fall time = `walk_end_s` minus
        the time of the maximum;
      - F for RX1, RX2 and RX3 on the walk's detected path (`engine.mean_F`);
      - the frame count: CSI frames received per link in [t0, t0 + 4 s), and the walking span in frames;
      - the engine's own Wi-Fi speed (radio only).
    - **1a:** `HistGradientBoostingRegressor` (squared error, learning rate 0.05, 300 iterations, 15 leaves, at least 20
      samples per leaf, L2 1.0, random_state 0), fixed, not tuned. Trained on every walk of the training sessions
      (identification and tracking walks, all paces; all 1,019 walks have a press speed).
    - **1b:** a small CNN regressor on RX2's and RX3's 4 s maps (frames after `walk_end_s` set to 0), F for RX2 and RX3
      joined before the head: conv 2-16, 16-32, 32-32 (3 x 3, batch norm, ReLU, max-pool after the first two), global
      average pool, then 34-32-1; Huber loss (delta 0.1), AdamW (1e-3, weight decay 1e-3), 1,500 steps of batch 64,
      seed 0 (then 1 and 2 if 1b wins at seed 0, averaged). One GPU job under the watchdog.
    - **Cross-fitting:** a training walk's learned speed is predicted by a regressor trained on the fold's OTHER
      training sessions (inner leave one session out); the test session's by the regressor on all its training
      sessions. The deployment model's sessions are each cross-fitted the same way.
    - **The better of 1a and 1b** is chosen on the inner cross-fitted Pearson against press speed over all training
      walks, averaged over the two walks folds (never on a test session). Test-session Pearsons and median absolute
      errors (natural, slow, fast, per fold) are reported as identity-blind information, beside the Wi-Fi speed's.
    - **Arm 1-L:** the five feature components retrained with the learned speed as the pace column (the three pace
      components use it), the CNNs as v4. **S_learned:** `iwg_screen.s_wifi`'s one-number LDA on the learned speed
      (trained on the other Room B day's identification walks, their cross-fitted values), beside S0 and S_wifi on
      natural, slow and fast.
  - **Part 2, the physics component (a ninth vote).**
    - **The vector (27 values):** the learned speed; RX2's and RX3's contour medians (25th, 50th, 75th, 90th), the 50th
      contour's IQR and slope, and the centroid median; on the best link, the speed trace (50th contour x 0.123 / (2F),
      5-frame median filter): steady speed = its median from 1.5 s to the walk end (NaN with under 0.5 s), time to
      steady = first time it reaches 0.9 x steady; the step rate (`cad|all|-|-|cadence_hz`, NaN where v3's fix F finds
      no rhythm) and its missing flag; RX1's shadowing depth, width, asymmetry and power at the step rate
      (`ili_stack.rx1_columns`'s arithmetic, distance from the learned speed); F for RX2 and RX3; `walk_end_s`.
    - **The classifier:** NaN replaced by the training median; standardised on the training walks (no calibration
      pool); multinomial logistic regression, C from {0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1} by leave one session out
      across the fold's training sessions (mean log loss; ties to the smaller C). Training walks: the fold's training
      rows (as the engine's components).
    - **Scored two ways:** the ninth component in the equal sum, and with the per-component temperatures
      (`ils_screen.temperatures`, fitted on the other Room B day). If both pass the step rule, the larger natural gain
      is kept.
  - **Part 3, MiniRocket.** sktime is not installed. It is installed with `--no-deps` into a scratch directory outside
    the repository, so the engine's environment (scikit-learn 1.7.2, numpy) is never changed; if that fails within 15
    minutes, Part 3 is skipped and logged.
    - **The inputs (10 channels x 600 samples, 150 Hz, the 4 s window, zero after a pending press):** RX1's and RX3's
      subcarrier mean band-passed to the engine's "full" band, and their PCs 2 to 4 of the "dop" band (4 to 70 Hz);
      RX2's 50th torso contour and 10 to 35 Hz envelope (from the maps, interpolated onto the 150 Hz grid). RX2's
      amplitude traces are left out.
    - **The classifier:** `MiniRocketMultivariate` (10,000 kernels, random_state 0) fitted on the fold's training walks;
      `RidgeClassifierCV` (alphas 10^-3 to 10^3, 10 values) on the standardised features; log-probabilities = log
      softmax of the decision scores / tau, with tau fitted by leave one session out on the training sessions (mean
      log loss). No calibration pool. Fused as an extra equal-sum component.
  - **Part 4, more CNN seeds.** Seeds 3 to 9 trained exactly as v3 trains its networks (`idz_core.train`, parts cnn, on
    v3's 3 s bank and the fold model's training rows, 6,000 steps, MPS), each seed in its own directory under
    `runs/identify/overnight/seeds/`; B2 and B1 interleaved (B2 s3, B1 s3, B2 s4, ...), so a cut-off leaves both folds
    with the same seeds. The budget is 75 minutes from the first training; complete seeds only are scored. Scored as
    v4 scores its CNNs (`iwg_screen.cnn_outputs` on the 4 s maps, AdaBN on same-layout pools), seeds averaged as the
    engine averages them. The Room A folds' seeds 3 to 9 (needed for the final rule's leave one session out) and then
    `deploy_all5`'s (needed for a v5 build) are queued after the walks folds; they are stopped if Part 4 fails the step
    rule.
  - **Part 5, the stack:** v4, then 1-L, then the 10 seeds (or the seeds finished), then Part 2, then Part 3; each step
    kept only if the step rule holds against the stack so far (natural >= +2.22; neither fold below -3.4; neither slow
    nor fast below -2.5; PA1's count up by no more than 5). The S_learned control is not a lever. **The final rule
    (v5):** natural paired gain over v4 >= +3.33 and positive on both folds; slow and fast each >= v4 - 2.5; Room A and
    Room B leave-one-session-out tracking >= v4 - 4.45; with every seed the stack uses; the shuffled-order check for any
    gain above +8.
  - **The shuffled-order check** (any arm above +8): each test session's walks re-scored in one shuffled order (seed 0),
    every causal pool (feature calibration and AdaBN) built in that order; the gain must survive (stay above +2.22).
  - **The guard against a false win:** nothing above groups, clusters, smooths, assigns or pseudo-labels the test day's
    walks; only the existing causal pools see the test day, unlabelled.
  - **Part 6:** if the final rule holds, engine v5 in `engine.py` (`ENGINE_VERSION = 5`, `SUFFIX = "_v5"`, every v4 file
    kept), retrained per fold, replayed, rig path n of n, tests, the full re-score. Otherwise engine v4 stands. Either
    way: the render's expected count on B2's natural blocks and its command, and the teaching pack on the final engine
    to the 1 October spec with the selection rule re-applied unchanged. The pack's three checks are re-run on the final
    engine as far as the night allows (the shuffled-label and ablation CNNs were trained on 3 s maps as v3/v4's are, so
    they are re-scored on the 4 s maps rather than retrained); any check not re-run is labelled with the engine it was
    measured on.
  - **If pipeline/live/ changes,** tracking's live tests (`tests/test_live*`) run before the commit (Tracking's request).

- **2026-10-02 05:26. The v5 brief (Uzayr, 2 Oct morning): engine v4 without same-day calibration, scored before anything is built.**
  - **The brief:** `reports/identification/briefs/2026-10-02_v5.md` (verbatim). Code: `pipeline/identify/iv5_check.py`.
    Outputs: `runs/identify/v5/`. Development evaluation, all data seen; the configuration is chosen with the test results
    in view (the overnight re-score showed it).
  - **The candidate (Step 1, no training):** each of engine v4's five fold models (`loso_<S>_v4`) classifies every window of
    its test session through `engine.Session.classify` with an empty pool: the feature standardisation from training
    statistics only, no AdaBN (the networks keep their training batch-norm statistics); the same bank windows, the same
    paths (`path_used` of v4's replays), the same speed column (the model's alpha), each window's layout. This is
    `ixa_measures.cal_none`'s arithmetic (CAL-none), saved per fold. MPS, one job under the guard.
  - **Anchor:** every window that v4 itself decided with an empty pool (`calib_n` 0 in v4's replays: the first window of
    each layout) must give v4's replay ensemble to 1e-6.
  - **Reported, paired against v4 on the same walks (participant bootstrap, 10,000 resamples, seed 0):** natural, slow,
    fast (and away, towards) with intervals; to B1 and to B2; per person, the walks named PA1, PA2's count; leave one
    session out on the tracking walks, Room A and Room B, with the paired change; S0 and S_wifi and the candidate minus
    each on natural, slow and fast; the deployment measures (`idw_eval.deployment`); confidence against coverage
    (`ixa_measures.coverage`), with PA1's share of the right answers in the most confident 30 %.
  - **The check (all must hold to build v5):** natural at least 37.78; slow at least 29.17 - 2.5 = 26.67; fast at least
    30.25 - 2.5 = 27.75; Room A at least 32.50 - 4.45 = 28.05; Room B at least 27.92 - 4.45 = 23.47 (figures as reported,
    to two decimals). If any fails: stop, build nothing, report which, and Uzayr decides. The record of Step 1 is
    `reports/identification/2026-10-02_v5-check.md`; `2026-10-02_v5.md` is kept for Step 3.

- **2026-10-02 07:28. Uzayr's decision on the v5 check: keep engine v4.** The check failed on Room B tracking (23.33
  against the 23.47 floor; `reports/identification/2026-10-02_v5-check.md`, b911d91). Engine v4 is the final
  identification engine; v5 is not built. Identification closes here: no further identification work.

- **2026-10-11 14:27. Engine v5 shipped; identification development closed.** Engine v5 (built 10 Oct on Uzayr's brief
  `prompt_identification_v5_ship.md`; not the 2 Oct candidate above, which was never built) is the final identification engine:
  the Room A run's A3-half choice (base A1+A3+A4+M3, C2 room weights), switched on per model by the manifest's engine_version 5,
  every v4 model running exactly as before. Uzayr's answers to the step 7 stop (11 Oct): option (c), the live app adapts each
  walk after its decision is written and shown and runs v5 on the GPU by default; storage of the large pickles on Drive
  (runs/identify/v5/STORAGE.md). The confirmation run (B2's whole day at 1x on mps, every decision timed) equals the harness
  exactly (299 of 299, difference 0) and keeps 297 of 299 decisions within the cap (largest 1.453 s after t0 + 4.0 s against
  1.30), memory growing 1.99 GB/h on the GPU side: both flagged for Uzayr, nothing changed. Development evaluation, all data
  seen; the configuration was chosen with A3 and B2 in view. Report: `reports/identification/2026-10-11_engine-v5.md`;
  queue `runs/identify/v5/QUEUE_V5.md`. No further identification development.

- **2026-10-12 10:28. Parallel window extraction tried in the v5 live app and REVERTED to serial (Uzayr's go and ship rule, 12 Oct).** A
  warm pool of three worker processes extracting the three windows in parallel (the engine's own extract_v4 on frozen copies;
  engine.py unchanged) was exact (897 of 897 B2 windows bitwise identical to serial; the live app bit-identical on all 299
  decisions; the mps run equal to the replay, difference 0) and fast (B2 at 1x: 299 of 299 within the cap, median 0.731 s and at
  most 1.125 s after t0 + 4.0 s, against serial's 298, 1.047 and 1.315 s). It failed the memory rule fixed before the run (rule
  (a): two workers above their 10 % band on single samples, slopes about 1 MB per hour; macOS pressure level 2 on 4 samples at
  minute 38 with 50 % free), so the ship rule reverted it (5b152dab; identify_engine.py exactly as at 7de0b32b): the serial
  figures (1.05 s, 298 of 299) stand. Report: `reports/identification/2026-10-12_parallel-extraction.md`; queue
  `runs/identify/v5/parallel/QUEUE_PAR.md`. Development evaluation, all data seen.

- **2026-10-12 11:48. Parallel window extraction re-adopted and SHIPPED in the v5 live app (Uzayr's second go, 12 Oct).** After the first run's
  memory failure and revert (note above), Uzayr redefined the memory rule (workers judged by trend; pressure level 2 allowed only
  with at least 30 % free; the total within serial's 1.875 GB/h + 10 %) BEFORE one fresh confirmation run, with no further
  redefinition; the pool re-adopted (d5cd118b; identify_engine.py as at 5e4193a6; engine.py unchanged). The run (B2 at 1x on mps,
  10:41 to 11:46, other apps closed but this VS Code window): exact (299 of 299, difference 0); 299 of 299 within the cap; delay
  after t0 + 4.0 s median 0.714 s, at most 0.813 s (serial 1.047 and 1.315); processing after the last data median 0.387 s, at
  most 0.484 s, the 0.5 s target met at the median and on 299 of 299 walks; memory by the redefined rule: total 1.995 GB/h
  (limit 2.0625), workers 78 to 88 MB with slopes -1.1 to +1.7 MB/h, no swap growth, pressure normal throughout. Ship rule
  held: parallel extraction ships with these figures (`--extract-workers 0` keeps the serial fallback). Report:
  `reports/identification/2026-10-12_parallel-extraction.md`. Development evaluation, all data seen.

- **2026-10-15 14:53. Components-and-features TEST: Part 1's rules, fixed before any candidate score (Uzayr's prompt
  `prompt_agent1_component_feature_analysis.md`, his full go in the Code agent's chat at about 14:48; approved by his
  supervisor as a test; nothing is adopted by this run).** Development evaluation, all data seen; exploratory. Engine v5,
  its models, manifests, replays, `engine.py`, `identify_engine.py` and the live app are read only; new code
  `pipeline/identify/iv6_*.py`, outputs `runs/identify/v6_test/`. Done before this note: the ensemble check only
  (`iv6_components check`: v5's ensemble and confidence recomputed from the stored component arrays with
  `engine.Session.combine`'s formula equal the stored ones, max abs difference 0.0 on all 13 v5 replays, 2,695 walks;
  `runs/identify/v6_test/checks/ensemble_equal.json`). No component accuracy, diagnostic or candidate had been computed.
  - **Data.** The 13 replays `runs/identify/engine/replays/*_v5_*_T4.0.npz`: each component's normalised log-probabilities
    for the windows at 0, 0.15 and 0.30 s (`c_<comp>`, `c_<comp>_0.15`, `c_<comp>_0.30`), the stored weight a per walk
    (`weight_a`), `te` into the v4 bank (labels). No retraining in Tier 1. Components: six feature (rf, rf_prior,
    rf_pace_prior, et_pace_prior, lda_pace_prior, hgb_pace_prior), three CNN (cnn, cnn_prior, cnn_perlink_prior).
  - **The combination.** Per window k, s_k = sum_c w_c g_c c_k, with g_c = the walk's stored a (the installation rule:
    0.25 on a Room A tracking walk for a model trained in Room A, else 1) for a feature component and 1 for a CNN
    component; each s_k normalised, the three averaged and normalised; the argmax decides. Engine v5 is every w_c = 1.
    The displayed confidence keeps `eq:confidence`'s form, softmax(mean_k s_k / a_+) with a_+ = sum_c w_c g_c. In algebra
    the ensemble equals log_softmax(sum_c w_c g_c m_c), m_c = the mean of the component's three windows; the fits below use
    that form, the scoring uses the engine's form. A component's own walk-level output is log_softmax(m_c).
  - **Cross-fitting.** A walk of test session S (A1, A2, A3, B1 or B2) is scored with weights fitted only on the pool P(S)
    = the stored held-out outputs of loso_X_v5 on X for the four sessions X other than S (all of X's walks: A1, A2, A3 120
    tracking walks each; B1 360; B2 299; each walk counts once). No label of S touches a weight. One weight set per
    candidate and S, used for every model scored on S (loso, xr_AB, xr_ABtrk, xr_A, xr_B1). **Disclosed:** each loso_X_v5
    trained on S, so the pool's outputs come from models that saw S (indirect exposure); Tier 2 removes it if a candidate
    passes. LL_c(P) = the mean over P's walks of -log softmax(m_c)[true class].
  - **The five candidates (no others will be added):**
    1. **INVLL:** w_c proportional to 1 / LL_c(P(S)), rescaled so the nine sum to 9.
    2. **TEMP:** one temperature per component, T_c = argmin over log T in [-4, 4] (scipy `minimize_scalar`, bounded) of the
       mean -log softmax(m_c / T)[true] on P(S); w_c = 1 / T_c (no rescale: a common scale changes no decision).
    3. **STACK:** w >= 0 minimising the mean -log softmax(sum_c w_c g_c m_c)[true] on P(S), g as stored on each pool walk,
       the overall scale left free (L-BFGS-B, bounds [0, inf), start w = 1, analytic gradient, scipy defaults), then
       rescaled to sum 9. "Summing to 9" is read as this normalisation; it changes no decision and only fixes the
       confidence's scale. (Fitting with the sum held at 9 would let the over-confident sum push weight onto flat
       components to lower its confidence, which is a calibration artefact, not a vote.)
    4. **TOP3:** the three components with the lowest LL_c(P(S)), w = 1 each, the other six 0 (ties by component order).
    5. **BEST1 ("favour the strongest"):** the single component with the lowest LL_c(P(S)), w = 1, the others 0.
    The installation rule stays on top of every candidate (the candidate as judged). Each is also reported **without it**
    (g = 1 on every walk; STACK refitted with g = 1, the other four need no refit): information only, it cannot pass.
  - **The headline cell.** (Z + D) / 2 as v5's brief section 4: Z = the mean of the three zero-shot cells (xr_A to B2 path
    and natural walks, xr_B1 to A3 path walks), D = the mean of `ilc_outer.CROSS`'s ten cross-day cells, through
    `ilr_report.zd` (paired participant bootstrap, 10,000 draws, seed 0, the cells resampled jointly), the candidate minus
    v5 on the same walks. v5: Z 33.61, D 33.35, (Z + D) / 2 33.48.
  - **The guards** (QUEUE_V5's scorecard margin, 5 points, as `ilc_outer.summarise`): each candidate's accuracy at least
    v5's minus 5.00 points on loso natural (180 walks; v5 36.67), loso slow (120; 33.33), loso fast (119; 30.25), Room A's
    tracking walks (loso A1+A2+A3 path, 360; 35.83) and Room B's (loso B1+B2 path, 240; 30.00).
  - **The core model** (no fall at all): the candidate's accuracy at least v5's on xr_ABtrk A3+B2 path (240; 32.08) and
    xr_A all B2 (299; 32.11).
  - **Adoption rule.** A candidate PASSES Tier 1 only if (i) its paired (Z + D) / 2 gain over v5 has a 95 % interval whose
    lower end is above zero, (ii) all five guards hold and (iii) both core cells hold. Five candidates are judged with no
    multiplicity correction (disclosed); Tier 2 is the safeguard. If none passes, that is the result: equal weights stand.
    Nothing is adopted by this run in any case; Uzayr decides.
  - **Tier 2, only if a candidate passes Tier 1:** the six feature components retrained in inner folds of each scored
    model's own training sessions (leave one training session out), the candidate's weights refitted on those clean
    held-out outputs and rescored under the same rule; no CNN is retrained. How the CNN components enter the inner pools
    (they are not retrained) is fixed in a further dated note before Tier 2 runs, and Tier 2 asks the Mastermind for its
    own slot. Adoption needs Tier 2 to pass the same rule.
  - **Diagnostics (1a; no weight fitted)**, per component, on every cell above (the 3 Z, 10 D, 5 guard and 2 core cells)
    and per held-out session (loso_X on X): top-1 accuracy, log-loss and Brier score of softmax(m_c); calibration error (10
    equal-width bins of the top probability); sharpness (the mean of max minus min of log_softmax(m_c), and of the 0 s
    window's c_k, comparable with the 1 Oct screen's 10.06); the share of v5's winning margin each component supplies (per
    walk, w_c g_c (m_c[top] - m_c[second]) over the sum of those terms, averaged); how often leaving it out flips v5's
    decision, split into right to wrong and wrong to right; pairwise error correlation (Pearson, of the error indicators)
    and disagreement (share of walks whose argmax differs); the nine leave-one-component-out ensembles (paired against
    v5); how often the best component (by accuracy, and by log-loss) changes from held-out session to session, and which
    component BEST1 picks for each S. **Oracles, unattainable by construction:** per cell, the best single component's
    accuracy, and STACK fitted on the cell's own walks and scored on them.
  - **Intervals:** accuracies by `idw_eval._boot`, differences by `ixr_eval.paired` (participant bootstrap, 10,000
    resamples, seed 0, paired against v5 on the same walks). Names in code and runs; PA codes in anything for the report.
  - **Part 2** (the 630 features) is fixed in its own dated note before its first permuted score, after its offline
    equality check; it is not an adoption question.

- **2026-10-15 15:05. Components-and-features TEST: Part 2's design, fixed before its offline check runs and before any
  permuted score (same prompt and go as the 14:53 note).** Part 1 Tier 1 ended NULL (69ebe84e): no candidate passed, so
  Tier 2 does not run. Part 2 is not an adoption question; it is for the Discussion whatever it shows. Code
  `pipeline/identify/iv6_features.py`; outputs `runs/identify/v6_test/part2/` and `part2.json`. CPU only, one process,
  nice 19, OMP 1, the 13 GB guard and the 30 % floor, on the Mastermind's slot (its caffeinate).
  - **The offline path.** Engine v5's feature side exactly as `ilb_core.score_feat_b` replays it (`idw_core`'s
    `Prior.apply` against the causal pool of earlier 0 s windows of the walk's layout, `PerPath` for rf, the windows at 0,
    0.15 and 0.30 s, the 0.15 and 0.30 s inputs from `runs/identify/best/extract/tta`, hgb on rf_pace_prior's state), with
    each classifier called once on the stacked rows instead of row by row (forests pinned to one thread). **Check, before
    anything is permuted:** on the unpermuted bank its six feature components equal the stored replays' `c_*` arrays,
    every window, max abs difference 0.0, on every unit below. If a component's batched call is not bit-exact, that
    component is called row by row and the check rerun; any other difference stops the run and goes to the Mastermind.
    The CNN components are the stored arrays (a feature permutation cannot reach them).
  - **Units and cells.** xr_ABtrk_v5 on A3 (tracking walks) and on B2 (tracking walks), xr_A_v5 on B2 (all 299),
    loso_B1_v5 on B1 and loso_B2_v5 on B2 (identification walks); only the layouts a cell needs are scored (pools are per
    layout, so the others cannot change them). Cells: core xr_ABtrk A3+B2 path (240) and xr_A all B2 (299), both pooled
    as "core pooled" (539 rows); loso natural (180), slow (120), fast (119).
  - **Groups (40), from the names `family|variant|link|sub|name`:** the seven families (rhythm 219, cycle templates 129,
    Doppler contours 141, spectral shape 69, wavelets 54, modulation 12, cadence 6); each family on RX1, RX2 and RX3 (21);
    cadence's three across-link columns (the only across-link columns in the 630); all families on one link (3; added
    here, information); the Wi-Fi speed column alone; each family together with the Wi-Fi speed (7, for 2c).
  - **2a, the permutation.** Within each unit and layout (the walks sharing a calibration pool), one permutation of the
    walks moves the group's columns (and the speed, when in the group) from walk pi(j) to walk j, the same permutation for
    all three windows, before the pool sees anything; every other column and the path stay the walk's own. Seed
    SeedSequence([group index, repeat, session index, layout index]): the same session's walks move alike for every model.
    20 repeats. Per walk: v5's ensemble (the permuted feature components with the stored CNN components through
    `engine.Session.combine`'s formula and the stored a) and each feature component (the mean of its windows), correct
    or not, and the NLL of the true class. The drop = the unpermuted value minus the mean over the 20 repeats, per walk;
    participant bootstrap (10,000 resamples, seed 0). Also the spread of the drop over repeats.
  - **"Which three groups matter most"** = the three largest ensemble accuracy drops on "core pooled" among the seven
    families and the Wi-Fi speed alone (8 groups), with intervals; the per-link and identification-walk tables beside it.
  - **2b, person or day.** On the bank's walks of A1 to B2 (all tracking and identification walks), per family and for
    all 630: the engine's random forest (300 trees, sqrt, random_state 0) names the person across days (leave one
    session out) and names the session (leave one participant out), plus the day within Room A (A1, A2, A3) and within
    Room B (B1, B2), each leave one participant out; balanced accuracy against chance. Two inputs: raw (global per-path
    z-scores, no session information removed) and session-standardised (each session per path on its own rows, the
    engine's prior). Per column (raw): the share of variance between participants, the share between days within a
    participant (participant x session means), and their ratio; medians per family.
  - **2c, speed in disguise.** Per family, each column's correlation with the Wi-Fi speed (alpha 0.5) and the
    press-implied speed: median and largest |r| and the count above 0.3; and a ridge regression (alphas 10^-2 to 10^4,
    leave one session out) of each speed from the family, its R^2. With 2a's "family + Wi-Fi speed" groups against the
    family alone and the speed alone.
  - **2d, secondary only** (biased measures, never leading a conclusion): the forests' impurity importances and the
    LDA's mean |coefficient| over classes (its inputs are standardised), normalised and summed by family, per model.
  - **2e, optional:** not planned in this slot; only on a free machine and a separate grant.
  - **The figure** (only if 2a is clear): the ensemble accuracy drop for the seven families and the Wi-Fi speed, the two
    core cells side by side, 95 % intervals, Okabe-Ito colours with hatching for greyscale, 4.4 cm tall,
    `runs/identify/v6_test/id_feature_importance.pdf` (not copied to the report).
  - **Correction (2026-10-15 15:06):** the note above is headed 15:05, a typed time; the clock read 15:03:44 when it was
    appended (committed 72af18c1). Nothing else in it changes.
  - **Correction (2026-10-15 15:04:04, from the clock):** the correction line above is headed 15:06, also typed; the clock read 15:03:55
    when it was appended (cc8d3770).
