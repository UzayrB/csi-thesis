# BRIEF: addendum to the teaching-pack brief, identification's copy

Received from Uzayr on 2026-10-01 as `identification_teachingpack_addendum_2026-10-01.md`, saved at 10:31 SAST (clock
read). The text between the rules is his, VERBATIM. Re-read this file before each stage; never work from memory of
it. Nothing below the second rule is part of the brief.

---

# Addendum to the teaching-pack brief (2026-10-01): three more measurements

Add these to the current brief. Everything in it still holds:
- the engine stays frozen;
- tracking has priority;
- names are used;
- every result carries its train and test sessions and its calibration.

These are measurements for the write-up, not development, and none of them changes the model. Put their definitions in a dated `PLAN.md` note and commit it before running any of them.

**Scheduling.** Run them after the current lanes, or in a spare lane when the GPU is free. Never delay the pack for them. Expect about 4 extra trainings and about an hour of CPU work, so a finish around 16:30.

## C1. Step-rate estimator check on simulated walks (bug check, CPU only)

**The open lead.** On the 55 walks with clear rhythm, the cadence resolver reads a median 12 % below the energy envelope (ratio 0.88, interquartile 0.76 to 0.95). The audit's simulated walk recovered 1.786 steps per second against a true 1.8.

**The test.** Extend `idz_synth` to a grid of simulated walks and push each through the real code path, unmodified: amplitude, causal clock, the 3 s engine window, then features. The grid:
- step rates of 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1 and 2.2 per second;
- both directions;
- every walk starting from standing, as on the rig;
- three walking speeds per step rate, 1.0, 1.2 and 1.4 m/s.

**Report, per grid point:**
- the resolved cadence divided by the true value;
- the envelope cadence divided by the true value, using the same envelope method as the cadence diagnostic.

**The reading.**
- **If the resolver recovers the true rate (within 5 %) and the envelope does not,** the 12 % gap is the envelope's, or a difference in definition, and there is no bug.
- **If the resolver is biased or erratic on simulated truth,** that is a bug. Find the line responsible, and report the fix and its effect on the features of the two worked walks.
  - **Do not change the frozen engine in this brief.** A fix would invalidate the pack and every figure, so stop and tell Uzayr, who decides.

## C2. Same-day identification (confounded by recording; for the literature comparison)

**Why.** Published accuracy figures are mostly within one session. This gives the engine's own same-day number, so the thesis can show the gap honestly.

**The split.** For B1, within each recording, alternate the walk cycles (one away and one towards walk each): cycles 1, 3, 5 and so on are for training, cycles 2, 4, 6 and so on are for testing. This keeps every person and every block on both sides.

**The run.**
- Train the full frozen engine recipe on B1's training cycles only, with no other session, then replay B1 and score only the test cycles. Calibration is causal, as usual.
- Repeat for B2 the same way.

**Report:**
- natural walks (and all paces), with intervals;
- chance, beside the engine's cross-day figure for the same day.

**Label it "same day, confounded by recording".** Each person's walks come from their own recording slot, so this measures recognising the person plus their recording, which is exactly why published same-session figures run high. Say that in one plain sentence.

## C3. Do the slow and fast walks in training help natural walks? (training-data ablation)

**The question.** Every training set so far included the other Room B day's slow and fast identification walks. It was never measured what they contribute.

**The run.** For both identification folds ("to B2" and "to B1"), retrain the frozen engine recipe on the same training data minus every slow and fast identification walk. Natural identification walks and every tracking walk stay in. Replay and score the test day: natural, away, towards, slow and fast.

**Report:**
- the paired differences against the engine as it is, each with its interval;
- the engine minus S0 and the engine minus S_wifi for both versions, by pace.

**Information only.** Whatever it shows, the engine is not changed, because choosing now would be choosing on the test days. Report it as the answer to "why the paced walks are in training".

## Where the results go

- **The pack:** add C1, C2 and C3 to the results section, with the usual fields.
- **Notes:** add them to `ID_TEACHING_NOTES_2026-10-01.md`:
  - C1 under "How we know it is right";
  - C2 under "How good it is", as the same-day comparison;
  - C3 under the pace confound.
- **The report:** add them to `ID_TEACHING_PACK_2026-10-01.md`.
- **The thesis summary:** append a dated block to `ID_THESIS_SUMMARY.md`.
- **Finish:** add one line each for C1 to C3 to the closing message, each with its number and interval and one plain sentence.

---
