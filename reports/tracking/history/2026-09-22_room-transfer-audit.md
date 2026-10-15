# Room transfer audit: every fitted component, and what DC2 must do with it

2026-09-22. Read only: nothing was trained, changed or re-run to produce this. Step 1 of the render
batch, `reports/RENDER_RULES.md` and the operator's instruction of 2026-09-22.

**The question.** DC2 is 26 and 27 September in a different room with the same taped grid and the
same relative node geometry. The thesis claim is cross-environment generalisation. So: which parts
of what ships have Room A baked into them, which are geometry that travels, and which cannot be
judged at all until Room B data exists.

**The verdict in one line.** Twelve fitted components. **Five must be refit**, four travel because
they are grid geometry or protocol rather than radio, and **three cannot be judged without Room B
data**. Two of the five are absolute levels in nats that nothing currently checks, and they are the
ones most likely to fail silently rather than loudly.

---

## The table

| component | fitted on | encodes Room A? | DC2 |
|---|---|---|---|
| per-link encoders and 25-cell heads | Room A CSI, training sessions of each pairing | **yes, entirely** | **REFIT** |
| per-channel standardisation mu and sd | training side only, carried with each model | **yes**, Room A channel statistics | **REFIT** (travels with the model) |
| the 25-cell training marginal the emissions divide by | training-side label counts | **yes**, 25.6 to 1 spread | **REFIT** |
| the chain prior | training-session line frequencies | **yes**, protocol not radio | **REFIT or drop** |
| the null level | training side, applied as an absolute nat offset | **yes**, and silently | **REFIT** |
| the motion gate threshold, 0.431 | Room A band energy, absolute | **yes**, and silently | **REFIT** |
| the A2 start-region classifier | training sessions, per pairing | partly | **REFIT** |
| transit geometry, 144 entries | the taped grid alone, no data | no | **REUSE** |
| the state space, 288 states at 0.25 m | the taped grid alone | no | **REUSE** |
| the eight start regions | the taped grid corners and mid-edges | no | **REUSE** |
| the walking speed model, 1.298 m/s, sd 0.123 | 360 labelled Room A passes | person, not room | **REUSE, verify** |
| display speed cap 0.80 m per window | swept against Room A walkers' pace | person, not room | **CANNOT JUDGE** |
| display prior `flatten_0.50` | chosen on Room A nine pairings | presentation choice | **CANNOT JUDGE** |
| DISP_END head offset, 0.75 s | measured on Room A | tied to the heads | **CANNOT JUDGE** |

---

## The five that must be refit, in order of how quietly they fail

### 1. The null level. An absolute nat offset, and nothing checks it

The null emission is documented as ADAPTIVE: a quantile of each recording's own emission peaks,
plus a learned offset, so that what transfers is an offset below a reference the recording supplies
itself. That is a good design and it is **inert as shipped**.

The five-head pool row-normalises every window (`pool()` in `g2_multihead.py` returns
`m - m.max(axis=1, keepdims=True)`), so every window's peak is exactly 0.000 and the 0.75 quantile
of those peaks is 0.000 whatever recording it is calibrated on. Measured on the demonstration
pairing: pooled row max ranges 0.000 to 0.000, and the adaptive reference resolves to **0.0000**.

**So the effective null level is a fixed constant: −7.50 nats, plus 4.0 when the gate reads still.**
That number was fitted on Room A and is applied as an absolute quantity against Room B emissions.

**Why it fails quietly.** Nothing in the suite asserts the reference is non-zero, and the component
is named `AdaptiveNullEmission`, so a reader checking the design would conclude it self-calibrates.
If Room B's pooled emissions are differently scaled, the decoder will enter and leave chains at the
wrong rate and the failure will look like a decoder problem rather than a calibration one.

**DC2 must refit the offset, or restore the adaptivity** by taking the reference before pooling
rather than after. The second is the better fix and is the one that makes the component do what its
name says.

### 2. The motion gate threshold, 0.431. Also absolute, also silent

`MOTION_THETA = 0.431` in `pipeline/branches/gate.py`, a threshold on the 0.3 to 2 Hz band energy,
measured over the eighteen Room A recordings as separating a median 1.247 on a taped path from
0.489 between paths. It feeds the null emission's gate weight and the STILL/TRANSIT split.

**Band energy is an absolute received quantity.** Different room, different multipath, different
scale. A threshold at 0.431 may sit anywhere in the new distribution.

**DC2 must refit it from the Room B empty-room baseline and dwell blocks**, which the protocol
already collects. This is cheap and needs no labels beyond "standing" versus "walking".

### 3. The 25-cell marginal the emissions are divided by

`scaled_cell_emission` divides the posterior by the training cell marginal, because eight of the
twelve lines cross the centre and the head would otherwise carry a centre prior into the HMM.
Measured on `s0102_to_s03`:

```
 7.3  0.8  4.7  0.7  6.4        the centre cell holds 16.5 percent of training mass
 1.0  4.8  3.5  4.8  0.9        the emptiest cell holds 0.64 percent
 4.9  3.3 16.5  3.2  4.7        a spread of 25.6 to 1
 0.6  4.4  3.2  4.5  0.8
 6.7  0.9  4.3  0.6  6.3
```

This is a property of **which lines the protocol walks**, not of the room, so if DC2 keeps the same
twelve lines the shape is nearly the same. It is computed from the training side at decode time, so
it refits itself automatically provided DC2 data goes through `sides()`. **Reuse the code, refit the
numbers, and check the spread has not changed shape.**

### 4. The chain prior. A per-line prior fitted to Room A's counts

`fit_chain_prior(st, tr_s)` counts each line's passes in the training sessions and takes logs.
Measured:

| lines | log prior |
|---|---|
| A_fwd, A_rev, B_fwd, B_rev, C_fwd, C_rev, D_fwd, D_rev | **+0.182** |
| E_col1, E_col5, E_row1, E_row5 | **−0.511** |

The spread is **0.693 nats, which is exactly log 2**, because the protocol walks each of the eight
main lines twice as often as each of the four edge lines: 12 passes against 6 in every 120.

**This is a per-line prior fitted to Room A's true counts.** It is legitimate Bayesian practice
only while the test distribution matches the training one. It is also the component closest to the
line the operator drew on 2026-09-22 against per-line quantities fitted to Room A, and the reason
it is not on the wrong side of that line is that it is fitted to the **protocol's sampling design**
and never to drawn-versus-true confusion counts. If DC2 changes the passes per line, it silently
becomes wrong.

**DC2 must refit it from the DC2 protocol's own line counts, or drop it to uniform.** Note for
Step 2: it penalises the edge lines, yet the drawn line **over**-produces E_col5 at 15 against 6
true, so the edge-line over-draw survives a prior pushing the other way.

### 5. The A2 start-region classifier

An LDA on the position head's `xy_hat` over windows straddling the press, trained per pairing on
the training sessions, turned into a per-line log offset at weight 0.5. Its INPUT is the Room A
position head, so it refits when the heads do. Its eight region targets are grid geometry and
travel. Its accuracy does not: 46.7 percent overall on Room A, and the corners group fails its
corrected bar (see `reports/SEMIBOUNDED_STATE.md` section 7e).

**DC2 must refit it and re-measure it per region**, and must not assume the Room A weight of 0.5
transfers.

---

## The four that travel

**Transit geometry, the state space and the eight start regions** are computed from the taped grid
and the node coordinates, with no data of any kind. DC2 keeps the same grid and the same relative
node geometry, so these are identical by construction. `transit_geometry.json` holds 144
line-to-line entries and is pure geometry.

**The walking speed model**, `V_MEAN = 1.298 m/s` with `V_SD = 0.123`, was measured over 360
labelled passes and verified at 1.302 implied against 1.298 assumed. Walking pace is a property of
the participants, not the room, and DC2 uses the same six people. **It should still be verified
rather than assumed**, because the DC2 protocol deliberately varies pace, which will widen the
distribution the sd describes.

---

## The three that cannot be judged until Room B exists

These are display choices swept on Room A. None of them affects a quoted accuracy figure, and none
of them can be checked before there is Room B data to sweep against.

- **The display speed cap, 0.80 m per window.** Chosen by sweeping against the walkers' own pace.
  Below 0.65 it stops binding because the chain's step model is 0.649 m per window. If DC2's
  deliberate pace variation widens the speed distribution, the cap will bind differently.
- **The display transition prior, `flatten_0.50`.** Chosen on nine Room A pairings under a gate
  that was loosened post hoc, which is disclosed where it is used.
- **The DISP_END head offset, 0.75 s.** Measured on Room A and tied to the heads, so it moves when
  they are refit.

---

## What this means for the cross-environment claim

**The claim is testable and the audit does not weaken it**, provided the five refits happen and are
reported as refits. A cross-room result where the encoders were refit and the geometry reused is
the honest version of the claim: the ARCHITECTURE and the GEOMETRIC PRIOR transfer, the learned
radio mapping does not and was never expected to.

**The risk is not the components that obviously need refitting.** It is the two absolute levels,
the null offset at −7.50 nats and the gate threshold at 0.431, because nothing currently asserts
either is appropriate to the data in front of it. They will not raise; they will quietly shift the
entry and exit rates and be read as the decoder generalising badly.

**The single cheapest safeguard**, and the one recommendation this audit makes: before any DC2
number is quoted, print the pooled emission scale, the realised null reference and the band-energy
distribution for Room B beside Room A's. Three numbers, no training, and they turn both silent
failures into loud ones.

---

## MEASURED, 2026-09-22: the two silent failures are not equally dangerous

`t8_calib` swept each quantity alone over nine pairings. **This corrects an emphasis in the audit
above, which treated the gate threshold and the null level as comparable risks. They are not.**

| quantity | shipped | within one pass of shipped | outside |
|---|---|---|---|
| gate threshold | 0.431 | 0.20, 0.30, 0.431, 0.60 | 0.80 costs 2.5 points, 1.10 costs 4.2 |
| **null level** | −7.50 nats | −9.0, −7.5 | **−10.5 costs 16.7 points** |

**The gate tolerates a threefold error. The null tolerates about 1.5 nats.** Calibration effort
belongs on the null.

### The relative forms were implemented and did NOT clear the bar on Room A

Three forms, all strictly causal, all fitted on the training sessions and applied per test session:

| form | all nine | worst per-pairing delta | paired delta | reproduces within one pass |
|---|---|---|---|---|
| gate scaled by the day's median pre-press energy | 60.00 | 3.33 | +0.00 [−1.30, 1.11] | **no** |
| gate two-point plus relative null | 61.67 | 3.33 | +1.67 [−1.20, 1.85] | **no** |
| gate two-point alone, null left absolute | 59.17 | 3.33 | +0.00 [−1.39, 0.83] | **no** |

**A hypothesis of mine was refuted here and is recorded as refuted.** Seeing the null's 6-nat swing
against its 1.5-nat tolerance, I expected the scatter to belong to the null. The gate-only arm has
**the same 3.33 point worst case**, so it does not. Both quantities scatter, and they scatter for
the same reason.

**The reason is the anchor, not the formula.** Room A has no calibration block, so the anchor had
to be the windows before each recording's first press, which are the participant arriving and the
operator setting up. Its median band energy varies **2.3x across three days in the same room**
(0.378, 0.875, 0.491), which pushes the derived threshold to 0.895 and 0.866 on the two pairings
that test on session 02, outside the flat region's upper edge of 0.60. Those two pairings are
exactly the ones that lose 3.33 points.

All three forms are **unbiased and noisy**: every paired interval straddles zero. They do not make
the decoder worse on average; they make it unpredictable per day, which for a cross-room claim is
the worse failure of the two.

### What this changes

- **The relative forms ship as available, not as default.** Enabling them on an anchor that was
  measured not to reproduce would be shipping on hope.
- **The DC2 protocol now specifies the calibration block**, including the calibration walks, which
  are the only thing that exercises what the null discriminates and the one thing Room A never
  recorded. See `reports/DC2_PROTOCOL_2026-09-18.md`.
- **The verification is re-run on DC2 day one** against the real block, and the relative forms are
  enabled only if they clear the same one-pass bar there.
- The three numbers to print beside any DC2 figure are listed in the protocol.

### One observation, flagged and not acted on

The null sweep scores **65.00 at −6.0 and 67.50 at −4.5**, against 62.50 at the shipped −7.50. That
is a sweep over the full evaluation set, not a selection: choosing a value because it scored well
there is the post-hoc test-set fitting this project refuses, and it is not being done. It does
suggest the null offset fitted on Room A training is not at its optimum, which is worth a
pre-registered look with a proper held-out split, after DC2 rather than before it.

---

**Not proposed, deliberately.** Moving a node. The node geometry is fixed and changing room and
layout together would confound the cross-room result, which is the whole point of DC2.
