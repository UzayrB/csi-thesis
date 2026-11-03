# Wi-Fi channel-state tracking and identification

One ESP32 transmitter and three ESP32 receivers record the Wi-Fi channel state around a taped 5 m x 5 m grid. The app
names which of twelve taped lines a person is walking and draws their position (tracking), and names which enrolled
person is walking from one key press (identification). Both models are frozen; nothing is trained here.

The thesis figures came from the recordings shared, anonymised, in the Google Drive folder of section 6: the code runs
on them without boards (a streamed run), and with the boards and this README the experiment can be rerun (a live run).

## How it fits together

`pipeline/` is the app and nothing else. Start at `pipeline/main.py`: `app` opens a start window (tracking or
identification) and runs that task's steps in order (`ports`, `preflight`, `track`, or `identify`), and each step
also works on its own. Each task then reads top to bottom in its own folder; every file starts with the steps it
holds (T1 to T11 for tracking, I1 to I9 for identification) and what it does. The one other folder is
`pipeline/io/Capture/`: the files that recorded the shared recordings and made their labels (its `README.md` says how a
label is made); the app never loads them.

```
pipeline/main.py                     START HERE: app | ports | preflight | track | identify | stream | ...

ESP32 receivers over USB
  -> pipeline/io/boards.py           which port each receiver is on (by MAC); the receivers and the keys on one clock
  -> pipeline/io/serial_capture.py   one reader thread per receiver, each line into one CSI record, rate checks
       track     pipeline/tracking/: run.py -> tracker.py (the frozen tracker) -> session.py, which runs each packet
                 through windows.py (2 s windows, with io/signals.py) -> networks.py -> start_terms.py ->
                 decoder.py (the line) -> display.py (the dot) -> screen.py (the window).
                 Model: runs/public_model/tracking/f05_A3/
       identify  pipeline/identification/: run.py -> window.py (the path map, Done, the result) -> engine.py
                 (features.py, classifiers.py), with extraction.py's helper processes.
                 Model: runs/identify/engine/models/deploy_all5_v5n/
  -> outputs in runs/live/ (see the end of this README)
Without the boards: tracking/run.py's stream (main stream) and identification/recordings.py (section 6)
```

| folder | what it holds | open first |
|---|---|---|
| `firmware/` | the change to Espressif's esp-csi that the four boards run | `esp-csi.patch` |
| `pipeline/main.py` | the app's front door: the start window, each task's steps in order, every command | `main.py` |
| `pipeline/io/` | the boards: finding them by MAC, the run loop, serial capture and CSI line parsing, the cleaned signal | `boards.py`, `serial_capture.py`, `signals.py` |
| `pipeline/io/Capture/` | how the recordings were made and labelled: the board check, the reaction-time test, the capture, the recording-day logger and its paths, the Room B identification captures, the press relabel, the labelled 2 s windows | `README.md`, `ground_truth.py`, `windows.py` |
| `configs/` | the operator's reaction-time calibration, subtracted from every press in the recordings (a new calibration is a new file beside it) | `operator_rt.json` |
| `pipeline/tracking/` | tracking: the run, the frozen tracker, the session, windows, networks, start terms, decoder, display and screen | `run.py`, `tracker.py`, `session.py` |
| `pipeline/identification/` | identification: the run, the window, the extraction helpers, the engine, its gait features and its classifiers | `run.py`, `window.py`, `engine.py` |
| `runs/public_model/` | the frozen tracker, the receivers' MACs, the identification files' hashes | `tracking/f05_A3/meta.json`, `boards.json`, `identification_hashes.txt` |
| `runs/identify/` | the identification model and its five fold models (every file in git); the identification recordings' order for a replay | `engine/models/deploy_all5_v5n/manifest.json` |
| `videos/` | the app's screens replayed on the recorded session B2 (PA1 to PA6) | `B2 Tracking walks/`, `B2 Identification walks/` |

## Requirements

- A Mac (Apple silicon) with Python 3.13, in an environment of its own, with the packages: `python3 -m venv .venv`,
  `source .venv/bin/activate`, then `pip install -r requirements.txt` (or a conda environment). Every command below
  uses `python`, that environment's interpreter; check with `python -c "import numpy, torch, matplotlib"`, which
  prints nothing when all is well.
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

Both tasks use these positions; nothing moves between them. The TX needs only power; the receivers plug into the Mac. Write your receivers' MAC addresses (printed by
`python -m pipeline.io.boards`) into `runs/public_model/boards.json`.

## 3. The app: one command

```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main app
```

A start window asks for the task, **Tracking** or **Identification** (identification needs no room: the model weighs
every walk the same in any room). One task runs per run. To skip the window: `--task tracking`, or `--task
identification`; `--minutes 20` stops after 20 minutes. The app then runs the commands of sections 4 and 5,
which also work on their own.

## 4. Tracking

Started from the app, tracking finds the ports, asks you to press Enter for the 60 s baseline, runs the pre-flight (it
stops if a line fails) and starts tracking (`--baseline <folder>` reuses an earlier baseline). By hand: find the ports,
record 60 s of the empty room (nobody moves), then check everything:

```
NODES=$(OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main ports)
```
```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.serial_capture --duration 60 --out runs/live/baselines --nodes "$NODES" --reset --interval 10
```
```
BASE=$(ls -td runs/live/baselines/*/ | head -1)
```
```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main preflight --baseline "$BASE"
```

Every line must read `ok`. Then run tracking:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main track --baseline "$BASE"
```

When it prints READY, click on the Terminal (the keys are read there), stand still for 10 s, press SPACE once as each
walk starts at its start tape, and press q to stop.

## 5. Identification

Started from the app, identification runs:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main identify
```

Walks can be on any of the twelve paths. One window opens, and every walk goes through it in three steps:

1. The map of the twelve paths: click the walk's path (one click gives its line and direction), then press **Done**.
2. The window waits: press SPACE in the Terminal as the walker starts. After Done the keyboard goes back to the Terminal
   (Terminal, iTerm or VS Code); otherwise click on the Terminal first. SPACE counts only after Done, once per Done,
   and it brings the window back in front by itself.
3. The result. **Next identification walk** (one click) goes back to the map with the last path still picked, so
   repeating a path is Done, then SPACE.

SPACE before Done, during a walk or on a result is refused, with what to press instead. `a` and `t` start a line-A walk
(away from or towards the TX) from the map or the waiting page, `n` marks a new person (it resets the on-screen tally)
and q stops; `n` and `q` also work in the identification window. The path is given
rather than detected: the engine's direction detector covers line A only, and with RX2 at its tracking position it is
right on 90.83 % of 120 line-A walks (96.9 % of 419 with RX2 beside the transmitter), below its 95 % rule. It runs on the
Apple GPU.

The identification model is engine v5n. It has the five components of engine v5s (`lda_pace_prior`, `hgb_pace_prior`,
`cnn`, `cnn_prior` and `cnn_perlink_prior`); the four forests of engine v5 are not shipped and never loaded. The two
feature components read the receivers' 107 bins, and each packet is divided by its mean over the bins before the
features are taken, and the Doppler contours' percentile crossing is interpolated inside its bin. The three
CNN components are v5s's, on the raw amplitude. `hgb_pace_prior` reads its standardiser from `state_rf_pace_prior.pkl`.
The model's `manifest.json` names the five components in its `v5s` field, and its `v5n` field selects the v5n feature
path in `pipeline/identification/engine.py`. The feature components carry the weight 1 on every walk in every room, so the
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
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main app --task tracking --stream B2/participant_PA5_walk
```

`--stream <session>/<stem>`: the session is A1, A2, A3, B1 or B2, and the stem is a recording's name without its
`.gt.json` (list them with `ls data/room_B/session_B2/*.gt.json`). A recording takes about 6 minutes and plays in real
time only. The frozen tracker was trained on A1, A2 and B1, so A3 and B2 are the sessions it never saw. The run writes
`runs/live/stream/<session>__<stem>/`: `log.jsonl` (every output), `summary.json` and `capture/` (the packets and presses
as the app received them). `python -m pipeline.main stream --stream B2/participant_PA5_walk --no-window`
runs it without the window.

**Identification.** A session's walks are decided by the fold model that never saw that session
(`runs/identify/engine/models/loso_<session>_v5n`). Streamed through the live app with its window:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main identify-recorded --session B2 --screen --speed max
```

(`--speed 1` plays in real time.) Every walk decided as fast as the CPU allows, without a window:

```
OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main replay-identify --session B2
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

---

## Recording more data, and training on it (a separate guide)

Everything above runs the finished models. This part is separate: how the shared recordings in `data/` were made, step
by step, if you want to record more, and then, in words, how the models were trained on them. The recording code is
all in `pipeline/io/Capture/` (its `README.md` explains each file). Put `OMP_NUM_THREADS=1 PYTHONPATH=.` in front of
every command, as above, and flash and place the boards as in sections 0 and 2. The examples record a new Room A
session, `04`, and a new participant, `P07`, so nothing already in `data/` is touched (the logger also refuses to
overwrite a recording).

### Before the first recording

1. Which board is on each USB port, and its MAC. With new boards, put the three receivers' MACs in
   `runs/public_model/boards.json`, which is how the next command finds them:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.identify_board
   ```

2. The receivers' ports, as in section 4:

   ```
   NODES=$(OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.main ports)
   ```

3. The operator's reaction-time test, once per operator: press SPACE as the marker on screen crosses the line, 25 times
   at each of 1.0 and 1.4 m/s. Each run writes a new file, `configs/operator_rt_<date>-<time>.json`, and never
   overwrites one (`configs/operator_rt.json`, the calibration behind the shared recordings, stays as it is). The
   logger uses the newest calibration, names it as it starts, and subtracts that delay from every press:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.rt_calibration
   ```

### A tracking recording (one per participant)

4. The 60 s empty-room baseline (nobody walks; the operator sits still), in a dated folder inside the session:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_logger --duration 60 --out data/room_A/session_04 --nodes "$NODES" --reset
   ```
   ```
   BASE=$(ls -td data/room_A/session_04/*/ | head -1)
   ```

5. The session's plan, without the boards: the twelve lines and the 25 grid cells in a seeded order:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.ground_truth --participant P07 --room A --session 04 --dry-run
   ```

6. The recording: the walking passes in two halves with the grid sweep between them.

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.ground_truth --participant P07 --room A --session 04 --mode both --baseline "$BASE" --nodes "$NODES" --rx-positions "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5" --tx-position 2.5,-0.5 --height-cm 175 --weight-kg 70 --clothing "jeans, T-shirt" --footwear trainers
   ```

   The keys go to the Terminal. Press SPACE as the walker's torso crosses each of the six taped crossings of a line,
   or once they have settled on a grid cell. `x` redoes the pass, or the one just closed, and `q` stops. It writes
   `participant_P07_walk_RX1.bin` to `_RX3.bin` and `participant_P07_walk.gt.json`: every press, each pass's line,
   the reaction time, the receivers' positions and the participant's details. For a held-out test session, add
   `--test` (the names get a `TEST` infix).

7. Check that each file holds real CSI (rate, signal, dead subcarriers, a verdict per file):

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.inspect_capture data/room_A/session_04
   ```

### Identification walks (Room B's design)

Line A only, walked away from the transmitter and back, with RX2 moved beside the transmitter at (2.0, -0.5). The
recordings go to `data/room_B/identification/session_0<day>/`. In the commands below, put the person's capture code in
place of `CODE`: it must be one of the six in `SIX` at the top of `pipeline/io/Capture/capture_idpath.py` (PA1 to PA6), so add a
new person there first. Add `--dry-run` to any of them to see what it would record.

8. Once, record RX2's identification spot:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_idboth --set-spot primary
   ```

9. The day's order of participants, and each one's order of blocks:

   ```
   OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_idboth --plan-day --day 1
   ```

10. With RX2 at its spot, 30 s of empty room before the person walks (`--move-time` is the clock time RX2 was moved):

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_idboth --empty --position idspot --participant CODE --day 1 --move-time 09:00 --nodes "$NODES"
    ```

11. The walk blocks: natural first, then slow and fast in the order step 9 printed (another order is refused). Press
    SPACE at every metre, six times a pass:

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_idboth --participant CODE --day 1 --block natural --height-cm 175 --weight-kg 70 --shoes trainers --clothing "jeans, T-shirt" --nothing-carried --nodes "$NODES"
    ```

12. RX2 back at its tracking position, then 30 s of empty room again:

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.capture_idboth --empty --position home --participant CODE --day 1 --move-time 09:40 --nodes "$NODES"
    ```

### After recording

13. Room B tracking sessions only: write down, at capture time, which recording was the calibration walk and any pass
    abandoned in the room (it only ever adds to `data/room_B/calibration.json`):

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.dc2b_manifest --session B3 --calibration participant_CODE_walk
    ```
    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.dc2b_manifest --session B3 --aborted participant_CODE_walk:7
    ```

14. Identification walks: if a press was doubled, the relabel removes the extra one by one fixed rule, in a copy under
    `runs/` (the capture is never edited). Use new paths so the shipped relabel stays as it is:

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.idrelabel --write-manifest --manifest runs/identify/new/relabel_manifest.json
    ```
    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.idrelabel --manifest runs/identify/new/relabel_manifest.json --dst runs/identify/new_relabelled/identification
    ```

15. The labelled 2 s windows of the new session: each window is `walk` (its position interpolated in time between the
    presses either side), `walk_edge`, `grid` or `idle`. Always give `--out`, as the default is inside `data/`:

    ```
    OMP_NUM_THREADS=1 PYTHONPATH=. python -m pipeline.io.Capture.windows --sessions 04 --out runs/windows_new
    ```

### Training on the recordings (in words)

Training is not part of this release: the code that trained the two models is the thesis's development code, and only
the frozen models are here. This is what each model needs, in words.

**The tracker.** Cut every recording into labelled 2 s windows: every 1 s (step 15), and every 0.5 s with one window
starting exactly on each start press, as the live app cuts them. Choose the training sessions and keep one session out
to test on (the shipped tracker trained on A1, A2 and B1 and was tested on A3). On the training sessions' walking
windows (not the standing dwells, which made it worse), train the five networks that give each window a position on
the grid: one on the 0.5 s windows, three seeds on the 1 s windows (25 cells each) and one on 1 s windows with 100
cells. Then train the two start readers on the same sessions: networks that read where a walk starts, with small
classifiers fitted on what they output. Take the walking pace (the mean and spread of walking speed) from the training
sessions' tape marks, and set the walking gate's threshold on standing dwells against walking windows. Decode the
held-out session and score it.

**The identification model.** Run every recording through the engine's own extractor. From each walk's press it takes
4 s windows and makes the gait features, the Doppler maps and the Wi-Fi walking speed, and together these make a bank.
On the bank, train the five classifiers: two on the features (a linear discriminant and gradient-boosted trees, each
with a walking-pace prior) and three CNNs on the Doppler maps (all links together, the same with the pace prior, and
one per link with the prior), three seeds each, with extra windows taken just after the press and copies stretched in
time. Check by leaving one session out at a time (the fold models); the deployed model then trains on every session.

**Putting a new model in.** For tracking, freeze the trained tracker into a folder of its own under
`runs/public_model/tracking/` (the networks, `readers.pkl`, `pieces.pkl`, `meta.json` and a `HASHES.txt` of every
file) and point `TRACKER` in `pipeline/tracking/tracker.py` at it. For identification, put the model folder in
`runs/identify/engine/models/<name>/` with its manifest, return its name from `deployment_model()` in
`pipeline/identification/run.py`, and list each of its files' sha256 in
`runs/public_model/identification_hashes.txt`. Streamed runs use the fold model that never saw the streamed session,
`loso_<session>_v5n` (the name is set in the same file). The pre-flight checks every one of those files before a run,
and the app then runs exactly as in sections 3 to 6.
