# Pre-registration: product fusion on the COMMITTED decision, on the ONE lattice

**Written 2026-09-23 (batch 23d, item 3), before any press-aligned fusion figure exists.** Operator
instruction 4, verbatim in the BRIEF: *"PRODUCT FUSION on the COMMITTED decision only (the lock
keeps mean fusion, since it fails even the amended (f) there). Choose w on the selection folds
s01_to_s02 and s02_to_s01 ONLY, on the press-aligned lattice. It ships if (a), (b), (c) as clarified,
substitution, both causal bounds and amended (f) pass at that w. Report the gain's split between
link agreement and sharpening (control T). If any arm from item 1 also passes and is compatible,
include it; report interactions."*

Known before writing: the grid-lattice sweep (`reports/FINDING_linkfusion_2026-09-23.md`) and the
item-1 re-evaluation (`reports/REEVAL_f_amended_2026-09-23.md`). Nothing on the press-aligned
lattice.

---

## 1. The arm

`z3a_linkprod` arm A, unchanged: `log p_w = (1 - w) log p_mean + w log p_product`, renormalised, on
every pool head. **Applied to the COMMITTED decision only**: the semi-bounded `final_line` (the
headline's quantity) and the bounded rescore the render prints at the end press. **The lock and the
drawn path keep mean fusion.** Grid w in {0, 0.25, 0.5, 0.75, 1.0}; control T (the mean cubed) at 1.0.
All on the ONE lattice (`pipeline/constrained/lattice.py`), no root set by hand.

## 2. Choosing w, on the selection folds ONLY

**w\* = the weight in {0.25, 0.5, 0.75, 1.0} with the largest mean committed paired delta against
w = 0 over s01_to_s02 and s02_to_s01; ties go to the SMALLER weight.** No held-out figure and no edge
line enters the choice. If no weight has a positive selection-fold delta, the arm is REFUSED.

## 3. It ships only if all of these hold at w\*, on the held-out seven

- **(a)** paired interval (`night_common.boot_ci` over the seven per-pairing deltas) entirely above 0;
- **(b)** median paired delta at least **two passes** per pairing, as integers;
- **(c) as clarified** (`SEMIBOUNDED_STATE.md` s.10): read on the median paired delta anchored at
  w = 0, the response over the grid must be NON-FLAT; an interior optimum is permitted because w\* is
  chosen on the selection folds;
- **substitution**: the committed line changes on another participant's radio at least as often as
  shipped, less at most one pass per pairing (median of `subs_line_changed` counts), and the
  along-line ratio is reported;
- **both causal bounds** of the render hold (item 4 measures them; the committed decision is the
  full-walk answer and draws nothing ahead of its evidence);
- **amended (f)**: the four edge lines' combined change in correct walks >= 0 and no line loses more
  than two, over nine pairings.

The committed reproduction check: w = 0 on the ONE lattice must return what `y4_pressalign`
measured, committed held-out **74.17**, all-nine median **67.50**.

## 4. Control T, the split

Committed paired gain of T at w = 1 over the gain of A at w = 1, on the held-out seven, reported as
the sharpening share; the remainder is the link-agreement share. As on the grid lattice.

## 5. The item-1 arms, and interactions

Two arms pass every condition under the amended (f) (`REEVAL_f_amended`). Both were measured on the
retired grid lattice, so both are **re-measured on the ONE lattice by their own stages, unchanged**,
before anything ships:

- **`y2_dial`**, the lock estimator mix. It acts on the LOCK, so it is compatible with a committed
  arm and cannot interact with it: the lock and the committed answer are separate decodes. Its
  pre-registered selection rule under the amended (f): the largest w in {0.05 .. 0.25} whose edge
  lines pass the amended (f). It ships if (a), (b), (c), substitution and amended (f) hold at that w.
- **`a_veto_1.0`**, the pre-press reader's veto on the COMMITTED decision (`u1_adapt` reader,
  `u2_useit` arm). It acts on the same decision as product fusion, so it IS an interaction: measured
  alone, and combined with product fusion at w\*. **The combination ships only if it passes every
  condition against shipped AND is not worse than fusion alone** (paired against fusion alone, the
  interval must not lie entirely below zero). Its 2026-09-22 decline on multiple testing is
  recorded beside it; the operator's instruction to include passing arms is followed.

## 6. Prediction, recorded before the run

The press-aligned lattice leaves the committed answer within noise (+0.36 [-1.79, 2.74] measured),
so product fusion should behave much as on the grid: a large committed gain, an interior optimum
near w = 0.25, and edge lines close to the amended (f)'s floor.
