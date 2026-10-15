# PREREG: the radius-free switch (R0) on A3 and B2, then the 12 videos. Written 14 October 2026, from 18:36 SAST (clock read), before any A3 or B2 replay

**Status.** Written and committed before any replay of this job. Its SHA-256 goes in `PREREG.md.sha256` and in the commit
that adds it; it is never edited afterwards, and any change before a run goes in a dated addendum. The harness
(`harness.py`) and the driver and scorer (`run.py`) are committed with it.

**The authority.** The Mastermind's queue item 12 (d422fced), sent to the Code agent at 18:32 as the spec and slot, on
Uzayr's request to the Mastermind ("do 1 and 2 and after that we will decide if we want to ship it"); Uzayr's go in the
Code agent's own chat (14 Oct, after 18:32): "do the Mastermind's queue item 12 as it sent you ... nothing ships until I
decide". Nothing ships, and the live app's default stays `clean_1s`.

**Labels.** Development evaluation, all data seen. **This is A3's tenth look and B2's eighth by the thesis table's count**
(the head-offset record's count, in which the 14 Oct 1.0 s decode was A3's ninth and B2's seventh); the deployed and the
zero-shot B2 decodes are both inside B2's eighth. R0 was chosen after the development-rotation result was seen
(`runs/switch_radius_2026-10-14/RESULT.md`, caac5a6c).

## 1. The arms

- **R1.5:** the shipped display, the app's default profile `clean_1s` (no profile given to the app).
- **R0:** `clean_1s` with the switch's `radius_m` set to None: a profile named `clean_1s_r0`, a deep copy of
  `DISPLAY_PROFILES["clean_1s"]` with only `sett["switch"]["radius_m"]` changed, registered in memory in each replay's
  process (`final_model.DISPLAY_PROFILES` is not edited on disk) and given to the app's replay as its `profile`. Every
  other setting is asserted equal to `clean_1s` on the built session.

## 2. Step 1: the A3 and B2 decodes (untimed)

- **Cells:** the deployed model on A3 (`f05_A3`, session 03) and on B2 (`f05_B2`), and the zero-shot model on B2
  (`z05_B2`): the six evaluated recordings of each, semi mode (one start press per walk), the causal clock, through the
  live app's own replay (`app_replay.replay_inner(model, session, stem, "start", "causal", False, profile=...)`), with the
  app's output folder (`app_replay.OUT`) set to this folder.
- **The device:** each replay calls `force_cpu()` before anything loads and asserts `nets.device()` is `cpu` at its start
  and its end, recording both; a device other than `cpu` is a STOP.
- **Compute:** one process per replay, nice 10, OMP_NUM_THREADS 1, the cell's own environment (`final_model._env`), at
  most 4 at a time; a memory guard kills the job above 12 GB in total or below 30 % free. A write guard refuses any write
  outside this folder.
- **R1.5 reuses the 14 Oct CPU 1.0 s logs** (`runs/head_offset_2026-10-14/step4_cpu/`, 18 recordings, written on the CPU
  with the clean profile and the head offset set to 1.0 s, the settings `clean_1s` holds) if **one check replay per cell**
  under R1.5 equals its log row for row (the text lines, every field and float): in each cell, the first recording
  alphabetically with the most switches in those logs: deployed A3 `participant_PA2_TEST_walk` (1 switch), deployed B2
  `participant_PA2_walk` (1), zero-shot B2 `participant_PA6_walk` (2). **Any difference is a STOP**, reported to the
  Mastermind before anything is scored. The three check replays reproduce logs already seen and add no figure.
- **Then the 18 R0 replays** (6 per cell). 21 replays in all.

## 3. The STOPs

- **Locks and committed lines** (and presses and true lines) of R0 must equal R1.5's on every walk of every cell; any
  difference is a STOP, nothing is scored, and the Mastermind and Uzayr are told.
- **No shipped or hash-listed file changes:** the SHA-256 of every file under the head-offset ship's hash roots (its
  `ship.py` ROOTS, with `runs/live/renders_K1gf` now `renders_K1gf_0p75s` and `renders_K1gf_1s` added), plus `pipeline/`,
  `runs/head_offset_2026-10-14/`, `runs/switch_radius_2026-10-14/` and every file of the two model-set manifests, is taken
  before step 1 and checked after step 1 and after step 2, with nothing expected to change; any change is a STOP. New files
  (this folder's outputs, the new video folder) are listed, not failures.
- Also STOPs: a replay errors; a write outside this folder (step 1).

## 4. The measures (per cell; the radius test's measures)

Per cell (no rotation weighting). Intervals: 95 % percentile bootstrap over walks, 1,000 draws, seed 0 (a fresh generator
per measure, as the head-offset step 4 scorer); **paired** intervals draw the same walks in both arms and take R0 minus
R1.5. Helpers from `runs/a3_clean_2026-10-08/measures.py`, unchanged.
1. **Switches,** each classed by the walk's true line: wrong-to-right (W2R), right-to-wrong (R2W), wrong-to-wrong (W2W)
   (`measures.switch_walk`'s classes), raw counts; the net **N = W2R minus R2W** for each arm, with the paired interval of
   N(R0) minus N(R1.5).
2. **The share of drawn frames on the true line** (all walks): frames from press + 2.0 s on (`measures.from_press_frames`),
   whose named line (`measures.named_line`) is the true line, pooled over the cell's walks; each arm's value and interval,
   and **the paired interval of R0 minus R1.5**.
3. **Dot error from the first decoded frame** (`measures.decoded_frames`, the truth at frame time minus 2.0 s): the median
   of the pooled frames, **on all walks and on correct-lock walks**; each arm's value and interval, and the paired
   interval.
4. **Per true line** (12 rows, E_col1, E_col5, E_row1 and E_row5 among them): walks, correct locks, each arm's W2R, R2W and
   W2W, each arm's share on the true line and dot-error median on all walks, and the difference in share.
5. **Slides over 1.5 m** (`switch_walk`'s `jumps_over_1_5m`), switch events, walks ending on the committed line, the
   minimum causality margin, the render rules on R0's logs (`app_score.rule_checks`: park, together, lock changes, walks
   over one switch), and the list of walks whose switches differ.
6. **PA6's B2 walk 5** (deployed B2, `participant_PA6_walk`, pass 5; true D_rev, locked B_rev, committed D_rev): its
   switches, the line drawn at its end and its share on the true line under R0, R1.5 and the 0.75 s display shipped until
   14 Oct (`runs/live/replay/final/semi_disp-K1gf_causal/`).

## 5. The confirmation rule (per cell)

**Confirmed** if N(R0) is higher than N(R1.5) (strictly) **AND** the paired 95 % interval of the share of frames on the
true line (R0 minus R1.5) lies above zero (its lower bound above 0). **Otherwise not confirmed.** Each of the three cells
is reported on its own; the dot error is reported either way. No overall rule: the decision is Uzayr's.

## 6. Step 2: the 12 videos (timed; only after step 1 ends, and only after the Mastermind's slot and LaTeX hold)

- **The videos:** the deployed model, A3 and B2, the six recordings of each, semi mode, real-time pace, the app's own
  screen, through the app's command line's inner path (`app_replay.session_inner`: the model-set check, then the replay),
  in a process that first calls `force_cpu()`, asserts the device, and registers `clean_1s_r0` (the session's switch
  radius asserted None on every recording). Videos into a NEW folder, `runs/live/renders_K1gf_1s_r0/` (refused if it
  exists); their logs into this folder. Alone on the machine, nice 19, 3 at a time, the 1-minute load sampled every 15 s.
- **Acceptance:** all 12 exit 0, and **each video's log equals its step 1 R0 replay row for row** (the parsed rows, as the
  1.0 s renders' rule). Any failure: nothing is accepted and the Mastermind is told.
- **Then `ACCEPTANCE.md`** in the video folder, in PA codes (PA1 PA1, PA2 PA2, PA3 PA3, PA4 PA4, PA5 PA5,
  PA6 PA6), with the 1.0 s acceptance table's columns (committed right, lock right, dot medians, render-rule failures,
  the first frame's distance from the entry, the switches by kind, the draw lag, log equal to the fast replay).
- Render processes carry no write guard (the 1.0 s renders used the app's command line without one); the hash check
  after step 2 covers them.

## 7. Not changed

`pipeline/` on disk, `FINAL_CONFIG.md`, the model sets, every shipped replay and render, the head-offset and radius-test
files, identification, and the report repository. The live app's default stays `clean_1s` with the radius.

## 8. Deliverables

`RESULT.json` and `RESULT.md` (step 1), `RENDERS.json` and the video folder's `ACCEPTANCE.md` (step 2), each reported to
the Mastermind for review (DONE after each step) before Uzayr decides on shipping.
