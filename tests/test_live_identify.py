"""Identification, live: `id29_dc2_score`'s features from packets and presses, and one pass predicted on its
own exactly as inside id29's batch. SYNTHETIC recordings only, written under pytest's tmp_path (the same
real-format captures `tests/test_id29_dc2_score.py` writes). The full run is `--gate 5`.
"""

import importlib.util
import json
import os

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _T():
    spec = importlib.util.spec_from_file_location("t_id29_live", os.path.join(REPO, "tests", "test_id29_dc2_score.py"))
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    return T


def _replay(rec_dir, stem, name, day, block, until=None):
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live.identify import LINKS, LiveIdRecording
    lr = LiveIdRecording(name, day, block)
    frs = {L: read_capture_file(os.path.join(rec_dir, f"{stem}_{L}.bin"))[1] for L in LINKS}
    gt = json.load(open(os.path.join(rec_dir, stem + ".gt.json"), encoding="utf-8"))
    ev = [(float(frs[L]["t_mono"][min(a + 14, len(frs[L]) - 1)]), 1, L, a) for L in LINKS for a in range(0, len(frs[L]), 15)]
    ev += [(float(q["t_start"]), 0, "press", q["t_start"]) for q in gt["passes"]]
    ev += [(float(q["t_end"]), 0, "end", q["t_end"]) for q in gt["passes"]]
    for e in sorted(ev, key=lambda x: (x[0], x[1])):
        if until is not None and e[0] > until:
            break
        if e[2] == "press":
            lr.press(e[3])
        elif e[2] == "end":
            lr.end_press(e[3])
        else:
            lr.push(e[2], frs[e[2]][e[3]:e[3] + 15])
    return lr, gt


@pytest.fixture(scope="module")
def one(tmp_path_factory):
    from pipeline.identify import id29_dc2_score as D
    T = _T()
    root = str(tmp_path_factory.mktemp("idlive"))
    cfg = T.make_cfg(root)
    d = os.path.join(cfg.data_root, "session_01")
    os.makedirs(d)
    T.write_walk(d, "PA5", 1, "natural", 4, np.random.default_rng(5))
    stem = __import__("pipeline.identify.capture_idpath", fromlist=["stem"]).stem("PA5", 1, "natural")
    found = {("PA5", 1, "natural"): {"dir": d, "stem": stem}}
    return cfg, d, stem, D.extract(cfg, found)


def test_every_pass_equals_id29_extract(one):
    from pipeline.live.identify import nan_equal as _nan_equal
    cfg, d, stem, off = one
    lr, _gt = _replay(d, stem, "PA5", 1, "natural")
    lr.close()
    assert len(lr.done) == len(off["rows"]) == 4
    for i, r in enumerate(lr.done):
        assert _nan_equal(r["feats"], off["feats"][i])
        assert all(_nan_equal(r["single"][k], off["single"][k][i]) for k in off["single"])
        assert np.array_equal(r["spec"], off["specs"][i], equal_nan=True)
        assert _nan_equal(r["row"], off["rows"][i])


def test_a_pass_waits_until_its_clock_map_is_final(one):
    """The clock map's bin after the pass must be complete: nothing is extracted WAIT_S before that."""
    from pipeline.live.identify import WAIT_S
    _cfg, d, stem, _off = one
    gt = json.load(open(os.path.join(d, stem + ".gt.json"), encoding="utf-8"))
    t_end = float(gt["passes"][0]["t_end"])
    early, _ = _replay(d, stem, "PA5", 1, "natural", until=t_end + WAIT_S - 2.0)
    assert not early.done and early.pending


def test_one_pass_on_its_own_equals_its_prediction_inside_the_batch():
    """PRIMARY and S0, with probabilities: a day-2 pass predicted alone from the enrolled day-1 passes
    equals the same pass predicted in one batch with the others."""
    from pipeline.identify import idmax_eval as E
    from pipeline.identify.common import SIX
    from pipeline.identify.id29_dc2_score import build
    from pipeline.live.identify import LiveIdentifier, pass_record
    T = _T()
    rng = np.random.default_rng(1)
    ra = T.synthetic_room_a()

    def rec(name, day, n):
        dur = 5.0 / T.SPEED[name] * (1.0 + rng.normal(0, 0.05))
        t = np.arange(0, dur, 1 / 150.0)
        links = []
        for L in ("RX1", "RX2", "RX3"):
            m = 1.0 + T.DEPTH[L] * np.sin(2 * np.pi * T.RATES[name] * t + rng.uniform(0, 6))
            a = (T._base(len(t), 1.0) * m[:, None] + rng.normal(0, 0.4, (len(t), 128)))
            from pipeline.identify.id19_bank import KEEP
            links.append((t + 100.0 * n, a[:, KEEP].astype(np.float32), np.full(len(t), -60.0, np.float32), 6))
        return pass_record(links, 100.0 * n, 100.0 * n + dur - 0.01, name, day, "natural")

    enrolled = [rec(nm, 1, 10 * i + j) for i, nm in enumerate(SIX) for j in range(4)]
    tests = [rec(nm, 2, 100 + i) for i, nm in enumerate(SIX)]
    ident = LiveIdentifier(enrolled, ra)
    alone = ident.predict(tests)
    M = build(ident._dc2(enrolled + tests), ra)
    n_ra = len(ra["rows"])
    tr = np.arange(n_ra, n_ra + len(enrolled))
    te = np.arange(n_ra + len(enrolled), n_ra + len(enrolled) + len(tests))
    fc = E.FConf("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")
    pred, P, cl = E.fit_predict(fc, "rf", tr, te, M["y"][tr], M, proba=True)
    sp, sP, scl = E.fit_predict(E.FConf("dc2e_S0", "S0", "-"), "lda", tr, te, M["y"][tr], M, proba=True)
    for j, g in enumerate(alone):
        assert g["pred"] == str(pred[j]) and g["s0_pred"] == str(sp[j])
        assert all(g["proba"][str(c)] == float(P[j][i]) for i, c in enumerate(cl))
        assert all(g["s0_proba"][str(c)] == float(sP[j][i]) for i, c in enumerate(scl))
        assert g["chance"] == 1.0 / len(cl)


def test_combining_passes_multiplies_their_probabilities():
    from pipeline.live.identify import combine
    c = combine([{"a": 0.6, "b": 0.4}, {"a": 0.6, "b": 0.4}])
    assert abs(c["a"] - 0.36 / 0.52) < 1e-12 and abs(sum(c.values()) - 1.0) < 1e-12
