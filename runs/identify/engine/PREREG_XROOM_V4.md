# PREREG_XROOM_V4: identification across days and rooms, on tracking's split (engine v4 frozen)

Written 09 Oct 2026, 11:36 SAST, by the Third overall chat (it first messaged as code-22), from Uzayr's prompt of 9 Oct
(`prompt_overall_xroom_identification_v2.md`) and his two additions of the same morning (a fourth model, and speed
controls on the existing leave-one-session-out tracking figures). Committed before anything trains. Development
evaluation, all data seen.

## 0. What this is

Tracking answers three questions on one split: across days, across rooms, and what one day of new-room data buys. Its
deployed model trains on A1+A2+B1 and tests on A3 and B2; its zero-shot model trains on A1+A2 and tests on B2. Every
engine v4 identification figure so far comes from leave-one-session-out models that train on both rooms. This run measures
identification on tracking's split, so both halves of the thesis answer the same questions the same way.

Identification stays frozen at engine v4. This is an evaluation, not a change to any model. Untouched: `deploy_all5_v4`,
the `loso_*_v4` models, `eval_v4.json`, the live app, everything in tracking, and the report repo. New files only.

## 1. Four models, engine v4's recipe

| model | trains on | walks | role |
|---|---|---|---|
| `xr_AB_v4` | A1, A2, B1 | 600 (360 tracking, 240 identification) | tracking's deployed split |
| `xr_ABtrk_v4` | A1, A2, B1, tracking walks only | 360 | tracking's deployed split, with no identification walks |
| `xr_A_v4` | A1, A2 | 240 (tracking only) | Room A only: tracking's zero-shot split |
| `xr_B1_v4` | B1 | 360 (120 tracking, 240 identification) | Room B only: same room for B2, zero-shot for A3 |

Each trains on every walk of its sessions (`xr_ABtrk_v4`: every tracking walk). A3 and B2 never enter any training.

**The recipe is the `loso_*_v4` models' own, found by tracing their files:**
- **Five feature components** (rf, rf_prior, rf_pace_prior, et_pace_prior, lda_pace_prior) on `bank_T4.0_v4` (4.0 s
  windows), columns v2, the pace column the Wi-Fi speed at the model's alpha, as `iv4_build.models`.
- **Three CNN components** (cnn, cnn_prior, cnn_perlink_prior, from cnn3 and cnn_link0 to 2; seeds 0, 1, 2; 6,000 steps;
  mps) on the **3.0 s maps of `bank_T3.0`**. This is what every v4 model carries: `loso_<s>_v4`'s CNN files were copied
  unchanged from `loso_<s>_v3`, those from `loso_<s>_x`, and those from `loso_<s>`, trained by `ide_train` on
  `bank_T3.0` (`meta_feat_cnn.json` of each, "copied unchanged"; `logs/lane_train.log`). The maps of `bank_T3.0`,
  `bank_T3.0_x` and `bank_T3.0_v3` are one git blob (19c009ef), as are their meta files (d5746739).
- `bank_T3.0` was removed in the 6 Oct cleanup (3f3612b4). It is recovered byte for byte from git (3f3612b4^) into
  `runs/identify/engine/xroom/recovered/bank_T3.0/`, each file's hash checked against its blob, and its row order checked
  equal to `bank_T4.0_v4`'s (`recovered/RECOVERED.json`).
- Fusion: the eight components summed equally; same-day causal calibration per antenna layout (fix L); direction as
  shipped.
- **Code.** The identification code at HEAD (cec9d891) is engine v4's: `engine.py` is unchanged since b13808d8 (the v4
  build, made at 64f936a); the only other change on these files is one data path in `idmax_common.pass_inventory`
  (1d75d725, Room A's 1 s windows moved out of `data/`), which neither training nor the replay calls. The trainer
  (`idz_core`, `idv2_core`, `idw_core`, `idx_loso`, `idx_dev`, `idz_bank`, `idmax_eval`) and `ide_replay` are unchanged
  since 64f936a.
- **Wrapper:** `pipeline/identify/ixr_train.py` (explicit sessions and walk kinds; models in
  `runs/identify/engine/models/xr_*_v4/` with a manifest). **Config check, done 11:34 (no training):** given A1, A2, B1
  and B2 it gives `loso_A3_v4`'s training rows exactly (899) and its manifest config field for field (bank, cols,
  layout, fn, amp_norm, engine_T, engine_version, alpha), with seeds, steps, device and parts equal
  (`runs/identify/engine/xroom/check_config.json`, PASSED).

**End-detector alpha, by the PLAN rule on each model's training sessions only** (the alpha in {0.05, 0.1, 0.2, 0.3, 0.5}
with the smallest median |detected end - end press| on the training sessions' identification walks; ties to the smaller
75th percentile, then the smaller alpha):

| model | identification walks in training | alpha |
|---|---|---|
| `xr_AB_v4` | B1's 240 | **0.5** (median error 0.996 s; next 0.3 at 1.149 s; `window_gait/alpha.json`, fold toB2, trained on B1, recovered from git) |
| `xr_B1_v4` | B1's 240 | **0.5** (the same fit) |
| `xr_A_v4` | none | **0.5** (the prompt's rule: the value every Room A fold uses) |
| `xr_ABtrk_v4` | none | **0.5** (the same rule) |

So every model's pace column is the bank's `wifi_speed` (alpha 0.5).

## 2. Test sets

The only test sessions are A3 and B2. Each recording holds one participant; every test cell has six recordings, one
per participant.

| cell | walks | how |
|---|---|---|
| A3 tracking | 120 (all 12 lines) | route known, as `loso_tracking_known_route` |
| B2 tracking | 120 | the same |
| B2 natural | 60 | identification walks, direction detected as shipped (`checks.json`: `RULE_detected_used`) |
| B2 slow | 60 | the same |
| B2 fast | 59 | the same |

Every model scores every cell. `xr_A_v4` on B2's identification walks is a **double jump** (cross-room and cross-layout:
Room A never had RX2 beside the transmitter); the row says so.

**Replay:** `ide_replay.run` (the leave-one-session-out replay path: the session in press order through `engine.Engine`,
one start press per walk), T 4.0, on mps as `eval_v4`'s replays. Every window's features and maps must equal the bank's
row; a mismatch stops the run.

## 3. Calibration, controls, intervals

- **CAL-causal** as shipped: each walk calibrated on its own session's earlier walks in its own layout, unlabelled. No
  labelled data from a test session is ever used. **CAL-none** (the engine's `Session.classify` with an empty pool:
  training statistics, no AdaBN) in every cell, as information.
- **S0** in every cell: press speed alone, an LDA (`idv2_core.lda_proba`, as `ixa_measures.lda_one`) trained on that
  model's own training walks.
- **S_wifi** in every cell (the existing code supports it, `ixa_measures.lda_one`): the model's own Wi-Fi speed column
  alone, an LDA trained on the same walks.
- **Intervals:** the bootstrap that made `eval_v4.json` (`idw_eval._boot` and `paired`: 10,000 resamples, seed 0, paired
  on the same walks for differences). Its clusters are participants. In every test cell here each participant has exactly
  one recording (asserted when scoring), so resampling participants is resampling recordings: six clusters per cell,
  printed beside every interval. The method does not change if the intervals come out wide.

## 4. The three questions, defined now

1. **Across days, same room only:** A3 by `xr_A_v4`; B2 (tracking walks and natural walks) by `xr_B1_v4`.
2. **Across rooms, zero-shot:** B2 (tracking, natural) by `xr_A_v4`, the direction tracking reports; A3 by `xr_B1_v4`, the
   reverse. Each compared, paired, with the same-room-only model on the same walks: B2 `xr_A_v4` minus `xr_B1_v4`; A3
   `xr_B1_v4` minus `xr_A_v4`. Training sizes are stated beside the result (240 against 360).
3. **What one day of new-room data buys:** on B2, `xr_AB_v4` minus `xr_A_v4`, paired, tracking walks and natural walks;
   the same difference on A3 as information.

**Tracking's deployed split:** `xr_AB_v4` on A3 and on B2.

**Addition 1, a model that never sees an identification walk** (`xr_ABtrk_v4` with `xr_A_v4`):
- across days: A3 by `xr_ABtrk_v4` (and by `xr_A_v4`, question 1);
- across rooms: B2 by `xr_A_v4`;
- one day of new-room data: `xr_ABtrk_v4` minus `xr_A_v4` on B2 (tracking, natural), paired; A3 as information;
- **what B1's identification walks add to the tracking-path score:** `xr_AB_v4` minus `xr_ABtrk_v4`, paired, on A3
  tracking and on B2 tracking.

**Addition 2, speed controls on the existing leave-one-session-out tracking figures** (no new models): on all 600
tracking walks under the `loso_*_v4` folds (their replays), S0 (press speed, an LDA trained on each fold's own training
walks, `loso_<s>_v4/train_rows.npy`) and S_wifi (each fold model's own Wi-Fi speed column: `loso_B1_v4` alpha 0.2, the
rest 0.5), per session, per room and pooled, beside the one-press engine (30.67 pooled, Room A 32.50, Room B 27.92) and
the two-press reference of `one_press_cost_tracking_information_v4.json` (35.67, 39.44, 30.00; its inputs
`final_loso_<s>_causal.npz`, removed on 6 Oct, recovered from git 3f3612b4^). Engine minus S0 and two-press minus S0,
paired, with the same bootstrap (S_wifi differences as information). **Anchor:** the scorer must reproduce those engine
and two-press figures exactly, and `eval_v4.json`'s per-session and per-room engine figures with their intervals, before
any S0 figure is written.

## 5. What the results may claim, fixed now

- "Above chance" only if the interval's lower bound is above 16.67.
- "Beyond speed" only if engine minus S0 excludes zero on the positive side (lower bound above 0); excluding it on the
  negative side is "below speed".
- A gain or a cost is called separable only if its paired interval excludes zero.
- **No reruns, extra seeds, alpha changes, window changes or config changes, whatever the result.** A step that fails
  before producing its output (a crash, a guard kill) may be run again after a fix recorded here as a dated note; no
  completed step is run again.
- **Looks.** These are the four models' first looks at A3 and B2. The identification design, the 4.0 s window included,
  was chosen with all data seen, B2 included. Every figure here is therefore a development evaluation, unlike tracking's
  B2, and the report says so.

## 6. Leakage proof (the Mastermind's requirement)

- **Open trace:** each training runs under a Python audit hook that logs every file opened; `ixr_train audit` maps each
  to its sessions. Allowed: code, the two banks (all five sessions' rows on disk; training indexes its own rows only),
  the GS decision file, the model's own output. Anything else under the repo (another model, a replay, a recording) fails.
- **Rows:** the saved `train_rows.npy` must equal the specified rows exactly, with no A3 or B2 row.
- **Substitution:** for each model, the feature components (in full) and the CNN components (seed 0, 30 steps, CPU) are
  trained twice, on the real banks and on banks whose non-training rows are replaced (features and maps by noise; labels,
  paths and sessions shuffled; speeds random). Every output must be identical. Run after launch, before the first
  training.

## 7. Schedule and cost

The Second Overall chat's dot side holds the machine until QUIET (ETA about 15:57). Before then: code and checks of
seconds only. Launch, by a detached watcher, only when all hold twice, 60 s apart: `machine_state.py is-quiet` exits 0;
the Now paragraph does not contain STOPPED; no process with `runs/a3_clean_2026-10-08/` in its command line is alive.
QUIET with STOPPED means no launch, and the Mastermind decides.

Then: one caffeinate for the whole run, nice 10, `setopt NO_BG_NICE`, every GPU job alone with MPS watermarks 0.3 / 0.2,
a guard that kills only this run's process below 30 % free memory or above 6 GB (a Metal or MPS crash is a STOP, not a
restart), every exit code captured before it is logged.

| step | where | minutes |
|---|---|---|
| launch checks, BUSY, log | CPU, light | 2 |
| substitution check, four models | CPU, 1 process | about 5 |
| per model (four, in the order `xr_AB_v4`, `xr_A_v4`, `xr_ABtrk_v4`, `xr_B1_v4`): training (CNNs 6,000 steps x 3 seeds x 4 on mps, measured 18.6 to 20.8 min for any row count; features under 15 s) | GPU, 1 | 20.5 |
| per model: open-file audit, A3 replay (measured 72.6 s for v4), B2 replay (169.8 s), CAL-none on both | GPU, 1 | 5.5 |
| scoring (Table 1, Table 2, the speed controls; 10,000-draw bootstrap) | CPU, 1 | 2 |

About 1 h 55 min in all; launch at 15:57 gives QUIET about 17:55. Replays run on mps in sequence, not behind the
trainings on CPU, so they match `eval_v4`'s replays. Then commit and push, `eval_xroom_v4.json`, and the report
`reports/identification/2026-10-09_xroom.md` (PA codes only in its sentences).

## Notes

(Dated notes, if any, go below this line; none change sections 1 to 5.)

- **09 Oct 2026, 16:00 SAST: a guard kill, and new limits for the replay and CAL-none steps (the Mastermind's
  decision).** The run launched at 15:34:19. The substitution check PASSED (63 s, 9 of 9 identical for each model);
  `xr_AB_v4` trained (15:35:22 to 15:56:00) and its open-file audit PASSED. The next step, the A3 replay through
  `xr_AB_v4`, was killed by the memory guard at 15:57:44: footprint 6,201 MB against the 6 GB per-job limit, with 68 %
  of memory free (the footprint grew steadily as the session's calibration pool grew: the engine re-adapts its CNNs on
  every earlier walk of the layout). The killed step wrote no output; no figure exists. **New limits, the Mastermind's
  decision (option A, keep mps), for the replay and CAL-none steps only:** per-job footprint limit 12 GB,
  `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7` with `PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5`. Unchanged on every step: the 30 %
  free-memory floor (this run's own process killed), one GPU job at a time, any Metal or MPS crash a STOP. Training stays
  at 6 GB with watermarks 0.3 / 0.2. **`xr_AB_v4` is kept as trained** (not retrained), and the substitution check is not
  repeated. The run resumes from the killed step; the driver skips every step whose output exists. Sections 1 to 5 are
  unchanged. Each replay's peak footprint and the lowest free percentage go into the report.
- **09 Oct 2026, 17:25 SAST: the guard's resolution (disclosed at the Mastermind's request, 16:3x; written after the run
  ended at 17:24).** Above 10 GB, `top` prints whole gigabytes ("10G", "11G", "12G") and the guard tested
  "footprint > 12". A reading of "12G" therefore passed, so the per-job limit for the replay and CAL-none steps was in
  effect 13 GB, below the Mastermind's pre-approved 16 GB contingency. All four B2 replays read "12G" (12 to 13 GB) at
  their peak; no step read "13G"; the lowest free memory of the whole run was 44 % (the 30 % floor never came near); no
  MPS or Metal error. The guard was not changed mid-run (the Mastermind's decision: continue).
- **09 Oct 2026, 17:25 SAST: a labelling bug in the scorer, fixed (no figure changes).** `ixr_eval` tested "above
  chance" as the rounded lower bound against 100/6 (16.666...), so a lower bound printed as 16.67 passed. Section 5's
  rule is "above 16.67". One cell was affected (`xr_B1_v4` on A3 tracking, 30.00 [16.67, 46.67]), now "not above
  chance". The scoring was run again (deterministic, seconds): every figure and interval in `eval_xroom_v4.json` is
  identical to the first scoring; only that label changed (in Table 1 and in Table 2's question 2 row).
