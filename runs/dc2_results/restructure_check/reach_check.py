"""Item 4e: which pipeline modules are reachable, statically, from pipeline/live/ and from the G2 and repro entry points
(every import statement anywhere in a file, including inside functions, plus every "pipeline.x.y" module named in a
string, as subprocess "-m" calls name them). Writes runs/dc2_results/restructure_check/REACH_CHECK.json."""
import ast, glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)
def file_of(mod):
    p = mod.replace(".", "/")
    for c in (p + ".py", p + "/__init__.py"):
        if os.path.exists(c):
            return c
    return None
def refs(path):
    out = set()
    tree = ast.parse(open(path, encoding="utf-8").read())
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module)
            out |= {f"{n.module}.{a.name}" for a in n.names}
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out |= set(re.findall(r"\bpipeline(?:\.[A-Za-z_][A-Za-z0-9_]*)+", n.value))
    return {m for m in out if m.startswith("pipeline")}
def closure(starts):
    seen, todo = set(), list(starts)
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        for m in refs(f):
            parts = m.split(".")
            for i in range(2, len(parts) + 1):          # the package inits on the way, and the module itself
                g = file_of(".".join(parts[:i]))
                if g and g not in seen:
                    todo.append(g)
    return seen
starts = {"pipeline/live (every module)": sorted(glob.glob("pipeline/live/*.py")),
          "G2 (final_model gate)": ["pipeline/live/final_model.py", "pipeline/live/gates.py"],
          "repro (pd_repro_trace)": ["pipeline/constrained/pd_repro_trace.py"]}
res = {}
for k, s in starts.items():
    c = closure(s)
    res[k] = {"n_files": len(c), "retired": sorted(x for x in c if "/retired/" in x), "files": sorted(c)}
    print(k, len(c), "files reachable; retired:", res[k]["retired"])
json.dump(res, open("runs/dc2_results/restructure_check/REACH_CHECK.json", "w"), indent=1)
