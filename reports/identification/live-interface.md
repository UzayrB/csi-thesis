# The identification engine's live output: one JSON line per decision (2026-09-30)

**For:** tracking, or any consumer of identification decisions. The writer is the one-press identification
mode, `pipeline/live/identify_engine.py`, which wraps `pipeline/identify/engine.py`
(`runs/identify/engine/PLAN.md`). Participants appear only as codes, P1 to P6.

## Where the lines are written

**One file per run**, appended one line per decision as each decision is made:
- **rig:** `runs/live/identify/rig_<YYYYmmdd_HHMMSS>.jsonl`;
- **replay:** `runs/live/identify/replay_<session>_<YYYYmmdd_HHMMSS>.jsonl`.

**Reading it live:** follow the file and parse each complete line. A line is written only after its decision
is final and is never rewritten.

## One line

```json
{"schema": "id_engine_decision_v1",
 "t_press_mono": 12345.678, "t_decision_mono": 12348.912, "t_written_host": 1790751421.5,
 "window_s": 3.0, "direction": "away", "path": "A_fwd", "direction_source": "detected",
 "top": "P3", "probability": 0.41, "runner_up": "P2", "runner_up_probability": 0.22,
 "displayed_confidence": {"P1": 0.05, "P2": 0.22, "P3": 0.41, "P4": 0.12, "P5": 0.1, "P6": 0.1},
 "ensemble_probability": {"P1": 0.0001, "P2": 0.02, "P3": 0.97, "P4": 0.004, "P5": 0.003, "P6": 0.002},
 "wifi_speed_m_s": 1.18, "latency_after_window_s": 0.21, "calibration_windows": 14,
 "closed_set": ["P1", "P2", "P3", "P4", "P5", "P6"], "model": "deploy_all5 (all five sessions)", "replay": false,
 "round_trip": null, "tally": {"k": 3, "top": "P3", "probability": 0.88}}
```

## The fields

**Times.** `t_*_mono` are on the host's `time.monotonic()` clock, the clock of the capture frames' `t_mono`
and of the space bar.

| field | meaning |
|---|---|
| `t_press_mono` | the operator's single press: the start of the walk |
| `t_decision_mono` | when the decision was made: the packet wait after the window plus the measured compute |
| `t_written_host` | the host wall clock when the line was written |
| `window_s` | the listening window after the press (3.0 s, fixed) |

**Direction.**

| field | meaning |
|---|---|
| `direction`, `path` | `away` / `A_fwd` (from the TX) or `towards` / `A_rev` (on line A); a tracking recording replayed with a known route gives its own path name |
| `direction_source` | `detected` (from RX2's 10 to 35 Hz energy slope), `key` (the `a` / `t` trigger keys) or `known route` (tracking replays) |

**Identity.**

| field | meaning |
|---|---|
| `top`, `runner_up` | the engine's answer and its second choice (the ensemble's argmax order) |
| `probability`, `runner_up_probability`, `displayed_confidence` | the displayed confidence: the geometric mean of the eight components, softmax(sum / 8); it never changes the decision |
| `ensemble_probability` | the ensemble's own normalised product of the eight; much sharper, and it is what decides |

**The walk and the model.**

| field | meaning |
|---|---|
| `wifi_speed_m_s` | the walking speed measured from Wi-Fi: torso Doppler x lambda / (2 F) on the best link; `null` when undefined |
| `latency_after_window_s` | from the window's end (t0 + 3 s) to the decision |
| `calibration_windows` | earlier walks this session the engine has adapted to, without labels (causal); the screen shows "adapting to this room: n walks seen". No walk is ever asked for: the engine decides from the first walk, on training statistics until enough walks have been seen |
| `closed_set` | only these six enrolled people can be named |
| `model` | which saved model decided; in a replay, the fold model that never saw the replayed day |
| `replay` | `true` for a replay of recorded data |

**Combined decisions.**

| field | meaning |
|---|---|
| `round_trip` | set when a towards walk's press comes within 15 s of an away walk's decision: `top` and `probability` of the two walks' summed log-probabilities |
| `tally` | set after the operator pressed `n` (new walker): the sum over that walker's `k` walks so far. It marks a change of walker only, never who the walker is |

## What the engine never does

- It never uses the end press, an operator label or the walk's duration.
- Press speed is not an input; it appears only as the S0 control in the thesis figures.
- It does not name anyone outside the six enrolled people.

## Schema v2 (from 30 September 2026, `id_engine_decision_v2`)

**Every v1 field is kept unchanged,** so a v1 reader keeps working. Added:

| field | meaning |
|---|---|
| `top_name`, `runner_up_name` | the participants' names beside the codes (names are allowed in every output from 30 September) |
| `truth_name` | recorded streams and replays only: who actually walked, taken from the recording. It is written after the decision exists and never enters the engine; on the rig it is absent |

**No warm-up.** The system works straight away: nobody is asked to walk to calibrate it. The unlabelled adaptation
to the room from walks that happen anyway (`calibration_windows`) stays as it was.

**Where the lines are written, v2:**
- the rig on the boards: `runs/live/identify/rig_<YYYYmmdd_HHMMSS>.jsonl`;
- a recorded stream (`python3 -m pipeline.live.identify_engine rig --source recorded --session B2`):
  `runs/live/identify/rig_recorded_<session>_<YYYYmmdd_HHMMSS>.jsonl`;
- a replay: as v1.

## Schema v3 (engine v5, from 10 October 2026, `id_engine_decision_v3`)

**Every v2 field is kept unchanged,** so a v2 reader keeps working. A v3 line comes from an engine v5 model (the
deployment model `deploy_all5_v5`, or a fold model `loso_<session>_v5`); a v4 model still writes v2.

**What changes in the meaning of v2 fields:**
- `window_s` stays 4.0, but each press now has **three windows**, at 0, 0.15 and 0.30 s after it. The decision comes
  after the 0.30 s window, whose window ends at t0 + 4.30 s (t0 + 5.30 s at the latest).
- `latency_after_window_s` is measured from t0 + 4.0 s to the decision.
- `displayed_confidence` is softmax(mean over the three windows of the raw sum / A), with A = 6a + 3: the nine
  components, the six feature components counted at their weight a.
- `ensemble_probability` is the average of the three windows' normalised ensembles, normalised again; it decides.
- `wifi_speed_m_s`, `direction` and `path` are the 0 s window's.
- `calibration_windows` counts earlier walks. Only each walk's 0 s window joins the pool.

**Added:**

| field | meaning |
|---|---|
| `engine_version` | 5 |
| `room` | the installation's room: `A`, `B` or `new`. On the boards it is set once with `rig --room` before any press; a recorded stream or replay takes it from its session. It never comes from a walk |
| `weight_a` | the feature components' weight for this walk: 0.25 on a tracking walk in Room A when the model trained in Room A, 1 everywhere else (Room B, a room the model never trained in, every identification walk) |
| `windows_s` | `[0.0, 0.15, 0.3]`: the three windows' offsets after the press |
| `window_decisions_mono` | each window's decision time (the engine's causal rule), on the host's `time.monotonic()` clock |
| `components` | per window, each of the nine components' normalised log-probabilities for P1 to P6 (`rf`, `rf_prior`, `rf_pace_prior`, `et_pace_prior`, `lda_pace_prior`, `hgb_pace_prior`, `cnn`, `cnn_prior`, `cnn_perlink_prior`) |
| `ensemble_without_pace_top` | the answer without the four pace components (information) |

**Where the lines are written:** as v2. The rig on the boards refuses to start without `--room A|B|new`; every other
refusal rule is kept, including that a recorded stream refuses any model trained on the day it streams.

**The adaptation and the device (engine v5, from 11 October 2026, Uzayr's option (c)):**
- A walk joins the calibration pool, and the AdaBN copies are recomputed on it, only **after its line is written and
  the screen shows it**. This happens at the app's next poll. If two walks are decided in one poll (as at a recording's
  close), the earlier walk's line is written first, then the walk joins the pool, then the later walk is classified.
  Every walk is still classified against exactly the earlier walks of its layout, so no field of any line changes;
  `calibration_windows` keeps its meaning. `latency_after_window_s` never included the adaptation and still does not.
- `rig` runs an engine v5 model on the GPU (`--device mps`) unless given `--device cpu`. On the cpu the adaptation
  grows with the day's pool, to about 6 s a walk for v4 and v5 alike, so only the GPU can keep identification in
  real time (the confirmation run of 11 October: 297 of 299 decisions within the cap, `reports/identification/2026-10-11_engine-v5.md`).
  A v4 model is unchanged: cpu by default, its adaptation inside the poll as before.
