### CR_D2_earlyx: d2p_earlyx@CR.ref against d2p_base@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 40.83 | 13.33 | +15.83 (+18 / +1 passes) |
| A2 | x1 | 70.83 | 37.50 | 66.67 | 41.67 | +0.00 (-5 / +5 passes) |
| A1 | x1 | 21.67 | 19.17 | 25.83 | 19.17 | +4.17 (+5 / +0 passes) |

Objective (weighted mean of committed + lock): base 56.46, arm 65.42.
Paired gain +8.96 points, 95% interval [1.88, 15.00], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 89 / 39; arm 44 / 50 / 83 / 33
- lock: base 11 / 22 / 33 / 11; arm 11 / 0 / 22 / 17
- guard FAILS: [{'what': 'lock', 'line': 'E_col5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
