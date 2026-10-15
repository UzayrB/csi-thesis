# Pre-registration: the pre-press region reader, version 2

Written 2026-09-22, **before any arm below was run**. Part 2 of
`reports/BRIEF_render_and_prepress_2026-09-22.md`, with the operator's amendments of 2026-09-22
folded in and marked.

---

## What is already established, and is NOT re-run

`reports/PREPRESS_REGION_REPORT_2026-09-21.md`. None of this is measured again:

| | |
|---|---|
| oracle ceiling | **+12.5 points**, CI [9.5, 26.2] |
| break-even, where a region term stops costing line accuracy | **about 74 percent** |
| best reader built | **40.0 percent** (arm C), and that was class collapse, W_mid at 0.9 |
| edge midpoints | about 60 percent readable |
| corners | at chance, and corners are where three lines share a start |
| substitution | 0.89 to 0.95, so the reader reads radio and not a clock |
| through the decoder | five passes in 840, no weight response |
| **the obstacle** | **cross-session generalisation**: 47 to 57 percent testing on 02 or 03, **16 to 18 testing on 01** |

**Why it still matters.** Under rule V3 the lock cannot wait longer, so evidence from before the
press is the only additional evidence that costs no latency.

**The question has changed.** Not "read the region accurately" but **"use a weak reader in a way
that cannot harm"**.

---

## Arm (d) IS A PILOT IN ROOM A, and that is stated before it runs

**Operator amendment, 2026-09-22.** Item 1 (`t8_calib`) measured that the only per-session anchor
Room A offers, the pre-press setup period, **varies 2.3x across three days in the same room**, and
that this alone was enough to make the relative gate and null scatter **3.33 points per pairing**
against a 0.833 bar. Arm (d) adapts from the same kind of data.

**Therefore arm (d) is a pilot.** It can show that causal per-session adaptation helps. It cannot,
on Room A, show that it does not, because Room A's anchor may be too unstable to carry it.

> **A null result in arm (d) is recorded as "UNTESTABLE WITH ROOM A'S ANCHOR", never as
> "adaptation does not work".** Those are different claims and only the first is supported by a
> negative here.

### The anchor: checked before the pre-registration was finalised

| | found |
|---|---|
| idle windows recorded before the first press of each recording | **yes**: 544, 174 and 169 per session for 01, 02, 03 |
| empty-room baseline captures | **yes**, one per session, but raw CSI that this batch does not window |
| windows in that period belonging to pass 1's own run-up | 24 per session, mode `walk_edge` |

**The anchor is the `idle` windows before the first press, with the 24 `walk_edge` windows
EXCLUDED.** Those 24 end before the press and so are causally legal, but they are the first
evaluated pass's own run-up, and the operator's rule is nothing from the evaluated passes. This is
a refinement on `t8_calib`, which included them.

**The instability is stated rather than discovered later**: session 01 offers 544 idle windows
against 169 and 174 for the other two, and the sessions' median band energies are 0.378, 0.875 and
0.491. The anchor is not of equal quality across days.

### AdaBN is available: checked, not assumed

`pipeline/models/link_cnn.py:67` contains **`nn.BatchNorm2d`** in every convolutional block. So
**AdaBN is available** and arm (d) uses it: the batch-norm running statistics are recomputed from
that session's own pre-press idle windows, with all weights frozen.

**Input-feature normalisation is run beside it** as the simpler comparator, so the arm reports
which of the two carries any effect rather than conflating them.

### Causality

Nothing from the evaluated passes or after them. Enforced by a new test in the style of
`tests/test_prepress_is_causal.py`, asserting that every window feeding an adaptation statistic
ends at or before the first press of its recording **and** carries mode `idle`.

### Reporting

**Per-pairing scatter beside the median**, as item 1 did, because a median hides exactly the
instability this arm is exposed to. **Per-fold, with the three session-01 folds explicit.**

---

## The arms, cheapest first

### (a) VETO, NOT VOTE

The reader only removes regions it rules out with high confidence, and **never boosts one**.

Threshold chosen **on the selection folds** so the TRUE region is vetoed on **at most 2 percent**
of passes there. **The true-region veto rate is then reported on the held-out folds**, where it is
not controlled and may be worse.

### (b) ABSTAIN

The term applies only where the reader's confidence exceeds a threshold set on the selection folds.
**Coverage and the accuracy on covered passes are both reported**; coverage without accuracy, or
accuracy without coverage, is meaningless.

### (c) COARSE FIRST

Two classes, midpoint against corner, then which midpoint when midpoint. Midpoints read about 60
percent and corners at chance, so **corners are never forced**.

### (d) CAUSAL PER-SESSION ADAPTATION — THE PRIORITY ARM

The thesis angle. AdaBN from the session's own pre-press idle windows, weights frozen, plus an
input-feature-normalisation comparator. Reported per fold, **especially the session-01 folds**.

### (e) CLASS-BALANCED TRAINING

For any retrained reader, with **per-region recall reported**, so arm C's collapse to W_mid at 0.9
percent cannot recur unnoticed.

---

## The rules every arm runs under

- **Strictly causal**: windows end at or before the press. Existing
  `tests/test_prepress_is_causal.py` guards stay green.
- **Grouped by pass**, with the grouping asserted on the window indices.
- **Substitution must pass**, generalised rule, ceiling from the actual pairs.
- **Ships only under the full rule through the decoder**: (a) interval above zero on held-out
  folds, (b) at least two passes per pairing, (c) monotone in weight, (d) substitution, plus
  **(f) edge lines not degraded**.
- Nine pairings, session-01 folds explicit, **never judged on `s0102_to_s03`**.
- "Either drawn or committed right" is an after-the-fact oracle and is not quoted as headroom.

## The conditional extension, which does not run unless earned

**Operator amendment.** If (d) lifts session-01 region reading under the ship rule, **the same
adaptation is applied to the TRACKER's emissions** and tested on the **committed semi-bounded
figure** under the full rule plus (f).

**If (d) does not lift it, the extension does not run.** This is written down now so that the
decision to extend is not made after seeing a tempting number.

### OPERATOR OVERRIDE, 2026-09-22, AND IT IS POST HOC

> **The rule above says the extension does not run.** Arm (d) returned a paired delta of +6.67
> points with an interval of [-2.22, 8.61] that INCLUDES ZERO, so condition (a) is not met.
>
> **The operator directed that the tracker extension be run anyway.**
>
> **THIS OVERRIDE IS POST HOC.** It was decided after the arm's result was seen, and it is named
> post hoc in those words rather than presented as the rule having been satisfied.

**What is NOT changed by the override.** The extension's own result is still judged under the full
rule, conditions (a) to (f). Running it is authorised; passing it is not.

**The defensible reading, stated so the override is not mistaken for a shrug.** Arm (d) was
pre-registered as a PILOT precisely because Room A's anchor may be too unstable to establish an
effect. The effect it did produce is positive on all three session-01 folds, lifts the session-01
median by 9.17 points and cuts the per-pairing spread from 40.83 to 28.33, while the input
normalisation control is significantly WORSE. An interval that includes zero on nine pairings is
weak evidence, not evidence of absence. The extension is therefore run as a second pilot, and a
null in it carries the same caveat.

## If nothing ships

Write it up as a measured negative and change nothing. Confirm the DC2 protocol still carries the
approach-walk capture item, since Room B is where this can be trained properly. That item is
present, and the confirmation is recorded at the end of the run either way.


---

# OUTCOME AND DECISIONS, 2026-09-22

## Item 1. b_abstain_0.25 DOES NOT SHIP. The 62.50 headline stands

**Operator decision.** The arm is reported as a **secondary positive finding**, not as a shipped
configuration, and the Room A headline is unchanged.

| condition | b_abstain_0.25 |
|---|---|
| (a) paired interval above zero | **passes**, +2.50 points, CI [0.71, 6.07] |
| (b) at least two passes per pairing | **passes**, three passes |
| (c) monotone response to its own weight | **FAILS** |
| (d) substitution | passes |
| (f) edge lines not degraded | **passes**, none degraded, two improved |

### The consistent reading of (c), and it is POST HOC

> Conditions (a) and (b) are read on the **median paired delta**. Condition (c) was implemented
> reading the **median held-out figure**, which is a different quantity. On this arm the two
> disagree completely: the median falls monotonically (74.17, 71.67, 70.83) while the paired delta
> rises then falls (+2.50, +3.33, +0.83). The median reading PASSED the arm; the paired reading
> FAILS it.
>
> **The implementation was corrected to read (c) on the paired delta, anchored at w = 0 where the
> delta is zero by construction. That correction was made AFTER seeing the data, and in the
> CONSERVATIVE direction: it turns a pass into a fail.**
>
> **THIS IS POST HOC** and is named so in those words.

### Both readings, because they disagree in sign

**Difference of medians −0.83. Median paired delta +2.50.** The median falls because it lands on
the single held-out pairing that lost a pass; six of seven improved or tied.

### The per-pairing table

| held-out pairing | baseline | arm | delta |
|---|---|---|---|
| s01_to_s03 | 50.00 | 60.83 | **+10.83** |
| s0203_to_s01 | 31.67 | 36.67 | +5.00 |
| s03_to_s01 | 25.83 | 30.00 | +4.17 |
| s0103_to_s02 | 86.67 | 89.17 | +2.50 |
| s0102_to_s03 | 88.33 | 89.17 | +0.83 |
| s02_to_s03 | 85.83 | 85.83 | 0.00 |
| s03_to_s02 | 75.00 | 74.17 | −0.83 |

**The session-01 gains, which is what Part 2 was aimed at:** s02_to_s01 +8.33, s03_to_s01 +4.17,
s0203_to_s01 +5.00. All three improve.

## Item 2. The mechanism check: IT HOLDS, and the control is exact

`u4_mechanism`. Held-out passes, counts rather than rates:

| group | n | gained | lost | net |
|---|---|---|---|---|
| **covered, reader correct** | 262 | **31** | **0** | **+31** |
| covered, reader wrong | 288 | 6 | 10 | −4 |
| **uncovered** (the control) | 290 | **0** | **0** | **0** |

**On the passes the reader covered and got right, 31 were gained and NOT ONE was lost.** On
covered-but-wrong the arm costs 4, as a real mechanism should. **On all 290 uncovered passes not a
single outcome changed**, which is the control holding exactly: the term is identically zero there,
so the decode is the shipped one, and this confirms the implementation rather than assuming it.

The net +27 comes entirely from covered-and-correct. **The finding is strengthened, not
downgraded.**

Coverage 66.8 percent overall, 65.5 on held-out folds, range 49.2 to 79.2.

**THE PATTERN, AND TWO EXPLANATIONS, NEITHER CLAIMED.**

| fold | baseline | headroom | reader | coverage | net passes |
|---|---|---|---|---|---|
| s01_to_s03 | 50.00 | 50.00 | 42.5 | 75.0 | **+13** |
| s0203_to_s01 | 31.67 | 68.33 | 26.7 | 60.8 | +6 |
| s03_to_s01 | 25.83 | 74.17 | 25.8 | 79.2 | +5 |
| s0103_to_s02 | 86.67 | 13.33 | 50.0 | 49.2 | +3 |
| s0102_to_s03 | 88.33 | 11.67 | 54.2 | 50.8 | +1 |
| s02_to_s03 | 85.83 | 14.17 | 49.2 | 73.3 | 0 |
| s03_to_s02 | 75.00 | 25.00 | 43.3 | 70.0 | −1 |

Seven held-out folds. **corr(reader accuracy, baseline) = +0.958.**
corr(net gain, headroom) = +0.603. corr(net gain, reader accuracy) = −0.380.

**The pattern:** the folds that gain most are the folds where the reader is weakest, and the folds
that gain least are where it is strongest.

**Explanation one, abstention.** A weak reader abstains more and speaks only when confident, so it
helps where the decoder most needs help and stays silent elsewhere.

**Explanation two, headroom.** The folds where the reader is strong are also the folds with almost
nothing left to win: s0102_to_s03, s0103_to_s02 and s02_to_s03 sit at baselines of 88.33, 86.67
and 85.83, leaving 11.67, 13.33 and 14.17 points of headroom. The folds where the reader is weak
are the low session-01 folds, with 68 to 74 points of headroom.

**THE TWO CANNOT BE SEPARATED HERE AND NEITHER IS CLAIMED.** Reader accuracy and baseline are
collinear at **+0.958** across seven folds, so any statistic that appears to favour one favours the
other by construction. Distinguishing them needs folds where a strong reader meets a low baseline,
or a weak reader a high one, and Room A has none.


## A second arm that clears the rule, reported and NOT shipped

**`a_veto_1.0`** clears all five conditions once a floating-point fault in (b) is fixed.

> **The fault.** The paired delta is a multiple of one pass, 100/120 = 0.8333 points. `a_veto_1.0`
> measured **1.6666666666666665** against a bar of **1.6666666666666667**: exactly two passes,
> rejected on the last bit. Condition (b) now converts to passes and compares integers.

It sits **exactly on** the two-pass bar and carries the same sign disagreement, difference of
medians **−0.83** against a paired delta of **+1.67**.

### OPERATOR DECISION, 2026-09-22: a_veto_1.0 DOES NOT SHIP

**Nothing from Part 2 ships into the Room A headline. 62.50 stands.**

Two grounds, the second the stronger:

1. **The same reason as `b_abstain_0.25`.** Declining a larger effect at three passes with a
   confirmed mechanism, while shipping this one at two, would rest the whole decision on condition
   (c) alone — the condition whose reading had to be corrected twice in a single day.

2. **MULTIPLE TESTING.** Part 2 has now tested **several arms at several weights against the same
   seven held-out folds**: three families at three weights each plus two class-balanced variants,
   eleven arms in all, every one scored on the same 840 passes. **An arm landing EXACTLY on the
   two-pass bar, with the two readings disagreeing in sign, is the result most likely to be
   selection by multiple testing.** The interval on a single arm accounts for none of the ten
   others that were looked at beside it.

**This is a ground of a different kind from condition (c).** (c) asks whether one arm behaves like
a real effect. Multiple testing asks whether the BEST of eleven arms would look like this by
chance, and the arm sitting nearest the bar is exactly where that question bites hardest.

## Item 3. RULE CLARIFICATION, FOR FUTURE WORK ONLY

**From DC2 onward. NOT applied retroactively to b_abstain_0.25**, which is judged under the rule as
it stood.

> **Condition (c)** is read on the **median paired delta**, anchored at **w = 0**, and requires a
> **non-flat response**: the effect must change with the dial. **An interior optimum is permitted
> only when the operating weight was selected on the selection folds.**

The canonical copy is `reports/SEMIBOUNDED_STATE.md` section 10.


---

# PROTOCOL DEVIATION: u3_trackeradapt SHOULD NOT HAVE RUN

**The pre-registration above says the tracker extension runs only if arm (d) lifts session-01
region reading UNDER THE SHIP RULE. Arm (d)'s interval includes zero, so the condition was NOT met.
The extension ran anyway, on an operator override that is recorded as post hoc. That is a
PROTOCOL DEVIATION, and it is listed here and in the own-faults list rather than only in the
override note.**

**Its result is therefore EXPLORATORY.** It is not a confirmatory test of anything, it does not
enter any headline, and it is labelled exploratory wherever it is reported.

## The result: significantly negative

| fold | unadapted | adapted | delta |
|---|---|---|---|
| s0102_to_s03 | 50.83 | 27.50 | **−23.33** |
| s01_to_s03 | 44.17 | 25.83 | **−18.33** |
| s02_to_s03 | 63.33 | 47.50 | **−15.83** |
| s03_to_s02 | 60.83 | 57.50 | −3.33 |
| s0203_to_s01 | 31.67 | 29.17 | −2.50 |
| s01_to_s02 | 48.33 | 46.67 | −1.67 |
| s03_to_s01 | 30.83 | 30.83 | 0.00 |
| s0103_to_s02 | 50.00 | 51.67 | +1.67 |
| s02_to_s01 | 29.17 | 32.50 | +3.33 |

Held-out seven: **50.00 unadapted against 30.83 adapted**. Paired **−3.33**, CI **[−15.83, −2.62]**,
entirely below zero. Session-01 median delta exactly **0.00**. Edge lines: E_col5 **−35.71**,
E_row5 −26.19, E_col1 −16.67, E_row1 +4.76.

### Where the harm concentrates, which is the informative part

**The harm falls on the folds where the unadapted tracker was WORKING.** The three worst losses are
the three highest unadapted baselines: 50.83, 63.33 and 44.17. **The three session-01 folds, where
the tracker was already poor, are essentially unchanged**: +3.33, 0.00 and −2.50.

So adaptation **destroys performance where there was performance, and does nothing where there was
none**. That is the opposite pattern to arm (d) on the region reader, and it is why the two results
are not two readings of one effect.

## Interpretation: two explanations, BOTH STATED, NEITHER CLAIMED

**One, the anchor is unfit.** Item 1 (`t8_calib`) measured that Room A's only per-session anchor,
the pre-press setup period, varies **2.3x across three days in the same room**, and that this alone
made the relative gate and null scatter 3.33 points per pairing. This extension adapts from the
same anchor. **A null or negative result on an unfit anchor does not show that adaptation fails
with a clean one.**

**Two, the downstream classifier is frozen.** In arm (d) the LDA is **refit** on the adapted
features, so the classifier moves with the representation. In the tracker the 25-cell head's final
layer is **frozen**, so re-anchoring the batch-norm statistics shifts the features out from under a
classifier calibrated on the originals. The calibration windows are also `idle`, a person standing
or milling about rather than walking a taped line, so the statistics come from a different regime
than the one the emission must serve.

**Neither is claimed.** They are not exclusive and this stage cannot separate them. The check that
would is a contrast between a refit and a frozen downstream classifier on the same adapted
features, and it has not been run.
