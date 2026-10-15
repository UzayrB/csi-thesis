# Identification development, batch 2: closing report and final model (2026-09-29 14:11 SAST)

Written under the operator's direction change of 2026-09-28 (`reports/BRIEF_ID_DIRECTION_2026-09-28.md`):
development work, not a pre-registered test.
- The log, with every step and why, is `reports/DEVLOG_ID_2026-09-28.md`. Batch 1's report is
  `reports/ID_DEV_BATCH1_2026-09-29.md`.
- The standard is leave one session out over A1, A2, A3 (Room A) and B1, B2 (Room B). The model is
  trained on the other four sessions and never sees the held-out one.
- Six-way accuracy is reported on each held-out session's 120 tracking passes, pooled per room (n 360
  and 240), with a 95 percent interval over participants; chance is 16.67.
- Participants are "participant P1" to "participant P6".

## 0. In short

- **The final identification model** is an equal-weight ensemble of eight gait and Doppler components,
  trained on four sessions.
- **On a session it has never seen:**
  - Room A 39.72 [27.50, 46.94], and Room B 30.00 [19.58, 39.17], against a chance of 16.67;
  - live, causally, at a 5 s decision latency: Room A 40.28 and Room B 31.67.
- **Compared with the frozen record:** Room A's frozen cross-day headline was 15.83.
- **Choosing loses to averaging:** every rule that picked a model from inner validation lost to
  averaging all eight.
- **Gait, not speed:** it stays above chance on deliberately slow and fast walks, where speed alone
  falls to chance.

## 1. The final model and its result

**The model** is the equal-weight product (sum of log-probabilities) of eight components. It is trained
on four sessions and involves no choice between them.

| component | input | adaptation to the new session (causal: earlier recordings only, no labels) |
|---|---|---|
| random forest | gait features | per-path z |
| random forest | gait features | standardised by the session's earlier walks |
| random forest | gait features with pace as one parameter | the same |
| extra trees | gait features with pace as one parameter | the same |
| shrinkage LDA | gait features with pace as one parameter | the same |
| CNN-v2 | conditioned Doppler maps, 3 links | none |
| CNN-v2 | the same | BatchNorm statistics from the earlier walks (AdaBN) |
| per-link CNN-v2 | one CNN per link, product fusion | AdaBN |

The CNNs train for 6,000 steps with 3 seeds.

| | A1 | A2 | A3 | B1 | B2 | Room A | Room B |
|---|---|---|---|---|---|---|---|
| **final model (ensemble of eight)** | 36.67 | 47.50 | 35.00 | 26.67 | 33.33 | **39.72 [27.50, 46.94]** | **30.00 [19.58, 39.17]** |
| batch 1's headline (the batch 2 chosen model) | 36.67 | 31.67 | 27.50 | 24.17 | 30.83 | 31.94 [23.06, 39.72] | 27.50 [18.75, 35.42] |

**Paired** (the same passes, bootstrap over participants): the final model minus batch 1's headline is
Room A **+7.78 [1.11, 14.44]** and Room B +2.50 [-1.67, 6.67].

**The "before" references,** from the frozen record:
- Room A's nested cross-day headline, 15.83 [10.28, 21.67];
- DC2 analysis P1 (Room A trained, day 1 to day 2), 26.67 [13.33, 36.67];
- P1-GP, 30.00;
- analysis P6, Room A to Room B on TX-RX3, 10.00.

Across sessions and rooms, the final model is about two and a half times chance in Room A and nearly
twice chance in Room B.

## 2. Live

The live runner replays each held-out session pass by pass in recording order. At each pass's end
press it uses only the frames that had arrived by then plus a wait, and classifies with the session's
earlier recordings as the only calibration.

**At a 21 s wait the live system is the offline system, exactly.** The clock map's bins around the pass
are complete by then:

| held-out | passes | live features and maps = offline | decisions = offline | decision latency, median |
|---|---|---|---|---|
| A1 | 120 | 120 | 120 | 22.6 s |
| A2 | 120 | 120 | 120 | 21.7 s |
| A3 | 120 | 120 | 120 | 21.4 s |
| B1 | 360 | 360 | 360 | 21.3 s |
| B2 | 299 | 299 | 299 | 21.8 s |

This holds on every pass of every session. So the live system's inputs are the offline inputs, and with
the same trained model its decisions are the offline decisions. Every offline figure in this report is
therefore the live system's figure at a 21 s decision latency. Feature equality does not depend on the
model; these replays used the batch 2 model.

**At a 5 s wait** the clock map's last bins are not final, so the features shift slightly. The system
is still causal, but it is a slightly different system. The final model's 5 s replays:

| held-out | passes | live features = offline | decisions = offline | tracking accuracy: live 5 s / offline | decision latency, median |
|---|---|---|---|---|---|
| A1 | 120 | 6 | 111 | 37.50 / 36.67 | 5.6 s |
| A2 | 120 | 6 | 114 | 46.67 / 47.50 | 5.6 s |
| A3 | 120 | 6 | 114 | 36.67 / 35.00 | 5.4 s |
| B1 | 360 | 24 | 341 | 26.67 / 26.67 | 5.3 s |
| B2 | 299 | 23 | 283 | 36.67 / 33.33 | 5.3 s |
| **Room A** | 360 | | | **40.28 [29.17, 46.94]** / 39.72 | |
| **Room B** | 240 | | | **31.67 [19.57, 42.92]** / 30.00 | |

- **Paired, live at 5 s minus offline:** Room A +0.56 [-1.11, 2.22], Room B +1.67 [-0.83, 4.17].
- **So a 5 s decision latency costs nothing measurable:** 95 percent of decisions are unchanged.
- **The live figures here are measured, not inferred.** The model was retrained for each replay, so the
  decision comparison includes any GPU retraining difference as well as the feature shift.

Model compute per pass is under 0.1 s (0.06 to 0.08 s median), and feature extraction about 0.25 to 0.6 s.
The decision latency is almost all the wait.

## 3. Is it gait or pace?

Room B's identification captures include deliberately slow and fast walks. These change pace but not
the person. The tracking passes are excluded here:

| model | natural (n 180) | slow (n 120) | fast (n 119) |
|---|---|---|---|
| final model | 44.4 | 30.0 | 26.9 |
| the same without its three pace components | 40.0 | 24.2 | 27.7 |
| S0, speed from the presses alone (a control, batch 1) | 45.0 (B1) | 16.7 (B1) | |

- Speed alone falls to chance on slow walks. The final model stays well above chance at every pace.
- The components that use pace are the flattest across pace (LDA 33.3 / 30.0 / 27.7; extra trees
  31.1 / 31.7 / 31.9).
- The ensemble without them has the same natural-pace peak. So the peak comes from training on
  natural-pace walks (every tracking pass is natural pace), not from the pace parameter.
- Pace enters only as one parameter inside the gait features, as the direction requires. Including it
  helps in both rooms (ensemble without it: 32.78 and 24.17).

## 4. How the model was found (every step in the log)

1. **Batch 1:** leave-one-session-out, with selection by inner validation on the four training
   sessions. It found the levers: causal session normalisation, pace as a gait parameter, AdaBN, the
   per-link CNN, and LDA.
2. **Batch 2, four selection rounds** (candidates widened each time; the last on the GPU with 5 seeds):

   | round | Room A | Room B |
   |---|---|---|
   | round 3 (+ per-link CNN) | 32.50 [21.67, 40.83] | 23.75 [10.00, 37.08] |
   | wide (+ extra trees, LDA) | 34.44 [22.76, 44.17] | 24.17 [16.25, 32.50] |
   | final round (everything, 5 seeds, GPU) | 34.44 [21.66, 43.89] | 22.08 [10.00, 32.93] |

   Every round did well in Room A and lost the Room B folds (B1 17.50 to 23.33). The inner validation of
   a Room B fold has three Room A sessions and one Room B session.
3. **Every component's outputs were saved** (`idx_all`), and the selection rules were compared without
   retraining (`idx_all_eval`). Every rule chooses on inner validation only:

   | rule | Room A | Room B |
   |---|---|---|
   | pick the best candidate (pooled inner accuracy) | 35.28 [24.44, 43.33] | 26.25 [15.00, 36.67] |
   | pick the best, rooms weighted equally | 35.28 | 24.58 |
   | greedy ensemble chosen by inner accuracy | 38.06 | 22.50 to 23.33 |
   | **no choice: all eight** | **39.72** | **30.00** |

   All eight minus the pooled pick: Room A +4.44 [0.83, 8.61], Room B +3.75 [0.00, 10.42]. Against each
   earlier selected model, the ensemble is higher in both rooms (Room A +5.28 to +7.78, every interval
   above zero; Room B +2.50 to +7.92, two of four above zero).
4. **Why choosing loses:** the components are individually weak (17.50 to 36.39 per room), and the best one
   changes from session to session:
   - LDA is best on B2 (37.50);
   - the random forest with pace on A1 and A2;
   - the per-link CNN on B1.

   Inner validation on four sessions cannot predict which one will win on the fifth. Averaging their
   log-probabilities does not need to.

## 5. Per participant (final model, tracking passes)

| | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| Room A recall | 46.7 | 45.0 | 41.7 | 10.0 | 46.7 | 48.3 |
| Room B recall | 40.0 | 40.0 | 10.0 | 17.5 | 42.5 | 30.0 |

- Four of six people are identified at about 40 to 48 in each room. One person per room is near
  chance.
- No participant takes an outsized share of the predictions (8 to 25 percent against 16.7).

## 6. What went wrong

- **The 5 s live claim.** At 07:41 the log said the live features at a 5 s wait equal the offline ones.
  With `--predict-live` the check compared the live features with a bank into which they had already
  been substituted, so it could not fail.
  - Measured correctly, only 23 of 299 B2 passes match at 5 s.
  - Corrected at 08:25: the entry is kept and a correction entry follows it. The runner now compares
    with the untouched bank and also reports decision agreement.
  - The operator was told at 07:44 and corrected at 08:25.
- **Wasted runs.**
  - One live run on the flawed check was stopped and re-queued.
  - Two queued jobs were withdrawn when the GPU replaced them.
  - Three of the final selection round's 5 s replays were withdrawn when the ensemble replaced that
    round's model.
- **Clock times.** One log time was written before the clock was read (08:31 for 08:25) and corrected
  in the same minute.

## 7. Limits

- **Sample size:** six participants and five sessions. The intervals are about ten points wide, so
  differences under about five points between the models in section 4 cannot be told apart.
- **Development, not a test:** the component list grew over batches 1 and 2 as test results came in.
  The final ensemble involves no choice, but the set it averages was assembled with test results in
  view.
- **Weak people:** one person per room is near chance, so the model does not identify everyone.
- **Latency:** exact live equality needs a 21 s wait. At 5 s the system is causal but slightly
  different (section 2).
- **Hardware:** the CNNs were trained on the GPU (MPS) for the final model and on the CPU for earlier
  rounds. The two differ numerically.

## 8. Files

- **Code (development, not frozen):** in `pipeline/identify/`:
  - `idx_bank.py`, `idx_loso.py`, `idx_dev.py`, `idx_train.py`;
  - `idx_sel.py` (selection rounds);
  - `idx_all.py` (every component's outputs saved);
  - `idx_all_eval.py` (rules and ensembles, paired tests, ensemble export);
  - `idx_live.py` (the causal live replay).
- **Outputs:** in `runs/identify/dev/`:
  - `all/all_<session>.npz`, `all/eval_all.json`;
  - `loso/sel_all_ens.json` (the final model's decisions);
  - `loso/sel_*.json` (selection rounds);
  - `live/` (replays).
- **Unchanged:** every frozen record, pre-registration and earlier report.
