# MODEL_FINAL_TRACKING: the final tracker, 29 September 2026

Brief: `reports/BRIEF_tracking_attack_2026-09-28.md` (the full model attack). Development log:
`reports/DEVLOG_TRACKING_2026-09-28.md`. Stage reports: `reports/ATTACK_D{1,2,3,4,5}_CLOSING_2026-09-29.md`
and `reports/ATTACK_MIDPOINT_2026-09-29.md`.

The final test ran at 09:50 to 09:55 SAST on 29 September. It was the second and last sanctioned look
at A3 and B2. The frozen DC2 results (`reports/DC2_RESULTS_2026-09-28.md`, `reports/MODEL_FREEZE_DC2.md`)
remain the confirmatory record beside this.

## 1. Results on the test sessions (never trained on, never used for any choice)

Trained on A1, A2 and B1 only. 120 evaluated passes per session. Percent, with 95 percent intervals
from a bootstrap over passes. Configuration A throughout. On this model configuration B is identical
to A (section 4).

| test | committed | display lock | scorer lock | edge lines, committed | edge lines, display lock |
|---|---|---|---|---|---|
| **A3** (Room A, third day) | **93.33** [88.33, 97.50] | **70.83** [62.50, 79.17] | 70.83 | 67 / 100 / 100 / 100 | 50 / 100 / 83 / 83 |
| **B2** (Room B, second day) | **94.17** [90.00, 98.33] | **74.17** [65.00, 81.67] | 70.00 | 100 / 100 / 83 / 100 | 100 / 100 / 50 / 50 |
| **B2, ZERO-SHOT** (trained on A1+A2 only: a room never seen) | **83.33** [75.83, 89.17] | **49.17** [40.00, 58.33] | 50.00 | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 |

Edge lines are E_col1 / E_col5 / E_row1 / E_row5, percent correct of that line's walks.

**Against the references, on the same passes** (paired change in points, 95 percent interval):

| test | split baseline (same split, the old recipe) | change: committed | change: display lock |
|---|---|---|---|
| A3 | 88.33 / 65.00 | +5.00 [0.00, 10.00] | +5.83 [-3.35, 15.00] |
| B2 | 57.50 / 20.83 | **+36.67 [28.33, 45.00]** | **+53.33 [44.17, 61.67]** |
| B2 against the calibrated split baseline (configuration B, DC2's definition) | 65.83 / 30.00 | +28.33 [20.00, 37.50] | +44.17 [34.17, 54.17] |
| B2 against the frozen DC2 reference (trained on A1+A2+A3); an unpaired difference | 50.00 / 12.50 | +44.17 | +61.67 |

The zero-shot row is the "unseen room" figure. It uses no Room B data at all: the tracking networks,
the start-of-walk readers and every statistic come from A1+A2. It reaches 83.33 / 49.17 on B2,
against the frozen reference's 50.00 / 12.50 from a comparable setup (Room A training only). The
A1+A2+B1 model is the "adapted" figure: one day of the new room lifts B2 to 94.17 / 74.17.

## 2. Spatial resolution (the drawn dot against the truth, metres)

| test | every labelled walk window (median / p90) | walks whose lock is correct | along the true line, on windows drawn on it |
|---|---|---|---|
| A3 | 0.50 / 3.26 | **0.31 / 0.90** | **0.28 / 0.86** |
| B2 | 0.48 / 2.50 | **0.32 / 0.86** | **0.32 / 0.81** |
| B2 zero-shot | | 0.37 / 1.02 | 0.35 / 1.00 |

- **When the line is right, the dot is about 0.3 m from the truth (median), and under 0.9 m nine
  times in ten.**
- The overall p90 is set by the walks drawn on a wrong line.
- The error across the line is 0 by construction: the dot is always drawn on a taped line.

## 3. Latency

**Per-window compute: the five heads.** Each head gives one window, three links, batch 1, on this
laptop's Apple GPU. The timing uses 200 windows of a development recording (A1), with the GPU
otherwise idle (`pd_latency`, `runs/dc2_results/final/latency_heads.json`).

| heads | median | p95 | p99 | max |
|---|---|---|---|---|
| **final: shared encoder with learned fusion** | **36.9 ms** | 39.6 ms | 42.5 ms | 44.6 ms |
| before: per-link networks (15 forward passes) | 65.1 ms | 69.7 ms | 72.3 ms | 90.2 ms |

The shared encoder makes one forward pass per head where the per-link design made three. The heads
are therefore about 40 percent faster.

**The rest of the window's work** is unchanged by this attack apart from one multiply: the start terms,
the decoder step and the display.
- **The live system's own streaming harness** measured the whole per-window chain at 0.060 s median
  and 0.135 s p99, with the old heads (`reports/LIVE_SYSTEM_2026-09-25.md`, section 3).
- **This timing harness carries more overhead:** its per-link heads alone take 65 ms. So the two
  harnesses should only be compared within themselves.
- **Within this harness,** the final heads cost 57 percent of the old heads' time. The chain therefore
  stays well inside the 0.5 s stride.

**End-to-end design latency:**
- **The dot:** each 2 s window's position is its centre, and the window is complete 1.0 s later. The
  display draws two 0.5 s steps behind the newest window, which is exactly that 1.0 s, and it reads no
  future radio. **A viewer sees where the walker was about 1.0 s earlier,** plus up to one 0.5 s
  display step, plus about 0.1 s of compute.
- **The line lock** is read 2.0 s after the start press.
- **The committed answer** comes when the decoder's causal exit fires at the walk's end.

## 4. The configuration, exactly

**Data and windows (unchanged):**
- 3 receivers (RX1 to RX3), 107 subcarriers, per-packet two-half shape normalisation, Hampel filter,
  150 Hz resample, empty-room baseline subtraction;
- 2 s windows (300 x 107 per link) on the ONE press-aligned 0.5 s lattice, labelled at the centre;
- features: the 2 Hz lowpassed CSI shape plus RSSI resampled onto the window's samples.

**Input changes (D2):**
- **Relative RSSI:** each recording's RSSI minus its own mean over its idle windows before the first
  press, per link. This is causal pre-pass data (`prn_stats.json`).
- **Training augmentation:**
  - RSSI offset uniform +-5 dB per link;
  - CSI-shape scale log-uniform x0.25 to x1.5 per link;
  - a time shift uniform +-0.25 s shared by the links, edges replicated;
  - Gaussian noise, sd 0.1 in standardised units.

**Networks (D4):** five heads, each ONE shared LinkCNN encoder over the three links with a learned
fusion head.
- The encoder: 5x5 convolutions 16/32/48, BatchNorm, ReLU, max-pool, adaptive pool 3x3, dropout
  0.2, a 64-d embedding.
- The fusion head: IDHead(192 -> cells) on the three embeddings in receiver order.
- Per-link auxiliary heads, trained jointly: the loss is the fused cross entropy plus the mean of the
  three auxiliary ones.
- Inputs are standardised per link and channel on the training windows.
- The five heads:
  - `half`: 0.5 s training stride, 25 cells (1 m), seed 0;
  - `fh1s`, `g1s1`, `g1s2`: 1 s stride, 25 cells, seeds 0, 1 and 2;
  - `g100`: 1 s stride, 100 cells (0.5 m).
- Training: Adam, lr 1e-3, weight decay 1e-4, batch 64, 24 epochs. No early stopping, no mixup.
- Pooling: an equal log-opinion pool of the five heads, renormalised per window. Emission: the
  posterior over the training cell marginal (alpha 1).

**Start-of-walk readers (unchanged in kind):**
- the A2 region reader (an LDA on the position head's xy);
- the veto (an LDA on AdaBN embeddings over pre-press windows).

They come from the pooled per-link A1+A2+B1 heads (`ph_A3` / `ph_B2`); the zero-shot row uses A1+A2
heads only (`zsp_B2`).

**Decoder (D3):**
- **Unchanged:**
  - the shipped semi-bounded decoder: Config(veto, split, geometry, late entry, margin 2.0,
    null_self 0.8, exit 1 at 0.5, clock_max 8, tight chains, bout log odds -1.2756);
  - pace N(1.298, 0.123) m/s, forward only;
  - the null -7.5 nats below each window's best state plus the still-gate weight 4.0, which is
    causal: the reference is identically 0;
  - the A2 start term at weight 0.5 with the veto, family-first chain totals, and the chain prior;
  - the display lock: spread 4.5, a cap of 0.8 m per window, read at press + 2.0 s.
- **CHANGED, the relative motion gate:** each recording's 0.3 to 2 Hz band energy is multiplied by
  max(1, G0 / g_rec), and the absolute threshold 0.431 then applies.
  - g_rec is the median band energy of the recording's own idle windows before its first press.
  - G0 = 0.7542 is the same statistic's median over the ROOM A training recordings (A1+A2).

**Configuration B** (B2's calibration walk) changes nothing on this model:
- the gate's re-anchoring is superseded by the relative gate;
- the null's re-anchoring (s_B 1.167 against S_A 2.111) lands outside DC2's 3-nat guard, so it falls
  back to absolute.

The model needs only the idle radio before the first press.

**System requirements, as kept:**
- no leakage: whole-session splits, and every statistic from training data or from causal pre-pass
  data;
- every component causal, the null included;
- signal only: no pace feature, elapsed time or dead reckoning (the decoder's motion prior is the
  allowed exception);
- `data/` untouched;
- the free-movement recordings never used;
- A3 and B2 used exactly twice: the midpoint, and this.

## 5. The ablation ladder (development rotations only)

Rotations: A1+A2 -> B1 (weight 2), A1+B1 -> A2, A2+B1 -> A1; configuration A, display lock. The
objective is the weighted mean of committed + lock. Each step's paired gain is against the step
before it.

| step | objective | paired gain [95%] | B1 (c / l) | A2 (c / l) | A1 (c / l) | edges committed | edges lock |
|---|---|---|---|---|---|---|---|
| D0 baseline: the pooled per-link recipe, shipped decode | 76.04 | | 37.50 / 18.33 | 73.33 / 45.00 | 45.83 / 28.33 | 72/50/72/33 | 50/33/28/22 |
| + D2 augmentation + relative RSSI | 85.83 | +9.79 [3.54, 16.25] | 40.00 / 15.83 | 80.00 / 62.50 | 53.33 / 35.83 | 67/50/72/33 | 50/33/50/22 |
| + D3 relative motion gate | 100.21 | +14.38 [9.38, 19.79] | 53.33 / 28.33 | 80.00 / 62.50 | 57.50 / 37.50 | 67/56/78/44 | 56/33/50/28 |
| + D4 shared encoder, learned fusion | **122.50** | +22.29 [14.37, 30.83] | 59.17 / 39.17 | 94.17 / 72.50 | 75.00 / 51.67 | 67/89/89/89 | 56/39/56/56 |

From D0 to the final model: **+46.46 [37.49, 55.62]**. Pooled over the rotations, committed goes
52.22 -> 76.11 and the lock 30.56 -> 54.44.

**Tried and not adopted, each decided by the rule on the rotations:**
- per-recording normalisation (-17.71);
- mixup (+6.88 [-0.21, 13.54]);
- early stopping. The honest form takes the epoch from the other rotations and scores +9.79 alone but
  fails the edge guard; it is -3.75 on top of D2. The optimistic form, which selects the epoch on the
  scored session, looked like +15 to +33.
- link product fusion at w 0.25 / 0.5 / 1.0, and for the lock only;
- the on-a-line head;
- abstain in place of the veto (+3.33 [-0.00, 7.08]);
- the scorer lock against the display lock;
- the pace re-fit;
- re-tuned null offset, margin, A2 weight and display spread;
- attention over links (-22.29);
- the g100 head at native 0.5 m (+0.83);
- interpolated within-cell emissions (-3.75).

## 6. Hashes

SHA-256 of every final model file, the start-of-walk reader files and the code that trains and
decodes them: `runs/dc2_results/final/FINAL_HASHES.txt`, 33 files. For example:
- the `half` head, link 0: `62c8518092b57eff...`;
- the `g100` head, link 0: `9e13dd99867b16e9...`;
- `pd_arch.py`: `da28eddf0cea6c67...`;
- `pd_decode.py`: `605168a68908de79...`.

Files:
- **The final model:** `runs/dc2_results/cells/fin_A3/art_{half,fh1s,g1s1,g1s2,g100}/models/s0102B1_to_s03_*`.
  `fin_B2` holds the same weights, byte for byte, under its own tag.
- **The zero-shot model:** `runs/dc2_results/cells/zsf_B2/`.
- **Tables:** `runs/dc2_results/final/FINAL.{md,json}`, `ZERO_SHOT.{md,json}`, `latency_heads.json`.
- **How to reproduce:**
  - `runs/dc2_results/final_chain.sh`, with the stage cells in `runs/dc2_results/stage_cells.json`;
  - `python3 -m pipeline.constrained.pd_cells run --cell fin_A3 --phase prep`, then
    `python3 -m pipeline.constrained.pd_decode --cell fin_A3 --variants relgateU`.

## 7. Limits

- **Two days per room, six participants, 120 passes per test session.** The intervals are about
  +-4 to +-8 points. The ranking of these changes rests on 360 development passes per comparison.
- **The lock's edge lines on B2** (E_row1 and E_row5 at 50) remain the weakest part. So does the
  zero-shot lock's E_row1 (0 of 6).
- **The start-of-walk readers are still the old per-link pooled heads.** Retraining them on the final
  architecture was not tried.
- **Configuration B** is shown to be unnecessary for this model. It was not re-derived for it:
  S_A would need recomputing for the new heads.
