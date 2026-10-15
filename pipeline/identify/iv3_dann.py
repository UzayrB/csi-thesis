"""iv3_dann. Engine v3's brief (`reports/identification/briefs/2026-10-01_v3-dann.md`; every rule in `runs/identify/engine/PLAN.md`,
the note of 2026-10-01 18:12), Parts 1 and 2:

    part1                     fix F alone, and fix F + fix L (the v3 reference), against engine v2
    train --fold B2 --arm X   the four CNNs at seed 0 for one walks fold: arm "base" (`idv2_core.train_cnn` itself),
                              "A0.1", "A1.0" (DANN, training domains) or "B0.1", "B1.0" (DANN, plus the test session)
    score                     every trained arm with the v3 reference's feature components and same-layout AdaBN

    PYTHONPATH=. python3 -m pipeline.identify.iv3_dann part1
    PYTHONPATH=. python3 -m pipeline.identify.iv3_dann train --fold B2 --arm A0.1 --device mps
    PYTHONPATH=. python3 -m pipeline.identify.iv3_dann score --device mps

DANN (Ganin et al., arXiv 1505.07818): a gradient-reversal domain head on the pooled 896 features (32 x 28, after the
mean over time, before dropout and the direction flag), 896 -> 64 -> ReLU -> domains, lambda(p) = lambda_max
(2 / (1 + exp(-10 p)) - 1). The identity path is exactly `idv2_core.train_cnn`'s (the same seed, generator order,
initialisation, sampling and augmentation); the head is initialised inside a forked CPU RNG and the test-session batch
(arm B) uses its own generator, so no random stream of the identity path moves.

Development evaluation, all data seen. A screen: the engine does not change here.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L
from pipeline.identify import ils_common as IL

OUT = os.environ.get("IV3_OUT", os.path.join("runs", "identify", "v3"))      # IV3_OUT: a smoke test's scratch
TAGS = ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")
ARMS = ("base", "A0.1", "A1.0", "B0.1", "B1.0")
STEPS = int(os.environ.get("IV3_STEPS", 6000))                                  # IV3_STEPS: a smoke test only
SEED = 0


def model_dir(fold: str) -> str:
    return os.path.join(EN.ENG, "models", f"loso_{fold}{IL.V2}")


def arm_dir(fold: str, arm: str) -> str:
    return os.path.join(OUT, "dann", "models", f"to{fold}", arm)


# ------------------------------------------------------------------ data

_B = {}


def bank() -> dict:
    if not _B:
        _B.update(L.load(IL.data()["bank"]))
        a = _B["a"]
        _B["layout"] = np.where(a["kind"] == "idcap", "id_spot", "home") if "kind" in a else None
    return _B


def domains(fold: str, rows: np.ndarray, arm: str) -> tuple:
    """Per training row, its domain: the session, Room B split by layout. Returns (labels, names)."""
    meta = IL.data()["meta"]
    key = np.array([m["session"] + ("|" + ("id_spot" if m["kind"] == "idcap" else "home") if m["room"] == "B" else "")
                    for m in meta])
    names = sorted(set(key[rows]))
    lab = np.array([names.index(k) for k in key[rows]])
    if arm.startswith("B"):
        names = names + [f"{fold} (test session, unlabelled)"]
    return lab, names


def stack(rows, chan):
    from pipeline.identify import idz_core as Z
    b = bank()
    Xw, dw, pw = X._stack(b["W"], rows, X._dirs(b["a"]), chan)
    st = Z.norm_stats_keyed(Xw, dw, None)
    return Z.apply_norm_keyed(Xw, dw, None, st), dw, pw, st


# ------------------------------------------------------------------ DANN training

def _grl():
    import torch

    class GRL(torch.autograd.Function):
        @staticmethod
        def forward(ctx, x, lam):
            ctx.lam = lam
            return x.view_as(x)

        @staticmethod
        def backward(ctx, g):
            return -ctx.lam * g, None
    return GRL


def train_dann(Xw, yw, dirw, dom, n_dom, seed, device, steps, lam_max, Xt=None, dirt=None):
    """`idv2_core.train_cnn` with a gradient-reversal domain head. Xt: the test session's windows (arm B)."""
    import torch
    nn = torch.nn
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    net = C.make_net(Xw.shape[1], 6).to(device)
    with torch.random.fork_rng(devices=[]):
        head = nn.Sequential(nn.Linear(C.HP["channels"][2] * C.HP["n_freq"], 64), nn.ReLU(), nn.Linear(64, n_dom)).to(device)
    opt = torch.optim.Adam(list(net.parameters()) + list(head.parameters()), lr=C.HP["lr"], weight_decay=C.HP["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=0.0)
    Xg = torch.tensor(Xw, dtype=torch.float32, device=device)
    D = nn.functional.one_hot(torch.tensor(dirw, dtype=torch.long), 2).float().to(device)
    Y = torch.tensor(yw, dtype=torch.long, device=device)
    DM = torch.tensor(dom, dtype=torch.long, device=device)
    by = [torch.tensor(np.flatnonzero(yw == c)) for c in range(6)]
    present = [c for c in range(6) if len(by[c])]
    GRL = _grl()
    if Xt is not None:
        g2 = torch.Generator().manual_seed(1000 + seed)
        XT = torch.tensor(Xt, dtype=torch.float32, device=device)
        tdom = torch.full((C.HP["batch"],), n_dom - 1, dtype=torch.long, device=device)
    net.train()
    head.train()
    for step in range(steps):
        lam = lam_max * (2.0 / (1.0 + math.exp(-10.0 * step / steps)) - 1.0)
        cls = torch.tensor(present)[torch.randint(0, len(present), (C.HP["batch"],), generator=g)]
        r = torch.rand(C.HP["batch"], generator=g)
        idx = torch.stack([by[int(c)][int(r[i] * len(by[int(c)]))] for i, c in enumerate(cls)]).to(device)
        xb = C.augment(Xg[idx], g)
        h = net.f(xb).mean(-1).flatten(1)
        loss = nn.functional.cross_entropy(net.head(net.drop(torch.cat([h, D[idx]], 1))), Y[idx])
        dl, dy = head(GRL.apply(h, lam)), DM[idx]
        if Xt is not None:
            it = torch.randint(0, len(Xt), (C.HP["batch"],), generator=g2).to(device)
            ht = net.f(C.augment(XT[it], g2)).mean(-1).flatten(1)
            dl, dy = torch.cat([dl, head(GRL.apply(ht, lam))]), torch.cat([dy, tdom])
        loss = loss + nn.functional.cross_entropy(dl, dy)
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
    net.eval()
    head.eval()
    return net, head


def domain_accuracy(net, head, Xw, dom, device) -> float:
    import torch
    ok = 0
    with torch.no_grad():
        for s in range(0, len(Xw), 1024):
            x = torch.tensor(Xw[s:s + 1024], dtype=torch.float32, device=device)
            ok += int((head(net.f(x).mean(-1).flatten(1)).argmax(1).cpu().numpy() == dom[s:s + 1024]).sum())
    return ok / len(Xw)


def train(fold: str, arm: str, device: str) -> dict:
    import torch
    b = bank()
    rows = np.load(os.path.join(model_dir(fold), "train_rows.npy"))
    lab, dnames = domains(fold, rows, arm)
    out = arm_dir(fold, arm)
    os.makedirs(out, exist_ok=True)
    te_rows = np.flatnonzero(b["a"]["session"] == fold)
    rec = {"label": IL.LABEL, "fold": f"to{fold}", "arm": arm, "seed": SEED, "steps": STEPS, "device": device,
           "domains": dnames, "networks": {}}
    t_all = time.time()
    for chan, tag in zip((None, 0, 1, 2), TAGS):
        t = time.time()
        Xn, dw, pw, st = stack(rows, chan)
        saved = pickle.load(open(os.path.join(model_dir(fold), f"{tag}_norm.pkl"), "rb"))["st"]
        assert all(np.allclose(st[k][0], saved[k][0]) and np.allclose(st[k][1], saved[k][1]) for k in st), tag
        yw = np.array([L.CLASSES.index(v) for v in b["a"]["anon"][rows]])[pw]
        dom = lab[pw]
        info = {}
        if arm == "base":
            net = C.train_cnn(Xn, yw, dw, 6, SEED, device, STEPS)
        else:
            lam = float(arm[1:])
            Xt = dt = None
            if arm.startswith("B"):
                from pipeline.identify import idz_core as Z
                Xtw, dt, _pt = X._stack(b["W"], te_rows, X._dirs(b["a"]), chan)
                Xt = Z.apply_norm_keyed(Xtw, dt, None, st)
            net, head = train_dann(Xn, yw, dw, dom, len(dnames), SEED, device, STEPS, lam, Xt, dt)
            Xd, dd = (Xn, dom) if Xt is None else (np.concatenate([Xn, Xt]), np.r_[dom, np.full(len(Xt), len(dnames) - 1)])
            acc = domain_accuracy(net, head, Xd, dd, device)
            share = np.bincount(dd, minlength=len(dnames)) / len(dd)
            info = {"domain_accuracy": round(100 * acc, 2), "majority_share": round(100 * float(share.max()), 2),
                    "one_over_n": round(100 / len(dnames), 2), "domain_shares": [round(100 * float(x), 2) for x in share]}
            torch.save(head.to("cpu").state_dict(), os.path.join(out, f"{tag}_head_seed{SEED}.pt"))
        torch.save(net.to("cpu").state_dict(), os.path.join(out, f"{tag}_seed{SEED}.pt"))
        rec["networks"][tag] = {**info, "n_windows": int(len(Xn)), "seconds": round(time.time() - t, 1)}
        print(f"{time.strftime('%H:%M:%S')} to{fold} {arm} {tag}: {rec['networks'][tag]}", flush=True)
    rec["seconds"] = round(time.time() - t_all, 1)
    IL.dump(os.path.join(out, "train.json"), rec)
    return rec


# ------------------------------------------------------------------ scoring

def cnn_outputs(fold: str, nets: dict, device: str) -> dict:
    """The seed's networks in replay order with same-layout AdaBN (fix L): per window, plain cnn3 and every adapted
    network's normalised log-probabilities (as `ils_cnn.run` with pool "layout", one seed)."""
    d = IL.data()
    maps = pickle.load(open(os.path.join(d["bank"], "maps.pkl"), "rb"))
    model = EN.Model(model_dir(fold), device)
    for tag in TAGS:
        model.nets[(tag, SEED)] = nets[tag].to(device)
    model.meta = dict(model.meta, seeds=[SEED])
    r = d["rep"][fold]
    te, paths = r["te"], r["path_used"]
    plain = np.zeros((len(te), 1, 6))
    adapt = np.zeros((len(te), len(TAGS), 1, 6))
    pools = {}
    for k, (i, path) in enumerate(zip(te, paths)):
        sess = pools.setdefault(d["a"]["layout"][i], EN.Session(model))
        Wn = C.windows(maps[i])
        for ti, tag in enumerate(TAGS):
            Xw, dw, pw = sess._cnn_input(tag, [Wn], [str(path)])
            if tag == "cnn3":
                plain[k, 0] = C.normalise_logp(C.pass_logp(model.nets[(tag, SEED)], Xw, dw, pw, 1, 6, device))[0]
            net = sess.adapted.get((tag, SEED), model.nets[(tag, SEED)])
            adapt[k, ti, 0] = C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, device))[0]
        sess.add({"features": d["X"][i], "wifi_speed": float(r["wifi_speed"][k]), "path": str(path), "maps": maps[i]})
    return {"te": te, "plain": plain, "adapt": adapt}


def load_nets(fold: str, arm: str) -> dict:
    import torch
    from pipeline.identify import idw_core as W
    return {tag: W._load_net(os.path.join(arm_dir(fold, arm), f"{tag}_seed{SEED}.pt"), 3 if tag == "cnn3" else 1)
            for tag in TAGS}


def gf() -> np.ndarray:
    """Fix F's gait matrix (the 630 columns of the re-extracted bank)."""
    d = IL.data()
    XF = np.load(os.path.join(IL.OUT, "bank_T3.0_cadF", "features.npy")).astype(np.float64)
    return XF[:, EN.v2_columns(d["names"])]


def _row(rid, ens, base_ok=None, extra=None) -> dict:
    d = IL.data()
    r = IL.score(ens, d)
    rec = {"id": rid, "label": IL.LABEL, **{k: v for k, v in r.items() if not k.startswith("_")}}
    rec["paired_vs_engine_v2"] = rec.pop("paired")
    rec["paired_vs_engine_v2_toB1"], rec["paired_vs_engine_v2_toB2"] = rec.pop("paired_toB1"), rec.pop("paired_toB2")
    if base_ok is not None:
        f = IL._flat(ens, d)
        rec["paired_vs_reference"] = EV.paired(f["ok"], base_ok["ok"], f["who"])
        for s in IL.SESS:
            m = f["fold"] == s
            rec[f"paired_vs_reference_to{s}"] = round(100 * float(f["ok"][m].mean() - base_ok["ok"][m].mean()), 2)
    if extra:
        rec.update(extra)
    rec["correct"] = [int(x) for x in r["_ok"]]
    rec["named"] = [IL.NAME[p] for p in r["_pred"]]
    IL.dump(os.path.join(OUT, "rows", f"{rid}.json"), rec)
    pv = rec.get("paired_vs_reference", rec["paired_vs_engine_v2"])
    print(f"{time.strftime('%H:%M:%S')} {rid:<34} natural {rec['natural']['pct']:6.2f}  paired {pv['pct']:+6.2f} "
          f"[{pv['ci95'][0]:+.2f}, {pv['ci95'][1]:+.2f}]  B1 {rec['toB1']:6.2f} B2 {rec['toB2']:6.2f}  PA1 {rec['pa1']:3d}  "
          f"PA2 {rec['pa2']}", flush=True)
    return rec


def reference_features() -> dict:
    """The v3 reference's feature components per session (fix F's bank, same-layout pools)."""
    from pipeline.identify import ils_feat as FT
    _ens, feats, _s = FT.lever({"G": gf(), "pool": "layout"})
    return feats


def part1() -> dict:
    from pipeline.identify import ils_cnn as CN
    from pipeline.identify import ils_feat as FT
    d = IL.data()
    G = gf()
    out = {}
    _e, fF, _s = FT.lever({"G": G})
    out["fixF"] = _row("part1.fixF", {s: IL.ensemble({**fF[s], **{c: d["rep"][s][f"c_{c}"] for c in IL.CNNC}}) for s in IL.SESS})
    fFL = reference_features()
    cl = {s: CN.components(CN.load("layout", s)) for s in IL.SESS}
    out["v3_reference"] = _row("part1.v3_reference_fixF_fixL", {s: IL.ensemble({**fFL[s], **cl[s]}) for s in IL.SESS})
    XF = np.load(os.path.join(IL.OUT, "bank_T3.0_cadF", "features.npy"))
    ci = d["names"].index("cad|all|-|-|cadence_hz")
    out["windows_without_rhythm"] = {"all": int(np.isnan(XF[:, ci]).sum()), "before_fix": int(np.isnan(d["X"][:, ci]).sum()),
                                     "of": int(len(XF))}
    IL.dump(os.path.join(OUT, "part1.json"), {k: (v if k == "windows_without_rhythm" else v["id"]) for k, v in out.items()})
    return out


def score(device: str) -> None:
    """Every arm's seed-0 networks with the v3 reference's feature components; paired against the same-seed baseline."""
    from pipeline.identify import ils_cnn as CN
    d = IL.data()
    feats = reference_features()
    ref3 = {s: CN.load("layout", s) for s in IL.SESS}                 # the v3 reference's three-seed outputs
    ref_ens = {s: IL.ensemble({**feats[s], **CN.components(ref3[s])}) for s in IL.SESS}
    ref_ok = IL._flat(ref_ens, d)
    base_ok = None
    for arm in ARMS:
        if not all(os.path.exists(os.path.join(arm_dir(f, arm), "cnn_link2_seed0.pt")) for f in IL.SESS):
            print(f"{arm}: not trained on both folds; skipped", flush=True)
            continue
        z = {f: cnn_outputs(f, load_nets(f, arm), device) for f in IL.SESS}
        for f in IL.SESS:
            np.savez(os.path.join(arm_dir(f, arm), "outputs_layout.npz"), **z[f])
        one = {s: CN.components(z[s]) for s in IL.SESS}
        ens = {s: IL.ensemble({**feats[s], **one[s]}) for s in IL.SESS}
        alone = {}
        for c in IL.CNNC:
            r = IL.score({s: one[s][c] for s in IL.SESS}, d)
            alone[c] = {"natural": r["natural"]["pct"], "named_pa1": r["pa1"]}
        dom = {f: json.load(open(os.path.join(arm_dir(f, arm), "train.json")))["networks"] for f in IL.SESS}
        extra = {"arm": arm, "cnn_components_alone": alone,
                 "domain_accuracy": {f"to{f}": {t: dom[f][t].get("domain_accuracy") for t in TAGS} for f in IL.SESS},
                 "majority_share": {f"to{f}": dom[f]["cnn3"].get("majority_share") for f in IL.SESS},
                 "one_over_n": {f"to{f}": dom[f]["cnn3"].get("one_over_n") for f in IL.SESS}}
        if arm == "base":
            base_ok = IL._flat(ens, d)
            _row("part2.base_seed0", ens, ref_ok, extra)
        else:
            _row(f"part2.{arm}_seed0", ens, base_ok, extra)
        sw = {}
        for s in IL.SESS:
            zz = {"plain": ref3[s]["plain"].copy(), "adapt": ref3[s]["adapt"].copy()}
            zz["plain"][:, 0] = z[s]["plain"][:, 0]
            zz["adapt"][:, :, 0] = z[s]["adapt"][:, :, 0]
            sw[s] = IL.ensemble({**feats[s], **CN.components(zz)})
        _row(f"part2.{arm}_swapped_into_v3_reference", sw, ref_ok, {"arm": arm})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("part1", "train", "score"))
    ap.add_argument("--fold", choices=IL.SESS)
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    a = ap.parse_args(argv)
    if a.what == "part1":
        part1()
    elif a.what == "train":
        train(a.fold, a.arm, a.device)
    else:
        score(a.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
