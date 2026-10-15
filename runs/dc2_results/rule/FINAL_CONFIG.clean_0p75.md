# FINAL_CONFIG: the corrected final tracker, frozen 2026-09-29 15:39 SAST, BEFORE any test decode

**Amended 2026-10-09 (section 8): every pool head is now trained on the 0.5 s stride** (Uzayr's decision of 8 October,
`runs/ablations/stride_mix_2026-10-08/DECISION_ship_0p5.md`). The cells, the heads and the weights below are the
amended ones; everything else is unchanged. The version frozen on 29 September is `FINAL_CONFIG.pre_0p5.md`.

**Amended 2026-10-10 (section 9): the live app draws the clean display** (Uzayr's decision of 10 October;
`runs/clean_display_2026-10-10/PLAN.md`). The lock's display decode is at spread 3.0 (it was 4.5); the committed
answers, the networks and the readers are unchanged. The version before it is `FINAL_CONFIG.pre_clean.md`.

This fixes the configuration of the one test (Uzayr's instructions of 29 September). Its SHA-256 is in
`FINAL_CONFIG.md.sha256` beside it. The test chain refuses to run if the hash does not match, and it checks
the hash again at its end. Nothing in this file changes after the test.

- **Selected on:** the three development rotations with the CLEAN start-of-walk readers
  (`reports/AUDIT_LEAKAGE_TRACKING_2026-09-29.md`):
  - A1+A2 -> B1, weight 2;
  - A1+B1 -> A2;
  - A2+B1 -> A1.
- **Rule:** pd_rule. The objective is the weighted mean of committed + display lock; a change is adopted
  only if the paired 95% interval is above zero and the edge guard holds.
- **Rounds:** the re-selection ran its rounds exactly as written: `rule/CR_CHOICES.md`, then round 1
  (`rule/RS_SUMMARY.md`), then round 2 (`rule/RS2_SUMMARY.md`), which adopted nothing further.
- **D2:** stays aug+rrel (Uzayr: option 2, no mixup screen).

## 1. What each model is trained on and tested on

| figure | trained and fitted on | tested on |
|---|---|---|
| main, A3 | A1+A2+B1 (cell f05_A3; fin_A3 before 9 Oct) | A3, 120 evaluated passes |
| main, B2 | A1+A2+B1 (cell f05_B2: f05_A3's weights, byte-identical; fin_B2 before 9 Oct) | B2, 120 evaluated passes, the calibration recording excluded |
| zero-shot, B2 | A1+A2 only (cell z05_B2; zsf_B2 before 9 Oct) | B2, 120 evaluated passes |

Chance is 8.33 percent, since there are 12 lines.

## 2. Networks (unchanged from `reports/MODEL_FINAL_TRACKING.md` section 4; no retraining)

**Input standardisation.** Pooled per link and channel on the training windows. D1's per-recording
normalisation was rejected: `CR_D1` -17.92 [-26.46, -9.17].

**Inputs:**
- 3 receivers, 2 s windows on the press-aligned 0.5 s lattice, labelled at the centre;
- the 2 Hz lowpassed CSI shape plus RSSI;
- **relative RSSI:** each recording's RSSI minus its own per-link mean over its idle windows before its
  first press.

**Training augmentation:**
- an RSSI offset of +-5 dB per link;
- a CSI-shape scale, log-uniform from x0.25 to x1.5;
- a time shift of +-0.25 s;
- Gaussian noise, sd 0.1.

**Architecture.** Five heads, each ONE shared LinkCNN encoder over the three links with a learned fusion
head (IDHead 192 -> cells) and a shared auxiliary head:
- `half`: 0.5 s stride, 25 cells, seed 0;
- `fh1s`, `g1s1`, `g1s2`: 0.5 s stride, 25 cells, seeds 3, 1 and 2 (the `fh1s` slot's files are named
  `s0` and hold the seed-3 network; the saved model records its seed);
- `g100`: 0.5 s stride, 100 cells, seed 0.
(Until 9 October `fh1s`, `g1s1`, `g1s2` and `g100` were trained on the 1 s stride, seeds 0, 1, 2 and 0.)

**Training.** Adam, learning rate 1e-3, weight decay 1e-4, batch 64, 24 epochs.

**Pool.** An equal log-opinion pool of the five heads. The emission is the posterior over the training
cell marginal, alpha 1.

**Weights:**
- main: `runs/dc2_results/cells/f05_A3/art_*/models/s0102B1_to_s03_*`, hashed in
  `runs/dc2_results/final/TRACE_HASHES_f05_A3.txt` (and `f05_B2`);
- zero-shot: `runs/dc2_results/cells/z05_B2/art_*/models/s0102_to_sB2_*`, hashed in `TRACE_HASHES_z05_B2.txt`;
- before 9 October: the `fin_A3`, `fin_B2` and `zsf_B2` cells, still loadable and reproducible.

## 3. Start-of-walk readers (CORRECTED)

**Training rows.** Each training session's rows come from heads trained only on the model's other
training sessions:

| model | A1 rows from | A2 rows from | B1 rows from |
|---|---|---|---|
| fin | `s02_to_s01` (A2) | `s01_to_s02` (A1) | `s0102_to_sB1` (A1+A2) |
| zero-shot | `s02_to_s01` (A2) | `s01_to_s02` (A1) | none: no B1 |

**Test side.** The V0 heads:
- fin: `ph_A3`'s per-link heads (A1+A2+B1);
- zero-shot: `4i_A3`'s (A1+A2).

**AdaBN** runs on each test recording's own idle windows before its first press.

## 4. The decoder: variant `relgateU+abstain+a2w0.25`, display lock

**The shipped semi-bounded decoder** (rb2, selected for `s0102_to_s03` on its training side, A1+A2):
- the veto structure, split, geometry and late entry;
- margin 2.0;
- null_self 0.8;
- exit 1 at 0.5;
- clock_max 8, tight chains;
- bout log odds -1.2756.

**The null** sits -7.5 nats below each window's best state, with a still-gate weight of 4.0 and a
threshold of 0.431. Its reference is identically 0, so it is causal.

**The relative motion gate (relgateU).** Each recording's 0.3 to 2 Hz band energy is multiplied by
max(1, G0 / g_rec).
- g_rec is the median over the recording's own idle windows before its first press.
- G0 is the same statistic's median over the Room A training recordings: fin A1+A2, zero-shot A1+A2.

**Start terms:**
- **the A2 start term at weight 0.25** (was 0.5);
- **abstain in place of the veto:** the reader's centred log term, added only when its top probability
  is at least 0.90, at weight 0.25 (u2_useit.term_abstain).

The committed answer takes A2 + abstain; the lock's decode takes A2 alone.

**The chain prior** is fitted on the training sessions' line counts, with family-first totals.

**THE PACE PRIOR: N(1.30341, 0.11255) m/s.**
- It is recomputed from the A1+A2 tape anchors by stage1_pace's own method, over 240 passes.
- The same method gives 1.2982 / 0.1230 over A1+A2+A3's 360 passes, which is the old constant
  N(1.298, 0.123).
- The change is +0.0054 in the mean and -0.0105 in the sd, within 0.02 m/s, so the selection was not
  re-run (Uzayr). The rotation decodes behind the evidence below used the old value.
- It is set in every module that holds it (common, decoder, decoder2, bout) through
  `pd_clean.apply_pace` (PD_PACE_MEAN, PD_PACE_SD). Record: `runs/dc2_results/final/PACE_A1A2.json`.

**The lock.** The display decode (spread 3.0 since 10 October, section 9, and 4.5 before; a cap of 0.80 m per window) with A2 alone, read at the
window that ends at press + 2.0 s. The scorer lock is not used.

**The decode outputs** are `cells/<cell>/d3/FC.relgateU+abstain+a2w0.25/` (PD_CLEAN_PREFIX=FC). Since 10 October the
lock is read at spread 3.0 from `cells/<cell>/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/` (PD_CLEAN_PREFIX=FCC, section 9),
whose committed lines equal FC's on every pass.

## 5. The rotation evidence for each choice

Clean readers; objectives are the weighted mean of committed + lock (display unless stated); paired gain
against the step before.

| choice | comparison (rule file) | base -> arm objective | paired gain [95%] | guard | decision |
|---|---|---|---|---|---|
| pooled standardisation (D1) | `CR_D1_display` | 74.38 -> 56.46 | -17.92 [-26.46, -9.17] | fails | keep pooled |
| aug + rrel (D2 confirmation) | `CR_D2_confirm_ar_display` | 74.38 -> 85.42 | +11.04 [4.79, 17.71] | holds | ADOPT |
| relgateU (D3, d1sp) | `CR_D3L_relgateU_over_ref_display` | 74.38 -> 93.33 | +18.96 [13.12, 24.79] | holds | ADOPT |
| relgateU (D3, D2 networks) | `CR_D3R_relgateU_over_ref_on_d2pc_scorer` (scorer) | 85.00 -> 98.54 | +13.54 [8.75, 18.55] | holds | ADOPT |
| abstain over relgateA (d1sp layer 2) | `CR_D3L_abstain_over_relgateA_display` | 85.83 -> 89.58 | +3.75 [1.25, 6.67] | holds | ADOPT |
| abstain over relgateU (d1sp layer 3) | `CR_D3L_abstain_over_relgateU_scorer` (scorer) | 96.88 -> 100.83 | +3.96 [0.83, 7.29] | holds | ADOPT |
| **abstain over relgateU (D2 networks)** | `CR_D3R_abstain_over_relgateU_on_d2pc_scorer` (scorer) | 98.54 -> 103.33 | +4.79 [1.04, 8.96] | holds | **ADOPT** |
| **A2 weight 0.25** | `RS_D3R_a2w0.25_over_abstain_display` | 100.62 -> 102.50 | +1.88 [0.42, 3.55] | holds | **ADOPT** |
| scorer lock over display lock | `RS2_D3R_scorer_over_display_display` | 102.50 -> 103.96 | +1.46 [-1.67, 4.79] | holds | keep the display lock |
| shared encoder, learned fusion (D4 confirmation) | `RS2_D4_confirm_fuse_display` | 102.50 -> 121.88 | +19.38 [11.25, 27.71] | holds | ADOPT |
| attention over links (D4 screen) | `RS2_D4_attn_display` | 98.54 -> 75.00 | -23.54 [-32.92, -14.17] | fails | reject |
| g100 native (D5) | `RS2_D5_g100n_on_d4c_display` | 121.88 -> 122.50 | +0.62 [-1.25, 2.29] | holds | keep |
| interpolated emissions (D5) | `RS2_D5_interp_on_d4c_display` | 121.88 -> 119.58 | -2.29 [-5.63, 1.05] | holds | keep |

**Round 2 rejected every other D3R option** on relgateU+abstain+a2w0.25:
- w0.25: -10.83;
- w0.5: -23.54;
- lw0.25: +6.88, but the guard fails;
- onhead: -2.08;
- pace re-fit: +0.62;
- off-9: 0.00;
- off-6: -4.17;
- sd3.5: -0.21;
- margin2.5: 0.00.

**The configuration's rotation objective is 121.88**, against 122.50 for the configuration first
selected. That first figure carried the leaky readers.

## 6. Provenance of the components (before the test; `runs/dc2_results/verify/provenance_*.md`)

**Fitted components.**
- **Zero-shot:** every fitted component comes from A1+A2 recordings. The check FAILS on any component
  touching B1 or B2 (Uzayr's correction: A3 is listed but not failed).
- **Main model:** every fitted component comes from A1+A2+B1. The check fails on A3 or B2.

**The test recording's own causal statistics.** The relative RSSI reference, g_rec and AdaBN each come
from that recording's idle windows before its first press.

**Design constants and where they were set:**

| constant | set on | consequence |
|---|---|---|
| pace N(1.30341, 0.11255) | A1+A2 (recomputed; section 4) | none |
| display cap 0.80 m per window | swept 2026-09-21 in f3_render on `s0102_to_s03`, A3's 120 walks (git `8590d47`): **SET ON A3** | **the A3 LOCK figure is labelled OPTIMISTIC; the B2 lock is the headline lock result.** Committed answers do not read the cap |
| display spread 4.5 | introduced 2026-09-20 with the 3 m/s ceiling in a3_lock / f3_render on the same pairing's A3 walks (git `0b18ee6`), with no independent tuning recorded: **SET ON A3 or untraceable** | treated as the cap |
| decoder configuration and null rule | the training side of `s0102_to_s03` (A1+A2) | none |
| veto and abstain thresholds and weights | selection folds `s01_to_s02` and `s02_to_s01` | none |
| the A2 weight 0.25, abstain, and every decode option | the development rotations, which include B1 | the zero-shot B2 is zero-shot in weights and fitted statistics, not in design choices |

## 7. The one test, as it will run (`runs/dc2_results/final_corrected_chain.sh relgateU+abstain+a2w0.25`)

Environment: `PD_CLEAN_PREFIX=FC`, `PD_PACE_MEAN=1.3034113357347858`, `PD_PACE_SD=0.11254567809955889`.

1. The hash of this file is checked.
2. The provenance pre-checks run: zero-shot, then main.
3. `pd_clean decode --variants relgateU+abstain+a2w0.25` runs on fin_A3, fin_B2 and zsf_B2 (clean readers).
4. The provenance post-checks run on each decode's file trace.
5. The tables are written:
   - `pd_final --name FINAL_CORRECTED`;
   - the zero-shot table, old and new;
   - the B1 gain, paired on B2 (fin_B2 minus zsf_B2 under the same decoder).

Then come the verification (substitution, shuffled radio), the teaching export, the renders, the live
gates, and the reproduction from hashes, all under this configuration.

## 8. Amendment, 9 October 2026: the all-0.5 s heads

- **What changed:** the four pool heads that were trained on the 1 s stride (`fh1s`, `g1s1`, `g1s2`, `g100`) were
  retrained on the 0.5 s stride, for the main model (A1+A2+B1) and the zero-shot model (A1+A2), by the shipped
  training function and recipe (`runs/ship_0p5_2026-10-08/`). `half` is unchanged byte for byte; retrained with the same
  wrapper it came out byte-identical, which checks the recipe.
- **Why:** simplicity, so all five heads use one stride. The stride ablation (`runs/ablations/stride_mix_2026-10-08/
  RESULTS.md`) found no measurable difference on the development rotations. It is not a performance choice, it was
  fixed before any test decode, and it ships whatever A3 and B2 show.
- **Unchanged:** the decode settings and the lock above, the display head DISP_END, the start-of-walk readers and
  their rows, the motion gate and the pace prior.
- **Cells:** `f05_A3`, `f05_B2`, `z05_B2`, registered in `runs/dc2_results/stage_cells.json` beside the old ones. Before
  the swap each new cell, holding the old heads, reproduced its old cell's record exactly (120 of 120 passes).
- **Test looks:** one decode of A3 (its fifth look) and of B2 (its fourth by the same counting; Uzayr's brief says
  second) for each model.

## 9. Amendment, 10 October 2026: the clean display

- **What changed:** the live app's display, for the main and the zero-shot model, is the A3-clean display (Uzayr's
  decision, given to the Mastermind at or before 08:31 on 10 October; plan `runs/clean_display_2026-10-10/PLAN.md`,
  5f13034c, with notes 1 to 4). Its values are `runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json` (6e225f6a), every one
  chosen without A3 and without B2:
  - no display head: the pooled heads' emission is drawn, and DISP_END is no longer loaded;
  - display prior flatten 0.50 (as before);
  - head offset 0.75 s (was 0.375 s) and dot phase SHIFT_W 1.0 (was 0.50);
  - switch arm A: theta 2.0, at most 1 switch, none in the final 1.0 m, radius 1.5 m (was arm C, final 1.5 m);
  - display spread 3.0 (was 4.5) on the display decode, which the lock reads too;
  - entry soft, 1.0 m window (as before);
  - the candidate K1gf: K1g with the glide starting at the first anchor frame, so that frame is the locked line's entry
    exactly (rule 2a as written; with the new offset and phase K1g's glide put it up to 0.37 m along the line).
- **In code:** `pipeline/live/final_model.DISPLAY_PROFILES` ("clean", the app's, and "pre_clean", the display before it,
  exactly) with `DISPLAY_PROFILE = "clean"`.
- **Unchanged:** the networks, the start-of-walk readers, the motion gate, the pace prior and every setting of the
  committed answer; the committed lines are identical on every pass. The no-press start detector stays at spread 4.5
  (PLAN_NOTE_1).
- **The lock's offline record:** `cells/<cell>/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/` (PD_CLEAN_PREFIX=FCC), beside FC.
- **Gates (records in `runs/clean_display_2026-10-10/`; 1 to 6 passed before this amendment, 7 runs on it):**
  1. hashes before (4,975 shipped files; checked again at the end, `HASHES_AFTER.json`);
  2. the live tests and the new tests;
  3. the pre_clean profile reproduces the shipped app on every row (1440 and 1396 rows);
  4. the FCC records: committed lines equal FC's on 120 of 120 in all three cells; f05_A3 equals A3's seventh look;
  5. G2 (legacy mode) EXACT against FCC on f05_A3, f05_B2 and z05_B2;
  6. A3 through the app reproduces the seventh look (PLAN_NOTE_2), with rule 2a on 120 of 120;
  7. the pre-flight on the amended app (`PREFLIGHT.json`).
- **Looks:** A3: none new (the seventh look reproduced). B2 and zero-shot B2: their FIFTH looks (the FCC decode, the semi
  replay, the no-press replay, one full-mode recording). Development evaluation, all data seen.
  - semi lock: B2 71.67 -> 71.67, zero-shot 56.67 -> 57.50;
    committed identical on 120 of 120;
  - no-press lock on the walks detected: B2 64.29 -> 66.67, zero-shot
    59.38 -> 59.38; detections and committed lines identical;
  - fully constrained: the lock equals the semi lock by construction, confirmed on one B2 recording (20 walks).
- **Model sets:** rebuilt without the display head (`runs/live/models/{final,zeroshot}.json`); the earlier ones are
  `{final,zeroshot}.pre_clean.json`.
- **The version before this amendment:** `FINAL_CONFIG.pre_clean.md` (hash in `FINAL_CONFIG.pre_clean.md.sha256`).
