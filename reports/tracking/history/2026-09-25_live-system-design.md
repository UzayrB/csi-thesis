# The live system: identification mode, then tracking mode

Written 2026-09-25 for whoever builds it. A program that runs on the rig as a person walks, separate from
the renders (`f3_render`, `f4_render` replay recorded CSI offline). It changes no model: it runs the
frozen DC2 configuration (`reports/MODEL_FREEZE_DC2.md`, freeze 23h) live, and adds an identification
mode in front. Build it in new modules, for example `pipeline/live/`. Every file under
`pipeline/constrained/`, `pipeline/io/` and the identification scorers is pinned: import them, never
edit them.

## 0. What exists, and the gap

| piece | file | live today? |
|---|---|---|
| streaming windows | `pipeline/realtime/engine.py` `RealTimeEngine` | **yes**. Records pushed in (it never opens a port), 2 s windows at a 0.5 s stride on the absolute lattice, cleaned per window exactly as offline. `rephase_to_press(t_press, eps)` moves the lattice onto the press live. Contract: at most 0.5 s latency per window, at most 4 s between outputs. It needs the session's baseline and a presence threshold |
| semi-bounded decode, one head | `pipeline/realtime/tracker_live.py` `LiveTracker` | **yes, single head**. Fed one window at a time from a start press; keeps its own RSSI ring buffer, because the engine carries amplitude only and the heads take amplitude and RSSI; locks at the window that ends at press + 2.0 s. On replay its decisions equal the offline ones 20 of 20, given the same windows |
| boards, capture, a live packet line | `pipeline/realtime/rig_run.py` (`scripts/live_rig_run.sh`) | yes; **draws nothing** |
| the five-head pool, the start terms (A2 + veto), the display (lock, path, switching, end text), identification | offline only | **the gap** |

## 1. Architecture

```
capture_logger.run_capture(..., extra_consumers=[LiveSession])     # the hook GroundTruthSession uses
    └─ LiveSession.handle(record)  ->  RealTimeEngine.push(node, t_mono, amplitude)  +  RSSI ring buffer
                                        └─ each completed window  ->  the current MODE  ->  the screen
KeyReader (pipeline.io.ground_truth)  ->  press events, stamped on the same t_mono clock
```

- **Read the capture in process**, through `run_capture`'s `extra_consumers`, not by tailing files:
  `rig_run.py` tails files, which adds latency. Name the boards by MAC, as `rig_run.py` does
  (`pipeline/constrained/nodes.py`). Never name them by port order.
- **One clock.** Frames and key presses are both on `t_mono`. **CORRECTED 2026-09-25, during the build:
  do NOT subtract the reaction-time bias from a live press.** This line said the opposite. The sidecar's
  `t_start` and `anchor_times` are the RAW key times (`pipeline/io/ground_truth.py` appends `ev.t_mono`
  unchanged; the bias is subtracted only inside position interpolation), and the press-aligned lattice
  is phased on that raw `t_start`. Subtracting 51 ms live would put every live window 51 ms off the
  tree the heads were run on. `reports/LIVE_SYSTEM_2026-09-25.md` has the evidence.
- **Baselines.** A 60 s baseline (`session_baseline`) is taken with RX2 where the current mode needs it.
  Moving RX2 changes the static room, so taking a new baseline is part of switching mode.

## 2. Identification mode (first)

**Geometry and walk.** RX2 is at its identification spot, (2.0, -0.5), facing north (`capture_idpath.SPOTS`,
recorded in `runs/identify/dc2/rx2_spot.json`). The walker goes along line A, away from the TX (`A_fwd`).
The operator presses at 0 m and at 5 m; the live mode needs only those two presses. A pass must last
1.5 to 12 s.

**Features and model.** These are the pre-registered PRIMARY configuration, exactly as `id29_dc2_score`
builds it:

- features: `id19_featbank.pass_features(a, rssi)` on the segment from the start press to the end press;
- feature configuration: `idmax_eval.FConf("dc2e", "U_all_gait", "mean@b08_35", links, "pc1-3", "perline_z")`;
- head: a random forest (`n_estimators=300, max_features="sqrt", random_state=0`), with training-side
  median imputation and z-scoring.

To check that live extraction equals offline, run `id29_dc2_score.extract` on the same recording and
compare.

**Enrolment is a closed set.** The model identifies only people it was trained on: the six DC2
participants, from their day 1 natural passes, or anyone enrolled on the spot with at least 10 passes.
Add an enrol step for anyone else.

**Show it honestly.**

- Display the probability for every enrolled person, with chance (1 in 6, 16.7 %) marked.
- Optionally combine several walks: sum the log-probabilities over N passes (the MULTI-PASS row of
  addendum C).
- Show speed-only identification beside it: S0, which is 5.0 m divided by the time between the two
  presses. In Room A, speed alone scored 36.11 % on `A_fwd`, the same as the best gait arm. The
  pre-registered expectation is that a single pass will not separate from chance. A live
  identification that looks good may simply be reading pace, and the screen should let a viewer see that.

**Then switch mode:** RX2 goes home to (-0.5, 2.5), facing east; take a new 60 s baseline.

## 3. Tracking mode (the shipped system, live)

Reproduce the DC2 configuration exactly. Each row names the offline code to reuse.

| step | exactly | offline code |
|---|---|---|
| windows | the ONE lattice: at each start press, `engine.rephase_to_press(t_press, PRESS_EPS_S)` (2 µs) | `pipeline/constrained/lattice.py`, `y4_pressalign.py` |
| heads | five heads at equal weight: g25 on 0.5 s windows, three g25 1 s seeds (0, 1, 2), and the g100 region head, all inferred on the 0.5 s windows. Each head's three link posteriors are fused by their **mean**, then the five heads are averaged. For Room B use tag `s010203_to_sB` (`runs/artefacts_s0.5_pressalign_roomA3`, `runs/artefacts_s1.0_roomA3_{s0,s1,s2,g100}`) | `g3_final.shipped_pool_emissions` (offline, per recording: do the same per window), `t2_embed.load_heads`, `g100_emissions` for the 100-cell head's mapping |
| start term A2 | an LDA on pre-press features, trained on the training sessions and applied to this pass at the press, weight 0.5 | `q4_arms.start_terms`, `q3_startclf.collect` |
| veto | where the region reader puts a start region below 0.01, that region is pushed down by 3.0 nats (weight 1.0). The reader's features come from AdaBN statistics taken ONLY from the idle windows before the session's first press, so a live session starts with a short still period | `u2_useit.fit_reader`, `term_veto`, `u1_adapt.session_rows` (mode `"adabn"`, `CALIB_MODE = "idle"`), `veto.py` |
| decoder | the semi-bounded decode: from the press, a forward pass keeps all 12 chains alive; the exit is the first step whose decode ends in the null state (causal, about 1 s of evidence); the interval is then rescored over the 12 chains to give the committed line | `night_arms.night_track` → `sb2_structural.track2` |
| constants | configuration A: gate 0.431, null -7.50. Configuration B: both re-anchored on that day's calibration walks, which must be recorded first | `dc2_pipeline.re_anchored_constants`; `dc2_run.do_decode` for `s_B` and the relative null |
| display | 2.0 s behind real time. **Lock:** read at the window that ends at press + 2.0 s, from the display decode (`sd_scale` 4.5, 0.8 m per window, A2 0.5, soft entry, 1.0 m entry window). **Path after the lock:** the restricted along-line decode, with the DISP_END head flattened by 0.50. **Switching:** rule 1a arm C. **End text:** the committed decision | `s2_display.py`, `switching.py`, composed as in `f3_render` / `f4_render`, but per window; `reports/RENDER_RULES.md` |

**Causality:** a frame may use only windows that have ended by the frame's time.
`tests/test_display_is_causal.py` states the rule; the live runner must pass the same test.

## 4. A live session, in order

1. **Setup.** Find the boards by MAC; run preflight; take a 60 s baseline with RX2 at home. For
   configuration B, record the calibration walk. Stand still for about 30 s so the veto reader has idle
   windows for its statistics.
2. **Identification.** Move RX2 to the spot; take a 60 s baseline; the walker goes along `A_fwd`, and
   the operator presses at 0 m and 5 m. The screen shows the enrolled people's probabilities, and the
   speed-only row beside them. Repeat for N passes.
3. **Switch.** Move RX2 home; take a 60 s baseline; reinitialise the engine and the tracker.
4. **Tracking.** For each walk, the operator presses at the start and at the end. The dot runs 2.0 s behind the
   walker; the line locks at press + 2.0 s; the end text appears once the decoder has declared the end.
   **CORRECTED 2026-09-25, during the build:** this said one press, at the start. The decoder is still
   told only the start press, but the press-aligned lattice places each segment boundary halfway
   between one walk's END press and the next START press, and `f3_render` draws a walk until its end
   press + 2.0 s. So the live system takes the end press too. See `reports/LIVE_SYSTEM_2026-09-25.md`.

## 5. Build order, each step proved before the next

1. **The pool, live.** Extend `LiveTracker` to the five heads. On a replayed recording, every window's
   pooled emission must equal `shipped_pool_emissions` to floating-point tolerance.
2. **The start terms, live.** The A2 and veto terms for each pass must equal the offline ones.
3. **Decode and commit.** On the replayed stand-in, the committed line must equal the shipped decision
   on every pass. That is the same check `dc2b_pipeline --stand-in` makes, 72 of 72.
4. **The display.** Frame by frame, the dot, the lock and the switch must equal `f3_render`'s on the
   same recording. The causality test must pass.
5. **Identification.** On a DC2 recording, the features must equal `id29_dc2_score.extract`, and the
   prediction must equal the offline model's.
6. **Timing.** On the laptop, compute each window's time with all five heads (about five times the
   single head's). It must stay under 0.5 s; the single-head decode measured 49.8 ms per window. The
   output gap must stay at or under 4 s.
7. **The screen.** A simple window: the grid, the dot, the line, the end text, and the identification
   probabilities. Then, and only then, run it on the rig with a person.

"Nearly equal" is a failure. Two things always differ in live data (the lattice's alignment and packet
loss), so all equality is proved on replay first.
