# The tracking dot's head offset: 1.0 s, chosen by Uzayr over the rule's 0.875 s, and shipped (14 October 2026)

**For the Mastermind's review, before anything goes to the report repository.** Written by Agent1 (Third overall), 14
October 2026; every time below was read from the clock. Every figure is development evaluation, all data seen. A3 and B2
were decoded with the new setting (section 6); the looks are counted in section 10.

**Folder:** `runs/head_offset_2026-10-14/`. **Authority:** Uzayr's prompt `prompt_mastermind_head_offset_1s.md` (14 Oct
09:43) and his decisions in Agent1's chat (`DECISION_1p0.md`, word for word).

## 1. Outcome

- **The rules chose 0.875 s.** On the three development rotations the median dot error from the press fell from 0.387 m
  (the shipped 0.75 s) to 0.326 m (0.875 s) and 0.311 m (1.0 s). 1.0 s was disqualified by the display-only guard fixed
  beforehand: on one A2-rotation walk its drawn line made a switch the shipped display did not (onto the true line), with
  the lock and committed line unchanged.
- **Uzayr chose 1.0 s over the rule's winner** (received in Agent1's chat at or before 12:35:39), after seeing the development results, against that guard. Each
  position is now drawn at its own window's centre, with no glide. It is the third decision of its kind, after the two of
  12 October.
- **On A3 and B2, 1.0 s against the shipped 0.75 s** (decoded on the CPU, the app's own path): every lock and committed line
  identical on all 120 walks of all three tests; correct-lock dot error from the first decoded frame A3 0.304 -> 0.246 m,
  B2 0.313 -> 0.219 m, zero-shot B2 0.326 -> 0.247 m; the dot now leads slightly (B2 +0.063 m [+0.006, +0.117]); B2 loses one
  corrective switch (PA6, PA6, walk 5). Uzayr accepted all of it after seeing it (section 7).
- **Shipped:** the display profile `clean_1s` (the clean display with head offset 1.0 s, everything else unchanged) is the
  live app's default. The earlier profiles reproduce their shipped replays exactly; G2 is EXACT; the pre-flight is ALL ok.
- **A mistake, found and corrected:** the first A3/B2 decode with 1.0 s ran its networks on the GPU (my script skipped the
  app's `force_cpu()`), so it compared 1.0 s on the GPU with 0.75 s on the CPU. It is not used; the corrected run on the CPU
  is (section 6.1).

## 2. The rules, and when they were fixed

| file | what | SHA-256 | commit |
|---|---|---|---|
| `PREREG.md` | arms, data, R0, measures, the choice, the guards, section 7 | 03eb0121... | 8109011c (09:59, before any decode) |
| `PREREG_ADDENDUM_1.md` | rule 2a applies only to walks with an anchor frame (Uzayr's answer, at or before 10:05:48) | 57a5aafe... | 4414eb13 (10:06, before any scoring) |
| `PREREG_ADDENDUM_2.md` | A3's geometry-only sidecars, the 9 Oct documented exception | 383c3237... | 5e8f4eb4 (10:10, before any scoring) |
| `DECISION_1p0.md` | Uzayr's 1.0 s decision and every later decision, word for word | - | 6eac36fc (12:38) and after |

## 3. The development selection (the rules' choice)

**Data and harness.** The three rotations of the 8 to 10 Oct protocol (A1+A2 -> B1 weight 2, A1+B1 -> A2, A2+B1 -> A1), the
all-0.5 s cells `f05r_*`, 18 recordings, 360 walks, semi mode, the causal clock, the networks on the CPU. One setting
changed per arm (`display.sett["head_offset_s"]` on the live app's own session, clean profile); every held setting
asserted on every session. 54 replays, 10:10 to 12:21, all rc 0.

**R0 (the harness reproduces the shipped display):** the 0.75 s arm equals the 9 Oct stage 5 arm A logs on every row
outside the anchor span on 18 of 18 recordings, and its first anchor frame is the locked line's entry exactly on 360 of 360
walks: **PASSES**.

| arm | median from the press, correct-lock (m) | mean signed offset (m) | within 0.5 m (%) | min margin (s) | display-only guard | eligible |
|---|---|---|---|---|---|---|
| 0.75 s (shipped) | 0.387 [0.355, 0.420] | -0.347 [-0.409, -0.288] | 60.5 [56.5, 64.9] | 0.250 | (reference) | yes |
| **0.875 s** | **0.326 [0.297, 0.359]** | -0.192 [-0.256, -0.132] | 66.6 [62.5, 70.9] | 0.125 | holds | **yes, chosen** |
| 1.0 s | 0.311 [0.277, 0.350] | -0.039 [-0.102, +0.021] | 68.2 [64.2, 72.0] | 1.3e-09 | **fails on 1 walk** | no |

Rotation-weighted (2 B1 + A2 + A1) / 4; intervals 95 % percentile bootstrap, 1,000 draws, seed 0, walks within rotations.
Signed offset and within 0.5 m from the first decoded frame. Draw lag at most 0.174 s in every arm, the shipped one included.
Rule 2a: at 0.75 and 0.875 s every walk has an anchor frame and the first is the entry exactly; at 1.0 s no walk has one
(exempt by addendum 1). The live suite passed (48 passed, 1 skipped). **The rules chose 0.875 s** (`SELECTION.json`, c7bb0985).

## 4. Uzayr's override: 1.0 s

Given first to the Mastermind, which paused the 0.875 s A3/B2 decode at 12:32:19 (it had started at 12:23:01 under section
7); recorded word for word in Agent1's chat at 12:38 (6eac36fc), before any code changed. **Why (his words):** each
position is drawn at its own window's centre, the moment it describes, so the marker sits level with the truth, with the
lowest median; it removes the 0.25 s lag and the start glide. **The rule it overrides:** the display-only guard. **His
disclosure:** chosen after the development-rotation results were seen, against a guard fixed beforehand; the third such
decision, after the two of 12 October. **A correction to it:** when it was made, A3 and B2 had begun to be decoded with 0.875
s (4 of 6 A3 recordings and 1 of 6 B2 recordings complete). That decode was stopped on his instruction (killed by PID; its
outputs moved aside unscored, names and hashes in `A3B2_0P875_DISCARDED.json`, 0503cea7).

## 5. Why the switches change: the mechanism, from the code

`switching.decide_walk` lets the drawn line switch (once, arm A) when, at two consecutive decision checks, (i) another
line's score leads the drawn line's by more than theta = 2.0 nats, (ii) that line's current state lies within the radius
(1.5 m) of the **marker's drawn position**, and (iii) the drawn marker has not reached the final 1.0 m of its line. (i) is
the decode and does not depend on the display; (ii) and (iii) read the drawn marker, which the head offset moves. Confirmed
by replaying each walk with decide_walk's quantities recorded (on the CPU; each replay reproduces its reference log).

- **The A2-rotation walk** (PA6's recording, walk 11; true D_rev, locked B_rev, committed D_rev). The lead for D_rev is
  above 2 nats from press + 3.5 s in both arms. At 0.75 s the marker is 1.52 to 1.89 m from D_rev's state to press + 5.0 s,
  and the final zone disables switching at press + 6.5 s: no switch. At 1.0 s the marker is drawn about 0.37 m further along
  B_rev, 1.39 and 1.49 m at press + 4.5 and + 5.0 s: two qualifying checks, a switch B_rev -> D_rev at press + 5.0 s,
  **onto the true line**.
- **B2, PA6 (PA6), walk 5** (true D_rev, locked B_rev, committed D_rev). At 0.75 s the marker is 1.42 m from D_rev's state
  at press + 3.0 and + 3.5 s: a switch B_rev -> D_rev at press + 3.5 s. At 1.0 s it is drawn further along B_rev, 1.16 then
  1.79 m: the persistence breaks; at + 4.0 s the best line becomes E_col5, and when D_rev leads again its state is over 2 m
  away; the final zone disables switching at press + 7.5 s: **no switch, the drawn line stays wrong to the end** (the
  committed line is right).

## 6. A3 and B2 with 1.0 s against the shipped 0.75 s

### 6.1 The first run used the GPU and is not used

The live app's command line calls `force_cpu()` before every replay (`app_replay.py`, lines 378 to 379); my step 4 script
called `replay_inner` directly and did not, so its networks ran on the Apple GPU (mps) while the shipped 0.75 s replays ran
on the CPU. Found at 13:16, when 0.75 s replays through the same path failed to reproduce the shipped logs. That run
(`STEP4_RESULT.json`, 26c0daec) mixed the offset with the device: it showed two lost switches on B2, one of which (PA4,
PA4, walk 5) is the GPU's. It is labelled by `STEP4_INVALID.md` (87dee341) and not used. Its locks and committed lines were
identical even so. The GPU was used against the slot's CPU-only condition, 12:23 to 12:32, 12:47 to 13:05 and 13:13 to
13:16; identification was not running.

### 6.2 The corrected run (the CPU, the app's own path)

First the corrected path reproduced a shipped 0.75 s replay row for row (B2, PA4's recording, 1,437 of 1,437 rows, its walk
5 switch included; `STEP4_CPU_CHECK.json`). Then 18 replays at 1.0 s (13:26 to 13:55, every one on the CPU;
`STEP4_CPU_RESULT.json`, 3cfc6c6d). Paired on the same walks; dot error from the first decoded frame against the truth 2.0 s
earlier (the thesis's measure); 95 % walk-cluster bootstrap, 1,000 draws, seed 0 (the 10 Oct record's, `EDITOR_FIGURES.json`,
whose shipped side reproduces the thesis's current values).

| | A3 (f05_A3) | B2 (f05_B2) | zero-shot B2 (z05_B2) |
|---|---|---|---|
| lock and committed identical | 240 of 240 | 240 of 240 | 240 of 240 |
| correct-lock median, 0.75 -> 1.0 s (m) | 0.304 -> 0.246 [0.207, 0.285] | 0.313 -> 0.219 [0.191, 0.256] | 0.326 -> 0.247 [0.209, 0.294] |
| paired difference (m) | -0.059 [-0.113, -0.004] | -0.093 [-0.137, -0.046] | -0.079 [-0.134, -0.016] |
| all-walks median (m) | 0.407 -> 0.372 [0.308, 0.461] | 0.430 -> 0.362 [0.298, 0.449] | 0.565 -> 0.499 [0.412, 0.649] |
| paired difference (m) | -0.035 [-0.091, +0.023] | -0.069 [-0.120, -0.007] | -0.066 [-0.130, -0.014] |
| correct-lock 90th percentile (m) | 0.836 -> 0.790 | 0.707 -> 0.686 [0.587, 0.765] | 0.766 -> 0.687 |
| within 0.5 m, correct-lock (%) | 74.2 -> 75.8 | 75.5 -> 82.0 [77.6, 85.8] | 74.0 -> 80.3 |
| within 0.5 m, all walks (%) | 57.4 -> 58.5 | 56.1 -> 60.0 [53.3, 66.9] | 45.7 -> 50.1 |
| mean signed offset, correct-lock (m) | -0.268 -> +0.037 [-0.030, +0.106] | -0.249 -> +0.063 [+0.006, +0.117] | -0.255 -> +0.058 [-0.004, +0.118] |
| switches changed | none | 1: PA6 (PA6) walk 5 lost | none |
| render rules (park, together, one lock, at most one switch) | 0 failures | 0 failures | 0 failures |
| rule 2a, retired: first frame from the entry, median / max (m); exactly at it | 0.130 / 1.003; 5 of 120 | 0.090 / 1.140; 6 of 120 | 0.088 / 1.147; 9 of 120 |
| min causal margin (s) | 8.4e-10 | 2.9e-04 | 2.9e-04 |
| draw lag, max (s) | 0.153 | 0.141 | 0.141 |

Median from the press (the selection's measure), correct-lock: A3 0.287 -> 0.246, B2 0.297 -> 0.219, zero-shot 0.308 ->
0.247. The first frame is always on the locked line (within 2e-16 m). The draw lag is unchanged by the offset (0.75 s:
0.153 and 0.141 s). **No stop condition fired.**

**Which videos now show a switch correcting a wrong lock** (the final model; the renders equal these logs, section 9):
B2's PA4 (PA4) walk 5 (E_row5 -> D_fwd) and B2's PA2 (PA2) walk 14 (C_rev -> E_row5). PA6's (PA6) B2 video keeps
walk 11's switch between two wrong lines (A_rev -> E_row5, committed D_fwd right) but no longer walk 5's correction. A3:
no correcting switch (two switches between wrong lines, PA2 walk 17 and PA4 walk 10, as at 0.75 s).

## 7. Uzayr's decisions after seeing the A3 and B2 results

Made on the first (GPU) figures (recorded at or before 13:12:48) and confirmed on the corrected ones ("Go ahead", at or
before 13:58:53), with decision
3 corrected from two lost switches to one (`DECISION_1p0.md`; the Decisions Log in Notion):
1. **Rule 2a is retired at 1.0 s:** the marker first appears on the locked line at its first decoded position, a median of
   about 0.1 m and at most about 1.1 m from the entry, instead of exactly on it.
2. **The slight lead is accepted:** about +0.05 m mean signed offset, B2 +0.063 m [+0.006, +0.117]. His prompt of 09:43
   had preferred a slight lag to a lead.
3. **One lost corrective switch on B2 is accepted:** PA6 (PA6) walk 5.
4. **The guard override of the development selection stands.**

## 8. Shipping (step 5)

| check | result | record |
|---|---|---|
| hashes before | 5,295 shipped files, 13:14, before any code change | `ship/HASHES_BEFORE.json` |
| the profile | `clean_1s` = clean with `head_offset_s` 1.0, the default (`final_model.DISPLAY_PROFILES`) | 19fcaf59 |
| the live suite | 49 passed, 1 skipped (one new test: the empty anchor span) | `ship/TESTS.json` |
| the profiles reproduce | `pre_clean` and `clean` (0.75 s) equal their shipped replays, `clean_1s` the corrected step 4, row for row, one A3 and one B2 recording each (6 of 6) | `ship/REPRO.json` |
| G2 (legacy mode) under `clean_1s` against FCC | EXACT on f05_A3, f05_B2, z05_B2 (committed and lock 120 of 120 each) | `ship/GATE.json` |
| model sets and FINAL_CONFIG | rebuilt for `clean_1s`, files identical; FINAL_CONFIG section 10, re-hashed (0b9073e9...); the 0.75 s versions kept as `*.clean_0p75.*` | `ship/ADOPT.json` |
| the pre-flight | ALL ok | `ship/PREFLIGHT.json` |

**The 1.0 s handling in `display.py`:** with `t_dec0` equal to `park_until` the anchor list is empty; the glide branch
computes its seam and draws nothing (no division: `span0 <= 0` gives 0); every frame from press + 2.0 s is a decoded
position; the margins skip the empty span. Tested (`test_the_1s_offset_has_an_empty_anchor_span_and_an_inert_glide`): no
anchor frame, the frames equal those with the glide switched off, every frame on the locked line, margin at least 0.

## 9. The twelve videos (step 6)

Recorded 14:47:56 to 15:27:00 (`renders.py run`) with the new default profile, into `runs/live/renders_K1gf_1s/`: the final model, semi-constrained, real-time pace, the app's own screen, through the app's command line (CPU), 3 at a time at nice 19, with the Mastermind's LaTeX hold (Uzayr built LaTeX himself meanwhile, by his choice). The 1-minute load: median 4.76, max 6.96 on 10 cores (156 samples). **Every video's log equals its full-speed replay row for row, 12 of 12** (the corrected step 4 logs; `RENDERS.json`). Per video (`runs/live/renders_K1gf_1s/ACCEPTANCE.md`, PA codes):

| test | participant | committed right | lock right | dot median, all walks (m) | dot median, correct-lock (m) | render-rule failures | first frame from the entry, median / max (m) | switches | draw lag max (s) | log equal to the fast replay |
|---|---|---|---|---|---|---|---|---|---|---|
| A3 | PA5 (PA5) | 17 of 20 | 12 of 20 | 0.471 | 0.190 | 0 | 0.168 / 1.000 | none | 0.153 | yes |
| A3 | PA1 (PA1) | 18 of 20 | 17 of 20 | 0.402 | 0.321 | 0 | 0.136 / 1.000 | none | 0.152 | yes |
| A3 | PA2 (PA2) | 18 of 20 | 16 of 20 | 0.227 | 0.148 | 0 | 0.133 / 1.000 | walk 17: A_rev to C_rev (between wrong lines) | 0.130 | yes |
| A3 | PA3 (PA3) | 20 of 20 | 15 of 20 | 0.422 | 0.301 | 0 | 0.121 / 1.000 | none | 0.133 | yes |
| A3 | PA4 (PA4) | 18 of 20 | 14 of 20 | 0.519 | 0.313 | 0 | 0.101 / 1.003 | walk 10: B_fwd to C_fwd (between wrong lines) | 0.138 | yes |
| A3 | PA6 (PA6) | 20 of 20 | 16 of 20 | 0.324 | 0.256 | 0 | 0.190 / 1.000 | none | 0.138 | yes |
| B2 | PA5 (PA5) | 20 of 20 | 15 of 20 | 0.391 | 0.268 | 0 | 0.096 / 1.107 | none | 0.130 | yes |
| B2 | PA1 (PA1) | 19 of 20 | 16 of 20 | 0.294 | 0.225 | 0 | 0.091 / 1.140 | none | 0.132 | yes |
| B2 | PA2 (PA2) | 19 of 20 | 15 of 20 | 0.295 | 0.186 | 0 | 0.082 / 1.063 | walk 14: C_rev to E_row5 (corrects a wrong lock) | 0.133 | yes |
| B2 | PA3 (PA3) | 20 of 20 | 16 of 20 | 0.243 | 0.172 | 0 | 0.087 / 1.000 | none | 0.132 | yes |
| B2 | PA4 (PA4) | 20 of 20 | 13 of 20 | 0.437 | 0.265 | 0 | 0.079 / 1.000 | walk 5: E_row5 to D_fwd (corrects a wrong lock) | 0.141 | yes |
| B2 | PA6 (PA6) | 19 of 20 | 11 of 20 | 0.738 | 0.226 | 0 | 0.193 / 1.024 | walk 11: A_rev to E_row5 (between wrong lines) | 0.127 | yes |

Locks and committed lines are those of the shipped 0.75 s replays on every walk (A3 90 and B2 86 locks right of 120). **The old renders** are kept, renamed `runs/live/renders_K1gf_0p75s` (13 files, identical, 15:27:25), until Uzayr has seen the new ones. **Hashes after** (`ship/HASHES_AFTER.json`): 5,295 shipped files checked, 0 changed (the 13 renamed render files checked under their new name); 31 new files, all expected (the render replay logs and the `*.clean_0p75*` archives).

## 10. Looks

| session | decode | Uzayr's count | the thesis's look table's convention |
|---|---|---|---|
| A3 | 0.875 s, partial (4 of 6 recordings), unscored, set aside | not counted | a partial look, beside the count |
| A3 | 1.0 s on the GPU, not used | not counted separately | a look, disclosed |
| A3 | **1.0 s on the CPU (used)** | **eighth** | ninth (the table counts the 11 Oct re-read as A3's eighth) |
| B2 | 0.875 s, partial (1 of 6 recordings), unscored, set aside | not counted | a partial look |
| B2 | 1.0 s on the GPU, not used | not counted separately | a look, disclosed |
| B2 | **1.0 s on the CPU (used)** | **sixth** | seventh |

The reproduction replays (step 4's check, the mechanism replays, step 5's reproductions, G2) re-run configurations already
decoded and reproduce them row for row; they are not looks.

## 11. Disclosures

1. **The override and the later acceptances** were made after results were seen (sections 4 and 7).
2. **The GPU run** (section 6.1), and the GPU used against a CPU-only slot.
3. **The first launch stopped on its own guard** (A3's geometry-only sidecars), fixed by addendum 2 before any scoring.
4. **The disclosure correction** in section 4 (A3 and B2 had begun to be decoded with 0.875 s).
5. **The margin at 1.0 s is essentially zero** (A3 8.4e-10 s, rotations 1.3e-09 s): the frames read radio that ends at their
   own time, not later. It holds, but with no slack.
6. **MACHINE_STATE:** step 5's start line was written late, at the Mastermind's reminder; one line said nice 0 for G2, which
   ran at nice 10 (corrected in the next line).
7. **Uzayr's original prompt preferred a lag to a lead;** the shipped dot leads slightly (decision 2).

## 12. The Editor list (not applied; the report repository is untouched)

Generated 14 Oct 2026 15:28:46 SAST by `runs/head_offset_2026-10-14/editor_list.py`, against the report repository as it read then (only read, never written). Development evaluation, all data seen. PA codes as the report uses them. For each item: the place, the exact old text (checked against the current file), the new text, and the source of every figure.

### E1. Methodology, the switch paragraph (Chapters/Methodology.tex)

*Why:* Section 5 of the record: the switch reads the drawn marker, so a display setting can change it.  
*Old text (found once):*

```
To correct a wrong lock the drawn line may switch once sliding over 0.5~s to a line whose $J(L)$, without the line prior, has led by over 2~nats at two consecutive checks.
```

*New text:*

```
To correct a wrong lock the drawn line may switch once, sliding over 0.5~s, to a line whose $J(L)$, without the line prior, has led by over 2~nats at two consecutive checks while that line's current state lay within 1.5~m of the drawn marker, and never in the marker's last metre of its line. Because both of these read the drawn marker, the display's timing can change a switch, though never the lock or the committed line.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 5; Code/pipeline/constrained/switching.py, decide_walk

### E2. Methodology, the position-track sentence (Chapters/Methodology.tex; already rewritten for 1.0 s)

*Why:* At 1.0 s there is no glide: the marker first appears at a drawn decoded position on the line, not exactly at the line's start (rule 2a retired, Uzayr). No glide remains in the code (the anchor span is empty).  
*Old text (found once):*

```
Using the first window (-1s to 1s) and its center it places the tracker at the start of the chosen line.
```

*New text:*

```
From the first window ($-1$ to 1~s), centred on the press, it places the marker on the chosen line at its first decoded position, a median of about 0.1~m and at most about 1.1~m from the line's start, with no glide.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (rule_2a_retired_reported: B2 median 0.090 m, max 1.140 m; A3 0.130 m, 1.003 m)

### E3. Methodology, fig:lock-timing (already rewritten for 1.0 s): the caption

*Why:* Optional precision: the dot sits on average 4 to 6 cm ahead, not exactly level (decision 2).  
*Old text (found once):*

```
draws each window's position at its centre, level with the truth.
```

*New text:*

```
draws each window's position at its centre, about level with the truth (on average 4 to 6~cm ahead).
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (signed offset, correct-lock: A3 +0.037, B2 +0.063, zero-shot B2 +0.058 m)

### E4. Results, tab:tracking-headline, footnote a (Chapters/Results.tex)

*Why:* The head offset was changed after A3 and B2 were seen.  
*Old text (found once):*

```
Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks, and the live app now draws that display.
```

*New text:*

```
Every display setting was re-chosen without A3 and the lock and committed line were unchanged on all 120 walks; the live app now draws that display with its head offset raised to 1.0~s after A3 and B2 were seen, which again leaves every lock and committed line unchanged.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 4 and 6.2

### E5. Results, the A3 paragraph after tab:tracking-headline (Chapters/Results.tex)

*Why:* The glide no longer exists, and the A3 figures above (0.304 m) are the 0.75 s display's, no longer the live app's.  
*Old text (found once):*

```
The live app now draws this re-chosen display. Its glide over the first quarter of a second after the lock was changed to start exactly at the locked line's entry, which removes the one render rule the re-chosen settings broke (on 11 of the 120 walks) without moving any decoded position, lock or committed line, so the A3 figures above are the live app's.
```

*New text:*

```
The live app now draws this re-chosen display with one change made after A3 and B2 had been seen: its head offset was raised from 0.75~s to 1.0~s, so that each position is drawn at its own window's centre with no glide (Uzayr's decision, overriding the 0.875~s the pre-registered rule chose on the development rotations). Every lock and committed line is unchanged, and A3's correct-lock dot error falls further, from 0.304~m to 0.246~m [0.207, 0.285], a paired difference of $-0.059$~m [$-0.113$, $-0.004$].
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|03 correct_lock_walks median_m); Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 3, 4 and 6.2

### E6. Results, the dot paragraph before tab:tracking-dot (Chapters/Results.tex)

*Why:* The new dot figures from step 4, measured from the first decoded frame (the table's own measure).  
*Old text (found once):*

```
On B2 its median error is 0.430~m [0.367, 0.503] over all walks, with 56.1\% [50.0, 62.5] of frames within 0.5~m, and on the walks whose lock is correct the median falls to 0.313~m [0.281, 0.344], with 75.5\% [70.7, 80.4] of frames within 0.5~m. A3 is almost the same, at 0.407~m over all walks and 0.304~m [0.271, 0.340] on correct-lock walks.
```

*New text:*

```
On B2 its median error is 0.362~m [0.298, 0.449] over all walks, with 60.0\% [53.3, 66.9] of frames within 0.5~m, and on the walks whose lock is correct the median falls to 0.219~m [0.191, 0.256], with 82.0\% [77.6, 85.8] of frames within 0.5~m. A3 is close, at 0.372~m over all walks and 0.246~m [0.207, 0.285] on correct-lock walks.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json

### E7. Results, the same paragraph: the 90th percentiles (Chapters/Results.tex)

*Why:* The new 90th percentiles.  
*Old text (found once):*

```
on correct-lock walks nine frames in ten lie within 0.71~m on B2 and 0.84~m on A3, whereas over all walks the 90th percentile reaches 2.68~m on both,
```

*New text:*

```
on correct-lock walks nine frames in ten lie within 0.69~m on B2 and 0.79~m on A3, whereas over all walks the 90th percentile reaches 2.65~m on B2 and 2.61~m on A3,
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (p90_m: B2 0.686 and 2.648, A3 0.790 and 2.607)

### E8. Results, the same paragraph: the comparison sentence (Chapters/Results.tex)

*Why:* The comparison that matters now is against the 0.75 s display the app drew until 14 October; the signed offset and the disclosure belong here.  
*Old text (found once):*

```
Compared on the same B2 walks with the display the application drew until 10~October, the clean display puts 5.4 points [0.3, 10.8] more frames within 0.5~m over all walks and leaves the correct-lock walks where they were, with their median moved by only 0.010~m [$-0.046$, 0.058].
```

*New text:*

```
Compared on the same B2 walks with the 0.75~s head offset the application drew until 14~October, drawing each position at its own window's centre lowers the correct-lock median by 0.093~m [0.046, 0.137] and puts 6.6 points [0.8, 12.6] more of those frames within 0.5~m, with every lock and committed line unchanged. The dot, which trailed the walker by 0.25~m, now sits slightly ahead of it, by 0.063~m [0.006, 0.117] on average on B2's correct-lock walks. The head offset of 1.0~s was chosen by the author after the development results were seen, over the 0.875~s the pre-registered rule chose and against a guard fixed beforehand (on one development walk the drawn line made a switch it had not made before), and after A3 and B2 were decoded with it he accepted the slight lead and that one B2 walk (PA6, walk~5) loses the switch that had corrected its wrong lock.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|B2: median diff -0.093 [-0.137, -0.046], within diff +6.555 [+0.756, +12.570], signed offset -0.249 -> +0.063 [+0.006, +0.117]); Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 4, 5 and 7

### E9. Results, tab:tracking-dot, the B2 row

*Why:* Step 4's figures, from the first decoded frame.  
*Old text (found once):*

```
B2 & 0.430 & 56.1 & 0.313 & 0.707 & 75.5 \\
```

*New text:*

```
B2 & 0.362 & 60.0 & 0.219 & 0.686 & 82.0 \\
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|B2)

### E10. Results, tab:tracking-dot, the A3 row

*Why:* Step 4's figures, from the first decoded frame. (Optional: keep the 0.75 s rows as "0.75~s display" rows.)  
*Old text (found once):*

```
A3\textsuperscript{a} & 0.407 & 57.4 & 0.304 & 0.836 & 74.2 \\
```

*New text:*

```
A3\textsuperscript{a} & 0.372 & 58.5 & 0.246 & 0.790 & 75.8 \\
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json (final|03)

### E11. Results, tab:tracking-dot, the caption's intervals

*Why:* The new intervals (the 10 Oct record's bootstrap, which reproduces the old ones exactly).  
*Old text (found once):*

```
B2's figures are 0.430~m [0.367, 0.503] and 56.1\% [50.0, 62.5] over all walks and 0.313~m [0.281, 0.344], 0.707~m [0.645, 0.774] and 75.5\% [70.7, 80.4] on correct-lock walks. For A3 only the correct-lock medians have intervals on record, 0.304~m [0.271, 0.340] with the live app's display and 0.391~m [0.354, 0.435] with the earlier one.
```

*New text:*

```
B2's figures are 0.362~m [0.298, 0.449] and 60.0\% [53.3, 66.9] over all walks and 0.219~m [0.191, 0.256], 0.686~m [0.587, 0.765] and 82.0\% [77.6, 85.8] on correct-lock walks. For A3 the correct-lock median is 0.246~m [0.207, 0.285] with the live app's display, 0.304~m [0.271, 0.340] with the 0.75~s head offset drawn from 10 to 14~October, and 0.391~m [0.354, 0.435] with the display before that.
```

*Source:* Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json; Code/runs/head_offset_2026-10-14/EDITOR_FIGURES.json

### E12. Results, tab:tracking-dot, footnote a

*Why:* The head offset was changed after A3 and B2 were seen.  
*Old text (found once):*

```
Every display setting re-chosen on the development rotations without A3, now the live app's display, with A3's exposure as in \cref{tab:tracking-headline}.
```

*New text:*

```
Every display setting re-chosen on the development rotations without A3, then the head offset raised to 1.0~s after A3 and B2 were seen, the live app's display since 14~October, with A3's exposure as in \cref{tab:tracking-headline}.
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 4

### E13. Results 4.5, the twelve demonstration videos (the per-video figures and the showcase)

*Why:* the videos were re-recorded with the 1.0 s display (`runs/live/renders_K1gf_1s/`); PA6's B2 walk 5 no longer shows a corrected lock; rule 2a is retired.  
*Old text:* the paragraph from "The twelve demonstration videos, one per participant" to "while the committed line stays right." (Chapters/Results.tex, Section 4.5).

*New text:*

```
The twelve demonstration videos, one per participant for A3 and for B2, are recordings replayed through the application with its current display, the head offset at 1.0~s, at real-time pace, semi-constrained with one start press per walk, with the application's own screen recorded, and each video's log equals its replay at full speed row for row. Per video the lock and the committed line are right on 60 to 85\% and 85 to 100\% of A3's walks and on 55 to 80\% and 95 to 100\% of B2's, and the dot's median error is 0.227 to 0.519~m on A3 and 0.243 to 0.738~m on B2 over all walks, and 0.148 to 0.321~m and 0.172 to 0.268~m on correct-lock walks. The render rules hold on all twelve, with no park, together or lock-change failure and no walk with more than one switch, the dot on the locked line on the green marker's first frame, a median of 0.08 to 0.19~m and at most 1.14~m from its entry since the glide is gone, and a draw lag of at most 0.153~s. PA3's B2 video shows the headline session as it usually runs, with every committed line right, 16 of 20 locks and an all-walks dot error of 0.243~m. A switch corrects a wrong lock in PA2's B2 video (walk 14) and PA4's B2 video (walk 5), while PA6's B2 video now shows only a switch from one wrong line to another on walk~11, with the committed line right.
```

*Source:* `Code/runs/live/renders_K1gf_1s/ACCEPTANCE.md`; `Code/runs/head_offset_2026-10-14/RENDERS_TABLE.json` and `RENDERS.json` (every log equal to its full-speed replay). Which video to feature is the Editor's choice: PA3's B2 video was the "as it usually runs" pick; its figures are in ACCEPTANCE.md.

### E14. Results, the latency table's draw lag

*No change:* the draw lag is the same at 1.0 s as at 0.75 s, at most 0.141 s on B2 and 0.153 s on A3 (Code/runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json, draw_lag_s; the renders' ACCEPTANCE.md). The lock frame's median 0.13 s there comes from the 30 Sep streamed run, not touched by this change.

### E15. Results, fig:error-cdf (results_dot_cdf.pdf)

*Its data change:* the cumulative distributions should be redrawn from the 1.0 s logs (`Code/runs/head_offset_2026-10-14/step4_cpu/final/semi_disp-K1gf_causal/`, identical row for row to the live app's renders). Not redrawn here.

### E16. The ledger (Appendices/appendixa.tex, tab:ledger, Tracking): a new row

```
Head offset of the drawn dot, 0.75, 0.875 and 1.0~s
    & Development rotations (A1 and A2 to B1, A1 and B1 to A2, A2 and B1
      to A1), 360 passes, correct-lock walks
    & Median dot error from the press 0.387, 0.326 and 0.311~m (0.311
      $[0.277, 0.350]$); signed offset $-0.35$, $-0.19$ and $-0.04$~m
    & 1.0~s kept by the author over the rule's 0.875~s, against a guard
      fixed beforehand (one walk's switch changed); on A3 and B2 every
      lock and committed line unchanged \\
```

*Source:* `Code/runs/head_offset_2026-10-14/SELECTION.json`; Code/reports/tracking/2026-10-14_head-offset-1s.md, Sections 3 and 4.

### E17. The look table (Appendices/appendixa.tex): new rows

Uzayr's count calls the 1.0 s decode A3's eighth and B2's sixth look; the table's own convention, which counts the 11 Oct re-read as A3's eighth and B2's sixth, makes it the ninth and seventh. Proposed rows, the numbering for Uzayr to choose:

```
    Head offset 0.875~s, stopped part-way, unscored & 14 Oct & (part) & (part) \\
    Head offset 1.0~s, first run on the GPU, not used & 14 Oct & (+1) & (+1) \\
    Head offset 1.0~s, the live app's display & 14 Oct & 9 & 7 \\
    Total, with the dwell ablation and the GPU run & & 11 & 9 \\
```

*Source:* Code/reports/tracking/2026-10-14_head-offset-1s.md, Section 10.

### E18. Discussion and Recommendations

*Nothing to remove:* the report holds no recommendation to extend the head-offset grid (searched Chapters/Discussion.tex, Chapters/Recommendations.tex and the Results for "grid" and "edge of"); the remark "part of the remaining lag is set by the grid range" is only in the 9 Oct Code record, which is not edited.


## 13. Files and commits

Records in `runs/head_offset_2026-10-14/`; code in `pipeline/live/final_model.py` and `tests/test_live_clean_display.py`;
shipped records in `runs/live/final/`, `runs/live/models/`, `runs/dc2_results/rule/`; renders in `runs/live/renders_K1gf_1s/`
(the earlier ones renamed `runs/live/renders_K1gf_0p75s/`). Commits from 8109011c (09:59) to the record's own.
