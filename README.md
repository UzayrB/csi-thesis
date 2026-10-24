# Wi-Fi channel-state tracking and identification

One ESP32 transmitter and three ESP32 receivers record the Wi-Fi channel state around a taped 5 m x 5 m grid. The app
names which of twelve taped lines a person is walking and draws their position (tracking), and names which enrolled
person is walking from one key press (identification). Both models are frozen; nothing is trained here.

The thesis figures came from recordings that are not public. With the boards and this README, the experiment can be
rerun.

## How it fits together

Start at `pipeline/live/frozen_model.py`: `app` opens a start dialog (tracking or identification) and runs the task with the
other four commands (`ports`, `preflight`, `track`, `identify`), which are the whole app.

```
pipeline/live/frozen_model.py      the entry point: app | ports | preflight | track | identify
pipeline/live/app.py               app: the start dialog, then one task's own commands

ESP32 receivers over USB
  -> pipeline/io/capture_logger.py   reads each receiver's serial port
  -> pipeline/io/parse.py            turns each line into one CSI record
  -> pipeline/live/rig.py            hands the records and the key presses to the running mode
       track      final_model.py runs the session: tracking.py -> stream.py, pool.py, start_terms.py,
                  decoder.py, display.py -> pipeline/constrained (decoder.py, paths.py, switching.py);
                  screen.py draws it. Model: runs/public_model/tracking/f05_A3/
       identify   identify_frozen.py -> identify_engine.py -> pipeline/identify/engine.py; the path map
                  (identify_engine.PathPopup) gives each walk's path. Model: runs/identify/engine/models/deploy_all5_v5s/
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
| `runs/identify/` | the identification model (every file in git) | `engine/models/deploy_all5_v5s/manifest.json` |
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

A start dialog asks for the task, **Tracking** or **Identification**, and for identification the room (`A`, `B`, or `new`
for a room the model never trained in). One task runs per run. To skip the dialog: `--task tracking`, or `--task
identification --room new`; `--minutes 20` stops after 20 minutes. The app then runs the commands of sections 4 and 5,
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
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model identify --room new --popup
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

The identification model is engine v5s: engine v5 with five of its nine components (`lda_pace_prior`, `hgb_pace_prior`,
`cnn`, `cnn_prior` and `cnn_perlink_prior`). The four forests (`rf`, `rf_prior`, `rf_pace_prior` and `et_pace_prior`)
are removed and never loaded; `hgb_pace_prior` reads its standardiser, the one it shared with `rf_pace_prior`, from
`state_rf_pace_prior.pkl`. The model's `manifest.json` names the five in its `v5s` field.

## Where the outputs go

- `runs/live/hw_2026-10-15/rig_<mode>_<date>_<time>/`: the raw capture, every key press and the run's summary.
- `runs/live/rig/<stem>.json`: the tracking summary; `runs/live/identify/rig_<date>_<time>.jsonl`: one line per
  identification decision.

`videos/` holds the app's own screens replayed on the recorded B2 session (participants as PA1 to PA6); the two
identification sets show the engine v5s model.
