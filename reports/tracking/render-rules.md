# The rendering contract

**THIS IS THE SINGLE PERMANENT RENDERING RULE SHEET. Rules live here and nowhere else.**
Every `ACCEPTANCE.md` holds MEASURED RESULTS ONLY and points here for rules. If you find a rule
stated anywhere else, that copy is wrong by construction: delete it and link here.

**Rewritten 30 September 2026 for the live app** (Uzayr's instruction of 30 Sep, "one model, and it
is the live app", item B3). The rules are unchanged in substance. What changed:
- **Who draws.** The live app (`pipeline/live/`, `final_model.py`) draws every frame, natively. A
  render is an app replay at real-time pace with the screen recorded (`python3 -m pipeline.live
  replay ... --realtime`). The offline renderers (`f3_render`, `f4_render`, `pd_render`) are
  cross-checks only.
- **How a rule is enforced on the app.** `pipeline/live/app_score.rule_checks` reads the app's own
  replay log, and no label, and counts every violation. A render's `ACCEPTANCE.md` reports those
  counts. The offline tests are kept by name below (`tests/test_render_rules.py`,
  `tests/test_switching.py`); they check the offline renders, which are now the cross-check.
- **The two live forms,** each stated where it applies: rule 2a's anchor is HELD, and a walk's frames
  end at the app's own causal exit in the semi-constrained mode.
- **Since 1 Oct the app ships K1g,** whose anchor GLIDES. Rule 2a now has a K1g form beside the K0 one,
  and each display is checked by its own form.

The sheet as it stood before this rewrite is in git (`3c3c779`), with the full history of each
rule.

---

## 1. The lock is final

**Once the displayed line locks, at press + 2.0 s, it never changes for the rest of the walk,
except by the ONE mid-walk switch of 1a.** A confidently wrong walk stays wrong and stays in the
video.

**On the app.**
- THE lock is the line first drawn (`FinalTrackingSession.first_lock`).
- The display re-composes a walk from the windows it holds, and a later start press re-cuts windows
  back 6.0 s. So a later composition could name another line. Every such change is logged
  (`lock_change`) and counted.
- The count must be 0.

*Enforced by* `rule_checks: lock_changes_after_first`; offline,
`test_the_locked_line_never_changes_after_the_lock`.

### 1a. One mid-walk switch, display only (operator decision, arm C)

**The locked line may change once,** under every one of these constraints:
- at most ONE switch per walk, and it is final;
- only to the decision scorer's best line, after it has led the drawn line by theta 2.0 for two
  consecutive decode steps;
- never once the dot is within the final 1.5 m of its line;
- radio up to display time + 2.0 s only;
- no teleport: a 0.5 s slide, marked on screen.

**What it changes:** no committed line and no accuracy figure. The record of the arms is in
`reports/PREREG_switching_arms_2026-09-23f.md`.

**Disclosed beside it, always:** as a DECISION arm it failed (f) in `y3_switch`.

*Enforced by* `rule_checks: walks_over_one_switch` (must be 0); offline,
`test_render_at_most_k_switches_and_never_back_to_a_drawn_line`,
`test_render_no_switch_in_the_final_zone`, `test_render_persistence_rule_holds`,
`test_render_every_switch_is_causal_on_both_bounds`,
`test_render_switch_jumps_are_counted_apart_from_lock_jumps`,
`test_render_slides_stay_on_their_segments` and `test_render_equals_the_measurement_walk_for_walk`.

### 1b. The end-of-walk text is the app's committed line, labelled by mode

**The banner names the committed line of the mode being shown:**

| mode | banner label |
|---|---|
| **semi-constrained** (the headline) | "committed at the causal exit": the line the app announced at its own causal exit |
| **fully constrained** | "committed at the end press (upper bound)": the rescore at the end press |

**RIGHT or WRONG** is shown only in a replay, where a ground truth exists. On the rig the banner says
NO GROUND TRUTH.

*Enforced by* `FinalTrackingSession.screen_state`; offline,
`test_the_end_text_is_the_shipped_headline_decision`.

## 2. Nothing is projected

**No projection, no extrapolation, no pace-based motion of the dot, ever.** Every position the red
dot takes is one of these:
- a position the decoder produced;
- a point on the straight segment between two such positions;
- the anchor of 2a.

*Enforced by* `test_no_projection_helpers_in_the_display_path` (it reads the display source the app
imports) and `test_the_render_declares_nothing_is_projected`.

### 2a. The press anchor: the LIVE form holds it (30 Sep)

**At the lock, press + 2.0 s, the dot is placed at the ENTRY POINT of the locked line.**
- **Why that is allowed:** the press is the walker crossing that line's start tape, so the position is
  known without inference.
- **A wrong lock:** the dot starts at the wrong line's entry, and that is shown.

**The live form.** The dot is HELD at the entry until the walk's first decoded position (0.625 s later
on the press-centred lattice). From then on it follows the decoded path.

**Why the live form changed.**
- **What the offline renders did:** they slid the dot from the entry towards the first decoded
  position across that span.
- **The problem:** that position reads radio ending up to 0.6 s after the anchor frames, so a screen
  that draws each frame at its own time does not have it.
- **The old live code:** it drew no anchor frame when its batch held no decoded frame. So the dot sat at
  the room centre for 0.6 s after the green marker appeared, on every walk (found 30 Sep; fixed in
  `display.compose_walk`, `sett["anchor"] = "hold"`).

**A hold is not a stall.**
- **How often it matters:** the first decoded position is the tape entry on most walks (95 of 120 in
  the 23 Sep measurement), so on those the hold and the slide coincide.
- **Otherwise:** the dot moves to the first decoded position at 0.625 s.

*Enforced by* `rule_checks: anchor_violations` (the first frame off the park must be the locked
line's entry; must be 0); offline, `test_2a_the_first_drawn_position_is_the_committed_lines_entry`
and `test_2a_the_anchor_segment_is_straight_and_uses_no_pace`.

### 2a, the K1g form: the glide (1 Oct)

**Since 1 Oct 00:02 the app draws with K1g.**
- **Its source:** Uzayr's decision, recorded in `runs/dc2_results/display/DOT_DECISION.md` and set as
  `final_model.DISPLAY_CANDIDATE`.
- **What it changes:** over the anchor span the dot no longer holds at the entry. It glides along the
  locked line from the line's entry towards the walk's first decoded position, as the display glides
  between decoded positions.
- **Why the K0 check cannot apply:** the glide starts at the entry at press + 2.0 s, but the frame grid
  puts the first drawn frame up to 0.1 s later, by which time the dot is already a little way along the
  glide.

**The check** (written 1 Oct 09:21, before any K1g re-score; the 0.15 m threshold is Uzayr's, from his
instruction of 09:19, `reports/BRIEF_LIVE_APP_4_2026-10-01.md`):
- **The frame:** the one on which the green marker first appears, which is the first frame at or after
  press + 2.0 s (rule 6; `TrackingSession.screen_state`).
- **On the locked line:** on that frame the red dot lies on the locked line. That means within 1e-6 m of
  the straight segment from the line's entry to its exit. The tolerance is the K0 check's own, for
  floating-point rounding only; all twelve lines are straight (`paths.PathStates` asserts it).
- **Near the entry:** the dot is within 0.15 m of the locked line's entry, measured as a straight-line
  distance.
- **Automatic failures:** a walk with no lock, or with no frame at or after press + 2.0 s.

**Which form applies:** the display a replay was drawn with, read from its summary's
`display_candidate`.
- **Held (K0, K1, K2):** the K0 form above, unchanged; it is the K0 record's check.
- **Glide (K1g, K2g):** this form.

*Enforced by* `rule_checks(rows, anchor="glide"): anchor_violations`; must be 0.

### 2b. The anchor span is never a tracking result

**The dot error is measured from the first decoded position on.** The park and the anchor span are
excluded (`app_score`: frames at or after `t_dec0`).

*Enforced by* `app_score.score_recording`; offline, `test_2b_tracking_excludes_the_anchor_segment`.

## 3. The delay is stated on screen

**The caption names the delay:** "THE WHOLE DISPLAY RUNS 2 s BEHIND REAL TIME" (`screen.py`).

*Enforced by* `test_the_caption_names_the_delay`.

## 4. The dot error and the display offset are separate

**They are reported separately and NEVER added.**

**The dot error:**
- **What is measured:** the displayed dot at frame time x, against the truth at x - 2.0 s (the scene
  moment the frame shows, V1).
- **The truth:** interpolated linearly between the pass's anchor presses, on raw press times.
- **Where it comes from:** `app_score`, which is the only reader of labels.

**The display offset:** the truth at x against the truth at x - 2.0 s, the walker's own travel during
the fixed delay.

*Enforced by* `app_score` (two fields, never summed); offline,
`test_acceptance_reports_the_two_accuracies_separately`.

## 5. Every render reports its own honesty checks

**From the app's log (`rule_checks`), per recording and in total:**

| check | what it counts | must be |
|---|---|---|
| park | frames before press + 2.0 s not at the room centre | 0 |
| together | walks whose first frame off the park is not the first frame at or after press + 2.0 s | 0 |
| anchor | walks whose first frame off the park is not the locked line's entry | 0 |
| one lock | lock changes after the first | 0 |
| switches | walks with more than one switch | 0 |
| draw lag | how long after its own time each frame was ready (median, p99, max) | at most the window's cutting delay |

**The draw lag (V1 on the screen, fixed 30 Sep).**
- **Before:** the app drew the frames before a window's end only when that window arrived, up to one
  stride (0.5 s) after their time. A live screen would have shown the dot in 0.5 s steps.
- **Now:** once a window is decoded, every frame before the next window's end is drawn, because it
  cannot read that window (`FinalTrackingSession._draw_ahead`). Only the frames that can read a
  window wait for it to be cut.

*Enforced by* `rule_checks`; offline, `test_the_render_reports_all_five_honesty_checks`.

## 6. The dot and the marker leave together

**The first frame off the park is the first frame at or after press + 2.0 s,** the frame on which the
green marker first appears (its truth starts at the press, shown 2.0 s later).

**What sets it:** the press and one fixed constant, never a decoder output.

*Enforced by* `rule_checks: together_violations` (must be 0); offline,
`test_the_dot_and_the_marker_leave_together`.

**The stall clause (post hoc, 23 Sep) stands:** a hold the decoder accounts for is its error shown
honestly.

---

# The operator's vision. Rules V1 to V5

These are DECISIONS, not findings. Nothing below may be traded against a score.

## V1. The display runs exactly 2.0 s behind real time

**At video time x the scene shows the moment x - 2.0 s,** and the app may read every window that had
ended by x.

**On the app:** `display.LATENCY_S = 2.0`, and each frame is ready by its own time up to the cutting
delay (rule 5).

*Enforced by* `test_v1_the_latency_is_exactly_two_seconds`.

## V2. The dot commits on the same frame the marker appears

**The red dot waits at the room centre** (the park) until press + 2.0 s. It then appears at the locked
line's entry on the frame the green marker first appears.

*Enforced by* `rule_checks: park_violations`, `together_violations`; offline,
`test_v2_the_commit_frame_is_the_marker_frame`.

## V3. Red and green move together on one fixed clock; the lock is at press + 2.0 s

**The lock time is structural:** the press plus 2.0 s, on every walk.

**What is FORBIDDEN:** any confidence-gated or variable-latency lock.

**On the app:** the lock reads the window ending at press + 2.0 s, on the press-centred lattice.

*Enforced by* `test_v3_the_lock_time_does_not_vary_across_walks`,
`test_v3_the_lock_offset_is_exactly_two_seconds` and
`test_v3_no_confidence_gated_or_variable_latency_lock`.

## V4. No static dwell footage in a demonstration video

**A demonstration video contains walks.**

**On the app:** the recorder cuts any gap of more than 60 s between one walk's end and the next walk's
start, keeping 3 s on each side and the 2.0 s delay (`app_replay.ScreenRecorder.CUT_GAP_S`).
- **The gaps:** Room A's standing block is 450 to 530 s; the longest gap between walks in B2 is 22 s.
- **No pacing inside a cut:** nothing is filmed there, so the replay runs through it at full speed.
- **Unchanged outputs:** the outputs are identical at any pace.

*Enforced by* `test_v4_no_dwell_footage_in_the_demonstration` and
`test_no_seconds_constant_used_as_a_window_count`.

## V5. The drawn dot's phase

**The phase is `SHIFT_W = 0.50` strides,** with the app's head offset 0.375 s (`final_model.
DISPLAY_HEAD_OFFSET_S`, the final renders' phase). They are single global constants, never indexed by
line, participant or session.

**Where they came from** is traced in `reports/DISPLAY_PROVENANCE_2026-09-30.md`.

*Enforced by* `test_v5_the_display_phase_is_a_single_global_constant`.

---

## When a walk's frames end (the modes)

| mode | a walk's frames end |
|---|---|
| **semi-constrained** (the headline; no end press) | at the app's own causal exit (the scene time of the exit window's centre), or at the next start press, whichever is first |
| **fully constrained** | at the end press |

**No mode** draws past the point its inputs allow.

## The standing rules these sit under

**Not restated here, but they apply to every render:**
- `data/` is read only;
- `testing/` is never imported;
- frozen artefacts are never overwritten;
- the node geometry is fixed;
- statuses are computed rather than asserted;
- completion is decided by output contracts rather than exit codes;
- the pairing key is `session|stem|pass_id`;
- no decision rests on a single pairing.
