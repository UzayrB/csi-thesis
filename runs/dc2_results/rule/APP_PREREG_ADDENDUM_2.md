# APP_PREREG addendum 2: the unconstrained mode's details, fixed before its m grid. 30 September 2026

**Status.** Written and hashed before any unconstrained replay of a rotation's m grid, and before any
unconstrained replay of A3 or B2. `APP_PREREG.md` section 6 governs; this fixes what it left open. Its
SHA-256 is in `APP_PREREG_ADDENDUM_2.md.sha256`.

**Code:** `pipeline/live/unconstrained.py` (the session and the detector). The scoring is
`app_score.score_unconstrained`, `choose_m` and `match`.

## (a) The statistics, at S

**S = 12.891 s** (`runs/live/unconstrained/S.json`).
- **Where it comes from:** the 10th percentile, over the 18 training walk recordings (A1, A2, B1), of the
  first press minus the recording's first window start (the app's own stream) minus 3.0 s.
- **The windows it gives:** 22 lie wholly inside it, against a floor of 10.

**What is fixed at S,** once the first window ending after the recording's first window start + S
arrives, from the windows wholly inside [w0, w0 + S]:
- the per-link relative RSSI means;
- g_rec (the median band energy) and so the gate scale max(1, G0 / g_rec);
- AdaBN, on the same windows.

**From then on,** every window's rows carry the heads.

## (b) The detector

**The decoder:** the full-state decode: the path states, the still states and the transit states
(`decoder2.Space`).

**The display decode's settings:**
- **Configuration and cap:** the display's configuration at sd_scale 4.5, and its transition matrix built
  with the 0.80 m per window cap.
- **Emission and gate:** the pooled emission, the scaled gate energy, and the gate veto.

**The track:** `decoder2.provisional_track`'s rule, one window at a time. It is the lag-1 argmax of the
UN-collapsed forward belief, Stage 3's live track: when window t arrives, window t - 1's state is the one
on the best path ending at t. The first window's belief is its own emission.

**The null level's reference:** the running 0.75 quantile of the path peaks of every window so far. The
display calibrates on the windows it holds; here that set grows. (The pooled emission is normalised to a
maximum of 0 per window, so the reference is 0.)

**A first version, replaced before any m run or test replay.**
- **What it did:** it committed each window at lag 0 with binding commitments (`fixed_lag_viterbi`'s rule,
  the display free path's lag).
- **The result:** on one development recording (B1, P4; `rotB1`, m = 2) it never left the transit states
  in 712 windows: 0 detections for 20 walks. Its transit level sat 3.5 nats below the path peak on every
  walking window.
- **Why:** the display's own path starts each walk ON a line, through its start prior at the press. A
  continuous decode has no press, so entering a line's first state never won a single greedy step.
- **The revised track** on the same recording: 29 detected walks, 5 matched within 1.5 s, 24 false
  starts. The matched starts were 0.8 to 1.4 s before the press; walkers start a step or two before the
  tape.
- **Nothing else was changed after seeing it.**

**It consumes each window once, as it arrives,** from the recording's first window on (the windows inside
S are fed at S). It is never re-decoded when a start re-cuts the stream's lattice. After a start the
stream's windows are on that start's phase, still 0.5 s apart.

**The trigger:** m consecutive path states on the track.
- **The start time** is the centre of the first of them.
- **A start is taken only when:**
  - no walk is open, meaning every started walk's committed line has been announced;
  - the run began after the last walk's exit window centre.
- **One run gives at most one start.**
- **A run that reaches m while a walk is still open** gives its start once the walk closes, if the run is
  still going and began after that walk's exit.

**A detected start is the walk's start press,** given internally, exactly as a semi-constrained start
press:
- the stream re-cuts back 6.0 s before it;
- the lock is read at start + 2.0 s;
- the committed line comes at the causal exit;
- the frames end at the exit or at the next start.

**Its first window** is the first centred at or after the start, as for a press in real time.

**Frames drawn late.** A start is detected after it happened: with the track's lag of one window, m = 1
at start + 1.5 s plus the cutting delay, and each extra step adds 0.5 s. So the new walk's frames from the start to the frames already
drawn are drawn at detection. Their draw lag is reported. So the lock is composed at detection, from the
windows held then (for m = 1, 0.5 s after start + 2.0 s).

## Choosing m

**The runs:** m in {1, 2, 3, 4}, on the three rotations through the app (development sets `rotB1`, `rotA2`
and `rotA1`), with the causal clock.

**What varies with m:** the display head of those sets is the final one, trained on B1. It changes no
detection and no committed line, so the objective does not depend on it.

**The objective:** the share of true passes detected (matched within 1.5 s, one to one, nearest first)
AND committed correctly, weighted over the rotations: B1 x2, A2 x1, A1 x1.

**Selection:** the argmax; ties go to the smaller m. It is written to `runs/live/unconstrained/M.json`
before any A3 or B2 replay in this mode.

**The cache.** A content-addressed cache of window rows is on only in these runs. It keys each window on
its raw radio bytes and the recording's statistics, so a window cut from the same radio with the same
statistics is not recomputed. It changes no output.

## (c) The report

**Per test session (A3 and B2 on the final model, B2 on the zero-shot model):**
- the detection rate;
- false starts per minute of recording;
- the committed line and the lock on matched passes;
- correct-and-detected over all passes (the main figure);
- lock-correct-and-detected.

**The m grid's whole table** is reported beside the choice.
