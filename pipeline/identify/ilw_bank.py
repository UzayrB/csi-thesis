"""ilw_bank. The link-weighting run's bank and models (`runs/identify/linkweight/PREREG_LW.md`, section 6): a bank whose
`meta.json` carries a speed estimator in place of the shipped one (`speed_m_s` and `wifi_speed` at alpha 0.5,
`wifi_speed_a0.2` on alpha 0.2's span), the other files symlinked from `bank_T4.0_v4`; and, for each listed model, its
five feature components retrained on its own rows and cfg with only the bank changed, the CNN files copied unchanged.

    PYTHONPATH=. python3 -m pipeline.identify.ilw_bank bank        # bank_T4.0_lw with the forwarded estimator
    PYTHONPATH=. python3 -m pipeline.identify.ilw_bank models      # the eight _lw models of LIST

Exploratory development, all data seen. Nothing here is adopted.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilw_cache as LC

T = 4.0
SRC = EN.bank_dir(T)
BANK_LW = os.path.join(LC.LW, "bank_T4.0_lw")
MODELS = os.path.join(LC.LW, "models")
LIST = ("loso_A1_v4", "loso_A2_v4", "loso_A3_v4", "loso_B1_v4", "loso_B2_v4", "xr_AB_v4", "xr_ABtrk_v4", "xr_A_v4")


def estimator_speeds(name: str) -> dict:
    """{alpha: array over the 1,019 rows} for one gate estimator ("V0" or "V1|P_nom" ...), from the cache."""
    from pipeline.identify import ilw_gate as G
    meta = json.load(open(os.path.join(SRC, "meta.json")))["passes"]
    rows = LC.load_all()
    return {a: np.array([G.speeds(r, meta[r["row"]], alpha=a)[name] for r in rows], float) for a in LC.ALPHAS}


def make_bank(out: str, name: str, sp: dict) -> str:
    """A bank at `out`: meta.json with the estimator's speeds, the other files symlinked read-only."""
    assert not os.path.exists(os.path.join(out, "meta.json")), f"{out} exists: never overwritten"
    meta = json.load(open(os.path.join(SRC, "meta.json")))
    for i, m in enumerate(meta["passes"]):
        m["speed_m_s"] = m["wifi_speed"] = float(sp[0.5][i])
        m["wifi_speed_a0.2"] = float(sp[0.2][i])
        m["speed_note"] = f"link weighting ({LC.LABEL}): speed estimator {name}, PREREG_LW; not the shipped speed"
    os.makedirs(out, exist_ok=True)
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    for f in ("features.npy", "maps.pkl", "feature_names.json"):
        os.symlink(os.path.relpath(os.path.join(SRC, f), out), os.path.join(out, f))
    json.dump({"label": LC.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "estimator": name, "from": SRC,
               "replaced": ["speed_m_s", "wifi_speed", "wifi_speed_a0.2"],
               "finite": {str(a): int(np.isfinite(sp[a]).sum()) for a in sp}}, open(os.path.join(out, "build.json"), "w"), indent=1)
    print(f"{time.strftime('%H:%M:%S')} bank {out}: estimator {name}", flush=True)
    return out


def retrain(model: str, bank_dir: str, out: str, estimator: str) -> str:
    """`model`'s five feature components on `bank_dir` (its own rows, cfg and seeds; alpha 0.2's column if its alpha is
    0.2, as `iv4_build.models`), the CNN files copied unchanged, a meta and a manifest."""
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    src = os.path.join(EN.ENG, "models", model)
    assert not os.path.exists(os.path.join(out, "meta_feat_cnn.json")), f"{out} exists: never overwritten"
    man = json.load(open(os.path.join(src, "manifest.json")))
    meta_old = json.load(open(os.path.join(src, "meta_feat_cnn.json")))
    a = man["alpha"]
    bank = L.load(bank_dir)
    if a != 0.5:
        bank["a"]["speed_m_s"] = np.array([m[f"wifi_speed_a{a}"] for m in json.load(open(os.path.join(bank_dir, "meta.json")))["passes"]], float)
    tr = np.load(os.path.join(src, "train_rows.npy"))
    cfg = {**meta_old["cfg"], "bank": bank_dir}
    t0 = time.time()
    Z.train(bank, tr, out, cfg, parts=("feat",), log=lambda s: None)
    for f in os.listdir(src):
        if f.startswith("cnn") and (f.endswith(".pt") or f.endswith("_norm.pkl")):
            shutil.copy(os.path.join(src, f), os.path.join(out, f))
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    json.dump({**meta_old, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "cfg": cfg, "parts": ["feat", "cnn"],
               "feature_components": f"retrained on {bank_dir} (speed estimator {estimator}; {LC.LABEL})",
               "cnn_components": f"copied unchanged from {model}", "seconds_feature_retraining": round(time.time() - t0, 1)},
              open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    json.dump({**{k: v for k, v in man.items() if k not in ("config", "bank", "derived_from", "plan", "use", "label",
                                                             "code_commit_at_training")},
               "model": os.path.basename(out), "config": cfg, "bank": bank_dir, "derived_from": model,
               "speed_estimator": estimator, "code_commit_at_training": head, "plan": "runs/identify/linkweight/PREREG_LW.md",
               "use": "the link-weighting run's identification scoring only; never deployed", "label": LC.LABEL},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{time.strftime('%H:%M:%S')} {out}: feature components {time.time() - t0:.0f} s", flush=True)
    return out


def forwarded() -> str:
    f = json.load(open(os.path.join(LC.LW, "gate.json")))["forwarded"]
    assert f, "the gate forwarded nothing"
    return f


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "bank":
        name = forwarded()
        make_bank(BANK_LW, name, estimator_speeds(name))
    elif what == "models":
        name = forwarded()
        for m in LIST:
            retrain(m, BANK_LW, os.path.join(MODELS, m.replace("_v4", "_lw")), name)
    else:
        raise SystemExit(what)
    sys.exit(0)
