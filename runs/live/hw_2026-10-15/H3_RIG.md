# H3 working notes (15 Oct 2026)

## Fix 1: the key reader's cbreak mode (10:06)

pipeline/live/rig.py run() started KeyReader with .start() and never entered it, so the terminal stayed line-buffered.
Test (kr_parent.py drives kr_child.py in a pseudo-terminal, writing one SPACE and no Enter):
- KeyReader via start() (the rig before the fix): GOT None (no key within 2 s);
- KeyReader as a context manager (cbreak): GOT ' '.

Fix: run() enters KeyReader as a context manager. When stdin is not a terminal the reader does not start (before, its
thread spun on EOF). Live tests after the fix: 49 passed, 1 skipped (the TDR_SLOW test), 10:06:58 to 10:10:36
(H3_tests_fix1.txt).

## Fix 2: the board rig on the CPU (10:13)

final_model.rig_inner (the board rig, python3 -m pipeline.live rig) never called pd_clean.force_cpu(); gate_inner and
the streamed run (stream_source.stream_inner) do. On this Mac nets.device() gives mps without it and cpu after it
(checked 10:06), so the board rig ran the tracker's networks on the GPU, unlike every replay, the streamed run and the
shipped setting (CPU), the 14 Oct device lesson exactly. Fix: rig_inner calls force_cpu() first. Live tests after it:
49 passed, 1 skipped in 218.12s (0:03:38) (start 10:11:20 to end 10:14:59 rc=0).

## The recording (ba6beee1, 5d0aa41d)

rig.run passes run_capture's own writer (out_dir, timestamped_subdir off, prefix <stem>_: one .bin per receiver and
<stem>_run.json, as the sessions were recorded) into runs/live/hw_2026-10-15/rig_<mode>_<YYYYmmdd_HHMMSS>/, on by
default, and keeps every key as the app received it (KeyTee in front of the consumer's key queue) in
<stem>.keys.json, written in a finally so a refused run is kept. The tracking rig (final_model.rig_inner) logs its
outputs with app_replay.Logger (it wraps the display's drawing and the session's decision callback, calls each
original unchanged and only appends rows: the streamed run's own logger) into <stem>.log.jsonl, and writes
<stem>.gt.json: the presses as the app got them, the mode, and the baseline as "baseline" and "baseline_capture"
(the field windows.baseline_dir_for reads; added in 5d0aa41d after the first test replay refused without it). The
identification rig passes its mode, stem and settings (model, room, device, extraction, its decision file). Live
tests after each commit: 49 passed, 1 skipped.

## The proof on a stream (h3_onoff.py, h3_chain.sh; B2 PA3's recording, 5.85 min, at 1x)

The recording was streamed through the streamed rig's own serial stand-in (every frame written back as a CSI_DATA
row, read by run_capture's SerialReader and parse_line) into rig.run itself, the session built as
stream_source.stream_inner builds it (cell f05_B2, shipped profile clean_1s_r0, CPU), the 20 recorded start presses
injected at their recorded times.

| run | recording | rows | committed | locks | device |
|---|---|---|---|---|---|
| on (10:23 to 10:29) | on | 1,369 | 20 | 20 | cpu |
| off (10:29 to 10:36) | off | 1,369 | 20 | 20 | cpu |
| on2 (10:47 to 10:53) | on | 1,370 | 20 | 20 | cpu |
| off2 (10:53 to 10:59) | off | 1,365 | 20 | 20 | cpu |

- **A recorded run replays exactly:** on2's own capture through the harness (app_replay.replay_inner, causal clock)
  gives 1,370 rows against the stream's 1,370, **IDENTICAL** row for row (wall-clock fields aside), 11:02. (The first
  attempt's replay refused for want of baseline_capture, which 5d0aa41d added.)
- **Two streamed runs never agree in absolute time** (each stamps packets and presses on its own wall clock: attempt 1's
  absolute comparison, 1,368 rows differing, was the wrong test), so runs are compared walk by walk, relative to each
  press (compare_rel, as stream_source.compare):

| pair | recording | committed equal | locks equal | switches | dots identical | dot deviation median / p99 / max (m) |
|---|---|---|---|---|---|---|
| on2 vs off2 | on vs off | 20 of 20 | 18 of 20 | 4 vs 4, 2 shared | 521 of 1,301 | 0.0001 / 3.81 / 4.5 |
| on vs off2 | on vs off | 20 of 20 | 17 of 20 | 3 vs 4, 2 shared | 531 of 1,301 | 0.0001 / 1.82 / 2.40 |
| **on vs on2** | **on vs on** | **20 of 20** | **19 of 20** | **3 vs 4, 2 shared** | **551 of 1,306** | **0.0001 / 3.81 / 4.5** |

- **Verdict:** recording changes nothing beyond the run-to-run variation of two wall-clock streams: two runs that BOTH
  record differ as much as a recording run and a non-recording one (locks 19 of 20, other switches, dots up to 4.5 m
  apart on those walks). Committed lines are equal in every pair. The variation is the known wall-clock effect: the
  lock is the line first drawn at press + 2.0 s and a switch is decided on the frames drawn so far, both read from
  the windows that exist on the wall clock when the screen asks, so reader jitter can tip a borderline walk (the
  30 Sep stream's six borderline locks; more switches since the radius was removed, 14 Oct). Every recorded run
  replays row for row, which is the proof that live equals replay for a recorded session.
