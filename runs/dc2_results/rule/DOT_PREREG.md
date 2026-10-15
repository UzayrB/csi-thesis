# DOT_PREREG: the dot leaves the entry with the walker. Written 30 September 2026, before any candidate run

**Status.** Written and hashed before any candidate is replayed on any session. Its SHA-256 is in
`DOT_PREREG.md.sha256`, and it is never edited afterwards.

**What it implements:** item 3 of `reports/BRIEF_LIVE_APP_2_2026-09-30.md`.

## 1. The diagnosis (from the code, and from the teaching pack's B2 pass 2)

**Why the first decoded positions sit at the entry.**
- **How each step is drawn:** each drawn step after the lock is the ENDPOINT of its own Viterbi within the
  locked line (`render_display.locked_chain_path`). It runs over the windows up to that step only:
  evidence lag 0, the 2-window draw offset less the 2 windows a window needs to end.
- **Where it starts:** from the soft entry, restricted to the line's first 1.0 m.
- **Why that holds the dot back:** the first steps' windows are centred at and just after the press and half
  hold the standing before it. So the endpoints stay at the entry, and the tight chain lets them advance by
  at most 0.8 m per 0.5 s.
- **Why it then races:** consecutive endpoints come from DIFFERENT Viterbis. When the radio re-routes the
  best path, the next endpoint lands far ahead, hence the 3.5 m/s catch-up.

**The slack.**
- **Where a frame sits:** a frame at video time x draws step i with x between P + 2.375 + 0.5 i and
  P + 2.875 + 0.5 i, where P is the press.
- **What it reads:** step i reads radio ending at P + 1.0 + 0.5 i.
- **So:** every frame reads radio that ended 1.375 to 1.875 s before it is shown. The old renders' 1.4 s is
  the lower end.

## 2. The candidates (display only)

| candidate | the drawn path's look-ahead within the locked line | the anchor span (press + 2.0 s to the first decoded frame) |
|---|---|---|
| K0 | 0 windows (the display of commit 63987d1) | held at the entry |
| K1 | 1 window | held |
| K2 | 2 windows | held |
| K1g | 1 window | glides from the entry to the first decoded frame's position |
| K2g | 2 windows | glides |

**The look-ahead** wraps the pinned `locked_chain_path` inside the display's own composition only
(`display.LiveDisplay._compose`). The lock (the free path) and every decision are untouched.

**Causality.**
- **K2 (hold):** every frame reads radio that has ended by its time, with a margin of at least 0.375 s.
- **The glide:** its first frame is the entry itself. It reads step 0, whose radio ends at press + 1.0 s
  plus the look-ahead: at or before the anchor frames for up to 2 windows.
- **Measured:** the margin is recorded per frame (`margin_s`).

**Not a candidate:** starting the walk's display decode from windows that end between the press and
press + 0.625 s. That changes the window the display decode, and so the lock, starts from, and no lock
may change.

## 3. Where it is chosen: the development rotations only

**The replays:** the app on the three rotations' test sessions: A1+A2 -> B1 (`rotB1`), A1+B1 -> A2
(`rotA2`) and A2+B1 -> A1 (`rotA1`).
- **Coverage:** every evaluated recording, 18 in all.
- **The mode:** semi-constrained, with the causal clock.
- **The candidate:** set by `app_replay --display <K>`.

**A3 and B2 are not replayed until the choice is written.** One number was seen before this rule: K0's
B2 figure. The metric was tested on the committed K0 render logs: 0.336 m, ahead share 0.321. It is the
old display's, and no candidate has been run on B2.

## 4. The metric (`app_score.dot_from_press`)

**Which walks:** those whose lock is correct. The lock is identical across candidates by construction;
a candidate whose locks or committed lines differ from K0's on any walk is disqualified.

**Which frames:** every drawn frame from the press on: scene time at or after the press, the anchor span
included, the park excluded, and the truth defined.

**The two measures:**
- **the error:** the dot against the truth at frame time - 2.0 s;
- **ahead:** the dot's projection on the true line lies further from the line's start than the truth's.

**Per rotation:** E_r is the median error and A_r the ahead share. Weighted (as `pd_rule` weights):
E = (2 E_B1 + E_A2 + E_A1) / 4, and A likewise.

## 5. The rule

1. **Disqualify** a candidate if any lock or committed line differs from K0's, or if its measured margin is
   below 0 on any walk.
2. **Eligible:** A_K <= A_K0. It must not increase the share of frames where the dot is ahead.
3. **Among the eligible, the lowest E.** Differences within 0.005 m are ties, which go to the first in the
   order K0, K1, K2, K1g, K2g, the smaller change first. K0 is always eligible.
4. **The choice** is written to `runs/dc2_results/display/DOT_CHOICE.json` and becomes
   `final_model.DISPLAY_CANDIDATE`.

## 6. Then (item 3d)

**What is rerun:**
- G2 (semi, the whole-file clock) on A3, B2 and zero-shot B2: it must stay 120 / 120;
- the A3, B2 and zero-shot B2 replays, once, semi and fully constrained;
- the 12 renders;
- the scores.

**What is reported, side by side:** the old and new dot error, both from the press, and the old
anchor-excluded figure.
