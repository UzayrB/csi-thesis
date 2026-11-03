# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T8, at SPACE: where the walk starts.

from __future__ import annotations

import os

import numpy as np

from pipeline.tracking.networks import LinkNet, load_network, position_of, stack_link
from pipeline.tracking.settings import E_POST, E_REG, WINDOW_S

VETO_THR = 0.01
VETO_W = 1.0
VETO_NATS = 3.0
A2_WEIGHT = 0.5
ABSTAIN_THR, ABSTAIN_W = 0.90, 0.25



# The frozen tracker's start-of-walk terms: the A2 term at the variant's weight, and the veto reader's term...
class StartTerms:

    # From the frozen folder: the readers and their scalers (readers.pkl), the three position networks and the...
    def __init__(self, folder: str, meta: dict, readers: dict, st):
        tag = meta["reader_tag"]
        self.st, self.reader_tag = st, tag
        self.a2_sc, self.a2, self.v_sc, self.reader = readers["a2_sc"], readers["a2"], readers["v_sc"], readers["reader"]
        nets = os.path.join(folder, "nets")
        paths = [os.path.join(nets, "models", f"{tag}_pos2_e{E_REG}_s0_link{li}.pt") for li in range(3)]
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: the frozen reader tag {tag}'s position heads are missing: {missing}")
        self.pos = [load_network(p) for p in paths]
        self.g25 = load_heads(tag, nets)
        if self.g25 is None:
            raise SystemExit(f"REFUSED: the frozen reader tag {tag}'s g25 heads are missing")
        self.heads = self.g25
        self.adaptation = {"adapted": False, "n_calibration_windows": 0}
        spec = variant_spec(meta["variant"])
        self.a2w = spec["a2w"] if spec["a2w"] is not None else A2_WEIGHT
        self.abstain = bool(spec["abstain"])
        self.variant = meta["variant"]
        if (self.a2w, self.abstain) != (meta["a2w"], meta["abstain"]):
            raise SystemExit(f"REFUSED: the start terms' weights differ from the frozen ones: {(self.a2w, self.abstain)}")

    # AdaBN on the recording's idle windows before its first press; unadapted below 20.
    def adapt(self, cal_feats: np.ndarray, cal_rssi: np.ndarray) -> dict:
        n = int(len(cal_feats))
        self.heads = adapt_batchnorm(self.g25, cal_feats.astype(np.float32), cal_rssi.astype(np.float32)) \
            if n >= 20 else self.g25
        self.adaptation = {"adapted": bool(n >= 20), "n_calibration_windows": n}
        return self.adaptation

    # The A2 feature row from the windows given (starts t0), selected exactly as offline.
    def a2_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        xh, xl = position_of(self.pos, feats, rssi)
        blk = {"xy_hat": xh.astype(np.float32), "xy_hat_link": xl.astype(np.float32)}
        return features(blk, np.asarray(t0, float), press)

    # Function veto row.
    def veto_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        sel = prepress_indices(np.asarray(t0, float), press)
        if len(sel) < 2:
            return None
        e = embed_rows(self.heads, feats[sel], rssi[sel])
        f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
        return np.where(np.isfinite(f), f, 0.0)

    # {line: nudge}: the A2 term (centred log probability of the line's start region, times a2w) plus the veto...
    def terms(self, a2_row, veto_row) -> dict:
        lr = line_regions(self.st)
        out = {}
        if a2_row is not None:
            P = self.a2.predict_proba(self.a2_sc.transform(a2_row[None]))[0]
            classes = list(self.a2.classes_)
            lp = np.log(np.clip(P, 1e-9, 1.0))
            base = float(np.mean(lp))
            out = {nm: self.a2w * float(lp[classes.index(r)] - base) for nm, r in lr.items() if r in classes}
        if veto_row is not None:
            p = self.reader.predict_proba(self.v_sc.transform(veto_row[None]))[0]
            ci = {c: i for i, c in enumerate(self.reader.classes_)}
            if self.abstain:
                if float(np.asarray(p, float).max()) >= ABSTAIN_THR:
                    lp = np.log(np.clip(np.asarray(p, float), 1e-9, 1.0))
                    base = float(np.mean(lp))
                    for nm, r in lr.items():
                        if r in ci:
                            out[nm] = out.get(nm, 0.0) + ABSTAIN_W * float(lp[ci[r]] - base)
            else:
                for nm, r in lr.items():
                    v = -VETO_W * VETO_NATS if (r in ci and p[ci[r]] < VETO_THR) else 0.0
                    out[nm] = out.get(nm, 0.0) + v
        return out



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



REGIONS = {"S_mid": (2.5, 0.0), "N_mid": (2.5, 5.0), "W_mid": (0.0, 2.5), "E_mid": (5.0, 2.5),
           "SW": (0.0, 0.0), "NE": (5.0, 5.0), "NW": (0.0, 5.0), "SE": (5.0, 0.0)}


# Function region of.
def region_of(xy):
    xy = np.asarray(xy, float)
    return min(REGIONS, key=lambda k: float(np.linalg.norm(xy - np.asarray(REGIONS[k], float))))


# {line: the region its FIRST state sits in}.
def line_regions(st) -> dict:
    xy = np.asarray(st.xy, float)
    return {nm: region_of(xy[st.slice_of[nm][0]]) for nm in st.names}


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


T1_BEFORE_S, T1_AFTER_S = 2.0, 0.0


# Windows whose END is at or before the press, within before_s of it.
def prepress_indices(t0: np.ndarray, press: float,
                     before_s: float = T1_BEFORE_S, after_s: float = T1_AFTER_S) -> np.ndarray:
    assert after_s == 0.0, (
        f"AFTER_S is {after_s}, not zero. A positive value selects windows whose end is AFTER the "
        f"press, which reads radio recorded after the moment this head claims to predict from")
    end = np.asarray(t0, float) + WINDOW_S
    return np.flatnonzero((end <= press + 1e-9) & (end >= press - before_s - 1e-9))



SEED = 0


# The three per-link g25 networks for one tag, from <nets_dir>/models/, with the training mu and sd they...
def load_heads(tag: str, nets_dir: str):
    import torch
    out = []
    for li in range(3):
        p = os.path.join(nets_dir, "models", f"{tag}_g25_e{E_POST}_s{SEED}_link{li}.pt")
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
