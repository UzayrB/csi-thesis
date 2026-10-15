# The propagation investigation: each link's response against the walker's position. 1 October 2026

**The instruction:** item 2 of `reports/BRIEF_PRESENCE_PROPAGATION_2026-10-01.md` (the brief's GA4: "the physical
signal propagation characteristics"). This is a measurement on existing recordings: **nothing is adopted, and no
model, setting or figure changes.**

**The scripts and numbers** are in `runs/dc2_results/propagation/`:
- `propagation.py`;
- the per-block table `blocks.csv` (81,592 blocks) and `doppler_passes.csv` (1,800 pass-links);
- every figure below, in `PROPAGATION.json`;
- the figures `falloff_rssi_dip_db.png`, `falloff_shape_change.png`, `crossings_rssi_dip_db.png`,
  `crossings_shape_change.png`, `along_link.png` and `doppler_vs_F.png`.

## 1. The method, fixed before any response was looked at

**The recordings:** the 30 evaluated walk recordings (A1, A2, A3, B1 and B2, six each; calibration recordings left
out), read only.

**The geometry:** the same in both rooms, read from every sidecar.
- **The nodes:** TX (2.5, -0.5), RX1 (2.5, 5.5), RX2 (-0.5, 2.5) at its home position (the identification walks
  moved it; these tracking walks did not), RX3 (5.5, 2.5).
- **The links:** link 1 is 6.00 m long, and line A runs along it. Links 2 and 3 are 4.24 m.

**The blocks:** 0.1 s of packets (about 15, and about 0.13 m of walking), inside every unflagged labelled pass.
The walker's position is the pass's anchor presses interpolated linearly.

**Two responses per block and link:**
- **The RSSI dip:** the app's own idle RSSI mean for that link (`stats.rssi_idle_mean`) minus the block's mean, in
  dB, positive when weaker.
- **The CSI-shape change:** the RMS difference between the block's subcarrier shape and the empty-room baseline's
  shape, in `baseline_shape`'s own space.

**For each block:** u, the position along the link (0 at TX, 1 at RX), and d, the perpendicular distance from the
link's line.

**The half-width:** the binned median response against d.
- **The peak:** d < 0.10 m.
- **The floor:** 1.5 to 2.5 m.
- **The half-width:** where the curve first falls half way from the peak to the floor.
- **Per link and room:** mid-link (0.3 <= u <= 0.7) and the two end segments.
- **The intervals:** a bootstrap over passes, 1,000 draws, seed 0.

**The first Fresnel radius:** r1(u) = sqrt(lambda L u (1 - u)), with lambda = 0.1218 m (channel 11, 2.462 GHz).
- **Link 1:** 0.427 m mid-link, 0.319 m at u = 1/6.
- **Links 2 and 3:** 0.359 m mid-link, 0.339 m at u = 1/3.

**The RX1 check:** per pass and link, the Doppler-band power (5 to 40 Hz, Welch, cleaned amplitude) over the empty
room's, against the line's mean projected bistatic factor F = |d(path length)/ds| / 2.

## 2. Results with the pre-fixed method

| room | link | segment (u) | first Fresnel radius at the segment centre | RSSI dip half-width [95 %] (peak / floor dB) | CSI-shape half-width [95 %] (peak / floor) |
|---|---|---|---|---|---|
| A | TX-RX1 | TX end (0.05 to 0.3) | 0.32 m | **not defined**: the on-line response is not above the far floor (-0.10 / 0.40) | 0.40 m [0.09, 0.62] (0.23 / 0.14) |
| A | TX-RX1 | mid (0.3 to 0.7) | 0.43 m | **not defined**: the on-line response is not above the far floor (-1.18 / -0.18) | 0.47 m [0.07, 0.69] (0.21 / 0.12) |
| A | TX-RX1 | RX end (0.7 to 0.95) | 0.32 m | **not defined**: the on-line response is not above the far floor (-0.76 / -0.05) | 0.65 m [0.06, 1.07] (0.24 / 0.12) |
| A | TX-RX2 | TX end (0.05 to 0.3) | 0.27 m | too few blocks | too few blocks |
| A | TX-RX2 | mid (0.3 to 0.7) | 0.36 m | **not defined**: the on-line response is not above the far floor (0.07 / 0.16) | 0.62 m [0.20, 0.87] (0.20 / 0.15) |
| A | TX-RX2 | RX end (0.7 to 0.95) | 0.27 m | too few blocks | too few blocks |
| A | TX-RX3 | TX end (0.05 to 0.3) | 0.27 m | too few blocks | too few blocks |
| A | TX-RX3 | mid (0.3 to 0.7) | 0.36 m | 0.55 m [0.12, 0.80] (1.00 / -0.23) | 0.40 m [0.22, 0.68] (0.18 / 0.10) |
| A | TX-RX3 | RX end (0.7 to 0.95) | 0.27 m | too few blocks | too few blocks |
| B | TX-RX1 | TX end (0.05 to 0.3) | 0.32 m | 0.14 m [0.06, 0.94] (1.06 / -0.01) | 0.13 m [0.06, 0.59] (0.10 / 0.04) |
| B | TX-RX1 | mid (0.3 to 0.7) | 0.43 m | 0.06 m [0.05, 0.39] (0.67 / 0.07) | 0.07 m [0.07, 0.37] (0.12 / 0.04) |
| B | TX-RX1 | RX end (0.7 to 0.95) | 0.32 m | 0.05 m [0.04, 0.14] (1.01 / 0.02) | 0.05 m [0.05, 0.11] (0.12 / 0.05) |
| B | TX-RX2 | TX end (0.05 to 0.3) | 0.27 m | too few blocks | too few blocks |
| B | TX-RX2 | mid (0.3 to 0.7) | 0.36 m | **not defined**: the on-line response is not above the far floor (-1.67 / -0.43) | 0.87 m [0.22, 1.12] (0.17 / 0.09) |
| B | TX-RX2 | RX end (0.7 to 0.95) | 0.27 m | too few blocks | too few blocks |
| B | TX-RX3 | TX end (0.05 to 0.3) | 0.27 m | too few blocks | too few blocks |
| B | TX-RX3 | mid (0.3 to 0.7) | 0.36 m | 0.42 m [0.11, 0.63] (1.88 / -0.06) | 0.60 m [0.14, 1.35] (0.08 / 0.05) |
| B | TX-RX3 | RX end (0.7 to 0.95) | 0.27 m | too few blocks | too few blocks |

**Where this method breaks down:**
- **The RSSI dip:** in four cells the on-line response is not above the far floor (Room A link 1; link 2 in both
  rooms), so no half-width exists.
- **The idle reference in Room A:** the app's idle RSSI mean comes from the windows before the first press, which in
  Room A are not stillness (`reports/PRESENCE_2026-10-01.md`: their band energy is near walking's). So Room A's
  "dips" are measured against a moving reference. Mid-link on link 1 they come out negative.
- **Link 1's on-line bin** is dominated by line A, where the walker walks ALONG the link for a whole pass. That is a
  different situation from crossing it, so in Room B the pooled curve drops almost at once (0.05 to 0.14 m) after
  line A.

## 3. The crossings alone (POST HOC)

**Why this analysis exists:** it was chosen after seeing section 2, and is labelled POST HOC for that reason. Only
the passes whose line crosses the link are used.

**How it works:**
- **The reference:** each block is taken against its own pass's far level (the median over 1.0 <= d <= 2.5 m in that
  pass), which removes the idle reference and the offsets between passes.
- **The half-width:** the same rule as before, with a floor of 0.
- **The crossing points** come from the taped lines' own anchors:
  - link 1 is crossed by B, C and D at u = 0.5 and by E_row1 and E_row5 at 1/6 and 5/6;
  - link 2 by E_row1 (1/3), C (1/2) and E_col1 (2/3);
  - link 3 by E_row1 (1/3), D (1/2) and E_col5 (2/3).

| room | link | crossing line | crossing u | first Fresnel radius there | RSSI: peak above the pass's far level; half-width [95 %] | CSI shape: peak above far; half-width [95 %] | passes |
|---|---|---|---|---|---|---|---|
| A | TX-RX1 | B | 0.50 | 0.43 m | -0.17 dB; not defined (no rise on the line) | +0.04; 0.96 m [0.51, 1.16] | 72 |
| A | TX-RX1 | C | 0.50 | 0.43 m | -0.50 dB; not defined (no rise on the line) | +0.06; 0.79 m [0.46, 0.99] | 72 |
| A | TX-RX1 | D | 0.50 | 0.43 m | -1.15 dB; not defined (no rise on the line) | +0.02; 0.62 m [0.51, 0.97] | 72 |
| A | TX-RX1 | E | 0.17 | 0.32 m | +0.62 dB; 0.15 m [0.10, 0.59] | +0.09; 0.52 m [0.12, 0.63] | 18 |
| A | TX-RX1 | E | 0.83 | 0.32 m | -0.33 dB; not defined (no rise on the line) | +0.05; 0.89 m [0.17, 1.16] | 18 |
| A | TX-RX2 | C | 0.50 | 0.36 m | -0.04 dB; not defined (no rise on the line) | +0.03; 0.86 m [0.11, 1.20] | 72 |
| A | TX-RX2 | E | 0.33 | 0.34 m | +0.53 dB; 0.15 m [0.10, 1.42] | +0.08; 0.44 m [0.08, 1.04] | 18 |
| A | TX-RX2 | E | 0.67 | 0.34 m | +0.18 dB; 0.08 m [0.03, 0.79] | +0.05; 0.65 m [0.10, 0.95] | 18 |
| A | TX-RX3 | D | 0.50 | 0.36 m | +0.21 dB; 0.91 m [0.07, 1.02] | +0.04; 0.69 m [0.12, 0.83] | 72 |
| A | TX-RX3 | E | 0.33 | 0.34 m | +2.84 dB; 0.31 m [0.11, 0.53] | +0.17; 0.35 m [0.20, 0.54] | 18 |
| A | TX-RX3 | E | 0.67 | 0.34 m | +3.13 dB; 0.37 m [0.21, 0.43] | +0.03; 0.17 m [0.15, 0.51] | 18 |
| B | TX-RX1 | B | 0.50 | 0.43 m | +0.33 dB; 0.41 m [0.05, 0.63] | +0.01; 0.72 m [0.42, 1.11] | 48 |
| B | TX-RX1 | C | 0.50 | 0.43 m | +0.55 dB; 0.11 m [0.10, 0.73] | +0.05; 0.55 m [0.39, 0.65] | 48 |
| B | TX-RX1 | D | 0.50 | 0.43 m | +0.02 dB; 0.05 m [0.04, 0.51] | +0.03; 0.49 m [0.42, 0.69] | 48 |
| B | TX-RX1 | E | 0.17 | 0.32 m | +0.73 dB; 0.08 m [0.05, 0.60] | +0.02; 0.77 m [0.10, 1.45] | 12 |
| B | TX-RX1 | E | 0.83 | 0.32 m | +0.06 dB; 0.14 m [0.04, 0.61] | -0.01; not defined (no rise on the line) | 12 |
| B | TX-RX2 | C | 0.50 | 0.36 m | -1.27 dB; not defined (no rise on the line) | +0.04; 0.91 m [0.25, 1.05] | 48 |
| B | TX-RX2 | E | 0.33 | 0.34 m | -1.03 dB; not defined (no rise on the line) | +0.04; 0.59 m [0.11, 0.90] | 12 |
| B | TX-RX2 | E | 0.67 | 0.34 m | -1.67 dB; not defined (no rise on the line) | +0.07; 0.51 m [0.12, 0.84] | 12 |
| B | TX-RX3 | D | 0.50 | 0.36 m | +0.77 dB; 0.69 m [0.11, 0.75] | +0.01; 0.69 m [0.12, 1.27] | 48 |
| B | TX-RX3 | E | 0.33 | 0.34 m | +2.27 dB; 0.21 m [0.12, 0.41] | +0.05; 0.56 m [0.27, 0.77] | 12 |
| B | TX-RX3 | E | 0.67 | 0.34 m | +2.28 dB; 0.17 m [0.11, 0.53] | +0.04; 0.15 m [0.06, 0.48] | 12 |

## 4. Along the link, and the RX1 bistatic finding

**Along line A** (the walker within 0.15 m of link 1's line; `along_link.png`):
- **Room B:** link 1's RSSI dip is 0.5 to 1 dB mid-link and 1.5 to 2 dB near the TX and RX ends, where the first
  Fresnel zone is narrowest. There the body blocks more of it.
- **Room A:** the same profile shows only near the TX, against its moving idle reference.

**Each link on line A** (median over line A's blocks):

| room | link | walker's median distance from the link | RSSI dip, median (dB) | CSI-shape change, median |
|---|---|---|---|---|
| A | TX-RX1 | 0.00 m | -1.02 | 0.230 |
| A | TX-RX2 | 2.08 m | +0.31 | 0.165 |
| A | TX-RX3 | 2.08 m | -0.30 | 0.109 |
| B | TX-RX1 | 0.00 m | +0.98 | 0.122 |
| B | TX-RX2 | 2.10 m | -0.28 | 0.102 |
| B | TX-RX3 | 2.10 m | -0.12 | 0.055 |

**The Doppler band against geometry** (`doppler_vs_F.png`):

| room | link and line | mean F | Doppler-band power / empty room (median over passes) | passes |
|---|---|---|---|---|
| A | TX-RX1, line A | 0.000 | 5.02 | 72 |
| A | TX-RX1, line B | 0.362 | 10.37 | 72 |
| A | TX-RX1, line C | 0.366 | 8.05 | 72 |
| A | TX-RX1, line D | 0.366 | 11.43 | 72 |
| A | TX-RX1, line E | 0.299 | 9.59 | 72 |
| A | TX-RX2, line A | 0.500 | 9.37 | 72 |
| A | TX-RX2, line B | 0.500 | 9.51 | 72 |
| A | TX-RX2, line C | 0.615 | 11.64 | 72 |
| A | TX-RX2, line D | 0.366 | 7.39 | 72 |
| A | TX-RX2, line E | 0.434 | 9.33 | 72 |
| A | TX-RX3, line A | 0.500 | 5.67 | 72 |
| A | TX-RX3, line B | 0.500 | 7.92 | 72 |
| A | TX-RX3, line C | 0.366 | 5.92 | 72 |
| A | TX-RX3, line D | 0.615 | 8.39 | 72 |
| A | TX-RX3, line E | 0.434 | 7.39 | 72 |
| B | TX-RX1, line A | 0.000 | 2.95 | 48 |
| B | TX-RX1, line B | 0.362 | 3.75 | 48 |
| B | TX-RX1, line C | 0.366 | 3.28 | 48 |
| B | TX-RX1, line D | 0.366 | 3.63 | 48 |
| B | TX-RX1, line E | 0.299 | 2.87 | 48 |
| B | TX-RX2, line A | 0.500 | 5.19 | 48 |
| B | TX-RX2, line B | 0.500 | 3.28 | 48 |
| B | TX-RX2, line C | 0.615 | 6.24 | 48 |
| B | TX-RX2, line D | 0.366 | 3.23 | 48 |
| B | TX-RX2, line E | 0.434 | 4.51 | 48 |
| B | TX-RX3, line A | 0.500 | 3.23 | 48 |
| B | TX-RX3, line B | 0.500 | 3.37 | 48 |
| B | TX-RX3, line C | 0.366 | 2.82 | 48 |
| B | TX-RX3, line D | 0.615 | 3.95 | 48 |
| B | TX-RX3, line E | 0.434 | 3.64 | 48 |

**How strongly F orders the Doppler band,** across the 15 link-and-line cells: Spearman rho 0.16 (p 0.57)
in Room A and 0.59 (p 0.021) in Room B.

## 5. What it shows

**Where the body clearly blocks a link, the response falls off on the scale of the first Fresnel zone.**
- **The clearest case:** link 3 at its E_row1 and E_col5 crossings (u = 1/3 and 2/3; first Fresnel radius 0.34 m
  at both), with RSSI dips of +2.8 to +3.1 dB in Room A and +2.3 dB in Room B.
- **The half-widths there** (E_row1, then E_col5): 0.31 [0.11, 0.53] and 0.37 [0.21, 0.43] m in Room A;
  0.21 [0.13, 0.41] and 0.17 [0.11, 0.53] m in Room B.
- **Mid-link on link 3,** pooled: 0.55 m (Room A) and 0.42 m (Room B), against 0.36 m.

**What limits the precision:**
- **The intervals are wide:** each crossing has 12 to 18 passes.
- **The position labels:** linear between presses 1 m apart, about +-0.1 m.
- **The blocks:** 0.13 m each.
- **The body:** about 0.4 m wide.
- **So:** half-widths below about 0.15 m are at the resolution floor, and "the same order as r1" is the claim the data
  supports, not an equality.

**Not every link behaves like this.**
- **Link 2 in Room B: RSSI rises** by 1.0 to 1.7 dB at all three crossings (the negative peaks in section 3). A
  link dominated by multipath can gain when the body removes a destructively interfering path. There is no fall-off
  to measure.
- **Link 2 in Room A:** its crossing responses are small (-0.04 to +0.53 dB).
- **Link 1 mid-link:** its crossing responses are small. Room B's dip is 0.0 to +0.55 dB; Room A's RSSI rises
  slightly (the dip is -0.2 to -1.2 dB).
- **Link 1 near the TX** (E_row1, u = 1/6): +0.6 to +0.7 dB and narrow (0.08 to 0.15 m).

**The CSI-shape change reaches further than the Fresnel zone.**
- **The half-widths:** mostly 0.4 to 1.0 m at the crossings, and 0.4 to 0.9 m mid-link in the pooled analysis.
  The exceptions are link 3's E_col5 crossings, at 0.15 and 0.17 m.
- **The cause:** the walker changes the subcarrier shape from up to about a metre off the line, by scattering, not
  only by blocking the line of sight.
- **Why it matters:** this is why the tracker reads position from the whole shape, and not from line-of-sight
  shadowing alone.

**The RX1 bistatic-factor finding holds, in the sense it was stated.**
- **What the finding says:** on line A, TX-RX1's F is 0 for the whole line, so the walker changes that path's length
  not at all.
- **What the data shows:** RX1's Doppler band on line A is the lowest of its five line families in Room A (5.0 x the
  empty room, against 8.1 to 11.4 x) and within the lowest pair in Room B (2.95 x, against 2.87 to 3.75 x).
- **It is not zero.** It is still 3 to 5 x the empty room, from the body's own shadowing changes and its limbs.
- **RX1 is not blind to line A,** though. The walker is inside RX1's Fresnel zone the whole way, so RX1 shows the
  largest CSI-shape change of the three links on line A in both rooms, and Room B's largest RSSI dip.
- **The finding is about Doppler, not presence:** F = 0 removes the path-length (Doppler) cue, not the shadowing one.
- **Across links and lines,** F orders the Doppler band only weakly (Spearman 0.16 and 0.59).

**For the thesis (GA4):**
- **The Fresnel scale:** on this rig, at 2.46 GHz, a walker's effect on a link's power is concentrated within about
  the first Fresnel zone of the crossing point (tenths of a metre), where the link is blocked cleanly.
- **The shape spreads further:** about a metre.
- **One link's power rises instead,** a multipath effect.
- **A receiver on the walker's line** loses the Doppler cue but keeps the shadowing one.
- **Nothing here changes the model or the app.**
