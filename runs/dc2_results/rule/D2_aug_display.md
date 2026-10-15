### D2_aug: d2p_aug against d2p_base (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 39.17 | 18.33 | +19.17 (+16 / +7 passes) |
| A2 | x1 | 70.00 | 37.50 | 65.83 | 45.00 | +3.33 (-5 / +9 passes) |
| A1 | x1 | 26.67 | 19.17 | 35.00 | 19.17 | +8.33 (+10 / +0 passes) |

Objective (weighted mean of committed + lock): base 57.50, arm 70.00.
Paired gain +12.50 points, 95% interval [4.79, 20.00], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 83 / 39; arm 67 / 39 / 83 / 28
- lock: base 11 / 22 / 33 / 11; arm 28 / 33 / 22 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_row5', 'base': 11.11111111111111, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
