"""dc2b_scorerlock. The EXPLORATORY display comparison (PREREG_DC2 section 13), with the dc2b corrections.

    python3 -m pipeline.constrained.dc2b_scorerlock --room room_B      # after dc2b_pipeline

The frozen `dc2_scorerlock` re-launches itself for its inner run; that launch is pointed here so the
inner process carries the same corrections.
"""

from __future__ import annotations

import subprocess as _sp
import sys
import types

from pipeline.constrained import dc2b

dc2b.install()

import pipeline.constrained.dc2_scorerlock as S  # noqa: E402


def _call(cmd, *a, **k):
    cmd = ["pipeline.constrained.dc2b_scorerlock" if x == "pipeline.constrained.dc2_scorerlock" else x
           for x in cmd]
    return _sp.call(cmd, *a, **k)


S.subprocess = types.SimpleNamespace(call=_call)

if __name__ == "__main__":
    sys.exit(S.main())
