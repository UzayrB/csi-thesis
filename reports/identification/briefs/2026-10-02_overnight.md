# Brief: overnight run, 2 October 2026 (unattended; I am asleep)

## How to run tonight

I am asleep until morning, so decide everything from this brief, write each decision into the PLAN note, and never wait for me.

**Running safely, unattended:**
- One GPU job at a time, under the watchdog (9 GB per job, stop below 30 % free memory).
- Long queues run detached.
- If a job fails twice, skip it, log why, and carry on. Never relaunch blindly.
- Commit and push after every part, so partial results survive.
- Keep a running log in `runs/identify/overnight/log.md`, with a timestamp per step, read from the clock.
- Each part has a time budget. If a part overruns it, stop that part, record what finished, and move on.

**Order of work:**
1. Let the engine v4 build that is already running finish untouched: replays, the screen-prediction check, the rig path n of n, the tests and the full re-score.
2. Then Parts 1 to 6 below, in order.
3. Whatever happens, by morning there must be:
   - a verified engine (v4, or v5 if the final rule holds);
   - its render command and expected count;
   - its teaching pack (the 1 October spec, with the selection rule re-applied);
   - the report with a morning summary at the top.

## Rules that do not change

- One start press and no end press. No press-timed walk time and no press speed as an input at test time.
- Nothing from tracking's output, no warm-up, only unlabelled same-day adaptation through the existing causal calibration pools (fix L), no new data, names not codes.
- The 4.0 s window and engine v3's bug fixes stay. Development evaluation, all data seen.
- **Press speed may be used as a training target, never as an input.** Learning to measure speed from the radio, with the stopwatch as the teacher, is allowed; the test-time speed must come from the radio alone.

## The guard against a false win (read this before choosing any method)

**No method may use the test day's other walks** except through the existing calibration pools. That rules out clustering the day's walks, smoothing over walk sequences, one-to-one name assignment, pseudo-labelling and self-training. The reason is how the recordings were made:
- each person's walks sit in one contiguous slot;
- RX2 was re-placed for every slot, so every slot has its own RX2 placement;
- tonight's diagnostic showed same-day RX2 at 45.24 % against 15.48 % across days.

So any method that groups the day's walks would learn the slot, not the person, and look excellent for no real reason.

**A sanity check before you trust any big gain.** If any arm gains more than +8 points, re-score it with each test session's walks in shuffled order; any causal pool should then be built in that order. Report whether the gain survives. If it does not, the arm is invalid.

## Part 1: learn the speed from the radio, with the stopwatch as the teacher (budget 90 minutes)

**Why this is the best bet.** At 4 s:
- press speed alone scores 38.33 %;
- the engine's Wi-Fi speed alone scores 31.67 %, and its Pearson against press speed is 0.717 on natural walks;
- the gait features on RX2 carry no cross-day identity.

The identity that crosses days is mostly in the physics, and the radio's speed measurement is the weak link.

**What to build.** A regressor that predicts each walk's press speed from the radio only, trained on the fold's training sessions only, using every walk with presses (identification and tracking walks, all paces).

1. **1a: gradient-boosted regression** (or ridge if boosting is unavailable). Inputs:
   - the RX2 and RX3 torso contours;
   - their centroid and percentile statistics;
   - the energy-envelope rise and fall times;
   - each link's bistatic factor F for the walk's path;
   - the window's frame count.
   
   This runs on the CPU in minutes.
2. **1b: a small CNN regressor** on the RX2 and RX3 4 s maps, with F as an input. One GPU job, seed 0, then seeds 1 and 2 if 1b beats 1a on its Pearson.

**Report, as identity-blind information:**
- Pearson against press speed and the median absolute error, on natural, slow and fast walks, for each fold;
- the same for the current Wi-Fi speed.

**Then use the better learned speed in three places:**
- in place of the Wi-Fi speed column in the three pace components (engine arm 1-L);
- as a new control, S_learned: a one-number LDA, like S_wifi;
- reported beside S0 and S_wifi on natural, slow and fast.

## Part 2: a physics component, scored as its own vote (budget 30 minutes)

Tonight's columns added to the 630 features were drowned among them. This time give the physics its own classifier, as a ninth component.

- **The vector** (about 20 to 40 values):
  - the learned speed;
  - the RX2 and RX3 contour statistics;
  - acceleration from standing (time to steady speed, steady speed);
  - the step rate, where usable (NaN otherwise);
  - RX1's along-path attenuation depth, width and asymmetry, and its power at the step rate.
- **The classifier:** strongly regularised logistic regression; choose C by leave-one-session-out across the training sessions only.
- **Score it two ways:** fused as a ninth component in the equal sum, and with the per-component temperatures.

## Part 3: MiniRocket as a fresh time-series component (budget 45 minutes)

MiniRocket (Dempster et al., 2021) uses random convolutional kernels with a ridge classifier. It is fast and strong on small time-series datasets, and it reads the signal in a different way from both the hand-made features and the CNNs.

- **The inputs:**
  - RX1's and RX3's band-passed subcarrier-mean and PC2 to PC4 traces at full rate;
  - RX2's torso contour and energy envelope;
  - RX2's amplitude traces are left out, because they follow RX2's placement.
- **Fuse it** as an extra component.
- **If the package cannot be installed** (sktime or the reference code) within 15 minutes, skip this part and log why.

## Part 4: more CNN seeds (budget 75 minutes, GPU, one job at a time)

- Train seeds 3 to 9 of the engine's CNN recipe, exactly as v3 trains them, then score the 4 s window with 10 seeds averaged against v4's 3.
- Single seeds range from 29.44 to 33.89, so averaging more of them may simply lower the noise.

## Part 5: stack and confirm

**Stack in this order:** v4, then Part 1 (the learned speed), then Part 4 (the 10 seeds), then Part 2, then Part 3.

**The step rule** (a lever is kept only if all of these hold against the stack so far):
1. the natural gain is at least +2.22;
2. neither fold falls by more than 3.4;
3. neither slow nor fast falls by more than 2.5;
4. the walks named PA1 rise by no more than 5.

**The final rule, for v5:**
1. the natural paired gain against v4 is at least +3.33 and positive on both folds;
2. slow and fast are each no more than 2.5 below v4's;
3. the leave-one-session-out tracking walks (Room A and Room B) are no more than 4.45 below v4's;
4. all of this holds with every seed involved;
5. the shuffled-order check passes for any gain above +8.

## Part 6: build, so there is a verified result in the morning

- **If the final rule holds:**
  - build engine v5 into `engine.py`;
  - retrain what it needs;
  - replay, and verify the rig path n of n;
  - run the tests;
  - re-score everything: natural, slow, fast, leave one session out, S0, S_wifi, S_learned, the deployment measures, confidence and per person.
- **If not,** engine v4 stands.
- **Either way,** finish with:
  - the final engine's render count on B2's natural blocks, and the command;
  - its teaching pack to the 1 October spec, with the selection rule re-applied unchanged.

## What to give me in the morning

**`reports/identification/2026-10-02_overnight.md`,** starting with a morning summary of no more than ten lines:
- the final engine and its natural, slow and fast figures with intervals;
- what won and what did not;
- the verification count;
- where the teaching pack and the render command are.

**Then:**
1. the full table, every row paired against v4;
2. the learned-speed Pearson table;
3. the step-by-step stack;
4. the final rule's checks;
5. the shuffled-order check, if any arm needed it;
6. a "plainly" section that tells me, in one paragraph, how close the final engine is to 50 %, and what in the data stands in the way.
