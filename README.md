# Wi-Fi channel-state tracking and identification

One ESP32 transmitter and three ESP32 receivers record the Wi-Fi channel state around a taped 5 m x 5 m grid. The app
names which of twelve taped lines a person is walking and draws their position (tracking), and names which enrolled
person is walking from one key press (identification). Both models are frozen; nothing is trained here.

The thesis figures came from the recordings shared, anonymised, in the Google Drive folder of section 6: the code runs
on them without boards (a streamed run), and with the boards and this README the experiment can be rerun (a live run).

## How it fits together

Start at `pipeline/live/frozen_model.py`: `app` opens a start dialog (tracking or identification) and runs the task with the
other four commands (`ports`, `preflight`, `track`, `identify`), which are the whole app.

```
pipeline/live/frozen_model.py      the entry point: app | ports | preflight | track | identify
pipeline/live/app.py               app: the start dialog, then one task's own commands
pipeline/live/stream_frozen.py     stream: a recording from data/ in place of the boards (section 6)

ESP32 receivers over USB
  -> pipeline/io/capture_logger.py   reads each receiver's serial port
  -> pipeline/io/parse.py            turns each line into one CSI record
  -> pipeline/live/rig.py            hands the records and the key presses to the running mode
       track      final_model.py runs the session: tracking.py -> stream.py, pool.py, start_terms.py,
                  decoder.py, display.py -> pipeline/constrained (decoder.py, paths.py, switching.py);
                  screen.py draws it. Model: runs/public_model/tracking/f05_A3/
       identify   identify_frozen.py -> identify_engine.py -> pipeline/identify/engine.py; the path map
                  (identify_engine.PathPopup) gives each walk's path. Model: runs/identify/engine/models/deploy_all5_v5n/
  -> outputs in runs/live/ (see the end of this README)
```

| folder | what it holds | open first |
|---|---|---|
| `firmware/` | the change to Espressif's esp-csi that the four boards run | `esp-csi.patch` |
| `pipeline/io/` | serial capture, CSI line parsing, finding the boards, 2 s windows | `capture_logger.py`, `parse.py`, `identify_board.py` |
| `pipeline/live/` | the app: the commands, the board runs, the tracking session, the screen, identification | `frozen_model.py`, `final_model.py`, `tracking.py` |
| `pipeline/constrained/` | the tracker: the twelve lines, the networks, the decoder | `paths.py`, `nets.py`, `decoder.py` |
| `pipeline/identify/` | the identification engine and its gait features | `engine.py`, `common.py` |
| `runs/public_model/` | the frozen tracker, the receivers' MACs, the identification files' hashes | `tracking/f05_A3/meta.json`, `boards.json`, `identification_hashes.txt` |
| `runs/identify/` | the identification model and its five fold models (every file in git); the identification recordings' order for a replay | `engine/models/deploy_all5_v5n/manifest.json` |
| `videos/` | the app's screens replayed on the recorded session B2 (PA1 to PA6) | `B2 Tracking walks/`, `B2 Identification walks/` |

## Requirements

- A Mac (Apple silicon) with Python 3.13 and: `pip install -r requirements.txt`
- Four ESP32 boards flashed as in step 0: one transmitter (channel 11, 20 MHz, 150 packets per second) and three
  receivers on USB.
- Tape: the 5 m x 5 m grid and its twelve lines as in `Paths.png`. Coordinates below are metres on that grid.

Run every command from the repository root with `OMP_NUM_THREADS=1 PYTHONPATH=.` in front, as written.

## 0. Flash the boards

Clone [esp-csi](https://github.com/espressif/esp-csi), `git checkout 8633d67`, then `git apply <this repository>/firmware/esp-csi.patch`. With ESP-IDF v5.4 (we used v5.4.4) and target esp32, run `idf.py set-target esp32 flash` in `examples/get-started/csi_send` for the transmitter and in `examples/get-started/csi_recv` for each of the three receivers.

## 1. Check the identification files

Every identification file is in git (nothing to download). Check them:

```
shasum -a 256 -c runs/public_model/identification_hashes.txt
```

## 2. Place the boards

| board | position (tracking and identification) |
|---|---|
| TX | (2.5, -0.5) |
| RX1 | (2.5, 5.5) |
| RX2 | (-0.5, 2.5) |
| RX3 | (5.5, 2.5) |

Both tasks use these positions; nothing moves between them. `identify --layout id_spot`, with RX2 moved to (2.0, -0.5)
beside the TX, is only for the geometry test. The TX needs only power; the receivers plug into the Mac. Write your receivers' MAC addresses (printed by
`python3 -m pipeline.io.identify_board`) into `runs/public_model/boards.json`.

## 3. The app: one command

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model app
```

A start dialog asks for the task, **Tracking** or **Identification** (identification needs no room: the model weighs
every walk the same in any room). One task runs per run. To skip the dialog: `--task tracking`, or `--task
identification`; `--minutes 20` stops after 20 minutes. The app then runs the commands of sections 4 and 5,
which also work on their own.

## 4. Tracking

Started from the app, tracking finds the ports, asks you to press Enter for the 60 s baseline, runs the pre-flight (it
stops if a line fails) and starts tracking (`--baseline <folder>` reuses an earlier baseline). By hand: find the ports,
record 60 s of the empty room (nobody moves), then check everything:

```
NODES=$(OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model ports)
```
```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.io.capture_logger --duration 60 --out runs/live/baselines --nodes "$NODES" --reset --interval 10
```
```
BASE=$(ls -td runs/live/baselines/*/ | head -1)
```
```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model preflight --baseline "$BASE"
```

Every line must read `ok`. Then run tracking:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model track --baseline "$BASE"
```

When it prints READY, click on the Terminal (the keys are read there), stand still for 10 s, press SPACE once as each
walk starts at its start tape, and press q to stop.

## 5. Identification

Started from the app, identification runs:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model identify --popup
```

Walks can be on any of the twelve paths. A map of the twelve paths opens beside the identification window. Before each
walk, click its path on the map (one click gives its line and direction), then press SPACE in the Terminal as the walker
starts. After a click the keyboard goes back to the Terminal (Terminal, iTerm or VS Code); otherwise click on the Terminal
first. The map takes no clicks during a walk and opens again after each decision with the last path still picked, so
repeating a path is one SPACE. SPACE with no path picked is refused. `a` and `t` still start a line-A walk (away from or
towards the TX), `n` marks a new person and q stops. The path is given rather than detected: the engine's direction
detector covers line A only, and with RX2 at its tracking position it is right on 90.83 % of 120 line-A walks (96.9 % of
419 with RX2 beside the transmitter), below its 95 % rule. Without `--popup`, only `a` and `t` (line A) start a walk. It
runs on the Apple GPU.

The identification model is engine v5n. It has the five components of engine v5s (`lda_pace_prior`, `hgb_pace_prior`,
`cnn`, `cnn_prior` and `cnn_perlink_prior`); the four forests of engine v5 are not shipped and never loaded. The two
feature components read the receivers' 107 bins, and each packet is divided by its mean over the bins before the
features are taken, and the Doppler contours' percentile crossing is interpolated inside its bin. The three
CNN components are v5s's, on the raw amplitude. `hgb_pace_prior` reads its standardiser from `state_rf_pace_prior.pkl`.
The model's `manifest.json` names the five components in its `v5s` field, and its `v5n` field selects the v5n feature
path in `pipeline/identify/engine.py`. The feature components carry the weight 1 on every walk in every room, so the
engine takes no room.

## 6. Run the thesis code on the recorded data

The recordings behind the thesis figures are in this Google Drive folder:
[TDR-03 recordings](https://drive.google.com/drive/folders/1CFtAod3h3Dvs25TpHo_GYJL8tKR7jpSl?usp=drive_link). Download
the two anonymised zips; the participants appear as PA1 to PA6 (the report's codes) in every file and folder name and
inside every file. The captures (`.bin`) are byte for byte the recorded ones.

| zip | unzips to | files | sha256 |
|---|---|---|---|
| `room_A_anon.zip` | `data/room_A`: sessions A1, A2, A3 (`session_01`, `session_02`, `session_03`) | 248 | `692194386257046e35104230edc80dd13ac96dee71716b61e760a3a5c607e513` |
| `room_B_anon.zip` | `data/room_B`: sessions B1, B2 (`session_B1`, `session_B2`) and the identification recordings | 459 | `2916a898a42606d5519191a64b813b8116339bd11f0706db7247ed5cbb494162` |

Put both in the repository root, check them, and unzip there (each zip holds its `data/room_...` folder; `data/` is not
tracked by git):

```
shasum -a 256 room_A_anon.zip room_B_anon.zip
```
```
unzip room_A_anon.zip && unzip room_B_anon.zip
```

### (a) Streamed run: the recordings, no boards

**Tracking.** One walk recording is streamed in real time through the boards' own ingestion path (the serial readers,
the line parser and the rig's consumer; only the packet source is replaced) to the frozen tracker, in the tracking window.
Each walk's recorded start press is given as a SPACE at its recorded time:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model app --task tracking --stream B2/participant_PA5_walk
```

`--stream <session>/<stem>`: the session is A1, A2, A3, B1 or B2, and the stem is a recording's name without its
`.gt.json` (list them with `ls data/room_B/session_B2/*.gt.json`). A recording takes about 6 minutes and plays in real
time only. The frozen tracker was trained on A1, A2 and B1, so A3 and B2 are the sessions it never saw. The run writes
`runs/live/stream/<session>__<stem>/`: `log.jsonl` (every output), `summary.json` and `capture/` (the packets and presses
as the app received them). `python3 -m pipeline.live.frozen_model stream --stream B2/participant_PA5_walk --no-window`
runs it without the window.

**Identification.** A session's walks are decided by the fold model that never saw that session
(`runs/identify/engine/models/loso_<session>_v5n`). Streamed through the live app with its window:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --screen --speed max
```

(`--speed 1` plays in real time.) Every walk decided as fast as the CPU allows, without a window:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine replay-identify --session B2
```

Each writes one line per decision to `runs/live/identify/` (`rig_recorded_B2_<date>_<time>.jsonl` or
`replay_B2_<date>_<time>.jsonl`): the top choice and the runner-up with their probabilities, as the model's classes P1 to
P6 (`top`, `runner_up`; P1 to P6 are PA5, PA1, PA2, PA3, PA4 and PA6) and as PA codes (`top_name`, `runner_up_name`).
The first identification run on the recordings builds `runs/identify/dc2_src_relabelled/` from `data/` (in one Room B
block a double key press is removed, as in the thesis, by `runs/identify/dc2/relabel_manifest.json`).

### (b) Live run: the boards

Sections 0 to 5: flash the boards, place them, then run the app. A live run needs no recorded data.

## Where the outputs go

- `runs/live/hw_2026-10-15/rig_<mode>_<date>_<time>/`: the raw capture, every key press and the run's summary.
- `runs/live/rig/<stem>.json`: the tracking summary; `runs/live/identify/rig_<date>_<time>.jsonl`: one line per
  identification decision.
- `runs/live/stream/<session>__<stem>/` and `runs/live/identify/replay_*.jsonl`, `rig_recorded_*.jsonl`: the streamed
  runs of section 6.

`videos/` holds the app's own screens replayed on the recorded B2 session (participants as PA1 to PA6); the two
identification sets show the engine v5n model.
