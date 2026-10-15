### CR_D3b_relgateA+abstain+lw0.25_vs_ref: d1sp@CR.relgateA+abstain+lw0.25 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 40.83 | +41.67 (+23 / +27 passes) |
| A2 | x1 | 74.17 | 45.00 | 60.00 | 48.33 | -10.83 (-17 / +4 passes) |
| A1 | x1 | 38.33 | 28.33 | 44.17 | 29.17 | +6.67 (+7 / +1 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 94.17.
Paired gain +19.79 points, 95% interval [11.88, 28.12], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 61 / 61 / 83 / 33
- lock: base 50 / 33 / 28 / 22; arm 28 / 28 / 11 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
