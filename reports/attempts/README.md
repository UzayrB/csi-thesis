# reports/attempts/: retired documents, safe to delete

Rewritten 1 October 2026, in the reports reorganisation (`../project/repository/2026-10-01_reports-reorganisation.md`).
Uzayr intends to delete this folder. Before anything was put here, it was checked against four things, and nothing
here is named by any of them:
- the freeze records in `runs/` and the pin list (`../project/repository/pinned-files.txt`);
- any code, test or tool that reads a report;
- the kept evidence: every document in a `dc2/` or `history/` folder;
- vital content: anything a kept document depends on for a figure, a rule or a method moved to `history/` instead.

Every file is in git, so deleting the folder loses nothing that cannot be recovered (`git log --all -- <path>`).
Kept documents still cite some of these by their old paths (`reports/HANDOFF_...`); the moves map
(`../project/repository/2026-10-01_reports-moves.json`) records where each went.

The previous README of this folder, the map of the 24 September cleanup, is now
`../project/repository/2026-09-24_reports-moves.md`; the files it listed that are still needed moved to `history/`
and `project/`.

| file | why it can go |
|---|---|
| `HANDOFF_TRACKING_2026-09-26.md`, `_2026-09-28.md`, `_2026-09-29.md`, `_2026-09-29_CORRECTED.md`, `_2026-09-30.md`, `HANDOFF_TRACKING_LIVE_AND_CAPTURE_2026-09-26.md` | superseded tracking handoffs; the current one is `../tracking/2026-10-01_handoff.md` |
| `HANDOFF_IDENTIFICATION_2026-09-26.md`, `_2026-09-28.md`, `_2026-09-30.md`, `_2026-10-01.md`, `_2026-10-01_PM.md` | superseded identification handoffs; the current one is `../identification/2026-10-01_handoff.md` |
| `CHECKIN_LOG_ID_DC2.md`, `CHECKIN_LOG_ID_AUDIT.md`, `CHECKIN_LOG_ID_WALKS.md`, `CHECKIN_LOG_ID_ENGINE.md` | identification's progress logs during runs; each run's results are in its own report |
| `ID_DEV_BATCH1_2026-09-29.md` | development batch 1, superseded by batch 2 (`../identification/2026-09-29_development-batch-2.md`) |
| `RIG_RUN_PROTOCOL_2026-09-29.md` | the first rig protocol, superseded by `../tracking/2026-09-30_rig-run-protocol.md` and its addendum |
| `teaching_pack_corrected_2026-09-29.json`, `teaching_pack_app_2026-09-30.json`, `teaching_pack_app_v2_2026-09-30.json` | older tracking teaching packs; the current one is `../tracking/teaching/2026-10-01_teaching-pack-app-v3.json` |
| `POST_DC2_REFACTOR.md` | the consolidation planned on 24 September for after the freezes; the 1 October restructure replaced it |
| `PREREG_edgeheads_2026-09-23.md`, `PREREG_retrain1s_2026-09-23.md`, `PREREG_switching_2026-09-23.md` | pre-registrations of refused or superseded arms, already retired on 24 September; `../tracking/history/record-tracking.md` records their outcomes |
| `status.txt` | the stage runners' status log before DC2 |
| `fig/architecture.png` | the 17 September architecture diagram (unified decoder, fixed 3 s lag); it no longer shows the model |

**One note on `status.txt`.** `pipeline/constrained/common.py` appends to `reports/status.txt` when an old stage
runner is run again. That file is pinned and hashed, so it was not changed: a re-run would create a new
`reports/status.txt`, which belongs here.
