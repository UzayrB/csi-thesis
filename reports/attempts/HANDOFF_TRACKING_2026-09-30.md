# HANDOFF: tracking, the night of 29 to 30 September. Decisions first

Written 30 September 2026, 08:19 SAST. This covers Uzayr's message of 29 September, parts A, B and C (22:39
to 01:33). The day before it is `reports/HANDOFF_TRACKING_2026-09-29_CORRECTED.md`.

**In one line.** The 15:39 model is unchanged and still the result:
- **V2** was tried on the rotations and **stopped by its own rule, with nothing adopted**; A3 and B2 were
  not touched.
- **Every check** asked for passed or was answered.
- **Nothing is running.**

## 1. Decisions for you

| # | decision | options | my recommendation |
|---|---|---|---|
| 1 | **Commit last night's work** (all uncommitted; list in section 3) | (a) commit everything; (b) commit parts A and C now and hold V2; (c) hold all | **(b)**. You asked to review V2 before any V2 commit. Parts A and C are checks and tools that change no model |
| 2 | **V2 option 4**, the lock-time corner term. It helped the lock (+6.25 [2.71, 9.79]; corner-pair lock errors 61 -> 41), but failed the edge guard: E_row5's lock fell from 10 of 18 to 5 of 18, because the NW corner is over-corrected towards D_fwd | (a) accept the stop, and stay on 15:39; (b) pre-register a NEW option (for example, the corner term with a per-corner weight, or not applied to the NW pair), judged on the rotations. If that is adopted, the test would be the **fourth look** at A3 and B2 | **(a) for the thesis.** (b) only if the lock matters enough to spend a fourth look. Re-tuning option 4 itself is ruled out |
| 3 | **The time-step units** (`reports/DT_MISMATCH_2026-09-30.md`). Real in the code, inert on every decision | (a) disclose only; (b) fix it in any future version (it is in V2-B already) | **(a) for the 15:39 model** (it is frozen), **(b)** for anything later |
| 4 | **The render's "decoded accuracy"** (`reports/TRACKING_CHECKS_2026-09-29.md`, 5d). The current figure compares the dot with the truth 1 s AFTER the moment on screen | (a) adopt the proposed definition in RENDER_RULES: the dot against the truth at frame time minus 2.0 s, with the display offset reported apart; (b) leave it | **(a)**. It already exists in the render results as "on-screen tracking against the delayed marker" (43.5 / 48.9 percent within 0.5 m) |
| 5 | **RENDER_RULES 2a's wording** (5b). The first dot sits on the LOCK line's entry, which is causal; the rule says "committed line" | (a) reword it to "the locked line"; (b) leave it | **(a)**. A wording fix; no render changes |
| 6 | **The committed architecture report's section 16** says the null rule's folds were "not traced". They are traced now: A1+A2 only, no A3 (5a) | (a) allow a dated correction note in the report; (b) leave the correction in `TRACKING_CHECKS_2026-09-29.md` alone | **(a)**, a two-line note pointing to the checks file |
| 7 | **The rig run on the boards** | when you choose | Follow `reports/RIG_RUN_PROTOCOL_2026-09-29.md`. It runs the 15:39 model |
| 8 | **The pre-flight's hash list.** It still checks the 133-file name-pattern list | (a) also check the new trace-derived lists (`final/TRACE_HASHES_fin_*.txt`, 267 and 273 files); (b) leave it | **(a)**. A small change to `pipeline/live/final_model.py`, committed separately |
| 9 | **Still open from 29 September** | | |
| 9a | the split baseline, decoded with the leaky readers | a clean re-decode, which would be a fourth look; or keep the caveat | keep the caveat |
| 9b | the display cap and spread, set on A3 | a re-sweep on the rotations; or keep the "optimistic" label on the A3 lock | keep the label |
| 9c | the teaching pack says the labels are "reaction-time corrected"; the code uses raw press times | tell the teaching chat | tell it |
| 10 | **`tools/dc2_hardware_check.py`** has an uncommitted change that is not tracking's. It re-orders a rehearsal script's blocks | whose it is, and whether to commit it | ask the chat that made it |

## 2. What was done

| item | result | where |
|---|---|---|
| A1 names to P1 to P6; commit the report and `pipeline/live/` | done, commit `c43dfde`. Two errors of mine fixed on the way: the 8.2 worked example is P5's recording, and start terms never reach the display lock | `reports/ARCHITECTURE_TRACKING_FINAL_2026-09-29.md` |
| A2 hash lists from each decode's own trace | 218 (zsf_B2), 273 (fin_B2) and 267 (fin_A3) files. Every file shared with the earlier lists agrees. All three traced rebuilds were EXACT | `pipeline/constrained/pd_repro_trace.py`; `runs/dc2_results/final/TRACE_HASHES_*.txt` |
| A3 zsf_B2 rebuilt from hashed files | **EXACT: 0 of 120 changed** (committed, display lock, scorer lock). All 218 hashes OK, and 0 unlisted inputs | `runs/dc2_results/verify/repro_trace/run/zsf_B2/` |
| A4 item 2, the time-step disclosure | 0 of 360 exits or committed lines change; committed and lock 0.00 [0.00, 0.00] | `reports/DT_MISMATCH_2026-09-30.md` |
| A5a the null rule and 0.431 | the null rule was fitted on A1+A2 (`8ca8cac`) and 0.431 on A1 (`05cc64d`). No A3, so no figure is touched | `reports/TRACKING_CHECKS_2026-09-29.md` |
| A5b the render's first dot | on the lock line's entry, as f3_render. Causal. Nothing changed | same |
| A5c git over data/, capture, firmware, serial, cleaning; imports of `testing/` | no code touch after 11 Sep; no firmware in the repo; two documented sidecar edits; no `testing/` import | same |
| A5d a video "decoded accuracy" | proposed (decision 4) | same |
| B V2 round | pre-registered and hashed before training; 10 networks on the GPU during Identification's pause. **Option 3: +2.29 [-0.21, 5.00], KEEP BASE. Option 4: +6.25 [2.71, 9.79], but the E_row5 edge guard failed: KEEP BASE. The stop rule applied: no A3 or B2 read** | `reports/V2_DEVELOPMENT_2026-09-30.md`; `runs/dc2_results/rule/V2_PREREG.md` |
| C the rig commands and protocol | done | `reports/RIG_RUN_PROTOCOL_2026-09-29.md` |
| AGC question (morning) | the firmware's missing gain is why the pipeline normalises each packet's shape. A per-packet scale cancels exactly. Not measured on the dips your tests found | chat only |

## 3. The state

**The model:**
- 15:39, `runs/dc2_results/rule/FINAL_CONFIG.md`, hash OK at 01:33;
- A3 93.33 / 70.83 (the lock is optimistic);
- B2 93.33 / 72.50;
- zero-shot B2 80.00 / 49.17.

**Test looks:** A3 and B2 have been decoded three times. **Any further figure is a fourth look, and needs
you.**

**Committed last night:** only `c43dfde` (A1).

**Uncommitted, and mine:**
- **code:** `pipeline/constrained/pd_dt.py`, `pd_repro_trace.py`, `pd_v2.py` (V2, held);
- **reports:** `reports/DT_MISMATCH_2026-09-30.md`, `RIG_RUN_PROTOCOL_2026-09-29.md`,
  `TRACKING_CHECKS_2026-09-29.md`, `V2_DEVELOPMENT_2026-09-30.md`, and this file;
- **records:** the `QUEUE.md` and `STATE.md` updates, and the DEVLOG entries (the DEVLOG also holds the
  teaching chat's own uncommitted section);
- **chain scripts:** `runs/dc2_results/{dt_chain.sh, fin_trace_chain.sh, trace_amend_chain.sh,
  zsf_trace_chain.sh, zsf_trace_chain2.sh, v2_chain.py, v2_summary.py}`;
- **outputs:** under `runs/dc2_results/` (`rule/V2_*`, `v2/`, `final/TRACE_HASHES_*`, the `DT*` and
  `V2B*` decodes).

**Running:** nothing for tracking. Identification was given the GPU back at 23:45.

## 4. My own slips last night, all caught before any result depended on them

1. **The architecture report had two errors** (the P5 example; the claim that A2 feeds the lock). Both
   were fixed before its commit.
2. **The first trace-derived hash lists missed** the files a rebuild copies in before its traced steps.
   Found at 01:19 and fixed; the lists were regenerated, and zsf_B2 was rebuilt again against the
   complete list.
3. **Tool bugs,** each fixed and rerun:
   - a relative module path taken for a repository file;
   - two import-guard bindings;
   - a strided-slice error on the GPU (the values are unchanged);
   - two key-format slips in the item 2 report.
4. **A wrong sentence in the draft item 2 report** ("arm 0 reproduces the record"). Corrected: it
   differs from round 2's record on 6 committed answers and 1 lock, which is the pace change.

## 5. Where the detail is

- **The queue:** the top section of `QUEUE.md`.
- **The log:** `reports/DEVLOG_TRACKING_2026-09-28.md`, the entries from "PARTS A, B AND C".
- **The model:** `reports/ARCHITECTURE_TRACKING_FINAL_2026-09-29.md` (how it works) and
  `reports/MODEL_FINAL_TRACKING_CORRECTED.md` (its results).
