# Addendum to PREREG_postDC2_training_2026-09-28: one exploratory cell. POST HOC

**Written 2026-09-28 from 20:13 SAST (clock read), before the cell ran. POST HOC, in those words:
designed by Uzayr after seeing the item 4 results.** Exploratory; it cannot change any confirmatory
verdict or replace the frozen model.

## The cell

- **Training:** one model on A1 + A2 + B1, walking windows only. The calibration walks are never
  trained on: B1's `participant_PA2_C_walk` is left out of the training view as in every harness
  cell.
- **Recipe and harness:** item 4 column (ii)'s: `pipeline/constrained/pd_cells.py`, the five-head
  pool and the position head, pooled standardisation. **One training job.**
- **Tested with that single model on two sessions:**
  - **A3** (Room A session 03), configuration A. A3 has no calibration walk, so B equals A.
  - **B2** (Room B day 2), configurations A and B. B re-anchors null and gate on B2's
    `participant_PA6_C_walk`.
- **How one model serves two cells:** the harness names a model after its test session. So the
  model is trained once, in cell `ph_A3`, and its weight files are copied unchanged into cell
  `ph_B2` under that cell's name. The copies are checked to be byte-identical.

## Reported

For each test session:
- committed and lock accuracy with 95 percent intervals;
- E_col1, E_col5, E_row1 and E_row5;
- paired differences on the same passes against:
  - **A3:** the Room-A-only model on A1 + A2. That is cell `4i_A3`, the same harness and recipe;
    the shipped fold `s0102_to_s03` is reported beside it.
  - **B2:** the frozen A1 + A2 + A3 model, item 2a under configuration A and item 2b under
    configuration B.

Also reported beside it, for context and not tested: item 4's `4ii_A3` (A1+A2+B1+B2) and `4ii_B2`
(A1+A2+A3+B1).
