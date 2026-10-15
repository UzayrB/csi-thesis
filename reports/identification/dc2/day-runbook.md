# DC2 identification: the runbook for the rehearsal, both days and the scoring

Written 2026-09-24; rewritten at 17:40 the same day for the both-directions capture decided that
afternoon. Three documents sit above this page:

- **`PREREG_DC2_ADDENDUM_2026-09-24.md`**, with its corrections `..._24b.md` and `..._2026-09-25.md`,
  governs how DC2 is captured wherever the pinned sheets disagree with it;
- **`DC2_DAY_PLAN_2026-09-24.md`** is the field sheet for each person's block, identification then
  tracking (addendum 2026-09-25), and every block is run from it, not from this page;
- the pinned identification sheets (`DC2_ID_PROTOCOL_2026-09-23d.md`, `DC2_ID_FIELD_CARD.md`,
  `DC2_ID_REHEARSAL.md`, `CAPTURE_INTERFACE_NOTES.md`) still hold for everything the addendum leaves
  alone. Their `capture_idpath` commands, the walk on `A_fwd` only and the `data/room_B/session_0<day>`
  folder are superseded. Their identification-first order stands again (addendum 2026-09-25).

**Never run `capture_idpath` for DC2 or the rehearsal.** It writes identification into
`data/room_B/session_01` and `session_02`, the names of Room A's own tracking sessions, and the
tracking session reproduced that folder being scored as Room A. Every identification capture is
`capture_idboth`, which writes to `data/room_B/identification/session_0<day>/`.

Run every command from the repo root as `PYTHONPATH=. /opt/anaconda3/bin/python3 -m <module> ...`,
written `py -m` below, after `export OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE`. `<code>` is a
capture code, which `--plan-day` prints beside its P code; capture codes are never written into a
report. `$NODES` is `"RX1=<port>,RX2=<port>,RX3=<port>"`, each port matched to its MAC with
`make identify PORT=<port>`: RX1 `68:09:47:4c:ef:b4`, RX2 `20:50:0d:1a:28:74`, RX3 `20:50:0d:30:5f:80`.
**Pass `--nodes "$NODES"` on every capture**, because without it the boards are named RX1, RX2, RX3 in
port order and a link can be mislabelled. There is no RX4 at DC2.

**What was checked, at 17:35 to 17:39 on 2026-09-24,** against the files frozen at 17:34:35 in
`runs/IDENTIFICATION_FROZEN_2026-09-24.json` (all 169 pinned files OK; the capture, view and freeze
tests 32 of 32): the capture commands with `--plan-day`, `--dry-run` and `--help`, writing nothing;
the layout check and the view on empty roots in a scratch folder. `--set-spot` was not run, because
it writes the spot file, and nothing was run on the hardware.

## 1. The rehearsal (Thursday 24 or Friday 25 September)

Nothing from the rehearsal is written to `data/room_B`. The practice block leaves out the tracking
walk, whose `ground_truth --room B` command would write there; tracking's stream check is step 9.

1. **Rig as for DC2** (day plan, "Before the first participant", step 1). Tape RX2's outline and
   arrow at home and at both spots.
2. **Cable check.** The 4 m passive cable must reach RX2 at (2.0, -0.5), facing north, with slack.
   If it will not, use (1.5, -0.5).
3. **Record the spot once, before DC2:** `py -m pipeline.identify.capture_idboth --set-spot primary`
   (or `fallback`). It writes `runs/identify/dc2/rx2_spot.json`.
   - Until then every DC2 capture refuses, empty rooms included: "RX2's identification spot has not
     been recorded", exit code 2 (checked). Rehearsal captures do not need it.
   - The spot cannot change once DC2 identification files exist.
4. **Brownout check, 10 minutes at full rate,** with RX2 on the 4 m run at the spot:
   `py -m pipeline.io.capture_logger --duration 600 --nodes "$NODES" --out data/rehearsal_idpath/soak --reset`.
   There must be no brownout or reboot lines, and RX2's rate and loss must match RX1's and RX3's in
   `py -m pipeline.identify.rehearsal_check`, section `link_health`.
5. **One practice block**, walked by Uzayr under any one capture code, in the day plan's order
   without the tracking walk. Every command carries `--rehearsal` and writes to
   `data/rehearsal_idpath/session_01/`, with `_REHEARSAL` in every name.
   1. RX2 to the spot, facing north, aligned, photographed, time noted.
   2. `py -m pipeline.identify.capture_idboth --rehearsal --empty --position idspot --participant <code> --day 1 --move-time HH:MM --nodes "$NODES"`.
   3. Natural, 5 cycles, which is 10 passes, 5 each way (`--passes` counts cycles):
      `py -m pipeline.identify.capture_idboth --rehearsal --participant <code> --day 1 --block natural --passes 5 --height-cm <cm> --weight-kg <kg> --shoes "<text>" --clothing "<text>" --nothing-carried --nodes "$NODES"`.
      **It must end with exit code 0 and no REFUSED line.** The capture counts the `A_fwd` and
      `A_rev` passes in the real `.gt.json`, so this is the first check on the hardware that walk mode
      labels both directions the way the view expects.
   4. The two pace blocks, 2 cycles each, in the order `--plan-day --day 1` prints for that code: the
      same command with `--block slow --passes 2` or `--block fast --passes 2`. They are added
      because day 1 now has pace blocks, and they show whether a slow pass stays under 12 s and a
      fast one over 1.5 s. The capture refuses a pace block before natural (checked).
   5. RX2 home, facing east, aligned, photographed, time noted.
   6. RX2 at home: `py -m pipeline.identify.capture_idboth --rehearsal --empty --position home --participant <code> --day 1 --move-time HH:MM --nodes "$NODES"`.
6. **Layout and signal.**
   - `py -m pipeline.identify.rehearsal_check` lists the rehearsal recordings, sidecars and pass
     counts. In its `rx2_modulation`, TX-RX2's gait or Doppler ratio against its empty room must be
     at least 2; if RX2 is flagged FLAT (exit code 1), raise it before DC2. TX-RX1 may read flat in
     the Doppler band, because line A is its line of sight.
   - `py -m pipeline.identify.id29_dc2_score --check-layout --data-root runs/identify/dc2_view/room_B`,
     before any DC2 data exists, must list the 48 pre-registered recordings as missing and nothing
     else. Until `--set-spot` has run it shows 49 problems, the 49th "RX2 spot not recorded". Both
     were seen on an empty root (exit code 1, as expected while recordings are missing).
   - `py -m pipeline.identify.idboth_view` must refuse, "no identification capture at
     data/room_B/identification", exit code 2, and write nothing: `data/room_B` holds no
     identification yet.
7. **Doppler check:** `py -m pipeline.identify.rehearsal_doppler_check`.
   - It prints the 10 to 40 Hz power of the walks over the empty room at the spot, per link, and
     writes spectrograms to `runs/identify/rehearsal_doppler/`. It reads every pass of at least 1 s,
     in both directions; F for TX-RX2 is 0.981 either way.
   - **What you want:** "RX2 exceeds its empty-room floor by more than x2 in every walk: YES", exit
     code 0.
   - **If it says NO,** raise it before DC2. It is a REHEARSAL DIAGNOSTIC and changes no analysis.
8. **Archive.** Once steps 4 to 7 have run, move `data/rehearsal_idpath/` out of `data/`, to
   `runs/identify/rehearsal_archive/<date>/`, so `data/` holds only the collections. This departs
   from step 7 of the pinned rehearsal sheet, by the 24 September brief's instruction.
9. **Tracking still works,** with RX2 home and facing east: `make run DURATION=20 NODES="$NODES"`.
   Every link must show packets at about the transmit rate.

**If the rehearsal finds a fault in the capture code,** it is fixed before any Room B data exists
under a new dated freeze that supersedes 2026-09-24, never by editing the frozen files (addendum,
section 5).

**Record, on the day:**

- the spot and the cable slack;
- the soak rates and loss per link;
- brownouts;
- the natural block's exit code, and its count (5 `A_fwd`, 5 `A_rev`);
- the slow and fast pass durations;
- the RX2 modulation and Doppler ratios;
- the tracking check.

Write them here, because the pinned rehearsal sheet cannot be edited:

## 2. Each person's block: run it from the day plan

The block is `DC2_DAY_PLAN_2026-09-24.md`, "Each participant", steps 1 to 8: RX2 to the spot, the
empty room there, the identification walks, RX2 home, the empty room at home, then the baseline and
tracking, then the day check. Every identification command is there. What identification needs from
those steps:

- **The home empty room closes the identification part,** straight before that person's baseline and
  tracking, so it is recorded in the placement that person then tracks in, as sheet 23d had it. Its
  `--move-time` is when RX2 was put home (step 4); the spot's is when RX2 reached the spot (step 1).
- **A cycle** is a pass away from the TX (`A_fwd`) and a pass back (`A_rev`). Stand still 5 s at the
  0 m mark facing north; walk away, pressing at 0, 1, 2, 3, 4 and 5 m; stop just before RX1, turn and
  stand still 5 s; walk back, pressing at 5, 4, 3, 2, 1 and 0 m; stop at 0 m without touching the TX
  or RX2, and turn to face north. Walk mode closes a pass on its sixth press. The pre-registered
  analyses read only the `A_fwd` passes and use their first and last presses.
- **Every pass lasts 1.5 to 12 s,** in both directions. The scorer refuses an `A_fwd` pass outside
  that, so a slow walker keeps moving (at least about 0.5 m/s).
- **Blocks run natural first, then the printed pace order, on both days;** the capture refuses any
  other order. Day 1 is natural 10, then slow 5 and fast 5 cycles; day 2 is 5, 5 and 5.
- **Nothing is overwritten:** the capture refuses to record a block or an empty room that already
  exists.

## 3. The order

`py -m pipeline.identify.capture_idboth --plan-day --day 1` gives P1 to P6 and `--day 2` gives P6 to
P1, each with its blocks and cycles. Checked: odd P codes walk slow before fast and even P codes fast
before slow, on both days.

## 4. When something goes wrong

- **A bad pass** (a stumble, the wrong line, someone entering, a stop mid-walk): press `x` straight
  away. During a pass it restarts that pass; straight after a pass closes, before the next begins, it
  discards that pass and reopens it. Either way the walker goes back to that pass's own start: the
  0 m mark for a pass away, the 5 m mark for a pass back.
- **A missed or extra press:** press `x`. Walk mode flags a pass with the wrong press count, and the
  first and last presses must be right.
- **A brownout** (a link stops, or the board reboots): press `q`. The presses so far are kept.
  - Re-seat the cable and hub, and check the stream as in section 1, step 9.
  - The block now holds fewer passes than planned, and a block counts as complete only when both
    directions reach the plan. At a terminal the capture asks for the reason at once; otherwise it
    prints REFUSED and exits with code 3. Log why with the same command plus
    `--amend-count-reason "<text>"`.
- **A participant has to leave:** log it with `--amend-count-reason` on the unfinished block. What
  each block feeds decides what a gap costs:
  - **the pre-registered analyses (P1 to P6 and P1-GP) need, per person:** day 1 natural and both
    empty rooms; day 2 natural, slow, fast and both empty rooms. If any of these 48 recordings is
    missing, `id29_dc2_score` refuses to score anything, and a new pre-registered addendum is needed
    before scoring. Record at least one cycle in every one of them if at all possible;
  - **day 1 slow and fast** are outside the pre-registered set and feed only the secondary P7. A
    missing one there does not stop P1 to P6.
- **Never overwrite or re-record.** A block is never re-recorded after its day without a reason
  logged first in the day's notes, and no DC2 file is ever deleted, renamed or moved.

## 5. After DC2: score once, in this order

Tracking's scoring is in the day plan's last section. For identification:

1. **The P1-REV and P7 code must exist first.** Done on 2026-09-28: `pipeline/identify/idsec_dc2_score.py`
   and `idsec_view.py`, tested on synthetic data and hashed with addendum E and the press relabel in
   `runs/IDENTIFICATION_FROZEN_2026-09-28.json` (which references the 2026-09-25 freeze), before any
   identification figure was computed. If that freeze does not exist, stop here: step 5 computes
   identification figures.
2. **Verify the frozen files:**
   - `shasum -a 256 -c <(grep -v '^#' reports/PINNED_FILES.txt | awk '{print $1"  "$2}')` must
     print OK for every line;
   - `py -m pytest tests/test_addendum_d_hash.py tests/test_freeze_2026_09_24.py tests/test_freeze_2026_09_28.py -q`
     must pass.

   Both scorers also check the pre-registration and addenda B and C themselves.
3. **Build the relabelled source, then the views, once.** Addendum E section 6 relabels one pass, as
   metadata that never touches `data/`:
   - `py -m pipeline.identify.idrelabel` builds `runs/identify/dc2_src_relabelled/identification/`
     from the frozen manifest `runs/identify/dc2/relabel_manifest.json`: every file a link into
     `data/room_B/identification/` except the one rewritten `.gt.json`. It refuses if that capture
     file changed since the manifest.
   - `py -m pipeline.identify.idboth_view --src runs/identify/dc2_src_relabelled/identification` writes
     `runs/identify/dc2_view/room_B/`. It should report 48 recordings included; the excluded list holds
     the 12 day 1 slow and fast recordings, each with its reason. Every walk keeps its `A_fwd` passes
     only.
   - `py -m pipeline.identify.idsec_view` writes `runs/identify/dc2_view_sec/room_B/` for P1-REV and
     P7: 36 recordings, natural walks with their `A_rev` passes, slow and fast walks with their `A_fwd`
     passes.
4. **Check the layouts:**
   `py -m pipeline.identify.id29_dc2_score --check-layout --data-root runs/identify/dc2_view/room_B` and
   `py -m pipeline.identify.idsec_dc2_score --check-layout`. Both must say `"ok": true`.
5. **Score P1 to P6, once:** `py -m pipeline.identify.id29_dc2_score --data-root runs/identify/dc2_view/room_B`.
6. **Score P1-GP, once:** `py -m pipeline.identify.idgp_dc2_score --data-root runs/identify/dc2_view/room_B`.
7. **Score P1-REV and P7, once:** `py -m pipeline.identify.idsec_dc2_score`.
8. **Never run a scorer again** without `--rerun-reason "<text>"`, which is logged; the earlier result
   is moved aside, never overwritten. **Never run the identification scorers on `data/room_B`
   itself:** they refuse it at discovery.

**What scoring needs from Room A:** P6 reads `runs/identify/idmax/features/steady_raw.npz` and the
360-file bank in `runs/identify/idmax/bank/`. Both were present on 2026-09-24. Keep them until
DC2 is scored.
