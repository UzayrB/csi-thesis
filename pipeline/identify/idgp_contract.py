"""IDGP contract. The ONLY object an IDGP identification feature may receive (brief 2026-09-23f).

THE IDENTIFICATION CONTRACT, decided by Uzayr. In DC2, identification and tracking are separate, no
ground-truth labels are recorded for identification, and each person walks one path. A model may
therefore use exactly:
  1. the CSI from the receivers between the walk's start and end;
  2. the walk's start and end times (in Room A, the first and last anchor presses of the pass,
     the 0 m and 5 m marks);
  3. the path's identity and length, known by protocol.
It may NOT use the intermediate anchor presses, interpolated positions, any other label, or anything
produced by the tracking branch.

`ContractPass` carries those three things and the rig's node positions (protocol geometry, the same
kind of knowledge as the path) and nothing else. `from_bank()` is the one door from the id19 signal
bank to a ContractPass. It reads the bank file's amplitude and its start and end indices; it never
reads the anchor times, the walk_edge indices, the RSSI or the gap arrays, and the pass it returns
has no field that could carry a label. `tests/test_idgp_contract.py` asserts the field set, the
segment length, that a row stripped to the allowed keys builds the identical pass, and that no
tracking module is loaded while the arms run.

The optional margin (0 or 0.5 s either side of the presses) exists for the cadence variant the brief
pre-registers in section 3 and for nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

FS = 150.0

#: the twelve taped lines, protocol constants (endpoints in room metres). The test compares them
#: with `pipeline.constrained.paths.load_paths()`, so they cannot drift from the tape, and no arm
#: module imports the tracking package to get them.
PATHS = {
    "A_fwd": ((2.5, 0.0), (2.5, 5.0)), "A_rev": ((2.5, 5.0), (2.5, 0.0)),
    "B_fwd": ((0.0, 2.5), (5.0, 2.5)), "B_rev": ((5.0, 2.5), (0.0, 2.5)),
    "C_fwd": ((0.0, 0.0), (5.0, 5.0)), "C_rev": ((5.0, 5.0), (0.0, 0.0)),
    "D_fwd": ((0.0, 5.0), (5.0, 0.0)), "D_rev": ((5.0, 0.0), (0.0, 5.0)),
    "E_col1": ((0.5, 0.0), (0.5, 5.0)), "E_col5": ((4.5, 0.0), (4.5, 5.0)),
    "E_row1": ((0.0, 0.5), (5.0, 0.5)), "E_row5": ((0.0, 4.5), (5.0, 4.5)),
}
#: Room A's rig, fixed for every Room A recording
RIG_ROOM_A = {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}
#: DC2's identification rig: RX2 at the identification spot (primary or fallback), others as Room A
RIG_DC2_IDSPOT = {"primary": {**RIG_ROOM_A, "RX2": (2.0, -0.5)},
                  "fallback": {**RIG_ROOM_A, "RX2": (1.5, -0.5)}}
LINKS = ("RX1", "RX2", "RX3")
#: the fields a ContractPass may have, and the test asserts it has exactly these
ALLOWED_FIELDS = ("amp", "fs", "t_start", "t_end", "t_amp0", "path_id", "path_length_m", "rig",
                  "margin_s")
#: the keys of an inventory row that from_bank may read: where the bank file is, and the presses
ROW_KEYS = ("session", "anon", "pass_id", "t_start_press", "t_end_press", "line")


def path_length(path_id: str) -> float:
    a, b = PATHS[path_id]
    return float(np.hypot(b[0] - a[0], b[1] - a[1]))


@dataclass(frozen=True)
class ContractPass:
    """One walk, as identification is allowed to see it.

    amp            (3, n, n_sub) amplitude of RX1, RX2, RX3 on the common 150 Hz grid, from
                   t_start - margin_s to t_end + margin_s
    t_start, t_end the walk's start and end (host clock, seconds)
    t_amp0         the time of amp[:, 0]
    path_id        the protocol path, e.g. "A_fwd"
    path_length_m  its protocol length
    rig            node positions by name, TX first
    """
    amp: np.ndarray
    fs: float
    t_start: float
    t_end: float
    t_amp0: float
    path_id: str
    path_length_m: float
    rig: tuple
    margin_s: float = 0.0

    @property
    def duration_s(self) -> float:
        return float(self.t_end - self.t_start)

    def index_of(self, t: float) -> int:
        return int(round((t - self.t_amp0) * self.fs))

    def walk(self) -> np.ndarray:
        """The amplitude strictly between the start and end presses, whatever the margin."""
        return self.amp[:, self.index_of(self.t_start):self.index_of(self.t_end), :]

    def rig_dict(self) -> dict:
        return dict(self.rig)


def s_se(p: ContractPass) -> float:
    """PACE FROM WALK START AND END: protocol path length over the time between the two presses."""
    return p.path_length_m / p.duration_s


def from_bank(row: dict, margin_s: float = 0.0, rig: dict = None) -> ContractPass:
    """Build the ContractPass of one Room A pass from the id19 bank. Reads only ROW_KEYS."""
    from pipeline.identify.id19_bank import bank_path
    from pipeline.identify.id19_featbank import SC
    r = {k: row[k] for k in ROW_KEYS}                    # nothing else of the row is visible below
    d = np.load(bank_path(r))
    a = d["amp_raw"]
    i0, i1 = int(d["i_start"]), int(d["i_end"])
    m = int(round(margin_s * FS))
    lo, hi = i0 - m, i1 + m
    if lo < 0 or hi > a.shape[1]:
        raise ValueError(f"margin {margin_s} s runs outside the bank span")
    t0 = float(d["t0"])                                   # time of bank sample 0
    return ContractPass(amp=np.asarray(a[:, lo:hi, :][:, :, SC], np.float32), fs=FS,
                        t_start=float(r["t_start_press"]), t_end=float(r["t_end_press"]),
                        t_amp0=t0 + lo / FS, path_id=str(r["line"]),
                        path_length_m=path_length(str(r["line"])),
                        rig=tuple(sorted((rig or RIG_ROOM_A).items())), margin_s=float(margin_s))


def contract_fields() -> tuple:
    return tuple(f.name for f in fields(ContractPass))


def mean_F(path_id: str, rig: dict, n: int = 501) -> dict:
    """Mean projected factor F per link along a path, by id15_factor_map, for late-fusion weights."""
    from pipeline.identify.id15_factor_map import score_segment
    a, b = PATHS[path_id]
    s = score_segment(a, b, n=n, tx=rig["TX"], rx={k: rig[k] for k in LINKS})
    return {k: s["per_link"][k]["mean_F"] for k in LINKS}
