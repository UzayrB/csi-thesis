# The lock-phase fix: the press-aligned lattice is the ONE lattice

> **CORRECTED 2026-09-23 (freeze 23d, `reports/CORRECTION_drawn_lock_2026-09-23.md`):** every lock figure below decoded the display at `sd_scale` 1.0. The render draws its lock at 4.5. As drawn: grid 55.83, ONE lattice 53.33 held-out, paired -3.10 [-4.88, -0.95]. The comparisons below are like with like and stand as measured.


2026-09-23, batch 23d, item 2. Operator instruction 4 (verbatim in the BRIEF): *"LOCK PHASE FIX
(correctness, not an arm, so the ship rule does not apply). The shipped lock breaks V3 ... Adopt the
press-aligned lattice as the ONE lattice for everything drawn and quoted. Make the live runner align
its windows to the press the same way, and confirm replay decision equality. Remove the strict-xfail
marker deliberately."* The fault: `reports/FINDING_lock_phase_2026-09-23.md`.

## What changed

- **`pipeline/constrained/lattice.py`**, standard library only, is the ONE definition of every tree
  the shipped system reads: the windows, the 0.5 s head, the three 1 s heads, the g100 region head,
  the DISP_END display head, and the shared press phase (`PRESS_EPS_S`, 2 microseconds). The seven
  places that hard-coded the grid trees now read it: the root defaults (`night_common`), the import
  guard (`_guard`, which maps the legacy `artefacts_half` literal onto the active tree), `n2_arms`,
  `sb2_structural`, `g2_multihead.ONE_S_TREES`, `g3_final.G100_TREE`, `s2a_dispend.END_ART`, the
  live runner's heads (`t2_embed`), and `scripts/render_demo.sh`.
- **`TDR_LATTICE=grid`** reproduces every figure quoted before 23d on the trees it was measured on.
  Reproduction only; never shipped.
- **The live engine** (`pipeline/realtime/engine.py`) gained `rephase_to_press`: at the operator's
  press it moves its lattice onto the press phase. The first walk window (press - 1.0 s) has not
  been emitted at the press and its radio is still buffered, so nothing is invented or re-read.
- **The live tracker** (`pipeline/realtime/tracker_live.py`) now locks the render's way, at the
  window that ends at press + 2.0 s, from windows `lo .. lo + 2` only. It had locked at `lo + 4`
  reading two windows past the lock, a different convention from the render.

## Verified

| check | result |
|---|---|
| the default roots, NO root set by hand, reproduce the hand-rooted press-aligned measurement | **1080 of 1080 passes identical in every field** (`y4_pressalign measure --lattice one` against `--lattice pa`) |
| every live-path root resolves to `lattice.py` | `tests/test_one_lattice.py`, 3 tests, in a subprocess with no roots set |
| the lock has finished recording by its frame, on the ONE lattice | **0 of 360** passes late; `tests/test_lock_phase.py`, **strict-xfail marker REMOVED deliberately** |
| the retired grid lattice still shows the fault | 360 of 360 late, kept as a test so the fault stays measured |
| live engine re-phased at each press against the stored ONE lattice, 20 passes | **20 of 20 aligned**, worst start difference 4.2e-7 s against a half-sample tolerance |
| live decisions against offline decisions, same windows, 20 passes | **20 of 20 identical**, lock included |
| live lock's last window against its frame | ends **2.5 microseconds** after press + 2.0 s: the deliberate 2 microsecond press offset, 1/3300 of a sample |
| live compute | 15.8 ms per window median, **31.7x** headroom per 0.5 s stride |
| suite | **1116 passed, 8 skipped, 0 expected failures** |

## Known gap, stated

**Pre-press windows differ in phase between the live engine and the offline tree, by
construction.** The engine can re-phase only AT the press, so windows it emitted before press - 2 s
stay on the previous pass's phase; the offline cutter switches phase at the midpoint between
passes. The shipped A2 start term reads windows ending in [press - 2, press + 1]. The live runner is
still single-head and implements no A2 term, so its decisions are unaffected, and its "pool caveat"
was corrected: the three 1 s heads read the 0.5 s windows, so a live stream CAN feed them. **Before a
live POOLED runner with A2 can equal the render, the offline pre-press windows must be cut the way
the live engine can cut them.**

## What the lock figure is now

On the ONE lattice the lock reads **50.00 held-out** (edge 37.04 / 66.67 / 27.78 / 50.00), against the
57.50 quoted before, which read a median 0.218 s of radio not yet recorded at its frame. Item 4
re-measures it with its interval after item 3.
