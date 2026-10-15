# PRE-REGISTRATION: the estimator prize at the 2 s lock. ONE dial

**Written 2026-09-23, before the arm was built and before any number in it was seen.** Item 2 of
the operator's batch of 2026-09-23. The ship rule is `reports/SEMIBOUNDED_STATE.md` section 10,
conditions (a), (b) and (c), plus substitution, both causal bounds, and **(f) no edge line
degraded**.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes, and no rule of this pre-registration is edited.**

---

## 1. What is being attempted, in the operator's words

> THE ESTIMATOR PRIZE. The chain-total lock gave +12.5 held-out but took E_col1 from 50.0 to 7.4.
> Find a version that keeps the gain without the edge cost, using ONE dial chosen on the selection
> folds: e.g. a mix between best-path and chain-total scores, or a tempered cell-marginal exponent.

## 2. WHICH LOCK. This is settled first, because two different quantities carry the name

There are **two** estimators in this repository called "the 2 s lock", and they disagree by up to
39 points on a single line. `y1_diag` and `y1b_locksrc` measured both on 2026-09-23:

| quantity | pooled | E_col1 | E_col5 | E_row1 | E_row5 | A_fwd drawn/true |
|---|---|---|---|---|---|---|
| **Viterbi proxy** (`t6_lockdiag.viterbi_state_line`) | 49.54 | **50.0** | 72.2 | **74.1** | 64.8 | 1.954 |
| **render display lock** (`night_arms` `display_locked`) | 47.87 | 42.6 | 77.8 | **35.2** | 57.4 | 2.620 |

**This arm is judged on the VITERBI PROXY**, and the reason is not preference. Every number the
operator's instruction quotes for item 2 is in that convention and only in that convention:
`reports/FINDING_pooled_vs_edge_2026-09-22.md` records the shipped lock at **60.8 held-out with
E_col1 at 50.0**, the chain-total lock at **73.3**, and `E_both` taking E_col1 to **7.4**. Those
are the proxy's numbers to the decimal. Judging the arm on the render lock would be judging it
against a baseline the target was never measured on.

**The render lock is a separate defect and is handled separately.** `y1b_locksrc` found that it
falls back to `st.names[0]`, which is `A_fwd`, whenever its free display path is off-chain at the
lock step. That is a per-line bias by alphabetical order. It is item 1's finding, it is reported
there, and **it is not fixed inside this arm**: mixing two estimators and repairing a name-order
fallback in one change would make neither attributable.

## 3. THE DIAL ALREADY EXISTS AND HAS ALREADY BEEN SWEPT ONCE. This is a refinement

**Recorded first, because it changes what item 2 is.** The operator's instruction says the prize is
untried: "Nobody has tried to take the +12.5 without paying the edge lines." That is not quite the
state of the evidence. `t7_lockarms` (2026-09-22) already implements exactly the mix the
instruction proposes, as its `W_*` arms, and already swept it at five weights:

```
  V(c) = viterbi_chain_scores(...)   best forward-path score among chain c's states. argmax IS
                                     the shipped lock: W_0.0 reproduces it to the decimal
  T(c) = chain_scores(..., chain_logprior=None, start_adj=adj)    chain total, PRIOR WITHHELD
  score(c) = (1 - w) * norm(V)(c) + w * norm(T)(c)                argmax over the twelve chains
```

The measured sweep, held-out seven, edge-line recall beside it, from
`runs/constrained/fh/t7_lockarms/results.json`:

| w | held-out 7 | E_col1 | E_col5 | E_row1 | E_row5 | edge mean | substitution |
|---|---|---|---|---|---|---|---|
| **0.00 = shipped** | **60.83** | **50.00** | 72.22 | 74.07 | 64.81 | 65.28 | 0.971 |
| **0.25** | **67.50** | **46.30** | 72.22 | 74.07 | 64.81 | 64.35 | 0.934 |
| 0.50 | 69.17 | 44.44 | 68.52 | 66.67 | 62.96 | 60.65 | 0.879 |
| 0.75 | 69.17 | 44.44 | 68.52 | 66.67 | 61.11 | 60.19 | 0.823 |
| 1.00 | 69.17 | 42.59 | 66.67 | 62.96 | 51.85 | 56.02 | 0.752 |

The table above is **NON-CAUSAL and SUPERSEDED**. The same sweep from `t7_lockarms` re-run at the
causal horizon on 2026-09-23c:

| w | held-out 7 | E_col1 | E_col5 | E_row1 | E_row5 | edge mean | substitution |
|---|---|---|---|---|---|---|---|
| **0.00 = shipped** | **57.50** | **42.59** | 77.78 | 35.19 | 57.41 | 53.24 | 0.941 |
| **0.25** | **62.50** | 42.59 | 79.63 | 33.33 | 57.41 | 53.24 | 0.862 |
| 0.50 | 63.33 | 42.59 | 72.22 | 33.33 | 57.41 | 51.39 | 0.787 |
| 0.75 | 63.33 | 42.59 | 72.22 | 33.33 | 51.85 | 50.00 | 0.719 |
| 1.00 | 62.50 | 42.59 | 70.37 | 29.63 | 46.30 | 47.22 | 0.658 |

Causally, w = 0.25 degrades E_row1 by one pass and gains E_col5 one pass, not E_col1 by two.

**Read what w = 0.25 actually does.** It gains **+6.67 points** held-out, and it degrades **exactly
one edge line, E_col1, by 3.70 points, which is 2 passes of 54**. E_col5, E_row1 and E_row5 are
**untouched, to the decimal**. That is most of the way to the prize for two passes of one line,
and it is nothing like the wholesale edge collapse of `E_both` or `E_no_marginal`.

So the prize is not untried. It is **bracketed**, and the unexplored interval is **between 0 and
0.25**, which no sweep has ever visited.

## 4. THE REFINEMENT, and its POST HOC disclosure

> **THIS RANGE WAS CHOSEN AFTER SEEING HELD-OUT NUMBERS, AND THAT IS POST HOC. Recorded in those
> words.** The interval 0 to 0.25 is where it is because `t7`'s held-out sweep, which I read before
> writing this, shows the gain arriving by w = 0.25 while three of the four edge lines are still
> exactly intact. No selection-fold-only argument would have located it. The consequence is that
> **the held-out figures this arm produces are no longer fully naive**, and any result it returns
> is reported with that attached rather than as a clean out-of-sample number.

The sweep: **w in {0.00, 0.05, 0.10, 0.15, 0.20, 0.25}**, six values, no more, no second pass.

**The choice rule, fixed here before running:** on the **selection folds only**
(`s01_to_s02`, `s02_to_s01`), take the **largest w whose edge-line recall is at or above the
shipped lock's on ALL FOUR edge lines, compared as integer passes**. If that rule returns w = 0,
the arm is REFUSED and no held-out figure is quoted as a candidate. The chosen w is then evaluated
**once** on the seven held-out pairings.

**Why the largest rather than the best.** The pooled figure rises with w and the edge lines fall
with it, so "best pooled subject to the edge constraint" and "largest w satisfying the edge
constraint" are the same rule; stating it as the latter removes any freedom to pick on the pooled
number after the fact.

## 4b. AMENDMENT, 2026-09-23 09:26, BEFORE THE SWEEP RAN. The baseline moves

`y2a_causal` was written to gate this arm and it did. **The estimator every figure in sections 3
and 4 is quoted in reads 1.0 s of radio that has not finished recording at the lock.** See
`reports/FINDING_two_locks_2026-09-23.md`. At the causal horizon:

| | as quoted | causal |
|---|---|---|
| shipped lock, held-out 7 | 60.83 | **57.50** |
| chain-total lock, held-out 7 | 73.33 | **65.00** |
| the prize | +12.50 | **+7.50** |
| E_col1 under the shipped lock | 50.00 | **42.59** |

**THIS ARM IS JUDGED AT THE CAUSAL HORIZON.** Its baseline is 57.50 held-out with edge recall
42.59 / 77.78 / 35.19 / 57.41, which is what the demonstration actually draws. Section 2's choice
of "the Viterbi proxy" is superseded: the proxy and the render lock are the SAME estimator, and
the horizon rather than the estimator was the difference. Condition (f) is measured against the
causal edge figures.

The sweep, the six weights and the selection rule in section 4 are otherwise unchanged.

## 5. The ship rule, all of it. This arm changes the line decision

| condition | bar |
|---|---|
| (a) | paired improvement interval on the **held-out folds** entirely above zero |
| (b) | median paired delta **at least two passes per pairing**, compared as **integer passes** (120 passes a pairing, so one pass is 0.8333 points) |
| (c) | **non-flat, monotone response to `lam`**, read on the **median paired delta anchored at `lam` = 0**, the same quantity (a) and (b) use. An interior optimum is permitted only because `lam` was selected on the selection folds, which it is |
| substitution | another participant's CSI must change the arm's answers. Coverage and exit codes prove nothing |
| causal bounds | both, the drawn-window bound and the evidence bound |
| **(f)** | **no edge line degraded**: E_col1, E_col5, E_row1, E_row5 each at or above the shipped lock's pooled recall, compared as integer passes (54 true passes each, so one pass is 1.8519 points) |

**Reported with every figure:** all nine pairings, the three session-01 folds shown explicitly,
and edge-line recall beside every pooled number. **`s0102_to_s03` is never the basis of a
conclusion**: it is the easiest of the nine.

## 6. What I expect, recorded so the run can refute it

**I expect this arm to be REFUSED**, and the reason is in the finding it comes from: every
estimator measured so far that raises pooled accuracy at the lock does it by moving probability
away from the edge lines, and `lam` interpolates between exactly two such estimators. If the
trade-off is smooth in `lam`, then every `lam > 0` buys pooled accuracy with edge recall and the
selection rule in section 4 returns `lam = 0`.

**The arm is worth running anyway, and this is why.** The claim "the trade-off is smooth" has
never been measured; only the two endpoints have. A non-monotone middle, where the two opinions
disagree most on the walks the best-path estimator gets wrong for reasons unrelated to the
marginal, is a real possibility and it is cheap to test. **If it comes out flat or monotone, the
finding is written up as a measured negative and nothing changes**, exactly as
`reports/PREREG_lengthnorm_2026-09-22.md` was.

## 7. What would make this arm INVALID rather than merely refused

Recorded in advance so it cannot be explained away afterwards:

- any per-line term, offset, prior or threshold indexed by line name and fitted to Room A counts.
  `y1_diag` produced exactly such a table and it is MECHANISM only;
- `lam` chosen, or the choice rule changed, after seeing held-out numbers;
- the endpoints failing to reproduce the arms they claim to be: **`lam = 0` must return the
  shipped lock's figures and `lam = 1` the chain-total-prior-withheld figures, to the pass.** This
  is a reproduction check and it runs first. If either endpoint disagrees, the stage stops and
  reports the disagreement rather than the sweep;
- a missing measurement scored as a pass. A null substitution result is a FAILURE, not a pass; the
  2026-09-23 batch had to fix exactly that.

## 8. Where it will be written

`pipeline/constrained/y2_dial.py`, results `runs/constrained/fh/y2_dial/results.json`,
log `runs/constrained/logs/y2_dial.log`. Nothing in `pipeline/identify/` or `runs/identify/` is
read or written: a second session owns those.
