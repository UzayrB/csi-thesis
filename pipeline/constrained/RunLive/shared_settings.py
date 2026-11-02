# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Settings shared across the tracker: folders, random seeds, the decoder's time step, walking-pace numbers...

from __future__ import annotations

import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ART_DIR = os.environ.get("TDR_ART_DIR") or os.path.join(REPO, "runs", "artefacts")

SIX = ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")

E_REG, E_POST = 20, 24

V_MEAN, V_SD, DT = 1.298, 0.123, 1.0

STRIDE = 0.5


# Nets.device() takes the Apple GPU when it exists; the GPU belongs to Identification.
def force_cpu() -> None:
    import torch
    torch.backends.mps.is_available = lambda: False


# The pace prior from PD_PACE_MEAN and PD_PACE_SD, set in every module that holds a copy (common, decoder...
def apply_pace() -> dict:
    global V_MEAN, V_SD
    mu, sd = os.environ.get("PD_PACE_MEAN"), os.environ.get("PD_PACE_SD")
    if not mu or not sd:
        return None
    import pipeline.constrained.RunLive.decoder_lines as D
    import pipeline.constrained.RunLive.decoder_v2 as D2
    mu, sd = float(mu), float(sd)
    V_MEAN, V_SD = mu, sd
    D.V_MEAN, D.V_SD = mu, sd
    D2.V_MEAN = mu
    D2._LT_CACHE.clear()
    return {"v_mean": mu, "v_sd": sd, "set_in": ["common", "decoder", "decoder2"],
            "source": "A1+A2 tape anchors (stage1_pace's method), Uzayr 29 Sep"}


WINDOW_S = 2.0


from dataclasses import dataclass


FS = 150.0


# One recording's windows in time order, with everything a decoder or a metric needs.
@dataclass
class Recording:

    session: str
    stem: str
    participant: str
    t0: np.ndarray
    t0_epoch: np.ndarray
    mode: np.ndarray
    pass_id: np.ndarray
    path_name: np.ndarray
    xy: np.ndarray
    cell_id: np.ndarray
    gap_flag: np.ndarray

    # The number of items.
    def __len__(self) -> int:
        return int(len(self.t0))

    # Function key.
    @property
    def key(self) -> str:
        return f"{self.participant}|{self.session}"

    # (pass_id, path_name, first_index, last_index) for each pass, in time order.
    def pass_spans(self) -> list:
        out = []
        for pid in sorted({int(p) for p in self.pass_id if p >= 0}):
            idx = np.flatnonzero(self.pass_id == pid)
            if len(idx):
                out.append((pid, str(self.path_name[idx[0]]), int(idx[0]), int(idx[-1])))
        return out


STRIDE_S = 0.5
