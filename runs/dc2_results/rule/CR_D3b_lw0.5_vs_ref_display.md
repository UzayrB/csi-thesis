### CR_D3b_lw0.5_vs_ref: d1sp@CR.lw0.5 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 37.50 | 19.17 | +0.83 (+0 / +1 passes) |
| A2 | x1 | 74.17 | 45.00 | 74.17 | 66.67 | +21.67 (+0 / +26 passes) |
| A1 | x1 | 38.33 | 28.33 | 38.33 | 26.67 | -1.67 (+0 / -2 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 79.79.
Paired gain +5.42 points, 95% interval [1.46, 9.58], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 72 / 50 / 78 / 33
- lock: base 50 / 33 / 28 / 22; arm 0 / 17 / 6 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 0.0}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
