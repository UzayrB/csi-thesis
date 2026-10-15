# POST_DC2_REFACTOR: the consolidation to do once the freezes are lifted

Written 2026-09-24 08:10 SAST by the cleanup session. **Nothing here may be done before DC2.** The DC2
model freeze (`reports/MODEL_FREEZE_DC2.md`, freeze 23h) hashes 34 files in `pipeline/constrained/` and
four elsewhere, the identification freezes hash 19 files in `pipeline/identify/`, and
`reports/PINNED_FILES.txt` lists 159 files (revised 2026-09-24) that no cleanup may touch. Every item below changes
at least one of them, or moves an import path that a pinned file uses. Each item is therefore gated on
the same thing: **the Room B analysis and the DC2 identification scoring are finished and reported,
and the operator has lifted the freezes.** After that, write a new freeze for whatever ships, as usual.

The import counts below were measured on the cleaned tree at `fbe2dd4` (2026-09-24 08:09).

## 1. Stage modules that have become libraries: move them into `pipeline/constrained/lib/`

These files are named after the batch stage that created them, but other modules import them for
their functions. A stage name hides what the code is, and several of them run an import-time guard
(`_guard.assert_isolated`) that makes importing them as a library fragile: the 2026-09-18 cleanup log
records that the bare form of that guard broke a library caller four times.

| module | importers | what the importers use it for |
|---|---|---|
| `rebuild_common.py` | 39 | the rebuild batch's plumbing: stage folders, loading results, headlines |
| `night_common.py` | 33 | the overnight batch's machinery: pairings, stage folders, loading |
| `decoder2.py` | 32 | the rebuilt decoder itself (this one is the model, not a stage, and should be `lib/decoder.py`) |
| `fh_common.py` | 26 | the F, H and live-render batch's shared bits |
| `night_arms.py` | 21 | the parameterised semi-bounded decoder every arm runs through |
| `g3_final.py` | 20 | the shipped pool, the verdict and the latency helpers |
| `q4_arms.py`, `r1_oldcensus.py` | 18 each | the A1 and A2 start terms; the display census instrument |
| `n2_arms.py` | 15 | the single-lever arms and the substitution gate |
| `sb2_structural.py` | 11 | the structural flags of the semi-bounded decoder |
| `rb3_display.py`, `p1_runup.py`, `q1_diag.py`, `rb10_bounded_demo.py`, `rb7_demo.py`, `s2_display.py`, `t1_region.py`, `u1_adapt.py` | 4 to 8 each | display, run-up and region helpers |

- **Files involved:** the modules above and every importer (`grep -rln "pipeline.constrained.<name>" pipeline tests`).
- **How:** move the reusable functions into `lib/` modules named for what they do (`lib/stages.py`,
  `lib/decoder.py`, `lib/pool.py`, `lib/start_terms.py`, `lib/display.py`), leave each stage module as a
  thin entry point that imports from `lib/`, and keep the `assert_isolated` guard only in entry points.
- **The check that proves it safe:**
  1. the full suite shows no new failures;
  2. `python3 -m pipeline.constrained.attempts.rescore` reproduces the 2026-09-17 headlines (it moved to `attempts/` on 2026-09-24);
  3. `python3 -m pipeline.constrained.d4_headline` returns 62.50 pre-registered and 73.33 post-amendment;
  4. the DC2 stand-in (`dc2_pipeline --room room_B --stand-in`) reports 72 of 72 EXACT;
  5. a re-render with `f3_render` gives an `ACCEPTANCE.md` whose per-walk tables match the current one row for row.

## 2. Duplicated helpers

| helper | defined in | state | files involved | check |
|---|---|---|---|---|
| `now()` | `common.py`, `rebuild_common.py` | byte-identical AST | both, plus their importers | suite |
| `J()` | `d4_headline.py` and `d6_lock_commit.py` (identical); `e1_switch.py` and `e2_switch.py` (identical); the two pairs differ | two copies of two versions | the four modules | diff the four bodies first; the JSON each stage writes must be byte-identical before and after |
| `viterbi_chain_scores()`, `_norm()` | `attempts/t7_lockarms.py`, `attempts/t9_lengthnorm.py` (moved 2026-09-24) | byte-identical AST | both, `tests/test_lock_is_causal.py` | `test_lock_is_causal` passes |
| `stage_dir()` | `fh_common.py`, `night_common.py`, `rebuild_common.py` | three versions | the three common modules | every stage still writes to the same `runs/constrained/...` folder (assert the paths in a test) |
| `load()` | `fh_common.py`, `night_common.py` (and an unrelated one in `idgp_cnn.py`) | two versions for stage results | the two common modules | every render-needed result (`a3_lock`, `b1_motion`, `d4_headline`, `d6_lock_commit`, `e2_switch`, `f2_verdict`, `g3_final`, `g6_timeline`, `r1_oldcensus`, `r1_reference`, `r3_lagsweep`, `r3_prior`, `s2_display`) loads identically |

The reason is the usual one: two copies drift, and a fix lands in one. Measured with an AST hash of
every top-level function in `pipeline/`.

## 3. The grid lattice option

`lattice.py` still offers `TDR_LATTICE=grid`, but the grid trees (`runs/artefacts_{half,fh1s,g1s1,
g1s2,g1g100s0,dispend}`, `runs/constrained/windows_half`) were removed on 2026-09-24. They can be
restored (`reports/attempts/ARCHIVE_CODE.md` section 7).

- **Decide one of two things:**
  1. drop the option; or
  2. keep it, and document that it needs the restore first.
- **Files involved:** `lattice.py`, `_guard.py`, `y4_pressalign.py` (its never-written list), and
  `tests/test_one_lattice.py::test_the_grid_lattice_is_still_reachable_for_reproduction`.
- **Check:**
  - `test_one_lattice` is updated to whichever choice is made;
  - grepping for `artefacts_half` finds only the `LEGACY_HALF` mapping, or nothing.
- **Since the cleanup, `tests/test_lock_phase.py::test_the_retired_grid_lattice_still_shows_the_fault_it_had`
  skips** (`grid tree absent`), because it re-measures the retired lattice's fault on `windows_half`. The
  shipped lattice's guard beside it still runs. Either:
  - rebuild `windows_half` (8.5 min) if the fault should stay demonstrated in the suite; or
  - delete that test along with the grid option.

## 4. Identification: collapse 32 modules into one small package

After the cleanup, `pipeline/identify/` holds 32 modules in six families.

| family | modules | shared helpers |
|---|---|---|
| DC2 capture | `capture_idpath`, `rehearsal_check`, `raw_access` | |
| conditioning and features | `conditioning`, `id19_featbank`, `idmax_features`, `idgp_signal`, `idgp_cadence`, `gait_features` (removed; `pass_features` also in `constrained/features.py`) | `pass_features` defined three times |
| banks | `id19_bank`, `idgp_bank` | `run_worker`, `merge` defined in `id19_featbank`, `idgp_bank`, `idgp_checks` |
| evaluation | `idmax_eval`, `idgp_eval`, `id25_learned`, `id_heads`, `id14_crossday`, `id15_corridor`, `id15_factor_map`, `id3_embeddings`, `idgp_cnn`, `idmax_common`, `common` | `run_fold`, `meta` and `fit_predict` each defined three times |
| DC2 scorers | `id28_dc2_score`, `id29_dc2_score`, `idgp_dc2_score` | `extract` and `run` each defined in all three |
| life support and checks | `idgp_checkin`, `idmax_checkin`, `idgp_checks`, `id26b_cnn_diag`, `yield_governor` | |

- **How:** subpackages `identify/{capture,features,bank,eval,dc2}` and one `dc2/common.py` holding the
  scorers' shared discovery, extraction and statistics. Delete the check-in modules; the batches
  they served are closed.
- **Files involved:** the 32 modules, `tests/test_id28_dc2_score.py`, `test_id29_dc2_score.py`,
  `test_idgp_dc2_score.py`, `test_idgp_contract.py`, `test_identification_clean.py`,
  `test_idmax_guards.py`, `test_id_heads.py`, `test_conditioning.py`, `test_fourth_receiver.py`.
- **Check:**
  1. every figure in `reports/ID_QUOTABLE_2026-09-23.md` is reproduced to the printed precision from
     the refactored code;
  2. the DC2 identification scores are reproduced exactly from the same Room B inputs;
  3. the suite passes.
- **Gate:** after DC2 identification is scored, and never before. Four identification files already
  differ from the 23b freeze's recorded hashes (see the cleanup log of 2026-09-24 in `reports/attempts/RECORD_CLEANUPS.md`), and the
  identification session must settle that first.

## 5. The T3 cache deletions (brief step 4)

| path | size | why it waits | check before deleting |
|---|---|---|---|
| `runs/artefacts_s0.5_pressalign_shared/` | 12.7 GB | the shipped lattice's features; the DC2 view step links it and the pressalign trees symlink into it | after DC2, rebuild cost is about 3 min; delete, then confirm `rescore` still reproduces from posteriors |
| `runs/artefacts_s1.0_retrain_shared/` | 6.3 GB | the frozen `artefacts_s1.0_roomA3_*` trees symlink `features` and `rssi_full` into it | delete together with those eight symlinks (remove each link with `rm <path>`, never with a trailing slash) |
| `runs/constrained/windows_s0.5_pressalign/` | 6.3 GB | the ONE lattice's Room A windows | rebuild with `y4_pressalign`'s cutter (8.5 min) |
| `runs/identify/idmax/{features,bank}` | 2.0 GB | DC2 identification scoring | after the scoring is reported |
| `runs/constrained/dc2_*` beyond the reports and `results.json` | whatever DC2 writes | the Room B analysis | keep `runs/constrained/fh/dc2_*` and `reports/DC2_REPORT_*` |
| every `posteriors/` folder | about 1 GB | the prompt keeps them on disk until the Room B analysis | they re-infer in about 19 minutes; the half tree's three reader posteriors are hashed in freeze addendum B and `tests/test_model_freeze.py` re-hashes them, so a re-inferred file must reproduce its hash or enter a new addendum |
| `runs/constrained/dc2_standin/windows/` | 12 dangling links | its targets (`windows_half`) were removed on 2026-09-24; the current stand-in reads only `dc2_standin/data/room_B/calibration.json` | delete the `windows/` subfolder; rerun the stand-in |
| `runs/artefacts_ends/`, `runs/artefacts_w1/`, `runs/artefacts_w05/`, `runs/cleanup/` | about 90 MB | outside the cleanup's exact step-1 set | grep for the names; they are finished arms |
| `~/.Trash/csi-thesis-cleanup-2026-09-24/` | about 28 GB | step 1 moved rather than deleted, because the permission layer refused `rm -rf` | empty it once DC2 has run cleanly |

## 6. Tests to settle after DC2

- **`tests/test_report_consistency.py`:** 8 cases now skip, because the documents they checked lived
  only in `testing/`. Either delete those cases or restore the documents from `pre-cleanup` into
  `reports/`.
- **The grid reachability test in `tests/test_one_lattice.py`, and the grid-fault test in
  `tests/test_lock_phase.py`:** both follow item 3.
- **`tests/test_idmax_guards.py`:** belongs to the identification session. At 13:52 on 2026-09-23 it
  failed on a DEMO path in `runs/identify/idmax/READS.log`; it passes at the cleanup baseline.
