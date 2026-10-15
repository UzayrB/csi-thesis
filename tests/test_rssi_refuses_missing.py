"""A missing RSSI source is a REFUSAL, never a zero fill. Found by the DC2 stand-in, 2026-09-23d.

`recordings.load_rssi` used to print "RSSI missing ... those links are left at zero" and carry on.
With `DATA_ROOT` hard-coded to `data`, DC2's view directory made every Room B link "missing", the
heads saw all-zero RSSI, and the stand-in decoded at chance with an emission spread of 27.6 nats
against Room A's 2.11. Run in a subprocess so its roots never touch this pytest process.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_missing_rssi_source_raises(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("TDR_")}
    env.update({"TDR_DATA_ROOT": str(tmp_path / "no_raw_here"), "TDR_ROOM": "room_A",
                "TDR_ART_DIR": str(tmp_path / "art"), "OMP_NUM_THREADS": "1"})
    code = ("import numpy as np\n"
            "from pipeline.constrained.recordings import load_meta, load_rssi, DATA_ROOT\n"
            f"assert DATA_ROOT == {str(tmp_path / 'no_raw_here')!r}, DATA_ROOT\n"
            "rec = load_meta('01', 'participant_PA5_walk')\n"
            "try:\n"
            "    load_rssi('01', 'participant_PA5_walk', rec.t0_epoch)\n"
            "    print('NO_RAISE')\n"
            "except RuntimeError as e:\n"
            "    print('REFUSED', 'refusing to fill with zeros' in str(e))\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True,
                       text=True, timeout=300)
    assert p.returncode == 0, p.stderr[-2000:]
    assert "REFUSED True" in p.stdout, p.stdout


def test_the_data_root_defaults_to_data():
    src = (REPO / "pipeline" / "constrained" / "recordings.py").read_text()
    assert 'DATA_ROOT = os.environ.get("TDR_DATA_ROOT", "data")' in src
