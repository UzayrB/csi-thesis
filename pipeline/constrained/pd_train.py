"""pd_train: the training variants of the tracking attack (reports/BRIEF_tracking_attack_2026-09-28.md, D2).

WITH EVERY OPTION OFF this is `nets.fit_posterior` / `nets.fit_position` step for step: the same
`seed_all(seed)`, the same model construction, the same per-channel standardisation on the training
windows, the same Adam (lr 1e-3, weight decay 1e-4), batch 64, and the same epoch permutations from
`np.random.default_rng(seed)`. Options draw their randomness from a SEPARATE generator, so switching
one on never disturbs the batch order.

Options (each a key of `opts`):
  aug      per batch, on the RAW (unstandardised) link input:
             RSSI offset uniform +-5 dB (times opts['rssi_unit'] when inputs are already normalised);
             CSI-shape scaling log-uniform x0.25 to x1.5;
             time shift uniform +-0.25 s (37 samples at 150 Hz), edges replicated;
           then, after standardisation, Gaussian noise sd 0.1.
  mixup    alpha 0.2: each sample mixed with a partner from a DIFFERENT training session; the loss is
           the lambda-weighted loss against both targets (the position target is mixed linearly).
  early    early stopping on the rotation's validation windows (never a calibration walk), at most
           opts['max_epochs'] (40) epochs; the best epoch's weights are kept. Posterior heads choose on
           validation accuracy, position heads on validation smooth-L1.
  epochs   a fixed epoch count, used by a final model that has no validation session (the median of
           the rotations' best epochs).
  snapshots  with early: every epoch's weights are returned (rec['_snapshots']), so a model at any
           other epoch count (the cross-rotation epoch) needs no retraining.

Saved under the standard file names (`e24` posterior, `e20` position) so every later stage reads them
unchanged; the epochs actually used and the options are recorded inside each file.
"""

from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn.functional as F

SHIFT_SAMPLES = 37           # 0.25 s at 150 Hz
NOISE_SD = 0.1               # in standardised units: mild
MIXUP_ALPHA = 0.2


def _augment(xb: torch.Tensor, rng, rssi_unit: float) -> torch.Tensor:
    """xb: (B, L, 2, T, S) raw input on CPU, L links (1 for a per-link network). Returns an augmented
    copy: RSSI offset and CSI scale drawn per link, the time shift shared by the links of a window."""
    B, L, C, T, S = xb.shape
    xb = xb.clone()
    if C > 1:
        off = torch.from_numpy(rng.uniform(-5.0, 5.0, (B, L)).astype(np.float32)) * float(rssi_unit)
        xb[:, :, 1] += off[:, :, None, None]
    sc = torch.from_numpy(np.exp(rng.uniform(np.log(0.25), np.log(1.5), (B, L))).astype(np.float32))
    xb[:, :, 0] *= sc[:, :, None, None]
    shift = torch.from_numpy(rng.integers(-SHIFT_SAMPLES, SHIFT_SAMPLES + 1, B))
    idx = (torch.arange(T)[None, :] - shift[:, None]).clamp(0, T - 1)
    idx = idx[:, None, None, :, None].expand(B, L, C, T, S)
    return torch.gather(xb, 3, idx)


def _evaluate(model, Xv, yv, mu, sd, kind, dev, batch=128) -> float:
    """Validation score, higher is better: accuracy for a posterior head, minus smooth-L1 for position."""
    model.eval()
    outs = []
    with torch.no_grad():
        for i in range(0, len(Xv), batch):
            xb = torch.from_numpy(((Xv[i:i + batch] - mu) / sd).astype(np.float32)).to(dev)
            outs.append(model(xb).cpu())
    out = torch.cat(outs)
    if kind == "pos":
        return -float(F.smooth_l1_loss(out, torch.from_numpy(np.asarray(yv, np.float32))))
    return float((out.argmax(1).numpy() == np.asarray(yv)).mean())


def fit_link(X: np.ndarray, y: np.ndarray, kind: str, out_dim: int, seed: int, opts: dict,
             sessions=None, Xv=None, yv=None, arch: str = None) -> tuple:
    """One link's network under `opts`, or with `arch` ('fuse' or 'attn', pd_arch) one shared network
    over all the links in X's second axis. Returns (model, mu, sd, record)."""
    from pipeline.constrained.common import E_POST, E_REG, seed_all
    from pipeline.constrained.nets import BATCH, LR, WEIGHT_DECAY, LinkNet, device, per_channel_stats
    if arch:
        from pipeline.constrained.pd_arch import SharedNet, link_stats, mixed_shared_loss, shared_loss
        assert kind == "g", "the shared architectures are posterior heads"
        mu, sd = link_stats(X)
    else:
        mu, sd = per_channel_stats(X)
    seed_all(seed)
    head = "position" if kind == "pos" else "posterior"
    model = SharedNet(X.shape[1], out_dim, arch, X.shape[2]) if arch else LinkNet(X.shape[1], out_dim, head, X.shape[2])
    dev = device()
    model = model.to(dev)
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    rng = np.random.default_rng(seed)                     # the recipe's permutations, untouched
    arng = np.random.default_rng(seed + 7919)             # every option's randomness
    loss_fn = F.smooth_l1_loss if kind == "pos" else F.cross_entropy
    yt = (torch.from_numpy(np.asarray(y, np.float32)) if kind == "pos"
          else torch.from_numpy(np.asarray(y, np.int64)))
    base = E_REG if kind == "pos" else E_POST
    early = bool(opts.get("early")) and Xv is not None
    epochs = int(opts.get("max_epochs", 40)) if early else int(opts.get("epochs") or base)
    plain = not (opts.get("aug") or opts.get("mixup") or arch)
    Xs = torch.from_numpy(((X - mu) / sd).astype(np.float32)) if plain else torch.from_numpy(X.astype(np.float32))
    mu_t, sd_t = torch.from_numpy(mu.astype(np.float32)), torch.from_numpy(sd.astype(np.float32))
    if opts.get("mixup"):
        sess = np.asarray(sessions).astype(str)
        by_sess = {s: np.flatnonzero(sess == s) for s in sorted(set(sess))}
    best, best_ep, hist, snaps = None, None, [], []
    for ep in range(epochs):
        model.train()
        order = rng.permutation(len(Xs))
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            xb = Xs[idx]
            if not plain:
                if opts.get("aug"):
                    xb = _augment(xb, arng, float(opts.get("rssi_unit", 1.0)))
                if opts.get("mixup"):
                    own = sess[idx]
                    part = np.array([arng.choice(by_sess[arng.choice([s for s in by_sess if s != o])]) for o in own])
                    xp = Xs[part]
                    if opts.get("aug"):
                        xp = _augment(xp, arng, float(opts.get("rssi_unit", 1.0)))
                    lam = torch.from_numpy(arng.beta(MIXUP_ALPHA, MIXUP_ALPHA, len(idx)).astype(np.float32))
                    xb = lam[:, None, None, None, None] * xb + (1 - lam[:, None, None, None, None]) * xp
                xb = (xb - mu_t) / sd_t
                if opts.get("aug"):
                    xb = xb + NOISE_SD * torch.from_numpy(arng.standard_normal(tuple(xb.shape)).astype(np.float32))
            optim.zero_grad()
            out = model(xb.to(dev))
            if opts.get("mixup") and not plain:
                ya, yb = yt[idx].to(dev), yt[part].to(dev)
                lam_d = lam.to(dev)
                if arch:
                    loss = mixed_shared_loss(out, ya, yb, lam_d)
                elif kind == "pos":
                    target = lam_d[:, None] * ya + (1 - lam_d[:, None]) * yb
                    loss = loss_fn(out, target)
                else:
                    loss = (lam_d * F.cross_entropy(out, ya, reduction="none")
                            + (1 - lam_d) * F.cross_entropy(out, yb, reduction="none")).mean()
            elif arch:
                loss = shared_loss(out, yt[idx].to(dev))
            else:
                loss = loss_fn(out, yt[idx].to(dev))
            loss.backward()
            optim.step()
        if dev.type == "mps":
            torch.mps.empty_cache()
        if early:
            score = _evaluate(model, Xv, yv, mu, sd, kind, dev)
            hist.append(round(score, 5))
            if best is None or score > hist[best_ep]:
                best, best_ep = copy.deepcopy(model.state_dict()), ep
            if opts.get("snapshots"):
                snaps.append({k: t.detach().cpu().clone() for k, t in model.state_dict().items()})
    if early:
        model.load_state_dict(best)
    model.eval()
    rec = {"epochs_run": epochs, "best_epoch": (best_ep + 1) if early else epochs, "val_history": hist,
           "opts": {k: v for k, v in opts.items() if k != "rssi_unit"}, "rssi_unit": opts.get("rssi_unit", 1.0)}
    if snaps:
        rec["_snapshots"] = snaps          # every epoch's weights: epoch k is the recipe trained k epochs
    return model, mu, sd, rec
