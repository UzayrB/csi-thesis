# pipeline/io/Capture: how the data was recorded and labelled

Every file that recorded the data and turned the operator's key presses into labels, in one place. The files import
only each other, and the live app never loads them (it has its own copies of the capture code in `io/RunLive/`). Run
every command from the repository root with `OMP_NUM_THREADS=1 PYTHONPATH=.` in front, as in the main README.

## How a label is made

1. Before a session, `identify_board.py` says which board is on each USB port, and `rt_calibration.py` measures the
   operator's press delay against a marker crossing a line at walking speed (`configs/operator_rt.json`).
2. `ground_truth.py` runs the capture (`capture_logger.py`, parsing each line with `parse.py`) and reads SPACE in the
   same process, so the CSI and the presses share one monotonic clock. The walker follows the plan from `anchors.py`:
   a press as the torso crosses each of the six taped crossings of a line, or as they settle on a grid cell. The press
   delay is subtracted from every press.
3. Each recording is saved as `<stem>_RX1.bin`, `_RX2.bin`, `_RX3.bin` (every packet, raw) and `<stem>.gt.json` (the
   session's metadata and every press: for each pass its `pass_id`, `path_name`, `anchor_times`, `anchor_coords`,
   `t_start`, `t_end` and any flags; for each dwell its cell, centre and times).
4. `windows.py` cuts each recording into 2 s windows and labels each from the sidecar: `walk` (the position
   interpolated in time between the presses either side of the window's midpoint), `walk_edge` (within 3 s of a pass),
   `grid` (a dwell's cell centre) or `idle`.

Room B's identification walks went through `capture_idpath.py` and `capture_idboth.py`: line A, with a press at
every metre (six per pass, as `ground_truth.py`'s walk mode needs; identification reads the first). `dc2b_manifest.py`
recorded Room B's calibration walks and the passes aborted in the room, and `idrelabel.py` later removed the extra
presses by one fixed rule, in a copy under `runs/` (never in `data/`).

## The files, in the order they ran

| file | what it does | how it runs |
|---|---|---|
| `identify_board.py` | asks each USB port which board is on it (transmitter or receiver) and its MAC; read only | `python -m pipeline.io.Capture.identify_board` |
| `rt_calibration.py` | the operator's reaction-time test, 25 presses at each of 1.0 and 1.4 m/s; writes `configs/operator_rt.json` | `python -m pipeline.io.Capture.rt_calibration` |
| `parse.py` | one `CSI_DATA` serial line into a checked record: MAC, RSSI, both clocks, the 256-byte channel payload (128 values) | imported by `capture_logger.py` |
| `capture_logger.py` | one reader thread per receiver, the packet-rate and loss checks, the `.bin` files; on its own it records the 60 s empty-room baseline | `python -m pipeline.io.Capture.capture_logger --duration 60 --out <folder> --nodes <RX1=...,RX2=...,RX3=...> --reset` |
| `anchors.py` | the twelve paths, each one's six taped crossings, start and end, the 25 grid cells and the session plan | `python -m pipeline.io.Capture.anchors` prints the paths |
| `ground_truth.py` | the recording-day logger: the capture and the presses on one clock, the walks and dwells in a seeded order, the `.gt.json` sidecar | `python -m pipeline.io.Capture.ground_truth --participant <code> --room A --session 01 --dry-run` prints a session's plan without the boards |
| `capture_idpath.py` | Room B identification walks on line A: a slot per person, natural, slow and fast blocks, RX2 at its identification spot (drives `ground_truth.py`'s walk mode) | `python -m pipeline.io.Capture.capture_idpath --help` |
| `capture_idboth.py` | the same, line A in both directions | `python -m pipeline.io.Capture.capture_idboth --help` |
| `dc2b_manifest.py` | writes `data/room_B/calibration.json` at capture time: the calibration recordings and the passes aborted in the room; only ever adds | `python -m pipeline.io.Capture.dc2b_manifest --show` |
| `idrelabel.py` | the Room B identification press relabel: a press 0.3 s or less after the one before is an extra press; a manifest of every change and a relabelled copy under `runs/identify/` | `python -m pipeline.io.Capture.idrelabel --help` |
| `clean.py` | amplitude, the receivers' clocks on the host clock, resampling and the baseline, for `windows.py` | imported by `windows.py` |
| `windows.py` | the labelled 2 s windows of every recording (above) | `python -m pipeline.io.Capture.windows --out <folder>`; give `--out` outside `data/`, as its default is `data/windows` |
| `inspect_capture.py` | whether a capture holds real CSI: frames, rate, RSSI, dead subcarriers, a verdict per file | `python -m pipeline.io.Capture.inspect_capture data/room_A/session_01/<capture folder>` |
| `check_gain_lock.py` | whether the receivers' gain lock held, from a near and a far capture | `python -m pipeline.io.Capture.check_gain_lock <near> <far>` |
| `check_channel_filter.py` | whether the radio's channel filter bends the shape across subcarriers, from a near and a far capture | `python -m pipeline.io.Capture.check_channel_filter <near> <far>` |

The commands that record (`rt_calibration`, `capture_logger`, `ground_truth` without `--dry-run`, `capture_idpath`,
`capture_idboth`) need the boards. None of them writes into an existing recording: `ground_truth.py` refuses a name
that is already taken unless `--redo` is given. The shared recordings use the codes PA1 to PA6 in their names.
