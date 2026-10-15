# RECORD_IDENTIFICATION_HISTORY: the closed identification batches' working files

Written 2026-09-24 09:49 SAST. The IDMAX batch's queue, check-in log and closing report, and version 0 of the DC2 identification sheet, verbatim (headings demoted two levels). The identification record itself is `reports/IDENTIFICATION_2026-09-18.md`, and the quotable figures are in `reports/ID_QUOTABLE_2026-09-23.md`. No participant is named in any section. `CLOSING_IDGP_2026-09-23.md` is not repeated here: its full text is already in the appendix of the identification record (SHA-256 checked), so that is its home.

## Index

| source | date | one-line summary | original |
|---|---|---|---|
| [DC2_ID_PROTOCOL_2026-09-23.md](#dc2-id-protocol-2026-09-23md) | 2026-09-23 | Version 0 (provisional) of the DC2 identification sheet. | combined here; at the tag `pre-cleanup:reports/DC2_ID_PROTOCOL_2026-09-23.md` |
| [QUEUE_IDMAX.md](#queue-idmaxmd) | 2026-09-23 | The IDMAX batch's queue (closed). | combined here; at the tag `pre-cleanup:reports/QUEUE_IDMAX.md` |
| [CHECKIN_LOG_IDMAX.md](#checkin-log-idmaxmd) | 2026-09-23 | The IDMAX batch's check-in log. | combined here; at the tag `pre-cleanup:reports/CHECKIN_LOG_IDMAX.md` |
| [CLOSING_IDMAX_2026-09-23.md](#closing-idmax-2026-09-23md) | 2026-09-23 | The IDMAX closing report. | combined here; at the tag `pre-cleanup:reports/CLOSING_IDMAX_2026-09-23.md` |

---

## DC2_ID_PROTOCOL_2026-09-23.md

**Source:** `reports/DC2_ID_PROTOCOL_2026-09-23.md`, 2026-09-23. **SHA-256:** `95175e9b28437d1794825421301f5d9be2a1d551d6fc5e522e56df2bb9465414`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** Superseded by versions b, c and d; the current sheet is `reports/DC2_ID_PROTOCOL_2026-09-23d.md`.

### DC2 identification sheet, 26 and 27 September. **v0, PROVISIONAL**

**v0, written 2026-09-23 01:00 SAST from the known constraints, before `id11`'s inventory and
before the power analysis had run.** It exists early on purpose, so the hard deliverable is on
paper whatever later stages do. `id15` supersedes it with the final version; if `id15` does not
finish by 12:00 SAST on Thursday 24 September, **this sheet stands** and is updated later with a
dated note. Numbers marked **[v0 DEFAULT]** are placeholders that the power analysis replaces.

**This sheet supersedes `reports/DC2_PROTOCOL_2026-09-18.md` for identification items only.** Every
tracking item on that sheet, including the start-of-day calibration block added 2026-09-22, stands
unchanged. Conflicts are listed at the bottom and **the merge of the two protocols into one day is
Uzayr's decision, not this sheet's.**

---

#### 1. The corridor

| item | specification |
|---|---|
| **path** | one straight path, chosen **on the morning of DC2** with `pipeline/identify/id15_factor_map.py`, once the new room's node coordinates are measured |
| **recorded length** | as long as the room allows. Target **at least 7 m, or at least six gait cycles, whichever the room permits**. A room diagonal is the natural candidate |
| **run-up and run-out** | **at least 1 m beyond each mark, walked but outside the scored segment**, so the scored segment is steady-state walking with no acceleration or braking |
| **geometry** | kept away from every TX-RX line of sight. **No link below F = 0.3 for more than 25 percent of the path length**, where F = \|(u_TX + u_RX) . v_hat\| / 2 |
| **direction** | **one designated forward direction.** The return walk goes off the corridor if the room allows; if not, it is recorded as a separate, labelled reverse condition |

**Why 7 m. CORRECTED 2026-09-23 06:00, and the original reasoning was WRONG.** The v0 sheet said
Room A's walks give about 2.5 gait cycles against the six that autocorrelation needs, and called
short walks the most likely reason identification has failed. **`id11` measured it and that is not
so.** The 2.5 figure came from `id1_foundations`, which times mode == 'walk' alone because the
tracker needs an interpolated position; the GAIT features also use `walk_edge`, and the span they
actually see is **11.0 s, giving 12.87 gait cycles per pass against the six needed.**

**Pass length is therefore NOT the binding constraint, and lengthening the walk is not the fix.**
The longer corridor is still worth having, for steady-state walking away from the acceleration and
braking at the marks and for more cycles per pass, but it should not be bought at the cost of
items that address the real constraints: **the geometry (section 1b), the number of separated
blocks (section 2), and the pace blocks (section 3).** If the room forces a choice, drop corridor
length first.

**Why away from the line of sight.** Path-length rate is dL/dt = (u_TX + u_RX) . v, which is
**exactly zero on the TX-RX line of sight**. Walking across a line of sight produces a shadowing
dip, not Doppler. This replaces the old "cross each line of sight at 30 degrees or more" rule.

#### 1b. NODE PLACEMENT. Added 01:25, and it outranks the corridor choice

**Measured, not argued** (`reports/PREREG_ID_2026-09-23_ADDENDUM_A.md`, figures F17 and F17b):

- **All twelve Room A lines fail the F gate.** So does every straight 4 m, 5 m and 7 m segment
  anywhere in the room. Room A has no compliant corridor and never had one.
- **Line A is exactly zero on RX1 for its whole length**, because it runs straight along the
  TX-RX1 sight line, where the two rays cancel. Everyone walked it 3 times.
- Over 543,004 candidate layouts on a 5 by 5 perimeter, scoring the 7.07 m diagonal:

| nodes spread over | best min-link mean F | worst link below F = 0.3 |
|---|---|---|
| **2 walls, clustered at the corridor's origin corner** | **0.938** | **0 %** |
| 3 or 4 walls | 0.456 | 32 % |
| **current Room A layout** | **0.373** | **43 %** |

**No layout spread over three or more walls passes the gate.** The trade-off is hard.

**THEREFORE, for DC2: run `pipeline/identify/id15_factor_map.py` BEFORE the nodes are fixed, not
after.** Choosing the corridor after mounting the nodes is choosing from an empty set, which is
exactly what happened in Room A. The tool takes room dimensions and candidate node coordinates and
runs in under a minute on a laptop.

**THIS CONFLICTS DIRECTLY WITH TRACKING AND IS UZAYR'S DECISION.** Tracking wants nodes spread for
multilateration; gait Doppler wants them gathered near one end of the walk, which is the doorway
geometry WiWho and Gate-ID use. A gait-first layout gives **2.5 times the projected Doppler factor**
of the current one. Options, in the order this sheet would rank them for identification:

1. **Gait-first corner layout for a dedicated identification block**, nodes re-mounted for that
   block only. Best for identification, costs room time and breaks tracking comparability.
2. **Compromise: keep the tracking layout, choose the corridor to favour the two best links**, and
   accept that one link contributes nothing. Identification stays marginal but DC1 and DC2 remain
   comparable.
3. **Keep the tracking layout unchanged and treat identification as a measured negative.** Costs
   nothing and is the honest fallback if the day runs short.

#### 2. Blocks. This is the item that makes within-day evaluation valid for the first time

| item | specification |
|---|---|
| **blocks per person per day** | **4 to 5, separated in time** (was 3), spread across morning and afternoon. Measured at ICC 0.421: blocks buy information, extra passes inside a block do not |
| **order** | round-robin across participants, **participant order randomised per block** |
| **blocks per day** | **4 to 5 separated blocks. THIS IS THE BINDING NUMBER, see below** |
| **passes per block** | **8 forward passes**, measured as sufficient once the block count is right |

**MEASURED 2026-09-23 10:20, and it changes this section's advice. The within-recording ICC is
0.421**, estimated from 54 recording groups of 20 passes each in `id14`. The v0 sheet's number was
computed from an ASSUMED 0.1 because the corridor pilot could not measure it, and at 0.421 the
picture is very different.

**Power grid at the measured ICC**, against the pre-registered targets of a 95 percent interval no
wider than plus or minus 10 points and 80 percent power to detect 35 against 16.7 percent:

| blocks per day | passes per block | total per person | interval half-width | power |
|---|---|---|---|---|
| 2 | 8 | 16 | 17.7 pts | 0.52 |
| 2 | 20 | 40 | 16.7 pts | 0.58 |
| 3 | 8 | 24 | 14.6 pts | 0.69 |
| 4 | 8 | 32 | **12.8 pts** | **0.82** |
| 5 | 8 | 40 | **11.5 pts** | **0.89** |
| 5 | 20 | 100 | **10.9 pts** | 0.93 |

**Read the columns against each other, because that is the finding.**

- **Going from 2 blocks to 5 blocks moves the half-width from 17.7 to 11.5.**
- **Going from 8 passes to 20 passes INSIDE a block moves it from 17.7 to 16.7.**

At an ICC of 0.42 extra passes in the same block are nearly redundant, because they are correlated
with each other. **Extra separated blocks are what buy information.** The v0 sheet led with passes
per block; that was the wrong lever and this table corrects it.

**BLOCKS ARE THE PROTOCOL'S MOST IMPORTANT NUMBER. Maximise separated blocks per day, and only
then passes per block.** A practical target is **4 to 5 blocks of 8 passes**, 32 to 40 passes per
person per day, which reaches the power target and gets the interval to about 11 to 13 points.

**AND A SIX-WAY RESULT STILL WILL NOT MEET THE INTERVAL TARGET.** Zero of the 28 designs searched
reach plus or minus 10 points; the best anywhere in the grid is 10.9 at 100 passes per person per
day, which is not a realistic ask. Three honest responses, and the choice is Uzayr's:

1. **Accept a wider interval.** State plus or minus 12 points as the design target and say why.
2. **Commit to a smaller cohort.** At three people chance is 33.3 percent and the same passes buy
   a far tighter answer. DC1 already put three-person identification at 50.5 percent.
3. **Attack the ICC itself, which is what blocks do.** The 0.421 was measured where each
   participant-session is a SINGLE recording. Splitting a day into separated blocks changes the
   unit and should lower it, so the measured figure is an upper bound rather than a fixed constant.

**Why blocks.** All 18 participant-session cells in DC1 hold exactly **one** recording, so within a session
the recording and the identity are perfectly confounded and **no within-day figure in this project
has ever been able to support a claim**. Three separated blocks per day breaks that confound and
makes cross-block within-day evaluation possible for the first time.

#### 3. Pace. The decisive gait-versus-pace test. Keep this item even if the day runs short

| block type | amount |
|---|---|
| natural pace | **at least 2 blocks per person per day** |
| **pace block** | **1 block per person per day**: self-selected slow and fast passes, randomised order, **each pass labelled** |

**Enrol on the natural-pace blocks, then identify on the slow and fast passes.** Speed matching
fails this by construction; real gait identification should survive it. On DC1 the speed-only
control beats every gait arm (28.33 against 23.33 percent at k = 1), so **without this block the
thesis cannot distinguish gait identification from pace recognition at all.**

#### 4. Baselines, keypresses and metadata

| item | specification |
|---|---|
| **empty room** | at least **2 minutes at the start and 2 at the end of each session** |
| **standing** | **20 s at the corridor start, per participant per block** |
| keypresses | at the start and end marks, **used only to validate onset and offset detection**, never as a speed feature |
| metadata per block | shoes, outer clothing, nothing carried in the hands |
| **radio configuration** | **identical to DC1**: same channel, packet rate, binary encoding, node heights, board orientation and facing rules. **Log the channel number** |

The empty-room and standing blocks are the two nulls that the M1 periodicity metric needs.
**And the standing block is the more important of the two** (`PREREG_ID_2026-09-23_ADDENDUM_C.md`):
DC1 has no empty-room or dwell recording at all, and M1 has to fall back on `idle` and `grid`
windows found inside the walk recordings. An empty room tests the easy case; a **present but still
body** tests the case that has actually been failing, which is why the 20 s standing block is not
optional. DC1's
periodicity diagnostic found rhythm on 60 percent of walking pass-links **and 35 percent of standing
ones**, and without both nulls that gap cannot be measured, let alone widened.

#### 5. Time estimate

A 7 m pass at about 1.3 m/s takes about 5.5 s; with the return and a reset, about 15 s per pass.

**6 people x 3 blocks x 8 passes x 15 s = about 36 minutes of walking per day**, before
changeovers, baselines and the standing blocks. Allow **90 minutes of room time per day** for the
identification protocol as specified.

#### 6. What each item enables

| item | the analysis it enables |
|---|---|
| 7 m corridor, six cycles | autocorrelation gait cycle, stride-normalised leg contour, cycle-to-cycle variability. All of A2 and A4 |
| one fixed corridor | removes the line-agreement problem: DC1's live tracker supplied the line at 57.5 percent agreement, which `id8` showed is worth no more than a randomly permuted line |
| one forward direction | comparable gait-cycle shapes across people; avoids Gate-ID's mirror-pattern confound |
| 3 separated blocks | the first valid within-day identification figure this project has had |
| **pace block** | **R6 and R7. The gait-versus-pace verdict** |
| empty room and standing | M1, M4, the C4 notch evidence, and the noise floor |
| keypresses | validation of sensed onset and offset, and nothing else |
| shoes and clothing log | the confound check on any cross-block result |
| radio identical to DC1 | lets DC1 and DC2 be pooled, and feeds the frozen tracking model unchanged |

---

#### 7. Conflicts with the 18 September sheet, stated plainly

| # | conflict | this sheet's position |
|---|---|---|
| 1 | **Time.** The 18 Sept sheet asks for 20 to 30 passes per person across 12 lines with edge lines over-sampled. This sheet asks for about 24 corridor passes per person per day in 3 blocks. **Both cannot have the same room time** | Unresolved by design. **Uzayr decides the split.** The tracking arm currently has the stronger result |
| 2 | **The approach walk.** The 18 Sept sheet (added 2026-09-21) wants the approach walk before each press **recorded and labelled**. This sheet wants **run-up excluded from the scored segment** | **Both, and there is no real conflict:** record continuously, and mark the steady-state segment with the start and end marks. Tracking gets its labelled approach; identification scores only between the marks |
| 3 | **Line coverage.** The 18 Sept sheet over-samples edge lines. A single corridor samples one geometry | Keep a reduced 12-line block for tracking. **The corridor is additional, not a replacement**, and the corridor is chosen by geometry, never by accuracy |
| 4 | **Speed variation.** Both sheets carry it, and the 18 Sept sheet already calls it the single most important identification item. This sheet **structures** it: enrol on natural pace, test on slow and fast | This sheet's structure supersedes. The requirement is unchanged |
| 5 | **Calibration block.** The 18 Sept sheet's start-of-day empty room, standing and calibration walks | **No conflict, and they overlap.** The identification empty-room and standing baselines can be the same blocks, provided the timings are logged |
| 7 | **Node placement.** The 18 Sept sheet fixes node height and orientation to match Room A but says nothing about positions in the new room. Section 1b shows positions dominate every gait figure | **Unresolved, and it is the biggest one.** Section 1b lists three options ranked for identification. The decision is Uzayr's and it should be made before DC2, not on the morning |
| 6 | **Video.** The 18 Sept sheet asks for frame-synchronised video of every walk | **Keep it, and it matters more here.** It is the only way cadence and stride become measured ground truth rather than spectral inference, and it would settle whether DC1's 115-of-360 stride-rate dominance is real gait asymmetry or an envelope artefact |

---

#### 8. What is still missing from v0

- **Passes per block and blocks per day from the power analysis** (`id15` step 5), for a 95 percent
  CI half-width of at most 10 points and 80 percent power to detect 35 against 16.7 percent chance.
  Until then, 8 passes per block is a default, not a measurement.
- **The corridor itself**, which cannot be chosen until the new room's node positions are measured
  on the day. The geometry tool is the deliverable that makes that a one-minute job.
- **Confirmation of the six-cycle figure** from `id11`'s gait-cycle inventory.

---

## QUEUE_IDMAX.md

**Source:** `reports/QUEUE_IDMAX.md`, 2026-09-23. **SHA-256:** `03d6125c803914911d0252549e84e1e34e2332b1ad44e9f0c94b627c9ac394f4`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### QUEUE_IDMAX. The authority on what to do next in the gait identification maximisation run

**RULE: on every wake read THIS FILE FIRST and start the next PENDING item immediately. Never end a
turn while an item is PENDING or RUNNING unless a background job is running and will notify on
completion. Never wait for the operator between items. A blocked item is marked BLOCKED with its
reason and the next one starts.**

Batch `2026-09-23b` (IDMAX) opened 2026-09-23 11:50 SAST. The brief is the operator's
"Identification by gait: maximisation across days and within days, plus the DC2 update".
Deadlines: item 1 by **12:00 SAST Thu 24 Sep**; the queue by **18:00 SAST Thu 24 Sep**, but
tracking's ETA always wins over that deadline and the 0b restrictions are never lifted to meet it.

**Coexistence.** The tracking workstream (batch 2026-09-23c, `reports/QUEUE.md`) is running and has
priority. This run writes only `reports/QUEUE_IDMAX.md`, `reports/CHECKIN_LOG_IDMAX.md`,
`runs/identify/logs/*idmax*`, `runs/identify/logs/governor*`, `runs/identify/idmax/`,
`pipeline/identify/` stages id19 onward, and the report and freeze files the brief names. It never
signals a process it did not start. Tracking PIDs are identified by the governor at every sample.

#### Keep-alive, this run's own PIDs

| what | pid | started |
|---|---|---|
| caffeinate -dimsu | 98980 | 11:54 |
| yield governor (`pipeline/identify/yield_governor.py run`) | 98981 | 11:54 |
| watchdog (`scripts/watchdog_idmax.sh`, heartbeat every 15 min) | 98982 | 11:54 |
| chain runner `scripts/idmax_chain.sh` (items 3 to 10, pool within the governor budget) | 4901 | 12:32 |
| compute jobs | registered in `runs/identify/logs/idmax_pids.tsv`; id20 is 2547 | |

#### Items

| # | item | status | next action | ETA |
|---|---|---|---|---|
| 1 | DC2 protocol update, `reports/DC2_ID_PROTOCOL_2026-09-23b.md` | **DONE** 12:10, path revised 13:00 | path now E_col1 by item 6's nested choice (the brief's rule); flagged unvalidated, E_row1 override is Uzayr's | done |
| 2 | Audit: the three open issues, CSI-only cadence, steady-state segmentation | **DONE** 12:25 | `reports/FINDINGS_stageid19.txt`; bank + 7 feature variants built | done |
| 3 | Positive controls (direction, line, session, synthetic cadence, shuffle) | **DONE** 12:39 | NOT BROKEN; `reports/FINDINGS_stageid20.txt` | done |
| 4 | Baselines in every scope, plus both references | **DONE** 12:53 | `reports/FINDINGS_stageid21.txt` | done |
| 5 | Maximisation sweep, nested | **DONE** 13:33 | `FINDINGS_stageid22.txt` | done |
| 6 | Identification path | **DONE** 12:44 | `reports/FINDINGS_stageid23.txt`; every path at chance | done |
| 7 | Voting and day alignment | **DONE** 13:38 | `FINDINGS_stageid24.txt` | done |
| 8 | Learned models (group D) | **DONE** 13:33, diagnostics 13:53 | `FINDINGS_stageid25.txt` | done |
| 9 | Final evaluation, speed diagnostic, post-hoc ceiling, DC2 freeze | **DONE** 13:41, PARTIAL | `FINDINGS_stageid26.txt`; fault 3 | done |
| 10 | Report, figures, freeze, tests, closing report | **DONE** 13:59 | `reports/CLOSING_IDMAX_2026-09-23.md` | done |

ETAs assume the governor pauses this run for about a quarter of the time while tracking runs.

#### Log

- 2026-09-23 11:50 SAST: batch opened. Read the closing report, the 09-23 report section, the old
  DC2 sheet and the fault log. Tracking is live: `y4_pressalign` prep-head x6 plus `z3a_linkprod`
  and `z3b_g100native`, nine python PIDs, GPU at 94 to 99 percent. This run starts on CPU.
- 2026-09-23 11:54 SAST: caffeinate, governor and watchdog started and verified alive. Governor
  sees 9 tracking PIDs, 3 to 5 idle cores, memory normal, mode RESTRICTED.
- 2026-09-23 12:10 SAST: item 1 DONE. `reports/DC2_ID_PROTOCOL_2026-09-23b.md`, path E_row1 walked
  (0.0, 0.5) to (5.0, 0.5), decided by `id15_factor_map` (highest min-link mean F, 0.458).
- 2026-09-23 12:11 SAST: id19 bank built, 360 passes, contract MET, two single-thread workers.
- 2026-09-23 12:20 SAST: seven feature variants built, each 360 x 8517, contracts MET.
- 2026-09-23 12:20 SAST: FAULT 1 of this run, and it crashed rather than producing a null:
  `job_start` imported torch into a scikit-learn job; at two threads the two OpenMP runtimes
  collided (pthread_mutex_init failed, segfault). torch is now imported only by torch jobs.
  id20 resumed from its checkpoint.
- 2026-09-23 12:25 SAST: item 2 DONE. walk_edge is 9.0 s, about half steady walking; CSI-only
  cadence does not agree across links (median spread 0.6 Hz) and is not stable within a person
  (ICC 0.018). `reports/FINDINGS_stageid19.txt`.
- 2026-09-23 12:22 SAST: the governor paused id20 (idle 0.66 cores; tracking launched eight
  z3 workers). It resumes at 2 idle cores for two samples. Working on code meanwhile.
- 2026-09-23 12:32 SAST: all stage code written (id21 to id26), guard tests 18 passed.
  `scripts/idmax_chain.sh` launched (PID 4901): it waits for id20, stops if the controls are
  BROKEN, then runs id21, id22 (five workers), id23 and id25 as a pool within the governor's
  thread budget, then id24, id26 and id27, each behind an output contract.
- 2026-09-23 12:36 SAST: id27_report (figures, tables, freeze) written. Guard tests 18 passed;
  four in-memory mutations (stem guard, a test-side leak into selection, a gait set reaching the
  static levels, a train/test overlap) are each caught. Tracking now runs 11 processes and idle
  cores are 0.05, so id20 stays paused; the chain waits behind it.
- 2026-09-23 12:37 SAST: the governor resumed id20 after 870 s paused (idle 8.58 cores).
- 2026-09-23 12:39 SAST: item 3 DONE, BROKEN = False. Direction 94.4 (chance 50), line 72.8
  (8.3), session on new people 80.4 (33.3), injected rhythm 32.2 (16.7), shuffles at chance.
  The chain started the pool: id21 launched at budget 4.
- 2026-09-23 12:53 SAST: item 4 DONE. Nested gait baseline LOSO 18.89 [13.06, 25.01], p 0.16;
  recording signature 91.7 within-day and 20.3 cross-day; S0 32.5. `FINDINGS_stageid21.txt`.
  Pool: id22 cross, wdt, lolo01, lolo02, lolo03 and id23 launched; id25 waits for a slot.
- 2026-09-23 12:44 SAST: item 6 DONE. Every directed line at chance cross-day; the nested path
  choice picked C_rev, B_fwd, E_col1 in the three folds and scored 13.3 held out (n = 30).
- 2026-09-23 13:00 SAST: DC2 sheet path REVISED once, E_row1 to E_col1, because the brief's rule
  takes item 6's nested choice when it exists before the deadline. The all-sessions run of the
  procedure picks E_col1 (25.0 mean inner, E_row1 16.7). The dated note sets out that the choice
  failed its own held-out test and names E_row1 as the geometric alternative; the override is
  Uzayr's. id27 now reads the path from `id23_path/dc2_path_choice.json`.
- 2026-09-23 13:12 SAST: FAULT 2 of this run, and it stopped loudly rather than producing a
  number: the per-model DTW ranking found no fittable candidate on s0203_to_s01, because DTW needs
  templates and that fold's LDA shortlist held none. Fixed by a rule set before any DTW score: DTW
  is offered only template-bearing feature sets, under its own name `MODEL_dtw1nn_tpl` so it never
  pools with the two folds checkpointed under the old set. The UNION, all seven blocks and 14 of
  18 model rankings had already finished (206 folds) and are unaffected. The relaunch at 13:13
  resumed from the checkpoint. (A first relaunch did not start: zsh does not word-split an
  unquoted prefix variable; relaunched through bash.)
- 2026-09-23 13:11 SAST: id25 learned models launched on CPU (the GPU gate was closed, tracking at
  99 percent GPU).
- 2026-09-23 13:41 SAST: the chain finished, every output contract MET. Final nested cross-day
  LOSO 15.83 [10.28, 21.67]. Learned family (2D CNN on Doppler spectrograms) 27.22 [21.11, 33.61].
- 2026-09-23 13:53 SAST: id26b CNN diagnostic: it reproduces 27.22 exactly; with speed regressed out
  of the embedding, 23.89 [17.22, 31.39], p 0.013; with shuffled test speeds, 27.78.
- 2026-09-23 13:52 SAST: FAULT 3. The brief's residualised speed diagnostic re-injects test oracle
  speed for an RF head (27.50 true against 16.39 shuffled). Not quotable; linear heads unaffected.
- 2026-09-23 13:57 SAST: FAULT 4. A test call had written the real READS.log (a DEMO entry from the
  12:34 mutation check, no file opened). Tests now use a private log; the entry is documented in
  READS.not_reads.tsv. Tracking's pass-key audit flagged format colons in two file-name f-strings;
  reformatted, with the paths unchanged. Full suite: 1105 passed, 8 skipped, 1 xfailed.
- 2026-09-23 13:59 SAST: BATCH CLOSED. Every item DONE, none BLOCKED. Closing report written;
  check-ins cancelled; this run's watchdog, governor and caffeinate stopped.

---

## CHECKIN_LOG_IDMAX.md

**Source:** `reports/CHECKIN_LOG_IDMAX.md`, 2026-09-23. **SHA-256:** `900f27b03a2bd7fc4d8354d80d85e0939f1f0d8c43cf8fa4d98e34dd104e2288`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

### CHECKIN_LOG_IDMAX. One line per 15-minute check-in, newest last

- 2026-09-23 12:30 | item 3 Positive controls (direction, line, sess | idmax_id20_controls.log: [2026-09-23T12:22:31] id20_controls: C_session ptr_245: 81.7 (steady_raw/U_all_gait/rms@b08_35/all/pc1-3/none|rf) | governor: mode RESTRICTED, idle 1.56, workers id20_controls=cpu_paused, paused 57% of last 15 min, totals cpu 8 min | TRACKING z3a_linkprod_T1.log: [2026-09-23T12:30:21]   w=1 s03_to_s01: lock 21.7%
- 2026-09-23 12:34 | item 3 Positive controls (direction, line, sess | idmax_chain.log:  | governor: mode RESTRICTED, idle 0.6, workers id20_controls=cpu_paused, paused 83% of last 15 min, totals cpu 12 min | TRACKING z3b_g100native_w025.log: [2026-09-23T12:34:40]   w=0.25 s0103_to_s02: lock 66.7%
- 2026-09-23 12:54 | item 5 Maximisation sweep, nested; 6 Identification path | idmax_id22_lolo02.log: [2026-09-23T12:54:11] id22_sweep: lolo wd_lolo_s02_B_rev: 16.7 (steady_raw/B7_handcrafted/mean@b08_35/all/pc1-3/none|logreg_C0.01) | governor: mode RESTRICTED, idle 4.13, workers id22_sweep_cross=running, id22_sweep_lolo01=running, id22_sweep_lolo02=running, id22_sweep_lolo03=running, paused 0% of last 15 min, totals cpu 15 min | TRACKING y5_heads_train_s1.log: [2026-09-23T12:53:48] train s1 s02_to_s03: max param diff vs frozen 0, 4.4 min
- 2026-09-23 13:14 | item 5 Maximisation sweep, nested | idmax_id22_cross.log: [2026-09-23T13:14:42] id22_sweep: MODEL_dtw1nn_tpl s0103_to_s02: 15.0 (walk_edge_hampel/U_all_gait/mean@b08_35/all/pc1-3/none|dtw1nn) | governor: mode RESTRICTED, idle 5.77, workers id22_sweep_lolo03=running, id25_learned=running, id22_sweep_cross=running, paused 0% of last 15 min, totals cpu 15 min | TRACKING y5_heads_train_s1.log: [2026-09-23T13:11:36] train s1 s0203_to_s01: max param diff vs frozen 0, 8.8 min
- 2026-09-23 13:59 | item none RUNNING | idmax_id26b_cnn_diag.log: [2026-09-23T13:53:22] id26b_cnn_diag: POOLED {'reproduced_ensemble_pct': 27.22, 'embedding_head_pct': 30.0, 'speed_residualised_head_pct': 23.89, 'substitution_ | governor: mode RESTRICTED, idle 8.03, workers none, paused 0% of last 15 min, totals cpu 15 min | TRACKING f3_render_23c.log: f3_render EXIT 0

---

## CLOSING_IDMAX_2026-09-23.md

**Source:** `reports/CLOSING_IDMAX_2026-09-23.md`, 2026-09-23. **SHA-256:** `8f8c2b4630e208feac9d4fb6890d24879e4ee1bb48ec8af8448876f4af2a8260`. **Original combined here** on 2026-09-24; it is also in git at the tag `pre-cleanup` and in every commit before this one.

> **Superseded:** The only quotable identification figures are in `reports/ID_QUOTABLE_2026-09-23.md`.

### Closing report: gait identification maximisation (IDMAX), 2026-09-23b

The batch opened at 11:50 SAST and closed at 13:59. The queue is in `reports/QUEUE_IDMAX.md` and
the full write-up in `reports/IDENTIFICATION_2026-09-18.md`, section "2026-09-23b". The freeze is
`runs/IDENTIFICATION_FROZEN_2026-09-23b.json`, with an `_ADDENDUM` beside it.

**No tracking file was written, and no tracking process was signalled.** The yield governor paused
this run for **14.5 minutes** (12:22 to 12:37), when tracking held eight cores. It never touched the
GPU, which tracking held at 99 percent throughout.

#### Verdict per item

| # | item | verdict |
|---|---|---|
| 1 | DC2 protocol update | **DONE** at 12:10; the path was revised once at 13:00, by the brief's rule |
| 2 | audit: the open issues, CSI-only cadence, steady segmentation | **DONE**, PASSED |
| 3 | positive controls | **DONE**. Not broken: every control recovered, and both shuffles fell to chance |
| 4 | baselines, both references | **DONE**, PASSED |
| 5 | the section 8 sweep, nested | **DONE**, PASSED: 174 feature configurations, 18 heads, 7 method blocks |
| 6 | the identification path | **DONE**, PASSED: every path is at chance |
| 7 | voting and alignment | **DONE**, PASSED |
| 8 | learned models | **DONE**, PASSED; a CNN diagnostic was added (id26b) |
| 9 | final evaluation, speed diagnostic, ceiling, freeze | **DONE**, PARTIAL: the speed diagnostic is invalid for random-forest heads (fault 3) |
| 10 | report, figures, freeze, tests, closing | **DONE**. `all_clean = True`: 1105 passed, 8 skipped, 1 xfailed |

**BLOCKED items: none.**

#### Headline figures

Six people, so chance is 16.67 percent. Intervals are 95 percent, over recordings.

| row | accuracy % | 95% interval | p |
|---|---|---|---|
| **cross-day, leave one session out (the nested final)** | **15.83** | [10.28, 21.67] | 0.71 |
| cross-day, nine pairings | 19.26 | [15.83, 22.96] | 0.033 |
| WITHIN-DAY, temporal / leave one line out | 32.64 / 33.33 | | 0.001 |
| recording signature, no gait: within-day / cross-day | 91.67 / 20.28 | | |
| session-ID control, frozen features (chance 33.33) | 80.33 | | 0.001 |
| S0 oracle speed, cross-day | 32.50 | [23.89, 42.50] | 0.003 |
| learned 2D CNN on Doppler spectrograms, cross-day | 27.22 | [21.11, 33.61] | 0.001 |
| the same CNN, speed regressed out of its embedding | 23.89 | [17.22, 31.39] | 0.013 |

- **The positive controls pass:** walking direction 94.4, line 72.8, the day of a new person 80.4,
  and an injected per-person rhythm 32.2.
- **Cross-day identification is at chance at every cohort size from two to six.** It reaches a mean
  above 50 at no size.
- **The only family above chance is the Doppler CNN.** About half its margin over chance is pace.
  It is reported as a family row, not as the headline.
- **The 50 percent target was not reached** in any honest scope at six people.

#### The DC2 sheet

**`reports/DC2_ID_PROTOCOL_2026-09-23b.md`, one page.**

- **Path:** E_col1 under the brief's rule, because it is item 6's nested choice, run on all three
  sessions. That choice failed its own held-out test (13.3 percent), and its geometry is poor.
  **E_row1, the best-geometry line, is the alternative; the override is Uzayr's decision.**
- **Rounds:** 3 rounds a day, hours apart, of 5 passes per person, with start and end presses only.
- **Frozen for DC2:** the primary configuration by the brief's rule (a random forest on every gait
  feature, chosen in only 2 of 9 folds), and the Doppler CNN as a labelled post-hoc secondary.

#### Faults found in this run

None produced a quoted number.

1. **An OpenMP runtime clash** (torch with scikit-learn) crashed id20. Fixed, and the job resumed
   from its checkpoint.
2. **The DTW head** had no fittable candidate on one fold, and stopped loudly. Fixed by a rule set in
   advance, under a new name.
3. **The brief's residualised speed diagnostic re-injects the test pass's oracle speed** for a
   random-forest head: 27.50 with the true speeds against 16.39 with them shuffled. That figure is
   not quotable. Linear heads are unaffected.
4. **A test call wrote the run's reads log.** The DEMO entry was a mutation check, not a read.
   Tests now use a private log, and the one entry is documented. Tracking's pass-key audit also
   flagged a format colon in file names; that was reformatted, with the paths unchanged.

---
