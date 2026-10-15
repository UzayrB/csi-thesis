# ACCEPTANCE: the app's renders. MEASURED RESULTS ONLY

**The rules are in `reports/RENDER_RULES.md`,** never here.

**Each video** is one recording replayed through the live app (`python3 -m pipeline.live replay --presses start --clock causal --realtime --screen`). It is the semi-constrained mode: one start press per walk, the as-it-arrives clock fit, at real-time pace, with the app's own screen recorded frame by frame.

**Each row** is that replay's own log, scored by `pipeline/live/app_score.py`. The render-rule counts come from the log alone (`rule_checks`).

Model set `final` (`runs/live/models/final.json`). Written 2026-10-01 10:27 SAST.

**The A3 display figures (the lock and the dot error) are labelled:** OPTIMISTIC. The A3 lock: the display spread and the soft entry were chosen on data that included A3 (the cap is equivalent to a training-derived one). The A3 dot error: the display's phase, switch arm, prior, head choice, spread and entry were chosen on data that included A3. See reports/DISPLAY_PROVENANCE_2026-09-30.md.

## A3

**Session:** lock 70.83 [62.50, 79.17], committed 93.33 [88.33, 97.50], 120 walks, 0 never announced.

**The edge lines:** E_col1 lock 50.0, committed 66.7; E_col5 lock 100.0, committed 100.0; E_row1 lock 83.3, committed 100.0; E_row5 lock 83.3, committed 100.0.

**The dot error** (all walks): median 0.556 m, p90 2.922 m, 45.8 percent within 0.5 m.

**On the walks whose lock is correct:** median 0.379 m.

**The display offset,** reported apart and never added: median 2.518 m.

**The anchor column** is rule 2a's K1g form (the glide): on the green marker's first frame the dot is on the locked line within 0.15 m of its entry. That frame's distance from the entry: median of the recordings' medians 0.023 m, at most 0.102 m; off the line at most 2.2e-16 m.

| video | participant | frames | lock % | committed % | dot err median (all / correct lock) m | within 0.5 m % | park / together / anchor / lock changes / >1 switch | switches | draw lag p99 / max s |
|---|---|---|---|---|---|---|---|---|---|
| `final_semi_A3_P1.mp4` | P1 | 4073 | 70.0 | 90.0 | 0.559 / 0.405 | 45.6 | 0 / 0 / 0 / 0 / 0 | 0 | 0.122 / 0.138 |
| `final_semi_A3_P2.mp4` | P2 | 3147 | 80.0 | 90.0 | 0.451 / 0.359 | 54.7 | 0 / 0 / 0 / 0 / 0 | 1 | 0.118 / 0.152 |
| `final_semi_A3_P3.mp4` | P3 | 3287 | 65.0 | 95.0 | 0.68 / 0.413 | 38.2 | 0 / 0 / 0 / 0 / 0 | 0 | 0.119 / 0.133 |
| `final_semi_A3_P4.mp4` | P4 | 3210 | 50.0 | 90.0 | 0.786 / 0.291 | 38.7 | 0 / 0 / 0 / 0 / 0 | 1 | 0.118 / 0.150 |
| `final_semi_A3_P5.mp4` | P5 | 3221 | 85.0 | 95.0 | 0.477 / 0.349 | 51.1 | 0 / 0 / 0 / 0 / 0 | 0 | 0.104 / 0.130 |
| `final_semi_A3_P6.mp4` | P6 | 2898 | 75.0 | 100.0 | 0.555 / 0.407 | 45.8 | 0 / 0 / 0 / 0 / 0 | 0 | 0.122 / 0.138 |

## B2

**Session:** lock 72.50 [63.33, 80.00], committed 93.33 [88.33, 97.50], 120 walks, 0 never announced.

**The edge lines:** E_col1 lock 100.0, committed 100.0; E_col5 lock 100.0, committed 100.0; E_row1 lock 50.0, committed 100.0; E_row5 lock 50.0, committed 100.0.

**The dot error** (all walks): median 0.475 m, p90 2.572 m, 51.8 percent within 0.5 m.

**On the walks whose lock is correct:** median 0.301 m.

**The display offset,** reported apart and never added: median 2.493 m.

**The anchor column** is rule 2a's K1g form (the glide): on the green marker's first frame the dot is on the locked line within 0.15 m of its entry. That frame's distance from the entry: median of the recordings' medians 0.025 m, at most 0.102 m; off the line at most 2.2e-16 m.

| video | participant | frames | lock % | committed % | dot err median (all / correct lock) m | within 0.5 m % | park / together / anchor / lock changes / >1 switch | switches | draw lag p99 / max s |
|---|---|---|---|---|---|---|---|---|---|
| `final_semi_B2_P1.mp4` | P1 | 3487 | 70.0 | 100.0 | 0.495 / 0.289 | 50.2 | 0 / 0 / 0 / 0 / 0 | 0 | 0.109 / 0.141 |
| `final_semi_B2_P2.mp4` | P2 | 3520 | 85.0 | 95.0 | 0.442 / 0.385 | 55.7 | 0 / 0 / 0 / 0 / 0 | 0 | 0.112 / 0.132 |
| `final_semi_B2_P3.mp4` | P3 | 3323 | 80.0 | 95.0 | 0.362 / 0.274 | 59.0 | 0 / 0 / 0 / 0 / 0 | 0 | 0.110 / 0.132 |
| `final_semi_B2_P4.mp4` | P4 | 3521 | 65.0 | 100.0 | 0.542 / 0.304 | 47.5 | 0 / 0 / 0 / 0 / 0 | 0 | 0.113 / 0.130 |
| `final_semi_B2_P5.mp4` | P5 | 3369 | 65.0 | 95.0 | 0.525 / 0.299 | 48.0 | 0 / 0 / 0 / 0 / 0 | 1 | 0.108 / 0.133 |
| `final_semi_B2_P6.mp4` | P6 | 3370 | 70.0 | 75.0 | 0.474 / 0.263 | 51.0 | 0 / 0 / 0 / 0 / 0 | 1 | 0.115 / 0.127 |

