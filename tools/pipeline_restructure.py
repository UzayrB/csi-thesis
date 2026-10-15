"""pipeline_restructure: the 1 October 2026 restructure of pipeline/ (Uzayr's instruction of that day).

    python3 -m tools.pipeline_restructure plan     # write the move map, reports/project/repository/2026-10-01_pipeline-moves.json
    python3 -m tools.pipeline_restructure apply    # git mv every file in the map, rewrite every reference
    python3 -m tools.pipeline_restructure lists    # translate the tracking hash lists through the map

THE LAYOUT. pipeline/ keeps four folders, constrained/, identify/, live/ and io/, and gains retired/:
  - branches/gate.py            -> constrained/gate.py
  - models/heads.py, link_cnn.py -> constrained/heads.py, link_cnn.py
  - clean/common.py             -> io/clean.py
  - splits/windows.py           -> io/windows.py
  - realtime/engine.py          -> live/realtime_engine.py   (identify/engine.py exists, hence the name)
  - realtime/rig_run.py, tracker_live.py -> live/
  - realtime/replay.py          -> live/realtime_replay.py   (live/replay.py exists)
  - every file nothing current uses -> retired/<the folder it came from>/

WHAT "USED" MEANS. A file is kept when the current models reach it from an entry point:
  1. every module in live/ and io/, the identification engine (engine, idw_core, ide_*, ixa_*, ixt_*) and every
     pipeline file committed today;
  2. every module named in a report first written on or after 28 September, a run script changed since then,
     the final tracking hash lists or the app's model sets;
  3. everything those import, and every module kept code launches by name ("pipeline.x.y"), to a fixed point.
Anything not reached moves to retired/. Retired files still import: every reference to them is rewritten too.

THE REWRITE. Every .py and .sh file under pipeline/, tests/, tools/ and scripts/, and the Makefile:
  - `from <package> import <module>` statements are rewritten by their syntax tree, split by destination,
    with `as <old name>` added where the module's name changed, so every local name stays the same;
  - then every dotted module path (pipeline.x.y) and file path (pipeline/x/y.py) is replaced, longest first.
Files that move one level deeper and find the repository from their own path get one more dirname.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = os.path.join
MAP_PATH = J(REPO, "reports", "project", "repository", "2026-10-01_pipeline-moves.json")
SELF = "tools/pipeline_restructure.py"

MERGES = {
    "pipeline/branches/gate.py": "pipeline/constrained/gate.py",
    "pipeline/models/heads.py": "pipeline/constrained/heads.py",
    "pipeline/models/link_cnn.py": "pipeline/constrained/link_cnn.py",
    "pipeline/clean/common.py": "pipeline/io/clean.py",
    "pipeline/splits/windows.py": "pipeline/io/windows.py",
    "pipeline/realtime/engine.py": "pipeline/live/realtime_engine.py",
    "pipeline/realtime/rig_run.py": "pipeline/live/rig_run.py",
    "pipeline/realtime/tracker_live.py": "pipeline/live/tracker_live.py",
    "pipeline/realtime/replay.py": "pipeline/live/realtime_replay.py",
}
#: packages that disappear: their __init__.py is removed once their modules have moved
GONE = ["pipeline/branches", "pipeline/clean", "pipeline/models", "pipeline/realtime", "pipeline/splits",
        "pipeline/constrained/attempts"]
TRACK_CELLS = ("fin_A3", "fin_B2", "zsf_B2")


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout


def mod(p: str) -> str:
    return p[:-3].replace("/", ".") if p.endswith(".py") else p.replace("/", ".")


def modpath(m: str):
    p = m.replace(".", "/")
    if os.path.isfile(J(REPO, p + ".py")):
        return p + ".py"
    if os.path.isfile(J(REPO, p, "__init__.py")):
        return p + "/__init__.py"
    return None


def pipeline_files() -> list:
    out = []
    for d, _, fs in os.walk(J(REPO, "pipeline")):
        if "__pycache__" in d:
            continue
        out += [os.path.relpath(J(d, f), REPO) for f in fs if f.endswith(".py")]
    return sorted(out)


def imports_of(path: str) -> set:
    try:
        tree = ast.parse(open(J(REPO, path), encoding="utf-8").read())
    except SyntaxError:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module)
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return {m for m in out if m.startswith("pipeline")}


def closure(entries) -> set:
    seen, stack = set(), list(entries)
    while stack:
        m = stack.pop()
        p = modpath(m)
        if not p or p in seen:
            continue
        seen.add(p)
        parts = m.split(".")
        stack += [".".join(parts[:i]) for i in range(1, len(parts))]
        stack += list(imports_of(p))
    return seen


def named_in(paths) -> set:
    pat = re.compile(r"pipeline[./][a-z_]+(?:[./][A-Za-z0-9_]+)+")
    out = set()
    for p in paths:
        try:
            t = open(J(REPO, p), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        out |= {m.replace("/", ".").removesuffix(".py") for m in pat.findall(t)}
    return out


def plan() -> dict:
    files = pipeline_files()
    since = "2026-09-28 00:00"
    reports = [p for p in git("log", "--diff-filter=A", f"--since={since}", "--name-only", "--format=", "--",
                              "reports").split() if os.path.exists(J(REPO, p))]
    cutoff = datetime.datetime(2026, 9, 28).timestamp()
    scripts = []
    for d in ("runs/dc2_results", "runs/identify/engine/queue", "runs/identify/final_extras/queue"):
        if os.path.isdir(J(REPO, d)):
            scripts += [J(d, f) for f in os.listdir(J(REPO, d))
                        if f.endswith(".sh") and os.path.getmtime(J(REPO, d, f)) >= cutoff]
    records = [J("runs/dc2_results/final", f"TRACE_HASHES_{c}.txt") for c in TRACK_CELLS]
    records += [J("runs/live/models", f) for f in os.listdir(J(REPO, "runs/live/models")) if f.endswith(".json")]
    today = [p for p in git("log", "--since=2026-10-01 00:00", "--name-only", "--format=", "--", "pipeline").split()
             if p.endswith(".py") and os.path.exists(J(REPO, p))]
    ident = [p for p in files if re.match(r"pipeline/identify/(engine|idw_core|ide_\w+|ixa_\w+|ixt_\w+)\.py$", p)]
    entries = {mod(p) for p in files if p.startswith(("pipeline/live/", "pipeline/io/"))}
    entries |= {mod(p) for p in ident + today}
    entries |= named_in(reports + scripts + records)
    while True:
        kept = closure(entries)
        more = named_in(sorted(kept)) - entries
        if not more:
            break
        entries |= more
    retire = [p for p in files if p not in kept and not p.endswith("__init__.py")]
    moves = dict(MERGES)
    for p in retire:
        parts = p.split("/")
        origin = "constrained" if parts[1] == "constrained" else parts[1]
        if p in moves:
            continue
        moves[p] = f"pipeline/retired/{origin}/{parts[-1]}"
    dests = list(moves.values())
    clash = sorted({d for d in dests if dests.count(d) > 1 or (os.path.exists(J(REPO, d)) and d not in moves)})
    if clash:
        raise SystemExit(f"REFUSED: destinations clash: {clash}")
    left = [p for p in files if p.startswith(tuple(g + "/" for g in GONE)) and p not in moves
            and not p.endswith("__init__.py")]
    if left:
        raise SystemExit(f"REFUSED: files in a removed package have no destination: {left}")
    out = {"written": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "rule": "kept = reached from the current models' entry points (tools/pipeline_restructure.py docstring)",
           "n_kept": len(kept), "n_moved": len(moves),
           "moves": dict(sorted(moves.items())),
           "modules": {mod(a): mod(b) for a, b in sorted(moves.items())},
           "packages_removed": GONE,
           "entry_sources": {"reports": len(reports), "scripts": len(scripts), "records": len(records),
                             "committed_today": len(today)}}
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"plan: {len(kept)} kept, {len(moves)} moved ({len(MERGES)} merged, {len(moves) - len(MERGES)} retired)")
    return out


def _rewrite_from_imports(text: str, mm: dict, path: str) -> str:
    """`from <package> import <names>` where a name is a moved module: one statement per destination."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    edits = []
    gone = {mod(g) for g in GONE}
    for n in ast.walk(tree):
        if not (isinstance(n, ast.ImportFrom) and n.level == 0 and n.module and n.module.startswith("pipeline")):
            continue
        if not any(f"{n.module}.{a.name}" in mm for a in n.names):
            if n.module in gone and n.module not in mm:
                raise SystemExit(f"{path}:{n.lineno}: imports from removed package {n.module}")
            continue
        groups = {}
        for a in n.names:
            full = f"{n.module}.{a.name}"
            if full in mm:
                pkg, name = mm[full].rsplit(".", 1)
                asname = a.asname or (a.name if name != a.name else None)
                groups.setdefault(pkg, []).append(name + (f" as {asname}" if asname else ""))
            else:
                if n.module in gone:
                    raise SystemExit(f"{path}:{n.lineno}: {a.name} from removed package {n.module} is not a module")
                groups.setdefault(n.module, []).append(a.name + (f" as {a.asname}" if a.asname else ""))
        first, last = lines[n.lineno - 1], lines[n.end_lineno - 1]
        indent = first[: n.col_offset]
        if indent.strip() or last[n.end_col_offset:].strip() not in ("", "\\") and not last[n.end_col_offset:].strip().startswith("#"):
            raise SystemExit(f"{path}:{n.lineno}: import shares its line with other code; rewrite by hand")
        tail = last[n.end_col_offset:]
        new = "".join(f"{indent}from {pkg} import {', '.join(items)}\n" for pkg, items in groups.items())
        new = new[:-1] + tail if tail.strip() else new[:-1] + "\n"
        edits.append((n.lineno - 1, n.end_lineno, new))
    for a, b, new in sorted(edits, reverse=True):
        lines[a:b] = [new]
    return "".join(lines)


def rewrite_text(text: str, mm: dict, pm: dict, path: str) -> str:
    if path.endswith(".py"):
        text = _rewrite_from_imports(text, mm, path)
    for old in sorted(mm, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9_.])" + re.escape(old) + r"(?![A-Za-z0-9_])", mm[old], text)
    for old in sorted(pm, key=len, reverse=True):
        text = text.replace(old, pm[old])
    text = text.replace("pipeline/constrained/attempts/", "pipeline/retired/constrained/")
    text = re.sub(r"(?<![A-Za-z0-9_.])pipeline\.constrained\.attempts\.", "pipeline.retired.constrained.", text)
    return text


def targets() -> list:
    out = ["Makefile"]
    for root in ("pipeline", "tests", "tools", "scripts"):
        for d, _, fs in os.walk(J(REPO, root)):
            if "__pycache__" in d:
                continue
            out += [os.path.relpath(J(d, f), REPO) for f in fs if f.endswith((".py", ".sh"))]
    return sorted(p for p in out if p != SELF)


def apply() -> int:
    m = json.load(open(MAP_PATH, encoding="utf-8"))
    moves = m["moves"]
    mm = dict(m["modules"])
    for a, b in moves.items():                       # the attempts package path, as imported
        mm.setdefault(mod(a), mod(b))
    pm = dict(moves)
    # refuse only when a file this run moves or rewrites has uncommitted changes (someone else's edit)
    dirty = {l[3:].strip() for l in git("status", "--porcelain", "--", "pipeline", "tests", "tools", "scripts",
                                         "Makefile").splitlines() if not l.startswith("??")}
    touched = set(moves)
    for p in targets():
        t = open(J(REPO, p), encoding="utf-8").read()
        if rewrite_text(t, mm, pm, p) != t:
            touched.add(p)
    clash = sorted(dirty & touched)
    if clash:
        raise SystemExit(f"REFUSED: uncommitted changes in files this run moves or rewrites: {clash}")
    # 1. the new packages
    for origin in sorted({b.split("/")[2] for b in moves.values() if b.startswith("pipeline/retired/")}):
        os.makedirs(J(REPO, "pipeline", "retired", origin), exist_ok=True)
        ip = J(REPO, "pipeline", "retired", origin, "__init__.py")
        if not os.path.exists(ip):
            with open(ip, "w", encoding="utf-8") as f:
                f.write(f'"""Retired 2026-10-01: modules from pipeline/{origin}/ that the current models do not use.\n\n'
                        f'Kept so that older results can be regenerated. The map of every move is\n'
                        f'reports/PIPELINE_MOVES_2026-10-01.json."""\n')
    ip = J(REPO, "pipeline", "retired", "__init__.py")
    if not os.path.exists(ip):
        with open(ip, "w", encoding="utf-8") as f:
            f.write('"""Retired code: modules the current models do not use, by the folder they came from.\n\n'
                    'Moved here on 2026-10-01 (reports/project/repository/2026-10-01_pipeline-restructure.md). Each still imports, as\n'
                    '``pipeline.retired.<origin>.<name>``."""\n')
    # 2. the moves, with the depth fix for files one level deeper
    deeper = []
    for a, b in moves.items():
        os.makedirs(os.path.dirname(J(REPO, b)), exist_ok=True)
        git("mv", a, b)
        if b.count("/") > a.count("/") and not a.startswith("pipeline/constrained/attempts/"):
            deeper.append(b)
    three = "os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    four = "os.path.dirname(" + three + ")"
    for b in deeper:
        t = open(J(REPO, b), encoding="utf-8").read()
        if three in t and four not in t:
            with open(J(REPO, b), "w", encoding="utf-8") as f:
                f.write(t.replace(three, four))
    # 3. the removed packages (their compiled caches go with them)
    for g in GONE:
        ip = J(g, "__init__.py")
        if os.path.exists(J(REPO, ip)):
            git("rm", "-q", ip)
        left = [f for f in os.listdir(J(REPO, g)) if f != "__pycache__"] if os.path.isdir(J(REPO, g)) else []
        if left:
            raise SystemExit(f"REFUSED: {g} still holds {left}")
        if os.path.isdir(J(REPO, g)):
            shutil.rmtree(J(REPO, g, "__pycache__"), ignore_errors=True)
            os.rmdir(J(REPO, g))
    # 4. every reference
    changed = []
    for p in targets():
        t = open(J(REPO, p), encoding="utf-8").read()
        n = rewrite_text(t, mm, pm, p)
        if n != t:
            with open(J(REPO, p), "w", encoding="utf-8") as f:
                f.write(n)
            changed.append(p)
    git("add", "pipeline/retired")
    print(json.dumps({"moved": len(moves), "one_level_deeper": len(deeper), "rewritten": len(changed),
                      "rewritten_files": changed}, indent=1))
    return 0


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lists() -> int:
    """Each tracking hash list through the map: moved files under their new paths, code re-hashed. The original
    list is kept beside it as TRACE_HASHES_<cell>.pre_restructure.txt; pd_repro_trace run then verifies it."""
    moves = json.load(open(MAP_PATH, encoding="utf-8"))["moves"]
    names = [f"TRACE_HASHES_{c}" for c in TRACK_CELLS] + ["FINAL_CORRECTED_HASHES"]   # the pre-flight reads all four
    for c in names:
        lp = J(REPO, "runs", "dc2_results", "final", f"{c}.txt")
        keep = lp.replace(".txt", ".pre_restructure.txt")
        if not os.path.exists(keep):
            os.replace(lp, keep)
        rows, moved, rehashed, data_changed, dropped = [], 0, 0, [], []
        gone_inits = {J(g, "__init__.py") for g in GONE}
        listed = set()
        for ln in open(keep, encoding="utf-8"):
            if not ln.strip():
                continue
            h, p = ln.split(None, 1)
            p = p.strip()
            if p in gone_inits:                      # a package that no longer exists
                dropped.append(p)
                continue
            q = moves.get(p, p)
            moved += q != p
            listed.add(q)
            if q.startswith("pipeline/"):
                nh = sha(J(REPO, q))
                rehashed += nh != h
                h = nh
            elif sha(J(REPO, q)) != h:
                data_changed.append(q)
            rows.append(f"{h}  {q}")
        if data_changed:
            raise SystemExit(f"REFUSED: {c}: non-code inputs changed: {data_changed}")
        added = []
        for q in sorted(listed):                     # the package a moved module now lives in
            ip = J(os.path.dirname(q), "__init__.py")
            if q.startswith("pipeline/") and q in set(moves.values()) and ip not in listed \
                    and os.path.exists(J(REPO, ip)):
                listed.add(ip)
                added.append(ip)
                rows.append(f"{sha(J(REPO, ip))}  {ip}")
        with open(lp, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(rows, key=lambda r: r.split(None, 1)[1])) + "\n")
        print(f"{c}: {len(rows)} files, {moved} under new paths, {rehashed} code files re-hashed, "
              f"dropped {dropped}, added {added}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("plan", "apply", "lists"))
    a = ap.parse_args(argv)
    os.chdir(REPO)
    if a.cmd == "plan":
        plan()
        return 0
    return apply() if a.cmd == "apply" else lists()


if __name__ == "__main__":
    sys.exit(main())
