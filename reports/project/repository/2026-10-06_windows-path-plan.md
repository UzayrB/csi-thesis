# Plan: Room A's 1 s windows leave `data/` for good (6 October 2026, 23:37 SAST)

**The instruction (Uzayr, 6 Oct, after the 23:25 move):** "I do not want the windows there in the data so do what
you can to fix this, check the hashes and then reproduce and make sure everything is fine." The 23:25 move left
`data/windows` as a symlink to `runs/constrained/windows_s1.0_roomA/` (`2026-10-06_cleanup.md`). This removes it.

## What changes

1. **The default path, in code** (from `data/windows` to `runs/constrained/windows_s1.0_roomA`), and nothing else
   in these files:
   - `pipeline/constrained/recordings.py`: `WINDOWS_ROOT`'s default (hash-listed);
   - `pipeline/constrained/pd_cells.py`: `A_WIN10` and its docstring line (hash-listed);
   - `pipeline/identify/idmax_common.py`, `tools/calibrate_gate.py`, `tests/test_stride_isolation.py`.
2. **Not changed:** `pipeline/io/windows.py`'s `--out` default stays `data/windows`, because `pipeline/io/` is never
   edited. Any future cut must pass `--out runs/constrained/windows_s1.0_roomA`.
3. **The symlink** `data/windows` is removed.
4. **The hash lists**, as the 1 October restructure did (`tools/pipeline_restructure.py lists`): each of the four
   lists the pre-flight reads (`TRACE_HASHES_{fin_A3,fin_B2,zsf_B2}.txt`, `FINAL_CORRECTED_HASHES.txt`) is kept
   beside itself as `<name>.pre_windows_move.txt`, then rewritten with only the edited code files re-hashed. The
   rewrite REFUSES if any other listed file's hash differs.
5. **The model sets** `runs/live/models/final.json` and `zeroshot.json` are kept as `<name>.pre_windows_move.json`
   and rebuilt with `pipeline.live.model_sets build`.

## The checks, all required before committing

- every file on the four new lists and both new model sets matches its hash;
- the pre-flight: ALL ok;
- the EXACT reproduction (`pipeline.constrained.pd_repro_trace run`) for `fin_A3`, `fin_B2` and `zsf_B2`, one at a
  time on the CPU, each `EXACT: True` with 0 committed, display-lock and scorer-lock changes;
- the live, identification and stride-isolation tests: 55 passed and 6 skipped, as before the change.

**If any check fails:** undo by restoring the `.pre_windows_move` lists and sets, reverting the five code files
with git, and putting the symlink back; then report to Uzayr.
