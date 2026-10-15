# Queue item 12, step 1: the radius-free switch (R0) on A3 and B2 (14 October 2026, 19:16 SAST)

**Every cell is confirmed by the committed rule (PREREG.md section 5, 0b58e3d6).** On the deployed model's A3 and B2 and on
the zero-shot model's B2, removing the switch's 1.5 m radius raises W2R minus R2W, and the paired 95 % interval of the share
of frames on the true line lies above zero. No switch goes from the right line to a wrong one, and every lock and committed
line is unchanged. **Nothing ships:** the live app's default stays `clean_1s` with the radius until Uzayr decides.

Development evaluation, all data seen. **A3's tenth look and B2's eighth** (the thesis table's count); R0 was chosen after
the development-rotation result was seen (caac5a6c). Intervals: 95 % percentile bootstrap over walks, 1,000 draws, seed 0,
paired R0 minus R1.5 where marked. Every replay ran on the CPU (`force_cpu()`; `nets.device()` was `cpu` at the start and
end of all 21). Figures from `RESULT.json`.

## The run

- Shipped-file hashes before (6,071 files) at 18:42:19. The decodes ran 18:42:19 to 19:13:57: 21 of 21 rc 0, at most 4
  processes, nice 10, OMP 1.
- **R1.5 check: PASSED** (`REPRO.json`). Deployed A3 PA2, deployed B2 PA2 and zero-shot B2 PA6 under `clean_1s` are
  identical row for row to the 14 Oct CPU 1.0 s logs (1,396, 1,402 and 1,373 rows), so those 18 logs are R1.5.
- **STOP checks: none fired.** Press, lock, committed and true lines are equal on all 360 walks. Every R0 log was drawn with
  `clean_1s_r0` (radius None). R0's render rules: park, together, lock changes and walks over one switch are 0 in every
  cell. **Hashes after step 1** (19:15:36): 6,071 checked, 0 changed.

## The rule, per cell

| cell | walks (lock right) | W2R minus R2W, R1.5 -> R0 (paired) | share on the true line, R1.5 -> R0 (%) | paired difference | verdict |
|---|---|---|---|---|---|
| deployed A3 (f05_A3) | 120 (90) | 0 -> 21 (+21 [14, 29]) | 73.87 -> 84.09 | **+10.22 [6.24, 14.59]** | confirmed |
| deployed B2 (f05_B2) | 120 (86) | 2 -> 21 (+19 [12, 27]) | 69.72 -> 78.53 | **+8.81 [5.35, 13.20]** | confirmed |
| zero-shot B2 (z05_B2) | 120 (69) | 4 -> 26 (+22 [14, 30]) | 57.13 -> 65.95 | **+8.82 [5.23, 12.62]** | confirmed |

## Dot error from the first decoded frame (reported either way)

| cell | all walks, R1.5 -> R0 (m) | paired | correct-lock walks (m) |
|---|---|---|---|
| deployed A3 | 0.372 -> 0.324 | -0.047 [-0.097, -0.023] | 0.246 in both |
| deployed B2 | 0.362 -> 0.314 | -0.048 [-0.093, -0.023] | 0.219 in both |
| zero-shot B2 | 0.499 -> 0.436 | -0.063 [-0.152, -0.030] | 0.247 in both |

Correct-lock walks are unchanged in every cell, because no R0 switch leaves a right line. Every switch R0 adds is on a
wrong-lock walk.

## Switches (raw counts)

| cell | R1.5 W2R / R2W / W2W | R0 W2R / R2W / W2W | slides over 1.5 m, R1.5 -> R0 | walks ending on the committed line, R1.5 -> R0 |
|---|---|---|---|---|
| deployed A3 | 0 / 0 / 2 | 21 / 0 / 5 | 0 -> 23 | 90 -> 112 |
| deployed B2 | 2 / 0 / 1 | 21 / 0 / 3 | 1 -> 20 | 87 -> 107 |
| zero-shot B2 | 4 / 0 / 2 | 26 / 0 / 6 | 0 -> 22 | 73 -> 95 |

The switches differ on 24, 21 and 26 walks (`RESULT.json`, `walks_whose_switches_differ`).

## The edge lines (share on the true line, R1.5 -> R0, %)

| cell | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|
| deployed A3 | 34.04 -> 40.43 | 100.00 -> 100.00 | 100.00 -> 100.00 | 80.39 -> 80.39 |
| deployed B2 | 100.00 -> 100.00 | 100.00 -> 100.00 | 50.00 -> 79.63 | 91.84 -> 91.84 |
| zero-shot B2 | 100.00 -> 100.00 | 45.00 -> 70.00 | 48.15 -> 79.63 | 63.83 -> 65.96 |

No line loses share in any cell. The largest gains are on C_fwd (deployed B2 +38.52, zero-shot +26.87) and D_fwd (deployed
A3 +31.30). The full 12-line tables are in `RESULT.json`.

## PA6's B2 walk 5 (deployed model; true D_rev, locked B_rev, committed D_rev)

| display | switch | line drawn at the end | frames on the true line |
|---|---|---|---|
| 0.75 s (shipped until 14 Oct) | B_rev to D_rev | D_rev | 76.9 % (50 of 65) |
| R1.5 (`clean_1s`, shipped) | none | B_rev | 0 % |
| **R0** | **B_rev to D_rev**, at the same frame as 0.75 s | **D_rev** | **76.9 %** |

The radius-free switch restores the correction the 1.0 s head offset lost.

## Worth knowing before any decision

- **Long slides:** 23 of 26 (A3), 20 of 24 (B2) and 22 of 32 (zero-shot) R0 switches move the dot more than 1.5 m in the
  0.5 s slide, against at most 1 under R1.5. A viewer will see the dot cross the room.
- **Wrong-to-wrong switches:** 5, 3 and 6 against 2, 1 and 2.
- The minimum causality margin is the same in both arms.

## Files

`PREREG.md` (+ `.sha256`), `harness.py`, `run.py`, `HASHES_BEFORE.json`, `HASHES_AFTER1.json`, `REPRO.json`,
`RESULT.json`, `run.log`, `step1.out`, `R0/` (18 recordings, each with `.arm.json`: profile, radius, device), `R1.5/` (the 3
check replays), `out/`. Step 2 (the 12 videos) follows on the Mastermind's slot.
