### D3b_relgateA+abstain+lw0.25_vs_ref: d1sp@relgateA+abstain+lw0.25 against d1sp@ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 44.17 | +45.00 (+23 / +31 passes) |
| A2 | x1 | 73.33 | 52.50 | 63.33 | 45.00 | -17.50 (-12 / -9 passes) |
| A1 | x1 | 45.83 | 30.83 | 46.67 | 34.17 | +4.17 (+1 / +4 passes) |

Objective (weighted mean of committed + lock): base 78.54, arm 97.71.
Paired gain +19.17 points, 95% interval [11.46, 26.67], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 72 / 33; arm 61 / 61 / 72 / 39
- lock: base 50 / 33 / 28 / 22; arm 28 / 28 / 11 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
