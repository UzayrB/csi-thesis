# Addendum to PREREG_postDC2_training_2026-09-28: recipe-matched Room A comparators. POST HOC

**Written 2026-09-28 from 09:15 SAST (clock read), before any item 4 cell produced a result.** Item 4
had not started training: its first cell, 4ii_B2, had only its view built. Items 2 and 3 were done.
This adds comparators and changes no pre-registered cell or comparison.

## What was found

**The training-path plumbing check** (`plumbT_A2`) trained Room A session 01 fresh through the item 3
and 4 harness and compared it with the shipped `s01_to_s02` fold:
- **The four 1 s heads' weights are bit for bit identical** to the shipped ones. The harness's views,
  features, sessions and training code are therefore the shipped path.
- **The 0.5 s g25 head and its position head differ.** The shipped Room A folds' 0.5 s heads were
  trained on the grid-lattice windows and copied into the press-aligned tree (`y4_pressalign`: "The
  shipped weights are COPIED in"). The frozen DC2 heads, whose recipe this pre-registration adopted
  (`d5_train_room_a`), train the 0.5 s head on the press-aligned windows. The harness does the same.
- **The size of that difference on `s01_to_s02`:** 96 of 120 committed decisions equal. Committed
  accuracy 69.17 against the shipped 73.33, paired −4.17 [−10.83, 2.50]. Drawn lock 58.33 against
  55.83. Recorded in `runs/dc2_results/plumbT_A2.json`.

**So the Room A comparators named in sections 4 and 5, the existing folds, are not the same recipe as
the cells they are compared with.** The B rows' column (i), item 2a, is the same recipe.

## What is added

Room A comparators trained through the same harness and recipe, reported **beside** the
pre-registered comparators, never instead of them:

| added | train | test | beside |
|---|---|---|---|
| 4i_A1 | A2+A3 | A1 | item 4 column (i), A1 row (`s0203_to_s01`) |
| 4i_A2 | A1+A3 | A2 | item 4 column (i), A2 row (`s0103_to_s02`) |
| 4i_A3 | A1+A2 | A3 | item 4 column (i), A3 row (`s0102_to_s03`) |
| 3ref_* | one Room A session | another | item 3's six single-day pairings (`plumbT_A2` is `s01_to_s02`) |

- **Scheduling:** they run after the ten pre-registered item 4 cells, one training job at a time.
- **Reporting:** for the Room A rows, (ii) minus (i) and item 3's comparison are reported twice,
  against the pre-registered comparator and against the recipe-matched one.
- **Reader rule:** as in every harness cell, the test session's reader features come from the cell's
  own heads.
