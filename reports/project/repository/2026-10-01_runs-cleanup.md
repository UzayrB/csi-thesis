# runs/ cleaned up, 1 October 2026

**Uzayr's instruction (1 October, late afternoon):**
- Lay out what is in `runs/` (45.5 GB), then delete the old tracking material ("section 2"); tracking is finished.
- Ask identification about its old models, since Uzayr still wants to try identification ideas.
- Look into tracking's model list; 28 GB is fine, so no change to the model was asked for.

**Result:** `runs/` went from 45.5 GB to 29.9 GB. Nothing was deleted outright: every file is in the macOS
Bin at `~/.Trash/TDR03_runs_cleanup_2026-10-01/<its path>`, and the space comes back when the Bin is emptied. The
list of every file moved, with its size, is `runs/restructure_2026-10-01/runs_cleanup_2026-10-01.tsv.gz`.

**Why the Bin.** A permanent delete of 15 GB of untracked files was blocked by Claude Code's safety check. Moving
the files to the Bin is the reversible version of the same step. Almost none of `runs/` is in git, so a file
deleted outright could only come back by re-running the code that made it.

## What went to the Bin (5,420 files, 16.96 GB)

| what | size | why it is not needed |
|---|---|---|
| `artefacts_s1.0_retrain_shared/` | 6.79 GB | 1 s feature arrays, read only by `pd_cells.py` to train cells; retraining input |
| 62 old cells in `dc2_results/cells/`: binaries only | 2.95 GB | development cells of 28 and 29 September (`d1*`, `d2p*`, `d4_attn*`, `3ref*`, `4i*`, ...). Nothing current reads them and no report since 29 September names them. Their `.json` result records (63 MB) stay in place. |
| `dc2_results/shared10_roomB/` | 1.73 GB | Room B training features; retraining input |
| `constrained/.../by_session/B1/windows/`: the window arrays | 1.01 GB | B1's 0.5 s windows; retraining input. Its 6 `meta.json` files stay: the app reads them for its cell prior. |
| `constrained/windows_s1.0_dc2/` | 0.95 GB | Room B 1 s windows; retraining input |
| `identify/audit/models/` (15 models) | 0.83 GB | identification's answer: only the audit runner and `ide_gs` loaded them. Every two-press figure comes from `audit/outputs/*.npz`, which stays. |
| `identify/engine/models/`: 9 v1 models and `gs_loso_A1`-`A3` | 0.79 GB | superseded by the v2 `_x` models. v1 `loso_B1` and `loso_B2` stay, because `ide_eval --v1` reloads them. |
| `identify/idwalks/models/` (16 models) | 0.60 GB | only `idw_run` (29 September); its figures are saved in `idwalks/outputs` |
| `artefacts/` | 0.50 GB | the 16 to 17 September 1 s tree, superseded. Its tracked `MANIFEST.md` stays. |
| `dc2_results/verify/`: rebuild scratch | 0.42 GB | scratch trees of earlier verification runs. The result files (`.json`) and the one reader cache the model reads stay. |
| `live/stream/`: the raw captures | 0.31 GB | the K0 streamed run, superseded by `stream_disp-K1g/`. Its screen recordings, logs and summaries (in git, cited by `LIVE_APP_BRIEF2_2026-09-30.md`) stay. |
| `attempts/`: binaries only | 0.09 GB | past experiments; their text records stay |

**The rule for mixed folders:** large binary arrays (`.npz`, `.npy`, `.pt`, `.bin`, `.pkl`) went, and text and
media records (`.json`, `.md`, `.jsonl`, `.mp4`, ...) stayed. Before the move, every file was checked against the
list of files the current tracking model reads (its model sets and hash lists, with links resolved). The one match,
`dc2_results/verify/reader_cache/B2_0102_*.pkl`, stayed.

## One wrong item, caught and restored

The small head trees `artefacts_s0.5_pressalign_{fh1s,g1s1,g1s2,g100,dispend}/` (367 MB, 180 files) were on the
list as "earlier head trees".
- **Why they are needed:** the live app's older tracking mode (`pipeline/live/tracking.py`, its five-head pool)
  loads its weights from them.
- **Why the check missed them:** they are not on the final model's list.
- **How it was caught:** 11 live tests errored ("head weights missing") and `test_dc2_ingest_guard` began to skip.
- **The fix:** all 180 files were moved back from the Bin. The 11 tests then passed, and the ingest guard passed 6
  of 6.

## Verification

**The current tracking model, after the move** (scripts and logs in `runs/restructure_2026-10-01/`,
`verify_runs_cleanup.sh`):

| cell | G2 gate (the app, semi mode, K1g) | exact reproduction (`pd_repro_trace run`) |
|---|---|---|
| fin_A3 | 120/120 committed lines, 120/120 locks, EXACT | PASS: EXACT, 0 committed changed, no input outside its list, no hash mismatched (51.5 min) |
| fin_B2 | 120/120, 120/120, EXACT | PASS, the same (36.6 min) |
| zsf_B2 | 120/120, 120/120, EXACT | PASS, the same (31.0 min) |

- **The model sets:** `final` (454 files) and `zeroshot` (218) pass `model_sets check`, every file present and matching.
- **The pre-flight:** ALL ok.
- **The gate files:** G2 rewrote `runs/live/final/gate_*_semi.json` with new timing fields only (service-time
  medians, percentiles, minutes). The committed versions were restored. The reproduction results are the new
  `run.json` files; the earlier ones are in git at `6769f8c`.

**The test suite.** The full run after the move gave:
- 11 errors in three live test files (`test_live_pool`, `test_live_tracking`, `test_live_decision_display`);
- 1 new skip in `test_dc2_ingest_guard`.

All of them came from the five head trees. After those were restored, the three live files passed 11 of 11 and the
ingest guard 6 of 6. Every other file matched the run before the cleanup: 1,125 passed and 9 skipped in all.

**Identification** checked its own files after the move: all ten `_x` models (25 files each), v1 `loso_B1` and
`loso_B2`, and `audit/outputs` (21 files) are intact.

**Tidying:**
- 1,598 empty folders left by the move were removed, among them the 42 emptied model folders.
- 2,768 links inside cells now point at files in the Bin. Nothing on the model's list follows them, and they would
  work again if the files were restored.

## Tracking's model list: what 10 GB would take (no change made)

**What needs the 25 GB.** About 25 GB stays for tracking: the Room A feature arrays (13.6 GB), the Room A 0.5 s
windows (6.8 GB) and the Room B features and windows (4.4 GB). Two things need them:
1. **The exact offline reproduction** (`pd_repro_trace`). Its per-step traces show the readers, the five head
   inferences and the decode each reading these arrays.
2. **The integrity checks.** The pre-flight hashes every file of `TRACE_HASHES_*`, and the replay harness checks
   the model set before each session. Both lists include the arrays because the reproduction reads them.

**What the live app reads at run time.** It does not read these arrays. Its code (`pipeline/live/final_model.py`)
opens:
- the head networks;
- a few config and statistics files;
- the training windows' `meta.json`, for the cell prior.

Every window's features it computes itself, as the packets arrive.

**What getting to about 10 GB would take:**
1. Split the model set into a run-time set (heads and small files) and a reproduction set.
2. Point the pre-flight and the replay harness at the run-time set.
3. Remove the arrays, so that exact reproduction would need them rebuilt from `data/` first (hours of compute).

That is a change to how the model is checked, so it belongs to a tracking chat, with its own verification. Uzayr
said 28 GB is fine, so it is left as an option.
