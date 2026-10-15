# A3_CLEAN_CONFIG_0p5: the display settings chosen without A3, on the shipped all-0.5 s heads. Lock side, 9 October 2026, 07:40 SAST (clock read)

**Status.** The LOCK SIDE only, selected exactly as `runs/a3_clean_2026-10-08/PREREG.md` (SHA-256 bf0284de..., committed in 9f8972ae on 8 October) fixes, on the shipped all-0.5 s heads, with this folder's `ADDENDUM.md` (SHA-256 62369e46..., committed in 24a4358b before anything ran). Written, hashed and committed before A3 is touched.

**Not adopted.** This is a configuration for one A3 decode (A3's sixth look), set in that decode's processes only. `FINAL_CONFIG.md`, the live app's defaults, B2, the zero-shot model and every shipped file are unchanged.

## The lock side (the display decode: the lock and the dot read it; the committed decision does not)

| setting | shipped | A3-clean | how it was chosen here |
|---|---|---|---|
| display spread (sd_scale) | 4.5 | **3.0** | S1: argmax of rotation-weighted display lock over {2.5, ..., 6.0}; best 52.50 at 3.0 (shipped 4.5: 51.88) |
| display entry | soft | **soft** | S2: soft minus free +0.42 [-1.46, +2.08]; soft ships if the interval contains zero or lies above it |
| display entry window | 1.0 m | **1.0 m** | S3: window minus none +20.00 [+16.04, +24.17]; the window ships only if the interval lies entirely above zero |

The machine line a3_replay.py reads (after checking this file's hash):

A3_CLEAN_LOCK_SIDE = {"sd_scale": 3.0, "display_entry": "soft", "display_entry_window_m": 1.0}

**Everything else in the display decode is as shipped:** the cap of 0.80 m per window, the A2 term alone as its start term, relgateU, abstain, the A2 weight 0.25 and the frozen A1+A2 pace.

**The committed decision** is the shipped decode, untouched. On all 96 decodes (32 arms x 3 rotations), every committed line equals the reference `D05.relgateU+abstain+a2w0.25`.

## The evidence (development evaluation, all data seen)

- **The cells:** `f05r_0102_to_B1`, `f05r_01B1_to_02`, `f05r_02B1_to_01` (registered in memory, `reg.py`), built beside `d4c_fuse_*`; the readers came from `d4c_fuse_*`'s byte copies of the d1sp twins' files, since the twins' trees were removed in the 6 Oct cleanup.
- **The plumbing gate before the swap:** each new cell, with the old heads, reproduces `d4c_fuse_<rotation>/d3/DT0.relgateU+abstain+a2w0.25` exactly (committed line, display lock, scorer lock): B1 120/120, A2 120/120, A1 120/120.
- **The swap:** the four slots replaced by the stride ablation's ALL05 seed set 0 networks (fh1s slot seed 3, g1s1 seed 1, g1s2 seed 2, g100 seed 0), byte-checked, inferred on the GPU; half unchanged.
- **The new reference D05** (shipped display settings, DT0 settings, new heads), committed / display lock: B1 69.17 / 44.17 (old heads 56.67 / 39.17); A2 95.00 / 72.50 (old heads 94.17 / 72.50); A1 74.17 / 46.67 (old heads 75.00 / 51.67).
- **The plumbing gate of PREREG section 7:** the shipped arm reproduces D05 exactly on all three rotations.
- **No input naming session 03** was opened by any decode, beyond A3's ground-truth sidecars, which `paths.load_paths` opens for the line geometry; the geometry was checked to be session 01's alone on every decode. Nothing was written outside this folder (audit hook).

| rotation-weighted | chosen | shipped |
|---|---|---|
| display lock | 52.50 | 51.88 |
| committed line | 76.88 | 76.88 |
| display lock, chosen minus shipped (paired, walks resampled within rotations) | +0.62 [-0.62, +1.88] | |

| rotation | chosen lock | shipped lock | lock edges E_col1 / E_col5 / E_row1 / E_row5, chosen | the same, shipped |
|---|---|---|---|---|
| A1+A2 -> B1, weight 2 | 43.33 | 44.17 | 66.7 / 66.7 / 0.0 / 50.0 | 66.7 / 66.7 / 0.0 / 50.0 |
| A1+B1 -> A2 | 73.33 | 72.50 | 83.3 / 50.0 / 100.0 / 50.0 | 66.7 / 50.0 / 100.0 / 50.0 |
| A2+B1 -> A1 | 50.00 | 46.67 | 0.0 / 66.7 / 83.3 / 0.0 | 0.0 / 50.0 / 83.3 / 0.0 |

**The figures:** `lock/SELECTION.json`; the decodes are under `lock/decodes/<rotation>/<arm>/`.
