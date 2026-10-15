# QUEUE_PAR: parallel window extraction in the v5 live app (Uzayr's go, 12 Oct)

Read this file first on every turn. Development evaluation, all data seen. Session: Third overall. Earlier jobs: ../QUEUE_V5.md,
../latency/QUEUE_LAT.md; their reports are not edited.

**Uzayr's go (in this chat, received at or before 12 Oct 2026 08:49:05 SAST), as given:** "wire parallel window extraction into the v5 live app using
worker processes. Timing only, every decision identical. Ask the Mastermind for the slot and keep caffeinate on for the whole job.
1. Build: a small pool of worker processes for the three-window extraction. No threads, ever. Create the pool once, at app start,
and keep it warm, not one per decision. Each worker sets the same one-thread and engine settings the serial path uses (the shared
setting that broke threads included), with BLAS threads at 1. Workers never touch the GPU. Call the engine's own extraction code,
and leave engine.py unchanged if you can. If engine.py has to change, make the change, then re-run all 26 harness replays as
before and report them. Add a switch to fall back to serial extraction (for example --extract-workers 0) and document it.
2. Exactness, before any timing run: extract every window of every B2 walk with the pool and serially: all three windows must be
bitwise identical on every walk. Run the same checks as yesterday's ship: the live app's decisions must equal the v5 replays on
every walk, with the ensemble values within yesterday's tolerances. If anything differs, stop, revert to serial and report.
3. Confirmation run, set up exactly as yesterday (B2 at 1x through the real serial parser; loso_B2_v5, --room B, mps, one thread,
nice 0, in-app MPS cache release on, to the end of the stream). Pass: every decision before its cap (t0 + 5.30 s), the stream's
lag at a press at most 0.5 s, and memory flat. Report per press: the decision delay after t0 + 4.0 s (median, p95, p99, max); the
processing time after the last data; the extraction, model and adaptation times; the lag; memory over time for each worker and
in total; how many of the 299 walks came in within the limit. 4. Ship rule: keep the change only if exactness holds, the run
passes, the median improves and memory stays flat. Otherwise revert to serial: today's figures (1.05 s, 298 of 299) stand. Either
way, report honestly, including whether processing after the last data meets the 0.5 s target or misses it. 5. Close: a new
report, reports/identification/2026-10-12_parallel-extraction.md, its Editor list giving the old and new value, with the source,
for Section 3.6, Figure 3.4, Section 4.5, the latency table and the compliance row; a dated note in runs/identify/engine/PLAN.md;
commit, QUIET, the Mastermind told. Rules: no change to any model, weight or accuracy figure; no new looks at test outputs beyond
the identity checks; never touch the report repo."

| step | state | next |
|---|---|---|
| 0 set-up | this file; slot and whole-job caffeinate asked of the Mastermind (08:48) | its reply |
| 1 build | DONE (5e4193a6; engine.py unchanged) | identify_engine.py: a warm process pool, the extractors' extract_v4 hooked per instance, --extract-workers (0 = serial) |
| 2 exactness | PASSED: 2a 897 of 897 windows; 2b bit-identical on all 299, replay within tolerance | all 299 B2 walks x 3 windows pool vs serial; the live app on cpu with workers vs last night's serial run (bit for bit) and the replay |
| 3 confirmation run | DONE 09:20:20 to 10:25:40: 299 of 299 within the cap, median 0.731 s; memory rule (a) FAILS | as yesterday's; pass rules fixed here before it starts |
| 4 ship rule | REVERTED to serial (5b152dab; identify_engine.py exactly as at 7de0b32b) | keep only if exactness, pass, median better, memory flat; else revert to serial |
| 5 close | DONE: the report, PLAN note, QUIET, the Mastermind told | the report, PLAN note, QUIET, the Mastermind told |

- **Noted to Uzayr at the start:** both of yesterday's runs failed "memory flat" on the GPU side (about 1.9 GB/h), which parallel
  extraction does not touch; the ship rule is applied as written unless he says otherwise before the ship decision.
- **12 Oct 2026 09:08:09 SAST: the memory rule (Uzayr, in this chat): (a), as he defined it; the confirmation run's pass rules, FIXED BEFORE IT STARTS
  (parallel/rules.json).** PASS needs all of: (i) every one of the 299 decisions timed and before its cap (t0 + 5.30 s); (ii) the
  stream's lag at every press at most 0.5 s; (iii) memory, rule (a): (1) the TOTAL (main process plus the three workers; the
  resource tracker excluded, its size reported) grows no faster than serial's measured 1.875 GB/h with 10 % for noise, so at most
  2.0625 GB/h, least-squares slope from minute 10 to the end; (2) EACH WORKER flat after warm-up: no sample after minute 10 more
  than 10 % above its size at minute 10 (a growing worker leaks on every extraction and fails); (3) NO SWAP AND NO PRESSURE: the
  swap in use (vm.swapusage; 5.7 GB already in use from before, at 09:07) and the Swapouts counter (vm_stat) do not grow from the
  run's start to its end, and kern.memorystatus_vm_pressure_level is 1 (normal) at every 30 s sample. Reported: the workers' fixed
  size (at minute 10), the total and per-worker slopes, the peak total. Exactness (stop rule): argmax 299 of 299, ensemble equal
  to the replay exactly (0). SHIP RULE (Uzayr): keep the change only if exactness holds, the run passes (i to iii), and the median
  delay improves on serial's 1.047 s (rig_timing_confirm_lat.json); otherwise revert to serial and 1.05 s, 298 of 299 stand.
  Step 2a PASSED (09:00:59): 299 walks, 897 of 897 windows bitwise identical, pool against serial (extract_exact.json).
- **12 Oct 2026 09:20:20 SAST: step 2b PASSED; the confirmation run starts.** The live app with the pool (three workers, cpu, full speed, nice 10,
  09:01:25 to 09:19:07): bit-identical on all 299 B2 decisions in every field to last night's serial run of the same app (7de0b32b,
  latency/cpu_exact/after.*, copied as parallel/cpu_exact/before.*); against the replay, argmax 299 of 299, 8.06e-06 on the 287
  decided during the stream (bound 8.1e-06), 9.47e-06 on the 12 closing-poll ones (as before) (parallel/cpu_exact.json); 1061 s
  against 1477 s serial. Harness smoke (two recordings at 20x, cpu, scratch): worker times recorded per window. The confirmation
  run: parallel/run_confirm_par.sh confirm_par 0 70 iv5_rig confirm --device mps --tag confirm_par (the shipped app, three workers).
- **12 Oct 2026 10:28:04 SAST: the confirmation run, the decision, the revert and the report.** 09:20:20 to 10:25:40 (65.2 min, rc 0, not killed;
  main and three workers at nice 0, alone). Exact: 299 of 299, difference 0. Within the cap 299 of 299; delay after t0 + 4.0 s
  median 0.731, p95 0.795, p99 0.866, max 1.125 s (serial 1.047 / 1.118 / 1.150 / 1.315); lag at most 0.01 s. Processing after the
  last data median 0.402, max 0.825 s: 293 of 299 within the 0.5 s target. Memory, rule (a): total slope 1.788 GB/h (holds, at
  most 2.0625); workers flat by trend (about 1 MB/h) but two above their 10 % band on 4 and 1 of 92 samples (fails as fixed);
  no new swap, but macOS pressure level 2 on 4 samples (09:57:47 to 09:59:35, free 50 to 53 %; fails). decide.py (the rules
  fixed before the run): REVERTED to serial. The pool commit reverted (5b152dab): identify_engine.py exactly as at 7de0b32b, the
  serial app confirmed on 11 Oct; 1.05 s and 298 of 299 stand. Report: reports/identification/2026-10-12_parallel-extraction.md.
- **12 Oct 2026 10:37:32 SAST: Uzayr's second go: re-adopt parallel extraction (d5cd118b, the revert of 5b152dab; identify_engine.py as at 5e4193a6)
  and ONE fresh confirmation run under a memory rule REDEFINED AFTER THE FIRST RUN'S RESULT, fixed here and in parallel/rules2.json
  before the run (Mastermind's slot 10:33).** His reasons, recorded in the report: the first run's worker band failures were noise
  around a flat trend (about 1 MB/h), and the pressure warning coincided with about 11 GB of other applications and 50 % free.
  The rule: (1) the total (main plus the three workers) grows at most 2.0625 GB/h (1.875 + 10 %), slope from minute 10; (2)
  workers by trend: each worker's slope from minute 10 at most 10 MB/h, and no worker above 150 MB at any sample; (3) no swap
  growth (the swap in use never above its start value, Swapouts unchanged), pressure never critical (level 4), and level 2 only
  at samples with free memory at or above 30 %. Ship rule: all three memory conditions, every decision within its cap, lag at a
  press at most 0.5 s, and the median below serial's 1.0468 s; otherwise revert to serial and STOP (no further redefinition).
  Exactness: the GPU decisions equal the replay, 299 of 299 (difference 0); this morning's window and cpu evidence stands
  (nothing changed but the revert). Before the run: Uzayr closes every other VS Code window and heavy app, this window staying
  open (it hosts the session; his choice); every running process logged at the start and the end.
- **12 Oct 2026 11:48:30 SAST: the second confirmation run and the decision: KEPT.** 10:41:12 to 11:46:40 (65.2 min, rc 0, not killed; main and three
  workers at nice 0, alone but for this VS Code window and the idle mysqld; processes logged at the start and the end). Exact: 299
  of 299, difference 0. 299 of 299 within the cap; delay median 0.714, p95 0.787, p99 0.805, max 0.813 s; lag at most 0.01 s;
  processing after the last data median 0.387, max 0.484 s (287 of the 287 decided during the stream within 0.5 s; 299 of 299
  counting the closing ones). Memory, the redefined rule: total slope 1.9946 GB/h (limit 2.0625, a margin of 0.07), peak 4.381
  GB; workers fixed 78, 88 and 79 MB at minute 10, slopes 1.62, -1.08 and 1.73 MB/h, largest 92 MB; swap in use 1163 MB
  throughout, Swapouts unchanged, pressure level 1 at every sample, free at least 77 %. Median 0.714 below 1.0468. decide2.py:
  KEPT; parallel extraction ships (HEAD's identify_engine.py as at 5e4193a6). The report updated with the second run, the
  redefinition section and the Editor list from this run's figures; the PLAN note added.

