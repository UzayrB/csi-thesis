# A3_CLEAN_CONFIG: the display settings chosen without A3. Lock side, 8 October 2026, 20:12 SAST (clock read)

**Status.** This version holds the LOCK SIDE only. It was selected exactly as `PREREG.md` (SHA-256 bf0284de..., committed in
9f8972ae before any selection run) fixes, with `PREREG_ADDENDUM_1.md` (compute only). The dot side (settings 4 to 8 of
`PHASE0.md`) is pending: it waits for Uzayr's answers and its own pre-registration, and will be a new version of this file
with a new hash.

**Not adopted.** This is a configuration for one A3 decode, loaded as a separate configuration. `FINAL_CONFIG.md`, the live
app's defaults and every shipped file are unchanged.

## The lock side (the display decode: the lock and the dot read it; the committed decision does not)

| setting | shipped | A3-clean | how it was chosen here |
|---|---|---|---|
| display spread (sd_scale) | 4.5 | **2.5** | S1: argmax of rotation-weighted display lock over {2.5, ..., 6.0}; 2.5 to 4.0 tie at 51.25, ties to the smallest |
| display entry | soft | **soft** | S2: soft minus free -0.42 [-2.08, +1.04]; the interval contains zero, so soft ships (non-inferiority) |
| display entry window | 1.0 m | **1.0 m** | S3: window minus none +21.25 [+17.29, +25.42]; the interval lies above zero, so the window ships |

**Everything else in the display decode is as shipped:**
- the cap of 0.80 m per window (cleared 30 Sep);
- the A2 term alone as its start term;
- relgateU, abstain, the A2 weight 0.25 and the frozen A1+A2 pace.

**The committed decision** is the shipped decode, untouched: its entry is soft with the 1.0 m window. On all 96 decodes
(32 arms x 3 rotations), every committed line equals the record `DT0.relgateU+abstain+a2w0.25`.

## The evidence

- **The plumbing gate:** the shipped arm reproduces DT0 exactly (committed line, display lock and scorer lock, 120/120) on
  B1 (17:16), A2 (17:15) and A1 (19:32).
- **The 30 Sep records:** all 24 soft, 1.0 m spread decodes equal the 30 Sep records `SD.relgateU+abstain+a2w0.25+sd<x>`,
  walk for walk.
- **No input naming session 03** was opened by any decode, beyond A3's six ground-truth sidecars, which `paths.load_paths`
  opens for the line geometry. The geometry was checked to be session 01's alone on every decode.
- **Nothing was written outside this folder** (audit hook).
- **The figures:** `lock/SELECTION.json`; the decodes are under `lock/decodes/<rotation>/<arm>/`.
