# Identification: building the best model (2026-10-10)

**For Mastermind's review. Exploratory, nothing adopted.** Exploratory development, all data seen. Engine v4 stays shipped until Uzayr decides.

- **Selection is on A3 and B2.** Every candidate and every greedy step is chosen on this morning's combine scorecard, which is built from A3 and B2.
- **Every scored configuration is a look at A3 and B2 and is counted** (35 configurations in this run; section 8).
- **Nothing in this run is confirmatory.** The winner is selected on the data it is scored on, so its figures are optimistic by an amount this run cannot estimate.
- **No figure from this run may be reported as a held-out or generalisation result.** A generalisation claim for the winner needs data it was never chosen on (new sessions).

Brief: Uzayr's prompt of 10 Oct (about 08:22) and his message asking for P2 ON and OFF. Plan: `runs/identify/best/POA_B.md` (b7e8aa25 and dated notes). Generated 10 Oct 2026 14:05:20 SAST by `ilb_report`.

## 1. Verdict

1. **The build's winner (greedy from F7, P2 OFF): A1+A3+A4+A5+M3** = A1 (dense offsets 0.05 to 0.50 s in training) + A3 (time-stretched training windows, 0.9 and 1.1) + A4 (test-time average over 0, 0.15, 0.30 s) + A5 (cross-day mixup) + M3 (gradient-boosted sixth component).
   Z 33.89, D 31.40, (Z + D) / 2 = **32.64** against v4's 26.57 (+6.07 [-0.03, +11.53]) and F7's 29.17 (+3.48 [-2.27, +9.46]). Against v4: Z +8.33 [-0.83, +17.22], D +3.81 [+0.67, +6.77]; the guard holds; by this morning's labels **HIGHER, NOT SEPARABLE** (chosen on A3 and B2, 35 configurations tried: exploratory, optimistic).
   Against F7: Z +6.67 [-2.78, +16.40], D +0.29 [-4.18, +4.52]. **Its advantage over this morning's F7 is entirely zero-shot**: D is level (+0.29), and the Z gain rests on three cells (360 walks) that the build was chosen on.
   **It is not better everywhere:** xr_A A3 path 16.67 (v4 23.33, F7 32.50; minus v4 -6.67 [-17.50, +3.33], minus F7 -15.83 [-24.17, -7.50]); loso B2 fast 27.12 (v4 37.29, F7 35.59; minus v4 -10.17 [-15.00, -5.08], minus F7 -8.47 [-18.33, -1.67]) (section 4).
2. **P2 ON (Uzayr's toggle) on the winner, A1+A3+A4+A5+M3+P2:** (Z + D) / 2 = 31.56 against OFF's 32.64 (Z 32.50, D 30.61; guard holds). P2 alone (v4 + P2): 26.68. P2's cells for xr_A and xr_B1 are not zero-shot (the tracker saw A1, A2 and B1).
3. **Nothing is adopted; v4 stays shipped.** Shipping the winner needs Uzayr's decision and its own brief (section 7 is the plan, written, not built).

## 2. The scorecard, every configuration

(Z + D) / 2 with Z the mean of the three zero-shot cells and D of the ten cross-day cells; intervals: paired participant bootstrap (10,000 draws, seed 0, participants resampled jointly across cells). Guard: loso natural, slow and fast each no more than 5 points below v4. 'Against v4' uses this morning's labels (BETTER needs both Z and D lower bounds above 0). v4 and F7 are this morning's files; F7 was reproduced exactly by this run's scorer.

| configuration | Z | D | (Z + D) / 2 | minus v4 [95 %] | minus F7 [95 %] | guard | against v4 |
|---|---|---|---|---|---|---|---|
| A1+A3+A4+A5+M3 | 33.89 | 31.40 | 32.64 | +6.07 [-0.03, +11.53] | +3.48 [-2.27, +9.46] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+M3 | 33.61 | 31.58 | 32.60 | +6.02 [-0.35, +11.80] | +3.43 [-2.43, +9.51] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+P1+M3 | 32.22 | 31.27 | 31.75 | +5.17 [-0.23, +10.23] | +2.58 [-2.56, +8.35] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+A5+P1+M3 | 32.22 | 30.94 | 31.58 | +5.01 [-0.94, +10.37] | +2.41 [-3.20, +8.08] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+A5+M3+P2 | 32.50 | 30.61 | 31.56 | +4.98 [-0.95, +10.38] | +2.39 [-3.37, +8.44] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4 | 30.56 | 32.27 | 31.41 | +4.84 [+0.47, +8.73] | +2.24 [-1.62, +6.44] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+P1 | 30.56 | 32.11 | 31.33 | +4.76 [+0.28, +8.88] | +2.16 [-1.60, +6.62] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+A5 | 30.56 | 31.69 | 31.12 | +4.55 [+0.15, +8.57] | +1.96 [-1.82, +5.64] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A4+A5 | 29.17 | 32.91 | 31.04 | +4.46 [+1.07, +7.21] | +1.87 [-1.12, +4.84] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A4+P1 | 28.89 | 32.73 | 30.81 | +4.24 [+0.88, +7.52] | +1.64 [-1.32, +5.14] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A4 | 28.61 | 32.60 | 30.61 | +4.03 [+0.75, +7.29] | +1.44 [-1.48, +4.91] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A4+M3 | 30.00 | 31.12 | 30.56 | +3.99 [-1.10, +8.28] | +1.39 [-3.06, +5.55] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+M3 | 29.44 | 31.19 | 30.32 | +3.74 [-0.63, +7.32] | +1.15 [-2.06, +4.21] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+P1 | 28.89 | 31.08 | 29.99 | +3.41 [+1.18, +5.66] | +0.82 [-1.07, +2.64] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A5 | 28.06 | 31.59 | 29.82 | +3.25 [+1.02, +5.51] | +0.66 [-1.17, +2.71] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+M2+M3 | 30.00 | 29.48 | 29.74 | +3.16 [-1.60, +7.67] | +0.57 [-3.27, +3.99] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+A5+M2+M3 | 30.00 | 29.43 | 29.72 | +3.14 [-1.49, +7.57] | +0.55 [-3.14, +3.89] | holds | HIGHER, NOT SEPARABLE |
| F7+A4 | 26.94 | 32.35 | 29.65 | +3.07 [+0.00, +5.47] | +0.48 [-1.63, +2.66] | FAILS | NOT BETTER |
| F7+A3 | 28.33 | 30.76 | 29.54 | +2.97 [+0.78, +5.25] | +0.38 [-1.42, +2.02] | holds | HIGHER, NOT SEPARABLE |
| F7+P1 | 27.78 | 31.25 | 29.51 | +2.94 [+0.79, +5.39] | +0.35 [-0.21, +1.24] | holds | HIGHER, NOT SEPARABLE |
| A1+A3 | 28.89 | 29.71 | 29.30 | +2.73 [-0.86, +6.68] | +0.13 [-2.83, +4.08] | holds | HIGHER, NOT SEPARABLE |
| A1 | 28.33 | 30.12 | 29.23 | +2.65 [-0.76, +6.45] | +0.06 [-2.54, +3.78] | holds | HIGHER, NOT SEPARABLE |
| F7 | 27.22 | 31.11 | 29.17 | +2.59 [+0.64, +5.12] | +0.00 [+0.00, +0.00] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+A4+M2 | 28.33 | 29.81 | 29.07 | +2.49 [-1.81, +6.87] | -0.10 [-3.65, +3.54] | holds | HIGHER, NOT SEPARABLE |
| A1+A3+A4+M2 | 28.33 | 29.52 | 28.93 | +2.35 [-1.97, +6.79] | -0.24 [-3.86, +3.50] | FAILS | NOT BETTER |
| A3 | 26.94 | 30.35 | 28.65 | +2.07 [-0.77, +4.57] | -0.52 [-3.09, +1.88] | holds | HIGHER, NOT SEPARABLE |
| F7+M3 | 26.67 | 30.27 | 28.47 | +1.89 [-1.36, +4.89] | -0.70 [-2.65, +1.25] | holds | HIGHER, NOT SEPARABLE |
| A4 | 26.11 | 30.10 | 28.11 | +1.53 [-0.49, +3.19] | -1.06 [-3.15, +0.62] | holds | HIGHER, NOT SEPARABLE |
| F7+A5 | 25.83 | 30.36 | 28.09 | +1.52 [-0.23, +3.77] | -1.07 [-1.78, -0.44] | holds | HIGHER, NOT SEPARABLE |
| F7+M2 | 25.83 | 29.18 | 27.51 | +0.93 [-3.21, +5.32] | -1.66 [-5.06, +1.54] | holds | HIGHER, NOT SEPARABLE |
| F7+A3+M2 | 25.28 | 28.94 | 27.11 | +0.53 [-3.55, +4.72] | -2.06 [-5.39, +1.34] | holds | NOT BETTER |
| M2 | 24.17 | 29.43 | 26.80 | +0.22 [-3.62, +4.11] | -2.37 [-5.49, +1.04] | holds | NOT BETTER |
| P1 | 25.00 | 28.57 | 26.78 | +0.21 [-0.38, +0.75] | -2.38 [-4.67, -0.51] | holds | NOT BETTER |
| P2 | 24.72 | 28.64 | 26.68 | +0.11 [-0.50, +0.71] | -2.49 [-5.23, -0.51] | holds | NOT BETTER |
| v4 | 25.56 | 27.59 | 26.57 | +0.00 [+0.00, +0.00] | -2.59 [-5.12, -0.64] | holds | reference |
| M3 | 25.56 | 27.36 | 26.46 | -0.12 [-2.22, +2.59] | -2.71 [-5.08, -0.26] | holds | NOT BETTER |
| A5 | 22.50 | 27.64 | 25.07 | -1.51 [-3.28, -0.05] | -4.10 [-6.96, -1.59] | holds | NOT BETTER |

Where a candidate could not apply (the configurations' flags, condensed):

- A5: xr_B1 has one training day, so no partner and no mixed rows (every configuration with A5).
- P1: xr_B1 has one training session, so P1 cannot be cross-fitted by session and keeps the Wi-Fi speed.
- M2: not applied on loso_A1, loso_A2 and loso_B1 (tested on development sessions; choosing weights there would use the test day's labels); elsewhere feature weight 0.0 on path walks, 0.5 on identification walks.
- P2: every model's trackers below; xr_A's and xr_B1's P2 cells are **not zero-shot: the tracker saw A1, A2, B1**.

| model | trackers behind its training rows' P2 | trackers behind its test sessions' P2 |
|---|---|---|
| loso_A1_v4 | {A2: [A1, B1], A3: [A1, A2, B1], B1: [A1, A2], B2: [A1, A2, B1]} | {A1: {[A2, B1]}} |
| loso_A2_v4 | {A1: [A2, B1], A3: [A1, A2, B1], B1: [A1, A2], B2: [A1, A2, B1]} | {A2: {[A1, B1]}} |
| loso_A3_v4 | {A1: [A2, B1], A2: [A1, B1], B1: [A1, A2], B2: [A1, A2, B1]} | {A3: {[A1, A2, B1]}} |
| loso_B1_v4 | {A1: [A2, B1], A2: [A1, B1], A3: [A1, A2, B1], B2: [A1, A2, B1]} | {B1: {[A1, A2]}} |
| loso_B2_v4 | {A1: [A2, B1], A2: [A1, B1], A3: [A1, A2, B1], B1: [A1, A2]} | {B2: {[A1, A2, B1]}} |
| xr_AB_v4 | {A1: [A2, B1], A2: [A1, B1], B1: [A1, A2]} | {A3: {[A1, A2, B1]}, B2: {[A1, A2, B1]}} |
| xr_ABtrk_v4 | {A1: [A2, B1], A2: [A1, B1], B1: [A1, A2]} | {A3: {[A1, A2, B1]}, B2: {[A1, A2, B1]}} |
| xr_A_v4 | {A1: [A2, B1], A2: [A1, B1]} | {A3: {[A1, A2, B1]}, B2: {[A1, A2]}} |
| xr_B1_v4 | {B1: [A1, A2]} | {A3: {[A1, A2, B1]}, B2: {[A1, A2, B1]}} |

Path walks keeping the Wi-Fi speed under P2: 36 (52 for xr_A, whose B2 comes from the zero-shot tracker).

## 3. The greedy path

- Round 1 from **F7** (29.17; Z 27.22, D 31.11): F7+A4 29.65 (guard FAILS), F7+A3 29.54, F7+P1 29.51, A1 29.23, F7+M3 28.47, F7+A5 28.09, F7+M2 27.51. Chosen: **A3** (F7+A3: Z +1.11, D -0.35; score +0.38).
- Round 2 from **F7+A3** (29.54; Z 28.33, D 30.76): F7+A3+A4 30.61, F7+A3+M3 30.32, F7+A3+P1 29.99, F7+A3+A5 29.82, A1+A3 29.30, F7+A3+M2 27.11. Chosen: **A4** (F7+A3+A4: Z +0.28, D +1.84; score +1.06).
- Round 3 from **F7+A3+A4** (30.61; Z 28.61, D 32.60): A1+A3+A4 31.41, F7+A3+A4+A5 31.04, F7+A3+A4+P1 30.81, F7+A3+A4+M3 30.56, F7+A3+A4+M2 29.07. Chosen: **A1** (A1+A3+A4: Z +1.95, D -0.33; score +0.81).
- Round 4 from **A1+A3+A4** (31.41; Z 30.56, D 32.27): A1+A3+A4+M3 32.60, A1+A3+A4+P1 31.33, A1+A3+A4+A5 31.12, A1+A3+A4+M2 28.93 (guard FAILS). Chosen: **M3** (A1+A3+A4+M3: Z +3.05, D -0.69; score +1.19).
- Round 5 from **A1+A3+A4+M3** (32.60; Z 33.61, D 31.58): A1+A3+A4+A5+M3 32.64, A1+A3+A4+P1+M3 31.75, A1+A3+A4+M2+M3 29.74. Chosen: **A5** (A1+A3+A4+A5+M3: Z +0.28, D -0.18; score +0.05; **a gain of about one walk in one cell, noise: the rule adds anything that raises the score**).
- Round 6 from **A1+A3+A4+A5+M3** (32.64; Z 33.89, D 31.40): A1+A3+A4+A5+P1+M3 31.58, A1+A3+A4+A5+M2+M3 29.72. None raises it: the build stops.

**M3's step is a zero-shot gain only.** Adding M3 in round 4 raised Z by +3.05 (the three zero-shot cells: 360 walks, 120 per cell) while D moved -0.69; the score rose because Z rose. Like every step here it was selected on A3 and B2 (35 configurations looked at), so it is exploratory and optimistic.

## 4. The winner's figures (A1+A3+A4+A5+M3), every cell with v4, F7 and S0

S0: xr cells and loso path walks as `ixr_eval` (an LDA on press speed trained on the model's own rows); loso identification walks as `eval_v4` (trained on the other Room B day's identification walks). Tracking's split is the xr_AB rows (trained on A1, A2, B1; tested on A3 and B2) and xr_ABtrk.

| cell | walks | this configuration [95 %] | v4 | F7 | S0 | minus v4 [95 %] | minus F7 [95 %] |
|---|---|---|---|---|---|---|---|
| xr_A B2 path | 120 | 28.33 [10.00, 47.50] | 23.33 | 23.33 | 20.83 | +5.00 [-5.83, +18.33] not separable | +5.00 [-4.17, +18.33] |
| xr_A B2 natural | 60 | 40.00 [15.00, 66.67] | 23.33 | 26.67 | 23.33 | +16.67 [+1.67, +31.67] separable gain | +13.33 [+0.00, +28.33] |
| xr_B1 A3 path | 120 | 33.33 [22.50, 45.00] | 30.00 | 31.67 | 44.17 | +3.33 [-3.33, +9.17] not separable | +1.67 [-5.83, +9.17] |
| loso all natural | 180 | 40.00 [26.67, 53.33] | 37.78 | 37.78 | 38.33 | +2.22 [-3.33, +7.78] not separable | +2.22 [-5.00, +8.33] |
| loso all path | 600 | 30.67 [20.67, 39.50] | 30.67 | 29.17 | 30.17 | +0.00 [-4.33, +4.17] not separable | +1.50 [-2.83, +5.67] |
| xr_AB A3 path | 120 | 33.33 [20.00, 48.33] | 30.00 | 34.17 | 42.50 | +3.33 [-2.50, +10.83] not separable | -0.83 [-6.67, +8.33] |
| xr_AB B2 path | 120 | 31.67 [17.50, 49.17] | 22.50 | 31.67 | 23.33 | +9.17 [+0.83, +15.83] separable gain | +0.00 [-9.17, +8.33] |
| xr_AB B2 natural | 60 | 33.33 [10.00, 60.04] | 25.00 | 30.00 | 25.00 | +8.33 [+1.67, +15.00] separable gain | +3.33 [-16.67, +21.67] |
| xr_A A3 path | 120 | 16.67 [10.00, 25.00] | 23.33 | 32.50 | 38.33 | -6.67 [-17.50, +3.33] not separable | -15.83 [-24.17, -7.50] |
| xr_B1 B2 path | 120 | 33.33 [21.67, 40.00] | 22.50 | 30.00 | 35.00 | +10.83 [+3.33, +18.33] separable gain | +3.33 [-4.17, +11.67] |
| xr_B1 B2 natural | 60 | 35.00 [15.00, 55.00] | 28.33 | 25.00 | 30.00 | +6.67 [-6.67, +23.33] not separable | +10.00 [-6.67, +28.33] |
| xr_ABtrk A3 path | 120 | 22.50 [15.00, 30.00] | 25.00 | 24.17 | 39.17 | -2.50 [-10.83, +5.00] not separable | -1.67 [-5.83, +2.50] |
| xr_ABtrk B2 path | 120 | 37.50 [25.83, 51.67] | 30.83 | 36.67 | 20.83 | +6.67 [-0.83, +14.17] not separable | +0.83 [+0.00, +2.50] |
| loso all slow | 120 | 35.00 [9.17, 63.33] | 29.17 | 29.17 | 17.50 | +5.83 [-11.67, +24.17] not separable | +5.83 [-6.67, +20.00] |
| loso all fast | 119 | 28.57 [20.17, 36.97] | 30.25 | 31.09 | 16.81 | -1.68 [-6.72, +5.88] not separable | -2.52 [-8.47, +4.17] |
| xr_A B2 slow | 60 | 33.33 [10.00, 63.33] | 18.33 | 30.00 | 16.67 | +15.00 [-1.67, +38.33] not separable | +3.33 [-16.67, +21.67] |
| xr_A B2 fast | 59 | 32.20 [8.47, 57.63] | 33.90 | 28.81 | 20.34 | -1.69 [-11.67, +7.02] not separable | +3.39 [-3.33, +12.28] |
| loso B1 natural | 120 | 39.17 [25.00, 52.50] | 41.67 | 36.67 | 42.50 | -2.50 [-10.83, +7.50] not separable | +2.50 [-5.83, +10.83] |
| loso B2 natural | 60 | 41.67 [15.00, 70.00] | 30.00 | 40.00 | 30.00 | +11.67 [+0.00, +23.33] not separable | +1.67 [-13.33, +16.67] |
| loso B1 slow | 60 | 31.67 [6.67, 58.33] | 31.67 | 28.33 | 18.33 | +0.00 [-21.67, +18.33] not separable | +3.33 [-13.33, +20.00] |
| loso B2 slow | 60 | 38.33 [8.33, 71.67] | 26.67 | 30.00 | 16.67 | +11.67 [-3.33, +36.67] not separable | +8.33 [+0.00, +25.00] |
| loso B1 fast | 60 | 30.00 [16.67, 41.67] | 23.33 | 26.67 | 16.67 | +6.67 [-3.33, +16.67] not separable | +3.33 [-5.00, +11.67] |
| loso B2 fast | 59 | 27.12 [14.29, 38.33] | 37.29 | 35.59 | 16.95 | -10.17 [-15.00, -5.08] separable cost | -8.47 [-18.33, -1.67] |
| loso A1 path | 120 | 27.50 [12.48, 42.50] | 30.83 | 27.50 | 13.33 | -3.33 [-8.33, +3.33] not separable | +0.00 [-4.17, +6.67] |
| loso A2 path | 120 | 35.83 [21.67, 46.67] | 35.83 | 34.17 | 24.17 | +0.00 [-10.83, +12.50] not separable | +1.67 [-5.00, +10.00] |
| loso A3 path | 120 | 30.83 [16.67, 46.67] | 30.83 | 30.00 | 48.33 | +0.00 [-13.33, +10.83] not separable | +0.83 [-10.00, +12.50] |
| loso B1 path | 120 | 25.00 [14.17, 37.50] | 24.17 | 25.00 | 41.67 | +0.83 [-7.50, +9.17] not separable | +0.00 [-8.33, +8.33] |
| loso B2 path | 120 | 34.17 [22.50, 48.33] | 31.67 | 29.17 | 23.33 | +2.50 [-7.50, +10.00] not separable | +5.00 [-1.67, +10.83] |
| top-2 (loso natural) | 180 | 61.67 [40.00, 80.00] | 62.78 |  | 67.78 | -1.11 [-10.56, +9.44] not separable |  |
| household of two (loso natural) | 180 | 75.89 [66.56, 84.78] | 72.33 |  | 76.78 | +3.56 [-0.00, +7.44] not separable |  |

**What the cells show.** Separable gains against v4: xr_A B2 natural (40.00), xr_AB B2 path (31.67), xr_AB B2 natural (33.33), xr_B1 B2 path (33.33). Separable costs against v4: loso B2 fast (27.12). Separable costs against F7: xr_A A3 path (16.67), loso B2 fast (27.12). The pooled guard holds (loso natural, slow and fast), but a pooled figure hides the per-day cells above. Speed alone (S0, the stopwatch's press speed: a speed oracle the engine does not have) is above the winner on: xr_B1 A3 path (33.33), xr_AB A3 path (33.33), xr_A A3 path (16.67), xr_B1 B2 path (33.33), xr_ABtrk A3 path (22.50), loso B1 natural (39.17), loso A3 path (30.83), loso B1 path (25.00); identification beyond speed stays weak on those cells.

P2 ON (A1+A3+A4+A5+M3+P2), same cells:

| cell | walks | this configuration [95 %] | v4 | F7 | S0 | minus v4 [95 %] | minus F7 [95 %] |
|---|---|---|---|---|---|---|---|
| xr_A B2 path | 120 | 28.33 [10.00, 47.50] | 23.33 | 23.33 | 20.83 | +5.00 [-5.83, +18.33] not separable | +5.00 [-4.17, +18.33] |
| xr_A B2 natural | 60 | 36.67 [10.00, 63.33] | 23.33 | 26.67 | 23.33 | +13.33 [-3.33, +28.33] not separable | +10.00 [-3.33, +23.33] |
| xr_B1 A3 path | 120 | 32.50 [19.17, 46.67] | 30.00 | 31.67 | 44.17 | +2.50 [-3.33, +9.17] not separable | +0.83 [-5.00, +7.50] |
| loso all natural | 180 | 37.78 [23.89, 51.11] | 37.78 | 37.78 | 38.33 | +0.00 [-5.00, +5.56] not separable | +0.00 [-7.22, +6.11] |
| loso all path | 600 | 30.83 [21.83, 40.50] | 30.67 | 29.17 | 30.17 | +0.17 [-3.17, +3.33] not separable | +1.67 [-2.00, +6.17] |
| xr_AB A3 path | 120 | 35.00 [23.33, 47.50] | 30.00 | 34.17 | 42.50 | +5.00 [-2.50, +12.50] not separable | +0.83 [-7.50, +10.00] |
| xr_AB B2 path | 120 | 30.00 [15.00, 48.33] | 22.50 | 31.67 | 23.33 | +7.50 [-0.83, +15.00] not separable | -1.67 [-10.00, +5.83] |
| xr_AB B2 natural | 60 | 33.33 [8.33, 61.67] | 25.00 | 30.00 | 25.00 | +8.33 [+3.33, +13.33] separable gain | +3.33 [-16.67, +21.67] |
| xr_A A3 path | 120 | 16.67 [10.00, 25.00] | 23.33 | 32.50 | 38.33 | -6.67 [-17.50, +3.33] not separable | -15.83 [-24.17, -7.50] |
| xr_B1 B2 path | 120 | 28.33 [15.83, 38.33] | 22.50 | 30.00 | 35.00 | +5.83 [-1.67, +15.00] not separable | -1.67 [-9.17, +8.33] |
| xr_B1 B2 natural | 60 | 35.00 [15.00, 55.00] | 28.33 | 25.00 | 30.00 | +6.67 [-6.67, +23.33] not separable | +10.00 [-6.67, +28.33] |
| xr_ABtrk A3 path | 120 | 20.83 [14.17, 28.33] | 25.00 | 24.17 | 39.17 | -4.17 [-12.50, +3.33] not separable | -3.33 [-8.33, +1.67] |
| xr_ABtrk B2 path | 120 | 38.33 [27.50, 54.17] | 30.83 | 36.67 | 20.83 | +7.50 [+0.00, +15.00] not separable | +1.67 [-5.00, +8.33] |
| loso all slow | 120 | 34.17 [7.50, 61.67] | 29.17 | 29.17 | 17.50 | +5.00 [-13.33, +25.83] not separable | +5.00 [-6.67, +20.00] |
| loso all fast | 119 | 27.73 [19.49, 36.67] | 30.25 | 31.09 | 16.81 | -2.52 [-6.72, +3.36] not separable | -3.36 [-8.47, +2.50] |
| xr_A B2 slow | 60 | 33.33 [10.00, 63.33] | 18.33 | 30.00 | 16.67 | +15.00 [-1.67, +38.33] not separable | +3.33 [-16.67, +21.67] |
| xr_A B2 fast | 59 | 30.51 [5.08, 57.63] | 33.90 | 28.81 | 20.34 | -3.39 [-16.67, +7.02] not separable | +1.69 [-6.67, +10.53] |
| loso B1 natural | 120 | 36.67 [21.67, 51.67] | 41.67 | 36.67 | 42.50 | -5.00 [-14.17, +5.83] not separable | +0.00 [-10.00, +9.17] |
| loso B2 natural | 60 | 40.00 [15.00, 68.33] | 30.00 | 40.00 | 30.00 | +10.00 [+0.00, +20.00] not separable | +0.00 [-13.33, +11.67] |
| loso B1 slow | 60 | 30.00 [5.00, 55.04] | 31.67 | 28.33 | 18.33 | -1.67 [-23.33, +16.67] not separable | +1.67 [-15.00, +16.67] |
| loso B2 slow | 60 | 38.33 [8.33, 71.67] | 26.67 | 30.00 | 16.67 | +11.67 [-3.33, +36.67] not separable | +8.33 [+0.00, +25.00] |
| loso B1 fast | 60 | 30.00 [16.67, 41.67] | 23.33 | 26.67 | 16.67 | +6.67 [-3.33, +16.67] not separable | +3.33 [-5.00, +11.67] |
| loso B2 fast | 59 | 25.42 [12.28, 36.67] | 37.29 | 35.59 | 16.95 | -11.86 [-15.25, -10.00] separable cost | -10.17 [-18.64, -3.33] |
| loso A1 path | 120 | 27.50 [12.50, 42.50] | 30.83 | 27.50 | 13.33 | -3.33 [-8.33, +2.50] not separable | +0.00 [-4.17, +5.00] |
| loso A2 path | 120 | 34.17 [21.65, 44.17] | 35.83 | 34.17 | 24.17 | -1.67 [-10.83, +9.17] not separable | +0.00 [-5.83, +6.67] |
| loso A3 path | 120 | 37.50 [22.50, 55.00] | 30.83 | 30.00 | 48.33 | +6.67 [-5.83, +19.17] not separable | +7.50 [-3.33, +20.00] |
| loso B1 path | 120 | 23.33 [14.17, 35.00] | 24.17 | 25.00 | 41.67 | -0.83 [-8.33, +5.83] not separable | -1.67 [-9.17, +5.83] |
| loso B2 path | 120 | 31.67 [20.00, 48.33] | 31.67 | 29.17 | 23.33 | +0.00 [-9.17, +8.33] not separable | +2.50 [-4.17, +9.17] |
| top-2 (loso natural) | 180 | 60.00 [39.44, 78.33] | 62.78 |  | 67.78 | -2.78 [-11.11, +6.67] not separable |  |
| household of two (loso natural) | 180 | 75.22 [65.44, 84.00] | 72.33 |  | 76.78 | +2.89 [-0.78, +6.44] not separable |  |

## 5. The speed checks (the stopwatch only; no identification score)

| session | P1 r | Wi-Fi r | P1 median abs error (m/s) | Wi-Fi median abs error |
|---|---|---|---|---|
| A1 | 0.531 | 0.164 | 0.066 | 0.194 |
| A2 | 0.453 | 0.219 | 0.079 | 0.259 |
| A3 | 0.613 | 0.231 | 0.087 | 0.221 |
| B1 | 0.241 | 0.424 | 0.093 | 0.512 |
| B2 | 0.383 | 0.144 | 0.096 | 0.499 |

P2 (POA_B's note of 08:38; tracker sessions in brackets):

| source | walks with P2 | P2 r | Wi-Fi r (same walks) | P2 median | press median |
|---|---|---|---|---|---|
| A1 (A2+B1) | 114 of 120 | 0.061 | 0.161 | 1.535 | 1.298 |
| A2 (A1+B1) | 116 of 120 | -0.079 | 0.241 | 1.539 | 1.278 |
| B1 (A1+A2) | 102 of 120 | 0.09 | 0.488 | 1.391 | 1.244 |
| A3 (A1+A2+B1) | 118 of 120 | 0.242 | 0.228 | 1.535 | 1.286 |
| B2 (A1+A2+B1) | 114 of 120 | 0.101 | 0.113 | 1.538 | 1.251 |
| B2z (A1+A2) | 98 of 120 | 0.241 | 0.144 | 1.318 | 1.251 |

P2's caveats (Second Overall's, as relayed): (a) the drawn path is a Viterbi under the pace prior N(1.30, 0.11), so its speed shrinks towards 1.30, and part of it is the motion model; (b) by press + 4.0 s the logged dot covers only about 1.4 s of walking; (c) the A1/A2/B1 source's display settings differ slightly from A3/B2's.
M2's weights (development folds): feature components 0.0 on path walks, 0.5 on identification walks (CNN weight 1); applied only to models tested on A3 or B2.

## 6. The GPU candidates on the development folds (A1, A2, B1; no A3 or B2)

| configuration | A1 path | A2 path | B1 path | B1 natural | B1 slow | B1 fast | DS | DS minus v4+F7 [95 %] | passes |
|---|---|---|---|---|---|---|---|---|---|
| v4 | 30.83 | 28.33 | 16.67 | 34.17 | 15.0 | 21.67 | 27.5 |  |  |
| v4+F7 | 27.5 | 32.5 | 19.17 | 39.17 | 23.33 | 23.33 | 29.59 |  |  |
| A2+F7 | 24.17 | 30.83 | 17.5 | 29.17 | 23.33 | 31.67 | 25.42 | -4.17 [-8.96, +0.83] | False |
| M1+F7 | 25.83 | 28.33 | 18.33 | 36.67 | 13.33 | 20.0 | 27.29 | -2.29 [-4.79, +0.42] | False |

**Not run, and why: A2M1.** The Mastermind's rule (POA_B, 11:00, confirmed by Uzayr 11:03): A2M1 runs only if A2 or M1 alone beats v4+F7's development score (29.59) with the development guard; neither did (A2+F7 DS 25.42, M1+F7 DS 27.29; intervals above).

## 7. The ship plan (engine v5; written, not built)

Only if Uzayr decides to ship, and under its own brief. **Engine v5 = v4 + A1, A3, A4, A5, M3**, same CAL-causal pools, same contract (start press only; nothing labelled from the test day; adaptation only from CAL-causal's pool; nothing that uses the order people walk in).

1. **A1 (dense offsets 0.05 to 0.50 s in training)**: training only: the dense offsets 0.05 to 0.50 s (`ilb_extract dense` and `ilc_extract`), appended as F7's; run time unchanged.
2. **A3 (time-stretched training windows, 0.9 and 1.1)**: training only: each training walk's frames rescaled in time by 0.9 and 1.1 (`ilb_extract stretch`, the engine's own `extract_window`), appended with pace v / s; run time unchanged.
3. **A4 (test-time average over 0, 0.15, 0.30 s)**: run time: the engine classifies three windows per press (0, 0.15 and 0.30 s after it) against the same CAL-causal pool and averages the ensembles; only the 0 s window enters the pool. The decision comes 0.30 s later and the CNN work triples; `Engine`/`Extractor` need a second and third poll per press.
4. **A5 (cross-day mixup)**: training only: one mixed row per training row (same person, same route, another day, weight U(0.2, 0.8), seed 0) in each component's normalised space; run time unchanged.
5. **M3 (gradient-boosted sixth component)**: training and run time: a sixth feature component (HistGradientBoosting on the Prior-standardised columns and pace) saved with the model; `Model` and `Session.classify` loop over six feature components.

Build order: (1) the extractions for every training walk of every shipped model (offsets, stretches) through the engine's own `Extractor`, anchors exact; (2) retrain the feature components (six with M3) of the nine scorecard models and the live model, the CNNs unchanged; (3) the run-time changes in `engine.py` behind a version switch, with a null check that v5 with every change off reproduces v4's replays exactly; (4) replay every session through v5 and regenerate every identification figure; (5) the live app's timing budget measured on the rig before adoption (A4 triples the CNN work per press and delays the decision 0.30 s); (6) nothing to the Editor until Uzayr approves the figures. Not built in this run.

## 8. Configurations tried and looks at A3 and B2

35 configurations, each scored on all nine models: 5 model-session looks at A3 (xr_AB, xr_ABtrk, xr_A, xr_B1, loso_A3) and 5 at B2 (the same xr models, loso_B2): **175 model-session looks at A3 and 175 at B2**, all on 10 Oct, all exploratory. The F7 reproduction (identical to this morning's F7) is not a new look. The GPU candidates were screened on the development folds only (A1, A2, B1): no A3 or B2 look.

| # | configuration | scored at |
|---|---|---|
| 1 | M2 | 09:43:52 |
| 2 | A5 | 09:45:19 |
| 3 | M3 | 09:46:39 |
| 4 | F7+M3 | 09:57:20 |
| 5 | F7+A3 | 09:58:01 |
| 6 | P1 | 10:00:02 |
| 7 | F7+P1 | 10:04:50 |
| 8 | F7+M2 | 10:07:56 |
| 9 | P2 | 10:09:31 |
| 10 | A1 | 10:12:46 |
| 11 | A3 | 10:17:05 |
| 12 | F7+A5 | 10:19:59 |
| 13 | A4 | 10:34:23 |
| 14 | F7+A4 | 10:38:32 |
| 15 | F7+A3+A5 | 10:59:10 |
| 16 | F7+A3+A4 | 11:01:26 |
| 17 | F7+A3+P1 | 11:11:24 |
| 18 | F7+A3+M2 | 11:12:40 |
| 19 | A1+A3 | 11:17:12 |
| 20 | F7+A3+M3 | 11:25:40 |
| 21 | F7+A3+A4+P1 | 11:40:09 |
| 22 | F7+A3+A4+A5 | 11:41:31 |
| 23 | F7+A3+A4+M2 | 11:53:18 |
| 24 | A1+A3+A4 | 11:59:04 |
| 25 | F7+A3+A4+M3 | 11:59:57 |
| 26 | A1+A3+A4+M2 | 12:25:09 |
| 27 | A1+A3+A4+P1 | 12:25:11 |
| 28 | A1+A3+A4+A5 | 12:26:03 |
| 29 | A1+A3+A4+M3 | 12:46:45 |
| 30 | A1+A3+A4+M2+M3 | 13:17:06 |
| 31 | A1+A3+A4+P1+M3 | 13:17:09 |
| 32 | A1+A3+A4+A5+M3 | 13:17:42 |
| 33 | A1+A3+A4+A5+M2+M3 | 13:41:16 |
| 34 | A1+A3+A4+A5+P1+M3 | 13:41:17 |
| 35 | A1+A3+A4+A5+M3+P2 | 14:03:01 |

## 9. Files, commits and timings

- Code: `pipeline/identify/ilb_extract.py`, `ilb_p1.py`, `ilb_p2.py`, `ilb_core.py`, `ilb_gpu.py`, `ilb_report.py`.
- Plan and queue: `runs/identify/best/POA_B.md`, `QUEUE_B.md`, `STEPS_CPU1`, `STEPS_GPU`, the driver `run_b.sh`, `slot.sh`, `ms_b.py`.
- Results: `runs/identify/best/scorecard.json` and `scorecard.md` (every configuration, every cell), `greedy.json`, `looks.json`, `p1_quality.json`, `p2_quality.json`, `m2_weights.json`, `dev/gpu_dev.json`, `dev/gate.json`, `checks/f7_reproduction.json`, `outer/<configuration>.npz` and `.json` (log-probabilities, flags), `a4cache/` (the A4 CNN components; offset 0 equal to every replay).
- Not committed (size): `extract/` (106 MB of windows), `models/` (214 MB of development-fold CNNs).

Commits (this run):

- e0aeee75 08:25:01 Identification best model (exploratory development, all data seen): block 1 extraction code (ilb_extract: A1 dense offsets, A3 time-stretched 
- b7e8aa25 08:25:42 Identification best model: POA_B committed before any scoring (selection on A3 and B2; every scored configuration a counted look; nothing conf
- 529b6ffd 08:26:46 Identification best model: POA_B dated note (Uzayr's 'Yes' relayed by the Mastermind, his P2 ON/OFF instruction, the Mastermind's conditions);
- 5ba3731e 08:42:24 Identification best model: P2 defined in a dated POA_B note before any P2 score (existing tracker logs only, frames by the identification deci
- a696e3ab 08:44:59 Identification best model: POA_B dated note (the greedy rounds, A2's augmentation step, the CPU share from 09:45) before any score; ilb_gpu A2
- b3000713 08:46:03 Identification best model: QUEUE_B states; GPU block B queued
- 879b66c1 08:46:24 Identification best model: the GPU screen reports DS(candidate) - DS(v4+F7) with paired participant intervals (the Mastermind's condition); po
- 79c5363c 08:46:45 Identification best model: report started (status only, no scores)
- 5b207d0d 08:48:03 Identification best model: the summary gives every cell with v4, F7 and S0 (per-session loso cells added), the ranking with S0, the verdict ag
- 6ffc6e69 09:07:47 Identification best model: CPU cap 3 from now (the Mastermind: Second Overall started early); block 1's unstarted tta steps take slots
- be126ad4 09:08:26 Identification best model: ms_b.py's QUIET guard widened (the Mastermind): no QUIET while any process's command line contains runs/clean_displ
- 695c86f3 09:33:26 Identification best model: block 1 done (09:32), P1's speed check (closer to the stopwatch than Wi-Fi except B1's r); report and QUEUE_B updat
- 07ada5a4 09:33:42 Identification best model: report status (formatting; block A's memory wait, kept by the Mastermind)
- 7e6bf8b7 10:27:00 Identification best model: ilb_p2 flag text prints session names plainly (cosmetic; no number changes)
- d182bb13 10:41:38 Identification best model: greedy round 1 (14 configurations, A3 chosen; F7+A4 fails the guard on fast); report status; ilb_report started
- 2249b743 11:00:48 Identification best model: POA_B dated note, A2M1 conditional on A2 or M1 passing the development screen (the Mastermind's decision, before an
- c5bdcab0 11:01:29 Identification best model: the A2M1 gate (ilb_gpu gate; the development guard B1 natural, slow, fast within 5 of v4) replaces A2M1's unconditi
- ff3c0a89 11:03:00 Identification best model: POA_B dated note, Uzayr confirms the A2M1 gate (relayed by the Mastermind)
- 691665ca 11:27:07 Identification best model: greedy round 2 chose A4 (F7+A3+A4); output checks for A4 configurations once the cache exists (round 3's added befo
- 24bff9fc 12:01:29 Identification best model: greedy rounds 2 and 3 (A4, then A1; current A1+A3+A4 at 31.41), 25 configurations; report status and builder
- 2a25dce1 13:06:45 Identification best model: GPU development screen (A2+F7 DS 25.42, M1+F7 27.29, against v4+F7's 29.59): neither passes, A2M1 skipped by the ga
- d701db89 13:08:16 Identification best model: ilb_report sections 7 to 9 (ship plan, looks, files, commits, timings), the greedy path with Z and D steps and M3's

Timings (the driver's log):

- [08:25:03] [CPU1] BLOCK START (CPU, about 25 min): block 1: A1 dense offsets, A3 stretched windows, A4 test windows with maps (CPU, up to 8 processes; extraction only)
- [08:42:04] [GPU] BLOCK START (GPU, about 45 min): A4 cache: the shipped CNNs on the 0.15 and 0.30 s test windows, 13 model-sessions, mps, one job at a time, empty_cache p
- [09:32:31] [CPU1] BLOCK END: block 1
- [09:32:31] [CPU1] BLOCK START (CPU, about 120 min): block 2: P1 check, F7 reproduction, the singles (P1, P2, A1, A3, A4, A5, M2, M3) and greedy round 1 from F7 on the com
- [10:26:10] [GPU] BLOCK END: GPU block A (A4 cache)
- [10:26:10] [GPU] BLOCK START (GPU, about 1 min): A4 cache check: every model-session present and offset 0 equal to its replay (writes DONE or FAILED)
- [10:26:21] [GPU] BLOCK END: GPU A4 check
- [10:26:22] [GPU] BLOCK START (GPU, about 200 min): GPU candidates A2, M1, A2M1 on the development folds D1 to D3 (v4 CNN recipe, 6,000 steps, seeds 0 to 2, mps, one job a
- [10:40:50] [CPU1] START next_2
- [10:41:01] [CPU1] END next_2 rc 0
- [11:26:36] [CPU1] START next_3
- [11:26:47] [CPU1] END next_3 rc 0
- [12:00:59] [CPU1] START next_4
- [12:01:09] [CPU1] END next_4 rc 0
- [12:47:29] [CPU1] START next_5
- [12:47:40] [CPU1] END next_5 rc 0
- [13:06:36] [GPU] BLOCK END: GPU block B (GPU candidates, development screen)
- [13:18:23] [CPU1] START next_6
- [13:18:33] [CPU1] END next_6 rc 0
- [13:41:44] [CPU1] START next_7
- [13:41:54] [CPU1] END next_7 rc 0
- [14:03:13] [CPU1] START summarise
- [14:03:34] [CPU1] BLOCK END: block 2 (greedy build) done

