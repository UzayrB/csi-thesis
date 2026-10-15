"""The P1-GP DC2 scorer (addendum C), on SYNTHETIC recordings only.

The recordings are id29's synthetic captures (real CSIBIN01 format, named as capture_idpath names
them): a per-person gait rate on TX-RX2 and TX-RX3 that the pace blocks do NOT change, and a
per-person walking speed that the pace blocks DO change. So a gait arm keeps its accuracy on the
pace blocks while S0 drops.
"""

import json
import os

import numpy as np
import pytest

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idgp_dc2_score as S
from pipeline.identify.common import RETIRED, SIX
from tests import test_id29_dc2_score as T

ARM = {"arm": "G", "head": "lda", "fusion": "concat", "form": "cor", "scope": "a"}


def make_cfg(tmp, arm=ARM):
    base = T.make_cfg(tmp)
    add = os.path.join(tmp, "ADD_C.md")
    open(add, "w").write("synthetic addendum C\n")
    fz = os.path.join(tmp, "FREEZE_f.json")
    json.dump({"addendum_c_sha256": D.sha256(add), "DC2_P1_GP": arm}, open(fz, "w"))
    return S.GPConfig(base=base, addendum_c=add, freeze_f=fz, out=os.path.join(tmp, "out_gp"),
                      findings=os.path.join(tmp, "FINDINGS_gp.txt"), report=os.path.join(tmp, "REPORT.md"))


@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("dc2gp"))
    cfg = make_cfg(tmp)
    open(cfg.report, "w").write("# report\n")
    T.make_dc2(cfg.base.data_root)
    return cfg, S.run(cfg)


def test_planted_gait_is_recovered_cross_day(scored):
    _cfg, r = scored
    assert r["P1_GP"]["arm"]["acc_pct"] > 50.0
    assert r["P1_GP"]["arm"]["n"] == 18 and r["P1_GP"]["S0"]["n"] == 18


def test_pace_blocks_move_S0_and_not_the_gait_arm(scored):
    _cfg, r = scored
    pb = r["pace_blocks"]
    assert pb["S0_manipulation_check"], pb
    assert pb["arm_minus_S0_on_slow_and_fast"]["ABOVE_ZERO"], pb["arm_minus_S0_on_slow_and_fast"]
    assert pb["READING"].startswith(("GAIT-CONSISTENT", "KEEPS MORE")), pb["READING"]


def test_every_row_and_check_is_present(scored):
    cfg, r = scored
    for k in ("P1_GP", "check1_vs_S0", "check2", "check3_speed_overlap", "check4_name", "pace_blocks",
              "MULTI_PASS", "wording", "margin_s"):
        assert k in r, k
    assert set(r["MULTI_PASS"]) == {"natural", "slow", "fast"}
    assert r["MULTI_PASS"]["natural"]["arm"]["n_decisions"] == 6
    assert r["check3_speed_overlap"]["n"] > 0
    txt = open(os.path.join(cfg.out, "results.json")).read() + open(cfg.findings).read() + open(cfg.report).read()
    assert not any(n in txt for n in SIX + RETIRED)
    assert open(cfg.findings).read().startswith("PASSED")


def test_label_shuffle_falls_towards_chance(scored):
    cfg, _r = scored
    found, _bad = D._scan(cfg.base.data_root)
    spot = tuple(json.load(open(cfg.base.spot_file))["xy"])
    W = S.matrices(S.extract(cfg, found, spot))
    y = np.random.default_rng(0).permutation(W["M"]["y"])
    r = S.score(cfg, W, ARM, spot, y=y)
    assert r["P1_GP"]["arm"]["acc_pct"] < 45.0


def test_hash_gate_blocks_a_modified_addendum_c(tmp_path):
    cfg = make_cfg(str(tmp_path))
    open(cfg.addendum_c, "a").write("edited after freezing\n")
    with pytest.raises(D.Refused) as e:
        S.run(cfg)
    assert e.value.kind == "hash"


def test_hash_gate_still_checks_addendum_b(tmp_path):
    cfg = make_cfg(str(tmp_path))
    open(cfg.base.addendum, "a").write("edited\n")
    with pytest.raises(D.Refused) as e:
        S.run(cfg)
    assert e.value.kind == "hash"


def test_refuses_an_arm_it_does_not_implement(tmp_path):
    cfg = make_cfg(str(tmp_path), arm={**ARM, "arm": "GPCNN_late"})
    with pytest.raises(D.Refused):
        S.run(cfg)


def test_rerun_guard(tmp_path):
    cfg = make_cfg(str(tmp_path))
    os.makedirs(cfg.out, exist_ok=True)
    open(os.path.join(cfg.out, "results.json"), "w").write("{}")
    with pytest.raises(D.Refused) as e:
        S.run(cfg)
    assert e.value.kind == "rerun"
