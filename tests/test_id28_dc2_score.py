"""The DC2 identification scorer, tested on SYNTHETIC recordings only. Never on Room A or DC2 data.

Synthetic captures are written in the real CSIBIN01 format (magic, JSON header with the frame
dtype, FRAME_DTYPE records) with the exact `idpath` naming scheme, and each person carries a
planted per-person gait rate and walking speed. Room A is replaced by a synthetic loader.
"""

import json
import os
import shutil

import numpy as np
import pytest

from pipeline.identify import id28_dc2_score as D
from pipeline.identify.common import SIX

RATES = dict(zip(SIX, np.linspace(1.5, 2.5, 6)))          # planted per-person gait rate, Hz
SPEED = dict(zip(SIX, np.linspace(1.0, 1.6, 6)))          # planted per-person natural speed, m/s
PACE = {"": 1.0, "slow": 0.7, "fast": 1.35}
FS = 150.0


def _amp128(n, rng, gain):
    base = 20.0 + 8.0 * np.sin(np.arange(128) * 0.21)
    a = np.tile(base * gain, (n, 1))
    for i in sorted({0, 1, 64} | set(range(27, 38)) | set(range(93, 104))):
        a[:, i] = 0.0
    return a


def _modulate(a, t, spans, rate, rng):
    m = np.ones(len(t))
    for t0, t1 in spans:
        k = (t >= t0) & (t <= t1)
        m[k] = 1.0 + 0.35 * np.sin(2 * np.pi * rate * t[k] + rng.uniform(0, 6.28))
    return a * m[:, None] + rng.normal(0, 0.4, a.shape)


def write_bin(path, t_true, amp, rng):
    from pipeline.io.capture_logger import FILE_MAGIC, FRAME_DTYPE
    n = len(t_true)
    fr = np.zeros(n, FRAME_DTYPE)
    fr["t_mono"] = t_true + rng.uniform(0, 0.045, n)          # host drains in batches, always late
    fr["t_host"] = fr["t_mono"] + 1.79e9
    fr["local_timestamp"] = np.round((t_true - t_true[0] + 3.0) * 1e6).astype(np.uint64)
    fr["pkt_id"] = np.arange(n)
    fr["rssi"] = -60
    fr["gain"] = 1.0
    data = np.zeros((n, 256), np.int8)
    data[:, 1::2] = np.clip(np.round(amp), 0, 127).astype(np.int8)     # (imag, real), imag = 0
    fr["data"] = data
    hdr = json.dumps({"node_id": os.path.basename(path)[-7:-4], "dtype": [list(d) for d in FRAME_DTYPE.descr],
                      "csi_len": 256}).encode()
    with open(path, "wb") as f:
        f.write(FILE_MAGIC)
        f.write(np.uint32(len(hdr)).tobytes())
        f.write(hdr)
        f.write(fr.tobytes())


def write_recording(d, name, day, rnd, pace, rng, n_pass=3):
    stem = f"participant_{name}_idpath_d{day}_r{rnd}{'_' + pace if pace else ''}"
    t0 = 1000.0 + 500 * day + 100 * rnd
    spans, t = [], t0 + 2.0
    for _ in range(n_pass):
        # per-pass jitter: with none, within-person speed variance is zero and shrinkage LDA on one
        # feature degenerates to a single class, which real walking never produces
        dur = 5.0 / (SPEED[name] * PACE[pace]) * (1.0 + rng.normal(0, 0.05))
        spans.append((t, t + dur))
        t += dur + 3.0
    t_true = np.arange(t0, t + 1.0, 1.0 / FS)
    for L in ("RX1", "RX2", "RX3"):
        a = _modulate(_amp128(len(t_true), rng, rng.uniform(0.9, 1.1)), t_true, spans, RATES[name], rng)
        write_bin(os.path.join(d, f"{stem}_{L}.bin"), t_true, a, rng)
    gt = {"passes": [{"pass_id": i + 1, "t_start": s, "t_end": e, "path_name": "E_row1", "direction": "E"}
                     for i, (s, e) in enumerate(spans)]}
    json.dump(gt, open(os.path.join(d, f"{stem}.gt.json"), "w"))


def make_dc2(root, seed=0):
    rng = np.random.default_rng(seed)
    for day in (1, 2):
        d = os.path.join(root, f"session_0{day}")
        os.makedirs(d, exist_ok=True)
        for name in SIX:
            for (dd, rnd, pace) in D.EXPECTED:
                if dd == day:
                    write_recording(d, name, day, rnd, pace, rng)


def synthetic_room_a(seed=1):
    """A small synthetic Room A in the loader's format: 6 people x 3 sessions x 4 passes, two lines."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.common import anon
    rng = np.random.default_rng(seed)
    rows, feats, specs = [], [], []
    for s in ("01", "02", "03"):
        for name in SIX:
            for k, line in enumerate(("E_row1", "E_row1", "A_fwd", "A_fwd")):
                dur = 5.0 / SPEED[name] * (1.0 + rng.normal(0, 0.05))
                t = np.arange(0, dur, 1 / FS)
                a = _modulate(_amp128(len(t), rng, 1.0), t, [(0, dur)], RATES[name], rng)
                a3 = np.stack([a[:, D_keep()][:, FB.SC] for _ in range(3)])
                feats.append(FB.pass_features(a3, np.full((3, len(t)), -60.0)))
                specs.append(D.spec_from_segment(a3))
                rows.append({"anon": anon(name), "day": 0, "round": 0, "pace": "roomA",
                             "session": f"A{s}", "rec": f"A{s}|{anon(name)}", "line": line, "t": float(k),
                             "pass_id": k + 1, "speed_m_s": 5.0 / dur})
    names = sorted(set().union(*[f.keys() for f in feats]))
    X = np.array([[f.get(n, np.nan) if f.get(n) is not None else np.nan for n in names] for f in feats], float)
    return {"rows": rows, "X": X, "names": names, "specs": np.asarray(specs, np.float32)}


def D_keep():
    from pipeline.identify.id19_bank import KEEP
    return KEEP


def make_cfg(tmp, prereg_text="synthetic pre-registration\n"):
    pre = os.path.join(tmp, "PREREG.md")
    open(pre, "w").write(prereg_text)
    fz = os.path.join(tmp, "FREEZE.json")
    json.dump({"prereg_sha256": D.sha256(pre)}, open(fz, "w"))
    return D.Config(prereg=pre, freeze=fz, data_root=os.path.join(tmp, "room_B"),
                    out=os.path.join(tmp, "out"), report=os.path.join(tmp, "REPORT.md"),
                    findings=os.path.join(tmp, "FINDINGS.txt"), cnn_seeds=(0,), cnn_epochs=2,
                    n_boot=200, n_perm=200, room_a_loader=synthetic_room_a)


# ------------------------------------------------------------------ the end-to-end synthetic run

@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("dc2"))
    cfg = make_cfg(tmp)
    open(cfg.report, "w").write("# report\n")
    make_dc2(cfg.data_root)
    res = D.run(cfg)
    return cfg, res


def test_planted_signal_is_recovered(scored):
    _cfg, res = scored
    a = res["analyses"]["a"]["PRIMARY"]
    assert a["acc_pct"] >= 60.0, a
    assert a["perm_p"] <= 0.05 and a["ci95_pct"][0] > a["chance_pct"]
    assert res["analyses"]["b"]["PRIMARY"]["acc_pct"] >= 50.0


def test_planted_speed_moves_s0_on_the_pace_round(scored):
    _cfg, res = scored
    assert res["analyses"]["a"]["S0"]["acc_pct"] >= 60.0          # speed is planted per person
    assert res["pace_test"]["drops"]["S0"]["drop_pts"] > 30.0     # and the pace round breaks it
    assert res["pace_test"]["S0_manipulation_check"] is True


def test_every_analysis_ran_and_outputs_were_written(scored):
    cfg, res = scored
    assert set(res["analyses"]) == {"a", "b", "c1", "c2", "d"}
    assert set(res["analyses"]["a"]) == {"PRIMARY", "SECONDARY", "S0", "RECSIG"}
    assert "session_id_control" in res and res["icc"].get("icc") is not None
    assert open(cfg.findings).read().split()[0] == "PASSED"
    rep = open(cfg.report).read()
    assert "DC2 identification, confirmatory" in rep and rep.startswith("# report")
    for n in SIX:
        assert n not in rep and n not in open(os.path.join(cfg.out, "results.json")).read()


def test_label_shuffle_falls_to_chance(scored):
    cfg, _res = scored
    found = D.discover(cfg.data_root)
    dc2 = D.extract(cfg, found)
    M, S = D.build(dc2, synthetic_room_a())
    y = M["y"].copy()
    y = y[np.random.default_rng(3).permutation(len(y))]
    res = D.score_all(cfg, M, S, y)
    a = res["analyses"]["a"]["PRIMARY"]
    assert a["acc_pct"] < 40.0, a                                  # planted run gives >= 60


# ------------------------------------------------------------------ guards

def test_hash_gate_blocks_a_modified_preregistration(tmp_path):
    cfg = make_cfg(str(tmp_path))
    assert D.check_prereg(cfg) == D.sha256(cfg.prereg)
    with open(cfg.prereg, "a") as f:
        f.write("one changed line\n")
    with pytest.raises(D.Refused) as e:
        D.run(cfg)
    assert e.value.kind == "hash"
    assert not os.path.exists(os.path.join(cfg.out, "results.json"))


def test_rerun_is_refused_without_a_reason_and_logged_with_one(tmp_path):
    cfg = make_cfg(str(tmp_path))
    os.makedirs(cfg.out)
    json.dump({"prior": True}, open(os.path.join(cfg.out, "results.json"), "w"))
    with pytest.raises(D.Refused) as e:
        D.run(cfg)
    assert e.value.kind == "rerun"
    os.makedirs(cfg.data_root)
    with pytest.raises(D.Refused) as e:                            # proceeds, then stops at discovery
        D.run(cfg, rerun_reason="synthetic test of the guard")
    assert e.value.kind == "discovery"
    assert "synthetic test of the guard" in open(os.path.join(cfg.out, "RERUNS.log")).read()
    assert any(f.startswith("results_superseded_") for f in os.listdir(cfg.out))
    assert not os.path.exists(os.path.join(cfg.out, "results.json"))


def _touch_set(root):
    d = os.path.join(root, "session_01")
    os.makedirs(d, exist_ok=True)
    for name in SIX:
        for day, rnd, pace in D.EXPECTED:
            stem = f"participant_{name}_idpath_d{day}_r{rnd}{'_' + pace if pace else ''}"
            for s in D.SUFFIXES:
                open(os.path.join(d, stem + s), "w").close()
    return d


def test_discovery_accepts_the_complete_set(tmp_path):
    _touch_set(str(tmp_path))
    assert len(D.discover(str(tmp_path))) == 48


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: os.remove(os.path.join(d, f"participant_{SIX[2]}_idpath_d2_r4_fast_RX2.bin")), "missing file"),
    (lambda d: open(os.path.join(d, "participant_Azrah_idpath_d1_r1_RX1.bin"), "w").close(), "retired"),
    (lambda d: open(os.path.join(d, f"participant_{SIX[0]}_idpath_d1_r5_RX1.bin"), "w").close(), "unexpected round"),
    (lambda d: open(os.path.join(d, f"participant_{SIX[0]}_idpath_d1_r4_fast_RX1.bin"), "w").close(), "unexpected round"),
    (lambda d: open(os.path.join(d, f"participant_{SIX[0]}_idpath_d1_r1.csv"), "w").close(), "unexpected file"),
    (lambda d: open(os.path.join(d, "participant_Stranger_idpath_d1_r1_RX1.bin"), "w").close(), "not one of the six"),
])
def test_discovery_fails_loudly(tmp_path, mutate, expect):
    d = _touch_set(str(tmp_path))
    mutate(d)
    with pytest.raises(D.Refused) as e:
        D.discover(str(tmp_path))
    assert e.value.kind == "discovery" and expect in str(e.value)


# ------------------------------------------------------------------ the pace-test arithmetic

def test_pace_drop_arithmetic_and_verdicts():
    # two days x two people; analysis a correct 3/4 for every unit; pace round correct 1/4
    M = {"day": np.array([1] * 8 + [2] * 8), "anon": np.array((["P1"] * 4 + ["P2"] * 4) * 2)}
    idx = np.arange(16)
    res_a = [{"te": idx.tolist(), "pred": ["x"] * 16, "truth": (["x", "x", "x", "y"] * 4)}]
    res_d = [{"te": idx.tolist(), "pred": ["x"] * 16, "truth": (["x", "y", "y", "y"] * 4)}]
    d = D.pace_drop(res_a, res_d, M, n_boot=100)
    assert d["n_units"] == 4 and abs(d["drop_pts"] - 50.0) < 1e-9
    assert d["ci95_pts"] == [50.0, 50.0]
    s0 = {"drop_pts": 50.0, "ci95_pts": [40.0, 60.0]}
    good_a = {"ci95_pct": [40.0, 70.0], "chance_pct": 16.67}
    assert D.pace_verdict({"drop_pts": 55.0, "ci95_pts": [45, 65]}, s0, good_a).startswith("ENCODES PACE")
    assert D.pace_verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]}, s0, good_a).startswith("GAIT-CONSISTENT")
    assert D.pace_verdict({"drop_pts": 20.0, "ci95_pts": [5, 35]}, s0, good_a) == "INCONCLUSIVE"
    assert D.pace_verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]}, s0,
                          {"ci95_pct": [10.0, 30.0], "chance_pct": 16.67}).startswith("NOT INFORMATIVE")
    assert D.pace_verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]},
                          {"drop_pts": 3.0, "ci95_pts": [-2, 8]}, good_a).startswith("NOT DECIDABLE")


def test_path_constants_match_the_grid_definition():
    from pipeline.constrained import paths as P
    v = np.asarray(P.load_paths()[D.PATH_LINE], float)
    assert np.allclose(v[0], [0.0, 0.5]) and np.allclose(v[-1], [5.0, 0.5])
    assert abs(np.linalg.norm(v[-1] - v[0]) - D.PATH_LEN_M) < 1e-9
