# CORRECTION: the quoted lock was not the drawn lock. 2026-09-23, batch 23d

Found while checking the 23d closing report's figures against the render, after every batch item was
DONE or BLOCKED. Stage `pipeline/constrained/d6_lock_commit.py`, results
`runs/constrained/fh/d6_lock_commit/results.json` (ONE lattice) and `.../d6_lock_commit_grid/` (grid).
**Freeze 2026-09-23d supersedes 23c on the lock; 23c is not overwritten. No ship verdict changes.**

## What was wrong

1. **Every lock figure since the causal correction decoded the display at the decision's `sd_scale`
   1.0**: `y2a_causal`, `z3a_linkprod` (the pre-registered 57.50), `y4_pressalign` (50.00), and so
   `d4_headline` and freeze 23c. **The render draws its lock from the DISPLAY decode at `sd_scale` 4.5**
   (`f3_render`: "the DISPLAY: the speed cap lives here"). On the render's own pairing the two locks
   differ on **13 of 120 walks**; at 4.5 they differ on **0**.
2. **ACCEPTANCE.md's table "The lock against the commitment" was read from `r5_lock` (2026-09-20)**:
   the lock at 1.5 s on the grid lattice, before the causal correction, printed as "locked at 2 s".
   Its 50.0 equalled the new lock figure by coincidence. Item 4 updated ACCEPTANCE's headline table
   and missed this one.

## The checks that make the new figures trustworthy

| check | result |
|---|---|
| the `sd_scale` 1.0 lock, recomputed, against the quoted rows | **1080 of 1080 identical on both lattices** (`y4_pressalign` rows_one; `z3a_linkprod_w0`) |
| the `sd_scale` 4.5 lock and the text answer, against ACCEPTANCE's per-walk tables | **120 of 120 walks identical** |
| the grid lattice's text answer against `r5_lock`'s 65.83 | 65.83, reproduced |

`sd_scale` is therefore the only difference between the quoted and the drawn lock. Every value of the
display decode is asserted against the render's own results file before the stage runs.

## The corrected figures (median over the nine cross-day pairings, 95 percent interval)

| | pre-registered (grid) | shipped (ONE lattice) | paired, ONE minus grid |
|---|---|---|---|
| **lock, as DRAWN, held-out seven** | **55.83** [27.50, 69.17] | **53.33** [26.67, 62.50] | -3.10 [-4.88, -0.95] |
| lock, as drawn, all nine | 55.83 [25.83, 69.17] | 53.33 [25.83, 62.50] | -2.41 [-4.17, -0.65] |
| lock as QUOTED until now (`sd_scale` 1.0), held-out seven | 57.50 | 50.00 | -4.52 [-7.02, -2.38] |
| **committed text, bounded at the end press, all nine** | **65.83** [55.00, 84.17] | **60.00** [55.83, 81.67] | **-2.59 [-4.63, -0.46]** |
| committed headline, semi-bounded + `a_veto_1.0` | 62.50 | 73.33 [35.00, 87.50] | +3.80 [0.83, 6.94] (from d4) |

Drawn against quoted, same lattice: +0.74 [-0.56, 2.04] on the ONE lattice and +0.19 [-1.30, 2.04] on
the grid; they agree on 89 percent of passes. **The correction changes what the lock figure
describes, and moves it by a few points; it does not change its size class.**

### The edge lines

| | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|
| drawn lock, grid | 35.19 | 66.67 | 31.48 | 55.56 |
| **drawn lock, ONE lattice** | 37.04 | 59.26 | **18.52** | 42.59 |
| quoted lock, ONE lattice | 37.04 | 66.67 | 27.78 | 50.00 |
| committed text, grid | 51.85 | 75.93 | 79.63 | 66.67 |
| **committed text, ONE lattice** | 40.74 | 70.37 | 74.07 | 55.56 |
| committed headline, ONE lattice | 46.30 | 77.78 | 83.33 | 59.26 |

Session-01 folds, drawn lock on the ONE lattice: 26.67, 25.83, 20.00. Committed text: 56.67, 55.83,
49.17. Committed headline: 34.17, 35.00, 32.50.

## A NEW COST, disclosed: the ONE lattice costs the answer the video shows as text

The ONE lattice shipped at the operator's direction as a correctness fix (item 2: the grid lock read
a median 0.218 s of radio not yet recorded at its frame), not as an arm, so no ship rule was applied
to it. It was measured on the semi-bounded decision (+1.02 [-0.83, 2.87]) and on the lock, never on
the bounded text answer. Measured now: **-2.59 [-4.63, -0.46] paired, and every edge line loses
walks: E_col1 -6, E_col5 -3, E_row1 -3, E_row5 -6 (net -18).** As an arm it would fail the amended
(f). The drawn lock also falls, -2.41 [-4.17, -0.65], with E_row1 at 18.5 percent; but the grid lock
it is compared with read radio that had not been recorded yet, so that fall is the price of
causality, not a regression. **The text answer has no causality problem at the end press, so its
loss is a real cost of the fix.** Whether to accept it, or have the bounded rescore read a different
lattice from the lock, is the operator's decision; nothing here changes it.

## What still stands

- **Every ship verdict, as measured.** The lock arms (t7, t9, fusion, `y2_dial`, switching) were
  compared like with like at `sd_scale` 1.0 on both sides, so their refusals stand on that decode.
  They are refusals on a decode the render does not draw. The t7, t9 and fusion lock arms collapsed
  the edge lines far past the floor. **`y2_dial` did not: on the ONE lattice it was refused by ONE
  edge walk (net -1, E_row1).** On the drawn decode that verdict could go either way. It is NOT
  re-measured here; it is an open item for the operator, and re-measuring it would be a new arm
  evaluation, pre-registered first. **CLOSED 2026-09-23 by operator decision (batch 23e item 5): `y2_dial` stays
  refused and is not re-measured.**
- The headline (62.50 pre-registered; 73.33 post-amendment) is the committed DECISION decode and is
  untouched.
- DC2: the lock is a component of the tested configuration, not an outcome. PREREG s.10 now names the
  display decode explicitly, written before any Room B data exists (`data/room_B` is absent).

## What was changed

- `f3_render`'s ACCEPTANCE writer reads `d6_lock_commit` in place of `r5_lock` and `g3_final`, and quotes
  it only if d6's rows equal the render's own walks, walk for walk; otherwise it prints STALE. The
  lock column of the headline table is the drawn lock on both lattices.
- `runs/constrained/demo/ACCEPTANCE.md` corrected by hand in the three places the writer now changes,
  marked as such, because the item-4 instruction was to render once. The next render writes the same.
- Freeze 2026-09-23d; STATE, HANDOFF, QUEUE and the 23d closing report carry the corrected lock.
