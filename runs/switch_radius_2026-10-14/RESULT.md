# Switch-radius test: result (14 October 2026, 18:25 SAST)

**Verdict by the committed rule (PREREG.md section 6, 036ee768): R0 is better.** Removing the switch's 1.5 m radius
condition raises the combined W2R minus R2W from 2.75 to 17.50, and the paired 95 % interval of the share of frames on the
true line lies above zero. **Nothing ships:** the live app's default stays `clean_1s` with the radius until Uzayr says
otherwise, and no A3 or B2 replay was run.

Development evaluation, all data seen: the 18 development-rotation recordings of the head-offset test, 360 walks, weights
(2 B1 + A2 + A1) / 4, intervals 95 % percentile bootstrap, 1,000 draws, seed 0, walks resampled within each rotation,
paired where marked (R0 minus R1.5). Every replay on the CPU (`force_cpu()`, `nets.device()` recorded `cpu` at start and
end in every summary). Figures from `RESULT.json`.

## The run

- Replays 17:34:54 to 18:23:57, 21 of 21 rc 0 (3 R1.5 check replays, 18 R0), at most 4 processes, nice 10, OMP 1;
  the memory guard (checked every 5 s) never fired; at the 21 logged completions the total was at most 3.66 GB and free
  memory at least 47 %.
- **R1.5 reproduction (PREREG section 3): PASSED** (`REPRO.json`). A1 PA1, A2 PA6 and B1 PA3 under `clean_1s` are
  identical row for row to the head-offset test's 1.0 s logs (1,312, 1,378 and 1,358 rows, 2 switches each), so those 18
  logs are R1.5.
- **The STOP check (section 4): passed.** Press, lock, committed line and true line are equal on all 360 walks.

## The rule's two measures

| measure | R1.5 (shipped) | R0 (no radius) | R0 minus R1.5, paired |
|---|---|---|---|
| W2R minus R2W, combined (2 B1 + A2 + A1) / 4 | 2.75 [1.00, 5.00] | 17.50 [12.75, 22.01] | +14.75 [10.25, 19.50] |
| share of frames on the true line, from press + 2 s (%) | 53.31 [48.02, 58.79] | 59.28 [54.16, 64.27] | **+5.97 [3.92, 8.16]** |

Both conditions hold: 17.50 is higher than 2.75, and the share's paired interval lies above zero. The raw form agrees
(W2R minus R2W over the 360 walks: 52 against 8).

## Switches (raw counts over 360 walks)

| | W2R | R2W | W2W | switches | slides over 1.5 m | walks ending on the committed line |
|---|---|---|---|---|---|---|
| R1.5 | 8 | 0 | 5 | 13 | 3 | 228 |
| R0 | 53 | 1 | 25 | 79 | 55 | 282 |

Per rotation (W2R / R2W / W2W): R1.5 B1 3/0/3, A2 3/0/1, A1 2/0/1; R0 B1 18/0/10, A2 18/0/4, A1 17/1/11. The switches
differ on 70 walks (`RESULT.json`, `walks_whose_switches_differ`). The one R2W is A1 PA1 walk 16, where the lock was right
(C_fwd) but the committed line wrong (E_row1); the switch comes in the walk's last 0.5 s and changes 5 frames.

## Dot error from the first decoded frame (reported either way)

| walks | R1.5 | R0 | R0 minus R1.5, paired |
|---|---|---|---|
| all walks, median (m) | 0.772 [0.662, 0.894] | 0.695 [0.601, 0.799] | -0.077 [-0.129, -0.036] |
| correct-lock walks, median (m) | 0.311 [0.278, 0.350] | 0.311 [0.278, 0.350] | 0.000 [0.000, 0.000] |

On correct-lock walks the median does not move. The only correct-lock walk that changes is the R2W walk above, and its 5
changed frames are above the pooled median in both arms (0.71 to 0.78 m before, 1.09 to 2.88 m after).

## Per true line (combined share and median; raw switch counts)

| true line | walks | correct locks | R1.5 W2R/R2W/W2W | R0 W2R/R2W/W2W | share on true line R1.5 -> R0 (%) | median error, all walks, R1.5 -> R0 (m) |
|---|---|---|---|---|---|---|
| A_fwd | 36 | 35 | 0/0/0 | 0/0/1 | 98.37 -> 98.37 | 0.331 -> 0.331 |
| A_rev | 36 | 27 | 0/0/0 | 4/0/0 | 73.72 -> 77.10 | 0.465 -> 0.423 |
| B_fwd | 36 | 11 | 0/0/1 | 5/0/9 | 24.73 -> 28.97 | 1.413 -> 1.392 |
| B_rev | 36 | 23 | 1/0/0 | 5/0/2 | 64.00 -> 65.96 | 0.551 -> 0.541 |
| C_fwd | 36 | 12 | 1/0/0 | 8/1/1 | 28.96 -> 38.87 | 1.266 -> 1.046 |
| C_rev | 36 | 22 | 1/0/0 | 4/0/0 | 61.79 -> 64.24 | 0.518 -> 0.501 |
| D_fwd | 36 | 15 | 0/0/3 | 4/0/4 | 40.78 -> 46.13 | 1.128 -> 1.006 |
| D_rev | 36 | 18 | 2/0/0 | 4/0/4 | 49.07 -> 54.64 | 0.827 -> 0.745 |
| **E_col1** | 18 | 9 | 0/0/1 | 4/0/1 | 51.78 -> 60.33 | 0.889 -> 0.695 |
| **E_col5** | 18 | 11 | 0/0/0 | 4/0/1 | 62.79 -> 71.35 | 0.642 -> 0.562 |
| **E_row1** | 18 | 11 | 1/0/0 | 5/0/1 | 47.34 -> 68.04 | 1.226 -> 0.516 |
| **E_row5** | 18 | 6 | 2/0/0 | 6/0/1 | 43.93 -> 55.43 | 0.988 -> 0.724 |

No line loses share; the four edge lines gain 8.55 to 20.70 points.

## Worth knowing before any decision

- **Long slides.** The radius kept a switch's target near the dot. Without it, 55 of R0's 79 switches move the dot more than
  1.5 m during the 0.5 s slide (3 of 13 at R1.5). No render rule limits this, but a viewer will see the dot cross the room.
- **More wrong-to-wrong switches:** 25 against 5. The rule's net leaves them out, but they are visible changes of line
  that do not help.
- **The display moves towards the committed line:** 282 walks end on it against 228. The lock and committed lines
  themselves are unchanged.
- The minimum causality margin is the same in both arms (1.25e-9 s, at or above the -1e-9 s tolerance).
- **This is selection data only.** Adopting R0 would need Uzayr's go. An A3 and B2 decode would be a further test look in
  each (the numbering is his open item) and needs his word.

## Files

`PREREG.md` (+ `.sha256`), `sr_harness.py`, `run.py`, `REPRO.json`, `RESULT.json`, `run.log`, `replays.out`, `logs/R0/`
(18 recordings), `logs/R1.5/` (the 3 check replays), `logs/out/` (each replay's console output).
