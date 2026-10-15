# pipeline/retired/ deleted, 1 October 2026

**Uzayr's instruction (1 October, afternoon):** delete the whole of `pipeline/retired/`. Where it is still
referenced, keep the reference as commented-out code. Old tests that do not help today go into commented code where
they stand. Retired files used only by other retired files go with them, and so do the two old scripts that ran
retired code.

This follows `reports/PIPELINE_RESTRUCTURE_2026-10-01.md`, which moved the 39 unused modules into `retired/` that
morning.

## What was deleted

| what | files | why it could go |
|---|---|---|
| `pipeline/retired/` | 39 modules and 5 package files | No current code imports or launches any of them (checked at 13:50, after identification's engine v2). |
| `scripts/render_demo.sh` | 1 | It ran `f3_render`, the first demonstration videos, which the app's renders replaced. |
| `scripts/attempts/track.py` | 1 | It ran the 17 September tracker through `stage4_unified` and `stage5_live`, both retired. |

**Where the deleted code still lives:**
- in git, at the tag `tracking-final-2026-10-01`, which the thesis cites;
- at the restructure commit `6769f8c`;
- `reports/PIPELINE_MOVES_2026-10-01.json` gives each file's original path.

## What still referred to it, and what was done

Every reference outside `retired/` was in `tests/`, plus the two scripts above.

The commenting was done by `runs/restructure_2026-10-01/comment_retired.py`. Each commented block starts with a
`# RETIRED 2026-10-01` line naming the tag.
- **A test, or a helper it needs,** that names deleted code is commented out whole.
- **A test that uses a name commented out** is commented out too, repeated until nothing more changes.
- **In a list or table** that names deleted files, only those entries are commented out.

**Tests commented out (41 in all):**
- **Whole files' worth:**
  - `test_track_entrypoint.py` (all 9, the deleted tracker);
  - `test_fusion.py` (1, `z3a_linkprod`).
- **Part of a file:**
  - `test_render_rules.py`: 7, all on `f3_render`;
  - `test_demo_exclusion.py`: 8 on the deleted split code. Its 15 tests of the current demo capture remain.
  - `test_lock_is_causal.py`: 5 on `lock_horizon` and the old lock stages. Its scan of current code remains.
  - `test_models.py`: 4 on `fusion`. Its 3 tests of the CNN and heads remain.
  - `test_f4_render.py`: 1, `test_f3_render_is_untouched`.
  - `test_drawn_path_is_decoded.py`, `test_red_dot_is_drawn.py`, `test_reported_config_is_applied.py`,
    `test_switching.py`: 1 each, on `f3_render`.
  - `test_no_pacer.py`: 1, `rc8_demo`.
  - `test_id29_dc2_score.py`: 1, identification's `rehearsal_check`.
- **Entries only:**
  - the pairing-key registries in `test_pass_pairing_key.py` (6) and `test_cross_pairing_key.py` (12);
  - `test_asserted_not_measured.py` (2);
  - `test_entrypoint_guard_form.py` (1).
- **Scans that also covered `retired/constrained/`** now cover current code only, with the old expression kept as a
  comment: `test_cross_pairing_key.py` (2), `test_no_shadowed_stage_loads.py`, and `test_lock_is_causal.py`'s
  lag scan.
- **The pin helper:** `tests/_restructure.py` knows a frozen file deleted with `retired/`. It is still checked at the
  restructure's base commit, and has no current version to compare.

## Verification

- **After the deletion, before any test change:** the full suite failed only in the 13 files above, and every
  failure named a deleted module, a deleted file or the deleted script.
- **After the changes:** the 18 edited test files pass.
- **The whole suite, 81 files:** 1,152 passed, 0 failed, 24 skipped. That includes the slow `test_idv2.py`
  (13 passed); the 41 commented-out tests no longer run.
- **No current module changed:** `pipeline/live/`, `constrained/`, `identify/` and `io/` were not touched. The model
  sets, the hash lists and the pre-flight are as in the restructure record.

## Documents updated

- `README.md` and `pipeline/README.md`: `retired/` and the two scripts are gone, and both point to the tag.
