# Shipping the all-0.5 s heads: plan, written 2026-10-08 23:31 SAST (clock read 23:31; first committed as 23:47, a time written before the clock was read), committed before any training

Decision: `runs/ablations/stride_mix_2026-10-08/DECISION_ship_0p5.md` (0f89263d, SHA-256 72524c13...). Uzayr's brief
of 8 October ("Ship the all-0.5 s heads"). This file is the how; the decision file fixes the what.

## Steps, in order; any failed check stops the work and is reported to Uzayr

1. **Training (GPU, one job at a time, memory watchdog, caffeinate; writes only `runs/ship_0p5_2026-10-08/train/`).**
   `train_head.py` calls the shipped `pd_cells.do_train_d2` on the cell `fin_A3` (deployed: A1+A2+B1) or `zsf_B2`
   (zero-shot: A1+A2), with one `g` job at the 0.5 s stride, reading those cells' existing 0.5 s views and caches
   (read only). Each file is named by its pool slot's seed (`fh1s` slot: file `s0`, trained with seed 3; `g1s1` s1;
   `g1s2` s2; `g100` s0, 100 cells); the saved model records the training seed it was trained with.
   - **Recipe check first:** `half` (0.5 s, 25 cells, seed 0) retrained with the same wrapper must be byte-identical
     to the shipped `fin_A3` half file. If it is not, stop.
   - Then the four new heads for the deployed model, then the four for the zero-shot model.
2. **New cells, added beside the old (nothing old is overwritten):** `f05_A3`, `f05_B2` (deployed; B2 shares A3's
   weights byte for byte, as `fin_B2` does) and `z05_B2` (zero-shot), registered in `runs/dc2_results/stage_cells.json`
   with exactly the `fin` and `zsf` entries' settings. Their view and models are built by `pd_cells`; the `half` slot and
   every reader file come from `fin_A3` / `zsf_B2` byte for byte, the four other slots from step 1.
3. **The offline decode of each new cell**, as the `fin` cells were made: `pd_cells` inference of the five heads, the
   readers, then `pd_clean decode --variants relgateU+abstain+a2w0.25` with `PD_CLEAN_PREFIX=FC` and the frozen A1+A2
   pace (`runs/dc2_results/final/PACE_A1A2.json`), outputs only under the new cells.
4. **The code changes, all additive** (the live app and the model-set definitions point at the new cells; the old
   cells, their records and the old model stay loadable): `pipeline/live/{app_replay,app_score,model_sets,final_model}.py`
   name the cells through one map. The old model sets, hash lists and FINAL_CONFIG are archived under
   `*.pre_0p5.*` names first.
5. **Old-model guard:** after the code changes, `pd_repro_trace run` on `fin_A3`, `fin_B2` and `zsf_B2` must reproduce
   their recorded decodes EXACTLY (old lists re-hashed for the changed files only, as on 6 and 7 October). If not, stop.
6. **New-model guards:** `pd_repro_trace hashes` and `run` on `f05_A3`, `f05_B2`, `z05_B2` (EXACT from hashed inputs);
   the model sets rebuilt (`final`, `zeroshot`); FINAL_CONFIG updated and re-hashed; the live app's gate G2 equals the
   offline decode; `tests/test_live*.py`, the pre-flight and the latency check.
7. **The test decodes, once each, in the live app** (semi mode, as-it-arrives clock, `app_score`, bootstrap 1,000,
   seed 0): B2 deployed, B2 zero-shot, A3 on the shipped display (spread 4.5); fully constrained and unconstrained
   wherever the report quotes them. A3's fifth look, B2's fourth (the decision file records both counts).
8. **The report-update file** `reports/tracking/2026-10-09_ship_0p5_report_update.md` (PA codes for anything bound for
   the report), and the cost of re-running the A3-clean lock selection on the new heads (estimate only).

Nothing under `data/` or `pipeline/io/`, no frozen network, no existing record and no identification file is changed.
