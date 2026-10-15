# Pre-registration: the three 1 s heads, retrained from source in stride-keyed trees

**Written 2026-09-23 (batch 23c, item 5), before anything was trained.** Operator instruction 3,
verbatim in the BRIEF: *"ONLY IF 2 IS DONE AND THE CACHE IS SAFELY STRIDE-KEYED: retrain the three
1 s heads."*

## 1. The gate, checked rather than assumed

- **Item 2 is DONE** before this runs (see `reports/QUEUE.md`). If it is not, this item waits.
- **Safely stride-keyed:** every tree this item writes carries its stride in its name
  (`artefacts_s1.0_retrain_*`, `artefacts_s0.5_retrain_*`), `y5_heads._guard` refuses any root
  without it and any shipped root by name, and the 1 s and 0.5 s feature caches live in different
  trees, so a stride-blind cache filename can no longer be served across strides. The shipped
  1 s cache (`runs/artefacts/features`, 6.3 GB) is never opened for writing.

## 2. What "retrain" means here, decided before the run

**A BASE retrain.** Same code, same seeds (0, 1, 2), same 24 epochs, same `data/windows` at the
1.0 s stride, same nine cross-day pairings. Nothing about the training set changes, for one
reason: the only change the record motivates for these heads is the entry-straddling windows, and
that was **refused** on the 0.5 s head on 2026-09-23 (paired lock -1.85 [-3.52, -0.28], entirely
below zero). Retraining the 1 s heads on a recipe that just failed is not a motivated arm.

What a base retrain answers, and nothing else answers it: **can the three 1 s heads be rebuilt
from source, in isolation, and do they reproduce the frozen weights?** Every pool figure this
project quotes rests on those weights, and they have never been regenerated.

## 3. What is measured, in order

1. **The 1 s feature cache**, rebuilt from `data/windows` into `artefacts_s1.0_retrain_shared`,
   checked file by file against the sha256 prefixes in `runs/artefacts/MANIFEST.md`.
2. **The weights**, per pairing and link: maximum absolute parameter difference (including the
   saved standardisation `mu`, `sd`) against `runs/artefacts/models`.
3. **The posteriors over the 0.5 s windows**, inferred into `artefacts_s0.5_retrain_s{0,1,2}`,
   against the frozen trees `artefacts_fh1s`, `artefacts_g1s1`, `artefacts_g1s2`: maximum
   absolute difference and argmax agreement.
4. **Only if any head differs at 3**: the five-head pool with the three retrained heads swapped
   in, scored on the lock and the committed answer over nine pairings, as the refit control.

## 4. The rule

**Nothing ships from a base retrain.** It changes no recipe. If the weights are bit-identical, the
pool is identical by construction and that is the result: the heads are reproducible, and a
future arm on them has a verified baseline. If they differ, the difference is a refit-noise
measurement and is reported with the lock and committed deltas and their intervals, and **the
frozen weights stay shipped** either way. Training nondeterminism is not a model improvement.

## 5. Prediction

The 0.5 s head's refit control (`x1_edgedisp` `base_retrained`) returned exactly 0.0 over 1077
passes, so CPU training here is deterministic. **Predicted: bit-identical weights and posteriors on
all nine pairings and all three seeds**, if and only if the 1 s feature cache also reproduces its
manifest hashes. A difference in the cache would be found first, at step 1.
