# PLAN note 2: how gate 6's condition 2 is checked. Written 10 October 2026, 09:02 SAST (clock read), before any decode

**Applies to:** `PLAN.md` (5f13034c), section 3, gate 6, condition 2 ("every anchor-span dot equals the glide_first
formula exactly"). The plan itself is unchanged. The definition below was proposed by this chat and APPROVED by the
Mastermind (10 Oct, about 09:01), with the two guards at the end.

**Why the logs alone cannot show it bit-exactly:**
- the logs round each frame time to 4 decimals;
- the glide's end point (the seam S) at an anchor frame is the drawn path's position as the app knew it when it drew
  that frame. Frames are drawn batch by batch as windows arrive, and S is not logged.

## The definition

1. **(a) The replay:** each A3 recording runs through the app's own `app_replay.replay_inner` (the CLI's code path),
   with its `hold` hook, which returns the session object. The recording's exact frame-grid origin is kept beside the
   log, and the exact frame times come from `display.frame_times(origin, n)`, as the app builds them. The app writes the
   log as usual.
2. **(b) The first anchor frame** of each walk must equal the locked line's entry BIT-EXACTLY (the formula gives f = 0
   there; rule 2a as written).
3. **(c) Every later anchor frame** must equal `entry + (S - entry) * f_glide_first` to within 1e-9 m, where:
   - `f_glide_first = (x - x_first) / (t_dec0 - x_first)`, with x and x_first exact;
   - S is recovered from the seventh look's K1g dot at the same frame: `S = entry + (old - entry) / f_K1g`;
   - `f_K1g = (x - park_until) / (t_dec0 - park_until)`.

   The 1e-9 m allows only for the float rounding in recovering S. The largest deviation found is reported.
4. **(d) Every non-xy field** of each anchor row (kind, pid, x, computed_at) must be identical to the seventh look's.

## The guards (the Mastermind's)

1. **The order:** condition 1 (every row outside the anchor span identical, floats included) is checked first and must
   PASS. Condition 2 is evaluated only after that, because recovering S assumes the app had the same path at the same
   frame.
2. **No skips:** an anchor frame other than the first where f_K1g = 0, or where S cannot be recovered, is a FAIL of
   condition 2, which makes A3 an eighth look and stops the work. The number of anchor frames checked per walk is
   reported.

**Anchor span membership:** a dot is in the anchor span when its exact frame time x satisfies
`park_until <= x < t_dec0` (display.compose_walk's own test), with park_until and t_dec0 read from the walk's lock row.
