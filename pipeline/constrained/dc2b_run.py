"""dc2b_run. One DC2 step process, run through the frozen `dc2_run` with the dc2b corrections.

`dc2b_pipeline` launches this in place of `dc2_run` (see `dc2b.py` for the three faults). The
command line is exactly `dc2_run`'s.
"""

from __future__ import annotations

import sys

from pipeline.constrained import dc2b

dc2b.install()

from pipeline.constrained.dc2_run import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
