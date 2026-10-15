# POA_DOT: plan of action for the dot side, minimal form. Written 9 October 2026, 07:02 SAST (clock read)

**The authority:** Uzayr's "Second Overall: go on the dot side, minimal, engineering first" (9 Oct, morning).
- **Engineering now:** code, tests, and checks of seconds to minutes.
- **No heavy CPU or GPU** until `runs/MACHINE_STATE.md` says QUIET AND Uzayr says go.
- **The pre-registration is `PREREG_DOT.md` (cdab65c4),** with one addendum (section 4) before any run.

## 1. What changed since PREREG_DOT.md

- **The pool heads are re-shipped at 0.5 s** (`f4d6fa98`, `bba8adc8`; `reports/tracking/2026-10-09_ship_0p5_report_update.md`).
  - Every stage now runs on the rotations' all-0.5 s heads. These are the stride ablation's ALL05 seed set 0, the exact
    shipped recipe and seeds, in `runs/ablations/stride_mix_2026-10-08/runs/<rot>/`:
    - slot `fh1s`: `p05_s3_k0`;
    - slot `g1s1`: `p05_s1_k0`;
    - slot `g1s2`: `p05_s2_k0`;
    - slot `g100`: `g100_05_k0`;
    - slot `half`: the cell's own.
  - The harness loads them per slot in its own process. No cell is edited.
  - The display head, the readers, the gate, the pace and every display setting are unchanged by the ship.
- **The lock side is re-selected by Overall on the new heads today** (ETA about 10:30). Every stage holds it fixed at the
  values in Overall's commit; this chat does not choose them.
- **No DISP_RAW (Uzayr):** the app cannot run it. Stage 1 compares `centre_labelled` (the pooled display) against the
  held-out DISP_END only. Every other stage and rule stays as written, including stages 1 and 2 with switching off.
- **The count of looks at A3:**
  - the 0.5 s ship decoded A3 (its fifth look, `8fd6859b`);
  - Overall's lock-side re-run, if it replays A3, is the sixth;
  - so **the dot side's single A3 decode is A3's seventh look** (sixth if Overall does not replay A3). The addendum and
    every record of it say so.

## 2. Engineering, now (no heavy compute)

| step | what | hours |
|---|---|---|
| E1 | **Held-out display heads, the wrapper** (`heads.py`). `pd_dispend`'s calls on the rotation's training sessions (A1+B1, A2+B1), outputs under `heads/`, assertions on sessions and calibration. B1's rotation reuses `pd_dispend_zs` after a recipe-identity check. A dry run builds the training windows and checks their counts, with no training | 1.0 |
| E2 | **The rotation harness, one variant** (`dot_harness.py`). An app replay of a rotation recording, with outputs redirected and the write guard, and with these swapped in: the pool slots (MIX for P1, ALL05 for the stages), the display head (shipped, held-out, or pooled with no end head), the lock-side values, prior flatten, head offset, SHIFT_W and the switch arm (or off). **The P1 check** (`p1_check.py`) compares the harness log row by row with `runs/live/replay/rot*/semi_disp-K1g_causal/`. Run now on a tiny slice only: one recording cut to its first two walks | 2.5 |
| E3 | **The shared per-frame decode** (`multi.py`). One replay drives one display per variant; the display decode (`night_track` with every variant's emission and flatten in `display_alt_e`) is computed once per frame step and shared, and each variant composes its own frames and writes its own log in `app_replay`'s format. **The P2 check** (`p2_check.py`) shows each variant's rows equal its single-variant replay's. Run now on a tiny slice only. A one-minute profile on the same slice says where the time goes; the CPU figures in section 3 are re-stated if it disagrees | 3.0 |
| E4 | **The measures and the stage rules** (`measures.py`, `stages.py`). s2's gates: dwell drift offline on A1 and A2 grid-dwell windows (`dwell_infer.py` infers the heads there); substitution offline on the captured emissions; causality from the app's margin. The frame measures: jumps over 0.5 m, mean and median error, displacement p95, excess motion, backwards steps, within 0.5 m, signed along-line offset; e2's quantities (time on correct line, W2R, R2W, W2W, end-on-committed agreement, switch events, jumps over 1.5 m). Each stage's rule exactly as PREREG_DOT section 4, with the 95 % rotation-weighted bootstrap | 3.0 |
| E5 | **Unit tests** (`tests_dot.py`). The measures on hand-made logs, each stage rule on synthetic tables (ties, gates, fallbacks), the slot and head loading, the write guard, and the P1 and P2 comparators on a deliberately changed row | 1.5 |
| E6 | **The addendum (section 4) and the run scripts.** The run scripts use one caffeinate, a MACHINE_STATE.md entry, `nice`, `mem_guard.py`, and resume where they stop | 0.5 |
| | **total** | **about 11.5 h** |

## 3. Compute, after QUIET and Uzayr's go

**The basis:** one app replay of one recording is about 12.5 CPU-min (30 Sep). Wall per round of parallel replays is
about 15 min at 3 processes and about 20 min at 6 on a quiet machine.

| step | what | CPU-h | wall at 3 processes | wall at 6 processes |
|---|---|---|---|---|
| C1 | train the two held-out heads (GPU, one at a time) | GPU about 15 min | 15 min | 15 min |
| C2 | P1 in full: the harness at the shipped display on the MIX rotation cells, 18 recordings, every row against the existing replays | 3.75 | 1.5 h | 1.0 h |
| C3 | dwell windows: the held-out heads and the ALL05 pooled heads on A1 and A2 grid-dwell windows (stage 1's gate (i)) | 0.5 | 15 min | 10 min |
| C4 | the five stages, multi-variant: 18 recordings each, at about 1.3 times a single replay | 24 | 10 h | 6.75 h |
| C5 | P2 as pre-registered: every variant against its single-variant replay on one recording per rotation (2 + 5 + 7 + 5 + 4 variants x 3) | 14 | alongside C4: +3.5 h | alongside C4: +3 h |
| C6 | the A3 decode with the full A3-clean configuration (6 recordings) | 1.25 | 45 min | 35 min |
| | **total** | **about 44 CPU-h + 15 min GPU** | **about 16 h** | **about 12 h** |

**The fallback without E3** (every variant its own replay, 20 runs x 18 recordings): about 80 CPU-h, about 30 h at 3
processes and about 20 h at 6.

## 4. What waits on Overall's lock-side result

- **The addendum to PREREG_DOT.md.** It says only:
  - the plan is rebased onto the shipped 0.5 s model (the ALL05 rotation heads, slots as section 1);
  - the lock side is held at the values in Overall's commit `<id>`, named with the values;
  - DISP_RAW is dropped;
  - the count of A3's looks is corrected (section 1).
  It is committed before any run.
- **Every stage replay (C4, C5),** because each holds the lock side fixed.
- **The full A3-clean configuration and the A3 decode (C6).**

Not waiting: the engineering (E1 to E6), the head training (C1) and P1 (C2, which runs at the shipped display on the MIX
cells and tests the harness, not the selection).

## 5. The order once Uzayr says go

1. **Check:** `runs/MACHINE_STATE.md` says QUIET and Uzayr has said go. Then log this run in it, start ONE caffeinate
   for the whole run, and start the memory guard (pause below 25 % free, resume at 40 %).
2. **C1 and C2 together:** the two heads train on the GPU (one at a time) while P1 runs on the CPU. **If P1 fails on any
   row, stop and report;** nothing is selected.
3. **C3**, then **stage 1** (head choice, switching off), with its P2 alongside.
4. **Stages 2 to 5**, in order: prior (switching off), head offset (arm C), SHIFT_W (arm C), switch arm (A, B or C
   against off). Each starts from the previous stage's winner. A failed P2 voids that stage's multi-variant run, and the
   stage is rerun one variant per replay.
5. **The full A3-clean configuration** (Overall's lock side plus the dot side): written to a new version of
   `A3_CLEAN_CONFIG.md`, hashed and committed before A3 is touched.
6. **C6:** A3 decoded once through the live app with it (the shipped f05_A3 heads; the display head as stage 1 chose,
   the shipped DISP_END being A3-free). It is recorded as **A3's seventh look** (or sixth, section 1). The shipped files
   are hashed before and after.
7. **The report to Uzayr:** the A3 dot error, clean against shipped (all walks, correct-lock walks, from the press;
   median, p90, within 0.5 m), and the dot label it leaves, with the exact wording. Then the MACHINE_STATE.md entry is
   closed and caffeinate released.

**Nothing shipped changes in any outcome:** FINAL_CONFIG, the live defaults, the model sets, B2 and zero-shot.
