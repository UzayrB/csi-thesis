# Pre-registration: the five pool heads, retrained on the entry-straddling windows

> **Terminology corrected 2026-09-23 (batch 23c):** g100 is a 100-cell REGION posterior head ("g" is the grid kind, 100 the cell count), not a motion gate. Earlier text here called it "the gate head" and has been corrected; the JSON keys `gate_head_g100` and `g100_gate` are kept as identifiers and mean the same region head.

Written 2026-09-23, **before `x2_edgepool` was written or run**. Item 3 of the batch. The full ship
rule applies: this changes the DECISION, not the display.

---

## The operator's premise, and what I could verify of it before writing this

> "The 2 s lock reads the earliest windows of each walk, which overlap the edge the pool heads
> never saw."

**Half of that is confirmed and half of it is not, and the difference decides what the arm can be.**

**Confirmed: there is an excluded set, and it is exactly at the entry.** `rb1_truth.centre_rule`
tags a window `walk` when its CENTRE falls inside the pass and `walk_edge` otherwise.
`dataset.walking_windows` trains on `walk` alone. So a window that begins before the press and ENDS
inside the walk is discarded. There are **exactly two per pass, 480 per pairing, about 28 percent
of the training set**, measured. They are the only windows that straddle the tape entry.

**Not confirmed: that the lock reads them.** The decoder starts at `lo`, the first `walk` window,
with `display_lead_in_w = 0`. **Every window the lock reads is a `walk` window and is therefore
already represented in training.** The lock does not read a straddling window at all.

**So the arm cannot work the way the premise implies.** It cannot put unseen windows into the
head's mouth at inference, because the same windows are read either way. **What it can do is give
the head more training data covering the entry region**, and any gain must come through the
weights. That is a weaker and slower mechanism than "the lock sees something new", and this
pre-registration says so before the numbers exist so that a null result is not later reinterpreted
as a surprise.

## The conflict the operator's own rule creates, stated rather than resolved quietly

Item 2's rule is **"never label a pre-press position: it is unknown"**, and it is right.

**The five pool heads are CENTRE-labelled.** A straddling window's centre is, by the definition
that excluded it, BEFORE the press. **So there is no valid centre label for any of them**, and
"include the same edge windows, centre-labelled" is not a thing that can be done honestly.

> **THE TRAP, and it is live in the repository.** `dataset.py`'s `TDR_END_LABELS` mechanism does
> exactly the forbidden thing: it takes windows whose centre is before the press and labels them
> with the entry position, asserting the walker was at the tape entry while still approaching it.
> Four stages enable it. **No stage in this batch does**, and every stage here asserts it is off.

**The resolution, pre-registered:** the straddling windows enter labelled at a moment that is
REAL and at or after the press, accepting that this is a **label-offset inconsistency with the
head's centre convention** for those windows alone. Two choices of moment are defensible and both
are measured rather than argued between:

| arm | the straddling windows are labelled at | offset from the centre convention |
|---|---|---|
| **E0 `base_retrained`** | not added. Same windows, refitted, same seed and epochs | none. **This is the control** |
| **E1 `edge_end`** | the window END | up to +1.0 s |
| **E2 `edge_press`** | the PRESS, the tape entry, the earliest valid moment | up to +1.0 s, the other way |

**E0 is not optional.** Retraining moves a head on its own, and without the control a one-point
difference cannot be told from a refit. The edge arms' deltas are read against E0, never against
zero.

**If both E1 and E2 degrade, that is the finding**: a centre-labelled head cannot absorb windows
whose centre has no label, and the entry-straddling windows are genuinely unusable for the pool.
It is a real answer and it will be written up as one.

## What is measured

Over **all nine pairings, with the three session-01 test folds shown explicitly**:

- the **2 s lock** accuracy, which is what the arm is aimed at;
- the **committed line**, semi-bounded at the decoder's own end, and bounded;
- **per-line drawn/true ratios and per-line recall**, with **E_col1, E_col5, E_row1 and E_row5
  printed beside every pooled figure**, per the standing rule;
- the **substitution ratio** on the line and on the end;
- both **causal bounds**.

## The ship rule, unchanged and applied in full

- **(a)** the paired improvement interval on the **held-out folds** is entirely above zero;
- **(b)** the median paired delta is **at least two passes per pairing**, which at 120 passes is
  **at least 1.67 points**, compared as **integer passes** so a floating-point last bit cannot
  decide it;
- **(c)** per `SEMIBOUNDED_STATE.md` section 10, a **monotone response to the term's own weight**.
  **This arm has no weight**: a window is in the training set or it is not. **Condition (c) is
  therefore read as the monotone response to the AMOUNT of edge data**, and the arm is run at
  **0, 50 and 100 percent of the available straddling windows**, sampled by whole pass with the
  grouping asserted. If the response is not monotone in that fraction, (c) fails.
- plus **substitution passes** on the line and the end, **both causal bounds at or below zero**,
  and **(f) no edge line degraded**.

**Condition (f) has refused every lock arm this project has tried.** `E_both` bought +10.00 points
[2.02, 11.55] while taking E_col1 from 50.0 to 7.4 percent (NON-CAUSAL lock figures, 2026-09-23c; **causally +4.17 [0.71, 8.57], E_col1 42.59 to 0.00**) and was refused. The expectation
recorded here, before the run, is that (f) is the binding constraint again.

## Grouped splits, and the leakage guard

Training uses the same grouped splits as the existing heads: whole recordings per session, and
`dataset.sides` raises on any pass appearing on both sides. **The straddling windows carry the
`pass_id` of the pass they belong to**, so they group with it and cannot leak a test pass into
training through the back door. This is asserted in the stage, not assumed.

## If it ships, and if it does not

**Ships:** one render, one freeze, and the 62.50 headline re-measured over nine pairings **with its
interval**, both readings printed, difference of medians and median of paired deltas.

**Does not ship:** it is written up as a measured negative and **nothing changes**. The render from
item 1 stands.

---

## AMENDMENT, written 2026-09-23 01:05, BEFORE any item 3 code ran. Cost, and what it buys

Measured from the stage register rather than guessed: **`s2a_dispend` trains ONE head over nine
pairings in 31.3 minutes.** The pool is **five heads**, so one full pool retrain over nine pairings
is about **2.6 hours**.

The plan as written above is E0, E1 at 50 and 100 percent, and E2 at 50 and 100 percent: **five
full retrains, about 13 hours** before a single number is read. That is not a sensible use of the
night, and the honest response is to say what is dropped and why rather than to run a smaller thing
and describe it as the plan.

**DROPPED: E2 `edge_press`.** It would have told us whether the label-offset inconsistency matters
in the direction of the label as well as its size. It is dropped for cost alone, not because it was
answered. **If E1 ships or comes close, E2 is the first follow-up.**

**RE-ORDERED, and this one costs nothing:** run **E0 and E1 at 100 percent first**. Condition (c),
the monotone response, is only reached by an arm that has already satisfied (a) and (b).
**If E1 at 100 percent fails (a) or (b), the 50 percent run is not evidence about anything** and it
is skipped. This is an ordering, not a weakening: every condition that can refuse the arm still
runs, and (c) is never waived, only reached conditionally.

**Expected cost as amended:** about **5.2 hours** for E0 and E1 at 100 percent, plus roughly an
hour of evaluation, and a further 2.6 hours only if the arm is still alive.

## ISOLATION, added at the same time

**The shipped weights are never overwritten.** `artefacts.train_pairing` writes to
`model_path(tag, kind, ...)` inside whatever `TDR_ART_DIR` names, so retraining under the shipped
tag with different training windows would **silently replace the heads every quoted figure in this
project rests on**. Each arm therefore gets its **own artefact tree**: `TDR_ART_DIR`,
`ONE_S_TREES` and `G100_TREE` are all redirected per arm, and `_guard.assert_isolated` checks it
before the stage does any work. **`runs/artefacts_half`, `artefacts_fh1s`, `artefacts_g1s1`,
`artefacts_g1s2` and the g100 tree are read-only to item 3.**

---

## SECOND AMENDMENT, 2026-09-23 01:10, BEFORE any item 3 code ran. WHICH heads can be retrained

The first amendment scoped this arm on COST. On reading how the pool is actually built, cost is
not the binding constraint and the real one is worse.

**THE FIVE HEADS ARE NOT FIVE TRAINABLE OBJECTS IN THIS REPOSITORY.**

| head | what it is | can it be retrained here |
|---|---|---|
| the 0.5 s head | trained on `windows_half` by `artefacts.build_full_posteriors` | **yes** |
| 1 s seeds 0, 1, 2 | **frozen weights from `runs/artefacts/models`**, copied into scratch trees by `fh_ensprep` and `g1_ensprep_multi` and only INFERRED over the 0.5 s windows | **not safely** |
| the g100 region head | the same, a 100-cell configuration | **not safely** |

**Why "not safely" and not merely "expensive".** `fh_ensprep`'s own docstring records it:

> "the 1 s heads live in runs/artefacts/, the 0.5 s windows in runs/constrained/windows_half/, and
> **the feature cache is keyed WITHOUT the stride in its filename**. Pointing the artefact root at
> the shipped 1 s tree while the window root points at the half-stride windows would write
> half-stride features into the shipped tree and **corrupt 6.3 GB of it**."

Retraining a 1 s head on edge-augmented data means building a 1 s feature cache. **The operation
that builds it is the one documented as able to corrupt the shipped artefacts, because the cache
filename does not carry the stride.** This project has already been bitten once by exactly this
class of fault: a 1 s posterior tree read against 0.5 s recordings silently dropped half the passes
per recording and changed a verdict. **It is not being attempted unattended overnight.**

**SO ITEM 3'S ARM IS: THE POOL WITH ITS 0.5 s HEAD RETRAINED ON THE ENTRY-STRADDLING WINDOWS, THE
OTHER FOUR HEADS UNCHANGED.** That is one head of five, and **the reported result says so in those
words**. It is a real, well-defined arm: the four frozen heads are inferred identically in both
conditions, so the comparison isolates the half-stride head exactly.

**What this cannot answer**, stated now rather than discovered later: whether retraining all five
together would do more. It probably would, since four fifths of the pool is untouched, and **a null
result here is therefore evidence about one head and not about the idea**. If this arm shows
anything, retraining the 1 s heads properly, with a stride-keyed cache built in isolation, is the
follow-up and it needs its own batch and someone awake.

**The cost falls with the scope:** about **31 minutes per arm** over nine pairings rather than 2.6
hours, so E0, E1 at 100 percent and, if it survives (a) and (b), E1 at 50 percent all fit
comfortably. **The labelling, the ship rule, the edge-line condition and the isolation requirement
above are unchanged.**

---

## THIRD AMENDMENT, 2026-09-23 01:35, BEFORE any arm ran. The reproduction check

**The `shipped` arm exists to prove the harness before any comparison is believed.** It trains
nothing and decodes the shipped pool through `x2_edgepool`'s own loop, so it must reproduce what
`t6_lockdiag` already measured on the same evidence:

| quantity | `t6_lockdiag`, nine pairings, 1080 passes | bar for `x2_edgepool` `shipped` |
|---|---|---|
| the 2 s lock | **49.17 percent** | within **one pass per pairing, 0.83 points** |
| the committed line | **62.50 percent** | within **one pass per pairing** |

Both stages read `display_locked["2\|2.0"]` at `lag_w = 2`, `delay = 2.0 s`, lock step index 2, so
they are naming the same object and an exact match is the expectation rather than a hope.

> **IF THE `shipped` ARM MISSES EITHER BAR, THE HARNESS IS WRONG AND EVERY COMPARISON BUILT ON IT
> IS VOID.** The arms are then not reported as results, the fault is found first, and the run is
> repeated.

**This is written because the same check has already earned its place twice tonight.** In
`w1_dotphase` a pre-registered reproduction check caught a harness built on the wrong convention,
which reported a dot a full second behind the drawn one, and then caught a pairing key that was not
unique across the nine pairings and silently paired each walk against another pairing's copy of
itself. Neither was visible in any aggregate; both would have been reported as findings.


### Correction to the third amendment, 2026-09-23 02:06, still before any arm ran

**The check as first written compared two different statistics and would have been meaningless.**
`t6_lockdiag`'s `line_pct_all9` is the **MEDIAN OF THE NINE PER-PAIRING RATES**, not a rate pooled
over 1080 passes. The first version of the check compared this stage's POOLED rate against that
median. Those are free to differ by more than one pass with nothing wrong, so the check would have
either passed by luck or voided a sound run.

**How it surfaced, which is the useful part.** A one-pairing smoke test of the `shipped` arm on
`s01_to_s02` returned a 2 s lock of **49.1667 percent**, a semi-bounded line of **62.50** and a
bounded line of **65.83** — all three matching the nine-pairing figures exactly. Three exact
matches from a single pairing is not a validation, it is a warning, and it turned out that
`s01_to_s02` simply IS the median pairing on all three.

**The check now takes the median of this stage's own per-pairing rates**, prints the pooled reading
beside it because the two have disagreed in sign before, and **requires all nine pairings to be
present**, so a partial run can never satisfy it.

---

## THE PREMISE, NOW MEASURED. 2026-09-23 02:18, still before any arm ran

The pre-registration above said the operator's premise was half confirmed and half not, and that
the unconfirmed half was whether the 2 s lock actually reads the entry-straddling windows. **It is
now measured over all 360 passes, from the recording metadata, and the answer is unambiguous.**

| | |
|---|---|
| passes | **360** |
| entry-straddling windows found | **720, exactly 2.00 per pass** |
| of those, strictly BEFORE the decoder's first window `lo` | **720. All of them** |
| of those, inside the lock's own window range `lo` to `lo+4` | **0** |
| index gap from the last straddling window to `lo` | **exactly 1, on every pass** |

> **THE LOCK NEVER READS AN ENTRY-STRADDLING WINDOW. Not once in 360 passes.** They sit exactly one
> index below the first window the decoder looks at, every time.

**So the mechanism is settled before the arm runs, and it is the weaker of the two.** Adding these
windows cannot put new evidence in front of the lock at inference, because the lock reads the same
windows either way. It can only change the head's WEIGHTS, by giving it 28 percent more training
data covering the entry region. Any gain has to arrive through that, and a null result is
therefore unsurprising rather than a refutation of the idea.

**This is recorded now so that the interpretation cannot be chosen after the numbers arrive.** If
the arm gains, the explanation is better weights near the entry and not "the lock saw more". If it
does not, the honest statement is that 28 percent more entry-region training data did not move a
head whose read windows were unchanged, on one head of five.

---

## THE REPRODUCTION CHECK, RUN. 2026-09-23 02:47. **PASSES EXACTLY**

Arm `shipped` trains nothing and decodes the shipped pool through this batch's own loop.

| reading | 2 s lock | semi-bounded line |
|---|---|---|
| `t6_lockdiag`, median of nine | 49.1667 | 62.5000 |
| **`x2_edgepool` shipped, median of nine** | **49.1667** | **62.5000** |
| **delta, bar ±0.8333** | **+0.0000** | **+0.0000** |

**Exact on both. The harness is validated and the comparisons built on it are reportable.**

### The correction at 02:06 was not academic

The same arm's POOLED readings are **47.8704** and **59.5370**. Against `t6`'s medians those are
**-1.30 and -2.96 points**, both outside the ±0.83 bar. **The check as originally written would
have declared this sound harness VOID and thrown away the whole of item 3.** The fault was mine,
it was caught by a one-pairing smoke test whose three exact matches looked like success, and the
fix was to compare the same statistic on both sides.

### The per-pairing spread, which is why no decision rests on one pairing

| pairing | 2 s lock | semi-bounded |
|---|---|---|
| s01_to_s02 | 49.2 | 62.5 |
| s01_to_s03 | 45.0 | 50.0 |
| **s02_to_s01** | **25.0** | **30.0** |
| s02_to_s03 | 57.5 | 85.8 |
| **s03_to_s01** | **25.8** | **25.8** |
| s03_to_s02 | 60.0 | 75.0 |
| **s0203_to_s01** | **28.3** | **31.7** |
| s0103_to_s02 | 67.5 | 86.7 |
| **s0102_to_s03, the demo pairing** | **72.5** | **88.3** |

**The lock ranges from 25.0 to 72.5 percent across the nine.** The demonstration pairing is the
**best of the nine on both measures**, which is why it is never the basis for a decision.

**All three session-01 folds sit at the bottom**, 25.0, 25.8 and 28.3 on the lock. That is the
session-01 shift this project has been unable to move with any arm, and item 3 is not expected to
move it either.

---

## THE NO-OP CHECK, recorded 2026-09-23 03:48, BEFORE the edge100 arm started

**The worst outcome available to this arm is not a negative result. It is a SILENT no-op**: if the
edge flag fails to reach `dataset.walking_windows`, `edge100` trains on exactly the same windows as
`base`, returns a delta of zero, and reads as a clean, well-controlled null. Nothing in the numbers
would give it away.

So the training-set size is pinned per pairing **before the arm runs**. `edge100` must log the
right-hand column; if it logs the left, the flag silently failed and **the arm is void, not null**.

| train set | must NOT be (edge off) | **must be (edge on)** | added |
|---|---|---|---|
| s01_to_s02 | 1056 | **1296** | +240 |
| s01_to_s03 | 1056 | **1296** | +240 |
| s02_to_s01 | 1075 | **1315** | +240 |
| s02_to_s03 | 1075 | **1315** | +240 |
| s03_to_s01 | 1089 | **1329** | +240 |
| s03_to_s02 | 1089 | **1329** | +240 |
| s0203_to_s01 | 2164 | **2644** | +480 |
| s0103_to_s02 | 2145 | **2625** | +480 |
| s0102_to_s03 | 2131 | **2611** | +480 |

**The `base` arm has already logged the left-hand column on all nine**, which confirms the control
ran without edge windows and that these numbers are the right reference rather than a guess. The
counts are also recorded per pairing in each arm's `results.json` under `training_windows`, so the
check can be made from the saved artefact and not only from a log that could be overwritten.

*One session of walk windows contributes 240 straddling windows, two sessions 480: 2 per pass,
120 passes per session. The arithmetic closes exactly, which is itself a check on the selection.*

---

## THE REFIT CONTROL, RUN. 2026-09-23 04:02. `base` against `shipped`, nine pairings, 1080 passes

`base` is the same head on the same windows, refitted with the same seed and epochs. Its training
counts matched the pre-registered edge-OFF column on **all nine pairings**, so it is confirmed to
have run without edge windows.

| | |
|---|---|
| pairings where the **2 s lock** differs at all | **0 of 9** |
| **individual pass lock decisions** that differ | **0 of 1080** |
| pairings where **semi-bounded** differs | 1 of 9 |
| **individual semi-bounded lines** that differ | **36 of 1080** |
| net effect on semi-bounded | 59.5370 to 59.4444, **one pass in 1080** |

> **REFITTING THE 0.5 s HEAD DOES NOT MOVE THE 2 s LOCK AT ALL. Not one pass in 1080.**

**This is the single most useful thing the control could have said**, because the 2 s lock is
exactly what item 3 is aimed at. The refit contributes **exactly zero** noise to the primary
measure, so **any lock difference `edge100` shows is attributable to the training data and to
nothing else**. There is no refit term to subtract and no ambiguity to argue about.

**The semi-bounded figure behaves quite differently and it is worth seeing.** Thirty-six individual
answers move under a refit, and they very nearly cancel: the aggregate shifts by one pass. **An
aggregate that moves by one pass is hiding 36 that moved.** Any future comparison on the
semi-bounded line, unlike the lock, carries that much refit noise underneath it and a delta of a
pass or two there means considerably less than the same delta on the lock.

### The no-op check, passed

`edge100` logged **1296** training windows for `s01_to_s03` against a pre-registered requirement of
1296 and a `base` value of 1056. **The edge flag is reaching the training set**, so a zero result
from this arm will be a real null rather than a silent no-op.
