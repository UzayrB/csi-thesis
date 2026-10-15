# QUEUE_LAT: engine v5's live latency, timing only (Uzayr's go, 11 Oct)

Read this file first on every turn. Development evaluation, all data seen. Session: Third overall. The previous job (engine v5's
ship and close) is in ../QUEUE_V5.md; its report reports/identification/2026-10-11_engine-v5.md is not edited.

**Uzayr's go, quoted (in this chat, received 11 Oct 2026 18:08:52 SAST):** "reduce engine v5's live latency, timing only. 1. Profile the live
app's decision path on B2 (where the ~0.53 s 'rest of the poll path' goes). 2. Change only pipeline/live/identify_engine.py (and
the iv5_rig harness if needed). engine.py, the models, weights and replays stay untouched; v4 runs exactly as before.
3. Exactness, as today: live app before vs after bit-identical on all 299 B2 decisions (cpu), and 299 of 299 equal to
loso_B2_v5's replay with difference 0 on mps. Any difference: stop and tell the Mastermind. 4. A new confirmation run, same
setup as today's (B2's whole day at 1x, mps, nice 0, every decision timed, alone on the machine), pass rules fixed before it.
Report it whatever it shows. 5. Write it up as a new report (don't edit today's), with an Editor list of the timing figures
that change. Ask the Mastermind for the slot before any heavy step."

| step | state | next action |
|---|---|---|
| 0 set-up | DONE (slot granted 18:09 for steps 1 to 4's heavy runs) | |
| 1 profile | DONE 18:10 to 18:21 (profile_mps.json) | |
| 2 change | DONE (7de0b32b): the screen redrawn on change; the CNNs warmed before the first press | |
| 3 exactness | PASSED: cpu (18:25 to 18:50), v4, mps (299 of 299, difference 0) | cpu: before (d63c2df7's code) and after bit-identical on all 299; mps: in the confirmation run, 299 of 299, difference 0 |
| 4 confirmation run | DONE 18:51:53 to 19:57:25: FAIL (298 of 299 within the cap; memory 1.875 GB/h), reported, flagged | |
| 5 report | DONE: reports/identification/2026-10-11_engine-v5-latency.md; to the Mastermind for review | |

- **11 Oct 2026 18:25:56 SAST: the profile and the change.** Profile (iv5_rig profile, B2's first 4 recordings at 1x, mps, nice 0, alone,
  18:10:01 to 18:21:07; the timers in the harness process only; 47 decisions; latency/profile_mps.json): delay after t0 + 4.0 s
  median 1.098 s. The decision waits on the engine's three window extractions IN SERIES (0.29 s each wall clock; their sum median
  0.865 s, max 1.337 s: the 0 s window's starts about t0 + 4.03, the 0.15 s and 0.30 s windows' queue behind it) and the
  classification (median 0.126 s; 0.299 s on the first walk, the device's first call). The app's share: the screen, redrawn every
  0.1 s of stream time whatever changed, 0.112 s of redraws in the 0.6 s before each decision and 131 s of the run's 200 s of tick
  time; flush, keys, line, cache release, combination: under 0.01 s. The engine's serial extraction cannot change (engine.py
  untouched). The change (7de0b32b, identify_engine.py only, v5 only): (A) the screen redrawn only when what it shows changes (the
  last decision, walks seen, a walk in progress, the score, the stream), its window's events pumped every 0.1 s; (B) each CNN run
  once on zero windows (10 to 12 of 28 x 34) before the first press, eval and no gradients (pass_logp), output discarded. Smoke
  (two recordings at 20x, cpu, scratch): 20 decisions, argmax equal to the replay, 41 redraws. Expected: about 0.1 s off the
  median and about 0.17 s off the first walk; the serial extraction stays.
  Step 2 (cpu exactness): before = 445d42c1's pipeline/ (the code before the change; its pipeline equals dad9acab's) in a scratch
  tree, after = 7de0b32b, side by side, nice 10 (latency/run_cpu_exact.sh, outputs latency/cpu_exact/ and latency/cpu_exact.json).
- **11 Oct 2026 18:28:30 SAST: the new confirmation run's pass rules, FIXED BEFORE IT STARTS (as option (c)'s run's).** Setup: as
  run_confirm.sh (latency/run_confirm_lat.sh, a copy with its own output names; iv5_rig confirm --tag confirm_lat, the shipped app,
  no timers): B2 through the real serial parser, every recording at 1x, loso_B2_v5, room B, mps, OMP_NUM_THREADS 1, nice 0, MPS
  0.7/0.5, alone; killed above 12 GB or below 30 % free. PASS needs all three: (1) every one of the 299 decisions timed and before
  its cap (t0 + 5.30 s); (2) the stream's lag at every press at most 0.5 s; (3) memory flat: the footprint sampled every 30 s, its
  least-squares slope from minute 10 to the end at most 0.5 GB/h, never above 12 GB. Exactness (stop rule): argmax 299 of 299 and
  the ensemble equal to loso_B2_v5's replay exactly (0). Reported against option (c)'s run walk by walk (descriptive, no new rule).
  The report is written whatever it shows (Uzayr). It starts only after step 2 has passed.
- **11 Oct 2026 18:51:53 SAST: step 2 PASSED.** cpu, before (445d42c1's pipeline/, scratch tree; its run loaded that tree's identify_engine.py)
  and after (7de0b32b), side by side, 18:25:56 to 18:50:51: bit-identical on all 299 B2 decisions in every field; after against
  the replay: argmax 299 of 299, 8.06e-06 on the 287 decided during the stream, 9.47e-06 on the 12 closing-poll ones (as before;
  latency/cpu_exact.json). v4: the live app before and after on loso_B2_v4 (B2's first recording, 10 decisions) bit-identical
  (latency/live_before_after_v4.json). The confirmation run starts now, alone, under the rules fixed above.
- **11 Oct 2026 19:58:33 SAST: the new confirmation run and the report.** 18:51:53 to 19:57:25 (65.3 min, rc 0, not killed). Exactness PASSED:
  argmax 299 of 299, difference 0 against loso_B2_v5's replay. Timing FAILS on one walk: 298 of 299 within the cap (option (c)'s
  run: 297); delay after t0 + 4.0 s median 1.047 (1.083), p95 1.118 (1.189), p99 1.150 (1.261), max 1.315 (1.453); the late
  walk is walk 26 (slow block), 15.3 ms after its cap (option (c)'s run: 1.114 s on it), its extra time in the queue before
  its last window ("the rest" 0.731 s). Lag at a press max 0.012 s (0.077). Walk by walk: median -0.029 s, faster on 233 of 299;
  the first walk 1.301 -> 1.033 s (its model 0.316 -> 0.147 s). Memory FAILS as before: slope 1.875 GB/h, largest 3.76 GB.
  Nothing changed after the run; reported and flagged for Uzayr. Report: reports/identification/2026-10-11_engine-v5-latency.md
  (lat_report.py), with the Editor list of the timing figures that change; the earlier report not edited.

