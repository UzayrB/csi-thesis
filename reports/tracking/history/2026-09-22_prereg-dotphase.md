# Pre-registration: the drawn dot's phase, and why it leads the walker

Written 2026-09-22, **before `w1_dotphase` was written or run**. Operator report: the red dot leads
the green marker, does not start at the start of the path, and the display feels less accurate than
it was.

## What is already known without running anything

Two facts, both read off the code and neither previously measured:

1. **`lead=True` is a permanent +1 stride phase shift, not a start-only fix.**
   `render_display.simulate_walk` under `lead=True` interpolates from `pts[i_max]` towards
   `pts[i_max+1]` instead of from `pts[i_max-1]` towards `pts[i_max]`. At every frame, not only the
   first, the drawn dot is one stride (0.5 s of walking, about 0.65 m at the measured pace) further
   along the path than trailing interpolation would place it. It was introduced in freeze
   `2026-09-20b` to cure a start stall under rule 6, and it cures it by moving the whole walk.

2. **The arm was selected under one drawing loop and is shipped under another.**
   `s2_display`, the nine-pairing stage that chose `DISP_END`, calls `simulate_walk` with the
   default `lead=False`. `f3_render` draws with `lead=True`. **The dot the operator is watching has
   never been measured over nine pairings.** Every nine-pairing display figure this project quotes
   describes the trailing dot.

Neither fact is a result. Both are reasons the measurement below is worth taking.

## The one-parameter family

`shift_w`, a phase shift in strides added to the drawn index, with trailing interpolation
throughout:

    raw = (tq - t_start) / stride - lag_w + shift_w

`shift_w = 0.0` is trailing. `shift_w = 1.0` is the shipped leading render. **The shipped
configuration is a member of the family**, which is what makes a monotone-response check meaningful.
Arms: **0.00, 0.25, 0.50, 0.75, 1.00**.

**Reproduction check, stated before it is run:** `shift_w = 1.0` with trailing endpoints must
reproduce the shipped `lead=True` drawing. They differ only in which element of `lines[]` is passed
to `Dot.step` at a line change, which cannot occur after the lock. **If the two do not agree on at
least 99 percent of frames, the family is not a superset of the shipped render and the sweep is
void.**

## Measurements, all over the NINE pairings

**PRIMARY: frames within 0.5 m** of the truth at the frame's own time, on **correct-line passes**,
paired per pass on `session|stem|pass_id`.

**SECONDARY, and it is the operator's actual complaint: the SIGNED along-line offset.** The drawn
position minus the truth, projected on the direction of travel of the line being drawn. **Positive
means the dot is ahead of the walker.** Reported as mean, median, and the fraction of frames ahead.
No figure this project has ever produced carries a sign, which is why a dot that leads and a dot
that lags have been indistinguishable in every table.

**ALSO: the start gap**, the distance between dot and marker on the first drawn frame, decomposed
into the part explained by cell quantisation (the distance from the true entry point to the nearest
cell centre on that line) and the remainder. And **the first-stride stall**, the distance the dot
travels in its first 0.5 s, which is what `lead=True` was introduced to cure.

## The ship rule, fixed now

A display arm ships only if all of:

- **(a)** the paired improvement in within-0.5 m on correct-line passes has a bootstrap interval
  **entirely above zero** over the nine pairings;
- **(b)** it improves in **at least 7 of the 9 pairings**;
- **(c)** the response across `shift_w` is **monotone**, so the effect belongs to the parameter;
- **(d)** the committed line and the semi-bounded own-end line are **bit-identical across every
  arm**, asserted per pass, because a display setting that moves the answer is not a display
  setting;
- **(e)** both causal bounds stay **at or below zero**;
- **(f)** rule 2 violations stay at **zero**, and the first-stride stall is **no worse than the
  shipped render's measured 0.10 s maximum with zero violations**.

**The tie-break, and it is the only place the operator's complaint enters the decision:** if two or
more arms have within-0.5 m point estimates inside the best arm's interval, **ship the one whose
mean signed offset is closest to zero**. A dot that is equally close on average but not
systematically ahead is the better display, and this rule is written before any signed number
exists.

**KILL:** if no arm satisfies (a), **nothing ships and the render is left alone**, and the signed
offset is reported as a measured property of the shipped display rather than fixed.

**Forbidden here, as everywhere:** any per-line offset, bias or prior fitted to Room A's counts. A
single global `shift_w` chosen by the rule above is a phase, not a per-line fit; anything indexed by
line is out.

## What this cannot do

`shift_w` moves the dot along the line it is already on. **On the 33-of-120 walks where the lock is
wrong it changes nothing that matters**, because the dot is on the wrong tape and the error is a
line error. This is a fix for the correct-line walks only, and the correct-line split is therefore
the primary.

---

# OUTCOME, appended after the run. Nothing was edited above.

**Reproduction check: 100.00 percent of 42,267 frames identical.** `shift_w = 1.00` with trailing
endpoints reproduces the shipped `lead=True` drawing exactly, so the family is a superset of the
shipped render and the sweep is valid. **Two earlier runs were voided by this check at 59 and 50
percent**, both for faults of mine recorded in the report.

| `shift_w` | within 0.5 m, correct line | paired vs shipped | 95 percent interval | pairings improved | signed mean | ahead on | start gap |
|---|---|---|---|---|---|---|---|
| 0.00 trailing | 44.77 | -6.87 | [-10.62, -3.30] | 1 of 9 | -0.588 m | 16.6 | 0.615 m |
| 0.25 | 49.82 | -1.81 | [-5.11, 1.18] | 2 of 9 | -0.440 m | 24.2 | 0.615 m |
| **0.50** best by primary | **53.05** | +1.41 | **[-0.98, 3.69]** | 6 of 9 | -0.281 m | 33.5 | 0.615 m |
| 0.75 | 52.83 | +1.20 | **[-0.27, 2.58]** | 6 of 9 | -0.118 m | 43.3 | 0.615 m |
| **1.00 SHIPPED** | 51.63 | 0.00 | | | **+0.046 m** | **52.8** | **0.544 m** |

**VERDICT: NOTHING SHIPS. The render is unchanged.**

| condition | result |
|---|---|
| (a) paired interval entirely above zero | **FAIL.** The best arm's interval is [-0.98, 3.69] and straddles zero |
| (b) improves in at least 7 of 9 pairings | **FAIL.** 6 of 9 |
| (c) monotone response | **FAIL as written**, see the disclosure below |
| (d) the answer never moved | PASS |
| (f) rule violations zero | PASS |
| reproduction check | PASS at 100.00 percent |

**THE TIE-BREAK, WRITTEN BEFORE ANY SIGNED NUMBER EXISTED, ENDORSES THE SHIPPED RENDER.** Arms
0.50, 0.75 and 1.00 all lie inside the best arm's interval [50.51, 55.44], and among them
`shift_w = 1.00` has the mean signed offset closest to zero at **+0.046 m**. The rule written to
answer the operator's complaint selects the configuration the operator is complaining about.

## POST HOC disclosure on condition (c)

**Condition (c) as written is the wrong shape of test and it failed for that reason.** A monotone
response suits a one-sided weight. A PHASE has an interior optimum, so the primary metric rises to
a peak at 0.50 and falls again, and no phase parameter could ever satisfy (c). **The signed offset
IS monotone across the family**, -0.588 to +0.046 without exception, and that is the evidence that
`shift_w` does what it claims.

**This reinterpretation is POST HOC and it changes nothing**, because (a) and (b) fail
independently and the arm does not ship either way. It is recorded so that a future phase sweep
pre-registers monotonicity of the SIGNED offset rather than of the primary.

## What the KILL rule requires, and it is the finding

No arm satisfies (a), so **the signed offset is reported as a measured property of the shipped
display rather than fixed**: the shipped dot sits **+0.046 m ahead on average and is ahead on 52.8
percent of frames**. It is centred, not biased. **There is no systematic lead to remove**, and the
one arm that reduces the fraction of frames ahead does so by sitting 0.28 m behind, which would
make a different complaint worse.
