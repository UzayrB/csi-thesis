# QUEUE_STAGED: staged window extraction in the v5 live app (Uzayr's go, 12 Oct)

Read this file first on every turn. Development evaluation, all data seen. Session: Agent1 (Third overall). Earlier jobs:
../parallel/QUEUE_PAR.md, ../latency/QUEUE_LAT.md, ../latency/stages/QUEUE_STAGES.md; their reports are not edited.

**Uzayr's go:** `prompt_agent1_staged_extraction.md`, given in this chat on 12 Oct 2026 (received at or before 12:45:23 SAST).
Timing only: no model, weight, replay, decision or accuracy figure may change. Background:
reports/identification/2026-10-12_extraction-stages.md (a944de32).

| step | state | next |
|---|---|---|
| 0 set-up | this file, written 12 Oct before any run (fixed at 12:58:44); committed before step B | the Mastermind's slot for A and B |
| build | 56eea977; reverted 7a1a3de2; RE-ADOPTED 7df749b3 on Uzayr's acceptance (pipeline/ hash-identical to step C's tree) | - |
| A exactness (windows) | PASSED (13:01:28 to 13:13:52): 897 of 897 identical, A2 117 of 117 (24 cut), every branch | - |
| B exactness (app on cpu) | PASSED (13:14 to 13:34:16): 299 of 299 bit-identical to the shipped app; replay 8.06e-06 (287), 9.47e-06 (12 closing) | - |
| C confirmation run | DONE 13:42:04 to 14:47:20: memory (1) FAILS (2.1794 GB/h against 2.0625); every other rule holds, median 0.545 s | - |
| report | UPDATED: KEPT on Uzayr's acceptance after the result; Editor list on step C's figures | the Mastermind's review |

## The change (fixed before any run)

- `pipeline/live/identify_engine.py` only (plus timing fields in `pipeline/identify/iv5_rig.py`); `engine.py` unchanged. Every
  feature, map, spectrogram, Hampel, search and interpolation is the engine's own function (`Extractor.t_dec_end`,
  `Extractor._raw`, `signal_measures`, `band_energy_rx2`, `detect_end`, `extract_window`, `best_link`, `torso_hz`).
- **Early jobs** (`_early_job`), sent after each finite poll by `ExtractPool.early`, each on a frozen copy of the frames that
  had arrived by that poll (`_dispatch`'s copy, untrimmed): stage "dir" (the direction on [t0, t0 + 3]: its search,
  interpolation and `signal_measures`, plus the 3.0 s checkpoint's band energy from the same interpolation) and stages 1 to 3
  (the checkpoints at 3.25, 3.5 and 3.75 s: search, interpolation, RX2 band energy). A stage is sent once its data end has
  passed and every receiver's latest frame on the causal clock is past it (`Receiver.last_time`, a readiness probe only).
  Its result is used only if its search settled within the copy (the search's result is at or before the copy's time),
  the job is done when the late job is sent, and its data end is still the window's (a press that cuts the window
  afterwards voids it). Otherwise the late job computes the stage.
- **Late job** (`_late_job`, `_staged_extract_v4`) at the window's decision time, on the frozen copy at the decision time:
  `extract_v4`'s statements in its order. Repeats dropped only where provably the same value: the 3.0 s checkpoint's search
  and interpolation are the direction's (the same call on the same frames); the last checkpoint's search is the window's
  decision time and its interpolation is shared with the speed (the same `_raw(t0, end, td)`). The second rests on every
  frame reaching the engine before the poll that passes its arrival time (the engine's own scan relies on it); the pool
  counts pushes that break it ("late frames"), and a window open during one uses no early result and no shortcut.
  `extract_window` is untouched (its own interpolation and its overwritten `signal_measures` stay).
- **Workers: 4** (`EXTRACT_WORKERS_STAGED`), fixed here before step B. Why 4: the machine has 4 performance and 6 efficiency
  cores; a walk's busiest moment holds about three early jobs and three late jobs within 0.6 s, and the main process (mps)
  needs a core.
- **Fallbacks:** `--extract-workers 0` is the serial path, unchanged; `--extract-mode pool` is the one-job-per-window pool
  exactly as shipped (03952698; `_dispatch` and `_extract_window_job` unchanged, three workers by default).

## Pass rules (fixed before any run; never redefined)

**Step A** (`staged/staged_exact.py`, cpu, nice 10, OMP_NUM_THREADS=1, the frames pushed in 0.05 s ticks and every
extractor polled after each tick, early jobs sent after each tick's poll as the app sends them). Part A: all 299 B2 walks,
897 windows, staged against the serial `extract_v4`. Part A2 (synthetic cuts, because B2 has no two presses within 6.1 s):
B2's first two identification recordings with an extra press for every walk, at t0 + 3.4 s handed over at t0 + 3.9 s or at
t0 + 2.5 s handed over at t0 + 3.6 s (a late key press), so cut windows occur and some early results are voided. PASS needs
all of: (1) A covers 897 windows; (2) every window of A and A2 bitwise identical to serial in every field but `extract_s`
(`n_frames` included), and every decision time equal; (3) A2 has cut windows; (4) every branch of the assembly ran at least
once (the direction early and late; the 3.0 s checkpoint early and from the direction; the 3.25 s checkpoint early and late;
the 4.0 s checkpoint from the decision time and late); (5) at least one stage sent again after a result that was not final;
(6) the late-frame fallback ran (walks with a simulated late frame). Closing polls and cap decisions are included and
counted. Any failure STOPS the job: revert to the shipped pool and report.

**Step B** (`cpu_exact.py run after`, the live app with the change, its defaults: staged, 4 workers; B2 at full speed through
the real serial parser; cpu, nice 10, OMP_NUM_THREADS=1), compared (`cpu_exact.py compare`) with the shipped app's own cpu
run: `parallel/cpu_exact/after.*` (12 Oct 09:01 to 09:19, the pool app at 5e4193a6 with iv5_rig at f367734a; `git diff`
shows `pipeline/` byte-identical between that run's code and 03952698, and unchanged since), copied as
`staged/cpu_exact/before.*`. PASS needs: bit-identical on all 299 decisions in every saved field (t0, t_dec, ensemble,
ensemble_nopace, confidence, calib_n, top, closing); against the replay, argmax 299 of 299 and the ensemble within 8.1e-06 on
the 287 decided during the stream (the existing cpu tolerance; the 12 closing-poll ones reported as measured, 9.47e-06
before). Any failure STOPS the job: revert and report.

**Step C** (confirmation run, set up exactly as confirm_par2: B2 at 1x through the real serial parser, loso_B2_v5, --room B,
mps, one thread, nice 0, the in-app MPS cache release, to the end of the stream; the launcher `staged/run_confirm_staged.sh`,
the copy of `parallel/run_confirm_par2.sh` with the tag confirm_staged and `staged/decide_staged.py` on
`staged/rules_staged.json`). Before it: the Mastermind's slot; then Uzayr's "go C" in this chat; no LaTeX build or pagecount
in any session; the machine quiet; every process logged at the start and the end; Uzayr told the moment it ends. PASS needs
ALL of: (i) mps exact: argmax 299 of 299 and the ensemble difference 0 against loso_B2_v5's replay; (ii) every decision timed
and before its cap (t0 + 5.30 s); (iii) the stream's lag at every press at most 0.5 s; (iv) memory as rules2.json, unchanged:
the total (main plus the workers) slope from minute 10 at most 2.0625 GB/h; each worker's slope from minute 10 at most 10 MB/h
and never above 150 MB (top's MB); no swap growth (swap in use never above its start value, Swapouts unchanged); pressure never
level 4, and level 2 only at samples with free memory at or above 30 %; all 4 workers present; (v) WORTH IT: the median
decision delay after t0 + 4.0 s at most 0.60 s. **If any rule fails:** revert to the shipped pool (identify_engine.py and
iv5_rig.py as at 03952698's tree, by a revert commit), report, and stop: no redefinition and no re-run.

## Log
- **12 Oct 2026 13:14:08 SAST: step A PASSED.** The Mastermind's slot for A and B at 12:59:04 (LaTeX allowed). Smoke (one recording) 12:59:42 to 13:01:19: 30 of 30 and A2 117 of 117 identical. Step A 13:01:28 to 13:13:52 (rc 0, not killed; main and 4 workers, cpu, nice 10): 299 walks, 897 of 897 windows bitwise identical in every field but extract_s, 897 equal decision times; 33 decided by a closing poll and 33 at their cap; 3155 early jobs; stages early on 662 to 675 windows and late on the rest (the late-frame and no-wait walks); A2 117 of 117 identical with 24 cut windows; every branch exercised, retries after unsettled results, the late-frame fallback ran (staged_exact.json). Step B starts.
- **12 Oct 2026 13:34:44 SAST: step B PASSED.** The live app with the change (staged, 4 workers; cpu, full speed, nice 10; 13:14 to 13:34:16, 1203 s against the shipped app's 1061 s at full speed): bit-identical to the shipped app's cpu run on all 299 decisions in every saved field (t0, t_dec, ensemble, ensemble_nopace, confidence, calib_n, top, closing); against the replay argmax 299 of 299, 8.06e-06 on the 287 decided during the stream (bound 8.1e-06) and 9.47e-06 on the 12 closing ones, as before (staged/cpu_exact.json). Next: the Mastermind's slot for C, then Uzayr's "go C".
- **12 Oct 2026 13:42:17 SAST: step C starts.** The Mastermind's slot at 13:34:58 (LaTeX hold on both Editors; its caffeinate PID 44463, -ims, 9000 s from 13:35, checked holding PreventSystemSleep on AC power at 13:41:59); Uzayr's "go C" in this chat ("go C and make sure you caffeinate, i am going to eat lunch"). Launched 13:42:04, detached: staged/run_confirm_staged.sh confirm_staged 0 70 iv5_rig confirm --device mps --tag confirm_staged (main pid 45498, nice 0); every process logged at the start.
- **12 Oct 2026 14:48:56 SAST: step C, the decision, the revert and the report.** 13:42:04 to 14:47:20 (65.2 min, rc 0, not killed; main and 4 workers at nice 0; processes logged at the start and the end). Exact on mps 299 of 299, difference 0; 299 of 299 within the cap; lag at most 0.01 s; delay median 0.545, p95 0.573, max 0.585 s (worth it: at most 0.60, holds); processing after the last data median 0.220, max 0.243 s. Memory: (1) the total's slope from minute 10 2.1794 GB/h against at most 2.0625: FAILS (the growth is in the main process, 1.63 to 3.47 GB; the shipped pool's run had 1.9946); (2) the 4 workers flat (at most 4.87 MB/h, largest 98 MB): holds; (3) no swap growth, pressure 1, free at least 70 %: holds. decide_staged.py: REVERT to the shipped pool. Reverted at 14:48:19 (7a1a3de2: identify_engine.py and iv5_rig.py exactly as at 03952698). Uzayr told at once (push, 14:48), the Mastermind told. No redefinition, no re-run: the job stops here.
- **12 Oct 2026 14:57:19 SAST: APPROVED by the Mastermind** (its review of 27198bad: the revert verified, git diff 03952698 HEAD -- pipeline/ empty; its own figures match: total slope 2.179 GB/h, main 2.171; caffeinate 44463 released 14:49:16; LaTeX hold lifted 14:48). Job closed.

## Uzayr's decision after step C's result (12 Oct 2026, received in this chat at or before 15:11:44 SAST)

Written AFTER step C's result was seen (the run ended 14:47:20; the revert 7a1a3de2 at 14:48:19; the Mastermind's approval of
the revert report, recorded in adfa3b1b at 14:57:19). This is an ACCEPTANCE OF A FAILED RULE: memory rule (1) failed as fixed before the run
(2.1794 against at most 2.0625 GB/h), no rule file is changed, no rule is redefined, and there is no new run. It is the second
memory-rule decision made after a result on 12 Oct (the first: the parallel extraction's memory rule redefined after its first
confirmation run, parallel/rules2.json, 10:37:32). Recorded word for word:

> # Agent1: ship the staged extraction on step C's figures (Uzayr's decision, 12 Oct)
>
> This prompt is my decision, made after seeing the result. I accept step C's memory slope of 2.18 GB/h, which is over the 2.0625 GB/h limit fixed before the run, and the staged extraction ships with step C's figures. There is no new run and no rule is redefined. This is an acceptance of a failed rule, and it must be recorded as one.
>
> My reasons:
> - all the growth was in the main process, which is the shipped app's existing day-long growth;
> - the four workers were flat (largest 98 MB);
> - the slope has varied by about this much between runs (1.79, 1.875, 1.99, 1.99);
> - every other rule held, including exactness (299 of 299, difference 0) and the 0.60 s bar.
>
> ## Steps
> 1. **Record my decision.** In QUEUE_STAGED.md, record it word for word, with the time, as written after step C's result was seen. Commit it before changing code.
> 2. **Re-adopt the staged code** from 56eea977 by reverting 7a1a3de2.
>    - Prove that `pipeline/` is byte-identical to the code that ran in step C, using a hash of every file under `pipeline/`.
>    - engine.py stays unchanged.
>    - If anything differs, stop and report. Do not run anything.
> 3. **Update** `reports/identification/2026-10-12_staged-extraction.md`:
>    - Final decision: "KEPT on Uzayr's acceptance after the result: memory rule (1) failed as fixed (2.18 against 2.0625 GB/h)". Give my reasons above and note that this is the second memory-rule decision made after a result on 12 Oct.
>    - Add the session length the growth allows: the hours from step C's minute-10 footprint to 12 GB at 2.18 GB/h. Show the arithmetic.
>    - Replace the Editor list with step C's figures:
>      - §3.6, Figure 3.4, §4.5 and the latency table: the decision median and maximum after t0 + 4.0 s, decisions within the cap, classification, and the adaptation after the decision;
>      - the compliance row: processing after the last data, median and maximum, and the 0.5 s target, worded "met at the median and on N of 299 walks";
>      - §4.5's memory limitation line: 2.18 GB/h and the session length;
>      - a sentence for where the app is described: each window's direction and end-detector checkpoints are extracted while the window is still being received (the engine's own functions, identical outputs), and `--extract-workers 0` remains the serial fallback.
>
>    Give the source file for every figure.
> 4. **Finish.** Commit, send the Mastermind a two-line summary, and stop. The Editor list waits for the Mastermind's review.
>
> ## Not allowed
> - No new confirmation run.
> - No change to any rule file.
> - No change to engine.py.
> - No new look at test outputs.
> - Latency work is closed after this.
- **12 Oct 2026 15:14:31 SAST: re-adopted and reported on Uzayr's acceptance.** 7df749b3 reverts 7a1a3de2: every file under pipeline/ (255, SHA-256) byte-identical to 89e02559, the tree that ran step C, and engine.py unchanged from 03952698 (staged/readopt_hashes.json); nothing run. The report updated (final decision KEPT on Uzayr's acceptance after the result, memory rule (1) failed as fixed; his reasons; the second memory-rule decision after a result on 12 Oct; the session length (12 - 1.953) / 2.18 = 4.61 h from minute 10; the Editor list on step C's figures, old values as the thesis reads now). No rule file changed. Latency work closed.
- **12 Oct 2026 15:15:27 SAST: the updated report APPROVED by the Mastermind** (400531b2: git diff f756ec9d HEAD -- pipeline/ empty; the Editor list matches the run's files; the session length consistent). It tells both Editors the parallel list (0.71 s) is superseded by this report's Section 4. Job closed; latency work closed.
