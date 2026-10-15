# Identification: longer windows and gait analysis (1 October 2026, night)

- **The brief:** `reports/identification/briefs/2026-10-01_window-gait.md` (verbatim, 9be68e6).
- **The rules, fixed before Parts A to D ran:** `runs/identify/engine/PLAN.md`, the note of 2026-10-01 20:15 (9be68e6).
- **Development evaluation, all data seen.** Parts A to C are screens; engine v3 is unchanged. Names throughout
  (tracking's codes differ; its "P5" is PA2).
- **The reference is engine v3,** from its replays: natural 32.22 %, slow 25.83 %, fast 23.53 %.
- **What every row scores:**
  - the natural (n 180), slow (n 120) and fast (n 119) identification walks of both walks folds: B2 replayed by the
    model trained on A1, A2, A3 and B1, and B1 by the model trained on A1, A2, A3 and B2;
  - causal calibration on same-layout pools (fix L);
  - each block paired against v3 on the same walks (Part C: against the same-seed baseline), with a participant
    bootstrap (10,000 resamples, seed 0);
  - chance is 16.67 %.
- **S_wifi** is an LDA on the row's own Wi-Fi speed, trained on the other Room B day's identification walks.

**The rule** (quoted in the PLAN note from the brief). PROMISING means all of:
1. the natural gain over v3 (or over the same-seed baseline in Part C) is at least +4.45 points;
2. it is positive on to B1 and on to B2;
3. neither the slow nor the fast paired change is below -4.45;
4. the engine minus S_wifi on natural walks does not shrink.

## 0. In short

- **Nothing is PROMISING, so identification closes at engine v3** (32.22 % [17.78, 48.33]), as the brief says.
  Part D did not run, and nothing is built into the engine.
- **The best deployable window is 4.0 s:** 37.78 % [23.33, 53.33], paired +5.56 [+1.67, +10.56].
  - Slow +3.33 and fast +6.72 hold.
  - It fails two points of the rule: to B2 falls 3.33, and its margin over speed alone shrinks to +6.11 (v3: +8.33).
  - **Most of what the longer window adds is a better speed estimate, not gait:** S_wifi alone rises from 23.89 %
    at 3 s to 31.67 % at 4 s.
- **The ceiling of whole-walk information (W-oracle,** the window from the press to the true end press) is 38.89 %
  [25.00, 53.89], paired +6.67 [-0.56, +15.00].
  - Even the whole walk, with its end known, closes at most 6.67 of the 7.78 points between v3 and 40 %.
- **The radio cannot see the end of a walk here.**
  - After the end press the walker keeps moving (turning, then walking back a median 4 s later), so RX2's
    torso-band energy stays at about 80 % of the walk's last second.
  - The end detector fires a median 1.4 to 1.6 s late, most windows run to its 6 s cap, and W-radio gains +2.22.
- **Gait parameters (Part B) add nothing beyond the 4 s window:** at most +0.56. With or without the raw speed column
  the result is the same.
- **Every network change (Part C) is worse than the same seed without it:**
  - pace-normalised maps -5.00 (WORSE);
  - velocity maps -3.89;
  - the cross-session contrastive loss -2.22 (weight 0.1) and -1.11 (weight 0.5).
- **The render, recorded once, on engine v3:** it should end at **20 of 60** (33.33 %) on B2's natural blocks
  (section 7).

## 1. Part 0: housekeeping (done first)

- **`reports/identification/thesis-summary.md` section 14** (39a92ab):
  - engine v3's figures are the thesis figures;
  - why v2 fell to v3;
  - the DANN result;
  - the one-press cost (-7.78 [-17.78, +3.89]), against the frozen two-press reference built with the v1 step-rate
    resolver;
  - T unchanged on the strength of the T-sensitivity check.
- **One dated "superseded" line** at the top of the 1 October morning and afternoon identification handoffs (39a92ab),
  now under `reports/attempts/`. They were written before the reports were reorganised, so they cite the old file
  names; `reports/project/repository/2026-10-01_reports-moves.json` resolves them.
- **README.md's identification paragraph** now carries engine v3's figures (423a68d, at Monitor's request).
- **No render and no teaching pack yet**, as the brief says.

## 2. Part A: how much of the walk to see

**What follows each walk** (both Room B days; `runs/identify/window_gait/alpha.json`, "follow"):

| block | walk, median (s) | end press to next start press, median [10th, 90th] (s) | RX2 energy in the second after the end press, against the walk's first 2.5 s | against the walk's last second |
|---|---|---|---|---|
| natural | 4.09 | 4.09 [3.36, 5.99] | 0.58 | 0.80 |
| slow | 5.19 | 4.90 [3.65, 6.89] | 0.42 | 0.89 |
| fast | 3.30 | 3.75 [2.80, 4.52] | 0.45 | 0.81 |

- **The walker does not stand still after the end press.**
  - RX2's 10 to 35 Hz energy stays at 80 to 89 % of the walk's last second.
  - The empty room is 11 to 19 % of the walking level on these days.
  - The walker turns at the line, and the next pass (the return walk) starts a median 4 s later. This measure cannot
    separate the walker's movement from anyone else's in the room.
- **A window is never cut short by the next start press at 4 or 5 s.** At 6 s, 10 B1 windows were.

**The end detector (W-radio):**
- **The threshold, from the training sessions only:** for each fold, the alpha with the smallest median error on the
  other Room B day's identification walks.
  - To B2 (fitted on B1): alpha 0.5, median |error| 1.00 s.
  - To B1 (fitted on B2): alpha 0.2, 1.16 s.
  - The folds differ, so each fold's windows were built with its own.
- **Detected end against the true end press** (`wradio_end_error.json`; information):

| block | median error (s, detected minus true) | median absolute error (s) | 90th percentile of the absolute error (s) |
|---|---|---|---|
| natural | +1.42 | 1.61 | 2.29 |
| slow | +0.31 | 0.91 | 2.62 |
| fast | +1.42 | 1.42 | 2.96 |

- **Is it better than the two-press era's start-only end detector,** which lost 14.44 points [-26.67, -2.78]
  (`reports/identification/2026-09-29_identification-walks.md`)?
  - **It does not lose (+2.22), but only because it hardly detects anything.** Its windows end a median 5.9 to 6.0 s
    after the press, at or near the cap, and it decides at 6.5 s.
  - **Why:** the energy test assumes the walker stops, and here the walker turns and keeps moving. A radio end
    detector would need a different cue, for example the reversal of the Doppler sign as the walker turns; that was
    not tested.

**The arms** (`runs/identify/window_gait/rows/A.*.json`):

| window | natural [95 %] | paired | slow (paired) | fast (paired) | to B1 / to B2 (paired) | PA1 | PA2 (of 30) | decision (s) | past the end press: natural / slow / fast | S_wifi, natural | engine minus S_wifi, natural | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v3 (3.0 s) | 32.22 [17.78, 48.33] | | 25.83 | 23.53 | 31.67 / 33.33 | 58 | 1 | 3.03 | 0 / 0 / 25 % | 23.89 | +8.33 [-3.33, +21.11] | reference |
| 3.5 s | 31.67 [18.33, 47.78] | -0.56 [-5.56, +3.89] | 24.17 (-1.67) | 28.57 (+5.04) | 0.00 / -1.67 | 57 | 2 | 3.53 | 3 / 0 / 59 % | 35.56 | -3.89 [-33.33, +23.33] | FLAT |
| **4.0 s** | **37.78 [23.33, 53.33]** | **+5.56 [+1.67, +10.56]** | 29.17 (+3.33) | 30.25 (+6.72) | +10.00 / **-3.33** | 56 | 3 | 4.03 | 41 / 0 / 88 % | 31.67 | **+6.11** [-21.67, +31.11] | FLAT |
| 4.5 s | 35.56 [21.11, 53.89] | +3.33 [-3.33, +9.44] | 28.33 (+2.50) | 26.05 (+2.52) | +4.17 / +1.67 | 57 | 4 | 4.53 | 80 / 4 / 96 % | 33.89 | +1.67 [-30.00, +29.44] | FLAT |
| 5.0 s | 34.44 [18.33, 53.33] | +2.22 [-9.44, +12.22] | 32.50 (+6.67) | 24.37 (+0.84) | +1.67 / +3.33 | 55 | 5 | 5.03 | 92 / 31 / 100 % | 31.11 | +3.33 [-30.56, +37.78] | FLAT |
| 6.0 s | 34.44 [18.89, 50.00] | +2.22 [-7.22, +13.33] | 22.50 (-3.33) | 27.73 (+4.20) | +4.17 / -1.67 | 48 | 4 | 6.03 | 100 / 87 / 100 % | 31.11 | +3.33 [-20.56, +31.67] | FLAT |
| W-radio | 34.44 [19.44, 53.33] | +2.22 [-5.56, +8.89] | 24.17 (-1.67) | 27.73 (+4.20) | +2.50 / +1.67 | 54 | 4 | 6.51 | 80 / 68 / 80 % | 30.56 | +3.89 [-20.56, +29.44] | FLAT |
| W-oracle (information) | 38.89 [25.00, 53.89] | +6.67 [-0.56, +15.00] | 33.33 (+7.50) | 28.57 (+5.04) | +6.67 / +6.67 | 51 | 5 | 4.12 | 0 / 0 / 0 % | 31.67 | +7.22 [-16.68, +30.00] | ceiling |

- **The anchor:** this pipeline's 3.0 s arm reproduces engine v3 exactly. Features equal the v3 bank on 1,019 of
  1,019 windows, and decisions equal v3's replays on 659 of 659 (ensemble difference 2.8e-14).
- **The two fixes for windows longer than 3 s held:**
  - the direction stayed v3's ([t0, t0 + 3 s]);
  - the Wi-Fi speed used only the walking span.
- **Carried forward to Parts B and C: 4.0 s.** It is the deployable arm with the best natural score whose slow and
  fast changes both stay above -4.45. **That choice was made with the results in view.**

**The W-oracle ceiling, plainly:**
- Seeing the whole walk, with its true end and without the walk time as a feature, reaches 38.89 %.
- That is 6.67 points above v3, an interval that includes zero, and still 1.11 below 40 %.
- On these walks, whole-walk information cannot lift one press above 40 %. The deployable 4.0 s window already gets
  most of the way to that ceiling, and much of it through a better speed estimate.

## 3. Part B: gait parameters on the 4.0 s window

**Identity-blind information** (`runs/identify/window_gait/partB_info.json`):
- **The population speed-cadence line is flat** on the training rows: step rate = 1.85 + 0.02 v (to B2) and 1.93 -
  0.02 v (to B1). In this data the step rate hardly varies with speed, so speed-normalised cadence is nearly the step
  rate itself.
- **A1's precise speed** (RX2's centroid minus the training days' empty room) reaches Pearson **0.717** against press
  speed on the 180 natural walks at 4 s. At 3 s it gave 0.697, against the 0.70 gate.
- **A usable step rate** (a channel with a clear rhythm) exists on 88.9 % of natural walks at 4 s, against 92.8 % at
  3 s. The extra second is often after the walk, which dilutes the rhythm.

**The rows** (all on the 4.0 s window, paired against v3; the CNN components are the 4.0 s arm's):

| row | natural (paired) | slow (paired) | fast (paired) | to B1 / to B2 (paired) | PA1 | PA2 | engine minus S_wifi | verdict |
|---|---|---|---|---|---|---|---|---|
| 4.0 s, as carried (Part A) | 37.78 (+5.56 [+1.67, +10.56]) | 29.17 (+3.33) | 30.25 (+6.72) | +10.00 / -3.33 | 56 | 3 | +6.11 | FLAT |
| 4.0 s, no speed column | 37.78 (+5.56 [+0.56, +10.56]) | 28.33 (+2.50) | 31.09 (+7.56) | +9.17 / -1.67 | 56 | 3 | +6.11 | FLAT |
| B1 (walk ratio, step length, speed-normalised cadence), with speed | 38.33 (+6.11 [+2.22, +11.11]) | 29.17 (+3.33) | 30.25 (+6.72) | +10.83 / -3.33 | 56 | 4 | +6.67 | FLAT |
| B1, without speed | 37.78 (+5.56 [+1.11, +11.11]) | 28.33 (+2.50) | 31.09 (+7.56) | +10.00 / -3.33 | 56 | 4 | +6.11 | FLAT |
| B2 (the contour: mean, fluctuation at the step rate, steady speed, t90, start ratio), with speed | 37.78 (+5.56 [+0.56, +11.67]) | 29.17 (+3.33) | 29.41 (+5.88) | +10.00 / -3.33 | 54 | 4 | +6.11 | FLAT |
| B2, without speed | 37.78 (+5.56 [+0.56, +11.67]) | 29.17 (+3.33) | 27.73 (+4.20) | +10.00 / -3.33 | 54 | 4 | +6.11 | FLAT |
| B1 + B2, with speed | 37.22 (+5.00 [+0.56, +11.11]) | 29.17 (+3.33) | 27.73 (+4.20) | +9.17 / -3.33 | 55 | 3 | +5.56 | FLAT |
| B1 + B2, without speed | 38.33 (+6.11 [+1.11, +12.22]) | 29.17 (+3.33) | 28.57 (+5.04) | +10.83 / -3.33 | 55 | 4 | +6.67 | FLAT |

- **None moves the 4.0 s window by more than 0.56 points,** and every row keeps its fall on to B2.
- **The pace-normalised parameters carry no identity beyond the window's own features:** with or without the raw
  speed column, the result is the same.
- **B4 (RX1's attenuation profile, body shape) was not run.** It was optional and needed one more extraction pass;
  with Parts A and B flat, the time went to Part C.

## 4. Part C: the networks (seed 0, both folds, on the 4.0 s maps)

**The same-seed baseline** is the engine's trainer at seed 0 on the 4.0 s maps. Against v3 (information) it gives
38.89 % [24.44, 55.56], +6.67 [+0.00, +13.33], with slow +1.67 and fast +10.08. It is one seed, and inside the
4.45-point noise floor.

| variant (against the same-seed baseline) | natural (paired) | slow (paired) | fast (paired) | to B1 / to B2 | PA1 | PA2 | engine minus S_wifi | cnn / cnn_prior / per-link alone (named PA1) | verdict |
|---|---|---|---|---|---|---|---|---|---|
| baseline (seed 0) | 38.89 | 27.50 | 33.61 | 39.17 / 38.33 | 54 | 5 | +7.22 | 24.44 (47) / 25.00 (64) / 31.11 (70) | |
| C1, pace-normalised maps + the speed scalar | 33.89 (**-5.00** [-15.00, +5.00]) | 30.00 (+2.50) | 30.25 (-3.36) | -3.33 / -8.33 | 52 | 6 | +2.22 | 26.11 (52) / 22.78 (70) / 35.00 (68) | WORSE |
| C2, velocity maps (geometry only) | 35.00 (-3.89 [-11.67, +4.44]) | 27.50 (0.00) | 27.73 (-5.88) | -2.50 / -6.67 | 46 | 5 | +3.33 | 29.44 (40) / 25.00 (46) / 32.22 (64) | FLAT (fast below the guard) |
| C3, cross-session contrastive, 0.1 | 36.67 (-2.22 [-6.11, +1.11]) | 27.50 (0.00) | 25.21 (**-8.40** [-14.29, -2.52]) | -2.50 / -1.67 | 51 | 5 | +5.00 | 30.00 (47) / 30.00 (55) / 31.67 (56) | FLAT (fast below the guard) |
| C3, cross-session contrastive, 0.5 | 37.78 (-1.11 [-6.11, +4.44]) | 27.50 (0.00) | 30.25 (-3.36) | -2.50 / +1.67 | 51 | 8 | +6.11 | 30.56 (50) / 32.22 (55) / 30.56 (66) | FLAT |

- **C1 against C2** (pace normalised against not): C1 is 1.11 points lower than C2. Removing pace from the maps lost
  identity rather than revealing gait, so pace carries part of what the maps identify.
- **C3** asked the same person to look the same across sessions. It did not help, and at weight 0.1 it cost the fast
  walks 8.40 points.

## 5. Part D

Not run: nothing in Parts A to C is PROMISING, so there is nothing to combine or confirm on three seeds.

## 6. Which levers worked, which did not, and why

- **A longer fixed window helped a little, mostly through speed.**
  - **The gain:** 4.0 s gained 5.56 points with the slow and fast walks intact, and about half of it went to PA5
    (33.3 to 50.0 %).
  - **Why it mostly tracks speed:** the extra second also made the Wi-Fi speed better (S_wifi 23.89 to 31.67 %; A1's
    Pearson 0.697 to 0.717), and the engine's margin over speed shrank (+8.33 to +6.11).
  - **It also failed on B2** (-3.33), and windows of 4.5 s or more gave less, because they run past the walk into the
    turn (80 to 100 % of natural windows at 4.5 s or more).
- **A radio end detector did not work, and it is the walk protocol that defeats it.** The walker never stops at the
  end of a pass, so an energy test cannot find the end.
- **Whole-walk information is not enough.** Even the true end gives 38.89 %, short of 40 %.
- **Gait parameters did not add identity.**
  - **The walk ratio and normalised cadence:** at a 4 s window the step rate is resolved on 89 % of walks and is
    barely tied to speed in this data (the population line is flat). So these columns mostly repeat the step rate,
    which the 630 gait features already hold.
  - **The velocity contour's fluctuation and start-up columns:** they are measured on a single 4 s window, at a
    0.053 s frame rate, through a 0.21 s STFT window that smooths the within-step speed swing.
- **Pace-normalised and velocity maps lost identity** (-5.00 and -3.89). Removing pace and geometry from the maps took
  away part of what the networks were using, and what was left did not transfer across days any better.
- **Contrastive alignment across sessions did not help,** in line with DANN: making the same person's features
  similar across days does not create the identity signal that is missing across days.
- **Overall:** with one start press on these recordings, the cross-day identity signal sits near one-third. Every
  route to 40 % tried here either tracks pace or does not transfer from one day to the other.

## 7. The render (to record once, on engine v3)

- **Expected end count:** 20 of 60 (33.33 %) on B2's natural blocks. This is engine v3's to-B2 natural figure, and
  the live app's rig path matches the harness on 299 of 299 B2 decisions.
- **The command** (from the repository root; the app picks `loso_B2_v3` by itself):

```
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.identify_engine rig --source recorded --session B2 --render natural --speed 1 --device mps
```

- **Part E** (build, replay, verify, re-score, then the teaching pack) waits for your choice. With nothing adopted,
  the engine is v3, already built and verified (`reports/identification/2026-10-01_v3-dann.md`); only the teaching pack
  is left to build.

## 8. What went wrong

- **I ran the machine out of memory (about 22:10).** I launched Part C's five scoring jobs at once on the GPU.
  - **Why memory grew:** each job re-adapted four networks on a pool that grew by one walk per step. PyTorch's GPU
    memory cache keeps blocks of every batch size it meets, so each job grew without limit, and each also loaded
    every arm's bank.
  - **The warning I ignored:** two jobs crashed first ("Unable to reach MTLCompilerService"), and I restarted them
    rather than stopping. The laptop then ran out of memory, VS Code (whose child processes these were) showed over
    100 GB, and the session ended.
  - **The fix:**
    - one job at a time, under a watchdog (`runs/identify/window_gait/queue/run_guarded.sh`) that kills only its job
      if free memory falls below 30 % or the job passes 6 GB;
    - a cap on each job's GPU memory;
    - the GPU cache emptied after every step;
    - each pool window normalised once instead of at every step.
    After the fix each job ran in about a minute, at under 5 GB.
  - **Lost work:** the B1 halves and C3_0.5 were recomputed.
  - **Results:** no result is affected. The surviving B2 caches were checked against the fixed loop: identical
    (difference 0.0, 299 of 299).
- **The exit code again:** the crashed jobs' logs said "EXIT 0", because `$(date)` ran before `$?` was read (the
  project's own lesson). The guarded queue captures the return code first.
- **The first guarded launch stopped at once:** PyTorch refused a GPU memory cap without a matching low-water ratio.
  Nothing ran; the watchdog stopped the queue as designed.
- **Two time slips:** in messages to Tracking (not in any record), I gave times about a quarter of an hour off before
  reading the clock. They were corrected in a second message.

## 9. Files and commands

| what | where |
|---|---|
| code (new) | `pipeline/identify/iwg_bank.py` (the windows: detector pre-pass, alpha, every arm through the engine's own `extract_window`), `iwg_screen.py` (scoring against v3, S_wifi, Part B), `iwg_cnn.py` (Part C: velocity and ratio maps, the speed-scalar head, the contrastive loss, causal AdaBN on same-layout pools); `ils_feat.py` gained optional `pace`, `nopace` and `extra` keys (defaults unchanged) |
| outputs | `runs/identify/window_gait/`: `alpha.json` (the threshold and what follows each walk), `anchor_T3.0.json`, `wradio_end_error.json`, `partB_info.json`, `rows/` (one record per row, names only), `table.md`, `logs/`, `queue/run_guarded.sh`; the banks (`bank/`, 1.1 GB), CNN outputs and Part C networks stay local |

Commands (from the repository root, with `PYTHONPATH=.`; Part C's scoring one job at a time):
```
python3 -m pipeline.identify.iwg_bank pass1 --session B2         # per session
python3 -m pipeline.identify.iwg_bank alpha
python3 -m pipeline.identify.iwg_bank bank --session B2 --alpha 0.5
python3 -m pipeline.identify.iwg_screen cnn --arm T4.0 --device mps
python3 -m pipeline.identify.iwg_screen partA ; python3 -m pipeline.identify.iwg_screen partB --arm T4.0
python3 -m pipeline.identify.iwg_cnn train --arm T4.0 --fold B2 --variant C1 --device mps
runs/identify/window_gait/queue/run_guarded.sh base C1 C2 C3_0.1 C3_0.5
python3 -m pipeline.identify.iwg_cnn score --arm T4.0 --device cpu ; python3 -m pipeline.identify.iwg_screen table
```

**Times:** Part 0 and the PLAN note by 20:16, Part A by 21:20, Part B by 21:22, Part C's trainings by 21:40, the
memory failure about 22:10, Part C's scoring by 22:32.
