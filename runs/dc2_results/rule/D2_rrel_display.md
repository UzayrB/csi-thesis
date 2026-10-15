### D2_rrel: d2p_rrel against d2p_base (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 35.83 | 18.33 | +15.83 (+12 / +7 passes) |
| A2 | x1 | 70.00 | 37.50 | 70.00 | 47.50 | +10.00 (+0 / +12 passes) |
| A1 | x1 | 26.67 | 19.17 | 46.67 | 19.17 | +20.00 (+24 / +0 passes) |

Objective (weighted mean of committed + lock): base 57.50, arm 72.92.
Paired gain +15.42 points, 95% interval [7.08, 23.12], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 83 / 39; arm 50 / 67 / 89 / 33
- lock: base 11 / 22 / 33 / 11; arm 44 / 44 / 39 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_row5', 'base': 11.11111111111111, 'arm': 0.0}]

**Decision: KEEP BASE.**
