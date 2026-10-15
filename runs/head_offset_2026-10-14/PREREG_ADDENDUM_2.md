# PREREG addendum 2, 14 October 2026, 10:09 SAST (clock read): A3's geometry-only sidecars, before any scoring

**Status.** Written and committed before any replay completed and before any arm is scored or any figure read.
`PREREG.md` (03eb0121..., 8109011c) and addendum 1 (57a5aafe..., 4414eb13) stand except where this changes them.

**What happened.** The first launch (10:03:33) stopped on its own guard: every replay that reached the end of its
recording stopped with "inputs naming session 03 or B2 were opened", listing only the six A3 walk sidecars
(`data/room_A/session_03/participant_*_TEST_walk.gt.json`). No B2 file and no other A3 input was listed, and no replay
log was written (each replay checks before it writes). The orchestrator and its replays were stopped by PID at 10:08 to
10:09. Their outputs are kept in `logs/out_stopped_1008/`.

**The cause.** `pipeline.constrained.paths.load_paths` (the room's line geometry) opens every Room A walk sidecar, A3's
included, but takes each line's taped endpoints from the first sidecar naming it, which is session 01's. This is the one
documented exception of the 8 to 10 Oct A3-clean protocol (pd_provenance; the 29 Sep leakage audit, note 1), applied by
`runs/a3_clean_2026-10-08/lock_side.py`: the 9 Oct record states "no input naming session 03 or B2 was read beyond A3's
geometry-only sidecars". PREREG section 2 named that protocol but its guard sentence left the exception out.

## The change to PREREG section 2's guard (the 9 Oct exception, exactly)

1. **Allowed:** an opened path matching `.*/data/room_A/session_03/participant_[^/]+_walk\.gt\.json` (A3's walk
   sidecars, read for geometry), **only if** `lock_side.geometry_from_session_01()` is true in that replay: the twelve
   lines `paths.load_paths` returns equal, exactly, those that session 01's sidecars give alone. If it is false, the run
   stops.
2. **Every other opened input naming session 03 or B2 still stops the run,** as written.
3. Each replay's summary records the A3 sidecars it opened for geometry and the result of the geometry check.

Nothing else changes. The replays are re-run from the start (none had written a log).
