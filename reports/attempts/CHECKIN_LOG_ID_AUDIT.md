# Check-in log: identification audit

One line per check (brief `reports/BRIEF_ID_AUDIT_2026-09-29.md`, section 1). Plan: `runs/identify/audit/PLAN.md`.

- 2026-09-29 22:22: plan written and committed; stage 1 (packet audit) starting; tracking: DONE (17:50), no tracking process running.
- 2026-09-29 22:43: queue held for tracking's GPU (about 1 h); B1 stopped by PID and re-queued as B1_r2; stages 1 and 2 done (no stage 1 bug; stage 2 bugs B-1 and B-2 fixed).
- 2026-09-29 22:45: tracking not ready for about 1 h (its pre-registration first), so the hold was released; B1_r2 training on MPS from 22:44; idz_run now pauses before each training or scoring step while HOLD_GPU exists (the handover for tracking's block).
- 2026-09-29 23:01: paused for tracking's GPU block (B1 fold toB2 trained; the controller waits at HOLD_GPU); GPU handed to tracking at 23:01.
- 2026-09-29 23:01: running B1_r2 (paused for tracking: yes); no job finished since the last line; tracking: "NOW: DONE (17:50). Every item of the task is complete; handoff reports/HANDOFF_TRACKING_20..."; tracking training processes: 0.
- 2026-09-29 23:20: running B1_r2 (paused for tracking: yes); no job finished since the last line; tracking: "NOW: V2 networks training on the GPU (from 23:01); item 2's rotation decodes on the CPU; t..."; tracking training processes: 3.
- 2026-09-29 23:46: tracking's GPU block done (23:45); pause cleared; B1_r2 resumed (fold toB1).
- 2026-09-29 23:50: running B1_r2 ; done: hold_for_tracking_r2 bank_v2 ; failed (known, replaced): B1 hold_for_tracking ; tracking: "NOW: V2 networks training on the GPU (7 of 10 done at 23:26); then the V2 driver (rows, op..."; tracking training processes: 0.
- 2026-09-30 00:20: running L2 ; finished since the last line: B1_r2 L1 fusion ; tracking: "NOW: V2 networks training on the GPU (7 of 10 done at 23:26); then the V2 driver (rows, op..."; tracking training processes: 0.
- 2026-09-30 00:50: running CF ; finished since the last line: L2 cadence_C1 ; tracking: "NOW: the trace-derived hash lists for fin_B2 and fin_A3 (`fin_trace_chain.sh`, from 00:38)..."; tracking training processes: 0.
- 2026-09-30 01:20: running FN ; finished so far today: B1_r2 CF L1 L2 cadence_C1 fusion ; tracking: "NOW: the trace-derived hash lists for fin_B2 and fin_A3 (`fin_trace_chain.sh`, from 00:38)..."; tracking training processes: 0.
- 2026-09-30 01:50: running GS ; finished since the last line: FN ; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instruction: the V2 work (..."; tracking training processes: 0.
- 2026-09-30 02:20: running GS ; finished so far today: CF FN ; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instru..."; tracking training processes: 0.
- 2026-09-30 02:50: running final ; finished since the last line: GS ; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instru..."; tracking training processes: 0.
- 2026-09-30 03:20: running final ; finished since the last line: none; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instru..."; tracking training processes: 0.
- 2026-09-30 03:50: running final ; finished since the last line: none; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instru..."; tracking training processes: 0.
- 2026-09-30 04:20: running nothing; finished since the last line: final ; tracking: "NOW: DONE (01:33). Nothing running for tracking. Uncommitted by instru..."; tracking training processes: 0.
- 2026-09-30 04:23: ALL DONE. Report reports/ID_AUDIT_2026-09-30.md; runner stopped; check-ins cancelled; nothing running.
