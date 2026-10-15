# A3-clean lock side on the shipped all-0.5 s heads: addendum, written 2026-10-09 07:01 SAST (clock read), committed before anything runs

**Why.** The A3-clean lock side of 8 October (`runs/a3_clean_2026-10-08/`, spread 2.5, soft entry, 1.0 m window) was
selected on the development rotations with the OLD pool heads (one at 0.5 s, four at 1 s). On 9 October the live app
shipped the all-0.5 s heads (`bba8adc8`), so A3's lock is OPTIMISTIC again. Uzayr's brief of 9 October asks for the
selection to be re-run on the shipped heads and A3 decoded once with the result.

**The rule is unchanged.** It is `runs/a3_clean_2026-10-08/PREREG.md` (SHA-256 bf0284de..., committed in 9f8972ae on 8
October before any selection run), sections 1 to 7 as written:
- the three development rotations (A1+A2 to B1, weight 2; A1+B1 to A2; A2+B1 to A1), nothing containing A3;
- the decode of the rotation records (variant relgateU+abstain+a2w0.25, the clean reader map, the frozen A1+A2 pace,
  readers fitted fresh, CPU), changing the DISPLAY decode only;
- the 32-arm grid (sd_scale 2.5 to 6.0; soft or free entry; 1.0 m window or none);
- S1 the spread (argmax of the rotation-weighted display lock, ties to the smallest), S2 soft against free
  (non-inferiority), S3 the window against none (superiority), paired bootstrap over walks within rotations, 1,000 draws,
  seed 0;
- the stops of section 7.

## What changes: the heads, and therefore the cells and the reference

- **The heads in each rotation are the shipped recipe at 0.5 s with the shipped seeds:** `half` is the rotation cell's own
  (unchanged); the `fh1s` slot holds the seed-3 network, `g1s1` seed 1, `g1s2` seed 2, `g100` (100 cells) seed 0. These are
  the stride ablation's ALL05 seed set 0 networks (`runs/ablations/stride_mix_2026-10-08/runs/<rotation>/p05_s3_k0`,
  `p05_s1_k0`, `p05_s2_k0`, `g100_05_k0`, committed in 65e22a80), trained by `pd_cells.do_train_d2` on the rotation cells'
  options, exactly as the shipped heads were trained on A1+A2+B1. None is retrained.
- **New rotation cells** `f05r_0102_to_B1`, `f05r_01B1_to_02`, `f05r_02B1_to_01`, built beside `d4c_fuse_*` exactly as the
  shipped `f05_*` cells were built beside `fin_*`: view, the old cell's weights copied byte for byte, the twin's readers,
  the cross-fitted rows. They are registered in memory inside each process that uses them, NOT in
  `runs/dc2_results/stage_cells.json` (the shipped model's hash lists cover that file).
- **Plumbing, before any swap:** each new cell, holding the old heads and their posteriors, decodes under the DT0 settings
  and must reproduce `d4c_fuse_<rotation>/d3/DT0.relgateU+abstain+a2w0.25` exactly (committed line, display lock, scorer
  lock, 120 of 120). If not, stop.
- **Then:** the four slots swapped for the networks above (byte-checked), the five heads inferred on the GPU (as every cell
  was), and the cell's own reference decoded with the shipped display settings (sd 4.5, soft, 1.0 m) under the DT0 settings,
  prefix `D05`. **This reference replaces DT0 in PREREG sections 2 and 7:** the plumbing check is the shipped arm
  reproducing it exactly, and every arm's committed lines must equal it.
- **Not repeated:** the comparison with the 30 September `SD.*` records (they hold the old heads).

## After the selection

The selected lock side is written to `A3_CLEAN_CONFIG_0p5.md`, hashed and committed **before A3 is touched**. Then A3 is
decoded ONCE through the live app (model set `final`, now the all-0.5 s heads), semi mode, as-it-arrives clock, display
K1g, with the selected display settings set in that process only, scored by `app_score`. **That is A3's sixth look.** The
paired lock difference is taken against the shipped A3 replay (lock 75.00). Nothing shipped changes: the live app, B2 and
the zero-shot model stay on the shipped settings; `FINAL_CONFIG.md`, the model sets and the hash lists are hashed before
and after.

## Compute

CPU for the decodes (at most 4 processes, `nice -n 10`), the GPU only for the 15 short head inferences, one at a time. One
caffeinate held for the whole job. `runs/MACHINE_STATE.md` is updated before and after each step. Writes: this folder and
the three new rotation cells only.
