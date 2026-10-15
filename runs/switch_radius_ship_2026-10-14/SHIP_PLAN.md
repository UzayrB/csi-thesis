# SHIP PLAN: the radius-free switch becomes the live app's display. Written 14 October 2026, from 20:26 SAST (clock read), before any change

**Status.** Committed before any shipped file changes, with its code (`apply_profile.py`, `ship.py`). Its SHA-256 goes in
`SHIP_PLAN.md.sha256`; never edited afterwards (any change before a step goes in a dated addendum).

**The authority.** Uzayr in the Code agent's chat, 14 Oct after 20:05, on the results of the radius test and its A3 and B2
confirmation: "okay ship it". The decision was made after A3 and B2 were seen (A3's tenth look, B2's eighth), so it is the
fourth decision after results (after 12 Oct twice and 14 Oct's 1.0 s), disclosed as such.

**What ships.** A display profile `clean_1s_r0` in `pipeline/live/final_model.DISPLAY_PROFILES`: `clean_1s` with the switch's
`radius_m` set to None, every other setting unchanged, made `DISPLAY_PROFILE`. This is exactly the profile the radius test
registered in memory (`runs/switch_radius_a3b2_2026-10-14/harness.register_r0`). `clean_1s`, `clean` and `pre_clean` are
kept. Display only: no network, reader, decoder setting, lock or committed answer changes.

## The steps (one job on the Mastermind's slot; CPU only, nice 10, OMP 1, at most 4 processes, 12 GB / 30 % floor)

1. **Hashes before.** SHA-256 of every file under the radius test's hash roots (queue 12's `run.py roots()`) plus `tests/`,
   with only these expected to change: `pipeline/live/final_model.py`, `tests/test_live_clean_display.py`,
   `runs/dc2_results/rule/FINAL_CONFIG.md` and `.sha256`, `runs/live/models/final.json` and `zeroshot.json`,
   `runs/live/final/gate_f05_A3.json`, `gate_f05_B2.json` and `gate_z05_B2.json`.
2. **The code change** (`apply_profile.py`, each replacement matching exactly once): the profile and the default in
   `final_model.py`; the live tests that pin the profiles updated to the new default (the profile equals `clean_1s` but
   the radius; its replay folder is tagged; its spread is 3.0; its model set's files equal `clean`'s). Then **the live
   suite** (`tests/test_live_*.py`) must pass; the code is committed only after it passes.
3. **The profiles reproduce** (8 CPU replays through the app's own replay with an explicit profile, output under this
   folder, write guard): on A3's and B2's PA5 recordings, `pre_clean`, `clean` and `clean_1s` each equal their shipped or
   test replays row for row (as the 1.0 s ship's gate), and **`clean_1s_r0` equals the radius test's step 1 R0 replays row
   for row** (`runs/switch_radius_a3b2_2026-10-14/R0/`). Any difference is a STOP.
4. **G2 under `clean_1s_r0`** (legacy mode, `python -m pipeline.live.final_model gate`, which forces the CPU), against FCC on
   f05_A3, f05_B2 and z05_B2; the current gate files are archived first as `gate_<cell>.clean_1s.json`. EXACT on all three,
   120 passes each, profile `clean_1s_r0`, or STOP.
5. **Adopt:** both model sets rebuilt (files identical to `clean_1s`'s, profile `clean_1s_r0`), the old ones kept as
   `<model>.clean_1s.json`; `FINAL_CONFIG.md` gets section 11 and a header line and is re-hashed, the version before kept as
   `FINAL_CONFIG.clean_1s.md` (+ `.sha256`); the variant and pace unchanged.
6. **Pre-flight:** `python -m pipeline.live.final_model preflight`, every line ok.
7. **Hashes after:** only the expected files changed (new archive files listed, not failures).

**No re-render.** The demonstration videos of the shipped display are `runs/live/renders_K1gf_1s_r0/` (3da9fd3e): each
video's log equals its step 1 R0 replay row for row, and step 3 shows the shipped profile reproduces those replays. The
`clean_1s` videos (`runs/live/renders_K1gf_1s/`) stay until Uzayr has seen the new ones.

## The rule

**Ship only if** step 2's suite passes, step 3 is identical on all 8, step 4 is EXACT on all 3, step 6 is all ok and step
7 shows only the expected changes. **Any failure: STOP**, restore every changed file from its kept copy or `git revert` the
code commit, and tell the Mastermind and Uzayr. A difference is never accepted by the Code agent.

## Then

The record `reports/tracking/2026-10-14_switch-radius.md` (both tests, the ship, the looks and the disclosure), and an
Editor list of exact old and new text (PA codes, unapplied) to the Editors through the Mastermind.
