# H1: offline proofs (15 Oct 2026, written 10:01:19)

- **The live tests** (`tests/test_live_*.py`, nine files; STATE.md's "the live tests"): 09:55:16 to 09:59:00,
  **49 passed, 1 skipped**, rc 0 (H1_tests.txt). The skip is `test_live_truth_isolation.py`'s slow test, which runs only
  with TDR_SLOW=1; run on its own with TDR_SLOW=1 at 09:59:21: 7 passed of 7 in that file, rc 0 (H1_slow_test.txt, 09:59:21 to 10:00:39). Every live test passes.
- **The identification engine diff:** runs/identify/v5/rig_timing_confirm_staged.json (built 2026-10-12 14:47:19, model
  loso_B2_v5, mps, B2 through the real SerialReader and parse_line at 1x, PASSED_exact true) was committed in 27198bad,
  together with the staged extraction's revert; 7df749b3 re-adopted it "identify_engine.py and iv5_rig.py as at
  56eea977, the code that ran in step C". Against 56eea977 (the code that produced the file), at HEAD baddef1f:
  pipeline/identify/engine.py, pipeline/live/identify_engine.py, pipeline/identify/idv2_core.py, idw_core.py,
  idz_core.py and pipeline/identify/iv5_rig.py are all **unchanged** (git diff empty). Against 27198bad itself only
  identify_engine.py differs (+280/-16), which is exactly the re-adoption of 56eea977's staged code.
  **No decision or extraction code changed since the confirmation, so the streamed confirmation is not rerun.**
