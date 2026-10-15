# RECORD_CLEANUPS: the repository cleanups, consolidated

Written 2026-09-24 09:49 SAST. The plans, briefs and logs of every cleanup of this repository, verbatim (headings demoted two levels), in date order. The restructure of 2026-09-24 that created `attempts/` folders is the last section, written for this record.

## Index

| source | date | one-line summary | original |
|---|---|---|---|
| [CLEANUP_PLAN_2026-09-18.md](#cleanup-plan-2026-09-18md) | 2026-09-18 | The first cleanup's plan. | combined here; at the tag `pre-cleanup:reports/CLEANUP_PLAN_2026-09-18.md` |
| [CLEANUP_LOG_2026-09-18.md](#cleanup-log-2026-09-18md) | 2026-09-18 | What the first cleanup did, including its two failures. | combined here; at the tag `pre-cleanup:reports/CLEANUP_LOG_2026-09-18.md` |
| [CLEANUP_BRIEF_2026-09-23.md](#cleanup-brief-2026-09-23md) | 2026-09-23 | The repository map and cleanup brief of 2026-09-23. | combined here; at the tag `pre-cleanup:reports/CLEANUP_BRIEF_2026-09-23.md` |
| [CLEANUP_LOG_2026-09-24.md](#cleanup-log-2026-09-24md) | 2026-09-24 | What the cleanup of 2026-09-24 did: 93 GB to 36 GB, the history rewrite, the push. | combined here; at the tag `pre-cleanup:reports/CLEANUP_LOG_2026-09-24.md` |
| [The attempts/ restructure, 2026-09-24](#the-attempts-restructure-2026-09-24) | 2026-09-24, 09:29 to 10:15 | Past work moved into attempts/ folders in pipeline, reports and runs; three combined records; one figures folder. | written for this record |

---

## CLEANUP_PLAN_2026-09-18.md

**Source:** `reports/CLEANUP_PLAN_2026-09-18.md`, 2026-09-18. **SHA-256:** `3207e71bb333c87754f439883638c50ccaf5a89f9339757293f75e6e5e6a8bf8`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### CLEANUP PLAN, 2026-09-18

Phase 1 of `tracking_cleanup_rerender_prompt_2026-09-18.md`. Written before anything moved.
Branch `cleanup-2026-09-18` from `identification-2026-09-18`. Nothing in this plan is executed
until the plan is complete and committed.

Scale: repository 28 G, of which `data/` is 16 G and `runs/` is 6.8 G. 90 modules under
`pipeline/`, 67 files under `reports/`, 549 image files of which 525 are already inside
`testing/`.

#### 0. Three places where the mechanical rule is wrong, and what I do instead

The brief's rule in 1.2 is "every module outside the import closure is MOVE-TO-TESTING". Applied
literally it retires things the brief itself protects elsewhere, so it is qualified in three
places. Each is a decision, and each is stated here rather than taken silently.

1. **`pipeline/identify/` is exempt.** The closure from `id5_report` does not reach
   `id1_foundations`, `id2_ladder`, `id3_embeddings`, `id4_verification`, `id6_extras` or
   `features`, because the report module reads their saved output rather than importing them.
   The brief's hard constraint says the identification branch is current work and is not touched.
   Exempt, all nine files stay.
2. **`pipeline/io/` is exempt.** Only `parse` and `capture_logger` are in the closure, but the
   rest of that directory is the instrument layer: `anchors`, `ground_truth`, `rt_calibration`,
   `identify_board`, `check_gain_lock`, `check_channel_filter`, `inspect_capture`. The second
   collection runs on 26 and 27 September, nine days from now, and those are the scripts that
   will be used to run it. Retiring them the week before a collection is the wrong trade. Exempt,
   and the brief separately forbids editing this directory.
3. **Modules a test imports stay.** Eleven modules outside the shipping closure are imported by
   the test suite: `rb1_truth`, `rb8_verify`, `rb9_report`, `stage5_live`, `clean/common`,
   `models/fusion`, `realtime/engine`, `realtime/replay`, `splits/assemble`,
   `splits/split_by_file`, `splits/windows`. Moving them means moving or rewriting their tests,
   which trades a green suite for tidiness. They stay.

`__init__.py` files stay everywhere, in every case, because moving one breaks the package.

#### 1.1 Top level and one level down

##### data/, 16 G. Nothing here is deleted, ever.

| path | what it is | action | reason |
|---|---|---|---|
| `data/room_A` 2.6 G | raw captures, Room A | **KEEP** | read by the loaders, 5 shipping references |
| `data/windows` 3.2 G | cut windows, `WINDOWS_ROOT` | **KEEP** | read by the loaders, 4 shipping references |
| `data/features` 2.3 G | derived feature cache | **KEEP** | no loader reads it, but it is derived from raw and named in `recordings.py`; a move buys no disk and makes a shipping docstring wrong |
| `data/retired` 3.9 G | `azrah_zaid/{captures,derived}` | **KEEP, untouched** | these are **raw captures of the two retired participants**. Zero shipping references, but the constraint is POPIA and not tidiness, and raw captures are never moved. Not read, not listed, not touched |
| `data/postmortem` 2.0 G | batch 0 run output | **MOVE** to `testing/from_data/postmortem/` | run output that was written into `data/`, not a capture |
| `data/push` 619 M | batch 1 run output | **MOVE** to `testing/from_data/push/` | as above |
| `data/push2` 589 M | batch 2 run output | **MOVE** to `testing/from_data/push2/` | as above |
| `data/push3` 803 M | batch 3 run output | **MOVE** to `testing/from_data/push3/` | as above |

Note on `data/retired`: the brief's classification is RAW CAPTURE or STRAY, and STRAY moves to
`testing/from_data/`. `azrah_zaid/captures` is raw capture by content, so it takes the RAW CAPTURE
branch and stays where it is. It is the one entry where the two rules disagree and the
conservative branch wins.

392 raw capture files hashed before anything moves, in `runs/cleanup/data_hashes_before.txt`.
Every hash is verified again in 2.1. One difference stops the cleanup.

##### runs/, 6.8 G

| path | what it is | action | reason |
|---|---|---|---|
| `runs/artefacts/features` 6.3 G | 18 walk feature memmaps | **KEEP** | the 1 s cache every decode reads |
| `runs/artefacts/posteriors` 384 M | 72 full posteriors | **KEEP** | the replay harness rebuilds every headline from these |
| `runs/artefacts/models` 84 M | 252 trained link CNNs | **KEEP** | without these nothing is reproducible |
| `runs/artefacts/MANIFEST.md` | artefact index | **KEEP** | named by `TRACKING_FROZEN_2026-09-17.json` |
| `runs/artefacts/rssi_full`, `gate_energy` | 8.6 M | **KEEP** | read by the gate and the diagnostics |
| `runs/*FROZEN*.json` (3) | frozen results | **KEEP, byte-identical** | hashed before and after |
| `runs/constrained/<stage>` (40 dirs, 32 M) | per-stage output | **KEEP** | small, and each is the evidence behind a report line |
| `runs/constrained/demo` 16 M | the current 13 videos and posters | **KEEP until 5.1 passes**, then superseded ones deleted per 5.4 | they are the acceptance reference for the re-render |
| `runs/identify` 392 K | identification output | **KEEP, untouched** | current work |

No `runs/` entry falls into the brief's "none of those" category, so nothing under `runs/` is
moved or deleted in phase 2.3. The size report for 2.3 will say so rather than inventing a move.

##### pipeline/, 3.4 M, 90 modules

59 stay: 33 in the shipping closure, 17 added by the test suite, 9 exempt under section 0.
**24 retire** to `testing/pipeline_retired/` preserving relative path:

- `pipeline/constrained/` (22): `null_config_probe`, `rb0_preflight`, `rb2_decoder`,
  `rb2b_stride`, `rb2c_alpha`, `rb2d_retrain`, `rb4_bout`, `rb5_calibrate`, `rb6_crossing`,
  `rc2_latency`, `rc3_column`, `rc3b_sweep`, `rc6_verify`, `rc7_static`, `stage0_preflight`,
  `stage2_emissions`, `stage3_paths`, `stage6_demo`, `stage7_optional`, `stage8_verify`,
  `stage9_archive`, `stage10_report`
- `pipeline/models/dann.py` (1), now `testing/pipeline_retired/pipeline/models/dann.py`
- `pipeline/splits/named.py` (1), now `testing/pipeline_retired/pipeline/splits/named.py`

**`dann.py` note.** Stage 8.4 of the rebuild was written to retire this file automatically when it
had no importers, and it reported `moved False` because its own `grep -rn models.dann pipeline/`
matched its own source lines and counted them as importers. There are no real importers. This move
is what that stage intended, not a reversal of it.

**Flagged consequence, stated rather than buried.** Those 22 constrained modules are the stages
that produced the frozen artefacts: `rb2_decoder` trained the link CNNs, `rb5_calibrate` ran the
calibration ladder, `rc7_static` produced the static verification headline. After the move the
cleaned tree can *rescore* every headline from artefacts, which is what `rescore.py` does, but it
cannot *retrain from raw* without restoring them. They are in git and restoring is one command,
recorded in the cleanup log:

    git mv testing/pipeline_retired/pipeline/constrained/<module>.py pipeline/constrained/

This is a real cost for a thesis and it is accepted deliberately, because the alternative is that
"cleaned" means nothing. The provenance of every frozen number stays legible through
`runs/artefacts/MANIFEST.md` and the appendices folded in at 2.5.

##### reports/, 1.4 M, 67 files

| class | files | action |
|---|---|---|
| REPORT | `DECODER_REBUILD_2026-09-18.md` | becomes `TRACKING_2026-09-18.md` |
| REPORT | `IDENTIFICATION_2026-09-18.md` | stays, appendix appended only |
| INSTRUMENT | `DC2_PROTOCOL_2026-09-18.md` | stays, printable sheet |
| APPENDIX to tracking | `APPENDIX_crossing_geometry.md` | fold in, the tracking report links it by name |
| APPENDIX to tracking | `FINDINGS_stage{0,1,2,2b,2c,2.4,3,3.2,4,5,6,7,8,9,10}.txt` (15) | fold in, dated, stage order |
| APPENDIX to identification | `FINDINGS_stage{C,D,E,F,G,H}.txt` (6) | fold in |
| RESULTS | `results.csv`, `recording_timeline.md`, `gate_inspection.md`, `protocol_facts.md`, `METHOD_LEDGER.md`, `NULL_CONFIG_PROBE.md`, `ROOM_B_PLACEMENT.md` | `ROOM_B_PLACEMENT.md` folds into the DC2 sheet because the second collection needs it in hand; the rest fold beside the section that discusses them |
| BRIEF | 5 `*_prompt_*.md`, `BRIEF_MAPPING.md` | `testing/briefs/` |
| SUPERSEDED REPORT | `CONSTRAINED_FINAL_2026-09-17.md`, `HANDOVER_2026-09-17.md`, `HANDOVER_2026-09-18.md`, `PERSON_ID_STATE_2026-09-18.md`, `OPEN_PROBLEMS_2026-09-17.md`, `FOR_DECISION_CHAT_2026-09-17.md`, `ARCHIVE_CLASSIFICATION.md`, `STATIC_LOCALISATION_PRIOR_WORK.md`, `DEMO_NOTES*.md` (3), `SUMMARY_REBUILD.txt`, `CLEANUP_2026-09-18.txt`, `OVERNIGHT_SUMMARY_2026-09-18.txt`, `SUMMARY.txt` | `testing/scratch/` |
| SCRATCH | `BATCH_STARTED.txt`, `PHASE.txt`, `QUEUE.md`, `status.txt`, `STAGE_TIMES.json`, `*.pid` (3), `SESSION_ACTIVE`, `CHECKIN_LOG.md` | `testing/scratch/`, pid files deleted |
| LIVE | `CHECKIN.md`, `ETA.txt`, `HEADLINES.txt` | stay |

On folding the identification findings: the brief says the identification report "stays as it is"
and also that `reports/` ends with nothing but the listed files. Appending an appendix is additive
and edits no existing sentence, so both hold. The alternative, retiring the stage findings of
current work into `testing/`, is worse.

`SUMMARY.txt` moves to scratch because phase 6.3 writes a new one. This file has been clobbered by
a stage generator three times in this project, so the new one is written by hand, once, at the end.

##### Figures, 24 outside testing/

| file | action | reason |
|---|---|---|
| `Layout.png`, `Paths.png` at root | **KEEP at root** | these are **inputs**, read by `pipeline/io/ground_truth.py`. They are geometry, not output. Not renamed, not moved |
| `reports/fig/architecture.png` | **KEEP** | named by `TRACKING_FROZEN_2026-09-17.json` |
| `reports/fig/confusion_*.png` (8) | **MOVE** to `testing/figs_retired/` | referenced by no current report; produced by `stage10_report.py`, itself retiring |
| `runs/constrained/demo/*.png` (13) | **CANONICAL**, regenerated in phase 5 | video posters for the demonstration set |

Neither current report embeds an image, so the canonical set is the demonstration posters plus the
two geometry inputs plus `architecture.png`. `reports/FIGURES.md` will say exactly that, so the
next reader does not go looking for figures that were never there.

The renaming scheme in 2.4 applies to the canonical set only. `Layout.png` and `Paths.png` are
**not** renamed because a shipping module opens them by name and the brief forbids editing that
module.

##### Root

`README.md`, `STATE.md`, `Makefile`, `requirements.txt`, `.gitignore`, `Layout.png`, `Paths.png`
and the package directories. `.DS_Store` deleted and added to `.gitignore`. Nothing else is loose.

##### scripts/, 14 shell scripts

One survives as the render entry point per 1.6, plus `heartbeat.sh` and `track.py`. The other
eleven are batch chains for batches that are finished: `run_bounded_demo.sh`, `run_completion.sh`,
`run_constrained.sh`, `run_d1.sh`, `run_d1_after_demo.sh`, `run_demo_then_static.sh`,
`run_final.sh`, `run_identify.sh`, `run_rc9_then_report.sh`, `run_rebuild.sh`,
`resume_rebuild.sh`, `finalise_report.sh`. All to `testing/scratch/scripts/`.

#### 1.2 Import graph, by AST walk

Entry points, three as the brief specifies, with the render entry counted as two modules because
the contrast clip is produced by a second module today and 1.6 resolves that:

- `pipeline.constrained.rescore`, the replay harness that rebuilds every headline from artefacts
- `pipeline.constrained.rc8_demo` and `pipeline.constrained.rc9_contrast`, the render
- `pipeline.identify.id5_report`, the identification entry

Closure 33 modules, saved with the full list in `runs/cleanup/import_closure.json`. Retire set and
the reasons above in `runs/cleanup/retire_candidates.json`. Walked with `ast.parse`, not grep.

#### 1.3 Artefact graph

Every file under `runs/` is a FROZEN json, an artefact a FROZEN json references, or an artefact a
current report references. The "none of those" category is empty. Nothing under `runs/` moves or
is deleted, except the superseded renders at 5.4 once the new set exists.

#### 1.4 Figures

Covered in the table above. `reports/FIGURES.md` is written at 2.4 with, for each canonical
figure, the filename, one sentence on what it shows, the report section that uses it, and the run
and script that produced it.

#### 1.5 Reports

Covered in the table above.

#### 1.6 The demonstration entry point

| module | what it does | produced the current set? |
|---|---|---|
| `stage6_demo` | the first demo stage, live self-segmenting mode | no, superseded |
| `rb7_demo` | rebuild-era demo, live mode | no, superseded; still imported by `rc8_demo` for helpers |
| `rc5_renders` | the render fixes, including the red-runs-ahead correction | no, but `rc8_demo` imports `red_track` from it |
| `rc8_demo` | boundaries-given set, 12 of the 13 videos at 23:14 to 23:22 on 17 September | **yes** |
| `rc9_contrast` | the uncalibrated against calibrated clip, 00:07 on 18 September | **yes**, the 13th |

They differ in more than bug fixes. `stage6_demo` and `rb7_demo` render the live unbounded mode,
which finds 4 of 120 passes and is not demonstrable; `rc8_demo` renders the boundaries-given mode,
which is the headline. That is a change of subject, not a fix, so `stage6_demo` retires and is not
deleted.

**Decision: one entry point, `scripts/render_demo.sh`, calling `pipeline.constrained.rc8_demo`,
with the contrast clip folded into that module from `rc9_contrast` so a single command produces
all 13 outputs.** No staging step. `rc5_renders` and `rb7_demo` stay in `pipeline/constrained/`
because `rc8_demo` imports from both; they are libraries to it, not stages. `rc9_contrast` is
deleted only if phase 5.1 proves the folded version reproduces its clip exactly, and retired to
`testing/` otherwise, per 2.6.

#### Order of execution

2.1 data moves and hash re-verification, and a full stop if one hash differs. 2.2 pipeline moves
then the suite green. 2.3 runs, which is a no-op with a size report. 2.4 figures and FIGURES.md.
2.5 reports consolidation with every link verified. 2.6 the render fold. 2.7 root, README and
STATE. 2.8 the cleanup log. Checkpoint commit after each.

Expected recovery: about 4.0 G moved out of `data/`, which is a move and not a deletion, so the
repository stays 28 G and what changes is that `data/` holds only captures. Actual deletion is
confined to `.DS_Store`, three pid files, and the superseded renders at 5.4.

---

## CLEANUP_LOG_2026-09-18.md

**Source:** `reports/CLEANUP_LOG_2026-09-18.md`, 2026-09-18. **SHA-256:** `b8aa343ceedb937bc19dd5559f3850ff4fdac22f9a247ee7d330b817f5c06ed1`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### CLEANUP LOG, 2026-09-18

What phase 2 actually did, against `CLEANUP_PLAN_2026-09-18.md`. Deviations from the plan are
marked and explained. Two things went wrong and both are recorded here in full.

#### The two failures, first, because they are the part worth reading

##### 1. I deleted two files under data/, against a hard constraint

The constraint is absolute: nothing under `data/` is ever deleted. At step 2.7 I ran
`find . -name '.DS_Store' -delete` to tidy the repository root. It was not scoped, so it also
removed `data/room_A/.DS_Store` and `data/room_A/session_01/.DS_Store`.

- **Verified scope.** The second hash check found exactly two differences out of 392, both
  deletions, zero files altered. The other 390 raw capture hashes are identical.
- **Recoverable?** No. `data/` is gitignored so they were never in git, and `-delete` does not
  use the trash.
- **Impact on the record.** None that is measurable. A `.DS_Store` holds Finder window and icon
  positions. It contains no capture data, and no module in `pipeline/` or `tools/` reads one.
  The captures themselves, 390 files of `.bin` and `.json`, are byte-identical.
- **Why it still counts.** The constraint is not "do not damage the science", it is "do not
  delete under data/", precisely so that this judgement never has to be made under pressure.
  I made it anyway by writing an unscoped command.
- **Cause and fix.** The tidy step and the protected tree were not separated. Any future sweep
  is written as `find . -path ./data -prune -o -name '.DS_Store' -print -delete`.

##### 2. Moving files out of data/ swept 4.0 GB into git

`data/` is gitignored. `testing/` is not. So moving `postmortem`, `push`, `push2` and `push3`
from one to the other made 142 files of derived `.npz` and `.npy` tracked for the first time,
and the phase 2.1 commit carried them. `.git` went from 4.9 GB to 8.9 GB. The operator's
original complaint about this repository was its size, so this made the actual problem worse
while appearing to fix it.

Caught by a size check after phase 2.7, not by anything in the plan. Fixed by rewinding that
one commit, adding `testing/from_data/` to `.gitignore` so the files stay exactly as
unversioned as they were under `data/`, recommitting, and expiring the orphaned blobs.
`.git` is now **498 MB**. The files themselves were never touched on disk.

#### Hashes

| check | result |
|---|---|
| 392 raw capture hashes before the cleanup | taken, `runs/cleanup/data_hashes_before.txt` |
| after the data moves | **392 of 392 identical** |
| after all of phase 2 | **390 of 392 identical, 2 deleted**, see failure 1 above |
| `runs/TRACKING_FROZEN_2026-09-17.json` | byte-identical |
| `runs/TRACKING_FROZEN_2026-09-18.json` | byte-identical |
| `runs/IDENTIFICATION_FROZEN_2026-09-18.json` | byte-identical |
| `runs/artefacts/MANIFEST.md` | byte-identical |

#### 2.1 data/

| moved | size | files | to |
|---|---|---|---|
| `data/postmortem` | 2.0 G | 37 | `testing/from_data/postmortem/` |
| `data/push` | 619 M | 43 | `testing/from_data/push/` |
| `data/push2` | 589 M | 8 | `testing/from_data/push2/` |
| `data/push3` | 803 M | 50 | `testing/from_data/push3/` |

All four held only `.npz` and `.npy`. Raw captures are `.bin` plus `.json`, so no capture moved.
`data/` now holds `room_A`, `windows`, `features` and `retired`, and nothing else.
`data/retired/azrah_zaid` holds raw captures of the two retired participants: zero shipping
references, and untouched, because it is raw capture and the cost of being wrong there is a
POPIA problem.

#### 2.2 pipeline/

24 modules retired to `testing/pipeline_retired/`, relative paths preserved. 90 modules before,
66 after. Nothing deleted.

**Deviation from the plan, and the plan's method is why.** The plan said the retire set was safe
because an AST walk found no importer. One test broke: `tests/test_stride_isolation.py` imports
`rb2d_retrain` inside a subprocess code **string**, which an AST import walk cannot see. The
brief chose the AST walk over grep for good reason, grep over-matches badly, and this is the
cost of that choice. It was caught by running the suite, not by reading.

The file was **split rather than retired**, because three of its five tests guard the default
artefact roots in `common.py` and `recordings.py`, which still ship and which are what stops a
0.5 s run silently overwriting 6.3 GB of 1 s features. Those three stay. The two that import
`rb2d_retrain` moved to `testing/tests_retired/tests/test_stride_isolation_rb2d.py`.

**Suite: 476 passed, 8 skipped, 0 failed.** Before the cleanup: 476 passed, 9 skipped, 1 failed.
The two tests that moved out account for the difference exactly.

##### Restoring a retired module

The 22 retired `constrained` modules include the stages that produced the frozen artefacts:
`rb2_decoder` trained the link CNNs, `rb5_calibrate` ran the calibration ladder, `rc7_static`
produced the static verification headline. The cleaned tree can **rescore** every headline from
artefacts, which is what `pipeline/constrained/rescore.py` does. It cannot **retrain from raw**
without restoring one:

    git mv testing/pipeline_retired/pipeline/constrained/<module>.py pipeline/constrained/

This is a real cost and it was accepted deliberately at plan time, not discovered afterwards.

#### 2.3 runs/

**No-op, as the plan predicted.** Every file under `runs/` is a frozen json, an artefact a frozen
json references, or an artefact a current report references. The brief's "none of those" category
is empty. 6.8 G before, 6.8 G after. The superseded renders are deleted at 5.4, not here.

#### 2.4 Figures

Eight superseded confusion matrices moved to `testing/figs_retired/`. `reports/fig/` keeps
`architecture.png`, which `TRACKING_FROZEN_2026-09-17.json` names.

**Deviation: nothing was renamed.** The plan's scheme `fig_tracking_<topic>_<date>.<ext>` is not
applied, because every canonical figure is pinned by name where renaming would break it:
`Layout.png` and `Paths.png` are opened by `pipeline/io/ground_truth.py`, which the brief forbids
editing; `architecture.png` is named inside a frozen json that must stay byte-identical; the demo
posters are regenerated by the render, which defines their names. `reports/FIGURES.md` records
this, and records that neither current report embeds an image at all.

#### 2.5 reports/

67 files before, 13 after, which is the brief's list plus this cleanup's own findings files and
the two live life-support files.

| deliverable | built from |
|---|---|
| `TRACKING_2026-09-18.md`, 868 lines | `DECODER_REBUILD_2026-09-18.md` plus appendix A crossing geometry, appendix B fifteen stage findings in stage order, appendix C the method ledger, null probe, gate inspection, recording timeline and protocol facts |
| `IDENTIFICATION_2026-09-18.md`, 169 lines | unchanged body, six stage findings appended as an appendix |
| `DC2_PROTOCOL_2026-09-18.md`, 53 lines | plus `ROOM_B_PLACEMENT.md`, because on 26 September both are needed in one hand |

`reports/results.csv`, 1537 rows, moved to `runs/constrained/results.csv`: it is a data artefact
and not a table a reader reads. Briefs to `testing/briefs/`, six files. Superseded reports and
scratch to `testing/scratch/`, 31 files.

**Link check: 31 references checked, all resolve.** 16 stale paths were rewritten, mostly
references to files that are now appendices.

#### 2.6 The render entry point

`scripts/render_demo.sh` is the one entry point, calling `pipeline.constrained.rc8_demo`.

`rc8_demo` now **calls** `rc9_contrast.main()` rather than duplicating its code, so the secondary
clip cannot change. `rc9_contrast` becomes a library to `rc8_demo` in the same way `rc5_renders`
and `rb7_demo` already are. That is why it is not deleted. A failure in the contrast clip is
logged and does not fail the primary set.

`stage6_demo` retired: it renders the live unbounded mode, which finds 4 of 120 passes. That is
a different subject, not an older version, so it was retired and not deleted.

Eleven finished batch chains moved to `testing/scratch/scripts/`. `scripts/` now holds
`track.py`, `render_demo.sh` and `heartbeat.sh`.

#### 2.7 Root

`.DS_Store` files removed, and see failure 1 above for what that cost. `.gitignore` extended.

`configs/`, `tools/` and `splits/` all stay: each is referenced by shipping code, `configs/gate.yaml`
points at `splits/dev.txt`, and the `v2_*` manifests in `splits/` are the nine cross-day pairings
every tracking number rests on.

**Not in the plan, done anyway:** `splits/loso_tracking_Azrah.*` and `splits/loso_tracking_Zaid.*`
moved to `testing/scratch/splits_retired/`. Those are split manifests that enumerate the two
retired participants' recordings, under a filename carrying their code names, outside `runs/`.
Nothing reads them. A manifest that lists a retired participant's files is an instruction to read
data that is never to be read.

`README.md` and `STATE.md` rewritten: the cleaned layout, how to replay, how to render, where
every frozen artefact lives, and the headline of each branch with its caveats. The README's
achievement section previously led with the self-segmenting cross-day numbers; it now leads with
the boundaries-given result and states the self-segmenting cross-day figure as the honest negative
it is.

#### Sizes

| | before | after |
|---|---|---|
| repository total | 28 G | **24 G** |
| `.git` | 4.9 G | **498 M** |
| `data/` | 16 G | 12 G |
| `testing/` | 372 M | 4.3 G |
| `reports/` | 1.4 M | 248 K |

Nothing was deleted to achieve this except two `.DS_Store` files, three pid files and the
orphaned git blobs from the rewound commit. The 4 G that left `data/` is in `testing/from_data/`,
on disk, untouched. The real reduction is the 4.4 G reclaimed from `.git`.

#### Phases 3 to 6, appended 2026-09-18

**5.1 passed.** The pre-fix re-render from the cleaned tree is metric-identical to the pre-cleanup
set: same line decision on all 120 passes, same per-pass median error to three decimals, same
summary of 96 of 120 at 80.0 percent. That is the acceptance test for this whole cleanup.

**5.4.** The superseded renders were deleted only after the new set existed and 5.1 had passed,
which is the order the brief sets. 12 of the 13 videos differ from the pre-cleanup set, which is
the render change; the metrics behind them are identical, which is the point.

**A third failure, recorded with the other two.** The reports consolidation silently degraded
twenty report-consistency tests to SKIPS, because the documents they check had moved. A skip is
worse than a failure here: the guarantee stops being enforced and nothing announces it. A redirect
map in `tests/test_report_consistency.py` brought thirteen straight back, and the remaining seven
returned when `reports/SUMMARY.txt` was written at phase 6.3. The suite is now 476 passed, 8
skipped, which is the same skip count as before the cleanup began.

**A compliance defect the consolidation introduced and the cleanup then caught.** Folding the
recording timeline and one stage finding into the tracking report carried twenty participant code
names into a report body, against the standing rule. They were replaced with P1 to P6 using the
mapping already in `pipeline/identify/common.py`. Every report, README and STATE now carries zero
code names. Filenames under `runs/` are unchanged, which the rule permits, and
`runs/constrained/demo/ACCEPTANCE.md` is where the two meet.

**Final state.** 476 passed, 8 skipped, 0 failed. Rescore rc=0, every headline rebuilt from
artefacts alone. Free-movement recordings never read, over 18 recordings. Retired participants
never read. Four of four frozen artefacts byte-identical. New freeze at
`runs/TRACKING_FROZEN_2026-09-18b.json`; no earlier freeze overwritten. The identification branch
was not touched.

---

## CLEANUP_BRIEF_2026-09-23.md

**Source:** `reports/CLEANUP_BRIEF_2026-09-23.md`, 2026-09-23. **SHA-256:** `9ed0d9e1fb28ad2e65a42e616cb88040b45d19b517600eb0fd7b059fc281306c`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** Its paths describe the repository before 2026-09-24; runs, reports and part of pipeline have since moved into attempts/ folders.

### Repository map and cleanup brief, 2026-09-23

Snapshot taken 2026-09-23 23:22 to 23:34 SAST (clock read). Every size, count and process below was
measured then, from the files and not from other documents. **Re-measure before acting**: this repo
changes under batches.

---

#### 0. For the session doing the cleanup: read this first

- **Your job:** make this repository small and current without breaking the system that DC2 (the
  second data collection, 26 and 27 September 2026) runs on. The thesis is due 26 October 2026.
- **This file is the authority for the cleanup.** Section 5 lists rules found in this repo's
  documents that are STALE. The operator asked for them to be overridden. Confirm the checklist in
  section 9 with the operator once, then work to it.
- **Do not** follow the "on every wake, read QUEUE.md first and start the next PENDING item" rule
  (section 5, R2). Do not start any measurement, arm, render or training. Do not write
  pre-registrations, freezes or addenda for housekeeping.
- **Never edit, move, rename or reformat a file pinned by a freeze** (section 4.1). Their SHA-256
  hashes are checked by `tests/test_model_freeze.py` and by the DC2 identification scorers, which
  refuse to run on a mismatch. Whitespace counts.
- **Order matters.** Section 6 is the order. Step 0 (fix `.gitignore`, commit everything, tag)
  comes before deleting anything that is tracked or that the system uses, because most of the live
  DC2 code has never been committed. The only deletions inside step 0 are untracked, disposable
  trees, removed first so the snapshot commit does not carry them.

---

#### 1. Snapshot

| | |
|---|---|
| Repository on disk | **93 GB** (`du -sh .`), up from 87 GB at 16:56 the same day |
| Disk | 460 GiB, 386 used, **49 GiB free (89 percent)** |
| Branch | `fh-live-2026-09-19`, last commit `707d2b0` on **2026-09-21 11:08** |
| Uncommitted | **590 paths** in `git status` (17 modified and 97 untracked Python modules among them) |
| Remote | `origin` = `https://github.com/UzayrB/csi-thesis.git`, only `origin/main`, last pushed **2026-09-09** |
| Tracking batch | 23g **closed 20:50**, "THE MODEL IS FROZEN FOR DC2" (freeze 23h, `reports/MODEL_FREEZE_DC2.md`). Instruction 8 done 22:48. Only open item: live rig run, BLOCKED (no receivers attached) |
| Gait ID batches | ID, IDMAX and IDGP all closed (`CHECKIN_LOG_ID.md`: "BATCH END 11:05"; `CLOSING_IDMAX_2026-09-23.md`; `CLOSING_IDGP_2026-09-23.md`). **No identification process running** |
| Processes still running | `watchdog_render.sh` PID **45061** (parent 1, since 2026-09-20), which keeps alive `heartbeat_render.sh` PID **20248** and `caffeinate -dimsu` PID **80143**. All three serve a render batch that ended days ago |
| Last recorded suite | 1254 passed at 20:50 (batch 23g report). Not re-run for this brief |

##### Where the 93 GB is

| path | size | nature |
|---|---|---|
| `runs/` | 71 GB | about 66 GB of it is derived caches that can be rebuilt in minutes |
| `data/` | 12 GB | raw captures 2.6, derived 8.5, retired participants' raw captures 0.9 |
| `.git/` | 5.6 GB | 5.1 GB is two window folders committed by mistake on 2026-09-18 |
| `testing/` | 4.3 GB | pre-pivot history; 3.9 GB is a gitignored derived cache |
| `pipeline/` `reports/` `tests/` and the rest | about 20 MB | code and documents |

**Rebuild costs, measured in batch 23c** (`reports/BATCH_2026-09-23c_REPORT.md`): cutting windows,
29.7 s per recording and 8.5 min for all 18; a 0.5 s feature cache, 10 s and 826 MB per recording;
re-inferring six heads, 19 min; training one 1 s head seed, 51 min. The DC2 stand-in rerun takes
5.5 min (freeze 23h).

---

#### 2. Five risks bigger than the size. Handle these first

1. **The frozen DC2 system is mostly not in git.** Freeze 23h pins 61 files (38 code, 18 models,
   4 documents, plus the freeze JSON itself). **36 have never been committed and 15 have uncommitted
   edits; only 10 are committed unchanged.** Untracked files include `dc2_run.py`,
   `dc2_pipeline.py`, `lattice.py`, `nodes.py`, `veto.py`, `fusion.py`, `switching.py`,
   `realtime/tracker_live.py`, `realtime/rig_run.py`, all 18 model files and the freeze JSON. If
   the laptop fails, the DC2 model is gone.
2. **No off-machine copy since 2026-09-09.** `main` is 525 commits ahead of `origin/main`, and
   every commit since 09-21 exists only as working-tree changes.
3. **It cannot be pushed as things stand.** Git history holds 25 blobs over GitHub's 100 MB
   per-file limit, all under `runs/constrained/windows_w1/` and `windows_w05/` (commit `cb521e0`,
   2026-09-18, carried by 4 branches). Without those, the largest blob is 20.7 MB.
4. **55.6 GB of untracked files are not gitignored** (5617 files; 96 of them over 50 MB, 52.5 GB).
   A single `git add -A` commits them. This has already happened twice: `testing/from_data` on
   2026-09-18 (see `CLEANUP_LOG_2026-09-18.md`, failure 2) and the window folders in `cb521e0`.
5. **Stale life support.** The three processes above keep the Mac awake and append a false
   "RUNNING since 94h" line to `reports/CHECKIN_LOG.md` every 15 minutes.

---

#### 3. What the system is, in one paragraph

One ESP32 transmitter and three receivers capture Wi-Fi CSI at 150 Hz in a 5 by 5 m room. A person
walks one of twelve taped lines. Each 2 s window per receiver goes through a per-link CNN with a
25-cell region head and a position head. A pool of five heads (one 0.5 s g25 head, three 1 s g25
seeds, one 1 s g100 region head) feeds a hidden Markov decoder with twelve path chains and a null
state. The shipped mode is **semi-bounded** (told when a walk starts): headline **62.50 percent
pre-registered, 73.33 post-amendment** (freeze 23h). The demonstration is six videos in
`runs/constrained/demo/`, drawn 2.0 s behind real time under `reports/RENDER_RULES.md`. Since
batch 23d the shipped system runs on **the ONE lattice** (press-aligned 0.5 s windows), defined in
`pipeline/constrained/lattice.py` (`SHIPPED = "pressalign"`). The older "grid" lattice is reachable
only with `TDR_LATTICE=grid`, for reproducing pre-23d figures. Person identification is a separate
branch in `pipeline/identify/`, with its own DC2 scorers.

---

#### 4. Directory map, with a verdict for every part

Verdicts: **KEEP**. **DELETE** (T1: now; untracked disposable trees in step 0.4, everything else
after the step-0 commit). **HISTORY** (T2: git rewrite). **AFTER DC2** (T3: once the Room B
analysis and DC2 identification scoring are done). **OPERATOR** (needs the operator's decision).

##### 4.1 Pinned by a freeze: never edit, move or rename (95 paths)

Collected from every `path: sha256` pair in `runs/TRACKING_FROZEN_2026-09-23h.json`, its
`_ADDENDUM`, and `runs/IDENTIFICATION_FROZEN_2026-09-23{b,b_ADDENDUM,c,e,f}.json`.

- **Tracking (freeze 23h, `DC2_MODEL_FREEZE`):** 34 files in `pipeline/constrained/` (`lattice`,
  `dc2_run`, `dc2_pipeline`, `nodes`, `veto`, `fusion`, `switching`, `night_arms`, `night_common`,
  `g3_final`, `g2_multihead`, `artefacts`, `recordings`, `common`, `decoder`, `decoder2`,
  `emissions`, `features`, `nets`, `n2_arms`, `q4_arms`, `r1_oldcensus`, `u1_adapt`, `u2_useit`,
  `t1_region`, `render_display`, `s2_display`, `s2a_dispend`, `f3_render`, `sb2_structural`,
  `y4_pressalign`, `fh_common`, `_guard`), plus `pipeline/splits/windows.py`,
  `pipeline/realtime/{engine,tracker_live,rig_run}.py`, `scripts/live_rig_run.sh`.
  **18 models:** `runs/artefacts_s0.5_pressalign_roomA3/models/*` (6) and
  `runs/artefacts_s1.0_roomA3_{g100,s0,s1,s2}/models/*` (12).
  **Documents:** `reports/PREREG_DC2_crossroom_2026-09-22.md` (changes only through an addendum
  JSON), `reports/RENDER_RULES.md`, `reports/DC2_FIELD_CHECKLIST.md`, `reports/MODEL_FREEZE_DC2.md`.
  **Videos:** the six `runs/constrained/demo/*.mp4` (by basename, `videos_sha256`).
- **Identification (ID freezes):** `pipeline/identify/{capture_idpath, id19_bank, id19_featbank,
  id25_learned, id26b_cnn_diag, id28_dc2_score, id29_dc2_score, idgp_bank, idgp_cadence,
  idgp_checkin, idgp_checks, idgp_cnn, idgp_contract, idgp_dc2_score, idgp_eval, idgp_signal,
  idmax_eval, idmax_features, rehearsal_check}.py`;
  `tests/{test_id28_dc2_score, test_id29_dc2_score, test_idgp_contract, test_idgp_dc2_score}.py`;
  `reports/{CAPTURE_INTERFACE_NOTES.md, DC2_ID_FIELD_CARD.md, DC2_ID_PROTOCOL_2026-09-23b.md,
  DC2_ID_PROTOCOL_2026-09-23c.md, DC2_ID_PROTOCOL_2026-09-23d.md, DC2_ID_REHEARSAL.md,
  FINDINGS_stageid19.txt}`; `runs/IDENTIFICATION_FROZEN_2026-09-23{b,b_ADDENDUM,c,e}.json`.
  The ID DC2 scorers also check the hashes of `reports/PREREG_ID_DC2_2026-09-23.md` and its
  addenda B and C: **treat every `reports/PREREG_ID_*` file as pinned**.

To regenerate this list before acting, walk those JSON files for keys under `reports/`, `runs/`,
`pipeline/`, `scripts/`, `tests/` whose value is a 64-hex string.

##### 4.2 `runs/` (71 GB, 92 entries)

**The big trees. This is where the space is.**

| path | GB | what it is | who reads it | verdict |
|---|---|---|---|---|
| `runs/artefacts_s0.5_pressalign_shared/` | 12.66 | Feature and RSSI cache for the **shipped** lattice, 18 Room A recordings | symlinked as `features`/`rssi_full` by `artefacts_s0.5_pressalign_{half,fh1s,g1s1,g1s2,g100,dispend}` and by the frozen `artefacts_s0.5_pressalign_roomA3` | **AFTER DC2**. Rebuild about 3 min |
| `runs/artefacts_s0.5_retrain_shared/` | 12.64 | Cache for batch 23c item 5, a base retrain whose heads came out bit-identical; nothing shipped | only the finished `artefacts_s0.5_retrain_s{0,1,2}` | **DELETE (T1)** with those three trees. Result kept in `runs/constrained/fh/y5_heads/` |
| `runs/artefacts/` | 6.78 | The original 1 s tree: `features/` 6.3 (1 s stride, stride-blind filenames), `posteriors/` 0.38, `models/` 0.08 (the 1 s heads' frozen weights), `MANIFEST.md` | `features/`: nothing on the shipped lattice, and no symlink points into `runs/artefacts/` (checked) | **DELETE `features/` only (T1).** A byte-identical copy (sha256, 18 of 18, batch 23c) is in `artefacts_s1.0_retrain_shared`. Keep models, posteriors, `rssi_full`, `gate_energy`, `MANIFEST.md` |
| `runs/artefacts_s1.0_retrain_shared/` | 6.34 | The 1 s feature cache rebuilt in 23c, identical to the one above | symlinked by the frozen `artefacts_s1.0_roomA3_{s0,s1,s2,g100}` and by `artefacts_s1.0_retrain_s{0,1,2}` | **AFTER DC2** |
| `runs/constrained/windows_s0.5_pressalign/` | 6.34 | **The ONE lattice's** Room A windows | `lattice.py`, `dc2_run`, `d5_train_room_a`, tests | **AFTER DC2**. Rebuild 8.5 min |
| `runs/constrained/windows_half/` | 6.34 | The retired grid lattice's 0.5 s windows, used only for `TDR_LATTICE=grid` reproduction | tests check the path **string** only; `y4_pressalign`'s guard is a path-prefix check and its snapshot walks a missing folder as empty (both verified) | **DELETE (T1).** Rebuild: `python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_half --stride 0.5` |
| `runs/constrained/dc2_room_B_standin_s0.5_pressalign/` | 5.61 | DC2 dry run: a Room A session dressed as Room B (view, cut, features, posteriors) | the result is in `runs/constrained/fh/dc2_pipeline_standin/results.json` and `reports/DC2_REPORT_room_B_STANDIN.md`; freeze 23h cites the JSON, not this folder | **DELETE (T1).** Rerun 5.5 min. Its `art_shared/` holds symlinks into the shipped cache: delete the whole folder, see hazard H1 |
| `runs/constrained/dc2_room_B_standin_decoys_s0.5_pressalign/` | 5.57 | The same dry run with decoy receivers (written 17:30) | `reports/DC2_REPORT_room_B_STANDIN_DECOYS.md` | **DELETE (T1)** |
| `runs/constrained/windows_w1/` | 3.19 | Window-probe arm: 1 s windows at a 0.5 s stride. **Committed to git** | finished stages only (`c2_window1s`, `wp2_window1s`, `u3_trackeradapt`); the DC2 checklist says **never** cut Room B into it | **DELETE (T1)** and **HISTORY (T2)** |
| `runs/constrained/windows_w05/` | 1.61 | Window-probe arm, 0.5 s windows; did not ship. **Committed to git** | finished stages only | **DELETE (T1)** and **HISTORY (T2)** |
| `runs/identify/` | 2.00 | `idmax/features` 1.2, `idmax/bank` 0.8 (per-pass banks written by `id19_bank`), small stage folders | DC2 identification scoring builds or reads banks | **AFTER DC2** |

**Small trees (1.5 GB together).**

| path | verdict |
|---|---|
| `runs/artefacts_s0.5_pressalign_{half,fh1s,g1s1,g1s2,g100,dispend}` | KEEP. Shipped lattice posteriors and models |
| `runs/artefacts_s0.5_pressalign_roomA3`, `runs/artefacts_s1.0_roomA3_{s0,s1,s2,g100}` | KEEP, pinned. The 18 DC2 models |
| `runs/artefacts_{half,fh1s,g1s1,g1s2,g1g100s0,dispend}` | KEEP. Grid lattice trees named by `lattice.py`; tracked in git; small |
| `runs/artefacts_s0.5_retrain_s{0,1,2}`, `runs/artefacts_s1.0_retrain_s{0,1,2}` | DELETE (T1). Batch 23c retrain outputs, bit-identical to the shipped heads |
| `runs/artefacts_ends`, `runs/artefacts_w1`, `runs/artefacts_w05` | DELETE (T1) after a grep: finished end-windows and window-probe arms, tracked in git |
| `runs/cleanup/` | DELETE (T1): the 2026-09-18 cleanup's hash lists |

**`runs/constrained/` small entries.**

| path | verdict |
|---|---|
| `fh/` (30 MB, one `results.json` per stage) | KEEP. Freeze 23h's `results_files` live here |
| `demo/` (13 MB: six videos, `ACCEPTANCE.md`) | KEEP, pinned. Never re-render into it |
| `demo_archive/` (63 MB, untracked, earlier renders) | DELETE (T1) |
| `logs/` (1.3 MB) | DELETE (T1) once life support is stopped |
| about 75 stage result folders (`rb*`, `rc*`, `rd*`, `re*`, `sb*`, `stage*`, `wp*`, `night`, `ends` and so on, under 20 MB total, 09-16 to 09-19) | **KEEP.** No space to gain, and product modules load several of them by name (`ends`, `night`, `rb2_decoder`, `rb3_display`, `rb10_bounded_demo`) |
| `RENDER_FIX_GO`, `heartbeat.log`, `results.csv` | DELETE (T1): markers and logs |

**Freeze and pre-registration JSONs in `runs/` (59 files, 1.3 MB).** KEEP all. Live:
`TRACKING_FROZEN_2026-09-23h(+_ADDENDUM)`, `IDENTIFICATION_FROZEN_2026-09-23{b,b_ADDENDUM,c,e,f}`,
`SUPERSESSION_tracking_open_2026-09-22`. Older ones are cited by live documents (18s, 18z, 20a,
22c, 22d, 23e and two PREREGISTRATION files). Clutter only, not space.

##### 4.3 `data/` (12 GB)

| path | GB | what it is | verdict |
|---|---|---|---|
| `data/room_A/` | 2.6 | **Raw captures**: sessions 01 to 03, 72 `.bin` plus 48 `.json`, and timestamped baseline folders. Irreplaceable | **KEEP, never touch** |
| `data/windows/` | 3.2 | 1 s-stride windows (09-10 to 09-13). The training input for the 1 s heads, including the four frozen DC2 1 s trees (`d5_train_room_a`), and `recordings.py`'s default `WINDOWS_ROOT` | **KEEP** |
| `data/features/` | 2.3 | Old caches: `band_30_nonotch`, `band_60_notch`, `band_60_nonotch`, `band_72_notch` (09-10 to 09-12 band experiments), `tracking` (09-15) | **OPERATOR, recommend DELETE.** Only reader: `pipeline/identify/id11_audit.py`, a closed stage listing directories. `recordings.py` says in its docstring that it does not read it |
| `data/retired/azrah_zaid/derived/` | 3.0 | Regenerable caches for the two retired participants. Their own README: "kept only so that a restore returns the tree to exactly its previous state" | **OPERATOR, recommend DELETE** |
| `data/retired/azrah_zaid/captures/` | 0.9 | Raw captures of Azrah and Zaid. Retired on 09-14 for method (their sessions 01 and 02 were recorded the same morning), not over consent | **OPERATOR**: keep, or move off the laptop. Never delete without the operator |

##### 4.4 `testing/` (4.3 GB, 3836 tracked files)

Everything the project did before it committed to constrained tracking on 16 September, plus the
2026-09-18 cleanup's retired modules. `from_data/` 3.9 GB (gitignored derived `.npz`/`.npy` from
09-12 to 09-14, nothing references it), `runs/` 362 MB, `demo_retired/` 16 MB, `reports/` 7.9 MB,
`pipeline/` 1.6 MB, `pipeline_retired/`, `scratch/`, `figs_retired/`, `failed_models/`, `briefs/`,
`tests/`, `scripts/`, `retired_tests_2026-09-20/`, and two empty folders.

**Verdict: DELETE all of `testing/` (T1)** after the step-0 commit and tag; git history keeps
every tracked file. Six tests mention `testing/` and must be fixed in the same step:
`test_stride_isolation_rb2d.py` (delete it: it tests a retired module), `test_identification_clean.py`,
`test_conditioning.py`, `test_render_rules.py`, `test_stride_isolation.py`,
`test_track_entrypoint.py`. Several of these only assert that `testing/` is *not* imported, which
stays true once it is gone.

##### 4.5 `pipeline/` (250 modules)

Classified by a static import walk (AST imports plus `pipeline.x.y` strings in code and shell) from
the frozen files and the live entry points (`scripts/track.py`, `scripts/render_demo.sh`,
`rescore`, `d4_headline`, `d6_lock_commit`, `dc2_scorerlock`, `e2_switch`).

| package | modules | verdict |
|---|---|---|
| `pipeline/io/` | 10 | **KEEP all.** Capture and ground truth; DC2 capture uses `capture_logger`, `identify_board`, `ground_truth` (Makefile, checklist). The brief keeps it untouched |
| `pipeline/realtime/` | 5 | KEEP. Three are pinned |
| `pipeline/clean/`, `branches/`, `models/`, `splits/` | 2, 2, 4, 4 | KEEP. Small; `splits/windows.py` is pinned |
| `pipeline/constrained/` | 162 | see below |
| `pipeline/identify/` | 60 | see below |

**`pipeline/constrained/`: 66 live, 7 guard dependencies, 5 optional, 84 finished.**

- **KEEP: the frozen DC2 system and everything it imports (66):** `__init__ _guard artefacts bout
  common d4_headline d6_lock_commit dataset dc2_pipeline dc2_run dc2_scorerlock decoder decoder2
  e1_switch e2_switch emissions f1_arms f3_render features fh_common fh_ensprep fusion g2_multihead
  g3_final grid lattice live2 metrics n2_arms nets night_arms night_common nodes p1_runup paths
  q1_diag q3_startclf q4_arms r1_oldcensus rb10_bounded_demo rb3_display rb7_demo rc1_diagnostics
  rc4_calibration rc5_renders rc8_demo rc9_contrast re4_semibounded rebuild_common recordings
  render_display rescore s2_display s2a_dispend sb2_structural stage1_pace stage4_unified
  stage5_live switching t0_oracle t1_region t2_embed u1_adapt u2_useit veto y4_pressalign`.
  Many of these look like finished stages but are libraries now: `q4_arms` has 38 importers,
  `r1_oldcensus` 46, `night_arms` 52, `g3_final` 51, `rebuild_common` 128.
- **KEEP: needed by guard tests (7):** `lock_horizon t6_lockdiag t7_lockarms t9_lengthnorm
  y2a_causal` (`test_lock_is_causal`), `z3a_linkprod z3b_g100native` (`test_fusion`; product
  fusion is DC2 exploratory arm B).
- **KEEP until DC2:** `d5_train_room_a` (it trained the 18 frozen models) and `t8_calib` (freeze
  23h's DC2 calibration block says DC2 must "re-run the verification against it").
- **OPTIONAL, test-only (5):** `rb1_truth` (`test_bounded_demo`), `rb8_verify` and `rb9_report`
  (`test_report_consistency`), `rb2b_stride` and `rb2d_retrain` (`test_stride_isolation_rb2d`).
  Recommend deleting them together with those tests.
- **DELETE (T1), finished stages nothing imports (82):** `a3_lock b1_motion c1_causal c2_window1s
  d1_reeval d3_combo d3_eval f0_repairs f2_verdict f4_verify g1_ablation g1_ensprep_multi
  g2_scorerlock g5_freeze g6_timeline n0_setup n1_diag n3_combos n4_calib n5_verdict n6_freeze
  night_eta night_summary p2_prepress p3_direction q2_extras r1_reference r2_softentry r3_lagsweep
  r3_prior r4_start r5_lock r5_timeline r6_latency rd1_stall rd2_pin rd3_verify rd4_halfstride
  re1_endlabels re2_retrain re3_bounded re5_ship re6_heads re7_finalise s0_verify s1_confirm
  s2b_decision_causality sb0_train_half sb1_decompose sb1b_d1_speed sb2g_gate sb3_exitsweep
  sb3v_verdict sb4_stride sb4c_stridedecision sb4o_override sb5_live sb6_freeze t3_ship t4_finetune
  t5_shipc u3_trackeradapt u4_mechanism v1_afwd w1_dotphase wp0_feasibility wp1_gate wp2_window1s
  wp3_window05s wp4_verdict wp_arm wp_window_common x1_edgedisp x2_edgepool x3_edgeeval y1_diag
  y1b_locksrc y2_dial y3_switch y4b_lockstep1 y5_heads z3_eval`. Their results stay in
  `runs/constrained/fh/` and the reports; the code stays in git history
  (`git checkout pre-cleanup -- <path>`).

**`pipeline/identify/`: 31 keep, 29 finished.**

- **KEEP (31):** the DC2 identification chain `__init__ capture_idpath common conditioning features
  id14_crossday id15_corridor id15_factor_map id19_bank id19_featbank id25_learned id28_dc2_score
  id29_dc2_score id3_embeddings id_heads idgp_cadence idgp_cnn idgp_contract idgp_dc2_score
  idgp_eval idgp_signal idmax_common idmax_eval idmax_features raw_access rehearsal_check
  yield_governor`, plus four pinned but outside that chain: `id26b_cnn_diag idgp_bank idgp_checkin
  idgp_checks`.
- **DELETE (T1) (29):** `audit_results figures gait_features id10_voting id11_audit
  id12_conditioning id13_representations id16_daybias id17_learned id18_report id19_audit
  id1_foundations id20_controls id21_baselines id22_sweep id23_path id24_voting id26_final
  id27_report id2_ladder id4_verification id5_report id6_extras id7_livepipeline id8_perline
  id8a_lines id9_threshold idgp_report idmax_checkin`. Tests to adjust with them:
  `test_gait_features.py` (`gait_features`) and `test_conditioning.py` (`id12_conditioning`).
  Check `test_identification_clean.py` and `test_idmax_guards.py` too.

##### 4.6 `tests/` (60 files)

- **KEEP, guards** (HANDOFF §7, the freeze, the render contract): `test_model_freeze`
  `test_render_rules` `test_cross_pairing_key` `test_pass_pairing_key` `test_dc2_ingest_guard`
  `test_lock_is_causal` `test_lock_phase` `test_one_lattice` `test_display_is_causal`
  `test_prepress_is_causal` `test_rssi_refuses_missing` `test_fusion` `test_switching`
  `test_fourth_receiver` `test_rig_run` `test_realtime` `test_entrypoint_guard_form`
  `test_stride_isolation` `test_no_pacer` `test_drawn_path_is_decoded` `test_red_dot_is_drawn`
  `test_reported_config_is_applied` `test_no_shadowed_stage_loads` `test_asserted_not_measured`
  `test_freeze_quotes_the_current_figure` `test_track_entrypoint`.
- **KEEP, capture and core:** `test_anchors test_parse test_ground_truth test_clean test_windows
  test_gate test_models test_synthetic_shapes test_shutdown _shutdown_driver test_rt_calibration
  test_inspect_capture test_channel_filter test_gain_lock test_demo_exclusion
  test_constrained_decoder test_decoder2 test_metrics`.
- **KEEP until DC2 identification is scored:** `test_id28_dc2_score test_id29_dc2_score
  test_idgp_dc2_score test_idgp_contract` (all four pinned), `test_identification_clean
  test_id_heads test_idmax_guards`. `test_idmax_guards` was failing at 13:52 (a DEMO path in
  `runs/identify/idmax/READS.log`); the batch 23c report records it as belonging to the ID session.
- **STALE:** `test_stride_isolation_rb2d` (tests a retired module and imports `testing/`): DELETE.
  `test_report_consistency`: **13 of the 15 documents it checks no longer exist**, so most of it
  skips silently; delete the dead cases (or the file) and keep the cases whose targets exist.
  `test_bounded_demo`: keep only if `rb1_truth` stays.

##### 4.7 `scripts/`, `tools/`, `configs/`, `splits/`

- **`scripts/` (35 files). KEEP 3:** `render_demo.sh` (the render entry point), `live_rig_run.sh`
  (pinned), `track.py` (tested by `test_track_entrypoint`). **DELETE 32:** `chain_*.sh` (5),
  `heartbeat*.sh` (6), `watchdog*.sh` (6), `run_*.sh` (10, including `run_identify_batch.sh`),
  `ends_summary.sh`, `write_fh_summary.sh`, `write_night_summary.sh`, `idmax_chain.sh`,
  `idmax_featbank.sh`. Stop the running ones first (step 0.1).
- **`tools/` (16). KEEP:** `__init__.py`, `calibrate_gate.py` (imported by the pinned
  `realtime/rig_run.py` and by `realtime/replay.py`), and optionally `make_layout_image.py` and
  `make_paths_image.py` (they regenerate `Layout.png` and `Paths.png`, which `pipeline/io/ground_truth.py`
  opens). **DELETE the other 12** (pre-pivot analysis tools from 09-08 to 09-12).
- **`configs/` (3) and `splits/` (49 small files):** KEEP.

##### 4.8 `reports/` (248 files; the 2026-09-18 cleanup left 13)

- **KEEP, referenced by a live freeze, a DC2 document, live code or a test (55):**
  `BATCH_2026-09-23c_REPORT` `BATCH_2026-09-23g_REPORT` `BRIEF_render_and_prepress_2026-09-22`
  `CAPTURE_INTERFACE_NOTES` `CHECKIN_LOG_IDMAX` `CLEANUP_PLAN_2026-09-18` `CLOSING_IDMAX_2026-09-23`
  `CORRECTION_causal_lock_2026-09-23` `CORRECTION_drawn_lock_2026-09-23` `DC2_FIELD_CHECKLIST`
  `DC2_ID_FIELD_CARD` `DC2_ID_PROTOCOL_2026-09-23b/c/d` `DC2_ID_REHEARSAL` `DC2_PROTOCOL_2026-09-18`
  `DC2_REPORT_room_B` `DECISIONS_ID_2026-09-23` `ETA.txt` `FIGURES` `FINDINGS_stageid19.txt`
  `FINDING_linkfusion_2026-09-23` `FINDING_lock_phase_2026-09-23` `FINDING_pooled_vs_edge_2026-09-22`
  `FINDING_two_locks_2026-09-23` `FIX_one_lattice_2026-09-23` `GEOMETRY_AUDIT_2026-09-20`
  `HANDOFF_2026-09-21` `HANDOFF_2026-09-22` `HEADLINES.txt` `INVESTIGATION_switching_2026-09-23f`
  `ITEM3_REPORT_2026-09-23` `MODEL_FREEZE_DC2` `PREREG_DC2_crossroom_2026-09-22`
  `PREREG_ID_2026-09-23` `PREREG_ID_DC2_2026-09-23(+_ADDENDUM_B, _C)` `PREREG_dotphase_2026-09-22`
  `PREREG_lengthnorm_2026-09-22` `PREREG_prepress_region_2026-09-21` `PREREG_prepress_v2_2026-09-22`
  `PREREG_pressalign_2026-09-23` `PREREG_scorerlock_2026-09-23` `PREREG_switching_arms_2026-09-23f`
  `PREREG_switching_display_2026-09-23e` `QUEUE_IDGP` `QUEUE_IDMAX` `REEVAL_f_amended_2026-09-23`
  `RENDER_RULES` `ROOM_TRANSFER_AUDIT_2026-09-22` `SCORERLOCK_AND_ABLATION_2026-09-23`
  `SEMIBOUNDED_STATE` `SUMMARY.txt` `TRACKING_2026-09-18`. (`ETA.txt` and `CLEANUP_PLAN` are only
  written or mentioned by code; deleting them is harmless if the operator prefers.)
- **KEEP, thesis record (nothing references them; the operator may prune):**
  `IDENTIFICATION_2026-09-18` `ID_QUOTABLE_2026-09-23` (the ID figures the thesis may quote)
  `ACCURACY_STATE_2026-09-22` `HANDOVER_ID_2026-09-23` `CLOSING_ID_2026-09-23`
  `CLOSING_IDGP_2026-09-23` `BATCH_2026-09-23_REPORT` `BATCH_2026-09-23d/e/f_REPORT`
  `PREPRESS_REGION_REPORT_2026-09-21` `RUNUP_FINDINGS_2026-09-20` `ITEMS_ABC_REPORT_2026-09-22`
  `PART1_REPORT_2026-09-22` `PART2_REPORT_2026-09-22` `PARTS_1_TO_3_REPORT_2026-09-20`
  `RENDER_DOTPHASE_2026-09-22` `DC2_REPORT_room_B_STANDIN(_DECOYS)`, every remaining `PREREG_*.md`,
  and the folders `fig/` (holds `architecture.png`, named in `TRACKING_FROZEN_2026-09-17`),
  `figures/`, `figures_idmax/`.
- **DELETE (T1), about 158 files:**
  - 119 `FINDINGS_stage*.txt` (every one except `FINDINGS_stageid19.txt`, which is pinned);
  - markers: `BATCH_STARTED_{FH,NIGHT,SB,WP}.txt` `FH_COMPLETE` `NIGHT_COMPLETE`
    `WINDOW_PROBE_COMPLETE` `PHASE.txt`;
  - pid files: `heartbeat.pid` `heartbeat_render.pid` `watchdog.pid` `watchdog_render.pid`;
  - logs: `status.txt` (714 KB) `WATCHDOG.log` `CHECKIN.md` `CHECKIN_LOG.md` `CHECKIN_LOG_ID.md`
    `CHECKIN_LOG_IDGP.md`;
  - closed queues: `QUEUE.md` `QUEUE_ID.md`;
  - superseded briefs, handoffs and summaries: `BRIEF_fh_live_2026-09-19` `BRIEF_motion_and_lock_2026-09-20`
    `BRIEF_render_fix_2026-09-20` `BRIEF_semibounded_night_2026-09-19`
    `end_windows_semibounded_prompt_2026-09-18` `HANDOVER_2026-09-18c` **`HANDOFF_2026-09-23`**
    (see R4) `PLAN_render_fix_2026-09-20` `BRANCHES_2026-09-18` `CLEANUP_LOG_2026-09-18`
    `MODEL_IMPROVEMENTS_QUEUE` `SUMMARY_ENDS.txt` `SUMMARY_FH_LIVE.txt` `SUMMARY_NIGHT.txt`
    `SUMMARY_SEMIBOUNDED.txt` `SUMMARY_WINDOW.txt` `SUPERSEDED_id18_first_attempt_2026-09-23`
    `DC2_ID_PROTOCOL_2026-09-23.md` (v0) `DC2_SCORERLOCK_room_B_STANDIN.md` (empty).
- **REWRITE:** `reports/README.md` (dated 09-19, lists files that are gone).

##### 4.9 Top-level files and `.git`

| path | verdict |
|---|---|
| `README.md` | **REWRITE.** It quotes "Boundaries given, which is the headline ... 63.2 percent" and names `track.py --mode live-lag --lag 3` as "THE DEMONSTRATION". Current: semi-bounded 62.50 / 73.33, demo in `runs/constrained/demo/`. `test_track_entrypoint` reads the README's command and `test_report_consistency` checks the README against `stage5_live` results: update the tests together with it |
| `STATE.md` (56 KB, about 830 lines, titled "STATE, 2026-09-20", newest-first log of every batch) | **REWRITE** as a short current-state page; history lives in git and the reports |
| `Layout.png`, `Paths.png` | KEEP (opened by `pipeline/io/ground_truth.py`) |
| `Makefile`, `requirements.txt`, `configs/`, `.vscode/` | KEEP |
| `.gitignore` | **AMEND** (step 0.2) |
| `.DS_Store` (11 outside `data/`), `__pycache__` (17 MB), `.pytest_cache` | DELETE. Scope the command so it cannot enter `data/` (hazard H6) |
| `.git` (5.6 GB: 5.12 GiB loose, 484 MiB pack) | **HISTORY (T2)**: about 0.5 GB after the rewrite |
| 16 local branches (`checks-2026-09-14` to `window-probe-2026-09-18`, plus `main`) | OPTIONAL: turn the old ones into tags `archive/<name>` after the rewrite |

---

#### 5. Rules register: which of the repo's rules are stale

Only rules that bear on the cleanup, or that a new session would otherwise obey by mistake.

| # | rule, as written | where it lives, and what enforces it | status | what to do |
|---|---|---|---|---|
| R1 | "A second Claude session runs gait ID. Never touch `pipeline/identify/`, `runs/identify/`, `reports/*_ID*`, its tests or processes" | HANDOFF_2026-09-23 §1; QUEUE.md "COEXISTENCE"; QUEUE_ID.md "SEPARATION"; CLEANUP_PLAN_2026-09-18; Claude memory `handoff-entry-point`. Prose only | **STALE.** All three ID batches closed; no ID process runs | Override. ID files may be cleaned, **except** the ID-pinned paths and the DC2 identification chain (4.1, 4.5) |
| R2 | "On every wake read QUEUE.md FIRST, start the next PENDING item immediately, never end a turn while an item is PENDING" | QUEUE.md, QUEUE_ID.md, QUEUE_IDGP.md, QUEUE_IDMAX.md | **STALE.** Batch 23g all DONE at 20:50; ID queues closed; the live rig run is BLOCKED on hardware | Ignore it. Delete QUEUE.md and QUEUE_ID.md; the two referenced ID queues stay as inert records |
| R3 | "Read the BRIEF verbatim, not a memory of it; come back to it between items" | `BRIEF_render_and_prepress_2026-09-22.md` header; HANDOFF §0; memory `handoff-entry-point` | **STALE as an instruction.** All eight instructions are executed (batches 23a to 23h) | Keep the file as a record (freeze 23h cites it). It is not the authority for the cleanup |
| R4 | "BEFORE DC2: CUT ROOM B TWICE, at 0.5 s AND at 1.0 s, into `windows_w1` and `windows_half`" | HANDOFF_2026-09-23 §6, top item | **STALE AND DANGEROUS.** The pinned `DC2_FIELD_CHECKLIST.md` (lines 100 to 102) says Room B needs no second cut and **"NEVER cut Room B into windows_half or windows_w1"**; `dc2_pipeline` uses `windows_s1.0_dc2` | Delete HANDOFF_2026-09-23.md (nothing live references it), so nobody follows it at DC2 |
| R5 | "`data/` is read only; nothing under `data/` is ever deleted" (called "absolute") | BRIEF hard constraints; QUEUE standing rules; CLEANUP_LOG_2026-09-18; docstrings in `recordings.py` and `lattice.gt_path`. Prose; no code writes `data/` | **AMEND** | Keep it absolute for `data/room_A`, `data/retired/*/captures` and `data/windows`. Override for `data/features` (2.3 GB) and `data/retired/azrah_zaid/derived` (3.0 GB), if the operator agrees |
| R6 | "`testing/` is never imported"; `testing/README.md`: kept "because every number on record must stay reproducible" | BRIEF; QUEUE; `testing/README.md` | **CONTRADICTED.** Six tests reference `testing/` | Override: delete `testing/` (the tracked part stays in git history) and fix the six tests |
| R7 | "Freezes superseded, never overwritten" | BRIEF; QUEUE; every freeze's `supersedes` | **KEEP**, with a clarification | Never edit a freeze JSON. The rule does **not** require keeping every intermediate a superseded freeze once pointed at |
| R8 | "THE DC2 MODEL FREEZE: no model change until the Room B analysis"; "documents change only through a recorded addendum" | freeze 23h `DC2_MODEL_FREEZE`; `MODEL_FREEZE_DC2.md`; **enforced** by `tests/test_model_freeze.py` | **KEEP, binding** | The pinned files are never edited, moved or renamed, and everything they import must stay importable. `RENDER_RULES.md`, `DC2_FIELD_CHECKLIST.md`, `PREREG_DC2`, `MODEL_FREEZE_DC2` cannot be tidied |
| R9 | ID hash gates: the DC2 ID scorers refuse unless the 23c, 23e and 23f freezes and the ID pre-registration hashes match | `id28/id29/idgp_dc2_score.py`, **enforced in code** (`raise Refused`) | **KEEP** until DC2 identification is scored | Same consequence as R8 for the ID-pinned paths and every `PREREG_ID_*` |
| R10 | "TRACKING IS NEVER CLOSED" | `runs/SUPERSESSION_tracking_open_2026-09-22.json`; BRIEF; STATE; freezes | **KEEP** as the operator's scope decision | It is not a retention rule: finished arms' caches and code can go |
| R11 | "Pre-register before anything runs; a rule changed after seeing data is POST HOC and says so" | BRIEF; every PREREG | **KEEP for measurements** | Does not apply to housekeeping. No pre-registration for deletions |
| R12 | Ship rule (a) to (f), substitution, edge lines beside pooled figures, pairing key `session\|stem\|pass_id`, six participants, signal-only, fixed node geometry, never judge on `s0102_to_s03` | BRIEF; QUEUE; tests | **KEEP** (science) | Irrelevant to the cleanup; leave the tests that enforce them |
| R13 | "The guards that exist. Do not remove them; they have all caught something" | HANDOFF_2026-09-23 §7 | **KEEP**, except one stale sub-part | Keep the guard tests (4.6). `test_stride_isolation_rb2d` guards a retired module: delete |
| R14 | Stride isolation: "6.3 GB of shipped features would be overwritten" | `_guard.assert_isolated` (pinned), `y4_pressalign.SHIPPED_TREES_NEVER_WRITTEN` (pinned), `n2_arms`, `test_stride_isolation`, `test_entrypoint_guard_form` | **KEEP the code** (pinned) | The danger goes away once `runs/artefacts/features` is deleted. The guards compare paths only, so deleting those folders does not trip them (verified in code) |
| R15 | Life support: "Keeps caffeinate and the heartbeat alive"; "never kill, restart or touch" another run's processes | `scripts/watchdog_render.sh` and the other watchdogs; HANDOFF §1 | **STALE.** PID 45061 has run since 2026-09-20 for a finished batch | Kill 45061, then 20248 and 80143, by PID only (step 0.1). Never `pkill` |
| R16 | `.gitignore`: lists the grid-era trees one by one ("runs/artefacts/MANIFEST.md records every hash") | `.gitignore` | **AMEND** | The stride-keyed trees of 23c and 23d are not covered: 55.6 GB is exposed. Replace with directory patterns (step 0.2) |
| R17 | README: bounded mode "is the headline, 63.2 percent"; "`track.py --mode live-lag --lag 3` is THE DEMONSTRATION" | `README.md`; `test_track_entrypoint`, `test_report_consistency` | **STALE** | Rewrite it with the tests (4.9) |
| R18 | STATE.md as an append-only log titled "STATE, 2026-09-20" | `STATE.md` | **STALE form** | Replace with a short current-state page |
| R19 | Retire code into `testing/pipeline_retired/` instead of deleting it | CLEANUP_PLAN and CLEANUP_LOG 2026-09-18 | **SUPERSEDE** | After the step-0 commit and tag, git history is the archive; a retired-code folder is clutter, and tests imported it anyway |
| R20 | Canonical figures are "pinned by name" | CLEANUP_LOG 2.4 | **KEEP** | `Layout.png` and `Paths.png` (ground_truth) and `reports/fig/architecture.png` (freeze 17) keep their names |
| R21 | British spelling, no em dashes | QUEUE standing rules | **KEEP** | Applies to anything the cleanup writes |
| R22 | Claude memory, loaded automatically by every Claude session in this repo, including the cleanup session | `~/.claude/projects/-Users-uzayrballim-Desktop-UNI-2026-EEE4022S-Code/memory/` | `handoff-entry-point` is **STALE** (second session, read order). `bounded-demo-is-the-demo` and `tdr03-framing-within-day` already carry SUPERSEDED headers. The rest hold | Update `handoff-entry-point` to point at this brief and drop the second-session claim |

---

#### 6. Execution order, with the check after each step

Run from the repository root. Stop at any failed check.

##### Step 0. Make everything safe (no deletions)

```bash
# 0.1 Stop the stale life support. Look first, kill by PID only, the watchdog first so it cannot respawn the others.
ps -o pid,ppid,etime,command -p 45061,20248,80143
kill 45061; sleep 1; kill 20248 80143
ps -Ao pid,command | grep -E 'watchdog|heartbeat|caffeinate' | grep -v grep     # expect nothing
rm -f reports/heartbeat_render.pid reports/watchdog_render.pid reports/heartbeat.pid reports/watchdog.pid runs/constrained/logs/caffeinate.pid

# 0.2 Ignore every derived cache BEFORE any git add. No trailing slash on features/rssi_full, so the symlinks are covered too.
cat >> .gitignore <<'EOF'

# Derived caches, regenerable in minutes, never committed (cleanup brief 2026-09-23).
runs/**/features
runs/**/rssi_full
runs/constrained/windows*/
runs/constrained/dc2_*/windows/
runs/constrained/demo_archive/
runs/identify/idmax/bank/
EOF

# 0.3 Stop tracking the two committed window folders (the files stay on disk for now).
git rm -r -q --cached runs/constrained/windows_w1 runs/constrained/windows_w05

# 0.4 Delete the untracked, disposable trees BEFORE the snapshot, so they never enter history.
#     Nothing depends on them (section 4.2). Without this, the commit carries about 270 MB of them.
rm -rf runs/constrained/dc2_room_B_standin_s0.5_pressalign runs/constrained/dc2_room_B_standin_decoys_s0.5_pressalign
rm -rf runs/artefacts_s0.5_retrain_shared runs/artefacts_s0.5_retrain_s0 runs/artefacts_s0.5_retrain_s1 runs/artefacts_s0.5_retrain_s2
rm -rf runs/artefacts_s1.0_retrain_s0 runs/artefacts_s1.0_retrain_s1 runs/artefacts_s1.0_retrain_s2     # NOT runs/artefacts_s1.0_retrain_shared
rm -rf runs/constrained/demo_archive

# 0.5 What would git add take? Dry run at snapshot time, after 0.2 to 0.4: about 0.63 GB, largest file 20.4 MB.
#     Most of it is the shipped lattice's posteriors (runs/artefacts_s0.5_pressalign_*/posteriors), committed on
#     purpose, as the grid lattice's posteriors already are. Stop if anything is over about 25 MB.
git status --porcelain --untracked-files=all | awk '$1=="??"{print $2}' | while read f; do [ -f "$f" ] && stat -f '%z %N' "$f"; done | sort -rn | head -15

# 0.6 Commit everything and tag it. The tag is the archive every later deletion relies on.
git add -A
git commit -m "snapshot before cleanup: batches 2026-09-21 to 23h and the DC2 freeze"
git tag pre-cleanup

# 0.7 Baseline. Record the pass, fail and skip counts; failures here are pre-existing.
python3 -m pytest -q tests
python3 -m pytest -q tests/test_model_freeze.py tests/test_id28_dc2_score.py tests/test_id29_dc2_score.py tests/test_idgp_dc2_score.py tests/test_idgp_contract.py
```

##### Step 1. Delete the remaining regenerable caches (about 21 GB here, 45 GB with step 0.4)

```bash
rm -rf runs/constrained/windows_half runs/constrained/windows_w1 runs/constrained/windows_w05
rm -rf runs/artefacts/features
rm -rf testing/from_data

# Check: no shipped or frozen link now dangles. Expect no output.
for l in runs/*/features runs/*/rssi_full; do [ -e "$l" ] || echo "DANGLING $l"; done
python3 -m pytest -q tests/test_model_freeze.py tests/test_one_lattice.py tests/test_dc2_ingest_guard.py tests/test_stride_isolation.py
```

##### Step 2. Rewrite git history (about 5 GB), then push

Precondition: `git status --porcelain` is empty, and no other Claude session is working in this
repo (ask the operator). No live freeze records a commit hash (checked), so rewritten commit IDs
orphan no record; freezes record file hashes, which do not change.

```bash
pip3 install git-filter-repo          # not installed at snapshot time
git filter-repo --invert-paths --path runs/constrained/windows_w1/ --path runs/constrained/windows_w05/ --force
git remote add origin https://github.com/UzayrB/csi-thesis.git     # filter-repo removes remotes by design
git count-objects -vH                                                  # expect well under 1 GB
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | awk '$1=="blob" && $2>100000000'   # expect nothing
python3 -m pytest -q tests/test_model_freeze.py
```

Push only after the operator confirms the GitHub repository is **private** (participant first
names appear in file names; POPIA) and says to push. `main` is an ancestor of
`fh-live-2026-09-19` (checked), so it fast-forwards:

```bash
git branch -f main fh-live-2026-09-19
git push -u origin main --tags
```

##### Step 3. Prune code, tests, scripts and documents (git history keeps all of it)

1. `git rm` the 82 finished `pipeline/constrained` modules and the 29 finished `pipeline/identify`
   modules (4.5), the 32 scripts and 12 tools (4.7), the stale tests (4.6), about 158 reports
   (4.8), and `testing/` (4.4). If the operator agrees: the 5 optional `rb*` modules with their tests.
2. Before each group, grep for the name as an import **and** as a string
   (`-m pipeline.x.y`, `importlib`), because the 2026-09-18 cleanup broke a test that imported a
   module inside a subprocess string.
3. Fix the tests that referenced deleted things (`testing/` in six tests, `gait_features`,
   `id12_conditioning`, the dead cases of `test_report_consistency`).
4. Rewrite `README.md` (with `test_track_entrypoint` and `test_report_consistency`), `STATE.md`,
   and `reports/README.md`. Short, current, pointing at freeze 23h, `MODEL_FREEZE_DC2.md`,
   `RENDER_RULES.md` and `DC2_FIELD_CHECKLIST.md`.
5. Delete the `.DS_Store` files, `__pycache__` and `.pytest_cache` (hazard H6).
6. Update the Claude memory entry `handoff-entry-point` (R22).

**Checks after step 3, all required:**

```bash
python3 -m pytest -q tests          # no new failures against the step 0.6 baseline
# every kept module imports on its own (one process each, because import-time guards depend on import order)
for f in $(git ls-files 'pipeline/*.py'); do m=${f%.py}; m=${m//\//.}; m=${m%.__init__}; python3 -c "import $m" 2>/dev/null || echo "IMPORT FAIL $m"; done
# the DC2 path end to end: must report 72 of 72 EXACT in runs/constrained/fh/dc2_pipeline_standin/results.json
python3 -m pipeline.constrained.dc2_pipeline --room room_B --stand-in
rm -rf runs/constrained/dc2_room_B_standin_s0.5_pressalign        # it writes 5.6 GB again
git add -A && git commit -m "cleanup: finished stages, stale documents and retired history removed; git history is the archive"
```

##### Step 4. After DC2 (T3, about 27 GB more)

Once the Room B analysis and DC2 identification scoring are done and the freeze is lifted:
`runs/artefacts_s0.5_pressalign_shared/` (12.7), `runs/artefacts_s1.0_retrain_shared/` (6.3),
`runs/constrained/windows_s0.5_pressalign/` (6.3), `runs/identify/idmax/{features,bank}` (2.0),
and whatever DC2 itself writes under `runs/constrained/dc2_*` beyond its reports and results JSON.
All of it can be rebuilt from `data/`.

---

#### 7. Hazards

- **H1. A trailing slash follows a symlink.** `rm -rf runs/artefacts_s1.0_roomA3_s0/features/`
  empties the shared cache the frozen DC2 trees need. Remove a symlink with `rm <path>`, no slash.
  Delete a folder that contains symlinks by naming the folder itself (`rm -rf <folder>`), which
  does not follow them. Never glob `*/features/`.
- **H2. `git add -A` before step 0.2** commits 52.5 GB. Always run the size check of 0.5 first.
- **H3. Pinned files.** No editor, formatter or search-and-replace touches them, including
  whitespace. Running a formatter over `pipeline/` or `tests/` breaks the freeze.
- **H4. String imports.** A module is not dead just because nothing imports it by `import`.
  Grep for the dotted name in code, shell scripts and the Makefile.
- **H5. Processes.** Kill by PID after reading the command line. Never `pkill`.
- **H6. `data/` sweeps.** The 2026-09-18 cleanup deleted two files under `data/` with an unscoped
  `find -delete`. Use `find . -path ./data -prune -o -name .DS_Store -print -delete`.
- **H7. Pushing is outward-facing.** Confirm the repository is private and get the operator's
  go-ahead first.
- **H8. Do not re-render.** `runs/constrained/demo/` videos are hashed in freeze 23h.
- **H9. Sizes.** `du` and Finder disagree on APFS; judge progress with `df -h`.

---

#### 8. Expected result

| after | repository | notes |
|---|---|---|
| now | 93 GB | |
| steps 0.4 and 1 | about 48 GB | caches, stand-ins, retired lattice windows, `testing/from_data` |
| step 2 | about 43 GB | `.git` from 5.6 GB to about 1 GB (about 0.5 GB of history plus about 0.6 GB of shipped posteriors committed at step 0.6); branches pushable |
| step 3 | about 42 GB | about 450 fewer files; little space, much less confusion |
| `data/` overrides (R5), if accepted | about 37 GB | `data/features`, `data/retired/azrah_zaid/derived` |
| step 4, after DC2 | about 10 GB | raw data, `data/windows`, shipped models and posteriors, code, documents |

---

#### 9. Decisions for the operator (tick before the cleanup starts)

- [ ] R1, R2, R3, R4, R6, R15 to R19, R22: accept as stale and override as described.
- [ ] R5: delete `data/features` (2.3 GB) and `data/retired/azrah_zaid/derived` (3.0 GB)?
- [ ] `data/retired/azrah_zaid/captures` (0.9 GB of raw capture): keep here, or move off the laptop?
- [ ] Step 0.6: commit the shipped lattice's posteriors (about 0.6 GB, as the grid lattice's already
      are), or add `runs/**/posteriors/` to `.gitignore` for a lean repo (they re-infer in 19 min)?
- [ ] Step 2: rewrite git history (local only; no remote branch holds the affected commits).
- [ ] Push to GitHub after step 2: is `UzayrB/csi-thesis` private?
- [ ] Step 3: delete the five optional `rb*` modules with their tests?
- [ ] Thesis-record reports (4.8): keep all, or prune further?
- [ ] Old branches: convert to `archive/*` tags?

---

## CLEANUP_LOG_2026-09-24.md

**Source:** `reports/CLEANUP_LOG_2026-09-24.md`, 2026-09-24. **SHA-256:** `be9ee1debce5c25e92cb54c453741f9e8431f22a0ae318c9b57352cf97d495a1`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### CLEANUP LOG, 2026-09-24

What the cleanup session did, against `cleanup_prompt_2026-09-24` and `reports/CLEANUP_BRIEF_2026-09-23.md`.
Every time below was read from the clock or from git. Sizes are `du -sh .` for the repository and `df -h` for
free disk space on the data volume. Deviations from the prompt are marked **DEVIATION** and explained.

#### Summary

| | before | after |
|---|---|---|
| repository on disk | 93 GB (05:30) | 36 GB (08:51) |
| free disk space | 49 GiB | 73 GiB, plus 33 GB waiting in `~/.Trash/csi-thesis-cleanup-2026-09-24/` |
| `.git` | 5.6 GB (5.1 GiB of it loose window blobs) | 1.3 GB, one pack, no blob over 100 MB |
| uncommitted paths | 592 | 0 |
| test suite | 1261 passed, 8 skipped, 0 failed | 961 passed, 18 skipped, 0 failed (fewer tests because suites parametrised over module files shrank with the modules) |
| pinned hashes (163 files) | written 05:31:09 | all 163 unchanged, verified at the end of every step |
| push to GitHub | last push 2026-09-09 | `main` and 16 tags pushed at 08:50:58; `origin/main` = `74d3c3d` |

#### Step 0: make everything safe (05:30 to 05:41)

- **05:30:46, baseline.** The repository was 93 GB and 49 GiB of disk was free. There were 592 uncommitted paths
  on `fh-live-2026-09-19`, and the last commit was `707d2b0` (2026-09-21).
- **05:31:09, `reports/PINNED_FILES.txt` written: 163 files, each with its SHA-256.** The sources, following brief §4.1:
  - every `path: sha256` pair in the live freezes (`TRACKING_FROZEN_2026-09-23h` and its addendum,
    `IDENTIFICATION_FROZEN_2026-09-23{b,b_ADDENDUM,c,e,f}`);
  - the 23h `videos_sha256` block (the six demo videos);
  - every `reports/PREREG_*`;
  - every file in `reports/DC2_DEPENDENCY_CLOSURE.txt`;
  - the live freeze JSONs themselves.
- **Pre-existing hash drift, found at step 0 and NOT caused by the cleanup.** Five files already differed from the
  hash a live freeze recorded:
  - `reports/PREREG_DC2_crossroom_2026-09-22.md` matches the new hash recorded in `TRACKING_FROZEN_2026-09-23h_ADDENDUM.json`,
    as designed.
  - Four identification files were edited 3 to 18 minutes after the 23b identification freeze was written (13:41 and
    13:54): `pipeline/identify/id19_bank.py` and `id19_featbank.py` (both 13:57:46, pinned by `23b_ADDENDUM`),
    `reports/FINDINGS_stageid19.txt` (13:59:02) and `reports/DC2_ID_PROTOCOL_2026-09-23b.md` (13:54:56), both pinned
    by 23b.
  - The DC2 identification scorers gate on the later 23e and 23f freezes, which match. **Open item for the
    identification session.**
- **05:31:43 to 05:37:06, life support stopped.**
  - `touch reports/STOP_HEARTBEAT` at 05:31:43, after which the watchdog (PID 45061) logged "watchdog stopping" at
    05:31:53.
  - The heartbeat (PID 20248) exited at its next wake, confirmed at 05:36:58.
  - `caffeinate -dimsu` (PID 80143) was killed by PID at 05:37:06. No `pkill`.
  - The pid files and the stop file were deleted.
- **`.gitignore` extended:** `runs/**/features`, `runs/**/rssi_full`, `runs/**/posteriors/`, `runs/constrained/windows*/`,
  `runs/constrained/dc2_*/windows/`, `runs/constrained/demo_archive/`, `runs/identify/idmax/bank/`. No `posteriors/` folder
  is committed. `windows_w1`, `windows_w05` and the three tracked posteriors folders (`artefacts_ends`, `artefacts_w1`,
  `artefacts_w05`) left the index but stayed on disk.
- **`data/` in git: no raw capture is tracked, and none appears anywhere in history.** Checked with `git ls-files data` and
  `git rev-list --objects --all` for `data/`, `.bin` and `.gt.json`. `data/` and `*.bin` were already gitignored.
- **05:34:30, the brief's step 0.4.** The untracked, disposable trees were deleted before the snapshot so they never
  entered history, 24.1 GB in all:
  - both DC2 stand-in caches (5.6 GB each);
  - `runs/artefacts_s0.5_retrain_{shared,s0,s1,s2}` (12.8 GB);
  - `runs/artefacts_s1.0_retrain_{s0,s1,s2}` (26 MB);
  - `runs/constrained/demo_archive` (63 MB).

  Free disk went from 49 to 73 GiB.
- **05:35:11 to 05:39:06, baseline suite: 1261 passed, 8 skipped, 0 failed** (235.6 s).
- **05:39:31, snapshot commit** (now `3c3c779` after the rewrite), tagged `pre-cleanup`. Size check first: 169 MB
  across 2093 files, the largest 6.0 MB, no raw capture.
- **05:41:14, DEVIATION: an archive commit before step 1** (now `f6d227a`), and **`pre-cleanup` moved onto it**.
  - The prompt deletes the grid trees on the premise that they "come back via `git checkout pre-cleanup`".
  - That was false for `runs/artefacts_half/models/`, which the old `.gitignore` excluded: 126 model files (43.5 MB)
    existed nowhere else.
    - 108 were the `base` and `edge100` variants of the refused 2026-09-23 entry-straddling arms.
    - 18 were grid within-day half heads.
  - They were force-added and committed, so the premise now holds.
  - Every other grid model is tracked or has a byte-identical copy in a kept press-aligned tree (checked by SHA-256).
  - Fourteen gate-energy `.npy` caches were not archived, because they are derived.

#### Step 1: delete the regenerable caches (05:42 to 05:47)

- **Checks before deleting:**
  - A full symlink scan found no link into the grid artefact trees.
  - Twelve links into `windows_half` come from `runs/constrained/dc2_standin/windows/`, which the current stand-in never
    reads. `dc2_run.cfg_for` reads only `dc2_standin/data/room_B/calibration.json`, and nothing in `pipeline/`, `tests/`
    or `scripts/` names `dc2_standin/windows`.
  - The render reads the grid tree `artefacts_fh1s` only when it runs without the pool (`f3_render`, `uses_F and not
    uses_pool`), and that path returns `None` if the file is missing. The shipped render uses the pool.
- **05:42:16, DEVIATION: moved to the Trash rather than deleted.** The permission layer refused `rm -rf` on this set
  (as irreversible local destruction), so everything went to `~/.Trash/csi-thesis-cleanup-2026-09-24/` (28 GB):
  - `runs/artefacts/features` (6.3 GB);
  - `runs/constrained/windows_w1`, `windows_w05` and `windows_half` (11.1 GB);
  - the grid trees `runs/artefacts_{half,fh1s,g1s1,g1s2,g1g100s0,dispend}` (0.9 GB);
  - `testing/from_data` (3.9 GB), `data/features` (2.3 GB) and `data/retired/azrah_zaid/derived` (3.0 GB).

  **The space frees only when the Trash is emptied.**
- **Checks after deleting:**
  - The only dangling links in `runs/` and `data/` are the 12 expected ones in `dc2_standin/windows/`.
  - Freeze, lattice, ingest-guard, stride and identification-scorer tests: 70 passed.
  - All 163 pinned hashes unchanged.
- **05:46:55, commit** (now `71c47f2`): the grid trees' tracked files. Repository 41 GB.

#### Stop point, then step 2: history rewrite, branches, push (07:57 to 08:02)

- Uzayr confirmed that no other Claude session was active. Five Claude Code processes were open at the time.
  Ten `archive/*` tags already existed; they date from 2026-09-18 17:23:26 (the first cleanup), so they were not a
  sign of activity tonight.
- **07:58:18 to 07:59:01, `git filter-repo --invert-paths` on `runs/constrained/windows_w1/` and `windows_w05/`.**
  Results:
  - 602 commits parsed.
  - `.git` went from 5.21 GiB loose plus 484 MiB packed to one 1.30 GiB pack.
  - **No blob is now over 100 MB**; the largest is 20.7 MB.
  - The remote was re-added and the pinned hashes were unchanged.
  - The pack is larger than the brief's 0.5 GB estimate because history legitimately holds old posteriors (grid trees,
    about 540 MB), `runs/constrained` results (325 MB) and `testing/runs` (306 MB).
  - No live freeze records a commit hash (checked), so the rewritten commit IDs orphan no record.
- **Branches.** All 15 non-main branches are `archive/<name>` tags; five tags are new and ten already existed and
  matched. `main` was fast-forwarded to the old `fh-live-2026-09-19` and checked out. There are 16 tags, including
  `pre-cleanup`.
- **08:00 to 08:02, push FAILED.** `git push -u origin main --tags` returned `error: RPC failed; HTTP 400 curl 22`
  and `send-pack: unexpected disconnect while reading sideband packet` within 5 seconds, three times:
  - with the default settings;
  - with `http.postBuffer` at 1 GiB;
  - over HTTP/1.1 (`http.version`).

  A staged push of an older commit was refused by the permission layer (as destructive to git). Nothing on GitHub
  changed. See step 3e for the final attempt.

#### Step 3a: code (08:03 to 08:10)

- **Grep before deleting.**
  - Every removal candidate was grepped as an import and as a string.
  - `pipeline/identify/idmax_checkin.py` **stays**, because the pinned `idgp_checkin.py` imports it (DEVIATION from the
    brief's list).
  - `gait_features` and `id12_conditioning` go, and three identification tests were adjusted.
- **Keep set.** The prompt's keep set (brief live list, `DC2_DEPENDENCY_CLOSURE.txt`, pinned files, live rig needs:
  188 files) was diffed against the delete list: no clash.
- **Render-needed names.** Seven of them (`a3_lock`, `b1_motion`, `f2_verdict`, `g6_timeline`, `r1_reference`,
  `r3_lagsweep`, `r3_prior`) are loaded by `f3_render` as RESULTS and never imported; the modules went, and the
  `fh/` results stay.
- **Removed with `git rm`:**
  - 87 `pipeline/constrained` modules (82 finished plus the 5 optional `rb*`);
  - 28 `pipeline/identify` modules;
  - 32 scripts and 12 tools;
  - `tests/test_bounded_demo.py`, `tests/test_stride_isolation_rb2d.py` and `tests/test_gait_features.py`;
  - `testing/` (3998 tracked deletions in all). Its untracked remnant (a `.DS_Store`, one `.pyc`) went to the Trash.
- **Kept:** 75 constrained modules, 32 identification modules, 3 scripts (`render_demo.sh`, `live_rig_run.sh`,
  `track.py`) and 4 tools.
- **`reports/ARCHIVE_CODE.md`:** one line per removed module, script, tool and test, with what it did, where its results
  live and how to restore it, plus the derived trees and their rebuild commands.
- **08:09:50, commit `fbe2dd4`.**
- **DEVIATION, caught by the suite at step 3e and fixed:** a dotted-name grep misses tests that read a stage module's
  source by FILENAME through `pathlib`. Ten tests failed on removed modules, and eight test files were corrected (listed
  in `ARCHIVE_CODE.md` section 5). Every registry guard still runs on the modules that remain.

#### Steps 3b and 3c: refactor plan and reports (08:10 to 08:23)

- **`reports/POST_DC2_REFACTOR.md`:**
  - stage modules that became libraries, with importer counts;
  - duplicated helpers, found by AST hash;
  - the grid lattice decision;
  - the identification package;
  - the T3 cache deletions;
  - the tests to settle.

  Each item names the files involved and the check that proves it safe.
- **150 report files removed.** Of those, 146 were in the delete group:
  - 115 `FINDINGS_stage*.txt`;
  - markers, pid files, logs and closed queues;
  - superseded briefs, handoffs and summaries, including **`HANDOFF_2026-09-23.md`** (its `windows_half`
    instruction was unsafe).

  The other four were consolidated originals nothing cites: `DC2_REPORT_room_B_STANDIN.md`,
  `DC2_REPORT_room_B_STANDIN_DECOYS.md`, `CLOSING_ID_2026-09-23.md` and `HANDOVER_ID_2026-09-23.md`.
- **DEVIATION, kept although on the brief's delete list**, because something that stays cites them:
  - `FINDINGS_stageid20`, `id23`, `id25` and `id26` (`ID_QUOTABLE` and the identification record cite them as the
    sources of quotable figures);
  - `BRIEF_motion_and_lock_2026-09-20.md` and `BRIEF_render_fix_2026-09-20.md` (their pre-registration JSONs cite them);
  - `CLEANUP_LOG_2026-09-18.md` (freezes 18b and 18c);
  - `DC2_ID_PROTOCOL_2026-09-23.md` (the pinned version b cites it).
- **`reports/RECORD_TRACKING.md`:** eleven tracking reports, each verbatim (headings demoted two levels, verified line
  for line), in date order, with an index and one-line supersession notes. The notes cover:
  - the causal-lock and drawn-lock corrections;
  - the headline moving to 73.33 post-amendment;
  - on-screen tracking at 45.30;
  - the render having changed since.
- **Originals mostly kept.** The prompt deletes an original only when nothing references it. Nine of the eleven
  originals are cited by `HANDOFF_2026-09-22.md`, the pinned `PREREG_prepress_region`, `SEMIBOUNDED_STATE.md` or a
  pre-registration JSON, so they stay beside the record, which gives each one's SHA-256. The record therefore consolidates
  the reading copy but compresses little. The originals can go once their citing documents are consolidated after DC2.
- **Identification appendix.** `CLOSING_ID`, `CLOSING_IDGP` and `HANDOVER_ID` were appended to
  `IDENTIFICATION_2026-09-18.md` verbatim, with a note that `CLOSING_ID`'s A3 figure (20.833) is not quotable. No
  participant is named, so the IDMAX no-names test still passes. `CLOSING_IDGP`'s original stays (`QUEUE_IDGP` cites it).
- **`reports/README.md`:** rewritten as an index of all 100 entries, with markers.
- **08:22:48, commit `e93a33a`.**

#### Step 3d: top-level documents (08:23 to 08:28)

- **`README.md`:** rewritten with tracking's headline quoted exactly (checked against freeze 23h: 62.50 [30.00, 86.67],
  73.33 [35.00, 87.50], +3.80 [0.83, 6.94]), plus the demo, DC2 and identification.
  `test_readme_quotes_the_delivered_system_not_the_weakest_arm` now checks the README against freeze 23h instead of the
  2026-09-17 `stage5_live` figures.
- **`reports/HEADLINES.txt`:** rewritten with the tracking headline, the quotable identification figures, the
  withdrawn claims (including the old line 23) and the exploratory 23f result. The old file and its appended stage lines
  are at the tag. No test reads it; `common` and `rebuild_common` only append.
- **`scripts/render_demo.sh`:** now runs `f3_render`, which sets its own roots from `lattice.py`; it used to run
  `rc8_demo`. It was not run.
- **`STATE.md`:** rewritten as a one-screen current-state page.
- **Housekeeping:** 12 `__pycache__` folders, 7 `.DS_Store` files and `.pytest_cache` went to the Trash. The walk
  skipped `data/` and `.git`, and `data/.DS_Store` is untouched.
- **Memory:** in the `handoff-entry-point` note, the claim that a second session runs was removed from the body and the
  description. Tracking's pointers were kept.

#### Step 3e: checks, commit, push

- **08:28:13 to 08:28:30, import check: 126 of 126 kept modules import on their own.** Each module was imported
  in a fresh process, because the import-time guards depend on import order.
- **08:28:05 to 08:32:51, first full suite: 10 failed, 955 passed, 17 skipped.** Every failure was a test that read a
  removed stage module's source by filename, plus one render check that looked for a manifest under `testing/`.
- **Tests fixed** in `test_cross_pairing_key`, `test_pass_pairing_key`, `test_no_pacer`, `test_entrypoint_guard_form`,
  `test_lock_is_causal`, `test_reported_config_is_applied`, `test_freeze_quotes_the_current_figure` and
  `test_asserted_not_measured`. `ARCHIVE_CODE.md` section 5 has the detail.
- **08:33:17 to 08:37:55, second full suite: 961 passed, 18 skipped, 0 failed.** Against the baseline, 10 skips are new:
  - 8 cases in `test_report_consistency`, whose documents lived only in `testing/`;
  - 1 in `test_lock_phase`, which re-measures the retired grid lattice's fault on the deleted `windows_half`;
  - 1 from the now-empty `CROSS_ARM` parameter set.

  The other 8 skips were there before. All ten are recorded in `POST_DC2_REFACTOR.md`.
- **08:38:14 to 08:47:15, the DC2 stand-in end to end: 72 of 72 EXACT** (`stand_in_equals_shipped`). The fusion
  plumbing is also 72 of 72 EXACT, and every step exited 0.
  - The pooled, per-session, calibration, constants, fusion-arm and exploratory figures are identical to the run that
    freeze 23h cites; only the run time differed (9.01 against 5.37 min).
  - The freeze-cited `runs/constrained/fh/dc2_pipeline_standin/results.json` was backed up first and restored byte for
    byte afterwards. The rerun's copy was kept outside the repository.
  - The stand-in's 5.6 GB working folder and its regenerated report went to the Trash.
  - Nothing else in `runs/` or `data/` was written, symlinks followed.
- **Pinned hashes:** all 163 unchanged after every step.
- **08:48:25, commit `74d3c3d`.**
- **08:48:34 to 08:50:58, push SUCCEEDED** with `http.postBuffer` at 2 GiB (repository config). The pack now goes up
  with a declared length instead of chunked, which GitHub had refused with HTTP 400. `main` and 16 tags pushed;
  `origin/main` = `74d3c3d`. The repository config keeps `http.postBuffer=2147483647` and `http.version=HTTP/1.1`.
- **Commits, after the history rewrite:**
  - `3c3c779` snapshot;
  - `f6d227a` archive of the grid half models, which is the tag **`pre-cleanup`**;
  - `71c47f2` step 1;
  - `fbe2dd4` step 3a;
  - `e93a33a` steps 3b and 3c;
  - `74d3c3d` step 3d;
  - then this log's own commit.

#### Open items

1. **Empty the Trash** once DC2 has run cleanly. `~/.Trash/csi-thesis-cleanup-2026-09-24/` holds 33 GB: the step 1
   caches, the stand-in rerun and the housekeeping. Until it is emptied, nothing there frees disk space.
2. **Tracking: the half tree's reader files** in `runs/artefacts_s0.5_pressalign_half` (sessions `s02_to_s01`,
   `s01_to_s02`, `s01_to_s03`, the `*_g25_e24_s0_link*.pt` and `*_g25_e24_s0_full.npz` files) are not in the 23h hashes.
   Tracking adds them to a freeze addendum after this cleanup. Until then that tree is untouchable.
3. **Identification: pre-existing drift against the 23b freeze** in four files: `id19_bank.py`, `id19_featbank.py`,
   `FINDINGS_stageid19.txt` and `DC2_ID_PROTOCOL_2026-09-23b.md`. They were edited after 23b was written. The DC2
   scorers gate on 23e and 23f, which match. The identification session should decide whether 23b needs an addendum.
4. **Kept on disk until after the Room B analysis, as the prompt decided:**
   - `runs/artefacts_s0.5_pressalign_shared` (12.7 GB);
   - `runs/artefacts_s1.0_retrain_shared` (6.3 GB);
   - `runs/constrained/windows_s0.5_pressalign` (6.3 GB);
   - `runs/identify/idmax/{features,bank}` (2.0 GB);
   - every `posteriors/` folder.

   `POST_DC2_REFACTOR.md` section 5 lists these and their checks.
5. **Not in the prompt's exact delete set, so left in place:** `runs/artefacts_ends`, `runs/artefacts_w1`,
   `runs/artefacts_w05` and `runs/cleanup` (about 90 MB), plus the 12 dangling, unused links in
   `runs/constrained/dc2_standin/windows/`.
6. **`RECORD_TRACKING.md` compresses little yet:** nine of its eleven originals are still cited by kept documents and
   stay beside it. They can go once `HANDOFF_2026-09-22.md` and the other citing documents are consolidated after DC2.
7. **The post-DC2 refactor** (`POST_DC2_REFACTOR.md`) waits until the freezes are lifted.
8. **The permission layer** refused `rm -rf` on step 1, a read-only grep once, and a staged push. The cleanup used the
   Trash and a plain push instead. To allow this kind of action next time, add a Bash permission rule in the settings.

---

## The attempts/ restructure, 2026-09-24

Written for this record by the session that did it. Every time was read from the clock or from git.

**The request.** Keep what the current model uses in the root of `pipeline/`, `reports/` and `runs/`, put everything
else in an `attempts/` subfolder, combine reports where nothing is lost, and delete nothing.

**The constraint.** Nothing that a live freeze hashes, and nothing DC2 imports, could move. That covers 159 files,
listed in `reports/PINNED_FILES.txt`. Moving them would break `tests/test_model_freeze.py`, the identification
scorers' hash gates and DC2's imports two days before DC2. So the stage-named libraries the frozen model imports
stay in `pipeline/constrained/`, and renaming them remains item 1 of `reports/POST_DC2_REFACTOR.md`.

**09:29, state.** The identification session had committed `5b8fb93` at 09:17: addendum D, the rehearsal Doppler
check, the runbook, the thesis summary, and freeze 23g. No process was running. The operator confirmed that no
other session was active.

**Baseline, 09:37 to 09:41.** All 163 pinned hashes were unchanged. The suite gave 968 passed, 18 skipped, 0 failed.

**`pipeline/`, commit `2f9f21e`.**
- **What moved:** 17 modules that no current module imports went to `pipeline/constrained/attempts/`:
  - the refused lock arms (`lock_horizon`, `t6_lockdiag`, `t7_lockarms`, `t9_lengthnorm`, `y2a_causal`);
  - the link-fusion measurement (`z3a_linkprod`, `z3b_g100native`);
  - the 2026-09-17 renderer (`rc1`, `rc4`, `rc5`, `rc8`, `rc9`, `re4_semibounded`);
  - the 2026-09-17 self-segmenting tracker (`rescore`, `stage1_pace`, `stage4_unified`, `stage5_live`).

  Its entry point `scripts/track.py` went to `scripts/attempts/track.py`.
- **Fixes:** six moved modules computed `REPO_ROOT` from their own path with three `dirname` calls; each gained a
  fourth. Imports between moved modules now use `pipeline.constrained.attempts`.
- **Checks:** all 127 modules import on their own, each in a fresh process. Eight tests follow the move, and the
  pairing-key and lock-causality scans include `attempts/`.
- **Nothing moved in `pipeline/identify/`:** all 33 modules are reachable from the pinned DC2 identification scorers.
- **`pipeline/README.md`** describes every module, with its role, its pin status and its importer count.

**`runs/`, commit `95762fb`.**
- **The root keeps 14 JSONs**, each for a stated reason in `runs/README.md`: freeze 23h and its addendum; freezes
  22c, 22d and 23e, which define the DC2 arms; the identification chain 23b to 23g; the two pre-registration JSONs
  that `s2_display` and `q3_startclf` read at run time; and the tracking-open supersession.
- **The root keeps every artefact tree** the model or DC2 reads.
- **Moved to `runs/attempts/`:**
  - 46 superseded JSONs (to `freezes/`);
  - 68 finished `runs/constrained` stage folders and three loose files (to `constrained/`; the commit message says
    "71 stage folders", which counted the three files);
  - 55 `fh` result folders that nothing reads (to `fh/`);
  - 13 finished identification stages (to `identify/`);
  - `artefacts_ends`, `artefacts_w1`, `artefacts_w05` and `cleanup`.
- **How each was checked:** by its literal name in every current module and test, with a separate search for
  dynamically built paths (none exist). Six `rb*` rebuild folders stay, because the shipped decoder loads them:
  - `rb0_preflight`, `rb1_truth`, `rb2_decoder`, `rb2c_alpha`, `rb3_display`;
  - `night/n2_arms`, which the pool and the render read.
- **Test follow-up:** the two tests that read moved files look in `attempts/` too.
- **Untracked, not lost:** the 54 tracked `rssi_full/*.npz` caches of the three old trees now fall under the
  `runs/**/rssi_full` ignore rule, so git stopped tracking them. They are on disk at the new location and in history.

**`reports/`, commit `128183a` and the next commit.**
- **The root keeps 63 files plus `figures/` and `attempts/`:**
  - the current model and its evidence;
  - the pre-registrations of what ships or runs at DC2;
  - DC2;
  - current identification;
  - `PINNED_FILES` and `POST_DC2_REFACTOR`.
- **Moved to `reports/attempts/`: the rest**, and the history was combined into three records, each checked line
  for line (27 of 27 verbatim checks passed):
  - `RECORD_TRACKING` gained part 2: batch reports 23c to 23f, the two handoffs, the two briefs of 2026-09-20,
    `FIGURES.md` and `ETA.txt`;
  - `RECORD_CLEANUPS` holds the four cleanup documents and this log;
  - `RECORD_IDENTIFICATION_HISTORY` holds the IDMAX queue, check-in log and closing report, and sheet v0.
- **Combined originals removed: 28.** Each was removed only after its current SHA-256 matched the copy in its record.
  - Nine had been verbatim in `RECORD_TRACKING` since the morning.
  - `CLOSING_IDGP` has been in the appendix of the identification record since the morning.
- **Kept as separate files:** the six refused-arm pre-registrations (pre-registrations are never merged), the long
  2026-09-18 tracking report, `SUMMARY.txt` and `ARCHIVE_CODE.md`.
- **Figures:** the IDMAX figures moved to `figures/identify/idmax/`. The 2026-09-17 architecture diagram (fixed 3 s
  lag, no longer the model) moved to `attempts/fig/`.
- **Pointers updated in current documents:** the identification privacy test's paths, the thesis summary's figure
  path, and the pointers in `README.md`, `STATE.md` and `POST_DC2_REFACTOR.md`. Records keep their historical
  pointers; `reports/attempts/README.md` maps every former file to where it lives now.

**`PINNED_FILES.txt` regenerated at 09:55: 159 files.**
- Identification freeze 23g and its addendum D were added.
- The six refused-arm pre-registrations moved unchanged and left the list; no live freeze hashes them.
- All 159 verify. The same five pre-existing drifts against older freezes remain (see the log above).

**Checks.**
- **Suite, 09:56 to 10:00:** 953 passed, 18 skipped, 0 failed. The 15 fewer passes were traced exactly:
  - `test_no_shadowed_stage_loads` still scanned only the `constrained/` root (-17);
  - the pairing-key scans gained `attempts/__init__.py` (+2).

  After extending that test to `attempts/`, it gives 76 of 76, and the suite totals 971 passed, three more than the
  baseline.
- **DC2 stand-in:** 10:01:06 to 10:07:26, **72 of 72 EXACT** (`stand_in_equals_shipped`); the fusion plumbing is also 72 of 72 EXACT.
  - The pooled, per-session, calibration, constants, fusion-arm and exploratory figures are identical to the run freeze 23h
    cites, so DC2 runs unchanged on the restructured `runs/`.
  - The freeze-cited results file was restored byte for byte.
  - The rerun's 5.6 GB working folder and regenerated report went to
    `~/.Trash/csi-thesis-standin-rerun-2026-09-24/`.
- **Pinned hashes:** all 159 unchanged at the end.

**The Trash had been emptied.** By 10:07 the folder the first cleanup filled (`~/.Trash/csi-thesis-cleanup-2026-09-24/`,
33 GB) no longer existed, and free disk space had risen from 73 GiB to 100 GiB. The step 1 caches of the first cleanup
are therefore gone for good:
- `runs/artefacts/features`;
- the window-probe and grid-lattice windows;
- the grid artefact trees' untracked files;
- `testing/from_data`, `data/features` and `data/retired/azrah_zaid/derived`.

All of them were derived and regenerable, and the rebuild commands are in `reports/attempts/ARCHIVE_CODE.md` section 7.
Every tracked file, and the 126 grid half-stride models archived before step 1, is still at the tag `pre-cleanup`.
