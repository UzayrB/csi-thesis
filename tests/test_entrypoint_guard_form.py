"""An entry-point guard must check the ROOTS, never the import order.

WHY THIS IS A TEST. The form

    assert "pipeline.constrained.common" not in sys.modules, "<mod> must be the entry point"

breaks the moment another stage imports the module as a library, because by then common is
legitimately already imported. That happened FOUR times in three days: sb2 broke sb1 and sb1b, wp1
broke wp_arm, n2 broke n3 and n4, and f1 broke f3. Each time it was fixed in one place and written
again in the next module, because nothing checked.

The roots-based form does the job the guard is actually for. The danger is the artefact root being
UNSET while a differently-strided tree is live, and that is what it tests.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
BANNED = re.compile(r'assert\s+"pipeline\.constrained\.common"\s+not\s+in\s+sys\.modules')

#: ENTRY-POINT-ONLY stages, never imported by another module, where the bare form is correct and
#: is load-bearing: each sets its own roots and the guard checks that doing so will take effect.
#: Kept as an explicit short list rather than a clever rule, because a clever rule is how a real
#: regression gets waved through. Verified by test_the_allowlist_is_honest below.
ENTRY_POINT_ONLY = {
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     "pipeline/retired/constrained/re4_semibounded.py": "the ends-tree semi-bounded decode",
}


def test_no_module_guards_on_import_order():
    hits = []
    for p in (REPO / "pipeline").rglob("*.py"):
        if "__pycache__" in str(p) or p.name == "test_entrypoint_guard_form.py":
            continue
        src = p.read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), 1):
            if not BANNED.search(line):
                continue
            # the COMBINED form is fine: it allows a library caller that set the roots correctly
            # and still catches the real danger. Only the bare form is banned.
            window = "\n".join(src.splitlines()[max(0, i - 4):i + 2])
            if "_already" in window or "assert_isolated" in window:
                continue
            if str(p.relative_to(REPO)) in ENTRY_POINT_ONLY:
                continue
            hits.append(f"{p.relative_to(REPO)}:{i}")
    assert not hits, (
        "these modules guard on IMPORT ORDER, which breaks any later stage that imports them as a "
        f"library: {hits}. Use the roots-based form instead:\n"
        '    assert os.environ.get("TDR_ART_DIR"), "<mod> needs the artefact root set"\n'
        "or, where the module must run on a specific tree, assert on that tree's path inside "
        "main() rather than at import time.")


def test_the_isolated_stages_still_assert_something():
    """The ban must not become a licence to drop the guard entirely."""
    missing = []
    for name in ("sb2_structural", "n2_arms", "f1_arms", "wp1_gate"):
        p = REPO / "pipeline" / "constrained" / f"{name}.py"
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        guarded = ("assert_isolated" in src
                   or ("TDR_ART_DIR" in src and "assert" in src))
        if not guarded:
            missing.append(name)
    assert not missing, f"these isolated stages assert nothing about their roots: {missing}"


def test_the_allowlist_is_honest():
    """Every module claimed as entry-point-only must really not be imported by another module."""
    imported_by = {}
    for p in (REPO / "pipeline").rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        src = p.read_text(encoding="utf-8")
        for rel in ENTRY_POINT_ONLY:
            mod = pathlib.Path(rel).stem
            if f"import {mod}" in src and p.name != f"{mod}.py":
                imported_by.setdefault(rel, []).append(str(p.relative_to(REPO)))
    assert not imported_by, (
        "these are listed as entry-point-only but ARE imported elsewhere, so their bare guard "
        f"will break those callers: {imported_by}")
