# The A3 dot with every display setting chosen without A3: the dot side and A3's seventh look, 9 October 2026

Written 9 October 2026, 16:57 SAST (clock read), by the Second Overall chat, for Mastermind's review before anything goes
to the report repository.

**What it builds on:**
- the 8 October record `reports/tracking/2026-10-08_a3-clean.md`, left unedited;
- Overall's lock side on the all-0.5 s heads, `reports/tracking/2026-10-09_a3-clean-0p5-and-renders.md`.

**Folder:** `runs/a3_clean_2026-10-08/`. Every figure here is development evaluation, all data seen, except the A3 rows,
which are A3's seventh look.

## 1. Outcome

- **The A3-clean display differs from the shipped one in five settings:** spread 3.0 (lock side, Overall), the pooled
  display, head offset 0.75 s, dot phase SHIFT_W 1.0 and switch arm A. Prior flatten 0.50, soft entry and the 1.0 m
  entry window are unchanged.
- **On A3** (one decode, the seventh look):
  - the committed line and the lock are identical to the shipped display on all 120 walks (92.50 % and 75.00 %);
  - the dot on correct-lock walks improves from 0.391 m to 0.304 m (paired difference -0.087 m [-0.138, -0.038]).
- **The label:** by the rule fixed before the decode (`PREREG_DOT_ADDENDUM_2.md`), the shipped A3 dot error drops
  OPTIMISTIC.
- **A render-rule failure:** the clean display breaks render rule 2a on 11 of the 120 A3 walks (section 5).

## 2. The rules, and when they were fixed

| file | what | SHA-256 | commit |
|---|---|---|---|
| `PREREG_DOT.md` | the dot side's five stages and their rules | c0fc2a7a... | cdab65c4 (8 Oct 20:56) |
| `POA_DOT.md` | plan of action, minimal form | 8caa2e61... | 49bfd69d (07:02) |
| `PREREG_DOT_ADDENDUM_1.md` | rebased on the 0.5 s ship and Overall's lock side; no DISP_RAW; the P1 exception; the switching-off reason corrected; SHIFT_W ties; A3's look count | 1b1b5b66... | 7aa5b1ff (07:44, before any run) |
| `PREREG_DOT_ADDENDUM_2.md` | the A3 dot label rule (Uzayr's words) | 58ad8cff... | cec9d891 (10:28, during stage 2) |
| `A3_CLEAN_CONFIG_FULL.json` / `.md` | the full configuration | 6e225f6a... / 5483abee... | 8986044e (15:17, before A3) |

**The lock side** is `runs/a3_clean_0p5_2026-10-09/A3_CLEAN_CONFIG_0p5.md` (d942cb16..., Overall's 2c701274): spread 3.0,
soft entry, 1.0 m window.

## 3. How it ran

**The data and the models:**
- **Rotations:** A1+A2 -> B1 (weight 2), A1+B1 -> A2 and A2+B1 -> A1, cells `f05r_*`.
- **The pool:** the shipped recipe at the 0.5 s stride and the shipped seeds, trained on each rotation's training
  sessions. Byte-checked: half (unchanged), fh1s seed 3, g1s1 seed 1, g1s2 seed 2, g100 seed 0.
- **Held-out display heads:** A1+B1 and A2+B1 trained on the GPU at 08:04 and 08:09 (1,844 and 1,850 windows, 24
  epochs). The B1 rotation used the zero-shot head (A1+A2), the identical recipe.
- **No input naming session 03 or B2** was read beyond A3's geometry-only sidecars.

**The harness:** the live app's own replay, with the display settings set in its process, and a shared replay for each
stage's arms.
- **P1** (the harness reproduces the app): passed at 08:56. All 18 rotation recordings match the 30 Sep replays row for row,
  except 468 park frames that the old Logger did not log (addendum 1's stated exception).
- **P2** (each arm of a shared replay equals its single replay) held on every stage: 6, 15, 21, 15 and 12 pairs.

**Compute:**
- 5 to 8 niced CPU processes (Uzayr raised it during the run); about 7.5 h, 07:59 to 15:31;
- one caffeinate per run segment;
- runs/MACHINE_STATE.md kept current;
- QUIET at 15:33.

## 4. The five stages (rotations, development evaluation, all data seen)

Measures on correct-lock walks unless stated; the signed offset is the dot minus the truth along the true line (negative:
behind).

**Stage 1, display head** (switching off). The gates:
- **(i) dwell drift:** held-out DISP_END 0.453 m/s against centre 0.470, ratio 0.964; passes.
- **(iii) substitution:** held-out DISP_END 0.66 against centre_labelled 0.80; DISP_END FAILS.
- **(iv) causality:** both pass.
- So **centre_labelled (the pooled display) is chosen.**

| arm | median from the press | within 0.5 m | signed offset | mean error, all walks | jumps over 0.5 m |
|---|---|---|---|---|---|
| held-out DISP_END | 0.360 m | 60.0 % | -0.334 m | 1.240 m | 88 |
| **centre_labelled** | 0.987 m | 12.2 % | -1.110 m | 1.598 m | 47 |

**Stage 2, prior flatten** (switching off). The rule as last applied chose **0.50**, the shipped value. The original rule
(shown, not adopted) would choose 0.00.

| flatten | median from the press | signed offset | excess motion |
|---|---|---|---|
| 0.00 | 0.717 m | -0.773 m | 0.00 % |
| 0.25 | 0.878 m | -0.983 m | 0.05 % |
| **0.50** | 0.987 m | -1.110 m | 0.12 % |
| 0.75 | 1.021 m | -1.160 m | 0.12 % |
| 1.00 | 1.216 m | -1.403 m | 0.27 % |

**Stage 3, head offset** (arm C). Chosen **0.75 s** (shipped 0.375), the lowest median.

| offset | median from the press | within 0.5 m | signed offset |
|---|---|---|---|
| **0.75** | 0.594 m | 39.3 % | -0.639 m |
| 0.625 | 0.726 m | 28.3 % | -0.796 m |
| 0.5 | 0.856 m | 19.0 % | -0.953 m |
| 0.375 | 0.987 m | 12.2 % | -1.110 m |
| 0.25 | 1.121 m | 7.4 % | -1.264 m |
| 0.125 | 1.250 m | 3.6 % | -1.417 m |
| 0 | 1.374 m | 2.0 % | -1.571 m |

**Stage 4, SHIFT_W** (arm C). Chosen **1.0 strides** (shipped 0.50), the highest within 0.5 m. The old tie-break would also
choose 1.0.

| SHIFT_W | within 0.5 m | median from the press | signed offset | min margin |
|---|---|---|---|---|
| 0 | 21.8 % | 0.856 m | -0.921 m | 0.50 s |
| 0.25 | 30.1 % | 0.726 m | -0.782 m | 0.50 s |
| 0.5 | 39.3 % | 0.594 m | -0.639 m | 0.50 s |
| 0.75 | 51.3 % | 0.479 m | -0.494 m | 0.375 s |
| **1.0** | 60.5 % | 0.388 m | -0.347 m | 0.25 s |

**Stage 5, switch arm.**
- **The measures:** A, B and C each qualify and are identical on every one: time on the correct line +0.065 s [+0.02,
  +0.13] against switching off; W2R 7, R2W 0, W2W 5; 227 walks ending on the committed line; 12 switch events; 2 jumps
  over 1.5 m.
- **The tie:** the rule cannot separate them, so the tie was broken by name order in code committed before the run
  (`measures.py`, d20953f3). That gives **arm A**: at most one switch, none in the final 1.0 m. Uzayr chose to use the
  committed tie-break, with no addendum.

**The lag:** the pooled display's -1.110 m is cut to -0.347 m by stages 3 and 4, a recovery of 0.763 m (69 %). Stage 3
alone recovers 0.471 m (to -0.639 m).

## 5. A3, the seventh look (one decode, 15:17:47 to 15:30:43, scored 15:31)

**The reference:** the shipped A3 replay (`runs/live/replay/final/semi_disp-K1g_causal_realtime_screen`). Overall's
lock-side A3-clean replay (the sixth look) is identical to it on every walk and dot.

| A3 | A3-clean (seventh look) | shipped |
|---|---|---|
| committed line | 92.50 % [87.50, 96.67] | 92.50 %, the same line on 120/120 walks |
| lock | 75.00 % [67.48, 82.50] | 75.00 %; paired 0.00; Overall's sixth look also 75.00 |
| edge lines, lock (E_col1 / E_col5 / E_row1 / E_row5) | 33.3 / 100 / 100 / 83.3 | identical |
| edge lines, committed | 66.7 / 66.7 / 100 / 100 | identical |
| dot, correct-lock walks: median / p90 / within 0.5 m | 0.304 m / 0.836 m / 74.2 % | 0.391 m / 0.864 m / 61.8 % |
| dot, all walks: median / p90 / within 0.5 m | 0.407 m / 2.681 m / 57.4 % | 0.534 m / 2.703 m / 47.2 % |
| dot from the press, correct-lock: median / ahead share | 0.289 m / 0.268 | 0.357 m / 0.305 |
| **render rule 2a (glide form) failures** | **11 of 120 walks** | 0 of 120 |
| other render rules (park, together, one lock) | 0 failures | 0 failures |

**The label rule** (addendum 2, computed by `a3_full.py`):
- 90 walks are lock-correct in both decodes;
- median clean 0.3044 m against shipped 0.3911 m;
- clean minus shipped -0.0866 m, 95 % [-0.1383, -0.0378] (walk-cluster bootstrap, 1,000 draws, seed 0);
- **decision: the shipped A3 dot drops OPTIMISTIC.**

**Hashes:** 144 shipped files are identical before and after the decode: FINAL_CONFIG and its .sha256, the live app's
code, the model-set JSONs, the shipped A3 replay, the zero-shot replays, the fin_*, f05_* and z05_B2 FC records, the
f05_A3 models and both DISP_END folders. The `final` model set checks clean before and after (454 files). B2 and the
zero-shot cell were not decoded.

## 6. Disclosures

1. **Render rule 2a fails on 11 of 120 A3 walks under the A3-clean display.** The 0.75 s offset shortens the glide to 0.25
   s, and SHIFT_W 1.0 places its target further along the line. So the first frame after the park (press + 2.04 to 2.09 s)
   lies 0.16 to 0.37 m along the locked line, exactly on it, against the rule's 0.15 m. No pre-registered rule covered the
   render rules.
2. **Stages 3 and 4 chose the edges of their pre-registered grids,** with the error still falling there (stage 3: 0.726
   then 0.594 m). The optimum may lie beyond them, so part of the remaining lag (-0.35 m) is set by the grid range. The
   grids were not extended (that would be post hoc).
3. **Stage 5 was a three-way tie,** broken by name order in committed code (section 4).
4. **Stage 1's gates.**
   - **Gate (i):** its "centre" is the rotation's half head alone (s2's centre head, from the d4c_fuse cells), while the
     stage-1 arm and gate (iii) use the pooled emission. This changes no outcome, since (iii) alone excludes DISP_END.
   - **Gate (iii):** the DISP_END it tests is the HELD-OUT, rotation-trained head, not the shipped one.
   - **The B1 rotation** has no grid dwells, so (i) is measured on A1 and A2 only.
5. **Stage 2:** the rule as last applied kept 0.50; the original rule would choose 0.00, the most accurate arm.
6. **Stage 3's false stop at 12:32:54.**
   - **The cause:** the "decisions identical across arms" check compared whole lock rows, and the head offset moves the
     lock row's t_dec0 by design. Every lock and committed line was identical.
   - **The fix:** the check compares the lines (a36ab239), which is what PREREG_DOT says. Stage 3's selection then ran
     from its finished replays at 12:36. The record is `dot/stage3/STOPPED.json`.
7. **Pauses:**
   - Uzayr's laptop lid, 08:23 to 08:33, SIGSTOP by this chat;
   - Mastermind's pause at Uzayr's word, 13:15:42 to 13:52:16.
   Wall-clock times of the jobs that spanned them are not comparable; no output changed.
8. **Scorer input.** `app_score` reads each summary's "timing", which the harness did not record. The first score failed
   (KeyError). It reads copies with timing marked unrecorded, and the replay files are untouched. Re-scoring the same
   logs is not another look at A3.
9. **Two commit messages carry times that were not read from the clock:**
   - 0c41c994 says 09:10 (committed 09:04);
   - 6a194b32 says 09:31 (committed 09:28).
   Every time in this report, the configuration and the RESULT was read from the clock.

## 7. For the report (no participant-level figures, so no PA codes)

> On the three development rotations (development evaluation, all data seen), a display head held out from each rotation's
> test session drew a far more accurate dot than the pooled heads (median error on correct-lock walks 0.36 m against
> 0.99 m), but its path responded to another recording's radio on 66 % of the steps where it could have, against 80 % for
> the pooled display, and it jumped more (88 against 47 jumps over 0.5 m); the pre-registered rule therefore kept the
> pooled display.

> The pooled display trails the walker (signed offset -1.11 m on correct-lock walks); re-selecting the head offset (0.375
> to 0.75 s) and the dot phase (0.5 to 1.0 strides) recovered 0.76 m of this, to -0.35 m and a median error of 0.39 m.
> Both settings lie at the edge of their pre-registered grids, so part of the remaining lag is set by the grid range.

> The three switch arms were identical on every measure on the rotations; the tie was broken by name order in code
> committed before the run, giving arm A (at most one switch, none in the final 1.0 m).

> A3 was decoded a seventh time, with every display setting chosen on the development rotations without A3 and fixed
> beforehand: committed line 92.50 % and lock 75.00 % [67.48, 82.50], both identical to the shipped display on all 120
> walks. The dot error on correct-lock walks fell from 0.391 m to 0.304 m (paired difference -0.087 m [-0.138, -0.038]),
> so by the rule fixed before the decode the shipped A3 dot error no longer carries the optimistic label.

> Under the A3-clean display, the first frame after the park lay 0.16 to 0.37 m along the locked line on 11 of the 120 A3
> walks, beyond the 0.15 m the render rules allow.

## 8. Corrections after the Mastermind's review (9 October 2026, 17:01 SAST, clock read)

Sections 1 to 7 stand as committed in 04c56b38. This section corrects them.

**The header.** Every figure in this report is development evaluation, all data seen, the A3 rows included: A3 had been
decoded six times before this, and `RESULT.json` carries both labels. The A3 rows are additionally A3's seventh look.

**The intervals for the rotation figures.** They come from the existing stage replays only, with no decode
(`dot/sentence_intervals.py`, `dot/SENTENCE_INTERVALS.json`). The method is PREREG_DOT's: a 95 % percentile bootstrap,
1,000 draws, seed 0, walks resampled within each rotation, (2 B1 + A2 + A1) / 4, paired.
- **Held-out DISP_END against the pooled display (stage 1):**
  - median error, correct-lock walks, from the press: 0.360 m [0.326, 0.399] against 0.987 m [0.934, 1.045]; paired
    -0.627 m [-0.689, -0.567];
  - jumps over 0.5 m per walk: 0.250 [0.140, 0.358] against 0.146 [0.060, 0.244]; paired +0.104 [-0.035, +0.231]. **The
    interval includes zero, so "it jumped more" in section 7 is withdrawn.**
- **The chosen configuration against the stage-1 pooled display:**
  - median error: 0.388 m [0.356, 0.424]; paired -0.599 m [-0.648, -0.548];
  - mean signed offset: -0.347 m [-0.410, -0.285] against -1.110 m [-1.174, -1.048]; recovered 0.763 m [0.744, 0.782].
- **The substitution shares (66 against 80 %)** were kept only as aggregates, so they have no interval and are dropped from
  the sentences.
- **The A3 dot levels,** from the logged A3 outputs, with the label rule's draws and no decode
  (`dot/a3/LEVEL_INTERVALS.json`): clean 0.304 m [0.271, 0.340], shipped 0.391 m [0.354, 0.435].

**The report sentences, corrected** (no semicolons, every figure with its interval). These replace section 7's.

> On the three development rotations (development evaluation, all data seen), a display head held out from each
> rotation's test session (not the shipped head) drew a far more accurate dot than the pooled heads, with a median error on
> correct-lock walks of 0.36 m [0.33, 0.40] against 0.99 m [0.93, 1.05] (paired difference -0.63 m [-0.69, -0.57]). Its
> drawn path, however, followed another recording's radio less than the pooled display's did, so the pre-registered
> substitution gate kept the pooled display. The two displays' jump rates did not differ measurably (0.25 [0.14, 0.36]
> against 0.15 [0.06, 0.24] jumps over 0.5 m per walk, paired difference +0.10 [-0.04, +0.23]).

> The pooled display trails the walker, with a mean signed offset of -1.11 m [-1.17, -1.05] on correct-lock walks.
> Re-selecting the head offset (0.375 to 0.75 s) and the dot phase (0.5 to 1.0 strides) recovered 0.76 m [0.74, 0.78] of
> this lag, leaving -0.35 m [-0.41, -0.29] and a median error of 0.39 m [0.36, 0.42]. Both settings lie at the edge of their
> pre-registered grids, so part of the remaining lag is set by the grid range.

> The three switch arms were identical on every measure on the rotations. The tie was broken by name order in code
> committed before the run, which gave arm A (at most one switch, none in the final 1.0 m).

> A3 was decoded a seventh time with the networks trained on A1, A2 and B1 and tested on A3, which they were never trained
> on, with no labelled same-day calibration and with every display setting chosen on the development rotations without A3
> and fixed beforehand (development evaluation, all data seen). The committed line was 92.50 % [87.50, 96.67] and the lock
> 75.00 % [67.48, 82.50], both identical to the shipped display on all 120 walks, as were the edge lines (lock 33.3, 100,
> 100 and 83.3 %, committed 66.7, 66.7, 100 and 100 %, for E_col1, E_col5, E_row1 and E_row5). The dot error on
> correct-lock walks fell from 0.391 m [0.354, 0.435] to 0.304 m [0.271, 0.340], a paired difference of -0.087 m
> [-0.138, -0.038], so by the rule fixed before the decode the shipped A3 dot error no longer carries the optimistic label.

> Under the A3-clean display, the first frame after the park lay 0.16 to 0.37 m along the locked line on 11 of the 120 A3
> walks, beyond the 0.15 m the render rules allow.

> The live app keeps the shipped display, because the A3-clean display breaks render rule 2a and was chosen to settle the
> A3 label, not for shipping.

> A3 stays clean in weights and fitted statistics but exposed in design choices, because decision-side choices made on
> folds that included A3 still feed the lock, and B2 remains the headline.
