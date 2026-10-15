> **SUPERSEDED 2026-10-01 09:53 SAST** by `reports/HANDOFF_IDENTIFICATION_2026-10-01.md`; nothing below is changed.

# Handoff: IDENTIFICATION, 2026-09-30 08:54 SAST

For a new session or chat that picks up identification. Everything below was checked against the files
on disk at the time above; the last identification commit is b52a355. It supersedes
`reports/HANDOFF_IDENTIFICATION_2026-09-28.md` for status. Re-check anything you act on.

**Nothing of identification's is running:**
- no queue runner;
- no scheduled check-in;
- no background job.

Tracking runs in its own session. Its latest handoff is `reports/HANDOFF_TRACKING_2026-09-30.md`.

## 0. Read first, in this order

1. `reports/ID_AUDIT_2026-09-30.md`: the latest state and figures, and the eight thesis corrections.
2. `reports/ID_ARCHITECTURE_2026-09-29.md`: how the system works, step by step, from packets to the
   decision, **and its addendum at the end** (the two bug fixes the audit adopted).
3. `reports/ID_WALKS_2026-09-29.md`: identification on the identification walks (training data,
   direction, calibration, deployment measures, limb Doppler, start-press-only).
4. `reports/ID_DEV_FINAL_2026-09-29.md`: how the final ensemble was found (leave one session out).
5. `reports/BRIEF_ID_DIRECTION_2026-09-28.md`: the operator's standing rules (verbatim).
6. `reports/DEVLOG_ID_2026-09-28.md`: every step since 28 Sept, with what, why and the result. It is
   long, so read its end first.

Each brief Uzayr gave is saved verbatim as `reports/BRIEF_ID_*.md`. **Re-read a brief file before acting
on it; never work from memory of it.**

## 1. Where things stand

**The model** is an equal-weight ensemble of eight components (sum of log-probabilities):
- random forests (per-path z, session-standardised, and with pace as one gait column);
- extra trees and shrinkage LDA, each with pace;
- CNN-v2 on Doppler maps, plain and with AdaBN;
- per-link CNNs with AdaBN.

It uses **630** gait features (633 minus the audit's bug B-1) and Doppler maps with a gain-relative log
constant (bug B-2). The full description is in the architecture document.

**Current figures** (after the audit's bug fixes; 95 % intervals over participants; chance 16.67):

| evaluation | figure |
|---|---|
| identification walks, natural, both directions, TR-AB (Room A + the other Room B day), calibrated on other people's walks | **43.33 [26.11, 62.78]** (was 46.67 before the fixes) |
| the same, speed alone (S0) | 38.33 [20.00, 61.11] |
| the model minus S0, fast walks | **+21.85 [5.00, 35.59]** (at natural pace, +5.00 [-17.22, 23.89], not separable) |
| leave one session out, tracking passes, Room A | **39.44 [26.11, 48.33]** |
| leave one session out, tracking passes, Room B | **30.00 [19.58, 39.17]** |
| deployment (identification walks) | top-2 69.44 (chance 33.33); household of 2 78.00 (chance 50); 3 walks 55.56 |
| live replay (dev batch model) | exact equality with offline at a 21 s wait; at 5 s, 95 % of decisions unchanged, accuracy the same within noise, latency 5.3 to 5.6 s |

**Settled questions:**

| question | answer |
|---|---|
| Room A helps? | yes: +18.33 [8.33, 27.78] over the other Room B day alone |
| Slot-structure dependence? | none: CAL-causal minus CAL-others -2.22 [-6.11, 1.67] |
| Direction effect? | none detectable: away 41 against towards 52, -11.11 [-23.33, 1.11] on 90 round trips |
| Usable limb Doppler at 150 packets per second? | no: energy is there in half the walks, but limb features add nothing |
| Start press only? | no: the end detector misses by about 2 s and accuracy drops by 14.44; keep both presses |
| The audit's seven candidates? | none adopted: fusion, L1, L2, CF, FN, GS; C1 not run (gate not met) |

**The open lead is GS, per-packet amplitude normalisation.**
- **Result:** +10.00 [-5.00, 23.33] on natural walks.
- **Why it's promising:** every one of the eight components improves, and so does each test day.
- **Why it wasn't adopted:** six participants cannot separate +10 points from zero.
- **Likely mechanism:** per-packet common-mode amplitude dips (about 2.6 % of packet pairs, as
  frequent in empty rooms) swamp the mean-channel gait features. GS kills 294 of the 630 columns and
  still does better.
- **Whether to test a principled version with a pre-declared test is Uzayr's decision.** It would
  normalise per packet for the PCA and Doppler side and drop the mean-channel features.

## 2. Decisions waiting for Uzayr

1. **The GS follow-up** (above).
2. **The live app.**
   - It still runs the old frozen random forest for identification.
   - `python3 -m pipeline.live rig --mode identify` refuses: no enrolment set is wired.
   - The last two briefs ruled the live app out of scope; it gets its own brief.
   - What the wiring would need is in the architecture document, section 13.3.
   - The recommendation:
     - train set TR-AB, retrained on all five sessions;
     - a 5 s decision wait;
     - warm-up calibration walks by several people;
     - both presses.
3. **Thesis framing.** The model's advantage over speed alone is robustness to changes of pace. At
   natural pace it does not clearly beat speed. Claim "identification that survives pace changes", not
   "gait beats pace".
4. **The eight thesis corrections** in `reports/ID_AUDIT_2026-09-30.md`, section 4:
   - 54 unique subcarriers, not 103;
   - a ceiling of about 74.5 Hz;
   - torso agreement at 2.34 Hz bin resolution;
   - rhythm visible in about 30 % of walks, not 3 %;
   - the headline 43.33;
   - 630 features;
   - gain invariance;
   - no AGC compensation.

## 3. Rules that bind (from the briefs; the latest brief overrides earlier ones where they differ)

**The standing rules** (the direction of 28 Sept):
- no leakage: whole-session splits, and statistics from training data or causal pre-pass data only;
- anything live must be causal;
- identification is gait-based, with pace only as one parameter;
- `data/` is read only;
- the free-movement (`DEMO_free`) and calibration (`_C_walk`) recordings are never used.

**Protected:**
- never edit `pipeline/io/`, firmware, serial code, `pipeline/clean/common.py`, pinned files,
  `PREREG_*` or freeze-hashed files (for example `idv2_core.py` and `idv2_run.py`, frozen with the v2
  registration);
- **new code goes in new files** (`idx_*`, `idw_*`, `idz_*`; pick a new prefix for new work);
- never overwrite a saved bank, model or output.

**Tracking has priority for compute:**
- run jobs under `taskpolicy -c utility nice -n 19` with `OMP_NUM_THREADS=1`, one at a time;
- use the GPU only when tracking isn't;
- no `caffeinate`, governor or watchdog (the last two briefs);
- **never touch tracking's files or processes**; kill only your own, by PID, never `pkill`.
- **The GPU handover** used on 29 Sept:
  1. tracking messages "ready";
  2. identification touches `runs/identify/audit/queue/HOLD_GPU`, and its controller pauses between
     steps;
  3. identification messages "GPU free";
  4. tracking messages "done";
  5. identification removes the flag.

**Writing:**
- participant names never leave `runs/` ("participant P1" to "P6"; the code asserts `IC.no_names`);
- British spelling, no em dashes;
- label figures "development evaluation, all data seen".

**Git:** commit named paths only, never `git add -A`; check that `.git/index.lock` doesn't exist
before each commit; push after committing. The repository has many uncommitted tracking files: never
stage them.

**The standard for a pre-declared test** (the walks brief and the audit):
- write and commit a `PLAN.md` with every definition and rule before any comparison;
- afterwards, dated notes only.

## 4. Code and data map

| what | where |
|---|---|
| the pass bank (1,019 passes: features, maps, meta) | `runs/identify/dev/bank/` (dev); **`runs/identify/audit/bank_v2/`** (maps with fix B-2; the current one); `bank_cf`, `bank_gs` (candidates) |
| bank build and recordings list | `pipeline/identify/idx_bank.py` |
| bug fixes B-1 and B-2; bank builder with context and normalisation options | `pipeline/identify/idz_bank.py` (`columns_v2`, `conditioned_map_v2`, `pass_features_cf`, `build`) |
| the current train and apply code (configurable) | `pipeline/identify/idz_core.py` (`train`, `apply`, `calibration_groups`, `fuse`) |
| the audit's stage controller and state | `pipeline/identify/idz_run.py`; `runs/identify/audit/state.json`, `final.json` |
| the pre-audit train-and-save and apply | `pipeline/identify/idw_core.py`, `idw_run.py` |
| evaluation (bootstrap, paired, rules, deployment) | `pipeline/identify/idw_eval.py` |
| live replay | `pipeline/identify/idx_live.py` (dev model), with `--selection sel_all_ens --wide --perlink` |
| synthetic walker and tests | `pipeline/identify/idz_synth.py`, `tests/test_idz_synth.py` (5 pass) |
| packet audit, cadence, physics | `pipeline/identify/idz_audit.py`, `idz_cadence.py`, `idw_physics.py` |
| **final models** (bug-fixed, TR-AB, per test day) | `runs/identify/audit/models/B1_toB2`, `B1_toB1` |
| leave-one-session-out models | `runs/identify/audit/models/final_loso_{A1,A2,A3,B1,B2}` |
| the relabelled DC2 source (addendum E, metadata only) | `runs/identify/dc2_src_relabelled/` |

## 5. Lessons worth keeping

- **Check a verification against the untouched source.** An equality check once compared live
  features with a bank that already contained them, so it could not fail.
- **zsh:** backticks inside an unquoted heredoc run as commands. Use `<<'EOF'` for text with backticks.
- **The priority wrapper** in the queue runners cannot run a shell loop; put waits in a script
  (`hold.sh`, `wait_for.sh`).
- **In a `&&` chain,** `grep -c` returns exit status 1 on zero matches.
- **Read the clock** (`date`) before writing any time into a record.
- **Build time grids exactly as the bank does** (`np.arange(t0, t1, 1/150)`). A 3.5e-8 s grid
  difference moved some features by 0.017.
