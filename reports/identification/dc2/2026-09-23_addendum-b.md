# Pre-registration addendum B: DC2 identification, per-person slot design

**Written on 2026-09-23 at 18:48 SAST; P2, P3 and P6 amended at 19:20, 19:35 and 19:55 SAST, before freezing.** No DC2 data existed at the time of writing: `data/room_B`
did not exist. Its SHA-256 is recorded, beside the unchanged original pre-registration's, in
`runs/IDENTIFICATION_FROZEN_2026-09-23e.json`, which references 23c and supersedes nothing. No
identification 23d freeze exists.

**This addendum replaces sections 1 and 3 of `reports/PREREG_ID_DC2_2026-09-23.md`** (data and
analyses) and its statistics clause. The original file is not edited. The scorer is
`pipeline/identify/id29_dc2_score.py`; `id28` implemented the superseded round-robin design and is
not used for DC2. The sheet is `reports/DC2_ID_PROTOCOL_2026-09-23d.md`.

## 1. Design and data, as captured by `pipeline/identify/capture_idpath.py`

**Slots and path**

- Each participant has one slot per day. The day 1 order is P1 to P6, and day 2 runs in reverse.
- In each slot, RX2 stands at the identification spot, beside the TX. The spot is recorded once,
  at the rehearsal, in `runs/identify/dc2/rx2_spot.json`:
  - primary: (2.0, -0.5);
  - fallback: (1.5, -0.5).
- The path is line A walked away from the TX, `A_fwd` in `paths.py` and `anchors.py`: (2.5, 0) to
  (2.5, 5), direction N.
- **Presses fall at every metre, six per pass**, because walk mode closes a pass on its sixth press.
  Speed and the segment use the first press (0 m) and the last (5 m).

**Files.** Names are `participant_<name>_idpath_d<day>_<what>`, written directly under
`data/room_B/session_0<day>/`, with no manifest. `<what>` is one of `natural`, `slow`, `fast`,
`empty_idspot` or `empty_home`.

| kind | files |
|---|---|
| walks | `_RX1.bin`, `_RX2.bin`, `_RX3.bin`, `.gt.json`, `.idmax.json`, and optionally `_run.json` |
| empty-room recordings (30 s) | the three `.bin` files, `.idmax.json`, and optionally `_run.json` |

**Expected per participant**

- day 1: `natural` (10 passes), `empty_idspot` and `empty_home`;
- day 2: `natural`, `slow` and `fast` (5 passes each), `empty_idspot` and `empty_home`.

**Refusals.** The scorer stops before scoring anything, listing every offence, if any of these
holds:

- a file is missing, a name does not match, or a recording is outside the expected set;
- a participant is not one of the six, or is retired;
- any file carries `REHEARSAL`;
- a walk block's pass count differs from its plan without a reason logged in its sidecar;
- a pass is not on `A_fwd`;
- the identification-spot sidecars disagree with each other or with `rx2_spot.json`.

`--check-layout` runs these checks, plus duration checks (empty rooms at least 25 s, passes 1.5 to
12 s), and touches no results.

## 2. Configurations: frozen, heads fixed, never tuned on DC2

| name | definition |
|---|---|
| **PRIMARY** | the 23b rule's configuration: `id19_featbank.pass_features` on the start-to-end segment, the U_all_gait set on the gait-band mean, training-side median imputation, per-path z-scoring from the training side, and a random forest (300 trees, `max_features` sqrt, `random_state` 0) |
| **SECONDARY**, labelled post hoc | the 23b 2D CNN on Doppler spectrograms, exactly as in `runs/IDENTIFICATION_FROZEN_2026-09-23b_ADDENDUM.json`: seeds 0 to 4, a five-seed ensemble, 60 epochs |
| **S0**, a control and never a result | speed = 5.0 m divided by the time between the first and last presses, with shrinkage LDA |

**Training.** Everything is fitted on DC2 day 1's natural passes and scored on day 2, once. The
exceptions are P4, which trains on day 1's empty rooms, and P6, which trains on Room A.

## 3. Analyses, each run exactly once

Each reports accuracy, n and chance (16.67 percent unless stated), a 95 percent cluster bootstrap
over PARTICIPANTS (1000 draws), and a permutation p (1000 draws, with the identity labels permuted
over participants within the test day).

- **P1, THE PRIMARY RESULT, cross-day.** Train on day 1 natural (10 per person), test on day 2
  natural (5 per person), all three links, with RX2 at the identification spot on both days.
  PRIMARY, SECONDARY and S0 are scored on the same passes.

- **P2, the geometry test.** P1 with PRIMARY on each link alone: TX-RX2 (the identification link),
  TX-RX3 and TX-RX1.
  - **Mean F on line A, from `id15_factor_map.py`:**

    | link | primary spot | fallback spot |
    |---|---|---|
    | TX-RX2 | 0.981 | 0.947 |
    | TX-RX3 | 0.500 | 0.500 |
    | TX-RX1 | 0.000 | 0.000 |

  - **Single-link features (added at 19:35, found before freezing).** The frozen feature code
    resolves ONE cadence across all three links and computes every link's rhythm, autocorrelation
    shape and templates at it, and a per-link column filter also keeps the cross-link cadence
    columns. So a "TX-RX1 alone" row built from the three-link features carries TX-RX2's rhythm.
    In a synthetic test, a noise-only TX-RX1 identified people at 66.7 percent that way. P2
    therefore computes each link's PRIMARY features from that link's data ALONE: the frozen code
    is given the single link in all three slots, so every quantity, the cadence included, comes
    from it.
  - **Why there are two versions (added at 19:20; figures corrected at 19:45, before freezing).**
    The features carry SEGMENT LENGTH, and on a fixed 5 m path duration is speed. On pure-noise
    passes differing only in duration (six durations, chance 16.67), a random forest named the
    duration class:
    - at 58.3 percent using every feature family, mostly through spectral shape, rhythm,
      modulation depth and the motion profile;
    - at 25 to 33 percent using PRIMARY's own columns with three links (three seeds);
    - at 17 to 29 percent using PRIMARY's own columns single-link.

    PRIMARY's leak is therefore weak but present. P2 is run twice so that a link's accuracy cannot
    rest on pace:
    - **full-length:** the single-link features on the start-to-end segment;
    - **fixed-length:** the single-link features on a centred 2.0 s crop of every pass, which
      removes duration as a cue.
  - **Prediction:** accuracy ordered TX-RX2 > TX-RX3 > TX-RX1 on the fixed-length rows, with TX-RX1
    near chance there.
  - **Verdict.** The ordering HOLDS only if, on the fixed-length rows, TX-RX2's accuracy exceeds
    TX-RX3's, TX-RX3's exceeds TX-RX1's, and TX-RX1's interval contains 16.67. Otherwise it is NOT
    HELD. The full-length rows are reported beside it; their TX-RX1 row measures how much identity
    arrives through pace alone.
  - **Physics check.** For each link, report the observed median torso-contour frequency beside the
    prediction f = 2 F v / lambda. The observed value is the 50th-percentile energy contour of the
    4 to 70 Hz STFT of PCs 2 to 4 of the per-pass PCA, with nperseg 32, noverlap 24 and nfft 64,
    taking the median over frames. The inputs to the prediction are:
    - v, from the presses;
    - lambda, the speed of light over the channel frequency, (2407 + 5 x channel) MHz, with the
      channel read from the frames.

    Report the median observed and predicted frequency per link, and their Spearman correlation
    across passes. This is reported and not gated.

- **P3, the pace test, across days.** Enrol on day 1 natural, as in P1, and score day 2 natural,
  day 2 slow and day 2 fast separately with PRIMARY, SECONDARY and S0 on the same passes.
  - **Drop.** For each configuration and each direction, the drop is the participant-level natural
    accuracy minus the slow (or fast) accuracy. It is averaged over the 6 participants, with a
    paired 95 percent bootstrap over participants.
  - **Two notes on the reading (added at 19:20):**
    - The frozen PRIMARY features carry some segment length (weakly, as P2 measures), so an
      ENCODES PACE verdict for PRIMARY may partly reflect duration rather than gait kinematics.
      The P2 fixed-length rows are the evidence for which it is.
    - SECONDARY pads passes shorter than its 3.0 s crop with zero frames, so a fast pass under
      3.0 s is itself a length cue.
  - **Reading, per direction:**
    - **NOT DECIDABLE** if S0's drop interval does not lie above zero.
    - **NOT INFORMATIVE** for a configuration whose P1 interval contains chance.
    - Otherwise:
      - **ENCODES PACE** if its drop is at least S0's;
      - **GAIT-CONSISTENT** if its drop interval contains zero and its upper bound is below S0's
        drop;
      - **INCONCLUSIVE** otherwise.

- **P4, the placement control.** Each 30 s empty-room recording at the identification spot is cut
  into ten 3 s windows.
  - **Features:** static levels, meaning the mean amplitude per subcarrier per link and the mean
    RSSI per link.
  - **Test:** shrinkage LDA, trained on day 1's 6 recordings and tested on day 2's 6, classifying
    which participant's slot a window came from. Chance is 16.67.
  - **Reading:** accuracy at chance is the evidence that RX2's placement did not differ
    systematically between people.
  - **Spread:** also report the spread of RX2's mean static amplitude across the twelve
    placements, as mean, SD, coefficient of variation, minimum and maximum.
  - **The home position:** the same control is repeated at home, as information for the tracking
    analysis.

- **P5, controls.**
  - **Recording signature:** static levels only, over each pass segment, all links, shrinkage LDA,
    day 1 natural to day 2 natural.
  - **Session-ID control, as defined in 23b:** PRIMARY's features and head predict the DAY on
    natural passes, splitting by participant (train three, test the other three, all 20 splits).
    Chance is 50, the bootstrap is over participants, and the days are permuted among each
    participant's recordings.

- **P6, cross-room, secondary.** Train on Room A's `A_fwd` passes (36: two per person per
  session, walked in the same direction) and test on DC2 day 2 natural. It uses TX-RX3 ONLY,
  because RX2 has moved and TX-RX1 is blind on line A. Its features are PRIMARY's, SINGLE-LINK, as
  in P2 (amended at 19:55): three-link features would carry the other links' cadence.
  - The Room A side is computed at scoring time from the 23b signal bank's start-to-end segments.
    Only these 36 passes and only TX-RX3 are used.

- **Within-day is not a result.** Each person's identification passes come from one slot, so
  within-day accuracy is confounded by the slot and by the RX2 placement. One labelled row is shown
  only as "WITHIN-DAY, ONE SLOT, CONFOUNDED": PRIMARY, trained on each participant's first 5 day 1
  natural passes and tested on the last 5.

## 4. Stated expectation, so it cannot be reinterpreted later

With 30 test passes, the 95 percent half-width is about 15 points, so a true accuracy near 25
percent will not separate from chance in P1. **P2's ordering and P3's contrast with S0 are the
tests DC2 can decide.**
