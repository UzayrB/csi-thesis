# Identification teaching notes, for the page writer (2026-10-01)

**For:** the claude.ai chat building the identification teaching page. It cannot see the repository.

**How to use this file:**
- **Prose facts:** it gives the facts the page's prose needs, chapter by chapter (the spec's chapters 00
  to 10).
- **Sources:** every fact names its source as a repository file and section, or as a pack path (`pack:
  <path>`). Results also state their train and test partition.
- **Numbers:** all of them are in the pack, `id_teaching_pack_2026-10-01.json`. Where this file and the
  pack disagree, the pack is right and this file is wrong.

**Conventions:**
- **Development evaluation, all data seen.**
- **Engine v2.**
  - Every engine figure here is from engine v2: the one-press engine with the cadence bug fixed (1 Oct
    2026, section 08).
  - Older figures appear only in the timeline, struck through.
- **Names only, never codes.** Tracking's code order differs: its "P5" is PA2, while identification's
  old P5 was PA4 (the key is in the README).
- **Partitions:**
  - **the walks folds:** each Room B identification walk is scored by the model that never saw its day.
    "To B2" trains on A1, A2, A3 and B1 and tests B2; "to B1" trains on A1, A2, A3 and B2 and tests B1.
  - **leave one session out:** train on four sessions, test the fifth (tracking walks, route known).
- **Intervals:** 95 %, by bootstrap over participants (10,000 resamples, seed 0). The interval runs from
  `ci_low` to `ci_high` in the pack.

## What changed recently (the box on chapter 00)

| date | what | source |
|---|---|---|
| 29 Sept | the development ensemble (two presses per walk) | `reports/ID_DEV_FINAL_2026-09-29.md` |
| 30 Sept, morning | the audit fixed two bugs (B-1, a hidden pace proxy; B-2, the maps' log constant) and adopted no candidate | `reports/ID_AUDIT_2026-09-30.md` |
| 30 Sept | one model, which is the live app: one press, a 3 s window, 36.11 on natural walks. GS (amplitude normalisation) rejected on 600 tracking passes (-2.00) | `reports/ID_FINAL_2026-09-30.md` |
| 30 Sept, afternoon | a bounded last attempt at a gain adopted nothing (A1 to A4); names used; no warm-up; the rig run gives 299 of 299 after a time-base fault was fixed | `reports/ID_EXTRAS_2026-09-30.md` |
| 1 Oct, morning | this pack, with three new checks (substitution, shuffled labels, conditioning ablation) | `reports/ID_TEACHING_PACK_2026-10-01.md` |
| **1 Oct, 13:09** | **the cadence bug.** The addendum's simulated walks (AC1) showed the step-rate resolver biased on fast walks. Uzayr adopted the fix as a bug fix (engine v2) and every figure was rebuilt. The headline moved from 36.11 to **35.56** and the worked walks changed (the rule, re-applied, chose PA4 instead of PA2) | `pack: addendum.AC1_step_rate_simulated`; `runs/identify/engine/PLAN.md` notes of 1 Oct 13:09 and 13:37 |

## 00. The two walks

- **Who and which:** two of PA4's walks towards the transmitter (`A_rev`), in his natural block on B2,
  the second Room B day (`pack: selection`, `walks.*`).
  - The model is `loso_B2_x`, trained on A1, A2, A3 and B1 only, so it never saw B2.
  - The calibration is causal: the session's earlier walks only, unlabelled.
- **The rule chose them before looking.** It was written in the PLAN note of 1 Oct 09:54 (commit aa500c3)
  and re-applied unchanged to engine v2 at 13:37 (db0898b).
  - **The commonest confusion:** three cells tie at 4 walks: PA2, PA4 and PA5 named as PA1.
    Each person has 10 natural walks, and the next tie-break (first recording) puts PA2 first.
  - **The fallback:** on engine v2 none of PA2's 10 B2 natural walks is right, so no recording of his
    holds a right and a wrong walk. The rule falls back, as written, to the next cell: PA4 named as
    PA1 (`pack: selection.fallbacks`, `selection.branches`).
  - **The recording:** PA4's natural recording holds right and wrong walks in the same direction.
  - **The wrong walk** is the first such confusion, pass 1 of his recording (replay position 151 of 299).
  - **The right walk** is pass 7 (position 157). Its displayed confidence, 0.4446, is closest to the
    median of all correct B2 natural walks (0.4446): a typical right walk, not the best.
- **What the app said** (`pack: walks.<role>.app`). These are the live app's own logged values from a
  rig-path replay of B2, unrounded.

  | | wrong walk | right walk |
  |---|---|---|
  | truth | PA4 | PA4 |
  | top identity (displayed confidence) | PA1 (0.4405) | PA4 (0.4446) |
  | runner-up (displayed confidence) | PA4 (0.3436) | PA1 (0.3873) |
  | ensemble probability of the top | 0.879 | 0.751 |
  | margin, log units | 1.99 | 1.11 |
  | direction detected | towards (`A_rev`), right | towards, right |
  | Wi-Fi speed | 1.18 m/s | 1.03 m/s |
  | press speed (S0 reference, not a model input) | 1.10 m/s | 0.95 m/s |
  | decision after the press | 3.35 s | 3.33 s |
  | calibration walks seen | 151 | 157 |
- **Replay equals live:** that rig-path run equals the thesis harness on 299 of 299 decisions
  (`pack: checks.verification`).

## 01. What gait does to Wi-Fi

- **The rig** (`pack: model.settings.node_positions_m`):
  - TX at (2.5, -0.5);
  - RX1 at (2.5, 5.5);
  - RX3 at (5.5, 2.5);
  - RX2 at (2.0, -0.5), beside the TX, for the identification walks, and at home (-0.5, 2.5) for
    tracking.
  - The identification path is line A, x = 2.5, from y = 0 to 5. Away is `A_fwd` (from the TX) and
    towards is `A_rev`.
- **Doppler from a moving body:**
  - a reflection's path length L = |p - TX| + |p - RX| changes at dL/dt = (u_TX + u_RX) . v, where u
    are the unit vectors from each node to the body;
  - amplitude-only CSI then fluctuates at f = |dL/dt| / lambda = 2 F v / lambda;
  - F = |(u_TX + u_RX) . v_hat| / 2 is the projected bistatic factor, between 0 and 1;
  - lambda = 0.123 m (channel 11, 2.462 GHz) (`pack: model.settings.lambda_m`;
    `pipeline/identify/id15_factor_map.py`).
- **F along line A** (`pack: model.settings.F_along_line_a_identification_layout`):
  - RX2: 0.981, both directions;
  - RX3: 0.50;
  - RX1: 0.
- **Why RX2 beside the TX gives F of about 0.98:**
  - TX and RX2 sit side by side at the start of line A, so both rays to a walker on the line point almost
    exactly along the walk;
  - u_TX + u_RX is then close to 2 v_hat;
  - on RX1, opposite the TX on the same line, the two rays are anti-parallel and cancel: F = 0, so there
    is no Doppler at all;
  - RX3, side-on, gives about 0.5.
- **The torso:** predicted 19.5 Hz at RX2 for the measured speeds; measured 18.75 Hz, both directions (90
  walks each). The FFT bin is 2.34 Hz, so they agree to within one bin (`pack:
  results.physics.torso_hz_rx2`; identity-blind; B1 and B2).
- **Limbs:**
  - limbs would sit higher, from 35 to 75 Hz;
  - that band is above twice the empty room in 53 % of natural walks (torso band: 99 %);
  - limb features add nothing to identity (`pack: results.physics.limb_bands_rx2_over_empty_room`).
- **Rhythm:** a step or stride rhythm is visible in about 30 % of natural walks (`pack:
  results.physics.rhythm_visibility_natural_rx2`). My reading: this is why gait features are weak on one
  3 s window.

## 02. Signal conditioning

- **The steps, per link, on the 3 s window** (`pack: walks.<role>.links.<link>.conditioning`; code
  `idz_bank.conditioned_map_v2`):
  1. the 103 CSI amplitudes resampled on a 150 Hz grid;
  2. a 4 to 70 Hz band-pass;
  3. a per-window PCA with PC1 discarded (it carries common-mode power changes), PCs 2 to 4 kept;
  4. an STFT per kept PC: a 32-sample window, hop 8, a 64-point FFT, so bins of 2.34 Hz and 18.75 frames
     per second;
  5. the magnitude summed over the PCs in 28 bins from 4.7 to 68 Hz, then a log with a relative constant
     (1e-6 times the map's median), minus the map's mean. This is the CNN's input.
- **Was it vital? The ablation** (information only; walks folds; causal; `pack:
  checks.conditioning_ablation`):
  - **The method:** the three CNN components were retrained without one step at a time, keeping the
    engine's feature components.
  - **The result,** on natural walks, paired against the engine's 35.56 %:

    | variant | natural | change, paired | separable from zero? |
    |---|---|---|---|
    | V1, no band-pass | 35.56 | 0.00 [-10.00, 6.67] | no |
    | V2, PC1 kept (PCs 1 to 3) | 30.56 | -5.00 [-13.89, 4.44] | no |
    | V3, the subcarrier mean instead of PCA | 21.67 | -13.89 [-29.44, 2.22] | no, but close |
    | V4, no log and no mean subtraction | 25.00 | **-10.56 [-22.78, -2.78]** | **yes, worse** |

  - **In plain words:** conditioning matters, but not every step does.
    - The log and mean subtraction is measurably needed.
    - Replacing PCA with the subcarrier mean costs about 14 points, not quite separable.
    - Keeping PC1 costs 5, not separable.
    - The band-pass alone makes no difference to accuracy.
  - The page should say exactly this, not that every step was vital.
- **Identity-blind:** RX2's 10 to 35 Hz energy over the training day's empty room, on natural walks
  (`pack: checks.conditioning_energy_identity_blind`):
  - raw: a median 1.45 times the empty room, with 23 % of walks above twice it;
  - conditioned (PCs 2 to 4 of the band-passed window): 6.37 times, with 91 % above twice it.
  - Conditioning is what lifts the walker's torso band clear of the empty room.

## 03. Segmentation from one press

- **The window:**
  - one space-bar press at the walk's start sets t0;
  - the window is [t0, t0 + 3 s];
  - the decision comes once every receiver has a packet past t0 + 3 s on its causal clock, or at t0 + 4 s
    at the latest;
  - the median packet wait is 0.03 s after the window (`pack: results.latency_s`).
- **The causal clock:**
  - each receiver's own microsecond clock is mapped to the host clock by the 5th percentile of the
    offset over the last 20 s of packets;
  - inside the windows it agrees with the whole-file map to 0.51 ms (99th percentile);
  - it handled the one receiver reboot (`pack: results.physics.clock_causal_vs_whole_file`).
- **What the app knows, and when:** the radio and the start press, nothing else.
  - **Never:** the end press, the walk's duration, the metre anchors, tracking's output, or any label.
  - **Calibration:** only earlier walks of the same session, unlabelled.
  - The metre anchors and the end press in the pack are flagged `truth_for_teaching_only_never_seen_by_the_model`.
- **The CNN windows:** 34 frames (1.81 s) at a hop of 4 frames inside the 3 s map, giving 5 windows per
  walk (`pack: model.settings.cnn_window`).

## 04. The features and the networks

- **630 gait features** (`pack: model.features_630_by_family`, `walks.<role>.gait_features`):

  | family | rhy | dop | tplacf | spec | wav | mod | cad |
  |---|---|---|---|---|---|---|---|
  | count | 219 | 141 | 129 | 69 | 54 | 12 | 6 |

  - **The families:** rhythm, Doppler contours, cycle templates, spectral shape, wavelets, modulation and
    cadence. All are shapes or ratios.
  - **The resolved step rate (cadence)** scales several families. Engine v2 fixed how it is resolved
    (section 09, AC1).
  - **The worked walks:**
    - the wrong walk's resolved step rate is 2.27 Hz and the right walk's 1.83 Hz;
    - no clear rhythm was visible in either walk's energy envelope (`pack:
      walks.<role>.gait_features.resolved_cadence_hz`, `envelope_cadence_hz`).
- **The CNNs** (`pack: model.cnn_3link`, `model.cnn_1link`, `model.saved_state_dict_totals`):
  - the 3-link CNN-v2 has 19,890 parameters and the 1-link one 19,602;
  - the layer-by-layer arithmetic is checked against the saved weights;
  - the CNN weights are those of 30 Sept, unchanged by the cadence fix (it touches only the gait
    features).
- **The eight components** (`pack: model.components`):
  - **three random forests** (300 trees):
    - one standardised per path;
    - two by the session (one with the Wi-Fi speed added);
  - **extra trees** with the Wi-Fi speed;
  - **a shrinkage LDA** with the Wi-Fi speed (fitted shrinkage 0.45 to 0.49 per class, `pack:
    model.lda_fitted_shrinkage_per_class_loso_B2`);
  - **the 3-link CNN**, plain and with AdaBN;
  - **the per-link CNNs** with AdaBN, summed.
- **Training** (`pack: model.training`):
  - `loso_B2_x` has 720 passes, 120 per person, from A1, A2, A3 and B1;
  - `deploy_all5_x` has all 1,019.

## 05. From evidence to an identity

- **The rule:**
  - sum the eight components' six log-probabilities, normalise, and take the argmax;
  - the displayed confidence is softmax(sum / 8), the geometric mean, which never changes the decision;
  - the runner-up is second in the same order.
- **Chance:** 16.67 % for six people; top-2 33.33 %; a household of g people 1/g (`pack:
  model.chance_pct`).
- **The two walks** (`pack: walks.<role>.evidence`):
  - **the wrong walk:** the per-link CNNs favour PA4 (0.57), but six of the other seven components lean
    PA1:
    - the LDA 0.51 and the 3-link CNN about 0.28;
    - the forests only slightly, 0.19 to 0.25;
    - the extra trees lean PA2.
    The sum names PA1 by 1.99 log units over PA4.
  - **the right walk:** the three CNN components carry PA4 (0.68 to 0.82), against an LDA that is 0.96
    sure of PA1. The two session-standardised forests also lean PA4, and the sum names him by 1.11
    log units.
  - The CNN scores evolve window by window (`evidence.cnn_evolution`). The feature components decide
    once, on the whole window.

## 06. The live app

- **Inputs:** radio from three receivers and one start press.
- **The screen:**
  - the direction, detected from RX2's 10 to 35 Hz energy slope (96.9 % right on 419 walks);
  - the top identity and runner-up, with the displayed confidence against chance;
  - the Wi-Fi speed and the latency;
  - the model;
  - "adapting to this room: n walks seen";
  - in recorded streams, the truth in green or red and a running score.
- **Keys:** SPACE (the press), `n` (new walker) and `q`.
- **Latency:**
  - a median 0.32 s after the window on this run (90th percentile 0.39 s), about 0.9 s before the
    walker's recorded end press;
  - the compute part is measured and varies from run to run (`pack: results.latency_s`).
- **The rig run:**
  - recorded B2, streamed through the real rig interface, equals the harness on 299 of 299 decisions on
    engine v2 (`pack: checks.verification`);
  - on engine v1 it did so at any speed, from any starting recording, and through the real serial parser
    (`reports/ID_EXTRAS_2026-09-30.md` section 4); the same tests were re-run on v2 (section 09);
  - a guard refuses any model trained on the streamed day;
  - no warm-up: the first walk is decided on training statistics (`tests/test_ide_rigrun.py`).
- **The render** (recorded B2's natural blocks as if live) will end at 21 of 60 (35.00 %) on engine v2.
  It was 25 of 60 on v1 and must be re-recorded.

## 07. How good it is

- **The headline** (walks folds, causal; `pack: results.headline.natural_both`):
  - **35.56 % [21.11, 52.78]** on the 180 natural identification walks, against 16.67 % chance;
  - to B2 35.00 %, to B1 35.83 %;
  - away 30.00, towards 41.11, slow 26.67, fast 26.89.
- **Confusion** (`pack: results.confusion_pooled`): 63 of the 180 natural walks are named PA1 (he has
  30). Per person: PA5 30.0, PA1 73.3, PA2 10.0, PA3 23.3, PA4 36.7, PA6 40.0.
- **Leave one session out** (tracking walks, known route; `pack: results.loso_tracking`):
  - Room A 30.28 % [22.50, 37.22] and Room B 23.75 % [18.75, 28.75];
  - per session: A1 30.00, A2 30.83, A3 30.00, B1 21.67, B2 25.83.
- **The pace confound, measured** (`pack: results.pace_confound`; walks folds):
  - **press speed alone (S0):** 38.33 % on natural walks. The engine minus S0 is -2.78 [-26.11, 15.56],
    so the engine does not beat a stopwatch it never has;
  - **its own Wi-Fi speed alone (S_wifi):** 23.89 %. The engine minus S_wifi is +11.67 [-1.67, 25.56],
    **no longer separable from zero** (on v1 it was +12.22 [0.56, 25.00]);
  - **the engine without its pace components:** 29.44 %;
  - **fast walks:** the engine 26.89 against S0 16.81, +10.08 [-13.45, 30.25], not separable.
  - **AC3, training without the slow and fast walks** (information; walks folds; causal; `pack:
    addendum.AC3_training_without_slow_and_fast_walks`):
    - **natural:** 34.44 % against the engine's 35.56, -1.11 [-7.78, 7.78];
    - **slow:** 20.83 against 26.67, **-5.83 [-10.83, -1.67]**;
    - **fast:** 23.53 against 26.89, -3.36 [-13.33, 6.72].
    - **Against the speed controls,** without the paced walks: natural minus S0 -3.89 [-27.78, 18.89],
      minus S_wifi +10.56 [-6.67, 32.22].
    - **The answer to "why are the paced walks in training":** they help the paced walks (slow
      measurably), and do not measurably help natural ones. The engine is not changed: choosing now
      would be choosing on the test days.
- **No same-day adaptation** (`pack: results.no_same_day_adaptation`): 32.78 % out of the box. Adapting
  adds +2.78 [-2.78, 8.33], not separable from zero.
- **Deployment measures** (`pack: results.deployment`):

  | measure | engine v2 | chance |
  |---|---|---|
  | top-2 | 56.11 | 33.33 |
  | round trip (natural) | 38.89 | 16.67 |
  | 3 walks | 42.59 | 16.67 |
  | 5 walks | 44.44 | 16.67 |
  | household of 2 | 70.33 | 50.00 |
  | household of 3 | 55.06 | 33.33 |
  | household of 4 | 45.72 | 25.00 |
  | household of 5 | 39.67 | 20.00 |

- **Confidence against coverage** (`pack: results.confidence_coverage`):
  - 39.26 % on the 75 % of walks it is most sure of, 37.78 % on the top half, 40.74 % on the top 30 %;
  - AUROC 0.585;
  - "confident" mostly means PA1: 14 of the 22 right answers in the top 30 % are his.
- **The cost of one press** (information; `pack: results.one_press_cost`):
  - **identification walks:** -4.44 [-16.67, 7.78], not separable;
  - **tracking passes:** -8.00 [-13.00, -2.33] pooled; Room A -9.17 [-15.00, -1.94], Room B -6.25.
- **T sensitivity** (information; T stays 3.0 s): T 2.5 gives 32.22 %, T 3.5 gives 34.44 %.
- **The same-day comparison (AC2, "same day, confounded by recording"; `pack:
  addendum.AC2_same_day_confounded_by_recording`):**
  - **The method:** within each recording of one Room B day, walk cycles alternate between training (1,
    3, 5 and so on) and testing (2, 4, 6 and so on). The engine recipe is trained on that day's training
    cycles only and scored causally on its test cycles.

    | day | same-day model, natural | cross-day engine, same walks | paired | chance |
    |---|---|---|---|---|
    | B1 (60 walks) | 55.00 [26.67, 81.67] | 35.00 [18.33, 48.33] | +20.00 [0.00, 41.67] | 16.67 |
    | B2 (24 walks) | 70.83 [50.00, 91.67] | 37.50 [12.50, 66.67] | +33.33 [16.67, 54.17] | 16.67 |

  - **All paces:** 49.07 (B1) and 54.17 (B2), against 31.48 and 31.94 cross-day.
  - **In one plain sentence:** each person's walks come from their own recording slot, so the same-day
    figure measures recognising the person plus their recording, which is exactly why published
    same-session figures run high.

## 08. What changed and when

- **The timeline:** `pack: timeline` holds every headline since 12 September, with its value,
  partition, calibration, status and why it was superseded.
- **The main line:**
  - 15.83 (Room A nested, 23 Sept);
  - 26.67 (DC2 pre-registered, 28 Sept);
  - 39.72 and 30.00 (the development ensemble, 29 Sept);
  - 46.67 (identification walks, 29 Sept);
  - 43.33 (after bug B-1);
  - 36.11 (the one-press engine, 30 Sept);
  - **35.56 (engine v2, 1 Oct, current).**
- **Why 36.11 was superseded:**
  - the cadence bug, found by the addendum's simulated walks (AC1) and fixed as a bug whatever its
    effect;
  - its effect had been measured beforehand by re-scoring the features (-0.56 [-3.89, 2.78]), and the
    rebuild gave the same 35.56;
  - the rule "bug fixes are adopted whatever they do" is the audit's.

## 09. How we know it is right

- **The substitution test** (`pack: checks.substitution`; B2 natural walks; `loso_B2_x`; causal):
  - **The donor:** each host walk's slot gets the next natural walk by a different person, in the same
    direction.
    - Its engine window is classified with the host's calibration pool (variant A).
    - In variant B, the pool is rebuilt as if the donor had walked that slot.
  - **The result:** the decision follows the radio:
    - **91.67 % [75.00, 100.00]** of swapped decisions equal the donor's own decision in its own slot,
      in both variants;
    - accuracy against the donor is 33.33 %, and against the host 16.67 %;
    - all 10 swapped decisions that name the host are cases where the donor's own walk was already named
      as the host in its own slot, so nothing comes from the host's pool.
  - **The worked walks:** both, given PA5's radio, become PA5 (`pack: walks.<role>.substitution`).
  - **The method:** the swapped window is the donor's own engine window. Its frames, timed by the
    donor's own causal clock, give exactly the donor's features, so no time shift changes them (PLAN
    note of 1 Oct 09:54, C1).
- **Shuffled labels** (`pack: checks.shuffled_full`, `checks.shuffled_null`; to B2; causal):
  - **The full engine** retrained with participant labels permuted within each training session scores
    20.00 % [13.33, 28.33] on B2 natural walks, against 16.67 % chance.
  - **The feature components alone:**
    - real labels 26.67 %;
    - 20 permutations: mean 18.33 %, maximum 31.67 %;
    - **p = 0.143**: two permutations matched or beat the real labels.
  - **On engine v2 the feature components alone do not separate from shuffled labels on B2.** On v1 the
    feature-only p was 0.048. Say it plainly.
  - **The two families on their own** (`pack: results.component_families`; information; walks folds):
    - CNNs only 30.00 % [12.78, 53.33];
    - features only 22.22 % [15.56, 30.00];
    - all eight 35.56 %;
    - on B2: 31.67, 26.67 and 35.00.
- **AC1, the step-rate check on simulated walks** (`pack: addendum.AC1_step_rate_simulated`;
  identity-blind):
  - **The grid:** 48 simulated walks (step rates 1.5 to 2.2 Hz, both directions, 1.0 to 1.4 m/s, from
    standing) pushed through the engine's own extraction.
  - **Engine v1:** the resolver was within 5 % on only 33 of 48. Fast walks away read 0.73 to 0.91 of the
    true rate:
    - channels with no rhythm voted equally with clear ones;
    - their estimates sat at the 0.8 Hz band-pass edge and were doubled into the step band.
  - **The fix:** only channels whose autocorrelation peak is at least 0.30 vote; if none qualifies, every
    channel votes as before.
  - **Engine v2:** 48 of 48 within 5 % (median 0.993).
  - **On the 180 real natural walks:** the step rate changed by more than 5 % on 96. Its median ratio to
    the energy envelope moved from 0.886 to 0.996 on the 19 walks with a clear envelope.
- **Replay equals live:**
  - B2 through the live app's rig path equals the harness on 299 of 299 decisions, with the ensemble
    equal to 0.0;
  - the worked walks' exported numbers are the app's own records, and match its JSON log to the log's
    rounding (`pack: checks.verification`).
- **Provenance** (`pack: provenance`):
  - one row per fitted part or design choice, saying what it saw;
  - five rows are flagged as chosen with test results in view: the component list, the fusion rule, the
    direction rule, the bands, and the cadence fix (adopted after its measured effect was seen, under
    the bug rule).
- **Uzayr's constraints, one by one:**

  | constraint | evidence | status |
  |---|---|---|
  | one press per walk | `engine.Engine.press`; `tests/test_ide_engine.py::test_one_press_one_decision` | met |
  | no end press, no walk time | the window is fixed at [t0, t0 + 3 s]; the end press is in the pack only as `truth_for_teaching_only` | met |
  | nothing from tracking | the engine reads only the three receivers' CSI and the press (`pipeline/identify/engine.py`) | met |
  | trained on prior sessions only | the manifests' `training_sessions` (`pack: models`); the guard (`tests/test_ide_rigrun.py::test_guard_refuses_deployment_model_for_b2`) | met |
  | only unlabelled same-day adaptation | `engine.Session` uses earlier windows without labels; CAL-none 32.78 shows its size | met |
  | no warm-up | `tests/test_ide_rigrun.py::test_first_walk_decides_without_warmup` | met |
  | pace only as one gait parameter | the Wi-Fi speed enters three of eight components as one column; the engine without pace scores 29.44 | met, but the confound is not excluded (chapter 07) |
  | the identification path is line A | every identification walk is on line A with RX2 beside the TX | met |
  | names | this pack | met |
  | no new data | only the five recorded sessions are used | met |
  | frozen | engine v2 is frozen after the rebuild check (PLAN note of 1 Oct 13:37); the only change since 30 Sept is the cadence bug fix, at Uzayr's decision | met, with that one bug fix |

## 10. Weak spots and next steps

- **Weak spots:**

  | weak spot | figure | status |
  |---|---|---|
  | the lean towards PA1 | 63 of 180 natural walks named PA1 (he has 30) | open; a correction from the training days moved 9 of 659 decisions (A4) and was not adopted |
  | PA2 | 3 of 30 (10.0 %); 0 of 10 on B2 | open |
  | confidence mostly means PA1 | 14 of 22 right answers in the top 30 %; AUROC 0.585 | open |
  | natural pace does not beat press speed | engine minus S0 -2.78 [-26.11, 15.56] | stated plainly |
  | its own Wi-Fi speed is not beaten either | engine minus S_wifi +11.67 [-1.67, 25.56] | new on engine v2; stated plainly |
  | the fast-walk lead is not separable | +10.08 [-13.45, 30.25] over S0 | stated plainly |
  | the feature components on B2 are at the shuffled-label level | p = 0.143 | new on engine v2; stated plainly |
  | the one-press cost on tracking walks | -8.00 [-13.00, -2.33] pooled; Room A -9.17 | information |
  | Room B leave one session out | 23.75 (was 29.17 before the fix) | the bug fix's cost; information |
  | no usable limb Doppler | limb band above the empty room in 53 % of walks; limb features add nothing | physics limit |
  | small samples | 6 people, 180 natural walks; intervals 30 points wide | stated |

- **Fixes and checks (status pills):**
  - FIXED: B-1 (the `dwt_6` pace proxy), B-2 (the maps' log constant), the time-base fault in the app's
    consumer, **the cadence bug (engine v2)**;
  - REJECTED: GS (-2.00 [-4.00, 0.50] on 600 tracking passes);
  - NOT ADOPTED: A1 (gate r 0.697 < 0.70), A2 (0.00), A3 (-3.33), A4 (-0.56);
  - VERIFIED: the rig run (299 of 299, v2), the substitution test, the shuffled-label control (full
    engine).
- **Open decisions, with a recommendation each:**
  1. **Thesis framing.**
     - **What the figures support (my reading):** identification above chance from one press, across
       days and rooms. They do not support a claim that it is better than walking speed: the engine separates
       from neither speed control at natural pace.
     - **Recommendation:** frame the result as "a gait-and-speed identity signal that transfers across
       days from one press", with the pace confound measured and not excluded.
  2. **The render:** re-record it on engine v2 (expected 21 of 60). Recommendation: record it, because
     the v1 render no longer matches the thesis model.
  3. **The two-press reference** (43.33, the audit) was built with the v1 resolver. Recommendation: keep
     it as a frozen reference, labelled as such, rather than rebuilding a superseded design.
  4. **The lean and PA2.** Recommendation: report, do not tune. Any correction would now be chosen on
     the test days.
- **Future work:**
  - more people and days, to narrow the intervals;
  - RX2 placement off line A, for speed on other paths;
  - a longer window or two presses where the use allows it (the one-press cost);
  - limb Doppler needs a higher sample rate or more bandwidth.
- **"Say it plainly in the write-up"** (from `reports/ID_FINAL_2026-09-30.md` section 11 and
  `reports/ID_EXTRAS_2026-09-30.md` section 7, updated to engine v2):
  1. One engine, run live and replayed for every figure: one press, a 3 s window, a decision a median
     0.32 s (this run) to 0.43 s (30 Sept) after the window, depending on the run's compute.
  2. 35.56 % [21.11, 52.78] on natural walks against 16.67 % chance, from models that never saw the day.
  3. At natural pace it is not distinguishable from press speed alone, nor from its own Wi-Fi speed
     alone.
  4. Out of the box (no same-day adaptation) 32.78 %; adaptation adds about 3 points, not separable.
  5. Direction from Wi-Fi alone: 96.9 %. Walking speed from Wi-Fi alone: Pearson 0.82, median error
     0.10 m/s.
  6. "Confident" mostly means PA1.
  7. A step-rate bug was found by simulated walks and fixed whatever its effect; the headline moved by
     -0.56.
  8. On B2 the gait features alone are not distinguishable from shuffled labels (p = 0.143); the
     substitution test shows the decision follows the radio (91.67 %).
- **Graduate attributes against the evidence** (the rubric PDFs are not in the repository, so this lists
  the evidence only):
  - **GA1, problem solving:**
    - the one-press constraint met by a causal engine (chapter 03);
    - the time-base fault found and fixed by the rig run;
    - the cadence bug found by a simulated-walk grid and fixed (AC1);
    - files: `pipeline/identify/engine.py`, `reports/ID_EXTRAS_2026-09-30.md` section 4,
      `pack: addendum.AC1_step_rate_simulated`.
  - **GA4, investigations, experiments and data analysis:**
    - the controls S0 and S_wifi, the substitution test, the shuffled-label null and the conditioning
      ablation;
    - every figure has its interval by participant bootstrap, partitions, and rules written before
      looking (`runs/identify/engine/PLAN.md`);
    - files: `pack: checks`, `pack: results.pace_confound`.
  - **GA5, engineering methods, skills and tools:**
    - the live app, with the replay harness equal to it on 299 of 299;
    - manifests and guards, tests, and committed provenance per fitted part;
    - files: `pipeline/live/identify_engine.py`, `tests/test_ide_rigrun.py`, `pack: provenance`.

## Self-test questions (two per chapter, answers from the pack)

- **00.**
  - Q: Why are the worked walks PA4's and not PA2's, though PA2's confusion with PA1 ties for
    commonest? A: On engine v2 none of PA2's 10 B2 natural walks is right, so no recording of his holds
    both a right and a wrong walk, and the rule falls back to the next cell.
  - Q: What did the app say for the wrong walk? A: PA1 at displayed confidence 0.4405, with PA4 the
    runner-up at 0.3436.
- **01.**
  - Q: Why does RX1 see no torso Doppler on line A? A: It sits opposite the TX on the line, so the two
    rays cancel and F = 0.
  - Q: What torso frequency does a walker at 1.2 m/s produce on RX2? A: 2 x 0.981 x 1.2 / 0.123, about
    19.1 Hz (arithmetic on quoted numbers); 18.75 Hz is measured.
- **02.**
  - Q: Why is PC1 discarded? A: It carries common-mode power changes, not motion.
  - Q: How wide is one map bin? A: 150 / 64 = 2.34 Hz.
- **03.**
  - Q: What does the app know at the decision? A: The radio and the start press only, never the end
    press or the walk's duration.
  - Q: When at the latest is a decision made? A: At t0 + 4 s, when the 1 s cap ends.
- **04.**
  - Q: How many parameters has the 3-link CNN? A: 19,890, checked against the saved weights.
  - Q: Which feature family is largest? A: rhythm (rhy), 219 of 630.
- **05.**
  - Q: Can the displayed confidence change the decision? A: No: softmax(sum / 8) keeps the order of the
    sum.
  - Q: What is chance for top-2? A: 33.33 %.
- **06.**
  - Q: How was replay equal to live checked? A: B2 was streamed through the rig path, and 299 of 299
    decisions equalled the harness.
  - Q: What does the guard refuse? A: Any model trained on the streamed session.
- **07.**
  - Q: Does the engine beat walking speed at natural pace? A: Not separably: -2.78 against press speed,
    +11.67 [-1.67, 25.56] against its own Wi-Fi speed.
  - Q: What is the headline and its interval? A: 35.56 % [21.11, 52.78] against 16.67 % chance.
  - (extra) Q: Why does the same-day figure (AC2) run higher than the headline? A: Each person's test walks
    come from the same recording as their training walks, so it measures person plus recording: 55.00 and
    70.83 against 35.00 and 37.50 cross-day.
- **08.**
  - Q: Why was 36.11 superseded? A: The cadence bug was fixed (engine v2); the rebuild gives 35.56.
  - Q: Which figure was the DC2 pre-registered analysis? A: 26.67 % (S0 40.00).
- **09.**
  - Q: How often does a swapped radio carry the donor's own decision? A: 91.67 % [75.00, 100.00].
  - Q: What does the shuffled-label full engine score? A: 20.00 % [13.33, 28.33] against 16.67 % chance.
  - (extra) Q: How was the cadence bug found? A: By 48 simulated walks with known step rates: engine v1 had
    33 of 48 within 5 %; engine v2 has 48 of 48.
- **10.**
  - Q: What is the biggest single bias? A: 63 of 180 natural walks are named PA1.
  - Q: What does one press cost on the tracking walks? A: -8.00 [-13.00, -2.33] pooled.
