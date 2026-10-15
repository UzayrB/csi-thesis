"""Step 5's code change (DECISION_1p0.md), applied once step 4 has passed: the `clean_1s` display profile (the clean display
with head_offset_s 1.0, everything else unchanged) as the live app's default, and the live tests that pin the profiles.
Run once from the repository root; each replacement must match exactly once.

    python3 runs/head_offset_2026-10-14/apply_profile.py
"""

import os
import sys

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
    ('''#: K1gf (the glide starts at the first anchor frame). Both models (final, zeroshot) draw with the same profile
DISPLAY_PROFILES = {''',
     '''#: K1gf (the glide starts at the first anchor frame). Both models (final, zeroshot) draw with the same profile.
#: "clean_1s" (Uzayr's decision, 14 Oct; runs/head_offset_2026-10-14/DECISION_1p0.md): the clean display with the head
#: offset 1.0 s, each position drawn at its own window's centre; every other setting is clean's. Its anchor span is zero
#: (t_dec0 equals park_until), so compose_walk draws no glide frame, and rule 2a is retired for it (Uzayr, 14 Oct)
DISPLAY_PROFILES = {'''),
    ('''              "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
              "source": "runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json (6e225f6a)"}}
DISPLAY_PROFILE = "clean"''',
     '''              "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
              "source": "runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json (6e225f6a)"},
    "clean_1s": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                 "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                          "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}},
                 "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                 "source": "runs/head_offset_2026-10-14/DECISION_1p0.md (Uzayr, 14 Oct): clean with head offset 1.0 s"}}
DISPLAY_PROFILE = "clean_1s"'''),
]

TESTS = [
    ('''    assert FM.DISPLAY_PROFILE == "clean" and FM.DISPLAY_CANDIDATE == "K1gf"
    assert FM.end_head_for(None, 1.0, "final", "clean") is None''',
     '''    assert FM.DISPLAY_PROFILE == "clean_1s" and FM.DISPLAY_CANDIDATE == "K1gf"          # Uzayr, 14 Oct
    assert FM.end_head_for(None, 1.0, "final", "clean") is None
    one = FM.DISPLAY_PROFILES["clean_1s"]
    assert one["sett"]["head_offset_s"] == 1.0 and c["sett"]["head_offset_s"] == 0.75
    assert {k: v for k, v in one.items() if k not in ("sett", "source")} == {k: v for k, v in c.items() if k not in ("sett", "source")}
    assert {k: v for k, v in one["sett"].items() if k != "head_offset_s"} == {k: v for k, v in c["sett"].items() if k != "head_offset_s"}
    assert FM.end_head_for(None, 1.0, "final", "clean_1s") is None'''),
    ('''    assert mode_dir_for("none", 4, "K1gf", "clean", False) == "unconstrained_m4_disp-K1gf"''',
     '''    assert mode_dir_for("none", 4, "K1gf", "clean", False) == "unconstrained_m4_disp-K1gf"
    assert mode_dir_for("start", None, "K1gf", "clean_1s", False) == "semi_disp-K1gf_prof-clean_1s"   # never the 0.75 s folders'''),
    ('''    assert disp == {"pre_clean": 4.5, "clean": 3.0}                     # the display's spread does follow the profile''',
     '''    assert disp == {"pre_clean": 4.5, "clean": 3.0, "clean_1s": 3.0}   # the display's spread does follow the profile'''),
    ('''    for prof in ("pre_clean", "clean"):
        monkeypatch.setattr(FM, "DISPLAY_PROFILE", prof)
        M.build("zeroshot")
        got[prof] = json.load(open(tmp_path / "zeroshot.json", encoding="utf-8"))
        os.remove(tmp_path / "zeroshot.json")''',
     '''    for prof in ("pre_clean", "clean", "clean_1s"):
        monkeypatch.setattr(FM, "DISPLAY_PROFILE", prof)
        M.build("zeroshot")
        got[prof] = json.load(open(tmp_path / "zeroshot.json", encoding="utf-8"))
        os.remove(tmp_path / "zeroshot.json")
    assert got["clean_1s"]["files"] == got["clean"]["files"] and got["clean_1s"]["display_profile"] == "clean_1s"'''),
]

NEW_TEST = '''

def test_the_1s_offset_has_an_empty_anchor_span_and_an_inert_glide(st):
    """clean_1s (Uzayr, 14 Oct): at head offset 1.0 s the first decoded frame is at press + 2.0 s (t_dec0 equals
    park_until), so compose_walk draws no anchor frame; the glide code runs on an empty span without error (no division by
    the zero span), every frame from press + 2.0 s on is a decoded position on the locked line, and the frames from t_dec0
    on equal those composed with the glide switched off (anchor "hold")."""
    from pipeline.live import display as D
    line = st.names[0]
    a, b = st.slice_of[line]
    P = 100.0
    t = np.array([P - 1.0 + 0.5 * i for i in range(40)])
    lpath = [{"state": int(min(a + i, b - 1)), "line": line, "evidence_window": i, "window": i} for i in range(40)]
    L = {"lock_line": line, "path": lpath, "paths_alt": {"end": lpath}}
    frames = [round(P - 10.0 + 0.03 + 0.1 * k, 4) for k in range(200)]
    out = {}
    for anchor in ("glide_first", "hold"):
        sett = {"shipped_display": "DISP_END", "switch": None, "path_lag_extra": 1, "anchor": anchor, "shift_w": 1.0,
                "head_offset_s": 1.0}
        out[anchor] = D.compose_walk(st, L, 0, t, P, None, [x for x in frames if x >= P], None, None, sett, None)
    drawn, _sw, facts = out["glide_first"]
    assert facts["t_dec0"] == facts["park_until"] == P + 2.0
    assert not [x for x in drawn if facts["park_until"] <= x < facts["t_dec0"]], "no anchor frame at 1.0 s"
    ea, eb = (np.asarray(st.xy[a], float), np.asarray(st.xy[b - 1], float))
    for x, p in drawn.items():
        if x >= P + 2.0:
            u = float(np.clip(np.dot(np.asarray(p) - ea, eb - ea) / float(np.dot(eb - ea, eb - ea)), 0.0, 1.0))
            assert float(np.hypot(*(np.asarray(p) - (ea + u * (eb - ea))))) <= 1e-6, f"frame {x} is off the locked line"
    assert out["hold"][0] == drawn, "with no anchor span the glide changes nothing"
    assert facts["min_margin_s"] is not None and facts["min_margin_s"] >= -D.TOL
'''


if __name__ == "__main__":
    edit("pipeline/live/final_model.py", FM)
    edit("tests/test_live_clean_display.py", TESTS)
    with open(os.path.join(REPO, "tests", "test_live_clean_display.py"), "a", encoding="utf-8") as f:
        f.write(NEW_TEST)
    print("appended the 1.0 s test")
    sys.exit(0)
