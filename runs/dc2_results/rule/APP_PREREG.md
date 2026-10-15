# APP_PREREG: the live app as the one tracking model. Pre-registered 30 September 2026, 09:26 SAST

**Status.** Written before any A3 or B2 replay. Its SHA-256 is in `APP_PREREG.md.sha256`, and it is never edited
afterwards. Nothing in it is changed after any A3 or B2 figure is seen.

**What it implements:** Uzayr's message of 30 September (the one-model principle; parts B, C, E and F).

**Development replays already made** (development sessions only, never A3 or B2):
- the A1+A2 -> B1 rotation, through the app;
- a truth-isolation check on two B1 walks.

## 1. The principle

**The live app is the tracking model:** `pipeline/live/`, `final_model.py` and its runner.
- **Every figure comes from it:** every thesis figure, render and rig run.
- **Offline evaluation** is a replay of the recorded packets and presses through the app
  (`python3 -m pipeline.live replay`), scored by `pipeline.live.app_score`.
- **The old offline code** (pd_decode, pd_render, drawn_errors) is a cross-check only. If it and the app
  disagree on anything reported, stop and report.

**What stays frozen:** the 15:39 networks, readers, configuration and `FINAL_CONFIG.md` hash.

**New A3 and B2 figures** are measurements of that model, under the rules below.

## 2. The model sets

| set | cells | files | display head |
|---|---|---|---|
| final | fin_A3 (for A3) and fin_B2 (for B2), byte-identical networks | `final/TRACE_HASHES_fin_A3.txt` and `_fin_B2.txt`, checked before each replay | DISP_END final (`pd_dispend`, A1+A2+B1) |
| zero-shot | zsf_B2 (A1+A2 heads; the zsp readers; A1+A2 marginal, chain prior and G0; the frozen A1+A2 pace) | `final/TRACE_HASHES_zsf_B2.txt` | **DISP_END zero-shot** (`pd_dispend_zs`, A1+A2 only, the same recipe) |

**The new display head.** The zero-shot display head is trained before any replay of the zero-shot model.
- **Why:** the final one was trained on B1, which the zero-shot model may not read.
- **What it touches:** it is display-only, so it changes no lock or committed line.
- **Its manifest:** its file is hashed into the zero-shot model's manifest (`runs/live/models/zeroshot.json`),
  beside `final.json`.

## 3. The inputs, and the three modes

**In every mode,** the app is given the radio: every packet, CSI and RSSI, in arrival order. **It is never
given:**
- presses 2 to 6 of a walk;
- the walk's duration;
- labels;
- pace features;
- elapsed time.

**The ground truth** is read only by the scorer, and by the replay-only green overlay
(`TrackingSession.set_truth`). `tests/test_live_truth_isolation.py` proves the overlay cannot reach the
model.

| mode | presses | committed line | lock | a walk's drawn frames end |
|---|---|---|---|---|
| **SEMI-CONSTRAINED** (the headline) | ONE per walk: the sidecar's `t_start`, the raw key time of its first anchor | at the app's own causal exit | press + 2.0 s | at the causal exit (the scene time of the exit window's centre), or at the next start press, whichever is first |
| **UNCONSTRAINED** | none | as semi, after the app's own detected start (section 6) | detected start + 2.0 s | as semi |
| **FULLY CONSTRAINED** (an upper bound, never the headline) | start and end press (`t_end`) | rescored with the walk ending at the end press: per-line Viterbi totals over [lo, hi_end], hi_end = the last window whose centre is at or before the end press, with the chain prior and the start terms, family first (night_track's own final rescore) | unchanged from semi | at the end press |

**The twelve-line assumption holds in every mode.**

**Without an end press, the stream** re-cuts windows back 6.0 s before each start press, and back to the
recording's start at the first press (`stream.RECUT_BACK_S`). Where two walks are close, windows can
differ from the offline tree, which was cut with the end presses. Section 4's gates measure whether any
decision moves.

**The clock.** Every reported figure uses the as-it-arrives clock fit (`--clock causal`), as the rig must.
The whole-file clock fit (`--clock file`, the offline tree's) is used only in the equality gates.

## 4. The gates, before any figure is quoted

**Every gate** covers every evaluated pass of A3 (final model), B2 (final model) and B2 (zero-shot model),
120 each, checking the committed line and the display lock pass for pass. **If any pass differs, stop and
report.**

**G1, agreement.** The app in legacy mode (both presses, as the tree was cut, with the committed line at the
causal exit), with the whole-file clock, against the corrected offline decodes
(`cells/<cell>/d3/FC.relgateU+abstain+a2w0.25`).

**G2, the semi gate (Uzayr's).** The app in SEMI mode (the start press only), with the whole-file clock,
against the same corrected answers: A3 93.33 / 70.83, B2 93.33 / 72.50, zero-shot B2 80.00 / 49.17. **Its
only difference from G1 is the missing end press.**

**When the gates are rerun:** after every change to the app, before a figure is quoted.

**If G1 and G2 pass, the headline replays run:** semi mode, the causal clock. Any pass whose answer differs
from G2 is listed with its cause: that is the clock fit, the only remaining difference.

## 5. The scoring (`pipeline/live/app_score.py`, which reads the app's log and the labels)

**Which passes.** Every pass of every evaluated recording (calibration recordings excluded), 120 per
session.

**The accuracies:**
- **the lock:** the line the display locked at press + 2.0 s, against the true line;
- **the committed line:** the line the app announced (semi: at its causal exit; full: rescored at the end
  press). A pass never announced counts as wrong, and the count is reported.

Both are given with 95 percent bootstrap intervals over passes (1,000 draws, seed 0), with the edge lines
E_col1, E_col5, E_row1 and E_row5 beside them.

**The dot error.** Every drawn frame from the walk's first decoded position on, with the park and the rule
2a anchor segment excluded (rule 2b). Each is measured against the truth at frame time minus 2.0 s, the
scene moment the frame shows under V1. The truth is linearly interpolated between the pass's anchor
presses, as the labels are, on raw press times.
- **Reported:** the median and 90th percentile in metres, and the share within 0.5 m, over all walks and
  over the walks whose lock is correct.

**The display offset,** reported apart and never added to the dot error: the truth at frame time against
the truth at frame time minus 2.0 s.

**Coverage:** the share of each true walk's frames that carry a decoded dot.

**The announcement latency:** when the app announced the committed line, against the walk's last anchor
press (the median, the 90th percentile and the maximum).

**The per-window service time:** from the replay summaries. The latency figures quoted come from replays
run while no Identification job is running; those runs are flagged to Identification first.

## 6. The unconstrained mode: its design, fixed now, with its settings chosen on the rotations only

**(a) The recording's statistics without a press.** The relative RSSI means, g_rec and AdaBN come from the
windows lying wholly in the first S seconds of the recording.
- **S:** the 10th percentile, over the training sessions' walk recordings (A1, A2 and B1, calibration
  recordings excluded), of (the first start press minus the recording's first window start minus 3.0 s).
  In 9 recordings of 10 that span is still idle.
- **A floor:** at least 10 windows, or the recording is refused, as `MIN_IDLE_WINDOWS`.

**(b) A walk start.** The app runs the display decoder (the full-state fixed-lag decode, the frozen display
settings) continuously on the base 0.5 s lattice, with no re-cut.
- **The trigger:** a walk starts when the decoded state enters a line state and stays on a line for m
  consecutive decode steps.
- **The start time:** the centre of the first on-line window. It then acts as that walk's start press:
  the lock at start + 2.0 s, and the committed line at the causal exit.
- **When the next start may be detected:** only after the current walk's causal exit.
- **Choosing m:** m in {1, 2, 3, 4}, chosen on the rotations alone (A1+A2 -> B1 x2, A1+B1 -> A2,
  A2+B1 -> A1). The chosen m maximises the weighted share of passes detected and committed correctly;
  ties go to the smaller m.
- **Which decoder does the choosing:** the offline decoder may do it, but only after a replay gate shows
  it and the app agree on those rotations.

**(c) Matching.** A detected start matches a true pass when it lies within 1.5 s of the pass's true first
press. Matching is one to one, nearest first.
- **Reported:**
  - the detection rate (matched true passes over all true passes);
  - false starts per minute of recording;
  - line accuracy on the matched passes (the committed line and the lock);
  - **correct-and-detected over all passes** (its main figure).

**(d) If it cannot be built cleanly** under these rules, the report says how far it got. It is last in the
order, and its figures are appended to the report when they are ready.

## 7. The order (Uzayr, 30 Sep)

1. A.
2. B and D, in parallel: the display provenance, `rule/DISPLAY_PREREG.md`.
3. E: the renders, replayed through the app with its display on, at real-time pace.
4. The fully constrained mode.
5. F, the report, with what exists.
6. The unconstrained mode, last; appended when ready.

## 8. What is never done

- No figure is chosen between modes or settings on A3 or B2.
- Nothing in the model changes after an A3 or B2 replay.
- `data/` is never written.
- No network of the 15:39 model is retrained. The zero-shot display head is new, and display-only.
