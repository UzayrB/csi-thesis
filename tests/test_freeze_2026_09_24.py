"""THE 2026-09-24 FREEZES ARE ENFORCED: the DC2 day design, the dc2b corrections and the both-directions capture.

`reports/tracking/dc2/2026-09-24_prereg-addendum-day-design.md` section 5. Written before any Room B data existed. A change
before Room B data gets a new dated freeze that supersedes these, never an edit; a change after is POST
HOC. Either way it starts with this test failing.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
TRACKING = REPO / "runs" / "TRACKING_FROZEN_2026-09-24.json"
IDENT = REPO / "runs" / "IDENTIFICATION_FROZEN_2026-09-24.json"
#: the freezes name each file by its path on the day (before the 1 October 2026 moves; tests/_restructure.py)
ADDENDUM = "reports/PREREG_DC2_ADDENDUM_2026-09-24.md"


#: RETIRED 2026-10-01: frozen files deleted that day with the DC2 tools (Uzayr), each checked in git at the last
#: commit that held it.
GONE_AT = {"tools/dc2_day_check.py": "5c49f09"}


def _h_or_git(p):
    if p in GONE_AT:
        import subprocess
        b = subprocess.run(["git", "show", f"{GONE_AT[p]}:{p}"], cwd=REPO, capture_output=True, check=True).stdout
        return hashlib.sha256(b).hexdigest()
    return _h(p)


def _h(p):
    from tests import _restructure as RS          # the file where it is now
    return hashlib.sha256((REPO / RS.current(p)).read_bytes()).hexdigest()


@pytest.mark.parametrize("freeze", [TRACKING, IDENT], ids=["tracking", "identification"])
def test_every_file_frozen_on_2026_09_24_is_unchanged(freeze):
    assert freeze.exists(), f"{freeze.name} is missing: the 2026-09-24 addendum names it"
    F = json.loads(freeze.read_text(encoding="utf-8"))
    assert F["sha256"], "a freeze with nothing in it"
    bad = [p for p, v in F["sha256"].items() if _h(p) != v]
    assert not bad, f"frozen on 2026-09-24 and changed since: {bad}. Supersede with a new dated freeze"


@pytest.mark.parametrize("freeze, prior", [
    (TRACKING, "runs/TRACKING_FROZEN_2026-09-23h.json"),
    (IDENT, "runs/IDENTIFICATION_FROZEN_2026-09-23g.json")], ids=["tracking", "identification"])
def test_each_freeze_hashes_the_addendum_and_references_the_one_before(freeze, prior):
    F = json.loads(freeze.read_text(encoding="utf-8"))
    assert ADDENDUM in F["sha256"]
    assert F["references"] == prior and (REPO / prior).exists()
    assert F["before_room_b_data"] is True


def test_the_frozen_code_is_the_code_the_day_plan_runs():
    T = json.loads(TRACKING.read_text(encoding="utf-8"))["sha256"]
    I = json.loads(IDENT.read_text(encoding="utf-8"))["sha256"]
    for p in ("pipeline/constrained/dc2b.py", "pipeline/constrained/dc2b_run.py",
              "pipeline/constrained/dc2b_pipeline.py", "pipeline/constrained/dc2b_scorerlock.py",
              "pipeline/constrained/dc2b_manifest.py"):
        assert p in T
    for p in ("pipeline/identify/capture_idboth.py", "pipeline/identify/idboth_view.py"):
        assert p in I


# Addendum 2026-09-24b: the corrections the hardware check found, and the two read-only checks
TRACKING_B = REPO / "runs" / "TRACKING_FROZEN_2026-09-24b.json"


def test_the_24b_freeze_is_unchanged_and_follows_24():
    assert TRACKING_B.exists(), "TRACKING_FROZEN_2026-09-24b.json is missing: addendum 24b names it"
    F = json.loads(TRACKING_B.read_text(encoding="utf-8"))
    assert F["references"] == "runs/TRACKING_FROZEN_2026-09-24.json" and F["before_room_b_data"] is True
    for p in ("reports/PREREG_DC2_ADDENDUM_2026-09-24b.md", "tools/dc2_day_check.py", "tools/dc2_verify_run.py"):
        assert p in F["sha256"]
    bad = [p for p, v in F["sha256"].items() if _h_or_git(p) != v]
    assert not bad, f"frozen in 24b and changed since: {bad}. Supersede with a new dated freeze"


# Addendum 2026-09-25: identification first, then tracking
@pytest.mark.parametrize("freeze, prior", [
    ("runs/TRACKING_FROZEN_2026-09-25.json", "runs/TRACKING_FROZEN_2026-09-24b.json"),
    ("runs/IDENTIFICATION_FROZEN_2026-09-25.json", "runs/IDENTIFICATION_FROZEN_2026-09-24.json")],
    ids=["tracking", "identification"])
def test_the_2026_09_25_freezes_are_unchanged_and_follow_on(freeze, prior):
    f = REPO / freeze
    assert f.exists(), f"{freeze} is missing: addendum 2026-09-25 names it"
    F = json.loads(f.read_text(encoding="utf-8"))
    assert F["references"] == prior and (REPO / prior).exists() and F["before_room_b_data"] is True
    assert "reports/PREREG_DC2_ADDENDUM_2026-09-25.md" in F["sha256"]
    bad = [p for p, v in F["sha256"].items() if _h(p) != v]
    assert not bad, f"frozen on 2026-09-25 and changed since: {bad}. Supersede with a new dated freeze"
