# PLAN note 4: the fully constrained mode is not replayed; one B2 recording confirms. Written 10 October 2026, 09:12 SAST (clock read), before any decode of it

**Applies to:** `PLAN.md` (5f13034c), section 4 (the looks).

**The question (this chat, 09:11):** the report quotes the fully constrained mode (committed, and "lock (= semi's)") for
B2, A3 and zero-shot B2. The plan did not replay it under the clean display.

**The ruling (the Mastermind, about 09:12): option (a), no full replay.**
- **The committed figures stand.** The display cannot move a committed line.
- **The lock is quoted as "equal to the semi-constrained lock by construction".** In both modes the lock is the line
  first drawn at press + 2.0 s. No end press has arrived by then, and `LiveDisplay._compose` reads the end press only once
  it exists.

## The confirmation (inside B2's fifth look: same configuration, another mode, so no new look)

- **When:** after the semi fifth looks PASSED (`run.py fullcheck`, which writes FULLCHECK.json and refuses to run
  earlier).
- **What runs:** ONE B2 recording, `participant_PA5_walk` (the first in name order), replayed in fully constrained
  mode (`--presses start_end`) under the clean profile. It writes the new folder
  `runs/live/replay/final/full_disp-K1gf_causal`.
- **The conditions, on its 20 walks (both must hold, or STOP and message the Mastermind):**
  1. the lock line equals the clean semi replay's (`semi_disp-K1gf_causal`) on every walk;
  2. the committed line equals the shipped full-mode replay's (`full_disp-K1g_causal`) on every walk, for both kinds
     the log carries: `committed_full` (the fully constrained answer) and `committed`.
- **Reported beside them:** whether the whole lock rows and the whole committed rows (floats included) are identical.
- **If both hold,** the report says "by construction, confirmed on one B2 recording (20 walks)".
