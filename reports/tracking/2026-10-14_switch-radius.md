# The switch without its 1.5 m radius condition: test, confirmation and ship (14 October 2026)

**Status:** **SHIPPED** 14 Oct 2026, 21:19 SAST: the live app's display is `clean_1s_r0` (`clean_1s` with the switch's 1.5 m radius condition removed), on Uzayr's "okay ship it" in the Code agent's chat. Display only: every lock and committed line is unchanged.

Development evaluation, all data seen. Every replay ran on the CPU (`force_cpu()`, the device recorded and asserted in every
output). Intervals are 95 % percentile bootstraps over walks (1,000 draws, seed 0), paired (no radius minus radius) where
marked; on the development rotations the walks are resampled within each rotation and the rotations weighted
(2 B1 + A2 + A1) / 4. W2R, R2W and W2W are switches from a wrong line to the true one, from the true line to a wrong one,
and between two wrong lines.

## 1. What changed, and why

The display's one switch (theta 2.0 nats at two consecutive checks, at most one switch, none in the final 1.0 m, a 0.5 s
slide) also required the new line's position to lie within 1.5 m of the drawn dot (`switching.decide_walk`, lines 258 to
261). Uzayr asked the Mastermind (14 Oct, about 17:26) "can you test quickly if removing that 1.5m rule is helpful or not?"
The radius condition is now removed (radius None); nothing else changes. The display changes only what is drawn: no lock or
committed line moves, so every lock and committed-line figure in the thesis stands.

## 2. The selection test on the development rotations

Plan `runs/switch_radius_2026-10-14/PREREG.md` (036ee768, sha256 ff809283), committed before any replay; result
`RESULT.md` (caac5a6c), reviewed by the Mastermind (recomputed from the raw logs). 18 recordings, 360 walks; the head-offset
test's 1.0 s logs reused as the radius arm after 3 check replays reproduced them row for row.

| measure | radius 1.5 m (shipped then) | no radius | paired difference |
|---|---|---|---|
| W2R minus R2W, weighted | 2.75 [1.00, 5.00] | 17.50 [12.75, 22.01] | +14.75 [10.25, 19.50] |
| share of frames on the true line (%) | 53.31 [48.02, 58.79] | 59.28 [54.16, 64.27] | **+5.97 [3.92, 8.16]** |
| dot error, all walks (median, m) | 0.772 | 0.695 | -0.077 [-0.129, -0.036] |
| dot error, correct-lock walks (m) | 0.311 | 0.311 | 0.000 |

Raw switches over the 360 walks: W2R / R2W / W2W 8 / 0 / 5 with the radius, 53 / 1 / 25 without. **The committed rule**
(no radius better only if W2R minus R2W is higher and the paired share interval lies above zero) **chose no radius.** Edge
lines (share on the true line): E_col1 51.78 to 60.33 %, E_col5 62.79 to 71.35 %, E_row1 47.34 to 68.04 %, E_row5 43.93 to
55.43 %; no line lost share. Costs: 55 of the 79 switches without the radius slide the dot more than 1.5 m (3 of 13 with it).

## 3. The confirmation on A3 and B2 (A3's tenth look, B2's eighth, by the thesis table's count)

Plan `runs/switch_radius_a3b2_2026-10-14/PREREG.md` (0b58e3d6, sha256 3f9799e8); result `RESULT.md` (28375754), reviewed by
the Mastermind (recomputed from the raw logs). The radius arm is the 14 Oct CPU 1.0 s replays, reproduced row for row by one
check replay per cell. Locks, committed lines and presses identical on all 360 walks.

| cell | W2R minus R2W (radius -> none) | share on the true line (%) | paired difference | dot error, all walks (m) | verdict |
|---|---|---|---|---|---|
| deployed A3 | 0 -> 21 | 73.87 -> 84.09 | +10.22 [6.24, 14.59] | 0.372 -> 0.324, -0.047 [-0.097, -0.023] | confirmed |
| deployed B2 | 2 -> 21 | 69.72 -> 78.53 | +8.81 [5.35, 13.20] | 0.362 -> 0.314, -0.048 [-0.093, -0.023] | confirmed |
| zero-shot B2 | 4 -> 26 | 57.13 -> 65.95 | +8.82 [5.23, 12.62] | 0.499 -> 0.436, -0.063 [-0.152, -0.030] | confirmed |

R2W is 0 in every cell, so every added switch is on a wrong-lock walk and the correct-lock dot error is unchanged (0.246,
0.219 and 0.247 m). PA6's B2 walk 5 (true D_rev, locked B_rev, committed D_rev) regains the correction the 1.0 s head offset
had lost: the switch to D_rev at the same frame as under the 0.75 s display, 76.9 % of its frames on the true line (0 %
with the radius). Edge lines: deployed A3 E_col1 34.04 to 40.43 %; deployed B2 E_row1 50.00 to 79.63 %; zero-shot E_col5
45.00 to 70.00 % and E_row1 48.15 to 79.63 %; no line lost share in any cell. Costs: 23, 20 and 22 slides over 1.5 m (0, 1
and 0 with the radius); W2W 5, 3 and 6 (2, 1 and 2).

## 4. The demonstration videos

`runs/live/renders_K1gf_1s_r0/` (3da9fd3e; `ACCEPTANCE.md` in PA codes): the 12 videos (deployed model, A3 and B2, semi,
real time, the app's own screen) drawn with the radius-free switch, every log equal to its fast replay row for row, render
rules held on all 12, draw lag at most 0.153 s. Two load spikes from outside the job (19:27, 19:36) and Editor Main's scratch
page counts (19:50 to 19:56, the hold waived by Uzayr in its chat) are recorded there and left no trace in the logs.

## 5. The ship

Plan `runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md` (1bcb5441, sha256 6a7f0db8), committed before any shipped file
changed, following the 1.0 s ship step for step; the Mastermind's slot (queue 14) 20:30.

| step | what | result |
|---|---|---|
| 1 | hashes before | 6,155 files (20:31:40) |
| 2 | the code change (`apply_profile.py`) and the live suite | `clean_1s_r0` added and made `DISPLAY_PROFILE`; the tests' pins updated; 49 passed, 1 skipped; code b3ffc91e |
| 3 | the profiles reproduce (8 CPU replays) | all identical row for row: `pre_clean`, `clean` and `clean_1s` against their shipped or 14 Oct replays, `clean_1s_r0` against the radius test's R0 replays (A3 1,446 rows, B2 1,399) |
| 4 | G2 (legacy) under `clean_1s_r0` against FCC | EXACT on f05_A3, f05_B2 and z05_B2, committed and lock 120 of 120 each (20:47:50 to 21:16:11); the previous gate files kept as `gate_<cell>.clean_1s.json` |
| 5 | adopt | both model sets rebuilt, files identical (452 and 234), profile `clean_1s_r0`, the previous ones kept as `<model>.clean_1s.json`; `FINAL_CONFIG.md` section 11 and header (sha256 c1936474a2ea), the previous version `FINAL_CONFIG.clean_1s.md`; variant and pace unchanged |
| 6 | pre-flight | all ok |
| 7 | hashes after | 9 changed, all expected, 0 unexpected; 7 new (the kept copies) |

Step 3 ties the shipped profile to the radius test's replays, so the videos of section 4 are the shipped display's videos and
nothing was re-rendered. The `clean_1s` videos (`runs/live/renders_K1gf_1s/`) stay until Uzayr has seen the new ones. The
dot figures for the report (`EDITOR_FIGURES.json`, the 1.0 s record's method, whose old side reproduces every current
tab:tracking-dot value): all walks, B2 0.314 m [0.266, 0.367] with 65.9 % [60.3, 71.8] within 0.5 m (was 0.362 and 60.0),
A3 0.324 m and 65.0 % (0.372 and 58.5), zero-shot B2 0.436 m [0.367, 0.506] and 55.5 % [49.5, 62.4] (0.499 and 50.1); the
90th percentile 1.78 m on B2 and 1.55 m on A3 (2.65 and 2.61); correct-lock figures identical.

## 6. Looks and disclosures

- **Looks:** the A3 and B2 decode of section 3 is A3's tenth and B2's eighth look by `tab:test-looks`' count (its total row
  becomes 12 and 10). The ship's reproduction replays (step 3) and G2 gate (step 4) are exactness checks inside those looks
  and add no figure.
- **A decision after results:** Uzayr chose to ship after A3 and B2 were seen (the fourth such decision, after 12 Oct twice
  and 14 Oct's 1.0 s). The selection itself was made on the development rotations by a rule committed beforehand.
- **Costs accepted with it:** about 20 slides per test cell that carry the dot more than 1.5 m in 0.5 s, and more
  wrong-to-wrong switches.
- **The report's description:** Methodology's switch sentence (line 404) never mentioned the radius condition, but its
  next-but-one sentence ("Because both of these read the drawn marker") relied on it: without the radius only the
  last-metre rule reads the drawn marker. Line 404 describes the shipped switch exactly only with the Editor list's E1
  and E1b.

## 7. For the report

The Editor list, exact old and new text in PA codes, not applied: `runs/switch_radius_ship_2026-10-14/EDITOR_LIST.md`.
