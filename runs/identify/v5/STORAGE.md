# Engine v5's large model files: kept on Google Drive, not in git

Written 2026-10-11 14:23:06 by `python3 -m pipeline.identify.iv5_train storage`. Uzayr's decision (11 Oct 2026): Drive, the way `data/` is kept, not Git LFS. Development evaluation, all data seen.

**What:** every engine v5 model's four random-forest and extra-trees pickles, 40 files, 5.78 GB (5.38 GiB). 27 of them are over GitHub's 100 MiB file limit and the rest are larger than any v4 pickle (at most 34 MB); a model needs all four, so all are kept out of git together (`.gitignore`). Everything else of each `*_v5` model (CNN files, the other two feature components, manifest, rows) is in git.

**Copy them to Drive (Uzayr, by hand; Drive for desktop is not installed here):**

```sh
cd ~/Desktop/UNI/2026/EEE4022S/Code
shasum -a 256 -c runs/identify/v5/STORAGE.sha256        # every line OK before you zip
cut -c67- runs/identify/v5/STORAGE.sha256 | zip -@ ~/Desktop/identify_v5_models_2026-10-11.zip
unzip -t ~/Desktop/identify_v5_models_2026-10-11.zip                             # "No errors detected"
```

Then upload `~/Desktop/identify_v5_models_2026-10-11.zip` to `My Drive/Thesis Backup Data/` (beside `room_A_2026-10-06.zip` and `room_B_2026-10-06.zip`) and wait until Drive shows it uploaded. To restore on any machine: download the zip into the Code folder, `unzip identify_v5_models_2026-10-11.zip`, then `shasum -a 256 -c runs/identify/v5/STORAGE.sha256` (every line OK).

**Rebuild instead of restore:** `PYTHONPATH=. python3 -m pipeline.identify.iv5_train rebuild <name> <empty folder>  (name: loso_A1, loso_A2, loso_A3, loso_B1, loso_B2, xr_AB, xr_ABtrk, xr_A, xr_B1, deploy_all5); then copy the four feat_*.pkl from <folder>/<name>_v5/ into runs/identify/engine/models/<name>_v5/ (the command prints each sha256 against this file)`.

| file | bytes | sha256 |
|---|---|---|
| `runs/identify/engine/models/loso_A1_v5/feat_rf.pkl` | 145866336 | `919ecf45e77d1cd5d8d2109af5fd430f889da2b3c91cfbe5a20ae9d9dfa8e2cf` |
| `runs/identify/engine/models/loso_A1_v5/feat_rf_prior.pkl` | 152059462 | `231e3522b45648852422bd27de607758d126d2e8d92caf4d56d7107e166d4d70` |
| `runs/identify/engine/models/loso_A1_v5/feat_rf_pace_prior.pkl` | 151100096 | `4743c1339e49e02a54441af8a0a6616acf185a3d722f787df9026c1840f982a4` |
| `runs/identify/engine/models/loso_A1_v5/feat_et_pace_prior.pkl` | 335898076 | `26d238234b26a025ff2911940c15f4e7499dc0dadb7e92c21e95ad5d46797f01` |
| `runs/identify/engine/models/loso_A2_v5/feat_rf.pkl` | 146535424 | `ea25cee081bcf7be8081ee4b08fef934ba0746930bf8194df59143cf27fba206` |
| `runs/identify/engine/models/loso_A2_v5/feat_rf_prior.pkl` | 153261446 | `c7b566c5306e1e7e2db122dd7dfa2e691e9e098e00156156905f9d7076a410c1` |
| `runs/identify/engine/models/loso_A2_v5/feat_rf_pace_prior.pkl` | 152674816 | `08873c660e47265f2b1a16e4e52b0348683a516630600c6b849084feae416cbb` |
| `runs/identify/engine/models/loso_A2_v5/feat_et_pace_prior.pkl` | 338678364 | `c083205ab507db8368450823569377b30905baf7dd42fc8967b8924679582d94` |
| `runs/identify/engine/models/loso_A3_v5/feat_rf.pkl` | 145760832 | `112f62ba4eefe827e09f1276e55028c433922f5083d77e670e4f9aaf2c6ee75e` |
| `runs/identify/engine/models/loso_A3_v5/feat_rf_prior.pkl` | 152817254 | `64c262a1b9947b1b2ef4c28028febc63299701f47294eaede9d575fcdd643859` |
| `runs/identify/engine/models/loso_A3_v5/feat_rf_pace_prior.pkl` | 152486880 | `141bbd08da5b89b9b32cb08c84b64b61f0ff7cac611ebf483d8a9187f87acca2` |
| `runs/identify/engine/models/loso_A3_v5/feat_et_pace_prior.pkl` | 337705756 | `e9ebba9028143e7f2f41d8f2a525a153b272846a43fc4e39da4c227afaea48ba` |
| `runs/identify/engine/models/loso_B1_v5/feat_rf.pkl` | 108781344 | `f9a17885d2352fecb8685c2f6d8c5c815c9a333b6087ab191087c303fb71dbae` |
| `runs/identify/engine/models/loso_B1_v5/feat_rf_prior.pkl` | 113895910 | `7f1eaef4b5ff8310b926470829db72519f7c5e9142f4e7a0997e7a11704a3ef5` |
| `runs/identify/engine/models/loso_B1_v5/feat_rf_pace_prior.pkl` | 113544256 | `e61ea7e06d56bac0a3c67c458631b509f7e21c57593ffb43c3c962aa8119928b` |
| `runs/identify/engine/models/loso_B1_v5/feat_et_pace_prior.pkl` | 247898780 | `fa91bfe84e975d6f5522bdb80b3ba5bf663e6e321e20bb3d490287cbc659baf9` |
| `runs/identify/engine/models/loso_B2_v5/feat_rf.pkl` | 115164672 | `65540d15d2395b65a37325f625e4d49cf674519d009ffed1d7aa8ea5fae596e1` |
| `runs/identify/engine/models/loso_B2_v5/feat_rf_prior.pkl` | 122508038 | `0a87d669be34ffa140b6cabeb1e8a4592884ba9811034bb3a24ecc44adb0ca49` |
| `runs/identify/engine/models/loso_B2_v5/feat_rf_pace_prior.pkl` | 121957696 | `6ad3db685879907cc9ee8aa00d90162fd9d263c023eb7091cc4093ce934222f7` |
| `runs/identify/engine/models/loso_B2_v5/feat_et_pace_prior.pkl` | 269411292 | `afe73da8f36e6fb50785e37b74e131013ea12815c750ed9a48091f5210ac431d` |
| `runs/identify/engine/models/xr_AB_v5/feat_rf.pkl` | 93818144 | `105eff78c8c0166d3895c3a54b66e9c0679a2c9b10447c6c1c12effb67786b6b` |
| `runs/identify/engine/models/xr_AB_v5/feat_rf_prior.pkl` | 99474566 | `c80e63ba2b90214190cd01e20bd99f9591d9ba08bcff4d5001a372f146715b03` |
| `runs/identify/engine/models/xr_AB_v5/feat_rf_pace_prior.pkl` | 98988288 | `c034f9dec3c478998453a1b1712d6457e6c806d21a8aff7ed6d34cf2a7425746` |
| `runs/identify/engine/models/xr_AB_v5/feat_et_pace_prior.pkl` | 220521276 | `34638020301d967d49a7aa921322be43230bdfee6dd672b8bafe9b9e1fc17442` |
| `runs/identify/engine/models/xr_ABtrk_v5/feat_rf.pkl` | 54440960 | `ffe4ae527c818a44543d73d5f07eb8ff26c593a8fec7fa4971fbc2fd73481f4c` |
| `runs/identify/engine/models/xr_ABtrk_v5/feat_rf_prior.pkl` | 59741446 | `1f663d02700c4e1842d01b9da6386f40ef8775e7ca1e1323865ebfab7581ba83` |
| `runs/identify/engine/models/xr_ABtrk_v5/feat_rf_pace_prior.pkl` | 59454528 | `adb5991a73926c750c962f50c2371fa693a7e18c648f9198cb17b049da82bea8` |
| `runs/identify/engine/models/xr_ABtrk_v5/feat_et_pace_prior.pkl` | 130257116 | `e80e67e7cef8fbc7cc42a08ea0501da7cdfe8befd1cd22298ec342779521c8fe` |
| `runs/identify/engine/models/xr_A_v5/feat_rf.pkl` | 36774740 | `cd98c14034d070ae459495c05a970925618f95da01ec111e8854a04a72772f3b` |
| `runs/identify/engine/models/xr_A_v5/feat_rf_prior.pkl` | 38609274 | `e0345dbbf25aa9b66956977e0cb7595217792d8049023e634ddf4ba3656ac5c8` |
| `runs/identify/engine/models/xr_A_v5/feat_rf_pace_prior.pkl` | 38617588 | `b2cbde9ee49275a126d090db0652490592e1ce3ff3b80fb919e554e5f658edfa` |
| `runs/identify/engine/models/xr_A_v5/feat_et_pace_prior.pkl` | 84510492 | `031a98b846e2548e38808d9026cb9957ec9325ca523a79174d52cb0f7ab91a4b` |
| `runs/identify/engine/models/xr_B1_v5/feat_rf.pkl` | 51627412 | `3347d50a0ffdc3c5919822bdb7e96485a62370d342d5e49002bdc6311c1466d3` |
| `runs/identify/engine/models/xr_B1_v5/feat_rf_prior.pkl` | 51475066 | `3ea8617f3c68e7a8b7fbfdd47bfa3b0ad598518f58276a36c8bce0f5c1067eb4` |
| `runs/identify/engine/models/xr_B1_v5/feat_rf_pace_prior.pkl` | 50879700 | `9f1a331937018f1a3f35dafa183576d493f1d6c1bc9adf7de6c32c14a0f69ee1` |
| `runs/identify/engine/models/xr_B1_v5/feat_et_pace_prior.pkl` | 120029052 | `33f21a193b61e55b6664a8cc9ccab68ae4200b1db7f31b0fa8c67568e6749614` |
| `runs/identify/engine/models/deploy_all5_v5/feat_rf.pkl` | 168129696 | `e77f97c985e84af328a6a2a48d53fa24e4da44f72de62ab90be3278b64f86449` |
| `runs/identify/engine/models/deploy_all5_v5/feat_rf_prior.pkl` | 176475462 | `0c38043aa6197d73ff5fcc11dc20f18b256e61463182021fa206416ce9193474` |
| `runs/identify/engine/models/deploy_all5_v5/feat_rf_pace_prior.pkl` | 175690368 | `a433d5cd1e11de63611e4a7361dbd0317088487d9d9ffb81c69da3a738229c6d` |
| `runs/identify/engine/models/deploy_all5_v5/feat_et_pace_prior.pkl` | 387994652 | `0bfc2e352f865c84eba8c6663cd6a202ba617c2deb3c1e6d32a412b536568341` |
