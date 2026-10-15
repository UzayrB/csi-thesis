# DC2 capture summary: Room B tracking data, as captured

Written 2026-09-28 08:05 SAST (clock read), before any model had run on Room B. Every figure comes
from read-only checks of the capture files that morning: both days' final day checks, the run
records, the ground-truth sidecars and the baselines. No radio was decoded. Tracking only.

## The two days

| | Day 1 (B1, 26 Sept) | Day 2 (B2, 27 Sept) |
|---|---|---|
| calibration walk, never scored or trained on | `participant_PA2_C_walk`, 10:43, 11 passes | `participant_PA6_C_walk`, 08:27, 8 passes |
| tracking | 6 × 20 = 120 passes | 6 × 20 = 120 passes |
| order and start times | PA2 11:04, PA1 12:09, PA3 12:41, PA5 13:08, PA4 13:46, PA6 14:14 | PA6 08:45, PA2 11:41, PA3 12:10, PA4 13:52, PA5 14:13, PA1 15:02 |
| lines | 12 passes on each of the 8 two-way lines, 6 on each of the 4 edge lines | the same |
| aborted passes | none | none |
| flagged passes | 0 after the relabel (11, all PA5's, before it) | 0 |
| median pace, pass length over first-to-last press | 1.26 m/s | 1.25 m/s |
| worst link loss on a walk | 1.87 % (RX2, PA4) | 1.31 % (RX2, PA4) |

The line mix is Room A's: the edge lines are walked half as often, which is what the decoder's
per-line prior assumes.

## Receivers, baselines, idle radio

- **Receivers:** RX1, RX2 and RX3 in every recording, matched by MAC; 147 to 150 packets per second;
  every stream gate passed; no header-only (dead link) file in either tracking session; no RX4.
- **Baselines:** 13 of 60 s, all passing. Every tracking walk has its own, taken 1 to 2 minutes
  before it, except PA1 on day 1 (below). The weakest is PA3's day 1 baseline: RX2 lost 3.5 %,
  inside the 5 % gate.
- **Idle radio before each walk's first press:** 14 to 38 s per recording.

## Pace against Room A

Median pace by the same measure: Room A sessions 1.30, 1.28 and 1.29 m/s; Room B 1.26 and 1.25 m/s.
The frozen motion model assumes 1.298 m/s. Description only; nothing was changed because of it.

| m/s | PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |
|---|---|---|---|---|---|---|
| Day 1 | 1.25 | 1.17 | 1.34 | 1.36 | 1.07 | 1.32 |
| Day 2 | 1.25 | 1.13 | 1.32 | 1.36 | 1.20 | 1.27 |

## Issues, and how each is resolved

1. **PA5, day 1, passes 10 to 20:** one extra space press at the end of pass 9 shifted every later
   pass by one mark. Relabelled POST HOC on 2026-09-28; the original is kept.
   `PREREG_DC2_ADDENDUM_2026-09-28_relabel.md` section 1.
2. **PA1, day 1:** his tracking uses PA2's 11:02 baseline, 66 minutes old, because his own lost
   RX2. Accepted as recorded and disclosed. Same addendum, section 2.
3. **Reaction time was not re-measured on day 2.** Every walk recording on both days carries the
   26 Sept 10:22 value, 0.041 s. `DC2_POSTHOC_TOOLING_NOTE_2026-09-28.md`.
4. **The pinned day check's cross-day false alarm.** Corrected beside it, in the same note.

## Where the data is

- Tracking: `data/room_B/session_B1` and `session_B2`.
- The manifest: `data/room_B/calibration.json`, naming the two calibration walks, no aborted passes.
- Set aside, never read by tracking: `data/room_B/aborted/`, and identification in
  `data/room_B/identification/`.
