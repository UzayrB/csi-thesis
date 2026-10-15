# Handoff: IDENTIFICATION after DC2, 2026-09-28 08:07 SAST

For a session or chat that picks up identification. Everything below was checked against the files
on disk at the time above. It supersedes `reports/HANDOFF_IDENTIFICATION_2026-09-26.md` for status,
but that file's rules and read-first list still hold. Re-check anything you act on.

**Update, 2026-09-28 08:48 SAST:** the three items under "In short" are settled. Addendum E is final at
`reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_E.md` (the draft name below is gone), the relabel and the
P1-REV and P7 scorer are frozen in `runs/IDENTIFICATION_FROZEN_2026-09-28.json`, and the work follows
`reports/BRIEF_ID_DC2_scoring_2026-09-28.md`.

## In short

- **DC2 capture is complete for identification.** Both days are on disk, 60 recordings, and both
  days' final checks say NOTHING WRONG.
- **Nothing has been scored.** No identification figure exists for Room B: there is no view
  (`runs/identify/dc2_view/`), and `runs/identify/dc2/` holds only `rx2_spot.json`.
- **Three things stand between the data and scoring:**
  1. the P1-REV and P7 scoring code, which is not written;
  2. addendum E, day 1 deviations, which is drafted but not approved;
  3. a decision on one mislabelled pass in participant P5's day 2 fast block.

## The model DC2 tests (frozen, never tuned on DC2)

**Room A background.** Room A identification is closed.
- Gait is at chance across days: the nested headline is 15.83 % [10.28, 21.67] against 16.67 %
  chance.
- Pace alone scored 36.1 % on `A_fwd` (exploratory), and no gait representation built here beats
  pace.
- The quotable figures are in `reports/ID_QUOTABLE_2026-09-23.md`.

**Configurations** (`reports/PREREG_ID_DC2_2026-09-23.md` and its addenda B, C, D):

| name | what | role |
|---|---|---|
| PRIMARY | `id19_featbank.pass_features`, U_all_gait set on the gait-band mean, 3 links; training-side median imputation and per-path z-scoring; random forest, 300 trees, `max_features` sqrt, `random_state` 0 | the result |
| SECONDARY | 2D CNN on Doppler spectrograms, seeds 0 to 4, five-seed ensemble, 60 epochs | post hoc |
| S0 | speed = 5.0 m / (last press - first press), shrinkage LDA | control, never a result |
| RECSIG | static levels (mean amplitude per subcarrier, mean RSSI), shrinkage LDA | recording-signature control |
| P1-GP (arm G) | gait without pace: rhythm at the fused cadence, per-link rhythm, geometry-corrected Doppler contours, envelope spectral shape; HistGradientBoosting (150 iterations, lr 0.05, depth 3); cadence margin 0 or 0.5 s chosen by day 1 ICC | added arm; Room A 22.22 % [8.33, 41.67] against S0's 36.11 % |

**Analyses, each scored once.** All train on day 1 natural `A_fwd` passes (10 per person) unless
stated. Statistics: accuracy, n, chance, a 95 % bootstrap over participants, and a permutation p.
- **P1 (THE result):** tested on day 2 natural (n = 30), with PRIMARY, SECONDARY and S0.
- **P2, geometry:** each link alone, full length and a fixed 2 s crop. Prediction on the crop:
  TX-RX2 > TX-RX3 > TX-RX1, with TX-RX1 near chance.
- **P3, pace:** tested on day 2 slow and fast. The drop from natural is compared with S0's drop.
- **P4, placement control:** empty rooms at the spot, day 1 to day 2. The home rows are information
  for tracking.
- **P5, controls:** recording signature, and a session-ID (day) control.
- **P6, cross-room:** trained on Room A, TX-RX3 only.
- **P1-GP** (`idgp_dc2_score`): four integrity checks, the pace blocks, and a multi-pass row.
- **Secondary, code NOT written:**
  - P1-REV: P1 on the `A_rev` passes;
  - P7: pace-matched cross-day, day 1 slow to day 2 slow, and the same for fast.
- **Stated expectation:** with 30 test passes the half-width is about 15 points, so a true 25 %
  will not separate from chance in P1. P2's ordering and P3's contrast with S0 are what DC2 can
  decide.

**Scorers:** `pipeline/identify/id29_dc2_score.py` and `idgp_dc2_score.py`, both pinned. They read
a view, `pipeline/identify/idboth_view.py`, that keeps the pre-registered recordings and `A_fwd`
passes only. The view excludes the `A_rev` passes and the day 1 slow and fast blocks.

**Freeze chain:** 23b, then 23c, 23e (addendum B), 23f (addendum C), 23g (addendum D, an erratum),
24 (both-directions capture and view), and 25 (identification before tracking). All are committed:
25 went in with Tracking's b531975 on 28 Sept. On 28 Sept all 191 pinned hashes printed OK
(`runs/dc2_results/logs/item0_pins.log`).

## The data

`data/room_B/identification/session_01/` (26 Sept) and `session_02/` (27 Sept), 30 recordings each.
For each of the six (participants P1 to P6; names are kept only under `data/` and `runs/`), each day has
an empty room at the spot, natural, slow, fast, and an empty room at home. Day 1 natural is 10
cycles; every other block is 5. A cycle is one `A_fwd` pass and one `A_rev` pass. Every walk block
is COMPLETE in both directions, and every empty room lasts about 32 s. Within each person the block
order held on both days.

**Block start times** (spot room, natural, slow, fast, home room):

| | day 1 | day 2 |
|---|---|---|
| P1 | 12:51 12:54 12:58 13:00 13:05 | 14:03 14:04 14:06 14:08 14:11 |
| P2 | 12:20 12:00 12:16 12:04 12:07 | 14:52 14:53 14:57 14:55 15:00 |
| P3 | 11:15 11:17 11:21 11:22 11:01 | 11:30 11:32 11:33 11:35 11:38 |
| P4 | 12:22 12:29 12:34 12:32 12:38 | 11:58 12:00 12:04 12:02 12:07 |
| P5 | 13:31 13:34 13:38 13:41 13:44 | 13:39 13:41 13:44 13:46 13:49 |
| P6 | 13:58 14:00 14:06 14:05 14:11 | 08:34 08:35 08:39 08:37 08:42 |

- **Order against tracking.** On day 2, all six walked identification before tracking. On day 1,
  P3's whole set and P2's slow block came after that person's tracking.
- **Time of day.** P3 and P5 were recorded at about the same time of day on both days. The
  2026-09-25 schedule addendum requires these times to be disclosed beside every cross-day figure.

**Day 1 deviations.** All are in `reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_E_DRAFT.md`, and
everything moved aside is in `data/room_B/aborted/`.
- P3 re-recorded after tracking. P2's first set had RX2 dead. P4's natural was redone. P1's and P6's
  empty rooms were redone.
- **RX2 low state.** In P2's and P3's day 1 natural blocks (P1 training data), RX2 read 8 to 13 dB
  below its normal level at the spot, for the whole block. The cause is unknown.
- P2's slow block was confirmed at the spot.
- Uzayr decided: everything is scored as recorded, with disclosure only and no sensitivity row. RX2
  was at home for P3's home room.

**Day 2 deviations.**
- **Two empty rooms at the spot were redone,** because RX2 had not been moved: P3 at 11:28 and P1 at
  14:00, both in `aborted/`.
- **Participant P5, day 2 fast, pass 9 (`A_fwd`) is mislabelled.** It holds a double press 0.17 s apart,
  so it closed on the real 4 m press. The tool flagged it, and the day check passes it.
  - As recorded it lasts 2.86 s, which is 1.75 m/s. With its real 5 m press, recorded as pass 10's
    first press, it lasts 3.70 s, or 1.35 m/s. P5's other fast `A_fwd` passes take 3.57 to 4.04 s.
  - Pass 10 (`A_rev`) runs 7.18 s, and its real 0 m press was never recorded (60 presses in the
    block).
  - Pass 9 feeds P3 fast, P1-GP's fast block and P7 fast. Its 2.86 s is inside the scorer's 1.5 to
    12 s gate, so nothing refuses it.
  - Tracking fixed an analogous error in participant P1's tracking walk by a POST HOC relabel
    (`reports/PREREG_DC2_ADDENDUM_2026-09-28_relabel.md`). That addendum covers tracking only.
- **RX2 on day 2** (a within-person check, levels only, no figure):
  - every walk block matches its own person's spot room (r 0.92 to 0.999), with no low state;
  - between the days, RX3 reads about 4 dB lower on day 2 for all six, and RX2 at the spot 4 to
    12 dB lower; RX1 is unchanged. Not analysed further.

## Before any identification figure (runbook section 5, `reports/DC2_ID_DAY_RUNBOOK.md`)

1. Write the P1-REV and P7 scorer. It imports `id29_dc2_score` unchanged, builds its own view
   (natural `A_rev` passes; `A_fwd` passes from both days' pace blocks), and scores only those
   rows. It is tested on synthetic data only and hashed into a new identification freeze that
   references `IDENTIFICATION_FROZEN_2026-09-25.json`. **Waiting for Uzayr's go-ahead.**
2. Approve addendum E. It needs a day 2 section: the participant P5 pass, the two redone spot rooms, the day 2
   RX2 levels and the time-of-day note. Then it drops `_DRAFT` and is hashed in that same freeze.
3. Decide on participant P5's pass 9: a POST HOC relabel before any figure, as Tracking did for participant P1, or
   score it as recorded and disclose it.
4. Verify the pins and run `tests/test_addendum_d_hash.py` and `tests/test_freeze_2026_09_24.py`.
5. Build the view (`idboth_view`: expect 48 recordings included, the 12 day 1 slow and fast excluded).
   Then `id29_dc2_score --check-layout --data-root runs/identify/dc2_view/room_B` must say
   `"ok": true`.
6. Score once each: `id29_dc2_score`, then `idgp_dc2_score`, then P1-REV and P7. Never score
   `data/room_B` directly. A rerun needs `--rerun-reason`.

**Coordination.** The Tracking session is running a DC2 tracking batch until about 29 Sept 06:00
(`QUEUE.md`), one training job at a time, and its brief says not to touch identification. The
identification scorers train a CNN (SECONDARY, 5 seeds). Ask Uzayr before starting them while that
batch runs.

## Related

- **Live identification mode:** `pipeline/live/identify.py` (untracked). It matches `id29` on
  synthetic data: 90 of 90 passes' features, and 18 of 18 predictions. It needs day 1 natural as
  its enrolment set.
- **Uncommitted identification files:**
  - this handoff and the 26 Sept one;
  - `ADDENDUM_E_DRAFT`;
  - the runbook edits;
  - `runs/identify/dc2/rx2_spot.json`, whose date was renewed on 27 Sept 08:25, same spot
    (primary, (2.0, -0.5)).

## Update, 2026-09-28 22:11 SAST: the operator's direction change

**Everything above is superseded for development work** by `reports/BRIEF_ID_DIRECTION_2026-09-28.md`
(verbatim; tracking's copy is INSTRUCTION 9 of `reports/BRIEF_render_and_prepress_2026-09-22.md`, and
STATE.md has the shared summary). In short:

- **The goal:** the best identification model that generalises across rooms and days, real time.
- **Stopped for development:** pre-registration, POST HOC labels, the ship rules, deference to the
  frozen configuration, and asking approval for each choice. A development log replaces them:
  `reports/DEVLOG_ID_2026-09-28.md`.
- **Still binding:** no leakage (whole-session splits, statistics from training or causal pre-pass
  data only); causal live claims; gait-based identification (pace only inside gait analysis);
  `data/` read only; free-movement recordings never used.
- **The evaluation standard:** leave one session out over A1, A2, A3, B1 and B2, with every choice
  made on validation inside the four training sessions, reported per held-out session and per room
  beside the frozen references.
- **Kept untouched:** every report, freeze and result above, including the scored DC2 rows
  (af74d8a, b74d647, 693a851) and the v2 registration (000ad28). The registered v2 run started at
  20:59 is allowed to finish and is logged as a "before" reference.
- **Where to start:** the development log's plan. Compute is shared with tracking: identification
  runs CPU-only at 4 threads unless tracking frees the GPU.

## Update, 2026-09-29 14:12 SAST: batch 2 done, final model adopted

- **Read first:** `reports/ID_DEV_FINAL_2026-09-29.md` (the closing report), then the end of
  `reports/DEVLOG_ID_2026-09-28.md`.
- **The final model:** the equal-weight ensemble of the eight `idx_all` components.
  - Its offline decisions are in `runs/identify/dev/loso/sel_all_ens.json`.
  - The components' saved outputs are in `runs/identify/dev/all/`.
- **Headline, leave one session out:** Room A 39.72 [27.50, 46.94], Room B 30.00 [19.58, 39.17].
- **Live:** at 5 s, Room A 40.28 and Room B 31.67; exact at 21 s.
- **To re-run a live replay:**

      python3 -m pipeline.identify.idx_live --selection sel_all_ens --wide --perlink --steps 6000 \
          --seeds 0 1 2 --device mps --wait 5 --predict-live --session <S>

- **Queues:** all identification queues are finished, and the runners are stopped.
- **Correction on record:** a 5 s live equality claim was wrong (DEVLOG, 08:25). Only the 21 s wait
  gives exact equality.
