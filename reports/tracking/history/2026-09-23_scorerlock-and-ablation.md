# The ablation and the scorer lock. Batch 2026-09-23g, items 1 to 3

Stages `g1_ablation` and `g2_scorerlock`, both VALID. Nine cross-day pairings, 1080 walks, the ONE
lattice. **Nothing ships from this file; nothing in the model changed.**

## 1. The ablation (diagnostic): what makes the display lock disagree with the scorer?

The display lock disagrees with the final-answer scorer at the lock on 363 of 1080 walks. The
operator's three candidates were removed one at a time from the display decode the lock is read from,
then all together. The `shipped` variant reproduces the drawn lock (`d6_lock_commit`) on 1080 of 1080.

| variant | lock right (of 1080) | lock median, nine / held-out seven [95%] | paired against shipped, all nine | locks changed | **disagree with the scorer** | edge walks E_col1 / E_col5 / E_row1 / E_row5 |
|---|---|---|---|---|---|---|
| shipped | 493 | 53.33 / 53.33 [26.67, 62.50] | | | **363 (33.6%)** | 20 / 32 / 10 / 23 |
| no speed cap | 485 | 50.00 / 50.00 [25.83, 63.33] | -0.74 [-2.04, 0.56] | 119 | **353 (32.7%)** | 20 / 36 / 15 / 27 |
| no display head | 493 | 53.33 / 53.33 | 0 | **0** | **363 (33.6%)** | 20 / 32 / 10 / 23 |
| with the veto term | 493 | 53.33 / 53.33 | 0 | **0** | **363 (33.6%)** | 20 / 32 / 10 / 23 |
| all three removed | 485 | 50.00 / 50.00 | -0.74 [-2.04, 0.56] | 119 | **353 (32.7%)** | 20 / 36 / 15 / 27 |
| (the scorer, for reference) | 538 | | | | | 19 / 32 / 13 / 22 |

**None of the three explains the disagreement.** Removing all three leaves 353 of the 363.

- **The speed cap** accounts for 10 disagreements. Removing it changes 119 locks, costs 8 pooled
  (-0.74 paired, interval spanning zero) and moves 13 edge walks the right way (E_col5 +4, E_row1 +5,
  E_row5 +4).
- **The display head** changes no lock, as the code predicts: it feeds only the path drawn AFTER the
  lock, never the lock line.
- **The veto term** changes no lock. Not a vacuous variant: every pass carries veto terms (a median of
  7 to 9.5 lines vetoed per pass), and the display lock was never on a vetoed line.
- **The disagreement is the two estimators' STRUCTURE**: the display lock is the best state of a
  Viterbi over the full state space, with transition costs and the null and exit states; the scorer
  sums each line's emissions along its own restricted path, without transition costs. That structure
  was not ablated; it is what the scorer-lock arm below mixes.

## 2. The scorer lock: REFUSED

Pre-registered in `reports/PREREG_scorerlock_2026-09-23.md` before the stage existed. **Not a clean
test: its lead was observed on all nine pairings, held-out folds included, in `e2_switch`; DC2 would be
its confirmatory test.** Reproductions exact: at w = 0 the arm is the drawn lock on 1080 of 1080; the
scorer's argmax equals `e2_switch`'s on 1080 of 1080.

| w | lock right | median, nine / held-out | paired, all nine | held-out paired [95%] | held-out median passes | selection delta | edge change (E_col1 / E_col5 / E_row1 / E_row5) |
|---|---|---|---|---|---|---|---|
| 0 (shipped) | 493 | 53.33 / 53.33 | | | | | |
| **0.25 (chosen)** | **541** | 57.50 / 57.50 | **+4.44 [2.59, 6.57]** | **+5.12 [2.98, 7.74]** | **5** | +2.08 | -1 / +1 / 0 / +1 (net +1) |
| 0.5 | 542 | 56.67 / 56.67 | +4.54 [1.76, 8.06] | +5.83 [2.85, 9.76] | 6 | 0.00 | -1 / 0 / 0 / +3 (net +2) |
| 0.75 | 544 | 57.50 / 58.33 | +4.72 [1.85, 8.70] | +6.07 [2.98, 10.48] | 6 | 0.00 | -1 / -1 / 0 / +2 (net 0) |
| 1.0 | 538 | 57.50 / 58.33 | +4.17 [0.93, 8.33] | +5.83 [2.74, 10.24] | 5 | -1.67 | -1 / 0 / +3 / -1 (net +1) |

The selection folds chose **w = 0.25**. The full rule at w = 0.25:

| condition | result |
|---|---|
| (a) held-out paired interval above zero | **pass**, [2.98, 7.74] |
| (b) at least two passes per pairing | **pass**, median 5 |
| (c) as clarified, non-flat, chosen w positive | **pass**, 5 / 6 / 6 / 5 |
| both causal bounds | **pass**: the lock reads the shipped lock's own windows (the same +2.5 us lattice offset); the drawn path -1.250 s on both bounds |
| (f) as amended | **pass**, net +1, no line below -1 |
| continuity | **pass**: 0 rule violations, 0 anchor frames off segment; 272 frame jumps after the lock against the shipped 303 |
| **substitution** | **FAIL: 0.38, the bar is 0.5** (the lock changes on 34% of the 115 held-out walks where the arm differs, against a ceiling of 88%) |

**It does not ship, so nothing changes**: no render, no new lock, no switching re-choice.

**Reading the substitution failure, as an interpretation and not a re-test.** The pre-registered test
(`y3_switch`'s definition) swaps the scorer's WALK emissions for another participant's and keeps the
start term, which comes from the pass's own pre-press radio. Over the lock's three windows that start
term weighs heavily, so on most walks where the arm changes the lock, it is the pre-press reader, not
the walk's first seconds of radio, that tips it. The rule was fixed before the numbers and is not
relaxed after them.

## 3. What this leaves for DC2

The DC2 lock is the display lock, unchanged (PREREG_DC2 section 12). The +4 to +5 points a scorer lock
shows on Room A remain a lead that is not clean and failed substitution; if the operator wants it
tested, it would be a pre-registered EXPLORATORY display comparison on DC2 data, which does not touch
any DC2 outcome because the lock is not one.
