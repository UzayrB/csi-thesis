# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The isolation guard, in one place.

from __future__ import annotations

import os
import sys


# Function assert isolated.
def assert_isolated(module_name: str, want_art_dir: str) -> None:
    from pipeline.constrained.lattice import canonical_art
    want_art_dir = canonical_art(want_art_dir)
    already = os.path.abspath(os.environ.get("TDR_ART_DIR", "")) == os.path.abspath(want_art_dir)
    fresh = "pipeline.constrained.common" not in sys.modules
    if already or fresh:
        return
    raise AssertionError(
        f"{module_name}: the artefact root is "
        f"{os.environ.get('TDR_ART_DIR')!r}, not {want_art_dir!r}, and pipeline.constrained.common "
        f"is already imported so setting it now would not take effect. Either run this module as "
        f"the entry point, or set the roots before importing any pipeline module.")
