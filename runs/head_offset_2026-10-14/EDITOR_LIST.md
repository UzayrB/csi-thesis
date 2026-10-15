# The Editor list for the 1.0 s head offset (not applied)

Generated 14 Oct 2026 15:28:46 SAST by `runs/head_offset_2026-10-14/editor_list.py`, against the report repository as it read then (only read, never written). Development evaluation, all data seen. PA codes as the report uses them. For each item: the place, the exact old text (checked against the current file), the new text, and the source of every figure.

### E1. Methodology, the switch paragraph (Chapters/Methodology.tex)

*Why:* Section 5 of the record: the switch reads the drawn marker, so a display setting can change it.  
*Old text (found once):*

```
To correct a wrong lock the drawn line may switch once sliding over 0.5~s to a line whose $J(L)$, without the line prior, has led by over 2~nats at two consecutive checks.
```

*New text:*

```
To correct a wrong lock the drawn line may switch once, sliding over 0.5~s, to a line whose $J(L)$, without the line prior, has led by over 2~nats at two consecutive checks while that line's current state lay within 1.5~m of the drawn marker, and never in the marker's last metre of its line. Because both of these read the drawn marker, the display's timing can change a switch, though never the lock or the committed line.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 5; Code/pipeline/constrained/switching.py, decide_walk

### E2. Methodology, the position-track sentence (Chapters/Methodology.tex; already rewritten for 1.0 s)

*Why:* At 1.0 s there is no glide: the marker first appears at a drawn decoded position on the line, not exactly at the line's start (rule 2a retired, Uzayr). No glide remains in the code (the anchor span is empty).  
*Old text (found once):*

```
Using the first window (-1s to 1s) and its center it places the tracker at the start of the chosen line.
```

*New text:*

```
From the first window ($-1$ to 1~s), centred on the press, it places the marker on the chosen line at its first decoded position, a median of about 0.1~m and at most about 1.1~m from the line's start, with no glide.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (rule_2a_retired_reported: B2 median 0.090 m, max 1.140 m; A3 0.130 m, 1.003 m)

### E3. Methodology, fig:lock-timing (already rewritten for 1.0 s): the caption

*Why:* Optional precision: the dot sits on average 4 to 6 cm ahead, not exactly level (decision 2).  
*Old text (found once):*

```
draws each window's position at its centre, level with the truth.
```

*New text:*

```
draws each window's position at its centre, about level with the truth (on average 4 to 6~cm ahead).
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (signed offset, correct-lock: A3 +0.037, B2 +0.063, zero-shot B2 +0.058 m)

### E4. Results, tab:tracking-headline, footnote a (Chapters/Results.tex)

*Why:* The head offset was changed after A3 and B2 were seen.  
*Old text (found once):*

```
Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks, and the live app now draws that display.
```

*New text:*

```
Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks; the live app now draws that display with its head offset raised to 1.0~s after A3 and B2 were seen, which again leaves every lock and committed line unchanged.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 4 and 6.2

### E5. Results, the A3 paragraph after tab:tracking-headline (Chapters/Results.tex)

*Why:* The glide no longer exists, and the A3 figures above (0.304 m) are the 0.75 s display's, no longer the live app's.  
*Old text (found once):*

```
The live app now draws this re-chosen display. Its glide over the first quarter of a second after the lock was changed to start exactly at the locked line's entry, which removes the one render rule the re-chosen settings broke (on 11 of the 120 walks) without moving any decoded position, lock or committed line, so the A3 figures above are the live app's.
```

*New text:*

```
The live app now draws this re-chosen display with one change made after A3 and B2 had been seen: its head offset was raised from 0.75~s to 1.0~s, so that each position is drawn at its own window's centre with no glide (Uzayr's decision, overriding the 0.875~s the pre-registered rule chose on the development rotations). Every lock and committed line is unchanged, and A3's correct-lock dot error falls further, from 0.304~m to 0.246~m [0.207, 0.285], a paired difference of $-0.059$~m [$-0.113$, $-0.004$].
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|03 correct_lock_walks median_m); Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 3, 4 and 6.2

### E6. Results, the dot paragraph before tab:tracking-dot (Chapters/Results.tex)

*Why:* The new dot figures from step 4, measured from the first decoded frame (the table's own measure).  
*Old text (found once):*

```
On B2 its median error is 0.430~m [0.367, 0.503] over all walks, with 56.1\% [50.0, 62.5] of frames within 0.5~m, and on the walks whose lock is correct the median falls to 0.313~m [0.281, 0.344], with 75.5\% [70.7, 80.4] of frames within 0.5~m. A3 is almost the same, at 0.407~m over all walks and 0.304~m [0.271, 0.340] on correct-lock walks.
```

*New text:*

```
On B2 its median error is 0.362~m [0.298, 0.449] over all walks, with 60.0\% [53.3, 66.9] of frames within 0.5~m, and on the walks whose lock is correct the median falls to 0.219~m [0.191, 0.256], with 82.0\% [77.6, 85.8] of frames within 0.5~m. A3 is close, at 0.372~m over all walks and 0.246~m [0.207, 0.285] on correct-lock walks.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json

### E7. Results, the same paragraph: the 90th percentiles (Chapters/Results.tex)

*Why:* The new 90th percentiles.  
*Old text (found once):*

```
on correct-lock walks nine frames in ten lie within 0.71~m on B2 and 0.84~m on A3, whereas over all walks the 90th percentile reaches 2.68~m on both,
```

*New text:*

```
on correct-lock walks nine frames in ten lie within 0.69~m on B2 and 0.79~m on A3, whereas over all walks the 90th percentile reaches 2.65~m on B2 and 2.61~m on A3,
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (p90_m: B2 0.686 and 2.648, A3 0.790 and 2.607)

### E8. Results, the same paragraph: the comparison sentence (Chapters/Results.tex)

*Why:* The comparison that matters now is against the 0.75 s display the app drew until 14 October; the signed offset and the disclosure belong here.  
*Old text (found once):*

```
Compared on the same B2 walks with the display the application drew until 10~October, the clean display puts 5.4 points [0.3, 10.8] more frames within 0.5~m over all walks and leaves the correct-lock walks where they were, with their median moved by only 0.010~m [$-0.046$, 0.058].
```

*New text:*

```
Compared on the same B2 walks with the 0.75~s head offset the application drew until 14~October, drawing each position at its own window's centre lowers the correct-lock median by 0.093~m [0.046, 0.137] and puts 6.6 points [0.8, 12.6] more of those frames within 0.5~m, with every lock and committed line unchanged. The dot, which trailed the walker by 0.25~m, now sits slightly ahead of it, by 0.063~m [0.006, 0.117] on average on B2's correct-lock walks. The head offset of 1.0~s was chosen by the author after the development results were seen, over the 0.875~s the pre-registered rule chose and against a guard fixed beforehand (on one development walk the drawn line made a switch it had not made before), and after A3 and B2 were decoded with it he accepted the slight lead and that one B2 walk (PA6, walk~5) loses the switch that had corrected its wrong lock.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|B2: median diff -0.093 [-0.137, -0.046], within diff +6.555 [+0.756, +12.570], signed offset -0.249 -> +0.063 [+0.006, +0.117]); Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 4, 5 and 7

### E9. Results, tab:tracking-dot, the B2 row

*Why:* Step 4's figures, from the first decoded frame.  
*Old text (found once):*

```
B2 & 0.430 & 56.1 & 0.313 & 0.707 & 75.5 \\
```

*New text:*

```
B2 & 0.362 & 60.0 & 0.219 & 0.686 & 82.0 \\
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|B2)

### E10. Results, tab:tracking-dot, the A3 row

*Why:* Step 4's figures, from the first decoded frame. (Optional: keep the 0.75 s rows as "0.75~s display" rows.)  
*Old text (found once):*

```
A3\textsuperscript{a} & 0.407 & 57.4 & 0.304 & 0.836 & 74.2 \\
```

*New text:*

```
A3\textsuperscript{a} & 0.372 & 58.5 & 0.246 & 0.790 & 75.8 \\
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|03)

### E11. Results, tab:tracking-dot, the caption's intervals

*Why:* The new intervals (the 10 Oct record's bootstrap, which reproduces the old ones exactly).  
*Old text (found once):*

```
B2's figures are 0.430~m [0.367, 0.503] and 56.1\% [50.0, 62.5] over all walks and 0.313~m [0.281, 0.344], 0.707~m [0.645, 0.774] and 75.5\% [70.7, 80.4] on correct-lock walks. For A3 only the correct-lock medians have intervals on record, 0.304~m [0.271, 0.340] with the live app's display and 0.391~m [0.354, 0.435] with the earlier one.
```

*New text:*

```
B2's figures are 0.362~m [0.298, 0.449] and 60.0\% [53.3, 66.9] over all walks and 0.219~m [0.191, 0.256], 0.686~m [0.587, 0.765] and 82.0\% [77.6, 85.8] on correct-lock walks. For A3 the correct-lock median is 0.246~m [0.207, 0.285] with the live app's display, 0.304~m [0.271, 0.340] with the 0.75~s head offset drawn from 10 to 14~October, and 0.391~m [0.354, 0.435] with the display before that.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json

### E12. Results, tab:tracking-dot, footnote a

*Why:* The head offset was changed after A3 and B2 were seen.  
*Old text (found once):*

```
Every display setting re-chosen on the development rotations without A3, now the live app's display, with A3's exposure as in \cref{tab:tracking-headline}.
```

*New text:*

```
Every display setting re-chosen on the development rotations without A3, then the head offset raised to 1.0~s after A3 and B2 were seen, the live app's display since 14~October, with A3's exposure as in \cref{tab:tracking-headline}.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 4

### E13. Results 4.5, the twelve demonstration videos (the per-video figures and the showcase)

*Why:* the videos were re-recorded with the 1.0 s display (`runs/live/renders_K1gf_1s/`); PA6's B2 walk 5 no longer shows a corrected lock; rule 2a is retired.  
*Old text:* the paragraph from "The twelve demonstration videos, one per participant" to "while the committed line stays right." (Chapters/Results.tex, Section 4.5).

*New text:*

```
The twelve demonstration videos, one per participant for A3 and for B2, are recordings replayed through the application with its current display, the head offset at 1.0~s, at real-time pace, semi-constrained with one start press per walk, with the application's own screen recorded, and each video's log equals its replay at full speed row for row. Per video the lock and the committed line are right on 60 to 85\% and 85 to 100\% of A3's walks and on 55 to 80\% and 95 to 100\% of B2's, and the dot's median error is 0.227 to 0.519~m on A3 and 0.243 to 0.738~m on B2 over all walks, and 0.148 to 0.321~m and 0.172 to 0.268~m on correct-lock walks. The render rules hold on all twelve, with no park, together or lock-change failure and no walk with more than one switch, the dot on the locked line on the green marker's first frame, a median of 0.08 to 0.19~m and at most 1.14~m from its entry since the glide is gone, and a draw lag of at most 0.153~s. PA3's B2 video shows the headline session as it usually runs, with every committed line right, 16 of 20 locks and an all-walks dot error of 0.243~m. A switch corrects a wrong lock in PA2's B2 video (walk 14) and PA4's B2 video (walk 5), while PA6's B2 video now shows only a switch from one wrong line to another on walk~11, with the committed line right.
```

*Source:* `Code/runs/live/renders_K1gf_1s/ACCEPTANCE.md`; `Code/runs/head_offset_2026-10-14/RENDERS_TABLE.json` and `RENDERS.json` (every log equal to its full-speed replay). Which video to feature is the Editor's choice: PA3's B2 video was the "as it usually runs" pick; its figures are in ACCEPTANCE.md.

### E14. Results, the latency table's draw lag

*No change:* the draw lag is the same at 1.0 s as at 0.75 s, at most 0.141 s on B2 and 0.153 s on A3 (Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json, draw_lag_s; the renders' ACCEPTANCE.md). The lock frame's median 0.13 s there comes from the 30 Sep streamed run, not touched by this change.

### E15. Results, fig:error-cdf (results_dot_cdf.pdf)

*Its data change:* the cumulative distributions should be redrawn from the 1.0 s logs (`Code/runs/head_offset_2026-10-14/step4_cpu/final/semi_disp-K1gf_causal/`, identical row for row to the live app's renders). Not redrawn here.

### E16. The ledger (Appendices/appendixa.tex, tab:ledger, Tracking): a new row

```
Head offset of the drawn dot, 0.75, 0.875 and 1.0~s
    & Development rotations (A1 and A2 to B1, A1 and B1 to A2, A2 and B1
      to A1), 360 passes, correct-lock walks
    & Median dot error from the press 0.387, 0.326 and 0.311~m (0.311
      $[0.277, 0.350]$); signed offset $-0.35$, $-0.19$ and $-0.04$~m
    & 1.0~s kept by the author over the rule's 0.875~s, against a guard
      fixed beforehand (one walk's switch changed); on A3 and B2 every
      lock and committed line unchanged \\
```

*Source:* `Code/runs/head_offset_2026-10-14/SELECTION.json`; Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 3 and 4.

### E17. The look table (Appendices/appendixa.tex): new rows

Uzayr's count calls the 1.0 s decode A3's eighth and B2's sixth look; the table's own convention, which counts the 11 Oct re-read as A3's eighth and B2's sixth, makes it the ninth and seventh. Proposed rows, the numbering for Uzayr to choose:

```
    Head offset 0.875~s, stopped part-way, unscored & 14 Oct & (part) & (part) \\
    Head offset 1.0~s, first run on the GPU, not used & 14 Oct & (+1) & (+1) \\
    Head offset 1.0~s, the live app's display & 14 Oct & 9 & 7 \\
    Total, with the dwell ablation and the GPU run & & 11 & 9 \\
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 10.

### E18. Discussion and Recommendations

*Nothing to remove:* the report holds no recommendation to extend the head-offset grid (searched Chapters/Discussion.tex, Chapters/Recommendations.tex and the Results for "grid" and "edge of"); the remark "part of the remaining lag is set by the grid range" is only in the 9 Oct Code record, which is not edited.
