# ACCEPTANCE: the app's renders. MEASURED RESULTS ONLY

**The rules are in `reports/tracking/render-rules.md`,** never here.

**Each video** is one recording replayed through the live app (`python3 -m pipeline.live replay --presses start --clock causal --realtime --screen`). It is the semi-constrained mode: one start press per walk, the as-it-arrives clock fit, at real-time pace, with the app's own screen recorded frame by frame.

**Each row** is that replay's own log, scored by `pipeline/live/app_score.py`. The render-rule counts come from the log alone (`rule_checks`).

**Participants:** P1 to P6 are tracking's codes (`runs/dc2_results/teaching/anon_map.json`). The report's codes, PA1 to PA6 by surname (`reports/project/2026-10-06_handoff.md`), are in the column beside them: P1 = PA4 (PA4), P2 = PA1 (PA1), P3 = PA3 (PA3), P4 = PA5 (PA5), P5 = PA2 (PA2), P6 = PA6 (PA6). Identification's codes are different again and are not used here.

Model set `final` (`runs/live/models/final.json`). Written 2026-10-09 07:59 SAST.

**The A3 display figures (the lock and the dot error) are labelled:** the A3 LOCK is A3-clean; the A3 DOT ERROR stays OPTIMISTIC. The lock: on these shipped all-0.5 s heads, the lock side chosen without A3 (spread 3.0, soft entry, 1.0 m window; `runs/a3_clean_0p5_2026-10-09/A3_CLEAN_CONFIG_0p5.md`) gives the same lock as these videos' spread 4.5 on all 120 walks (A3's sixth look, 9 Oct), so the lock figures below are the A3-clean ones; every display setting the lock reads is chosen without A3 or equivalent to a training-derived value. The dot error: the display's phase, switch arm, prior and head choice were chosen on data that included A3 (`reports/tracking/2026-09-30_display-provenance.md`). A3 in general stays clean in weights and fitted statistics and exposed in design choices; B2 is the headline.

## A3

**Session:** lock 75.00 [67.48, 82.50], committed 92.50 [87.50, 96.67], 120 walks, 0 never announced.

**The edge lines:** E_col1 lock 33.3, committed 66.7; E_col5 lock 100.0, committed 66.7; E_row1 lock 100.0, committed 100.0; E_row5 lock 83.3, committed 100.0.

**The dot error** (all walks): median 0.534 m, p90 2.703 m, 47.2 percent within 0.5 m.

**On the walks whose lock is correct:** median 0.391 m.

**The display offset,** reported apart and never added: median 2.519 m.

**The anchor column** is rule 2a's K1g form (the glide): on the green marker's first frame the dot is on the locked line within 0.15 m of its entry. That frame's distance from the entry: median of the recordings' medians 0.019 m, at most 0.102 m; off the line at most 2.2e-16 m.

| video | participant | report code | frames | lock % | committed % | dot err median (all / correct lock) m | within 0.5 m % | park / together / anchor / lock changes / >1 switch | switches | draw lag p99 / max s |
|---|---|---|---|---|---|---|---|---|---|---|
| `final_semi_A3_P1.mp4` | P1 | PA4 (PA4) | 4073 | 70.0 | 90.0 | 0.569 / 0.409 | 44.6 | 0 / 0 / 0 / 0 / 0 | 1 | 0.122 / 0.138 |
| `final_semi_A3_P2.mp4` | P2 | PA1 (PA1) | 3147 | 85.0 | 90.0 | 0.424 / 0.375 | 56.4 | 0 / 0 / 0 / 0 / 0 | 0 | 0.119 / 0.152 |
| `final_semi_A3_P3.mp4` | P3 | PA3 (PA3) | 3287 | 75.0 | 100.0 | 0.612 / 0.435 | 39.2 | 0 / 0 / 0 / 0 / 0 | 0 | 0.117 / 0.133 |
| `final_semi_A3_P4.mp4` | P4 | PA5 (PA5) | 3210 | 60.0 | 85.0 | 0.667 / 0.339 | 39.9 | 0 / 0 / 0 / 0 / 0 | 0 | 0.121 / 0.153 |
| `final_semi_A3_P5.mp4` | P5 | PA2 (PA2) | 3221 | 80.0 | 90.0 | 0.441 / 0.363 | 52.8 | 0 / 0 / 0 / 0 / 0 | 2 | 0.103 / 0.130 |
| `final_semi_A3_P6.mp4` | P6 | PA6 (PA6) | 2898 | 80.0 | 100.0 | 0.497 / 0.399 | 50.4 | 0 / 0 / 0 / 0 / 0 | 0 | 0.122 / 0.138 |

## B2

**Session:** lock 71.67 [63.33, 80.00], committed 97.50 [94.17, 100.00], 120 walks, 0 never announced.

**The edge lines:** E_col1 lock 100.0, committed 100.0; E_col5 lock 100.0, committed 100.0; E_row1 lock 50.0, committed 100.0; E_row5 lock 83.3, committed 100.0.

**The dot error** (all walks): median 0.490 m, p90 2.830 m, 50.7 percent within 0.5 m.

**On the walks whose lock is correct:** median 0.302 m.

**The display offset,** reported apart and never added: median 2.493 m.

**The anchor column** is rule 2a's K1g form (the glide): on the green marker's first frame the dot is on the locked line within 0.15 m of its entry. That frame's distance from the entry: median of the recordings' medians 0.027 m, at most 0.102 m; off the line at most 1.9e-16 m.

| video | participant | report code | frames | lock % | committed % | dot err median (all / correct lock) m | within 0.5 m % | park / together / anchor / lock changes / >1 switch | switches | draw lag p99 / max s |
|---|---|---|---|---|---|---|---|---|---|---|
| `final_semi_B2_P1.mp4` | P1 | PA4 (PA4) | 3487 | 65.0 | 100.0 | 0.541 / 0.299 | 45.9 | 0 / 0 / 0 / 0 / 0 | 0 | 0.109 / 0.141 |
| `final_semi_B2_P2.mp4` | P2 | PA1 (PA1) | 3520 | 80.0 | 95.0 | 0.427 / 0.361 | 56.9 | 0 / 0 / 0 / 0 / 0 | 1 | 0.112 / 0.132 |
| `final_semi_B2_P3.mp4` | P3 | PA3 (PA3) | 3323 | 80.0 | 100.0 | 0.388 / 0.257 | 57.7 | 0 / 0 / 0 / 0 / 0 | 0 | 0.110 / 0.132 |
| `final_semi_B2_P4.mp4` | P4 | PA5 (PA5) | 3521 | 75.0 | 100.0 | 0.474 / 0.314 | 51.8 | 0 / 0 / 0 / 0 / 0 | 0 | 0.113 / 0.130 |
| `final_semi_B2_P5.mp4` | P5 | PA2 (PA2) | 3369 | 75.0 | 95.0 | 0.475 / 0.327 | 52.8 | 0 / 0 / 0 / 0 / 0 | 1 | 0.108 / 0.133 |
| `final_semi_B2_P6.mp4` | P6 | PA6 (PA6) | 3370 | 55.0 | 95.0 | 0.727 / 0.243 | 39.6 | 0 / 0 / 0 / 0 / 0 | 1 | 0.115 / 0.127 |

