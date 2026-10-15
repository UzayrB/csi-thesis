# INVESTIGATION: how switching works, and what it is actually doing. Batch 2026-09-23f

The operator asked: "How is the switching happening and how does my model know to switch, does this
need to be investigated?", then "Investigate". Every figure is from `runs/constrained/fh/e2_switch/`
(VALID: the lock equals `d6_lock_commit` on 1080 of 1080 passes; arm A reproduces `e1_switch` at every
theta). Nine cross-day pairings, 1080 walks. **This is a diagnosis. Nothing here ships.**

## 1. Two estimators, not one

| | the LOCK (what the dot is drawn on) | the SWITCH SCORER (what a switch follows) |
|---|---|---|
| decoder | the DISPLAY decode: speed cap (`sd_scale` 4.5, 0.8 m per window), the end-of-walk display head flattened 0.50, A2 start term | each line's evidence total from a restricted decode on the DECISION emissions (no cap), prior withheld, the SHIPPED start term (A2 + `a_veto_1.0`): the committed decision's own estimator |
| read | the line of the free display path at press + 2.0 s | every 0.5 s from then on, on the radio finished by the frame |

Nothing is learned for switching. The display switches when the scorer's best line leads the drawn
line by more than 2 nats at two consecutive checks, within 1.5 m of the dot, and not in the final
zone. Substitution (another participant's radio) changes 82 percent of the decisions it could: the
switch follows the radio.

## 2. The two estimators disagree at the lock on a third of walks, on the SAME radio

The scorer read on exactly the lock's windows (the first switch check sees the same radio):

| | display lock | scorer on the lock's radio |
|---|---|---|
| **disagree** | **363 of 1080 walks (33.6 percent)**; per pairing 20.0 to 43.3 percent (20.8 on the demo pairing) | |
| right, pooled | 493 (45.6%) | **538 (49.8%)** |
| right, median over pairings | 53.33 | **57.50** |
| **scorer minus lock, paired** | | **+4.17 [0.93, 8.33]; held-out seven +5.83 [2.74, 10.24]** |
| equals the committed decision | 598 (55.4%) | 694 (64.3%) |
| E_col1 / E_col5 / E_row1 / E_row5 (of 54) | 20 / 32 / 10 / 23 | 19 / 32 / 13 / 22 |

On the 363 disagreeing walks: the lock is right on 81, the scorer on 126, neither on 156.

**Stated plainly: the lock is drawn from the "edge-safe" display decoder because lock arms that replaced
it collapsed the edge lines (t7, t9). Measured here, on the same radio at the lock, the scorer is NOT
worse on the edges (net +1 walk) and is better overall.** This is an after-the-fact observation, not a
result: the lock is a quoted figure and a lock arm would need its own pre-registration and the full
ship rule. It is the most useful lead this investigation produced.

## 3. What a switch actually is

| arm C (rendered), 95 switches | |
|---|---|
| median time after the lock | 2.0 s |
| **reconciling** (target = the scorer's line on the lock's own radio) | **71 (74.7 percent)** |
| new evidence (target emerged after the lock) | 24 |
| wrong-to-right: reconciling / new evidence | 30 / 7 |
| right-to-wrong: reconciling / new evidence | 9 / 1 |
| target = the final committed line | 57 (60.0 percent) |

**Most switches reconcile the two estimators rather than react to new mid-walk evidence.** The switch
is mostly the final-answer estimator overriding the display lock one to two seconds late, which is
why it helps a little and why its wrong-to-wrong share is large.

## 4. Why the dot and the text still disagree on 40 percent of walks

The dot ends on the committed line on 598 walks under lock-final and 647 under arm C (+49). The text
contradicts the dot on 433. The reason is §2: the lock disagrees with the committed decision on 482
walks, and **280 of the 363 walks where the two estimators disagree at the lock never switch**, blocked by
the 1.5 m proximity rule, the persistence rule or the final zone. More switches do not close it: arm B's
second switch fired on 2 walks of 1080.

## 5. What this means, for the operator

- Switching as rendered is small (+1.54 time on correct, 95 walks of 1080) and honest, but it is mostly
  a late correction of a lock drawn from a different estimator.
- **The lever is the lock, not the switch.** A lock read from the scorer on the same radio is, on this
  measurement, +4.17 better paired with no edge loss. It is not proposed here; it would be a pre-registered
  lock arm (the lock is quoted), measured under the full ship rule with (f) as amended, and the
  display's continuity after the lock would need re-checking because the dot's path would come from
  the scorer's line.
- Not measured: which component of the display decode (the cap, the display head, the missing veto
  term) drives the disagreement. An ablation over those three would answer it.
