# DC2 identification sheet, 26 and 27 September 2026. Version 2026-09-23d

Written on 2026-09-23. **This version supersedes version c in full.** Tracking items stay in the
tracking sheets, unchanged. The analysis is pre-registered in `reports/PREREG_ID_DC2_2026-09-23.md`
and addendum B, and frozen in `runs/IDENTIFICATION_FROZEN_2026-09-23e.json`. Version c's capture
blocker is resolved: `pipeline/identify/capture_idpath.py` drives the existing walk mode, and
`pipeline/io/` is not edited.

## 1. Decided by Uzayr on 23 September

1. **Participants come one at a time**, with one slot per person per day.
2. **A dedicated identification link.** At the start of each slot, RX2 moves beside the TX, the
   identification walks are recorded, and RX2 goes home before that person's tracking.
3. **The path is line A, walked away from the TX**: `A_fwd`, (2.5, 0) to (2.5, 5), direction N,
   replacing E_row1. Run-up and run-out are not managed. The walker stops just before RX1.
4. **The operator seat is fixed at (-1.0, 0.5) for all of DC2**, identification and tracking, with
   the laptop and a powered USB-C hub. The operator keeps still while recording. **The tracking
   analysis must know this.**
5. **RX2 runs on a 4 m passive cable** from the hub at the seat.
6. **Day 2 runs in the reverse of day 1's order**, so that time of day and room conditions cannot
   line up with identity across days.

## 2. Positions

Every node stands at 1.1 m.

| node | where | facing |
|---|---|---|
| TX | (2.5, -0.5) | as Room A |
| RX1 | (2.5, 5.5) | as Room A |
| RX3 | (5.5, 2.5) | as Room A |
| RX2 at home, for tracking | (-0.5, 2.5) | east |
| **RX2 at the identification spot** | **primary (2.0, -0.5)**, or fallback (1.5, -0.5) if the cable will not reach with slack | **north, into the grid** |

- **Alignment.** Align RX2 with its tape outline and arrow at both positions, and photograph it at
  each move.
- **The identification spot** is decided at the rehearsal and recorded once
  (`capture_idpath --set-spot primary` or `fallback`). The tool refuses to change it once DC2 files
  exist.

**Projected factor F on line A**, computed by `id15_factor_map.py` (501 points):

| link | RX2 at the primary spot | RX2 at the fallback spot | RX2 at home, reference |
|---|---|---|---|
| **TX-RX2** | **0.981** (0.854 at 0 m, 0.998 at 5 m) | 0.947 (0.724 at 0 m) | 0.500 |
| TX-RX3 | 0.500 (0.180 at 0 m, 0.820 at 5 m; 24 % of the path below 0.3) | 0.500 | 0.500 |
| TX-RX1 | 0.000 along the whole path: line A is its line of sight | 0.000 | 0.000 |

For comparison, the best Room A line reached 0.46 on its weakest link. On E_row1, the moved RX2
link would drop to F = 0 mid-walk.

## 3. One slot, per person, per day, in this order

Commands are `PYTHONPATH=. python3 -m pipeline.identify.capture_idpath ...`.

1. **Move RX2 to the identification spot.** Face it north, align it, photograph it, and note the
   time.
2. **Empty room, 30 s,** with RX2 at the spot. The participant and the operator stay outside the
   grid and still:
   `--empty --position idspot --participant <code> --day <d> --move-time HH:MM`
3. **Identification walks on line A, away from the TX:**
   - **Presses at every metre, 0 m to 5 m, six per pass.** Walk mode closes a pass on its sixth
     press. The scorer uses the 0 m and 5 m presses.
   - Before each pass, stand still for 5 s at the start. Walk back around the outside of the grid,
     with no press.
   - **Day 1:** 10 natural passes, in one file: `--participant <code> --day 1 --block natural`.
   - **Day 2:** 5 natural passes (`--block natural`), then 5 slow and 5 fast, each block in its own
     file. Odd-numbered participants walk slow before fast, even-numbered fast before slow. The
     tool enforces this order.
4. **Move RX2 home** to (-0.5, 2.5), facing east. Align it, photograph it, and note the time.
5. **Empty room, 30 s,** with RX2 at home: `--empty --position home ...`
6. **Tracking**, exactly as the tracking protocol specifies.
7. **Metadata:** shoes, outer clothing, nothing carried, and both move times. Pass
   `--shoes`, `--clothing` and `--nothing-carried` on the walk commands; both move times go in as
   `--move-time` on the empty-room commands, as in steps 2 and 5.

**Order:** day 1 runs P1, P2, P3, P4, P5, P6, and day 2 runs P6, P5, P4, P3, P2, P1
(`--plan-day --day 1` and `--plan-day --day 2` print it).

**File names** are written directly, with no manifest: `participant_<name>_idpath_d<day>_<block>`,
and `..._empty_idspot` and `..._empty_home`. The folder is `data/room_B/session_0<day>/`.

**Pass counts.** A block whose count differs from the plan is refused until a reason is logged with
`--amend-count-reason`.

## 4. Time

| day | identification per person | total |
|---|---|---|
| day 1 | about 8 min | **about 48 min** |
| day 2 | about 10 min | **about 60 min** |

That covers RX2's two moves, the two empty rooms, and 10 or 15 passes. The merge with tracking time
is Uzayr's decision.

## 5. What it decides

The analyses are pre-registered in addendum B:

- **P1, the result:** cross-day, day 1 natural to day 2 natural.
- **P2:** the geometry test, TX-RX2 > TX-RX3 > TX-RX1, on single-link features at a fixed length.
- **P3:** the pace test against S0.
- **P4:** the placement control.
- **P5:** controls.
- **P6:** cross-room on TX-RX3.

**Within-day is not a result:** one slot confounds it.

With 30 test passes, P1's 95 percent half-width is about 15 points. **P2's ordering and P3's
contrast with S0 are what DC2 can decide.**
