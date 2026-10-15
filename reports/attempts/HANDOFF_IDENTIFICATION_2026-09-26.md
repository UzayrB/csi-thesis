# Handoff: IDENTIFICATION, 2026-09-26 22:56 SAST (end of DC2 day 1)

For a new session that works on identification only. Tracking has its own handoff,
`reports/HANDOFF_TRACKING_2026-09-26.md`. Everything below was checked against the files on disk
at the time above; re-check anything you act on.

## Read first, in this order

1. `STATE.md`, section "Identification" (Room A closed: gait at chance across days; pace alone 36.1 %
   on A_fwd).
2. `reports/PREREG_ID_DC2_2026-09-23.md` with addenda B, C and D, and the P1-REV and P7 definitions in
   `reports/PREREG_DC2_ADDENDUM_2026-09-24.md` (from line 119).
3. `reports/DC2_ID_DAY_RUNBOOK.md`, especially section 5, "After DC2: score once, in this order".
4. `reports/PREREG_DC2_ADDENDUM_2026-09-25.md` (identification first, then tracking, per person) and
   `-25_schedule.md` (participants in any order; not pinned).

## Rules that bind you

- Never edit, move or delete a file in `reports/PINNED_FILES.txt`; import frozen code, never change it.
- `data/` is read only for you. The user moves capture files; give the user the command, and never
  one that can overwrite (a new folder per move, `mv -n`).
- On a DC2 day (26 and 27 September) ask before any heavy job or anything that opens a serial port.
  Check `ListAgents` and `git status` first: other sessions work in this repo.
- Commit only when asked, only your own files, by name. `OMP_NUM_THREADS=1`; `date` before writing a
  time; never `pkill` broadly.
- Docs: British spelling, no em dashes. A component is signal-driven only if another participant's CSI
  changes its answer (substitution), never because it runs.

## The capture design

`pipeline/identify/capture_idboth.py`, run through the pre-flight wrapper
`python -m tools.dc2_capture pipeline.identify.capture_idboth ...` (Tracking2's).

- **RX2 position.** RX2 sits at the identification spot, primary (2.0, -0.5), facing north. The spot
  is locked in `runs/identify/dc2/rx2_spot.json`: the code refuses a change once DC2 files exist. It
  was re-run with the same label on 26 Sept at 10:23, which only renewed its date.
- **Cycles.** One cycle is `A_fwd` away from the TX then `A_rev` back, six presses each way.
- **Blocks, in cycles.** Day 1 is natural 10, slow 5, fast 5; day 2 is natural 5, slow 5, fast 5.
  Natural comes first; then odd P codes walk slow before fast and even P codes fast before slow, on
  both days. The capture refuses any other order and never overwrites.
- **Empty rooms.** Per person per day, 30 s each: at the spot before the walks, and at home after
  them.
- **What is scored.** The pre-registered view keeps `A_fwd` only (`idboth_view`). Day 1 slow and fast
  feed only the secondary P7.

## Where DC2 identification stands

**Day 1 (26 Sept) is complete and checked.** `dc2_day_check --day 1 --final` says NOTHING WRONG.

- `data/room_B/identification/session_01/`: 30 recordings. For each of the six (P3,
  P2, P4, P1, P5 and P6, in the order they came; names are kept only under `data/` and `runs/`), there are:
  - empty room at the spot;
  - natural, 20 walks;
  - slow, 10 walks;
  - fast, 10 walks;
  - empty room at home.
- Every recording was checked link by link: RX2 within a few percent of RX1, same start and end, no
  gap over 1 s.

**Day 1 deviations, for the day notes and for any analysis decision.** Everything moved aside is in
`data/room_B/aborted/`, which `idboth_view` and `dc2_day_check` never read.

1. **Participant P3, identification redone after that participant's tracking.**
   - A 10:53 start was aborted with 0 walks.
   - A 10:56 natural block mixed paces: walks 1 to 10 natural (1.25 to 1.42 m/s), 11 to 15 slow (about
     1.0 m/s), 16 to 20 fast (1.6 to 1.8 m/s). The operator had read "10 natural, 5 slow, 5 fast" as
     walks, not cycles.
   - Both files were later OVERWRITTEN by plain `mv` into the same folder, so they are gone. What
     remains in `aborted/` is the original empty-at-spot (10:50) and a 2-walk natural attempt (11:16,
     reason "problem").
   - The final set is empty-at-spot 11:16, natural 11:18, slow 11:21, fast 11:23, recorded with RX2
     moved back to the spot after the 11:04 tracking. The empty-at-home (11:02) is from before.
   - The re-taken empty-at-spot stores its move time as the literal text "HH:MM".
2. **Participant P2.** The first set (11:41 to 11:53) had RX2 dead (header-only files). It is in
   `aborted/<P2>_d1_no_rx2/` and was redone: natural 12:00, fast 12:04, empty-at-home 12:07,
   empty-at-spot 12:21, all with RX2. The slow block (12:16) was recorded after that participant's tracking. Where RX2
   stood during it is NOT confirmed; ask the user.
3. **Participant P4.** A first natural block was moved aside (`aborted/<P4>_d1_natural_redo/`) and
   redone.
4. **Participant P1.** The first empty-at-spot and empty-at-home had RX2 dead. They are in
   `aborted/<P1>_d1_no_rx2/` and `aborted/<P1>_d1_home_no_rx2/`, and were redone.
5. **Participant P6.** The first empty-at-home was recorded with RX2 still at the spot. It is in
   `aborted/<P6>_d1_home_rx2_not_moved/` and was redone.
6. **RX2 hardware.** RX2 goes silent right after being moved (three times on day 1). Tape its cable,
   and check its file sizes or run `make run DURATION=10` after every move.

**Day 2 is 27 Sept:** `--day 2`, files to `session_02`, 5, 5 and 5 cycles, and the real `--move-time`
for each RX2 move.

## Before any identification figure: the scoring order (runbook section 5)

1. **The P1-REV and P7 code must be written first.** It must be tested on synthetic data and hashed
   into a new identification freeze that references `runs/IDENTIFICATION_FROZEN_2026-09-24.json`, all
   before any identification figure is computed. **Not done:** no file in `pipeline/identify/`
   implements P1-REV or P7 (checked 26 Sept). This is the main piece of work outstanding.
2. **Verify the pinned hashes** (`shasum -a 256 -c` on `PINNED_FILES.txt`) and run
   `tests/test_addendum_d_hash.py` and `tests/test_freeze_2026_09_24.py`.
3. **Build the view.** `PYTHONPATH=. python3 -m pipeline.identify.idboth_view` should report 48
   recordings, with the 12 day 1 slow and fast recordings excluded, each with its reason.
4. **Check the layout.** `id29_dc2_score --check-layout --data-root runs/identify/dc2_view/room_B` must
   report `"ok": true`.
5. **Score once each:** P1 to P6 with `id29_dc2_score`, P1-GP with `idgp_dc2_score`, then P1-REV and P7
   with the frozen code. A rerun needs `--rerun-reason`; never score `data/room_B` directly.
6. **Decide before scoring whether deviations 1 and 2 need a pre-registered note:** participant P3's
   identification recorded after that participant's tracking, and participant P2's slow block after theirs.

## Related, already built

`pipeline/live/identify.py` is the live identification mode. It is proved equal to `id29_dc2_score`
on id29's synthetic recordings: 90 of 90 passes' features, and 18 of 18 predictions with
probabilities, plus S0 (`reports/LIVE_SYSTEM_2026-09-25.md`, gate 5). A pass's features settle about
21 s after its end press. It needs an enrolment set (DC2 day 1 natural) before it can run on the rig.

## Uncommitted work

See `reports/HANDOFF_TRACKING_2026-09-26.md`, "Uncommitted work". Nothing identification-specific was
committed after 25 Sept. `runs/identify/dc2/rx2_spot.json` shows as modified only because its date
was renewed.
