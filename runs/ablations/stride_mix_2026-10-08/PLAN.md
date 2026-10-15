# Does the five-head pool's stride mix matter? Plan, written 2026-10-08 13:41 SAST (clock read 13:40)

Brief: `BRIEF.md` (Uzayr, 8 October, about 13:33, verbatim). Committed and pushed before any network is trained. The
same message asked for the run to be started under caffeinate and monitored while he is away, which is taken as the
go-ahead of the brief's step 3, given in advance.

## Background

The final tracker pools five cell-classifier heads with equal weight: one trained on 2 s windows started every 0.5 s
(`half`) and four on 2 s windows started every 1 s (`fh1s`, `g1s1`, `g1s2`, 25 cells; `g100`, 100 cells). All five
are applied to the same press-aligned windows at a 0.5 s stride. The split was inherited from a Room A screen on the
old per-link networks (19 September, `runs/constrained/fh/g2_multihead/results.json`: mixed four-head pool 60.00 %,
1 s-only three-head pool 58.33 %, one 0.5 s head 46.67 %; no interval) and never re-tested on the final recipe.

## Step 2 of the brief, checked

- **The rotation cells of the final recipe are `d4c_fuse_<rotation>`, not `d1sp_*`.** `stage_cells.json` registers
  `d4c_fuse` on the three rotations with the final recipe exactly (`aug` and `rrel` on, `arch` `fuse`, all five
  heads, base `d1sp`); `d1sp_*` are the base cells whose start-of-walk readers these cells use. Their five heads exist
  (`runs/dc2_results/cells/d4c_fuse_*/art_*/models`) and their decodes under the final variant exist
  (`d3/CR.relgateU+abstain+a2w0.25/`). They serve as MIX seed set 0 (training is deterministic here, as the dwell
  ablation's W0 showed byte for byte).
- **B1's window arrays:** both strides had been deleted (0.5 s on 1 October, 1 s in the 6 October cleanup).
  - **1 s:** re-cut from `data/` into `b1_recut/` (`pipeline.io.windows --stride 1.0 --sessions B1`, 2,622 windows,
    13:37 to 13:39); all seven `meta.json` files byte-identical to the surviving ones; the seven arrays moved to
    `runs/constrained/windows_s1.0_dc2/room_B/session_B1/` at 13:40, where none existed.
  - **0.5 s:** not needed. The 0.5 s networks train from the rotation cells' cached features (`shared05`), which
    resolve, as the dwell ablation's `half` trained on 6 October.
- **The cells' 1 s window views are broken** (they point at `data/windows`, moved on 7 October). This ablation builds
  its own views under `views/<rotation>/win10`, linked to `runs/constrained/windows_s1.0_roomA` and
  `windows_s1.0_dc2`, dropping the calibration recordings as `pd_cells.do_view` does. No cell is edited.
- **Load check (13:40):** rotation A1+B1 to A2 loads 2,300 training windows at 0.5 s (A1 1,122, B1 1,178) and 1,080
  at 1 s (A1 526, B1 554), the counts in `reports/tracking/2026-09-29_architecture.md` section 6.2.

## Arms

Ten networks per rotation and seed set, each one `g` job of `pd_cells.do_train_d2` on the rotation cell's options
(no position job: the decode never reads the position head). Seed set k adds 100 x k to each base seed.

| network | stride | cells | base seed |
|---|---|---|---|
| p05_s0, p05_s1, p05_s2, p05_s3 | 0.5 s | 25 | 0, 1, 2, 3 |
| p10_s0, p10_s1, p10_s2, p10_s3 | 1 s | 25 | 0, 1, 2, 3 |
| g100_05, g100_10 | 0.5 s, 1 s | 100 | 0 |

The pool's five slots per arm (equal weight, as shipped):

| arm | half slot | fh1s slot | g1s1 slot | g1s2 slot | g100 slot |
|---|---|---|---|---|---|
| **MIX** (shipped) | p05_s0 | p10_s0 | p10_s1 | p10_s2 | g100_10 |
| **ALL05** | p05_s0 | p05_s3 | p05_s1 | p05_s2 | g100_05 |
| **ALL1** | p10_s3 | p10_s0 | p10_s1 | p10_s2 | g100_10 |

Each arm has four distinct 25-cell networks and one 100-cell network. MIX seed set 0 is the recorded `d4c_fuse`
heads. Arms share networks where the recipe is the same (for example ALL1 and MIX share four).

## Data

The three training rotations only: A1+A2 to B1 (`d4c_fuse_0102_to_B1`), A1+B1 to A2 (`d4c_fuse_01B1_to_02`) and
A2+B1 to A1 (`d4c_fuse_02B1_to_01`). A3 and B2 are never read: `train_one.py` and `pd_cells.do_train_d2` both
assert it. Calibration recordings are excluded as in every cell.

## Evaluation

The dwell ablation's evaluator (`pd_repro_trace`'s `build`, `readers`, `infer` and `decode` steps, unchanged), on
the rotation cells, with the records' settings: prefix CR and the modules' default pace N(1.298, 0.123), which is
what `pace: None` meant when the rotation records were made. Every arm uses the same settings, so the paired
comparison does not depend on them. The default pace was measured on A1+A2+A3 anchors; disclosed, the same for every
arm.

**The plumbing check:** MIX seed set 0 decodes the recorded heads with nothing replaced and must reproduce each
rotation's recorded decode exactly (`pd_repro.decode_inner` exits 0 only then). If any of the three fails, training
stops.

**Metrics,** semi-constrained mode (one start press), per rotation (120 walks each) and pooled over the three (360):
committed-line error (100 minus percent correct), display lock, and the four edge lines (E_col1, E_col5, E_row1,
E_row5; 6 walks each per rotation) beside every pooled figure.

## Decision rule (fixed now)

**Primary:** ALL05 minus MIX and ALL1 minus MIX on pooled committed-line error, paired by seed set. Mean difference
and a 95 % t-interval over the three seed sets (t with 2 degrees of freedom, critical value 4.30).
- **better than MIX:** the whole interval below zero;
- **worse than MIX:** the whole interval above zero;
- **no measurable difference:** the interval includes zero.

**The stride mix matters** if either arm is better or worse than MIX under this rule. Otherwise it does not
measurably matter on these data.

**Secondary, reported, not changing the verdict:** the lock and the edge lines; per-rotation figures; for each arm, its
committed and lock percentages averaged over the seed sets, with a 95 % bootstrap interval over walks (1,000 draws,
seed 0, each draw resampling the walks and averaging correctness over the seed sets).

Every figure: development evaluation, all data seen (these rotations chose the decode variant on 29 September).

## Compute and safety

- About 42 networks at 0.5 s (about 7.5 min each on two sessions) and 33 at 1 s (about 3.5 min), so about 7 h of
  training, one network at a time on the GPU (`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.3`, `LOW 0.2`), under a watchdog that
  stops the run if system free memory falls below 15 % or a job's footprint passes 14 GB.
- 27 decodes (3 arms x 3 seed sets x 3 rotations) on the CPU, three niced workers, while training continues.
- Order: seed set 0 for every rotation first, then 1, then 2; within a rotation, MIX's networks, then ALL1's, then
  ALL05's, so complete arms decode as early as possible.
- `run.py` runs under nohup and holds `caffeinate -dimsu` for its own lifetime (Uzayr asked). A stopped run restarts
  where it stopped. Nothing under `data/`, `pipeline/`, `runs/dc2_results/` or `runs/live/` is written; no shipped file
  changes, whatever the result.

## Addendum, 8 October 2026, 14:27 SAST (clock read): B1's 0.5 s arrays restored, driver restarted

**What happened.** At 14:18 the plumbing check on rotation A1+A2 to B1 (MIX seed set 0, nothing replaced) failed
before its decode: the motion gate reads the test session's raw 0.5 s window arrays
(`recordings.gate_energy`), and B1's had been deleted on 1 October (only their `meta.json` survived). Training is
unaffected (it reads cached features). The driver stopped training as designed at 14:19, after five networks.

**The repair (an input rebuild; no change to arms, data, metrics or rule).** B1's 0.5 s press-aligned arrays were
re-cut with the shipped cutter (`y4_pressalign.cut_one`, as `dc2_run.do_cut` calls it; `recut_b1_05.py`) through the
DC2 tree's own data view, which links to `data/`. All seven `meta.json` files are byte-identical to the surviving
ones. A first cut read `data/` directly and differed only in the provenance field `rx_files` (the path recorded); its
arrays were byte-identical to the second cut's; it was deleted. The seven arrays were moved at 14:25 to
`runs/constrained/dc2_room_B_s0.5_pressalign/by_session/B1/windows/room_B/session_B1/`, where none existed; the
rotation cells' 0.5 s views then had no broken links.

**The restart.** The first driver (pid 84866) was stopped at 14:26 and a new one started (pid 88822, its own
caffeinate). Decodes the first driver had started kept running; the new driver waits for any decode of the same
rotation, arm and seed set still running before it starts one (`run.py`, evaluator). Finished networks were not
retrained. The B1 plumbing check resumes at its decode step from its kept scratch tree. No decode result had been
produced or seen when this was written.

## Addendum, 8 October 2026, 14:50 SAST (clock read): six decode workers

Each decode on the A1 and A2 rotations spends about an hour re-deriving the cross-fitted reader rows before its head
inference, so three workers would have left decoding running until about 01:00. The driver was restarted at 14:49
(pid 90804) with six decode workers; it also waits for any network still training from the previous driver rather than
start it again. Compute only: arms, data, metrics and rule unchanged. The B1 plumbing check had passed exactly at
14:32 (0 of 120 committed, display-lock and scorer-lock changes); no other result had been read.

## Addendum, 8 October 2026, 15:39 SAST (clock read): an early look, at Uzayr's request

Uzayr asked for the results so far. Shown to him at about 15:39: rotation A1+A2 to B1, seed set 0 only, all three arms
(committed, lock, edge lines, walk-bootstrap intervals, and the paired arm-minus-MIX differences on that one
rotation). Nothing else had been decoded (A1 and A2 rotations: not yet; seed sets 1 and 2: not yet). The run continues
unchanged to all three seed sets; the decision rule above is unchanged and is applied only to the complete set. Any
change to the run after this point would be decided after an early look and would be disclosed as such.

## Addendum, 8 October 2026, 17:18 SAST (clock read 17:18; first committed with 17:25 written before the clock was read): the readers step computed once per rotation

The decode's readers step (the test-side V0 reader and the cross-fitted reader rows, about an hour on the A1 and A2
rotations) does not depend on the arm. Checked before the change: its output files are byte-identical between ALL05
and ALL1 seed set 0 on the A1 rotation (3 of 3 files) and on the A2 rotation (3 of 3). From 17:18, `eval_one.py`
stores those files per rotation (`runs/<rotation>/readers_cache/`, seeded from the A1 and A2 ALL05 seed set 0 trees
and the B1 ALL05 seed set 1 tree) and copies them into each new decode's scratch tree in place of re-deriving them;
the trace records `from_cache`. The head inference and the decode are unchanged and still run for every arm. Compute
only: no result can change, since the inputs are byte-identical. Decodes already running finish as they were.

## Addendum, 8 October 2026, 19:31 SAST (clock read): normal priority after training, eight workers

Uzayr left the machine quiet and asked for both jobs to push on. The driver was restarted at 19:31 (pid 28519):
decodes started after the last network is trained run without `nice` (until then they stay niced, so training keeps
the fast cores), and up to eight decodes run at once. Compute only; arms, data, metrics and rule unchanged. Results read
so far: the 15:39 early look only (B1, seed set 0).

## Addendum, 8 October 2026, 19:40 SAST (clock read): a memory guard for the decodes

At Uzayr's request, `mem_guard.py` (pid 29880, started 19:40) pauses this ablation's newest decode (SIGSTOP, never a kill) whenever the system free-memory percentage falls below 25 %, one more per 15 s check, and resumes them at 40 %. Training keeps its own watchdog (stop below 15 %). Free memory was 52 % when it started. Compute safety only; nothing else changes.

## Addendum, 8 October 2026, 21:56 SAST (clock read): a second early look, at Uzayr's request

Uzayr asked how the results stood. Shown to him at 21:56: seed sets 0 and 1, complete on all three rotations, every arm (pooled and per rotation, committed, lock, edge lines, and the paired arm-minus-MIX differences over the two seed sets). Computed in memory with `score.py`'s functions; no results file was written. Seed set 2 was still training and decoding, every remaining network already queued; nothing in the run changed, and the decision rule is applied only to the complete set.

## Addendum, 8 October 2026, 22:35 SAST (clock read): the last four decodes, at normal priority

Training ended at 22:33 (75 networks, no failure). Four decodes remained (A2 ALL05 seed set 2; A1 MIX, ALL1 and ALL05
seed set 2), all running niced. The cause, found now: zsh's default BG_NICE option runs every background job at nice
+5, so every driver started with `&` ran at +5 and its `nice -n 5` decodes at +10. The 19:31 "normal priority after
training" change therefore never took effect. At 22:33 the driver (pid 28519) and the four decode trees were stopped
(own PIDs, checked) and `finish.sh` started them again with BG_NICE off (nice 0), resuming each from its scratch tree
(finished steps are skipped). A first restart at 22:34 still ran at nice 10 and was replaced at 22:35. The wrapper
holds caffeinate and the memory guard. Compute only; no result had been read beyond the two early looks.
