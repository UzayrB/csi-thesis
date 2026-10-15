# MODEL_FINAL_TRACKING_CORRECTED: the final tracker with the reader leak fixed, 29 September 2026

Written 15:49 SAST.

**What this replaces.** It supersedes the figures of `reports/MODEL_FINAL_TRACKING.md`, which is left
unchanged as the record of the first decode. The frozen DC2 results (`reports/DC2_RESULTS_2026-09-28.md`)
remain the confirmatory record beside both.

**Sources:**
- the configuration: `runs/dc2_results/rule/FINAL_CONFIG.md`, frozen 15:39, before any test decode,
  with SHA-256 `360053d7...`;
- the tables: `runs/dc2_results/final/FINAL_CORRECTED.md` and `ZERO_SHOT_CORRECTED.md`;
- the audit: `reports/AUDIT_LEAKAGE_TRACKING_2026-09-29.md`;
- the log: `reports/DEVLOG_TRACKING_2026-09-28.md`, section VERIFY.

## 1. The figures, old and new

**The partitions.** Every figure is on 120 evaluated passes of its test session, and chance is 8.33
percent (12 lines).
- The main model is trained on A1+A2+B1, and every statistic is fitted on those sessions.
- The zero-shot model is trained on A1+A2 only, and every statistic is fitted on A1+A2 only.
- A3 and B2 never entered training or any choice.

Brackets are 95 percent bootstrap intervals over passes.

| figure | trained and fitted on | tested on | committed | display lock | old (leaky readers), committed / lock |
|---|---|---|---|---|---|
| **A3** | A1+A2+B1 | A3 (Room A, third day) | **93.33** [88.33, 97.50] | **70.83** [62.50, 79.17], **optimistic** (see below) | 93.33 / 70.83 |
| **B2** | A1+A2+B1 | B2 (Room B, second day) | **93.33** [88.33, 97.50] | **72.50** [63.33, 80.00], **the headline lock result** | 94.17 / 74.17 |
| **zero-shot B2** | A1+A2 only | B2 | **80.00** [72.50, 86.67] | **49.17** [40.00, 58.33] | 83.33 / 49.17 (its readers were already clean) |

**The old figures carried the reader leak.** The start-of-walk readers of the A3 and B2 models had
learnt B1's rows from networks trained on A1+A2+A3 (section 2). The old zero-shot readers were clean.
Its figure changes only through the re-selected decode and the A1+A2 pace.

**The A3 lock is optimistic.** The display decode that draws the lock uses a speed cap of 0.80 m per
window and a spread of 4.5. Both were set on the A3 demonstration pairing in September:
- the cap was swept 2026-09-21 on A3's 120 walks (git `8590d47`);
- the spread arrived with the 3 m/s ceiling on the same walks (git `0b18ee6`), with no independent
  tuning recorded.

So the A3 lock figure is labelled optimistic, and **the B2 lock (72.50) is the headline lock result.**
The committed answers do not read the cap or the spread.

**The B1 gain on B2.** This is the full model minus the zero-shot, under the same decoder, paired on the
same 120 passes:
- committed: **+13.33 [7.48, 20.00] points** (93.33 against 80.00);
- lock: **+23.33 [15.83, 31.67] points** (72.50 against 49.17).

**The configuration was selected on development rotations that include B1.** So the zero-shot B2 figure
is zero-shot in its weights and fitted statistics, but not in its design choices.

**The edge lines,** E_col1 / E_col5 / E_row1 / E_row5, in percent:

| figure | committed | lock |
|---|---|---|
| A3 | 67 / 100 / 100 / 100 | 50 / 100 / 83 / 83 |
| B2 | 100 / 100 / 100 / 100 | 100 / 100 / 50 / 50 |
| zero-shot B2 | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 |

The B2 lock's E_row1 and E_row5 (50) and the zero-shot lock's E_row1 (0 of 6) remain the weakest part.

## 2. What was wrong, and the fix

**The leak.** Two paths ran through the start-of-walk readers' TRAINING rows. Both readers are LDAs fitted
on per-pass rows from each training session: the A2 region reader, and the reader behind the veto or
abstain. Each session's rows are made by a per-link network that did not train on that session.
1. **B1's rows came from the frozen DC2 networks `s010203_to_sB`, trained on A1+A2+A3.** The harness
   copied them in under the name `s010203_to_sB1`. For the A3 test this is leakage from the test
   session, through the networks that shaped the readers' training features. For B2 it broke "trained
   on A1+A2+B1 only".
2. **On two development rotations, the Room A rows came from a head trained on the validation
   session:**
   - A1+B1 -> A2 used A1 rows from an A2-trained head;
   - A2+B1 -> A1 used A2 rows from an A1-trained head.

**The widened audit.** It traced every file each decode opened. Nothing else in the model saw A3 or B2.
The B2 decodes open A3's sidecars, but only for the taped line geometry, and all 12 lines come from A1's
sidecar.

**The fix** (`pipeline/constrained/pd_clean.py`). Every training session's reader rows now come from heads
trained only on the model's other training sessions:
- final model: A1's rows from A2-only heads, A2's from A1-only heads, B1's from A1+A2 heads;
- rotations: B1-only heads where A1 or A2 had used the validation session's.

**The fix was checked before it was trusted:**
- the rebuilt reader files match the originals' builder to 2e-6;
- seven CPU reproductions of the record were exact before the fix was applied.

## 3. The re-selection (rotations only; `rule/CR_CHOICES.md`, `RS_SUMMARY.md`, `RS2_SUMMARY.md`)

**All 78 recorded rule comparisons were re-run on the clean readers.** Eight decisions moved:
- **abstain was adopted wherever it was layered:**
  - over relgateA: +3.75 [1.25, 6.67];
  - over relgateU: +3.96 [0.83, 7.29];
  - on the D2 networks: +4.79 [1.04, 8.96];
- d1sp's layer-1 relgate and scorer lock were no longer adopted, which is superseded by the later
  layers;
- relgate+abstain now fails the edge guard.

**Why abstain moved.** The abstain arm's own score did not change; the veto's did. On the A2-validation
rotation the veto had been fitted partly on rows from a head trained on A2 itself. With clean rows it
lost 2.5 points, committed and lock. **The leak had flattered the veto on its own validation data.**

**Replaying the decision sequence in its original order:**
1. Round 1, on relgateU+abstain, adopted the A2 start-term weight 0.25 (+1.88 [0.42, 3.55]).
2. Round 2, on relgateU+abstain+a2w0.25, adopted nothing further:
   - the other options were kept out;
   - the display lock stays (+1.46 [-1.67, 4.79]);
   - the shared encoder is confirmed (+19.38 [11.25, 27.71]);
   - attention and the D5 options are rejected.
3. D2 stays aug+rrel (Uzayr).

**The configuration.**
- **Networks:** unchanged (no retraining).
- **Decode:** relgateU + abstain in place of the veto + the A2 weight 0.25, with the display lock.
- **Rotation objective:** 121.88, against 122.50 for the configuration first selected with the leaky
  readers.

**The clean ladder** (display lock):

| step | objective |
|---|---|
| D0 | 74.38 |
| + D2 | 85.42 |
| + D3 relgateU | 99.58 |
| + D4 | 121.46 |

D0 to final: +47.08 [38.33, 56.04].

## 4. Provenance (`runs/dc2_results/verify/provenance_*.md`: pre-checks and the decodes' own traces)

**Every fitted component** comes from the model's training sessions:
- the five heads and their standardisation;
- the position head;
- both readers' training rows and the heads that made them;
- the test-side reader heads;
- the A2 term and abstain;
- the relative gate's G0;
- the chain prior;
- the emission marginal.

**The fail-loud checks passed**, before the test and on each decode's file trace:
- zero-shot: fails on any component touching B1 or B2;
- main model: fails on any component touching A3 or B2.

**The zero-shot's fitted components come from A1+A2 recordings only.** The test recordings' own causal
statistics come from each B2 recording's idle windows before its first press: the relative-RSSI
reference, g_rec and AdaBN.

**Design constants:**

| constant | set on | here |
|---|---|---|
| **pace prior** | the old N(1.298, 0.123) was measured on A1+A2+A3's 360 passes | **recomputed on A1+A2 by the same anchor method: N(1.30341, 0.11255), 240 passes**. The change is within 0.02 m/s, so the selection stands (Uzayr). Used in every test decode |
| display cap 0.80, spread 4.5 | A3 (section 1) | kept; the A3 lock is labelled optimistic |
| decoder configuration and null rule | the training side of `s0102_to_s03` (A1+A2) | unchanged |
| veto and abstain thresholds | the selection folds A1 -> A2 and A2 -> A1 | unchanged |
| the A2 weight 0.25, abstain, relgateU and the other decode options | the development rotations, which include B1 | design choices |

## 5. Resolution and latency

**Resolution: the drawn dot against the truth, median / p90, in metres:**

| figure | walks whose lock is correct | along the true line, on windows drawn on it |
|---|---|---|
| A3 | 0.32 / 0.92 | 0.29 / 0.90 |
| B2 | 0.37 / 0.90 | 0.35 / 0.85 |
| zero-shot B2 | 0.41 / 1.02 | |

Old: A3 0.31 / 0.90; B2 0.32 / 0.86.

**Head latency per window is unchanged.** The networks are the same files:
- the five shared-encoder heads take **36.9 ms median** (p95 39.6, p99 42.5, max 44.6), for one window
  of three links at batch 1 on this laptop's Apple GPU;
- the per-link heads they replaced took 65.1 ms (`runs/dc2_results/final/latency_heads.json`).

The per-window service time of the whole live chain on the CPU is measured by the live replay gates and
is added when they run. The decoder change (abstain, the A2 weight) adds no per-window work.

**End-to-end:** the display runs 2.0 s behind real time; the lock is read 2.0 s after the start press;
the committed answer comes at the decoder's causal exit.

## 6. Against the references

`pd_final` pairs each test with the split baseline:
- ph_A3: 88.33 / 65.00; paired +5.00 [0.00, 10.00] committed and +5.83 [-3.35, 15.00] lock;
- ph_B2: 57.50 / 20.83; paired +35.83 [26.67, 45.00] and +51.67 [42.50, 60.83].

**The split baseline was decoded with the same leaky readers and the old pace,** so these paired
differences mix the fix with the model change. A clean-reader baseline would need another A3 and B2
decode of a reference model, and was not run.

The frozen DC2 reference on B2 (trained on A1+A2+A3) is 50.00 / 12.50.

## 7. Verification: the substitution test and the shuffled-radio control (appended 15:55)

**These are diagnostics only; nothing in them feeds back into the configuration.** Code:
`pipeline/constrained/pd_subst.py`. Results: `runs/dc2_results/verify/subst/<cell>.json`.

**Reproduction first.** Before any swap, each run decodes every pass on its OWN radio and must reproduce
the test's saved rows, or it is void. **All three reproduce exactly: 120 of 120, committed and lock.**

**How a swap works.** Every radio-derived input a pass's decisions read becomes a donor's:
- the pooled emissions and the relative gate energy, from 4 s before the walk's first window to the
  donor walk's end plus 4 s;
- both start terms, which read the radio around the press.

The pass keeps only its press times.

**The two schemes:**
- **substitution:** the donor is the next participant's walk at the same pass number, on whatever line
  they walked;
- **shuffle:** the donor is the next participant's walk on a DIFFERENT line, closest in duration.

**Substitution.** The changed share is set against its ceiling, which is the share of passes whose donor
walked a different line:

| test | decision | on its own radio | on the donor's radio | changed | ceiling | changed / ceiling | equals the donor's own decision |
|---|---|---|---|---|---|---|---|
| A3 | committed | 93.33 | 8.33 [4.17, 14.17] | 92.50 | 90.83 | 1.02 | 100.0 |
| A3 | lock | 70.83 | 10.00 [5.00, 15.83] | 92.50 | 90.83 | 1.02 | 100.0 |
| B2 | committed | 93.33 | 11.67 [5.83, 18.33] | 89.17 | 90.00 | 0.99 | 99.2 |
| B2 | lock | 72.50 | 10.83 [5.83, 16.67] | 90.00 | 90.00 | 1.00 | 100.0 |
| zero-shot B2 | committed | 80.00 | 12.50 [6.67, 18.35] | 86.67 | 90.00 | 0.96 | 100.0 |
| zero-shot B2 | lock | 49.17 | 11.67 [6.67, 17.50] | 83.33 | 90.00 | 0.93 | 100.0 |

**Shuffle.** Accuracy against the pass's own line should fall to chance (8.33) or below:

| test | decision | on its own radio | on a different line's radio | follows the donor's line |
|---|---|---|---|---|
| A3 | committed | 93.33 | **2.50** [0.00, 5.83] | 78.33 |
| A3 | lock | 70.83 | **3.33** [0.83, 6.67] | 61.67 |
| B2 | committed | 93.33 | **0.00** [0.00, 0.00] | 90.83 |
| B2 | lock | 72.50 | **0.83** [0.00, 2.50] | 70.00 |
| zero-shot B2 | committed | 80.00 | **0.00** [0.00, 0.00] | 79.17 |
| zero-shot B2 | lock | 49.17 | **5.83** [2.48, 10.00] | 32.50 |

**Reading.** The decisions are made from the radio.
- With another person's radio the decision changes almost exactly as often as the donor's line differs:
  0.93 to 1.02 of the ceiling.
- It equals what the donor's own pass decided on 99 to 100 percent.
- On radio from a different line, accuracy against the true line falls to 0 to 6 percent, below chance.

**Caveats:**
- **Donor walks cut short by the recipient's next pass** (the rest is the recipient's own radio): 1 to 5
  per run.
- **A3 shuffle exits past the donor's segment:** on 19 A3 shuffle walks the decoder's exit fired after
  the donor's segment, reading some of the recipient's own later radio. The collapse to 2.5 percent holds
  regardless.

## 8. The demonstration renders (appended 16:22)

**Made by** `pipeline/constrained/pd_render.py` under `reports/RENDER_RULES.md` in full. The composition
is f3_render's, with f4_render's three changes:
- the 0.375 s display phase;
- causal bounds on the glide step;
- a CORRECT or WRONG verdict at each walk's end.

**What they draw:**
- the corrected final model, with the frozen variant and the A1+A2 pace;
- after the lock, the dot follows the display head DISP_END, retrained on A1+A2+B1 only with the final
  recipe (`pd_dispend.py`, 2744 end-labelled windows).

**Output:** 6 videos per test session in `runs/dc2_results/render_final/03/` and `B2/`, each with
`RESULTS.json` and `ACCEPTANCE.md`.

| check | A3 | B2 |
|---|---|---|
| committed and lock equal the corrected decode | 120 / 120 | 120 / 120 |
| every RENDER_RULES check (rules 1, 1a, 1b, 2, 2a, 5, 6, V1 to V5) | PASS | PASS |
| drawn-window and evidence causal bounds | -1.375 s | -1.376 s |
| frames without a dot, whole videos | 0 of 21,918 | 0 of 21,607 |
| jumps over 0.5 m (of which at the lock) | 124 (120) | 125 (119) |
| one-switch display (arm C): switches | 3, all wrong -> right | 1, wrong -> wrong |
| the drawn line ends on the committed line | 91 of 120 | 89 of 120 |
| dwell footage (V4): frames cut, frames left | 29,163 cut, 0 left | none recorded |
| on-screen tracking within 0.5 m, against the delayed marker | 43.5 percent | 48.9 percent |

**The acceptance files' "decoded accuracy"** (2.3 and 1.9 percent) keeps f3 and f4's inherited
definition, the truth 1.0 s before the frame. Under V1's 2.0 s delay it is not the decoder's accuracy,
and each file carries a note saying so. Quote the resolution of section 5 instead.

## 9. The live system: the corrected final model, ported and gated (appended 17:08)

**Code:** `pipeline/live/final_model.py`.
- **FinalPool:** the five shared-encoder heads, run window by window.
- **The relative statistics at the first press.** The relative-RSSI means and the gate's g_rec are fixed
  from the idle windows that ended before the first press; the heads never run before it.
- **FinalStartTerms:** abstain and the A2 weight 0.25, with the corrected readers.
- **FinalEndHead:** the retrained display head.
- **The frozen inputs:** the variant is read from `FINAL_CONFIG.md` only after its hash checks, and the
  A1+A2 pace from `final/PACE_A1A2.json`.

**The replay gate.** Every recording of the two test sessions was fed as raw packets and key presses, in
arrival order, through the whole live session: stream, heads, start terms, decoder and display. Each
pass's committed line and display lock were compared with the corrected offline decode
(`cells/<cell>/d3/FC.relgateU+abstain+a2w0.25`). Results: `runs/live/final/gate_fin_A3.json`,
`gate_fin_B2.json`.

| test | committed equal | lock equal | relative-RSSI means against the offline references | per-window service, median / p95 / p99 / max | per start press, median / max |
|---|---|---|---|---|---|
| A3 | **120 / 120** | **120 / 120** | identical (max difference 0) | 0.094 / 0.141 / 0.256 / 0.401 s | 0.84 / 2.39 s |
| B2 | **120 / 120** | **120 / 120** | identical (max difference 0) | 0.097 / 0.170 / 0.273 / 0.303 s | 0.87 / 3.37 s |

**How the timing was measured.** On one CPU thread, forced off the Apple GPU, with the tracking chain
and Identification's jobs sharing the machine. So these are conservative figures.

**Per-window latency.** Cutting a window from packets, running the five heads, the start terms, the
decoder step and the display takes 94 to 97 ms median and 0.26 to 0.27 s at the 99th percentile. That is
inside the 0.5 s stride. Of it, the five heads alone take 36.9 ms median on the GPU (section 5).

**A start press** re-cuts the windows, fixes the statistics on the first press, and recomputes the rows:
0.84 to 0.87 s median, 3.37 s at most. Windows queued behind a press are drawn late by up to that.

**End-to-end:**
- **The dot:** the display runs 2.0 s behind real time by design (V1), and a window's outputs are ready
  within that except just after a press.
- **The lock** is read 2.0 s after the start press.
- **The committed answer** comes at the decoder's causal exit.
- **Recording ends:** 6 passes per session are decided only when the recording ends, as in the offline
  decode.

**The rig.** `python3 -m pipeline.live preflight --baseline <dir>` checks that:
- the configuration hash matches;
- the frozen pace is in force;
- the corrected model's 133 hashed files match (`final/FINAL_CORRECTED_HASHES.txt`);
- the display head exists;
- both replay gates were exact for this variant;
- the reader map is built;
- the baseline is present and recent.

It passes now. `python3 -m pipeline.live rig --baseline <dir>` runs the final model in either room, and it
refuses unless the pre-flight passes. It has not been run on the boards: that opens the serial ports and
needs Uzayr.

## 10. Reproduction from the hashes (appended 17:50)

**The procedure.** `pipeline/constrained/pd_repro.py` (the `run` step) first checks the 133 files hashed in
`runs/dc2_results/final/FINAL_CORRECTED_HASHES.txt`: the code, the configuration, the five heads' weights,
and the readers' networks and rows. It refuses if any differs. It then builds scratch trees under
`runs/dc2_results/verify/repro/<cell>/` holding the hashed weights, and re-derives from them:
- the test-side reader posteriors;
- the corrected B1 reader rows;
- the five heads' posteriors on the test recordings.

Finally it refits the readers with the cache switched off, decodes with the frozen variant and the A1+A2
pace, and compares every pass with the one-test decode.

| cell | passes | committed changed | display lock changed | scorer lock changed | result | minutes |
|---|---|---|---|---|---|---|
| fin_A3 | 120 | 0 | 0 | 0 | **EXACT** (93.33 / 70.83) | 27.0 |
| fin_B2 | 120 | 0 | 0 | 0 | **EXACT** (93.33 / 72.50) | 14.4 |

`rule/FINAL_CONFIG.md` matched its hash at the start of the chain and again at its end (17:49).

**A gap in the hashed set, found during the reproduction and closed by evidence.** The 133 files omit the
three position networks of the corrected B1 reader. These are `s0102_to_sB1_pos2_*` in both cells: byte
copies, from 18 September, of the shipped `s0102_to_s03_pos2_*`, which were trained on A1+A2. The rebuild
read the B1 reader's networks from the shipped tree. The evidence that the rebuild still used the right
files:
- the shipped classifier files are byte-identical to the hashed cell copies;
- in both cells, the rebuilt B1 rows equal the hashed rows file in every array, including the position
  estimates those networks produce (compared with NaN-aware equality; the NaNs are idle windows' missing
  ground truth);
- fin_B2's test-side position networks are byte-identical to fin_A3's hashed ones.

The 15 files concerned are listed with their hashes in `final/FINAL_CORRECTED_HASHES_SUPPLEMENT.txt`.
It was written at 17:24, after the test, as a record; it is not part of the frozen configuration.

**Not re-derived here:**
- the heads' weights, which are taken from the hashed files rather than retrained;
- the A1 and A2 reader rows, which are hashed inputs copied in (their opt-in rebuild,
  `PD_REPRO_REBUILD_AB=1`, was not run);
- the zero-shot cell, zsf_B2, which is not re-decoded from hashes. Its figure rests on the one-test decode
  and its provenance post-check.
