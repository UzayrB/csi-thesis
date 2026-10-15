# Identification: parallel window extraction in the v5 live app (2026-10-12)

**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in view. Timing only: no model, weight, replay, decision or accuracy figure changes, and no new look at any test output beyond the identity checks. Uzayr's go (12 Oct, given in `runs/identify/v5/parallel/QUEUE_PAR.md`): extract the three windows of each walk in a warm pool of worker processes, prove every extraction and decision identical, run a confirmation run set up as before, and keep the change only if the ship rule holds. The first run failed its memory rule and the change was reverted; Uzayr then redefined the memory rule (section 4) before one fresh run, with no further redefinition. The earlier reports are not edited. Generated 12 Oct 2026 11:48:00 SAST from the result files by `runs/identify/v5/parallel/par_report.py`.

**Final ship decision (the second run): KEPT (parallel extraction ships; this run's figures).** Every condition of Uzayr's ship rule holds.

## 1. What was built (`pipeline/live/identify_engine.py` only; engine.py unchanged)

- **A warm pool of three worker processes** (`ExtractPool`), made once at app start and warmed (each worker imports the extraction modules and extracts one synthetic window), never one per decision. Spawned processes, numpy's and BLAS's threads at one (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, `NUMEXPR_NUM_THREADS` set before the pool is made). No threads anywhere. Workers import no torch and never use the GPU.
- **The engine's own extraction:** each window extractor's `extract_v4` is replaced, on the instance, by a dispatch. At the window's decision time the frames each receiver had by then are copied and sent to a worker, which runs the engine's own `Extractor.extract_v4` on them. Each worker is one thread, so the engine's scoped swap of `idmax_features.resolve_cadence` inside each extraction (the shared setting that broke threads in the feasibility test) applies exactly as in the serial path. The engine stores the pending result and the app fills it in just before the window is classified.
- **The fallback:** `--extract-workers 0` (on `rig` and `replay-identify`) keeps the serial extraction, unchanged; the default is three workers for an engine v5 model. A v4 model always extracts serially.
- **History:** built 5e4193a6; reverted 5b152dab after the first run; re-adopted d5cd118b (the revert of 5b152dab) for the second run.

## 2. Exactness

1. **Every window of every B2 walk, pool against serial** (`parallel/extract_exact.json`): 299 walks, 897 windows, the same frames fed to the engine's serial extractors and to the app's pool: 897 of 897 windows bitwise identical in every field (features, maps, path, speed and the rest; NaN in the same places) with equal decision times, 0 differences: **PASSED**. Extraction took 134.3 s in the pool against 294.4 s serially.
2. **The live app, as in yesterday's ship** (`parallel/cpu_exact.json`; B2 through the app and the real serial parser on cpu at full speed, nice 10): with the pool against last night's serial run of the same app (7de0b32b), bit-identical on all 299 decisions in every field (PASSED); against loso_B2_v5's replay, argmax 299 of 299, largest ensemble difference 8.06e-06 on the 287 decisions made during the stream (yesterday's bound 8.1e-06) and 9.47e-06 on the 12 closing-poll ones (as before): **PASSED**. This evidence stands for the second run: the code re-adopted for it is the same (identify_engine.py exactly as at 5e4193a6).
3. **mps, the first confirmation run against the replay:** argmax 299 of 299, largest ensemble difference 0 (required 0): **PASSED**.
4. **mps, the second confirmation run against the replay:** argmax 299 of 299, largest ensemble difference 0 (required 0): **PASSED**.

## 3. The first confirmation run (09:20, memory rule (a))

Set up as yesterday's (`parallel/run_confirm_par.sh confirm_par 0 70`, `iv5_rig confirm --tag confirm_par`: the shipped app, its default three workers): B2 through the real SerialReader and parse_line (fake port); every recording at 1x with the screen drawn (headless); loso_B2_v5, room B, mps, OMP_NUM_THREADS 1, nice 0 (the workers too), the in-app MPS cache release on, alone on the machine; 65.2 min, ended 2026-10-12 10:25:37. Every decision timed. Pass rules fixed before the run: every decision before its cap (t0 + 5.30 s); the stream's lag at every press at most 0.5 s; memory: no worse than serial (Uzayr's rule (a)): (1) the total (main process plus the three workers) grows no faster than 1.875 GB/h x 1.10 = 2.0625 GB/h, least-squares slope from minute 10 to the end; (2) each worker flat after warm-up: no sample after minute 10 more than 10 % above its size at minute 10; (3) no swap used and no memory pressure: the swap in use (vm.swapusage) and the Swapouts counter (vm_stat) do not grow from the run's start to its end, and kern.memorystatus_vm_pressure_level is 1 (normal) at every 30 s sample.

| per press (seconds after t0 + 4.0 s unless named) | last night's serial run (19:57) | this parallel run |
|---|---|---|
| decision delay, median / p95 / p99 / max | 1.047 / 1.118 / 1.150 / 1.315 | 0.731 / 0.795 / 0.866 / 1.125 |
| decisions within the cap (t0 + 5.30 s) | 298 of 299 | **299 of 299** |
| processing after the last data (decision delay minus the last window's packet wait), median / p95 / p99 / max | 0.718 / 0.784 / 0.812 / 0.980 | 0.402 / 0.462 / 0.550 / 0.825 |
| of it within the 0.5 s target | 12 of 299 | 293 of 299 |
| a window's extraction in its worker (s), median / p95 / p99 / max | (serial: about 0.29 per window, one after another; profile of 11 Oct) | 0.326 / 0.383 / 0.444 / 0.666 |
| a window's wait for a free worker (s), median / max | - | 0.023 / 0.095 |
| the decision path's wait for the workers (s), median / p95 / p99 / max | - | 0.251 / 0.328 / 0.375 / 0.411 |
| the classification of the three windows, median / p95 / p99 / max (the parallel run's model time minus the wait for the workers, which happens inside it) | 0.140 / 0.149 / 0.156 / 0.167 | 0.145 / 0.179 / 0.214 / 0.409 |
| the engine's model time as recorded (the parallel run's includes the wait above), median / max | 0.140 / 0.167 | 0.398 / 0.814 |
| the adaptation after the decision, median / p95 / p99 / max | 0.289 / 0.481 / 0.519 / 0.546 | 0.312 / 0.5 / 0.532 / 0.733 |
| the stream's lag at a press, median / largest | 0.005 / 0.012 | 0.005 / 0.01 |

Walk by walk: this run's delay minus the serial run's, median -0.316 s (p5 -0.410, p95 -0.249); faster on 298 of 299.

**No decision came after its cap.**

**The 0.5 s processing target** (the specification's compliance row: host processing from the last window's packets to the decision): median 0.402 s and at most 0.825 s, so it is met at the median and on 293 of 299 walks (281 of the 287 decided during the stream, the largest 0.825 s; the 12 decided at a recording's close count trivially). The decision delay is longer than this processing time because it is counted from t0 + 4.0 s and so also includes the wait for the last window, which ends at t0 + 4.30 s, and for its last packets (a median 0.33 s together). What remains of the processing is the last window's extraction, which cannot start before its packets, and the classification.

| minute | main (GB) | worker 1 (GB) | worker 2 (GB) | worker 3 (GB) | total (GB) | free (%) |
|---|---|---|---|---|---|---|
| 0 | 0.07 | - | - | - | 0.07 | 66 |
| 5 | 1.72 | 0.08 | 0.08 | 0.08 | 1.96 | 63 |
| 10 | 1.72 | 0.08 | 0.08 | 0.08 | 1.96 | 64 |
| 15 | 1.82 | 0.08 | 0.08 | 0.08 | 2.06 | 61 |
| 21 | 2.05 | 0.08 | 0.08 | 0.09 | 2.29 | 62 |
| 25 | 3.31 | 0.08 | 0.08 | 0.08 | 3.55 | 52 |
| 30 | 2.39 | 0.08 | 0.08 | 0.08 | 2.63 | 59 |
| 35 | 2.36 | 0.08 | 0.08 | 0.08 | 2.59 | 58 |
| 40 | 2.54 | 0.08 | 0.08 | 0.09 | 2.79 | 55 |
| 45 | 2.58 | 0.08 | 0.08 | 0.08 | 2.82 | 58 |
| 50 | 3.02 | 0.08 | 0.08 | 0.09 | 3.26 | 57 |
| 56 | 2.94 | 0.08 | 0.08 | 0.09 | 3.19 | 58 |
| 60 | 3.39 | 0.08 | 0.08 | 0.08 | 3.63 | 56 |
| 65 | 3.41 | 0.08 | 0.08 | 0.09 | 3.65 | 58 |

**Memory against rule (a)** (fixed before the run, `parallel/rules.json`):

1. **The total** (main plus the three workers): slope from minute 10 1.7878 GB per hour against at most 2.0625; peak 4.373 GB: **holds**.
2. **Each worker flat after warm-up:** worker 1 (pid 56319): fixed size 77 MB at minute 10, 4 of 92 later samples above its 10 % band (largest 91 MB), slope 0.7 MB per hour; worker 2 (pid 56320): fixed size 81 MB at minute 10, 1 of 92 later samples above its 10 % band (largest 93 MB), slope 1.0 MB per hour; worker 3 (pid 56324): fixed size 86 MB at minute 10, 0 of 92 later samples above its 10 % band (largest 90 MB), slope 1.4 MB per hour. No worker shows a trend (about 1 MB per hour, so no leak per extraction across 897 extractions), but two exceeded the 10 % band on single samples: **FAILS** as the rule was fixed.
3. **No swap, no pressure:** the swap in use went from 5728 to 5680 MB and the Swapouts counter did not move, but macOS reported pressure level 2 (warning) on 4 of 110 samples (09:57:47 (minute 37.5, free 50 %), 09:58:23 (minute 38.0, free 52 %), 09:58:59 (minute 38.6, free 52 %), 09:59:35 (minute 39.2, free 53 %)); free memory never fell below 50 %. Other applications held several GB at the time (seen after the run: Visual Studio Code's helpers about 11 GB, a virtualisation service 1.9 GB), but the rule allowed none: **FAILS**.

**The ship rule, condition by condition:**

- exactness: every window of every B2 walk identical pool against serial (897 of 897), the live app on cpu bit-identical to serial and within yesterday's tolerances of the replay, the run equal to the replay (299 of 299, difference 0): **holds**
- every decision before its cap: 299 of 299: **holds**
- the stream's lag at every press at most 0.5 s: largest 0.01 s: **holds**
- memory, rule (a): the total's slope from minute 10 1.7878 GB/h against at most 2.0625 (holds); each worker flat after minute 10 within 10 % (worker 1 (pid 56319): fixed 0.075 GB, largest after 0.089 GB, slope 0.0007 GB/h, GROWS; worker 2 (pid 56320): fixed 0.079 GB, largest after 0.091 GB, slope 0.001 GB/h, GROWS; worker 3 (pid 56324): fixed 0.084 GB, largest after 0.088 GB, slope 0.0014 GB/h, flat); swap in use 5728 to 5680 MB, Swapouts 2178600 to 2178600, pressure levels [1, 2] (FAILS); peak total 4.373 GB: **FAILS**
- the median delay better than serial's: 0.7310 s against 1.0468 s: **holds**

**Decision on this run: REVERTED to serial extraction.**

## 4. The memory rule, redefined after the first run

After the first run had failed its memory rule and the change had been reverted, Uzayr redefined the memory rule (12 Oct, in this chat) and asked for one fresh confirmation run under it, with no further redefinition. His reasons: the worker band failures were noise around a flat trend (each worker's slope about 1 MB per hour, with no leak per extraction across 897 extractions), and the pressure warning coincided with about 11 GB of other applications and 50 % free memory. The new rule judges the workers by their trend and allows the warning level only while at least 30 % of memory is free: (1) the total (main process plus the three workers) grows at most 1.875 x 1.10 = 2.0625 GB/h, least-squares slope from minute 10 to the end; (2) workers judged by trend: each worker's slope from minute 10 at most 10 MB/h, and no worker above 150 MB at any sample (MB = top's own figure, GB x 1024); (3) no swap growth (the swap in use never above its value at the run's start, and the Swapouts counter unchanged), memory pressure never critical (kern.memorystatus_vm_pressure_level never 4), and level 2 only at samples where free memory is at or above 30 %. It was fixed in `parallel/rules2.json` and QUEUE_PAR (commit 4af57630) at 2026-10-12 10:37:32, before the second run started (10:41:12); the first run's figures were seen before it was written, which the reader should weigh.

## 5. The second confirmation run (10:41, the redefined rule)

Set up as yesterday's (`parallel/run_confirm_par2.sh confirm_par2 0 70`, `iv5_rig confirm --tag confirm_par2`: the shipped app, its default three workers): B2 through the real SerialReader and parse_line (fake port); every recording at 1x with the screen drawn (headless); loso_B2_v5, room B, mps, OMP_NUM_THREADS 1, nice 0 (the workers too), the in-app MPS cache release on, alone on the machine; 65.2 min, ended 2026-10-12 11:46:29. Every decision timed. Pass rules fixed before the run: every decision before its cap (t0 + 5.30 s); the stream's lag at every press at most 0.5 s; memory: (1) the total (main process plus the three workers) grows at most 1.875 x 1.10 = 2.0625 GB/h, least-squares slope from minute 10 to the end; (2) workers judged by trend: each worker's slope from minute 10 at most 10 MB/h, and no worker above 150 MB at any sample (MB = top's own figure, GB x 1024); (3) no swap growth (the swap in use never above its value at the run's start, and the Swapouts counter unchanged), memory pressure never critical (kern.memorystatus_vm_pressure_level never 4), and level 2 only at samples where free memory is at or above 30 %.

| per press (seconds after t0 + 4.0 s unless named) | last night's serial run (19:57) | this parallel run |
|---|---|---|
| decision delay, median / p95 / p99 / max | 1.047 / 1.118 / 1.150 / 1.315 | 0.714 / 0.787 / 0.805 / 0.813 |
| decisions within the cap (t0 + 5.30 s) | 298 of 299 | **299 of 299** |
| processing after the last data (decision delay minus the last window's packet wait), median / p95 / p99 / max | 0.718 / 0.784 / 0.812 / 0.980 | 0.387 / 0.458 / 0.471 / 0.484 |
| of it within the 0.5 s target | 12 of 299 | 299 of 299 |
| a window's extraction in its worker (s), median / p95 / p99 / max | (serial: about 0.29 per window, one after another; profile of 11 Oct) | 0.306 / 0.374 / 0.397 / 0.439 |
| a window's wait for a free worker (s), median / max | - | 0.027 / 0.074 |
| the decision path's wait for the workers (s), median / p95 / p99 / max | - | 0.239 / 0.314 / 0.369 / 0.417 |
| the classification of the three windows, median / p95 / p99 / max (the parallel run's model time minus the wait for the workers, which happens inside it) | 0.140 / 0.149 / 0.156 / 0.167 | 0.139 / 0.161 / 0.163 / 0.167 |
| the engine's model time as recorded (the parallel run's includes the wait above), median / max | 0.140 / 0.167 | 0.380 / 0.561 |
| the adaptation after the decision, median / p95 / p99 / max | 0.289 / 0.481 / 0.519 / 0.546 | 0.255 / 0.458 / 0.481 / 0.506 |
| the stream's lag at a press, median / largest | 0.005 / 0.012 | 0.006 / 0.01 |

Walk by walk: this run's delay minus the serial run's, median -0.328 s (p5 -0.421, p95 -0.266); faster on 299 of 299.

**No decision came after its cap.**

**The 0.5 s processing target** (the specification's compliance row: host processing from the last window's packets to the decision): median 0.387 s and at most 0.484 s, so it is met at the median and on 299 of 299 walks (287 of the 287 decided during the stream, the largest 0.484 s; the 12 decided at a recording's close count trivially). The decision delay is longer than this processing time because it is counted from t0 + 4.0 s and so also includes the wait for the last window, which ends at t0 + 4.30 s, and for its last packets (a median 0.33 s together). What remains of the processing is the last window's extraction, which cannot start before its packets, and the classification.

| minute | main (GB) | worker 1 (GB) | worker 2 (GB) | worker 3 (GB) | total (GB) | free (%) |
|---|---|---|---|---|---|---|
| 0 | 0.03 | - | - | - | 0.03 | 81 |
| 5 | 1.69 | 0.08 | 0.09 | 0.08 | 1.93 | 82 |
| 10 | 1.68 | 0.08 | 0.09 | 0.08 | 1.92 | 83 |
| 15 | 1.79 | 0.08 | 0.09 | 0.08 | 2.03 | 82 |
| 20 | 2.01 | 0.08 | 0.09 | 0.08 | 2.25 | 82 |
| 25 | 2.08 | 0.08 | 0.09 | 0.08 | 2.32 | 81 |
| 30 | 2.39 | 0.08 | 0.09 | 0.08 | 2.64 | 81 |
| 35 | 2.43 | 0.08 | 0.09 | 0.08 | 2.67 | 83 |
| 40 | 2.67 | 0.08 | 0.09 | 0.08 | 2.92 | 84 |
| 45 | 2.67 | 0.08 | 0.09 | 0.08 | 2.91 | 83 |
| 51 | 3.11 | 0.08 | 0.09 | 0.08 | 3.35 | 83 |
| 55 | 2.94 | 0.08 | 0.09 | 0.08 | 3.20 | 84 |
| 60 | 3.39 | 0.08 | 0.09 | 0.09 | 3.64 | 84 |
| 65 | 3.39 | 0.08 | 0.09 | 0.08 | 3.63 | 82 |

**Memory against the redefined rule** (fixed before the run, `parallel/rules2.json`):

1. **The total** (main plus the three workers): slope from minute 10 1.9946 GB per hour against at most 2.0625; at minute 10 1.919 GB, peak 4.381 GB: **holds**.
2. **The workers by trend** (slope from minute 10 at most 10 MB per hour; never above 150 MB): worker 1 (pid 89799): fixed size 78.0 MB at minute 10, slope 1.62 MB per hour, largest 86.0 MB; worker 2 (pid 89800): fixed size 88.0 MB at minute 10, slope -1.08 MB per hour, largest 92.0 MB; worker 3 (pid 89801): fixed size 79.0 MB at minute 10, slope 1.73 MB per hour, largest 88.0 MB: **holds**.
3. **Swap and pressure:** the swap in use 1163 MB at the start, at most 1163 MB, 1163 MB at the end; the Swapouts counter 2206899 to 2206899; pressure levels seen [1]; free memory at least 77 %: **holds**.

**Running at the start** (`logs/confirm_par2_processes_start.txt`, every process logged; those above 200 MB): Code Helper (Renderer) 1126 MB; claude 436 MB; Code Helper (Renderer) 410 MB; Code 398 MB; claude 391 MB; server.bundle.js 325 MB; Code Helper (Plugin) 255 MB. Uzayr closed every other Visual Studio Code window and the Claude desktop app (its virtualisation service went with it); this Visual Studio Code window stayed open because it hosts the session (his choice); mysqld (a database server started by macOS, idle) stayed, as stopping it needs an administrator.

**The ship rule, condition by condition:**

- exactness on the GPU: 299 of 299, difference 0: **holds**
- every decision before its cap: 299 of 299: **holds**
- the stream's lag at every press at most 0.5 s: largest 0.01 s: **holds**
- memory (1), the total: slope from minute 10 1.9946 GB/h against at most 2.0625, peak 4.381 GB: **holds**
- memory (2), the workers by trend: worker 1 (pid 89799): fixed 78.0 MB at minute 10, slope 1.62 MB/h, largest 86.0 MB (holds); worker 2 (pid 89800): fixed 88.0 MB at minute 10, slope -1.08 MB/h, largest 92.0 MB (holds); worker 3 (pid 89801): fixed 79.0 MB at minute 10, slope 1.73 MB/h, largest 88.0 MB (holds): **holds**
- memory (3), swap and pressure: swap in use 1163 MB at the start, at most 1163, 1163 at the end; Swapouts 2206899 to 2206899; pressure levels [1]; free memory at least 77 %: **holds**
- the median delay below serial's 1.0468 s: 0.7143 s: **holds**

**Decision on this run: KEPT (parallel extraction ships; this run's figures).**

## 6. The Editor list (only after the Mastermind's review)

The change is kept with the second run's figures, so these change (old: last night's serial run; new: that parallel run). Every accuracy is unchanged. The 0.5 s processing target is stated as met at the median and on N of 299 walks, not as met outright.

| place | figure | old | new | source |
|---|---|---|---|---|
| Section 3.6 (Real-time application) | the decision after t0 + 4.0 s, median / at most; decisions within the cap | 1.05 / 1.32 s; 298 of 299, one miss of 0.015 s | 0.71 / 0.81 s; 299 of 299 | old `reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`; new `reports/identification/2026-10-12_parallel-extraction.md` Section 5; `runs/identify/v5/rig_timing_confirm_par2.json` |
| Figure 3.4 (`fig:id-engine`, Figures/tikz/id_engine.tex) | the output box: median / at most after t0 + 4.0 s | 1.05 / 1.32 s | 0.71 / 0.81 s | old `reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`; new `reports/identification/2026-10-12_parallel-extraction.md` Section 5; `runs/identify/v5/rig_timing_confirm_par2.json` |
| Section 4.5 | the classification of the three windows; the decision, median / at most; within the cap; the calibration after each decision | 0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 (miss 0.015 s); 0.29 / 0.55 s | 0.139 / 0.167 s; 0.71 / 0.81 s; 299 of 299; 0.26 / 0.51 s | old `reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`; new `reports/identification/2026-10-12_parallel-extraction.md` Section 5; `runs/identify/v5/rig_timing_confirm_par2.json` |
| The latency table (identification column) | computing per step; output against design time; final output; wall-clock delays | 0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 by t0 + 5.30 s; 0.29 / 0.55 s | 0.139 / 0.167 s; 0.71 / 0.81 s; 299 of 299 by t0 + 5.30 s; 0.26 / 0.51 s | old `reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`; new `reports/identification/2026-10-12_parallel-extraction.md` Section 5; `runs/identify/v5/rig_timing_confirm_par2.json` |
| The compliance row (Latency, at most 0.5 s) | from the last window's packets to the decision, median / at most; the 0.5 s target | 0.718 / 0.980 s; missed at the median, met on 12 of 299 walks (0 of the 287 decided during the stream, the largest 0.980 s; the 12 decided at a recording's close count trivially) (Met: Y / N) | 0.387 / 0.484 s; met at the median and on 299 of 299 walks (287 of the 287 decided during the stream, the largest 0.484 s; the 12 decided at a recording's close count trivially) (Met: Y / Y for this run, worded as met at the median and on the N of 299 walks given, not outright) | old `reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`; new `reports/identification/2026-10-12_parallel-extraction.md` Section 5; `runs/identify/v5/rig_timing_confirm_par2.json` |

Where the application is described, a sentence may be added that the three windows are extracted in parallel by three worker processes (the engine's own extraction, identical outputs), with `--extract-workers 0` as the serial fallback.

## 7. Files and commits

- Code: `pipeline/live/identify_engine.py` (`ExtractPool`, `PendingExtraction`, `--extract-workers`); `pipeline/identify/iv5_rig.py` (worker times per window, each worker's memory). engine.py unchanged.
- Records: `runs/identify/v5/parallel/` (QUEUE_PAR.md, extract_exact.py and .json, cpu_exact/ and cpu_exact.json, rules.json and rules2.json, decide.py and decide2.py, run_par_step.sh, run_confirm_par.sh, run_confirm_par2.sh, this generator); `runs/identify/v5/rig_timing_confirm_par.json` and `rig_timing_confirm_par2.json`, their per-walk files and jsonl; `logs/confirm_par*_memory.csv`, `_workers.csv`, `_system.csv`, and `logs/confirm_par2_processes_start.txt` and `_end.txt`.

Commits:

- a6b9140e 08:49:05 Parallel extraction in the v5 live app (Uzayr's go, 12 Oct): the queue, his go as given
- 5e4193a6 08:52:51 Live app, engine v5 parallel extraction (Uzayr's go, 12 Oct; timing only): ExtractPool, a warm pool of 3 spawned worker processes made at app start (num
- 9329185c 08:53:40 Parallel extraction: step 2a's check (every window of every B2 walk, pool against serial, bitwise) and the step launcher (main and workers guarded as on
- f367734a 08:55:08 iv5_rig: the parallel extraction's worker times per window (sent, start, end, wait), the processing after the last data, and each worker's memory judged
- 608266dd 09:01:25 Parallel extraction, step 2a PASSED: every window of every B2 walk (299 walks, 897 windows) bitwise identical, pool against serial (extraction 134 s aga
- cd8022b6 09:08:09 Parallel extraction: the confirmation run's pass rules fixed before it starts, the memory rule (a) as Uzayr defined it (total slope at most 1.875 GB/h +
- 6e253ba5 09:09:23 Parallel extraction: the confirmation run's launcher (one clock per sample; swap, Swapouts and pressure logged) and the ship rule's decision script (rul
- bd5e2f8d 09:20:20 Parallel extraction, step 2b PASSED: the live app with the pool bit-identical to the serial app on all 299 B2 decisions (cpu); against the replay within
- dec7365a 10:26:53 Parallel extraction: the confirmation run (299 of 299 within the cap, median 0.731 s, max 1.125 s; exact, 299 of 299, difference 0; lag 0.01 s) and the 
- 5b152dab 10:26:53 Revert the parallel extraction (5e4193a6): the ship rule's memory condition failed on the confirmation run (rules fixed before it), so the live app retu
- c8001f62 10:28:05 Parallel extraction closed: the report reports/identification/2026-10-12_parallel-extraction.md (exact; 299 of 299 within the cap, median 0.731 s; memor
- d5cd118b 10:33:14 Re-adopt the parallel extraction (revert 5b152dab, Uzayr's go, 12 Oct): the memory rule redefined before a fresh confirmation run; identify_engine.py as
- 4af57630 10:37:32 Parallel extraction, second go (Uzayr, 12 Oct): the memory rule redefined after the first run's result and fixed before the fresh confirmation run (rule
- 7d98eba6 10:38:21 Parallel extraction, second run: decide2.py (the redefined rule, rules2.json) and its launcher (every process logged at the start and the end)
- c9f24ac7 10:43:54 par_report: both confirmation runs, the memory rule's redefinition after the first (why, and that it was fixed before the second), the Editor list from 
