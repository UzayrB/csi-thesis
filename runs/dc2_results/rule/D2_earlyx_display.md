### D2_earlyx: d2p_earlyx against d2p_base (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 40.83 | 13.33 | +15.83 (+18 / +1 passes) |
| A2 | x1 | 70.00 | 37.50 | 70.00 | 41.67 | +4.17 (+0 / +5 passes) |
| A1 | x1 | 26.67 | 19.17 | 30.00 | 19.17 | +3.33 (+4 / +0 passes) |

Objective (weighted mean of committed + lock): base 57.50, arm 67.29.
Paired gain +9.79 points, 95% interval [2.71, 15.84], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 83 / 39; arm 50 / 56 / 83 / 33
- lock: base 11 / 22 / 33 / 11; arm 11 / 0 / 22 / 17
- guard FAILS: [{'what': 'lock', 'line': 'E_col5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
