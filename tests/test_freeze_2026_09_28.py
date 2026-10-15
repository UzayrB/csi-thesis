"""THE 2026-09-28 IDENTIFICATION FREEZE IS ENFORCED: addendum E, the press relabel, and P1-REV and P7.

`reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_E.md` section 9. Written after both DC2 days existed and
before any identification figure was computed. A change after it is POST HOC and needs a new dated
freeze that supersedes this one, never an edit; either way it starts with this test failing.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib

from tests import _restructure as RS

REPO = pathlib.Path(__file__).resolve().parents[1]
FREEZE = REPO / "runs" / "IDENTIFICATION_FROZEN_2026-09-28.json"
PRIOR = "runs/IDENTIFICATION_FROZEN_2026-09-25.json"
MUST = ("reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_E.md", "runs/identify/dc2/relabel_manifest.json",
        "pipeline/identify/idrelabel.py", "pipeline/identify/idsec_view.py",
        "pipeline/identify/idsec_dc2_score.py", "tests/test_idrelabel.py", "tests/test_idsec_dc2_score.py")


def _h(p):
    return RS.frozen_sha(p)


def test_every_file_frozen_on_2026_09_28_is_unchanged():
    assert FREEZE.exists(), f"{FREEZE.name} is missing: addendum E names it"
    F = json.loads(FREEZE.read_text(encoding="utf-8"))
    bad = [p for p, v in F["sha256"].items() if _h(p) != v]
    assert not bad, f"frozen on 2026-09-28 and changed since: {bad}. Supersede with a new dated freeze"


def test_the_freeze_holds_addendum_e_the_relabel_and_the_secondary_scorer():
    F = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert set(MUST) <= set(F["sha256"])
    assert F["references"] == PRIOR and (REPO / PRIOR).exists()
    assert F["before_room_b_data"] is False and F["before_any_identification_figure"] is True


def test_the_scorer_gates_on_the_files_this_freeze_holds():
    from pipeline.identify import idsec_dc2_score as S
    F = json.loads(FREEZE.read_text(encoding="utf-8"))["sha256"]
    assert S.FREEZE_28 == "runs/IDENTIFICATION_FROZEN_2026-09-28.json"
    assert S.ADDENDUM_E in F and S.MANIFEST in F


def test_the_frozen_manifest_is_the_one_the_rule_writes():
    """The rule, re-applied to the capture now, gives the frozen manifest's changes exactly."""
    from pipeline.identify import idrelabel as R
    src = REPO / R.SRC
    if not src.is_dir():
        return                                              # a checkout without data/: the hash test stands
    M = json.loads((REPO / R.MANIFEST).read_text(encoding="utf-8"))
    cwd = os.getcwd()
    try:
        os.chdir(REPO)
        again = R.scan(R.SRC)
    finally:
        os.chdir(cwd)
    assert M["rule"] == R.RULE and M["rule_id"] == R.RULE_ID
    assert again["changes"] == M["changes"] and again["blocks_scanned"] == M["blocks_scanned"]
