# Wi-Fi channel-state tracking and identification

One ESP32 transmitter and three ESP32 receivers record the Wi-Fi channel state around a taped 5 m x 5 m grid. The app
names which of twelve taped lines a person is walking and draws their position (tracking), and names which enrolled
person is walking from one key press (identification). Both models are frozen; nothing is trained here.

The thesis figures came from recordings that are not public. With the boards and this README, the experiment can be
rerun.

## How it fits together

Start at `pipeline/live/frozen_model.py`: its four commands (`ports`, `preflight`, `track`, `identify`) are the whole app.

```
pipeline/live/frozen_model.py      the entry point: ports | preflight | track | identify

ESP32 receivers over USB
  -> pipeline/io/capture_logger.py   reads each receiver's serial port
  -> pipeline/io/parse.py            turns each line into one CSI record
  -> pipeline/live/rig.py            hands the records and the key presses to the running mode
       track      final_model.py runs the session: tracking.py -> stream.py, pool.py, start_terms.py,
                  decoder.py, display.py -> pipeline/constrained (decoder.py, paths.py, switching.py);
                  screen.py draws it. Model: runs/public_model/tracking/f05_A3/
       identify   identify_frozen.py -> identify_engine.py -> pipeline/identify/engine.py.
                  Model: runs/identify/engine/models/deploy_all5_v5/
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
| `runs/identify/` | the identification model (four of its files come from the release) | `engine/models/deploy_all5_v5/manifest.json` |
| `videos/` | the app's screens replayed on the recorded session B2 (PA1 to PA6) | `B2 Tracking walks/`, `B2 Identification walks/` |

## Requirements

- A Mac (Apple silicon) with Python 3.13 and: `pip install -r requirements.txt`
- Four ESP32 boards flashed as in step 0: one transmitter (channel 11, 20 MHz, 150 packets per second) and three
  receivers on USB.
- Tape: the 5 m x 5 m grid and its twelve lines as in `Paths.png`. Coordinates below are metres on that grid.

Run every command from the repository root with `OMP_NUM_THREADS=1 PYTHONPATH=.` in front, as written.

## 0. Flash the boards

Clone [esp-csi](https://github.com/espressif/esp-csi), `git checkout 8633d67`, then `git apply <this repository>/firmware/esp-csi.patch`. With ESP-IDF v5.4 (we used v5.4.4) and target esp32, run `idf.py set-target esp32 flash` in `examples/get-started/csi_send` for the transmitter and in `examples/get-started/csi_recv` for each of the three receivers.

## 1. Fetch the release files

Four identification files are too large for git. Download them into the model folder and check them:

```
for f in feat_rf.pkl feat_rf_prior.pkl feat_rf_pace_prior.pkl feat_et_pace_prior.pkl; do curl -L -o runs/identify/engine/models/deploy_all5_v5/$f https://github.com/UzayrB/csi-thesis/releases/download/v1.0/$f; done
```
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

Both apps use these positions. `identify --layout id_spot`, with RX2 moved to (2.0, -0.5) beside the TX, is only for the
geometry test. The TX needs only power; the receivers plug into the Mac. Write your receivers' MAC addresses (printed by
`python3 -m pipeline.io.identify_board`) into `runs/public_model/boards.json`.

## 3. Tracking

Find the ports, record 60 s of the empty room (nobody moves), then check everything:

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

## 4. Identification

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.frozen_model identify --room new
```

When it prints READY, press `a` (away from the TX) or `t` (towards it) once as each walker starts on line A, `n` when a
new person takes over, and q to stop. SPACE is refused here: with RX2 at home the direction detector is right on 90.83 %
of 120 walks, below its 95 % rule. It runs on the Apple GPU.

## Where the outputs go

- `runs/live/hw_2026-10-15/rig_<mode>_<date>_<time>/`: the raw capture, every key press and the run's summary.
- `runs/live/rig/<stem>.json`: the tracking summary; `runs/live/identify/rig_<date>_<time>.jsonl`: one line per
  identification decision.

`videos/` holds the app's own screens replayed on the recorded B2 session (participants as PA1 to PA6).
