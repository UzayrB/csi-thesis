"""idx_train. Identification development (the operator's direction of 2026-09-28): the CNN trainer with
extra augmentation for placement change. `idv2_core` is frozen with the v2 registration, so this is a new
file; with `tilt_sd` 0 it trains exactly as `idv2_core.train_cnn`.

Placement augmentation: moving a receiver changes which multipath components a link sees, which on the
log-magnitude map looks like a smooth, frequency-dependent gain. Per sample and per link, a linear tilt
across the 28 frequency bins with a slope ~ N(0, tilt_sd) is added after the standard augmentation.
"""

from __future__ import annotations

import numpy as np

from pipeline.identify import idv2_core as C


def train_cnn(Xw, yw, dirw, n_cls, seed, device="cpu", steps=3000, tilt_sd=0.0):
    import torch
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    net = C.make_net(Xw.shape[1], n_cls).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=C.HP["lr"], weight_decay=C.HP["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=0.0)
    X = torch.tensor(Xw, dtype=torch.float32, device=device)
    D = torch.nn.functional.one_hot(torch.tensor(dirw, dtype=torch.long), 2).float().to(device)
    Y = torch.tensor(yw, dtype=torch.long, device=device)
    by = [torch.tensor(np.flatnonzero(yw == c)) for c in range(n_cls)]
    present = [c for c in range(n_cls) if len(by[c])]
    ramp = torch.linspace(-1.0, 1.0, Xw.shape[2]).to(device)[None, None, :, None]
    net.train()
    for _ in range(steps):
        cls = torch.tensor(present)[torch.randint(0, len(present), (C.HP["batch"],), generator=g)]
        r = torch.rand(C.HP["batch"], generator=g)
        idx = torch.stack([by[int(c)][int(r[i] * len(by[int(c)]))] for i, c in enumerate(cls)]).to(device)
        xb = C.augment(X[idx], g)
        if tilt_sd > 0:
            xb = xb + tilt_sd * torch.randn(xb.shape[0], xb.shape[1], 1, 1, generator=g).to(device) * ramp
        loss = torch.nn.functional.cross_entropy(net(xb, D[idx]), Y[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
    net.eval()
    return net
