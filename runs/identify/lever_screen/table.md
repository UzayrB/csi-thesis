| tier | lever | natural | paired [95 %] | to B1 | to B2 | PA1 | PA2 | verdict | runtime |
|---|---|---|---|---|---|---|---|---|---|
| 1.2 | one temperature per component (cross-fitted), then the sum | 38.89 | +3.33 [-4.44, +13.33] | 40.00 (+4.17) | 36.67 (+1.67) | 53 | 5 of 30 | FLAT | 0 s |
| 1.5 | session bias correction over earlier windows (same layout); assumes everyone walks equally often | 36.67 | +1.11 [-5.56, +7.78] | 34.17 (-1.67) | 41.67 (+6.67) | 57 | 5 of 30 | FLAT | 0 s |
| 2.2 | LDA with fixed shrinkage 0.7 | 36.11 | +0.56 [-1.11, +2.22] | 35.00 (-0.83) | 38.33 (+3.33) | 64 | 3 of 30 | FLAT | 21 s |
| 1.3 | the sum of ranks (ties broken by the engine's ensemble) | 35.56 | +0.00 [-10.00, +10.00] | 35.83 (+0.00) | 35.00 (+0.00) | 47 | 8 of 30 | FLAT | 0 s |
| 1.3 | features and CNNs each summed and normalised, then added | 35.56 | +0.00 [+0.00, +0.00] | 35.83 (+0.00) | 35.00 (+0.00) | 63 | 3 of 30 | FLAT | 0 s |
| 1.1 | leave out cnn_prior | 35.00 | -0.56 [-3.33, +1.67] | 35.83 (+0.00) | 33.33 (-1.67) | 58 | 4 of 30 | FLAT | 0 s |
| 1.1 | leave out et_pace_prior | 35.00 | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 63 | 3 of 30 | FLAT | 0 s |
| 1.1 | leave out rf | 35.00 | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 64 | 3 of 30 | FLAT | 0 s |
| 1.1 | leave out rf_pace_prior | 35.00 | -0.56 [-1.67, +0.00] | 35.00 (-0.83) | 35.00 (+0.00) | 63 | 3 of 30 | FLAT | 0 s |
| noise | noise floor: feature components with random_state 1 | 34.44 | -1.11 [-3.33, +0.00] | 34.17 (-1.67) | 35.00 (+0.00) | 65 | 3 of 30 | diagnostic | 20 s |
| 0.1 | fix L, the AdaBN half only (information) | 34.44 | -1.11 [-2.22, +0.00] | 34.17 (-1.67) | 35.00 (+0.00) | 62 | 2 of 30 | diagnostic | 0 s |
| 1.1 | leave out rf_prior | 34.44 | -1.11 [-2.22, +0.00] | 34.17 (-1.67) | 35.00 (+0.00) | 62 | 2 of 30 | FLAT | 0 s |
| 1.3 | the two families at equal weight: feature mean + CNN mean (addition 1) | 34.44 | -1.11 [-4.44, +2.22] | 32.50 (-3.33) | 38.33 (+3.33) | 67 | 2 of 30 | FLAT | 0 s |
| 1.3 | the sum of per-walk z-scored log-probabilities | 34.44 | -1.11 [-8.89, +7.22] | 32.50 (-3.33) | 38.33 (+3.33) | 54 | 6 of 30 | FLAT | 0 s |
| 1.5 | session bias correction over earlier windows (every one); assumes everyone walks equally often | 34.44 | -1.11 [-5.56, +3.89] | 32.50 (-3.33) | 38.33 (+3.33) | 69 | 1 of 30 | FLAT | 0 s |
| 2.2 | LDA with fixed shrinkage 0.9 | 34.44 | -1.11 [-3.89, +2.22] | 33.33 (-2.50) | 36.67 (+1.67) | 62 | 3 of 30 | FLAT | 20 s |
| 2.2 | logistic regression (L2, C 0.01) in the LDA's place | 34.44 | -1.11 [-4.44, +3.89] | 35.00 (-0.83) | 33.33 (-1.67) | 70 | 2 of 30 | FLAT | 20 s |
| noise | noise floor: all three CNN components from seed 0 only | 33.89 | -1.67 [-7.78, +4.44] | 33.33 (-2.50) | 35.00 (+0.00) | 60 | 5 of 30 | diagnostic | 0 s |
| noise | noise floor: feature components with random_state 2 | 33.89 | -1.67 [-3.89, +0.00] | 33.33 (-2.50) | 35.00 (+0.00) | 64 | 2 of 30 | diagnostic | 21 s |
| 1.4 | the per-link component from RX2 only | 33.89 | -1.67 [-5.56, +3.89] | 32.50 (-3.33) | 36.67 (+1.67) | 56 | 3 of 30 | FLAT | 0 s |
| 2.4 | families dop, spec, wav, mod only | 33.89 | -1.67 [-5.56, +2.22] | 32.50 (-3.33) | 36.67 (+1.67) | 65 | 3 of 30 | FLAT | 10 s |
| 0.1 | fix L, the feature standardisation half only (information) | 33.33 | -2.22 [-4.44, -0.56] | 32.50 (-3.33) | 35.00 (+0.00) | 59 | 1 of 30 | diagnostic | 26 s |
| 1.1 | leave out cnn | 33.33 | -2.22 [-6.11, +1.11] | 33.33 (-2.50) | 33.33 (-1.67) | 60 | 4 of 30 | FLAT | 0 s |
| 1.3 | the mean of probabilities | 33.33 | -2.22 [-5.56, +2.22] | 31.67 (-4.17) | 36.67 (+1.67) | 72 | 1 of 30 | FLAT | 0 s |
| 2.3 | feature components trained on matched rows only | 33.33 | -2.22 [-13.33, +11.67] | 32.50 (-3.33) | 35.00 (+0.00) | 52 | 11 of 30 | FLAT | 9 s |
| 2.5a | standardisation by (session, layout); test pool same layout | 33.33 | -2.22 [-4.44, -0.56] | 33.33 (-2.50) | 33.33 (-1.67) | 60 | 1 of 30 | FLAT | 14 s |
| noise | noise floor: all three CNN components from seed 1 only | 32.78 | -2.78 [-5.56, +0.00] | 31.67 (-4.17) | 35.00 (+0.00) | 60 | 4 of 30 | diagnostic | 0 s |
| 1.2 | beyond the brief: eight weights fitted jointly (cross-fitted) | 32.78 | -2.78 [-11.67, +7.22] | 35.00 (-0.83) | 28.33 (-6.67) | 56 | 3 of 30 | FLAT | 0 s |
| 2.1 | feature columns: RX2 + RX3 (418 + 3) | 32.78 | -2.78 [-8.89, +2.78] | 30.83 (-5.00) | 36.67 (+1.67) | 68 | 5 of 30 | FLAT | 16 s |
| 2.3 | matched rows (other Room B day's identification walks) weighted x2 | 32.78 | -2.78 [-8.89, +2.22] | 30.83 (-5.00) | 36.67 (+1.67) | 64 | 5 of 30 | FLAT | 24 s |
| 2.4 | families without rhy and tplacf | 32.78 | -2.78 [-7.22, +1.67] | 32.50 (-3.33) | 33.33 (-1.67) | 65 | 4 of 30 | FLAT | 13 s |
| addition 3 | information, chosen with results in view: temperature + LDA shrinkage 0.7 + bias correction (same-layout pools) | 32.78 | -2.78 [-12.78, +7.22] | 32.50 (-3.33) | 33.33 (-1.67) | 47 | 3 of 30 | diagnostic | 13 s |
| 0.1 | fix L: calibrate only on earlier windows of the same layout (features and AdaBN) | 32.22 | -3.33 [-7.22, +0.56] | 30.00 (-5.83) | 36.67 (+1.67) | 56 | 1 of 30 | FLAT | 29 s |
| 1.4 | the per-link component from RX2 + RX3 only | 32.22 | -3.33 [-7.78, -0.56] | 31.67 (-4.17) | 33.33 (-1.67) | 60 | 3 of 30 | FLAT | 0 s |
| 2.5b | standardisation per path from training statistics only | 32.22 | -3.33 [-10.00, +3.33] | 31.67 (-4.17) | 33.33 (-1.67) | 72 | 2 of 30 | FLAT | 13 s |
| 2.5d | session standardisation without the path split | 32.22 | -3.33 [-7.78, +1.11] | 30.83 (-5.00) | 35.00 (+0.00) | 72 | 2 of 30 | FLAT | 14 s |
| addition 3 | information, chosen with results in view: temperature + LDA shrinkage 0.7 + bias correction (same-layout pools) + fix L | 32.22 | -3.33 [-12.22, +5.00] | 30.83 (-5.00) | 35.00 (+0.00) | 46 | 4 of 30 | diagnostic | 12 s |
| 1.1 | leave out cnn_perlink_prior | 31.67 | -3.89 [-9.44, +2.22] | 33.33 (-2.50) | 28.33 (-6.67) | 56 | 2 of 30 | FLAT | 0 s |
| 2.1 | feature columns: RX2 only (209 + 3 step-rate) | 31.67 | -3.89 [-10.56, +2.78] | 30.83 (-5.00) | 33.33 (-1.67) | 67 | 4 of 30 | FLAT | 12 s |
| 2.3 | matched rows weighted x4 | 31.67 | -3.89 [-11.11, +2.22] | 30.00 (-5.83) | 35.00 (+0.00) | 64 | 5 of 30 | FLAT | 41 s |
| 0.3 | component rf_prior alone | 31.11 | -4.44 [-26.11, +17.22] | 29.17 (-6.67) | 35.00 (+0.00) | 28 | 9 of 30 | diagnostic | 0 s |
| 0.4 | the per-link CNN, RX1 alone | 31.11 | -4.44 [-14.44, +6.11] | 31.67 (-4.17) | 30.00 (-5.00) | 53 | 4 of 30 | diagnostic | 0 s |
| 1.1 | leave out lda_pace_prior | 31.11 | -4.44 [-10.56, +2.22] | 30.00 (-5.83) | 33.33 (-1.67) | 71 | 3 of 30 | FLAT | 0 s |
| 2.2 | the LDA component removed (retrained set) | 31.11 | -4.44 [-10.56, +2.22] | 30.00 (-5.83) | 33.33 (-1.67) | 71 | 3 of 30 | FLAT | 20 s |
| 0.3 | component cnn_perlink_prior alone | 30.56 | -5.00 [-15.56, +5.00] | 28.33 (-7.50) | 35.00 (+0.00) | 76 | 4 of 30 | diagnostic | 0 s |
| noise | noise floor: all three CNN components from seed 2 only | 29.44 | -6.11 [-9.44, -3.89] | 25.00 (-10.83) | 38.33 (+3.33) | 58 | 2 of 30 | diagnostic | 0 s |
| 0.3 | component rf_pace_prior alone | 29.44 | -6.11 [-28.89, +17.78] | 27.50 (-8.33) | 33.33 (-1.67) | 31 | 7 of 30 | diagnostic | 0 s |
| 2.5c | no session standardisation: global training statistics | 29.44 | -6.11 [-12.78, +0.00] | 28.33 (-7.50) | 31.67 (-3.33) | 67 | 2 of 30 | WORSE | 13 s |
| 0.3 | component cnn alone | 28.33 | -7.22 [-12.78, -1.67] | 26.67 (-9.17) | 31.67 (-3.33) | 64 | 4 of 30 | diagnostic | 0 s |
| 0.3 | component cnn_prior alone | 28.33 | -7.22 [-14.44, -0.56] | 26.67 (-9.17) | 31.67 (-3.33) | 72 | 4 of 30 | diagnostic | 0 s |
| 0.3 | component rf alone | 25.56 | -10.00 [-25.00, +8.33] | 27.50 (-8.33) | 21.67 (-13.33) | 40 | 3 of 30 | diagnostic | 0 s |
| 0.4 | the per-link CNN, RX2 alone | 22.78 | -12.78 [-21.11, -5.00] | 20.00 (-15.83) | 28.33 (-6.67) | 59 | 3 of 30 | diagnostic | 0 s |
| 0.3 | component lda_pace_prior alone | 21.67 | -13.89 [-30.00, -0.56] | 20.00 (-15.83) | 25.00 (-10.00) | 35 | 5 of 30 | diagnostic | 0 s |
| 0.3 | component et_pace_prior alone | 21.11 | -14.44 [-30.00, +1.11] | 20.00 (-15.83) | 23.33 (-11.67) | 31 | 6 of 30 | diagnostic | 0 s |
| 0.4 | the per-link CNN, RX3 alone | 19.44 | -16.11 [-21.67, -7.78] | 17.50 (-18.33) | 23.33 (-11.67) | 51 | 4 of 30 | diagnostic | 0 s |
