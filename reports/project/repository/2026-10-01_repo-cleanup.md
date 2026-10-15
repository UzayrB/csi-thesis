# scripts/, splits/ and the old tools deleted, 1 October 2026

**Uzayr's instruction (1 October, afternoon):** delete `scripts/` and `splits/`, and cut `tools/` down to what is
still needed, "but make sure when you are deleting we do not need them". This follows
`reports/PIPELINE_RETIRED_DELETED_2026-10-01.md`.

## How "not needed" was checked

For each file:
1. Search every possible caller:
   - `pipeline/`, `tests/`, `tools/` and the Makefile;
   - the current run scripts (`runs/dc2_results/*.sh`, the identification queues, `runs/restructure_2026-10-01/`);
   - for `splits/`, any code that reads the folder or `configs/splits.yaml`.
2. Ask whether a result the thesis cites still depends on it.

Three files had never been committed: `tools/dc2_capture.py`, `tests/test_dc2_capture.py` and
`tools/teaching_pack.py`. They were committed first as they stood (`5c49f09`), so everything deleted here is in git
at that commit.

## Deleted

| what | files | why it is not needed |
|---|---|---|
| `scripts/live_rig_run.sh` (and so `scripts/`) | 1 | It ran the 23h tracker live through `pipeline/live/rig_run.py`'s own entry point. The current rig is `python3 -m pipeline.live rig`, which uses only two helper functions from `rig_run.py`. Only a docstring and already commented-out tests named it. |
| `splits/` | 47 | The first version's split lists. Their only reader, `splits/split_by_file.py`, was deleted with `pipeline/retired/`. No code, test or script reads the folder. |
| `configs/splits.yaml` | 1 | Read only by the same deleted `split_by_file.py`. |
| `tools/dc2_capture.py`, `dc2_day_check.py`, `dc2b_day_check.py`, `dc2_hardware_check.py` | 4 | DC2 capture and day tools. Data collection is closed for good (identification brief, 30 September). They were used only by each other and by their own tests. |
| `tools/teaching_pack.py`, `teaching_pack_corrected.py` | 2 | The first teaching pack (29 September). The live app's export, `pipeline/live/app_teaching.py`, replaced it; the app names the old tool only in a docstring. Only old run scripts from 29 September called them. |

## Kept

| what | why |
|---|---|
| `tools/dc2_verify_run.py` | `pipeline/constrained/dc2c_pipeline.py`, which is kept, names it as the DC2 run's required verification step ("must say VERIFIED"). Deleting it would leave the DC2 results unverifiable in the repository. It imports only the standard library. |
| `tools/calibrate_gate.py` | Recalibrates the walking gate (`configs/gate.yaml`) if the boards are plugged in again. |
| `tools/make_layout_image.py`, `make_paths_image.py` | They draw `Layout.png` and `Paths.png`, which are usable as thesis figures. |
| `tools/pipeline_restructure.py` | The record of how `pipeline/` was restructured on 1 October. |
| `configs/gate.yaml`, `configs/operator_rt.json` | Read by `calibrate_gate.py` and by `pipeline/io/rt_calibration.py`. |
| `tests/` | The suite that checked every change of the day. |

## Tests

Each changed block is marked `# RETIRED 2026-10-01`, as in the previous note, and was commented out by
`runs/restructure_2026-10-01/comment_deleted_tools.py`.

- **`test_dc2_capture.py`:** all 17 of its tests are commented out.
- **`test_dc2b_day_check.py`:** 4 of its 5 tests are commented out. The one left does not need the tool.
- **`test_dc2_tools.py`:** the 6 day-check tests are commented out.
  - Its two tests of `dc2_verify_run` still run. They need three constants from the deleted day check (the board
    MACs, the receiver geometry and the transmitter position), which are copied into the test unchanged.
- **`test_freeze_2026_09_24.py`:** the 24b freeze includes `tools/dc2_day_check.py`. That file is now checked in git
  at `5c49f09`, the last commit that held it, and still matches its frozen hash.

## Verification

- **The full suite** (81 files, 14:59 to 15:15): **1,125 passed, 0 failed, 24 skipped.** Before this cleanup it
  was 1,152 passed. The difference is exactly the 27 tests commented out above (17 + 4 + 6).
- **The pre-flight:** ALL ok.
- **The code folders:** `pipeline/live/`, `constrained/`, `identify/` and `io/` were not touched.
