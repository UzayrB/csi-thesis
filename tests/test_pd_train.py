"""pd_train with every option off must be the recipe (nets.fit_posterior / fit_position) exactly."""

import numpy as np
import torch

import pipeline.constrained.nets as N
from pipeline.constrained.pd_train import _augment, fit_link


def _data(n=96, seed=3):
    r = np.random.default_rng(seed)
    X = r.standard_normal((n, 1, 2, 40, 24)).astype(np.float32)
    X[:, :, 1] = X[:, :, 1, :, :1]                      # RSSI broadcast across subcarriers, as stack_link
    return X, r.integers(0, 25, n), r.uniform(0, 5, (n, 2)).astype(np.float32)


def _same(a, b):
    sa, sb = a.state_dict(), b.state_dict()
    return sa.keys() == sb.keys() and all(torch.equal(sa[k].cpu(), sb[k].cpu()) for k in sa)


def _cpu(monkeypatch):
    monkeypatch.setattr(N, "device", lambda: torch.device("cpu"))


def test_posterior_identity(monkeypatch):
    _cpu(monkeypatch)
    X, c, _xy = _data()
    ref, mu0, sd0 = N.fit_posterior(X, c, 25, 2, 0)
    mine, mu1, sd1, rec = fit_link(X, c, "g", 25, 0, {"epochs": 2})
    assert _same(ref, mine) and np.array_equal(mu0, mu1) and np.array_equal(sd0, sd1)
    assert rec["epochs_run"] == 2


def test_position_identity(monkeypatch):
    _cpu(monkeypatch)
    X, _c, xy = _data()
    ref, _m, _s = N.fit_position(X, xy, 2, 0)
    mine, _m2, _s2, _r = fit_link(X, xy, "pos", 2, 0, {"epochs": 2})
    assert _same(ref, mine)


def test_early_stopping_keeps_a_recipe_epoch(monkeypatch):
    _cpu(monkeypatch)
    X, c, _xy = _data()
    Xv, cv, _ = _data(48, seed=4)
    mine, _m, _s, rec = fit_link(X, c, "g", 25, 0, {"early": True, "max_epochs": 3}, Xv=Xv, yv=cv)
    assert rec["epochs_run"] == 3 and 1 <= rec["best_epoch"] <= 3 and len(rec["val_history"]) == 3
    ref, _m0, _s0 = N.fit_posterior(X, c, 25, rec["best_epoch"], 0)
    assert _same(ref, mine)                              # the kept weights are the recipe's at that epoch


def test_options_run_and_change_the_weights(monkeypatch):
    _cpu(monkeypatch)
    X, c, xy = _data()
    sess = np.array(["01"] * 48 + ["B1"] * 48)
    ref, _m, _s = N.fit_posterior(X, c, 25, 1, 0)
    for opts in ({"aug": True}, {"mixup": True}, {"aug": True, "mixup": True}):
        m, _m1, _s1, _r = fit_link(X, c, "g", 25, 0, dict(opts, epochs=1), sessions=sess)
        assert not _same(ref, m)
    m, _m1, _s1, _r = fit_link(X, xy, "pos", 2, 0, {"mixup": True, "epochs": 1}, sessions=sess)


def test_augment_ranges():
    r = np.random.default_rng(0)
    xb = torch.ones((200, 1, 2, 40, 24))
    out = _augment(xb, r, 1.0)
    sc = out[:, 0, 0].amax(dim=(1, 2))
    assert float(sc.min()) >= 0.25 - 1e-6 and float(sc.max()) <= 1.5 + 1e-6
    off = out[:, 0, 1, 0, 0] - 1.0
    assert float(off.abs().max()) <= 5.0 + 1e-6
    ramp = torch.arange(40, dtype=torch.float32)[None, None, None, :, None].expand(3, 1, 2, 40, 24).clone()
    sh = _augment(ramp, np.random.default_rng(1), 0.0)
    assert sh.shape == ramp.shape


def test_shared_architectures_train_and_infer(monkeypatch):
    _cpu(monkeypatch)
    from pipeline.constrained.pd_arch import SharedNet, infer_shared
    r = np.random.default_rng(5)
    Xl = r.standard_normal((64, 3, 40, 24)).astype(np.float32)
    R = r.standard_normal((64, 3, 40)).astype(np.float32)
    from pipeline.constrained.pd_arch import stack_all
    X = stack_all(Xl, R)
    c = r.integers(0, 25, 64)
    sess = np.array(["01"] * 32 + ["B1"] * 32)
    for arch in ("fuse", "attn"):
        for opts in ({"epochs": 1}, {"epochs": 1, "aug": True, "mixup": True}):
            m, mu, sd, _r = fit_link(X, c, "g", 25, 0, opts, sessions=sess, arch=arch)
            assert isinstance(m, SharedNet) and mu.shape == (1, 3, 2, 1, 1)
            p, pl = infer_shared(m, mu, sd, Xl, R)
            assert p.shape == (64, 25) and pl.shape == (3, 64, 25) and np.allclose(p.sum(1), 1)
