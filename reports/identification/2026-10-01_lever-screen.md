# Identification: the lever screen (2026-10-01, evening)

- **The brief:** `reports/BRIEF_ID_LEVER_SCREEN_2026-10-01.md` (verbatim, 2afb5be).
- **The rules, fixed before anything ran:** in `runs/identify/engine/PLAN.md`:
  - the note of 17:18 (2afb5be): the levers, the order, the anchors, the noise floor and the promise rule;
  - the note headed 17:38 (9f958ac), written at 17:33 (correction d21fa89): three additions, defined after the tiers
    ran and before any addition ran.
- **Development evaluation, all data seen.** This is a screen, so every number here is exploratory. **Engine v2 is
  unchanged.** Names are used throughout; tracking's codes differ (its "P5" is PA2).
- **What is scored:**
  - the 180 natural identification walks: `loso_B2_x` replays B2 (60 walks; trained on A1, A2, A3 and B1), and
    `loso_B1_x` replays B1 (120 walks; trained on A1, A2, A3 and B2);
  - calibration is causal (every earlier window of the session), as in the engine, unless a lever says otherwise;
  - every change is paired against engine v2 on the same walks, with a 95 % bootstrap interval over participants
    (10,000 resamples, seed 0);
  - chance is 16.67 %.
- **Engine v2, the reference:**
  - 35.56 % [21.11, 52.78] (to B1 35.83, to B2 35.00);
  - 63 of 180 walks named PA1; PA2 3 of 30;
  - per person: PA5 30.0, PA1 73.3, PA2 10.0, PA3 23.3, PA4 36.7, PA6 40.0.

## 0. In short

- **No lever is PROMISING.** Nothing in Tiers 0 to 2 moves the engine towards 50 % by a margin the screen can
  separate from training noise.
- **The noise floor is large:** S = 4.45 points.
  - An ensemble whose CNNs come from one seed scores 29.44 to 33.89.
  - The feature components with other random states score 33.89 to 35.56.
  - Engine v2's own settings sit at the top of both spreads.
- **The best single lever** is one temperature per component, cross-fitted:
  - natural 38.89 %, a paired +3.33 [-4.44, +13.33];
  - positive on both folds (to B1 +4.17, to B2 +1.67);
  - fewer walks named PA1 (53) and more of PA2's right (5 of 30).
  - It fails only the noise floor (3.33 is below 4.45), so it is FLAT.
- **The small gains do not add up.** Temperature + LDA shrinkage 0.7 + bias correction, chosen with the results in
  view, scores 32.78 (-2.78 [-12.78, +7.22]).
- **Tier 0.1 found the brief's bug: the calibration pool mixes layouts.**
  - For 170 of the 180 natural walks, the standardisation and AdaBN pools hold tracking windows recorded with RX2 at
    home.
  - **The fix (fix L) costs 3.33 points:** 32.22 % [17.78, 47.22], paired -3.33 [-7.22, +0.56].
  - Under the brief's rule a bug fix is adopted whatever its effect. It is not built into the engine yet (section 5).
  - It also means that **engine v2's 35.56 includes about 3 points from calibrating identification walks on
    tracking recordings**, which a one-layout deployment would not have.
- **The cadence fallback is not confirmed as the bug.** It fires on 13 of 180 natural walks (7.2 %), and only 5 of
  those 13 sit at the doubled band edge, short of the majority the rule requires.
- **The PA1 lean comes from the CNN components:**
  - alone, they name PA1 on 64, 72 and 76 of 180 walks (the per-link CNN most);
  - the feature components name PA1 on only 28 to 40.
- **Two components dominate the sum because they are sharp:** the LDA (mean log-probability spread 10.06) and the
  per-link CNN (9.43). The four tree components (spread 0.60 to 0.69) barely vote.
- **RX1 is the strongest single link** in the per-link CNN (31.11 % alone), not noise:
  - RX2 alone scores 22.78 and RX3 alone 19.44;
  - dropping RX1 from that component costs 3.33 [-7.78, -0.56].

## 1. The promise rule (quoted from the PLAN note of 17:18) and the noise floor

> **PROMISING** if all four hold:
> 1. the paired natural gain is at least +3.00 points;
> 2. the paired change is above zero on to B1 and on to B2 separately;
> 3. the gain is larger than S;
> 4. the natural walks named PA1 do not rise above 63.
>
> **WORSE** if the paired natural change is -3.00 points or lower and its size is larger than S. **FLAT** otherwise.
> Diagnostic rows that are not an ensemble (single components, single links) are not marked.

**The noise floor** (`runs/identify/lever_screen/noise.json`; inference only for the CNN seeds, retrained feature
components for the random states):

| variant | natural | paired against engine v2 |
|---|---|---|
| CNN components from seed 0 only | 33.89 | -1.67 [-7.78, +4.44] |
| CNN components from seed 1 only | 32.78 | -2.78 [-5.56, +0.00] |
| CNN components from seed 2 only | 29.44 | -6.11 [-9.44, -3.89] |
| feature components, random_state 0 (the engine) | 35.56 | 0 |
| feature components, random_state 1 | 34.44 | -1.11 [-3.33, +0.00] |
| feature components, random_state 2 | 33.89 | -1.67 [-3.89, +0.00] |

- The CNN range is 4.45 and the feature range 1.67, so **S = 4.45**.
- The single-seed range overstates the noise of the three-seed average the engine uses, but the brief asked for this
  measure. Read plainly, on 180 walks a lever needs more than about 4 points before training noise can be ruled out.

**The anchors** (both passed before any lever):
- **A-F:** the feature components retrained on each fold's training rows and re-scored in replay order reproduce the
  replays to 4.6e-14, with 659 of 659 decisions equal.
- **A-C:** the CNN harness reproduces the three CNN components exactly (difference 0.0), with 659 of 659 decisions
  equal.

## 2. The table: every marked lever, sorted by paired gain

All rows are natural walks (n 180), development evaluation, all data seen. "To B1 (paired)" is that fold's accuracy
with its change against engine v2 in brackets. The runtime is the lever's own training and scoring on this machine.

| tier | lever | natural [95 %] | paired [95 %] | to B1 (paired) | to B2 (paired) | named PA1 | PA2 (of 30) | verdict | runtime |
|---|---|---|---|---|---|---|---|---|---|
| 1.2 | one temperature per component (cross-fitted), then the sum | 38.89 [25.56, 53.33] | +3.33 [-4.44, +13.33] | 40.00 (+4.17) | 36.67 (+1.67) | 53 | 5 | FLAT | 0 s |
| 1.5 | session bias correction over earlier windows (same layout); assumes everyone walks equally often | 36.67 [24.44, 48.89] | +1.11 [-5.56, +7.78] | 34.17 (-1.67) | 41.67 (+6.67) | 57 | 5 | FLAT | 0 s |
| 2.2 | LDA with fixed shrinkage 0.7 | 36.11 [21.67, 55.00] | +0.56 [-1.11, +2.22] | 35.00 (-0.83) | 38.33 (+3.33) | 64 | 3 | FLAT | 21 s |
| 1.3 | the sum of ranks (ties broken by the engine's ensemble) | 35.56 [26.67, 44.44] | +0.00 [-10.00, +10.00] | 35.83 (+0.00) | 35.00 (+0.00) | 47 | 8 | FLAT | 0 s |
| 1.3 | features and CNNs each summed and normalised, then added (identical to the engine by construction; section 6) | 35.56 [21.11, 52.78] | +0.00 [+0.00, +0.00] | 35.83 (+0.00) | 35.00 (+0.00) | 63 | 3 | FLAT | 0 s |
| 1.1 | leave out cnn_prior | 35.00 [22.22, 51.67] | -0.56 [-3.33, +1.67] | 35.83 (+0.00) | 33.33 (-1.67) | 58 | 4 | FLAT | 0 s |
| 1.1 | leave out et_pace_prior | 35.00 [21.11, 52.22] | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 63 | 3 | FLAT | 0 s |
| 1.1 | leave out rf | 35.00 [21.11, 52.22] | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 64 | 3 | FLAT | 0 s |
| 1.1 | leave out rf_pace_prior | 35.00 [21.11, 52.22] | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 63 | 3 | FLAT | 0 s |
| 1.1 | leave out rf_prior | 34.44 [19.44, 52.22] | -1.11 [-2.22, +0.00] | 34.17 (-1.67) | 35.00 (+0.00) | 62 | 2 | FLAT | 0 s |
| 1.3 | the two families at equal weight: feature mean + CNN mean (addition 1) | 34.44 [18.89, 54.44] | -1.11 [-4.44, +2.22] | 32.50 (-3.33) | 38.33 (+3.33) | 67 | 2 | FLAT | 0 s |
| 1.3 | the sum of per-walk z-scored log-probabilities | 34.44 [25.00, 46.11] | -1.11 [-8.89, +7.22] | 32.50 (-3.33) | 38.33 (+3.33) | 54 | 6 | FLAT | 0 s |
| 1.5 | session bias correction over earlier windows (every one); assumes everyone walks equally often | 34.44 [17.22, 52.78] | -1.11 [-5.56, +3.89] | 32.50 (-3.33) | 38.33 (+3.33) | 69 | 1 | FLAT | 0 s |
| 2.2 | LDA with fixed shrinkage 0.9 | 34.44 [20.56, 49.44] | -1.11 [-3.89, +2.22] | 33.33 (-2.50) | 36.67 (+1.67) | 62 | 3 | FLAT | 20 s |
| 2.2 | logistic regression (L2, C 0.01) in the LDA's place | 34.44 [18.33, 56.11] | -1.11 [-4.44, +3.89] | 35.00 (-0.83) | 33.33 (-1.67) | 70 | 2 | FLAT | 20 s |
| 1.4 | the per-link component from RX2 only | 33.89 [21.11, 48.89] | -1.67 [-5.56, +3.89] | 32.50 (-3.33) | 36.67 (+1.67) | 56 | 3 | FLAT | 0 s |
| 2.4 | families dop, spec, wav, mod only | 33.89 [20.00, 52.78] | -1.67 [-5.56, +2.22] | 32.50 (-3.33) | 36.67 (+1.67) | 65 | 3 | FLAT | 10 s |
| 1.1 | leave out cnn | 33.33 [20.00, 50.56] | -2.22 [-6.11, +1.11] | 33.33 (-2.50) | 33.33 (-1.67) | 60 | 4 | FLAT | 0 s |
| 1.3 | the mean of probabilities | 33.33 [16.67, 54.44] | -2.22 [-5.56, +2.22] | 31.67 (-4.17) | 36.67 (+1.67) | 72 | 1 | FLAT | 0 s |
| 2.3 | feature components trained on matched rows only | 33.33 [21.67, 47.78] | -2.22 [-13.33, +11.67] | 32.50 (-3.33) | 35.00 (+0.00) | 52 | 11 | FLAT | 9 s |
| 2.5a | standardisation by (session, layout); test pool same layout | 33.33 [17.78, 51.67] | -2.22 [-4.44, -0.56] | 33.33 (-2.50) | 33.33 (-1.67) | 60 | 1 | FLAT | 14 s |
| 1.2 | beyond the brief: eight weights fitted jointly (cross-fitted) | 32.78 [17.22, 52.22] | -2.78 [-11.67, +7.22] | 35.00 (-0.83) | 28.33 (-6.67) | 56 | 3 | FLAT | 0 s |
| 2.1 | feature columns: RX2 + RX3 (418 + 3) | 32.78 [20.00, 51.67] | -2.78 [-8.89, +2.78] | 30.83 (-5.00) | 36.67 (+1.67) | 68 | 5 | FLAT | 16 s |
| 2.3 | matched rows (other Room B day's identification walks) weighted x2 | 32.78 [21.11, 48.89] | -2.78 [-8.89, +2.22] | 30.83 (-5.00) | 36.67 (+1.67) | 64 | 5 | FLAT | 24 s |
| 2.4 | families without rhy and tplacf | 32.78 [20.56, 51.67] | -2.78 [-7.22, +1.67] | 32.50 (-3.33) | 33.33 (-1.67) | 65 | 4 | FLAT | 13 s |
| 0.1 | fix L: calibrate only on earlier windows of the same layout (features and AdaBN); **a bug fix** | 32.22 [17.78, 47.22] | -3.33 [-7.22, +0.56] | 30.00 (-5.83) | 36.67 (+1.67) | 56 | 1 | FLAT | 29 s |
| 1.4 | the per-link component from RX2 + RX3 only | 32.22 [19.44, 49.44] | -3.33 [-7.78, -0.56] | 31.67 (-4.17) | 33.33 (-1.67) | 60 | 3 | FLAT | 0 s |
| 2.5b | standardisation per path from training statistics only | 32.22 [15.56, 53.90] | -3.33 [-10.00, +3.33] | 31.67 (-4.17) | 33.33 (-1.67) | 72 | 2 | FLAT | 13 s |
| 2.5d | session standardisation without the path split | 32.22 [16.67, 52.78] | -3.33 [-7.78, +1.11] | 30.83 (-5.00) | 35.00 (+0.00) | 72 | 2 | FLAT | 14 s |
| 1.1 | leave out cnn_perlink_prior | 31.67 [18.89, 45.00] | -3.89 [-9.44, +2.22] | 33.33 (-2.50) | 28.33 (-6.67) | 56 | 2 | FLAT | 0 s |
| 2.1 | feature columns: RX2 only (209 + 3 step-rate) | 31.67 [18.89, 52.22] | -3.89 [-10.56, +2.78] | 30.83 (-5.00) | 33.33 (-1.67) | 67 | 4 | FLAT | 12 s |
| 2.3 | matched rows weighted x4 | 31.67 [19.44, 50.00] | -3.89 [-11.11, +2.22] | 30.00 (-5.83) | 35.00 (+0.00) | 64 | 5 | FLAT | 41 s |
| 1.1 | leave out lda_pace_prior | 31.11 [16.11, 53.33] | -4.44 [-10.56, +2.22] | 30.00 (-5.83) | 33.33 (-1.67) | 71 | 3 | FLAT | 0 s |
| 2.2 | the LDA component removed (retrained set) | 31.11 [16.11, 53.33] | -4.44 [-10.56, +2.22] | 30.00 (-5.83) | 33.33 (-1.67) | 71 | 3 | FLAT | 20 s |
| 2.5c | no session standardisation: global training statistics | 29.44 [14.44, 50.00] | -6.11 [-12.78, +0.00] | 28.33 (-7.50) | 31.67 (-3.33) | 67 | 2 | WORSE | 13 s |

**Per person for the two rows that matter most** (natural, %; engine v2: PA5 30.0, PA1 73.3, PA2 10.0, PA3
23.3, PA4 36.7, PA6 40.0):

| | PA5 | PA1 | PA2 | PA3 | PA4 | PA6 |
|---|---|---|---|---|---|---|
| 1.2, temperature | 56.67 | 66.67 | 16.67 | 26.67 | 30.00 | 36.67 |
| 0.1, fix L | 33.33 | 63.33 | 3.33 | 23.33 | 30.00 | 40.00 |

Every row's per-person figures, decisions and settings are in `runs/identify/lever_screen/levers/<id>.json`.

## 3. Tier 0: the findings

**0.1 The calibration pool mixes layouts (the brief's bug).** Source: `runs/identify/lever_screen/tier0/pools.json`.

*What the pools hold:*
- **Feature standardisation:** the earlier windows of the session with the same engine path, used once there are at
  least 10 earlier windows. Line-A tracking passes, recorded with RX2 at home (-0.5, 2.5), carry the same path labels
  (`A_fwd`, `A_rev`) as the identification walks, recorded with RX2 beside the TX (2.0, -0.5). So they enter the
  identification walks' pool.
- **AdaBN:** every earlier window of the session, for all four networks and three seeds, with no split by path or
  layout.
- **How much is mixed:**
  - 170 of the 180 natural walks have home-layout windows in both pools;
  - the median home share is 9 % of the standardisation pool and 33 % of the AdaBN pool;
  - PA4's worked walk (B2, position 151) adapted on 151 windows, 60 of them tracking windows; its standardisation
    pool held 51 windows, 6 of them home layout.

*Fix L:* each window calibrates only on earlier windows of its own layout, with the same thresholds. It is test side
only, with no retraining.

| | natural | paired |
|---|---|---|
| fix L (both halves) | 32.22 [17.78, 47.22] | -3.33 [-7.22, +0.56] |
| the standardisation half only (information) | 33.33 | -2.22 [-4.44, -0.56] |
| the AdaBN half only (information) | 34.44 | -1.11 [-2.22, +0.00] |
| 2.5a, the same split on the training side too | 33.33 | -2.22 [-4.44, -0.56] |

- **Under the brief's rule the fix is adopted whatever its effect.** As the PLAN says, it is built into `engine.py`
  only after this report, once, together with whatever you choose.
- **What it means for the thesis:**
  - The replayed sessions stream the tracking recordings too, so engine v2's figures calibrate identification walks
    partly on another antenna layout.
  - A home with one layout would not. Engine v2's 35.56 is about 3 points above what fix L gives on the same walks.
  - Fix L also changes the Room B tracking walks' calibration (home windows only), which this screen did not score.

**0.2 The cadence fallback** (the 180 natural walks re-extracted by the engine's own Extractor; the resolved rate equals
the bank's on 180 of 180 to float32 precision). Source: `runs/identify/lever_screen/tier0/cadence_gaps.json`.
- **How often it fires:** on 13 of 180 walks (7.22 %), with no channel's autocorrelation peak at least 0.30:
  - B2 5, B1 8;
  - PA5 2, PA1 3, PA2 1, PA3 3, PA4 2, PA6 2.
- **Where those walks resolve:** 1.58 to 2.14 Hz, median 1.82 (1.90 on the other walks).
  - 5 of the 13 lie within 0.1 Hz of a doubled band-edge estimate.
  - None of the 13 has a clear energy envelope, so none can be checked against one.
- **By the PLAN's rule (a majority at the doubled edge), the bug is not confirmed,** and fix F was not run.
  - The doubled edge does decide 5 walks.
  - Fix F (no qualifying channel means no rhythm) can be screened in about 5 minutes if you want it.
- **The per-link resolvers fall back far more often:** RX1 69, RX2 77, RX3 76 of 180 walks; 14, 19 and 17 of those
  at the doubled edge. Information only: these feed 3 of the 630 columns and the link spread.
- **The rhythm is weak on natural walks generally:** the number of the 9 voting channels with a clear rhythm is 0 on
  13 walks, 1 on 32, 2 on 39, 3 on 39, and 4 or more on 57.

**0.3 Each component alone** (from the saved replays). Source: `runs/identify/lever_screen/tier0/components.json`.

| component | natural [95 %] | named PA1 | mean log-probability spread | true-class NLL | temperature fitted (to B2, to B1) |
|---|---|---|---|---|---|
| rf | 25.56 [10.00, 42.78] | 40 | 0.666 | 1.704 | 0.50, 0.50 |
| rf_prior | 31.11 [21.11, 46.11] | 28 | 0.690 | 1.715 | 0.79, 0.50 |
| rf_pace_prior | 29.44 [17.22, 46.67] | 31 | 0.685 | 1.704 | 0.81, 0.49 |
| et_pace_prior | 21.11 [13.33, 30.01] | 31 | 0.598 | 1.754 | 0.97, 0.52 |
| lda_pace_prior | 21.67 [17.78, 26.67] | 35 | **10.062** | **3.967** | 13.23, 8.15 |
| cnn | 28.33 [16.67, 44.44] | 64 | 4.462 | 2.141 | 6.09, 5.14 |
| cnn_prior | 28.33 [13.89, 47.78] | **72** | 4.034 | 2.022 | 5.08, 4.82 |
| cnn_perlink_prior | 30.56 [13.89, 54.44] | **76** | **9.433** | 3.188 | 7.99, 7.79 |

- **The lean towards PA1 comes from the CNN components.** Alone they name PA1 on 64, 72 and 76 walks. Under
  the per-link CNN, PA5's walks are named PA1 18 times of 30 and PA2's 11. The feature components name PA1
  on 28 to 40 walks, near the 30 an even spread would give.
- **The sum is dominated by the sharp components:**
  - the LDA (spread 10.06, and the worst true-class log-likelihood, 3.97) and the per-link CNN (9.43) carry most of
    it;
  - the four tree components (spreads 0.60 to 0.69) barely move it, which is why leaving any one tree out changes
    the natural score by at most 1.11.
- **Every component is over-confident except the trees.** The cross-fitted temperatures flatten the LDA by 8 to 13
  times and the CNNs by 5 to 8, and sharpen the trees by up to about 2. That rebalancing is what lever 1.2 does.

**0.4 Each receiver's per-link CNN alone** (AdaBN on the engine's pool, mean over seeds).

| link | natural [95 %] | named PA1 |
|---|---|---|
| RX1 | **31.11** [18.89, 42.78] | 53 |
| RX2 | 22.78 [9.44, 40.56] | 59 |
| RX3 | 19.44 [9.44, 32.78] | 51 |

- **RX1 is not at chance; it is the strongest link.** On line A it has F = 0 (no walking Doppler), so what it
  carries is most likely the walker shadowing the TX to RX1 line of sight, not gait.
- Fusing the per-link component without RX1 costs 3.33 [-7.78, -0.56] (lever 1.4).

**0.5 Packet gaps** (report only; every identification window re-extracted):
- No natural window holds a 50 ms bin empty on all three receivers, or on any one receiver.
- The longest gap between frames in a natural window is a median of 13 to 14 ms per receiver, and at most 20 ms.
- One of all 419 identification windows (a fast walk on B1) holds two bins empty on all three receivers; its longest
  gap is 148 ms on RX2.
- **How a gap is filled:** `id19_bank._interp_cols` interpolates linearly between the neighbouring frames by causal
  clock time, clamped at the window's ends, so a gap is a straight line and never zeros.
- Nothing here needs changing.

## 4. The combination

- **The combination the brief asks for** is the compatible PROMISING levers plus any adopted bug fix. **No lever is
  PROMISING, so it is fix L alone:** 32.22 % [17.78, 47.22], paired -3.33 [-7.22, +0.56]. It moves away from 50 %,
  not towards it.
- **Do the small gains add up?** Information only, chosen with the test days' results in view (PLAN note 17:33,
  addition 3):

| combination | natural [95 %] | paired | to B1 | to B2 | named PA1 | PA2 (of 30) |
|---|---|---|---|---|---|---|
| temperature + LDA shrinkage 0.7 + bias correction (same-layout pools) | 32.78 [20.00, 45.00] | -2.78 [-12.78, +7.22] | 32.50 | 33.33 | 47 | 3 |
| the same + fix L | 32.22 [19.44, 44.44] | -3.33 [-12.22, +5.00] | 30.83 | 35.00 | 46 | 4 |

- **They do not add up; they overlap and partly cancel.** Their separate point gains were +3.33, +0.56 and +1.11.
  Together they do worse than temperature alone, although they cut the walks named PA1 from 63 to 47.
- **How far towards 50 %:** none of the way. The best single number in the screen, 38.89 (temperature), is 11 points
  short, inside the noise floor of engine v2, and its interval runs from -4.44 to +13.33.

## 5. Recommendation

**Build fully (all seeds, both folds, the leave-one-session-out tracking walks, then the engine and the app with n of
n verification):**
1. **Fix L, because it is a bug fix.** I recommend building it whatever its cost.
   - It is what a home with one antenna layout does anyway.
   - It gives the honest deployment figure, which the screen puts near 32 % rather than 35.56 %.
   - It needs your go-ahead, because it lowers the headline and opens engine v3.
2. **Optionally, the per-component temperatures (1.2).** It is the only lever whose gain is positive on both folds
   and that also reduces the lean (PA1 53, PA2 5 of 30).
   - It is FLAT by the rule, and a full build must fit the temperatures without either test day, for example on
     inner leave-one-session-out replays of the training sessions, as A4 did (7 inner trainings and 8 replays).
   - My expectation is that it will not survive that, since its interval spans -4.44 to +13.33.

**Tier 3, which you asked to see this table before starting:**
- **3.1, CNNs with matched-data weighting:** not indicated. Matched weighting made the feature components worse
  (x2 -2.78, x4 -3.89).
- **3.2, the per-link CNN without RX1:** contraindicated. RX1 is the best single link, and dropping it costs 3.33
  [-7.78, -0.56].
- **3.3, DANN:** the one Tier 3 item worth running.
  - It is your stated thesis angle, and it targets what limits this engine. The same day gives 55.00 % on B1 and
    70.83 % on B2 against 35.00 and 37.50 across days (the teaching pack's AC2).
  - The cross-day gap is about 20 to 33 points, while every fusion, feature and standardisation lever here moves
    the result by less than the 4.45-point noise floor.
  - Run one seed first, judged against S.

**Drop:**
- link subsets for the features and the per-link component;
- the LDA variants and the LDA's removal;
- the matched weighting and matched-only training (though matched-only did lift PA2 to 11 of 30 and cut PA1 to
  52, at -2.22 [-13.33, +11.67]);
- the family subsets;
- standardisation variants b to d;
- the fusion rules (mean, ranks, z-scores, family weights);
- the session bias correction.

**Plainly:** nothing cheap moves engine v2 towards 50 %. The engine's limit is cross-day transfer, not fusion,
feature choice or standardisation.

## 6. Notes and what went wrong

- **One lever was degenerate as written.** "Each family's sum normalised, then added" (1.3) is identical to the
  engine by construction: normalising subtracts one constant per window, which never changes the argmax. The
  equal-weight version (feature mean plus CNN mean) was added under the 17:33 PLAN note, before it ran: -1.11 [-4.44,
  +2.22].
- **The cadence anchor first matched only 45 of 180 walks.** The cause was a tolerance of 1e-9 against a float32
  bank; the largest relative difference was 5.2e-8. With a relative tolerance of 1e-6 it is 180 of 180, and no
  finding changed.
- **Two PLAN note times were wrong** because they were typed before the clock was read:
  - the note headed 17:38 was written at 17:33, and a correction note says so;
  - that correction is headed 17:34 but was written at 17:33.
  - Nothing ran in between, and the order of rules before results holds.
- **What the screen does not cover:** the leave-one-session-out tracking walks, slow and fast walks, and the app.
  Each chosen lever needs those in its full build.

## 7. Files and commands

| what | where |
|---|---|
| code (new) | `pipeline/identify/ils_common.py` (data, scoring, rule, records), `ils_cnn.py` (CNN harness, anchor A-C), `ils_feat.py` (feature retrains and re-scoring, anchor A-F), `ils_extract.py` (Tier 0.2 and 0.5; fix F's bank, not run), `ils_screen.py` (Tiers 0 to 2, noise floor, additions, table) |
| outputs | `runs/identify/lever_screen/`: `levers/<id>.json` (one per row), `table.json`, `table.md`, `noise.json`, `anchor_feat.json`, `anchor_cnn.json`, `tier0/` (pools, cadence and gaps, components), `cnn/` (every network and seed's output, engine and layout pools), `logs/` |

Commands, from the repository root with `OMP_NUM_THREADS=1 PYTHONPATH=.`:
```
python3 -m pipeline.identify.ils_feat                         # anchor A-F
python3 -m pipeline.identify.ils_cnn --pool engine --device mps   # anchor A-C
python3 -m pipeline.identify.ils_cnn --pool layout --device mps   # fix L's AdaBN
python3 -m pipeline.identify.ils_extract walks                 # Tier 0.2 and 0.5
python3 -m pipeline.identify.ils_screen noise | tier0 | tier1 | tier2 | extra | table
```

The whole screen ran from 17:22 to 17:34 on this machine; every lever's runtime is in the table.
