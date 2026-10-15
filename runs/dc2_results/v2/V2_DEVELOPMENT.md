# V2 development round: rotations only (rule/V2_PREREG.md, 9bb52b68...)

Committed / display lock, percent. The objective is the weighted mean of committed + lock (B1 x2).

| arm | decode | objective | B1 | A2 | A1 | pooled | edge lines, lock (col1/col5/row1/row5) | corner-pair lock errors |
|---|---|---|---|---|---|---|---|---|
| V2-B (base) | `DT1K.relgateU+abstain+a2w0.25` | 121.25 | 56.67 / 39.17 | 94.17 / 72.50 | 75.00 / 51.67 | 75.28 / 54.44 | 56/39/56/56 | 61 |
| option 3 candidate | `V2Bo3t0.8b0.25.relgateU+abstain+a2w1.0` | 123.54 | 60.83 / 39.17 | 95.83 / 72.50 | 74.17 / 51.67 | 76.94 / 54.44 | 56/39/56/56 | 61 |
| option 4 base | `DT1K.relgateU+abstain+a2w0.25` | 121.25 | 56.67 / 39.17 | 94.17 / 72.50 | 75.00 / 51.67 | 75.28 / 54.44 | 56/39/56/56 | 61 |
| option 4 candidate | `V2Bo4w0.5.relgateU+abstain+a2w0.25` | 127.50 | 56.67 / 47.50 | 94.17 / 75.00 | 75.00 / 57.50 | 75.28 / 60.00 | 50/44/61/28 | 41 |

## Option 3: the grid (12 variants; the candidate is the highest objective)

| w_A2, theta, w_ab | objective |
|---|---|
| [0.25, 0.8, 0.25] | 122.92 |
| [0.25, 0.8, 0.5] | 122.71 |
| [0.25, 0.9, 0.25] | 122.50 |
| [0.25, 0.9, 0.5] | 122.29 |
| [0.5, 0.8, 0.25] | 122.92 |
| [0.5, 0.8, 0.5] | 122.71 |
| [0.5, 0.9, 0.25] | 122.92 |
| [0.5, 0.9, 0.5] | 122.71 |
| [1.0, 0.8, 0.25] | 123.54 |
| [1.0, 0.8, 0.5] | 123.12 |
| [1.0, 0.9, 0.25] | 123.54 |
| [1.0, 0.9, 0.5] | 123.54 |

Candidate [1.0, 0.8, 0.25]; paired gain over V2-B +2.29 [-0.21, 5.00]; edge guard holds: True; **KEEP BASE**

## Option 4: the grid (3 variants, on whatever option 3 left)

| w4 | objective |
|---|---|
| 0.5 | 127.50 |
| 1.0 | 126.25 |
| 2.0 | 126.46 |

Candidate w4 = 0.5; paired gain over its base +6.25 [2.71, 9.79]; edge guard holds: False; **KEEP BASE**

- corner-pair lock errors, option 4 base: {'total': 61, 'by_pair': {'C_fwd->E_col1': 16, 'C_fwd->E_row1': 4, 'D_fwd->E_row5': 11, 'D_rev->E_col5': 8, 'E_col1->C_fwd': 6, 'E_col5->D_rev': 4, 'E_row1->C_fwd': 2, 'E_row1->E_col1': 5, 'E_row5->D_fwd': 5}}
- corner-pair lock errors, option 4 candidate: {'total': 41, 'by_pair': {'C_fwd->E_col1': 4, 'C_fwd->E_row1': 4, 'D_fwd->E_row5': 2, 'D_rev->E_col5': 5, 'E_col1->C_fwd': 6, 'E_col1->E_row1': 1, 'E_col5->D_rev': 3, 'E_row1->C_fwd': 5, 'E_row1->E_col1': 1, 'E_row5->D_fwd': 10}}
