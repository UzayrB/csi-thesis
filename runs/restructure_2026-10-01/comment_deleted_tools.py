"""Comment out, in test files, everything that needs the deleted pipeline/retired/ or the two deleted scripts.

A top-level statement (function with its decorators, assignment, import) is commented out when its source names
deleted code, or when it uses a name bound by a statement already commented out (to a fixed point). In a module-level
dict, list, tuple or set literal that mixes deleted and current entries, only the deleted entries are commented out.
"""
import ast, glob, os, re, sys

REPO = sys.argv[1]
FILES = sys.argv[2:]
PAT = re.compile(r"tools[./](dc2_capture|dc2_day_check|dc2b_day_check|dc2_hardware_check|teaching_pack|teaching_pack_corrected)\b|from tools import [^\n]*\b(dc2_capture|dc2_day_check|dc2b_day_check|dc2_hardware_check|teaching_pack|teaching_pack_corrected)\b")
MARK = ("# RETIRED 2026-10-01: commented out with the DC2 and teaching-pack tools, deleted that day (Uzayr); the code "
        "it needed is in git at 5c49f09.\n")


def names_bound(n):
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {n.name}
    if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        ts = n.targets if isinstance(n, ast.Assign) else [n.target]
        return {x.id for t in ts for x in ast.walk(t) if isinstance(x, ast.Name)}
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        return {(a.asname or a.name).split(".")[0] for a in n.names}
    return set()


def names_used(n):
    return {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}


def span(n):
    start = min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])
    return start, n.end_lineno


def process(path):
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
    whole, partial = set(), {}
    for n in body:
        a, b = span(n)
        seg = "".join(l for l in lines[a - 1:b] if not l.lstrip().startswith("#"))
        if not PAT.search(seg):
            continue
        val = getattr(n, "value", None)
        if isinstance(n, ast.Assign) and isinstance(val, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
            elts = list(zip(val.keys, val.values)) if isinstance(val, ast.Dict) else [(e, e) for e in val.elts]
            bad = [(k, v) for k, v in elts if PAT.search("".join(l for l in lines[min(k.lineno, v.lineno) - 1:v.end_lineno]
                                                                  if not l.lstrip().startswith("#")))]
            if bad:
                partial[id(n)] = (n, bad)
                continue
        whole.add(id(n))
    while True:
        dead = set().union(*[names_bound(n) for n in body if id(n) in whole]) if whole else set()
        more = {id(n) for n in body if id(n) not in whole and id(n) not in partial and names_used(n) & dead}
        if not more:
            break
        whole |= more
    ranges = []
    for n in body:
        if id(n) in whole:
            ranges.append(span(n))
    for n, bad in partial.values():
        for k, v in bad:
            ranges.append((min(k.lineno, v.lineno), v.end_lineno))
    ranges.sort()
    for (a1, b1), (a2, b2) in zip(ranges, ranges[1:]):
        if a2 <= b1:
            raise SystemExit(f"{path}: overlapping ranges {a1}-{b1} and {a2}-{b2}; do it by hand")
    for a, b in reversed(ranges):
        ind = re.match(r"\s*", lines[a - 1]).group(0)
        block = [ind + MARK.lstrip()] + [("# " + l if l.strip() else "#\n") for l in lines[a - 1:b]]
        lines[a - 1:b] = block
    new = "".join(lines)
    compile(new, path, "exec")
    open(path, "w", encoding="utf-8").write(new)
    kept = [n.name for n in body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_") and id(n) not in whole]
    gone = [n.name for n in body if isinstance(n, ast.FunctionDef) and id(n) in whole]
    other = [sorted(names_bound(n)) for n in body if id(n) in whole and not isinstance(n, ast.FunctionDef)]
    print(f"{path}: commented functions {gone}; other statements {other}; "
          f"entries {sum(len(b) for _, b in partial.values())}; tests kept {len(kept)}")


for f in FILES:
    process(os.path.join(REPO, f))
