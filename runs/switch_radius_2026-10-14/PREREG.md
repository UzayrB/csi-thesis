# PREREG: the switch without its 1.5 m radius condition (display only). Written 14 October 2026, from 17:30 SAST (clock read), before any replay

**Status.** Written and committed before any replay of this test. Its SHA-256 goes in `PREREG.md.sha256` and in the commit
that adds it; it is never edited afterwards, and any change before a run goes in a dated addendum file. The scoring code
(`run.py`, `sr_harness.py`) is committed with it.

**The authority.** Uzayr's prompt pasted into the Code agent's chat on 14 Oct (after 17:26), with his go there; slot
pre-granted by the Mastermind (ref af0c82) at 17:26 (MACHINE_STATE queue item 11, a99dae55). His question to the Mastermind:
"can you test quickly if removing that 1.5m rule is helpful or not?". Nothing ships without his go.

Every figure is development evaluation, all data seen.

## 1. The arms

- **R1.5:** the shipped display, profile `clean_1s` (`pipeline/live/final_model.py`, `DISPLAY_PROFILES["clean_1s"]`):
  K1gf, the pooled display (no display head), prior flatten 0.50, SHIFT_W 1.0, head offset 1.0 s, switch arm A (theta 2.0,
  at most 1 switch, none in the final 1.0 m, **radius 1.5 m**), display spread 3.0, soft entry with the 1.0 m window, the
  0.80 m per-window cap, latency 2.0 s, 10 frames per second. Every one of these is asserted on every built session.
- **R0:** the same, with `radius_m` set to `None` on the built display's switch settings
  (`session.display.sett["switch"]`, a copy, in the replay's own process), so `switching.decide_walk` skips its lines
  258 to 261 and every candidate line is "near". No shared file, default or other setting changes.

## 2. Data

- **The 18 development-rotation recordings of the head-offset test** (`runs/head_offset_2026-10-14/PREREG.md` section 2):
  A1+A2 -> B1 (weight 2), A1+B1 -> A2 (weight 1), A2+B1 -> A1 (weight 1), on the all-0.5 s rotation cells `f05r_0102_to_B1`,
  `f05r_01B1_to_02`, `f05r_02B1_to_01` (registered by `runs/a3_clean_0p5_2026-10-09/reg.py`); the six walk recordings of
  each rotation's test session, semi mode, the causal clock, fed by `runs/a3_clean_2026-10-08/dot_harness.feed`. 360 walks
  (120 per rotation; 12 true lines, the four edge lines 6 walks each per rotation).
- **No A3 or B2 replay.** The input guard of the head-offset harness is kept: any opened input naming session 03 (A3) or
  B2 stops the run, A3's walk sidecars read for the line geometry excepted only while
  `lock_side.geometry_from_session_01()` holds (the head-offset test's addendum 2). Writes outside this folder are refused.
- **The device:** every replay calls `force_cpu()` before anything loads, and records `nets.device()` in its summary; a
  device other than `cpu` is a STOP.

## 3. R1.5 reuses the head-offset test's 1.0 s logs if they reproduce exactly

The 1.0 s arm's logs (`runs/head_offset_2026-10-14/logs/o1/`, 18 recordings, written 10:10 to 12:21 on 14 Oct on the CPU by
`ho_harness.py`, which calls `force_cpu()`) used the clean profile with the head offset set to 1.0 s; `clean_1s` has the
same settings (commit 19fcaf59 changed only the profile table). The check:
- **three recordings are replayed under R1.5** with this test's harness: in each rotation, the first recording
  (alphabetically) with the most R1.5 switches in those logs: A1 `participant_PA1_walk`, A2 `participant_PA6_walk`,
  B1 `participant_PA3_walk` (2 switches each);
- **each must equal its 1.0 s log row for row**, in order, every field and float included;
- **if all three are equal,** the 18 logs are R1.5. **If any differs, the run STOPS** before anything is scored and the
  Mastermind is told (an exactness difference is never accepted by the Code agent).

## 4. The STOP before scoring

On all 360 walks, **the lock line and the committed line of R0 equal R1.5's.** The switch draws only the display, so any
difference is a STOP: nothing is scored and the Mastermind and Uzayr are told. Also a STOP: a replay errors, a device other
than `cpu`, a forbidden input, a write outside this folder.

## 5. The measures

Per rotation, then combined with the weights (2 B1 + A2 + A1) / 4. Intervals: 95 % percentile bootstrap, 1,000 draws,
seed 0, walks resampled within each rotation; **paired** intervals draw the same walks in both arms and take R0 minus R1.5.
Helpers from `runs/a3_clean_2026-10-08/measures.py`, unchanged.
1. **Switches,** each classed by the walk's true line: wrong-to-right (W2R: old line wrong, new line true), right-to-wrong
   (R2W), wrong-to-wrong (W2W) (`measures.switch_walk`'s classes). Per rotation counts, raw totals over the 360 walks, and
   **the net N = W2R minus R2W, combined (2 N_B1 + N_A2 + N_A1) / 4** (the rule's form), with each arm's interval and the
   paired interval of N(R0) minus N(R1.5). The raw total of W2R minus R2W is shown beside it.
2. **The share of drawn frames on the true line** (all walks): frames from press + 2.0 s on (`measures.from_press_frames`,
   the frames of stage 5's time on the correct line), the share whose named line (`measures.named_line`: the lock, then
   each switch's new line from its frame) is the true line, pooled over the rotation's walks; each arm's value and
   interval, and **the paired interval of R0 minus R1.5 (the rule's interval)**.
3. **Dot error from the first decoded frame** (`measures.decoded_frames`, the truth at frame time minus 2.0 s,
   `measures.errors`): the median of the rotation's pooled frames, combined; **on all walks and on correct-lock walks**
   (lock equals true, the same walks in both arms since the locks are equal); each arm's value and interval, and the
   paired interval of R0 minus R1.5.
4. **Per true line** (12 rows, E_col1, E_col5, E_row1 and E_row5 among them): walks, correct locks, each arm's W2R, R2W and
   W2W (raw counts), each arm's share on the true line and the dot-error median on all walks (combined as above), and the
   difference in share.
5. **Shown, selecting nothing:** switch events, the slides longer than 1.5 m (`switch_walk`'s `jumps_over_1_5m`: the dot
   before the switch to the first frame after the 0.5 s slide), walks ending on the committed line, the minimum causality
   margin, and the walks whose switch differs between the arms (a list).

## 6. The rule (Uzayr's, verbatim in substance)

**R0 is better only if** N(R0) is higher than N(R1.5) (section 5.1, the combined form, strictly higher) **AND** the paired
95 % interval of the share of frames on the true line, R0 minus R1.5 (section 5.2), lies above zero (its lower bound above
0). **Otherwise R1.5 stays.** The dot error is reported either way. If the combined and raw forms of N disagree in
direction, that is reported; the combined form decides.

## 7. Not changed

`pipeline/`, `engine.py`, identification, the networks, the readers, `FINAL_CONFIG.md`, the model sets, every shipped
replay and render, the head-offset test's files, and the report repository. Nothing ships; the live app's default stays
`clean_1s` with the radius whatever this shows, until Uzayr says otherwise. No A3 or B2 decode without his word.

## 8. Compute

21 replays (3 R1.5 for the check, 18 R0), each one process at nice 10 with OMP_NUM_THREADS 1, at most 4 at a time, CPU
only; about 12.5 CPU-min each, so about 70 min of wall clock. A memory guard kills the job above 12 GB in total or below
30 % free. Untimed, so no LaTeX hold. MACHINE_STATE written before and after; the Mastermind holds the caffeinate.

## 9. Deliverables

`RESULT.json` (every figure, the rule's verdict) and a short `RESULT.md` in this folder, reported to Uzayr and the
Mastermind. No Editor list unless Uzayr asks.
