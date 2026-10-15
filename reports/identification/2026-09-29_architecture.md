# The identification system, end to end: architecture and every transformation (2026-09-29 21:49 SAST)

**Purpose.** This document lets Uzayr make decisions about the identification system. It follows one
walk from the radio to the answer on screen and states every transformation, shape, number and
choice on the way. Everything here was read from the code on 29 September, not from memory. File
references are given so each step can be checked.

**Where the results are.**
- The final model's development report is `reports/ID_DEV_FINAL_2026-09-29.md`.
- The identification-walks evaluation is `reports/ID_WALKS_2026-09-29.md`.
- The step-by-step log is `reports/DEVLOG_ID_2026-09-28.md`.

Figures in section 14 are quoted from those.

## Contents

1. [The whole pipeline on one page](#1-the-whole-pipeline-on-one-page)
2. [The hardware and the rooms](#2-the-hardware-and-the-rooms)
3. [What a capture file contains](#3-what-a-capture-file-contains)
4. [The dataset](#4-the-dataset)
5. [Step 1: from bytes to amplitude](#5-step-1-from-bytes-to-amplitude)
6. [Step 2: putting the receivers on one clock](#6-step-2-putting-the-receivers-on-one-clock)
7. [Step 3: cutting a pass and resampling it to 150 Hz](#7-step-3-cutting-a-pass-and-resampling-it-to-150-hz)
8. [Step 4a: the gait features (633 numbers per pass)](#8-step-4a-the-gait-features-633-numbers-per-pass)
9. [Step 4b: the Doppler maps (the CNN's input)](#9-step-4b-the-doppler-maps-the-cnns-input)
10. [Step 5: the eight components](#10-step-5-the-eight-components)
11. [Step 6: calibration to a new session](#11-step-6-calibration-to-a-new-session-test-time-adaptation)
12. [Step 7: fusion and the decision](#12-step-7-fusion-and-the-decision)
13. [Live operation: what exists, what does not](#13-live-operation-what-exists-what-does-not)
14. [How it was evaluated, and what it scores](#14-how-it-was-evaluated-and-what-it-scores)
15. [Decisions you need to make](#15-decisions-you-need-to-make)
16. [File map](#16-file-map)

---

## 1. The whole pipeline on one page

```
 TX (ESP32) ──packets, 2.4 GHz channel 11 (about 143 to 150 per second)──►  RX1, RX2, RX3 (ESP32)
                                                                               │  CSI per packet:
                                                                               │  128 subcarriers,
                                                                               │  int8 imag + real
                                                                               ▼
                                                           host laptop, over USB serial (one .bin per receiver)
                                                                               │
 STEP 1  bytes → amplitude       sqrt(imag² + real²) per subcarrier; keep 103 of 128 subcarriers
 STEP 2  clocks → one timeline   each receiver's own microsecond clock mapped to the host clock
                                 (10 s bins, 5th percentile of the offset, interpolated)
 STEP 3  cut the pass            start press to end press; linear resampling onto a 150 Hz grid
                                 → A: (3 links, n samples, 103 subcarriers), R: (3 links, n) RSSI
                                           │                                     │
            ┌──────────────────────────────┘                                     └────────────────────┐
 STEP 4a  gait features (8,517 computed; 633 used)          STEP 4b  conditioned Doppler map per link
          cadence, rhythm, cycle templates,                          4-70 Hz filter → PCA (PCs 2-4) →
          spectral shape, Doppler contours,                          STFT → log magnitude − mean
          wavelets, modulation depth                                 → (3, 28 freq, ~76 frames)
          + pace = 5 m / (end − start) for 3 components              → windows of 34 frames, hop 4
                   │                                                          │
 STEP 5   5 feature classifiers:                                     3 CNN components:
          RF (per-path z), RF (session-standardised),                CNN (plain), CNN (AdaBN),
          RF + pace, extra trees + pace, LDA + pace                  per-link CNNs (AdaBN), 3 seeds each
                   │                                                          │
 STEP 6   calibration from unlabelled walks of the new session (feature standardisation; AdaBN)
                   └──────────────────────────────┬───────────────────────────┘
 STEP 7   each component → 6 log-probabilities; SUM them (equal weights); normalise; argmax
                                                  ▼
                           "participant P3", with a probability for each of the six
```

**Two separate halves.**
- **Steps 1 to 4** turn radio packets into numbers. They contain no learning; every choice was fixed
  before this development batch.
- **Steps 5 to 7** are the learned model: eight different classifiers, trained on labelled walks, whose
  votes are added.

---

## 2. The hardware and the rooms

**Nodes.** Four ESP32 boards:
- one **transmitter (TX)** sends Wi-Fi packets continuously;
- three **receivers (RX1, RX2, RX3)** each report the channel state information (CSI) of every packet
  they hear.

**Radio.**
- **Band:** 2.4 GHz, channel 11 on every recording in the bank (2,462 MHz, wavelength about 0.122 m;
  the physics code uses lambda = 0.123 m).
- **Rate:** nominally 150 packets per second; 143.1 per second was measured on Room A session 01 RX1.
- **Link:** each receiver streams to the host laptop over USB serial.

**Geometry.** Metres, (0, 0) at the bottom-left of the taped 5 m x 5 m grid; x is the column, y the row.

| node | Room A, and Room B tracking | Room B identification walks |
|---|---|---|
| TX | (2.5, -0.5), below the grid's bottom edge | (2.5, -0.5) |
| RX1 | (2.5, 5.5), above the top edge, opposite the TX | (2.5, 5.5) |
| RX2 | (-0.5, 2.5), left edge, "home" | **(2.0, -0.5), beside the TX** (the "identification spot") |
| RX3 | (5.5, 2.5), right edge | (5.5, 2.5) |

- **Why RX2 moves.** In DC2 (Room B), RX2 was moved beside the TX for each participant's identification
  walks and returned home for their tracking walks. A receiver beside the transmitter is close to
  monostatic, so it sees the walker's full Doppler (bistatic factor F about 0.98 along line A).
- **The other links on line A:**
  - RX1 sits on the TX-RX1 line, so a walker on line A changes that path length hardly at all (F = 0);
  - RX3 is side-on (F about 0.5).
- **Room A never had RX2 beside the TX.**

---

## 3. What a capture file contains

**One `.bin` per receiver per recording.** The name is `<stem>_RX1.bin`, `_RX2.bin` or `_RX3.bin`,
written by `pipeline/io/capture_logger.py` (protected code, never edited). Its layout:
1. 8 bytes of magic `CSIBIN01`;
2. a little-endian uint32 header length;
3. a JSON header (node id, port, MAC, the frame layout);
4. fixed-width binary frames, one per packet, in arrival order.

**The fields of each frame** (`FRAME_DTYPE`):
- `t_host`, `t_mono`: the host's wall clock and monotonic clock when the frame was read;
- `pkt_id`;
- `local_timestamp`: the receiver's own microsecond clock, uint64, which wraps at 2^32;
- `rssi`, `noise_floor`;
- radio metadata: `ampdu_cnt`, `sig_len`, `rate`, `sig_mode`, `mcs`, `bandwidth`, `smoothing`,
  `not_sounding`, `aggregation`, `stbc`, `fec_coding`, `sgi`, `channel`, `secondary_channel`;
- the CSI payload `data`: **256 bytes = 128 subcarriers x (imag, real), int8, LLTF then HT-LTF**.

**Ground truth: `.gt.json` per recording.** It lists the passes. Each pass has:
- `path_name` (for example `A_fwd`), `direction`;
- `anchor_coords` (the taped marks);
- `anchor_times`: one operator press per metre mark, six per 5 m pass on the identification walks;
- `t_start` (the first press) and `t_end` (the last press), on the host monotonic clock.

**Relabelling.** DC2's identification walks are read through a relabelled copy
(`runs/identify/dc2_src_relabelled/`, built by `pipeline/identify/idrelabel.py`). It fixes one double
press in participant P5's day 2 fast block. It never edits `data/`.

---

## 4. The dataset

The whole dataset is five sessions. No more data will be collected.

| session | room | what | passes |
|---|---|---|---|
| A1, A2, A3 (DC1) | A | tracking walks, 6 people x 20 passes (12 paths: lines A to D both ways, twice each; edge lines E_col1, E_col5, E_row1, E_row5 once each) | 120 each |
| B1 (DC2 day 1) | B | tracking walks (120) + identification walks (240: natural 10 cycles, slow 5, fast 5 per person; a cycle is one away and one towards pass on line A) | 360 |
| B2 (DC2 day 2) | B | tracking walks (120) + identification walks (179: 5 cycles per pace; P5's fast pass 10 excluded) | 299 |

- **Totals:** the bank holds **1,019 passes** (`runs/identify/dev/bank/`).
- **Pass length:** median 4.26 s (range 2.62 to 7.16 s).
- **Participants:** six, anonymised P1 to P6. Their names exist only under `runs/` and are asserted absent
  from every written output.
- **Paths:** identification walks are on line A (x = 2.5). `A_fwd` walks **away** from the TX (y 0 to 5)
  and `A_rev` walks **towards** it.
- **Other recordings:**
  - empty rooms: 30 s at the identification spot and at home, per participant-day;
  - calibration walks (`_C_walk`) and free-movement recordings (`DEMO_free`) are never used.

---

## 5. Step 1: from bytes to amplitude

File: `pipeline/identify/raw_access.amplitude_from_frames`.

1. **Amplitude.** The 256-byte payload is read as int8 and split into imag (even bytes) and real (odd
   bytes):
   - amplitude = sqrt(imag² + real²), per subcarrier, per packet;
   - the result is (packets, 128);
   - phase is discarded: the system is amplitude-only.
2. **Subcarrier selection, stage 1.** `id19_bank.KEEP` drops 22 of the 128 positions:
   - 0, 1 and 64, which are the DC and guard positions;
   - 27 to 37 and 96 to 103, the unused band edges;
   - this leaves 106.
3. **Subcarrier selection, stage 2.** `id19_featbank.SC` drops subcarriers 93, 94 and 95, measured as
   null on all three links on 23 September. This leaves **103 subcarriers**.

**Output:** for each receiver, a stream of (time, 103 amplitudes, RSSI).

---

## 6. Step 2: putting the receivers on one clock

File: `pipeline/identify/id29_dc2_score._link` (the frozen "id29 clock map"). The live copy is
`pipeline/live/identify.link_from_frames`.

**The problem.** Each frame carries two useful times.
- `t_mono`: the host's clock at the moment the frame was read. The host drains the serial buffer about
  20 times a second and stamps a whole batch at once, so `t_mono` jumps in about 50 ms steps. Used
  directly, it would quantise the signal onto a 20 Hz grid and destroy everything above 10 Hz.
- `local_timestamp`: the receiver's own microsecond clock. It is precise, at the true packet rate, but
  it has an unknown offset from the host clock and drifts. It also wraps at 2^32 microseconds (about
  71.6 minutes); wraps are detected (a backwards jump of more than 1 s) and unwrapped.

**The mapping.**
1. lt = local_timestamp x 10^-6, unwrapped.
2. offset = t_mono − lt, for every frame.
3. The recording is cut into **10 s bins of lt**.
4. For every bin with at least 20 frames:
   - centre = the median lt in the bin;
   - value = the **5th percentile** of the offset in the bin.

   The 5th percentile picks the frames read with the least serial delay.
5. Every frame's corrected time is t̂ = lt + (offset interpolated linearly between bin centres, held
   flat beyond the first and last centres). With fewer than 2 bins, t̂ = t_mono.
6. Frames are sorted by t̂.

**Result:** all three receivers' packets on the host's timeline, the same timeline as the operator's
presses, at their true spacing.

**Why this matters live.** A pass's clock mapping depends on the bin holding its last packet and the
next bin. Those are final only once both bins have filled. So a live decision that must equal the
offline one exactly has to wait **21 s after the end press** (`pipeline/live/identify.WAIT_S` = 2 x
10 s + 1 s).
- At a 5 s wait the mapping is slightly different. Features shift, but decisions barely change
  (section 13).

---

## 7. Step 3: cutting a pass and resampling it to 150 Hz

File: `pipeline/identify/idx_bank.pass_items` (the same code built the whole bank).

1. **The pass** is the span from its start press t0 to its end press t1.
2. **The grid** is t0, t0 + 1/150, t0 + 2/150, ... up to t1: n = (t1 − t0) x 150 samples, 639 for a
   4.26 s pass.
3. **Resampling.** Each subcarrier's amplitude, and each link's RSSI, is linearly interpolated at the
   grid times from the two nearest packets (`id19_bank._interp_cols`). Beyond the data the edge values
   are held.
4. **Output:**
   - **A**, shape (3 links, n, 103): amplitude, float64;
   - **R**, shape (3, n): RSSI.
5. **Pace**, also recorded: **speed = 5.0 m / (t1 − t0)** for identification walks; for tracking walks
   it is path length / duration. This is the only use of the press times beyond cutting.

No filtering or cleaning is applied here. The bank uses the raw resampled amplitude; Hampel outlier
removal is not applied to the model's inputs.

---

## 8. Step 4a: the gait features (633 numbers per pass)

File: `pipeline/identify/id19_featbank.pass_features(A, R)`, with the functions in
`pipeline/identify/idmax_features.py`.

**Principle.** The feature code never reads speed, duration, anchors or press times; the presses only
decide where the pass is cut. Every feature is a shape or a ratio, so absolute gain cancels.

### 8.1 Frequency bands (4th-order Butterworth, zero-phase `sosfiltfilt`, 150 Hz sampling)

| band | Hz | carries |
|---|---|---|
| `b03_2` | 0.3 to 2.0 | slow body sway |
| `b08_35` | 0.8 to 3.5 | the step and stride rhythm (the "gait envelope") |
| `dop` | 4.0 to 70.0 | Doppler from moving body parts |
| `full` | 0.3 to 70.0 | everything |

### 8.2 Channels: 103 subcarriers reduced to a few signals per link

- `mean`: the band-limited mean across subcarriers.
- `rms`: the RMS across the band-limited subcarriers (the motion energy envelope), re-band-limited to
  the gait band.
- `pca`: a **per-pass** PCA of the band-limited subcarriers.
  - The data are mean-centred and the covariance is eigen-decomposed; the top n components are kept.
  - Each component's sign is set so its skewness is positive, which makes components comparable
    across passes.
  - The PCA is per pass, never per recording, so the basis cannot encode who is walking.

### 8.3 Families

The model uses the set `U_all_gait` on the `mean@b08_35` channel, all three links, **633 of the 8,517
computed columns** (`idmax_eval.FEATURE_SETS`):

| family | per link | what it measures |
|---|---|---|
| `cad` cadence | 6 in total | Step rate, estimated three ways on three channels per link and resolved by agreement across estimators and links (`resolve_cadence`); also the agreement fraction and the spread between links. |
| `rhy` rhythm | 73 | The autocorrelation at one step and one stride; 63 autocorrelation-shape samples; cadence sharpness; relative power at the step, stride, 2-step and 3rd harmonic; step alternation, step CV, step symmetry. All tempo-normalised by the resolved cadence. |
| `tplacf` cycle templates | 43 | The average stride cycle, cut by the autocorrelation and resampled to 32 points (circularly aligned to its maximum); 8 harmonic magnitudes; cycle-to-cycle correlation and variance; half-cycle symmetry. |
| `spec` spectral shape | 23 | 8 relative band powers, centroid and spread in units of the band (0 to 1), flatness, and 12 cepstral coefficients of the log filterbank energies (MFCC-style). |
| `dop` Doppler contours | 47 | From a 0.2 s STFT of PCs 2 onwards of the `dop` band, summed over PCs. The 50th- and 95th-percentile energy contours (torso and leg proxies) as 16-point per-cycle shapes, their CV and periodicity; leg/torso, q25/torso and q75/torso ratios; an 8-point profile over the walk. All normalised by the pass's own median torso contour, so no absolute rate enters. |
| `wav` wavelets | 19 | Relative discrete-wavelet energy per level (db4, 7 levels) and relative Morlet CWT energy at 12 log-spaced scales from 0.5 to 20 Hz, on the full-band mean. |
| `mod` modulation | 4 | How strongly the walk modulates the link relative to its own level: gait-band and Doppler-band modulation depth, RSSI SD, dispersion across subcarriers. |

Totals: 210 per link x 3 links, plus 3 cross-link cadence features, = 633.

**Output:** one row of 633 numbers per pass. Missing values (undefined features) are NaN and are
imputed later from training medians.

**Pace is not in this row.** Three components append it as one extra column (section 10).

---

## 9. Step 4b: the Doppler maps (the CNN's input)

File: `pipeline/identify/idv2_core.conditioned_map`, applied to each link separately.

**Per link:** the input is (n samples, 103 subcarriers) and the output is a map of 28 frequencies x T
frames.
1. **Band-pass** 4 to 70 Hz: 4th-order Butterworth, zero-phase, over the whole pass.
2. **Per-pass PCA** of the 103 filtered subcarriers:
   - mean-centred; top 4 components by the covariance eigen-decomposition; positive-skew sign rule;
   - **PC1 is discarded and PCs 2 to 4 kept.** PC1 mostly carries common-mode power changes rather than
     Doppler.
3. **Short-time Fourier transform** of each of the 3 PCs:
   - 32-sample Hann window (0.213 s), 24 samples overlap, so the hop is 8 samples (53.3 ms; 18.75
     frames per second);
   - FFT length 64, so the bins are 2.34 Hz apart;
   - no boundary padding, so T = floor((n − 32) / 8) + 1 frames; about 76 for a 4.26 s pass.
4. **Magnitude,** summed over the 3 PCs.
5. **Keep the 28 bins from 4.69 to 67.97 Hz.**
6. **log(magnitude + 1e-6),** then **subtract the map's own mean** so absolute gain cancels.

**Stack the three links:** a pass becomes **(3, 28, T)**, float32. It is stored in
`runs/identify/dev/bank/maps.pkl`.

**Windows** (`idv2_core.windows`):
- the map is cut into windows of **34 frames** (about 1.97 s of signal), hop **4 frames** (0.213 s);
- only inside the pass, never padded;
- a pass of T frames gives floor((T − 34) / 4) + 1 windows: a median of 11 per pass, at least 4 in
  the bank;
- each window is **(3, 28, 34)**;
- each window also carries the pass's direction as a flag: 0 for `*_fwd`, 1 for `*_rev`.

**What the picture shows.** The torso moving at speed v Doppler-shifts the reflected path by
f = 2 F v / lambda.
- On RX2 beside the TX at 1.2 m/s, that is about 19.5 Hz. The measured torso contour is 18.75 Hz.
- Arms and feet, which move faster, would sit higher; section 14.5 tests whether they are visible.

---

## 10. Step 5: the eight components

Each component maps a pass to **six log-probabilities**, one per enrolled person. Each is normalised
so the probabilities sum to 1, with a floor of 1e-9 on any probability.

### 10.1 The five feature components (on the 633 gait features)

All five start the same way, fitted on the **training passes only**:
1. **Imputation.** NaN in a column is replaced by that column's training median. Columns whose
   training median is undefined are dropped.
2. **Dead columns.** Columns constant in training are dropped (SD at most 1e-12).
3. **Standardisation,** one of two kinds:
   - **per-path z** (`rf` only): each walking path (`A_fwd`, `B_rev` and so on) gets its own mean and
     SD, taken from training passes on that path (if at least 3; otherwise the global training mean
     and SD). A test pass is standardised with its path's training statistics. **Nothing about the
     test session is used.**
   - **session standardisation ("prior")**, used by the other four:
     - Training passes are standardised **within their own session, per path**, so every training
       session is centred and scaled on itself.
     - A test pass is standardised per path with the mean and SD of its **calibration rows**: other,
       unlabelled walks from the same new session (section 11), when there are at least 10.
     - Otherwise it uses the global training mean and SD.
     - This removes room and day offsets.

| component | features | standardisation | classifier |
|---|---|---|---|
| `rf` | 633 gait | per-path z | random forest: 300 trees, `max_features` sqrt, `random_state` 0 |
| `rf_prior` | 633 gait | session | the same random forest |
| `rf_pace_prior` | 633 gait **+ pace** (one column, m/s) | session | the same random forest |
| `et_pace_prior` | 633 gait + pace | session | extra trees: 300 trees, sqrt, `random_state` 0 |
| `lda_pace_prior` | 633 gait + pace | session | linear discriminant analysis, `lsqr` solver, automatic (Ledoit-Wolf) shrinkage |

**Output of each:** `predict_proba`, then log, reordered to P1 to P6. File: `pipeline/identify/idw_core.py`
(`PerPath`, `Prior`, `train`, `apply`). Arithmetic: `idx_dev.features` and `idx_dev.prior_standardise`.

**Pace** is one column among 634 in three of the eight components. It is never compared on its own;
S0, which does exactly that, is kept only as a control.

### 10.2 The CNN (CNN-v2), layer by layer

File: `pipeline/identify/idv2_core.make_net`. Input: a window **x** of shape (C links, 28, 34), with
C = 3 for the 3-link net or 1 for a per-link net, and the direction flag **d** (one-hot, 2 values).

| layer | operation | output shape (C = 3) |
|---|---|---|
| conv1 | 3x3 convolution, 16 filters, padding 1 → BatchNorm → ReLU | 16 x 28 x 34 |
| pool1 | max-pool over **time only** (1 x 2) | 16 x 28 x 17 |
| conv2 | 3x3 convolution, 32 filters → BatchNorm → ReLU | 32 x 28 x 17 |
| pool2 | max-pool over time (1 x 2) | 32 x 28 x 8 |
| conv3 | 3x3 convolution, 32 filters → BatchNorm → ReLU | 32 x 28 x 8 |
| time average | mean over the 8 time steps; **frequency is kept** | 32 x 28 = 896 |
| concatenate | append the direction one-hot | 898 |
| dropout | p = 0.3 (training only) | 898 |
| head | linear 898 → 6 | 6 logits |

**Size and design.**
- **Parameters:** 19,890 (3-link) and 19,602 (1-link).
- **Frequency is never pooled:** the network keeps where energy sits in frequency and averages over
  time.

**Input normalisation** (`norm_stats`, `apply_norm`):
- per link and per direction, the mean and SD over all training windows;
- applied to training and test windows alike;
- a direction absent from training uses the other direction's statistics.

**Training** (`train_cnn`), per seed:
- **Optimiser:** Adam, learning rate 1e-3, weight decay 1e-4, with a cosine decay of the learning rate
  to 0.
- **Length:** 6,000 steps of 64 windows. There is no validation split and no early stopping.
- **Class-balanced sampling:** each window in a batch picks a person uniformly, then a window of that
  person uniformly.
- **Augmentation, per window:**
  - a time mask of 0 to 4 frames and a frequency mask of 0 to 2 bins (set to 0);
  - a per-link log-gain offset drawn from N(0, 0.2);
  - each link dropped with p = 0.15 (3-link net only);
  - added noise with SD 0.02.
  - Never a time shift, stretch or frequency shift.
- **Loss:** cross-entropy.
- **Seeds:** 0, 1 and 2 give three independent nets per CNN component.

**From windows to a pass** (`pass_logp`): each window gets log-softmax scores. **A pass's score is the
mean over its windows**, and each seed's pass scores are normalised. The three seeds are then
averaged and normalised again.

### 10.3 The three CNN components

| component | nets | adaptation |
|---|---|---|
| `cnn` | 3-link CNN-v2, 3 seeds | none |
| `cnn_prior` | **the same trained nets** | **AdaBN** (section 11) |
| `cnn_perlink_prior` | one 1-link CNN-v2 per receiver (RX1, RX2, RX3), 3 seeds each (9 nets) | AdaBN per net; the three links' log-probabilities are **summed** (product fusion), then normalised |

**One trained model is 12 nets:** 3 three-link and 9 one-link, each trained for 6,000 steps. On the Mac's
GPU (MPS) one full training (the five classifiers plus 12 nets) takes about 16 minutes.

---

## 11. Step 6: calibration to a new session (test-time adaptation)

**What calibration is.** Before scoring a walk in a new room or on a new day, the model looks at other
walks recorded in that session. It uses them **without labels**, to re-centre itself. Two mechanisms:
- **Feature standardisation** (the four "prior" feature components): the session's own mean and SD
  per path, computed from the calibration walks (at least 10, else training statistics).
- **AdaBN** (`cnn_prior`, `cnn_perlink_prior`):
  - a copy of each trained net is made;
  - its BatchNorm layers' running mean and variance are reset and recomputed in **one forward pass,
    with no labels and no gradients**, over the calibration walks' windows;
  - the weights are untouched.

  This moves every layer's statistics to the new room.

**Which walks count as calibration.** Three settings were compared (`idw_core.calibration_groups`):

| setting | calibration walks for a test walk | live meaning |
|---|---|---|
| **CAL-others** | every walk of that session **by the other five people** | a household system warmed up on everyone else's walks |
| CAL-causal | every walk of that session **recorded before** this one | a system that adapts as the day goes on |
| CAL-none | none; training statistics only | out of the box |

- **CAL-others uses the label only to exclude:** the test walker's own walks are left out, and nothing
  is fitted on labels.
- **The dev batch used CAL-causal.** The identification-walks brief showed CAL-others is as good or
  slightly better (-2.22 [-6.11, 1.67]), and CAL-none loses only 2 to 4 points.

---

## 12. Step 7: fusion and the decision

File: `idw_core.apply`, which follows `idx_all_eval`'s rule "all".

1. **Collect.** The eight components each give six normalised log-probabilities:
   L_rf, L_rf_prior, L_rf_pace_prior, L_et_pace_prior, L_lda_pace_prior, L_cnn, L_cnn_prior,
   L_cnn_perlink_prior.
2. **Sum them** with equal weights, one sum per person. This is a product of the probabilities, as
   if the components were independent witnesses.
3. **Normalise** (subtract the log-sum-exp) to get six probabilities that sum to 1.
4. **Decide:** the answer is the person with the highest probability. The runner-up gives the
   "top-2" answer.

**Why equal weights and no selection.** In development, every rule that chose components from inner
validation did worse than this. The best component differs from session to session, and
four training sessions cannot predict which will win on a fifth. Summing is also robust when one
component is badly wrong. Summing all eight beat the pooled pick by +4.44 [0.83, 8.61] in Room A
(`reports/ID_DEV_FINAL_2026-09-29.md`, section 4).

**Several walks by the same person** (round trip, k walks): add their summed log-probabilities, then
take the argmax.

**Smaller groups** (a household of g people): take the argmax over those g people's columns only.

---

## 13. Live operation: what exists, what does not

### 13.1 What the live app runs today for identification

`pipeline/live/identify.py` and `pipeline/live/__main__.py`:
- **The model is the old frozen PRIMARY random forest,** not the final ensemble.
  - It is refitted on the enrolled passes for every new pass.
  - S0 (speed alone) is shown beside it.
- **Only a replay exists.** `python3 -m pipeline.live replay-identify` runs gate 5 on id29's synthetic
  DC2 recordings.
- **The rig refuses identification.** `python3 -m pipeline.live rig --mode identify` stops with
  "REFUSED: the identification rig mode needs an enrolment set (DC2 day 1 natural passes)".
- **So live identification on the boards is not built.**

**What the live identification recording object already does** (`LiveIdRecording`):
1. it buffers each receiver's frames;
2. it records the start and end presses;
3. it extracts a pass only once every receiver has data up to **end press + 21 s**, so the clock map
   is final (section 6);
4. it builds the pass's features exactly as the offline extractor does.

### 13.2 What the final ensemble does live (measured by replay)

`pipeline/identify/idx_live.py` replays each held-out session pass by pass, in recording order. It uses
only the frames that had arrived by the decision time, and retrains the model on the other four
sessions.

| wait after the end press | live features = offline | accuracy (Room A / Room B, leave-one-session-out) | median decision latency |
|---|---|---|---|
| 21 s | **yes, on every pass of all five sessions** | 39.72 / 30.00 (identical to offline) | about 21.5 s |
| 5 s | no (about 6 % of passes equal within tolerance), but 95 % of decisions unchanged | **40.28 / 31.67** | **5.3 to 5.6 s** |
| 1 s (B2 only, batch 2 model) | no | 28.76 on B2 (offline 29.77) | 1.6 s |

**Where the time goes.**
- Compute per pass: feature extraction 0.2 to 0.6 s, the whole eight-component model about 0.08 s.
- Everything else is the wait for the clock map.

### 13.3 What putting the final model live needs (not done; section 15)

1. **Train on the chosen set and save it.** Train the ensemble on the chosen training set and save it
   (`idw_core.train` already saves everything under `runs/identify/idwalks/models/`). The Room A plus
   Room B model now exists for each test day, `TR-AB_toB1` and `TR-AB_toB2`. A deployment model would
   be trained on all five sessions.
2. **An enrolment set.** Labelled walks of the people to be recognised: the training set itself.
3. **Calibration walks.** Unlabelled walks in the demo session by several people (CAL-others), or the
   walks so far that day (CAL-causal).
4. **Wire it in.** Replace `LiveIdentifier`'s refitted random forest with `idw_core.apply` on the saved
   model, choose the wait (21 s exact or 5 s), and lift the rig's refusal.
5. **The receivers:** RX2 beside the TX, as in the identification walks; Room A data were recorded
   with RX2 at home.

---

## 14. How it was evaluated, and what it scores

### 14.1 Leave one session out (the development standard, `ID_DEV_FINAL`)

**Protocol.**
- Train on four of A1, A2, A3, B1, B2, test on the fifth, rotating.
- Tracking passes scored (120 per session).
- CAL-causal calibration; CNNs 6,000 steps, 3 seeds.
- 95 % intervals by bootstrap over participants.

| | A1 | A2 | A3 | B1 | B2 | Room A | Room B |
|---|---|---|---|---|---|---|---|
| final ensemble | 36.67 | 47.50 | 35.00 | 26.67 | 33.33 | **39.72 [27.50, 46.94]** | **30.00 [19.58, 39.17]** |
| the frozen Room A cross-day headline (reference) | | | | | | 15.83 [10.28, 21.67] | |

### 14.2 The identification walks (`ID_WALKS`)

**Protocol.**
- Room B's identification walks only; test day B2 (trained without it) or B1.
- CAL-others calibration.
- Natural walks pooled over both test days (n 180).

| training set | natural, both directions | slow | fast |
|---|---|---|---|
| **Room A + the other Room B day (TR-AB)** | **46.67 [29.44, 66.11]** | 35.00 | 36.97 |
| the other Room B day, identification + tracking (TR-B+) | 33.89 | 35.00 | 29.41 |
| the other Room B day's identification walks only (TR-B) | 28.33 | 30.00 | 38.66 |
| S0: speed alone (control) | 38.33 [20.00, 61.11] | 17.50 | 16.81 |

- **Room A helps:** +18.33 [8.33, 27.78] over TR-B.
- **Against speed:**
  - at natural pace the model is **not distinguishable from speed alone** (+8.33 [-14.44, 27.22]);
  - on fast walks it beats speed (+20.17 [4.24, 32.77]), because speed falls to chance when people
    change pace and the model does not.

### 14.3 Deployment measures (TR-AB, CAL-others, natural)

| measure | score | chance |
|---|---|---|
| single walk, top-1 | 46.67 | 16.67 |
| single walk, top-2 | 69.44 | 33.33 |
| round trip (away + towards) | 50.00 | 16.67 |
| three walks | 61.11 | 16.67 |
| household of 2 | 78.44 | 50.00 |
| household of 3 | 65.72 | 33.33 |

### 14.4 Direction

- Towards 52.22 against away 41.11 on 90 round trips: -11.11 [-23.33, 1.11], **not detectable**.
- Identity learned in one direction works in the other.

### 14.5 Physics (identity-blind)

- **Torso:** the torso Doppler follows the bistatic prediction (18.75 Hz measured against 19.5
  predicted on RX2).
- **Limb bands:** the 35 to 75 Hz band sits above the empty room in 53 % of natural walks, but features
  built from it add nothing (+0.56 [0.00, 1.67]).
- **Stride rhythm:** visible in 3 % of walks.
- **So:** no usable limb Doppler at 150 packets per second.

### 14.6 Start press only

- A causal end detector on RX2 misses the end by about 2 s.
- Accuracy drops by 14.44 [-26.67, -2.78]. **Keep both presses.**

### 14.7 The limits that apply to every figure

- **Sample size:** six people, five sessions. Intervals are 20 to 37 points wide, so differences under
  about 5 to 10 points cannot be told apart.
- **Uneven people:** one person is identified 87 % of the time and another 20 %.
- **Development evaluation, all data seen:** the ensemble's components were chosen over batches in
  which test results were visible; only the latest brief's rules were fixed before its trainings.
- **Pace:** at natural pace, speed alone does about as well.

---

## 15. Decisions you need to make

For each: the options, what the data say, and my recommendation.

**D1. Which training set goes into the live model?**
- **Options:**
  - Room A plus Room B (TR-AB);
  - Room B only (TR-B or TR-B+).
- **Data:** TR-AB is clearly better: +18.33 over TR-B and +12.78 over TR-B+, both intervals above zero.
- **Recommendation:** TR-AB, retrained on **all five sessions** for the demo. The saved TR-AB models
  each leave out one Room B day.

**D2. Build live identification on the boards at all?**
- **Current state:** the rig refuses identification, and the replay uses the old frozen random forest.
- **Cost:** about 1 to 2 hours of wiring (section 13.3), plus one training (about 16 minutes on the GPU).
- **Recommendation:** yes, if identification is to be demonstrated live. Otherwise demonstrate by
  replay (`idx_live`), which is causal and measured.

**D3. How long to wait before deciding?**

| wait | behaviour |
|---|---|
| 21 s | exactly equal to offline, provably |
| 5 s | 95 % of decisions unchanged and accuracy the same within noise (Room A 40.28 against 39.72) |
| 1 s | about one point lower |

- **Recommendation:** 5 s for the demo, and state that 21 s reproduces the offline figures exactly.

**D4. One press or two?**
- **Data:** two. Start-only loses 14.44 points with the only end detector the brief allowed (RX2
  energy).
- **Option:** a different end cue, such as tracking's position estimate, was ruled out by that brief.
  It would need your decision to try.

**D5. How to calibrate in the demo?**
- **Options:** CAL-others, CAL-causal or CAL-none.
- **Data:** they differ by at most 4 points, and CAL-others is best.
- **Recommendation:**
  - record a few warm-up walks by **several people** in the demo room before identifying;
  - AdaBN needs at least one walk, and feature standardisation at least 10;
  - never calibrate only on the person being identified.

**D6. What to report as the result?**
- **Options:**
  - the single-walk top-1 (46.67 on identification walks; 39.72 / 30.00 leave-one-session-out on
    tracking walks);
  - the deployment measures (household of 2: 78.44; top-2: 69.44; three walks: 61.11).
- **Recommendation:** lead with single-walk top-1 and give the deployment measures beside it, as the
  brief required. Never replace one with the other.

**D7. How to frame gait against pace in the thesis?**
- **Data:** at natural pace the model is not distinguishable from speed alone. Its advantage is
  robustness: when people change pace, speed falls to chance and the model holds at 35 to 37 %.
- **Recommendation:** claim "identification that survives changes of pace", not "gait beats pace".

**D8. Direction and physics claims.**
- **Direction:** say there is no detectable direction effect.
- **Limb Doppler:** say the ESP32 at 150 packets per second gives no usable limb Doppler (energy is
  there in half the walks, but it adds nothing).
- **Torso:** the torso Doppler matching the bistatic prediction is a clean, identity-blind physics
  result worth keeping.

---

## 16. File map

| stage | file |
|---|---|
| capture format (protected) | `pipeline/io/capture_logger.py` (`FRAME_DTYPE`, `read_capture_file`) |
| bytes to amplitude | `pipeline/identify/raw_access.py` (`amplitude_from_frames`) |
| subcarrier selection | `pipeline/identify/id19_bank.py` (`KEEP`), `pipeline/identify/id19_featbank.py` (`SC`, `NULL_SC`) |
| clock map | `pipeline/identify/id29_dc2_score.py` (`_link`), live copy `pipeline/live/identify.py` (`link_from_frames`) |
| pass cutting, resampling, the bank | `pipeline/identify/idx_bank.py` (`recordings`, `pass_items`, `build`); `runs/identify/dev/bank/` |
| relabelled DC2 source | `pipeline/identify/idrelabel.py`; `runs/identify/dc2_src_relabelled/` |
| gait features | `pipeline/identify/id19_featbank.py` (`pass_features`), `pipeline/identify/idmax_features.py` |
| column sets, classifiers | `pipeline/identify/idmax_eval.py` (`FEATURE_SETS`, `make_model`, `prep`) |
| Doppler maps, CNN, training, AdaBN | `pipeline/identify/idv2_core.py` |
| the dev levers and session standardisation | `pipeline/identify/idx_dev.py`, `pipeline/identify/idx_sel.py`, `pipeline/identify/idx_loso.py` |
| every component saved; ensemble evaluation | `pipeline/identify/idx_all.py`, `pipeline/identify/idx_all_eval.py` |
| train-and-save, apply-with-calibration | `pipeline/identify/idw_core.py`, `pipeline/identify/idw_run.py` |
| identification-walks evaluation | `pipeline/identify/idw_eval.py`, `idw_physics.py`, `idw_starts.py`, `idw_extra.py`, `idw_setup.py` |
| live replay of the final model | `pipeline/identify/idx_live.py` |
| live app (tracking and the old identification) | `pipeline/live/` (`__main__.py`, `identify.py`, `screen.py`) |
| saved models | `runs/identify/idwalks/models/<set>_<fold>/` (`feat_*.pkl`, `cnn3_seed*.pt`, `cnn_link*_seed*.pt`, `*_norm.pkl`, `meta.json`) |
| reports | `reports/ID_DEV_FINAL_2026-09-29.md`, `reports/ID_WALKS_2026-09-29.md`, `reports/DEVLOG_ID_2026-09-28.md` |

---

## Addendum, 2026-09-30 04:21 SAST: changes adopted by the identification audit

The audit (`reports/ID_AUDIT_2026-09-30.md`, brief `reports/BRIEF_ID_AUDIT_2026-09-29.md`) adopted two bug
fixes. Everything above describes the system before them. Nothing else changed: no candidate met the
audit's rule.

1. **B-1: the gait feature set is 630 columns, not 633.**
   - The three `wav|mean@full|RX{1,2,3}|0|dwt_6` columns (the 7th db4 wavelet level) are removed.
   - The reason: a 7-level decomposition needs more samples than a walk under about 6 s has. The
     columns were NaN on 94.6 % of passes and imputed with the training median, so they marked long
     (slow) walks, a pace proxy inside the gait set.
   - Code: `pipeline/identify/idz_bank.columns_v2`.
2. **B-2: the Doppler map's log uses a relative constant.**
   - Step 6 of section 9 becomes log(magnitude + 1e-6 x the map's median summed magnitude), per link
     and pass, instead of log(magnitude + 1e-6), so the map is exactly gain-invariant.
   - On real passes this moves map values by at most 5e-5.
   - Code: `pipeline/identify/idz_bank.conditioned_map_v2`; bank `runs/identify/audit/bank_v2`.

**Figures after the fixes:**
- identification walks (TR-AB, CAL-others, natural): **43.33 [26.11, 62.78]** (was 46.67);
- leave one session out on tracking passes: **Room A 39.44 [26.11, 48.33], Room B 30.00 [19.58, 39.17]**
  (was 39.72 and 30.00);
- models: `runs/identify/audit/models/B1_toB2`, `B1_toB1` and `final_loso_*`.

**Corrections to statements above (from the audit's measurements):**
- the 103 CSI entries are 54 unique subcarriers (49 in both LLTF and HT-LTF, 5 in one);
- the packet rate is about 149 per second, so the Doppler ceiling is about 74.5 Hz;
- the AGC `gain` field is 1.0 throughout (the firmware reports none);
- step or stride rhythm is visible in about 30 % of natural identification walks, not 3 %.

---

## Addendum, 2026-09-30 13:44 SAST: the one-press engine replaces steps 3, 6, 7 and section 13

The engine brief (`reports/BRIEF_ID_ENGINE_2026-09-30.md`, rules in `runs/identify/engine/PLAN.md`,
results in `reports/ID_FINAL_2026-09-30.md`) made one engine the live app and the thesis model.
Everything above still describes the two-press reference system.

1. **Step 2, the clock.** The frozen centred map is replaced by a causal clock per receiver:
   - the offset is the 5th percentile of (t_mono minus local time) over the frames that arrived in the
     trailing 20 s (at least 20 frames, otherwise t_mono);
   - a wrap is unwrapped; any other backwards jump of more than 1 s is a reboot and restarts the
     estimate.
   - It agrees with the frozen map to 0.51 ms (99th percentile) inside the windows.
2. **Step 3, the pass.** The end press is gone. The one press sets t0, and the window is
   [t0, t0 + 3.0 s].
   - The decision comes at the first frame arrival at which every receiver has a frame past t0 + 3 s on
     the causal clock, or at t0 + 4 s.
   - Tracking passes use their first 3 s.
3. **Steps 4a and 4b** are unchanged (the 630 v2 features and the v2 maps), computed on the 3 s window.
   **GS was tested and not adopted** (-2.00 [-4.00, +0.50] on 600 tracking passes).
4. **Direction and pace, new.**
   - **Direction:** the sign of the slope of RX2's 10 to 35 Hz energy (96.9 % on 419 walks).
   - **Pace:** Wi-Fi speed, v = f_torso x 0.123 / (2 F) on the best link, replaces press speed as the
     single pace column. Press speed survives only as the S0 control.
5. **Step 5, the model.** The same eight components, retrained on the engine's own bank
   (`runs/identify/engine/bank_T3.0`). The models are `runs/identify/engine/models/`:
   - `loso_{A1,A2,A3,B1,B2}`;
   - `deploy_all5` for the rig.
6. **Step 6, calibration.** Every earlier window of the session (causal), updated after each decision.
7. **Section 13, live.**
   - `python3 -m pipeline.live rig --mode identify` runs the engine
     (`pipeline/live/identify_engine.py`).
   - `replay-identify --session <S> --realtime` renders a recorded session through the same app.
   - Decisions are JSON lines (`reports/ID_LIVE_INTERFACE.md`).
   - The median latency is 0.42 s after the window, usually before the walk ends.
8. **The figures now:**
   - identification walks: **36.11 [24.44, 52.22]** (S0 38.33);
   - leave one session out: **Room A 30.83, Room B 29.17**.

---

## Addendum, 2026-09-30 18:18 SAST: the extras brief (no engine change; the rig run through the rig path; the display)

The record is `reports/ID_EXTRAS_2026-09-30.md`, under the brief `reports/BRIEF_ID_EXTRAS_2026-09-30.md`.

1. **Section 2 changed nothing.** None of the four candidates met the rule: precise Wi-Fi speed, the speed
   profile, offset training windows, and the lean correction. `engine.py`, its models and the PLAN's
   parameters are as the previous addendum describes, and frozen again.
2. **The recorded-stream source** (`pipeline/live/identify_recorded.py`):
   - **What it does:** stands in for the three serial ports. It releases a recorded session's frames as
     the `CsiRecord`s the serial reader produces, in recorded `t_mono` order, and injects only the
     start presses as space-bar key events.
   - **Tracking recordings** carry their known routes with the stream.
   - **Command:** `python3 -m pipeline.live.identify_engine rig --source recorded --session B2
     [--speed 1|max] [--from <recording>] [--render natural]`.
   - The serial path (`--source serial`, the default) is unchanged.
3. **The time base.** The consumer now polls the engine with the tick's own time. It used to read the host
   clock, which is correct on the boards (the same clock) but wrong for recorded streams.
4. **The guard.** A recorded stream refuses any model trained on the streamed session (training sessions
   from the model's manifest, or from its `train_rows.npy` and bank). The deployment model stays the
   boards' default.
5. **The display** (`EngineScreen`):
   - names instead of codes;
   - "adapting to this room: n walks seen" (no warm-up is ever asked for);
   - in recorded streams and replays, "truth: <name>" in green or red, and "correct k of n";
   - the truth is read after each decision and never enters the engine.
6. **The JSON lines:** schema `id_engine_decision_v2` adds `top_name`, `runner_up_name` and
   `truth_name`, and keeps every v1 field.
