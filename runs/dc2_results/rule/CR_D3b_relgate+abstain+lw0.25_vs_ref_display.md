### CR_D3b_relgate+abstain+lw0.25_vs_ref: d1sp@CR.relgate+abstain+lw0.25 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 40.83 | +41.67 (+23 / +27 passes) |
| A2 | x1 | 74.17 | 45.00 | 53.33 | 38.33 | -27.50 (-25 / -8 passes) |
| A1 | x1 | 38.33 | 28.33 | 40.83 | 26.67 | +0.83 (+3 / -2 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 88.54.
Paired gain +14.17 points, 95% interval [6.25, 22.29], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 67 / 61 / 61 / 17
- lock: base 50 / 33 / 28 / 22; arm 22 / 22 / 6 / 6
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 33.33333333333333, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
