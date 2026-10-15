# Editor list: the switch without its radius condition (14 October 2026), NOT APPLIED

For the Editors, through the Mastermind. Exact old text (from the report repository as read on 14 Oct, about 20:45; match on
the words, since lines may wrap) and new text, PA codes only, British spelling, no semicolons in prose. Evidence for every
figure: `Code/reports/tracking/2026-10-14_switch-radius.md`; the dot figures from
`Code/runs/switch_radius_ship_2026-10-14/EDITOR_FIGURES.json` (the 1.0 s record's method exactly: its "old" side
reproduces every current tab:tracking-dot and tab:tracking-zeroshot-dot value). Correct-lock figures, locks and committed
lines do not change anywhere. Development evaluation, all data seen.

## Methodology

**E1. Methodology.tex:404, the switch sentence** (it never named the 1.5 m condition, so it now describes the shipped switch
exactly; this adds that the distance no longer matters, and the slide).
- Old: `To correct a wrong lock the drawn line may switch once to a line whose $J(L)$ (without the line prior) has led by over 2~nats at two consecutive checks.`
- New: `To correct a wrong lock the drawn line may switch once to a line whose $J(L)$ (without the line prior) has led by over 2~nats at two consecutive checks, however far that line lies from the marker, and the marker then slides to it over 0.5~s.`

**E1b. Methodology.tex:404, the sentence after the next** (with the radius gone, only the last-metre rule reads the drawn
marker, so "both of these" no longer holds; the Mastermind's review, 14 Oct).
- Old: `Because both of these read the drawn marker, the display's timing can change a switch, though never the lock or the committed line.`
- New: `Because this rule reads the drawn marker, the display's timing can change a switch, though never the lock or the committed line.`

**E2. Methodology.tex:661, the look count.**
- Old: `looked at eleven and nine times (Table~\ref{tab:test-looks}).`
- New: `looked at twelve and ten times (Table~\ref{tab:test-looks}).`

## Results

**E3. Results.tex:327, B2's all-walks figures.**
- Old: `On B2 its median error is 0.362~m [0.298, 0.449] over all walks, with 60.0\% [53.3, 66.9] of frames within 0.5~m,`
- New: `On B2 its median error is 0.314~m [0.266, 0.367] over all walks, with 65.9\% [60.3, 71.8] of frames within 0.5~m,`

**E4. Results.tex:327, A3.**
- Old: `A3 is close, at 0.372~m over all walks`
- New: `A3 is close, at 0.324~m over all walks`

**E5. Results.tex:328 to 329, the all-walks 90th percentiles, and what a wrong lock does.**
- Old: `whereas over all walks the 90th percentile reaches 2.65~m on B2 and 2.61~m on A3, because on a wrong-lock walk the dot follows the locked line rather than the walker`
- New: `whereas over all walks the 90th percentile reaches 1.78~m on B2 and 1.55~m on A3, because on a wrong-lock walk the dot follows the locked line rather than the walker until a switch corrects it`

**E6. Results.tex:330, a new passage after the paragraph's last sentence** (which ends `loses the switch that had corrected its wrong lock.`). Insert:

```latex
The switch was then freed of its 1.5~m radius condition, by which a line could take over only if its position lay within 1.5~m of the dot. A rule fixed beforehand chose this on the development rotations, where it put 6.0 points [3.9, 8.2] more of the drawn frames on the true line, and A3 and B2 confirmed it. On B2 the share of frames on the true line rises from 69.7 to 78.5\% (8.8 points [5.4, 13.2] more), on A3 from 73.9 to 84.1\% (10.2 [6.2, 14.6]) and with the zero-shot model on B2 from 57.1 to 66.0\% (8.8 [5.2, 12.6]). Switches onto the true line rise from 2 to 21 on B2, 0 to 21 on A3 and 4 to 26 with the zero-shot model, and none leaves a right line, so every added switch falls on a wrong-lock walk and the correct-lock figures do not move, whilst the all-walks median falls by 0.048~m [0.023, 0.093] on B2. PA6's walk~5 regains its correction. The cost is that about 20 switches per test now carry the dot more than 1.5~m in half a second. The author shipped it after A3 and B2 were seen.
```

**E7. Table tab:tracking-dot, Results.tex:353 and 358** (the correct-lock columns unchanged).
- Old: `B2 & 0.362 & 60.0 & 0.219 & 0.686 & 82.0 \\` / New: `B2 & 0.314 & 65.9 & 0.219 & 0.686 & 82.0 \\`
- Old: `A3\textsuperscript{a} & 0.372 & 58.5 & 0.246 & 0.790 & 75.8 \\` / New: `A3\textsuperscript{a} & 0.324 & 65.0 & 0.246 & 0.790 & 75.8 \\`

**E8. The caption, Results.tex:371.**
- Old: `B2's figures are 0.362~m [0.298, 0.449] and 60.0\% [53.3, 66.9] over all walks`
- New: `B2's figures are 0.314~m [0.266, 0.367] and 65.9\% [60.3, 71.8] over all walks`

**E9. Footnote a, Results.tex:372.**
- Old: `then the head offset raised to 1.0~s after A3 and B2 were seen, the live app's display since 14~October,`
- New: `then the head offset raised to 1.0~s and the switch's radius condition removed, both after A3 and B2 were seen, the live app's display since 14~October,`

**E10. Figure fig:error-cdf (`Figures/results_dot_cdf.pdf`, Results.tex:390): panel (a) must be redrawn.** Its all-walks
curves come from the `clean_1s` logs and change. Panel (b) (correct-lock walks) is unchanged. The new curves come from
`Code/runs/switch_radius_a3b2_2026-10-14/R0/{final,zeroshot}/semi_disp-K1gf_prof-clean_1s_r0_causal/` (the shipped
profile's replays, tied to it by the ship's step 3), scored as now (app_score.score_recording, from the first decoded frame).
The Code agent can draw it on request.

**E11. Figure fig:decode-example (`Figures/results_decode_example.pdf`), panel (b) and its caption, Results.tex:473 to 476.**
The walk (B2, recording 1 of 6, pass 3: PA5, true C_fwd, locked E_col1, committed C_fwd) was drawn from the display of
11 October, and the shipped display now switches it from E_col1 to C_fwd 5.5 s after the press. Its dot median becomes
0.63~m (2.35~m in the figure) with 36\% of its frames on the true line (0\% before). Either redraw panel (b) from
the shipped profile's B2 replay of recording 1 of 6 (PA5), under
`Code/runs/switch_radius_a3b2_2026-10-14/R0/final/semi_disp-K1gf_prof-clean_1s_r0_causal/`
with the caption changed, or keep the figure and change the caption:
- Old: `so the dot runs up E\_col1 whilst the walker crosses the diagonal, a median 2.35~m away, yet the committed line, announced 1.03~s after the walk's end, is C\_fwd.`
- New (keeping the figure): `so the dot runs up E\_col1 whilst the walker crosses the diagonal, a median 2.35~m away, yet the committed line, announced 1.03~s after the walk's end, is C\_fwd. The live app's display now switches this walk to C\_fwd 5.5~s after the press, which brings its median to 0.63~m.`

**E12. Results.tex:667, the zero-shot comparison** (1.39 times, so "about 1.4 times" stands).
- Old: `median grows about 1.4 times, from 0.362 to 0.499~m,`
- New: `median grows about 1.4 times, from 0.314 to 0.436~m,`

**E13. Table tab:tracking-zeroshot-dot, Results.tex:766 to 767, and its caption, 777.**
- Old: `Deployed & 0.362 & 60.0 & 0.219 & 0.686 & 82.0 \\` / New: `Deployed & 0.314 & 65.9 & 0.219 & 0.686 & 82.0 \\`
- Old: `Zero-shot & 0.499 & 50.1 & 0.247 & 0.687 & 80.3 \\` / New: `Zero-shot & 0.436 & 55.5 & 0.247 & 0.687 & 80.3 \\`
- Old: `the zero-shot model's figures are 0.499~m [0.412, 0.649] and 50.1\% [43.3, 57.8] over all walks`
- New: `the zero-shot model's figures are 0.436~m [0.367, 0.506] and 55.5\% [49.5, 62.4] over all walks`

**E14. Results.tex:1245, the demonstration videos** (now `Code/runs/live/renders_K1gf_1s_r0/`, ACCEPTANCE.md; the lock,
committed, correct-lock, entry-distance and draw-lag figures are unchanged).
- Old: `with its current display, the head offset at 1.0~s, at real-time pace,`
- New: `with its current display, the head offset at 1.0~s and the switch without its radius condition, at real-time pace,`
- Old: `and the dot's median error is 0.227 to 0.519~m on A3 and 0.243 to 0.738~m on B2 over all walks,`
- New: `and the dot's median error is 0.205 to 0.447~m on A3 and 0.227 to 0.483~m on B2 over all walks,`
- Old: `with every committed line right, 16 of 20 locks and an all-walks dot error of 0.243~m.`
- New: `with every committed line right, 16 of 20 locks and an all-walks dot error of 0.227~m.`
- Old: `A switch corrects a wrong lock in PA2's B2 video (walk 14) and PA4's B2 video (walk 5), while PA6's B2 video now shows only a switch from one wrong line to another on walk~11, with the committed line right.`
- New: `Switches correct 21 wrong locks in A3's videos and 21 in B2's, among them PA6's B2 walk~5, five and three switches move between two wrong lines, such as PA6's B2 walk~11, and none leaves a right line.`

## Appendix A

**E15. The ledger table, a new row after the head-offset row (Appendices/appendixa.tex, after line 225's `\addlinespace`).**

```latex
  % ADDED 14 Oct 2026 (the switch's radius condition removed, Uzayr's go). Evidence:
  %   Code/reports/tracking/2026-10-14_switch-radius.md, Sections 2 and 3
  Switch without its 1.5~m radius condition
    & Development rotations (A1 and A2 to B1, A1 and B1 to A2, A2 and B1
      to A1), 360 passes
    & Frames on the true line 59.3 against 53.3\% (paired $+6.0$
      $[3.9, 8.2]$), switches onto the true line minus off it 17.50 against 2.75
    & Kept by its rule, confirmed on A3 and B2 with no switch off a right
      line, shipped by the author after both were seen \\
  \addlinespace
```

**E16. Table tab:test-looks (Appendices/appendixa.tex, about lines 403 to 405).**
- Old: `Head offset 1.0~s, the live app's display & 14 Oct & 9 & 7 \\`
- New: `Head offset 1.0~s & 14 Oct & 9 & 7 \\` followed by a new row `Switch without its radius condition, the live app's display & 14 Oct & 10 & 8 \\`
- Old: `Total, with the dwell ablation and the GPU run & & 11 & 9 \\`
- New: `Total, with the dwell ablation and the GPU run & & 12 & 10 \\`

The ship's reproduction replays and G2 gate are exactness checks inside these looks and add no row.
