# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T8, at SPACE: where the walk starts.

from __future__ import annotations

import copy
import os

import numpy as np
import torch
import torch.nn as nn

from pipeline.tracking.networks import LinkNet, load_network, position_of, stack_link
from pipeline.tracking.settings import E_POST, E_REG, WINDOW_S

ABSTAIN_THR, ABSTAIN_W = 0.90, 0.25
A2_BEFORE_S, A2_AFTER_S = 2.0, 1.0
VETO_BEFORE_S = 2.0
REGIONS = {"S_mid": (2.5, 0.0), "N_mid": (2.5, 5.0), "W_mid": (0.0, 2.5), "E_mid": (5.0, 2.5),
           "SW": (0.0, 0.0), "NE": (5.0, 5.0), "NW": (0.0, 5.0), "SE": (5.0, 0.0)}


# The frozen tracker's start-of-walk terms: the A2 reader's at weight a2w, and the veto reader's, which...
class StartTerms:

    # From the frozen folder: the readers and their scalers (readers.pkl), the three position networks and the...
    def __init__(self, folder: str, meta: dict, readers: dict, st):
        if not meta["abstain"]:
            raise SystemExit("REFUSED: the frozen tracker's veto reader does not abstain; the app has only that one")
        tag = meta["reader_tag"]
        self.st, self.a2w = st, float(meta["a2w"])
        self.a2_sc, self.a2, self.v_sc, self.reader = readers["a2_sc"], readers["a2"], readers["v_sc"], readers["reader"]
        models = os.path.join(folder, "nets", "models")
        pos = [os.path.join(models, f"{tag}_pos2_e{E_REG}_s0_link{li}.pt") for li in range(3)]
        g25 = [os.path.join(models, f"{tag}_g25_e{E_POST}_s0_link{li}.pt") for li in range(3)]
        missing = [p for p in pos + g25 if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: the frozen reader tag {tag}'s networks are missing: {missing}")
        self.pos = [load_network(p) for p in pos]
        self.g25 = [load_g25(p) for p in g25]
        self.heads = self.g25
        self.adaptation = {"adapted": False, "n_calibration_windows": 0}

    # AdaBN on the recording's idle windows before its first press; unadapted below 20.
    def adapt(self, cal_feats: np.ndarray, cal_rssi: np.ndarray) -> dict:
        n = int(len(cal_feats))
        self.heads = adapt_batchnorm(self.g25, cal_feats.astype(np.float32), cal_rssi.astype(np.float32)) \
            if n >= 20 else self.g25
        self.adaptation = {"adapted": bool(n >= 20), "n_calibration_windows": n}
        return self.adaptation

    # The A2 reader's input: the position networks' guesses over the windows ending around the press (their...
    def a2_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        xh, xl = position_of(self.pos, feats, rssi)
        xh, xl = xh.astype(np.float32), xl.astype(np.float32)
        end = np.asarray(t0, float) + WINDOW_S
        sel = np.flatnonzero((end >= press - A2_BEFORE_S - 1e-9) & (end <= press + A2_AFTER_S + 1e-9))
        sel = sel[sel < len(xh)]
        if len(sel) < 2:
            return None
        v = [np.nanmean(xh[sel], axis=0), np.nanstd(xh[sel], axis=0), xh[sel[0]], xh[sel[-1]]]
        for li in range(xl.shape[0]):
            v += [np.nanmean(xl[li][sel], axis=0), xl[li][sel[0]], xl[li][sel[-1]]]
        f = np.concatenate([np.asarray(x, float).ravel() for x in v])
        return np.where(np.isfinite(f), f, 0.0)

    # The veto reader's input: the g25 networks' embeddings of the windows ending in the 2 s before the press...
    def veto_row(self, t0: np.ndarray, feats: np.ndarray, rssi: np.ndarray, press: float):
        end = np.asarray(t0, float) + WINDOW_S
        sel = np.flatnonzero((end <= press + 1e-9) & (end >= press - VETO_BEFORE_S - 1e-9))
        if len(sel) < 2:
            return None
        e = embed_rows(self.heads, feats[sel], rssi[sel])
        f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
        return np.where(np.isfinite(f), f, 0.0)

    # {line: nudge}: the A2 term (the centred log probability of the line's start region, times a2w) plus the...
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
            p = np.asarray(self.reader.predict_proba(self.v_sc.transform(veto_row[None]))[0], float)
            ci = {c: i for i, c in enumerate(self.reader.classes_)}
            if float(p.max()) >= ABSTAIN_THR:
                lp = np.log(np.clip(p, 1e-9, 1.0))
                base = float(np.mean(lp))
                for nm, r in lr.items():
                    if r in ci:
                        out[nm] = out.get(nm, 0.0) + ABSTAIN_W * float(lp[ci[r]] - base)
        return out


# {line: the region its first point sits in}: the nearest of the eight start regions.
def line_regions(st) -> dict:
    xy = np.asarray(st.xy, float)
    return {nm: min(REGIONS, key=lambda k: float(np.linalg.norm(xy[st.slice_of[nm][0]] - np.asarray(REGIONS[k], float))))
            for nm in st.names}



# One receiver's g25 network, with the training mean and sd it carries.
def load_g25(path: str):
    o = torch.load(path, map_location="cpu", weights_only=False)
    m = LinkNet(o["n_links"], o["out_dim"], "posterior", o["in_channels"])
    m.load_state_dict(o["state_dict"])
    m.eval()
    return m, np.asarray(o["mu"]), np.asarray(o["sd"])


# Every BatchNorm2d running statistic recomputed from this session's own calibration windows.
def adapt_batchnorm(heads, F, R) -> list:
    torch.set_num_threads(1)
    out = []
    for li, (m0, mu, sd) in enumerate(heads):
        m = copy.deepcopy(m0)
        bns = [q for q in m.modules() if isinstance(q, nn.BatchNorm2d)]
        for q in bns:
            q.reset_running_stats()
            q.momentum = None
            q.train()
        Xb = ((stack_link(F[:, [li]], R[:, [li]]) - mu) / sd).astype(np.float32)
        with torch.no_grad():
            for i in range(0, len(Xb), 32):
                m(torch.from_numpy(Xb[i:i + 32]))
        m.eval()
        out.append((m, mu, sd))
    return out


# (n, 3 * EMBED): each receiver's embedding of each window.
def embed_rows(heads, F, R, batch: int = 32) -> np.ndarray:
    torch.set_num_threads(1)
    parts = []
    for li, (m, mu, sd) in enumerate(heads):
        Xb = ((stack_link(F[:, [li]], R[:, [li]]) - mu) / sd).astype(np.float32)
        ch = []
        with torch.no_grad():
            for i in range(0, len(Xb), batch):
                ch.append(m.embed(torch.from_numpy(Xb[i:i + batch])).numpy())
        parts.append(np.concatenate(ch) if ch else np.zeros((0, 1), np.float32))
    return np.concatenate(parts, axis=1).astype(np.float32)
