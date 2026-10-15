# Identification: the teaching pack, its checks, the addendum, and engine v2 (2026-10-01)

**Brief:** `reports/BRIEF_ID_TEACHING_2026-10-01.md` (verbatim, 69fc041) and its addendum
`reports/BRIEF_ID_TEACHING_ADDENDUM_2026-10-01.md` (5782af8).

**Rules before results:** the PLAN notes of 1 Oct in `runs/identify/engine/PLAN.md`:
- 09:54, aa500c3: the selection rule and the three checks;
- 10:32, 5782af8: the addendum's AC1 to AC3;
- 13:09, 46215b1: Uzayr's decision on the cadence bug;
- 13:37, db0898b: the rebuild checked and the selection re-applied.

**Development evaluation, all data seen.** Names are used throughout; tracking's codes differ (its "P5"
is PA2).

## 0. In short

- **The addendum's AC1 found a bug.**
  - **The bug:** on simulated walks with a known step rate, the step-rate (cadence) resolver read fast
    walks away from the TX at 0.73 to 0.91 of the truth, and only 33 of 48 grid walks fell within 5 %.
  - **The decision:** Uzayr adopted the fix as a bug fix (13:09, "Option 1").
  - **Engine v2** is the engine with that fix. Every figure was rebuilt on it, and nothing old was
    overwritten.
- **Engine v2's headline:** **35.56 % [21.11, 52.78]** on the 180 natural identification walks, against
  16.67 % chance.
  - It was 36.11 before the fix, and the fix's effect had been measured beforehand at -0.56.
  - Leave one session out: Room A 30.28 %, Room B 23.75 % (was 29.17).
- **Two statements weaken on engine v2. Both are reported plainly:**
  - the engine no longer separates from its own Wi-Fi speed alone at natural pace: +11.67 [-1.67, 25.56]
    (was +12.22 [0.56, 25.00]);
  - the feature components alone on B2 no longer separate from shuffled labels: p = 0.143 (was 0.048).
- **The worked walks:**
  - The rule, re-applied unchanged, chose two of **PA4's** walks towards the TX on B2.
  - It fell back from PA2's cell, because none of his B2 natural walks is right on engine v2.
  - The wrong walk is named PA1 at 0.4405; the right walk is PA4 at 0.4446.
- **Replay equals live:** 299 of 299 decisions on engine v2, with the ensemble difference 0.0.
- **The checks:**
  - **substitution:** the decision follows the swapped-in radio in 91.67 % [75.00, 100.00] of swaps;
  - **shuffled labels:** the full engine scores 20.00 % [13.33, 28.33] against 16.67 % chance;
  - **conditioning ablation:** removing the log and mean subtraction costs 10.56 [-22.78, -2.78], the only step whose removal is separable from zero; the band-pass alone costs nothing.
- **The addendum:**
  - **AC1:** the bug and its fix. Engine v2 resolves 48 of 48 simulated walks within 5 %.
  - **AC2 (same day, confounded by recording):** 55.00 % [26.67, 81.67] on B1 and 70.83 % [50.00, 91.67] on B2, against 35.00 and 37.50 cross-day on the same walks.
  - **AC3 (training without the slow and fast walks):** natural -1.11 [-7.78, 7.78], slow -5.83 [-10.83, -1.67]; the paced walks help paced walks, not natural ones (information).
- **The pack:** one JSON file of 1.10 MB (under 3 MB, so not split), with the notes, the README (field guide of 1,816 rows) and 9 check plots: 12 files for Uzayr to upload (section 7).

## 1. The cadence bug and engine v2

**How it was found (AC1).**
- **The grid:** 48 simulated walks (step rates 1.5 to 2.2 Hz, both directions, 1.0, 1.2 and 1.4 m/s,
  from standing).
- **The path:** the walks went through the engine's own extraction, unmodified: amplitude, the causal
  clock, the 3 s window and `pass_features`.
- **The result on engine v1:**
  - the resolver was within 5 % on 33 of 48;
  - fast walks away read 0.73 to 0.91 of the true rate;
  - the envelope method was within 5 % on 36.
- **The brief's reading:** this is a bug.

**The cause and the fix.**
- **The cause** is in `idmax_features.resolve_cadence`:
  - every channel's estimates vote equally;
  - channels with no rhythm give estimates at the 0.8 Hz band-pass edge;
  - `_candidates` doubles those into the step band.
- **The fix:**
  - only channels whose autocorrelation peak is at least 0.30 vote (the threshold the cadence diagnostic
    already uses for a clear rhythm);
  - if none qualifies, every channel votes as before.
- **Where it lives:** in `engine.extract_window`, as a scoped swap. The frozen module's text is unchanged,
  and its other callers keep the old rule (80cbf0c).
- **What it touches:** only the gait features (the cadence-scaled families cad, rhy, tplacf and dop).

**The effect, measured before the decision (information).**
- **The method:** feature re-scoring with the engine unchanged (839e6d1).
- **The result:**
  - natural walks 35.56 against 36.11 (-0.56 [-3.89, 2.78]);
  - Room A tracking -0.56;
  - Room B tracking -5.42 [-8.75, -1.67];
  - 944 of 1,019 windows' features change.
- **Uzayr's rule for bugs:** adopted whatever their effect (PLAN note 13:09).

**The rebuild and its checks** (`pipeline/identify/ixt_rebank.py`; PLAN note 13:37).
- **The banks:**
  - one pass of the engine's own Extractor at T 2.5, 3.0 and 3.5;
  - every decision time and Doppler map is asserted equal to the v1 banks;
  - the gait features changed in 944 of 1,019 windows at T 3.0 (952 at T 2.5 and 3.5).
- **The models:** ten `_x` models (five leave one session out, the deployment model and four T models):
  - the five feature components retrained on the same rows, heads and seeds;
  - the CNN files copied unchanged, since the maps are equal;
  - each with a manifest.
- **The replays:** all nine (five sessions, four T models) have features and maps equal to the v2 bank on
  every window.
- **The figures match the prediction:** the evaluation gives 35.56 on natural walks (35.00 to B2, 35.83 to
  B1), exactly the re-scoring's prediction.
- **AC1 re-run on engine v2:** 48 of 48 within 5 %, median 0.993 (`runs/identify/teaching/synth_grid/synth_grid_x.json`).
- **The real walks:**
  - on the 180 natural walks, the resolved step rate changed by more than 5 % on 96;
  - on the 19 walks whose energy envelope shows a clear rhythm, the median ratio to the envelope moved
    from 0.886 to 0.996;
  - agreement within 10 % went from 5 to 4 of those 19.
- **Slow tests on engine v2** (`IDE_SLOW=1`, `tests/test_ide_engine.py` and `tests/test_ide_rigrun.py`):
  13 of 13 passed in 12.6 minutes (`runs/identify/teaching/logs/slow_tests_x.log`). They cover:
  - the app's replay equals the harness;
  - the rig run equals the harness on the whole of B2;
  - speed 1 equals maximum speed;
  - starting from any recording equals the whole day;
  - the fake serial port equals the recorded source;
  - the guard;
  - no warm-up;
  - the deployment manifest, now `deploy_all5_x`.

**The fix's effect on the worked walks' features.**
- **v1's worked walks** (AC1's instruction: PA2, positions 50 and 56): the effect is recorded in
  `runs/identify/teaching/synth_grid/cadence_fix_check.json` (`worked_walks`).
- **Engine v2's worked walks** (PA4): the resolved step rates are 2.27 Hz (wrong walk) and 1.83 Hz (right
  walk).

## 2. The two worked walks

| | wrong walk | right walk |
|---|---|---|
| who | PA4 | PA4 |
| session, recording | B2, `participant_PA4_idpath_d2_natural` | the same |
| pass in the recording (replay position) | 1 (151) | 7 (157) |
| direction (true, detected) | towards, towards | towards, towards |
| the app said | PA1, 0.4405 (runner-up PA4 0.3436) | PA4, 0.4446 (runner-up PA1 0.3873) |
| Wi-Fi speed | 1.18 m/s | 1.03 m/s |
| calibration walks seen | 151 | 157 |
| decision after the press | 3.35 s | 3.33 s |

**Which branch of the rule decided each choice** (`runs/identify/teaching/selection_x.json`):
1. **The confusion:**
   - three cells tie at 4 walks: PA2, PA4 and PA5 named as PA1;
   - their row totals are equal (10 each);
   - the first recording ranks PA2, then PA4, then PA5.
2. **The fallback:**
   - PA2's cell has no qualifying recording, because none of his 10 B2 natural walks is right on
     engine v2;
   - the rule's fallback takes cell 2, PA4 named as PA1.
3. **The recording:** PA4's natural recording, the first with a right and a wrong walk in the same
   direction (the preferred branch).
4. **The wrong walk:** the first of that confusion in the recording.
5. **The right walk:** a correct walk in the same direction, whose confidence is closest to the median of
   all correct B2 natural walks (0.4446; it equals it to 4 figures).

**Before the fix**, the same rule on engine v1 chose PA2 named as PA1 (5 walks, no tie; positions 50
and 56). That selection (`selection.json`, 5a62cf4) is kept as superseded.

## 3. Verification against the app

1. **Replay equals live.**
   - **The run:** B2 streamed through the live app's rig path (`identify_recorded`, `EngineConsumer`,
     `loso_B2_x`).
   - **The result:** it equals the saved harness replay on **299 of 299** decisions: the same press times,
     the same argmax, and the ensemble equal (maximum difference 0.0).
   - **The record:** `runs/identify/teaching/verify_B2_x.json`, with the run's log in
     `verify_B2_x_rig_path.jsonl`.
   - **On engine v1** the same check also gave 299 of 299 (`verify_B2.json`).
2. **The worked walks' numbers.**
   - The pack's app-level numbers are the run's own decision records, so they are equal exactly.
   - **Against the run's JSON lines log:**
     - decision, runner-up, direction and calibration count are equal;
     - probabilities, confidence, Wi-Fi speed and latency agree to the log's rounding (largest
       difference 4.7e-4, from latency logged to 3 decimals).

## 4. The three checks

**C1. The substitution test** (B2 natural walks, `loso_B2_x`, causal; `substitution_x.json`).

| | variant A (host's pool) | variant B (pool rebuilt for the donor) |
|---|---|---|
| swapped decision equals the donor's own decision | **91.67 % [75.00, 100.00]** | 91.67 % [75.00, 100.00] |
| accuracy against the donor | 33.33 % [8.33, 66.67] | 33.33 % [8.33, 66.67] |
| accuracy against the host | 16.67 % [0.00, 33.33] | 16.67 % [0.00, 33.33] |

- **The answer follows the radio.**
  - All 10 swapped decisions that name the host are cases where the donor's own walk was already named
    as the host in its own slot.
  - The 5 swapped decisions that differ from the donor's own are all PA6's radio in PA1's slot,
    which becomes PA5: the calibration pool tips it, and it never becomes the host.
  - References: the donors' own accuracy is 41.67 %, the hosts' 35.00 %.
- **The worked walks:** both, given PA5's radio, are named PA5 (0.4071 and 0.4106).
- **The method** (PLAN C1): the swapped window is the donor's own engine window.
  - Its frames are timed by the donor's own causal clock.
  - The brief's frame splice from press - 1 s to + 4 s, time-shifted, holds every frame of that window,
    and a time shift changes no feature.
  - So this is the splice, minus the mixing of two clock estimates.
- **On engine v1:** 91.67 % [75.00, 100.00] as well.

**C2. The shuffled-label control** (to B2, causal; `shuffled_full_x.json`, `shuffled_null_x.json`).
- **The full engine,** with labels permuted within each training session (seed 0), scores **20.00 %
  [13.33, 28.33]** on B2's 60 natural walks, against 16.67 % chance.
  - On all 299 B2 windows it scores 16.05 %.
  - It names nobody in particular: the predicted shares run from 8.3 % to 28.3 %.
  - Feature components were retrained on the v2 bank with the same permutation; the shuffled CNNs were
    copied from the v1 control, since the maps are unchanged.
- **The feature-only null (20 permutations):**
  - real labels 26.67 %;
  - null mean 18.33 %, maximum 31.67 %;
  - **p = 0.143**.
  - In plain words: on B2, the five feature components alone are not distinguishable from shuffled labels
    on engine v2. On v1 they were (35.00 %, p = 0.048).
- **Where B2's 35.00 % comes from** (information): the CNNs alone score 31.67 % on B2 and 30.00 % [12.78,
  53.33] on both folds; the features alone score 26.67 % and 22.22 % [15.56, 30.00]
  (`pack: results.component_families`).

**C3. The conditioning ablation** (information only; walks folds; the CNNs retrained per variant, the
engine's feature components kept; `ablation_x.json`).

| variant | natural | slow | fast | natural, paired against the engine |
|---|---|---|---|---|
| the engine | 35.56 [21.11, 52.78] | 26.67 | 26.89 | |
| V1, no band-pass | 35.56 [23.89, 44.44] | 24.17 | 26.89 | 0.00 [-10.00, 6.67] |
| V2, PC1 kept | 30.56 [18.33, 44.44] | 24.17 | 19.33 | -5.00 [-13.89, 4.44] |
| V3, subcarrier mean instead of PCA | 21.67 [10.00, 34.44] | 19.17 | 21.85 | -13.89 [-29.44, 2.22] |
| V4, no log and no mean subtraction | 25.00 [17.22, 32.22] | 27.50 | 25.21 | **-10.56 [-22.78, -2.78]** |

- **In plain words:** conditioning matters, but not every step does.
  - Removing the log and mean subtraction costs 10.56 points, an interval below zero.
  - Replacing PCA with the subcarrier mean costs 13.89, not quite separable.
  - Keeping PC1 costs 5.00, not separable.
  - Removing the band-pass costs nothing.
- **Identity-blind:**
  - RX2's 10 to 35 Hz energy on natural walks is a median 1.45 times the training day's empty room raw
    (23 % of walks above twice it);
  - after conditioning it is 6.37 times (91 %) (`runs/identify/teaching/ablation/maps.json`).
- **The scoring:** the ablation's CNNs do not depend on the cadence fix. The scoring used engine v2's
  feature components from the v2 replays.

## 5. The addendum

**AC1. The step-rate estimator on simulated walks:** section 1.

**AC2. Same day, confounded by recording** (`runs/identify/teaching/extra/extra.json`).

- **The method** (PLAN AC2): within each recording of a Room B day, passes are paired into cycles by
  press time. Cycles 1, 3, 5 and so on train the full engine recipe on that day alone; cycles 2, 4, 6 and
  so on are scored causally. The bank is engine v2's.

| day | test walks | same-day model | cross-day engine (`loso_<day>_x`), same walks | paired, natural |
|---|---|---|---|---|
| B1, natural | 60 | 55.00 [26.67, 81.67] | 35.00 [18.33, 48.33] | +20.00 [0.00, 41.67] |
| B1, all paces | 108 | 49.07 [30.56, 69.44] | 31.48 [19.44, 42.59] | |
| B2, natural | 24 | 70.83 [50.00, 91.67] | 37.50 [12.50, 66.67] | +33.33 [16.67, 54.17] |
| B2, all paces | 72 | 54.17 [36.11, 70.83] | 31.94 [19.44, 48.61] | |

- **Chance** is 16.67 %.
- **In one plain sentence:** each person's walks come from their own recording slot, so this measures
  recognising the person plus their recording, which is exactly why published same-session figures run
  high.
- **The B2 counts:** B2's natural blocks hold 10 walks per person, so its test cycles hold only 24 natural
  walks.

**AC3. Training without the slow and fast walks** (information only).

- **The method** (PLAN AC3): for "to B2" and "to B1", the engine recipe was retrained on the same rows
  minus the other Room B day's slow and fast identification walks. Engine v2's bank was used, and each
  test day was replayed causally.

| block | without paced walks | the engine | paired | without minus S0 | the engine minus S0 | without minus S_wifi | the engine minus S_wifi |
|---|---|---|---|---|---|---|---|
| natural | 34.44 [18.33, 51.11] | 35.56 | -1.11 [-7.78, 7.78] | -3.89 [-27.78, 18.89] | -2.78 [-26.11, 15.56] | +10.56 [-6.67, 32.22] | +11.67 [-1.67, 25.56] |
| away | 30.00 | 30.00 | 0.00 [-8.89, 8.89] | -7.78 | -7.78 | +7.78 | +7.78 |
| towards | 38.89 | 41.11 | -2.22 [-6.67, 6.67] | 0.00 | +2.22 | +13.33 | +15.56 |
| slow | 20.83 [5.83, 40.00] | 26.67 | **-5.83 [-10.83, -1.67]** | +3.33 [-15.83, 19.17] | +9.17 [-13.33, 29.17] | 0.00 [-10.83, 10.83] | +5.83 [-9.17, 20.00] |
| fast | 23.53 [13.68, 32.50] | 26.89 | -3.36 [-13.33, 6.72] | +6.72 [-10.92, 25.00] | +10.08 [-13.45, 30.25] | -4.20 [-18.49, 13.45] | -0.84 [-18.49, 15.13] |

- **The answer to "why are the paced walks in training":** they help the paced walks, measurably on slow
  walks, and make no measurable difference to natural walks.
- **Information only:** the engine is not changed, because choosing now would be choosing on the test
  days.

## 6. Engine v2 against engine v1

| figure | v1 (30 Sept) | v2 (1 Oct) |
|---|---|---|
| natural identification walks | 36.11 [24.44, 52.22] | **35.56 [21.11, 52.78]** |
| to B2, to B1 | 41.67, 33.33 | 35.00, 35.83 |
| slow, fast | 24.17, 30.25 | 26.67, 26.89 |
| engine minus S0 (natural) | -2.22 [-25.56, 15.56] | -2.78 [-26.11, 15.56] |
| engine minus S_wifi (natural) | +12.22 [0.56, 25.00] | **+11.67 [-1.67, 25.56]** |
| engine minus S0 (fast) | +13.45 [-5.04, 30.01] | +10.08 [-13.45, 30.25] |
| engine without pace (natural) | 30.56 | 29.44 |
| CAL-none (natural) | 32.78 | 32.78 |
| leave one session out, Room A | 30.83 | 30.28 [22.50, 37.22] |
| leave one session out, Room B | 29.17 | **23.75 [18.75, 28.75]** |
| one-press cost, walks | -3.89 | -4.44 [-16.67, 7.78] |
| one-press cost, tracking pooled | -5.50 [-12.33, 1.67] | -8.00 [-13.00, -2.33] |
| AUROC of confidence | 0.60 | 0.585 |
| named PA1, of 180 | 63 | 63 |
| PA2, natural | 16.67 | 10.00 |
| T 2.5, T 3.5 (information) | 29.44, 35.56 | 32.22, 34.44 |

- **Sources:**
  - `runs/identify/engine/eval/eval_x.json`;
  - `runs/identify/final_extras/measures/measures_x.json`;
  - `runs/identify/engine/eval/one_press_cost_tracking_information_x.json` (from `ixt_v2`, whose `--v1`
    mode reproduces the v1 file exactly).
- **The v1 files are unchanged.**

## 7. The pack

**Files for Uzayr to upload to the new chat** (all under `reports/teaching/`):

| file | bytes |
|---|---|
| `id_teaching_pack_2026-10-01.json` | 1,099,561 |
| `ID_TEACHING_NOTES_2026-10-01.md` | 33,346 |
| `README_ID_TEACHING_PACK.md` | 190,139 |
| `check_png/01_rx2_raw_and_map_right.png` | 129,556 |
| `check_png/01_rx2_raw_and_map_wrong.png` | 130,019 |
| `check_png/02_cnn_score_evolution.png` | 42,632 |
| `check_png/03_component_logprobs.png` | 25,835 |
| `check_png/04_confusion_B2.png` | 26,328 |
| `check_png/05_substitution.png` | 22,177 |
| `check_png/06_shuffled_label.png` | 24,490 |
| `check_png/07_conditioning_ablation.png` | 17,447 |
| `check_png/08_ac1_step_rate.png` | 21,702 |

**What the pack holds** (`pipeline/identify/ixt_pack.py`, built with `--final`):
- **Provenance fields:** the schema version, the build time, the git commit, the PLAN's SHA-256,
  `engine_version` 2, and the models with their manifests' training sessions.
- **The selection.**
- **The two walks, opened up:**
  - identity and context, the press time, and the truth for teaching only;
  - the event timeline;
  - the raw signal per link;
  - five conditioning steps per link;
  - the gait-feature path with all 630 features, raw and standardised;
  - direction and speed;
  - the evidence, with each component and the CNN scores evolving per window;
  - the drivers (diagnostics);
  - the substitution;
  - the app's own values.
- **The model:**
  - the settings;
  - the CNN layer tables (19,890 and 19,602, equal to the saved weights);
  - the components, the LDA's fitted shrinkage and the features by family;
  - the training statistics of `loso_B2_x` and `deploy_all5_x`;
  - chance.
- **The results:**
  - the headline;
  - the component families;
  - the confusion matrices;
  - per person;
  - leave one session out;
  - the pace confound;
  - CAL-none;
  - the deployment measures;
  - confidence coverage;
  - the one-press cost;
  - T sensitivity;
  - latency;
  - the two-press reference;
  - physics;
  - the rejected candidates.
- **Provenance:** 17 rows, 5 of them flagged as chosen with test results in view.
- **The timeline:** 21 entries, with 36.11 struck through and 35.56 current.
- **The checks** and **the addendum:** AC1 before and after the fix, AC2 and AC3.
- **Every result entry** carries `value`, `ci_low`, `ci_high`, `n`, `train_sessions`, `test_session`,
  `calibration`, `scored_set`, `source_file` and `source_commit`.
- **Names only:** the builder refuses any code.

## 8. What went wrong

- **The cadence bug** (section 1).
  - **Why nobody saw it:** the real-walk diagnostic of 30 Sept read the resolver as running "a median 12 %
    low" and called it a definitional gap.
  - **What found it:** simulated truth, which the addendum asked for.
  - **What it cost:** every figure was rebuilt, about two hours of compute (13:10 to 15:16).
- **The worked walks changed after the fix.** The rule was re-applied unchanged and the first selection
  was kept as superseded, but the page's worked example is now PA4, not PA2.
- **The pack's rounding destroyed the absolute press times.**
  - 4 significant figures turned a monotonic time of 848,7xx s into 848,700, caught in the provisional
    build.
  - Absolute clock times are now kept to 1e-6 s.
- **A code reached the pack:** the shuffled-label result listed its predicted shares by code (P1 to P6),
  caught by reading the file. Codes are now converted to names, and the builder refuses any code.
- **Two wrong sentences in the notes' first draft:**
  - which components leaned which way on the worked walks (the LDA's 0.96 on the right walk is for
    PA1, not PA4);
  - a claim that B2's accuracy "rests mainly on the CNNs".
  - Both were caught by checking against the pack before committing. The second is now a measured figure
    (`component_families`).
- **A shell slip:** a path list was not split by zsh, and the commit was refused. It was retried with an
  array; nothing wrong was committed.

## Commits

| commit | what |
|---|---|
| 69fc041 | the brief saved verbatim |
| 8d67a05 | Part 1: the merged handoff (morning) |
| aa500c3 | PLAN note: the selection rule and the three checks, before looking |
| 5a62cf4 | the v1 selection (PA2; superseded) |
| c01ed6d, 83ee53b, cfa1838 | the checks' runners, the pack builder, the compute lanes |
| 5782af8 | the addendum saved verbatim; PLAN note defining AC1 to AC3 |
| 1d19960, 7630ca6 | the addendum's code; the README field-guide generator |
| 9657f91 | AC1: the cadence resolver is biased on simulated truth |
| 839e6d1 | the fix's effect measured for Uzayr's decision (information) |
| 46215b1 | PLAN note: Uzayr adopts the fix (engine v2) |
| 80cbf0c | engine v2: the fix in the engine's one code path; the v2 bank and model builder |
| e7eb81f | the downstream scripts on v2; AC1 re-run on v2; bank records and manifests |
| db0898b | PLAN note: the rebuild checked; the selection re-applied; verification 299 of 299 |
| 185d4af | the v2 results: evaluation, measures, replays' summaries, the checks |
| 8183dda | the pack, notes, README, plots, ablation, AC2 and AC3, thesis summary section 13, the afternoon handoff |
| the next commit | this report, and the pack rebuilt so its `git_commit` names the committed builder (8183dda); only that field and `generated_at` differ |
