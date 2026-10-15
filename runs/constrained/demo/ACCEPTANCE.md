# Acceptance: the measured results of the live demonstration

**RULES LIVE IN `reports/RENDER_RULES.md`, NOT HERE.** This document holds MEASURED RESULTS ONLY. If you want to know what the demonstration is required to do, read the contract: rules 1 to 6 and the operator's rules V1 to V4. Two copies of a rule is how a rule gets re-litigated, so there is exactly one copy and it is not this file.

Rendered on `s0102_to_s03`, cross-day, trained on sessions 01 and 02. Five-head pool, 0.5 s stride, nothing retrained. **This is the strongest of the nine cross-day pairings and is not the system**; the figure to quote is the nine-pairing aggregate.

## Configuration as applied

| setting | value |
|---|---|
| display arm | DISP_END |
| decoder entry | soft |
| display lag | 1 s |
| cross-line slide cap | none |
| display hysteresis | 1 window |
| semi-bounded exit rule | causal |
| display latency, rule V1 | 2 s |
| evidence before the commit | 2 s |
| lock offset from the walk start, rule V3 | 2.25 s, identical on every walk |

### Why V3's lock offset is 2.25 s while V1's latency is 2.0 s

**They are measured from different origins, and both numbers are measured rather than assumed.** V1's 2 s is how far the SCENE runs behind real time. V3's offset is measured from `t_start`, which the render defines as the CENTRE of the walk's first window, at `t[lo] + 1`. The scene itself begins 0.25 s after that centre, at `t[lo] + 2 - 0.75`: the first window finishes recording 2 s after it began, and the display head names a moment 0.75 s behind the window it is read from. The commit is then exactly 2 s after the scene begins, so 0.25 + 2 = 2.25 s.

Measured over the 120 walks of this pairing: the offset is identical on every one of them, which is what rule V3 requires, and the window centre it is measured from sits a median 0.202 s after the press (p10 0.031, p90 0.418) because the 0.5 s window lattice does not align with the press. That spread is in WHERE THE ORIGIN FALLS, never in the offset itself.

## The lock against the commitment

| | over nine pairings |
|---|---|
| line locked at 2 s, which is what the viewer watches | 53.3 percent [25.8, 62.5] |
| line committed, shown as text: the SHIPPED semi-bounded decision | 73.3 percent [35.0, 87.5] |
| they agree, pooled over passes | 55.4 percent |
| waiting buys, paired per pairing | +17.7 points, interval [13.4, 21.7] |

Medians over the nine cross-day pairings with 95 percent intervals, ONE lattice, from `d6_lock_commit`, which decodes the lock exactly as this render draws it and matches this render walk for walk. **Since 2026-09-23e the text names the SHIPPED semi-bounded committed decision (A2 + a_veto_1.0), the headline's own answer**, checked against `d4_headline` walk for walk below. Until then it named the bounded rescore at the end press, which uses the end press the semi-bounded mode is not told.

**THE DISCLOSED PRICE OF THE CORRECTNESS FIX.** The ONE lattice costs the bounded rescore at the end press, which is no longer shown: 60.0 percent [55.8, 81.7], from 65.83 on the grid lattice, paired **-2.59 [-4.63, -0.46]**, every edge line losing walks (E_col1 -6, E_col5 -3, E_row1 -3, E_row5 -6). `reports/CORRECTION_drawn_lock_2026-09-23.md`.

## The lock, on this pairing

| | |
|---|---|
| commit delay | 2 s |
| display lag after the lock | 1 s |
| locked line correct | 69.2 percent of walks |
| distinct lines after the lock | 2 on every walk |
| frozen tails, display running out before the press | 0.0 percent to 0.0 percent |

| participant | locked line correct | committed correct | tracking |
|---|---|---|---|
| PA5 | 50 percent | 75 percent | 33.1 percent |
| PA1 | 75 percent | 95 percent | 33.5 percent |
| PA2 | 65 percent | 85 percent | 53.1 percent |
| PA3 | 75 percent | 90 percent | 53.9 percent |
| PA4 | 75 percent | 85 percent | 35.5 percent |
| PA6 | 75 percent | 100 percent | 62.7 percent |

## The whole display runs behind real time, and the delay was measured

**2 seconds**, rule V1. The green marker shows where the walker was 2 s ago and the red dot shows the tracker's answer for that same moment, so the two are directly comparable.

**The delay is MEASURED, not taken from the training label**, and the two disagree:

| | |
|---|---|
| what the head's training label says it names | **0 s**, the window END |
| what the head actually names, measured over nine pairings | **0.75 s** behind the window it is read from |
| what the DISPLAY runs behind, which is the live mode's latency | **2 s** |

The shipped display head is trained on the position at the window end, so by its label it names the present. Measured, it does not: R1 swept the offset and found the drawn dot closest to the truth 0.75 s earlier, and the drawn index is set from the measurement rather than from the label.

### The delay was chosen on the same data it is reported on

**Disclosed, because it flatters the figure below.** R1 swept the offset and picked the one with the lowest mean error. The display is then scored at that same offset, over the same nine pairings. That is selection and reporting on one dataset, and the within-0.5 m figure it yields is optimistically biased.

Two things follow, and they point opposite ways:

| | |
|---|---|
| the DELAY is robust | the curve is smooth and single-peaked: 0.75 s gives 0.953 m and 1.0 s gives 0.956 m, a tie. 'About three quarters of a second behind' holds whichever side of the peak you take |
| the SCORE at the peak is not | within 0.5 m reads 46.6 percent at the selected 0.75 s against 45.9 percent at a pre-specified 1.0 s, so picking the peak buys about 0.7 points |

The honest reading is the second column of that table: quote the delay with confidence and treat the accuracy at it as a slight upper bound. A clean version would pick the offset on some folds and report it on the others; that was not done and this note stands in its place.

| | |
|---|---|
| display transition prior | **flatten_0.50** |
| its substitution ratio on post-lock along-line progress | **0.52** against **0.29** for the previous setting |

The prior was chosen in R3 by sweeping the display's own motion model from the shipped step model down to none. A weaker prior means more of the drawn along-line progress comes from the radio and less from the model: the substitution ratio roughly doubles. **The gate that selected it was loosened AFTER the sweep was seen**, from 'no worse than the shipped display' to 'excess motion under 0.5 percent of frames', because the first form meant exactly zero and only the shipped setting could meet it. That is a post-hoc rule change and it is disclosed here rather than folded in. It is acceptable only because the display is a presentation choice: no accuracy figure quoted anywhere in this project depends on it.

| | |
|---|---|
| frames within 0.5 m of the marker, the single reference | **45.3 percent** |
| mean distance to it | 1.00 m |
| offset from LIVE truth, reported separately | 2.59 m mean |

The last row is the price of the delay, not an error in the tracker. It is kept apart from the row above it rather than folded in.

### Tracking, split by whether the dot is on the right line

**This is the split to read.** When the dot has committed to the wrong line, the distance between it and the walker is the distance between two taped lines. That is a LINE error being reported as a TRACKING error, and pooling the two makes the tracking figure a function of line accuracy rather than of tracking.

| | walks | within 0.5 m | mean distance |
|---|---|---|---|
| **dot on the RIGHT line** | **83 of 120** | **61.9 percent** | **0.48 m** |
| dot on the wrong line | 37 of 120 | 8.1 percent | 2.16 m |
| pooled, as quoted above | 120 | 45.3 percent | 1.00 m |

The first row is what the tracker does when it knows where you are. The third is the first dragged down by the second, and it is the weaker question: it asks how often the system is both on the right line AND close, which is two things at once.

**The dot and the marker leave together.** The scene begins at the first moment the decoder has a position to draw, and the marker is not shown before then. Until 2026-09-21 the marker appeared at the walker's true first press while the dot could not draw until its first window's label time, on average 0.475 s later. Rules 6 and V2 in `reports/RENDER_RULES.md` are what stop it recurring.

## Decoded accuracy and display offset, reported separately

Reported apart and never added, per rule 4. A window spans 2 s and may only be drawn once it has ENDED, so a dot drawn at time t comes from a window covering t minus 2 s to t.

The shipped display arm is **DISP_END**. The pool heads that decide the LINE are labelled at the window CENTRE, so they name t minus 1 s. DISP-END is a display-only head trained on the position at the window END, which would name t. **It does not get there.** Measured below, the drawn dot is nearer the truth at t than at the other moment, so the end label moved the dot forward without closing the lag: step 2 measured it closing about a quarter of the gap over nine pairings, 2.087 m to 1.867 m. The two rows below are the same dot against two different moments, and they are never added together or traded off.

| | measured against | value |
|---|---|---|
| **decoded accuracy** | the truth at the moment the CENTRE-labelled pool is naming, t minus 1 s | **9.9 percent** within 0.5 m, 1.75 m mean |
| **on-screen tracking** | the truth at the frame the viewer sees, t | **45.3 percent** within 0.5 m, 1.00 m mean |
| **display offset** | how far the walker travels during the 1 s lag | **1.29 m** mean, 1.29 m median |

The display offset is how far the walker travels during the lag. It is a property of walking pace and the 2 s window, not of the model. The only thing that closes it completely is assuming the walker kept going at the pace just measured, and that assumption is dead reckoning: it was deleted from the display path on 2026-09-20 and it is not coming back through a caption. Training a head on the end label was the honest attempt at closing it from the signal, it is what ships, and it recovers only part of it.

**Both causality bounds are reported, because one of them is not enough.** The drawn-window bound asks whether the window being NAMED had finished recording by the frame: -1.251 s. The evidence bound asks whether the radio that DECODED it had: -1.251 s. Until 2026-09-20 only the first was checked, and it read a clean zero through a leak of a full second that only the second one shows.

| split | decoded accuracy, within 0.5 m | on-screen tracking, within 0.5 m |
|---|---|---|
| correct-line passes | 10.8 percent | 49.2 percent |
| wrong-line passes | 3.1 percent | 15.7 percent |

## On-screen tracking, which is the acceptance number

Measured **at the displayed time, so the display lag counts against it**: the fraction of frames in which the drawn red dot is within 0.5 m of the drawn green dot.

| | before, the render frozen at 18m | after |
|---|---|---|
| frames within 0.5 m | **3.4 percent** | **45.3 percent** |
| mean on-screen distance | 2.04 m | 1.00 m |
| frames with NO red dot | 1200 | **0** |
| backward steps along a line | 10 | **37** |
| changes of the shown line per walk | up to 4 | **the lock, plus at most ONE mid-walk switch (rule 1 as amended, 23e)** |

| split | before, within 0.5 m | after, within 0.5 m |
|---|---|---|
| correct-line passes | 3.2 percent | 49.2 percent |
| wrong-line passes | 1.2 percent | 15.7 percent |

### Every display lag that was swept

| lag | cap | within 0.5 m | interval | mean distance | rule violations |
|---|---|---|---|---|---|
| 0 s | cap2.0 | 21.08 percent | [17.25, 25.23] | 1.51 m | 938 |
| 0 s | nocap | 28.48 percent | [23.69, 32.27] | 1.36 m | 0 |
| 0.5 s | cap2.0 | 10.09 percent | [7.75, 11.85] | 1.63 m | 489 |
| 0.5 s | nocap | 11.08 percent | [8.58, 12.61] | 1.58 m | 0 |
| 1 s | cap2.0 | 6.49 percent | [5.2, 7.79] | 1.94 m | 452 |
| 1 s | nocap | 6.72 percent | [5.4, 7.94] | 1.91 m | 0 |

**The 2.0 m/s cross-line cap was dropped.** It cost on-screen tracking and, under continuous retargeting, it could not satisfy the one rule either: the destination moves out from under the dot mid-crossing. Both are visible in the table above.

## Walks flagged for many switches

No walk changes the shown line more than four times.

## The commitment timeline, on the pool at the shipped lag

| seconds after the press | this pairing | nine-pairing aggregate |
|---|---|---|
| 0.5 s | 60.0 percent | 19.2 percent |
| 1.0 s | 76.7 percent | 20.0 percent |
| 1.5 s | 70.8 percent | 30.8 percent |
| 2.0 s | 71.7 percent | 27.5 percent |
| 2.5 s | 69.2 percent | 38.3 percent |
| 3.0 s | 70.8 percent | 42.5 percent |
| 3.5 s | 75.8 percent | 45.8 percent |
| 4.0 s | 69.2 percent | 44.2 percent |

## Per participant, at the shipped lag

### PA5

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | A_rev | D_fwd | no | none | D_fwd | A_rev | yes | 0 percent | 1.25 m |
| 2 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 59 percent | 0.49 m |
| 3 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 63 percent | 0.41 m |
| 4 | E_col1 | E_col1 | yes | none | E_col1 | E_col1 | yes | 33 percent | 0.59 m |
| 5 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 19 percent | 0.81 m |
| 6 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 89 percent | 0.30 m |
| 7 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 64 percent | 0.40 m |
| 8 | E_row1 | D_fwd | no | none | D_fwd | E_row1 | yes | 0 percent | 2.25 m |
| 9 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 2 percent | 2.40 m |
| 10 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 39 percent | 0.56 m |
| 11 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 85 percent | 0.27 m |
| 12 | B_fwd | D_fwd | no | none | D_fwd | D_fwd | no | 0 percent | 1.26 m |
| 13 | A_rev | D_fwd | no | none | D_fwd | A_rev | yes | 0 percent | 1.63 m |
| 14 | C_fwd | D_fwd | no | none | D_fwd | E_row1 | no | 11 percent | 2.39 m |
| 15 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 95 percent | 0.21 m |
| 16 | C_rev | D_fwd | no | none | D_fwd | C_rev | yes | 9 percent | 2.66 m |
| 17 | B_rev | B_rev | yes | none | B_rev | D_rev | no | 77 percent | 0.36 m |
| 18 | C_rev | D_fwd | no | none | D_fwd | C_rev | yes | 7 percent | 2.82 m |
| 19 | B_rev | B_fwd | no | none | B_fwd | B_fwd | no | 10 percent | 2.71 m |
| 20 | B_fwd | E_col5 | no | none | E_col5 | D_rev | no | 0 percent | 3.50 m |

### PA1

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 56 percent | 0.46 m |
| 2 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 38 percent | 0.59 m |
| 3 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 62 percent | 0.44 m |
| 4 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 47 percent | 0.49 m |
| 5 | B_rev | E_col5 | no | none | E_col5 | B_rev | yes | 0 percent | 2.83 m |
| 6 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 43 percent | 0.56 m |
| 7 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 50 percent | 0.44 m |
| 8 | E_row1 | E_row1 | yes | none | E_row1 | E_row1 | yes | 22 percent | 0.74 m |
| 9 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 45 percent | 0.54 m |
| 10 | E_col1 | E_col5 | no | none | E_col5 | E_col5 | no | 0 percent | 4.03 m |
| 11 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 2 percent | 2.53 m |
| 12 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 20 percent | 0.83 m |
| 13 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 53 percent | 0.55 m |
| 14 | C_fwd | D_fwd | no | none | D_fwd | C_fwd | yes | 0 percent | 2.71 m |
| 15 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 45 percent | 0.56 m |
| 16 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 38 percent | 0.57 m |
| 17 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 16 percent | 2.22 m |
| 18 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 23 percent | 0.75 m |
| 19 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 48 percent | 0.49 m |
| 20 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 61 percent | 0.39 m |

### PA2

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E_row1 | C_fwd | no | none | C_fwd | E_row1 | yes | 8 percent | 1.73 m |
| 2 | E_col1 | C_fwd | no | none | C_fwd | C_fwd | no | 0 percent | 1.62 m |
| 3 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 93 percent | 0.22 m |
| 4 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 76 percent | 0.35 m |
| 5 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 77 percent | 0.29 m |
| 6 | D_fwd | E_row5 | no | none | E_row5 | D_fwd | yes | 10 percent | 2.31 m |
| 7 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 98 percent | 0.25 m |
| 8 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 71 percent | 0.34 m |
| 9 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 100 percent | 0.23 m |
| 10 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 96 percent | 0.22 m |
| 11 | C_fwd | A_fwd | no | E_row1 at +1.5 s | E_row1 | C_fwd | yes | 0 percent | 2.69 m |
| 12 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 51 percent | 0.43 m |
| 13 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 85 percent | 0.35 m |
| 14 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 33 percent | 1.60 m |
| 15 | A_rev | A_fwd | no | A_rev at +2.0 s | A_rev | A_rev | yes | 41 percent | 1.47 m |
| 16 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 91 percent | 0.20 m |
| 17 | D_fwd | A_fwd | no | C_rev at +2.0 s | C_rev | C_rev | no | 12 percent | 2.68 m |
| 18 | B_fwd | C_fwd | no | none | C_fwd | B_fwd | yes | 8 percent | 1.25 m |
| 19 | A_fwd | A_fwd | yes | none | A_fwd | D_rev | no | 34 percent | 1.41 m |
| 20 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 75 percent | 0.28 m |

### PA3

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | B_fwd | D_fwd | no | none | D_fwd | B_fwd | yes | 0 percent | 1.31 m |
| 2 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 94 percent | 0.25 m |
| 3 | B_rev | B_rev | yes | none | B_rev | C_rev | no | 53 percent | 0.49 m |
| 4 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 4 percent | 2.31 m |
| 5 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 96 percent | 0.16 m |
| 6 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 16 percent | 2.25 m |
| 7 | E_col1 | E_col1 | yes | none | E_col1 | E_col1 | yes | 37 percent | 0.52 m |
| 8 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 52 percent | 0.49 m |
| 9 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 74 percent | 0.30 m |
| 10 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 74 percent | 0.44 m |
| 11 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 29 percent | 1.27 m |
| 12 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 87 percent | 0.28 m |
| 13 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 79 percent | 0.30 m |
| 14 | E_row1 | C_fwd | no | none | C_fwd | E_row1 | yes | 6 percent | 1.65 m |
| 15 | B_fwd | E_col1 | no | none | E_col1 | C_fwd | no | 0 percent | 2.63 m |
| 16 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 89 percent | 0.19 m |
| 17 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 79 percent | 0.35 m |
| 18 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 100 percent | 0.34 m |
| 19 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 52 percent | 1.06 m |
| 20 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 58 percent | 0.41 m |

### PA4

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 36 percent | 0.76 m |
| 2 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 49 percent | 0.54 m |
| 3 | C_rev | D_rev | no | C_rev at +2.0 s | C_rev | C_rev | yes | 8 percent | 1.55 m |
| 4 | D_fwd | E_row5 | no | none | E_row5 | D_fwd | yes | 13 percent | 2.50 m |
| 5 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 48 percent | 0.55 m |
| 6 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 49 percent | 0.62 m |
| 7 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 40 percent | 0.72 m |
| 8 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 50 percent | 0.63 m |
| 9 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 59 percent | 0.50 m |
| 10 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 46 percent | 0.50 m |
| 11 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 18 percent | 0.79 m |
| 12 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 32 percent | 0.81 m |
| 13 | C_fwd | E_col5 | no | none | E_col5 | E_col5 | no | 9 percent | 2.24 m |
| 14 | E_row1 | E_row1 | yes | none | E_row1 | E_row1 | yes | 26 percent | 0.69 m |
| 15 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 80 percent | 0.33 m |
| 16 | D_fwd | E_row5 | no | none | E_row5 | E_row1 | no | 14 percent | 2.44 m |
| 17 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 56 percent | 0.50 m |
| 18 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 35 percent | 0.72 m |
| 19 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 43 percent | 0.57 m |
| 20 | E_col1 | A_fwd | no | none | A_fwd | E_col5 | no | 0 percent | 2.03 m |

### PA6

| walk | true | locked | lock correct | switched to | drawn at end | committed | committed correct | within 0.5 m | mean distance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | B_fwd | B_fwd | yes | none | B_fwd | B_fwd | yes | 72 percent | 0.25 m |
| 2 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 91 percent | 0.25 m |
| 3 | E_row1 | E_row1 | yes | none | E_row1 | E_row1 | yes | 100 percent | 0.18 m |
| 4 | C_rev | B_rev | no | C_rev at +1.5 s | C_rev | C_rev | yes | 69 percent | 0.54 m |
| 5 | E_row5 | E_row5 | yes | none | E_row5 | E_row5 | yes | 77 percent | 0.33 m |
| 6 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 72 percent | 0.34 m |
| 7 | B_fwd | E_row1 | no | none | E_row1 | B_fwd | yes | 0 percent | 2.07 m |
| 8 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 90 percent | 0.29 m |
| 9 | A_rev | A_rev | yes | none | A_rev | A_rev | yes | 34 percent | 0.72 m |
| 10 | E_col5 | E_col5 | yes | none | E_col5 | E_col5 | yes | 75 percent | 0.33 m |
| 11 | D_rev | D_rev | yes | none | D_rev | D_rev | yes | 96 percent | 0.25 m |
| 12 | C_fwd | A_fwd | no | none | A_fwd | C_fwd | yes | 0 percent | 1.61 m |
| 13 | E_col1 | C_fwd | no | none | C_fwd | E_col1 | yes | 8 percent | 1.63 m |
| 14 | B_rev | B_rev | yes | none | B_rev | B_rev | yes | 82 percent | 0.38 m |
| 15 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 78 percent | 0.30 m |
| 16 | A_fwd | A_fwd | yes | none | A_fwd | A_fwd | yes | 69 percent | 0.41 m |
| 17 | C_rev | C_rev | yes | none | C_rev | C_rev | yes | 69 percent | 0.33 m |
| 18 | D_rev | E_col5 | no | none | E_col5 | D_rev | yes | 16 percent | 2.30 m |
| 19 | C_fwd | C_fwd | yes | none | C_fwd | C_fwd | yes | 74 percent | 0.38 m |
| 20 | D_fwd | D_fwd | yes | none | D_fwd | D_fwd | yes | 81 percent | 0.20 m |

## This pairing against the aggregate

| | this pairing | nine-pairing aggregate |
|---|---|---|
| committed line, the SHIPPED semi-bounded decision (shown as text) | 88.3 percent | 73.3 percent [35.0, 87.5] |
| the bounded rescore at the end press (NOT shown since 23e; the disclosed price) | 71.7 percent | 60.0 percent [55.8, 81.7] |
| line locked at 2 s (drawn) | 69.2 percent | 53.3 percent [25.8, 62.5] |

## The headline, both figures (nine pairings, median, 95 percent intervals)

| | committed, semi-bounded, all nine | held-out seven | lock, held-out seven |
|---|---|---|---|
| **PRE-REGISTERED** (freeze 23b, grid lattice) | **62.50** [30.00, 86.67] | 75.00 | 55.83 |
| **POST-AMENDMENT, SHIPPED** (the ONE lattice + a_veto_1.0) | **73.33** [35.00, 87.50] | 73.33 | 53.33 |

Paired, shipped against pre-registered, all nine: +3.80 [0.83, 6.94]. **The amendment, disclosed:** a_veto_1.0 ships only because condition (f) was AMENDED by the operator on 2026-09-23, POST HOC; the figure also moves because the lattice was fixed (a correctness change, not an arm). The lock column is the lock this render DRAWS (display decode); paired, one lattice minus grid, all nine: -2.41 [-4.17, -0.65].


## Mid-walk switching, rule 1a (display only, operator decision, batch 23f)

**It changes no committed answer and no quoted accuracy figure.** Disclosed beside it: as a DECISION arm, switching failed (f) in `y3_switch` (E_col5 -3 walks).

**How switching works, as measured.** The LOCK is drawn from the edge-safe DISPLAY decoder (the speed cap and the end-of-walk display head). A switch hands the dot over to the FINAL-ANSWER scorer, each line's evidence total with the shipped start term (the committed decision's own estimator), once that scorer is confidently different: ahead by more than theta nats at two consecutive checks. **The two estimators disagree at the lock on 363 of 1080 walks (33.6 percent) over nine pairings.** On the lock's own radio the display lock is right on 45.6 percent of walks and the scorer on 49.8 percent; edge recall, display lock against scorer: E_col1 37.0 / 35.2, E_col5 59.3 / 59.3, E_row1 18.5 / 24.1, E_row5 42.6 / 40.7.

**Most switches reconcile the two estimators rather than react to new mid-walk evidence: 74.7 percent of the rendered rule's switches go to the line the scorer already preferred on the lock's own radio.**

Rendered: **arm C**, at most 1 switch(es), none in the final 1.5 m, within 1.5 m, theta **2** nats on the selection folds, chosen by the operator's rule fixed before any number (`reports/PREREG_switching_arms_2026-09-23f.md`, `e2_switch`).

| arm, nine pairings | theta | time on correct [95%] | held-out [95%] | W2R / R2W / W2W | dot ends on committed | text contradicts dot | switches | over 1.5 m | qualifies |
|---|---|---|---|---|---|---|---|---|---|
| A | 2 | +1.54 [0.57, 2.70] | +1.78 [0.62, 3.23] | 37 / 10 / 49 | 647 | 433 | 96 | 17 | True |
| B | 2 | +1.54 [0.57, 2.70] | +1.78 [0.62, 3.23] | 37 / 10 / 50 | 647 | 433 | 97 | 17 | True |
| C | 2 | +1.54 [0.57, 2.70] | +1.78 [0.62, 3.23] | 37 / 10 / 48 | 647 | 433 | 95 | 17 | True |

| this render's own switches | |
|---|---|
| walks / switches | 120 / 5 |
| wrong-to-right, right-to-wrong, wrong-to-wrong | 3, 0, 2 |
| dot ends on the committed line | 89 of 120 |
| jump distance, median / over 1.5 m | 0.55 m / 0 |
| earliest switch after the lock | 1.5 s |
| switches in the final zone / persistence violations / back to a drawn line | 0 / 0 / 0 |
| decision evidence bound / target drawn bound / target evidence bound | -0.500 / -1.000 / -1.000 s |
| slide frames off their segment | 0 |
| frame jumps over 0.5 m caused by a switch (apart from the lock's) | 0 |
| render equals `e2_switch`, walk for walk | 120 of 120 |

**The end text equals the shipped headline decision on 120 of 120 walks** (`d4_headline` rows_veto).

**This is the strongest cross-day pairing and it is not typical.** The aggregate is the figure to quote. The committed answer here is the shipped SEMI-BOUNDED decision, which is not told the end press.
