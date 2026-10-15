# PLAN_RA: identification, lift Room A, keep the gains, pick the model to ship

Written 10 Oct 2026, 15:26:36 SAST by the Third overall chat from Uzayr's prompt (received at or before 10 Oct 2026
15:25:40 SAST, the first `date` read on it; "This prompt is my go"). Committed before any score of this run. Exploratory development, all data seen; **selection uses this morning's
combine scorecard (A3 and B2)**. Nothing is adopted by this run; the pick is the configuration Uzayr will confirm and
ship as engine v5 (his decision).

## 0. What this run is, plainly (the Mastermind's condition, added 10 Oct 2026, 15:26:52 SAST, before any score)

- **Selection is on A3 and B2** (the combine scorecard).
- **Every scored configuration is a counted look** at A3 and B2 (each base and each of the 1,500 mixes).
- **Nothing in this run is confirmatory**, and **nothing from it is reportable as a held-out or generalisation result**;
  the pick's figures are optimistic by an amount this run cannot estimate. Confirming the pick needs data it was never
  chosen on.

## 1. The scorecard (`ilc_outer` and `ilb_core`, unchanged)

Z = the mean of the three zero-shot cells (A1+A2 [xr_A] to B2 path walks and natural walks; B1 [xr_B1] to A3 path walks);
D = the mean of the ten cross-day cells; the guard: the other-four-sessions models' (loso) natural, slow and fast walks
each no more than 5 points below v4. Intervals: paired participant bootstrap, 10,000 draws, seed 0.
**Core Room A cells:** A1+A2 [xr_A] to A3 path walks and A1+A2+B1 path walks [xr_ABtrk] to A3 path walks.

## 2. Bases (feature components retrained by `ilb_core`'s code; the CNNs reused: the shipped replays and best/a4cache)

- W = A1+A3+A4+A5+M3 (the build's winner); B = A1+A3+A4+M3; F = F7+A3+A4+A5+M3 (C3: F7's offsets in place of A1's).
- Each with and without P1 (C4): six bases. Each base is rescored once with every component's log-probabilities saved;
  W and B with all weights 1 must reproduce this morning's files (`runs/identify/best/outer/`) exactly, or the run is
  BLOCKED.

## 3. Mixes (no retraining: re-weighting the saved log-probabilities)

Each window's ensemble = normalise(w x the sum of the feature components (six with M3) + the sum of the three CNN
components); A4's three windows averaged and normalised as before. The CNN weight stays 1. w = w_id on identification
walks; on path walks:
- **C1, walk-type mix:** one w_path for every path walk.
- **C2, room-aware mix:** w_A when the test session is in Room A and the model trained on a Room A session, w_B likewise
  for Room B, and w_unseen when the model never trained in the test session's room (only A1+A2 [xr_A] on B2 and B1
  [xr_B1] on A3, so the zero-shot path cells always use w_unseen).
- Grid: w_path, w_A, w_B, w_unseen in {0, 0.25, 0.5, 0.75, 1}; w_id in {0.5, 1}. C1 is C2 with w_A = w_B = w_unseen.
  250 mixes per base, 1,500 in all; each one is a configuration scored on A3 and B2 and is counted.

## 4. The selection rule (Uzayr's, fixed now)

- **Qualifies:** the guard holds, both core Room A cells >= 25.00, Z >= 32.00 and D >= 31.00.
- **The pick:** the qualifier with the highest (Z + D) / 2. Every qualifier within 0.25 of that highest score is tied;
  among the tied, the one with the higher mean of the two core Room A cells. Remaining exact ties: the higher
  (Z + D) / 2, then the base order (W, B, F; without P1 before with P1), then the mix with the weights closest to 1
  (smallest sum of |w - 1|).
- **If nothing qualifies:** the trade-off set is reported and the run stops for Uzayr's choice. The trade-off set is
  every configuration, among those holding the guard, that no other configuration beats on all three of the core Room A
  mean, Z and D.

## 5. Extra cells and the report

A1+A2+B1 path walks [xr_ABtrk] on B2's natural, slow and fast walks, for v4, the winner and the pick, from the existing
log-probabilities (its replay and A4 cache cover all 299 B2 walks). The report, `reports/identification/2026-10-10_room-a.md`,
follows the prompt's sections 1 to 6, with v4 and the pick side by side, S0 beside every cell, and paired intervals for the
pick minus v4 and the pick minus S0.

## Notes

(Dated notes go below this line.)

- **10 Oct 2026, 15:33:11 SAST: the SPLIT CHECK (report-only, added by the Mastermind; selection unchanged).** Written while the six bases
  were still being rescored, before the mix step ran (no mix scored). It estimates how much of the pick's gain is
  selection, from the same cached log-probabilities:
  - **The halves.** The A3 half is every scorecard cell restricted to A3's walks: Z_A3 = B1 [xr_B1] to A3 path walks; D_A3 =
    the mean of the other four sessions' model on A3's path walks [loso_A3], and A1+A2+B1 path + B1 identification walks
    [xr_AB], A1+A2 [xr_A] and A1+A2+B1 path walks [xr_ABtrk] to A3's path walks; the core Room A cells are both A3 cells.
    The B2 half is every cell restricted to B2's walks: Z_B2 = the mean of A1+A2 [xr_A] to B2 path and natural walks; D_B2
    = the mean of loso_B2 natural and path, xr_AB to B2 path and natural, xr_B1 to B2 path and natural, and xr_ABtrk to B2
    path; the guard on B2 = loso_B2's natural, slow and fast walks each no more than 5 points below v4's.
  - **Selection on one half.** PLAN_RA's rule with only that half's cells: on the A3 half, both core cells >= 25.00, Z_A3
    >= 32.00 and D_A3 >= 31.00 (no guard: A3 has no identification walks); on the B2 half, the B2 guard, Z_B2 >= 32.00 and
    D_B2 >= 31.00 (no core cells). The highest (Z + D) / 2 of the half, ties within 0.25 by the core mean (A3 half) or by
    the remaining tie order (B2 half). If nothing qualifies on a half, its highest (Z + D) / 2 among all mixes (B2 half:
    among those holding the B2 guard) is used, and labelled so.
  - **Reported:** the A3-chosen mix's figures on the B2 half and the B2-chosen mix's on the A3 half, beside PLAN_RA's pick
    and this morning's winner on each half, with paired participant intervals (10,000 draws, seed 0) against v4 and the
    winner; the total configuration count beside every chosen figure. The split check changes nothing in the pick.
