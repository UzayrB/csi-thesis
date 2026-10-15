# The tracking model is the live app: its figures, its gates, and what changed. 30 September 2026

**Uzayr's instruction of 30 September:** one model, and it is the live app.
- **What that means:** every thesis figure, render and rig run now comes from `pipeline/live/`
  (`final_model.py` and its runner).
- **Offline evaluation** is a replay of the recorded packets and presses through the app, scored by
  `pipeline/live/app_score.py`.
- **The old offline code** (pd_decode, pd_render, drawn_errors) is a cross-check.

**The rules** were written and hashed before any A3 or B2 replay:
- `runs/dc2_results/rule/APP_PREREG.md` (82a6b47a...);
- addendum 1 (29aeedb5..., four display fixes);
- addendum 2 (the unconstrained mode's details).

**What stays frozen:** the 15:39 networks, readers, configuration and `FINAL_CONFIG.md`.

## 1. The three modes

| mode | the app is given | committed line | lock | a walk's frames end |
|---|---|---|---|---|
| **SEMI-CONSTRAINED** (the headline) | the radio and ONE start press per walk | at the app's own causal exit | press + 2.0 s | at the causal exit or the next start press |
| **UNCONSTRAINED** | the radio only | as semi, from the app's own detected start | detected start + 2.0 s | as semi |
| **FULLY CONSTRAINED** (an upper bound) | the radio, the start and the end press | rescored with the walk ending at the end press | as semi | at the end press |

**Never given, in any mode:**
- presses 2 to 6;
- the walk's duration;
- labels;
- pace features;
- elapsed time.

**The twelve-line assumption holds throughout.**

**The clock for every figure:** the as-it-arrives fit (`--clock causal`), as on the rig.

## 2. The figures

**Where they come from.** Every figure is the app's own output, from its replay logs
(`runs/live/replay/<model>/<mode>/`), scored by `pipeline/live/app_score.py`. 120 walks per session,
calibration recordings excluded. Intervals are bootstrap over passes (1,000 draws, seed 0).

**The final model's A3 and B2 rows are the render replays themselves.** They ran at real-time pace with the
screen recorded, and their logs are byte-identical to a replay at full speed without the screen (tested on
B1).

### 2.1 SEMI-CONSTRAINED, the headline (one start press per walk, the as-it-arrives clock)

| test | committed | lock | never announced | answers differing from the gate |
|---|---|---|---|---|
| **B2, final model** | **93.33 [88.33, 97.50]** | **72.50 [63.33, 80.00]** | 0 | 0 of 120 |
| A3, final model | 93.33 [88.33, 97.50] | 70.83 [62.50, 79.17] (optimistic, see below) | 0 | 0 of 120 |
| B2, zero-shot model (A1+A2 only) | 80.00 [72.50, 86.67] | 49.17 [40.00, 58.33] | 0 | 0 of 120 |

**Every committed line and every lock equals the corrected offline answer,** so the as-it-arrives clock fit
moved nothing.

**The edge lines** (percent; about 6 walks each):

| test | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|
| B2, committed / lock | 100 / 100 | 100 / 100 | 100 / 50 | 100 / 50 |
| A3, committed / lock | 66.7 / 50 | 100 / 100 | 100 / 83.3 | 100 / 83.3 |
| B2 zero-shot, committed / lock | 100 / 100 | 100 / 50 | 83.3 / 0 | 100 / 33.3 |

**The displayed dot** is the dot the screen shows, at frame time x, against the truth at x - 2.0 s. It is
counted from the walk's first decoded position on.

| test | all walks: median / p90 m / within 0.5 m % | correct-lock walks: median / p90 m / within 0.5 m % | display offset (apart), median m | coverage, median |
|---|---|---|---|---|
| **B2, final** | 0.54 / 2.60 / 47.6 | **0.32 / 0.98 / 65.0** | 2.49 | 0.83 |
| A3, final | 0.61 / 2.97 / 42.2 | 0.41 / 0.98 / 58.5 (optimistic) | 2.52 | 0.83 |
| B2, zero-shot | 1.01 / 3.35 / 31.3 | 0.42 / 1.26 / 55.4 | 2.50 | 0.82 |

**Coverage** is the share of a walk's frames, between its first and last press, that carry a decoded dot.
It leaves out the 0.625 s anchor span and the frames after the app's causal exit.

**The A3 labels** (`reports/DISPLAY_PROVENANCE_2026-09-30.md`):
- **The lock:** "A3 lock (optimistic: the display spread and the soft entry were chosen on data that
  included A3; the cap is equivalent to a training-derived one)".
- **The dot error:** "A3 dot error (optimistic: the display's phase, switch arm, prior, head choice,
  spread and entry were chosen on data that included A3)".
- **B2 carries no such label.**

**When the committed line is announced,** against the walk's last press:

| test | median | p90 | maximum |
|---|---|---|---|
| B2 | 1.20 s | 1.61 s | 2.76 s |
| A3 | 1.30 s | 1.76 s | 2.36 s |
| B2 zero-shot | 1.15 s | 1.59 s | 2.69 s |

**The service time per window** (the cut, the five heads, the start terms, the decoder and the display, one
CPU thread) is in section 2.3, from a replay on a quiet machine.

### 2.2 FULLY CONSTRAINED, an upper bound (start and end presses, the as-it-arrives clock)

**The committed line is rescored with the walk ending at the end press.**
- **The rescore:** per-line Viterbi totals over the walk's windows up to the last window centred at or
  before the end press, with the chain prior and the start term, family first.
- **No offline counterpart:** the offline decoder has no end-press rescore to cross-check it against.
- **The lock:** unchanged from the semi mode.

| test | committed (rescored at the end press) | lock | the semi mode's committed |
|---|---|---|---|
| B2, final | 94.17 [89.17, 98.33] | 72.50 [63.33, 80.00] | 93.33 |
| A3, final | 93.33 [89.17, 97.50] | 70.83 [62.50, 79.17] (optimistic) | 93.33 |
| B2, zero-shot | 83.33 [76.67, 90.00] | 49.17 [40.00, 58.33] | 80.00 |

**What the end press is worth, then:**
- **B2, final model:** +1 pass (0.83 points).
- **B2, zero-shot model:** +4 passes.
- **A3:** 0 net.

**The displayed dot** (correct-lock walks, median / p90 / within 0.5 m):

| test | the displayed dot | coverage |
|---|---|---|
| B2 | 0.31 m / 0.97 m / 65.6 % | 0.85 |
| A3 (optimistic) | 0.40 m / 0.98 m / 59.2 % | 0.85 |
| B2 zero-shot | 0.41 m / 1.25 m / 56.4 % | 0.85 |

The frames run to the end press, not the causal exit, hence the coverage of 0.85.

**Every render-rule count is 0.**

### 2.3 Service time, on a quiet machine

**The run:** B2, the final model, the semi mode, the as-it-arrives clock, 13:42 to 13:57.
- **Identification** was paused at our request, and tracking's other processes were stopped by PID.
- **Where:** `runs/live/replay/final/semi_causal/`, on one CPU thread.

**Per window** (the cut, the five heads, the start terms, the decoder and the display):

| | seconds |
|---|---|
| median over recordings | 0.087 to 0.102 (pooled median 0.097) |
| p99 | 0.25 to 0.27 |
| maximum | 0.31 |

The window stride is 0.5 s, so the app keeps up with about a fifth of one thread.

**Per start press** (the re-cut and the heads on the 6 s of windows before it):
- the median is 0.83 to 0.95 s;
- the maximum is 1.8 to 3.2 s, on the recording's first press, which re-cuts every window since the start.

**What a live screen does with this.** The screen runs 2.0 s behind, so a 0.9 s press is absorbed before
the lock frame at press + 2.0 s. On the first walk of a session, the lock frame can show up to about
1.2 s late, and the queue then drains at 0.1 s per 0.5 s window. The draw lag in section 3 is the
information lag in stream time, 0.15 s at most. It does not include this compute time.

**The logs of this quiet replay are byte-identical to the render replays,** which ran at real time with
the screen on, on a busy machine: 6 of 6 recordings. So the figures do not depend on pace or load.

## 3. The gates

**All gates were run on the final app,** after the display fixes (09:56 to 11:40). Every one is exact. The
reference is the corrected offline decode (`cells/<cell>/d3/FC.relgateU+abstain+a2w0.25`). The clock is
the whole-file fit, as the offline tree was cut.

| gate | the app is given | A3 (final) | B2 (final) | B2 (zero-shot) |
|---|---|---|---|---|
| **G2, the semi gate** (Uzayr's B6) | ONE start press per walk | 120 / 120 committed, 120 / 120 locks | 120 / 120, 120 / 120 | 120 / 120, 120 / 120 |
| **G1, agreement** | start and end presses (legacy) | 120 / 120, 120 / 120 | 120 / 120, 120 / 120 | 120 / 120, 120 / 120 |

**So the semi-constrained app reproduces the corrected answers pass for pass:** A3 93.33 / 70.83, B2
93.33 / 72.50 and zero-shot B2 80.00 / 49.17. Without the end press, no decision and no lock moved.

**On the development rotations,** in legacy mode against the offline DT0 decode (Part D's precondition):
A1+A2 -> B1, A1+B1 -> A2 and A2+B1 -> A1 are each 120 / 120 committed and 120 / 120 locks.

**Files:** `runs/live/final/gate_*.json`. The pre-fix gate files are kept as `*.before_20260930.json`.

**The other checks:**
- **Real time against full speed:** the same recording replayed both ways gives byte-identical logs
  (B1 rotation, 20 walks, sha256 `eddeeadaf673...`), because nothing in the app reads a wall clock.
- **The truth cannot reach the model:** `tests/test_live_truth_isolation.py`.
  - **Static:** the truth is read only by the screen functions, and no app module reads a label.
  - **Dynamic:** true against scrambled truth gives identical outputs.
- **The render rules on every replay** (`app_score.rule_checks`): park, together, anchor, one lock, at
  most one switch, and the draw lag. **Every count is 0 on all 360 test walks.** 1, 3 and 8 switches were drawn (B2, A3, B2 zero-shot), none past one per walk; the worst draw lag is 0.15 s.

## 4. What the audit found, and what was done

**The app's inputs against the offline code (item B1):**

| # | difference | consequence | done |
|---|---|---|---|
| 1 | The stream placed the next walk's window boundary at the previous END press, and the display ended a walk's frames there | without end presses, the boundary falls back to 6.0 s before the next start press | semi mode: frames end at the causal exit or the next start. **G2 measures whether any decision moves.** |
| 2 | The replay used the whole-file clock fit by default | a fit a live system cannot have | figures use the causal fit; the file fit is used only in the equality gates |
| 3 | The instruction said "at most two switches"; the recorded arm C allows one | | kept at one, as recorded (arm C) |
| 4 | The frozen live display's head offset was 0.75 s; the final renders drew at 0.375 s | | the final model sets 0.375 s (the final renders' phase) |
| 5 | The display head's path carries the flatten 0.50 prior | display only | recorded; traced in `DISPLAY_PROVENANCE` |
| 6 | Short gaps between walks are common | the re-cut fallback is exercised | measured by G2 |
| 7 | The old dot figures (drawn_errors, 0.32 / 0.37 m) measured the pooled-evidence path before the lock and the locked path after it, with no phase and no switch. That is not the dot the screen shows | | replaced by the app's displayed dot, section 2 |

**Found while making the display follow RENDER_RULES natively (item B3; addendum 1):**
1. **Frames were computed up to one stride late.** A live screen would show the dot in 0.5 s steps.
   - **Now:** frames are drawn ahead to the next window's end.
   - **Measured:** draw lag p99 0.11 s, maximum 0.13 s, the cutting delay.
2. **Rule 2a's anchor frames were lost on every walk.** The dot stayed at the room centre for 0.6 s after
   the green marker appeared.
   - **Now:** the dot is held at the locked line's entry until the first decoded position. This is the
     live form; the offline slide read radio from after those frames.
3. **The lock was read from the walk's last composition.**
   - **Now:** THE lock is the first line drawn, and any later change is counted. There have been none.
4. **The lock frame could be lost** on about 1 walk in 20, through rounding.
   - **Now:** it waits for its window.

**Also:**
- the rig takes every SPACE as a start press in the semi mode (`reports/RIG_RUN_PROTOCOL_ADDENDUM_2026-09-30.md`);
- the banner names the mode's committed line;
- `reports/RENDER_RULES.md` is rewritten for the app.

## 5. Retired paths and replaced figures

**Retired as the source of figures:**
- `pd_decode` (the committed and lock rows);
- `pd_render` and `f3_render` / `f4_render` (the videos);
- `drawn_errors` (the dot error).

They remain as cross-checks: G1 and G2 compare against pd_decode's corrected rows.

**Renamed:** the old stand-in replay is now `python3 -m pipeline.live replay-standin`.
`python3 -m pipeline.live replay` is the app's harness (`app_replay.py`).

**Replaced figures:**

| figure | before (offline) | now (the app) |
|---|---|---|
| committed and lock, A3 / B2 / zero-shot B2 | 93.33 / 70.83, 93.33 / 72.50, 80.00 / 49.17 | the same, pass for pass: A3 93.33 / 70.83, B2 93.33 / 72.50, zero-shot B2 80.00 / 49.17 (semi-constrained, the as-it-arrives clock) |
| dot error | drawn_errors: the path's error, 0.32 / 0.37 m (median over correct-lock walks) | the displayed dot against the truth at the scene moment, section 2 |
| the render videos | f4_render | the app's screen, recorded at real-time pace (`runs/live/renders/`) |

## 6. Edits made to `data/` sidecars (item A8)

**No file under `data/` was written by any of this work.** Two earlier edits exist and are listed here.

| when | what | by | record |
|---|---|---|---|
| 2026-09-13 03:52 | 18 Room A walk sidecars gained four fields: `true_recording_day`, `same_day_duplicate`, `cohort` and `data_correction_note` (a same-day recording mislabel between two Room A participants) | push task 0, commit 7cd12eb (`pipeline/eval/push/task0.py`, item 0b) | each sidecar's own `data_correction_note`. `runs/push/task0/0b.json` was later overwritten by a `--skip-correct` run and says "skipped" |
| 2026-09-28 07:50 | `data/room_B/session_B1/participant_PA5_walk.gt.json` (P4): one spurious press removed, and passes 10 to 20 regrouped, pass 20's 5 m press estimated | the DC2 relabel | `reports/PREREG_DC2_ADDENDUM_2026-09-28_relabel.md`. The original is in `data/room_B/aborted/pa5_d1_gt_before_relabel/`; the current sha `35aeb15a...` matches |

## 7. The unconstrained mode (no press at all), appended 30 Sep 18:07

**The rules:** `rule/APP_PREREG.md` section 6 and addendum 2 (`ebb9feed`), both hashed before any run in
this mode.

**The code:** `pipeline/live/unconstrained.py`; the scoring is `app_score.score_unconstrained`.

**Every figure is the app's own:** A3 and B2 replayed with no press, the causal clock, and the display on.

**What the app does without a press:**
- **(a) The statistics:** S = 12.891 s, the 10th percentile over the 18 training walk recordings. The
  relative RSSI, the gate and AdaBN are fixed on the 22 windows inside it.
- **(b) The detector:** the full-state display decode, as `decoder2.provisional_track` runs it.
  - A walk starts after m consecutive on-line windows, at the first one's centre.
  - The start is given to the app as that walk's start press, and the rest is the semi-constrained mode.
  - A first version (binding at lag 0) never entered a line on a development recording, and was replaced
    before any m run (addendum 2).
- **(c) Matching:** a detected start matches a true walk within 1.5 s of its first press, one to one,
  nearest first.

### 7.1 The choice of m, on the rotations only

**The objective:** the rotation-weighted share of true walks detected and committed correctly. The runs
are the app on the three rotations, m = 1 to 4. The display drew no frames in the Room A grids; on B1 the
detections and committed lines were identical with and without it.

| m | objective % | B1: detected / correct-and-detected / false starts per min | A2 | A1 |
|---|---|---|---|---|
| 1 | 21.46 | 15.8 / 10.0 / 3.39 | 39.2 / 36.7 / 4.52 | 43.3 / 29.2 / 4.80 |
| 2 | 21.67 | 15.8 / 10.0 / 3.16 | 39.2 / 36.7 / 4.23 | 42.5 / 30.0 / 4.44 |
| 3 | 21.67 | 16.7 / 10.0 / 3.03 | 39.2 / 36.7 / 4.05 | 41.7 / 30.0 / 4.18 |
| **4 (chosen)** | **21.88** | 16.7 / 10.0 / 2.90 | 40.0 / 36.7 / 3.80 | 41.7 / 30.8 / 3.97 |

**The curve is flat.** m changes the false starts more than the detections.

### 7.2 The test cells (m = 4)

| | B2, final model | A3, final model | B2, zero-shot model |
|---|---|---|---|
| true walks | 120 | 120 | 120 |
| walks the app started | 183 | 385 | 164 |
| **detected** (matched within 1.5 s) | **39.2 %** (47) | 35.0 % (42) | 26.7 % (32) |
| false starts per minute, whole recording | 3.77 | 4.02 | 3.66 |
| false starts per minute, walking block | 3.77 | 3.79 | 3.66 |
| false starts per minute, standing block | none (B2 has no standing block) | 4.18 | none |
| start-time error of matched detections, median / median absolute / p90 absolute | +0.23 / 0.65 / 1.23 s | -0.04 / 0.51 / 1.30 s | +0.17 / 0.79 / 1.24 s |
| committed line correct, on matched walks | 93.6 % | 83.3 % (A3: optimistic) | 75.0 % |
| lock correct, on matched walks | 63.8 % | 54.8 % (optimistic) | 43.8 % |
| **correct-and-detected, over all walks** (the main figure) | **36.7 %** | 29.2 % | 20.0 % |
| lock-correct-and-detected, over all walks | 25.0 % | 19.2 % | 11.7 % |

**What it shows.** Without a press, the app finds about a third to two fifths of the walks within 1.5 s.
- **On the walks it finds,** its committed line is almost as good as with a press on B2 (93.6 %).
- **What limits it:** detection and false starts, roughly two false starts per true walk. A walker's own
  run-up and the standing block's cell-to-cell steps look like walks to a detector that sees no press.

### 7.3 The three modes side by side

| test | UNCONSTRAINED: correct-and-detected (committed on matched; lock on matched) | SEMI-CONSTRAINED: committed / lock | FULLY CONSTRAINED: committed / lock |
|---|---|---|---|
| B2, final | 36.7 % (93.6 %; 63.8 %) | **93.33 / 72.50** | 94.17 / 72.50 |
| A3, final (optimistic) | 29.2 % (83.3 %; 54.8 %) | 93.33 / 70.83 | 93.33 / 70.83 |
| B2, zero-shot | 20.0 % (75.0 %; 43.8 %) | 80.00 / 49.17 | 83.33 / 49.17 |

**The files:**
- `runs/live/replay/<model>/unconstrained_m4_causal/`, with `SCORE_UNCONSTRAINED_<session>.json`;
- `runs/live/unconstrained/S.json` and `M.json`;
- the grid: `runs/live/replay/rot*/unconstrained_m*_causal/`.

## 8. Files

**The code** (`pipeline/live/`):
- **The model's runner:** `final_model.py`.
  - the three modes;
  - the draw-ahead;
  - the first lock;
  - the full-mode rescore;
  - the rig mode;
  - the mode-labelled banner.
- **The replay harness:** `app_replay.py`, with the screen recorder and the V4 cut.
- **The scorer and the render-rule checks:** `app_score.py`.
- **The renders' results page:** `app_acceptance.py`.
- **The teaching pack from the app:** `app_teaching.py`.
- **The manifests:** `model_sets.py`.
- **The unconstrained mode:** `unconstrained.py`.
- **Also changed:**
  - `display.py` (rule 2a's hold);
  - `tracking.py` (the marker on the dot's frame);
  - `screen.py`, `rig.py` and `__main__.py` (the `replay` entry, and Identification's hook, added at its
    request).

**The rest of the code:**
- `pipeline/constrained/pd_dispend_zs.py` (the zero-shot display head);
- `pd_disp_prov.py` (Part D);
- `tests/test_live_truth_isolation.py` and `tests/_truth_isolation_run.py`.

**The rules:** `runs/dc2_results/rule/`:
- `APP_PREREG.md`;
- `APP_PREREG_ADDENDUM_1.md` and `APP_PREREG_ADDENDUM_2.md`;
- `DISPLAY_PREREG.md`;
- the `.sha256` beside each.

**The model sets:** `runs/live/models/final.json` (456 files) and `zeroshot.json` (220 files). The
zero-shot display head is `runs/dc2_results/dispend_zeroshot/` (its `.pt` is hashed in the manifest).

**The gates:** `runs/live/final/gate_*.json`.

**The replays and scores:** `runs/live/replay/<model>/<mode>/`:
- `<session>__<stem>.jsonl`, every output with its time;
- `.summary.json`;
- `SCORE_<session>.json`.

**The renders:** `runs/live/renders/` (12 videos and `ACCEPTANCE.md`).

**Part D:** `runs/dc2_results/display/`, and `reports/DISPLAY_PROVENANCE_2026-09-30.md`.

**Also rewritten or new:**
- `reports/RENDER_RULES.md` (rewritten);
- `reports/RIG_RUN_PROTOCOL_ADDENDUM_2026-09-30.md`;
- `reports/teaching_pack_app_2026-09-30.json`.
