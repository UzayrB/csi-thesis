# Mastermind: live application on the boards, then hand over to Uzayr (15 Oct 2026)

(Uzayr's prompt `prompt_mastermind_live_hardware_test.md`, pasted into the Mastermind's chat on 15 Oct 2026 about 09:50,
with his words: "you can do this one for me, i am going to take a nap now so you have the go on everything do not wait up
and ensure the prompt is completed fully ... do not let agent do this you must". Copied verbatim below.)

From Uzayr. The TX and RX1, RX2 and RX3 are plugged into this Mac. Prove that the live application works on the boards exactly as it does when B2 is streamed in. Fix only what stops it working. When everything passes, send Uzayr **one** message saying it is ready, then **stop** and ask him to go through the flow and UI himself. Do not change the UI before he has done that.

## KEEP-ALIVE

- Keep a queue in `runs/live/hw_2026-10-15/QUEUE.md`, with items H0 to H6 marked PENDING, RUNNING, DONE or BLOCKED, each with its next action and ETA. Read it first on every turn.
- Do not stop or ask permission between items. The only exceptions are a BLOCKED hardware item (see H2) and the final hand-over (H6).
- Run long jobs in the background, with their verification chained after them. Run `caffeinate -dimsu` for the whole job.
- Check in every 15 minutes in `runs/live/hw_2026-10-15/CHECKINS.md`, and run a shell heartbeat watchdog.
- Run timed work (H4, H5) only on a quiet machine. Before each timed run, check that nothing heavy is running, including other sessions' LaTeX builds. Record the 1-minute load average throughout.

## Rules

- **Do not touch** any model, weight, threshold, display profile, decode or decision code. No retraining. No report edits.
- **Allowed code changes,** only if needed:
  1. the live rig recording what it receives (H3);
  2. a **test-only** key injector for the board smoke runs (H4), off by default.
  Commit each with its reason. Run the live tests after each one.
- Use `/opt/anaconda3/bin/python3`, `OMP_NUM_THREADS=1` and `PYTHONPATH=.`. Write everything under `runs/live/hw_2026-10-15/` and never under `data/`.
- The shipped settings must stay exactly as they are. Record them in H0:
  - tracking: `MODEL_CELLS["final"]` = `f05_A3` / `f05_B2`, `DISPLAY_PROFILE = "clean_1s_r0"`, semi mode (one SPACE per walk), CPU;
  - identification: `deploy_all5_v5`, engine v5, staged extraction with 4 workers, `--device mps`.

## The queue

**H0. State.**
- Record git HEAD and the shipped settings above.
- Check that nothing heavy is running.
- Confirm `python3 -m pipeline.live preflight` is ALL ok, without a baseline for now.

**H1. Offline proofs.**
- Run the live test set that STATE.md calls "the live tests". Every one must pass.
- Diff `pipeline/identify/engine.py`, `pipeline/live/identify_engine.py`, `idv2_core.py`, `idw_core.py` and `idz_core.py` against the commit of `runs/identify/v5/rig_timing_confirm_staged.json` (12 Oct).
  - If any decision or extraction code changed, rerun that streamed confirmation: B2 through the real `SerialReader` and `parse_line`, 1x, mps. It must give 299 of 299 equal decisions and a maximum ensemble difference of 0.0.
  - If nothing changed, record that and skip the rerun.

**H2. The boards.**
- Find every `/dev/cu.usbserial-*` port and name it by station MAC with `pipeline.io.identify_board`, never by port order. Expect:
  - RX1 `68:09:47:4c:ef:b4`;
  - RX2 `20:50:0d:1a:28:74`;
  - RX3 `20:50:0d:30:5f:80`;
  - the transmitter detected.
- Capture 3 minutes with the project's own capture tool and record per receiver:
  - packets per second, which must be at least 146;
  - loss from the TX frame counter, which must be under 5%;
  - parse errors, which must be 0;
  - the config watch: channel 11, HT20.
- **If anything fails, mark H2 BLOCKED and message Uzayr at once** with what failed and what he should check (power, cable, port, firmware, channel). Do not continue to H4 until it passes.

**H3. The live rig must keep what it receives.**
- Check whether `pipeline.live.rig.run` (used by both tracking's `rig` and `identify_engine rig`) saves the raw packets and presses. Today it calls `run_capture` without a writer, so it saves neither.
- If it still does not save them, add recording through the **same capture writer** the sessions were recorded with, on by default, into `runs/live/hw_2026-10-15/rig_<mode>_<time>/`, with the presses in a sidecar. Add nothing to the decision path.
- Show that the app's outputs on a stream are unchanged with recording on and off (identical logs).
- Why this matters: every live session must then be replayable through the harness. That is the proof that live equals replay.

**H4. Smoke runs on the boards, no walker.**
- **Tracking:**
  - Take a fresh 60 s baseline with the capture tool. Uzayr should be out of the sensing area if he is in the room. If he is at the desk, record that the baseline is not a true empty room. For a smoke run that is acceptable.
  - Run `python3 -m pipeline.live rig --baseline <dir> --minutes 6` with the test-only injector pressing SPACE every 15 s after a 15 s idle start.
  - Record:
    - pre-flight ALL ok;
    - the refusal with fewer than 10 idle windows (start one run with an early press to show it refuses);
    - packets parsed and dropped;
    - per-window service (median and max);
    - draw lag and frames late (over 0.1 s and over 0.5 s);
    - redraws against ticks;
    - press service time;
    - no exception.
  - Then replay the recorded capture through the harness. The decisions and the log must be **identical row for row** to the live log. If they are not, find out why. If the cause is only wall-clock timing, report which rows moved and why, as the 30 Sep stream's six borderline locks did.
- **Identification:**
  - Run `python3 -m pipeline.live.identify_engine rig --mode identify --room new --minutes 6` (mps, staged) with the injector pressing every 20 s.
  - Record:
    - decisions written (schema v3);
    - every decision before its cap (t0 + 5.30 s);
    - decision delay after t0 + 4.0 s (median and max);
    - adaptation after each decision, and no walk waiting for it;
    - the memory slope.
  - Replay the recorded capture through the engine. The decisions must be identical: argmax equal and the largest ensemble difference 0.0 on mps.
- The answers on an empty room mean nothing. These runs prove the path, not accuracy.

**H5. Stream B2 with the shipped tracker.** This is the gap in the report: tracking was last streamed with its earlier heads and display (30 Sep and 1 Oct).
- Rerun `python3 -m pipeline.live rig --stream B2/<recording> --speed 1.0` for all six B2 recordings, with the shipped `clean_1s_r0`, on a quiet machine.
- Report against the fast replay:
  - packets parsed and dropped;
  - committed lines equal (of 120);
  - locks equal (of 120), with the reason for any that moved;
  - each re-replay of the stream's own capture, which must be identical row for row;
  - per-window service, draw lag, announcement after the walk's end (median and max), and press service.
- About one hour. These numbers go to the Editors later. Write them in `runs/live/hw_2026-10-15/REPORT.md` with PA codes, never names, in anything meant for the report.

**H6. Hand over, then stop.** Send Uzayr **one** message, at most one screen:
1. **READY**, or what is not ready.
2. A PASS/FAIL line for H1 to H5, with the key numbers.
3. Exactly how he runs his walkthrough:
   - the baseline command (room empty, under 2 hours before the first walk);
   - the tracking command, with RX2 at its tracking position (-0.5, 2.5);
   - the identification command, with RX2 beside the TX at (2.0, -0.5);
   - which window takes SPACE: `KeyReader` reads the **terminal** in cbreak mode, not the plot window;
   - the keys: SPACE, `n`, `a`/`t`, `q`;
   - the 10 s of standing still before the first tracking press;
   - where each session's recording and log land.
4. Anything he should know before he starts.

Then **stop** and ask him to go through the flow and the UI and tell you what he wants changed. Do not change the UI, the flow or any setting until he replies.
