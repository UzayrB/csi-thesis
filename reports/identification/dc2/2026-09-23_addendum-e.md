# Pre-registration addendum E: DC2 identification, both days as recorded, and one press relabel

**Drafted on 2026-09-26 from 23:22 SAST and finalised on 2026-09-28 from 08:45 SAST, both read from the
clock; approved by Uzayr on 2026-09-28.** Both days of DC2 identification data exist
(`data/room_B/identification/session_01/` and `session_02/`, 30 recordings each), so everything here
is POST HOC in the sense of the tracking relabel addendum (`PREREG_DC2_ADDENDUM_2026-09-28_relabel.md`):
it was written after the data existed and **before any identification figure was computed**. At 08:45
on 2026-09-28 `runs/identify/dc2/` held only `rx2_spot.json` and the relabel manifest of section 6, and
no view existed under `runs/identify/`.

**What this addendum does.** It records how both days departed from the protocol, fixes how each
departure is treated, and registers one pre-scoring data correction, a press relabel applied as
metadata. It changes no analysis, configuration, statistic, verdict rule or scorer. The
pre-registration, addenda B, C and D, and the addenda of 24 and 25 September are unchanged.

Participants are named by P code only: "participant P2" is a person, "analysis P1" is a row. In the
tables, the participant column holds P codes.

## 1. What was read to write this

- The sidecars of both days (`.idmax.json`, `_run.json`), including those in `data/room_B/aborted/`,
  for times, placements and counts; and the press times in the `.gt.json` files.
- For each recording and each link: the mean amplitude per subcarrier over the 103 kept subcarriers,
  the mean RSSI, the frame count and the receiver clock, read through the frozen clock map
  (`id29_dc2_score._link`). Each walk block was compared only with the same participant's own empty
  rooms of the same day, by the correlation of the mean amplitude profiles across subcarriers (r
  below). RX1 and RX3, which never move, are the control.

No feature, classifier, accuracy or analysis P4 quantity was computed. The participants' levels appear
side by side in the check's output; they were used only to see that the recordings flagged in sections
4 and 5 stand apart, and to state the day-level shift in section 5, never to compare placements
between people.

## 2. Both days as recorded

Times are block starts, SAST, from the sidecars.

| participant | day | empty at spot | natural | slow | fast | empty at home | tracking | order |
|---|---|---|---|---|---|---|---|---|
| P3 | 1 | 11:15 | 11:17 | 11:21 | 11:22 | 11:01 | 11:04 | identification after tracking; home room before it |
| P2 | 1 | 12:20 | 12:00 | 12:16 | 12:04 | 12:07 | 12:09 | slow block and spot room after tracking |
| P4 | 1 | 12:22 | 12:29 | 12:34 | 12:32 | 12:38 | 12:41 | as planned |
| P1 | 1 | 12:51 | 12:54 | 12:58 | 13:00 | 13:05 | 13:08 | as planned |
| P5 | 1 | 13:31 | 13:34 | 13:38 | 13:41 | 13:44 | 13:46 | as planned |
| P6 | 1 | 13:58 | 14:00 | 14:06 | 14:05 | 14:11 | 14:14 | as planned |
| P6 | 2 | 08:34 | 08:35 | 08:39 | 08:37 | 08:42 | 08:45 | as planned |
| P3 | 2 | 11:30 | 11:32 | 11:33 | 11:35 | 11:38 | 11:41 | as planned |
| P4 | 2 | 11:58 | 12:00 | 12:04 | 12:02 | 12:07 | 12:10 | as planned |
| P5 | 2 | 13:39 | 13:41 | 13:44 | 13:46 | 13:49 | 13:52 | as planned |
| P1 | 2 | 14:03 | 14:04 | 14:06 | 14:08 | 14:11 | 14:13 | as planned |
| P2 | 2 | 14:52 | 14:53 | 14:57 | 14:55 | 15:00 | 15:02 | as planned |

On both days and for every participant the block order held: natural first, then slow before fast
for participants P1, P3 and P5 and fast before slow for participants P2, P4 and P6. Every walk block is
COMPLETE against its plan in both directions, and the day check (`--final`) reports NOTHING WRONG for
both days (`runs/dc2_results/logs/item0_daycheck_day1.log` and `..._day2.log`). The calibration walk
was walked by participant P3 on day 1 (10:43) and participant P6 on day 2 (08:27).

**Time of day, for every cross-day figure** (the schedule addendum of 2026-09-25 requires it). The
natural block started later on day 2 than on day 1 by: participant P1 1 h 10 min, participant P2
2 h 53 min, participant P3 0 h 15 min, participant P5 0 h 07 min; and earlier by: participant P4
0 h 29 min, participant P6 5 h 25 min. **Participants P3 and P5 were recorded at about the same time of
day on both days**, which the schedule addendum stated as a preference to avoid.

## 3. Departures recorded at capture

**Day 1.**

1. **Participant P3.** A 10:53 start was aborted with no walks, and a 10:56 natural block was walked at
   mixed paces, because the plan was read as walks rather than cycles. Both were later overwritten by a
   move into the same folder and no longer exist; their description comes from the day 1 handoff. Kept
   in `aborted/`: participant P3's original empty room at the spot (10:49) and a one-cycle natural
   attempt (11:16, reason "problem"). The final set was recorded from 11:15 to 11:23, after participant
   P3's tracking (11:04), with RX2 moved back to the spot; the home room (11:01) is from before
   tracking. The final spot room's move time is stored as the literal text "HH:MM"; the move was after
   11:04:17 and before 11:15:46. `move_time` is never read by the view or the scorers.
2. **Participant P2.** The first set (11:41 to 11:53) had RX2 silent (header-only files) and is in
   `aborted/`. It was redone: natural 12:00, fast 12:04, home room 12:07, tracking 12:09, slow 12:16,
   spot room 12:20. The slow block was walked after tracking.
3. **Participant P4.** The first natural block (12:24, 9 cycles, reason "Messed it up") is in
   `aborted/` and was redone at 12:29.
4. **Participant P1.** The first spot room (12:48) and first home room (13:02) had RX2 silent. Both are
   in `aborted/` and were redone (12:51, 13:05).
5. **Participant P6.** The first home room (14:08) was recorded with RX2 still at the spot. It is in
   `aborted/` and was redone (14:11).
6. **RX2** went silent after being moved, three times on day 1.

**Day 2.**

7. **Two spot rooms were redone because RX2 had not yet been moved to the spot:** participant P3's
   (11:28, redone at 11:30) and participant P1's (14:00, redone at 14:03). The first recordings are in
   `aborted/`.
8. **Participant P5's fast block** holds a double press; section 6 relabels it.

## 4. What the signal shows about RX2 on day 1

- **a. Participant P2's slow block (12:16) was walked with RX2 at the spot.** RX2 in it matches
  participant P2's spot room of 12:20 (r 0.996; RSSI -65.6 against -65.5 dBm), not the home room
  (r 0.58; -79.9 dBm).
- **b. Participant P2's natural block (12:00 to 12:04): RX2 in a different state.** RX2 reads about
  8 dB low for the whole block, -73.5 dBm against -65.2 in the fast block that began 32 s after it
  ended, with no step inside the block. Its profile matches neither room well (r 0.84 with the spot
  room, 0.91 with the home room). RX1 and RX3 are unchanged. The operator reports that RX2 was only
  unplugged and plugged back in after the silent first set, and nothing else was changed. The cause is
  unknown.
- **c. Participant P3's final set: RX2 not in one state throughout.**

  | participant P3 | at | RX2 RSSI (dBm) | r with the 10:49 spot room | r with the 11:15 spot room |
  |---|---|---|---|---|
  | spot room, original (aborted) | 10:49 | -65.0 | 1 | 0.59 |
  | spot room, final | 11:15 | -79.6 | 0.59 | 1 |
  | natural | 11:17 | -78.5 | 0.77 | 0.87 |
  | slow | 11:21 | -75.0 | 0.90 | 0.50 |
  | fast | 11:22 | -74.6 | 0.91 | 0.52 |

  The final spot room and the natural block share one state, and the slow and fast blocks sit closer
  to the original spot room, so the final spot room does not represent RX2 during participant P3's
  slow and fast blocks. The cause is unknown.
- **d. Participant P3's home room (11:01) reads close to the spot.** It is -68.6 dBm, 3.6 dB from
  participant P3's original spot room, with r 0.90; for the other five participants the home room
  reads 6.8 to 21 dB below their spot room. The operator reports that RX2 was at home for it. It feeds
  only analysis P4's home row, which is information for tracking.
- **e. Participant P1's natural block: RX2 rebooted at the start.** Its clock restarts 0.31 s into the
  file. The frozen clock map mis-times only the one frame before the reboot and places it outside every
  pass. No other day 1 file has a clock step. No effect on any analysis.
- **f. Participants P2's and P4's spot rooms were recorded two minutes apart** (12:20 and 12:22), with
  no home placement between them. Participant P4's sidecar logs a move at 12:22; whether RX2 was lifted
  and replaced is not recorded.
- **g. Everything else on day 1 is consistent.** Each other walk block matches its participant's own
  spot room (r 0.88 to 0.998) and reads within 2.4 dB of it. RX1 and RX3 are steady throughout.

## 5. What the signal shows on day 2 (levels only, not analysed)

- **Within each participant, day 2 is consistent.** Every walk block matches its participant's own
  day 2 spot room (r 0.92 to 0.999), and none shows the low state of 4b or 4c. Every block reads within
  3.3 dB of its spot room except participant P6's slow block, 5.5 dB below it, in which RX1 also shifts
  (r 0.91 with its spot room).
- **Between the days, the levels shifted.** RX3 reads about 4 dB lower on day 2 for all six
  participants (about -70 to -72 dBm on day 1, about -74 to -77 on day 2). RX2 at the spot reads 3.6 to
  11.8 dB lower on day 2 for five participants; participant P3's day 2 spot room is 1.0 dB above
  participant P3's day 1 final spot room, which was in the low state of 4c. RX1 is unchanged. The cause
  is not established, and the shift is not analysed or corrected for.
- **Participant P2's day 2 home room: RX1 rebooted at the start.** Its clock restarts 0.11 s into the
  file. The frozen clock map mis-times only the four frames before the reboot and places them about
  4118 s before the recording, outside the span the empty-room windows are cut from. It is the only
  day 2 file with a clock step, and it feeds only analysis P4's home row. No effect.

## 6. The press relabel: a pre-scoring data correction

**The error.** In participant P5's day 2 fast block, the operator pressed twice at one mark, 0.166 s
apart, during `A_fwd` pass 9. The capture closes a pass on its sixth press, so pass 9 closed on its
real 4 m press, 2.86 s after its start (1.75 m/s against the participant's other fast `A_fwd` passes of
3.57 to 4.04 s). Its real 5 m press became the first press of pass 10 (`A_rev`), and the block stopped
at its planned 60 presses, so pass 10's real 0 m press was never recorded. The capture tool flagged
both passes, and the day check passes them. Pass 9's 2.86 s lies inside the scorers' 1.5 to 12 s gate,
so no scorer would have refused it.

**The rule, frozen with this addendum and applied to every identification walk block of both days:**

> Where two consecutive presses in a walk block are 0.3 s apart or less, the later is an extra press
> and is removed, and the block's presses from that pass on are regrouped in sixes, in order. A pass
> left with fewer than six presses is excluded.

Uzayr's brief of 2026-09-28 first worded it as "Where a pass's closing press is followed within 0.3 s
by a further press, the pass closes on the later press, which is the true mark. A pass left without its
opening press is excluded." Applied to the data, that wording touched no pass, because the double press
lies inside pass 9 and not after its closing press. The wording above was approved by Uzayr on
2026-09-28, before it was applied, as the statement of the same intent; its outcome is the one the
brief stated in advance.

**What it touched: 36 blocks scanned, one pass relabelled, one excluded.**

| participant P5, day 2 fast | before | after |
|---|---|---|
| pass 9, `A_fwd` | 2.86 s, 1.75 m/s, closing on the 4 m press | 3.70 s, 1.35 m/s, closing on the real 5 m press; start unchanged |
| pass 10, `A_rev` | six presses, the first being pass 9's 5 m press | five presses; excluded |

No other pair of presses on either day lies within 0.3 s. Which of the two close presses is removed
moves only pass 9's 2 m mark, which no identification row reads: every row uses the first and last
presses.

**As metadata, never in the capture.** The manifest `runs/identify/dc2/relabel_manifest.json` records
the rule, every change, and the SHA-256 of the capture file before it. `pipeline/identify/idrelabel.py`
builds a relabelled source under `runs/identify/dc2_src_relabelled/`, in which every file links to the
capture except the one rewritten `.gt.json`; it refuses if that file has changed since the manifest was
written. The frozen view reads it (`idboth_view --src runs/identify/dc2_src_relabelled/identification`),
as does the secondary view. `data/` is never written.

**What it reaches.** Pass 9 is scored in analysis P3 (day 2 fast), in P1-GP's fast block and in
analysis P7 (fast). Pass 10 is `A_rev` in a pace block and reaches no registered row.

## 7. Treatment, fixed now

1. **Every recording in `session_01` and `session_02` is scored as recorded, and every pass in it is
   used, except as section 6 relabels.** None is excluded for anything in sections 3 to 5. A pass is
   excluded only if aborted at capture time (addendum 2026-09-24, section 4) or by the rule of section
   6. The files in `aborted/` are never read by the views or the scorers.
2. **Disclosure.**
   - Beside analyses P1, P1-GP, P2, P3 and P5: the day 1 natural blocks of participants P2 and P3,
     which are training data for those rows, were recorded with RX2 in a state unlike their other
     blocks (4b, 4c), and the levels shifted between the days (section 5).
   - Beside analysis P4: 4c, 4d, 4f and section 5.
   - Beside analysis P7: participant P2's and participant P3's day 1 pace blocks were walked after
     their tracking, with RX2 at the spot for participant P2's slow block (4a) and in the state of 4c
     for participant P3's; and the relabel of section 6 touches the fast row.
   - Beside analysis P3 and P1-GP's pace blocks: the relabel of section 6.
   - Beside every cross-day figure: the block times and time-of-day note of section 2, and that
     participant P3's day 1 identification followed participant P3's tracking, so participant P3's two
     days are not matched for warm-up.
3. **No sensitivity row is registered** (Uzayr's decision, 2026-09-26). Sections 4b and 4c are
   disclosed and not analysed separately; any figure that leaves out participants P2 or P3 is
   exploratory.

## 8. Stated expectation, so it cannot be reinterpreted later

Sections 4b and 4c touch the TX-RX2 link of two participants' training passes. If they matter, the
most plausible effect is lower cross-day accuracy for those two participants in the rows that read
TX-RX2, and a larger TX-RX2 difference between days in analysis P5's session-ID control. The day-level
shift of section 5 works in the same direction for every cross-day row. No correction is made for
either.

## 9. The freeze

This file is hashed in `runs/IDENTIFICATION_FROZEN_2026-09-28.json`, which references
`runs/IDENTIFICATION_FROZEN_2026-09-25.json` and supersedes nothing, together with the relabel manifest,
`pipeline/identify/idrelabel.py`, the P1-REV and P7 scorer and view
(`pipeline/identify/idsec_dc2_score.py`, `pipeline/identify/idsec_view.py`) and their tests, before any
identification figure is computed. `tests/test_freeze_2026_09_28.py` re-hashes them.
