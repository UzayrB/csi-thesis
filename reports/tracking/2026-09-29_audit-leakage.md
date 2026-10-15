# Leakage audit of the final tracker, 29 September 2026 (written 11:18 SAST)

This report covers the final tracking model (`reports/MODEL_FINAL_TRACKING.md`: fin_A3, fin_B2 and the
zero-shot zsf_B2) and the development rotation cells its choices were made on.
- Task: Uzayr's verification task of 29 September, items 1d and F1.
- Code: `pipeline/constrained/pd_clean.py`.
- Evidence: `runs/dc2_results/verify/`.
- Log: `reports/DEVLOG_TRACKING_2026-09-28.md`, section VERIFY.

## 1. The answer

**Two leakage paths were found. Both run through the start-of-walk readers' TRAINING rows.**

1. **B1's reader rows came from networks trained on A1+A2+A3.**
   - Cells affected: every cell with B1 in training, the final model and two of the three rotations
     among them.
   - The mechanism:
     - `pd_cells.env_for` maps B1 to the tag `s010203_to_sB1`.
     - `pd_cells.do_view` fills that tag by copying in the frozen DC2 heads `s010203_to_sB`, which
       were trained on Room A sessions 01, 02 and 03 together (`reports/MODEL_FREEZE_DC2.md`).
     - The copies are byte-identical: sha256 `a4c7553e...` for the link-0 model and `5dfcff51...`
       for the posteriors.
   - For the A3 test this is leakage from the test session. For B2 it breaks "trained on A1+A2+B1
     only".
2. **On two rotations, the Room A reader rows came from a head trained on the validation session.**
   - On A1+B1 -> A2, A1's rows came from `s02_to_s01` (trained on A2).
   - On A2+B1 -> A1, A2's rows came from `s01_to_s02` (trained on A1).
   - The development numbers of those two rotations carry it. The rotation A1+A2 -> B1 is clean.

**Nothing else was found.** Every other artefact the final cells read was fitted on their training
sessions, or on each recording's own idle radio before its first press.
- **Zero-shot:** zsf_B2 is clean.
- **Test-side readers:** the V0 heads are clean.
- **The tracking networks** are clean.

**The fix.** Every training session's reader rows now come from per-link heads trained only on the
cell's OTHER training sessions (section 4). It is being applied to all 78 rule comparisons on the
rotations; then comes the corrected FINAL. Those results go in a separate record when they exist.

## 2. How the audit was done

**Three sources, each checked against the others:**
1. **The code paths.**
   - `pd_cells` (view, environment, training, readers, shared models);
   - `pd_decode.inner`;
   - `t2_embed.tag_for_session`;
   - `q3_startclf.collect` (the A2 region reader);
   - `u1_adapt.session_rows` (the veto);
   - `pd_train.fit_link` (standardisation).
2. **A trace of every file a decode opens.** A Python audit hook recorded every file opened by the
   decode process, which reproduced the record exactly on the CPU:
   - 169 files for fin_A3;
   - 174 for fin_B2;
   - 147 for zsf_B2;
   - 129 for d1sp_01B1_to_02.

   Each network file is mapped to the sessions its tag says it was trained on
   (`verify/audit_trace.json`, `verify/own/<cell>/clean.json`).
3. **The training records** (`cells/<cell>/train_*.json`): windows per session for every trained head.

**The reproductions confirm the trace describes the decode behind the figures.** The CPU decodes,
with the original map, equal the record row for row, committed answer and both locks:
- fin_A3: 93.33 / 70.83;
- fin_B2: 94.17 / 74.17;
- zsf_B2: 83.33 / 49.17;
- d1sp_01B1_to_02 and d2p_base_01B1_to_02: 120 of 120 each.

## 3. Every component of the final model

"Saw A3 / B2" means whether data from that session entered the fitting, directly or through another
network.

| component | fitted or trained on | saw A3 | saw B2 | evidence | status |
|---|---|---|---|---|---|
| **the five tracking heads** (shared encoder, learned fusion) | A1+A2+B1 walking windows, calibration excluded (3428 windows at 0.5 s; 1615 at 1 s) | no | no | `do_train_d2` asserts the test session and calibration recordings absent; `fin_A3/train_*.json` | clean |
| input standardisation (mu, sd per link and channel) | the same training windows | no | no | `pd_train.fit_link`: `per_channel_stats(X)` on the training array | clean |
| augmentation | fixed parameters, nothing fitted | | | `pd_train` | clean |
| relative RSSI | each recording's own idle windows before its first press | no | no | `prn_stats.json`, `u1_adapt.calibration_indices` | clean (causal) |
| fin_B2's heads | byte-identical copies of fin_A3's | no | no | `fin_B2/shared_models.json` | clean |
| the pool's cell marginal | the training windows' positions | no | no | `shipped_pool_emissions(tag, train, ...)` | clean |
| the relative gate's G0 (0.7542) | Room A training recordings, A1+A2 | no | no | `pd_decode.gate_reference(train, room_a_only=True)`; the trace reads no B1 or A3 gate energy for it | clean |
| the relative gate's g_rec | each recording's own idle windows before its first press | no | no | `pd_decode` relgateU | clean (causal) |
| the chain prior | the training sessions' line counts | no | no | `n2_arms.fit_chain_prior(st, train)` | clean |
| AdaBN (the veto's embeddings) | each recording's own idle windows before its first press | no | no | `u1_adapt.session_rows` | clean (causal) |
| **the A2 region reader: test-side rows** | V0 = ph_A3's per-link heads, trained on A1+A2+B1 | no | no | byte-identical to ph_A3's (`fcb6225d...`, `8caa594b...`) | clean |
| **the A2 region reader and veto: A1's training rows** | `s02_to_s01`, trained on A2 | no | no | trace | clean for the final model |
| **the A2 region reader and veto: A2's training rows** | `s01_to_s02`, trained on A1 | no | no | trace | clean for the final model |
| **the A2 region reader and veto: B1's training rows** | `s010203_to_sB1` = the frozen DC2 heads, **trained on A1+A2+A3** | **YES** | no | trace; byte-identical to `by_session/B1/art_half/models/s010203_to_sB_*` | **LEAK: fixed (section 4)** |
| the room's line geometry | the taped endpoints, from A1's sidecar (PA5, session 01) | no | no | see note 1 | clean |
| decoder configuration (rb2, keyed `s0102_to_s03`): margin 2.0, null_self 0.8, exit, clock, bout prior | the training side of that pairing, A1+A2 | no | no | `rb2_decoder/results.json`: "fitted on the training side of this pairing alone" | clean |
| the null rule (quantile 0.75, offset -7.5, gate weight 4.0, theta 0.431) | pre-DC2 "stage 4 fit", recorded under the same pairing | not traced | no | `rb2_decoder/results.json`, `null_rule` | **flagged**: folds not traced; D3 re-tuned the offset on the rotations and rejected it |
| the pace model N(1.298, 0.123) | 360 labelled Room A passes, **A1+A2+A3** | **YES** | no | `reports/ROOM_TRANSFER_AUDIT_2026-09-22.md` | **flagged** (see note 2) |
| the A2 weight 0.5 | pre-DC2 held-out Room A folds, **A3 among them** | **YES** | no | `reports/attempts/RECORD_TRACKING.md` ("selected on their own paired improvement on the held-out folds") | **flagged** (see note 2) |
| the veto threshold 0.01 and weight 1.0 | selection folds `s01_to_s02` and `s02_to_s01` | no | no | `veto.py`, `u2_useit.SELECTION_FOLDS` | clean |
| display spread 4.5 and cap 0.8 m per window (the lock) | pre-DC2 display stages on Room A | not traced | no | `PREREG_DC2_crossroom` section on the lock | **flagged**: folds not traced; D3 re-tuned the spread (3.5, 5.5) on the rotations and rejected it |
| emission kind and alpha (`rb1_truth`, `rb2c_alpha`), and the `n2_arms` option set | pre-DC2 Room A stages | not traced | no | the trace reads these results | **flagged**: pre-DC2 choices, not re-derived |

Notes:

1. **The A3 sidecars are opened, but none of their data is used.** The B2 decodes open
   `data/room_A/session_03/*.gt.json`, read straight from `data/`. The only code that opens them is
   `paths.load_paths()`, which reads the room's line geometry. It takes each line from the FIRST
   sidecar naming it:
   - all 12 lines come from A1 (PA5, session 01);
   - every sidecar in all three sessions records identical coordinates.

   The other function in that module, `pass_path_labels()`, would read A3's line labels, but it is
   never called.
2. **The pace model and the A2 weight carry pre-DC2 Room A information that included A3.** Uzayr
   flagged this before the audit, and it holds for these two. On the rotations, D3 re-fitted the
   pace on A1+A2 (1.307 +- 0.113) and re-tuned the A2 weight (0.25 and 1.0). The rule rejected both,
   so the shipped values were kept on development evidence. They were not re-derived without A3.

**The render only (not the decisions):**
- **DISP_END:** retrained on A1+A2+B1 for these renders.
- **The switch theta:** chosen on the selection folds, without A3.
- **The dot phase 0.50:** a single display constant measured over nine Room A pairings, A3 among the
  test sides. It changes no decision and no accuracy figure (RENDER_RULES V5).

## 4. The fix: clean reader rows

**The rule.** A training session's reader rows must come from heads trained only on the cell's OTHER
training sessions.
- An existing tag is kept when its training sessions are a subset of those.
- Otherwise the rows are rebuilt under a new tag from existing per-link heads, with
  `dc2_run.do_infer`'s own block construction, on the CPU.

**The builder is checked against a file `dc2_run.do_infer` wrote.** It rebuilt the frozen heads' B1
posteriors to within 2e-6, with the argmax equal on all six recordings (`verify/crossfit_plumb.json`).

| cells | session | was (trained on) | now (trained on) |
|---|---|---|---|
| A1+B1 -> A2 (all prefixes) | A1 | `s02_to_s01` (A2) | `sB1_to_s01`: cell 3a's heads (B1) |
| A1+B1 -> A2 | B1 | `s010203_to_sB1` (A1+A2+A3) | `s01_to_sB1`: shipped half-tree heads (A1) |
| A2+B1 -> A1 | A2 | `s01_to_s02` (A1) | `sB1_to_s02` (B1) |
| A2+B1 -> A1 | B1 | `s010203_to_sB1` | `s02_to_sB1` (A2) |
| A1+A2 -> B1 | none | already clean | unchanged |
| fin_A3, fin_B2 | B1 | `s010203_to_sB1` | `s0102_to_sB1`: shipped half-tree heads (A1+A2) |
| zsf_B2 | none | already clean | unchanged |

**Where the fixed decodes go.**
- New folders `cells/<cell>/d3/CR.<variant>`; pd_rule reads them as `<prefix>@CR.<variant>`. No
  record is overwritten.
- Each keeps its own file trace (`clean.json`).
- The readers are fitted once per rotation and read back from a cache keyed by the hashes of every
  file they read. The cache is validated: `d2p_base_01B1_to_02` read it and still equalled its
  record, 120 of 120.

## 5. What remains

The results of the fix have not been read yet:
- the 78 rule comparisons on the clean readers (`rule/CR_*`);
- whether any D-stage choice moves;
- the corrected FINAL.

They will be recorded in MODEL_FINAL_TRACKING (a dated section), the DEVLOG, STATE and the HANDOFF.
The figures of 93.33 / 70.83 (A3) and 94.17 / 74.17 (B2) stay on record, labelled as carrying the
path in section 1.1.
