# PRE-REGISTRATION: the scorer lock. Batch 2026-09-23g, item 2

**Written 2026-09-23 20:17 (clock read), before the stage (`g2_scorerlock`) exists and before any
number for this arm at any w other than the two endpoints already seen (below).** The operator's item
is stored verbatim in the BRIEF, INSTRUCTION 7.

## 0. DISCLOSURE, first: this Room A test is NOT clean

**The lead this arm tests (+4.17 [0.93, 8.33] paired, held-out +5.83 [2.74, 10.24], edge walks net
+1) was observed on ALL NINE PAIRINGS, the held-out folds included, in `e2_switch`**
(`reports/INVESTIGATION_switching_2026-09-23f.md`). That is the w = 1.0 endpoint of this arm, seen on
the folds it will be judged on. Choosing w on the selection folds does not undo that: the idea was
formed after looking at the held-out folds. **This Room A test is therefore not clean, and DC2 is its
confirmatory test.** Any Room A figure below is quoted with that sentence beside it.

## 1. The arm

For each walk, at the lock (press + 2.0 s, the lock's own three windows):

    lock line (w) = argmax over lines of  (1 - w) * D(line)  +  w * S(line),   w in {0, 0.25, 0.5, 0.75, 1.0}

| score | definition |
|---|---|
| **D(line)**, the display-lock score | the best Viterbi score over that line's states at the lock's last window, from the SAME display decode the shipped lock is read from (`night_track(..., display_lock_scores=True)`). Its argmax is the shipped lock whenever the lock state is on a chain |
| **S(line)**, the scorer score | the final-answer scorer's line total with the shipped start term (A2 + `a_veto_1.0`) on the lock's own windows, `switching.Scorer`, as `e2_switch` read it |

Raw nats, no rescaling. **w = 0 IS the shipped lock** by definition; the number of walks on which the
argmax of D differs from the shipped lock (an off-chain lock state) is reported, and must be 0 or those
walks keep the shipped lock at w = 0. **The dot's path after the lock is the restricted along-line decode
on the chosen line** (`locked_chain_path` with the display emissions, display prior, entry prior and
evidence horizon), the construction a switch already uses.

## 2. w, on the selection folds only

The w in {0.25, 0.5, 0.75, 1.0} with the largest mean paired lock-accuracy delta against the shipped
lock over `s01_to_s02` and `s02_to_s01`; ties to the SMALLER w. **If no w has a positive selection
delta, the arm is REFUSED at w = 0.** The chosen w is evaluated once on the held-out seven.

## 3. The ship rule, in full

The metric is the lock's correct line, per pairing, against the shipped (display) lock on the same passes.

- **(a)** the held-out seven's paired 95 percent interval of the per-pairing delta entirely above zero.
- **(b)** the median over the held-out seven of the per-pairing delta, in passes of 120, at least 2
  (integers).
- **(c) as clarified:** read on the median held-out paired delta across w in {0.25, 0.5, 0.75, 1.0}: the
  response is not flat (not all four equal) and the chosen w's is above zero. An interior optimum is
  allowed because w is chosen on the selection folds.
- **Substitution:** the arm's added component, the scorer, is recomputed on the NEXT recording's radio
  (another participant's, `y3_switch`'s definition), the display score held. Over held-out passes where
  the arm's lock differs from the shipped lock, the share whose lock changes under substitution, divided
  by the share of held-out passes whose partner walked a different line, must be at least 0.5.
- **Both causal bounds:** the lock reads only the lock's own windows, the same windows as the shipped
  lock, and its evidence bound is reported beside the shipped lock's. The dot's path after the lock is
  checked frame by frame on both bounds, as the render does; either above zero fails.
- **(f) as amended:** per edge line, lock-correct walks against the shipped lock over nine pairings:
  combined change at least 0, and no line losing more than two walks.

## 4. Continuity, checked

Each walk's dot is simulated with the render's own functions on the chosen line: the anchor segment from
the chosen line's entry, then `simulate_walk` on its path. Reported, arm against shipped: rule violations
(must be 0), anchor frames off segment (must be 0), frame jumps over 0.5 m after the lock, and the
first decoded position's distance from the line entry.

## 5. Then

**Ships:** item 3 of the instruction (switching theta re-chosen under the new lock, one render, a new
freeze letter, the contradiction rate against 433). **Does not ship:** recorded beside the ablation and
nothing changes. The committed headline does not change either way; the lock figure is quoted beside
the shipped lock's.
