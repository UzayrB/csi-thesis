# Batch 2026-09-23g: closing report. THE LAST MODEL BATCH BEFORE DC2

Operator instruction 7, verbatim in `reports/BRIEF_render_and_prepress_2026-09-22.md`. Opened 20:14 and
closed 20:50 on 23 September (clock read), well inside the 12:00, 24 September deadline. Every figure is read
from `runs/constrained/fh/{g1_ablation,g2_scorerlock,dc2_pipeline_standin}/results.json`.

**Freeze `runs/TRACKING_FROZEN_2026-09-23h.json`, THE DC2 MODEL FREEZE** (written 20:46:25, clock read,
before any Room B data): the SHA-256 of 38 code files, the 18 Room A model files DC2 runs and 4 documents.
**No model change is made until the Room B analysis.** The headline does not change: 62.50
pre-registered, 73.33 post-amendment.

## 1. The ablation table (diagnostic, ships nothing)

The shipped variant reproduces the drawn lock on 1080 of 1080 passes.

| variant | lock right (of 1080) | lock median, nine / held-out | paired against shipped | locks changed | **disagree with the scorer** | edge walks E_col1 / E_col5 / E_row1 / E_row5 |
|---|---|---|---|---|---|---|
| shipped | 493 | 53.33 / 53.33 | | | **363 (33.6%)** | 20 / 32 / 10 / 23 |
| no speed cap | 485 | 50.00 / 50.00 | -0.74 [-2.04, 0.56] | 119 | **353 (32.7%)** | 20 / 36 / 15 / 27 |
| no display head | 493 | 53.33 / 53.33 | 0 | 0 | **363** | 20 / 32 / 10 / 23 |
| with the veto term | 493 | 53.33 / 53.33 | 0 | 0 | **363** | 20 / 32 / 10 / 23 |
| all three removed | 485 | 50.00 / 50.00 | -0.74 [-2.04, 0.56] | 119 | **353** | 20 / 36 / 15 / 27 |

**None of the three explains the disagreement; removing all three leaves 353 of 363.** The cap accounts
for 10 (and trades 8 pooled locks for 13 edge walks); the display head feeds only the path after the lock
and changes no lock; the veto term changes no lock (not vacuous: 7 to 9.5 lines vetoed per pass). The
disagreement is the two estimators' structure. `reports/SCORERLOCK_AND_ABLATION_2026-09-23.md`.

## 2. The scorer-lock verdict: REFUSED

Pre-registered in `reports/PREREG_scorerlock_2026-09-23.md` at 20:17, before the stage, **disclosing that
its lead was observed on all nine pairings, held-out folds included, so this Room A test is not clean and
DC2 would be its confirmatory test.** Reproductions exact (w 0 = the drawn lock, the scorer = `e2_switch`,
1080 of 1080 each). The selection folds chose **w = 0.25**:

| condition | result |
|---|---|
| (a) held-out paired interval | **pass**: +5.12 [2.98, 7.74] (all nine +4.44 [2.59, 6.57]); lock median 53.33 to 57.50 |
| (b) two passes per pairing | **pass**: median 5 |
| (c) as clarified | **pass**: 5 / 6 / 6 / 5 across w, non-flat |
| both causal bounds | **pass**: the shipped lock's own windows; the drawn path -1.250 s |
| (f) as amended | **pass**: net +1 (E_col1 -1, E_col5 +1, E_row5 +1) |
| continuity | **pass**: 0 violations, 0 off-segment frames, 272 jumps after the lock against 303 |
| **substitution** | **FAIL: 0.38 against 0.5** |

**It does not ship, so nothing changed**: no render, no new lock, no switching re-choice, no new render
figures. Read as an interpretation, not a re-test: the pre-registered substitution swaps the scorer's
walk emissions and keeps the start term from the pass's own pre-press radio, which dominates over the
lock's three windows.

## 3. New lock and switching figures

**None: the scorer lock did not ship.** The lock, the switching rule (arm C) and the render of freeze 23g
stand unchanged.

## 4. DC2 status

- **PREREG_DC2 section 12** (before any Room B data): the display component is the DISPLAY lock,
  unchanged, with arm C switching and the shipped committed decision as the end text.
- **`reports/MODEL_FREEZE_DC2.md`**: the exact configuration DC2 tests, and the line: **no model change is
  made until the Room B analysis.**
- **The stand-in plumbing check PASSES on the frozen code** (run 20:40, 5.5 min): **the DC2 path equals
  the shipped decisions on 72 of 72 walks, EXACT**; the exploratory arm's fused pool equals Room A's own
  measurement 72 of 72, EXACT; the node identity check passes on all 18 Room A recordings (no mismatch,
  no swap). A 83.33, B 83.33, the relative null -6.93 (plumbing figures, never results).
- **Live rig run: BLOCKED ON OPERATOR**, no receiver attached at any check-in; `scripts/live_rig_run.sh`.

## Suite

**1254 passed, 8 skipped, 0 failures** (20:50:33).
