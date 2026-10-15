# BRIEF: the direction change of 2026-09-28, identification's copy

Received from Uzayr on 2026-09-28, saved at 22:11 SAST (clock read). It applies to both tracking and
identification; tracking records it as INSTRUCTION 9 of `reports/BRIEF_render_and_prepress_2026-09-22.md`
and in the top section of `STATE.md`. The text between the rules is his, VERBATIM. It governs all
identification development from now on. Re-read this file before each batch; never work from memory
of it. Nothing below the second rule is part of the brief.

---

DIRECTION CHANGE, from the operator, applies to BOTH tracking and identification. Record it in the
BRIEF, STATE, HANDOFF and your memory.

The goal is now the best model that generalises across rooms and days and meets the project brief:
real-time identification and 2D tracking, evaluated for spatial resolution, latency and robustness
to environmental change.

KEEP, untouched: every existing report, freeze and result. They are the thesis record and the "before"
reference. Never delete or rewrite them.

STOP, for development work:
- pre-registering each change;
- labelling things POST HOC;
- the three-condition ship rule and the per-line edge rule (f);
- deferring to the frozen configuration;
- asking me to approve each development choice.
Keep a development log instead: what changed, why, and the result.

KEEP, because these are system requirements, not ceremony:
- no leakage: split by whole sessions, and fit every statistic on training data only (or on causal
  pre-pass data, such as a calibration walk);
- anything claimed as live must be causal;
- the tracker stays signal-only: no pace, elapsed time or dead reckoning;
- identification is gait-based: pace only as one parameter inside gait analysis, never a bare speed
  comparison;
- the rendering rules for demo videos;
- data/ is read only, and the free-movement recordings are never used for training or testing.

EVALUATION STANDARD, replacing all previous ship rules: five sessions, A1, A2, A3, B1 and B2. Leave
one session out: train on four, test on the fifth, rotating through all five. Every tuning and model
choice is made on validation inside the four training sessions, never on the test session. Report
per held-out session and per room, lock and committed, the four edge lines, with 95 percent intervals,
beside the frozen Room A to Room B figures as the reference.

FREEDOM: retrain, change architectures, fuse links (including product fusion), joint or per-link
encoders, normalisation, multi-room training, anything that improves generalisation. Priorities for
tracking: the Room B lock (currently 14 to 30 percent) and the committed answer in both rooms.
Note that in DC2, RX2 was moved beside the TX for each participant's identification capture and then
returned to taped marks, so small placement differences between recordings are possible. Treat that as
real-world variation the model must cope with.

Keep-alive as usual; one closing report per batch.

---

## Notes at capture (not part of the brief)

- For identification, "lock and committed" and "the four edge lines" are tracking metrics; the
  identification analogue reported per held-out session and per room is six-way accuracy with its
  95 percent interval over participants, beside the frozen references (analysis P1, P1-GP, P6, and
  Room A's nested cross-day headline).
- The registered v2 run (`reports/REGISTER_ID_DC2_V2_2026-09-28.md`, started 20:59) was in progress
  when this arrived. It is allowed to finish and its results are logged as a "before" reference.
