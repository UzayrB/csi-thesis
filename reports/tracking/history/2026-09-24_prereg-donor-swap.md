# PRE-REGISTRATION: the donor swap, 2026-09-24

Written 2026-09-24 17:45 SAST (clock read), before any donor-swap number exists. **Diagnostic**: it
ships nothing and changes no model, decision or figure. Code: `pipeline/constrained/f5_donor.py`.

## The question

The operator asked, again, whether the tracker reads the radio or is a motion model in disguise.
The existing evidence is the per-walk substitution flag in `d4_headline`'s rows. Swapping in the next
recording's emissions at the same window indices changes the committed line on 72.8 percent of the
1080 walks. That flag was read before this was written. It shows the answer depends on the radio. It
does not show that the answer FOLLOWS the radio, because the swapped windows are not aligned to any one
walk.

## The test

For every walk X on the nine cross-day pairings, the shipped committed decision (A2 at 0.5 plus
`a_veto_1.0`, exactly as `d4_headline` takes it) is taken twice:

1. **Own:** on X's own radio. This must reproduce `d4_headline`'s `rows_veto.json` walk for walk, or
   the run is VOID.
2. **Donor:** on a DONOR's radio. The donor Y is a walk by the NEXT participant (sorted order, wrapping
   round) in the same test session, on a DIFFERENT line from X. Among those, Y is the walk closest to X
   in press-to-press duration, with ties going to the lowest pass id.

Every CSI-derived input X's decision reads is replaced by Y's:
- the five-head pool emissions and the gate energy, from X's first window for the length of Y's walk
  plus 8 windows (4 s, so the causal exit sees Y's own stop), capped at X's next walk;
- the pre-press start term (the A2 classifier and the veto reader, fed by the radio BEFORE the press).

What stays X's is the press time, which is what the semi-bounded mode is told, and X's position in its
recording.

## Reported

Per pairing (session-01 folds shown), per participant and pooled:
- **follows donor**: committed = Y's line;
- **stays on own**: committed = X's line;
- **neither**.

Also reported:
- follows-donor beside the own-radio accuracy on the same walks;
- the edge lines, as donor's line and as X's line;
- walks where Y's walk had to be truncated to fit, and walks whose causal exit ran past the donor
  segment into X's own radio.

## Reading it, fixed now

The answer is read from the radio if follows-donor is close to the own-radio accuracy and
stays-on-own is near chance (one line in twelve is 8.3 percent, and X's own line is excluded as Y's).
A stays-on-own rate well above chance would mean something other than the radio (timing, the press,
the prior) carries X's line, and it will be reported as that.
