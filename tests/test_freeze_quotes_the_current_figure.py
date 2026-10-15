"""A freeze's headline may not name a superseded figure, and a superseded figure must say so.

WHY THIS IS A TEST. On 2026-09-20 the freeze wrote a correct headline_semibounded of 62.50 percent
and then emitted a headline line quoting 57.5, which is the five-head POOL batch's number carried
forward in headline_numbers. Both blocks sat in the same file. A headline that names a superseded
number is exactly how a superseded number gets quoted, and this batch had just spent an evening
marking 64.17 percent unquotable for the same reason.

THE RULE. Where a freeze carries headline_semibounded, that is its headline: the emitted line
quotes it, any stale block beside it is labelled, and the superseded figure is named as superseded
in the payload rather than left to be inferred.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
# superseded freezes moved to runs/attempts/freezes/ on 2026-09-24; the rule still holds for every one of them
FREEZES = sorted((REPO / "runs").glob("TRACKING_FROZEN_*.json")) + sorted((REPO / "runs" / "attempts" / "freezes").glob("TRACKING_FROZEN_*.json"))


# test_the_freeze_stage_quotes_headline_semibounded_when_it_has_one read the source of g5_freeze, the
# freeze stage of 2026-09-20, which was removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
# The rule it guarded is still enforced on every freeze PAYLOAD by the test below.


@pytest.mark.parametrize("path", FREEZES, ids=lambda p: p.name)
def test_a_freeze_with_a_headline_figure_marks_the_superseded_one(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    hs = d.get("headline_semibounded")
    if hs is None:
        return
    assert "pct" in hs and "basis" in hs, f"{path.name}: headline_semibounded has no figure or basis"
    sup = hs.get("SUPERSEDED_AND_NOT_QUOTABLE")
    assert sup is not None and "pct" in sup and sup.get("why"), (
        f"{path.name}: a freeze that replaces a quoted figure must name the replaced one and say "
        f"why it is not quotable, or the old number stays in circulation")
    assert abs(float(sup["pct"]) - float(hs["pct"])) > 1e-9, (
        f"{path.name}: the superseded figure and the headline are the same number")
