# Where the display's settings come from, and what the A3 display figures may claim

**30 September 2026. Part D of Uzayr's instruction of 30 Sep, run as `rule/DISPLAY_PREREG.md`**
(hashed 09:15, `ad7eeb5a...`, before any Part D run on data).

**Nothing is adopted in either outcome.** `rule/FINAL_CONFIG.md`, its hash and every file of the 15:39
model are unchanged.

**Code:** `pipeline/constrained/pd_disp_prov.py`.
**Results:** `runs/dc2_results/display/`.

**The rotations** (the frozen model's rotation form: the `d4c_fuse_*` cells, relgateU + abstain + A2
weight 0.25, the frozen A1+A2 pace, the clean reader map):
- A1+A2 -> B1 (weight 2);
- A1+B1 -> A2 (weight 1);
- A2+B1 -> A1 (weight 1).

## 1. The cap: 0.80 and the training-derived 0.8205 are the same cap

**The training-derived cap** is (pace mean + 3 SD) x 0.5 s = (1.30341 + 3 x 0.11255) x 0.5 = 0.8205 m per
window.

**(a) From the code** (`CAP_MATRICES.json`).
- **Where the cap is read:** in one place, `decoder.MAX_ADVANCE_M`.
- **What it reaches:**
  - the display decode's `transition_matrix2`;
  - the chains' `transition_matrix`;
  - the switching scorer's matrices.
- **The result:** built at 0.80 and at 0.8205, every one of them is bit-identical. At 0.7499 and 0.8212
  they differ.
- **Why:** the along-line steps are 0.25 k m (0.25 k + 0.0711 m on a diagonal's short last step), so any
  cap in [0.75, 0.8211) allows exactly the same steps.

**(b) On the rotations.**

| run | passes | locks equal | drawn paths equal (every field) |
|---|---|---|---|
| offline, A1+A2 -> B1 | 131 | 131 | 131 |
| offline, A1+B1 -> A2 | 120 | 120 | 120 |
| offline, A2+B1 -> A1 | 120 | 120 | 120 |
| the app, A1+A2 -> B1, 6 recordings (every logged output: dots, locks, committed lines, switches) | 120 | 120 | every logged row equal |

`CAP_EQUIVALENCE.json`, `APP_CAP_EQUIVALENCE.json`.

**Outcome:** (a) and (b) both hold. The cap is equivalent to the training-derived value, and **its A3 label is cleared**.

## 2. The spread

**The grid:** sd_scale in {2.5, 3.0, ..., 6.0}, with the cap at 0.80. The objective is the
rotation-weighted display-lock accuracy.

**The precondition held on every rotation:** the app, replayed in legacy mode with the whole-file clock,
equals the offline DT0 decode on every committed line and display lock. A1+A2 -> B1, A1+B1 -> A2 and A2+B1 -> A1: 120 of 120 committed lines and 120 of 120 locks each (`runs/live/final/gate_d4c_fuse_*.json`).

**The curve** (`SPREAD_SWEEP.json`; rotation-weighted display-lock accuracy, percent):

| sd_scale | 2.5 | 3.0 | 3.5 | 4.0 | **4.5** | 5.0 | 5.5 | 6.0 |
|---|---|---|---|---|---|---|---|---|
| weighted | 51.25 | 51.25 | 51.25 | 51.25 | **50.63** | 50.63 | 50.63 | 50.83 |
| B1 | 40.00 | 40.00 | 40.00 | 40.00 | **39.17** | 39.17 | 39.17 | 39.17 |
| A2 | 73.33 | 73.33 | 73.33 | 73.33 | **72.50** | 72.50 | 72.50 | 73.33 |
| A1 | 51.67 | 51.67 | 51.67 | 51.67 | **51.67** | 51.67 | 51.67 | 51.67 |

**The argmax is 2.5,** an exact tie from 2.5 to 4.0, which goes to the smallest spread. It is not 4.5.

**The paired difference of 4.5 against the argmax:** -0.63 points [-2.29, +1.04]. That is one pass fewer
on B1 and one on A2.

**The sweep's 4.5 point** reproduces the offline DT0 decode on 360 of 360 locks.

**Outcome, by the rule:** the spread is not re-derived on training data, and its A3 label stays. The
curve is flat to within one pass per rotation, and nothing is adopted.

## 3. The other settings, traced to the data they were set on

**The rule (DISPLAY_PREREG section 4):**
- A setting chosen on A3's walks, or on data that included A3, keeps the A3 display figures labelled
  OPTIMISTIC, unless a check like sections 1 or 2 clears it.
- Operator decisions are recorded as such.
- A setting that cannot be traced is treated as set on A3.

**What "the nine pairings" means below:** the Room A folds 01->02, 01->03, 02->01, 02->03, 03->01, 03->02,
0102->03, 0103->02 and 0203->01. **Session 03 is A3.**

| setting | value | reads it | where it was set | A3 in that data? |
|---|---|---|---|---|
| latency (V1) | 2.0 s | the dot | operator decision, 22 Sep | no: operator |
| lock time (V3) | press + 2.0 s | the lock | operator decision, 23 Sep | no: operator |
| frame rate | 10 per s | the dot | operator and structural (f3_render's grid) | no: operator |
| display lag | 2 windows draw offset, 0 windows of evidence past the step | the lock and the dot | structural: half a window, the strict causal lag (`night_arms`, 20 Sep) | no: structural |
| cap | 0.80 m per window | the lock and the dot | swept on the 120 walks of the demonstration pairing s0102_to_s03 (A3), git 8590d47 | **yes; cleared by section 1** |
| spread | sd_scale 4.5 | the lock and the dot | introduced with the 3 m/s ceiling, git 0b18ee6, measured on the demonstration pairing (A3) | **yes; section 2** (**not cleared**: the argmax is 2.5) |
| soft entry, 1.0 m entry window | | the lock and the dot | q4_arms: arm A1 selected on the folds 01->02 and 02->01, and SHIPPED only because its paired interval on the seven held-out folds was above zero; those include A3 | **yes** (the ship decision) |
| A2 start term in the lock's decode, weight 0.25 | | the lock | pd_rule on the rotations A1, A2, B1 (28 to 29 Sep) | no |
| head offset | 0.375 s | the dot | PREREG_display_phase_2026-09-24, chosen on s0103_to_s02, whose model was trained on A3 | **yes** (training side) |
| dot phase SHIFT_W | 0.50 strides | the dot | PREREG_dotphase_2026-09-22, the nine pairings | **yes** |
| switch theta | 2.0 | the dot | e1_switch and e2_switch, on the folds 01->02 and 02->01 only | no |
| switch arm C (1 switch, final 1.5 m, radius 1.5 m) | | the dot | e2_switch (PREREG_switching_arms_2026-09-23f), selected over the nine pairings | **yes** |
| display prior | flatten 0.50 on the display head's path | the dot | r3_prior, over the nine pairings (30,033 frames), loosened POST HOC | **yes** |
| display head | DISP_END (final: trained A1+A2+B1; zero-shot: A1+A2) | the dot | the head's training has no A3; the choice of DISP_END (s2_display) was made over the nine pairings | **yes** (the choice) |
| anchor | held at the locked line's entry (the live form of rule 2a, 30 Sep) | the dot's anchor span, excluded from the dot error | a causality fix, not tuned | no |

## 4. The labels

**The A3 lock.** **OPTIMISTIC.**
- **Cleared:** the cap (section 1).
- **Not cleared:** the spread (section 2), although its curve is flat.
- **Also not cleared:** the soft entry that the lock's decode uses was shipped on a paired interval over
  held-out folds that include A3.

**The A3 dot error.** OPTIMISTIC. Several settings the dot reads were chosen on data that included A3:
- the dot phase;
- the head offset;
- switch arm C;
- the display prior;
- the choice of display head;
- soft entry.

No check of the kind in sections 1 or 2 clears them.

**Exact wording for every table that quotes them:**
- **For the lock:** "A3 lock (optimistic: the display spread and the soft entry were chosen on data that
  included A3; the cap is equivalent to a training-derived one)".
- **For the dot error:** "A3 dot error (optimistic: the display's phase, switch arm, prior, head choice,
  spread and entry were chosen on data that included A3)".

**B2 is unaffected.** No display setting was chosen on B2 or on Room B data after B1, so the B2 display
figures carry no label from this report.
