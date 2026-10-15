# PRE-REGISTRATION: mid-walk switching. Amends rule 1 only if it passes

**Written 2026-09-23, before the stage was built and before any switching number existed.** Item 3
of the operator's batch of 2026-09-23.

---

## 1. The operator's specification, verbatim

> MID-WALK SWITCHING, amends rule 1 only if it passes. Measured against whatever lock ships after
> item 2. After the 2 s lock the drawn line may change at most twice per walk (test max 1 and max
> 2), only when another line's running decode margin exceeds a threshold chosen on the selection
> folds, and never once the dot is within the final 1.0 m of the locked line. A decision at display
> time t may use radio up to t + 2.0 s, never beyond. On a switch the dot moves to the decoder's
> position on the new line, and the switch is marked on screen. Measure time-on-correct-line
> against lock-final, switches wrong-to-right against right-to-wrong, and switches per walk. Keep
> it only if time-on-correct-line improves with the held-out interval above zero AND wrong-to-right
> exceeds right-to-wrong by at least two passes per pairing. Either way, show the whole-walk
> committed line as on-screen text at each walk's end.

## 2. The baseline, and it is not the one the batch started with

**Item 2 shipped nothing**, so the baseline is the lock as it stands. That lock is the renderer's
own, and `reports/FINDING_two_locks_2026-09-23.md` establishes what it actually reads:

| | held-out 7 | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|
| **the shipped render lock, causal** | **57.50** | 42.59 | 77.78 | 35.19 | 57.41 |

**Not 60.83 and not E_col1 50.0.** Those are the lookahead horizon's figures and no live display
can produce them. Every comparison in this arm is against 57.50 and the causal edge figures.

## 3. What rule 1 currently forbids, and what would be amended

`reports/RENDER_RULES.md` rule 1: "Once the displayed line locks at the commit delay, it NEVER
changes for the rest of the walk." Enforced by
`test_the_locked_line_never_changes_after_the_lock`.

**Rule 1 is amended ONLY if this arm passes section 6.** If it does not, the rule stands unchanged
and the test stands unchanged. **The test is not weakened in advance to let the arm run**: the arm
is measured in a stage, not by relaxing the contract and re-rendering.

Rules NOT touched, whatever this arm does: **V1** (2.0 s latency), **V2** (commit and marker are
one event), **V3** (the lock time is structural and identical on every walk). **A switch is not a
delayed lock.** The lock still happens at press + 2.0 s on every walk; what is at issue is whether
the drawn line may be revised afterwards. A confidence-gated LOCK TIME remains forbidden by V3 and
nothing here proposes one.

## 4. The arm

At each display step after the lock, with `L` the currently drawn line:

```
  margin(t) = max over chains c != L of [ running_score(c, t) - running_score(L, t) ]
  switch to argmax c   iff   margin(t) > theta
                       and   switches_so_far < K
                       and   the dot is NOT within the final 1.0 m of L
```

- `running_score(c, t)` is the chain total over the windows available at display time `t`, by the
  same `chain_scores` the committed answer uses, **prior withheld**, so the switch decision and
  the committed answer are the same kind of quantity.
- **K in {1, 2}**, both measured, as the operator asked.
- **theta chosen on the SELECTION FOLDS ONLY** (`s01_to_s02`, `s02_to_s01`), swept over
  {0.5, 1.0, 1.5, 2.0, 3.0} nats, and the chosen theta is then evaluated once on the held-out
  seven. If no theta satisfies section 6 on the selection folds, the arm is REFUSED.
- **On a switch the dot moves to the decoder's position on the new line.** It is not interpolated
  across and it is not projected: it is the decoded position on the new chain at that step, so
  rule 2 holds. The jump is a jump and rule 5 counts it among the jumps over 0.5 m.
- **The switch is marked on screen.**

### THE CAUSAL BOUND, which is the constraint most likely to be violated silently

**A decision at display time `t` may use radio up to `t + 2.0 s` and never beyond.** In window
indices, at display step `i` the decision may read windows up to `i + (2.0 / STRIDE) - LAG_W`,
which is the same horizon the lock itself is held to and the same one
`FINDING_two_locks_2026-09-23.md` had to establish. **The stage asserts this per switch and
reports both bounds per rule 5**, and a missing bound is a FAILURE, not a pass.

## 5. What is measured

| quantity | definition |
|---|---|
| **time on correct line** | fraction of drawn frames after the lock whose drawn line is the true line. The primary measure |
| switches wrong to right | a switch whose new line is the true line and whose old line was not |
| switches right to wrong | a switch whose old line was the true line and whose new line is not |
| switches per walk | mean and distribution, with the K cap shown to be binding or not |
| final drawn line accuracy | for comparison with lock-final, since a switch changes what the walk ends on |

Reported over **nine pairings with the session-01 folds shown**, with **edge-line recall beside
every pooled figure**, and `s0102_to_s03` is never the basis of a conclusion.

## 6. The keep rule, exactly as the operator set it

**Both, not one:**

- **time on correct line improves, with the held-out paired interval entirely above zero**; and
- **wrong-to-right exceeds right-to-wrong by at least two passes per pairing**, compared as
  **integer passes** (120 passes a pairing).

Plus, because this changes what is drawn: **substitution** (another participant's CSI must change
the switching decisions), **both causal bounds**, and **(f) no edge line degraded** against the
causal baseline in section 2.

## 7. The part that happens either way

> "Either way, show the whole-walk committed line as on-screen text at each walk's end."

**This is display-only and is NOT conditional on the arm.** It gets the lighter treatment the
standing rules give display changes: contract checks plus one measurement. It is compatible with
rule 1 as it stands, which already says the committed answer "is shown on screen as text, as an
answer. It is never shown by moving the dot." **This makes the rule's existing allowance real
rather than notional.**

## 8. What I expect, recorded so the run can refute it

I expect **time on correct line to improve and the wrong-to-right balance to be the condition that
refuses it**. The lock is wrong on about 42 percent of walks at the causal horizon and the
committed answer recovers many of them, so there is real room to move; but `t6`'s probe showed the
chain-total posterior is already led by the true line at 2.0 s on only about half the walks it
eventually gets right, so early switches will fire on evidence that is not yet settled and some
will fire the wrong way.

## 9. What would make this INVALID rather than refused

- a switch reading radio beyond `t + 2.0 s`;
- `theta` or `K` chosen after seeing held-out numbers;
- rule 1's test weakened before the arm has passed;
- the dot placed anywhere that is not a decoded position on the new line;
- a missing measurement scored as a pass.

## 10. Where it will be written

`pipeline/constrained/y3_switch.py`, results `runs/constrained/fh/y3_switch/results.json`,
log `runs/constrained/logs/y3_switch.log`. Nothing in `pipeline/identify/` or `runs/identify/` is
read or written.

## 11. AMENDMENT, 2026-09-23 (batch 23c), written before `y3_switch` first ran

Dated and labelled, and written before any switching number exists. The operator re-issued this
item as item 4 of batch 23c: *"MID-WALK SWITCHING (old item 3), demonstration quality only,
against the causal 57.50 baseline: at most 2 switches, none in the final 1.0 m, decisions using
radio to t + 2.0 s only. Keep it if time-on-correct-line improves (held-out interval above zero)
and wrong-to-right switches exceed right-to-wrong by at least two passes per pairing. Show the
committed line as text at walk end."* The specification is unchanged from sections 1 to 10. What
this amendment fixes is how each clause is measured, where the text above left room:

1. **The causal bound is WALL-CLOCK, not window arithmetic.** Section 4's index form
   (`i + 2.0 / STRIDE - LAG_W`) assumes the lock window is named at the press, and
   `reports/FINDING_lock_phase_2026-09-23.md` found that on the shipped lattice it is not: the
   shipped lock reads a median 0.218 s past its own frame. So a switch decision takes effect at
   video frame `x_k = press + 2.0 + k * 0.5 s`, k >= 1, and reads only windows with
   `t_start + 2.0 <= x_k`. The worst value of `t_start + 2.0 - x_k` over every decision is reported
   and must be <= 0. **The lock itself is the shipped one, unchanged**, because it is the
   baseline; its own phase leak is item 2's question and is stated, not corrected, here.
2. **"The dot is in the final 1.0 m"** is read from the decoded position on the drawn line at the
   decision, the end state of the same within-chain Viterbi over the same windows.
3. **Time on correct line** counts every frame from the lock frame (press + 2.0 s) to the end press
   + 2.0 s at 10 fps. Lock-final scores 100 or 0 per walk on the same frames.
4. **Selection with two folds.** An interval over two folds means nothing, so on the selection
   folds a theta qualifies if the mean time-on-correct delta is above zero AND the median of
   (wrong-to-right minus right-to-wrong) over the two is at least 2. The qualifying theta with the
   largest selection delta is chosen, ties to the larger theta. None qualifying: REFUSED for that K.
5. **Held-out seven, once per K:** (i) the bootstrap interval of the seven per-pairing
   time-on-correct deltas entirely above zero; (ii) the median over the seven of (wrong-to-right
   minus right-to-wrong) at least 2, as integers.
6. **Substitution:** the same decisions are recomputed on the next recording's radio with this
   pass's lock, entry prior and start term. Over held-out passes that switch at all, the share
   whose switch sequence changes, divided by the share of passes whose partner walked a different
   line, must be at least 0.5.
7. **(f):** the line drawn at walk end, against the lock, per edge line over nine pairings, in
   passes. Any edge line losing a pass refuses the arm.
8. **K:** both measured. If both pass, the larger held-out time-on-correct gain is kept, ties to
   K = 1.
9. **The committed line as text at walk end** is display-only and happens either way (section 7).
   The render already printed the committed answer when it DISAGREED with the lock; it now names
   the committed line on every walk. Checked by a contract test, rendered once at batch end.
