"""The corrected DC2 day check (tools/dc2b_day_check.py): the cross-day manifest fault is gone, and a
manifest session with no folder on disk is still reported."""

import os

from pipeline.constrained import dc2b
# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# from tools import dc2b_day_check as C


def _room(tmp_path, days=("B1", "B2")):
    room = tmp_path / "room_B"
    for d in days:
        s = room / f"session_{d}"
        s.mkdir(parents=True)
        (s / f"participant_PA6_C_walk.gt.json").write_text("{}")
        (s / f"participant_PA5_walk.gt.json").write_text("{}")
    return room


def _man():
    one = {"calibration_recordings": ["participant_PA6_C_walk"], "aborted": {}}
    return {"sessions": {"B1": dict(one), "B2": dict(one)}}


def test_pinned_check_reports_the_other_day(tmp_path):
    room = _room(tmp_path)
    bad = dc2b.manifest_problems(_man(), {"B1": str(room / "session_B1")})
    assert any("'B2' has no folder" in b for b in bad)


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_corrected_check_passes_when_both_folders_exist(tmp_path):
#     room = _room(tmp_path)
#     for day in ("B1", "B2"):
#         assert C.manifest_problems(_man(), {day: str(room / f"session_{day}")}) == []


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_corrected_check_still_reports_a_missing_folder(tmp_path):
#     room = _room(tmp_path, days=("B1",))
#     bad = C.manifest_problems(_man(), {"B1": str(room / "session_B1")})
#     assert bad == ["manifest session 'B2' has no folder data/room_B/session_B2"]


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_corrected_check_keeps_the_other_checks(tmp_path):
#     room = _room(tmp_path)
#     man = _man()
#     man["sessions"]["B1"]["calibration_recordings"] = ["participant_Nobody_C_walk"]
#     bad = C.manifest_problems(man, {"B1": str(room / "session_B1")})
#     assert any("participant_Nobody_C_walk is not in" in b for b in bad)


# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code it needed is in git at 5c49f09.
# def test_main_restores_the_pinned_function():
#     try:
#         C.main(["--day", "1", "--data-root", os.devnull])
#     except SystemExit:
#         pass
#     except Exception:
#         pass
#     assert dc2b.manifest_problems is C._ORIGINAL
