# The A3-clean lock on the shipped all-0.5 s heads (A3's sixth look), two checks, and the demo videos, 9 October 2026

**Status at 08:00 SAST (clock read).** All three parts of Uzayr's brief of 9 October are done:
- the A3-clean lock side was re-selected on the new heads and A3 decoded once with it;
- the two checks are answered;
- the demo videos have their `ACCEPTANCE.md`, and the old renders are retired.

The machine has been QUIET since 07:58.

**Where everything is:** `runs/a3_clean_0p5_2026-10-09/` (the lock side and the A3 decode) and
`runs/live/renders_K1g_0p5/ACCEPTANCE.md` (the videos).

**Nothing shipped changed.** The live app, `FINAL_CONFIG.md`, the model sets, the hash lists, `stage_cells.json`, the
shipped cells' records and every existing replay were hashed before and after the A3 decode: 175 files, all identical.
B2 and the zero-shot model were not decoded. The tables stay on the shipped app.

**Every figure here** is a development evaluation, all data seen (the rotations, and B2, decoded on 8 and 9 October).
The A3 figure of section 1.3 is A3's sixth look.

## 1. The A3-clean lock side on the shipped all-0.5 s heads

### 1.1 What was done, in order

| step | when (9 Oct) | record |
|---|---|---|
| addendum to the 8 Oct PREREG (same rule; new heads, new cells, new reference), committed before anything ran | 07:01 | `ADDENDUM.md` (62369e46), 24a4358b |
| three rotation cells `f05r_*` built beside `d4c_fuse_*` and registered in memory (not in `stage_cells.json`) | 07:08 | `reg.py`, `build_rot.py` |
| plumbing: each new cell, with the old heads, reproduces `d4c_fuse_*/d3/DT0` exactly (120 of 120 on all three) | 07:09 to 07:11 | `logs/plumb_*.json` |
| the four slots swapped for the ALL05 seed set 0 networks (byte-checked), 12 GPU inferences one at a time | 07:11 to 07:16 | `SWAPPED_0p5.json` in each cell |
| the new reference `D05` on each rotation (shipped display settings, DT0 settings, new heads) | 07:16 to 07:18 | `cells/f05r_*/d3/D05.*` |
| the 32-arm grid on the three rotations: 96 decodes, the shipped arm reproducing `D05` exactly on all three | 07:19 to 07:40 | `lock/SELECTION.json` |
| `A3_CLEAN_CONFIG_0p5.md` hashed and committed, before A3 was touched | 07:41 | d942cb16, 2c701274 |
| A3 decoded once through the live app with it (A3's SIXTH look) | 07:41 to 07:57 | `a3_lock/RESULT.json` |

**One false start, disclosed.** The grid first started at 07:18. It stopped before any decode, on a check in my own code
that compared the registered cell names in the wrong order. I fixed the check and restarted at 07:19. Nothing had been
written.

**The readers came from `d4c_fuse_*`.** The d1sp twin cells, whose start-of-walk reader files the cells copy, were
removed in the 6 Oct cleanup. `d4c_fuse_*` holds those files byte for byte (alias `V0`), so they were copied from there.
The plumbing check, which passed, covers this.

**A cross-check.** On B1, the new reference equals the stride ablation's ALL05 seed set 0 figures exactly:
committed 69.17, lock 44.17. On A2 and A1 the locks are equal and the committed line differs by one walk, as expected,
because the ablation used the modules' default pace and the older reader map.

### 1.2 The selection on the rotations (no A3 anywhere)

**No input naming session 03 was opened by any of the 96 decodes.** The one exception is A3's ground-truth sidecars,
which `paths.load_paths` opens for the line geometry; the geometry was checked to be session 01's alone on every decode.

**What could change:** only the display decode, which the lock and the dot read. Every committed line equals the
reference on all 96 decodes.

| setting | shipped | chosen without A3 | the test (rotation-weighted display lock) |
|---|---|---|---|
| display spread | 4.5 | **3.0** | S1, the argmax: 52.50 at 3.0, against 52.29 at 3.5, 52.08 at 2.5 and 4.0, 51.88 at 4.5 and 5.0, 51.67 at 5.5 and 6.0 |
| soft entry | soft | soft | S2: soft minus free +0.42 [-1.46, +2.08], not worse, so soft stays |
| 1.0 m entry window | 1.0 m | 1.0 m | S3: window minus none +20.00 [+16.04, +24.17], better, so the window stays |

**The curve is nearly flat.** It spans 51.67 to 52.50 over the whole grid, which is 0.8 points, about one walk in the
weighted sum. On the old heads (8 Oct) the choice was 2.5, out of a four-way tie at 51.25.

### 1.3 Its effect on the rotations

| | chosen (3.0) | shipped (4.5) |
|---|---|---|
| display lock, rotation-weighted | 52.50 | 51.88 |
| display lock, chosen minus shipped (paired, walks resampled within rotations, 1,000 draws) | +0.62 [-0.62, +1.88] | |
| committed line, rotation-weighted | 76.88 | 76.88 (the same line on every walk) |

| rotation | lock, chosen | lock, shipped | walks gained / lost | lock edges E_col1 / E_col5 / E_row1 / E_row5, chosen | the same, shipped |
|---|---|---|---|---|---|
| A1+A2 -> B1 (weight 2) | 43.33 | 44.17 | 0 / 1 | 66.7 / 66.7 / 0.0 / 50.0 | 66.7 / 66.7 / 0.0 / 50.0 |
| A1+B1 -> A2 | 73.33 | 72.50 | 1 / 0 | 83.3 / 50.0 / 100.0 / 50.0 | 66.7 / 50.0 / 100.0 / 50.0 |
| A2+B1 -> A1 | 50.00 | 46.67 | 4 / 0 | 0.0 / 66.7 / 83.3 / 0.0 | 0.0 / 50.0 / 83.3 / 0.0 |

**Pooled over the 360 walks**, the lock edges are 50.0 / 61.1 / 61.1 / 33.3 against 44.4 / 55.6 / 61.1 / 33.3. The two
gains on the edges are one walk each (E_col1 on A2, E_col5 on A1). The committed edges are unchanged.

### 1.4 A3, decoded once with the A3-clean lock side (A3's SIXTH look)

**How it was run:**
- the live app, model set `final` (the shipped all-0.5 s heads, cell `f05_A3`, 454 files manifest-checked);
- semi mode (one start press per walk), the as-it-arrives clock, display K1g, scored by `app_score`;
- one change, set in the replay processes only after the config's hash was checked: the display spread 3.0. The entry
  and window are the shipped values;
- every LiveDisplay built was checked to carry (3.0, soft, 1.0 m).

**The comparison** is against the shipped A3 replay (`runs/live/replay/final/semi_disp-K1g_causal_realtime_screen`),
the same 120 walks. The intervals are app_score's bootstrap over walks (1,000 draws, seed 0).

| | A3-clean lock side (spread 3.0) | shipped (spread 4.5) |
|---|---|---|
| **lock** | **75.00 [67.48, 82.50]** | 75.00 [67.48, 82.50] |
| lock, clean minus shipped | **0.00 [0.00, 0.00]**: the same line on all 120 walks, 0 gained, 0 lost | |
| lock edges E_col1 / E_col5 / E_row1 / E_row5 (6 walks each) | 33.3 / 100.0 / 100.0 / 83.3 | the same |
| committed line | 92.50 [87.50, 96.67], the same line on all 120 walks, 0 differ from the FC record | 92.50 |
| committed edges | 66.7 / 66.7 / 100.0 / 100.0 | the same |
| the drawn dot | 8,025 of 8,025 dots identical | |

**Why nothing moved.** The spread widens the display decode's along-line step. On these heads, 3.0 and 4.5 give the same
display path on every A3 walk, so the lock and every dot are the same. On the rotations the same change moved the locked line
on 9 of 360 walks, 6 of them between right and wrong.

**The change was in effect.** The display decode calls `night_track` with `LiveDisplay.cfg_disp`, which carried 3.0 in
every process. On 8 Oct, the same in-process route at spread 2.5 moved two A3 locks on the old heads.

**The render rules:** none broken (park, together, anchor in its glide form, one lock, at most one switch); 3 switches;
the largest draw lag 0.153 s.

### 1.5 The A3 label under our rules

**The rule (8 Oct, `reports/tracking/2026-10-08_a3-clean.md` section 6):** the display label OPTIMISTIC leaves a lock
figure when every display setting the lock reads is chosen without A3, or shown equivalent to a training-derived value.
Those settings are the cap, the spread, the soft entry and its window.

**The A3 lock is A3-clean as it stands. Drop OPTIMISTIC from the A3 lock (75.00 [67.48, 82.50]).**
- The settings chosen without A3 give the shipped lock on every one of A3's 120 walks.
- So the figure in the tables, from the shipped app, is the A3-clean figure, and no table number changes.
- Suggested wording: "A3 lock 75.00 % [67.48, 82.50]; with the display settings the lock reads re-chosen on the
  development rotations without A3, the lock is the same on every walk (A3's sixth look)".

**The A3 dot error stays OPTIMISTIC.** The display's phase, switch arm, prior and head choice were chosen on data that
included A3 (`reports/tracking/2026-09-30_display-provenance.md`). The spread and entry are no longer on that list. The
dot side is the Second Overall chat's work (`runs/a3_clean_2026-10-08/PREREG_DOT_ADDENDUM_1.md`). Its full A3-clean
decode, if it runs, is A3's SEVENTH look.

**A3 in general:** the 30 Sep sentence stands: "clean in weights and fitted statistics, exposed in design choices".
Decision-side choices made on folds with A3 still feed the lock (`normalise`, the HMM's structure, the Config defaults,
pooling, the head recipe). B2 remains the headline.

**The look count:** A3 has now been decoded six times, B2 four.

## 2. Two checks

### 2a. Are the five heads still distinct? Yes.

**The seeds are 0, 3, 1, 2, 0 for `half`, `fh1s`, `g1s1`, `g1s2`, `g100`.** Since 9 Oct every head has the same stride
(0.5 s) and the same recipe (`pd_cells.do_train_d2`, 24 epochs, augmentation on). Two pairs could collide.

- **`half` and `fh1s`.** They are the same task (25 cells), so at the same seed they would be the same network. Last
  night's recipe check showed training is deterministic on this machine (`half` retrained came out byte-identical to the
  shipped file). That is why the ship put the seed-3 network in the `fh1s` slot.
- **`half` and `g100`.** These two do share stride, seed and recipe. They are still different networks, for two reasons.
  - **The task differs.** `half` is trained to name one of 25 cells (1 m grid) and `g100` one of 100 cells (0.5 m grid),
    on different labels.
  - **The output layers differ.** `g100` has 105,995 parameters against 86,645, because its classifier and auxiliary
    layers end in 100 outputs, not 25.

**What they do share is the starting point.** With the same seed, the shared encoder starts from the same random weights.
After training, the first layer of `half` and `g100` still correlates at 0.89 (any other pair: -0.05 to +0.10).

**What matters for the pool is the outputs, and those are no more alike than any other pair's.** On B2's 1,238 walking
windows, I mapped `g100`'s 100 cells onto the 25 and compared argmax cells:

| pair | same argmax cell | median distance between expected positions |
|---|---|---|
| `half` / `g100` | 62.2 % | 0.38 m |
| the nine other pairs (all different seeds) | 58.2 % to 76.0 % | 0.22 m to 0.50 m |

**So the pool does not count one head twice.** `half` and `g100` are the least independent pair in weight space, but the
fact is not new. In the old pool, `half`, `fh1s` and `g100` were all seed 0, and all three pairs had first-layer
correlations of about 0.89.

### 2b. Fully constrained B2 (96.67) against semi (97.50): three walks, not one

**The end press does not move the lock.** The lock is 71.67 in both modes, the same line on all 120 walks.

**The committed line differs on three walks.** Full mode wins one and loses two, a net loss of one walk (116 against 117
of 120).

| walk (report code) | true | semi | full | walk length | semi's own exit, relative to the end press |
|---|---|---|---|---|---|
| PA1 (PA1), walk 18 | C_rev | C_fwd (wrong) | **C_rev (right)** | 6.3 s | 5.80 s before it |
| PA6 (PA6), walk 1 | B_fwd | **B_fwd (right)** | D_fwd (wrong) | 3.9 s | 1.05 s after it |
| PA6 (PA6), walk 10 | B_fwd | **B_fwd (right)** | D_fwd (wrong) | 3.8 s | 1.66 s after it |

**Why the end press helped once.** On PA1's walk 18 the decoder's causal exit fired 0.5 s after the start press. Semi
committed C_fwd on about 1.5 s of evidence. Full mode waited for the end press and rescored the whole 6.3 s walk.

**Why it hurt twice.** The two modes stop reading the radio at different times.
- **Full mode** rescores each walk on the windows whose centres are at or before the end press
  (`final_model._full_due`). By construction, it never reads the radio after the press.
- **Semi mode** commits at the decoder's own exit. On PA6's two short walks that exit came 1.05 s and 1.66 s after
  the end press. So semi's decision also used two or three more windows (0.5 s stride) in which the walker is standing at
  B's end point, (5, 2.5).
- **Those end windows decide the case.** B_fwd and D_fwd both start on the left edge and both cross the centre. Both
  walks also began in a way that read as the top-left corner (both locked E_row5). Without the end windows, the rescore
  picked D_fwd, the line that ends at (5, 0).

**The same pattern on A3, where both modes score 92.50.** Four walks differ, two each way.
- Full mode lost PA3 walk 1 (B_fwd to D_fwd again) and PA2 walk 2. In both, semi's exit came 0.58 to 0.74 s after
  the press.
- It won PA1 walk 7, where semi's exit fired 0.73 s early, and PA5 walk 7.

**Across the seven walks where the modes disagree:**
- in the two where semi's exit fired before the end press, the end press was right both times;
- in the five where the exit came after the end press, semi was right in four.

**It is a trade, not a defect.** The fully constrained figure is a bound on a walk that ends at the press, and some
walks' evidence runs past the press. A three-walk swing is within either figure's interval: full 96.67 [93.31, 99.17],
semi 97.50 [94.17, 100.00] (development evaluation, all data seen).

## 3. The demo videos (`runs/live/renders_K1g_0p5/`)

**`ACCEPTANCE.md`** is written by the shipped generator (`pipeline/live/app_acceptance.py`, unchanged), in the old
file's form. Every row is that replay's own log, scored by `app_score`, with the render-rule counts from `rule_checks`.
`runs/a3_clean_0p5_2026-10-09/acceptance_renders.py` then adds one column: the report's code beside tracking's P1 to P6
(`anon_map.json`, and the PA codes by surname from `reports/project/2026-10-06_handoff.md`):

| P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|
| PA4 PA4 | PA1 PA1 | PA3 PA3 | PA5 PA5 | PA2 PA2 | PA6 PA6 |

**The render rules hold on all twelve videos:** 0 park, 0 together, 0 anchor, 0 lock changes and 0 walks with more than
one switch. The draw lag is at most 0.153 s.

**Frames checked by eye.** I pulled frames from `final_semi_A3_P5.mp4` (PA2, PA2) and `final_semi_B2_P2.mp4`
(PA1, PA1). The frame times came from each replay's log (first press minus 3 s, 10 fps, the cut between the two
halves of each session removed). They show what the log says.

- **A3 P5, frame 0:** the room, the twelve lines, the nodes, "waiting for the first press".
- **A3 P5, walk 7, the lock (1:58):** E_col5 is drawn blue, which is wrong (the true line is D_rev). The red dot is on
  E_col5 at its entry, with the green dot (the walker 2 s ago) beside it at the bottom-right corner.
- **A3 P5, the switch (2:00):** the line turns orange, "switched to D_rev", and the red dot slides across from E_col5.
- **A3 P5, the end of walk 7 (2:03):** both dots are together at D_rev's end, (0, 5).
- **B2 P2, walk 13 (3:44 to 3:48):**
  - the lock is B_fwd, with the red dot at (0, 2.5) while the walker is at the bottom-left;
  - the switch to C_fwd comes at the centre;
  - then both dots travel together up C_fwd.
- **B2 P2, the last frame:** walk 20 shows the green "RIGHT" banner ("committed at the causal exit: D_rev, drawn: D_rev
  (agrees), true: D_rev"). The red dot stops on D_rev about 2 m short of its end, because in semi mode a walk's frames
  end at the app's causal exit (`reports/tracking/render-rules.md`).

**The two most worth watching:**
1. **`final_semi_B2_P3.mp4` (PA3, PA3).** This is the headline session. All 20 committed lines are right and 16 of 20
   locks are right, with the lowest dot error of the twelve (median 0.388 m, 0.257 m on correct-lock walks). It shows
   the system as it usually is.
2. **`final_semi_A3_P5.mp4` (PA2, PA2).** This is the other room, and the only video with both outcomes of the one
   switch. Walk 7 (about 1:58) is a wrong lock that the switch corrects. Walk 17 (about 4:29) is a switch to the wrong
   diagonal. Committed 18 of 20, lock 16 of 20.

`final_semi_B2_P2.mp4` (PA1, PA1) is the alternative if you want both from B2. Its walk 13 is a corrected lock, at
about 3:44.

**The old renders** are moved, not deleted. `runs/live/renders_K1g/` is now `runs/live/retired/renders_K1g/` (all 13
files, by `git mv`). `runs/live/retired/README.md` says what it was and what replaced it. Reports written before today
still name the old path, and it resolves there.

## 4. For the report

**No table number changes.** Only one label changes: drop OPTIMISTIC from the A3 lock (75.00 [67.48, 82.50]). Add the
sixth-look sentence of section 1.5, and keep the dot's OPTIMISTIC label.

**The numbers, with the report's codes** (development evaluation, all data seen; trained on A1, A2 and B1; tested on A3
and B2, never trained on; no labelled same-day calibration):
- **The A3-clean lock side:** chosen on the rotations without A3, spread 3.0, soft entry, 1.0 m window. On the rotations
  it gives +0.62 [-0.62, +1.88] display lock over the shipped 4.5.
- **On A3** it gives 75.00 [67.48, 82.50], the shipped figure on every walk (paired 0.00 [0.00, 0.00]). The lock edges
  are 33.3 / 100 / 100 / 83.3 and the committed edges 66.7 / 66.7 / 100 / 100.
- **Fully constrained against semi on B2:** 96.67 [93.31, 99.17] against 97.50 [94.17, 100.00]. The end press fixed
  PA1's walk 18 and lost PA6's walks 1 and 10.
- **The five heads are five networks.** `half` and `g100` share stride, seed and recipe but not their task (25 against
  100 cells) or their output layers. Their outputs agree no more than any other pair's.
