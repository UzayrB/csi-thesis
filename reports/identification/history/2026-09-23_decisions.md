# Identification decisions, 2026-09-23

One entry per decision: the decision, then a one-line reason. Ready for the Notion Decisions Log.

1. **2026-09-23: The DC2 identification path is E_row1, walked from (0.0, 0.5) to (5.0, 0.5) heading
   E, chosen by geometry and overriding the item-6 rule.**
   Reason: the rule's choice (E_col1) scored 13.3 percent on its own held-out test and has the worst
   geometry, while E_row1 has the highest minimum-link F (0.458), a physics argument fixed before
   the data.

2. **2026-09-23: The DC2 pace rounds are compulsory: one extra round on day 1 at a self-selected
   slower pace and one on day 2 at a self-selected faster pace, 5 passes per person each.**
   Reason: speed alone (32.5 percent) beats every gait method on Room A, and a pace change is the
   only direct test of whether a classifier reads gait or speed.

3. **2026-09-23: Identification on Room A is closed. The only remaining identification analysis
   is the pre-registered DC2 scoring in `reports/PREREG_ID_DC2_2026-09-23.md`.**
   Reason: 174 configurations, 18 heads, 4 learned models, voting and alignment all left Room A
   cross-day identification at chance, while the pipeline passes its positive controls, so more
   Room A analysis can only add selection noise.

4. **2026-09-23: The DC2 PRIMARY and SECONDARY configurations are those frozen in
   `runs/IDENTIFICATION_FROZEN_2026-09-23b.json` and its addendum, unchanged.**
   Reason: a confirmatory test is only confirmatory if nothing is tuned after the pre-registration,
   and both were fixed before any DC2 data existed.

**Open item, and not a decision:** the capture tool (`pipeline/io/ground_truth.py`) has no `idpath`
mode. One must be added before 26 September, outside this workstream, or the DC2 identification
rounds cannot be recorded as specified. **RESOLVED on the evening of 2026-09-23:**
`pipeline/identify/capture_idpath.py` drives the existing walk mode on one line, and `pipeline/io/`
is not edited (`reports/CAPTURE_INTERFACE_NOTES.md`).

## Added 2026-09-23 evening: the per-person slot design (version d, addendum B)

5. **2026-09-23: Participants come one at a time, one slot per person per day. RX2 is moved beside
   the TX (identification spot, facing north) for that person's identification walks, then
   returned home (-0.5, 2.5, facing east) before their tracking.**
   Reason: moving RX2 behind the walker gives a link with both ends behind them, F = 0.98 on
   line A, which Room A's ring layout never had, while tracking keeps its layout.

6. **2026-09-23: The identification path changes from E_row1 to line A walked away from the TX
   (`A_fwd`).**
   Reason: with RX2 moved, line A gives that link a mean F of 0.981 (0.854 at the 0 m mark)
   against 0.46 for the best Room A line, whereas E_row1 would put the moved link's dead spot
   mid-walk (minimum F 0.0).

7. **2026-09-23: The operator seat is fixed at (-1.0, 0.5) for all of DC2, identification and
   tracking.**
   Reason: a moving operator is a moving reflector, and a fixed seat keeps the static channel,
   and the 4 m RX2 cable run, identical in every slot.

8. **2026-09-23: Day 2 runs in the reverse of day 1's participant order.**
   Reason: so that time of day and room conditions, such as Room A's aircon line, cannot line up
   with identity across days.

9. **2026-09-23: Within-day identification is demoted to a labelled, confounded figure. Cross-day
   P1 (day 1 natural to day 2 natural) is the result.**
   Reason: each person's identification passes come from one slot with one RX2 placement, so a
   within-day figure cannot separate the person from the slot.

10. **2026-09-23, 19:31 SAST: Room A is reopened for one labelled EXPLORATORY run, integrated gait
    analysis with pace as one gait parameter (IDGP, brief 2026-09-23f), by Uzayr's decision.**
    Reason: to test whether spatio-temporal gait parameters, of which pace is one, beat speed alone;
    every result from it is EXPLORATORY until DC2 confirms it.

11. **2026-09-23, 19:47 SAST: Room A is reopened for this labelled exploratory run, IDGP under the
    identification contract (the revised brief 2026-09-23f), by Uzayr's decision on 23 September.
    Every result from it is EXPLORATORY until DC2 confirms it.** It supersedes decision 10, whose run
    was cancelled at 19:38 before any compute.
    Reason: the revised brief binds every arm to the DC2 inputs (the CSI between the walk's start and
    end, those two times, and the path's identity and length), so Room A can choose the DC2 pipeline
    without any input DC2 will not have.
