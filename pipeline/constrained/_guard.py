"""The isolation guard, in one place. Imports only the standard library, so it is safe to call
BEFORE any pipeline module is imported, which is the whole point.

THE GUARD EXISTS FOR ONE DANGER: a stage running on a differently-strided tree while the artefact
root still points at a shipped one, because the feature cache is keyed without the stride in its
filename and 6.3 GB of shipped features would be overwritten.

TWO THINGS SATISFY IT, and both are safe:
  the roots ALREADY point where this stage needs them, which is the case when a later stage
    imports this one as a library after setting them itself; or
  no pipeline module has been imported yet, so setting them now will take effect.

The bare import-order form, without the first clause, broke a library caller four separate times.
tests/test_entrypoint_guard_form.py bans it.
"""

from __future__ import annotations

import os
import sys


def assert_isolated(module_name: str, want_art_dir: str) -> None:
    # THE ONE LATTICE, 2026-09-23d. Every stage passes the literal runs/artefacts_half, meaning "the
    # shipped half-stride tree"; which tree that is now lives in `lattice`, stdlib only.
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
