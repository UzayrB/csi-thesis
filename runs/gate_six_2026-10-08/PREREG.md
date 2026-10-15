# Motion gate from the six participants without dwells: pre-registration (8 October 2026, written 18:45 SAST)

**The brief:** Uzayr's "re-derive the motion-gate threshold from the six participants without static dwells". A verbatim
copy is in `BRIEF.md` beside this file (SHA-256 `062b106457c73c25552952a78759d3aca0f0eee03ade4a832faea9db584c1723`).
The Overall chat cleared the start before 18:34 SAST (this chat's first clock read after it) under these limits:
- one process at `nice -n 10`, with every thread cap at 1;
- no GPU and no torch;
- cached gate energies wherever they exist;
- writes only here and in `reports/tracking/2026-10-08_gate-six.md`.

**Nothing is changed:** FINAL_CONFIG, the code, the networks and every existing result stay as they are. No energy
was computed for this task before this file was committed.

## 0. What had been read when this was written

- **Code.** `tools/calibrate_gate.py`, plus these modules in `pipeline/constrained/`:
  - `gate.py`, `recordings.py`, `pd_decode.py`, `decoder2.py`, `emissions.py`;
  - `night_arms.py`, `night_common.py`, `u1_adapt.py`, `bout.py`, `rb3_display.py`, `r1_oldcensus.py`.

  Also `pipeline/live/final_model.py`, and `rb2_decoder.py` as committed in 8a0ecbe1.
- **Records.**
  - `configs/gate.yaml`;
  - the session 01 and 02 `gate_manifest.json` files;
  - `runs/dc2_results/rule/FINAL_CONFIG.md`;
  - the `info` blocks only (G0 and gate scales) of the three final decode records, with no row read;
  - `runs/constrained/rb2_decoder/results.json` (the selected configuration).
- **`reports/tracking/2026-10-01_presence.md`, which already reports this task's candidate still class.** It gives the
  idle windows before the first press as median [p25, p75]:

  | session | raw | scaled | scaled walking, for comparison |
  |---|---|---|---|
  | A1 | 0.477 [0.205, 1.160] | 0.794 [0.322, 1.779] | 2.206 |
  | A2 | 1.185 [0.585, 1.875] | 1.205 [0.634, 1.997] | 1.804 |

  **The still-class choice below is made with those distributions in view.**
- **Structure only, no energies.**
  - The A1 and A2 mode sequences: every recording runs passes, then the 25-cell standing sweep, then passes
    (`mode_order: walk_half, grid, walk_half`).
  - Per-recording counts of idle windows before the first press.
  - On the training sessions only (A1, A2 and B1; 371 passes): the first labelled walk window of every pass has
    t0 = press - 1.0 s exactly, so it is the window centred on the press.

## 1. Provenance found (step 1), fixed here before any result

**The threshold.**
- **Where it was set.** It is `tools/calibrate_gate.py` `best_split`. It was committed 10 Sept 23:26 to 23:45 SAST
  (7345cf78, 05cc64d9), and `configs/gate.yaml` dates its acceptance at Checkpoint 4 to 11 Sept.
- **The value.** The search gave 0.431285. The code uses 0.431.
- **What it was set on.** It was placed on session 01 (A1): the `grid` (standing-sweep dwell) windows against the
  `walk` windows, on the 1 s lattice, using raw energy. It was checked on session 02.
- **Participants.** All eight, including Azrah and Zaid, as listed in both sessions' `gate_manifest.json`.
- **Verdict: it touched dwells and the removed participants.** It is re-derived here.

**G0, for the deployed and zero-shot models alike.**
- **Value.** 0.7541556642487132 (`pd_decode.gate_reference`, `room_a_only=True`).
- **What it is.** Over the Room A training recordings (A1 and A2 for both models), it is the median of each
  recording's median raw energy over its idle windows before the first press.
- **Participants.** The six, through the `recordings()` filter on `SIX`.
- **Window types.** Only `idle` windows that end at or before the first press. No dwell is among them: the sweep comes
  after the first pass in every A1 and A2 recording.
- **Verdict: clean.** It is left unchanged.

**g_rec.**
- **Offline:** the median raw energy over the recording's own `u1_adapt.calibration_indices` windows.
- **Live:** the same windows by time (`final_model._final_stats`).
- **Verdict: clean.** It is left unchanged.

**Further gate values found, which read the gate at 0.431.** These are:
- the null rule: quantile 0.75, offset -7.5 and still weight 4.0;
- the veto: on, hysteresis 1;
- the bout prior: log odds -1.2756.

They were fitted or selected in rb2 (17 Sept) on A1+A2, using the six participants and whole recordings:
- the null's F1 fit (`decoder2.fit_adaptive_null2`) counts the dwell windows as off-path negatives;
- the selection score charges "stationary" false occupancies;
- the bout prior counts walking bouts over the whole recording.

**So they touched dwells, but not the removed participants.** Re-deriving them means re-selecting the decoder and
re-decoding, which the brief rules out. They are reported, not re-derived.

## 2. The still class (step 2)

Each candidate is weighed against "reliably not walking, from the protocol":
- **Standing between passes: rejected.** The capture protocol (`pipeline/io/ground_truth.py`, Mode B) gives no
  instruction to stand between passes. The participant goes to the next line's start (transit), and 53.2 % of transit
  windows read as walking (`recordings.gate_energy` docstring).
- **Empty-room baselines: rejected.** They are reliably not walking, but they hold no person, which makes them a
  different class from a standing person (raw median 0.011, against 0.042 for standing). They also separate from
  walking perfectly (AUROC 1.000 on A1), so a balanced-accuracy threshold would sit at the lowest walking window.
- **Idle windows before the first press: not reliably still either.**
  - The A1 and A2 protocol (captured 9 and 10 Sept) gives no stillness instruction before the first walk. The 15 s rule
    dates from 29 Sept (architecture 17.4).
  - The 1 October distributions above show these windows reach walking levels, in A2 especially.
- **Conclusion.** In A1 and A2, the only protocol-guaranteed still person is the standing sweep (Mode A), which the
  brief excludes.

**The pre-registered still class** is the idle windows before each recording's first press:
- **Definition.** `u1_adapt.calibration_indices`: windows that end at or before the first start press, with mode
  `idle`.
- **Scope.** A1 for the derivation and A2 for the check, six participants.
- **Why this source:**
  - it is the first source the brief names;
  - it is the deployed system's own definition of a recording's quiet period (g_rec, the relative RSSI, AdaBN);
  - it holds no dwell and no removed participant.
- **It is labelled throughout as NOT reliably still.** Whatever threshold it gives is the dwell-free threshold these
  data allow, not a cleaner estimate of the boundary between standing and walking.
- **Counts per recording** (PA5, PA1, PA2, PA3, PA4, PA6):

  | session | counts | total |
  |---|---|---|
  | A1 | 91, 147, 102, 86, 31, 85 | 542 |
  | A2 | 19, 35, 42, 23, 26, 25 | 170 |

## 3. The walking class

- **Windows:** those with mode `walk`, meaning inside a labelled pass with its pass id set.
- **Scope:** six participants, A1, with A2 for the check.
- **`walk_edge` is excluded,** as the original used `modes == "walk"`.

## 4. Statistic, scaling, rule and tie rule (step 3)

**The statistic** is `gate.band_energy` per window (the original's formula) on the deployed 0.5 s press-aligned lattice.
- It is read from the cached `.npy` files, read only:
  - fin_B2's cache for A1, A2 and B2 (its `art_half/gate_energy`);
  - fin_A3's for A3;
  - `runs/constrained/dc2_room_B_s0.5_pressalign/by_session/B1/art_half/gate_energy` for B1.
- **Primary:** the scaled energy, raw x max(1, G0 / g_rec), with G0 = 0.7541556642487132 and g_rec as in section 1.
  This is what the deployed decoder thresholds.
- **Secondary, informative only:** the raw energy, the original's statistic, which had no scaling. It decides nothing.

**The rule** is `tools/calibrate_gate.best_split`, imported and not re-implemented:
- the energies go to log10;
- the candidates are 2000 values spaced linearly from the pooled minimum to the pooled maximum of the two classes;
- balanced accuracy = 0.5 x (share of still < c + share of walking >= c);
- the threshold is 10^c at the maximum over (balanced accuracy, c).

**The tie rule** is the original's, implicit in Python's tuple order: ties go to the HIGHEST candidate. The flat range of
maximal balanced accuracy and its midpoint are reported, but not used.

**Reported:**
- the new threshold (theta_new);
- balanced accuracy on A1 and on A2, each at theta_new and at 0.431 (A2 places nothing);
- the curves of balanced accuracy against threshold for A1 and A2, with 0.431 and theta_new marked;
- the same for the raw secondary.

## 5. Equivalence check (step 4)

**The settings compared.**
- **Old:** theta = 0.431, the deployed constant.
- **New:** theta_new.
- **G0 and g_rec do not change**, so the scaled statistic is identical under both. A flip is a window where
  (s < 0.431) differs from (s < theta_new).

**What is checked.**
- **Models and sessions:** fin (deployed) on A1, A2, B1, A3 and B2; zsf (zero-shot) on B2. zsf's G0 equals fin's,
  read from its decode record's `info`.
- **Windows:** every window of every recording, including the calibration recordings B1 PA2_C and B2 PA6_C.

**Presses.** press_k is pass k's first anchor press, read by `p1_runup.first_presses`. These are the deployed
decoder's own inputs:
- A3 is read from `data/room_A/session_03`;
- B1 and B2 are read from `data/room_B/session_B*`.

Nothing else is read from an A3 or B2 ground-truth file. Their end presses and pass spans are not read.

**Decode range.** The shipped decode (`night_arms.night_track`) reads the gate only over [lo_k, min(n - 1, lo_k + 40)]:
- 40 windows = MAX_WALK_S 20 s / 0.5 s;
- the shipped options have no run-up;
- lo_k on A1, A2 and B1 is the first `walk` window of pass k;
- lo_k on A3 and B2 is the window with t0 = press_k - 1.0 s (within 1 ms). That is the relation measured on all 371
  training-session passes, so no label is read.

**Spans.**
- **A1, A2 and B1:**
  - before the first press: the window ends at or before the recording's first press;
  - press to walk end: [lo_k, last `walk` window of pass k];
  - walk end to horizon: after the walk end, up to lo_k + 40;
  - elsewhere: every other window.
- **A3 and B2 (label-free):**
  - before the first press;
  - inside a decode range: [lo_k, lo_k + 40] for some pass k;
  - elsewhere.

  The press-to-walk-end split on A3 and B2 waits for Uzayr's answer on the walk end.

**Reach.** From the code, the report states whether a window in each span can reach the committed line, the lock, the
drawn track or the switch:
- offline: `night_track`, `decoder2.stack2`;
- live: `pipeline/live`.

**Pre-registered expectation:** any window inside a decode range can reach an output, and windows outside every range
cannot.

**Outcome (brief step 5).**
- **Any flip inside a decode range,** on any session and model, is the STOP case: the counts are reported, nothing is
  re-decoded, and Uzayr decides.
- **Otherwise,** the outputs are identical and the thesis sentence is drafted.

## 6. Checks before any result is read

The run halts and reports if any of these fail:
1. A recording's cache files are byte-identical across every cell that holds them. Cache lengths equal the window
   counts in the meta files.
2. One A1 recording and one B1 recording, B1 from the arrays re-cut today, are recomputed from their window files with
   `gate.band_energy`. This happens only while the system reports at least 30 % free memory, and they must equal the
   cache exactly.
3. G0 recomputed from the caches equals 0.7541556642487132 (|difference| < 1e-12).
4. The gate scales recomputed for the A3 and B2 recordings equal the final decode records' `gate_scale` values
   (|difference| < 1e-9).
   - On A3 and B2, g_rec's windows are chosen by the live app's label-free time rule: the window ends at or before the
     first press, and its centre is more than WALK_EDGE_S = 3.0 s before it.
   - No `mode` is read there.
   - On A1, A2 and B1, the time rule must select exactly the `calibration_indices` windows.
