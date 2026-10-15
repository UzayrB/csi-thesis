# THE DC2 MODEL FREEZE

**No model change is made until the Room B analysis.** Anything changed after Room B data exists is POST
HOC and says so, in those words, at the point of change (PREREG_DC2 section 9).

Frozen 2026-09-23, batch 23g, before any Room B data (`data/room_B` does not exist). Freeze record
`runs/TRACKING_FROZEN_2026-09-23h.json` holds the SHA-256 of every code, model and document file below.
Pre-registration `reports/PREREG_DC2_crossroom_2026-09-22.md`, sections 10 to 12. One command:
`python3 -m pipeline.constrained.dc2_pipeline --room room_B`.

## What DC2 tests

| component | exactly |
|---|---|
| window lattice | **the ONE lattice** (`lattice.SHIPPED = "pressalign"`): 2.0 s windows at a 0.5 s stride, re-phased per pass so a window starts 2 us after each press (`PRESS_EPS_S`) |
| heads | the five-head pool at EQUAL weight, **mean link fusion**: the 0.5 s g25 head (seed 0), three 1 s g25 heads (seeds 0, 1, 2) and the g100 100-cell region head, all inferred over the 0.5 s windows. **Trained on Room A sessions 01, 02 and 03 together, tag `s010203_to_sB`**: `runs/artefacts_s0.5_pressalign_roomA3` (g25 and the position head) and `runs/artefacts_s1.0_roomA3_{s0,s1,s2,g100}`; 18 model files, hashed |
| pre-press reader | the region reader on the same `s010203_to_sB` heads |
| decoder | the shipped semi-bounded decoder: Viterbi over the chain state space with null and exit, soft entry within 1.0 m of each line's start, the chain prior fitted on the training sessions, family-first, maximum-likelihood final rule, causal exit |
| **committed decision** | the A2 start-consistency term (weight 0.5) **plus `a_veto_1.0`**: a start region the reader puts below 0.01 is pushed down by 3.0 nats (`veto.py`) |
| receivers | tracking reads **RX1, RX2 and RX3 only, by name AND by board MAC** (Room A's: RX1 68:09:47:4c:ef:b4, RX2 20:50:0d:1a:28:74, RX3 20:50:0d:30:5f:80); a fourth receiver (RX4, identification) is accepted and never read by tracking; a tracking board under another name REFUSES the run |

## The DC2 comparisons (section 10 and 11 of the pre-registration)

| | |
|---|---|
| **A**, the honest baseline | the frozen tracker unchanged |
| **B**, the primary outcome | gate threshold and null re-anchored on the calibration walks: null = -7.50 x s_B / s_A (s_A = 2.1108124982838437, a +-3 nat guard back to -7.50), gate re-anchored from 0.431. No tracker adaptation |
| confirmatory arms, each at 97.5 percent | `a_veto_1.0` (B against B without the veto) and `b_abstain_0.25` (abstain threshold 0.90, weight 0.25); conditions (a), (b) in DC2's own pass counts, (f) as amended |
| exploratory | `B_prod0.25`: product link fusion at w = 0.25, null re-anchored at the product's scale (s_A,prod = 3.7428177798574556); no claim rests on it |
| chance | 8.33 percent (one in twelve lines) |
| Room A reference | 62.50 pre-registered; 73.33 post-amendment, disclosed as such |
| never scored | the calibration passes (asserted) |

## The display (a component, not a DC2 outcome)

| | |
|---|---|
| **lock** | the DISPLAY lock, unchanged: the display decode (`sd_scale` 4.5, 0.8 m per window, A2 start term) read at the window that ends at press + 2.0 s. **The scorer lock was refused** (`g2_scorerlock`, substitution 0.38 against 0.5) and is not carried |
| path after the lock | the restricted along-line decode on the locked line, DISP_END display head flattened 0.50, phase 0.50 strides |
| switching | rule 1a arm C: at most one switch, none in the final 1.5 m, to the final-answer scorer's best line within 1.5 m of the dot after two consecutive leads over 2.0 nats, radio to t + 2.0 s only, a 0.5 s slide, marked |
| end-of-walk text | the shipped semi-bounded committed decision |
| latency and contract | 2.0 s behind real time; `reports/RENDER_RULES.md` in full |

## Verified before the freeze

- **The stand-in plumbing check** (`dc2_pipeline --stand-in`, Room A session 03 dressed as Room B, from
  its raw files): the DC2 path equals the shipped system's decisions on every evaluated walk, and the
  exploratory arm's fused pool equals Room A's own measurement; see the closing report
  `reports/BATCH_2026-09-23g_REPORT.md` for the run and its figures.
- With decoy receivers beside every recording the same equality holds (batch 23e).
- The live rig run is **BLOCKED ON OPERATOR** (no receiver attached); `scripts/live_rig_run.sh` is the one
  command, and `reports/DC2_FIELD_CHECKLIST.md` the sheet.
