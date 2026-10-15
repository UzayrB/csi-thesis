# PLAN note 1: the unconstrained start detector is pinned at spread 4.5. Written 10 October 2026, 08:52 SAST (clock read), before any decode

**Applies to:** `PLAN.md` (5f13034c, SHA-256 4ac0c68c...). The plan itself is unchanged.

**The finding (engineering, 0de57fdd):** the unconstrained (no-press) mode builds its start detector from the display's
configuration (`display.cfg_disp`) after the session is built. Under the clean profile, that configuration has spread
3.0, so the detector would have decoded at 3.0. Its figures were made at 4.5.

**The ruling (the Mastermind, 10 Oct, 08:50):** pin the start detector to spread 4.5 under both profiles.
- **The reason:** Uzayr's decision adopts the clean DISPLAY. The start detector makes a decision (when a walk starts), so
  it must not change silently with the display profile.
- **What it keeps valid:** the existing no-press figures (`unconstrained_m4_disp-K1g`), with no new looks.

**The change (`pipeline/live/unconstrained.py`):**
- the constant `DETECTOR_SD_SCALE = 4.5`;
- `StartDetector.__init__` replaces the spread of whatever configuration it is given with it, so every caller (the
  session and `choose_m`) decodes at 4.5;
- `StartDetector.sd_scale` records it.

Under pre_clean the display's spread is already 4.5, so nothing changes there.

**The test (`tests/test_live_clean_display.py`):** each profile's display configuration is built as LiveDisplay and
FinalTrackingSession build it (4.5 for pre_clean, 3.0 for clean). The detector's Space and transition matrix must both
see 4.5 under both profiles.

**What the pin keeps valid, checked in the code (`UnconstrainedSession._maybe_start`):** a start is detected from the
detector and the committed decisions only, never from the display. Under the clean app, the detections and the committed
lines in no-press mode are therefore those of the existing replays. The figures that stay valid (correct and detected,
from the score files):

| model, session | correct and detected | file |
|---|---|---|
| final, B2 | 33.33 % | `runs/live/replay/final/unconstrained_m4_disp-K1g_causal/SCORE_UNCONSTRAINED_B2.json` |
| final, A3 | 35.00 % | `runs/live/replay/final/unconstrained_m4_disp-K1g_causal/SCORE_UNCONSTRAINED_03.json` |
| zero-shot, B2 | 20.83 % | `runs/live/replay/zeroshot/unconstrained_m4_disp-K1g_causal/SCORE_UNCONSTRAINED_B2.json` |

**What the pin does not cover:** the no-press LOCK figures (lock correct and detected: final A3 18.33 %, final B2
22.50 %, zero-shot B2 15.83 %). The lock is read from the display decode, which the clean profile runs at spread 3.0.
Those figures therefore describe the pre_clean display. They are not replayed under clean (no new looks), so they are
labelled "pre_clean display" wherever they are quoted.
