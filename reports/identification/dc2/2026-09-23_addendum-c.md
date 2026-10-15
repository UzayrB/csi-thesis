# Pre-registration addendum C: DC2 identification, P1-GP

**Written on 2026-09-23 at 20:10 SAST, read from the clock.** No DC2 data existed at the time of
writing: `data/room_B` did not exist. Its SHA-256 is recorded in
`runs/IDENTIFICATION_FROZEN_2026-09-23f.json`, which references the 23e freeze and supersedes
nothing. The original pre-registration and addendum B are unchanged, and every analysis they define
(P1 to P6) stands exactly as frozen. This addendum ADDS one arm, P1-GP, and the rows scored with it.

The scorer is `pipeline/identify/idgp_dc2_score.py`. It refuses to run unless the pre-registration
and addendum B match the 23e freeze and this addendum matches the 23f freeze. `id29_dc2_score.py` is
not edited; the new scorer imports its discovery, layout check, clock map and statistics.

## 1. Where the arm comes from

The arm was chosen on Room A by the exploratory IDGP run (brief 2026-09-23f; decision 11 in
`reports/DECISIONS_ID_2026-09-23.md`; results in `reports/IDENTIFICATION_2026-09-18.md`, section
"2026-09-23f"). The rule was fixed in `reports/QUEUE_IDGP.md` at 19:47, before any run:

- the frozen arm is the pace arm the nested procedure preferred most often across the three
  leave-one-session-out folds, among the pace arms that beat speed alone (integrity check 1: the
  paired difference against S0 on the same A_fwd passes has its 95 percent interval above zero);
- if no pace arm passes check 1, the arm without pace, G, is frozen.

**No pace arm passed check 1 on Room A.** The best, GP plus the CNN embedding, tied S0 at 36.11
percent (difference 0.0, interval -22.29 to 25.0, n = 36). **The frozen arm is therefore G**,
gait without pace, which scored 22.22 percent on Room A (interval 8.33 to 41.67). GPu, the variant
with CSI-sensed speed, is not frozen, because CSI-sensed speed failed its validation on Room A
(correlation with pace from the presses 0.05, against the 0.8 rule).

## 2. The identification contract

P1-GP uses exactly what DC2 gives identification, and nothing else:

1. the CSI of the three receivers between the walk's start press (the 0 m mark) and its end press
   (the 5 m mark);
2. those two press times;
3. the path, `A_fwd` ((2.5, 0) to (2.5, 5), heading N, away from the TX), its length (5.0 m), and the
   rig, with RX2 at the identification spot recorded in `runs/identify/dc2/rx2_spot.json`.

The intermediate presses (1 to 4 m), any interpolated position, any other label, and everything
the tracking branch produces are never read. Each pass is built as an `idgp_contract.ContractPass`;
`tests/test_idgp_contract.py` enforces the field set and that no tracking module is loaded.

## 3. P1-GP, frozen

- **Features** (`idgp_signal.pass_features`, per pass, from the ContractPass):
  - the pass-level rhythm at the fused cadence: cadence, stride time, cadence variability and the
    step-to-stride autocorrelation ratio;
  - for each link, its rhythm at the fused cadence;
  - the geometry-corrected Doppler contour shapes (the `cor` form, using the recorded RX2 spot);
  - the envelope spectral shape.

  No pace, step length, walk ratio or speed-adjusted cadence enters, because G has none.
- **Cadence margin:** 0 or 0.5 s either side of the presses, chosen by the person ICC of the fused
  cadence on day 1's natural passes, never by accuracy.
- **Head:** gradient boosting (`HistGradientBoostingClassifier`, 150 iterations, learning rate 0.05,
  depth 3, `random_state` 0), on the concatenated features after training-side median imputation and
  z-scoring.
  - **How it was chosen.** The three Room A folds each chose a different G configuration. This one
    won the tie on inner accuracy (45.83 percent), so Room A does not favour it over the other two.
  - **Scope.** DC2 walks only A_fwd, so the model trains on A_fwd passes by necessity.
- **Training:** DC2 day 1 natural passes (10 per person). No Room A model or statistic transfers,
  because RX2 has moved.

## 4. Rows, each scored exactly once

The statistics are as addendum B's: accuracy, n, chance 16.67 percent, a 95 percent bootstrap over
participants (1000 draws), and a permutation p that permutes identities over participants within the
test day (1000 draws).

- **P1-GP.** Train on day 1 natural, test on day 2 natural (5 per person, n = 30). S0 (pace from the
  presses, 5.0 m over the press interval, shrinkage LDA) is scored on the same passes.
- **Integrity check 1.** P1-GP minus S0 on the same passes, with a bootstrap over participants. It
  PASSES only if the interval lies above zero.
- **Integrity check 2.** Report the share of P1-GP's gain over chance that S0 accounts for,
  (S0 - 16.67) / (P1-GP - 16.67). P1-GP has no pace input, so its speed-only row is S0 and its
  speed-removed row is P1-GP itself.
- **Integrity check 3, the speed-overlap test.** Take the d' of pace between every pair of
  participants on day 1, and the third of pairs with the lowest d'. On those pairs, refit P1-GP and
  S0 on the pair's day 1 natural passes and score both on the pair's day 2 natural passes (chance
  50).
- **Integrity check 4, the name.**
  - If check 1 passes: "gait without pace, above speed".
  - Otherwise: "gait without pace, not above speed".
  - The wording "identification from Wi-Fi-sensed spatio-temporal gait parameters, of which pace is
    one" is NOT available to this arm, because it has no pace input.
- **The pace blocks.** P1-GP and S0, trained as in P1, are scored on day 2 slow and day 2 fast. The
  drops are addendum B's participant-level drops, natural minus pace.
  - **The reading, fixed now:**
    - NOT DECIDABLE if S0's drop interval does not lie above zero on both blocks;
    - GAIT-CONSISTENT if P1-GP minus S0 on the slow and fast passes pooled (n = 60) has its interval
      above zero AND P1-GP's own drop interval contains zero on both blocks;
    - KEEPS MORE THAN S0, BUT DROPS if only the first condition holds;
    - NOT SHOWN otherwise.
  - **Why this replaces the brief's reading.** The brief's reading, that a pace arm loses some
    accuracy on the pace blocks and counts as integrated gait only if it keeps more than S0, was
    written for an arm with pace as an input. The frozen arm has none, so it is expected not to drop
    at all.
- **MULTI-PASS.** For each day 2 block (natural, slow, fast) and each participant, sum the
  log-probabilities over the block's 5 passes into one decision (6 per block), for P1-GP and for S0.
  It is labelled "identification from several walks". The single-pass row stays the result.

## 5. Stated expectation, so it cannot be reinterpreted later

- **P1-GP.** Room A gave the frozen arm 22.22 percent against S0's 36.11 on A_fwd, and on the lowest-d'
  pairs it was at chance (51.67 against 50). With 30 test passes, the half-width is about 15 points.
  **P1-GP is not expected to beat S0 on day 2 natural.**
- **The pace blocks.** If S0 drops there and P1-GP holds its level, that is the only way this arm
  can show that it reads something other than pace. That result would be GAIT-CONSISTENT, and it
  would still not be integrated gait.

## 6. The identification path, checked

`pipeline/constrained/paths.py`, sheet 23d, the field card, `capture_idpath.py` and addendum B all
define A_fwd identically: (2.5, 0) to (2.5, 5), heading N, away from the TX. The walker starts at the
0 m mark beside the TX and stops before RX1. **No correction was needed.**

F for the moved RX2, by `id15_factor_map.py`, is identical in both walking directions, because F is
the magnitude of the projection:

| RX2 spot | TX-RX2 mean F (min) | TX-RX3 | TX-RX1 |
|---|---|---|---|
| primary (2.0, -0.5) | 0.981 (0.854) | 0.500 (0.180) | 0.000 |
| fallback (1.5, -0.5) | 0.947 (0.724) | 0.500 (0.180) | 0.000 |
