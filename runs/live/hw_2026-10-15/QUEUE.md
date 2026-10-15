# Hardware job queue (Mastermind, 15 Oct 2026; Uzayr's prompt prompt_mastermind_live_hardware_test.md, his go "you have the go on everything", Mastermind to do it itself)

Started 15 Oct 09:52:19. Caffeinate PID 25833 (`caffeinate -dimsu -t 28800`). Heartbeat PID 25848 (heartbeat.log, one line a minute).

| item | status | next action | ETA |
|---|---|---|---|
| H0 state | DONE 09:55 | H0_STATE.md: HEAD baddef1f, settings as shipped, quiet, preflight ALL ok | |
| H1 offline proofs | DONE 10:02 | H1_OFFLINE.md: live tests 49 passed + the slow one with TDR_SLOW=1; engine unchanged since 56eea977, no rerun | |
| H2 boards | DONE 11:48 | re-check PASS after RX3 was moved: 148.4 / 149.3 / 149.8 pkt/s, loss 1.10 / 0.50 / 0.14 %, 0 parse errors, ch 11 HT20 (H2_BOARDS.md) | |
| H3 rig recording | DONE 11:03 | H3_RIG.md: fixes 18c49ef8, 0dcf44ac; recording ba6beee1, 5d0aa41d; recorded runs replay IDENTICAL (2 of 2); on/off within run-to-run variation | |
| H4 board smoke runs | DONE 13:00 | tracking PASS (live = replay IDENTICAL, 1,388 rows; refusal shown at 6 s); identification PARTIAL (17 of 18 before the cap; replay differs, argmax 17 of 18) | |
| H5 B2 streamed, shipped tracker | DONE 12:27 | 6 of 6 re-replays IDENTICAL; committed 118 / 120, locks 114 / 120 | |
| H6 hand-over | DONE 13:01 | REPORT.md; one message to Uzayr; stopped for his walkthrough | |

## H4 fix (Uzayr, 15 Oct about 13:05: "Fix H4 needs to be perfect"), from 13:13

| item | status | next action | ETA |
|---|---|---|---|
| F1 identification consumer in data-time order | DONE 13:19 | 90d878c8; proof A IDENTICAL | |
| F2 tracking refusal clean | DONE 13:19 | 86b122ac | |
| F3 proof B: B2 recorded source vs the 12 Oct confirmation | DONE 13:21 | 299 of 299 IDENTICAL | |
| F4 live tests, commits | DONE 13:19 | 49 passed, 1 skipped | |
| F5 H4 rerun on the boards | DONE 13:53 | refusals clean; tracking replay IDENTICAL; identification replay IDENTICAL x2; 34 of 35 decisions within the cap (one 3.6 s stall); RX3 outage crash (existing weakness) | |
| F6 report and hand-over | DONE | REPORT.md section 'H4 after the fix' | |
