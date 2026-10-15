# The live app adopts the clean display: everything the report needs (10 October 2026)

Written from 10:46 SAST (clock read) for Uzayr, to update the LaTeX report through the Editor. The report repository
was read, not edited. Anything quoted for the report uses the codes PA1 to PA6; code, data and markdown keep first
names. Every figure is development evaluation, all data seen.

## 0. What happened

- **The decision** (Uzayr, given to the Mastermind at or before 08:31 on 10 October): the live app adopts the A3-clean
  display, `runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json`, for the deployed and the zero-shot model.
  - **The plan:** `runs/clean_display_2026-10-10/PLAN.md` (5f13034c), committed before any decode, with four dated
    notes, also committed before their decodes.
  - **The order:** gates 1 to 6 below ran and passed before the B2 replays; the pre-flight ran on the amended app
    after them.
- **The display, old against new:**

| setting | before (K1g) | now (K1gf, the clean display) |
|---|---|---|
| display head | DISP_END (a sixth network) | none: the five networks' pooled emissions |
| step spread of the display decode (the lock reads it too) | 4.5 | 3.0 |
| head offset | 0.375 s | 0.75 s |
| dot phase | 0.5 stride | 1.0 stride |
| switch | at most 1, none in the last 1.5 m, radius 1.5 m | at most 1, none in the last 1.0 m, radius 1.5 m |
| glide over the anchor span | from press + 2.0 s | from the first frame after the park (below) |
| prior flatten, entry, cap | 0.50, soft with a 1.0 m window, 0.80 m | unchanged |

- **The one engineering change (K1gf):**
  - **What it is:** the glide that carries the dot from the locked line's entry to its first decoded position now
    starts at the first frame after the park, so that frame is the entry exactly.
  - **Why:** with the clean offset and phase, the old glide put the first frame up to 0.37 m along the line, and rule 2a
    (within 0.15 m of the entry) failed on 11 of A3's 120 walks.
  - **What it touches,** against K1g with the same settings: only the 2 or 3 frames of each walk's anchor span. No
    decoded frame, lock or committed line moves.
- **Unchanged:** the networks, the readers, the motion gate, the pace prior and every setting of the committed answer.
  The no-press start detector stays at spread 4.5 (it decides when a walk starts, so it does not follow the display).
- **Guards, all passed** (records in `runs/clean_display_2026-10-10/`):
  1. **Hashes:** 4,975 shipped files hashed before the work, checked again after (section 6).
  2. **Tests:** the live suite (44 passed, 1 skipped, 08:46), the clean display's tests (8 pass) and dry tests of the
     gate 6 check (7 pass).
  3. **The old display still exists exactly:** the "pre_clean" profile reproduces the shipped app on every row (one A3
     and one B2 recording, floats included).
  4. **New offline references at spread 3.0:** the committed lines are identical to the old records on 120 of 120 in all
     three cells, and A3's equal its seventh look's.
  5. **The app equals the offline decode** (G2, the whole-file clock): EXACT on A3, B2 and zero-shot B2.
  6. **A3 through the app reproduces the seventh look:**
     - every row outside the anchor span is identical to the seventh look, floats included;
     - every anchor frame follows the new glide (the first exactly on the entry, the others within 1.3e-15 m);
     - rule 2a holds on 120 of 120.

     So A3 has **no new look**.
  7. **The pre-flight** on the amended app: ALL ok (11:13).
- **Test looks:**
  - **A3:** still seven, because the clean display's A3 replay reproduces the seventh look.
  - **B2 and zero-shot B2:** their **fifth** look each. It comprises the offline decode, the semi-constrained replay, the
    no-press replay, and one recording in fully constrained mode.

## 1. Old against new, every reported figure

Live app, as-it-arrives clock, scored by `app_score`; intervals are 95 % bootstrap over walks (1,000 draws, seed 0),
differences paired on the same drawn walks. Edge lines in the order E_col1, E_col5, E_row1, E_row5.

### 1.1 B2, deployed (the headline)

| B2, deployed | before | now |
|---|---|---|
| committed | 97.50 [94.17, 100.00] | **97.50 [94.17, 100.00]**, identical on 120 of 120 walks |
| lock | 71.67 [63.33, 80.00] | **71.67 [63.33, 80.00]**, paired +0.00 [0.00, 0.00] |
| edges, committed | 100, 100, 100, 100 | 100, 100, 100, 100 |
| edges, lock | 100, 100, 50, 83.3 | 100, 100, 50, 83.3 |

One walk's lock changed, from one wrong line to another (PA1, walk 13, true C_fwd: B_fwd to E_row1).

| B2 dot, deployed | before | now | paired difference |
|---|---|---|---|
| all walks, median | 0.490 m [0.407, 0.586] | **0.430 m [0.367, 0.503]** | -0.060 [-0.129, +0.008] |
| all walks, 90th percentile | 2.830 m | 2.683 m | -0.147 [-0.366, +0.053] |
| all walks, within 0.5 m | 50.7 % [43.9, 57.2] | **56.1 % [50.0, 62.5]** | +5.4 [+0.3, +10.8] |
| correct-lock walks, median | 0.302 m [0.264, 0.348] | **0.313 m [0.281, 0.344]** | +0.010 [-0.046, +0.058] |
| correct-lock walks, 90th percentile | 0.791 m [0.714, 0.899] | **0.707 m [0.645, 0.774]** | -0.084 [-0.205, +0.020] |
| correct-lock walks, within 0.5 m | 70.5 % [65.5, 75.0] | **75.5 % [70.7, 80.4]** | +4.9 [-2.0, +12.1] |

**Reading:**
- **On B2 the clean display draws a dot about as accurate as before on correct-lock walks.** Every correct-lock interval
  holds zero, and the median rises by 0.010 m.
- **Over all walks it does better on one measure:** more frames within 0.5 m, +5.4 points [+0.3, +10.8]. The all-walks
  median falls by 0.060 m, but its interval holds zero.

### 1.2 A3, deployed (unchanged: these are now the live app's own figures)

| A3 | figure |
|---|---|
| committed | 92.50 [87.50, 96.67], edges 66.7, 66.7, 100, 100 |
| lock | 75.00 [67.48, 82.50], edges 33.3, 100, 100, 83.3 |
| dot, all walks | median 0.407 m, within 0.5 m 57.4 % |
| dot, correct-lock walks | median 0.304 m [0.271, 0.340], 90th percentile 0.836 m, within 0.5 m 74.2 % |

These are the seventh look's figures, which the report already carries as the "A3-clean display" row. They are now the
live app's figures, not a side check. The previous A3 row (0.534, 47.2, 0.391, 0.864, 61.8) becomes "the earlier
display".

**The dot from the press** (the anchor span included), recomputed with the new glide on correct-lock walks: median
0.287 m (0.289 m with the old glide), 90th percentile 0.805 m and within 0.5 m 75.5 % (both unchanged).

### 1.3 Zero-shot B2

| zero-shot B2 | before | now |
|---|---|---|
| committed | 90.00 [84.17, 95.00] | **90.00 [84.17, 95.00]**, identical on 120 of 120 walks |
| lock | 56.67 [47.50, 65.83] | **57.50 [48.33, 66.67]**, paired +0.83 [0.00, +2.50] |
| edges, committed | 83.3, 100, 83.3, 100 | 83.3, 100, 83.3, 100 |
| edges, lock | 100, 50, 50, 33.3 | 100, 50, 50, 33.3 |

One walk's lock changed, from wrong to right (PA5, walk 2, true D_rev: A_fwd to D_rev).

| zero-shot B2 dot | before | now | paired difference |
|---|---|---|---|
| all walks, median | 0.759 m [0.615, 1.021] | **0.565 m [0.471, 0.732]** | -0.194 [-0.328, -0.112] |
| all walks, within 0.5 m | 37.4 % [31.7, 43.4] | **45.7 % [39.3, 52.7]** | +8.4 [+4.8, +12.0] |
| correct-lock walks, median | 0.394 m [0.336, 0.444] | **0.326 m [0.290, 0.356]** | -0.068 [-0.122, -0.015] |
| correct-lock walks, 90th percentile | 1.149 m [0.985, 1.284] | **0.766 m [0.678, 0.825]** | -0.384 [-0.530, -0.227] |
| correct-lock walks, within 0.5 m | 59.9 % [55.2, 64.9] | **74.0 % [69.0, 78.9]** | +14.1 [+8.1, +19.8] |

**Reading:** in the room it never saw, the clean display's dot is clearly better on every measure but one (the all-walks
90th percentile, unchanged). The zero-shot model had drawn through its own display head (DISP_END trained on A1 and A2),
which the clean display does not use.

### 1.4 The value of one day of new-room data (deployed minus zero-shot, B2, paired by walk)

Computed by the same code as before (`runs/ship_0p5_2026-10-08/paired_gain.py`), on the spread-3.0 offline rows, which
the app equals by gate 5. The same code reproduces the report's old figures exactly.

| | before | now |
|---|---|---|
| committed | +7.50 [2.50, 13.33] | **+7.50 [2.50, 13.33]** |
| lock | +15.00 [7.50, 23.33] | **+14.17 [6.67, 21.67]** (71.67 against 57.50) |

### 1.5 Operating modes

| mode | B2 before | B2 now | A3 |
|---|---|---|---|
| semi-constrained, committed / lock | 97.50 / 71.67 | 97.50 / 71.67 | 92.50 / 75.00 (unchanged) |
| fully constrained, committed | 96.67 [93.31, 99.17] | 96.67 [93.31, 99.17] (the display cannot move it) | 92.50 [87.50, 96.67] |
| fully constrained, lock | 71.67 (= semi's) | 71.67, equal to the semi lock by construction, confirmed on one B2 recording (20 walks) | 75.00 |
| no press, correct and detected of all walks (Wilson) | 33.33 [25.53, 42.17] | 33.33 [25.53, 42.17] (identical) | 35.00 [27.05, 43.88] (stands) |
| no press, committed on the walks detected (Wilson) | 95.24 [84.21, 98.68] | 95.24 [84.21, 98.68] (identical) | 85.71 [73.33, 92.90] (stands) |
| no press, lock on the walks detected (Wilson) | 64.29 [49.17, 77.01] | **66.67 [51.55, 78.99]** | 44.90 [31.85, 58.68], **measured with the earlier display** |
| no press, detected / false starts per min | 35.0 % / 4.10 | 35.0 % / 4.10 (identical) | 40.8 % / 3.91 (stands) |

**B2 no press, deployed:**
- Every detection and every committed line is identical to before, on every walk of the 12 recordings.
- The lock on the 42 walks detected rises from 27 to 28 correct: one walk went from wrong to right and none the other
  way, paired +2.38 points [0.00, +7.14].
- Lock correct and detected, of all 120 walks: 22.50 [15.95, 30.76] becomes 23.33 [16.67, 31.66].

**Zero-shot B2, other modes:**
- **Fully constrained:** committed 89.17 [83.31, 94.17] is unchanged; its lock equals the semi lock, 57.50.
- **No press, everything identical:** correct and detected 20.83 [14.53, 28.95], detected 26.7 %, committed on detected
  78.1 % and lock on detected 59.4 % (19 of 32; no walk changed).
- **Its lock correct and detected** stays 15.83.

**The confirmation:** one B2 recording (PA5, 20 walks) was replayed in fully constrained mode with the clean display.
Its lock rows are identical to the semi-constrained replay's, and its committed lines identical to the earlier
fully constrained replay's, on all 20 walks, floats included.

**Why the fully constrained lock equals the semi lock by construction:** in both modes the lock is the line first
drawn at press + 2.0 s. No end press has arrived by then, since every walk is longer than 2 s, and the display reads an
end press only once it exists.

**A3's no-press mode was not replayed** (Uzayr: that would be an eighth look):
- its detections and committed lines stand unlabelled, because the display cannot move them;
- its lock carries the label "measured with the earlier display" wherever it is quoted.

### 1.6 The display's behaviour and latency

- **Rule 2a, now exact:** on the green marker's first frame the dot is at the locked line's entry, 0.000 m away, on every
  walk of A3, B2 and zero-shot B2 (before: up to 0.102 m on the renders, within the 0.15 m allowed).
- **Every other render rule:** no park, together or lock-change failure and no walk with more than one switch, on all
  three sessions.
- **Switches:** B2 deployed 4 (before 3), A3 2 (before 3), zero-shot B2 6.
- **Announcement after the walk's end** (B2): median 1.215 s, p90 1.604 s, max 2.755 s. Unchanged, since it is the
  committed decision's timing.
- **Draw lag:** on the stream clock, at most 0.141 s on B2 and 0.153 s on A3. The renders' own figures are in section
  1.7.

### 1.7 The renders

**Where they are:** `runs/live/renders_K1gf/`, with `ACCEPTANCE.md` (PA codes in a column beside P1 to P6). Twelve
videos, one per participant for A3 and for B2. Each is a recording replayed through the live app with the clean display:
semi-constrained, one start press per walk, at real-time pace, with the app's own screen recorded.
- **Each video's log** equals its as-fast-as-possible replay row for row.
- **The machine's load while they were recorded:** median 7.71, max 9.27 on 10 cores (three at a time).
- **A first attempt** on an overloaded machine was stopped and set aside, unused.

**Measured per video, lock and committed (%):** the same as the earlier renders, since the display moves neither.
- A3: PA4 70 and 90, PA1 85 and 90, PA3 75 and 100, PA5 60 and 85, PA2 80 and 90, PA6 80 and 100.
- B2: PA4 65 and 100, PA1 80 and 95, PA3 80 and 100, PA5 75 and 100, PA2 75 and 95, PA6 55 and 95.

**The dot's median error per video:**

| | all walks | correct-lock walks |
|---|---|---|
| A3 | 0.298 to 0.516 m (before: 0.424 to 0.667 m) | 0.251 to 0.358 m (before: 0.339 to 0.435 m) |
| B2 | 0.379 to 0.597 m (before: 0.388 to 0.727 m) | 0.254 to 0.354 m (before: 0.243 to 0.361 m) |

**The render rules hold on all twelve:**
- no park, together, anchor or lock-change failure, and no walk with more than one switch;
- on the green marker's first frame the dot is exactly at the locked line's entry, 0.000 m on every walk (before: at
  most 0.102 m, within the 0.15 m allowed);
- the draw lag is at most 0.153 s, as before.

The draw lag is measured on the recording's own clock, so it does not depend on the machine's load.

**The switches, which changed with the switch rule:**
- **A3:** two, both from one wrong line to another (PA2 walk 17, PA4 walk 10). The earlier renders' correcting switch on
  A3 PA2 walk 7 no longer happens.
- **B2:** four. Three correct a wrong lock (PA2 walk 14, PA4 walk 5, PA6 walk 5) and one goes from wrong to wrong (PA6
  walk 11). The earlier renders' correcting switch on B2 PA1 walk 13 no longer happens: that walk's lock is now E_row1,
  and the true line was C_fwd.

**The two most worth watching (replacing Results 760 to 767):**
- **`final_semi_B2_P3.mp4` (PA3):** still the headline session as it usually runs: every committed line right, 16 of 20
  locks, and the lowest all-walks dot error of the twelve (0.379 m, and 0.313 m on correct-lock walks).
- **`final_semi_B2_P6.mp4` (PA6):** now the only video with both outcomes of the one switch:
  - walk 5 is a wrong lock (B_rev) that the switch corrects (to D_rev);
  - walk 11 a switch from a wrong lock (A_rev) to another wrong line (E_row5), with the committed line right (D_fwd);
  - 19 of 20 committed lines and 11 of 20 locks right.

  `final_semi_A3_P5.mp4` (PA2) no longer shows the correcting switch.

## 2. Where the old values are in the report repository

`BLLUZA001_Final_Year_Report`, branch `report-skeleton`, working tree read from 10:45 on 10 Oct. It holds uncommitted
edits and line numbers move, so re-check. Lines as read.

**Results.tex**
- **121 to 125:** "The live app keeps the shipped display, because the re-chosen one breaks a render rule on 11 of the
  120 walks and was chosen only to settle the label." No longer true; see section 4 for the replacement.
- **129 to 134** (the dot item): "The A3 dot is no longer optimistic: ... fell to 0.304 m". Still true. Add that this is
  now the live app's display.
- **205** (`tab:tracking-headline`): B2 lock 71.67 and its edges are unchanged; nothing to change.
- **Footnote a, 218 to 221:** "Every display setting was re-chosen without A3 and the lock and committed line were
  unchanged". Add: "and the live app now draws that display".
- **`tab:tracking-dot`:**
  - **241, B2 row:** 0.490, 50.7, 0.302, 0.791, 70.5 become 0.430, 56.1, 0.313, 0.707, 75.5.
  - **243 to 244, the A3 rows:** the live app's A3 row is now 0.407, 57.4, 0.304, 0.836, 74.2. Keep 0.534, 47.2, 0.391,
    0.864, 61.8 only as "the earlier display", or drop it.
  - **The caption, 248 to 259:** intervals are now on record for every B2 figure (section 1.1). Footnote b ("The app
    does not ship it, because its first frame after the park breaks a render rule on 11 of the 120 walks") is no longer
    true; see section 4.
- **`tab:tracking-modes`:**
  - **347 to 348:** the fully constrained lock stays 71.67 and 75.00. The caption gets "by construction, confirmed on one
    B2 recording (20 walks)".
  - **352 to 353:** of the B2 no-press figures only the lock changes, 64.29 [49.17, 77.01] becoming 66.67 [51.55, 78.99];
    95.24 and 33.33 stand. A3's lock, 44.90 [31.85, 58.68], gets the label "measured with the earlier display". A3's
    85.71 and 35.00 stand.
- **397:** "90.00% committed and 56.67% lock" becomes 90.00% and 57.50%.
- **401:** "+7.50 points committed and +15.00 points lock" becomes +7.50 and +14.17.
- **404 to 406:** "The lock falls from 71.67% to 56.67% and the all-walks dot median grows about 1.5 times (0.490 m to
  0.759 m), while on correct-lock walks the median moves only from 0.30 m to 0.39 m" becomes: "The lock falls from
  71.67% to 57.50% and the all-walks dot median grows about 1.3 times (0.430 m to 0.565 m), while on correct-lock walks
  the median moves only from 0.31 m to 0.33 m".
- **408 (the `\tbc`):** "locks only 56.67%" becomes 57.50%.
- **`tab:tracking-zeroshot`:**
  - **455:** zero-shot lock 56.67 [47.50, 65.83] becomes 57.50 [48.33, 66.67]; its edges are unchanged;
  - **462:** the gain becomes +14.17 [6.67, 21.67].
- **`tab:tracking-zeroshot-dot`:**
  - **487, deployed:** 0.430, 56.1, 0.313, 0.707, 75.5;
  - **488, zero-shot:** 0.565, 45.7, 0.326, 0.766, 74.0;
  - **the caption:** "No intervals are on record" no longer holds (sections 1.1 and 1.3).
- **741 to 768, the renders** (section 1.7):
  - **change:** the folder (`renders_K1gf`), the sentence "They use the shipped display, so the A3-clean render-rule
    failures do not apply to them", the dot ranges, the anchor sentence (now 0.000 m) and the two "worth watching" picks;
  - **stay:** the per-video lock and committed figures, and the draw lag (at most 0.153 s).

**Discussion.tex**
- **117 to 122:** the semi and fully constrained B2 figures, and the no-press 33.33% [25.53, 42.17] with 4.10 false
  starts per minute, all stand.
- **172 to 176:** "zero-shot B2 90.00% and 56.67%" compares the head mixes under the earlier display. Either leave it
  as it is, adding "with the earlier display", or quote 57.50%.
- **181 to 185:** "+15.00 [7.50, 23.33] lock (71.67 against 56.67)" becomes "+14.17 [6.67, 21.67] lock (71.67 against
  57.50)". The comparison with the earlier mix (+13.33 and +23.33) stands, but "smaller than with the earlier mix"
  now also includes the display change.
- **213:** "71.67% lock against 97.50% committed" is unchanged.
- **262** (`tab:tradeoffs`): "+15.00 lock" becomes "+14.17 lock".

**Methodology.tex**
- **727 to 734** (the dot appears at the locked line's entry when the green marker first appears): now exactly true.
  Nothing to change.
- **761 to 765** (the architecture caption, "FIXED 10 Oct", no display head): matches the code.
- **1130 to 1147** (the display decode, "FIXED 10 Oct"): matches the code on every value: spread 3.0, the 0.8 m cap, the
  pooled emissions with no separate display head, 0.75 s behind each window's end and one stride further along. The
  comment says gates 5 and 6 were still running at 09:28; both have now passed. One sentence is worth adding, for the
  glide (section 3).
- **1169 to 1179** (the switch, "FIXED 10 Oct"): matches the clean display's arm A: 2 nats at two consecutive checks,
  within 1.5 m, not in the last 1.0 m.
- **1665 to 1669** (test looks): "B2 four" becomes "B2 five (... and the clean display of 10 Oct)". A3 stays at seven,
  with the note that the clean display's A3 replay reproduced its seventh look exactly.

**Appendices:** nothing found that names the display head or quotes these figures.

## 3. Methodology text (optional, one sentence for the glide)

For 3.4.x after "...which takes back most of that lag":

```latex
Over the first quarter of a second after the lock the marker glides from the locked line's entry to its first decoded
position, starting exactly at the entry, so the marker first appears at the start of the locked line.
```

## 4. The A3 statement and the dot footnote (paste-ready replacements)

Results 121 to 125, replacing "The live app keeps the shipped display, ... to settle the label.":

```latex
The live app now draws this re-chosen display. Its glide over the first quarter of a second after the lock was changed
to start exactly at the locked line's entry, which removes the one render rule the re-chosen settings broke (on 11 of
the 120 walks) without moving any decoded position, lock or committed line, so the A3 figures above are the live app's.
```

`tab:tracking-dot`, footnote b:

```latex
\textsuperscript{b}Every display setting re-chosen on the development rotations without A3, now the live app's
display.  Paired with the earlier display on the 90 walks whose lock is correct in both, the median falls by
0.087~m [0.038, 0.138].
```

## 5. What is now stale

- **Renders:** the 12 videos in `runs/live/renders_K1g_0p5/` (and their ACCEPTANCE) show the earlier display. The new
  ones are in `runs/live/renders_K1gf/`. A first attempt, stopped because the machine was overloaded, is set
  aside in `runs/clean_display_2026-10-10/discarded_overload_2026-10-10_1027/` and is not used.
- **The streamed demonstration** (`runs/live/stream_disp-K1g/`, B2 streamed as if live, 1 October) and the teaching
  exports show an earlier display (and an earlier head mix).
- **Figures in the report** drawn from the old replays: anything plotted from the B2 or zero-shot dot (the error CDF,
  `fig:error-cdf`), and any example frame or decode figure showing the old marker position.
- **Records:** `reports/tracking/2026-10-09_ship_0p5_report_update.md` (its sections 1.1, 1.3 to 1.5 for the dot and
  zero-shot lock) and `2026-10-09_a3-clean-dot-side.md` (its "the app keeps the shipped display"). They stay as the
  record; the new figures are here.

## 6. Files

- **Plan and notes:** `runs/clean_display_2026-10-10/PLAN.md` and `PLAN_NOTE_1.md` to `PLAN_NOTE_4.md`.
- **The steps' records:** `GATE3.json` to `GATE6.json`, `LOOKS.json`, `NOPRESS.json`, `FULLCHECK.json`, `ADOPT.json`,
  `PREFLIGHT.json`, `RENDERS.json`, `HASHES_BEFORE.json`, `HASHES_AFTER.json`, all in that folder.
- **New replays** in `runs/live/replay/{final,zeroshot}/`:
  - `semi_disp-K1gf_causal` (with `SCORE_*.json`);
  - `unconstrained_m4_disp-K1gf_causal`;
  - `full_disp-K1gf_causal`;
  - `semi_disp-K1gf_causal_realtime_screen`.
- **The offline references at spread 3.0:** `runs/dc2_results/cells/{f05_A3,f05_B2,z05_B2}/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/`.
- **The code:**
  - `pipeline/live/final_model.py`: `DISPLAY_PROFILES`, "clean" the app's, "pre_clean" the earlier display exactly;
  - `pipeline/live/display.py`: candidate K1gf.
- **FINAL_CONFIG:** amended with section 9 and re-hashed. The earlier version is
  `runs/dc2_results/rule/FINAL_CONFIG.pre_clean.md`, and the earlier model sets are
  `runs/live/models/{final,zeroshot}.pre_clean.json`.
