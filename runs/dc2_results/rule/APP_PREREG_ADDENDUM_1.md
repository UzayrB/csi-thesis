# APP_PREREG addendum 1: four display fixes before any figure. 30 September 2026, 09:57 SAST

**Status.** Written and hashed before any headline replay of A3 or B2, and before any A3 or B2 display
figure exists. Its SHA-256 is in `APP_PREREG_ADDENDUM_1.md.sha256`. `APP_PREREG.md` (82a6b47a...) is
unchanged and still governs; this adds to it.

## What had run on A3 or B2 when these were found

**One gate run:** G2 (semi mode, whole-file clock) on fin_B2 had completed 3 of 6 recordings when it
was stopped at 09:39.
- **What it outputs:** only committed-line and lock EQUALITY counts against the corrected offline
  answers, which are already known (93.33 / 72.50). All three recordings were 20 of 20.
- **What it does not output:** no dot, frame or display figure.

**Nothing was chosen on it.** Each fix below was found by reading the display code and by development
replays on the A1+A2 -> B1 rotation. Every gate is rerun on the fixed app (section 4 of the
pre-registration: "after every change to the app").

## The fixes (all in the display: none can change a committed line)

| # | what was wrong | the fix | where |
|---|---|---|---|
| 1 | Frames were drawn only when the NEXT window arrived, up to one stride (0.5 s) after their own time: a live screen would show the dot in 0.5 s steps, breaking V1 and V3 | once a window is decoded, every frame before the next window's end is drawn (it cannot read that window); the screen shows each from its time. Frames that can read a window wait for it to be cut | `FinalTrackingSession._draw_ahead`, `_park_drawn_ahead` |
| 2 | Rule 2a's anchor frames (press + 2.0 s to the first decoded position, 0.625 s) were drawn only in a batch that also held a decoded frame, so they were lost on every walk; the dot stayed at the room centre 0.6 s after the green marker appeared. The offline slide towards the first decoded position also reads radio ending after those frames | the LIVE form of rule 2a: the dot is held at the locked line's entry until the first decoded position | `display.compose_walk` (`sett["anchor"] = "hold"`, the app only) |
| 3 | The lock was read from the LAST composition of a walk; a later press's re-cut could in principle rename it | THE lock is the line first drawn; every later change is logged and counted (rule 1) | `FinalTrackingSession.first_lock`, `lock_changes`; the gates read `first_lock` |
| 4 | The frame at exactly press + 2.0 s coincides with the lock window's end up to rounding, and was sometimes drawn just before that window was added (lost on 1 walk in 20) | a frame within 1e-6 s of a window's end waits for it; push's own pre-add draw is skipped (fix 1 has already drawn those frames from the same windows) | `FRAME_EPS_S`, the push wrapper |

**Not a fix, but new:** the rig takes every SPACE as a start press in the semi mode (it raised on the
second SPACE before).

## What they change in the reported figures

**The dot error:** only through the frames near a start press drawn from the pre-press windows. The
anchor span is excluded from the dot error (rule 2b), so fix 2 changes no dot figure.

**The lock:** fix 3 makes the reported lock the one drawn at press + 2.0 s. On the development test
(one B1 recording, 20 walks) there were 0 changes after the first.

**The committed line:** unchanged by construction; the decoder does not read the display.

## New outputs of the scorer (reported beside the figures, never replacing them)

`app_score.rule_checks` reads the app's log alone:
- **The counts:** park, together, anchor, lock changes and walks with more than one switch. Each must
  be 0.
- **The draw lag:** how long after its own time each frame was ready. It replaces the count "frames
  computed after their time", which was always about all frames, because a frame was drawn when the
  window after it arrived.

**The development test** (B1 rotation, one recording, whole-file clock): all counts 0; draw lag p99
0.114 s and maximum 0.133 s (the window's cutting delay).

## A development model set

`rotB1` (`app_replay.DEV_SETS`) replays the A1+A2 -> B1 rotation through the app, for behaviour checks
only. It refuses a test session.

**Its display head is the final one, trained on B1,** so its dots are not a held-out measurement. They
are never a figure.
