# PRE-REGISTRATION: three switching arms, the winner rendered. Batch 2026-09-23f

**Written ~18:00, before the stage (`e2_switch`) existed and before any number for arms B or C.** The
operator's instruction and selection rule are stored verbatim in the BRIEF, INSTRUCTION 6; the rule
was "fixed now before any numbers exist". This file only fixes how each clause is READ.

## 1. The arms (all: 1.5 m proximity, persistence of two consecutive checks, radio to t + 2.0 s only)

| arm | switches | no switch in the final | theta |
|---|---|---|---|
| **A** (current) | at most 1 | 1.0 m | chosen per arm |
| **B** (operator's proposal) | at most 2 | 1.5 m | chosen per arm |
| **C** (separates the cutoff) | at most 1 | 1.5 m | chosen per arm |

**theta.** The instruction says both "the 2-nat margin" and "Theta chosen on the selection folds ...
per arm". theta IS the margin. Read: **theta is chosen per arm on `s01_to_s02` and `s02_to_s01` only,
from {0.5, 1.0, 1.5, 2.0, 3.0}**, by `e1_switch`'s rule (the largest selection-fold mean
time-on-correct delta among thetas whose selection-fold wrong-to-right exceeds right-to-wrong, ties to
the larger theta). **Every arm is also reported at theta = 2.0**, and a chosen theta other than 2.0 is
stated beside the result.

## 2. The second switch (arm B)

- It is evaluated only on checks AFTER the first switch's slide has finished (x >= x_1 + 0.5 s), with
  a fresh persistence streak, so the earliest second switch is 1.0 s after the first.
- Its target must be the decoder's best line, leading the CURRENT drawn line by more than theta at two
  consecutive checks, within 1.5 m of the dot, and **never a line already drawn in the walk** (the lock
  or the first switch's line). A best line that was already drawn does not qualify and resets the streak.
- "No switch in the final 1.5 m" reads the drawn dot on its CURRENT line: once the dot has been within
  the final zone of the line it is on, no further switch.
- Slide frames (the 0.5 s between lines) are never used for the final-zone test.

## 3. The quantities

| quantity | definition |
|---|---|
| time on correct line | as `e1_switch`: frames from the lock to the end press + 2.0 s whose named line is true; the named line changes at each switch frame |
| W2R, R2W, W2W | per switch EVENT, pooled over nine pairings, integers |
| **end-on-committed agreement** | walks (of 1080) whose line drawn at walk end equals the shipped committed decision (`d4_headline` rows_veto). **Text contradicts the dot** = 1080 minus that |
| switches per walk | switch events over walks, and the distribution 0 / 1 / 2 |
| jumps over 1.5 m | switch events whose slide spans more than 1.5 m |
| time of each switch | median seconds after the lock, first and second switch separately |
| **estimator disagreement at the lock** | walks where the display lock differs from the switch scorer's best line computed at the lock frame from the radio finished by then (same scorer, same shipped start term) |

## 4. The selection rule, as read

1. **Qualify:** the nine-pairing mean paired time-on-correct delta is above zero AND the held-out
   seven's 95 percent paired interval is entirely above zero; AND pooled W2R > R2W.
2. **Pick** the highest end-on-committed agreement (a count of walks).
3. **"Within one walk per pairing"** = within 9 walks of the top count (one per pairing, nine
   pairings). Among the arms in that band: fewer switch events, then fewer jumps over 1.5 m.
4. **No arm qualifies:** render lock-final (no switching; the end text stays the shipped decision),
   rule 1a is withdrawn, and the reason is reported.

## 5. Checks that void the run

Arm A at every theta must reproduce `e1_switch`'s `radius_t{theta}` decisions on 1080 of 1080 walks
(the generalised code must equal the code the rendered variant was measured with). The lock must equal
`d6_lock_commit` on every pass. Every switch causal on both bounds.

## 6. The investigation, and what ACCEPTANCE may say

The operator asked ACCEPTANCE and STATE to say that "most switches reconcile the two estimators rather
than react to new mid-walk evidence". **That sentence is written only if the data says so:** a switch
counts as RECONCILING when its target is already the scorer's best line at the lock frame, and as NEW
EVIDENCE otherwise. If reconciling switches are not the majority for the chosen arm, ACCEPTANCE says
what was measured instead. The disagreement rate is printed beside it either way.
