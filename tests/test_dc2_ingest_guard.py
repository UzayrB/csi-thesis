"""THE DC2 INGEST GUARD, enforced. REWRITTEN 2026-09-23d with its premise corrected.

Until 2026-09-23d this file enforced "cut Room B at BOTH 1.0 s and 0.5 s or refuse", on the belief
that three of the five pool heads need a 1 s window tree. They do not: the shipped pool infers
every head over the 0.5 s windows (`g2_multihead.ONE_S_TREES`, "posteriors over the 0.5 s windows";
batch 23c item 5 reproduced them over `windows_half` to 3e-8). `reports/PREREG_DC2_crossroom_
2026-09-22.md` section 10.2 records the correction.

WHAT STILL HOLDS, and is what these tests protect: a missing input STOPS the run rather than
printing a warning that scrolls past at 2 a.m. The input that matters is now the RAW capture, which
the pipeline cuts on the ONE lattice itself. The 1.0 s cut is needed only to train 1 s heads on DC2
data; its absence is stamped, not a refusal, and the primary comparison runs without it.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from pipeline.constrained.dc2_pipeline import POOL_HEADS, ingest_check, main

REPO = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_env_leak():
    """main() may touch os.environ; snapshot and restore so no other module's guard is affected.

    The first version of this file broke pipeline/identify/id11_audit.py, a module it has nothing to
    do with, through a process-wide TDR_ART_DIR.
    """
    before = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(before)


def _raw(tmp_path, *, with_raw: bool, with_one: bool, room: str = "room_B"):
    data = tmp_path / "data" / room
    data.mkdir(parents=True)
    if with_raw:
        s = data / "session_B1"
        s.mkdir()
        (s / "participant_Test_walk.gt.json").write_text("{}", encoding="utf-8")
        for n in ("RX1", "RX2", "RX3"):
            (s / f"participant_Test_walk_{n}.bin").write_bytes(b"")
    one = tmp_path / "windows_w1"
    if with_one:
        d = one / room / "session_B1"
        d.mkdir(parents=True)
        (d / "participant_Test_walk.meta.json").write_text("{}", encoding="utf-8")
    else:
        one.mkdir()
    return str(data), str(one)


def test_raw_present_is_reproducible_without_any_1s_cut(tmp_path):
    raw, one = _raw(tmp_path, with_raw=True, with_one=False)
    out = ingest_check(raw, one, "room_B")
    assert out["pool_reproducible"] is True and out["WARNING"] is None
    assert out["within_dc2_training_possible"] is False
    assert "--stride 1.0" in out["within_dc2_note"], "the missing 1.0 s cut must be named, with its command"


def test_the_1s_cut_only_unlocks_within_dc2_training(tmp_path):
    raw, one = _raw(tmp_path, with_raw=True, with_one=True)
    out = ingest_check(raw, one, "room_B")
    assert out["within_dc2_training_possible"] is True and out["within_dc2_note"] is None


def test_no_raw_capture_REFUSES_TO_RUN(tmp_path):
    """The behaviour that matters: the run stops, it does not print and carry on."""
    raw, one = _raw(tmp_path, with_raw=False, with_one=True)
    with pytest.raises(SystemExit) as e:
        main(["--room", "room_B", "--data", str(tmp_path / "data"), "--windows-1s", one,
              "--out", str(tmp_path / "out")])
    msg = str(e.value)
    assert "REFUSING TO RUN" in msg and "NO RAW RECORDINGS" in msg
    assert "calibration.json" in msg, "a refusal must say how to fix it"


def test_every_pool_head_is_inferred_over_the_half_stride_windows():
    assert {v["inferred_over"] for v in POOL_HEADS.values()} == {"0.5 s"}


def test_the_1s_heads_posteriors_are_indexed_on_the_half_stride_windows():
    """THE CORRECTION, measured: a 1 s head's posterior file lives on the 0.5 s window lattice."""
    import numpy as np
    from pipeline.constrained import lattice
    p = REPO / lattice.one_s_trees()[0] / "posteriors" / "s0102_to_s03_g25_e24_s0_full.npz"
    meta = REPO / lattice.windows_root() / "room_A" / "session_03" / "participant_PA5_TEST_walk.meta.json"
    if not p.exists() or not meta.exists():
        pytest.skip("shipped trees absent")
    import json
    t_meta = np.array([w["t_start_abs"] for w in json.loads(meta.read_text())["windows"]])
    d = np.load(p, allow_pickle=False)
    t_post = d["participant_PA5_TEST_walk::t0"]
    assert len(t_post) == len(t_meta) and np.allclose(t_post, t_meta)
    assert abs(float(np.median(np.diff(t_post))) - 0.5) < 1e-6


def test_the_field_checklist_names_the_one_cut_and_keeps_the_training_cut():
    sheet = (REPO / "reports" / "project" / "dc2-capture" / "field-checklist.md").read_text(encoding="utf-8")
    assert "dc2_pipeline" in sheet, "the sheet must send the operator to the one command"
    assert "--stride 1.0" in sheet, "the 1.0 s cut stays on the sheet, for within-DC2 training"
