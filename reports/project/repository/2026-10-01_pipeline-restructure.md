# The restructure of pipeline/, 1 October 2026

**Uzayr's instruction (1 October):** keep `constrained/`, `identify/`, `live/` and `io/`; combine the smaller folders
into them; put every file nothing uses into a folder called `retired`. Before that, check whether the pinned files
still need to be pinned and whether the README is true, and update it. Both chats paused for it: tracking sent
"done" at 10:31, and identification sent "held", with nothing running and nothing uncommitted.

- **Applied:** 10:44, from base commit `5782af8`.
- **The map of every move:** `reports/PIPELINE_MOVES_2026-10-01.json` (old path to new path, old module to new
  module, and the base commit).
- **The tool:** `tools/pipeline_restructure.py` (`plan`, `apply`, `lists`).
- **The verification scripts and logs:** `runs/restructure_2026-10-01/`.

## 1. The new layout

| folder | holds |
|---|---|
| `live/` | the app, where both current models run |
| `constrained/` | the tracking model |
| `identify/` | the identification model |
| `io/` | from the boards to clean 2 s windows: capture, parsing, ground truth, cleaning, windowing |
| `retired/` | modules the current models do not use, by the folder they came from; each still imports |

`branches/`, `clean/`, `models/`, `realtime/`, `splits/` and `constrained/attempts/` no longer exist.

**Combined into the four folders (9 files):**

| was | now |
|---|---|
| `branches/gate.py` | `constrained/gate.py` |
| `models/heads.py` | `constrained/heads.py` |
| `models/link_cnn.py` | `constrained/link_cnn.py` |
| `clean/common.py` | `io/clean.py` |
| `splits/windows.py` | `io/windows.py` |
| `realtime/engine.py` | `live/realtime_engine.py` (`identify/engine.py` already exists) |
| `realtime/replay.py` | `live/realtime_replay.py` (`live/replay.py` already exists) |
| `realtime/rig_run.py` | `live/rig_run.py` |
| `realtime/tracker_live.py` | `live/tracker_live.py` |

**Retired (39 files):**
- **`retired/constrained/` (24):**
  - d4_headline, d5_train_room_a, d6_lock_commit, e1_switch, e2_switch, f3_render, t8_calib;
  - the 17 modules of the former `constrained/attempts/`: lock_horizon, rc1_diagnostics, rc4_calibration,
    rc5_renders, rc8_demo, rc9_contrast, re4_semibounded, rescore, stage1_pace, stage4_unified, stage5_live,
    t6_lockdiag, t7_lockarms, t9_lengthnorm, y2a_causal, z3a_linkprod, z3b_g100native.
- **`retired/identify/` (12):** id26b_cnn_diag, id_dc2_physics, idgp_bank, idgp_checkin, idgp_checks, idmax_checkin,
  idv2_figures, idw_extra, idw_physics, idw_setup, idw_starts, rehearsal_check.
- **Elsewhere:** `retired/models/fusion.py`, `retired/splits/assemble.py`, `retired/splits/split_by_file.py`.

**Both chats checked the list before the move:**
- **Identification** confirmed that current code imports none of its 12, and asked that `rehearsal_doppler_check.py`
  stay, since the engine uses it. It stayed.
- **Tracking** confirmed that the live app imports none of its own.

## 2. How "used" was decided

A file is kept when the current models reach it:
1. **Entry points:**
   - every module in `live/` and `io/`;
   - the identification engine (`engine`, `idw_core`, `ide_*`, `ixa_*`, `ixt_*`);
   - every pipeline file committed on 1 October.
2. **Records:** every module named in any of these:
   - a report first written on or after 28 September (77);
   - a run script changed since then (42);
   - the final tracking hash lists;
   - the app's model sets.
3. **Closure:** every module those import, and every module kept code launches by name (`python -m pipeline...`),
   repeated until nothing new appears.

Everything not reached was retired. This says what must exist for the current models to load and for every current
record to be regenerated. It does not prove that every function in a kept file runs.

## 3. What was rewritten

- **79 files:** imports, module paths and file paths were rewritten in `pipeline/`, `tests/`, `tools/`,
  `scripts/` and the Makefile.
  - `from <package> import <module>` statements were rewritten by their syntax tree, so every local name is
    unchanged.
  - Two of the 79 are tracking's untracked live tests (`tests/_live_checks.py`, `tests/test_live_stream.py`). They
    were rewritten and left uncommitted for tracking.
- **22 files** moved one level deeper; each finds the repository with one more `dirname`.
- **13 test files** referred to moved files in ways the rewrite could not see (section 6.4). They were fixed by hand.
- **Not rewritten:**
  - reports, run scripts and records under `runs/`;
  - historical docstrings that name the old packages.

  The JSON map resolves any old path.
- **Saved models:** across 4,894 saved model files in `runs/`, the only module path recorded is
  `pipeline.identify.idw_core`. It did not move, so no saved model needed changing.

## 4. The pins

`reports/PINNED_FILES.txt` lists 191 files from the freezes of 23 to 25 September. It says they may not be edited,
moved or renamed **until the Room B analysis is done**. That analysis closed on 28 September
(`reports/DC2_RESULTS_2026-09-28.md`).

- **On 1 October, before the move:** 190 of 191 still matched. `reports/RENDER_RULES.md` had changed with Uzayr's
  display decisions.
- **Released** for this restructure, on Uzayr's instruction: 17 pinned files moved, and 10 more had import lines
  rewritten.
- **Still checkable:** `PINNED_FILES.txt` is not edited. The two tests that hold pins now check each pinned file at
  the base commit, and allow the restructure to have changed only path lines (`tests/_restructure.py`):
  - `test_model_freeze.test_every_frozen_code_file_is_unchanged`;
  - `test_f4_render.test_f3_render_is_untouched`.

  Both pass.

## 5. The tracking model's own checks, carried over

- **Hash lists** (`runs/dc2_results/final/`): translated through the map:
  - which lists: `TRACE_HASHES_fin_A3`, `fin_B2` and `zsf_B2`, and `FINAL_CORRECTED_HASHES`;
  - each trace list dropped the two removed package files (`branches/__init__.py`, `models/__init__.py`);
  - each listed `constrained/gate.py`, `heads.py` and `link_cnn.py` under their new paths;
  - each re-hashed the code files whose import lines changed: 7 in each trace list, and `pd_arch.py` in the
    corrected list;
  - every data, model and result file kept its hash;
  - the originals are beside them as `*.pre_restructure.txt`.
- **Model sets** (`runs/live/models/`): rebuilt from those lists with `pipeline.live.model_sets build`:
  - `final`: 456 to 454 files;
  - `zeroshot`: 220 to 218 files;
  - the same changes as the lists; both pass `model_sets check`;
  - the originals are `*.pre_restructure.json`.

## 6. Verification

### 6.1 Imports
Every module imports, each in a fresh process:
- **before the move:** 247 of 247;
- **after it:** 246 of 246. Six package files were removed and five `retired/` package files added.

### 6.2 Pre-flight
`python3 -m pipeline.live preflight`: **ALL ok**.
- Its first run after the move failed one check, because `FINAL_CORRECTED_HASHES.txt` still held `pd_arch.py`'s old
  hash.
- After that list was translated, all checks passed. They passed again after the gates.

### 6.3 Tracking: exact reproduction and the G2 gate
**Exact reproduction** (`pd_repro_trace run`, with tracking's chain environment). Each run checks every listed
file's hash, rebuilds the decode in a fresh scratch tree with a trace on every file read, and compares it with the
frozen decode:

| cell | hashes checked, mismatched | inputs read outside the list | decode against the frozen one | PASS |
|---|---|---|---|---|
| fin_B2 | 271, 0 | none | EXACT, 0 committed lines changed | yes (36.0 min) |
| zsf_B2 | 216, 0 | none | EXACT, 0 committed lines changed | yes (32.8 min) |
| fin_A3 | 265, 0 | none | EXACT, 0 committed lines changed | yes (67.9 min) |

No run wrote outside its scratch tree. A3's g100 inference step took about 20 min, against 3 min on 30 September.
It was computing throughout (a sample showed the network's convolution and batch-norm steps), and its result is
EXACT. The cause of the slowdown is not known.

**The app's G2 gate** (semi mode, display K1g, whole-file clock, against the FC reference):

| cell | committed lines equal | locks equal | EXACT |
|---|---|---|---|
| fin_A3 | 120 / 120 | 120 / 120 | yes |
| fin_B2 | 120 / 120 | 120 / 120 | yes |
| zsf_B2 | 120 / 120 | 120 / 120 | yes |

The previous gate files are kept as `runs/live/final/gate_<cell>_semi.pre_restructure.json`.

### 6.4 The test suite
Run file by file.
- **Before the move:** 1,257 passed, 7 failed, 24 skipped. The 7 failures predate the move:
  `test_cross_pairing_key` (4), `test_model_freeze` (1, the RENDER_RULES change), `test_pass_pairing_key` (1),
  `test_report_consistency` (1).
- **First run after the move:** 25 failed, in 13 files. Every new failure came from a test's own reference to the
  old layout, never from a result:
  - paths assembled from parts (`REPO / "pipeline" / "constrained" / "f3_render.py"`);
  - two pin tests looking a file up by its new path;
  - a list of allowed packages that did not include today's packages;
  - two tests whose file scans still pointed at `constrained/attempts/`.
- **The fixes, in the tests only:**
  - each path now points at the new location;
  - the pin tests check pins as section 4 says;
  - the allowed packages are today's;
  - the scans cover `retired/constrained/`.
- **After the fixes:** each of the 13 files matches its baseline. Two collect more cases than before, because
  `gate.py`, `heads.py` and `link_cnn.py` are now among the files they scan.
- **A final full run** (11:57 to 12:08): **1,266 passed, 7 failed, 24 skipped.** The 7 failures are the same ones
  that predate the move. The only differences from the baseline are the 9 extra passing cases above.

**Identification:** `IDE_SLOW=1 python3 -m pytest tests/test_ide_engine.py tests/test_ide_rigrun.py`: **13 passed**.
These include the recorded B2 rig run equal to the harness, 299 of 299.

### 6.5 One slip in my own logging
The first launch of the reproduction runs (`verify.sh`) left out tracking's environment (`PD_CLEAN_PREFIX=FC` and
the frozen pace prior), so each run failed when it looked for the decode. The log still read `EXIT 0`, because the
`$(date)` in the same line reset `$?` before it was printed. This is the same pattern that hid a crash on
30 September.

`verify_repro.sh` re-ran the three cells with the environment and captures the exit code first. The figures above
come from that run.

## 7. What each chat was told

Both chats were sent:
- the move map;
- the verification results above;
- the rule for old paths in their notes and briefs: they resolve through `reports/PIPELINE_MOVES_2026-10-01.json`.

Tracking was also told that its untracked `tests/_live_checks.py` and `tests/test_live_stream.py` were rewritten.
