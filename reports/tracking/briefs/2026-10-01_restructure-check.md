# BRIEF: the pipeline/ restructure, tracking's checks. Received 1 October 2026, about 11:00 SAST

**Uzayr's instruction, verbatim below.** Work from this file, never from memory of it. The status of each item is in
`QUEUE.md`, section "RESTRUCTURE CHECK (1 OCT)". It was held outside the repository until Monitor sent "carry on"
(12:09), as item 1 asks.

---

Tracking only. The pipeline/ restructure. Monitor is already running the import check, pre-flight, the model-set rebuild, pd_repro_trace on fin_A3, fin_B2 and zsf_B2, G2 (semi, K1g) on the same cells, and the full test suite. Don't repeat those; read their results and do the rest below.

1. Wait. Start no job and edit no file until Monitor sends the map and "carry on". If Monitor hasn't told Identification to carry on, tell it: "restructure done, you can run". Don't touch Identification's files, processes or results.

2. Tag the reference. Tag the last commit before Monitor's restructure commit as tracking-final-2026-10-01, and record in STATE.md that the thesis cites this tag.

3. Read Monitor's results for tracking. Each must pass: pd_repro_trace EXACT on all three cells; G2 120/120 committed lines and locks on all three; imports; pre-flight. Explain two numbers from its summary:
   a. The model sets went from 456 to 454 files (final) and from 220 to 218 (zero-shot). Name the four files that left and show that none is read by the model.
   b. The module count went from 247 to 246. Name the module and say whether anything in tracking used it.

4. What Monitor's checks don't cover:
   a. Code diffs. For every tracking code file whose hash changed, show that the diff is only import statements and path strings. List any other change.
   b. The display. G2 and pd_repro check decisions, not the dot. Replay with K1g on the causal clock and compare byte for byte with the committed logs: one semi recording per test cell, plus one fully constrained and one unconstrained (m = 4) recording on B2. If a log differs only in recorded file paths, say so and show the diff.
   c. The teaching-pack export for B2 PA2 must reproduce reports/teaching_pack_app_v3_2026-10-01.json, apart from its "made" timestamp and recorded paths.
   d. Stream mode. Pre-flight must pass in stream mode, and rig --stream must run one B2 recording to the end with no dropped packets, with its own capture re-replaying identically through the harness.
   e. The retired/ folder. List every tracking module moved there, and confirm none is reached from pipeline/live/ or from the G2 and repro paths.

5. The 7 test failures that predate the move. Give the cause of each one that is tracking's (at least test_model_freeze, the two pairing-key tests and test_report_consistency).
   - test_model_freeze fails because RENDER_RULES.md was edited. That edit was authorised: rewritten for the app on 30 Sep, and rule 2a's K1g form added on 1 Oct. Update the freeze record to the new hash with a dated note citing those decisions, so the test passes and the record shows why.
   - For the others: if the cause is a stale test or an old report, fix the test or add a dated note to the report, changing no model or figure. If the cause is a real inconsistency in a figure, stop and report it.

6. If everything passes, tag the verified commit tracking-final-restructured-2026-10-01. Write reports/RESTRUCTURE_CHECK_TRACKING_2026-10-01.md containing Monitor's results, items 3 to 5, and a table translating every path cited in the tracking reports from old to new (taken from reports/PIPELINE_MOVES_2026-10-01.json), so the thesis's citations still resolve. Commit it by name.

If any check fails, stop and report. Don't fix anything by changing the model. A path fix that changes no output is fine, but list it.

Report back with one table: item, result, commit.
