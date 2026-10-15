# Addendum C to `reports/PREREG_ID_2026-09-23.md`: the M1 nulls and the C4 evidence

**Written 2026-09-23 03:08 SAST during the tracking gate. No CSI amplitude has been read: the
counts below come from window METADATA and from file listings.** It settles open question 10.9,
which asked whether M1's two nulls exist, and it redefines M1 and part of C4 before either is
computed.

---

## 1. What was asked, and what is actually there

Open question 10.9 said: "Do static dwells and empty-room baselines exist per session? M1 needs
both nulls. If either is missing, M1 is redefined in the addendum before it is computed."

**There are no standalone static-dwell or empty-room recordings in `data/room_A/`.** Every capture
is a participant recording: `*_walk` in sessions 01 and 02, and `*_TEST_walk` plus `*_DEMO_free` in
session 03. Taken at face value that would leave M1 with no null at all.

**But the nulls are inside the walk recordings, as labelled window modes, and there are two of
them.** Window-mode counts, from metadata:

| session | walk | walk_edge | **idle** | **grid** |
|---|---|---|---|---|
| 01 | 526 | 702 | **4736** | **750** |
| 02 | 535 | 702 | **3809** | **750** |
| 03 | 541 | 695 | **3112** | **750** |

`idle` is the room between passes. `grid` is the static-position grid, a person standing still at
known cells, 750 windows in every session. Both are stationary, and together they outnumber the
walking windows by about three to one.

## 2. M1, redefined

**M1 was registered as:** the normalised autocorrelation peak in the step-period range, on walking
passes against static dwells, with **the empty room as a second null**.

**M1 is now:** the same statistic, on walking windows (`walk` and `walk_edge`) against **two
stationary nulls, `idle` and `grid`, each reported separately and never pooled.**

**This is a change of null, and on the evidence it is an improvement rather than a compromise.**

- The empty room tests whether the chain separates motion from an empty channel, which is the easy
  case and not the one that has been failing.
- `grid` is **a stationary person at a known position**. It tests whether the chain separates
  WALKING from a PRESENT BUT STILL body, which is the hard case and the one the earlier diagnostic
  actually failed: it found periodicity on 60 percent of walking pass-links **and 35 percent of
  standing ones**. That 35 percent is a `grid`-like condition, not an empty room.
- Reporting `idle` and `grid` separately also separates two different failure modes: a chain that
  fires on an empty room is broken, while a chain that fires on a standing person is merely
  undiscriminating.

**The pre-registered direction of M1 is unchanged: conditioning should WIDEN the gap between
walking and each null**, and R1 still judges a stage by whether removing it narrows that gap with
an interval that excludes zero.

**If an empty-room capture is found elsewhere** (`reports/DC2_PROTOCOL_2026-09-18.md` refers to
Room A having one), it is added as a third null and reported alongside. It is not searched for
further, because the two nulls above are sufficient and better matched to the question.

## 3. The C4 stationary-line evidence, redefined

C4 was registered to notch 50.5 Hz "plus any other stationary line found in **the empty-room
spectra**". With no empty-room capture, **the stationary-line search runs on the `idle` and `grid`
windows instead.**

This is at least as good and arguably better: a line present in the `idle` windows of the very
recording being conditioned is demonstrably present in that recording, whereas a line found in a
separate empty-room capture would have to be assumed to persist into it. Every notch is still
listed with its evidence, as registered, and the evidence is now per recording.

**The C4 prediction is unchanged and still falsifiable**: without C4, session 02 carries a
day-specific artefact and cross-day accuracy on the pairings involving session 02 falls relative to
those that do not. The archived branch records the line as appearing from 11:44 on 10 September and
absent before, which is what makes it a session-level nuisance rather than a constant.

## 4. What does not change

M2, M3, M4 and M5 are unchanged. Every other conditioning stage is unchanged. The arms, the heads,
the nine pairings, the speed policy and R1 to R7 are unchanged. This addendum touches M1's nulls
and C4's line-search corpus, and nothing else.

## 5. A note for DC2, carried into the sheet

**DC2 should record both nulls explicitly rather than relying on them appearing as labelled modes
inside a walk recording.** The v0 sheet already asks for 2 minutes of empty room at the start and
end of each session and 20 s of standing per participant per block; this addendum is the evidence
for why both items are there, and why the standing block is the more important of the two.
