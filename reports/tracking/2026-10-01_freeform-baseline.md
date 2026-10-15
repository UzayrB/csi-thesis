# Room A's free-form 2D position result: where it is, what it was, and what became of it. 1 October 2026

**The instruction:** item 3 of `reports/BRIEF_PRESENCE_PROPAGATION_2026-10-01.md`. This is a lookup; nothing was
re-run.

**In short:**
- **The result:** 1.49 to 1.50 m median error against a 2.00 m centre guess. It was written on 14 September in
  `reports/MODEL_STATE_2026-09-14.md`, and the regressor was trained on Room A sessions 01 + 02 and tested on
  session 03.
- **It was withdrawn the same afternoon:** the regressor mostly shrinks its answers towards the room centre, and a
  predictor with no CSI input matches its median.
- **The disciplined re-run of 17 to 18 September** (`rc7_static`) gives 8 to 19 % below a centre guess when trained
  and tested on standing still, and 4 to 22 % when tested on walking. It beats the centre outside noise on 2 of 3
  pairings.
- **So the thesis can use it,** with both qualifications, as the reason for the twelve-line formulation.

## 1. Where it is

**The report:** `reports/MODEL_STATE_2026-09-14.md`, "TDR-03: full state of the model, 14 September 2026".
- **Its sections:** section 0 (the summary) and section 7 (tracking results, 7.1 to 7.3).
- **When it was written:** commit `087986e` (14 Sep 13:18).
- **Where it is now:** it was removed from the working tree on 16 Sep (`ad61a00`) and is kept in git at the tags
  `archive/tracking-final-2026-09-15`, `archive/tracking-push-2026-09-15`, `archive/tracking-rescue-2026-09-16`,
  `archive/checks-2026-09-14` and `archive/v2-rebuild-2026-09-14`:

      git show archive/tracking-final-2026-09-15:reports/MODEL_STATE_2026-09-14.md

**Its source:** `testing/runs/final_tracking/results.json`, frozen on 12 September, which is cited by the
re-verification below.

## 2. The model

**The architecture** (section 4 of that report):

```
per link (x3, SHARED WEIGHTS): LinkCNN(in_channels=1, channels=(16, 32, 48), embed_dim=64, dropout=0.2) -> 64-d
fusion: feature_concat -> 192-d
head:   PositionHead(192, 64, 0.2) -> (x, y)
```

**The training:**
- **Size:** 79,600 parameters.
- **The optimiser:** Adam, learning rate 1e-3, weight decay 1e-4; batch 64.
- **Epochs:** a budget of 37, with link dropout 0.2, seed 0, on Apple MPS.
- **The operating point:** the best-validation-loss checkpoint (epoch 5). The final epoch was worse.
- **The input:** 2 s amplitude windows of the three links.
- **What it was trained on:** the standing-grid windows (25 cells). The archive's claims also give its error on
  walking windows.

## 3. The train/test partition

| split | train | test | use |
|---|---|---|---|
| `dev` | session 01 | session 02 | selection |
| `dev_reverse` | session 02 | session 01 | the reverse-night check |
| `final` | sessions 01 + 02 | **session 03** | one score |

**How the split was kept clean:**
- **No random windows:** the split was made before preprocessing, and normalisation and standardiser statistics were
  fitted on the training side only.
- **The participants:** the frozen figure used eight (including Azrah and Zaid); the recomputation used the clean six.

## 4. The exact figures, as reported on 14 September

**The frozen, pre-registered result** (eight participants, best-validation-loss checkpoint, 1,000 test windows):

| metric | value |
|---|---|
| median error | **1.50 m** |
| p90 error | 2.65 m |
| within 1 m | 29.3 % |
| random-cell baseline | 2.24 m |
| centre-guess baseline | **2.00 m** |
| final-epoch (37) selection instead | 1.724 m median, p90 3.056 m, within 1 m 22.0 % |

**The clean six, recomputed** (750 windows, 150 dwell groups):
- **Median:** **1.492 m** [1.377, 1.710].
- **p90:** 2.685 m.
- **Mean:** 1.592 m.
- **Share within 0.5 / 1.0 / 1.5 m:** 7.2 / 27.5 / 50.5 %.

**Across days:**
- **Within day 1:** 1.59 m.
- **Across a night:** 1.54 m.
- **On walking windows:** 1.48 m.

**Per participant:** 1.32 to 1.62 m.

## 5. What became of it (it must be cited with this)

### 5.1 Withdrawn the same afternoon

**Where:** `reports/checks/CHECKS_2026-09-14.md`, commit `c960e7a`, 14 Sep 14:53; in git at the same tags.

**The verdict:** "**WITHDRAWN** The 1.49 m tracking result is a position estimate. It is substantially a shrunken
centre guess."

**The measurements behind it,** on the grid dwells:
- **The shrinkage coefficient k:** 0.243 [0.19, 0.30], where prediction = centre + k (truth - centre).
- **The spread ratio** (predicted spread over true spread): x 0.63, y 0.38.
- **The correlation per axis:** r = 0.62 (x) and 0.26 (y).
- **The mean radial error:** -1.39 m, pointing inward.
- **A synthetic shrinkage predictor carrying no CSI information** reproduces the median within 0.02 m.
- **Expanding the predictions to full room scale** gives 3.37 m, worse than the 2.00 m centre guess.

**The walking arm:** k = 0.15.

**Within one session:** 2.08 m against a 2.12 m centre guess (session 01).

### 5.2 Re-verified under the later discipline, 17 to 18 September

**Where:** the stage `rc7_static`. Its results are `runs/constrained/rc7_static/results.json` and its report is
`reports/TRACKING_2026-09-18.md`, stage 7. Both are in git at the tag `pre-cleanup`; the code is
`testing/pipeline_retired/pipeline/constrained/rc7_static.py` at that tag.

**What changed in the method:**
- **The participants:** the six.
- **The grouping:** dwells kept whole, never split across train and test.
- **The centre baseline:** computed on the exact windows of each row.
- **The model:** three per-link position heads (`nets.fit_position`) at the final epoch (24), with no validation-loss
  selection, since no separate validation session existed.
- **The intervals:** a cluster bootstrap over dwells (1,000 draws, seed 0).

**Its rule:** report the relative error reduction, not the absolute margin. The 2.00 m grid baseline is analytic
(the mean distance from the centre to the 25 cell centres), and the walking baseline (about 1.8 m) describes a
different target distribution.

**Stationary regression, trained and tested on the grid, cross-day** (2 Hz lowpass):

| pairing | median error [95 %] | centre guess | reduction |
|---|---|---|---|
| s0102 to s03 | 1.620 m [1.449, 1.788] | 2.00 m | 19.0 % |
| s0103 to s02 | 1.806 m [1.657, 1.956] | 2.00 m | 9.7 % |
| s0203 to s01 | 1.838 m [1.678, 2.023] | 2.00 m | 8.1 % |

**Without the filter:** 1.649, 1.824 and 1.852 m.

**Grid-trained, tested on walking windows** (2 Hz lowpass):

| pairing | median error [95 %] | centre guess (same windows) | reduction | the then-shipped constrained decoder on the same windows |
|---|---|---|---|---|
| s0102 to s03 | 1.435 m [1.368, 1.533] | 1.838 m | 21.9 % | 1.759 m |
| s0103 to s02 | 1.566 m [1.488, 1.629] | 1.803 m | 13.2 % | |
| s0203 to s01 | 1.715 m [1.611, 1.807] | 1.783 m | 3.8 % | |

**The verdict:** "holds" (it beats the centre guess outside the 0.11 m noise floor on 2 of 3 pairings, and beats
the 17 September decoder on the same windows). The stage recorded the follow-up only as future work.

## 6. How the thesis can use it for the twelve-line formulation

**What the free-form evidence shows:** free-form 2D regression from this rig's three single-antenna amplitude links
gets little past a centre guess.
- **The 14 September figure (1.49 m):** mostly shrinkage towards the room centre, matched by a predictor with no CSI
  input.
- **The disciplined re-run:** 4 to 22 % below the centre guess across days, beating it outside noise on 2 of 3
  pairings.

**What the twelve-line formulation does instead:** it gives the decoder the room's structure, twelve taped lines.
The question becomes which line, and where along it.
- **On the live app's B2 test** (semi-constrained, display K1g): the committed line is right on 93.33 % of walks
  and the lock on 72.50 %. The drawn dot's median error is 0.30 m on correct-lock walks and 0.475 m over all walks
  (`reports/LIVE_APP_K1G_2026-10-01.md`).

**The comparison is motivation, not a matched head-to-head.**
- **Different targets:** the free-form figures are per window, on Room A's dwell or walking windows. The line
  figures are per walk and per drawn frame, on B2's walks.
- **What it supports:** free-form position from these links barely beats a centre guess, while the line
  formulation, which uses the known paths, resolves position along a line to a few tens of centimetres when the
  line is right.
