# Identification: staged window extraction in the v5 live app (2026-10-12)

**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in view. Timing only: no model, weight, replay, decision or accuracy figure changes, and no new look at any test output beyond the identity checks. Uzayr's go (12 Oct, `prompt_agent1_staged_extraction.md`, recorded in `runs/identify/v5/staged/QUEUE_STAGED.md`): run the half of each window's extraction whose data ends before the window's end while the window is still open, drop repeated work only where provably the same value, prove every extraction and decision identical, and run one confirmation run set up as the shipped pool's; if any rule fails, revert to the shipped pool, report and stop. Background: `reports/identification/2026-10-12_extraction-stages.md` (a944de32). The earlier reports are not edited. Generated 12 Oct 2026 15:14:17 SAST from the result files by `runs/identify/v5/staged/staged_report.py`.

**Final decision: KEPT on Uzayr's acceptance after the result: memory rule (1) failed as fixed (2.18 against 2.0625 GB/h).** The rules fixed before the run decided REVERT (section 3), and the code was reverted (7a1a3de2). Uzayr then accepted the failed rule (12 Oct 2026, at or before 15:11:44 SAST; recorded word for word in `runs/identify/v5/staged/QUEUE_STAGED.md`, 2375cd59, before any code changed): the staged extraction ships with step C's figures. No rule file was changed, no rule was redefined and there was no new run. His reasons: all the growth was in the main process, which is the shipped app's existing day-long growth; the four workers were flat (largest 98 MB); the slope has varied by about this much between runs (1.79, 1.875, 1.99, 1.99); every other rule held, including exactness (299 of 299, difference 0) and the 0.60 s bar. This is the second memory-rule decision made after a result on 12 Oct: the first was the parallel extraction's memory rule, redefined after its first confirmation run (`parallel/rules2.json`, 10:37:32, `reports/identification/2026-10-12_parallel-extraction.md` Section 4). The reader should weigh both.

**Decision by the rules fixed before the run: REVERT to the shipped pool (and stop).** Not every condition of Uzayr's pass rules holds (below), so the app returns to the shipped one-job-per-window pool, its figures (0.714 s, 299 of 299) stand, and the work stops (no redefinition, no re-run).

## 1. What was built (`pipeline/live/identify_engine.py`; timing fields in `pipeline/identify/iv5_rig.py`; engine.py unchanged)

- **Early jobs** (`_early_job`, sent by `ExtractPool.early` after each finite poll of the app): stage `dir`, the direction on [t0, t0 + 3] (its decision-time search `Extractor.t_dec_end`, its interpolation `Extractor._raw` and `signal_measures`), with the 3.0 s checkpoint's RX2 band energy from the same interpolation; stages 1 to 3, the end detector's checkpoints at 3.25, 3.5 and 3.75 s (search, interpolation, `band_energy_rx2`). Each runs on a frozen copy of the frames that had arrived by the poll that sent it, copied as `ExtractPool._dispatch` copies them (never trimmed). A stage is sent once its data end has passed and every receiver's latest frame, on the causal clock, is past it (`Receiver.last_time`, a readiness probe only). Its result counts only if its search settled within the copy (the result at or before the copy's time), the job is done when the late job is sent, and its data end is still the window's (a press that cuts the window afterwards voids it); otherwise the late job computes the stage.
- **The late job** (`_late_job`, `_staged_extract_v4`), at the window's decision time on the frozen copy then: `Extractor.extract_v4`'s statements in its order, from the engine's own functions, using the early results.
- **Repeated work dropped, only where provably the same value:** the 3.0 s checkpoint's search and interpolation are the direction's (the same call on the same frames; the engine's functions copy before changing an array, so `signal_measures` leaves the interpolation unchanged); the last checkpoint's search is the window's decision time (the engine's own scan of the same frames) and its interpolation `_raw(t0, end, td)` is shared with the speed. The second holds while every frame reaches the engine before the poll that passes its arrival time, which the engine's own scan also relies on; the pool counts pushes that break it (late frames), and a window open during one uses no early result and no shortcut. `extract_window` is untouched: its own interpolation and its `signal_measures` (whose values `extract_v4` overwrites) stay.
- **Workers:** 4 (`EXTRACT_WORKERS_STAGED`), fixed in QUEUE_STAGED before step B: the machine has 4 performance and 6 efficiency cores, a walk's busiest 0.6 s holds about three early and three late jobs, and the main process (mps) needs a core. Spawned processes, BLAS at one thread, no torch, no GPU, warmed at app start, as the shipped pool.
- **Fallbacks:** `--extract-mode pool` gives the one-job-per-window pool exactly as shipped (03952698; `_dispatch` and `_extract_window_job` unchanged, three workers); `--extract-workers 0` is the serial path, unchanged.
- **History:** built 56eea977; reverted 7a1a3de2 after the confirmation run failed a pass rule (section 3): `pipeline/` is again byte-identical to 03952698, the shipped pool; re-adopted 7df749b3 (the revert of 7a1a3de2) on Uzayr's acceptance: every file under `pipeline/` (255 files, SHA-256, `staged/readopt_hashes.json`) is byte-identical to the tree that ran step C (89e02559, HEAD at its launch; `pipeline/` there identical to 56eea977's), and engine.py is unchanged from 03952698.

## 2. Exactness

1. **Step A, every window of every B2 walk, staged against serial** (`staged/staged_exact.json`, cpu, nice 10, 4 workers, frames pushed in 0.05 s ticks and every extractor polled after each, early jobs sent after each tick's poll as the app sends them): 299 walks, 897 windows, 897 bitwise identical in every field but `extract_s` (`n_frames` included) and 897 with equal decision times; 33 decided by a recording's closing poll and 33 at their cap, all included; 0 cut windows (B2 has no two presses within 6.1 s). Walk i followed policy i mod 4 (wait for early results; no waiting; no readiness probe, so unsettled results are discarded and sent again; one simulated late frame): 3155 early jobs. How each stage was obtained, over windows: cp0 direction 223, early 674; cp1 early 672, late 225; cp2 early 668, late 229; cp3 early 662, late 235; cp4 decision time 675, late 222; dir early 674, late 223.
2. **Step A2, synthetic cuts** (B2's first two identification recordings, an extra press per walk at t0 + 3.4 s handed over at t0 + 3.9 s, or at t0 + 2.5 s handed over at t0 + 3.6 s, as a late key press): 117 windows, 117 identical with 117 equal decision times; 24 cut windows; sources: cp0 direction 16, early 101; cp1 decision time 1, early 101, late 6; cp2 decision time 10, early 91, late 6; cp3 decision time 4, early 87, late 6; cp4 decision time 93; dir early 101, late 16.
3. **Step A's checks** (QUEUE_STAGED, fixed before the run): A all windows: holds; A identical: holds; A t dec equal: holds; A2 identical: holds; A2 cut windows: holds; branches exercised: holds; retries after not final: holds; late frame fallback: holds; branches not exercised: none: **PASSED** (743 s).
4. **Step B, the live app on cpu** (`staged/cpu_exact.json`; B2 through the app and the real serial parser at full speed, nice 10, the change's defaults: staged, 4 workers), against the shipped app's own cpu run (`parallel/cpu_exact/after.*`, 12 Oct 09:19; its `pipeline/` byte-identical to 03952698's): bit-identical on all 299 decisions in every saved field (t0, t_dec, ensemble, ensemble_nopace, confidence, calib_n, top, closing): **PASSED**; against loso_B2_v5's replay, argmax 299 of 299, largest ensemble difference 8.06e-06 on the 287 decided during the stream (bound 8.1e-06) and 9.47e-06 on the 12 closing-poll ones (9.47e-06 before): **PASSED**. The app took 1203 s against the shipped app's 1061 s.
5. **Step C, mps, the confirmation run against the replay:** argmax 299 of 299, largest ensemble difference 0 (required 0): **PASSED**.

## 3. The confirmation run

Set up as the shipped pool's (`staged/run_confirm_staged.sh confirm_staged 0 70`, `iv5_rig confirm --tag confirm_staged`: the app with the change, its defaults, staged with 4 workers): B2 through the real SerialReader and parse_line (fake port); every recording at 1x with the screen drawn (headless); loso_B2_v5, room B, mps, OMP_NUM_THREADS 1, nice 0 (the workers too), the in-app MPS cache release on; 65.2 min, ended 2026-10-12 14:47:19. Every decision timed. Pass rules fixed before the run (QUEUE_STAGED, `staged/rules_staged.json`): (i) exact on mps; (ii) every decision before its cap (t0 + 5.30 s); (iii) the stream's lag at every press at most 0.5 s; (iv) memory as `parallel/rules2.json`, unchanged: (1) the total (main process plus the workers) grows at most 1.875 x 1.10 = 2.0625 GB/h, least-squares slope from minute 10 to the end; (2) workers judged by trend: each worker's slope from minute 10 at most 10 MB/h, and no worker above 150 MB at any sample (MB = top's own figure, GB x 1024); (3) no swap growth (the swap in use never above its value at the run's start, and the Swapouts counter unchanged), memory pressure never critical (kern.memorystatus_vm_pressure_level never 4), and level 2 only at samples where free memory is at or above 30 %; (v) worth it: the median decision delay after t0 + 4.0 s at most 0.60 s.

| per press (seconds after t0 + 4.0 s unless named) | the shipped pool (confirm_par2, 10:41) | this staged run |
|---|---|---|
| decision delay, median / p95 / p99 / max | 0.714 / 0.787 / 0.805 / 0.813 | **0.545 / 0.573 / 0.584 / 0.585** |
| decisions within the cap (t0 + 5.30 s) | 299 of 299 | 299 of 299 |
| processing after the last data (decision delay minus the last window's packet wait), median / p95 / p99 / max | 0.387 / 0.458 / 0.471 / 0.484 | 0.220 / 0.234 / 0.239 / 0.243 |
| the last window's late extraction in its worker (s), median / p95 / p99 / max | 0.307 / 0.373 / 0.390 / 0.400 (the whole window) | 0.137 / 0.153 / 0.229 / 0.299 |
| every window's extraction in its worker (s), median / p95 / p99 / max | 0.306 / 0.374 / 0.397 / 0.439 | 0.135 / 0.153 / 0.228 / 0.299 |
| the decision path's wait for the workers (s), median / p95 / p99 / max | 0.239 / 0.314 / 0.369 / 0.417 | 0.064 / 0.088 / 0.251 / 0.314 |
| the classification of the three windows (model time minus that wait), median / p95 / p99 / max | 0.139 / 0.161 / 0.163 / 0.167 | 0.144 / 0.166 / 0.168 / 0.170 |
| the adaptation after the decision, median / p95 / p99 / max | 0.255 / 0.458 / 0.481 / 0.506 | 0.281 / 0.488 / 0.523 / 0.531 |
| the stream's lag at a press, median / largest | 0.006 / 0.01 | 0.006 / 0.01 |

**The budget per part** of each decision (the last window, at t0 + 0.30 s, is the one the decision waits for), median / p95 in seconds:

| part | the shipped pool | this staged run |
|---|---|---|
| packet wait: the last window's end (t0 + 4.30 s) and its packets, after t0 + 4.0 s | 0.332 / 0.351 | 0.332 / 0.351 |
| dispatch: the copy and submit of the last window's late job in the main process | (not recorded) | 0.000 / 0.001 |
| the late job's wait for a free worker | 0.025 / 0.030 | 0.026 / 0.034 |
| late extraction: the last window's job in its worker | 0.307 / 0.373 | 0.137 / 0.153 |
| classification of the three windows | 0.139 / 0.161 | 0.144 / 0.166 |
| the whole decision delay | 0.714 / 0.787 | 0.545 / 0.573 |

The parts overlap and do not add up exactly: the late job starts at the first poll after the last window's packets (the rig polls after every batch of frames), and the result is fetched inside the classification step.

Walk by walk: this run's delay minus the shipped pool's, median -0.166 s (p5 -0.235, p95 -0.119); faster on 299 of 299.

**The 0.5 s processing target:** median 0.220 s and at most 0.243 s, so it is met at the median and on 299 of 299 walks (287 of the 287 decided during the stream, the largest 0.243 s; the 12 decided at a recording's close count trivially).

**How the stages were obtained in the run** (897 windows; 897 with no late frame while open): checkpoint 3.00 direction: 6; checkpoint 3.00 early: 891; checkpoint 3.25 early: 886; checkpoint 3.25 late: 11; checkpoint 3.50 early: 880; checkpoint 3.50 late: 17; checkpoint 3.75 early: 872; checkpoint 3.75 late: 25; checkpoint 4.00 decision time: 897; dir early: 891; dir late: 6.

| minute | main (GB) | worker 1 (GB) | worker 2 (GB) | worker 3 (GB) | worker 4 (GB) | total (GB) | free (%) |
|---|---|---|---|---|---|---|---|
| 0 | 0.05 | - | - | - | - | 0.05 | 80 |
| 5 | 1.64 | 0.09 | 0.08 | 0.08 | 0.08 | 1.95 | 80 |
| 10 | 1.63 | 0.09 | 0.08 | 0.08 | 0.08 | 1.95 | 80 |
| 15 | 1.71 | 0.09 | 0.08 | 0.08 | 0.08 | 2.03 | 80 |
| 20 | 1.96 | 0.09 | 0.08 | 0.08 | 0.08 | 2.28 | 79 |
| 25 | 2.09 | 0.09 | 0.09 | 0.08 | 0.08 | 2.43 | 77 |
| 31 | 2.38 | 0.09 | 0.08 | 0.08 | 0.08 | 2.70 | 77 |
| 35 | 2.34 | 0.09 | 0.09 | 0.08 | 0.08 | 2.68 | 77 |
| 40 | 2.73 | 0.09 | 0.08 | 0.08 | 0.08 | 3.06 | 76 |
| 45 | 2.68 | 0.09 | 0.08 | 0.08 | 0.08 | 3.01 | 76 |
| 50 | 3.07 | 0.09 | 0.08 | 0.08 | 0.08 | 3.39 | 73 |
| 55 | 2.99 | 0.10 | 0.08 | 0.09 | 0.08 | 3.34 | 73 |
| 61 | 3.45 | 0.09 | 0.08 | 0.08 | 0.08 | 3.77 | 70 |
| 65 | 3.47 | 0.09 | 0.08 | 0.08 | 0.08 | 3.80 | 70 |

**Memory against the rule** (`parallel/rules2.json`, unchanged; fixed in `staged/rules_staged.json`):

1. **The total** (main plus the 4 workers): slope from minute 10 2.1794 GB per hour against at most 2.0625; at minute 10 1.953 GB, peak 4.542 GB: **FAILS**.
2. **The workers by trend** (slope from minute 10 at most 10 MB per hour; never above 150 MB): worker 1 (pid 45537): fixed size 89.0 MB at minute 10, slope 2.92 MB per hour, largest 98.0 MB; worker 2 (pid 45539): fixed size 79.0 MB at minute 10, slope -0.29 MB per hour, largest 91.0 MB; worker 3 (pid 45540): fixed size 79.0 MB at minute 10, slope 4.87 MB per hour, largest 90.0 MB; worker 4 (pid 45541): fixed size 79.0 MB at minute 10, slope 1.5 MB per hour, largest 88.0 MB: **holds**.
3. **Swap and pressure:** the swap in use 1091 MB at the start, at most 1091 MB, 1083 MB at the end; the Swapouts counter 2206899 to 2206899; pressure levels seen [1]; free memory at least 70 %: **holds**.

Where the growth is: the main process went from 1.63 GB at minute 10 to 3.47 GB at the end, while the 4 workers stayed flat (above). The shipped pool's run, on the same rule, had a total slope of 1.9946 GB/h. The main process's growth over a day is the one noted in the handoff (cause not attributed); this run does not attribute it either.

**Running at the start** (`logs/confirm_staged_processes_start.txt`, every process logged; those above 200 MB): Code Helper (Renderer) 915 MB; Code Helper (Renderer) 828 MB; Claude Helper (Renderer) 719 MB; Code Helper (Plugin) 703 MB; Code Helper (Renderer) 467 MB; claude 425 MB; claude 376 MB; Code Helper (Renderer) 374 MB; Code 372 MB; claude 360 MB; Claude 329 MB; Code Helper (Plugin) 284 MB; Code Helper (Renderer) 273 MB; claude 268 MB; Code Helper 261 MB; server.bundle.js 240 MB; mediaanalysisd 231 MB; server.bundle.js 230 MB.

**The pass rules, condition by condition:**

- exactness on the GPU: 299 of 299, difference 0: **holds**
- every decision before its cap: 299 of 299: **holds**
- the stream's lag at every press at most 0.5 s: largest 0.01 s: **holds**
- memory (1), the total: slope from minute 10 2.1794 GB/h against at most 2.0625, peak 4.542 GB: **FAILS**
- memory (2), the workers by trend: worker 1 (pid 45537): fixed 89.0 MB at minute 10, slope 2.92 MB/h, largest 98.0 MB (holds); worker 2 (pid 45539): fixed 79.0 MB at minute 10, slope -0.29 MB/h, largest 91.0 MB (holds); worker 3 (pid 45540): fixed 79.0 MB at minute 10, slope 4.87 MB/h, largest 90.0 MB (holds); worker 4 (pid 45541): fixed 79.0 MB at minute 10, slope 1.5 MB/h, largest 88.0 MB (holds): **holds**
- memory (3), swap and pressure: swap in use 1091 MB at the start, at most 1091, 1083 at the end; Swapouts 2206899 to 2206899; pressure levels [1]; free memory at least 70 %: **holds**
- worth it, the median delay after t0 + 4.0 s at most 0.6 s: 0.5451 s: **holds**

**Decision on this run: REVERT to the shipped pool (and stop).**

## 3a. The session length the growth allows (Uzayr's acceptance)

Step C's total footprint (main process plus the 4 workers) was 1.953 GB at minute 10 and grew at 2.1794 GB per hour from there (least-squares, `staged/rules_staged.json`, measured from `logs/confirm_staged_memory.csv` and `_workers.csv`). At that rate it reaches the run guard's 12 GB after

(12 - 1.953) GB / 2.18 GB per hour = 10.047 / 2.18 = 4.61 hours (4.61 at the unrounded 2.1794)

from minute 10, so about 4.8 hours from the app's start. This assumes the growth stays linear beyond the 65 minutes measured (it reached 3.47 GB in the main process by the end), and 12 GB is the guard the runs use, not a measured point of failure.

## 4. The Editor list (only after the Mastermind's review)

The staged extraction is kept on Uzayr's acceptance with step C's figures, so these change. Old values are what the thesis says now (the 11 Oct latency run, 1.05 s); the parallel extraction's Editor list (0.71 / 0.81 s, `reports/identification/2026-10-12_parallel-extraction.md` Section 6) was not applied and is superseded by this one. Every accuracy is unchanged. The 0.5 s processing target is worded as met at the median and on N of 299 walks, not as met outright. The memory line states the failed rule as accepted, not as passed.

| place | figure | old | new | source |
|---|---|---|---|---|
| Section 3.6 (Methodology, the real-time application) | the decision after t0 + 4.0 s, median / at most; decisions within the cap | 1.05 / 1.32 s; 298 of 299, one miss of 0.015 s | 0.55 / 0.59 s; 299 of 299 | old: the thesis as it reads now (`reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`); new: `reports/identification/2026-10-12_staged-extraction.md` Section 3; `runs/identify/v5/rig_timing_confirm_staged.json` and `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz` |
| Figure 3.4 (`fig:id-engine`, Figures/tikz/id_engine.tex) | the output box: median / at most after t0 + 4.0 s | 1.05 / 1.32 s | 0.55 / 0.59 s | old: the thesis as it reads now (`reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`); new: `reports/identification/2026-10-12_staged-extraction.md` Section 3; `runs/identify/v5/rig_timing_confirm_staged.json` and `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz` |
| Section 4.5 (Results, real-time performance) | the classification of the three windows, median / at most; the decision, median / at most; within the cap; the calibration (adaptation) after each decision, median / at most | 0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 (miss 0.015 s); 0.29 / 0.55 s | 0.144 / 0.170 s; 0.55 / 0.59 s; 299 of 299; 0.28 / 0.53 s | old: the thesis as it reads now (`reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`); new: `reports/identification/2026-10-12_staged-extraction.md` Section 3; `runs/identify/v5/rig_timing_confirm_staged.json` and `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz`; the classification is model_s minus the wait for the workers, from `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz` |
| The latency table (identification column) | computing per step; output against design time; final output; wall-clock delays | 0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 by t0 + 5.30 s; 0.29 / 0.55 s | 0.144 / 0.170 s; 0.55 / 0.59 s; 299 of 299 by t0 + 5.30 s; 0.28 / 0.53 s | old: the thesis as it reads now (`reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`); new: `reports/identification/2026-10-12_staged-extraction.md` Section 3; `runs/identify/v5/rig_timing_confirm_staged.json` and `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz`; the classification is model_s minus the wait for the workers, from `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz` |
| The compliance row (Latency, at most 0.5 s) | from the last window's packets to the decision, median / at most; the 0.5 s target | 0.718 / 0.980 s; missed at the median (Met: Y / N) | 0.220 / 0.243 s; met at the median and on 299 of 299 walks (287 of the 287 decided during the stream, the largest 0.243 s; the 12 decided at a recording's close count trivially) (Met: Y / Y, worded as met at the median and on the N of 299 walks given) | old: the thesis as it reads now (`reports/identification/2026-10-11_engine-v5-latency.md` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`); new: `reports/identification/2026-10-12_staged-extraction.md` Section 3; `runs/identify/v5/rig_timing_confirm_staged.json` and `runs/identify/v5/rig/rig_timing_confirm_staged_20261012_134206.npz` (delay_after_t0_plus_4_s minus wait_s) |
| Section 4.5, the memory limitation line (new; the thesis has none) | the app's memory growth and the session length it allows | none | the application's memory grows about 2.18 GB per hour over a day's stream (all in the main process, on the GPU side; the extraction workers stay flat), so from 1.95 GB it would reach 12 GB after about 4.6 hours (about 4.8 hours from the start); this is above the 2.0625 GB per hour fixed before the run, and was accepted after the result | `staged/rules_staged.json` (measured.memory.total); `logs/confirm_staged_memory.csv`; `reports/identification/2026-10-12_staged-extraction.md` Sections 3 and 3a |

Where the application is described, a sentence may be added: each window's direction and end-detector checkpoints are extracted while the window is still being received (the engine's own functions, identical outputs), and `--extract-workers 0` remains the serial fallback. Source: this report, Sections 1 and 2.

## 5. Files and commits

- Code: `pipeline/live/identify_engine.py` (`_early_job`, `_staged_extract_v4`, `_late_job`, `ExtractPool.early` and `_late`, `--extract-mode`); `pipeline/identify/iv5_rig.py` (per-window dispatch and stage sources, the classification time, a timing-only rows file). engine.py unchanged.
- Records: `runs/identify/v5/staged/` (QUEUE_STAGED.md, staged_exact.py and .json, cpu_exact/ and cpu_exact.json, rules_staged.json, decide_staged.py, run_staged_step.sh, run_confirm_staged.sh, this generator); `runs/identify/v5/rig_timing_confirm_staged.json`, its per-walk files and jsonl; `logs/confirm_staged_memory.csv`, `_workers.csv`, `_system.csv`, `_processes_start.txt` and `_end.txt`.

Commits:

- 56eea977 12:58:51 Staged window extraction in the v5 live app (Uzayr's go, 12 Oct; timing only), with its pass rules fixed before any run
- a12fbb1a 13:14:08 Staged extraction, step A PASSED: every window of every B2 walk (897) bitwise identical staged against serial with equal decision times (33 closing-poll
- f756ec9d 13:34:44 Staged extraction, step B PASSED: the live app with the change bit-identical to the shipped app on all 299 B2 decisions (cpu); against the replay within
- 7a1a3de2 14:48:19 Revert the staged extraction (56eea977's code): step C failed memory rule (1), the total's slope from minute 10 2.1794 GB/h against at most 2.0625 (rule
- 27198bad 14:49:02 Staged extraction closed: the confirmation run (exact 299 of 299, difference 0; 299 of 299 within the cap; median 0.545 s, max 0.585 s; processing after
- adfa3b1b 14:57:19 QUEUE_STAGED: the staged-extraction report APPROVED by the Mastermind; job closed
- 2375cd59 15:12:01 QUEUE_STAGED: Uzayr's decision after step C's result, recorded word for word before any code changes: accept the failed memory rule (1) (2.18 against 2.
- 7df749b3 15:12:11 Re-adopt the staged extraction (revert 7a1a3de2) on Uzayr's acceptance after step C's result (QUEUE_STAGED, 2375cd59): memory rule (1) failed as fixed (
