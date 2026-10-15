### CR_D3b_lw0.25_vs_ref: d1sp@CR.lw0.25 against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 37.50 | 18.33 | +0.00 (+0 / +0 passes) |
| A2 | x1 | 74.17 | 50.83 | 74.17 | 67.50 | +16.67 (+0 / +20 passes) |
| A1 | x1 | 38.33 | 29.17 | 38.33 | 31.67 | +2.50 (+0 / +3 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 80.83.
Paired gain +4.79 points, 95% interval [1.88, 8.12], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 72 / 50 / 78 / 33
- lock: base 50 / 33 / 28 / 17; arm 22 / 28 / 11 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 16.666666666666664, 'arm': 0.0}]

**Decision: KEEP BASE.**
