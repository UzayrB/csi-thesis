# QUEUE_V5: identification, build and ship engine v5, then close identification

Uzayr's brief (prompt_identification_v5_ship.md; received at or before 10 Oct 2026 17:42:24 SAST, the first `date` read on it). v5 = the Room A
run's A3-half choice: base A1+A3+A4+M3, C2 weights w_A 0.25, w_B 1, w_unseen 1, w_id 1 (runs/identify/roomA/stores/split_A3.npz).
Development evaluation, all data seen. Read this file first on every turn. Session: Third overall. Stop rules: an exactness
check fails (steps 1 to 4) or the timing fails: stop, report, wait for Uzayr.

| step | state | next action |
|---|---|---|
| 0 set-up | DONE | the whole job granted by the Mastermind (its caffeinate PID 19101; JOB_DONE only at the end) |
| 1 expected figures | DONE (every number of section 4 reproduced) | runs/identify/v5/expected.json; every number of the brief's section 4 reproduced |
| 2 version switch, null check | DONE (13 of 13 v4 replays exact, max abs diff 0.0; 18:29) | engine.py behind the manifest's engine_version; 13 v4 replays reproduced exactly |
| 3 train v5 | DONE (18:29 to 18:43; 10 models, CNN hashes equal v4, components equal roomA exactly) | nine scorecard models and deploy_all5 as *_v5; components equal roomA/comps |
| 4 v5 replays | DONE (18:44 to 19:47; 13 of 13 reproduce split_A3 exactly, max abs diff 0.0; every window equals the bank or tta) | 13 model-sessions; split_A3.npz reproduced (1e-6, every decision); offset windows equal tta |
| 5 figures | DONE (19:55; eval_v5.json, eval_xroom_v5.json; scorecard_v5.json equals expected.json in every figure) | eval_v5.json, eval_xroom_v5.json, scorecard_v5.json (equals expected.json) |
| 6 live app | DONE (19:58; smoke test passed: 20 decisions, schema v3, room A, a 0.25; the rig refuses without --room) | deploy_all5_v5, --room A/B/new, schema, live-interface.md, smoke test |
| 7 rig timing | FAILED 10 Oct (cpu); option (c) 11 Oct: exactness PASSED (mps 299 of 299, 0; cpu before = after bit-identical); the confirmation run FAILS narrowly (297 of 299 within the cap; memory 1.99 GB/h): reported and flagged, nothing changed | B2 identification walks at 1x with loso_B2_v5; renders identify_v5_* |
| 8 report, close | DONE 11 Oct: reports/identification/2026-10-11_engine-v5.md (the stop report kept); PLAN note; QUIET; JOB_DONE; the Mastermind told | report, Editor list, PLAN.md note, commit, QUIET, message |

- **10 Oct 2026 19:48:31 SAST: step 5 stopped on a missing input, not a difference.** ide_eval's one-press cost reads the two-press outputs
  runs/identify/audit/outputs/B1_to{B1,B2}_causal.npz, removed by the 6 Oct cleanup (3f3612b4). Recovered byte for byte from
  git 3f3612b4^ into runs/identify/v5/recovered/two_press/ (RECOVERED.json: blob hashes equal); the recovered files reproduce
  eval_v4.json's two-press blocks exactly (every block, intervals included). ide_eval --version 5 reads them only when the
  original is absent (v4's default path unchanged). Steps 5 to 7 re-queued behind their gates (steps 6 and 7 were held by
  their gates, as designed).
- **10 Oct 2026 19:54:46 SAST: step 5's cross-room scoring stopped on a bug of mine, not a difference.** ixr_eval's `table1` default
  argument (models=MODELS) is bound to v4's names at definition, so `--version 5` scored v4's models and table2 found no
  v5 name. Fixed by passing the evaluated version's models; v4's default output rechecked identical to eval_xroom_v4.json;
  a dry run of the v5 scoring and of the replay scorecard (equal to expected.json in every figure) passed. eval_v5.json and
  the 8 CAL-none files were already written; the rest of step 5 and steps 6 and 7 re-queued behind their gates.
- **10 Oct 2026 19:57:19 SAST: step 6's smoke test found a real deployment bug.** deploy_all5_v5 decided A3's first recording (20 walks,
  schema v3, room A, weight 0.25), but the rig refused it for "the manifest lacks gs_adopted" (the live app's deployment
  check), not for the missing --room. The v5 manifests now carry gs_adopted from their v4 manifests (False; nothing else
  changed; iv5_train writes it from now on); the rig without --room now refuses for the room. Steps 6 and 7 re-queued.
- **10 Oct 2026 20:30:11 SAST: step 7's first rig run was killed by the 13 GB memory guard at 20:29:59 (not a timing failure).** The live
  app's path does not release the MPS allocator's cache, so the run's footprint grew to 13G over 31 min (47 of 60 natural
  screens rendered). The timing harness now releases it after each decision is out (fcdbec05), as the replays do; its
  partial outputs (the jsonl under rig/, 47 renders) are superseded by the rerun. Step 7 re-queued.
- **10 Oct 2026 20:32:12 SAST: step 7's device (the Mastermind's question).** The 30 Sep rig run used `--device mps` (its report's command
  line); the boards' `rig` defaults to `--device cpu`, so step 7 measures **cpu** (what ships), under the run's rules
  (OMP_NUM_THREADS=1, nice 10: a conservative bound), with the renders; an mps run follows as a secondary figure
  (rig_timing_mps.json, no renders). The mps rerun started at 20:30:29 was stopped by PID before it measured anything.
  The MPS cache release moved from the timing harness into the live app (`identify_engine.EngineApp.poll`, engine v5 on
  mps only, after each decision is out; v4 untouched), so the harness measures the app as shipped.
- **10 Oct 2026 20:33:23 SAST: step 7's fallback (agreed with the Mastermind).** cmd_rig pins no threads in code; every documented launch
  (pipeline/live/__main__.py, rig_run.py, the 30 Sep rig run's command) uses OMP_NUM_THREADS=1 at nice 0. If the cpu run
  (one thread, nice 10) passes, it is the result, labelled a conservative bound; if it fails, it is rerun once at the
  shipped setting (one thread, nice 0, outside the driver, with a memory watch) as rig_timing_cpu_shipped.json, and the
  stop rule applies to that run. No AdaBN deferral (Uzayr's call). The 30 Sep v4 timing was on mps; the mps run here is the
  like-for-like comparison.
- **10 Oct 2026 22:21:30 SAST: STOP (the brief's stop rule, step 7).** The rig timing fails at the shipped setting (cpu, one thread, nice 0:
  10 of 171 decisions before the cap; AdaBN median 2.96 s); mps also misses the cap narrowly (74 of 171; delay median 1.33 s)
  with no backlog; the AdaBN sample shows the cost is the engine's (v5/v4 median ratio 1.006). Options for Uzayr: (a) mps as
  identification's rig default, (b) the AdaBN adaptation after the decision (no figure changes), (c) both. Nothing changed;
  the driver's hold block closed (nothing running); waiting for Uzayr.
- **11 Oct 2026 12:39:25 SAST: Uzayr's go, in this chat (after his 02:41 "wait").** DECISION: option (c), "AdaBN after the decision is written, for
  v5 only, and mps as v5's rig default. v4 stays untouched." STORAGE: Drive ("the manifest, .gitignore and a note telling me how
  to copy the files to Drive myself"). Section 2 of ~/Downloads/prompt_mastermind_ship_v5_and_methodology.md (his, file time
  11 Oct 02:42) applies. Proofs: a change in pipeline/live/identify_engine.py only, so the 26 harness replays are not rerun;
  instead B2 through the live app on mps and on cpu, every decision equal to the v5 replays, and the 02:51 before capture
  (loso_B2_v4 on B2's first recording, loso_B2_v5 on its first four; scratch) shows v4 unchanged. A change to engine.py or
  ide_replay would need the null and v5 replays, the scorecard and the smoke test again. Confirmation run: mps, at least 40
  minutes, every decision timed; identification closes whatever it shows; a failure changes nothing and is reported and
  flagged. Slot asked of the Mastermind 12:39; nothing heavy before its reply.
- **11 Oct 2026 12:49:10 SAST: the change (da199808), its check, and the confirmation run's rules, fixed before it starts.** The change is in
  pipeline/live/identify_engine.py only (engine.py, ide_replay and every replay untouched), so the 26 harness replays are not rerun
  (Uzayr's go). `AfterDecision` holds each walk's Session.add until its decision is written and shown; it runs at the app's next
  poll, or just before a later walk's classification when two walks are decided in one poll (a recording's close), after the
  earlier decision is written. `rig` defaults to mps for an engine v5 model, cpu for any other. Check: the live app before
  (02:51) and after (12:40) on cpu is bit-identical in every decision field for loso_B2_v4 (one recording, 10 decisions) and
  loso_B2_v5 (four recordings, 50 decisions); only the three wall-clock timing fields differ (checks/live_before_after.json).
  Confirmation run (run_confirm.sh; iv5_rig confirm): B2 through the real serial parser, EVERY recording at 1x (tracking ones
  too, so every decision is timed and the run lasts about 65 min, past 40), loso_B2_v5, room B, mps, OMP 1, nice 0, MPS 0.7/0.5,
  killed above 12 GB or below 30 % free. Pass, fixed now: every one of the 299 decisions timed and before its cap (t0 + 5.30 s);
  the stream's lag at every press at most 0.5 s; memory flat (the footprint sampled every 30 s; its least-squares slope from
  minute 10 to the end at most 0.5 GB/h, and never above 12 GB). Exactness (stop rule): argmax 299 of 299 and the ensemble equal
  to loso_B2_v5's replay exactly (0) on mps. Identification closes whatever the timing shows (Uzayr).
  Found in the harness test (four recordings, cpu, 20x, scratch): cpu against the mps replay reaches 9.47e-06 on a closing-poll
  decision, with the code before the change as well (same value, same row); step 7's 8.1e-06 covered only the 287 decisions it
  timed, never the closing ones. Put to the Mastermind before the cpu check.
- **11 Oct 2026 14:02:22 SAST: the confirmation run (12:49:15 to 13:54:49, 65.4 min, rc 0, not killed): exactness PASSED, timing FAILS on 2
  of 299, memory FAILS its rule; per Uzayr nothing is changed, the measurement is reported and flagged, the close goes on.**
  Exactness: argmax 299 of 299, ensemble difference 0.0 against loso_B2_v5's replay. Every decision timed (the 12 closing-poll
  ones included): 297 of 299 before the cap; delay after t0 + 4.0 s median 1.083, p95 1.189, p99 1.261, max 1.453 s; lag at a
  press max 0.077 s. Late: the day's first walk (1.301 s, 1.3 ms over; its model call 0.316 s, the GPU's first) and a slow-block
  walk (1.453 s; its last window's extraction 0.482 s against a median 0.105). The adaptation, after the decision: median 0.277,
  max 0.525 s; all 299 at the next poll, none waited for; each done at least 4.99 s before the next walk's last window was due.
  Memory: 1.64 GB at 10 min, 3.35 GB at the end, largest 4.47 GB; slope 1.99 GB/h against the rule's 0.5. The app's arrays are
  0.08 GB at 299 walks (checks/memory_account.json); step 7's cpu run grew only 0.94 to 1.17 GB while both mps runs grew: the
  GPU side, not attributed further. The Mastermind told (14:01). Also corrected (the Mastermind, 13:10, checked against the
  records): the 10 Oct note above calling 30 Sep's rig run a v4 timing on mps is wrong; it was engine v2 at maximum speed, so
  this run is the first whole-day 1x timing of any engine. Step 3 (cpu exactness, before and after side by side) started 14:00:15.
- **11 Oct 2026 14:26:14 SAST: step 3 (cpu exactness) PASSED; storage done.** B2 through the live app and the real serial parser on cpu at full
  speed, nice 10, the code before option (c) (f80266b7's pipeline/ in a scratch tree; its run loaded that tree's identify_engine.py)
  and after it, side by side, 14:00:15 to 14:22:12: bit-identical on all 299 decisions (t0, t_dec, ensemble, ensemble without
  pace, confidence, calib_n, top, closing). After against loso_B2_v5's replay: argmax 299 of 299; 8.06e-06 on the 287 decided
  during the stream (within 8.1e-06, as step 7); the 12 closing-poll ones (never compared by step 7) at most 9.47e-06, the same
  with the code before the change (checks/cpu_exact.json). Storage (14:23 to 14:25): STORAGE.json, STORAGE.md (Uzayr's copy to
  `My Drive/Thesis Backup Data/` by hand; Drive is not on this machine), STORAGE.sha256 (40 of 40 OK); all 40 RF/ET pickles
  (5.78 GB; 27 over GitHub's 100 MiB limit, the other 13 larger than any v4 pickle; a model needs all four) in .gitignore; loso_B2_v5
  rebuilt in scratch: its four pickles byte-identical to the stored ones (checks/rebuild_loso_B2.json). Next: step 8.
- **11 Oct 2026 14:27:17 SAST: step 8, identification closed.** The final report, `reports/identification/2026-10-11_engine-v5.md` (iv5_report;
  the 10 Oct stop report kept unchanged), with every check, every figure, the confirmation run's timing (FAIL on 2 of 299 and on
  memory, flagged for Uzayr), the cpu finding, storage, files and commits, and the Editor list in PA order (for the Editor only
  after the Mastermind's review). PLAN.md: "engine v5 shipped; identification development closed". live-interface.md: the
  adaptation after the line is written; mps as v5's rig default. Then QUIET and runs/identify/v5/JOB_DONE.

