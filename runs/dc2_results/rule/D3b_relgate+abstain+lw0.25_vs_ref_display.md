### D3b_relgate+abstain+lw0.25_vs_ref: d1sp@relgate+abstain+lw0.25 against d1sp@ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 40.83 | +41.67 (+23 / +27 passes) |
| A2 | x1 | 73.33 | 45.00 | 57.50 | 38.33 | -22.50 (-19 / -8 passes) |
| A1 | x1 | 45.83 | 28.33 | 42.50 | 26.67 | -5.00 (-4 / -2 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 90.00.
Paired gain +13.96 points, 95% interval [6.04, 22.09], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 72 / 33; arm 61 / 61 / 61 / 22
- lock: base 50 / 33 / 28 / 22; arm 22 / 22 / 6 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
