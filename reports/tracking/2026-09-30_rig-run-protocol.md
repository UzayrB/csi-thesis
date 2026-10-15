# The rig run: the streamed demonstration, and the boards as the plugged-in path. 30 September 2026

**This replaces, for the demonstration:**
- `reports/RIG_RUN_PROTOCOL_2026-09-29.md`;
- its addendum `reports/RIG_RUN_PROTOCOL_ADDENDUM_2026-09-30.md`.

Both stay as the record, and their boards procedure is carried into part B below.

**Why (Uzayr, 30 Sep).**
- **The rig run:** it is the app fed recorded B2 data, streamed in as if live. There will be no run on the
  physical boards and no new recordings.
- **The boards:** the app must still work unchanged if they were plugged in.

**The model** in both parts is the live app's final model: the 15:39 networks and readers, the frozen
configuration (`rule/FINAL_CONFIG.md`), and the semi-constrained mode (one press per walk).

## A. THE DEMONSTRATION: a B2 recording, streamed as if live

### A1. What happens

**Only the packet source is replaced.** A stand-in serial port replays each receiver of the recording.
- **The lines:** every recorded frame is written back as the firmware's base64 `CSI_DATA` row, the exact
  inverse of the parser.
- **The pace:** the rows are released at their recorded pace, in wall-clock time.

**From there on it is the plugged-in path, unchanged:**
- `run_capture`'s per-receiver reader threads, stamping each chunk on the host clock;
- the parser and the queue;
- the rate monitor;
- the rig's tracking consumer: the causal clock anchor and the final model;
- the screen.

**Nothing under `pipeline/io/` is edited.**

**The operator's key** is injected: each walk's FIRST press, as a SPACE key event at its recorded time,
stamped on the host clock when it is injected. There is no end press, since the app ends each walk itself.

**The screen** also shows the green truth marker and RIGHT or WRONG. That is a replay-only overlay, shifted
onto the stream's clock and read only by the screen.

### A2. The commands, from the repository root

```
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code

# one recording, the screen recorded to runs/live/stream/stream_B2_<stem>.mp4
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --stream B2/participant_PA2_walk --screen runs/live/stream

# all six B2 recordings, one after another, each compared with the replay of the same recording and
# re-replayed from its own capture
runs/dc2_results/stream_chain.sh runs/live/replay/final/semi_disp-K0_causal
```

**The pre-flight runs first and refuses on any failure.** It checks everything the boards' pre-flight checks.
- **The one difference:** the baseline must be recent against the RECORDING's start, not against today.
- **On B2:** each recording's own 60 s baseline was taken under a minute before it.

**Ask for a quiet machine** before a timed run. Send Identification a request, and wait for its "paused".

**What a run writes, in `runs/live/stream/B2__<stem>/`:**
- `log.jsonl`: every output of the app with its wall-clock time;
- `summary.json`: the measurements below;
- `capture/`: exactly what the app received, written by the boards' own capture writer, with a sidecar
  holding the injected presses;
- `rereplay.json`: that capture replayed through the harness;
- the video, in `runs/live/stream/`.

### A3. What to expect (measured, 30 Sep, a quiet machine)

**The run:** the six B2 recordings (`runs/live/stream/`, 22:23 to 23:25). Details are in
`reports/LIVE_APP_BRIEF2_2026-09-30.md` section 5d.

| | measured |
|---|---|
| packets | 968,652 parsed, 0 dropped; every receiver PASSED the capture's gates |
| per-window service | median 0.097 s, p99 0.26 s, maximum 0.28 s (the stride is 0.5 s) |
| a lock frame, against press + 2.0 s | 0.13 s late (median); the session's FIRST lock 0.7 to 2.1 s late |
| the committed line, after the walk's end | 1.1 to 1.5 s (median), 2.8 s at most |
| frames computed late | 24 % over 0.1 s and 10 % over 0.5 s, around the presses (a press costs 0.9 s) |
| the screen | 68 % of 10 redraws a second; the screen and the model share one thread |
| the decisions, against a replay of the same recording | 120 / 120 committed lines, 114 / 120 locks (the stream's millisecond timing moves six borderline locks); the stream's own capture replays to identical outputs |

### A4. Every difference from a plugged-in run

1. **The packet source:** replayed rows in place of the UART.
2. **The key source:** an injector thread in place of the terminal key reader.
3. **No board reset:** no reset and no boot banner, as the rig itself runs.
4. **The read timeout:** the replay port emulates the serial read timeout.
5. **The truth overlay on the screen:** replay-only; a live run has none.
6. **The pre-flight's baseline age:** judged against the recording's start.

## B. THE PLUGGED-IN PATH: the boards (unchanged; carried from the 29 Sep protocol and its addendum)

**The setup (as DC2):**
- TX at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at HOME (-0.5, 2.5), RX3 at (5.5, 2.5);
- the boards found by station MAC: RX1 68:09:47:4c:ef:b4, RX2 20:50:0d:1a:28:74, RX3 20:50:0d:30:5f:80;
- channel 11, HT20, about 150 packets a second.

```
scripts/live_rig_run.sh --dry-run                                        # the ports, by MAC
NODES="RX1=/dev/cu.usbserial-<a>,RX2=/dev/cu.usbserial-<b>,RX3=/dev/cu.usbserial-<c>"
make run DURATION=20 NODES="$NODES"                                      # optional radio check
make baseline BASELINE_S=60 OUT=runs/live/baselines NODES="$NODES"       # 60 s, room empty, operator still
BASE=$(ls -td runs/live/baselines/2026*/ | head -1)
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live preflight --baseline "$BASE"
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --baseline "$BASE" --minutes 20
```

**The capture protocol:**
- **Before the first walk:** at least 15 s of stillness.
- **Each walk:** ONE SPACE at the start tape, in the semi-constrained mode. The app ends the walk itself.
- **Between walks:** at least 5 s of stillness.
- **To stop:** press q.

The fully constrained mode (start and end presses) is `python3 -m pipeline.live.final_model rig --baseline
"$BASE" --mode full`.
