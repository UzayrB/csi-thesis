"""The 0.5 s arm (amendment D1) must never touch the 1 s artefact tree.

WHY THIS FILE EXISTS. The feature cache is keyed ``session_<id>_<stem>.npy`` with NO stride in the
filename, and there are 6.3 GB of 1 s features that every other stage depends on. A 0.5 s run that
resolved the default root would overwrite them silently: no error, no warning, just every downstream
number quietly computed from the wrong features. The isolation is therefore enforced by the
environment and asserted here, both directions.

The two tests that exercised rb2d_retrain itself lived in tests/test_stride_isolation_rb2d.py until
2026-09-24, when they were removed with that module (git tag pre-cleanup). What stays here guards
the DEFAULT roots, which still ship and still matter.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(code: str, env_extra: dict | None = None):
    env = dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1", KMP_DUPLICATE_LIB_OK="TRUE")
    env.pop("TDR_ART_DIR", None)
    env.pop("TDR_WINDOWS_ROOT", None)
    env.update(env_extra or {})
    return subprocess.run([PY, "-c", code], capture_output=True, text=True, cwd=REPO, env=env)


def test_default_roots_are_unchanged():
    """The override must be invisible unless someone asks for it."""
    r = run("from pipeline.constrained.recordings import WINDOWS_ROOT\n"
            "from pipeline.constrained.common import ART_DIR\n"
            "print(WINDOWS_ROOT); print(ART_DIR)")
    assert r.returncode == 0, r.stderr
    windows, art = r.stdout.strip().splitlines()
    assert windows == "runs/constrained/windows_s1.0_roomA", f"default WINDOWS_ROOT changed to {windows!r}"
    assert art.endswith(os.path.join("runs", "artefacts")), f"default ART_DIR changed to {art!r}"


def test_override_redirects_every_cache_off_the_one_second_tree():
    r = run("import os\n"
            "from pipeline.constrained.recordings import WINDOWS_ROOT, feature_cache_path\n"
            "from pipeline.constrained.common import ART_DIR\n"
            "from pipeline.constrained.artefacts import posterior_path, MODEL_DIR, POST_DIR\n"
            "print(WINDOWS_ROOT); print(ART_DIR)\n"
            "print(feature_cache_path('01', 'x')); print(posterior_path('t', 25, 1, 0))\n"
            "print(MODEL_DIR); print(POST_DIR)",
            {"TDR_WINDOWS_ROOT": "runs/constrained/windows_half",
             "TDR_ART_DIR": os.path.join(REPO, "runs", "artefacts_half")})
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines[0] == "runs/constrained/windows_half"
    one_second = os.path.join(REPO, "runs", "artefacts") + os.sep
    for p in lines[1:]:
        assert "artefacts_half" in p, f"{p} is not in the isolated tree"
        assert not p.startswith(one_second), f"{p} would land in the 1 s tree"


def test_nothing_in_the_isolated_arm_resolves_under_data():
    r = run("import os\n"
            "from pipeline.constrained.recordings import WINDOWS_ROOT, feature_cache_path\n"
            "from pipeline.constrained.common import ART_DIR\n"
            "for p in (WINDOWS_ROOT, ART_DIR, feature_cache_path('01', 'x')):\n"
            "    assert not os.path.abspath(p).startswith(os.path.abspath('data')), p\n"
            "print('ok')",
            {"TDR_WINDOWS_ROOT": "runs/constrained/windows_half",
             "TDR_ART_DIR": os.path.join(REPO, "runs", "artefacts_half")})
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout

