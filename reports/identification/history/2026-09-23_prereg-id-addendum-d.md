# Addendum D to `reports/PREREG_ID_2026-09-23.md`: R6 is UNCHANGED, and why

**Written 2026-09-23 04:02 SAST during the tracking gate, on synthetic data only. No CSI has been
read and no identification number exists.** This addendum changes nothing. It records a rule change
that was written, measured and then rejected, and a measured limitation of R6 that the report must
carry.

---

## 1. A strengthening of R6 was tried and rejected

R6 residualises every feature on oracle pass speed, fitted on the training side, and asks whether
the arm still beats the permutation null. The pre-registered regression is **linear**.

**The concern.** A feature that encodes speed NON-LINEARLY should survive a linear residualisation
and be reported as gait. On synthetic arms where the answer was known, that concern was real: an
arm built from speed squared and exp(speed) fell only from 25.0 percent to 18.8 against a 16.7
chance line, where a linear pace arm fell from 27.5 to 11.2.

**The proposed fix** was to regress on a quadratic, `[1, s, s^2]`, which is strictly more of the
speed structure and looked like an obvious improvement.

**It measurably made the test WORSE.** Over 12 seeds:

| residualisation | non-linear PACE arm, should FAIL | genuine GAIT arm, should PASS |
|---|---|---|
| **`[1, s]`, as registered** | **18.0 +- 3.1** | 43.3 +- 3.8 |
| `[1, s, s^2]` | **26.4 +- 4.1** | 43.6 +- 3.9 |

Chance is 16.7. Regressing out more speed structure moved the pace arm from the chance line to
nearly ten points above it, which is the opposite of what the change was for.

**The mechanism, because it generalises.** A harder residualisation does not remove the identity
information that speed carries. It only shrinks the SCALE of what remains, and the classifier
standardises its inputs, which restores that scale and lets the residual higher-order speed
dependence be read as identity again. More aggressive nuisance removal is not automatically a
stronger control.

**R6 therefore stays exactly as pre-registered, linear.** The proposal is recorded here as
rejected, with the numbers, rather than quietly dropped.

## 2. A measured limitation of R6 that the report must carry

**Residualising on speed cannot fully remove identity when speed and identity are correlated at
all.** On this cohort they are: speed separability is 0.51, so pace is a weak but non-zero
identifier. Whatever order the regression uses, a residual non-linear dependence on speed remains
and it still tracks identity. R6 is a strong test, not a complete one.

**The speed probe is the sharper instrument, and by a wide margin.** The same synthetic arms, same
12 seeds:

| arm | residualised accuracy | **speed-probe R squared** |
|---|---|---|
| non-linear pace arm | 18.0 (marginal, near chance) | **0.996** |
| genuine gait arm | 43.3 (clearly above) | **0.172** |

The residualisation separates these two by a margin that its own spread nearly covers. The probe
separates them by 0.8 of an R squared. **The probe is already clause 3 of R6 as registered**, and
it is reported for every arm in `id14`.

**What this changes: nothing in the decision rule.** R6's verdict stays "the speed-residualised
version beats the 95th percentile of the permutation null on at least 5 of 9 pairings". No
threshold is invented for the probe after the fact, because choosing a threshold once the real
numbers exist is exactly the post-hoc move this project refuses.

**What it changes in the reporting, fixed now.** For every arm, `id14` reports the residualised
accuracy, the residualisation drop, the speed-probe R squared and the agreement with S0 together,
and the report interprets them together. **An arm that passes R6 while showing a speed-probe R
squared near 1 and high agreement with the oracle speed control is reported as pace-carrying
despite passing R6**, with all four numbers shown, so a reader can see the tension rather than
being handed a verdict.

## 3. What does not change

R1 to R5 and R7 are untouched. The arms, the heads, the nine pairings, the speed policy and the
three outcomes are untouched. R6's decision rule is untouched.
