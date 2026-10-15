## ZERO-SHOT (trained on A1+A2 only; readers from A1+A2 only; tested once on B2)

| test | committed | display lock | scorer lock | edges committed | edges display lock | resolution: correct-lock walks, along the line (median / p90, m) |
|---|---|---|---|---|---|---|
| B2 (A) | 83.33 [75.83, 89.17] | 49.17 [40.00, 58.33] | 50.00 [40.83, 59.17] | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 | 0.37 / 1.02; 0.35 / 1.00 |
| B2 (B) | 83.33 [75.83, 89.17] | 49.17 [40.00, 58.33] | 50.00 [40.83, 59.17] | 100 / 100 / 83 / 100 | 100 / 50 / 0 / 33 | 0.37 / 1.02; 0.35 / 1.00 |

Beside it: the frozen DC2 reference on B2 (trained on A1+A2+A3) 50.00 / 12.50.
