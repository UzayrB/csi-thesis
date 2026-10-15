# Do the static dwells help the final walking tracker? Plan, written 2026-10-06 10:34 SAST (clock read)

Brief: `BRIEF.md` in this folder (Uzayr, 6 October), with his answers of 10:3x: the Bin copy of the 1 October
retraining inputs is deleted, so rebuild what is needed; train as briefly as the design allows; drop the capped
arm if it is redundant; run under caffeinate. Committed before any training run starts.

## Part A (done before this plan)

No existing run matches the final tracker. The nearest is v2 stage 8 (15 September, `db3157f1`): a free-form
position regressor on Room A only, where walks + dwells beat walks only outside the interval on 0 of 12 pairings.
Reported in the final report, not repeated here.

## What changes between arms, and what never does

- **Trained components fed the dwells:** the five cell-classifier heads of the final tracker (`half`, `fh1s`,
  `g1s1`, `g1s2`, `g100`; `pipeline.constrained.pd_cells.do_train_d2`, cell options of `fin_A3`: shared `fuse`
  encoder, augmentation on, relative RSSI, 24 epochs). They learn from position labels through `cell_index(xy)`.
- **Unchanged in every arm:** the `half` head's `pos` regressor (copied as shipped; its output `xy_hat` is stored
  but never read by the decode), the start-of-walk readers, the pool, the relgateU gate and its 0.431 threshold,
  the HMM decoder and every decode setting (variant `relgateU+abstain+a2w0.25`).
- **No shipped file is modified.** Every model, cache and decode tree is written under this folder.

## Data

- **Walking windows:** A1, A2 and B1, exactly as the final tracker (`dataset.walking_windows`): 3,428 at the 0.5 s
  stride, 1,615 at 1 s.
- **Dwell windows (W+D only):** every `grid` window of A1 and A2 with a finite cell-centre label. The cut already
  keeps them inside each dwell's usable span (the capture records `t_start` = press + 2 s and `t_end` = press + 9 s),
  so the protocol's discards are applied. Expected 3,000 at 0.5 s and 1,500 at 1 s. They are admitted by
  relabelling `grid` as `walk` in the training process only.
- **Never trained on:** A3 or B2 of any kind (`do_train_d2` asserts this).
- **Rebuilt input:** B1's 1 s window arrays (`runs/constrained/windows_s1.0_dc2/room_B/session_B1/*.npz`) were
  deleted with the Bin. They are re-cut with the command the DC2 pipeline names (`pipeline.io.windows --stride 1.0
  --sessions B1`) into this folder first, accepted only if every new `meta.json` equals the surviving one byte for
  byte, then put back at their original path so the existing views resolve. The 1 s feature and RSSI caches are
  recomputed by the loaders into this folder's own artefact trees.

## Arms

- **W:** the final tracker's recipe, retrained.
- **W+D:** the same, plus the dwell windows.
- **W+D_cap: dropped.** The cap (dwells at most the walking count) never binds: 3,000 < 3,428 and 1,500 < 1,615,
  so W+D_cap would equal W+D.

## Seeds

Five seed sets per arm, the same in both arms. Seed set k adds 100 x k to every cell head's seed (set 0 is the
shipped seeds: 0, 0, 1, 2, 0). The run order alternates W_k, W+D_k so that every finished pair is usable.

## Evaluation

The offline decode that equals the live app on 360 of 360 walks (`pipeline.constrained.pd_repro_trace`'s build and
step functions, unchanged), with the arm's five head files copied into a scratch tree under this folder, for the
cells `fin_A3` (test A3) and `fin_B2` (test B2). The app's default model is not touched.

**Metrics,** per test session and pooled over A3 + B2 (240 walks), semi-constrained mode (one start press):
1. **headline:** committed-line error, 100 minus percent correct; with the display lock and the four edge lines
   (E_col1, E_col5, E_row1, E_row5) beside it;
2. **per-frame position error** in metres (median and mean): the tracker has no position regressor in its
   decision path, so this is the drawn dot's error on every scored frame, from the decode's own rows.

## Decision rule (fixed now)

Primary: W+D minus W on pooled committed-line error, paired by seed set. Mean difference and a 95 % t-interval over
the five seed sets (t with 4 degrees of freedom).
- **Dwells help** only if the whole interval is below zero.
- **No measurable gain** if it includes zero.
- **Dwells hurt** if the whole interval is above zero.

The lock, the edge lines, the per-frame error and the per-session splits are reported and do not change the verdict.

## Compute and safety

One GPU job at a time (`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3`, `PYTORCH_MPS_LOW_WATERMARK_RATIO=0.2`), under a
watchdog with the identification guard's thresholds (stop the job if free memory falls below 30 % or its footprint
passes 6 GB), logging here. Decodes run on the CPU while the next arm trains. `caffeinate` holds the machine awake
for the run and is stopped at the end. This is a further look at A3 and B2, made at Uzayr's request.

## Addendum, 6 October 2026: the folder moved

At Uzayr's request this folder moved from `ablations/dwell_aid_2026-10-06/` to `runs/ablations/dwell_aid_2026-10-06/`,
matching the repository rule that results live under `runs/`. Only the repository-root depth in `run.py` and
`eval_one.py` changed; nothing in the design, data or decision rule did.

## Addendum, 6 October 2026, 20:12 SAST (clock read): three seed sets instead of five

**Decision (Uzayr, for time):** the ablation stops at seed sets 0, 1 and 2. Seed sets 3 and 4 are not trained.

**What had been seen when this was decided:** three decodes only, W seed set 0 on A3 and on B2 (byte-identical to the
shipped tracker: 93.33 / 70.83 and 93.33 / 72.50) and W+D seed set 0 on B2 (79.17 committed, 56.67 lock). No other
seed set had been decoded. This is optional stopping after an early look, and it is disclosed as such.

**What does not change:** the arms, the data, the metrics and the decision rule. The primary comparison is still W+D
minus W on pooled committed-line error, paired by seed set, with a 95 % t-interval, now over three seed sets (t with 2
degrees of freedom, critical value 4.30). Help, hurt and no measurable gain keep their definitions.

**Compute:** once training ends, eight decoders instead of six.
