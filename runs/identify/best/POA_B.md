# POA_B: identification, build the best model (exploratory, adopt nothing)

Written 10 Oct 2026, 08:25:42 SAST by the Third overall chat, from Uzayr's prompt (received at about 08:22 on 10 Oct) and his message asking for
P2 (tracker speed) to be tried both ON and OFF. Committed before any scoring (block 2 onward).
**Exploratory development, all data seen. Nothing is adopted; engine v4 stays shipped until Uzayr decides.**

## 0. What this run is, plainly

- **Selection is on A3 and B2.** Every candidate and every greedy step is chosen on this morning's combine scorecard,
  which is built from A3 and B2 (the xr models' test sessions and the loso folds that hold them out).
- **Every scored configuration is a look at A3 and B2 and is counted** (listed with its date, models and cells).
- **Nothing in this run is confirmatory.** The winner is selected on the data it is scored on, so its figures are
  optimistic by an amount this run cannot estimate.
- **No figure from this run may be reported as a held-out or generalisation result.** A generalisation claim for the
  winner needs data it was never chosen on (new sessions).

## 1. The scorecard (`ilc_outer`, unchanged)

Z (the three zero-shot cells), D (the ten cross-day cells), the guard (loso natural, slow and fast each no more than 5
points below v4), every cell with v4 and S0 beside it; a candidate's score is (Z + D) / 2, reported against v4 and F7
(this morning's F7: Z 27.22, D 31.11). Intervals as this morning (paired participant bootstrap, 10,000 draws, seed 0).

## 2. Candidates (fixed now; the contract of PREREG_LP binds every one)

- **P1, learned path-walk speed:** a regressor (sklearn HistGradientBoostingRegressor, max_iter 200, learning_rate 0.05,
  max_depth 3, random_state 0) from the link-weighting cache's three per-link contours (per link: median contour, its 25th
  and 75th percentiles, the median of contour / F at the nominal position, the fraction of usable frames), the route
  (one-hot), each link's mean F, onto the press speed; on the walking span of the model's alpha. Trained on the model's
  training sessions' path walks only; the training rows' pace column is cross-fitted by session; identification walks keep
  the Wi-Fi speed. A model with one training session (xr_B1) cannot be cross-fitted by session: it keeps the Wi-Fi speed
  (flagged). Its quality report (correlation with the stopwatch on each held-out session) comes first.
- **P2, tracker speed (ON and OFF, at Uzayr's word):** only if Second Overall's inventory shows held-out tracker outputs;
  defined in a dated note once the inventory is known, before it is scored.
- **A1, dense offsets:** training windows at every 0.05 s from 0.05 to 0.50 s after the press (supersedes F7's 0.15 and
  0.30), same labels.
- **A3, speed-scale features:** training windows' frames rescaled in time by 0.9 and 1.1 (features recomputed by the
  engine's extract_window; the pace column divided by the factor).
- **A4, test-time augmentation:** the ensemble log-probabilities averaged (then normalised) over the test windows at 0,
  0.15 and 0.30 s, every window classified against the same CAL-causal pool of earlier walks (offset-0 windows only enter
  the pool); the CNN components of the offset windows from the shipped CNNs (GPU cache).
- **A5, cross-day mixup:** for each training row, one extra row mixing its standardised features with a random row of the
  same person, same route, from another training day (weight drawn uniformly from 0.2 to 0.8, seed 0), in every feature
  component's normalised space.
- **M2, weights by walk type:** the feature components' weight against the CNN components (0, 0.5, 1 or 2) chosen
  separately for path walks and identification walks on last night's development folds (A1, A2, B1); applied to models
  whose test session is A3 or B2; a loso model tested on A1, A2 or B1 keeps v4's weights (choosing them there would use the
  test day's labels; flagged).
- **M3, a sixth feature component:** sklearn HistGradientBoostingClassifier (random_state 0, defaults) on the
  Prior-standardised 630 columns and the pace column, added to the ensemble.
- **GPU, on last night's development folds first:** A2 (a random time stretch with matching frequency scaling of each CNN
  training window, factor uniform in 0.85 to 1.15, in augment's place), M1 (CNNs trained on bank_T4.0_v4's 4.0 s maps),
  A2+M1. Each scored with F7's feature components; only those beating v4+F7's development score (29.59) go to the full
  scorecard (nine models), each requested from the Mastermind.

## 3. The build

Each candidate is scored alone (v4 plus the candidate) and the winner is built greedily from F7: at each step add the
candidate that raises (Z + D) / 2 most while the guard holds; stop when none raises it. The path is reported.

## 4. The report

`reports/identification/2026-10-10_best-model.md`, headed "For Mastermind's review. Exploratory, nothing adopted.", with
this file's section 0 at its top, every configuration scored, the looks, and a ship plan written but not built.

## Notes

(Dated notes go below this line.)

- **10 Oct 2026, 08:26:46 SAST: Uzayr's confirmation, relayed by the Mastermind.** Uzayr answered the Mastermind
  directly "Yes" to this run selecting on A3 and B2, as exploration only; he also asked me directly for P2 to be tried
  both ON and OFF. The Mastermind's conditions: this file committed and pushed before any score, with the four statements
  of section 0; block 2 (CPU) and the GPU A4 cache may run in parallel (one GPU job at a time); the full-scorecard GPU
  runs are requested one by one with their development score against v4+F7's; P2 waits for Second Overall's inventory (a
  new tracker decode would be a separate decision); every look (model x session x configuration) counted as it happens
  and reported with each block's end.

- **10 Oct 2026, 08:38:17 SAST: P2 defined (before any P2 score), with the Mastermind's decision and label addition.** The Mastermind's
  decision (relayed with Second Overall's read-only inventory): P2 from the EXISTING tracker logs only, using only frames
  available by the identification decision time; no new decode (requested only if P2 proves worth extending).
  - **Definition** (`pipeline/identify/ilb_p2.py`): for each path walk, the tracker log's press row matched to the bank by
    press time; the latest lock with `at` by the bank's identification decision time `t_dec`; the dot frames with
    frame time `x` after the lock's `t_dec0` (the anchor's end) and `computed_at` by `t_dec`; each frame's distance
    along the locked line (projection onto the line in `idgp_contract.PATHS`); P2 = the least-squares slope of that
    distance against frame time. Fewer than 5 such frames, no lock by `t_dec`, or a slope outside 0.5 to 2.5 m/s: the
    walk keeps the Wi-Fi speed of the model's alpha (counted). Identification walks keep the Wi-Fi speed. Extra training
    rows (F7, A1 offsets, A3 stretches) take their source walk's P2 value (A3: divided by the factor).
  - **Sources** (no tracker trained on its walk's session): A1, A2, B1 from
    `runs/a3_clean_2026-10-08/dot/stage1/multi/h-heldout_f0.5_o0.375_s0.5_sw-off_sd3_soft1/` (A1's tracker on A2+B1, A2's on
    A1+B1, B1's on A1+A2); A3 from `runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/03__*` (f05_A3: A1+A2+B1);
    B2 from the same directory's `B2__*` (f05_B2: A1+A2+B1; its dots and locks are identical to the non-screen run's on
    all six recordings, checked), except for xr_A, whose B2 comes from the zero-shot tracker
    `runs/live/replay/zeroshot/semi_disp-K1g_causal/B2__*` (z05_B2: A1+A2). Not used: `runs/live/replay/rot*/`, `dot/p1/`.
  - **Caveats (Second Overall's, as relayed):** (a) the drawn path is a Viterbi under the pace prior N(1.30, 0.11), so its
    speed shrinks towards 1.30, and part of it is the motion model (substitution 0.80 pooled, 0.66 held-out DISP_END);
    (b) timing: park until press + 2.0, the anchor until t_dec0 = press + 2.625 (shipped), and a frame at x shows scene
    time x - 2.0. So by press + 4.0 s the logged dot covers only scene press + 0.625 to press + 2.0, about 1.4 s of
    walking; (c) the A1/A2/B1 source's display settings differ slightly from A3/B2's (spread 3.0 and switching off
    against 4.5 and arm C).
  - **Labels (the Mastermind's addition):** P2 brings each tracker's training sessions into the identification model's
    features. Every P2 cell states the sessions its trackers trained on; xr_A's and xr_B1's P2 cells are labelled "not
    zero-shot: the tracker saw <sessions>" (xr_A: its A1 and A2 rows' trackers include B1, its A3 tracker A1+A2+B1; xr_B1:
    its B1 rows' tracker A1+A2, its A3 tracker A1+A2+B1). xr_AB and xr_ABtrk are consistent (trackers on A1+A2+B1).
  - **ON and OFF (Uzayr's toggle):** OFF is every configuration without P2 (the greedy build runs with P2 OFF); ON is P2
    alone and P2 added to the OFF winner, both scored and reported beside OFF.
  - **The speed check came first** (`runs/identify/best/p2_quality.json`, 08:36:54, the stopwatch only, no
    identification score): Pearson r of P2 with the press speed on the walks it covers: A1 0.06, A2 -0.08, B1 0.09, A3
    0.24, B2 0.10, B2 (zero-shot tracker) 0.24, against the Wi-Fi speed's 0.16, 0.24, 0.49, 0.23, 0.11, 0.14 on the same
    walks; P2's median 1.32 to 1.54 m/s against the press speed's 1.25 to 1.30; walks keeping the Wi-Fi speed 6, 4, 18,
    2, 6 and 22 of 120. P2 is a weak speed; it is scored at Uzayr's word, not because the check favours it.

- **10 Oct 2026, 08:44:59 SAST: mechanics fixed before any score (no candidate scored yet).**
  - **The greedy build's rounds:** round 1 (F7 plus each CPU candidate: A1, A3, A4, A5, P1, M2, M3; A1 replaces F7's
    offsets) runs with the singles; `ilb_core next` then compares each round's configurations by (Z + D) / 2 (point
    estimates) with the guard, adds the best that raises the current score, and queues the next round, until none raises
    it. A round waits for A4's GPU cache; if the cache fails, A4 is dropped from the build (logged). P2 is OFF in the build
    and added to the winner afterwards (P2 ON). A GPU candidate (A2, M1, A2M1) enters only if it passes the development
    screen and its full scorecard is granted; it is then tried as an addition to the build's current configuration.
  - **A2's wording "in augment's place" means at the augmentation step:** each training window is stretched (factor s ~
    U(0.85, 1.15) per window, about its centre, frequency axis scaled by s: new(f, t) = old(f / s, c + (t - c) s),
    bilinear, zeros outside), and then augment's own time and frequency masks, gain, link drop and noise are applied as in
    v4; nothing of augment is removed.
  - **The CPU share from 09:45 (the Mastermind):** every block-2 CPU step takes a slot (`slot.sh`: at most 6 before
    09:45, 2 from 09:45); a step holding a slot runs to its end. QUIET is not written while a
    runs/clean_display_2026-10-10 process is alive (`ms_b.py`).

- **10 Oct 2026, 09:07:47 SAST: the CPU share changed (the Mastermind).** Second Overall's replays started early: from now this run holds
  at most 3 CPU processes (slot.sh cap 3), plus the GPU queue; block 1's unstarted test-window extractions (tta) now take
  slots too. Nothing else changes.

- **10 Oct 2026, 11:00:48 SAST: A2M1 made conditional (the Mastermind's decision, before any A2 or M1 development result).** This
  changes the prompt's candidate list to save about 2 GPU-hours (block B measured about 40 min per fold for A2, not 20).
  Decided by the Mastermind under its authority from Uzayr ("make the best decisions you can"); Uzayr can override.
  When this note was written no A2 or M1 fold had finished training (no development result existed). The rule: after A2
  and M1 are trained and scored on D1 to D3, a screen (`ilb_gpu gate`) computes each with F7's feature components; A2M1
  runs only if A2 or M1 alone beats v4+F7's development score (DS point value above 29.59) with the development guard
  holding (B1 natural, slow and fast each no more than 5 points below v4's development value). If A2M1 is skipped, the
  report lists it under "not run, and why", with A2's and M1's DS and their paired intervals.

- **10 Oct 2026, 11:03:00 SAST: Uzayr confirms the A2M1 gate (2249b743), relayed by the Mastermind:** "don't run it regardless. Mastermind's rule is sound ... If A2 or M1 passes, the pair runs anyway." No change to the queue.
