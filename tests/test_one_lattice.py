"""THE ONE LATTICE: every root the shipped system draws from resolves to `lattice.py`.

Operator instruction 4, item 2, 2026-09-23d. The shipped roots were hard-coded in seven places;
one missed literal would quietly serve the retired grid lattice to part of the pool. Imported in a
SUBPROCESS with no roots set, exactly as a stage entry point would be, so the defaults are what is
tested and nothing leaks into this pytest process.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_PROBE = r'''
import json, os
import pipeline.constrained.g3_final as G3
import pipeline.constrained.g2_multihead as G2
import pipeline.constrained.s2a_dispend as SA
import pipeline.constrained.common as C
import pipeline.constrained.recordings as RC
import pipeline.constrained.n2_arms as N2
from pipeline.constrained import lattice as L
print("JSON" + json.dumps({
  "lattice": L.LATTICE, "art": os.path.abspath(C.ART_DIR), "half": L.half_art_dir(),
  "win": RC.WINDOWS_ROOT, "want_win": L.windows_root(),
  "one_s": {str(k): v for k, v in G2.ONE_S_TREES.items()},
  "want_one_s": {str(k): v for k, v in L.one_s_trees().items()},
  "g3_one_s": {str(k): v for k, v in G3.ONE_S_TREES.items()},
  "g100": G3.G100_TREE, "want_g100": L.g100_tree(),
  "dispend": os.path.abspath(SA.END_ART), "want_dispend": L.dispend_tree(),
  "n2_want": N2._WANT}))
'''


def _probe(extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ("TDR_ART_DIR", "TDR_WINDOWS_ROOT",
                                                             "TDR_LATTICE")}
    env.update(extra_env or {})
    env["OMP_NUM_THREADS"] = "1"
    p = subprocess.run([sys.executable, "-c", _PROBE], cwd=REPO, env=env, capture_output=True,
                       text=True, timeout=300)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads([ln for ln in p.stdout.splitlines() if ln.startswith("JSON")][-1][4:])


def test_every_shipped_root_is_the_press_aligned_lattice():
    d = _probe()
    assert d["lattice"] == "pressalign"
    assert d["art"] == d["half"] == d["n2_want"] and "s0.5_pressalign_half" in d["art"]
    assert d["win"] == d["want_win"] and "windows_s0.5_pressalign" in d["win"]
    assert d["one_s"] == d["want_one_s"] == d["g3_one_s"]
    assert all("s0.5_pressalign" in v for v in d["one_s"].values())
    assert d["g100"] == d["want_g100"] and "s0.5_pressalign_g100" in d["g100"]
    assert d["dispend"] == d["want_dispend"] and "s0.5_pressalign_dispend" in d["dispend"]


def test_the_grid_lattice_is_still_reachable_for_reproduction():
    d = _probe({"TDR_LATTICE": "grid"})
    assert d["lattice"] == "grid" and d["art"].endswith(os.path.join("runs", "artefacts_half"))
    assert d["g100"].endswith("artefacts_g1g100s0")


def test_the_live_engine_and_the_offline_cutter_share_one_press_phase():
    src = (REPO / "pipeline" / "constrained" / "y4_pressalign.py").read_text()
    assert "from pipeline.constrained.lattice import PRESS_EPS_S as EPS_S" in src
    live = (REPO / "pipeline" / "live" / "tracker_live.py").read_text()
    assert "from pipeline.constrained.lattice import PRESS_EPS_S" in live
    assert "rephase_to_press" in live
