# The demo re-render and the CSI check, 2026-09-24

Written 2026-09-24 18:08 SAST (clock read). Record of the operator's request of the afternoon:
- fix the renders' layout;
- make each walk's result obvious;
- explain "lag 1s" and the red dot running ahead;
- confirm the tracker reads the CSI;
- give accuracy per participant.

**Nothing in the model, the decision or the DC2 freeze changed.** The frozen videos in
`runs/constrained/demo/` and `f3_render.py` are untouched (all 159 pinned files verify). The new
videos are in `runs/constrained/demo_v2/`, from `pipeline/constrained/f4_render.py`.

## 1. Why the red dot ran ahead, and the fix

**Measured on the frozen videos** (lock-correct walks without a switch, 3424 frames): the red dot is
ahead of the green marker along the true line on 67.6 percent of frames, mean +0.175 m. It is behind in
the first quarter of the line, then ahead on about 80 percent of frames from the halfway point.

**Why.** The dot's timing rests on `HEAD_OFFSET_S`: the moment the display head is taken to name,
behind the end of its window. It was 0.75 s, measured by R1 on 2026-09-21. That was before the ONE
lattice, and the value was never re-measured. What the head actually names depends on how well it is
trained. Heads trained on two sessions, as on the demo pairing, name a later moment, so their dot
leads. Weaker heads, and the session-01 folds, lag. It also depends on pace: the display dot is capped
at 1.6 m/s, so for the fastest walker (PA6, about 1.7 m/s) it cannot lead at all.

**The fix, pre-registered** (`reports/PREREG_display_phase_2026-09-24.md`, written before any value
was swept):
- the grid is {0.75, 0.625, ..., 0};
- the value is chosen on `s0103_to_s02`, the other two-session pairing, never the demo pairing;
- the target is the operator's accepted phase of 2026-09-23 (ahead on 33.5 percent of frames).

It chose **0.375 s**. A smaller value only draws decoded positions later, so both causal bounds improve.
The sweep reproduces the frozen videos' drawn frames exactly at 0.75 (`tests/test_f4_render.py`).

| lock-correct frames, post-lock | 0.75: ahead | mean | within 0.5 m | 0.375: ahead | mean | within 0.5 m |
|---|---|---|---|---|---|---|
| **s0102_to_s03 (the demo)** | 67.6 % | +0.175 m | 61.1 % | **34.7 %** | **-0.282 m** | 58.2 % |
| s0103_to_s02 (selection) | 69.4 % | +0.190 m | 55.1 % | 39.5 % | -0.278 m | 63.1 % |
| s01_to_s02 | 56.6 % | +0.021 m | 60.7 % | 27.4 % | -0.457 m | 53.5 % |
| s01_to_s03 | 59.6 % | +0.048 m | 53.5 % | 32.2 % | -0.404 m | 51.4 % |
| s02_to_s03 | 59.1 % | +0.059 m | 57.4 % | 30.8 % | -0.405 m | 50.3 % |
| s03_to_s02 | 57.3 % | -0.049 m | 58.4 % | 28.0 % | -0.488 m | 54.7 % |
| s02_to_s01 | 39.9 % | -0.299 m | 52.0 % | 16.2 % | -0.770 m | 35.5 % |
| s03_to_s01 | 25.0 % | -0.607 m | 47.8 % | 9.0 % | -1.026 m | 25.9 % |
| s0203_to_s01 | 37.4 % | -0.345 m | 53.0 % | 14.4 % | -0.796 m | 38.0 % |

**The costs, disclosed.**
- **The right value for the demo is not right for every pairing.** On the one-session pairings and the
  session-01 folds, 0.375 makes the dot trail. No single constant fits every head. A DC2 display would
  need its own measurement, and a freeze addendum before Room B data exists.
- **On the demo videos**, pooled on-screen tracking (every walk and frame) falls from 45.3 to 39.6
  percent within 0.5 m. It improves for the slower walkers:
  - PA1 33.5 to 55.9 percent;
  - PA4 35.5 to 47.1 percent;
  - PA5 33.1 to 36.3 percent.

  It falls for the faster ones:
  - PA6 62.7 to 32.3 percent;
  - PA3 53.9 to 34.0 percent;
  - PA2 53.1 to 32.3 percent.
- **The standstill at the line entry after the commit** lengthens: at most 0.9 s, against 0.5 s. Every
  one is explained by the decoder not yet having moved, which rule 6 allows.
- **Switching reads the dot's position**, so three walks switch differently from `e2_switch`. There are
  4 switches against 5; wrong-to-right is 2 against 3, and right-to-wrong is 0 in both.
- **Centred instead of slightly behind:** 0.5 on the demo gives 44.3 percent ahead, -0.128 m, and 61.6
  percent within 0.5 m. Choosing it now would be POST HOC, because these numbers have been seen.

**"lag 1s"** was `LAG = WINDOW_S / 2`, the window-centre offset. It was never a delay the viewer sees.
The display runs 2.0 s behind real time (V1), and that is now the only delay on screen.

## 2. The picture

- **The room:** it fills the frame. The legend and the clock sit in a band above it, clear of RX1,
  which stays at its measured position.
- **The result:** at each walk's end the bottom says CORRECT in green or WRONG in red for the shipped
  committed decision, with the walk number. It gives this participant's running accuracy and the total
  over all six (106 of 120, from `d4_headline`), and states that the demo pairing is the easiest of nine
  (median 73.3 percent). It stays up until the next walk commits: at least 4 s, typically 12 s.
- **Rule checks:** V1 to V3 and rule 6 hold, the one rule has 0 violations, no frame lacks a dot, and
  the end text equals the headline decision on 120 of 120 walks. Both causal bounds are -1.375 s, now
  computed on the step actually drawn.

## 3. Is it reading the CSI? The donor swap

Pre-registered in `reports/PREREG_donor_swap_2026-09-24.md`; code `pipeline/constrained/f5_donor.py`;
results in `runs/constrained/fh/f5_donor/`.

**The method.** For every walk on the nine pairings, the shipped committed decision is taken on the
walk's own radio. That run equals `d4_headline` on **1080 of 1080** walks. The decision is then taken
again on a DONOR's radio: another participant's walk on a different line. The swap replaces the pool
emissions, the gate energy and the pre-press start term. Only the press time stays the walker's own.

| | own-radio accuracy | follows the DONOR's line | stays on the walker's own line | chance |
|---|---|---|---|---|
| pooled, 1080 walks | 63.3 % | **61.1 %** | **3.4 %** | 8.3 % |
| s0102_to_s03 (demo) | 88.3 % | 90.8 % | 1.7 % | |
| session-01 folds | 32.5 to 35.0 % | 20.0 to 30.0 % | 5.0 to 9.2 % | |

**The answer follows the radio.** How often it follows the donor tracks own-radio accuracy pairing by
pairing. How often it stays on the walker's real line is at or below chance on every pairing: when the
radio is someone else's, the walker's own line is not recovered from timing or a motion prior.

**Caveats:**
- 51 donor walks were truncated to fit before the next walk.
- 56 exits ran past the donor segment into the walker's own radio after the walk.

**The along-line position is a different matter, and the answer there is "about half".** The display
path is a Viterbi restricted to the committed line, with a motion prior (flattened 0.5) and a speed
cap. In `r3_prior`, another participant's CSI moved the drawn along-line position on 43 percent of the
steps where it could have, against a ceiling of 84 percent: a ratio of 0.52. **The LINE is read from
the radio. Progress ALONG the line is about half radio and half motion model.**

## 4. Accuracy per participant

The shipped committed decision (A2 + `a_veto_1.0`) and the 2 s lock the render draws, over the nine
cross-day pairings (`d4_headline` rows_veto, `d6_lock_commit` rows). There is one value per pairing
per participant, about 20 walks each. The bracketed interval is a bootstrap of the median over nine
values, so it is wide. Chance is 8.3 percent.

| participant | committed, median of 9 [95 %] | held-out 7 | session-01 folds | 2 s lock, median of 9 | demo pairing, committed (lock) | edges right, E_col1 / E_col5 / E_row1 / E_row5 | substitution changes the line |
|---|---|---|---|---|---|---|---|
| PA5 | 60.0 [25.0, 85.0] | 75.0 | 30 / 25 / 25 | 45.0 | 15/20 (10/20) | 5/9, 6/9, 5/9, 6/9 | 66.7 % |
| PA1 | 70.0 [20.0, 85.0] | 70.0 | 20 / 20 / 20 | 50.0 | 19/20 (15/20) | 3/9, 6/9, 7/9, 6/9 | 66.7 % |
| PA2 | 70.0 [20.0, 90.0] | 70.0 | 20 / 20 / 20 | 45.0 | 17/20 (13/20) | 3/9, 6/9, 8/9, 2/9 | 74.4 % |
| PA3 | 80.0 [70.0, 90.0] | 85.0 | 75 / 70 / 75 | 45.0 | 18/20 (15/20) | 8/9, 8/9, 9/9, 8/9 | 75.6 % |
| PA4 | 70.0 [45.0, 100.0] | 80.0 | 30 / 45 / 30 | 50.0 | 17/20 (15/20) | 2/9, 9/9, 9/9, 6/9 | 78.9 % |
| PA6 | 55.0 [30.0, 90.0] | 55.0 | 30 / 30 / 25 | 35.0 | 20/20 (15/20) | 4/9, 7/9, 7/9, 4/9 | 74.4 % |

The session-01 folds are `s02_to_s01`, `s03_to_s01` and `s0203_to_s01`. Session 01 is where every
participant but PA3 falls to 20 to 45 percent. That is the known session-01 shift, not a
per-person effect. E_col1 is the weakest edge line for four of the six.

**Donor swap per participant** (pooled over the nine pairings):

| participant | own-radio | follows donor | stays on own |
|---|---|---|---|
| PA5 | 57.8 % | 54.4 % | 3.9 % |
| PA1 | 57.8 % | 54.4 % | 6.1 % |
| PA2 | 59.4 % | 82.8 % | 0.0 % |
| PA3 | 79.4 % | 66.1 % | 2.8 % |
| PA4 | 67.2 % | 54.4 % | 4.4 % |
| PA6 | 58.3 % | 54.4 % | 3.3 % |
