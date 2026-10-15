# The lock-side A3 decode: checks before it started, 8 October 2026, 20:58 SAST (clock read)

**What runs.** A3's FOURTH look, as Uzayr's reply of 8 October (item 2) orders, after `PREREG_DOT.md` was committed (cdab65c4):
- the live app on A3's six evaluated recordings, once each, model set "final" (fin_A3);
- semi mode (start presses only), the causal clock, the app's display K1g;
- one change, in the replay processes only: the display decode's spread 2.5 (A3_CLEAN_CONFIG.md, lock side, 0d1f47f3...)
  instead of 4.5;
- the soft entry and the 1.0 m window as shipped;
- six niced CPU processes, CPU forced, under `mem_guard.py` (pause below 25 %, resume at 40 %).

**The three confirmations the primary chat asked for:**
1. **Every output path is inside runs/a3_clean_2026-10-08/.**
   - `app_replay.OUT` is redirected to `a3_lock/replay/`, and `app_score.REPLAY` to the same folder for the score.
   - An audit hook (`lock_side.install_guard`) refuses any write outside this folder; each recording's writes are listed
     in `a3_lock/meta/<stem>.json`.
   - The existing A3 record (`runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/`) is only read.
2. **The A3-clean config loads as a separate file.**
   - `a3_replay.py` reads `A3_CLEAN_CONFIG.md` after checking its hash, then sets `display.DISPLAY_SD_SCALE` in its own
     process and checks every LiveDisplay built carries 2.5.
   - `final_model.py`, `display.py`, `app_replay.py`, `app_score.py`, `tracking.py`, `FINAL_CONFIG.md` (and .sha256),
     `runs/live/models/*.json`, the existing A3 replay, the zero-shot replays and the fin_A3 and fin_B2 FC records were
     hashed before: `a3_lock/HASHES_before.json`, 136 files. They are hashed again after.
3. **The model-set check passes on the shipped files:** `python3 -m pipeline.live.model_sets check --model final` gives
   ok, 454 files, none mismatched (`a3_lock/logs/model_set_check_before.json`). Each replay process checks it again
   (`app_replay.session_inner`).

B2 and the zero-shot cell are not decoded.
