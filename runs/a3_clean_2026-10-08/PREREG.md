# PREREG, lock side: the display decode's spread and entry, re-selected without A3. Written 8 October 2026, 17:06 SAST (clock read)

**Status.** Written before any selection run. Its SHA-256 is recorded in `PREREG.md.sha256` and in the commit that adds it,
and it is never edited afterwards; anything later goes in a dated addendum file.

**The brief:** Uzayr's "an A3 figure with every display setting chosen without A3", 8 October (Phases 1 and 2), run in the
second-work chat. The go for the lock side and the requirement in section 2 came from the primary chat (Overall), 8 October.
**Phase 0:** `PHASE0.md` (16:58), which lists the eight A3-touched display settings.

**Scope.** The LOCK SIDE only: settings 1 to 3 of PHASE0.md (the spread, the soft entry, the 1.0 m entry window). The dot side
(settings 4 to 8) waits for Uzayr's answers on PHASE0.md findings 1 to 3 and the compute budget, and gets its own
pre-registration. **A3 is not decoded** by anything here (Phase 3 is a hard stop). **Nothing shipped changes:**
`runs/dc2_results/rule/FINAL_CONFIG.md`, the frozen networks, `pipeline/live/final_model.py`'s defaults and every existing
result, render and report are only read.

## 1. The data: the development rotations, and nothing that contains A3

| rotation | cell | test | weight |
|---|---|---|---|
| A1+A2 -> B1 | `d4c_fuse_0102_to_B1` | B1 | 2 |
| A1+B1 -> A2 | `d4c_fuse_01B1_to_02` | A2 | 1 |
| A2+B1 -> A1 | `d4c_fuse_02B1_to_01` | A1 | 1 |

- **The decode:** the 15:39 model's rotation form, exactly as the records `cells/<cell>/d3/DT0.relgateU+abstain+a2w0.25`
  were made (`pd_dt` arm 0, through `pd_clean.decode_inner`): variant relgateU + abstain + A2 weight 0.25, the clean reader
  map, the cells' cached posteriors, `pd_decode.inner` unchanged, on the CPU.
- **The pace: the frozen A1+A2 value** N(1.30341, 0.11255) (`runs/dc2_results/final/PACE_A1A2.json`), as in the final model
  and DISPLAY_PREREG section 3. Not the modules' default N(1.298, 0.123) that the `CR.` records used: that value was fitted
  on A1+A2+A3 anchors, so selecting with it would put an A3-fitted statistic into the selection decode.
- **The readers** (A2 start term, abstain) are fitted fresh in the decoding process and kept in memory across arms;
  `pd_clean`'s reader cache is neither read nor written.
- **No input names session 03,** checked from an audit trace of every file the decode opens. The one exception is
  documented and checked: `paths.load_paths` opens A3's six ground-truth sidecars but takes each line's taped endpoints from
  the first sidecar naming it, session 01's (the 29 Sep leakage audit, note 1). Each run asserts that the twelve lines equal
  session 01's sidecars alone. Any other A3-named input stops the run.
- **The driver:** `lock_side.py` in this folder. It writes only under this folder: an audit hook refuses any other write.

## 2. What may change, and what may not

**Each arm changes the DISPLAY decode only:** the decode `night_track(..., want_display=True)` that the display lock and the
drawn dot read.
- **The spread** enters through the variant's `sd<x>` part, which only `cfg_disp` reads.
- **The entry** enters by replacing `opts["entry"]` and `opts["entry_window_m"]` in that call only.

**The committed decision's decode is passed through unchanged** (its entry stays soft with the 1.0 m window). The A3 committed
figure carries no OPTIMISTIC label, so nothing chosen here may move a committed answer.

**Required on every arm and every rotation:** the committed lines equal the record `DT0.relgateU+abstain+a2w0.25`, 120 of 120.
An arm that moves any committed line stops the run.

**The plumbing check (first, on every rotation):** the shipped arm (sd 4.5, soft, 1.0 m) reproduces the record exactly:
committed line, display lock and scorer lock, 120 of 120 each. If it fails on any rotation, nothing is selected and the run
stops.

**Also reported, not gating:** the shipped spread's other values against the 30 Sep records `SD.relgateU+abstain+a2w0.25+sd<x>`
(same pace and map). A difference is investigated before the selection is written.

## 3. The arms

The full grid is decoded on every rotation in one pass per rotation, so the readers are fitted once. The selection reads
only the arms section 4 names; the rest are reported as a sensitivity table and select nothing.
- **sd_scale:** 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0 (the original grid, DISPLAY_PREREG section 3);
- **display entry:** soft, free;
- **display entry window:** 1.0 m, none.

That is 32 arms x 3 rotations.

## 4. The selection, in this order

Each step holds the earlier steps at their new values and the later ones at their shipped values.

**The objective throughout: rotation-weighted display-lock accuracy,** (2 B1 + A2 + A1) / 4, over the 120 evaluated walks of
each rotation (the display lock from `scorerlock.json`).

**The paired interval throughout:** the per-walk difference in display-lock correctness, weighted over the rotations as above.
It is a 95 % percentile bootstrap, 1,000 draws, seed 0, walks resampled within each rotation (DISPLAY_PREREG section 3,
`pd_dt._paired`'s method).

**S1, the spread.** The display entry is held soft with the 1.0 m window. Selection: the argmax over the grid, and exact ties go
to the smallest spread (DISPLAY_PREREG section 3, unchanged).
- **Disclosed:** this curve was computed on 30 Sep on the same rotations (argmax 2.5; 2.5 to 4.0 tie at 51.25). The re-run
  touches no test data and is expected to reproduce it.

**S2, the soft entry.** Soft against free, at S1's spread, with the 1.0 m window held. The rule is r2_softentry's, a
non-inferiority test:
- **soft ships** if the interval of (soft minus free) contains zero or lies above it;
- **otherwise free.**

**S3, the 1.0 m entry window.** The window against none, at S1's spread and S2's entry. The rule is q4_arms', a superiority
test:
- **the window ships** only if the interval of (window minus none) lies entirely above zero;
- **otherwise none.**

**The result** is the A3-clean lock side: (S1, S2, S3). It is written to `lock/SELECTION.json`, then to `A3_CLEAN_CONFIG.md`,
which is hashed and committed. The dot side is added to that file later, under its own pre-registration.

## 5. Deviations from the original procedures, fixed now

- **The objective is the display lock, not committed-line accuracy.** The original r2 and q4 decisions read committed-line
  accuracy because the entry then fed one decode. Here the committed decision is fixed (section 2), so the only accuracy the
  entry can move is the lock's. This is the brief's own objective for lock settings.
- **The interval.** The original r2 interval was a cluster bootstrap on the median of per-pairing deltas over nine pairings,
  and q4's was over seven held-out folds. Three rotations are too few clusters for that, so the walks are resampled within
  each rotation, as DISPLAY_PREREG section 3 did.
- **Not ported: the r2 and q4 substitution guards.** Both scored the committed decision's end time under substitution, which
  is fixed here by construction.
- **The pace and the readers** (section 1): the A1+A2 pace, and readers fitted fresh.

## 6. Reported

Every figure is labelled "development evaluation, all data seen": these rotations chose the decode variant on 29 Sep, and the
spread curve was seen on 30 Sep.
- **For the A3-clean lock side and for the shipped one,** per rotation (120 walks), weighted and pooled (360):
  - the display lock, the committed line (unchanged by construction) and the scorer lock;
  - the four edge lines E_col1, E_col5, E_row1 and E_row5 (lock and committed), beside every pooled figure;
  - the paired lock difference, A3-clean minus shipped, with its interval.
- **The S1 curve; S2 and S3's paired differences** with intervals, passes gained and lost per rotation.
- **Every arm's weighted and pooled lock,** as the sensitivity table.

## 7. Stops

The run stops, and nothing is selected, if any of these happens:
- the plumbing check fails on any rotation;
- any arm moves any committed line;
- any input naming session 03 is opened, beyond the documented sidecars;
- the line geometry is not session 01's alone;
- the guard refuses a write outside this folder;
- system free memory falls below 25 % before a long step. That pauses the run, and the primary chat is told.

## 8. Compute

- CPU only (`pd_clean.force_cpu`, one thread per process), `nice -n 10`, at most 2 processes at once, alongside the stride
  ablation's GPU run.
- Order: B1 and A2 first, then A1.
- Expected: the readers about 1 h on each Room A rotation, then about 0.5 min per arm.
