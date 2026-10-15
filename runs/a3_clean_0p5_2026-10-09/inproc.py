"""Run a pipeline command in this process after registering the f05r cells (reg.py), so the command sees them.

    python3 inproc.py pd_clean crossfit --cell f05r_...           (pd_clean.main with --inner)
    python3 inproc.py pd_clean decode --cell f05r_... --variants V (pd_clean.main with --inner)
    python3 inproc.py pd_cells infer --cell f05r_... --head h      (pd_cells.main)

The caller sets the cell's environment (pd_cells.env_for), as pd_clean._outer and pd_cells._sub do.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import reg  # noqa: E402

reg.register()
mod, rest = sys.argv[1], sys.argv[2:]
if mod == "pd_clean":
    from pipeline.constrained import pd_clean as M
    sys.exit(M.main(rest + ["--inner"]))
if mod == "pd_cells":
    from pipeline.constrained import pd_cells as M
    sys.exit(M.main(rest))
raise SystemExit(f"unknown module {mod}")
