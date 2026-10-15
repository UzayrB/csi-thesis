# Pre-registration: two no-retraining arms. Link fusion by product, and g100 at native resolution

**Written 2026-09-23 (batch 23c, item 3), before either arm has been built or run.** Operator
instruction 3, verbatim in the BRIEF: *"TWO NO-RETRAINING ARMS, pre-registered: (A) combine the
three link posteriors by renormalised product instead of arithmetic mean; (B) feed the g100 head to
the decoder at its native 0.5 m resolution instead of folding it to 25 cells, reporting the
along-line substitution ratio too. Correct any document that calls g100 a "gate head"."*

Both arms change the emissions, so both change the line decision and get the **full ship rule plus
(f), as written**. Nothing is retrained: every number comes from the posterior files already on
disk. Both run on the SHIPPED lattice (`runs/constrained/windows_half`); item 2's press-aligned
lattice is a separate question and is not mixed in.

---

## Arm A. Renormalised product of the three link posteriors

**Now:** each head fuses its three per-link posteriors by arithmetic mean, renormalised
(`nets.posterior_of`, "uniform decision-level averaging"). **Arm:** the renormalised product,
`p(c) proportional to p1(c) p2(c) p3(c)`, applied to every one of the five pool heads (the g100
head is fused at 100 cells and folded afterwards, as now). The per-link posteriors are stored in
every posterior file, so this is arithmetic on disk.

**The dial, for condition (c):** a log-linear blend of the two fusions,
`log p_w = (1 - w) log p_mean + w log p_product`, renormalised. w = 0 is the shipped pool exactly
(the stored fused posterior, not a recomputation); w = 1 is the pure product.

**Why it might matter:** a product rewards cells all three links agree on and punishes a cell any
one link rules out, which is what a mean cannot do. **Why it might hurt:** a product is
over-confident when the links are not independent, and three links seeing one person are not.
No prediction of sign is recorded; the size is expected to be small.

## Arm B. The g100 head at its native 0.5 m

**Now:** `g3_final.g100_to_25` sums each 2 by 2 block of the 10 by 10 grid onto the 5 by 5 grid
and the emission is built at 25 cells. **Arm:** the emission is built at 100 cells, each state
reading the 0.5 m cell it sits in, scaled by the head's own 100-cell training marginal
(`cell_marginal(xy, 100)`), same alpha. Only this one head of five changes.

**The dial:** `e_w = (1 - w) e_folded + w e_native` on the g100 head's log emission. w = 0 is
shipped exactly.

**Along-line substitution ratio, reported for both arms and binding for B:** on the locked line
after the lock, the same restricted along-line Viterbi is run on this pass's pool emission and on
the next recording's (another participant's radio), and `s2_display.substitution_on_arc` counts a
step as changed when the two decodes differ by more than one state spacing, against the ceiling
of steps whose two truths differ by that much. **Ratio = changed / ceiling.** A finer emission that
does not respond to the radio would show here first.

## What is measured, both arms

Nine pairings, session-01 folds shown, key `tag|session|stem|pass_id`, through one harness
modelled on `x2_edgepool`:

- **the 2 s lock at the causal horizon** (the render lock, `display_locked`, lag 2, delay 2.0);
- **the committed semi-bounded answer** (`final_line`), the 62.50 headline's quantity;
- edge recall E_col1 / E_col5 / E_row1 / E_row5 beside every pooled figure;
- decision substitution (`subs_end_changed`, `subs_line_changed`, partner = next recording);
- the along-line substitution ratio above.

**The lock-phase caveat applies to every lock figure here** (`reports/FINDING_lock_phase_2026-09-23.md`):
on the shipped lattice the lock's last window ends a median 0.218 s after the frame it is drawn
on. Both arms and the baseline share it equally, so the paired comparison is unaffected, and it is
stated rather than corrected, because correcting it is item 2's question.

## The rule, per arm, judged on the lock AND on the committed answer

**Reproduction check, voiding the run if it fails:** w = 0 must return the lock at **57.50
held-out, edge 42.593 / 77.778 / 35.185 / 57.407**, and the committed semi-bounded at **62.50** on
the median of nine.

An arm ships only if, on the quantity it is judged on, all of these hold:
(a) paired interval on the seven held-out folds entirely above zero; (b) median paired delta at
least two passes per pairing, compared as integers; (c) monotone response over w in
{0, 0.25, 0.5, 0.75, 1.0}; (d) decision substitution not worse than shipped by more than one pass
per pairing, and for B the along-line ratio not below shipped's; both causal bounds (the render's,
unchanged); **(f) no edge line degraded, as written, by even one pass.**

**It must also not degrade the other decision.** An arm that lifts the lock while costing the
committed answer a pass per pairing, or the reverse, does not ship; that is reported as a trade.

**Order, to save a sweep nobody needs:** w = 0 and w = 1 run first. The three intermediate weights
run only if w = 1 satisfies (a) and (b) on at least one of the two decisions; (c) cannot rescue an
arm that fails them. Recorded before the run, as `x2_edgepool` did.

---

## AMENDMENT 1, 2026-09-23 12:25, after arm A's w = 1 result and BEFORE the control below ran

**Stated plainly: this control was added after seeing arm A's w = 1 figures** (lock +9.29
[5.00, 13.69], committed +9.64 [2.14, 17.86], (f) failed on both). It changes no rule and cannot
make arm A ship; it only asks what the gain is made of, which decides how it is reported.

**The confound.** A product of three posteriors is far SHARPER than their mean. The null level
(-7.50 nats) and the gate were fitted to the MEAN's emission scale, so a sharper emission changes
the balance against those fixed constants whether or not the links carry agreeing information.

**Control T, tempered mean:** `p proportional to p_mean ** 3`, renormalised: the same three-factor
sharpening applied to the mean itself, so it carries NO cross-link agreement beyond the mean.
Run at w = 1 only, same harness, same baseline.

**Reading, fixed now:** if T recovers most of A's committed gain, A's effect is emission SCALE
against Room A's fitted constants, which is exactly what `ROOM_TRANSFER_AUDIT` marks as refit for
DC2, and it is reported that way. If T recovers little, the gain is the links agreeing, which is a
property of the sensing and more likely to transfer.
