# Pre-registration addendum 2026-09-25: identification first, then tracking

**Written on 2026-09-25 from 08:53 SAST, read from the clock. No Room B data existed: `data/room_B` did
not exist, checked at 08:52:56.** The order is Uzayr's decision of 2026-09-25. It amends
`PREREG_DC2_ADDENDUM_2026-09-24.md` (section 1, the "blocks" and "RX2 within a block" rows, and a note in
section 3), which is pinned and not edited; where the two disagree, this file governs. **It changes no
analysis, no model, no constant and no code.** Tracking (`pipeline.io.ground_truth`) and identification
(`pipeline.identify.capture_idboth`) are separate tools that write to separate folders, and neither of them,
nor the day check, enforces an order between them.

## The block per person, each day

1. RX2 to its identification spot, (2.0, -0.5), facing north; photographed, time noted.
2. 30 s empty room at the spot.
3. The identification walks: natural first, then the participant's pace order.
4. RX2 home, (-0.5, 2.5), facing east; photographed, time noted.
5. 30 s empty room at home.
6. 60 s baseline (addendum 24b).
7. Tracking: 20 passes.
8. The day check.

The start of each day is unchanged: the calibration walk, with its baseline, runs with RX2 at home before
the first block.

## What the order does

- **It is the order sheet 23d pre-registered:** identification, RX2 home, the home empty room, then
  tracking. The only addition is 24b's 60 s baseline before tracking.
- **P4's home control keeps its meaning.** The home empty room still comes straight before that person's
  tracking, in the placement they track in, as under 23d.
- **Withdrawn from addendum 24, section 3:** "Identification now follows about 7 minutes of tracking
  walks". Identification now comes first, as 23d had it. Tracking now follows the identification walks:
  20 cycles on day 1 and 15 on day 2, so its warm-up is slightly longer on day 1. The note is disclosed
  here and is not corrected for.
- **Everything else in addenda 24 and 24b stands:** both directions on line A, the day 1 pace blocks, the
  view the frozen scorers read, the secondary rows P1-REV and P7, the baselines, the calibration recording
  named `<first participant>_C`, and the two read-only checks.

## The freeze

This file is hashed in `runs/TRACKING_FROZEN_2026-09-25.json` (which references
`TRACKING_FROZEN_2026-09-24b.json`) and in `runs/IDENTIFICATION_FROZEN_2026-09-25.json` (which references
`IDENTIFICATION_FROZEN_2026-09-24.json`). Both are re-hashed by `tests/test_freeze_2026_09_24.py`.
