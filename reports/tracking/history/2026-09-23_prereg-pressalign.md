# Pre-registration: the press-aligned window lattice

**Written 2026-09-23 (batch 23c, item 2), before any press-aligned number exists.** The cut and the
head inference were built and verified first (they produce no figure); the shipped-lattice
measurement was started as the reproduction check. No press-aligned lock, tracking or hold figure
has been computed when this is written. Operator instruction 3, verbatim in the BRIEF:
*"Time one recording's cut first and report the ETA. Build the new cache in a new location whose
name carries the stride, never overwriting the shipped tree. Then measure the entry hold, the lock
and whole-walk tracking."*

---

## 1. What the arm is

`pipeline/constrained/y4_pressalign.py`. The shipped 0.5 s lattice is ONE grid per recording, so
its phase against each press is arbitrary: the first walk window `lo` starts **0.501 to 0.999 s**
before the press, median **0.782** (measured, 360 passes). The arm re-phases the same lattice PER
PASS, by at most a quarter stride, so that a window STARTS on each press (2 microseconds after it,
see section 6). Window length 2 s, stride 0.5 s, `windows.label_window` and the cutter are the
shipped ones, unchanged. Nothing is retrained: the six frozen heads the render reads (five pool
heads and the DISP_END display head) are re-inferred over the new windows from COPIED weights.

**Isolation:** windows in `runs/constrained/windows_s0.5_pressalign`, artefacts in
`runs/artefacts_s0.5_pressalign_{shared,half,fh1s,g1s1,g1s2,g100,dispend}`. Every name carries the
stride; `assert_not_shipped` refuses any write inside a shipped tree or any path without it.

**Verified before this was written:** one recording cuts in 29.7 s (18 recordings about 9 min);
20 of 20 presses land on a window start in the recording checked; the inference path reproduces
the shipped half-stride posteriors to 3e-8 with 100 percent argmax agreement on two recordings.

## 2. What it does to `lo`, stated before measuring, because it is not what the handoff assumed

Under the unchanged labelling rule a window is `walk` when its CENTRE is inside the pass. With a
window starting on the press, the first window whose centre is inside is the one starting
**exactly 1.0 s before** the press. So:

| | shipped lattice | press-aligned |
|---|---|---|
| `lo` start relative to the press | -0.782 median (-0.999 to -0.501) | **-1.000 exactly** |
| pre-press share of `lo`'s radio | 39 percent median | **50 percent** |
| window `lo + 2` ends, relative to the lock frame press + 2.0 s | **+0.218 median, +0.001 to +0.499, late on 360 of 360** | **+0.000 on every pass** |

`reports/HANDOFF_2026-09-23.md` motivated this item as removing run-up from the first window. **On
the index semantics every stage uses, it adds run-up to `lo` instead, and what it removes is the
lock's lookahead** (`reports/FINDING_lock_phase_2026-09-23.md`). A lattice where `lo` itself starts
on the press would make the index lock `lo .. lo + 2` read to press + 3.0 s, a full second past the
lock frame, and is not run.

## 3. Predictions, recorded before the run

1. **The lock falls a little.** Its last window now ends a median 0.218 s earlier, exactly at the
   lock frame. Expected -1 to -4 points held-out; the shipped 57.50 is partly lookahead.
2. **The entry hold does NOT improve** and may worsen: `lo` carries more run-up, so the first
   decoded position is at least as likely to be the tape entry.
3. **Whole-walk tracking moves little**: the first decoded frame moves a median 0.22 s earlier and
   the rest of the walk is the same radio re-phased by at most 0.25 s.
4. **The committed answer and the 62.50 headline move by noise only**, within about one pass per
   pairing, because the full-walk decoder reads the same radio.

## 4. What is measured, all nine pairings, session-01 folds shown, key `tag|session|stem|pass_id`

Both lattices through ONE harness (`y4_pressalign measure`), which mirrors `x1_edgedisp`'s
render conventions exactly (LATENCY 2.0, HEAD_OFFSET 0.75, SHIFT_W 0.50, display cap 0.80 m per
window, PRIOR_F 0.50, the DISP_END display path).

- **The lock**: held-out seven median, all nine, edge recall E_col1 / E_col5 / E_row1 / E_row5,
  session-01 folds, and per pass the **wall-clock lock bound**: when the lock's last window ended,
  minus the frame it is drawn on.
- **The committed semi-bounded answer** (`final_line`): same breakdown.
- **The entry hold**, correct-lock walks: share whose first decoded position is within 0.05 m of
  the line entry; mean distance; the decoder's own hold in seconds (leading steps at the first
  state); when the first decoded frame falls after the lock frame.
- **Whole-walk tracking**: within 0.5 m, whole walk and correct-line walks, plus the **early (first
  1.0 s of decoded frames) versus late split** the handoff says was never measured.

## 5. The rules

**Reproduction check, which voids the run if it fails.** The shipped lattice through this harness
must return the lock at **57.50 held-out with edge 42.59 / 77.78 / 35.19 / 57.41** and whole-walk
within 0.5 m **28.2456 over 1077 passes, 53.1045 on 517 correct-line walks** (`x1_edgedisp`).

**The display half** (entry hold, tracking): contract checks plus one measurement. Non-inferiority
as `x1` used: the paired delta's 95 percent interval must not lie entirely below zero.

**The decision half** (lock, committed answer): the lattice changes the emissions, so this is a
decision change and gets the full rule. (a) paired interval on held-out folds entirely above zero,
(b) median paired delta at least two passes per pairing as integers, (d) substitution, both causal
bounds, (f) no edge line degraded, all as written. **(c), monotone response to the arm's weight,
cannot be evaluated: a lattice phase is binary and has no dial.** By the rule as written the arm
therefore cannot ship a decision change in this batch. If everything else passes, it goes to the
operator as a decision, stated as such, exactly as (f) did.

**Substitution** is not re-measured: the decoder, heads and weights are unchanged and read only
CSI. The press positions the lattice, but the semi-bounded mode is already given the press and
defines `lo` from it; no pace, elapsed time or projection enters.

**The causal bound is new and binding for the arm:** every pass's lock must end at or before its
frame, to 1e-5 s. The shipped lattice is reported beside it and does NOT meet it.

## 6. A fault found while building, recorded because it would have voided the result

Aligning a window start EXACTLY on the press put the first window's centre exactly on the press,
and `label_window`'s `t_start <= t_mid` then labelled it `walk` or `walk_edge` by float rounding:
on the first recording **9 of 20 passes put `lo` half a stride late**, which would have made the
arm's lock LESS causal than the shipped one. Starts are now 2 microseconds after the press
(1/3300 of a sample) and the cutter verifies `lo` starts at press - 1.0 s on every pass.
