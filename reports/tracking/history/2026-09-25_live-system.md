# The live system, built and gated on replay

Written 2026-09-25 11:55 SAST for Uzayr. The design is `reports/LIVE_SYSTEM_DESIGN_2026-09-25.md`, and this report
covers its section 5, step by step. The code is `pipeline/live/`, and nothing frozen was edited: the live
modules import `pipeline/constrained/`, `pipeline/identify/` and `pipeline/io/` and change nothing in
them. Every gate below is an EXACT equality on replayed recordings, apart from the two float tolerances
stated at gates 1 and 2. The evidence files are in `runs/live/`.

## The answer

The shipped tracking system runs live on replay and gives the offline answers.

- **From raw packets and key presses to the committed decision:** 120 of 120 passes equal the shipped
  decision.
- **Display:** 120 of 120 walks and 5055 of 5055 frames equal `f3_render`'s drawn frames.
- **Stand-in:** the Room A stand-in (session 03, heads `s0102_to_s03`), all six recordings.

Identification gives `id29_dc2_score`'s features and predictions exactly, on id29's synthetic DC2
recordings. No DC2 identification recording exists yet.

It has not run on the boards. That needs you, the boards, and your go-ahead to open the serial ports.

Four things in the design or the build prompt were wrong, and the code follows the evidence instead.
They are listed first.

## 1. Four corrections to the spec

1. **Do not subtract the reaction-time bias from a live press.** The build prompt's trap list and the
   design's section 1 both said to subtract it.
   - The sidecar's `t_start` and `anchor_times` are the RAW key times: `pipeline/io/ground_truth.py:1526`
     appends `ev.t_mono` unchanged, and the bias is subtracted only inside `interpolate_position`.
   - The press-aligned tree is phased on that raw `t_start`, so subtracting 51 ms live would put every
     window 51 ms off the tree the heads were run on.
   - The mutation check below confirms it: subtracting the bias turns the lattice test red.
   - The design is corrected in place, with a dated note.
2. **The live system needs the END press as well.** The decoder is still told only the start press, but:
   - the tree places each segment boundary halfway between one walk's end press and the next walk's
     start press;
   - `f3_render` draws a walk until its end press + 2.0 s.

   The design said one press per walk. It is corrected.
3. **The pinned engine's cleaning is not the tree's.** `RealTimeEngine` cleans each window from a slice
   0.05 s wider than the window, which gives the Hampel filter fewer than its 10 packets at the edges.
   - Result: 94 of 94 probe windows differ from the tree, by up to 0.93 against a typical value of 0.11.
   - `LiveStream` cleans with 13 packets of margin and resamples on the whole file's own grid instants.
   - Resampling on a slice's own grid moved values by one float16 step, in 311 of 1128 windows.
4. **The last pass of five recordings is decided only because the recording ends.** There, the exit
   search times out on the file's last window. The live equivalent is the operator stopping the
   recording (`LiveDecoder.close`), and gate 3 counts those 5 passes separately.

## 2. The gates, in order

| gate | what is compared | result | evidence |
|---|---|---|---|
| 1 pool | each window's five-head pooled emission against `g3_final.shipped_pool_emissions` | **10197 of 10197** windows within 1e-4 (largest difference 7.1e-6), argmax 10197 of 10197, gate energy identical | `gate1.json` |
| 2 start terms | A2 + `a_veto_1.0` per pass against `dc2_run.do_decode`'s terms; AdaBN on each recording's idle windows before its first press | **120 of 120** within 1e-4 nats (largest 3.2e-6); the same lines vetoed on every pass | `gate2.json` |
| 3 decision | the committed line against `d4_headline` `rows_veto.json`, and the exit window against the offline decode | **120 of 120** (5 decided when the recording stops); decided a median 6.0 s after the press (3.5 to 9.0) | `gate3.json` |
| 3 live | as 3, with the live pool and the live start terms in place of the offline ones | **120 of 120** | `gate3live.json` |
| stream | each window the decision can read, cut live from packets and presses, against the tree: the float16 array, the RSSI series, the epoch start | **6982 of 6982** windows bit for bit; no live window in the read range missing from the tree | `gatestream.json` |
| 4 display | every frame, computed from the windows that had ended by its time, against `f3_render`'s saved `rpost`; the lock; the switches; the anchor; `f3`'s recorded constants | **120 of 120** walks, **5055 of 5055** frames, the 5 switches equal, constants equal | `gate4.json` |
| 5 identification | features, single-link rows, spectrogram and row per pass against `id29_dc2_score.extract`; each day-2 pass predicted ON ITS OWN against the offline PRIMARY batch and S0 | **90 of 90** passes equal; PRIMARY **18 of 18** with probabilities, S0 **18 of 18** | `gate5.json` |
| end to end | raw packets and presses through the whole session (stream, pool, display head, terms, decoder, display) | decisions **120 of 120**, displays **120 of 120**, frames **5055 of 5055** | `gatee2e.json` |
| end to end, causal clock | the same, with the device clock anchored causally as the rig must | decisions **120 of 120**, displays **119 of 120** (a measurement, not a gate) | `gatee2e-causal.json` |

Notes on the gates:

- **Gate 1's tolerance.** Offline ran each head over 256 windows at once, and live runs one window, so
  float32 summation order differs. 1e-4 is the stated tolerance; the argmax and every decision
  downstream are equal.
- **The stream gate's read range.** A press re-cuts the windows it re-assigns back to 6 s before the
  press, and the first press re-cuts back to the recording's start (for AdaBN). In a gap between walks
  longer than 12 s, the windows before that stay on the older phase. Nothing reads them (the decision
  and display read at most 5 s before a press; see below). They are counted apart: 3215 windows, most of
  them in the one break of 7.5 to 10 minutes each recording has between its two blocks of walks.
- **Why the decoder's look-back is 8 windows.** The decode is exact with 6 windows kept before a walk's
  first window (gates 3 and 4 both 120 of 120), and the frozen decoder refuses at 2. So the decode reads
  about 3 s before its first window. 8 keeps a margin, and the re-cut covers it.
- **Gate 4 is also the causality test.** A frame computed from the windows ended by its time that
  equalled `f3_render`'s every time means `f3_render` read nothing later. The substitution test in
  `tests/test_live_decision_display.py` shows it the other way round: replacing every window after a cut
  with another participant's changes no earlier frame and no earlier decision, and does change later
  ones.

## 3. Timing (gate 6)

Measured on this laptop with nothing else running (PA5, PA3, `timing_alone_pa5_pa3.json`),
all five heads plus the display head:

| | median | p99 | max | contract |
|---|---|---|---|---|
| per window, cut from packets | 0.057 s | 0.061 s | 0.077 s | |
| per window, heads + terms + decoder + display | 0.060 s | 0.135 s | 0.189 s | |
| per window, both | | 0.197 s | | under 0.5 s: **met** |
| per start press (re-cut, rows, re-sync) | 0.536 s | | 1.689 s | |

The live clock is emulated by a queue model: one worker serves each window when its last packet
arrives, and each press when it is pressed, for the service time measured here.

- The largest gap between outputs is **1.921 s**, against a contract of at most 4 s:
  **met**.
- Latency after a window ends: p99 0.597 s, max 1.802 s.
- **38 of 3274 windows are ready more than 0.5 s after they end.**
- Those are the windows queued behind a press. A press re-cuts and recomputes about 8 windows (the
  first press re-cuts the whole still period, for AdaBN), and its cost is mostly the heads on the Apple
  GPU.
- Measured and rejected: batching the re-cut windows was slower on the GPU (45 ms per head and link for
  twelve windows, against 2.4 ms for one).
- The gate timings inside `gatee2e.json` were measured with four jobs sharing the machine, and are
  slower for that reason.

**What a viewer sees.**

- The dot is drawn 2.0 s behind real time, as the render rules require, and a window's outputs are
  ready well inside that except just after a press.
- The committed decision is reached a median 6.0 s after the start press.
- `f3_render` shows the end text at the end press + 2.0 s. Live, the text waits for the decision, which
  came later on 12 of 120 walks, by at most 1.614 s.
- Identification waits 21 s after the end press for `_link`'s clock map to settle, which equality with
  id29 requires: the bin after the pass must be complete. Extraction then takes 0.52 s per pass and
  prediction 0.26 s.

## 4. The screen (gate 7) and the rig

- **Screen:** `pipeline/live/screen.py`. Tracking shows:
  - the room, the lines, and the receivers (RX2 at home);
  - the red dot, and the locked or switched line;
  - the green marker, where the walker was 2.0 s ago, in `f3_render`'s style;
  - the 2.0 s delay caption;
  - on the right, after the walk, the banner naming the shipped committed decision, the drawn line and
    the true line.

  The banner is green when the committed line is the true one, red when it is not, grey with no ground
  truth, and "still deciding" while the decoder has not declared the walk's end.

  The green marker and the banner's colour come from the recording's sidecar (its anchor presses at
  known tape positions), for the screen only. Nothing that decides or draws the dot reads it. On the rig
  there is no ground truth unless one is supplied, so the rig shows no green marker and a grey banner.
- **Identification screen:** every enrolled person's probability, chance at 1 in 6, S0 beside it, the
  pass's speed, and the product over passes (RX2 at the spot).
- **Replay snapshots:** `runs/live/screen/`, at the lock and after the end text.
- **Rig:** `pipeline/live/rig.py` reads records in process through `run_capture`'s `extra_consumers`,
  names boards by MAC, anchors each device clock causally, and maps SPACE to the start and end presses
  at the raw key time.
- **Rig tests:** `tests/test_live_rig.py` runs it with scripted records and keys and no serial port.
- **Not run on the hardware.** The boards are unplugged, and the rules say to ask you before touching
  the serial ports.

## 5. What is still not live

- **The rig run on the boards.** Command: `python3 -m pipeline.live rig --mode tracking --baseline <dir>`.
  It needs a 60 s baseline taken first with RX2 at home.
- **Room B.** `rig --room B` refuses, because three things are missing:
  - a DISP_END display head for `s010203_to_sB` (none is trained; the shipped display draws from it);
  - the Room B tree binding `dc2_run` builds;
  - configuration B's constants, re-anchored on that day's calibration walk.
- **The identification rig mode** needs an enrolment set (DC2 day 1 natural passes) and Room A's 23b
  rows, which fix the feature columns. It refuses until then; `replay-identify` runs it on synthetic
  data.
- **A walk without an end press** falls back to re-cutting the whole look-back, and that fallback is not
  measured.
- **The latency just after a press** is above 0.5 s for the few windows queued behind it (section 3).
- **Causal clock anchoring** is measured, not proved: it differs from the whole-file fit by a median of
  7 µs and at most 4.4 ms on RX1 of one recording.
  - Decisions: 120 of 120 equal.
  - Displays: 119 of 120 equal. The one differing walk, PA2's pass 2, keeps its locked line and
    17 of 32 of its frames.

## 6. Tests

`tests/test_live_stream.py`, `test_live_pool.py`, `test_live_start_terms.py`,
`test_live_decision_display.py`, `test_live_identify.py`, `test_live_rig.py`, `test_live_tracking.py`:
30 tests, sampled from the gates.

**Every guard and equality was broken on purpose** (`runs/live/mutations.json`). **21 of
22 mutations turned their test red.**

The one that stays green, number 15, is equivalent rather than missed. It lets the display see one
more window than the frame's time allows. But `f3_render`'s own composition chooses every window it
reads by time or by step index, so the extra window is never read, and no output can differ. When the
frame is drawn is covered by the queue model, not by this test.

One survived the first round: subtracting the bias from the press. Its test compared the lattice with
the stream's own stored press, so it could not see the change. The test now compares with the
sidecar's raw press, and the mutation turns it red.

| # | broken on purpose | test | red |
|---|---|---|---|
| 0 | stream: margin below the Hampel window | `test_every_window_the_decision_reads_equals_the_tree` | yes |
| 1 | stream: resample on the slice's own grid | `test_every_window_the_decision_reads_equals_the_tree` | yes |
| 2 | stream: reaction-time bias subtracted from the press | `test_the_first_walk_window_starts_one_second_before_each_raw_press` | yes |
| 3 | stream: no re-cut at a press | `test_a_press_re_cuts_the_windows_it_re_assigns_onto_its_phase` | yes |
| 4 | stream: close does not withdraw | `test_close_withdraws_windows_past_the_trees_end_limit` | yes |
| 5 | stream: backwards packet kept | `test_a_packet_behind_its_predecessor_is_dropped_and_counted` | yes |
| 6 | stream: RSSI slice starts one sample late | `test_rssi_is_the_whole_series_interpolation_even_with_tied_host_times` | yes |
| 7 | pool: links fused by the max rather than the mean | `test_each_window_pools_to_the_offline_emission` | yes |
| 8 | pool: the g100 head dropped | `test_the_pool_has_the_five_shipped_heads` | yes |
| 9 | display head: the pool's marginal instead of its own | `test_the_display_head_equals_its_offline_emission` | yes |
| 10 | start terms: the veto never fires | `test_every_pass_term_equals_the_offline_term` | yes |
| 11 | start terms: no AdaBN | `test_every_pass_term_equals_the_offline_term` | yes |
| 12 | decoder: decides before the exit window exists | `test_every_decision_equals_the_shipped_one` | yes |
| 13 | display: dot phase 0.0 rather than 0.50 | `test_every_frame_equals_f3_render` | yes |
| 14 | display: the speed cap not applied to the display decode | `test_every_frame_equals_f3_render` | yes |
| 15 | display: a frame drawn after its window is added (reads ahead) | `test_a_frame_never_reads_a_window_that_ended_after_it` | NO (equivalent: the frozen composition picks every window it reads by time or step index, so an extra later window in the list is never read; no output can show it) |
| 16 | identify: the clock map's 5th percentile changed | `test_every_pass_equals_id29_extract` | yes |
| 17 | identify: no wait for the clock map | `test_a_pass_waits_until_its_clock_map_is_final` | yes |
| 18 | identify: enrolled passes out of extract's order | `test_one_pass_on_its_own_equals_its_prediction_inside_the_batch` | yes |
| 19 | rig: bias subtracted from the key time | `test_space_alternates_start_and_end_presses_at_the_raw_key_time` | yes |
| 20 | rig: packets pushed on the host clock before the fit | `test_packets_are_timed_by_the_causal_fit_and_never_before_it` | yes |
| 21 | tracking: no re-sync after a press | `test_each_pass_is_drawn_as_f3_render_drew_it` | yes |

`make test`: 1106 passed, 18 skipped, 30 warnings in 568.26s (0:09:28), after the screen changes.

The first full-suite run failed ten of these tests, and every one of them passed on its own.

- **The cause.** The shipped tree's roots are module constants, fixed by whichever test first imports
  `pipeline.constrained`, and `set_half_roots` only sets environment defaults. Inside one pytest
  process my tests read the 1 s tree, and binding the roots from inside pytest has broken other tests
  before (`tests/test_lock_is_causal.py`).
- **The fix.** The checks that read the tree now run in a child process (`tests/_live_checks.py`), as
  this repository's other lattice tests do.
- **Confirmed.** All 22 mutations were rerun against the child-process tests, with the same result.
  The suite above is the run after that fix.

## 7. How to run it

    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live gates --gate e2e                  # the proofs
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay --stem participant_PA5_TEST_walk --screen
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay-identify --snapshots runs/live/screen
    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --mode tracking --baseline <dir>   # opens ports
