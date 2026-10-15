# The tracking model, end to end: architecture, training, decoding, and where to attack it

Written 2026-09-28 22:31 SAST (clock read) for Uzayr, from the code, not from memory. Every constant below was read
from the source files named beside it. This describes the recipe that the frozen DC2 model uses and
that every development cell reuses, so it is the model to attack.

**The split, the operator's decision of 2026-09-28:**
- **Train on A1, A2 and B1** (Room A sessions 01 and 02, Room B day 1). Every model trains only on
  these, and every choice is made on validation inside them: train on two, validate on the third.
- **Test on A3 and B2** (Room A session 03, Room B day 2). These are also the demo renders. They never
  enter training or any choice. Only their causal pre-pass data may be used at test time: B2's
  calibration walk for configuration B, and each recording's idle radio before its first press.

---

## 0. Where it stands on this split, and what is running now

**The baseline on the split** is one model on A1+A2+B1 with the current recipe, cells `ph_A3` and
`ph_B2` (`runs/dc2_results/posthoc_cell.md`):

| test | configuration | committed (line named at walk end) | display lock (2 s after the press) | scorer lock | committed edges E_col1 / E_col5 / E_row1 / E_row5 |
|---|---|---|---|---|---|
| A3 | A (= B) | **88.33** [82.50, 94.17] | **65.00** [56.67, 73.33] | 69.17 [60.83, 77.52] | 33 / 100 / 100 / 100 |
| B2 | A | **57.50** [49.17, 66.67] | **20.83** [13.33, 29.17] | 20.83 [13.33, 29.17] | 100 / 83 / 50 / 17 |
| B2 | B (calibrated) | **65.83** [57.50, 74.17] | **30.00** [21.67, 38.33] | 33.33 [25.00, 41.67] | 100 / 100 / 83 / 33 |

- **Chance** is 8.33 percent, one line in twelve.
- **Each test has 120 passes:** 6 people × 20.
- **The frozen reference:** heads on A1+A2+A3 score 50.00 (A) and 57.50 (B) on B2, with locks 12.50
  and 25.00.

**What to attack, in one line:** Room A is nearly solved on the committed answer (88) and fair on the
lock (65). Room B is the problem: 58 to 66 committed and 21 to 30 lock.

**Running now (D1, development batch 1, on this split):** per-recording normalisation.
- **The change:** every recording, training and test alike, is standardised per receiver link and
  input channel by the statistics of its own idle radio before its first press. That is causal
  pre-pass data, and a live system has it before anyone walks.
- **Why it's promising:** section 11.1.
- **How the choice is made:** on the three development rotations (A1+A2 → B1, A1+B1 → A2,
  A2+B1 → A1), under both normalisations and both lock methods.
- **The test:** the chosen setting's final model trains on A1+A2+B1 and is tested once on A3 and B2.
- **Timing:** started 22:25, six trainings, about 3 hours. Log: `runs/dc2_results/logs/queue_d1s.log`.
  Record: `reports/DEVLOG_TRACKING_2026-09-28.md`, D1.

---

## 1. The task and the geometry

- **The room:** a 5 × 5 m taped grid, with the origin at the bottom-left corner.
- **The radios:** one transmitter at (2.5, −0.5) sends at about 150 packets per second. Three
  receivers at 1.1 m height:
  - RX1 at (2.5, 5.5), north;
  - RX2 at (−0.5, 2.5), west, facing east;
  - RX3 at (5.5, 2.5), east.

  Each receiver gives one TX-to-RX link, so the system has **three links**.
- **Twelve taped lines:**
  - A_fwd and A_rev: the vertical centre line x = 2.5, both directions;
  - B_fwd and B_rev: the horizontal centre line y = 2.5;
  - C and D, fwd and rev: the two diagonals;
  - four edge lines, one direction each: E_col1 (x = 0.5), E_col5 (x = 4.5), E_row1 (y = 0.5),
    E_row5 (y = 4.5).
- **A pass:** a person walks one line and the operator presses space at six marks: every 1 m on a
  straight line, every 1.41 m on a diagonal, 0 m to 5 m. Each person walks 20 passes per session: the
  eight two-way lines twice each and the four edge lines once, in random order.

**Why it is posed this way.** Naming which of twelve known lines was walked, and where along it, is a
constrained version of 2-D tracking. The constraint lets a hidden Markov decoder turn weak per-window
evidence into a confident answer. The cost is that the model cannot track arbitrary paths; every
answer is one of the twelve lines.

---

## 2. The signal chain: from packets to model input

Code: `pipeline/io/capture_logger.py`, `pipeline/clean/common.py`, `pipeline/splits/windows.py`,
`pipeline/constrained/features.py`.

### 2.1 Per packet, per receiver

**1. The raw data.** Each packet carries 128 complex channel values (one per OFDM subcarrier) and the
RSSI in dBm. The amplitude is the complex magnitude.

**2. Dead subcarriers are dropped:** the null and guard bins and two invalid first words, leaving 107
of 128 (51 legacy, 56 HT). *Why:* they carry no signal and would drag every normalisation.

**3. Per-packet shape normalisation.** Each packet's legacy half and HT half are each divided by
their own mean. *Why:* the ESP32's automatic gain control rescales every packet and cannot be read
or locked. It was measured that an 11.8 dB change in received power moved the recorded amplitude by
only 0.5 dB. So **absolute amplitude carries no information**; only the relative shape across
subcarriers does, and that shape is frequency-selective fading, which is where position lives. Two
scalars per packet, not one, because the 802.11n preamble retrains the gain between the legacy and
HT halves.

**4. Outlier removal:** a Hampel filter over 21 samples (140 ms), removing only spikes. *Why:* a mean
or median filter would smear motion; a Hampel filter leaves clean samples bit-identical.

**5. Uniform resampling** to a 150 Hz grid by linear interpolation. *Why:* packets arrive
irregularly, and a network needs a fixed sample lattice.

**6. Baseline subtraction in shape space.** The per-subcarrier median shape of that recording's own
60 s empty-room capture is subtracted. *Why:* it removes the room's static multipath, the fixed
furniture and walls, leaving the change a person makes. In DC2 every tracking recording has its own
baseline taken 1 to 2 minutes before (PA1's day 1 walk used PA2's, 66 minutes earlier).

### 2.2 Windows

**7. Cutting.** 2.0 s windows of 300 samples × 107 subcarriers × 3 receivers, stored at float16.
Float16 was checked against float32: median relative error 1.7e-4.

**8. The ONE lattice.** A 0.5 s stride, re-phased per pass so that one window starts 2 µs after the
pass's first press (`pipeline/constrained/lattice.py`, `y4_pressalign`). *Why:* the 2 s lock must be
read from a window that ends exactly at press + 2.0 s. On the old grid lattice the lock read up to
0.5 s of radio recorded after its own frame, a causality leak that was found and fixed on
2026-09-23.

**9. Labels, per window, at the window's CENTRE:**
- **mode:**
  - `walk` if the centre falls between the pass's first and last press;
  - `walk_edge` within 3 s outside a pass;
  - `idle` otherwise;
  - `grid` in the older static protocol.
- **position:** linear interpolation between the six presses at the centre time, using the raw press
  times. *Why no reaction-time correction here:* the pressing convention varied (waist against heel),
  so the offset is spread, not bias, and it cancels over forward and reverse passes
  (`reports/v2/label_uncertainty.md`).
- **cell:** the 1 m cell (25 cells) or 0.5 m cell (100 cells) containing that position.

### 2.3 Model input features (`features.py`)

**10. Channel 1, the CSI shape:** a zero-phase 4th-order Butterworth low-pass at 2 Hz per
subcarrier, with no high-pass, detrending or mean removal. *Why:* a person's position shows as a slow
drift in the relative subcarrier pattern (near-DC). Walking-rate Doppler (around 1 to 3 Hz) is gait
information, which identification uses, not position.

**11. Channel 2, RSSI:** resampled onto the window's own 300-sample lattice and broadcast across the
107 subcarriers. *Why:* body shadowing swings RSSI as a person crosses a link. Averaging it to one
number per window would destroy that swing.

**12. The result:** each window becomes, per link, a 2-channel image of 300 time samples × 107
subcarriers.

---

## 3. The networks: five heads, each three per-link CNNs

Code: `pipeline/constrained/nets.py`, `pipeline/models/link_cnn.py`, `pipeline/models/heads.py`,
`pipeline/constrained/artefacts.py`.

### 3.1 One link's network (`LinkNet`), trained separately for each of the three links

**Input standardisation.** Per channel, one mean and one standard deviation over all training windows
(CSI shape and RSSI separately). *Why per channel:* the CSI shape has a spread of about 0.26 and RSSI
about 2 dB. One global statistic would flatten the CSI channel to noise.

**Encoder (`LinkCNN`),** about 80,000 parameters:
- 3 blocks of [Conv2d 5×5, padding 2 → BatchNorm2d → ReLU → MaxPool 2×2], widths 16, 32, 48;
- adaptive average pool to 3 × 3;
- flatten, then dropout 0.2;
- linear to a **64-dimensional embedding**.

*Why a small 2-D CNN:* the 5 × 5 kernels see local time-by-subcarrier texture. Pooling gives some
tolerance to where in the window a feature sits. The size suits about 3,400 training windows.

**Posterior head (`IDHead`):** dropout 0.2 and a linear layer to 25 (or 100) cell logits. Plain
cross-entropy, no label smoothing (it was absent when the frozen weights were made, so it stays
absent).

**Position head:** linear 64 → 64, ReLU, dropout, linear to (x, y) in metres, smooth-L1 loss. It is
used only by the start-of-walk reader (section 6), not by the tracker.

**Training** (`nets.run_epochs`):
- Adam, learning rate 1e-3, weight decay 1e-4, batch 64;
- 24 epochs for the posterior head, 20 for the position head;
- deterministic given the seed; the 1 s heads retrain bit for bit;
- on the MPS GPU.

**Training data:** only `walk` windows with a position label, from the training sessions, and never
a calibration walk. On the split: 3,428 windows at 0.5 s (A1 1,122, A2 1,128, B1 1,178) and 1,615 at
1.0 s.

**Links are NOT shared:** three independent networks per head. *Why, historically:* each receiver
sees the room from a different place, and per-link heads were what the frozen record used. *The
cost:* no network ever reasons across links, and the fusion (below) is the only place they meet.

### 3.2 From three links to one head output: mean link fusion

A head's output for a window is the **mean of its three links' cell posteriors** (`fusion.py`; w = 0).

*Why:* robust, and it was the shipped choice. Product fusion (w > 0, towards multiplying the links'
opinions) is an option. It was exploratory in DC2 and scored 50.00 against 45.83 pooled on Room B.

### 3.3 The five-head pool

| head | stride trained on | output | seed |
|---|---|---|---|
| `half` | 0.5 s (the ONE lattice) | 25 cells (1 m) | 0 |
| `fh1s`, `g1s1`, `g1s2` | 1.0 s | 25 cells | 0, 1, 2 |
| `g100` | 1.0 s | 100 cells (0.5 m) | 0 |

- **Inference:** all five run over the same 0.5 s windows.
- **Pooling** (`g2_multihead.pool`): an **equal-weight log-opinion pool**. Each head's per-state log
  evidence is averaged, then shifted so each window's best state scores 0.
- *Why five heads:* seeds and strides give an ensemble. The 100-cell head adds 0.5 m resolution the
  1 m heads cannot give. Equal weights, so no head is chosen on a result.
- **The position head** is trained with the `half` head, for the reader only.

---

## 4. Emissions: from cells to the decoder's states

Code: `pipeline/constrained/emissions.py`, `rebuild_common.emission_choice`.

- **The states:** each of the twelve lines is sampled every 0.25 m, 288 line states in all.
- **A state's evidence** is the head's log-probability of the **cell that state lies in**, divided
  by that cell's frequency in the training labels (the "scaled" emission, alpha 1.0):
  `log p(cell | window) − log p(cell)`.
  - *Why divided:* eight of the twelve lines cross the centre, so the centre cells are
    over-represented in training. The raw posterior carries a centre bias that the decoder would then
    double-count.
- **THE STAIRCASE:** every 0.25 m state inside one 1 m cell gets **the same** evidence from the 1 m
  heads. Only the 100-cell head distinguishes 0.5 m. **The radio cannot place a person within a
  cell**; the motion model does that.

---

## 5. The decoder: a hidden Markov model over the twelve lines

Code: `pipeline/constrained/decoder.py`, `decoder2.py`, `night_arms.night_track`,
`night_common.shipped_pieces`. The shipped configuration (`rb2_decoder`), read from the code:

```
Config(veto=True, split=True, geometry=True, late_entry=True, margin=2.0, null_self=0.8,
       exit_k=1, exit_p=0.5, clock_max=8, kind='tight', sd_scale=1.0,
       bout_log_odds=-1.2756, abort_cost=60.0)
AdaptiveNullEmission(quantile=0.75, offset=-7.5, gate_weight=4.0, motion_theta=0.431)
emission: scaled, alpha 1.0; step 0.5 s; V_MEAN 1.298 m/s; V_SD 0.123 m/s
```

### 5.1 The states

- **288 line states:** 12 chains, a point every 0.25 m.
- **"Not on a line", split in two:**
  - **STILL(p):** standing, remembering the line p just left, or none;
  - **TRANSIT(p, k):** walking between lines, with a **walking clock** k counting windows since the
    last still reading, capped at 8.

  *Why:* someone who finishes a line and walks on must still cover the distance to the next line's
  start, and the clock plus transit geometry forbid impossible jumps.

### 5.2 Transitions

- **Along a line: forward only, at a fixed pace.** Each 0.5 s step advances
  N(0.649 m, 0.0615 m); backward steps are impossible. That is the walking speed 1.298 m/s ± 0.123
  measured on Room A. *Why:* it turns noisy evidence into a smooth, physically plausible walk.
  *The cost:* in the committed decision's line totals, once a line and a start point are fixed, the
  pace model decides where along the line the person is, to about a quarter of a metre.
- **Entry:** a walk may join a line within 1.0 m of its start ("soft entry": the first window's own
  evidence picks the point).
  - **Late entry** is also allowed, at any distance the walking clock permits (s ≤ v(k+1)), for a
    cost of 2.0 nats.
  - Every entry from walking pays the **bout prior**, a −1.28 log-odds that a walking bout is a pass
    at all.
- **Exit:** only from a line's last state (probability 0.5 per window there). "Not on a line" stays
  put with probability 0.8.
- **Motion gate veto:** when the 0.3 to 2 Hz band energy of the raw window is below 0.431, every line
  state is forbidden for that window. *Why:* a person standing still is not walking a line.

### 5.3 The null level

**"Not on a line" competes with the lines through a single level per window:**

    level = the 75th percentile of this recording's per-window best line evidence − 7.5 nats
            + 4.0 nats when the gate reads still

*Why adaptive:* a fixed level did not transfer across days (recall 63 fell to 26). A level set
relative to the recording's own evidence does.

**Note:** the percentile is taken over the whole recording, so offline it uses windows after the
current one. That matters for any live claim (section 11).

### 5.4 The committed decision: the answer given when the walk ends ("semi-bounded")

1. **The start is given.** The decode starts at the operator's first press. The end is not given.
2. **Causal exit.** One forward pass. The walk ends at the first window where the most likely state,
   using only radio received so far, is "not on a line", with a 20 s cap.
3. **Line totals.** For each of the twelve lines, a Viterbi decode inside that line alone, over the
   walk's windows, with the forward-only pace model. Its total log evidence is the line's score.
4. **Plus the per-line prior:** log of each line's frequency in the training sessions. The edge lines
   are walked half as often, so they get −log 2.
5. **Plus the A2 start term:** 0.5 × the centred log-probability, from the start-region reader
   (section 6), that the walker started in this line's start region.
6. **Plus the veto:** −3.0 nats for a line whose start region the veto reader gives below 0.01.
7. **Family first.** Sum the likelihood within each family (vertical, horizontal, diagonal C,
   diagonal D, edge), take the best family, then its best member.

*Why the family-first rule:* confusions were mostly within families, and choosing the family on
pooled evidence first reduced them.

---

## 6. The start-of-walk readers (the A2 term and the veto)

Code: `q3_startclf.py`, `q4_arms.start_terms`, `u1_adapt.py`, `u2_useit.py`, `veto.py`.

**The eight start regions:** the four wall midpoints and the four corners. Every line starts in one
of them.

**A2 reader:**
- *Input:* the position head's (x, y) estimates, fused and per link, over windows ending between 2 s
  before and 1 s after the first press. It takes their mean, spread, first and last values.
- *Model:* LDA with automatic shrinkage and a standard scaler, 8 classes.
- *Training:* on the training sessions' passes, with each session's features from heads that did
  **not** train on it.
- *Result on Room A:* 46.7 percent against 12.5 chance; 61.8 at wall midpoints, 36.6 at corners.

**Veto reader:**
- *Input:* the 0.5 s head's 64-d encoder embeddings (all three links) over windows ending at or
  before the press, within 2 s (strictly pre-press). The features are the mean embedding and the
  last one.
- **AdaBN:** the encoder's batch-norm statistics are re-estimated for each recording from its idle
  windows before the first press. This is the only part of the shipped model that adapts to a new
  recording, and it reads no labels.
- *Model:* LDA with automatic shrinkage.

**Use:**
- A2 adds 0.5 × the centred log-probability of each line's start region to the committed decision
  and to the display decode.
- The veto subtracts 3 nats from lines whose start region is below 1 percent, in the committed
  decision only.
- **In Room B the veto did not help** (+0.42, not confirmed). Abstaining (b_abstain_0.25) did,
  +2.92 [0.42, 5.83].

---

## 7. The lock, the drawn dot, and latency

Code: `dc2_scorerlock._inner`, `night_arms` (display), `f4_render.py`, `reports/RENDER_RULES.md`.

**The display decode** is the same decoder with the pace model loosened:
- a 4.5 × wider step spread;
- a speed cap of 0.8 m per 0.5 s step (1.6 m/s);
- the A2 term, but not the veto.

**The display lock** is the line of the display decode's best state at the window that **ends at
press + 2.0 s**. *Why 2.0 s:* the operator's rule V1, which runs the whole display exactly 2.0 s behind
real time. A longer wait buys accuracy but costs delay.

**The scorer lock** (exploratory) takes, for each line, 0.75 × the display lock score + 0.25 × the
committed decision's line total over the same windows (with A2 and the veto), and picks the best. On
the split it gives 69.17 against 65.00 on A3, and 33.33 against 30.00 on B2 (B).

**The drawn dot** after the lock:
- a Viterbi restricted to the locked line;
- a separate display head (DISP_END) with its pace model mixed 50 percent towards uniform;
- a display phase of 0.375 s (demo v2);
- one switch at most, not in the final 1.5 m, to a line the final-answer scorer leads by more than
  2 nats twice running;
- drawn 2.0 s behind real time.

The along-line position is about half radio, half pace model (substitution ratio 0.52).

**Latency:** a window can only be used once it ends. Per window the pipeline takes a p99 0.20 s on an
idle laptop (the live system). The design latency is the rule's 2.0 s.

---

## 8. Configuration B: same-day calibration from a calibration walk

On a Room B test day only:
- **The null offset** is rescaled by how spread the model's evidence is on that day's calibration
  walk against Room A's: −7.5 × s_B / s_A, with s_A = 2.111, and a ±3 nat guard.
- **The motion gate** is re-anchored between that day's idle and calibration-walk band energy.

B2's gate moved from 0.431 to 0.201, because Room B's motion energy runs about 5 times lower than
Room A's. B1's bracket inverted (a quiet walker against a whole-day idle level), so its gate fell back
to 0.431.

Room A test sessions have no calibration walk, so B equals A there.

---

## 9. What is fitted on what (the leakage audit)

| component | fitted on | on the split |
|---|---|---|
| network weights, all five heads and the position head | training walking windows | A1+A2+B1 |
| input standardisation (per channel) | training windows | A1+A2+B1 |
| cell frequencies for the scaled emission | training labels | A1+A2+B1 |
| per-line prior | training line counts | A1+A2+B1 |
| A2 and veto readers | training passes, out-of-sample features | A1+A2+B1 |
| AdaBN statistics (veto reader) | each recording's own idle radio before its first press | causal, per recording |
| null reference (75th percentile) | each recording's own evidence, whole recording | **not strictly causal** |
| configuration B null and gate | the test day's calibration walk | causal pre-pass |
| decoder constants: margin 2.0, null_self 0.8, bout −1.28, offset −7.5, gate weight 4.0, gate 0.431, display 4.5 and 0.8 m, A2 weight 0.5, veto 0.01 and 3 nats | **tuned on Room A sessions 01 to 03 before DC2** | includes A3; re-tune on A1, A2, B1 |

**The last row is the one leak on this split.** The decoder's constants were chosen on Room A folds
that tested on session 03. They are not neural weights, but they are choices, and a strict reading of
the split says to re-choose them on A1, A2 and B1.

---

## 10. The numbers that define the problem

| where | committed | lock | what it says |
|---|---|---|---|
| A3, split baseline | 88.33 | 65.00 | Room A works |
| B2, split baseline, A / B | 57.50 / 65.83 | 20.83 / 30.00 | Room B is the problem, the lock most of all |
| B2, frozen A1+A2+A3 model, A / B | 50.00 / 57.50 | 12.50 / 25.00 | adding B1 to training helped B2 |
| B1 → B2, one Room B day only | 18.33 | 8.33 | one Room B day alone does not transfer to the other |
| window-level cell top-1, Room B heads on their own day / the other day | 77 to 84 / 3.6 to 4.1 | | overfit to the day's exact geometry |
| CSI shape spread, Room A / Room B idle | 0.12 to 0.29 / 0.03 to 0.12 | | Room B's input looks 4 to 10 times weaker |
| motion band energy while walking, Room A / Room B | about 1.25 / 0.2 to 0.9 | | the gate threshold does not transfer |
| mean RSSI shift between Room B days, links 1 and 2 | 3.4 and 4.6 dB | | placement moved between days |

---

## 11. Where to attack, ranked, with the reason for each

### 11.1 Input scale and placement shifts: the biggest lever (D1 is testing the first part)

**The problem:** Room B's CSI shape spread is 4 to 10 times smaller than Room A's, its motion energy
about 5 times lower, and its RSSI levels shift by 3 to 5 dB between days on two links. The network
standardises with one global mean and spread from training, so Room B looks like "almost nothing
happening". RX2 is also re-placed for every participant, so every recording's geometry differs a
little.

**Attacks:**
- **Per-recording normalisation** from idle radio (D1, running).
- **Per-link normalisation of RSSI only**, since RSSI levels carry placement, not position.
- **Augmentation during training:** random per-link gain and offset on RSSI, random scaling of the
  CSI shape, small time shifts. That makes the model insensitive to exactly the variations DC2 shows.
- **Train the gate threshold relative** to each recording's idle band energy, not as an absolute
  number.

### 11.2 The networks see one link at a time

**The problem:** three separate per-link CNNs, fused by averaging probabilities. No network reasons
across links, but position is inherently a cross-link question: which link is shadowed, and which
fading pattern goes with which.

**Attacks:**
- **A joint encoder:** the three links as channels, or one shared per-link encoder with a learned
  fusion head over the three embeddings.
- **Product fusion,** already better in DC2 (50.00 against 45.83 on Room B).
- **Attention over links,** so a link that looks unfamiliar (for example, a moved RX2) is down-weighted.

### 11.3 Resolution is capped by 1 m cells

**The problem:** four of the five heads output 1 m cells, and within a cell the pace model, not the
radio, places the dot.

**Attacks:**
- A continuous position output: a regression head, or the probability-weighted mean of cell centres.
- More weight on the 100-cell head.
- A decoder that reads a continuous position likelihood. That also serves the project brief's
  "spatial resolution".

### 11.4 The lock sees too little evidence in Room B

**The problem:** the lock reads about 2 s of walking. In Room B the per-window evidence is weak, so
the loosened display decode has little to go on. B2 lock: 21 (A), 30 (B).

**Attacks:**
- **Better early-walk evidence,** from 11.1 and 11.2.
- **The scorer lock:** already +3 to +4 points on the split; free to choose.
- **A dedicated start-and-direction head,** trained to name the line from the first 2 s: the
  pre-press run-up plus the first 1 to 2 m. The run-up carries direction (55 percent against 50).
- **Include the pre-press run-up windows,** which are causal, in the lock's evidence.

### 11.5 The decoder's priors and constants were tuned on Room A, and some use elapsed time

**The problem:**
- The pace model (1.298 m/s ± 0.123), the walking clock, the transit geometry, late entry and the bout
  prior all encode Room A's walking protocol and timing.
- The system requirement says the tracker is signal-only: no pace, elapsed time or dead reckoning.
  The pace prior and the walking clock sit uneasily with that.
- Room B's walkers are about 4 percent slower (1.25 against 1.30 m/s).
- Every constant was chosen on folds that include A3.

**Attacks:**
- **Re-tune the constants on A1, A2 and B1:** the margin, the null offset, the gate weight, the bout
  prior, the display spread.
- **A radio-led along-line model:** steps in either direction, no assumed speed, a physical speed cap.
  That meets the signal-only requirement more cleanly and should make the dot follow the radio.

### 11.6 The null level and exit

**The problem:** the null reference is a whole-recording percentile, so it is not causal for live use.
The exit waits for "not on a line" to win, and in Room B the evidence is flatter, so exits come late
or early.

**Attacks:**
- A causal running percentile over the radio received so far.
- Train "on a line" against "not on a line" as an explicit head. Idle and walk_edge windows are never
  used in training now, so the model has no negatives.

### 11.7 Training data use

**The problem:** only walking windows train the networks, one day's geometry is easy to overfit (item
3), and the training recipe runs a fixed 24 epochs with no early stopping on validation.

**Attacks:**
- **Early stopping on a validation session inside the split.**
- **More regularisation:** stronger dropout, weight decay, mixup across sessions.
- **Domain-adversarial training** that cannot tell Room A from Room B. It was tried on Room A days
  with little success, but the room difference is larger than the day difference.
- **Test-time adaptation** beyond AdaBN on the tracking heads themselves, from each recording's idle
  radio. D1's normalisation is the simplest version.

### 11.8 The readers

**The problem:** A2 and the veto read the position head's outputs and embeddings trained on Room A
sessions. In Room B the veto did not help; abstaining did.

**Attacks:**
- Retrain the readers inside the split.
- Replace the veto with abstaining (confirmed in DC2).
- Fold the start-region evidence into the tracking heads, so it is not a separate brittle classifier.

---

## 12. How to test an attack, under the split

1. **Develop on A1, A2 and B1:** train on two, validate on the third, for all three rotations.
   Choose on the pooled validation, weighting the lock and the Room B session (B1) if Room B is the
   priority.
2. **Train the chosen setting once on A1+A2+B1.**
3. **Test once on A3 and B2**, under configuration A, and B for B2. Report committed and lock, both
   lock methods, the four edge lines, and 95 percent intervals, beside the baseline in section 0 and
   the frozen reference.
4. **Log it** in `reports/DEVLOG_TRACKING_2026-09-28.md`: what changed, why, the result.

**The machinery is ready:**
- `pipeline/constrained/pd_cells.py` defines a cell by training sessions, test session and
  normalisation, and runs training, inference, decoding and both locks. D1's cells on the split are
  `d1s*`.
- `pipeline/constrained/pd_report.py` computes the tables.
- A new cell costs about 20 minutes to train on two sessions and 30 on three, plus 5 minutes per test.
