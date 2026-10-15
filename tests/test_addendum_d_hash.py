"""Addendum D is protected by its freeze (23g). The DC2 identification scorers are pinned and cannot
gain a hash gate, so this test is the gate: it fails if addendum D, or anything freeze 23g records as
unchanged, differs from the hash recorded there."""

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FREEZE = os.path.join(ROOT, "runs", "IDENTIFICATION_FROZEN_2026-09-23g.json")


def sha(p):
    from tests import _restructure as RS          # the freeze names the old paths; the file where it is now
    with open(os.path.join(ROOT, RS.current(p)), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check(freeze_path=FREEZE):
    fz = json.load(open(freeze_path, encoding="utf-8"))
    bad = []
    if sha(fz["addendum_d"]) != fz["addendum_d_sha256"]:
        bad.append(fz["addendum_d"])
    for p, h in fz["unchanged_at_this_freeze"].items():
        if sha(p) != h:
            bad.append(p)
    for p, h in fz["references"].items():
        if sha(p) != h:
            bad.append(p)
    return bad


def test_addendum_d_matches_freeze_23g():
    assert check() == [], "changed after freeze 23g: " + ", ".join(check())


def test_the_check_fails_on_a_changed_hash(tmp_path):
    fz = json.load(open(FREEZE, encoding="utf-8"))
    fz["addendum_d_sha256"] = "0" * 64
    p = tmp_path / "freeze.json"
    p.write_text(json.dumps(fz))
    assert check(str(p)) == [fz["addendum_d"]]


def test_addendum_d_changes_no_analysis_and_predates_dc2():
    fz = json.load(open(FREEZE, encoding="utf-8"))
    assert fz["changes_no_analysis"] is True
    assert fz["written_before_any_DC2_data"] is True and fz["data_room_B_existed"] is False
