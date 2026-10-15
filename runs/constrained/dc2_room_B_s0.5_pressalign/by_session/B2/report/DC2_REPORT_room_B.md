# DC2 report: room_B

**room_B**

Generated 2026-09-28T08:20:56, 3.76 min. Pre-registration: `reports/PREREG_DC2_crossroom_2026-09-22.md`, section 10. Heads `s010203_to_sB`, trained on Room A sessions 01, 02, 03.

## 0. Ingest

| | |
|---|---|
| raw recordings | 14 |
| cut | the ONE lattice (press-aligned 0.5 s), by this pipeline |
| within-DC2 training possible (1.0 s tree) | True |

## 0b. The receivers, by board

Tracking reads RX1, RX2 and RX3 by NAME, and each name was checked against the Room A tracking board's MAC: mismatches 0, swapped 0, unverified 0. Extra receivers present and never read by tracking: none.

## 1. The primary comparison, per session and pooled (95 percent)

| session | n | A, unchanged | B, re-anchored | B minus A, paired | chance |
|---|---|---|---|---|---|
| B2 | 120 | 50.00 [40.83, 60.00] | 57.50 [48.33, 65.83] | +7.50 [2.50, 13.33] | 8.3 |
| ALL | 120 | 50.00 [40.83, 60.00] | 57.50 [48.33, 65.83] | +7.50 [2.50, 13.33] | 8.3 |

**Claim supported (B above chance with its interval): True.** Room A's pre-registered figure is 62.50.

## 2. Edge lines, individually

| session | config | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|
| B2 | A | 83.3 | 66.7 | 50.0 | 16.7 |
| B2 | B | 83.3 | 66.7 | 66.7 | 33.3 |

## 3. The confirmatory arms, each at 97.5 percent

| arm | paired points [97.5%] | passes, median per pairing | edge walks | amended (f) | CONFIRMED |
|---|---|---|---|---|---|
| `a_veto_1.0` (B against B without it) | +1.67 [-2.50, 6.67] | 2.0 | {'E_col1': 0, 'E_col5': 1, 'E_row1': 0, 'E_row5': 0} | True | False |
| `b_abstain_0.25` (against B without the veto) | +0.83 [0.00, 3.33] | 1.0 | {'E_col1': 0, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0} | True | False |

## 4. The three calibration numbers

| session | s_B | s_A | null (relative) | null used | fell back | gate theta |
|---|---|---|---|---|---|---|
| B2 | 1.6001362197593414 | 2.111 | -5.68549866838114 | -5.68549866838114 | False | 0.201 |

## 5. EXPLORATORY arms (batch 23e item 4). NOT confirmatory; no claim rests on them

Product link fusion, re-anchored at the PRODUCT's scale for the arm only (`TRACKING_FROZEN_2026-09-23e`). 95 percent intervals, reported, never tested.

| arm | fusion w | pct [95%] | n | s_B | s_A | null used | fell back |
|---|---|---|---|---|---|---|---|
| B_prod0.25 (B2) | 0.25 | 64.17 [55.83, 72.50] | 120 | 3.214938998206843 | 3.7428177798574556 | -6.442216507657401 | False |
