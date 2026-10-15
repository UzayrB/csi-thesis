# A3_CLEAN_CONFIG_FULL: every display setting chosen without A3. Written 2026-10-09 15:17:11 (clock), before A3 is touched

**Status.** The full A3-clean configuration:
- **the lock side:** Overall's on the shipped all-0.5 s heads (`runs/a3_clean_0p5_2026-10-09/A3_CLEAN_CONFIG_0p5.md`, 2c701274, SHA-256
  d942cb16ec221dcd...);
- **the dot side:** selected by this run's five stages under `PREREG_DOT.md` (cdab65c4), addendum 1 (7aa5b1ff) and
  addendum 2 (cec9d891).

**What comes next:** it is used for ONE A3 decode, A3's SEVENTH look (`a3_full.py`), set in that decode's processes only.
**Nothing shipped changes:** `FINAL_CONFIG.md`, the live app's defaults, the model sets, B2 and zero-shot.

| setting | shipped | A3-clean |
|---|---|---|
| display head | DISP_END (shipped) | **centre_labelled (the pooled heads)** |
| display prior (flatten) | 0.5 | **0.5** |
| head offset (s) | 0.375 | **0.75** |
| dot phase SHIFT_W (strides) | 0.5 | **1.0** |
| switch arm | C | **A** |
| display spread (sd_scale) | 4.5 | **3.0** |
| display entry | soft | **soft** |
| display entry window (m) | 1.0 | **1.0** |

**Also as shipped:**
- the cap of 0.80 m per window;
- latency 2.0 s, lock at press + 2.0 s, 10 frames per second;
- K1g's look-ahead and glide;
- the pool's five 0.5 s networks (`f05_A3`).

**The stages** (development evaluation, all data seen; `dot/stage<n>/SELECTION.json`):
- stage 1: centre_labelled;
- stage 2: f0.50;
- stage 3: o0.75;
- stage 4: s1;
- stage 5: A.

**The machine-read form:** `A3_CLEAN_CONFIG_FULL.json` (SHA-256 6e225f6a315f10a47e5a8e496af4363ccffd33bc903f670d4acf1c3bbfa55f41).
