# Provenance of zsf_B2 (relgateU+abstain+a2w0.25): what every component was fitted on

Training sessions 01, 02; test B2; allowed for fitted components: 01, 02, 03.

| component | sessions | recordings | source | outside allowed |
|---|---|---|---|---|
| head half (weights and input standardisation) | 01, 02 | 12 | cells/zsf_B2/train_half.json (2250 windows) | none |
| position head (half) | 01, 02 | 12 | copied from 4i_A3 (its train_half.json) | none |
| head fh1s (weights and input standardisation) | 01, 02 | 12 | cells/zsf_B2/train_fh1s.json (1061 windows) | none |
| head g1s1 (weights and input standardisation) | 01, 02 | 12 | cells/zsf_B2/train_g1s1.json (1061 windows) | none |
| head g1s2 (weights and input standardisation) | 01, 02 | 12 | cells/zsf_B2/train_g1s2.json (1061 windows) | none |
| head g100 (weights and input standardisation) | 01, 02 | 12 | cells/zsf_B2/train_g100.json (1061 windows) | none |
| reader rows of 01 (A2 region reader and abstain reader) | 01, 02 | 6 | rows of 01 made by heads s02_to_s01 (trained on 02) | none |
| reader rows of 02 (A2 region reader and abstain reader) | 01, 02 | 6 | rows of 02 made by heads s01_to_s02 (trained on 01) | none |
| test-side reader heads (V0: position and g25) | 01, 02 | 0 | s0102_to_sB2V0: the pooled twin's per-link heads | none |
| A2 start term (LDA) and the reader (LDA) | 01, 02 | 12 | fitted on the reader rows above | none |
| relative gate G0 | 01, 02 | 12 | pd_decode.gate_reference(train, room_a_only=True) | none |
| chain prior | 01, 02 | 12 | n2_arms.fit_chain_prior(st, train) | none |
| emission cell marginal | 01, 02 | 12 | the training windows' positions | none |

**The test recording's own causal statistics** (not fitted on other data):

- relative RSSI reference (per link mean): each test recording of B2: its own idle windows ending before its first press
- relative gate g_rec (median band energy): each test recording of B2: its own idle windows ending before its first press
- AdaBN statistics of the reader heads: each test recording of B2: its own idle windows ending before its first press

**Design constants** (not fitted per model):

| constant | sessions it was set on | provenance |
|---|---|---|
| pace prior N(1.3034, 0.1125) m/s (was N(1.298, 0.123)) | 01, 02 | RECOMPUTED 29 Sep from the A1+A2 tape anchors by stage1_pace's own method (240 passes; the same method gives 1.2982 / 0.1230 on A1+A2+A3's 360, the old constant). Changes within 0.02 m/s, so no re-selection (Uzayr) |
| display cap 0.80 m per window | 01, 02, 03 | swept 2026-09-21 in f3_render on the s0102_to_s03 demonstration pairing, A3's 120 walks (git 8590d47): SET ON A3. Kept (Uzayr); the A3 LOCK is optimistic, the B2 lock is the headline; committed answers do not read it |
| display spread 4.5 | 01, 02, 03 | introduced 2026-09-20 with the 3 m/s ceiling in a3_lock / f3_render on the s0102_to_s03 pairing's session-03 walks (git 0b18ee6), no independent tuning recorded: SET ON A3 or untraceable. Treated as the cap |
| decoder configuration (margin, null_self, exit, clock, bout prior) and null rule (-7.5, gate weight 4.0, threshold 0.431) | 01, 02 | rb2_decoder, selected for s0102_to_s03 on its training side (A1+A2) |
| veto threshold 0.01 / abstain threshold 0.90 and weight 0.25 | 01, 02 | u2_useit selection folds s01_to_s02 and s02_to_s01 |
| A2 start-term weight 0.25, abstain in place of the veto, and every other decode option | 01, 02, B1 | chosen on the development rotations (A1+A2->B1, A1+B1->A2, A2+B1->A1): design choices |

**The decode's file trace** (runs/dc2_results/verify/own/zsf_B2/clean.json): networks opened:

- s0102_to_sB2: trained on 01, 02
- s0102_to_sB2V0: trained on 01, 02
- s01_to_s02: trained on 01
- s02_to_s01: trained on 02

**PASS**
