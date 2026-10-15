# PREREG_DOT addendum 1, 9 October 2026, 07:43 SAST (clock read): rebased on the 0.5 s ship, before any dot-side run

**Status.** Written and committed before any dot-side run. Uzayr's instructions of 9 Oct ("Second Overall: go on the dot
side, minimal" and "Go for the dot side once Overall is done") fix every item below. `PREREG_DOT.md` (SHA-256
c0fc2a7a..., cdab65c4) stands except where this changes it. Nothing here was chosen after seeing any dot-side result:
the only dot-side outputs that exist are the engineering's tiny-slice checks (two walks of one B1 recording), which
select nothing.

## 1. Rebased on the shipped all-0.5 s model

- **Every stage runs on the rotation cells of the shipped recipe:** `f05r_0102_to_B1`, `f05r_01B1_to_02`,
  `f05r_02B1_to_01`.
  - They are built by Overall (commit 2c701274) and registered in memory by `runs/a3_clean_0p5_2026-10-09/reg.py`.
  - Their pool slots hold the stride ablation's ALL05 seed set 0 networks, the exact shipped recipe and seeds: `fh1s` seed
    3, `g1s1` seed 1, `g1s2` seed 2, `g100` seed 0, and `half` the cell's own.
- **The held-out display heads are as PREREG_DOT section 2.** The display head was not changed by the ship.

## 2. The lock side held fixed: Overall's selection on the 0.5 s heads

`runs/a3_clean_0p5_2026-10-09/A3_CLEAN_CONFIG_0p5.md` (commit 2c701274, SHA-256
d942cb16ec221dcd8a9edd0f5530560d1041ba2e7f65a12aa70a5a1f45b7559d), selected under `PREREG.md`:
- **display spread 3.0** (shipped 4.5);
- **display entry soft** (shipped soft);
- **display entry window 1.0 m** (shipped 1.0 m).

Copied into `dot/LOCK_SIDE.json`. This chat did not choose them.

## 3. DISP_RAW dropped

The app cannot run it, so if it won, A3's dot would come from a display the app cannot draw (Uzayr). Stage 1 compares
`centre_labelled` (the pooled emission through the display path) against the rotation's held-out DISP_END only.

## 4. P1: the one stated exception to "every row equal"

- **Why there is an exception.** The reference, `runs/live/replay/rot*/semi_disp-K1g_causal/` (30 Sep, from 19:48), was
  recorded before the Logger fix of 30 Sep 23:30 (commit d12afe72). That fix logs the park frames a start press draws
  directly (`app_replay.Logger`, the `_park_drawn_ahead` hook), so those frames are missing from the reference logs.
- **The exception, exactly:** a dot row present in the harness log and absent from the reference is allowed only if it is
  a PARK frame:
  - its position is the room centre (2.5, 2.5) exactly;
  - its frame time is before its walk's press + 2.0 s, which is "just after a press": the tiny slice found them at press
    + 0.05 s and + 0.15 s.
- **Every other row must match exactly:** every other dot, every lock, committed line, margin, switch and press, with the
  same values, floats included.
- **Anything outside the exception that does not match stops the run,** and it is reported.
- **The slice evidence** (B1, PA5, walks 1 and 2): 129 dot rows in common, all identical; 2 rows only in the harness,
  both park frames as above.

## 5. Switching off in stages 1 and 2: the reason corrected

Stages 1 and 2 run with switching off because the selections they re-make, s2_display and r3_prior (20 Sep), were made
before switching existed (23 Sep). PREREG_DOT section 4 also said "the app's switch is defined only for the DISP_END
display". **That reason is withdrawn:** with no display head the app draws the pooled emission through the same display
path and can switch. Stages 3 and 4 hold arm C; stage 5 chooses the arm.

## 6. SHIFT_W: the tie between two values equally near 0.50

Ties (within 0.01 points) go to the value closest to 0.50. **Between two values equally close, the smaller value wins**
(0.25 over 0.75; 0.00 over 1.00).

## 7. The count of looks at A3

| look | what |
|---|---|
| fifth | the 0.5 s ship's A3 decode (8fd6859b) |
| sixth | Overall's lock-side A3-clean replay on the 0.5 s heads (9 Oct) |
| **seventh** | the single A3 decode with the full A3-clean configuration (lock side plus dot side); every record of it says so |

## 8. How it runs (Uzayr)

- **Resources:** `nice`, 5 CPU processes (3 if Uzayr says the laptop is sluggish), one caffeinate for the whole run, this
  chat's line in `runs/MACHINE_STATE.md` kept current with the stage and ETA.
- **Order:**
  1. the two display heads (GPU, one at a time);
  2. P1;
  3. the offline gates and the five stages;
  4. the full A3-clean configuration, written and committed;
  5. the one A3 decode.
- **It stops and reports** if P1 fails beyond section 4's exception, if any stage errors, or if anything would change the
  shipped app or the model sets.
