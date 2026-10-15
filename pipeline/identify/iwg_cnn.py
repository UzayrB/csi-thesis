"""iwg_cnn. The window and gait brief's Part C (`runs/identify/engine/PLAN.md`, the note of 2026-10-01 20:15): the networks
at seed 0, both walks folds, on the carried window's maps, against the same-seed baseline (`idv2_core.train_cnn`).

    train --arm T4.0 --fold B2 --variant base|C1|C2|C3_0.1|C3_0.5 --device mps
    comp --arm T4.0 --variant C1 --device mps     one variant's CNN components, both folds (cached; one job at a time)
    score --arm T4.0 --device mps

    base   the engine's four networks on the original maps
    C2     velocity maps (u = f x 0.123 / (2F), 0.3 to 4.3 m/s; F < 0.3 is zeros): `cnn3` on RX2 + RX3, per-link RX2 and
           RX3; RX1's per-link network is the baseline's on its original map
    C1     as C2 with the axis u / v(t) (0.2 to 3.0), and the standardised Wi-Fi speed as one scalar in each head
    C3_w   the four original networks with a supervised contrastive loss (weight w, temperature 0.1) on a projection of
           the pooled features; positives are the same person from another session in the batch

    whole  (lean-in 2.2) the four original networks, each input the whole map instead of 34-frame windows
    paceaug (lean-in 2.3) the four original networks; in training each map becomes new(f, t) = old(f / s, t x s),
           s ~ U(0.92, 1.08) per sample, from its own generator
    wholepace (lean-in, stack step 6 if both are kept) whole and paceaug together
    A variant name may end in _s1 or _s2 (seed 1 or 2; otherwise seed 0).

Every variant's identity path uses `train_cnn`'s seed and generator order; added heads start inside a forked RNG.
Development evaluation, all data seen; the engine does not change.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import re
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L
from pipeline.identify import ils_common as IL
from pipeline.identify import iwg_screen as S

OUT = os.environ.get("IWG_PARTC_OUT", os.path.join(S.OUT, "partC"))        # IWG_PARTC_OUT: a smoke test's scratch
VARIANTS = ("base", "C1", "C2", "C3_0.1", "C3_0.5")
SEED, STEPS = 0, int(os.environ.get("IWG_STEPS", 6000))                   # IWG_STEPS: a smoke test only
U_GRID = np.linspace(0.3, 4.3, 28)
R_GRID = np.linspace(0.2, 3.0, 28)
TAU = 0.1
PACE_S = (0.92, 1.08)


def parse(variant: str) -> tuple:
    """(kind, seed): "base_s2" -> ("base", 2); "C3_0.1" -> ("C3_0.1", 0)."""
    m = re.match(r"^(.*)_s(\d)$", variant)
    return (m.group(1), int(m.group(2))) if m else (variant, 0)


def _data():
    from pipeline.identify import ili_stack as LS        # the Room A folds' replays and training rows
    return LS.data()


# ------------------------------------------------------------------ inputs

def contours(arm_name: str, fold: str) -> list:
    """Per bank row, the per-frame speed v(t) on the map's frame grid (B2's contour; NaN frames filled by the walk's
    median, then the Wi-Fi speed, then 1.2 m/s)."""
    from pipeline.identify import ixa_speed as XS
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    g = S.arm(arm_name, fold)
    emp = pickle.load(open(os.path.join("runs", "identify", "final_extras", "a_data", "empty_idspot.pkl"), "rb"))
    E = XS.empty_spectrum(emp, XS.room_b_training_days(fold))
    out = []
    for i, m in enumerate(meta):
        lay = "id_spot" if m["kind"] == "idcap" else "home"
        v = S.contour(g, i, E, m["engine_path"], lay)
        n = g["maps"][i].shape[-1]
        fill = np.nanmedian(v) if np.isfinite(v).any() else (g["wifi_speed"][i] if np.isfinite(g["wifi_speed"][i]) else 1.2)
        w = np.full(n, fill)
        k = min(n, len(v))
        w[:k] = np.where(np.isfinite(v[:k]), v[:k], fill)
        out.append(np.clip(w, 0.3, 2.5))
    return out


def transform(M: np.ndarray, Fs: list, v: np.ndarray, kind: str) -> np.ndarray:
    """(3, 28, n) map -> the C1 (ratio) or C2 (velocity) axis per link; a link with F < 0.3 is all zeros."""
    out = np.zeros_like(M)
    fb = C.F_BINS
    for l, F in enumerate(Fs):
        if F < EN.F_MIN:
            continue
        for j in range(M.shape[-1]):
            u = U_GRID if kind == "C2" else R_GRID * v[j]
            out[l, :, j] = np.interp(2.0 * F * u / EN.LAMBDA, fb, M[l, :, j], left=0.0, right=0.0)
    return out


def maps_for(arm_name: str, fold: str, variant: str) -> list:
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    g = S.arm(arm_name, fold)
    if variant in ("C1", "C2"):
        vs = contours(arm_name, fold) if variant == "C1" else [None] * len(meta)
        out = []
        for i, m in enumerate(meta):
            lay = "id_spot" if m["kind"] == "idcap" else "home"
            Fs = [EN.mean_F(Lk, m["engine_path"], lay) for Lk in EN.LINKS]
            out.append(transform(g["maps"][i], Fs, vs[i], variant).astype(np.float32))
        return out
    return g["maps"]


# (tag, channels taken from which maps): "t" = the variant's transformed maps, "o" = the original maps
def nets_of(variant: str) -> dict:
    if variant in ("C1", "C2"):
        return {"cnn3": ("t", [1, 2]), "cnn_link0": ("o", [0]), "cnn_link1": ("t", [1]), "cnn_link2": ("t", [2])}
    return {"cnn3": ("o", [0, 1, 2]), "cnn_link0": ("o", [0]), "cnn_link1": ("o", [1]), "cnn_link2": ("o", [2])}


def wins(M: np.ndarray, whole: bool) -> np.ndarray:
    return M[None] if whole else C.windows(M)


def stack(maps: list, rows, chans, whole: bool = False):
    Xs, ds, ps = [], [], []
    a = IL.data()["a"]
    dirs = X._dirs({"path": a["path"]})
    for k, i in enumerate(rows):
        w = wins(maps[i], whole)[:, chans]
        Xs.append(w)
        ds.append(np.full(len(w), dirs[i]))
        ps.append(np.full(len(w), k))
    return np.concatenate(Xs), np.concatenate(ds).astype(int), np.concatenate(ps).astype(int)


# ------------------------------------------------------------------ the networks

def make_net(c_in: int, scalar: bool):
    if not scalar:
        return C.make_net(c_in, 6)
    import torch
    nn = torch.nn
    base = C.make_net(c_in, 6)                     # same construction order as `make_net`; head widened by one input

    class CNNs(nn.Module):
        def __init__(self):
            super().__init__()
            self.f, self.drop = base.f, base.drop
            self.head = nn.Linear(base.head.in_features + 1, 6)

        def forward(self, x, d, s):
            h = self.f(x).mean(-1).flatten(1)
            return self.head(self.drop(torch.cat([h, d, s[:, None]], 1)))
    return CNNs()


def pace_resample(x, s, device):
    """new(f, t) = old(f / s, t x s) per sample (frequency rows linear from F_BINS[0]; time about the centre); zero
    outside the source."""
    import torch
    B, _C, Fq, T = x.shape
    f0, df = float(C.F_BINS[0]), float(C.F_BINS[1] - C.F_BINS[0])
    fi = torch.tensor(C.F_BINS, dtype=torch.float32)
    src_i = (fi[None, :] / s[:, None] - f0) / df                           # (B, F)
    tj = torch.arange(T, dtype=torch.float32)
    c = (T - 1) / 2.0
    src_j = (tj[None, :] - c) * s[:, None] + c                             # (B, T)
    gy = 2.0 * src_i / max(Fq - 1, 1) - 1.0
    gx = 2.0 * src_j / max(T - 1, 1) - 1.0
    grid = torch.stack([gx[:, None, :].expand(B, Fq, T), gy[:, :, None].expand(B, Fq, T)], dim=-1).to(device)
    return torch.nn.functional.grid_sample(x, grid, mode="bilinear", padding_mode="zeros", align_corners=True)


def train(Xn, yw, dw, sw, sess_w, seed, device, steps, scalar=False, contrast=0.0, paceaug=False):
    """`idv2_core.train_cnn`'s loop; `scalar`: the speed scalar in the head; `contrast`: the supervised contrastive weight."""
    import torch
    nn = torch.nn
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    net = make_net(Xn.shape[1], scalar).to(device)
    params = list(net.parameters())
    if contrast:
        with torch.random.fork_rng(devices=[]):
            proj = nn.Linear(C.HP["channels"][2] * C.HP["n_freq"], 128).to(device)
        params += list(proj.parameters())
    opt = torch.optim.Adam(params, lr=C.HP["lr"], weight_decay=C.HP["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=0.0)
    Xg = torch.tensor(Xn, dtype=torch.float32, device=device)
    D = nn.functional.one_hot(torch.tensor(dw, dtype=torch.long), 2).float().to(device)
    Y = torch.tensor(yw, dtype=torch.long, device=device)
    SP = torch.tensor(sw, dtype=torch.float32, device=device)
    SS = torch.tensor(sess_w, dtype=torch.long, device=device)
    by = [torch.tensor(np.flatnonzero(yw == c)) for c in range(6)]
    present = [c for c in range(6) if len(by[c])]
    g2 = torch.Generator().manual_seed(2000 + seed)
    net.train()
    for _ in range(steps):
        cls = torch.tensor(present)[torch.randint(0, len(present), (C.HP["batch"],), generator=g)]
        r = torch.rand(C.HP["batch"], generator=g)
        idx = torch.stack([by[int(c)][int(r[i] * len(by[int(c)]))] for i, c in enumerate(cls)]).to(device)
        x0 = Xg[idx]
        if paceaug:
            s = PACE_S[0] + (PACE_S[1] - PACE_S[0]) * torch.rand(C.HP["batch"], generator=g2)
            x0 = pace_resample(x0, s, device)
        xb = C.augment(x0, g)
        h = net.f(xb).mean(-1).flatten(1)
        z = torch.cat([h, D[idx]] + ([SP[idx][:, None]] if scalar else []), 1)
        loss = nn.functional.cross_entropy(net.head(net.drop(z)), Y[idx])
        if contrast:
            e = nn.functional.normalize(proj(h), dim=1)
            sim = e @ e.T / TAU
            yb, sb = Y[idx], SS[idx]
            eye = torch.eye(len(yb), dtype=torch.bool, device=device)
            pos = (yb[:, None] == yb[None, :]) & (sb[:, None] != sb[None, :]) & ~eye
            logp = sim - torch.logsumexp(sim.masked_fill(eye, -1e9), dim=1, keepdim=True)
            has = pos.any(1)
            if has.any():
                lc = -(logp * pos).sum(1)[has] / pos.sum(1)[has]
                loss = loss + contrast * lc.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
    net.eval()
    return net


def out_dir(arm_name: str, fold: str, variant: str) -> str:
    return os.path.join(OUT, arm_name, f"to{fold}", variant)


def run_train(arm_name: str, fold: str, variant: str, device: str) -> dict:
    import torch
    from pipeline.identify import idz_core as Z
    d = _data()
    a = d["a"]
    kind, seed = parse(variant)
    rows = d["tr"][fold]
    mp = {"o": S.arm(arm_name, fold)["maps"]}
    if kind in ("C1", "C2"):
        mp["t"] = maps_for(arm_name, fold, kind)
    wifi = S.arm(arm_name, fold)["wifi_speed"]
    med = float(np.nanmedian(wifi[rows]))
    wf = np.where(np.isfinite(wifi), wifi, med)
    mu, sd = float(wf[rows].mean()), float(wf[rows].std() + 1e-9)
    sess_ids = {s: i for i, s in enumerate(sorted(set(a["session"])))}
    od = out_dir(arm_name, fold, variant)
    os.makedirs(od, exist_ok=True)
    rec = {"arm": arm_name, "fold": f"to{fold}", "variant": variant, "kind": kind, "seed": seed, "steps": STEPS,
           "speed_mu_sd": [mu, sd], "networks": {}}
    for tag, (src, chans) in nets_of(kind).items():
        if kind in ("C1", "C2") and tag == "cnn_link0":
            continue                                  # RX1's per-link network is the baseline's
        t = time.time()
        Xw, dw, pw = stack(mp[src], rows, chans, whole=kind in ("whole", "wholepace"))
        st = Z.norm_stats_keyed(Xw, dw, None)
        Xn = Z.apply_norm_keyed(Xw, dw, None, st)
        yw = np.array([L.CLASSES.index(v) for v in a["anon"][rows]])[pw]
        sw = ((wf[rows] - mu) / sd)[pw]
        ss = np.array([sess_ids[s] for s in a["session"][rows]])[pw]
        if kind in ("base", "whole"):
            net = C.train_cnn(Xn, yw, dw, 6, seed, device, STEPS)
        else:
            net = train(Xn, yw, dw, sw, ss, seed, device, STEPS, scalar=(kind == "C1"),
                        contrast=float(kind.split("_")[1]) if kind.startswith("C3") else 0.0,
                        paceaug=kind in ("paceaug", "wholepace"))
        torch.save(net.to("cpu").state_dict(), os.path.join(od, f"{tag}_seed{seed}.pt"))
        pickle.dump({"st": st}, open(os.path.join(od, f"{tag}_norm.pkl"), "wb"))
        rec["networks"][tag] = {"n_windows": int(len(Xn)), "channels": chans, "maps": src, "seconds": round(time.time() - t, 1)}
        print(f"{time.strftime('%H:%M:%S')} {arm_name} to{fold} {variant} {tag}: {rec['networks'][tag]}", flush=True)
    IL.dump(os.path.join(od, "train.json"), rec)
    return rec


# ------------------------------------------------------------------ scoring: replay order, AdaBN on same-layout pools

def load_net(arm_name, fold, variant, tag, c_in):
    import torch
    kind, seed = parse(variant)
    src = variant if not (kind in ("C1", "C2") and tag == "cnn_link0") else "base"
    net = make_net(c_in, kind == "C1" and src != "base")
    net.load_state_dict(torch.load(os.path.join(out_dir(arm_name, fold, src), f"{tag}_seed{parse(src)[1]}.pt")))
    st = pickle.load(open(os.path.join(out_dir(arm_name, fold, src), f"{tag}_norm.pkl"), "rb"))["st"]
    return net, st, kind == "C1" and src != "base"


def _fwd(net, x, d, s, scalar):
    return net(x, d, s) if scalar else net(x, d)


def adabn(net, Xo, do, so, scalar, device):
    import torch
    net2 = copy.deepcopy(net)
    bns = [m for m in net2.modules() if isinstance(m, torch.nn.BatchNorm2d)]
    for m in bns:
        m.reset_running_stats()
        m.momentum = None
    net2.eval()
    for m in bns:
        m.train()
    with torch.no_grad():
        x = torch.tensor(Xo, dtype=torch.float32, device=device)
        d = torch.nn.functional.one_hot(torch.tensor(do, dtype=torch.long), 2).float().to(device)
        s = torch.tensor(so, dtype=torch.float32, device=device)
        _fwd(net2, x, d, s, scalar)
    net2.eval()
    return net2


def logp(net, Xw, dw, sw, scalar, device) -> np.ndarray:
    import torch
    with torch.no_grad():
        x = torch.tensor(Xw, dtype=torch.float32, device=device)
        d = torch.nn.functional.one_hot(torch.tensor(dw, dtype=torch.long), 2).float().to(device)
        s = torch.tensor(sw, dtype=torch.float32, device=device)
        lp = torch.log_softmax(_fwd(net, x, d, s, scalar), 1).cpu().numpy()
    return C.normalise_logp(lp.mean(0, keepdims=True))[0]


def components(arm_name: str, fold: str, variant: str, device: str) -> dict:
    """The three CNN components of a variant's networks (one seed), in replay order, AdaBN on same-layout pools."""
    from pipeline.identify import idz_core as Z
    d = _data()
    a = d["a"]
    kind, _seed = parse(variant)
    whole = kind in ("whole", "wholepace")
    r = d["rep"][fold]
    te, paths = r["te"], r["path_used"]
    mp = {"o": S.arm(arm_name, fold)["maps"]}
    if kind in ("C1", "C2"):
        mp["t"] = maps_for(arm_name, fold, kind)
    tr = json.load(open(os.path.join(out_dir(arm_name, fold, variant), "train.json")))
    mu, sd = tr["speed_mu_sd"]
    wifi = S.arm(arm_name, fold)["wifi_speed"]
    wf = np.where(np.isfinite(wifi), wifi, float(np.nanmedian(wifi[d["tr"][fold]])))
    nets = {}
    for tag, (src, chans) in nets_of(kind).items():
        net, st, scalar = load_net(arm_name, fold, variant, tag, len(chans))
        nets[tag] = (net.to(device).eval(), st, scalar, src, chans)
    pools = {}
    out = {"plain": [], "cnn3": [], "cnn_link0": [], "cnn_link1": [], "cnn_link2": []}
    for k, (i, path) in enumerate(zip(te, paths)):
        lay = a["layout"][i]
        pool = pools.setdefault(lay, {"items": [], "adapted": {}})
        dk = 1 if str(path).endswith("_rev") else 0
        for tag, (net, st, scalar, src, chans) in nets.items():
            w = wins(mp[src][i], whole)[:, chans]
            dw = np.full(len(w), dk)
            Xn = Z.apply_norm_keyed(w, dw, None, st)
            sw = np.full(len(w), (wf[i] - mu) / sd)
            if tag == "cnn3":
                out["plain"].append(logp(net, Xn, dw, sw, scalar, device))
            out[tag].append(logp(pool["adapted"].get(tag, net), Xn, dw, sw, scalar, device))
        pool["items"].append((i, dk))
        for tag, (net, st, scalar, src, chans) in nets.items():
            cache = pool.setdefault("W", {}).setdefault(tag, ([], [], []))   # each pool window normalised once
            w = wins(mp[src][i], whole)[:, chans]
            cache[0].append(Z.apply_norm_keyed(w, np.full(len(w), dk), None, st))
            cache[1].append(np.full(len(w), dk))
            cache[2].append(np.full(len(w), (wf[i] - mu) / sd))
            pool["adapted"][tag] = adabn(net, np.concatenate(cache[0]), np.concatenate(cache[1]), np.concatenate(cache[2]),
                                         scalar, device)
        if device == "mps":
            import torch
            torch.mps.empty_cache()                   # release the varying-size blocks (memory grew without it, 1 Oct)
    o = {k: np.asarray(v) for k, v in out.items()}
    return {"cnn": C.normalise_logp(o["plain"]), "cnn_prior": C.normalise_logp(o["cnn3"]),
            "cnn_perlink_prior": C.normalise_logp(o["cnn_link0"] + o["cnn_link1"] + o["cnn_link2"]),
            "_alone": {t: o[t] for t in ("cnn_link0", "cnn_link1", "cnn_link2")}}


def comp_cache(arm_name: str, fold: str, variant: str) -> str:
    return os.path.join(out_dir(arm_name, fold, variant), "components.npz")


def run_comp(arm_name: str, variant: str, device: str, folds=None) -> None:
    """One variant's CNN components for both folds, cached. Run ONE such job at a time: five in parallel on MPS ran the
    machine out of memory on 1 Oct (22:1x)."""
    for s in (folds or IL.SESS):
        p = comp_cache(arm_name, s, variant)
        if os.path.exists(p):
            continue
        t = time.time()
        c = components(arm_name, s, variant, device)
        tmp = p[:-4] + ".tmp.npz"
        np.savez(tmp, **{k: v for k, v in c.items() if not k.startswith("_")}, **{f"alone_{k}": v for k, v in c["_alone"].items()})
        os.replace(tmp, p)                           # never a half-written cache
        S._BANK.clear()                              # one fold's bank in memory at a time
        print(f"{time.strftime('%H:%M:%S')} components {arm_name} to{s} {variant}: {time.time() - t:.0f} s", flush=True)


def cached(arm_name: str, fold: str, variant: str, device: str) -> dict:
    p = comp_cache(arm_name, fold, variant)
    if not os.path.exists(p):
        return components(arm_name, fold, variant, device)
    z = np.load(p)
    return {**{k: z[k] for k in z.files if not k.startswith("alone_")},
            "_alone": {k[6:]: z[k] for k in z.files if k.startswith("alone_")}}


def run_score(arm_name: str, device: str) -> None:
    feats, wifi = S.feat_comps(arm_name)
    dec = {s: S.arm(arm_name, s)["dec_s"] for s in IL.SESS}
    end = {s: S.arm(arm_name, s)["end_s"] for s in IL.SESS}
    base_ens, base_sw = None, None
    for variant in VARIANTS:
        if not all(os.path.exists(os.path.join(out_dir(arm_name, f, variant), "train.json")) for f in IL.SESS):
            print(f"{variant}: not trained on both folds; skipped", flush=True)
            continue
        t = time.time()
        cc = {s: cached(arm_name, s, variant, device) for s in IL.SESS}
        ens = {s: IL.ensemble({**feats[s], **{k: v for k, v in cc[s].items() if not k.startswith("_")}}) for s in IL.SESS}
        alone = {}
        for c in IL.CNNC:
            ok = np.concatenate([S._ok(cc[s][c], s, "natural") for s in IL.SESS])
            pred = np.concatenate([IL.CL[cc[s][c][S.positions(s)["natural"]].argmax(1)] for s in IL.SESS])
            alone[c] = {"natural": round(100 * float(ok.mean()), 2), "named_pa1": int((pred == "P2").sum())}
        extra = {"cnn_components_alone": alone, "seconds": round(time.time() - t, 1)}
        if variant == "base":
            r = S.score(f"C.{arm_name}.base", "C", f"{arm_name}: the same-seed baseline (seed 0; information against v3)",
                        ens, wifi, dec, end, extra=extra, mark=False)
            base_ens, base_sw = ens, r["blocks"]["natural"]["minus_S_wifi"]["pct"]
        else:
            S.score(f"C.{arm_name}.{variant}", "C", f"{arm_name}: {variant}", ens, wifi, dec, end, ref=base_ens,
                    ref_sw=base_sw, extra=extra)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("train", "comp", "score"))
    ap.add_argument("--arm", required=True)
    ap.add_argument("--fold", choices=("A1", "A2", "A3", "B1", "B2"))
    ap.add_argument("--variant", help="base, C1, C2, C3_0.1, C3_0.5, whole or paceaug; optionally _s1 or _s2")
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    ap.add_argument("--folds", nargs="+", default=None)
    x = ap.parse_args(argv)
    if x.what == "train":
        run_train(x.arm, x.fold, x.variant, x.device)
    elif x.what == "comp":
        run_comp(x.arm, x.variant, x.device, x.folds)
    else:
        run_score(x.arm, x.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
