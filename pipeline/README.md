# pipeline/: the code, in four folders

Rewritten 2026-10-01 for the restructure of that day (`reports/project/repository/2026-10-01_pipeline-restructure.md`). Results live
in `runs/` and write-ups in `reports/`. Every module that moved, and where it went, is in
`reports/project/repository/2026-10-01_pipeline-moves.json`. The 39 modules the current models did not use were moved to
`retired/` and then deleted the same day; they are at the git tag `tracking-final-2026-10-01`.

| folder | what it holds |
|---|---|
| `live/` | **the app.** Both current models run inside it, and every thesis figure comes from replaying the recorded sessions through it. |
| `constrained/` | **the tracking model:** the networks, the windows' features, the decoder, the display rule, and the scripts that trained and checked the final model |
| `identify/` | **the identification model:** the one-press engine and the scripts that built, trained, replayed and checked it |
| `io/` | **from the boards to clean 2 s windows:** serial capture, raw CSI parsing, ground truth and presses, cleaning (`clean.py`) and windowing (`windows.py`) |

## How the current models run

**Tracking** (`python3 -m pipeline.live replay ...`, or `rig` on the boards):
1. **Packets in:** `live/rig.py` on the boards, or `live/stream_source.py` for a recorded session streamed as if
   live. Both go through `io/capture_logger.run_capture`: one serial reader per receiver, parsing with
   `io/parse.py`; the stream only replaces the packet source.
2. **Windows:** `live/stream.py` cleans with `io/clean.py` and cuts 2 s windows with `io/windows.py`;
   `constrained/lattice.py` places one on each press.
3. **Heads:** `constrained/link_cnn.py`, `heads.py`, `nets.py` and `pd_arch.py`, loaded through `artefacts.py`.
4. **Decision:** the decoder in `constrained/decoder.py` and `emissions.py`, with the start terms in
   `live/start_terms.py`; `live/final_model.py` ties the final model together.
5. **Display:** `live/display.py` and `live/screen.py`, display K1g (`final_model.DISPLAY_CANDIDATE`).
6. **Checks:** `live/model_sets.py` (the app's file manifests), the pre-flight in `final_model.py`, the harness in
   `live/app_replay.py` and the scorer in `live/app_score.py`.

**Identification** (`python3 -m pipeline.live.identify_engine ...`):
1. One press starts a 3 s window; `identify/engine.py` extracts its features, detects the direction and estimates
   the Wi-Fi speed (`identify/rehearsal_doppler_check.py`).
2. The eight-component ensemble decides; its saved classifiers name `pipeline.identify.idw_core`, so that module
   must keep its path.
3. `identify/ide_bank.py`, `ide_train.py`, `ide_replay.py` and `ide_eval.py` built, trained, replayed and scored it.

## The modules

Each table lists every module with the first sentence of its own docstring. Moved modules say where they were.

### `live/` (29 modules)

| module | what it does (its own docstring) |
|---|---|
| `__main__.py` | The live system's one entry command. |
| `anchor.py` | Device-clock anchoring, live. |
| `app_acceptance.py` | ACCEPTANCE for the app's renders (Uzayr, 30 September 2026, part E): MEASURED RESULTS ONLY. |
| `app_replay.py` | The app's replay harness (Uzayr, 30 September 2026: one model, and it is the live app). |
| `app_score.py` | The scorer: reads the app's replay logs and the labels, and nothing else (Uzayr, 30 September 2026). |
| `app_teaching.py` | The teaching pack from the live app (Uzayr, 30 September 2026, part E): B2, P5, passes 2 and 10. |
| `decoder.py` | The shipped semi-bounded committed decision, live. |
| `display.py` | The shipped display, live: the dot, the lock at press + 2.0 s, the one switch, the end text. |
| `final_model.py` | The FINAL tracker on the live path (29 September 2026; QUEUE item 2, DEVLOG_TRACKING section VERIFY). |
| `gates.py` | The live system's equality gates, run on replayed Room A recordings. Evidence, not assertion. |
| `identify.py` | Identification mode, live: who is walking, pass by pass, with chance and pace shown beside it. |
| `identify_engine.py` | Identification mode, live: the one-press engine (`pipeline/identify/engine.py`) and nothing else. |
| `identify_recorded.py` | Identification, the rig run: a recorded session streamed into the live app through the rig's own interface. |
| `model_sets.py` | The app's model sets, each a manifest of files with their SHA-256 (rule/APP_PREREG.md section 2). |
| `pool.py` | The SHIPPED five-head pool, computed one window at a time. |
| `press_profile.py` | Where a start press's service time goes (Uzayr, 30 September 2026, item 4). |
| `realtime_engine.py` | Streaming inference: 2 s windows on the shared lattice, emitted as they complete. (was `realtime/engine.py`) |
| `realtime_replay.py` | Feed a capture file through the engine, for testing without hardware. (was `realtime/replay.py`) |
| `replay.py` | A recorded session as the live system would have received it: frames in arrival order, and presses. |
| `rig.py` | The rig: `capture_logger.run_capture`'s extra consumer, the key reader, and the screen. |
| `rig_run.py` | THE LIVE RIG RUN, as ONE command. Batch 2026-09-23e, item 7. (was `realtime/rig_run.py`) |
| `screen.py` | The live screen: one window, two modes. |
| `start_terms.py` | The shipped committed decision's start terms, A2 plus a_veto_1.0, computed for one pass at its press. |
| `stream.py` | The live window stream: packets in, the shipped tree's windows out, re-cut at every start press. |
| `stream_source.py` | The streamed rig run (Uzayr, 30 September 2026, item 5): a recorded session fed to the live app, in wall-clock time, through the SAME ingestion path the boar... |
| `timing.py` | Gate 6's timing model: the live clock, emulated from replayed service times. |
| `tracker_live.py` | ITEM B: REAL-TIME OPERATION. The frozen tracker, live, under RENDER_RULES V1 to V4. (was `realtime/tracker_live.py`) |
| `tracking.py` | Tracking mode: packets and presses in; windows, the committed decision and the drawn frames out. |
| `unconstrained.py` | The UNCONSTRAINED mode (rule/APP_PREREG.md section 6, hashed 09:26): no press at all. |

### `constrained/` (83 modules)

| module | what it does (its own docstring) |
|---|---|
| `_guard.py` | The isolation guard, in one place. Imports only the standard library, so it is safe to call BEFORE any pipeline module is imported, which is the whole point. |
| `artefacts.py` | Train the canonical model, SAVE ITS WEIGHTS, and run it over whole recordings. |
| `bout.py` | The bout decoder: one decision per walking bout, not per window. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 4. |
| `common.py` | The shared contract for the constrained batch. Every stage imports its standards from here. |
| `dataset.py` | The training and evaluation sets, built from the window cache directly. |
| `dc2_pipeline.py` | THE DC2 PIPELINE. One command, a room folder in, the full cross-room report out. |
| `dc2_run.py` | DC2: THE ROOM B RUN, END TO END. Called by `dc2_pipeline`, one subcommand per step. |
| `dc2_scorerlock.py` | DC2, EXPLORATORY DISPLAY COMPARISON: the scorer lock at w = 0.25 against the display lock. |
| `dc2b.py` | dc2b. The DC2 pipeline's pass bookkeeping, corrected, around the FROZEN code (2026-09-24). |
| `dc2b_manifest.py` | dc2b_manifest. Writes data/room_B/calibration.json AT CAPTURE TIME, in the per-recording form dc2b reads. |
| `dc2b_pipeline.py` | dc2b_pipeline. THE DC2 COMMAND from 2026-09-24: the frozen `dc2_pipeline`, with the dc2b corrections. |
| `dc2b_run.py` | dc2b_run. One DC2 step process, run through the frozen `dc2_run` with the dc2b corrections. |
| `dc2b_scorerlock.py` | dc2b_scorerlock. The EXPLORATORY display comparison (PREREG_DC2 section 13), with the dc2b corrections. |
| `dc2c.py` | dc2c. The DC2 run, one Room B session at a time. POST HOC TOOLING NOTE, 2026-09-28. |
| `dc2c_pipeline.py` | dc2c_pipeline. THE DC2 COMMAND from 2026-09-28: dc2b_pipeline, run one Room B session at a time. |
| `dc2c_run.py` | dc2c_run. One DC2 step process with the dc2b and dc2c corrections. Command line exactly `dc2_run`'s. |
| `dc2c_scorerlock.py` | dc2c_scorerlock. The EXPLORATORY display comparison (PREREG_DC2 section 13), one Room B session at a time. |
| `decoder.py` | The decoder: twelve path chains, one null state, and the motion model along a path. |
| `decoder2.py` | The rebuilt decoder. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 2. |
| `emissions.py` | What the radio says about each state: log P(the person is at this point on this path). |
| `f1_arms.py` | PHASE 1: arms F and H, the two the overnight batch specified and never ran. |
| `f4_render.py` | F4: the demonstration re-rendered for the operator, 2026-09-24. A COPY of `f3_render.py`. |
| `f5_donor.py` | F5: THE DONOR SWAP. Is the committed line read from the radio, or from the walk's timing? |
| `features.py` | The model's input: the slowly varying part of the normalised shape, and the RSSI series. |
| `fh_common.py` | Shared bits for the F, H and live-render batch. Thin: it reuses the night batch's machinery. |
| `fh_ensprep.py` | Arm F's preparation: run the FROZEN 1 s heads over the 0.5 s window set. |
| `fusion.py` | HOW THE THREE LINK POSTERIORS OF EACH HEAD ARE FUSED. One definition, used by every reader. |
| `g2_multihead.py` | IMPROVEMENT 1, step two: multi-head ensembles of the frozen heads. |
| `g3_final.py` | The shipped pool, the re-taken verdict, the latency, and arm F's within-day rows. |
| `gate.py` | Walking gate: 0.3 to 2 Hz band energy used to LABEL windows. (was `branches/gate.py`) |
| `grid.py` | The cell grids the posterior head is trained over, and the mapping from a position to a cell. |
| `heads.py` | Task heads: identity, 2D position, and 25-way cell. (was `models/heads.py`) |
| `lattice.py` | THE ONE LATTICE. Every tree the shipped system draws from or quotes, defined in one place. |
| `link_cnn.py` | Per-link CNN with weights shared across the three receiver links. (was `models/link_cnn.py`) |
| `live2.py` | The rebuilt decoder as a stream: one window in, a committed state and a provisional state out. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 3. |
| `metrics.py` | THE CORRECTED MEASUREMENT. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, the block headed "THE CORRECTED MEASUREMENT", and stage 1.2. Every number quo... |
| `n2_arms.py` | PHASE 2: the single-lever arms, every one gated by the substitution test before its line counts. |
| `nets.py` | The encoder and the two heads, built from ``pipeline.models`` alone. |
| `night_arms.py` | The parameterised semi-bounded decoder every arm of the overnight batch runs through. |
| `night_common.py` | Shared machinery for the overnight semi-bounded batch, 2026-09-19. |
| `nodes.py` | THE TRACKING NODES, BY NAME AND BY BOARD. Batch 2026-09-23e, item 6: the fifth receiver. |
| `p1_runup.py` | ITEM 1: verify the operator's run-up account, and map where the run-up physically lies. |
| `paths.py` | The twelve taped lines, their arc-length state spaces, and the families they fall into. |
| `pd_arch.py` | pd_arch: D4 of the tracking attack (BRIEF_tracking_attack_2026-09-28), the architecture options. |
| `pd_cells.py` | pd_cells: items 3 and 4 of the DC2 results batch. EXPLORATORY, POST HOC to the Room B data. |
| `pd_clean.py` | pd_clean: the start-of-walk reader leak and its fix (29 September 2026; DEVLOG_TRACKING, VERIFY). |
| `pd_decode.py` | pd_decode: D3 of the tracking attack (BRIEF_tracking_attack_2026-09-28): decoder and decision variants on a finished cell's networks, with no retraining. Con... |
| `pd_disp_prov.py` | pd_disp_prov: Part D, the display's provenance, run exactly as rule/DISPLAY_PREREG.md (hashed 09:15, ad7eeb5a...). |
| `pd_dispend.py` | pd_dispend: the display head (DISP_END) for the FINAL model's renders (29 September 2026, QUEUE item 3). |
| `pd_dispend_zs.py` | pd_dispend_zs: the ZERO-SHOT model's display head (DISP_END on A1+A2 only), for the app (30 September 2026). |
| `pd_dt.py` | pd_dt: item 2 of Uzayr's message of 29 September: the 1 s time-step units inside the 0.5 s decoder, DISCLOSED on the development rotations for the 15:39 mode... |
| `pd_final.py` | pd_final: the test-session tables for the attack's MIDPOINT CHECK and FINAL (BRIEF_tracking_attack_2026-09-28). |
| `pd_latency.py` | pd_latency: per-window compute of a cell's five heads, for FINAL's latency section. |
| `pd_provenance.py` | pd_provenance: what every component of a decode was fitted on, and a check that FAILS LOUDLY on a forbidden session (29 September 2026; Uzayr's instruction 4... |
| `pd_render.py` | pd_render: the demonstration videos of the FINAL tracker on A3 and B2 (29 September 2026, QUEUE item 3). |
| `pd_report.py` | pd_report: per-pass rows, accuracy and paired intervals for the DC2 results batch (items 2 to 5). |
| `pd_repro.py` | pd_repro: the corrected FINAL reproduced from its hashes (29 September 2026; QUEUE item 1b). |
| `pd_repro_trace.py` | pd_repro_trace: rebuild a test decode from hashed files, with the hash list taken from FILE TRACES (29 to 30 September 2026; Uzayr's items A2 and A3). |
| `pd_rule.py` | pd_rule: the attack brief's choice rule on the three development rotations (BRIEF_tracking_attack_2026-09-28). |
| `pd_subst.py` | pd_subst: the substitution test and the shuffled-radio control on the final model (VERIFY 1c). |
| `pd_train.py` | pd_train: the training variants of the tracking attack (reports/tracking/briefs/2026-09-28_tracking-attack.md, D2). |
| `pd_v2.py` | pd_v2: the V2 development round (runs/dc2_results/rule/V2_PREREG.md, SHA-256 9bb52b68..., hashed 29 September 2026 22:49 before anything here was trained or ... |
| `q1_diag.py` | PART 1, D1 to D4: diagnostics only. No model changes, nothing trained, nothing shipped. |
| `q3_startclf.py` | A3, as a STANDALONE start-reading test. The bar was fixed before this was written. |
| `q4_arms.py` | PART 2: A1 and A2, each singly then combined, against the shipped decoder. |
| `r1_oldcensus.py` | R1: the BEFORE numbers. What the old display did, measured with the new instrument. |
| `rb10_bounded_demo.py` | STAGE 10 of the decoder rebuild: the BOUNDARIES-GIVEN tracking demonstration. |
| `rb3_display.py` | STAGE 3 of the decoder rebuild: the display layer, provisional and committed. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 3, items 3.1 to 3.3. |
| `rb7_demo.py` | STAGE 7 of the decoder rebuild: the demonstration renders, in real time. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 7, items 7.1 to 7.4. |
| `rebuild_common.py` | Shared plumbing for the decoder rebuild batch of 2026-09-17. |
| `recordings.py` | Whole recordings, end to end, every window in time order. |
| `render_display.py` | The display model: what the red dot does, and the one rule it obeys on every frame. |
| `s2_display.py` | STEP 2: DISPLAY POSITION, TWO ARMS, HEAD TO HEAD. |
| `s2a_dispend.py` | STEP 2 ARM: DISP-END. A display-only head trained with the position label at the window END. |
| `sb2_structural.py` | PHASE 2: the four structural changes to the semi-bounded decoder, each behind its own flag. |
| `switching.py` | MID-WALK SWITCHING as a DISPLAY decision. Batch 2026-09-23e, item 1, operator decision. |
| `t0_oracle.py` | STEP 0 of the pre-press region work: THE ORACLE CEILING. Brief: reports/tracking/history/2026-09-21_prereg-prepress-region.md |
| `t1_region.py` | STEPS 1 TO 3: can the START REGION be read from the PRE-PRESS windows alone? Brief: reports/tracking/history/2026-09-21_prereg-prepress-region.md. Runs only because t0_oracle... |
| `t2_embed.py` | ARM B2, THE PRE-REGISTERED EMBEDDING ARM. Brief: reports/tracking/history/2026-09-21_prereg-prepress-region.md |
| `u1_adapt.py` | ARM (d): CAUSAL PER-SESSION ADAPTATION. The priority arm and the thesis angle. Brief: reports/tracking/history/2026-09-22_prereg-prepress-v2.md, written before this ran. |
| `u2_useit.py` | ARMS (a), (b), (c) and (e): use a WEAK reader in a way that cannot harm. Brief: reports/tracking/history/2026-09-22_prereg-prepress-v2.md, written before any of this ran. |
| `veto.py` | THE SHIPPED COMMITTED-DECISION VETO, `a_veto_1.0`. One definition, for the render and the headline. |
| `y4_pressalign.py` | ITEM 2 of batch 2026-09-23c: THE PRESS-ALIGNED WINDOW LATTICE. Pre-registration `reports/tracking/history/2026-09-23_prereg-pressalign.md`. |

### `identify/` (86 modules)

| module | what it does (its own docstring) |
|---|---|
| `capture_idboth.py` | capture_idboth. The DC2 identification capture from 2026-09-24: line A in BOTH directions. |
| `capture_idpath.py` | capture_idpath. The DC2 identification capture wrapper, per-person slot design (2026-09-23e). |
| `common.py` | Shared pieces for the identification branch. Brief: reports/overnight_identification_prompt_2026-09-18.md. |
| `conditioning.py` | C0 to C7: the identification conditioning chain. Switchable per stage, for R1 and R2. |
| `engine.py` | engine. The one-press identification engine (`reports/identification/briefs/2026-09-30_engine.md`; every parameter is fixed in `runs/identify/engine/PLAN.md`, section 2).... |
| `features.py` | Per-PASS gait and geometry features. Brief phase D1. |
| `id14_crossday.py` | id14. Cross-day identification on all nine pairings, with the R6 speed diagnostics. |
| `id15_corridor.py` | id15. The corridor pilot and the DC2 power analysis. The geometry tool is id15_factor_map. |
| `id15_factor_map.py` | Projected bistatic factor map. Chooses the DC2 corridor on the morning, from geometry alone. |
| `id19_bank.py` | id19_bank. The IDMAX signal bank: every pass, three links, on ONE common 150 Hz grid. |
| `id19_featbank.py` | id19_featbank. Every section 8 B feature for every pass, per (segmentation, conditioning). |
| `id25_learned.py` | id25_learned. Item 8: the learned models of section 8 group D, nested, five seeds each. |
| `id28_dc2_score.py` | id28_dc2_score. The DC2 identification scorer: pre-registered, run once. |
| `id29_dc2_score.py` | id29_dc2_score. The DC2 identification scorer for the per-person slot design (2026-09-23e). |
| `id3_embeddings.py` | PHASE E: line-conditioned embeddings. Brief phases E1 to E4. |
| `id_dc2_explore.py` | id_dc2_explore. DC2 identification, EXPLORATORY: the fixed menu of brief 2026-09-28, phase 4. |
| `id_heads.py` | Fixed heads, cluster bootstrap and the permutation null. Shared by id11 to id18. |
| `idboth_view.py` | idboth_view. The pre-registered identification data, cut out of the both-directions capture, for the FROZEN scorers. |
| `ide_bank.py` | ide_bank. The engine's training banks, built by the engine's own extraction (`runs/identify/engine/PLAN.md`, sections 2.2 and 3), and the identity-blind cloc... |
| `ide_cadence.py` | ide_cadence. The engine brief's stage 4 (`runs/identify/engine/PLAN.md`, section 6): for the natural identification walks where the energy envelope shows a c... |
| `ide_checks.py` | ide_checks. The engine's identity-blind checks (`runs/identify/engine/PLAN.md`, sections 2.2, 2.4 and 2.5), from the engine bank's own extraction records (`i... |
| `ide_eval.py` | ide_eval. The engine's figures (`runs/identify/engine/PLAN.md`, section 4), from the harness's replays only (`ide_replay`). No training. Development evaluati... |
| `ide_gs.py` | ide_gs. The engine brief's stage 1 (`runs/identify/engine/PLAN.md`, section 1): the GS confirmation on the 600 tracking passes, leave one session out, CAL-ca... |
| `ide_replay.py` | ide_replay. The evaluation harness (`runs/identify/engine/PLAN.md`, section 4): a recorded session replayed through `engine.Engine`, in session order, one st... |
| `ide_train.py` | ide_train. The engine's models (`runs/identify/engine/PLAN.md`, section 3), trained on the engine's own bank by the audit's unchanged trainer (`idz_core.trai... |
| `idgp_cadence.py` | idgp_cadence. IDGP items 2 and 3: S_csi validation, cadence reliability, the geometry sanity check. |
| `idgp_cnn.py` | idgp_cnn. IDGP item 4: the 2D CNN Doppler-spectrogram model, retrained per training set. |
| `idgp_contract.py` | IDGP contract. The ONLY object an IDGP identification feature may receive (brief 2026-09-23f). |
| `idgp_dc2_score.py` | idgp_dc2_score. The DC2 scorer for P1-GP, addendum C (brief 2026-09-23f section 7). |
| `idgp_eval.py` | idgp_eval. IDGP item 5: the arms of brief 2026-09-23f section 5, nested, in every scope of section 6. |
| `idgp_signal.py` | IDGP signal layer: every per-pass quantity of brief 2026-09-23f sections 2 to 4, from a ContractPass. |
| `idmax_common.py` | Shared pieces for the 2026-09-23b gait identification maximisation run (IDMAX, stages id19 on). |
| `idmax_eval.py` | IDMAX evaluation engine: nested selection, sealed test labels, and every scope of section 5. |
| `idmax_features.py` | IDMAX feature layer: every gait feature of section 8 B, computed from the id19 signal bank. |
| `idrelabel.py` | idrelabel. The pre-scoring press relabel for DC2 identification (addendum E), as METADATA. |
| `idsec_dc2_score.py` | idsec_dc2_score. The two SECONDARY DC2 identification rows, P1-REV and P7, scored once. |
| `idsec_view.py` | idsec_view. The data of the two SECONDARY rows, P1-REV and P7, cut out of the both-directions capture. |
| `idv2_core.py` | idv2_core. DC2 identification v2 (brief 2026-09-28b): the building blocks. EXPLORATORY, registered before its first run in `reports/REGISTER_ID_DC2_V2_2026-0... |
| `idv2_run.py` | idv2_run. DC2 identification v2 (brief 2026-09-28b): EXPLORATORY, registered before its first run. |
| `idw_core.py` | idw_core. The identification-walks brief (`reports/identification/briefs/2026-09-29_walks.md`): the final ensemble of `reports/identification/2026-09-29_development-batch-2.md`, split into TRA... |
| `idw_eval.py` | idw_eval. The identification-walks brief: stages A (training data, calibration check), B (direction) and C (deployment measures), from the saved per-pass log... |
| `idw_run.py` | idw_run. The identification-walks brief: train one training set for one fold (once, saved), then score the test day's identification passes under the three c... |
| `idx_all.py` | idx_all. Identification development (the operator's direction of 2026-09-28): every selector component's log-probabilities for one held-out session, saved, s... |
| `idx_all_eval.py` | idx_all_eval. Identification development (the operator's direction of 2026-09-28): selection rules and ensembles compared on the saved component log-probabil... |
| `idx_bank.py` | idx_bank. Identification development (the operator's direction of 2026-09-28): one pass bank over the five sessions A1, A2, A3 (Room A sessions 01 to 03) and... |
| `idx_dev.py` | idx_dev. Identification development levers (the operator's direction of 2026-09-28), on the pass bank. |
| `idx_live.py` | idx_live. Identification development (the operator's direction of 2026-09-28): the chosen model run causally, pass by pass, on a held-out session, with measu... |
| `idx_loso.py` | idx_loso. Identification development (the operator's direction of 2026-09-28): leave one session out over A1, A2, A3, B1 and B2 on the pass bank (`idx_bank`). |
| `idx_sel.py` | idx_sel. Identification batch 2 (the operator's direction of 2026-09-28): the model chosen by inner leave-one-session-out, never by the test session. |
| `idx_train.py` | idx_train. Identification development (the operator's direction of 2026-09-28): the CNN trainer with extra augmentation for placement change. `idv2_core` is ... |
| `idz_audit.py` | idz_audit. Identification audit (`reports/identification/briefs/2026-09-29_audit.md`), stage 1: capture and packet audit of every recording and receiver in the bank (`run... |
| `idz_bank.py` | idz_bank. Identification audit (`runs/identify/audit/PLAN.md`): bank builds for the bug fixes and the candidates. Never writes to the dev bank; every bank go... |
| `idz_cadence.py` | idz_cadence. Identification audit, stage 5 (`runs/identify/audit/PLAN.md` section 5): is stride or step rhythm visible, on signals that can show it, in the n... |
| `idz_core.py` | idz_core. Identification audit (`runs/identify/audit/PLAN.md`): the final ensemble's train-and-save and apply-with-calibration (as `idw_core`), made configur... |
| `idz_run.py` | idz_run. Identification audit: the stage controller (`runs/identify/audit/PLAN.md`). Each stage reads the current best configuration from `runs/identify/audi... |
| `idz_synth.py` | idz_synth. Identification audit, stage 2 (`runs/identify/audit/PLAN.md` section 2): a synthetic walker on line A, written in the capture format and run throu... |
| `ils_cnn.py` | ils_cnn. The lever screen's CNN harness (PLAN note 2026-10-01 17:18, anchor A-C): the three CNN components recomputed from the saved `_x` models in replay or... |
| `ils_common.py` | ils_common. The identification lever screen (`reports/identification/briefs/2026-10-01_lever-screen.md`; every rule fixed in `runs/identify/engine/PLAN.md`, the note of 2... |
| `ils_extract.py` | ils_extract. The lever screen's Tier 0.2 and 0.5 (PLAN note 2026-10-01 17:18): the identification walks re-extracted with the engine's own Extractor (as `ixt... |
| `ils_feat.py` | ils_feat. The lever screen's feature side (PLAN note 2026-10-01 17:18): the five feature components retrained on a lever's inputs with `idz_core.train`'s fea... |
| `ils_screen.py` | ils_screen. The identification lever screen's driver (`reports/identification/briefs/2026-10-01_lever-screen.md`; every rule in `runs/identify/engine/PLAN.md`, the note o... |
| `ixa_a4.py` | ixa_a4. The extras brief's candidate A4 (`runs/identify/engine/PLAN.md`, the extras note): the lean correction learned from the training days only. For each ... |
| `ixa_data.py` | ixa_data. The extras brief's candidates A1 to A3 (`runs/identify/engine/PLAN.md`, the extras note): the identity-blind ingredients, from one pass over every ... |
| `ixa_inner.py` | ixa_inner. The extras brief's candidate A4 (`runs/identify/engine/PLAN.md`, the extras note): the inner leave-one-session-out loop inside each outer fold, to... |
| `ixa_measures.py` | ixa_measures. The extras brief's measures on the FINAL engine (`runs/identify/engine/PLAN.md`, the extras note): 2.4 CAL-none (adaptation off), 3 S_wifi (the... |
| `ixa_run.py` | ixa_run. The extras brief's section 2, stages E0 (anchor) and A1 to A3, in the PLAN's order, each against the current best configuration (`runs/identify/fina... |
| `ixa_score.py` | ixa_score. The extras brief's section 2 scoring (`runs/identify/engine/PLAN.md`, the extras note, E0): the five feature components retrained on a candidate's... |
| `ixa_speed.py` | ixa_speed. The extras brief's A1 (precise Wi-Fi speed) and A2 (speed profile), exactly as the PLAN's extras note defines them, from `ixa_data`'s identity-bli... |
| `ixt_ablate.py` | ixt_ablate. The teaching-pack brief's conditioning ablation (`runs/identify/engine/PLAN.md`, the teaching note, C3). Information only; never adopted; the eng... |
| `ixt_cadfix.py` | ixt_cadfix. The teaching-pack addendum's AC1 found the cadence resolver biased on simulated truth (fast walks walking away read 0.73 to 0.91 of the true step... |
| `ixt_cadimpact.py` | ixt_cadimpact. Information for Uzayr's decision on the cadence bug (`ixt_cadfix`): what the candidate fix would do to the engine's figures, measured WITHOUT ... |
| `ixt_extra.py` | ixt_extra. The teaching-pack addendum's AC2 (same day, confounded by recording) and AC3 (training without the slow and fast identification walks), as `runs/i... |
| `ixt_pack.py` | ixt_pack. The identification teaching pack (`reports/identification/briefs/2026-10-01_teaching.md`, sections 2.2 and 2.3): the two worked walks opened up, the model, the ... |
| `ixt_plots.py` | ixt_plots. Sanity plots made FROM the teaching pack itself (`reports/identification/teaching/check_png/`), so the page writer can check its own figures against them. Nothin... |
| `ixt_readme.py` | ixt_readme. The teaching pack's field guide: every key path of the built pack with its type or shape, and its meaning and units from the descriptions below (... |
| `ixt_rebank.py` | ixt_rebank. Engine v2 (the cadence bug fix, `runs/identify/engine/PLAN.md` note of 2026-10-01): the v2 banks and models. |
| `ixt_select.py` | ixt_select. The teaching-pack brief's rule for the two worked walks (`runs/identify/engine/PLAN.md`, the teaching note, section S), applied to the saved B2 r... |
| `ixt_shuffle.py` | ixt_shuffle. The teaching-pack brief's shuffled-label control (`runs/identify/engine/PLAN.md`, the teaching note, C2). |
| `ixt_subst.py` | ixt_subst. The teaching-pack brief's substitution test (`runs/identify/engine/PLAN.md`, the teaching note, C1): each B2 natural walk (host) is given another ... |
| `ixt_synth.py` | ixt_synth. The teaching-pack addendum's AC1 (`runs/identify/engine/PLAN.md`, the addendum note): the step-rate estimator on a grid of simulated walks, pushed... |
| `ixt_v2.py` | ixt_v2. Engine v2 (the cadence bug fix, `runs/identify/engine/PLAN.md` note of 2026-10-01): the one figure of the engine's final report that had no saved scr... |
| `ixt_verify.py` | ixt_verify. The teaching-pack brief's verification (`runs/identify/engine/PLAN.md`, the teaching note, section V): B2 streamed through the live app's rig pat... |
| `ixt_walk.py` | ixt_walk. One worked walk, opened up for the teaching pack (`reports/identification/briefs/2026-10-01_teaching.md` section 2.3 A): the engine's own extraction of the walk... |
| `raw_access.py` | The ONE place that knows how to get raw per-packet CSI for a pass. Everything else calls this. |
| `rehearsal_doppler_check.py` | rehearsal_doppler_check. A REHEARSAL DIAGNOSTIC: does the moved RX2 see Doppler above its own floor? |
| `yield_governor.py` | The yield governor for the 2026-09-23b identification maximisation run (IDMAX). |

### `io/` (11 modules)

| module | what it does (its own docstring) |
|---|---|
| `anchors.py` | Walking-path and grid-cell definitions for ground-truth capture. |
| `capture_logger.py` | Streaming multi-node CSI capture: serial readers, rate monitor, writer. |
| `check_channel_filter.py` | Test whether ``channel_filter_en`` is degrading the across-subcarrier shape. |
| `check_gain_lock.py` | Test whether the receivers' AGC gain lock actually engaged. |
| `clean.py` | Cleaning steps shared by every branch: amplitude, resampling, baseline. (was `clean/common.py`) |
| `ground_truth.py` | Ground-truth anchor logging, in the same process as the CSI capture. |
| `identify_board.py` | Identify which esp-csi firmware is running on a serial port. |
| `inspect_capture.py` | Inspect a written capture and report whether it looks like real CSI. |
| `parse.py` | Parse raw ESP32 ``CSI_DATA`` serial lines into validated CSI records. |
| `rt_calibration.py` | Measure the operator's keypress latency for ground-truth anchor logging. |
| `windows.py` | Cut every recording into 2 s fusion windows with the metadata a result needs. (was `splits/windows.py`) |
