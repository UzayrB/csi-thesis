# BRIEF: the full tracking model attack, 2026-09-28

Received from Uzayr on 2026-09-28, saved at 22:47 SAST (clock read). The text between the rules is
his, VERBATIM, and is the specification. Re-read it before each stage; never work from memory of it.
His covering line: "do all of this and juggle it with identification, give me an eta for tracking
and tell my identification chat to update its eta after your is done".

---

FULL MODEL ATTACK. Goal: the best tracker that generalises across rooms and days, meeting the brief
(real-time 2D tracking; evaluated for spatial resolution, latency and robustness to environmental
change). Read reports/TRACKING_MODEL_ARCHITECTURE_2026-09-28.md and DEVLOG_TRACKING first. Model work
STOPS at 23:59 on 1 October; whatever is best by then is the final model.

KEEP-ALIVE: QUEUE.md (PENDING/RUNNING/DONE/BLOCKED, next action, ETA), never stop between items or
wait for me, 15-minute check-ins, caffeinate -dimsu, heartbeat watchdog, OMP_NUM_THREADS=1, ONE
training job at a time. Log every change in DEVLOG_TRACKING: what, why, result. One closing report per
stage.

SYSTEM REQUIREMENTS (not ceremony; never break): no leakage (whole-session splits; every statistic from
training data or causal pre-pass data); everything claimed live is causal; the tracker is signal-only
(no pace features, elapsed time or dead reckoning; a motion prior inside the decoder is allowed);
data/ is read only; the free-movement recordings are never used; existing reports and freezes stay
untouched as the thesis record.

SPLIT: train only on A1, A2, B1. Test sessions A3 and B2 never enter training or any choice. At test
time only causal pre-pass data may be used (idle radio before the first press; B2's calibration walk
for configuration B).

HOW CHOICES ARE MADE
- Development rotations: A1+A2 -> B1 (zero-shot into Room B), A1+B1 -> A2, A2+B1 -> A1.
- Objective, fixed now: the mean over rotations of (committed + lock), with the B1 rotation weighted x2.
- Guard: reject any option that drops an edge line to 0 or halves its recall on the rotations.
- Adopt a change only if its paired gain on the pooled rotation passes has a 95 percent interval above
  zero; otherwise keep the simpler option. This stops us chasing noise.
- SCREEN cheaply, CONFIRM properly: screen training changes with the single 0.5 s g25 head on the
  rotations; confirm only the winners with the full five-head pool.
- TEST DISCIPLINE: A3 and B2 are tested exactly twice more: a midpoint check after stage D3, and the
  final model. Never after individual changes.

STAGES, in order; each builds on the previous stage's winner.

D1 (running): per-recording normalisation from each recording's idle radio. Finish it and adopt it or
not by the rule.

D2, INPUT AND TRAINING ROBUSTNESS (screen, then confirm):
- training-time augmentation: per-link RSSI offset uniform +-5 dB; CSI-shape scaling log-uniform
  x0.25 to x1.5, per link; time shift +-0.25 s; mild Gaussian noise;
- RSSI made relative: subtract each recording's idle RSSI mean per link (level carries placement, not
  position);
- early stopping on the rotation's validation session, maximum 40 epochs;
- mixup across training sessions (alpha 0.2).
Screen each alone, then the best combination.

D3, DECODER AND DECISION (no retraining, on D2's networks; each option on every rotation):
- link fusion: product at w = 0, 0.25, 0.5 and 1.0;
- lock: display lock against the scorer lock (the lock stays read at press + 2.0 s, rule V1);
- CAUSAL null level (running 75th percentile over radio received so far) replacing the whole-recording
  percentile; required for the live claim whatever it costs;
- an explicit ON-A-LINE head: logistic regression on the frozen 64-d embeddings, walk windows against
  idle and walk_edge windows from the training sessions, used as the evidence for "not on a line"
  instead of the fixed offset; compare against the causal null;
- motion gate relative to each recording's own idle band energy, against the absolute 0.431;
- abstain (b_abstain_0.25) against the veto;
- decoder constants re-fitted on the TRAINING sessions: pace mean and spread from A1+A2+B1 passes;
  then re-tune the null offset, margin, A2 weight and display spread on the rotations.
MIDPOINT CHECK: the D3 configuration trained on A1+A2+B1 with the full pool, tested once on A3 and
B2 (configurations A and B).

D4, ARCHITECTURE (only if D2 and D3 are done by 12:00 on 1 October; screen with g25):
- a shared per-link encoder with a learned fusion head over the three embeddings;
- attention over links (a link that looks unfamiliar, such as a moved RX2, gets down-weighted);
- adopt only by the rule; otherwise keep per-link networks with the D3 fusion.

D5, SPATIAL RESOLUTION (decode-level, if time): feed g100 at its native 0.5 m in emissions, and a
probability-weighted within-cell offset. Adopt only if line accuracy does not fall.

FINAL, by 23:59 on 1 October:
- Train the chosen configuration with the full pool on A1+A2+B1; test once on A3 and B2.
- ZERO-SHOT row: the same recipe trained on A1+A2 only, tested once on B2. This is the "unseen room"
  figure; the A1+A2+B1 model is the "adapted" figure.
- Report per test session: committed and lock (display and scorer), configurations A and B for B2,
  edge lines, 95 percent intervals, beside the split baseline (A3 88.33 / 65.00; B2 57.50 / 20.83,
  calibrated 65.83 / 30.00) and the frozen reference (B2 50.00 / 12.50).
- SPATIAL RESOLUTION: median and 90th-percentile position error in metres, overall and on correct-line
  walks, and along-line error.
- LATENCY: per-window compute (median, p99) and end-to-end design latency.
- ABLATION LADDER for the thesis: baseline, then each adopted change added in order, committed and lock
  on the rotations, so every gain is attributable.
- Write reports/MODEL_FINAL_TRACKING.md with the exact configuration and hashes, and update STATE,
  HANDOFF and memory. The frozen DC2 results remain the confirmatory record beside it.

---

## Notes at capture (not part of the brief)

- **D1's first relaunch on the split** included the two final test cells (`d1sr_final_A3/B2`). Under
  TEST DISCIPLINE they were removed at 22:46, before either ran. D1 now runs the six rotation cells
  only.
