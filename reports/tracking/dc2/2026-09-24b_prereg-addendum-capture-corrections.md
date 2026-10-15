# Pre-registration addendum 2026-09-24b: three capture corrections, found by running the day on the hardware

**Written on 2026-09-24 from 20:25 SAST, read from the clock. No Room B data existed: `data/room_B` did
not exist, checked at 20:24:59.** It corrects `PREREG_DC2_ADDENDUM_2026-09-24.md`, which is pinned and not
edited; where the two disagree, this file governs. **It changes no analysis, no model and no constant.**
It restores what Room A did and names what the frozen code requires.

**How the faults were found.** Between 18:22 and 20:24 the whole of Saturday's chain was run on the three
receivers and the TX, with the boards beside the laptop rather than on the rig: tracking captures, the
manifest, the DC2 pipeline, the identification capture for all six people on both days, and both frozen
identification scorers. Key presses were scripted through the real capture code in place of the keyboard
(`tools/dc2_hardware_check.py`), and every file went to a scratch folder. Nothing was written to `data/`,
to `runs/identify/dc2` or to the real DC2 outputs.

## 1. The corrections

| | found | now |
|---|---|---|
| **baselines** | the frozen cut normalises every window by its recording's empty-room baseline (`windows.baseline_dir_for`, `session_baseline`) and **stops** without one: "sidecar names no baseline capture". Room A took one, 60 s, operator seated, nobody in the grid, immediately before every participant (18 folders) | a **60 s baseline before the calibration walk and before each participant's tracking** (`make baseline BASELINE_S=60`), named with `--baseline`. The first addendum's "no 60 s empty room for tracking" is withdrawn: the baseline is part of the model's input, not a static recording of the kind dropped. A baseline that fails the stream gates is taken again |
| **the calibration recording's name** | the frozen recording list (`recordings.recordings`) keeps only recordings whose name, before its first underscore, is one of the six. A recording named `CAL` was dropped **without an error**: configuration B came out identical to A (`s_B` empty, the null left at -7.50, exit 0) | walked by **the day's first participant under `<name>_C`** (day 1 `PA5_C`, day 2 `PA6_C`). It replaces the first addendum's "participant code `CAL`". Its passes are never scored |
| **code length** | the capture tool accepts participant codes of **at most 8 characters**, so `PA5_CAL` was refused | hence `_C` |

**The block per person is now:** 30 s empty room at home; 60 s baseline; tracking; RX2 to the
identification spot; 30 s empty room there; the identification walks; RX2 home. The day plan
(`DC2_DAY_PLAN_2026-09-24.md`) has every command.

## 2. Two read-only checks, run on the day and before any figure

- `tools/dc2_day_check.py`, after each participant: the layout and manifest `dc2b` accepts; every
  tracking recording named for one of the six, with its baseline (60 s, gates passed), the tracking
  boards by MAC, Room A's geometry and the reaction-time bias recorded as applied; the stream gates of
  every capture; every identification recording present, complete, alternating, and in the duration limits.
- `tools/dc2_verify_run.py`, after `dc2b_pipeline` and **before any DC2 figure is read**: refuses unless
  every Room B session has calibration constants and a numeric `s_B`, and configurations A and B scored
  exactly the manifest's passes, with no calibration pass among them.

Both are tested on synthetic files (`tests/test_dc2_tools.py`), and each of the named catches fails its
test when it is disabled.

## 3. What the hardware check showed once corrected

Plumbing only. The boards were not on the rig and nobody walked, so no figure below is a result.

- **Tracking.** The calibration recording (8 passes) and two participants (20 passes each), each with its
  own 60 s baseline, passed the stream gates. The DC2 pipeline ran through every step with exit 0. `s_B` came out
  at 2.70, re-anchoring the null at -9.58. The gate fell back to 0.431, as designed, because the bracket
  was inverted: with nobody walking, the calibration "walks" are no busier than idle. The post-run gate
  VERIFIED the run: 40 of 40 participant passes scored, no calibration pass.
- **Identification.** All six people on both days: 24 empty rooms and 36 walk blocks, every block
  COMPLETE, every block alternating `A_fwd` then `A_rev`, every pass inside 1.5 to 12 s, none flagged,
  every stream gate passed. The view took exactly the 48 pre-registered recordings and left out the 12
  day 1 pace blocks. The frozen layout check passed. Both frozen scorers ran end to end and returned every
  pre-registered row (P1 to P6 and the within-day row; P1-GP with its four integrity checks). They ran
  with one CNN seed, 2 epochs and 100 draws, as plumbing. Their outputs went to scratch, so the
  once-only guard in `runs/identify/dc2` is untouched.

**Two hardware events, both caught by the stream gates:**

- At 18:56, all three boards saw the TX's sequence count jump by about 490 in one minute. The next
  minute was clean.
- At 19:18, after the laptop had slept (18:58) and half-woken (19:14), RX2's USB adapter stuck. Its port
  stayed listed but refused every setting. Unplugging RX2 and plugging it back in at 19:26 cleared it,
  and it ran cleanly for the next hour.

On the day, the laptop is kept awake (`caffeinate`) and on its charger.

## 4. The freeze

This file, `tools/dc2_day_check.py` and `tools/dc2_verify_run.py` are hashed in
`runs/TRACKING_FROZEN_2026-09-24b.json`, which references `TRACKING_FROZEN_2026-09-24.json`, and re-hashed
by `tests/test_freeze_2026_09_24.py`. A change before Room B data exists gets a new dated freeze; a change
after is POST HOC and says so.
