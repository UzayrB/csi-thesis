"""The ground truth cannot reach the app's model (Uzayr, 30 September 2026: one model, the live app).

The truth enters the live app in ONE place, `TrackingSession.set_truth`, for the replay-only green overlay and
the CORRECT/WRONG verdict. These tests prove it goes nowhere else:

1. STATIC (always): in `pipeline/live/`, the truth attribute and `_truth_at` are read only inside the three
   screen functions (`set_truth`, `_truth_at`, `screen_state`). No other app module reads a sidecar's labels.
   The replay reads the sidecar's press times, the operator's inputs, and passes nothing else.
2. DYNAMIC (TDR_SLOW=1): the first two walks of one B2 recording are replayed twice through the final model,
   once with the true sidecar and once with a scrambled one (the line names permuted, the anchors reversed).
   Every committed line, lock and drawn dot must be identical.
"""

from __future__ import annotations

import ast
import copy
import glob
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO_ROOT, "pipeline", "live")
SCREEN_FUNCS = {"set_truth", "_truth_at", "screen_state"}


def _truth_uses(path: str) -> list:
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_FunctionDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Attribute(self, node):
            # a READ of the truth (a store, the initialisation to None, is not a read)
            if node.attr in ("truth", "_truth_at") and isinstance(node.ctx, ast.Load):
                out.append((node.attr, self.stack[-1] if self.stack else "<module>", node.lineno))
            self.generic_visit(node)
    V().visit(tree)
    return out


def test_truth_is_read_only_by_the_screen():
    bad = []
    for p in sorted(glob.glob(os.path.join(LIVE, "*.py"))):
        if os.path.basename(p) in ("app_score.py", "app_teaching.py") or os.path.basename(p).startswith("identify"):
            continue                               # the scorer is not the app: it is the one reader of labels;
                                                   # identification's modules are not the tracking app
        for attr, fn, line in _truth_uses(p):
            if fn not in SCREEN_FUNCS:
                bad.append(f"{os.path.relpath(p, REPO_ROOT)}:{line} {attr} read in {fn}")
    assert not bad, "the truth is read outside the screen: " + "; ".join(bad)


def test_no_app_module_reads_labels():
    """Only the replay opens a sidecar, for the presses; no app module reads path_name or anchor_coords."""
    bad = []
    for p in sorted(glob.glob(os.path.join(LIVE, "*.py"))):
        name = os.path.basename(p)
        if name in ("app_score.py", "app_teaching.py", "__main__.py", "gates.py") or name.startswith("identify"):
            continue                               # the scorer and the teaching export (both read labels AFTER a
                                                   # replay, as the scorer does); the entry point's stand-in replay;
                                                   # the old gates; IDENTIFICATION's modules (not the tracking app)
        src = open(p, encoding="utf-8").read()
        for token in ("anchor_coords", '"path_name"', "'path_name'"):
            if token in src and name not in ("tracking.py",):
                bad.append(f"{name}: {token}")
    assert not bad, "; ".join(bad)


def test_replay_passes_only_press_times():
    """recording_events reads, of a sidecar pass, only t_start, t_end and pass_id: every string key it
    subscripts is checked, so a label (path_name, anchor_times, anchor_coords, xy) cannot be read. (The
    function `anchor_times` it imports is the device-clock fit, not the sidecar field.)"""
    tree = ast.parse(open(os.path.join(LIVE, "replay.py"), encoding="utf-8").read())
    keys = {n.slice.value for n in ast.walk(tree) if isinstance(n, ast.Subscript)
            and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}
    labels = {"path_name", "anchor_times", "anchor_coords", "xy", "cells", "direction"}
    assert not (keys & labels), f"replay.py subscripts label keys {sorted(keys & labels)}"
    assert {"t_start", "t_end", "pass_id"} <= keys, sorted(keys)


# ------------------------------------------------------------------ the identity tag (Uzayr, 30 Sep, item 2)
#: identification's decision lines (reports/identification/live-interface.md) reach the tracking app through ONE setter,
#: TrackingSession.identity, and are read only by the screen
IDENTITY_FUNCS = {"identity", "_identity_for", "screen_state"}
#: the modules that ARE identification, the entry point that routes its commands to it, and the old equality-gate
#: suite (`gates.py`, a verification harness holding identification's own gate 5; no tracking run imports it)
IDENTIFICATION_SIDE = {"identify.py", "identify_engine.py", "__main__.py", "gates.py"}


def _attr_loads(path: str, attrs: set) -> list:
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_FunctionDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Attribute(self, node):
            if node.attr in attrs and isinstance(node.ctx, ast.Load):
                out.append((node.attr, self.stack[-1] if self.stack else "<module>", node.lineno))
            self.generic_visit(node)

        def visit_Call(self, node):
            # getattr(x, "identities") is a read too
            if (isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant) and node.args[1].value in attrs):
                out.append((node.args[1].value, self.stack[-1] if self.stack else "<module>", node.lineno))
            self.generic_visit(node)
    V().visit(tree)
    return out


def test_identity_tag_is_read_only_by_the_screen():
    """STATIC: the identity lines are read only inside the screen functions, in every tracking module."""
    bad = []
    for p in sorted(glob.glob(os.path.join(LIVE, "*.py"))):
        if os.path.basename(p) in IDENTIFICATION_SIDE or os.path.basename(p).startswith("identify"):
            continue
        for attr, fn, line in _attr_loads(p, {"identities", "_identity_for"}):
            if fn not in IDENTITY_FUNCS:
                bad.append(f"{os.path.relpath(p, REPO_ROOT)}:{line} {attr} read in {fn}")
    assert not bad, "the identity tag is read outside the screen: " + "; ".join(bad)


def test_no_tracking_module_imports_identification():
    """STATIC: no tracking module imports identification's code (pipeline.identify, identify_engine or the old
    identify mode); only the entry point routes identification's commands to it."""
    bad = []
    for p in sorted(glob.glob(os.path.join(LIVE, "*.py"))):
        name = os.path.basename(p)
        if name in IDENTIFICATION_SIDE or name.startswith("identify"):
            continue                               # identification's modules (identify*.py) are its side
        tree = ast.parse(open(p, encoding="utf-8").read())
        # identification's own classes inside a shared module (rig.py's IdentificationConsumer) are skipped
        skip = set()
        for c in ast.walk(tree):
            if isinstance(c, ast.ClassDef) and "Identif" in c.name:
                skip |= {id(x) for x in ast.walk(c)}
        for n in ast.walk(tree):
            if id(n) in skip:
                continue
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                mods = [n.module or ""] + [f"{n.module}.{a.name}" for a in n.names]
            for m in mods:
                if m.startswith("pipeline.identify") or "identify_engine" in m or m.endswith("live.identify"):
                    bad.append(f"{name}:{n.lineno} imports {m}")
    assert not bad, "; ".join(bad)


def test_the_hook_routes_only_identification_commands():
    """STATIC: the entry point's hook sends only `replay-identify --session` and `rig ... identify` to the
    identification engine; `replay` and the tracking rig never reach it."""
    src = open(os.path.join(LIVE, "__main__.py"), encoding="utf-8").read()
    hook = [ln for ln in src.splitlines() if "identify_engine import" in ln]
    assert len(hook) == 1, hook
    cond = [ln for ln in src.splitlines() if 'argv[:1] == ["replay-identify"]' in ln]
    assert cond and '"identify" in argv' in cond[0] and '"--session" in argv' in cond[0], cond


@pytest.mark.skipif(os.environ.get("TDR_SLOW") != "1", reason="slow: replays two walks through the model")
def test_scrambled_truth_changes_nothing():
    sys.path.insert(0, REPO_ROOT)
    import subprocess
    code = subprocess.call([sys.executable, os.path.join(REPO_ROOT, "tests", "_truth_isolation_run.py")], cwd=REPO_ROOT)
    assert code == 0
