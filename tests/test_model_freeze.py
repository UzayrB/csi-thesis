"""THE DC2 MODEL FREEZE (23h) IS ENFORCED, NOT REMEMBERED.

`reports/tracking/dc2/model-freeze.md`: "No model change is made until the Room B analysis." Every code and model
file DC2 runs is hashed in `runs/TRACKING_FROZEN_2026-09-23h.json`; this test re-hashes them. A document
may change only through a dated addendum that records its new hash (the DC2 pre-registration's section 13,
operator instruction 8). A change after Room B data exists is POST HOC and must say so, which starts with
this test failing.

THE RESTRUCTURE OF 2026-10-01 (reports/project/repository/2026-10-01_pipeline-restructure.md), after the Room B analysis,
moved frozen code files and rewrote their import lines. A frozen code file is therefore checked at the
restructure's base commit, and its current version may differ only in path lines (tests/_restructure.py).
"""

from __future__ import annotations

import glob
import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
FREEZE = REPO / "runs" / "TRACKING_FROZEN_2026-09-23h.json"


def _h(p):
    from tests import _restructure as RS          # the file where it is now (freezes name the old paths)
    return hashlib.sha256((REPO / RS.current(p)).read_bytes()).hexdigest()


def _freeze():
    if not FREEZE.exists():
        pytest.skip("the DC2 model freeze is not present")
    return json.loads(FREEZE.read_text(encoding="utf-8"))["DC2_MODEL_FREEZE"]


def test_every_frozen_code_file_is_unchanged():
    from tests import _restructure as RS
    code = _freeze()["code_sha256"]
    bad = [p for p, v in code.items() if RS.sha(RS.at_base(p)) != v]
    assert not bad, f"code frozen for DC2 had changed before the restructure: {bad}"
    edited = {p: RS.non_mechanical_changes(p) for p in code if p.endswith(".py")}
    edited = {p: d for p, d in edited.items() if d}
    assert not edited, f"the restructure changed frozen code beyond path lines: {edited}"


def test_every_frozen_model_file_is_unchanged():
    D = _freeze()
    assert len(D["model_sha256"]) == 18
    bad = [p for p, v in D["model_sha256"].items() if _h(p) != v]
    assert not bad, f"model files frozen for DC2 have changed: {bad}"


def test_documents_change_only_through_a_recorded_addendum():
    D = _freeze()
    recorded = {}
    for a in sorted(glob.glob(str(REPO / "runs" / "TRACKING_FROZEN_2026-09-23h_ADDENDUM*.json"))):
        A = json.loads(pathlib.Path(a).read_text(encoding="utf-8"))
        if A.get("PREREG_DC2_new_sha256"):
            recorded["reports/PREREG_DC2_crossroom_2026-09-22.md"] = A["PREREG_DC2_new_sha256"]
        # addendum C (2026-10-01) and later: any document's new hash, with the decisions that changed it
        recorded.update(A.get("documents_new_sha256") or {})
    for p, v in D["doc_sha256"].items():
        assert _h(p) in (v, recorded.get(p)), (
            f"{p} changed without a recorded addendum; the DC2 freeze documents change only by one")


# Addendum B (2026-09-24) closes the gap the cleanup recorded: dc2_run.py copies the half tree's reader
# models and posteriors for each training session, and 23h did not hash them.
ADDENDUM_B = REPO / "runs" / "TRACKING_FROZEN_2026-09-23h_ADDENDUM_B.json"
HALF = "runs/artefacts_s0.5_pressalign_half"


def _addendum_b():
    _freeze()
    assert ADDENDUM_B.exists(), "addendum B is missing: the half tree's reader files DC2 copies are unhashed"
    return json.loads(ADDENDUM_B.read_text(encoding="utf-8"))


def test_the_reader_files_dc2_copies_are_unchanged():
    R = _addendum_b()["reader_sha256"]
    assert len(R) == 12
    bad = [p for p, v in R.items() if _h(p) != v]
    assert not bad, f"reader files DC2 copies from the half tree have changed: {bad}"


def test_addendum_b_covers_every_reader_file_dc2_copies():
    # dc2_run.do_heads' copy rule (t2_embed.tag_for_session): for each training session, the first
    # pairing that tests it alone
    from pipeline.constrained.common import E_POST, pairings, tag_of

    want = set()
    for sess in ("01", "02", "03"):
        t = next(tag_of(tr, te, False) for tr, te in pairings() if te == (sess,) and tr != te)
        want |= {f"{HALF}/models/{t}_g25_e{E_POST}_s0_link{li}.pt" for li in range(3)}
        want.add(f"{HALF}/posteriors/{t}_g25_e{E_POST}_s0_full.npz")
    assert set(_addendum_b()["reader_sha256"]) == want
