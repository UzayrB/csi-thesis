# H2: the boards (15 Oct 2026, written 10:05:14): BLOCKED

**Ports, named by station MAC** (pipeline.io.identify_board, 09:58:56 and 10:01:29): RX1 68:09:47:4c:ef:b4 on
/dev/cu.usbserial-3; RX2 20:50:0d:1a:28:74 on /dev/cu.usbserial-4 (its first cable or connection flapped, the CP2102
appearing and dropping every 1 to 4 s, 09:58:01 to 09:58:33, then stable); RX3 20:50:0d:30:5f:80 on
/dev/cu.usbserial-0001. All three run csi_recv. The TX is on power only, not on USB (Uzayr, 09:54), so it is detected
through its frame counter: 150.0 frames/s sent on every receiver.

**The 3-minute capture** (pipeline.io.capture_logger --duration 180 --reset, the boards' MACs recovered at boot for 3 of
3; 10:01:38 to 10:04:41; files H2_capture/20261015-100138/; full output H2_capture.log):

| receiver | received | sent (TX counter) | received/s | sent/s | loss (TX counter) | parse errors (malformed) | RSSI at 30 s | verdict |
|---|---|---|---|---|---|---|---|---|
| RX1 | 25,930 | 27,018 | 144.0 | 150.0 | 4.03 % | 0 | -74.7 dBm | rate below 146 |
| RX2 | 26,520 | 27,017 | 147.3 | 150.0 | 1.84 % | 1 (one bad-data line in 26,857) | -72.1 dBm | 1 parse error |
| RX3 | 24,378 | 27,009 | 135.4 | 150.0 | **9.74 %** | 0 | -83.6 dBm | **FAIL** |

- **Config watch:** channel 11, secondary 0, bandwidth 0 (HT20), sig_mode 1, rate 11, MCS 0, the same on every node and
  unchanged through the run. PASS.
- **Reconciliation:** all packets accounted for (79 non-CSI boot lines per node, no torn lines, no queue drops, no read
  or write errors).
- The capture tool's own gate (sent at least 146/s, loss under 5 %) fails on RX3 only. The prompt's per-receiver gates
  (at least 146 packets/s, loss under 5 %, 0 parse errors) fail on RX3 (rate and loss), RX1 (144.0/s received) and RX2
  (1 parse error).
- **Likely cause:** RX3's signal is about 10 dB weaker than RX1's and RX2's (-83.6 against -72 to -75 dBm), so it is
  too far from the TX, turned away from it, or shadowed. RX2's one bad line fits its flapping cable.

**Status: BLOCKED** (the prompt: do not continue to H4 until H2 passes). Uzayr messaged at 10:05:14. H3 and H5 do not need the
boards and go on.

## Re-check after RX3 was moved (PASS, written 11:48:27)

Uzayr moved RX3 closer to the TX about 11:40 and kept RX2's cable (re-seated). The re-check ran alone between H5's
streams: the H5 chain's bash paused with SIGSTOP at 11:40:43 so PA2's stream (11:37:34 to 11:44:53) finished
untouched and no next stream started; resumed with SIGCONT at 11:47:57 (h2_recheck.sh, H2_recheck.log; the chain logs
PA2's stream end at 11:47:57 because it was paused, its real end is 11:44:53). Boards by MAC at 11:44:55: RX1
68:09:47:4c:ef:b4 on cu.usbserial-3, RX2 20:50:0d:1a:28:74 on cu.usbserial-4, RX3 20:50:0d:30:5f:80 on
cu.usbserial-0001. Capture 11:44:56 to 11:47:57 (files H2_capture2/20261015-114455/):

| receiver | received | sent (TX counter) | received/s | sent/s | loss | parse errors | RSSI (last 10 s) | verdict |
|---|---|---|---|---|---|---|---|---|
| RX1 | 26,717 | 27,013 | 148.4 | 150.0 | 1.10 % | 0 | -79.3 dBm | PASS |
| RX2 | 26,886 | 27,022 | 149.3 | 150.0 | 0.50 % | 0 | -73.9 dBm | PASS |
| RX3 | 26,981 | 27,020 | 149.8 | 150.0 | 0.14 % | 0 | -67.0 dBm | PASS |

Config watch: channel 11, secondary 0, bandwidth 0 (HT20), sig_mode 1, rate 11, MCS 0 on every node; all packets
accounted for. Every gate holds on every receiver (at least 146 packets/s, loss under 5 %, 0 parse errors, channel
11 HT20). **H2: PASS.** RX3's signal rose 17 dB (-84 to -67 dBm); RX1's fell 5 dB (-75 to -80) with the
rearrangement, still well inside the gates.
