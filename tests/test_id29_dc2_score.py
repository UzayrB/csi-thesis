"""The slot-design DC2 scorer (id29) and the capture wrapper's rules, on SYNTHETIC data only.

Synthetic recordings are real-format CSIBIN01 captures named exactly as `capture_idpath` names them.
Planted: a per-person gait rate, strongest on the TX-RX2 link, weaker on TX-RX3 and absent on TX-RX1
(so the P2 ordering is recoverable); a per-person walking speed that the pace blocks change (so S0
drops); and random per-recording gain, with NO person-linked placement signal (so P4 sits at chance).
"""

import json
import os

import numpy as np
import pytest

from pipeline.identify import capture_idpath as CAP
from pipeline.identify import id29_dc2_score as D
from pipeline.identify.common import SIX

FS = 150.0
RATES = dict(zip(SIX, np.linspace(1.5, 2.5, 6)))
SPEED = dict(zip(SIX, np.linspace(1.0, 1.6, 6)))
PACE = {"natural": 1.0, "slow": 0.65, "fast": 1.4}
DEPTH = {"RX1": 0.0, "RX2": 0.25, "RX3": 0.25}
#: how often a link carries the person's OWN rate (otherwise a random participant's): TX-RX2 always,
#: TX-RX3 half the time, so the planted ordering is TX-RX2 > TX-RX3 > TX-RX1 below the ceiling
RELIABLE = {"RX1": 0.0, "RX2": 1.0, "RX3": 0.5}
PLAN = {(1, "natural"): 6, (2, "natural"): 3, (2, "slow"): 3, (2, "fast"): 3}
SPOT = CAP.SPOTS["primary"]


def _base(n, gain):
    b = 20.0 + 8.0 * np.sin(np.arange(128) * 0.21)
    a = np.tile(b * gain, (n, 1))
    for i in sorted({0, 1, 64} | set(range(27, 38)) | set(range(93, 104))):
        a[:, i] = 0.0
    return a


def write_bin(path, t_true, amp, rng):
    from pipeline.io.capture_logger import FILE_MAGIC, FRAME_DTYPE
    n = len(t_true)
    fr = np.zeros(n, FRAME_DTYPE)
    fr["t_mono"] = t_true + rng.uniform(0, 0.045, n)
    fr["t_host"] = fr["t_mono"] + 1.79e9
    fr["local_timestamp"] = np.round((t_true - t_true[0] + 3.0) * 1e6).astype(np.uint64)
    fr["rssi"] = -60
    fr["channel"] = 6
    data = np.zeros((n, 256), np.int8)
    data[:, 1::2] = np.clip(np.round(amp), 0, 127).astype(np.int8)
    fr["data"] = data
    hdr = json.dumps({"dtype": [list(d) for d in FRAME_DTYPE.descr], "csi_len": 256}).encode()
    with open(path, "wb") as f:
        f.write(FILE_MAGIC + np.uint32(len(hdr)).tobytes() + hdr + fr.tobytes())


def write_walk(d, name, day, block, n_pass, rng, spot=SPOT):
    st = CAP.stem(name, day, block)
    t0 = 1000.0 + 1000 * day + 200 * ["natural", "slow", "fast"].index(block)
    spans, t = [], t0 + 2.0
    for _ in range(n_pass):
        dur = 5.0 / (SPEED[name] * PACE[block]) * (1.0 + rng.normal(0, 0.05))
        spans.append((t, t + dur))
        t += dur + 3.0
    tt = np.arange(t0, t + 1.0, 1.0 / FS)
    for L in ("RX1", "RX2", "RX3"):
        m = np.ones(len(tt))
        for a0, a1 in spans:
            k = (tt >= a0) & (tt <= a1)
            rate = RATES[name] if rng.random() < RELIABLE[L] else RATES[SIX[rng.integers(0, 6)]]
            m[k] = 1.0 + DEPTH[L] * np.sin(2 * np.pi * rate * tt[k] + rng.uniform(0, 6.28))
        a = _base(len(tt), rng.uniform(0.85, 1.15)) * m[:, None] + rng.normal(0, 0.4, (len(tt), 128))
        write_bin(os.path.join(d, f"{st}_{L}.bin"), tt, a, rng)
    passes = [{"pass_id": i + 1, "t_start": a0, "t_end": a1, "path_name": "A_fwd", "direction": "N",
               "anchor_times": list(np.linspace(a0, a1, 6))} for i, (a0, a1) in enumerate(spans)]
    json.dump({"passes": passes}, open(os.path.join(d, f"{st}.gt.json"), "w"))
    CAP.write_sidecar(d, st, {"kind": "walk", "day": day, "block": block, "position": "idspot",
                              "rx2_xy": list(spot), "count": CAP.count_status(n_pass, n_pass, None)})


def write_empty(d, name, day, pos, rng, gain=None, spot=SPOT):
    st = CAP.stem(name, day, f"empty_{pos}")
    tt = np.arange(0, 26.0, 1.0 / FS) + 5000 * day
    for L in ("RX1", "RX2", "RX3"):
        g = gain if (gain is not None and L == "RX2") else rng.uniform(0.85, 1.15)
        write_bin(os.path.join(d, f"{st}_{L}.bin"), tt, _base(len(tt), g) + rng.normal(0, 0.4, (len(tt), 128)), rng)
    CAP.write_sidecar(d, st, {"kind": "empty", "position": pos,
                              "rx2_xy": list(spot if pos == "idspot" else CAP.RX2_HOME)})


def make_dc2(root, seed=0):
    rng = np.random.default_rng(seed)
    for day in (1, 2):
        d = os.path.join(root, f"session_0{day}")
        os.makedirs(d, exist_ok=True)
        for name in SIX:
            for (dd, block), n in PLAN.items():
                if dd == day:
                    write_walk(d, name, day, block, n, rng)
            for pos in ("idspot", "home"):
                write_empty(d, name, day, pos, rng)


def synthetic_room_a(seed=1):
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.common import anon
    from pipeline.identify.id19_bank import KEEP
    rng = np.random.default_rng(seed)
    rows, feats, single = [], [], []
    for s in range(3):
        for name in SIX:
            for k in range(2):
                dur = 5.0 / SPEED[name] * (1.0 + rng.normal(0, 0.05))
                t = np.arange(0, dur, 1 / FS)
                A = []
                for L in ("RX1", "RX2", "RX3"):
                    m = 1.0 + 0.5 * DEPTH[L] * np.sin(2 * np.pi * RATES[name] * t)
                    A.append((_base(len(t), 1.0) * m[:, None] + rng.normal(0, 0.4, (len(t), 128)))[:, KEEP][:, FB.SC])
                feats.append(FB.pass_features(np.asarray(A), np.full((3, len(t)), -60.0)))
                single.append(FB.pass_features(np.stack([A[2]] * 3), np.full((3, len(t)), -60.0)))
                rows.append({"anon": anon(name), "day": 0, "block": "roomA", "t": float(k), "line": "A_fwd",
                             "speed_m_s": 5.0 / dur})
    names = sorted(set().union(*[f.keys() for f in feats]))
    X = np.array([[np.nan if f.get(n) is None else f[n] for n in names] for f in feats], float)
    return {"rows": rows, "X": X, "names": names, "single_RX3": single}


def make_cfg(tmp):
    pre = os.path.join(tmp, "PREREG.md")
    add = os.path.join(tmp, "ADD_B.md")
    open(pre, "w").write("synthetic pre-registration\n")
    open(add, "w").write("synthetic addendum B\n")
    fz = os.path.join(tmp, "FREEZE_e.json")
    json.dump({"prereg_sha256": D.sha256(pre), "addendum_b_sha256": D.sha256(add)}, open(fz, "w"))
    spot = os.path.join(tmp, "rx2_spot.json")
    json.dump({"label": "primary", "xy": list(SPOT)}, open(spot, "w"))
    return D.Config(prereg=pre, addendum=add, freeze=fz, data_root=os.path.join(tmp, "room_B"),
                    out=os.path.join(tmp, "out"), report=os.path.join(tmp, "REPORT.md"),
                    findings=os.path.join(tmp, "FINDINGS.txt"), spot_file=spot, plan=dict(PLAN),
                    cnn_seeds=(0,), cnn_epochs=2, n_boot=200, n_perm=200, room_a_loader=synthetic_room_a)


@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("dc2e"))
    cfg = make_cfg(tmp)
    open(cfg.report, "w").write("# report\n")
    make_dc2(cfg.data_root)
    return cfg, D.run(cfg)


# ------------------------------------------------------------------ the scored synthetic run

def test_planted_signal_is_recovered_cross_day(scored):
    _c, r = scored
    p = r["P1"]["PRIMARY"]
    assert p["acc_pct"] >= 60.0 and p["ci95_pct"][0] > p["chance_pct"] and p["perm_p"] <= 0.05, p


def test_p2_link_ordering_is_recovered_when_planted(scored):
    _c, r = scored
    L = r["P2"]["per_link_fixed_length"]
    assert L["RX2"]["acc_pct"] > L["RX3"]["acc_pct"] > L["RX1"]["acc_pct"], L
    assert r["P2"]["TX_RX1_near_chance"] and r["P2"]["ordering_held"]
    assert L["RX2"]["mean_F"] > 0.95 and L["RX3"]["mean_F"] == 0.5 and L["RX1"]["mean_F"] == 0.0


def test_the_blind_link_cannot_borrow_another_links_rhythm(scored):
    """TX-RX1 carries no planted signal. Its P2 rows are built from its own data alone, so they
    must sit at chance at BOTH lengths; three-link features leaked the planted rhythm into it
    through the shared cadence (66.7 percent, found 2026-09-23 19:35)."""
    _c, r = scored
    for kind in ("per_link_fixed_length", "per_link_full_length"):
        s = r["P2"][kind]["RX1"]
        assert s["ci95_pct"][0] <= s["chance_pct"], (kind, s)


def test_p3_speed_control_drops_on_the_pace_blocks(scored):
    _c, r = scored
    assert r["P3"]["S0"]["natural"]["acc_pct"] >= 60.0
    for d in ("slow", "fast"):
        assert r["P3"]["S0"][f"drop_{d}"]["drop_pts"] > 30.0
        assert r["P3"]["S0_manipulation_check"][d] is True


def test_p4_placement_is_at_chance_without_a_placement_signal(scored):
    _c, r = scored
    s = r["P4"]["idspot"]
    assert s["ci95_pct"][0] <= s["chance_pct"], s
    assert s["rx2_static_amplitude"]["n_placements"] == 12


def test_every_analysis_ran_and_the_outputs_were_written(scored):
    cfg, r = scored
    assert set(r) >= {"P1", "P2", "P3", "P4", "P5", "P6", "WITHIN_DAY_ONE_SLOT_CONFOUNDED"}
    assert open(cfg.findings).read().split()[0] == "PASSED"
    rep = open(cfg.report).read()
    assert rep.startswith("# report") and "DC2 identification, confirmatory" in rep
    for n in SIX:
        assert n not in rep and n not in open(os.path.join(cfg.out, "results.json")).read()


def test_label_shuffle_falls_to_chance(scored):
    cfg, _r = scored
    found, bad = D._scan(cfg.data_root)
    assert not bad
    dc2 = D.extract(cfg, found)
    M = D.build(dc2, synthetic_room_a())
    y = M["y"][np.random.default_rng(7).permutation(len(M["y"]))]
    r = D.score_all(cfg, M, dc2, SPOT, y)
    assert r["P1"]["PRIMARY"]["acc_pct"] < 40.0, r["P1"]["PRIMARY"]


# ------------------------------------------------------------------ P4 with a planted placement signal

def _empties(planted: bool, seed=3):
    rng = np.random.default_rng(seed)
    out = []
    for day in (1, 2):
        for k, name in enumerate(SIX):
            g = 0.7 + 0.1 * k if planted else rng.uniform(0.85, 1.15)
            X = []
            for _w in range(10):
                lv = np.concatenate([np.full(103, 20.0 * rng.uniform(0.95, 1.05)),
                                     np.full(103, 20.0 * g) + rng.normal(0, 0.3, 103),
                                     np.full(103, 20.0 * rng.uniform(0.95, 1.05)), [-60, -60, -60]])
                X.append(lv + rng.normal(0, 0.2, len(lv)))
            out.append({"anon": f"P{k + 1}", "day": day, "position": "idspot", "X": np.asarray(X),
                        "rx2_mean_amp": float(20.0 * g)})
    return out


def test_p4_detects_a_planted_placement_signal():
    cfg = D.Config(n_boot=200, n_perm=200)
    assert D.placement(_empties(True), "idspot", cfg)["ci95_pct"][0] > 100 / 6
    s = D.placement(_empties(False), "idspot", cfg)
    assert s["ci95_pct"][0] <= 100 / 6


# ------------------------------------------------------------------ P3 arithmetic

def test_p3_drop_arithmetic_and_verdicts():
    M = {"anon": np.array(["P1"] * 4 + ["P2"] * 4)}
    nat = {"te": list(range(8)), "pred": ["a"] * 8, "truth": ["a", "a", "a", "b"] * 2}
    pace = {"te": list(range(8)), "pred": ["a"] * 8, "truth": ["a", "b", "b", "b"] * 2}
    d = D.drop(nat, pace, M, 100)
    assert d["n_participants"] == 2 and abs(d["drop_pts"] - 50.0) < 1e-9 and d["ci95_pts"] == [50.0, 50.0]
    s0 = {"drop_pts": 50.0, "ci95_pts": [40.0, 60.0]}
    p1 = {"ci95_pct": [40.0, 70.0], "chance_pct": 16.67}
    assert D.verdict({"drop_pts": 55.0, "ci95_pts": [45, 65]}, s0, p1).startswith("ENCODES PACE")
    assert D.verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]}, s0, p1).startswith("GAIT-CONSISTENT")
    assert D.verdict({"drop_pts": 20.0, "ci95_pts": [5, 35]}, s0, p1) == "INCONCLUSIVE"
    assert D.verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]}, s0,
                     {"ci95_pct": [10.0, 30.0], "chance_pct": 16.67}).startswith("NOT INFORMATIVE")
    assert D.verdict({"drop_pts": 2.0, "ci95_pts": [-5, 9]}, {"drop_pts": 3, "ci95_pts": [-2, 8]},
                     p1).startswith("NOT DECIDABLE")


# ------------------------------------------------------------------ guards

def test_hash_gate_blocks_a_modified_addendum(tmp_path):
    cfg = make_cfg(str(tmp_path))
    assert set(D.check_hashes(cfg)) == {"prereg_sha256", "addendum_b_sha256"}
    open(cfg.addendum, "a").write("changed after freezing\n")
    with pytest.raises(D.Refused) as e:
        D.run(cfg)
    assert e.value.kind == "hash" and "addendum_b_sha256" in str(e.value)


def test_hash_gate_blocks_a_modified_preregistration(tmp_path):
    cfg = make_cfg(str(tmp_path))
    open(cfg.prereg, "a").write("changed\n")
    with pytest.raises(D.Refused) as e:
        D.run(cfg)
    assert e.value.kind == "hash" and "prereg_sha256" in str(e.value)


def test_rerun_guard(tmp_path):
    cfg = make_cfg(str(tmp_path))
    os.makedirs(cfg.out)
    json.dump({"prior": 1}, open(os.path.join(cfg.out, "results.json"), "w"))
    with pytest.raises(D.Refused) as e:
        D.run(cfg)
    assert e.value.kind == "rerun"
    os.makedirs(cfg.data_root)
    with pytest.raises(D.Refused) as e:
        D.run(cfg, rerun_reason="synthetic guard test")
    assert e.value.kind == "discovery"
    assert "synthetic guard test" in open(os.path.join(cfg.out, "RERUNS.log")).read()
    assert any(f.startswith("results_superseded_") for f in os.listdir(cfg.out))


def test_layout_check_passes_clean_data_and_touches_no_results(scored, tmp_path):
    cfg, _r = scored
    before = sorted(os.listdir(cfg.out))
    r = D.check_layout(cfg)
    assert r["ok"], r["problems"]
    assert sorted(os.listdir(cfg.out)) == before


@pytest.mark.parametrize("breakit,expect", [
    ("drop_empty", "missing recording"),
    ("rehearsal", "rehearsal file"),
    ("retired", "retired"),
    ("short_block", "passes against a plan"),
    ("moved_spot", "disagree"),
])
def test_layout_check_catches(tmp_path, breakit, expect):
    rng = np.random.default_rng(0)
    cfg = make_cfg(str(tmp_path))
    make_dc2(cfg.data_root, seed=5)
    d = os.path.join(cfg.data_root, "session_02")
    name = SIX[0]
    if breakit == "drop_empty":
        os.remove(os.path.join(d, CAP.stem(name, 2, "empty_home") + ".idmax.json"))
        for L in ("RX1", "RX2", "RX3"):
            os.remove(os.path.join(d, CAP.stem(name, 2, "empty_home") + f"_{L}.bin"))
    elif breakit == "rehearsal":
        open(os.path.join(d, CAP.stem(name, 2, "natural", rehearsal=True) + "_RX1.bin"), "w").close()
    elif breakit == "retired":
        open(os.path.join(d, "participant_Azrah_idpath_d2_natural_RX1.bin"), "w").close()
    elif breakit == "short_block":
        p = os.path.join(d, CAP.stem(name, 2, "slow") + ".gt.json")
        g = json.load(open(p))
        g["passes"] = g["passes"][:2]
        json.dump(g, open(p, "w"))
    elif breakit == "moved_spot":
        write_empty(d, name, 2, "idspot", rng, spot=CAP.SPOTS["fallback"])
    r = D.check_layout(cfg)
    assert not r["ok"] and any(expect in p for p in r["problems"]), r["problems"]


# ------------------------------------------------------------------ the capture wrapper's rules

def test_capture_rules():
    assert [pc for pc, _c in CAP.day_order(1)] == ["P1", "P2", "P3", "P4", "P5", "P6"]
    assert [pc for pc, _c in CAP.day_order(2)] == ["P6", "P5", "P4", "P3", "P2", "P1"]
    assert CAP.pace_order(SIX[0]) == ("slow", "fast") and CAP.pace_order(SIX[1]) == ("fast", "slow")
    assert CAP.planned_passes(1, "natural") == 10 and CAP.planned_passes(2, "fast") == 5
    for bad in ((1, "slow"), (1, "fast")):
        with pytest.raises(CAP.Refused):
            CAP.planned_passes(*bad)
    with pytest.raises(CAP.Refused):
        CAP.number("Azrah")
    with pytest.raises(CAP.Refused):
        CAP.check_block_order(SIX[0], 2, "slow", set())                  # natural first
    with pytest.raises(CAP.Refused):
        CAP.check_block_order(SIX[0], 2, "fast", {"natural"})            # P1 walks slow first
    CAP.check_block_order(SIX[1], 2, "fast", {"natural"})                # P2 walks fast first
    with pytest.raises(CAP.Refused):
        CAP.check_block_order(SIX[1], 2, "fast", {"natural", "fast"})    # never overwritten
    assert CAP.count_status(10, 10, None)["status"] == "COMPLETE"
    assert CAP.count_status(10, 9, None)["status"].startswith("REFUSED")
    assert CAP.count_status(10, 9, "one pass aborted, walker tripped")["status"] == "COUNT_DIFFERS_REASON_LOGGED"
    assert CAP.stem(SIX[0], 1, "natural", True).endswith("_REHEARSAL")
    assert CAP.out_dir(1, True).startswith(CAP.REHEARSAL_ROOT)


def test_spot_is_never_changed_once_dc2_files_exist(tmp_path):
    spot = str(tmp_path / "spot.json")
    root = str(tmp_path / "data")
    CAP.set_spot("primary", spot, root)
    assert CAP.spot(spot) == ("primary", (2.0, -0.5))
    CAP.set_spot("fallback", spot, root)                                 # no DC2 files yet: allowed
    os.makedirs(os.path.join(root, "room_B", "session_01"))
    open(os.path.join(root, "room_B", "session_01", CAP.stem(SIX[0], 1, "natural") + ".gt.json"), "w").close()
    with pytest.raises(CAP.Refused):
        CAP.set_spot("primary", spot, root)


def test_line_a_away_from_tx_is_a_fwd_in_the_grid_definition():
    from pipeline.constrained import paths as P
    from pipeline.io.anchors import PATHS
    v = np.asarray(P.load_paths()["A_fwd"], float)
    assert np.allclose(v[0], [2.5, 0.0]) and np.allclose(v[-1], [2.5, 5.0])
    assert PATHS["A_fwd"].direction == "N" and len(PATHS["A_fwd"].anchors) == 6


# ------------------------------------------------------------------ the rehearsal checker

# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_rehearsal_checker_sees_rx2_modulate_and_reads_link_health(tmp_path):
#     from pipeline.retired.identify import rehearsal_check as R
#     rng = np.random.default_rng(11)
#     d = str(tmp_path / "session_01")
#     os.makedirs(d)
#     name = SIX[0]
#     write_walk(d, name, 1, "natural", 3, rng)
#     write_empty(d, name, 1, "idspot", rng)
#     for f in os.listdir(d):                                   # rehearsal naming, as the wrapper writes it
#         root, ext = f.split("_idpath_d1_")
#         rest = ext.replace("natural", "natural_REHEARSAL").replace("empty_idspot", "empty_idspot_REHEARSAL")
#         os.rename(os.path.join(d, f), os.path.join(d, f"{root}_idpath_d1_{rest}"))
#     mod = R.modulation(str(tmp_path))
#     walk = [v for k, v in mod.items() if "natural" in k][0]["links"]
#     assert walk["RX2"]["FLAT"] is False and walk["RX2"]["gait_ratio"] > R.FLAT_RATIO
#     h = R.link_health(glob_one(d, "_RX2.bin"))
#     assert h["packets"] > 1000 and h["rate_hz"] > 100


def glob_one(d, suffix):
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(suffix)][0]
