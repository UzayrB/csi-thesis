"""SHIP_PLAN.md step 2's code change: the `clean_1s_r0` display profile (clean_1s with the switch radius None, everything
else unchanged) as the live app's default, and the live tests that pin the profiles. Run once from the repository root;
each replacement must match exactly once, or nothing is written.

    python3 runs/switch_radius_ship_2026-10-14/apply_profile.py
"""

import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def edit(rel: str, reps: list) -> None:
    p = os.path.join(REPO, rel)
    s = open(p, encoding="utf-8").read()
    for a, b in reps:
        if s.count(a) != 1:
            raise SystemExit(f"STOP: {rel}: {a[:70]!r} found {s.count(a)} times")
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)
    print("edited", rel)


FM = [
    ('''#: (t_dec0 equals park_until), so compose_walk draws no glide frame, and rule 2a is retired for it (Uzayr, 14 Oct)
DISPLAY_PROFILES = {''',
     '''#: (t_dec0 equals park_until), so compose_walk draws no glide frame, and rule 2a is retired for it (Uzayr, 14 Oct).
#: "clean_1s_r0" (Uzayr's decision, 14 Oct; runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md): clean_1s with the switch's
#: 1.5 m radius condition removed (radius_m None), every other setting clean_1s's; chosen on the development rotations
#: (runs/switch_radius_2026-10-14) and confirmed on A3 and B2 (runs/switch_radius_a3b2_2026-10-14)
DISPLAY_PROFILES = {'''),
    ('''                 "source": "runs/head_offset_2026-10-14/DECISION_1p0.md (Uzayr, 14 Oct): clean with head offset 1.0 s"}}
DISPLAY_PROFILE = "clean_1s"''',
     '''                 "source": "runs/head_offset_2026-10-14/DECISION_1p0.md (Uzayr, 14 Oct): clean with head offset 1.0 s"},
    "clean_1s_r0": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                    "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                             "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": None}},
                    "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                    "source": "runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md (Uzayr, 14 Oct): clean_1s with the switch "
                              "radius removed"}}
DISPLAY_PROFILE = "clean_1s_r0"'''),
]

TESTS = [
    ('''    assert FM.DISPLAY_PROFILE == "clean_1s" and FM.DISPLAY_CANDIDATE == "K1gf"          # Uzayr, 14 Oct''',
     '''    assert FM.DISPLAY_PROFILE == "clean_1s_r0" and FM.DISPLAY_CANDIDATE == "K1gf"       # Uzayr, 14 Oct (no radius)'''),
    ('''    assert FM.end_head_for(None, 1.0, "final", "clean_1s") is None
''',
     '''    assert FM.end_head_for(None, 1.0, "final", "clean_1s") is None
    r0 = FM.DISPLAY_PROFILES["clean_1s_r0"]                                             # Uzayr, 14 Oct: no switch radius
    assert r0["sett"]["switch"] == {**one["sett"]["switch"], "radius_m": None} and one["sett"]["switch"]["radius_m"] == 1.5
    assert {k: v for k, v in r0["sett"].items() if k != "switch"} == {k: v for k, v in one["sett"].items() if k != "switch"}
    assert {k: v for k, v in r0.items() if k not in ("sett", "source")} == \\
        {k: v for k, v in one.items() if k not in ("sett", "source")}
    assert FM.end_head_for(None, 1.0, "final", "clean_1s_r0") is None
'''),
    ('''    assert mode_dir_for("start", None, "K1gf", "clean_1s", False) == "semi_disp-K1gf_prof-clean_1s"   # never the 0.75 s folders
''',
     '''    assert mode_dir_for("start", None, "K1gf", "clean_1s", False) == "semi_disp-K1gf_prof-clean_1s"   # never the 0.75 s folders
    assert mode_dir_for("start", None, "K1gf", "clean_1s_r0", False) == "semi_disp-K1gf_prof-clean_1s_r0"
'''),
    ('''    assert disp == {"pre_clean": 4.5, "clean": 3.0, "clean_1s": 3.0}''',
     '''    assert disp == {"pre_clean": 4.5, "clean": 3.0, "clean_1s": 3.0, "clean_1s_r0": 3.0}'''),
    ('''    for prof in ("pre_clean", "clean", "clean_1s"):''',
     '''    for prof in ("pre_clean", "clean", "clean_1s", "clean_1s_r0"):'''),
    ('''    assert got["clean_1s"]["files"] == got["clean"]["files"] and got["clean_1s"]["display_profile"] == "clean_1s"
''',
     '''    assert got["clean_1s"]["files"] == got["clean"]["files"] and got["clean_1s"]["display_profile"] == "clean_1s"
    assert got["clean_1s_r0"]["files"] == got["clean"]["files"] and got["clean_1s_r0"]["display_profile"] == "clean_1s_r0"
'''),
]


def main() -> int:
    # check every replacement first, so a mismatch writes nothing
    for rel, reps in (("pipeline/live/final_model.py", FM), ("tests/test_live_clean_display.py", TESTS)):
        s = open(os.path.join(REPO, rel), encoding="utf-8").read()
        for a, _b in reps:
            if s.count(a) != 1:
                raise SystemExit(f"STOP: {rel}: {a[:70]!r} found {s.count(a)} times; nothing written")
    edit("pipeline/live/final_model.py", FM)
    edit("tests/test_live_clean_display.py", TESTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
