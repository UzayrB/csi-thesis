"""One name, one stage. A variable may not be bound to two different load() calls in a module.

WHY THIS IS A TEST. On 2026-09-20 f3_render gained three stage reads whose names were already
taken twenty lines above: r3 was the lag sweep and became the prior sweep, r1 was the old census
and became the reference diagnostic, r5 was the timeline and became the lock comparison. The
render then produced six videos and crashed while writing ACCEPTANCE.md, because the later use of
the ORIGINAL binding got the new stage's results and indexed a list with a string.

That is the benign version. The dangerous version is the one where the shapes happen to match:
the stage would have written a full ACCEPTANCE.md with another stage's numbers in it, exited
zero, and nothing would have looked wrong.

THE RULE. Within a module, a name assigned from load("x") may not also be assigned from
load("y"). Rename one of them.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
CONSTRAINED = REPO / "pipeline" / "constrained"


def _shadowed(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    seen, dupes = {}, []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        v = node.value
        call = v.values[0] if isinstance(v, ast.BoolOp) and v.values else v
        if not (isinstance(call, ast.Call) and getattr(call.func, "id", "") == "load"
                and call.args):
            continue
        arg = getattr(call.args[0], "value", None)
        name = node.targets[0].id
        if name in seen and seen[name] != arg:
            dupes.append((name, seen[name], arg, getattr(node, "lineno", 0)))
        seen[name] = arg
    return dupes


# retired/constrained/ holds the past modules (attempts/ until 2026-10-01); the rule still covers them
# RETIRED 2026-10-01: this scan no longer includes pipeline/retired/constrained/, deleted with that folder
# (git tag tracking-final-2026-10-01). It was: + sorted((REPO / "pipeline" / "retired" / "constrained").glob("*.py"))
@pytest.mark.parametrize("path", sorted(CONSTRAINED.glob("*.py")), ids=lambda p: p.name)
def test_no_name_is_bound_to_two_different_stage_loads(path):
    dupes = _shadowed(path)
    assert not dupes, (
        f"{path.name} binds the same name to two different stages: "
        + "; ".join(f"{n!r} was load({a!r}) and is load({b!r}) at line {ln}"
                    for n, a, b, ln in dupes)
        + ". The later use of the first binding will silently read the second stage's results. "
          "Rename one of them.")
