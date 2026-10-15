"""The clean display (runs/clean_display_2026-10-10/PLAN.md): the profiles, the rule 2a fix K1gf, and the scorer's form.

K1gf's glide starts at the first anchor frame, so that frame is the locked line's entry exactly (rule 2a as written), and
nothing from the first decoded frame on differs from K1g. Tested on compose_walk itself, with a frame grid that is not
aligned to the press (the case that broke rule 2a: the first frame after the park lands part-way into the glide).
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def st():
    cwd = os.getcwd()
    os.chdir(REPO)                                        # load_paths reads the sidecars relative to the repository
    try:
        from pipeline.constrained.paths import PathStates
        return PathStates()
    finally:
        os.chdir(cwd)


def _walk(st, anchor: str):
    """compose_walk on a synthetic walk along one line: windows every 0.5 s with t[lo] + 1.0 = press, the dot's path
    advancing one state (0.25 m) per window, and frames on a 0.1 s grid offset 0.03 s from the press."""
    from pipeline.live import display as D
    line = st.names[0]
    a, b = st.slice_of[line]
    P = 100.0
    t = np.array([P - 1.0 + 0.5 * i for i in range(40)])
    lpath = [{"state": int(min(a + i, b - 1)), "line": line, "evidence_window": i, "window": i} for i in range(40)]
    L = {"lock_line": line, "path": lpath, "paths_alt": {"end": lpath}}
    frames = [round(P - 10.0 + 0.03 + 0.1 * k, 4) for k in range(200)]
    sett = {"shipped_display": "DISP_END", "switch": None, "path_lag_extra": 1, "anchor": anchor,
            "shift_w": 1.0, "head_offset_s": 0.75}
    drawn, _sw, facts = D.compose_walk(st, L, 0, t, P, None, [x for x in frames if x >= P], None, None, sett, None)
    return P, drawn, facts


def test_glide_first_puts_the_first_anchor_frame_on_the_entry(st):
    from pipeline.live.app_score import GLIDE_ENTRY_M
    P, drawn, facts = _walk(st, "glide_first")
    first = min(x for x in drawn if x >= P + 2.0 - 1e-4)
    assert first < facts["t_dec0"], "the first frame after the park must be an anchor frame"
    assert tuple(drawn[first]) == tuple(facts["line_entry"]), "K1gf: the first anchor frame is the entry exactly"
    _P, drawn_g, facts_g = _walk(st, "glide")
    d = float(np.hypot(*(np.asarray(drawn_g[first]) - np.asarray(facts_g["line_entry"]))))
    assert d > 0.0, "K1g starts at press + 2.0, so on this misaligned grid its first anchor frame is part-way along"
    assert GLIDE_ENTRY_M == 0.15                         # rule 2a's tolerance is not loosened


def test_glide_first_changes_only_the_anchor_span(st):
    P, a, fa = _walk(st, "glide_first")
    _P, b, fb = _walk(st, "glide")
    assert fa["t_dec0"] == fb["t_dec0"] and sorted(a) == sorted(b)
    for x in a:
        if x >= fa["t_dec0"] - 1e-9 or x < P + 2.0 - 1e-4:
            assert a[x] == b[x], f"frame {x} outside the anchor span differs"


def test_profiles():
    from pipeline.live import display as D
    from pipeline.live import final_model as FM
    pre = FM.DISPLAY_PROFILES["pre_clean"]
    assert pre == {"candidate": "K1g", "end_head": True, "sd_scale": None, "sett": {},
                   "gate_ref": "FC.relgateU+abstain+a2w0.25"}, "pre_clean must draw exactly as before"
    cfg = json.load(open(os.path.join(REPO, "runs", "a3_clean_2026-10-08", "A3_CLEAN_CONFIG_FULL.json"), encoding="utf-8"))
    v, c = cfg["variant"], FM.DISPLAY_PROFILES["clean"]
    assert v["end_head"] == "pooled" and c["end_head"] is False
    assert (c["sett"]["prior_f"], c["sett"]["head_offset_s"], c["sett"]["shift_w"], c["sd_scale"]) == \
        (v["prior_f"], v["head_offset"], v["shift_w"], v["sd"])
    assert (v["display_entry"], v["display_window"]) == ("soft", 1.0)        # the app's entry, unchanged
    assert v["switch"] == "A" and c["sett"]["switch"] == {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0,
                                                          "radius_m": 1.5}
    assert c["candidate"] == "K1gf" and D.DISPLAY_CANDIDATES["K1gf"] == {"path_lag_extra": 1, "anchor": "glide_first"}
    assert D.DISPLAY_CANDIDATES["K1g"] == {"path_lag_extra": 1, "anchor": "glide"}   # K1g untouched
    assert FM.DISPLAY_PROFILE == "clean_1s_r0" and FM.DISPLAY_CANDIDATE == "K1gf"       # Uzayr, 14 Oct (no radius)
    assert FM.end_head_for(None, 1.0, "final", "clean") is None
    one = FM.DISPLAY_PROFILES["clean_1s"]
    assert one["sett"]["head_offset_s"] == 1.0 and c["sett"]["head_offset_s"] == 0.75
    assert {k: v for k, v in one.items() if k not in ("sett", "source")} == {k: v for k, v in c.items() if k not in ("sett", "source")}
    assert {k: v for k, v in one["sett"].items() if k != "head_offset_s"} == {k: v for k, v in c["sett"].items() if k != "head_offset_s"}
    assert FM.end_head_for(None, 1.0, "final", "clean_1s") is None
    r0 = FM.DISPLAY_PROFILES["clean_1s_r0"]                                             # Uzayr, 14 Oct: no switch radius
    assert r0["sett"]["switch"] == {**one["sett"]["switch"], "radius_m": None} and one["sett"]["switch"]["radius_m"] == 1.5
    assert {k: v for k, v in r0["sett"].items() if k != "switch"} == {k: v for k, v in one["sett"].items() if k != "switch"}
    assert {k: v for k, v in r0.items() if k not in ("sett", "source")} == \
        {k: v for k, v in one.items() if k not in ("sett", "source")}
    assert FM.end_head_for(None, 1.0, "final", "clean_1s_r0") is None


def test_scorer_applies_the_glide_rule_to_glide_first():
    from pipeline.live.app_score import rule_checks
    rows = [{"kind": "press", "pid": 1, "t": 10.0},
            {"kind": "lock", "pid": 1, "line": "A_fwd", "line_entry": [0.0, 0.0], "t_dec0": 12.25, "park_until": 12.0},
            {"kind": "dot", "pid": 1, "x": 10.03, "xy": [2.5, 2.5], "computed_at": 10.1},
            {"kind": "dot", "pid": 1, "x": 12.03, "xy": [0.4, 0.0], "computed_at": 12.1}]
    from pipeline.live import app_score as S
    S._LINES["A_fwd"] = (np.array([0.0, 0.0]), np.array([5.0, 0.0]))
    assert rule_checks(rows, anchor="glide_first")["anchor_violations"] == [1]      # 0.4 m from the entry
    rows[-1]["xy"] = [0.0, 0.0]
    assert rule_checks(rows, anchor="glide_first")["anchor_violations"] == []


def test_replay_folders_never_overwrite_the_shipped_replays():
    from pipeline.live.app_replay import mode_dir_for
    assert mode_dir_for("start", None, "K1gf", "clean", False) == "semi_disp-K1gf"               # the adopted app
    assert mode_dir_for("start", None, "K1g", "pre_clean", True) == "semi_disp-K1g_prof-pre_clean"  # gate 3
    assert mode_dir_for("start", None, "K1g", "clean", False) == "semi_disp-K1g_prof-clean"      # K1g on clean settings
    assert mode_dir_for("start", None, "K1g", "pre_clean", False) == "semi_disp-K1g"             # as before 10 Oct
    assert mode_dir_for("none", 4, "K1gf", "clean", False) == "unconstrained_m4_disp-K1gf"
    assert mode_dir_for("start", None, "K1gf", "clean_1s", False) == "semi_disp-K1gf_prof-clean_1s"   # never the 0.75 s folders
    assert mode_dir_for("start", None, "K1gf", "clean_1s_r0", False) == "semi_disp-K1gf_prof-clean_1s_r0"


def test_the_start_detector_spread_is_pinned_under_both_profiles(monkeypatch):
    """The Mastermind's ruling (10 Oct): the unconstrained start detector decodes at 4.5 under "clean" and "pre_clean",
    whatever the display's spread. Each profile's display config is built as LiveDisplay and FinalTrackingSession
    build it; the detector's Space and transition matrix must both see 4.5."""
    import contextlib
    import dataclasses as dc

    from pipeline.constrained import decoder2
    from pipeline.constrained.decoder2 import Config
    from pipeline.live import display as D
    from pipeline.live import final_model as FM
    from pipeline.live import unconstrained as U
    seen = []
    monkeypatch.setattr(decoder2, "Space", lambda st, cfg: seen.append(("space", cfg.sd_scale)))
    monkeypatch.setattr(decoder2, "transition_matrix2", lambda st, cfg, tr=None: seen.append(("lT", cfg.sd_scale)))

    class Caps:
        def cap(self, _m):
            return contextlib.nullcontext()

    assert U.DETECTOR_SD_SCALE == 4.5
    disp = {}
    for name, prof in FM.DISPLAY_PROFILES.items():
        cfg = dc.replace(Config(), sd_scale=D.DISPLAY_SD_SCALE)                          # LiveDisplay.__init__
        if prof["sd_scale"] is not None:
            cfg = dc.replace(cfg, sd_scale=float(prof["sd_scale"]))                       # the profile
        disp[name] = cfg.sd_scale
        seen.clear()
        det = U.StartDetector(None, cfg, {}, None, Caps(), 4)
        assert det.sd_scale == 4.5 and seen == [("space", 4.5), ("lT", 4.5)], (name, seen)
    assert disp == {"pre_clean": 4.5, "clean": 3.0, "clean_1s": 3.0, "clean_1s_r0": 3.0}   # the display's spread does follow the profile


def test_acceptance_anchor_line_names_the_form():
    from pipeline.live.app_acceptance import _anchor_line
    g = {"from_entry_median": 0.0, "from_entry_max": 0.0, "off_line_max": 0.0}
    k1gf = _anchor_line({"render_rules": {"anchor_form": ["glide_first"], "per_recording": {"a": {"anchor_glide_m": g}}}})
    assert "drawn by K1gf" in k1gf and "within 0.15 m" in k1gf and "held form" not in k1gf
    k1g = _anchor_line({"render_rules": {"anchor_form": ["glide"], "per_recording": {"a": {"anchor_glide_m": g}}}})
    assert k1g.startswith("**The anchor column** is rule 2a's K1g form (the glide): on the green marker's first frame")
    held = _anchor_line({"render_rules": {"anchor_form": ["hold"], "per_recording": {}}})
    assert "held form" in held


def test_the_clean_model_set_drops_only_the_display_head(tmp_path, monkeypatch):
    from pipeline.live import final_model as FM
    from pipeline.live import model_sets as M
    monkeypatch.setattr(M, "OUT", str(tmp_path))
    got = {}
    for prof in ("pre_clean", "clean", "clean_1s", "clean_1s_r0"):
        monkeypatch.setattr(FM, "DISPLAY_PROFILE", prof)
        M.build("zeroshot")
        got[prof] = json.load(open(tmp_path / "zeroshot.json", encoding="utf-8"))
        os.remove(tmp_path / "zeroshot.json")
    assert got["clean_1s"]["files"] == got["clean"]["files"] and got["clean_1s"]["display_profile"] == "clean_1s"
    assert got["clean_1s_r0"]["files"] == got["clean"]["files"] and got["clean_1s_r0"]["display_profile"] == "clean_1s_r0"
    pre, clean = got["pre_clean"], got["clean"]
    head = {pre["display_head"], "runs/dc2_results/dispend_zeroshot/train.json"}
    assert head <= set(pre["files"]) and set(pre["files"]) - set(clean["files"]) == head
    assert set(clean["files"]) <= set(pre["files"]) and all(clean["files"][k] == pre["files"][k] for k in clean["files"])
    assert clean["display_head"] is None and clean["display_profile"] == "clean" and pre["display_profile"] == "pre_clean"


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
