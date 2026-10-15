# Identification: engine v5's live latency (2026-10-11)

**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in view. Timing only: no model, weight, replay, decision or figure changes. Uzayr's go (11 Oct, quoted in `runs/identify/v5/latency/QUEUE_LAT.md`): profile the live app's decision path on B2, change only `pipeline/live/identify_engine.py` (and the `iv5_rig` harness), prove exactness as before, and run a new confirmation run with its pass rules fixed before it. The earlier report, `reports/identification/2026-10-11_engine-v5.md`, is not edited; this report replaces its timing figures only. Generated 11 Oct 2026 19:58:15 SAST from the result files by `runs/identify/v5/latency/lat_report.py`.

## 1. Where a decision's time went (the profile)

B2's first 4 recordings at 1x through the real serial parser on mps (OMP_NUM_THREADS 1, nice 0, alone on the machine; 47 decisions), the app as it was, with its and the engine's methods wrapped by timers inside the harness process only (`iv5_rig profile`; `latency/profile_mps.json`). Medians over the decisions:

| | seconds |
|---|---|
| the decision delay after t0 + 4.0 s | 1.098 |
| the three windows' extractions, one after another (median of their sum; largest) | 0.865; 1.337 |
| of them, the last (0.30 s) window's, in the decision tick | 0.2877 |
| the classification of the three windows (first walk: 0.299) | 0.1258 |
| the stream's lag when the decision tick started | 0.3474 |
| the screen's redraws in the 0.6 s before the decision | 0.1124 |
| frame flush, keys, line written, cache release, combination (decision tick) | 0.0002 |

Over the whole run (11.0 min), the ticks took 200 s of work, 132 s of it redrawing the screen (every 0.1 s of stream time, whatever had changed), 41 s extracting windows and 6 s classifying.

**What it shows.** The 0 s window's extraction starts when its last packets arrive, about t0 + 4.03 s; each window's extraction takes about 0.29 s of wall clock on one thread, so the 0.15 s and 0.30 s windows queue behind it and the last finishes about 0.87 s later; the classification adds about 0.13 s. That serial chain is the engine's own work (`engine.py`, untouched under this go) and sets the floor near 1.0 s after t0 + 4.0 s. The app's share was the screen: redrawn every 0.1 s, its redraws sat in front of the windows' extractions (0.11 s in the 0.6 s before a decision). The first walk's classification paid the GPU's first-call cost.

## 2. The change (`pipeline/live/identify_engine.py` only; engine v5 only; commit 7de0b32b)

- **The screen is redrawn when what it shows changes:** the last decision, the walks seen, whether a walk is in progress, the score, the stream. Between redraws its window's events are pumped every 0.1 s, so the window stays responsive. What the screen shows is unchanged.
- **The CNNs are warmed before the first press:** each of the 12 CNNs is run once on zero windows of the usual shapes (10 to 12 windows of 28 x 34; three channels for cnn3, one for each link) in eval mode without gradients, its output discarded. No weight, statistic or pool changes.
- Engine v4's path, screen and defaults are unchanged; `engine.py`, the models, the weights and the replays are untouched.

## 3. Exactness

1. **cpu, before against after** (B2 through the live app and the real serial parser on cpu at full speed, untimed, nice 10; the code before the change, 445d42c1's `pipeline/` in a scratch tree, and after it, side by side): bit-identical on all 299 decisions in every field (t0, t_dec, ensemble, ensemble_nopace, confidence, calib_n, top, closing): **PASSED**. After against loso_B2_v5's replay: argmax 299 of 299; largest ensemble difference 8.06e-06 on the 287 decisions made during the stream, 9.47e-06 on the 12 made by the recordings' closing polls: the same values as before option (c) and the change (the cpu's arithmetic against the mps replay). `latency/cpu_exact.json`.
2. **v4, before against after** (the live app on cpu, loso_B2_v4 on B2's first recording, 10 decisions): bit-identical in every decision field, only the wall-clock timing fields differ: **PASSED**. `latency/live_before_after_v4.json`.
3. **mps, the new confirmation run against loso_B2_v5's replay:** argmax 299 of 299, largest ensemble difference 0 (required 0): **PASSED**.

## 4. The new confirmation run

The same setup as option (c)'s (`runs/identify/v5/latency/run_confirm_lat.sh`, a copy of `run_confirm.sh` with its own output names): B2 through the real SerialReader and parse_line (fake port); every recording at 1x with the screen drawn (headless); model loso_B2_v5, room B, mps, OMP_NUM_THREADS 1, nice 0, alone on the machine; 65.3 min, ended 2026-10-11 19:57:16. Every decision timed, the closing polls included. Pass, fixed before the run (QUEUE_LAT), as option (c)'s: every decision before its cap (t0 + 5.30 s); the stream's lag at every press at most 0.5 s; memory flat (slope from minute 10 at most 0.5 GB per hour, never above 12 GB).

| | option (c)'s run (12:49) | the new run |
|---|---|---|
| decision delay after t0 + 4.0 s (s), all walks, median / p95 / p99 / max | 1.083 / 1.189 / 1.261 / 1.453 | 1.047 / 1.118 / 1.15 / 1.315 |
| decisions before their cap, all / identification / tracking walks | 297 of 299 / 177 of 179 / 120 of 120 | 298 of 299 / 178 of 179 / 120 of 120 |
| model time, three windows (s), median / p95 / p99 / max | 0.127 / 0.147 / 0.162 / 0.316 | 0.14 / 0.149 / 0.156 / 0.167 |
| the adaptation after the decision (s), median / p95 / p99 / max | 0.277 / 0.48 / 0.511 / 0.525 | 0.289 / 0.481 / 0.519 / 0.546 |
| adaptations waited for by a later walk | 0 | 0 |
| the stream's lag at a press (s), median / largest | 0.005 / 0.077 | 0.005 / 0.012 |
| memory: footprint at 10 min / largest / last (GB); slope from minute 10 (GB per hour) | 1.64 / 4.47 / 3.35; 1.99 | 1.68 / 3.76 / 3.45; 1.875 |
| verdict (timing; memory) | FAIL; FAIL | **FAIL; FAIL** |

**Walk by walk** (the same 299 walks): the new run's delay minus option (c)'s, median -0.029 s (p5 -0.125, p95 +0.029); faster on 233 of 299. The day's first walk: 1.301 s before, 1.033 s now (its model time 0.316 s before, 0.147 s now).

**Where the delay goes now** (seconds after t0 + 4.0 s, all decisions; packet wait, extraction and model from the decisions' own lines; the engine's `extract_s` covers only part of a window's extraction, about 0.105 s of the 0.29 s the profile measured around the whole `extract_v4`; "the rest" is the time beyond those three from the frame that closes the last window to the decision being out: the remainder of the last window's extraction and the earlier windows' extractions queued in front of it):

| part | option (c)'s run, median / max | the new run, median / max |
|---|---|---|
| the wait for the last window's packets (0.30 s offset included) | 0.332 / 1.300 | 0.332 / 1.300 |
| the last window's extraction | 0.105 / 0.482 | 0.105 / 0.142 |
| the model, three windows | 0.127 / 0.316 | 0.140 / 0.167 |
| the rest | 0.526 / 0.699 | 0.477 / 0.731 |
| the decision delay | 1.083 / 1.453 | 1.047 / 1.315 |

**The one decision after its cap in the new run:** walk 26 of the day (an identification walk, slow block) at 1.315 s, 15.3 ms after its cap (packet wait 0.335, extraction 0.114, model 0.135, rest 0.731; option (c)'s run: 1.114 s).

**Verdict: FAIL.** Reported as measured, nothing changed after the run; flagged for Uzayr. The serial extraction of the three windows (the engine's) remains the floor of the delay.

## 5. The Editor list: the timing figures that change (only after the Mastermind's review)

Every other figure, including every accuracy, is unchanged. Where the thesis quotes the confirmation run (B2's whole day at 1x on the GPU), its timing figures change as follows:

| figure | was (option (c)'s run, 11 Oct 12:49) | now (this run) |
|---|---|---|
| decisions within the cap of t0 + 5.30 s | 297 of 299 | 298 of 299 |
| the decision after t0 + 4.0 s, median | 1.08 s | 1.05 s |
| the decision after t0 + 4.0 s, at most | 1.45 s (1.4534) | 1.32 s (1.3153; 15 ms past the cap of 1.30 s) |
| the decision after t0 + 4.0 s, p95 | 1.19 s | 1.12 s |
| the stream's largest lag at a press | 0.08 s | 0.01 s |
| the adaptation after the decision, median / at most | 0.28 / 0.53 s | 0.29 / 0.55 s |
| memory: growth per hour; largest | 1.99 GB; 4.47 GB | 1.875 GB; 3.76 GB |
| verdict | FAIL | FAIL |

- **Methodology 3.5.1**, the engine figure's "median / at most" note, as shipped: "a median 1.08 s and at most 1.45 s" becomes "a median 1.05 s and at most 1.32 s" after t0 + 4.0 s.
- **The real-time statement:** "297 of 299 decisions came before their cap" becomes "298 of 299", with the median and largest delay above; the sentence that the screen is redrawn only when it changes and the CNNs are warmed before the first press may be added where the app is described. The cpu finding (about 6 s per walk on the cpu) is unchanged.

## 6. Files and commits

- Code: `pipeline/live/identify_engine.py` (the change); `pipeline/identify/iv5_rig.py` (`profile`, `confirm --tag`); `pipeline/identify/iv5_report.py` (its confirmation-run file pattern narrowed so the earlier report regenerates unchanged); `runs/identify/v5/cpu_exact.py` (an output path argument).
- Records: `runs/identify/v5/latency/` (QUEUE_LAT.md, profile_mps.json, cpu_exact/, cpu_exact.json, live_before_after_v4.json, run_profile.sh, run_cpu_exact.sh, run_confirm_lat.sh, this generator); `runs/identify/v5/rig_timing_confirm_lat.json` and `rig/rig_timing_confirm_lat_*.npz`, its jsonl, `logs/confirm_lat_memory.csv`.

Commits:

- 1cf0086a 18:08:52 Identification v5 latency (Uzayr's go, 11 Oct): the queue, his go quoted
- dad9acab 18:10:01 iv5_rig profile (the latency go): the live app's decision tick timed part by part, timers in the harness process only; its launcher
- 7de0b32b 18:25:20 Live app, engine v5 latency (Uzayr's go, 11 Oct; timing only): the screen redrawn when what it shows changes (a press, a decision, the score), its event
- 5c4f5b67 18:25:56 Identification v5 latency: the profile (the serial window extractions dominate; the screen's redraws are the app's share) and step 2's launcher
- 191cf55a 18:28:30 Identification v5 latency: the new confirmation run's pass rules fixed before it starts (as option (c)'s); its launcher (confirm --tag confirm_lat); the
- 9563249a 18:51:53 Identification v5 latency, step 2 PASSED: the live app before and after the change bit-identical on all 299 B2 decisions (cpu) and on v4 (loso_B2_v4, B2
