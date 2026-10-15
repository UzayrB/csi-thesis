# RECORD_TRACKING: the tracking record, consolidated

Written 2026-09-24 08:15 SAST by the cleanup session (`cleanup_prompt_2026-09-24`). This record gathers the thesis-record tracking reports, the ones written between batches that no code reads, one section per source document in date order. Every section is the source's text **verbatim**; the only change is that its headings are demoted two levels so they nest under the section heading. Where a later document overrides a figure, a one-line note says so at the top of the section; no old figure is dropped. Every source is also in git at the tag `pre-cleanup` under its original path.

**Originals.** Until 2026-09-24 the originals of part 1 were kept beside this record because other documents cited them. On 2026-09-24 all history moved to `reports/attempts/`, and each original was removed only after its SHA-256 was checked against the one recorded in its section, so every section below is the complete, exact text. Every original is also in git at the tag `pre-cleanup`.

## Index

### Part 1, written 2026-09-24 08:15

| source | date | one-line summary | original | at the tag |
|---|---|---|---|---|
| [RUNUP_FINDINGS_2026-09-20.md](#runup-findings-2026-09-20md) | 2026-09-20 | The run-up: 80.8 % of pre-press windows are walking; the direction of approach reads at 55.2 % [52.4, 57.6] against 50 % chance. | combined here | `pre-cleanup:reports/RUNUP_FINDINGS_2026-09-20.md` |
| [PARTS_1_TO_3_REPORT_2026-09-20.md](#parts-1-to-3-report-2026-09-20md) | 2026-09-20 | Parts 1 to 3 (D1 to D5 diagnostics, arms A1 to A3, the display), frozen at 18w; includes the 2026-09-21 chance-level correction. | combined here | `pre-cleanup:reports/PARTS_1_TO_3_REPORT_2026-09-20.md` |
| [PREPRESS_REGION_REPORT_2026-09-21.md](#prepress-region-report-2026-09-21md) | 2026-09-21 | The start region from the pre-press windows, a measured negative: the best buildable reader reaches 40.0 % against a 20.0 % baseline and a 74.2 % break-even. | combined here | `pre-cleanup:reports/PREPRESS_REGION_REPORT_2026-09-21.md` |
| [PART1_REPORT_2026-09-22.md](#part1-report-2026-09-22md) | 2026-09-22 | Part 1, fix the render at its source: nothing shipped in the decision; the dwell cut and rules V1 to V4 entered the render (freeze 22b). | combined here | `pre-cleanup:reports/PART1_REPORT_2026-09-22.md` |
| [PART2_REPORT_2026-09-22.md](#part2-report-2026-09-22md) | 2026-09-22 | Part 2, the pre-press region reader version 2: no ship, and one active harm. | combined here | `pre-cleanup:reports/PART2_REPORT_2026-09-22.md` |
| [ITEMS_ABC_REPORT_2026-09-22.md](#items-abc-report-2026-09-22md) | 2026-09-22, evening | Items A to C: the DC2 dry run, real-time operation (20 of 20 decisions identical to offline) and the A_fwd diagnostic. | combined here | `pre-cleanup:reports/ITEMS_ABC_REPORT_2026-09-22.md` |
| [RENDER_DOTPHASE_2026-09-22.md](#render-dotphase-2026-09-22md) | 2026-09-22, late | The drawn dot: why it leads the walker and starts out, measured with a sign. | combined here | `pre-cleanup:reports/RENDER_DOTPHASE_2026-09-22.md` |
| [ACCURACY_STATE_2026-09-22.md](#accuracy-state-2026-09-22md) | 2026-09-22 | Where the model sits: accuracy, and whether it is CSI, every figure read back from the frozen runs (freeze 22b). | combined here | `pre-cleanup:reports/ACCURACY_STATE_2026-09-22.md` |
| [BATCH_2026-09-23_REPORT.md](#batch-2026-09-23-reportmd) | 2026-09-23 | Batch 2026-09-23: the edge, the display head and the pool head; on-screen tracking 40.00 to 41.66 %. | combined here | `pre-cleanup:reports/BATCH_2026-09-23_REPORT.md` |
| [DC2_REPORT_room_B_STANDIN_DECOYS.md](#dc2-report-room-b-standin-decoysmd) | 2026-09-23 17:23 | DC2 stand-in with decoy receivers (batch 23e item 6): 72 of 72 decisions equal to the shipped path. A plumbing check, not results. | combined here | `pre-cleanup:reports/DC2_REPORT_room_B_STANDIN_DECOYS.md` |
| [DC2_REPORT_room_B_STANDIN.md](#dc2-report-room-b-standinmd) | 2026-09-23 22:39 | DC2 stand-in on the frozen code (freeze 23h): 72 of 72 decisions equal to the shipped path. A plumbing check, not results. | combined here | `pre-cleanup:reports/DC2_REPORT_room_B_STANDIN.md` |

### Part 2, added 2026-09-24

| source | date | one-line summary | original |
|---|---|---|---|
| [FIGURES.md](#figuresmd) | 2026-09-18 | The index of the canonical figures after the first cleanup, and why none was renamed. | combined here; at the tag `pre-cleanup:reports/FIGURES.md` |
| [ETA.txt](#etatxt) | 2026-09-19 | The overnight semi-bounded batch's ETA file at completion. | combined here; at the tag `pre-cleanup:reports/ETA.txt` |
| [BRIEF_motion_and_lock_2026-09-20.md](#brief-motion-and-lock-2026-09-20md) | 2026-09-20 | The operator's brief for the motion model and park-watch-lock batch. | combined here; at the tag `pre-cleanup:reports/BRIEF_motion_and_lock_2026-09-20.md` |
| [BRIEF_render_fix_2026-09-20.md](#brief-render-fix-2026-09-20md) | 2026-09-20 | The operator's brief for the render fix (the red dot tracking the green one). | combined here; at the tag `pre-cleanup:reports/BRIEF_render_fix_2026-09-20.md` |
| [HANDOFF_2026-09-21.md](#handoff-2026-09-21md) | 2026-09-21 | The handoff after the display fixes and the delayed-playback demonstration. | combined here; at the tag `pre-cleanup:reports/HANDOFF_2026-09-21.md` |
| [HANDOFF_2026-09-22.md](#handoff-2026-09-22md) | 2026-09-22 | The handoff with the open items of 2026-09-22 (the render batch and the pre-press reader). | combined here; at the tag `pre-cleanup:reports/HANDOFF_2026-09-22.md` |
| [BATCH_2026-09-23c_REPORT.md](#batch-2026-09-23c-reportmd) | 2026-09-23 | Batch 23c: the causal correction, the press-aligned lattice, link fusion, switching, the 1 s retrain. | combined here; at the tag `pre-cleanup:reports/BATCH_2026-09-23c_REPORT.md` |
| [BATCH_2026-09-23d_REPORT.md](#batch-2026-09-23d-reportmd) | 2026-09-23 | Batch 23d: the amended (f), the ONE lattice, a_veto_1.0, the headline at 73.33. | combined here; at the tag `pre-cleanup:reports/BATCH_2026-09-23d_REPORT.md` |
| [BATCH_2026-09-23e_REPORT.md](#batch-2026-09-23e-reportmd) | 2026-09-23 | Batch 23e: switching as a display decision, the end text, fusion for DC2, the fifth receiver. | combined here; at the tag `pre-cleanup:reports/BATCH_2026-09-23e_REPORT.md` |
| [BATCH_2026-09-23f_REPORT.md](#batch-2026-09-23f-reportmd) | 2026-09-23 | Batch 23f: three switching arms, the winner rendered, the investigation. | combined here; at the tag `pre-cleanup:reports/BATCH_2026-09-23f_REPORT.md` |

### Kept in `reports/`, not copied here

These are evidence for the current model and stay in `reports/` as they are; this record only points at them.

| file | what it holds |
|---|---|
| `reports/BRIEF_render_and_prepress_2026-09-22.md` | the operator's instructions 1 to 8, verbatim, including the post hoc amendment of condition (f) |
| `reports/BATCH_2026-09-23g_REPORT.md` | batch 23g: the ablation, the scorer lock refused, the DC2 model freeze |
| `reports/CORRECTION_causal_lock_2026-09-23.md` | every 2 s lock figure, restated at the causal horizon |
| `reports/CORRECTION_drawn_lock_2026-09-23.md` | the quoted lock was not the drawn lock |
| `reports/INVESTIGATION_switching_2026-09-23f.md` | how switching works and what it actually does |
| `reports/SCORERLOCK_AND_ABLATION_2026-09-23.md` | the ablation and the scorer lock |

---

## RUNUP_FINDINGS_2026-09-20.md

**Source:** `reports/RUNUP_FINDINGS_2026-09-20.md`, 2026-09-20. **SHA-256:** `bcdcb2123b1c2fe8c38916a6255be176c9e8f280525ae42081bf1c7df27963cc`. **Original combined here** on 2026-09-24.

### The run-up: what is in the two seconds before the press

Read only. Nothing retrained, no new labels, no change to the window or the stride. Semi-bounded is
still told only the start press; what this batch asks is whether it may also look BACKWARDS from
that press at signal which already existed in windows that had already finished recording.

**The pre-press windows are legal.** A window whose END is at or before the first press consists
only of samples recorded before the press. This does not reopen the causality leak found earlier.

#### Item 1: the operator's account is confirmed

| | |
|---|---|
| pre-press walking fraction, 360 passes | mean **80.8 %**, median **100 %** |
| during the labelled walk | 99.1 % |
| standing still on a grid point | **11.3 %** |
| passes more than half walking | 279 of 360 |
| passes entirely walking | **247 of 360** |

The two seconds before the press are walking, not standing and not a pause. The still reference is
the grid dwells, not the idle windows between passes: those are mostly TRANSIT, when the person
genuinely is walking to the next start, and the gate's own documentation says it calls 53 percent
of transit windows walking for that reason.

#### Item 1: where the run-up physically lies

The nodes sit 0.5 m outside each edge, at the edge midpoints: TX (2.5, -0.5), RX1 (2.5, 5.5),
RX2 (-0.5, 2.5), RX3 (5.5, 2.5). Every line's start is ON the grid boundary, so **every run-up zone
is entirely outside the 5 by 5 taped grid** and has no cell of its own; the nearest cell is the
start cell.

| line | start | run-up runs towards | usable | blocked by |
|---|---|---|---|---|
| A_fwd | (2.5, 0.0) | (2.5, -0.25) | **0.25 m** | **TX** |
| A_rev | (2.5, 5.0) | (2.5, 5.20) | **0.20 m** | **RX1** |
| B_fwd | (0.0, 2.5) | (-0.25, 2.5) | **0.25 m** | **RX2** |
| B_rev | (5.0, 2.5) | (5.20, 2.5) | **0.20 m** | **RX3** |
| C_fwd | (0.0, 0.0) | (-1.06, -1.06) | 1.50 m | clear |
| C_rev | (5.0, 5.0) | (6.06, 6.06) | 1.50 m | clear |
| D_fwd | (0.0, 5.0) | (-1.06, 6.06) | 1.50 m | clear |
| D_rev | (5.0, 0.0) | (6.06, -1.06) | 1.50 m | clear |
| E_col1 | (0.5, 0.0) | (0.5, -1.5) | 1.50 m | clear |
| E_col5 | (4.5, 0.0) | (4.5, -1.5) | 1.50 m | clear |
| E_row1 | (0.0, 0.5) | (-1.5, 0.5) | 1.50 m | clear |
| E_row5 | (0.0, 4.5) | (-1.5, 4.5) | 1.50 m | clear |

**Four of the twelve lines have a node directly behind their start** and effectively no run-up at
all: a person cannot walk through the transmitter. The other eight have the full 1.5 m. Any
extended-chain arm must therefore extend eight chains and barely extend four, which is a constraint
the brief's flat "up to 1.5 m" did not anticipate.

#### Item 2: the pre-press windows carry DIRECTION, not LINE

Frozen five-head pool, no retraining, nine cross-day pairings, windows ending at the press and at
0.5, 1.0, 1.5 and 2.0 s before it.

| quantity | median | interval | chance | above chance? |
|---|---|---|---|---|
| **line** | 9.2 % | [7.7, 12.3] | 8.3 % | **no** |
| **direction** | **55.2 %** | **[52.4, 57.6]** | 50 % | **yes** |
| corner | 9.2 % | [7.7, 12.3] | 8.3 % | no |

| substitution, another participant's CSI over the same windows | |
|---|---|
| line answer moves | 81.7 % |
| direction answer moves | 41.4 % |
| corner answer moves | 81.7 % |

**Which of the twelve lines cannot be read from the run-up at all.** That is not surprising once
the geometry is in front of you: the run-up happens outside the taped grid, where the encoder was
never trained, and four lines have only 20 to 25 cm of it.

**The direction of approach can be read, modestly but outside the interval**: 55.2 percent against
50, interval [52.4, 57.6]. That is exactly the quantity the operator predicted would matter, and it
is exactly the error the shipped decoder makes at twice its chance share: reversed-direction
confusions are 18 percent of all errors against a 9 percent chance share.

**On the substitution figure for direction.** 41.4 percent sits below the 50 percent bar this
project uses elsewhere, and that bar deserves care here because it was set for a CONTINUOUS
quantity, the end time, where a clock scores 0. For a BINARY direction decision the ceiling is not
100: substituting another participant's CSI only changes the answer when their pass ran the other
way, which is about half the time. So a fully signal-driven direction decision would score about
50 and a decision ignoring the radio would score 0. **41.4 is near the ceiling, not below a floor.**
That is an argument about what the number means, made before acting on it, and the operator should
be the one to accept or reject it.

#### The consequence for item 3

The two arms were both framed as LINE priors. Line is at chance, so neither can be justified as a
line prior. Both remain justified as DIRECTION mechanisms, because both operate over the twelve
chains and A_fwd and A_rev differ only in direction: a prior that is uninformative about which tape
but informative about which way still pushes weight off the reversed chain.

So item 3 is worth running, with its purpose restated: **not to identify the line from the run-up,
which the data says is impossible, but to stop the decoder choosing the reversed chain.**

#### Item 4: the next step, recorded and NOT run

If the information is present but the frozen heads read it weakly, the next step is retraining with
labels on the run-up windows. The label rule, written down now so it is not reinvented later:

> the start point, minus that pass's own anchor-measured speed times the time before the press,
> along the line's direction, bounded at the run-up distance in the table above.

This is the **same constant-pace interpolation every walking label already uses**, extended one
segment before the first anchor rather than a new kind of label.

**The precedent that must be checked against.** The end-window retrain of 18 September labelled the
equivalent windows at the other end with the start coordinate ITSELF rather than an interpolated
position. It moved the core and did not ship. The difference is that a constant-pace extrapolation
puts the person where they actually were, while a fixed coordinate puts a moving person at a
standstill; but that is an argument, and the 18 September result is the evidence that this class of
relabelling can make things worse.

Per-line run-up bounds from the table are not optional in that rule: labelling A_fwd's run-up out
to 1.5 m would place the walker 1.25 m beyond the transmitter, inside a wall.

---

## PARTS_1_TO_3_REPORT_2026-09-20.md

**Source:** `reports/PARTS_1_TO_3_REPORT_2026-09-20.md`, 2026-09-20. **SHA-256:** `78d4f17739635efeab5eb72552d718491593952fd87152821f578b1da84a27e6`. **Original combined here** on 2026-09-24.

> **Superseded:** The semi-bounded figures here were measured at freeze 18w. Freeze 18z (the causal exit, later the same evening) set the headline at 62.50 percent, and the post-amendment headline is 73.33 percent from freeze 23d onward (`runs/TRACKING_FROZEN_2026-09-23h.json`, `headline_semibounded`).

### Parts 1 to 3: diagnostics, arms and display. 2026-09-20

The consolidated report for the D1 to D5, A1 to A3 and Part 3 batch. Frozen at
`runs/TRACKING_FROZEN_2026-09-18w.json`. Pre-registrations were written before any arm ran:
`runs/PREREGISTRATION_part2_arms_2026-09-20.json`.

#### Where each item lives

| item | stage | findings | full numbers |
|---|---|---|---|
| D1 two accuracies, reconciliation | `q1_diag` | `reports/FINDINGS_stageq1.txt` | `runs/constrained/fh/q1_diag/results.json` key `D1` |
| D2 start versus commitment | `q1_diag` | same | same, key `D2` |
| D3 TX versus RX1 | `q1_diag` | same | same, key `D3` |
| D4 direction by segment | `q1_diag` | same | same, key `D4` |
| D5 line order | run inline, read only | in this document | `data/room_A/session_*/‹stem›.gt.json` |
| A1 start-region entry | `q4_arms` | `reports/FINDINGS_stageq4.txt` | `runs/constrained/fh/q4_arms/results.json` |
| A2 start term on the chain totals | `q4_arms` | same | same |
| A3 start-region classifier | `q3_startclf` | `reports/FINDINGS_stageq3.txt` | `runs/constrained/fh/q3_startclf/results.json` |
| extra 1, the 3 m/s ceiling | `q2_extras` | `reports/FINDINGS_stageq2.txt` | `runs/constrained/fh/q2_extras/results.json` key `extra_1` |
| extra 2, along-line progress | `q2_extras` | same | same, key `extra_2` |
| Part 3, the display | `f3_render` | `reports/FINDINGS_stagef3.txt` | `runs/constrained/fh/f3_render/results.json` |
| geometry audit | read only | `reports/GEOMETRY_AUDIT_2026-09-20.md` | `python3 -m pipeline.constrained.paths` |
| the run-up batch that preceded this | `p1`, `p2`, `p3` | `FINDINGS_stagep{1,2,3}.txt` | `runs/constrained/fh/p*/results.json` |
| the causality batch that preceded it | `c1`, `c2` | `FINDINGS_stagec{1,2}.txt` | `runs/constrained/fh/c*/results.json` |

---

### PART 1: DIAGNOSTICS

#### D1 The two accuracies, kept apart, and the three figures reconciled

**Decoded accuracy** compares the dot with where the person was at that window's own centre.
**Display offset** compares it with where the person is at the frame time, and carries the whole
causal lag. They are different quantities and are never added.

| figure | what | mode | population |
|---|---|---|---|
| 33.3 percent | locked DISPLAY line | semi-bounded | nine pairings |
| 63.3 percent | locked DISPLAY line | semi-bounded | demonstration pairing |
| 78.3 percent | committed line at the END PRESS | **bounded** | demonstration pairing |
| 62.5 percent | committed at its own end | semi-bounded | demonstration pairing |
| **50.0 percent** | committed at its own end | semi-bounded | **nine pairings** |

Those figures are all at the 3 m/s ceiling. Extra 1 below shows what the ceiling costs.

Decoded error when right: **1.195 m** on the demonstration pairing, **1.296 m** over nine.

#### D2 Start region against committed line

The start region is read from the last window to have ENDED before the first press, over the eight
regions: four edge midpoints and four corners.

| | |
|---|---|
| passes | 1080 |
| start region right | **18.5 percent**, against a 12.5 percent chance |
| of the 200 right, line still wrong | **110** |

| how they disagree | count | share |
|---|---|---|
| a line that does not start there | **89** | 81 percent |
| entering another line mid-chain | 11 | 10 percent |
| the same line reversed | 10 | 9 percent |

#### D3 TX versus RX1, hypothesis tested and confirmed

Reversed errors by line pair:

| pair | reversed | interval |
|---|---|---|
| **A** | **12.0 percent** | [7.9, 16.7] |
| B | 2.3 | [0.5, 4.6] |
| C | 2.3 | [0.5, 4.6] |
| D | 1.4 | [0.0, 3.2] |

Per link, can the first windows separate a start near TX from a start near RX1? 50 percent is
chance.

| link | line A | line B |
|---|---|---|
| **RX1** | **50.5 percent, chance** | 60.6 |
| RX2 | 81.0 | 76.9 |
| RX3 | 56.5 | 78.2 |

**The hypothesis holds exactly.** TX sits at (2.5, -0.5) and RX1 at (2.5, 5.5), diametrically
opposite through the room centre, so the TX to walker to RX1 path length is **6.00 m from either
end of line A** while RX2 and RX3 differ by 5.00 m. That link is blind to which half of any
centre-crossing line the walker is on, which is why it is weakest on line B as well, and why line A
carries five times the reversed errors of the other pairs.

#### D4 Direction by segment. THE HYPOTHESIS IS REFUTED.

Given the true tape, forward against reverse. Chance is 50 percent.

| from | accuracy |
|---|---|
| first window after the press | **43.8 percent** |
| first two | 44.3 |
| first three | 45.2 |
| first four | 45.2 |
| **the middle windows only** | **75.3 percent** |
| the full interval | 70.3 |

**The start does not carry direction. The middle does.** The brief's hypothesis was the opposite,
and this is what skipped A2 in its original form.

#### D5 Line order, read only from the labels

Shuffled per participant per session, **different across all three days for every participant** and
different across the six participants within every session. Pass index predicts the line across
days on **0 of 120 positions**, against a three-way chance of 1 in 144.

**The recording-block confound is cleared**, which is what permitted A3.

---

### PART 2: ARMS

Pre-registered before running. The 3 m/s ceiling is OFF for the decision throughout, following
extra 1.

#### A3 The start-region classifier. RUNS FIRST, and PASSES.

> ### CORRECTION, 2026-09-21. THE CHANCE LEVEL BELOW IS UNDERSTATED AND THE CORNERS GROUP DOES NOT CLEAR ITS BAR.
>
> **This section is restated, not amended.** Everything below the correction is left exactly as it
> was written on 2026-09-20, so the record shows what was claimed and on what basis.
>
> `q3_startclf` reports `chance_pct: 12.5`, which is uniform over eight regions. **The classes are
> not uniform.** Measured over all 360 passes: SW 72, NW 54, SE 54, and 36 each for NE, S_mid,
> N_mid, E_mid and W_mid. The honest baseline is the best constant predictor, and it differs per
> group because the groups are subsets of passes:
>
> | task | best constant predictor | correct baseline | the bar, twice baseline | measured | verdict |
> |---|---|---|---|---|---|
> | overall, 8 regions | always SW, 72 of 360 | **20.0 percent** | **40.0** | 46.7 | clears, on the point estimate |
> | edge midpoints, 144 passes | any edge region, 36 of 144 | **25.0 percent** | **50.0** | 61.8, lower bound 53.5 | **clears** |
> | corners, 216 passes | always SW, 72 of 216 | **33.3 percent** | **66.7** | 36.6, interval [30.1, 42.6] | **DOES NOT CLEAR** |
>
> **What this changes.**
>
> 1. The bar as written was "twice the 12.5 percent chance, so 25 percent". Against the correct
>    overall baseline of 20.0 percent it should have been **40 percent**. The bar was set against
>    an understated chance level.
> 2. **The corners group fails the corrected bar**, at 36.6 percent against 66.7. Worse, its
>    interval of [30.1, 42.6] **contains its own 33.3 percent baseline**, so on the corner passes
>    the classifier is not distinguishable from a predictor that answers SW every time. The
>    original table's "yes" in the clears column for corners is withdrawn.
> 3. The edge midpoints group clears its corrected bar of 50 percent on its lower bound of 53.5,
>    so that row stands.
> 4. Overall 46.7 percent still clears the corrected 40 percent bar on the point estimate, so the
>    classifier is not vacuous. **But it earns that on the edge midpoints alone.**
> 5. **Nothing that ships depends on this bar.** A1 and A2 at weight 0.5 were selected on their own
>    paired improvement on the held-out folds, which is unaffected by how chance was stated. The
>    shipped arm stands on that improvement, not on A3 having passed a gate.
>
> The corners failure matters beyond bookkeeping: corners are where three lines share a start, so
> they are exactly where a region reader would be worth the most. See
> `reports/PREREG_prepress_region_2026-09-21.md`.

The bar was fixed before training: a lower confidence bound of at least twice the 12.5 percent
chance, so 25 percent, within each group, with substitution per group.

| group | accuracy | interval | lower bound | clears the 25 bar | substitution ratio |
|---|---|---|---|---|---|
| edge midpoints | **61.8 percent** | [53.5, 69.4] | 53.5 | yes | 0.84 |
| corners | **36.6 percent** | [30.1, 42.6] | 30.1 | yes | 0.83 |

Overall **46.7 percent**, against the position head's 18.5 from D2 and a 12.5 chance.

**The caveat, recorded rather than buried.** The three folds score 58.3, 62.5 and **19.2**. A
fold-clustered interval would be [19.2, 62.5] and would NOT clear the bar. The bar fixed in advance
was a per-pass bootstrap and it clears that; session 01 is much harder than the other two.

#### A1 Start-region entry. SHIPS.

Entry restricted to the first 1.0 m of each chain, not pinned to a cell, emissions choosing within
that window and driving progress afterwards.

**The pinned-entry clock check, explicit:** end-time substitution falls from 77.5 to 66.7 percent.
That is the pinned-entry signature in weakened form. It stays clear of the bar and the guard passes,
but it moved and that is reported.

#### A2 Start term on the chain totals. SHIPS at weight 0.5.

Re-aimed from direction, which D4 refuted, to **start consistency**: a per-line term scoring how
well each line's start region agrees with A3's read. It acts on the chain totals, where the line is
actually decided; an entry prior alone was measured **inert** on the committed answer.

#### The arms, measured

Nine cross-day pairings, seven used for the decision after excluding the two selection folds.

| arm | line, 7 pairings | line, 9 | paired delta | interval | not starting there | reversed | ships |
|---|---|---|---|---|---|---|---|
| shipped | 69.17 | 58.33 | | | 400 | 60 | |
| A1 | 75.00 | 62.50 | +5.00 | [2.38, 5.83] | 362 | 31 | yes |
| A2_0.25 | 75.00 | 57.50 | +3.33 | [1.55, 5.00] | 375 | 36 | yes |
| A2_0.5 | 75.00 | 58.33 | +4.17 | [0.36, 4.64] | 385 | 32 | yes |
| A2_1.0 | 71.67 | 54.17 | +1.67 | [-2.74, 4.05] | 421 | 27 | **no** |
| A1_A2_0.25 | 75.83 | 61.67 | +6.67 | [3.93, 8.57] | 343 | 30 | yes |
| **A1_A2_0.5** | **76.67** | **64.17** | **+5.83** | **[2.50, 7.26]** | **359** | **27** | **SHIPPED** |
| A1_A2_1.0 | 76.67 | 60.83 | +5.00 | [-1.07, 5.95] | 403 | 21 | **no** |

**Selection was made on the held-out folds only**, never on the decision pairings: shipped 41.25,
A1 45.83, A1_A2_0.25 46.67, **A1_A2_0.5 47.92**. A first version of the stage selected by
decision-pairing accuracy, which is test-side selection; that was caught and corrected, and the
answer did not change.

**Same-line reversals fall from 60 to 27.** Commitments to a line that does not start there fall
from 400 to 359, a smaller move than hoped given A2 was aimed at exactly that category.

#### Extra 1 The 3 m/s ceiling. THE MOST CONSEQUENTIAL RESULT.

Paired over nine pairings, pairing key `stem|pass_id`.

| | with the ceiling | without |
|---|---|---|
| semi-bounded line | 50.0 percent | **58.3** |
| bounded line | 65.8 | 65.8 |
| paired delta | **-7.50, interval [-11.48, -3.15], excludes zero** | |
| **verdict gap** | **15.83 points** | **7.50 points** |
| **semi-bounded becomes the core** | **NO** | **YES** |

**Applied to the decision the ceiling loses the verdict.** It is therefore OFF for the decision and
ON for the display, which is what the instruction to keep it on the display either way asks for.

#### Extra 2 Along-line progress error, decoded

On correct-line passes, decoded against the truth at the same window centre. Not the display
offset.

| | |
|---|---|
| median | **0.500 m** |
| p90 | 3.750 m |
| within 0.25 m | 40.7 percent |
| within 0.5 m | 57.6 percent |
| window comparisons | 4536 |

---

### PART 3: THE DISPLAY

| | |
|---|---|
| total latency | 1.0 s, the first frame at which a window has finished recording |
| internal lock | 1.5 s; the display does not wait for it |
| **causal bound over every drawn frame** | **-0.000 s** |
| rule violations on the decoded segment | **0** |
| frames with no red dot | **0** |
| jumps over 0.5 m | **116, all 116 at the lock**, one per walk |
| committed line, demonstration pairing | 78.3 percent |
| locked display line | 70.0 percent |

#### The two tracking figures, and why both are printed

| fraction of frames within 0.5 m | |
|---|---|
| **projected, what a viewer sees** | **21.7 percent**, mean 1.55 m |
| **decoded only, what the decoder alone supports** | **2.6 percent**, mean 1.76 m |

The encoder reports where the walker was at the window's **CENTRE**, verified to 0.000 m against
the interpolated truth, while the window's own END is 1.28 to 1.32 m further along. A window may
only be drawn once it has ended, so the newest decoded position is always about a second old. The
dot is therefore drawn at that position **projected forward** along the committed line at the
decoder's own measured pace, closing the gap at up to 3.0 m/s: 3463 projected frames, furthest
3.15 m ahead.

**The difference between those two rows is the projection, not the decoder.** It is dead reckoning,
the same class as the ramp extension deleted earlier for drawing without evidence, and it ships on
the condition that it is never silent: declared in the caption, in ACCEPTANCE.md, and enforced by a
standing test that fails any render which projects without recording how many frames and how far.

**The honest fix is a retrain with position labels at the window END rather than its centre**, which
would remove the gap instead of assuming past it. That is a model change and was not in this batch.

---

## PREPRESS_REGION_REPORT_2026-09-21.md

**Source:** `reports/PREPRESS_REGION_REPORT_2026-09-21.md`, 2026-09-21. **SHA-256:** `0c61c04fb497b19920235b14c646a2c76332c4765bfba649ce728258c3758335`. **Original combined here** on 2026-09-24.

### The start region from the pre-press windows: a measured negative

2026-09-21. Pre-registration: `reports/PREREG_prepress_region_2026-09-21.md`, written before any
arm ran and approved with amendments A to G.

**The result in one line.** A perfect start-region reader would be worth **+12.5 points** of line
accuracy. The best reader that can actually be built from the pre-press windows reaches **40.0
percent** against a **20.0 percent** baseline, where **74.2 percent** is the break-even. Put
through the decoder with its weight re-swept it buys, at best, **one pass per pairing**: five
passes out of 840. **Nothing was changed and nothing was re-rendered, and there is one decision
left for the operator** (§9).

**The four arms, in the order they ran.**

| arm | region accuracy | interval |
|---|---|---|
| A, the A3 feature set with `AFTER_S = 0` | 25.00 | [24.0, 42.0] |
| B, the 25-cell posterior | 21.67 | [18.3, 33.0] |
| B2, the frozen encoder embedding | 33.33 | [26.3, 46.9] |
| **C, the fine-tuned encoder** | **40.00** | [30.1, 43.1] |

None reaches the break-even, and arm C's margin over B2 turns out to be class collapse rather than
better localisation (§8).

---

#### 1. Why this was worth asking

The premise was the operator's and it was a good one: the decoder's dominant failure is picking a
line that starts somewhere else entirely, and the start regions are metres apart, so a coarse
"which corner" reader ought to be easy even where "which of three lines" is not.

The premise checks out on both counts.

**The failure really is a start-region failure.** On the shipped arm over nine pairings and 1080
passes, 436 passes get the wrong line and **359 of them, 82.3 percent, pick a line whose start
region is not the true one**. Only 27 are reversals of the right line.

**And the pre-press windows really are absent from training.** `pipeline/constrained/dataset.py:121`
selects `(rec.mode == "walk") & np.isfinite(rec.xy).all(1)`. Measured across all eighteen
recordings there are **1440 pre-press windows, exactly four per pass, every one labelled
`walk_edge` and not one carrying a finite `xy`**. No head on record has ever seen a participant
outside the grid. The four windows are 2 s wide on a 0.5 s stride and cover a **3.5 s span**
which, measured over all 360 passes, ends a median **0.282 s before the press** and begins a
median 3.782 s before it. The lattice does not align with the press, so the span neither reaches
the press nor reaches back a full 4 s.

---

#### 2. Step 0, the ceiling: worth chasing

`runs/constrained/fh/t0_oracle/results.json`. The true region substituted into the A2 term. No
training, no decoder change: the term already accepts a per-pass per-line log offset.

| arm | held-out 7 | paired delta | interval | |
|---|---|---|---|---|
| A1_A2_0.5, the current ship | 75.00 | | | baseline |
| oracle, weight 0.5 | 87.50 | **+12.50** | [9.51, 26.19] | clears the 5 point bar |
| oracle, weights 1.0, 2.0, 4.0 and hard | 87.50 | +12.50 | | identical, as predicted |

The four weights agreeing is the check that the term reaches the chain totals as intended: a
one-hot posterior clipped at 1e-9 already separates the true region by about 20 nats at weight 0.5,
so the sweep was expected to plateau and does.

**Per region, at the operator's instruction, because a ceiling carried by SW alone is not worth
chasing.** It is not carried by SW:

| region | passes | baseline | oracle | gain |
|---|---|---|---|---|
| W_mid | 84 | 53.6 | 88.1 | **+34.5** |
| N_mid | 84 | 64.3 | 97.6 | **+33.3** |
| NW | 126 | 57.9 | 82.5 | +24.6 |
| E_mid | 84 | 65.5 | 84.5 | +19.0 |
| NE | 84 | 71.4 | 90.5 | +19.0 |
| SW | 168 | 57.1 | 68.5 | +11.3 |
| S_mid | 84 | 89.3 | 100.0 | +10.7 |
| SE | 126 | 58.7 | 62.7 | +4.0 |

SW gains least precisely because SW holds three lines, so even a perfect region leaves a three-way
choice. That is the geometry working as expected.

#### 3. The number that governs everything below: the break-even

The same stage ran **simulated** readers, right with probability *a* and otherwise on a uniformly
drawn wrong region, at the shipped weight.

| realised region accuracy | line accuracy delta | interval | |
|---|---|---|---|
| 37.5 percent | **-10.00** | [-15.60, -1.90] | significantly **worse** |
| 56.7 percent | -4.17 | [-6.67, 8.10] | no gain |
| 74.2 percent | **+5.00** | [1.31, 15.24] | real gain |

**A region term must reach roughly 75 percent before it stops costing line accuracy.** This is the
same effect `q4_arms` already saw when A2 at weight 1.0 made wrong-region errors worse, 421 against
359. Beating the 20.0 percent baseline was the pre-registered kill rule; it is necessary and
nowhere near sufficient.

#### 4. Steps 1 and 2: what can actually be read

`runs/constrained/fh/t1_region/results.json`, `runs/constrained/fh/t2_embed/results.json`.
Strictly causal, windows whose END is at or before the press, `AFTER_S = 0`, asserted in
`tests/test_prepress_is_causal.py`. One feature row per pass, grouping asserted on the window
indices themselves, because the four windows of a pass overlap by 1.5 s and are not four
observations.

| arm | what it reads | region accuracy | interval |
|---|---|---|---|
| A | the A3 feature set, xy_hat, re-fitted with AFTER_S = 0 | 25.00 | [24.0, 42.0] |
| B | the 25-cell posterior over the same windows | 21.67 | [18.3, 33.0] |
| **B2** | **the frozen encoder embedding, 384 dims** | **33.33** | **[26.3, 46.9]** |

Median over the nine pairings. Each pass is predicted once per pairing whose test side is its
session, so the 1080 rows are 360 passes over again and the row count is not a sample size; the
deciding figure is the per-pairing median.

**It is reading the radio, not a clock.** Substitution ratio 0.89 to 0.95 against a ceiling
computed from the actual pairs. Swapping another participant's CSI over the same windows changes
the answer 78 to 79 percent of the time against an 87.5 percent ceiling. The head is not vacuous.
It is simply not accurate.

##### Where it works, and where it does not

B2's per-region recall against a 20.0 percent baseline:

| edge midpoints | | corners | |
|---|---|---|---|
| S_mid | **67.6** | NE | 36.1 |
| N_mid | **60.2** | SE | 31.5 |
| E_mid | **57.4** | NW | 20.4 |
| W_mid | 32.4 | **SW** | **17.1** |

**The corners cannot be read and SW is below the baseline.** That is the third independent
measurement of the same thing: A3's corners group fails its corrected bar at 36.6 percent (see
§6), and the corners are exactly where the prize is, because SW holds three lines.

Arm C later moves SW to 45.8 percent, which looks like the corner problem being solved and is not:
it buys that by leaning on SW as the largest class while W_mid falls to 0.9 percent. §8 has the
full redistribution.

##### The cross-session structure, which is the real obstacle

| pairings testing on 02 or 03 | pairings testing on 01 |
|---|---|
| 47.5, 53.3, 55.8, 56.7 | 15.8, 17.5, 18.3 |

Sessions 01, 02 and 03 were recorded on three consecutive days, 9 to 11 September, with no
same-day duplicates, so this is not a same-day artefact. **Session 01 is simply the hard fold**,
which is the caveat A3 already carried in those words. At n equals 3 sessions there is no power to
say more. The failure is cross-session generalisation, not model capacity.

#### 5. Step 3, the previous-pass confound: small, and measured either way

The walker approaches from wherever the previous pass ended, so a head might be reading where they
came from rather than where they are.

- **Only 11.7 percent of passes have their previous pass ending where this one starts.**
- Accuracy when it matches: 40.0 percent. When it does not: 35.7 percent (arm B2).

There is a little of it and it is not carrying the result. Reported either way, as instructed.

#### 6. Amendment B, restated: A3's chance level was understated

`q3_startclf` reports `chance_pct: 12.5`, uniform over eight regions. The classes are not uniform:
SW 72 passes of 360, NW 54, SE 54, and 36 each for the rest. The honest baseline is the best
constant predictor, which differs per group because the groups are subsets of passes.

| task | correct baseline | bar, twice baseline | measured | verdict |
|---|---|---|---|---|
| overall, 8 regions | **20.0** | **40.0** | 46.7 | clears on the point estimate |
| edge midpoints, 144 passes | **25.0** | **50.0** | 61.8, lower bound 53.5 | **clears** |
| corners, 216 passes | **33.3** | **66.7** | 36.6, interval [30.1, 42.6] | **DOES NOT CLEAR** |

A3's bar was "twice the 12.5 percent chance, so 25 percent". Against the correct 20.0 percent
baseline it should have been 40 percent. **The corners group fails, and its interval contains its
own 33.3 percent baseline**, so on corner passes A3 is not distinguishable from a predictor that
answers SW every time. Overall 46.7 percent still clears the corrected bar, but it earns that on
the edge midpoints alone.

**Nothing that ships depends on this bar.** A1 and A2 at 0.5 were selected on their own paired
improvement on the held-out folds, which is unaffected by how chance was stated.

Carried into `reports/PARTS_1_TO_3_REPORT_2026-09-20.md` under A3 and
`reports/SEMIBOUNDED_STATE.md` section 7e, restated in both rather than quietly amended.

#### 7. The ship test: nothing ships

`runs/constrained/fh/t3_ship/results.json`. The real B2 classifier's posterior in the A2 term,
weight re-swept with the real classifier as amendment E requires. `replace_w` removes the shipped
A3 term; `add_w` keeps it and adds the pre-press term on top.

| arm | held-out 7 | paired delta | difference of medians | interval | ships |
|---|---|---|---|---|---|
| A1_A2_0.5, current ship | **75.00** | | | | baseline |
| add_0.25 | 75.00 | +0.00 | +0.00 | [-0.83, 3.33] | no |
| replace_0.25 | 71.67 | +0.00 | -3.33 | [-1.19, 4.40] | no |
| add_0.5 | 72.50 | -0.83 | -2.50 | [-1.55, 1.31] | no |
| replace_0.5 | 70.00 | -0.83 | -5.00 | [-2.50, 1.07] | no |
| add_1.0 | 70.83 | **-4.17** | -4.17 | [-5.00, -1.43] | no, significantly worse |
| replace_1.0 | 66.67 | **-5.83** | -8.33 | [-9.17, -1.79] | no, significantly worse |

Neutral at best, and significantly negative once the term is given real weight. **The shipped arm
is `None`.** Per amendment F, nothing was changed, no render was run, and no freeze was written.

##### The mechanism, in the error counts

The failure is not that the term does nothing. It is that **it moves passes onto lines starting in
the wrong region, which is the exact error it was built to prevent**:

| arm | wrong lines | of those, a wrong start region |
|---|---|---|
| A1_A2_0.5, baseline | 437 | **356** |
| replace_0.25 | 424 | 339 |
| add_0.25 | 428 | 352 |
| replace_0.5 | 450 | 372 |
| add_0.5 | 448 | 377 |
| add_1.0 | 491 | 435 |
| replace_1.0 | 515 | **455** |

Wrong-region errors rise from 356 to 455 as the term is given weight. A reader that is right about
one pass in three, pushed hard, relocates more passes than it rescues. This is the same shape
`q4_arms` recorded when A2 at weight 1.0 took wrong-region errors from 359 to 421, now reproduced
with a different and independently built reader.

*(These counts are computed in `t3_ship` rather than carried: `n2_arms.summarise()` does not emit
`not_starting_there`, and summing an absent key gave a clean 0 on every arm in the first run. That
is the shape `test_asserted_not_measured.py` exists for and it was corrected before the figures
above were read.)*

#### 8. Arm C, the fine-tuned encoder

The pre-registered kill rule fires only if arms A and B both fail to beat the baseline with a lower
bound above it. Arm A cleared it at 25.00 with a lower bound of 24.0, so the rule did not fire and
arm C was permitted. It ran to close the question rather than in hope, with hyperparameters fixed
in advance and not tuned: lr 1e-4, 8 epochs, batch 16, seed 0, encoder transferred from the trained
posterior head. The expectation was recorded before the run: the failure is cross-session
generalisation, not capacity, and more capacity fitted to 240 passes is the wrong medicine.

**Result: 40.00 percent region accuracy, interval [30.1, 43.1], median over the nine pairings,
33.6 minutes.** Better than the frozen embedding's 33.3, and still 34 points short of the 74.2
percent break-even.

The cross-session structure is unchanged, which is the point:

| pairings testing on 02 or 03 | pairings testing on 01 |
|---|---|
| 34.2, 40.0, 40.8, 45.8, 47.5, 49.2 | 21.7, 22.5, 27.5 |

**And the seven extra points are not better localisation.** Arm C's per-region recall against
B2's shows a redistribution rather than an improvement:

| region | share of passes | B2, frozen | C, fine-tuned | |
|---|---|---|---|---|
| S_mid | 10.0 | 67.6 | **86.1** | |
| SW | **20.0** | 17.1 | **45.8** | the largest class |
| SE | 15.0 | 31.5 | 43.2 | |
| N_mid | 10.0 | 60.2 | 44.4 | fell |
| NW | 15.0 | 20.4 | 25.9 | |
| E_mid | 10.0 | 57.4 | 24.1 | fell |
| NE | 10.0 | 36.1 | 14.8 | fell |
| **W_mid** | 10.0 | 32.4 | **0.9** | **effectively never predicted** |

Fine-tuning moved the model onto the frequent classes and all but stopped predicting W_mid. That is
class collapse at 30 passes per class, which is exactly what the pre-registered expectation said
would happen, recorded before the run: *"the failure is cross-session generalisation, not capacity,
and if arm C improves anything it will most likely be the folds that were already easy."* It is
also why a higher pooled accuracy here is not straightforwardly better news: a start term built
from a prior-chasing posterior pushes passes toward the common regions, which is the opposite of
what the term is for.

##### The best reader, decoded

Because arm C superseded B2 as the best reader, the end-to-end test was re-run with it so that the
claim does not rest on a superseded one: `runs/constrained/fh/t5_shipc/results.json`. The
expectation was recorded before that run too, arm C at 40.0 percent sitting inside the range
`t0_oracle` measured as significantly negative.

**That expectation was wrong, and the way it was wrong is informative.**

| arm | held-out 7 | paired delta | difference of medians | interval | wrong-region errors | rule says |
|---|---|---|---|---|---|---|
| A1_A2_0.5, current ship | 75.00 | | | | 356 | baseline |
| add_0.25 | 75.83 | +0.00 | +0.83 | [0.00, 0.60] | 354 | no |
| **add_0.5** | **75.83** | **+0.83** | +0.83 | **[0.24, 1.07]** | 352 | **ships** |
| **add_1.0** | **75.83** | **+0.83** | +0.83 | **[0.24, 1.07]** | 354 | **ships** |
| replace_0.25 | 71.67 | -1.67 | -3.33 | [-2.50, 2.74] | 343 | no |
| replace_0.5 | 70.83 | -0.83 | -4.17 | [-2.62, 3.34] | 340 | no |
| replace_1.0 | 71.67 | -0.83 | -3.33 | [-2.03, 3.81] | 335 | no |

Arm C does not cost line accuracy the way the simulation predicted. The simulated reader was wrong
**uniformly at random**; arm C is wrong in a **prior-aligned** way, leaning on the regions the
decoder already favours, so it does far less damage. It also does almost no good.

#### 9. The one decision left for the operator

**By the letter of the pre-registered ship rule, `add_0.5` ships.** Its paired improvement interval
on the seven held-out pairings is [0.24, 1.07], entirely above zero, and the guard passes. Under
amendment F that would trigger one render, one freeze superseding the current one, and the headline
figure re-measured.

**I have not done that, because three things about this number say it is at the resolution floor
rather than a result.**

**One. The effect is five passes.** A pairing holds 120 passes, so a per-pairing rate moves in
steps of 0.833 points. A paired delta of **+0.83 is exactly one pass**. Across the seven held-out
pairings the deltas are +0.83, +0.83, +1.67, +0.83, 0.00, 0.00, 0.00 — **five passes out of 840**,
or +0.6 points pooled.

**Two. The interval excludes zero for a reason that is not effect size.** No held-out pairing moved
down: four moved up by one or two passes and three were exactly flat. A bootstrap over seven values
that are all zero or positive will exclude zero however small they are. The only pairing that got
worse, s01_to_s02 at -1.67, is a **selection** fold and so is excluded from the decision by the
rule's own design.

**Three. There is no weight gradient.** Weights 0.25, 0.5 and 1.0 all give the same +0.83 median.
A term carrying real information should respond to being weighted; one that flips the same handful
of passes regardless of weight is not carrying information, it is jostling. Compare the `replace_`
family, which does respond to weight, and responds downward.

**Set against that**, one point in favour deserves stating plainly: the `replace_` arms cut
wrong-region errors from 356 to 335, which is the mechanism working in the intended direction even
as line accuracy falls. The term does push passes toward the right region; it just costs more
elsewhere than it gains.

##### THE DECISION, 2026-09-22

> **The pre-registered rule's verdict: `add_0.5` SHIPS.** Paired improvement interval on the seven
> held-out folds [0.24, 1.07], entirely above zero; guard passes.
>
> **The operator declined to ship it.**
>
> **This override is POST HOC.** It was made after seeing the data, and it is named as post hoc in
> those words rather than presented as the rule having been applied.

**The grounds, as given:**

1. **The effect is five passes in 840.** Held-out deltas: +0.83, +0.83, +1.67, +0.83, 0, 0, 0.
2. **Per-pairing rates move in 0.833-point steps**, because a pairing holds 120 passes, so a median
   paired delta of **+0.83 is one pass**.
3. **There is no weight gradient.** Weights 0.25, 0.5 and 1.0 all return the same +0.83. A term
   carrying real information responds to being weighted; the `replace_` family does, and responds
   downward.
4. **A bootstrap over seven non-negative deltas excludes zero regardless of effect size.** Four
   held-out pairings moved up and three were exactly flat; none moved down. The interval's exclusion
   of zero is therefore a statement about sign consistency, not about magnitude.

**Consequences, all of them:**

- **The shipped arm remains A1 + A2_0.5.** Unchanged.
- **Nothing rendered, nothing frozen, the headline figure unchanged.** The semi-bounded figure stays
  62.50 percent on the per-pairing difference of medians, and `runs/TRACKING_FROZEN_2026-09-20c.json`
  remains the authority.
- **The standing ship rule is amended for all future analyses, DC2 included**, so that condition (a)
  can no longer fire alone at the resolution floor. The amended rule is in
  `reports/SEMIBOUNDED_STATE.md` section 10 and is itself recorded as a rule change made after
  seeing the data:
  > an arm ships only if **(a)** its paired improvement interval on the held-out folds is entirely
  > above zero, **(b)** the median paired delta is at least **two passes per pairing**, which is
  > 1.67 points at 120 passes a pairing, and **(c)** the effect shows a **monotone response to the
  > term's weight**.

  Conditions (b) and (c) would each have caught `add_0.5` on their own.

#### 10. What this means, and what it does not

**It does not mean the run-up carries nothing.** `p2_prepress` already showed direction is readable
at 55.2 percent against 50, and this work shows edge-midpoint start regions are readable at about
60 percent. Both are real and both are too weak to move a decision.

**It does mean the retrofit route is closed.** Room A never labelled a position outside the grid,
the approach happens in a strip that is 1.5 m deep at best and 0.20 m on the A and B lines before a
node blocks it, and no amount of re-reading the existing artefacts recovers a label that was never
recorded.

**The honest framing for the thesis.** This is a measured negative with a clean ceiling beside it,
which is more useful than a null on its own: the +12.5 point ceiling says the idea is right, the
74.2 percent break-even says what would be needed, and the 33.3 percent says how far away the
current data is. The obstacle is identified and it is a data-collection obstacle, not a modelling
one.

#### 11. Carried into DC2

`reports/DC2_PROTOCOL_2026-09-18.md` gains the approach walk as a capture item: record it, label
its start region (which is free, being the known start of the pass about to be walked), give it a
position track where the video allows, record each line's usable run-up depth, and keep the
approach origin varied so an approach-trained head cannot learn the pass order.

---

#### Where everything lives

| | |
|---|---|
| pre-registration | `reports/PREREG_prepress_region_2026-09-21.md` |
| the ceiling and the break-even | `runs/constrained/fh/t0_oracle/results.json` |
| arms A and B, confusion, substitution, confound | `runs/constrained/fh/t1_region/results.json` |
| arm B2, the frozen embedding | `runs/constrained/fh/t2_embed/results.json` |
| the ship test | `runs/constrained/fh/t3_ship/results.json` |
| arm C | `runs/constrained/fh/t4_finetune/results.json` |
| arm C through the decoder | `runs/constrained/fh/t5_shipc/results.json` |
| the causality and grouping guards | `tests/test_prepress_is_causal.py` |
| findings, one per stage | `reports/FINDINGS_staget*.txt` |

---

## PART1_REPORT_2026-09-22.md

**Source:** `reports/PART1_REPORT_2026-09-22.md`, 2026-09-22. **SHA-256:** `26fd8ab9663c093bc91a880a23527892c6018d6b14795c4bc4cfb6fe31ddbf63`. **Original combined here** on 2026-09-24.

> **Superseded:** The causal lock figures that batch 23c added beside the originals decoded the display at sd_scale 1.0; the lock the render actually draws (sd_scale 4.5) is in `reports/CORRECTION_drawn_lock_2026-09-23.md`, and `runs/TRACKING_FROZEN_2026-09-23h.json` records it as 53.33 percent held-out (`lock.SHIPPED_one_lattice`).

> **Superseded:** 62.50 percent remains the PRE-REGISTERED headline. The post-amendment headline is 73.33 percent [35.00, 87.50] from freeze 23d onward (`runs/TRACKING_FROZEN_2026-09-23h.json`, `headline_semibounded`).

### Part 1: fix the render at its source

2026-09-22. Standing brief `reports/BRIEF_render_and_prepress_2026-09-22.md`. Accepted by the
operator. Frozen at `runs/TRACKING_FROZEN_2026-09-22b.json`.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes.**

---

#### Outcome

**Nothing shipped in the decision. The headline is 62.50 percent, unchanged and carried rather
than re-measured.** The render changed for the dwell cut and rules V1 to V4 only, neither of which
touches the decoder.

The useful outputs are a diagnosis, an audit, and a rule that caught something.

---

#### Step 0. The permanent rendering rule sheet

`reports/RENDER_RULES.md` is now **the single place rendering rules live**. Rules 1 to 6 verbatim,
then V1 to V4 as binding operator decisions. `runs/constrained/demo/ACCEPTANCE.md` holds measured
results only and points at the contract.

| rule | measured on the shipped render |
|---|---|
| **V1** display runs exactly 2.0 s behind real time | 2.0 s, identical on all 120 walks |
| **V2** commit and marker are one event | **0 violations, max gap 0.000 s** |
| **V3** lock time structural, identical every walk | **exactly one** distinct offset, 2.25 s, over 120 walks |
| **V4** no dwell footage | **29,165 frames removed, 0 remaining** inside a grid block |

**V1 decides the open latency item at 2 s.** **V3 forbids confidence-gated or variable latency
outright.** Seven new tests enforce them, all binding on measured data rather than on constants.

**The dwell bug was as reported:** `DWELL_EXCERPT_S = 30.0` added to a window **index**, giving
15 s at a 0.5 s stride while the name said 30. The constant is deleted and an AST test now refuses
any `*_S` constant used as a subscript anywhere in the render.

**Why 2.25 s and not 2.0 s**, measured and now in ACCEPTANCE.md: `t_start` is the first walk
window's **centre**; the scene begins 0.25 s later at `t[lo] + WINDOW_S − HEAD_OFFSET_S`; the
commit is 2.0 s after that. The window centre itself sits a median 0.202 s after the press because
the lattice does not align with it. The sentence is computed from the constants, so it cannot drift.

#### Step 1. The room-transfer audit

`reports/ROOM_TRANSFER_AUDIT_2026-09-22.md`. Twelve fitted components: **seven refit for DC2, four
reuse as grid geometry, three unjudgeable until Room B exists.**

**Two silent failures found**, and they matter more than the count:

1. **The "adaptive" null is inert.** The five-head pool row-normalises every window, so
   `AdaBN`-style self-calibration resolves to exactly 0.000 and the effective null is a **fixed
   −7.50 nats** fitted to Room A. A component named `AdaptiveNullEmission` that does not adapt.
2. **The gate threshold 0.431** is an absolute band energy.

Neither raises in a new room. Both quietly shift entry and exit rates and read as the decoder
generalising badly.

#### Step 2. The 2 s lock, diagnosed

`t6_lockdiag`, nine pairings. The stage reproduces the committed figure at 62.5, which is what
validates it.

| at the 2 s lock | all nine | held-out seven, NON-CAUSAL | **held-out seven, causal** |
|---|---|---|---|
| shipped lock | 49.2 (causal **49.17**) | 60.8 | **57.50** |
| no cell-marginal division | 58.3 (causal **56.67**) | 68.3 | **58.33** |
| chain-total lock | 55.8 (causal **54.17**) | 73.3 | **65.00** |
| committed answer, whole walk | 62.5 | 75.0 | 75.0, not a lock, unchanged |

**Two causes, both mechanisms rather than Room A fits.**

**The estimator.** The lock takes the single best-path STATE of a Viterbi; the committed answer
scores each CHAIN. Same evidence, **+12.5 points** (NON-CAUSAL; **+7.50 causally**). Neither the chain prior nor the A2 term reaches
the lock at all, which is why two of the five pre-registered ablations would have been vacuous as
specified and were aimed at the estimator that reads them instead.

**The cell marginal.** Edge-line cells hold 0.6 to 1.0 percent of training mass against 16.5 at the
centre, so dividing by it boosts edge lines by roughly 3 nats. Every E line is over-drawn
(E_col5 2.94), every diagonal under-drawn (C_fwd 0.44). (NON-CAUSAL; **causally E_col5 2.74 and
C_fwd 0.54, and E_row1 is UNDER-drawn at 0.67**, so "every E line" does not hold at the causal lock.)

**Not explained, and said so:** A_fwd is over-drawn at 1.95 (NON-CAUSAL; **2.61 causally**) under every estimator including the
committed answer at 2.24, and no ablation moves it. *(Resolved later: see
`reports/ITEMS_ABC_REPORT_2026-09-22.md`, item C.)*

#### Step 3. Four arms, all refused

`t7_lockarms`. Every arm that raised pooled accuracy degraded the edge lines.

| arm | held-out 7, NON-CAUSAL | **causal** | paired, NON-CAUSAL | **paired, causal** | edge mean, NON-CAUSAL | **causal** | ships |
|---|---|---|---|---|---|---|---|
| shipped | 60.8 | **57.50** | | | 65.3 | **53.24** | |
| E_chain_total | 73.3 | **65.00** | +7.50 | **+5.83 [2.50, 11.79]** | 49.1 | **36.57** | no |
| **E_both** | 71.7 | **63.33** | +10.00 [2.02, 11.55] | **+4.17 [0.71, 8.57]** | 27.3 | **9.72** | **no** |
| E_no_marginal | 66.7 | **59.17** | +4.17 | **+1.67 [-0.95, 5.60]** | 22.2 | **12.96** | no |

**Condition (f) did the work.** Without it `E_both` would have shipped at +10 points while taking
E_col1 from 50.0 to **7.4** percent (NON-CAUSAL; **causally from 42.59 to 0.00**). `reports/FINDING_pooled_vs_edge_2026-09-22.md` records the
trade-off and the operator's decision to **keep the shipped lock**, with the four grounds.

**Nothing helps on the session-01 folds** — flat or worse on all three, as pre-registered before
the arms ran.

#### Items 1 to 3 (the follow-up instruction)

**Item 1, DC2 calibration.** `t8_calib` measured the sensitivity that **reverses the audit's
emphasis**:

| | flat region | outside |
|---|---|---|
| gate threshold | 0.20 to 0.60, about **3x** | 1.10 costs 4.2 points |
| **null level** | −9.0 to −7.5, about **1.5 nats** | **−10.5 costs 16.7 points** |

The relative forms were implemented and **verified NOT to reproduce within one pass**: worst
scatter 3.33 points against a 0.833 bar, every paired interval straddling zero. **Unbiased and
noisy.** A hypothesis of mine was **refuted** — I expected the scatter to belong to the null, and
the gate-only arm has the same worst case, so it does not. **The anchor is the problem, not the
formula:** Room A's pre-press period varies 2.3x across three days. The forms ship **disabled**,
and the DC2 protocol now specifies the calibration block that would make them work.

**Item 2**, the 2.25 s explanation: above, in Step 0.

**Item 3, length-normalised chain totals.** `t9_lengthnorm`. All three normalisations returned
**69.17, identical to the raw chain total** (NON-CAUSAL; **causally 62.50, 62.50 and 63.33 against
62.50**, per-metre one pass off inert because the causal lock sees 3 windows, not 5), and the reason is exact: at the lock **every chain is
traversed identically** — 5 windows, 5 states, 3.00 m of arc. The 21-versus-30 state asymmetry
belongs to the whole chain, which the lock never sees. **Inert by construction.**

#### Faults of my own in Part 1

| fault | effect |
|---|---|
| a 1 s posterior tree read against 0.5 s recordings | **silently dropped half the passes**. Now asserted, never truncated |
| `not_starting_there` summed a key the summariser never emits | a clean **0** on every arm that looked like a measurement |
| `t9` inherited `t7`'s `findings()` name | **overwrote `FINDINGS_staget7lockarms.txt`**; re-ran t7 to restore it |

#### Where the numbers live

`runs/constrained/fh/t6_lockdiag`, `t7_lockarms`, `t8_calib`, `t9_lengthnorm`, `f3_render`.
Freeze `runs/TRACKING_FROZEN_2026-09-22b.json`. Pre-registrations
`reports/PREREG_lock_2026-09-22.md`, `reports/PREREG_lengthnorm_2026-09-22.md`.

---

## PART2_REPORT_2026-09-22.md

**Source:** `reports/PART2_REPORT_2026-09-22.md`, 2026-09-22. **SHA-256:** `72d000f1f3dea57c16eb86b70b8dd29bf0ab22bac3782fb624b8aeda4a386c0a`. **Original combined here** on 2026-09-24.

> **Superseded:** 62.50 percent remains the PRE-REGISTERED headline. The post-amendment headline is 73.33 percent [35.00, 87.50] from freeze 23d onward (`runs/TRACKING_FROZEN_2026-09-23h.json`, `headline_semibounded`).

### Part 2: the pre-press region reader, version 2

2026-09-22. Pre-registration `reports/PREREG_prepress_v2_2026-09-22.md`, written before any arm
ran. Standing brief `reports/BRIEF_render_and_prepress_2026-09-22.md`.

---

#### What Part 2 produced

**No ship, and one active harm.** Nothing from Part 2 enters the Room A headline, which stands at
**62.50 percent**, unchanged and untouched.

That is the honest summary and it should not be dressed up. The useful outputs are three, and none
of them is a gain:

1. **A mechanism control** that worked exactly as a control should.
2. **A confound I had to withdraw a claim over.**
3. **A frozen arm for DC2 to test**, which is a question rather than an answer.

Set against that: **the tracker extension was significantly negative**, and **three faults in my
own code each briefly changed a verdict**.

---

#### 1. The arms, and what each settled

| arm | result |
|---|---|
| (a) veto | `a_veto_1.0` cleared all five conditions. **Declined.** |
| (b) abstain | `b_abstain_0.25` passes (a), (b), (d), (f); **fails (c)**. Declined. |
| (c) coarse | fails (c) |
| (d) causal per-session adaptation | **+9.17 on session-01 folds, interval includes zero. Untestable with Room A's anchor.** |
| (e) class-balanced | reader 38.33 against 42.50 plain; no arm shipped |
| extension: AdaBN on the tracker | **significantly NEGATIVE.** Protocol deviation, exploratory |

**Seven of eleven arms were harmless**, meaning they neither gained under the rule nor degraded
any edge line. For a reader at 42.5 percent against a 74.2 percent break-even, harmlessness was
the realistic target and it was met.

#### 2. Arm (d): the right direction, not establishable here

| mode | median | per-pairing spread | session-01 folds | other folds |
|---|---|---|---|---|
| unadapted | 33.33 | 40.83 | **17.50** | 50.42 |
| **AdaBN** | **42.50** | **28.33** | **26.67** | 46.25 |
| input normalisation | 22.50 | 39.17 | 18.33 | 39.17 |

Paired **+6.67**, CI **[−2.22, 8.61]**, which **includes zero**. Positive on all three session-01
folds (+14.17, +7.50, +10.83) and it **cuts the per-pairing spread from 40.83 to 28.33**, which is
the instability item 1 identified as Room A's limitation.

**Recorded as untestable with Room A's anchor, not as adaptation failing.** A control makes this
stronger: input normalisation is significantly **worse**, paired −10.00 with CI [−10.83, −1.39]
excluding zero. The effect is specifically AdaBN, not any per-session rescaling.

#### 3. The mechanism check, which is the best thing in Part 2

Held-out passes, counts rather than rates:

| group | n | gained | lost | net |
|---|---|---|---|---|
| **covered, reader correct** | 262 | **31** | **0** | **+31** |
| covered, reader wrong | 288 | 6 | 10 | −4 |
| **uncovered, the control** | 290 | **0** | **0** | **0** |

**On the 262 passes the reader covered and got right, 31 were gained and not one lost.** On
covered-but-wrong it costs 4, as a real mechanism should. **On all 290 uncovered passes not a
single outcome changed** — the term is identically zero there, so the decode is the shipped one,
and this confirms the implementation rather than assuming it.

#### 4. A claim I made and withdrew

I wrote that the gains showed abstention protecting hard folds. **That claim is withdrawn.**

| fold | baseline | headroom | reader | coverage | net |
|---|---|---|---|---|---|
| s01_to_s03 | 50.00 | 50.00 | 42.5 | 75.0 | **+13** |
| s0203_to_s01 | 31.67 | 68.33 | 26.7 | 60.8 | +6 |
| s03_to_s01 | 25.83 | 74.17 | 25.8 | 79.2 | +5 |
| s0103_to_s02 | 86.67 | 13.33 | 50.0 | 49.2 | +3 |
| s0102_to_s03 | 88.33 | 11.67 | 54.2 | 50.8 | +1 |
| s02_to_s03 | 85.83 | 14.17 | 49.2 | 73.3 | 0 |
| s03_to_s02 | 75.00 | 25.00 | 43.3 | 70.0 | −1 |

**corr(reader accuracy, baseline) = +0.958.** The folds with the best readers are the folds with
almost no headroom left. **Abstention and headroom cannot be separated on Room A**, and neither is
claimed. Distinguishing them needs a fold where a strong reader meets a low baseline, and Room A
has none.

#### 5. The tracker extension: a protocol deviation, and a negative

**It should not have run.** The pre-registration gates it on arm (d) lifting session-01 reading
under the ship rule; arm (d)'s interval includes zero, so the condition was not met. It ran on an
operator override recorded as post hoc. **Deviation, and the result is exploratory.**

Held-out seven: **50.00 unadapted against 30.83 adapted.** Paired **−3.33**, CI **[−15.83, −2.62]**,
entirely below zero. Edge lines E_col5 −35.71, E_row5 −26.19, E_col1 −16.67.

**Where the harm concentrates is the informative part.** The three worst losses are the three
highest unadapted baselines (−23.33, −18.33, −15.83); the three session-01 folds are essentially
unchanged (+3.33, 0.00, −2.50). **Adaptation destroys performance where there was performance and
does nothing where there was none** — the opposite pattern to arm (d).

**Two explanations, both stated, neither claimed:** Room A's anchor is unfit (it varies 2.3x across
days, per item 1), and the tracker's downstream classifier is **frozen** where arm (d)'s LDA is
**refit**. They are not exclusive and this stage cannot separate them.

#### 6. Three faults of my own, each of which changed a verdict

| fault | effect |
|---|---|
| **a lattice-dependent test assertion** | "at least 500 calibration windows" passes or fails on **test order**, since a window count depends on which stride tree is bound. Green alone, red in the suite. Replaced with a per-recording minimum that holds on either lattice. |
| **rounded against unrounded edge comparison** | marked **every one of eleven arms** as degrading the edge lines, including ones that strictly improved them. An exact tie failed by up to 0.005. |
| **condition (c) reading the wrong quantity** | (a) and (b) read the paired delta; (c) read the median. They disagreed completely, and the median reading **passed an arm the paired reading fails.** |

**Two of these briefly made something look shippable that was not.** All three are the same shape
as the faults already in this project's test suite: a number that looked right, produced by code
that was not doing what its name said.

A fourth, smaller: condition (b) rejected an arm measuring **exactly two passes** on a
floating-point last bit. Now compared as integer passes.

#### 7. What goes to DC2

| | |
|---|---|
| **primary, carries the claim alone** | `b_abstain_0.25`, frozen `22c`, threshold 0.90, weight 0.25 |
| secondary, exploratory | `a_veto_1.0`, frozen `22d`, veto 0.01, 3.0 nats, weight 1.0 |
| exploratory | AdaBN on the tracker, statistics from the **calibration block only** |
| **primary comparison** | gate and null re-anchoring, **no tracker adaptation** |

The falsifiable prediction stands: a collapsed Room-B reader should tend toward **no effect**
rather than harm, because it abstains. A negative paired delta would mean abstention did not
protect, and that would be a real result.

#### Where the numbers live

`runs/constrained/fh/u1_adapt`, `u2_useit`, `u3_trackeradapt`, `u4_mechanism`.
Freezes `runs/TRACKING_FROZEN_2026-09-22c.json` and `...22d.json`.
Pre-registrations `reports/PREREG_prepress_v2_2026-09-22.md`,
`reports/PREREG_DC2_crossroom_2026-09-22.md`.

---

## ITEMS_ABC_REPORT_2026-09-22.md

**Source:** `reports/ITEMS_ABC_REPORT_2026-09-22.md`, 2026-09-22, evening. **SHA-256:** `5276308e86519d8e2eb1fc3d74738c6a1a005faf94372c794a5763dca7ec5e0f`. **Original combined here** on 2026-09-24.

> **Superseded:** The causal lock figures that batch 23c added beside the originals decoded the display at sd_scale 1.0; the lock the render actually draws (sd_scale 4.5) is in `reports/CORRECTION_drawn_lock_2026-09-23.md`, and `runs/TRACKING_FROZEN_2026-09-23h.json` records it as 53.33 percent held-out (`lock.SHIPPED_one_lattice`).

### Items A, B and C: DC2 dry run, real-time operation, and the A_fwd diagnostic

2026-09-22, evening. Standing brief `reports/BRIEF_render_and_prepress_2026-09-22.md`, open items
A, B and C. **Tracking is not closed; the backlog was empty, which is a different thing.**

---

#### The one finding that came from two directions

> **THE SHIPPED FIVE-HEAD POOL CANNOT BE REPRODUCED LIVE, AND MAY NOT BE REPRODUCIBLE ON DC2.**
>
> Three of its five heads are 1 s heads needing the 1 s window tree. A live stream produces one
> tree, so **a live demo runs single-head**. DC2 ingest must cut the room **twice** or its pooled
> figure is unreproducible too.

Item A's ingest check and item B's acceptance test found this independently, neither looking for
it. Both now name it and refuse to substitute a reduced-head configuration silently.

---

### Item A. The DC2 dry run

**One command**, tested end to end on a stand-in before any Room B exists:

```
python3 -m pipeline.constrained.dc2_pipeline --room room_B
```

Writes `reports/DC2_REPORT_<room>.md` and `runs/constrained/fh/dc2_pipeline/results.json`.

**`data/room_A` is never touched.** The room is a layout parameter, `TDR_ROOM`, added to
`recordings.py` with a default that leaves every existing caller bit-identical — which the suite
proves at 966 tests.

#### What it does

| step | |
|---|---|
| 0 | **ingest check**: which window trees exist, and what their absence costs |
| 1 | **manifest**: calibration, aborted and evaluated passes, written at capture time |
| 2 | **the three calibration numbers** that must be printed beside every DC2 figure |
| 3/4 | **re-anchored gate and null** from the calibration block |
| 5/6 | **primary arm** `b_abstain_0.25`, plus the exploratory arms |
| 7 | the tables the pre-registration promises |

**The manifest is a hard error if absent.** The pipeline will not guess which passes were
calibration. **"Calibration passes are never scored" is asserted**, not trusted: on the stand-in,
6 recordings, 48 calibration passes, 72 evaluated, assertion passed.

#### Two defects the dry run found before capture

**1. One window tree is not enough.** Detected, reported, and the fix printed:

```
python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_w1   --stride 1.0
python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_half --stride 0.5
```

**2. The re-anchored gate came out at 0.871, outside the [0.20, 0.60] region measured flat on
Room A.** Cause: the stand-in has no standing block, so the "still" end of the bracket fell back to
idle windows, which in Room A are setup activity rather than stillness. **A guard now falls back to
the absolute value and prints "CHECK THE STANDING BLOCK".** On DC2 night that is exactly the
distinction between a bracket fault and an unusual room.

#### Honestly outstanding

The arms are **wired but cannot execute without per-room inference**, and **within-DC2 cross-day
additionally needs heads trained on DC2 day 1**, which cannot be pre-built. Both are stated in the
generated report rather than left to be discovered.

**Every stand-in table is stamped PLUMBING CHECK, NOT RESULTS**, and the report refuses to omit
the stamp.

---

### Item B. Real-time operation

```
python3 -m pipeline.realtime.tracker_live --session 03 --stem participant_PA5_TEST_walk
```

Reuses `pipeline/realtime/engine.py` for the streaming contract and `pipeline/io/` **read-only**.
Neither is edited.

#### The acceptance test PASSES

| | |
|---|---|
| **decision equality, live against offline** | **20 of 20 passes, exact** |
| lattice alignment | offset from the absolute lattice **0.000000 s** |
| compute per window | median **14.7 ms**, p90 16.4, max 17.0 |
| **headroom per 0.5 s stride** | median **34x**, worst **29.5x**, meets budget |

The two questions are kept apart on purpose: **decision equality** isolates the tracker given
identical windows; **lattice alignment** asks whether the engine's own windows land where the
stored tree's do. Reporting one number for both would hide which failed.

**The feared lattice mismatch does not exist.** The stored tree sits exactly on the absolute
lattice the engine cuts on.

#### The 7-of-8 "failure" was my test, not the tracker

My offline helper read `lo + commit_w + LAG_W` — **two windows more** than the live lock sees — so
I compared decisions taken on different evidence and called the difference a live-path defect.
Aligning the horizon made all 20 agree.

**That is the same evidence-horizon fault class as the +20.5 s look-ahead exit and the −0.000 s
causal bound**, reproduced by me inside a harness written to catch exactly that.

#### Two structural gaps, stated rather than worked around

**The engine carries amplitude only; the shipped heads take two channels, CSI and RSSI.** The
branches the engine was built for do not use RSSI, so the runner keeps its own RSSI buffer
alongside. That is why it wraps the engine rather than being handed to it as a `Predictor`.

**The equality is live-versus-offline SINGLE-HEAD**, for the pool reason at the top of this
document. A live demo in Room B would run a different configuration from every offline figure
until that is resolved.

#### Not done

A live run on the rig. The replay path is the acceptance test and it passes; hardware was not
exercised.

---

### Item C. The A_fwd diagnostic: HYPOTHESIS REFUTED

`v1_afwd`, 360 passes. RX2/RX3 posterior agreement per pass, one minus total variation distance.

| | RX2/RX3 agreement | RX1-to-side |
|---|---|---|
| **A_fwd** | **0.1894** [0.158, 0.218] | **0.1419** |
| **A_rev** | **0.1826** [0.156, 0.210] | **0.1267** |
| other ten lines, mean | **0.2388** | ~0.24 |

**The hypothesis predicted A_fwd would show HIGHER agreement** — RX2 and RX3 being mirror images
about the TX-RX1 axis and so unable to tell left from right along it. **The A lines have the
LOWEST agreement of the twelve.** The stated mechanism is not present.

**The second control sharpens it.** RX1-to-side agreement is also distinctly low on the A lines,
0.1419 and 0.1267 against ~0.24. On the A lines *all three* links disagree more than usual, the
opposite of the degeneracy the hypothesis describes.

**The control that decides it:** A_fwd and A_rev are nearly identical, 0.1894 against 0.1826,
**while one is over-drawn at 1.95 and the other under-drawn at 0.61** (NON-CAUSAL lock figures; **causally 2.61 and 0.565**, `reports/CORRECTION_causal_lock_2026-09-23.md`). Whatever distinguishes them
is not in the link relationship at all.

> **VERDICT: the A_fwd over-draw is an OPEN DEFECT with no surviving hypothesis.** It is not a
> physical limitation of the node layout on this evidence. The TX-proximity hypothesis is
> withdrawn. **Do not re-propose axis symmetry without new evidence: it has been measured and it
> fails.**

Better than confirmation would have been: an over-draw attributed to fixed geometry would have
been written off as unfixable, and it now stays on the defect list where it can be chased.

**What it does not establish**, stated in the stage's own output: agreement between two links is
not a cause. Even the supporting branch would have shown only consistency, never production.

---

#### Faults of my own in A, B and C

| fault | effect |
|---|---|
| offline helper read two windows more than the live lock | a **false FAIL** at 7 of 8, blamed on the live path |
| the live runner tripped the pass-id guard | suite red on my own code; registered rather than reported green |

#### Where the numbers live

`runs/constrained/fh/dc2_pipeline`, `live_tracker`, `v1_afwd`.
Code: `pipeline/constrained/dc2_pipeline.py`, `pipeline/realtime/tracker_live.py`,
`pipeline/constrained/v1_afwd.py`. Suite 966 passed, 8 skipped.

---

## RENDER_DOTPHASE_2026-09-22.md

**Source:** `reports/RENDER_DOTPHASE_2026-09-22.md`, 2026-09-22, late. **SHA-256:** `7e928e5811b7cabebc57bac666e575196e2fb58a4b758248d1193cb034aa3232`. **Original combined here** on 2026-09-24.

> **Superseded:** The render changed after this report (freezes 23a to 23g: the ONE lattice, mid-walk switching, the end text). Its current measurements are in `runs/TRACKING_FROZEN_2026-09-23h.json` (`render_2026_09_23f`) and `runs/constrained/demo/ACCEPTANCE.md`.

### The drawn dot: why it leads, why it starts out, and what is actually wrong

2026-09-22, late. Operator report: the red dot leads the green marker, does not start at the start
of the path, is sometimes a metre out, and the display feels less accurate than it was.

Pre-registration and full result table: `reports/PREREG_dotphase_2026-09-22.md`.
Stage `pipeline/constrained/w1_dotphase.py`, nine pairings, 1078 passes, five phases each.

---

#### Verdict

> **NOTHING SHIPS. THE RENDER IS UNCHANGED**, and the reproduction check proves it is unchanged
> rather than asserting it: `shift_w = 1.00` reproduces the shipped drawing on **100.00 percent of
> 42,267 frames**.
>
> **The phase is not the defect.** The shipped dot is **centred at +0.046 m** and ahead on **52.8
> percent** of frames. There is no systematic lead to remove.

Three of the four things reported are real and measured. None of them is fixed by moving the dot,
and one of them is not a change at all.

---

#### 1. "Is it tracking a green dot two seconds ahead?" No, and this is certain

The video's marker is `green_at(tq) = truth_at(tq - 2.0 s)` and the red dot is drawn from the
decode for that same delayed instant, indexed from `park_until = scene_start + 2.0 s`. **Both are
delayed by the identical 2.0 s.** You are not watching a live marker beside a delayed dot; that
display was tried and retired on 2026-09-20 for exactly the reason it reads as error when it is
latency.

#### 2. The lead was real in the code, and it is defensible in the data

**`lead=True` is a permanent +1 stride phase shift, not the start-only fix it was added as.**
`render_display.simulate_walk` under `lead=True` interpolates from `pts[i_max]` towards
`pts[i_max+1]` rather than from `pts[i_max-1]` towards `pts[i_max]`, on every frame. It entered in
freeze `2026-09-20b` to cure a start stall under rule 6, and it cures it by moving the whole walk
forward about 0.65 m.

**It had never been measured.** `s2_display`, the nine-pairing stage that CHOSE the display arm,
calls `simulate_walk` with the default `lead=False`; `f3_render` draws with `lead=True`. **Every
nine-pairing display figure this project has quoted describes a dot nobody has watched.** That is
now fixed by measurement rather than by argument.

`shift_w` makes the shift a swept parameter with the shipped render as one member:

| `shift_w` | within 0.5 m, correct line | 95 percent paired interval | signed mean | ahead on |
|---|---|---|---|---|
| 0.00 trailing | 44.77 | [-10.62, -3.30] | -0.588 m | 16.6 |
| 0.50 best by primary | **53.05** | [-0.98, 3.69] | -0.281 m | 33.5 |
| 0.75 | 52.83 | [-0.27, 2.58] | -0.118 m | 43.3 |
| **1.00 SHIPPED** | 51.63 | | **+0.046 m** | **52.8** |

**The best arm's interval straddles zero and it wins only 6 of 9 pairings**, so it fails the ship
rule on two independent conditions. And **the tie-break, written before any signed number existed,
selects the shipped render**: among the arms not separated from the best, `1.00` has the signed
offset closest to zero.

**So the honest answer to "the dot is ahead" is: it is ahead about half the time, because it is
centred.** What is being noticed is the excursions, not a bias. The only arm that leads less often
does so by sitting 0.28 m behind, which trades this complaint for the opposite one.

#### 3. The start gap is real, and it is the entry cell, not the phase

On the 87 correct-line walks of the demo pairing, measured at the first drawn frame:

| | |
|---|---|
| dot to marker at the first drawn frame | **mean 1.03 m, median 0.70 m, p90 1.64 m** |
| walks starting more than 0.75 m out | **47 percent** |
| signed, at the window centre | **+0.02 m**, ahead on 11 percent |
| signed, at the first drawn frame | **-0.30 m**, ahead on **9 percent** |

**The decoded entry cell is unbiased and noisy.** States sit 0.25 m apart, so quantisation cannot
account for more than 0.125 m of it. The dot starts **behind**, not ahead, on 91 percent of walks,
and the scatter is the decode.

**The phase does not cause it and cannot cure it:** the start gap is 0.615 m at every shift from
0.00 to 0.75 and **0.544 m at the shipped 1.00**, which is the best of the family. Moving the dot
back would make the start worse.

#### 4. "It used to be more accurate and closer." On the numbers, it did not

| freeze | pooled on-screen tracking, within 0.5 m |
|---|---|
| 2026-09-20a | 29.6353 |
| 2026-09-20b | 34.4601 |
| **2026-09-20c** | **40.0046** |
| **the current render** | **40.0046** |

**Bit-identical to the best it has ever been.** No tracking regression exists.

**But something visible did change, and it is worth naming.** The playback latency went from
**1.0 s to 2.0 s** at V1 on 2026-09-22. That is a uniform delay on both dots, so it leaves the
red-to-green gap mathematically untouched, which is why no metric moved. What it does change is
that **the dot now sits parked at the room centre for 2 s at the start of every walk instead of
1 s**, and the whole video sits twice as far behind the world. That reads as less responsive
without a single number moving, and it is the most likely source of the impression.

#### 5. What is actually wrong, and it is not the render

Over nine pairings the dot is locked to the **correct line on 517 of 1078 walks, 48 percent**. On
the other 52 percent the dot is on a different tape and tracks it faithfully at over 2 m. **That is
the "running away", and it is a line error, not a tracking error.** V3 forbids confidence-gated
latency, so the dot commits at 2.25 s on every walk whether the evidence is good or not, and never
switches. The render is executing that rule correctly.

**On the walks where the line is right, the dot is within 0.5 m on 51.6 percent of frames and
centred to within 5 cm.** That is the display working.

---

#### Faults of my own in this batch

| fault | effect |
|---|---|
| built the sweep on `s2_display`'s convention, `display_paths` with `lag_w=2`, instead of the renderer's locked path with `lag_w=0` from `park_until` | measured a dot a **full second behind** the drawn one and reported **-1.0 m of lag where a lead was reported**. Caught by the reproduction check at 59 percent |
| keyed the pairing on `session\|stem\|pass_id` | session 02 is the test fold in several pairings, so half the comparisons **paired a walk against another pairing's copy of itself**. Caught by the reproduction check at 50 percent, and the repo's own `test_cross_pairing_key` then refused the file until it was registered |
| pre-registered condition (c) as a **monotone** response | a phase has an interior optimum, so **no phase arm could ever satisfy it**. Disclosed POST HOC in the pre-registration; it changes nothing because (a) and (b) fail independently |

**The reproduction check was pre-registered and it earned its place twice.** Without it, the first
run's "-1.0 m, the dot lags" and the second run's numbers would both have been reported as answers
to a question about a lead.

#### Where the numbers live

`runs/constrained/fh/w1_dotphase/results.json`, `reports/FINDINGS_stagew1dotphase.txt`,
`runs/constrained/logs/w1_dotphase.log`. Pre-registration and outcome
`reports/PREREG_dotphase_2026-09-22.md`. Suite 969 passed, 8 skipped.

---

## ACCURACY_STATE_2026-09-22.md

**Source:** `reports/ACCURACY_STATE_2026-09-22.md`, 2026-09-22. **SHA-256:** `526beab18e4a5164c0188de5a34065af6d12177f017e7ed6aa3d01e06c489f93`. **Original combined here** on 2026-09-24.

> **Superseded:** The causal lock figures that batch 23c added beside the originals decoded the display at sd_scale 1.0; the lock the render actually draws (sd_scale 4.5) is in `reports/CORRECTION_drawn_lock_2026-09-23.md`, and `runs/TRACKING_FROZEN_2026-09-23h.json` records it as 53.33 percent held-out (`lock.SHIPPED_one_lattice`).

> **Superseded:** 62.50 percent remains the PRE-REGISTERED headline. The post-amendment headline is 73.33 percent [35.00, 87.50] from freeze 23d onward (`runs/TRACKING_FROZEN_2026-09-23h.json`, `headline_semibounded`).

### Where the model actually sits: accuracy, and whether it is CSI

2026-09-22. Written at the close of building. Nothing here is new work: every figure is read back
from the frozen runs and named with the measurement that produced it. Where two measurements of the
same thing disagree, both are printed and the disagreement is called an open item rather than
resolved in the flattering direction.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes.**

Standing brief `reports/BRIEF_render_and_prepress_2026-09-22.md`. Freeze
`runs/TRACKING_FROZEN_2026-09-22b.json`.

---

#### 1. The headline, and the three numbers that are not it

**62.50 percent.** Semi-bounded, cross-day, nine pairings, per-pairing difference of medians.
Chance is 8.33 percent on twelve lines. Bounded is 65.83 percent, so **granting the walk's end
press is worth 3.33 points against a 10 point bar**: the decoder finds its own end nearly as well
as being told it.

Three numbers get quoted at this project by mistake, so they are named here:

| not the headline | value | why not |
|---|---|---|
| the demo pairing | **78.3 percent** committed | `s0102_to_s03` is the **strongest of the nine** and is not typical. The nine-pairing aggregate of the same measurement is **65.8** |
| "either drawn or committed right" | 89.2 percent | an after-the-fact oracle. It is never headroom |
| the retired 64.17 | 64.17 percent | produced by an exit search with a **+20.5 s look-ahead**. Not a live figure at any value |

**The live mode's own figure, its own end, over nine pairings, is 57.5 percent.** That is the
number a live rig would produce, and it is lower than the headline because the headline's
difference-of-medians convention is not the same estimator.

##### What the system is at each moment of a walk

| moment | demo pairing | nine pairings |
|---|---|---|
| the 2 s lock, shipped estimator (`t6_lockdiag`) | | **49.2** all nine, 60.8 held-out seven (NON-CAUSAL; **57.50 causally**, the figure that stands) |
| the line actually drawn at 2.0 s, fixed-lag Viterbi (`r5_timeline`) | 70.8 | **27.5** |
| the committed answer, whole walk, bounded rescore | 78.3 | **65.8** |
| the committed answer, semi-bounded, own end | | **62.5** |

> **OPEN ITEM, and it is the most important line in this table.** Two measurements of "correct line
> at the 2 s lock over nine pairings" read **49.2** and **27.5**. They use different estimators, the
> lock's best-path state against the drawn fixed-lag Viterbi path, and nobody has reconciled them.
> **Until that is done, the honest statement about the demo's lock is that it is somewhere between a
> quarter and a half correct on a typical pairing, against 72.5 percent on the demo pairing.**

**The demo pairing overstates the lock by roughly 20 to 45 points.** That is the single largest
gap between what the videos show and what the system is.

##### Per line, on the demo pairing only

| line | n | correct at the 2 s lock | correct at commit |
|---|---|---|---|
| A_fwd | 12 | 100.0 | 75.0 |
| A_rev | 12 | 50.0 | 83.3 |
| B_fwd | 12 | 66.7 | 41.7 |
| B_rev | 12 | 91.7 | 50.0 |
| C_fwd | 12 | 66.7 | 91.7 |
| C_rev | 12 | 75.0 | 91.7 |
| D_fwd | 12 | 58.3 | 91.7 |
| D_rev | 12 | 50.0 | 100.0 |
| **E_col1** | 6 | **50.0** | **50.0** |
| **E_col5** | 6 | 100.0 | 100.0 |
| **E_row1** | 6 | 83.3 | 83.3 |
| **E_row5** | 6 | 100.0 | 83.3 |

**Read the edge lines, never the pooled figure alone.** On nine pairings the shipped lock holds
E_col1 at 50.0 (NON-CAUSAL; **42.59 causally**), and `reports/FINDING_pooled_vs_edge_2026-09-22.md` records that **every arm that
raised pooled accuracy destroyed them**: `E_both` bought +10.00 points [2.02, 11.55] while taking
E_col1 from 50.0 to **7.4** (NON-CAUSAL; **causally +4.17 [0.71, 8.57], E_col1 42.59 to 0.00**). It was refused. The pooled number this project could have quoted is
about ten points higher (causally about five) than the one it does quote, and the difference is the edge lines.

**Two line-level defects are open.** A_fwd is over-drawn at 1.95 (NON-CAUSAL; **2.61 causally**) under every estimator, and its one
hypothesis was **measured and refuted** this evening: A_fwd's RX2/RX3 link agreement is 0.1894
against 0.2388 on the other ten lines, the **lowest** of the twelve where the hypothesis predicted
the highest. Every diagonal is under-drawn, C_fwd at 0.44 (NON-CAUSAL; **0.54 causally**), because edge cells hold 0.6 to 1.0
percent of training mass against 16.5 at the centre and dividing by that marginal boosts edges by
about 3 nats.

---

#### 2. Is it fully CSI, or is it a motion model?

**It is CSI, and the reason to believe that is not the architecture. It is that the same test was
applied to four things that looked like signal and threw three of them out.**

The test: **swap in another participant's CSI and see whether the answer changes.** A component
whose answer does not move is reading something other than the radio.

| what it decides | substitution ratio, pool | single head |
|---|---|---|
| the walk's end time | **77.5 percent** | 80.0 |
| the line | **90.0 percent** | 90.8 |
| the shipped lock estimator | **97.1 percent** | |
| the pre-press region reader | 0.89 to 0.95 | |

Nine walks in ten change their line when the radio changes. Three in four change their end. **The
gate is absolute: an arm whose end-time substitution falls to 50 percent or below is out whatever
its line figure.**

##### What that gate actually threw out

| rejected | what it was | what the test showed |
|---|---|---|
| **`pinned_entry`** | fixing entry at a known state at a known time | end-time substitution **-12.5 points at 1 s, -32.5 at 0.5 s**. It bought 7.5 points of line accuracy and the gate took all of it back |
| **ramp extension** | drawing the segment ahead of the last decode | removing the CSI changed **0.0 percent** of the drawn path |
| **forward projection** | assuming the walker kept the pace just measured | the same: **0.0 percent** |
| **display speed cap at 2.0 m/s cross-line** | a motion constraint on the dot | cost on-screen tracking and could not satisfy the one drawing rule |

`pinned_entry` is the important one. It was a **higher-scoring configuration** and it was refused,
because the chain carries one sharp global duration prior, so pinning entry makes arrival at the
end partly a function of **elapsed time** rather than of the emissions. **The project has a number
it did not take because the number was partly a clock.**

Neither the ramp nor the projection was caught by code review, a coverage figure, or an exit code.
Both were caught only by substitution.

##### What honestly remains of a motion model

Not nothing, and it should be stated rather than defended:

- **A 25-cell transition structure and 288 chain states.** The geometry of the taped lines is prior
  knowledge, not decoded. The system knows twelve lines exist and that walkers traverse them.
- **A display step model**, 0.8 m per window, 1.6 m/s ceiling, used for **drawing only**. It is
  measured inert on the decision: implied traversal speed is a median 1.26 m/s with no pass above
  2.0 m/s, so a cap at 1.6 to 2.4 cannot bind.
- **A geometric safety timeout** at chain length over 0.5 m/s, so a pass can always end.

**The line identity, the position within the line, and the end are all decided by the radio.** The
prior supplies where the lines are, not which one you walked.

---

#### 3. Accuracy on the right tracks

**This is the split to read**, and it is the honest answer to how well the system tracks:

| | walks | frames | within 0.5 m | mean distance |
|---|---|---|---|---|
| **the dot locked to the RIGHT line** | 87 | 3346 | **51.5 percent** | **0.59 m** |
| the dot locked to the wrong line | 33 | 1437 | 8.6 percent | 2.26 m |
| pooled, as the acceptance file quotes it | 120 | 4783 | 38.6 percent | 1.09 m |

**When the system knows which line you are on, it is within half a metre about half the time, and
its mean error is 0.59 m.** On a 6 m line with 25 cells at 1 m spacing that is roughly half a cell.

**The pooled figure is not a tracking figure.** When the dot has committed to the wrong line, the
distance between the dot and the walker is the distance between two taped lines. That is a **line
error reported as a tracking error**, and pooling makes the tracking number a function of line
accuracy. The third row asks two questions at once and answers neither.

For completeness, the same split by the committed answer rather than the lock: 43.0 percent within
0.5 m at 0.99 m mean when committed right, 21.6 percent at 1.51 m when wrong.

**Where the render currently stands, measured:** 0 causality violations over 4783 frames, both
causal bounds at **-1.300 s**, 0 frames with no dot, exactly one line switch per walk and that at
the lock, 147 frame-to-frame jumps over 0.5 m of which **0 are caused by the lock**.

---

#### 4. Why the dot looks fast, and why it runs away

Two different things are happening, and only one of them is the tracker.

##### It runs away because the line is wrong, not because the tracking is bad

**On 33 of 120 walks the dot is on the wrong tape.** It then tracks that tape faithfully, at a mean
2.26 m from the walker, and what a viewer sees is a dot heading confidently somewhere else. **That
is the 2 s lock being wrong, not the tracker drifting.** Section 1 says how often: on the demo
pairing 27.5 percent of walks, and on a typical pairing very likely more.

**Nothing can fix this in the render.** V3 forbids confidence-gated or variable latency outright, so
the dot commits at 2.25 s on every walk whether or not the evidence is good, and it never switches
afterwards. That rule was chosen deliberately, and this is its price.

##### It looks fast because of a 1.25 m structural gap the display is chasing

| | measured against | value |
|---|---|---|
| decoded accuracy | the truth at the moment the centre-labelled pool names, t minus 1 s | 12.0 percent within 0.5 m, 1.68 m mean |
| on-screen tracking | the truth at the frame the viewer sees, t | 40.0 percent within 0.5 m, 1.04 m mean |
| **display offset** | how far the walker travels during the 1 s lag | **1.29 m mean** |

A window spans 2 s and can only be drawn once it has ended. The heads that decide the line are
labelled at the **window centre**, so they name t minus 1 s, while the viewer is watching t. The
walker has moved 1.29 m in between.

**The dot chases that gap, and chasing is what reads as speed.** The shipped display head DISP_END
is trained on the position at the window **end**, which is the honest attempt to close the gap from
the signal, and **it recovers about a quarter of it**: 2.087 m to 1.867 m over nine pairings. The
only thing that closes it completely is assuming the walker kept going at the pace just measured,
and that is dead reckoning. It was deleted on 2026-09-20 and it is not coming back.

**It used to be much worse.** The dot ran ahead of the walker on **72 percent of frames**, by more
than half a metre on 46, with a speed p90 of **2.50 m/s against the walker's 1.53**. The display cap
at 0.80 m per window, 1.6 m/s, took within-0.5 m from 33.0 to 40.0 percent and ahead-by-half-a-metre
from 46 to 34 percent. **So the dot is still ahead by more than half a metre on about a third of
frames.** That is what is being seen, it is measured, and it is structural rather than a bug.

**In one sentence: the dot is fast because it is 1.29 m behind in time and closing, and it runs away
when the line under it is wrong.**

---

#### 5. The three things that would change these numbers, none of them built

1. **The pool cannot be reproduced live.** Three of its five heads need the 1 s window tree; a live
   stream produces one tree, so **a live demo runs single-head**, and DC2 must cut the room twice or
   its pooled figure is unreproducible. Found independently by the DC2 ingest check and the
   real-time acceptance test, neither looking for it.
2. **The 49.2 against 27.5 discrepancy in section 1.**
3. **The A_fwd over-draw is an open defect with no surviving hypothesis.** Do not re-propose axis
   symmetry: it has been measured and it fails.

The real-time runner passes its acceptance test, **20 of 20 passes decision-identical to offline**,
median 14.7 ms per window against a 0.5 s stride, **34x headroom**. It has never been run on the
rig.

---

#### Where the numbers live

`runs/TRACKING_FROZEN_2026-09-22b.json`, `runs/constrained/fh/f3_render/results.json`,
`r5_timeline`, `t6_lockdiag`, `t7_lockarms`, `v1_afwd`, `runs/constrained/demo/ACCEPTANCE.md`.
Contract `reports/RENDER_RULES.md`. Suite 966 passed, 8 skipped.

---

## BATCH_2026-09-23_REPORT.md

**Source:** `reports/BATCH_2026-09-23_REPORT.md`, 2026-09-23. **SHA-256:** `138b1445d4be34c312b508f28f2fc0c554d2bbb4f30434196acb2cc6cb70edba`. **Original combined here** on 2026-09-24.

> **Superseded:** Every 2 s lock figure in this report predates the causal correction and is NON-CAUSAL and SUPERSEDED: `reports/CORRECTION_causal_lock_2026-09-23.md`, then The causal lock figures that batch 23c added beside the originals decoded the display at sd_scale 1.0; the lock the render actually draws (sd_scale 4.5) is in `reports/CORRECTION_drawn_lock_2026-09-23.md`, and `runs/TRACKING_FROZEN_2026-09-23h.json` records it as 53.33 percent held-out (`lock.SHIPPED_one_lattice`).

> **Superseded:** On-screen tracking of 41.66 percent is superseded by 45.30 percent in the 23e and 23f renders (`runs/TRACKING_FROZEN_2026-09-23h.json`, `render_2026_09_23f.on_screen_within_pct`).

> **Superseded:** 62.50 percent remains the PRE-REGISTERED headline. The post-amendment headline is 73.33 percent [35.00, 87.50] from freeze 23d onward (`runs/TRACKING_FROZEN_2026-09-23h.json`, `headline_semibounded`).

### Batch report, 2026-09-23. Three items: the edge, the display head, the pool head

> **Terminology corrected 2026-09-23 (batch 23c):** g100 is a 100-cell REGION posterior head ("g" is the grid kind, 100 the cell count), not a motion gate. Earlier text here called it "the gate head" and has been corrected; the JSON keys `gate_head_g100` and `g100_gate` are kept as identifiers and mean the same region head.

Standing brief `reports/BRIEF_render_and_prepress_2026-09-22.md`. Contract
`reports/RENDER_RULES.md`. Queue `reports/QUEUE.md`. **Tracking is never closed.**

> **STATUS: item 1 DONE and frozen. Items 2 and 3 running. This file is written as they land and
> is not complete until the closing section says so.**

---

### Item 1. START TOGETHER, AT THE EDGE. **SHIPPED**, frozen `runs/TRACKING_FROZEN_2026-09-23a.json`

**Nothing in the decision changed. The 62.50 headline is carried, not re-measured**, and the freeze
records it as carried in those words.

#### What the operator decided, and what it measures at

| rule | decision | measured on the shipped render |
|---|---|---|
| **6, amended** | the scene starts at the **delayed press moment**; red and green appear on the same frame; the 0.45 s gap is removed | **0 violations, max gap 0.000 s over 120 walks** |
| **2a, new** | at the press the dot is placed at the **entry point of the committed line** | **573 anchor frames, 0 off the segment** |
| **2b, new** | the start gap is a **display rule**, never a tracking result | tracking measured from the first decoded position onward, declared per walk |
| **V3, amended** | the lock offset is **exactly 2.0 s** | **2.0 s, one distinct value over 120 walks** |
| **V5, new** | the display phase is **`shift_w` = 0.50** | 0.50, a single global constant |

#### The start gap is zero, and it is an identity rather than an achievement

| | walks | mean | max |
|---|---|---|---|
| **correct committed line, by construction** | 87 | **0.000 m** | **0.000 m** |
| correct line, at the first DRAWN frame | 87 | 0.050 m | 0.183 m |
| **wrong committed line** | 33 | **2.904 m** | 5.590 m |

The first row is zero because the press IS the walker at the tape entry and the dot is placed
there. **Quoting it as tracking accuracy would be quoting an identity**, which is why rule 2b
exists and why tracking is measured from the first decoded position onward. The second row is the
same quantity with up to one frame of grid quantisation in it, which is what a viewer actually
sees. **The third row is a wrong line starting at the wrong line's entry, and it is shown.**

#### Where the 0.45 s went

It was never one thing. **0.202 s** was the fixed 0.5 s window lattice not aligning with the press,
and **0.25 s** was a 2 s window having to finish recording while the display head names a moment
0.75 s behind its end. Both are properties of the lattice rather than of the walker. **The origin
is now the press, which is a physical event, so V3's offset is exact rather than merely identical
to six decimals.**

#### The render's own honesty checks, rule 5

| | |
|---|---|
| the one rule, decoded segment | **0 violations over 4783 frames** |
| frames without a dot | **0 of 21926** |
| drawn-window causal bound | **-1.300 s** |
| evidence causal bound | **-1.300 s** |
| jumps over 0.5 m | 144, **of which 120 at the lock** |
| dwell footage | 29,165 frames removed, **0 remaining inside a grid block** |
| on-screen tracking | **41.66 percent** within 0.5 m, mean 1.036 m, over 4783 frames |
| suite | **984 passed, 8 skipped** at the freeze |

**Tracking rose from 40.0046 to 41.66 percent.** 40.0046 was the figure at freeze `20c` and again
at `22b`, bit-identical, so this is the first movement in that number since 2026-09-20.

#### A mis-attribution fixed in passing

**Jumps at the lock now read 120 of 144. They read 0 before, and the lock jump was always there.**
The attribution window was anchored on the window centre and tested a crossing of `DELAY`, but the
jump happens at the commit, 0.25 s later, so it never matched. Moving the origin onto the press
made the test find what it had always been looking for.

#### THE RULE I CHANGED AFTER SEEING DATA. It is POST HOC and it is recorded in those words

Rule 2a's anchor made the dot **hold still at the start of 95 of 120 walks, for up to 0.9 s**. That
is exactly the fault rule 6's stall clause was written to catch, so it was measured before anything
was changed.

> **On 95 of 120 walks the decoder's own first decoded position IS the tape entry.** Mean distance
> 0.21 m, median 0.00 m. **95 and 95: the correspondence is exact.**

The dot holds because **the decoder says the walker has not moved**, not because the display is
interpolating backwards. The clause is therefore **scoped, not dropped**: a stall is a violation
when the dot holds *longer than the decoder accounts for*. The render now reports
`stall_explained_by_the_decoder`, which reads **120 of 120**, beside `max_stall_s`, so a display
fault and an honest hold can never again be one number. The original fault is still caught: a dot
that holds while the decodes underneath it differ still fails.

**The honest reading of that 95 is a DECODER result, not a display one.** On four walks in five the
decoder cannot yet tell the walker has left the entry. **Item 3 is aimed at precisely that**, which
is the one place in this batch where the three items touch.

#### Tests added

`test_v3_the_lock_offset_is_exactly_two_seconds`,
`test_2a_the_first_drawn_position_is_the_committed_lines_entry`,
`test_2a_the_anchor_segment_is_straight_and_uses_no_pace`,
`test_2b_tracking_excludes_the_anchor_segment`,
`test_v5_the_display_phase_is_a_single_global_constant`.

The anchor test has two halves on purpose. The measured half proves the drawn frames lie on the
segment; the source half proves the interpolation parameter is an elapsed fraction and not a speed.
**A measurement of positions on a straight line cannot tell those apart**, because a dot moving at
a fitted pace along that same segment would also lie on it.

---

### Item 2. BETTER EARLY TRACKING. **The rule says keep. I am not re-rendering on it, and that is a judgement I am flagging rather than burying**

Nine pairings, 1077 passes, three arms. `runs/constrained/fh/x1_edgedisp/results.json`.

#### What was added to the training set

A window is tagged `walk_edge` when its CENTRE falls outside the pass, so a window that begins
before the press and ENDS inside the walk was discarded. For an END-labelled head those windows
carry a real label: the tape position at the window's end, a moment at or after the press.
**Exactly two per pass, 480 per pairing, a 28 percent larger training set.**

**No pre-press position is ever labelled.** The end-time filter requires the labelled moment to lie
between the two presses. This is the distinction `dataset.py`'s existing `TDR_END_LABELS`
mechanism gets wrong: that one labels windows whose CENTRE is BEFORE the press with the entry
position, asserting the walker was at the tape entry while still approaching it. **Four stages
enable it. No stage in this batch does, and every stage here asserts it is off.**

#### The result

| arm | whole-walk within 0.5 m | correct-line within 0.5 m | mean distance | signed | paired vs shipped |
|---|---|---|---|---|---|
| shipped | **28.246** | **53.105** | 1.501 m | -0.287 m | |
| **base_retrained**, the control | **28.246** | **53.105** | 1.501 m | -0.287 m | **+0.0000 [0.000, 0.000]** |
| **edge** | **27.518** | **51.394** | 1.518 m | -0.366 m | **-0.7277 [-1.810, +0.347]** |

**The control returns EXACTLY zero, not merely a small number.** The same head on the same windows,
refitted into a separate file with the same seed, reproduced the shipped head in every digit.
Training is deterministic. **That is worth more than it looks: the entire edge-versus-shipped
difference is attributable to the training data and nothing else, with no refit noise to argue
about.**

**The committed and semi-bounded answers are identical across all three arms, 1080 passes checked.**
A display head that moved the decision would not be a display head.

#### The decision, and where my own rule was too weak

**The pre-registered bar was non-inferiority: keep unless the paired interval lies entirely below
zero. It does not, so the rule returns KEEP.**

**But the point estimate is negative on both measures**, -0.73 whole-walk and -1.71 on correct-line
walks, and the dot sits further behind, -0.287 to -0.366 m. **"Not shown to be worse" is not the
same as "no worse", and the bar I wrote cannot tell those two apart.** An interval of
[-1.81, +0.35] would have returned KEEP for almost any arm that did not collapse.

> **SO THE HEAD IS KEPT ON THE RULE AND THE RENDER IS NOT REBUILT ON IT.** Re-rendering would ship
> a change whose best estimate is a small loss. **This is a judgement made after seeing the data
> and it is POST HOC in those words**; it is made in the direction that does NOT ship, and the
> re-render is put to the operator rather than taken unilaterally.

#### The gap in my own design, stated plainly

**The arm was aimed at the first second of the walk and judged on the whole walk.** Whole-walk
within 0.5 m was the operator's own stated bar, so the bar is not wrong, but it cannot see an arm
that improves the opening and costs the rest. **An early-window split was never measured**, and
`x1_edgedisp` saved aggregates rather than per-pass rows, so it cannot be recovered without a
re-run. **That is a gap in what I built, not a property of the result**, and the early-versus-late
split is the first follow-up.

---

### Item 3. PATH IDENTIFICATION ARM. **REFUSED. A measured negative, and nothing changed**

Pre-registration `reports/PREREG_edgeheads_2026-09-23.md`, with four amendments all written before
any arm ran. Nine pairings, 1080 passes, three arms.

#### What was actually tested, stated before the numbers

**ONE HEAD OF FIVE.** The three 1 s seeds and the g100 region head are frozen weights from
`runs/artefacts/models` that `fh_ensprep` only infers. Retraining them needs a 1 s feature cache,
and the cache filename does not carry the stride, which that module's own docstring records as able
to **corrupt 6.3 GB of the shipped tree**. Not attempted unattended. So this arm is the pool with
its **0.5 s head** retrained and the other four untouched.

**AND THE LOCK NEVER READS THE WINDOWS THAT WERE ADDED.** Measured over all 360 passes before the
arm ran: **720 entry-straddling windows, 2.00 per pass, and all 720 sit strictly below the
decoder's first window `lo`. Zero fall inside the lock's own range.** They are always exactly one
index below it. So the arm could only ever act through the weights, never by putting new evidence
in front of the lock.

#### The verdict

| arm | 2 s lock | semi-bounded | paired lock vs shipped | median per pairing |
|---|---|---|---|---|
| shipped | 47.87 | 59.54 | | |
| **base**, the refit control | 47.87 | 59.44 | **+0.0000 [0.000, 0.000]** | 0 passes |
| **edge100** | **46.02** | 60.19 | **-1.8519 [-3.519, -0.278]** | 0 passes |

> **SHIPS: FALSE.** The paired lock interval is **entirely BELOW zero**. The arm is not merely
> unhelpful, it is **measurably worse on the thing it was aimed at**.

| condition | result |
|---|---|
| (a) paired interval entirely above zero | **FAIL.** It is entirely below zero |
| (b) median at least two passes per pairing | **FAIL.** 0 passes |
| (c) monotone response to the amount of edge data | **not reached.** Only an arm satisfying (a) and (b) reaches it. **A null here is a refusal before (c) mattered, never (c) waived** |
| substitution | **NOT MEASURED.** See the fault below |
| (f) no edge line degraded | **FAIL.** E_col5 77.8 to 75.9, **-1.9 points** |

**The reproduction check passed exactly** before any of this was read: the `shipped` arm returned
**49.1667** and **62.5000** on the median reading against `t6_lockdiag`'s identical figures, delta
**+0.0000** on both, over nine pairings.

**The no-op check passed on all nine pairings.** Training counts 1296, 1296, 1315, 1315, 1329,
1329, 2644, 2625, 2611, each matching the value pinned before the arm started, against `base`
values 240 or 480 lower. **A zero from this arm would have been a real null; it is not even that.**

#### The two readings disagreed, for the third time in this project

**Median of the per-pairing deltas: +0.00 points, 0 passes. Paired delta over 1080 passes: -1.85,
interval [-3.52, -0.28], excluding zero.** The median says flat; the paired reading says
significantly worse. `SEMIBOUNDED_STATE.md` section 10 requires both to be printed precisely
because they have now disagreed three times. **Across four consecutive check-ins the running median
read -2.50, -1.25, 0.00 and 0.00 as folds arrived**, which is why no call was made until all nine
were in.

#### The refit control is the most useful number here

**Refitting the 0.5 s head moved the 2 s lock on 0 of 1080 passes.** Not one. So the -1.85 points
is the training data and nothing else, with no refit term to subtract.

**The same control moved 36 of 1080 individual semi-bounded answers, netting one pass.** An
aggregate that shifts by a pass is hiding 36 that moved. **That is why the +0.65 semi-bounded
figure is not quoted as a gain here**: on that measure the refit noise alone is larger than the
effect.

#### A fault of mine, found while reading the verdict

**The substitution gate did not run, and my evaluator scored the missing measurement as a pass.**
`x2_edgepool` called `night_track` with `alt_e=None`, so `subs_end_changed` is null on every pass,
and the condition read `... is None or ... > 50.0` — a test that never ran satisfied the gate.

**That is precisely what this project's own standard forbids**: a component is signal-driven only
if another participant's CSI changes its answer, and coverage figures prove nothing. **An
unmeasured gate is a coverage figure wearing a verdict's clothes.** The condition now requires the
measurement to exist, `substitution_measured` is reported beside it, and the re-run returns the
same verdict because the arm fails (a), (b) and (f) independently. **No verdict turned on it, and
it would have on a closer arm.**

#### What this does and does not establish

**Establishes:** adding the entry-straddling windows to the 0.5 s head's training set makes the
2 s lock worse by about two passes per pairing and costs E_col5 nearly two points.

**Does NOT establish**, and the pre-registration said so before the run: that the idea is wrong.
**Four fifths of the pool was untouched**, and the lock never reads the added windows. This is
evidence about one head under one labelling choice, not about the edge.

**Not attempted and named as such:** `E2 edge_press`, the same windows labelled at the press rather
than the window end, dropped for cost; and retraining the 1 s heads, which needs a stride-keyed
feature cache built in isolation and someone awake.

---

### The per-fold table, and the edge lines beside every pooled figure

Measured on the SHIPPED pool by `x2_edgepool` arm `shipped`, nine pairings, 1080 passes. This
is the reference every item 3 arm is compared against, and it reproduces `t6_lockdiag` exactly
on the median reading: **49.1667** and **62.5000**, delta **+0.0000** on both.

| pairing | n | 2 s lock | semi-bounded |
|---|---|---|---|
| `s01_to_s02` | 120 | 49.2 | 62.5 |
| `s01_to_s03` | 120 | 45.0 | 50.0 |
| `s02_to_s01` **session-01 fold** | 120 | 25.0 | 30.0 |
| `s02_to_s03` | 120 | 57.5 | 85.8 |
| `s03_to_s01` **session-01 fold** | 120 | 25.8 | 25.8 |
| `s03_to_s02` | 120 | 60.0 | 75.0 |
| `s0203_to_s01` **session-01 fold** | 120 | 28.3 | 31.7 |
| `s0103_to_s02` | 120 | 67.5 | 86.7 |
| `s0102_to_s03` **the demo pairing** | 120 | 72.5 | 88.3 |

| **median of the nine** | | **49.1667** | **62.5000** |
| pooled over all passes | 1080 | 47.8704 | 59.5370 |

**Both readings are printed because they have disagreed in sign before.** The median is the
statistic every quoted figure in this project uses; the pooled reading sits 1.3 and 3.0 points
lower, and using one where the other is meant is how a sound harness gets declared void.

**The demonstration pairing is the best of the nine on both measures**, 72.5 and 88.3, which is
why no decision rests on it. **All three session-01 folds are the worst three on the lock**,
25.0, 25.8 and 28.3.

#### Per line, on the shipped pool over nine pairings

| line | n true | 2 s lock recall | semi-bounded recall | drawn/true at the lock |
|---|---|---|---|---|
| A_fwd | 108 | 97.2 | 85.2 | 2.62 |
| A_rev | 108 | 48.1 | 59.3 | 0.61 |
| B_fwd | 108 | 41.7 | 48.1 | 0.68 |
| B_rev | 108 | 57.4 | 62.0 | 0.75 |
| C_fwd | 108 | 29.6 | 39.8 | 0.54 |
| C_rev | 108 | 47.2 | 68.5 | 0.66 |
| D_fwd | 108 | 27.8 | 53.7 | 0.45 |
| D_rev | 108 | 23.1 | 44.4 | 0.37 |
| **E_col1** | 54 | **42.6** | 53.7 | **1.54** |
| **E_col5** | 54 | **77.8** | 74.1 | **2.74** |
| **E_row1** | 54 | **35.2** | 83.3 | **0.67** |
| **E_row5** | 54 | **57.4** | 57.4 | **1.70** |

**The edge lines are in bold and they are the reason condition (f) exists.** Every arm this
project has measured that raised the pooled figure did it by degrading them.


---

### Closing

#### What shipped

| item | outcome |
|---|---|
| **1. Start together, at the edge** | **SHIPPED.** Frozen `runs/TRACKING_FROZEN_2026-09-23a.json` |
| **2. Better early tracking** | **Kept on the rule, NOT rendered.** The head is retained; the render was not rebuilt on a negative point estimate, and that refusal is POST HOC |
| **3. Path identification arm** | **REFUSED.** A measured negative. Nothing changed |

#### Did the headline move?

**No. 62.50 percent stands, carried and not re-measured.**

Item 1 changed the render only and the freeze records the headline as carried in those words.
Items 2 and 3 did not ship, so there is nothing to re-measure. **The interval is therefore the one
already on record and no new interval is quoted**, because quoting an interval for a figure that
was not recomputed would imply a measurement that did not happen.

The one figure that did move is the render's own: **on-screen tracking 40.0046 to 41.66 percent**,
the first movement in that number since 2026-09-20, from V5's display phase and the anchor.

#### The checks that earned their place

**Three harness faults were caught tonight, none visible in any aggregate, all mine.**

| check | what it caught |
|---|---|
| reproduction check, `w1_dotphase` | a harness built on the wrong convention, measuring a dot a full second behind the drawn one |
| reproduction check, `w1_dotphase` | a pairing key not unique across the nine, silently pairing each walk against another pairing's copy of itself |
| reproduction check, `x3_edgeeval` | **my own check comparing a pooled rate against a median**, which would have declared item 3's sound harness VOID |

**And two crashes that would have landed at the end of a multi-hour unattended chain:** a list and
a `None` formatted with a width spec, both `TypeError`, found by testing the path rather than
reading it.

**And one gate that was passing without running:** item 3's substitution condition scored a missing
measurement as a pass. Fixed; no verdict turned on it.

#### Open, and carried forward

1. **Item 2's early-versus-late split was never measured.** The arm was aimed at the first second
   and judged on the whole walk, which was the operator's own bar, but a whole-walk figure cannot
   see an arm that improves the opening and costs the rest. `x1_edgedisp` saved aggregates rather
   than per-pass rows, so it needs a re-run. **First follow-up.**
2. **Item 2's re-render decision.** The pre-registered rule says keep; the point estimate is a
   loss. The render was not rebuilt and that call is the operator's.
3. **`E2 edge_press`**, the same windows labelled at the press rather than the window end. Dropped
   for cost, not answered.
4. **Retraining the 1 s heads and the g100 region head** needs a stride-keyed feature cache built in
   isolation. The cache filename does not carry the stride and the shipped tree is 6.3 GB.
   **Not an unattended job.**
5. **A_fwd is drawn 2.62 times as often as it occurs at the 2 s lock**, against D_rev at 0.37.
   The largest single distortion in the system, and its one hypothesis was refuted on 2026-09-22.
6. **E_row1 reads 35.2 percent at the lock and 83.3 percent on the committed answer.** The
   evidence is in the walk; the lock estimator cannot reach it in 2 s.
7. **On 95 of 120 walks the decoder's first decoded position is still the tape entry.** Four walks
   in five, it cannot yet tell the walker has moved. Item 3 aimed at this and failed.

**Tracking is not closed. The backlog is not empty.**

---

## DC2_REPORT_room_B_STANDIN_DECOYS.md

**Source:** `reports/DC2_REPORT_room_B_STANDIN_DECOYS.md`, 2026-09-23 17:23. **SHA-256:** `65483b7246c6860aee77847b35a8e51af912aaf3850b2fe473005202ec49ec3c`. **Original deleted** on 2026-09-24; this section is its home.

> **Superseded:** The current stand-in is the 22:39 run below; the decoy variant was not repeated after it.

### DC2 report: room_B (STAND-IN)

**STAND-IN, PLUMBING CHECK, NOT RESULTS**

Generated 2026-09-23T17:23:27, 7.26 min. Pre-registration: `reports/PREREG_DC2_crossroom_2026-09-22.md`, section 10. Heads `s0102_to_s03`, trained on Room A sessions 01, 02.

> **EVERY NUMBER BELOW IS A PLUMBING CHECK.** It says the path runs, not what it found.
> No figure here may be quoted as a result.

**The DC2 path against the SHIPPED path on the same passes (configuration A):** EXACT (72 of 72 decisions equal)

#### 0. Ingest

| | |
|---|---|
| raw recordings | 6 |
| cut | the ONE lattice (press-aligned 0.5 s), by this pipeline |
| within-DC2 training possible (1.0 s tree) | False |

> within-DC2 cross-day cannot train its 1 s heads until the 1.0 s cut exists: python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_s1.0_dc2 --stride 1.0 --sessions <Room B ids>

#### 0b. The receivers, by board

Tracking reads RX1, RX2 and RX3 by NAME, and each name was checked against the Room A tracking board's MAC: mismatches 0, swapped 0, unverified 0. Extra receivers present and never read by tracking: ['RX0', 'RX4'].

**Decoy receivers present:** True. **The exploratory fusion arm's plumbing against Room A's own measurement (z3a_linkprod_pa_w025):** EXACT (72 of 72).

#### 1. The primary comparison, per session and pooled (95 percent)

| session | n | A, unchanged | B, re-anchored | B minus A, paired | chance |
|---|---|---|---|---|---|
| B1 | 72 | 83.33 [75.00, 91.67] | 83.33 [75.00, 91.67] | +0.00 [0.00, 0.00] | 8.3 |
| ALL | 72 | 83.33 [75.00, 91.67] | 83.33 [75.00, 91.67] | +0.00 [0.00, 0.00] | 8.3 |

**Claim supported (B above chance with its interval): True.** Room A's pre-registered figure is 62.50.

#### 2. Edge lines, individually

| session | config | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|
| B1 | A | 33.3 | 100.0 | 100.0 | 100.0 |
| B1 | B | 33.3 | 100.0 | 100.0 | 100.0 |

#### 3. The confirmatory arms, each at 97.5 percent

| arm | paired points [97.5%] | passes, median per pairing | edge walks | amended (f) | CONFIRMED |
|---|---|---|---|---|---|
| `a_veto_1.0` (B against B without it) | -2.78 [-9.72, 2.78] | -2.0 | {'E_col1': 0, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0} | True | False |
| `b_abstain_0.25` (against B without the veto) | +0.00 [0.00, 0.00] | 0.0 | {'E_col1': 0, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0} | True | False |

#### 4. The three calibration numbers

| session | s_B | s_A | null (relative) | null used | fell back | gate theta |
|---|---|---|---|---|---|---|
| B1 | 1.951767541756978 | 2.111 | -6.934891931461792 | -6.934891931461792 | False | 0.431 |

#### 5. EXPLORATORY arms (batch 23e item 4). NOT confirmatory; no claim rests on them

Product link fusion, re-anchored at the PRODUCT's scale for the arm only (`TRACKING_FROZEN_2026-09-23e`). 95 percent intervals, reported, never tested.

| arm | fusion w | pct [95%] | n | s_B | s_A | null used | fell back |
|---|---|---|---|---|---|---|---|
| B_prod0.25 (B1) | 0.25 | 88.89 [81.94, 95.83] | 72 | 3.5506512738185165 | 3.7428177798574556 | -7.114929478253432 | False |

---

## DC2_REPORT_room_B_STANDIN.md

**Source:** `reports/DC2_REPORT_room_B_STANDIN.md`, 2026-09-23 22:39. **SHA-256:** `e3284493c165a4e2e10e49c9e568370e49f8780d273cfbd598af7b5f4873e7d1`. **Original deleted** on 2026-09-24; this section is its home.

### DC2 report: room_B (STAND-IN)

**STAND-IN, PLUMBING CHECK, NOT RESULTS**

Generated 2026-09-23T22:39:30, 5.37 min. Pre-registration: `reports/PREREG_DC2_crossroom_2026-09-22.md`, section 10. Heads `s0102_to_s03`, trained on Room A sessions 01, 02.

> **EVERY NUMBER BELOW IS A PLUMBING CHECK.** It says the path runs, not what it found.
> No figure here may be quoted as a result.

**The DC2 path against the SHIPPED path on the same passes (configuration A):** EXACT (72 of 72 decisions equal)

#### 0. Ingest

| | |
|---|---|
| raw recordings | 18 |
| cut | the ONE lattice (press-aligned 0.5 s), by this pipeline |
| within-DC2 training possible (1.0 s tree) | False |

> within-DC2 cross-day cannot train its 1 s heads until the 1.0 s cut exists: python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_s1.0_dc2 --stride 1.0 --sessions <Room B ids>

#### 0b. The receivers, by board

Tracking reads RX1, RX2 and RX3 by NAME, and each name was checked against the Room A tracking board's MAC: mismatches 0, swapped 0, unverified 0. Extra receivers present and never read by tracking: none.

**Decoy receivers present:** False. **The exploratory fusion arm's plumbing against Room A's own measurement (z3a_linkprod_pa_w025):** EXACT (72 of 72).

#### 1. The primary comparison, per session and pooled (95 percent)

| session | n | A, unchanged | B, re-anchored | B minus A, paired | chance |
|---|---|---|---|---|---|
| B1 | 72 | 83.33 [75.00, 91.67] | 83.33 [75.00, 91.67] | +0.00 [0.00, 0.00] | 8.3 |
| ALL | 72 | 83.33 [75.00, 91.67] | 83.33 [75.00, 91.67] | +0.00 [0.00, 0.00] | 8.3 |

**Claim supported (B above chance with its interval): True.** Room A's pre-registered figure is 62.50.

#### 2. Edge lines, individually

| session | config | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|
| B1 | A | 33.3 | 100.0 | 100.0 | 100.0 |
| B1 | B | 33.3 | 100.0 | 100.0 | 100.0 |

#### 3. The confirmatory arms, each at 97.5 percent

| arm | paired points [97.5%] | passes, median per pairing | edge walks | amended (f) | CONFIRMED |
|---|---|---|---|---|---|
| `a_veto_1.0` (B against B without it) | -2.78 [-9.72, 2.78] | -2.0 | {'E_col1': 0, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0} | True | False |
| `b_abstain_0.25` (against B without the veto) | +0.00 [0.00, 0.00] | 0.0 | {'E_col1': 0, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0} | True | False |

#### 4. The three calibration numbers

| session | s_B | s_A | null (relative) | null used | fell back | gate theta |
|---|---|---|---|---|---|---|
| B1 | 1.951767541756978 | 2.111 | -6.934891931461792 | -6.934891931461792 | False | 0.431 |

#### 5. EXPLORATORY arms (batch 23e item 4). NOT confirmatory; no claim rests on them

Product link fusion, re-anchored at the PRODUCT's scale for the arm only (`TRACKING_FROZEN_2026-09-23e`). 95 percent intervals, reported, never tested.

| arm | fusion w | pct [95%] | n | s_B | s_A | null used | fell back |
|---|---|---|---|---|---|---|---|
| B_prod0.25 (B1) | 0.25 | 88.89 [81.94, 95.83] | 72 | 3.5506512738185165 | 3.7428177798574556 | -7.114929478253432 | False |

---

# Part 2, added 2026-09-24

## FIGURES.md

**Source:** `reports/FIGURES.md`, 2026-09-18. **SHA-256:** `6cf54352b4c002931d2772c54f3975ca8d173e796cf806b5a8aa590f6a09370a`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** `reports/fig/architecture.png`, the figure it describes, shows the 2026-09-17 decoder (fixed lag 3, 3 s behind); it moved to `reports/attempts/fig/architecture.png` on 2026-09-24. The current figures are under `reports/figures/`.

### FIGURES, index of the canonical set

Written at phase 2.4 of the 2026-09-18 cleanup. The point of this file is that nobody has to guess
again which figure is current.

#### The thing to know first

**Neither current report embeds an image.** `TRACKING_2026-09-18.md` and
`IDENTIFICATION_2026-09-18.md` are text and tables throughout. So the canonical set is not "the
figures in the reports", it is the demonstration set plus the geometry inputs plus one architecture
diagram that a frozen artefact names. If you go looking for plots inside the reports you will not
find them, and that is not a cleanup error.

#### Nothing here is renamed, and each has a reason

The brief's scheme was `fig_tracking_<topic>_<date>.<ext>`. It is not applied, because every
canonical figure is pinned by name somewhere that renaming would break:

| figure | pinned by |
|---|---|
| `Layout.png`, `Paths.png` | opened by name in `pipeline/io/ground_truth.py`, which the brief forbids editing |
| `reports/fig/architecture.png` | named inside `runs/TRACKING_FROZEN_2026-09-17.json`, which must stay byte-identical |
| `runs/constrained/demo/*.png` | regenerated by the render each time, so the render defines the names |

Renaming any of them trades a working reference for a tidier filename. Not done.

#### Canonical figures

##### Geometry inputs, at the repository root

| file | what it shows | used by | produced by |
|---|---|---|---|
| `Layout.png` | the 5 by 5 m room, the 25 cell grid, and where the TX and the three RX nodes sit | `pipeline/io/ground_truth.py`; tracking report, geometry section | drawn by hand, part of the experiment design |
| `Paths.png` | the twelve taped straight lines walked by every participant | as above | drawn by hand |

These are **inputs to the truth system**, not outputs of a run. They are the only two images at the
repository root and they belong there.

##### Architecture

| file | what it shows | used by | produced by |
|---|---|---|---|
| `reports/fig/architecture.png` | the constrained decoder as a block diagram, CSI to link features to per-link CNN to fused emission to Viterbi over the twelve chains | named by `runs/TRACKING_FROZEN_2026-09-17.json` | `testing/pipeline_retired/pipeline/constrained/stage10_report.py`, retired there on 2026-09-18. Restore that module to regenerate it |

##### The demonstration set, `runs/constrained/demo/`

Thirteen videos, each with a poster frame of the same name. Regenerated in phase 5 from the single
render entry point, `scripts/render_demo.sh`.

| file | what it shows | produced by |
|---|---|---|
| `participant_<name>_TEST_walk_bounded.mp4` and `.png`, six of them | the boundaries-given mode, cross-day, trained on sessions 01 and 02 and tested on 03. Start and end of each walk are supplied, the line is not. Red is the decoder, green is truth. A cue fires on screen at the moment each walk is declared | `pipeline.constrained.rc8_demo` |
| `participant_<name>_TEST_walk_highlight.mp4` and `.png`, six of them | a 60 to 90 s selected excerpt per recording, three or four passes plus one transit period, captioned as an excerpt | `pipeline.constrained.rc8_demo` |
| `CONTRAST_uncalibrated_vs_calibrated.mp4` and `.png` | the live unbounded mode, uncalibrated beside calibrated, on one recording, with the enrolment caption. Secondary clip only: the live mode finds 4 of 120 passes cross-day and is not the headline | `pipeline.constrained.rc9_contrast`, folded into `rc8_demo` at phase 2.6 |

**Participant names in these filenames.** They are ethics code names, and the standing rule is that
they never appear in a filename that leaves `runs/`, in a figure caption, or in a report body. These
files are inside `runs/`, so the names are permitted where they sit. **If any of these videos is
sent to a supervisor, put in a thesis, or copied anywhere outside `runs/`, it must be renamed to the
participant index P1 to P6 first.** The index mapping is not written to this file, because a mapping
that leaves `runs/` is itself the identifying link.

#### Retired figures

`testing/figs_retired/` holds eight confusion matrices from 16 September:
`confusion_classifier_{cross,within}.png`, `confusion_decoder_{cross,within}.png`,
`confusion_decoder_entry2.0_{cross,within}.png`, `confusion_decoder_with_prior_{cross,within}.png`.
No current report references any of them, and they were produced by a retired stage. They are
superseded by the identification report's own tables, which carry the same information with the
within-day caveat attached.

---

## ETA.txt

**Source:** `reports/ETA.txt`, 2026-09-19. **SHA-256:** `b2574279d8496187f784817612f059bfd69311233c0610ef629ec20c9d855a2c`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

OVERNIGHT SEMI-BOUNDED, SECOND PASS, 2026-09-19: COMPLETE. All seven stages run.
Nothing is running. Life support stopped: caffeinate, heartbeat and watchdog all cleared.

THE VERDICT IS UNCHANGED: semi-bounded stays at 46.7 percent and does NOT become the core
mode, 11.7 points from bounded against a ten-point bar. Nothing shipped, renders untouched.

Start here: reports/SUMMARY_NIGHT.txt
Then:       "The live mode, second pass" at the end of reports/TRACKING_2026-09-18.md
Frozen at:  runs/TRACKING_FROZEN_2026-09-18h.json   (18g kept, see STATE.md)

---

## BRIEF_motion_and_lock_2026-09-20.md

**Source:** `reports/BRIEF_motion_and_lock_2026-09-20.md`, 2026-09-20. **SHA-256:** `90dec5cb05c508d04168c4244727da630e98ccaa847837a5266313924c05208c`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### BRIEF: the motion model, then park-watch-lock. 2026-09-20, second batch

Stored verbatim. Approved with B1 authorised as a gated decoder change, a confidently wrong locked
walk accepted as correct behaviour, and the ORDER CHANGED so B1 runs BEFORE the display stages:
the motion-model cap causes the frozen tails and the trailing, and every display parameter swept on
top of a capped decoder would be tuned to a defect that B1 then removes.

ORDER: stage 0, B1, A4, A1 to A3, A5, render, freeze.

#### STAGE 0
Re-verify from artefacts that committed line identification is 94 of 120 on `s0102_to_s03` and that
the nine-pairing semi-bounded figure is 58.3 with soft entry, before and after the last render, so
"accuracy dropped" is settled by numbers. Record per-participant measured walking speed beside the
model's 1.30 m/s cap.

#### B1 THE MOTION MODEL, pre-registered
Two axes, swept ONE AT A TIME from the shipped values, NEVER JOINTLY:
- the maximum advance per window, currently one state (0.649 m preferred, 0.75 m states), raised to
  allow two states so the cap becomes about 3 m/s, a physical ceiling on human walking and
  identical for every participant and line;
- the preferred step, swept over the current 0.649 and two higher values up to the observed 0.85 m
  per window.

Selection on held-out passes from the other training session, NEVER test-side. Every arm reports
the full measurement on all nine cross-day pairings and three within-day, never pooled, both
aggregate readings with the interval on the paired one, the guard (end-time substitution above 50,
line substitution of the same order as bounded), per-participant frozen-tail fraction, and the
implied traversal speed distribution against the measured one.

**SHIP RULE**: passes the guard, line identification not worse than the shipped arm on the paired
reading, frozen tails reduced, on-screen tracking improved outside its interval. If line
identification falls, it does not ship and the report states that the speed cap is the price of
line accuracy. If it ships, re-take the semi-bounded verdict against bounded under the same heads
AND the same motion model, ordering asserted, and re-measure bounded, since the demonstration's
committed answer uses it.

#### A4 KEEP DECODING TO THE HORIZON for the display
The display path continues past the decoder's own end using only windows up to the current frame
plus lag; the committed answer still comes from the own-end decision. Report frozen-tail fraction
per participant before and after, and on-screen tracking for walks that previously froze against
those that did not.

#### A1 to A3 PARK, WATCH, LOCK
The red dot sits at the room centre for a commit delay, then jumps once to the fixed-lag Viterbi
path's current estimate and LOCKS to that line for the rest of the walk; no switches after the
lock. Sweep the delay over 0.5, 1.0, 1.5 and 2.0 s and report, per delay, the fraction of walks
whose locked line is correct and on-screen tracking; **ship the shortest delay whose locked-line
accuracy is inside the interval of the best**. Display lag is separate from the delay: ship 0 s lag
after the lock, since the lag sweep showed 0 s tracks best (28.5 against 6.7 at 1 s), and state
both numbers in the caption. During the delay nothing is drawn except the parked dot.

#### A5 NO JUMP AT THE END
At the operator's end press, if the bounded commit agrees with the locked line nothing moves; if it
disagrees, the dot slides to the committed line at no more than 2.0 m/s of drawn motion, cross-line
only, snapping to the latest decoded point once on the new line. Keep the strong ending.

#### THE ONE RULE ON EVERY FRAME, unchanged
Every drawn position is a decoded position or a point between two consecutive decoded positions,
never ahead of the latest decode. Assert per frame.

#### ACCEPTANCE
On-screen tracking at the displayed time, fraction of frames within 0.5 m of green and mean
distance, per pass and per participant, split correct-line and wrong-line, before and after every
stage, in ACCEPTANCE.md. Locked-line accuracy per participant. Frozen-tail fraction per
participant. Switches per walk, which must read exactly one after the lock. Six videos plus
ACCEPTANCE.md and nothing else, removed files to `testing/demo_retired/` with a manifest, all from
one render run, verified by bytes against frame count, no frame without a red dot.

#### CAPTION
Dot waits at centre for the commit delay, then locks to one line for the whole walk and tracks at
0 s lag; final answer locked at the end press; on roughly one walk in five on this pairing the
locked line is wrong and the dot is visibly on the wrong line, which is correct behaviour and left
in.

#### CLOSE
Semi-bounded throughout, five-head pool, soft entry, 0.5 s stride. Suite and standing tests green,
freeze once with the shipped motion model, delay and lag recorded, one letter everywhere, STATE.md
and SEMIBOUNDED_STATE.md updated, then stop. Summary in six lines: stage 0 result, B1 verdict with
the guard, frozen tails before and after, shipped delay and lag, on-screen tracking before and
after, anything that failed.

---

## BRIEF_render_fix_2026-09-20.md

**Source:** `reports/BRIEF_render_fix_2026-09-20.md`, 2026-09-20. **SHA-256:** `fa03e72f85e38720957407a5c018fccb0f64b8e20c53a6d40039a8f30ce687f2`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### BRIEF: fix the live demonstration render so the red dot visibly tracks the green one

Received 2026-09-20. Stored verbatim. Display changes and one pre-registered decoder entry test.
Frozen five-head pool throughout, 0.5 s stride, nothing retrained, no freeze overwritten.
British spelling, no em dashes.

#### THE ONE RULE ON EVERY FRAME

Every drawn red position is either a decoded position or a point on the straight segment between
two consecutive decoded positions. Nothing is ever drawn ahead of the latest decode. Assert it per
frame; a frame that fails fails the render.

#### 1. SOFT ENTRY ON THE POOL

Re-measure `entry="soft"` on the shipped five-head pool, all nine cross-day pairings, with the
guard: line identification, end-time and line substitution, median error when right.
Pre-registered: **it ships if it passes the guard and its line identification is inside the
interval of the shipped arm**, since it was chosen for position error and opening behaviour rather
than line. Report the opening error, the median on-screen distance over the first 1.5 s of each
walk, shipped against soft.

#### 2. THE LIVE DOT IS THE DECODER'S RUNNING PATH

Draw the latest point of the fixed-lag Viterbi path, not a per-window argmax. Assert that within a
committed line the drawn path is monotone along the line, which the chain structure guarantees for
the Viterbi path and the argmax violated. Report per pass how many backward steps the old argmax
display contained, as the record of what this fixes.

#### 3. DISPLAY LAG FOR THIS MODE

Sweep the display lag over 0, 0.5 and 1.0 s for semi-bounded only; the committed answer at the end
press is unaffected and must be shown to be identical across the three. Judge on the on-screen
tracking figure in item 6 and the guard. Ship the shortest lag whose on-screen tracking is best or
inside the interval of the best, and state the choice and its basis in the caption.

#### 4. NO JUMPS

Within a line, interpolate the drawn position at frame rate between consecutive decoded points so
the dot glides instead of holding for five frames and stepping. On a line switch, slide the dot to
the new line's corresponding position at no more than 2.0 m/s of drawn motion, so a switch reads as
a move and not a teleport. Keep hysteresis at one window. Both are display interpolation between
decoded points and are labelled as such in ACCEPTANCE.md; the decision rate stays 2 Hz.

#### 5. ALWAYS VISIBLE

The red dot is never hidden. Between walks it is parked at the room centre; at the start press it
jumps to the soft-entry position and begins tracking; at the end press it locks to the bounded
rescore as already specified, then returns to centre when the walk is over. Test: no frame without
a red dot.

#### 6. ON-SCREEN TRACKING IS THE ACCEPTANCE NUMBER

For every walk, **at the displayed time rather than the decoded time so the lag counts against
it**: the fraction of frames where the drawn red dot is within 0.5 m of the drawn green dot, and
the mean on-screen distance, split into correct-line and wrong-line passes. Per pass, per
participant and pooled, in ACCEPTANCE.md, for each display lag in item 3. Print the same figure for
the previous render so the change is visible.

#### 7. FOLDER AND FILES

Unchanged: six videos, one per participant, and ACCEPTANCE.md, nothing else, removed files to
`testing/demo_retired/` with a manifest, all six from one render run, verified by bytes against
frame count. Re-measure the commitment timeline on the pool at the shipped lag for section 7 of
`SEMIBOUNDED_STATE.md` and the captions.

#### 8. CAPTION, on every video

Live estimate during the walk, told only when it started, drawn at the shipped display lag; final
answer locked at the operator's end press; on about two walks in five across days and one in five
on this pairing the line is wrong and the dot is visibly on the wrong line, which is correct
behaviour and is left in.

#### CLOSE

Suite and standing tests green, then freeze once with the shipped entry and display lag recorded,
one letter everywhere, update `STATE.md` and `SEMIBOUNDED_STATE.md`, and stop. Summary in five
lines: soft entry verdict, shipped lag, on-screen tracking before and after, backward steps
removed, anything that failed.

---

#### REFINEMENT to item 4, received 2026-09-20 before the batch ran

Apply the 2.0 m/s cap **only to the cross-line slide on a switch, and never to catching up along
the current line**: once the dot is on the decoder's line it snaps to the latest decoded point on
that line within one frame, so a slide can never leave it trailing behind a decode it has already
caught. Keep the continuous retargeting for the cross-line part. **If the measurement still says
the cap hurts on-screen tracking, report it and ship without the cap rather than tuning the speed.**

---

## HANDOFF_2026-09-21.md

**Source:** `reports/HANDOFF_2026-09-21.md`, 2026-09-21. **SHA-256:** `a13ecc62b788baef6456c0eaab4828a042a9806623e889ceef67f05257317ba1`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** Its open items were worked through in batches 22 to 23h; the current state is `STATE.md` and freeze 23h.

### Handoff, 2026-09-21

**Read this first, then stop reading and go to the files it names.** This document is a map, not
a summary. Everything here is checkable; nothing relies on remembering a conversation.

---

#### 1. Where the truth lives

| you want | read |
|---|---|
| where the project is, in plain language | `STATE.md` |
| the semi-bounded mode: what it is, what it scores, how it works | `reports/SEMIBOUNDED_STATE.md` |
| **the rendering contract. Six rules. Non-negotiable** | `reports/RENDER_RULES.md` |
| the last frozen record, with this batch's findings and void list | `runs/TRACKING_FROZEN_2026-09-22b.json` |
| what every stage found, in order | `reports/FINDINGS_stage*.txt`, `reports/HEADLINES.txt` |
| a stage's actual numbers | `runs/constrained/fh/<stage>/results.json` |
| the demonstration | `runs/constrained/demo/` — six videos and `ACCEPTANCE.md` |

**The freeze file is the authority on figures.** Read `headline_semibounded` in it. Do NOT read
`headline_numbers`: that block is carried forward from the five-head pool batch and says 57.5,
which is not the current figure. The payload says so itself in `headline_numbers_WARNING`.

---

#### 2. The numbers, and which are forbidden

**Quotable.**

| | |
|---|---|
| semi-bounded, cross-day, nine pairings | **62.50 percent** (per-pairing difference of medians) |
| bounded, same basis | 65.83 percent |
| verdict gap | 3.33 points against a ten-point bar, so semi-bounded REMAINS THE CORE MODE |
| chance, twelve lines | 8.3 percent |

**Void. Do not quote, and challenge anyone who does.**

- **64.17 percent** semi-bounded. Produced by a non-causal exit search with +20.5 s of look-ahead.
- **57.5 percent**, if quoted as current. It is the older five-head pool batch.
- `n1_diag`'s pooled `bounded_decode_on_the_TRUE_window` figure from before the pairing-key fix.
- Any locked-line or wait-curve figure taken before the evidence-horizon fix of 2026-09-20.

The freeze's `void_figures` and `SUPERSEDED_AND_NOT_QUOTABLE` blocks are the machine-readable
version of this list.

---

#### 3. Standing rules. These are not preferences

- `data/` is **read only**. `testing/` is **never imported**. Frozen artefacts are **never
  overwritten** — a freeze that needs correcting gets a new letter and records the supersession.
- Six participants only. Code names never leave `runs/`.
- Node geometry is fixed: TX (2.5, -0.5), RX1 (2.5, 5.5), RX2 (-0.5, 2.5), RX3 (5.5, 2.5).
- **The pairing key is `session|stem|pass_id`.** A dict spanning pairings adds the tag on top.
- `set -o pipefail` on every shell line. **Never** gate on an exit code that has passed through a
  pipe: capture `RC=$?` immediately and test that.
- Completion is decided by **output contracts**, not exit codes. Statuses are computed, not claimed.
- No decision rests on a single pairing. Report **both** the difference of medians and the median
  of paired deltas. Selection happens on held-out folds only.
- Pre-register before anything runs. If a rule changes after seeing the data, it is **post hoc**
  and is disclosed in those words — see the R3 gate change in the freeze for the worked example.
- British spelling. No em dashes.

---

#### 4. What ships right now

**Decoder.** Five-head equal-weight log-opinion pool, 0.5 s stride, 2.0 s windows, arm
`A1_A2_0.5` (entry restricted to the first 1.0 m, start-consistency term at weight 0.5), soft
entry, causal exit. The 3 m/s ceiling is **off for the decision and on for the display**.

**Display.** `DISP_END`, a display-only head labelled at the window END. Transition prior
`flatten_0.50`. Speed cap **0.80 m per window, 1.6 m/s**. Playback latency **2.0 s**, evidence
before commit **2.0 s**.

**Where these are set:** `pipeline/constrained/f3_render.py`, near the top of `main()`. The
constants carry comments explaining what each was measured against; read those before changing one.

---

#### 5. Failure modes this project has already paid for

Every one is now encoded in a test. **When a test in this list fails, it is almost certainly
right and you are almost certainly wrong.** Read its docstring: it names the failure it exists for.

| test | catches |
|---|---|
| `test_render_rules.py` | the six rendering rules. Rule 1 lock finality, rule 2 no projection, rule 3 the delay is stated, rule 4 the two accuracies stay apart, rule 5 the honesty checks, rule 6 the dot and marker leave together |
| `test_display_is_causal.py` | a display drawing from samples not yet recorded, **and** the evidence horizon leak the drawn-window bound cannot see |
| `test_cross_pairing_key.py` | `stem|pass_id` collisions across sessions and pairings |
| `test_pass_pairing_key.py` | `pass_id`-keyed dicts spanning recordings |
| `test_no_shadowed_stage_loads.py` | one name bound to two different `load()` calls |
| `test_reported_config_is_applied.py` | a setting that is recorded but never applied |
| `test_freeze_quotes_the_current_figure.py` | a freeze whose headline names a superseded figure |
| `test_asserted_not_measured.py` | claims that were never computed |

**The recurring shape of every one of these:** a number that looked right, produced by code that
was not doing what its name said. The drawn-window causal bound read a clean -0.000 s through a
full second of leaked future. The aggregate display lag read -0.25 s while the dot visibly stalled
at the start of every walk. **Aggregates hide faults that live at the start of things. Measure per
walk, at frame resolution, before believing a pooled number.**

---

#### 6. How to run things

```bash
cd /Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code
PYTHONPATH=. OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE \
  python3 -u -m pipeline.constrained.<stage> > runs/constrained/logs/<stage>.log 2>&1

# the suite, with the exit code captured before anything can eat it
PYTHONPATH=. python3 -m pytest tests -q > /tmp/suite.txt 2>&1; RC=$?; tail -2 /tmp/suite.txt; echo $RC
```

Stages run 4 to 10 minutes each over nine pairings. The render is about 8 minutes for six videos.
**Launch long work in the background and chain the verification behind it** — polling by hand has
cost this project over an hour in single sittings.

Before changing the render, **write the check first**. There is a working pattern in the session
scratchpad: a script of assertions over `results.json` and `ACCEPTANCE.md`, run automatically after
each render. It caught a caption that failed to interpolate and a section describing the wrong
head.

---

#### 7. Decided, and one reporting convention

**The demonstration latency is DECIDED: exactly 2.0 s.** Taken by the operator on 2026-09-22 and
written into the rendering contract as rule V1, `reports/RENDER_RULES.md`. It is no longer an open
question and is not to be re-opened by a score. `runs/constrained/fh/r6_latency/results.json` keeps
the curve that was available when the decision was taken.

**Rules V1 to V4 now bind the demonstration**: the 2.0 s latency, the commit and the marker as one
event, one fixed structural lock time with confidence-gated or variable latency FORBIDDEN, and no
dwell footage in a demonstration video. Read them in `reports/RENDER_RULES.md`, which is the single
place rendering rules live.

**Tracking is reported split by whether the dot is on the right line**, because on a wrong line
the dot-to-walker distance is a line separation, not a tracking error: 52.0 percent within 0.5 m
on the 87 correct-line walks, 40.0 percent pooled over all 120. The operator has said wrong-line
error does not matter much to them. This is a reporting convention, not an open decision.

---

#### 8. Two things measured and rejected, so they are not retried

- **Reaching back one window** so the scene starts at the walker's own first press: nearly halved
  accuracy (38.6 to 20.2 percent within 0.5 m), made the start gap worse, left 88 frames with no
  marker.
- **Widening A1's entry window**: removed a real truncation bias, moving the entry estimate from
  0.26 m to 0.55 against a truth of 0.61, and cost 15 points of tracking.

Both are in the freeze as measured negatives. The residual 0.58 m start gap on correct-line walks
is the decoder's entry error and currently has no cure worth its cost.

---

#### 9. Tracking is OPEN

**Superseded 2026-09-22 by operator decision: TRACKING IS NEVER CLOSED.** This section previously
read "Tracking is CLOSED until DC2". Every such statement in this repository is superseded; the
record of where they stood is `runs/SUPERSESSION_tracking_open_2026-09-22.json`.

`reports/DC2_PROTOCOL_2026-09-18.md` remains the next protocol, and DC2 is 26 and 27 September.
Work on tracking does not wait for it.

---

## HANDOFF_2026-09-22.md

**Source:** `reports/HANDOFF_2026-09-22.md`, 2026-09-22. **SHA-256:** `a92b6d551f7050247a17938d2f0574ccdf7d63093a88f7ecaa3f7148feaad8e7`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** Its open items were worked through in batches 23a to 23h; the current state is `STATE.md` and freeze 23h.

### Handoff, 2026-09-22. OPEN ITEMS

**The standing brief is `reports/BRIEF_render_and_prepress_2026-09-22.md`** and it holds the
operator's instructions verbatim. Read that, not a summary of it. This file is the live list of
what is open, and it is updated after each item.

> **CAUSAL CORRECTION, 2026-09-23 (batch 23c).** Every 2 s lock figure in this document was
> measured at a horizon reading two windows (1.0 s) of radio that had not finished recording at the
> lock. Those figures are **NON-CAUSAL and SUPERSEDED**; the causal figure now stands beside each.
> Why: `reports/FINDING_two_locks_2026-09-23.md`. Full tables:
> `reports/CORRECTION_causal_lock_2026-09-23.md`. **No verdict here changes.**

`reports/HANDOFF_2026-09-21.md` remains the map to where everything lives. **Tracking is never
closed**: `runs/SUPERSESSION_tracking_open_2026-09-22.json`.

Current freezes: `22c` the PRIMARY DC2 confirmatory reader, `22d` the SECONDARY exploratory arm. Headline: **62.50 percent**, unchanged. Headline: **62.50 percent**, unchanged.

---

#### THE REPORTS, which are the deliverable rather than any chat message

| batch | report |
|---|---|
| Part 1, the render batch | `reports/PART1_REPORT_2026-09-22.md` |
| Part 2, the pre-press reader | `reports/PART2_REPORT_2026-09-22.md` |
| Items A, B, C | `reports/ITEMS_ABC_REPORT_2026-09-22.md` |
| **where the model sits: accuracy, CSI vs motion model, the dot** | `reports/ACCURACY_STATE_2026-09-22.md` |
| the drawn dot: phase, start gap, and the non-regression | `reports/RENDER_DOTPHASE_2026-09-22.md` |
| **the 2026-09-23 batch: the edge, the display head, the pool head** | `reports/BATCH_2026-09-23_REPORT.md` |
| **what to do next, the authority** | `reports/QUEUE.md` |
| the operator's instructions, VERBATIM | `reports/BRIEF_render_and_prepress_2026-09-22.md` |
| the field sheet for the room | `reports/DC2_FIELD_CHECKLIST.md` |

Supporting: `ROOM_TRANSFER_AUDIT_2026-09-22.md`, `FINDING_pooled_vs_edge_2026-09-22.md`,
`PREREG_lock_`, `PREREG_lengthnorm_`, `PREREG_prepress_v2_`, `PREREG_DC2_crossroom_`.

#### DONE

| item | outcome |
|---|---|
| **Item 1, 2026-09-23: start together, at the edge** | **SHIPPED**, frozen `2026-09-23a`. Rule 6 starts the scene at the delayed press; rule 2a anchors the dot at the committed line entry; rule 2b makes the start gap a display rule; V3 offset exactly 2.0 s; V5 `shift_w` 0.50. Start gap **0.000 m** on all 87 correct-line walks, tracking **41.66%** from 40.0046%. **Rule 6's stall clause was scoped POST HOC** after measuring that 95 of 120 holds are explained exactly by the decoder's first decode being the tape entry |
| **Item 2, 2026-09-23: the display head on the edge windows** | Kept on the pre-registered non-inferiority rule, paired **-0.73 [-1.81, +0.35]**. **The render was NOT rebuilt on it**, a POST HOC refusal in the non-shipping direction. Refit control returned exactly 0.0 over 1077 passes |
| **Item 3, 2026-09-23: the pool's 0.5 s head on the edge windows** | **REFUSED.** Paired lock **-1.85 [-3.52, -0.28]**, entirely below zero; (b) 0 passes; (f) E_col5 -1.9. Reproduction check exact, no-op check passed on all nine. **ONE head of five; the lock never reads the added windows, 0 of 720** |
| Part 1, steps 0 to 4 | accepted by the operator. Nothing shipped in the decision; the render changed for the dwell cut and V1 to V4 only |
| V1 to V4 | in `reports/RENDER_RULES.md`, enforced by 17 tests |
| Room transfer audit | `reports/ROOM_TRANSFER_AUDIT_2026-09-22.md` |
| 2 s lock diagnosis | `t6_lockdiag`. Two causes: the estimator, and the cell marginal over-boosting edge lines |
| Lock arms | `t7_lockarms`. All four refused on condition (f): every one bought pooled accuracy by degrading the edge lines |
| **Item 1, DC2 calibration** | procedure written into `reports/DC2_PROTOCOL_2026-09-18.md`; relative forms implemented in `t8_calib` and **verified NOT to reproduce within one pass** on Room A's improvised anchor |
| **Item 2, the 2.25 s explanation** | measured and added to the acceptance writer, computed from the constants rather than hard-coded |
| **Item 3, length-normalised arm** | refused; inert by construction. `reports/PREREG_lengthnorm_2026-09-22.md` |
| **Operator decision, the lock** | **KEEP THE SHIPPED LOCK**, recorded with its four grounds in `reports/FINDING_pooled_vs_edge_2026-09-22.md`. Estimator arms are reported as ABLATIONS beside the edge-line figures, never as candidates |
| **DC2 cross-room pre-registration** | **written 2026-09-22, before any Room B data exists**: `reports/PREREG_DC2_crossroom_2026-09-22.md` |
| **Part 2 pre-registration** | `reports/PREREG_prepress_v2_2026-09-22.md`, arm (d) framed as a Room A PILOT |

---

#### OPEN

> **TRACKING IS NOT CLOSED. THE BACKLOG IS EMPTY, WHICH IS A DIFFERENT THING.** Every statement
> that tracking is closed until DC2 is superseded:
> `runs/SUPERSESSION_tracking_open_2026-09-22.json`. Three items are now open, below.

##### A. DC2 DRY RUN. Build and test the whole Room B path NOW, before capture

**Why:** so DC2 results turn around the night of capture rather than a week later.

**What:** ingest a new room's recordings into the existing layout as a NEW ROOM FOLDER, **never
touching `data/room_A`**; process the calibration block; apply the re-anchored gate and null; run
the frozen tracker, the primary arm `b_abstain_0.25` (`22c`) and the exploratory arms; and produce
**every table `reports/PREREG_DC2_crossroom_2026-09-22.md` promises**.

**Tested end to end on a STAND-IN**: one Room A session treated as if it were Room B, its first
minutes standing in for the calibration block.

> **THE STAND-IN NUMBERS ARE A PLUMBING CHECK AND ARE NEVER REPORTED AS RESULTS.** They say the
> path runs, not what it found.

**Deliverable:** ONE command that takes the DC2 folder and writes the full report.

##### B. REAL-TIME OPERATION. A required deliverable

A live runner, **separate from `pipeline/io/` and the serial code, which are used READ-ONLY and
never edited**. Streams CSI from the three receivers, windows causally, runs the frozen tracker in
semi-bounded mode from an operator start press, and draws the display live under
`reports/RENDER_RULES.md` V1 to V4.

**Measured and reported:** the end-to-end latency distribution, radio sample to drawn frame, and
the **headroom per 0.5 s stride**.

**THE ACCEPTANCE TEST:** replay a Room A recording at real-time speed and check the live decisions
match the offline ones **exactly**. That equality is the test; anything less is not acceptance.

**If time allows:** a live run on the rig before DC2, so a genuinely live demo can be recorded in
Room B.

##### C. DONE. THE A_fwd DIAGNOSTIC: HYPOTHESIS REFUTED, over-draw is an OPEN DEFECT

`v1_afwd`, 360 passes. RX2/RX3 posterior agreement, 1 minus total variation distance, per pass.

| | agreement |
|---|---|
| **A_fwd** | **0.1894**, CI [0.158, 0.218] |
| **A_rev** | **0.1826**, CI [0.156, 0.210] |
| other ten lines, mean | **0.2388** |

**The hypothesis predicted A_fwd would show HIGHER RX2/RX3 agreement** — the side links being
mirror images about the TX-RX1 axis and so unable to tell left from right along it. **The
measurement is the opposite: the A lines have the LOWEST agreement of the twelve.** The stated
mechanism is not present.

**Two things the control settles.** A_fwd and A_rev are nearly identical to each other (0.1894
against 0.1826) and both below the rest, which is consistent with their sharing the axis — but the
axis effect runs the wrong way for the hypothesis. And they remain nearly identical **while one is
over-drawn at 1.95 and the other under-drawn at 0.61** (NON-CAUSAL lock figures; **causally 2.61 and 0.565**, `reports/CORRECTION_causal_lock_2026-09-23.md`), so whatever distinguishes them is not in
the RX2/RX3 relationship at all.

> **VERDICT: the A_fwd over-draw is an OPEN DEFECT with no surviving hypothesis.** It is not a
> physical limitation of the node layout, on this evidence. It is carried as an open defect rather
> than as an explained quirk, and the TX-proximity hypothesis is withdrawn.

**Do not re-propose the axis-symmetry explanation** without new evidence: it has been measured and
it fails.

##### 1. The relative gate and null are implemented but NOT enabled

`pipeline/constrained/t8_calib.py`. All three forms are unbiased and noisy: paired deltas +0.00 to
+1.67 with every interval straddling zero, but a **worst per-pairing scatter of 3.33 points against
a 0.833 bar**.

**The anchor is the problem, not the formula.** Room A has no calibration block, so the anchor had
to be the pre-press setup period, whose median band energy varies 2.3x across three days in the
same room.

**What has to happen, on DC2 day one, before any figure is quoted:** record the calibration block
the protocol now specifies, re-run the verification against it, and enable the relative forms only
if they clear the same one-pass bar. Otherwise fall back to the absolute constants and print the
three calibration numbers beside every DC2 figure.

##### 2. The null level may not be at its optimum, and this must NOT be settled by the current sweep

`t8_calib` scored **65.00 at −6.0 nats and 67.50 at −4.5**, against 62.50 at the shipped −7.50.
That is a sweep over the full evaluation set. Selecting on it is post-hoc test-set fitting and is
refused. **Open for a pre-registered look with a proper held-out split, after DC2.**

##### 3. A_fwd is over-drawn at 1.95 (NON-CAUSAL; 2.61 causally) and nothing explains it

Measured in `t6_lockdiag` over 1080 passes: A_fwd's drawn-over-true ratio is **1.95 under the
shipped lock, 2.81 under the chain-total lock and 2.24 under the committed answer** (NON-CAUSAL;
**causally 2.61 and 3.09**, the committed 2.24 unchanged). It is
over-drawn under **every** estimator, including the one that scores whole walks, and no ablation
moved it: not the cell marginal, not the chain prior, not the A2 term, not the estimator swap.

**Hypothesis, UNTESTED, recorded as a hypothesis and not as a cause: TX proximity at S_mid plus the
RX1 link's symmetry.** A_fwd starts at (2.5, 0.0), which is 0.5 m from TX at (2.5, −0.5), and runs
straight up the line joining TX to RX1 at (2.5, 5.5). A walker on A_fwd is on the TX-RX1 axis for
its whole length, and the two side links RX2 and RX3 are mirror images about that axis, so they
cannot distinguish left from right along it. Whether that produces a posterior that favours A_fwd
has not been tested and must not be reported as though it had.

**How it would be tested:** compare the per-link posteriors on A_fwd passes against the other
eleven lines, and check whether the RX2 and RX3 posteriors are more nearly identical there than
elsewhere. No such measurement exists yet.

##### 4. RESOLVED. Item 3, length-normalised chain totals: inert by construction

`t9_lengthnorm`. All three normalisations returned **69.17 on the held-out folds, identical to the
raw chain total** (NON-CAUSAL; **causally 62.50, 62.50 and 63.33 against 62.50**), and the arm was refused on condition (f) like the others.

**The reason is exact rather than empirical.** Measured directly: at the lock every one of the
twelve chains is traversed identically, 5 windows, 5 distinct states, **3.00 m of arc**, because
the step model inside a chain is the same everywhere. The 21-versus-30 state asymmetry is a
property of the WHOLE chain, and the lock never sees the whole chain. There is no length asymmetry
at the lock for a length normalisation to correct.

**The prediction recorded before the run was that `N_per_step` would be nearly inert. It was, and
so were the other two, for a reason the prediction did not anticipate.**

##### 5. Part 2, the pre-press region reader. IN PROGRESS

Pre-registered in `reports/PREREG_prepress_v2_2026-09-22.md`. **Arm (d), causal per-session
adaptation, is the priority arm** and runs first, because every Part 1 arm was flat or worse on the
three session-01 folds: the shift is the obstacle, not the reader.

**Arm (d) is a PILOT in Room A, and that is pre-registered.** Item 1 showed Room A's only
per-session anchor varies 2.3x across three days and that this alone produced 3.33 points of
scatter. **A null in arm (d) is recorded as "untestable with Room A's anchor", never as
"adaptation does not work".**

Checked before the pre-registration was finalised:

- **idle windows before the first press exist**: 544, 174 and 169 for sessions 01, 02, 03. The 24
  `walk_edge` windows in that period belong to pass 1's own run-up and are **excluded**, which
  refines what `t8_calib` did.
- **empty-room baseline captures exist** per session, but as raw CSI this batch does not window.
- **`nn.BatchNorm2d` IS present** in `pipeline/models/link_cnn.py:67`, so **AdaBN is available**
  and is the arm; input-feature normalisation runs beside it as the comparator.

**Conditional extension, pre-registered:** if (d) lifts session-01 region reading under the ship
rule, the same adaptation is applied to the TRACKER's emissions and tested on the committed
semi-bounded figure under the full rule plus (f). **If it does not, the extension does not run.**

##### 5b. ARM (d) RESULT: the right direction, but Room A cannot establish it

`u1_adapt`, 1.7 min, contract satisfied, 18 recordings audited, every calibration window `idle`
and ending at least **2.007 s** before its recording's first press.

| mode | median over pairings | per-pairing spread | **session-01 folds** | other folds |
|---|---|---|---|---|
| unadapted | 33.33 | 40.83 | **17.50** | 50.42 |
| **AdaBN** | **42.50** | **28.33** | **26.67** | 46.25 |
| input normalisation | 22.50 | 39.17 | 18.33 | 39.17 |

**AdaBN against unadapted: paired +6.67 points, CI [−2.22, 8.61], which INCLUDES ZERO.** Condition
(a) is not met, so by the pre-registration **the tracker extension does not run**.

**What is nonetheless true, and is the reason this is a pilot.** The effect is positive on **all
three** session-01 folds (+14.17, +7.50, +10.83), it lifts the session-01 median by 9.17 points,
and it **cuts the per-pairing spread from 40.83 to 28.33** — which is precisely the instability
`t8_calib` identified as Room A's limitation. It costs 4.17 points on the easier folds.

**This is recorded as UNTESTABLE WITH ROOM A'S ANCHOR, not as adaptation failing.** With nine
pairings and this much residual scatter the interval cannot close, which is what the pilot framing
anticipated before the run.

**A control that matters:** input normalisation is **significantly WORSE**, paired −10.00 with CI
[−10.83, −1.39] excluding zero. So the gain is specifically AdaBN re-anchoring the batch-norm
statistics, not any per-session rescaling.

**Caveat:** 2 of 18 recordings had fewer than 20 calibration windows and were left unadapted.

**Carried into DC2:** this is the strongest argument yet for the calibration block. AdaBN on a
controlled anchor is a different experiment from AdaBN on a setup period.

##### 5e. PART 2 IS COMPLETE. Report: `reports/PART2_REPORT_2026-09-22.md`

**No ship, and one active harm.** The 62.50 headline is unchanged and untouched. The useful
outputs are a mechanism control, a withdrawn claim, and a frozen arm for DC2 to test. None is a
gain, and the report says so.

**PROTOCOL DEVIATION, recorded:** `u3_trackeradapt` was gated on arm (d) lifting session-01
reading under the ship rule. Arm (d)'s interval includes zero, so the condition was not met and the
extension should not have run. It ran on an operator override recorded as post hoc. **Its result
is exploratory.**

**The extension was significantly NEGATIVE.** Held-out seven: 50.00 unadapted against 30.83
adapted, paired −3.33, CI [−15.83, −2.62] entirely below zero. **The harm falls where the tracker
was working**: the three worst losses (−23.33, −18.33, −15.83) are the three highest baselines,
while the three session-01 folds are unchanged (+3.33, 0.00, −2.50). Edge lines E_col5 −35.71,
E_row5 −26.19.

**Two explanations, both stated, neither claimed:** Room A's anchor is unfit (2.3x across days), and
the tracker's downstream classifier is frozen where arm (d)'s LDA is refit. A negative on an unfit
anchor does not show adaptation fails with a clean one.

**FOUR FAULTS OF MY OWN, each of which changed a verdict**: a lattice-dependent test assertion that
passed or failed on test order; a rounded-against-unrounded edge comparison that marked all eleven
arms as degrading the edge lines; condition (c) reading a different quantity from (a) and (b); and
(b) rejecting an exactly-two-pass arm on a floating-point last bit. Two briefly made something look
shippable that was not.

##### 5c. PART 2 DETAIL: the arms

**`b_abstain_0.25` does not ship. The 62.50 headline stands.** It passes (a) +2.50 points CI
[0.71, 6.07], (b) three passes, (d) substitution, (f) no edge line degraded and two improved. It
**fails (c)** under the consistent paired-delta reading: +0.00, +2.50, +3.33, +0.83, rise then
fall. **That consistent reading was adopted after seeing the data, in the conservative direction,
and is recorded as POST HOC.**

**The mechanism check settles what the arm is doing** (`u4_mechanism`, held-out counts):

| group | n | gained | lost | net |
|---|---|---|---|---|
| covered, reader correct | 262 | **31** | **0** | **+31** |
| covered, reader wrong | 288 | 6 | 10 | −4 |
| **uncovered, the control** | 290 | **0** | **0** | **0** |

31 gained and none lost where the reader covered and was right; the control holds **exactly**.
Coverage 66.8 percent overall. **The gains concentrate where the reader is WORST**: 25.8 percent
reader nets +5, 26.7 nets +6, 31.7 nets +10 with zero losses, while the best reader at 54.2 nets
+1. Abstention protects hard folds, which is why a new room is worth testing it on.

**`a_veto_1.0` DOES NOT SHIP EITHER. NOTHING FROM PART 2 SHIPS INTO THE ROOM A HEADLINE.** It
clears all five conditions once a floating-point fault in (b) is fixed — it measured exactly two
passes, 1.6666666666666665 against a bar of 1.6666666666666667, rejected on the last bit; (b) now
compares passes as integers. It was declined on two grounds, the second the stronger:

1. shipping it at two passes while declining `b_abstain_0.25` at three would rest the decision on
   condition (c) alone, the condition whose reading was corrected twice in one day;
2. **MULTIPLE TESTING.** Eleven arms were scored against the same seven held-out folds and the
   same 840 passes. **An arm landing exactly on the two-pass bar, with the two readings
   disagreeing in sign, is the result most likely to be selection by multiple testing.** The
   interval on one arm accounts for none of the ten looked at beside it.

**THE PATTERN THAT IS NOT EXPLAINED, and is no longer claimed.** Gains are largest on the folds
with the weakest readers. Two explanations fit — abstention protecting hard folds, or plain
headroom — and **they cannot be separated**: reader accuracy and baseline are collinear at
**+0.958** across the seven held-out folds. Both are stated, neither is claimed, and the per-fold
table showing baseline beside reader accuracy and gain is in the pre-registration.

##### 5d. DC2 CONFIRMATORY STRUCTURE: one primary, one exploratory, frozen separately

**PRIMARY, and the cross-room claim rests on it ALONE:** `b_abstain_0.25`, frozen as
`runs/TRACKING_FROZEN_2026-09-22c.json`, **abstain threshold 0.90, weight 0.25**. Applied once,
unchanged. **(a), (b) and (f) apply; (c) does not**, because a single fixed application has no
dial. Pre-registration section 7a.

**SECONDARY, EXPLORATORY, and it does NOT carry the claim:** `a_veto_1.0`, frozen as
`runs/TRACKING_FROZEN_2026-09-22d.json`, **veto threshold 0.01, 3.0 nats, weight 1.0**. Labelled
exploratory wherever it appears. Kept separate so the primary is not diluted by a second chance to
succeed: two arms on Room B are two opportunities for one to clear a bar, and a claim resting on
whichever does is a selected claim. Pre-registration section 7b.

**The falsifiable prediction stands:** a collapsed Room-B reader should tend toward NO EFFECT
rather than harm, and a negative paired delta would mean abstention did not protect.

##### 5f. THE FIELD CHECKLIST IS WRITTEN

`reports/DC2_FIELD_CHECKLIST.md`. One page, capture order, for use in the room. Covers node
geometry held identical, the calibration block (empty room, standing, **2 passes on each of 4
lines**), approach walks with start regions labelled, **two separated blocks per participant
interleaved with others** for the recording-block confound, speed variation, reaction-time bias
before the first evaluated pass, the exclusion list written at capture time, and the three
calibration numbers to print before any figure is quoted.

##### 5a. DUE BEFORE 26 SEPTEMBER

- **`reports/PREREG_DC2_crossroom_2026-09-22.md` is written and is not edited once Room B data
  exists.** Any change after that point is POST HOC and says so at the point of change.
- **The DC2 confirmatory arm is frozen and listed**: `runs/TRACKING_FROZEN_2026-09-22c.json`,
  threshold 0.90, weight 0.25, applied once with no sweep and no refitting.
- **The DC2 calibration block must actually be recorded** on the morning of each DC2 day, before
  any evaluated pass: empty room 60 s, standing 60 s, and **2 passes on each of 4 named lines**.
  Without the calibration walks the null cannot be re-anchored, and the null is the quantity whose
  error costs 16.7 points.

##### 6. RESOLVED as a written finding, and one judgement is now the operator's

`reports/FINDING_pooled_vs_edge_2026-09-22.md`. The trade is real and is NOT resolvable at the
lock: keep the shipped lock at 60.8 pooled with edge recall 65.3, or take the estimator fix at
69.2 to 73.3 pooled with edge recall 49.1 to 56.0 (NON-CAUSAL; **causally 57.50 with edge 53.24
against 62.50 to 65.00 with edge 36.57 to 47.22**). **No arm is recommended**, because which is
better is a judgement about what the edge lines are worth and not a measurement.

Every lock arm that raised pooled accuracy degraded the edge lines. E_col1 recall: **50.0 percent
shipped, 42.6 under the chain-total lock, 7.4 under `E_both`, 1.9 under `E_no_marginal`.**
(NON-CAUSAL; **causally 42.59, 29.63, 0.00 and 0.00**.) The
shipped lock's over-drawing of the E lines is what buys its edge-line recall. Condition (f) is
what caught this, and without it `E_both` at +10.00 points would have shipped.

---

#### Standing, and not open

The latency is DECIDED at 2.0 s, rule V1. Confidence-gated or variable latency is FORBIDDEN, rule
V3. Node geometry is fixed and moving a node is never proposed, including for DC2, because changing
room and layout together would confound the cross-room result.

---

## BATCH_2026-09-23c_REPORT.md

**Source:** `reports/BATCH_2026-09-23c_REPORT.md`, 2026-09-23. **SHA-256:** `4d6fa89682435185fce380beeab23f30ae1e12c00ed9e1d0f576550ec8b1cea2`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** Its lock figures were decoded at sd_scale 1.0; the drawn lock (sd_scale 4.5) is in `reports/CORRECTION_drawn_lock_2026-09-23.md` and `runs/TRACKING_FROZEN_2026-09-23h.json` records it at 53.33 percent held-out. The headline moved to 73.33 post-amendment in batch 23d.

### Batch 2026-09-23c: closing report

Operator instruction 3, verbatim in `reports/BRIEF_render_and_prepress_2026-09-22.md`. Queue and
log: `reports/QUEUE.md`. Every figure below is read back from a results file named beside it.

**The 62.50 headline is unchanged.** No decision change shipped. One display change shipped: the
committed line is now named as text at the end of every walk (item 4's "either way" clause).

---

#### Before anything

Suite **1051 passed, 8 skipped** at batch open; `tests/test_dc2_ingest_guard.py` **7 of 7**. The 8
skips are scaffolds and one pattern test, none of them the DC2 guards. Keep-alive reused: the
existing caffeinate and watchdog, and the heartbeat restarted by that watchdog after its stage list
was rewritten (my PID, command line read first). Nothing of the gait ID session was touched.

#### The four findings that matter most, in order

1. **Fusing the three links by product is the largest effect this project has measured, and it is
   refused as written.** Committed semi-bounded **62.50 to 79.17** on the median of nine, held-out
   **+11.07 [5.24, 18.21]**, session-01 folds up 9 to 18 points. Refused on (c) (non-monotone) and
   (f): **one pass of E_col1** on the committed answer at w = 0.25, and 5 to 25 passes per edge
   line at the lock. About half the gain is sharpening against Room A's fitted null and gate, half
   is the links agreeing. `reports/FINDING_linkfusion_2026-09-23.md`.
2. **The shipped lock is drawn before its evidence has finished recording.** Since 23a it is drawn
   at press + 2.0 s but reads window `lo + 2`, which ends a median **0.218 s** later (up to 0.499 s)
   on **1080 of 1080** passes. No check covered it. Making it exactly causal costs about four
   held-out points either way, and the two fixes differ sharply on the edge lines.
   `reports/FINDING_lock_phase_2026-09-23.md`.
3. **Mid-walk switching works for the viewer and is refused on one line.** Time on the correct line
   **+4.05 [0.87, 8.08]**, net wrong-to-right median **5** per pairing, substitution passes; **(f)
   refuses: E_col5 -3 passes** while the edge lines net +15.
4. **The three 1 s heads can be rebuilt from source, exactly.** 27 of 27 pairing-seeds retrained
   **bit-identical** to the frozen weights; their posteriors agree to 3e-8 (float32 storage) with
   100 percent argmax agreement. Every pool figure this project quotes is now reproducible from
   `data/` and the code alone.

Findings 1 and 3 have the same shape as `y2_dial`: a per-line rule refusing a change that is
positive across the edge lines. The operator ruled (f) stands as written; each is recorded as a
refusal and none is re-proposed with a relaxed rule.

---

#### Item 1. CORRECT THE RECORD: DONE

`reports/CORRECTION_causal_lock_2026-09-23.md`.

- **`pipeline/constrained/lock_horizon.py`** is the one place a lock's end window is computed; it
  refuses anything past `lo + step`. t6, t7, t9, y1_diag and y2_dial take their end from it;
  `y2a_causal`, whose purpose was measuring lookahead, is retired and refuses to run.
- **`tests/test_lock_is_causal.py`, 9 tests**: every window after `lo + step` is poisoned and all
  four lock estimators must return the same answer; the poison is shown potent first; a static test
  bans `... + LAG_W`. **Mutation-checked**: t7's old lookahead turns it red.
- **t6, t7, t9, y1_diag re-run causally**, lookahead outputs archived first at
  `runs/constrained/fh/_LOOKAHEAD_superseded_2026-09-23c/`. Reproduction exact; the committed answer
  is identical in both runs (75.00), which is the control.
- **Fifteen documents annotated** with the causal figure beside each lookahead one (t6, t7, t9 and
  y1 findings files, FINDING_pooled_vs_edge, PART1_REPORT, both HANDOFFs, PREREG_lock,
  PREREG_lengthnorm, PREREG_lockmix, PREREG_edgeheads, ACCURACY_STATE, ITEMS_ABC, my notes in the
  BRIEF). The operator's verbatim text was not edited.
- **No verdict changes.** New facts: A_fwd's over-draw is **2.61** causally, not 1.95; E_col1 falls
  to **0.00** under E_both and E_no_marginal; t9's per-metre normalisation is one pass off inert
  causally; t9's sweep label was wrong and is fixed.
- **The operator's y2_dial decision** is recorded in `reports/FINDING_two_locks_2026-09-23.md`:
  +5.00 held-out, refused by one E_row1 pass, zero net change across the four edge lines.
- **One qualification of the record**, found this batch: the render lock and the t6/t7 causal proxy
  agree on the held-out median and all four edge figures but NOT on every pairing (one pass apart
  on four of nine). Added to the two-locks finding.

#### Item 2. PRESS-ALIGNED FIRST WINDOW: DONE, nothing ships

Pre-registration `reports/PREREG_pressalign_2026-09-23.md`; results
`runs/constrained/fh/y4_pressalign/results.json`.

- **Timing, as asked, first:** one recording cut in **29.7 s**; all 18 in 8.5 min; features 10 s and
  826 MB per recording; six heads re-inferred in 19 min.
- **Cache location carries the stride:** `runs/constrained/windows_s0.5_pressalign`,
  `runs/artefacts_s0.5_pressalign_{shared,half,fh1s,g1s1,g1s2,g100,dispend}`. The inference path
  reproduced the shipped posteriors to 3e-8 before use. The measurement snapshot-compared the
  shipped half-stride trees before and after: untouched.
- **Reproduction check PASSED** (lock 57.50 and its four edge figures; tracking 28.2456 / 1077 and
  53.1045 / 517).

| | shipped lattice | press-aligned | paired |
|---|---|---|---|
| locks drawn before their evidence ended | **1080 of 1080**, median +0.218 s | **0** (max +2.5 microseconds) | |
| lock, held-out 7 | 57.50 | 50.00 | **-4.52 [-6.90, -2.38]** |
| lock edge E_col1 / E_col5 / E_row1 / E_row5 | 42.59 / 77.78 / 35.19 / 57.41 | 37.04 / 66.67 / 27.78 / 50.00 | every line down |
| committed, held-out 7 | 75.00 | 74.17 | +0.36 [-1.79, 2.74] |
| **entry hold**: first decoded position at the tape entry | 75.8 percent | **81.6 percent** | not improved |
| tracking within 0.5 m, whole walk | 28.25 | 29.26 | +1.10 [-0.53, 2.76] |
| opening second of decoded frames | 23.70 | 33.73 | +10.1 [8.2, 12.0] |
| the rest of the walk | 30.67 | 28.42 | -2.65 [-4.56, -0.76] |

**Predicted before the run, and borne out:** under the unchanged labelling rule the lattice ADDS
run-up to `lo` (50 percent from 39) and does not help the entry hold; what it removes is the lock's
lookahead. The opening-second gain is partly a different stretch of walk (it starts 0.22 s
earlier), so it is not read as a clean display gain. (c) cannot be evaluated for a binary lattice
change, so no decision change could have shipped by the rule as written; (a) fails in the negative
direction in any case.

**Faults of mine, each caught by the stage before a number:** a window start exactly on the press
made `lo` a float-rounding coin flip (9 of 20 passes half a stride late), fixed with a 2
microsecond offset and verified on every pass; `s2a_dispend`'s import guard in prep; the A2 start
term needing the position head, which the first prep skipped (the measurement failed 9 of 9,
loudly). `n2_arms` asserts the literal shipped root at import, so the press-aligned roots are bound
first and the shipped trees are snapshot-verified.

#### Item 3. TWO NO-RETRAINING ARMS: DONE, both refused

Pre-registration `reports/PREREG_linkfusion_g100native_2026-09-23.md` and amendment 1; results
`runs/constrained/fh/z3_eval.json`; finding `reports/FINDING_linkfusion_2026-09-23.md`.

- **A, renormalised product of the three link posteriors**: see finding 1 above and the finding
  document for the full sweep. Refused on (c) and (f).
- **Control T** (the mean sharpened to the product's three factors; **added after seeing w = 1, and
  labelled so**) recovers 48 percent of A's committed gain, interval including zero.
- **B, g100 at native 0.5 m**: small. Committed at most +1.07 [0.12, 2.02], non-monotone; the lock
  fails (b) and (f). **Along-line substitution ratio 0.29 against 0.26 shipped** (A: 0.40).
- **"Gate head" corrected**: g100 is a 100-cell region posterior head, not a gate. Seven reports,
  STATE.md and two code files; the JSON keys `gate_head_g100` / `g100_gate` kept as identifiers and
  noted.

#### Item 4. MID-WALK SWITCHING: DONE, refused under (f)

Pre-registration `reports/PREREG_switching_2026-09-23.md` with amendment section 11 (written before
the run); results `runs/constrained/fh/y3_switch/results.json`.

- Every switch decision **wall-clock causal**: worst `window end - frame` -0.0007 s. The lock is the
  shipped one (reproduction exact).
- theta chosen on the selection folds only: **3.0 for both K**, the top of the pre-registered grid.

| | K = 1 | K = 2 |
|---|---|---|
| time on correct line, held-out paired | **+4.05 [0.87, 8.08]** | **+4.10 [0.89, 8.09]** |
| wrong-to-right minus right-to-wrong, median per pairing | 5 | 5 |
| substitution ratio | 0.65 | 0.73 |
| edge, final drawn line vs lock, passes | E_col1 +5, **E_col5 -3**, E_row1 +12, E_row5 +1 | +6, **-3**, +15, +1 |

Both of the operator's conditions pass; **(f) refuses on E_col5**, and every one of the ten
(K, theta) arms costs E_col5 at least 3 passes. The session-01 folds are flat. **Rule 1 is
unchanged.**

**Either way:** the render now names the committed line as text at every walk's end ("COMMITTED:
X (drawn Y, agrees/differs) true: Z"); before, it named it only when it disagreed with the lock.
Contract test added and mutation-checked. **The one measurement:** the frame at the end of walk 1
of the re-rendered PA5 video reads "COMMITTED: D_fwd   (drawn D_fwd, agrees)   true: A_rev",
an agreeing walk, which is the case that used to show no committed line.

#### The render and the freeze

**Rendered once for the batch, and it took two runs, which is my fault.** The first run FAILED
only its folder check: I had put a backup of the 23a videos inside `runs/constrained/demo/`, and
the render requires that folder to hold exactly six videos and `ACCEPTANCE.md`. Every other check
passed. The backup was moved to `runs/constrained/demo_archive/_render_23a_before_23c/` and the
render re-run, rather than the verdict being asserted. The render's own `one_render_run: true`
refers to the second run.

The render that stands: **PASSED**. 0 rule violations over 4783 frames; 0 missing dots of 7756
expected; causal bound -1.300 s on both bounds; V2 and leave-together 0 violations over 120 walks;
anchor segment 0 off-segment frames; on-screen tracking **41.66 percent**, unchanged from 23a, as a
text-only change should leave it.

**Freeze `runs/TRACKING_FROZEN_2026-09-23b.json`**, superseding 23a, which is not overwritten.
Headline **62.50, carried, not re-measured**: every decision arm was refused and the 1 s heads
retrained bit-identical. Both reproduction checks this batch (`y4_pressalign`, `z3a_linkprod_w0`)
returned 62.50 on the shipped configuration. The lock-phase defect is carried in the freeze as
OPEN.

**Suite at close: 1101 passed, 9 skipped, 1 xfailed, 2 failed.** The xfail is the strict
lock-phase marker, as intended. **Both failures are the gait ID session's and were not touched:**
`test_pass_pairing_key` on its new `pipeline/identify/id19_*.py`, and `test_idmax_guards`, which
finds a DEMO path in its own `runs/identify/idmax/READS.log` written at 12:34:34. Nothing outside
`pipeline/identify/` imports the module that writes that log, and its current guard refuses a
DEMO path before logging, so the entry predates that guard.

#### Item 5. THE THREE 1 s HEADS, RETRAINED: DONE, bit-identical, nothing to ship

Pre-registration `reports/PREREG_retrain1s_2026-09-23.md`; results `runs/constrained/fh/y5_heads/`.

- **Gate met:** item 2 DONE; every tree this item wrote carries its stride
  (`artefacts_s1.0_retrain_*`, `artefacts_s0.5_retrain_*`) and `y5_heads._guard` refuses any
  shipped root by name. The shipped 1 s cache (6.3 GB, stride-blind filename) was never opened for
  writing.
- **A BASE retrain**, decided before the run: same code, seeds 0/1/2, 24 epochs, `data/windows` at
  1.0 s, nine cross-day pairings. The only motivated recipe change (entry-straddling windows) was
  refused on the 0.5 s head, so it was not repeated here.

| check | result |
|---|---|
| 1 s feature cache rebuilt, against the shipped manifest's sha256 | **byte-identical, 18 of 18** |
| retrained weights (and `mu`, `sd`) against `runs/artefacts/models` | **bit-identical, 27 of 27** (max parameter difference 0) |
| posteriors over the 0.5 s windows against `artefacts_fh1s` / `g1s1` / `g1s2` | max difference **3e-8** (float32 storage), argmax agreement **100 percent**, 27 of 27 |
| training time | 51 min per seed, seeds in parallel |

**As predicted.** The heads are identical, so the pool is identical by construction and the
pre-registered pool re-scoring (step 4) was not needed. **Nothing ships from a base retrain.** What
it establishes: the heads every quoted figure rests on are reproducible from source, the
stride-keyed machinery works end to end, and any future 1 s head arm has a verified baseline and a
safe place to train.

---

#### Decisions that are the operator's

1. **The lock phase.** Keep the 0.218 s leak and state it; take the press-aligned lattice (-4.52,
   edges kept); lock on `lo + 1` (-3.69, E_row1 to 1.85); or move the lock frame to press + 2.5 s
   (not measured, changes V1/V3).
2. **Product link fusion.** The largest effect measured, refused on (c) and (f). The honest test is
   a frozen arm pre-registered for DC2, with (f) as written.
3. **Switching.** Passes the operator's own two conditions; refused on one edge line.

#### Not mine, recorded

The two suite failures above, both the gait ID session's. Not touched.

---

## BATCH_2026-09-23d_REPORT.md

**Source:** `reports/BATCH_2026-09-23d_REPORT.md`, 2026-09-23. **SHA-256:** `2cccd3efd662040625a96a30e28505352e660c200a677d5cb0b86219f9b08b42`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### Batch 2026-09-23d: closing report

Operator instruction 4, verbatim in `reports/BRIEF_render_and_prepress_2026-09-22.md`. Queue and log
`reports/QUEUE.md`. Every figure is read from a results file named beside it.

**Freeze `runs/TRACKING_FROZEN_2026-09-23d.json`**, superseding 23c on the lock only; 23c (the item-4
freeze) and 23b are not overwritten. **Found after the items, while checking this report's figures:
the quoted lock was not the lock the render draws** (section "Found after the items" below).

#### The headline, both figures (committed semi-bounded, nine pairings, median, 95 percent interval)

| | figure | configuration |
|---|---|---|
| **pre-registered** | **62.50** [30.00, 86.67] | freeze 23b: grid lattice, no veto |
| **post-amendment, shipped** | **73.33** [35.00, 87.50] | freeze 23c: the ONE lattice + `a_veto_1.0` |

| committed headline | E_col1 | E_col5 | E_row1 | E_row5 | session-01 folds (s0203, s02, s03 to s01) |
|---|---|---|---|---|---|
| pre-registered | 53.70 | 74.07 | 83.33 | 57.41 | 31.67, 30.00, 25.83 |
| shipped | **46.30** | 77.78 | 83.33 | 59.26 | 34.17, 35.00, 32.50 |

E_col1 is 4 walks lower than pre-registered: 3 to the lattice fix (not an arm), 1 to the veto (within
the amended (f)).

**The amendment, disclosed:** `a_veto_1.0` ships only because condition (f) was AMENDED by the
operator on 2026-09-23, POST HOC in those words. **Paired, shipped against pre-registered: +3.80
[0.83, 6.94]** over nine pairings; held-out seven +2.62 [-0.48, 5.96], interval including zero. The
difference of medians is +10.83, mostly the median landing on a different pairing on each side, so
**quote the paired figure beside the median, never the median alone.** Of the paired gain, the
lattice fix alone is +1.02 [-0.83, 2.87] (noise) and the veto +2.78 [0.93, 4.63].

**The lock AS DRAWN (held-out seven): 53.33 [26.67, 62.50]**, from 55.83 on the grid; paired -3.10
[-4.88, -0.95] (all nine -2.41 [-4.17, -0.65]). Edge recall at the lock 37.04 / 59.26 / **18.52** /
42.59; session-01 folds 26.67, 25.83, 20.00. It fell because the grid lock read a median 0.218 s of
radio not yet recorded at its frame. `runs/constrained/fh/d6_lock_commit/results.json`. *Quoted in
item 4 and freeze 23c as 50.00 from 57.50, which is the same decode at `sd_scale` 1.0; see below.*

#### What shipped

1. **The ONE lattice** (item 2, correctness, not an arm): the press-aligned lattice for everything
   drawn and quoted, defined once in `pipeline/constrained/lattice.py`.
2. **`a_veto_1.0` on the committed decision** (item 3): passes every condition under the amended (f).
3. **Nothing else.** Product fusion, `y2_dial` and switching were refused.

#### Item 1. The amended (f), applied to every arm refused since 2026-09-22

`reports/REEVAL_f_amended_2026-09-23.md`, 44 rows, only (f) re-read. **Two arms pass everything:
`y2_dial` at w 0.10 to 0.25 (the only arm the amendment changes; its pre-registered rule then picks
w = 0.25, +4.05 [2.26, 6.67]) and `a_veto_1.0` (passed before, had been declined by judgement).**
Product fusion on the committed answer at w = 0.25 passes (f) but fails its pre-registered (c);
switching fails the amended (f) on E_col5 -3 (the two-walk floor); every lock arm of t7, t9 and
fusion collapses the edges far past the floor. Recorded in SEMIBOUNDED_STATE section 10 and the BRIEF.

#### Item 2. The lock-phase fix

`reports/FIX_one_lattice_2026-09-23.md`. Seven hard-coded roots and the render script routed through
`lattice.py`; the default roots reproduce the press-aligned measurement **1080 of 1080 passes
identical**. The lock ends by its frame on **0 of 360** late passes; **the strict-xfail marker was
removed deliberately**. The live engine re-phases at the press: **20 of 20 aligned, 20 of 20 live
decisions equal to offline**, 15.8 ms per window (31.7x headroom). Known gap stated: pre-press windows
differ in phase live against offline, which matters once a live runner carries the A2 term.

#### Item 3. Product fusion on the committed decision, and the item-1 arms

`reports/ITEM3_REPORT_2026-09-23.md`. **Product fusion REFUSED.** The selection folds chose w\* = 1.0,
where (a), (b), (c) as clarified and substitution pass, +8.69 [3.10, 14.17] held-out, but the amended
(f) fails, net -20 walks (E_col5 -12). **At w = 0.25 it would pass every condition; it was not the
pre-registered choice and is not shipped.** That one is the operator's to decide, POST HOC. Split
(control T): 29 percent sharpening, 71 percent link agreement. **`y2_dial` refused on the one lattice**
(no weight meets the amended (f): E_row1 -1 on every weight, net -1). **`a_veto_1.0` ships**: +1.67
[0.24, 4.40], two passes, edge net +4; caveat carried: exactly on the bar, the two readings disagree
in sign (held-out difference of medians -0.83). Veto with fusion: +0.83 [0.24, 1.43] over fusion
alone, not shipped because fusion is not.

#### Item 4. The render, every rule-5 check computed

| check | result |
|---|---|
| rule violations | **0** over 5055 frames |
| dots missing after the first legal frame | **0** of 7756 |
| drawn-window causal bound / evidence causal bound | **-1.251 s / -1.251 s** |
| jumps over 0.5 m | 150, of which 120 at the lock |
| V1 latency | 2.0 s, every walk |
| V2 commit frame = marker frame | 0 violations, 120 walks |
| V3 lock offset | one value, 2.0 s |
| rule 6, leave together | 0 violations; max stall 0.5 s, 120 of 120 explained by the decoder |
| rule 2a anchor segment | 0 off-segment frames |
| V4 dwell | none; folder is six videos and ACCEPTANCE.md |
| on-screen tracking | **44.32 percent** within 0.5 m (41.66 on the grid lattice) |
| committed line as text at every walk end | yes |

PASSED on its first run. ACCEPTANCE.md, HANDOFF and STATE carry both headlines with the amendment
disclosed.

#### Item 5. DC2

- **Pre-registration amended before any Room B data** (`PREREG_DC2_crossroom_2026-09-22.md` s.10):
  DC2 tests the shipped configuration of 23c; primary A (unchanged) against B (gate re-anchored, null
  RELATIVE to the calibration walks' emission spread, `s_A` = 2.111 fixed now); confirmatory arms
  `a_veto_1.0` and `b_abstain_0.25`, each at 97.5 percent; (f) as amended. **"At the PRODUCT's scale"
  became the shipped MEAN scale, because product fusion did not ship**; the pipeline takes a fusion
  flag if that changes before Room B data exists.
- **A correction of the record:** Room B does NOT need a second (1.0 s) cut for the pool; every pool
  head is inferred over the 0.5 s windows. The ingest guard and its six tests were rewritten; the
  refusal now fires on a missing RAW capture.
- **Wired:** `dc2_pipeline` (ingest, orchestration, report) and `dc2_run` (view, cut, features, infer,
  decode). One command: `python3 -m pipeline.constrained.dc2_pipeline --room room_B`.
- **Stand-in plumbing check PASSED: 72 of 72 decisions equal to the shipped system's** on the same
  passes, from the raw files. It found two faults first, both of which would have produced wrong
  Room B numbers without a sound: **RSSI silently filled with zeros** (a hard-coded data root; now a
  refusal, tested) and the pre-press readers' head rule (recorded and pre-registered for DC2).
- **Room A heads for DC2 (sessions 01 + 02 + 03), stride-keyed, all trained: 18 of 18 load strictly**
  with the right tag, seed and output size and finite weights (the 0.5 s g25 and position heads; the
  three 1 s seeds; g100 from its restart after memory pressure). `runs/constrained/logs/d5_roomA3_check.log`.

#### Item 6. DC2 readiness

**The live rig run is BLOCKED: no receiver was attached** (`/dev/cu.*` shows Bluetooth and debug
only), and it needs a person walking. Its procedure is now the first section of
`reports/DC2_FIELD_CHECKLIST.md`. The checklist was corrected: one command cuts the ONE lattice; the
1.0 s cut only for within-DC2 training, into a stride-named tree (never `windows_w1`, which holds 1 s
windows, and never `windows_half`, the retired grid lattice); sidecars must record the reaction-time
bias applied; `calibration.json` is required.

#### Found after the items: the quoted lock was not the drawn lock

`reports/CORRECTION_drawn_lock_2026-09-23.md`, stage `d6_lock_commit`, freeze 23d. **No ship verdict
changes.**

- **Every lock figure since the causal correction decoded the display at the decision's `sd_scale`
  1.0; the render draws at 4.5.** 13 of 120 walks differ on the render's pairing, 0 at 4.5. Proven the
  only difference: recomputed at 1.0, the lock equals the quoted rows 1080 of 1080 on both lattices;
  at 4.5 it and the text answer equal ACCEPTANCE's per-walk tables 120 of 120.
- **ACCEPTANCE's "lock against the commitment" table was read from `r5_lock`** (2026-09-20: 1.5 s,
  grid lattice), printed as the 2 s lock. The writer now reads `d6` and prints STALE unless d6 matches
  the render walk for walk; ACCEPTANCE was corrected by hand in three marked places, because item 4
  said render once.
- **A NEW COST, disclosed: the ONE lattice costs the answer the video shows as text** (bounded rescore
  at the end press): 65.83 -> 60.00, **paired -2.59 [-4.63, -0.46], every edge line losing walks (net
  -18)**. As an arm it would fail the amended (f); it shipped as a correctness fix and was never
  measured on this answer. **The operator's to weigh.**
- **Open for the operator:** `y2_dial` was refused on the ONE lattice by one edge walk at `sd_scale`
  1.0; on the drawn decode it could go either way. Not re-measured; that would be a new arm
  evaluation, pre-registered first.
- DC2 prereg s.10 now names the display decode as "the render's own lock", written before any Room B
  data (the lock is a component, not a DC2 outcome).

#### Faults of mine this batch, each caught before a number was quoted

- `y2_dial`'s reproduction anchor was grid-only; re-keyed per lattice and recorded.
- A bare `else` in the measurement harness caught the new mode.
- The DC2 inference step imported a guarded module under the DC2 root.
- **The DC2 RSSI zero fill**, caught by the stand-in, not by me.
- Five three-session training jobs at once swapped the 24 GB machine; three were stopped and re-run
  one at a time.
- **Item 4 quoted the lock from `y4` rows without checking them against the render**, and left
  ACCEPTANCE's older table in place. Both caught before this report closed, by the reproduction check
  of the stage written to fix the table; the first version of that stage FAILED its check on exactly
  those 13 walks, which is how the decode difference was found.

#### Suite

**1159 passed, 8 skipped, 0 expected failures** (after the correction; 1155 before it).

---

## BATCH_2026-09-23e_REPORT.md

**Source:** `reports/BATCH_2026-09-23e_REPORT.md`, 2026-09-23. **SHA-256:** `4f758ce1957b0944e7c89f4572de69006b9c49f59ef67374f2a73bfa0b6bc4d4`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### Batch 2026-09-23e: closing report

Operator instruction 5, verbatim in `reports/BRIEF_render_and_prepress_2026-09-22.md`. Queue and log
`reports/QUEUE.md`. Every figure below is read from the results file named beside it.

**Freezes: `runs/TRACKING_FROZEN_2026-09-23e.json`** (the DC2 exploratory arm, before any Room B data)
**and `runs/TRACKING_FROZEN_2026-09-23f.json`** (the render). 23d and every earlier freeze are kept.
**The headline does not change:** pre-registered 62.50, post-amendment 73.33 [35.00, 87.50].

#### 1. Mid-walk switching, a display decision (item 1)

`reports/PREREG_switching_display_2026-09-23e.md` (written before any number), stage `e1_switch`
(VALID: the lock equals `d6_lock_commit` on 1080 of 1080 passes), one implementation
`pipeline/constrained/switching.py` shared with the render. RENDER_RULES rule 1 amended (section 1a).
**Disclosed beside it: as a decision arm it failed (f) in `y3_switch` (E_col5 -3 walks).**

theta was chosen on `s01_to_s02` and `s02_to_s01` only: **2.0 nats for both variants.**

| nine pairings, against lock-final | your rule | 1.5 m variant (rendered) |
|---|---|---|
| **time on the correct line, paired** | **+5.77 [3.47, 8.13]** | **+1.54 [0.57, 2.70]** |
| held-out seven | +6.71 [4.14, 9.36] | +1.78 [0.62, 3.23] |
| wrong-to-right / right-to-wrong / wrong-to-wrong | **162 / 49 / 153** | **37 / 10 / 49** |
| walks that switch | 364 of 1080 (33.7%) | 96 of 1080 (8.9%) |
| **jump distance, median; over 1.5 m** | 2.24 m; **297 of 364 (82%)** | 0.75 m; 17 of 96 (18%) |
| earliest switch after the lock | 1.0 s | 1.0 s |
| frame jumps over 0.5 m inside slides | 623 | 0 |
| substitution ratio (another participant's radio) | 0.82 | |

Both keep under the operator's rule (time on the correct line positive, wrong-to-right above
right-to-wrong). **More than a quarter of your rule's switches moved the dot over 1.5 m (82%), so
the restricted variant was also run and, as pre-registered, it is the one rendered.** The price is
stated: it keeps a quarter of the gain (+1.54 against +5.77).

**Wrong-to-wrong is large and is not in the keep rule:** 153 of your rule's 364 switches move the dot
from one wrong line to another, and 49 of the variant's 96. They cost nothing on time-on-correct and
they are visible on screen.

| edge line (54 walks each), your rule | lock right | end right | W2R | R2W |
|---|---|---|---|---|
| E_col1 | 20 | 26 | 6 | 0 |
| E_col5 | 32 | 35 | 4 | 1 |
| E_row1 | 10 | 36 | **26** | 0 |
| E_row5 | 23 | 31 | 11 | 3 |

| edge line, 1.5 m variant | lock right | end right | W2R | R2W |
|---|---|---|---|---|
| E_col1 | 20 | 20 | 0 | 0 |
| E_col5 | 32 | 34 | 2 | 0 |
| E_row1 | 10 | 13 | 3 | 0 |
| E_row5 | 23 | 23 | 1 | 1 |

Session-01 folds, time on correct, your rule against lock-final: 27.1 / 26.7, 26.6 / 25.8, 24.3 /
20.0 (W2R against R2W 15/11, 8/7, 14/6). The variant: 26.4 / 26.7, 25.8 / 25.8, 21.9 / 20.0.

Causal on both bounds, every switch: decision evidence -0.500 s (the window ending at the decision
frame finishes 2 us after it on the ONE lattice and is excluded); the drawn target's bounds are
reported by the render below.

#### 2. The end text is the shipped committed decision (item 2)

The walk-end text now names **"COMMITTED (shipped, semi-bounded)"**, the headline's own decision (A2 +
`a_veto_1.0`), and **equals `d4_headline`'s decision on 120 of 120 walks** (106 correct on this
pairing, 88.33 percent). The bounded rescore at the end press is no longer shown; **its cost under the
ONE lattice stays on record as the disclosed price of the correctness fix: 65.83 to 60.00, paired
-2.59 [-4.63, -0.46], every edge line losing walks**, in ACCEPTANCE (generated) and STATE.

#### 3. The render (item 3), every rule-5 check computed

| check | result |
|---|---|
| rule violations | **0** over 5030 frames |
| dots missing after the first legal frame | **0** of 7756 |
| drawn-window / evidence causal bound | **-1.251 s / -1.251 s** |
| jumps over 0.5 m | 145: **120 at the lock, 0 from a switch** (counted apart) |
| V1 latency / V2 commit = marker / V3 lock offset | 2.0 s / 0 violations of 120 / one value, 2.0 s |
| rule 6, leave together | 0 violations; max stall 0.5 s, 120 of 120 explained by the decoder |
| rule 2a anchor segment | 0 off-segment frames |
| V4 dwell; folder | none; six videos and ACCEPTANCE.md |
| **switches drawn (1.5 m variant, theta 2.0)** | **5 of 120 walks**: W2R 3, R2W 0, W2W 2; jumps 0.25 to 0.79 m; earliest 1.5 s after the lock |
| switch constraints | 0 in the final 1.0 m, 0 persistence violations, 0 back to the lock, 0 slide frames off segment |
| switch causal bounds | decision evidence -0.500 s; drawn target -1.000 s; target evidence -1.000 s (from the slide's first frame, with the step `simulate_walk` actually reads) |
| **render equals `e1_switch`, walk for walk** | **120 of 120** (run 2; see below) |
| on-screen tracking | **45.30 percent** within 0.5 m (44.32 in 23d) |
| end text equals the headline decision | 120 of 120 |

ACCEPTANCE's per-walk tables (locked, switched to, drawn at end, committed) are generated by the
render from its own decode, with no hand edit.

**THE RENDER RAN TWICE, disclosed.** Run 1 passed every rule-5 check but its own walk-for-walk check
against `e1_switch` reported 115 of 120. The fault was mine and in the CHECK: the render's switch record
carries no `switched` key and the comparison read the missing key as False, so each of the 5 switched
walks, identical in line and decision frame, compared as a mismatch. The comparison was fixed, the
contract test now recomputes the equality itself from the walk records instead of trusting the
render's flag, and the render was run once more so that ACCEPTANCE is generated correct rather than
hand-edited. **Run 2 against run 1, field by field: all 120 walks identical in every drawn field (positions, locked line, switch, drawn end line, committed text, tracking, jumps), every top-level check identical, and all six videos BYTE-IDENTICAL.** Only the check's report changed, to 120 of 120. Run 1 is archived in
`runs/constrained/demo_archive/_render_23e_run1_check_bug`.


#### 4. Product fusion at w = 0.25, EXPLORATORY for DC2 (item 4)

NOT shipped in Room A. PREREG_DC2 section 11.1, frozen in **23e** before any Room B data
(`data/room_B` absent): configuration B with every head's link posteriors fused at w = 0.25, the null
re-anchored at the PRODUCT's scale for that arm only, **`s_A,prod = 3.7428`** (computed as `s_A` on the
same 3394 Room A windows; the same code reproduces `s_A = 2.1108124982838437` exactly at w = 0), the
gate as B's (band energy is untouched by fusion). `dc2_pipeline --fusion ARM=W` per arm; the four
pre-registered arms are fixed at mean fusion and a flag on them is refused.

**The stand-in plumbing check re-passed** (`runs/constrained/fh/dc2_pipeline_standin_decoys/results.json`,
run with the decoys of item 6 present): **configuration A equals the shipped decisions 72 of 72,
EXACT**, and **the exploratory arm's fused pool, run unanchored with A2 alone, equals Room A's own
measurement of exactly that (`z3a_linkprod_pa_w025`) 72 of 72, EXACT**, so the flag reaches every head
as it did in Room A. On the stand-in the arm reads 88.89 [81.94, 95.83] with its relative null at
-7.11 (s_B,prod 3.551 against s_A,prod 3.743), a plumbing figure and never a result.

#### 5. `y2_dial` stays refused (item 5)

Recorded in the operator's words in REEVAL_f_amended, SEMIBOUNDED_STATE and the drawn-lock
correction's open item, which is closed by decision. Not re-measured.

#### 6. The fifth receiver (item 6)

Every tracking loader names RX1, RX2, RX3 (`recordings`, `splits.windows`, `realtime.engine`), and
the live engine drops packets from any other node. **The real hazard was elsewhere and is now
guarded:** the capture logger (protected, not edited) names AUTODISCOVERED ports RX1..RXN in sorted
port order, so a fourth board could be recorded AS a tracking node. `pipeline/constrained/nodes.py`
checks every tracking name against its Room A board's MAC (from the Room A sidecars, identical across
all three sessions); DC2 REFUSES a tracking board under another name or a tracking name on another
board (`--node-macs-changed-ok`, stamped, for a deliberate board change). The checklist names it RX4,
requires an explicit `--nodes` mapping and a four-way streaming check.

**Tests, 9 in `tests/test_fourth_receiver.py`:** the three loaders agree on the names; no tracking loader globs capture files; with
decoys RX0 (a copy of RX3, sorts first) and RX4 (a copy of RX2, sorts last) the cutter opens exactly
RX1, RX2, RX3 and the live engine's windows and gates are identical with and without the decoys
streaming; the identity check accepts an extra board, refuses a mislabel and a changed board.

**End to end, the fifth-receiver test: the whole DC2 path run from raw files with the RX0 and RX4 decoys
beside every recording reproduces the shipped system's decisions 72 of 72, EXACT**; the node check
reported the extras [RX0, RX4], no mismatch and no swap. Those 9 and the 6 ingest-guard tests pass.

#### 7. The live rig run (item 7): BLOCKED ON OPERATOR, command prepared

`scripts/live_rig_run.sh --participant P01 --baseline <dir>`: a short prompt, every board identified
by MAC and named by MAC, the capture with that explicit mapping, a live follower that reads the
capture files as they grow and prints packets, loss and windows per link every 0.5 s, and per-link
loss, latency and live-fit timestamp drift at the end. Tested on a simulated growing capture (4
tests: whole frames only, each once, RX4 never pushed, drift measured, MAC naming, refusals). **It
does not draw the live dot**: the pooled live runner is the known gap in `tracker_live`, stated.
`/dev` held only Bluetooth and the debug console at every check-in.

#### Suite

**1199 passed, 8 skipped, 0 expected failures** (1159 before this batch; the new tests are the switching (16), fourth-receiver (9) and rig-run (4) files and the registrations).

---

## BATCH_2026-09-23f_REPORT.md

**Source:** `reports/BATCH_2026-09-23f_REPORT.md`, 2026-09-23. **SHA-256:** `68babf7798fa30268d0387860a624540f43523d695381077a3b139bfdcb61343`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### Batch 2026-09-23f: closing report

Operator instruction 6, verbatim in `reports/BRIEF_render_and_prepress_2026-09-22.md`. Queue and log
`reports/QUEUE.md`. Every figure is read from `runs/constrained/fh/e2_switch/results.json` or
`runs/constrained/fh/f3_render/results.json`. **Freeze `runs/TRACKING_FROZEN_2026-09-23g.json`**; 23f and
every earlier freeze are kept. **The headline does not change: 62.50 pre-registered, 73.33
post-amendment.**

#### 1. The three arms (`e2_switch`, pre-registered in `reports/PREREG_switching_arms_2026-09-23f.md`)

VALID: arm A reproduces the previously measured rule (`e1_switch`) at every theta on 1080 of 1080 walks,
and the lock equals `d6_lock_commit` on every pass. All arms: 1.5 m proximity, two consecutive checks,
radio to t + 2.0 s only. **theta was chosen per arm on `s01_to_s02` and `s02_to_s01` only, and was 2.0
for all three.**

| nine pairings | A: 1 switch, final 1.0 m | B: 2 switches, final 1.5 m | **C: 1 switch, final 1.5 m** |
|---|---|---|---|
| time on correct line, paired against lock-final | +1.54 [0.57, 2.70] | +1.54 [0.57, 2.70] | **+1.54 [0.57, 2.70]** |
| held-out seven | +1.78 [0.62, 3.23] | +1.78 [0.62, 3.23] | **+1.78 [0.62, 3.23]** |
| wrong-to-right / right-to-wrong / wrong-to-wrong | 37 / 10 / 49 | 37 / 10 / 50 | **37 / 10 / 48** |
| dot ENDS on the committed line (of 1080) | 647 | 647 | **647** |
| end-of-walk text contradicts the dot | 433 | 433 | **433** |
| switch events; per walk | 96; 0.089 | 97; 0.090 (2 walks switched twice) | **95; 0.088** |
| jumps over 1.5 m | 17 | 17 | **17** |
| median time of each switch after the lock | 2.0 s | 2.0 s; the second 4.0 s | **2.0 s** |
| qualifies | yes | yes | **yes** |

Edge-line walks (54 each; lock right / end right / W2R / R2W), identical in all three: E_col1 20 / 20 /
0 / 0, E_col5 32 / 34 / 2 / 0, E_row1 10 / 13 / 3 / 0, E_row5 23 / 23 / 1 / 1. Session-01 folds, time on
correct against lock-final: 26.4 / 26.7, 25.8 / 25.8, 21.9 / 20.0 (W2R against R2W 4/5, 2/2, 5/1).

**The selection, by the operator's fixed rule:** all three qualify (the held-out interval is above zero
and W2R exceeds R2W); all three are within one walk per pairing on end-on-committed agreement (647
each); the fewest switches decides: **arm C, at most one switch, none in the final 1.5 m.** The
operator's two-switch proposal (B) is almost exactly A and C: its second switch fired on 2 walks of 1080.

#### 2. How switching works, and the investigation

`reports/INVESTIGATION_switching_2026-09-23f.md`.

- **The lock uses the edge-safe display decoder; a switch hands the dot over to the final-answer scorer
  (the committed decision's own estimator) once it is confidently different.**
- **The two estimators disagree at the lock on 363 of 1080 walks (33.6 percent)**, per pairing 20.0 to
  43.3 percent, 20.8 on the demo pairing.
- **74.7 percent of arm C's switches (71 of 95) go to the line the scorer already preferred on the
  lock's own radio: most switches reconcile the two estimators rather than react to new mid-walk
  evidence.** Wrong-to-right 30 reconciling against 7 new-evidence; right-to-wrong 9 against 1.
- 280 of the 363 disagreeing walks never switch (blocked by proximity, persistence or the final zone),
  which is why the text still contradicts the dot on 433 walks.
- **The lead:** on the lock's own radio the scorer is right more often than the display lock, **+4.17
  [0.93, 8.33] paired, held-out +5.83 [2.74, 10.24]** (median 57.50 against 53.33), and it is not worse
  on the edge lines (net +1 walk). Measured, "edge-safe" is the display decoder's history rather than
  an advantage it shows here. **The lever is the lock, not the switch.** This is after the fact: a lock
  arm would need its own pre-registration and the full ship rule.

#### 3. The render, every rule-5 check computed

| check | result |
|---|---|
| rule violations | **0** over 5030 frames |
| dots missing after the first legal frame | **0** of 7756 |
| drawn-window / evidence causal bound | **-1.251 s / -1.251 s** |
| jumps over 0.5 m | 145: **120 at the lock, 0 from a switch** |
| V1 latency / V2 commit = marker / V3 lock offset | 2.0 s / 0 violations of 120 / one value, 2.0 s |
| rule 6, leave together | 0 violations; max stall 0.5 s, 120 of 120 explained by the decoder |
| rule 2a anchor segment; V4 dwell; folder | 0 off-segment; none; six videos and ACCEPTANCE.md |
| **switches drawn (arm C)** | **5 of 120 walks: W2R 3, R2W 0, W2W 2**; jumps 0.25 to 0.79 m; earliest 1.5 s after the lock |
| switch constraints | 0 in the final zone, 0 persistence violations, 0 back to a drawn line, 0 slide frames off segment |
| switch causal bounds | decision evidence -0.500 s; drawn target -1.000 s; target evidence -1.000 s |
| **render equals `e2_switch`, walk for walk** | **120 of 120** |
| end text equals the headline decision | 120 of 120 |
| dot ends on the committed line | 89 of 120 |
| on-screen tracking | 45.30 percent within 0.5 m |

On the demo pairing arm C draws exactly the same five switches as arm A did in 23e, so the videos show
the same walks switching. ACCEPTANCE and STATE describe switching as above, with the disagreement rate
beside it; ACCEPTANCE is generated by the render, with no hand edit. RENDER_RULES rule 1a is amended to
arm C as an operator decision.

**Disclosed: the first render attempt crashed on its first recording.** A fault of mine: the switch list
reused the walk record's integer `switches` field (the lock count), which a later line overwrote, and the
frame callback failed iterating it. It was stopped by its process id before completing any video; the
field was renamed `mid_switches`, and the render that completed is the one reported and frozen. Log:
`runs/constrained/logs/f3_render_23f_attempt1_crash.log`.

#### 4. Still open

- **The live rig run: BLOCKED ON OPERATOR** (no receiver attached at any check-in); `scripts/live_rig_run.sh`.
- **For the operator:** whether to pre-register a lock read from the final-answer scorer (section 2).

#### Suite

**1229 passed, 8 skipped, 0 failures** (1199 at the end of batch 23e; the new tests are the second-switch unit tests, the K-switch contract tests and the new stage's registrations).

---
