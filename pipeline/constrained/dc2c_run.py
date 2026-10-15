"""dc2c_run. One DC2 step process with the dc2b and dc2c corrections. Command line exactly `dc2_run`'s.

`dc2c_pipeline` launches this in place of `dc2b_run` (see `dc2c.py`).
"""

from __future__ import annotations

import sys

from pipeline.constrained import dc2c

dc2c.install()

from pipeline.constrained.dc2_run import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
