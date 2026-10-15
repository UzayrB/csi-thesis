# The semi-bounded mode: state, parts, and how it works

> **Terminology corrected 2026-09-23 (batch 23c):** g100 is a 100-cell REGION posterior head ("g" is the grid kind, 100 the cell count), not a motion gate. Earlier text here called it "the gate head" and has been corrected; the JSON keys `gate_head_g100` and `g100_gate` are kept as identifiers and mean the same region head.

Rewritten 2026-09-19 after the multi-head pool. Everything here is checkable against files; nothing
relies on remembering a conversation. Frozen record: `runs/TRACKING_FROZEN_2026-09-20c.json`. The rendering contract is `reports/RENDER_RULES.md`, enforced by `tests/test_render_rules.py`. The demonstration runs 2 s behind real time, stated on every frame as the live mode's latency, and its dot commits on 2 s of evidence: it draws an EARLY answer by design, not the decoder's final one. Tracking is reported SPLIT by whether the dot is on the right line, 52.0 percent within 0.5 m when it is, because on a wrong line the dot-to-walker distance is a line error and not a tracking error.
Sections 4 to 7 describe machinery that the pool did NOT change; sections 1, 2, 3, 8c and 9 are new.

---

## 1. What it is, in one paragraph

Three modes exist, separated by what they are TOLD. The unbounded mode is told nothing and must
decide for itself that a walk began. The bounded mode is told when each walk starts AND ends.
**Semi-bounded is told only when a walk STARTS**, and must work out both which of the twelve lines
it is and when the walk ended. It matters because the start of a walk is a fact available at the
moment it happens, while the end is a FUTURE fact: semi-bounded is therefore the only one of the
three that could run live, and bounded is a retrospective upper bound on what the radio contains
rather than a system.

## 2. Where it stands

**Updated 2026-09-20: the exit rule is now causal and the headline is 62.50 percent.** The
semi-bounded decoder decides for itself when a walk ended. Until 2026-09-20 it did that by running
one Viterbi from the walk's start out to twenty seconds and taking the first window the null state
won, so the exit could depend on radio recorded long after the walk: an evidence bound of
**+20.5 s**. A live system cannot do that. It now declares the end at the first step whose decode,
over the windows available at that moment, ends in the null state, and its evidence bound is
**+1.0 s**, the same declaration latency the committed answer already carries.

| | |
|---|---|
| **line identification, cross-day, nine pairings** | **62.50 percent** |
| the same figure per pass, pooled over 1080 passes | 59.54 percent |
| bounded, nine pairings | 65.83 percent |
| **gap to bounded** | **3.33 points** against a **ten-point** bar |
| **verdict** | **SEMI-BOUNDED REMAINS THE CORE MODE** |
| superseded, NOT quotable | 64.17 percent, produced by the non-causal exit search |
| exit rule evidence bound | +1.0 s, was +20.5 s |

**64.17 percent is superseded and must not be quoted.** It was produced by an exit search with
+20.5 s of look-ahead, which is not something a live system can do, so it is not a live figure
whatever its value.

**The 1.67-point drop is not the causal exit being worse.** Per-pairing rates move in steps of
1.67 points, because a pairing holds a hundred and twenty passes and 2/120 is 1.67 percent. Six of
the nine pairings moved down one step and three moved up, by one, one and three steps. Per pass
over all 1080 the paired delta is **+0.09 points with an interval of [-1.30, 1.57]**, and the
**total number of passes decoded correctly went UP by one**. The median over pairings fell one
step because it landed on a different pairing, which is exactly what a median of nine numbers does
and exactly why this project reports the paired reading beside it.

### The earlier five-head pool figures, kept for the record

| | |
|---|---|
| line identification, cross-day | **57.5 percent** |
| chance, twelve lines | 8.3 percent, so **6.9 times chance** |
| bounded under the SAME heads | 65.8 percent |
| gap to bounded | **8.3 points** against a **ten-point** bar |
| verdict | **SEMI-BOUNDED BECOMES THE CORE MODE** |
| within-day, reported separately and never pooled | 94.2 percent, over 3 pairings |
| end-to-end latency | **49.8 ms per window** against a **500 ms** contract |

The verdict was recorded in `g3_final` BEFORE any re-render, and it is measured against bounded
UNDER THE SAME HEADS, which is the like-for-like reference the bar was written against. All four
pre-registered conditions hold: within ten points, median end error inside one second, never-ended
under five percent, and both substitution tests pass. The stretch target of five points is NOT met.

**Quote 62.50 percent for the live mode**, which is 7.5 times the 8.3 percent chance. Quote 65.83
only as bounded, and never as what a live system does. The 57.5 and 65.8 figures above belong to
the five-head pool batch and are kept for the record; they were taken under the non-causal exit.

## 2a. What changed, and why it worked when nothing else did

Every lever tried on the decoder between 17 and 19 September failed, and they failed for one
reason: each of them tried to fix the END, and the only ways to improve the end turned out to be
ways of inferring it from elapsed time rather than from the radio. The substitution test caught
each one.

**Pooling heads is the lever that works, and it works because it does not touch the end machinery
at all.** It sharpens the EVIDENCE the decoder reads, leaving the end rule exactly as it was.
Several independently trained encoders each produce a posterior over cells; averaging their log
posteriors cancels the part of each head's error that is particular to its own training run and
keeps the part they agree on. The decoder then runs unchanged on a cleaner emission. That is why
every pooled arm passes the guard while every end-directed arm that gained points failed it: there
is no mechanism by which a sharper emission can smuggle in the clock.

Replace any earlier sentence saying that nothing reaches the bar without turning the end into a
clock. The correct statement is: **nothing that attacks the end directly reaches the bar without
turning the end into a clock, and the thing that does reach the bar never attacks the end at all.**

## 3. The shipped configuration

Stride **0.5 s**, window **2 s**, frozen heads, display lag 1 s.

Decoder arm: `C_family + G_maxlik + I_chainprior`, over a **five-head equal-weight pool**.

| head | what it is |
|---|---|
| half-stride 25-cell head | the original shipped head, trained at the 0.5 s stride |
| 1 s seed 0, seed 1, seed 2 | three independently seeded 1 s heads, inferred over the 0.5 s window set |
| g100 region head | a 100-cell head, summed 4 cells to 1 onto the same 5 by 5 grid |

**THE POOL IS EVERY AVAILABLE HEAD AT EQUAL WEIGHT, and that is a rule rather than a result.**
Using every head equally is parameter-free. Choosing a best subset by looking at the numbers is a
selection, and selection was measured to HURT: a weighted arm that tuned the mix scored 50.8
against the equal-weight 60.0. So no head is dropped for scoring badly, including the g100 region head,
which scores slightly below the four-head pool on one of the two readings.

The pool is a log-opinion pool: the mean of the log posteriors, renormalised per window, which is
the geometric mean of the probabilities. Built by `shipped_pool_emissions()` in
`pipeline/constrained/g3_final.py`; the renderer calls that function rather than rebuilding the
pool, so what is drawn is the same object the verdict was taken on.

## 3a. The head-count curve, and the saturation finding

| heads | semi-bounded, cross-day |
|---|---|
| 1 | 46.7 |
| 2 | 54.2 |
| 3 | 59.2 |
| 4 | 60.0 |
| 5, with the g100 region head | 57.5 |

**The curve saturates at three.** The 3-to-4 step has a paired interval of **[-1.39, +2.59]**,
which includes zero, so a fourth head is not distinguishable from no fourth head. The 4-to-5 step
is the same: difference of medians **-2.5**, median of paired deltas **+0.8**, interval
**[-1.02, +1.11]**, which includes zero. **The two readings disagree in SIGN on that step**, which
is exactly why both are always printed; the difference-of-medians move is a median-swap artefact,
since per pairing the deltas run from -2.5 to +1.7 and five of nine are positive.

Heads four and five ship anyway, because the rule was fixed before the numbers: equal weight over
every available head. They cost nothing that can be measured, and dropping them would be a
selection.

**The verdict does not depend on this choice.** Four heads give 60.0 against 66.7, a gap of 6.7.
Five heads give 57.5 against 65.8, a gap of 8.3. Both pass the ten-point bar, so semi-bounded
becomes the core mode either way.

## 3b. Against the single-head baseline, both readings

| reading | value |
|---|---|
| difference of medians | **+10.8 points**, 46.7 to 57.5 |
| median of per-pairing paired deltas | **+5.0 points**, interval **[0.92, 10.09]** |
| interval excludes zero | **yes**, over 9 cross-day pairings |

The two readings differ because the median picks a different pairing on each side. The paired
reading is the one that controls for how hard each pairing is; the interval on it is what carries
the claim.

## 3c. The guard still passes

| | pool | single head |
|---|---|---|
| end-time substitution | **77.5 percent** | 80.0 |
| line substitution | **90.0 percent** | 90.8 |
| passes the gate | **yes** | yes |

Swapping in another participant's CSI moves the decoder's end on more than three passes in four.
The end is still read from the radio, and pooling did not erode that, which is the point of
section 2a.

## 4. How it works, step by step

Entry point for the decode is `track2()` in `pipeline/constrained/sb2_structural.py:307`, reached
through `night_track()` in `pipeline/constrained/night_arms.py` for the shipped arm.

1. **The start press is given.** The decoder enters at that window with every on-chain state
   allowed at equal cost. Entry is NOT pinned to the chains' first states, deliberately.
2. **A forward pass keeps all twelve chains alive.** At each window it takes a log-sum-exp over
   each chain's own states and shows the leading chain. The display changes only when a different
   chain has led for **two consecutive windows**, so the dot does not flicker. Each change is
   counted as a revision.
3. **The decoder finds its own end.** A Viterbi over the extended state space, which includes the
   null and transit states, runs from the start press; the first window that returns to null is the
   end. A geometric safety timeout at chain length over 0.5 m/s guarantees a pass can always end.
4. **At that end it rescores.** The whole interval from the start press to its own end is decoded
   again over the twelve chains alone, with no null, and the final line and track are committed.
   This is the bounded machinery with a SELF-DETECTED end instead of an operator-supplied one, and
   it uses no information the mode was not given.
5. **The committed track is audited.** Impossible transitions must be zero and are: **0** on every
   final committed track.

The pool enters at step 1 and nowhere else: it changes what the emissions say, not what any of
these five steps do with them.

## 5. How the end is scored, which is easy to get wrong

**Against the LAST ANCHOR PRESS**, read from the read-only `data/room_A/session_*/‹stem›.gt.json`
as `t_end`, which equals `anchor_times[-1]` exactly.

**The 51 ms reaction-time bias is ALREADY subtracted** at labelling time
(`reaction_time.applied` in every sidecar). Subtracting it again over-corrects, which
`pipeline/io/rt_calibration.py` warns about by name.

Two other definitions exist and are reported as secondary columns, because they disagree by more
than the one-second bar:

| definition | offset from the press |
|---|---|
| pass-span end, the far edge of a 3 s run-out grace zone | **+3.25 s** |
| centre of the last position-labelled window | **-0.68 s**, about 0.88 m of line |

## 6. THE GUARD, which is a gate and not an axis

**An arm whose end-time substitution falls at or below 50 percent is OUT, whatever its line
figure. Among the arms that pass, take the best line.** Applied the other way round, the project
would have shipped a higher number whose end is partly a clock.

**`pinned_entry` was refused by this gate and that was the finding of the 18 September batch.**
Pinning entry fixes position at a known state at a known time, and the chain carries one sharp
global duration prior, so arrival at the chain's end becomes partly a function of ELAPSED TIME
rather than of the emissions. Its marginal effect on end-time substitution is **-12.5 points at
1 s and -32.5 at 0.5 s**, against **0.00 for `all_alive` and `rescore_end`**. It bought 7.5 points
of line and the gate took all of it back.

This is the same defect as the deleted ramp extension in a different disguise: that was a segment
DRAWN without evidence, this is an end INFERRED from the clock. Neither was caught by code review,
a coverage figure or an exit code; both were caught only by a substitution test.

## 7. The commitment timeline, on the line the viewer is actually shown

How often the line on the screen is already correct, by seconds after the start press. NOT the
committed answer, which arrives at the end. Re-measured by `r5_timeline` on the shipped display:
the fixed-lag Viterbi path at soft entry and a 0 s display lag, over the nine
cross-day pairings, median over pairings and never pooled.

| seconds after the press | 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | 3.5 | 4.0 |
|---|---|---|---|---|---|---|---|---|
| **nine-pairing aggregate** | 19.2 | 20.0 | 30.8 | 27.5 | 38.3 | 42.5 | 45.8 | 44.2 |
| demonstration pairing | 20.8 | 42.5 | 61.7 | 59.2 | 63.3 | 65.0 | 65.0 | 56.7 |

**The video and this document now describe the same curve**, because this is measured on the line
the renderer draws rather than on a per-window argmax display that no longer exists. The
demonstration pairing is the strongest one and is not typical; quote the aggregate.

**A pass takes about four seconds, so the line is still assembling when the walk ends.** At four
seconds the shown line is correct on 44.2 percent of passes while the committed answer,
taken at the end over the whole interval, reaches 57.5. The distance between those two numbers is
the value of rescoring at the end rather than trusting the running display.

The window probe of 2026-09-19 established by measurement that **no confidence margin exists** at
which the display commits on more than half of passes before the walk ends and is right more often
than not when it does. Neither a fixed hold nor a confidence gate is a tuning problem.

**The display lag is now 0 s**, chosen in `r3_lagsweep` because it tracked
the walker best on screen: 28.5 percent of frames within 0.5 m against 11.1 at 0.5 s and 6.7 at
1.0 s. The earlier 1 s lag was inherited from the bounded renderer and had never been judged on
what it did to the live display.

## 7b. What the demonstration draws, since 2026-09-20

The dot **parks at the room centre for 1.5 s**, watching, then jumps once and **locks to one line
for the whole walk**. After the lock the position comes from a Viterbi restricted to that chain, so
it is still a decoded position and the one rule still holds; it is not a projection onto the line.

| | |
|---|---|
| commit delay | **1.5 s**, the shortest whose locked-line accuracy lies inside the best delay's interval |
| display lag after the lock | **0 s** |
| switches of the shown line | **exactly one**, by construction |
| locked line correct | **57.5 percent** of walks |
| committed line at the end press | 78.3 percent on this pairing |
| frozen tails | **13.3 to 0.0 percent** |
| tracking, whole walk | 23.1 percent within 0.5 m |
| tracking, after the lock | **36.9 percent** |

The delay sweep, locked-line accuracy with intervals: 0.5 s gives 20.8 [14.2, 28.3], 1.0 s gives
42.5 [35.0, 51.7], 1.5 s gives 63.3 [55.0, 71.7], 2.0 s gives 64.2 [55.8, 72.5]. Waiting longer than
1.5 s buys nothing outside the interval.

**A confidently wrong walk is correct behaviour and is left in the video.** On roughly one walk in
three on this pairing the locked line is wrong and the dot tracks the wrong line for the whole walk.
That is what the system believes, and hiding it was the defect of the render before 19 September.

## 7c. The three display bugs of 2026-09-20, and what they cost

**The lock position was a clock.** The chain-restricted Viterbi had no entry prior, so with flat
within-chain emissions it began at the chain's first state and advanced at the preferred step:
every pass locked at exactly 2.25 m of arc. Fixed by passing the soft-entry distribution restricted
to the chain. **It reached the screen because a display construct was never put through the
substitution test.** Any future display component that produces a POSITION must be.

**The dot jumped lines at the end press**, sliding to the bounded rescore whenever it disagreed
with the locked line, which is 37 percent of walks. It now holds its final position and the bounded
answer is reported as text.

**The dot raced to the end of the line and parked there**, the same root cause as the clock.

The settings that changed with them: a **3 m/s ceiling**, which B1 had rejected on the pre-lock
display where wrong-line errors masked the along-line lag, and a **0.75 s wait** as an operator
override of the 1.5 s the rule chose.

## 7d. The causality leak, and what the display honestly does

**A live display may use only windows whose END is at or before the frame time.** `t0` is the
window START and a window spans [t0, t0 + 2.0]. The render defined the walk's start as the window
CENTRE and drew, at "0 s lag", a window ending 0.51 to 1.00 s after the frame. Every frame used
samples not yet recorded. `tests/test_display_is_causal.py` now refuses any lag below half the
window length, and it failed against the shipped render before this was fixed.

**The strict lag is 1.0 s and the earliest legal lock is 1.0 s.** A 0.75 s wait is impossible.

| | |
|---|---|
| wait | 1.5 s |
| display lag | 1.0 s, the strict minimum |
| on-screen tracking | **3.5 percent within 0.5 m**, mean 2.40 m |
| committed line, end press | 78.3 percent on this pairing |
| rule violations | 0 over 3463 frames |
| frames with no red dot | 0 of 22946 |

The causal wait curve, for the record: at 1.0, 1.5, 2.0, 2.5 and 3.0 s the locked line is correct
on 49.2, 63.3, 62.5, 63.3 and 68.3 percent of walks on the demonstration pairing, and 27.5, 33.3,
38.3, 36.7 and 49.2 over nine pairings. Position tracking is 1 to 3 percent at every wait, because
with a 2 s window the walker moves 1.5 to 2 m before the window may be used.

## 7e. The run-up, measured and not used

The two seconds before the press are a continuation of the walk, not transit: the gate says walking
on 80.8 percent of those windows, median 100, against 11.3 standing still. They are legal to use,
having ended before the press. With the frozen pool they carry **direction** (55.2 against 50,
interval [52.4, 57.6]) and **not line** (9.2 against 8.3 chance).

Two arms were built and both were refused by their pre-registered gate: a zero-sum direction prior
between fwd/rev pairs, which trades 0.83 points of reversed error for 0.80 points of line accuracy,
and chains extended 1.0 m backwards, which are 15.83 points worse on the line outside the interval.
The run-up is real and readable; it is not enough to change a decision.

**They are also absent from every training set**, which is a separate fact and was not known when
the arms above were refused. `pipeline/constrained/dataset.py:121` selects
`(rec.mode == "walk") & np.isfinite(rec.xy).all(1)`. Measured over all eighteen recordings there
are **1440 pre-press windows, exactly 4 per pass, every one labelled `walk_edge` and not one
carrying a finite `xy`**. No head on record has ever seen a participant outside the grid. Whether
that is worth fixing is `reports/PREREG_prepress_region_2026-09-21.md`.

### CORRECTION, 2026-09-21: A3's chance level was understated, and the corners group fails its corrected bar

**Restated, not quietly amended.** `q3_startclf` reports `chance_pct: 12.5`, uniform over eight
regions. The classes are not uniform: over 360 passes, SW 72, NW 54, SE 54, and 36 each for NE,
S_mid, N_mid, E_mid and W_mid. The honest baseline is the best constant predictor, which differs
per group because the groups are subsets of passes:

| task | correct baseline | bar, twice baseline | measured | verdict |
|---|---|---|---|---|
| overall, 8 regions | **20.0** percent, always SW | **40.0** | 46.7 | clears on the point estimate |
| edge midpoints, 144 passes | **25.0** percent | **50.0** | 61.8, lower bound 53.5 | **clears** |
| corners, 216 passes | **33.3** percent, always SW | **66.7** | 36.6, interval [30.1, 42.6] | **DOES NOT CLEAR** |

A3's bar was written as "twice the 12.5 percent chance, so 25 percent". Against the correct 20.0
percent overall baseline it should have been 40 percent. **The corners group fails**, and its
interval contains its own 33.3 percent baseline, so on corner passes the classifier is not
distinguishable from one that answers SW every time. The overall 46.7 percent still clears the
corrected bar, but **it earns that on the edge midpoints alone.**

**Nothing that ships depends on this bar.** A1 and A2 at weight 0.5 were selected on their own
paired improvement on the held-out folds, which is unaffected by how chance was stated. The shipped
arm stands on that improvement and not on A3 having passed a gate. The fuller restatement is in
`reports/PARTS_1_TO_3_REPORT_2026-09-20.md` under A3.

## 8. What was tried and did not work, so it is not tried again

- **An arc-fraction null lockout.** Cannot bind: the decoder already reaches a median 95.5 percent
  of its chain before leaving.
- **A maximum-speed cap and a time-based lockout.** Both measured inert: implied traversal speed is
  a median 1.26 m/s with no pass above 2.0 m/s, so a cap at 1.6 to 2.4 cannot bind.
- **The exit parameter sweep.** Changes nothing: aggregate line 53.3 before and after.
- **Every lever at the one-second stride.** At 1 s the last 0.68 s of every line carries no
  labelled window, so the emission model had never seen a line ending.
- **A guard-safe pinned entry via a flattened duration prior.** Makes the guard and the line worse
  TOGETHER: end substitution 47.5 to 21.7 and line 48.3 to 25.8. Sharpness was never the mechanism.
- **Proposing candidate ends.** 24 to 28 percent against the shipped 42.5, and unexplained.
- **Day-only calibration on the live mode.** 81.5 calibrated against 81.5 uncalibrated, over six
  calibrators. Zero.
- **A weighted head mix.** 50.8 against the equal-weight 60.0. Selection hurts, which is the
  evidence behind the equal-weight rule in section 3.

## 8c. What the pool changed for the bounded mode as well

Arm F, the pool, ships for bounded too, on its own pre-registered test:

| | |
|---|---|
| bounded, single head | 58.3 percent |
| bounded, five-head pool | **65.8 percent** |
| difference of medians | **+7.5 points** |
| median of paired deltas | **+4.2 points**, interval **[0.56, 7.04]** |
| interval excludes zero | **yes** |
| median error when right, not worse | **yes** |

So the demonstration's committed answer uses the pool, and the bounded upper bound the live mode is
measured against moved up with it. That is why the gap closed to 8.3 rather than to 1.7: the
reference is not held fixed while the live mode improves, which would have been the easy and wrong
way to pass the bar.

## 9. Open, in the order I would take it

1. **The end, still, but not by attacking it.** Half the passes have an end more than a second from
   the press, and those score far below the good half. No lever aimed at the end has survived the
   guard. Pooling improved the line without improving the end, so the end remains the open problem
   and the stops-short tail is 85 percent of the failures.
2. **More heads is done.** The curve saturates at three and the fourth and fifth are within noise.
   Training further seeds is not worth machine time; if more heads are wanted they should differ in
   KIND, as the g100 region head does, rather than in seed.
3. **The second collection**, 26 and 27 September, in a different room.
   `reports/DC2_PROTOCOL_2026-09-18.md` is printable. Deliberate speed variation per participant is
   the most important item on it.

**Not open any more, 2026-09-22.** The demonstration latency is DECIDED at exactly 2.0 s, as rule
V1 of `reports/RENDER_RULES.md`. And TRACKING IS NEVER CLOSED: every statement that it is closed
until DC2 is superseded, recorded in `runs/SUPERSESSION_tracking_open_2026-09-22.json`. Rendering
rules live in `reports/RENDER_RULES.md` and nowhere else.

## 10. Rules that apply to any further work

- **No decision is taken on a single pairing.** Earned repeatedly: the exit sweep's four significant
  intervals became zero under correct pairing, and pinned entry RAISED the guard on `s01_to_s02`
  while costing 12.5 and 32.5 on the aggregate.
- **A component is signal-driven only if another participant's CSI changes its answer.** Coverage
  figures and exit codes prove nothing.
- **Every aggregate comparison prints BOTH readings**, difference of medians and median of paired
  deltas, with the interval on the paired one. They have now disagreed in sign twice, most recently
  on the 4-to-5 head step.
- **Never quote a median without its distribution**, and never compare one pairing against an
  aggregate.
- `data/` is read only. Frozen artefacts are never overwritten. British spelling, no em dashes.

### THE SHIP RULE, amended 2026-09-22. All three conditions, not one

**An arm ships only if all three hold:**

- **(a)** its paired improvement interval on the **held-out folds** is entirely above zero;
- **(b)** the median paired delta is **at least two passes per pairing**, which at 120 passes a
  pairing is **at least 1.67 points**;
- **(c)** the effect shows a **monotone response to the term's own weight**.

**This is a RULE CHANGE MADE AFTER SEEING THE DATA, and it is recorded in those words.** Until
2026-09-22 the rule was condition (a) alone. `t5_shipc` then showed that (a) can fire at the
resolution floor: `add_0.5` returned a paired delta of **+0.83 points with an interval of
[0.24, 1.07]** that excludes zero and a guard that passes, and **the whole effect was five passes
out of 840**. A pairing holds 120 passes, so a per-pairing rate moves in steps of 0.833 points and
+0.83 IS ONE PASS. The interval excluded zero only because no held-out pairing moved down: four
moved up by one or two passes and three were exactly flat, and a bootstrap over seven non-negative
values excludes zero whatever their size. Weights 0.25, 0.5 and 1.0 all returned the same +0.83,
so there was no gradient either.

Conditions (b) and (c) are the two independent checks that would each have caught it alone.

**Applies to all future analyses, DC2 included.** The arm that prompted the change was NOT shipped;
see `reports/PREPRESS_REGION_REPORT_2026-09-21.md` section 9 and the pre-registration's amendment E.

### Condition (c) clarified, 2026-09-22. FROM DC2 ONWARD, not retroactive

> **(c) is read on the MEDIAN PAIRED DELTA, anchored at w = 0**, which is the same quantity
> conditions (a) and (b) use, and it requires a **NON-FLAT response**: the effect must change with
> the dial. **An interior optimum is permitted only when the operating weight was selected on the
> selection folds.**

**Why.** (c) was implemented reading the median held-out figure, a DIFFERENT quantity from the one
(a) and (b) use. On `b_abstain_0.25` the two disagreed completely: the median fell monotonically
while the paired delta rose then fell, so the median reading PASSED an arm the paired reading
FAILS. Conditions of one rule must be read on one quantity.

**And a floating-point fault in (b), fixed at the same time.** The paired delta is a multiple of
one pass, 100/120 = 0.8333 points. An arm measuring exactly two passes read 1.6666666666666665
against a bar of 1.6666666666666667 and was rejected on the last bit. **(b) now converts to passes
and compares integers.**

### Condition (f) AMENDED, 2026-09-23. OPERATOR DECISION. POST HOC, in those words

> **An arm passes (f) if the four edge lines' combined change in correct walks is zero or
> positive, AND no single edge line loses more than TWO walks.**

The two-walk floor is the same as (b)'s two-pass floor, and it still stops a collapse such as
E_col1 to 0.00. **Why, in the operator's words:** one walk is the resolution floor, and the old
per-line zero tolerance refused arms that were net positive across the edge lines (`y2_dial`
+5.00 held-out refused by one E_row1 walk, net zero; switching refused by E_col5, net +15).

**This is a rule changed after seeing the data and it is POST HOC, in those words.** It was applied
UNIFORMLY on the day it was made: every arm refused since 2026-09-22, 44 rows, re-read on (f) alone,
every other condition as its own stage judged it. `reports/REEVAL_f_amended_2026-09-23.md`,
`runs/constrained/fh/d1_reeval/results.json`. Edge changes are counted in walks on each stage's own
evaluation set (54 per line over nine pairings, or 42 over the held-out seven).

**The former (f)** was "no edge line degraded, by even one pass". Every verdict taken under it is
recorded as taken; figures quoted under it are not re-labelled.

**NOT RETROACTIVE.** `b_abstain_0.25` is judged under the rule as it stood on the day, and the
correction to (c) that decided it was itself post hoc and is recorded as such in
`reports/PREREG_prepress_v2_2026-09-22.md`.

## 11. Where to look

| | |
|---|---|
| the pool, the verdict, the latency | `pipeline/constrained/g3_final.py` |
| the head sweep and the weighted control | `pipeline/constrained/g2_multihead.py` |
| the 1 s and g100 region head inference | `pipeline/constrained/g1_ensprep_multi.py` |
| the decoder | `pipeline/constrained/sb2_structural.py`, `track2()` at line 307 |
| the arm options | `pipeline/constrained/night_arms.py`, `night_track()` |
| the gate rule | `sb2_structural.py`, `apply_gate()` at line 185 |
| the render | `pipeline/constrained/f3_render.py` |
| results | `runs/constrained/fh/g3_final/results.json` |
| the freeze | `runs/TRACKING_FROZEN_2026-09-18m.json` |
| the standing queue | `reports/MODEL_IMPROVEMENTS_QUEUE.md` |


**2026-09-23, batch 23e item 5, operator decision:** `y2_dial` stays refused; not re-measured on the drawn decode. `reports/REEVAL_f_amended_2026-09-23.md`.
