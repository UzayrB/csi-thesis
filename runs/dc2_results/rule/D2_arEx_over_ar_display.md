### D2_arEx_over_ar: d2p_arEx against d2p_ar (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 40.00 | 15.83 | 35.00 | 15.00 | -5.83 (-6 / -1 passes) |
| A2 | x1 | 73.33 | 49.17 | 80.83 | 53.33 | +11.67 (+9 / +5 passes) |
| A1 | x1 | 52.50 | 34.17 | 39.17 | 32.50 | -15.00 (-16 / -2 passes) |

Objective (weighted mean of committed + lock): base 80.21, arm 76.46.
Paired gain -3.75 points, 95% interval [-11.04, 3.96], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 78 / 44; arm 67 / 50 / 83 / 22
- lock: base 33 / 33 / 50 / 17; arm 39 / 44 / 56 / 17
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 44.44444444444444, 'arm': 22.22222222222222}]

**Decision: KEEP BASE.**
