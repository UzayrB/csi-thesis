# HANDOFF: tracking, 2026-09-28 22:15 SAST (clock read). After DC2, and after the direction change

Tracking only. Identification keeps its own handoff and development log.

## 1. Read first

1. **`reports/BRIEF_render_and_prepress_2026-09-22.md`, INSTRUCTION 9:** the operator's direction
   change of 2026-09-28, verbatim. It governs all development from now on.
2. **The top section of `STATE.md`.**
3. **`reports/DC2_RESULTS_2026-09-28.md`:** the DC2 results, the "before" reference.
4. **`reports/DEVLOG_TRACKING_2026-09-28.md`:** the development log, which replaces
   pre-registration for development work.

`reports/HANDOFF_2026-09-23.md` is unsafe; never follow it. The older tracking handoff is
`reports/HANDOFF_TRACKING_2026-09-26.md`.

## 2. The rules now

- **Kept, as system requirements:**
  - no leakage: whole-session splits, and every statistic fitted on training data or on causal
    pre-pass data;
  - live claims causal;
  - the tracker signal-only: no pace, elapsed time or dead reckoning;
  - the rendering rules for demo videos;
  - `data/` read only; the free-movement recordings never used;
  - every existing report, freeze and result kept untouched.
- **Stopped for development:**
  - pre-registration of each change;
  - POST HOC labels;
  - the three-condition ship rule and rule (f);
  - deference to the frozen configuration;
  - asking approval for each development choice.
- **The evaluation standard:** leave one session out over A1, A2, A3, B1 and B2 (Room A 01, 02, 03;
  Room B B1, B2).
  - Every choice is made on validation inside the four training sessions.
  - Reported per held-out session and per room: committed and lock, the four edge lines, 95 percent
    intervals.
  - The frozen Room A to Room B figures sit beside them.
- **Standing practice:** British spelling, no em dashes, run `date` before writing any time, commit
  only own paths by name, never `pkill` broadly (kill by PID after reading the command line).

## 2b. THE SPLIT (22:26, the operator's decision, supersedes leave-one-session-out for tracking)

- **Train and choose on A1, A2 and B1 only.**
- **A3 and B2 are the tests and the renders,** never in training.
- **The baseline** is `ph_A3` / `ph_B2`:
  - A3: committed 88.33, lock 65.00;
  - B2: committed 57.50 (A) and 65.83 (B), lock 20.83 (A) and 30.00 (B).
- **D1 runs on this split.**

## 3. Where tracking stands (DC2 results, 2026-09-28)

- **The frozen A1+A2+A3 tracker on Room B:**
  - committed 42.92 (A) and 45.83 (B) over 240 walks;
  - lock 14.17 (A) and 20.42 (B);
  - `b_abstain_0.25` CONFIRMED, `a_veto_1.0` not.
- **Within Room B across days:** 18.75. The heads fit their own day and fall to chance on the other.
  Links 1 and 2 shift 3.4 and 4.6 dB in mean RSSI between the days.
- **Leave one session out, the current recipe (item 4 column ii), the development baseline:**

  | held out | committed A | committed B | lock A | lock B |
  |---|---|---|---|---|
  | A1 | 60.00 | 60.00 | 32.50 | |
  | A2 | 90.00 | 90.00 | 70.00 | |
  | A3 | 89.17 | 89.17 | 65.00 | |
  | B1 | 45.00 | 45.00 | 16.67 | |
  | B2 | 56.67 | 65.00 | 21.67 | 32.50 |

  Room A has no calibration walk, so B equals A there. The decoder's constants were tuned on Room A
  before DC2, which the development log must note.
- **Per-room normalisation from mismatched statistics failed.** Its test statistics came from idle
  radio, its training statistics from walking windows.

## 4. The machinery available

- **`pipeline/constrained/pd_cells.py`:** trains the five-head pool on any set of sessions from
  either room, then runs the frozen DC2 inference, decode and lock on one test session.
  - Calibration walks are kept out of training views; each Room B day has its own reader tag.
  - Plumbing: the shipped heads through it give the shipped decisions and lock 120 of 120.
    Retraining gives the 1 s heads bit for bit.
  - One cell trains in about 45 minutes on four sessions, 30 on three, 14 on one.
- **`pipeline/constrained/pd_report.py`:** accuracy, intervals and paired differences, keyed
  session|stem|pass.
- **Room B windows:**
  - 0.5 s press-aligned, under `runs/constrained/dc2_room_B_s0.5_pressalign/by_session/<B1|B2>/`;
  - 1.0 s, in `runs/constrained/windows_s1.0_dc2/`, with its features in
    `runs/dc2_results/shared10_roomB/`.
- **The DC2 command** is `dc2c_pipeline`: the frozen infer step collides two Room B sessions, and
  dc2c runs one session at a time.

## 5. The first development batch, D1

In the development log, section D1:
1. The leave-one-session-out baseline table.
2. Per-recording normalisation: every recording, training and test alike, standardised per link and
   channel by its own idle radio before its first press. That is causal pre-pass data, and it is the
   matched version of the normalisation that failed.
3. Choices made on inner validation. The ten distinct three-session training sets are each tested on
   both sessions they leave out, under both normalisations. The lock method (display lock or scorer
   lock) is a decode-time choice on the same validation.
4. The chosen configuration per held-out session, then the closing report.

## 6. Other sessions

- **Identification** runs in its own session. The GPU is tracking's; identification is CPU-only, at
  most 4 threads.
- **Shared files:** tracking writes the shared direction text in `STATE.md` and the memory note
  `direction-change-2026-09-28.md`. Identification adds its own subsections and memory.
- **Pushing:** it pushes `main`, and all tracking commits may be pushed.

## 7. Open items carried over

From `DC2_RESULTS_2026-09-28.md` section 7:
- the Room B setup photographs;
- a per-link look at PA2's quiet day 1 radio;
- the missing Room B display head;
- the edge lines behind A1's pooled gain.
