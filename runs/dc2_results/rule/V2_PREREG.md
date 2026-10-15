# V2_PREREG: the second development round, pre-registered 29 September 2026, 22:48 SAST

**Status of this file.** It was written before any V2 network was trained and before any V2 decode. Its
SHA-256 is in `V2_PREREG.md.sha256` beside it, and it is **never edited afterwards**. Anything learnt later
goes into the V2 report, labelled as learnt later.

**What stays frozen.** The 15:39 model does not change:
- `rule/FINAL_CONFIG.md` and its hash (360053d7...);
- every file of that model.

All V2 work is written under new names: `runs/dc2_results/v2/`, `pipeline/constrained/pd_v2.py`,
`pipeline/constrained/pd_dt.py`, and decode prefixes beginning `V2` or `DT`.

**The instruction this implements:** Uzayr's message of 29 September, part B, which is tracking only.

## 1. The rotations and the rule (unchanged from rounds 1 and 2)

**The rotations:**
- A1+A2 -> B1, weight 2;
- A1+B1 -> A2, weight 1;
- A2+B1 -> A1, weight 1.

**Their networks** are the `d4c_fuse_*` cells: the final architecture, with a shared encoder, learned
fusion, augmentation and relative RSSI, and all five heads. These are the cells round 2 confirmed the
shared encoder on.

**The rule:** `pipeline/constrained/pd_rule.py`, as in rounds 1 and 2.

- **Objective:** the weighted mean over the rotations of (committed + display lock), configuration A.
- **Paired gain:** per pass, 100 x the change in (committed + lock). It is the weighted mean of the
  per-rotation means. Its 95 percent interval comes from a bootstrap that resamples passes within each
  rotation, 1,000 draws, seed 0.
- **The edge guard:** on the pooled rotation passes, for the committed answer and for the lock
  separately, no edge line (E_col1, E_col5, E_row1, E_row5) may fall to 0, or to half its base recall
  or less.
- **ADOPT** only if the guard holds and the interval's lower bound is above 0. Otherwise keep the base.

**Held fixed in every arm, and never re-tuned:**
- **The pace:** the frozen N(1.30341, 0.11255) m/s. It was fitted on A1+A2 tape anchors, so on two
  rotations it includes the validation session's passes. It is one constant shared by every arm here,
  so no paired comparison depends on it.
- **The reader map:** the clean reader map (`pd_clean`).
- **The rest of the configuration:** every other setting of `FINAL_CONFIG.md`.

## 2. The base, V2-B: the 15:39 configuration with the transit and late-entry terms in 0.5 s units

**Why a fix is needed.** The decoder rebuild of 17 September ran at a 1 s stride
(`rebuild_common.STRIDE_S = 1.0`), and three of its quantities are counted in 1 s windows. The 0.5 s
decoder reads them unchanged, because `decoder2.py` takes Dt = 1.0 from `common.py`:
1. **late-entry reach and cost:** v x Dt per window;
2. **the minimum transit windows:** ceil(distance / 1.298 m/s / 1 s), from
   `runs/constrained/rb0_preflight/transit_geometry.json`;
3. **the transit clock's saturation:** clock_max = 8 windows, which was 8 s.

**V2-B puts all three in 0.5 s units:**
1. `decoder2.DT = 0.5`, so a late entry reaches v x 0.5 s x (k + 1) and costs 1 nat per 0.5 s window of
   arc it leaves unexplained;
2. the minimum transit windows are ceil(min_time_s / 0.5 s), from the same `min_time_s`, written to a
   NEW file, `runs/dc2_results/v2/transit_geometry_s05.json`. The rb0 file is untouched;
3. clock_max = 16 windows: the same 8 s.

**Why item 3 is included.** With the clock left at 8 windows (4 s at 0.5 s), 42 of the 144 line-to-line
transits need 9 to 11 windows, more than the clock can ever count. Those entries would become impossible,
which is a new constraint, not a unit conversion.

**How the base is treated.** V2-B is a bug fix, applied in V2 whatever item 2's disclosure shows. It is
not judged by the rule; the rule judges the options on it.

## 3. Option 3: the start-of-walk readers on the final recipe

### 3.1 New networks

All trained on 0.5 s press-aligned walk windows, calibration recordings excluded (`walking_windows`),
with the final recipe:
- **encoder and fusion:** one shared LinkCNN encoder over the 3 links with a learned fusion head;
- **inputs:** relative RSSI; input standardisation per link and channel on the training windows;
- **augmentation:** RSSI offset +-5 dB, CSI scale x0.25 to x1.5, time shift +-0.25 s, noise sd 0.1;
- **optimiser:** Adam, learning rate 1e-3, weight decay 1e-4, batch 64, seed 0.

| network | kind | training sessions | epochs |
|---|---|---|---|
| g25 cell posterior | `pd_train.fit_link(..., arch="fuse")`, exactly as `fin_A3`'s `half` head | {A1}, {A2}, {B1} | 24 |
| position regression | shared encoder; fused head PositionHead(192 -> 64 -> 2); per-link auxiliary PositionHead(64 -> 64 -> 2) shared by the links; loss = smooth-L1(fused) + mean over links of smooth-L1(auxiliary) | {A1}, {A2}, {B1}, {A1,A2}, {A1,B1}, {A2,B1}, {A1,A2,B1} | 20 |

That is ten new networks, in `runs/dc2_results/v2/nets/`.

**Existing final-recipe g25 networks,** reused byte for byte:

| sessions | network |
|---|---|
| {A1,A2} | `d4c_fuse_0102_to_B1`'s `half` head; for the zero-shot model's own rows, `zsf_B2`'s `half` head |
| {A1,B1} | `d4c_fuse_01B1_to_02`'s `half` head |
| {A2,B1} | `d4c_fuse_02B1_to_01`'s `half` head |
| {A1,A2,B1} | `fin_A3`'s `half` head |

### 3.2 Where each row comes from: cross-fitted exactly as pd_clean

A training session's rows come from networks trained only on the model's OTHER training sessions. The
test or validation rows come from networks trained on the model's own training sessions. **No network
that saw a session makes that session's training rows, and the validation session is never in a
reader's training.**

| model | A1 rows | A2 rows | B1 rows | test / validation rows |
|---|---|---|---|---|
| rotation A1+A2 -> B1 | {A2} | {A1} | (validation) | B1 from {A1,A2} |
| rotation A1+B1 -> A2 | {B1} | (validation) | {A1} | A2 from {A1,B1} |
| rotation A2+B1 -> A1 | (validation) | {B1} | {A2} | A1 from {A2,B1} |
| final (A1+A2+B1) | {A2} | {A1} | {A1,A2} | A3 and B2 from {A1,A2,B1} |
| zero-shot (A1+A2) | {A2} | {A1} | not used | B2 from {A1,A2} (g25: `zsf_B2`'s own head) |

### 3.3 The A2 region reader, rebuilt

**Features:** `q3_startclf.features`'s 26 features:
- read from the position network's fused (x, y) and its three per-link auxiliary (x, y);
- over the windows whose end lies in [press - 2.0 s, press + 1.0 s].

**Classifier:** StandardScaler, then LDA (lsqr, automatic shrinkage), over the 8 start regions.

**Term:** w_A2 x (log P(the line's start region) - the mean over regions of log P), as `q4_arms.start_terms`.

### 3.4 The abstain reader, rebuilt

**AdaBN.** Every BatchNorm of the g25 network's encoder is recomputed on the recording's idle windows
that end at or before its first press (`u1_adapt.calibration_indices`), with the links folded into the
batch as the encoder folds them. It needs at least 20 such windows; with fewer, the network is used
unadapted, as `u1_adapt`.

**Features.** The 64-d embedding of each link, concatenated to 192, for the windows ending in
[press - 2.0 s, press]. The feature vector is their mean plus the last window: 384 numbers.

**Classifier:** StandardScaler, then LDA (lsqr, automatic shrinkage), over the 8 regions.

**Term:** if the top probability is at least theta, w_ab x the centred log P; otherwise 0, as
`u2_useit.term_abstain`.

### 3.5 The grid and the selection (rotations only)

**The 12 variants:** w_A2 in {0.25, 0.5, 1.0}, theta in {0.80, 0.90}, w_ab in {0.25, 0.5}.

**Selection:**
1. The candidate is the variant with the highest rotation objective. Ties go to the first in the order
   w_A2, then theta, then w_ab, each ascending.
2. `pd_rule` then compares V2-B with V2-B + the candidate.
3. **Option 3 is adopted only if the rule says ADOPT.**

**Disclosed:** choosing the best of 12 on the same rotations it is then judged on is optimistic. That is
the practice of rounds 1 and 2.

## 4. Option 4: separating the lines that share a start corner, at the lock

**The groups:**
- SW: C_fwd, E_col1, E_row1;
- SE: D_rev, E_col5;
- NW: D_fwd, E_row5.

**Features.** For each pass, the final-recipe g25 network's 192-d embedding (3 links x 64) of windows
lo, lo + 1 and lo + 2, concatenated in time order: 576 numbers.
- lo is the first walk window, the one centred on the start press. Window lo + 2 ends at press + 2.0 s.
- No AdaBN; relative RSSI.
- The rows are cross-fitted from the g25 networks of the table in 3.2.

**Classifier.** StandardScaler, then LDA (lsqr, automatic shrinkage), over the 7 corner lines. It is
trained on the training sessions' passes of those lines only.

**The lock rule.** This applies to a pass whose display-lock line f lies in a corner group g.
1. For each l in g: P(l | g) = P(l) / (the sum over g of P). T[l] = w4 x (log P(l | g) - the mean over
   g of log P(. | g)).
2. S[l] is the lock score the display decode already computes: `viterbi_last_scores` at the lock's last
   window, from the same decode, with evidence ending at press + 2.0 s.
3. **The lock becomes argmax over l in g of (S[l] + T[l]).**

**What it leaves alone:**
- a lock outside the three groups;
- the committed decision;
- the scorer lock.

After the lock, the dot follows the chosen line's restricted decode (`locked_chain_path`, the same
horizon and the same entry distribution restricted to that line).

**The constraints, checked in code:**
- evidence ends at press + 2.0 s;
- the lock time stays 2.0 s (V3);
- signal only: no pace feature, elapsed time or dead reckoning;
- every statistic comes from training sessions;
- cross-fitted as 3.2.

**The grid:** w4 in {0.5, 1.0, 2.0}. The candidate is the highest rotation objective; ties go to the
smaller w4. `pd_rule` then compares (the configuration left after option 3's decision) with the same
plus option 4. **Option 4 is adopted only if the rule says ADOPT.**

## 5. Order

1. V2-B.
2. Option 3 on V2-B.
3. Option 4 on whatever option 3 leaves.

**No other options, and nothing else re-tuned.**

## 6. The stop rule

**If neither option is adopted, stop.** No A3 or B2 decode is made. The 15:39 model stays the result,
and V2-B alone is not tested.

## 7. If something is adopted

1. **Build the zero-shot V2 the same way,** with every new component fitted on A1+A2 only (3.2's last
   row).
2. **Freeze** `rule/FINAL_CONFIG_V2.md` and its SHA-256 **before any test decode.**
3. **Run the provenance pre-checks:**
   - the main model fails on anything touching A3 or B2;
   - the zero-shot fails on anything touching B1 or B2.
4. **Run ONE test** (fin_A3, fin_B2, zsf_B2 under V2), then the post-checks on each decode's file trace.
   **This is the FOURTH look at A3 and B2,** and the report says so.
5. **V2 becomes the headline by this rule, whether its test figures are higher or lower.** V2 and the
   15:39 model are never chosen between on test results.
6. **Write `reports/MODEL_FINAL_TRACKING_V2.md`:**
   - both models side by side;
   - the corner-pair lock confusion counts, before and after.
7. **Then run the verification:**
   - the substitution and shuffled-radio checks;
   - the rebuild from hashes, with the list from traces;
   - the teaching pack, regenerated with P1 to P6.
8. **Hold the live port, the renders and any commit of V2** until Uzayr has reviewed it.

## 8. Compute

- **The GPU:** only when Identification's jobs leave it free, by its handover ("ready", then "GPU free",
  then "done"). Its processes are never paused, killed or touched by tracking.
- **The CPU:** otherwise, one tracking job at a time.
