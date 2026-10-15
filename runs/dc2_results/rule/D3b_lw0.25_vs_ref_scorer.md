### D3b_lw0.25_vs_ref: d1sp@lw0.25 against d1sp@ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 37.50 | 18.33 | +0.00 (+0 / +0 passes) |
| A2 | x1 | 73.33 | 52.50 | 73.33 | 67.50 | +15.00 (+0 / +18 passes) |
| A1 | x1 | 45.83 | 30.83 | 45.83 | 31.67 | +0.83 (+0 / +1 passes) |

Objective (weighted mean of committed + lock): base 78.54, arm 82.50.
Paired gain +3.96 points, 95% interval [1.04, 7.08], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 72 / 33; arm 72 / 50 / 72 / 33
- lock: base 50 / 33 / 28 / 22; arm 22 / 28 / 11 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
