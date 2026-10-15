# DC2 identification sheet, 26 and 27 September 2026. Version 2026-09-23b

Written 2026-09-23 12:10 SAST; path revised 13:00 SAST (section 1). **It supersedes the identification items of
`reports/DC2_PROTOCOL_2026-09-18.md` and all of `reports/DC2_ID_PROTOCOL_2026-09-23.md`.** Every
tracking item on the 18 September sheet and in `reports/DC2_FIELD_CHECKLIST.md`, including the
start-of-day calibration block, stands unchanged.

## 1. Decided by Uzayr

**The layout does not change.** TX at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at (-0.5, 2.5) and RX3 at
(5.5, 2.5) relative to the taped grid, with the same node heights, board orientation, twelve-line
grid, channel, packet rate and binary encoding as Room A. The layout is the same on both DC2 days
and nothing is re-mounted between them. This removes the node-placement options in section 1b of
the previous sheet.

**The identification path is E_col1, walked from (0.5, 0.0) to (0.5, 5.0)**, the same direction it
was taped and walked in Room A: 1 m in from the RX2 wall, from the TX side to the RX1 side. It is
the same line on both days.

**REVISED 2026-09-23 13:00 SAST, once, as this sheet said it would be.** Item 6's nested choice
arrived before the deadline, so the rule Uzayr set now decides it. Written at 12:10 the sheet said
E_row1, by geometry, because item 6 did not yet exist.

- **Which rule decided it: item 6's nested choice.** It is the id23 path-choice procedure, run on all
  three Room A sessions. The head is fixed in advance: 1-NN on rhythm, spectral and Doppler features.
  Every ordered session pair trains on one session and validates on another, and the best mean
  accuracy wins. E_col1 has the best, at 25.0 percent, where chance is 16.7. The runner-up lines are
  A_rev and C_rev at 23.6, and E_row1 scores 16.7
  (`runs/identify/idmax/id23_path/dc2_path_choice.json`).
- **The choice has no demonstrated validity, and Uzayr should see that before the day.** Inside the
  three cross-day folds the same procedure chose C_rev, B_fwd and E_col1, a different line each
  time. The chosen lines then scored **13.3 percent held out (n = 30)**, which is below chance.
  E_col1's six session-pair scores run from 0 to 66.7 on 6 passes each. Its geometry is among the
  worst: RX1 sits at F = 0.142 and is below F = 0.3 on 91 percent of the path. It is also the line
  the 09-19 tie-break chose, which then scored 16.7 on session 03.
- **The alternative is E_row1, by geometry.** It has the highest minimum-link mean F, 0.458. It also
  fails the F gate, as every Room A line does. Every directed line is at chance cross-day
  (FINDINGS_stageid23), so no path is supported by accuracy. **Overriding the rule to E_row1 is
  Uzayr's decision.** Nothing else on this sheet changes if he does.
- **Room A passes on the path pool with DC2.** Either edge line holds one pass per person per session
  in Room A, so 18 in all, 3 per person.

**Keypresses at the start and end marks only.** No 1 m presses and no position labels. The walk
back goes off the path, or along it without a press.

**Rounds.** 5 passes per person per round. Each round takes all six participants in an order
randomised for that round, and each round is saved as its own recording file per participant,
named `participant_<name>_idpath_d<day>_r<round>`.

**3 rounds per day, hours apart:** start of day, midday and end of day. That gives 15 passes per
person per day and 30 over DC2. Separate rounds, rather than more passes in one sitting, are what
add information at the measured within-recording ICC of 0.421, and they break the recording
confound, so cross-round evaluation within a day is valid for the first time in this project.

## 2. Also on the day

| item | specification |
|---|---|
| **Optional pace round** | One extra round on day 2 at a self-selected slower or faster pace, labelled in the file name only (`..._d2_r4_pace`). It is the only direct test of whether the classifier recognises gait rather than speed |
| **Empty-room baselines** | 2 minutes at the start and end of each day, if the room allows. They can be the same recordings as the tracking calibration block, provided the times are logged |
| **Metadata per round** | Start time, participant order, shoes and outer clothing, nothing carried in the hands |

## 3. Time this sheet needs

About 15 s per pass including the return, so 6 x 5 x 15 s = **about 8 minutes of walking per
round** and **about 25 minutes per day** for three rounds. With about 30 s per participant for
file changeover, a round takes about 11 minutes and a day about 35 minutes. Add 4 minutes for the
empty-room baselines, and about 11 minutes on day 2 if the pace round runs. **About 40 minutes on
day 1 and 50 on day 2**, spread across three sittings each. **How this merges with the tracking
protocol's time on the same days is Uzayr's decision.**

## 4. What it enables, with the interval each test can reach

Half-widths come from the existing beta-binomial power simulation (`id15_corridor._simulate`,
2000 runs) at the measured ICC of 0.421, for a six-way result at a true accuracy of 35 percent.

| analysis | test data | 95 % half-width | power vs chance |
|---|---|---|---|
| **Cross-round within a day** (valid for the first time) | leave one round out, all three rounds scored | 15.0 pts | 0.65 |
| **Cross-day**, DC2 day 1 to day 2 | day 2, 3 rounds | 15.0 pts | 0.65 |
| **Cross-room**, Room A to DC2, same path and layout | both days, 6 rounds | 10.9 pts | 0.93 |
| **Confirmatory test of the frozen configuration** | the frozen IDMAX configuration, scored once on all 30 DC2 passes per person | 10.9 pts | 0.93 |

At an ICC of 0.2, which separated rounds should approach because the ICC was measured where a whole
session was one recording, the first two rows narrow to 12.2 points.

**Frozen for the confirmatory test (added 2026-09-23 14:05).** PRIMARY, by the brief's rule: the
configuration the nested procedure chose most often across folds, a random forest on all gait
features with per-line z-scoring (`runs/IDENTIFICATION_FROZEN_2026-09-23b.json`). It was chosen in
only 2 of 9 folds. SECONDARY, labelled post hoc: the 2D CNN on Doppler spectrograms, the only
family above chance on Room A (27.2 percent cross-day; 23.9 with speed removed), with its exact
recipe in the addendum freeze. Each is scored once on DC2, with S0 on the same passes beside it.
