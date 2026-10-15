# Handoff companion: tracking's live system and day 1 capture incidents, 2026-09-26 22:59 SAST

Read `reports/HANDOFF_TRACKING_2026-09-26.md` first (written by the session "Tracking2"). It holds the
tracking state, decisions and the analysis order. This companion, from the session "TestRig", adds
three things that handoff does not cover in full. Identification is in
`reports/HANDOFF_IDENTIFICATION_2026-09-26.md`.

## 1. Day 1 capture incidents that touch tracking

- **RX2 went silent three times on day 1, each right after RX2 was moved** between home and the
  identification spot. Its USB adapter wedges: the port stays listed but delivers 0 bytes, and only
  unplugging and replugging RX2 clears it. The capture does NOT stop on a dead link: it writes
  786-byte, header-only files. `dc2_day_check` checks counts and durations, not bytes per link.
- **Every day 1 recording was checked link by link at 14:20** (identification, tracking, the
  calibration walk and six baselines). RX2 is within a few percent of RX1 in every recording, the three
  links start and stop together, and no recording has a gap over 1 s.
- **Tracking's only casualty** was the 11:54 baseline, now in `data/room_B/aborted/pa1_d1_no_rx2/`.
  That is why PA1's tracking (12:09) names PA2's 11:03 baseline (`20260926-110249`); see the main
  handoff's Issue 2.
- **PA5's flagged passes** (main handoff, Issue 1) were confirmed at 22:58. Passes 10 to 20 are all
  flagged, with the first press 7.4 to 17.8 s before the second while every later gap is about 1 s. The
  first space was pressed while she stood at the start. **For day 2:** press the first space as the
  walker crosses the 0 m tape while walking.
- **Calibration** has 11 passes, not 8. The manifest names the whole recording, so all 11 are
  calibration.

**Day 2 cautions** (27 Sept, session `B2`):

- After every RX2 move, run `make run DURATION=10 NODES="$NODES"` and see RX2's packets before
  recording.
- Check the baseline the tracking command will use:

      ls -dt data/room_B/session_B2/2026*/ | head -1

  It must be this person's own, taken just now. If the pre-flight warns that the baseline predates the
  last recording, take a fresh one.
- To redo a recording, move it aside into a NEW folder with `mkdir` and `mv -n`. Plain `mv` into a
  shared folder overwrote two day 1 files.

## 2. The live system (`pipeline/live/`, built 25 Sept)

`reports/LIVE_SYSTEM_2026-09-25.md` has every gate's numbers. In summary:

- **Proof.** On the Room A stand-in (session 03, heads `s0102_to_s03`), raw packets and presses through
  the whole session give the shipped committed decision on 120 of 120 passes, and `f3_render`'s drawn
  frames on 120 of 120 walks (5055 of 5055 frames). Every component is also gated alone. Identification
  gives `id29_dc2_score`'s features and predictions exactly, on synthetic recordings.
- **Presses are RAW key times.** The sidecar stores `time.monotonic()` unchanged, and the press-aligned
  lattice is phased on it. Do not subtract the reaction-time bias. The live system also needs the END
  press, because the lattice places each segment boundary with it; the decoder is never told it.
- **Timing, idle laptop.** Per window, p99 0.20 s. The largest gap between outputs is 1.9 s. Windows
  queued behind a start press are ready up to 1.8 s after they end.
- **Entry command:** `python3 -m pipeline.live {gates,replay,replay-identify,rig}`.
  - `replay --stem participant_<name>_TEST_walk --screen --passes N` plays a session 03 recording in a
    window, with the green truth marker and a right-hand verdict banner (green right, red wrong).
  - The window mode itself has not been tried; the saved snapshots have.
- **Not live for Room B.** There is no DISP_END display head for `s010203_to_sB`, no Room B tree binding,
  and no configuration B constants in the live path. `rig --room B` refuses, and the rig has never run on
  the boards.
- **Tests:** `tests/test_live_*.py`. The checks that read the shipped tree run in a child process
  (`tests/_live_checks.py`), because binding the tree roots inside pytest broke the suite. `make test`:
  1106 passed, 18 skipped, about 10 min on 26 Sept.

## 3. Demo videos, day 2 (optional)

Film tracking walks for a side-by-side with the render:

- a still tripod outside the grid;
- the phone in airplane mode, since its radio shares 2.4 GHz;
- set up and recording before the 60 s baseline, untouched until that tracking recording ends;
- the laptop clock in frame at the start;
- 1080p at 30 fps, about 60 MB a minute.

## Uncommitted (TestRig's, commit only when Uzayr asks)

`pipeline/live/`, `tests/test_live_*.py`, `tests/_live_checks.py`, `runs/live/`,
`reports/LIVE_SYSTEM_*.md`, this file, `reports/HANDOFF_IDENTIFICATION_2026-09-26.md`, and the
identification-first reorder edits:

- the day plan and the ID runbook;
- `PINNED_FILES.txt`, the 25 Sept freezes and addendum, and `tests/test_freeze_2026_09_24.py`;
- `tools/dc2_hardware_check.py`;
- the two README index lines.
