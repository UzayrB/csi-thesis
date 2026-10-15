"""pd_v2: the V2 development round (runs/dc2_results/rule/V2_PREREG.md, SHA-256 9bb52b68..., hashed
29 September 2026 22:49 before anything here was trained or decoded).

    python3 -m pipeline.constrained.pd_v2 train_all            # the ten networks of V2_PREREG 3.1, GPU if free
    python3 -m pipeline.constrained.pd_v2 train --net pos_s0102 # one of them

Part 1 (this section): the networks of V2_PREREG 3.1, all on the final recipe:
  - g25 cell posteriors on {A1}, {A2}, {B1}: `pd_train.fit_link(..., arch="fuse")` exactly as fin_A3's
    half head (24 epochs, aug, relative RSSI);
  - position regressions on the seven session sets: `SharedPosNet`, one shared LinkCNN encoder over the
    three links, a fused PositionHead(192 -> 64 -> 2) and a per-link auxiliary PositionHead(64 -> 64 -> 2)
    shared by the links; loss = smooth-L1(fused) + mean over links of smooth-L1(auxiliary); 20 epochs;
    trained by `fit_pos_shared`, which is `pd_train.fit_link`'s loop step for step (the same seeding,
    permutations, augmentation generator and standardisation), with this loss.

Training reads fin_A3's view (sessions 01, 02 and B1, B1's calibration recording absent) through
`pd_cells.env_for(fin_A3, "half", "train")`, with relative RSSI installed before the data modules import.
Nothing is written anywhere except runs/dc2_results/v2/nets/. Every frozen file of the 15:39 model is
only read.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
V2 = J(RES, "v2")
NETS_DIR = J(V2, "nets")
PREREG = J(RES, "rule", "V2_PREREG.md")
PREREG_SHA = "9bb52b6851f0fa7cb1b1a87a4ca931019de4a2c924d3c981c887b28877c558f8"
SESS_NAME = {"01": "A1", "02": "A2", "B1": "B1"}
#: V2_PREREG 3.1: name -> (kind, training sessions)
NETS = {"g25_s01": ("g", ("01",)), "g25_s02": ("g", ("02",)), "g25_sB1": ("g", ("B1",)),
        "pos_s01": ("pos", ("01",)), "pos_s02": ("pos", ("02",)), "pos_sB1": ("pos", ("B1",)),
        "pos_s0102": ("pos", ("01", "02")), "pos_s01B1": ("pos", ("01", "B1")),
        "pos_s02B1": ("pos", ("02", "B1")), "pos_s0102B1": ("pos", ("01", "02", "B1"))}
ORDER = ["g25_s01", "g25_s02", "g25_sB1", "pos_s01", "pos_s02", "pos_sB1", "pos_s0102", "pos_s01B1",
         "pos_s02B1", "pos_s0102B1"]


def prereg_ok() -> None:
    import hashlib
    with open(PREREG, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    if h != PREREG_SHA:
        raise SystemExit(f"REFUSED: V2_PREREG.md does not match its hash ({h})")


def net_path(name: str) -> str:
    return J(NETS_DIR, f"v2_{name}.pt")


# ------------------------------------------------------------------------------ the position network

def shared_pos_net(n_links: int = 3, in_channels: int = 2):
    import torch.nn as nn
    from pipeline.constrained.heads import PositionHead
    from pipeline.constrained.link_cnn import LinkCNN, encode_links
    from pipeline.constrained.pd_arch import CHANNELS, DROPOUT, EMBED

    class SharedPosNet(nn.Module):
        """One LinkCNN shared by the links; a fused position head and a per-link auxiliary one."""

        def __init__(self):
            super().__init__()
            self.n_links = int(n_links)
            self.encoder = LinkCNN(in_channels=in_channels, embed_dim=EMBED, channels=CHANNELS, dropout=DROPOUT)
            self.head = PositionHead(EMBED * n_links, 64, DROPOUT)
            self.aux = PositionHead(EMBED, 64, DROPOUT)

        def forward_all(self, x):
            z = encode_links(self.encoder, x)                                  # (B, L, 64)
            fused = self.head(z.reshape(z.shape[0], -1))                       # (B, 2)
            aux = self.aux(z.reshape(-1, z.shape[-1])).reshape(z.shape[0], z.shape[1], -1)   # (B, L, 2)
            return fused, aux

        def forward(self, x):
            fused, aux = self.forward_all(x)
            return (fused, aux) if self.training else fused

        def embed(self, x):
            return encode_links(self.encoder, x)

    return SharedPosNet()


def fit_pos_shared(X: np.ndarray, y: np.ndarray, seed: int, opts: dict) -> tuple:
    """`pd_train.fit_link`'s loop for a shared position network: the same seed_all, link statistics,
    Adam, permutation generator, option generator, augmentation and noise; 20 epochs (E_REG)."""
    import torch
    import torch.nn.functional as F
    from pipeline.constrained.common import E_REG, seed_all
    from pipeline.constrained.nets import BATCH, LR, WEIGHT_DECAY, device
    from pipeline.constrained.pd_arch import link_stats
    from pipeline.constrained.pd_train import NOISE_SD, _augment
    mu, sd = link_stats(X)
    seed_all(seed)
    model = shared_pos_net(X.shape[1], X.shape[2])
    dev = device()
    model = model.to(dev)
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    rng = np.random.default_rng(seed)
    arng = np.random.default_rng(seed + 7919)
    yt = torch.from_numpy(np.asarray(y, np.float32))
    Xs = torch.from_numpy(X.astype(np.float32))
    mu_t, sd_t = torch.from_numpy(mu.astype(np.float32)), torch.from_numpy(sd.astype(np.float32))
    epochs = int(opts.get("epochs") or E_REG)
    hist = []
    for ep in range(epochs):
        model.train()
        order = rng.permutation(len(Xs))
        tot, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            xb = Xs[idx]
            if opts.get("aug"):
                xb = _augment(xb, arng, float(opts.get("rssi_unit", 1.0)))
            xb = (xb - mu_t) / sd_t
            if opts.get("aug"):
                xb = xb + NOISE_SD * torch.from_numpy(arng.standard_normal(tuple(xb.shape)).astype(np.float32))
            optim.zero_grad()
            fused, aux = model(xb.to(dev))
            yb = yt[idx].to(dev)
            # .contiguous(): the MPS backend refuses smooth-L1 on a strided slice; the values are the same
            loss = F.smooth_l1_loss(fused, yb) + sum(F.smooth_l1_loss(aux[:, li].contiguous(), yb)
                                                     for li in range(aux.shape[1])) / aux.shape[1]
            loss.backward()
            optim.step()
            tot += float(loss.detach().cpu())
            nb += 1
        hist.append(round(tot / max(nb, 1), 5))
        if dev.type == "mps":
            torch.mps.empty_cache()
    model.eval()
    return model, mu, sd, {"epochs_run": epochs, "train_loss_by_epoch": hist, "opts": dict(opts)}


# ----------------------------------------------------------------------------------------- training

def train_inner(name: str) -> int:
    """One network, in its own process under fin_A3's training environment."""
    prereg_ok()
    kind, sessions = NETS[name]
    from pipeline.constrained import pd_cells as PC
    PC.install_rrel()                                   # before the data modules import, as pd_cells' own order
    t0 = time.time()
    c = PC.cfg("fin_A3", "train")
    from pipeline.constrained.artefacts import _save
    from pipeline.constrained.dataset import walking_windows
    from pipeline.constrained.grid import cell_index
    from pipeline.constrained.pd_arch import stack_all
    from pipeline.constrained.nets import device
    tr = walking_windows(list(sessions))
    stems = set(tr.stem.tolist())
    for s in sessions:
        leak = stems & PC.cal_stems(s)
        assert not leak, f"calibration recordings among the training windows: {leak}"
    assert set(tr.session.tolist()) == set(sessions), (set(tr.session.tolist()), sessions)
    assert not (set(sessions) & {"03", "B2"}), "a test session in V2 training"
    X = stack_all(tr.X, tr.rssi)
    opts = {"aug": True, "rssi_unit": 1.0}
    rec = {"net": name, "kind": kind, "sessions": list(sessions), "windows": int(len(tr)),
           "by_session": {s: int(np.sum(tr.session == s)) for s in sessions}, "device": str(device()),
           "prereg_sha256": PREREG_SHA, "recipe": "final: shared encoder + learned fusion, aug, relative RSSI"}
    if kind == "g":
        from pipeline.constrained.pd_train import fit_link
        y = cell_index(tr.xy, 25)
        model, mu, sd, r = fit_link(X, y, "g", 25, 0, dict(opts), sessions=tr.session, arch="fuse")
        r.pop("_snapshots", None)
        meta = {"kind": "g", "out_dim": 25, "n_links": X.shape[1], "in_channels": X.shape[2], "epochs": 24,
                "seed": 0, "tag": f"v2_{name}", "link": None, "arch": "fuse", "pd_train": r}
    else:
        model, mu, sd, r = fit_pos_shared(X, tr.xy, 0, dict(opts))
        meta = {"kind": "pos", "out_dim": 2, "n_links": X.shape[1], "in_channels": X.shape[2], "epochs": 20,
                "seed": 0, "tag": f"v2_{name}", "arch": "fuse_pos", "record": r}
    meta["v2"] = rec
    os.makedirs(NETS_DIR, exist_ok=True)
    p = net_path(name)
    if os.path.exists(p):
        raise SystemExit(f"REFUSING to overwrite {p}")
    _save(model.cpu(), mu, sd, p + ".tmp", meta)
    os.replace(p + ".tmp", p)
    rec["minutes"] = round((time.time() - t0) / 60.0, 2)
    with open(J(NETS_DIR, f"v2_{name}.json"), "w", encoding="utf-8") as f:
        json.dump({**rec, "train_record": r if kind == "pos" else {k: v for k, v in r.items() if k != "val_history"}},
                  f, indent=1, default=str)
    print(f"[{time.strftime('%H:%M:%S')}] {name}: {rec['windows']} windows, {rec['minutes']} min on {rec['device']}",
          flush=True)
    return 0


def train_all() -> int:
    prereg_ok()
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    env = dict(PC.env_for(PC.cfg("fin_A3", "train"), "half", "train"), PYTHONPATH=REPO_ROOT)
    for name in ORDER:
        if os.path.exists(net_path(name)):
            print(f"{name}: exists, skipped", flush=True)
            continue
        print(f"[{time.strftime('%H:%M:%S')}] START {name}", flush=True)
        code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_v2", "train", "--net", name],
                               cwd=REPO_ROOT, env=env)
        if code:
            raise SystemExit(f"V2 TRAINING FAILED at {name} (exit {code})")
    print(f"[{time.strftime('%H:%M:%S')}] V2 TRAINING DONE", flush=True)
    return 0


# ======================================================================== part 2: the reader rows (V2_PREREG 3.2 to 4)

ROWS_DIR = J(V2, "rows")
#: V2_PREREG 3.2: {cell: {session: the source network set its rows come from}}
ROWS_SRC = {
    "d4c_fuse_0102_to_B1": {"01": "s02", "02": "s01", "B1": "s0102"},
    "d4c_fuse_01B1_to_02": {"01": "sB1", "B1": "s01", "02": "s01B1"},
    "d4c_fuse_02B1_to_01": {"02": "sB1", "B1": "s02", "01": "s02B1"},
    "fin_A3": {"01": "s02", "02": "s01", "B1": "s0102", "03": "s0102B1"},
    "fin_B2": {"01": "s02", "02": "s01", "B1": "s0102", "B2": "s0102B1"},
    "zsf_B2": {"01": "s02", "02": "s01", "B2": "s0102zs"},
}
#: the g25 network of each set: new (v2 nets) or reused byte for byte (V2_PREREG 3.1)
G25_SRC = {"s01": ("v2", "g25_s01"), "s02": ("v2", "g25_s02"), "sB1": ("v2", "g25_sB1"),
           "s0102": ("cell", "d4c_fuse_0102_to_B1"), "s01B1": ("cell", "d4c_fuse_01B1_to_02"),
           "s02B1": ("cell", "d4c_fuse_02B1_to_01"), "s0102B1": ("cell", "fin_A3"), "s0102zs": ("cell", "zsf_B2")}
POS_SRC = {k: f"pos_{'s0102' if k == 's0102zs' else k}" for k in G25_SRC}
SET_SESSIONS = {"s01": ("01",), "s02": ("02",), "sB1": ("B1",), "s0102": ("01", "02"), "s01B1": ("01", "B1"),
                "s02B1": ("02", "B1"), "s0102B1": ("01", "02", "B1"), "s0102zs": ("01", "02")}
CORNER = {"SW": ("C_fwd", "E_col1", "E_row1"), "SE": ("D_rev", "E_col5"), "NW": ("D_fwd", "E_row5")}
CORNER_LINES = tuple(l for g in CORNER.values() for l in g)
GROUP_OF = {l: g for g, ls in CORNER.items() for l in ls}


def rows_path(netset: str, session: str) -> str:
    return J(ROWS_DIR, f"{netset}__{session}.npz")


def _g25_file(netset: str) -> str:
    kind, nm = G25_SRC[netset]
    if kind == "v2":
        return net_path(nm)
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(nm)
    return J(c["tree"]("half"), "models", f"{c['heads_tag']}_g25_e24_s0_link0.pt")


def _load_g25(netset: str):
    import torch
    from pipeline.constrained.pd_arch import SharedNet
    d = torch.load(_g25_file(netset), map_location="cpu", weights_only=False)
    assert d.get("arch") == "fuse" and d["out_dim"] == 25, (netset, d.get("arch"), d.get("out_dim"))
    m = SharedNet(d["n_links"], d["out_dim"], d["arch"], d["in_channels"])
    m.load_state_dict(d["state_dict"])
    return m.eval(), np.asarray(d["mu"]), np.asarray(d["sd"])


def _load_pos(netset: str):
    import torch
    d = torch.load(net_path(POS_SRC[netset]), map_location="cpu", weights_only=False)
    assert d.get("arch") == "fuse_pos", (netset, d.get("arch"))
    m = shared_pos_net(d["n_links"], d["in_channels"])
    m.load_state_dict(d["state_dict"])
    return m.eval(), np.asarray(d["mu"]), np.asarray(d["sd"])


def _std_input(X, R, mu, sd):
    from pipeline.constrained.pd_arch import stack_all
    return ((stack_all(np.asarray(X, np.float32), np.asarray(R, np.float32)) - mu) / sd).astype(np.float32)


def _embed(model, Xs, batch: int = 32) -> np.ndarray:
    import torch
    from pipeline.constrained.link_cnn import encode_links
    out = []
    with torch.no_grad():
        for i in range(0, len(Xs), batch):
            z = encode_links(model.encoder, torch.from_numpy(Xs[i:i + batch]))
            out.append(z.reshape(z.shape[0], -1).numpy())
    return np.concatenate(out) if out else np.zeros((0, 192), np.float32)


def _adabn(model, Xs_idle):
    """u1_adapt.adapt_batchnorm on the shared encoder: running statistics recomputed from the idle windows
    (links folded into the batch as the encoder folds them), every weight frozen."""
    import copy
    import torch
    import torch.nn as nn
    from pipeline.constrained.link_cnn import encode_links
    m = copy.deepcopy(model)
    bns = [q for q in m.modules() if isinstance(q, nn.BatchNorm2d)]
    for q in bns:
        q.reset_running_stats()
        q.momentum = None
        q.train()
    with torch.no_grad():
        for i in range(0, len(Xs_idle), 32):
            encode_links(m.encoder, torch.from_numpy(Xs_idle[i:i + 32]))
    m.eval()
    return m


def rows_inner(pairs: list, view: str = "fin_A3") -> int:
    """For each (network set, session): per pass, the A2 features, the abstain features and option 4's
    features, from the final-recipe networks, on relative RSSI. Written to runs/dc2_results/v2/rows/."""
    prereg_ok()
    from pipeline.constrained import pd_cells as PC
    PC.install_rrel()                                   # before the data modules import
    from pipeline.constrained.pd_clean import _bound, force_cpu
    _bound(view)                                        # the view's roots bound, then the import guards satisfied
    import torch
    torch.set_num_threads(1)
    force_cpu()
    from pipeline.constrained import paths as P
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.q1_diag import region_of
    from pipeline.constrained.q3_startclf import features as a2_features
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi, session_recordings
    from pipeline.constrained.t1_region import prepress_indices
    from pipeline.constrained.u1_adapt import calibration_indices
    from pipeline.constrained.rebuild_common import WINDOW_S
    st = P.states()
    xy = np.asarray(st.xy)
    starts = {nm: xy[st.slice_of[nm][0]] for nm in st.names}
    os.makedirs(ROWS_DIR, exist_ok=True)
    for netset, sess in pairs:
        out = rows_path(netset, sess)
        if os.path.exists(out):
            print(f"{netset} x {sess}: exists", flush=True)
            continue
        t0_ = time.time()
        g25, gmu, gsd = _load_g25(netset)
        pos, pmu, psd = _load_pos(netset)
        A2k, A2X, ABk, ABX, O4k, O4X, reg, lin = [], [], [], [], [], [], {}, {}
        adapted = {}
        for _s, stem in session_recordings(sess):
            rec = load_meta(sess, stem)
            fp = first_presses(sess, stem)
            t0 = np.asarray(rec.t0, float)
            R_all = load_rssi(sess, stem, rec.t0_epoch)
            spans = [(int(pid), nm) for pid, nm, _a, _b in rec.pass_spans() if nm in starts and fp.get(int(pid)) is not None]
            need_pos, jobs = set(), []
            for pid, nm in spans:
                press = fp[pid]
                end = t0 + WINDOW_S
                a2sel = np.flatnonzero((end >= press - 2.0 - 1e-9) & (end <= press + 1.0 + 1e-9))
                pre = prepress_indices(t0, press)
                w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
                o4 = [int(w[0]) + k for k in range(3)] if len(w) and int(w[0]) + 2 < len(rec) else []
                need_pos |= set(a2sel.tolist())
                jobs.append((pid, nm, press, pre, o4))
            # the position network over the windows the A2 features read
            xh = np.full((len(rec), 2), np.nan, np.float32)
            xl = np.full((3, len(rec), 2), np.nan, np.float32)
            idx = np.array(sorted(need_pos), int)
            if len(idx):
                Xs = _std_input(load_features(sess, stem, idx), R_all[idx], pmu, psd)
                with torch.no_grad():
                    f_, a_ = pos.forward_all(torch.from_numpy(Xs))
                xh[idx] = f_.numpy()
                xl[:, idx] = a_.numpy().transpose(1, 0, 2)
            blk = {"xy_hat": xh, "xy_hat_link": xl}
            # AdaBN on the idle windows before the first press (at least 20), as u1_adapt
            cal = np.asarray(calibration_indices(rec, fp), int)
            gm = g25
            if len(cal) >= 20:
                gm = _adabn(g25, _std_input(load_features(sess, stem, cal), R_all[cal], gmu, gsd))
            adapted[stem] = {"n_idle": int(len(cal)), "adapted": bool(len(cal) >= 20)}
            pre_all = sorted({i for _p, _n, _pr, pre, _o in jobs for i in pre.tolist()})
            o4_all = sorted({i for *_x, o4 in jobs for i in o4})
            E_ad = dict(zip(pre_all, _embed(gm, _std_input(load_features(sess, stem, pre_all), R_all[pre_all], gmu, gsd)))) if pre_all else {}
            E_o4 = dict(zip(o4_all, _embed(g25, _std_input(load_features(sess, stem, o4_all), R_all[o4_all], gmu, gsd)))) if o4_all else {}
            for pid, nm, press, pre, o4 in jobs:
                key = f"{sess}|{stem}|{pid}"
                reg[key], lin[key] = region_of(starts[nm]), nm
                f = a2_features(blk, t0, press)
                if f is not None:
                    A2k.append(key)
                    A2X.append(f)
                if len(pre) >= 2:
                    e = np.stack([E_ad[i] for i in pre.tolist()])
                    v = np.concatenate([np.nanmean(e, axis=0), e[-1]])
                    ABk.append(key)
                    ABX.append(np.where(np.isfinite(v), v, 0.0))
                if len(o4) == 3:
                    O4k.append(key)
                    O4X.append(np.concatenate([E_o4[i] for i in o4]))
        np.savez(out + ".tmp.npz", a2_keys=np.array(A2k), a2_X=np.array(A2X, np.float64),
                 ab_keys=np.array(ABk), ab_X=np.array(ABX, np.float64), o4_keys=np.array(O4k),
                 o4_X=np.array(O4X, np.float64), keys=np.array(sorted(reg)),
                 region=np.array([reg[k] for k in sorted(reg)]), line=np.array([lin[k] for k in sorted(reg)]),
                 meta=np.array(json.dumps({"netset": netset, "session": sess, "g25": os.path.relpath(_g25_file(netset), REPO_ROOT),
                                           "pos": os.path.relpath(net_path(POS_SRC[netset]), REPO_ROOT),
                                           "trained_on": list(SET_SESSIONS[netset]), "adabn": adapted})))
        os.replace(out + ".tmp.npz", out)
        print(f"[{time.strftime('%H:%M:%S')}] rows {netset} x {sess}: A2 {len(A2k)}, abstain {len(ABk)}, option 4 {len(O4k)} "
              f"({round((time.time() - t0_) / 60, 1)} min)", flush=True)
    return 0


def rows_outer(view: str, pairs: list) -> int:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    env = dict(PC.env_for(PC.cfg(view, "decode"), "half", "decode"), PYTHONPATH=REPO_ROOT, OMP_NUM_THREADS="1")
    for ns, s in pairs:
        assert s not in SET_SESSIONS[ns], f"rows of {s} from a network trained on it ({ns})"
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_v2", "rows", "--inner", "--view", view,
                            "--pairs", *[f"{ns}:{s}" for ns, s in pairs]], cwd=REPO_ROOT, env=env)


# ============================================================================ part 3: the V2 decodes (V2_PREREG 2 to 5)

def _read_rows(netset: str, sess: str) -> dict:
    d = np.load(rows_path(netset, sess), allow_pickle=False)
    reg = dict(zip(d["keys"].tolist(), d["region"].tolist()))
    lin = dict(zip(d["keys"].tolist(), d["line"].tolist()))
    return {"a2": (d["a2_keys"].tolist(), d["a2_X"]), "ab": (d["ab_keys"].tolist(), d["ab_X"]),
            "o4": (d["o4_keys"].tolist(), d["o4_X"]), "region": reg, "line": lin}


def _lda(Xtr, ytr, Xte, classes=None):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(sc.transform(Xtr), ytr)
    return clf.predict_proba(sc.transform(Xte)), list(clf.classes_)


def install_v2(cell: str, spec: dict, record: dict) -> None:
    """Patch the pieces pd_decode.inner asks for at call time: the V2-B unit fix; option 3's readers
    (A2 start terms and the abstain rows); option 4's lock rule. spec: {"o3": bool, "theta", "w_ab",
    "o4": w4 or None}. Every row is read from runs/dc2_results/v2/rows/ under ROWS_SRC[cell]."""
    import dataclasses
    import pipeline.constrained.dc2_run as R
    import pipeline.constrained.decoder2 as D2
    import pipeline.constrained.night_arms as NA
    import pipeline.constrained.night_common as NC
    import pipeline.constrained.q4_arms as Q4
    import pipeline.constrained.u1_adapt as U1
    from pipeline.constrained import pd_cells as PC
    from pipeline.constrained.pd_dt import GEOM
    c = PC.cfg(cell, "decode")
    src = ROWS_SRC[cell]
    train, test = tuple(c["train"]), c["test"]
    assert set(src) == set(train) | {test}, (cell, src, train, test)
    for s, ns in src.items():
        assert s not in SET_SESSIONS[ns], f"{cell}: {s}'s rows from a network trained on {s}"
        if s != test:
            assert set(SET_SESSIONS[ns]) <= set(train) - {s}, f"{cell}: {s}'s rows not cross-fitted ({ns})"
        else:
            assert set(SET_SESSIONS[ns]) == set(train), f"{cell}: test rows not from the model's own sessions"
    # V2-B: the transit and late-entry terms in 0.5 s units (V2_PREREG 2)
    orig = NC.shipped_pieces

    def pieces():
        st, cfg, ne, _transit, kind, alpha = orig()
        D2.DT = 0.5
        with open(GEOM, encoding="utf-8") as f:
            transit = json.load(f)
        cfg = dataclasses.replace(cfg, clock_max=16)
        D2._LT_CACHE.clear()
        record["base"] = {"decoder2_DT": D2.DT, "clock_max": cfg.clock_max, "transit": os.path.relpath(GEOM, REPO_ROOT)}
        return st, cfg, ne, transit, kind, alpha
    NC.shipped_pieces = pieces
    rows = {s: _read_rows(ns, s) for s, ns in src.items()}
    record["rows"] = {s: os.path.relpath(rows_path(ns, s), REPO_ROOT) for s, ns in src.items()}
    if spec.get("o3"):
        from pipeline.constrained.q1_diag import region_of
        from pipeline.constrained.t0_oracle import line_regions

        def start_terms(tr_s, te_s, st, weight):
            assert tuple(tr_s) == train and tuple(te_s) == (test,), (tr_s, te_s)
            Xtr = np.vstack([rows[s]["a2"][1] for s in train])
            ytr = np.array([rows[s]["region"][k] for s in train for k in rows[s]["a2"][0]])
            kte, Xte = rows[test]["a2"]
            P_, classes = _lda(Xtr, ytr, Xte)
            lr = line_regions(st)
            out = {}
            for i, key in enumerate(kte):
                lp = np.log(np.clip(P_[i], 1e-9, 1.0))
                base = float(np.mean(lp))
                out[key] = {nm: weight * float(lp[classes.index(r)] - base) for nm, r in lr.items() if r in classes}
            record["a2_reader"] = {"train_rows": int(len(Xtr)), "test_rows": int(len(kte)), "classes": classes}
            return out
        Q4.start_terms = start_terms

        def session_rows(sessions, st, mode, cache):
            ss = tuple(sessions)
            keys, X = [], []
            for s in ss:
                k, x = rows[s]["ab"]
                keys += k
                X.append(x)
            X = np.vstack(X)
            y = np.array([rows[k.split("|")[0]]["region"][k] for k in keys])
            who = np.array([k.split("|")[1] for k in keys])
            return X, y, keys, who, {}, {}
        U1.session_rows = session_rows
        R.ABSTAIN_THR, R.ABSTAIN_W = float(spec["theta"]), float(spec["w_ab"])
        record["abstain"] = {"theta": R.ABSTAIN_THR, "w_ab": R.ABSTAIN_W}
    if spec.get("o4") is not None:
        w4 = float(spec["o4"])
        Xtr, ytr = [], []
        for s in train:
            for k, x in zip(*rows[s]["o4"]):
                if rows[s]["line"][k] in CORNER_LINES:
                    Xtr.append(x)
                    ytr.append(rows[s]["line"][k])
        kte, Xte = rows[test]["o4"]
        P_, classes = _lda(np.array(Xtr), np.array(ytr), Xte)
        T = {}
        for i, key in enumerate(kte):
            t = {}
            for g, ls in CORNER.items():
                p = np.array([P_[i][classes.index(l)] for l in ls])
                lp = np.log(np.clip(p / max(p.sum(), 1e-300), 1e-12, 1.0))
                for l, v in zip(ls, lp - lp.mean()):
                    t[l] = w4 * float(v)
            T[key] = t
        record["option4"] = {"w4": w4, "train_rows": len(Xtr), "test_rows": len(kte), "classes": classes,
                             "changed": 0, "path_checks": 0}
        ont = NA.night_track

        def night_track(*a, **k):
            rows_ = ont(*a, **k)
            if not k.get("want_display"):
                return rows_
            return _option4(rows_, a, k, T, record["option4"])
        NA.night_track = night_track


def _option4(rows_, a, k, T, rec4) -> list:
    """V2_PREREG 4: a lock in a corner group becomes argmax over the group of (lock score + T). The drawn
    path after the lock is recomputed for the new line exactly as night_track computes it; the
    recomputation is checked against night_track's own path for the unchanged line on every pass."""
    from pipeline.constrained.decoder import transition_matrix
    from pipeline.constrained.decoder2 import Space, stack2
    from pipeline.constrained.night_arms import MAX_WALK_S, NEG_BIG, entry_start
    from pipeline.constrained.decoder import decoded_paths
    from pipeline.constrained.render_display import locked_chain_path
    e_path, rec, st, cfg, _transit, ne, ge, stride_s, opts = a[:9]
    sp = Space(st, cfg)
    ne.calibrate(e_path)
    e_st = stack2(e_path, ge, ne, sp)
    all_names = np.asarray(decoded_paths(np.arange(sp.N), st)).astype(str)
    on_chain = all_names != ""
    first_state = np.zeros(sp.N, bool)
    for nm in st.names:
        first_state[st.slice_of[nm][0]] = True
    lT_chains = transition_matrix(st, "tight", with_null=False)
    s_arr = np.asarray(st.s_of, float)
    horizon_w = int(round(MAX_WALK_S / stride_s))
    for r in rows_:
        Lk = (r.get("display_locked") or {}).get("2|2.0")
        if not Lk:
            continue
        key = f"{rec.session}|{rec.stem}|{int(r['pass_id'])}"
        lo = int(r["lo"])
        st_lo = np.asarray(entry_start(opts.get("entry", "free"), e_st, st, sp, lo, on_chain, first_state), float).copy()
        lim = float(opts.get("entry_window_m") or 0)
        if lim:
            for nm_x in st.names:
                aa, bb = st.slice_of[nm_x]
                far = aa + np.flatnonzero((s_arr[aa:bb] - s_arr[aa]) > lim + 1e-9)
                st_lo[far] = NEG_BIG
        hi = int(min(len(rec) - 1, len(e_st) - 1, lo + horizon_w))
        f = Lk["lock_line"]
        # the recomputation must reproduce night_track's own locked path for the line it chose
        chk = locked_chain_path(e_path, lT_chains, st, int(Lk["lo_disp"]), hi, int(Lk["evidence_horizon_w"]), f, log_start=st_lo)
        assert [p["state"] for p in chk] == [p["state"] for p in Lk["path"]], f"{key}: the path recomputation differs"
        rec4["path_checks"] += 1
        if f not in GROUP_OF or key not in T:
            continue
        S = Lk["lock_scores"]
        grp = CORNER[GROUP_OF[f]]
        new = max(grp, key=lambda l: (S[l] + T[key][l], l == f))
        if new != f:
            Lk["lock_line"], Lk["lock_line_source"] = new, "option4"
            Lk["lock_correct"] = bool(new == r["true_line"])
            Lk["path"] = locked_chain_path(e_path, lT_chains, st, int(Lk["lo_disp"]), hi, int(Lk["evidence_horizon_w"]),
                                           new, log_start=st_lo)
            rec4["changed"] += 1
    return rows_


def spec_prefix(spec: dict) -> str:
    p = "V2B"
    if spec.get("o3"):
        p += f"o3t{spec['theta']}b{spec['w_ab']}"
    if spec.get("o4") is not None:
        p += f"o4w{spec['o4']}"
    return p


def decode_inner(cell: str, spec: dict, variants: list) -> int:
    prereg_ok()
    assert os.environ.get("PD_CLEAN_PREFIX") == spec_prefix(spec)
    assert os.environ.get("PD_CLEAN_NOCACHE") == "1", "the reader cache would replace V2's readers"
    record = {"spec": spec, "prereg_sha256": PREREG_SHA}
    from pipeline.constrained.pd_clean import _bound
    _bound(cell)                     # the roots first, as pd_clean.decode_inner binds them (idempotent)
    install_v2(cell, spec, record)
    from pipeline.constrained import pd_clean
    code = pd_clean.decode_inner(cell, list(variants), False)
    if code:
        return code
    for v in variants:
        dst = J(RES, "cells", cell, "d3", f"{spec_prefix(spec)}.{v}")
        with open(J(dst, "clean.json"), encoding="utf-8") as f:
            assert "copied_from" not in json.load(f), f"{dst}: copied rather than decoded"
        with open(J(dst, "v2.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=1, default=str)
    print(f"{cell} {spec_prefix(spec)} {variants}: {json.dumps({k: v for k, v in record.items() if k != 'rows'}, default=str)}", flush=True)
    return 0


def decode_outer(cell: str, spec: dict, variants: list) -> int:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    from pipeline.constrained.pd_dt import PACE
    env = dict(PC.env_for(PC.cfg(cell, "decode"), "half", "decode"), PYTHONPATH=REPO_ROOT, OMP_NUM_THREADS="1",
               PD_CLEAN_PREFIX=spec_prefix(spec), PD_CLEAN_NOCACHE="1", PD_PACE_MEAN=PACE[0], PD_PACE_SD=PACE[1])
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_v2", "decode", "--inner", "--cell", cell,
                            "--spec", json.dumps(spec), "--variants", *variants], cwd=REPO_ROOT, env=env)


# ============================================================================ part 4: the grids, the selection, the rule

BASE_ARM = "d4c_fuse@DT1K.relgateU+abstain+a2w0.25"       #: V2-B on the rotations (pd_dt arm 1K = V2_PREREG 2)
O3_GRID = [(w, t, b) for w in (0.25, 0.5, 1.0) for t in (0.8, 0.9) for b in (0.25, 0.5)]   #: the tie order
O4_GRID = (0.5, 1.0, 2.0)


def o3_arm(w, t, b) -> str:
    return f"d4c_fuse@{spec_prefix({'o3': True, 'theta': t, 'w_ab': b})}.relgateU+abstain+a2w{w}"


def o4_arm(w4, o3) -> str:
    if o3:
        w, t, b = o3
        return f"d4c_fuse@{spec_prefix({'o3': True, 'theta': t, 'w_ab': b, 'o4': w4})}.relgateU+abstain+a2w{w}"
    return f"d4c_fuse@{spec_prefix({'o4': w4})}.relgateU+abstain+a2w0.25"


def select(option: str) -> int:
    """V2_PREREG 3.5 and 4: the candidate is the grid's highest rotation objective (ties to the first in the
    pre-registered order); then pd_rule against the base; ADOPT only on the rule."""
    prereg_ok()
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_rule as PR
    if option == "3":
        base, grid = BASE_ARM, [(g, o3_arm(*g)) for g in O3_GRID]
    else:
        with open(J(PR.RULE_DIR, "V2_option3.json"), encoding="utf-8") as f:
            d3 = json.load(f)
        o3 = tuple(d3["candidate"]) if d3["decision"] == "ADOPT" else None
        base = o3_arm(*o3) if o3 else BASE_ARM
        grid = [(w4, o4_arm(w4, o3)) for w4 in O4_GRID]
    scores = []
    for g, arm in grid:
        R_ = PR.rot_rows(arm, "display")
        assert len(R_) == 3, f"{arm}: {len(R_)} rotations decoded"
        scores.append((g, arm, PR.summarise(R_)["objective"]))
    best = max(scores, key=lambda x: (x[2], -scores.index(x)))
    name = f"V2_option{option}"
    PR.main(["compare", "--name", name, "--base", base, "--arm", best[1], "--lock", "display"])
    with open(J(PR.RULE_DIR, f"{name}_display.json"), encoding="utf-8") as f:
        o = json.load(f)
    out = {"option": option, "base": base, "grid": [{"setting": g, "arm": a, "objective": round(v, 4)} for g, a, v in scores],
           "candidate": best[0], "candidate_arm": best[1], "base_objective": o["base_summary"]["objective"],
           "paired": o.get("paired"), "guard": o.get("guard"), "decision": o.get("decision"),
           "prereg_sha256": PREREG_SHA, "at": time.strftime("%Y-%m-%d %H:%M")}
    with open(J(PR.RULE_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("option", "candidate", "base_objective", "paired", "decision")}, indent=1), flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "train_all", "rows", "decode", "select"])
    ap.add_argument("--option")
    ap.add_argument("--net")
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--view", default="fin_A3")
    ap.add_argument("--pairs", nargs="+")
    ap.add_argument("--cell")
    ap.add_argument("--spec")
    ap.add_argument("--variants", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "train":
        return train_inner(a.net)
    if a.cmd == "train_all":
        return train_all()
    if a.cmd == "rows":
        pairs = [tuple(x.split(":")) for x in a.pairs]
        return rows_inner(pairs, a.view) if a.inner else rows_outer(a.view, pairs)
    if a.cmd == "select":
        return select(a.option)
    spec = json.loads(a.spec)
    return decode_inner(a.cell, spec, a.variants) if a.inner else decode_outer(a.cell, spec, a.variants)


if __name__ == "__main__":
    sys.exit(main())
