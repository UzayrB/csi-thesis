"""ilp_cnn. The last push's representation candidates R1 and R2 (`runs/identify/lastpush/PREREG_LP.md`, section 5): the
development folds' CNN components retrained (v4 recipe: `idz_core.train`, parts "cnn", on `bank_T3.0`'s 3.0 s maps, 6,000
steps, seeds 0 to 2, mps) on transformed maps, the fold model's feature components copied unchanged; the folds scored
by the offline Session scorer with the test maps transformed the same way (R2 causally, per layout, in replay order).

- R1: each map's frequency axis divided by its own torso frequency, resampled onto 28 bins from 0.3 to 3.0 x f_torso
  (training: bank_T3.0's `f_torso`; test: the link-weighting cache's 4.0 s walking-span f_torso).
- R2: a training map minus its own session-and-layout mean frequency profile; a test map minus the mean profile of the
  earlier maps of its layout in its session (CAL-causal's pool), the training mean when there are none.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_cnn train R1 D1 [--device mps]
    PYTHONPATH=. python3 -m pipeline.identify.ilp_cnn score R1 D1 [--device mps]

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import pickle
import shutil
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilp_score as PS
from pipeline.identify import ilp_train as LT
from pipeline.identify import ixr_train as XT

FREQS = None
U = np.linspace(0.3, 3.0, 28)


def freqs() -> np.ndarray:
    from pipeline.identify import idv2_core as C
    return C.FREQS[C.KEEP_F]


def torso_norm(m: np.ndarray, ft: float) -> np.ndarray:
    f = freqs()
    out = np.empty_like(m)
    for c in range(m.shape[0]):
        for t in range(m.shape[2]):
            out[c, :, t] = np.interp(U * ft, f, m[c, :, t])
    return out


def ft_train() -> np.ndarray:
    meta = json.load(open(os.path.join(XT.BANK3, "meta.json")))["passes"]
    v = np.array([m["f_torso"] for m in meta], float)
    return np.where(np.isfinite(v), v, np.nanmedian(v))


def ft_test() -> np.ndarray:
    from pipeline.identify import ilw_cache as LC
    v = np.array([r["spans"][0.5]["f_torso"] for r in LC.load_all()], float)
    return np.where(np.isfinite(v), v, np.nanmedian(v))


def layouts(meta) -> np.ndarray:
    return np.array(["id_spot" if m["kind"] == "idcap" else "home" for m in meta])


def train_maps(cand: str, tr: np.ndarray) -> list:
    """The 3.0 s training maps of bank_T3.0, transformed (every row; only `tr` is trained on); "none" = unchanged."""
    maps = pickle.load(open(os.path.join(XT.BANK3, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(XT.BANK3, "meta.json")))["passes"]
    if cand == "none":
        return [m.copy() for m in maps]
    if cand == "R1":
        ft = ft_train()
        return [torso_norm(m, ft[i]) for i, m in enumerate(maps)]
    if cand == "R2":
        lay, ses = layouts(meta), np.array([m["session"] for m in meta])
        out = list(maps)
        for key in {(ses[i], lay[i]) for i in tr}:
            rows = [i for i in tr if (ses[i], lay[i]) == key]
            mu = np.mean([maps[i].mean(axis=2) for i in rows], axis=0)
            for i in np.flatnonzero((ses == key[0]) & (lay == key[1])):
                out[i] = (maps[i] - mu[:, :, None]).astype(np.float32)
        return out
    raise ValueError(cand)


def test_maps(cand: str, session: str, tr: np.ndarray) -> list:
    """The 4.0 s test maps of bank_T4.0_v4, transformed; R2 causally per layout in the replay order."""
    maps = pickle.load(open(os.path.join(EN.bank_dir(4.0), "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    out = list(maps)
    o = PS.LS.order(session)
    if cand in ("none", "R3"):
        return [m.copy() for m in maps]
    if cand == "R1":
        ft = ft_test()
        for i in o["te"]:
            out[i] = torso_norm(maps[i], ft[i]).astype(np.float32)
        return out
    if cand == "R2":
        maps3 = pickle.load(open(os.path.join(XT.BANK3, "maps.pkl"), "rb"))
        mu_train = np.mean([maps3[i].mean(axis=2) for i in tr], axis=0)
        lay = layouts(meta)
        pool = {}
        for i in o["te"]:
            P = pool.setdefault(lay[i], [])
            mu = np.mean(P, axis=0) if P else mu_train
            out[i] = (maps[i] - mu[:, :, None]).astype(np.float32)
            P.append(maps[i].mean(axis=2))
        return out
    raise ValueError(cand)


def model_dir(cand: str, f: str) -> str:
    return os.path.join(LT.MODELS, f"{cand}_{f}")


def train(cand: str, f: str, device: str = "mps") -> str:
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    s, src = PS.FOLDS[f]
    out = model_dir(cand, f)
    assert not os.path.exists(os.path.join(out, "meta_feat_cnn.json")), f"{out} exists"
    tr = np.load(os.path.join(src, "train_rows.npy"))
    bank3 = L.load(XT.BANK3)
    bank3["maps"] = train_maps(cand, tr)
    bank3["W"] = [C.windows(m) for m in bank3["maps"]]
    t0 = time.time()
    Z.train(bank3, tr, out, XT.cfg_cnn(), parts=("cnn",), device=device, log=print)
    for fn in os.listdir(src):
        if fn.startswith("feat_"):
            shutil.copy(os.path.join(src, fn), os.path.join(out, fn))
    meta = json.load(open(os.path.join(src, "meta_feat_cnn.json")))
    cnn_meta = json.load(open(os.path.join(out, "meta_cnn.json")))
    meta.update({"seeds": cnn_meta["seeds"], "steps": cnn_meta["steps"]})
    meta.update({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "device": device,
                 "cnn_components": f"retrained on bank_T3.0's maps transformed by {cand} ({LT.LABEL})",
                 "feature_components": f"copied unchanged from {src}", "seconds_cnn_training": round(time.time() - t0, 1)})
    json.dump(meta, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    man = json.load(open(os.path.join(src, "manifest.json")))
    man.update({"model": os.path.basename(out), "derived_from": src, "candidate": cand, "label": LT.LABEL,
                "plan": "runs/identify/lastpush/PREREG_LP.md", "use": "development fold only"})
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


def score(cand: str, f: str, device: str = "mps") -> str:
    s, src = PS.FOLDS[f]
    tr = np.load(os.path.join(src, "train_rows.npy"))
    p = os.path.join(PS.SC, f"{cand}_{f}_{s}.npz")
    np.savez(p, **PS.score(model_dir(cand, f), s, device=device, maps=test_maps(cand, s, tr)))
    return p


def train_cnn_group(Xw, yw, dirw, gw, n_cls, seed, device, steps, loss):
    """`idv2_core.train_cnn` (Adam, cosine decay, class-balanced batches of 64, the same augmentation and seeding), with
    the loss across training days (R3): GroupDRO (eta 0.1), V-REx (beta 1), CORAL (lambda 1, on the time-averaged
    convolutional features) or supervised contrastive (tau 0.1, lambda 1, positives the same person on another day)."""
    import torch
    from pipeline.identify import idv2_core as C
    HP = C.HP
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    net = C.make_net(Xw.shape[1], n_cls).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=HP["lr"], weight_decay=HP["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=0.0)
    X = torch.tensor(Xw, dtype=torch.float32, device=device)
    D = torch.nn.functional.one_hot(torch.tensor(dirw, dtype=torch.long), 2).float().to(device)
    Y = torch.tensor(yw, dtype=torch.long, device=device)
    Gr = torch.tensor(gw, dtype=torch.long, device=device)
    G = int(gw.max()) + 1
    by = [torch.tensor(np.flatnonzero(yw == c)) for c in range(n_cls)]
    present = [c for c in range(n_cls) if len(by[c])]
    q = torch.ones(G, device=device) / G
    ce = torch.nn.functional.cross_entropy
    net.train()
    for _ in range(steps):
        cls = torch.tensor(present)[torch.randint(0, len(present), (HP["batch"],), generator=g)]
        r = torch.rand(HP["batch"], generator=g)
        idx = torch.stack([by[int(c)][int(r[i] * len(by[int(c)]))] for i, c in enumerate(cls)]).to(device)
        xb = C.augment(X[idx], g)
        h = net.f(xb).mean(-1).flatten(1)
        logits = net.head(net.drop(torch.cat([h, D[idx]], 1)))
        yb, gb = Y[idx], Gr[idx]
        groups = [k for k in range(G) if bool((gb == k).any())]
        per = torch.stack([ce(logits[gb == k], yb[gb == k]) for k in groups])
        if loss == "groupdro":
            qk = q[groups] * torch.exp(0.1 * per.detach())
            q = q.clone()
            q[groups] = qk
            q = q / q.sum()
            w = q[groups] / q[groups].sum()
            L = (w * per).sum()
        elif loss == "vrex":
            L = per.mean() + 1.0 * per.var(unbiased=False)
        elif loss == "coral":
            pen = torch.zeros((), device=device)
            covs = [torch.cov(h[gb == k].T) for k in groups if int((gb == k).sum()) > 1]
            for i in range(len(covs)):
                for j in range(i + 1, len(covs)):
                    pen = pen + ((covs[i] - covs[j]) ** 2).sum() / (4 * h.shape[1] ** 2)
            L = ce(logits, yb) + 1.0 * pen
        elif loss == "supcon":
            e = torch.nn.functional.normalize(h, dim=1)
            sim = e @ e.T / 0.1
            n = len(yb)
            eye = torch.eye(n, dtype=torch.bool, device=device)
            pos = (yb[:, None] == yb[None, :]) & (gb[:, None] != gb[None, :])
            logprob = sim - torch.logsumexp(sim.masked_fill(eye, -1e9), 1, keepdim=True)
            has = pos.sum(1) > 0
            L = ce(logits, yb) + (1.0 * (-(logprob * pos).sum(1)[has] / pos.sum(1)[has]).mean() if bool(has.any()) else 0.0)
        else:
            raise ValueError(loss)
        opt.zero_grad()
        L.backward()
        opt.step()
        sched.step()
    net.eval()
    return net


def train_r3(f: str, loss: str, device: str = "mps", steps: int = 6000, seeds=(0, 1, 2), out: str = None) -> str:
    """R3: the fold's CNN components retrained (bank_T3.0's maps, untransformed) with the best F9 loss across days."""
    import torch
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    s, src = PS.FOLDS[f]
    out = out or model_dir("R3", f)
    assert not os.path.exists(os.path.join(out, "meta_feat_cnn.json")), f"{out} exists"
    os.makedirs(out, exist_ok=True)
    tr = np.load(os.path.join(src, "train_rows.npy"))
    bank3 = L.load(XT.BANK3)
    a = bank3["a"]
    gid = {d: i for i, d in enumerate(sorted(set(a["session"][tr])))}
    t0 = time.time()
    for chan in (None, 0, 1, 2):
        Xw, dw, pw, lw = Z._stack(bank3, tr, chan, False, False)
        yw = np.array([Z.CLASSES.index(v) for v in a["anon"][tr]])[pw]
        gw = np.array([gid[d] for d in a["session"][tr]])[pw]
        st = Z.norm_stats_keyed(Xw, dw, lw)
        Xn = Z.apply_norm_keyed(Xw, dw, lw, st)
        tag = "cnn3" if chan is None else f"cnn_link{chan}"
        for sd in seeds:
            net = train_cnn_group(Xn, yw, dw, gw, 6, sd, device, steps, loss)
            torch.save(net.to("cpu").state_dict(), os.path.join(out, f"{tag}_seed{sd}.pt"))
        pickle.dump({"st": st, "dir_map": W._dir_map(dw)}, open(os.path.join(out, f"{tag}_norm.pkl"), "wb"))
        print(f"{time.strftime('%H:%M:%S')} R3 {f} {tag} ({loss}) saved ({time.time() - t0:.0f} s)", flush=True)
    np.save(os.path.join(out, "train_rows.npy"), tr)
    for fn in os.listdir(src):
        if fn.startswith("feat_"):
            shutil.copy(os.path.join(src, fn), os.path.join(out, fn))
    meta = json.load(open(os.path.join(src, "meta_feat_cnn.json")))
    meta.update({"seeds": list(seeds), "steps": steps, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "device": device,
                 "cnn_components": f"retrained on bank_T3.0's maps with the {loss} loss across training days (R3; {LT.LABEL})",
                 "feature_components": f"copied unchanged from {src}", "seconds_cnn_training": round(time.time() - t0, 1)})
    json.dump(meta, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
    man = json.load(open(os.path.join(src, "manifest.json")))
    man.update({"model": os.path.basename(out), "derived_from": src, "candidate": f"R3 ({loss})", "label": LT.LABEL,
                "plan": "runs/identify/lastpush/PREREG_LP.md", "use": "development fold only"})
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


def null(device: str = "mps") -> bool:
    """The R family's null switch on D1 (PREREG_LP section 4): (i) the training path with the transform off ("none")
    gives the same CNN weights as the v4 recipe's own call (CPU, 2 steps, seed 0, exact); (ii) the scoring path with the
    transform off reproduces the v4 baseline of D1 (dev_A1_v4 on A1, mps): decisions and ensemble within 1e-9."""
    import tempfile
    import torch
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    s, src = PS.FOLDS["D1"]
    tr = np.load(os.path.join(src, "train_rows.npy"))
    same = {}
    with tempfile.TemporaryDirectory() as d:
        b0 = L.load(XT.BANK3)
        Z.train(b0, tr, os.path.join(d, "v4"), XT.cfg_cnn(), parts=("cnn",), seeds=(0,), steps=2, device="cpu", log=lambda x: None)
        b1 = L.load(XT.BANK3)
        b1["maps"] = train_maps("none", tr)
        b1["W"] = [C.windows(m) for m in b1["maps"]]
        Z.train(b1, tr, os.path.join(d, "none"), XT.cfg_cnn(), parts=("cnn",), seeds=(0,), steps=2, device="cpu", log=lambda x: None)
        for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
            a0 = torch.load(os.path.join(d, "v4", f"{tag}_seed0.pt"))
            a1 = torch.load(os.path.join(d, "none", f"{tag}_seed0.pt"))
            same[tag] = bool(all(torch.equal(a0[k], a1[k]) for k in a0))
    r = PS.score(src, s, device=device, maps=test_maps("none", s, tr))
    z = np.load(os.path.join(PS.SC, f"v4_D1_{s}.npz"))
    diff = float(np.abs(r["ensemble"] - z["ensemble"]).max())
    dec = int((r["ensemble"].argmax(1) == z["ensemble"].argmax(1)).sum())
    res = {"family": "R", "fold": "D1", "training_path_identical": same, "scoring_max_abs_diff": diff,
           "same_decisions": dec, "n": int(len(z["te"])), "device": device}
    res["PASSED"] = all(same.values()) and diff <= 1e-9 and dec == len(z["te"])
    os.makedirs(os.path.join(LT.LP, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(LT.LP, "checks", "null_switch_R_D1.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    if sys.argv[1] == "null":
        sys.exit(0 if null(sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps") else 1)
    if sys.argv[1] == "train-r3":
        train_r3(sys.argv[2], sys.argv[3], sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps")
        sys.exit(0)
    what, cand, f = sys.argv[1:4]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
    {"train": train, "score": score}[what](cand, f, dev)
    sys.exit(0)
