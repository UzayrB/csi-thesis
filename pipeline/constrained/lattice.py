# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: THE ONE LATTICE.

from __future__ import annotations

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

LEGACY_HALF = os.path.join(REPO_ROOT, "runs", "artefacts_half")


# The window tree, relative to the repository, as TDR_WINDOWS_ROOT expects it.
def windows_root() -> str:
    return _TREES[LATTICE]["windows"]


# The 0.5 s head's artefact tree, absolute, as TDR_ART_DIR expects it.
def half_art_dir() -> str:
    return os.path.join(REPO_ROOT, _TREES[LATTICE]["half"])


# {seed: tree} for the three 1 s heads, relative, as g2_multihead.ONE_S_TREES uses them.
def one_s_trees() -> dict:
    return dict(_TREES[LATTICE]["one_s"])


# Function g100 tree.
def g100_tree() -> str:
    return _TREES[LATTICE]["g100"]


# The DISP_END display head's tree, absolute, as s2a_dispend.END_ART uses it.
def dispend_tree() -> str:
    return os.path.join(REPO_ROOT, _TREES[LATTICE]["dispend"])


# Map the legacy runs/artefacts_half literal to the active lattice's half tree.
def canonical_art(want: str) -> str:
    if os.path.abspath(want) == LEGACY_HALF:
        return half_art_dir()
    return want


# A recording's ground-truth sidecar.
def gt_path(session: str, stem: str) -> str:
    return os.path.join(os.environ.get("TDR_DATA_ROOT", "data"), os.environ.get("TDR_ROOM", "room_A"),
                        f"session_{session}", f"{stem}.gt.json")


# The posterior tag for a TEST session that is not one of Room A's, or None.
def test_tag_override(session: str):
    import json as _json
    raw = os.environ.get("TDR_TEST_TAG_MAP", "")
    return (_json.loads(raw).get(session) if raw else None)
