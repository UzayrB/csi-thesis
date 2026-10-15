# ARCHIVE_CODE: every module, script, tool and test removed by the cleanup of 2026-09-24

Nothing listed here is lost. Every file is in git at the tag `pre-cleanup` (commit `f6d227a`), and every result it produced stays under `runs/constrained/fh/`, `runs/constrained/<stage>/`, `runs/identify/` or in the reports. Restore one file with

    git checkout pre-cleanup -- <path>

A restored stage module may need modules that were also removed, and some stage modules guard their import on the artefact roots (`pipeline/constrained/_guard.py`); restore the family together and run it as the entry point. The dates are the file's last modification before removal. The descriptions are the first sentence of each file's own docstring or header comment.

## 1. `pipeline/constrained/`: 87 finished stage modules

None is imported by the frozen DC2 system, the demonstration render, the live rig or a kept test (checked against `reports/DC2_DEPENDENCY_CLOSURE.txt`, `reports/PINNED_FILES.txt` and a grep for each name as an import and as a string). Stage names that the render loads as RESULTS (`a3_lock`, `b1_motion`, `f2_verdict`, `g6_timeline`, `r1_reference`, `r3_lagsweep`, `r3_prior`) keep their `runs/constrained/fh/<name>/results.json`.

### Decoder rebuild, 2026-09-17 (brief `decoder_rebuild_prompt_2026-09-17.md`)

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/rb1_truth.py` | 2026-09-17 | STAGE 1 of the decoder rebuild: fix the truth, fix the metric, re-baseline. | `runs/constrained/rb1_truth/` |
| `pipeline/constrained/rb2b_stride.py` | 2026-09-17 | STAGE 2b of the decoder rebuild: the half-second stride. | `runs/constrained/rb2b_stride/` |
| `pipeline/constrained/rb2d_retrain.py` | 2026-09-19 | STAGE 2d of the decoder rebuild: the 0.5 s RETRAIN. | `runs/constrained/rb2d_retrain/` |
| `pipeline/constrained/rb8_verify.py` | 2026-09-17 | STAGE 8 of the decoder rebuild: verification. | `runs/constrained/rb8_verify/` |
| `pipeline/constrained/rb9_report.py` | 2026-09-18 | STAGE 9 of the decoder rebuild: Room B, freeze and report. | `runs/constrained/rb9_report/` |

### Cleanup and mid-line stall batch, 2026-09-18

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/rd1_stall.py` | 2026-09-18 | PHASE 3. THE MID-LINE STALL, measured before anything is changed. | `runs/constrained/rd1_stall/` |
| `pipeline/constrained/rd2_pin.py` | 2026-09-18 | PHASE 4.3. THE PINNED DECODER, AND THE GUARD THAT STOPS IT CHEATING. | `runs/constrained/rd2_pin/` |
| `pipeline/constrained/rd3_verify.py` | 2026-09-18 | PHASE 6.2. Verification for the cleanup and the stall batch: rescore, leakage, assertions, hashes. | `runs/constrained/rd3_verify/` |
| `pipeline/constrained/rd4_halfstride.py` | 2026-09-19 | ITEM 2 of the operator's round of 2026-09-18: the BOUNDED mode on the 0.5 s features. | `runs/constrained/rd4_halfstride/` |

### End windows and the semi-bounded mode, 2026-09-18

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/re1_endlabels.py` | 2026-09-18 | PHASE 1 of the end-windows brief, 2026-09-18. | `runs/constrained/re1_endlabels/` |
| `pipeline/constrained/re2_retrain.py` | 2026-09-19 | PHASE 2: retrain the heads on the extended label set, in an isolated tree. | `runs/constrained/re2_retrain/` |
| `pipeline/constrained/re3_bounded.py` | 2026-09-19 | PHASE 3: the bounded mode decoding the whole line, with the extended-label heads. | `runs/constrained/re3_bounded/` |
| `pipeline/constrained/re5_ship.py` | 2026-09-18 | PHASE 5: renders, report, freeze, verification. | `runs/constrained/re5_ship/` |
| `pipeline/constrained/re6_heads.py` | 2026-09-20 | THE HEADS DECISION, made on the aggregate and never on the demonstration pairing. | `runs/constrained/re6_heads/` |
| `pipeline/constrained/re7_finalise.py` | 2026-09-18 | PHASE 5 finalisation: acceptance table, report section, freeze 18c, verification, summary. | `runs/constrained/re7_finalise/` |

### Semi-bounded and stride batch, 2026-09-18

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/sb0_train_half.py` | 2026-09-19 | PHASE 0.3 of the semi-bounded and stride batch: train the MISSING 0.5 s pairings. | `runs/constrained/sb0_train_half/` |
| `pipeline/constrained/sb1_decompose.py` | 2026-09-18 | PHASE 1: decompose the semi-bounded gap. | `runs/constrained/sb1_decompose_half/`, `runs/constrained/sb1_decompose_one/` |
| `pipeline/constrained/sb1b_d1_speed.py` | 2026-09-18 | D1, READ-ONLY: is the chain being FINISHED early rather than ABANDONED early, and can the motion gate see the end? | `runs/constrained/sb1b_d1_speed_half/`, `runs/constrained/sb1b_d1_speed_one/` |
| `pipeline/constrained/sb2g_gate.py` | 2026-09-18 | Apply the GUARD-AS-GATE rule to an ablation that has already been measured. | `runs/constrained/sb2g_gate/` |
| `pipeline/constrained/sb3_exitsweep.py` | 2026-09-20 | PHASE 3: the exit parameters, swept for THIS mode rather than inherited from the unbounded one. | `runs/constrained/sb3_exitsweep_half/`, `runs/constrained/sb3_exitsweep_one/` |
| `pipeline/constrained/sb3v_verdict.py` | 2026-09-18 | THE SEMI-BOUNDED VERDICT, taken BEFORE phase 4's bounded figure existed. | `runs/constrained/sb3v_verdict/` |
| `pipeline/constrained/sb4_stride.py` | 2026-09-20 | PHASE 4: the stride decision for the BOUNDED demonstration. | `runs/constrained/sb4_stride_half/`, `runs/constrained/sb4_stride_one/` |
| `pipeline/constrained/sb4c_stridedecision.py` | 2026-09-20 | PHASE 4.3: does the 0.5 s stride ship for the BOUNDED demonstration? | `runs/constrained/sb4c_stridedecision/` |
| `pipeline/constrained/sb4o_override.py` | 2026-09-18 | O3: the OPERATOR OVERRIDE shipping the 0.5 s stride for the bounded demonstration. | `runs/constrained/sb4o_override/` |
| `pipeline/constrained/sb5_live.py` | 2026-09-18 | PHASE 5: the three-mode table at the shipped stride, live behaviour, and the audits. | `runs/constrained/sb5_live/` |
| `pipeline/constrained/sb6_freeze.py` | 2026-09-18 | PHASE 6: verification and the freeze. | `runs/constrained/sb6_freeze/` |

### Window probe, 2026-09-18 to 19

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/wp0_feasibility.py` | 2026-09-18 | PHASE 0 of the window probe: is a shorter analysis window feasible at all? | `runs/constrained/wp0_feasibility/` |
| `pipeline/constrained/wp1_gate.py` | 2026-09-20 | PHASE 1: the confidence-gate curve. | `runs/constrained/wp1_gate/` |
| `pipeline/constrained/wp2_window1s.py` | 2026-09-19 | PHASE 2 of the window probe: the 1.0 s analysis window on the demonstration pairing. | `runs/constrained/wp2_window1s/` |
| `pipeline/constrained/wp3_window05s.py` | 2026-09-19 | PHASE 3 of the window probe: the 0.5 s analysis window on the demonstration pairing. | `runs/constrained/wp3_window05s/` |
| `pipeline/constrained/wp4_verdict.py` | 2026-09-19 | PHASE 4: the verdict, the report section, the summary and the verification. | `runs/constrained/wp4_verdict/` |
| `pipeline/constrained/wp_arm.py` | 2026-09-20 | One window-probe ARM: regenerate, train one pairing, and measure it against the shipped window. | no results folder; see the report named in its docstring |
| `pipeline/constrained/wp_window_common.py` | 2026-09-18 | Shared machinery for the window-probe arms. | no results folder; see the report named in its docstring |

### F, H and live render batch, 2026-09-19

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/f0_repairs.py` | 2026-09-19 | PHASE 0: repairs before any new result. | `runs/constrained/fh/f0_repairs/` |
| `pipeline/constrained/f2_verdict.py` | 2026-09-19 | PHASE 2: combinations with F and H, the RE-TAKEN verdict, and freeze 18i. | `runs/constrained/fh/f2_verdict/` |
| `pipeline/constrained/f4_verify.py` | 2026-09-19 | PHASE 4: verification and the summary. | `runs/constrained/fh/f4_verify/` |

### Multi-head pool batch, 2026-09-19 to 20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/g1_ensprep_multi.py` | 2026-09-19 | IMPROVEMENT 1, step one: infer the remaining frozen 1 s head sets over the 0.5 s window set. | no results folder; see the report named in its docstring |
| `pipeline/constrained/g5_freeze.py` | 2026-09-20 | THE FREEZE for the multi-head pool batch. | `runs/constrained/fh/g5_freeze/` |
| `pipeline/constrained/g6_timeline.py` | 2026-09-19 | The commitment timeline on the shipped pool, at the display hysteresis the video draws. | `runs/constrained/fh/g6_timeline/` |

### Overnight semi-bounded batch, 2026-09-19

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/n0_setup.py` | 2026-09-19 | PHASE 0: setup and the reading that arm B depends on. | no results folder; see the report named in its docstring |
| `pipeline/constrained/n1_diag.py` | 2026-09-20 | PHASE 1: read-only diagnostics on the shipped semi-bounded output. | no results folder; see the report named in its docstring |
| `pipeline/constrained/n3_combos.py` | 2026-09-19 | PHASE 3: combinations of the arms that survived phase 2, every one gated, one configuration out. | no results folder; see the report named in its docstring |
| `pipeline/constrained/n4_calib.py` | 2026-09-19 | PHASE 4: day-only calibration on the live mode, on ONE pairing, LABELLED, deciding nothing. | no results folder; see the report named in its docstring |
| `pipeline/constrained/n5_verdict.py` | 2026-09-19 | PHASE 5: the three-mode table, the verdict, the timelines and the audits. | no results folder; see the report named in its docstring |
| `pipeline/constrained/n6_freeze.py` | 2026-09-19 | PHASE 6: verification, the freeze, the report section. | no results folder; see the report named in its docstring |
| `pipeline/constrained/night_eta.py` | 2026-09-19 | ETA.txt, rebuilt after every stage from MEASURED stage times. | no results folder; see the report named in its docstring |
| `pipeline/constrained/night_summary.py` | 2026-09-19 | SUMMARY_NIGHT.txt. Always written, by the runner's trap, even when a stage failed. | no results folder; see the report named in its docstring |

### Motion model and park-watch-lock, 2026-09-20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/a3_lock.py` | 2026-09-20 | A4 and A1 to A3: keep decoding to the horizon, then park, watch and lock. | `runs/constrained/fh/a3_lock/` |
| `pipeline/constrained/b1_motion.py` | 2026-09-20 | B1: the motion model, swept one axis at a time, pre-registered and gated. | `runs/constrained/fh/b1_motion/` |

### Render fix: the strict causal rule, 2026-09-20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/c1_causal.py` | 2026-09-20 | ITEM 1 and ITEM 4: the strict causal rule, and the wait curve under it. | `runs/constrained/fh/c1_causal/` |
| `pipeline/constrained/c2_window1s.py` | 2026-09-20 | ITEM 5: the same wait curve on a ONE SECOND analysis window, because item 1 found a leak. | `runs/constrained/fh/c2_window1s/` |

### Run-up and pre-press, 2026-09-20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/p2_prepress.py` | 2026-09-20 | ITEM 2: how much is in the pre-press windows, read with the FROZEN five-head pool. | `runs/constrained/fh/p2_prepress/` |
| `pipeline/constrained/p3_direction.py` | 2026-09-20 | ITEM 3: can the run-up stop the decoder choosing the REVERSED chain? | `runs/constrained/fh/p3_direction/` |

### Parts 1 to 3, 2026-09-20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/q2_extras.py` | 2026-09-20 | The two extra measurements the operator asked for alongside Part 2. | `runs/constrained/fh/q2_extras/` |

### Render rules R1 to R6, 2026-09-20 to 21

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/r1_reference.py` | 2026-09-20 | R1: WHICH REFERENCE DOES THE DOT ACTUALLY TRACK? | `runs/constrained/fh/r1_reference/` |
| `pipeline/constrained/r2_softentry.py` | 2026-09-20 | R2: soft entry against the shipped free entry, on the five-head pool, nine cross-day pairings. | `runs/constrained/fh/r2_softentry/` |
| `pipeline/constrained/r3_lagsweep.py` | 2026-09-20 | R3: the display lag sweep for semi-bounded, judged on on-screen tracking. | `runs/constrained/fh/r3_lagsweep/` |
| `pipeline/constrained/r3_prior.py` | 2026-09-20 | R3: LESS MOTION MODEL. | `runs/constrained/fh/r3_prior/` |
| `pipeline/constrained/r4_start.py` | 2026-09-20 | R4: START EVIDENCE, FINER AND CONFIDENCE-WEIGHTED. | `runs/constrained/fh/r4_start/` |
| `pipeline/constrained/r5_lock.py` | 2026-09-20 | R5: THE LOCK AGAINST THE COMMITMENT, shown honestly. | `runs/constrained/fh/r5_lock/` |
| `pipeline/constrained/r5_timeline.py` | 2026-09-20 | R5: the commitment timeline on the pool, measured on the line the viewer is ACTUALLY SHOWN. | `runs/constrained/fh/r5_timeline/` |
| `pipeline/constrained/r6_latency.py` | 2026-09-21 | R6: THE LATENCY CURVE. | `runs/constrained/fh/r6_latency/` |

### Decoder confirmation and display causality, 2026-09-20

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/s0_verify.py` | 2026-09-20 | STAGE 0: settle "the accuracy dropped" with numbers, recomputed from artefacts. | `runs/constrained/fh/s0_verify/` |
| `pipeline/constrained/s1_confirm.py` | 2026-09-20 | STEP 1: confirm the shipped decoder, A1 + A2 at 0.5, ceiling off for the decision. | `runs/constrained/fh/s1_confirm/` |
| `pipeline/constrained/s2b_decision_causality.py` | 2026-09-20 | STEP 2b: the EVIDENCE BOUND of the DECISION path, not only the display. | `runs/constrained/fh/s2b_decision_causality/` |

### Pre-press region reader and the 2 s lock, 2026-09-21 to 23

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/t3_ship.py` | 2026-09-21 | THE SHIP TEST: the REAL pre-press region reader through the decoder, its weight re-swept. | `runs/constrained/fh/t3_ship/` |
| `pipeline/constrained/t4_finetune.py` | 2026-09-21 | ARM C: FINE-TUNE THE ENCODER on the pre-press windows. | `runs/constrained/fh/t4_finetune/` |
| `pipeline/constrained/t5_shipc.py` | 2026-09-21 | THE SHIP TEST FOR ARM C: the BEST available region reader through the decoder. | `runs/constrained/fh/t5_shipc/` |

### Pre-press reader version 2, 2026-09-22

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/u3_trackeradapt.py` | 2026-09-22 | THE TRACKER EXTENSION: causal per-session adaptation applied to the TRACKER'S emissions. | `runs/constrained/fh/u3_trackeradapt/` |
| `pipeline/constrained/u4_mechanism.py` | 2026-09-22 | MECHANISM CHECK on b_abstain_0.25: WHERE do the gained and lost passes come from? | `runs/constrained/fh/u4_mechanism/` |

### Items A to C and the drawn dot's phase, 2026-09-22

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/v1_afwd.py` | 2026-09-22 | ITEM C: THE A_fwd DIAGNOSTIC. | `runs/constrained/fh/v1_afwd/` |
| `pipeline/constrained/w1_dotphase.py` | 2026-09-22 | W1: THE DRAWN DOT'S PHASE. | `runs/constrained/fh/w1_dotphase/` |

### Batch 2026-09-23d

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/d1_reeval.py` | 2026-09-23 | D1: EVERY ARM REFUSED SINCE 2026-09-22, RE-EVALUATED UNDER THE AMENDED CONDITION (f). | `runs/constrained/fh/d1_reeval/` |
| `pipeline/constrained/d3_combo.py` | 2026-09-23 | D3: THE INTERACTION. The pre-press veto arms WITH product fusion on the committed decision. | no results folder; see the report named in its docstring |
| `pipeline/constrained/d3_eval.py` | 2026-09-23 | D3 EVALUATION: item 3 of batch 23d, by `reports/PREREG_committed_fusion_2026-09-23.md`. | `runs/constrained/fh/d3_eval/` |

### Batch 2026-09-23g

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/g1_ablation.py` | 2026-09-23 | G1: WHY THE DISPLAY LOCK AND THE SCORER DISAGREE. | `runs/constrained/fh/g1_ablation/` |
| `pipeline/constrained/g2_scorerlock.py` | 2026-09-23 | G2: THE SCORER LOCK. Batch 2026-09-23g, item 2. | `runs/constrained/fh/g2_scorerlock/` |

### Batch 2026-09-23: entry-straddling heads

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/x1_edgedisp.py` | 2026-09-23 | X1: THE DISPLAY HEAD, RETRAINED ON THE WINDOWS THAT STRADDLE THE TAPE ENTRY. | `runs/constrained/fh/x1_edgedisp/` |
| `pipeline/constrained/x2_edgepool.py` | 2026-09-23 | X2: THE POOL'S 0.5 s HEAD, RETRAINED ON THE ENTRY-STRADDLING WINDOWS. | `runs/constrained/fh/x2_edgepool_base/`, `runs/constrained/fh/x2_edgepool_edge100/`, `runs/constrained/fh/x2_edgepool_shipped/` |
| `pipeline/constrained/x3_edgeeval.py` | 2026-09-23 | X3: THE SHIP RULE, applied to item 3's arms. | `runs/constrained/fh/x3_edgeeval/` |

### Batch 2026-09-23c

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/constrained/y1_diag.py` | 2026-09-23 | ITEM 1: TWO DIAGNOSTICS. | `runs/constrained/fh/y1_diag/` |
| `pipeline/constrained/y1b_locksrc.py` | 2026-09-23 | ITEM 1, SECOND HALF: THE SAME TWO QUESTIONS, ASKED OF THE LOCK THAT IS ACTUALLY DRAWN. | `runs/constrained/fh/y1b_locksrc/` |
| `pipeline/constrained/y2_dial.py` | 2026-09-23 | ITEM 2: THE ESTIMATOR PRIZE. | `runs/constrained/fh/y2_dial/` |
| `pipeline/constrained/y3_switch.py` | 2026-09-23 | Y3: MID-WALK SWITCHING. | `runs/constrained/fh/y3_switch/` |
| `pipeline/constrained/y4b_lockstep1.py` | 2026-09-23 | Y4B: THE SECOND FIX FOR THE LOCK PHASE, PRICED. | `runs/constrained/fh/y4b_lockstep1/` |
| `pipeline/constrained/y5_heads.py` | 2026-09-23 | Y5: THE THREE 1 s HEADS, RETRAINED FROM SOURCE IN STRIDE-KEYED TREES. | `runs/constrained/fh/y5_heads/` |
| `pipeline/constrained/z3_eval.py` | 2026-09-23 | Z3 EVALUATION: arms A and B against the shared w = 0 baseline, by the pre-registered rule. | no results folder; see the report named in its docstring |

## 2. `pipeline/identify/`: 28 finished identification modules

None is in the DC2 identification chain (`capture_idpath`, `id28_dc2_score`, `id29_dc2_score`, `idgp_dc2_score`, `rehearsal_check` and their imports) or pinned by an identification freeze.

### Identification, first passes, 2026-09-18 to 19

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/identify/id10_voting.py` | 2026-09-19 | Line selection held out, then multi-pass voting on that line, with every control. | `runs/identify/id10_voting/` |
| `pipeline/identify/id1_foundations.py` | 2026-09-18 | PHASE C: identification foundations and the confound audit. | `runs/identify/id1_foundations/` |
| `pipeline/identify/id2_ladder.py` | 2026-09-18 | PHASE D: the geometry and gait feature ladder. | `runs/identify/id2_ladder/` |
| `pipeline/identify/id4_verification.py` | 2026-09-18 | PHASE F: verification, the realistic pipeline, and cohort subsets. | `runs/identify/id4_verification/` |
| `pipeline/identify/id5_report.py` | 2026-09-18 | PHASE H: verification, the reports, the freeze and the DC2 protocol sheet. | `runs/identify/id5_report/` |
| `pipeline/identify/id6_extras.py` | 2026-09-18 | E3 and PHASE G, the two arms the drop order puts last. | `runs/identify/id6_extras/` |
| `pipeline/identify/id7_livepipeline.py` | 2026-09-19 | Identification under the LIVE mode, on nine pairings instead of one. | `runs/identify/id7_livepipeline/` |
| `pipeline/identify/id8_perline.py` | 2026-09-19 | Does line-conditioned identification survive a real tracker? | `runs/identify/id8_perline/` |
| `pipeline/identify/id8a_lines.py` | 2026-09-19 | Dump the tracker's committed line per pass, so identification can read it WITHOUT the pool. | `runs/identify/id8a_lines/` |
| `pipeline/identify/id9_threshold.py` | 2026-09-19 | How accurate must the tracker's line be before line conditioning is worth anything? | `runs/identify/id9_threshold/` |

### Identification helpers

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/identify/audit_results.py` | 2026-09-23 | Structural audit of a stage's results.json. | no results folder; see the report named in its docstring |
| `pipeline/identify/figures.py` | 2026-09-23 | Thesis figures for the identification run. | `runs/identify/idgp/figures/` |
| `pipeline/identify/gait_features.py` | 2026-09-23 | Gait representations: ENV, SPEC, TEMPLATE and GAITPAR. | no results folder; see the report named in its docstring |

### Gait identification batch, 2026-09-23

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/identify/id11_audit.py` | 2026-09-23 | id11. Audit and reproduce. | `runs/identify/id11_audit/` |
| `pipeline/identify/id12_conditioning.py` | 2026-09-23 | id12. The conditioning chain and the signal-level evidence: M1 to M5, cumulative and LOO. | `runs/identify/id12_conditioning/` |
| `pipeline/identify/id13_representations.py` | 2026-09-23 | id13. Gait representations per pass: ENV, SPEC, TEMPLATE and GAITPAR, plus two gates. | `runs/identify/id13_representations/` |
| `pipeline/identify/id16_daybias.py` | 2026-09-23 | id16. Day bias, transductive session alignment, calibration and the voting curve. | `runs/identify/id16_daybias/` |
| `pipeline/identify/id17_learned.py` | 2026-09-23 | id17. Learned models: a prototypical MLP on features, and a small CNN on spectrograms. | `runs/identify/id17_learned/` |
| `pipeline/identify/id18_report.py` | 2026-09-23 | id18. The report section, the figures index, the freeze and the all_clean tests. | `runs/identify/id18_report/` |

### IDMAX, gait identification maximisation, 2026-09-23b

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/identify/id19_audit.py` | 2026-09-23 | id19_audit. Item 2: the three open issues, CSI-only cadence, and what each span contains. | `runs/identify/idmax/id19_audit/` |
| `pipeline/identify/id20_controls.py` | 2026-09-23 | id20_controls. Item 3: positive controls, MANDATORY before any maximisation. | `runs/identify/idmax/id20_controls/` |
| `pipeline/identify/id21_baselines.py` | 2026-09-23 | id21_baselines. Item 4: baselines re-established under section 6, in every scope of section 5. | `runs/identify/idmax/id21_baselines/` |
| `pipeline/identify/id22_sweep.py` | 2026-09-23 | id22_sweep. Item 5: the section 8 maximisation sweep, nested throughout. | `runs/identify/idmax/id22_sweep/` |
| `pipeline/identify/id23_path.py` | 2026-09-23 | id23_path. Item 6: identification on ONE path, as a deployment with one entry corridor would. | `runs/identify/idmax/id23_path/` |
| `pipeline/identify/id24_voting.py` | 2026-09-23 | id24_voting. Item 7: multi-pass voting within the test day, and day alignment. | `runs/identify/idmax/id24_voting/` |
| `pipeline/identify/id26_final.py` | 2026-09-23 | id26_final. Item 9: the nested winner everywhere, the speed diagnostic, the post-hoc ceiling, and the DC2 pre-registered configuration. | `runs/identify/idmax/id26_final/` |
| `pipeline/identify/id27_report.py` | 2026-09-23 | id27_report. Item 10, the generated part: seven figures, the headline tables, and the freeze. | `runs/identify/idmax/id27_report/` |

### IDGP, integrated gait with pace, 2026-09-23f

| file | last changed | what it did | where its results live |
|---|---|---|---|
| `pipeline/identify/idgp_report.py` | 2026-09-23 | idgp_report. IDGP item 8: the five figures (vector PDF and PNG) for the 2026-09-23f section. | no results folder; see the report named in its docstring |

## 3. `scripts/`: 32 batch runners, heartbeats, watchdogs and chains

Every one served a batch that has closed. The kept scripts are `render_demo.sh`, `live_rig_run.sh` (pinned) and `track.py`.

### Scripts

| file | last changed | what it did |
|---|---|---|
| `scripts/chain_after_render.sh` | 2026-09-20 | Waited for f3_render to finish, then ran r5_timeline and f4_verify, holding the freeze for review (2026-09-20). |
| `scripts/chain_dot_close.sh` | 2026-09-19 | Waited for f3_render to finish, then ran f4_verify and g5_freeze (2026-09-19). |
| `scripts/chain_pool_close.sh` | 2026-09-19 | Close out the multi-head pool batch: wait for the render, verify, freeze. |
| `scripts/chain_refreeze.sh` | 2026-09-19 | Ran f4_verify and g5_freeze again to re-take the freeze (2026-09-19). |
| `scripts/chain_render_fix.sh` | 2026-09-20 | The render-fix chain, 2026-09-20. |
| `scripts/ends_summary.sh` | 2026-09-18 | The trap's safety net: a SUMMARY always exists even if the chain died. |
| `scripts/heartbeat.sh` | 2026-09-17 | The 15-minute check-in, running as its OWN process, separate from the chain. |
| `scripts/heartbeat_fh.sh` | 2026-09-19 | The 15-minute check-in for the F,H and live-render batch, 2026-09-19. |
| `scripts/heartbeat_night.sh` | 2026-09-19 | The 15-minute check-in for the overnight semi-bounded batch, 2026-09-19. |
| `scripts/heartbeat_render.sh` | 2026-09-23 | Check-in for the render-fix batch of 2026-09-20. |
| `scripts/heartbeat_semibounded.sh` | 2026-09-18 | The 15-minute check-in for the SEMI-BOUNDED AND STRIDE batch of 2026-09-18. |
| `scripts/heartbeat_window.sh` | 2026-09-18 | The 15-minute check-in for the WINDOW PROBE batch of 2026-09-18. |
| `scripts/idmax_chain.sh` | 2026-09-23 | IDMAX chain (2026-09-23b): items 3 to 10 as one runner, so no stage waits for a Claude turn. |
| `scripts/idmax_featbank.sh` | 2026-09-23 | IDMAX feature-bank runner (2026-09-23b). |
| `scripts/run_ends.sh` | 2026-09-18 | THE END-WINDOWS AND SEMI-BOUNDED CHAIN, brief of 2026-09-18. |
| `scripts/run_fh.sh` | 2026-09-19 | The overnight stage runner. |
| `scripts/run_half_block.sh` | 2026-09-18 | Phase 3 at 1 s re-run under the corrected pass matching and ship rule, then the whole 0.5 s arm. |
| `scripts/run_identify_batch.sh` | 2026-09-23 | The identification batch, chained end to end. |
| `scripts/run_improvements.sh` | 2026-09-19 | The model improvement queue, per reports/MODEL_IMPROVEMENTS_QUEUE.md. |
| `scripts/run_night.sh` | 2026-09-19 | The overnight stage runner. |
| `scripts/run_phase4.sh` | 2026-09-18 | Phase 4 at both strides, serial, so the stride comparison is like for like. |
| `scripts/run_phase56.sh` | 2026-09-18 | The tail of the batch, queued so nothing waits on a person. |
| `scripts/run_semibounded_train.sh` | 2026-09-18 | PHASE 0.3: train the eleven missing 0.5 s pairings, ONE PROCESS PER PAIRING, strictly serial. |
| `scripts/run_window_probe.sh` | 2026-09-18 | THE STAGE RUNNER for the window probe. |
| `scripts/watchdog.sh` | 2026-09-18 | THE WATCHDOG. Keeps life support and the stage runner alive while the operator is away. |
| `scripts/watchdog_fh.sh` | 2026-09-19 | Keeps caffeinate, the heartbeat and the runner alive all night. |
| `scripts/watchdog_idgp.sh` | 2026-09-23 | IDGP watchdog (2026-09-23b). |
| `scripts/watchdog_idmax.sh` | 2026-09-23 | IDMAX watchdog (2026-09-23b). |
| `scripts/watchdog_night.sh` | 2026-09-19 | Keeps caffeinate, the heartbeat and the runner alive all night. |
| `scripts/watchdog_render.sh` | 2026-09-20 | Keeps caffeinate and the heartbeat alive for the render-fix batch. |
| `scripts/write_fh_summary.sh` | 2026-09-19 | The trap: SUMMARY_FH_LIVE.txt is always written, even on failure, and never overwrites an earlier |
| `scripts/write_night_summary.sh` | 2026-09-19 | The trap: SUMMARY_NIGHT.txt is always written, even on failure, and never overwrites an earlier |

## 4. `tools/`: 12 pre-pivot analysis tools (2026-09-08 to 12)

The kept tools are `__init__.py`, `calibrate_gate.py` (imported by the live rig and the replay), `make_layout_image.py` and `make_paths_image.py` (they draw `Layout.png` and `Paths.png`).

### Tools

| file | last changed | what it did |
|---|---|---|
| `tools/apply_gate.py` | 2026-09-10 | Fill the gate label of every stored window, and write the per-session gate manifest. |
| `tools/audit_baseline.py` | 2026-09-10 | Empty-room checks on every baseline: per-subcarrier variance and the spectrum to 75 Hz. |
| `tools/audit_capture.py` | 2026-09-10 | Audit every capture against the filed goalposts, one row per file. |
| `tools/check_float16.py` | 2026-09-10 | Is float16 good enough for the stored windows? |
| `tools/clothing_confound.py` | 2026-09-12 | Cross-day identification accuracy split by whether the participant changed clothes. |
| `tools/group_size_report.py` | 2026-09-12 | Group-size curve over ten seeds: accuracy against the per-size chance line and speed-only. |
| `tools/link_curve.py` | 2026-09-12 | Does a third receiver help? |
| `tools/overnight_report.py` | 2026-09-12 | Assemble the overnight report: what failed, what is uncertain, what passed. |
| `tools/realtime_demo.py` | 2026-09-12 | End to end: the trained source-only model driving the streaming engine on a session 03 walk. |
| `tools/session03_checks.py` | 2026-09-12 | Step E: the three checks specific to the held-out session, run with the operator present. |
| `tools/tenseed_report.py` | 2026-09-12 | The ten-seed dev comparison: mean, standard deviation and range, both directions, both arms. |
| `tools/verify_paths.py` | 2026-09-09 | Check every walking path against its own label, from the geometry alone. |

## 5. `tests/`: 3 test files removed with the code they tested

### Tests

| file | last changed | what it did |
|---|---|---|
| `tests/test_bounded_demo.py` | 2026-09-17 | The boundaries-given demonstration must be the SAME computation as the figure it illustrates. |
| `tests/test_gait_features.py` | 2026-09-23 | Cadence is resolved WITHOUT speed, and it is right for both symmetric and asymmetric gaits. |
| `tests/test_stride_isolation_rb2d.py` | 2026-09-18 | The two rb2d_retrain tests, retired 2026-09-18 with the module they test. |

- `tests/test_report_consistency.py`: removed `test_calibration_table_shows_the_floor_and_the_centre_baseline`, `test_calibration_verdict_matches_the_measured_rows` (both imported `rb9_report`) and `test_audit_counts_only_the_shipped_decoders_committed_tracks` (imported `rb8_verify`). The other 19 tests stay.
- `tests/test_conditioning.py`: removed `test_the_auc_saturates_and_the_separation_does_not`, which imported `id12_conditioning`.
- `tests/test_identification_clean.py`: `id11_audit`, `id12_conditioning`, `id13_representations` and `gait_features` left the `NEW_STAGES` list; `test_no_gait_feature_function_accepts_a_speed` (which imported `gait_features`) and `test_free_mode_recordings_are_excluded_where_passes_are_gathered` (which checked only `id12_conditioning` and `id13_representations`) were removed. Of the kept identification modules, the DEMO/free-mode exclusion now lives in `pipeline/identify/idmax_common.py`.
- `pipeline/identify/idmax_checkin.py` was on the brief's delete list but STAYS: the pinned `idgp_checkin.py` imports it.
- Registries of stage modules, read by path, lost the entries for removed modules and keep guarding the rest: `test_cross_pairing_key.py` `CLASSIFIED` (23 entries), `test_pass_pairing_key.py` `PER_RECORDING` (18) and `CROSS_ARM` (both entries, now an empty set), `test_no_pacer.py` `CHECKERS` (both entries), `test_entrypoint_guard_form.py` `ENTRY_POINT_ONLY` (5 of 6).
- `test_pass_pairing_key.py::test_sb3_pairs_on_the_stem_bearing_key_and_asserts_uniqueness` was removed (it read `sb3_exitsweep.py`). `test_cross_pairing_key.py`'s two-stage tag test now checks `s2_display` alone (the other was `n1_diag`) and is renamed `test_the_stage_that_spans_pairings_carries_the_tag`.
- `test_lock_is_causal.py` checks `t6_lockdiag`, `t7_lockarms` and `t9_lengthnorm` (it also read `y1_diag` and `y2_dial`). `test_reported_config_is_applied.py` checks `s2_display` (it also read `s2b_decision_causality`).
- `test_freeze_quotes_the_current_figure.py::test_the_freeze_stage_quotes_headline_semibounded_when_it_has_one` was removed (it read `g5_freeze.py`); the same rule is still enforced on every freeze payload by the parametrised test.
- `test_asserted_not_measured.py` no longer checks `rc8_demo`'s retired renders, whose retirement manifest lived in `testing/demo_retired/`; it still checks the shipped `f3_render` videos.
- `test_report_consistency.py::test_readme_quotes_the_delivered_system_not_the_weakest_arm` now checks the README against freeze 23h's headline instead of the 2026-09-17 `stage5_live` figures.

## 6. `testing/`: the pre-pivot archive, removed whole

Everything the project did before it committed to constrained tracking on 16 September 2026, and the modules the 2026-09-18 cleanup retired. Every tracked file is at the tag; `testing/from_data/` was never tracked and holds derived caches only. Restore the whole tree with `git checkout pre-cleanup -- testing`.

| folder | files | what it held |
|---|---|---|
| `testing/pipeline/` | 122 | the pre-pivot pipeline modules (identification branch, free-form tracking, v1 and v2 stages) |
| `testing/pipeline_retired/` | 22 | the 22 constrained stage modules the 2026-09-18 cleanup retired (rb2_decoder, rb5_calibrate, rc7_static and others) |
| `testing/runs/` | 3425 | every pre-pivot batch's run folders, including the pre-registered runs/final/ and runs/FROZEN_BLOCK.json |
| `testing/reports/` | 121 | every pre-pivot report, including tracking_method_ledger.md, METHODS_TRIED_2026-09-14.md and MODEL_STATE_2026-09-14.md |
| `testing/scratch/` | 72 | scratch scripts and notes from 2026-09-10 to 16 |
| `testing/demo_retired/` | 27 | superseded demonstration renders |
| `testing/failed_models/` | 20 | methods scored against a matched control and rejected |
| `testing/figs_retired/` | 8 | eight superseded confusion matrices |
| `testing/tests/` | 8 | pre-pivot tests, including test_id_branch.py |
| `testing/briefs/` | 6 | pre-pivot briefs |
| `testing/retired_tests_2026-09-20/` | 2 | render-test helpers retired on 2026-09-20 |
| `testing/scripts/` | 1 | one pre-pivot runner |
| `testing/README.md, testing/SEMIBOUNDED_STATE_pre_pool_2026-09-19.md` | 2 | the archive's index, and the semi-bounded state page before the multi-head pool |
| `testing/from_data/` | 138 (never tracked) | derived .npz and .npy from the 2026-09-12 to 14 post-mortem and push batches; moved to the Trash in step 1 |

## 7. Derived trees removed in step 1, and how to rebuild them

These were never code; they are listed because their rebuild commands belong with the code that uses them. Step 1 moved them to `~/.Trash/csi-thesis-cleanup-2026-09-24/` (the permission layer refused `rm -rf`), so until the Trash is emptied they can also be moved back.

| tree | size | rebuild |
|---|---|---|
| `runs/constrained/windows_half/` | 6.3 GB | `python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_half --stride 0.5` (about 8.5 min); the grid lattice's 0.5 s windows, needed only with `TDR_LATTICE=grid` |
| `runs/artefacts_{half,fh1s,g1s1,g1s2,g1g100s0,dispend}/` | 0.9 GB | `git checkout pre-cleanup -- runs/artefacts_half runs/artefacts_fh1s runs/artefacts_g1s1 runs/artefacts_g1s2 runs/artefacts_g1g100s0 runs/artefacts_dispend`; the grid lattice's trees. Their gitignored posteriors re-infer from the restored models over the rebuilt windows (six heads in about 19 min) |
| `runs/constrained/windows_w1/, windows_w05/` | 4.8 GB | window-probe arms that did not ship; regenerate with `pipeline.constrained.wp_arm` restored from the tag. Also removed from git history in step 2 |
| `runs/artefacts/features/` | 6.3 GB | a byte-identical copy (sha256, 18 of 18) is `runs/artefacts_s1.0_retrain_shared/features/`, kept until after DC2; otherwise about 3 min through `pipeline.constrained.recordings` |
| `runs/artefacts_s0.5_retrain_{shared,s0,s1,s2}/, runs/artefacts_s1.0_retrain_{s0,s1,s2}/` | 12.8 GB | batch 23c item 5, heads bit-identical to the shipped ones; result in `runs/constrained/fh/y5_heads/`; rerun `y5_heads` restored from the tag. Deleted outright in step 0.4 |
| `runs/constrained/dc2_room_B_standin{,_decoys}_s0.5_pressalign/` | 11.2 GB | `python3 -m pipeline.constrained.dc2_pipeline --room room_B --stand-in` (about 6 min; add `--decoy-receivers` for the decoy variant). Deleted outright in step 0.4 |
| `runs/constrained/demo_archive/` | 63 MB | superseded renders. Deleted outright in step 0.4 |
| `data/features/` | 2.3 GB | old identification band caches and a tracking cache (2026-09-10 to 15); only reader was `id11_audit` |
| `data/retired/azrah_zaid/derived/` | 3.0 GB | regenerable caches of the two retired participants; `restore.sh` will now restore the captures only |

