# The live app adopts the A3-clean display: the plan. Written 10 October 2026, 08:34 SAST (clock read), before any decode

**The decision:** Uzayr's, "the live app must adopt the clean display", given to the Mastermind at or before 08:31 on 10 Oct.
The work is owned by the Second Overall chat under the Mastermind.

**The design:** approved by the Mastermind (10 Oct): K1gf "glide_first", DISPLAY_PROFILES clean and pre_clean, the
zero-shot model on the same profile, FCC references beside FC, and `_disp-K1gf` replay folders.

**The display adopted:** `runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json` (SHA-256 6e225f6a..., 8986044e).

| setting | shipped | adopted |
|---|---|---|
| display head | DISP_END | the pooled heads, no display head |
| prior flatten | 0.50 | 0.50 |
| head offset | 0.375 s | 0.75 s |
| SHIFT_W | 0.50 | 1.0 |
| switch arm | C | A (theta 2.0, at most 1 switch, none in the final 1.0 m, radius 1.5 m) |
| spread | 4.5 | 3.0 |
| entry, window | soft, 1.0 m | soft, 1.0 m |
| candidate | K1g | **K1gf**: K1g with the rule 2a fix below |

## 1. The rule 2a fix (the rule unchanged)

**The fix: the glide starts at the FIRST ANCHOR FRAME,** not at press + 2.0 s. That frame is the locked line's entry
exactly, and the glide ends at the first decoded position as before.
- **What changes:** only the anchor-span dots (x in [press + 2.0, t_dec0), 2 or 3 per walk).
- **What does not change:** every decoded dot from t_dec0 on, every switch, every lock and every committed line, by
  construction.
- **K1g and every older candidate are untouched,** so the pre_clean display reproduces exactly.

## 2. The changes (all committed by name, each new file beside the old)

- **`pipeline/live/display.py`:** the "glide_first" anchor branch and the candidate K1gf.
- **`pipeline/live/final_model.py`:** `DISPLAY_PROFILES = {"clean": {...}, "pre_clean": {today's values exactly}}` and
  `DISPLAY_PROFILE = "clean"`. FinalTrackingSession applies the profile before the display is built. Both models (final,
  zeroshot) use the same profile.
- **`pipeline/live/app_replay.py`, `final_model.rig_inner`:** the end head comes from the profile (none for clean), and
  every summary records the profile.
- **`pipeline/live/app_score.py`:** `anchor_form` maps "glide_first" to rule 2a's glide check (0.15 m, on the line), as
  written.
- **The pre-flight:** "the display head the profile needs exists" (none for clean); the gate files per profile.
- **Tests (`tests/test_live_*`):** the display constants follow the profile, with new tests:
  - rule 2a holds by construction under K1gf;
  - K1gf's decoded frames equal K1g's;
  - the pre_clean profile reproduces the shipped K1g replays exactly.
- **`runs/dc2_results/rule/FINAL_CONFIG.md`:** amendment section 9 (the display profile, its values, K1gf, the source), and
  the .sha256 re-written. The current file is kept as `FINAL_CONFIG.pre_clean.md`.
- **Model sets:** `runs/live/models/{final,zeroshot}.json` rebuilt (the clean app loads no DISP_END), with the current ones
  kept as `{final,zeroshot}.pre_clean.json`.
- **The G2 references:** NEW offline records `cells/{f05_A3,f05_B2,z05_B2}/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/`
  (pd_clean decode, variant +sd3.0), written beside FC, never over it. `dc2_scorerlock.py` and the TRACE_HASHES lists are
  not edited.
- **Gate records:** `runs/live/final/gate_{f05_A3,f05_B2,z05_B2}*.json` are kept as `*.pre_clean.json` before the new
  gates write theirs.
- **Replays:** new `_disp-K1gf` folders only, so no shipped replay is overwritten.

## 3. The gates, in order (any failure stops the work and is reported)

1. **Hashes before:** every shipped file outside section 2's list: data, networks, the FC records, the shipped replays,
   the renders. After the work, those files are identical.
2. **The live tests and the new tests pass.**
3. **pre_clean reproduces the shipped app:** one full A3 recording and one full B2 recording, replayed with the pre_clean
   profile, equal the shipped K1g replays (`semi_disp-K1g_causal_realtime_screen`) on every row. This re-runs the
   shipped configuration, so it is not a new look.
4. **The FCC references (offline, spread 3.0):**
   - **f05_A3:** its committed lines and locks must equal the seventh look's on 120 of 120. The configuration is the same
     as A3's sixth and seventh looks, so it is not a new look; any difference stops the work.
   - **f05_B2 and z05_B2:** part of B2's fifth look (section 4).
5. **G2 (legacy mode, the whole-file clock), the clean profile against FCC:** EXACT on f05_A3, f05_B2 and z05_B2, every
   committed line and lock.
6. **A3 through the live app** (semi mode, the as-it-arrives clock, the clean profile), against the seventh look's log
   (`runs/a3_clean_2026-10-08/dot/a3/replay/03__*`). It counts as the **SEVENTH LOOK REPRODUCED** if and only if, checked
   mechanically (the Mastermind's ruling, 10 Oct):
   1. every row outside the anchor span (press, lock, committed, switch, margin, and every dot from t_dec0 on) is
      identical, floats included;
   2. every anchor-span dot equals the glide_first formula exactly;
   3. rule 2a holds on 120 of 120, and every other render rule as before.

   Anything else makes it an **EIGHTH LOOK:** stop and report.
   - **The headline dot figures** (from the first decoded frame) must equal the seventh look's exactly: correct-lock
     median 0.304 m, and so on.
   - **"Dot from the press"** (it includes the anchor span) is recomputed and labelled "recomputed from the seventh look's
     decode with the K1gf anchor".
7. **The pre-flight:** ALL ok on the adopted app.

## 4. The looks

| session | decode | what it counts as |
|---|---|---|
| A3 | the gate 6 replay | the seventh look reproduced (gate 6), or an eighth look, which stops the work |
| B2 | the offline FCC decode at spread 3.0 and the app replay with the clean profile | **B2's FIFTH look** (one look, one configuration) |
| zero-shot B2 | the same pair | **zero-shot B2's FIFTH look** |

**What is reported for B2 and zero-shot B2,** each against its shipped replay:
- the committed line, which must be identical on 120 of 120: the display cannot move it, so any difference stops the work;
- the lock, paired against the shipped 71.67 (zero-shot 56.67), with the four edge lines beside it;
- the dot figures, old against new (all walks and correct-lock walks: median, p90, within 0.5 m), with intervals.

Every figure is labelled "development evaluation, all data seen". No labelled same-day calibration.

## 5. Renders and the report update

**Renders:** the 12 videos (A3 and B2, six each, semi mode, real time, the app's screen) are re-recorded with the adopted
display into `runs/live/renders_K1gf/`, with a new `ACCEPTANCE.md` (every render rule, per video). The old renders are
untouched.

**The report update:** `reports/tracking/2026-10-10_clean_display_report_update.md`, for the Editor via Uzayr, as
`2026-10-09_ship_0p5_report_update.md` did it:
- every figure old against new, and the file and line where it appears, with PA codes;
- the display description in the Methodology (the pooled display, the K1gf glide);
- the A3 label (the dot drops OPTIMISTIC, addendum 2);
- the stale material.

Nothing goes to the report repository from this chat.

## 6. Compute

- **CPU:** at most 6 niced processes; no GPU.
- **Timing:** it starts when the Mastermind allots the slot (CPU free from about 09:45); one caffeinate for the whole
  run; runs/MACHINE_STATE.md kept current.

| step | jobs | CPU-h |
|---|---|---|
| gate 3 | 2 replays (one A3, one B2) | 0.4 |
| gate 4 | 3 offline decodes (readers and decode) | 0.5 |
| gate 5 | 18 legacy replays | 2.3 |
| gate 6 and section 4 | 18 semi replays | 2.3 |
| renders | 12 real-time replays (A3 about 13 min each, B2 about 6 min), low priority, alongside | 2.4 |
| **total** | | **about 8** |

**Wall clock:** about 2 h at 6 processes. Engineering (code and tests) about 2 h, done first.

## 7. Stops

The work stops and reports if any of these happens:
- any gate fails;
- any committed line moves;
- A3 becomes an eighth look;
- a file outside section 2 changes.
