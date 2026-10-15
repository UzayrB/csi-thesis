# Person identification from Wi-Fi CSI, 2026-09-18

Six participants, so chance is 16.7 percent. Every figure here is computed on six classes tonight. The archived identification arm of 12 September was computed on eight and none of its numbers are quoted except in the clearly labelled history paragraph below.

## The pre-registered rules, and whether each was met

These were fixed in phase D before any number existed and are not reworded now that the numbers are in.

| rule | pairings | met |
|---|---|---|
| a feature earns its place if it moves cross-day accuracy outside the interval on more than one pairing | see the ladder | see below |
| the branch is POSITIVE if all-features beats speed-only cross-day outside the interval on more than one pairing | 0 | **False** |
| the GAIT question is YES if the speed-removed all-features row beats chance outside the interval on more than one pairing | 3 | **True** |

## Why this branch was built on constraints rather than on another model

The frozen arm of 12 September lost to a baseline that used nothing but walking speed, and its failure had a specific shape: the same-morning pair scored zero on a two-class problem, the within-session ceiling was 33.3 percent, and per-recording accuracy ran from 0 to 100. That is a model reading the recording rather than the person. The tracking branch escaped the same trap by refusing the general problem and assuming twelve lines, and this branch does the same thing: it assumes the walk boundaries and the line are known, because the tracker supplies both, and asks what identity signal is left once the geometry is held constant.

### The confound, measured

All 18 participant-session cells hold exactly ONE recording. Within a session the recording and the identity are therefore perfectly confounded, so no within-day figure can separate a model that has learned the person from one that has learned the recording, and only cross-day evaluation can. That is the structural reason the frozen arm's per-recording accuracy was bimodal, and it is why every within-day number in this report is shown but never used to support a claim.

Speed separability is 0.51: between-participant spread 0.191 m/s against within-participant 0.375. Because that ratio is well below one the six participants' pace distributions overlap heavily, which is good news for this branch: pace is a weak identifier on this cohort, so accuracy above the speed baseline is less likely to be pace in disguise than it would be on the eight-person cohort where speed alone reached 28.6 percent.

### The gait extraction, and the harmonic that nearly sank it

The gait band is 0.8 to 3.5 Hz, taken from the raw stream, and it is separate from the tracking features whose 2 Hz lowpass removes the step rhythm entirely. The first sanity gate failed on 28.9 percent of passes and a second attempt made it worse at 32.5, but every single failure was an implied step length ABOVE the plausible range and none below, with cadence never at a band edge. The extraction was right and the gate was wrong. A walking spectrum carries energy at both the step rate, about 2 Hz, and the stride rate, about 1 Hz, which is one full gait cycle of two steps, and which peak dominates depends on gait SYMMETRY. Resolving that harmonic took the failure rate to 0.6 percent, and the flag itself became a feature: 115 of 360 passes are dominated by the stride rate, which is what an asymmetric gait looks like.

Cadence median 2.34 Hz, step length 0.71 m.

## The ladder

Per-pass features only, LDA and regularised logistic regression, standardised on the training sessions alone, seed 0, cluster bootstrap over passes with 1000 resamples. Cross-day and within-day are never pooled.

| row | cross-day | within-day | bimodal pairings |
|---|---|---|---|
| chance | 16.67 | 16.67 | |
| speed only | 23.33 | 22.22 | 4 |
| speed only [speed removed] | 23.70 | 20.56 | 11 |
| plus cadence | 25.65 | 22.78 | 0 |
| plus cadence [speed removed] | 24.91 | 22.78 | 1 |
| plus step length | 25.74 | 23.33 | 0 |
| plus step length [speed removed] | 25.19 | 20.00 | 0 |
| plus spectral symmetry | 25.65 | 24.44 | 0 |
| plus spectral symmetry [speed removed] | 25.83 | 20.00 | 1 |
| plus cadence variability | 24.17 | 20.00 | 0 |
| plus cadence variability [speed removed] | 24.72 | 18.33 | 0 |
| plus band ratio | 23.70 | 21.11 | 0 |
| plus band ratio [speed removed] | 24.35 | 18.89 | 1 |
| plus spectral shape | 22.41 | 21.67 | 0 |
| plus spectral shape [speed removed] | 22.22 | 18.33 | 0 |
| plus shadow depth | 21.20 | 25.00 | 0 |
| plus shadow depth [speed removed] | 21.11 | 23.33 | 0 |
| plus shadow asymmetry | 21.20 | 25.00 | 0 |
| plus shadow asymmetry [speed removed] | 21.11 | 23.33 | 0 |

**Accuracy peaks at plus spectral symmetry [speed removed] on 25.83 percent and then declines as more features are added.** That is overfitting rather than harm from any individual feature: there are 360 passes and six classes, and the feature count grows to more than twenty while each pairing trains on roughly 240 passes. Cadence and step length are the two features that clearly earn their place, adding about 2.4 points over speed alone. Shadow depth costs accuracy cross-day while gaining it within-day, which is what a real body-size signal that does not transfer across days would look like.

## The learned representation, held to the same geometry

| arm | cross-day | within-day | bimodal pairings |
|---|---|---|---|
| E1_pooled | 22.22 | 78.89 | 10 |
| E2_per_line_z | 25.83 | 80.00 | 3 |
| E4_fusion | 26.02 | 80.00 | 3 |

The tracking encoder is frozen throughout and is never fine-tuned. E1 pools its embedding over a pass with no conditioning and is the control: it reaches 22.22 percent cross-day with 10 pairings flagged bimodal on per-recording accuracy, which is the signature of reading the recording. E2 z-scores every pass by the mean and standard deviation of its OWN LINE, computed on the training sessions only, and reaches 25.83 percent with the bimodal count falling to 3. **Holding the geometry constant both raises accuracy and removes most of the recording effect, which is the result this phase existed to test.**

### Two arms the drop order puts last, neither dropped

The brief's drop order is phase G, then E3, then E2, and the batch was not over budget, so both ran and both are clean negatives.

**E3, one classifier PER LINE**, pools to 17.66 percent against chance 16.7. It is starved by construction at about 1.67 passes per participant per line per session, and it exists to show whether the line-conditional signal is there at all rather than to ship. It confirms the signal is too thin to exploit one line at a time, which is why E2's approach of z-scoring by line while keeping a single classifier is the right way to use the geometry.

**Phase G, a 1D convolution over the three gait-band envelopes of a whole pass**, with the line supplied as a one-hot so the model is line-conditioned BY CONSTRUCTION, early stopped on held-out passes from the other training session and never on the test side, reaches 16.85 percent cross-day. It beats the geometry ladder on 0 pairings and therefore **does not ship**. A learned pass-level gait model loses to hand-built per-pass features, which is a pre-registered negative and it strengthens rather than weakens the argument this branch was built on: the constraints beat the model.

## Verification, the realistic pipeline, and cohort size

**Verification is a scope change and is reported as one.** Enrolling on sessions 01 and 02 and verifying on 03, one participant against the other five, gives a mean AUC of 0.684 and a mean equal error rate of 0.405. That is better than chance and not deployable.

**The realistic pipeline is the row that matters for a system claim.** Every arm above was handed the true line. The tracker supplies it correctly on 80.0 percent of passes, and substituting the tracker's decision for the truth moves identification from 31.67 percent to 30.00, a degradation of only 1.67 points. The joint system does nearly as well as the idealised one, and that is measured rather than assumed.

| cohort | chance | mean | above chance |
|---|---|---|---|
| 2 person | 50.0 | 66.0 | 14/15 |
| 3 person | 33.3 | 50.5 | 20/20 |

**At three people the signal is clear**: 50.5 percent against 33.3 chance, above chance on 20 of 20 subsets. At six it is marginal. The thesis can state a cohort size at which this rig identifies people, and it is small.

## What is defensible and what is not

**Defensible.** That the gait question was pre-registered and answered on its own terms. That holding the line constant both raised accuracy and removed most of the recording effect, with the per-recording bimodality count as independent evidence. That the realistic pipeline was measured with the tracker's own decisions rather than assumed. That three-person identification sits clearly above chance.

**Not defensible.** Any within-day figure as evidence of identity, because one recording per participant-session makes the recording and the person the same variable. Any claim that six-way identification works: it reaches the low thirties against 16.7 chance, which is real but not usable. Any comparison with the archived eight-class numbers.

### History, clearly labelled

The 12 September arm reported 15.7 percent for a CNN and 16.3 for an adversarial variant against a 28.6 percent speed-only baseline, on EIGHT classes with two participants who have since been retired. Those numbers are not comparable with anything above and are recorded here only so the change of cohort is visible.

## Scope statement

On the evidence here this rig does not identify six people reliably, and it does something more specific than that sentence suggests. The speed baseline is weak on this cohort, so what accuracy exists is not pace recognition. The gait question was answered YES on 3 pairings, so there is identity signal beyond pace. Holding the geometry constant exposes more of it. And at a cohort of three the signal is unambiguous. The honest claim is that constrained, line-conditioned identification works at small cohort sizes and degrades to marginal at six.

---

# Appendix. Stage findings, in stage order

Folded in at the 2026-09-18 cleanup. The report body above is unchanged: this appendix is additive.
Each file was written by its stage as that stage finished, and the first word of each is its verdict.

## Stage C

```
PASSED

Identification foundations, read-only. Six participants, chance 16.7 percent; the two retired participants are never read and every archived eight-class figure is recomputed rather than quoted. 360 walking passes inventoried. 18 participant-session cells have a SINGLE recording, so within a session the recording and the identity are perfectly confounded and only cross-day evaluation can separate them, which is the structural reason the frozen arm's per-recording accuracy ran from 0 to 100. Speed separability ratio 0.51, between-participant 0.191 against within-participant 0.375 m/s. Gait gate: 2 of 360 passes implausible (0.6 percent), cadence median 2.34 Hz and implied stride 0.71 m. PASSED, cadence features are available

(2026-09-18T02:29:09, decoder rebuild batch)
```

## Stage D

```
PASSED

The geometry and gait ladder over 360 passes, six classes, chance 16.7 percent, cluster bootstrap over passes with 1000 resamples. PRE-REGISTERED VERDICTS: the branch is positive on 0 pairings, so False; the gait question, whether anything beyond pace carries identity, is answered on 3 pairings, so True. Speed-only cross-day 23.33 percent against all-features 21.20 percent.

(2026-09-18T02:34:06, decoder rebuild batch)
```

## Stage E

```
PASSED

Line-conditioned embeddings over 360 passes with the tracking encoder FROZEN and never fine-tuned, embedding dimension 384. E1, the pooled control, reaches 22.22 percent cross-day with 10 pairings flagged bimodal on per-recording accuracy, which is the signature of reading the recording rather than the person. E2, z-scoring each pass by its own line's training statistics, reaches 25.83 percent. The difference is 3.61 points and is the direct test of whether holding geometry constant exposes identity. Chance is 16.7 percent.

(2026-09-18T02:48:23, decoder rebuild batch)
```

## Stage F

```
PASSED

Verification, the realistic pipeline and cohort subsets. F1, a SCOPE CHANGE from identification: enrolled on sessions 01 and 02 and verified on 03, one versus rest, mean AUC 0.684 and mean equal error rate 0.405. F2, the joint system as it would actually run: the tracker supplies the line correctly on 80.0 percent of passes and identification falls from 31.67 to 30.00 percent, a degradation of 1.67 points, measured rather than assumed. F3, cohort size: two-person 66.0 percent against 50 chance and three-person 50.5 against 33.3.

(2026-09-18T02:57:10, decoder rebuild batch)
```

## Stage G

```
PASSED

E3 and phase G, neither dropped because the batch is not over budget. E3 fits ONE classifier PER LINE, which is starved at about 1.67 passes per participant per line per session, and pools to 17.66 percent against chance 16.7; the pass counts are printed beside every line because the intervals are wide by construction and this arm exists to show whether the line-conditional signal is there at all, not to ship. Phase G, a 1D convolution over the three gait-band envelopes of a whole pass with the line supplied as a one-hot so the model is line-conditioned BY CONSTRUCTION, reaches 16.85 percent cross-day against the geometry ladder's 21.20. It beats the ladder outside the interval on 0 pairings, so it is recorded and NOT shipped.

(2026-09-18T03:20:38, decoder rebuild batch)
```

## Stage H

```
PASSED

Reports, freeze and the DC2 sheet. Tests all_clean=True: the two retired participants and the free-movement recordings were never read, the gait band never touches the tracking feature transform, no pass is split across train and test, and both the speed regression and the per-line statistics are fitted on training sessions only. reports/IDENTIFICATION_2026-09-18.md and reports/DC2_PROTOCOL_2026-09-18.md written, runs/IDENTIFICATION_FROZEN_2026-09-18.json frozen without touching the tracking freeze.

(2026-09-18T03:32:40, decoder rebuild batch)
```

---

# IDENTIFICATION UNDER THE LIVE MODE, 2026-09-19

Three stages, all on nine cross-day pairings rather than the single pairing the earlier record was
restricted to, and all with the line supplied by a real tracker rather than by the truth. Chance is
16.7 percent over six participants. Frozen at `runs/IDENTIFICATION_FROZEN_2026-09-19.json`.

## Why this was worth doing

The frozen record carried two soft spots, both stated in its own text. The realistic pipeline said
"Only s0102_to_s03 is covered, because that is the pairing the tracker was scored on", and one
pairing is the weakest evidence this project accepts anywhere. And the line it fed identification
came from the BOUNDED tracker, which is told when each walk ends. Now that semi-bounded is the core
mode, the honest question is what identification does with the line a LIVE system would have.

## The geometry features are inert

`id7_livepipeline`, nine pairings, same classifier and features, only the line source changing:

| line source | median accuracy | line agreement |
|---|---|---|
| oracle, the true line | 25.8 percent | 100 |
| bounded on the pool | 26.7 percent | 65.8 |
| semi-bounded on the pool, the live mode | 25.8 percent | 57.5 |
| **shuffled control, the line destroyed** | **25.8 percent** | 8.3 |

Every paired delta is exactly 0.00 and every interval includes zero. Oracle to semi-bounded:
difference of medians +0.00, paired +0.00, interval [-1.67, +1.30].

**The shuffled control is what makes this readable.** Destroying the line entirely changes nothing,
so the near-node geometry columns carry no information, and the zero degradation from oracle to
semi-bounded says nothing whatever about the tracker. `fit_predict` takes a `use_line_key`
parameter that it never uses, which is the shape of the same mistake in the code.

**The frozen 1.67-point degradation is therefore not a measurement of the tracker's cost.** It is
noise on an inert feature pair, taken on one pairing. Superseded, not contradicted.

## Per-line standardisation does use the line, and does not survive the live mode

`id8_perline`. Per-line z-scoring is where the line genuinely earns its place: it takes cross-day
identification from 22.2 to 25.8 percent. But `per_line_z` looks up the line on the TEST rows, and
a deployed system does not know it.

**This stage reproduces the frozen figures exactly before claiming anything**: pooled 22.222
against a frozen 22.222, oracle per-line 25.833 against a frozen 25.833. The check is made on the
mean over pairings, which is the statistic the freeze reports.

| arm | mean | median | line agreement |
|---|---|---|---|
| pooled, no line at all | 22.22 | 20.83 | |
| oracle line | 25.83 | 26.67 | 100 |
| bounded on the pool | 25.46 | 25.00 | 65.8 |
| **semi-bounded on the pool** | **22.22** | 22.50 | 57.5 |
| shuffled control | 23.52 | 23.33 | 8.3 |

| comparison | paired delta | interval | excludes zero |
|---|---|---|---|
| pooled to oracle | +2.50 | [1.85, 5.65] | **yes** |
| oracle to shuffled | -2.50 | [-3.70, -1.02] | **yes** |
| **pooled to semi-bounded** | **+0.83** | **[-2.22, +2.41]** | **no** |
| oracle to semi-bounded | -3.33 | [-5.46, -1.76] | **yes** |
| shuffled to semi-bounded | -0.83 | [-2.78, +0.37] | no |
| shuffled to bounded | +1.67 | [0.65, 3.52] | **yes** |

**The benefit is real and it is line information**, because the shuffled control falls below oracle
outside the interval. **It does not survive the live mode.** At 57.5 percent line agreement the
live tracker's line is statistically indistinguishable from a randomly permuted one, and the gain
over the pooled arm has an interval that includes zero. The bounded line at 65.8 percent does
retain it.

## How accurate must the line be, and what the frozen headline actually contains

`id9_threshold` degrades the oracle line to a controlled agreement over five seeds and scores
per-line standardisation at each level.

| line agreement | accuracy | over pooled | **over a random line** | pairings above the random line |
|---|---|---|---|---|
| 0.0 | 23.70 | +1.48 | +0.00 | 0 of 9 |
| 17.8 | 22.74 | +0.52 | -0.96 | 1 of 9 |
| 37.7 | 23.31 | +1.09 | -0.39 | 3 of 9 |
| 47.8 | 24.26 | +2.04 | +0.56 | 6 of 9 |
| 58.5 | 24.31 | +2.09 | +0.61 | 6 of 9 |
| **68.5** | 25.04 | +2.81 | **+1.33** | **7 of 9** |
| 78.7 | 25.35 | +3.13 | +1.65 | 7 of 9 |
| 100.0 | 25.83 | +3.61 | +2.13 | 6 of 9 |

**The floor is the random-line arm, not the pooled arm, and that is the finding.** Z-scoring by a
grouping that carries NO information already beats pooled by **+1.48 points**. So of the frozen
22.2 to 25.8 result, about 1.5 points is variance normalisation that any arbitrary grouping would
buy, and only about 2.1 points is the line actually being right. **The headline overstates the
line's own contribution by roughly forty percent**, and the correct statement is that per-line
standardisation is worth 3.6 points of which 2.1 are line conditioning.

**Line information starts paying only from about 68.5 percent agreement.** The live mode supplies
57.5 and the bounded mode 65.8, which is exactly consistent with id8: bounded sits at the edge and
keeps the benefit, semi-bounded sits below it and does not.

## What to claim

- Identification is **25.8 percent cross-day against 16.7 chance** with the true line, and that is
  an oracle figure.
- **A live system gets 22.2 percent**, which is the pooled arm: the line its own tracker supplies
  is not accurate enough to condition on.
- The tracker would need roughly **68.5 percent line agreement** before conditioning on its output
  beats conditioning on nothing. Semi-bounded is at 57.5, so **this is a concrete, measured target
  for the second collection** rather than a vague aspiration.
- Six-person identification remains marginal, as the earlier record already says. Nothing here
  changes the three-person result.

## What was checked, because one version of this was wrong

The first attempt at `id8` set the half-stride artefact roots so the pooled decoder would load, and
those roots also select the identification ENCODER and the window set. It therefore scored the
0.5 s encoder against a freeze built on the 1 s one and produced an oracle figure 6.6 points low.
That is a confound, not a finding, and the numbers were discarded. The stages are now split:
`id8a_lines` computes the tracker's lines in its own process under the 0.5 s roots and writes them
to disk, and `id8_perline` runs under the frozen 1 s roots, asserts at import that the half-stride
roots are NOT set, and refuses to claim anything unless it reproduces both frozen figures first.

---

# MULTI-PASS VOTING, AND THE MEASURED LIMIT OF IDENTIFICATION ON THIS DATA, 2026-09-19

`id10_voting`. Frozen at `runs/IDENTIFICATION_FROZEN_2026-09-19b.json`.

**The line is supplied from the protocol throughout this section. No tracker output is read
anywhere in it.** That is deliberate: id8 and id9 established that a live tracker's line at 57.5
percent agreement is worth no more than a random one, so mixing it in here would only re-measure
that. Features are the frozen ones, the line-standardised embedding fused with the gait features
`speed, cadence, step_length`; no new feature was added. The classifier head is fixed to LDA rather
than chosen per row on the test set, because the frozen `score()` picks the better of two heads by
test accuracy and that would bend a curve read for where it flattens.

## 1. Choosing the line, held out on 01 and 02, never the other way round

Per-line accuracy of the POOLED classifier, averaged over the two folds inside sessions 01 and 02,
01 to 02 and 02 to 01. Session 03 is never used to choose.

| line | held-out mean | folds |
|---|---|---|
| **E_col5** | **41.7** | 33.3, 50.0 |
| **E_row1** | **41.7** | 33.3, 50.0 |
| **E_col1** | **41.7** | 16.7, 66.7 |
| B_rev | 33.3 | 16.7, 50.0 |
| D_fwd | 25.0 | 16.7, 33.3 |
| D_rev | 25.0 | 16.7, 33.3 |
| E_row5 | 25.0 | 16.7, 33.3 |
| A_rev | 20.8 | 25.0, 16.7 |
| B_fwd | 20.8 | 16.7, 25.0 |
| C_rev | 20.8 | 16.7, 25.0 |
| A_fwd | 16.7 | 16.7, 16.7 |
| C_fwd | 16.7 | 16.7, 16.7 |

**Three lines tie exactly at the top and the choice between them is arbitrary.** The tie was broken
alphabetically to E_col1, and that is recorded as a tie-break rather than a finding. All three
edge lines topping the table is consistent with the standing note that edge lines behave
differently from the diagonals.

**The confirmation on session 03 FAILS.**

| tied line | session 03 | n |
|---|---|---|
| E_col1, the chosen one | **16.7 percent** | 6 |
| E_col5 | 16.7 percent | 6 |
| E_row1 | **0.0 percent** | 6 |

Chance is 16.7 percent. The chosen line lands exactly on chance and one of the tied three lands at
zero. **Per-line selection is not supported by this data**: with six test passes per line in the
held-out session, no line could have confirmed, and the 41.7 percent that won the selection is six
passes' worth of noise. The selection procedure is reported because it was asked for and because
the table is auditable, not because it produced a usable line.

## 2. Multi-pass voting

The vote is the sum of the per-pass log posteriors over the group, argmax. Groups are k passes of
the same person on the same day; train 01 and 02, test 03.

**What the data allows.** Each participant walks each line at most TWICE in a day: 360 passes over
six people, three sessions, twelve lines. **A vote over three or more passes of ONE line does not
exist in this data.** Three scopes are therefore reported and labelled:

| scope | k available | why |
|---|---|---|
| same line, the chosen one | 1 only | no participant walked E_col1 twice in session 03 |
| same line, pooled over all twelve | 1 and 2 | 48 groups at k=2 |
| same day, across lines | 1 to 5 | twenty passes per person per day |

### The curve, cohort six, same day across lines

| k | fusion | interval | shuffled-line floor | speed only | substitution on the vote |
|---|---|---|---|---|---|
| 1 | 23.33 | [16.7, 30.8] | 19.17 | 28.33 | 45.8 percent |
| 2 | 21.40 | [18.9, 23.9] | 21.93 | 31.49 | 39.9 percent |
| 3 | 20.75 | [18.5, 22.8] | 21.75 | 34.58 | 32.8 percent |
| 4 | 21.25 | [18.9, 23.6] | 21.50 | 40.33 | 28.1 percent |
| 5 | 21.08 | [18.8, 23.5] | 21.92 | 42.67 | 28.1 percent |

### Every cohort size, fusion arm

| cohort | chance | k=1 | k=2 | k=3 | k=4 | k=5 | rises | flattens at |
|---|---|---|---|---|---|---|---|---|
| six | 16.7 | 23.3 | 21.4 | 20.8 | 21.2 | 21.1 | **no** | 2 |
| three, all 20 subsets | 33.3 | 41.8 | 43.0 | 42.6 | 43.3 | 42.5 | **no** | 2 |
| two, all 15 subsets | 50.0 | 55.0 | 56.5 | 57.2 | 58.0 | 57.5 | **no** | 2 |

Same line pooled over all twelve lines, cohort six: 23.3 at k=1 and 22.9 at k=2, also flat.

## 3. What the controls say, and they are the point

**THE CURVE DOES NOT RISE WITH PASSES, at any cohort size.** The largest k never beats k=1 outside
k=1's interval; every curve flattens by the second pass. **This is the measured version of the walk
being unidentifiable on this data**, and it is reported as such rather than as a number that needs
more passes.

**The fusion arm does not beat its own shuffled-line floor.** From k=2 onwards the floor is level
with or above it: 21.4 against 21.9, 20.8 against 21.8, 21.3 against 21.5, 21.1 against 21.9. Only
at k=1 is fusion ahead, 23.3 against 19.2, and those intervals overlap.

**The substitution test on the final vote FALLS as more passes are voted**, from 45.8 percent at
one pass to 28.1 at five. Replacing a group's passes with another participant's leaves the vote
unchanged about seven times in ten. For a six-class decision that is reading identity, the vote
should move on roughly five in six. **The vote is collapsing onto a few classes rather than
tracking the person**, and the more passes are added the more it collapses. By this project's own
standard the voted decision is not signal-driven.

**Per-recording accuracy is not bimodal**, flag False at the single-pass level, accuracy 26.7
percent with interval [19.2, 35.0]. So the weakness is genuine weakness and not the
read-the-recording artefact that the bimodality flag exists to catch.

**The speed-only baseline dominates everywhere and is the ONLY arm that rises with passes.**

| cohort | chance | speed k=1 | speed k=5 | rises |
|---|---|---|---|---|
| six | 16.7 | 28.33 | **42.67** | **yes** |
| three | 33.3 | 49.33 | **64.23** | yes |
| two | 50.0 | 65.00 | **79.07** | yes |

**What accumulates over repeated passes on this data is PACE, not the CSI representation.** This
qualifies the earlier record's claim that the work "is not pace recognition, because the speed
baseline is weak on this cohort at a separability ratio of 0.51". That statement was made on
single-pass accuracy, where it holds. Under voting it does not: pace separates people better than
the learned representation at every cohort size, and it is the only thing repeated observation
improves.

## 4. The identification-walk length

**There is no useful identification-walk length for the CSI representation on this data**, because
the curve is flat from the second pass. The honest entry for the second collection's protocol sheet
is therefore not a number of passes but the item already first on it: **deliberate speed variation
per participant**. Without it, pace and identity cannot be separated, and this section shows pace
is carrying whatever accumulates. If the intent is to claim identification from the radio rather
than from walking speed, the protocol has to break the correlation that currently does the work.

## 5. The demonstration, stated plainly

**The operator-assisted demonstration commits the line at the END PRESS, using the bounded rescore
on the shipped pool at 65.8 percent line agreement.** That is marginally below the 68.5 percent
crossing measured in id9, and it is below it on the paired reading which is the one that carries
the claim. **Identification conditioned on that line is therefore reported as viable AT THE END
PRESS and NOT during the walk**, and even at the end press it sits at the edge of the interval
rather than comfortably inside it. During the walk the live mode supplies 57.5 percent, which id8
showed is indistinguishable from a randomly permuted line, so nothing in the demonstration should
be described as identifying a person while they are still walking.






---

# 2026-09-23, gait conditioning, Doppler spectrograms and the corridor walk

Frozen at `runs/IDENTIFICATION_FROZEN_2026-09-23.json`. Pre-registered in `reports/PREREG_ID_2026-09-23.md` with 5 addenda, all hashed
**before any identification number in this batch existed**. Chance is 16.7 percent over
six participants. The 19b freeze is kept and not overwritten.

## How each claim changed relative to 19b

| claim in 19b | now |
|---|---|
| identification is 25.8 percent with the true line | reproduced at 25.926 with the FROZEN procedure, and **21.852 with the head fixed before the run**. The difference, 4.074 points, is test-set head selection |
| cadence is a gait feature | **cadence in the reference arm was resolved using ORACLE speed** on about a third of passes; A0 recomputes it without any speed |
| the geometry features are inert | unchanged, and now explained: **all twelve Room A lines fail the F gate** and line A is F = 0.000 on RX1 for its whole length |
| what accumulates over passes is pace | unchanged, and R6 now tests it arm by arm |
| there is no useful identification-walk length | unchanged; the DC2 requirement is now **computed**: NO design in the searched grid meets both targets. The grid tops out at 20 passes per block in 5 blocks, so DC2 cannot measure a six-way result at this effect size and the honest move is to commit to a smaller cohort |

## The arms

| arm | median over nine pairings | edge-line recall | agrees with the oracle speed control | R6 |
|---|---|---|---|---|
| A0 | 20.833 | 25.47 | 20.46 | fail |
| A1_ENV | 16.667 | 20.37 | 17.13 | fail |
| A2_SPEC | 19.167 | 23.61 | 16.2 | fail |
| A3_ENV_SPEC | 20.833 | 22.22 | 15.65 | fail |
| A6_ENCODER | 21.667 | 25.47 | 20.19 | fail |
| S0_ORACLE_SPEED | 22.5 | 23.15 | n/a, the control is not compared with itself | - |

**R6 is the verdict, not a robustness check.** An arm that beats chance but fails R6 is reported as
encoding pace. Arms passing R6: **NONE**.

## Conditioning

C3 took the branch **C3-normalise**, decided by measurement per addendum B.
Signal-vital stages under R1: **NONE**.

The sensed-speed validation gate returned r = 0.1022,
so A5 and S1 DID NOT RUN.

Band (b) physical check, observed torso content against the projected bistatic factor F:
r = 0.0828.
NOT DECIDABLE ON THIS RIG, and NOT a negative result. Room A's F spans only 0.333 to 0.474 across all twelve lines, so the prediction spans 3.0 Hz while the STFT bin width is 2.34 Hz, 78% of it. The observed values sit exactly on bins. The correlation r = 0.083 measures the quantiser, not the physics. DC2's node placement (addendum A) is what would widen the F range enough to decide this

## The corridor, and why it is a pilot whatever it shows

The corridor was chosen by geometry alone and never by accuracy. **Every one of the twelve Room A
lines is struck out by the pre-registered F gate, and so is every straight 4 m, 5 m and 7 m segment
anywhere in the room.** The pilot therefore runs on geometry known in advance to be unsuitable, and
a result either way says nothing about whether a corridor works on a rig built for one.

The useful output is for DC2, and it is a node-placement finding rather than a corridor one: over
543,004 layouts, **no arrangement spreading the four nodes across three or more walls can pass the
gate**, while a gait-first corner layout reaches min-link F 0.938 against this rig's 0.373. That is
a direct conflict with what multilateration wants, and it is Uzayr's decision.

## The outcome

**Outcome 3.** no gait arm passes R6. On this data the identity signal is dominated by pace and session, and that is reported as a measured sensing limit of three single-antenna, amplitude-only 2.4 GHz links

## Not quotable from this batch

- any within-day figure as evidence of identity: one recording per participant-session makes the recording and the person the same variable
- any speed-containing arm (A5, S0, S1) as an identification result
- the archived eight-class figures, which are on a retired cohort
- the corridor pilot as evidence about corridors: the Room A geometry fails the F gate

Stages NOT RUN in this batch, reported rather than omitted: **none**.
all_clean = **True** (48 passed in 1.14s).


---

# 2026-09-23b, gait identification maximisation: across days and within days

This section covers the IDMAX run, batch 2026-09-23b, stages id19 to id27. The code is in
`pipeline/identify/`, the results in `runs/identify/idmax/`, and the freeze in
`runs/IDENTIFICATION_FROZEN_2026-09-23b.json` with its `_ADDENDUM`.

The run was an exploratory maximisation, so the earlier pre-registered gates do not bind it. Every
number below is nevertheless nested:

- every choice was made on the training side;
- the test labels were sealed until predictions were committed, and a test proves it.

There are six participants, so chance is 16.67 percent. The intervals are 95 percent cluster
bootstraps over recordings. The p-values come from permuting labels over recordings, 1000 draws.

**WITHIN-DAY rows: same recording, learns the session and the recording as well as the person.**

## Headline table

| row | nested accuracy % | 95% interval | chance % | permutation p | cohort |
|---|---|---|---|---|---|
| **cross-day, leave one session out (the headline)** | **15.83** | [10.28, 21.67] | 16.67 | 0.71 | 6 |
| cross-day, nine pairings pooled (mean of pairings 19.26, median 19.17) | 19.26 | [15.83, 22.96] | 16.67 | 0.033 | 6 |
| WITHIN-DAY, temporal split | 32.64 | [23.59, 40.97] | 16.67 | 0.001 | 6 |
| WITHIN-DAY, leave one line out | 33.33 | [28.45, 37.95] | 16.67 | 0.001 | 6 |
| identification path, cross-day, nested choice of line | 13.33 | [3.23, 25.81] | 16.67 | 0.72 | 6 (n = 30) |
| identification path, cross-day, best-geometry line E_row1 | 16.67 | [0.00, 33.33] | 16.67 | 0.57 | 6 (n = 18) |
| identification path, WITHIN-DAY, centre lines, earlier pass enrols the later | 16.7 to 33.3 per line | see table P | 16.67 | | 6 (n = 18 per line) |
| RECORDING-SIGNATURE REFERENCE, cross-day | 20.28 | [6.66, 36.67] | 16.67 | 0.19 | 6 |
| RECORDING-SIGNATURE REFERENCE, WITHIN-DAY temporal | 91.67 | [86.11, 97.22] | 16.67 | 0.001 | 6 |
| RECORDING-SIGNATURE REFERENCE, WITHIN-DAY leave one line out | 98.61 | [97.23, 99.72] | 16.67 | 0.001 | 6 |
| SESSION-ID CONTROL, frozen gait features, predicting the day of 3 new people, 20 splits | 80.33 | [77.92, 82.47] | 33.33 | 0.001 | 3 of 6 |
| S0 oracle speed, cross-day (a control, never a result) | 32.50 | [23.89, 42.50] | 16.67 | 0.003 | 6 |
| learned family alone, 2D CNN on Doppler spectrograms, cross-day | 27.22 | [21.11, 33.61] | 16.67 | 0.001 | 6 |
| the same CNN with oracle speed regressed out of its embedding | 23.89 | [17.22, 31.39] | 16.67 | 0.013 | 6 |

**Edge-line recall, headline row:** E_col1 33.3, E_col5 16.7, E_row1 16.7, E_row5 16.7 percent, on
18 passes each.

**How the headline was chosen.** The headline is the final nested winner. In each fold it takes
whichever of the classical and learned selections scored the higher accuracy on the inner,
training-side split. It chose classical in every fold. The rule was fixed before the run.

The rule favours classical by the winner's curse. The classical inner accuracy is a maximum over
174 configurations and 18 heads; the learned one is a maximum over four architectures. The learned
family's own nested row is therefore shown beside the headline, and not in place of it.

## Positive controls, run first and mandatory

The same pipeline and the same nested selection were given labels that must be learnable (figure
`F2_positive_controls`):

| label | accuracy % | chance % |
|---|---|---|
| walking direction, cross-day | 94.44 | 50 |
| line, of twelve | 72.78 | 8.33 |
| a new person's session | 80.44 | 33.33 |
| a per-person rhythm injected at half the natural gait modulation | 32.22 | 16.67 |

The labels shuffled per pass and per recording fall to 15.83 and 14.17. The pipeline is not the
reason identification fails.

## Cohort size

Cross-day, the final winner, averaged over every subset of each size (figure `F1_cohort_size`):

| people | accuracy % | chance % |
|---|---|---|
| 2 | 49.33 | 50 |
| 3 | 32.44 | 33.3 |
| 4 | 23.50 | 25 |
| 5 | 18.83 | 20 |
| 6 | 15.83 | 16.7 |

**No cohort size reaches a mean above 50 percent cross-day, and none clears chance.**

Within-day temporal gives 62.50, 46.94, 40.56, 36.39 and 32.64 for two to six people. It is above
50 only at two people, and the recording-signature reference scores 99.31 at that size.

## The section 8 sweep, ranked by nested cross-day accuracy

Each menu item was searched nested on its own, around a common default; the table ranks them by
cross-day LOSO accuracy.

| menu item searched alone | LOSO % | interval | p | nine-pairing mean |
|---|---|---|---|---|
| D learned models (the 2D CNN in all three folds) | 27.22 | [21.11, 33.61] | 0.001 | 22.59 pooled |
| A1 conditioning (raw, Hampel, notch, static removal) | 21.67 | [16.39, 27.22] | 0.019 | 20.74 |
| B feature sets (every section 8 B set) | 18.61 | [15.00, 22.78] | 0.18 | 19.63 |
| A2 subcarriers (mean, RMS, per-pass PCA, RSSI) | 18.06 | [13.61, 22.78] | 0.28 | 17.31 |
| A4 segmentation (steady against walk_edge; acf cycles against step peaks) | 18.06 | [13.05, 23.61] | 0.24 | 18.89 |
| A3 bands | 17.22 | [13.06, 21.94] | 0.42 | 19.26 |
| E per-line z-scoring | 16.94 | [13.61, 20.83] | 0.48 | 20.00 |
| F link sets | 14.72 | [12.22, 17.50] | 0.83 | 16.67 |
| every item together, the run's nested search | 15.83 | [10.28, 21.67] | 0.71 | 19.26 |

**Heads.** Each of the 18 heads, searched alone, falls between 15.0 and 21.1. The best is gradient
boosting at 21.11 (p 0.031). With 26 rows tested, a p of that size is expected somewhere by chance.

**A1's interval** clears chance by 0.28 points, which is one pass in 360, so it is not a finding.

**Transductive alignment** cannot rescue the classical features:

| alignment | accuracy % |
|---|---|
| per-session standardisation (AdaBN for a classical head) | 15.56 |
| rank normalisation | 15.00 |
| CORAL | 15.00 |

**Voting.** Voting within the test day lowers the gait winner, from 15.83 at one pass to 12.42 at
five. Its calibration temperature is 12 to 20, which is the calibration's own verdict that the
per-pass outputs carry almost nothing. Speed alone rises from 32.50 to 36.11 (figure `F6_voting`).

## The identification path (table P)

Every one of the twelve directed lines is at chance cross-day, with intervals 20 to 45 points wide
on n = 36 (centre lines) or n = 18 (edge lines). Pooling a physical line's two directions changes
nothing, with direction-invariant features or with direction as a flag.

| directed line | cross-day LOSO % | interval | n | WITHIN-DAY % | n |
|---|---|---|---|---|---|
| A_fwd | 13.89 | [2.78, 27.78] | 36 | 27.78 | 18 |
| A_rev | 19.44 | [5.56, 33.33] | 36 | 33.33 | 18 |
| B_fwd | 13.89 | [2.78, 27.78] | 36 | 22.22 | 18 |
| B_rev | 13.89 | [5.56, 25.0] | 36 | 27.78 | 18 |
| C_fwd | 16.67 | [5.56, 27.78] | 36 | 16.67 | 18 |
| C_rev | 16.67 | [5.56, 30.56] | 36 | 33.33 | 18 |
| D_fwd | 11.11 | [2.78, 22.22] | 36 | 16.67 | 18 |
| D_rev | 19.44 | [5.56, 36.11] | 36 | 22.22 | 18 |
| E_col1 | 27.78 | [5.56, 50.0] | 18 | no cell | 0 |
| E_col5 | 16.67 | [0.0, 33.33] | 18 | no cell | 0 |
| E_row1 | 16.67 | [0.0, 33.33] | 18 | no cell | 0 |
| E_row5 | 22.22 | [5.56, 44.44] | 18 | no cell | 0 |
| A, both directions, invariant features / direction as flag | 16.67 / 16.67 | [8.33, 27.78] / [8.33, 25.0] | 72 | | |
| B, both directions, invariant features / direction as flag | 16.67 / 12.5 | [9.72, 23.61] / [5.56, 22.22] | 72 | | |
| C, both directions, invariant features / direction as flag | 19.44 / 22.22 | [11.11, 29.17] / [8.33, 37.5] | 72 | | |
| D, both directions, invariant features / direction as flag | 22.22 / 13.89 | [12.5, 33.33] / [6.94, 20.83] | 72 | | |


Choosing the line inside each fold picked C_rev, B_fwd and E_col1, a different line each time, and
the chosen lines scored 13.33 held out. Within-day on a single line, enrolling on the earlier pass,
the centre lines score 16.7 to 33.3 on n = 18.

**The DC2 path under the brief's rule.** The rule makes E_col1 the DC2 path, because run on all
three sessions it is item 6's nested choice. That choice failed its own held-out test. E_row1, the
best-geometry line, is the alternative, and the override is Uzayr's. The detail is in
`FINDINGS_stageid23.txt` and the DC2 sheet.

## Speed diagnostic

**The frozen configuration.** The linear probe for speed from its features gives R^2 = 0.096. The
brief's residualised accuracy is **not valid for a random-forest head**: it rose from 19.72 to
27.50. The test-side residual re-injects the test pass's oracle speed wherever the slope differs
between days, and with test speeds shuffled it falls to 16.39 (fault 3, `FINDINGS_stageid26.txt`).
Linear heads are unaffected and show no pace reliance: logistic regression scores 16.39 plain and
14.72 residualised.

**The learned CNN.** The same diagnostic on its embedding, with a linear head:

| reading | accuracy % | interval |
|---|---|---|
| plain | 30.00 | |
| true speed removed | 23.89 | [17.22, 31.39], p 0.013 |
| a shuffled speed removed | 27.78 | |

Linear-probe R^2 for speed is 0.118. Substituting another participant's pass changes 72.5 percent
of its decisions.

About half the CNN's margin over chance is pace. What remains clears chance by less than one pass
per fold.

## POST-HOC CEILING: selected on the test data, not a result

| configuration, head | cross-day LOSO % |
|---|---|
| Doppler contour shapes, walk_edge span, Hampel, gait-band mean, random forest | 28.33 |
| the same on the first three PCs | 28.33 |
| Doppler contour shapes, steady span, Hampel, random forest | 26.94 |
| the same on the first three PCs | 26.94 |
| Doppler contour shapes, steady span, running-mean removal, random forest | 26.67 |
| median over all 696 configuration-and-head pairs | 17.78 |

## What this run established

**The target of 50 percent was not reached in any honest scope at six people.** It was reached
across days at no cohort size at all. Within a day it was reached only at two people (62.5), where a
meter reading static amplitude levels, with no gait content, reaches 99.3.

**The within-day figures are recording recognition.** Each participant-session is a single
recording, so within a day the person and the recording are the same variable. The recording
signature identifies people within a day at 91.7 to 98.6 percent and collapses to 20.3 across days.
The frozen gait features name a new person's day at 80.3 percent against 33.3. Taken together,
whatever within-day accuracy the gait features show cannot be separated from recognising the
recording.

**Across days, nothing the run built identifies people by how they walk.**

- 174 feature configurations, 18 heads, voting and three alignments all stay at chance.
- The pipeline itself passes every positive control.
- The CSI-only cadence that the gait features rest on is not being measured: the three links
  disagree by a median 0.6 Hz, and cadence is not stable within a person (ICC 0.018).

**What carried the most** was path-rate content, not rhythm. The Doppler contour shapes top the
post-hoc ceiling. The 2D CNN on Doppler spectrograms is the only nested family above chance, at
27.2. About half of that is pace, and the rest is a weak signal that DC2 can test.

The DC2 sheet pre-registers the rule's configuration as primary and that CNN as a labelled post-hoc
secondary. DC2's separated rounds give cross-round within-day evaluation that is valid for the first
time. Its optional slower and faster pace round is the only direct test of gait against speed.


---

# 2026-09-23c, superseded claims and what is quotable

Written on 2026-09-23. **Identification on Room A is closed.** The earlier sections are left exactly
as written. This section lists every claim in them that is no longer quotable, with the reason and,
where one exists, the figure that replaces it. The one-page list of what may be quoted is
`reports/ID_QUOTABLE_2026-09-23.md`.

**Replacement sources.** The nested replacements come from the 2026-09-23b section of this report:

- figures: `runs/identify/idmax/id26_final/results.json`;
- freeze: `runs/IDENTIFICATION_FROZEN_2026-09-23b.json`.

| superseded claim | where | why it is not quotable | replaced by |
|---|---|---|---|
| two-person identification 66.0 percent, three-person 50.5 percent | 18 September, "Verification, the realistic pipeline, and cohort size" | produced by the frozen procedure, which picks the head on the test session and is not nested | nested cross-day cohort curve: **49.33** at two (chance 50) and **32.44** at three (chance 33.3), both at chance |
| "the gait question was answered YES on 3 pairings" | 18 September, the rules table and the scope statement; also `reports/HEADLINES.txt` line 23, a shared file this workstream does not edit | its speed-removed arm rested on cadence resolved with oracle speed, and on test-set head selection. Under nested evaluation no gait arm is above chance across days (R6 on 23 September; 15.83 in 23b) | **none**: on Room A the gait question is answered no. The only family above chance, the Doppler CNN, falls to 23.89 [17.22, 31.39] with speed removed, and is post hoc |
| 25.8 percent (per-line z) and 22.2 percent (pooled) across days | 18 and 19 September freezes | inflated about 4 points by picking the head on test accuracy | **21.85** and **19.17** with the head fixed (23 September), then the nested **15.83** |
| cadence from the step/stride harmonic resolution | 18 and 19 September | resolved with ORACLE speed on 115 of 360 passes (31.9 percent) | the CSI-only cadence (23b), which does not measure cadence on this rig: the links differ by a median 0.60 Hz, and the within-person ICC is 0.018 |
| the realistic pipeline, 31.67 percent with the true line and 30.00 with the tracker's | 18 September, "Verification, the realistic pipeline, and cohort size" | one pairing under the frozen procedure, heads picked on test, not nested; the 19 September live-mode section already found that per-line standardisation does not survive the live mode | the nested nine-pairing figure, with per-line z-scoring available to the search: **19.26** pooled |
| the random-forest speed-residualised 27.5 percent | 23b, id26 speed diagnostic | fault 3: the test-side residual re-injects the test pass's oracle speed (it falls to 16.39 with the test speeds shuffled) | for a linear head on the same features: **14.72** residualised, 16.39 plain |
| verification AUC 0.684 and EER 0.405 | 18 September | never re-evaluated under the nested protocol | **none**; do not quote without re-running nested |
| any within-day figure as evidence of identity | every section | each participant-session is one recording, so within a day the person and the recording are the same variable | within-day figures are quoted only beside the recording-signature reference (**91.67** to **98.61** with no gait content) and labelled as recording recognition |

**What remains open.** Only the pre-registered DC2 scoring
(`reports/PREREG_ID_DC2_2026-09-23.md`, SHA-256 `e5d7acfa31f9006e9703e54dd4dc41f76d33d19b935b3f6c58dca10062479cb3`)
remains, and it is run once by `pipeline/identify/id28_dc2_score.py` on the DC2 data.


---

# 2026-09-23e, two properties of the feature code, found while building the DC2 scorer

Written on 2026-09-23. **Neither changes any quoted figure,** because every Room A result they
touch is already at chance, but both limit what those results can mean. They were found on
synthetic data and are set out in `reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_B.md`, P2.

1. **A "single-link" row built from three-link features is not single-link.**
   `id19_featbank.pass_features` resolves ONE cadence across all three links and computes every
   link's rhythm, autocorrelation shape and templates at it. The per-link column filter also keeps
   the cross-link cadence columns. On synthetic data, a noise-only link identified people at 66.7
   percent by borrowing another link's rhythm.
   - **23b consequence:** its F_links block (each link alone: 14.72 nested, at chance) was not a
     true single-link test.
   - **DC2:** P2 computes each link's features from that link alone.
2. **The features carry segment length, and so pace.** On pure-noise passes differing only in
   duration (chance 16.67), a random forest named the duration class:
   - at 58.3 percent using every feature family;
   - at 25 to 33 percent using the PRIMARY columns.

   **The 23b claim that no feature depends on the number of samples holds for explicit counts but
   not in effect.** Finite-length estimation of spectra, autocorrelation and modulation depth
   varies with duration. On a fixed-length path, duration is speed.
   - **DC2:** P2 adds a fixed-length (2.0 s crop) version, and P3 reads PRIMARY's pace verdict in
     that light.


---

# 2026-09-23f, integrated gait analysis with pace as a gait parameter (EXPLORATORY)

Written on 2026-09-23. Room A was reopened for this one labelled exploratory run by Uzayr's
decision (decision 11 in `reports/DECISIONS_ID_2026-09-23.md`). **Every figure in this section is
EXPLORATORY until DC2 confirms it, and none replaces a quotable figure.**

- **Code:** `pipeline/identify/idgp_*.py`.
- **Results:** `runs/identify/idgp/`.
- **Figures:** `runs/identify/idgp/figures/FGP1` to `FGP5` (PDF and PNG).
- **Freeze:** `runs/IDENTIFICATION_FROZEN_2026-09-23f.json`, with
  `reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_C.md`.

Every choice was made nested, on the training side, from menus fixed in `reports/QUEUE_IDGP.md` at
19:47 before any run. Six participants, chance 16.67 percent. Intervals are 95 percent cluster
bootstraps over test recordings; p-values permute identities over the recordings of each test
session, 1000 draws.

## The identification contract, which binds every row below

Every arm sees exactly what DC2 gives identification, and nothing else:

1. the CSI of the three receivers between the walk's start and end;
2. the start and end times, which in Room A are the pass's first and last presses (0 m and 5 m);
3. the path's identity and protocol length, with the rig's node positions.

Intermediate presses, interpolated positions, other labels and everything from the tracking branch
are unreachable. The object handed to the features is `idgp_contract.ContractPass`, and ten tests
in `tests/test_idgp_contract.py` enforce it: the field set, start-to-end CSI only, a row stripped or
poisoned builds the same pass, and no tracking module is imported or loaded. A mutant module that
imported tracking code and read the anchor times turned three of them red.

**Pace** is S_se: 5.0 m (7.07 m on C and D) over the time between the start and end presses. It is
called "pace from walk start and end" throughout.

## Headline: A_fwd, nested leave one session out (figure FGP1)

| arm | accuracy % | 95% interval | p | n | minus S0, points [interval] | share of gain from speed |
|---|---|---|---|---|---|---|
| **S0, pace only (the bar)** | **36.11** | [19.44, 52.78] | 0.011 | 36 | | |
| G, gait without pace | 22.22 | [8.33, 41.67] | 0.29 | 36 | -13.89 [-38.89, 11.11] | no pace input |
| GP, full parameter set | 25.00 | [8.33, 41.67] | 0.15 | 36 | -11.11 [-38.89, 16.67] | S0 alone scores higher |
| GP + CNN, early fusion | 36.11 | [16.67, 58.33] | 0.018 | 36 | 0.00 [-22.29, 25.00] | all of it (1.00) |
| GP + CNN, late fusion | 30.56 | [11.11, 50.00] | 0.055 | 36 | -5.56 [-33.33, 19.44] | S0 alone scores higher |
| GP stack | 13.89 | [2.78, 27.78] | 0.73 | 36 | -22.22 [-41.67, 0.00] | arm at chance |
| GPu, CSI-sensed speed | not run | | | | | S_csi failed its validation |

**Per fold** (s01+02 to s03, s01+03 to s02, s02+03 to s01):

| arm | per fold % |
|---|---|
| S0 | 41.67, 41.67, 25.00 |
| G | 25.00, 25.00, 16.67 |
| GP | 25.00, 16.67, 33.33 |
| GP + CNN early | 50.00, 33.33, 25.00 |
| GP + CNN late | 41.67, 16.67, 33.33 |

**Per person, the arm's correct decisions out of 6** (P1 to P6):

| arm | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| S0 | 2 | 2 | 2 | 0 | 3 | 4 |
| GP + CNN early | 4 | 4 | 2 | 0 | 1 | 2 |
| GP | 3 | 4 | 1 | 1 | 0 | 0 |

The pace arms gain on P1 and P2 and lose on P5 and P6. P4 is never identified by anything.

## Integrity checks

1. **Beats speed alone.** FAILED by every pace arm: no paired interval lies above zero. **Every pace
   arm is therefore named "speed comparison"** (check 4).
2. **Gait carries weight.** Each arm's selected configuration was refitted with S_se alone, and with
   S_se, step length, walk ratio and speed-adjusted cadence removed:

   | arm | arm % | speed only % | speed removed % |
   |---|---|---|---|
   | GP | 25.00 | 36.11 | 19.44 |
   | GP + CNN early | 36.11 | 25.00 | 27.78 (the CNN embedding kept; it carries some pace itself) |
   | GP + CNN late | 30.56 | 36.11 (S0) | 25.00 |
   | GP stack | 13.89 | 36.11 (S0) | 13.89 |

   G's own columns carry little pace: a ridge probe predicts S_se from them at test-day R^2 = 0.063
   (0.087, 0.036, 0.067 by fold).
3. **Speed-overlap test** (figure FGP4). In each fold, the five pairs of fifteen whose training-side
   pace overlaps most (d' 0.00 to 1.16) were taken, each arm refitted on the pair, and scored on
   the pair's A_fwd test passes (n = 60, chance 50):

   | arm | accuracy % | 95% interval | minus S0 [interval] |
   |---|---|---|---|
   | S0 | 55.00 | [45.45, 65.16] | |
   | G | 51.67 | [37.10, 66.67] | -3.33 [-20.38, 13.34] |
   | GP | 46.67 | [32.00, 62.07] | -8.33 [-23.33, 6.67] |
   | GP + CNN early | 55.00 | [39.70, 73.08] | 0.00 [-16.67, 16.67] |
   | GP + CNN late | 53.33 | [36.21, 71.67] | -1.67 [-16.00, 13.24] |
   | GP stack | 40.00 | [27.27, 54.55] | -15.00 [-27.78, -1.52] |

   Where speed cannot separate two people, nothing else does either: every arm is at chance.
4. **Naming.** Every pace arm failed check 1 and is a speed comparison, however it is built.

**Substitution test** (the project standard). Each A_fwd test pass was given another participant's
CSI from the same test session, keeping its own pace, or another participant's pace, keeping its own
CSI:

| arm | CSI swapped: decisions changed % | pace swapped: decisions changed % |
|---|---|---|
| G | 83.33 | 0.00 |
| GP | 75.00 | 33.33 |
| GP + CNN early | 83.33 | 25.00 |

The arms do read the CSI. What they read changes the answer, but not towards the right person.

## Pace and cadence as measurements

**S_csi, the unbounded variant, FAILED** and GPu was dropped:

- its correlation with S_se is 0.05 pooled, and 0.07, 0.08 and 0.01 on the three training sides,
  against the 0.8 rule;
- the median duration error is 1.47 s, and onset errors run from -1.61 to 1.67 s (interquartile).

On Room A the motion-energy detector cannot find the walk, because the recording span also holds the
walk to the start mark and the turn.

**Cadence stays unreliable** (figure FGP5). It was fused across three sources and three links, with
weak sources dropped and harmonics resolved without speed, over 3.9 strides per segment (median):

| margin | person ICC, passes | person ICC, day medians | recording ICC | link disagreement, Hz | r with S_se |
|---|---|---|---|---|---|
| 0 s (chosen in 7 of 9 folds) | 0.033 | 0.464 | 0.046 | 0.548 | 0.115 |
| 0.5 s | -0.006 | -0.076 | -0.008 | 0.534 | 0.063 |
| 23b CSI-only cadence, for reference | 0.018 | | | 0.60 | 0.156 |

**The per-pass ICC stays below 0.2, so every cadence-derived parameter inherits that weakness**:
stride time, step length, walk ratio and speed-adjusted cadence. The per-day ICC of 0.46 says a
person's median cadence over 20 passes repeats across days better than any single pass does. That
is 3 values per person, and it is a reason to try multi-pass cadence in DC2's blocks, not a result.

**The geometry correction does not describe this rig.** On A_fwd, F for TX-RX2 and TX-RX3 rises from
0.18 to 0.82 along the walk, which predicts the raw torso contour should rise (slope +1.41 in
normalised units). It is flat instead:

| link | raw slope | corrected slope | frames masked |
|---|---|---|---|
| TX-RX2 | -0.04 | -1.66 | 2.7 percent |
| TX-RX3 | -0.07 | -1.68 | 2.7 percent |

TX-RX1 is masked throughout (F = 0 on line A). The correction therefore creates a trend rather than
removing one: the 4 to 70 Hz torso contour on this rig does not track 2 F v / lambda. The nested
search chose the corrected form in 22 of 54 arm-folds on A_fwd, as a free choice among equals.

**Per link beside mean F, G features, that link's own cadence, A_fwd:**

| link | mean F on A_fwd | accuracy % | 95% interval |
|---|---|---|---|
| TX-RX1 | 0.00 | 19.44 | [8.33, 30.56] |
| TX-RX2 (home) | 0.50 | 13.89 | [2.78, 25.00] |
| TX-RX3 | 0.50 | 22.22 | [8.33, 38.89] |

There is no ordering by F on Room A. DC2's P2 is the test with a link at F = 0.98.

## Cohort size (figure FGP2)

The fold's selected configuration refitted on every subset, mean over subsets, A_fwd, leave one
session out:

| people | S0 % | G % | GP + CNN early % | chance % |
|---|---|---|---|---|
| 2 | 73.33 | 59.44 | 70.00 | 50 |
| 3 | 54.72 | 37.78 | 56.67 | 33.3 |
| 4 | 47.78 | 28.61 | 48.06 | 25 |
| 5 | 37.22 | 21.67 | 41.11 | 20 |
| 6 | 36.11 | 22.22 | 36.11 | 16.7 |

- The best pace arm stays above 50 percent up to **three people** (56.67), where it exceeds S0 by
  1.95 points. That margin is well inside any interval these n allow.
- S0 alone is above 50 up to three people too (54.72).

## MULTI-PASS: identification from several walks (figure FGP3)

- **A_fwd:** there are only two A_fwd passes per person per test day. Voting both (n = 18
  decisions) gives:
  - S0: 36.11 to 33.33;
  - G: 22.22 to 27.78;
  - GP + CNN early: 36.11 to 38.89.
- **All lines, scope (b), k walks voted:**

  | arm | k = 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | S0 | 28.06 | 31.20 | 32.72 | 31.83 | 33.39 |
  | G | 20.83 | 21.20 | 22.69 | 24.22 | 24.81 |
  | GP + CNN early | 30.56 | 34.68 | 36.89 | 38.14 | 38.92 |

The single pass is the headline. At five walks the pace-plus-CNN arm leads pace alone by 5.5
points, with no interval computed. DC2's 5-pass blocks score multi-pass once (addendum C).

## Secondary rows

**Every line, re-selected with all lines as target (scope b), leave one session out, n = 360:**

| arm | accuracy % | 95% interval | p | minus S0 [interval] |
|---|---|---|---|---|
| S0 | 29.17 | [17.77, 41.67] | 0.012 | |
| G | 22.78 | [18.06, 27.50] | 0.007 | -6.39 [-21.40, 8.33] |
| GP | 35.00 | [27.50, 42.78] | 0.001 | 5.83 [-7.50, 18.61] |
| GP + CNN early | 33.33 | [24.44, 41.12] | 0.001 | 4.17 [-11.94, 19.74] |
| GP + CNN late | 37.22 | [28.61, 45.56] | 0.001 | 8.06 [-6.94, 22.22] |

- **The lower bound.** G across all lines is the first gait-without-pace row whose lower bound
  (18.06) clears chance. It is one row among many, the margin is 1.4 points, and G's columns carry
  a little pace (R^2 0.06), so it is not a finding.
- **Edge lines, G:** E_col1 27.78, E_col5 16.67, E_row1 0.00, E_row5 22.22 (n = 18 each).
- **Edge lines, GP + CNN late:** 38.89, 27.78, 27.78, 38.89.
- **Centre lines.** Per directed line the centre lines (n = 36) span 13.89 to 36.11 for G and 33.33
  to 44.44 for GP + CNN late; the full table is in `runs/identify/idgp/idgp_eval/results.json`.

**Nine pairings, A_fwd**, the six single-session pairings pooled (n = 72), with the three two-session
folds as in the headline:

| arm | six single-session pairings % | 95% interval | nine pooled % |
|---|---|---|---|
| S0 | 33.33 | [22.22, 44.44] | 34.26 |
| G | 27.78 | [16.67, 40.31] | 25.93 |
| GP | 30.56 | [18.06, 43.09] | 28.70 |
| GP + CNN early | 30.56 | [19.44, 43.06] | 32.41 |
| GP + CNN late | 23.61 | [13.89, 36.11] | 25.93 |

**WITHIN-DAY, SAME RECORDING, CONFOUNDED** (temporal split, all lines, n = 144): S0 34.72, G 30.56,
GP 39.58. These say nothing about identity; Room A's static-level signature reached 91.67 within a day.

**Positive controls, the final pipeline**:

| label | IDGP % | 95% interval | chance % | 23b % |
|---|---|---|---|---|
| walking direction | 90.28 | [87.15, 93.06] | 50 | 94.44 |
| line | 71.94 | [65.56, 78.33] | 8.33 | 72.78 |

Both used raw Doppler, rhythm, envelope and motion profile with shrinkage LDA. Nothing regressed.

## POST-HOC CEILING: selected on the test data, never quoted

| arm | best candidate by test accuracy | LOSO % | median over candidates % |
|---|---|---|---|
| S0 | scope (a), LDA | 41.67 | 33.33 (10) |
| G | scope (b), random forest, late F-weighted, raw | 36.11 | 19.44 (60) |
| GP | scope (b), random forest, late F-weighted, raw | 47.22 | 26.39 (60) |

## The DC2 freeze

- **The arm.** No pace arm passed check 1, so the rule froze **G**. Its configuration is gradient
  boosting on the concatenated features with the corrected Doppler form. The three folds chose three
  different G configurations, and this one won the tie on inner accuracy, so Room A does not favour
  it.
- **P1-GP.** It trains on DC2 day 1 A_fwd natural passes only and is scored once on day 2, beside S0.
  The analysis also covers the four integrity checks, the pace blocks and a multi-pass row per day 2
  block.
- **The pace-block reading.** It was rewritten for an arm without pace (addendum C, section 4):
  GAIT-CONSISTENT only if G keeps more accuracy than S0 on the slow and fast passes and does not drop
  itself.
- **The scorer.** It is `pipeline/identify/idgp_dc2_score.py`, gated on the pre-registration,
  addendum B and addendum C, and has been tested on synthetic recordings only. id29 is unchanged.
- **The path.** A_fwd is identical in `paths.py`, sheet 23d, the field card, the capture wrapper and
  addendum B: (2.5, 0) to (2.5, 5), heading N, away from the TX. F for the moved RX2 is the same in
  both directions: 0.981 at the primary spot, 0.947 at the fallback.

## What this run established

- **Integrated gait did not beat speed alone on Room A.** The best integrated arm, GP with the CNN
  embedding, tied pace from walk start and end at 36.11 percent on A_fwd. The difference was 0.0
  points, interval -22.3 to 25.0, n = 36. Every other pace arm scored below S0.
- **By person.** The pace-plus-CNN arm gained on P1 and P2, lost on P5 and P6, and never identified
  P4.
- **Where speed cannot separate two people,** every arm was at chance.
- **The spatio-temporal parameters are not being measured.** Cadence is not a stable measurement on
  this rig (per-pass ICC 0.033), so stride time, step length and walk ratio inherit its noise. The
  geometry correction did not describe the torso contour, and CSI-sensed speed could not find the
  walk.
- **What DC2 will test.** It scores the arm without pace, G, once from day 1 to day 2 on A_fwd with a
  link at F = 0.98. It scores it beside S0 on the same passes, on the lowest-overlap pairs, and on the
  slow and fast blocks, where the only way G can show that it reads something other than pace is to
  hold its level while S0 drops.
- **The wording.** The thesis should NOT use "identification from Wi-Fi-sensed spatio-temporal gait
  parameters, of which pace is one", because integrity check 1 failed. On Room A the honest wording
  is that pace from walk start and end carries more identity than any gait representation built
  here, with or without pace among its inputs.

---

## APPENDIX, 2026-09-24: the identification closing documents

Appended 2026-09-24 08:18 SAST by the cleanup session (`cleanup_prompt_2026-09-24`). Each section below is a source document's text verbatim, with its headings demoted three levels so they nest here. A one-line note marks any figure a later document overrides. Every source is also in git at the tag `pre-cleanup` under its original path. No participant is named in any of them (the IDMAX section's no-names test reads from that section to the end of this file).

| source | date | one-line summary | original |
|---|---|---|---|
| `CLOSING_ID_2026-09-23.md` | 2026-09-23, 11:05 | Closing report of the gait conditioning and corridor batch: A3 at 20.833 % cross-day, ICC 0.421, DC2 sheet corrected to 4 to 5 blocks. | deleted; this section is its home |
| `CLOSING_IDGP_2026-09-23.md` | 2026-09-23 (batch 23f) | Closing report of IDGP, integrated gait with pace as one gait parameter (exploratory). | kept, `reports/QUEUE_IDGP.md` cites it |
| `HANDOVER_ID_2026-09-23.md` | 2026-09-23, 19:40 | The identification workstream's handover: DC2 identification readiness, the slot design, the rehearsal, and where everything lives. | deleted; this section is its home |

### CLOSING_ID_2026-09-23.md

**Source:** `reports/CLOSING_ID_2026-09-23.md`, 2026-09-23, 11:05. **SHA-256:** `19dbaa47541c5afb3891e8ff85113040cb5d6ff6cbc6bcc1c76b0a9c11250896`. **Original deleted** on 2026-09-24; this section is its home.

> **Superseded:** Its A3 figure (20.833 percent, ENV + SPEC) is not quotable. The nested cross-day headline is 15.83 percent [10.28, 21.67], p 0.71 (`reports/ID_QUOTABLE_2026-09-23.md`, first row, from `runs/identify/idmax/id26_final/results.json`). `reports/ID_QUOTABLE_2026-09-23.md` lists the only identification figures the thesis may quote; anything else is superseded.

#### Closing report: identification, gait conditioning and the corridor. 2026-09-23

Batch opened 00:50 SAST, closed 11:05. Frozen at `runs/IDENTIFICATION_FROZEN_2026-09-23.json`.
Every figure below comes from **one clean end-to-end run** finished 11:01 with the final code, and
each reproduces the earlier partial runs exactly. **No tracking file was written and no tracking
process was signalled at any point.**

##### Verdict per item

| # | item | verdict |
|---|---|---|
| 0 | GATE, wait for tracking | **DONE.** Held 00:50 to 05:48, ~5 h. No CSI read. All code, tests and the pre-registration written inside it |
| 1 | `id11` audit and reproduce | **DONE, PASSED.** The gate held and opened |
| 2 | DC2 sheet v0 | **DONE** 01:00, then revised three times from measurement |
| 3 | `id12` conditioning, M1-M5, R1 | **DONE.** No stage is signal-vital |
| 4 | `id13` representations, speed gate | **DONE.** Gate FAILED at r = 0.102, so A5 and S1 did not run |
| 5 | `id14` cross-day, R6, R7 | **DONE.** No arm passes R6 |
| 6 | `id15` corridor, geometry tool, power, final DC2 sheet | **DONE.** ICC measured at 0.421 |
| 7 | `id16` day bias, R4 | **DONE.** R4 not supported |
| 8 | `id17` learned models | **DONE.** id17a ran; id17b NOT RUN, drop-order entry 2, reason recorded |
| 9 | `id18` report, figures, freeze, tests | **DONE.** `all_clean = True`, 48 tests |

**BLOCKED items: none.** Nothing was dropped.

##### Which section 11 outcome holds

**OUTCOME 3.** No gait arm passes R6. On this data the identity signal is dominated by pace and
session, and it is reported as a measured limit of three single-antenna, amplitude-only 2.4 GHz
links.

##### The best gait-only cross-day figure, with its interval

**A3, ENV + SPEC: 20.833 percent**, median over nine cross-day pairings, against chance 16.667.
Median recording-level 95 percent interval **[9.17, 35.83]**, which contains chance.
Edge-line recall 22.22 percent. It fails R6, beating the permutation null on **1 of 9** pairings
where five are required, and it sits **below the oracle speed control at 22.5 percent.**

##### What is quotable, and what this corrects in the existing record

- **The frozen 19b figures are inflated by test-set head selection.** The pipeline reproduces them
  exactly with the frozen procedure (22.222 and 25.926) and gives **19.167 and 21.852** with the
  head fixed before the run. Margins over chance roughly halve.
- **Cadence in the frozen reference arm was resolved using ORACLE speed on 115 of 360 passes
  (31.94 percent)**, matching the frozen record's own count.
- **No conditioning stage is signal-vital**, and C2 and C3 have intervals entirely below zero:
  removing them improves the signal. C3 was dropped by its own registered clause.
- **The Doppler premise is UNTESTED, not refuted.** Room A's F spans 0.333 to 0.474, so the
  prediction spans 3.0 Hz against an STFT bin of 2.34 Hz. The physics check is `NOT DECIDABLE`.
- **Geometry:** all twelve Room A lines fail the F gate; line A is F = 0.000 on RX1 for its whole
  length; no node layout spread over three or more walls can pass.

##### The DC2 sheet

**`reports/DC2_ID_PROTOCOL_2026-09-23.md`.** Three decisions wait on Uzayr, all with measured
numbers behind them:

1. **Node placement.** A gait-first layout gives 2.5x the projected Doppler factor, and conflicts
   directly with what multilateration wants. Run `pipeline/identify/id15_factor_map.py` BEFORE the
   nodes are fixed.
2. **Blocks, not passes.** At the measured ICC of 0.421, going from 2 to 5 blocks moves the
   interval from 17.7 to 11.5 points; going from 8 to 20 passes inside a block moves it from 17.7
   to 16.7. **4 to 5 blocks of 8 passes.**
3. **Cohort size.** Zero of 28 designs reach the plus or minus 10 point target for six people.
   Accept a wider interval, or commit to three.

##### Caveats a reader must carry

- The corridor pilot ran on geometry known in advance to fail the F gate. R5 stands: pilot only.
- `idle` is not a valid stationary null and M1 is claimed against `grid` alone (addendum E).
- Eleven of the seventeen figures in the brief were not produced. Six were, and they are the ones
  that carry the result: F8, F9, F12, F15, F17, F17b.
- Ten faults were found and fixed during the run. **Not one crashed**; every one produced a
  plausible null. They are itemised in `reports/QUEUE_ID.md` and `reports/CHECKIN_LOG_ID.md`.

### CLOSING_IDGP_2026-09-23.md

**Source:** `reports/CLOSING_IDGP_2026-09-23.md`, 2026-09-23 (batch 23f). **SHA-256:** `368b81adae7a16fdaddab81e2b9594b4718b74fabd7b7b2ee2e0b6af5a9c83b4`. **Original kept** because `reports/QUEUE_IDGP.md` cites it.

> **Superseded:** `reports/ID_QUOTABLE_2026-09-23.md` lists the only identification figures the thesis may quote; anything else is superseded.

#### Closing report: IDGP, integrated gait with pace as one gait parameter (2026-09-23f)

Batch opened 19:47 SAST, items 1 to 8 done by 20:17 on 2026-09-23. EXPLORATORY on Room A (decision
11). The full account is `reports/IDENTIFICATION_2026-09-18.md`, section "2026-09-23f".

##### The answer

**Integrated gait did not beat speed alone.** Under the identification contract (the CSI between the
start and end presses, those times, and the path), on A_fwd, nested leave one session out, n = 36:

| arm | accuracy % | 95% interval | minus S0 |
|---|---|---|---|
| S0, pace from walk start and end | 36.11 | [19.44, 52.78] | |
| G, gait without pace | 22.22 | [8.33, 41.67] | -13.89 |
| GP | 25.00 | [8.33, 41.67] | -11.11 |
| GP + CNN, early | 36.11 | [16.67, 58.33] | 0.00 [-22.29, 25.00] |
| GP + CNN, late | 30.56 | [11.11, 50.00] | -5.56 |
| GP stack | 13.89 | [2.78, 27.78] | -22.22 |

- **Check 1 fails for every pace arm**, so each is named "speed comparison".
- **On the lowest-d' third of pairs,** every arm is at chance (S0 55.0, G 51.7, best 55.0, n = 60).
- **By person,** the best arm gained on P1 and P2 and lost on P5 and P6; P4 was never identified.
- **The wording** "identification from Wi-Fi-sensed spatio-temporal gait parameters, of which pace is
  one" is not available.

##### Why the parameters could not help

- **Cadence is still noise.** Fused over three sources and three links, its per-pass person ICC is
  0.033, and the links differ by 0.55 Hz. Every cadence-derived parameter inherits that.
- **CSI-sensed speed fails** (r = 0.05), so GPu was dropped.
- **The geometry correction does not describe this rig.** The torso contour stays flat where F
  predicts a fourfold rise, so correcting it creates a trend rather than removing one.
- **The positive controls hold:** direction 90.28, line 71.94. The pipeline is not the reason.

##### DC2

- **Frozen: arm G** (no pace arm passed check 1), in `runs/IDENTIFICATION_FROZEN_2026-09-23f.json`.
  The DC2 rows are pre-registered in `reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_C.md` (written 20:10
  before any DC2 data, SHA-256 `eaa344477e87ab58ade65cb8e442e273ee9ecd675a55be45f9bd7f03293e6481`):
  - P1-GP beside S0;
  - the four integrity checks;
  - the pace-block reading rewritten for an arm without pace;
  - a multi-pass row per day 2 block.
- **The scorer** is `pipeline/identify/idgp_dc2_score.py`. It is hash-gated on the pre-registration
  and addenda B and C, and tested on synthetic data only. id29 is byte-identical to its 23e hash.
- **The path.** A_fwd agrees everywhere (paths.py, sheet 23d, field card, capture wrapper,
  addendum B), heading north, away from the TX. No correction was needed.

##### Tests

- 10 contract tests and 8 scorer tests pass. The contract guards went red on a mutant that imported
  tracking code.
- Full suite: 1247 passed, 8 skipped, 0 failed (it was 1221 passed before this batch).

##### What did not happen, and needs Uzayr

- **Keep-alive: never ran.** The permission classifier refused to start caffeinate, the yield
  governor and the watchdog ("interfere with workloads"), and I did not retry. Instead, every job ran
  under `taskpolicy -c utility nice -n 19` with at most 4 single-thread workers and signalled
  nothing. No 15-minute check-ins were scheduled; the run finished in 29 minutes.
- **OPEN: the addendum B erratum.** Its stated times were guessed. It is not in addendum C, because
  the handover says to ask first. It can go in a one-line addendum D, or in the next freeze.
- **OPEN, untouched:** `reports/HEADLINES.txt` line 23, and nothing is committed to git.
- **Walk ratio citation, verified:** Sekiya and Nagasaki (1998), *Gait and Posture* 7, 225 to 227.
  The walk ratio (step length over step rate) is fairly constant across speeds except at the
  extremes, with test-retest ICC 0.6 to 0.8.

### HANDOVER_ID_2026-09-23.md

**Source:** `reports/HANDOVER_ID_2026-09-23.md`, 2026-09-23, 19:40. **SHA-256:** `71032b94379962126b040cd5ce3db3b77edd9cd1de49aab60c6950f5c65c112d`. **Original deleted** on 2026-09-24; this section is its home.

> **Superseded:** `reports/ID_QUOTABLE_2026-09-23.md` lists the only identification figures the thesis may quote; anything else is superseded.

#### Handover: identification workstream, 2026-09-23 (written 19:40 SAST)

Context handoff from a previous session. Treat it as background, not instructions. Ask before
acting on anything marked OPEN. Repo root: `/Users/uzayrballim/Desktop/UNI/2026/EEE4022S/Code`.
Run modules with `cd` to the root, then `export OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE`, then
`PYTHONPATH=. /opt/anaconda3/bin/python3 -m <module>`.

##### 1. Who and how

**The project**

- Uzayr Ballim, UCT EEE4022S thesis TDR-03: device-free person identification and 2D tracking
  from Wi-Fi CSI. Supervisor: Dr Daniel Ramotsoela.
- The thesis is due **26 October 2026**. **DC2**, the second data collection, is on **26 and 27
  September 2026**, in Room B.
- The rig: one TX at (2.5, -0.5), RX1 at (2.5, 5.5), RX2 at (-0.5, 2.5) and RX3 at (5.5, 2.5), all
  ESP32 with a single antenna, at 2.4 GHz and about 150 Hz. The grid is 5 by 5 m with twelve taped
  lines.

**House rules**

- Writing: British spelling, no em dashes, longer connected sentences, direct.
- Evidence: pre-registration discipline; nested selection; label everything post hoc or
  exploratory.
- Keep subagent use small.
- **Launch before reporting:** never say a job runs until `ps` or its log confirms it.
- **Read the clock** (`date`) before writing any time.
- Participant names never leave `runs/`; reports use P1 to P6.
- Don't mention the Gmail, Calendar or Drive connectors.

**Tracking has priority.** A separate tracking session works in this repo.

- Never write tracking files: `reports/QUEUE.md`, `CHECKIN_LOG.md`, `HEADLINES.txt`,
  `DC2_PROTOCOL_2026-09-18.md`, `DC2_FIELD_CHECKLIST.md`, `runs/constrained/`, or tracking freezes.
- Never signal a process you did not start. Read the command line before any kill.
- Never edit `pipeline/io/`, firmware, serial code or `pipeline/clean/common.py`; never modify
  `data/`.

##### 2. Active threads

**A. DC2 identification readiness, slot design (brief 23e)**. STATUS: ready, waiting on the
rehearsal (Thursday 24 or Friday 25 September).

- **Slots.** One slot per person per day. RX2 moves from home (-0.5, 2.5, facing east) to the
  identification spot (2.0, -0.5), facing north, or the fallback (1.5, -0.5) if the 4 m passive
  cable is short. It returns home before that person's tracking.
- **Seat and path.** The operator seat is fixed at (-1.0, 0.5). The path is **line A walked away
  from the TX, `A_fwd`**: (2.5, 0) to (2.5, 5), direction N.
- **F along the path:**

  | link | primary spot | fallback spot |
  |---|---|---|
  | TX-RX2 | 0.981 (0.854 at 0 m) | 0.947 |
  | TX-RX3 | 0.500 | 0.500 |
  | TX-RX1 | 0.000 | 0.000 |

- **Presses fall at every metre, six per pass**, because walk mode closes a pass on its sixth
  press.
- **Blocks.** Day 1: 10 natural passes. Day 2: 5 natural, 5 slow and 5 fast. Odd-numbered
  participants walk slow first. The order is P1 to P6 on day 1, reversed on day 2.
- **Time.** About 48 minutes on day 1 and 60 on day 2.
- **Frozen.** The pre-registration and addendum B, with freeze `runs/IDENTIFICATION_FROZEN_2026-09-23e.json`:

  | file | SHA-256 |
  |---|---|
  | pre-registration | `e5d7acfa31f9006e9703e54dd4dc41f76d33d19b935b3f6c58dca10062479cb3` |
  | addendum B | `47c737cc14e66eb9e776cb7e119b88032675a406e08eaf2dd31481b27e1e8d99` |

- **Scorer.** `id29_dc2_score` scores analyses P1 to P6 once, behind a hash gate, and offers
  `--check-layout`. It has been tested on synthetic data only.
- **Next action:** run the rehearsal per `reports/DC2_ID_REHEARSAL.md`. That includes setting the
  spot once with `pipeline.identify.capture_idpath --set-spot primary` (or `fallback`).

**B. Integrated gait with pace as a gait parameter (brief 23f, IDGP)**. STATUS: CANCELLED by Uzayr
at 19:38, before any compute. Uzayr will give an updated prompt.

- **What exists:**
  - `reports/QUEUE_IDGP.md`, marked cancelled;
  - one line in `reports/CHECKIN_LOG_IDGP.md`;
  - `pipeline/identify/idgp_checkin.py` and `scripts/watchdog_idgp.sh`;
  - **decision 10** in `reports/DECISIONS_ID_2026-09-23.md`, which records Room A reopened for
    that exploratory run.
- **Next action:** read the new prompt. If it changes the scope, append a decision superseding
  decision 10.

**C. Room A identification results.** STATUS: done. All nested, cross-day, six people, chance
16.67 %; the only quotable figures are in `reports/ID_QUOTABLE_2026-09-23.md`.

| result | figure |
|---|---|
| headline, leave one session out | **15.83 %** [10.28, 21.67], p 0.71 |
| cohort curve, 2 to 6 people | at chance throughout: 49.33 / 32.44 / 23.50 / 18.83 / 15.83 |
| S0, oracle speed alone | 32.50 % |
| 2D CNN on Doppler spectrograms, post hoc | 27.22 %, falling to 23.89 [17.22, 31.39] with speed removed |
| recording signature, static levels only | 91.67 to 98.61 % within a day, 20.28 % across days |
| session-ID control | 80.33 % against 33.33 |
| positive controls | direction 94.44, line 72.78, session 80.44, injected rhythm 32.22 |
| CSI cadence | links disagree by a median 0.60 Hz; within-person ICC 0.018 |
| recording ICC | 0.421 |

##### 3. Decisions

**DECIDED by Uzayr**

- The node geometry stays unchanged for tracking and the report.
- The DC2 path went E_col1 (the rule) to E_row1 (a geometry override, 23c), then to line A away
  from the TX with RX2 moved (23e). Line A is current.
- Participants come one at a time.
- RX2 moves beside the TX for identification only.
- The operator seat is fixed.
- Day 2 runs in reversed order.
- Within-day identification is demoted to a confounded label; cross-day P1 is the result.
- The pace blocks are compulsory; in 23e they are on day 2.
- Room A identification was closed (23c), then reopened for IDGP (decision 10), which is now
  cancelled.
- The DC2 PRIMARY and SECONDARY configurations are the 23b freezes, unchanged.

**Written by Claude inside a brief's scope, frozen, never explicitly reviewed by Uzayr**

- Addendum B's P2 uses single-link features and a fixed 2.0 s crop. P6 is single-link on TX-RX3.
- P3 carries notes on the length leak.
- The RX2 spot is locked once any DC2 files exist.

**Forced by the capture tool:** presses at every metre, not only at 0 m and 5 m.

##### 4. Artifacts

All of these are untracked in git; nothing was committed.

- **DC2 sheet and support:**
  - `reports/DC2_ID_PROTOCOL_2026-09-23d.md`, the current sheet;
  - `reports/DC2_ID_FIELD_CARD.md`;
  - `reports/DC2_ID_REHEARSAL.md`;
  - `reports/CAPTURE_INTERFACE_NOTES.md`.
- **Pre-registration:** `reports/PREREG_ID_DC2_2026-09-23.md` and `..._ADDENDUM_B.md`.
- **Record:**
  - `reports/DECISIONS_ID_2026-09-23.md`, decisions 1 to 10;
  - `reports/ID_QUOTABLE_2026-09-23.md`;
  - `reports/IDENTIFICATION_2026-09-18.md`, with sections 23b, 23c and 23e appended;
  - `reports/CLOSING_IDMAX_2026-09-23.md`;
  - `reports/FINDINGS_stageid19.txt` to `id27`.
- **Freezes:** `runs/IDENTIFICATION_FROZEN_2026-09-23b.json` with its `_ADDENDUM`, then `-23c` and
  `-23e`.
- **Code, in `pipeline/identify/`:**
  - the IDMAX engine: `idmax_common.py`, `idmax_eval.py`, `idmax_features.py`;
  - stages `id19` to `id27`, plus `id26b_cnn_diag.py`;
  - `id28_dc2_score.py`, superseded but kept because 23c hashes it;
  - `id29_dc2_score.py`, the current DC2 scorer;
  - `capture_idpath.py`, the DC2 capture wrapper, which drives walk mode without editing
    `pipeline/io/`;
  - `rehearsal_check.py`;
  - `yield_governor.py`.
- **Tests:** `tests/test_idmax_guards.py`, `test_id28_dc2_score.py` and `test_id29_dc2_score.py`.
  The full suite was last at **1221 passed, 8 skipped**.
- **Data products:** the signal bank in `runs/identify/idmax/bank/`, 360 passes; the features in
  `runs/identify/idmax/features/`, seven variants.

##### 5. Already ruled out

- **Moving the nodes for the whole DC2:** it would break tracking and cross-room comparability.
- **Two-press passes:** walk mode indexes six anchors and closes on the sixth press.
- **The torso-contour speed proxy:** r = 0.102 against true speed.
- **Choosing a line by accuracy on Room A:** it was noise three times.
- **Random forests on speed-residualised features:** the test-side residual re-injects oracle speed
  (27.50 against 16.39 shuffled).
- **The old `walk_edge` span:** about half of it is turning and braking; the steady span runs press
  to press.
- **Cadence resolved with oracle speed:** it used oracle speed on 115 of 360 passes.
- **Within-day accuracy as evidence of identity.**
- **Several earlier figures, now superseded:**
  - 66.0 and 50.5 percent;
  - "the gait question is answered YES";
  - 25.8 and 22.2 percent;
  - the realistic-pipeline 31.67 and 30.00 percent;
  - verification AUC 0.684 and EER 0.405.

##### 6. Open loops

- **OPEN: the addendum B erratum.** Its stated amendment times (19:20, 19:35, 19:55) were guessed
  and postdate its own freeze (19:08). The content stands. The erratum must go into the next
  addendum or freeze, because B is hashed.
- **OPEN: `reports/HEADLINES.txt` line 23** still says the gait question was answered "YES". The
  file is shared with tracking, so Uzayr must decide who updates it.
- **OPEN: two feature-code flaws** (noted in the report, section 23e):
  - one cadence shared across links leaks rhythm into "single-link" rows, which voids 23b's
    F_links block as a single-link test;
  - the features carry segment length, and with it pace (25 to 33 percent on PRIMARY's columns,
    58.3 percent on all families).

  Any new analysis should use single-link extraction and fixed-length crops.
- **OPEN: nothing is committed to git.** Branch `fh-live-2026-09-19`. Commit only if Uzayr asks.
- **OPEN: the walk-ratio citation** in the IDGP brief is unverified.


---

# DC2 identification, confirmatory (2026-09-28)

Scored once by `pipeline/identify/id29_dc2_score.py` against the pre-registration and addendum B (SHA-256 e5d7acfa31f9006e..., 47c737cc14e66eb9...). Heads fixed, labels sealed. SECONDARY is post hoc; S0 is a control.

| analysis | accuracy % | 95% interval (participants) | chance % | p | n |
|---|---|---|---|---|---|
| P1 cross-day, PRIMARY (THE RESULT) | 26.67 | [13.33, 36.67] | 16.67 | 0.1518 | 30 |
| P1 cross-day, SECONDARY (post hoc) | 13.33 | [3.33, 26.67] | 16.67 | 0.8531 | 30 |
| P1 cross-day, S0 (control) | 40.0 | [10.0, 73.33] | 16.67 | 0.044 | 30 |
| P2 link TX-RX2 alone, fixed 2 s crop (mean F 0.9814) | 23.33 | [6.67, 40.0] | 16.67 | 0.2707 | 30 |
| P2 link TX-RX3 alone, fixed 2 s crop (mean F 0.5) | 23.33 | [6.67, 43.33] | 16.67 | 0.2557 | 30 |
| P2 link TX-RX1 alone, fixed 2 s crop (mean F 0.0) | 13.33 | [0.0, 33.33] | 16.67 | 0.7512 | 30 |
| P2 link TX-RX2 alone, full length, carries pace (mean F 0.9814) | 10.0 | [3.33, 16.67] | 16.67 | 0.8971 | 30 |
| P2 link TX-RX3 alone, full length, carries pace (mean F 0.5) | 13.33 | [0.0, 33.33] | 16.67 | 0.7572 | 30 |
| P2 link TX-RX1 alone, full length, carries pace (mean F 0.0) | 10.0 | [0.0, 23.33] | 16.67 | 0.8412 | 30 |
| P3 PRIMARY, day 2 slow | 16.67 | [3.33, 33.33] | 16.67 | 0.6124 | 30 |
| P3 PRIMARY, day 2 fast | 26.67 | [13.33, 43.33] | 16.67 | 0.1489 | 30 |
| P3 SECONDARY, day 2 slow | 26.67 | [6.67, 50.08] | 16.67 | 0.0689 | 30 |
| P3 SECONDARY, day 2 fast | 20.0 | [0.0, 46.67] | 16.67 | 0.4326 | 30 |
| P3 S0, day 2 slow | 16.67 | [0.0, 50.0] | 16.67 | 0.8412 | 30 |
| P3 S0, day 2 fast | 16.67 | [0.0, 50.0] | 16.67 | 0.6893 | 30 |
| P4 placement control, identification spot | 33.33 | [0.0, 66.67] | 16.67 | 0.1249 | 60 |
| P4 placement control, home (information for tracking) | 16.67 | [0.0, 50.0] | 16.67 | 1.0 | 60 |
| P5 recording signature, cross-day | 16.67 | [0.0, 50.0] | 16.67 | 1.0 | 30 |
| P5 session-ID (day) control | 84.11 | [80.11, 87.89] | 50.0 | 0.001 | 900 |
| P6 cross-room, TX-RX3 only | 10.0 | [3.33, 16.67] | 16.67 | 0.953 | 30 |
| WITHIN-DAY, ONE SLOT, CONFOUNDED (not a result) | 63.33 | [53.33, 73.33] | 16.67 | 0.002 | 30 |

**P2 geometry ordering**, fixed-length rows (TX-RX2 > TX-RX3 > TX-RX1, TX-RX1 near chance): NOT HELD. Physics: TX-RX1 F 0.0: observed 16.41 Hz against predicted 0.0 Hz (Spearman None); TX-RX2 F 0.9814: observed 18.75 Hz against predicted 19.73 Hz (Spearman 0.744); TX-RX3 F 0.5: observed 16.41 Hz against predicted 10.05 Hz (Spearman 0.276).

**P3 pace.** S0 manipulation check: {'slow': False, 'fast': False}. Verdicts: PRIMARY slow: NOT DECIDABLE: S0's drop interval does not lie above zero; PRIMARY fast: NOT DECIDABLE: S0's drop interval does not lie above zero; SECONDARY slow: NOT DECIDABLE: S0's drop interval does not lie above zero; SECONDARY fast: NOT DECIDABLE: S0's drop interval does not lie above zero.

**P4.** Identification spot: placement NOT distinguishable between people; RX2 static amplitude over the placements {'n_placements': 12, 'mean': 29.126, 'sd': 3.725, 'cv': 0.1279, 'min': 19.674, 'max': 33.221}.


---

# DC2 P1-GP (addendum C), scored 2026-09-28 19:14

Frozen arm G ({'arm': 'G', 'head': 'gb', 'fusion': 'concat', 'form': 'cor', 'scope': 'a', 'margin': '0 or 0.5 s by the day 1 person ICC of the fused cadence', 'training': 'DC2 day 1 natural A_fwd passes only; no Room A model transfers'}), margin 0.0 s.

| row | accuracy % | 95% interval | p | n |
|---|---|---|---|---|
| P1-GP | 30.0 | [13.25, 60.0] | 0.1379 | 30 |
| S0, same passes | 40.0 | [10.0, 73.33] | 0.044 | 30 |

Arm minus S0: -10.0 [np.float64(-43.33), np.float64(20.0)]; check 1 FAILS. Name: gait without pace, not above speed. Pace blocks: NOT DECIDABLE: S0 does not drop on both pace blocks.


---

# DC2 identification, secondary rows P1-REV and P7 (2026-09-28)

Scored once by `pipeline/identify/idsec_dc2_score.py` against addendum 2026-09-24 section 3 (SHA-256 3ca7a0ed30ca8395...) and addendum E (SHA-256 42b7dcd26d6e33e0...), with the frozen id29 features, heads and statistics. Secondary: P1-REV neither replaces nor rescues analysis P1, and a figure pooling A_fwd and A_rev is exploratory.

| row | accuracy % | 95% interval (participants) | chance % | p | n |
|---|---|---|---|---|---|
| P1-REV, A_rev, day 1 natural to day 2 natural, PRIMARY | 20.0 | [0.0, 53.33] | 16.67 | 0.3906 | 30 |
| P1-REV, A_rev, day 1 natural to day 2 natural, SECONDARY (post hoc) | 30.0 | [10.0, 53.33] | 16.67 | 0.031 | 30 |
| P1-REV, A_rev, day 1 natural to day 2 natural, S0 (control) | 50.0 | [26.67, 76.67] | 16.67 | 0.016 | 30 |
| P7, A_fwd, day 1 slow to day 2 slow, PRIMARY | 16.67 | [3.33, 36.67] | 16.67 | 0.5624 | 30 |
| P7, A_fwd, day 1 slow to day 2 slow, S0 (control) | 30.0 | [6.67, 60.0] | 16.67 | 0.1658 | 30 |
| P7, A_fwd, day 1 fast to day 2 fast, PRIMARY | 40.0 | [16.67, 63.33] | 16.67 | 0.0559 | 30 |
| P7, A_fwd, day 1 fast to day 2 fast, S0 (control) | 33.33 | [20.0, 46.67] | 16.67 | 0.0889 | 30 |


---

# DC2 identification, confirmatory and exploratory (2026-09-28)

**Written on 2026-09-28 from 19:34 SAST, read from the clock.** The sections above, headed "DC2
identification, confirmatory", "DC2 P1-GP" and "DC2 identification, secondary rows P1-REV and P7",
are the three scorers' own appended output, written as each ran; this section reports them together
with the physics check and the exploratory menu of the brief of 2026-09-28
(`reports/BRIEF_ID_DC2_scoring_2026-09-28.md`). Participants are "participant P1" to "participant P6"
and analyses "analysis P1" to "analysis P7".

**How it was scored.** The pre-registration and addenda B, C, D and E fix every row. Each scorer ran
exactly once, after tracking's batch had finished, on 2026-09-28: `id29_dc2_score` at 19:12 to 19:13,
`idgp_dc2_score` at 19:14 and `idsec_dc2_score` at 19:15 to 19:17, each committed before its figures
were read (af74d8a, b74d647, 693a851). The data are both DC2 days, 60 recordings, read through the
pre-registered view (48 recordings, `A_fwd` passes only) and the secondary view (36 recordings),
both built from the relabelled source of addendum E, section 6, which gives participant P5's day 2
fast pass 9 its real end press. `data/` was never written.

**Disclosed beside every cross-day figure below** (addendum E, sections 2 to 7):

- The natural block started later on day 2 than on day 1 by 1 h 10 min (participant P1), 2 h 53 min
  (P2), 15 min (P3) and 7 min (P5), and earlier by 29 min (P4) and 5 h 25 min (P6); participants P3
  and P5 were recorded at about the same time of day on both days.
- Participant P3's day 1 identification followed that participant's tracking, so participant P3's two
  days are not matched for warm-up.
- The day 1 natural blocks of participants P2 and P3, which are training data for analyses P1, P2,
  P3, P5 and P1-GP, were recorded with RX2 in a low state, 8 to 13 dB below its normal level at the
  spot.
- The levels shifted between the days: RX3 reads about 4 dB lower on day 2 for all six participants,
  and RX2 at the spot 3.6 to 11.8 dB lower for five of them.
- Participant P5's day 2 fast `A_fwd` pass 9 was relabelled before any figure (2.86 s to 3.70 s); it
  enters analysis P3 (fast), P1-GP's fast block and analysis P7 (fast).

## 1. Confirmatory, exactly as pre-registered

Accuracy in percent; 95 percent bootstrap over participants; p is the within-day permutation p (1000
draws); chance 16.67 unless stated.

**Analyses P1 to P6 (addendum B), `runs/identify/dc2/results.json`.**

| analysis | accuracy % | 95% interval | chance % | p | n |
|---|---|---|---|---|---|
| P1 cross-day, PRIMARY (THE RESULT) | 26.67 | [13.33, 36.67] | 16.67 | 0.152 | 30 |
| P1 cross-day, SECONDARY (post hoc) | 13.33 | [3.33, 26.67] | 16.67 | 0.853 | 30 |
| P1 cross-day, S0 (control) | 40.00 | [10.00, 73.33] | 16.67 | 0.044 | 30 |
| P2 TX-RX2 alone, fixed 2 s crop (mean F 0.981) | 23.33 | [6.67, 40.00] | 16.67 | 0.271 | 30 |
| P2 TX-RX3 alone, fixed 2 s crop (mean F 0.500) | 23.33 | [6.67, 43.33] | 16.67 | 0.256 | 30 |
| P2 TX-RX1 alone, fixed 2 s crop (mean F 0.000) | 13.33 | [0.00, 33.33] | 16.67 | 0.751 | 30 |
| P2 TX-RX2 alone, full length, carries pace | 10.00 | [3.33, 16.67] | 16.67 | 0.897 | 30 |
| P2 TX-RX3 alone, full length, carries pace | 13.33 | [0.00, 33.33] | 16.67 | 0.757 | 30 |
| P2 TX-RX1 alone, full length, carries pace | 10.00 | [0.00, 23.33] | 16.67 | 0.841 | 30 |
| P3 PRIMARY, day 2 slow | 16.67 | [3.33, 33.33] | 16.67 | 0.612 | 30 |
| P3 PRIMARY, day 2 fast | 26.67 | [13.33, 43.33] | 16.67 | 0.149 | 30 |
| P3 SECONDARY, day 2 slow | 26.67 | [6.67, 50.08] | 16.67 | 0.069 | 30 |
| P3 SECONDARY, day 2 fast | 20.00 | [0.00, 46.67] | 16.67 | 0.433 | 30 |
| P3 S0, day 2 slow | 16.67 | [0.00, 50.00] | 16.67 | 0.841 | 30 |
| P3 S0, day 2 fast | 16.67 | [0.00, 50.00] | 16.67 | 0.689 | 30 |
| P4 placement control, identification spot | 33.33 | [0.00, 66.67] | 16.67 | 0.125 | 60 |
| P4 placement control, home (information for tracking) | 16.67 | [0.00, 50.00] | 16.67 | 1.000 | 60 |
| P5 recording signature, cross-day | 16.67 | [0.00, 50.00] | 16.67 | 1.000 | 30 |
| P5 session-ID (day) control | 84.11 | [80.11, 87.89] | 50.00 | 0.001 | 900 |
| P6 cross-room, TX-RX3 only | 10.00 | [3.33, 16.67] | 16.67 | 0.953 | 30 |
| WITHIN-DAY, ONE SLOT, CONFOUNDED (not a result) | 63.33 | [53.33, 73.33] | 16.67 | 0.002 | 30 |

- **Analysis P1.** PRIMARY's interval contains chance. Among analysis P1's rows, S0, the speed-only
  control, is the only one whose permutation p falls below 0.05, and its interval also reaches below
  chance.
- **Analysis P2's ordering is NOT HELD.** On the fixed-length crops TX-RX2 and TX-RX3 tie at 23.33,
  so TX-RX2 does not exceed TX-RX3; TX-RX1 is near chance, as predicted. The registered physics row:
  TX-RX2's median torso contour is 18.75 Hz against a predicted 2 F v / lambda of 19.73 Hz, with a
  Spearman correlation of 0.744 across passes; TX-RX3's is 16.41 Hz against 10.05 Hz (0.276); TX-RX1's
  is 16.41 Hz against a prediction of 0.
- **Analysis P3 is NOT DECIDABLE for every configuration.** Its manipulation check needs S0's drop
  interval above zero, and S0 drops 23.33 points on both pace blocks with intervals of [-6.67, 60.00]
  (slow) and [-33.42, 73.33] (fast). PRIMARY drops 10.00 [-16.67, 33.33] (slow) and 0.00 [-10.00,
  6.67] (fast); SECONDARY -13.33 [-36.67, 6.67] and -6.67 [-23.33, 6.67].
- **Analysis P4.** Placement at the spot is not distinguishable between people (the interval reaches
  chance). RX2's mean static amplitude over the twelve placements is 29.13 (SD 3.73, CV 0.128,
  range 19.67 to 33.22).
- **Analysis P5.** The recording signature is at chance across days, and the day itself is read from
  PRIMARY's features at 84.11 percent: the two days differ systematically, as the level shift of
  addendum E, section 5, would make them.
- **Analysis P6.** Room A's TX-RX3 features do not transfer.

**P1-GP (addendum C), `runs/identify/dc2/idgp/results.json`.** The frozen arm G (gradient boosting on
gait features without pace), margin 0 s by the day 1 ICC rule.

| row | value |
|---|---|
| P1-GP, day 1 natural to day 2 natural | 30.00 [13.25, 60.00], p 0.138, n 30 |
| S0 on the same passes | 40.00 [10.00, 73.33], p 0.044, n 30 |
| Integrity check 1, P1-GP minus S0 | -10.00 [-43.33, 20.00]: FAILS |
| Integrity check 2, share of the gain S0 accounts for | 1.75 (S0 exceeds the arm) |
| Integrity check 3, lowest-d' third of pairs, chance 50 | arm 50.0, S0 56.0, n 50 (see the note below) |
| Integrity check 4, the name | "gait without pace, not above speed" |
| Pace blocks, day 2 slow | arm 16.67 [3.33, 30.00], S0 16.67 [0.00, 50.00]; arm drop 13.33 [-3.33, 33.33] |
| Pace blocks, day 2 fast | arm 26.67 [6.67, 50.00], S0 16.67 [0.00, 50.00]; arm drop 3.33 [-26.67, 33.33] |
| Pace blocks, arm minus S0 on both (n 60) | 5.00 [-16.67, 31.67]; reading: NOT DECIDABLE (S0 does not drop on both blocks) |
| MULTI-PASS, one decision per participant per block (6 each) | natural: arm 50.00, S0 33.33; slow: 33.33 and 16.67; fast: 33.33 and 16.67 |

**A note on integrity check 3, found after scoring.** The frozen head,
`HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=3)`, keeps scikit-learn's
default minimum of 20 samples per leaf, so it cannot split fewer than 40 training passes and then
predicts one class for every pass. Check 3 fits each pair on its 20 day 1 passes, so the arm's 50.0
is chance by construction and says nothing about gait. The other P1-GP rows train on 60 passes and
are unaffected. The scorer's appended text above prints two numbers as `np.float64(...)`, a formatting
artefact of the frozen code; the values are those in the table.

**Secondary rows P1-REV and P7 (addendum 2026-09-24), `runs/identify/dc2/idsec/results.json`.**

| row | accuracy % | 95% interval | p | n |
|---|---|---|---|---|
| P1-REV, `A_rev`, PRIMARY | 20.00 | [0.00, 53.33] | 0.391 | 30 |
| P1-REV, `A_rev`, SECONDARY (post hoc) | 30.00 | [10.00, 53.33] | 0.031 | 30 |
| P1-REV, `A_rev`, S0 (control) | 50.00 | [26.67, 76.67] | 0.016 | 30 |
| P7, day 1 slow to day 2 slow, PRIMARY | 16.67 | [3.33, 36.67] | 0.562 | 30 |
| P7, day 1 slow to day 2 slow, S0 | 30.00 | [6.67, 60.00] | 0.166 | 30 |
| P7, day 1 fast to day 2 fast, PRIMARY | 40.00 | [16.67, 63.33] | 0.056 | 30 |
| P7, day 1 fast to day 2 fast, S0 | 33.33 | [20.00, 46.67] | 0.089 | 30 |

P1-REV neither replaces nor rescues analysis P1. In P7 the fast row's PRIMARY interval starts at chance
(16.67) and its permutation p is 0.056; the slow row is at chance.

## 2. The physics check (descriptive, identity-blind), beside analysis P2

`pipeline/identify/id_dc2_physics.py`, `runs/identify/dc2/physics/results.json`, commit c459941. Natural
`A_fwd` passes of the 12 participant-days, 90 passes.

| link | mean F | 10 to 40 Hz energy over the empty room: participant-days above x2 | median ratio (range) | along-walk trend: F predicts | observed raw | F-corrected |
|---|---|---|---|---|---|---|
| TX-RX2 | 0.984 (0.854 to 0.998) | 12 of 12 | 6.67 (3.41 to 33.63) | +0.073 | +0.411 | +0.360 |
| TX-RX3 | 0.499 (0.18 to 0.82) | 9 of 12 | 3.03 (1.70 to 5.82) | +1.406 | +0.008 | -1.589 |
| TX-RX1 | 0.000 | 12 of 12 | 3.29 (2.03 to 6.40) | none | +0.076 | masked |

**The question, answered plainly: no, not as posed.** TX-RX2 beside the TX does show gait Doppler
well above its floor, and the highest ratio of the three links in 10 of the 12 participant-days
(TX-RX1 is higher for participants P4 and P6 on day 1), but TX-RX1, whose F is zero on line A, also
exceeds twice its floor in all 12, and TX-RX3 in 9. The walker walks on TX-RX1's line of sight,
where the bistatic path length does not change, yet the body blocks and scatters around that line and
modulates it, so the energy test does not separate the links by geometry. What does follow the geometry is the frequency: TX-RX2's torso contour tracks
2 F v / lambda from pass to pass (analysis P2's physics row, Spearman 0.744), and TX-RX3's does not
(0.276). The along-walk trend fails on TX-RX3 exactly as it did on Room A (flat where F predicts a
rise, and the correction creates a trend), and on TX-RX2 it rises more than F predicts, as the
walker's acceleration from a standing start would also make it.

## 3. EXPLORATORY: the fixed menu, both directions, no arm selected

`pipeline/identify/id_dc2_explore.py`, `runs/identify/dc2/explore/results.json`, commit df67367.
**Every row here is EXPLORATORY and replaces no confirmatory row.** No arm is selected, because with
two days any selection is selection on the test day.

**Anchors.** Day 1 to day 2 reproduces six committed confirmatory rows exactly (analysis P1's PRIMARY
26.67 and S0 40.00, analysis P2's TX-RX2 rows 10.00 and 23.33, P1-GP 30.00 and its S0 40.00), so the
exploratory pipeline is the confirmatory one.

**Arm G's head below 40 training passes.** For the reason in the note on check 3, every G cell
trained on fewer than 40 passes predicts one class and reads exactly chance by construction. Those
cells are marked "constant" below and carry no evidence: every G cell trained on day 2 (30 natural
passes), except both directions for training (60), and the cohort cells at k = 2 and 3 trained on
day 1.

| arm | day 1 to day 2 | day 2 to day 1 |
|---|---|---|
| PRIMARY, all links (reference) | 26.67 [13.33, 36.67], p 0.152 | 23.33 [10.00, 40.00], p 0.154 |
| S0 (reference) | 40.00 [10.00, 73.33], p 0.044 | 50.00 [25.00, 76.67], p 0.006 |
| G (reference) | 30.00 [13.25, 60.00], p 0.138 | 16.67, constant |
| TX-RX2 alone, PRIMARY, full length | 10.00 [3.33, 16.67] | 16.67 [5.00, 31.67] |
| TX-RX2 alone, PRIMARY, fixed 2 s crop | 23.33 [6.67, 40.00] | 30.00 [16.67, 38.33], p 0.057 |
| TX-RX2 alone, G | 30.00 [10.00, 53.33], p 0.127 | 16.67, constant |
| GP (G plus pace), S0 beside it | 26.67 [13.25, 50.00]; S0 40.00 | 16.67, constant; S0 50.00 |
| GP check 1, GP minus S0 | -13.33 [-46.67, 16.67]: fails | -33.33 [-75.00, 11.71]: fails |
| GP check 2 | speed only 40.00, speed removed (G) 30.00 | speed only 50.00, speed removed 16.67 (constant) |
| GP check 4, the name | "speed comparison" | "speed comparison" |
| GP pace blocks | NOT DECIDABLE; S0 drops 23.33 on both | NOT DECIDABLE; S0 drops 33.33 [11.67, 56.67] (slow) and 26.67 [-23.33, 63.33] (fast) |
| Block voting, PRIMARY (6 and 12 decisions) | 16.67 (single pass 26.67) | 16.67 (single pass 23.33) |
| Block voting, G | 50.00 (single pass 30.00) | 16.67, constant |
| Block voting, S0 | 33.33 (single pass 40.00) | 58.33 (single pass 50.00) |
| Both directions for training, PRIMARY | 30.00 [20.00, 43.33], p 0.093 (A_fwd only 26.67) | 21.67 [10.00, 33.33] (23.33) |
| Both directions for training, G | 26.67 [6.67, 56.67] (30.00) | 31.67 [20.00, 43.33], p 0.054 (constant) |
| Both directions for training, S0 | 40.00 [10.00, 73.33] (40.00) | 45.00 [20.00, 71.67], p 0.019 (50.00) |
| PRIMARY, RX2 level removed per recording | 20.00 [6.67, 33.33] (unchanged 26.67) | 25.00 [11.67, 38.33] (unchanged 23.33) |

Block voting sums temperature-calibrated log-probabilities over each 5-pass block, one temperature
per model and direction fitted on the training day's out-of-fold probabilities. In the reverse
direction the test day has two blocks per participant, so 12 decisions.

**Cohort curves**, mean accuracy over every subset of k participants (chance 100/k):

| k (subsets) | chance | PRIMARY, d1 to d2 | G, d1 to d2 | S0, d1 to d2 | PRIMARY, d2 to d1 | S0, d2 to d1 |
|---|---|---|---|---|---|---|
| 2 (15) | 50.00 | 58.00 | 50.00, constant | 72.67 | 52.67 | 78.33 |
| 3 (20) | 33.33 | 41.00 | 33.33, constant | 59.67 | 38.33 | 65.67 |
| 4 (15) | 25.00 | 32.00 | 34.33 | 51.00 | 32.17 | 58.17 |
| 5 (6) | 20.00 | 26.00 | 30.00 | 44.67 | 24.33 | 53.33 |
| 6 (1) | 16.67 | 26.67 | 30.00 | 40.00 | 23.33 | 50.00 |

G in the reverse direction is constant at every k and is left out.

**Figures** (`runs/identify/dc2/explore/figures/`):

- `fig_spectrograms.png`: conditioned spectrograms of one natural `A_fwd` pass per participant and
  day on TX-RX2 and TX-RX3, chosen by the median-duration rule fixed before plotting (the chosen
  passes are listed in `figures.json`);
- `fig_p1_confusion.png`: analysis P1's confusion matrices for PRIMARY, SECONDARY and S0, re-fitted
  with the frozen code (each accuracy equals the committed one);
- `fig_p2_links_vs_F.png`: analysis P2's per-link accuracies against mean F;
- `fig_p3_pace_drop.png`: analysis P3's pace drops against S0.

## 4. What DC2 decided

On geometry, DC2 decided against the pre-registered prediction of analysis P2: moving the
identification receiver beside the transmitter, where the projected factor is near one along the
whole walk, gave a Doppler signal whose frequency follows the bistatic physics (Spearman 0.744 against
2 F v / lambda, and the highest energy ratio in 10 of 12 participant-days), but it did not order identification
accuracy by geometry, since TX-RX2 and TX-RX3 tie at 23.33 percent on fixed-length crops and every
fixed-length per-link interval contains chance. On gait against pace, DC2 could not run its planned test, because
analysis P3's manipulation check failed: speed from the presses did not lose accuracy reliably when
people walked slow or fast, so no gait-against-speed verdict is available; wherever gait and pace
met on the same passes, pace was at least as good, since S0 reached 40.00 percent on analysis P1's
passes against PRIMARY's 26.67 and P1-GP's 30.00, P1-GP failed its first integrity check and is
named "gait without pace, not above speed", the exploratory GP arm is a "speed comparison" in both
directions, and the pace-matched analysis P7 leaves PRIMARY at chance on slow walks and at 40.00
percent (p 0.056) on fast ones. The thesis may therefore claim a pre-registered, twice-replicated
negative for cross-day gait identification from Wi-Fi CSI on this rig and cohort (Room A 15.83
percent, DC2 26.67 percent with an interval containing chance, against 16.67), the finding that walk
timing from the presses carries more identity across days than any gait representation built here
(40.00 and 50.00 percent across DC2's days), and the physical result that a receiver beside the
transmitter sees torso Doppler that tracks the bistatic prediction; it may not claim gait
identification, integrated gait, or that better geometry improves identification.
