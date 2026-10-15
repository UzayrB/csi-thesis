# Pre-registration: training after DC2, items 3 and 4 of the DC2 results batch

**Written 2026-09-28 from 08:11 SAST (clock read), BEFORE item 2 ran.** No model had run on Room B:
`runs/constrained/dc2_room_B_s0.5_pressalign/` did not exist and no DC2 result file existed. Both
days of Room B data did exist, so everything here is **POST HOC with respect to the data, and
EXPLORATORY**. Nothing here can change a confirmatory verdict of item 2, replace the frozen model, or
enter the thesis claim. The brief is `reports/BRIEF_DC2_results_2026-09-28.md`. Section 4 of
`PREREG_DC2_crossroom_2026-09-22.md` pre-registered item 3's pairings on 2026-09-22; this fixes how
they are run.

## 1. Data, and what is never trained on

- **Sessions:** A1, A2, A3 are Room A sessions 01, 02, 03. B1 and B2 are Room B, 26 and 27 September.
  Each has 120 scored passes.
- **Calibration walks** (`participant_PA2_C_walk` in B1, `participant_PA6_C_walk` in B2) are
  **never scored and never trained on**, by the heads or by the start-of-walk readers. They are used
  only to re-anchor configuration B's null and gate and, in (iii), to normalise.
- **A test session is never in its own training set.**
- PA5's B1 labels are the relabelled ones, and PA1's B1 baseline is PA2's
  (`PREREG_DC2_ADDENDUM_2026-09-28_relabel.md`).

## 2. The recipe, identical in every cell

- **Heads:** the frozen DC2 heads' code, recipe, epochs and seeds (`d5_train_room_a`,
  `artefacts.train_pairing`):
  - the 0.5 s g25 head (seed 0, 24 epochs) and its position head (20 epochs), on the ONE lattice's
    walking windows;
  - three 1 s g25 heads (seeds 0, 1, 2) and the 1 s g100 head, on 1.0 s-stride windows;
  - three per-link networks each.
- **Room B's 1 s windows:** cut from the raw capture by `pipeline.splits.windows` at its defaults
  (2 s windows, 1.0 s stride), the cutter that made Room A's `data/windows`. They are written to
  `runs/constrained/windows_s1.0_dc2`, the tree `dc2_pipeline` names for this purpose.
- **The pool:** all five heads inferred over the test session's 0.5 s press-aligned windows, mean
  link fusion, equal weights: the frozen pool's construction.
- **The decision:** the shipped committed decision (A2 start term 0.5 plus `a_veto_1.0`, the shipped
  decoder).
- **The start-of-walk readers** (A2 and the veto) are fitted on the training sessions' passes, with
  calibration recordings excluded. Each training session's reader features come from heads that did
  not train on it:
  - a Room A session: the shipped rule (`t2_embed.tag_for_session`, the first Room A pairing that
    tests it);
  - a Room B day: the frozen Room A heads `s010203_to_sB` as inferred on that day in item 2.

  The test session's reader features come from the cell's own heads, as in DC2.
- **The lock:** the drawn lock, read at the window that ends at press + 2.0 s: display decode,
  `sd_scale` 4.5, 0.8 m per window, A2 term. It is computed as `dc2_scorerlock` computes DC2's
  display lock.

## 3. Configurations

- **Every cell is decoded under configuration A,** the absolute constants (null −7.50, gate 0.431).
  **This is the basis of every comparison below.** The brief's column (i) for the B rows is item 2a,
  and Room A's existing folds are decoded this way.
- **Cells that test a Room B day are also decoded under configuration B,** with null and gate
  re-anchored on that day's calibration walk exactly as in DC2. This is reported beside
  configuration A, never instead of it.
- Room A test sessions have no calibration walk, so they have configuration A only.

## 4. Item 3: new day against new room

| cell | train | test |
|---|---|---|
| 3a | B1 | B2 |
| 3b | B2 | B1 |

- **Against Room A's six single-day pairings,** which also train on one day: `s01_to_s02`,
  `s01_to_s03`, `s02_to_s01`, `s02_to_s03`, `s03_to_s01`, `s03_to_s02`. Committed accuracy from
  `d4_headline` (the shipped configuration); drawn lock from `d6_lock_commit` (`LOCK_DRAWN`).
- **Also, on the same test day, paired pass by pass:** 3a against item 2a on B2, and 3b against 2a
  on B1. This is new room against new day with the test passes held fixed. The training amounts
  differ (one Room B day against three Room A days), and that is stated beside it.
- With two Room B pairings there is no test across pairings. Per-pairing figures and the paired
  intervals are the result.

## 5. Item 4: training on both rooms

| test | (i) one room only | (ii) pooled | (iii) per-room normalisation |
|---|---|---|---|
| B2 | A1+A2+A3 (item 2a) | A1+A2+A3+B1 | as (ii) |
| B1 | A1+A2+A3 (item 2a) | A1+A2+A3+B2 | as (ii) |
| A1 | A2+A3, the existing fold `s0203_to_s01` | A2+A3+B1+B2 | as (ii) |
| A2 | A1+A3, the existing fold `s0103_to_s02` | A1+A3+B1+B2 | as (ii) |
| A3 | A1+A2, the existing fold `s0102_to_s03` | A1+A2+B1+B2 | as (ii) |

**(ii), pooled:** the recipe unchanged on the union of the training sessions. Its own per-channel
standardisation (one mean and one spread per input channel per link, `nets.per_channel_stats`) is
computed over the pooled windows.

**(iii), per-room normalisation:**
- **Training:** before the unchanged recipe runs, each training window is standardised by its own
  room's per-channel statistics. These are the same statistic as `per_channel_stats`, computed per
  head and per link over that room's training windows. The recipe's own standardisation then runs
  unchanged on the pre-standardised windows.
- **Test:** each test recording is standardised by statistics from its own test session only, never
  from its labels:
  - a Room B test day: every window of that day's calibration recording, plus the idle windows
    before the first press of each of that day's evaluated recordings;
  - a Room A test session, which has no calibration walk: the idle windows before the first press
    of each of its recordings, using `u1_adapt`'s anchor (mode `idle`, ending before the first
    press, `walk_edge` excluded).
- **This asymmetry is disclosed beside every (iii) figure:** Room A's test normalisation rests on
  idle radio alone, Room B's on a calibration walk and idle radio.

**Comparisons, each paired pass by pass on the same 120 test passes, with 95 percent intervals:**
- (ii) against (i), per row: does the other room's data help or hurt? The B rows are also compared
  with item 3 on the same test day, and the A1 row (the session-01 shift) is reported explicitly.
- (iii) against (ii), per row: does per-room normalisation make pooling work?

## 6. What is reported, for every cell whatever its result

- Committed accuracy and drawn-lock accuracy over the 120 scored passes, with 95 percent bootstrap
  intervals.
- Recall on E_col1, E_col5, E_row1 and E_row5.
- The paired differences above.
- Chance: 8.33 percent.
- Per-pairing figures always, never a median alone.

## 7. The speed rule, fixed now

One training job runs at a time. Measured on 2026-09-23, the five heads on three Room A sessions
took about 40 minutes run alone.
- **If the first item 4 cell's six networks take more than 90 minutes of wall clock,** every item 3
  and item 4 cell switches to the single 0.5 s g25 head (with its position head, which the A2 term
  needs). So do their comparators: item 2a on each Room B day, Room A's three two-session folds and
  six single-day pairings, all re-decoded from their existing single-head posteriors.
- **The switch is labelled "single-head" everywhere,** with the measured time as the reason.
- The rule is decided here, before any item 3 or item 4 figure exists.

## 8. Order

1. Item 2 runs first and alone.
2. Then the Room B 1 s cut.
3. Then item 3 (3a, 3b).
4. Then item 4: the five (ii) cells in the table's order, then the five (iii) cells.

One training job at a time throughout.
