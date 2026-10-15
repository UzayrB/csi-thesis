# PLAN note 3: B2's no-press replays join its fifth look. Written 10 October 2026, 09:07 SAST (clock read), before any decode

**Applies to:** `PLAN.md` (5f13034c), section 4 (the looks), after PLAN_NOTE_1.md (the detector pinned at 4.5).

**Uzayr's answer** (to the Mastermind directly, relayed verbatim about 09:06):

> "Yes. Replay B2's no-press mode under the clean display as part of its fifth look, and leave A3's no-press lock
> labelled "earlier display". The detections and committed lines must match the shipped ones exactly, or the run stops
> as planned. The label goes beside the A3 no-press lock wherever it's quoted, and A3's detections and committed lines
> stand as they are."

## What runs

- **The replays:** B2 and zero-shot B2 in no-press mode under the clean profile (the detector pinned at spread 4.5):
  12 recordings, one niced process each, through the app's CLI (`--presses none`).
  - **New folders:** `runs/live/replay/{final,zeroshot}/unconstrained_m4_disp-K1gf_causal`.
  - **When:** after the semi fifth looks, within the 6-process share.
  - **What they count as:** part of B2's and zero-shot B2's FIFTH looks (one configuration, another mode of the same
    app).
- **The scoring:** `app_score.score_unconstrained`, unchanged, pointed at the K1gf folders by `run.py score_nopress`
  (a link named `unconstrained_m4_causal` in this folder's `_scoreroot`; dry-tested at 09:06 on a scratch copy of the
  shipped folder, where it reproduced the shipped score exactly).
- **The step:** `run.py nopress` writes NOPRESS.json and refuses to run before the semi fifth looks PASSED.

## The STOP rule

The detections and the committed lines must be identical to the shipped no-press replays on every walk, final and
zero-shot, compared row for row: every `detected_start` row and every `committed` row. Any difference stops the work, and
the Mastermind is messaged. Only the no-press lock may move.

## What is reported

- **The no-press lock on detected walks,** paired against the shipped figure (B2 64.29 %, 27 of 42; zero-shot B2
  59.38 %, 19 of 32), each with its Wilson 95 % interval, as the report uses. Beside it: the paired difference (a
  bootstrap over the matched walks, 1,000 draws, seed 0) and the discordant counts.
- **Lock correct and detected,** shipped against new, with Wilson intervals.
- Every figure is labelled "development evaluation, all data seen".

## A3

- **No replay.**
- **In the report-update file,** the A3 no-press LOCK carries "measured with the earlier display" beside it wherever it
  is quoted: Results, Discussion, every table and sentence.
- **A3's no-press detections and committed figures** stand unlabelled.
