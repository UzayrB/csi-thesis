# Check-in log: identification on the identification walks

One line per check (brief `reports/BRIEF_ID_WALKS_2026-09-29.md`, section 1). Queue:
`runs/identify/idwalks/queue/`. Plan: `runs/identify/idwalks/PLAN.md`.

- 2026-09-29 15:54: queue started 15:53 (stage A, then stage B's direction-specific trainings, 14 jobs); A_TR-B_toB2 training on MPS; stage D done (gate passes, 0.533); tracking running its substitution test (pd_subst, not a training).
- 2026-09-29 16:23: running A_TR-B+_toB2 ; done so far: A_TR-B_toB2 ; tracking: "NOW: renders of A3 (B2 DONE 16:09, all rules pass); then live gates, reproduction from hashes (logs/final_corr..."; tracking training processes: 0.
- 2026-09-29 16:53: running A_TR-B_toB1 ; done so far: A_TR-B+_toB2 A_TR-AB_toB2 A_TR-B_toB2 ; tracking: "NOW: renders of A3 (B2 DONE 16:09, all rules pass); then live gates, reproduction from hashes (logs/final_corr..."; tracking training processes: 0.
- 2026-09-29 17:23: running A_TR-AB_toB1 ; done so far: A_TR-AB_toB2 A_TR-B+_toB1 A_TR-B_toB1 A_TR-B_toB2 A_TR-B+_toB2 ; tracking: "NOW: reproduction from hashes (pd_repro, fin_B2 then fin_A3; ~18:50). Everything else of the task is DONE: tes..."; tracking training processes: 0.
- 2026-09-29 17:53: running B_TR-B_towards_toB2 ; done so far: A_TR-AB_toB1 A_TR-AB_toB2 A_TR-B+_toB1 A_TR-B+_toB2 A_TR-B_toB2 A_TR-B_toB1 B_TR-B_away_toB2 eval_A ; tracking: "NOW: DONE (17:50). Every item of the task is complete; handoff reports/HANDOFF_TRACKING_2026-09-29_CORRECTED.m..."; tracking training processes: 0.
- 2026-09-29 18:23: running B_TR-AB_away_toB1 B_TR-AB_towards_toB2 ; done so far: A_TR-AB_toB1 A_TR-AB_toB2 A_TR-B_toB2 A_TR-B_toB1 A_TR-B+_toB2 A_TR-B+_toB1 B_TR-B_away_toB2 E_starts B_TR-B_towards_toB1 eval_A B_TR-AB_away_toB2 X_extra_features B_TR-B_towards_toB2 ; tracking: "NOW: DONE (17:50). Every item of the task is complete; handoff reports/HANDOFF_TRACKING_20..."; tracking training processes: 0.
- 2026-09-29 18:53: running X_arm_toB1 X_arm_toB2 ; done so far: A_TR-B+_toB1 A_TR-AB_toB2 A_TR-AB_toB1 A_TR-B_toB2 B_TR-AB_away_toB1 A_TR-B_toB1 B_TR-AB_towards_toB2 B_TR-B_away_toB1 B_TR-AB_towards_toB1 A_TR-B+_toB2 B_TR-B_towards_toB2 E_starts B_TR-B_towards_toB1 X_extra_features eval_A B_TR-AB_away_toB2 B_TR-B_away_toB2 ; tracking: "NOW: DONE (17:50). Every item of the task is complete; handoff reports/HANDOFF_TRACKING_20..."; tracking training processes: 0.
- 2026-09-29 18:58: ALL DONE. 20 of 20 jobs done, no failures; both runners stopped; report reports/ID_WALKS_2026-09-29.md; check-ins cancelled.
