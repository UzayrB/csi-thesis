# Phase 0: the A3-touched display settings, checked against the code and git. 8 October 2026, 16:58 SAST (clock read)

Brief: Uzayr's "an A3 figure with every display setting chosen without A3" (8 Oct, pasted into the second-work chat).
Read only: nothing was run on data, nothing outside this folder was written.

## Sources read

- `reports/tracking/2026-09-30_display-provenance.md` (section 3 is the table rebuilt here), `runs/dc2_results/rule/DISPLAY_PREREG.md`.
- `reports/tracking/2026-10-01_display-k1g.md`, `runs/dc2_results/rule/DOT_PREREG.md`, `runs/dc2_results/display/DOT_DECISION.md`.
- `reports/tracking/2026-09-30_live-app-second-instruction.md` section 1b (the 23-row exposure table).
- The code that sets each value now: `pipeline/live/display.py` (constants, `settings()`), `pipeline/live/final_model.py`
  (`DISPLAY_HEAD_OFFSET_S`, `DISPLAY_CANDIDATE`), `pipeline/live/tracking.py:47` and `pipeline/constrained/pd_decode.py:517, 532`
  (the entry), `pipeline/live/app_replay.py:56-60` (the rotation replays' display head).
- The stage results `display.settings()` reads: `runs/constrained/fh/{r3_prior,e2_switch,s2_display}/results.json`; and
  `runs/constrained/fh/q4_arms/results.json`.
- The pre-registrations: `reports/tracking/history/2026-09-22_prereg-dotphase.md`, `2026-09-24_prereg-display-phase.md`,
  `2026-09-23f_prereg-switching-arms.md`; the operator's render brief `reports/tracking/briefs/2026-09-22_render-and-prepress.md`.
- Git: 0b18ee6 (20 Sep 10:16), 8590d47 (21 Sep 10:15), e26f4cb (20 Sep 01:52), 0ca7ca6 (20 Sep 12:43), 3834d7f (20 Sep 13:34) all
  exist; the retired stage code (r2_softentry, r3_prior, w1_dotphase, e2_switch) is readable at 3c3c7799.

## The values in force (read from the code, 16:58)

`display.settings()` returns prior `flatten_0.50`, switch arm C (theta 2.0, max 1 switch, final 1.5 m, radius 1.5 m),
display `DISP_END`. `DISPLAY_SD_SCALE = 4.5`, `DISPLAY_CAP_M_PER_WINDOW = 0.80`, `SHIFT_W = 0.50`, `final_model.DISPLAY_HEAD_OFFSET_S
= 0.375` (overrides display.py's 0.75 in `FinalTrackingSession.__init__`), `DISPLAY_CANDIDATE = "K1g"`, entry "soft" with
`entry_window_m` 1.0 (hard-coded in `live/tracking.py:47` and `pd_decode.py:517, 532`; not a decode-variant part).

## The list: A3-touched display settings

| # | setting | shipped value | reads it | how it was chosen | A3 in that data |
|---|---|---|---|---|---|
| 1 | spread (display sd_scale) | 4.5 | lock and dot | introduced with the 3 m/s ceiling on the demonstration pairing s0102_to_s03 (0b18ee6). Re-swept 30 Sep under DISPLAY_PREREG s3: grid 2.5 to 6.0 step 0.5, rotation-weighted display-lock accuracy, ties to the smallest: argmax 2.5 (2.5 to 4.0 tie at 51.25; 4.5 gives 50.63) | yes (the original) |
| 2 | soft entry (entry = "soft") | soft | lock and dot; committed line through the exit only | r2_softentry (e26f4cb): soft against the free entry, non-inferiority over the nine cross-day pairings | yes (A3 the test side of 3 of the 9) |
| 3 | 1.0 m entry window | 1.0 m (5 states per line) | lock and dot, the switch scorer; committed line through the exit | q4_arms arm A1: arm and weight selected on s01_to_s02 and s02_to_s01; SHIPPED on its paired interval of committed-line accuracy over the seven decision folds, with the end-substitution guard | yes (the ship decision) |
| 4 | head offset | 0.375 s | dot | PREREG_display_phase (24 Sep): grid {0.75, 0.625, 0.50, 0.375, 0.25, 0.125, 0.00} on s0103_to_s02 (trained on A1+A3); the value whose share of correct-lock frames with the dot ahead is closest to 33.5 %, ties within 1.0 point to the larger. The 33.5 % target is w1_dotphase's share at shift 0.50 over the nine pairings | yes (training side, and the target) |
| 5 | dot phase SHIFT_W | 0.50 strides | dot | w1_dotphase (22 Sep), grid {0, 0.25, 0.50, 0.75, 1.00}, nine pairings, primary: frames within 0.5 m of the truth on correct-line passes. The pre-registered rule SHIPPED NOTHING (its tie-break picked 1.00); 0.50 ("best by primary") was then set by the operator's instruction 4 in the render brief | yes |
| 6 | switch arm C | 1 switch, final 1.5 m, radius 1.5 m, theta 2.0 | dot | e2_switch (PREREG 23f): qualify on the nine-pairing mean time-on-correct delta, the held-out seven's interval and pooled W2R > R2W; pick the highest end-on-committed agreement; within 9 walks, fewer switches, then fewer jumps. Band A_t2, B_t2, C_t2 (top 647); C chosen | yes |
| 7 | display prior | flatten 0.50 on DISP_END's path | dot | r3_prior: grid flatten {0, 0.25, 0.50, 0.75, 1.0} and DISP_RAW over the nine pairings (30,033 frames); the weakest prior with excess motion under 0.5 % of frames and at most 1 backwards step over 0.5 m per walk; rule loosened POST HOC | yes |
| 8 | display head choice | DISP_END | dot | s2_display: arms centre_labelled, DISP_END, DISP_RAW; pass dwell drift and causality, no worse on substitution; then zero jumps over 0.5 m; then the best mean position-now error over the nine pairings | yes (the choice; the head's own training, A1+A2+B1, has no A3) |

**Cleared or clean, not on the list:** the cap (cleared 30 Sep, DISPLAY_PREREG s2); latency 2.0 s, lock time press + 2.0 s,
frame rate (operator); display lag (structural); the A2 weight 0.25 in the lock's decode (the rotations); switch theta 2.0
(s01_to_s02, s02_to_s01); the anchor hold (a causality fix).

**K1g (1 Oct).** It introduced two settings: the drawn path's look-ahead (1 window) and the glide over the anchor span. Both were
chosen on the three rotations only (`DOT_CHOICE.json`, 30 Sep 20:53), by Uzayr's decision after DOT_PREREG's rule kept K0
(`DOT_DECISION.md`). No A3, so neither joins the list. They were chosen with settings 1 to 8 at their shipped values.

## Findings that bear on Phases 1 and 2

1. **The rotation replays' display head is in-sample.** `app_replay.DEV_SETS` gives every rotation the final DISP_END, trained on
   A1+A2+B1, so on every rotation the drawn path reads a head trained on the test session (the code says so at line 57).
   No A3 is involved, so a dot-side selection there is A3-clean, but each dot objective is measured with an in-sample head.
   Setting 8 (DISP_END against the pooled display) cannot be compared fairly that way. A held-out end head exists for one rotation
   only: the zero-shot DISP_END (`pd_dispend_zs`, A1+A2) on A1+A2 to B1. No retraining is allowed, so on A1+B1 to A2 and A2+B1 to
   A1 there is no held-out display head.
2. **The head offset's target (33.5 %) is itself an A3-touched number.** Re-selecting setting 4 on the rotations needs a target
   not derived from A3; none is recorded.
3. **SHIFT_W was an operator decision that overrode a pre-registered KILL.** Re-running "the original procedure" means choosing
   either the pre-registered rule (its tie-break selects by the signed offset closest to zero) or the operator's basis (the argmax
   of the primary).
4. **The original dot objectives were computed by retired offline stages** (f3-era renderer, the nine pairings, the grid lattice
   for w1). On the rotations they must be recomputed on the app's frames; each is a port, not a re-run.
5. **The entry (settings 2 and 3) is hard-coded**, not a decode-variant part: sweeping it needs a wrapper in this folder that sets
   `opts["entry"]` and `opts["entry_window_m"]` in a copy of the decode, with the shipped point reproducing the records exactly.
   Its original objective is committed-line accuracy with the end-substitution guard, not the lock.
6. **Outside this brief's scope, still feeding the A3 lock and dot:** the decision-side design choices of the 30 Sep exposure table
   (rows 7 to 10, 12, 14 to 16: pooling, the head recipe, stride, window, using s0102_to_s03's Config everywhere, the untraceable
   Config defaults, the HMM structure, `normalise`, which was decided on A3's own test-side arm). DISPLAY_PREREG's label covers
   display settings only, so these do not carry the OPTIMISTIC label, but the A3 sentence "clean in weights and fitted statistics,
   exposed in design choices" stays whatever this brief finds.
