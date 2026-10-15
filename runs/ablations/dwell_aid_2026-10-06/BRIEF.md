# Brief, stored verbatim (Uzayr, 6 October 2026), followed by his answers to the blockers

# Claude Code prompt: do the static dwells help the walking tracker?

The thesis needs to say whether adding the standing-sweep dwells to the training set improves the final walking tracker. First search the existing records. If nothing there answers the question for the final tracker, run one controlled ablation.

This is an evidence-gathering task, so report whatever the result is. A result where the dwells help is as useful to the thesis as one where they don't. Do not tune, re-run or select either arm to favour an outcome.

## Ground rules

- **Leave the shipped system alone.** Do not modify the shipped tracker, the live app's default model, any config, any saved weights, or any existing result or report file. Work only in a new directory, `ablations/dwell_aid_2026-10-06/`.
- **Data you can use:**
  - Room B (B1, B2) has no standing sweep, so the only dwells are from Room A.
  - The final tracker trains on the walking windows of A1, A2 and B1.
  - Never train on A3 or B2 data of any kind. They are evaluation sessions only.
- **Names.** Participant names are fine in code and run files, as usual. PA codes are for the report only.

## Part A: search the existing records first

Search the code repository for:
- the methods ledgers (`METHODS_TRIED_*`);
- the model state records (`MODEL_STATE_*`);
- the tracking-methods ledger;
- `reports/`;
- the dated records and handoffs;
- run logs.

Report the following, each with its file path and the exact numbers.

1. **Walking plus dwells against walking alone.** Find any run that trained on walking plus standing dwells and compared it with walking alone, evaluated on walking windows. For each run give:
   - the date and file;
   - the training and test sessions;
   - the model;
   - the metric and the numbers;
   - whether it matches the final tracker's architecture, training sessions and evaluation.
2. **The 18 September dwell-only transfer result.** A regressor trained only on the dwells transferred to walking. Give:
   - its training and test sessions;
   - the metric and the number;
   - the walking-trained comparator on the same test set.
3. **The 14 September frozen model** (`MODEL_STATE_2026-09-14`, 1.49 m):
   - confirm it was trained on the standing grid;
   - say what it was evaluated on (dwells or walking, and which session);
   - say whether it beat the centre-guess and random-cell baselines.
4. **The 13 to 14 September ledger comparison** (walking 1.53 m against dwells 1.81 m): state what each arm trained on and what it was tested on.

If item 1 finds a run that matches the final tracker's architecture, training sessions and evaluation, **stop after Part A and report.** Otherwise do Part B.

## Part B: controlled ablation (only if Part A found nothing usable)

### B1. Write the plan before anything trains

Write `ablations/dwell_aid_2026-10-06/PLAN.md` containing everything in this section. If the repository is under git, commit it before any training run starts, and report the commit hash.

### B2. Identify what the dwells can feed

Identify which trained components of the final tracker learn from position labels, such as the per-link regressors. Add the dwells only to those components. The twelve-line decoder, the motion gate and its 0.431 threshold stay unchanged in every arm.

### B3. Arms

**W (reference).** The final tracker exactly as shipped:
- the same code, conditioning, windowing and hyperparameters;
- the same epochs;
- the same training windows (walking, A1, A2, B1).

**W+D (primary).** Identical to W, except the training set also includes every standing-sweep window from A1 and A2:
- apply the protocol's discards (drop the first 2 s and the last 1 s of each 10 s dwell);
- label each window with its cell centre;
- pass it through exactly the same conditioning and windowing as the walking windows.

**W+D_cap (secondary).** As W+D, except the dwell windows are randomly subsampled with a fixed, logged seed to at most the number of walking training windows, so the dwells cannot swamp the walking data.

### B4. Seeds

Use five training seeds per arm, the same five in every arm.

### B5. Evaluation

Evaluate on the final tracker's test walking windows, and state which sessions they are (expected A3 and B2). Use the same evaluation path that produces the shipped tracker's reported numbers. If those numbers come from the live app replaying recorded sessions, evaluate each arm the same way, by loading its weights into the replay path without changing the app's default model.

Report two metrics, each per room and pooled:
1. the shipped tracker's headline metric (the semi-constrained mode, with a single start press);
2. the per-window regression error in metres, as a median and a mean.

### B6. Decision rule

The rule is fixed before the runs. The primary comparison is W+D against W on the headline metric, pooled.

- Compute the per-seed paired difference (W+D minus W), its mean, and a 95 % t-interval over the five seeds.
- **Dwells help** only if the whole interval lies below zero, meaning lower error with the dwells.
- **No measurable gain** if the interval includes zero.
- **Dwells hurt** if the whole interval lies above zero.

Report W+D_cap and the secondary metrics, but they do not change the verdict.

## Report back

1. **Part A findings**, each with its file path and numbers.
2. **If Part B ran:**
   - the `PLAN.md` commit hash, or a note that the repository isn't under git;
   - the window counts in each arm (walking and dwell);
   - a table of per-seed values and the mean ± SD, for each arm, metric and room;
   - the paired difference, its interval, and the verdict under the rule.
3. **What the thesis can and cannot claim**, in two plain sentences.
4. **Any deviation** from this plan, and why.

---

## Uzayr's answers, 6 October 2026 (after Part A)

"I can't restore as I deleted it. Try reduce what you need to add, be as efficient as you can without messing up my
folder structure and creating unnecessary fluff. Train for as short as possible to get me my answer. Caffeinate, and
if the capped arm is redundant remove it. Go for it and give me an ETA as well as a laptop status update."
