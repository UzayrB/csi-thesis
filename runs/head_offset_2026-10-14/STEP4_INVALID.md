# Step 4 is INVALID as a head-offset comparison: its replays ran the networks on the GPU (found 14 Oct, 13:18:00 SAST)

**What happened.** The live app's own command line (`pipeline/live/app_replay.py`, lines 378 to 379) calls
`pipeline.constrained.pd_clean.force_cpu()` before every replay, so the networks run on the CPU; `nets.device()` takes
the Apple GPU (mps) whenever it exists. `step4.py` (and `a3b2.py` and `switch_explain_app.py`) called
`app_replay.replay_inner` directly and did not call `force_cpu()`, so their networks ran on **mps**. Checked: in this
environment `nets.device()` returns mps without `force_cpu()` and cpu after it. The rotation harness (`ho_harness.py`)
does call `force_cpu()`, so the development selection (SELECTION.json, R0 against the 9 Oct logs) is unaffected.

**How it was found.** Replaying B2's PA4 and PA6 recordings at 0.75 s through the same direct path (for the switch
mechanism, `explain/`) did NOT reproduce the shipped 0.75 s replays (`runs/live/replay/final/semi_disp-K1gf_causal/`,
10 Oct, CPU): 64 and 136 rows differ, decoded dot positions from the first differing frame on (PA4 walk 5 at press + 2.76
s: the GPU replay holds the dot at (1.0, 4.5) where the shipped one moves 0.15 m a frame), and the shipped switch on walk 5
of each (press + 3.5 s) is absent at 0.75 s too. The 1.0 s mechanism replays reproduce step 4's logs exactly (both mps).

**What it means.**
- Step 4 compared 1.0 s on the GPU against 0.75 s on the CPU. Its paired dot figures, signed offsets and switch changes
  mix the head offset with the device; they are not the head offset's effect. The two "lost corrective switches" on B2 are
  lost at 0.75 s on the GPU as well, so they are at least partly the device, not the offset.
- Locks and committed lines were identical on 240 of 240 in all three cells even so.
- Uzayr's decisions after the A3 and B2 results (DECISION_1p0.md) were made on these figures.
- The GPU was used (18 step 4 replays 12:47 to 13:05, 4 mechanism replays 13:13 to 13:16, and the discarded 0.875 s
  decode 12:23 to 12:32), although the slot was CPU only; identification was not running.

**Nothing has been shipped:** step 5 was not started (`pipeline/` unchanged, hashes before taken at 13:14).
`STEP4_RESULT.json` is kept as it is, labelled by this file; it is not used.
