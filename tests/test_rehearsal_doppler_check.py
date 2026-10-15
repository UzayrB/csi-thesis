"""The rehearsal Doppler diagnostic on SYNTHETIC rehearsal recordings (real CSIBIN01 format).

Planted: during each pass, TX-RX2 carries three Doppler tones (15, 22 and 31 Hz) with independent
per-subcarrier weights, so they survive dropping PC1. The empty room and the other links are noise.
"""

import json
import os

import numpy as np
import pytest

from pipeline.identify import rehearsal_doppler_check as R
from pipeline.identify.common import SIX
from tests import test_id29_dc2_score as T

FS = 150.0
CODE = SIX[0]


def _times(rng, t0, t1):
    """Irregular packet times at about 143 Hz, as the receivers deliver them (a regular 150 Hz grid
    would make the resampling phase differ between the walk and the empty room)."""
    n = int((t1 - t0) * 143.1 * 1.05)
    t = t0 + np.cumsum(rng.uniform(0.5, 1.5, n) / 143.1)
    return t[t < t1]


def _stem(d, what):
    return os.path.join(d, f"participant_{CODE}_idpath_d1_{what}_REHEARSAL")


def make(d, planted: bool, seed=0):
    rng = np.random.default_rng(seed)
    os.makedirs(d, exist_ok=True)
    st = _stem(d, "empty_idspot")
    tt = _times(rng, 5000.0, 5030.0)
    for L in R.LINKS:
        T.write_bin(f"{st}_{L}.bin", tt, T._base(len(tt), 1.0) + rng.normal(0, 0.4, (len(tt), 128)), rng)
    st = _stem(d, "natural")
    spans, t = [], 1002.0
    for _ in range(4):
        spans.append((t, t + 4.0))
        t += 7.0
    tt = _times(rng, 1000.0, t + 1.0)
    W = rng.normal(0, 1, (3, 128))
    for L in R.LINKS:
        a = T._base(len(tt), 1.0) + rng.normal(0, 0.4, (len(tt), 128))
        if planted and L == "RX2":
            for a0, a1 in spans:
                k = (tt >= a0) & (tt <= a1)
                for j, f in enumerate((15.0, 22.0, 31.0)):
                    a[k] += 2.0 * np.sin(2 * np.pi * f * tt[k] + rng.uniform(0, 6.28))[:, None] * W[j][None, :]
        T.write_bin(f"{st}_{L}.bin", tt, np.clip(a, 0, 127), rng)
    json.dump({"passes": [{"pass_id": i + 1, "t_start": a0, "t_end": a1, "path_name": "A_fwd"}
                          for i, (a0, a1) in enumerate(spans)]}, open(st + ".gt.json", "w"))
    return d


def test_a_planted_doppler_tone_is_detected(tmp_path, capsys):
    d = make(str(tmp_path / "rehearsal_idpath"), planted=True)
    rep = R.run(d, str(tmp_path / "fig"))
    (r,) = rep["recordings"].values()
    assert r["links"]["RX2"]["EXCEEDS_FLOOR"], r["links"]["RX2"]
    assert not r["links"]["RX1"]["EXCEEDS_FLOOR"], r["links"]["RX1"]
    assert rep["RX2_EXCEEDS_FLOOR_IN_EVERY_WALK"]
    assert os.path.exists(r["figure"])
    assert R.main(["--dir", d, "--figures", str(tmp_path / "fig")]) == 0
    out = capsys.readouterr().out
    assert "REHEARSAL DIAGNOSTIC" in out and CODE not in out


def test_pure_noise_is_not_detected(tmp_path):
    d = make(str(tmp_path / "rehearsal_idpath"), planted=False, seed=1)
    rep = R.run(d)
    (r,) = rep["recordings"].values()
    for L in R.LINKS:
        assert not r["links"][L]["EXCEEDS_FLOOR"], (L, r["links"][L])
    assert R.main(["--dir", d, "--figures", str(tmp_path / "fig")]) == 1


def test_refuses_the_scored_rooms(tmp_path):
    for room in ("room_A", "room_B"):
        d = make(str(tmp_path / "data" / room), planted=True)
        with pytest.raises(R.Refused):
            R.run(d)
        assert R.main(["--dir", d]) == 2
    with pytest.raises(R.Refused):
        R.refuse_scored_data(os.path.join(R.REPO, "data", "room_A", "session_01"))


def test_refuses_a_folder_holding_non_rehearsal_recordings(tmp_path):
    d = make(str(tmp_path / "rehearsal_idpath"), planted=True)
    open(os.path.join(d, f"participant_{CODE}_idpath_d1_natural.gt.json"), "w").write("{}")
    with pytest.raises(R.Refused):
        R.run(d)
