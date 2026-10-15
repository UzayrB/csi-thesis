# Identification: the overnight run (2026-10-02)

**Brief:** `reports/identification/briefs/2026-10-02_overnight.md` (Uzayr, 2 Oct 00:40, verbatim; unattended).
**Rules before results:** `runs/identify/engine/PLAN.md`, the note of 2 Oct 00:51 (7fff5ba).
**Log:** `runs/identify/overnight/log.md` (a clock-read timestamp per step). **Code:** `pipeline/identify/ion_night.py`.
**Records:** `runs/identify/overnight/` (rows, `stack.json`, `final_rule.json`, `part1/`, `part2/`, `part3/`, `seeds/`).

**Development evaluation, all data seen.** Walks-fold figures are the 180 natural (120 slow, 119 fast) identification
walks, each scored by the fold that never saw its day: to B2 trained on A1, A2, A3 and B1; to B1 on A1, A2, A3 and B2.
Calibration is causal (earlier windows of the same layout, unlabelled). Intervals: participant bootstrap, 10,000
resamples. Every row is paired against engine v4. Names are used throughout; tracking's "P5" is PA2.

## Morning summary

1. **Final engine: engine v4** (verified): natural **37.78 % [23.33, 53.33]**, slow 29.17 % [6.67, 54.17], fast 30.25 % [20.34, 42.02]; chance 16.67.
2. **Nothing won:** learned speed in the pace components +0.00, nine CNN seeds -0.56, physics vote -1.11 (-5.56 with temperatures), MiniRocket -1.11.
3. All fail the step rule, so the final rule fails (+0.00 against +3.33) and no v5 was built; no arm passed +8, so no shuffled-order check was needed.
4. Notable: a radio-learned speed tracks the stopwatch better (natural Pearson 0.766 against 0.713) yet identifies worse alone (21.67 % against 31.67 %).
5. **Verification:** replays equal the prediction on 1,019 of 1,019 windows; rig path **299 of 299** (difference 0.0); 13 of 13 identification tests.
6. **Render:** 18 of 60 on B2's natural blocks; the command is in section 9.
7. **Teaching pack:** `reports/identification/teaching/2026-10-02_teaching-pack.json`, with `2026-10-02_teaching-notes.md`, `2026-10-02_teaching-readme.md` and nine `check_png/2026-10-02_*.png` (12 files to upload).
8. Pack checks on v4: substitution 75.00 % [41.67, 100.00] (v2 91.67), shuffled-label engine 16.67 % (chance), no conditioning step separable.
9. Three faults tonight, each caught and corrected (section 11); no wrong number was kept.
10. Plainly: v4 sits at the speed ceiling (a perfect stopwatch alone scores 38.33 %); 50 % needs RX2 kept in place across days, or more people and days (section 10).

## 1. The full table (every row paired against v4)

| row | natural [95 %] | paired against v4: natural [95 %] | slow (vs v4) | fast (vs v4) | to B2 / to B1 (vs v4) | named PA1 | step rule |
|---|---|---|---|---|---|---|---|
| **engine v4** | **37.78 [23.33, 53.33]** | | 29.17 | 30.25 | 30.00 / 41.67 | 56 | |
| Part 1, arm 1-L: the learned speed (1b) as the pace column | 37.78 [23.33, 53.33] | +0.00 [-1.67, +1.67] | 30.00 (+0.83) | 29.41 (-0.84) | 30.00 / 41.67 (+0.00 / +0.00) | 56 | fails |
| Part 4: the CNNs averaged over seeds 0 to 8 | 37.22 [21.11, 55.56] | -0.56 [-6.67, +4.44] | 29.17 (+0.00) | 26.05 (-4.20) | 31.67 / 40.00 (+1.67 / -1.67) | 57 | fails |
| Part 2: the physics component, a ninth equal vote | 36.67 [22.22, 51.67] | -1.11 [-2.78, +1.11] | 29.17 (+0.00) | 30.25 (+0.00) | 30.00 / 40.00 (+0.00 / -1.67) | 55 | fails |
| Part 2: the physics component, with per-component temperatures | 32.22 [20.00, 47.22] | -5.56 [-15.00, +4.44] | 30.83 (+1.67) | 34.45 (+4.20) | 30.00 / 33.33 (+0.00 / -8.33) | 39 | fails |
| Part 3: MiniRocket, a ninth equal vote | 36.67 [22.22, 52.78] | -1.11 [-2.22, +0.00] | 29.17 (+0.00) | 29.41 (-0.84) | 30.00 / 40.00 (+0.00 / -1.67) | 56 | fails |
| control: S0, press speed alone | 38.33 | | 17.50 | 16.81 | | | information |
| control: S_wifi, v4's Wi-Fi speed alone | 31.67 | | 17.50 | 31.09 | | | information |
| control: S_learned, the learned speed alone (Part 1) | 21.67 | | 16.67 | 28.57 | | | information |
| alone: the physics component (Part 2) | B2 33.33, B1 19.17 | | | | | | information |
| alone: MiniRocket (Part 3) | B2 26.67, B1 25.83 | | | | | | information |

Train and test: the walks folds (to B2: A1, A2, A3, B1; to B1: A1, A2, A3, B2); calibration causal; the controls are one-number LDAs trained on the other Room B day's identification walks.

## 2. The learned speed (Part 1), and its Pearson table

**What was built** (PLAN note 2 Oct 00:51): a regressor from the radio to each walk's press speed, trained on each fold's
training sessions only (every walk with presses: identification and tracking walks, all paces), the stopwatch as the
teacher and never an input. A training walk's value comes from a regressor that did not see its session (inner leave
one session out); the test session's from the regressor on all training sessions.

- **1a, gradient boosting** (46 radio inputs: RX2's and RX3's torso contours and centroids read off the walk's own maps,
  their envelope rise and fall, F per link, frames received per link, the walking span, the engine's Wi-Fi speed).
- **1b, a small CNN regressor** on RX2's and RX3's 4 s maps (zero after the detected end) with F joined before the head;
  seeds 0 to 2 averaged (seed 0 on the GPU; seeds 1 and 2 on the CPU, because the GPU held Part 4's queue).
- **The choice** was fixed beforehand as the inner cross-fitted Pearson over all training walks (never a test session):
  1b 0.378 against 1a 0.286, so **1b** was used.

**Identity-blind: Pearson against press speed / median absolute error (m/s)** on each test session's walks.

| test walks | n | 1b (chosen): Pearson / median abs error (m/s) | 1a | Wi-Fi speed (v4) |
|---|---|---|---|---|
| to B2, natural | 60 | 0.828 / 0.070 | 0.734 / 0.080 | 0.633 / 0.075 |
| to B2, slow | 60 | 0.401 / 0.086 | 0.341 / 0.086 | 0.388 / 0.075 |
| to B2, fast | 59 | 0.682 / 0.103 | 0.843 / 0.086 | 0.720 / 0.180 |
| to B1, natural | 120 | 0.749 / 0.075 | 0.780 / 0.083 | 0.753 / 0.071 |
| to B1, slow | 60 | 0.620 / 0.090 | 0.561 / 0.108 | 0.499 / 0.057 |
| to B1, fast | 60 | 0.696 / 0.099 | 0.841 / 0.075 | 0.816 / 0.132 |
| both folds, natural | 180 | 0.766 / 0.073 | 0.763 / 0.082 | 0.713 / 0.073 |
| both folds, slow | 120 | 0.583 / 0.087 | 0.514 / 0.095 | 0.466 / 0.067 |
| both folds, fast | 119 | 0.672 / 0.101 | 0.828 / 0.078 | 0.760 / 0.169 |
| A1 tracking (leave A1 out) | 120 | 0.492 / 0.073 | 0.460 / 0.080 | 0.164 / 0.194 |
| A2 tracking | 120 | 0.500 / 0.069 | 0.429 / 0.073 | 0.219 / 0.259 |
| A3 tracking | 120 | 0.698 / 0.067 | 0.586 / 0.085 | 0.231 / 0.221 |

Inner cross-fitted Pearson over all training walks (the choice): 1b 0.255 (to B2) and 0.501 (to B1), mean 0.378; 1a 0.210 and 0.363, mean 0.286.

**Reading.** On the identification walks the learned speed tracks press speed a little better than the Wi-Fi speed at
natural and slow pace (natural 0.766 against 0.713), worse at fast pace (0.672 against 0.760); 1a is better than 1b
on the identification walks' fast pace (0.828), and the inner criterion preferred 1b because the tracking walks, where
1b is much better than the Wi-Fi speed (Room A 0.49 to 0.70 against 0.16 to 0.23), dominate the training sessions.

**Used in three places:**

| row | natural | slow | fast |
|---|---|---|---|
| S0, press speed alone (one-number LDA) | 38.33 | 17.50 | 16.81 |
| S_wifi, the engine's Wi-Fi speed alone | 31.67 | 17.50 | 31.09 |
| **S_learned, the learned speed alone** | **21.67** | **16.67** | **28.57** |
| arm 1-L (the learned speed as the pace column), paired against v4 | +0.00 [-1.67, +1.67] | +0.83 | -0.84 |

A better-correlated speed did not carry more identity: S_learned is 10 points below S_wifi at natural pace, and in the
engine the learned pace column changes nothing (no fold moved). My reading: a regressor trained across people and paces
shrinks each walk towards the population's speed for its conditions, and its error (median 0.07 m/s) is larger than
the gaps that separate most people: at natural pace on B1, PA2, PA3 and PA6 average 1.32, 1.32 and 1.30 m/s by
the stopwatch, each person's own walks vary by about 0.06 m/s, and the six people's means spread by only 0.12 m/s
(standard deviation; identity-blind arithmetic on the bank's press speeds).

## 3. The physics component (Part 2)

A ninth vote from 26 physics values (the learned speed; RX2's and RX3's contour statistics; the steady speed and the
time to reach it; the step rate where usable, and its missing flag; RX1's shadowing depth, width, asymmetry and its
power at the step rate; F for RX2 and RX3; the walking span). The PLAN note says 27 values: a counting slip in the note
(the list itself was built as written).

- **Strongly regularised logistic regression,** C by leave one session out across the training sessions: C 0.001 for
  to B2 and 0.003 for to B1, the most regularised values allowed, with the inner log loss at chance (1.796 against
  ln 6 = 1.792). The physics vector carries almost no identity across the training sessions.
- **Alone:** 33.33 % on B2's natural walks, 19.17 % on B1's.
- **Fused, paired against v4:** as a ninth equal vote -1.11 [-2.78, +1.11]; with the per-component temperatures
  -5.56 [-15.00, +4.44] (to B1 -8.33). Neither passes the step rule.

## 4. MiniRocket (Part 3)

sktime 1.2.0 installed with `--no-deps` into a scratch directory outside the repository (the engine's scikit-learn
1.7.2 untouched), in under a minute. Inputs: RX1's and RX3's subcarrier mean ("full" band) and PCs 2 to 4 ("dop" band)
at 150 Hz over the 4 s window, each z-scored per walk; RX2's 50th torso contour and 10 to 35 Hz envelope from its map.
10,000 kernels, a ridge classifier, softmax temperature by leave one session out.

- **Alone:** inner (training-session) accuracy 21.7 to 26.1 % across the five folds; 26.67 % on B2's natural walks and
  25.83 % on B1's.
- **Fused as a ninth equal vote, paired against v4:** -1.11 [-2.22, +0.00]. Fails the step rule.

## 5. More CNN seeds (Part 4)

Seeds 3 to 8 of the engine's CNN recipe were trained exactly as v3 trains them (`idz_core.train`, parts cnn, v3's 3 s
bank, the fold model's rows, 6,000 steps), B2 and B1 interleaved. **The anchor:** the same code path retrained to B2's
3-link network at seed 0 bit for bit, and its input statistics too; and seeds 0 to 2 re-scored through the overnight
path reproduce v4's CNN components exactly (difference 0.0). **The budget:** 75 minutes from the anchor (01:03); B1's
seed 8 ended at 02:14, so seed 9 was not trained, and each fold averages **nine** seeds, not ten.

| seed | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | nine averaged | v4 (three) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| natural % (single seed, with v4's features) | 38.33 | 35.56 | 36.67 | 38.89 | 37.78 | 35.00 | 38.33 | 32.22 | 35.00 | 37.22 | 37.78 |

Averaging more seeds does not lift the ensemble: nine seeds give 37.22, -0.56 [-6.67, +4.44] against v4, and fast falls
by 4.20, so the step rule fails. The seed spread (32.22 to 38.89) is noise around the same level.

## 6. The step-by-step stack (Part 5)

The brief's order: v4, then Part 1, then Part 4, then Part 2, then Part 3. Each step is tested against the stack so
far; since nothing was kept, every step was tested against v4 itself.

| step | against | natural gain (rule: >= +2.22) | worst fold (>= -3.4) | worst of slow and fast (>= -2.5) | PA1 rise (<= 5) | kept |
|---|---|---|---|---|---|---|
| 1. Part 1: the learned speed (1-L) | v4 (nothing kept before it) | +0.00 | +0.00 | -0.84 | +0 | no |
| 2. Part 4: seeds 0 to 8 | v4 (nothing kept before it) | -0.56 | -1.67 | -4.20 | +1 | no |
| 3. Part 2: physics, equal sum | v4 (nothing kept before it) | -1.11 | -1.67 | +0.00 | -1 | no |
| 3. Part 2: physics, temperatures | v4 (nothing kept before it) | -5.56 | -8.33 | +1.67 | -17 | no |
| 4. Part 3: MiniRocket | v4 (nothing kept before it) | -1.11 | -1.67 | -0.84 | +0 | no |

**The final stack is engine v4 itself.**

## 7. The final rule's checks

| condition | needed | the final stack (v4) | holds |
|---|---|---|---|
| natural paired gain over v4 | at least +3.33, positive on both folds | +0.00; to B2 +0.00, to B1 +0.00 | no |
| slow and fast | each no more than 2.5 below v4 | +0.00, +0.00 | yes |
| leave one session out, Room A and Room B | no more than 4.45 below v4 | equal to v4 (32.50, 27.92) | yes |
| every seed involved | the stack's seeds | v4's three | yes |
| shuffled order for any gain above +8 | | no gain above +8 | not needed |

**The final rule fails, so v5 is not built; engine v4 stands.**

## 8. The shuffled-order check

Not needed: no arm gained more than +8 (the largest gain was +0.00). The guard against a false win held by
construction: no method used the test day's walks except through the existing causal pools.

## 9. Part 6: engine v4, its verification, the render and the teaching pack

**Engine v4** (built before the overnight parts, at the start of the night; `reports/identification/2026-10-02_lean-in.md`
section 6): the 4.0 s window, the direction from its first 3 s, the radio-only end detector and the Wi-Fi speed on the
walking span. **Verified:** the v4 bank equals the screen's 4.0 s bank on all 1,019 windows at both alphas; the replays
equal the screen's prediction 1,019 of 1,019 (largest difference 4.3e-14); the rig path 299 of 299, ensemble difference
0.0 (`runs/identify/teaching/verify_B2_v4.json`); 13 of 13 identification tests (`IDE_SLOW=1`).

**The full re-score** (`runs/identify/engine/eval/eval_v4.json`, `runs/identify/final_extras/measures/measures_v4.json`):
natural 37.78 [23.33, 53.33] (to B2 30.00, to B1 41.67); away 38.89, towards 36.67; slow 29.17; fast 30.25; without the
pace components 30.56; S0 38.33 (engine minus S0 -0.56 [-25.56, +17.78]); S_wifi 31.67 (+6.11 [-21.67, +31.11]);
S_learned 21.67; no same-day calibration 40.56 (adaptation -2.78 [-8.33, +3.33]); top-2 62.78; households of 2 to 5:
72.33, 58.56, 49.39, 42.78; confidence: 50.00 on the top 30 %, AUROC 0.62; per person: PA5 50.0, PA1 70.0,
PA2 10.0, PA3 30.0, PA4 30.0, PA6 36.7; leave one session out: Room A 32.50 [23.06, 39.72], Room B 27.92
[19.58, 38.75].

**The render:** 18 of 60 (30.00 %) on B2's natural blocks with `loso_B2_v4`. Command:
`OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1 --device mps`.

**The teaching pack** (the 1 October spec, `reports/identification/briefs/2026-10-01_teaching.md`; the selection rule
re-applied unchanged; built with `--final`, so `provisional` is false):

- **Files** (`reports/identification/teaching/`, beside the 1 October ones, nothing overwritten):
  `2026-10-02_teaching-pack.json` (1,389,072 bytes, one file), `2026-10-02_teaching-notes.md` (the notes, chapter by
  chapter), `2026-10-02_teaching-readme.md` (conventions, the selection, the checks, the field guide), and nine check
  plots `check_png/2026-10-02_01` to `_08`. These twelve files are what to upload to the page's chat.
- **The worked walks** (`runs/identify/teaching/selection_v4.json`): the commonest B2 confusion is PA4 named as
  PA1 (7 walks, no tie, no fallback); from his natural recording, the wrong walk is his first pass, named PA1 at
  displayed confidence 0.2973 with its direction also misread (towards; he walked away), and the right walk is pass 2,
  PA4 at 0.5826 (the closest of his correct walks away to the median 0.4838). Both are away from the TX.
- **Verification:** the rig path 299 of 299 on v4; the worked walks' exported numbers equal the app's records, and its
  JSON log to the log's rounding (largest difference 4.6e-4); the engine re-run inside the pack builder equals the
  app's ensemble to 1e-6.
- **The three checks, re-run on v4:**

  | check | engine v4 | engine v2 (1 Oct) |
  |---|---|---|
  | substitution: swapped decision equals the donor's own (host's pool / rebuilt pool) | 75.00 [41.67, 100.00] / 83.33 [50.00, 100.00] | 91.67 / 91.67 |
  | shuffled labels, the full engine, B2 natural | 16.67 [8.33, 26.67] | 20.00 [13.33, 28.33] |
  | the feature components alone against 20 permutations | 23.33 against null mean 16.58, p 0.143 | 26.67 against 18.33, p 0.143 |
  | conditioning ablation, natural, paired | no band-pass 0.00; PC1 kept 0.00; mean instead of PCA -7.22 [-22.22, 5.56]; no log -2.22 [-15.00, 8.33]: none separable | no log -10.56 [-22.78, -2.78], separable |
  | identity-blind: RX2 torso-band energy over the empty room, raw / conditioned | 1.39 / 6.53 times (4 s windows) | 1.45 / 6.37 times |

  Plainly: the decision still follows the radio, but on v4 more decisions move with the calibration pool (since fix L
  the pool holds only the same layout's earlier walks), and no single conditioning step is separately needed for
  accuracy on v4. The addendum's AC1 to AC3 were not re-run and are labelled as engine v2's in the pack.

## 10. Plainly: how close to 50 %, and what stands in the way

Engine v4 is 37.78 %, about 12 points short of 50 %, and nothing tried tonight closed any of that gap; its interval
[23.33, 53.33] reaches 50 only at the top, and with 180 walks from six people even a real 12-point gain would be hard to
separate from zero. What stands in the way is in the data, not in the model. First, the identity that crosses days is
mostly walking speed, and speed is already used to its ceiling: a perfect stopwatch alone scores 38.33 % and the engine
37.78 %, because each person's natural speed moves between the two Room B days by a mean 0.057 m/s, as much as the gaps
between neighbouring people (0.006 to 0.165 m/s on B1), so even a perfect speed separates only a few of the six; a
better radio speed (Part 1) cannot beat that ceiling, and it did not. Second, the gait signal that could add identity
beyond speed lives mostly on RX2, which was re-placed for every person's slot, so what it learns within a day is partly
the placement: RX2's columns give 45.24 % within a day and 15.48 % across days. Third, the other links see little of
the walker on line A (RX1's F is 0 and RX3's 0.5), the limb band clears the empty room in only about half the walks, and
a step rhythm shows in about 30 %, so the physics vector and MiniRocket had little left to find. Fourth, the errors are
systematic: 55 % of a person's wrong walks on a day share one wrong name (0.20 if spread), and 56 of 180 natural walks
are named PA1, which is what a day-level shift in the features produces. My reading: 50 % across days needs either
RX2 kept in one place across sessions, so its same-day signal can travel, or more people and days to learn what in a
walk survives a day; with these recordings the engine sits at the speed ceiling.

## 11. What went wrong tonight

- **A stop-watcher fired at once (01:31).** To end Part 4 on its budget, I wrote a watcher that waited for B1's seed 8;
  it also tested for "QUEUE STOPPED" anywhere in the guard log, and an old line from earlier in the night matched. It
  stopped the seed queue's watchdog while B2's seed 5 trained and started the seed scoring beside it, so two GPU jobs
  overlapped for about 17 s. Found within 20 s: the scoring was stopped before it wrote anything, seed 5 finished under a
  new watchdog loop with the guard's limits, and the remaining seeds ran under the guard. The later watchers read only
  lines written after they start.
- **Two teaching scripts predated fix L** (engine v3's per-layout calibration pools). The substitution test built its
  pool without layouts, so B2's tracking walks were mixed into the identification walks' pool; its first v4 result
  (71.67 and 81.67) is kept as `runs/identify/teaching/substitution_v4_mixedpool_fault.json` and not used. The
  conditioning ablation's AdaBN had the same flaw and was corrected before it ran; the pack's walk section was corrected
  before it ran (its own assertion against the app's ensemble would have refused it).
- **A queued re-run never started (02:38 to 02:41).** The watcher that was to launch the corrected substitution after the
  ablation passed a space-padded line count (macOS `wc -l`) to `tail`, so its check could never match. Noticed when
  the queue went quiet; the watcher was stopped and the substitution launched directly three minutes late.
- **Part 1b's seeds 1 and 2 ran on the CPU,** not the GPU (the GPU held Part 4's queue); seed 0 ran on the GPU. The
  three seeds are averaged as planned.
- **The PLAN note says the physics vector has 27 values;** it has 26, as listed. A counting slip in the note.
- **Part 4 trained seeds 3 to 8,** not 3 to 9, inside its 75-minute budget.

## Files

- Report: `reports/identification/2026-10-02_overnight.md` (this file); the lean-in report
  `reports/identification/2026-10-02_lean-in.md`.
- Rows: `runs/identify/overnight/rows/*.json`; the stack `runs/identify/overnight/stack.json`; the final rule
  `runs/identify/overnight/final_rule.json`; Part 1 `runs/identify/overnight/part1/part1.json`; Part 4's single seeds
  `runs/identify/overnight/part4_single_seeds.json`.
- Teaching: `reports/identification/teaching/2026-10-02_teaching-pack.json`, `2026-10-02_teaching-notes.md`,
  `2026-10-02_teaching-readme.md`, `check_png/2026-10-02_*.png`; checks `runs/identify/teaching/selection_v4.json`,
  `verify_B2_v4.json`, `substitution_v4.json`, `shuffled_full_v4.json`, `shuffled_null_v4.json`,
  `ablation/ablation_v4.json`, `ablation/maps_T4.0.json`.
