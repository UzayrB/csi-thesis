# Pre-registration: improving the line decision at a FIXED 2 s lock

Written 2026-09-22, **before any arm below was run**, after `t6_lockdiag` and before `t7_lockarms`.
Part 1 step 3 of the operator's instruction of 2026-09-22.

**The lock time cannot move.** Rule V3 of `reports/RENDER_RULES.md` fixes it as structural and
identical on every walk, and forbids confidence-gated or variable latency. So every gain here must
come from **better use of the same 2 s of evidence**, never from waiting longer.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes, and no rule of this pre-registration is edited**: the annotations are
> dated and sit beside the figures they correct.

---

## What Step 2 established

`runs/constrained/fh/t6_lockdiag/results.json`, nine pairings, 1080 passes, nothing retrained.
The stage reproduces the shipped committed figure exactly, 62.5 percent over all nine, which is
the check that it is measuring the right object.

| arm at the 2 s lock | all nine | held-out seven, NON-CAUSAL | **held-out seven, causal (23c)** | bias spread, NON-CAUSAL |
|---|---|---|---|---|
| **shipped lock** | 49.2 (causal **49.17**) | 60.8 | **57.50** | 2.50 (causal **2.37**) |
| (i) no cell-marginal division | 58.3 (causal **56.67**) | 68.3 | **58.33** | 1.87 |
| (ii) display prior flattened | 22.5 (causal **45.00**) | 28.3 | **53.33** | 3.63 |
| (v) emission-only argmax | 28.3 (causal **25.83**) | 30.0 | **29.17** | 3.65 |
| **(vi) chain-total lock** | 55.8 (causal **54.17**) | 73.3 | **65.00** | 2.29 |
| (vi) minus the chain prior | 55.0 (causal **46.67**) | 69.2 | **62.50** | 2.29 |
| (vi) minus the A2 term | 54.2 (causal **54.17**) | 61.7 | **60.00** | 1.82 |
| committed answer, whole walk | 62.5 | 75.0 | 75.0, not a lock | 1.67 |

**Two causes, both room-agnostic mechanisms.**

**1. The estimator.** The lock takes the single best-path STATE of a Viterbi and reports its chain;
the committed answer scores each chain and adds the chain prior and the A2 term. On the same 2 s of
evidence, swapping estimator is worth **+12.5 points on the held-out folds** and lands 1.7 points
short of the full-walk answer. Neither the chain prior nor A2 reaches the shipped lock at all,
which is why ablating them against it would have been vacuous and why they were ablated against
arm (vi) instead.

**2. The cell-marginal division over-boosts the edge lines.** Measured drawn-over-true ratios under
the shipped lock: **every E line is over-drawn** (E_col5 2.94, E_col1 1.98, E_row1 1.80, E_row5
1.65) and **every diagonal is under-drawn** (C_fwd 0.44, D_rev 0.45, D_fwd 0.51, C_rev 0.61). The
E lines run along the grid edges, whose training marginal is 0.6 to 1.0 percent against 16.5 at the
centre, so dividing by it boosts edge-line cells by roughly 3 nats. Removing the division is worth
+7.5 points and takes the bias spread from 2.50 to 1.87.

**Chains do not compete on equal terms**: 21 states over 5.0 m for the straight lines, 30 over
7.071 m for the diagonals. Recorded as measured; it is not the cause of the direction of the bias,
since the longer chains are the under-drawn ones.

**What Step 2 did NOT explain, stated rather than invented.** A_fwd is over-drawn at 1.95 (NON-CAUSAL; **2.61 causally**) under
every estimator including the committed answer at 2.24, and no ablation moves it. It is not the
marginal and not the estimator. This pre-registration does not propose a cause for it.

---

## The arms

All at a **fixed 2 s lock**. No retraining. Nothing per-line fitted to Room A is introduced.

| arm | what changes | why it follows from Step 2 |
|---|---|---|
| `shipped` | nothing | the incumbent |
| `E_chain_total` | the lock reads chain totals instead of the Viterbi best-path state | cause 1 |
| `E_no_marginal` | the lock reads the unscaled emission, alpha 0 | cause 2 |
| `E_both` | both | both |
| `E_chain_total_no_prior` | chain totals, chain prior withheld | see the note below |

### The chain prior is withheld from the headline arm, deliberately

`fit_chain_prior` penalises the four E lines by exactly **log 2**, because the Room A protocol
walks each of the other eight twice as often. `reports/ROOM_TRANSFER_AUDIT_2026-09-22.md` classes
it as REFIT-or-drop for DC2.

Using it in the display would import a **per-line prior fitted to Room A's counts** into the thing
the viewer watches, which is what the operator's generalisation constraint forbids in substance
even though the prior is fitted to the protocol's sampling design rather than to drawn-versus-true
counts. It is worth about 4 points at the lock, so this is a real cost, paid on purpose.

**`E_chain_total_no_prior` is therefore the arm that may ship. `E_chain_total` is reported beside
it as the measurement of what the prior is worth, and does not ship.**

### The weight, for ship-rule condition (c)

The two estimators are blended so the arm has a weight to respond to:

> `S_w(chain) = (1 - w) * V(chain) + w * T(chain)`
> where `V(chain)` is the best forward path score among that chain's states at the lock step, and
> `T(chain)` is that chain's total over the windows available at the lock.

At **w = 0** this is the shipped lock exactly, and at **w = 1** it is the chain-total lock.
Swept at **w in {0, 0.25, 0.5, 0.75, 1.0}**. Condition (c) requires the response to be monotone
across that sweep.

---

## The ship rule, all conditions

An arm ships only if **all** of these hold:

- **(a)** its paired improvement interval on the **held-out folds** is entirely above zero;
- **(b)** the median paired delta is at least **two passes per pairing**, 1.67 points at 120 passes;
- **(c)** the effect is **monotone in w** across the sweep;
- **(d)** substitution passes, under the generalised rule with the ceiling computed from the actual
  pairs;
- **(e)** both causal bounds hold, the drawn-window bound and the evidence bound;
- **(f)** **edge-line recall is not degraded.** E_col1, E_col5, E_row1 and E_row5 are reported
  individually beside every pooled figure, and an arm that raises the pooled figure by lowering an
  edge line does not ship.

**Judged on all nine pairings, with the three session-01 test folds shown explicitly.** The
demonstration pairing `s0102_to_s03` is the easiest fold and is never the basis of a conclusion.
"Either drawn or committed right" is an after-the-fact oracle and is not quoted as headroom.

### The session-01 warning, recorded in advance

Arm (vi) was **worse** than the shipped lock on two of the three session-01 folds in Step 2:
25.0 against 28.3 on `s02_to_s01`, and 25.8 against 34.2 on `s0203_to_s01`. If that pattern holds
under the paired test the arm may still clear conditions (a) and (b) on the held-out seven while
being a regression on the hardest fold. **That is reported as a split whatever the verdict**, and
it is the reason the per-fold table is a deliverable rather than a courtesy.

## If nothing ships

The render changes for the dwell cut and V1 to V4 only, the headline does not move, and the
diagnosis is written up as the finding.
