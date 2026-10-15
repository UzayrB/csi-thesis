# QUEUE_IDGP. The authority on what to do next: integrated gait with pace as one parameter

**RULE: on every wake read THIS FILE FIRST and start the next PENDING item. Never end a turn while an
item is PENDING or RUNNING unless a background job will notify. Never wait for the operator. A
blocked item is marked BLOCKED with its reason and the next one starts.**

Batch 2026-09-23f (IDGP, revised brief with the identification contract), EXPLORATORY on Room A,
opened 19:47 SAST on 2026-09-23. The earlier 23f batch (opened 19:30) was cancelled at 19:38 before
any compute; its log is kept at the bottom. Tracking has priority. This run writes only
`reports/QUEUE_IDGP.md`, `reports/CHECKIN_LOG_IDGP.md`, `runs/identify/logs/*idgp*`,
`runs/identify/idgp/`, new `pipeline/identify/idgp_*.py` modules, new tests, and the report, addendum
and freeze files the brief names.

## Keep-alive, this run's own PIDs

| what | pid | state |
|---|---|---|
| caffeinate, governor, watchdog | none | **NOT RUNNING.** The permission classifier refused both launches at 19:47 ("interfere with workloads"). Not retried; the operator decides. |
| yield policy in force instead | | every compute job runs under `taskpolicy -c utility nice -n 19` with at most 4 single-thread workers while tracking is alive, and signals nothing |
| compute jobs | see the item rows | |

## Items

| # | item | status | next action | ETA |
|---|---|---|---|---|
| 1 | 23e freeze exists; record the Room A reopening | **DONE** 19:47 | 23e written 19:08; decision 11 appended | done |
| 2 | Contract pass object and tests; S_se; S_csi validation | **DONE** 19:56 | 10 contract tests pass, mutation-checked red; S_csi r = 0.05, FAILS, GPu dropped | done |
| 3 | Cadence, fused, with its reliability report | **DONE** 19:56 | person ICC 0.033 (below 0.2), days 0.464, links 0.55 Hz; margin 0 in all folds; geometry correction does NOT flatten | done |
| 4 | GP feature bank, CNN embedding per fold | **DONE** 19:58 | bank 360 x 676 per margin; 45 CNNs (9 training sides x 5 seeds), input equal to id25's | done |
| 5 | Arms and evaluation, nested | **DONE** 20:04 | A_fwd LOSO: S0 36.11, G 22.22, GP 25.00, GP+CNN early 36.11, late 30.56, stack 13.89 | done |
| 6 | Integrity checks, cohort, multi-pass, speed-overlap | **DONE** 20:06 | no pace arm passes check 1; frozen arm G by the rule; controls 90.28 / 71.94 | done |
| 7 | Freeze 23f, addendum C, DC2 scorer update | **DONE** 20:11 | addendum C 20:10 (sha eaa34447...); freeze 23f 20:11; `idgp_dc2_score` 8 synthetic tests pass; gate OK | done |
| 8 | Report, figures, tests, closing | **DONE** 20:17 | full suite 1247 passed, 8 skipped; `reports/CLOSING_IDGP_2026-09-23.md` | done |

## Fixed before any run (19:47 SAST, 2026-09-23). Nothing below is changed after results exist.

**Contract.** Features receive a `ContractPass`: amplitude of the three links from the start press to
the end press (plus a fixed margin of 0 or 0.5 s in the cadence variant only), the start and end
times, the path ID, its protocol length and the rig's node positions. Nothing else. Intermediate
anchors, the old walk_edge span, labels and tracking code are unreachable from it (tests).

**S_se** = protocol path length / (t_end - t_start): 5.0 m for A, B and E lines, 7.071 m for C and D.
**S_csi** = path length / CSI-sensed duration. Motion energy is the mean over links of the RMS across
subcarriers of the 0.3 to 70 Hz amplitude, smoothed over 0.5 s, on the bank's whole span. Threshold =
P20 + 0.3 x (P95 - P20) of that span; gaps under 0.3 s are merged; onset and offset are the ends of
the longest run above threshold. No press, anchor or window offset is used. GPu runs only if the
correlation of S_csi with S_se is at least 0.8 on the training side of every LOSO fold.

**Cadence.** Per link, three sources: envelope autocorrelation (RMS envelope, 0.8 to 3.5 Hz), Doppler
torso-contour autocorrelation (50th-percentile contour of the 4 to 70 Hz STFT of PCs 2 to 4), and
step-peak counting on the envelope. Periodicity: the autocorrelation peak height (sources 1 and 2)
and 1 - CV of the peak intervals (source 3). A source below 0.2 is dropped. Candidates are each rate
at x0.5, x1 and x2 inside step time 0.35 to 0.75 s (1.333 to 2.857 Hz). The harmonic is the
candidate with the greatest periodicity-weighted support within 0.1 Hz; the cadence is the
periodicity-weighted median of the supporting candidates. Per-link cadence uses that link's sources
only; the fused cadence uses all links. The margin (0 or 0.5 s) is chosen per fold by the
training-side person ICC of the fused cadence, never by accuracy.

**Feature blocks.** Pass level: fused rhythm (cadence, stride time, cadence variability, step-to-stride
autocorrelation ratio); pace (S_se); spatial (step length, walk ratio = S_se / cadence^2, and
speed-adjusted cadence fitted inside the fold on training rows). Per link: rhythm, Doppler contour
shapes (cycle-normalised c50 and c95 templates, leg-to-torso, q25 and q75 ratios, contour CV and
periodicity, frequency profile) in RAW and GEOMETRY-CORRECTED form (steady progress along the known
path, F(t) per frame, divide by 2F/lambda, mask F < 0.2), and envelope spectral shape. Per-link
blocks for late fusion and per-link rows use that link's own cadence; concatenation uses the fused
cadence.

**Arms.** S0 (S_se), G (no pace, no spatial), GP (all), GP+CNN early (GP concatenated with a 16-d
training-side PCA of the five-seed 2D CNN embedding), GP+CNN late (calibrated posteriors of the GP
arm and the CNN, summed log-probabilities), GP-stack (logistic stacker on G, S0 and CNN out-of-fold
log-posteriors from the inner folds), GPu (only if S_csi validates).

**Selection menu, in tie order.** Scope (b) all lines with per-line z, then (a) A_fwd only; heads
shrinkage LDA, logistic regression C 0.1, linear SVM C 0.1, random forest (300 trees), gradient
boosting; fusion concatenated, late F-weighted, late uniform; Doppler form corrected, then raw. Tree
heads never receive speed-adjusted cadence. S0 is searched over scope and head. Inner criterion:
accuracy on the validation side's A_fwd passes (all validation passes when fewer than 6), then the
mean probability on the true class, then menu order. LOSO inner: train one training session,
validate the other, both ways. Single-session pairings: the 60/40 temporal split per recording.

**Late-fusion weights.** Link weights sum to 1 and the pass-level model has weight 1. Uniform: a third
each. F-weighted: each link's mean F on the target path from `id15_factor_map` (Room A A_fwd: RX1 0,
RX2 0.5, RX3 0.5).

**Statistics.** Headline: nested LOSO, scored on A_fwd test passes (36). Cluster bootstrap over test
recordings, 1000; permutation p, identities permuted among the recordings of each test session, 1000.

**Integrity check 1 PASSES only if** the paired difference arm - S0 on the same A_fwd passes has its
95 percent cluster-bootstrap interval entirely above zero. Check 2: the arm's selected configuration
refitted with S_se alone, and with S_se, step length, walk ratio and speed-adjusted cadence removed;
share of gain from speed = (S0 - chance) / (arm - chance). Check 3: per fold, training-side d' of S_se
for all 15 pairs; the 5 lowest; two-person accuracy on their A_fwd test passes, selected
configuration refitted on the pair. Check 4: an arm failing check 1 is named "speed comparison".

**DC2 freeze rule.** Per fold, the arm with the highest inner accuracy among G, GP, GP+CNN early, GP+CNN
late and GP-stack. The frozen arm is the most often preferred among the pace arms that pass check 1
(ties to the higher mean inner accuracy); if none passes, G. Its configuration is the one its
selection chose most often across the three LOSO folds, ties to the higher mean inner accuracy. DC2
has only A_fwd, so its scope is A_fwd by necessity.

**Secondary tables.** Other paths: the arms re-selected with every line as target (scope b only),
scored per directed line and pooled. Multi-pass: A_fwd k = 1, 2; all lines k = 1 to 5 with the
selected configuration refitted in scope b, temperature fitted on inner out-of-fold posteriors.
Cohorts 2 to 6, all subsets, selected configuration refitted per subset. Within-day temporal,
labelled "same recording, confounded". Post-hoc ceiling: best candidate by test accuracy, never
quoted. Positive controls: walking direction (centre lines, chance 50) and line (chance 8.33), raw
Doppler, rhythm, envelope and motion profile, shrinkage LDA, global z, LOSO.

## Log

- 2026-09-23 19:47 SAST: batch reopened under the revised brief; decision 11 recorded; keep-alive
  launches refused by the permission classifier and not retried.
- 19:54 bank built (`idgp_bank`, 33 s). 19:56 `idgp_cadence`: S_csi fails (r 0.05, timing error
  median 1.47 s), cadence person ICC 0.033, the geometry correction steepens rather than flattens.
- 19:58 45 CNNs trained. 20:04 `idgp_eval`, 15 fold jobs, no errors. 20:06 `idgp_checks`, all six parts.
  No pace arm beats S0 (best: GP+CNN early, difference 0.0 [-22.29, 25.0]); DC2 arm = G by the rule.
- 20:10 addendum C written (clock read; data/room_B absent). 20:11 freeze 23f. The addendum B erratum
  is NOT in addendum C: the handover marks it OPEN (ask first), so it waits for the operator.
- 20:13 figures FGP1 to FGP5; 20:14 report section 23f appended (first 780 lines unchanged), quotable
  EXPLORATORY block and STATE.md entry appended; walk-ratio citation verified. 20:16 closing report
  drafted; full suite running (background, nice 19).
- 20:17 full suite 1247 passed, 8 skipped. BATCH CLOSED. Nothing of this run is still running; no
  keep-alive process was ever started, so there is nothing to stop.

## Previous batch (cancelled), kept for the record

- 2026-09-23 19:31 SAST: batch opened; keep-alive started and verified; decision 10 recorded.
  ERRATUM noted for addendum B: its stated amendment times (19:20, 19:35, 19:55) were estimated, not
  read from the clock, and postdate its own freeze (19:08). Content and order stand. The correction
  goes into addendum C and the 23f freeze, because addendum B is hashed.
- 2026-09-23 19:38 SAST: BATCH CANCELLED by the operator before any compute started (items 2 to 8
  never ran). caffeinate, governor and watchdog stopped; check-ins cancelled.
