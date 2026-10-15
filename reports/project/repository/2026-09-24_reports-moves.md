# reports/attempts/: every older report, and where each one went

Written 2026-09-24. Everything here is history: tried and tested work, closed batches, superseded handoffs
and briefs, and the cleanups. **Nothing was deleted.** Some files were combined into records, which keep
each file's full text verbatim (headings demoted two levels), with its date, its SHA-256 and a one-line
note wherever a later document overrides one of its figures. Every file is also in git at the tag
`pre-cleanup` under its original path.

**If a document points at `reports/X` and X is not in `reports/`, look here.** X is either in this folder
under the same name, or it was combined into one of the records below. The table says which.

## What is in this folder

| file | what it is |
|---|---|
| `RECORD_TRACKING.md` | the tracking history: 21 reports, verbatim, each with its own index row. Part 1 holds the reports of 2026-09-20 to 23; part 2 holds the batch reports 23c to 23f, the handoffs, the briefs of 2026-09-20, `FIGURES.md` and `ETA.txt` |
| `RECORD_CLEANUPS.md` | the four documents of the repository cleanups (2026-09-18 and 2026-09-24) and the log of this restructure |
| `RECORD_IDENTIFICATION_HISTORY.md` | the closed IDMAX batch's queue, check-in log and closing report, and version 0 of the DC2 identification sheet |
| `TRACKING_2026-09-18.md` | the long tracking report up to the 2026-09-18 rebuild (bounded and self-segmenting modes); a test reads it |
| `SUMMARY.txt` | the 2026-09-17 batch summary; a test reads it |
| `ARCHIVE_CODE.md` | every module, script, tool and test removed on 2026-09-24: what it did, where its results live, how to restore it |
| `PREREG_lock_2026-09-22.md` | pre-registration: improving the line decision at a fixed 2 s lock (refused) |
| `PREREG_lengthnorm_2026-09-22.md` | pre-registration: length-normalised chain totals at the 2 s lock (refused) |
| `PREREG_lockmix_2026-09-23.md` | pre-registration: the estimator dial at the 2 s lock (refused) |
| `PREREG_edgeheads_2026-09-23.md` | pre-registration: the pool heads retrained on entry-straddling windows (refused) |
| `PREREG_retrain1s_2026-09-23.md` | pre-registration: the three 1 s heads retrained from source (bit-identical, nothing shipped) |
| `PREREG_switching_2026-09-23.md` | pre-registration: the first mid-walk switching attempt (superseded by the 23e and 23f versions, which are in `reports/`) |
| `fig/architecture.png` | the 2026-09-17 architecture diagram (unified decoder, fixed 3 s lag); it no longer shows the model |

## Where every former file now lives

| former `reports/` file | now |
|---|---|
| `ACCURACY_STATE_2026-09-22.md` | `RECORD_TRACKING.md`, part 1 |
| `ARCHIVE_CODE.md` | here |
| `BATCH_2026-09-23_REPORT.md` | `RECORD_TRACKING.md`, part 1 |
| `BATCH_2026-09-23c_REPORT.md`, `...23d...`, `...23e...`, `...23f...` | `RECORD_TRACKING.md`, part 2 (23g stays in `reports/`) |
| `BRIEF_motion_and_lock_2026-09-20.md`, `BRIEF_render_fix_2026-09-20.md` | `RECORD_TRACKING.md`, part 2 |
| `CHECKIN_LOG_IDMAX.md`, `QUEUE_IDMAX.md`, `CLOSING_IDMAX_2026-09-23.md` | `RECORD_IDENTIFICATION_HISTORY.md` |
| `CLEANUP_PLAN_2026-09-18.md`, `CLEANUP_LOG_2026-09-18.md`, `CLEANUP_BRIEF_2026-09-23.md`, `CLEANUP_LOG_2026-09-24.md` | `RECORD_CLEANUPS.md` |
| `CLOSING_IDGP_2026-09-23.md` | the appendix of `reports/IDENTIFICATION_2026-09-18.md` (full text, SHA-256 checked) |
| `CLOSING_ID_2026-09-23.md`, `HANDOVER_ID_2026-09-23.md` | the appendix of `reports/IDENTIFICATION_2026-09-18.md` (since the first cleanup) |
| `DC2_ID_PROTOCOL_2026-09-23.md` (version 0) | `RECORD_IDENTIFICATION_HISTORY.md` |
| `DC2_REPORT_room_B_STANDIN.md`, `DC2_REPORT_room_B_STANDIN_DECOYS.md` | `RECORD_TRACKING.md`, part 1 (since the first cleanup) |
| `ETA.txt`, `FIGURES.md` | `RECORD_TRACKING.md`, part 2 |
| `HANDOFF_2026-09-21.md`, `HANDOFF_2026-09-22.md` | `RECORD_TRACKING.md`, part 2 |
| `HANDOFF_2026-09-23.md` | deleted on 2026-09-24 as unsafe (its `windows_half` instruction); at the tag `pre-cleanup` |
| `ITEMS_ABC_REPORT_2026-09-22.md`, `PART1_REPORT_2026-09-22.md`, `PART2_REPORT_2026-09-22.md`, `PARTS_1_TO_3_REPORT_2026-09-20.md`, `PREPRESS_REGION_REPORT_2026-09-21.md`, `RENDER_DOTPHASE_2026-09-22.md`, `RUNUP_FINDINGS_2026-09-20.md` | `RECORD_TRACKING.md`, part 1 |
| `PREREG_edgeheads...`, `PREREG_lengthnorm...`, `PREREG_lock_...`, `PREREG_lockmix...`, `PREREG_retrain1s...`, `PREREG_switching_2026-09-23.md` | here, unchanged (pre-registrations are never merged) |
| `RECORD_TRACKING.md`, `SUMMARY.txt`, `TRACKING_2026-09-18.md` | here |
| `fig/architecture.png` | here, as `fig/architecture.png` |
| `figures_idmax/` | not history: moved to `reports/figures/identify/idmax/` |
| stage `FINDINGS_stage*.txt` files, markers, logs, closed queues, older briefs and summaries | removed in the first cleanup of 2026-09-24; listed in the cleanup log in `RECORD_CLEANUPS.md`, and at the tag `pre-cleanup` |
