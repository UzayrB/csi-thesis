# POST HOC TOOLING NOTE, 2026-09-28: the corrected day check, and two disclosures

Written 2026-09-28 from 08:05 SAST (clock read), after both days of Room B data existed and before
any model had run on it. **This note changes no model, decision or threshold.**

## 1. The corrected day check, `tools/dc2b_day_check.py`

**The fault.** The pinned `tools/dc2_day_check.py` (line 76) hands the manifest check only the day
being checked. With both days in `data/room_B/calibration.json`, each day's check reports the other
day's folder as missing, although it exists, and both `--final` checks exit 1. Seen on 2026-09-28:
day 1 said `manifest session 'B2' has no folder`, day 2 said the same of B1. Every other line of
both checks was clean.

**The correction.** `tools/dc2b_day_check.py` runs the pinned tool unchanged and swaps in one
function for the length of the run, as `pipeline/constrained/dc2b.py` does for the pipeline. A
manifest session whose folder is missing on disk is still reported, in the same words. Every other
manifest check runs unchanged. The pinned file is not edited (its hash still verifies).
`tests/test_dc2b_day_check.py`, 5 tests:
- the pinned check reproduces the fault;
- the corrected check passes with both folders present;
- it still reports a folder that is truly missing;
- it keeps the other manifest checks;
- it restores the pinned function after the run.

**Result, 2026-09-28 08:04:** `python3 -m tools.dc2b_day_check --day 1 --final` and `--day 2 --final`
both print NOTHING WRONG and exit 0. Logs: `runs/dc2_results/logs/item0_daycheck_day{1,2}.log`.

**The analysis order from now on:**

    python3 -m tools.dc2b_day_check --day 1 --final && python3 -m tools.dc2b_day_check --day 2 --final
    python3 -m pipeline.constrained.dc2b_pipeline --room room_B
    python3 -m tools.dc2_verify_run --room room_B        # VERIFIED, or no figure is read
    python3 -m pipeline.constrained.dc2b_scorerlock --room room_B

## 2. Disclosure: the reaction-time bias was not re-measured on day 2

The day plan asks for `pipeline.io.rt_calibration` before the first participant each day. It ran
on day 1: `configs/operator_rt.json` was written 2026-09-26 10:22, bias 0.041 s, sd 0.044 s, 50
trials. It did not run on day 2. Every Room B walk recording on both days carries that day 1
measurement. The bias is subtracted from every press at labelling time. The previous measurement
was 0.051 s, so a 10 ms change in the operator's bias is the scale at stake. It is reported, not
corrected.

## 3. Disclosure: commit times do not date these records

The 2026-09-25 freeze records, the 2026-09-25 addenda, the pin-list revision and the 2026-09-28
relabel addendum were committed on 2026-09-28, after both days of Room B data existed. **A commit
time does not prove a file predates the data.** For the 2026-09-25 files the evidence is their own
text, which records that `data/room_B` did not exist when they were written, their file dates, and
their hashes in `reports/PINNED_FILES.txt`, all of which verified on 2026-09-28.

## 4. Pinned files

All 191 hashes in `reports/PINNED_FILES.txt` verified on 2026-09-28 at 08:04
(`runs/dc2_results/logs/item0_pins.log`). The freeze tests pass, 13 of 13.

## 5. The DC2 run, one Room B session at a time: `dc2c` (added 2026-09-28 08:15, before item 2 ran)

**The fault.** `dc2_run.do_infer` writes each head's posteriors to one file named by the head tag
alone (`{tag}_g{cells}_e{E}_s{seed}_full.npz`, `dc2_run.py` line 242), rewriting it once per Room B
session. With B1 and B2, the second session's file replaces the first. `pairing_emissions` then reads
that one file for every session, taking its recordings from the file and each recording's labels
from the session being decoded. B1 and B2 hold recordings with the same names, so day 1 would have
been decoded on day 2's radio against day 1's labels. `dc2_verify_run` compares pass lists, which are
identical across the days, so it could not see this. Every earlier run (the stand-ins, the hardware
check) had one Room B session. Found by reading the code before any model ran on Room B.

**The correction** (`pipeline/constrained/dc2c.py`, `dc2c_run.py`, `dc2c_pipeline.py`,
`dc2c_scorerlock.py`; `tests/test_dc2c.py`, 6 tests) changes no model, decision, threshold or arm:
- **One run per Room B session.** The frozen steps (view, cut, features, infer, decode) run once per
  session, exactly as the validated one-session stand-in ran them, each in
  `runs/constrained/dc2_room_B_s0.5_pressalign/by_session/<session>/`. `dc2b`'s three corrections stay
  installed underneath.
- **Merged decode.** The two decodes are merged into that folder's `decode.json`. The report is
  written from it through `dc2b_pipeline` unchanged, and `dc2_verify_run` reads it as before.
- **A new guard.** Every head's posterior file must hold exactly its own session's recordings, and
  every window in it must be dated that session's capture day. The run refuses otherwise.
- **The scorer lock** gets the same per-session treatment, then the frozen outer summary runs on the
  merged file.

**The analysis order from now on:**

    python3 -m tools.dc2b_day_check --day 1 --final && python3 -m tools.dc2b_day_check --day 2 --final
    python3 -m pipeline.constrained.dc2c_pipeline --room room_B
    python3 -m tools.dc2_verify_run --room room_B        # VERIFIED, or no figure is read
    python3 -m pipeline.constrained.dc2c_scorerlock --room room_B
