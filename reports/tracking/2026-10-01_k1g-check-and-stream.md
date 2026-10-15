# The K1g anchor check, and the streamed B2 run with K1g. 1 October 2026

**Uzayr's instruction,** verbatim: `reports/BRIEF_LIVE_APP_4_2026-10-01.md` (received 09:19). It follows
`reports/LIVE_APP_K1G_2026-10-01.md`, which adopted K1g as the app's display.

## 1. Rule 2a's check under K1g

### 1.1 The rule, fixed before any re-score

**Where it is written:** `reports/RENDER_RULES.md`, rule 2a, "the K1g form: the glide". It was committed in
`431b180` at 09:22, before any K1g log was re-scored.

**A walk passes if,** on the frame where the green marker first appears (the first frame at or after
press + 2.0 s), the red dot meets both conditions:
- **On the locked line:** within 1e-6 m of the segment from its entry to its exit. This tolerance is K0's
  own, for floating-point rounding only.
- **Near the entry:** within 0.15 m of the locked line's entry, Uzayr's threshold.

**Automatic failures:** a walk with no lock, no frame at or after press + 2.0 s, or no frame at all.

**Which form applies:** the display each replay was drawn with, read from its summary's
`display_candidate`.
- **Held displays (K0, K1, K2):** keep K0's check unchanged.
- **Glide displays (K1g, K2g):** take the new form.

**The code:** `pipeline/live/app_score.py` (`rule_checks(rows, anchor=...)`, `anchor_form`, `_glide_measure`).
- **Checked by hand-made walks** (no log read), which behave as the rule says:
  - **Glide form:** a dot at the entry passes and one 0.10 m along the line passes; one 0.20 m along fails,
    one 5 cm off the line fails, and a walk never drawn fails.
  - **Held form:** unchanged.
- **The live tests pass** (30 passed, 1 skipped: stream, rig, tracking, decision display, truth isolation).

### 1.2 The 360 test walks and the 12 acceptance sheets, re-scored from the existing logs

**Re-scored at 10:28 from the logs already on disk** (no replay was re-run):
`runs/dc2_results/k1g_anchor_check.py`, written to `runs/dc2_results/display/K1G_ANCHOR_CHECK.json`.

| walks | display | form checked | failures | the K0 form's count, for reference | the marker frame's distance from the entry: median / max |
|---|---|---|---|---|---|
| B2 final, semi | K1g | glide | **0 / 120** | 98 | 0.024 / 0.102 m |
| A3 final, semi | K1g | glide | **0 / 120** | 111 | 0.023 / 0.102 m |
| zero-shot B2, semi | K1g | glide | **0 / 120** | 104 | 0.035 / 0.102 m |
| **the 360 test walks** | K1g | glide | **0 / 360** | 313 | at most 0.102 m |
| the same 360, the K0 record | K0 | held, unchanged | 0 / 360 | | |
| the 360 fully constrained walks (aside) | K1g | glide | 0 / 360 | 313 | the same frames |

**What the re-score shows:**
- **On the line:** every marker frame is on its locked line to within 2.2e-16 m, which is floating-point
  rounding.
- **Near the entry:** the farthest is 0.102 m from the entry, inside the 0.15 m threshold.
- **The K0 record:** it keeps K0's held check unchanged, and still passes it.

**The 12 K1g acceptance sheets:** `runs/live/renders_K1g/ACCEPTANCE.md` was rewritten from the same logs.
- **The anchor column:** it now counts the K1g form, and reads 0 on every one of the 12 videos (before: 14
  to 19 per video under the held form).
- **What the sheet now states:** which form it counts, and the marker frame's distance from the entry
  (median of the recordings' medians 0.023 m on A3 and 0.025 m on B2; at most 0.102 m).
- **The other columns are unchanged:**
  - lock;
  - committed;
  - the dot error;
  - park, together, lock changes and over one switch (all 0);
  - switches;
  - draw lag.
- **K0's sheet** (`runs/live/renders/ACCEPTANCE.md`) is not touched.

## 2. The streamed B2 run with K1g

### 2.1 The run

**The command, as proposed:**
`runs/dc2_results/stream_chain.sh runs/live/replay/final/semi_disp-K1g_causal_realtime_screen`.
- **The display:** the app as it ships (`DISPLAY_CANDIDATE = "K1g"`).
- **The pace:** the six B2 recordings, one after another, at their recorded pace.
- **The screen:** recorded throughout.
- **After each recording:** it is compared with the K1g replay of the same recording, and its own capture is
  re-replayed through the harness.
- **When:** 09:23:56 to 10:27:02, under caffeinate, which exited with the chain.

**A quiet machine:**
- **Identification:** idle. Its queue runner had stopped on 30 Sep at 04:21, and no job of its was
  running. It agreed (09:24) to start nothing until "stream done", which was sent at 10:27.
- **Nothing else of Tracking's ran:** every re-score in section 1 waited until the stream had ended.

**Where it writes, and why it moved:** `runs/live/stream_disp-K1g/`.
- **The problem:** the stream wrote to `runs/live/stream/` whatever the display, so a K1g run would have
  overwritten K0's 30 Sep record.
- **The fix:** `stream_source.out_root()` now sends any display other than K0 to `stream_disp-<K>`, as the
  replay folders already do.
- **The chain:** it takes its screen folder from the same place, and now also writes each comparison to
  `compare.json`.
- **The tests:** the stream's tests pass (7 of 7).

**The pre-flight:** passed on every recording before anything was streamed.

### 2.2 The wall-clock table, K0 (30 Sep) and K1g (1 Oct) side by side

**The sources:** each run's own `summary.json`, built by `runs/dc2_results/stream_table.py` into
`runs/dc2_results/display/STREAM_K0_K1G.json`.

| recording | display | window service, median / p99 / max (s) | lock frame late, median / p90 / max (s) | committed line after the walk's end, median / p90 / max (s) | frames late over 0.1 / 0.5 s (of) | press service, median / max (s) | packets parsed, dropped |
|---|---|---|---|---|---|---|---|
| PA5 | K0 | 0.097 / 0.259 / 0.265 | 0.13 / 0.16 / 0.71 | 1.10 / 1.64 / 2.21 | 310 / 120 (1,279) | 0.91 / 1.78 | 162,899, 0 |
| PA5 | K1g | 0.098 / 0.258 / 0.289 | 0.13 / 0.14 / 0.74 | 1.13 / 1.83 / 2.19 | 316 / 132 (1,315) | 0.92 / 1.78 | 162,899, 0 |
| PA1 | K0 | 0.097 / 0.259 / 0.283 | 0.13 / 0.16 / 1.01 | 1.06 / 1.52 / 2.19 | 282 / 118 (1,298) | 0.91 / 2.03 | 163,607, 0 |
| PA1 | K1g | 0.100 / 0.264 / 0.360 | 0.13 / 0.19 / 1.01 | 1.01 / 1.43 / 2.20 | 331 / 143 (1,315) | 0.93 / 1.99 | 163,607, 0 |
| PA2 | K0 | 0.098 / 0.259 / 0.280 | 0.13 / 0.16 / 0.97 | 1.40 / 1.67 / 2.24 | 304 / 124 (1,287) | 0.92 / 2.03 | 157,258, 0 |
| PA2 | K1g | 0.105 / 0.272 / 0.297 | 0.13 / 0.17 / 1.12 | 1.41 / 1.69 / 2.21 | 347 / 154 (1,320) | 0.98 / 2.12 | 157,258, 0 |
| PA3 | K0 | 0.098 / 0.259 / 0.268 | 0.13 / 0.16 / 1.31 | 1.49 / 1.72 / 2.18 | 300 / 123 (1,280) | 0.91 / 2.31 | 156,996, 0 |
| PA3 | K1g | 0.109 / 0.287 / 0.346 | 0.12 / 0.20 / 1.52 | 1.47 / 1.71 / 2.24 | 366 / 167 (1,305) | 1.02 / 2.46 | 156,996, 0 |
| PA4 | K0 | 0.097 / 0.256 / 0.274 | 0.13 / 0.15 / 0.97 | 1.28 / 1.51 / 2.17 | 307 / 123 (1,339) | 0.91 / 2.03 | 162,256, 0 |
| PA4 | K1g | 0.104 / 0.282 / 0.314 | 0.13 / 0.20 / 1.28 | 1.13 / 1.77 / 2.49 | 356 / 154 (1,360) | 0.99 / 2.19 | 162,256, 0 |
| PA6 | K0 | 0.096 / 0.256 / 0.267 | 0.13 / 0.16 / 2.13 | 1.21 / 2.11 / 2.76 | 337 / 147 (1,294) | 0.90 / 3.18 | 165,636, 0 |
| PA6 | K1g | 0.102 / 0.268 / 0.290 | 0.13 / 0.16 / 2.23 | 1.21 / 2.13 / 2.78 | 366 / 162 (1,315) | 0.97 / 3.28 | 165,636, 0 |

**The totals:**

| | K0 (30 Sep) | K1g (1 Oct) |
|---|---|---|
| packets parsed, dropped, read errors | 968,652, 0, 0 | 968,652, 0, 0 |
| the capture's gates (18 receiver checks) | all PASS | all PASS |
| the first walk's lock, late by; every later walk's, at most | 0.71 to 2.13 s; 0.17 s | 0.74 to 2.23 s; 0.49 s (PA1; the others 0.15 to 0.29 s) |
| frames late over 0.1 s / over 0.5 s | 1,840 / 755 of 7,777 (24 % / 10 %) | 2,082 / 912 of 7,930 (26 % / 12 %) |
| the screen: redraws against ticks at 10 a second | 14,835 / 21,906 (68 %) | 14,511 / 21,918 (66 %) |
| against the replay of the same recording, same display: committed lines equal | 120 / 120 | 118 / 120 |
| locks equal | 114 / 120 | 113 / 120 |
| the stream's own capture, re-replayed through the harness | 2 of 6 identical row for row as committed; the other 4 differ only by park frames the K0 stream's logger missed (found and fixed 30 Sep 23:30) | **6 of 6 identical row for row** (1,365 to 1,420 rows) |
| the stream scored against the truth: committed / lock | 93.33 / 69.17 | 93.33 / 70.00 |

**The K1g stream under the render rules** (its own logs, with the presses from its summaries):
- **Rule 2a, the K1g form:** 0 failures of 120; the marker frame is at most 0.102 m from the entry.
- **The other rules:** park, together, lock changes and over one switch are all 0.

### 2.3 What it shows

**The demonstration now runs the app as it ships,** on the boards' own ingestion path.
- **The packets:** every one was parsed and none was dropped.
- **The rules:** every walk passes the render rules.
- **The stream's own capture** replays to identical outputs on all six recordings, now that the logger
  records every park frame. So the app is the same on both paths.

**K1g costs a little time on every recording:**
- **The window service:** the median rises from 0.096-0.098 s to 0.098-0.109 s.
- **The press service:** the median rises from 0.90-0.92 s to 0.92-1.02 s.
- **Frames late:** the share over 0.1 s rises from 24 % to 26 %, and over 0.5 s from 10 % to 12 %.
- **The screen:** it redraws 66 % of its ticks, against 68 %.
- **The cause is not separated:** K1g's display does more per walk (the glide's first-position simulation,
  and the look-ahead), but the two runs were also made at different times on the same machine (30 Sep 22:23
  to 23:25; 1 Oct 09:24 to 10:27).
- **The screen:** it still redraws in the app's own thread, unchanged by decision (`LIVE_APP_K1G` section
  3), so busy moments still skip redraws.

**The stream against the replay:**
- **The difference is the wall clock,** as on 30 Sep. The stream stamps every packet and press on it, so
  the press-phased windows move by milliseconds and borderline answers flip.
- **Locks:** 7 differ.
- **Committed lines:** 2 differ. They go in opposite directions:
  - **PA5 pass 7** (true E_row1): the stream committed D_fwd, the replay E_row1;
  - **PA1 pass 18** (true C_rev): the stream committed C_rev, the replay C_fwd.
- **So the score does not move:** the stream's committed score is 93.33, the same as the K1g replay's B2
  figure. Its lock is 70.00, against the replay's 72.50.
- **The display does not cause it:** K0's stream differed from its replay by 6 locks in the same way.

## 3. Files and commits

| file | what |
|---|---|
| `reports/BRIEF_LIVE_APP_4_2026-10-01.md` | the instruction, verbatim (commit `431b180`) |
| `reports/RENDER_RULES.md` | rule 2a's K1g form, fixed before the re-score (commit `431b180`, 09:22) |
| `pipeline/live/app_score.py` | the glide form of the anchor check, chosen per replay by its display; K0's held form unchanged |
| `pipeline/live/app_acceptance.py` | the sheet states which form its anchor column counts |
| `runs/dc2_results/k1g_anchor_check.py`, `runs/dc2_results/display/K1G_ANCHOR_CHECK.json` | the re-score of the 360 walks (and the K0 and full-mode checks) |
| `runs/live/renders_K1g/ACCEPTANCE.md`; `SCORE_{03,B2}.json` in `runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/` | the 12 sheets, rewritten from the same logs |
| `pipeline/live/stream_source.py` | `out_root()`: a non-K0 stream writes to `runs/live/stream_disp-<K>` |
| `runs/dc2_results/stream_chain.sh` | its screen folder from `out_root()`; each comparison written to `compare.json` |
| `runs/live/stream_disp-K1g/` | the K1g streamed run: six videos, logs, summaries, comparisons, re-replays (the raw captures are git-ignored, as K0's) |
| `runs/dc2_results/stream_table.py`, `runs/dc2_results/display/STREAM_K0_K1G.json` | the side-by-side table |
| `reports/LIVE_APP_K1G_CHECK_STREAM_2026-10-01.md` | this report |
| `QUEUE.md`, `STATE.md`, `reports/DEVLOG_TRACKING_2026-09-28.md` | the records |

**The chain's log:** `runs/dc2_results/logs/stream_chain_K1g.log`. It stays uncommitted, like the other
chain logs.

**Committed by name** in `6854bb5` (10:31), "Tracking: the K1g anchor check and the streamed B2 run with K1g".

**Caffeinate:** the chain ran under `caffeinate -dimsu`, which exited with it. Afterwards no caffeinate
process of Tracking's remained.
