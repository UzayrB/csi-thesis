"""How a pinned or frozen file is held after the 1 October 2026 restructure of pipeline/.

The restructure (reports/project/repository/2026-10-01_pipeline-restructure.md) moved files and rewrote the lines that name a
pipeline module or file, and gave files one level deeper one more dirname to find the repository. Every move is in
reports/project/repository/2026-10-01_pipeline-moves.json, with the commit it started from ("base_commit"). A frozen file is held two
ways:
  1. at the base commit its bytes still have the frozen hash, so the freeze held until the restructure;
  2. at the restructure commit, at its new path, every line that differs from the base names a pipeline module or
     file, or is the repository-root line, so the restructure changed nothing else.

Check 2 compares the base commit with the restructure commit itself (RESTRUCTURE), not with the working tree: it
proves the move was mechanical. Later edits are separate changes (the pins were released that day), so they do not
fail it, and files deleted later (pipeline/retired/, the same afternoon) are still compared as the move left them.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
MAP = json.loads((REPO / "reports" / "project" / "repository" / "2026-10-01_pipeline-moves.json").read_text(encoding="utf-8"))
BASE = MAP["base_commit"]
RESTRUCTURE = "6769f8c"        # the restructure commit (reports/project/repository/2026-10-01_pipeline-restructure.md)
MECHANICAL = re.compile(r"pipeline[./]|__file__|^\s*$")


def new_path(p: str) -> str:
    return MAP["moves"].get(p, p)


def at_base(p: str) -> bytes:
    return subprocess.run(["git", "show", f"{BASE}:{p}"], cwd=REPO, capture_output=True, check=True).stdout


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def deleted(p: str) -> bool:
    """True for a file (old path) that moved to pipeline/retired/ and was deleted with it."""
    return new_path(p).startswith("pipeline/retired/") and not (REPO / new_path(p)).exists()


def at_restructure(p: str) -> bytes:
    """`p` (old path) as the restructure commit left it, at its new path."""
    return subprocess.run(["git", "show", f"{RESTRUCTURE}:{new_path(p)}"], cwd=REPO, capture_output=True,
                          check=True).stdout


def non_mechanical_changes(p: str) -> list:
    """The lines the restructure commit changed in `p` (old path) that are not restructure edits."""
    old = at_base(p).decode("utf-8").splitlines()
    new = at_restructure(p).decode("utf-8").splitlines()
    out = []
    for ln in difflib.unified_diff(old, new, lineterm="", n=0):
        if ln.startswith(("---", "+++", "@@")):
            continue
        if ln[:1] in "+-" and not MECHANICAL.search(ln[1:]):
            out.append(ln)
    return out


# ---------------------------------------------------------------- the reports reorganisation, 1 October 2026
#
# The same evening every report was moved and renamed (reports/project/repository/2026-10-01_reports-reorganisation.md).
# The freezes and the pins name the old paths, unchanged; the map gives each old path its new one. A frozen file is
# hashed where it is now. Two freeze tests hash themselves and were edited to follow the moves; for those, the bytes
# at the reorganisation's base commit carry the frozen hash, and the file now must equal those bytes with exactly
# the line edits listed in EDITED, nothing else.

REPORTS = json.loads((REPO / "reports" / "project" / "repository" / "2026-10-01_reports-moves.json")
                     .read_text(encoding="utf-8"))

EDITED = {
    "tests/test_freeze_2026_09_28.py": [
        ("REPO = pathlib.Path(__file__).resolve().parents[1]\n",
         "from tests import _restructure as RS\n\nREPO = pathlib.Path(__file__).resolve().parents[1]\n"),
        ("def _h(p):\n    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()\n",
         "def _h(p):\n    return RS.frozen_sha(p)\n"),
    ],
    "tests/test_freeze_2026_09_28b.py": [
        ("REPO = pathlib.Path(__file__).resolve().parents[1]\n",
         "from tests import _restructure as RS\n\nREPO = pathlib.Path(__file__).resolve().parents[1]\n"),
        ("def _h(p):\n    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()\n",
         "def _h(p):\n    return RS.frozen_sha(p)\n"),
        ('(REPO / "reports/REGISTER_ID_DC2_V2_2026-09-28.md")', '(REPO / RS.current("reports/REGISTER_ID_DC2_V2_2026-09-28.md"))'),
        ('(REPO / "reports/BRIEF_ID_DC2_V2_2026-09-28.md")', '(REPO / RS.current("reports/BRIEF_ID_DC2_V2_2026-09-28.md"))'),
    ],
}


def current(p: str) -> str:
    """Where a file named before 1 October 2026 is now: through the pipeline moves, then the reports moves."""
    p = MAP["moves"].get(p, p)
    return REPORTS["moves"].get(p, p)


def frozen_sha(p: str) -> str:
    """SHA-256 of the file a freeze names as `p`, as the freeze held it (see the note above EDITED)."""
    if p in EDITED:
        base = subprocess.run(["git", "show", f"{REPORTS['base_commit']}:{p}"], cwd=REPO, capture_output=True,
                              check=True).stdout
        text = base.decode("utf-8")
        for old, new in EDITED[p]:
            assert text.count(old) == 1, f"{p}: the recorded edit {old!r} no longer applies once"
            text = text.replace(old, new)
        if text.encode("utf-8") == (REPO / p).read_bytes():
            return sha(base)
    return sha((REPO / current(p)).read_bytes())
