# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The ONLY object an IDGP identification feature may receive.

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

FS = 150.0

PATHS = {
    "A_fwd": ((2.5, 0.0), (2.5, 5.0)), "A_rev": ((2.5, 5.0), (2.5, 0.0)),
    "B_fwd": ((0.0, 2.5), (5.0, 2.5)), "B_rev": ((5.0, 2.5), (0.0, 2.5)),
    "C_fwd": ((0.0, 0.0), (5.0, 5.0)), "C_rev": ((5.0, 5.0), (0.0, 0.0)),
    "D_fwd": ((0.0, 5.0), (5.0, 0.0)), "D_rev": ((5.0, 0.0), (0.0, 5.0)),
    "E_col1": ((0.5, 0.0), (0.5, 5.0)), "E_col5": ((4.5, 0.0), (4.5, 5.0)),
    "E_row1": ((0.0, 0.5), (5.0, 0.5)), "E_row5": ((0.0, 4.5), (5.0, 4.5)),
}
RIG_ROOM_A = {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}
RIG_DC2_IDSPOT = {"primary": {**RIG_ROOM_A, "RX2": (2.0, -0.5)},
                  "fallback": {**RIG_ROOM_A, "RX2": (1.5, -0.5)}}
LINKS = ("RX1", "RX2", "RX3")
ALLOWED_FIELDS = ("amp", "fs", "t_start", "t_end", "t_amp0", "path_id", "path_length_m", "rig",
                  "margin_s")
ROW_KEYS = ("session", "anon", "pass_id", "t_start_press", "t_end_press", "line")


# Function path length.
def path_length(path_id: str) -> float:
    a, b = PATHS[path_id]
    return float(np.hypot(b[0] - a[0], b[1] - a[1]))


# One walk, as identification is allowed to see it.
@dataclass(frozen=True)
class ContractPass:
    amp: np.ndarray
    fs: float
    t_start: float
    t_end: float
    t_amp0: float
    path_id: str
    path_length_m: float
    rig: tuple
    margin_s: float = 0.0

    # Function duration s.
    @property
    def duration_s(self) -> float:
        return float(self.t_end - self.t_start)

    # Function index of.
    def index_of(self, t: float) -> int:
        return int(round((t - self.t_amp0) * self.fs))

    # The amplitude strictly between the start and end presses, whatever the margin.
    def walk(self) -> np.ndarray:
        return self.amp[:, self.index_of(self.t_start):self.index_of(self.t_end), :]

    # Function rig dict.
    def rig_dict(self) -> dict:
        return dict(self.rig)


# PACE FROM WALK START AND END: protocol path length over the time between the two presses.
def s_se(p: ContractPass) -> float:
    return p.path_length_m / p.duration_s


# Build the ContractPass of one Room A pass from the id19 bank.
def from_bank(row: dict, margin_s: float = 0.0, rig: dict = None) -> ContractPass:
    from pipeline.identify.id19_bank import bank_path
    from pipeline.identify.id19_featbank import SC
    r = {k: row[k] for k in ROW_KEYS}
    d = np.load(bank_path(r))
    a = d["amp_raw"]
    i0, i1 = int(d["i_start"]), int(d["i_end"])
    m = int(round(margin_s * FS))
    lo, hi = i0 - m, i1 + m
    if lo < 0 or hi > a.shape[1]:
        raise ValueError(f"margin {margin_s} s runs outside the bank span")
    t0 = float(d["t0"])
    return ContractPass(amp=np.asarray(a[:, lo:hi, :][:, :, SC], np.float32), fs=FS,
                        t_start=float(r["t_start_press"]), t_end=float(r["t_end_press"]),
                        t_amp0=t0 + lo / FS, path_id=str(r["line"]),
                        path_length_m=path_length(str(r["line"])),
                        rig=tuple(sorted((rig or RIG_ROOM_A).items())), margin_s=float(margin_s))


# Function contract fields.
def contract_fields() -> tuple:
    return tuple(f.name for f in fields(ContractPass))


# Mean projected factor F per link along a path, by id15_factor_map, for late-fusion weights.
def mean_F(path_id: str, rig: dict, n: int = 501) -> dict:
    from pipeline.identify.id15_factor_map import score_segment
    a, b = PATHS[path_id]
    s = score_segment(a, b, n=n, tx=rig["TX"], rx={k: rig[k] for k in LINKS})
    return {k: s["per_link"][k]["mean_F"] for k in LINKS}
