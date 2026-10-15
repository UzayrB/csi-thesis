# PREREG_C: identification, the shortlist singly and combined, against v4 (exploratory, adopt nothing)

Written 10 Oct 2026, 07:59:26 SAST by the Third overall chat, from Uzayr's prompt (received at about 07:45 on 10 Oct). Committed before
any look at A3 or B2. **Exploratory development, all data seen. Nothing is adopted; engine v4 stays shipped** (shipping
anything else needs Uzayr's decision and its own brief).

## 0. Why this outer test exists, plainly

Last night's committed PREREG_LP (5996218f) said there is no outer test unless a configuration clears v4's development
score by 3 points; nothing did (48 configurations; the best +2.50), so **PREREG_LP's rule produced no outer test**. This
outer test is run **at Uzayr's new instruction, given after the development null was known**: his prompt of 10 Oct
(about 07:45), and his answer "Yes" to the Mastermind's question "test the shortlist on A3 and B2 anyway?" (relayed at
about 07:5x). No A3 or B2 file is scored before this file is committed and pushed and v4's reproduction (C4) has passed;
an interlock file, `C5_GO`, gates every score. The results are read in that light.

## 1. The contract (PREREG_LP's, unchanged)

Start press only; nothing labelled from the test day; adaptation only from CAL-causal's pool; nothing that uses the order
people walk in; speed only as one gait parameter; existing data only; slow and fast reported wherever they exist.

## 2. The shortlist (fixed by the prompt) and the development stage (done before this file)

F3 = F3_shrink_k160; F7 = F7_offset_augmentation; CNN = H3_cnn_only (stands alone); NP = H3_drop_pace; F4 =
F4_icc_top200; F5 = F5a_drop_mod. On last night's development folds, scorer and DS (A1, A2, B1 only;
`runs/identify/combine/dev.json`):

| configuration | DS | minus v4 | A1 path | A2 path | B1 path | B1 natural | B1 slow | B1 fast | guard |
|---|---|---|---|---|---|---|---|---|---|
| v4 | 27.50 |  | 30.83 | 28.33 | 16.67 | 34.17 | 15.00 | 21.67 |  |
| F3 | 30.00 | +2.50 | 30.83 | 25.00 | 24.17 | 40.00 | 18.33 | 21.67 | holds |
| F3+F7 | 30.00 | +2.50 | 30.00 | 27.50 | 21.67 | 40.83 | 25.00 | 26.67 | holds |
| F7 | 29.59 | +2.09 | 27.50 | 32.50 | 19.17 | 39.17 | 23.33 | 23.33 | holds |
| F3+F4 | 29.59 | +2.09 | 34.17 | 30.00 | 22.50 | 31.67 | 18.33 | 18.33 | holds |
| F7+F4 | 29.38 | +1.88 | 33.33 | 30.83 | 19.17 | 34.17 | 15.00 | 25.00 | holds |
| NP+F5 | 29.17 | +1.67 | 29.17 | 28.33 | 24.17 | 35.00 | 20.00 | 21.67 | holds |
| F7+NP | 29.16 | +1.66 | 30.00 | 28.33 | 23.33 | 35.00 | 18.33 | 23.33 | holds |
| NP | 28.96 | +1.46 | 29.17 | 28.33 | 24.17 | 34.17 | 20.00 | 21.67 | holds |
| F4 | 28.75 | +1.25 | 34.17 | 29.17 | 21.67 | 30.00 | 16.67 | 20.00 | holds |
| F5 | 28.75 | +1.25 | 29.17 | 30.00 | 21.67 | 34.17 | 18.33 | 21.67 | holds |
| F3+NP | 28.75 | +1.25 | 28.33 | 28.33 | 24.17 | 34.17 | 20.00 | 21.67 | holds |
| F3+F5 | 28.75 | +1.25 | 30.00 | 26.67 | 23.33 | 35.00 | 16.67 | 20.00 | holds |
| NP+F4 | 28.75 | +1.25 | 30.00 | 26.67 | 23.33 | 35.00 | 20.00 | 21.67 | holds |
| F3+F7+NP+F4+F5 | 28.34 | +0.84 | 29.17 | 25.83 | 24.17 | 34.17 | 20.00 | 21.67 | holds |
| F7+F5 | 27.09 | -0.41 | 25.00 | 32.50 | 19.17 | 31.67 | 18.33 | 16.67 | holds |
| F4+F5 | 27.08 | -0.42 | 28.33 | 28.33 | 21.67 | 30.00 | 16.67 | 20.00 | holds |

Greedy path: step 1, the best single F3 (DS 30.00); step 2, the best addition F7 gives 30.00, not higher, so the path stops. The five singles recomputed equal last night's exactly; 16 configurations scored today (5 singles, 10 pairs, the stack). (The prompt said three of the ten pairs were scored last night; only F3+F7 was among these five, and it reproduces 30.00. The other two scored pairs involved H3_cnn_only.)

**The primary configuration (the greedy result): F3 (F3_shrink_k160 alone).** The full stack is F3+F7+NP+F4+F5, DS 28.34, which differs from the primary.

## 3. The outer test (held until confirmed)

- **Configurations (at most nine):** v4, the six singles, the primary, and the stack if it differs: v4, F3 (the primary), F7, CNN, NP, F4, F5, and the stack F3+F7+NP+F4+F5.
  **7 configurations besides v4.**
- **Models:** loso_A1 to loso_B2 (every walk of the other four sessions), xr_AB (A1+A2+B1, 600), xr_ABtrk (360), xr_A
  (240), xr_B1 (360); for each configuration the five feature components are retrained with its change on the model's own
  rows, cfg, seeds and speed column (loso_B1's alpha 0.2); the CNN components are the shipped replays' own (reused).
  F7's offset windows come from `ilc_extract` (every session, both alphas). F4 cannot run on one training day (xr_B1): its
  change is dropped there, and the table flags it.
- **Before any configuration is scored:** v4 recomputed through this path must reproduce every v4 figure below exactly
  (C4); otherwise the outer test is BLOCKED.

## 4. The scorecard (every configuration, every row: the score, v4, S0, the paired difference against v4 with its
interval and `ixr_eval`'s labels)

| group | cell | v4 |
|---|---|---|
| zero-shot | xr_A to B2 path walks | 23.33 |
| zero-shot | xr_A to B2 natural | 23.33 |
| zero-shot | xr_B1 to A3 path walks | 30.00 |
| cross-day | loso, natural identification walks, 180 (B1 / B2) | 37.78 (41.67 / 30.00), S0 38.33 |
| cross-day | loso, path walks, 600 (A2) | 30.67 (35.83), S0 30.17 |
| cross-day | xr_AB to A3 path walks | 30.00 |
| cross-day | xr_AB to B2 path walks / natural | 22.50 / 25.00 |
| cross-day | xr_A to A3 path walks | 23.33 |
| cross-day | xr_B1 to B2 path walks / natural | 22.50 / 28.33 |
| cross-day | xr_ABtrk to A3 / B2 path walks | 25.00 / 30.83 |
| guard | loso, slow / fast | 29.17 / 30.25, S0 17.50 / 16.81 |
| ranking | top-2 / household of two, natural 180 | 62.78 / 72.33 |

Also xr_A to B2 slow and fast. S0: xr cells and loso path walks as `ixr_eval` (an LDA on press speed trained on the
model's own rows); loso identification walks as `eval_v4` (trained on the other Room B day's identification walks), which
is how the v4 figures above were made. Intervals: participant bootstrap, 10,000 draws, seed 0.

## 5. The verdict (fixed now)

- **Z** = the equal-weight mean of the three zero-shot cells; **D** = the equal-weight mean of the ten cross-day cells;
  their differences against v4 with a paired participant bootstrap (10,000 draws, seed 0, the six participants resampled
  jointly across cells), as last night's DS intervals.
- **BETTER:** Z and D both above v4 with paired lower bounds above 0, and loso natural, slow and fast each no more than 5
  points below v4.
- **HIGHER, NOT SEPARABLE:** Z and D both above v4 on point estimates, with the same guard.
- **NOT BETTER:** anything else.
- **Only the primary's verdict is confirmatory.** Every other configuration's verdict carries "chosen on A3 and B2, N
  configurations tried" (N = 7).

## 6. Looks

Every configuration scored on A3 and B2 counts as looks on both sessions (its five zero-shot and cross-day xr cells and
the loso folds), all on 10 Oct, listed in the report. No rerun, no extra configuration, no setting change after any look.

## Notes

(Dated notes go below this line.)
