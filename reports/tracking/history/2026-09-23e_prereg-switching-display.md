# PRE-REGISTRATION: mid-walk switching as a DISPLAY decision. Batch 2026-09-23e, item 1

**Written 2026-09-23 ~17:10, before the shared switching module, the stage (`e1_switch`) or the render
existed, and before any number under this rule.** The operator's item is stored verbatim in the BRIEF,
INSTRUCTION 5. This file fixes how each clause is read and measured, where the instruction leaves room.

## 1. Status: a presentation decision, not a ship-rule arm

The operator adopted switching as display only: it changes no committed answer and no quoted accuracy
figure (the headline stays 62.50 pre-registered, 73.33 post-amendment). RENDER_RULES rule 1 is amended
by the operator's constraints. **Disclosed beside it, always: as a DECISION arm it failed (f) in
`y3_switch` (K = 1, theta 3.0: E_col5 -3 walks).**

## 2. The baseline

**The DRAWN lock**: the display decode exactly as `f3_render` runs it (`sd_scale` 4.5, 0.8 m per window,
DISP_END flattened 0.50, A2 0.5, soft entry, lock at press + 2.0 s) on the ONE lattice. Nine pairings,
held-out 53.33 (`d6_lock_commit`). Lock-final scores 100 or 0 per walk on the frames below. The stage
asserts its lock equals `d6_lock_commit`'s `lock_drawn` on 1080 of 1080 passes.

## 3. The rule, exactly

Decision frames `x_k = press + 2.0 + k * 0.5 s`, k >= 1, while `x_k < end press + 2.0` (video time).

1. **Causal, wall-clock.** At `x_k` the decision reads only windows with `t_start + 2.0 <= x_k`, the
   scene-time horizon `t + 2.0`. Reported per switch, both bounds: the EVIDENCE bound (the latest window
   the decision read) and the DRAWN bound (the window whose decoded position the dot is sent to). Both
   must be <= 0.
2. **The running score** is `y3_switch`'s: each line's within-chain Viterbi total over the causal
   windows, prior withheld, **plus the SHIPPED committed start term (A2 + `a_veto_1.0`,
   `veto.committed_start_terms`)**, because the veto now ships on the committed decision and "the
   decoder" is the shipped one. The A2-only score `y3` used is reported beside it at the chosen theta, as
   a diagnostic only.
3. **Only to the decoder's current best line**: `best = argmax` over all twelve lines. If the drawn
   line is best, nothing happens and any streak resets.
4. **Persistence: TWO consecutive decode steps.** The SAME line must be best and lead the drawn line by
   more than theta at `x_{k-1}` and at `x_k`; the switch happens at `x_k`. Since k starts at 1, the
   earliest switch is `k = 2`, 1.0 s after the lock.
5. **At most ONE switch per walk, final**: after it nothing is evaluated, so the dot never returns to
   the locked line.
6. **Never once the dot is within the final 1.0 m of its current line**: if the DRAWN dot's arc along
   its line has reached `line length - 1.0 m` on ANY frame up to `x_k`, switching is disabled for the
   rest of the walk. "The dot" is the drawn dot, computed by the render's own `simulate_walk` on the
   render's own frame grid; the stage reproduces that grid.
7. **No teleport.** At `x_s` the dot is at `p_old`, its drawn position on the old line. Over the next
   0.5 s (frames in `[x_s, x_s + 0.5)`) it moves along the straight segment from `p_old` to `q_new`, the
   first drawn position of the NEW line's decoded path at `x_s + 0.5`, by elapsed fraction of the fixed
   0.5 s interval: no pace, no fitting, and every slide frame is checked to lie on that segment
   (`switch_segment.off_segment_frames` must be 0). From `x_s + 0.5` the dot follows the new line's
   path, which is `locked_chain_path` on the new line with the SAME display emissions, display prior,
   entry prior, window range and evidence horizon as the locked line's; so every post-switch position is
   a decoded display position under the same causal horizon.
8. **Marked on screen** from `x_s` for the rest of the walk: "SWITCHED <old> -> <new>".

## 4. Theta, on the selection folds only

Swept over {0.5, 1.0, 1.5, 2.0, 3.0} nats (`y3_switch`'s grid). **Chosen on `s01_to_s02` and
`s02_to_s01` only**: the theta with the largest mean time-on-correct delta over the two folds among
those with pooled wrong-to-right > right-to-wrong on the two folds; ties to the larger theta. If none
qualifies, the theta with the largest selection delta is taken and evaluated anyway (the keep rule then
decides). Held-out numbers are never seen by the choice.

## 5. What is measured, nine pairings, session-01 folds shown, edge lines beside every pooled figure

| quantity | definition |
|---|---|
| **time on correct line** | share of frames from the lock frame (press + 2.0) to end press + 2.0, at 10 fps, whose NAMED line is the true line. The named line changes at `x_s` (the frame the switch is marked), `y3_switch`'s convention |
| **paired delta** | per pairing, switching minus lock-final, mean over walks; nine-pairing mean with a bootstrap interval (1000 resamples, seed 0), held-out seven beside it |
| wrong-to-right, right-to-wrong, wrong-to-wrong | integer walk counts, per pairing and pooled |
| edge-line walks | per edge line: walks, lock right, drawn-at-end right, W2R, R2W, time on correct |
| **switch jump distance** | `|q_new - p_old|`, metres, distribution; count and share over 1.5 m |
| frame jumps | frame-to-frame moves over 0.5 m inside slides, counted SEPARATELY from lock jumps |
| substitution | the decisions recomputed on the next recording's radio; changed share over the partner-different share, reported, `y3`'s definition |

## 6. The keep rule, as the operator set it, read exactly

**Keep if (i) the nine-pairing mean paired time-on-correct delta is above zero AND (ii) pooled over
the nine pairings, wrong-to-right walks exceed right-to-wrong walks (integers).** The held-out seven's
interval is reported beside it, not gating.

## 7. The 1.5 m restriction

**If more than a quarter of the chosen rule's switches move the dot over 1.5 m**, the restricted variant
is also run: a switch is allowed only if the decoder's position on the candidate line is within 1.5 m
of the drawn dot, at BOTH persistence steps. Its theta is chosen by section 4 on the same folds. Both are
reported. **Which is rendered, fixed now:** if the trigger fired and the restricted variant keeps, it is
rendered (the operator asked for it because of large jumps); otherwise the operator's rule if it keeps;
otherwise the restricted one if it keeps; otherwise NO switching, and rule 1 stays as it is.

## 8. Render equals measurement

The render and the stage call the SAME functions (`pipeline/constrained/switching.py`) for the scores,
the decision and the slide. **After the render, its switch decisions on its pairing must equal the
stage's at the rendered theta, walk for walk (120 of 120), or the render is not frozen.**

## 9. What makes it INVALID rather than refused

A switch reading radio past `x_k` on either bound; theta chosen with held-out numbers; any slide frame
off its segment; the stage's lock not equal to `d6_lock_commit` on every pass; the render's switches not
equal to the stage's; a missing measurement scored as a pass.
