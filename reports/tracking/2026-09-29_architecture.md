# How the final tracker works: the architecture, stage by stage

Written 29 September 2026, 21:22 SAST, for Uzayr. It describes the CORRECTED final tracker
(`reports/MODEL_FINAL_TRACKING_CORRECTED.md`, configuration frozen in `runs/dc2_results/rule/FINAL_CONFIG.md`).

**How it was written.** Every statement below was read from the code that produced the test figures,
not from earlier reports. File and function names are given at each step, so any statement can be
checked. Where the code and an earlier document disagree, the code is followed and the disagreement is
noted in section 17.

**Participants are coded P1 to P6** with the teaching pack's map (`runs/dc2_results/teaching/anon_map.json`,
which stays out of the report). The repository's own file names still carry the names.

**Corrected 29 September, 22:40,** before the first commit of this report:
- the worked gate example in 8.2 is P5's recording (it had named the wrong one);
- the start terms never reach the display lock (10.1, 10.2, 12.1, 17.1).

**Nothing new was run for it.** No decode, no training and no new A3 or B2 figure. The only numbers it
adds are counts read from saved rows, such as the per-line accuracies and confusions in section 15.

**Where to find what:**
- sections 0 to 16: how the model works, stage by stage;
- section 17: what was found while tracing it that bears on decisions;
- section 18: the files;
- **section 19:** everything done to the model on 29 September, in order;
- **section 20:** its current state, and what is open.

---

## 0. The whole system on one page

```
 ESP32 TX (2.5, -0.5) ──ESP-NOW broadcast, channel 11, HT20, ~150 packets/s──┐
                                                                             │
 RX1 (2.5, 5.5)   RX2 (-0.5, 2.5)   RX3 (5.5, 2.5)   each: 128 complex CSI values + RSSI per packet
       │                │                 │
       └── USB serial, one host process, one monotonic clock ── operator SPACE presses (6 per pass)
                                   │
 1  PARSE          CSI_DATA rows -> int8[256] -> 128 amplitudes; RSSI in dBm; device and host times
 2  CLEAN          per receiver: drop 21 dead bins -> 107; per-packet two-half shape normalisation;
                   Hampel despike; linear resample to 150 Hz on a shared grid; empty-room baseline
                   shape subtracted
 3  WINDOW         2 s (300 samples) x 107 subcarriers x 3 receivers, every 0.5 s, the lattice
                   re-phased so a window STARTS on each start press; labelled by the window centre
 4  FEATURES       per link: channel 0 = 2 Hz zero-phase lowpass of the shape deviation (300 x 107);
                   channel 1 = RSSI(t) minus the recording's idle mean, broadcast over 107 columns;
                   plus one scalar per window: the 0.3 to 2 Hz band energy (the motion gate)
 5  FIVE NETWORKS  each: ONE shared CNN encoder applied to all 3 links -> 3 x 64-d -> fusion layer
                   -> posterior over 25 one-metre cells (one head: 100 half-metre cells)
 6  POOL           per head: log p(cell) - log p_train(cell); mapped onto 288 states along the 12
                   taped lines; equal-weight mean of the 5 heads; best state set to 0 each window
 7  GATE AND NULL  band energy x max(1, G0 / g_rec) against 0.431: walking or still; STILL and
                   TRANSIT states scored -7.5 +- 4 nats; all line states forbidden when still
 8  START READERS  at each start press: A2 region reader (position heads, LDA over 8 start regions,
                   weight 0.25) and the abstain reader (AdaBN embeddings, LDA, used only when >= 0.90
                   sure, weight 0.25)
 9  DECODER        418-state HMM, told only when a walk STARTS: soft entry in the first 1 m of every
                   line; walks forward along a line at ~0.65 m per window; the walk ends when the
                   forward decode's best state is off every line (causal exit)
10  OUTPUTS        COMMITTED line: at the exit, per-line Viterbi totals + chain prior + start terms,
                   best family then best member.
                   DISPLAY LOCK: at press + 2.0 s, the line of a fixed-lag display decode.
                   THE DOT: that decode's position, then the locked line's restricted decode, drawn
                   2.0 s behind real time.
```

The three things the system reports per walk:

| output | when it exists | what it is | test figure (A3 / B2) |
|---|---|---|---|
| **committed line** | at the causal exit, about the end of the walk | which of the 12 taped lines was walked, decided on the whole walk | 93.33 / 93.33 |
| **display lock** | press + 2.0 s, on every walk | the line the dot is locked to on screen | 70.83 (optimistic) / 72.50 |
| **the dot** | every display frame, 2.0 s behind real time | a decoded position on a taped line | 0.32 / 0.37 m median error on walks whose lock is right |

Chance is 1 in 12, 8.33 percent.

---

## 1. The physical system and the protocol

### 1.1 Room, boards and geometry

**The frame** is the same in both rooms. Metres, x to the right, y up, origin at the bottom-left corner of
the taped 5 m x 5 m grid. Every sidecar records the positions below, identically in Room A and Room B
(`data/room_*/session_*/*.gt.json`, key `geometry`).

| node | position (m) | role |
|---|---|---|
| TX | (2.5, -0.5) | one ESP32, broadcasting ESP-NOW frames; 0.5 m south of the grid |
| RX1 | (2.5, 5.5) | north receiver; link 0 is TX to RX1 |
| RX2 | (-0.5, 2.5) | west receiver; link 1 |
| RX3 | (5.5, 2.5) | east receiver; link 2 |

**The radio settings,** read from a B2 capture file (`participant_P4_walk_RX1.bin`):
- channel 11, no secondary channel, 20 MHz (bandwidth 0);
- HT frames (sig_mode 1, rx_format 1), MCS 0, rate index 11;
- 47-byte frames, antenna 0;
- **149.6 packets per second** (54,330 frames in 363 s);
- RSSI between -87 and -71 dBm in that recording.

**Each receiver** runs Espressif's `esp-csi` receive firmware in the project's base64 format
(`pipeline/io/parse.py`). A row carries:
- 25 metadata fields: RSSI, rate, noise floor, channel, the receiver's own microsecond timestamp and
  others;
- the gain factor;
- 256 int8 values: 128 complex pairs, imaginary first, which are the legacy LTF (64 subcarriers) then
  the HT-LTF (64).

The transmitter's packet counter is shared by all receivers, so a gap in it is that receiver's drop.

**Amplitude only; phase is never computed.** The receivers' automatic gain control removes absolute
level before anything is stored. It was measured on 8 September: -11.8 dB of received power became
-0.5 dB of recorded amplitude. So only the SHAPE across subcarriers carries information
(`pipeline/clean/common.py`, module docstring).

### 1.2 The twelve taped lines

From `pipeline/constrained/paths.py`. The coordinates are read from the first sidecar naming each line,
and every sidecar records identical coordinates.

| line | start -> end | length | states | family (parallel lines) | decision group | start region |
|---|---|---|---|---|---|---|
| A_fwd | (2.5, 0) -> (2.5, 5) | 5.0 m | 21 | vertical | vert | S_mid |
| A_rev | (2.5, 5) -> (2.5, 0) | 5.0 m | 21 | vertical | vert | N_mid |
| B_fwd | (0, 2.5) -> (5, 2.5) | 5.0 m | 21 | horizontal | horz | W_mid |
| B_rev | (5, 2.5) -> (0, 2.5) | 5.0 m | 21 | horizontal | horz | E_mid |
| C_fwd | (0, 0) -> (5, 5) | 7.071 m | 30 | diagonal | diagC | SW |
| C_rev | (5, 5) -> (0, 0) | 7.071 m | 30 | diagonal | diagC | NE |
| D_fwd | (0, 5) -> (5, 0) | 7.071 m | 30 | diagonal | diagD | NW |
| D_rev | (5, 0) -> (0, 5) | 7.071 m | 30 | diagonal | diagD | SE |
| E_col1 | (0.5, 0) -> (0.5, 5) | 5.0 m | 21 | vertical | edge | SW |
| E_col5 | (4.5, 0) -> (4.5, 5) | 5.0 m | 21 | vertical | edge | SE |
| E_row1 | (0, 0.5) -> (5, 0.5) | 5.0 m | 21 | horizontal | edge | SW |
| E_row5 | (0, 4.5) -> (5, 4.5) | 5.0 m | 21 | horizontal | edge | NW |

**The states.** Each line is cut into states every 0.25 m of arc length: 21 on a 5 m line, 30 on a
diagonal (28 full steps and a short last one, so the chain ends on the last tape mark). That gives
**288 line states in all.**

**The families and groups.** There are three families of parallel lines (vertical, horizontal,
diagonal). The committed decision groups them differently, into five DECISION GROUPS, with the four
edge lines together: vert, horz, diagC, diagD and edge.

**The start regions.** A start region is the nearest of 8 points (the 4 corners and the 4 edge
midpoints). **Three regions are shared:**
- SW holds C_fwd, E_col1 and E_row1;
- SE holds D_rev and E_col5;
- NW holds D_fwd and E_row5.

This matters for the lock (section 17.1).

### 1.3 Sessions, recordings and passes

| session | room | day | used for | recordings |
|---|---|---|---|---|
| A1 (`session_01`) | A | 1 | training | 6 participants x one walk recording |
| A2 (`session_02`) | A | 2 | training | 6 x one walk recording |
| A3 (`session_03`) | A | 3 | **test only** | 6 x `participant_<name>_TEST_walk` |
| B1 (`session_B1`) | B | 1 | training | 6 x walk recording, plus `participant_P5_C_walk` (calibration, 11 passes, **excluded from training**) |
| B2 (`session_B2`) | B | 2 | **test only** | 6 x walk recording, plus `participant_P6_C_walk` (calibration, 8 passes, **not evaluated**) |

**The walk recordings.** Each holds **20 passes**: every A to D line twice and every E line once, in a
shuffled order (`path_order` in the sidecar). The six participants are coded P1 to P6.

**How the rooms' recordings differ:**
- Room A recordings run `walk_half, grid, walk_half`: ten passes, a 25-cell standing block, then ten
  more.
- Room B recordings are `walk_only`.
- The Room A `DEMO_free` free-movement recordings are never used.

**Each recording has an empty-room baseline capture**, a separate directory named in the sidecar
(`baseline_capture`).

**Totals:**
- **360 training passes:** A1, A2 and B1, 120 each.
- **240 test passes:** A3 and B2, 120 each.
- The calibration recordings are neither trained on nor evaluated.

---

## 2. Capture and ground truth (`pipeline/io/`)

**Capture** (`capture_logger.py`). One reader thread per receiver, at 921,600 baud, feeds one bounded
queue. Readers never block: a full queue drops a counted frame rather than stalling the UART.
- **Parsing:** each row is parsed by `parse.parse_line`, which never raises. A malformed line is counted
  in one of six rejection counters and dropped. The B2 file above had 54,409 lines, 54,330 of them
  good, 79 non-CSI log lines, and 0 to 1 malformed per receiver.
- **Storage:** each receiver's frames go to `<stem>_RX<n>.bin`: an 8-byte magic `CSIBIN01`, a JSON
  header, then fixed records. Each record holds host time, host monotonic time, packet id, device
  timestamp, RSSI, noise floor, the PHY fields, the gain, and the 256 int8 CSI values.
- **The run summary** is `<stem>_run.json`, with drop percentages per receiver (0.29 percent on RX1 in
  that file).

**Ground truth** (`ground_truth.py`, in the SAME process, so presses share the CSI's monotonic clock).
- **Six anchors per pass.** The operator presses SPACE as the walker crosses each of six equally spaced
  tape marks along the line: every 1 m on a 5 m line, and every (1, 1) m step on a diagonal. The
  sidecar stores each pass's `anchor_times` (six raw press times) and `anchor_coords`.
- **The first anchor is the START PRESS; the last is the END PRESS.** `t_start` and `t_end` are the pass
  boundaries.
- **The operator's reaction time** was measured separately (`configs/operator_rt.json`: bias 40.6 ms,
  sd 43.6 ms for the Room B sessions) and is recorded in the sidecar. **The offline labels do not
  subtract it** (section 4.3).
- **Validation.** A pass is flagged if any implied speed between anchors is above 4.0 m/s (a missed
  press) or below 0.3 m/s (a spurious one).

**Worked example of one pass** (B2, pass 2 of the teaching pack, C_fwd). Presses at 0.00, 0.97, 2.07,
3.16, 4.30 and 5.48 s. That is 7.071 m in 5.48 s, 1.29 m/s.

---

## 3. Cleaning, per receiver (`pipeline/clean/common.py`, `clean_arrays`)

The same chain runs on every receiver file, in this order. The order is deliberate: normalisation comes
before any time-domain step, so gain switches cannot become edges.

| step | function | what it does | parameters |
|---|---|---|---|
| 0 time base | `anchor_times` (via `splits.windows.load_node`) | fits one line from the receiver's 32-bit microsecond clock to the host monotonic clock over the whole file (wraps and reboots handled; a fit more than 500 ppm from nominal is refused); stale packets from a previous boot are dropped | |
| 1 amplitude | `load_node` | sqrt(imag^2 + real^2) for each of the 128 pairs | gain factor 1.0 in these captures |
| 2 dead bins | `select_subcarriers` | removes 21 structurally empty bins: the legacy LTF nulls (0, 27 to 37), the HT-LTF nulls (64, 93 to 99), and the invalid first word (0, 1) | **107 live subcarriers**: 51 legacy, 56 HT |
| 3 shape | `normalise_shape` | **each HALF of each packet divided by its own mean** (legacy and HT separately, because the AGC re-trains between the two preambles) | a half with mean below 1e-3 becomes zeros |
| 4 despike | `remove_outliers` | Hampel filter on the packets: a value more than 4 robust sigmas (1.4826 x MAD) from the median of its 21-packet neighbourhood is replaced by that median; everything else is untouched | window 10 each side, 4.0 sigma |
| 5 resample | `resample_uniform` | linear interpolation onto a uniform 150 Hz grid whose origin is absolute host time 0, so all three receivers share one lattice | 150 Hz; refuses if more than 5 percent of stamps are duplicated |
| 6 baseline | `subtract_baseline` | subtracts the session's empty-room baseline SHAPE, per subcarrier. The baseline is the median over the baseline capture after steps 1 to 4 (`session_baseline`, `baseline_shape`) | per receiver, per recording's named baseline |

**Output per receiver:** `(n_samples, 107)` shape deviations from the empty room, near 0 when nobody is
there, plus the gap between the source packets bracketing each sample.

**Not done, by design:**
- no bandpass;
- no PCA;
- no temporal mean removal. A subcarrier's slow drift IS the position signal.

---

## 4. Windows, the lattice and the labels (`pipeline/splits/windows.py`, `pipeline/constrained/y4_pressalign.py`)

### 4.1 The window

**Shape.** A window is **2.0 s = 300 samples x 107 subcarriers x 3 receivers**, stored as float16. It
was measured before being chosen: median relative error 1.7e-4, and the gate band energy shifts by at
most 1.3e-4.

**Metadata.** Each window carries:
- its absolute start time and its wall-clock time;
- its mode and pass id, and the line name;
- its interpolated position;
- the pass's mean speed;
- the longest packet gap under it on any receiver, with a flag if that exceeds the verified 0.25 s.

### 4.2 The lattice: 0.5 s stride, re-phased on every start press

**The base lattice** is every multiple of 0.5 s from the first instant all three receivers cover
(`window_starts`).

**The final model uses the PRESS-ALIGNED lattice** (`y4_pressalign.pa_starts`):
- The recording is split into segments, one per pass. Segments meet halfway between one pass's end
  press and the next pass's start press.
- Within a segment the whole lattice is shifted by one constant, at most 0.25 s either way, so a window
  STARTS exactly 2 microseconds after that pass's start press.
- The 2 microseconds make the window whose CENTRE is the press come out as a walk window, not by float
  rounding.
- Windows that would leave the data or overlap their predecessor are dropped.

**What the alignment gives.** The first walk window of every pass (`lo`) starts exactly 1.0 s before
the press, so its centre IS the press. Window `lo + 2` then ends exactly at press + 2.0 s, the lock
frame (section 12).

### 4.3 The labels (`label_window`)

| mode | rule | used for |
|---|---|---|
| `walk` | the window's MIDPOINT lies between the pass's first and last anchor presses | training labels, evaluation |
| `walk_edge` | not walk, but the midpoint is within 3.0 s of a pass boundary (the run-up and run-out) | never a training label |
| `idle` | everything else | the per-recording statistics (section 5.3) |
| `grid` | inside a standing-block dwell (Room A only) | not used by the tracker |

**The position label** of a walk window is the linear interpolation of the six anchors at the window's
midpoint (`_interp_xy`). It uses the **raw press times: the operator's 41 to 51 ms reaction bias is NOT
subtracted.** This is about 5 to 7 cm along the direction of travel. It is disclosed in the code, and
largely cancels between forward and reverse passes (`reports/v2/label_uncertainty.md`).

**The cell label** is `cell_index(xy)`:
- 25 cells of 1 m: index = row x 5 + col, with row = floor(y) and col = floor(x);
- or 100 cells of 0.5 m for the g100 head;
- clipped to the room.

**A typical pass.** A 5 m line walked at 1.3 m/s gives about 8 walk windows; a diagonal about 11.

---

## 5. Features

### 5.1 The CSI channel (`pipeline/constrained/features.py`)

Per link, a **zero-phase 4th-order Butterworth lowpass at 2 Hz** (`sosfiltfilt`, pad 108 samples) over
the 300 x 107 window. DC passes unchanged.

**What it keeps:**
- **kept:** the slowly varying shape of the fading pattern across subcarriers, which is where position
  lives;
- **removed:** fast fluctuations above about 2 Hz, the gait and limb motion.

The result is cached per recording (`load_features`: shape `(n, 3, 300, 107)`, float32).

### 5.2 The RSSI channel (`features.rssi_series`, `pd_cells.install_rrel`)

**The series.** Each receiver's per-packet RSSI (dBm) is interpolated onto the window's own 300 sample
times, using the host receive time. It is not averaged: the shadowing swing over the 2 s is the signal.

**RELATIVE RSSI (the final model's D2 change).** Each recording's RSSI has its own **per-link mean over
its idle windows before its first press** subtracted (`prn_stats.json`). So a link sits near 0 dB when
the room is quiet.

**Why it was needed.** The idle levels move by several dB from recording to recording. B1's RX2 idle
mean ranges from -84.1 to -68.1 dBm across its seven recordings, and B2's from -85.9 to -77.1. The
networks would otherwise learn a recording's absolute level.

### 5.3 The per-recording statistics: "idle windows before the first press"

`u1_adapt.calibration_indices` selects them:
- windows that **end at or before the recording's first start press**; and
- whose mode is `idle`, which excludes the first pass's own run-up (walk_edge).

**Idle windows per recording.** From 17 to 68 across the test recordings; B1's calibration recording
has 159. The per-recording counts are in `prn_stats.json`.

**These windows are pre-pass data from the recording itself, so every statistic below is causal.** Three
things are fixed from them:
- the relative-RSSI means (5.2);
- the gate's reference g_rec (section 8);
- the abstain reader's AdaBN statistics, when there are at least 20 windows (section 10.2).

### 5.4 The network input

**Per link:** `nets.stack_link` stacks the two channels into a `(2, 300, 107)` tensor:
- channel 0: the lowpassed shape;
- channel 1: the relative RSSI series repeated across all 107 columns.

**All three links:** `pd_arch.stack_all` makes `(3, 2, 300, 107)` per window.

**Standardisation.** Per link AND per channel, with the mean and sd over the training windows
(`pd_arch.link_stats`, axes (0, 3, 4)). Each link has its own statistics, even though the encoder is
shared. For the `half` head:

| link | CSI mean / sd | relative RSSI mean / sd (dB) |
|---|---|---|
| 0 (RX1) | 0.00013 / 0.147 | 0.006 / 1.91 |
| 1 (RX2) | 0.00031 / 0.238 | -0.100 / 2.07 |
| 2 (RX3) | 0.00006 / 0.197 | 0.070 / 1.25 |

### 5.5 The motion-gate statistic (`recordings.gate_energy`, `pipeline/branches/gate.band_energy`)

One scalar per window, computed on the CLEANED window (section 3, before the lowpass):
1. subtract each subcarrier's own mean over the window;
2. take the FFT along time. With 300 samples at 150 Hz the bins are 0.5 Hz apart, so the band is the
   0.5, 1.0, 1.5 and 2.0 Hz bins;
3. sum the power in **0.3 to 2.0 Hz**;
4. average over subcarriers and links.

Measured on Room A: a median of 1.247 on a taped path, 0.489 between paths.

---

## 6. The five tracking networks (`pipeline/constrained/pd_arch.py`, `pd_train.py`, `pd_cells.do_train_d2`)

### 6.1 One network, layer by layer

Each head is a `SharedNet(n_links=3, out_dim=cells, mode="fuse", in_channels=2)`.

**The encoder** is one `LinkCNN` (`pipeline/models/link_cnn.py`), applied to all three links. The links
are folded into the batch, so BatchNorm statistics are pooled across links.

| layer | output per link |
|---|---|
| input | 2 x 300 x 107 |
| Conv 5x5 (pad 2), 16 channels; BatchNorm; ReLU; MaxPool 2 | 16 x 150 x 53 |
| Conv 5x5, 32; BatchNorm; ReLU; MaxPool 2 | 32 x 75 x 26 |
| Conv 5x5, 48; BatchNorm; ReLU; MaxPool 2 | 48 x 37 x 13 |
| crop to a multiple of 3 | 48 x 36 x 12 |
| adaptive average pool to 3 x 3; flatten | 432 |
| Dropout 0.2; Linear 432 -> 64 | **64-d embedding** |

**The encoder has 80,000 parameters** (checked: 816 + 32 + 12,832 + 64 + 38,448 + 96 + 27,712).

**The heads on top** (`IDHead`: Dropout 0.2, then Linear):

| head | input | output | parameters |
|---|---|---|---|
| fusion head (the output used) | the three embeddings concatenated in receiver order, 192 | cells | 4,825 at 25 cells; 19,300 at 100 |
| auxiliary head, shared by the links | each link's 64-d embedding | cells, per link | 1,625 at 25; 6,500 at 100 |

A 25-cell network has **86,450 parameters** in all, and the 100-cell one 105,800.

**The loss** is the fusion head's cross entropy plus the mean of the three auxiliary cross entropies
(`shared_loss`).

**At inference** the fusion head's softmax is the posterior (`prob`). The auxiliary softmaxes are stored
as `per_link` and are not used by the decode.

**Storage.** The same weights are saved under three per-link file names, which the loaders expect; the
three files are byte-identical.

### 6.2 The five heads

| head | trained on windows at | classes | seed | training windows (A1 / A2 / B1) | minutes |
|---|---|---|---|---|---|
| `half` | 0.5 s stride | 25 (1 m) | 0 | 3,428 (1,122 / 1,128 / 1,178) | 9.6 |
| `fh1s` | 1 s stride | 25 | 0 | 1,615 (526 / 535 / 554) | 4.5 |
| `g1s1` | 1 s stride | 25 | 1 | 1,615 | 4.5 |
| `g1s2` | 1 s stride | 25 | 2 | 1,615 | 4.4 |
| `g100` | 1 s stride | 100 (0.5 m) | 0 | 1,615 | 4.5 |

**Which windows.** Training uses every `walk` window with a finite position in the training sessions
(`dataset.walking_windows`). Calibration recordings are refused by assertion; so is any test session.

**Two strides, one input.** The 1 s heads train on 2 s windows cut every 1 s:
- Room A: `data/windows/room_A`, on the base lattice (not press-aligned);
- Room B: `runs/constrained/windows_s1.0_dc2`.

ALL heads are then applied to the 0.5 s press-aligned windows. The input is the same object, a 2 s
window; only the phase differs.

### 6.3 Training (`pd_train.fit_link` with `arch="fuse"`)

**The recipe:**
- Adam, learning rate 1e-3, weight decay 1e-4;
- batch 64, **24 epochs**, no early stopping, no mixup;
- batch order from `np.random.default_rng(seed)`, with the augmentation randomness from a separate
  generator (seed + 7919).

**Augmentation, per batch, on the RAW input before standardisation:**
- **RSSI offset:** uniform +-5 dB, drawn per window and per link, added to channel 1;
- **CSI-shape scale:** log-uniform x0.25 to x1.5, per window and per link, on channel 0;
- **time shift:** an integer shift of up to +-37 samples (+-0.25 s), the same for the three links of a
  window, with edges replicated;
- then, after standardisation, **Gaussian noise** with sd 0.1.

**Device.** The GPU (Apple MPS) when free. The final heads were trained on 29 September, 08:58 to
09:26, one head after another (the `train_*.json` records).

### 6.4 One set of weights, two test cells

`fin_A3` trained the heads. `fin_B2` holds **byte-identical copies** under its own tag
(`shared_models.json`). One model is tested on both rooms.

**The zero-shot model (`zsf_B2`)** is the same recipe trained on **A1+A2 only**. Its readers, marginal,
chain prior, G0 and pace also come from A1+A2 only.

---

## 7. From networks to emissions: inference and the pool

### 7.1 Inference (`dc2_run.do_infer`, `pd_arch.infer_shared`)

Every head runs over **every window of every test recording**, in time order, whatever its mode. The
result is written once per head to `cells/<cell>/art_<head>/posteriors/*_full.npz` as float32:
- `prob`: the (n, cells) posterior;
- `per_link`;
- the window times, modes, pass ids and positions.

### 7.2 One head's emission (`night_common.pairing_emissions`, `emissions.scaled_cell_emission`)

1. **g100 only:** its 100 half-metre cells are summed into the 25 one-metre cells (`g100_to_25`) and
   renormalised.
2. **Divide by the training marginal**: `log p(cell | window) - 1.0 x log p_train(cell)`. That is the
   "scaled" emission, alpha 1.0 (`rb1_truth`, `rb2c_alpha`).
   - p_train is the share of TRAINING walk windows in each cell, add-one smoothed (`cell_marginal`).
   - It removes the heads' learnt preference for the centre cells, which 8 of the 12 lines cross.
   - The marginal runs from 0.0078 in some edge cells to 0.157 in the centre cell (12).
3. **Map to states:** each of the 288 line states takes the value of the 1 m cell it lies in, so all
   states in one cell share a value (the "staircase").

### 7.3 The pool (`g3_final.shipped_pool_emissions`, `g2_multihead.pool`)

- **The heads,** in order: the 0.5 s head, the three 1 s seeds, then g100.
- **Equal weight:** the mean of their per-state log emissions. No head is weighted by its result.
- **Renormalised per window** by subtracting the window's maximum, so **the best state of every window
  scores exactly 0**.

The output is `e_path`, a (windows x 288) array of log scores for each recording. It is the only thing
the networks give the decoder.

---

## 8. The motion gate and the null states (`pd_decode.inner`, relgateU; `decoder2.stack2`)

### 8.1 The relative gate (relgateU, the final model's D3 change)

- **G0 = 0.7542.** For each Room A training recording (A1, A2), take the median band energy of its
  idle windows before the first press; G0 is the median of those medians (`gate_reference`,
  `room_a_only=True`). Room A is the energy space the threshold 0.431 was tuned in.
- **g_rec** is the same statistic for the recording being decoded: the median band energy of its own
  idle windows before its first press.
- **Scaling.** Every window's band energy is multiplied by **max(1, G0 / g_rec)**. Quiet recordings are
  scaled up; recordings are never scaled down.
- **Threshold.** A window is **still** if the scaled energy is below **0.431**, and walking otherwise.

**The scales in the test sessions** (from the decode record):

| session | per-recording scale |
|---|---|
| A3 | 1.00, 1.00, 2.22, 1.91, 1.33, 4.12 |
| B2 | 26.5, 2.42, 7.54, 5.16, 6.71, 79.7 (and 32.0 on the calibration recording) |

Room B's idle periods are far quieter than Room A's. Without this scaling, the absolute gate called Room
B's walking "still" and forbade the lines.

### 8.2 The null states and their levels

**The null rule** (`emissions.AdaptiveNullEmission`, fitted in `rb2_decoder` for the pairing A1+A2 to
A3 on its training side):

    level = reference + offset + gate_weight x [still],  with reference 0, offset -7.5, gate weight 4.0

**The reference** is the 0.75 quantile of each window's best score. The pool fixes that best score at
0, so **the reference is identically 0 and causal.**

**What each state kind scores per window** (`stack2`, split mode):

| window read as | STILL states | TRANSIT states | line states |
|---|---|---|---|
| walking | -11.5 | **-3.5** | the pooled emission (0 at the best state) |
| still | **-3.5** | -11.5 | **forbidden** (the veto: -1e18) |

**The veto.** One still window (hysteresis 1) forbids every line state for that window. A walk can only
be decoded through windows the gate reads as walking.

**A worked example** (B2 recording of P5, the teaching pack's worked example: G0 0.754, g_rec 0.100
from 33 idle windows, scale 7.54).
Window 0 of pass 2 has raw band energy 0.388. Scaled, that is 2.924, above 0.431, so it reads as
walking. STILL scores -11.5 and TRANSIT -3.5.

---

## 9. The decoder's state space and transitions (`pipeline/constrained/decoder2.py`, `decoder.py`)

**The configuration**, selected in `rb2_decoder` for the pairing A1+A2 to A3 on its training side
(A1+A2): veto on, split on, geometry on, late entry on; margin 2.0; null_self 0.8; exit after the last
1 state at 0.5; clock_max 8; tight step kernel; bout log odds -1.2755; abort cost 60.

### 9.1 States: 418

| block | count | meaning |
|---|---|---|
| line states | 288 | position along one of the 12 lines, every 0.25 m |
| STILL(p) | 13 | standing; p = the line just left (0 = none yet) |
| TRANSIT(p, k) | 13 x 9 = 117 | walking between lines; p as above, k = windows walked since standing (saturates at 8) |

### 9.2 Moving along a line (`decoder.along_log_score`, kind "tight")

**The score** of a step of d metres along a line is -0.5 ((d - v Dt) / (s Dt x sd_scale))^2:
- d below 0 is forbidden: no going backwards;
- Dt = 0.5 s (set by `night_common.shipped_pieces`);
- **the pace prior is N(1.30341, 0.11255) m/s** (the A1+A2 tape anchors, `final/PACE_A1A2.json`), so
  a window moves 0.652 m on average, with sd 0.056 m.

This score is a log likelihood of the displacement, deliberately not normalised per row: normalising
cost 19 points in the past, because it rewards being near a line's end.

| step d (m) | committed decode (sd x1) | display decode (sd x4.5, cap 0.8 m) |
|---|---|---|
| 0 | -67.1 | -3.3 |
| 0.25 | -25.5 | -1.3 |
| 0.50 | **-3.6** | -0.2 |
| 0.75 | **-1.5** | -0.1 |
| 1.00 | -19.2 | forbidden |
| 1.25 | -56.5 | forbidden |

**In practice:**
- On the committed side a line is walked in steps of 0.5 or 0.75 m per window.
- The display decode may also stand still or step 0.25 m, which lets the dot follow a slower walker.
- The 0.8 m cap forbids a step of 1.0 m or more.

### 9.3 Between lines

| transition | log score |
|---|---|
| last state of a line -> STILL(line) or TRANSIT(line, 0) (the exit) | log 0.5 = -0.69 |
| any other line state -> STILL(line) (the abort; worse than any legal on-line step) | -60 |
| STILL -> STILL, and TRANSIT(k) -> TRANSIT(k+1) | log 0.8 = -0.22 |
| STILL -> TRANSIT(p, 0), and TRANSIT -> STILL | log 0.2 = -1.61 |
| STILL -> first state of a line (only if no transit is owed) | log 0.2 - log 12 - margin 2.0 = **-6.09** |
| TRANSIT(p, k) -> a line, once k covers the minimum transit windows from p's end | -6.09 + bout log odds -1.28 = **-7.37** |
| late entry: TRANSIT(p, k) -> a state s metres into a line, if s <= v x Dt x (k+1) | the entry cost minus 1.0 nat per window of arc left unexplained |

**Where these come from:**
- **The bout log odds -1.2755** is log(0.218 / 0.782). On the training side, 61 of 282 walking bouts
  contained a pass. It is protocol dependent.
- **The minimum transit windows** between lines come from `runs/constrained/rb0_preflight/transit_geometry.json`.
  For example, A_fwd to B_fwd is 3.54 m, 2.72 s, 3 windows.

Section 17.3 notes that the transit and late-entry quantities are in 1 s units.

---

## 10. The start-of-walk readers (`q4_arms.start_terms`, `u1_adapt.session_rows`, `u2_useit`)

Two small classifiers read, at each start press, where the walk began. Each is turned into a per-line
additive term. Both work on the **eight start regions** (section 1.2). Both are fitted on rows from
the TRAINING sessions and applied to rows from the test session.

**What produces their rows** is the old per-link recipe with ABSOLUTE RSSI, not the final shared
encoder. Retraining them on the final architecture was not tried.

| rows for | come from networks trained on | tag |
|---|---|---|
| A1's passes | A2 only | `s02_to_s01` |
| A2's passes | A1 only | `s01_to_s02` |
| B1's passes | A1+A2 (the corrected map) | `s0102_to_sB1` |
| the test session's passes | A1+A2+B1 (`ph_A3`'s per-link heads, "V0") | `s0102B1_to_s03V0` / `..._sB2V0` |

**Why the rows are cross-fitted.** Every training row comes from a network that never saw that
session, so the classifier learns from rows that look like the test rows: rows from an unseen session.
That is the leak fix of 29 September (`reports/AUDIT_LEAKAGE_TRACKING_2026-09-29.md`).

### 10.1 The A2 region reader

**Features** (`q3_startclf.features`): 26 per pass, from the position heads' `xy_hat`. The position
head is a per-link regression network (Linear 64 -> 64 -> 2, smooth-L1 loss, 20 epochs).
- It reads the windows whose END lies in [press - 2.0 s, press + 1.0 s]: 7 windows.
- From the fused estimate: the mean, sd, first and last xy (8 numbers).
- From each of the 3 per-link estimates: the mean, first and last xy (18).

**Classifier.** StandardScaler, then LDA (lsqr solver, automatic shrinkage), over the 8 regions.

**The term.** For each line: 0.25 x (log P(the line's start region) - the mean over regions of log P).
- It is centred, so no line gains overall.
- Lines sharing a region get the same term.
- **The weight is 0.25**, chosen on the rotations; it was 0.5.

**Its data ends at press + 1.0 s,** which is inside the lock's 2.0 s. It feeds the committed decision
and the scorer lock (12.3). It does NOT reach the display lock: in `night_arms.night_track` the start
term (`start_adj`) is added only to the chain totals, never to the display decode's entry or path.

### 10.2 The abstain reader (in place of the old veto)

**Adaptation (AdaBN, `u1_adapt.adapt_batchnorm`).** For each recording, a copy of the per-link g25
networks has its BatchNorm running means and variances recomputed on that recording's idle windows
before its first press. All weights stay frozen.
- It runs only if there are **at least 20** such windows; otherwise the networks are unadapted.
- A3's P5 recording has 17, so it is unadapted.

**Features.** The windows ending in [press - 2.0 s, press], 5 windows, strictly before the press. Each
link's 64-d embedding is taken and the three are concatenated (192). The feature vector is the mean
over the windows plus the last window: **384 numbers.**

**Classifier.** StandardScaler, then LDA (lsqr, auto shrinkage), over the 8 regions.

**The term** (`term_abstain`):
- applied only if the classifier's top probability is **at least 0.90**;
- then 0.25 x (log P(region) - mean log P), centred, as above;
- otherwise 0 for every line.

**The threshold and weight** were chosen on the Room A selection folds A1 to A2 and A2 to A1. On the
rotations, abstain replaced the veto after the leak fix.

**Where it applies.** It feeds the **committed decision** and the scorer lock. Like A2, it never
reaches the display lock.

---

## 11. Decoding one pass: the committed line (`night_arms.night_track`, called by `pd_decode.inner`)

**The mode is semi-bounded.** The decoder is told when each walk STARTS: the start press, via the
first walk-labelled window `lo`, whose centre is the press. It is never told where the walk goes, which
line it is, or when it ends.

**Per pass:**

1. **Entry.** At window `lo` the start distribution is the pooled emission of that window, restricted
   to the **first 1.0 m of every line** (5 states per line) and normalised to its best value. Null
   states are impossible at the start.
2. **The causal exit** (`causal_end`). A forward max-product recursion runs from `lo` over the full
   418-state model: emissions from section 8, transitions from section 9. At each new window it checks
   the best state. **The walk is declared over at the first window where that best state is off every
   line** (STILL or TRANSIT).
   - It reads nothing after that window.
   - If it never fires, the walk ends at `lo` + 40 windows (20 s).
3. **The committed decision** runs at the exit over the windows `lo` to `exit`, and each term is
   computed per line:
   - **chain_viterbi:** a Viterbi restricted to that line (the tight kernel, no cap), scored as the SUM
     OF THE POOLED EMISSIONS along its best path;
   - **+ chain prior:** log(the line's share of training passes / (1/12)). A to D lines are walked twice
     per recording and E lines once, so this is **+0.182** for A to D and **-0.511** for E
     (`n2_arms.fit_chain_prior`);
   - **+ the A2 term** (10.1), **+ the abstain term** (10.2).

   Then, **family first** (`pick_line`): the decision group whose members' totals have the largest
   log-sum-exp wins (vert, horz, diagC, diagD, edge), and then its best member.

**Worked example** (B2, P5, pass 2, true line C_fwd):
- The exit fires at window 11, 5.5 s after the press. The last press was at 5.48 s.
- **The totals at commit:** C_fwd -1.30, B_fwd -17.26, E_col1 -33.88, E_row5 -35.56, and every other
  line below -41. **Committed: C_fwd.**
- **C_fwd's total** is chain_viterbi -2.52 + chain prior 0.18 + A2 term 1.04. The abstain term was 0
  because the reader was below 0.90; its top region was SE at 0.51.

---

## 12. The display lock and the dot (`pd_decode.inner`'s lock loop; `night_track` display branch; `render_display`)

### 12.1 The display decode

The same pass is decoded again with **display settings:**
- the step spread x4.5, so sd 0.253 m per window;
- a hard **0.8 m-per-window cap** on steps;
- `pd_decode` passes it the A2 term, but the lock never reads it: start terms enter only the chain
  totals (the display decode's own rescore, not used), so **the display lock uses no start term**;
- the same gate, nulls and entry.

It keeps decoding past the committed exit, up to the horizon, so the dot does not freeze while the
walker carries on.

### 12.2 The free path and the lock

**The free path** (`fixed_lag_path`) is one step per window from `lo`. Step i is window `lo + i`,
decoded by a Viterbi over windows `lo` to `lo + i + h`. h is the evidence horizon:
- The display draws 2 windows behind the newest (LAG_W = 2).
- A 2 s window needs 2 strides to finish recording (lw0 = 2).
- So h = 2 - 2 = **0**: **every drawn step uses only windows that have finished recording.**

A step that falls on a null state holds the last on-line position.

**The lock** is read at **lock step 2** = round(2.0 s / 0.5 s) - 2:
- **The lock line is the free path's line at window `lo + 2`.**
- That window **ends at press + 2.0 s**: the lock's evidence ends there, on every walk, by the lattice
  alignment.
- **Its centre, the moment it names, is press + 1.0 s,** about 1.3 m into the walk.
- If the free path is off every line there, the entry line is used; if there is none, "A_fwd" by name
  order. The decoder records which of the three was used (`lock_line_source`). The saved test rows do
  not keep that field; both worked examples read `path`.

**After the lock** (`locked_chain_path`), the dot comes from a fixed-lag Viterbi restricted to the
locked line:
- the tight kernel with the 0.8 m cap;
- the same horizon;
- started from the entry distribution restricted to that line.

Every drawn point is a decoded position ON the locked line. The dot is never projected or advanced by
pace.

### 12.3 The scorer lock (reported, not the headline)

For each line the scorer lock combines two scores and takes the largest:

    0.75 x (the display lock score: the best Viterbi score on the line at the lock's last window)
    + 0.25 x (the committed estimator's chain total from lo to that window, plus A2 and abstain)

It scores 70.00 on A3 and 71.67 on B2, against the display lock's 70.83 and 72.50.

### 12.4 How the resolution figures are measured (`pd_decode.drawn_errors`, `resolution`)

**What is compared.** On every labelled walk window, the drawn state's coordinates are compared with the
interpolated truth. Before the lock step the drawn state is the free path's; from it on, the locked
path's.

**Which emissions.** These figures use the **pooled emissions** for the locked path, with no display
phase. The video renders use the display head instead (13.2). The reported figures are therefore the
decoder's resolution, not the video's.

| figure | A3 | B2 | zero-shot B2 |
|---|---|---|---|
| all labelled walk windows (median / p90, m) | 0.51 / 3.26 | 0.53 / 2.83 | |
| walks whose lock is correct | **0.32 / 0.92** | **0.37 / 0.90** | 0.41 / 1.02 |
| along the true line, on windows drawn on it | 0.29 / 0.90 | 0.35 / 0.85 | |

The error across the line is 0 by construction on the true line: the dot always sits on a taped line.

### 12.5 Worked example of a wrong lock (B2, P5, pass 10, true C_fwd)

**At the lock** (window 2), the lock scores are:

| line | score |
|---|---|
| E_col1 | **-1.72** |
| C_fwd | -1.87 |
| E_row1 | -3.06 |
| B_fwd | -6.34 |

**The lock goes to E_col1 by 0.15 nats.** All three leading lines start at the SW corner.
- **The dot** is drawn up the x = 0.5 line while the walker goes diagonally: a median error of 2.57 m
  on that walk.
- **The committed decision** at the end reads C_fwd +0.12 against E_col1 -31.65, and is right.
- **What the viewer sees:** the display rules keep the wrong lock on screen; the end text shows the
  right committed line.

---

## 13. The demonstration renders (`pipeline/constrained/pd_render.py`, under `reports/RENDER_RULES.md`)

### 13.1 The screen rules

**Timing rules:**
- **V1, the delay.** The whole display runs **exactly 2.0 s behind real time**, and the caption says so
  (rule 3).
- **V2 and rule 6, the start.** The scene starts at the delayed start press. The red dot and the green
  truth marker appear on the same frame.
- **V3, the lock time.** The lock is at press + 2.0 s on every walk. A lock that waits longer when
  unsure is forbidden.

**What the dot may do:**
- **Rule 2a, the one exception.** At the press the dot is placed at the committed line's entry point:
  the press means the walker is at that tape. It then slides straight to the first decoded position.
  That is the only drawn point the decoder did not produce.
- **Rule 2, nothing projected.** Every other drawn point is a decoded position, or on the straight
  segment between two of them.
- **Rule 1, the lock is final,** except rule 1a arm C: at most ONE display-only switch per walk.
  - It goes only to the scorer's current best line, after that line has led by theta 2.0 for two
    consecutive steps (1.0 s).
  - It is never allowed in the final 1.5 m.
  - It uses radio only up to display time + 2.0 s.
  - The dot slides over 0.5 s and the switch is marked on screen.
- **Rule 1b, the end text,** names the committed decision. The render marks it CORRECT or WRONG, with
  the running accuracy.

**What is left out:**
- **V4:** no standing-block footage. On A3, 29,163 frames were cut.

### 13.2 The drawn position

**After the lock** the dot reads the **display head DISP_END** (`pd_dispend`):
- the final recipe (a shared encoder with fusion, augmentation and relative RSSI);
- 25 cells, trained on A1+A2+B1 only;
- **labelled at the window END**, not its centre, so it names where the walker is at the window's last
  sample.

It feeds only the restricted along-line decode after the lock. It never enters a decision.

**The display phase:**
- HEAD_OFFSET_S = 0.375 s, f4_render's pre-registered phase;
- SHIFT_W = 0.50 stride (V5): the dot is drawn half a stride along the decoded path, kept slightly
  behind the walker on purpose.

**Frames.** 10 frames per second. Both causal bounds are computed on every drawn step: had the named
window finished recording, and had the radio that decoded it? They are -1.375 s on A3 and -1.376 s on
B2, so no frame uses future radio.

### 13.3 The "decoded accuracy" in the ACCEPTANCE files

It is f3's and f4's definition: the dot against the truth 1.0 s before the frame. Under V1 that is not
the decoder's accuracy (section 17.6).

---

## 14. The live system (`pipeline/live/`, final model in `final_model.py`)

The live system reproduces the offline objects window by window. Replay gates prove it equal on
recorded sessions: A3 120/120 and B2 120/120, committed and lock (`runs/live/final/`).

### 14.1 Per packet

`rig.py` hosts the capture as an extra consumer in the capture process, so CSI and key presses share
one clock.

`stream.py` cleans and cuts windows exactly as offline:
- It waits a margin of packets after each window so the Hampel filter and the interpolation see the
  same neighbourhood (about 0.09 s).
- It **re-cuts on every start press** onto that press's phase.

`anchor.py` fits the device clock causally, refitting as packets arrive.

### 14.2 At the first press of a recording (`FinalTrackingSession._final_stats`)

The recording's statistics are fixed from the windows that ended before the first press:
- **Which windows.** Windows ending at or before the first press whose centre is more than 3.0 s from
  it; live, "idle" means that.
- **What is fixed from them:** the relative-RSSI means, g_rec, and AdaBN (if at least 20 windows).
- **At least 10 such windows** are required, or the session refuses.
- **The heads never run before the first press;** earlier windows are provisional and are re-cut by it.

### 14.3 Per window, in causal order (`tracking.py`)

1. The window's five-head pool and band energy (`FinalPool`), with relative RSSI.
2. The start terms of any pass whose windows have all ended (`FinalStartTerms`):
   - the abstain row at the press;
   - the A2 row 1 s after it.
3. Every display frame that could not have read this window (`display.py`: the lock at press + 2.0 s,
   the switch, the dot from `FinalEndHead`).
4. The decoder advances. It calls the frozen `night_track` on the prefix of windows that exist; the
   exit is causal, so a prefix gives the offline answer.

### 14.4 Latency

Measured on one CPU thread with the GPU masked off (report section 9):
- **per window:** 94 to 97 ms median, 0.26 to 0.27 s at p99, inside the 0.5 s stride;
- **at a start press** (the re-cut plus recomputed rows): 0.84 to 0.87 s median, 3.37 s at most;
- **the five heads alone:** 36.9 ms median on the GPU.

**What the viewer experiences:**
- the dot runs 2.0 s behind by design;
- the lock is at press + 2.0 s;
- the committed answer comes at the exit.

### 14.5 Running it

`python3 -m pipeline.live preflight --baseline <dir>` checks:
- the FINAL_CONFIG hash;
- the A1+A2 pace;
- the 133 hashed files;
- the display head;
- both replay gates;
- the reader map;
- the baseline.

It then allows `rig`. The rig has not been run on the boards.

---

## 15. Evaluation

### 15.1 How it is scored

**Which passes count** (`dc2b.split_passes`). Every pass of the six walk recordings; the calibration
recording's passes are not evaluated. That is 120 per test session.

**The three measures:**
- **committed:** the committed line equals the true line;
- **display lock:** the lock line equals the true line;
- **scorer lock:** as reported in 12.3.

**Intervals** (`dc2_pipeline._boot`): a percentile bootstrap over passes, 1,000 draws, seed 0.
**Paired gains** use the same bootstrap on per-pass differences.

**Edge lines** (E_col1 / E_col5 / E_row1 / E_row5) are reported beside every pooled figure.

### 15.2 Results

| test | trained on | committed | display lock | scorer lock | edges, committed | edges, lock |
|---|---|---|---|---|---|---|
| A3 | A1+A2+B1 | 93.33 [88.33, 97.50] | 70.83 [62.50, 79.17] (optimistic) | 70.00 | 67 / 100 / 100 / 100 | 50 / 100 / 83 / 83 |
| B2 | A1+A2+B1 | 93.33 [88.33, 97.50] | **72.50 [63.33, 80.00]** | 71.67 | 100 / 100 / 100 / 100 | 100 / 100 / 50 / 50 |
| B2 zero-shot | A1+A2 | 80.00 [72.50, 86.67] | 49.17 [40.00, 58.33] | 50.00 | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 |

The B1 gain on B2 is +13.33 [7.48, 20.00] committed and +23.33 [15.83, 31.67] lock.

### 15.3 Per line (correct committed / correct lock, of n), read from the saved rows

| line | A3 | B2 | zero-shot B2 |
|---|---|---|---|
| A_fwd | 12 / 12 of 12 | 12 / 12 | 12 / 12 |
| A_rev | 12 / 12 | 12 / 12 | 12 / 12 |
| B_fwd | 9 / 7 | 10 / 4 | 8 / 1 |
| B_rev | 11 / 8 | 10 / 12 | 7 / 10 |
| C_fwd | 11 / 7 | 12 / **3** | 10 / **0** |
| C_rev | 12 / 9 | 11 / 11 | 12 / 11 |
| D_fwd | 11 / 5 | 12 / 10 | 6 / 0 |
| D_rev | 12 / 6 | 9 / 5 | 6 / 2 |
| E_col1 | 4 / 3 of 6 | 6 / 6 | 6 / 6 |
| E_col5 | 6 / 6 | 6 / 6 | 6 / 3 |
| E_row1 | 6 / 5 | 6 / 3 | 5 / 0 |
| E_row5 | 6 / 5 | 6 / 3 | 6 / 2 |

**The commonest lock errors** (true -> locked):
- **A3:** D_rev -> E_col5 (6), D_fwd -> E_row5 (5), C_fwd -> E_col1 (4), B_rev -> E_col5 (3).
- **B2:** C_fwd -> E_col1 (9), B_fwd -> C_fwd (5), E_row1 -> E_col1 (3), D_rev -> B_rev (3).
- **Zero-shot:** C_fwd -> E_col1 (12), D_fwd -> E_row5 (10), B_fwd -> E_col1 (8), E_row1 -> E_col1 (6).

**The lock is wrong while the committed line is right** on 28 A3 passes, 27 B2 passes and 42 zero-shot
passes.

**The commonest committed errors** are diagonal/midline confusions:
- **A3:** B_fwd -> D_fwd (2), E_col1 -> E_col5 (2);
- **B2:** B_rev -> D_rev (2), B_fwd -> D_fwd (2), D_rev -> E_col5 (2).

---

## 16. What every component was fitted on (provenance)

**CORRECTION, 30 September 2026, 09:09 SAST (Uzayr's instruction).** The null-rule row below is wrong.
- **The null rule** (-7.5, gate weight 4.0) was fitted on A1+A2: rb2_decoder stage 2.5, commit `8ca8cac`, on the
  first two recordings of each of A1 and A2, in-sample.
- **The threshold 0.431** was set on A1 (commit `05cc64d`).
- **Neither saw A3.** Section 8.2 was right. See `reports/TRACKING_CHECKS_2026-09-29.md`, 5a.

| component | fitted on | notes |
|---|---|---|
| the five heads, their standardisation | A1+A2+B1 walk windows (calibration excluded) | test sessions refused by assertion |
| augmentation | nothing (fixed ranges) | |
| relative RSSI, g_rec, AdaBN | each recording's own idle windows before its first press | causal, pre-pass |
| cell marginal | the training walk windows | |
| chain prior | the training sessions' line counts | protocol makes it 2:1 |
| G0 0.7542 | A1+A2 idle windows | |
| A2 and abstain readers | cross-fitted rows from A1, A2, B1 (section 10) | the leak fix |
| pace N(1.30341, 0.11255) | A1+A2 tape anchors, 240 passes | recomputed 29 Sep; the old value saw A3 |
| decoder configuration (margin, null_self, exit, clock, bout prior) | rb2_decoder, A1+A2 side of the A1+A2 to A3 pairing | |
| null rule (-7.5, gate weight 4.0, threshold 0.431) | pre-DC2 stage 4 fit | folds not traced |
| abstain threshold 0.90 and weight 0.25 | Room A selection folds A1 to A2, A2 to A1 | |
| A2 weight 0.25, abstain instead of veto, relgateU, aug+rrel, the shared encoder | the development rotations (A1+A2 to B1 x2, A1+B1 to A2, A2+B1 to A1) | design choices; B1 is in them |
| **display cap 0.80 m/window** | **swept on A3's 120 walks** (git 8590d47) | **so the A3 lock is optimistic** |
| **display spread 4.5** | introduced on the A3 pairing (git 0b18ee6) | treated as the cap |
| display phase 0.375 s, SHIFT_W 0.50, switch theta 2.0 | Room A folds (0.375 on A1+A3 to A2; 0.50 over nine pairings incl. A3 test sides; theta on A1 to A2, A2 to A1) | render only; no decision reads them |
| DISP_END | A1+A2+B1 | render only |
| emission kind (scaled, alpha 1) | pre-DC2 Room A stages | not re-derived |

---

## 17. Things found while tracing that bear on decisions

Each is a fact from the code or the saved rows, with what it implies.

### 17.1 The lock names the position 1 s after the press, where lines that share a corner are still together

**The fact.** The lock is read from window `lo + 2`: its evidence ends at press + 2.0 s, and its centre
is press + 1.0 s. At that moment the walker is about 1.3 m along. Consider C_fwd and E_col1, which both
start at the SW corner:
- at 1.3 m, C_fwd is at (0.92, 0.92) and E_col1 at (0.5, 1.3), about 0.57 m apart;
- the emissions are 1 m cells;
- no start term reaches the lock (10.1). Even if one did, the A2 term gives lines of one start region
  the same value.

**The evidence.** The lock errors are dominated by exactly these pairs (15.3): C_fwd/E_col1,
D_fwd/E_row5 and D_rev/E_col5. The worked example is decided by 0.15 nats. The committed decision,
which sees the whole walk, gets those passes right.

**What would change it:**
- a longer lock delay, which V3 fixes at 2.0 s and forbids varying;
- a finer emission than 1 m cells (the g100 native and interpolated emissions were tried in D5 and
  rejected);
- a start reader that separates a corner's lines, for example by direction of travel.

### 17.2 The start readers are the old per-link networks with absolute RSSI

**The fact.** The tracking heads are the final shared encoder with relative RSSI. The A2 and abstain
readers still read the pooled per-link heads with absolute RSSI (section 10). Retraining them on the
final recipe was never tried.

**The implication.** This is untested headroom, and it would need a new development round on the
rotations.

### 17.3 The transit and late-entry quantities are in 1 s units inside a 0.5 s decoder

**The fact.** `decoder2.py` imports Dt from `common.py`, where it is 1.0. `night_common.shipped_pieces`
sets 0.5 only in `decoder.py`. Two things follow:
- **Late entry.** `transition_matrix2` computes its reach and its cost with v x 1.0 s = 1.30 m per
  window: the reach is doubled, and the cost per window is halved.
- **Minimum transit time.** The minimum transit windows in `rb0_preflight/transit_geometry.json` were
  computed for 1 s windows. For example, A_fwd to A_fwd is 3.85 s = 4 windows, which at a 0.5 s stride
  is only 2 s.

**The implication.** Only re-entry after leaving a line reads these: the drawn free path, and the null
paths the exit compares against. The along-line motion of section 9.2 uses the correct 0.5 s. **Every
figure on record was produced with it, so it is not a leak.** Its effect has not been measured.

### 17.4 The live rig needs more than 10 s of standing before the first walk for the abstain reader to adapt

**The fact.** Live, the idle windows are those whose centre is more than 3 s before the first press.
- **At least 10** are required, which is about 9 s of recording before the press.
- **AdaBN needs at least 20,** about 14 s. The rig's docstring says "at least 10 s".

**The implication.** Tell the participant to stand still for **15 s or more** before the first walk.
Offline, A3's P5 recording had 17 idle windows, so its abstain reader ran unadapted.

### 17.5 The relative gate leans hard on each recording's quiet period

**The fact.** Room B's gate scales run from x2.4 to x79.7 (8.1). A recording whose pre-press period is
very quiet gets a large multiplier. One where someone moved before the first press gets less, never
below x1.

**The implication.** The live protocol should keep the room empty and still before the first press.

### 17.6 Three definitions that are easy to misread

- **The labels use raw press times.** The operator's 41 to 51 ms reaction bias is left in (4.3). The
  teaching pack's conventions say "reaction-time corrected", which does not match the code.
- **The resolution figures use the pooled emissions** for the drawn path. The renders use DISP_END with
  a display phase (12.4, 13.2).
- **The render's "decoded accuracy"** compares the dot with the truth 1 s before the frame. That is not
  the decoder's accuracy (13.3).

### 17.7 The A3 lock is optimistic, and the B2 lock is the headline

The display cap and spread were set on A3's walks (16). The committed decision reads neither.

### 17.8 One reference is stale

The paired differences in `final/FINAL_CORRECTED.md` against the split baseline (ph_A3 and ph_B2) mix
the leak fix with the model change. Those baselines were decoded with the leaky readers and the old
pace.

---

## 18. Where everything is

| what | file |
|---|---|
| capture, parsing, ground truth | `pipeline/io/capture_logger.py`, `parse.py`, `ground_truth.py` |
| cleaning | `pipeline/clean/common.py` |
| windows, labels | `pipeline/splits/windows.py`, `pipeline/constrained/y4_pressalign.py`, `lattice.py` |
| features, RSSI, gate energy | `pipeline/constrained/features.py`, `recordings.py`, `pipeline/branches/gate.py` |
| the cells, relative RSSI, training driver | `pipeline/constrained/pd_cells.py` |
| network, training | `pipeline/constrained/pd_arch.py`, `pd_train.py`, `pipeline/models/link_cnn.py`, `heads.py` |
| inference | `pipeline/constrained/dc2_run.py` (`do_infer`), `artefacts.py`, `nets.py` |
| emissions, pool | `emissions.py`, `night_common.py`, `g2_multihead.py`, `g3_final.py` |
| decoder | `decoder.py`, `decoder2.py`, `night_arms.py`, `r1_oldcensus.py`, `n2_arms.py`, `rb3_display.py` |
| start readers | `q3_startclf.py`, `q4_arms.py`, `u1_adapt.py`, `u2_useit.py`, `t2_embed.py` |
| the final decode and its variants | `pd_decode.py`, `pd_clean.py` (the corrected map, the pace) |
| display, lock, dot, renders | `render_display.py`, `switching.py`, `pd_dispend.py`, `pd_render.py`, `reports/RENDER_RULES.md` |
| live | `pipeline/live/` (`final_model.py` for the final model) |
| scoring, rule | `dc2_pipeline.py` (`_acc`, `_boot`), `pd_rule.py`, `pd_final.py` |
| frozen configuration, results | `runs/dc2_results/rule/FINAL_CONFIG.md`, `runs/dc2_results/final/` |
| worked example, per window | `reports/teaching_pack_corrected_2026-09-29.json` |

---

## 19. What was done to the model on 29 September, in order (appended 21:49)

**Sources:** `reports/DEVLOG_TRACKING_2026-09-28.md` (section VERIFY) has every step, with its commands
and outputs. `reports/MODEL_FINAL_TRACKING_CORRECTED.md` has the results, and
`reports/HANDOFF_TRACKING_2026-09-29_CORRECTED.md` the handoff.

**The starting point.** At 09:55 the previous session had tested the final model: A3 93.33 / 70.83,
B2 94.17 / 74.17, zero-shot B2 83.33 / 49.17 (`reports/MODEL_FINAL_TRACKING.md`). Uzayr asked for no
model changes: verification, porting and rendering only.

| time | step | result |
|---|---|---|
| 10:30 | VERIFY 1a: the 09:55 model's 33 hashed files | 33 of 33 match |
| 10:33 | VERIFY 1d: the leakage audit | **FAILED.** B1's reader rows came from networks trained on A1+A2+A3. Work stopped and was reported |
| 10:44 | Uzayr: "fix it properly" | |
| to 11:19 | **the widened audit:** every file each decode opens, traced by a Python audit hook, each network mapped to the sessions it trained on | a **second path**: on two rotations, the Room A reader rows came from the validation session's own head. Nothing else saw A3 or B2 (A3's sidecars are opened for line geometry only). Seven CPU reproductions of the record were exact before any fix. `reports/AUDIT_LEAKAGE_TRACKING_2026-09-29.md` |
| 11:19 onwards | **the fix,** `pipeline/constrained/pd_clean.py` | every training session's reader rows now come from heads trained only on the model's OTHER training sessions (section 10). The rebuilt reader files match the originals' builder to 2e-6 |
| 12:56 to 14:04 | **all 78 recorded rule comparisons re-run** on the development rotations with clean readers (`rule/CR_*`) | **8 decisions moved.** Abstain now beats the veto: the leak had flattered the veto on its own validation data |
| 13:00 to 13:08 | the display head DISP_END retrained on A1+A2+B1 with the final recipe, on the GPU once Identification freed it (`pd_dispend.py`) | 2,744 end-labelled windows |
| 14:53 | re-selection round 1 (`rule/RS_SUMMARY.md`) | **adopted the A2 start-term weight 0.25** (+1.88 [0.42, 3.55]) |
| 15:20 to 15:35 | Uzayr's decisions | D2 stays aug+rrel; round 2 is final; the zero-shot provenance check fails on Room B only; the pace is recomputed on A1+A2 (stop if it moves more than 0.02 m/s); the cap and spread are kept, with the A3 lock labelled optimistic |
| 15:36 | the pace recomputed (`final/PACE_A1A2.json`) | A1+A2: N(1.30341, 0.11255), 240 passes. The same method on A1+A2+A3 reproduces the old N(1.298, 0.123). The change is within 0.02 m/s |
| after round 1, summary written 15:39 | round 2 (`rule/RS2_SUMMARY.md`) | **nothing further adopted.** Display lock kept (+1.46 [-1.67, 4.79]); shared encoder confirmed (+19.38) |
| 15:39 | **the configuration frozen** before any test decode: `rule/FINAL_CONFIG.md` | SHA-256 360053d7... |
| 15:41 to 15:45 | **THE ONE TEST** (`final_corrected_chain.sh`) | A3 93.33 / 70.83; B2 93.33 / 72.50; zero-shot B2 80.00 / 49.17 |
| 15:45 to 15:54 | verification (`pd_subst.py`) | substitution and shuffled radio (details below) |
| 15:55 | the teaching export, re-run on the corrected model | `reports/teaching_pack_corrected_2026-09-29.json`; the eight teaching questions answered in chat |
| 15:57 to 16:21 | the renders, A3 and B2 (`pd_render.py`) | 12 videos; every RENDER_RULES check passes |
| 16:21 to 17:08 | the live port (`pipeline/live/final_model.py`): the replay gates | A3 120/120, B2 120/120, committed and lock |
| 17:08 | the live pre-flight | fixed (details below); now passes |
| 17:07 to 17:49 | the reproduction from hashes (`pd_repro.py`) | fin_B2 and fin_A3 EXACT |
| 17:50 | records and the commit | report sections 7 to 10, the handoff, DEVLOG, QUEUE and STATE; **commit 86217ca**, 383 files by name |
| 21:22 | this report | not committed |

**The one test,** once, on the frozen configuration:
- **provenance pre-checks** on each model's components (`pd_provenance.py`), with fail-loud checks:
  - the zero-shot fails on anything touching B1 or B2;
  - the main model fails on anything touching A3 or B2;
- **three decodes:** fin_A3, fin_B2 and zsf_B2, all with clean readers and the A1+A2 pace;
- **provenance post-checks** on each decode's own file trace;
- **the tables:** `final/FINAL_CORRECTED.md` and `ZERO_SHOT_CORRECTED.md`;
- **the hash** of `FINAL_CONFIG.md` checked again at the end.

**Verification** (`verify/subst/`). Each run first reproduces the test's rows on the pass's own radio,
120 of 120 in all three cases.
- **Substitution** (another participant's radio, same pass number): the decision changes 0.93 to 1.02
  times as often as the donor's line differs. It equals the donor's own decision on 99 to 100 percent.
- **Shuffled radio** (a different line's radio): committed accuracy falls to 0.0 to 2.5 percent, and the
  lock to 0.8 to 5.8.

**The renders** (`runs/dc2_results/render_final/`):
- 0 frames without a dot;
- causal bounds of -1.375 s (A3) and -1.376 s (B2);
- one-switch display: 3 switches on A3, all wrong to right, and 1 on B2, wrong to wrong;
- on-screen tracking within 0.5 m of the delayed marker: 43.5 percent (A3) and 48.9 percent (B2).

**The live port.** The final model runs in the live code; section 14 describes how. Measured:
- per window: 94 to 97 ms median on one CPU thread;
- at a start press: 0.84 to 0.87 s median;
- the relative-RSSI means are identical to the offline references.

**The pre-flight fix.** The pre-flight first read a selection file the chain never wrote, and the rig
would not have set the A1+A2 pace. Both now come from the frozen files: the variant from the
hash-checked `FINAL_CONFIG.md`, and the pace from `final/PACE_A1A2.json`.

**The reproduction from hashes.** The 133 hashed files were checked, and fin_A3 and fin_B2 rebuilt from
them in scratch trees and re-decoded: 0 of 120 changed in each.
- **A gap in the hash list:** it had missed the B1 reader's three position networks.
- **How it was closed:** the rebuilt rows equal the hashed rows file in every array, in both cells.
- **The record:** the files are listed in `final/FINAL_CORRECTED_HASHES_SUPPLEMENT.txt`.

**Faults of my own during the day,** all caught and fixed before any result depended on them:
- a monitor matched its own command line;
- a key error on B1's calibration recording in the reader check;
- round 2 refusing to overwrite a variant that round 1 had already written;
- the provenance script not following fin_B2's shared weights to fin_A3;
- an import-order guard in the teaching wrapper;
- the pre-flight above;
- one timestamp written as 17:12 when the clock read 17:08, corrected.

---

## 20. The current state of the model (21:49, 29 September)

**THE MODEL IS FINAL, CORRECTED, TESTED ONCE AND FROZEN.**
- **Configuration:** `runs/dc2_results/rule/FINAL_CONFIG.md`, hash-checked.
- **Networks:** `runs/dc2_results/cells/fin_A3/art_*/models/s0102B1_to_s03_*`, trained on A1+A2+B1.
  fin_B2 holds byte-identical copies.
- **Decode:** relgateU + abstain + A2 weight 0.25, with the display lock and the A1+A2 pace.
- **Zero-shot model:** `cells/zsf_B2/`, trained and fitted on A1+A2 only.

| | state |
|---|---|
| **headline figures** | A3 93.33 / 70.83 (lock optimistic); **B2 93.33 / 72.50**; zero-shot B2 80.00 / 49.17; B1 gain on B2 +13.33 / +23.33 |
| **superseded** | `reports/MODEL_FINAL_TRACKING.md`'s figures (they carried the reader leak); that file is kept, unchanged, as the record |
| **the confirmatory record beside it** | the frozen DC2 results, `reports/DC2_RESULTS_2026-09-28.md` |
| **test looks** | **A3 and B2 have been decoded three times:** the midpoint, the 09:55 FINAL, and the corrected test. The verification, renders, gates and reproduction re-use that decode. **Any further A3 or B2 figure would be a fourth look and needs Uzayr** |
| verification | substitution and shuffled radio pass; reproduction from hashes exact on fin_A3 and fin_B2 |
| renders | done, A3 and B2, every rule check passes |
| live system | replay gates exact; pre-flight passes; **never run on the boards** (the rig opens the serial ports and needs Uzayr) |
| committed | **86217ca**: code, reports, tables, the rotation evidence, provenance and traces, render results |
| not committed | `pipeline/live/` (TestRig's uncommitted tree, including `final_model.py`, which is committed only when Uzayr asks); this report; the teaching chat's `tools/teaching_pack.py`, `reports/teaching_pack.json` and its DEVLOG section; videos, weights, caches and scratch trees |
| running | **nothing for tracking.** The GPU and CPU belong to Identification |
| where the next session starts | `reports/HANDOFF_TRACKING_2026-09-29_CORRECTED.md`, then this report |

**Open items**, none started:
1. **The split baseline** (ph_A3, ph_B2) was decoded with the leaky readers and the old pace, so the
   paired differences against it mix the fix with the model change. A clean baseline would need another
   A3 and B2 decode.
2. **The cap and spread were set on A3.** A re-sweep on the rotations would remove the "optimistic"
   label from the A3 lock.
3. **The render's "decoded accuracy"** is an inherited definition that is not the decoder's accuracy.
   Redefining it in RENDER_RULES is Uzayr's call.
4. **The rig run on the boards:** `python3 -m pipeline.live preflight --baseline <dir>`, then `rig`,
   with 15 s or more of standing still before the first walk (17.4).
5. **The zero-shot cell** is not reproduced from hashes: about 15 CPU minutes, and no new figure.
6. **Future hash lists** should come from the decode's own file trace, not a name pattern.
7. **Untested headroom** (section 17), all development work on the rotations, not the test sessions:
   - the start readers on the final architecture (17.2);
   - separating lines that share a start corner at the lock (17.1);
   - the 1 s units in the decoder's transit and late-entry terms (17.3).
