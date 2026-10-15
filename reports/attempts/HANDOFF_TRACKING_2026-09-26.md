# HANDOFF: TDR-03 tracking, 2026-09-26 22:57 SAST (clock read). DC2 day 2 is tomorrow, 27 September.

Tracking only. Identification appears only where it touches tracking. Background, not a task list:
anything marked OPEN needs Uzayr's word before you act.

**Also read the companion `reports/HANDOFF_TRACKING_LIVE_AND_CAPTURE_2026-09-26.md`** (session TestRig):
day 1's RX2 failures, day 2 capture cautions, and the live system. Identification is in
`reports/HANDOFF_IDENTIFICATION_2026-09-26.md`.

## 1. Who and how

- **Who:** Uzayr Ballim, EEE4022S thesis. WiFi CSI tracking (TDR-03): three ESP32 receivers and one
  transmitter, 12 taped lines on a 5 x 5 m grid.
- **The claim:** cross-room generalisation. DC2 (Room B, 26 and 27 September) is the test.
- **Writing:** British spelling, no em dashes.
- **The clock:** run `date` before writing any time into a record.
- **Commits:** commit only when asked, own paths only, by name, never `git add -A`.
- **Standing rules:** signal-only; `data/` is read only; never edit or move a file listed in
  `reports/PINNED_FILES.txt`; freezes are superseded, never overwritten; any change after Room B data
  exists is POST HOC and says so in those words.
- **Processes:** never `pkill` broadly; kill by PID after reading the command line.
- **Memory:** notes at `~/.claude/projects/-Users-uzayrballim-Desktop-UNI-2026-EEE4022S-Code/memory/`
  (edge-line recall beside pooled figures, substitution-test standard, launch before reporting, verify
  claimed guards).
- **Another Claude session, "TestRig",** works in this repo on DC2 tooling and a live system
  (`pipeline/live/`, `tests/test_live_*.py`, uncommitted). Message it before touching shared files;
  never stage its files.
- **Read first:** `reports/MODEL_FREEZE_DC2.md`, `STATE.md`, `README.md`, then
  `reports/DC2_DAY_PLAN_2026-09-24.md`. Ignore `HANDOFF_2026-09-23.md`: unsafe.

## 2. Active threads

**DC2 day 2 capture, tracking part.** `STATUS: active, tomorrow`
- **Session and names:** B2, and `--day 2` / `session_02` for identification. Participants come in any
  order.
- **Calibration:** walked by whoever is first, as `<name>_C`, before any tracking walk, then
  `python -m pipeline.constrained.dc2b_manifest --session B2 --calibration participant_<name>_C_walk`.
  The two names must match; the manifest refuses a recording that isn't on disk.
- **Each person:** identification, RX2 home, the home empty room, a fresh 60 s baseline
  (`make baseline BASELINE_S=60 OUT=data/room_B/session_B2 EXPECT=150 NODES="$NODES"`), then tracking
  with `--baseline "$(ls -dt data/room_B/session_B2/2026*/ | head -1)"`, then
  `python -m tools.dc2_day_check --day 2`.
- **Optional check in front of each capture:** `python -m tools.dc2_capture <module> <args>`. It
  stops on a wrong name, day, existing file, missing baseline or calibration order, warns on a stale
  baseline or someone else's height and weight, then asks for the person's name typed. Uncommitted, and
  not in the day plan.
- **Next action:** none unless Uzayr asks. The capture is his.

**Day 1 tracking data (B1), captured 26 September.** `STATUS: waiting on Uzayr`
- **On disk:** `data/room_B/session_B1/`; the day check says NOTHING WRONG and every gate passed.
- **Calibration:** `participant_PA2_C_walk`, 10:43, 11 passes (the plan said 8), in the manifest.
  `aborted: {}`.
- **Tracking,** 20 passes each, in this order: PA2 11:04, PA1 12:09, PA3 12:41, PA5 13:08,
  PA4 13:46, PA6 14:14.
- **Issue 1, PA5:** 11 of 20 passes flagged, passes 10 to 20, "anchors 1->2: 0.06 to 0.19 m/s
  implies a SPURIOUS press". The first press comes 7 to 18 s before the second (pass 10: 7.36 s,
  pass 11: 17.76 s). The pipeline aligns windows to the FIRST press and has no rule for flagged passes,
  so the 2 s lock will read PA5 standing still.
- **Issue 2, PA1:** his tracking names PA2's 11:02 baseline (`20260926-110249`). His own 11:54
  baseline was moved to `data/room_B/aborted/pa1_d1_no_rx2/` with his RX2-less identification files.
- **`data/room_B/aborted/`** (moved by Uzayr on day 1) holds identification files from RX2 failures.
  The tracking view reads `session_*` folders only.
- **Next action:** report both issues to Uzayr before any analysis. The pre-registered rule is that
  only passes abandoned at capture time are aborted, so any exclusion now is POST HOC.

**Analysis after day 2.** `STATUS: waiting (both days first)`
- Run in this order, only after both days' `--final` checks pass:

      python3 -m tools.dc2_day_check --day 1 --final && python3 -m tools.dc2_day_check --day 2 --final
      python3 -m pipeline.constrained.dc2b_pipeline --room room_B
      python3 -m tools.dc2_verify_run --room room_B        # must say VERIFIED before any figure is read
      python3 -m pipeline.constrained.dc2b_scorerlock --room room_B

- Never `dc2_pipeline` or `dc2_scorerlock` on DC2 data.
- **Pre-registration:** `reports/PREREG_DC2_crossroom_2026-09-22.md` sections 10 to 13, plus addenda
  24, 24b, 25 and 25_schedule.
- **Primary:** configuration A (frozen) against B (gate and null re-anchored on the calibration walk).
- **Confirmatory,** each at 97.5 %: `a_veto_1.0` and `b_abstain_0.25`.
- **Exploratory:** `B_prod0.25` and the scorer lock at w 0.25.
- **Chance:** 8.33 %.

**Demo v2 dot timing.** `STATUS: waiting on Uzayr`
- `runs/constrained/demo_v2/` holds six videos drawn at `HEAD_OFFSET_S` 0.375.
- At 0.375 on the demo pairing: dot ahead on 34.7 % of frames, -0.28 m, within 0.5 m 58.2 %.
- The alternative, 0.5: 44.3 % ahead, 61.6 %; choosing it would be POST HOC.
- Re-render (about 10 min): `F4_HEAD_OFFSET_S=0.5 OMP_NUM_THREADS=1 python3 -m pipeline.constrained.f4_render`.

## 3. Decisions

- `DECIDED` Participants come in any order, and whoever is first does the calibration as `<name>_C`
  (Uzayr, 25 Sept; `reports/PREREG_DC2_ADDENDUM_2026-09-25_schedule.md`, uncommitted and unpinned).
- `DECIDED` Identification first, then tracking, per person (addendum 25, TestRig's, uncommitted).
- `DECIDED` The model is frozen for DC2 (freeze 23h, `runs/TRACKING_FROZEN_2026-09-23h.json`, plus
  addendum B hashing the 12 half-tree reader files, committed `b528de2`).
- `DECIDED` The frozen demo (`runs/constrained/demo/`, 0.75) is untouched; demo v2 is committed at 0.375
  (`bddd91e`).
- `PROPOSED` Keep three empty-room captures per person: each has a reader, and merging needs frozen-code
  changes.
- `PROPOSED` Keep the within-person identification block order. Uzayr has not answered.

## 4. Artifacts

- **Headline** (Room A, nine cross-day pairings, semi-bounded committed line):
  - 62.50 % [30.00, 86.67] pre-registered;
  - 73.33 % [35.00, 87.50] post-amendment (`a_veto_1.0`, condition (f) amended post hoc on 23 Sept);
  - paired +3.80 [0.83, 6.94];
  - drawn lock 53.33 held-out.
- **Donor swap** (`pipeline/constrained/f5_donor.py`, `runs/constrained/fh/f5_donor/`): swapping
  another participant's radio into a walk makes the answer follow the donor's line 61.1 % of the time,
  against 63.3 % accuracy on the walk's own radio; it stays on the true line 3.4 % (chance 8.3 %). It
  reproduces the shipped decisions 1080 of 1080. The along-line position is about half radio (r3_prior
  substitution ratio 0.52).
- **Per participant, committed, median of nine:** PA5 60, PA1 70, PA2 70, PA3 80, PA4 70,
  PA6 55. Session-01 folds 20 to 45 % for all but PA3.
  (`reports/DEMO_V2_AND_CSI_CHECK_2026-09-24.md`.)
- **`tools/dc2_capture.py`** and `tests/test_dc2_capture.py`: 17 tests, red-checked. Uncommitted.

## 5. Already ruled out

- **Re-rendering the frozen demo videos:** hashed in 23h; new renders go to `demo_v2` only.
- **Choosing the display phase on the demo pairing:** it is selection on shown data. It was chosen on
  `s0103_to_s02`.
- **`--participant CAL`:** dropped silently by the pipeline.
- **Naming Room B sessions 01, 02 or 03:** the view then scores Room A data as Room B.
- **Gmail for backups:** a day is about 1 GB.
- **A fixed slot order:** withdrawn on 25 Sept.

## 6. Open loops

- **PA5 passes 10 to 20 on B1:** keep them as evaluated, or exclude them POST HOC? Ask Uzayr; measure
  nothing first.
- **PA1's baseline** is PA2's from 11:02: accept and disclose, or not? Ask Uzayr.
- **Commits waiting on Uzayr:** the schedule addendum, `tools/dc2_capture.py` and its tests, and this
  handoff. Pinning the addendum is his call.
- **Demo dot timing:** 0.375 or 0.5?
