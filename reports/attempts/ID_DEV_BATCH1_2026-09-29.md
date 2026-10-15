# Identification development, batch 1: closing report (2026-09-29 03:07 SAST)

Written under the operator's direction change of 2026-09-28 (`reports/BRIEF_ID_DIRECTION_2026-09-28.md`):
development work, not a pre-registered test.
- The log, with every step and why, is `reports/DEVLOG_ID_2026-09-28.md`.
- The standard is leave one session out over A1, A2, A3 (Room A) and B1, B2 (Room B). Every choice is
  made on validation inside the four training sessions.
- Six-way accuracy is reported on each held-out session's 120 tracking passes, pooled per room (n 360
  and 240), with a 95 percent interval over participants; chance is 16.67.
- Participants are "participant P1" to "participant P6".

## 1. The result

The model chosen by inner validation identifies people above chance in both rooms, across sessions.
- **The model** (`idx_sel`, batch 2): in most folds, a product fusion of two parts:
  - a random forest on gait features, with pace as one parameter and each walk standardised by its
    session's earlier walks;
  - CNN-v2 on conditioned Doppler maps, with BatchNorm statistics from the session's earlier walks.
  Both parts are causal and use no test labels.

| | A1 | A2 | A3 | B1 | B2 | Room A | Room B |
|---|---|---|---|---|---|---|---|
| **chosen model (batch 2)** | 36.67 | 31.67 | 27.50 | 24.17 | 30.83 | **31.94 [23.06, 39.72]** | **27.50 [18.75, 35.42]** |
| gait RF, per-path z | 13.33 | 30.00 | 28.33 | 20.00 | 25.00 | 23.89 [13.60, 33.89] | 22.50 [12.08, 33.76] |
| CNN-v2, 3 seeds | 26.67 | 22.50 | 32.50 | 20.83 | 25.00 | 27.22 [19.44, 35.56] | 22.92 [17.08, 28.33] |
| S0, speed from the presses (a control, not a system) | 13.33 | 24.17 | 48.33 | 41.67 | 23.33 | 28.61 [16.11, 40.84] | 32.50 [17.92, 44.58] |
| RECSIG, static levels (a control) | 14.17 | 22.50 | 15.83 | 2.50 | 20.00 | 17.50 [5.00, 31.67] | 11.25 [1.67, 27.50] |

**The "before" references,** from the frozen record:
- Room A's nested cross-day headline, 15.83 [10.28, 21.67];
- DC2 analysis P1 (Room A trained, day 1 to day 2), 26.67 [13.33, 36.67];
- P1-GP, 30.00;
- analysis P6, Room A to Room B on TX-RX3, 10.00.

## 2. Is it gait or pace?

B's identification captures include deliberately slow and fast walks, which change pace but not the
person.
- S0 (speed alone) collapses on the slow walks: B1 45.0 on natural walks, 16.7 on slow.
- The chosen model holds its level: natural / slow / fast B1 35.0 / 33.3 / 31.7, and B2 30.0 /
  38.3 / 18.6 (B2's fast block is the exception).
- The gait-only RF with causal normalisation holds at every pace, 30 to 35 on B2.
- Static levels (RECSIG) do not transfer across sessions, so the gain is not recognition of the
  recording.

So the model is not a disguised speed comparison: pace is one parameter among gait features.

## 3. The levers (every one reported; none chosen on a test session)

| lever | effect |
|---|---|
| causal session normalisation (features) | Room A up (23.89 to 30.00), Room B down (22.50 to 17.50) |
| pace as one gait parameter | Room B up (to 30.00), carried by pace |
| gait with pace plus causal normalisation | Room A 36.39 [24.44, 46.40], Room B 23.33 |
| causal AdaBN (CNN) | about neutral (A 25.83, B 24.58) |
| 6,000 training steps (CNN, AdaBN) | Room A up (28.33 [24.72, 31.94]) |
| per-link CNNs, product fusion | best CNN in Room B (28.33) |
| pace-normalised frequency axis | Room A down (20.83) |
| placement augmentation (frequency tilt) | no measurable gain |

## 4. The registered v2 run (a "before" reference, started before the direction change)

- It ran once on the real data, from 20:59 to 03:03, and all anchors reproduced the committed rows.
- Its registered verdicts, word for word:
  - R-A: "no gait signal across days shown";
  - R-B: "pace-led";
  - R-C: "pace is sensed by Wi-Fi rather than taken from the presses";
  - R-D: "within-session identification that cannot be separated from slot recognition".
- Its figures are in `runs/identify/dc2/v2/figures/`.
- It trained within DC2 only (one room, day to day); batch 1's gains come from training across four
  sessions and both rooms.

## 5. What went wrong

- The 30-minute check-ins did not fire overnight. After 02:45, lanes 2 and 3 were idle until 03:05,
  and three finished jobs were logged late.
- The queue is now filled several jobs ahead, so no lane waits for a check-in.

## 6. Next (batch 2, CPU until tracking releases the GPU at about 20:00)

- **Running:**
  - a selector round adding the per-link CNN and 6,000-step final fits;
  - three seeds of the two strongest CNN variants;
  - a 12,000-step budget test.
- **Then:**
  - the causal live runner with measured latency;
  - on the GPU from about 20:00, the final model retrained with larger budgets and five seeds.
- The final identification report is due about 08:00 on 30 Sept.
