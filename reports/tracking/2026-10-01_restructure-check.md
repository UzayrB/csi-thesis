# Tracking's check of the pipeline/ restructure. 1 October 2026

**Uzayr's instruction,** verbatim: `reports/BRIEF_RESTRUCTURE_CHECK_2026-10-01.md`.

**The restructure:** done by Monitor and committed as `6769f8c` (12:09), from base `5782af8`. Its record is
`reports/PIPELINE_RESTRUCTURE_2026-10-01.md`, and the map of every move is
`reports/PIPELINE_MOVES_2026-10-01.json`.

**This check:** started on Monitor's "carry on" (12:09), as item 1 asks. Before that, nothing was edited and
no job started. The scripts and their outputs are in `runs/dc2_results/restructure_check/`.

## 1. The two tags

- **`tracking-final-2026-10-01`:** on `5782af8`, the last commit before the restructure.
  - **What that commit is:** an identification teaching-pack commit that touches no tracking file (two
    files: its brief and its PLAN).
  - **What it holds for tracking:** exactly tracking's last commit, `ac63425`: the live app with display
    K1g, the K1g anchor check and the K1g stream.
  - **The thesis cites this tag** (`STATE.md`).
- **`tracking-final-restructured-2026-10-01`:** on `395ddb1`, this check's commit: the restructured code (tracking's
  code is `6769f8c`'s) with every check below passing.

## 2. Monitor's results for tracking (read, not repeated)

| check | result | source |
|---|---|---|
| `pd_repro_trace run`, with tracking's chain environment (`PD_CLEAN_PREFIX=FC`, the A1+A2 pace prior) | **PASS, EXACT on all three cells.** fin_A3: 265 hashes; fin_B2: 271; zsf_B2: 216. In every cell: 0 mismatched, 0 unlisted inputs, 0 writes outside scratch, and 0 of 120 committed, display-lock or scorer-lock changes | `runs/dc2_results/verify/repro_trace/run/<cell>/<cell>/run.json` |
| G2 (semi, display K1g, whole-file clock, FC reference) | **120 / 120 committed and 120 / 120 locks, EXACT, on fin_A3, fin_B2 and zsf_B2** | `runs/live/final/gate_<cell>_semi.json` |
| imports | every module imports in a fresh process: 247 of 247 before, 246 of 246 after | `reports/PIPELINE_RESTRUCTURE_2026-10-01.md` 6.1 |
| pre-flight | `python3 -m pipeline.live preflight`: **ALL ok** (once `FINAL_CORRECTED_HASHES.txt` was translated) | the same, 6.2 |
| the test suite | 1,266 passed; the same 7 failures as before the move (section 4 below) | the same, 6.4 |

**One slip in Monitor's logging, which Monitor recorded:** the first repro launch lacked the chain environment
and failed. Its log line read "EXIT 0" only because `$(date)` reset `$?`. The second launch, with the
environment, is the result above.

### 2.1 The model sets: 456 to 454 files (final), 220 to 218 (zero-shot)

**The four files that left** are two per set, and each is the package marker of a package that no longer
exists:

| set | file | its whole content (at `5782af8`) |
|---|---|---|
| `final` | `pipeline/branches/__init__.py` | `"""Parallel processing branches: motion gate, identification, tracking."""` (75 bytes) |
| `final` | `pipeline/models/__init__.py` | `"""Model components: per-link CNN, fusion variants, task heads, DANN."""` (73 bytes) |
| `zeroshot` | `pipeline/branches/__init__.py` | the same file |
| `zeroshot` | `pipeline/models/__init__.py` | the same file |

**The other path changes in each set:**
- **Three moves:** `branches/gate.py`, `models/heads.py` and `models/link_cnn.py` moved to `constrained/`.
  Five old paths went out and three new ones came in: 456 - 5 + 3 = 454, and 220 - 5 + 3 = 218.
- **The moved files are byte-identical** to their originals.
- **Seven files kept their path but changed their hash, in import lines only (section 3.1):** `dc2_pipeline`,
  `dc2_run`, `g3_final`, `nets`, `pd_arch`, `recordings` and `u1_adapt`.

**Why none of the four is read by the model:**
- **No data or state:** each file is one docstring. Before the move, Python executed it on import, and it
  set only the package's `__doc__`.
- **They no longer exist:** after the move they are gone, and the repro trace's audit hook recorded every file
  each step opened and every module it loaded.
- **The repro shows it:** the 53 `pipeline` modules its steps loaded include none of the removed packages.
  There were 0 unlisted inputs, and the decode is EXACT.

### 2.2 The module count: 247 to 246

**No code module was lost.** The difference of one is in package markers:
- **Removed, six `__init__.py` files:** `branches`, `clean`, `models`, `realtime`, `splits` and
  `constrained/attempts`.
- **Added, five `__init__.py` files:** `retired/` and its four subfolders (`constrained`, `identify`,
  `models`, `splits`).
- **Everything else:** every other module was kept (207) or moved (48).

**Did tracking use the removed markers?**
- **Content:** five of the six hold only a docstring. `constrained/attempts/__init__.py` was tracking's, with
  a docstring that says how to import the attempts.
- **What tracking imported:** only modules inside those packages, never the markers' content. Every such
  import now names the new module (section 3.1).
- **Today's tracking code:** it loads none of them (sections 2.1 and 3.5).

## 3. What Monitor's checks do not cover

### 3.1 (4a) The code diffs: imports and path strings only

**The check:** `runs/dc2_results/restructure_check/diff_check.py` translates every old line through the map.
- **What counts as path-only:** a change where the old line, translated through the moves file (its modules,
  its file paths, the `from a import b` form and the `"a" / "b.py"` parts form), equals the new line.
- **What else it does:** it lists every other change for reading.
- **Its output:** `DIFF_CHECK.json`.

**Scope:** 77 tracking code files changed between `5782af8` and `6769f8c`.
- **What is counted:** content changed, so the 13 byte-identical renames are left out, as are identification's files.
- **The split:**
  - `pipeline/live/` 16;
  - `pipeline/constrained/` 9;
  - `pipeline/io/` 2;
  - `pipeline/retired/` 20;
  - `scripts/` 3;
  - `tools/` 1;
  - `tests/` 26.

**62 files are path-only.** These include every file under `pipeline/live/`, `pipeline/constrained/` and
`pipeline/io/`, the app and the model.

**The other 15, each read:**

| files | the change | output changed? |
|---|---|---|
| the 7 retired modules `d4_headline`, `d5_train_room_a`, `d6_lock_commit`, `e1_switch`, `e2_switch`, `f3_render`, `t8_calib` | `REPO_ROOT` takes one more `os.path.dirname`, because each file is now one folder deeper (`pipeline/retired/constrained/`) | no: it is the same repository root, a path fix |
| `tests/test_fourth_receiver.py` | `from pipeline.realtime import engine` became `from pipeline.live import realtime_engine as engine` | no: an import, aliased to its old local name |
| `tests/test_cross_pairing_key.py`, `test_no_shadowed_stage_loads.py`, `test_lock_is_causal.py`, `test_render_rules.py` | each now globs or reads `pipeline/retired/constrained/` where it read `constrained/attempts/` or `constrained/` | no: tests only |
| `tests/test_track_entrypoint.py` | the list of allowed packages is now today's (`io`, `constrained`, `live`, `identify`, `retired`) | no: test only |
| `tests/test_model_freeze.py`, `tests/test_f4_render.py` | a pinned file is checked at the base commit, and its current version may differ only in path lines (`tests/_restructure.py`) | no: test only |

**Two more files, untracked and tracking's:** Monitor rewrote one import line in each. There is no git base
to diff against.
- `tests/_live_checks.py`: `pipeline.io.windows`.
- `tests/test_live_stream.py`: `pipeline.io.clean`.
- **Both run:** the live tests pass (section 3.4).

### 3.2 (4b) The display, byte for byte

**How the replays were run:** with K1g on the causal clock, on the restructured code, and with the cell's
environment and one thread, as the committed logs were made.
- **Where they wrote:** the app's own replay function (`app_replay.session_inner`) was pointed at
  `runs/dc2_results/restructure_check/replay/`, so no committed log was overwritten
  (`restructure_check/app_check.py`).
- **The result:** every log is byte-identical to the committed one.

| replay | the committed log | log bytes | identical |
|---|---|---|---|
| A3, final, semi (PA5) | `final/semi_disp-K1g_causal_realtime_screen/03__participant_PA5_TEST_walk.jsonl` | 149,009 | **yes** |
| B2, final, semi (PA2) | `final/semi_disp-K1g_causal_realtime_screen/B2__participant_PA2_walk.jsonl`, and the teaching pack's `final/semi_disp-K1g_causal/` | 151,627 | **yes, both** |
| zero-shot B2, semi (PA2) | `zeroshot/semi_disp-K1g_causal/B2__participant_PA2_walk.jsonl` | 145,369 | **yes** |
| B2, final, fully constrained (PA2) | `final/full_disp-K1g_causal/B2__participant_PA2_walk.jsonl` | 149,437 | **yes** |
| B2, final, unconstrained m = 4 (PA2) | `final/unconstrained_m4_disp-K1g_causal/B2__participant_PA2_walk.jsonl` | 218,670 | **yes** |

**No log differs, so none differs only by paths.**
- **The summaries:** beside the wall-clock timings, they differ only in `realtime`. It is true for the two
  committed render logs, which were real-time, and false here. Recorded paths (the end head's file) are
  identical.
- **Every walk's lines:** the dot, every frame of it, the locks, the committed lines and the detections are
  the same.

### 3.3 (4c) The teaching pack

**The export:** the app's own export (`app_teaching.inner`), with v3's settings: the K1g unconstrained log,
B2 PA2, written to `restructure_check/teaching/teaching_pack.json`. Its replay log also went into the
check folder.
- **The result:** compared field by field with `reports/teaching_pack_app_v3_2026-10-01.json`, the **only
  difference is `made`** (01:24 against 12:22).
- **Recorded paths:** none differs.
- **The plumbing check:** 20 / 20 committed lines and 20 locks equal to FC.

### 3.4 (4d) Stream mode

**The run:** on a quiet machine (Identification paused by agreement, 12:30 to 12:41), one B2 recording (PA5)
was streamed.
- **What ran:** the app's own stream function (`stream_source.stream_inner`) at its recorded pace, through the
  boards' ingestion path (`run_capture`, the parser, the queue, the rig's consumer). The screen was recorded.
- **Where it wrote:** `restructure_check/stream/stream_disp-K1g/`. Then its own capture was re-replayed
  through the harness (`stream_source.rereplay_inner`).

| check | result |
|---|---|
| pre-flight, in stream mode (the baseline judged against the recording's start) | **ALL ok**, every check of the boards' pre-flight, including both replay gates and all 265 + 271 trace hashes |
| ran to the end | **yes**: exit 0, 6.1 min, 20 walks, 20 committed lines, 20 locks |
| packets | **162,899 parsed, 0 dropped, 0 read errors**; RX1, RX2 and RX3 all PASS the capture's gates |
| its own capture, re-replayed through the harness | **identical, row for row** (1,376 rows) |
| against the K1g replay of the same recording, for the record | 19 / 20 committed lines and 18 / 20 locks equal. These are the wall-clock stamps, as in this morning's streamed run (19 and 20 on PA5 then). The identical re-replay is the check that the app is the same |

**The live tests** pass on the restructured code: 282 passed, 10 skipped, with the four test files of
section 4. They include the two untracked tests Monitor rewrote.

### 3.5 (4e) The retired/ folder

**The modules moved into `retired/` from tracking's folder and the shared early folders** (27, by origin):

| from | modules |
|---|---|
| `pipeline/constrained/` (7), tracking's | `d4_headline`, `d5_train_room_a`, `d6_lock_commit`, `e1_switch`, `e2_switch`, `f3_render`, `t8_calib` |
| `pipeline/constrained/attempts/` (17), tracking's | `lock_horizon`, `rc1_diagnostics`, `rc4_calibration`, `rc5_renders`, `rc8_demo`, `rc9_contrast`, `re4_semibounded`, `rescore`, `stage1_pace`, `stage4_unified`, `stage5_live`, `t6_lockdiag`, `t7_lockarms`, `t9_lengthnorm`, `y2a_causal`, `z3a_linkprod`, `z3b_g100native` |
| `pipeline/models/` (1), shared | `fusion` |
| `pipeline/splits/` (2), shared | `assemble`, `split_by_file` |

**None is reached from the live app, G2 or the repro:**
- **Statically** (`restructure_check/reach_check.py`): every import anywhere in a file, including inside
  functions, plus every `pipeline.x.y` module named in a string, as `-m` calls name them, followed
  transitively. Output: `REACH_CHECK.json`.

  | start | files reachable | under `retired/` |
  |---|---|---|
  | every module of `pipeline/live/` | 142 | 0 |
  | G2 (`final_model`, `gates`) | 113 | 0 |
  | the repro (`pd_repro_trace`) | 112 | 0 |

- **In the runs:**
  - **The repro:** across all its steps on all three cells, its traces loaded 53 `pipeline` modules, none
    under `retired/` or the removed packages.
  - **The hash lists and model sets:** they hold no `retired/` file. A read of one would have been an
    unlisted input, and there were none.

## 4. (5) The 7 test failures that predated the move

**All 7 are tracking's checks, and none was a figure.**
- **What they are:** 6 failures concern tracking's files. The seventh test also flagged one identification
  file, which Identification audited and worded itself.
- **The fixes:** each is in the tests or the freeze record. No model or figure changed.
- **The result:** the four test files now pass, 246 passed and 9 skipped.

| test | cause | what was done |
|---|---|---|
| `test_model_freeze::test_documents_change_only_through_a_recorded_addendum` | `reports/RENDER_RULES.md`, a DC2 freeze document, had changed twice by Uzayr's decisions. The freeze hash `2cad86f6` was kept until `63987d1` (30 Sep, rewritten for the app, rules unchanged in substance). It became `b956c4ac`, then `50079193` at `431b180` (1 Oct, rule 2a's K1g form) | **The freeze record:** `runs/TRACKING_FROZEN_2026-09-23h_ADDENDUM_C.json` (dated, clock read). It records the new hash, the three-step history with commits, the decisions (`BRIEF_LIVE_APP_3`, `BRIEF_LIVE_APP_4`, this brief), "no model change", and "post hoc: yes". **The test:** it reads any addendum's `documents_new_sha256` (it read only the pre-registration's before) |
| `test_cross_pairing_key` (4: `pd_decode.py`, `pd_render.py`, `pd_report.py`, `pd_v2.py`) | a stale registry: the corrected tracker's modules (added 28 to 30 Sep) build session-stem-pass keys and were never classified | each site was read and classified: `pd_decode` and `pd_render` ONE_PAIRING (one cell per run); `pd_report` ROWS (keys go into lists; its one dict compares one cell with one fold, asserted 120); `pd_v2` PER_PAIRING (rebuilt per network set and session). No key needed fixing |
| `test_pass_pairing_key::test_every_pass_id_keyed_dict_is_classified` | a stale registry: five tracking files written after the last audit, `pd_subst`, `pd_render`, `app_teaching`, `final_model` and `app_score`, plus identification's `idrelabel.py` | **Tracking's five:** each read in context and classified PER_RECORDING. Each dict is built from one recording, and `app_teaching` filters the session's rows to its one stem. **`idrelabel.py`:** audited by Identification, and added in its own words |
| `test_report_consistency::test_readme_quotes_the_delivered_system_not_the_weakest_arm` | a stale test. It checked the README against the DC2 semi-bounded decoder (62.50 % [30.00, 86.67]), the delivered system until 30 Sep. Monitor's README rewrite quotes today's delivered system, the live app. Its figures match the app's own score: B2 93.33 % [88.33, 97.50] committed and 72.50 % [63.33, 80.00] lock, as in `SCORE_B2.json` | **The test now checks:** that the README quotes the live app's B2 headline, read from its committed score, and still names the DC2 record's pre-registered 62.50 %. **Is it a figure inconsistency?** No |

## 5. The old paths, translated (for the thesis's citations)

**The scope:** every moved file or module that a tracking report cites, by its old path (with or without
`pipeline/`) or its old dotted module.
- **Which reports:** `reports/` and `reports/attempts/`, less identification's own files and the restructure's
  records; 109 files.
- **How it was built:** `restructure_check/path_table.py`, from `reports/PIPELINE_MOVES_2026-10-01.json`.
- **Its output:** `PATH_TABLE.json`, with the full list of reports per path.

**The reports are not edited.** Read an old citation through this table. `reports/PINNED_FILES.txt` is shared,
so it also cites some identification files; they are listed too.

| old path (old module) | new path (new module) | tracking reports citing it |
|---|---|---|
| `pipeline/branches/gate.py` (`pipeline.branches.gate`) | `pipeline/constrained/gate.py` (`pipeline.constrained.gate`) | 5: ARCHITECTURE_TRACKING_FINAL_2026-09-29.md, DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, ROOM_TRANSFER_AUDIT_2026-09-22.md, and 1 more |
| `pipeline/clean/common.py` (`pipeline.clean.common`) | `pipeline/io/clean.py` (`pipeline.io.clean`) | 6: ARCHITECTURE_TRACKING_FINAL_2026-09-29.md, BRIEF_render_and_prepress_2026-09-22.md, DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, and 2 more |
| `pipeline/constrained/attempts/rescore.py` (`pipeline.constrained.attempts.rescore`) | `pipeline/retired/constrained/rescore.py` (`pipeline.retired.constrained.rescore`) | 1: POST_DC2_REFACTOR.md |
| `pipeline/constrained/d4_headline.py` (`pipeline.constrained.d4_headline`) | `pipeline/retired/constrained/d4_headline.py` (`pipeline.retired.constrained.d4_headline`) | 1: POST_DC2_REFACTOR.md |
| `pipeline/constrained/d5_train_room_a.py` (`pipeline.constrained.d5_train_room_a`) | `pipeline/retired/constrained/d5_train_room_a.py` (`pipeline.retired.constrained.d5_train_room_a`) | 2: DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt |
| `pipeline/constrained/d6_lock_commit.py` (`pipeline.constrained.d6_lock_commit`) | `pipeline/retired/constrained/d6_lock_commit.py` (`pipeline.retired.constrained.d6_lock_commit`) | 1: CORRECTION_drawn_lock_2026-09-23.md |
| `pipeline/constrained/f3_render.py` (`pipeline.constrained.f3_render`) | `pipeline/retired/constrained/f3_render.py` (`pipeline.retired.constrained.f3_render`) | 5: DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, PREREG_display_phase_2026-09-24.md, SEMIBOUNDED_STATE.md, and 1 more |
| `pipeline/constrained/t8_calib.py` (`pipeline.constrained.t8_calib`) | `pipeline/retired/constrained/t8_calib.py` (`pipeline.retired.constrained.t8_calib`) | 4: DC2_DEPENDENCY_CLOSURE.txt, DC2_PROTOCOL_2026-09-18.md, PINNED_FILES.txt, RECORD_TRACKING.md |
| `pipeline/identify/id26b_cnn_diag.py` (`pipeline.identify.id26b_cnn_diag`) | `pipeline/retired/identify/id26b_cnn_diag.py` (`pipeline.retired.identify.id26b_cnn_diag`) | 1: PINNED_FILES.txt |
| `pipeline/identify/idgp_bank.py` (`pipeline.identify.idgp_bank`) | `pipeline/retired/identify/idgp_bank.py` (`pipeline.retired.identify.idgp_bank`) | 1: PINNED_FILES.txt |
| `pipeline/identify/idgp_checkin.py` (`pipeline.identify.idgp_checkin`) | `pipeline/retired/identify/idgp_checkin.py` (`pipeline.retired.identify.idgp_checkin`) | 1: PINNED_FILES.txt |
| `pipeline/identify/idgp_checks.py` (`pipeline.identify.idgp_checks`) | `pipeline/retired/identify/idgp_checks.py` (`pipeline.retired.identify.idgp_checks`) | 1: PINNED_FILES.txt |
| `pipeline/identify/idmax_checkin.py` (`pipeline.identify.idmax_checkin`) | `pipeline/retired/identify/idmax_checkin.py` (`pipeline.retired.identify.idmax_checkin`) | 2: ARCHIVE_CODE.md, RECORD_CLEANUPS.md |
| `pipeline/identify/rehearsal_check.py` (`pipeline.identify.rehearsal_check`) | `pipeline/retired/identify/rehearsal_check.py` (`pipeline.retired.identify.rehearsal_check`) | 1: PINNED_FILES.txt |
| `pipeline/models/heads.py` (`pipeline.models.heads`) | `pipeline/constrained/heads.py` (`pipeline.constrained.heads`) | 3: DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, TRACKING_MODEL_ARCHITECTURE_2026-09-28.md |
| `pipeline/models/link_cnn.py` (`pipeline.models.link_cnn`) | `pipeline/constrained/link_cnn.py` (`pipeline.constrained.link_cnn`) | 6: ARCHITECTURE_TRACKING_FINAL_2026-09-29.md, DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, PREREG_prepress_v2_2026-09-22.md, and 2 more |
| `pipeline/realtime/engine.py` (`pipeline.realtime.engine`) | `pipeline/live/realtime_engine.py` (`pipeline.live.realtime_engine`) | 5: DC2_DEPENDENCY_CLOSURE.txt, FIX_one_lattice_2026-09-23.md, LIVE_SYSTEM_DESIGN_2026-09-25.md, PINNED_FILES.txt, and 1 more |
| `pipeline/realtime/replay.py` (`pipeline.realtime.replay`) | `pipeline/live/realtime_replay.py` (`pipeline.live.realtime_replay`) | 3: DC2_DEPENDENCY_CLOSURE.txt, PINNED_FILES.txt, RECORD_CLEANUPS.md |
| `pipeline/realtime/rig_run.py` (`pipeline.realtime.rig_run`) | `pipeline/live/rig_run.py` (`pipeline.live.rig_run`) | 5: DC2_DEPENDENCY_CLOSURE.txt, LIVE_SYSTEM_DESIGN_2026-09-25.md, PINNED_FILES.txt, TRACKING_CHECKS_2026-09-29.md, and 1 more |
| `pipeline/realtime/tracker_live.py` (`pipeline.realtime.tracker_live`) | `pipeline/live/tracker_live.py` (`pipeline.live.tracker_live`) | 7: DC2_DEPENDENCY_CLOSURE.txt, DC2_FIELD_CHECKLIST.md, FIX_one_lattice_2026-09-23.md, LIVE_SYSTEM_DESIGN_2026-09-25.md, and 3 more |
| `pipeline/splits/windows.py` (`pipeline.splits.windows`) | `pipeline/io/windows.py` (`pipeline.io.windows`) | 9: ARCHITECTURE_TRACKING_FINAL_2026-09-29.md, DC2_DEPENDENCY_CLOSURE.txt, DC2_FIELD_CHECKLIST.md, PINNED_FILES.txt, and 5 more |

**The removed packages** are cited as folders too:
- `pipeline/branches/`;
- `pipeline/clean/`;
- `pipeline/models/`;
- `pipeline/realtime/`;
- `pipeline/splits/`;
- `pipeline/constrained/attempts/`.

Each folder's files are in the table above, or kept at the same name in the four folders.

**A bare module name** (for example `f3_render`) resolves by name, since the file names are kept. Four
names changed:
- `engine` is now `realtime_engine`;
- `replay` (of `realtime/`) is now `realtime_replay`;
- `common` (of `clean/`) is now `io/clean`;
- `windows` keeps its name, in `io/`.

## 6. Files and commits

| file | what |
|---|---|
| `reports/BRIEF_RESTRUCTURE_CHECK_2026-10-01.md` | the instruction, verbatim (held outside the repository until 12:09) |
| `reports/RESTRUCTURE_CHECK_TRACKING_2026-10-01.md` | this report |
| `runs/dc2_results/restructure_check/` | the scripts: `diff_check.py`, `app_check.py`, `reach_check.py`, `path_table.py`; their outputs: `DIFF_CHECK.json`, `APP_CHECK.json`, `REACH_CHECK.json`, `PATH_TABLE.json` and `.md`; the replays, teaching pack, stream and logs (the raw captures are git-ignored) |
| `runs/TRACKING_FROZEN_2026-09-23h_ADDENDUM_C.json` | the freeze record for RENDER_RULES (section 4) |
| `tests/test_model_freeze.py` | reads an addendum's `documents_new_sha256` |
| `tests/test_cross_pairing_key.py`, `tests/test_pass_pairing_key.py` | the 2026-10-01 audit's classifications (identification's `idrelabel.py` in its own words) |
| `tests/test_report_consistency.py` | the README checked against the live app's headline |
| `QUEUE.md`, `STATE.md`, `reports/DEVLOG_TRACKING_2026-09-28.md` | the records; `STATE.md` says the thesis cites `tracking-final-2026-10-01` |

**Not committed:**
- **`tests/_live_checks.py` and `tests/test_live_stream.py`,** which Monitor rewrote. They are untracked like
  the other `tests/test_live_*.py`, so they stay as they were.
- **The chain logs.**

**The tags:**
- **`tracking-final-2026-10-01`:** on `5782af8`.
- **`tracking-final-restructured-2026-10-01`:** on this check's commit.

**This check's commit:** `395ddb1` (12:46), tagged `tracking-final-restructured-2026-10-01`.
