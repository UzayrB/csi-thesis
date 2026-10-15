# The all-0.5 s heads shipped: everything the report needs (9 October 2026)

Written from 05:35 SAST (clock read) for Uzayr, to update the LaTeX report. The report repository was read, not edited.
Anything quoted for the report uses the codes PA1 to PA6; code, data and markdown keep first names.

## 0. What happened

- **The decision** (Uzayr, 8 October; `runs/ablations/stride_mix_2026-10-08/DECISION_ship_0p5.md`, `0f89263d`, committed
  before any training or test decode): every one of the five pool heads is trained on the 0.5 s stride, for simplicity.
  The stride ablation found no measurable difference on the development rotations (committed-line error -1.48
  [-5.52, +2.56] points, lock +0.09 [-0.96, +1.15]). It ships whatever A3 and B2 show.
- **The heads:** `half` unchanged byte for byte; `fh1s`, `g1s1`, `g1s2` retrained at 0.5 s with seeds 3, 1 and 2 (the
  `fh1s` slot's seed 0 would have copied `half` exactly; confirmed by Uzayr, 8 Oct 23:4x); `g100` at 0.5 s, seed 0.
  Deployed model on A1+A2+B1, zero-shot on A1+A2. Display head DISP_END, start-of-walk readers, motion gate, pace and
  every decode setting unchanged.
- **Where:** new cells `f05_A3`, `f05_B2`, `z05_B2` beside the old `fin_A3`, `fin_B2`, `zsf_B2`, which stay loadable.
  The live app reads the new cells (`pipeline/live/final_model.MODEL_CELLS`). Commit `bba8adc8` (pushed).
- **Guards, all passed:**
  - recipe check: `half` retrained by the wrapper came out byte-identical to the shipped file;
  - plumbing: each new cell, holding the old heads, reproduced its old record on 120 of 120 passes;
  - the old model after the code change: `pd_repro_trace run` EXACT on `fin_A3`, `fin_B2`, `zsf_B2`, no unlisted input;
  - the new model: hash lists (265, 271, 234 files), each traced rebuild EXACT; model sets `final` (454 files) and
    `zeroshot` (236) check clean;
  - the live-app gate G2 EXACT on `f05_A3` and `f05_B2` (120 of 120 committed and lock, semi and legacy);
  - pre-flight ALL ok; live tests 48 passed, 2 skipped.
- **Test looks:** one live-app decode of each test session. By the records' counting this is **A3's fifth look and B2's
  fourth** (Uzayr's brief said B2's second; both are recorded in the decision file).
- **An incident, no effect on any result:** from 00:57 to about 03:50 nothing held caffeinate (each stage's caffeinate
  ended with its stage) and the Mac went into maintenance sleep; jobs ran in bursts. Fixed with one standalone
  caffeinate; recorded in memory.

## 1. Old against new, every reported figure

All: development evaluation, all data seen. Live app, semi-constrained unless stated, as-it-arrives clock, scored by
`app_score` (bootstrap over walks, 1,000 draws, seed 0). Edge lines are committed / lock in %, 6 walks each, in the order
E_col1, E_col5, E_row1, E_row5. Deployed = trained on A1+A2+B1; zero-shot = A1+A2. No labelled same-day calibration.

### 1.1 Headline, B2 (deployed)

| B2 | old (mix) | new (all 0.5 s) |
|---|---|---|
| committed | 93.33 [88.33, 97.50] | **97.50 [94.17, 100.00]** |
| lock | 72.50 [63.33, 80.00] | **71.67 [63.33, 80.00]** |
| edges, committed | 100, 100, 100, 100 | 100, 100, 100, 100 |
| edges, lock | 100, 100, 50, 50 | 100, 100, 50, 83 |
| dot, all walks: median / within 0.5 m | 0.475 m / 51.8 % | 0.490 m / 50.7 % |
| dot, correct-lock walks: median / p90 / within 0.5 m | 0.301 / 0.812 m / 70.3 % | 0.302 / 0.791 m / 70.5 % |
| display: rule violations / switches | 0 / 2 | 0 / 3 |

### 1.2 A3 (deployed; the lock and dot are OPTIMISTIC, display spread 4.5 as shipped)

| A3 | old (mix) | new (all 0.5 s) |
|---|---|---|
| committed | 93.33 [88.33, 97.50] | **92.50 [87.50, 96.67]** |
| lock | 70.83 [62.50, 79.17] | **75.00 [67.48, 82.50]** |
| edges | 66.7/50, 100/100, 100/83.3, 100/83.3 | 66.7/33.3, 66.7/100, 100/100, 100/83.3 |
| dot, all walks | 0.556 m / 45.8 % | 0.534 m / 47.2 % |
| dot, correct-lock walks | 0.379 / 0.862 m / 63.3 % | 0.391 / 0.864 m / 61.8 % |
| display: rule violations / switches | 0 / not recorded here | 0 / 3 |

### 1.3 Zero-shot, B2

| zero-shot B2 | old (mix) | new (all 0.5 s) |
|---|---|---|
| committed | 80.00 [72.50, 86.67] | **90.00 [84.17, 95.00]** |
| lock | 49.17 [40.00, 58.33] | **56.67 [47.50, 65.83]** |
| edges, committed | 100, 100, 83.3, 100 | 83.3, 100, 83.3, 100 |
| edges, lock | 100, 50, 0, 33.3 | 100, 50, 50, 33.3 |
| dot, all walks | 0.947 m / 32.6 % | 0.759 m / 37.4 % |
| dot, correct-lock walks | 0.416 / 1.230 m / 58.2 % | 0.394 / 1.149 m / 59.9 % |

### 1.4 The value of one day of new-room data (deployed minus zero-shot, B2, paired by walk)

Computed from the FC decode rows (equal to the app by the gates); the same code reproduces the old figures exactly.

| | old | new |
|---|---|---|
| committed | +13.33 [7.48, 20.00] | **+7.50 [2.50, 13.33]** |
| lock | +23.33 [15.83, 31.67] | **+15.00 [7.50, 23.33]** |

Smaller because the zero-shot model gained most (80.00 to 90.00); the interval stays above zero.

### 1.5 Operating modes

| mode | B2 old | B2 new | A3 old | A3 new |
|---|---|---|---|---|
| semi-constrained, committed / lock | 93.33 / 72.50 | 97.50 / 71.67 | 93.33 / 70.83 | 92.50 / 75.00 |
| fully constrained, committed | 94.17 [89.17, 98.33] | 96.67 [93.31, 99.17] | 93.33 [89.17, 97.50] | 92.50 [87.50, 96.67] |
| fully constrained, lock (= semi's) | 72.50 | 71.67 | 70.83 | 75.00 [67.48, 82.50] |
| fully constrained, edges committed / lock | 100/100, 100/100, 83/50, 100/50 | 100/100, 100/100, 100/50, 100/83 | 67/50, 100/100, 100/83, 100/83 | 50/33, 83/100, 100/100, 100/83 |
| no press, correct and detected of all walks (Wilson) | 36.67 [28.58, 45.58] | 33.33 [25.53, 42.17] | 29.17 [21.78, 37.84] | 35.00 [27.05, 43.88] |
| no press, committed on the walks detected (Wilson) | 93.62 [82.84, 97.81] | 95.24 [84.21, 98.68] | 83.33 [69.40, 91.68] | 85.71 [73.33, 92.90] |
| no press, lock on the walks detected (Wilson) | 63.83 [49.54, 76.03] | 64.29 [49.17, 77.01] | 54.76 [39.95, 68.78] | 44.90 [31.85, 58.68] |
| no press, detected / false starts per min | 39.2 % / 3.77 | 35.0 % / 4.10 | 35.0 % / 4.02 | 40.8 % / 3.91 |

Zero-shot B2, other modes (old to new): fully constrained committed 83.33 [76.67, 90.00] to **89.17 [83.31, 94.17]**
(lock 49.17 to 56.67); no press, correct and detected 20.00 [13.82, 28.04] to **20.83 [14.53, 28.95]** (detected 26.7 %
both; committed on detected 75.0 to 78.1 %, lock on detected 43.8 to 59.4 %).

**The no-press detector changed on the deployed model:** it reads the pooled heads. On B2 it found five fewer walks (42
against 47) with slightly more false starts, and on the walks it found both answers improved. On A3 it found seven more
(49 against 42) with fewer false starts, its committed line improved and its lock fell (44.90 against 54.76 on the
walks found).

### 1.6 Latency and training

- **Announcement after the walk end and draw lag (B2, real-time replay):** median 1.215 s, p90 1.604 s, max 2.755 s
  (old 1.201 / 1.605 / 2.755); draw lag at most 0.141 s (old 0.141). Unchanged.
- **Service time, quiet machine** (a timing-only B2 replay, display K1g, real time, 06:00 to 06:20; its decisions equal
  the scored replay's, 97.50 / 71.67, so it adds no accuracy information): per window median 0.086 to 0.095 s, p99
  0.241 to 0.254 s, inside the 0.5 s stride (30 September, K0, quiet machine: 0.087 to 0.102 s and 0.25 to 0.27 s);
  per start press median 0.84 to 0.93 s, at most 3.08 s on a recording's first press (before: 0.83 to 0.95 s, up to
  3.2 s). Unchanged. Tonight's other timings shared the CPU and are not comparable.
- **Training windows per head:** deployed, every head 3,428 (A1 1,122, A2 1,128, B1 1,178); before, the four 1 s heads
  had 1,615 each. Zero-shot, every head 2,250 (A1 1,122, A2 1,128); before, 1,061 for the 1 s heads.
- **Training time:** deployed, the four new heads 41.5 min (10.0 to 11.1 each; the CPU was shared) against 18.0 min for
  the four 1 s heads; all five 51.1 against 27.6 min. Zero-shot, four new heads 25.4 min against 12.0; all five 31.6
  against 18.2.

## 2. Where the old values are in the report repository (read 9 Oct, 04:5x; Uzayr edits continuously, so re-check)

`BLLUZA001_Final_Year_Report`, branch `report-skeleton`. Line numbers as read.

**Results.tex**
- 104 to 106: "93.33 %" committed on both days and "the locks differ by two walks (72.50 % against 70.83 %)" -> committed
  97.50 % on B2 and 92.50 % on A3 (no longer the same on both days), locks 71.67 % against 75.00 % (four walks apart,
  now A3 above B2; A3 stays optimistic).
- 130: "93.62 %" (no press, committed on detected) -> 95.24 %.
- 158 to 162 (`tab:tracking-headline`): B2 committed 93.33 [88.33, 97.50], edges 100/100/100/100; B2 lock 72.50
  [63.33, 80.00], edges 100/100/50/50 -> 97.50 [94.17, 100.00] and 71.67 [63.33, 80.00], lock edges 100/100/50/83;
  A3 committed 93.33 [88.33, 97.50], edges 66.7/100/100/100 -> 92.50 [87.50, 96.67], edges 66.7/66.7/100/100; A3 lock
  70.83 [62.50, 79.17], edges 50/100/83.3/83.3 -> 75.00 [67.48, 82.50], edges 33.3/100/100/83.3.
- 190 to 191 (dot table): B2 0.475, 51.8, 0.301, 0.812, 70.3 -> 0.490, 50.7, 0.302, 0.791, 70.5; A3 0.556, 45.8, 0.379, 0.862, 63.3 -> 0.534, 47.2, 0.391, 0.864, 61.8.
- 272 to 290 (`tab:tracking-modes`): every cell, per section 1.5.
- 331 to 339: zero-shot "80.00 % committed and 49.17 % lock"; "+13.33 points committed and +23.33 points lock"; "falls
  from 72.50 % to 49.17 %"; "the all-walks dot median roughly doubles (0.475 m to 0.947 m)" -> 90.00 and 56.67; +7.50
  and +15.00; 71.67 to 56.67; 0.490 m to 0.759 m (no longer "roughly doubles": about 1.5 times).
- 351: "So 80.00 % is an upper..." -> 90.00 %.
- 359 to 360 (guide item): zero-shot fully constrained 83.33 [76.67, 90.00] -> 89.17 [83.31, 94.17]; no press 20.00
  [13.82, 28.04] -> 20.83 [14.53, 28.95].
- 380 to 397 (`tab:tracking-zeroshot`): deployed committed and lock rows (as 1.1), zero-shot committed 80.00 [72.50,
  86.67] edges 100/100/83.3/100 -> 90.00 [84.17, 95.00] edges 83.3/100/83.3/100; zero-shot lock 49.17 [40.00, 58.33]
  edges 100/50/0/33.3 -> 56.67 [47.50, 65.83] edges 100/50/50/33.3; gain rows -> +7.50 [2.50, 13.33] and +15.00 [7.50,
  23.33].
- 424 to 425 (dot table, deployed and zero-shot): per 1.1 and 1.3.
- Not tracking (leave): 467, 507, 515, 516, 519, 520, 559, 566, 587, 588, 633, 635 (identification).

**Discussion.tex** (every `\tbc{update after 0.5~s ship}`)
- 110 to 113: "93.33 % committed on B2" -> 97.50 %.
- 119 to 125: semi 93.33 [88.33, 97.50] / 72.50 [63.33, 80.00]; fully constrained 94.17 [89.17, 98.33]; no press 36.67
  [28.58, 45.58] with 3.77 false starts per minute -> 97.50 [94.17, 100.00] / 71.67 [63.33, 80.00]; 96.67 [93.31,
  99.17]; 33.33 [25.53, 42.17] with 4.10.
- 130 to 133 (dwells), 140 to 144 (shared encoder), 150 to 153 (relative gate): these are development records measured
  on the mix; they stay as recorded (say "measured with the earlier head mix" if wanted). Nothing re-run.
- 162 to 166 (the stride row): already right; add that it shipped and the test figures it gave.
- 170 to 175 (one day of new-room data): +13.33 [7.48, 20.00] (93.33 against 80.00) and +23.33 [15.83, 31.67] (72.50
  against 49.17) -> +7.50 [2.50, 13.33] (97.50 against 90.00) and +15.00 [7.50, 23.33] (71.67 against 56.67).
- 198 to 203 (lock at 2 s): "72.50 % lock against 93.33 % committed" -> 71.67 % against 97.50 %.
- 243 (`tab:tradeoffs` row): fill "simplicity, no measurable difference" with the evidence: the stride ablation and
  this ship.

**Methodology.tex**
- 832 to 836: `\tbc{Four of the five networks were trained on windows cut every 1~s, but all five read these
  press-aligned windows}` -> see section 3.
- 897 to 899 (`tab:tracking-networks`): stride row 0.5 / 1 / 1 / 1 / 1 s -> 0.5 s for all; training windows
  3,428 / 1,615 x4 -> 3,428 for all; seed row 0 / 0 / 1 / 2 / 0 -> 0 / 3 / 1 / 2 / 0.

**Appendices/appendixa.tex**
- `tab:ledger` has no stride row yet: add section 4's row.

## 3. Methodology text

Replace the `\tbc{...}` at Methodology.tex 834 to 836 with:

```latex
All five networks are trained on the same press-aligned windows, at the 0.5~s stride.
```

The disclosure sentence (for 3.4.2, after the networks table, or in 3.8):

```latex
Until 8~October four of the five networks were trained on windows cut every 1~s, a mix inherited from an earlier
Room~A screen. A stride ablation on the development rotations found no measurable difference between that mix and
all five at 0.5~s (committed-line error $-1.48$ $[-5.52, +2.56]$ points, lock $+0.09$ $[-0.96, +1.15]$, three seed
sets), so the single stride was adopted for simplicity, fixed before the test sessions were decoded again, and
reported whatever they showed.
```

The networks table, new values: window stride 0.5~s for all five; training windows 3{,}428 for all five; cell size
unchanged; seed 0, 3, 1, 2, 0.

## 4. The ledger row (`tab:ledger`)

```latex
  Every network at the 0.5~s stride, against one at 0.5~s and four at 1~s
    & Development rotations (A1 and A2 to B1, A1 and B1 to A2, A2 and B1
      to A1), three seed sets, 360 passes
    & Committed-line error $-1.48$ $[-5.52, +2.56]$ points, lock $+0.09$
      $[-0.96, +1.15]$, and on the cross-room rotation 66.94\% against
      59.17\%, shrinking with each seed set
    & Kept for simplicity, no measurable difference, shipped on 9~October
      whatever the test showed \\
```

## 5. What is now stale

- **Renders and demo videos:** the 12 K1g videos in `runs/live/renders_K1g/` (and its `ACCEPTANCE.md`), the earlier
  renders, and the streamed demonstration `runs/live/stream_disp-K1g/` (B2 streamed as if live, 1 October) were made with
  the mix. Tonight's real-time replays recorded new screen captures in `runs/live/renders_K1g_0p5/` (not yet checked as
  renders).
- **Teaching material:** `pipeline/live/app_teaching.py` still reads `fin_B2` (the old cell), and the tracking teaching
  exports built from it describe the mix.
- **Figures in the report** built from tracking test figures: the headline, dot and zero-shot tables and anything plotted
  from them (Results 4.3); the networks table (Methodology 3.4); any lock-timing or confusion figure drawn from the old
  replays.
- **Records:** `reports/tracking/2026-10-02_handoff.md` (sections 4.1 to 4.4), `2026-09-30_live-app-model.md` and the
  A3-clean report `2026-10-08_a3-clean.md` (its lock result, 70.83 unchanged at spread 2.5, was measured on the old mix).
  They stay as the record; the new figures are here.

## 6. Identification and anything else that moved

- **Identification is untouched.** No commit tonight touched an identification path; the live identification engine
  (`pipeline/live/identify_engine.py`) was not edited; tracking's model sets contain no identification file.
- **The zero-shot model gained most:** +10.00 committed, +7.50 lock on B2. That changes the zero-shot paragraph's reading
  (Results 331 to 351), and the cross-room hint of the stride ablation now looks like more than a hint.
- **The A3-clean lock selection** (spread 2.5) was made on the old mix and is not re-run. **Cost on the new heads:** the
  rotations' all-0.5 s heads already exist (the stride ablation's ALL05 seed set 0, the exact shipped recipe and seeds),
  so it needs about 1 h of engineering to point the second chat's `lock_side.py` at them, about 1 to 1.5 h of CPU on a
  quiet machine (96 decodes), and one more A3 replay (A3's sixth look), about 40 min.

## 7. Files

- Decision: `runs/ablations/stride_mix_2026-10-08/DECISION_ship_0p5.md`; plan and logs: `runs/ship_0p5_2026-10-08/`.
- FINAL_CONFIG amended (section 8) and re-hashed; the 29 September version: `runs/dc2_results/rule/FINAL_CONFIG.pre_0p5.md`.
- Old model's archives: `runs/live/models/{final,zeroshot}.pre_0p5.json`, `runs/dc2_results/final/*.pre_0p5.txt`,
  `runs/live/replay/{final,zeroshot}.pre_0p5/`.
- New scores: `runs/live/replay/{final,zeroshot}/*/SCORE_*.json`; old against new: `runs/ship_0p5_2026-10-08/logs/
  compare_scores.json`.
