# Identification: the summary to write the thesis chapter from

Written 2026-09-24. It adds no analysis. Every number below already exists in a report, and its
source is given as file and section.

- `REC` is `reports/IDENTIFICATION_2026-09-18.md`, cited by section title.
- `QUOT` is `reports/ID_QUOTABLE_2026-09-23.md`, which lists the only figures the thesis may quote.

Six participants throughout, reported as P1 to P6, so chance is 16.67 percent. Intervals are 95
percent cluster bootstraps over recordings.

## 1. The question and the constraints

- **The deliverable.** TDR-03's second deliverable, beside tracking, is device-free person
  identification from Wi-Fi CSI (`README.md`): name which of six enrolled people is walking, from the
  radio alone. The project brief's exact wording is not in the repository, so quote it from the
  brief itself.
- **Gait first.**
  - **The choice.** The branch identifies people by how they walk, meaning rhythm and Doppler
    content. Static amplitude levels were excluded from every gait arm, because they recognise the
    recording (§3).
  - **The constraints.** It assumes the walk's boundaries and its line are known, rather than asking
    a general model to find them. That is the constraint idea tracking used (REC, "Why this branch
    was built on constraints rather than on another model").
- **The rig.** One TX, three single-antenna ESP32 receivers, 2.4 GHz, amplitude only, about 150 Hz.
  It sits in a 5 by 5 m room with twelve taped lines, recorded over three sessions of 20 passes per
  person (360 passes).

## 2. The history, in date order

1. **12 September, archived.** An eight-class arm, with two participants since retired, lost to
   speed alone: CNN 15.7 against speed 28.6. It is not comparable with anything since (REC, "History,
   clearly labelled").
2. **18 September, the ladder.**
   - Per-pass gait features peaked at 25.83 percent cross-day, and per-line z-scoring gave 25.83.
   - Two- and three-person figures of 66.0 and 50.5 were reported, and "the gait question" was
     answered YES on 3 pairings (REC, "The ladder" and "Verification").
   - **All of this is superseded** (§4).
3. **19 September, the live mode and voting.**
   - **The geometry columns are inert:** a shuffled line scores the same 25.8 as the true one.
   - **Per-line z-scoring does not survive a live tracker's line** (22.22), which needs about 68.5
     percent agreement (REC, "The geometry features are inert", "How accurate must the line be").
   - **Voting passes does not help gait** (23.3 at one pass, 21.1 at five), while speed alone rises
     from 28.33 to 42.67 (REC, "Multi-pass voting").
4. **23 September, morning, the corrections and conditioning** (pre-registered,
   `PREREG_ID_2026-09-23.md`).
   - **Head fixed before the run:** the 19b figures fall from 22.222 and 25.926 to 19.167 and 21.852.
     The difference was test-set head selection.
   - **Oracle cadence:** the reference arm's cadence had used oracle speed on 115 of 360 passes.
   - **No gait arm passed R6.** The best, A3, scored 20.833 with interval [9.17, 35.83] (REC, section
     "2026-09-23"; appendix, `CLOSING_ID`).
5. **23 September, the nested maximisation (23b).** 174 feature configurations and 18 heads, every
   choice nested.
   - The cross-day headline is 15.83 [10.28, 21.67], p 0.71.
   - Speed alone is 32.50.
   - A 2D CNN on Doppler spectrograms scored 27.22, falling to 23.89 with speed removed (REC,
     "2026-09-23b").
6. **23 September, feature-code checks (23e).** A shared cadence leaks rhythm into "single-link" rows
   (66.7 percent on a noise-only link, synthetic). The features also carry segment length, and so
   pace (REC, "2026-09-23e").
7. **23 September, the integrated-pace run (23f, EXPLORATORY).**
   - **Under the identification contract** (only the CSI between the start and end presses, those
     times, and the path), pace from walk start and end scored 36.11 on A_fwd (n = 36).
   - Gait without pace scored 22.22.
   - The best integrated arm tied pace at 36.11, a difference of 0.0 [-22.29, 25.00]. No arm beat
     speed alone (REC, "2026-09-23f"; QUOT, EXPLORATORY block).

## 3. What failed, and the measured mechanism

- **Within-day accuracy is recording recognition.** Each person-session is one recording. Static
  levels alone, with no gait, identify people within a day at 91.67 to 98.61 percent and fall to
  20.28 across days. Frozen gait features name a new person's session at 80.33 against 33.33 (QUOT,
  "Within-day" and "Session-ID control").
- **Cadence is not reproducible:**
  - the links disagree by a median 0.60 Hz, and the within-person ICC is 0.018 (QUOT, "Cadence
    inconsistency");
  - fused across three sources and three links it is still 0.033 per pass, with 0.55 Hz between
    links (REC, 23f, "Pace and cadence as measurements").
- **Speed cannot be read from the signal.** The torso-contour speed proxy gives r = 0.102 against true
  speed (REC, 2026-09-23, "Conditioning"). A motion-energy walk detector gives r = 0.05 (REC, 23f).
- **Doppler does not follow the bistatic geometry.**
  - On A_fwd the projected factor F rises from 0.18 to 0.82, which predicts a rising torso contour
    (slope +1.41). The observed contour is flat (-0.05), and correcting it for F produces -1.67.
  - The earlier physics check was not decidable, because Room A's F spans only 3.0 Hz of prediction
    against a 2.34 Hz bin (REC, 23f, and 2026-09-23 "Conditioning").
- **No Room A line gives strong Doppler.**
  - Room A's lines span mean F 0.333 to 0.474, and every one fails the pre-registered F gate.
  - Line A is F = 0 on RX1 for its whole length.
  - No layout spread over three or more walls passes. A gait-first corner layout reaches minimum-link
    F 0.938 against this rig's 0.373 (QUOT, "Geometry"; REC, 2026-09-23 "The corridor").
- **The pipeline itself works.** Its positive controls score: direction 94.44, line 72.78, session
  80.44, and an injected rhythm 32.22 (QUOT, "Positive controls"). Under the contract, direction and
  line reach 90.28 and 71.94 (REC, 23f).

## 4. The corrected record (REC, "2026-09-23c")

| superseded claim | why | replaced by |
|---|---|---|
| two-person 66.0, three-person 50.5 | test-set head selection, not nested | 49.33 and 32.44, both at chance |
| "the gait question was answered YES" | oracle cadence and test-set heads | none: on Room A the answer is no |
| 25.8 and 22.2 across days | head picked on test accuracy | 21.85 and 19.17 with the head fixed, then the nested 15.83 |
| cadence from harmonic resolution | oracle speed on 115 of 360 passes | CSI-only cadence, ICC 0.018 |
| realistic pipeline 31.67 and 30.00 | one pairing, heads picked on test | nested nine-pairing 19.26 |
| random-forest speed-residualised 27.5 | the test-side residual re-injects speed | linear head: 14.72 |
| verification AUC 0.684, EER 0.405 | never re-run nested | none |
| any within-day figure as identity | the person and the recording are one variable | quoted only beside 91.67 to 98.61 |

## 5. The quotable figures (QUOT)

| figure | value |
|---|---|
| nested headline, cross-day, leave one session out | **15.83** [10.28, 21.67], p 0.71; nine pairings 19.26 [15.83, 22.96] |
| cohort curve, 2 to 6 people | 49.33, 32.44, 23.50, 18.83, 15.83 (chance 50, 33.3, 25, 20, 16.7) |
| within-day, RECORDING RECOGNITION | gait 32.64 [23.59, 40.97]; static levels 91.67 and 98.61, 20.28 across days |
| session-ID control | 80.33 [77.92, 82.47] against 33.33 |
| S0, oracle speed alone, a control | 32.50 [23.89, 42.50]; 36.11 with 5 passes voted |
| positive controls | direction 94.44, line 72.78, session 80.44, injected rhythm 32.22 |
| CNN secondary, POST HOC | 27.22 [21.11, 33.61]; speed removed 23.89 [17.22, 31.39] |
| cadence | links differ by 0.60 Hz; ICC 0.018; r with speed 0.156 |
| within-recording ICC | 0.421 |
| geometry | Room A lines mean F 0.333 to 0.474; line A F = 0 on RX1 |
| **EXPLORATORY (23f)**, A_fwd, n = 36 | pace from walk start and end 36.11 [19.44, 52.78]; gait without pace 22.22 [8.33, 41.67]; best integrated 36.11, minus pace 0.0 [-22.29, 25.00] |

**How to state it (QUOT).** Across days, six-way gait identification is at chance on this rig at
every cohort size. The pipeline passes its positive controls, and within-day accuracy is recording
recognition. Walking speed carries more identity than any gait representation built here, with or
without pace among its inputs. **The wording "identification from Wi-Fi-sensed spatio-temporal
gait parameters, of which pace is one" is not available** (REC, 23f).

## 6. The redesign for DC2, and why

- **The ring layout.** The Room A nodes sit one per wall around the grid. As Uzayr gives it, the
  layout followed Gaiba et al.'s walk across the links. This rationale is not recorded in the
  reports; cite the paper (§9). The ring is right for tracking, which multilaterates, and wrong for
  Doppler (§3). The conflict is REC, 2026-09-23, "The corridor".
- **A doorway-style identification link beside the TX.**
  - For each person's identification slot only, RX2 moves to (2.0, -0.5), facing north, then goes
    home before tracking (decision 5, `DECISIONS_ID_2026-09-23.md`).
  - With both ends behind the walker, that link has mean F 0.981 on line A against 0.46 for the best
    Room A line (decisions 5 and 6).
- **The path, A_fwd:** line A, walked north away from the TX.
  - With RX2 moved, A_fwd gives the identification link F 0.854 at its start and 0.981 on average.
  - E_row1 would put the moved link's dead spot mid-walk, at F = 0 (decision 6).
  - TX-RX3 is 0.500, and TX-RX1 stays blind at 0.000 (`PREREG_ID_DC2_2026-09-23_ADDENDUM_B.md`, P2).
- **The contract.** Identification receives only the CSI between the start and end presses, the two
  press times, and the path and its length: nothing from tracking and no intermediate press. This
  is what a deployed walk-through system would know (REC, 23f; enforced by
  `tests/test_idgp_contract.py`).
- **The design choices around the link:**
  - pace blocks, compulsory (decision 2), placed on day 2 as slow and fast by the 23e slot design,
    because they are the only direct test of gait against speed;
  - day 2 in reverse order (decision 8);
  - within-day demoted to a confounded label, because each person's walks come from one slot
    (decision 9).

## 7. What DC2 tests, and what was expected before it

- **The analyses** (pre-registration, addenda B, C and D):
  - **P1**, cross-day, day 1 natural to day 2 natural: PRIMARY, SECONDARY and S0 on the same passes;
  - **P1-GP**, the arm without pace (G) against S0, with four integrity checks;
  - **P2**, the per-link geometry test, TX-RX2 > TX-RX3 > TX-RX1, on single-link, fixed-length
    features;
  - **P3**, the pace test;
  - **P4**, the placement control;
  - **P5**, the recording and session controls;
  - **P6**, cross-room on TX-RX3.
- **The power limits, stated before the data.** With 30 test passes the 95 percent half-width is about
  15 points. So a true accuracy near 25 percent will not separate from chance in P1 (addendum B,
  section 4). At the measured ICC of 0.421, blocks matter more than passes (REC, appendix,
  `CLOSING_ID`, "The DC2 sheet").
- **The decisive tests are P2's ordering and P3's contrast with speed** (addendum B, section 4).
- **P1-GP is not expected to beat S0.** Its only route to showing gait is to hold its level on the
  pace blocks while S0 drops, which would read GAIT-CONSISTENT (addendum C, section 5).

## 8. Figures available (all tracked in git)

| folder | figures |
|---|---|
| `reports/figures/identify/2026-09-23/` | F8 conditioning ablation, F9 arms per pairing, F12 DC2 power, F15 speed leakage, F17 and F17b factor maps |
| `reports/figures/identify/idmax/` | F1 cohort size, F2 positive controls, F3 confusion, F4 gait cycles, F5 Doppler spectrograms, F6 voting, F7 within-day against cross-day |
| `runs/identify/idgp/figures/` | FGP1 headline against pace, FGP2 cohort, FGP3 multi-pass, FGP4 speed-overlap test, FGP5 cadence reliability (EXPLORATORY) |

Each exists as PNG and PDF. The idmax ones also have a JSON of their data.

## 9. Citations to verify before submission

- **Gaiba et al.**, IEEE CCNC 2024, doi:10.1109/CCNC51664.2024.10454655.
- **WiWho:** Zeng et al., IPSN 2016.
- **WifiU:** Wang et al., UbiComp 2016, doi:10.1145/2971648.2971670.
- **CARM:** Wang et al., MobiCom 2015, doi:10.1145/2789168.2790093.
- **Sekiya and Nagasaki,** *Gait and Posture* 7 (1998) 225 to 227. Checked against its bibliographic
  record on 23 September: the walk ratio (step length over step rate), with test-retest ICC 0.6 to 0.8.

## 10. DC2, the second room (added 2026-09-28)

Added after DC2 was scored; sections 1 to 9 are unchanged. Sources: `REC`, section "DC2
identification, confirmatory and exploratory (2026-09-28)"; `QUOT`, "DC2 block, 2026-09-28". In this
section participants are "participant P1" to "participant P6" and analyses "analysis P1" to "analysis
P7".

- **What was captured.** Two days in Room B (26 and 27 September), six participants, 60 recordings:
  line A walked in both directions, natural blocks on both days and slow and fast blocks on both, with
  RX2 moved beside the transmitter (mean F 0.981) for identification. Every departure and its
  treatment is in addendum E, including one press relabel made before any figure and the day 1 RX2
  low state in two participants' training blocks.
- **The confirmatory answer.** Analysis P1, the cross-day result, is 26.67 percent [13.33, 36.67]
  against 16.67, so it does not separate from chance, as the pre-registration expected at this sample
  size; speed from the presses (S0) reaches 40.00 percent on the same passes. P1-GP, gait without pace,
  reaches 30.00 percent and fails its first integrity check against S0.
- **Geometry.** Analysis P2's ordering is NOT HELD: TX-RX2 and TX-RX3 tie at 23.33 percent on
  fixed-length crops. The physics nevertheless behaves: TX-RX2's torso contour tracks 2 F v / lambda
  across passes (Spearman 0.744), which TX-RX3's does not (0.276), and the along-walk trend fails on
  TX-RX3 as on Room A.
- **Gait against pace.** Analysis P3 is NOT DECIDABLE, because speed itself did not drop reliably on
  the pace blocks. Pace-matched, analysis P7, leaves PRIMARY at chance on slow walks and at 40.00
  percent (p 0.056) on fast ones. Wherever gait and pace met on the same passes, pace was at least as
  good.
- **Exploratory, labelled.** The reverse direction gives PRIMARY 23.33 and S0 50.00 percent; the GP
  arm is a "speed comparison" in both directions; arm G's frozen head cannot split fewer than 40
  training passes, so its day 2-trained cells, and the confirmatory check 3, are chance by
  construction.
- **What the chapter may claim.** A pre-registered, twice-replicated negative for cross-day Wi-Fi CSI
  gait identification on this rig and cohort; that walk timing carries more identity than gait; and
  that a receiver beside the transmitter sees Doppler that follows the bistatic prediction. Not gait
  identification, not integrated gait, and not that better geometry improves identification.
- **Figures.** `runs/identify/dc2/explore/figures/`: spectrograms by the median-duration rule,
  analysis P1's confusion matrices, analysis P2 against F, analysis P3 against S0 (EXPLORATORY
  figures of confirmatory numbers, except the spectrograms, which carry none).

## 11. Identification on the identification walks (added 2026-09-29 18:58, development evaluation, all data seen)

The record is `reports/ID_WALKS_2026-09-29.md`, under the brief `reports/BRIEF_ID_WALKS_2026-09-29.md`
with its rules locked in `runs/identify/idwalks/PLAN.md` before any training. The model is the final
eight-component ensemble of `reports/ID_DEV_FINAL_2026-09-29.md`, scored on Room B's identification
walks only (419 passes; natural n 180), with the other Room B day as the test.

- **Headline.** Trained on Room A and the other Room B day, and calibrated on the other five people's
  walks: 46.67 percent [29.44, 66.11] on natural walks against 16.67 chance. Pace alone (S0) reaches
  38.33 on the same walks, and the model is not distinguishable from it at natural pace (+8.33
  [-14.44, 27.22]). On deliberately slow and fast walks S0 falls to chance (17.50, 16.81) while the
  model holds at 35.00 and 36.97 (fast: +20.17 [4.24, 32.77]).
- **Room A helps.** +18.33 [8.33, 27.78] over the other Room B day's identification walks alone
  (28.33), and +12.78 [8.89, 16.67] over them with that day's tracking walks.
- **No slot-structure dependence.** Calibrating on the day's earlier recordings against the other
  people's walks: -2.22 [-6.11, 1.67].
- **Direction.** Towards 52.22 against away 41.11 on 90 round trips, -11.11 [-23.33, 1.11]: no
  detectable difference at this sample size. Identity carries across directions.
- **Deployment.** Top-2 69.44 (chance 33.33); three walks 61.11; a household of two 78.44 (chance 50).
- **Start press only.** A causal RX2 end detector misses the end by about 2 s; accuracy falls by
  14.44 [-26.67, -2.78], so both presses stay.
- **Limb Doppler.** RX2 beside the TX sees energy above the empty room in the 35 to 75 Hz band in
  53 percent of natural walks (the gate passes narrowly). Limb-band features add nothing (EXPLORATORY,
  +0.56 [0.00, 1.67]), and stride periodicity is clear in 3 percent of walks. So there is no usable limb
  Doppler for identification at 150 packets per second.

## 12. The one-press identification engine (added 2026-09-30 13:44, development evaluation, all data seen)

**Sources:**
- the record: `reports/ID_FINAL_2026-09-30.md`;
- the brief: `reports/BRIEF_ID_ENGINE_2026-09-30.md`;
- the rules: `runs/identify/engine/PLAN.md`, committed before any training.

The engine is one model, both the live app and the source of every figure below, replayed causally from
the recordings. **Identification is frozen.**

- **GS** (per-packet amplitude normalisation) was tested on the 600 tracking passes: -2.00
  [-4.00, +0.50]. **Not adopted.**
- **One press, 3 s.** The operator presses once when the walker starts. The engine detects the
  direction from RX2's energy slope (96.9 % of 419 walks). It measures the speed from torso Doppler
  (Pearson 0.82, 0.10 m/s median error on the identification walks). It decides a median 0.42 s after
  its 3 s window, a median 0.86 s before the recorded end of the walk.
- **The headline** (natural identification walks, calibrated causally on earlier walks that day):
  **36.11 percent [24.44, 52.22]** against 16.67 chance.
  - Press speed alone reaches 38.33 (engine minus S0: -2.22 [-25.56, 15.56]).
  - On fast walks the engine leads speed by +13.45 [-5.04, 30.01], **not separable from zero**.
- **Leave one session out** (tracking walks, route known): **Room A 30.83, Room B 29.17**.
- **Deployment:** top-2 54.44 (chance 33.33); a household of two 70.33 (chance 50); three walks 46.30.
- **The cost of one press** against the two-press model:
  - -3.89 [-14.44, +5.56] on natural identification walks;
  - **-8.61 [-15.28, -0.83] on Room A's tracking walks**, mostly from the shorter window (-6.67
    without pace).
- **The clock.** Causal clock mapping agrees with the whole-file map to 0.51 ms (99th percentile) and
  handles the dataset's one receiver reboot.
- **Cadence.** Where the rhythm is clear, the cadence resolver never confuses step with stride, but
  reads a median 12 percent low.
- **What the chapter may claim:**
  - a live, causal, one-press identifier at about twice chance, which knows its own direction and speed;
  - not that gait beats pace at natural pace;
  - the pace-robustness claim is weaker than for the two-press model (a framing decision for Uzayr).

## Names (added 2026-09-30 18:18, development evaluation, all data seen)

**The key from code to name.** From 30 September 2026 participant names are used everywhere (Uzayr: ethics
clearance; the names are nicknames). Earlier reports keep their P1 to P6 codes and are not rewritten.

| code | name |
|---|---|
| P1 | PA5 |
| P2 | PA1 |
| P3 | PA2 |
| P4 | PA3 |
| P5 | PA4 |
| P6 | PA6 |

**The final engine** (`reports/ID_EXTRAS_2026-09-30.md`; unchanged by the last attempt at a gain).

**Per participant,** natural identification walks, causal, pooled over both Room B days (30 walks each):

| PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |
|---|---|---|---|---|---|
| 33.3 | **73.3** | 16.7 | 26.7 | 33.3 | 33.3 |

**The last bounded attempt at a gain: nothing adopted.** Each candidate was judged by the audit's rule,
fixed beforehand:
- **precise Wi-Fi speed:** its physics gate was not met, at r = 0.697 against the 0.70 needed;
- **speed-profile features:** 0.00;
- **offset training windows:** -3.33, worse;
- **a lean correction learned from the training days:** -0.56.

The headline stays **36.11 percent [24.44, 52.22]**.

**Without same-day adaptation** (training statistics only): 32.78 [16.11, 55.00]. Adaptation adds +3.33
[-4.44, 10.56], which cannot be separated from zero.

**Against the speed the engine measures itself** (S_wifi, 23.89): the engine leads by **+12.22 [0.56,
25.00]**. So it identifies people beyond its own Wi-Fi speed. S0 (38.33) uses a two-press stopwatch the
engine never has.

**When the engine is confident:**
- the top 50 % of walks by displayed confidence are right 43.33 %, and the top 30 % 46.30 %;
- in the top 30 %, 16 of the 25 correct answers are PA1's walks, so "confident" mostly means PA1;
- AUROC 0.60.


## 13. Engine v2 (the cadence bug fixed) and the teaching pack's checks (added 2026-10-01 15:18, development evaluation, all data seen)

**The record:** `reports/ID_TEACHING_PACK_2026-10-01.md`. The handoff is
`reports/HANDOFF_IDENTIFICATION_2026-10-01_PM.md`.

**A bug, found by simulated truth.**
- **The test:** 48 simulated walks with known step rates (1.5 to 2.2 Hz, both directions, 1.0 to 1.4 m/s)
  were pushed through the engine's own extraction.
- **What it showed:** the step-rate (cadence) resolver read fast walks away from the transmitter at 0.73
  to 0.91 of the truth, and only 33 of 48 fell within 5 %.
- **The cause:**
  - channels with no rhythm voted equally with clear ones;
  - their estimates sat at the 0.8 Hz band-pass edge and were doubled into the step band.
- **The fix:** only channels whose autocorrelation peak is at least 0.30 vote. It resolves 48 of 48
  within 5 %.
- **The decision:** Uzayr adopted it as a bug fix whatever its effect (engine v2, 1 Oct 13:09). Every
  figure was rebuilt, and only the gait features changed (944 of 1,019 windows). The real walks' resolved
  step rate now agrees with the energy envelope in median (ratio 0.996, from 0.886).

**Engine v2's figures.**

| figure | engine v1 (30 Sept) | engine v2 (1 Oct) |
|---|---|---|
| natural identification walks | 36.11 [24.44, 52.22] | **35.56 [21.11, 52.78]** |
| leave one session out, Room A / Room B | 30.83 / 29.17 | 30.28 / **23.75** |
| the engine minus press speed (S0), natural | -2.22 | -2.78 [-26.11, 15.56] |
| the engine minus its own Wi-Fi speed (S_wifi), natural | +12.22 [0.56, 25.00] | **+11.67 [-1.67, 25.56]** |
| the engine minus S0, fast walks | +13.45 | +10.08 [-13.45, 30.25] |
| one-press cost, tracking walks pooled | -5.50 | -8.00 [-13.00, -2.33] |

**What weakened, plainly:**
- **Speed:** at natural pace the engine is now distinguishable from neither speed control.
- **Room B:** leave one session out falls to 23.75, the cost of the fix.

**The teaching pack's three checks** (engine v2, B2 or both folds, causal).
- **Substitution:** another person's radio placed in a walk's slot carries the donor's own decision in
  91.67 % [75.00, 100.00] of 60 swaps. No swap names the host unless the donor's own walk was already
  named as the host: the answer follows the radio.
- **Shuffled labels:**
  - the full engine retrained on labels permuted within each training session scores 20.00 % [13.33,
    28.33] on B2's natural walks, against 16.67 % chance;
  - the five feature components alone score 26.67 % on B2 with real labels, inside the null of 20
    permutations (p = 0.143);
  - **on engine v2 the gait features alone do not separate from shuffled labels on B2.** The CNNs alone
    score 30.00 % on both folds and the features alone 22.22 %.
- **Conditioning ablation** (information): removing the log and mean subtraction costs -10.56 [-22.78,
  -2.78], the only step whose removal is separable from zero.
  - Replacing PCA with the subcarrier mean costs -13.89 [-29.44, 2.22];
  - keeping PC1 costs -5.00;
  - removing the band-pass costs nothing.
  - Identity-blind, conditioning lifts RX2's torso band from 1.45 to 6.37 times the empty room.

**The addendum.**
- **AC1:** the bug above.
- **AC2, same day, confounded by recording:** trained and tested on one Room B day (alternate walk cycles), natural walks score 55.00 % [26.67, 81.67] on B1 and 70.83 % [50.00, 91.67] on B2, against 35.00 and 37.50 for the cross-day engine on the same walks (+20.00 [0.00, 41.67] and +33.33 [16.67, 54.17]). Each person's walks come from their own recording slot, so this measures recognising the person plus their recording, which is why published same-session figures run high.
- **AC3, training without the slow and fast walks:** removing the other Room B day's slow and fast walks from training changes natural walks by -1.11 [-7.78, 7.78] (34.44 against 35.56) and costs slow walks -5.83 [-10.83, -1.67] (fast -3.36 [-13.33, 6.72]). The paced walks are in training because they help the paced walks; they do not measurably help natural ones. Information only.

**The live app:**
- B2 streamed through the rig path equals the harness on 299 of 299 decisions on engine v2;
- the slow tests pass (13 of 13);
- the render's score becomes 21 of 60, so it must be re-recorded.

## 14. Engine v3: two bug fixes, and one test of domain-adversarial training (added 2026-10-01 20:15, development evaluation, all data seen)

**The record:** `reports/ID_V3_DANN_2026-10-01.md` (7b032fe). **Engine v3's figures are the thesis figures;** v2's
(section 13) are superseded.

**Why the headline fell from v2 to v3.** Two bug fixes were adopted whatever their effect. v2's 35.56 % included
about 3 points from calibrating identification walks on tracking recordings made with another antenna layout. A home
has one layout, so v3 calibrates each window only on earlier windows of its own layout (fix L). v3 also gives a walk
with no measurable rhythm no step rate (fix F).

| figure | engine v3 |
|---|---|
| natural identification walks (each Room B day held out; trained on the other four sessions; causal) | **32.22 % [17.78, 48.33]** (to B2 33.33, to B1 31.67) |
| slow, fast | 25.83 [9.17, 43.33], 23.53 [15.13, 31.93] |
| leave one session out, tracking walks: Room A / Room B | 31.67 [24.44, 38.06] / 27.50 [19.58, 39.58] |
| the engine minus press speed (S0), natural | -6.11 [-29.44, +12.22] |
| the engine minus its own Wi-Fi speed (S_wifi), natural | +8.33 [-3.33, +21.11] |
| the live app against the harness (B2, rig path) | 299 of 299 decisions equal |

- **Speed:** as on v2, the engine separates from neither speed control at natural pace.
- **DANN** (domain-adversarial training, one seed, both folds) did not help:
  - the deployable arm gained 0.00 [-3.89, +3.89] (lambda_max 0.1) and lost 5.00 [-12.22, +2.22] (1.0) against the
    same seed without it;
  - even with the test day's own unlabelled windows in training, alignment moved the result by at most +1.11
    [+0.00, +3.33];
  - so aligning the CNN features across sessions closes almost none of the 20 to 33-point gap between same-day and
    cross-day accuracy.
- **The cost of one press:** -7.78 [-17.78, +3.89] on natural walks (32.22 against 40.00).
  - It is measured against the frozen two-press reference, which was built with the v1 step-rate resolver, and its
    interval includes zero. It is reported, not leaned on.
- **The window stays 3.0 s.** T was not changed on the strength of the T-sensitivity check, although 3.5 s gave 35.00 %
  [21.11, 50.00] (information). Any change of window comes only through the rule of
  `reports/BRIEF_ID_WINDOW_GAIT_2026-10-01.md`.

## 15. Engine v4: the 4.0 s window, and an overnight of levers that did not help (added 2026-10-02 02:47, development evaluation, all data seen)

**The records:** `reports/identification/2026-10-02_lean-in.md` (the window and the v4 build; b13808d, 0ba56ab) and
`reports/identification/2026-10-02_overnight.md` (the overnight levers and the teaching pack; d5477fa). **Engine v4's
figures are the thesis figures;** v3's (section 14) are superseded.

**What changed.** A screen of eight windows (3.0 to 6.0 s) put 4.0 s on a plateau (3.75 s 36.11, 4.0 s 37.78, 4.25 s
36.67), so the window was lengthened to 4.0 s, with a radio-only end detector so the Wi-Fi speed is measured on the
walking span. The window was chosen with all the data seen, and the thesis should say so.

| figure | engine v4 |
|---|---|
| natural identification walks (each Room B day held out; trained on the other four sessions; causal) | **37.78 % [23.33, 53.33]** (to B2 30.00, to B1 41.67) |
| against engine v3, paired | +5.56 [+1.67, +10.56] |
| slow, fast | 29.17 [6.67, 54.17], 30.25 [20.34, 42.02] |
| leave one session out, tracking walks: Room A / Room B | 32.50 [23.06, 39.72] / 27.92 [19.58, 38.75] |
| the engine minus press speed (S0), natural | -0.56 [-25.56, +17.78] |
| the engine minus its own Wi-Fi speed (S_wifi), natural | +6.11 [-21.67, +31.11] |
| no same-day calibration (CAL-none), natural | 40.56 [22.78, 61.67] (adaptation -2.78 [-8.33, +3.33]) |
| the live app against the harness (B2, rig path) | 299 of 299 decisions equal; the render 18 of 60 |

- **Speed:** as before, the engine separates from neither speed control at natural pace.
- **The overnight levers** (a speed learned from the radio with the stopwatch as teacher, nine CNN seeds, a physics
  vote, MiniRocket) all failed the step rule against v4 (+0.00, -0.56, -1.11, -1.11). The learned speed tracks the
  stopwatch better than the Wi-Fi speed (natural Pearson 0.766 against 0.713) yet identifies worse alone (21.67 %
  against 31.67 %).
- **The teaching pack's checks on v4:** the decision follows the radio in 75.00 % [41.67, 100.00] of substitutions (v2:
  91.67 %); the shuffled-label engine scores 16.67 % (chance); the feature components alone stay at the shuffled-label
  level on B2 (p 0.143); no single conditioning step's removal is separable from zero.
- **What stands in the way of more** (the overnight report, section 10): v4 sits at the speed ceiling (the stopwatch
  alone 38.33 %), because each person's speed moves between days by about as much as the gaps between people, and
  RX2's gait identity does not cross days (45.24 % same day against 15.48 % across days), because RX2 was re-placed for
  every person's slot.

## 16. The final decision: engine v4 (added 2026-10-02 07:28, development evaluation, all data seen)

**The record:** `reports/identification/2026-10-02_v5-check.md` (b911d91). Engine v4 without same-day calibration
(training statistics only, no AdaBN) was scored as a candidate engine v5: natural 40.56 % [22.78, 61.67], +2.78
[-3.33, +8.33] against v4, not separable from zero. It failed its check on Room B tracking (23.33 % against a floor of
23.47 %, one walk of 240), and it weakened the measures that combine walks (5 walks 38.89 % against 55.56 %). Uzayr
kept engine v4 (2 Oct 07:28). **Engine v4's figures (section 15) are the final identification figures;**
identification is closed (`reports/identification/2026-10-02_handoff.md`).
