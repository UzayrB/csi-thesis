# Correction of the record: every lock figure, at the causal horizon

2026-09-23, batch 23c, item 1. Operator instruction 3 (verbatim in the BRIEF): *"Every document
quoting the lookahead lock (t6, t7, FINDING_pooled_vs_edge, PART1_REPORT, HANDOFF) gets the causal
figures beside it, with the lookahead ones marked non-causal and superseded. Add a test so no lock
figure can be computed past the causal horizon."*

**Why:** `reports/FINDING_two_locks_2026-09-23.md`. The lock figures in t6, t7, t9 and y1 read
windows `lo .. lo + step + LAG_W`, two windows (1.0 s) of radio that have not finished recording
at the 2 s lock. The render reads `lo .. lo + step`. Only the second can exist live.

---

## What was done

1. **`pipeline/constrained/lock_horizon.py`**: the one place a lock's end window is computed.
   `lock_end(lo, step, n)` returns `min(lo + step, n - 1)` and `check_end` raises
   `NonCausalLock` for anything later. There is no lookahead flag.
2. **t6, t7, t9, y1_diag and y2_dial** now take every lock end window from it. `y2a_causal`,
   whose purpose was to measure lookahead, is **retired**: `proxy_line` refuses `extra > 0` and
   `main()` refuses to run. Its one run is kept as the evidence.
3. **`tests/test_lock_is_causal.py`, 9 tests.** A poison test replaces every window after
   `lo + step` with a spike on another chain and requires all four lock estimators to return the
   same answer; the spike is first shown to move a two-window lookahead decode, so the poison is
   potent. A static test bans `... + LAG_W` anywhere in `pipeline/constrained`.
   **Mutation-checked:** with t7's old `lo + step + 2` put back, the t7 case goes red; restored,
   green.
4. **t6, t7, t9 and y1_diag re-run at the causal horizon.** Their lookahead outputs were archived
   first, never overwritten: `runs/constrained/fh/_LOOKAHEAD_superseded_2026-09-23c/`.
5. The documents below carry the causal figures beside the lookahead ones.

## Reproduction, which is what makes the re-run trustworthy

The causal t6, t7, t9 and y1 shipped lock is **57.50 held-out, edge 42.59 / 77.78 / 35.19 / 57.41**,
equal to the renderer's own lock (`y1b_locksrc`) and to `y2a_causal.proxy_extra0` on the median
and all four edge lines. t7's causal `w = 0.25` point is **62.50**, equal to `y2_dial`'s. The
**committed answer is identical in both runs, 75.00 held-out and 62.50 on all nine**, which is the
control: only the lock moved.

## The tables. Lookahead columns are NON-CAUSAL and SUPERSEDED

| stage | arm | held-out 7, lookahead (NON-CAUSAL) | **held-out 7, causal** | edge E_col1/E_col5/E_row1/E_row5, lookahead | **edge, causal** | ships (causal) | fails (causal) |
|---|---|---|---|---|---|---|---|
| t7 | shipped | 60.83 | **57.50** | 50.00 / 72.22 / 74.07 / 64.81 | **42.59 / 77.78 / 35.19 / 57.41** |  |  |
| t7 | E_chain_total | 73.33 | **65.00** | 31.48 / 66.67 / 51.85 / 46.30 | **29.63 / 57.41 / 24.07 / 35.19** | no | c,f |
| t7 | E_chain_total_no_prior | 69.17 | **62.50** | 42.59 / 66.67 / 62.96 / 51.85 | **42.59 / 70.37 / 29.63 / 46.30** | no | c,f |
| t7 | E_no_marginal | 66.67 | **59.17** | 1.85 / 35.19 / 29.63 / 22.22 | **0.00 / 35.19 / 9.26 / 7.41** | no | a,b,c,f |
| t7 | E_both | 71.67 | **63.33** | 7.41 / 46.30 / 29.63 / 25.93 | **0.00 / 27.78 / 5.56 / 5.56** | no | c,f |
| t7 | weight sweep | [[0.0, 60.833], [0.25, 67.5], [0.5, 69.167], [0.75, 69.167], [1.0, 69.167]] | **[[0.0, 57.5], [0.25, 62.5], [0.5, 63.333], [0.75, 63.333], [1.0, 62.5]]** | | | | |
| t9 | shipped | 60.83 | **57.50** | 50.00 / 72.22 / 74.07 / 64.81 | **42.59 / 77.78 / 35.19 / 57.41** |  |  |
| t9 | raw_chain_total | 69.17 | **62.50** | 42.59 / 66.67 / 62.96 / 51.85 | **42.59 / 70.37 / 29.63 / 46.30** | no | f |
| t9 | N_per_step | 69.17 | **62.50** | 42.59 / 66.67 / 62.96 / 51.85 | **42.59 / 70.37 / 29.63 / 46.30** | no | f |
| t9 | N_per_state | 69.17 | **62.50** | 42.59 / 66.67 / 62.96 / 51.85 | **42.59 / 70.37 / 29.63 / 46.30** | no | f |
| t9 | N_per_metre | 69.17 | **63.33** | 42.59 / 66.67 / 62.96 / 53.70 | **42.59 / 70.37 / 29.63 / 46.30** | no | f |
| t9 | weight sweep | [[0.0, 69.167], [0.25, 69.167], [0.5, 69.167], [0.75, 69.167], [1.0, 69.167]] | **[[0.0, 62.5], [0.25, 62.5], [0.5, 62.5], [0.75, 62.5], [1.0, 62.5]]** | | | | |

| t6 arm | held-out 7 lookahead (NON-CAUSAL) | **causal** | all 9 lookahead | **all 9 causal** | A_fwd drawn/true lookahead | **causal** |
|---|---|---|---|---|---|---|
| shipped | 60.83 | **57.50** | 49.17 | **49.17** | 1.954 | **2.611** |
| i_no_marginal | 68.33 | **58.33** | 58.33 | **56.67** | 2.037 | **2.694** |
| ii_disp_prior_flat | 28.33 | **53.33** | 22.50 | **45.00** | 1.954 | **2.769** |
| v_emission_only | 30.00 | **29.17** | 28.33 | **25.83** | 3.009 | **2.972** |
| vi_chain_totals_lock | 73.33 | **65.00** | 55.83 | **54.17** | 2.806 | **3.093** |
| ii_no_chain_prior | 69.17 | **62.50** | 55.00 | **46.67** | 2.741 | **3.074** |
| iii_no_A2 | 61.67 | **60.00** | 54.17 | **54.17** | 2.093 | **2.639** |
| committed | 75.00 | **75.00** | 62.50 | **62.50** | 2.241 | **2.241** |

t6 n_lock_wrong_commit_right 197 -> 216
t6 most over-drawn [['E_col5', 2.944], ['E_col1', 1.981], ['A_fwd', 1.954]] -> [['E_col5', 2.741], ['A_fwd', 2.611], ['E_row5', 1.704]]

Edge-line means, lookahead to **causal**: shipped 65.28 to **53.24**; E_chain_total 49.07 to
**36.57**; chain total with prior withheld 56.02 to **47.22**; E_both 27.31 to **9.72**;
E_no_marginal 22.22 to **12.96**.

Paired deltas against the shipped lock, held-out, lookahead to **causal**: E_chain_total +7.50 to
**+5.83 [2.50, 11.79]**; prior withheld +5.83 to **+3.33 [0.60, 7.14]**; E_both +10.00 to
**+4.17 [0.71, 8.57]**; E_no_marginal +4.17 to **+1.67 [-0.95, 5.60]**.

Session-01 folds, causal shipped lock: s02_to_s01 **24.17**, s03_to_s01 **25.00**, s0203_to_s01
**27.50**.

## What changes and what does not

- **No verdict changes.** Every arm refused under lookahead is still refused causally, on (f) and
  in t7 also on (c). The rule held in both conventions.
- **The trade in `FINDING_pooled_vs_edge` is sharper, not softer.** Causally the estimator arms
  buy less (+3.33 to +5.83 paired, not +5.83 to +10.00) and cost more at the edge: **E_col1 is 0.00
  under E_both and E_no_marginal**, not 7.4 and 1.9.
- **The shipped lock's own edge recall is 53.24 mean, not 65.3**, and **E_row1 is 35.19, not
  74.07**. E_row1 was the best edge line in the quoted convention and is the worst causally.
- **A_fwd's over-draw at the shipped lock is 2.61, not 1.95** (t6; the render's own census reads
  2.620, one walk apart). Under the chain-total lock it is **3.09**, not 2.81. The committed answer's
  2.24 is unchanged. A_fwd is still over-drawn under every estimator, so the open defect stands and
  is larger than recorded.
- **t9's "inert by construction" is no longer exact.** Causally, per-step and per-state still
  equal the raw chain total (62.50), but **per-metre reads 63.33, one pass above it**. The
  structural argument (every chain traversed identically over the windows the lock sees) was made
  at five windows; the causal lock sees three. Recorded, not chased: the arm is refused on (f)
  either way.
- **t6's ii_disp_prior_flat moved from 28.33 to 53.33.** The display-prior flattening was being
  judged mostly on the two lookahead windows. It is a diagnostic ablation and ships nothing.
- **t6's lock-wrong-commit-right count is 216, not 197.**
- **t9's sweep label was wrong.** It said w = 0 is the shipped lock; t9's sweep runs from the raw
  chain total to per-state normalisation. The numbers were always the raw chain total's. The label
  is corrected in the code.

## Where the numbers live

Causal: `runs/constrained/fh/{t6_lockdiag,t7_lockarms,t9_lengthnorm,y1_diag}/results.json`.
Lookahead, NON-CAUSAL, SUPERSEDED: `runs/constrained/fh/_LOOKAHEAD_superseded_2026-09-23c/`.
