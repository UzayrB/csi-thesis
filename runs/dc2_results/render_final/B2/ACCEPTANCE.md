# Render of the FINAL tracker on B2: acceptance (measured results only)

Rules: `reports/RENDER_RULES.md`. Model: FINAL, corrected readers, re-selected decode (relgateU+abstain+a2w0.25). Display head: the final DISP_END (pd_dispend), trained on A1+A2+B1.
Every walk's committed line and lock equal the corrected decode (`CR.relgateU`): committed 120/120, lock 120/120.

| check | holds |
|---|---|
| decode_equality (committed and lock equal the corrected decode) | yes |
| rule 1 / 1a (the lock is final; at most one switch; never back) | yes |
| rule 1a (no switch in the final 1.5 m; persistence) | yes |
| rule 1a (switch decisions and targets causal) | yes |
| rule 1a (slides on their segments) | yes |
| rule 1b (end text is the committed decision) | yes |
| rule 2 (nothing projected: every frame decoded or between two decodes) | yes |
| rule 2a (anchor frames on the anchor segment) | yes |
| rule 5 (drawn-window causal bound <= 0) | yes |
| rule 5 (evidence causal bound <= 0) | yes |
| rule 5 (no frame without a dot inside a walk) | yes |
| rule 5 (frames without a dot, whole video) | yes |
| rule 6 / V2 (dot and marker leave together) | yes |
| rule 6 (no stall the decoder does not account for) | yes |
| V1 (2.0 s latency) | yes |
| V3 (lock offset one constant, 2.0 s) | yes |
| V4 (no dwell footage) | yes |
| V5 (dot phase 0.50) | yes |

**All checks: PASS.**

## Rule 5, the computed quantities

- jumps over 0.5 m: 125, of which at the lock 119 and at a switch 0;
- frames without a dot: 0 of 21607 (the contract: 0); inside walks 0 of 7860;
- the drawn-window causal bound: -1.376 s (must be at or below 0);
- the evidence causal bound: -1.376 s (must be at or below 0).

## Rule 4: two numbers, never added

- decoded accuracy (the dot against where the walker was at the moment the decoder names), within 0.5 m: mean over walks 1.9 percent
- on-screen tracking (against the delayed marker, the anchor segment excluded), within 0.5 m: mean over walks 48.9 percent
- display offset (how far the walker moves during the lag): median over walks 1.26 m

Switches (arm C): 1 (wrong to right 0, right to wrong 0, wrong to wrong 1); the drawn line ends on the committed line on 89 of 120 walks.

Committed correct: 93.33 percent; lock correct: 72.50 percent (120 walks; these equal the corrected decode, they are not a new measurement).

## Definitions note (added 16:22, 29 Sep)

**The "decoded accuracy" above uses f3 and f4's inherited definition:** the dot against where the walker
was 1.0 s before each frame. It dates from before the 2.0 s delayed timeline. Under V1 the dot at frame
time x depicts the moment x - 2.0 s. So this figure compares the dot with a moment 1 s LATER than the
one it depicts, and it is not the decoder's accuracy. f4's accepted demonstration reports 1.94 percent by
the same definition. It is kept for comparability, and should not be quoted.

**The meaningful figures under V1:**
- **the on-screen tracking,** the dot against the delayed marker, which shows exactly the depicted moment;
- **the decoder's resolution** in `reports/MODEL_FINAL_TRACKING_CORRECTED.md` section 5: the drawn
  dot's error on walks whose lock is correct.

The walker's travel during the 2.0 s delay, about 2.6 m (f4), is the display offset of rule 4, and is
never added to either.
