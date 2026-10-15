# Brief: identification lever screen (1 October 2026, evening)

## Goal

Find which changes to the identification engine (engine v2, 35.56 % [21.11, 52.78] on the 180 natural identification walks) could move it towards 50 %, **quickly and cheaply**, before we spend time on full retrains. This is a screen, not a final evaluation: test many levers at the lowest cost that can tell us whether each one helps, rank them, and stop. I will choose which levers to take deeper from your table.

Write a PLAN note before you run anything (the levers below, the order, the promise rule), and commit it.

## Rules that do not change

- One model, and it is the live app: one start press, a 3 s window, no end press, no press-timed walk time, nothing from tracking's output, no warm-up, only unlabelled same-day adaptation, no new data, names not codes.
- Improving on the test days (B1, B2) is allowed; label everything "development evaluation, all data seen".
- Screening numbers are exploratory. Any lever I adopt must be built into `pipeline/identify/engine.py`, re-run through the replay, and re-verified against the app (n of n equal) before any figure counts for the thesis.
- Bugs are fixed and adopted whatever their effect, as with the cadence fix.

## How to score every lever (the same for all)

- **Primary:** natural identification walks, both folds (n 180), causal calibration, paired against engine v2 on the same walks, with the participant-bootstrap 95 % interval (10,000 resamples, seed 0).
- **Always report beside it:**
  - to B1 and to B2 separately;
  - how many walks are named PA1 (engine v2: 63 of 180);
  - PA2's accuracy (engine v2: 3 of 30);
  - per-person accuracy;
  - the runtime.
- **Noise floor first.** Before any lever, score each of the three CNN seeds' components on their own from the saved models (inference only), and the feature components with two other `random_state` values (seconds each). Report the seed-to-seed spread of the natural accuracy. A lever is only interesting if it beats that spread.
- **Promise rule** (write it in the PLAN note before running):
  - a paired gain of at least +3 points on natural walks;
  - positive on both to B1 and to B2;
  - larger than the seed spread;
  - and not raising the number of walks named PA1.
  
  Mark each lever PROMISING, FLAT or WORSE by that rule.

## Tier 0: bug checks and diagnostics (no training; do these first)

1. **The calibration pool (most important).** For an identification walk, list exactly which earlier windows feed (a) the session feature standardisation and (b) the AdaBN statistics. The B2 replay has 299 windows (179 identification, 120 tracking); PA4's walk 1 used 151 earlier windows.
   - Does the pool include tracking walks, recorded with RX2 at its home position (−0.5, 2.5), when the identification walks have RX2 beside the TX at (2.0, −0.5)?
   - Is it split by path or layout?
   - If it mixes layouts, that is a bug: fix it so identification walks calibrate only on identification-layout windows, re-score, and report the change.
2. **The cadence fallback.** The v2 fix lets only channels with an autocorrelation peak ≥ 0.30 vote, but if none qualifies every channel votes as before (the v1 behaviour).
   - On what fraction of the 180 natural walks does the fallback fire?
   - On those walks, does the resolved step rate sit near the doubled band-edge value that caused the bug?
   - If the fallback reproduces the bug on real walks, propose the fix (for example: return "no rhythm" and let the cadence-scaled features fall back to unscaled versions), and treat it as a bug fix.
3. **Per-component diagnosis.** Score each of the eight components alone on the natural walks, from the saved replays. For each, report:
   - accuracy;
   - how many walks it names PA1;
   - the per-class confusion matrix;
   - its mean log-probability spread (max minus min per walk);
   - its mean negative log-likelihood of the true class.
   
   I want to know which component creates the lean towards PA1, and which components dominate the sum because their probabilities are sharp. On the two worked walks the spreads were: per-link CNN 10.7 to 12.3, LDA 8.9 to 10.1, 3-link CNNs 2.6 to 4.4, tree models 0.3 to 0.9.
4. **Per-link diagnosis.** Score the per-link CNN component one receiver at a time (inference only): RX1 alone, RX2 alone, RX3 alone.
   - On line A, RX1 has F = 0 (no walking Doppler) but sits on the TX–RX1 line of sight the walker blocks, so it may carry shadowing rather than gait.
   - Report each link's accuracy and PA1 count.
5. **Packet gaps (minor).** How often a 50 ms bin with no packets on all three receivers falls inside a 3 s window, and how the resampler fills it. Report only; do not change anything yet.

## Tier 1: re-fusion of the saved replays (no training; minutes)

The replays already hold every component's six log-probabilities for every walk, so these cost nothing to test:

1. **Leave one component out:** the sum without each of the eight in turn.
2. **Calibrate before summing:** fit one temperature per component (scale its log-probabilities, then renormalise) by minimising the true-class negative log-likelihood. Cross-fit it so no walk is scored with a temperature fitted on its own fold: fit on the to-B1 walks and apply to B2, and the reverse.
3. **Fusion rules:**
   - the mean of probabilities instead of the sum of log-probabilities;
   - the sum within each family (features, CNNs), each family's sum normalised, then the two families added with equal weight;
   - the sum of rank or z-scored log-probabilities per component.
4. **Link subsets in fusion:** using the Tier 0 per-link scores, the per-link component as RX2 only, RX2 + RX3, and all three.
5. **Session bias correction (unlabelled, causal):** subtract from each class's summed log-probability its running mean over the session's earlier walks, so a class the session keeps choosing is pulled back.
   - This targets the PA1 lean, but it quietly assumes everyone walks equally often, which is true in our evaluation and not guaranteed in a home.
   - Report it, and flag that assumption beside the number.

## Tier 2: cheap retrains of the feature components only (seconds each)

The five feature components retrain in about 6 to 10 s per model, so test all of these on both folds:

1. **Link subsets for the 630 features:** RX2 columns only (209 + the step-rate columns), RX2 + RX3, all three.
2. **Replace or regularise the LDA:**
   - stronger fixed shrinkage (0.7, 0.9);
   - logistic regression with strong L2 instead of the LDA;
   - the LDA removed.
   
   Report the PA1 count for each.
3. **Matched training data:** the training walks that share the test layout are only the other B day's identification walks (40 per person). Try:
   - weighting them ×2 and ×4 against Room A and tracking passes;
   - training the feature components on identification-layout walks only.
4. **Drop the fragile families:** without `rhy` and `tplacf`, the families that hang on the step rate (on one walk, a step-rate change altered 448 of 630 features); and with only `dop`, `spec`, `wav` and `mod`.
5. **Standardisation variants:** session statistics from identification-layout windows only (if Tier 0.1 shows mixing), per path, and none.

## Tier 3: CNN retrains (only for what Tiers 0 to 2 point to)

Do **not** start these until I have seen the Tier 0 to 2 table. One seed first, both folds, using the noise floor to judge. Candidates, in priority order:

1. the CNN components trained with the matched-data weighting from Tier 2.3, if it was promising on the features;
2. the per-link CNN retrained without RX1, or a 1-link RX2 CNN, if Tier 0.4 shows RX1 at chance;
3. **domain-adversarial training (DANN):** a gradient-reversal head predicting the session from the 3-link CNN's pooled 896 features, trained alongside the identity head.
   - This is the thesis's stated research angle (cross-environment generalisation), so I want one honest test of it even if the gain is small.
   - Use Ganin et al. (`1505.07818`): the λ schedule from the paper, sessions as domains.

## What to give me

1. **One table**, every lever as a row, sorted by paired gain. Columns:
   - tier and lever;
   - natural accuracy;
   - paired change [95 % interval];
   - to B1; to B2;
   - walks named PA1; PA2;
   - PROMISING, FLAT or WORSE;
   - runtime.
2. **The bug findings from Tier 0** stated plainly, with any fix adopted and its effect.
3. **The best combination** of PROMISING levers that are compatible, scored once together.
   - Say how far it gets towards 50 %.
   - Say whether the gains add up or overlap.
4. **Your recommendation:**
   - which one to three levers deserve a full build (all seeds, both folds, the leave-one-session-out tracking walks, then into the engine and the app with n of n verification);
   - which to drop.
5. A short report, `reports/ID_LEVER_SCREEN_2026-10-01.md`, with the table and the PLAN note's promise rule quoted.

## Time

- Tiers 0 to 2 should take hours, not days, because nothing in them trains a CNN.
- Stop after Tier 2 and report.
- If nothing in Tiers 0 to 2 is PROMISING, say so plainly; that is a result too.
