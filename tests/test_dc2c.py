"""dc2c: the DC2 run one Room B session at a time (POST HOC TOOLING NOTE 2026-09-28)."""

import datetime
import json
import os

import numpy as np
import pytest

from pipeline.constrained import dc2b, dc2c


def _cfg(tmp_path):
    base = str(tmp_path / "base")
    return {"base": base, "room": "room_B", "stand_in": False, "train": ("01", "02", "03"),
            "b_sessions": {"B1": str(tmp_path / "B1"), "B2": str(tmp_path / "B2")},
            "heads_tag": "s010203_to_sB", "reader_tag": "s010203_to_sB", "model_src": {},
            "manifest": "m.json", "data_view": os.path.join(base, "data"),
            "win_view": os.path.join(base, "windows"), "tree": lambda h: os.path.join(base, f"art_{h}"),
            "shared": os.path.join(base, "art_shared")}


def test_per_session_cfg_keeps_one_session_and_moves_every_tree(tmp_path):
    c = _cfg(tmp_path)
    s = dc2c.per_session_cfg(c, "B2")
    where = os.path.join(c["base"], "by_session", "B2")
    assert s["b_sessions"] == {"B2": c["b_sessions"]["B2"]}
    assert s["base"] == where and s["tree"]("half") == os.path.join(where, "art_half")
    for k in ("data_view", "win_view", "shared"):
        assert s[k].startswith(where)
    assert s["train"] == c["train"] and s["heads_tag"] == c["heads_tag"] and s["manifest"] == c["manifest"]
    with pytest.raises(dc2b.Refused):
        dc2c.per_session_cfg(c, "B3")


def test_session_cfg_follows_the_environment(tmp_path, monkeypatch):
    c = _cfg(tmp_path)
    f = dc2c.session_cfg(lambda room, stand_in: c)
    monkeypatch.delenv(dc2c.SESSION_ENV, raising=False)
    assert f("room_B", False) is c
    monkeypatch.setenv(dc2c.SESSION_ENV, "B1")
    assert f("room_B", False)["b_sessions"] == {"B1": c["b_sessions"]["B1"]}


def _decode(b, tag="s010203_to_sB"):
    return {"heads_tag": tag, "train": ["01", "02", "03"], "fusion_per_arm": {"A": 0.0},
            "bound_roots": {"art": b}, "calibration": {"per_session": {b: {"x": 1}}, "room_A_reference": {"r": 1}},
            "constants": {b: {"theta": 0.3}}, "sessions": {b: {"rows": {"A": [{"k": b}]}}}}


def _write(base, b, d):
    p = os.path.join(base, "by_session", b)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "decode.json"), "w") as f:
        json.dump(d, f)


def test_merge_decodes_joins_the_sessions(tmp_path):
    base = str(tmp_path)
    for b in ("B1", "B2"):
        _write(base, b, _decode(b))
    out = dc2c.merge_decodes(base, ["B1", "B2"])
    assert sorted(out["sessions"]) == ["B1", "B2"]
    assert out["calibration"]["per_session"] == {"B1": {"x": 1}, "B2": {"x": 1}}
    assert out["calibration"]["room_A_reference"] == {"r": 1}
    assert sorted(out["constants"]) == ["B1", "B2"]
    assert json.load(open(os.path.join(base, "decode.json")))["sessions"]["B2"]["rows"]["A"] == [{"k": "B2"}]


def test_merge_decodes_refuses_mixed_runs(tmp_path):
    base = str(tmp_path)
    _write(base, "B1", _decode("B1"))
    _write(base, "B2", _decode("B2", tag="other"))
    with pytest.raises(dc2b.Refused):
        dc2c.merge_decodes(base, ["B1", "B2"])
    two = _decode("B1")
    two["sessions"]["B2"] = {}
    _write(base, "B1", two)
    with pytest.raises(dc2b.Refused):
        dc2c.merge_decodes(base, ["B1"])


def _session(tmp_path, b, day, stems):
    sdir = tmp_path / "data" / f"session_{b}"
    (sdir / f"{day}-101010").mkdir(parents=True)
    for s in stems:
        (sdir / f"{s}.gt.json").write_text("{}")
    return str(sdir)


def _post(base, b, h, stems, when):
    d = os.path.join(base, "by_session", b, f"art_{h}", "posteriors")
    os.makedirs(d, exist_ok=True)
    flat = {"__stems__": np.array(sorted(stems), dtype="U64")}
    t = when.timestamp()
    for s in stems:
        flat[f"{s}::t0_epoch"] = np.array([t, t + 300.0])
    np.savez_compressed(os.path.join(d, "s010203_to_sB_g25_e24_s0_full.npz"), **flat)


def test_posterior_guard_catches_the_other_days_radio(tmp_path):
    base = str(tmp_path / "base")
    stems = ["participant_PA5_walk", "participant_PA6_C_walk"]
    sd = {"B1": _session(tmp_path, "B1", "20260926", stems)}
    _post(base, "B1", "half", stems, datetime.datetime(2026, 9, 26, 12, 0))
    assert dc2c.posterior_guard(base, sd, ["half"]) == []
    _post(base, "B1", "half", stems, datetime.datetime(2026, 9, 27, 12, 0))       # day 2's radio
    assert any("windows dated ['20260927']" in b for b in dc2c.posterior_guard(base, sd, ["half"]))
    _post(base, "B1", "half", stems[:1], datetime.datetime(2026, 9, 26, 12, 0))   # a recording missing
    assert any("differ from" in b for b in dc2c.posterior_guard(base, sd, ["half"]))


def test_the_frozen_infer_names_its_output_without_the_session():
    """The fault itself, read from the pinned source: the posterior file name carries the head tag
    and never the session, which is why two sessions collide."""
    import inspect
    from pipeline.constrained import dc2_run
    src = inspect.getsource(dc2_run.do_infer)
    line = [x for x in src.splitlines() if 'out = os.path.join(tree, "posteriors"' in x]
    assert len(line) == 1 and "{b}" not in line[0] and "{tag}" in line[0]
