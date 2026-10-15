## ZERO-SHOT B2 (trained and fitted on A1+A2 only; tested once on B2)

| decode | committed | display lock | scorer lock | edges committed | edges display lock | dot error, correct-lock walks (median / p90, m) |
|---|---|---|---|---|---|---|
| CORRECTED: relgateU+abstain+a2w0.25, A1+A2 pace | 80.00 [72.50, 86.67] | 49.17 [40.00, 58.33] | 50.00 [40.83, 59.17] | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 | 0.41 / 1.02 |
| as first reported, 29 Sep 09:55: relgateU, shipped pace | 83.33 [75.83, 89.17] | 49.17 [40.00, 58.33] | 50.00 [40.83, 59.17] | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 | 0.37 / 1.02 |

## THE B1 GAIN on B2 under the same decoder (full A1+A2+B1 minus zero-shot A1+A2; paired on the same 120 passes)

| | committed | display lock |
|---|---|---|
| full (A1+A2+B1) | 93.33 [88.33, 97.50] | 72.50 [63.33, 80.00] |
| zero-shot (A1+A2) | 80.00 [72.50, 86.67] | 49.17 [40.00, 58.33] |
| gain (points) | +13.33 [7.48, 20.00] | +23.33 [15.83, 31.67] |
