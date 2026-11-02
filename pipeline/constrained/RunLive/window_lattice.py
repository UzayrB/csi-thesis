# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Where each set of windows lives on disk, and the one shared grid of window start times.

from __future__ import annotations

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_TREES = {
    "pressalign": {
        "windows": os.path.join("runs", "constrained", "windows_s0.5_pressalign"),
        "half": os.path.join("runs", "artefacts_s0.5_pressalign_half"),
        "one_s": {0: os.path.join("runs", "artefacts_s0.5_pressalign_fh1s"),
                  1: os.path.join("runs", "artefacts_s0.5_pressalign_g1s1"),
                  2: os.path.join("runs", "artefacts_s0.5_pressalign_g1s2")},
        "g100": os.path.join("runs", "artefacts_s0.5_pressalign_g100"),
        "dispend": os.path.join("runs", "artefacts_s0.5_pressalign_dispend"),
    },
    "grid": {
        "windows": os.path.join("runs", "constrained", "windows_half"),
        "half": os.path.join("runs", "artefacts_half"),
        "one_s": {0: os.path.join("runs", "artefacts_fh1s"),
                  1: os.path.join("runs", "artefacts_g1s1"),
                  2: os.path.join("runs", "artefacts_g1s2")},
        "g100": os.path.join("runs", "artefacts_g1g100s0"),
        "dispend": os.path.join("runs", "artefacts_dispend"),
    },
}

SHIPPED = "pressalign"

PRESS_EPS_S = 2e-6
LATTICE = os.environ.get("TDR_LATTICE", SHIPPED)
if LATTICE not in _TREES:
    raise ValueError(f"TDR_LATTICE={LATTICE!r}: must be one of {sorted(_TREES)}")

