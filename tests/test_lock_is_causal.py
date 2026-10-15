"""No lock figure can be computed past the causal horizon.

2026-09-23. Two quantities were both called "the 2 s lock": the renderer's, reading windows
`lo .. lo + step`, and the diagnostic proxy in t6, t7, t9 and y1, reading `lo .. lo + step + LAG_W`,
two windows of radio that have not finished recording at the lock.
`reports/tracking/history/2026-09-23_finding-two-locks.md`. Every lock estimator now takes its end window from
`pipeline/retired/constrained/lock_horizon.py`, and these tests hold it there three ways:

1. the guard itself refuses any end past `lo + step`;
2. POISON: every lock estimator is run on emissions whose windows after `lo + step` are replaced by
   a spike on another chain, and its answer must not change. The spike is first shown to be potent:
   a decode that reads two windows further DOES change. A guard that passes a toothless poison
   proves nothing;
3. STATIC: no module in pipeline/constrained adds `LAG_W` to anything, which is the exact form the
   lookahead took in five stages.

The estimators are imported in a SUBPROCESS. Importing them sets `TDR_ART_DIR` process-wide via
`set_half_roots`, which once turned the gait ID session's import guard red from inside pytest.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONSTRAINED = REPO / "pipeline" / "constrained"
# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# RETIRED = REPO / "pipeline" / "retired" / "constrained"   # the former attempts/ (2026-10-01)

#: every function that computes a 2 s lock line or lock score, as (module, function)
LOCK_ESTIMATORS = (
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     ("pipeline.retired.constrained.t6_lockdiag", "viterbi_state_line"),
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     ("pipeline.retired.constrained.t7_lockarms", "viterbi_chain_scores"),
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     ("pipeline.retired.constrained.t9_lengthnorm", "viterbi_chain_scores"),
    # RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
#     ("pipeline.retired.constrained.y2a_causal", "proxy_line"),
)

# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# _POISON = r'''
# import importlib, json, sys
# import numpy as np
#
# class St:
#     names = ["A", "B", "C"]
#     slice_of = {"A": (0, 3), "B": (3, 6), "C": (6, 9)}
#     n_states = 9
#
# rng = np.random.default_rng(7)
# T, S, lo, step = 12, 9, 2, 2
# E = rng.normal(0.0, 1.0, (T, S))
# # chains as the real lattice has them: moving within a chain is cheap, jumping between chains is
# # not, so a spike after the horizon can pull a lookahead backtrace onto its chain
# lT = np.full((S, S), -20.0) + rng.normal(0.0, 0.3, (S, S))
# for nm, (a_, b_) in St.slice_of.items():
#     lT[a_:b_, a_:b_] = np.log(1.0 / (b_ - a_)) + rng.normal(0.0, 0.3, (b_ - a_, b_ - a_))
# st_lo = np.zeros(S)
#
# import pipeline.retired.constrained.lock_horizon as H
# from pipeline.constrained.decoder import viterbi
# from pipeline.constrained.render_display import chain_of
#
# def reported(e):
#     """What a LOOKAHEAD lock would report: the state at `step` decoded through lo + step + LAG_W."""
#     s = viterbi(e[lo:lo + step + H.LAG_W + 1], lT, log_start=st_lo)
#     return chain_of(St, int(s[step]))
#
# target = [n for n in St.names if n != reported(E)][0]
# a, b = St.slice_of[target]
# P = E.copy()
# P[lo + step + 1:, :] = -50.0
# P[lo + step + 1:, a:b] = 50.0
# out = {"lag_w": H.LAG_W, "potent": reported(E) != reported(P), "est": {}}
# for mod, fn in json.loads(sys.argv[1]):
#     f = getattr(importlib.import_module(mod), fn)
#     args = (E, lT, St, st_lo, lo, step) + ((0,) if fn == "proxy_line" else ())
#     pargs = (P,) + args[1:]
#     r0, r1 = f(*args), f(*pargs)
#     out["est"][mod + "." + fn] = {"same": r0 == r1, "clean": str(r0)[:80], "poisoned": str(r1)[:80]}
# print("JSON" + json.dumps(out))
# '''


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def _run_poison():
#     env = dict(os.environ, OMP_NUM_THREADS="1")
#     p = subprocess.run([sys.executable, "-c", _POISON, json.dumps(LOCK_ESTIMATORS)],
#                        cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
#     assert p.returncode == 0, p.stderr[-3000:]
#     line = [ln for ln in p.stdout.splitlines() if ln.startswith("JSON")][-1]
#     return json.loads(line[4:])


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# @pytest.fixture(scope="module")
# def poison():
#     return _run_poison()


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_guard_refuses_any_lookahead():
#     src = (RETIRED / "lock_horizon.py").read_text()
#     tree = ast.parse(src)
#     names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
#     assert {"lock_end", "check_end", "lock_step", "NonCausalLock"} <= names
#     # exercised in the subprocess too, but the arithmetic is simple enough to pin here without
#     # importing pipeline modules into the pytest process
#     ns: dict = {}
#     body = src.split("class NonCausalLock", 1)[1]
#     exec("LAG_W = 2\nSTRIDE = 0.5\nDELAY_S = 2.0\nclass NonCausalLock" + body, ns)
#     assert ns["lock_end"](10, 2, 100) == 12
#     assert ns["lock_end"](10, 2, 11) == 10
#     for end in (13, 14):
#         with pytest.raises(ns["NonCausalLock"]):
#             ns["check_end"](10, 2, end)
#     ns["check_end"](10, 2, 12)
#     assert ns["lock_step"](2.0, 0.5) == 2


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_the_poison_is_potent(poison):
#     assert poison["lag_w"] == 2
#     assert poison["potent"], "the poison does not move a lookahead lock, so it cannot test anything"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# @pytest.mark.parametrize("mod,fn", LOCK_ESTIMATORS)
# def test_no_lock_estimator_reads_past_the_horizon(poison, mod, fn):
#     r = poison["est"][f"{mod}.{fn}"]
#     assert r["same"], (f"{mod}.{fn} changed its answer when only windows AFTER lo + step were "
#                        f"changed: {r['clean']} -> {r['poisoned']}. It reads radio that has not "
#                        f"finished recording at the lock")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_y2a_causal_refuses_lookahead_and_is_retired():
#     env = dict(os.environ, OMP_NUM_THREADS="1")
#     code = ("import numpy as np\n"
#             "from pipeline.retired.constrained.y2a_causal import proxy_line, main\n"
#             "from pipeline.retired.constrained.lock_horizon import NonCausalLock\n"
#             "class St: names=['A']; slice_of={'A':(0,2)}; n_states=2\n"
#             "for f in (lambda: proxy_line(np.zeros((9,2)), np.zeros((2,2)), St, np.zeros(2), 0, 2, 2),"
#             " main):\n"
#             "    try:\n        f()\n    except NonCausalLock:\n        print('REFUSED')\n")
#     p = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True,
#                        text=True, timeout=300)
#     assert p.returncode == 0, p.stderr[-3000:]
#     assert p.stdout.count("REFUSED") == 2, p.stdout


def _adds_lag_w(tree) -> list:
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            for side in (n.left, n.right):
                if isinstance(side, ast.Name) and side.id == "LAG_W":
                    hits.append(n.lineno)
    return hits


def test_no_module_adds_lag_w_to_a_window_index():
    bad = {}
    # RETIRED 2026-10-01: pipeline/retired/constrained/ (the former attempts/) is no longer scanned; it was deleted
    # (git tag tracking-final-2026-10-01). It was: + sorted(RETIRED.glob("*.py"))
    for p in sorted(CONSTRAINED.glob("*.py")):
        hits = _adds_lag_w(ast.parse(p.read_text()))
        if hits:
            bad[p.name] = hits
    assert not bad, (f"`... + LAG_W` is the exact form the lock lookahead took; route the end "
                     f"window through lock_horizon.lock_end instead: {bad}")


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_every_lock_stage_takes_its_end_from_the_horizon_module():
#     # y1_diag and y2_dial were removed on 2026-09-24 with the finished stage modules (git tag pre-cleanup; reports/project/repository/archive-code.md).
#     for stem in ("t6_lockdiag", "t7_lockarms", "t9_lengthnorm"):
#         src = (RETIRED / f"{stem}.py").read_text()
#         assert "from pipeline.retired.constrained.lock_horizon import" in src, stem
#         assert "lock_end(" in src, stem
