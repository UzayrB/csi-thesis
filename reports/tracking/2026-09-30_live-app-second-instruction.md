# The live app, second instruction: the report. 30 September 2026

**The brief,** verbatim: `reports/BRIEF_LIVE_APP_2_2026-09-30.md` (received 15:24). The queue is in `QUEUE.md`.

**Scope** (Uzayr, 15:58): this report covers items 0 to 6 and 8. The unconstrained mode (item 7) belongs to
the morning's instruction, and its figures are in `reports/LIVE_APP_MODEL_2026-09-30.md`, section 7.

**The standing changes (item 0):**
- **Names:** participant names are used freely from now on, and existing P-codes are left as they are.
- **The rig run:** it is the app fed recorded B2 data, streamed as if live, through the boards' own
  ingestion path (item 5). There are no boards and no new recordings. The boards' path is unchanged.

## 1. A3's design exposure (text and code reading; no figure changed)

### 1a. Does the committed decode read the soft entry or the 1.0 m entry window?

**Not directly. Only through the exit,** which sets the right end of the interval the committed line is
scored over.

**Where the entry prior is built:**
- `night_arms.py:283`: `st_lo = entry_start(o["entry"], ...)`. The soft entry is the first window's own
  emission on the line states.
- `night_arms.py:298-306`: states further than 1.0 m along each line are set to -inf.

**How it reaches the exit:**
- `night_arms.py:352`: `st_lo` seeds the forward recursion of the causal exit.
- `night_arms.py:359`: `end_i = causal_end(...)`.
- `night_arms.py:428`: `sl = slice(lo_dec, end_i + 1)`.

**The committed line never reads it:**
- `night_arms.py:569-581`: the committed line is `pick_line(chain_totals(e_res, st, sl, ...), family_first)`.
- `chain_totals` (`night_arms.py:145`) runs a Viterbi within each line with NO start prior. That is a
  uniform start over the whole line, neither soft nor limited to 1.0 m.
- The interval's start `lo` does not depend on the entry.
- The one branch that would read `st_lo` for the line (`night_arms.py:593`) is unreachable, because the
  exit is always after `lo`.

**Where it does matter directly:**
- **The lock:** the free display path `fixed_lag_path(..., st_lo, ...)` reads it.
- **The dot:** the drawn path `locked_chain_path(..., log_start=st_lo)` reads it, and so does the switching
  scorer's own soft 1.0 m start (`switching.py:104-114`).

The offline decode and the app use the same settings (`pd_decode.py:517, 532`; `live/tracking.py:47`).

### 1b. The choices still in the model that were selected or shipped on folds with A3 on the test side

**Traced from git and the pre-registrations.** The trace was made by a read-only agent and spot-checked:
- soft entry's ship rule (`e26f4cb`, `r2_softentry.py`: non-inferiority over the nine cross-day pairings);
- `normalise` (`8ca8cac`, `rb2_decoder.py` stage 2.4: "decided on the test-side single arm");
- the night arms' survivor rule (`n2_arms.py:237-240`: a point estimate over `pairings()`);
- the pool's equal weights (`g3_final.py:1-10`).

**What "the nine pairings" means:** the Room A cross-day folds. A3 (session 03) is on the test side in three
of them: 01->03, 02->03 and 0102->03.

| # | choice | value | decided | on folds with A3 as the test? | affects |
|---|---|---|---|---|---|
| 1 | soft entry | the first window's emission on line states | `e26f4cb` (20 Sep), `r2_softentry`: non-inferiority over the nine pairings. The opening figure was measured on 0102->03 only | **yes** | committed (through the exit only); lock; dot |
| 2 | 1.0 m entry window | 5 states per line | `0ca7ca6` / `3834d7f` (20 Sep), `q4_arms` arm A1: shipped on its paired interval over the seven held-out folds | **yes** | committed (exit); lock; dot, and the switch scorer |
| 3 | family-first | on | the night batch (`0a353c9`, 19 Sep), n2/n3 arms over the nine pairings | **yes** | committed |
| 4 | chain prior | log(n_line / n_total) - log(1/12) from the training sessions' pass counts | its use and form: night arm I, prompted by a test-side family bias over the nine pairings. Its values are fitted on training sessions | **yes** (use and form); no (values) | committed |
| 5 | the final rule | chain totals ("maxlik"), not the majority | night arm G, prompted by 0102->03 (80.0 against 71.7); n2 over the nine pairings | **yes** | committed |
| 6 | causal exit | the first window whose forward argmax is a null state | `d6f4464` (20 Sep): a correctness fix, adopted although the headline fell | no | committed (interval end); where the frames end |
| 7 | pooling the five heads | the equal-weight log-opinion pool | `3073eb2` (19 Sep): pooling adopted on the nine pairings. The weights and "every head" were fixed in advance | **yes** (to pool); no (the weights) | committed, lock, dot |
| 8 | which heads, and g100 | half, three 1 s seeds, g100 | joined by the "every head" rule on the nine pairings | **yes** (the recipe); the retraining on A1+A2+B1 is clean | all |
| 9 | stride | 0.5 s | a requirement (17 Sep), then evaluated on the nine pairings | **yes, in part** | all |
| 10 | window | 2 s | kept after a probe on 0102->03 only; its origin cannot be traced | **yes** (keeping it) | all |
| 11 | the press-aligned lattice | one window starts on each press | a correctness fix (23 Sep), not chosen on results | no | all |
| 12 | margin | 2.0 | `8ca8cac` (`rb2`): the training side of 0102->03 (A1+A2) | no (the value). **Yes** for using 0102->03's configuration everywhere | committed (exit); lock; dot |
| 13 | null_self 0.8, exit_k 1, the bout log odds | | `rb2`, training side (A1+A2) | no | committed (exit); lock; dot |
| 14 | exit_p 0.5, clock_max 8, abort_cost 60, "tight", lam 1.0 | | Config defaults, never swept; their origin cannot be traced | cannot trace; treated as **exposed**, as DISPLAY_PREREG treats an untraceable setting | committed (exit); lock; dot |
| 15 | the HMM's structure (veto, split, geometry, late entry) | on | the decoder rebuild brief; accepted on the nine pairings (stage 2.6; operator override O1) | **yes** (the acceptance) | committed (exit); lock; dot |
| 16 | `normalise` | False | `rb2` stage 2.4: decided on each pairing's TEST-side arm, A3 for 0102->03 | **yes** | committed (exit); lock |
| 17 | the semi-bounded structure | the committed line rescored over [lo, exit] | `c04684b` (18 Sep), the nine pairings | **yes** | committed |
| 18 | no speed ceiling on the decision decode | | `3834d7f`: the 3 m/s ceiling cost -7.50 on the nine pairings | **yes** | committed |
| 19 | the A2 start term | a region term on the chain totals | the part-2 pre-registration; q3 folds (one is 01+02 -> 03) and q4's seven held-out folds. The current weight of 0.25 was chosen on the rotations (clean) | **yes** (the term); no (the weight) | committed; the switch |
| 20 | the abstain term | threshold 0.90, weight 0.25 | threshold on 01->02 and 02->01; adopted on the rotations. Why 0.25 and not 0.5 cannot be traced | no (threshold); cannot trace (weight) | committed; the switch |
| 21 | emission scaling | "scaled", alpha 1.0 | `f3e9d4f`: the training sides of all pairings (A3 only as training data) | no | all |
| 22 | display settings (cap, spread, phase, switching, prior, head, anchor) | | `reports/DISPLAY_PROVENANCE_2026-09-30.md` | cap cleared; the rest **yes** | lock, dot |
| 23 | null rule, the 0.431 threshold, relgateU, the pace | | `TRACKING_CHECKS_2026-09-29.md`; the rotations; the pace recomputed on A1+A2 | no | all |

**What cannot be traced:**
- the origin of the 2 s window and of the Config defaults (row 14);
- the script that wrote q4's "selection fold" keys;
- why the abstain weight is 0.25.

**Also:** the night brief asks for survivors "outside the interval", but `n2_arms.py` uses a point
estimate.

### 1c. The A3 sentence, for the A3 row of every table

> **A3: clean in weights and fitted statistics, exposed in design choices.** Every network, reader and
> fitted statistic was trained without A3, but A3 was a held-out fold during Room A development. The entry
> rule, family-first, the chain prior's form, pooling the heads, the 0.5 s stride, the HMM's structure and
> most display settings were chosen on results that included it. **B2 is the headline: it is the only
> test session no design choice saw.**

## 2. The identity hook

**What the tag is.** Identification's one-press engine writes one JSON line per decision
(`reports/ID_LIVE_INTERFACE.md`, schema `id_engine_decision_v1`). The interface is written for tracking to
follow the file.

**How the tracking app now takes it: through ONE setter, `TrackingSession.identity(line)`.**
- **Who reads it:** only the screen. `screen_state` shows "who: <top> p <probability>" beside the walk
  whose press matches the line's press (within 1.0 s), once the line's decision time has passed.
- **How the harness feeds it:** `app_replay` hands each line to the app at its decision time
  (`replay_inner(identity=...)`), as the live app would follow the file.
- **The entry point's hook** (Identification's three lines, `63987d1`) routes only `replay-identify
  --session` and `rig ... identify` to the engine.

**Static** (`tests/test_live_truth_isolation.py`, 6 pass, 1 slow skipped):
- `test_identity_tag_is_read_only_by_the_screen`: in every tracking module the identity lines are read only
  inside `identity`, `_identity_for` and `screen_state`;
- `test_no_tracking_module_imports_identification`: no tracking module imports `pipeline.identify`, the
  engine or the old identify mode. Identification's own class in `rig.py` and the old gate suite are its
  side;
- `test_the_hook_routes_only_identification_commands`.

**Dynamic** (`tests/_identity_isolation_run.py`; `runs/live/identity_check/`, 20:56 to 21:25).
- **The runs:** B2, PA5, replayed three times with the screen drawn every frame, so the one function that
  reads the tag runs throughout.
- **The three tags:** present, absent and scrambled.
- **What the tags are:** synthetic, in the interface's schema, one per walk at its press and decided 3.5 s
  later. The test is about the tag's path, not its content.

| run | the app's log (every dot, lock, committed line, switch) | the screen |
|---|---|---|
| present | sha256 `7507bac6...` | shows "who: P1  p 0.4" beside walk 1 |
| absent | sha256 `7507bac6...` | no "who" line |
| scrambled | sha256 `7507bac6...` | shows the scrambled codes |

**The logs are byte-identical; the screens differ** (287 pixels at 9 s between present and absent). The tag
reaches the screen and nothing else.


## 3. The dot leaves the entry with the walker

### 3a. The diagnosis

**The rule** was written and hashed before any candidate run: `runs/dc2_results/rule/DOT_PREREG.md`
(`26b41a5b`).

**Why the first decoded positions sit at the entry.**
- **How each step is drawn:** each step after the lock is the ENDPOINT of its own Viterbi within the locked
  line (`render_display.locked_chain_path`, called from `night_arms.py:513, 545`). It runs over the windows
  up to that step and no further (evidence lag 0), from the soft entry restricted to the line's first
  1.0 m.
- **Why that holds the dot at the entry:** the first steps' windows are centred at and just after the press,
  and half their radio is the standing before it. So their endpoints stay at the entry. The tight chain
  then lets them advance by at most 0.8 m per 0.5 s.
- **Why it then races:** consecutive endpoints come from DIFFERENT Viterbis. When new radio re-routes the
  best path, the next endpoint lands far ahead.

In the teaching pack's B2 pass 2 (C_fwd) the drawn dot:
- holds at the entry until scene 0.84 s;
- moves at 1.0 to 1.5 m/s while 1.2 to 1.3 m behind;
- jumps at 3.5 m/s between scene 1.9 and 2.4 s. That is faster than any single decoded step allows, so it is
  two endpoints of different Viterbis.

**The slack between the radio a frame reads and the radio that has arrived by its time.**
- **Where a frame sits:** a frame at video time x draws step i (with `SHIFT_W` 0.5 and head offset
  0.375 s), with x between P + 2.375 + 0.5 i and P + 2.875 + 0.5 i, where P is the press.
- **What it reads:** step i reads radio that ends at P + 1.0 + 0.5 i.
- **So:** every frame reads radio that ended 1.375 to 1.875 s before it is shown.
- **Measured** on the K0 replays (`margin_s`, logged per walk): a minimum of 1.375 s, the lower end.
- **The old renders' 1.4 s** is the same slack.

**So the display could read up to about 1.4 s more radio and still be causal.**
- **Two more windows** (1.0 s) keep every decoded frame's margin at 0.375 s or more, above the stream's
  cutting delay (at most 0.15 s).
- **Three would not:** the margin would be -0.125 s.

### 3b. The candidates (display only)

**The five candidates:**
- **K0:** the current display.
- **K1 and K2:** the drawn path looks 1 or 2 windows ahead within the locked line.
- **K1g and K2g:** the same, with the anchor span (0.625 s) gliding from the entry to the first decoded
  frame's position, instead of holding.

**How it is built.**
- **The look-ahead** wraps the pinned `locked_chain_path` for the display's own compositions only
  (`night_track` imports it at call time), so the lock (the free path) and every decision are untouched.
- **The glide** reads step 0 alone, whose radio ends at or before the first glide frame.

**Not a candidate:** starting the display decode from later windows. The lock is read from that decode,
and no lock may change.

**The code:** `display.DISPLAY_CANDIDATES`, `LiveDisplay._compose` (the wrapper), `compose_walk` (the glide
and the per-frame margin), `app_replay --display`.

**No pinned file was edited.**

### 3c. The choice, on the rotations only

**The runs:** the five candidates on the three rotations' 18 evaluated recordings, through the app (semi
mode, the causal clock), 90 replays from 18:06 to 20:53 (`runs/dc2_results/dot_chain.sh`). The rule was
applied by `app_score.choose_dot`, and the result is in `runs/dc2_results/display/DOT_CHOICE.json`.

**The figures:** correct-lock walks, every frame from the press (the anchor span included). Median error in
metres / share of frames with the dot ahead / % within 0.5 m. The weighting is B1 x2, A2 x1, A1 x1.

| candidate | B1 | A2 | A1 | **weighted error** | **weighted ahead share** | minimum margin |
|---|---|---|---|---|---|---|
| K0 (the current display) | 0.336 / 0.376 / 68.5 | 0.368 / 0.293 / 63.5 | 0.366 / 0.211 / 61.0 | **0.351** | **0.314** | 1.375 s |
| K1 (look-ahead 1) | 0.309 / 0.378 / 71.4 | 0.350 / 0.307 / 67.3 | 0.355 / 0.221 / 66.3 | 0.331 | 0.321 | 0.875 s |
| K2 (look-ahead 2) | 0.273 / 0.414 / 76.0 | 0.329 / 0.325 / 71.6 | 0.337 / 0.225 / 70.1 | 0.303 | 0.345 | 0.375 s |
| K1g (look-ahead 1, glide) | 0.264 / 0.388 / 76.4 | 0.321 / 0.307 / 71.4 | 0.319 / 0.221 / 70.8 | 0.292 | 0.326 | 0.500 s |
| K2g (look-ahead 2, glide) | 0.233 / 0.424 / 81.2 | 0.292 / 0.325 / 76.2 | 0.301 / 0.225 / 75.2 | 0.265 | 0.350 | 0.0 s |

**What holds for every candidate:**
- its locks and committed lines equal K0's on all 360 walks;
- its margin is at least 0, so no frame reads radio after its own time.

K2g's margin of 0 is the glide's first moving frame, which reads step 0, whose radio ends exactly at
press + 2.0 s.

**The choice, by the pre-registered rule: K0, no change.**
- **Every candidate lowers the error** (K2g by 0.086 m, a quarter).
- **But every one raises the share of frames with the dot ahead,** by 0.7 (K1) to 3.6 (K2g) points.
- **The rule** (the brief's "without increasing the share of frames where the dot is ahead of the truth")
  admits none of them.

The rule was hashed before any run and is binding, so nothing is adopted.

**This needs Uzayr's decision:** whether a small rise in the dot running ahead is acceptable for a large fall
in the error. Two examples:
- **K1g:** -17 % error for +1.2 points ahead.
- **K2g:** -25 % error for +3.6 points ahead.

Adopting one would be a new choice made after seeing these development figures. Its G2 rerun and the test
replays would then follow as item 3d describes.


### 3d. The test sessions, once, with the chosen display

**The runs** (`runs/dc2_results/dot_3d_chain.sh`, 20:55 to 22:08). The rule chose K0, the display of the
committed renders, so this is run once as a check on today's code changes:
- the identity overlay;
- the candidate machinery;
- the margin logging;
- the stream mode.

**G2 again** (semi, the whole-file clock):

| cell | committed | locks |
|---|---|---|
| A3 (final) | 120 / 120 | 120 / 120 |
| B2 (final) | 120 / 120 | 120 / 120 |
| B2 (zero-shot) | 120 / 120 | 120 / 120 |

All exact.

**The replays** (the causal clock), semi and fully constrained on A3, B2 and zero-shot B2: 36 recordings
(`runs/live/replay/<model>/{semi,full}_disp-K0_causal/`).
- **Every log is byte-identical** to its committed counterpart, the only difference being the new per-walk
  `margin` rows.
- **The renders:** they were made from those same logs, so the 12 videos (`runs/live/renders/`) stand and
  were not remade.

**The dot error, old and new side by side.** Correct-lock walks. "From the press" counts every frame from
the press, the anchor span included. "Anchor-excluded" is the old figure, from the first decoded position
on. Each cell gives the median / p90 in metres / % within 0.5 m.

| test | mode | old = new, from the press | the old anchor-excluded figure | ahead share (from the press) | minimum margin |
|---|---|---|---|---|---|
| B2 final | semi | 0.336 / 0.94 / 64.4 | 0.319 / 0.98 / 65.0 | 0.321 | 1.376 s |
| A3 final (optimistic) | semi | 0.406 / 0.96 / 59.0 | 0.406 / 0.99 / 58.5 | 0.275 | 1.375 s |
| B2 zero-shot | semi | 0.421 / 1.20 / 56.2 | 0.422 / 1.26 / 55.4 | 0.246 | 1.376 s |
| B2 final | full | 0.330 / 0.94 / 64.9 | 0.314 / 0.98 / 65.6 | 0.333 | 1.376 s |
| A3 final (optimistic) | full | 0.401 / 0.96 / 59.5 | 0.401 / 0.98 / 59.2 | 0.289 | 1.375 s |
| B2 zero-shot | full | 0.409 / 1.19 / 57.0 | 0.405 / 1.25 / 56.4 | 0.265 | 1.376 s |

**"Old" and "new" are the same display (K0), so they are equal.** Counted from the press, the error is
about 0.02 m higher on B2, because the held anchor span is included. On A3 and zero-shot B2 it is within
0.01 m.

**If a candidate is adopted** (the decision in 3c), this step is rerun with it and the 12 videos remade.



## 4. The first walk of a session

**The measurement first** (`pipeline/live/press_profile.py`; `runs/live/press_profile/B2__participant_PA5_walk.json`).
The run is B2, PA5, the first three presses, at 18:07 with the candidate replays running (a loaded
machine).

| press | total | the stream's re-cut | windows re-cut | heads on the walk's re-cut windows | features on older windows | the statistics | AdaBN |
|---|---|---|---|---|---|---|---|
| 1st | 3.14 s | 0.67 s | 29 | 1.66 s (9 windows) | 0.10 s (20) | 0.015 s | 0.69 s |
| 2nd | 2.69 s | 0.30 s | 8 | 2.39 s (8) | none | none | none |
| 3rd | 2.49 s | 0.30 s | 7 | 2.19 s (7) | none | none | none |

**What it shows:**
- **The first press does not re-cut the whole recording.** It re-cuts the 29 windows the stream retains
  (`RETAIN_S` = 20 s). Later presses re-cut 7 to 8 (`RECUT_BACK_S` = 6 s).
- **The cut itself is the smaller part:** 0.67 s against 0.30 s.
- **What makes every press slow:** the five heads on the walk's re-cut windows.
- **What the first press adds:** AdaBN (0.69 s) and the extra 21 windows' re-cut (0.37 s).
- **On a quiet machine** (section 2.3 of LIVE_APP_MODEL) the same presses take 0.83 to 0.95 s median, and
  up to 3.2 s for a first press.

**Why an incremental first cut cannot keep every output byte-identical:**
- **What the first press fixes:** the recording's statistics (the relative RSSI, the gate) and AdaBN.
- **Where they come from:** the idle windows before it, cut on ITS phase (`FinalTrackingSession.
  _final_stats`, `_adapt`). That is what the offline tree did, and what G1 and G2 reproduce.
- **Why the work can't be done earlier:** the phase is the press's own time, so those windows cannot be
  cut before the press.
- **The heads can't be cut either:** the heads on the walk's own re-cut windows are needed by the lock at
  press + 2.0 s at every press.

So no rearrangement that keeps the outputs identical removes more than scheduling.

**Nothing was changed. This needs Uzayr's decision.** The options that would help all change outputs
slightly, and would need the gates rerun:
- (a) fix the statistics and AdaBN on the base lattice's idle windows before the press, cut incrementally,
  which removes the first press's extra 1.1 s;
- (b) run the five heads on a press's re-cut windows as one batch, which changes the float32 results in
  their last bits;
- (c) keep the app as it is, and state the first walk's lock delay (up to about 1.2 s on a quiet machine).


## 5. The streamed B2 run (the "rig run")

### 5a. The stream mode

`python3 -m pipeline.live rig --stream B2/<stem> [--screen <folder>]`, in `pipeline/live/stream_source.py`,
routed from `pipeline/live/__main__.py`.

**Only the packet source is replaced.**
- **The stand-in:** a stand-in `serial` module is registered before `run_capture` opens its ports. Its
  ports replay each receiver: every recorded frame is written back as the firmware's base64 `CSI_DATA`
  row, and released at its recorded pace in wall-clock time.
- **Unchanged from there on:**
  - `run_capture`, its per-receiver `SerialReader` threads (stamping on the host clock), `parse_line` and the
    queue;
  - the rate monitor and the config watch;
  - the rig's `TrackingConsumer`: the causal anchor, the final model in semi mode, the screen.
- **The capture writer** writes what the app received, as a plugged-in run does.
- **Nothing under `pipeline/io/` was edited.**

**The keys:** each walk's first press is injected as a SPACE `KeyEvent` at its recorded time, stamped when
injected.

**Every difference from a plugged-in run, other than the packet source:**
1. the key source: an injector thread in place of the terminal key reader;
2. no board reset (the rig runs without one too);
3. the replay port emulates the serial read timeout;
4. the screen's truth overlay: replay-only, shifted onto the stream's clock;
5. the pre-flight's baseline age: judged against the recording's start (5c).

**One set-up fault, found and fixed on the first attempt (22:13).** The stream's clock started before
the replay ports had written the ~27,000 rows. So the rows then came out in a burst, and a press was
injected before any window existed, which stopped the run (`LiveStream._shift` on `None`). Now the ports
are built first, and the clock starts two seconds before the readers open.

### 5b. The boards' serial path, exercised with recorded packets

`tests/test_stream_serial_path.py`, 2 pass, with nothing under `pipeline/io/` edited.
- **Every frame round-trips:** each of a B2 recording's frames (RX1, PA5), written as a CSI_DATA row,
  parses back to the same metadata, the same 256 values and the same gain.
- **The real reader thread carries them:** a real `SerialReader` thread, given a port that returns those
  rows in 1,500-byte chunks (read boundaries mid-line), stamps, splits, parses and queues all 600, in
  order, identical to their frames.

### 5c. The pre-flight in stream mode

**It runs first, and refuses on any failure.**

**Its first run refused, correctly by its own rule:** each B2 baseline is 4,800 minutes old today.
- **The fix:** `preflight(baseline, at=...)`. In stream mode "recent" is judged against the recording's
  first packet, so it means what it meant when the recording was made. On the boards it is still judged
  against now.
- **On B2:** each recording's own baseline was taken 0.7 to 0.9 minutes before it, so every check passes.

### 5d. The streamed B2 run

**The run:** all six recordings, one after another, on a quiet machine (Identification paused by
agreement, 22:09 to 23:30). The screen was recorded (`runs/live/stream/stream_B2_<stem>.mp4`).

**Wall-clock measurements** (`runs/live/stream/B2__<stem>/summary.json`):

| recording | window service, median / p99 / max | lock frame late, median / p90 / max | committed line after the walk's end, median / p90 / max | frames late over 0.1 / 0.5 s (of) | press service, median / max | packets parsed, dropped |
|---|---|---|---|---|---|---|
| PA5 | 0.097 / 0.259 / 0.265 s | 0.13 / 0.16 / 0.71 s | 1.10 / 1.64 / 2.21 s | 310 / 120 (1,279) | 0.91 / 1.78 s | 162,899, 0 |
| PA1 | 0.097 / 0.259 / 0.283 | 0.13 / 0.16 / 1.01 | 1.06 / 1.52 / 2.19 | 282 / 118 (1,298) | 0.91 / 2.03 | 163,607, 0 |
| PA2 | 0.098 / 0.259 / 0.280 | 0.13 / 0.16 / 0.97 | 1.40 / 1.67 / 2.24 | 304 / 124 (1,287) | 0.92 / 2.03 | 157,258, 0 |
| PA3 | 0.098 / 0.259 / 0.268 | 0.13 / 0.16 / 1.31 | 1.49 / 1.72 / 2.18 | 300 / 123 (1,280) | 0.91 / 2.31 | 156,996, 0 |
| PA4 | 0.097 / 0.256 / 0.274 | 0.13 / 0.15 / 0.97 | 1.28 / 1.51 / 2.17 | 307 / 123 (1,339) | 0.91 / 2.03 | 162,256, 0 |
| PA6 | 0.096 / 0.256 / 0.267 | 0.13 / 0.16 / 2.13 | 1.21 / 2.11 / 2.76 | 337 / 147 (1,294) | 0.90 / 3.18 | 165,636, 0 |

**What it shows:**
- **Every packet was parsed, none dropped:** 968,652 in all. Every receiver PASSED the capture's own gates.
- **The app keeps up:** 0.1 s per 0.5 s window.
- **A typical lock** shows 0.13 s after its due time, the window's cutting delay.
- **The first walk's lock is late** by 0.7 to 2.1 s (item 4).
- **Frames late:** 24 % of frames are computed more than 0.1 s after their time and 10 % more than 0.5 s.
  They cluster at the presses, which block the app for 0.9 s (up to 3.2 s on a first press).
- **The screen:** it redraws in the same thread, and drew 14,835 times against about 21,900 ticks at
  10 per second (68 %). Busy moments skip redraws.
- **Where this points:** a second thread for the screen, or a cheaper press (item 4's options), would
  address both. **This needs Uzayr's decision.**

**Do the streamed outputs equal the replay logs?**
- **Against the replay of the same recording** (`runs/live/replay/final/semi_disp-K0_causal/`):
  - **committed lines:** 120 of 120 equal;
  - **locks:** 114 of 120 equal;
  - **dots:** median difference 0.00 m; up to 6.4 m on the walks whose lock differs.
- **Why they differ.** The stream stamps every packet and the injected press on the wall clock, as a live
  run does. So the press-phased windows' edges move by milliseconds, and six borderline locks flip. A replay
  of a recording and a live run of the same walks would differ in the same way.
- **The proof that this is the only difference.** Each stream wrote exactly what the app received (the
  capture writer the boards use, and the injected presses). That capture was replayed through the harness,
  and the outputs are identical to the stream's, row for row, on all six recordings (960 to 1,020 rows
  each, compared without the moments things were computed).
- **The one exception was a logging gap, now fixed:** a walk's first park frames written directly when a
  press lands on frames already drawn ahead (`_park_drawn_ahead`) were not logged. With the logger fixed
  (`app_replay.Logger`), the re-replay of PA4 logs every row the stream did, plus the 21 park frames the
  stream's own logger had missed.
- **The app is the same on the boards' ingestion path as in the replay harness.**

### 5e. The protocol

`reports/RIG_RUN_PROTOCOL_2026-09-30.md` (new; the 29 Sep protocol and its addendum stay as the record).
- **The demonstration:** the streamed run, with its commands, its pre-flight, what it writes, what to expect
  (measured) and every difference from a plugged-in run.
- **The plugged-in path:** the boards, unchanged, with one press per walk.


## 6. This morning's Part A, confirmed

| item | status | commit |
|---|---|---|
| The V2 record: pre-registered, nothing adopted, A3 and B2 not read (`reports/V2_DEVELOPMENT_2026-09-30.md`, `rule/V2_PREREG.md` and the results) | done | `b980cc9` (30 Sep 09:09) |
| The V2 future-work notes: option 4 and fixing the time-step units later (`reports/FUTURE_WORK_TRACKING.md`) | done | `8097d91` (09:11) |
| The time-step disclosure (`reports/DT_MISMATCH_2026-09-30.md`, `pd_dt.py`, the DT decodes: inert, 0 of 360 decisions) | done | `9a25fa7` (09:09) |
| The section 16 correction note in `reports/ARCHITECTURE_TRACKING_FINAL_2026-09-29.md` (the null rule on A1+A2; 0.431 on A1; neither saw A3) | done | `8097d91` |
| The pre-flight checks the trace-derived hash lists (`TRACE_HASHES_fin_A3/fin_B2`, 267 and 273 files). **Rerun on the app after the brief arrived (15:24): all nine checks ok**, both gates included | done | `8097d91` (code); the lists are in `9a25fa7` |
| `tools/teaching_pack.py` line 446 now reads "raw press times; the 41 to 51 ms reaction bias is not subtracted". The JSON is untouched | done | **not committed**: the file is the teaching chat's, and untracked |
| `tools/dc2_hardware_check.py` | untouched by tracking. It carries another session's working-tree edit, dated 25 Sep 09:05, which was never committed by us | none |

## 8. The teaching pack with the fixed dot

**The file:** `reports/teaching_pack_app_v2_2026-09-30.json` (45 KB, built 20:56 to 21:05). The morning's
`teaching_pack_app_2026-09-30.json` stays beside it.

**Who:** B2, PA2 (P5), passes 2 and 10, from the app. Names are now in the pack.

**The dot:** the display item 3's rule chose, K0: the current display, since no candidate was adopted. Every
frame's margin is recorded by the app.

**Plumbing:** the app's committed line and lock on all 20 of PA2's walks equal the corrected offline
decode, 20 of 20 each.

**With the start press** (the semi-constrained mode):

| pass | true line | lock | committed | decoded dot, median error |
|---|---|---|---|---|
| 2 | C_fwd | C_fwd (right) | C_fwd (right) | 0.27 m |
| 10 | C_fwd | E_col1 (wrong) | C_fwd (right) | 2.50 m (on the wrong line) |

**The unconstrained view: the same walks, as the app saw them with NO press** (m = 4, from
`runs/live/replay/final/unconstrained_m4_causal/`):

| pass | detected? | detected start against the true press | lock | committed | announced |
|---|---|---|---|---|---|
| 2 | yes (the app's walk 5) | +1.35 s | B_fwd (wrong) | C_fwd (right) | press + 5.97 s |
| 10 | yes (the app's walk 18) | +1.02 s | C_fwd (right) | C_fwd (right) | press + 7.12 s |

**What the pack holds:**
- each view's frames, 55 and 70, with the truth and the error;
- how late each frame was computed.

**What it shows:** without the press the start is found about a second late. That moves the lock's window,
which can flip the lock either way. Here it turns pass 2's right lock wrong and pass 10's wrong lock right.
The committed line, read at the causal exit from the whole walk, is right both times.


## Files and commits

**The code** (`pipeline/live/`):
- `stream_source.py` (new): the stream mode, the comparison and the capture re-replay.
- `press_profile.py` (new): item 4's measurement.
- `display.py`: the five dot candidates (the look-ahead wrapper, the glide, the per-frame margin). K0, the
  default, draws exactly as before.
- `final_model.py`:
  - `DISPLAY_CANDIDATE` (K0);
  - the `display_candidate` parameter;
  - `preflight(at=)`.
- `tracking.py` and `screen.py`: the screen-only identity overlay.
- `app_replay.py`:
  - the identity feed;
  - `--display`;
  - a capture folder as the source;
  - the per-walk margin rows;
  - the logger's park-frame fix.
- `app_score.py`: the from-press dot metric and `choose_dot`.
- `app_teaching.py`: v2 with the unconstrained view; names allowed.
- `__main__.py`: `rig --stream`.

**The tests:**
- `tests/test_live_truth_isolation.py` (the identity tests);
- `tests/_identity_isolation_run.py`;
- `tests/test_stream_serial_path.py`.

**The rules:** `runs/dc2_results/rule/DOT_PREREG.md` and its hash (`26b41a5b`, written before any
candidate run).

**The results:**
- **Item 3c:** `runs/dc2_results/display/DOT_CHOICE.json`; the candidate replays in
  `runs/live/replay/rot*/semi_disp-K*_causal/`.
- **Item 3d:** the checks in `runs/live/replay/{final,zeroshot}/{semi,full}_disp-K0_causal/`; G2 in
  `runs/live/final/gate_*_semi.json`.
- **Item 4:** `runs/live/press_profile/`.
- **Item 2:** `runs/live/identity_check/` (the three logs, the three screens, `RESULT.json`).
- **Item 5:** `runs/live/stream/`, holding:
  - per recording: `log.jsonl`, `summary.json`, the capture's sidecar and run file, and the re-replay;
  - the six screen recordings.
  The captured `.bin` files are git-ignored as data, and regenerable by streaming.

**The reports:**
- this report;
- `reports/BRIEF_LIVE_APP_2_2026-09-30.md` (the brief, verbatim);
- `reports/RIG_RUN_PROTOCOL_2026-09-30.md`;
- `reports/teaching_pack_app_v2_2026-09-30.json`.

**The chain scripts:** `runs/dc2_results/{brief2_after_U,dot_chain,dot_3d_chain,stream_chain}.sh`.

**The decisions this report leaves to Uzayr:**
1. **The dot (3c):** whether a small rise in the dot running ahead is acceptable for a large fall in its
   error (K1g: -17 % for +1.2 points; K2g: -25 % for +3.6).
2. **The first press (item 4):** options (a), (b) or (c).
3. **The rig's screen (5d):** a second thread for the screen, so busy moments stop skipping redraws.

