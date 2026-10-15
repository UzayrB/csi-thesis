# Identification: per-point link weighting for the Wi-Fi speed (2026-10-10)

**For Mastermind's review. Nothing goes to the Editor. Exploratory development, all data seen. Nothing adopted.**

**Brief:** Uzayr's overnight prompt (10 Oct, about 00:15; hard stop 07:00). **Rules before results:**
`runs/identify/linkweight/PREREG_LW.md`, committed on its own before anything trained (9d56cb6e, 09 Oct 23:53:44), with
one dated note before the full cache (c30d829c, 23:55). **Code:** `pipeline/identify/ilw_cache.py`, `ilw_gate.py`,
`ilw_bank.py`, `ilw_score.py`, `ilw_eval.py`; driver `runs/identify/linkweight/run_lw.sh`. **Records:**
`runs/identify/linkweight/` (`cache/`, `cache_verify.json`, `gate.json`, `gate_table.md`, `plumb/`, `bank_T4.0_lw/`,
`models/`, `scores/`, `eval_lw.json`, `eval_lw_tables.md`, `logs/`, `QUEUE_LW.md`, `checkin.log`, `heartbeat.log`).

## 1. Verdict

1. **Speed:** one deployable candidate passed the pre-registered gate, V1 with P_nom (the shipped link, each frame
   corrected by F at a nominal 1.2 m/s position): tracking-walk r against the stopwatch 0.155 to 0.216, Delta r +0.060
   [+0.013, +0.116], median error 0.314 to 0.143 m/s. **But no oracle candidate passes, and the same estimator at the
   true positions is worse than shipped (Delta r -0.060 [-0.108, -0.009]), so the gain does not come from reading
   position better.**
2. **Identification:** the forwarded speed changes nothing separable in any of 23 cells (new minus shipped between -1.67
   and +1.67 points, every interval across or touching zero); the leave-one-session-out tracking walks go from 30.67 to
   31.33 % (+0.67 [-0.50, +2.17]); no cell is beyond speed. The expected null holds.
3. **Nothing is adopted.** A better speed by the stopwatch again did not mean better identification.

## 2. The gate

Pearson r against `press_speed_m_s`; Delta r against V0 with a paired cluster bootstrap over the 30 tracking recordings
(session x participant, 10,000 resamples, seed 0). A deployable candidate passes only if Delta r >= +0.05 with its lower
bound above 0, its median |error| is within 0.02 m/s of V0's, and its identification-walk Delta r >= -0.02. Coverage is
1.000 everywhere (no walk without a usable frame).

| estimator | position | tracking r | Delta r [95 %] | median abs error (m/s) | coverage | identification r | Delta r (identification) | passes |
|---|---|---|---|---|---|---|---|---|
| V0 | shipped | 0.155 |  | 0.314 | 1.000 | 0.846 |  |  |
| V1 | P_or | 0.096 | -0.060 [-0.108, -0.009] | 0.142 | 1.000 | 0.860 | +0.013 | no |
| V1 | P_nom | 0.216 | +0.060 [+0.013, +0.116] | 0.143 | 1.000 | 0.855 | +0.009 | yes |
| V1 | P_it | 0.027 | -0.129 [-0.175, -0.081] | 0.109 | 1.000 | 0.852 | +0.006 | no |
| V2 | P_or | 0.134 | -0.022 [-0.093, +0.047] | 0.133 | 1.000 | 0.860 | +0.013 | no |
| V2 | P_nom | 0.218 | +0.062 [-0.013, +0.137] | 0.132 | 1.000 | 0.855 | +0.009 | no |
| V2 | P_it | 0.094 | -0.061 [-0.118, -0.006] | 0.113 | 1.000 | 0.852 | +0.006 | no |
| V3 | P_or | 0.090 | -0.065 [-0.175, +0.045] | 0.125 | 1.000 | 0.859 | +0.013 | no |
| V3 | P_nom | 0.238 | +0.083 [-0.021, +0.189] | 0.122 | 1.000 | 0.856 | +0.010 | no |
| V3 | P_it | 0.162 | +0.006 [-0.093, +0.114] | 0.094 | 1.000 | 0.848 | +0.002 | no |

**Decision (mechanical):** V1|P_nom is the only passing deployable candidate and is forwarded. No P_or candidate passes:
**perfect position does not help.** The prompt's reading of that case, that no deployable version can then help, did not
hold literally: a nominal-position version passed. Since the true-position version of the same estimator is worse than
shipped, the pass cannot be credited to geometry.

**Breakdowns (secondary, never gating):**

| set | walks | V0 r | V1 P_nom r | V1 P_or r | V0 median abs error | V1 P_nom | V1 P_or |
|---|---|---|---|---|---|---|---|
| tracking, family A | 120 | 0.236 | 0.249 | 0.128 | 0.404 | 0.225 | 0.215 |
| tracking, family B | 120 | 0.167 | 0.178 | 0.074 | 0.361 | 0.164 | 0.174 |
| tracking, family C/D | 240 | 0.210 | 0.190 | 0.156 | 0.193 | 0.122 | 0.113 |
| tracking, family E_col | 60 | 0.396 | 0.716 | 0.349 | 0.542 | 0.092 | 0.132 |
| tracking, family E_row | 60 | 0.177 | 0.461 | 0.155 | 0.383 | 0.131 | 0.124 |
| tracking, A1 | 120 | 0.164 | 0.311 | 0.225 | 0.195 | 0.120 | 0.096 |
| tracking, A2 | 120 | 0.219 | 0.330 | 0.125 | 0.259 | 0.120 | 0.133 |
| tracking, A3 | 120 | 0.231 | 0.243 | 0.099 | 0.221 | 0.113 | 0.137 |
| tracking, B1 | 120 | 0.424 | 0.397 | 0.310 | 0.512 | 0.219 | 0.204 |
| tracking, B2 | 120 | 0.144 | 0.358 | 0.251 | 0.499 | 0.204 | 0.190 |
| identification, natural | 180 | 0.684 | 0.699 | 0.706 | 0.074 | 0.070 | 0.070 |
| identification, slow | 120 | 0.466 | 0.482 | 0.480 | 0.067 | 0.063 | 0.065 |
| identification, fast | 119 | 0.774 | 0.773 | 0.776 | 0.170 | 0.167 | 0.162 |

The prompt expected most room on the C, D and E_col tracking walks. E_col improves strongly (r 0.396 to 0.716, error
0.542 to 0.092 m/s) and so does E_row (0.177 to 0.461), but C/D does not (0.210 to 0.190). On the identification walks,
where per-point selection never leaves RX2, every estimator is within 0.02 of V0 (r 0.85 to 0.86).

**A post hoc check, exploratory, not in the pre-registration** (run after the gate, before writing this): rescaling V0
by one constant per path (the median of V1|P_nom / V0 on that path) leaves r at 0.157 (V0 0.156), so the pass is not a
per-path recalibration. The gain is within paths: the mean within-path r against the stopwatch is 0.232 for V0, 0.345 for
V1|P_nom and 0.166 for V1|P_or. Within a path V1|P_nom tracks V0 closely (median within-path Pearson 0.848; the ratio
V1|P_nom / V0 varies by a median 7.8 % within a path). One reading, untested: at nominal positions every walker on a path
gets the same F profile in time, so V1|P_nom acts as a fixed time-weighting of the frames, while true positions tie the
weighting to the walker's own speed and, with Doppler that follows geometry only weakly (section 3), add noise.

## 3. Does the Doppler follow geometry, and the SNR

Within-walk Spearman of the contour c_k against F_L(p_k) at the true positions (P_or), median over walks (at least 5
frames, F not constant), beside the record (whose exact definition this run does not reproduce):

| room, walks | RX1 | RX2 | RX3 | the record |
|---|---|---|---|---|
| Room A tracking | 0.051 (288) | 0.188 (360) | 0.190 (360) | -0.05 (Room A) |
| Room B tracking | 0.030 (192) | 0.350 (240) | 0.215 (240) | |
| Room B identification | | 0.458 (419) | 0.075 (419) | 0.744 (RX2), 0.276 (RX3) |

The direction matches the record (RX2 follows geometry in Room B, RX3 barely; Room A weakly), with smaller values. RX1
has F = 0 on the identification walks and is undefined there.

Torso-band SNR (PREREG_LW section 5: 10 log10 of the median 10 to 35 Hz power over the median 60 to 70 Hz power on the
walking span), median over walks: Room A tracking RX1 17.1, RX2 18.2, RX3 15.8 dB; Room B tracking 14.0, 15.3, 13.5 dB;
Room B identification 14.0, 15.7, 12.7 dB. RX2 has the highest SNR in every group; Room B is about 3 dB below Room A.

## 4. Identification (the forwarded speed, V1|P_nom)

**Plumbing first (both passed):** (a) `loso_A3_v4`'s five feature components retrained on a bank built by this run's code
with the shipped speed reproduce the shipped predictions exactly on A3's 120 walks (5 of 5 components); (b) the offline
scorer (`engine.Session` from bank rows in the replay's order, classify then add, pools per layout, on mps) reproduces
`loso_A3_v4` on A3 and `xr_AB_v4` on A3 and B2: 539 of 539 decisions, maximum log-probability difference 0.0. (On CPU
the same scorer differs by 4.3e-6, so all scoring ran on mps, as the replays.) **Anchor:** the shipped figures recomputed
equal `eval_xroom_v4.json` and its `loso_speed_controls` exactly in 23 of 23 cells (pooled engine 30.67, S0 30.17;
A3 by `xr_AB_v4` 30.00).

Each `_lw` model is its `_v4` parent with only the five feature components retrained on `bank_T4.0_lw` (its own rows,
cfg and seeds; `loso_B1_lw` on alpha 0.2's span, as its parent); the CNN files are copied unchanged. CAL-causal as
shipped. Intervals: `ixr_eval`'s (participant bootstrap, 10,000 resamples, seed 0; six clusters per cell). S0 is trained
on the shipped figure's rows. Labels by `ixr_eval`'s rules.

| model, cell | walks | new | shipped | new minus shipped | S0 | new minus S0 | S_wifi shipped / new | label |
|---|---|---|---|---|---|---|---|---|
| `xr_AB_lw` A3 tracking | 120 | 31.67 [21.67, 40.83] | 30.00 [20.00, 40.00] | +1.67 [+0.00, +5.00] not separable | 42.50 [23.33, 64.17] | -10.83 [-29.17, +9.17] not separable | 13.33 / 25.83 | above chance, not beyond speed |
| `xr_AB_lw` B2 tracking | 120 | 22.50 [10.00, 36.67] | 22.50 [10.00, 36.67] | +0.00 [+0.00, +0.00] not separable | 23.33 [10.00, 38.33] | -0.83 [-24.17, +16.67] not separable | 18.33 / 22.50 | not above chance, not beyond speed |
| `xr_AB_lw` B2 natural | 60 | 26.67 [6.67, 48.33] | 25.00 [3.33, 48.33] | +1.67 [+0.00, +5.00] not separable | 25.00 [5.00, 53.33] | +1.67 [-33.33, +28.33] not separable | 18.33 / 26.67 | not above chance, not beyond speed |
| `xr_AB_lw` B2 slow | 60 | 30.00 [6.67, 58.33] | 30.00 [6.67, 58.33] | +0.00 [+0.00, +0.00] not separable | 16.67 [0.00, 50.00] | +13.33 [-1.67, +30.00] not separable | 16.67 / 16.67 | not above chance, not beyond speed |
| `xr_AB_lw` B2 fast | 59 | 35.59 [18.97, 51.67] | 35.59 [18.97, 51.67] | +0.00 [+0.00, +0.00] not separable | 20.34 [0.00, 54.24] | +15.25 [-22.03, +44.07] not separable | 20.34 / 33.90 | above chance, not beyond speed |
| `xr_ABtrk_lw` A3 tracking | 120 | 25.00 [20.00, 29.17] | 25.00 [20.00, 29.17] | +0.00 [+0.00, +0.00] not separable | 39.17 [19.17, 62.50] | -14.17 [-35.02, +4.17] not separable | 18.33 / 18.33 | above chance, not beyond speed |
| `xr_ABtrk_lw` B2 tracking | 120 | 30.83 [21.67, 42.50] | 30.83 [21.67, 44.17] | +0.00 [-2.50, +2.50] not separable | 20.83 [10.00, 30.83] | +10.00 [-5.00, +25.00] not separable | 20.83 / 20.00 | above chance, not beyond speed |
| `xr_ABtrk_lw` B2 natural | 60 | 23.33 [8.33, 40.00] | 23.33 [8.33, 40.00] | +0.00 [+0.00, +0.00] not separable | 25.00 [6.67, 51.67] | -1.67 [-36.67, +26.67] not separable | 16.67 / 16.67 | not above chance, not beyond speed |
| `xr_ABtrk_lw` B2 slow | 60 | 26.67 [6.67, 46.67] | 26.67 [6.67, 46.67] | +0.00 [+0.00, +0.00] not separable | 16.67 [0.00, 50.00] | +10.00 [-13.33, +33.33] not separable | 16.67 / 16.67 | not above chance, not beyond speed |
| `xr_ABtrk_lw` B2 fast | 59 | 28.81 [8.77, 49.15] | 28.81 [8.77, 49.15] | +0.00 [+0.00, +0.00] not separable | 23.73 [1.69, 57.63] | +5.08 [-18.64, +30.00] not separable | 15.25 / 25.42 | not above chance, not beyond speed |
| `xr_A_lw` A3 tracking | 120 | 21.67 [13.33, 32.50] | 23.33 [14.17, 33.33] | -1.67 [-3.33, +0.00] not separable | 38.33 [19.17, 63.33] | -16.67 [-31.67, -4.17] separable cost | 19.17 / 22.50 | not above chance, below speed |
| `xr_A_lw` B2 tracking | 120 | 22.50 [15.00, 30.00] | 23.33 [15.00, 32.50] | -0.83 [-2.50, +0.00] not separable | 20.83 [7.50, 36.67] | +1.67 [-14.17, +17.50] not separable | 17.50 / 20.83 | not above chance, not beyond speed |
| `xr_A_lw` B2 natural | 60 | 23.33 [10.00, 36.67] | 23.33 [10.00, 36.67] | +0.00 [+0.00, +0.00] not separable | 23.33 [3.33, 55.00] | +0.00 [-40.00, +31.67] not separable | 16.67 / 21.67 | not above chance, not beyond speed |
| `xr_A_lw` B2 slow | 60 | 18.33 [8.33, 28.33] | 18.33 [8.33, 28.33] | +0.00 [+0.00, +0.00] not separable | 16.67 [0.00, 50.00] | +1.67 [-30.00, +23.33] not separable | 16.67 / 16.67 | not above chance, not beyond speed |
| `xr_A_lw` B2 fast | 59 | 33.90 [15.52, 53.33] | 33.90 [15.52, 53.33] | +0.00 [+0.00, +0.00] not separable | 20.34 [1.67, 53.33] | +13.56 [-13.33, +40.00] not separable | 20.34 / 28.81 | not above chance, not beyond speed |

| model, cell | walks | new | shipped | new minus shipped | S0 | new minus S0 | S_wifi shipped / new | label |
|---|---|---|---|---|---|---|---|---|
| `loso_*_lw` A1 (tracking walks) | 120 | 30.83 [15.83, 45.00] | 30.83 [18.33, 43.33] | +0.00 [-3.33, +4.17] not separable | 13.33 [4.17, 25.00] | +17.50 [-5.00, +38.33] not separable | 13.33 / 16.67 | not above chance, not beyond speed |
| `loso_*_lw` A2 (tracking walks) | 120 | 35.83 [24.17, 46.67] | 35.83 [24.17, 46.67] | +0.00 [-2.50, +2.50] not separable | 24.17 [12.50, 37.50] | +11.67 [-3.33, +25.00] not separable | 16.67 / 21.67 | above chance, not beyond speed |
| `loso_*_lw` A3 (tracking walks) | 120 | 32.50 [22.50, 42.50] | 30.83 [21.67, 40.00] | +1.67 [+0.00, +3.33] not separable | 48.33 [25.00, 70.00] | -15.83 [-40.00, +7.50] not separable | 11.67 / 25.00 | above chance, not beyond speed |
| `loso_*_lw` B1 (tracking walks) | 120 | 25.00 [15.00, 35.00] | 24.17 [15.00, 33.33] | +0.83 [+0.00, +2.50] not separable | 41.67 [21.67, 65.00] | -16.67 [-43.33, +8.33] not separable | 19.17 / 17.50 | not above chance, not beyond speed |
| `loso_*_lw` B2 (tracking walks) | 120 | 32.50 [20.00, 47.50] | 31.67 [20.00, 46.67] | +0.83 [-1.67, +3.33] not separable | 23.33 [10.83, 38.33] | +9.17 [-14.17, +27.50] not separable | 18.33 / 22.50 | above chance, not beyond speed |
| `loso_*_lw` room A (tracking walks) | 360 | 33.06 [23.61, 40.00] | 32.50 [23.06, 39.72] | +0.56 [-1.11, +2.50] not separable | 28.61 [16.11, 41.11] | +4.44 [-15.56, +21.94] not separable | 13.89 / 21.11 | above chance, not beyond speed |
| `loso_*_lw` room B (tracking walks) | 240 | 28.75 [20.83, 38.75] | 27.92 [19.58, 38.75] | +0.83 [+0.00, +1.67] not separable | 32.50 [18.33, 44.17] | -3.75 [-20.83, +14.17] not separable | 18.75 / 20.00 | above chance, not beyond speed |
| `loso_*_lw` pooled (tracking walks) | 600 | 31.33 [22.50, 39.17] | 30.67 [21.67, 39.17] | +0.67 [-0.50, +2.17] not separable | 30.17 [17.33, 41.67] | +1.17 [-16.33, +17.00] not separable | 15.83 / 20.67 | above chance, not beyond speed |

No difference between new and shipped is separable in any cell. The only cell below speed is `xr_A_lw` on A3 (new minus
S0 -16.67 [-31.67, -4.17]), as its parent was (-15.00). S_wifi on the new speed is at or above S_wifi on the shipped speed
in 21 of 23 cells (pooled 20.67 against 15.83), consistent with the better stopwatch correlation, without moving the engine.

## 5. What was not done, and why

- V2, V3 and P_it were not taken to identification: the rule forwards exactly one candidate.
- `xr_B1_v4` was not rescored: the prompt lists `xr_AB`, `xr_ABtrk` and `xr_A` only.
- The replay route (`ilw_engine.py`) was not needed: the offline scorer reproduced the replays exactly.
- CAL-none, per-participant tables and confusions were not computed: not in LW7.
- No reruns, seeds or setting changes. Nothing adopted; no shipped file, default or report text changed.

**Incidents, all disclosed:**
- The bank's `f_torso` field is engine v3's stale 3.0 s value (`iv4_build.merge` never updated it; equal to
  `bank_T3.0_v3`'s on all 1,019 rows). The smoke caught it; f_torso is checked through V0 against `wifi_speed` instead
  (dated note c30d829c, before the full cache). Every other check held on every pass.
- **My MACHINE_STATE helper had a path bug** (`ms_lw.py`, copied from `ms_xr.py`, resolved the repository one directory
  too high), so every MACHINE_STATE write failed silently during the run: the file never showed this run between 23:59
  and 00:23. The machine was QUIET with an empty queue at 23:51 and at launch. The lines were written late at 00:24,
  marked as late, and the helper is fixed.
- Memory: the B2 scores and plumbing check (b) read "12G" in `top` (whole gigabytes above 10 GB, so 12 to 13 GB); the
  lowest free memory of the run was 32 % (during `xr_AB_lw`'s B2 score), above the 30 % floor; no "13G", no MPS or
  Metal error.

## 6. Looks this run added

Every scored cell counts as one identification look, all on 2026-10-10:

| session | looks | model and cell |
|---|---|---|
| A3 | 4 | `xr_AB_lw`, `xr_ABtrk_lw`, `xr_A_lw` on A3 tracking; `loso_A3_lw` on A3's tracking walks |
| B2 | 13 | `xr_AB_lw`, `xr_ABtrk_lw`, `xr_A_lw` on B2 tracking, natural, slow and fast (12); `loso_B2_lw` on B2's tracking walks |
| A1, A2, B1 | 1 each | `loso_<s>_lw` on its session's tracking walks |

The gate looks at speed only (no identity labels) on all 1,019 walks.

## 7. Files, commits and timings

| time (SAST) | step |
|---|---|
| 09 Oct 23:51 | set-up; MACHINE_STATE QUIET, queue empty; check-ins every 15 min, heartbeat every 60 s |
| 23:53:44 | PREREG_LW committed alone (9d56cb6e); 23:55 dated note (c30d829c) |
| 23:59:11 to 00:03:00 | the cache, 1,019 passes (CPU, 1 process), then its verification (PASSED) |
| 00:03:21 | the gate: V1|P_nom forwarded |
| 00:06:51 to 00:09:18 | plumbing (a) and (b), both PASSED |
| 00:09:18 to 00:10:20 | `bank_T4.0_lw` and the eight `_lw` models (feature components 2 to 8 s each) |
| 00:10:20 to 00:23:14 | eleven offline scores on mps, one at a time |
| 00:23:24 | `ilw_eval` (anchor 23 of 23); QUIET; caffeinate released |

Commits: 9d56cb6e (pre-registration), c30d829c (note, cache code), 97233b6e (gate, driver, heartbeat, helper), bb0dde93
(phase 2 code), and the closing commit with the results, models, logs and this report. The driver held one caffeinate
for the whole run; the heartbeat recorded the driver alive every minute and its clean end.

## 8. Corrections after the Mastermind's review (10 Oct 2026, 00:29 SAST)

Sections 1 to 7 stand as committed (0ceef9e2), with these two corrections.

1. **The prompt's time.** The header's "Uzayr's overnight prompt (10 Oct, about 00:15 ...)" was copied from the prompt's
   own text without checking it. The prompt reached this session on **09 Oct, at or just before 23:51:04 SAST** (the
   first clock reading of the turn that received it), before the set-up (23:51) and the pre-registration's commit
   (23:53:44). The same correction is a dated note in `PREREG_LW.md`.
2. **The gate's second condition, worded exactly.** Section 2 says a candidate's median |error| must be "within 0.02 m/s
   of V0's". The pre-registered condition (PREREG_LW section 5) is that it is **no more than 0.02 m/s worse than V0's**,
   and `ilw_gate.py` tests exactly that (median |error| <= V0's + 0.02; the JSON key `mae_within_0.02_of_V0` is only a
   name). V1|P_nom's 0.143 m/s against V0's 0.314 passes under that condition and would fail a two-sided "within 0.02".
   (Section 2's "every estimator is within 0.02 of V0 (r 0.85 to 0.86)" is about r on the identification walks, not the
   error.)
