# Check-ins (every 15 min)

- 15 Oct 09:52:19: job started; H0 running; boards at 09:51: RX1, RX3 present; RX2, TX absent.
- 15 Oct 09:59:12: paused 09:55 to 09:58 at Uzayr's word to sort out RX2; RX2 found flapping (CP2102 appearing and dropping every 1 to 4 s), stable from 09:58:38 as cu.usbserial-4, identified 09:58:56; job resumed; H0 DONE; H1 tests running; engine diff: unchanged since the code that ran the 12 Oct confirmation (56eea977).
- 15 Oct 10:05:14: H2 BLOCKED: RX3 9.74 % loss, 135.4/s (RSSI -83.6); RX1 144.0/s; RX2 1 parse error; channel 11 HT20 on all; Uzayr notified; H3 started. Load 2.95.
- 15 Oct 10:22:42: H3: two fixes found and committed (rig key reader not in cbreak mode, 18c49ef8; board rig not on the CPU, 0dcf44ac); recording committed ba6beee1; live tests 49 passed after each; on/off proof running. Load 2.32.
- 15 Oct 10:46:51: Uzayr asked ETA (answered: about 13:00 if the boards are fixed soon). H3: sidecar baseline_capture 5d0aa41d, injector fcefe97c, live tests 49 passed after each; on/off proof rerun with per-walk comparison running. Load 2.14.
- 15 Oct 11:40:52: Uzayr moved RX3 closer (RX2's cable kept); H2 re-check queued between H5 streams (chain SIGSTOP after PA2's stream, resumes after the capture). H3 DONE. Load 1.92.
- 15 Oct 11:48:27: H2 re-check PASS (RX1 148.4/s 1.10 %, RX2 149.3/s 0.50 %, RX3 149.8/s 0.14 %, 0 parse errors, ch 11 HT20); H5 resumed 11:47:57 (stream 4 of 6). Load 3.29.
- 15 Oct 12:14:54: H5 streams 6 of 6 done (12:10:25); re-replays running, PA5 IDENTICAL; measurement commit c4169c88, live tests 49 passed; H4 next. Load 3.30.
- 15 Oct 13:01:34: H4 and H5 DONE; REPORT.md written; heartbeat and caffeinate released, the check-in cron deleted; hand-over sent; stopped for Uzayr's walkthrough.
- 15 Oct 13:13:04: H4 fix started at Uzayr's word; F1 and F2 coded; proof A running.
- 15 Oct 13:57:01: H4 fix DONE; report updated; caffeinate released.
