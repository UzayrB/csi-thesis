# DC2 identification sheet, 26 and 27 September 2026. Version 2026-09-23c

Written on 2026-09-23. **This version supersedes version b in full.** Every item not changed below
carries over from b unchanged. Every tracking item on `reports/DC2_PROTOCOL_2026-09-18.md` and
`reports/DC2_FIELD_CHECKLIST.md` stands unchanged, including the start-of-day calibration block.

## 0. BLOCKER: the capture tool cannot record these rounds yet

`pipeline/io/ground_truth.py` accepts only three modes: `grid`, `walk` and `free`. It names every
capture `participant_<code>_<mode>`.

- The `walk` mode drives the fixed 20-pass, twelve-line composition with presses every metre.
- The `free` mode records no presses, and every split rejects it by name.

Neither can produce this sheet's rounds, and this workstream may not edit `pipeline/io/`.

**Uzayr decides who adds an `idpath` mode before 26 September.** The scorer
(`pipeline/identify/id28_dc2_score.py`) expects exactly the following, and will refuse anything
else:

- **Files:** `data/room_B/session_<NN>/participant_<code>_idpath_d<day>_r<round>[_slow|_fast]`,
  followed by `_RX1.bin`, `_RX2.bin`, `_RX3.bin` and `.gt.json`.
- **The `.gt.json` sidecar:** a `passes` list. Each pass carries:
  - `pass_id`
  - `t_start` and `t_end`, the two presses, on the same monotonic clock as the frames
  - `path_name: "E_row1"`
  - `direction: "E"`
- **Every recording** holds at least 3 passes.

## 1. Decided by Uzayr

**The layout does not change.** TX sits at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at (-0.5, 2.5) and
RX3 at (5.5, 2.5), relative to the taped grid. Heights, orientation, grid and radio configuration
are all as in Room A, identical on both days, with nothing re-mounted.

**The identification path is E_row1, walked from (0.0, 0.5) to (5.0, 0.5), heading E (+x).** These
are its taped Room A anchors as the grid definition reads them (`pipeline/constrained/paths.py`
`load_paths()`): five 1 m anchors along y = 0.5, walked in direction "E". The path runs along the TX
wall, 1 m in from the TX, from the RX2 side to the RX3 side, and is the same on both days.

**This is a deliberate override,** decided by Uzayr on 23 September before any DC2 data exists.

- **The rule's choice.** The rule took item 6's nested choice, which was E_col1 (version b).
- **Why E_col1 was rejected:**
  - its own held-out test scored 13.3 percent (n = 30), below chance;
  - the inner folds chose three different lines (C_rev, B_fwd and E_col1);
  - its geometry is among the worst: RX1 sits at F = 0.142, and is below F = 0.3 on 91 percent of
    the path.
- **Why E_row1:**
  - it has the highest minimum-link mean F of the twelve lines, 0.458, an argument from physics
    that is fixed before the data;
  - choosing a line by accuracy on this data has been noise three times (the id10 tie-break, the
    id23 folds, and the held-out 13.3).
- **Pooling with Room A.** Room A holds one E_row1 pass per person per session, 18 in all, and
  they pool with DC2.

**Presses at the start and end marks only.** There are no 1 m presses and no position labels. The
walk back goes off the path, or along it without a press.

**Natural rounds.** 5 passes per person per round, with the six participants in an order
randomised for each round. Each round is saved as its own file per participant:
`participant_<name>_idpath_d<day>_r<round>`. There are 3 natural rounds per day, hours apart:
start of day, midday and end of day.

**The pace test is compulsory.** It is the only direct test of gait against speed, and speed beats
every gait method on Room A (32.5 percent against a gait winner at 15.8).

- **Day 1:** a fourth round after the three natural rounds, 5 passes per person, all at a
  self-selected SLOWER pace, saved as `participant_<name>_idpath_d1_r4_slow`.
- **Day 2:** a fourth round, all at a self-selected FASTER pace, saved as
  `participant_<name>_idpath_d2_r4_fast`.
- The pace is labelled by the file name only.

## 2. Also on the day

- **Empty-room baselines:** 2 minutes at the start and end of each day, if the room allows. They
  can be the tracking calibration block's.
- **Metadata per round:** start time, participant order, shoes, outer clothing, and nothing carried
  in the hands.

## 3. Time

A pass takes about 15 s including the return, so a round is about 8 minutes of walking, or about
11 minutes with file changeovers. **Four rounds a day plus 4 minutes of baselines comes to about 50
minutes per day, over four sittings.** How that merges with the tracking protocol's time is Uzayr's
decision.

## 4. What it enables

The analyses are pre-registered in `reports/PREREG_ID_DC2_2026-09-23.md`. Half-widths assume the
measured ICC of 0.421.

| analysis | test data | 95 % half-width |
|---|---|---|
| **a. cross-round within a day**, valid for the first time | leave one natural round out, both days | about 15 pts |
| **b. cross-day within DC2** | day 1 to day 2, and the reverse | about 15 pts |
| **c. cross-room**, same path and layout | Room A to DC2 natural rounds | about 11 pts |
| **d. the pace test, gait against speed** | enrol on the day's natural rounds, test on its pace round; S0 on the same passes | read against S0's drop |
| **e. controls on DC2** | recording signature and session-ID, as in the 23b run | as a and b |

**Frozen for the confirmatory test** (`runs/IDENTIFICATION_FROZEN_2026-09-23b.json`, unchanged):

- **PRIMARY:** the rule's random forest on every gait feature, with per-path z-scoring.
- **SECONDARY:** the 2D CNN on Doppler spectrograms, labelled post hoc.
- **Speed control:** S0, speed only.

**Stated expectation.** A true accuracy near 24 percent cannot be told apart from chance in a or b.
Analyses a, d and e are the ones DC2 can decide.
