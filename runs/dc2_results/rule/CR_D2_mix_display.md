### CR_D2_mix: d2p_mix@CR.ref against d2p_base@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 29.17 | 15.00 | +5.83 (+4 / +3 passes) |
| A2 | x1 | 70.83 | 37.50 | 70.83 | 43.33 | +5.83 (+0 / +7 passes) |
| A1 | x1 | 21.67 | 19.17 | 35.00 | 22.50 | +16.67 (+16 / +4 passes) |

Objective (weighted mean of committed + lock): base 56.46, arm 65.00.
Paired gain +8.54 points, 95% interval [1.46, 15.42], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 89 / 39; arm 39 / 39 / 78 / 22
- lock: base 11 / 22 / 33 / 11; arm 39 / 39 / 28 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_row5', 'base': 11.11111111111111, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
