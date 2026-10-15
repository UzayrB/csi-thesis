"""iv5_train. Engine v5's models (`prompt_identification_v5_ship.md`, step 3): for each of the nine scorecard models and
deploy_all5, `<name>_v5` beside `<name>_v4` (never touched):

- the CNN files copied from the v4 model unchanged (cnn3 and cnn_link0 to 2, seeds 0 to 2, their norms), hash-checked;
- six feature components (v4's five and hgb_pace_prior, M3) trained by `ilb_core.train_feat_b(..., m3=True)` on the
  model's own rows plus their extra windows (`ilb_core.extra_rows` for A1+A3: F7's 0.15 and 0.30 s offsets, A1's dense
  offsets, A3's 0.9 and 1.1 stretches with pace v / s); the pace column the Wi-Fi speed at the model's alpha; no A5, M2, P1
  or P2;
- a manifest with engine_version 5, the flags, the training sessions and rooms, the room weights, the v4 model it derives
  from and the code commit.

`check --models ...` (step 3's check): each scorecard model's saved feature components, loaded fresh, give exactly the
component log-probabilities of `runs/identify/roomA/comps/A1+A3+A4+M3/` on its test windows (all three windows).

    PYTHONPATH=. python3 -m pipeline.identify.iv5_train train loso_A1 loso_A2
    PYTHONPATH=. python3 -m pipeline.identify.iv5_train check loso_A1 loso_A2
    PYTHONPATH=. python3 -m pipeline.identify.iv5_train merge
    PYTHONPATH=. python3 -m pipeline.identify.iv5_train storage               # STORAGE.json and STORAGE.md (sizes, sha256)
    PYTHONPATH=. python3 -m pipeline.identify.iv5_train rebuild loso_B2 <dir> # one model trained again into <dir>, compared

Storage (Uzayr, 11 Oct): each v5 model's four RF/ET pickles (`LARGE`, 40 files, 37 to 338 MB) are kept out of git
(.gitignore) and on his Google Drive, the way data/ is kept; runs/identify/v5/STORAGE.json gives each one's size and
sha256, and `rebuild` remakes any of them exactly.

Development evaluation, all data seen.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilb_core as B
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC

BASE = "A1+A3+A4+M3"
V5D = os.path.join("runs", "identify", "v5")
CHK = os.path.join(V5D, "checks")
NAMES = ("loso_A1", "loso_A2", "loso_A3", "loso_B1", "loso_B2", "xr_AB", "xr_ABtrk", "xr_A", "xr_B1", "deploy_all5")
V5 = {"extra_feature_components": ["hgb_pace_prior"], "offsets": [0.15, 0.30],
      "room_weights": {"trained": {"A": 0.25, "B": 1.0}, "unseen": 1.0, "identification": 1.0}}
LABEL = "development evaluation, all data seen"
LARGE = ("feat_rf.pkl", "feat_rf_prior.pkl", "feat_rf_pace_prior.pkl", "feat_et_pace_prior.pkl")
STORAGE = os.path.join(V5D, "STORAGE.json")


def cnn_files(d: str) -> list:
    meta = json.load(open(os.path.join(d, "meta_feat_cnn.json")))
    tags = ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")
    return [f"{t}_norm.pkl" for t in tags] + [f"{t}_seed{s}.pt" for t in tags for s in meta["seeds"]]


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def train(name: str, root: str = None) -> str:
    """`root`: where `<name>_v5` is written (default the engine's models folder; `rebuild` passes a scratch folder)."""
    src = os.path.join(EN.ENG, "models", f"{name}_v4")
    out = os.path.join(root or os.path.join(EN.ENG, "models"), f"{name}_v5")
    assert not os.path.exists(os.path.join(out, "manifest.json")), f"{out} exists"
    man4 = json.load(open(os.path.join(src, "manifest.json")))
    tr = np.load(os.path.join(src, "train_rows.npy"))
    v, alpha = CO.speed_col(f"{name}_v4")
    assert alpha == man4["alpha"]
    fl = B.flags_of(BASE)
    t0 = time.time()
    extra = B.extra_rows(fl, tr, alpha)
    models = B.train_feat_b(PC.bank()["F"], v, tr, extra, mixup=False, m3=True)
    os.makedirs(out, exist_ok=True)
    for c, d in models.items():
        pickle.dump(d, open(os.path.join(out, f"feat_{c}.pkl"), "wb"))
    hashes = {}
    for fn in cnn_files(src):
        shutil.copy2(os.path.join(src, fn), os.path.join(out, fn))
        h4, h5 = sha(os.path.join(src, fn)), sha(os.path.join(out, fn))
        assert h4 == h5, fn
        hashes[fn] = h5
    np.save(os.path.join(out, "train_rows.npy"), tr)
    meta = json.load(open(os.path.join(src, "meta_feat_cnn.json")))
    meta.update({"feature_components": list(models), "cnn_components": f"copied unchanged from {src} (sha256 checked)",
                 "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "engine_version": 5})
    json.dump(meta, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    sessions = sorted({str(x) for x in PC.bank()["a"]["session"][tr]})
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    man = {"model": f"{name}_v5", "engine_version": 5, "T_s": 4.0, "alpha": alpha, "training_sessions": sessions,
           "training_rooms": sorted({s[0] for s in sessions}), "n_train": int(len(tr)), "n_extra_windows": int(len(extra["rows"])),
           "flags": {"A1": "training windows every 0.05 s from 0.05 to 0.50 s after the press (F7's 0.15 and 0.30 included)",
                     "A3": "training windows' frames time-stretched by 0.9 and 1.1, pace v / s",
                     "A4": "three windows per press at 0, 0.15 and 0.30 s, one CAL-causal pool, only the 0 s window joins it",
                     "M3": "a sixth feature component, HistGradientBoostingClassifier(random_state=0) on rf_pace_prior's "
                           "Prior-standardised matrix with pace (its state shared)",
                     "C2": "the feature components' weight a: 0.25 on a tracking walk in Room A when the model trained in "
                           "Room A; 1 everywhere else", "not_used": ["A5", "M2", "P1", "P2"]},
           "v5": V5, "derived_from": f"{name}_v4", "cnn_sha256": hashes, "config": man4.get("config"),
           "gs_adopted": man4.get("gs_adopted"),
           "bank": man4.get("bank"), "code_commit_at_training": head, "plan": "runs/identify/v5/QUEUE_V5.md (Uzayr's brief)",
           "configuration_source": "runs/identify/roomA/stores/split_A3.npz (the Room A run's A3-half choice)",
           "use": man4.get("use"), "label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "seconds_training": round(time.time() - t0, 1)}
    if "training_kinds" in man4:
        man["training_kinds"] = man4["training_kinds"]
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{time.strftime('%H:%M:%S')} {out}: {len(tr)} rows + {len(extra['rows'])} extra windows, "
          f"{len(models)} feature components, {len(hashes)} CNN files copied ({time.time() - t0:.0f} s)", flush=True)
    return out


def check(name: str) -> dict:
    """The saved components against the Room A run's components, every model-session and window, exactly."""
    from pipeline.identify import ilr_core as R
    m = [k for k, (mm, _s) in CO.MODELS.items() if mm == f"{name}_v4"][0]
    _mm, sessions = CO.MODELS[m]
    md = os.path.join(EN.ENG, "models", f"{name}_v5")
    models = {c: pickle.load(open(os.path.join(md, f"feat_{c}.pkl"), "rb"))
              for c in ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior", "hgb_pace_prior")}
    b = PC.bank()
    v, alpha = CO.speed_col(f"{name}_v4")
    out = {}
    for s in sessions:
        z = np.load(os.path.join(CO.REP, f"{name}_v4_{s}_T4.0.npz"))
        fd = {"te": z["te"], "path_used": z["path_used"], "layout": np.where(b["kind"][z["te"]] == "idcap", "id_spot", "home")}
        got = B.score_feat_b(models, b["F"], v, fd, B.tta_windows(s, alpha), own_speed=True)
        ref = np.load(os.path.join(R.CMP, BASE, f"{m}_{s}.npz"))
        assert np.array_equal(ref["te"], z["te"])
        d = {f"{w}|{c}": float(np.abs(a - ref[f"{w}|feat|{c}"]).max()) for w, cm in got.items() for c, a in cm.items()}
        out[s] = {"max_abs_diff": max(d.values()), "n_arrays": len(d), "n_windows": int(len(z["te"]))}
    res = {"model": f"{name}_v5", "sessions": out, "PASSED": all(v_["max_abs_diff"] == 0.0 for v_ in out.values()),
           "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(CHK, exist_ok=True)
    json.dump(res, open(os.path.join(CHK, f"train_{name}.json"), "w"), indent=1)
    print(json.dumps(res), flush=True)
    return res


def merge() -> bool:
    """checks/train.json: every scorecard model's component check passed, every model's CNN hashes equal its v4 model's."""
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "models": {}}
    ok = True
    for name in NAMES:
        md = os.path.join(EN.ENG, "models", f"{name}_v5")
        man = json.load(open(os.path.join(md, "manifest.json")))
        src = os.path.join(EN.ENG, "models", f"{name}_v4")
        hashes_ok = all(sha(os.path.join(src, fn)) == h == sha(os.path.join(md, fn)) for fn, h in man["cnn_sha256"].items())
        r = {"cnn_hashes_equal_v4": hashes_ok, "n_cnn_files": len(man["cnn_sha256"]), "engine_version": man["engine_version"]}
        if name != "deploy_all5":
            c = json.load(open(os.path.join(CHK, f"train_{name}.json")))
            r["components_equal_roomA"] = c["PASSED"]
            r["max_abs_diff"] = max(v["max_abs_diff"] for v in c["sessions"].values())
        r["PASSED"] = bool(hashes_ok and man["engine_version"] == 5 and r.get("components_equal_roomA", True))
        ok = ok and r["PASSED"]
        res["models"][name] = r
    res["PASSED"] = bool(ok)
    json.dump(res, open(os.path.join(CHK, "train.json"), "w"), indent=1)
    print(json.dumps({k: (v["PASSED"], v.get("max_abs_diff")) for k, v in res["models"].items()} | {"PASSED": res["PASSED"]}), flush=True)
    return res["PASSED"]


def storage() -> dict:
    """STORAGE.json: every v5 model's four RF/ET pickles with size and sha256, and the command that rebuilds them."""
    files = {}
    for name in NAMES:
        for fn in LARGE:
            p = os.path.join(EN.ENG, "models", f"{name}_v5", fn)
            files[p] = {"bytes": os.path.getsize(p), "sha256": sha(p)}
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": LABEL, "files": files, "n": len(files),
           "bytes": sum(f["bytes"] for f in files.values()),
           "over_github_100MiB_limit": sum(f["bytes"] > 100 * 2 ** 20 for f in files.values()),
           "rebuild": "PYTHONPATH=. python3 -m pipeline.identify.iv5_train rebuild <name> <empty folder>  (name: "
                      + ", ".join(NAMES) + "); then copy the four feat_*.pkl from <folder>/<name>_v5/ into "
                      "runs/identify/engine/models/<name>_v5/ (the command prints each sha256 against this file)"}
    json.dump(res, open(STORAGE, "w"), indent=1)
    with open(os.path.join(V5D, "STORAGE.sha256"), "w") as f:          # `shasum -a 256 -c` format, from the Code folder
        for fp, v in files.items():
            f.write(f"{v['sha256']}  {fp}\n")
    zipname = "identify_v5_models_2026-10-11.zip"
    L = ["# Engine v5's large model files: kept on Google Drive, not in git", "",
         f"Written {res['built']} by `python3 -m pipeline.identify.iv5_train storage`. Uzayr's decision (11 Oct 2026): Drive, the way "
         "`data/` is kept, not Git LFS. Development evaluation, all data seen.", "",
         f"**What:** every engine v5 model's four random-forest and extra-trees pickles, {res['n']} files, "
         f"{res['bytes'] / 1e9:.2f} GB ({res['bytes'] / 2 ** 30:.2f} GiB). {res['over_github_100MiB_limit']} of them are over GitHub's "
         "100 MiB file limit and the rest are larger than any v4 pickle (at most 34 MB); a model needs all four, so all are kept "
         "out of git together (`.gitignore`). Everything else of each `*_v5` model (CNN files, the other two feature components, "
         "manifest, rows) is in git.", "",
         "**Copy them to Drive (Uzayr, by hand; Drive for desktop is not installed here):**", "",
         "```sh", "cd ~/Desktop/UNI/2026/EEE4022S/Code",
         "shasum -a 256 -c runs/identify/v5/STORAGE.sha256        # every line OK before you zip",
         f"cut -c67- runs/identify/v5/STORAGE.sha256 | zip -@ ~/Desktop/{zipname}",
         f"unzip -t ~/Desktop/{zipname}                             # \"No errors detected\"", "```", "",
         f"Then upload `~/Desktop/{zipname}` to `My Drive/Thesis Backup Data/` (beside `room_A_2026-10-06.zip` and "
         "`room_B_2026-10-06.zip`) and wait until Drive shows it uploaded. To restore on any machine: download the zip into the "
         f"Code folder, `unzip {zipname}`, then `shasum -a 256 -c runs/identify/v5/STORAGE.sha256` (every line OK).", "",
         f"**Rebuild instead of restore:** `{res['rebuild']}`.", "",
         "| file | bytes | sha256 |", "|---|---|---|"]
    L += [f"| `{fp}` | {v['bytes']} | `{v['sha256']}` |" for fp, v in files.items()]
    open(os.path.join(V5D, "STORAGE.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps({k: res[k] for k in ("n", "bytes", "over_github_100MiB_limit")}), flush=True)
    return res


def rebuild(name: str, root: str) -> bool:
    """`name`'s v5 model trained again into `root` (`train`'s code, the same rows, seeds and bank); its four RF/ET pickles'
    sha256 against STORAGE.json."""
    os.makedirs(root, exist_ok=True)
    out = train(name, root)
    want = json.load(open(STORAGE))["files"]
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "model": f"{name}_v5", "rebuilt_in": out, "files": {}}
    for fn in LARGE:
        key = os.path.join(EN.ENG, "models", f"{name}_v5", fn)
        got = sha(os.path.join(out, fn))
        res["files"][fn] = {"sha256": got, "stored": want[key]["sha256"], "equal": got == want[key]["sha256"]}
    res["PASSED"] = all(f["equal"] for f in res["files"].values())
    json.dump(res, open(os.path.join(CHK, f"rebuild_{name}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "train":
        for nm in sys.argv[2:]:
            train(nm)
    elif what == "check":
        ok = True
        for nm in sys.argv[2:]:
            ok = check(nm)["PASSED"] and ok
        sys.exit(0 if ok else 1)
    elif what == "merge":
        sys.exit(0 if merge() else 1)
    elif what == "storage":
        storage()
    elif what == "rebuild":
        sys.exit(0 if rebuild(sys.argv[2], sys.argv[3]) else 1)
    sys.exit(0)
