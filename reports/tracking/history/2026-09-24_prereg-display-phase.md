# PRE-REGISTRATION: the demonstration's display phase, 2026-09-24

Written 2026-09-24 17:35 SAST (clock read), before any sweep value below exists. **Display only**: it
changes no committed answer, no lock, no switch rule and no quoted accuracy figure. The frozen renderer
`pipeline/constrained/f3_render.py`, its six hashed videos and the DC2 freeze are untouched; the change
lives in a new renderer, `pipeline/constrained/f4_render.py`, writing to `runs/constrained/demo_v2/`.

## Why

The operator reported that the red dot runs ahead of the green marker most of the time. Measured on the
frames the shipped videos draw (`runs/constrained/fh/f3_render/results.json`, lock-correct walks with no
switch, 3424 frames over 83 walks): the dot is ahead along the true line on **67.6 percent** of frames,
median **+0.22 m**; behind in the first quarter of the line (median -0.30 m), ahead on about 80 percent of
frames from the halfway point on.

The drawn dot's timing rests on `HEAD_OFFSET_S = 0.75`: the moment the display head is taken to name,
behind the end of the window it is read from. R1 measured it on 2026-09-21, on the grid lattice and the
heads of that date. The operator's phase decision of 2026-09-23 (`w1_dotphase`, shift 0.50) was also
measured on the grid lattice. Neither was re-measured after the ONE lattice (2026-09-23d).

**Disclosed, seen before this was written:** `y4_pressalign`'s per-walk signed offsets at the shipped
setting, per pairing. The pairings trained on two sessions lead (`s0102_to_s03` median +0.198 m,
`s0103_to_s02` +0.243 m); the session-01 folds lag (-0.24 to -0.46 m). No value at any other offset has
been computed.

## What varies

`HEAD_OFFSET_S` in {0.75 (current), 0.625, 0.50, 0.375, 0.25, 0.125, 0.00}. Nothing else: `SHIFT_W` stays
0.50, and the decode, the lock, the switching rule and its theta, and V1 to V4 are unchanged. A smaller
value draws every decoded position LATER, never earlier, so neither causal bound can get worse. The
anchor segment (rule 2's exception) runs from the commit to the first decoded frame and gets longer as
the value falls.

## Selection pairing

**`s0103_to_s02` only.** It is trained on two sessions, as the demo pairing is; its test session is not
01, whose shift dominates the lag on those folds; and it is not the pairing the videos show. The demo
pairing `s0102_to_s03` is never used to choose.

## Target and rule

Target: the operator's accepted phase of 2026-09-23, `w1_dotphase` at 0.50 (nine pairings, grid
lattice): the dot ahead on **33.5 percent** of correct-line frames, mean -0.281 m. Slightly behind.

Rule: on `s0103_to_s02`, over lock-correct walks, on the frames from the first decoded frame to the end
press (`w1`'s definition), pick the value whose share of frames with the red dot ahead along the true
line is closest to 33.5 percent. Ties within 1.0 point go to the larger value (the smaller change).

## Reported, at the chosen value and at 0.75

On the demo pairing and on all nine pairings, session-01 folds shown:
- the share of frames ahead, and the signed mean and median;
- within 0.5 m on correct-line frames;
- the same over every frame from the commit, the anchor segment included;
- both causal bounds.

The demo pairing's on-screen tracking figure is not selected on, and is reported beside the old one.

## Not a model change, and not DC2

`reports/MODEL_FREEZE_DC2.md` lists the display path with "phase 0.50 strides". This changes
`HEAD_OFFSET_S` in the new renderer only. Adopting it for any DC2 display would need a freeze addendum
before Room B data exists.
