# Overnight summary for Uzayr, 10 to 11 October 2026

Written by the Mastermind from 11 Oct 2026 14:31 SAST (clock read). Every figure is development evaluation, all data seen. Tracking was trained on A1, A2 and B1 (zero-shot: A1 and A2) and tested on A3 and B2, which it never trained on. Identification's engine v5 configuration was chosen with A3 and B2 in view. Intervals are 95 %: a bootstrap over walks for tracking (1,000 draws, seed 0), and a paired participant bootstrap for identification (10,000 draws, seed 0, six clusters). Chance is 8.33 % for tracking (1 of 12 lines) and 16.67 % for identification (1 of 6 people). "Stopwatch" means S0, the press-timed speed through an LDA. It needs the end press, which the engine never gets.

## 1. What happened overnight

**In short.** Engine v5 is shipped with your option (c), and identification development is closed. The confirmation run that the thesis quotes was exact on all 299 decisions. It met the decision cap on 297 of 299 and failed its memory rule, both flagged below. Chapter 3 is written in full and reviewed against the Code. Most of the night was lost to a permission block and the Mac sleeping, so the work ran from 12:39 to 14:30.

**The night, in order.**

| time (11 Oct) | what happened |
|---|---|
| 02:40 | I took over as Mastermind. The machine was QUIET, and engine v5 had been held at its step 7 stop since 10 Oct 22:21. I reproduced the stop report's timing from the result files: cpu 10 of 171 before the cap, mps 74 of 171, and the arithmetic for option (b) 156 and 171 of 171. This showed that only option (c) was predicted to pass. |
| 02:42 to 02:48 | Your prompt arrived (option (c), Drive, close whatever the run shows). I started one caffeinate and granted Agent1 (Third overall) the slot. My first grant message was blocked by the safety classifier as "instruction poisoning", because I had pointed Agent1 at your file without reading it myself. I read it first-hand and resent the grant, citing it line by line. |
| 02:53 | Agent1's own permission layer refused to act on a decision it had been pointed to by another session, and you had told it at 02:41 to wait for your own prompt. It changed nothing and waited. I released the caffeinate at 02:54, since nothing was running. |
| 03:15 to 11:04 | The Mac was in idle sleep (pmset log). Nothing ran and nothing was committed. |
| (my error) | I held the Editor's GO because your prompt said to send it after identification closed. The Editor's tracking sections never depended on identification, and I should have sent a partial GO on my own rather than only offering one. |
| 11:04 | Caffeinate indefinite at your word: PID 8616, detached. It is still on. |
| 12:39 | Your go reached Agent1 in its own chat. I granted the slot. |
| 12:40 | I sent the Editor "GO: methodology", with the timing items left open. |
| 12:48 | Option (c) in the live app, v5 only (da199808): each walk joins the pool and its AdaBN copies are recomputed after its decision is written and shown, and mps is v5's rig default. The live app before and after the change is bit-identical in every decision field for v4 (10 decisions) and v5 (50 decisions) on cpu. |
| 12:49 to 13:54 | **The confirmation run** (section 2.2, the real-time timing). It was alone on the machine, B2's whole day at 1x through the real serial parser, with every decision timed. Exactness PASSED: 299 of 299, difference 0. Timing FAILED: 297 of 299 before the cap. Memory FAILED: it grew 1.99 GB an hour. Under your point 3 nothing was changed. |
| 12:50 | A decision of mine on the cpu exactness check. Agent1 found that the 12 decisions a recording's closing poll makes differ on cpu from the mps replay by up to 9.47e-06, above step 7's 8.1e-06. They do so with the code before the change too, and step 7 had never compared them. I agreed a stricter test: before and after bit-identical on all 299, after within 8.1e-06 of the replay on step 7's 287, and the 12 reported as measured. This accepts no difference. |
| 14:00 to 14:22 | The cpu exactness check PASSED. Before and after are bit-identical on all 299 decisions, and after against the replay gives argmax 299 of 299 and 8.06e-06 on the 287. |
| 14:23 to 14:25 | Storage. All four RF/ET pickles of every v5 model (40 files, 5.78 GB) are kept out of git, because a model needs all four. 27 of them are over GitHub's 100 MiB limit. `runs/identify/v5/STORAGE.json`, `.md` and `.sha256` give each file's size and sha256 and the rebuild command. loso_B2_v5 was rebuilt in a scratch folder and came out byte-identical. I checked all 40 hashes. Drive for desktop is not installed (you removed it on 7 Oct), so the copy to Drive is yours: the steps are in `STORAGE.md`. |
| 14:27 | Identification CLOSED. The final report is `reports/identification/2026-10-11_engine-v5.md` (d63c2df7), with the PLAN note "engine v5 shipped; identification development closed" and JOB_DONE (3a15bcb6). |
| 14:30 | My review APPROVED it. Section 3 equals `expected.json` in all 246 entries. Section 4 matches the run's files, which I recomputed myself. The cpu exactness record and the storage hashes check out, and section 6 (the Editor list) agrees with section 3 and `eval_v5.json`. |

**The Methodology.** The Editor finished Chapter 3 at 13:07, and I reviewed every changed number and claim against the Code in three rounds. I found one factual error in its new text: the pre-registration count left out tracking's cross-room pre-registration of 22 Sep. I also checked what its permission classifier had stopped it reading: `tracking_arch.tex` is clean, and two v4 figures in Results are right. The Editor in turn caught two errors in my GO: DC2 had one block per person per day, not two, and the 30 Sep rig run was engine v2 at maximum speed, not v4 at 1x. The confirmation run's timing went in at 14:04, and at 14:06 a qualifier that the CPU's 10 of 171 was measured with the calibration still before the decision. Chapter 3 has no `\tbc` and no VERIFY marker left.

**What went wrong, and why.**
- The permission blocks: Agent1 would not act on your decision passed through me, and that held everything until 12:39.
- The Mac's sleep from 03:15 to 11:04, after I released the caffeinate at 02:54.
- My held Editor GO.
- Two factual errors in my GO, which the Editor caught.
- The stop report's claim that v4 was timed on mps on 30 Sep, which was wrong. The final report corrects it, and the confirmation run is the first whole-day 1x timing of any engine. The 10 Oct stop report is kept as it was.
- Three times I typed a time into a message or record instead of reading the clock. Each was corrected (the MACHINE_STATE line in 31f5605e).

**Commits** (Code repo, all pushed):
- Agent1: f80266b7 (your go recorded), da199808 (option (c)), 75395573 (the run's pass rules, fixed before it), 7ef73556, 2a7957fb (the 30 Sep correction), d5f273a8 (the confirmation run), 57f8148e (cpu exactness), d63c2df7 (the final report and PLAN note), 3a15bcb6 (JOB_DONE).
- Mine, MACHINE_STATE: f19655a2, 673d73d9, df1671b5, b5e2a3a6, 7dbc5557, 0fa03b59, 31f5605e, 196d3a4e, 6db4ad16.
- Nothing was committed in the report repository. The Editor does not commit.

## 2. All results of the shipped system

### 2.1 Tracking (the clean display, K1gf, live since 10 Oct 12:03)

| figure | committed line [95 %] | lock at press + 2.0 s [95 %] | edges committed (E_col1, E_col5, E_row1, E_row5) | edges lock |
|---|---|---|---|---|
| B2, deployed (the headline) | 97.50 [94.17, 100.00] | 71.67 [63.33, 80.00] | 100, 100, 100, 100 | 100, 100, 50, 83.3 |
| A3, deployed | 92.50 [87.50, 96.67] | 75.00 [67.48, 82.50] | 66.7, 66.7, 100, 100 | 33.3, 100, 100, 83.3 |
| B2, zero-shot (Room A only) | 90.00 [84.17, 95.00] | 57.50 [48.33, 66.67] | 83.3, 100, 83.3, 100 | 100, 50, 50, 33.3 |
| one day of Room B data (deployed minus zero-shot, B2, paired by walk) | +7.50 [2.50, 13.33] | +14.17 [6.67, 21.67] | | |

Source: `reports/tracking/2026-10-10_clean_display_report_update.md`, sections 1.1 to 1.4. The dot on correct-lock walks has a median error of 0.313 m on B2, 0.304 m on A3 and 0.326 m zero-shot. Test looks: A3 seven, B2 five, zero-shot B2 five, plus the 6 Oct dwell ablation's further look at A3 and B2, which the records do not count.

### 2.2 Identification (engine v5)

Source: `reports/identification/2026-10-11_engine-v5.md` (d63c2df7), section 3, with every figure equal to `runs/identify/v5/expected.json`.

**The core model across days** (trained on A1, A2 and B1 path walks only, tested on path walks):

| tested on | walks | v5 [95 %] | stopwatch | v5 minus stopwatch [95 %] | v4 |
|---|---|---|---|---|---|
| A3 and B2 together | 240 | 32.08 [25.83, 43.33] | 30.00 | +2.08 [-13.33, +15.43], level | 27.92 |
| B2 (Room B, a day later) | 120 | 40.00 [27.50, 57.50] | 20.83 | **+19.17 [+3.33, +35.83], beyond it** | 30.83 |
| A3 (Room A, a third day) | 120 | 24.17 [15.83, 32.50] | 39.17 | -15.00 [-38.33, +0.00], level | 25.00 |

**Room A alone** (trained on A1 and A2, tested on A3 path walks): 26.67 [15.83, 39.17], stopwatch 38.33, -11.67 [-39.17, +14.17].

**Zero-shot** (trained in one room, tested in the other):

| trained on, tested on | walks | v5 [95 %] | stopwatch | v5 minus stopwatch [95 %] |
|---|---|---|---|---|
| A1+A2 to B2 path walks | 120 | 29.17 [10.00, 50.00] | 20.83 | +8.33 [-15.00, +33.33] |
| A1+A2 to all B2 walks | 299 | 32.11 [15.38, 48.33] | 20.40 | +11.71 [-15.54, +36.00] |
| B1 to A3 path walks | 120 | 33.33 [22.50, 45.00] | 44.17 | -10.83 [-31.67, +11.67] |

**One day of Room B data** (A1+A2+B1 path walks minus A1+A2, on B2 path walks): +10.83 [-5.00, +24.17], not separable.

**The controlled test (DC2, 26 and 27 Sep).** RX2 was moved beside the transmitter for one fixed identification line, at a mean bistatic factor of 0.981. The physics behaved: RX2's torso contour followed 2Fv/λ across walks (Spearman 0.744), and RX3's did not (0.276). The pre-registered single-link comparison tied TX-RX2 with TX-RX3 at 23.33 % each, on 30 test walks. The pre-registered cross-day result was 26.67 [13.33, 36.67], against the stopwatch's 40.00. Source: `reports/identification/thesis-summary.md`, section 10.

**The best case: the identification walks.** Each Room B day is scored by the model trained on the other four sessions.

| pace | walks | v5 [95 %] | stopwatch | v5 minus stopwatch [95 %] | v4 |
|---|---|---|---|---|---|
| natural | 180 | 36.67 [23.33, 50.00] | 38.33 | -1.67 [-22.78, +13.89], level | 37.78 |
| slow | 120 | 33.33 [9.17, 60.00] | 17.50 | +15.83 [-2.50, +39.17] | 29.17 |
| fast | 119 | 30.25 [20.34, 41.18] | 16.81 | +13.45 [-1.68, +26.89] | 30.25 |
| paced (slow and fast) | 239 | 31.80 [21.67, 43.04] | 17.15 | +14.64 [+0.00, +30.83], at the edge | 29.71 |
| B1 to B2, slow | 60 | 35.00 [6.67, 68.33] | 16.67 | **+18.33 [+3.33, +41.67], beyond it** | 31.67 |

**Top-2 and the household of two** (natural walks, 180):

| measure | v5 [95 %] | chance | stopwatch | v5 minus stopwatch [95 %] |
|---|---|---|---|---|
| top-2 | 61.11 [38.89, 81.11] | 33.33 | 67.78 | -6.67 [-16.67, +3.33] |
| household of two | 75.56 [66.33, 84.22] | 50.00 | 76.78 | -1.22 [-7.89, +4.22] |

**What B1's identification walks add** (A1+A2+B1 all walks, minus path walks only, on the same walks):

| tested on | path walks only | plus B1's identification walks | difference [95 %] |
|---|---|---|---|
| A3 path | 24.17 | 37.50 | +13.33 [+6.67, +21.67] |
| B2 path | 40.00 | 33.33 | -6.67 [-13.33, +2.50] |
| B2 natural | 31.67 | 33.33 | +1.67 [-5.00, +8.33] |
| B2 slow | 43.33 | 36.67 | -6.67 [-18.33, +6.67] |
| B2 fast | 22.03 | 27.12 | +5.08 [-6.90, +18.64] |
| all 419 | 32.22 | 34.13 | +1.91 [-3.58, +6.92] |

**The day diagnostics.**
- Within a day, the amplitude levels alone, which carry no gait, recognise each Room A recording at 91.67 to 98.61 %. Across days they fall to 20.28 %. Each person-session is one recording, so within-day accuracy measures recording recognition (`reports/identification/thesis-summary.md`, section 3).
- Each person's natural speed moves between the two Room B days by a mean 0.057 m/s. The gaps between neighbouring people on B1 are 0.006 to 0.165 m/s (`reports/identification/2026-10-02_overnight.md`, section 10).
- RX2's columns give 45.24 % within a day and 15.48 % across days, because RX2 was re-placed for every person's slot (same source).

**The real-time timing (the confirmation run, 11 Oct 12:49 to 13:54).** B2 was streamed at 1x through the real serial reader and parser, every recording, with `loso_B2_v5` on the GPU (mps), the calibration after each decision, one thread and nice 0. All 299 decisions were timed.

| per press | figure |
|---|---|
| decision delay after t0 + 4.0 s, median / p95 / p99 / max | 1.083 / 1.189 / 1.261 / 1.453 s |
| decisions before the cap (t0 + 5.30 s) | **297 of 299**: the day's first walk 0.001 s late (model call 0.316 s), one slow-block walk 0.153 s late (one window's extraction 0.482 s) |
| model time, three windows, median / max | 0.127 / 0.316 s |
| adaptation after the decision, median / max | 0.277 / 0.525 s; never waited for, done at least 4.99 s before the next walk's last window was due |
| the stream's lag at a press, max | 0.077 s (the rule: at most 0.5 s) |
| decisions equal to the v5 replay | 299 of 299, ensemble difference 0.0 |
| memory | **grew 1.99 GB an hour** (1.64 GB at 10 min, peak 4.47 GB, lowest free memory 62 %), against the "flat" rule of at most 0.5 GB an hour; GPU side, not attributed further |

The run therefore fails two of its three pre-fixed rules, the cap by 2 of 299 decisions and the memory slope. Under your point 3 nothing was changed, and identification closed with the measured figures. The memory growth matters for a long session: at about 2 GB an hour, a session of several hours would approach the 12 GB limit. On the CPU the per-walk calibration grows with the day's pool, to about 6 s per walk (median 2.96 s, max 6.03 s), for v4 and v5 alike (median ratio 1.006). So on the CPU only 10 of 171 decisions met the cap, measured on 10 Oct with the calibration still before the decision (the shipped arrangement was never timed on the CPU), and identification runs in real time on the GPU only.

**The multi-walk figures, for the Discussion** (natural walks, v4 now in the Discussion against v5):

| figure | v4 | v5 [95 %] |
|---|---|---|
| one walk | 37.78 [23.33, 53.33] | 36.67 [23.33, 50.00] |
| round trip | 45.56 | 43.33 [24.44, 63.33] |
| three walks | 48.15 | 50.00 [24.07, 74.07] |
| five walks | 55.56 | 50.00 [30.56, 69.44] |
| household of three, four, five, six | 58.56, 49.39, 42.78, 37.78 | 59.44, 48.78, 41.56, 36.67 |
| one press against two, natural | -2.22 [-10.56, +6.67] | -3.33 [-12.78, +5.00] |
| one press against two, tracking walks | -5.00 [-11.33, +1.17] | -2.17 [-9.67, +5.17] |

## 3. Your framing, filled in

Your paragraphs, with every [pending] filled from the final figures and nothing else changed:

> **Tracking framing.** Tracking is judged on one question, whether it holds on a new day and in a new room, and it answers both. The deployed model is trained only on the path walks of A1, A2 and B1 and tested on A3 and B2, two days it never saw. It commits to the right line on 97.50 % of B2's walks and 92.50 % of A3's, against a chance of 8.33 %, and locks onto it two seconds into the walk on 71.67 % and 75.00 % of them. The zero-shot model, trained on Room A alone, still commits to the right line on 90.00 % of B2's walks in a room it has never seen, and one day of Room B data adds 7.50 points, so tracking carries across both days and rooms at a small, measured cost for a new room.
>
> **Identification framing.** Identification is judged on exactly the same question, on tracking's own split. The core model is the identification engine trained only on the path walks tracking uses. On that footing it identifies people across days at 32.08 % and zero-shot in the other room at 29.17 %, against a chance of 16.67 %. Every figure sits beside the stopwatch, which shows how much of it walking speed alone explains, and two figures go beyond it, B2 a day later by 19.17 points [3.33, 35.83] and the B1 to B2 slow walks by 18.33 points [3.33, 41.67], whilst the rest sit level with it, such as 32.08 against 30.00 % over both days. Room A's first results pointed to a likely cause, because the layout chosen to serve tracking leaves most walking lines with weak or changing Doppler, with line A reaching a factor of only about 0.5. The second data collection was therefore designed as a controlled test of that cause rather than as an improvement: RX2 was moved beside the transmitter for one fixed identification line, raising its factor to 0.98, and then returned to its tracking position, so nothing else about the system changed.
>
> The test came out cleanly. The physics behaved as predicted, with RX2's Doppler following 2Fv/λ, and the pre-registered single-link comparison tied RX2 with RX3 at 23.33 %, so the stronger link identified no better than the weaker one and geometry is ruled out as the limit. Trained with the other Room B day's identification walks, the model reached 36.67 % across days on those walks, against 38.33 % for the stopwatch alone on the same walks, level with it at -1.67 points [-22.78, +13.89]. What does limit identification is the day itself. Within a day the model recognises each recording almost perfectly, at 91.67 to 98.61 %, against only 20.28 % across days, and each person's walking speed shifts between days by about as much as it differs between people. Identification is then presented as a working real-time subsystem with a limit that was investigated and explained. That answers the brief's call to detail robustness against environmental change and is exactly the investigation GA4 asks for. On the identification walks it still offers a real capability, a top-2 accuracy of 61.11 % and 75.56 % for a household of two, and it leads to a clear recommendation: record each person in several separated blocks per day, over more days, with more people.

**Sentences the figures contradict or overstate, each with a fix:**

1. **"at a small, measured cost for a new room"** holds for the committed line (7.50 [2.50, 13.33]) but not the lock, where one day of Room B data is worth 14.17 points [6.67, 21.67] (71.67 against 57.50). Fix: "at a small, measured cost for a new room on the committed line, though a larger one on the lock".
2. **"zero-shot in the other room at 29.17 %, against a chance of 16.67 %"**: its interval, 10.00 to 50.00 %, includes chance. Fix: add "though its interval includes chance".
3. **"identifies people across days at 32.08 %"** holds pooled (the interval [25.83, 43.33] excludes chance), but it comes from B2 at 40.00 %, whilst A3 alone is 24.17 % [15.83, 32.50], which includes chance and sits below the stopwatch's 39.17. Fix, if you want the split visible: "at 32.08 % (40.00 % on B2, 24.17 % on A3)".
4. **"geometry is ruled out as the limit"**: the single-link test had 30 test walks and both links' intervals include chance. Fix: "the main limit".
5. **"leaves most walking lines with weak or changing Doppler"** sits beside 3.5's "every line except A keeps a usable bistatic factor on its best link (0.53 to 0.70)". Both are true, since the factor changes along each line. Fix: say so in one of the two places.
6. **"Within a day the model recognises each recording almost perfectly, at 91.67 to 98.61 %"**: that figure comes from the amplitude levels alone, which carry no gait, in Room A, not from the engine. Fix: "Within a day the amplitude levels alone, which carry no gait, recognise each Room A recording at 91.67 to 98.61 %".
7. **"a working real-time subsystem"**: on the GPU it met its cap on 297 of 299 walks, its memory grew by about 2 GB an hour, and on the CPU it fails (10 of 171). Fix: "a working real-time subsystem on the GPU, meeting its decision cap on 297 of 299 walks".
8. **"a real capability, a top-2 accuracy of 61.11 % and 75.56 % for a household of two"**: the stopwatch ranks slightly better on both (67.78 and 76.78). Fix: "against chance levels of 33.33 and 50 %, though a stopwatch timing both presses, which the system does not have, ranks slightly better".

Every other sentence holds against the Code. That covers: 97.50 and 92.50; the lock at press + 2.0 s; 90.00 zero-shot; +7.50 committed; RX2's factor 0.981; Spearman 0.744 against 0.276; the 23.33 % tie; the stopwatch's 38.33; 20.28 % across days; and the speed shift, a mean 0.057 m/s against gaps of 0.006 to 0.165 m/s between neighbouring people.

## 4. The Editor's work (Chapter 3, report repository, nothing committed)

The Editor's own record is `../BLLUZA001_Final_Year_Report/REPORT_methodology_final_2026-10-11.md`, sections 1 to 6. I reviewed every changed number and claim against the Code over rounds 1 to 4. Chapter 3 was marked clean at 14:32, and the build is clean (only the five old 0.15 pt longtable boxes).

**The change log, in brief.**
- **The 10 Oct framing pass closed.** All 23 `% VERIFY v5 build` markers are closed, and every v5 number equalled the ship report, so none changed. "A median 0.41 s after the walker's end press" is filled in from `eval_v5.json`. `fig:id-confusion` is drawn as a TikZ heat map in PA order (diagonal 66 of 180, which is 36.67 %).
- **Factual fixes in 3.1 to 3.5:**
  - the system figure's identity hand-off is removed, since the app runs one task at a time;
  - the dwell ablation is dated 6 Oct, after Room B, and counted as a look;
  - lines A and B had only 0.20 to 0.25 m of run-up, because a node stands 0.5 m outside the grid on each;
  - the "ten-minute empty-room recording" is deleted, because none exists (set to 600 s, recorded 170.6 s);
  - "until 8 October" became "until 9 October";
  - "in version 4 the alternatives" became "in versions 2 and 4";
  - "an engine without it" became "version 4 without it";
  - the engine figure's "ends early" note is corrected;
  - the clean display's glide sentence is added.
- **3.5:** a new paragraph says the engine runs on the GPU and adapts after each decision is written and shown, which changes the timing, never a decision (evidence da199808).
- **3.6, written in full:**
  - one model per task, which is the live app, with its inputs and screens;
  - every figure is a replay;
  - the rig run;
  - tracking latency;
  - identification on the GPU: a median 1.08 s and at most 1.45 s after t0 + 4.0 s, 297 of 299 within the cap at t0 + 5.30 s, 299 of 299 exact;
  - the CPU finding, with "measured with the calibration still before the decision".
- **3.7, written in full:**
  - splits by whole session, and one question on one split;
  - a complete `tab:partitions`;
  - the development rotations and test looks (A3 seven and B2 five by the records, eight and six with the dwell ablation, flagged), and identification chosen among about 1,540 configurations;
  - the recording-block confound and the 29 Sep reader leakage;
  - the metrics;
  - tracking's bootstrap as a new equation, `eq:ci-track`;
  - the controls;
  - the geometry test and the day diagnostics as methods;
  - the pre-registration history.
- **Appendix A:** a new `tab:test-looks`.
- **Results:** only the VERIFY items, all equal, plus the ship report's date and the v4 figures' evidence.

**Its "flagged, not changed" list, in full,** with where each stands now:

1. `tracking_arch.tex` was not checked, because its read was blocked. **Closed:** I read it, and there is no old setting and no display head.
2. Two v4 figures in Results 4.4 ("by 5.00 points", "8.33 points [-15.83, -1.67] in version 4") were not checked. **Closed:** both are right (`eval_xroom_v4.json`, table2).
3. **Open, yours.** The two Doppler predictions disagree: 3.5.1 has 18.75 Hz measured "within one bin of the 19.5 Hz predicted" (teaching notes), while Results 4.4 has "18.75 Hz against 19.73 Hz predicted" (`findings-id29.txt:35`). The suggested fix is to use one, or say which speeds each uses.
4. My "DC2's two separated blocks per participant" was wrong, so the Editor didn't use it. **Closed:** the day design was one block per person per day.
5. My "identification v4, 30 Sep (mps, 1x, 299 of 299)" was wrong (it was engine v2 at maximum speed). **Closed:** 3.6 cites v5's own 299 of 299.
6. **Open, yours.** "Room B was no longer available" comes only from your brief, and no Code file says it.
7. **Open, out of the Editor's scope.** Results is stale on the clean display: `Results.tex:122`, the `tab:tracking-dot` rows and footnote, the zero-shot lock 56.67 to 57.50, the gain +15.00 to +14.17, and section 4.5's "shipped display", the `renders_K1g_0p5` folder, the dot ranges and the "worth watching" picks. Section 2 of the clean display report gives every replacement.
8. The midpoint check's date was not in the record. **Closed:** it was 29 Sep, so "by 29 September" stands.
9. **Open, yours to word.** 3.7 now discloses that tracking's walk bootstrap treats one person's walks as independent. That is true of the code.
10. **Open.** 3.3's "Each day began with mounting and photographing the nodes" was not verified.
11. **Open.** `appendixa.tex:139`, "shrinking with each seed set" (an older flag), was not checked.
12. **Open.** The handoff's flags on other chapters still stand: Introduction 69 and 91, Literature 539 and 556, Discussion 51, 60 and 223, and Recommendations 13.
13. The storage manifest did not exist when the Editor looked. **Closed:** it exists now (`runs/identify/v5/STORAGE.md`, d63c2df7).

Two further notes from the Editor:
- **Page budget:** Chapter 3 is 27.00 pages against 16.25 (8.75 over before this job). The body is 49.00 of 50, because other chapters are under. The Editor moved only its own detail, the test-looks table, to Appendix A, and left the cuts of your text to you. The candidates on record are the 3.4 and 3.5 conditioning detail, the stand photos, the slot order, and the 3.7 controls and day-diagnostic paragraphs.
- **Privacy:** sections 6 of both ship reports print the code-to-name key. The Editor stays out of those parts under your standing rule and copied no name.

## 5. What is left for you

1. **Copy the 40 v5 pickles to Drive** (5.78 GB): the steps are in `runs/identify/v5/STORAGE.md`, and the hashes in `STORAGE.sha256` let you check the copy. Until then they exist only on this laptop, though `iv5_train` rebuilds them exactly.
2. **The Discussion's v4 figures** (one walk, round trip, three and five walks, one press against two) go to v5's values: section 6 of `reports/identification/2026-10-11_engine-v5.md`, or the multi-walk table in section 2.2 above.
3. **The Results tracking values the clean display changed:** section 2 of `reports/tracking/2026-10-10_clean_display_report_update.md` (Editor flag 7). You've started Editor 2 for the Results, so it may carry these.
4. **Your framing's eight flags** (section 3): which fixes to take.
5. **The Editor's open flags** 3, 6, 9, 10, 11 and 12 (section 4), and the **page budget**: Chapter 3 is 10.75 pages over.
6. **The two failures of the confirmation run**, for how the thesis words them:
   - 297 of 299 decisions met the cap, with the two misses at 0.001 s and 0.153 s;
   - the GPU process's memory grew about 2 GB an hour. For a session of several hours that would approach the 12 GB limit, and a long live demo should be restarted between blocks or checked first.
   - On the CPU, identification is not real time, and the shipped arrangement (calibration after the decision) was never timed there.
7. **Caffeinate PID 8616 is still on** at your word. Tell me when to stop it.
8. **Still deferred from earlier handoffs:**
   - the Room A rename (session_01 to 03 as A1 to A3; 38 pinned files and 108 hash-list lines depend on the old paths);
   - the f05r rotation cells registered in memory only (writing them into `stage_cells.json` needs a plan and a re-hash);
   - the teaching material, which is yours to update.
