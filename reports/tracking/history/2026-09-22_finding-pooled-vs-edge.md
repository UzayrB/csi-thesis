# The pooled-versus-edge-line trade-off at the 2 s lock

2026-09-22. Written because `reports/PREREG_lengthnorm_2026-09-22.md` said to write it if the arm
was refused, and it was. Nothing was changed as a result of this document.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes.**

---

## The finding in one line

**Every estimator that raises pooled line accuracy at the 2 s lock does so by degrading the edge
lines.** The shipped lock's over-drawing of E_col1, E_col5, E_row1 and E_row5 is not simply a
defect: it is what buys their recall. Correcting the bias trades that recall away.

## The evidence

Five estimators at a fixed 2 s lock, nine pairings, 1080 passes, nothing retrained.

**As first measured, NON-CAUSAL and SUPERSEDED** (reads 1.0 s past the lock):

| arm | held-out seven | **E_col1** | E_col5 | E_row1 | E_row5 | edge mean |
|---|---|---|---|---|---|---|
| **shipped lock** | 60.8 | **50.0** | 72.2 | 74.1 | 64.8 | **65.3** |
| chain-total lock | 73.3 | 31.5 | 66.7 | 51.9 | 46.3 | 49.1 |
| chain-total, prior withheld | 69.2 | 42.6 | 66.7 | 63.0 | 51.9 | 56.0 |
| **E_both**, +10.00 points pooled | 71.7 | **7.4** | 46.3 | 29.6 | 25.9 | 27.3 |
| **E_no_marginal** | 66.7 | **1.9** | 35.2 | 29.6 | 22.2 | 22.2 |

**CAUSAL, 2026-09-23c, the figures that stand** (reads `lo .. lo + step`, as the render does):

| arm | held-out seven | **E_col1** | E_col5 | E_row1 | E_row5 | edge mean |
|---|---|---|---|---|---|---|
| **shipped lock** | **57.50** | **42.59** | 77.78 | **35.19** | 57.41 | **53.24** |
| chain-total lock | 65.00 | 29.63 | 57.41 | 24.07 | 35.19 | 36.57 |
| chain-total, prior withheld | 62.50 | 42.59 | 70.37 | 29.63 | 46.30 | 47.22 |
| **E_both** | 63.33 | **0.00** | 27.78 | 5.56 | 5.56 | 9.72 |
| **E_no_marginal** | 59.17 | **0.00** | 35.19 | 9.26 | 7.41 | 12.96 |

**E_col1 falls from 50.0 percent to 1.9** (NON-CAUSAL; **causally from 42.59 to 0.00**). An arm
that gains 4.2 points pooled (causally **+1.67 [-0.95, 5.60]**) answers E_col1 correctly on one
pass in fifty (causally on **none**).

## Why it happens

The four E lines run along the grid edges, and the cells they occupy hold **0.6 to 1.0 percent** of
the training marginal against **16.5 percent** at the centre. `scaled_cell_emission` divides by
that marginal, so edge-line states are boosted by roughly 3 nats. The lock over-draws them:
measured drawn-over-true ratios of E_col5 2.94, E_col1 1.98, E_row1 1.80, E_row5 1.65.

That over-draw is a **precision-recall trade made by the emission, not by the decoder**. Drawing an
E line too readily costs precision on the eight other lines and buys recall on the four E lines.
Removing the division, or replacing the estimator with one that weighs chains more evenly, recovers
the precision and surrenders the recall.

**The edge lines are the ones with least data**: the protocol walks each of them 6 times per 120
passes against 12 for each of the other eight. The quantity that props them up is the same quantity
the room-transfer audit flags as Room-A-fitted.

## What the ship rule did

Condition (f), edge lines not degraded, refused all four arms. **Without it, `E_both` would have
shipped at +10.00 points paired, interval [2.02, 11.55], substitution passing, monotone in its
weight.** It clears (a), (b), (c) and (d) cleanly. Only (f) stops it.

This is the second time in two days that a condition added after seeing a previous failure has
caught the next one. Condition (b), two passes per pairing, was added on 2026-09-22 after an arm
cleared an interval test on a five-pass effect; condition (f) then caught an arm that cleared (a),
(b) and (c).

## Why length normalisation could not help, which is exact rather than empirical

`t9_lengthnorm` tested per-step, per-state and per-metre normalisation. All three were **inert**,
returning 69.17 on the held-out folds against the raw chain total's 69.17 (NON-CAUSAL; **causally
62.50, 62.50 and 63.33 against 62.50**, so per-metre is one pass off inert at the causal horizon,
where the lock sees three windows rather than the five below).

The reason is structural and was measured directly: at the lock, **every chain is traversed
identically**. Over the 5 windows the lock sees, the within-chain Viterbi advances the same number
of states on all twelve chains, because the step model inside a chain is the same everywhere:

| | every one of the twelve chains |
|---|---|
| windows scored | 5 |
| distinct states occupied | 5 |
| arc length traversed | 3.00 m |

The 21-versus-30 state asymmetry between straight lines and diagonals is a property of the
**whole** chain. The lock never sees the whole chain, so there is no length asymmetry for a
length normalisation to correct. The arm is inert by construction, not by underperforming.

## What this means for the trade-off

The trade is real and it is not obviously resolvable at the lock:

- **Keep the shipped lock** and accept 60.8 percent pooled with edge recall at 65.3
  (NON-CAUSAL; **causally 57.50 with edge recall 53.24**).
- **Take the estimator fix** and get 69.2 to 73.3 pooled with edge recall at 49.1 to 56.0
  (NON-CAUSAL; **causally 62.50 to 65.00 with edge recall 36.57 to 47.22**).

Which is better depends on what the edge lines are worth, and that is not a question the pooled
figure can answer. The project's standing rule is that edge-line recall is reported beside every
pooled figure precisely because a pooled number hides this.

**No arm is recommended.** The trade-off is stated so the operator can decide whether edge-line
recall is worth 8 to 12 points of pooled accuracy, which is a judgement about what the system is
for and not a measurement.

## THE OPERATOR'S DECISION, 2026-09-22: KEEP THE SHIPPED LOCK

**Decided by the operator. The shipped lock stands and no estimator arm ships.** The grounds, as
given:

1. **The 2 s lock only decides the DRAWN line.** The committed headline of 62.50 percent is
   produced by the full-walk answer and is unaffected by any of these arms, so what is at stake is
   what the viewer watches and not what the system scores.
2. **The estimator's gain comes from the least transferable component.** It works by shifting
   probability away from lines whose training-cell mass reflects Room A's capture design. The
   25-cell marginal is exactly what `reports/ROOM_TRANSFER_AUDIT_2026-09-22.md` classes as
   REFIT-for-DC2, so a gain drawn from it is a gain least likely to survive the room change that
   the thesis claim rests on.
3. **Condition (f) was pre-registered.** Taking the estimator now, after seeing that it clears
   (a), (b), (c) and (d) and fails only (f), would be a **post hoc override** of a rule written
   before the arms ran. The project refused exactly that move on 2026-09-22 over a five-pass
   effect, and the reasoning does not change because this effect is larger.
4. **E_col1 drawn right on 1.9 percent of walks fails visibly in the demonstration.** (NON-CAUSAL;
   **causally 0.00 percent** under E_no_marginal and under E_both.) A pooled
   figure can absorb that; six videos cannot. An arm that is almost never right about one of the
   twelve lines is worse to watch than an arm that is moderately right about all of them.

**How the estimator arms are reported from here.** As **ablations**, beside the edge-line figures,
never as candidate configurations. They are evidence about where the lock's accuracy comes from,
which is a finding; they are not a shortlist.

## What would actually resolve it, and is not proposed here

The edge lines are under-sampled by the protocol, 6 passes per 120 against 12. A protocol that
sampled all twelve lines equally would remove the marginal asymmetry at its source rather than
compensating for it in the emission. `reports/DC2_PROTOCOL_2026-09-18.md` already asks for the edge
lines to be deliberately over-sampled, for a different reason, and that item is now doubly
justified.

## Where the numbers live

`runs/constrained/fh/t7_lockarms/results.json`, `runs/constrained/fh/t9_lengthnorm/results.json`,
`runs/constrained/fh/t6_lockdiag/results.json`. Pre-registrations:
`reports/PREREG_lock_2026-09-22.md`, `reports/PREREG_lengthnorm_2026-09-22.md`.
