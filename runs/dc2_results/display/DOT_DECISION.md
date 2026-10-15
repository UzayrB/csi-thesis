# The dot: K1g adopted by Uzayr's decision, 1 October 2026, 00:02 SAST

**The decision, verbatim:** "The dot: adopt K1g (look-ahead 1, glide off the entry), chosen on the rotation
figures in DOT_CHOICE.json. Record it as my decision on development data, taken after the pre-registered rule
kept K0." (`reports/BRIEF_LIVE_APP_3_2026-10-01.md`, item 1.)

**What the pre-registered rule had chosen:** K0, no change (`rule/DOT_PREREG.md`, `DOT_CHOICE.json`, 30 Sep
20:53).
- **Why:** every candidate lowered the error but raised the share of frames with the dot ahead of the truth,
  and the rule admitted no rise.

**What K1g is:**
- **The look-ahead:** the drawn path after the lock reads 1 window past each step, within the locked line.
- **The glide:** over the anchor span, the dot glides from the locked line's entry to the first decoded
  frame's position.
- **What it leaves alone:** no lock and no committed line (identical to K0 on all 360 rotation walks).
- **Causal:** the minimum margin is 0.500 s.

**Its development figures** (the rotations, correct-lock walks, from the press; weighted B1 x2, A2, A1):

| | K0 | K1g |
|---|---|---|
| median error | 0.351 m | 0.292 m (-17 %) |
| ahead share | 0.314 | 0.326 (+1.2 points) |

**The status of this choice:** taken on development data after the rule kept K0. It is a decision, not the
rule's outcome, and is reported as such. A3 and B2 had not been replayed with any candidate before it.
