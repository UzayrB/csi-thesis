# THE STANDING BRIEF. Read this file, not a memory of it

**This is the authority on what this batch is doing and why.** It holds the operator's instructions
VERBATIM. Any summary of them, anywhere, including one written by me in a previous message, is a
paraphrase and loses something. **Come back here between items rather than working from memory.**

Written 2026-09-22. Companion documents, which this brief points at rather than repeats:
`reports/RENDER_RULES.md` (the rendering contract, the single place rules live),
`reports/ROOM_TRANSFER_AUDIT_2026-09-22.md`, `reports/PREREG_lock_2026-09-22.md`,
`reports/PREPRESS_REGION_REPORT_2026-09-21.md`, `reports/HANDOFF_2026-09-22.md` (open items).

---

## INSTRUCTION 1, verbatim. The render batch and the pre-press reader

> Read reports/HANDOFF_2026-09-21.md, reports/SEMIBOUNDED_STATE.md and reports/RENDER_RULES.md first.
> TRACKING IS NEVER CLOSED. Wherever any document says "closed until DC2", that is superseded:
> remove it and record the supersession. Two parts, in order. Part 2 does not start until Part 1 is
> finished and reported. Keep contact minimal: write, queue, run in the background, report once per
> part.
>
> HARD CONSTRAINTS, unchanged: signal-only (no pace, elapsed time, dead reckoning or projection);
> data/ read only; pipeline/io/, firmware, serial code and pipeline/clean/common.py untouched;
> testing/ never imported; six participants only; freezes superseded, never overwritten; pairing key
> session|stem|pass_id; node geometry fixed (never propose moving a node, including for DC2, since
> changing room and layout together confounds the cross-room result). Pre-register before anything
> runs; any rule changed after seeing data is POST HOC and says so in those words. Ship rule, all
> three: (a) paired improvement interval on held-out folds entirely above zero, (b) median paired
> delta at least two passes per pairing, (c) monotone response to the arm's own weight. Plus
> substitution passes, both causal bounds hold (drawn-window and evidence), edge lines not degraded.
> British spelling, no em dashes.
>
> GENERALISATION. The thesis claim is cross-environment generalisation and DC2 (26 and 27
> September, different room, same grid, same relative node geometry) is the test. Fix causes in the
> model or decoder, never cosmetically in the renderer. Retraining is allowed wherever the evidence
> points at the model; train with grouped splits exactly as the existing heads were. Forbidden: any
> per-line bias, offset or prior fitted to Room A's drawn/true counts. It fits the answer and will not
> transfer. Judge everything on all nine pairings with the session-01 test folds shown explicitly and
> edge-line recall reported. Never judge on the demo pairing s0102_to_s03, which is the easiest fold.
> "Either drawn or committed right" (89.2%) is an after-the-fact oracle and is never quoted as
> headroom.
>
> ==================== STEP 0: THE PERMANENT RENDERING RULE SHEET ====================
>
> Make reports/RENDER_RULES.md the single permanent rendering rule sheet. Rewrite runs/constrained/
> demo/ACCEPTANCE.md so it holds measured results only and points to RENDER_RULES.md for rules;
> there must be exactly one place the rules live. Keep the six existing rules verbatim, then add the
> operator's vision as binding rules, decided by the operator and no longer open:
>
>   V1. THE DISPLAY RUNS EXACTLY 2.0 s BEHIND REAL TIME, whole system, every walk. This DECIDES the
>       open latency item (2 s, not about 5 s). Record it as an operator decision.
>   V2. THE RED DOT WAITS AT THE ROOM CENTRE until the commit, then commits to its line on the same
>       frame the green truth marker appears. Commit and marker appearance are one event.
>   V3. RED AND GREEN MOVE TOGETHER for the whole walk: both on the same 2 s delayed clock, the red
>       dot never shown ahead of its evidence, never parked beyond the fixed commit time. The
>       lock time is structural and identical on every walk, never adaptive, per rule 6. Therefore
>       any confidence-gated or variable-latency lock is FORBIDDEN.
>   V4. No static dwell footage appears in a demonstration video.
>
> Delete open item 2 ("tracking is closed until DC2"). Extend tests/test_render_rules.py so V1 to V4
> are each enforced by a test, including a test that the commit frame equals the marker's first
> frame on every walk and that the lock time does not vary across walks.
>
> ==================== PART 1: FIX THE RENDER AT ITS SOURCE ====================
>
> Known problems, from the six demo videos (120 walks): the 2 s locked line is 72.5% right against
> 78.3% for the full-walk committed answer. PA5 pass 1 (true A_rev, locked D_fwd) and pass 9 (true
> D_rev, locked E_col5) chose correctly early and then locked wrong. The lock over-draws E_col5 (15
> drawn vs 6 true), A_fwd (19 vs 12) and D_fwd (16 vs 12). D_rev to E_col5 is the largest confusion
> in the system. The mid-recording grid dwell appears in the videos.
>
> STEP 1, ROOM-TRANSFER AUDIT (read only). Write reports/ROOM_TRANSFER_AUDIT_2026-09-22.md: every
> component fitted to data (encoders, heads, standardisation statistics, the 25-cell marginal the
> emissions are divided by, the chain transition prior, the A2 start classifier, null and gate
> levels, display speed cap and flatten), what each is fitted on, whether it encodes Room A
> quantities, and whether DC2 must refit it, can reuse it, or cannot be judged without Room B data.
>
> STEP 2, DIAGNOSE THE 2 s LOCK (diagnostic, ships nothing). Over all nine pairings: drawn/true ratio
> per line and the drawn vs committed vs true confusion. Attribute the bias with no-retraining
> ablations at the 2 s lock: (i) no cell-marginal division, (ii) chain prior flattened, (iii) A2 start
> term removed, (iv) whether every chain has equal entry-state counts and comparable scores across
> chain lengths, (v) emission-only argmax over lines. Also measure, for walks where the lock was wrong
> but the committed answer right, what the line posterior looked like at 1.0, 1.5 and 2.0 s. If no
> ablation explains the bias, say so and do not invent a cause.
>
> STEP 3, IMPROVE THE DECISION AT A FIXED 2 s, PRE-REGISTERED in reports/PREREG_lock_2026-09-22.md.
> The lock time cannot move (V3), so the gain must come from better use of the same evidence. Arms
> follow from Step 2: a fix for any room-agnostic cause it finds, and if it points at the emissions,
> a retrained emission head, for example one trained specifically on early-walk windows (the first
> 2 s of each pass), since that is what the lock reads. Every arm must beat the current ship under
> the three-condition rule on held-out folds.
>
> STEP 4, RENDER. Cut the grid dwell entirely. Fix f3_render.py:443-447, where DWELL_EXCERPT_S
> (seconds) is added to a window index and yields 15 s, not 30, and add a guard test so no constant
> named *_S can be used as a window count. One re-render and one freeze whatever happens: if Step 3
> ships, the new decision, the dwell cut and V1 to V4 go in together and the 62.50 headline is
> re-measured over nine pairings with its interval; if it does not, the render changes for the dwell
> and V1 to V4 only and the headline does not move. Report every rule-5 check.
>
> ==================== PART 2: THE PRE-PRESS REGION READER, SEPARATE ====================
>
> Starts only after Part 1 is reported. Read reports/PREPRESS_REGION_REPORT_2026-09-21.md. Do not
> re-run anything it measured. Established: oracle ceiling +12.5 points; a reader must reach about
> 74% before it stops costing line accuracy; best reader 40.0% (arm C) and that was class collapse
> (W_mid 0.9%); edge midpoints read about 60%, corners at chance; substitution 0.89 to 0.95; the
> obstacle is cross-session generalisation (47 to 57% testing 02 or 03, 16 to 18% testing 01).
> Through the decoder it bought five passes in 840 with no weight response. Why it still matters:
> under V3 the lock cannot wait longer, so evidence from before the press is the only extra evidence
> that costs no latency.
>
> The question is no longer "read the region accurately" but "use a weak reader in a way that cannot
> harm". Pre-register in reports/PREREG_prepress_v2_2026-09-22.md, cheapest arms first:
>
>   (a) VETO, NOT VOTE. The reader only removes regions it rules out with high confidence, and never
>       boosts one. Choose the veto threshold on the selection folds so the TRUE region is vetoed on
>       at most 2% of passes there, then report the true-region veto rate on held-out folds.
>   (b) ABSTAIN. Apply the term only on passes where the reader's confidence exceeds a threshold set
>       on the selection folds; report coverage and accuracy on the covered passes.
>   (c) COARSE FIRST. Midpoint vs corner (two classes), plus which midpoint when midpoint, since
>       midpoints read about 60%. Corners are not forced.
>   (d) THE GENERALISATION ARM, which is the thesis angle: attack the session-01 shift directly with
>       causal per-session adaptation, meaning feature normalisation or AdaBN-style statistics
>       computed only from data recorded BEFORE the pass (for example that session's empty-room
>       baseline or earlier idle windows), never from the test pass or anything after it. Report
>       per-fold, especially the session-01 folds.
>   (e) Class-balanced training for any retrained reader, with per-region recall reported, so the
>       class collapse seen in arm C cannot recur unnoticed.
>
> Every arm is strictly causal (windows end at or before the press), grouped by pass with the
> grouping asserted, must pass substitution, and ships only under the three-condition rule through
> the decoder. The existing tests/test_prepress_is_causal.py guards stay green. If nothing ships,
> write it up as a measured negative and change nothing. Either way, confirm the DC2 protocol still
> carries the approach-walk capture item, since Room B is where this can be trained properly.
>
> DELIVERABLES: RENDER_RULES.md and ACCEPTANCE.md as above; the audit; the Step 2 diagnosis; both
> pre-registrations and their results; one re-render and freeze; one closing message per part with
> what shipped, whether the headline moved (with interval), the per-fold table, and which components
> DC2 must refit.

**PART 1 STATUS: ACCEPTED by the operator on 2026-09-22.** The refusal under condition (f) was
confirmed correct. Frozen at `runs/TRACKING_FROZEN_2026-09-22a.json`.

---

## INSTRUCTION 2, verbatim. The order of work after Part 1

> Part 1 accepted. The refusal under condition (f) was correct. Now, in this order:
>
> 1. DC2 CALIBRATION, BEFORE ANYTHING ELSE (DC2 is 26 September). The audit found the null level
>    fixed at -7.50 nats and the gate threshold an absolute 0.431 band energy, both fitted to Room A.
>    Write a calibration procedure into reports/DC2_PROTOCOL_2026-09-18.md: an empty-room baseline and
>    a few calibration walks recorded at the start of each DC2 day, with the gate threshold and null
>    level re-expressed RELATIVE to that day's own baseline, using only data recorded before any
>    evaluated pass. Implement the relative forms now and verify on Room A that they reproduce the
>    62.50 headline within one pass per pairing, so DC2 runs on a gate that transfers by design.
>    Record this in the room-transfer audit.
>
> 2. ACCEPTANCE.md: one sentence explaining why V3's lock offset is 2.25 s while V1's latency is
>    2.0 s (the first window centre relative to the press), measured, not assumed.
>
> 3. ONE PRE-REGISTERED STRUCTURAL ARM for the 2 s lock: length-normalised chain totals (per-state or
>    per-step mean, not sum), cell marginal KEPT, chain prior withheld as before. Same
>    three-condition rule plus condition (f). If refused, write up the pooled-versus-edge-line
>    trade-off as a finding, with the E_col1 figures, and change nothing.
>
> 4. Then Part 2, as written. Arm (d), causal per-session adaptation, is the priority arm because the
>    session-01 folds stayed flat on every Part 1 arm.
>
> Keep HANDOFF_2026-09-22.md OPEN ITEMS current after each item. Record the A_fwd over-draw (1.95
> under every estimator) as an open diagnostic with the hypothesis "TX proximity at S_mid plus the RX1
> link's symmetry", untested, not a cause.
>
> Give me an ETA and make sure the above prompt I gave you (the one talking about part two and
> everything) is stored in a markdown somewhere so that you persistantly come back to it through that
> and not through memeory

---

## INSTRUCTION 3, verbatim. The 2026-09-23 afternoon batch, after the crash

> Fresh session; the previous one crashed. Get up to speed from files, not memory:
> reports/QUEUE.md, reports/HANDOFF_2026-09-22.md, reports/RENDER_RULES.md,
> reports/BRIEF_render_and_prepress_2026-09-22.md, and the y1_diag, y1b_locksrc, y2a_causal and
> y2_dial results. Tracking is never closed.
>
> STATE: items 1 and 2 are DONE. Two locks existed. The quoted one read two windows past the lock
> horizon (60.83 held-out, E_col1 50.0); the causal render lock is 57.50, E_col1 42.59. y2_dial was
> REFUSED under (f) by one E_row1 pass.
>
> OPERATOR DECISIONS: (f) stays as written, and y2_dial's refusal stands. Record it as a finding
> (+5.00 held-out, refused by one pass, zero net change across the four edge lines). No retroactive
> rule change.
>
> COEXISTENCE / KEEP-ALIVE: the gait ID session is running; never touch its processes, files or its
> in-flight PREREG_ID addendum. Reuse the existing watchdog, heartbeat and caffeinate. OMP_NUM_THREADS=1.
> Rewrite QUEUE.md with the items below; on every wake read it and start the next PENDING item, never
> stop between items or wait for me; check in every 15 min in reports/CHECKIN_LOG.md.
>
> RULES: standing constraints unchanged; decision changes need pre-registration and the full ship rule
> plus (f); display-only items get contract checks plus one measurement; nine pairings, session-01
> folds shown; causal horizon only.
>
> QUEUE, in order:
> 1. CORRECT THE RECORD. Every document quoting the lookahead lock (t6, t7, FINDING_pooled_vs_edge,
>    PART1_REPORT, HANDOFF) gets the causal figures beside it, with the lookahead ones marked
>    non-causal and superseded. Add a test so no lock figure can be computed past the causal horizon.
> 2. PRESS-ALIGNED FIRST WINDOW (old item 4). Time one recording's cut first and report the ETA. Build
>    the new cache in a new location whose name carries the stride, never overwriting the shipped
>    tree. Then measure the entry hold, the lock and whole-walk tracking.
> 3. TWO NO-RETRAINING ARMS, pre-registered: (A) combine the three link posteriors by renormalised
>    product instead of arithmetic mean; (B) feed the g100 head to the decoder at its native 0.5 m
>    resolution instead of folding it to 25 cells, reporting the along-line substitution ratio too.
>    Correct any document that calls g100 a "gate head".
> 4. MID-WALK SWITCHING (old item 3), demonstration quality only, against the causal 57.50 baseline:
>    at most 2 switches, none in the final 1.0 m, decisions using radio to t + 2.0 s only. Keep it if
>    time-on-correct-line improves (held-out interval above zero) and wrong-to-right switches exceed
>    right-to-wrong by at least two passes per pairing. Show the committed line as text at walk end.
> 5. ONLY IF 2 IS DONE AND THE CACHE IS SAFELY STRIDE-KEYED: retrain the three 1 s heads.
>
> Before anything, run the suite and confirm the DC2 pipeline guards still pass. ETA per item in
> QUEUE.md. One closing report when all items are DONE or BLOCKED.

---

## INSTRUCTION 4, verbatim. Batch 2026-09-23d: the amended (f), the lock-phase fix, fusion, DC2

> Read first: reports/QUEUE.md, reports/RENDER_RULES.md, BATCH_2026-09-23c_REPORT.md,
> FINDING_lock_phase_2026-09-23.md, FINDING_linkfusion_2026-09-23.md, CORRECTION_causal_lock_2026-09-23.md,
> PREREG_DC2_crossroom_2026-09-22.md. Tracking is never closed. DC2 is 26 September.
>
> KEEP-ALIVE. Rewrite QUEUE.md with items 1 to 6 (PENDING/RUNNING/DONE/BLOCKED, next action, ETA). On
> every wake read it and start the next PENDING item; never stop between items or wait for me; if
> blocked, mark BLOCKED and move on. Compute as background jobs with verification chained. Reuse the
> existing watchdog, heartbeat and caffeinate; check in every 15 min in reports/CHECKIN_LOG.md. Never
> touch the gait ID session's processes, files or tests. OMP_NUM_THREADS=1. One closing report when
> all items are DONE or BLOCKED.
>
> STANDING RULES unchanged: signal-only, data/ read only, protected code untouched, freezes superseded
> never overwritten, key session|stem|pass_id, geometry fixed, causal horizon only, nine pairings with
> session-01 folds shown, British spelling.
>
> 1. CONDITION (f) AMENDED TO A NET-POSITIVE RULE. OPERATOR DECISION, POST HOC in those words.
>    An arm passes (f) if the four edge lines' combined change in correct walks is zero or positive,
>    AND no single edge line loses more than TWO walks (the same two-pass floor as (b); it stops a
>    collapse such as E_col1 to 0.00). Reason: one walk is the resolution floor, and the old per-line
>    zero tolerance refused arms that were net positive across the edge lines. Record it in
>    SEMIBOUNDED_STATE.md section 10 and the BRIEF. Apply it UNIFORMLY: re-evaluate every arm refused
>    since 2026-09-22 (y2_dial, the t7 lock estimator arms, t9, b_abstain_0.25, a_veto_1.0, switching,
>    product fusion, g100 native) and table which now pass all conditions. No cherry-picking.
>
> 2. LOCK PHASE FIX (correctness, not an arm, so the ship rule does not apply). The shipped lock breaks
>    V3: it is drawn ahead of its evidence on 1080 of 1080 passes. Adopt the press-aligned lattice as the
>    ONE lattice for everything drawn and quoted. Make the live runner align its windows to the press
>    the same way, and confirm replay decision equality. Remove the strict-xfail marker deliberately.
>
> 3. PRODUCT FUSION on the COMMITTED decision only (the lock keeps mean fusion, since it fails even the
>    amended (f) there). Choose w on the selection folds s01_to_s02 and s02_to_s01 ONLY, on the
>    press-aligned lattice. It ships if (a), (b), (c) as clarified, substitution, both causal bounds and
>    amended (f) pass at that w. Report the gain's split between link agreement and sharpening
>    (control T). If any arm from item 1 also passes and is compatible, include it; report interactions.
>
> 4. RE-RENDER, once, following reports/RENDER_RULES.md in full: rules 1 to 6 and V1 to V4 as amended
>    (2.0 s latency, both dots start together at the delayed press with red at the committed line's
>    entry, the lock final, no dwell footage, shift_w 0.50, committed line named as text at every walk's
>    end). Report every rule-5 check (jumps, missing dots, both causal bounds including the evidence
>    bound), all as computed quantities. One freeze under a new letter. Re-measure the committed headline
>    and the lock over nine pairings with intervals. Report BOTH figures everywhere: the pre-registered
>    62.50 and the post-amendment figure, with the amendment disclosed beside it. Update ACCEPTANCE.md,
>    HANDOFF and STATE.
>
> 5. DC2 PRE-REGISTRATION, amended before any Room B data exists: the shipped configuration is what DC2
>    tests. Primary comparison: the frozen tracker unchanged against the same tracker with null and gate
>    re-anchored on the calibration block, at the PRODUCT's scale. Confirmatory arms b_abstain_0.25 and
>    any item-1 arm that now ships, each at 97.5 percent intervals for multiplicity. (f) as amended.
>    Wire everything into dc2_pipeline and pass the stand-in plumbing check.
>
> 6. DC2 READINESS: if the live rig run has not been done, do it (three receivers, live display, raw
>    capture recorded, decoded offline, decision equality confirmed, packet loss and latency reported).
>    Update DC2_FIELD_CHECKLIST.md.
>
> CLOSING REPORT: the item-1 re-evaluation table, what shipped, the pre-registered and post-amendment
> headlines with intervals, the lock figure, the render's rule-5 checks, the freeze letter, DC2 status.

---

## RULE CHANGE RECORDED FROM INSTRUCTION 4 (the operator's, POST HOC in those words)

**Condition (f) is amended:** an arm passes (f) if the four edge lines' combined change in correct
walks is zero or positive, AND no single edge line loses more than TWO walks. Recorded in full in
`reports/SEMIBOUNDED_STATE.md` section 10, and applied uniformly in
`reports/REEVAL_f_amended_2026-09-23.md`.

---

## INSTRUCTION 5, verbatim. Batch 2026-09-23e: switching as display, the end text, fusion for DC2, a fifth receiver

Received 2026-09-23 ~16:40.

> Read reports/QUEUE.md, BATCH_2026-09-23d_REPORT.md, CORRECTION_drawn_lock_2026-09-23.md,
> reports/RENDER_RULES.md and PREREG_switching_2026-09-23.md first. Tracking is never closed. DC2 is
> 26 September. Keep-alive as before: rewrite QUEUE.md with items 1 to 7, never stop between items or
> wait for me, 15-minute check-ins in CHECKIN_LOG.md, reuse the existing watchdog, heartbeat and
> caffeinate, OMP_NUM_THREADS=1, never touch the gait ID session. Standing rules unchanged. One
> closing report when every item is DONE or BLOCKED.
>
> 1. MID-WALK SWITCHING, OPERATOR DECISION (display only; it changes no committed answer or quoted
>    accuracy figure, so it is adopted as a presentation decision, not through the ship rule). Amend
>    RENDER_RULES rule 1 with these constraints:
>    - at most ONE switch per walk, and it is final (never back to the locked line). Measured K=1
>      +4.05 against K=2 +4.10, so a second switch buys nothing;
>    - only to the decoder's current best line, and only after it has led the drawn line by theta for
>      TWO consecutive decode steps (1.0 s), so the earliest switch is 1.0 s after the lock;
>    - never once the dot is within the final 1.0 m of its current line;
>    - decisions use radio up to display time t + 2.0 s only, never beyond;
>    - no teleport: the dot slides over 0.5 s along the straight segment between its position on the
>      old line and the decoder's position on the new line (rule 2 holds, no pace), and the switch is
>      marked on screen.
>    Choose theta on the selection folds s01_to_s02 and s02_to_s01 only. Measure over nine pairings,
>    session-01 folds shown: time on correct line against lock-final (paired, with interval),
>    wrong-to-right against right-to-wrong, edge-line walks, and the distribution of switch jump
>    distances, including how many move the dot more than 1.5 m. Keep it if time on correct line is
>    positive and wrong-to-right exceeds right-to-wrong. If more than a quarter of switches move the dot
>    over 1.5 m, also test restricting switches to lines whose decoded position is within 1.5 m of the
>    dot, and report both. Disclose beside it that it failed (f) as a decision arm (E_col5 -3 in
>    y3_switch). Tests: at most one switch per walk, none back to the locked line, none in the final
>    1.0 m, the persistence rule holds, every switch decision causal on both bounds, and switch jumps
>    counted separately from lock jumps.
>
> 2. END-OF-WALK TEXT SHOWS THE SHIPPED COMMITTED DECISION. The text currently shows the bounded rescore
>    at the end press (60.00 on the ONE lattice), which is below the shipped committed headline (73.33,
>    with a_veto_1.0) and uses the end press the semi-bounded mode is not told. Show the shipped
>    semi-bounded committed decision instead, labelled as such, and verify walk for walk that the text
>    equals the headline decision. Record the ONE lattice's cost on the bounded answer (65.83 to 60.00,
>    paired -2.59) in ACCEPTANCE and STATE as the disclosed price of the correctness fix.
>
> 3. RE-RENDER ONCE with items 1 and 2, following RENDER_RULES in full (2.0 s latency, both dots start
>    together at the delayed press with red at the committed line's entry, shift_w 0.50, no dwell
>    footage), every rule-5 check computed. New freeze letter. The headline does not change. ACCEPTANCE's
>    per-walk tables are regenerated from the render's own decode and checked walk for walk, with no hand
>    edits.
>
> 4. PRODUCT FUSION AT w = 0.25: NOT shipped in Room A (selecting it now would be selecting on held-out
>    folds). Add it to PREREG_DC2_crossroom as an EXPLORATORY arm, not confirmatory, frozen under a new
>    letter before any Room B data, with null and gate re-anchored at the product's scale for that arm
>    only. Wire the fusion flag into dc2_pipeline per arm and re-pass the stand-in plumbing check.
>
> 5. y2_dial stays refused. Record it; do not re-measure.
>
> 6. FIFTH RECEIVER. The operator is adding a spare ESP32 as an extra receiver next to the TX for DC2,
>    as a dedicated identification link. The tracking node geometry is unchanged. Make dc2_pipeline, the
>    ingest guard and the live runner accept a fourth receiver's capture without error, and ensure
>    tracking reads ONLY the original three links, by node name, never by file order. Add a test that
>    tracking decisions are identical with and without the fourth receiver's file present. Update
>    DC2_FIELD_CHECKLIST.md with its port, naming and a check that all four receivers stream.
>
> 7. LIVE RIG RUN: prepare it as ONE command plus a short on-screen prompt for the operator, so it runs
>    the moment the receivers are attached. Check /dev for the receivers at every check-in; if they
>    appear, run it (live display, raw capture recorded, decoded offline, decision equality, packet loss
>    and latency per link). Otherwise mark it BLOCKED ON OPERATOR at the top of QUEUE.md.
>
> CLOSING REPORT: switching figures (chosen theta, time on correct line, wrong-to-right against
> right-to-wrong, jump distances), the end-text check, the render's rule-5 checks, the freeze letter,
> the fifth-receiver test, and DC2 status.

## INSTRUCTION 6, verbatim. Batch 2026-09-23f: three switching arms, the winner rendered, the investigation

Received 2026-09-23 ~17:55. It follows my reply proposing a K = 2 / 1.5 m measurement.

> Yes, run it, then render the winner without asking. Choose by the rule below, fixed now before any
> numbers exist.
>
> ARMS, all with the 1.5 m proximity rule (the rendered variant), the 2-nat margin on two consecutive
> checks, and decisions using radio to display time t + 2.0 s only:
>   A. current: at most 1 switch, no switch in the final 1.0 m
>   B. operator's proposal: at most 2 switches, no switch in the final 1.5 m
>   C. at most 1 switch, no switch in the final 1.5 m (separates the cutoff's effect from the second
>      switch's)
> Theta chosen on the selection folds s01_to_s02 and s02_to_s01 only, per arm. A second switch may
> never return to a line already drawn in that walk.
>
> REPORT over nine pairings, session-01 folds shown, held-out paired intervals:
> time on correct line against lock-final; wrong-to-right against right-to-wrong; how often the dot
> ENDS on the committed line (and how often the end-of-walk text contradicts the dot); switches per
> walk; jumps over 1.5 m; the median time of each switch after the lock; edge-line walks; and how often
> the two estimators disagree at the lock.
>
> SELECTION RULE (fixed now): keep only arms where time on correct line is positive with the held-out
> interval above zero AND wrong-to-right exceeds right-to-wrong. Among those, pick the highest
> end-on-committed agreement. If two are within one walk per pairing of each other, pick the one with
> fewer switches, then fewer jumps over 1.5 m. If no arm qualifies, keep lock-final and report why.
>
> Then amend RENDER_RULES rule 1 to the chosen arm as an operator decision, re-render once under the
> full RENDER_RULES with every rule-5 check computed, new freeze letter, headline unchanged. In
> ACCEPTANCE and STATE, describe switching honestly: the lock uses the edge-safe display decoder, the
> switch hands over to the final-answer scorer once it is confidently different, and most switches
> reconcile the two estimators rather than react to new mid-walk evidence. Give the disagreement rate
> beside it.
>
>
> Investigate

## INSTRUCTION 7, verbatim. Batch 2026-09-23g: the ablation, the scorer lock, the DC2 model freeze

Received 2026-09-23 20:14 (clock read). The LAST model batch before DC2; deadline 12:00 on 24 September.

> Read reports/INVESTIGATION_switching_2026-09-23f.md, BATCH_2026-09-23f_REPORT.md and
> PREREG_DC2_crossroom_2026-09-22.md first. Keep-alive as before (QUEUE.md, never stop between items,
> 15-minute check-ins, reuse watchdog, heartbeat and caffeinate, OMP_NUM_THREADS=1). This is the LAST
> model batch before DC2: finish by 12:00 on 24 September, then the model is frozen for DC2.
>
> 1. ABLATION, diagnostic, ships nothing: which component of the display decode causes the 33.6 percent
>    lock disagreement with the scorer? Remove one at a time: the speed cap, the display head, and the
>    missing veto term. Report the lock accuracy, the disagreement rate and edge walks for each.
>
> 2. SCORER LOCK, pre-registered in reports/PREREG_scorerlock_2026-09-23.md BEFORE running. Disclose in
>    the pre-registration that the lead (+4.17 paired, edges net +1) was observed on all nine pairings,
>    held-out folds included, in e2_switch, so this Room A test is not clean and DC2 is its confirmatory
>    test. Arm: the lock line = argmax of (1 - w) x display-lock score + w x scorer score, with w in
>    {0, 0.25, 0.5, 0.75, 1.0}. Choose w on the selection folds only. Full ship rule: (a), (b), (c) as
>    clarified, substitution, both causal bounds, amended (f). The dot's path after the lock comes from
>    the restricted along-line decode on the chosen line, as after a switch; check continuity.
>
> 3. IF IT SHIPS: re-choose the switching theta on the selection folds under the new lock (same
>    constraints as arm C), re-render once under the full RENDER_RULES with every rule-5 check,
>    re-measure the lock and the switch figures, report the end-text-versus-dot contradiction rate
>    against the current 433, new freeze letter. The committed headline does not change. Update ACCEPTANCE
>    and STATE: the lock, switches and final answer now come from one scorer.
>    IF IT DOES NOT SHIP: record it with the ablation, and change nothing.
>
> 4. DC2 FREEZE: amend PREREG_DC2_crossroom before any Room B data, naming the final lock (whichever it
>    is) as the display component. Re-pass the stand-in plumbing check. Write reports/MODEL_FREEZE_DC2.md
>    listing the exact configuration DC2 will test, with a line stating that no model change is made
>    until the Room B analysis.
>
> Closing report: the ablation table, the scorer-lock verdict, the new lock and switching figures if
> shipped, the freeze letter, and confirmation the DC2 plumbing check passes.

## INSTRUCTION 8, verbatim. 2026-09-23 22:37: the scorer lock as an exploratory DC2 display comparison

> Optional, no model change (the freeze 23h hashes must still verify): add to PREREG_DC2_crossroom, before
> any Room B data, an EXPLORATORY display comparison: the scorer lock at w = 0.25 against the display
> lock, scored once on DC2. Define its substitution test now as swapping BOTH the walk emissions and the
> pre-press radio behind the start term. It affects no DC2 outcome. Confirm the freeze hashes still verify
> after adding the analysis code, and re-pass the stand-in plumbing check.

## INSTRUCTION 9, verbatim. 2026-09-28 22:12 SAST: THE DIRECTION CHANGE (tracking and identification)

Recorded by the Tracking session on receipt. It supersedes, for DEVELOPMENT work, the ship rule,
rule (f), pre-registration of each change and deference to the frozen configuration. Every earlier
instruction in this file stays as the record of how the thesis figures were made.

> DIRECTION CHANGE, from the operator, applies to BOTH tracking and identification. Record it in the
> BRIEF, STATE, HANDOFF and your memory.
>
> The goal is now the best model that generalises across rooms and days and meets the project brief:
> real-time identification and 2D tracking, evaluated for spatial resolution, latency and robustness
> to environmental change.
>
> KEEP, untouched: every existing report, freeze and result. They are the thesis record and the "before"
> reference. Never delete or rewrite them.
>
> STOP, for development work:
> - pre-registering each change;
> - labelling things POST HOC;
> - the three-condition ship rule and the per-line edge rule (f);
> - deferring to the frozen configuration;
> - asking me to approve each development choice.
> Keep a development log instead: what changed, why, and the result.
>
> KEEP, because these are system requirements, not ceremony:
> - no leakage: split by whole sessions, and fit every statistic on training data only (or on causal
>   pre-pass data, such as a calibration walk);
> - anything claimed as live must be causal;
> - the tracker stays signal-only: no pace, elapsed time or dead reckoning;
> - identification is gait-based: pace only as one parameter inside gait analysis, never a bare speed
>   comparison;
> - the rendering rules for demo videos;
> - data/ is read only, and the free-movement recordings are never used for training or testing.
>
> EVALUATION STANDARD, replacing all previous ship rules: five sessions, A1, A2, A3, B1 and B2. Leave
> one session out: train on four, test on the fifth, rotating through all five. Every tuning and model
> choice is made on validation inside the four training sessions, never on the test session. Report
> per held-out session and per room, lock and committed, the four edge lines, with 95 percent intervals,
> beside the frozen Room A to Room B figures as the reference.
>
> FREEDOM: retrain, change architectures, fuse links (including product fusion), joint or per-link
> encoders, normalisation, multi-room training, anything that improves generalisation. Priorities for
> tracking: the Room B lock (currently 14 to 30 percent) and the committed answer in both rooms.
> Note that in DC2, RX2 was moved beside the TX for each participant's identification capture and then
> returned to taped marks, so small placement differences between recordings are possible. Treat that as
> real-world variation the model must cope with.
>
> Keep-alive as usual; one closing report per batch.

## Reading notes that are mine, not the operator's

Kept separate so the instructions above stay clean.

- **Item 1 is the deadline item.** DC2 is 26 September. The relative gate and null must be
  implemented and verified on Room A before anything else, because a gate that does not transfer
  makes every DC2 number unreadable and the failure is silent rather than loud.
- **"Within one pass per pairing"** is the acceptance bar for the relative forms on Room A: a
  pairing holds 120 passes, so one pass is 0.833 points.
- **Condition (f) did the work in Part 1.** Without it, `E_both` at +10.00 points would have
  shipped while taking E_col1 from 50.0 to 7.4 percent. (Annotated 2026-09-23c: NON-CAUSAL lock
  figures; **causally +4.17 and E_col1 42.59 to 0.00**, `reports/CORRECTION_causal_lock_2026-09-23.md`.) Expect item 3 to meet the same wall and
  write the trade-off up rather than hunting for a way round it.
- **Part 2 arm (d) is the priority** and is also the thesis angle: every Part 1 arm was flat or
  worse on the three session-01 folds, so the shift is the obstacle rather than the reader.
