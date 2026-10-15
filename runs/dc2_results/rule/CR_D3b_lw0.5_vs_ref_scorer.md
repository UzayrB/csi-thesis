### CR_D3b_lw0.5_vs_ref: d1sp@CR.lw0.5 against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 37.50 | 19.17 | +0.83 (+0 / +1 passes) |
| A2 | x1 | 74.17 | 50.83 | 74.17 | 67.50 | +16.67 (+0 / +20 passes) |
| A1 | x1 | 38.33 | 29.17 | 38.33 | 27.50 | -1.67 (+0 / -2 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 80.21.
Paired gain +4.17 points, 95% interval [0.42, 8.12], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 72 / 50 / 78 / 33
- lock: base 50 / 33 / 28 / 17; arm 0 / 17 / 6 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 0.0}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 16.666666666666664, 'arm': 0.0}]

**Decision: KEEP BASE.**
