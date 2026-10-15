# Identification on the identification walks (2026-09-29 18:56 SAST)

**Development evaluation, all data seen.** This is not a pre-registered test.
- **Sources:**
  - the brief is `reports/BRIEF_ID_WALKS_2026-09-29.md` (verbatim);
  - the plan, with every definition and rule, was locked before any training in 8c17b4f
    (`runs/identify/idwalks/PLAN.md`);
  - the step-by-step log is `reports/DEVLOG_ID_2026-09-28.md`.
- **The model** is the final identification ensemble of `reports/ID_DEV_FINAL_2026-09-29.md`,
  unchanged except in the one EXPLORATORY arm (section 6).
- **The scoring set** is Room B's identification captures only. No tracking pass is scored.
- **Participants** are "participant P1" to "participant P6".
- **Statistics:**
  - chance is 16.67 % unless stated;
  - intervals are 95 % by bootstrap over participants (10,000 resamples);
  - differences are paired on the same passes.
- **Folds:** "to B2" trains without B2 and tests on it, the deployment-realistic fold. "To B1" tests on
  B1. The headline pools both.

**Anchor.** The retrained Room A plus B1 model reproduced the dev batch's saved outputs exactly (under
the earlier-recordings calibration, on the B2 captures). All eight components and all 179 decisions are
identical (`runs/identify/idwalks/anchor_TR-AB_toB2_causal.json`).

## 1. The count table

Day 1 is B1 and day 2 is B2. Away is `A_fwd`: from (2.5, 0) to (2.5, 5), with the TX at (2.5, -0.5);
this holds on all 210 passes. Towards is `A_rev`, from (2.5, 5) to (2.5, 0); this holds on all 209.

| day | participant | direction | natural | slow | fast |
|---|---|---|---|---|---|
| 1 | P1 to P6, each | away | 10 | 5 | 5 |
| 1 | P1 to P6, each | towards | 10 | 5 | 5 |
| 2 | P1 to P6, each | away | 5 | 5 | 5 |
| 2 | P1 to P4, P6, each | towards | 5 | 5 | 5 |
| 2 | P5 | towards | 5 | 5 | **4** |

- **Plan check:** all 48 cells match the capture plan, 419 passes in total.
- **Relabel:** participant P5's day 2 fast away pass 9 closes on the real 5 m press (1.35 m/s). Its
  towards pass 10 is excluded, as addendum E set out.
- **Round trips:** there are 209 (90 at natural pace). The only unpaired pass is P5's pass 9.
- **Full table:** `runs/identify/idwalks/counts.md`.

## 2. Stage A: which training data

Natural-pace walks, both directions, pooled over both folds (n 180: 60 on B2, 120 on B1).

| training set | CAL-others | CAL-causal | CAL-none | to B2 / to B1 (CAL-others) |
|---|---|---|---|---|
| **TR-AB: Room A + the other Room B day (headline)** | **46.67 [29.44, 66.11]** | 44.44 [25.56, 65.00] | 42.22 [19.44, 66.67] | 41.67 / 49.17 |
| TR-B+: the other Room B day, identification + tracking walks | 33.89 [15.56, 55.56] | 32.78 [15.56, 53.89] | 31.11 [11.67, 53.33] | 33.33 / 34.17 |
| TR-B: the other Room B day's identification walks only | 28.33 [12.22, 47.78] | 30.00 [11.11, 53.33] | 26.67 [12.22, 43.89] | 30.00 / 27.50 |

**Controls beside it** (CAL-others; S0 is the same for every set because it trains on the other day's
identification walks):

| | natural | away | towards | slow | fast |
|---|---|---|---|---|---|
| **ensemble, TR-AB** | **46.67** | 41.11 | 52.22 | 35.00 | 36.97 |
| ensemble without its 3 pace components, TR-AB | 40.56 | 36.67 | 44.44 | 25.00 | 28.57 |
| ensemble, TR-B+ | 33.89 | 27.78 | 40.00 | 35.00 | 29.41 |
| ensemble, TR-B | 28.33 | 26.67 | 30.00 | 30.00 | 38.66 |
| S0, pace from the presses alone | 38.33 [20.00, 61.11] | 37.78 | 38.89 | 17.50 | 16.81 |

**The rule (PLAN section 6) picks TR-AB.** Room A clearly helps:

| paired difference, natural, pooled | |
|---|---|
| TR-AB minus TR-B | **+18.33 [8.33, 27.78]** |
| TR-AB minus TR-B+ | **+12.78 [8.89, 16.67]** |
| TR-B+ minus TR-B | +5.56 [-5.56, 16.67] |

**Against pace** (TR-AB, paired):

| ensemble minus S0 | |
|---|---|
| natural | +8.33 [-14.44, 27.22] |
| slow | +17.50 [-3.33, 39.17] |
| fast | **+20.17 [4.24, 32.77]** |

- **Natural pace:** the model is not distinguishable from pace alone. The ensemble without its pace
  components is 6.11 points below it [-7.78, 23.33].
- **When the walker changes pace,** S0 falls to chance and the model holds at 35 to 37.

**Per participant** (TR-AB, CAL-others, natural): P1 63.3, P2 86.7, P3 20.0, P4 33.3, P5 50.0, P6 26.7.
Confusion (rows are the true participant, columns the prediction, P1 to P6):

| | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| P1 | 19 | 3 | 1 | 2 | 2 | 3 |
| P2 | 0 | 26 | 0 | 1 | 3 | 0 |
| P3 | 0 | 19 | 6 | 3 | 1 | 1 |
| P4 | 10 | 1 | 6 | 10 | 0 | 3 |
| P5 | 4 | 10 | 1 | 0 | 15 | 0 |
| P6 | 6 | 0 | 2 | 13 | 1 | 8 |

- P3 is mostly taken for P2.
- P6 is taken for P4 about as often as for themself (13 against 8).

## 3. The calibration check (slot structure)

CAL-causal minus CAL-others, natural, pooled, paired:

| training set | CAL-causal minus CAL-others | CAL-none minus CAL-others |
|---|---|---|
| **TR-AB (headline)** | **-2.22 [-6.11, 1.67]** | -4.44 [-10.56, 2.78] |
| TR-B+ | -1.11 [-2.78, 1.11] | -2.78 [-10.00, 3.33] |
| TR-B | +1.67 [-6.11, 8.89] | -1.67 [-9.44, 5.56] |

- **Within 5 points in every set.** The dev batch's figure did not depend on the slot structure.
- **Calibrating from others works:** calibrating on the other five people's walks does as well as on
  the day's earlier recordings, and slightly better.
- **Calibration helps only a little:** no calibration at all loses 2 to 4 points.

## 4. Direction

**Pooled-direction models, paired by round trip** (natural pairs, CAL-others):

| model | fold | away | towards | away minus towards | pairs |
|---|---|---|---|---|---|
| TR-AB (headline) | to B2 | 33.33 | 50.00 | -16.67 [-40.00, 3.33] | 30 |
| | to B1 | 45.00 | 53.33 | -8.33 [-23.33, 6.67] | 60 |
| | **pooled** | **41.11** | **52.22** | **-11.11 [-23.33, 1.11]** | **90** |
| TR-B | pooled | 26.67 | 30.00 | -3.33 [-16.67, 8.89] | 90 |

- **The rule's verdict: no detectable difference at this sample size.**
  - Towards is ahead by 11 points on 90 pairs, but the interval reaches +1.11.
- **Per participant, TR-AB** (away / towards):

  | P1 | P2 | P3 | P4 | P5 | P6 |
  |---|---|---|---|---|---|
  | 46.7 / 80.0 | 73.3 / 100.0 | 26.7 / 13.3 | 26.7 / 40.0 | 46.7 / 53.3 | 26.7 / 26.7 |

  - Four people are better walking towards, one is better walking away, and one is equal.

**Direction-specific training** (natural walks, CAL-others, pooled over folds):

| trained on | tested on the same direction (one-way corridor) | tested on the other direction |
|---|---|---|
| TR-AB, away only | 42.22 [26.64, 57.78] | 45.56 [31.11, 64.44] |
| TR-AB, towards only | 48.89 [27.78, 71.11] | 43.33 [28.89, 55.56] |
| TR-B, away only | 18.89 [8.89, 28.89] | 30.00 [15.56, 48.89] |
| TR-B, towards only | 30.00 [11.11, 51.11] | 30.00 [18.89, 45.56] |

- **Identity carries across directions:** a model trained one way identifies the other way about as
  well.
- **Restricting to one direction buys nothing:** the one-way figures are no better than the
  pooled-direction model's (41.11 and 52.22).

**Physics beside it** (RX2, natural walks, identity-blind):

| | away (`A_fwd`) | towards (`A_rev`) |
|---|---|---|
| torso frequency, median | 18.75 Hz | 18.75 Hz |
| measured over 2 F v / lambda | 0.94 (Spearman 0.74) | 1.00 (Spearman 0.74) |
| 10 to 35 Hz energy by thirds of the walk (relative) | **1.79**, 0.68, 0.46 | 0.47, 0.80, **1.74** |
| 35 to 75 Hz over the empty room, median (fraction above 2) | 2.92 (0.64) | 1.60 (0.42) |

- **The torso frequency does not depend on direction,** as amplitude-only CSI requires.
- **The strongest signal is always the part of the walk nearest the TX and RX2:**
  - walking away, that is the first third, where the walker speeds up from standing;
  - walking towards, it is the last third, the steady walk arriving.
- **The towards advantage is therefore consistent with position:** towards walks put steady strides
  where the signal is strongest.
- **The data cannot test** the other explanation (which side of the body faces the link).
- **Neither explanation is established,** since the accuracy difference itself is not significant.

## 5. Deployment measures

Natural walks, CAL-others, pooled over folds, from the saved log-probabilities.

| measure | TR-AB (headline) | TR-B | chance |
|---|---|---|---|
| single walk, top-1 | 46.67 [29.44, 66.11] | 28.33 [12.22, 47.78] | 16.67 |
| single walk, top-2 | **69.44 [53.33, 86.11]** | 57.78 [40.00, 78.33] | 33.33 |
| round trip, away + towards (90 pairs) | 50.00 [30.00, 73.33] | 26.67 [11.11, 45.56] | 16.67 |
| round trip, every pace (209 pairs) | 44.98 [34.45, 55.71] | 34.45 [25.84, 43.06] | 16.67 |
| 3 consecutive walks (54 groups) | **61.11 [40.74, 81.48]** | 31.48 [7.41, 57.41] | 16.67 |
| 5 consecutive walks (36 groups) | 52.78 [25.00, 80.56] | 36.11 [8.33, 66.67] | 16.67 |
| group of 2 people | **78.44 [69.78, 87.67]** | 67.89 [57.00, 80.67] | 50.00 |
| group of 3 | 65.72 [52.22, 80.22] | 51.56 [37.11, 68.83] | 33.33 |
| group of 4 | 57.22 [41.61, 74.78] | 41.44 [25.50, 60.56] | 25.00 |
| group of 5 | 51.22 [34.44, 69.78] | 34.22 [17.78, 53.33] | 20.00 |
| group of 6 | 46.67 [29.44, 66.11] | 28.33 [12.22, 47.78] | 16.67 |

- **Best against chance:**
  - a household of two, 78.44 against 50;
  - three walks combined, 61.11 against 16.67;
  - top-2, 69.44 against 33.33.
- **Five walks beat one walk but not three.** There are only 36 groups, and walks the model
  consistently gets wrong (P3's go to P2) stay wrong when combined.

## 6. Limb Doppler (identity-blind)

**Band energies.** Natural walks; conditioned spectrogram energy over the empty room recorded at the
same spot with RX2 beside the TX; all 12 empty-room recordings exist. Median ratio, with the fraction
of passes above 2:

| link | 10-35 Hz (torso) | 35-55 Hz (arms, shins) | 55-75 Hz (feet) | 35-75 Hz |
|---|---|---|---|---|
| RX1 (on the TX-RX1 line, F = 0) | 4.03 (0.99) | 1.45 (0.20) | 1.19 (0.21) | 1.35 (0.16) |
| **RX2 (beside the TX, F = 0.98)** | 6.34 (0.99) | 2.47 (0.56) | 1.92 (0.49) | **2.35 (0.53)** |
| RX3 (F = 0.5) | 3.07 (0.88) | 1.62 (0.28) | 1.45 (0.30) | 1.60 (0.27) |

**Predicted positions on RX2** at the median natural pace, 1.22 m/s, from f = 2 F v / lambda with
lambda = 0.123 m:
- the torso sits at **19.5 Hz**; 18.75 Hz is measured;
- **assumption:** arms at 1.5 to 2 v, which gives 29 to 39 Hz;
- **assumption:** feet at 2.5 to 3.5 v, which gives 49 to 68 Hz.
- At fast pace the feet can exceed 75 Hz and fold back to 150 minus f.
- The conditioning's 4 to 70 Hz band means the 55 to 75 Hz band measures 55 to 70 Hz.

**Figure:** `runs/identify/idwalks/physics/rx2_mean_spectrogram.png`, the mean conditioned
spectrogram per direction on RX2 with the predicted bands and the 75 Hz ceiling.

**Cadence:** clear stride periodicity shows in only **6 of 180** natural walks (3 %). That is RX2's
torso contour with an autocorrelation peak of at least 0.30 at 0.8 to 1.3 s.

**The gate** asks for the 35 to 75 Hz ratio to exceed 2 in at least half of RX2's natural walks. It
is 0.533, so the gate **passes, narrowly**.

**The gated EXPLORATORY arm:**
- **What changed:** a limb-band feature group (per link, the 35-55 and 55-75 Hz energy relative to the
  torso band, and the mean and SD of the 35-75 Hz centroid) was added to the three random-forest
  components of TR-AB. It was retrained for both folds.
- **EXPLORATORY:** 47.22 [29.44, 67.22] against the frozen ensemble's 46.67 on natural walks, paired
  **+0.56 [0.00, 1.67]**. Slow 35.83 against 35.00; fast 36.13 against 36.97.

**Reading:**
- **What RX2 sees:** there is energy above the empty room in the limb bands in about half the natural
  walks, more walking away than towards.
- **What the ratio can't separate:** limb Doppler from the broadband spread of a moving body.
- **For identification:** the features built from that band add nothing, and stride rhythm is almost
  never visible.
- **So, in plain words:** the ESP32 data at 150 packets per second show some energy in the limb bands,
  but **no usable limb Doppler for identification**.

## 7. Start press only

The end detector is causal and uses RX2 only (PLAN section 8). Its grid was tuned on the training day
only, and chose f 0.5 and h 0.25 s in both folds.

| | to B2 | to B1 | pooled |
|---|---|---|---|
| end-time error, median absolute (90th percentile) | 2.04 s (2.97) | 1.54 s (3.65) | |
| capped at 8 s | 6 of 60 | 18 of 120 | |
| accuracy, start press only | 21.67 | 37.50 | **32.22 [20.00, 47.22]** |
| accuracy, two presses | 41.67 | 49.17 | **46.67 [29.44, 66.11]** |
| change | -20.00 [-50.00, 10.00] | -11.67 [-24.17, 3.33] | **-14.44 [-26.67, -2.78]** |
| decision latency after the true end, median (90th) | 5.7 s (8.5) | 6.2 s (9.1) | |
| decision latency after the start press, median | 10.4 s | 10.5 s | |

- **The rule:** the change is below -3 points and its interval excludes zero, so **keep both
  presses**.
- **The reason is physical:** RX2's torso-band energy has no sharp end.
  - **Walking away,** it fades steadily as the walker leaves the TX, so the detector fires early.
  - **Walking towards,** the walk ends beside RX2, where stopping and turning keep the energy high,
    so it fires late.
- **A start-only demo** would need a different end cue (another link, or tracking's position, which
  this brief rules out).

## 8. What went wrong

- **Tracking's queue file.** The brief names it `reports/QUEUE.md`, but it is the root `QUEUE.md`.
  The plan says so, and the checks read the root file.
- **A missing check-in line.** The first 16:23 check-in line was not written, because the shell
  chain stopped on `grep -c`'s exit code. It was written one minute later.
- **A look at the test day before stage E.** While checking the detector code before stage E, I
  looked at B2's energy traces and detector errors for two grid settings. B2 is the test day of the
  "to B2" fold. Nothing was changed as a result: the grid, the tuning rule and the decision rule stand
  as locked.
- **Deviations from the plan's procedure, with dated notes:**
  - stage A's evaluation ran straight after stage A, before stage B;
  - a second lane was added at 17:58 when Uzayr said tracking was done.
- **No job failed.** All 20 queued jobs completed.

## 9. Limits

- **Sample size:** six people and two test days. The headline interval is about 37 points wide
  (29.44 to 66.11), and the paired intervals are 10 to 25 points wide.
- **Pace:** on natural walks pace alone (S0, 38.33) is not distinguishable from the model. The model's
  advantage appears only when the walker changes pace.
- **Uneven participants:** one participant is identified 87 % of the time and another 20 %.
- **Development evaluation, all data seen:**
  - the ensemble's components were chosen in earlier batches with Room B results in view;
  - this brief's rules were fixed before its own trainings.
- **Stage D:** the ratio cannot separate limb Doppler from broadband spread. The conditioning's
  70 Hz edge cuts the top of the feet band.
- **No further data will be collected.** DC1 and DC2 are the whole dataset.

## 10. Answers, in plain words

1. **Identification walks only.** On natural walks, trained on Room A and the other Room B day and
   calibrated only on other people's walks, the final model names the right person 46.67 % of the
   time out of six [29.44, 66.11]. That is nearly three times chance. But pace alone gets 38.33 % on
   the same walks, and the model is not clearly better than that. When people walk slowly or quickly
   on purpose, pace falls to chance and the model holds at 35 to 37 %.
2. **Room A.** Yes, Room A's data help. They add 18 points over the other Room B day alone, and 13
   over it with its tracking walks, both clearly above zero. The other Room B day on its own is not
   enough: 28.33 %.
3. **Direction.** Walking towards the TX scored higher than walking away (52 against 41 %), but on 90
   round trips the difference is not detectable at this sample size. A model trained in one direction
   identifies the other direction about as well. The data are consistent with the strongest,
   steadiest part of a towards walk falling near the receivers, but do not prove it.
4. **Slot structure.** No. Calibrating on the other five people's walks gives the same figure as
   calibrating on the day's earlier recordings (a difference of 2 points), so the dev batch's result
   was not an artefact of each person's own time slot.
5. **Start press only.** Not with this detector. It misses the end of the walk by about 2 seconds,
   because RX2 sees no sharp end, and accuracy drops by 14 points. Keep both presses for the demo.
6. **Deployment measures.**
   - The right person is in the top two 69 % of the time (chance 33 %).
   - Three walks together are right 61 % of the time.
   - In a household of two the model is right 78 % of the time (chance 50 %), and of three 66 %
     (chance 33 %).
7. **Physics.** The receiver beside the transmitter sees some energy above the empty room in the arm
   and foot bands in about half the walks. But features built from those bands add nothing to
   identification, and stride rhythm is almost never visible. At 150 packets per second the ESP32
   data contain no usable limb Doppler.
