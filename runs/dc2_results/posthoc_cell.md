## POST HOC cell: one model on A1+A2+B1, tested on A3 and B2

| test | configuration | committed [95%] | edges | lock [95%] |
|---|---|---|---|---|
| A3 | A | 88.33 [82.50, 94.17] | 33 / 100 / 100 / 100 | 65.00 [56.67, 73.33] |
| B2 | A | 57.50 [49.17, 66.67] | 100 / 83 / 50 / 17 | 20.83 [13.33, 29.17] |
| B2 | B | 65.83 [57.50, 74.17] | 100 / 100 / 83 / 33 | 30.00 [21.67, 38.33] |

Paired on the same passes (this model minus the comparator):

- A3, configuration A, against the Room-A-only model 4i_A3 (A1+A2, same harness and recipe): committed +1.67 [-2.50, 5.83] (+2 passes); lock -2.50 [-10.83, 5.00] (-3 passes); edge walks {'E_col1': -1, 'E_col5': 0, 'E_row1': 0, 'E_row5': 1}
- A3, configuration A, against the shipped fold s0102_to_s03 (A1+A2, grid-lattice 0.5 s head): committed +0.00 [-3.33, 3.33] (+0 passes); lock -4.17 [-13.33, 3.33] (-5 passes); edge walks {'E_col1': -1, 'E_col5': 0, 'E_row1': 0, 'E_row5': 0}
- B2, configuration A, against the frozen A1+A2+A3 model, item 2a: committed +7.50 [-1.67, 17.50] (+9 passes); lock +8.33 [2.48, 15.83] (+10 passes); edge walks {'E_col1': 1, 'E_col5': 1, 'E_row1': 0, 'E_row5': 0}
- B2, configuration B, against the frozen A1+A2+A3 model, item 2b: committed +8.33 [-1.67, 19.17] (+10 passes); lock +5.00 [-4.17, 14.19] (+6 passes); edge walks {'E_col1': 1, 'E_col5': 2, 'E_row1': 1, 'E_row5': 0}

Context, not tested (item 4 column ii):

- 4ii_A3, configuration A: committed 89.17 [83.33, 94.17], edges 50 / 83 / 100 / 83, lock 65.00 [56.67, 73.33]
- 4ii_B2, configuration A: committed 56.67 [47.50, 65.02], edges 100 / 83 / 50 / 17, lock 21.67 [14.17, 29.17]
- 4ii_B2, configuration B: committed 65.00 [56.67, 73.33], edges 100 / 100 / 50 / 33, lock 32.50 [24.17, 40.83]
