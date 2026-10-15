"""The one-press identification engine (`runs/identify/engine/PLAN.md`; `pipeline/identify/engine.py`) and its
live mode (`pipeline/live/identify_engine.py`).

- the causal clock tells a wrap from a reboot and restarts on a reboot;
- one press gives exactly one decision;
- how frames are batched when pushed never changes a decision (so the rig, the app replay and the harness
  agree by construction);
- the app's replay equals the evaluation harness's decisions pass for pass (once the fold model and the
  harness replay exist);
- the deployment model loads from its manifest (once trained);
- the legacy random-forest mode still gives its old decisions (gate 5), with IDE_SLOW=1.

    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pytest -q tests/test_ide_engine.py
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _at_repo(monkeypatch):
    monkeypatch.chdir(REPO)


def _recording():
    from pipeline.identify import engine as EN
    from pipeline.identify import idx_bank as B
    from pipeline.io.capture_logger import read_capture_file
    rec = [r for r in B.recordings() if r["kind"] == "idcap" and r["session"] == "B2" and r["block"] == "natural"][0]
    fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
    gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
    return fr, sorted(float(q["t_start"]) for q in gt["passes"])


def _frames(local_us, t_mono):
    from pipeline.io.capture_logger import FRAME_DTYPE
    fr = np.zeros(len(local_us), FRAME_DTYPE)
    fr["local_timestamp"] = local_us
    fr["t_mono"] = t_mono
    fr["data"] = 10
    return fr


def test_clock_wrap_and_reboot():
    from pipeline.identify import engine as EN
    top = 2 ** 32
    n = 300
    tm = 100.0 + np.arange(3 * n) / 150.0
    lu = np.concatenate([top - (n - np.arange(n)) * 6667,        # ends 6.7 ms below the top of the clock
                         100 + np.arange(n) * 6667,               # a wrap: continues from 0 (up to about 2 s)
                         200_000 + np.arange(n) * 6667])          # a reboot: back from about 2 s to 0.2 s
    r = EN.Receiver()
    r.push(_frames(lu[:n + 10], tm[:n + 10]))
    r.push(_frames(lu[n + 10:], tm[n + 10:]))
    r.consolidate()
    assert r.n_wraps == 1 and r.n_reboots == 1
    assert np.all(np.diff(r.lt[:2 * n]) > 0)                     # unwrapped across the wrap
    assert set(r.ep[:2 * n]) == {0} and set(r.ep[2 * n:]) == {1}
    idx = r.arrived(tm[-1])
    assert idx[0] == 2 * n                                       # after a reboot only the new epoch is read


def test_one_press_one_decision():
    from pipeline.identify import engine as EN
    fr, presses = _recording()
    ex = EN.Extractor()
    t0 = presses[0]
    cap = t0 + EN.T_S + EN.CAP_S
    for L in EN.LINKS:
        ex.push(L, fr[L][: int(np.searchsorted(fr[L]["t_mono"], cap, side="right"))])
    assert ex.poll(cap) == []                                    # no press, no decision
    ex.press(t0)
    got = ex.poll(cap)
    assert len(got) == 1 and ex.poll(cap + 5) == []


def test_batching_does_not_change_decisions():
    from pipeline.identify import engine as EN
    fr, presses = _recording()
    t0 = presses[1]
    cap = t0 + EN.T_S + EN.CAP_S
    big = EN.Extractor()
    for L in EN.LINKS:
        big.push(L, fr[L][: int(np.searchsorted(fr[L]["t_mono"], cap + 2.0, side="right"))])
    big.press(t0)
    (_w, td_big, x_big), = big.poll(cap + 2.0)
    small = EN.Extractor()
    small.press(t0)
    pos = {L: 0 for L in EN.LINKS}
    got = []
    for now in np.arange(t0 - 30.0, cap + 0.2, 0.1):
        for L in EN.LINKS:
            n = int(np.searchsorted(fr[L]["t_mono"], now, side="right"))
            small.push(L, fr[L][pos[L]:n])
            pos[L] = n
        got += small.poll(now)
    assert len(got) == 1
    _w, td_small, x_small = got[0]
    assert td_small == td_big
    assert np.array_equal(x_small["features"], x_big["features"], equal_nan=True)
    assert np.array_equal(x_small["maps"], x_big["maps"])
    assert x_small["dir_detected"] == x_big["dir_detected"] and x_small["wifi_speed"] == x_big["wifi_speed"]


def test_app_replay_equals_harness():
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.live.identify_engine import final_model, replay_session
    m = final_model("B2")                                  # engine v2's fold model (the cadence bug fix) once built
    p = os.path.join(RP.OUT, f"{m}_B2_T{EN.T_S:.1f}.npz")
    if not os.path.exists(p):
        pytest.skip("the harness replay of B2 does not exist yet")
    dev = json.load(open(p.replace(".npz", ".json")))["device"]
    h = np.load(p)
    app = replay_session("B2", model=m, device=dev, recordings=2)
    n = len(app.decisions)
    assert n > 0
    ens = np.array([d["ensemble"] for d in app.decisions])
    assert np.array_equal(np.array([d["t0"] for d in app.decisions]), h["t0"][:n])
    assert np.array_equal(ens.argmax(1), h["ensemble"][:n].argmax(1))
    assert np.allclose(ens, h["ensemble"][:n], atol=1e-6, rtol=0)


def test_deployment_model_loads_from_manifest():
    from pipeline.live import identify_engine as IE
    if not os.path.exists(os.path.join(IE.model_dir(IE.deployment_model()), "manifest.json")):
        pytest.skip("the deployment model is not trained yet")
    from pipeline.identify import engine as EN
    md, man = IE.load_deployment()
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"])
    assert eng.model is not None and man["model"] == IE.deployment_model() and man["n_train"] == 1019
    assert man["model"] == EN.model_name("deploy_all5") and man["engine_version"] == EN.ENGINE_VERSION


@pytest.mark.skipif(os.environ.get("IDE_SLOW") != "1", reason="slow: set IDE_SLOW=1")
def test_legacy_random_forest_mode_unchanged():
    from pipeline.live.gates import gate5
    assert gate5()["PASSED"]
