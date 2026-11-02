# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Everything for the start-of-walk terms: the veto and A2 weights, which start region each line begins in...

from __future__ import annotations

VETO_THR = 0.01
VETO_W = 1.0
A2_WEIGHT = 0.5


ABSTAIN_THR, ABSTAIN_W = 0.90, 0.25


SUPPORTED_PARTS = {"relgate", "relgate_a", "relgate_up", "abstain", "a2w"}


# Pd_decode.parse, refusing anything the downstream tools do not reproduce.
def variant_spec(variant: str) -> dict:
    v = parse(variant)
    default = parse("ref")
    extra = [k for k in v if v[k] != default[k] and k not in SUPPORTED_PARTS]
    if extra:
        raise SystemExit(f"variant {variant!r}: {extra} are not reproduced by the downstream tools")
    assert v["relgate"] and v["relgate_a"] and v["relgate_up"], f"variant {variant!r} is not relgateU-based"
    return v


# Function parse.
def parse(name: str) -> dict:
    v = {"w": 0.0, "cnull": False, "relgate": False, "abstain": False, "pace": False,
         "offset": None, "margin": None, "a2w": None, "sd": None, "onhead": None, "g100n": False,
         "interp": False, "cfgB": None, "lw": None, "relgate_a": False, "relgate_up": False}
    if name == "ref":
        return v
    for part in name.split("+"):
        if part in ("cnull", "relgate", "abstain", "pace", "g100n", "interp"):
            v[part] = True
        elif part == "relgateA":
            v["relgate"], v["relgate_a"] = True, True
        elif part == "relgateU":
            v["relgate"], v["relgate_a"], v["relgate_up"] = True, True, True
        elif part in ("cfgB", "cfgBc", "cfgBn"):
            v["cfgB"] = part
        elif part.startswith("onhead"):
            v["onhead"], v["cnull"] = float(part[6:] or 1.0), True
        elif part.startswith("margin"):
            v["margin"] = float(part[6:])
        elif part.startswith("off"):
            v["offset"] = float(part[3:])
        elif part.startswith("a2w"):
            v["a2w"] = float(part[3:])
        elif part.startswith("sd"):
            v["sd"] = float(part[2:])
        elif part.startswith("lw"):
            v["lw"] = float(part[2:])
        elif part.startswith("w"):
            v["w"] = float(part[1:])
        else:
            raise SystemExit(f"unknown variant part {part!r}")
    return v


import numpy as np

REGIONS = {"S_mid": (2.5, 0.0), "N_mid": (2.5, 5.0), "W_mid": (0.0, 2.5), "E_mid": (5.0, 2.5),
           "SW": (0.0, 0.0), "NE": (5.0, 5.0), "NW": (0.0, 5.0), "SE": (5.0, 0.0)}


# Function region of.
def region_of(xy):
    xy = np.asarray(xy, float)
    return min(REGIONS, key=lambda k: float(np.linalg.norm(xy - np.asarray(REGIONS[k], float))))


from pipeline.constrained.RunLive.shared_settings import WINDOW_S

BEFORE_S, AFTER_S = 2.0, 1.0


# The position head and the three per-link heads over the windows straddling the press.
def features(blk, t, press):
    end = np.asarray(t, float) + WINDOW_S
    sel = np.flatnonzero((end >= press - BEFORE_S - 1e-9) & (end <= press + AFTER_S + 1e-9))
    xh = np.asarray(blk.get("xy_hat"))
    xl = np.asarray(blk.get("xy_hat_link"))
    sel = sel[sel < len(xh)]
    if len(sel) < 2:
        return None
    v = [np.nanmean(xh[sel], axis=0), np.nanstd(xh[sel], axis=0), xh[sel[0]], xh[sel[-1]]]
    for li in range(xl.shape[0]):
        v += [np.nanmean(xl[li][sel], axis=0), xl[li][sel[0]], xl[li][sel[-1]]]
    f = np.concatenate([np.asarray(x, float).ravel() for x in v])
    return np.where(np.isfinite(f), f, 0.0)


# {line: the region its FIRST state sits in}.
def line_regions(st) -> dict:
    xy = np.asarray(st.xy, float)
    return {nm: region_of(xy[st.slice_of[nm][0]]) for nm in st.names}


T1_BEFORE_S, T1_AFTER_S = 2.0, 0.0


# Windows whose END is at or before the press, within before_s of it.
def prepress_indices(t0: np.ndarray, press: float,
                     before_s: float = T1_BEFORE_S, after_s: float = T1_AFTER_S) -> np.ndarray:
    assert after_s == 0.0, (
        f"AFTER_S is {after_s}, not zero. A positive value selects windows whose end is AFTER the "
        f"press, which reads radio recorded after the moment this head claims to predict from")
    end = np.asarray(t0, float) + WINDOW_S
    return np.flatnonzero((end <= press + 1e-9) & (end >= press - before_s - 1e-9))


from pipeline.constrained.RunLive.shared_settings import E_POST
import os

SEED = 0


# The three per-link posterior heads for one tag, with the training mu and sd they carry.
def load_heads(tag: str):
    import torch
    from pipeline.constrained.RunLive.network_build import LinkNet
    out = []
    for li in range(3):
        from pipeline.constrained.RunLive.shared_settings import ART_DIR
        p = os.path.join(ART_DIR, "models",
                         f"{tag}_g25_e{E_POST}_s{SEED}_link{li}.pt")
        if not os.path.exists(p):
            return None
        o = torch.load(p, map_location="cpu", weights_only=False)
        m = LinkNet(o["n_links"], o["out_dim"], "posterior", o["in_channels"])
        m.load_state_dict(o["state_dict"])
        m.eval()
        out.append((m, np.asarray(o["mu"]), np.asarray(o["sd"])))
    return out


# Recompute every BatchNorm2d running statistic from this session's own calibration windows.
def adapt_batchnorm(heads, F, R):
    import copy

    import torch
    import torch.nn as nn
    from pipeline.constrained.RunLive.network_build import stack_link
    torch.set_num_threads(1)
    out = []
    for li, (m0, mu, sd) in enumerate(heads):
        m = copy.deepcopy(m0)
        bns = [q for q in m.modules() if isinstance(q, nn.BatchNorm2d)]
        if not bns:
            out.append((m, mu, sd))
            continue
        for q in bns:
            q.reset_running_stats()
            q.momentum = None
            q.train()
        Xb = stack_link(F[:, [li]], R[:, [li]])
        Xb = ((Xb - mu) / sd).astype(np.float32)
        with torch.no_grad():
            for i in range(0, len(Xb), 32):
                m(torch.from_numpy(Xb[i:i + 32]))
        m.eval()
        out.append((m, mu, sd))
        del Xb
    return out


# (n, 3 * EMBED) from whichever head set is handed in.
def embed_rows(heads, F, R, batch: int = 32) -> np.ndarray:
    import torch
    from pipeline.constrained.RunLive.network_build import stack_link
    torch.set_num_threads(1)
    parts = []
    for li, (m, mu, sd) in enumerate(heads):
        Xb = stack_link(F[:, [li]], R[:, [li]])
        Xb = ((Xb - mu) / sd).astype(np.float32)
        ch = []
        with torch.no_grad():
            for i in range(0, len(Xb), batch):
                ch.append(m.embed(torch.from_numpy(Xb[i:i + batch])).numpy())
        parts.append(np.concatenate(ch) if ch else np.zeros((0, 1), np.float32))
        del Xb
    return np.concatenate(parts, axis=1).astype(np.float32)


VETO_NATS = 3.0
