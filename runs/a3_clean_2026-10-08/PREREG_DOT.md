# PREREG_DOT: the dot side of the A3-clean display, re-selected without A3. Written 8 October 2026, 20:54 SAST (clock read)

**Status.** A plan only: written before any dot-side run, and before the lock-side A3 decode. Its SHA-256 is recorded in
`PREREG_DOT.md.sha256` and in the commit that adds it, and it is never edited afterwards; any change before a run goes in a
dated addendum file.

**The authority:** Uzayr's reply of 8 October (about 20:30), "plan the dot side (Phase A only)". Its answers are taken as
given:
- DISP_END may be retrained, and only DISP_END, held out per rotation;
- the head offset minimises the median dot error on correct-lock frames, with ties to the larger offset;
- SHIFT_W is selected by frames within 0.5 m, with the old tie-break shown beside it;
- the order is head choice, prior, head offset, SHIFT_W, switch arm.

**Compute is NOT approved.** Nothing here runs until Uzayr approves the estimate in section 9.

**A3.** The lock-side A3 decode (A3_CLEAN_CONFIG, lock side) is A3's fourth look. If the dot side is run and A3 is then
decoded with the full A3-clean configuration, **that is A3's fifth decode, and every record of it must say so.** B2, the
zero-shot cell and every shipped file are untouched in every outcome.

## 1. What is held fixed

**The lock side at its A3-clean values** (`A3_CLEAN_CONFIG.md`, 0d1f47f3...):
- spread 2.5, soft entry, 1.0 m entry window;
- the cap of 0.80 m per window;
- the A2 term alone in the display decode.

**K1g's look-ahead (1 window) and glide.** These were chosen on the rotations only, by Uzayr's decision of 1 Oct.

**The rest of the display as shipped:** latency 2.0 s, lock at press + 2.0 s, 10 frames per second, the display lag.
The committed decision and the lock are never changed by anything here: the dot-side settings are draw-only, and every run
asserts that its committed lines and locks equal the stage's reference run, walk for walk.

## 2. Data, and the display heads

**The rotations** (weights as pd_rule):
- A1+A2 -> B1 (`d4c_fuse_0102_to_B1`), weight 2;
- A1+B1 -> A2 (`d4c_fuse_01B1_to_02`), weight 1;
- A2+B1 -> A1 (`d4c_fuse_02B1_to_01`), weight 1.

Every evaluated recording is used (18), with no fold or pairing containing session 03 or B2.

**Held-out display heads (DISP_END), one per rotation**, each trained only on that rotation's training sessions:

| rotation | head | trained on |
|---|---|---|
| A1+A2 -> B1 | `pd_dispend_zs` (`s0102_dispend_zeroshot`), reused | A1+A2 |
| A1+B1 -> A2 | new, `s01B1_dispend_rot` | A1+B1 |
| A2+B1 -> A1 | new, `s02B1_dispend_rot` | A2+B1 |

- **Reusing `pd_dispend_zs` is allowed:** it is the identical recipe. Its `train_inner` makes the same calls as
  `pd_dispend`'s: `end_labelled_windows(include_edge=False)`, `stack_all`, `cell_index` at 25 cells, `fit_link("g", 25,
  seed 0, {"aug": True, "rssi_unit": 1.0}, arch="fuse")`, relative RSSI. The training code is unchanged since 30 Sep except
  the verified 1 Oct restructure.
- **The two new heads use the same calls,** through a wrapper in this folder. It asserts the training windows' sessions
  equal the rotation's training sessions and that no calibration recording is among them, and it writes only under this
  folder (`heads/`).
- **Training:** on the GPU, one job at a time, only when the primary chat has freed it, under the watchdog pattern
  (PYTORCH_MPS_HIGH_WATERMARK_RATIO 0.3, LOW 0.2).
- **Never trained on A3 or B2.** The shipped DISP_END and the zero-shot head's files are only read.
- **Each head's emission** is scaled by its own training marginal, as `FinalEndHead` does.

## 3. The harness, and its plumbing checks

**Every dot measure is taken on the app's own drawn frames:** `pipeline.live` replays in semi mode with the causal (as it
arrives) clock, scored from the replay logs. A wrapper in this folder:
- redirects every output here;
- loads the rotation's held-out head in place of the final one;
- sets the stage's display settings by patching module attributes in its own process (`display.DISPLAY_SD_SCALE`,
  `display.SHIFT_W`, `final_model.DISPLAY_HEAD_OFFSET_S`, the `settings()` it passes) and never edits a shared file.

**Multi-variant composition.** Within one replay, the expensive part of each frame, the display decode (`night_track` on the
prefix), is shared by all variants of a stage. Each variant then composes its own frames.
- **Head choice and prior:** the display decode is given one alternative emission per variant (`display_alt_e`, with its own
  `display_alt_flatten`).
- **Head offset, SHIFT_W and the switch arms:** `compose_walk` is run per variant on the same decode.

**P1, the harness reproduces the app.** At the shipped display (spread 4.5, the shipped DISP_END, prior 0.50, offset 0.375,
SHIFT_W 0.50, arm C, K1g), the harness reproduces the existing development replays `runs/live/replay/rot*/semi_disp-K1g_causal/`
on all 18 recordings, every logged row (locks, committed lines, every dot, switches). If it fails, nothing is selected.

**P2, each variant equals its own single-variant replay.** In every stage, every variant equals its single-variant replay on
one recording per rotation, every dot row. A failure voids that stage's multi-variant run, and it is rerun one variant per
replay.

## 4. The order and the rules

Each stage holds the earlier stages at their new values and the later ones at their shipped values, with one disclosed
exception: **stages 1 and 2 run with switching off.** The app's switch is defined only for the DISP_END display
(`compose_walk` asserts it), so the pooled arm of stage 1 cannot hold arm C. The two stages being re-made (s2_display,
r3_prior) were also originally selected before switching existed. Stages 3 and 4 hold arm C, and stage 5 chooses the arm.

**Rotation weighting** throughout: (2 B1 + A2 + A1) / 4 for a percentage or a median, taken per rotation and then weighted.
**Intervals:** 95 % percentile bootstrap, 1,000 draws, seed 0, walks resampled within each rotation, weighted.

### Stage 1: head choice (8), s2_display ported

**Arms:**
- `centre_labelled`: the pooled heads' emission, as the app draws with no end head;
- `DISP_END`: the held-out head;
- `DISP_RAW`: the held-out head's own per-window output projected onto the locked line, with no transitions. This is
  s2_display's `raw_path`, implemented in the wrapper's composition.

**Gates** (an arm must pass all three):
- **(i) dwell drift:** drift on static grid dwells at most 1.25 times `centre_labelled`'s. It is s2's `dwell_drift`,
  offline, on the posteriors of the A1 and A2 test sessions' grid-dwell windows. B1 has no grid dwells, so it is not
  measured there (disclosed).
- **(iii) substitution:** no worse than `centre_labelled`. It is s2's `substitution_on_arc`, offline, on the rotations,
  substituting the next recording's emission as s2 did; the share of changed steps over the ceiling is compared.
- **(iv) causality:** the app's per-walk minimum margin is at least 0 on every walk.

**Ranking:**
1. zero jumps over 0.5 m first: frame-to-frame dot displacement over 0.5 m at 10 frames per second, summed over walks;
2. then the lowest rotation-weighted MEAN dot error, over all walks and every frame from the first decoded frame, against the
   truth at frame time minus 2.0 s (app_score's frames; s2's "position-now" error is read as the truth the frame shows
   under V1).

If no arm passes, the shipped head (DISP_END) is kept and **its label stays**.

### Stage 2: the prior (7), r3_prior ported

**Arms:** flatten 0.00, 0.25, 0.50, 0.75, 1.00 on the stage 1 head's path, and DISP_RAW.

**Measures** (r3's `motion_stats` on the app's frames from the first decoded frame, per walk):
- displacement: frame to frame;
- excess motion: the dot moved more than the truth moved plus 0.5 m;
- backwards steps over 0.5 m in along-line arc.

**THE RULE AS LAST APPLIED (selects):**
- **eligible:** excess motion under 0.5 % of frames (post-lock line switches are zero by construction with switching off);
- **then the chain** flatten 0.50, flatten 0.25, flatten 0.00. The first that is eligible AND averages at most 1.0 backwards
  step over 0.5 m per walk is chosen;
- **if none passes,** flatten 0.00.

**THE ORIGINAL RULE (shown beside it, selects nothing):** the weakest arm whose 95th percentile displacement AND
excess-motion count are no worse than flatten 0.00's.

### Stage 3: head offset (4), Uzayr's objective

**Grid:** {0.75, 0.625, 0.50, 0.375, 0.25, 0.125, 0.00} s.

**Objective:** the rotation-weighted MEDIAN dot error over correct-lock walks. The frames are every drawn frame from press
+ 2.0 s on, the anchor span included and the park excluded, against the truth at frame time minus 2.0 s (`app_score.
dot_from_press`, DOT_PREREG's frames). The offset moves the first decoded frame, so a fixed frame set is used; a set starting
at the first decoded frame would differ between candidates.

**Selection:** the lowest. Differences within 0.005 m (DOT_PREREG's tolerance) are ties, and go to the larger offset.

### Stage 4: SHIFT_W (5)

**Grid:** {0.00, 0.25, 0.50, 0.75, 1.00} strides.

**Primary:** the rotation-weighted share of frames within 0.5 m of the truth, over correct-lock walks, on the frames from the
first decoded frame (w1's frames; the truth at frame time minus 2.0 s).

**Selection:** the highest. Ties (equal to 0.01 points) go to the value closest to 0.50, the smaller change.

**Shown beside it, selects nothing: the old pre-registered tie-break.** Among the arms whose point estimate lies inside the
best arm's 95 % interval, the one whose mean signed along-line offset is closest to zero.

### Stage 5: the switch arm (6), e2_switch ported

**Arms (thetas fixed):** A (at most 1 switch, final 1.0 m), B (at most 2, final 1.5 m), C (at most 1, final 1.5 m). Each uses
the 1.5 m radius and two-check persistence. The thetas are e2's choices on s01_to_s02 and s02_to_s01, which contain no A3:
2.0 for every arm.

**The reference:** switching off (lock-final).

**Measures** (e2's definitions on the app's frames):
- time on correct line: from the lock to the end of the walk's frames;
- W2R, R2W and W2W per switch event;
- end-on-committed agreement: walks whose line drawn at walk end equals the committed line;
- switch events;
- jumps over 1.5 m.

**Rule** (e2's, with three rotations in place of nine pairings):
- **qualify:** the rotation-weighted mean paired time-on-correct delta against switching off is above zero, AND its 95 %
  interval lies above zero, AND pooled W2R > R2W;
- **pick:** the highest end-on-committed agreement;
- **within one walk per rotation of the top (3 walks):** fewer switch events, then fewer jumps over 1.5 m;
- **no arm qualifies:** switching off.

## 5. Outcome and labels

**The result** is written to `dot/SELECTION.json` and to a NEW version of `A3_CLEAN_CONFIG.md` (lock side plus dot side),
hashed and committed.

**A setting keeps its OPTIMISTIC label**, and is named, if its stage cannot be run as written. Examples:
- P1 fails;
- a head cannot be trained;
- no arm passes stage 1's gates.

## 6. Not adopted

`FINAL_CONFIG.md`, the live app's defaults (`final_model.py`, `display.py`), `runs/live/models/*.json` and every existing
result, render and report are unchanged. They are hashed before and after.

## 7. Stops

The run stops if any of these happens:
- P1 fails;
- any run's committed lines or locks differ from its stage reference;
- any input naming session 03 or B2 is opened, beyond A3's geometry-only sidecars;
- any write leaves this folder;
- system free memory falls below 25 % (pause; resume at 40 %).

## 8. Labels on every figure

"development evaluation, all data seen". The A3 decode that follows is recorded as **A3's fifth decode**.

## 9. Estimate

**My engineering, about 13 h:**

| part | hours |
|---|---|
| the held-out heads' wrapper and recipe check | 1 |
| the rotation harness, settings injection and P1 | 3 |
| DISP_RAW in the composition | 1.5 |
| multi-variant composition and P2 | 3 |
| s2's offline gates (dwell drift, substitution) | 2 |
| the frame measures (jumps, mean error, motion, within 0.5 m, signed offset, e2's quantities) | 1.5 |
| the report | 1 |

**Training:** 2 heads at about 5 min each on the GPU, one at a time. The shipped head took 7.34 min for 2,744 windows; a
two-session head has about 1,850. That is about 15 min with loading, after the GPU is free.

**CPU:** one app replay of one recording takes about 12.5 CPU-min (the 30 Sep rotation replays).

| item | CPU-h |
|---|---|
| P1, 18 recordings | 3.75 |
| five stage passes, 18 recordings each, at about 1.3 times a single replay | 24 |
| P2 spot checks | 3 |
| offline gates | 1 |
| **total** | **about 32** |

Without the multi-variant composition it would be about 83 CPU-h (21 single-variant runs x 18 recordings).

**Wall clock:** the stages are sequential (each needs the previous winner).
- **At 6 niced CPU processes:** each stage about 50 min, so about 5.5 h of compute in all.
- **At 3 processes, alongside the stride ablation's decodes:** about 10 h.

**End to end, about 19 h** (17 to 22 h), engineering first. The heads train while the harness is built.
