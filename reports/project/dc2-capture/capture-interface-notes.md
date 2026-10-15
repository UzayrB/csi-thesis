# Capture interface notes: how `walk` mode works, and how the DC2 identification wrapper drives it

Written on 2026-09-23 from a reading of `pipeline/io/ground_truth.py`, `pipeline/io/anchors.py` and
`pipeline/io/capture_logger.py`. **Nothing in `pipeline/io/` was edited.** The wrapper,
`pipeline/identify/capture_idpath.py`, imports the tool's classes and calls them.

## How `walk` mode works

**Choosing the line and direction.** A pass is a `PassStep(path=PathDef, pass_id=n)`.

- A `PathDef` (in `anchors.py` `PATHS`) carries:
  - a name and a compass direction;
  - a cue for the operator;
  - `start_xy` and `end_xy`, which are cues only;
  - exactly `N_ANCHORS = 6` anchor points.
- `main()` builds a shuffled 20-pass `SessionPlan` over the twelve lines (`build_session(seed)`),
  then `build_steps()` orders it.
- The session itself, `GroundTruthSession`, accepts **any list of steps**. Nothing forces 20
  passes or a mix of lines, and the sidecar builder records whatever plan it is given.

**Line A walked away from the TX is `A_fwd`.** In `paths.py` and in `anchors.py` it has direction
`N` and anchors (2.5, 0) to (2.5, 5) at 1 m spacing, starting next to the TX at (2.5, -0.5). Its
recorded `start_xy` is (2.5, -1.5) and its `end_xy` is (2.5, 6.0). Both are cues only: in DC2 the
walker starts wherever the run-up allows and stops just before RX1 at (2.5, 5.5).

**Recording presses.** The space bar is `KEY_MARK`.

- Each press appends one anchor time, on the host monotonic clock minus the reaction-time bias
  (`RtBias`).
- The pass **closes itself on the sixth press** (`N_ANCHORS`), and `validate_pass` flags passes
  with the wrong count or implausible segment speeds.
- `x` redoes the current pass, or the one just closed; `q` aborts.

**So `walk` mode requires a press at every metre, 0 m to 5 m, six per pass.** A two-press pass
would need a path with two anchors. The tool indexes `anchors[n - 1]` for every press up to six,
so a two-anchor path fails on the third press. Presses at every metre are therefore the policy for
DC2 identification. The scorer uses the first press (0 m) and the last (5 m) only.

**Counting passes.** `session.passes` holds the closed passes, and a redo removes one. The sidecar
records `n_passes` and every pass's `t_start`, `t_end` and `anchor_times`, plus `aborted`.

**Naming output.**

- `main()` names files through `session_paths()`, which allows only `grid`, `walk` or `free`
  (`participant_<code>_walk`).
- The two lower-level calls take the name directly: `GroundTruthSession(stem=...)` writes
  `<stem>.gt.json`, and `run_capture(out_dir=..., writer_prefix=f"{stem}_",
  timestamped_subdir=False)` writes `<stem>_RX1.bin` and the rest.
- **The wrapper names outputs directly. No manifest is needed.**

**Driving it programmatically.** The wrapper repeats `main()`'s sequence:

1. `load_rt_bias()`;
2. `parse_positions()`;
3. a `SessionConfig`;
4. `GroundTruthSession(steps=[PassStep(PATHS["A_fwd"], i) ...], plan=SessionPlan(seed, paths), cell_order=CellOrder(seed, ()), ...)`;
5. a `KeyReader`;
6. `run_capture(..., extra_consumers=[session], stop_when=lambda: session.finished, writer_prefix=f"{stem}_", timestamped_subdir=False)`;
7. `session.close()` in a `finally`, as `main()` does, so the presses survive an abort.

**An empty-room recording** is `run_capture(duration=30, ...)` with no session. It produces CSI
only, and the wrapper writes its own sidecar.

## What the wrapper adds

- a JSON sidecar `<stem>.idmax.json` for every recording, holding:
  - RX2's position (the identification spot or home, with coordinates);
  - start and end times;
  - the metadata line;
  - the fixed operator seat at (-1.0, 0.5);
  - the planned and recorded pass counts, and any count reason;
- the block rules:
  - 10 natural passes on day 1;
  - 5 natural, 5 slow and 5 fast on day 2;
  - slow and fast refused on day 1;
  - slow before fast for odd-numbered participants, fast before slow for even;
- a refusal to finish a block whose pass count differs from the plan without a logged reason;
- the RX2 identification spot, recorded once at the rehearsal and refused if changed afterwards;
- `--plan-day`, which prints day 1's order as codes P1 to P6 and day 2's in reverse;
- `--rehearsal`, which writes to `data/rehearsal_idpath/` with a `REHEARSAL` infix. The scorer
  refuses any such file.
