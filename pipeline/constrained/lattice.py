"""THE ONE LATTICE. Every tree the shipped system draws from or quotes, defined in one place.

Operator instruction 4, item 2, 2026-09-23 (verbatim in the BRIEF): "Adopt the press-aligned
lattice as the ONE lattice for everything drawn and quoted." A correctness fix, not an arm:
`reports/FINDING_lock_phase_2026-09-23.md` found the shipped lock drawn ahead of its evidence on
1080 of 1080 passes on the grid lattice, and the press-aligned lattice (`y4_pressalign`) removes it
by construction, 0 of 1080.

WHY ONE MODULE. The shipped roots were hard-coded in seven places (the root defaults, the import
guard, `n2_arms`, the three 1 s trees, the g100 region head, the display head, the live runner's
heads). Changing seven literals is how one gets missed. Every one now reads from here.

`TDR_LATTICE=grid` reproduces every figure quoted before 2026-09-23d on the trees they were
measured on. It is for reproduction only and is never the shipped configuration.

Standard library only, so the import guard may import it before any pipeline module.
"""

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

#: the shipped lattice since 2026-09-23d
SHIPPED = "pressalign"

#: THE PRESS PHASE, shared by the offline cutter (`y4_pressalign`) and the live engine. A window
#: starts this long AFTER each press rather than on it: on the press itself the first window's
#: midpoint is the press to the last bit and `label_window` would call it walk or walk_edge by
#: float rounding (measured, 9 of 20 passes). 2 microseconds is 1/3300 of a sample period.
PRESS_EPS_S = 2e-6
LATTICE = os.environ.get("TDR_LATTICE", SHIPPED)
if LATTICE not in _TREES:
    raise ValueError(f"TDR_LATTICE={LATTICE!r}: must be one of {sorted(_TREES)}")

#: the literal every stage module passes to `_guard.assert_isolated`, which means "the shipped
#: half-stride tree", whichever lattice that currently is
LEGACY_HALF = os.path.join(REPO_ROOT, "runs", "artefacts_half")


def windows_root() -> str:
    """The window tree, relative to the repository, as TDR_WINDOWS_ROOT expects it."""
    return _TREES[LATTICE]["windows"]


def half_art_dir() -> str:
    """The 0.5 s head's artefact tree, absolute, as TDR_ART_DIR expects it."""
    return os.path.join(REPO_ROOT, _TREES[LATTICE]["half"])


def one_s_trees() -> dict:
    """{seed: tree} for the three 1 s heads, relative, as `g2_multihead.ONE_S_TREES` uses them."""
    return dict(_TREES[LATTICE]["one_s"])


def g100_tree() -> str:
    return _TREES[LATTICE]["g100"]


def dispend_tree() -> str:
    """The DISP_END display head's tree, absolute, as `s2a_dispend.END_ART` uses it."""
    return os.path.join(REPO_ROOT, _TREES[LATTICE]["dispend"])


def canonical_art(want: str) -> str:
    """Map the legacy `runs/artefacts_half` literal to the active lattice's half tree."""
    if os.path.abspath(want) == LEGACY_HALF:
        return half_art_dir()
    return want


def gt_path(session: str, stem: str) -> str:
    """A recording's ground-truth sidecar. Room and data root from the environment, defaults Room A.

    DC2 (2026-09-23d) reads Room B through a view directory of symlinks, so `data/` stays read only;
    `TDR_DATA_ROOT` points at that view and `TDR_ROOM` names the room. With neither set this is
    `data/room_A/...`, exactly the path every reader hard-coded before.
    """
    return os.path.join(os.environ.get("TDR_DATA_ROOT", "data"), os.environ.get("TDR_ROOM", "room_A"),
                        f"session_{session}", f"{stem}.gt.json")


def test_tag_override(session: str):
    """The posterior tag for a TEST session that is not one of Room A's, or None.

    `TDR_TEST_TAG_MAP` is JSON, {session: tag}. Empty by default, so every Room A lookup is unchanged.
    DC2 maps each Room B session to the Room A heads' tag.
    """
    import json as _json
    raw = os.environ.get("TDR_TEST_TAG_MAP", "")
    return (_json.loads(raw).get(session) if raw else None)
