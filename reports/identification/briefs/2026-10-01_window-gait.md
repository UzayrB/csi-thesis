# Brief: housekeeping, then longer windows and gait analysis (1 October 2026, night)

## Goal

Engine v3 scores 32.22 % [17.78, 48.33] on the 180 natural identification walks. Find out whether seeing more of the walk, and reading gait more carefully, can lift it above 40 % from one start press, with speed used only as one gait parameter, and without the slow and fast walks dropping.

Everything after Part 0 is a screen: nothing changes in the engine until I choose.

**Hard stop: the end of 2 October.** After that I write.

Write a PLAN note before anything in Parts A to D runs, with the arms, the reference, the rule and the order below, and commit it.

## Rules that do not change

- **One start press and no end press** (semi-constrained). No press-timed walk time and no press speed as inputs.
- Nothing from tracking's output, no warm-up, only unlabelled same-day adaptation (fix L layout pools), no new data, names not codes.
- **Development evaluation, all data seen.** Engine v3's two bug fixes stay in.
- **The end press may be used only in the information-only ceiling arm (W-oracle),** never in a deployable arm, and never as a feature.
- **Speed is one gait parameter, never the identifier.** Every arm is judged on the slow and fast walks as well as the natural ones. Speed alone is at chance on paced walks (press speed: slow 17.5 %, fast 16.8 %), so those walks are the test that a gain is gait and not pace.

## Part 0: housekeeping (do this first, about 15 minutes)

1. **`reports/ID_THESIS_SUMMARY.md`: add an engine v3 section.** It should state:
   - engine v3's figures are the thesis figures;
   - the drop from v2 to v3 in one plain sentence: two bug fixes, with v2's 35.56 % including about 3 points from calibrating identification walks on tracking recordings of another antenna layout;
   - the DANN result;
   - the one-press cost of −7.78 [−17.78, +3.89], as measured against the frozen two-press reference, which was built with the v1 step-rate resolver and whose interval includes zero (report it, do not lean on it);
   - that T was not changed on the strength of the T-sensitivity check (3.5 s gave 35.00 %), and that any window change comes only through this brief's rule.
2. **Add one dated "superseded" line** at the top of `HANDOFF_IDENTIFICATION_2026-10-01` and of `HANDOFF_IDENTIFICATION_2026-10-01_PM`, pointing to `reports/ID_V3_DANN_2026-10-01.md` and to this brief's report. That is the only edit to those files.
3. **The render: do not re-record yet.** The engine may change again tomorrow. At the very end, state the expected end count for the final engine on B2 natural blocks and the exact command, so I record it once.
4. **The teaching pack** is built only after I choose the final engine (Part E), with the 1 October spec and the same selection rule re-applied.

## Part A: how much of the walk to see (feature retrains in seconds, CNN inference only)

**First, check what follows each walk.**
- Report what the recordings hold after the end press on identification walks: standing still, turning, the next pass, or the operator.
- Give the median time from one walk's end press to the next start press, by pace block.
- Any window must stop at the next start press if that comes first (causal: the live app would have that press too).

**Two fixes for every window longer than 3 s:**
- The direction rule keeps using only [t0, t0 + 3 s]. RX2's energy falls once the walker stops, which could flip the slope's sign on towards walks.
- The Wi-Fi speed uses only frames with walking, up to the detected end in W-radio and up to t0 + T in the fixed windows, with standing frames excluded by the same torso-energy test.

**Feature components** retrain on each arm's windows. **The CNNs keep v3's weights:** they score fixed 34-frame (1.81 s) windows, so a longer map just gives more windows to average.

**The arms:**
1. **Fixed windows:** T = 3.0 (the v3 reference), 3.5, 4.0, 4.5, 5.0 and 6.0 s.
2. **W-radio, an end detected from the radio** (deployable). The window runs from the press until RX2's 10 to 35 Hz torso-band energy falls below a threshold for 0.5 s, capped at 6 s and never shorter than 2.5 s.
   - Fix the threshold rule in the PLAN note before scoring, from physics or the training sessions only.
   - Report the detected end against the true end press (median error, by block), as information.
   - A start-only end detector lost 14 points in the two-press era. Say plainly whether this one is better, and why.
3. **W-oracle** (information only). The window from the press to the true end press: the ceiling of whole-walk information without the timing as a feature.

**Carry the best window forward.** Parts B and C use the deployable window with the best natural score that does not break the slow and fast guard (rule point 3), even if it is not PROMISING on its own. Longer windows give more steps, and several gait levers below depend on that. Record that this choice was made with results in view.

## Part B: gait parameters, on the best window (seconds each)

1. **The walk ratio and speed-normalised cadence.**
   - **Walk ratio:** step length divided by step rate, which is v / f_step². In the gait literature (Sekiya and Nagasaki, 1998) it stays close to constant for one person across walking speeds and differs between people.
   - **Speed-normalised cadence:** the residual of step rate from a population speed–cadence line fitted on the training sessions only.
   - **Stride length:** v / f_step.
   - **Step-rate reliability:** use only walks whose step rate has a qualifying channel, and NaN otherwise (fix F).
   - Report the share of walks with a usable step rate at this window against 3 s.
2. **A sub-bin torso velocity contour.** Replace the arg-max torso bin with a continuous per-frame estimate: the power-weighted centroid in the torso band, or parabolic interpolation around the peak.
   - Re-run A1's precise-speed estimator on this window and report its Pearson against press speed, as identity-blind information; its gate at 3 s missed by 0.003.
   - From the contour add:
     - the mean speed;
     - the velocity fluctuation at the step rate, divided by the mean speed (a pace-normalised gait parameter);
     - the start-up acceleration from standing, as the time to 90 % of the steady speed and that speed's ratio to the steady speed.
3. **Report Part B with and without the raw Wi-Fi speed column.** I want to see whether the pace-normalised parameters carry identity beyond speed.
4. **(Optional, labelled body shape and not gait.)** RX1 is the strongest single link (31.11 % alone) and probably reads the walker shadowing the TX to RX1 line of sight.
   - Resample its attenuation profile from time to distance along the path, using the Wi-Fi speed, so that it is pace-invariant.
   - Add its depth and width as features.

## Part C: the networks (one seed against the same-seed baseline, both folds; about 8 minutes per arm)

Use the exact same-seed method as the DANN screen: the engine's trainer at seed 0, reproduced bit for bit, as the baseline.

1. **C1, pace-normalised Doppler maps.** For each frame, divide the frequency axis by the walk's own torso frequency (from the contour), so the torso always sits in the same row and limb energy sits at a fixed multiple of it.
   - The map then holds the shape of the gait, with pace and geometry removed.
   - Feed the Wi-Fi speed back to the head as one scalar beside the direction flag, so speed enters as one parameter.
   - Use RX2 and RX3 only (RX1 has no torso Doppler on line A); keep RX1 in its own per-link component as now.
2. **C2, velocity maps (geometry only).** Convert each link's frequency axis to body velocity through its bistatic factor, v = f λ / (2F), masking links with F below 0.3.
   - This is the 1-D version of Widar3.0's body-velocity profile, and it lets Room A's line-A passes share an axis with the identification layout.
   - Comparing C1 with C2 tells me whether pace carries identity beyond the gait's shape.
3. **C3, cross-session contrastive training.** Add a supervised contrastive loss on the pooled 896 features whose positives are the same person from a different session, alongside the identity loss.
   - DANN removed the session but never asked the same person to look the same across days; this does.
   - Use two weights, 0.1 and 0.5.

## Part D: combine and confirm

- Combine the PROMISING levers from A to C that are compatible, scored once together.
- Confirm the best deployable combination with all three seeds, the leave-one-session-out tracking walks (Room A and Room B), S0 and S_wifi on natural, slow and fast, and per-person accuracy.
- A lever is only adopted after it passes on all three seeds, because with this many arms one can pass at a single seed by luck.

## How to score every row

- **Primary:** natural walks (n 180), causal, paired against engine v3 with the participant bootstrap.
- **Equally important:** slow (n 120) and fast (n 119), paired against v3's 25.83 and 23.53.
- **Also:**
  - S_wifi alone on the same windows and the engine minus S_wifi, on natural, slow and fast;
  - to B1 and to B2;
  - the walks named PA1, and PA2;
  - the median decision time after the press, and the share of walks per block whose window ran past the true end press.

**The rule** (quote it in the PLAN note). **PROMISING** means all of:
1. the natural gain over v3 (or over the same-seed baseline in Part C) is at least +4.45 points;
2. it is positive on to B1 and on to B2;
3. neither the slow nor the fast paired change is below −4.45;
4. the engine minus S_wifi on natural walks does not shrink.

Point 4 matters most: a gain that only tracks pace is not the gain I want.

## What to give me

1. **One table:** every row with natural, slow and fast (each paired), to B1 and to B2, PA1, PA2, the decision time, the engine minus S_wifi, and the verdict.
2. **The W-oracle ceiling,** stated plainly: how much of the gap to 40 % whole-walk information could close at best.
3. **The confirmed best combination,** if any, with Part D's checks. Do not build it into the engine until I say.
4. **A plain statement of which gait levers worked and which did not, and why.** I will write about the failures too.
5. **A report:** `reports/ID_WINDOW_GAIT_2026-10-02.md`.

If nothing is PROMISING, say so plainly and stop: identification closes at engine v3, and Part 0's render command and Part E follow for v3.

## Part E (only after I choose)

1. Build the chosen engine (v3, or v4 with the adopted levers) into `engine.py`.
2. Replay it, and verify the rig path n of n.
3. Re-score the full set of figures.
4. Then build the teaching pack to the 1 October spec.
