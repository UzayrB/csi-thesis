# Pre-registration: the DC2 cross-room evaluation

**Written 2026-09-22, four days before DC2 and BEFORE ANY ROOM B DATA EXISTS.** That is the point
of the document: the cross-room result is the thesis claim, and a claim decided after seeing the
data is not a claim. Everything below is fixed now.

DC2: 26 and 27 September, a different room, the same taped grid, the same relative node geometry.

---

## 1. The primary comparison

**Two configurations, one comparison, decided in advance.**

| | configuration |
|---|---|
| **A, the honest baseline** | the frozen Room A tracker applied to Room B **unchanged** |
| **B, the calibrated tracker** | the same tracker with the **gate threshold and null level re-anchored on the DC2 calibration block**. **NO TRACKER ADAPTATION.** |

> **CONFIRMED 2026-09-22: THE PRIMARY COMPARISON CONTAINS NO TRACKER ADAPTATION.** Arm (d) did not
> ship, and the tracker extension `u3_trackeradapt` was significantly NEGATIVE, paired −3.33 with
> an interval of [−15.83, −2.62] entirely below zero. Configuration B is therefore **gate and null
> re-anchoring only**. Any adaptation of the tracker's emissions is exploratory and lives in
> section 7c, not here.

**The primary outcome is B.** A is reported beside it as the measure of what a completely
uncalibrated transfer costs, which is itself a result worth having.

**Nothing else differs between A and B.** Same weights, same heads, same decoder arm
`A1_A2_0.5`, same 0.5 s stride, same 2.0 s windows, same causal exit. The comparison is calibration
alone.

**The calibration passes are NEVER SCORED.** They are training-side data by construction: they set
the constants and then take no part in any figure. A test asserts that no calibration pass key
appears in any evaluated set.

## 2. Which passes are evaluated

**Every walking pass of DC2 that is not a calibration pass**, with no selection on outcome.

| | |
|---|---|
| evaluated | all passes recorded under the DC2 protocol's walking blocks |
| excluded | the calibration block's passes, and any pass the operator flags at capture time as aborted |
| **excluded for no other reason** | in particular, never excluded for scoring badly |

The exclusion list is written at capture time, in the sidecar, and not revisited afterwards.

## 3. Chance level

**8.3 percent**, one in twelve lines, unchanged, because DC2 keeps the same twelve taped lines.

If DC2 ends up walking a different number of lines, chance is recomputed as 100/n and the change
is disclosed; it is not carried over silently.

**The relevant comparisons are against 8.3 percent chance and against Room A's 62.50 percent**, and
those two answer different questions: the first is whether the system works in Room B at all, the
second is what the room change costs.

## 4. The per-pairing structure across the two DC2 days

DC2 gives two days. Written out now so the pairing set is not chosen after the fact:

| comparison | train on | test on | what it answers |
|---|---|---|---|
| **Room A to Room B** | Room A sessions 01, 02, 03 | each DC2 day | **the thesis claim**: does it cross rooms |
| **within-DC2 cross-day** | DC2 day 1 | DC2 day 2 | does it cross days inside the new room |
| | DC2 day 2 | DC2 day 1 | the same, the other way |
| within-DC2 within-day | DC2 day 1 split by pass | | reported SEPARATELY and never pooled with cross-day |

**Both Room A to Room B and within-DC2 cross-day are reported.** Neither substitutes for the other:
a good within-DC2 figure with a poor Room A to Room B figure means the model works but does not
transfer, which is a different finding from failing in the new room outright.

**Per-pairing figures are reported individually**, never only as a median, because with two days
there are few pairings and a median over few numbers hides everything.

## 5. The null level gets the calibration priority

From `t8_calib`, measured on Room A over nine pairings:

| quantity | flat region | cost outside it |
|---|---|---|
| gate threshold | 0.20 to 0.60, about **3x** | 1.10 costs 4.2 points |
| **null level** | −9.0 to −7.5, about **1.5 nats** | **−10.5 costs 16.7 points** |

**So the null level is calibrated first and most carefully**, from the calibration walks rather
than from the standing block or the empty room, because a walk on a known line is the only thing
that exercises what the null discriminates.

**The three numbers printed beside every DC2 figure**, per the protocol: the pooled emission scale,
the realised null reference, and the band-energy distribution for the empty room, the standing
block and the calibration walks. If Room B's numbers sit far outside Room A's, the decoder has not
failed; it has been handed constants that do not describe the room it is in.

## 6. Same-day calibration matches the deployment decision of 17 September

**Calibrating on the same day's own data is not a concession, it is the deployment model.** The
17 September decision was that a deployed system calibrates itself on arrival, which is why the
null emission was designed to take its reference from the recording in front of it rather than
from a constant. That design is currently inert under the five-head pool, which
`reports/ROOM_TRANSFER_AUDIT_2026-09-22.md` records; DC2 restores the intent.

So configuration B is **what a deployment would actually do**, and configuration A is the
pessimistic bound of shipping a model with no calibration step at all.

**What this does NOT license.** Calibration uses only data recorded **before** the evaluated
passes, on the same day. It never uses the evaluated passes, never uses later ones, and never uses
labels from Room B. Any figure that breaks this is void, exactly as the +20.5 s look-ahead exit was
void.

## 7. What counts as success, fixed now

**No single number is the bar**, and these are stated in advance so none is chosen afterwards:

- **The claim is supported** if configuration B on Room A to Room B is materially above the 8.3
  percent chance level with its interval, and the gap to Room A's 62.50 percent is reported
  plainly whatever it is.
- **Calibration is shown to matter** if B exceeds A, reported with both readings and the interval,
  per-pairing.
- **A negative is a result.** If B is at or near chance, that is the finding, and it is written up
  with the calibration numbers from section 5 beside it so a reader can tell a transfer failure
  from a calibration failure.

**The edge lines are reported individually** in every DC2 table, per the standing rule, because
pooled figures hide them and they are the least-sampled lines.

## 7a. THE SINGLE PRIMARY CONFIRMATORY ARM. Added 2026-09-22, still before any Room B data exists

**`b_abstain_0.25`: the Room-A-trained pre-press region reader, frozen, applied ONCE to DC2.**

> **THIS IS THE SINGLE PRIMARY CONFIRMATORY ARM AND THE CROSS-ROOM CLAIM RESTS ON IT ALONE.** One
> arm, one application, one comparison. Section 7b adds a secondary exploratory arm that does NOT
> carry the claim.

Frozen as `runs/TRACKING_FROZEN_2026-09-22c.json` so it cannot drift. That freeze holds the
reader's construction, its **abstain threshold of 0.90** and its **weight of 0.25**, both fixed
exactly as measured in `b_abstain_0.25`.

| | |
|---|---|
| applied | **once**, unchanged, against the same DC2 tracker without it |
| weight sweep | **none** |
| refitting or threshold re-selection on Room B | **none** |
| calibration passes | never scored, as everywhere else |

**Conditions that apply on DC2:** **(a)** paired improvement interval on the held-out folds
entirely above zero; **(b)** at least **two passes per pairing**, stated in **DC2's own pass
counts** rather than Room A's 0.8333 points per pass; **(f)** edge lines not degraded, reported
per line.

**Condition (c) does NOT apply**, and the reason is structural rather than a concession: there is
no weight sweep and no refitting, so there is no dial for the effect to respond to. (c) exists to
catch an effect that does not move with its own knob; a single fixed application has no knob.

### Why this arm and not another

It did **not** ship into the Room A headline, failing (c) under the consistent paired-delta
reading. Three things make it the right confirmatory arm anyway:

1. **The mechanism is confirmed, with an exact control.** On the 262 held-out passes the reader
   covered and got right, **31 were gained and none lost**. On covered-but-wrong it costs 4. On
   **all 290 uncovered passes, not a single outcome changed**, which is the control holding
   exactly and confirms the implementation rather than assuming it.
2. **It gains most on the folds with the lowest baselines, and the reason is UNRESOLVED.** Two
   explanations fit and they cannot be separated on Room A: abstention protecting hard folds, or
   simple headroom. Reader accuracy and baseline are collinear at **+0.958** across the seven
   held-out folds, so no statistic here distinguishes them. **Neither is claimed.** The detail is
   in `reports/PREREG_prepress_v2_2026-09-22.md`. This is a reason to TEST the arm in a new room,
   not a reason to expect it to work there.
3. **It degrades no edge line**, and improves two.

### The honest prediction, recorded now

**The reader is Room-A-trained and Room B is a different room.** Its accuracy there may collapse.
The abstain mechanism is what protects against that: on a pass it is unsure about it contributes
nothing, so a collapsed reader should tend toward **no effect** rather than toward harm.

**That is the hypothesis this arm tests, and it is falsifiable:** if DC2 shows a NEGATIVE paired
delta, abstention did not protect, and the finding is that a Room-A reader cannot be carried across
rooms even when it declines to speak. That would be a real and reportable result.

## 7b. THE SECONDARY, EXPLORATORY ARM, and why it is kept separate

**`a_veto_1.0`, frozen as `runs/TRACKING_FROZEN_2026-09-22d.json`.** Veto threshold **0.01**, veto
depth **3.0 nats**, weight **1.0**. Applied once, unchanged, no sweep, no refitting.

> **THE CROSS-ROOM CLAIM DOES NOT REST ON THIS ARM.** It is reported beside the primary and is
> **labelled exploratory** wherever it appears.

**Why it is separated rather than run as a second primary.** Two arms tested on Room B are two
opportunities for one of them to clear a bar, and a claim resting on whichever happens to succeed
is a **selected** claim. The primary must not be diluted by a second chance to succeed. So
`b_abstain_0.25` carries the claim alone, and this one can only ever add colour to it.

**What it would mean if the secondary succeeded and the primary did not.** Not a cross-room
result. It would be a hypothesis for a later, separately pre-registered test, and it would be
written up in those words.

**One measurement worth carrying over.** The veto threshold sat at the **floor** of its candidate
range, 0.01, because at any higher value the reader vetoes the TRUE region on more than 2 percent
of selection-fold passes. The veto barely fires. That is itself a measurement of how weak a 42.5
percent reader is, and it should be re-measured on Room B rather than assumed to carry.

## 7c. EXPLORATORY: AdaBN on the tracker, from the calibration block only

**Exploratory. It does NOT enter the primary comparison and does NOT carry the cross-room claim.**

Part 2 ran this on Room A and it was significantly negative, paired −3.33 with an interval entirely
below zero. It is nonetheless worth one run on DC2, for a reason that is a hypothesis and not a
prediction: **on Room A the only available anchor was the pre-press setup period, which varies 2.3x
across three days and which item 1 measured to be unfit for anchoring anything.** DC2 will have a
proper calibration block for the first time. A negative on an unfit anchor does not establish that
adaptation fails with a clean one.

**What it may use, and nothing else.** Batch-norm statistics recomputed **only** from the DC2
calibration block: the empty-room segment, the standing segment and the calibration walks.

**What it may never use.** Any evaluated pass, anything recorded after an evaluated pass, or any
Room B label. The same rule as everywhere else, and the same test asserts it.

**How it is reported.** Beside the primary and the secondary, **labelled exploratory**, with its
per-fold table. If it is positive, that is a hypothesis for a separately pre-registered test and
is written up in those words. If it is negative again, Room A and Room B agree and the question is
closed.

**Expected, and recorded now:** the Room A result predicts harm. The reason for running it is that
the anchor is different in kind, not that the result is expected to reverse.

## 8. What is fixed and may not move

- **Node geometry.** Fixed, and moving a node is never proposed, for DC2 or otherwise: changing
  room and layout together would confound the cross-room result, which is the entire purpose.
- **The rendering contract**, rules 1 to 6 and V1 to V4, including the 2.0 s latency.
- **The ship rule**, all conditions including (f).
- **The pairing key**, `session|stem|pass_id`, with the room on top where a key spans rooms.

## 9. Due date

**This document is complete before 26 September and is not edited after Room B data exists.** Any
change made after that point is POST HOC and says so in those words, in the document, at the point
of change.

---

## 10. AMENDMENT, 2026-09-23 (batch 23d). WRITTEN BEFORE ANY ROOM B DATA EXISTS

**Checked at the time of writing: `data/` holds `room_A` only.** Operator instruction 4, item 5,
verbatim in the BRIEF: *"DC2 PRE-REGISTRATION, amended before any Room B data exists: the shipped
configuration is what DC2 tests. Primary comparison: the frozen tracker unchanged against the same
tracker with null and gate re-anchored on the calibration block, at the PRODUCT's scale.
Confirmatory arms b_abstain_0.25 and any item-1 arm that now ships, each at 97.5 percent intervals
for multiplicity. (f) as amended. Wire everything into dc2_pipeline and pass the stand-in plumbing
check."* **Where this section and sections 1 to 9 disagree, this section governs.**

### 10.1 What DC2 tests: the shipped configuration of freeze 2026-09-23c

| component | shipped |
|---|---|
| window lattice | **the ONE lattice**: 0.5 s stride, 2 s windows, re-phased per pass so a window starts on each press (`pipeline/constrained/lattice.py`, `y4_pressalign`) |
| pool | the five heads at equal weight, **mean link fusion** |
| committed decision | A2 start term (0.5) **plus `a_veto_1.0`** (`pipeline/constrained/veto.py`: threshold 0.01, 3.0 nats, weight 1.0) |
| lock | the render's own lock, at the window that ends at press + 2.0 s: the DISPLAY decode, `sd_scale` 4.5, 0.8 m per window (clarified 2026-09-23 before any Room B data, `d6_lock_commit`: every lock figure quoted before then decoded at `sd_scale` 1.0, which is not the drawn lock). The lock is a component here, not a DC2 outcome |
| exit | causal, as shipped |

**On "at the PRODUCT's scale".** The instruction was written before item 3 finished. **Product
fusion did not ship** (`reports/ITEM3_REPORT_2026-09-23.md`: the selection folds chose w = 1.0 and
the amended (f) fails there). The shipped scale is therefore the MEAN fusion's, and the re-anchoring
below is done at that scale. **If the operator ships product fusion before any Room B data exists,
this section is amended again first**, and the same procedure runs with `fusion_w`, which
`dc2_pipeline` takes as a flag.

### 10.2 The heads, and the ONE cut Room B needs

**Room A to Room B uses heads trained on Room A sessions 01, 02 and 03 together**, tag `s010203`,
none of which existed before this batch. They are trained before DC2 with the recipe, seeds and
epochs of the shipped heads, in stride-keyed trees, and the 1 s heads are inferred over the 0.5 s
windows exactly as the shipped pool infers them.

**A CORRECTION OF THE RECORD.** `HANDOFF_2026-09-23` and `dc2_pipeline`'s ingest guard say Room B
must be cut at BOTH 0.5 s and 1.0 s, because "three of the five pool heads are 1 s heads". **The
shipped pool never reads 1.0 s windows**: all five heads are inferred over the 0.5 s windows
(`g2_multihead.ONE_S_TREES`, "posteriors over the 0.5 s windows"; batch 23c item 5 reproduced the
three 1 s heads' posteriors over `windows_half` to 3e-8, 27 of 27). So:

- **Room A to Room B, the thesis claim, needs ONE cut: the press-aligned 0.5 s lattice.**
- **The 1.0 s cut is needed only to TRAIN 1 s heads on DC2 data**, for the within-DC2 cross-day
  comparison of section 4. It stays on the field sheet for that reason.

**The pre-press readers' heads, fixed now.** The shipped A2 start term and the veto reader take
their test-session features from `t2_embed.tag_for_session`, which returns the FIRST Room A
pairing that tests a session (session 03: `s01_to_s03`, trained on session 01 only), whichever
pairing the pool is decoding. Found 2026-09-23d when the stand-in reproduced the shipped decisions
on 64 of 72 passes until it copied that rule. **For DC2 the readers and the pool both use the
all-sessions heads `s010203_to_sB`**: no Room A pairing tests Room B, so there is no "first" one, and
using the same heads throughout is the consistent choice.

### 10.3 The primary comparison

| | |
|---|---|
| **A** | the shipped configuration applied to Room B **unchanged**: gate 0.431, null -7.50 nats |
| **B** | the same, with the gate and the null **re-anchored on the calibration block** |

- **Gate:** `dc2_pipeline.re_anchored_constants`, the two-point bracket between the still and
  calibration-walk band energies, with its guard (outside the [0.20, 0.60] region measured flat on
  Room A, it falls back to 0.431 and says so).
- **Null, relative, pre-registered now:** `null_B = -7.50 * (s_B / s_A)`, where `s` is the
  **pooled emission spread**: the median over windows of (the largest minus the median on-chain log
  emission) of the shipped pool's emission. `s_B` is taken on Room B's calibration walks; `s_A` on
  Room A's walking windows, computed once and written into the pipeline before any Room B data. **If
  `null_B` lands more than 3 nats from -7.50 it falls back to -7.50 and is flagged**: `t8_calib`
  measured -10.5 costing 16.7 points.
- **The three numbers** printed beside every DC2 figure: `s_B` against `s_A`, the realised null,
  and the band-energy distribution of the still block and the calibration walks.
- **Reported:** A, B, and B against A paired per pairing, both readings, with intervals; edge lines
  individually; the session structure of section 4. **The claim is supported** if B is materially
  above 8.3 percent chance with its interval, the gap to Room A reported plainly (section 7).

### 10.4 The confirmatory arms, each at a 97.5 percent interval

**This SUPERSEDES sections 7a and 7b.** Two confirmatory arms, not one primary and one exploratory,
each judged at a **97.5 percent interval** so the pair carries a 95 percent family-wise level:

| arm | frozen | reference it is compared against | what it adds |
|---|---|---|---|
| `a_veto_1.0` | `veto.py`; also `TRACKING_FROZEN_2026-09-22d.json` | B **without** the veto | the shipped committed arm |
| `b_abstain_0.25` | `TRACKING_FROZEN_2026-09-22c.json` | B without the veto | the pre-press reader, abstaining |

Each applied **once**, no sweep, no refitting, no threshold re-selection on Room B. Conditions:
**(a)** the paired 97.5 percent interval entirely above zero; **(b)** at least two passes per
pairing in DC2's own pass counts; **(f) as amended** (edge lines' combined change in correct walks
>= 0, no line losing more than two walks). (c) does not apply: no dial.

### 10.5 What does not change

Calibration passes are never scored (asserted). No Room B label, no evaluated pass and nothing
recorded after an evaluated pass enters any calibration. Node geometry fixed. Per-pairing figures
reported individually. The AdaBN tracker arm stays exploratory (7c). The pairing key is
`room|session|stem|pass_id`.

### 10.6 The plumbing check

`dc2_pipeline --stand-in` runs this whole path on Room A session 03 dressed as Room B, from its RAW
files: the press-aligned cut, inference with heads trained on sessions 01 and 02, configurations A
and B, both confirmatory arms, and the report. **Its numbers are a plumbing check and never a
result**, and the report is stamped so.

## 11. AMENDMENT, 2026-09-23e, BEFORE ANY ROOM B DATA (`data/room_B` does not exist)

Operator instruction 5 (BRIEF), items 4 and 6, recorded in the operator's words where they decide.

### 11.1 An EXPLORATORY arm: product link fusion at w = 0.25

> "PRODUCT FUSION AT w = 0.25: NOT shipped in Room A (selecting it now would be selecting on
> held-out folds). Add it to PREREG_DC2_crossroom as an EXPLORATORY arm, not confirmatory, frozen
> under a new letter before any Room B data, with null and gate re-anchored at the product's scale
> for that arm only."

| | |
|---|---|
| arm | **`B_prod0.25`**: configuration B (gate and null re-anchored, `a_veto_1.0` start term) with every head's three link posteriors fused by the log-linear blend at **w = 0.25** towards the renormalised product (`pipeline/constrained/fusion.py`) |
| status | **EXPLORATORY.** Not confirmatory, not in the family-wise level of 10.4, and no claim rests on it. Reported with its 95 percent interval beside B, never tested against a threshold |
| null | re-anchored at the PRODUCT's scale for this arm only: `null = -7.50 * (s_B,prod / s_A,prod)`, the same +-3 nat guard. **`s_A,prod = 3.7428177798574556`**, computed 2026-09-23e exactly as `s_A` on the same 3394 Room A walking windows (per session 4.721, 3.093, 3.890); the same code reproduces `s_A = 2.1108124982838437` to the last digit at w = 0. `s_B,prod` on Room B's calibration walks under the same fusion |
| gate | B's re-anchored threshold. The gate reads band energy, which no emission fusion touches, so its re-anchoring is the same at every fusion scale; stated so it is not mistaken for an omission |
| the flag | `dc2_pipeline --fusion ARM=W`, per arm. The pre-registered arms A, B, B0 and B0_abstain are fixed at mean fusion and the decode REFUSES a flag on them; only an arm with an `s_A` frozen at its scale may run |
| frozen | `runs/TRACKING_FROZEN_2026-09-23e.json`, with this file's SHA-256 |

### 11.2 A fourth receiver, for identification only

The operator adds a spare ESP32 next to the TX as a dedicated identification link; the tracking
geometry is unchanged. **Tracking reads RX1, RX2 and RX3 only, by node name, and each name is checked
against the Room A tracking board's MAC** (`pipeline/constrained/nodes.py`): a Room A tracking board
recorded under any other name, or a tracking name carrying another board, REFUSES the run. The capture
logger names autodiscovered ports RX1..RXN in sorted port order, so the capture uses an explicit
`--nodes` mapping (DC2_FIELD_CHECKLIST). Nothing in sections 10 and 11.1 reads the fourth receiver.

## 12. AMENDMENT, 2026-09-23g, THE DC2 MODEL FREEZE, BEFORE ANY ROOM B DATA (`data/room_B` does not exist)

Operator instruction 7 (BRIEF), item 4: "amend PREREG_DC2_crossroom before any Room B data, naming the
final lock (whichever it is) as the display component". Written 2026-09-23 after the scorer lock was
refused (`reports/PREREG_scorerlock_2026-09-23.md`, `g2_scorerlock`: the pre-registered substitution
test failed, 0.38 against 0.5; `reports/SCORERLOCK_AND_ABLATION_2026-09-23.md`).

### 12.1 The display component DC2 carries

| component | frozen for DC2 |
|---|---|
| **lock** | **the DISPLAY lock, unchanged**: the display decode (`sd_scale` 4.5, 0.8 m per window, A2 start term 0.5, soft entry, entry window 1.0 m) read at the window that ends at press + 2.0 s on the ONE lattice. The scorer lock was refused and is NOT carried |
| path after the lock | the restricted along-line decode on the locked line with the DISP_END display head flattened 0.50 (V5 phase 0.50) |
| mid-walk switching | RENDER_RULES rule 1a, arm C: at most one switch, none in the final 1.5 m, only to the final-answer scorer's best line within 1.5 m of the dot after two consecutive leads over theta 2.0 nats, radio to t + 2.0 s only, a 0.5 s slide |
| end-of-walk text | the shipped semi-bounded committed decision (A2 + `a_veto_1.0`) |
| latency | 2.0 s, the rendering contract (RENDER_RULES) in full |

**The display component is not a DC2 outcome.** Sections 10 and 11 are unchanged: the DC2 outcomes are
the committed decisions of configurations A and B, the two confirmatory arms at 97.5 percent, and the
exploratory product arm.

### 12.2 The freeze

`reports/MODEL_FREEZE_DC2.md` lists the exact configuration DC2 tests, with the SHA-256 of every code
and model file it runs (`runs/TRACKING_FROZEN_2026-09-23h.json`). **No model change is made until the
Room B analysis.** Anything changed after Room B data exists is POST HOC and says so, per section 9.

## 13. AMENDMENT, 2026-09-23 22:37, BEFORE ANY ROOM B DATA: an EXPLORATORY display comparison

Operator instruction 8 (BRIEF), verbatim there: "add to PREREG_DC2_crossroom, before any Room B data,
an EXPLORATORY display comparison: the scorer lock at w = 0.25 against the display lock, scored once on
DC2. Define its substitution test now as swapping BOTH the walk emissions and the pre-press radio behind
the start term. It affects no DC2 outcome."

**No model change.** The DC2 model freeze (23h) is untouched: none of its 38 code files or 18 model
files changes, and the check is recorded in `runs/TRACKING_FROZEN_2026-09-23h_ADDENDUM.json`. This
section changes this document's own bytes, by the operator's instruction, and the addendum records its
new hash. **It affects no DC2 outcome**: sections 10 to 12 are unchanged, and the display lock stays
DC2's frozen display component (section 12).

| | |
|---|---|
| status | **EXPLORATORY**. No claim rests on it. Reported once, beside the DC2 results, never tested against a threshold that could change anything |
| the two locks | the DISPLAY lock (DC2's frozen display component, section 12) against the SCORER LOCK at **w = 0.25 fixed**: argmax over lines of 0.75 x D(line) + 0.25 x S(line), with D and S exactly as in `reports/PREREG_scorerlock_2026-09-23.md` section 1. No re-selection of w on Room B |
| configuration | **B** (the primary: gate and null re-anchored on the calibration walks, the frozen heads `s010203_to_sB`); **A** reported beside it |
| start terms | the display: A2 (0.5); the scorer: A2 + `a_veto_1.0`, both from the DC2 reader on the frozen heads |
| passes | every evaluated DC2 walk (calibration passes never scored), per session and pooled |
| measures | each lock's correct line; the paired difference with a 95 percent per-pass paired bootstrap interval (1000 resamples, seed 0); locks changed; edge walks per edge line, and the amended (f) reading |
| **substitution, defined now** | the scorer part recomputed with **BOTH** the partner's WALK EMISSIONS (the next recording in the session, `y3_switch`'s partner) **AND the partner pass's START TERM** (A2 + veto as the reader computed them from the partner pass's own pre-press radio, same pass id); D held. Over walks where the scorer lock differs from the display lock, the share whose scorer lock changes, divided by the share of walks whose partner walked a different line; reported against 0.5 |
| how it runs | a SEPARATE command after the DC2 pipeline, reading its trees and constants and writing its own report: `python3 -m pipeline.constrained.dc2_scorerlock --room room_B` |
| plumbing check | on the stand-in (Room A session 03 dressed as Room B), under configuration A, both locks must equal Room A's `g2_scorerlock` rows (the display lock and the w = 0.25 lock) on every evaluated walk |

The Room A record, for the reader: the scorer lock was refused on the pre-registered Room A rule
(substitution 0.38 against 0.5, with only the walk emissions swapped), and that Room A test was not clean
(its lead was seen on the held-out folds).
