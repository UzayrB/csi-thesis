"""THE 2026-09-28b IDENTIFICATION FREEZE IS ENFORCED: the v2 registration, its code and its tests.

`reports/REGISTER_ID_DC2_V2_2026-09-28.md` section E. Written after both DC2 days were scored and before
v2's first run on DC2 data. A change after it is POST HOC and needs a dated amendment and a new freeze,
never an edit; either way it starts with this test failing.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from tests import _restructure as RS

REPO = pathlib.Path(__file__).resolve().parents[1]
FREEZE = REPO / "runs" / "IDENTIFICATION_FROZEN_2026-09-28b.json"
PRIOR = "runs/IDENTIFICATION_FROZEN_2026-09-28.json"
MUST = ("reports/REGISTER_ID_DC2_V2_2026-09-28.md", "reports/BRIEF_ID_DC2_V2_2026-09-28.md",
        "pipeline/identify/idv2_core.py", "pipeline/identify/idv2_run.py", "tests/test_idv2.py",
        "tests/test_freeze_2026_09_28b.py")


def _h(p):
    return RS.frozen_sha(p)


def test_every_file_frozen_on_2026_09_28b_is_unchanged():
    assert FREEZE.exists(), f"{FREEZE.name} is missing: the v2 registration names it"
    F = json.loads(FREEZE.read_text(encoding="utf-8"))
    bad = [p for p, v in F["sha256"].items() if _h(p) != v]
    assert not bad, f"frozen on 2026-09-28b and changed since: {bad}. Amend with a dated, post hoc note"


def test_the_freeze_holds_the_registration_its_code_and_tests_and_follows_28():
    F = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert set(MUST) <= set(F["sha256"])
    assert F["references"] == PRIOR and (REPO / PRIOR).exists()
    assert F["before_v2_real_data_run"] is True


def test_the_registration_carries_the_brief_sections_4_to_6_verbatim():
    reg = (REPO / RS.current("reports/REGISTER_ID_DC2_V2_2026-09-28.md")).read_text(encoding="utf-8")
    brief = (REPO / RS.current("reports/BRIEF_ID_DC2_V2_2026-09-28.md")).read_text(encoding="utf-8")
    verb = brief[brief.index("## 4. The configurations"):brief.index("## 7. Tests")].rstrip()
    assert verb in reg


def test_the_code_carries_the_registered_hyperparameters():
    from pipeline.identify import idv2_core as C
    assert C.HP["win_frames"] == 34 and C.HP["hop_frames"] == 4 and C.HP["steps"] == 3000
    assert C.HP["batch"] == 64 and C.HP["lr"] == 1e-3 and C.HP["weight_decay"] == 1e-4
    assert C.HP["channels"] == (16, 32, 32) and C.HP["dropout"] == 0.3 and C.HP["seeds"] == (0, 1, 2, 3, 4)
    assert C.n_params(C.make_net(3, 6)) == 19890
