# TDR-03: device-free tracking and identification from Wi-Fi channel state

> **About this public copy (15 October 2026).** This is the code and the written records of the thesis project,
> copied without its git history. Participants appear only as the report's codes, PA1 to PA6, everywhere, including
> recording names (for example `participant_PA2_walk`). The recordings (`data/`), the trained models, the caches, the
> raw run outputs, and every image and video are not included, so the commands below describe how the project runs
> but need that private material to run here. Work in progress; not the final submitted version.

A final-year thesis project for UCT EEE4022S. One ESP32 transmitter broadcasts ESP-NOW frames (channel 11,
20 MHz, about 150 packets per second) and three ESP32 receivers record the channel state around a taped
5 m x 5 m grid. A person walks one of twelve taped straight lines with nothing on their body and no camera in
the room. The live app does two things:

- **Tracking:** it names the line being walked and draws the walker's position on screen.
- **Identification:** from one key press when a walk starts, it names which of six people is walking.

Two rooms were recorded: Room A (sessions A1, A2, A3; folders `session_01` to `session_03`) and Room B (B1, B2).
The models train on A1, A2 and B1 and are tested on A3 and B2, which they never train on.

This README was checked against the code on 15 October 2026. Every command below was taken from the code as it
stands, and the folders it names are where the app writes today.

## The two shipped models

| model | what runs | headline (development evaluation, all data seen) | record |
|---|---|---|---|
| Tracking | `pipeline/live/final_model.py`, the final model, display profile `clean_1s_r0`, on the CPU | B2: committed line 97.50 % [94.17, 100.00], lock 71.67 % [63.33, 80.00]; A3: committed 92.50 % [87.50, 96.67], lock 75.00 % [67.48, 82.50]; chance 8.3 % | `reports/tracking/2026-10-10_clean_display_report_update.md`, `reports/tracking/2026-10-14_switch-radius.md` |
| Identification | `pipeline/live/identify_engine.py`, engine v5, deployment model `deploy_all5_v5` (trained on all five sessions), on the Apple GPU | natural walks, each session held out: 36.67 % [23.33, 50.00]; chance 16.7 % | `reports/identification/2026-10-11_engine-v5.md` |

The live app was tested on the boards on 15 October 2026: a board run and its replay give identical outputs for
both models (`runs/live/hw_2026-10-15/REPORT.md`).

## Before you start

- **Python:** the Anaconda interpreter, `/opt/anaconda3/bin/python3` (called `python3` below). Run every command
  from the repository root.
- **Environment:** put `OMP_NUM_THREADS=1 PYTHONPATH=.` in front of every command, as written below.
- **Data:** the recordings in `data/` must be present (read only; nothing writes there).
- **Terminal (zsh):** paste one command at a time. Do not add `#` comments to a command line: zsh does not
  treat them as comments and the command fails.
- **One heavy job at a time:** the identification app uses the GPU. Do not run two apps, or an app and a long
  job, at the same time, or the timing suffers.

## 1. Stream a recorded session (no boards needed)

A recorded session is played back in real time through the same path the boards use, with the presses at
their recorded times. You watch the app's window as if the walks were happening now.

**Tracking, one recording:**

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --stream B2/participant_PA2_walk --screen runs/live/stream_screen
```

- B2 recordings: `B2/participant_<name>_walk`, with `<name>` one of PA5, PA1, PA2, PA3, PA4,
  PA6.
- A3 recordings: `03/participant_<name>_TEST_walk`, with the same six names.
- `--speed 2` plays twice as fast. Leave out `--screen` to run without recording the screen.
- **Results:** `runs/live/stream_disp-K1gf/B2__participant_PA2_walk/`, with `log.jsonl` (every output: lock,
  committed line, dots, with their times) and `summary.json` (counts and timing). With `--screen`, the video
  goes to the folder you name.

**Identification, a whole session:**

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1
```

- `--render natural` shows only the natural identification walks; the rest of the day is fed fast behind the
  scenes, so the app has adapted to the whole day by the time each shown walk starts.
- To watch identification on the **tracking walks** (the grid's paths), start from a tracking recording and
  show the window:

  ```
  OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --from track_track_PA6 --speed 1 --screen
  ```

  `--from` takes a recording's index or label. B2's labels, in order, repeat this pattern for each person:
  `idcap_natural_<name>`, `idcap_fast_<name>`, `idcap_slow_<name>`, `track_track_<name>`. The tracking
  recordings are `track_track_PA6`, `track_track_PA2`, `track_track_PA3`, `track_track_PA4`,
  `track_track_PA5` and `track_track_PA1`.
- `--session` can be A1, A2, A3, B1 or B2. A recorded stream uses the model that never trained on that session,
  not the deployment model.
- `--snapshots <folder>` saves a picture of the screen after each shown decision.
- **Results:** `runs/live/identify/rig_recorded_<session>_<date>_<time>.jsonl`, one line per decision (the
  top person, every person's probability, and the timing).

## 2. Replay a recorded session fast (for figures)

Replays feed the same recordings through the same app as fast as possible, without a window. The thesis
figures come from these.

**Tracking:**

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay --session B2 --presses start
```

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.app_score --model final --mode semi_disp-K1gf_prof-clean_1s_r0_causal --session B2
```

- `--session B2` or `--session 03` (A3) replays every evaluated recording; `--recording B2/participant_PA2_walk`
  replays one. `--presses start` is the headline mode: one press per walk, at its start.
- `--realtime --screen <folder>` records the app's screen as a video (a render).
- **Results:** `runs/live/replay/final/semi_disp-K1gf_prof-clean_1s_r0_causal/`, one `<session>__<stem>.jsonl`
  log and one `.summary.json` per recording, and `SCORE_<session>.json` from the scorer (committed line and
  lock accuracy with intervals, per-line recall, dot error).

**Identification:**

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live replay-identify --session B2 --device mps
```

- **Results:** `runs/live/identify/replay_B2_<date>_<time>.jsonl`, one line per decision.

## 3. Live capture on the boards

**Set-up:** the transmitter at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at (-0.5, 2.5) and RX3 at (5.5, 2.5), in metres
on the taped grid. The transmitter needs only power. The three receivers plug into the Mac by USB. The app finds
each receiver by its MAC address, so it does not matter which USB port each one is in: RX1 `68:09:47:4c:ef:b4`,
RX2 `20:50:0d:1a:28:74`, RX3 `20:50:0d:30:5f:80`.

**The keys go to the Terminal, not to the plot window.** When the app is ready it prints a READY banner. Click on
the Terminal window before pressing anything.

### Tracking

Tracking needs a 60 s recording of the empty room (the baseline) taken just before the walks.

1. Find the receivers' ports (prints, for example, `RX1=/dev/cu.usbserial-3,RX2=...,RX3=...`):

   ```
   NODES=$(OMP_NUM_THREADS=1 PYTHONPATH=. python3 -c "from pipeline.live.rig_run import identify, mapping_by_mac; from pipeline.constrained.nodes import room_a_macs; m = mapping_by_mac(identify(), room_a_macs('data')); print(','.join(f'{k}={v}' for k, v in sorted(m.items()) if k in ('RX1', 'RX2', 'RX3')))")
   ```
   ```
   echo $NODES
   ```

2. Record the baseline. Nobody walks; the operator sits still for 60 s:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.io.capture_logger --duration 60 --out runs/live/baselines --nodes "$NODES" --reset --interval 10
   ```
   ```
   BASE=$(ls -td runs/live/baselines/*/ | head -1)
   ```

3. Check that everything the model needs is in place (opens no port; every line must read `ok`):

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live preflight --baseline "$BASE"
   ```

4. Run tracking (here for 20 minutes; leave out `--minutes` to run until you press q):

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --baseline "$BASE" --minutes 20
   ```

   Start-up takes about a minute and shows four numbered steps. Then: stand still for at least 10 s, press
   SPACE once as each walk starts (at the start tape), wait at least 5 s between walks, and press q to stop.
   The app ends each walk itself. A press in the first seconds, before the app has seen 10 s of still room, is
   refused with a message; start again.

### Identification

No baseline is needed. Give the room: `A`, `B`, or `new` for a room the model never trained in.

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --room new --minutes 10
```

Start-up takes about half a minute. Then press SPACE once as each walker starts, `n` when a new person takes
over, `a` or `t` instead of SPACE to give the route (away or towards) on the identification path, and q to stop.
Keep the plot window visible during a walk: macOS can slow a hidden window.

### While a board run is going

- **A receiver goes silent** (power or cable): both apps print `RXn is silent`. Identification skips each walk it
  cannot identify and says why; tracking keeps going and lists the affected walks in its summary. A receiver
  that is unplugged and plugged back in stays silent until the app is restarted.
- **To stop:** press q once (or Ctrl+C once) and wait for the summary to print. Do not press Ctrl+C a second time
  or close the Terminal while it saves, or the run's records are lost.

### Where a board run's results go

Board recordings go to `runs/live/hw_2026-10-15/` (the folder of the 15 October hardware test; every board run
since writes there):

| file | what it is |
|---|---|
| `rig_tracking_<date>_<time>/` or `rig_identify_<date>_<time>/` | one folder per run |
| `<stem>_RX1.bin`, `_RX2.bin`, `_RX3.bin` | the raw capture, every packet as it arrived (git-ignored, about 3 MB a minute per receiver) |
| `<stem>_run.json` | the capture's own summary: packet rates, drops, every packet accounted for |
| `<stem>.keys.json` | every key press with its time, and each receiver's counters |
| `<stem>.log.jsonl` (tracking) | every output of the app: lock, committed line, dots, with their times |
| `<stem>.gt.json` (tracking) | the presses and the baseline, so the run can be replayed |
| `<stem>.summary.json` | the run's counts, timing and, if any, receiver outages and skipped walks |

Identification also writes its decisions to `runs/live/identify/rig_<date>_<time>.jsonl` (one line per decision),
and tracking writes a short summary to `runs/live/rig/<stem>.json`.

A board run can be replayed through the app to check that the replay gives the same outputs:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/live/hw_2026-10-15/live_replay.py tracking runs/live/hw_2026-10-15/rig_tracking_<date>_<time>
```
```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 runs/live/hw_2026-10-15/live_replay.py identify runs/live/hw_2026-10-15/rig_identify_<date>_<time>
```

The comparison is written to `REPLAY_COMPARE.json` in the run's folder.

## Where the results are

| what | where |
|---|---|
| tracking replays and scores | `runs/live/replay/final/<mode>/` (`SCORE_<session>.json`, one log per recording) |
| tracking streamed runs | `runs/live/stream_disp-K1gf/<session>__<stem>/` |
| tracking videos of the shipped display (A3 and B2, every participant) | `runs/live/renders_K1gf_1s_r0/` |
| identification decisions (replays, streams, board runs) | `runs/live/identify/*.jsonl` |
| board recordings | `runs/live/hw_2026-10-15/rig_*/` |
| the hardware test (15 October 2026) | `runs/live/hw_2026-10-15/REPORT.md` |
| the tracking model's files | `runs/dc2_results/` (cells `f05_A3`, `f05_B2`), checked at start-up against `runs/live/models/final.json` |
| the identification models | `runs/identify/engine/models/` (`deploy_all5_v5` on the boards, `loso_<session>_v5` for replays) |
| write-ups of every result | `reports/` (index `reports/README.md`) |

## How the repository is laid out

| folder | what it holds |
|---|---|
| `pipeline/live/` | the live app: `final_model.py` (tracking), `identify_engine.py` (identification), `rig.py` (the board run), `stream_source.py` (streaming a recording), `app_replay.py` and `app_score.py` (replay and scoring), `screen.py` (the tracking window) |
| `pipeline/constrained/` | the tracking model (training, decoding, the model cells) |
| `pipeline/identify/` | the identification model (`engine.py`, the classifiers in `idw_core.py`, which must keep its path because the saved models name it) |
| `pipeline/io/` | capture from the boards (`capture_logger.py`), parsing, cleaning and windowing |
| `data/` | the raw recordings: `room_A/session_01` to `session_03`, `room_B/session_B1`, `session_B2` and `room_B/identification/`, plus `windows/room_A/`. Never edited |
| `runs/` | results, trained models, caches and run records; `runs/MACHINE_STATE.md` logs who is using the machine |
| `reports/` | write-ups, split into `tracking/`, `identification/` and `project/`; files are named `YYYY-MM-DD_topic.md` |
| `tests/` | the test suite: `python3 -m pytest -q tests` (the live app's tests: `tests/test_live_*.py`) |
| `tools/` | helper commands (the walking-gate calibration, the DC2 verification step, the layout and path images) |
| `configs/` | the operator reaction-time calibration and the walking-gate settings |

`pipeline/README.md` describes every module. Modules the current models do not use were removed on 1 October
2026 and are in git at the tag `tracking-final-2026-10-01`.

## Older work still in the repository

Earlier stages are kept because records cite them, but none is the current model: the frozen Room A tracker and
its DC2 cross-room test (`runs/TRACKING_FROZEN_2026-09-23h.json`, `reports/tracking/dc2/2026-09-28_results.md`),
the identification engines v3 and v4 (`runs/identify/engine/models/*_v4`), and retired documents in
`reports/attempts/` and `runs/attempts/`. Removed code is in git at the tags `pre-cleanup` and
`tracking-final-2026-10-01`.

What protects the shipped models: the live app checks its model files at start-up (`runs/live/models/final.json`
and `zeroshot.json`); the pre-flight checks the hash lists in `runs/dc2_results/final/TRACE_HASHES_*.txt`; each
identification model records the code commit it was trained at (`runs/identify/engine/models/*/manifest.json`).
