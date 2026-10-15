# PREREG: the 1 s head offset for the tracking dot (display only). Written 14 October 2026, from 09:56 SAST (clock read), before any decode

**Status.** Written and committed before any replay of this test. Its SHA-256 goes in `PREREG.md.sha256` and in the commit
that adds it; it is never edited afterwards, and any change before a run goes in a dated addendum file.

**The authority.** Uzayr's prompt `~/Downloads/prompt_mastermind_head_offset_1s.md` (file time 14 Oct 09:43, SHA-256
e98ad8c4dfa0163437b91ca98f27107821db473db09545fb44a8eb6ba14c000c), routed to Agent1 by the Mastermind (09:49), and his go in
Agent1's own chat (14 Oct, about 09:51): "do not worry about machine being quiet just run". The quiet-machine limit in the
prompt is therefore waived by him; every other rule of the prompt stands, and the rules below implement it.

Every figure is development evaluation, all data seen.

## 1. The one setting, and what is held

- **Changed:** the display head offset only, `head_offset_s` in the clean display profile
  (`pipeline/live/final_model.py`, `DISPLAY_PROFILES["clean"]["sett"]`), which `display.compose_walk` reads from the
  display's `sett`. In this test it is set on each built session's display (`session.display.sett["head_offset_s"]`), in
  the replay's own process. No shared file, no default and no other setting changes.
- **Arms:** 0.75 s (the shipped reference), 0.875 s, 1.0 s. Nothing above 1.0 s.
- **Held as shipped** (the clean profile, `FINAL_CONFIG.md` section 9, SHA-256 f4a9162f...), each asserted on every built
  session: candidate K1gf (look-ahead 1, anchor `glide_first`); the pooled display (no display head); prior flatten 0.50;
  SHIFT_W 1.0; switch arm A (theta 2.0, at most 1 switch, none in the final 1.0 m, radius 1.5 m); display spread 3.0; soft
  entry with the 1.0 m window; the 0.80 m per-window cap; latency 2.0 s, lock at press + 2.0 s, 10 frames per second.

## 2. Data (selection uses the development rotations only; A3 and B2 play no part)

- **The rotations**, exactly as the 8 to 10 Oct A3-clean display protocol (`runs/a3_clean_2026-10-08/PREREG_DOT.md`,
  addendum 1; `runs/clean_display_2026-10-10/PLAN.md`): A1+A2 -> B1 (weight 2), A1+B1 -> A2 (weight 1), A2+B1 -> A1
  (weight 1), on the all-0.5 s rotation cells `f05r_0102_to_B1`, `f05r_01B1_to_02`, `f05r_02B1_to_01`, registered in
  memory by `runs/a3_clean_0p5_2026-10-09/reg.py` as the 9 Oct dot side did.
- **Recordings:** the six walk recordings of each rotation's test session (18 in all), semi mode (one start press per
  walk), the causal (as it arrives) clock, fed by the 9 Oct harness's event loop (`dot_harness.feed`).
- **The guard:** every replay records the files it opens and refuses any write outside `runs/head_offset_2026-10-14/`. Any
  opened input naming session 03 (A3) or B2 stops the run.

## 3. R0: the harness reproduces the shipped display (before any arm is compared)

The 0.75 s arm is the shipped clean display. Its 18 replays must reproduce the 9 Oct stage 5 arm A replays
(`runs/a3_clean_2026-10-08/dot/stage5/multi/h-pooled_f0.5_o0.75_s1_sw-A_sd3_soft1/`, the same settings drawn with K1g),
under the 10 Oct gate 6 standard:
1. every row outside the anchor span identical, in order, floats included (press, lock, committed, switch, margin, and
   every dot outside the anchor span);
2. on every walk, the first anchor frame equals the locked line's entry exactly (K1gf), the only intended difference
   being the anchor-span dots.

If R0 fails, nothing is selected and the run stops.

## 4. The measures (the rule's metric is stage 3's)

On correct-lock walks, the truth at frame time minus 2.0 s, per rotation and then weighted (2 B1 + A2 + A1) / 4, by
`runs/a3_clean_2026-10-08/measures.py` unchanged (`arm_figures`):
- **The metric:** the median dot error from the press: frames from press + 2.0 s on, the anchor span included, the park
  excluded (`median_error_from_press_ok_m`), stage 3's objective.
- **The mean signed offset** (dot minus truth along the true line; negative: behind), on frames from the first decoded
  frame (`signed_offset_ok_mean_m`, the 9 Oct record's -0.35 m), with its 95 % interval.
- **The share within 0.5 m** on frames from the first decoded frame (`within_0_5m_ok_pct`), with its 95 % interval.
- **Intervals:** 95 % percentile bootstrap, 1,000 draws, seed 0, walks resampled within each rotation, weighted
  (`measures.boot_weighted_pooled`), as the 9 Oct sentence intervals. The median's interval is reported too.
- **Shown beside them, selecting nothing:** the signed offset and the share within 0.5 m on frames from the press.

## 5. The choice

1. Only arms that pass every guard (section 6) are eligible. The 0.75 s arm is the reference.
2. **Take the eligible arm with the lowest median.** Medians within 0.005 m of the lowest (DOT_PREREG's tolerance, as
   stage 3) are ties, broken towards the **smaller** offset (Uzayr).
3. **If that arm's signed-offset interval lies entirely above zero** (lower bound above 0: the dot leads the truth), take
   the next eligible arm by median whose interval does not.
4. If 0.75 s is chosen, it is reported plainly, because that changes the report's recommendation.

## 6. The guards (any failure disqualifies that arm)

1. **Display only.** On every walk of the 18 recordings, the lock line, the committed line and every switch (frame,
   old line, new line) equal the 0.75 s arm's in this harness (which R0 ties to the shipped display).
2. **Render rules,** on every walk (`pipeline.live.app_score.rule_checks` on the arm's logs, read with no label):
   - **rule 2a as Uzayr wrote it:** the first frame at or after press + 2.0 s is the locked line's entry exactly
     (within 1e-6 m, the hold form's own tolerance);
   - **rule 2a as the app's acceptance checks K1gf** (`anchor="glide_first"`): on the locked line within 0.15 m of its
     entry: zero anchor violations;
   - **the other rules:** zero park, together and one-lock violations, and at most one switch per walk;
   - **rule 2 (nothing is projected)** is a property of the display code, which this test does not change: the live
     suite's `test_no_projection_helpers_in_the_display_path` and `test_the_render_declares_nothing_is_projected` (guard
     4).
3. **Causality.** No frame reads radio that ends after its own stream time: every walk's minimum margin (the `margin`
   rows `display.compose_walk` computes) is at least -1e-9 s (`display.TOL`). Reported beside it: the minimum margin, and
   the draw lag on the stream clock (each dot's `computed_at` minus its frame time, as `rule_checks` measures it), its
   median, p99 and maximum, against today's worst of 0.153 s. The draw lag is reported, not a guard: the prompt's guard is
   the margin.
4. **Tests.** The live suite (`tests/test_live_*`) passes on the code the replays run, which this test does not change.

**The empty anchor span.** At 1.0 s the first decoded frame is at the park's end (`t_dec0` equals `park_until`), so there
is no anchor frame and no glide. The guards are applied as written. Also recorded: on how many walks each arm has any
anchor frame, and that every walk has a frame at or after press + 2.0 s.

**A prediction, written before any run, which selects nothing:** with no anchor frame, the first frame at or after press
+ 2.0 s at 1.0 s is a decoded position one SHIFT_W step (about 0.5 s of walking) along the line, so rule 2a may fail on
most walks and disqualify the 1.0 s arm. The minimum margins are expected near 0.25 s (0.75), 0.125 s (0.875) and 0 s
(1.0).

## 7. Then, only if an arm other than 0.75 s is chosen

- **A3 and B2 decoded once each with the chosen arm,** the final model, through the live app's own replay
  (`app_replay.replay_inner`, semi mode, the causal clock, the clean profile, the arm set in the replay's process only),
  into new folders under this folder. This is **A3's eighth look and B2's sixth look** (the record: A3's seventh look on 9
  Oct, reproduced not repeated by the 10 Oct gate 6; B2's fifth look on 10 Oct, `runs/clean_display_2026-10-10/LOOKS.json`),
  disclosed as chosen after the shipped results were seen.
- **Against the shipped replays** (`runs/live/replay/final/semi_disp-K1gf_causal/`), on the same walks:
  - the committed line and the lock identical on every walk (the display cannot move them; any difference stops and is
    reported);
  - the paired difference in the dot error on correct-lock walks (frames from the first decoded frame, the headline
    measure; and from the press), median against median on the walks lock-correct in both, 95 % walk-cluster bootstrap,
    1,000 draws, seed 0, as the 9 Oct A3 label rule (`runs/a3_clean_2026-10-08/a3_full.py`);
  - the signed offset (mean, with its interval) and the share within 0.5 m;
  - the render rules, the minimum margin and the draw lag.
- **No change to the live app's default and no re-render** until Uzayr says go.

## 8. Not changed

`pipeline/`, `engine.py`, identification, the networks, the readers, the decoder settings of the committed answer,
`FINAL_CONFIG.md`, the model sets, every shipped replay and render, and the report repository. Nothing ships.

## 9. Compute and stops

- **Compute:** 54 single-arm replays (18 recordings x 3 arms), each one process at nice 10 with OMP_NUM_THREADS 1, at most
  4 at a time; about 12.5 CPU-min each, so about 11 CPU-h and about 3 h of wall clock. A memory guard kills the job above
  12 GB in total or below 30 % free. runs/MACHINE_STATE.md written before and after each heavy step.
- **Stops:** R0 fails; a replay errors; an input naming session 03 or B2 is opened during selection; a write leaves this
  folder; a committed line or lock differs in section 7. A guard failure disqualifies its arm and does not stop the run.
- **Time box:** Thursday 16 Oct 18:00 SAST; if it cannot finish cleanly by then, it stops and reports where it got to.

## 10. Deliverables

A record in `reports/tracking/` (whichever arm wins), this pre-registration, a proposed row for the thesis ledger
(`tab:ledger`), and an Editor list of exact old and new text, not applied. The report repository is not touched.
