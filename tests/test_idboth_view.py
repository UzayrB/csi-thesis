"""The identification view (2026-09-24): the both-directions capture, scored by the FROZEN id29, must
give exactly what the 23e layout gives on the same A_fwd data. SYNTHETIC data only.

The same synthetic recordings are laid out twice: as the 23e capture had them (A_fwd only), and as
capture_idboth has them (A_rev passes between every A_fwd pass, day 1 slow and fast blocks added,
in data/room_B/identification/). The second goes through the view. Every pre-registered figure must
be identical: the extra data must not reach a pre-registered analysis, and nothing may be lost.
"""

from __future__ import annotations

import glob
import json
import os
import shutil

import pytest

from pipeline.identify import capture_idboth as C
from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idboth_view as V
from tests.test_id29_dc2_score import PLAN as SYN_PLAN
from tests.test_id29_dc2_score import make_cfg, make_dc2


def _as_idboth(old_root: str, new_root: str) -> None:
    """Rewrite a 23e-layout synthetic capture in capture_idboth's layout, CSI byte-identical."""
    for d in sorted(glob.glob(os.path.join(old_root, "session_0*"))):
        nd = os.path.join(new_root, os.path.basename(d))
        os.makedirs(nd)
        for p in glob.glob(os.path.join(d, "*.bin")):
            shutil.copy(p, nd)
        for sp in glob.glob(os.path.join(d, "*.idmax.json")):
            st = os.path.basename(sp)[: -len(".idmax.json")]
            side = json.load(open(sp))
            if side["kind"] == "empty":
                shutil.copy(sp, nd)
                continue
            gt = json.load(open(os.path.join(d, f"{st}.gt.json")))
            passes = []
            for i, q in enumerate(sorted(gt["passes"], key=lambda z: z["t_start"])):
                passes.append({**q, "pass_id": 2 * i + 1})
                t0 = q["t_end"] + 0.5                                   # inside the 3 s gap
                passes.append({"pass_id": 2 * i + 2, "t_start": t0, "t_end": t0 + 2.0, "path_name": "A_rev",
                               "direction": "S", "anchor_times": [t0 + 0.4 * k for k in range(6)]})
            json.dump({"passes": passes}, open(os.path.join(nd, f"{st}.gt.json"), "w"))
            n = len(gt["passes"])
            C.write_sidecar(nd, st, {"kind": "walk", "day": side["day"], "block": side["block"],
                                     "position": "idspot", "rx2_xy": side["rx2_xy"],
                                     "count": C.count_status(n, {"A_fwd": n, "A_rev": n}, None)})
        for name_nat in glob.glob(os.path.join(nd, "*_idpath_d1_natural*")):      # day 1 pace blocks
            for extra in ("slow", "fast"):
                shutil.copy(name_nat, name_nat.replace("_d1_natural", f"_d1_{extra}"))


def _strip(res):
    drop = {"started", "ended", "minutes", "out", "report", "findings", "data_root", "paths", "layout"}
    if isinstance(res, dict):
        return {k: _strip(v) for k, v in res.items() if k not in drop}
    if isinstance(res, list):
        return [_strip(v) for v in res]
    return res


@pytest.fixture(scope="module")
def both(tmp_path_factory):
    old = str(tmp_path_factory.mktemp("old"))
    cfg_old = make_cfg(old)
    open(cfg_old.report, "w").write("# report\n")
    make_dc2(cfg_old.data_root)
    new = str(tmp_path_factory.mktemp("new"))
    _as_idboth(cfg_old.data_root, os.path.join(new, "room_B", "identification"))
    view = os.path.join(new, "view", "room_B")
    doc = V.build(os.path.join(new, "room_B", "identification"), view, plan=dict(SYN_PLAN))
    vtmp = str(tmp_path_factory.mktemp("v"))
    cfg_v = make_cfg(vtmp)
    open(cfg_v.report, "w").write("# report\n")
    cfg_v.data_root = view
    return doc, D.run(cfg_old), D.run(cfg_v), cfg_old, cfg_v


def test_view_keeps_only_the_preregistered_data(both):
    doc = both[0]
    walks = [e for e in doc["included"] if e["kind"] == "walk"]
    assert walks and all(e["dropped"] == e["a_fwd"] for e in walks)          # every A_rev dropped
    assert {e["stem"].split("_d1_")[1] for e in doc["excluded"] if "_d1_" in e.get("stem", "")} == {"slow", "fast"}


def test_every_preregistered_figure_is_identical(both):
    _doc, r_old, r_view, _a, _b = both
    assert json.dumps(_strip(r_old), sort_keys=True, default=str) == \
        json.dumps(_strip(r_view), sort_keys=True, default=str)


def test_the_view_passes_the_frozen_layout_check(both):
    cfg_v = both[4]
    found, bad = D._scan(cfg_v.data_root)
    assert bad == []
    more, _summary = D.layout_problems(cfg_v, found)
    assert more == []


def test_without_the_view_the_frozen_scorer_refuses_the_new_layout(both):
    """The reason the view exists: the frozen layout check rejects A_rev passes and day 1 pace blocks."""
    cfg_old = both[3]
    new_root = os.path.join(os.path.dirname(os.path.dirname(both[4].data_root)), "room_B", "identification")
    found, bad = D._scan(new_root)
    more, _ = D.layout_problems(cfg_old, found)
    assert bad or more


def test_the_view_is_never_built_inside_data(tmp_path):
    with pytest.raises(V.Refused):
        V.build(str(tmp_path), os.path.join("data", "room_B", "view"))


def test_the_frozen_scorer_refuses_data_room_b_itself(both, tmp_path):
    """Run with its default root on the new layout, id29 refuses at discovery; it never scores it by accident."""
    new_room_b = os.path.join(os.path.dirname(os.path.dirname(both[4].data_root)), "room_B")
    found, bad = D._scan(new_room_b)
    assert any("unexpected recording" in b for b in bad)            # the day 1 pace blocks
    cfg = make_cfg(str(tmp_path))
    open(cfg.report, "w").write("# report\n")
    cfg.data_root = new_room_b
    with pytest.raises(D.Refused):
        D.run(cfg)


@pytest.mark.parametrize("fwd, src_status, want", [
    (10, "COMPLETE", "COMPLETE"),
    (10, "COUNT_DIFFERS_REASON_LOGGED", "COMPLETE"),                # A_rev short, A_fwd whole
    (9, "COUNT_DIFFERS_REASON_LOGGED", "COUNT_DIFFERS_REASON_LOGGED"),
    (9, "REFUSED_COUNT_DIFFERS_NO_REASON", "REFUSED_COUNT_DIFFERS_NO_REASON"),
])
def test_counts_are_restated_for_a_fwd_and_keep_the_refusal(fwd, src_status, want):
    side = {"count": {"status": src_status, "reason": "stumbled"}}
    c = V._frozen_count(side, 1, "natural", fwd, {(1, "natural"): 10})
    assert c["status"] == want and c["planned"] == 10 and c["recorded"] == fwd
