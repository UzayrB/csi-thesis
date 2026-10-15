# The live application on the boards (15 October 2026): H0 to H5

Uzayr's prompt (PROMPT.md), run by the Mastermind at his word. Development evaluation, all data seen. PA codes only
(PA1 to PA6 as in the report). Records in this folder: QUEUE.md, CHECKINS.md, H0_STATE.md, H1_OFFLINE.md, H2_BOARDS.md,
H3_RIG.md, H4.log, H5.log and the per-run folders.

## Summary

- **Tracking on the boards: READY.** A 6-minute smoke run on the boards (CPU, `clean_1s_r0`, semi mode, test key presses
  every 15 s) ran without an exception, and its own recording replayed through the harness gives the live log
  **identical row for row** (1,388 rows, 23 committed lines, 23 locks). B2 streamed at 1x through the boards' ingestion
  path: every stream's own capture replays identical row for row (6 of 6); against the fast replay, committed 118 of
  120 and locks 114 of 120 (the wall-clock effect, below).
- **Identification on the boards: works, NOT identical to its replay.** 18 presses, 18 decisions (schema v3), adaptation
  after each decision with no walk waiting, but 17 of 18 decisions before the cap (t0 + 5.30 s; median 0.880 s after
  t0 + 4.0 s, one at 1.683 s) and the replay of its recording differs on every decision (largest ensemble difference
  0.577 on the last, whose top class changed; up to 0.061 on the others). The replay is deterministic (two replays
  identical); the engine's decisions depend on when it polls relative to the frames it holds, which the recording does
  not keep.
- **Three faults found and fixed** (none in model, weight, threshold, display, decode or decision code): the rig's key
  reader never entered cbreak mode (a SPACE needed Enter); the board rig never forced the CPU (the tracker ran on the
  GPU); the rig kept nothing it received (now it records). Two found and NOT changed (decision-adjacent, Uzayr's call):
  a press before the first anchored packet crashes instead of refusing; after a refusal the final drain raises a second,
  harmless error.

## H0, state: PASS

HEAD baddef1f at the start. Tracking: MODEL_CELLS["final"] = f05_A3 / f05_B2, DISPLAY_PROFILE `clean_1s_r0`, semi, CPU.
Identification: deploy_all5_v5 (engine v5), staged extraction with 4 workers, mps for a v5 manifest. Quiet machine;
pre-flight without a baseline ALL ok (09:54:06).

## H1, offline proofs: PASS

The live tests (tests/test_live_*.py): 49 passed, 1 skipped; the skipped slow test run with TDR_SLOW=1: 7 of 7 passed.
The identification engine files (engine.py, identify_engine.py, idv2_core.py, idw_core.py, idz_core.py, iv5_rig.py) are
unchanged since 56eea977, the code that produced runs/identify/v5/rig_timing_confirm_staged.json (12 Oct), so the
streamed confirmation was not rerun. The live tests were rerun after each of the seven code commits below: 49 passed,
1 skipped every time.

## H2, the boards: PASS (after one fix by Uzayr)

Ports by station MAC: RX1 68:09:47:4c:ef:b4, RX2 20:50:0d:1a:28:74 (its cable flapped at plug-in, then held), RX3
20:50:0d:30:5f:80; the TX on power only (its frame counter: 150.0 frames/s on every receiver). First capture (10:01)
FAILED: RX3 loss 9.74 % (RSSI -84 dBm). Uzayr moved RX3 closer; re-check (11:44, 3 min, alone):

| receiver | packets/s | loss (TX counter) | parse errors | config |
|---|---|---|---|---|
| RX1 | 148.4 | 1.10 % | 0 | channel 11, HT20 |
| RX2 | 149.3 | 0.50 % | 0 | channel 11, HT20 |
| RX3 | 149.8 | 0.14 % | 0 | channel 11, HT20 |

## H3, the rig keeps what it receives: PASS

Code commits (each with its reason; live tests after each):
- 18c49ef8 **fix**: rig.run entered the key reader with start() only, leaving the terminal line-buffered; in a
  pseudo-terminal test one SPACE never arrived without Enter. Now a context manager (cbreak, restored after).
- 0dcf44ac **fix**: rig_inner never called force_cpu(); nets.device() gives mps on this Mac, so the board rig ran the
  tracker on the GPU, unlike every replay. Now forced onto the CPU.
- ba6beee1, 5d0aa41d, c4169c88, 8200fca3 **recording**: rig.run passes run_capture's own writer (the sessions' format)
  into rig_<mode>_<time>/ in this folder, on by default, with every key as received (<stem>.keys.json, each receiver's
  counters); the tracking rig logs its outputs with the replay harness's Logger (<stem>.log.jsonl), writes the presses
  and baseline (<stem>.gt.json, with baseline_capture) and its measurements (<stem>.summary.json), and keeps the record
  when a failed session cannot close; the identification rig writes its adaptations (<stem>.summary.json).
- fcefe97c, 8d1e2b82 **test-only key injector**, off unless RIG_TEST_INJECT is set (renamed from TDR_RIG_TEST_INJECT,
  which pd_cells.env_for strips from the rig's environment).

Proof on a stream (B2 PA3's recording at 1x into rig.run itself): a recorded run's capture replays IDENTICAL row for row
(1,370 rows; and 1,369 for a second recorded run). Recording on against off, walk by walk: committed 20 of 20, locks
18 of 20; two runs that BOTH record differ as much (committed 20 of 20, locks 19 of 20), so recording adds nothing
beyond the run-to-run variation of two wall-clock streams (H3_RIG.md).

## H4, smoke runs on the boards (no walker): tracking PASS, identification PARTIAL

Baseline: 60 s at 12:27:33 (Uzayr seated at the desk: not a true empty room, acceptable for a smoke run). Pre-flight
with it: ALL ok.

**Tracking** (rig_tracking_20261015_124531; `python3 -m pipeline.live rig --baseline <dir> --minutes 6`, RIG_TEST_INJECT
15,15):
- pre-flight ALL ok; no exception; exit 0; CPU; `clean_1s_r0`;
- 24 presses, 23 committed lines and 23 locks (the 24th press fell at the run's end);
- packets parsed 53,486 / 53,704 / 53,989; dropped 0; read errors 0;
- per-window service median 0.076 s, p95 0.098 s, max 0.29 s (693 windows);
- draw lag median 0.0 s, max 1.62 s; frames late over 0.1 s: 339 of 1,316; over 0.5 s: 134;
- redraws 2,614 against 3,600 ten-per-second slots (73 %; 160,828 consumer ticks);
- press service median 0.744 s, max 1.58 s;
- **its recording replayed through the harness: IDENTICAL row for row, in order** (1,388 rows; committed 23 of 23,
  locks 23 of 23).
- **The refusal:** a press at 6 s gave the app's own "REFUSED: 3 idle windows before the first press, below 10; record
  at least 10 s of stillness before the first walk" (rig_tracking_20261015_125949). Two notes, NOT changed: a press at
  3 s, before any packet had been anchored, crashed instead (stream._shift, first_base None: TypeError); and after the
  refusal, run_capture's final drain feeds the refused session, which raises an AssertionError (harmless, noisy).

**Identification** (rig_identify_20261015_123240; `python3 -m pipeline.live.identify_engine rig --mode identify --room new
--minutes 6`, RIG_TEST_INJECT 20,20):
- 18 presses, 18 decisions written, all schema id_engine_decision_v3, deploy_all5_v5, room new; GPU (the adaptations
  took 0.08 to 0.09 s; on the CPU they reach about 6 s);
- **decision delay after t0 + 4.0 s: median 0.880 s, max 1.683 s; 17 of 18 before the cap t0 + 5.30 s** (the 12 Oct
  streamed confirmation: median 0.545 s, max 0.585 s, 299 of 299);
- adaptation after each decision: 17 settles, every one at the next poll, none waited for by a walk;
- memory (the rig and its workers, sampled every 5 s): 1.24 to 3.15 GB, slope 10.7 to 13.1 GB/h after the first 1 to
  2 minutes; a 6-minute run with workers still warming, not comparable with 12 Oct's 2.18 GB/h over 65 minutes;
- **its recording replayed through the engine: presses equal, argmax 17 of 18, largest ensemble difference 0.577**
  (the last decision, top P1 live against P2 replayed; 0.0001 to 0.061 on the others). Two replays of the same capture
  are identical (0.0), and polling the replay a fixed 0.05 to 0.3 s ahead of its data changes its decisions by up to
  0.13: the engine's decisions depend on when it polls relative to the frames it holds. On the boards, run_capture
  hands the engine one frame per loop and polls it on the wall clock, so whenever the loop is held up (the window's
  redraw, a decision) the poll runs ahead of frames still queued; the recording keeps each frame's time, not the
  poll sequence, so the replay cannot reproduce it. Making identification replay exactly needs either the engine to
  decide on data time (every receiver's frames past the window's end) or the rig to record its poll sequence (a
  decision-code change or a further recording change: Uzayr's call). The likely cause of the slower decisions is the
  same loop with a real window (12 Oct's confirmation drew off screen); not tested.

## H5, B2 streamed with the shipped tracker: PASS (as the 30 Sep stream)

The streamed rig's code (stream_source.stream_inner, rereplay_inner, compare; unchanged; the cell environment of the
CLI) at 1x, alone, outputs in H5_stream/ instead of runs/live/stream_disp-K1gf/; the reference a fresh fast replay of
each recording through app_replay with the shipped default (H5_fast/, `clean_1s_r0`, causal clock, CPU: 20 committed
and 20 locks each).

| recording | re-replay of the stream's capture | committed equal | locks equal | packets parsed | dropped | window service median / max (s) | frames late > 0.1 s / > 0.5 s | announcement after the walk's end median / max (s) | press service median / max (s) |
|---|---|---|---|---|---|---|---|---|---|
| PA5 | IDENTICAL (1,381 rows) | 20 / 20 | 19 / 20 | 162,899 | 0 | 0.081 / 0.247 | 203 / 60 | 1.142 / 2.208 | 0.797 / 1.667 |
| PA1 | IDENTICAL (1,388) | 20 / 20 | 19 / 20 | 163,607 | 0 | 0.081 / 0.247 | 184 / 53 | 1.111 / 2.132 | 0.788 / 1.816 |
| PA2 | IDENTICAL (1,386) | 20 / 20 | 18 / 20 | 157,258 | 0 | 0.082 / 0.264 | 203 / 61 | 1.405 / 2.145 | 0.792 / 1.881 |
| PA3 | IDENTICAL (1,368) | 20 / 20 | 20 / 20 | 156,996 | 0 | 0.081 / 0.255 | 183 / 60 | 1.476 / 2.151 | 0.800 / 2.201 |
| PA4 | IDENTICAL (1,422) | 20 / 20 | 18 / 20 | 162,256 | 0 | 0.082 / 0.246 | 199 / 59 | 1.235 / 2.117 | 0.803 / 1.860 |
| PA6 | IDENTICAL (1,385) | 18 / 20 | 20 / 20 | 165,636 | 0 | 0.080 / 0.562 | 235 / 74 | 1.186 / 2.179 | 0.790 / 3.051 |
| **total** | **6 of 6** | **118 / 120** | **114 / 120** | | **0** | | | | |

- **Why locks and two committed lines move:** the stream stamps every packet and press on the wall clock as a board
  run does, so press-phased windows move by milliseconds (every walk's minimum margin differs by a few ms) and
  borderline outputs tip. The 30 Sep stream (earlier heads and display): committed 120 of 120, locks 114 of 120; the
  locks now agree exactly with that, and two committed lines moved on PA6: walk 1 (the same exit window, +5.0 s, a
  different winner: a near-tie, on the walk that also reads the recording's idle statistics) and walk 10 (the causal
  exit at +3.5 s against +5.5 s). Each stream's own capture replays identical, so the app is the same on both paths.
- **Late frames and slow presses:** a press takes about 0.8 s (up to 3.1 s) and the screen draws in the same thread, so
  about 15 % of frames are drawn over 0.1 s late and 5 % over 0.5 s late (as noted 30 Sep: a separate screen thread or
  a cheaper press, Uzayr's decision).

## H4 after the fix (Uzayr: "Fix H4 needs to be perfect"; 13:05 to 13:56)

**The fixes** (no model, weight, threshold, display, decode or decision rule changed):
- 90d878c8: identification's rig consumer hands frames to the engine in timestamp order, one group of equal t_mono at a
  time below a horizon (the oldest latest frame of the receivers still sending, and 0.05 s behind now), each group
  followed by the keys up to its time and a poll AT ITS TIME (before: polls at the wall clock while frames were still in
  the capture queue, so windows could be cut before their last frames arrived). iv5_rig's timing harness follows it.
- 86b122ac: the tracking consumer refuses cleanly a press before any packet (before: a TypeError) and ignores packets
  after a refusal (before: a second error from the final drain).

**Offline proofs before any board run:**
- Proof A (h4fix_offline.py): the morning's board recording fed canonically through the new consumer equals the replay
  made before the change (18 of 18, differences 0.0); fed as two simulated board runs (serial chunks 0 to 30 ms late,
  receivers interleaved, one frame per loop, about 308 stalls of 0.1 to 0.4 s each, the clock running ahead of queued
  frames) it gives identical decisions.
- Proof B: B2 through the fixed recorded-source rig: 299 of 299 decisions identical to the 12 Oct confirmation (tops,
  ensemble probabilities, components: differences 0.0). The fix changes no decision.
- Live tests after the fixes: 49 passed, 1 skipped.

**The board rerun** (H4_run3.log; fresh baseline 13:21:12, Uzayr seated at the desk; pre-flight ALL ok):

| check | result |
|---|---|
| press at 3 s (before any packet) | **clean refusal**: "REFUSED: no packets had reached the app before the first press; stand still for at least 10 s before the first walk"; no traceback |
| press at 6 s (3 idle windows) | **clean refusal**: "REFUSED: 3 idle windows before the first press, below 10 ..."; no second error |
| tracking, 6 min (rig_tracking_20261015_132620) | exit 0, no exception, CPU, clean_1s_r0; 24 presses, 23 committed, 23 locks; window service median 0.076 s, max 0.29 s; press service median 0.75 s, max 1.59 s; packets 52,813 / 53,342 / 53,872, dropped 0; **replay IDENTICAL row for row, in order (863 rows; 23 of 23 committed and locks)** |
| identification, 6 min, presses from 20 s (rig_identify_20261015_133513) | exit 0; 18 decisions, schema v3, mps; adaptation after each decision, none waited; memory 3.4 to 3.8 GB/h after warm-up; **replay IDENTICAL (18 of 18, differences 0.0)**; decisions 1 to 17 written 0.56 to 0.63 s after t0 + 4.0 s (within the cap); decision 18 is an artefact of the test: its press fell at the run's end (360 s), so it was decided at the closing poll with no walk after it |
| identification, presses from 10 s (rig_identify_20261015_134227) | **crashed at +175 s**: RX3 stopped sending frames at +114 s (13:44:20) with its port open and no read error, and streamed normally again at 13:46; a window then held no RX3 frame and the extraction raised IndexError; the replay crashes identically, and so does the code before the fix (checked in a worktree of 8200fca3): an existing weakness, a silent receiver crashes identification |
| identification, presses from 10 s, again (rig_identify_20261015_134654) | exit 0, no exception; 18 decisions, schema v3, mps; adaptation after each decision, none waited; memory about 2.1 GB/h after 2 min; **replay IDENTICAL (18 of 18, differences 0.0)**; decision clock: 18 of 18 before the cap (median 0.655 s, max 0.911 s after t0 + 4.0 s); **wall clock: 17 of 18 written within the cap (median 0.598 s); decision 14 written 4.505 s after t0 + 4.0 s** |

**Decision 14:** the app's loop fell about 3.6 s behind real time around 13:51:29 and caught up; no receiver paused (the
longest arrival gap 0.053 s), no report build ran, macOS logged no memory pressure, the process ran at normal
priority. Cause not identified. Untested candidate: macOS App Nap throttling the rig's plot window while it sits
behind other windows (the 12 Oct confirmation drew off screen; Uzayr's walkthrough would have the window in front).

**Where H4 stands:** tracking is perfect on every check. Identification now replays identically and refuses nothing
wrongly; over the two clean runs, 34 of 35 real decisions were written within the cap (decision 14 the exception).
Open for Uzayr: (1) decision 14's stall (a test with the window in front, or the rig asking macOS not to App-Nap it,
then a longer timing run); (2) a guard for a receiver going silent (report it and skip the walk, not crash); (3)
tracking's late frames (the screen draws in the press's thread: a separate screen thread or a cheaper press).

**Note added after the fix job:** Uzayr said (about 13:57) that around then he may have clicked onto his external monitor
to work on the report, which would have put the rig's window behind others; that fits the App Nap candidate for
decision 14's stall (a hidden window throttled by macOS), still untested.

## The silent-receiver guard and the walkthrough's UI changes (Queue 19; 14:03 to 15:59)

Uzayr's word after his UI walkthrough: "you can create the silent reciever guard and test it"; "put a status bar in
the terminal and make it known the space bar must be clicked there"; "fix where it says casual exit". Built in a
separate git worktree while he walked through, so his runs imported unchanged code. No model, weight, threshold,
display, decode or decision rule changed.

**The code** (ced6bd4f, then f1d1d780 after the board test):
- Identification: a walk whose window lacks a receiver (fewer than two frames, or a gap over 1 s inside it or at
  either end) raises `SilentReceiver` in the extraction worker, before the extraction that crashed at 13:44 (H4). The
  app prints that the walk could not be identified and why, lists it in `summary.json`
  (`skipped_walks_silent_receiver`) and carries on. The walk never joins the adaptation pool, so the engine continues
  as if it was never pressed (a synthetic 25 s gap with and without those presses: 16 of 16 later decisions
  identical, differences 0.0). f1d1d780: the window is checked only up to the newest frame of any receiver, and a
  walk with under 1 s of data because the data ended is reported as `DataEnded` ("the data ended 0.1 s into its
  window"), not as a silent receiver.
- Tracking: the consumer prints "TRACKING: RXn is silent ..." and "... is sending again", keeps each outage, and
  `summary.json` lists the outages and the walks overlapping one. Printed only; no decision reads it.
- Both apps: silent means more than 1 s behind the newest receiver, in data time (`rig.silent_receivers`), so a
  stalled loop (3.6 s at decision 14) is no false alarm; every receiver is called silent once nothing arrived for 5 s.
- Start-up: numbered steps with their times ([1/4] pre-flight, [2/4] the model, [3/4] the boards by MAC with the
  mapping, [4/4] the window), then a READY banner: click on THIS Terminal window, the keys are read here, not in the
  plot window. The window titles say the same. The tracking label "committed at the causal exit" now reads
  "committed line (the walk has ended)".

**Offline tests** (outputs in `guard/`; tracking through `guard/track_guard_consumer.py`: the real `TrackingConsumer`,
one record per loop, the clock following the data, a 3.6 s stall at +60 s):

| test | result |
|---|---|
| tracking, the 13:26 board run, no gap | 23 of 23 committed lines identical to the live run; no message (no false alarm through the stall) |
| tracking, the same with RX3's frames removed from +100 to +125 s | no crash; "RX3 is silent" at +100.97 s and "sending again" at +125.01 s; walks 7, 8 and 9 listed as overlapping the outage; 21 of 23 committed lines identical, the two that change (walks 8 and 9, A_fwd and E_col1 against E_row5) are both listed |
| identification, the 13:46 board run (healthy) | 18 of 18 identical, differences 0.0, nothing skipped |
| identification, the 13:42 board run (RX3 died at +114 s) | no crash; the 6 walks before the outage identical (0.0); the 3 after it skipped, each with its reason. The live run before the guard decided 2 of those 3 on stale RX3 data, then crashed |
| identification, the 13:35 board run | 17 of 17 identical (0.0); its last press came after every receiver's last frame (its window holds no data) and is now skipped as "the data ended"; the old code had decided it on no window data (H4's "decision 18" artefact) |

**The board test** (Uzayr at the desk, 15:03, `rig_identify_20261015_150308`, ced6bd4f; presses injected every 20 s;
he unplugged RX3's USB after about 3 decisions and plugged it back about 20 s later):
- No crash. "RX3 is silent" printed once; the 4 walks before were decided; the 7 walks after were skipped, each
  with its message; device mps.
- RX3 stayed silent after it was plugged back (1,404 read errors on its old port): the capture does not reopen a port
  that disappeared (pipeline/io, behaviour before today too). Exit code 1 is the capture's own gate failing RX3
  (59.4 packets/s against 146), as it should.
- The last press, 0.1 s before the 4-minute stop, was reported live as "RX1 was silent for 3.9 s" (wrong: the run
  had ended). Fixed in f1d1d780; the replay through the fixed code gives 4 of 4 decisions identical to the live run
  (differences 0.0) and the same 8 skips, the last now "the data ended 0.1 s into its window".
- Live tests after each change: 49 passed, 1 skipped.

**Found on the way, open for Uzayr:**
1. The two tracking runs of his walkthrough (14:09 and 14:15) kept only the capture (`.bin` and `_run.json`): no
   `keys.json`, `log.jsonl`, `gt.json` or `summary.json`. The capture puts the default Ctrl+C and hang-up handling
   back as soon as it stops, so a second Ctrl+C, or a closed Terminal window, while the run writes its records kills
   it before they are written. Proposed fix (not made): ignore Ctrl+C and hang-up from the capture's stop until the
   records are written, with a printed "saving the records" line.
2. A receiver that is unplugged and plugged back stays silent until the next start (above). Reopening the port would
   be a change in pipeline/io.
