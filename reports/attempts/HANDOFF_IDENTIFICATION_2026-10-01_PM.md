> **SUPERSEDED 2026-10-01 20:15 SAST** by `reports/ID_V3_DANN_2026-10-01.md` (engine v3: the current engine and figures) and `reports/ID_WINDOW_GAIT_2026-10-02.md` (the window and gait screen, to come); nothing below is changed.

# Handoff: IDENTIFICATION, 2026-10-01 afternoon (engine v2)

**For:** a fresh Claude Code session picking up identification. It should be able to act from this file
alone.

**What it supersedes:** `reports/HANDOFF_IDENTIFICATION_2026-10-01.md` (the morning's).
- Since that one, the addendum's simulated walks found a bug in the step-rate resolver.
- Uzayr adopted the fix (**engine v2**), and every figure was rebuilt on it.
- This file is the morning handoff brought up to date: every figure here is engine v2's.

**Development evaluation, all data seen.**

**State at writing (15:18):**
- **Nothing of identification's is running:** no lane, no queue and no scheduled check-in.
- The teaching pack and its report are committed with this file.
- The pack files for the new chat are listed in `reports/ID_TEACHING_PACK_2026-10-01.md` section 7.

**The briefs:**
- `reports/BRIEF_ID_TEACHING_2026-10-01.md` and its addendum `reports/BRIEF_ID_TEACHING_ADDENDUM_2026-10-01.md`
  (the teaching pack; done, `reports/ID_TEACHING_PACK_2026-10-01.md`).
- Every brief is saved verbatim as `reports/BRIEF_ID_*.md`. **Re-read a brief file before acting on it;
  never work from memory.**

## 1. The engine: what identification is now

**One model, and it is the live app.**
- The one-press engine, `pipeline/identify/engine.py`, is the only identification model.
- The bank builder, the evaluation harness and the live app all call the same code. Every thesis figure
  comes from replaying recordings through it.
- **Engine v2** (`ENGINE_VERSION = 2`) is engine v1 plus the cadence bug fix. **It is frozen again**: nothing
  that decides may change unless a new brief says so.

**From one press to one answer:**
1. **Stream.** Each receiver's frames are pushed in arrival order into a 60 s buffer.
2. **Causal clock, per receiver.**
   - The offset is the 5th percentile of (t_mono minus local time) over the frames that arrived in the
     trailing 20 s (at least 20 frames, otherwise t_mono).
   - Wraps are unwrapped. Any other backwards jump of more than 1 s is a reboot, and the estimate
     restarts.
3. **Press.** The space bar sets t0. The window is **[t0, t0 + 3.0 s]**.
4. **Decision time.** The first frame arrival at which every receiver has a frame past t0 + 3 s on the
   causal clock, or t0 + 4 s at the latest.
5. **Extract.**
   - The window goes onto a 150 Hz grid over 103 CSI entries (54 unique subcarriers).
   - **Gait features:** 630 v2 columns (`id19_featbank.pass_features`, `idz_bank.columns_v2`).
     - **Engine v2:** the step rate (cadence) that scales several feature families is resolved with only
       the channels whose autocorrelation peak is at least 0.30 voting; if none qualifies, all vote as
       before.
     - This is a scoped swap of `idmax_features.resolve_cadence` inside `engine.extract_window`
       (`engine.resolve_cadence_v2`, `CADENCE_VOTE_MIN_ACF`). The frozen module's text is unchanged.
   - **Doppler maps** (`idz_bank.conditioned_map_v2`):
     - a 4 to 70 Hz band-pass;
     - per-pass PCA, keeping PCs 2 to 4;
     - an STFT (32, 24, 64) and 28 bins from 4.7 to 68 Hz;
     - the log with a relative constant, minus the map's mean.
     - The maps are unchanged by v2 (asserted for every window).
6. **Direction.** The sign of the slope of log RX2 10 to 35 Hz energy over the window: falling means away
   (`A_fwd`), rising means towards.
7. **Wi-Fi speed.** v = f_torso x 0.123 / (2 F) on the best link (RX2 beside the TX, F = 0.98); NaN if
   F < 0.3.
   - It is the single pace column of three components.
   - Press speed is never an input.
8. **Calibration** (unsupervised, causal), from every earlier window of the session:
   - feature standardisation needs at least 10 windows, and uses training statistics until then;
   - AdaBN needs at least 1;
   - no warm-up is ever asked for.
9. **Decision.** The equal-weight sum of the eight components' log-probabilities, then the argmax. The
   displayed confidence is softmax(sum / 8).
   - **The components:**
     - random forests: per-path z, session-standardised, and with pace;
     - extra trees with pace;
     - shrinkage LDA with pace;
     - CNN-v2, plain and with AdaBN;
     - per-link CNNs with AdaBN.

**The parameters** are fixed in `runs/identify/engine/PLAN.md` (0ef1e58 before any training), with dated
notes since, the last of them on 1 Oct 13:09 (the decision) and 13:37 (the rebuild checked).

**Models** (`runs/identify/engine/models/`). **Engine v2 uses the `_x` names**; the v1 models are kept
beside them and never deleted.

| model | trained on | used for |
|---|---|---|
| `loso_A1_x` to `loso_A3_x`, `loso_B1_x`, `loso_B2_x` | every pass of the other four sessions (bank `bank_T3.0_x`) | every thesis figure, and every replay and render (never shown its own day) |
| `deploy_all5_x` | every pass of all five sessions; `manifest.json` | the rig on real boards only; never scores anything |
| `T2.5_to*_x`, `T3.5_to*_x` | T sensitivity only | information |

- **How the v2 models were made:** the five feature components were retrained on the v2 bank with the
  same rows, heads and seeds, and the CNN files were copied from the v1 model of the same name
  (`pipeline/identify/ixt_rebank.py`).
- **The manifests** carry `engine_version` 2 and `training_sessions`.
- **The live app picks v2 by itself:** `identify_engine.final_model` and `deployment_model` prefer the
  `_x` models when they exist.

**How to run it** (all from the repository root, with `OMP_NUM_THREADS=1 PYTHONPATH=.`):
- **The rig, on the boards:** `python3 -m pipeline.live.identify_engine rig --mode identify`.
  - It loads `deploy_all5_x` from its manifest.
  - Keys: SPACE when the walker starts on line A; `n` for a new walker; `q` to stop.
- **The recorded stream:** `python3 -m pipeline.live.identify_engine rig --source recorded --session B2
  [--speed 1|max] [--from <recording>]`.
  - It uses `loso_B2_x`.
  - A guard refuses any model trained on the streamed session.
- **The render:** `python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render
  natural --speed 1 --device mps`.
  - It plays B2's six natural blocks, with `--snapshots <dir>` for stills.
  - **On engine v2 its running score ends at 21 of 60 (35.00 %)**, from the verified decisions. The v1
    recording's 25 of 60 is superseded, so **it must be re-recorded**.
- **The harness** (the figures):
  1. `python3 -m pipeline.identify.ide_replay --session <s> --model <m>_x`;
  2. then `ide_eval` (writes `eval_x.json`; `--v1` reproduces v1), `ixa_measures` (writes
     `measures_x.json`) and `ixt_v2` (the tracking one-press cost).
- **Tests:** `tests/test_ide_engine.py` and `tests/test_ide_rigrun.py`, 13 in all (the slow ones need
  `IDE_SLOW=1`). All 13 pass on engine v2 (1 Oct, 12.6 minutes).
- **The decision log:** one JSON line per decision under `runs/live/identify/` (schema v2,
  `reports/ID_LIVE_INTERFACE.md`).

## 2. Every current figure (engine v2)

**Conventions:**
- Chance is 16.67 %.
- Intervals are 95 % by bootstrap over participants (10,000 resamples).
- Calibration is causal unless stated.
- "To B2" is `loso_B2_x` replaying B2.
- **Sources:**
  - `runs/identify/engine/eval/eval_x.json`;
  - `runs/identify/final_extras/measures/measures_x.json`;
  - `runs/identify/engine/eval/one_press_cost_tracking_information_x.json`.

**Identification walks, natural** (both Room B days pooled, n 180; each fold trained on the four other
sessions):

| measure | value | interval | to B2 / to B1 |
|---|---|---|---|
| **the engine (headline)** | **35.56** | [21.11, 52.78] | 35.00 / 35.83 |
| away / towards | 30.00 / 41.11 | [17.78, 42.22] / [24.44, 64.44] | |
| slow / fast | 26.67 / 26.89 | [9.17, 45.00] / [18.10, 35.00] | |
| the engine without its 3 pace components | 29.44 | [12.78, 52.78] | 31.67 / 28.33 |
| CAL-none (no same-day adaptation) | 32.78 | [16.67, 53.33] | 33.33 / 32.50 |
| adaptation adds (paired) | +2.78 | [-2.78, +8.33] | |
| CAL-others (information; not causal) | 34.44 | [21.67, 51.67] | 31.67 / 35.83 |
| the CNN components only (information) | 30.00 | [12.78, 53.33] | 31.67 / 29.17 |
| the feature components only (information) | 22.22 | [15.56, 30.00] | 26.67 / 20.00 |

**Leave one session out, tracking walks** (120 per session, route known):

| A1 | A2 | A3 | B1 | B2 | **Room A** | **Room B** |
|---|---|---|---|---|---|---|
| 30.00 | 30.83 | 30.00 | 21.67 | 25.83 | **30.28 [22.50, 37.22]** | **23.75 [18.75, 28.75]** |

Without adaptation: Room A 25.83 [13.61, 37.50], Room B 25.00 [15.00, 37.92].

**The controls** (natural; each trained on the other Room B day's identification walks):

| control | natural | slow | fast | the engine minus it, natural | the engine minus it, fast |
|---|---|---|---|---|---|
| S0: press speed (a two-press stopwatch the engine never has) | 38.33 [20.00, 61.11] | 17.50 | 16.81 | -2.78 [-26.11, +15.56] | +10.08 [-13.45, +30.25] |
| S_wifi: the engine's own Wi-Fi speed | 23.89 [12.78, 34.44] | 20.83 | 27.73 | **+11.67 [-1.67, +25.56]** | -0.84 [-18.49, +15.13] |

- The engine without pace, minus S_wifi: +5.56 [-12.22, +25.56].
- **On engine v2 the engine separates from neither speed control at natural pace.** On v1 it separated
  from S_wifi (+12.22 [0.56, 25.00]).

**Deployment measures** (natural):

| measure | value | interval | chance |
|---|---|---|---|
| top-2 | 56.11 | [42.22, 71.11] | 33.33 |
| round trip, natural | 38.89 | [21.11, 63.33] | 16.67 |
| round trip, every pace | 31.10 | [17.62, 44.71] | 16.67 |
| 3 walks | 42.59 | [24.07, 68.52] | 16.67 |
| 5 walks | 44.44 | [19.44, 72.22] | 16.67 |
| household of 2 | 70.33 | [62.11, 79.78] | 50 |
| household of 3 | 55.06 | [42.94, 68.28] | 33.33 |
| household of 4 | 45.72 | [32.50, 60.83] | 25 |
| household of 5 | 39.67 | [25.78, 56.22] | 20 |

**Accuracy by confidence coverage** (natural, ranked by displayed confidence):

| coverage | 100 % | 75 % | 50 % | 30 % | 20 % |
|---|---|---|---|---|---|
| accuracy | 35.56 | 39.26 [21.74, 60.29] | 37.78 [17.33, 61.11] | 40.74 [12.50, 71.01] | 41.67 [3.12, 77.78] |

- AUROC 0.585.
- In the top 30 %, 14 of the 22 correct answers are PA1's walks: confident mostly means PA1.

**Per person** (natural):

| PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |
|---|---|---|---|---|---|
| 30.0 | 73.3 | 10.0 | 23.3 | 36.7 | 40.0 |

- 63 of the 180 walks are named PA1.
- PA2 is 0 of 10 on B2.

**The cost of one press** (against the two-press B1 configuration, CAL-causal, paired):

| where | one press | two presses | paired |
|---|---|---|---|
| natural identification walks | 35.56 | 40.00 | -4.44 [-16.67, +7.78] |
| tracking walks, pooled | 27.67 | 35.67 | **-8.00 [-13.00, -2.33]** |
| Room A tracking walks | 30.28 | 39.44 | **-9.17 [-15.00, -1.94]** |
| Room B tracking walks | 23.75 | 30.00 | -6.25 [-15.83, +1.25] |

**The two-press reference** (the audit, 30 Sept; a frozen reference, built with the v1 resolver):
- 43.33 [26.11, 62.78] on identification walks (CAL-others), with a fast-walk lead over S0 of +21.85
  [5.00, 35.59];
- leave one session out: Room A 39.44, Room B 30.00.

**T sensitivity** (information; T stays 3.0 s):
- 2.5 s gives 32.22 [18.33, 51.67];
- **3.0 s gives 35.56**;
- 3.5 s gives 34.44 [21.11, 50.56].

**Latency** (in replay):
- a median 0.32 s after the window (90th percentile 0.39 s, maximum 1.37 s);
- a median 0.88 s before the recorded end press;
- the compute part varies from run to run (0.43 s on 30 Sept).

**Physics** (identity-blind; unchanged by v2 except the cadence):
- **direction detector:** 96.9 % on 419 identification walks;
- **Wi-Fi speed against press speed:** r 0.82 on all identification walks, 0.60 on natural walks, median
  error 0.10 m/s;
- **causal clock against the whole-file map:** 0.51 ms (99th percentile);
- **torso frequency:** 18.75 Hz measured against 19.5 Hz predicted, at bin resolution;
- **rhythm:** visible in about 30 % of natural walks;
- **cadence resolver on engine v2:**
  - simulated walks: 48 of 48 within 5 % (v1: 33 of 48);
  - real natural walks with a clear envelope: median ratio to the envelope 0.996 (v1: 0.886).

**The rig run on engine v2:** recorded B2 through the rig interface equals the harness on **299 of 299**
decisions (`runs/identify/teaching/verify_B2_x.json`). The slow tests also confirm it at speed 1, from
`--from`, and through a fake serial port.

**The teaching pack's checks** (`reports/ID_TEACHING_PACK_2026-10-01.md`):
- **substitution:** the swapped decision equals the donor's own in 91.67 % [75.00, 100.00];
- **shuffled labels:**
  - the full engine scores 20.00 % [13.33, 28.33];
  - **the feature components alone on B2 are not distinguishable from shuffled labels** (p = 0.143);
- **conditioning ablation:** no log or mean subtraction costs -10.56 [-22.78, -2.78] (separable); the subcarrier mean instead of PCA -13.89 [-29.44, 2.22]; PC1 kept -5.00; no band-pass 0.00;
- **AC2** (same day, confounded by recording): B1 55.00 [26.67, 81.67], B2 70.83 [50.00, 91.67] on natural test-cycle walks, against 35.00 and 37.50 cross-day;
- **AC3** (training without the slow and fast walks): natural -1.11 [-7.78, 7.78], slow -5.83 [-10.83, -1.67] (information; the engine unchanged).

## 3. Tried and rejected (each with its number; measured on engine v1, not re-run)

| what | result | source |
|---|---|---|
| GS (per-packet amplitude normalisation) | on 600 tracking passes, -2.00 [-4.00, +0.50]: **not adopted** | `ID_FINAL` section 1 |
| A1 precise Wi-Fi speed | physics gate r **0.697** against the 0.70 needed: **not tested** | `ID_EXTRAS` section 1 |
| A2 speed profile | 0.00 [-3.33, +3.33]: **not adopted** | same |
| A3 offset training windows | **-3.33 [-5.56, -1.11]**: worse | same |
| A4 lean correction from the training days | -0.56 [-1.67, 0.00]: **not adopted** | same |
| the 3.5 s window | information only; T stays 3.0 | `ID_FINAL` section 7 |
| a warm-up (calibration walks) | **removed by Uzayr's decision (30 Sept)** | `ID_EXTRAS` sections 4 and 6.1 |
| the audit's L1, L2, CF, FN, F1 to F3 | none met the rule | `ID_AUDIT_2026-09-30.md` |
| start-press-only with an RX2 end detector (two-press era) | -14.44 [-26.67, -2.78] | `ID_WALKS_2026-09-29.md` |

**Bugs fixed** (each adopted whatever its effect):
- **B-1:** the `dwt_6` pace proxy;
- **B-2:** the maps' log constant;
- **the app's consumer** polled the host clock instead of the stream time (30 Sept);
- **the cadence resolver** (1 Oct, engine v2).

## 4. Uzayr's decisions (dated)

| date | decision |
|---|---|
| 28 Sept | Direction change: the best cross-room, cross-day model. Pre-registration and the ship rule are dropped for development. The kept rules are no leakage and gait-based identification with pace only as one parameter (`BRIEF_ID_DIRECTION_2026-09-28.md`). |
| 29 Sept | The identification-walks brief and the audit brief. |
| 30 Sept, 09:12 | Go-ahead for the engine brief. |
| 30 Sept | **One model, and it is the live app: one press, T = 3.0 s** (`BRIEF_ID_ENGINE_2026-09-30.md`). |
| 30 Sept, 15:46 | One bounded attempt at a gain, then frozen. **Names everywhere. No warm-up, ever.** Learn only from prior sessions. The rig run is recorded B2 streamed as if live (`BRIEF_ID_EXTRAS_2026-09-30.md`). |
| 1 Oct, 09:51 | The merged handoff, then the teaching pack (`BRIEF_ID_TEACHING_2026-10-01.md`); 10:31 the addendum (AC1 to AC3). |
| **1 Oct, 13:09** | **"Option 1": the cadence bug is fixed and adopted as a bug fix (engine v2); rebuild and re-run everything on it.** |
| 1 Oct | Keep the Mac awake for jobs (`caffeinate -dimsu`); coordinate directly with Tracking (relayed by Monitor). |

## 5. Open items

1. **Re-record the render** on engine v2 (expected 21 of 60; Uzayr screen-records it; command in section 1).
2. **Thesis framing.**
   - On engine v2 the engine beats chance (35.56 [21.11, 52.78]).
   - It separates from neither speed control at natural pace.
   - Its fast-walk lead is not separable.
   - "Confident" mostly means PA1.
   - One press costs 8.00 points on the tracking walks.
   - On B2 the feature components alone are at the shuffled-label level.
3. **The two-press reference** was built with the v1 resolver. The recommendation is to keep it, labelled,
   as a frozen reference.
4. **The teaching page:** Uzayr uploads the pack files listed in `reports/ID_TEACHING_PACK_2026-10-01.md`
   section 7 to the new chat.

## 6. Names, and the tracking code-order warning

| P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|
| PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |

- **Names** have been used in every new output since 30 September. Earlier reports keep their codes.
- **Warning:** tracking uses a different code order; its page calls PA2 "P5". Never mix codes across
  the branches.

## 7. Rules that bind

- **Compute:** tracking has priority.
  - Read the root `QUEUE.md` and the process list before any job.
  - Run under `taskpolicy -c utility nice -n 19` with `OMP_NUM_THREADS=1` (and `caffeinate -dimsu` on
    1 Oct).
  - Use the GPU only when tracking is idle, and message Tracking before and after.
  - `runs/identify/audit/queue/HOLD_GPU` pauses identification's lanes between jobs.
  - Stop only identification's processes, by PID.
- **Protected:**
  - never edit `pipeline/io/`, firmware, serial code, `PREREG_*` or freeze-hashed files;
  - never modify `data/`;
  - **never overwrite banks, models or outputs.** v2 lives beside v1 under `_x` names.
- **Writing:**
  - British spelling, no em dashes;
  - figures labelled "development evaluation, all data seen";
  - existing reports are never edited: write a new dated file.
- **Git:**
  - commit named paths only (`git commit -- <paths>`), never `git add -A`;
  - check `.git/index.lock` first;
  - push after committing.
- **Rules before results:** a dated note in `runs/identify/engine/PLAN.md`, committed before any new
  measurement.

## 8. File map

| what | where |
|---|---|
| the engine (v2) | `pipeline/identify/engine.py` (80cbf0c) |
| v2 banks and models | `ixt_rebank.py`; `runs/identify/engine/bank_T{2.5,3.0,3.5}_x` (each with `build.json`), `models/*_x` |
| v1 banks and models (kept, superseded) | `runs/identify/engine/bank_T*`, `models/loso_*`, `deploy_all5`, `T*_to*` |
| replay harness; evaluation | `ide_replay.py`, `ide_eval.py`, `ixa_measures.py`, `ixt_v2.py`; replays `runs/identify/engine/replays/*_x_*`; `eval/eval_x.json` |
| the teaching pack | `reports/teaching/` (pack, notes, README, `check_png/`); builders `ixt_pack.py`, `ixt_walk.py`, `ixt_plots.py`, `ixt_readme.py` |
| the pack's checks | `ixt_select.py`, `ixt_verify.py`, `ixt_subst.py`, `ixt_shuffle.py`, `ixt_ablate.py`; `runs/identify/teaching/*_x.json`, `ablation/` |
| the addendum | `ixt_synth.py` (AC1), `ixt_cadfix.py`, `ixt_cadimpact.py`, `ixt_extra.py` (AC2, AC3); `runs/identify/teaching/synth_grid/`, `cadence_fix/`, `extra/` |
| the live app | `pipeline/live/identify_engine.py`, `pipeline/live/identify_recorded.py` |
| tests | `tests/test_ide_engine.py`, `tests/test_ide_rigrun.py` |
| the rules and their notes | `runs/identify/engine/PLAN.md` |
| reports | `ID_TEACHING_PACK_2026-10-01.md` (today), `ID_FINAL_2026-09-30.md` and `ID_EXTRAS_2026-09-30.md` (v1 figures, superseded), `ID_ARCHITECTURE_2026-09-29.md`, `ID_THESIS_SUMMARY.md` (section 13 for v2), `ID_LIVE_INTERFACE.md` |
