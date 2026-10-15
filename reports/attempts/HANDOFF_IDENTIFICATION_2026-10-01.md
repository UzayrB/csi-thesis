> **SUPERSEDED 2026-10-01 20:15 SAST** by `reports/ID_V3_DANN_2026-10-01.md` (engine v3: the current engine and figures) and `reports/ID_WINDOW_GAIT_2026-10-02.md` (the window and gait screen, to come); nothing below is changed.

# Handoff: IDENTIFICATION, 2026-10-01 09:52 SAST

**For:** a fresh Claude Code session picking up identification; it should be able to act from this file
alone.
- **It merges** `reports/ID_FINAL_2026-09-30.md` (the one-press engine) and `reports/ID_EXTRAS_2026-09-30.md`
  (the last attempt at a gain, the measures, the rig run, the render) with every decision since 28 September.
- **It supersedes** `reports/HANDOFF_IDENTIFICATION_2026-09-30.md`.
- **Development evaluation, all data seen.**
- **Nothing of identification's is running.** There is no queue, no scheduled check-in and no background
  job. The last identification commit before this file is 69fc041.

**The current brief** is `reports/BRIEF_ID_TEACHING_2026-10-01.md`: this handoff, then the teaching pack.
Every brief is saved verbatim as `reports/BRIEF_ID_*.md`. **Re-read a brief file before acting on it; never
work from memory.**

## 1. The engine: what identification is now

**One model, and it is the live app.**
- The one-press engine, `pipeline/identify/engine.py`, is the only identification model. It is **frozen**:
  nothing that decides may change unless a new brief says so.
- The bank builder, the evaluation harness and the live app all call the same code. Every thesis figure
  comes from replaying recordings through it.

**From one press to one answer:**
1. **Stream.** Each receiver's frames are pushed in arrival order into a 60 s buffer.
2. **Causal clock, per receiver.** The offset is the 5th percentile of (t_mono minus local time) over the
   frames that arrived in the trailing 20 s (at least 20 frames, otherwise t_mono).
   - Wraps are unwrapped.
   - Any other backwards jump of more than 1 s is a reboot and restarts the estimate.
3. **Press.** The space bar sets t0. The window is **[t0, t0 + 3.0 s]**.
4. **Decision time.** The first frame arrival at which every receiver has a frame past t0 + 3 s on the
   causal clock, or t0 + 4 s at the latest.
5. **Extract.**
   - The window goes onto a 150 Hz grid over 103 CSI entries (54 unique subcarriers).
   - Gait features: 630 v2 columns (`id19_featbank.pass_features`, `idz_bank.columns_v2`).
   - Doppler maps (`idz_bank.conditioned_map_v2`): 4 to 70 Hz band-pass, per-pass PCA keeping PCs 2 to 4,
     an STFT (32, 24, 64), 28 bins from 4.7 to 68 Hz, the log with a relative constant, minus the map's mean.
6. **Direction.** The sign of the slope of log RX2 10 to 35 Hz energy over the window: falling means away
   (`A_fwd`), rising means towards.
7. **Wi-Fi speed.** v = f_torso x 0.123 / (2 F) on the best link (RX2 beside the TX, F = 0.98); NaN if
   F < 0.3. It is the single pace column of three components; press speed is never an input.
8. **Calibration** (unsupervised, causal), from every earlier window of the session:
   - feature standardisation needs at least 10 windows, and uses training statistics until then;
   - AdaBN needs at least 1.
   - No warm-up is ever asked for.
9. **Decision.** The equal-weight sum of the eight components' log-probabilities, then the argmax. The
   displayed confidence is softmax(sum / 8).
   - The components: random forests (per-path z; session-standardised; with pace), extra trees with pace,
     shrinkage LDA with pace, CNN-v2 plain and with AdaBN, and per-link CNNs with AdaBN.

**The parameters** are fixed in `runs/identify/engine/PLAN.md` (committed 0ef1e58 before any training, with
dated notes since).

**Models** (`runs/identify/engine/models/`):

| model | trained on | used for |
|---|---|---|
| `loso_A1` to `loso_A3`, `loso_B1`, `loso_B2` | every pass of the other four sessions (engine bank `bank_T3.0`) | every thesis figure, and every replay and render: never shown its own day |
| `deploy_all5` | every pass of all five sessions; `manifest.json` | the rig on real boards only; never scores anything |
| `T2.5_to*`, `T3.5_to*` | T sensitivity only | information |

**How to run it** (all from the repository root, with `OMP_NUM_THREADS=1 PYTHONPATH=.`):
- **The rig, on the boards:** `python3 -m pipeline.live.identify_engine rig --mode identify`.
  - The deployment model loads from its manifest.
  - Keys: SPACE when the walker starts on line A; `n` for a new walker; `q` to stop.
- **The recorded stream:** `python3 -m pipeline.live.identify_engine rig --source recorded --session B2 [--speed 1|max]
  [--from <recording>]`.
  - It plays recorded B2 through the rig interface as if live: `CsiRecord`s in recorded `t_mono` order, and
    only the start presses as space-bar events.
  - A guard refuses any model trained on the streamed session.
- **The render:** `python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1 --device mps`.
  - It plays B2's six natural blocks and feeds everything else fast and hidden.
  - It takes about 17 minutes, 9.8 of them walks, in a window of 1,200 x 660.
  - `--snapshots <dir>` saves a still after each decision.
- **The harness** (the figures): `python3 -m pipeline.identify.ide_replay`, then `ide_eval` and
  `ixa_measures`.
- **Tests:** `tests/test_ide_engine.py` (6) and `tests/test_ide_rigrun.py` (7; the slow ones need
  `IDE_SLOW=1`). All pass.
- **The decision log:** one JSON line per decision under `runs/live/identify/` (schema v2,
  `reports/ID_LIVE_INTERFACE.md`).

## 2. Every current figure

**Conventions.** Chance is 16.67 %. Intervals are 95 % by bootstrap over participants (10,000 resamples).
Calibration is causal unless stated. "To B2" is `loso_B2` replaying B2.

**Identification walks, natural** (both Room B days pooled, n 180; each fold trained on the four other
sessions):

| measure | value | interval | to B2 / to B1 |
|---|---|---|---|
| **the engine (headline)** | **36.11** | [24.44, 52.22] | 41.67 / 33.33 |
| away / towards | 28.89 / 43.33 | [20.00, 40.00] / [28.89, 64.44] | |
| slow / fast | 24.17 / 30.25 | [6.67, 43.33] / [23.28, 35.83] | |
| the engine without its 3 pace components | 30.56 | [13.89, 53.33] | 31.67 / 30.00 |
| CAL-none (no same-day adaptation) | 32.78 | [16.11, 55.00] | 36.67 / 30.83 |
| adaptation adds (paired) | +3.33 | [-4.44, +10.56] | |
| CAL-others (information; not causal) | 36.67 | [25.56, 53.89] | 38.33 / 35.83 |

**Leave one session out, tracking walks** (120 per session, route known):

| A1 | A2 | A3 | B1 | B2 | **Room A** | **Room B** |
|---|---|---|---|---|---|---|
| 26.67 | 36.67 | 29.17 | 27.50 | 30.83 | **30.83 [22.50, 38.06]** | **29.17 [26.67, 31.67]** |

Without adaptation: Room A 27.78 [16.39, 38.06], Room B 27.50 [19.17, 37.50].

**The controls** (natural; each trained on the other Room B day's identification walks):

| control | natural | slow | fast | the engine minus it, natural | the engine minus it, fast |
|---|---|---|---|---|---|
| S0: press speed (a two-press stopwatch the engine never has) | 38.33 [20.00, 61.11] | 17.50 | 16.81 | -2.22 [-25.56, +15.56] | +13.45 [-5.04, +30.01] |
| S_wifi: the engine's own Wi-Fi speed | 23.89 [12.78, 34.44] | 20.83 | 27.73 | **+12.22 [0.56, 25.00]** | +2.52 [-10.17, +16.81] |

The engine without pace, minus S_wifi: +6.67 [-11.11, +26.11].

**Deployment measures** (natural):

| measure | value | interval | chance |
|---|---|---|---|
| top-2 | 54.44 | [40.00, 71.11] | 33.33 |
| round trip, natural (90 pairs) | 38.89 | [21.11, 62.22] | 16.67 |
| round trip, every pace (209) | 33.49 | [22.97, 44.76] | 16.67 |
| 3 walks (54 groups) | 46.30 | [27.78, 70.37] | 16.67 |
| 5 walks (36) | 44.44 | [19.44, 69.44] | 16.67 |
| household of 2 | 70.33 | [61.33, 79.89] | 50 |
| household of 3 | 54.78 | [42.89, 68.56] | 33.33 |
| household of 4 | 45.50 | [33.06, 61.28] | 25 |
| household of 5 | 39.78 | [27.56, 56.22] | 20 |

**Accuracy by confidence coverage** (natural, ranked by displayed confidence):

| coverage | 100 % | 75 % | 50 % | 30 % | 20 % |
|---|---|---|---|---|---|
| accuracy | 36.11 | 38.52 [24.62, 57.14] | 43.33 [21.97, 64.71] | 46.30 [17.39, 74.66] | 47.22 [12.12, 77.36] |

AUROC 0.60. In the top 30 %, 16 of the 25 correct answers are PA1's walks: confident mostly means PA1.

**Per person** (natural):

| PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |
|---|---|---|---|---|---|
| 33.3 | 73.3 | 16.7 | 26.7 | 33.3 | 33.3 |

63 of the 180 walks are named PA1.

**The cost of one press** (against the two-press B1 configuration, CAL-causal, paired):

| where | one press | two presses | paired |
|---|---|---|---|
| natural identification walks | 36.11 | 40.00 | -3.89 [-14.44, +5.56] |
| Room A tracking walks | 30.83 | 39.44 | **-8.61 [-15.28, -0.83]** (about 7 points from the shorter window) |
| Room B tracking walks | 29.17 | 30.00 | -0.83 [-9.58, +7.92] |

**The two-press reference** (the audit, superseded as the headline):
- 43.33 [26.11, 62.78] on identification walks (CAL-others), with a fast-walk lead over S0 of +21.85
  [5.00, 35.59];
- leave one session out: Room A 39.44 [26.11, 48.33], Room B 30.00 [19.58, 39.17].

**T sensitivity** (information; T stays 3.0 s):

| window | natural | interval |
|---|---|---|
| 2.5 s | 29.44 | [16.67, 47.78] |
| **3.0 s** | **36.11** | |
| 3.5 s | 35.56 | [26.11, 50.00] |

**Latency** (in replay):
- a median 0.42 s after the window (90th percentile 0.49 s, maximum 1.42 s);
- a median 0.86 s **before** the recorded end press.

**Physics** (identity-blind):
- **direction detector:** 96.9 % on 419 identification walks;
- **Wi-Fi speed against press speed:**
  - the current estimator: r 0.82 on all identification walks, 0.60 on natural walks, median error
    0.10 m/s;
  - A1's estimator: 0.81 and 0.697, median error 0.067 m/s;
- **causal clock against the whole-file map:** 0.51 ms (99th percentile) in the windows;
- **torso frequency:** 18.75 Hz measured against 19.5 Hz predicted on RX2, at bin resolution;
- **rhythm:** visible in about 30 % of natural walks;
- **cadence resolver:** a median 12 % low, with no step-stride confusion;
- **limb bands:** the 35 to 75 Hz band sits above the empty room in 53 % of walks but adds nothing to
  identity.

**The rig run:** recorded B2 through the rig interface equals the harness on **299 of 299** decisions. It
gives the same decisions at speed 1 and at maximum speed, from `--from`, and through a fake serial port and
the real `SerialReader` and `parse_line`. The render's running score ends at **25 of 60 (41.67 %)**.

## 3. Tried and rejected (each with its number)

| what | result | source |
|---|---|---|
| GS (per-packet amplitude normalisation) | on 600 tracking passes, -2.00 [-4.00, +0.50]: **not adopted** (its +10.00 on the identification walks, seen in the audit, did not carry over) | `ID_FINAL` section 1 |
| A1 precise Wi-Fi speed | physics gate r **0.697** against the 0.70 needed: **not tested** | `ID_EXTRAS` section 1 |
| A2 speed profile | 0.00 [-3.33, +3.33]: **not adopted** | same |
| A3 offset training windows | **-3.33 [-5.56, -1.11]**: worse | same |
| A4 lean correction from the training days | -0.56 [-1.67, 0.00]; 9 of 659 decisions change: **not adopted** | same |
| the 3.5 s window | 35.56 against 36.11: information only; T stays 3.0 (choosing on test days would be selection) | `ID_FINAL` section 7 |
| a warm-up (calibration walks) | **removed by Uzayr's decision (30 Sept)**; the engine decides from the first walk (test `test_first_walk_decides_without_warmup`) | `ID_EXTRAS` sections 4 and 6.1 |
| the audit's L1, L2, CF, FN, F1 to F3; C1 not run | none met the rule | `ID_AUDIT_2026-09-30.md` |
| start-press-only with an RX2 end detector (two-press era) | -14.44 [-26.67, -2.78] | `ID_WALKS_2026-09-29.md` |

**Bugs fixed:**
- **B-1:** the `dwt_6` pace proxy;
- **B-2:** the maps' log constant;
- **the app's consumer** polled the host clock instead of the stream time (found by the rig run, fixed 30
  Sept 16:05).

## 4. Uzayr's decisions (dated)

| date | decision |
|---|---|
| 28 Sept | Direction change: the best cross-room, cross-day model. Pre-registration and the ship rule are dropped for development. The kept rules are no leakage (whole-session splits, statistics from training or causal data) and gait-based identification with pace only as one parameter (`BRIEF_ID_DIRECTION_2026-09-28.md`). |
| 29 Sept | The identification-walks brief and the audit brief (`BRIEF_ID_WALKS`, `BRIEF_ID_AUDIT`). |
| 30 Sept, 09:12 | Go-ahead for the engine brief, accepting tracking passes replayed with their route known, and only additive lines in the shared dispatcher. |
| 30 Sept | **One model, and it is the live app: one press, T = 3.0 s.** Every thesis figure comes from replays; the design stays one-press whatever it costs (`BRIEF_ID_ENGINE_2026-09-30.md`). |
| 30 Sept, 15:46 | The engine is unfrozen for one bounded attempt at a gain, then frozen again. **Names are used everywhere. No warm-up, ever.** Learn only from prior sessions. The rig run is recorded B2 streamed as if live. Do not edit `pipeline/live/__main__.py` (`BRIEF_ID_EXTRAS_2026-09-30.md`). |
| 1 Oct | This handoff, then the teaching pack (`BRIEF_ID_TEACHING_2026-10-01.md`). |

## 5. Open items

1. **Record the render** (Uzayr screen-records it; command in section 1).
2. **Thesis framing:**
   - the engine beats its own Wi-Fi speed (+12.2) but not press speed at natural pace;
   - its fast-walk lead is not separable;
   - "confident" mostly means PA1;
   - one press costs 8.6 points on Room A's tracking walks.
3. **The teaching pack** (the current brief, Part 2).

## 6. Names, and the tracking code-order warning

| P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|
| PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |

- **Names in outputs:** used in every new output since 30 September. Earlier reports keep the codes and
  are not rewritten.
- **Warning: tracking uses a different code order.** Its page calls PA2 "P5". Never mix codes across
  the branches; use names.

## 7. Rules that bind

- **Compute:** tracking has priority.
  - Read the root `QUEUE.md` and the process list before any job.
  - Run under `taskpolicy -c utility nice -n 19` with `OMP_NUM_THREADS=1`.
  - Use the GPU only when tracking is idle.
  - Message tracking before a job (it replies "paused"), and send "done" afterwards.
  - Stop only identification's processes, by PID.
- **Protected:**
  - never edit `pipeline/io/`, firmware, serial code, `pipeline/clean/common.py`, pinned files, `PREREG_*`
    or freeze-hashed files;
  - never modify `data/`;
  - never overwrite banks, models or outputs.
- **Writing:** British spelling, no em dashes, figures labelled "development evaluation, all data seen".
- **Git:**
  - commit named paths only, never `git add -A`;
  - check `.git/index.lock` first;
  - push after committing;
  - many uncommitted tracking files share the tree, so never stage them.
- **Rules before results:** a dated note in `runs/identify/engine/PLAN.md`, committed before any new
  measurement.

## 8. File map

| what | where |
|---|---|
| the engine | `pipeline/identify/engine.py` |
| engine bank builder and clock check | `pipeline/identify/ide_bank.py`; banks `runs/identify/engine/bank_T{2.5,3.0,3.5}` (the `_gs` banks unused) |
| training; replay harness; evaluation | `ide_train.py`, `ide_replay.py`, `ide_eval.py`; replays in `runs/identify/engine/replays/`; `eval/eval.json` |
| stage 1 (GS) | `ide_gs.py`; `runs/identify/engine/stage1/result.json` |
| checks (clock, direction, speed); cadence | `ide_checks.py`, `ide_cadence.py`; `runs/identify/engine/checks/`, `cadence/` |
| the extras (A1 to A4, measures) | `ixa_data.py`, `ixa_speed.py`, `ixa_score.py`, `ixa_run.py`, `ixa_inner.py`, `ixa_a4.py`, `ixa_measures.py`; `runs/identify/final_extras/` |
| the live app | `pipeline/live/identify_engine.py` (app, screen, consumer, guard, CLI), `pipeline/live/identify_recorded.py` (the recorded source) |
| tests | `tests/test_ide_engine.py`, `tests/test_ide_rigrun.py` |
| the rules and their notes | `runs/identify/engine/PLAN.md` |
| reports | `ID_FINAL_2026-09-30.md`, `ID_EXTRAS_2026-09-30.md`, `ID_ARCHITECTURE_2026-09-29.md` (with addenda), `ID_THESIS_SUMMARY.md` (sections 12 and "Names"), `ID_LIVE_INTERFACE.md`, `CHECKIN_LOG_ID_ENGINE.md` |
| earlier records (the two-press reference) | `ID_AUDIT_2026-09-30.md`, `ID_WALKS_2026-09-29.md`, `ID_DEV_FINAL_2026-09-29.md`, `DEVLOG_ID_2026-09-28.md` |
