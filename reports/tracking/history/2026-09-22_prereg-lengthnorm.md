# Pre-registration: length-normalised chain totals at the fixed 2 s lock

Written 2026-09-22, **before the arm was run**. Instruction 2 item 3 of
`reports/BRIEF_render_and_prepress_2026-09-22.md`. One arm, pre-registered, then measured.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes, and no rule of this pre-registration is edited**: the annotations are
> dated and sit beside the figures they correct.

## What is being tested

`t6_lockdiag` measured that the chains do not compete on equal terms:

| | straight lines | diagonals |
|---|---|---|
| states | 21 | **30** |
| length | 5.000 m | **7.071 m** |

and that under the shipped lock every diagonal is under-drawn (C_fwd 0.44, D_rev 0.45, D_fwd 0.51,
C_rev 0.61) while every edge line is over-drawn.

The arm: **score each chain by a length-normalised total rather than a raw sum**, cell marginal
KEPT, chain prior WITHHELD for the reason in `reports/PREREG_lock_2026-09-22.md`.

## The three normalisations, and an honest prediction about one of them

| arm | score |
|---|---|
| `N_per_step` | total divided by the number of windows |
| `N_per_state` | total divided by the number of distinct states the decoded path occupies |
| `N_per_metre` | total divided by the arc length the decoded path traverses |

**`N_per_step` is predicted NEARLY INERT, and the prediction is recorded here so the run can refute
it.** Every chain is scored over the same window range at the lock, so the divisor is the same
constant for all twelve and the argmax cannot move. The only reason it is not exactly inert is that
the entry term is divided along with the emissions, and the entry term does differ per chain. If it
moves the result by more than a pass or two, this reasoning is wrong and that is the finding.

`N_per_state` and `N_per_metre` are the ones that can actually change the ranking, because the
divisor differs across chains.

**Direction is not predicted.** Normalising by length penalises the chains that cover more ground,
and those are the diagonals, which are already under-drawn. So this may well make the bias worse.
The arm is run because the asymmetry is real and measured, not because the sign is known.

## The weight, for ship-rule condition (c)

`S_w(chain) = (1 - w) * raw_total + w * normalised_total`, swept at w in {0, 0.25, 0.5, 0.75, 1.0}.
At w = 0 this is the raw chain total, so the sweep runs through a known reference by construction.

## The rule, all conditions

Ships only if **all** hold, against the current shipped lock on the **held-out folds**:

- **(a)** paired improvement interval entirely above zero;
- **(b)** median paired delta at least two passes per pairing, 1.67 points at 120 passes;
- **(c)** monotone response in w;
- **(d)** substitution passes, ceiling from the actual pairs;
- **(f)** **edge-line recall not degraded**, reported per line, not pooled.

Judged on all nine pairings with the three session-01 folds shown. `s0102_to_s03` is the easiest
fold and is never the basis of a conclusion.

## If it is refused

**Write up the pooled-versus-edge-line trade-off as the finding**, with the E_col1 figures from
`t7_lockarms`: 50.0 percent under the shipped lock, 42.6 under the chain-total lock, 7.4 under
`E_both` and **1.9** under `E_no_marginal`. Change nothing. (Annotated 2026-09-23c: those are
NON-CAUSAL; **causally 42.59, 29.63, 0.00 and 0.00**.)
