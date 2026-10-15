# QUEUE_B: identification, build the best model (Uzayr's prompt, received at or before 10 Oct 2026 08:22:47 SAST)

Exploratory development, all data seen; selection on the combine scorecard (A3 and B2 included). Adopt nothing; v4 stays
shipped. P2 (tracker speed): OFF in the build; ON tried as P2 alone and on the winner (Uzayr's message). Read this file first on every turn. Session: Third overall.

| item | state | next action | ETA |
|---|---|---|---|
| B0 set-up | DONE (08:46) | POA_B b7e8aa25, notes 529b6ffd, 5ba3731e, a696e3ab; slot granted; CPU share 2 processes from 09:45 (slot.sh) | |
| B1 extraction (CPU) | DONE (08:25 to 09:32; every file checked, anchors exact) | A1 dense offsets, A3 time-stretched windows, A4 test windows with maps (all sessions) | |
| B2 P1 quality (and P2's speed check, done 08:36) | DONE (09:32; P1 r 0.24 to 0.61 against Wi-Fi's 0.14 to 0.42) | the learned path-walk speed's correlation with the stopwatch per held-out session | |
| B3 CPU candidates | DONE (09:32 to 10:41; 14 configurations in round 1) | singles P1, P2, A1, A3, A4, A5, M2, M3 and greedy round 1 (F7 + each), 14 configurations; F7 reproduced first | |
| B4 GPU: A4 caches | DONE (09:41 to 10:26; offset 0 equal to every replay) | CNN log-probabilities of the 0.15 and 0.30 s test windows (CAL-causal pool), every model | |
| B5 GPU: A2, M1, A2+M1 on development | DONE (10:26 to 13:06; A2 25.42, M1 27.29 against 29.59; A2M1 skipped by the gate) | 9 trainings; those beating v4+F7's DS go to the full scorecard | |
| B6 greedy from F7 | DONE (13:41; winner A1+A3+A4+A5+M3, 32.64; P2 ON 31.56) | add what raises (Z+D)/2 most while the guard holds | |
| B7 report, ship plan, commit, QUIET | DONE (14:05; QUIET 14:03 by the driver, JOB_DONE written) | reports/identification/2026-10-10_best-model.md | |
