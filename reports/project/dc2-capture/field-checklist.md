# DC2 FIELD CHECKLIST. One page, in capture order

**26 and 27 September, Room B. Print this and work down it.**

Every item exists because a pre-registration depends on it. The right-hand column says what breaks
if it is skipped. Full detail: `reports/DC2_PROTOCOL_2026-09-18.md`,
`reports/PREREG_DC2_crossroom_2026-09-22.md`.

**Tick each item. If one cannot be done, write down WHY on the sheet at the time** — a note made
in the room is worth more than a reconstruction afterwards.

---

## BEFORE DC2, ONCE: THE LIVE RIG RUN. **BLOCKED ON OPERATOR (no receiver attached, checked every 15 min on 2026-09-23)**

**ONE COMMAND** (batch 23e item 7): `scripts/live_rig_run.sh --participant P01 --baseline <empty-room baseline dir>`.
It prints a short prompt, identifies every board by MAC, names RX1 to RX3 BY MAC (never by port order),
starts the capture with that explicit mapping, shows a live line every 0.5 s (packets, loss per link,
windows), and writes per-link loss, latency and the timestamp drift of the live fit to
`runs/constrained/fh/rig_run/results.json`. `--dry-run` identifies and prints the plan only.
**It does not draw the live DOT** (the pooled live runner is the known gap in `tracker_live`); it
runs the hardware-dependent part: live windowing, gate and packet statistics.

| ☐ | item | if skipped |
|---|---|---|
| ☐ | TX and all receivers on USB; `scripts/live_rig_run.sh --dry-run` shows RX1, RX2, RX3 found BY MAC (and RX4 if the ID board is on) | nothing below can run; a board named by port order can be the wrong radio |
| ☐ | Empty-room baseline for the session captured first (`make baseline`), its directory passed as `--baseline` | the live engine has no baseline and refuses |
| ☐ | **Run the one command**; walk the passes the capture tool prompts | no raw capture, no live figures |
| ☐ | **After:** `python3 -m pipeline.realtime.tracker_live --session <id> --stem <stem>` for lattice alignment of live against offline windows (decision equality given the same windows is already 20 of 20 on replay) | a live figure no offline figure can reproduce |
| ☐ | **Packet loss** per receiver and **latency** read from `rig_run/results.json` | the headroom figure (31.7x per stride on replay) is unverified on hardware |

## THE FIFTH RECEIVER (a fourth RX, identification only). Batch 23e item 6

A spare ESP32 next to the TX, as a dedicated identification link. **Tracking geometry unchanged, and
tracking reads ONLY RX1, RX2 and RX3, by node name; every name is checked against its board's MAC.**

| ☐ | item | if skipped |
|---|---|---|
| ☐ | **Name it RX4.** Flash it as a receiver (`csi_recv`); find its port and MAC with `make identify` (`python -m pipeline.io.identify_board`): its port is the `/dev/cu.usbserial-*` whose station MAC is NOT one of the three tracking MACs below | a board named RX1..RX3 by port order silently becomes a tracking link |
| ☐ | Tracking boards by MAC, from Room A's sidecars: **RX1 68:09:47:4c:ef:b4, RX2 20:50:0d:1a:28:74, RX3 20:50:0d:30:5f:80** | DC2 REFUSES a tracking name carrying another board, or a tracking board under another name |
| ☐ | **Every capture uses an explicit mapping**, never autodiscovery: `NODES="RX1=<port>,RX2=<port>,RX3=<port>,RX4=<port>"` (autodiscovery names ports RX1..RXN in sorted port order) | the ID board can be recorded as RX1, RX2 or RX3 |
| ☐ | **Check all four stream** before each session: `make run DURATION=20 NODES="..."`, and every one of RX1 to RX4 shows packets at about the transmit rate with no long gap in the logger's per-node table (or the rig command's live line) | an ID link that drops out is only found afterwards |
| ☐ | The sidecar records `node_macs` for all four (the capture tool does this) | DC2 cannot verify the boards and reports them as unverified |

## BEFORE ANYTHING ELSE, each day

| ☐ | item | if skipped |
|---|---|---|
| ☐ | **Node geometry identical to Room A**: TX (2.5, −0.5), RX1 (2.5, 5.5), RX2 (−0.5, 2.5), RX3 (5.5, 2.5) relative to the taped grid. Same heights, same orientations. | **The cross-room result is confounded.** Room and layout would change together and neither could be blamed. Do not move a node for any reason. |
| ☐ | Taped grid laid to 5 x 5 m, same twelve lines, anchors at the same coordinates | chance is no longer 8.3 percent and the state space no longer matches |
| ☐ | Photograph the layout and the node mounts | the only record of whether geometry was actually held |
| ☐ | **Reaction-time bias measured, BEFORE the first evaluated pass** | every anchor timestamp is biased. `pipeline/io/rt_calibration.py` warns about double-subtraction by name |
| ☐ | Record the start time of each block | the causality checks prove calibration precedes evaluation |
| ☐ | **Every sidecar records the reaction-time bias as APPLIED** | `p1_runup.first_presses` and `sb2_structural.press_ends` REFUSE a sidecar that does not, and the run stops |

## THE CALIBRATION BLOCK, each day, before any evaluated pass

**This is the item DC2 exists to add. Room A has no equivalent and that is why two pre-registered
analyses could not be verified.**

| ☐ | item | duration | if skipped |
|---|---|---|---|
| ☐ | **Empty room, nobody inside** | 60 s | no noise floor; the gate threshold cannot be re-anchored |
| ☐ | **One person standing still, room centre** | 60 s | no STILL end of the gate bracket |
| ☐ | **Calibration walks: 2 passes on each of 4 named lines** | ~3 min | **THE NULL LEVEL CANNOT BE CALIBRATED.** A 3-nat error costs 16.7 points, and a walk on a known line is the only thing that exercises what the null discriminates |
| ☐ | Write down which 4 lines were used | the analysis must exclude exactly these passes |
| ☐ | **Write `data/room_B/calibration.json`**: per session, `calibration_pass_ids` and `aborted_pass_ids` | the pipeline cannot tell calibration from evaluated passes; a calibration pass scored is a void figure |

**Calibration passes are NEVER scored.** They set constants and take no part in any figure.

## PER PARTICIPANT, per day

| ☐ | item | if skipped |
|---|---|---|
| ☐ | **At least TWO SEPARATED blocks per person, interleaved with other participants** | **the recording-block confound.** One block per person makes "who" and "when" the same variable, and any per-person result becomes unreadable |
| ☐ | **20 to 30 walking passes per person**, not 20 | per-person arms cannot be measured at 8 passes each |
| ☐ | **Edge lines deliberately over-sampled** (E_col1, E_col5, E_row1, E_row5) | they are 6 passes in 120 in Room A, the least-sampled lines, and the ones every ship rule reports separately |
| ☐ | **Deliberate speed variation: slow, normal and fast passes** | the single most important item for identification. Without it, pace and identity cannot be separated |
| ☐ | **The APPROACH WALK before each press, recorded and not discarded** | the pre-press reader cannot be trained properly. Room A discarded these and the retrofit failed |
| ☐ | **Label each approach walk's START REGION** (free: it is the known start of the pass about to be walked) | the labels are the whole point of recording the approach |
| ☐ | A short standing block over a handful of cells, 3 to 4 min | presence examples for the motion gate |
| ☐ | **Labelled off-path walking**: weaving, curving, stopping and starting, several minutes | the negative class the transit false-fires show is missing |
| ☐ | Video of every walk, frame-synchronised | ground truth without the anchor lattice; lets cadence be measured |
| ☐ | Per-participant log: height, build, clothing, footwear | the found rate orders loosely with body size and n=6 cannot settle it |
| ☐ | Keep temporal spread within a session | the within-day split depends on passes being separated in time |

## AT THE END OF EACH DAY

| ☐ | item | if skipped |
|---|---|---|
| ☐ | **Write the exclusion list in the sidecar NOW**: any pass aborted at capture time | exclusions decided later are selection on outcome |
| ☐ | **Never exclude a pass for scoring badly.** Aborted-at-capture only | the evaluation stops being honest |
| ☐ | Note anything unusual: interference, people entering, equipment moved | the only chance to explain an outlier without guessing |
| ☐ | Back up the captures before leaving | |

## THE FIRST THING TO DO WITH THE DATA, before any figure is quoted

| ☐ | item | why |
|---|---|---|
| ☐ | **RUN THE ONE COMMAND: `python3 -m pipeline.constrained.dc2_pipeline --room room_B`.** It cuts the ONE lattice (press-aligned 0.5 s) itself from the raw capture, runs the five heads trained on Room A 01 + 02 + 03, configurations A and B, both confirmatory arms, and writes `reports/DC2_REPORT_room_B.md`. It REFUSES if the raw capture is missing | the thesis figure. **Corrected 2026-09-23d:** Room B does NOT need a second cut for the pool, because every pool head is inferred over the 0.5 s windows |
| ☐ | **Only for within-DC2 cross-day training:** `python3 -m pipeline.splits.windows --data data --out runs/constrained/windows_s1.0_dc2 --stride 1.0 --sessions <the Room B session ids>` | within-DC2 cross-day cannot train its 1 s heads. It does not affect Room A to Room B |
| ☐ | **NEVER** cut Room B into `runs/constrained/windows_half` (the retired GRID lattice) or `windows_w1` (1 s WINDOWS, a different tree) | a run on the wrong lattice, or two different trees under one name |
| ☐ | **Print the three calibration numbers**: the pooled emission scale, the realised null reference, and the band-energy distribution (p10, p50, p90) for the empty room, the standing block and the calibration walks | turns two SILENT failures into loud ones. If Room B's numbers sit far outside Room A's, the decoder has not failed — it has been handed constants that do not describe the room |
| ☐ | **Re-run the relative-form verification against the day's own calibration block.** Enable the relative gate and null only if they clear the one-pass bar | they did NOT clear it on Room A's improvised anchor and are disabled by default |
| ☐ | Confirm no calibration pass key appears in any evaluated set | asserted by test |

## WHAT IS BEING TESTED, so nothing gets improvised in the room

| | |
|---|---|
| **what DC2 tests** | the SHIPPED configuration of freeze 23c: the ONE lattice, the five-head pool (mean fusion), the committed decision with `a_veto_1.0`, heads trained on Room A 01 + 02 + 03 |
| **primary comparison** | that tracker unchanged (A) against the same tracker with the **gate and a RELATIVE null re-anchored on the calibration block** (B). **No tracker adaptation.** Pre-registration section 10.3 |
| **confirmatory arms, each at 97.5 percent** | `a_veto_1.0` (against B without it) and `b_abstain_0.25` (frozen `22c`), each applied **once**, no sweep, no refitting; (f) as amended |
| exploratory | AdaBN on the tracker, statistics from the **calibration block only** |

**Nothing on this list is tuned in the room.** Every constant is frozen before arrival. If
something has to change, write down what and why at the time, and it is disclosed as a deviation.
