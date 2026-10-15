# The rig run on the boards: commands and capture protocol (Uzayr's part C)

Written 29 September 2026, 23:13 SAST, from the code: `pipeline/live/__main__.py`, `pipeline/live/final_model.py`,
`Makefile`, `scripts/live_rig_run.sh` and `reports/DC2_DAY_PLAN_2026-09-24.md`.

**The model.** The rig runs the **15:39 model**:
- `pipeline.live rig` defaults to `--model final`;
- `final_model.py` reads the decode variant from `runs/dc2_results/rule/FINAL_CONFIG.md`, and refuses if its
  hash has changed.

V2 is not wired into the live path. It stays so until it has been reviewed and approved.

**Where it runs.** In either room, because nothing is re-anchored per room:
- the networks, readers and constants come from A1+A2+B1;
- the per-recording statistics come from the recording's own idle radio before its first press.

## 1. The setup (as DC2)

**Positions** (metres, origin at the bottom-left corner of the taped 5 m x 5 m grid):
- TX at (2.5, -0.5);
- RX1 at (2.5, 5.5);
- **RX2 at its HOME position (-0.5, 2.5).** Not the identification spot: tracking needs RX2 at home;
- RX3 at (5.5, 2.5).

**The boards.** The rig finds them by station MAC: RX1 68:09:47:4c:ef:b4, RX2 20:50:0d:1a:28:74,
RX3 20:50:0d:30:5f:80. Use the same transmitter, at channel 11, HT20, about 150 packets a second.

**The operator** sits at the desk, in the chair at (-1.0, 0.5) as in DC2, and stays seated and still
during the baseline.

**The machine.** Identification's jobs share it. The live timing (94 to 97 ms median per window) was
measured with them running, so pausing them is not required. To be safe during a demonstration, ask the
Identification chat to pause its lane first.

## 2. The commands, from the repository root

```
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code

# (a) the boards, identified by MAC; prints each receiver's port and captures nothing
scripts/live_rig_run.sh --dry-run
NODES="RX1=/dev/cu.usbserial-<a>,RX2=/dev/cu.usbserial-<b>,RX3=/dev/cu.usbserial-<c>"

# (b) optional radio check, 20 s: every link near 150 Hz, under 5 % lost
make run DURATION=20 NODES="$NODES"

# (c) the empty-room baseline, 60 s: nobody in the grid, operator seated and still
make baseline BASELINE_S=60 OUT=runs/live/baselines NODES="$NODES"
BASE=$(ls -td runs/live/baselines/2026*/ | head -1); echo $BASE

# (d) the pre-flight: every line must read "ok", ending with "ok   ALL"; it opens no port
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live preflight --baseline "$BASE"

# (e) the rig: opens the serial ports and the screen; q stops it
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --baseline "$BASE" --minutes 20
```

**About (c).** The baseline goes under `runs/live/baselines/`, not `data/`: a live run is not a DC2
session, and `data/` stays untouched.

**What (d) checks:**
- the FINAL_CONFIG hash;
- the frozen A1+A2 pace;
- the 133 hashed model files;
- the display head;
- both replay gates;
- the reader map;
- a baseline holding RX1, RX2 and RX3, **less than 120 minutes old**. Take a fresh one after moving any
  receiver, or after two hours.

**What (e) does.** It runs the pre-flight again and refuses if anything fails. It writes
`runs/live/rig/rig_final_<date>_<time>.json`: the decisions, the timing and the recording's statistics.

## 3. The capture protocol

**1. Before the first walk: at least 15 s of stillness.**
- **What to do:** the room is empty except for the participant, who stands still a step or two behind
  the first line's start tape (the operator seated). Start the rig, then wait **at least 15 s, better 20 s,** before
  the first press. Nobody moves in or near the grid.
- **Why 15 s.** The recording's statistics are fixed at the first press from the windows centred more
  than 3 s before it:
  - the relative RSSI and the gate reference;
  - the abstain reader's adaptation.

  The rig needs at least 10 such windows, about 9 s, and refuses below that. The adaptation needs 20,
  about 14 s; below 20 the abstain reader runs unadapted.
- **What spoils it:** anything moving in that period.

**2. Each walk: two presses.**
- **The walk:** the participant walks one of the 12 taped lines, in its direction, at their natural
  pace. They start a step or two before the start tape, so they are walking as they cross it, as in the
  recordings.
- **The first SPACE,** the start press: at the moment the walker crosses the line's start tape (0 m).
  The decoder is told only this.
- **The second SPACE,** the end press: at the end tape. It ends the drawn walk and places the next
  window boundary. The decoder is never told it; the walk ends by its own causal exit.
- **Order:** any lines, in any order. Each A to D line twice and each E line once is the recorded
  protocol, but it is not required.

**3. Between walks.** The participant stops, stands still for **at least 5 s** (the recordings left several seconds between walks),
and then walks the next line. Stillness lets the motion gate read "still", so the decoder can close the
walk.

**4. What the screen shows** (V1 to V3):
- the dot, 2.0 s behind real time;
- the lock, 2.0 s after each start press;
- at most one marked mid-walk switch;
- at the walk's end, the committed line as text.

Live, there is no green truth marker, because no ground truth is recorded.

**5. To stop:** q. Then read the summary in `runs/live/rig/`.

## 4. Figures to expect

These are the test figures of the 15:39 model on 120 walks per session: they tell you roughly what to
expect, not what a live run will score.
- **B2:** committed 93.33, lock 72.50.
- **A3:** committed 93.33, lock 70.83 (the A3 lock is optimistic).

**Where the lock errs.** The lock is weakest on lines that share a start corner: C_fwd with E_col1, D_fwd
with E_row5, and D_rev with E_col5. A wrong lock stays on screen, and the end text shows the committed
line.
