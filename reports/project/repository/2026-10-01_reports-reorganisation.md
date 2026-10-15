# reports/ split into tracking and identification, and renamed, 1 October 2026

Written 1 October 2026, 20:35 SAST onwards, by the monitoring session.

**Uzayr's instruction (1 October, evening):** "Read over the reports do you thik a lot of it can be removed or
combined and stuff? I also do not like the naming convention, all over th eplace and i would appreciate it being
split into Identification and tracking. anything that is unnecessary or retired just put into attempts, i want to
do delete that folder eventually so just check it can be deleted but if it has vital info place it into one the
identifcation or trackig folder. not even sure about figures and teaching, figure that out". The plan was put to
him and approved ("go for it").

**Result.** All 228 files under `reports/` moved with `git mv`, so git keeps each file's history (`git log --follow`).
The move changed no report's text; the two indexes (`reports/README.md`, `attempts/README.md`) were rewritten, and
this record was added. Each file's old path, new path and the reason are in
`2026-10-01_reports-moves.json` in this folder. The base commit is `39a92ab`.

| destination | files |
|---|---|
| `tracking/` (current records 21, `history/` 37, `dc2/` 16, `briefs/` 8, `attack/` 7, `teaching/` 2) | 91 |
| `identification/` (current records 13, `figures/` 33, `history/` 16, `dc2/` 15, `briefs/` 12, `teaching/` 12) | 101 |
| `project/` (`repository/` 10, `dc2-capture/` 4) | 14 |
| `attempts/` (22 new, beside the 4 already there that stay) | 22 |

**Naming.** `YYYY-MM-DD_topic.md`: the date first, the topic in lower case with hyphens. A letter after the date
keeps its batch (`2026-09-23f_...`). A document kept up to date has no date (`render-rules.md`,
`thesis-summary.md`, `live-interface.md`, `future-work.md`). Files moved to `attempts/` keep their old names, since
they are to be deleted and are easiest to find that way.

## The answers to the questions

**Remove: yes, 26 files.** `attempts/` now holds the superseded handoffs (11), the identification check-in logs (4),
three older tracking teaching packs, the first rig protocol, development batch 1, the 24 September refactor plan
that the restructure replaced, the stage runners' status log, three refused pre-registrations retired on
24 September and the old architecture diagram. `attempts/README.md` gives each a reason.

**Combine: no.** The reports are the evidence trail. Twenty of them are hashed by path in the freeze records, the
pin list holds more, the tests read some, and a correction is always a new file, never an edit. Merging would mean
rewriting records. The handoffs, the thesis summary and `reports/README.md` already act as the combined
summaries.

**Figures and teaching: both are identification's.**
- `figures/identify/` became `identification/figures/` (one level dropped). The thesis summary cites them and
  `tests/test_idmax_guards.py` scans them; no current code writes them.
- `teaching/` became `identification/teaching/`, renamed to the convention
  (`2026-10-01_teaching-pack.json`, `2026-10-01_teaching-notes.md`, `README.md`). `ixt_pack` and `ixt_plots` write
  and read it there now.
- Tracking's two teaching packs went to `tracking/teaching/`.

## Can `attempts/` be deleted? The checks

Nothing went to `attempts/` without passing four checks:
1. **Freezes and pins:** not hashed or cited by any `runs/*FROZEN*.json`, and not in the pin list.
2. **Code:** not read by any code, test or tool (every string literal outside docstrings, found with the AST).
3. **The evidence chain:** not cited by any document kept in a `dc2/` or `history/` folder, repeated until nothing
   new came in. The two combined records `record-tracking.md` and `record-identification-history.md` were not
   counted as citers, since they mention every document of their time.
4. **Vital content:** the rest were read for a figure, a rule or a method that no kept document holds.

The plan put to Uzayr had 41 files for `attempts/`; the checks moved 19 of them out:

| moved out of `attempts/` | why | to |
|---|---|---|
| `SEMIBOUNDED_STATE.md` | freeze 23h cites its section 10 as the canonical ship rule | `tracking/history/semibounded-state.md` |
| `CORRECTION_causal_lock_2026-09-23.md`, `FINDING_linkfusion_2026-09-23.md` | freeze 23h cites them as batch 23c results | `tracking/history/` |
| `QUEUE_IDGP.md` | freeze 23f cites it as where rule G was fixed before any run | `identification/history/queue-idgp.md` |
| `PREREG_committed_fusion`, `PREREG_dotphase`, `PREREG_linkfusion_g100native`, `PREREG_switching_display_2026-09-23e` | in the pin list | `tracking/history/` |
| `BATCH_2026-09-23g_REPORT.md` | the DC2 model freeze (`tracking/dc2/model-freeze.md`) cites it | `tracking/history/` |
| `FINDING_lock_phase_2026-09-23.md`, `FINDING_two_locks_2026-09-23.md` | kept pre-DC2 records rest on them (`FINDING_pooled_vs_edge`, which freeze 23h hashes, among them) | `tracking/history/` |
| `SCORERLOCK_AND_ABLATION_2026-09-23.md` | the DC2 pre-registration cites it | `tracking/history/` |
| `LIVE_SYSTEM_DESIGN_2026-09-25.md` | the kept `LIVE_SYSTEM_2026-09-25.md` rests on it | `tracking/history/` |
| `HEADLINES.txt` | the log of every resolved test before DC2; `IDENTIFICATION_2026-09-18.md` cites it | `tracking/history/headlines.txt` |
| `ID_QUOTABLE_2026-09-23.md` | the thesis summary cites it | `identification/history/` |
| `IDENTIFICATION_2026-09-18.md` | `test_idmax_guards` reads it | `identification/history/` |
| `GEOMETRY_AUDIT_2026-09-20.md` | the room, the receivers and the coordinate convention, checked end to end: the methods chapter needs it | `tracking/history/` |
| `DEMO_V2_AND_CSI_CHECK_2026-09-24.md` | the check that the tracker reads the CSI, and accuracy per participant | `tracking/history/` |
| `MODEL_FINAL_TRACKING.md` | the first decode of the final model; the leakage audit is about it | `tracking/history/2026-09-29_final-model-first-decode.md` |

Of the 14 files already in `attempts/`, 10 moved out for the same reasons:
- `RECORD_TRACKING.md` and `RECORD_IDENTIFICATION_HISTORY.md` went to `history/`; a test scans the second.
- `SUMMARY.txt` and `TRACKING_2026-09-18.md` went to `tracking/history/`; `test_report_consistency` reads both and
  would otherwise have skipped.
- `PREREG_lengthnorm_2026-09-22.md` (the length-normalised arm, which freeze 23h cites), `PREREG_lock_2026-09-22.md`
  (cited by `FINDING_pooled_vs_edge`) and `PREREG_lockmix_2026-09-23.md` (cited by `FINDING_two_locks`) went to
  `tracking/history/`.
- `ARCHIVE_CODE.md`, `RECORD_CLEANUPS.md` and the old `attempts/README.md` (the 24 September map) went to
  `project/repository/`.

## What changed in code and tests

**Left byte for byte unchanged:** every file the final tracking model's lists hash (`TRACE_HASHES_*`,
`FINAL_CORRECTED_HASHES*`, the model sets `final` and `zeroshot`), every file in the pin list, and every file a
freeze record hashes. Tracking asked for this; an edit would mean regenerating the lists and an exact
reproduction. Identification's files in progress (`pipeline/identify/iwg_*`, `ils_*`) were also left alone.

**What that means for those files.** Their docstrings name the old report paths, which the moves map resolves.
Four also open a report by its old path when run: the DC2 identification scorers `id28_dc2_score`,
`id29_dc2_score`, `idgp_dc2_score` and `idsec_dc2_score`, which hash the pre-registration before scoring and append
to the 18 September report. Each was run once and is finished. Run again at HEAD, it stops because the file is
missing. To re-run one, check out `39a92ab`, the commit before the move. (`dc2b_pipeline` only records its
addendum's old path as a label, and `rebuild_common`'s `BRIEF` and `OPEN_PROBLEMS` are never opened.) `common.py` and `rebuild_common.py` still write their stage
logs (`status.txt`, `HEADLINES.txt`, `FINDINGS_stage*.txt`) into `reports/` when an old stage runner is run; none of
the current models runs them.

**Changed:**
- **Run-time paths:**
  - `pipeline/identify/ixt_pack.py` and `ixt_plots.py` (the identification teaching pack's folder and file name).
    Also, `ixt_pack.commit_of` now follows renames and skips pure renames, so a source report's commit is still
    the one that wrote it, not this move.
  - `pipeline/live/app_teaching.py`: the output folder and the first pack it compares against. Its default
    output name no longer matches an existing pack, so a plain run cannot overwrite v3.
  - `tools/pipeline_restructure.py`: the path of the pipeline moves map.
- **Citations:** the report paths named in docstrings, comments and generated text of 22 unprotected modules in
  `pipeline/`,
  in `README.md`, `pipeline/README.md`, `runs/README.md` and `STATE.md`, rewritten from the map. `README.md`'s
  identification handoff pointer and its `reports/` row were also corrected.
- **Tests:**
  - `tests/_restructure.py` reads both moves maps. `current(p)` gives where a file named before 1 October is now.
  - The freeze tests (`test_model_freeze`, `test_freeze_2026_09_24`, `test_addendum_d_hash`) hash each frozen
    file where it is now. The freezes' own keys keep the old paths.
  - `test_freeze_2026_09_28` and `_28b` hash themselves, so they could not simply be edited. Their bytes at
    `39a92ab` carry the frozen hash, and `frozen_sha` accepts the current file only if it equals those bytes with
    exactly the line edits recorded in `tests/_restructure.py` (`EDITED`). Any other change fails the freeze, as
    before.
  - `test_render_rules`, `test_report_consistency`, `test_idmax_guards`, `test_identification_clean` and
    `test_dc2_ingest_guard` read the new paths. `test_idmax_guards` scans the same 29 files as before, and
    `test_render_rules` accepts an acceptance document that names the contract by either path.
  - Other references in tests' docstrings and comments were rewritten from the map.

## Verification

| check | result |
|---|---|
| the pre-flight (`python3 -m pipeline.live preflight`) | ALL ok: the corrected model matches `FINAL_CORRECTED_HASHES.txt`; `TRACE_HASHES_fin_A3` (265 files) and `fin_B2` (271) match; both replay gates equal the corrected decode |
| the model sets | `final` 454 files and `zeroshot` 218, every file present and matching |
| protected files | none changed (the only other edits in the tree are identification's own, uncommitted) |
| the report-reading tests (10 files) | 98 passed, none skipped |
| the full suite (77 files, 20:35 to 20:57) | 1,125 passed, 9 skipped, 0 failed: the same as before the move, the skips in the same six files (`test_ground_truth` 1, `test_ide_engine` 1, `test_ide_rigrun` 4, `test_live_truth_isolation` 1, `test_lock_phase` 1, `test_pass_pairing_key` 1) |

## The lanes

Both were held for the move:
- Tracking confirmed nothing of theirs was open in `reports/`.
- Identification kept writing only under `runs/identify/window_gait/` and `pipeline/identify/iwg_*`.

Its uncommitted edit to `CHECKIN_LOG_ID_ENGINE.md` was not made by the identification session, which asked that it
be committed as is with the move; it is in `attempts/`. Both lanes were sent the map afterwards. Identification's
window and gait report will be `identification/2026-10-02_window-gait.md`.
