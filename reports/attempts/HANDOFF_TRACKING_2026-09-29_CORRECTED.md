# HANDOFF: tracking, 2026-09-29 (evening). The corrected final model

Read `reports/HANDOFF_TRACKING_2026-09-29.md` sections 0, 0b and 5 first: the orientation, the working
rules and how to operate the harness. This file adds what happened after 10:00 on 29 September and the
state at the end of that session.

## 1. Where things stand

**The final tracker is CORRECTED and tested once:** `reports/MODEL_FINAL_TRACKING_CORRECTED.md`.
- **Leak and fix:** a reader leak was found and fixed (`reports/AUDIT_LEAKAGE_TRACKING_2026-09-29.md`).
- **Re-selection:** on the rotations. 8 of 78 rule decisions moved.
- **The configuration** was frozen and hashed before the test (`runs/dc2_results/rule/FINAL_CONFIG.md`,
  sha256 in `FINAL_CONFIG.md.sha256`): the same networks, decoded with relgateU + abstain + A2 weight
  0.25, display lock, pace N(1.30341, 0.11255) from A1+A2.

**The figures, committed / display lock:**

| test | figure | note |
|---|---|---|
| A3 | 93.33 / 70.83 | the lock is OPTIMISTIC: the cap and spread were set on A3 |
| B2 | 93.33 / 72.50 | the headline lock |
| B2 zero-shot (A1+A2 only) | 80.00 / 49.17 | |

The B1 gain on B2 is +13.33 committed and +23.33 lock.

**The old figures stay on record as carrying the leak:** A3 93.33 / 70.83, B2 94.17 / 74.17, zero-shot
83.33 / 49.17 (its readers were already clean).

**Verification:** substitution changes decisions at 0.93 to 1.02 of the ceiling; shuffled radio takes the
committed accuracy to 0.0 to 2.5 percent. The reproductions of the record are exact.

**A3 and B2 have now been decoded three times:** the midpoint, FINAL, and this corrected test (Uzayr's
sanctioned bug-fix re-measurement). The diagnostics of section 3 re-use the same decode. **Any further A3
or B2 figure needs Uzayr.**

## 2. What changed today, in order (the DEVLOG, section VERIFY, has every step)

1. **10:33: the leak.** The start-of-walk readers' B1 training rows came from the frozen DC2 heads
   (A1+A2+A3). On two rotations, the Room A rows came from the validation session's head.
2. **The fix:** `pipeline/constrained/pd_clean.py`.
   - Clean reader rows: heads trained only on the cell's other training sessions, built once into
     `runs/dc2_results/clean_readers/`.
   - Decodes with the clean map go to `cells/<cell>/d3/CR.<variant>` (rotations) and
     `FC.<variant>` (the corrected test).
   - A file trace of every decode.
   - A reader cache keyed by file hashes.
3. **The rotations re-run:** `rule/CR_*`, `CR_CHOICES.md`, `CR_LADDER.md`.
   - Abstain moved: the leak had flattered the veto on its own validation data.
   - Round 1 (`RS_*`) adopted the A2 weight 0.25; round 2 (`RS2_*`) adopted nothing further.
4. **Uzayr's decisions:**
   - D2 stays aug+rrel;
   - round 2 is final;
   - the zero-shot check fails on Room B only;
   - the pace is recomputed on A1+A2;
   - the cap and spread are kept, with the A3 lock labelled optimistic.
5. **The display head (DISP_END)** was retrained on A1+A2+B1 with the final recipe, on the GPU 13:00 to
   13:08 (`pipeline/constrained/pd_dispend.py`, `runs/dc2_results/dispend_final/`).
6. **The one test, 15:41 to 15:45** (`runs/dc2_results/final_corrected_chain.sh`):
   - provenance checks (`pipeline/constrained/pd_provenance.py`, `runs/dc2_results/verify/provenance_*.md`);
   - tables (`runs/dc2_results/final/FINAL_CORRECTED.md`, `ZERO_SHOT_CORRECTED.md`).
7. **Verification:** `pipeline/constrained/pd_subst.py`, `runs/dc2_results/verify/subst/`.
8. **Teaching:** `tools/teaching_pack_corrected.py` wraps the teaching chat's tool, which is unchanged.
   Export: `reports/teaching_pack_corrected_2026-09-29.json`.
9. **Renders:** `pipeline/constrained/pd_render.py`, f3's composition with f4's three changes, written
   to `runs/dc2_results/render_final/<test>/` (videos, RESULTS.json, ACCEPTANCE.md).
10. **The live port:** `pipeline/live/final_model.py`.
    - FinalPool, FinalStartTerms and FinalEndHead;
    - the relative statistics fixed at the first press;
    - `gate`, `preflight` and `rig`.

    `python3 -m pipeline.live rig` now runs the final model by default; the frozen model is available
    with `--model frozen`.
11. **The reproduction from hashes:** `pipeline/constrained/pd_repro.py`, with
    `runs/dc2_results/final/FINAL_CORRECTED_HASHES.txt`.

## 3. Results that arrived after the first draft

All have now arrived; see section 5. They are the renders on A3, the live replay gates and the
reproduction from hashes.

## 4. Open items for Uzayr

1. **The split baseline.** ph_A3 / ph_B2 were decoded with the leaky readers and the old pace, so
   `FINAL_CORRECTED.md`'s paired differences against them mix the fix with the model change. A clean
   baseline would be another A3 and B2 decode of a reference model.
2. **The "decoded accuracy" in the render ACCEPTANCE files is f3 and f4's inherited definition:** the dot
   against the truth 1.0 s before the frame. Under V1's 2.0 s delay, that compares the dot with a moment
   1 s later than the one it depicts, so it is not the decoder's accuracy. The meaningful figures are:
   - the tracking against the delayed marker;
   - the resolution (the dot's error on correct-lock walks, 0.32 to 0.41 m median).

   Whether to redefine it in RENDER_RULES is Uzayr's call.
3. **The cap and spread** were set on A3. A re-sweep on the rotations would remove the "optimistic" label
   from the A3 lock. Not done: Uzayr said keep them.
4. **The rig run on the boards:** `python3 -m pipeline.live preflight --baseline <dir>`, then `rig`. Never
   run by a gate; it opens the serial ports.

## 5. End of session (17:50, 29 September)

**Every item of the task is done.** The chain `runs/dc2_results/final_corrected_chain.sh` ran as one CPU job.
It resumed from the teaching step as `final_corrected_resume.sh`, and its log is
`runs/dc2_results/logs/final_corrected_resume.log`. It finished at 17:49:16 with `FINAL_CONFIG.md`'s hash
unchanged.

| step | result | where |
|---|---|---|
| the one test | A3 93.33 / 70.83, B2 93.33 / 72.50, zero-shot B2 80.00 / 49.17 | report section 1 |
| substitution and shuffled radio | the decisions follow the radio | report section 7 |
| teaching export | plumbing 20 of 20 | `reports/teaching_pack_corrected_2026-09-29.json` |
| renders, A3 and B2 | 12 videos; every RENDER_RULES check passes | report section 8, `render_final/` |
| live replay gates | A3 120/120 and B2 120/120, committed and lock; 94 to 97 ms median per window | report section 9, `runs/live/final/` |
| live pre-flight | passes | report section 9 |
| reproduction from hashes | fin_A3 and fin_B2 EXACT, 0 of 120 changed each | report section 10 |

**Two fixes late in the session:**
- **The pre-flight.** `final_variant()` read a selection file that is never written, and the rig would not
  have set the A1+A2 pace. Now both come from the frozen files, and the pre-flight checks them.
- **The hashed set.** It missed the B1 reader's three position networks. The rebuild reproduced the hashed
  rows exactly, and the files are listed in `final/FINAL_CORRECTED_HASHES_SUPPLEMENT.txt`.

**Committed:** my files, by name. The commit leaves out:
- `pipeline/live/` (TestRig's uncommitted tree, including `final_model.py`), which is committed only when
  Uzayr asks;
- the teaching chat's `tools/teaching_pack.py` and `reports/teaching_pack.json`;
- videos, weights, reader caches, the scratch trees under `verify/repro/`, and the clean rotation
  decodes (`cells/*/d3/CR.*`, 43 MB, regenerable with `pd_clean`).

**Open items, in addition to section 4:**
5. **The zero-shot cell** is not re-decoded from hashes (only fin_A3 and fin_B2 are). It would take about
   15 CPU minutes and produces no new figure: `pd_repro run --cell zsf_B2`, after adding its files to a
   new hash list.
6. **Future hash lists** should take the readers' position networks from the decode's own opened-file
   trace, not from a name pattern.

**Where the next session starts.** Nothing is running for tracking. The GPU and CPU remain
Identification's. Any new A3 or B2 figure would be a fourth look and needs Uzayr.
