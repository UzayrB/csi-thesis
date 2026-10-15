# runs/attempts/: past results, moved out of the way on 2026-09-24

Nothing here is read by the current model, the demonstration, DC2 or current identification. Each item was checked
by its literal name against every current module and test before it moved. Nothing was deleted: each folder moved
whole, with its own path kept underneath, so `runs/X` became `runs/attempts/X`, with two exceptions:

- the freezes now sit under `freezes/`;
- the `fh` result folders now sit under `fh/`.

## `freezes/`: 46 superseded JSON records

| files | what they are |
|---|---|
| 38 `TRACKING_FROZEN_2026-09-17` to `..._23g.json`, except 22c, 22d and 23e | every tracking freeze before the DC2 freeze 23h. Each superseded the one before and none was overwritten. The history of the headline is here: 62.50 from freeze 18z, 73.33 post-amendment from 23d |
| 4 `IDENTIFICATION_FROZEN_2026-09-18.json`, `..._19.json`, `..._19b.json`, `..._23.json` | the identification freezes before the DC2 chain that starts at 23b |
| 4 `PREREGISTRATION_motion_and_lock`, `..._render_fix`, `..._render_rules`, `..._runup_direction` (2026-09-20) | pre-registrations of the 2026-09-20 batches |

The tests that check these still find them here: `test_freeze_quotes_the_current_figure` checks every freeze in both
places, and `test_report_consistency` reads the 2026-09-17 freeze from here.

## `constrained/`: 68 finished tracking stages, and three loose files

| group | folders |
|---|---|
| decoder rebuild, 2026-09-17 | `rb2b_stride`, `rb2d_retrain`, `rb2_decoder_nobout`, `rb4_bout`, `rb5_calibrate`, `rb6_crossing`, `rb7_demo`, `rb8_verify`, `rb9_report`, `rb10_bounded_demo`, `rb_c4_reconcile` |
| completion phases and the 2026-09-17 renderer | `rc1_diagnostics` to `rc9_contrast` |
| cleanup and mid-line stall, 2026-09-18 | `rd1_stall`, `rd2_pin`, `rd3_verify`, `rd4_halfstride` |
| end windows and the first semi-bounded mode, 2026-09-18 | `ends`, `re1_endlabels` to `re7_finalise` |
| semi-bounded and stride batch, 2026-09-18 | `sb0_train_half` to `sb6_freeze` (both strides) |
| window probe, 2026-09-18 to 19 | `window_probe`, `wp0_feasibility` to `wp4_verdict` |
| the first constrained batch, 2026-09-16 to 17 | `stage0_preflight` to `stage10_report`, `null_config_probe` |
| loose files | `heartbeat.log`, `results.csv`, `RENDER_FIX_GO` |

`test_report_consistency` still reads `stage3_paths`, `stage4_unified`, `stage5_live` and `stage6_demo` from here.

## `fh/`: 55 result folders no current code reads

The refused and diagnostic arms of 2026-09-19 to 23. They include `c1_causal`, `c2_window1s`, `d1_reeval`, `d3_eval`, `f0_repairs`,
`f4_verify`, `g1_ablation`, `g5_freeze`, `p2_prepress`, `p3_direction`, `q2_extras`, `r2_softentry`, `r4_start`, `r5_lock`,
`r6_latency`, `s0_verify`, `s1_confirm`, `t3_ship`, `t4_finetune`, `t5_shipc`, `u3_trackeradapt`, `u4_mechanism`,
`v1_afwd`, `w1_dotphase`, `x1_edgedisp`, `x2_edgepool_*`, `x3_edgeeval`, `y1_diag`, `y1b_locksrc`, `y2_dial`, `y2a_causal`,
`y4b_lockstep1`, the link-fusion sweeps `z3a_linkprod*` and `z3b_g100native*` (the two that DC2 and the headline read stay in
`runs/constrained/fh/`), two smoke runs, and two superseded result sets (`_LOOKAHEAD_superseded_2026-09-23c`, `_grid_superseded_23d`).

## `identify/`: 13 finished identification stages

`id4_verification`, `id5_report`, `id6_extras`, `id7_livepipeline`, `id8_perline`, `id8a_lines`, `id9_threshold`, `id10_voting`,
`id11_audit`, `id12_conditioning`, `id16_daybias`, `id17_learned`, `id18_report`.

## Old artefact trees

| folder | what it was |
|---|---|
| `artefacts_ends/` | the end-windows arm's heads (2026-09-18) |
| `artefacts_w1/`, `artefacts_w05/` | the window probe's 1 s and 0.5 s window arms (did not ship) |
| `cleanup/` | the first cleanup's hash lists (2026-09-18) |

Their `rssi_full/` caches match the `runs/**/rssi_full` ignore rule at this location, so git no longer tracks them. They are
on disk here, and in git history at the tag `pre-cleanup`.

The derived caches removed on 2026-09-24 (the grid lattice's trees and windows, the window-probe windows, the stand-in
caches, the retrain outputs) are listed with their rebuild commands in `reports/attempts/ARCHIVE_CODE.md`, section 7.
