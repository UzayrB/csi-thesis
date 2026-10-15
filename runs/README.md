# runs/: results, trained models and caches

Rewritten 1 October 2026, after the cleanup of that day (`reports/project/repository/2026-10-01_runs-cleanup.md`). `runs/` is about
30 GB. Almost none of it is in git, so a file removed from here can only come back by re-running the code that made
it.

**Where removed files are:**
- **1 October:** 17 GB of old tracking binaries and old identification models were moved to the macOS Bin, at
  `~/.Trash/TDR03_runs_cleanup_2026-10-01/<their path>`, until the Bin is emptied. The list is
  `restructure_2026-10-01/runs_cleanup_2026-10-01.tsv.gz`.
- **24 September:** older results went to `attempts/` (see `attempts/README.md`). If a document points at `runs/X`
  and it is not here, look in `runs/attempts/X` or in that list.

## What the current models need

| model | what it reads under `runs/` |
|---|---|
| **Tracking**, the live app's final model | the files in `live/models/final.json` (454) and `zeroshot.json` (218), which the replay harness checks before each session, and the hash lists in `dc2_results/final/`, which the pre-flight checks (`python3 -m pipeline.live preflight`). They include the 25 GB of feature arrays and windows below, which the exact offline reproduction reads. |
| **Tracking**, the live app's older tracking mode (`pipeline/live/tracking.py`) | the five head trees `artefacts_s0.5_pressalign_{half,fh1s,g1s1,g1s2,g100}/` and the display head `..._dispend/` |
| **Identification**, the one-press engine (v2) | `identify/engine/`: the banks `bank_T*` and the models `*_x`; v1 `loso_B1` and `loso_B2` stay for `ide_eval --v1`. Its saved classifiers name `pipeline.identify.idw_core`. |

## The top-level folders

| folder | size | what it holds |
|---|---|---|
| `artefacts_s0.5_pressalign_shared/` | 12.6 GB | Room A feature arrays (`features/`, 18 files of 0.6 to 0.9 GB) and RSSI, which the press-aligned trees and cells link to. The final model's reproduction reads them. |
| `constrained/` | 10.8 GB | tracking results; see below |
| `identify/` | 4.3 GB | identification results; see below |
| `dc2_results/` | 1.1 GB | the final tracking model's cells, rules, hash lists and checks; see below |
| `live/` | 0.6 GB | the live app's model sets, replays, renders and streamed runs; see below |
| `artefacts_s0.5_pressalign_{half,fh1s,g1s1,g1s2,g100,dispend}/` | 0.4 GB | the heads the live tracking mode loads (models and posteriors) |
| `artefacts_s0.5_pressalign_roomA3/`, `artefacts_s1.0_roomA3_{s0,s1,s2,g100}/` | about 5 MB | the 18 frozen DC2 models of freeze 23h, re-hashed by `tests/test_model_freeze.py`. Their `features` links point at `artefacts_s1.0_retrain_shared/`, which is now in the Bin; the models themselves are here. |
| `artefacts/` | under 1 MB | the 16 to 17 September 1 s tree's `MANIFEST.md`; its binaries are in the Bin |
| `attempts/` | 20 MB | results moved out of the way on 24 September (`attempts/README.md`) |
| `restructure_2026-10-01/` | small | the records of 1 October: the restructure's verification scripts and logs, the commenting scripts, and the cleanup list |

## The JSON files in the root (the freezes)

Each is a frozen record that a document or test still cites. They are small and stay.

| file | what it records |
|---|---|
| `TRACKING_FROZEN_2026-09-23h.json` | the DC2 model freeze: the headline, the lock, the render, and the SHA-256 of every file DC2 ran (`tests/test_model_freeze.py`) |
| `TRACKING_FROZEN_2026-09-23h_ADDENDUM.json`, `_ADDENDUM_B.json`, `_ADDENDUM_C.json` | the recorded changes to 23h: the DC2 pre-registration's bytes; the 12 reader files `dc2_run.py` copies; `RENDER_RULES.md` (1 October) |
| `TRACKING_FROZEN_2026-09-24.json`, `_24b.json`, `_25.json` | the dc2b corrections and the DC2 day design; the capture corrections; identification first, then tracking (`tests/test_freeze_2026_09_24.py`) |
| `TRACKING_FROZEN_2026-09-22c.json`, `_22d.json`, `_23e.json` | the DC2 arms `b_abstain_0.25`, `a_veto_1.0` and product fusion at w = 0.25 |
| `IDENTIFICATION_FROZEN_2026-09-23b.json` and `_ADDENDUM.json`, `_23c.json`, `_23e.json`, `_23f.json`, `_23g.json`, `_24.json`, `_25.json`, `_28.json`, `_28b.json` | identification's freezes, from the DC2 configurations to 28 September; the hash gates of `id28_dc2_score`, `id29_dc2_score` and `idgp_dc2_score`; addendum D (`tests/test_addendum_d_hash.py`) |
| `PREREGISTRATION_display_position_2026-09-20.json`, `PREREGISTRATION_part2_arms_2026-09-20.json` | read by `pipeline/constrained/s2_display.py` and `q3_startclf.py` |
| `SUPERSESSION_tracking_open_2026-09-22.json` | the record that tracking is never closed (freeze 23h cites it) |

## `constrained/`

| folder | size | what it holds |
|---|---|---|
| `windows_s0.5_pressalign/` | 6.5 GB | the press-aligned 0.5 s windows of Room A; the final model's reproduction reads them |
| `dc2_room_B_s0.5_pressalign/` | 4.5 GB | Room B's windows and features by session (`by_session/B1`, `B2`); B1's window arrays are in the Bin, and its `meta.json` files stay because the app's cell prior reads them |
| `demo/`, `demo_v2/` | 33 MB | the first demonstration videos (freeze 23h) and the f4 render |
| `fh/` | 21 MB | results of earlier stages that tests and freezes still read |
| `rb0_preflight/`, `rb1_truth/`, `rb2_decoder/`, `rb2c_alpha/`, `rb3_display/` | 10 MB | the 17 September rebuild results the decoder still loads (configuration, transit geometry, truth) |
| `night/`, `dc2_standin/`, `dc2_standin_decoys/`, `windows_s1.0_dc2/`, `logs/` | small | the overnight arms; the DC2 stand-in; what is left of the Room B 1 s windows after the cleanup; logs |

## `dc2_results/`: the final tracking model

| folder or file | what it holds |
|---|---|
| `cells/` | one folder per cell. `fin_A3`, `fin_B2` and `zsf_B2` are the test cells of the final and zero-shot models; the three `d4c_fuse_*` are the rotations the app uses for development. The other cells keep their JSON results; the binaries of 62 old development cells are in the Bin. |
| `final/` | the hash lists (`TRACE_HASHES_*`, `FINAL_CORRECTED_HASHES*`), the pace prior, and the midpoint and zero-shot records |
| `rule/` | `FINAL_CONFIG.md` and the pre-registrations and rules of the app, the display and the dot, each with its `.sha256` |
| `verify/` | the checks' results (`repro_trace/run/<cell>/<cell>/run.json`, `clean/`, the reader cache the model reads) |
| `clean_readers/`, `dispend_final/`, `dispend_zeroshot/` | the cross-fit readers and the two display heads |
| `display/`, `v2/`, `presence/`, `propagation/`, `restructure_check/` | the dot choice, the V2 round, tracking's presence and propagation work of 1 October, and its restructure check |
| `render_final/`, `teaching/`, `teaching_corrected/`, `b10_view/`, `prn_view/` | earlier renders, teaching exports and views |
| `*.sh`, `logs/`, `HEARTBEAT.txt` | the run scripts and logs behind every result here |

## `identify/`

| folder | size | what it holds |
|---|---|---|
| `idmax/` | 2.0 GB | the IDMAX bank and features, and the stages `id19` to `id27`; still read by `id19_featbank`, `idmax_common` and `idgp_cadence` |
| `engine/` | 1.2 GB | **the current engine:** `PLAN.md`, the banks, the v2 models (`*_x`), v1 `loso_B1` and `loso_B2`, replays, evaluation and stage 1 |
| `final_extras/` | 0.4 GB | the 30 September extras (A1 to A4, the measures) |
| `teaching/` | 0.4 GB | the teaching pack's runs (1 October) |
| `audit/` | 0.3 GB | the audit's banks (`bank_v2` is the two-press reference), `outputs/` (every two-press figure) and `synth/`; its models are in the Bin |
| `dev/`, `idgp/`, `dc2/`, `dc2_view*/`, `dc2_src_relabelled/` | 0.1 GB | the dev bank the engine's bank builder reads; the IDGP run; the DC2 scoring views |
| `idwalks/` | 6 MB | the 29 September identification-walk results (`outputs/`, `eval_*.json`); its models are in the Bin |
| `lever_screen/` | 2 MB | the lever screen of 1 October (`reports/identification/2026-10-01_lever-screen.md`) |
| `id1_foundations/` to `id15_geometry/`, `logs/` | small | early stages whose results the identification modules `id3_embeddings`, `id14_crossday`, `id15_corridor` and `id28_dc2_score` still read; logs |

## `live/`

| file or folder | what it holds |
|---|---|
| `models/` | the app's model sets, `final.json` and `zeroshot.json` (and their versions from before the restructure) |
| `final/` | the app's gate files: G2 (semi) and G1 (legacy) for the three test cells and the rotations, with earlier versions kept beside them |
| `replay/` | the app's replay logs, by model and mode |
| `renders/`, `renders_K1g/` | the app's renders of A3 and B2 |
| `stream_disp-K1g/` | the streamed B2 run with display K1g, the demonstration of the rig path |
| `stream/` | the earlier K0 streamed run: screen recordings and summaries (its raw captures are in the Bin) |
| `identify/`, `identity_check/`, `id_synthetic/` | identification's rig runs, the identity-hook check, and gate 5's synthetic recordings |
| `gate*.json`, `timing_alone_*.json`, `mutations.json`, `screen/`, `cache/`, `unconstrained/`, `press_profile/` | the 25 September live-system gates (`reports/tracking/history/2026-09-25_live-system.md`), the timing, the mutation checks, and later checks |
