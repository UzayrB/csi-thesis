# PREREG addendum 1, 14 October 2026, 10:05 SAST (clock read): rule 2a and an empty anchor span, before any scoring

**Status.** Written and committed while the 54 replays run, before any replay has finished and before any arm is scored
or any figure read. `PREREG.md` (SHA-256 03eb01219e4f82ea768d4fadec02186da55c0da5cbf0835bd627ed6865606cf0, 8109011c) stands
except where this changes it.

**Why.** PREREG section 6 predicted that at 1.0 s the anchor span is empty (`t_dec0` equals `park_until`), so the first
frame at or after press + 2.0 s is a decoded position about one SHIFT_W step along the line, not the line's entry. Rule
2a as written would then disqualify the 1.0 s arm by construction, whatever its dot error. The Mastermind raised it
(10:0x) and asked that nothing be scored until Uzayr answered.

**Uzayr's answer, in Agent1's chat (14 Oct, about 10:05), to the question** "How should rule 2a apply to the 1.0 s arm?":
**"Exempt an empty anchor span"**, the option worded: "When an arm has no anchor frame, rule 2a doesn't apply; the other
render rules, rule 2 and causality still do. 1.0 s competes on its dot error. Written as a dated addendum before any
scoring."

## The change to guard 2

1. **Rule 2a (both forms: the entry exactly, and app_score's `glide_first` form) applies to a walk only if that walk has
   at least one anchor frame in that arm:** a drawn frame with `park_until <= x < t_dec0`, read from the walk's own lock
   row (tolerance 1e-4 s, the log's frame-time rounding). A walk with no anchor frame in that arm is exempt from rule 2a.
   The rule is applied the same way in every arm, and the number of exempt walks is reported per arm.
2. **Unchanged, on every walk:** display only; the park, together, one-lock and at-most-one-switch rules; rule 2 (the
   live suite); causality (the margin). **A walk with no frame at or after press + 2.0 s still fails** (it is counted
   under the other render rules).
3. Nothing else changes: the arms, the data, R0, the measures, the choice rule and section 7.

**The prediction stands as written:** with the exemption, the 1.0 s arm is expected to be exempt from rule 2a on (almost)
every walk and to compete on its dot error.
