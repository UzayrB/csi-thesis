# Identification teaching notes, for the page writer (2026-10-02)

**For:** the claude.ai chat building the identification teaching page. It cannot see the repository.

**This file replaces the notes of 1 October** (`2026-10-01_teaching-notes.md`) for every number and every engine
fact. The page's chapters, the physics and the rig are unchanged; where a fact below is unchanged, it is restated so this
file stands alone.

**How to use this file:**
- **Prose facts:** it gives the facts the page's prose needs, chapter by chapter (the spec's chapters 00 to 10).
- **Sources:** every fact names its source as a repository file and section, or as a pack path (`pack: <path>`).
  Results also state their train and test partition.
- **Numbers:** all of them are in the pack, `2026-10-02_teaching-pack.json`. Where this file and the pack disagree,
  the pack is right and this file is wrong.

**Conventions:**
- **Development evaluation, all data seen.**
- **Engine v4.**
  - Every engine figure here is from engine v4: the one-press engine with a 4.0 s window, an end detector and the Wi-Fi
    speed measured on the walking span (2 Oct 2026, chapter 08). It carries engine v3's two bug fixes and engine v2's.
  - Older figures appear only in the timeline, struck through.
  - **Three checks were not re-run on v4** and are labelled as engine v2's where they appear: the addendum's AC1 (the
    step-rate grid), AC2 (same day) and AC3 (training without the paced walks).
- **Names only, never codes.** Tracking's code order differs: its "P5" is PA2, while identification's old P5 was
  PA4 (the key is in the README).
- **Partitions:**
  - **the walks folds:** each Room B identification walk is scored by the model that never saw its day. "To B2" trains
    on A1, A2, A3 and B1 and tests B2; "to B1" trains on A1, A2, A3 and B2 and tests B1.
  - **leave one session out:** train on four sessions, test the fifth (tracking walks, route known).
- **Intervals:** 95 %, by bootstrap over participants (10,000 resamples, seed 0). The interval runs from `ci_low` to
  `ci_high` in the pack.

## What changed recently (the box on chapter 00)

| date | what | source |
|---|---|---|
| 30 Sept | one model, which is the live app: one press, a 3 s window, 36.11 on natural walks | `reports/identification/2026-09-30_final.md` |
| 1 Oct, 13:09 | **engine v2**, the cadence bug fixed (AC1's simulated walks): 35.56 | `reports/identification/2026-10-01_teaching-pack.md` |
| 1 Oct, evening | **engine v3**, two more bug fixes: fix L (the same-day calibration pools kept per layout) and fix F (a window with no rhythm has no step rate): 32.22 | `reports/identification/2026-10-01_v3-dann.md` |
| 2 Oct, 00:40 | **engine v4**, the lean-in brief: a 4.0 s window, the end detector, the Wi-Fi speed on the walking span: **37.78** | `reports/identification/2026-10-02_lean-in.md` |
| 2 Oct, night | the overnight brief: a speed learned from the radio, a physics vote, MiniRocket and more CNN seeds; nothing passed its step rule, so engine v4 stands | `reports/identification/2026-10-02_overnight.md` |
| 2 Oct, night | this pack, rebuilt on engine v4 with the selection rule re-applied unchanged | this file |

## 00. The two walks

- **Who and which:** two of PA4's walks away from the transmitter (`A_fwd`), in his natural block on B2, the second
  Room B day (`pack: selection`, `walks.*`).
  - The model is `loso_B2_v4`, trained on A1, A2, A3 and B1 only, so it never saw B2.
  - The calibration is causal: the session's earlier walks of the same layout only, unlabelled.
- **The rule chose them before looking.** It was written in the PLAN note of 1 Oct 09:54 (commit aa500c3) and
  re-applied unchanged on engine v4 (`runs/identify/teaching/selection_v4.json`).
  - **The commonest confusion:** PA4 named as PA1, 7 walks, with no tie (the next cells: PA6 as PA5 and
    PA6 as PA1, 4 each).
  - **No fallback was needed** this time (on engine v2 the rule had to fall back from PA2's cell).
  - **The recording:** PA4's natural recording (`participant_PA4_idpath_d2_natural`) holds right and wrong walks
    in the same direction.
  - **The wrong walk** is the first such confusion: his first pass (pass index 0; replay position 150 of 299).
  - **The right walk** is pass index 2 (position 152): his correct walk away whose displayed confidence (0.5826) is
    closest to the median of all correct B2 natural walks (0.4838). It is the closest available, not close: it is a
    confident right walk.
- **What the app said** (`pack: walks.<role>.app`). These are the live app's own logged values from a rig-path replay
  of B2, unrounded in the pack.

  | | wrong walk | right walk |
  |---|---|---|
  | truth | PA4 | PA4 |
  | top identity (displayed confidence) | PA1 (0.2973) | PA4 (0.5826) |
  | runner-up (displayed confidence) | PA2 (0.2362) | PA1 (0.1633) |
  | ensemble probability of the top | 0.801 | 1.000 (to 3 figures) |
  | margin, log units | 1.84 | 10.18 |
  | direction detected | **towards (`A_rev`), wrong** (he walked away) | away (`A_fwd`), right |
  | walking span (end detector) | 3.31 s | the whole 4.0 s (no end found) |
  | Wi-Fi speed | 1.03 m/s | 1.03 m/s |
  | press speed (S0 reference, not a model input) | 1.21 m/s | 1.04 m/s |
  | decision after the press | 4.15 s | 4.18 s |
  | calibration walks seen (same layout) | 90 | 92 |
- **Two teaching points in the wrong walk:** its direction was read wrongly (one of only 4 natural walks in 180), so
  the CNNs were told the wrong direction and the per-path statistics were the other path's; and its Wi-Fi speed (1.03)
  is well below its stopwatch speed (1.21), while the right walk's speed is close (1.03 against 1.04). The two walks
  get the same Wi-Fi speed because the torso median falls in the same 2.34 Hz bin.
- **Replay equals live:** that rig-path run equals the thesis harness on 299 of 299 decisions (`pack: checks.verification`).

## 01. What gait does to Wi-Fi

- **The rig** (`pack: model.settings.node_positions_m`): TX at (2.5, -0.5); RX1 at (2.5, 5.5); RX3 at (5.5, 2.5); RX2
  at (2.0, -0.5), beside the TX, for the identification walks, and at home (-0.5, 2.5) for tracking. The identification
  path is line A, x = 2.5, from y = 0 to 5. Away is `A_fwd` (from the TX) and towards is `A_rev`.
- **Doppler from a moving body:**
  - a reflection's path length L = |p - TX| + |p - RX| changes at dL/dt = (u_TX + u_RX) . v, where u are the unit
    vectors from each node to the body;
  - amplitude-only CSI then fluctuates at f = |dL/dt| / lambda = 2 F v / lambda;
  - F = |(u_TX + u_RX) . v_hat| / 2 is the projected bistatic factor, between 0 and 1;
  - lambda = 0.123 m (channel 11, 2.462 GHz) (`pack: model.settings.lambda_m`; `pipeline/identify/id15_factor_map.py`).
- **F along line A** (`pack: model.settings.F_along_line_a_identification_layout`): RX2 0.981 both directions; RX3
  0.50; RX1 0.
- **Why RX2 beside the TX gives F of about 0.98:** TX and RX2 sit side by side at the start of line A, so both rays to a
  walker on the line point almost exactly along the walk, and u_TX + u_RX is close to 2 v_hat. On RX1, opposite the TX
  on the same line, the two rays are anti-parallel and cancel: F = 0, no Doppler at all. RX3, side-on, gives about 0.5.
- **The torso:** predicted 19.5 Hz at RX2 for the measured speeds; measured 18.75 Hz, both directions (90 walks each),
  within one 2.34 Hz bin (`pack: results.physics.torso_hz_rx2`; identity-blind; B1 and B2).
- **Limbs:** limbs would sit from 35 to 75 Hz; that band is above twice the empty room in 53 % of natural walks (torso
  band: 99 %); limb features add nothing to identity (`pack: results.physics.limb_bands_rx2_over_empty_room`).
- **Rhythm:** a step or stride rhythm is visible in about 30 % of natural walks (`pack:
  results.physics.rhythm_visibility_natural_rx2`). My reading: this is why gait features are weak on one window.

## 02. Signal conditioning

- **The steps, per link, on the 4 s window** (`pack: walks.<role>.links.<link>.conditioning`; code
  `idz_bank.conditioned_map_v2`):
  1. the 103 CSI amplitudes resampled on a 150 Hz grid (600 samples);
  2. a 4 to 70 Hz band-pass;
  3. a per-window PCA with PC1 discarded (it carries common-mode power changes), PCs 2 to 4 kept;
  4. an STFT per kept PC: a 32-sample window, hop 8, a 64-point FFT, so bins of 2.34 Hz and 18.75 frames per second
     (72 frames);
  5. the magnitude summed over the PCs in 28 bins from 4.7 to 68 Hz, then a log with a relative constant (1e-6 times
     the map's median), minus the map's mean. This is the CNN's input.
- **Was it vital? The ablation** (information only; walks folds; causal; `pack: checks.conditioning_ablation`):
  - **The method:** the three CNN components were retrained without one step at a time (on 3 s maps, as the engine's
    own CNNs were) and scored on the 4 s maps, keeping engine v4's feature components.
  - **The result,** on natural walks, paired against the engine's 37.78 %:

    | variant | natural | change, paired | separable from zero? |
    |---|---|---|---|
    | V1, no band-pass | 37.78 | 0.00 [-9.44, 8.33] | no |
    | V2, PC1 kept (PCs 1 to 3) | 37.78 | 0.00 [-8.89, 11.67] | no |
    | V3, the subcarrier mean instead of PCA | 30.56 | -7.22 [-22.22, 5.56] | no |
    | V4, no log and no mean subtraction | 35.56 | -2.22 [-15.00, 8.33] | no |

  - **In plain words:** on engine v4 no single conditioning step's removal is separable from zero. Replacing PCA with
    the subcarrier mean costs about 7 points and dropping the log about 2, neither separable; on engine v2 the log and
    mean subtraction was measurably needed (-10.56 [-22.78, -2.78]). The page must not claim that every step was vital
    to accuracy; the identity-blind check below shows what conditioning does do.
- **Identity-blind:** RX2's 10 to 35 Hz energy over the training day's empty room, on natural walks' 4 s windows
  (`pack: checks.conditioning_energy_identity_blind`): raw, a median 1.39 times the empty room, with 21 % of walks above
  twice it; conditioned (PCs 2 to 4 of the band-passed window), 6.53 times, with 98 % above twice it. Conditioning is
  what lifts the walker's torso band clear of the empty room.

## 03. Segmentation from one press

- **The window:**
  - one space-bar press at the walk's start sets t0;
  - the window is [t0, t0 + 4 s] (engine v4; it was 3 s until 2 Oct);
  - the decision comes once every receiver has a packet past t0 + 4 s on its causal clock, or at t0 + 5 s at the latest;
  - the median packet wait is 0.03 s after the window; the median decision is 0.18 s after it (`pack:
    results.latency_s`).
- **Inside the window, three readings (engine v4):**
  - **the direction** from RX2's 10 to 35 Hz energy slope on the first 3 s, at that 3 s window's own decision time
    (96.9 % right on 419 identification walks; 176 of 180 natural);
  - **the end detector:** at t0 + 3.0, 3.25, 3.5, 3.75 and 4.0 s, RX2's 10 to 35 Hz energy per frame; the reference is
    the median over frames centred in the first 2.5 s; the walk has ended at the first run of 10 frames (0.53 s) below
    alpha times the reference, starting at or after 2.5 s. Alpha is 0.5 for `loso_B2_v4` (0.2 for `loso_B1_v4`), fitted
    on each model's training sessions only (`pack: model.settings.engine_v4`);
  - **the Wi-Fi speed** on the walking span only; the features and maps use the whole window.
- **The 4 s window and the walk:** the decision now comes a median 0.02 s after the walker's own end press on the
  identification walks (it was about 0.9 s before it with 3 s). My reading: a 4 s window covers nearly the whole 5 m
  walk at natural pace, which is why it helped.
- **The causal clock:** each receiver's own microsecond clock is mapped to the host clock by the 5th percentile of the
  offset over the last 20 s of packets; inside the windows it agrees with the whole-file map to 0.51 ms (99th
  percentile); it handled the one receiver reboot (`pack: results.physics.clock_causal_vs_whole_file`).
- **What the app knows, and when:** the radio and the start press, nothing else.
  - **Never:** the end press, the walk's duration, the metre anchors, tracking's output, or any label. The end detector
    reads only the radio.
  - **Calibration:** only earlier walks of the same session and layout, unlabelled.
  - The metre anchors and the end press in the pack are flagged `truth_for_teaching_only_never_seen_by_the_model`.
- **The CNN windows:** 34 frames (1.81 s) at a hop of 4 frames inside the 4 s map, giving 10 windows per walk (`pack:
  model.settings.cnn_window`).

## 04. The features and the networks

- **630 gait features** (`pack: model.features_630_by_family`, `walks.<role>.gait_features`):

  | family | rhy | dop | tplacf | spec | wav | mod | cad |
  |---|---|---|---|---|---|---|---|
  | count | 219 | 141 | 129 | 69 | 54 | 12 | 6 |

  - All are shapes or ratios. The resolved step rate (cadence) scales several families; engine v2 fixed how it is
    resolved, and engine v3 leaves it empty when no channel shows a rhythm (fix F).
  - **The worked walks:** the wrong walk's resolved step rate is 1.33 Hz and the right walk's 1.71 Hz; no clear rhythm was visible in either
    walk's energy envelope (`pack: walks.<role>.gait_features.resolved_cadence_hz`, `envelope_cadence_hz`).
- **The CNNs** (`pack: model.cnn_3link`, `model.cnn_1link`, `model.saved_state_dict_totals`): the 3-link CNN-v2 has
  19,890 parameters and the 1-link one 19,602, checked against the saved weights. The weights are those of 30 Sept,
  trained on 3 s maps; engine v4 applies them to the 4 s maps (10 windows instead of 5) and averages the windows.
- **The eight components** (`pack: model.components`): three random forests (300 trees: one standardised per path, two
  by the session, one of those with the Wi-Fi speed added); extra trees with the Wi-Fi speed; a shrinkage LDA with the
  Wi-Fi speed; the 3-link CNN, plain and with AdaBN; the per-link CNNs with AdaBN, summed.
- **Training** (`pack: model.training`): `loso_B2_v4` has 720 passes, 120 per person, from A1, A2, A3 and B1;
  `deploy_all5_v4` has all 1,019.

## 05. From evidence to an identity

- **The rule:** sum the eight components' six log-probabilities, normalise, and take the argmax; the displayed
  confidence is softmax(sum / 8), the geometric mean, which never changes the decision; the runner-up is second in the
  same order.
- **Chance:** 16.67 % for six people; top-2 33.33 %; a household of g people 1/g (`pack: model.chance_pct`).
- **The two walks** (`pack: walks.<role>.evidence`):
  - **the wrong walk:** the LDA is 0.97 sure of PA1; the two 3-link CNN components lean PA2 (0.46 and 0.48), having
    been told the wrong direction; the per-link CNNs favour PA4 (0.83); the four forests spread thinly (0.15 to 0.22).
    The sum names PA1 by 1.84 log units over PA2.
  - **the right walk:** the three CNN components (0.77, 0.53 and 0.91) and the LDA (0.86) all name PA4, while the
    forests spread thinly; the sum names him by 10.18 log units over PA1.
  - The CNN scores evolve window by window (`evidence.cnn_evolution`, 10 windows). The feature components decide once,
    on the whole window.

## 06. The live app

- **Inputs:** radio from three receivers and one start press.
- **The screen:** the direction; the top identity and runner-up, with the displayed confidence against chance; the
  Wi-Fi speed and the latency; the model; "adapting to this room: n walks seen"; in recorded streams, the truth in
  green or red and a running score.
- **Keys:** SPACE (the press), `n` (new walker) and `q`.
- **Latency:** a median 0.18 s after the window on this run (90th percentile 0.20 s); the compute part is measured and
  varies from run to run (`pack: results.latency_s`).
- **The rig run:** recorded B2, streamed through the real rig interface, equals the harness on 299 of 299 decisions on
  engine v4, ensemble difference 0.0 (`pack: checks.verification`); the identification tests pass on v4 (13 of 13,
  including the full B2 stream, speed 1 against speed max, a late start and the real serial parser); a guard refuses any
  model trained on the streamed day; no warm-up: the first walk is decided on training statistics.
- **The render** (recorded B2's natural blocks as if live) will end at **18 of 60 (30.00 %)** on engine v4. Command:
  `OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1 --device mps`.

## 07. How good it is

- **The headline** (walks folds, causal; `pack: results.headline.natural_both`): **37.78 % [23.33, 53.33]** on the 180
  natural identification walks, against 16.67 % chance; to B2 30.00 %, to B1 41.67 %; away 38.89, towards 36.67, slow
  29.17, fast 30.25.
- **Confusion** (`pack: results.confusion_pooled`): 56 of the 180 natural walks are named PA1 (he has 30). Per
  person: PA5 50.0, PA1 70.0, PA2 10.0, PA3 30.0, PA4 30.0, PA6 36.7.
- **Leave one session out** (tracking walks, known route; `pack: results.loso_tracking`): Room A 32.50 % [23.06,
  39.72] and Room B 27.92 % [19.58, 38.75]; per session A1 30.83, A2 35.83, A3 30.83, B1 24.17, B2 31.67.
- **The pace confound, measured** (`pack: results.pace_confound`; walks folds):
  - **press speed alone (S0):** 38.33 % on natural walks. The engine minus S0 is -0.56 [-25.56, 17.78]: the engine does
    not beat a stopwatch it never has;
  - **its own Wi-Fi speed alone (S_wifi):** 31.67 %. The engine minus S_wifi is +6.11 [-21.67, 31.11], not separable;
  - **the engine without its pace components:** 30.56 %;
  - **fast walks:** the engine 30.25 against S0 16.81, +13.45 [-6.67, 29.41], not separable; slow +11.67 [-5.00,
    30.00].
  - **A speed learned from the radio** (the overnight brief, information): it tracks the stopwatch better than the Wi-Fi
    speed at natural pace (Pearson 0.77 against 0.71) yet identifies worse alone (21.67 %), and in the engine it
    changed nothing (`reports/identification/2026-10-02_overnight.md`).
  - **AC3, training without the slow and fast walks** (engine v2; information): natural -1.11 [-7.78, 7.78], slow
    **-5.83 [-10.83, -1.67]**, fast -3.36 [-13.33, 6.72] (`pack: addendum.AC3_training_without_slow_and_fast_walks`).
- **No same-day adaptation** (`pack: results.no_same_day_adaptation`): **40.56 %** out of the box, above the engine:
  adapting costs -2.78 [-8.33, 3.33], not separable. On the tracking walks adapting adds +1.67 (Room A) and +4.58
  (Room B), neither separable.
- **Deployment measures** (`pack: results.deployment`):

  | measure | engine v4 | chance |
  |---|---|---|
  | top-2 | 62.78 | 33.33 |
  | round trip (natural) | 45.56 | 16.67 |
  | 3 walks | 48.15 | 16.67 |
  | 5 walks | 55.56 | 16.67 |
  | household of 2 | 72.33 | 50.00 |
  | household of 3 | 58.56 | 33.33 |
  | household of 4 | 49.39 | 25.00 |
  | household of 5 | 42.78 | 20.00 |

- **Confidence against coverage** (`pack: results.confidence_coverage`): 41.48 % on the 75 % of walks it is most sure
  of, 46.67 % on the top half, 50.00 % on the top 30 %, 55.56 % on the top 20 %; AUROC 0.62; "confident" mostly means
  PA1: 14 of the 27 right answers in the top 30 % are his.
- **The cost of one press** (information; `pack: results.one_press_cost`): identification walks -2.22 [-10.56, 6.67];
  tracking passes -5.00 [-11.33, 1.17] pooled, Room A -6.94 [-12.78, -0.83], Room B -2.08.
- **The window** (information; the lean-in screen, all data seen): 3.0 s 32.22, 3.5 s 31.67, 3.75 s 36.11, **4.0 s
  37.78**, 4.25 s 36.67, 4.5 s 35.56, 5.0 s 34.44, 6.0 s 34.44 (`reports/identification/2026-10-02_lean-in.md`
  section 1).
- **The same-day comparison (AC2, engine v2, "same day, confounded by recording"):** 55.00 % on B1 and 70.83 % on B2,
  against 35.00 and 37.50 cross-day on the same walks (`pack: addendum.AC2_same_day_confounded_by_recording`). Each
  person's walks come from their own recording slot, with RX2 re-placed for each slot, so the same-day figure measures
  recognising the person plus their recording. Link by link (the lean-in diagnostics, engine v3): RX2's columns give
  45.24 % same day against 15.48 % across days.

## 08. What changed and when

- **The timeline:** `pack: timeline` holds every headline since 12 September, with its value, partition, calibration,
  status and why it was superseded.
- **The main line:** 15.83 (Room A nested, 23 Sept); 26.67 (DC2 pre-registered, 28 Sept); 39.72 and 30.00 (the
  development ensemble, 29 Sept); 46.67 (identification walks, 29 Sept); 43.33 (after bug B-1); 36.11 (the one-press
  engine, 30 Sept); 35.56 (engine v2, 1 Oct); 32.22 (engine v3, 1 Oct evening); **37.78 (engine v4, 2 Oct, current).**
- **Why each was superseded:** v2 fixed the cadence bug; v3 fixed two more bugs, fix L and fix F, adopted whatever their effect (35.56 to 32.22); v4 lengthened
  the window to 4.0 s after a screen of eight windows on all the data, so its +5.56 [1.67,
  10.56] over v3 was chosen with the test results in view (flagged in `pack: provenance`).
- **What the overnight brief tried and did not adopt:** a speed learned from the radio (+0.00 in the pace components; alone 21.67 % against S_wifi's 31.67), the CNNs averaged over nine seeds (-0.56), a physics vote (-1.11; -5.56 with temperatures) and MiniRocket (-1.11). None passed the step rule (`reports/identification/2026-10-02_overnight.md`).

## 09. How we know it is right

- **The substitution test** (`pack: checks.substitution`; B2 natural walks; `loso_B2_v4`; causal):
  - **The donor:** each host walk's slot gets the next natural walk by a different person, in the same direction.
  - **The result:** the decision follows the radio: **75.00 % [41.67, 100.00]** of swapped decisions equal the donor's
    own decision in its own slot with the host's pool (variant A), and 83.33 % [50.00, 100.00] with the pool rebuilt as
    if the donor had walked that slot (variant B); accuracy against the donor 33.33 %, against the host 8.33 % (below
    chance). Only 5 of 60 swaps name the host, none because the donor's own walk was named as the host.
  - **Against engine v2** the follow rate fell from 91.67 %: on v4 more decisions move with the calibration pool, which
    since fix L holds only the same layout's earlier walks (the identification walks of earlier people's slots). My
    reading: the pool matters more than it did, and CAL-none (chapter 07) says it does not help on these walks.
  - **The worked walks:** both, given PA5's radio, become PA5 (`pack: walks.<role>.substitution`).
  - **The method:** the swapped window is the donor's own engine window, classified with the host's calibration pool
    (variant A) or a pool rebuilt as if the donor had walked that slot (variant B).
- **Shuffled labels** (`pack: checks.shuffled_full`, `checks.shuffled_null`; to B2; causal):
  - **The full engine** retrained with participant labels permuted within each training session: 16.67 % [8.33, 26.67] on B2 natural walks, exactly chance (16.67 %).
  - **The feature components alone:** real labels 23.33 %; 20 permutations: mean 16.58 %, maximum 23.33 %; **p =
    0.143**. On engine v4, as on v2, the feature components alone do not separate from shuffled labels on B2. Say it
    plainly.
  - **The two families on their own** (`pack: results.component_families`; information): CNNs only 30.00 % [13.89, 52.78]; features only 27.78 % [17.78, 45.00]; all eight 37.78 %; on B2: 31.67, 23.33 and 30.00. Neither family alone reaches the fusion.
- **AC1, the step-rate check on simulated walks** (engine v2's 3 s window; identity-blind; `pack:
  addendum.AC1_step_rate_simulated`): 48 simulated walks; engine v1 had 33 of 48 within 5 %, engine v2 48 of 48. Engine
  v3's fix F changes only windows with no rhythm-bearing channel, which the simulated walks do not have.
- **Replay equals live:** B2 through the live app's rig path equals the harness on 299 of 299 decisions, ensemble
  difference 0.0; the worked walks' exported numbers are the app's own records (`pack: checks.verification`).
- **Provenance** (`pack: provenance`): one row per fitted part or design choice, saying what it saw. Flagged as chosen
  with test results in view: the component list, the fusion rule, the direction rule, the bands, the cadence fix, fix L
  and fix F (bug fixes adopted whatever their effect, after their effect was seen), and **the 4.0 s window**.
- **Uzayr's constraints, one by one:**

  | constraint | evidence | status |
  |---|---|---|
  | one press per walk | `engine.Engine.press`; `tests/test_ide_engine.py::test_one_press_one_decision` | met |
  | no end press, no walk time | the window is fixed at [t0, t0 + 4 s]; the end detector reads only the radio; the end press is in the pack only as `truth_for_teaching_only` | met |
  | nothing from tracking | the engine reads only the three receivers' CSI and the press | met |
  | trained on prior sessions only | the manifests' `training_sessions` (`pack: models`); the guard test | met |
  | only unlabelled same-day adaptation | `engine.Session` uses earlier windows of the same layout without labels; CAL-none 40.56 shows it does not help on these walks | met |
  | no warm-up | `tests/test_ide_rigrun.py::test_first_walk_decides_without_warmup` | met |
  | pace only as one gait parameter | the Wi-Fi speed enters three of eight components as one column; the engine without pace scores 30.56 | met, but the confound is not excluded (chapter 07) |
  | the identification path is line A | every identification walk is on line A with RX2 beside the TX | met |
  | names | this pack | met |
  | no new data | only the five recorded sessions are used | met |
  | one model, the live app | engine v4 is the app's model; replay equals live 299 of 299 | met |

## 10. Weak spots and next steps

- **Weak spots:**

  | weak spot | figure | status |
  |---|---|---|
  | the lean towards PA1 | 56 of 180 natural walks named PA1 (he has 30) | open |
  | PA2 | 3 of 30 (10.0 %) | open |
  | confidence mostly means PA1 | 14 of 27 right answers in the top 30 %; AUROC 0.62 | open |
  | natural pace does not beat press speed | engine minus S0 -0.56 [-25.56, 17.78] | stated plainly |
  | nor its own Wi-Fi speed, separably | engine minus S_wifi +6.11 [-21.67, 31.11] | stated plainly |
  | the feature components on B2 are at the shuffled-label level | p = 0.143 | stated plainly |
  | same-day adaptation does not help on the identification walks | -2.78 [-8.33, 3.33] | new on v4; stated plainly |
  | RX2's identity does not cross days | 45.24 same day against 15.48 across days (placement confound) | the main data limit |
  | the 4.0 s window was chosen with all data seen | +5.56 [1.67, 10.56] over 3.0 s, on a plateau | flagged |
  | the one-press cost on tracking walks | -5.00 [-11.33, 1.17] pooled; Room A -6.94 | information |
  | no usable limb Doppler | limb band above the empty room in 53 % of walks | physics limit |
  | small samples | 6 people, 180 natural walks; intervals 30 points wide | stated |

- **Fixes and checks (status pills):**
  - FIXED: B-1, B-2, the time-base fault in the app's consumer, the cadence bug (v2), fix L and fix F (v3);
  - ADOPTED: the 4.0 s window and the end detector (v4);
  - REJECTED: GS; NOT ADOPTED: A1 to A4, the lever screen, DANN, the window and gait levers, the lean-in levers,
    and the overnight levers (the learned speed, nine seeds, the physics vote, MiniRocket);
  - VERIFIED: the rig run (299 of 299, v4), the substitution test, the shuffled-label control.
- **Open decisions, with a recommendation each:**
  1. **Thesis framing.** What the figures support (my reading): identification above chance from one press, across days
     and rooms; not a claim that it beats walking speed. Recommendation: "a gait-and-speed identity signal that transfers
     across days from one press", with the pace confound measured and not excluded, and the 4.0 s window flagged as
     chosen on all the data.
  2. **The render:** re-record it on engine v4 (expected 18 of 60). Recommendation: record it, because the earlier
     renders no longer match the thesis model.
  3. **The two-press reference** (43.33, the audit): keep it frozen and labelled.
  4. **The lean and PA2.** Recommendation: report, do not tune.
- **Future work:** more people and days, to narrow the intervals; RX2 kept in one place across days (its placement
  carries the same-day advantage); RX2 placement off line A, for speed on other paths; limb Doppler needs a higher
  sample rate or more bandwidth.
- **"Say it plainly in the write-up":**
  1. One engine, run live and replayed for every figure: one press, a 4 s window, a decision a median 0.18 s after the
     window, about when the walker reaches the end.
  2. 37.78 % [23.33, 53.33] on natural walks against 16.67 % chance, from models that never saw the day.
  3. At natural pace it is not distinguishable from press speed alone, nor from its own Wi-Fi speed alone.
  4. Out of the box (no same-day adaptation) 40.56 %: adaptation does not help on these walks.
  5. Direction from Wi-Fi alone: 96.9 %. Walking speed from Wi-Fi alone: Pearson 0.71 on natural walks; a speed learned
     from the radio reaches 0.77 and still adds no identity.
  6. "Confident" mostly means PA1.
  7. Three bugs were found by checks and fixed whatever their effect; the window was chosen on all the data (flagged).
  8. On B2 the gait features alone are not distinguishable from shuffled labels (p = 0.143); the substitution test shows
     the decision follows the radio (75.00 % [41.67, 100.00] of swaps (83.33 % with the pool rebuilt)).
- **Graduate attributes against the evidence** (the rubric PDFs are not in the repository, so this lists the evidence
  only):
  - **GA1, problem solving:** the one-press constraint met by a causal engine with a radio-only end detector (chapter
    03); the time-base fault, the cadence bug and fixes L and F found by checks; files `pipeline/identify/engine.py`,
    `reports/identification/2026-10-01_v3-dann.md`, `pack: addendum.AC1_step_rate_simulated`.
  - **GA4, investigations, experiments and data analysis:** the controls S0, S_wifi and S_learned, the substitution
    test, the shuffled-label null, the conditioning ablation; every figure with its interval by participant bootstrap,
    partitions, and rules written before looking (`runs/identify/engine/PLAN.md`); files `pack: checks`, `pack:
    results.pace_confound`.
  - **GA5, engineering methods, skills and tools:** the live app, with the replay harness equal to it on 299 of 299;
    manifests and guards, tests, a memory watchdog for the GPU jobs, and committed provenance per fitted part; files
    `pipeline/live/identify_engine.py`, `tests/test_ide_rigrun.py`, `pack: provenance`.

## Self-test questions (two per chapter, answers from the pack)

- **00.**
  - Q: Which confusion chose the worked walks? A: PA4 named as PA1, the commonest cell on B2's natural walks (7).
  - Q: What did the app get wrong on the wrong walk besides the name? A: The direction: it read towards; he walked away.
- **01.**
  - Q: Why does RX1 see no torso Doppler on line A? A: It sits opposite the TX on the line, so the two rays cancel and
    F = 0.
  - Q: What torso frequency does a walker at 1.2 m/s produce on RX2? A: 2 x 0.981 x 1.2 / 0.123, about 19.1 Hz
    (arithmetic on quoted numbers); 18.75 Hz is measured.
- **02.**
  - Q: Why is PC1 discarded? A: It carries common-mode power changes, not motion.
  - Q: How many frames does a 4 s map have? A: 72, at 18.75 frames per second.
- **03.**
  - Q: What ends the walking span? A: RX2's torso-band energy falling below alpha times its early level for 10 frames,
    read from the radio alone.
  - Q: When at the latest is a decision made? A: At t0 + 5 s, when the 1 s cap ends.
- **04.**
  - Q: How many parameters has the 3-link CNN? A: 19,890, checked against the saved weights.
  - Q: How many CNN windows does one walk give? A: 10 (34 frames at a hop of 4 in 72 frames).
- **05.**
  - Q: Can the displayed confidence change the decision? A: No: softmax(sum / 8) keeps the order of the sum.
  - Q: What is chance for top-2? A: 33.33 %.
- **06.**
  - Q: How was replay equal to live checked? A: B2 was streamed through the rig path, and 299 of 299 decisions equalled
    the harness.
  - Q: What will the render show? A: 18 of 60 right on B2's natural blocks.
- **07.**
  - Q: Does the engine beat walking speed at natural pace? A: No: -0.56 against press speed, +6.11 [-21.67, 31.11]
    against its own Wi-Fi speed.
  - Q: What is the headline and its interval? A: 37.78 % [23.33, 53.33] against 16.67 % chance.
- **08.**
  - Q: Why is the window 4 s? A: A screen of eight windows put 4.0 s on a plateau, +5.56 over 3 s; it was chosen with
    all the data seen.
  - Q: Which figure was the DC2 pre-registered analysis? A: 26.67 % (S0 40.00).
- **09.**
  - Q: How often does a swapped radio carry the donor's own decision? A: 75.00 % [41.67, 100.00] of swaps (83.33 % with the pool rebuilt).
  - Q: Do the feature components alone beat shuffled labels on B2? A: No: 23.33 % against a null maximum of 23.33 %, p
    = 0.143.
- **10.**
  - Q: What is the biggest single bias? A: 56 of 180 natural walks are named PA1.
  - Q: Why does RX2 not carry identity across days? A: It was re-placed for every person's slot, so what it learns on a
    day is partly the placement: 45.24 % same day against 15.48 % across days.
