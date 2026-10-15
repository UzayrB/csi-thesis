# The 2 s lock is quoted at a horizon it cannot reach live

2026-09-23. Found while answering item 1 and confirmed by `y2a_causal`, which was written to gate
item 2 and did. **Nothing has been changed as a result of this document.** It changes what item 2's
target means, so it is written before item 2's sweep runs.

---

## The finding in one line

**Two different quantities in this repository are both called "the 2 s lock", and they are the
same estimator at two different evidence horizons. Every figure item 2 is aimed at is quoted at
the horizon the live system cannot reach.**

## The two, and they are now identified exactly

| | reads windows up to | held-out 7 | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|---|
| **the render's lock**, `night_arms` `display_locked`, what is actually drawn | `lo + step` | **57.50** | 42.59 | 77.78 | **35.19** | 57.41 |
| `y2a_causal` `proxy_extra0` | `lo + step` | **57.50** | 42.59 | 77.78 | **35.19** | 57.41 |
| **the quoted lock**, `t6`/`t7`/`t9`/`FINDING_pooled_vs_edge` | `lo + step + LAG_W` | **60.83** | **50.00** | 72.22 | **74.07** | 64.81 |

> **Qualified 2026-09-23 (batch 23c):** they agree on those aggregates, NOT on every pairing. The
> render lock (`night_track`) reads s03_to_s01 25.83, s0203_to_s01 28.33, s0103_to_s02 67.50 and
> s03_to_s02 60.00 where the proxy reads 25.00, 27.50, 66.67 and 59.17, one pass apart on four of
> nine pairings (`y4_pressalign` rows against `t7_lockarms`). The medians and edge figures coincide.

**Rows one and two agree on the held-out median and on all four edge lines, to the decimal.** That
is not a near miss, it is an identification: the renderer's causal lock and the diagnostic proxy
are one estimator, and the only difference between the proxy and the quoted baseline is
**`LAG_W` = 2 windows = 1.0 s of lookahead**.

## Why `lo + step` is the causal horizon, and `lo + step + LAG_W` is not

This is the renderer's own rule, not a new one. `night_arms` asserts it by name:

```python
lw0 = int(round((WINDOW_S / 2.0) / stride_s))      # = 2 windows = 1.0 s
ev_w = int(lw) - lw0
if ev_w < 0:
    raise AssertionError(... "cannot be drawn causally")
```

A 2 s window has not finished recording until `LAG_W` windows after the moment it names. At the
2 s lock the display may read radio up to `press + 2.0 s`, which is window index `lo + 4`; the
windows that have finished by then are those indexed `<= lo + 4 - LAG_W = lo + 2`, and `lo + 2` is
`lo + step`, the window the lock names. The renderer draws at `ev_w = 0` and reads no further.

**The diagnostic reads to `lo + step + LAG_W`.** Those last two windows are still recording at the
moment the lock is taken.

## What that does to item 2's target

| | as quoted, `extra = 2` | at the causal horizon, `extra = 0` |
|---|---|---|
| shipped lock, held-out 7 | 60.83 | **57.50** |
| chain-total lock, held-out 7 | 73.33 | **65.00** |
| **the prize** | **+12.50** | **+7.50** |

**The +12.5 is real arithmetic on numbers that a live lock cannot produce.** Collected causally the
same estimator change is worth **+7.50**, still large, and still refused by condition (f): at the
causal horizon the chain-total lock takes E_col1 from 42.59 to 29.63 and E_row1 from 35.19 to
24.07.

## And what it does to condition (f)

**Condition (f) has been defended on E_col1 = 50.0.** That is the quoted horizon's figure. The
E_col1 the demonstration actually draws is **42.59**. Likewise E_row1: the operator's item 1
premise, "35.2 at the lock against 83.3 committed", is the **render** figure and is correct; the
74.07 that `t6` and `t7` report for the same line is the lookahead horizon.

The four edge lines do not even rank the same way at the two horizons, so an arm selected to
protect them at one horizon is not selected to protect them at the other.

## What this does NOT say

- **It does not say the shipped system is non-causal.** The renderer is causally tight, reports
  both bounds per rule 5, and is enforced by `tests/test_render_rules.py`. The leak is in the
  DIAGNOSTIC stages that have been used to choose between estimators, not in what ships.
- **It does not void the committed answer or the 62.50 headline.** Those come from the full-walk
  decoder, which is entitled to the whole walk. Nothing here touches them.
- **It does not mean the earlier arms were wrongly refused.** `t7`'s arms were refused, and at the
  causal horizon they are still refused, more heavily. The rule held in both conventions.

## A hypothesis of mine, measured and REFUTED. Do not re-propose it

I read in `night_arms` that the locked line falls back by name when the free path is off-chain:

```python
nm_lock = free[li]["line"] or entry_nm or st.names[0]        # st.names[0] is A_fwd
```

and proposed that this alphabetical fallback was a cause of the A_fwd over-draw, which is 2.620
drawn-over-true at the render lock. **`y1b_locksrc` measured it over all 1080 passes:
`lock_line_source` is `path` on 1080 of 1080. The fallback never fires.** It is a latent hazard,
not a current cause, and the A_fwd over-draw is not explained by it. This joins TX proximity and
RX1 axis symmetry on the list of refuted explanations for A_fwd.

`night_arms` now records `lock_line_source` per walk so the question cannot be asked twice.

## What item 2 does about it

Item 2's sweep is judged at the **causal horizon**, and its baseline is **57.50 with E_col1 at
42.59**, not 60.83 with E_col1 at 50.0. The pre-registration
`reports/PREREG_lockmix_2026-09-23.md` is amended to say so before the sweep runs, and the
amendment is dated and labelled.

## What item 2 then found at the causal horizon. REFUSED, by one pass

`y2_dial` swept the mix dial at w in {0.00, 0.05, 0.10, 0.15, 0.20, 0.25}, both scores reading
`lo .. lo + step` and no further. **The reproduction check passed**: w = 0 returned 57.50 held-out
with edge recall 42.593 / 77.778 / 35.185 / 57.407, the renderer's own figures to three decimals.

| w | pooled | all 9 | held-out 7 | E_col1 | E_col5 | E_row1 | E_row5 | substitution | (f) |
|---|---|---|---|---|---|---|---|---|---|
| **0.00** | 47.41 | 49.17 | **57.50** | 42.59 | 77.78 | **35.19** | 57.41 | 0.941 | **holds** |
| 0.05 | 48.33 | 50.00 | 59.17 | 42.59 | 79.63 | **33.33** | 59.26 | 0.924 | fails |
| 0.10 | 49.63 | 51.67 | 61.67 | 42.59 | 79.63 | **33.33** | 57.41 | 0.913 | fails |
| 0.15 | 49.91 | 50.83 | 62.50 | 42.59 | 79.63 | **33.33** | 57.41 | 0.902 | fails |
| 0.20 | 50.65 | 50.83 | 62.50 | 42.59 | 79.63 | **33.33** | 57.41 | 0.887 | fails |
| **0.25** | 50.83 | 50.00 | **62.50** | 42.59 | **79.63** | **33.33** | 57.41 | 0.862 | fails |

**The selection rule returned w = 0 and the arm is REFUSED. Nothing was changed.**

**But look at what it is refused for.** At the causal horizon the mix buys **+5.00 points
held-out**, and the entire edge cost is **one pass of E_row1**, 35.185 to 33.333. E_col1 does not
move at all, at 42.59 on every weight. **E_col5 GAINS one pass**, 77.78 to 79.63. Taken as a
group the four edge lines are exactly level: minus one pass, plus one pass.

This is not the trade `FINDING_pooled_vs_edge_2026-09-22` describes. There, taking the pooled gain
cost E_col1 half its recall and the edge mean fell from 65.3 to 27.3. Here the pooled gain is
smaller, +5.00 rather than +12.50, and the edge cost is a single walk.

**Condition (f) is per line and it refuses this, and that refusal stands.** Overriding it now,
having seen that the arm clears everything else, is precisely the post hoc move the project
refused on 2026-09-22 and again on 2026-09-23, and the reasoning does not change because the cost
is small. **This is for the operator to decide, not for me to decide by relaxing a rule after
seeing which way it fell.** What is new and worth their attention is that the choice is now
"5 points of pooled lock accuracy against one pass of one edge line", which is a different
question from the one they answered on 2026-09-22.

## THE OPERATOR'S DECISION, 2026-09-23 (batch 23c): (f) STANDS AS WRITTEN, THE REFUSAL STANDS

**Decided by the operator, recorded as a finding and not as an open question:**

> (f) stays as written, and y2_dial's refusal stands. Record it as a finding (+5.00 held-out,
> refused by one pass, zero net change across the four edge lines). No retroactive rule change.

**THE FINDING.** At the causal horizon the best-path / chain-total mix buys **+5.00 points
held-out** (57.50 to 62.50 at w = 0.15 to 0.25) and is **refused under condition (f) by ONE pass of
E_row1** (35.19 to 33.33), while E_col5 **gains one pass** (77.78 to 79.63) and E_col1 and E_row5 do
not move. **Net change across the four edge lines: zero passes.** Condition (f) is per line, and a
per-line rule refuses a trade that nets to zero across lines. That is what it was written to do,
and it is not changed after seeing which way this fell.

The mix is not shipped, not queued, and not re-proposed with a relaxed (f). The render lock is
unchanged at 57.50.

## Where the numbers live

`runs/constrained/fh/y2a_causal/results.json` (the three horizons),
`runs/constrained/fh/y1b_locksrc/results.json` (the render lock and the fallback census),
`runs/constrained/fh/y1_diag/results.json` (the proxy, the joint confusion, the E_row1 posterior),
`runs/constrained/fh/t7_lockarms/results.json` (the original weight sweep).
